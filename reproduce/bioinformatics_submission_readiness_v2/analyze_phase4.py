#!/usr/bin/env python3
"""Apply the frozen candidate-site and 24-hour capacity gates to Phase 4."""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = ROOT / "reproduce/bioinformatics_submission_readiness_v2"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(SCRIPT_ROOT))

import gasal2_candidate_sites as candidate_sites  # noqa: E402
import gasal2_longtarget as legacy  # noqa: E402
import run_phase4 as runner  # noqa: E402
from capacity import WorkloadTimings, paired_hierarchical_bootstrap  # noqa: E402
from cpu_reference_screen import receipt_mapping  # noqa: E402


PAPER = ROOT / "paper/bioinformatics_submission_readiness_v2"
PLAN = PAPER / "phase_3_performance_plan.json"
CONTRACT_SPEC = ROOT / "paper/biological_topk/contract_spec.json"
COMPARATOR = ROOT / "reproduce/biological_topk/compare_candidate_topk.py"
PHASE4_ROOT = ROOT / ".paper-artifacts/bioinformatics-submission-readiness-v2/phase4"
FORMAL_ROOT = PHASE4_ROOT / "formal"
COMPARISON_ROOT = PHASE4_ROOT / "comparisons"
ANALYSIS_ROOT = PHASE4_ROOT / "analysis"


class AnalysisError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AnalysisError(message)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    legacy.atomic_json(path, dict(value))


def load_attempts() -> list[dict[str, str]]:
    return runner.load_attempts()


def product_identity(row: Mapping[str, str]) -> candidate_sites.ProductIdentity:
    return candidate_sites.ProductIdentity(
        workload_id=row["workload_id"],
        query_ordinal_namespace=row["query_ordinal_namespace"],
        query_source_ordinal=row["query_source_ordinal"],
        target_ordinal_namespace=row["target_ordinal_namespace"],
        target_source_ordinal=row["target_source_ordinal"],
        assembly=row["assembly"],
        target_coordinate_namespace=row["target_coordinate_namespace"],
        query_extraction_recipe_id=row["query_extraction_recipe_id"],
        target_extraction_recipe_id=row["target_extraction_recipe_id"],
        target_region_start0=int(row["target_region_start0"]),
    )


def write_gpu_receipt(row: Mapping[str, str], gpu_attempt: Path, destination: Path) -> Path:
    query = candidate_sites.read_single_fasta(ROOT / row["query_path"], "query")
    target = candidate_sites.read_single_fasta(ROOT / row["target_path"], "target")
    receipt = candidate_sites.build_receipt(
        query=query,
        target=target,
        tfosorted=gpu_attempt / "product/diagnostics/native-TFOsorted",
        identity=product_identity(row),
    )
    receipt = replace(receipt, evidence_role="v2_phase4_gpu_offline_comparison")
    path = destination / "gpu-input-receipt.json"
    atomic_json(path, receipt_mapping(receipt))
    return path


def run_comparator(row: Mapping[str, str], authority: Path, gpu: Path, destination: Path) -> dict[str, Any]:
    gpu_receipt = write_gpu_receipt(row, gpu, destination)
    command = [
        sys.executable,
        str(COMPARATOR),
        "--authority",
        str(authority / "product/diagnostics/native-TFOsorted"),
        "--candidate",
        str(gpu / "product/diagnostics/native-TFOsorted"),
        "--authority-receipt",
        str(authority / "product/input-receipt.json"),
        "--candidate-receipt",
        str(gpu_receipt),
        "--contract-spec",
        str(CONTRACT_SPEC),
        "--output-json",
        str(destination / "comparison.json"),
        "--details-tsv",
        str(destination / "comparison-details.tsv"),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (destination / "comparator-stdout.log").write_text(completed.stdout, encoding="utf-8")
    (destination / "comparator-stderr.log").write_text(completed.stderr, encoding="utf-8")
    require((destination / "comparison.json").is_file(), "comparator did not emit JSON")
    result = load_json(destination / "comparison.json")
    return {
        "command": command,
        "returncode": completed.returncode,
        "result": result,
    }


def analyze_pair(rows: list[dict[str, str]]) -> dict[str, Any]:
    require(len(rows) == 2 and {row["arm"] for row in rows} == {"A", "G"}, "invalid formal pair manifest")
    by_arm = {row["arm"]: row for row in rows}
    pair_id = rows[0]["pair_id"]
    destination = COMPARISON_ROOT / pair_id
    if destination.exists():
        terminal = destination / "pair-terminal.json"
        require(terminal.is_file(), f"existing comparison lacks terminal receipt: {pair_id}")
        return load_json(terminal)
    partial = COMPARISON_ROOT / f".{pair_id}.partial"
    require(not partial.exists(), f"orphaned comparison partial: {partial}")
    partial.mkdir(parents=True)
    attempts = {arm: FORMAL_ROOT / row["attempt_id"] for arm, row in by_arm.items()}
    terminals = {arm: load_json(path / "attempt-terminal.json") for arm, path in attempts.items()}
    pair: dict[str, Any] = {
        "schema_version": 1,
        "phase": 4,
        "pair_id": pair_id,
        "workload_id": rows[0]["workload_id"],
        "repeat_index": int(rows[0]["repeat_index"]),
        "technical_success_pair": all(item["technical_success"] for item in terminals.values()),
        "contract_pass": False,
        "comparison_status": "not_run_technical_failure",
        "failure_reason": None,
        "arm_wall_seconds": {
            arm: terminal["execution"]["wall_seconds"] if terminal["execution"] is not None else None
            for arm, terminal in terminals.items()
        },
        "arm_candidate_sites_sha256": {
            arm: terminal["product"]["candidate_sites_sha256"] if terminal["product"] is not None else None
            for arm, terminal in terminals.items()
        },
        "comparator": None,
    }
    try:
        require(pair["technical_success_pair"], "one or both formal arms failed technically")
        comparison = run_comparator(by_arm["G"], attempts["A"], attempts["G"], partial)
        pair["comparator"] = comparison
        pair["comparison_status"] = comparison["result"]["comparison_status"]
        pair["contract_pass"] = comparison["result"]["contract_pass"] is True
        require(comparison["returncode"] == 0, "candidate-site comparator rejected formal pair")
        require(pair["contract_pass"], "candidate-site contract did not pass")
    except Exception as error:
        pair["failure_reason"] = f"{type(error).__name__}:{error}"
    pair["terminal_utc"] = legacy.utc_now()
    atomic_json(partial / "pair-terminal.json", pair)
    os.replace(partial, destination)
    return pair


def write_pair_table(path: Path, pairs: list[dict[str, Any]]) -> None:
    fields = (
        "pair_id",
        "workload_id",
        "repeat_index",
        "technical_success_pair",
        "contract_pass",
        "comparison_status",
        "authority_wall_seconds",
        "gpu_wall_seconds",
        "paired_speedup",
        "failure_reason",
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for pair in sorted(pairs, key=lambda item: (item["workload_id"], item["repeat_index"])):
            authority = pair["arm_wall_seconds"]["A"]
            gpu = pair["arm_wall_seconds"]["G"]
            writer.writerow(
                {
                    "pair_id": pair["pair_id"],
                    "workload_id": pair["workload_id"],
                    "repeat_index": pair["repeat_index"],
                    "technical_success_pair": int(pair["technical_success_pair"]),
                    "contract_pass": int(pair["contract_pass"]),
                    "comparison_status": pair["comparison_status"],
                    "authority_wall_seconds": authority if authority is not None else "NA",
                    "gpu_wall_seconds": gpu if gpu is not None else "NA",
                    "paired_speedup": authority / gpu if authority is not None and gpu is not None else "NA",
                    "failure_reason": pair["failure_reason"] or "",
                }
            )


def workload_timings(pairs: list[dict[str, Any]]) -> tuple[list[WorkloadTimings], dict[str, Any]]:
    grouped: dict[str, dict[int, dict[str, Any]]] = {}
    for pair in pairs:
        grouped.setdefault(pair["workload_id"], {})[pair["repeat_index"]] = pair
    rows: list[WorkloadTimings] = []
    determinism: dict[str, Any] = {}
    for workload_id in sorted(grouped):
        repeats = grouped[workload_id]
        require(set(repeats) == set(range(5)), f"repeat inventory drift: {workload_id}")
        authority = tuple(float(repeats[index]["arm_wall_seconds"]["A"]) for index in range(5))
        gpu = tuple(float(repeats[index]["arm_wall_seconds"]["G"]) for index in range(5))
        arm_digests = {
            arm: {repeats[index]["arm_candidate_sites_sha256"][arm] for index in range(5)}
            for arm in ("A", "G")
        }
        determinism[workload_id] = {
            "authority_unique_candidate_sites_digests": len(arm_digests["A"]),
            "gpu_unique_candidate_sites_digests": len(arm_digests["G"]),
            "pass": len(arm_digests["A"]) == 1 and len(arm_digests["G"]) == 1,
        }
        rows.append(WorkloadTimings(workload_id, authority, gpu))
    return rows, determinism


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyze", action="store_true", required=True)
    parser.parse_args()
    try:
        phase3_commit, plan = runner.verify_launch_boundary()
        attempts = load_attempts()
        run_summary = load_json(PHASE4_ROOT / "run-summary.json")
        require(run_summary["formal_execution_complete"] is True, "formal arm execution is incomplete")
        require(run_summary["planned_arm_attempts"] == len(attempts), "formal run denominator drift")
        by_pair: dict[str, list[dict[str, str]]] = {}
        for row in attempts:
            by_pair.setdefault(row["pair_id"], []).append(row)
        require(len(by_pair) == 50, "formal paired-row count drift")
        COMPARISON_ROOT.mkdir(parents=True, exist_ok=True)
        pairs = [analyze_pair(rows) for _, rows in sorted(by_pair.items())]
        ANALYSIS_ROOT.mkdir(parents=True, exist_ok=False)
        technical_pairs = sum(pair["technical_success_pair"] for pair in pairs)
        contract_pairs = sum(pair["contract_pass"] for pair in pairs)
        all_eligible = technical_pairs == len(pairs) and contract_pairs == len(pairs)
        timings: list[WorkloadTimings] = []
        determinism: dict[str, Any] = {}
        capacity = None
        secondary: dict[str, Any] = {}
        deterministic = False
        if all_eligible:
            timings, determinism = workload_timings(pairs)
            deterministic = all(item["pass"] for item in determinism.values())
            if deterministic:
                estimator = plan["capacity_estimator"]
                capacity = paired_hierarchical_bootstrap(
                    timings,
                    authority_workers=estimator["authority_workers"],
                    gpu_workers=estimator["gpu_workers"],
                    replicates=estimator["bootstrap_replicates"],
                    seed=estimator["bootstrap_seed"],
                )
                point = capacity["point_estimate"]
                speeds = [
                    pair["arm_wall_seconds"]["A"] / pair["arm_wall_seconds"]["G"]
                    for pair in pairs
                ]
                secondary = {
                    "median_paired_end_to_end_speedup": statistics.median(speeds),
                    "absolute_batch_wall_time_saving_seconds": point["authority_makespan_seconds"] - point["gpu_makespan_seconds"],
                }
        gate_pass = bool(
            capacity is not None
            and capacity["bootstrap"]["one_sided_95_lcb"] >= plan["primary_gate"]["capacity_ratio_lcb_minimum"]
            and capacity["point_estimate"]["capacity_ratio"] >= plan["primary_gate"]["point_estimate_consistency_minimum"]
        )
        decision = "performance_pass" if all_eligible and deterministic and gate_pass else "performance_no_go"
        timings_mapping = {
            "schema_version": 1,
            "workloads": [
                {
                    "workload_id": row.workload_id,
                    "authority_seconds": list(row.authority_seconds),
                    "gpu_seconds": list(row.gpu_seconds),
                }
                for row in timings
            ],
        }
        atomic_json(ANALYSIS_ROOT / "timings.json", timings_mapping)
        atomic_json(ANALYSIS_ROOT / "determinism.json", {"schema_version": 1, "workloads": determinism})
        write_pair_table(ANALYSIS_ROOT / "pair-results.tsv", pairs)
        result = {
            "schema_version": 1,
            "phase": 4,
            "phase3_commit": phase3_commit,
            "software_epoch": "submission_rc_v2_2",
            "planned_pair_rows": len(pairs),
            "technical_success_pair_rows": technical_pairs,
            "candidate_site_contract_pass_rows": contract_pairs,
            "all_outputs_deterministic": deterministic,
            "primary_capacity_estimate_computed": capacity is not None,
            "capacity": capacity,
            "secondary": secondary,
            "primary_gate_pass": gate_pass,
            "decision": decision,
            "downstream_phases_authorized": decision == "performance_pass",
            "completed_utc": legacy.utc_now(),
        }
        atomic_json(ANALYSIS_ROOT / "decision.json", result)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, AnalysisError, runner.Phase4Error) as error:
        print(f"Phase 4 analysis failed closed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
