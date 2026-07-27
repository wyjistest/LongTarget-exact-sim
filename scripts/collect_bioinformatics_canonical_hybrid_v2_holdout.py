#!/usr/bin/env python3
"""Validate and freeze canonical-hybrid-v2 fresh holdout evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "reproduce/bioinformatics/run_canonical_hybrid_v2.py"
STAGE_ROOT = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/fresh-holdout"
PLAN_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_plan.tsv"
PLAN_RECEIPT_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_plan_receipt.json"
SELECTION_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_selection.json"
WORKLOAD_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_workloads.tsv"
RESULTS_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_results.tsv"
ARTIFACTS_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_artifacts.tsv"
RECEIPT_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_receipt.json"
DECISION_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout_decision.md"
CHECKSUM_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_holdout.sha256"
RESULT_FIELDS = (
    "validation_id",
    "workload_id",
    "repeat_id",
    "query_id",
    "target_id",
    "query_stratum",
    "target_chromosome",
    "gpu_physical_index",
    "authority_attempt_id",
    "hybrid_attempt_id",
    "authority_output_rows",
    "hybrid_output_rows",
    "authority_output_sha256",
    "hybrid_output_sha256",
    "score_equal",
    "stability_equal",
    "nt_equal",
    "all_three_equal",
    "boundary_ties_equal",
    "full_output_equal",
    "full_missing_rows",
    "full_extra_rows",
    "declared_contract_clean",
    "authority_wall_seconds",
    "hybrid_wall_seconds",
    "score_prepass_seconds",
    "cpu_traceback_replay_seconds",
    "cpu_traceback_align_seconds",
    "triplex_convert_seconds",
    "attempt_rows",
    "selected_attempts",
    "cpu_traceback_calls",
    "fallbacks",
    "authority_max_rss_kib",
    "hybrid_max_rss_kib",
    "gpu_measurement_status",
    "gpu_sample_count",
    "gpu_memory_peak_mib",
    "authority_receipt_sha256",
    "hybrid_receipt_sha256",
)
ARTIFACT_FIELDS = ("path", "size_bytes", "sha256", "role", "formal_source_data")


class CollectionError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CollectionError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def tsv_bytes(fieldnames: Sequence[str], rows: list[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, delimiter="\t", lineterminator="\n", extrasaction="raise"
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def atomic_new(path: Path, payload: bytes) -> None:
    require(not path.exists(), f"refusing to replace frozen holdout evidence: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    require(completed.returncode == 0, completed.stderr.strip() or "git command failed")
    return completed.stdout.strip()


def require_clean_checkout() -> str:
    status = git_output("status", "--porcelain=v1", "--untracked-files=all", "--ignored=no")
    require(not status, f"holdout evidence freeze requires a clean checkout: {status}")
    return git_output("rev-parse", "HEAD")


def load_runner():
    spec = importlib.util.spec_from_file_location("canonical_hybrid_v2_holdout_collector_runner", RUNNER_PATH)
    require(spec is not None and spec.loader is not None, "cannot load canonical hybrid runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_tsv(path: Path) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def validate_snapshot() -> dict[str, object]:
    snapshot_root = STAGE_ROOT / "execution-snapshot"
    snapshot_path = snapshot_root / "snapshot.json"
    require(snapshot_path.is_file() and not snapshot_path.is_symlink(), "execution snapshot is missing")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    require(snapshot.get("schema_version") == 1 and snapshot.get("stage") == "fresh-holdout", "snapshot identity drift")
    require(snapshot.get("plan_sha256") == sha256_file(PLAN_PATH), "snapshot plan drift")
    observed: set[str] = set()
    for path in sorted(snapshot_root.rglob("*")):
        require(not path.is_symlink(), f"snapshot artifact is a symlink: {path}")
        if path.is_file():
            observed.add(path.relative_to(snapshot_root).as_posix())
    require(observed == set(snapshot["files"]) | {"snapshot.json"}, "post-execution snapshot file set drift")
    for relative, identity in snapshot["files"].items():
        path = snapshot_root / relative
        require(path.stat().st_size == identity["size_bytes"], f"snapshot size drift: {relative}")
        require(sha256_file(path) == identity["sha256"], f"snapshot digest drift: {relative}")
    require(not any(part == "__pycache__" for path in snapshot_root.rglob("*") for part in path.parts), "snapshot bytecode cache detected")
    return snapshot


def artifact_role(relative: str) -> str:
    if relative.startswith("execution-snapshot/"):
        return "execution_snapshot"
    if relative == "stage-summary.json":
        return "stage_summary"
    if relative.endswith("attempt-telemetry.tsv"):
        return "per_attempt_telemetry"
    if "/output/" in relative:
        return "contract_output"
    if relative.endswith("authority-reference.tfosorted"):
        return "paired_authority_copy"
    if relative.endswith("comparison.json") or relative.endswith("comparison-details.tsv"):
        return "comparison"
    if relative.endswith("attempt-complete.json"):
        return "attempt_receipt"
    return "supporting_raw_artifact"


def decision_bytes(receipt: dict[str, object]) -> bytes:
    text = f"""# Canonical-Hybrid-v2 Fresh Holdout Decision

The input-only fresh holdout completed all 60 frozen A/H validation instances
from 48 workloads. Six workloads received the preregistered three complete
repeats. No attempt was replaced or retried.

## Correctness result

```text
correctness_gate = pass
score clustered Top-5 canonical rows = 60/60
stability clustered Top-5 canonical rows = 60/60
Nt clustered Top-5 canonical rows = 60/60
all three declared rankings = 60/60
full-output diagnostic equality = 60/60
technical failures = 0
fallbacks = 0
timeouts = 0
OOMs = 0
```

This fresh result promotes the correctness evidence for the versioned
`all-ranked-top5-canonical-row-v2` contract. Arm H executed a GASAL2 score
prepass followed by CPU SSW canonical traceback only for selected attempts; it
did not execute a complete CPU authority run. The exact post-execution snapshot
file set matched its frozen manifest, and no Python bytecode cache was created.

Full-output equality is reported as a diagnostic. It does not silently expand
the preregistered clustered Top-5 contract.

## Remaining gate

```text
canonical-hybrid-v2 correctness = pass
canonical-hybrid-v2 performance = pending fixed A/H pilot
B3-v2 = pending_performance_pilot
Bioinformatics route = conditionally reopened, not submission-ready
```

The correctness-run timings are diagnostic only and cannot promote performance.
The next authorized step is to freeze and commit a separate A/H performance
pilot before execution. The original H/A speedup threshold remains `>=10x`; no
lower substitute threshold is permitted.

## Historical boundary

The historical records remain unchanged:

```text
gpu-traceback-v1 Phase 2 = verified_only_contract
sequential verified-v1 Phase 3 B3 = no_go
```

The old regression set remains regression-only. This decision neither rewrites
those results nor reports v1 candidate-only or sequential-verified timing as
canonical-hybrid-v2 speedup.

Evidence receipt SHA-256: `{sha256_bytes(json_bytes(receipt))}`.
"""
    return text.encode("utf-8")


def build_payloads(collector_commit: str) -> dict[Path, bytes]:
    runner = load_runner()
    rows = runner.read_plan("fresh-holdout")
    require(len(rows) == 120, "fresh holdout plan count drift")
    snapshot = validate_snapshot()
    require(snapshot["git_head"] == "c6355bbabbf5d7e281c85716bdcf83b18eb35bc1", "execution commit drift")
    stage_summary_path = STAGE_ROOT / "stage-summary.json"
    stage_summary = json.loads(stage_summary_path.read_text(encoding="utf-8"))
    require(stage_summary["stage_status"] == "complete_clean", "fresh holdout stage is not complete-clean")
    require(stage_summary["complete_representation"] is True, "fresh holdout representation is incomplete")
    for field in (
        "clustered_score_top5_equal",
        "clustered_stability_top5_equal",
        "clustered_nt_top5_equal",
        "all_three_top5_equal",
        "full_output_equal",
    ):
        require(stage_summary[field] == 60, f"fresh holdout {field} drift")
    require(stage_summary["technical_failures"] == 0, "fresh holdout technical failure")
    require(stage_summary["fallbacks"] == 0, "fresh holdout fallback")
    require(stage_summary["timeouts"] == 0 and stage_summary["ooms"] == 0, "fresh holdout timeout or OOM")
    require(not list(STAGE_ROOT.glob(".*.partial.*")), "fresh holdout contains a partial attempt")

    workloads = {row["workload_id"]: row for row in read_tsv(WORKLOAD_PATH)}
    grouped: dict[str, dict[str, tuple[dict[str, str], dict[str, object]]]] = {}
    for row in rows:
        receipt = runner.validate_attempt_receipt(STAGE_ROOT / row["attempt_id"], row)
        grouped.setdefault(row["validation_id"], {})[row["arm"]] = (row, receipt)
    require(len(grouped) == 60, "fresh holdout validation grouping drift")

    result_rows: list[dict[str, object]] = []
    authority_walls: list[float] = []
    hybrid_walls: list[float] = []
    for validation_id, attempts in sorted(grouped.items()):
        require(set(attempts) == {"A", "H"}, f"incomplete validation pair: {validation_id}")
        authority_row, authority = attempts["A"]
        hybrid_row, hybrid = attempts["H"]
        comparison = hybrid["comparison"]
        metrics = comparison["metrics"]
        telemetry = hybrid["telemetry_summary"]
        timings = telemetry["component_timings"]
        authority_execution = authority["execution"]
        hybrid_execution = hybrid["execution"]
        authority_walls.append(float(authority_execution["wall_seconds"]))
        hybrid_walls.append(float(hybrid_execution["wall_seconds"]))
        workload_id = validation_id.split("__", 1)[0]
        workload = workloads[workload_id]
        require(comparison["declared_contract_clean"] is True, f"declared mismatch: {validation_id}")
        require(comparison["command"][1] == "-B", f"comparator bytecode isolation drift: {validation_id}")
        require(comparison["explicit_environment"]["PYTHONDONTWRITEBYTECODE"] == "1", f"comparator environment drift: {validation_id}")
        result_rows.append(
            {
                "validation_id": validation_id,
                "workload_id": workload_id,
                "repeat_id": authority_row["repeat_id"],
                "query_id": authority_row["query_id"],
                "target_id": authority_row["target_id"],
                "query_stratum": workload["query_stratum"],
                "target_chromosome": workload["target_chromosome"],
                "gpu_physical_index": hybrid_row["gpu_physical_index"],
                "authority_attempt_id": authority_row["attempt_id"],
                "hybrid_attempt_id": hybrid_row["attempt_id"],
                "authority_output_rows": authority["output_rows"],
                "hybrid_output_rows": hybrid["output_rows"],
                "authority_output_sha256": authority["output_sha256"],
                "hybrid_output_sha256": hybrid["output_sha256"],
                "score_equal": metrics["clustered_score_top5_equal"],
                "stability_equal": metrics["clustered_stability_top5_equal"],
                "nt_equal": metrics["clustered_nt_top5_equal"],
                "all_three_equal": metrics["all_three_top5_equal"],
                "boundary_ties_equal": metrics["boundary_ties_equal"],
                "full_output_equal": int(metrics["full_missing_rows"] == 0 and metrics["full_extra_rows"] == 0),
                "full_missing_rows": metrics["full_missing_rows"],
                "full_extra_rows": metrics["full_extra_rows"],
                "declared_contract_clean": int(comparison["declared_contract_clean"]),
                "authority_wall_seconds": authority_execution["wall_seconds"],
                "hybrid_wall_seconds": hybrid_execution["wall_seconds"],
                "score_prepass_seconds": timings["fasim_gasal2_longtarget_score_select_seconds"],
                "cpu_traceback_replay_seconds": timings["fasim_gasal2_cpu_traceback_replay_seconds"],
                "cpu_traceback_align_seconds": timings["fasim_gasal2_cpu_traceback_align_seconds"],
                "triplex_convert_seconds": timings["fasim_gasal2_cpu_traceback_convert_seconds"],
                "attempt_rows": telemetry["attempt_rows"],
                "selected_attempts": telemetry["selected_attempts"],
                "cpu_traceback_calls": telemetry["cpu_traceback_calls"],
                "fallbacks": telemetry["fallbacks"],
                "authority_max_rss_kib": authority_execution["resources"]["max_rss_kib"],
                "hybrid_max_rss_kib": hybrid_execution["resources"]["max_rss_kib"],
                "gpu_measurement_status": hybrid_execution["resources"]["gpu_measurement_status"],
                "gpu_sample_count": hybrid_execution["resources"]["gpu_sample_count"],
                "gpu_memory_peak_mib": hybrid_execution["resources"]["gpu_memory_peak_mib"],
                "authority_receipt_sha256": sha256_file(STAGE_ROOT / authority_row["attempt_id"] / "attempt-complete.json"),
                "hybrid_receipt_sha256": sha256_file(STAGE_ROOT / hybrid_row["attempt_id"] / "attempt-complete.json"),
            }
        )
    results_payload = tsv_bytes(RESULT_FIELDS, result_rows)

    artifact_rows: list[dict[str, object]] = []
    for path in sorted(STAGE_ROOT.rglob("*")):
        require(not path.is_symlink(), f"raw holdout artifact is a symlink: {path}")
        if not path.is_file():
            continue
        stage_relative = path.relative_to(STAGE_ROOT).as_posix()
        artifact_rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "role": artifact_role(stage_relative),
                "formal_source_data": 1,
            }
        )
    artifacts_payload = tsv_bytes(ARTIFACT_FIELDS, artifact_rows)
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    plan_receipt = json.loads(PLAN_RECEIPT_PATH.read_text(encoding="utf-8"))
    receipt = {
        "schema_version": 1,
        "stage": "fresh-holdout",
        "result_status": "correctness_promotion_pass",
        "declared_contract": "all-ranked-top5-canonical-row-v2",
        "workload_count": 48,
        "repeat_subset_workload_count": 6,
        "validation_count": 60,
        "attempt_count": 120,
        "arm_counts": {"A": 60, "H": 60},
        "query_count": 12,
        "query_stratum_counts": {stratum: 4 for stratum in ("short_500_800", "medium_801_1600", "long_1601_2812")},
        "target_count": 4,
        "target_chromosome_counts": {"chr21": 2, "chr22": 2},
        "score_clustered_top5_equal": 60,
        "stability_clustered_top5_equal": 60,
        "nt_clustered_top5_equal": 60,
        "all_three_clustered_top5_equal": 60,
        "full_output_equal_diagnostic": 60,
        "full_output_contract_promoted": False,
        "declared_contract_mismatches": 0,
        "technical_failures": 0,
        "fallbacks": 0,
        "timeouts": 0,
        "ooms": 0,
        "score_prepass_attempts": sum(int(row["attempt_rows"]) for row in result_rows),
        "selected_attempts": sum(int(row["selected_attempts"]) for row in result_rows),
        "cpu_traceback_calls": sum(int(row["cpu_traceback_calls"]) for row in result_rows),
        "selected_cpu_traceback_count_equal": all(row["selected_attempts"] == row["cpu_traceback_calls"] for row in result_rows),
        "complete_cpu_authority_inside_hybrid": False,
        "fresh_holdout_selection_input_only": selection["prohibited_selection_input_used"] is False,
        "prior_pilot_outcomes_read_for_selection": selection["prior_pilot_outcomes_read"],
        "regression_evidence_used_for_promotion": False,
        "correctness_promotion_passed": True,
        "performance_promotion_assessed": False,
        "b3_v2_status": "pending_performance_pilot",
        "b3_speedup_threshold": 10.0,
        "b3_speedup_threshold_changed": False,
        "correctness_timing_claim_role": "diagnostic_only_not_performance_promotion",
        "authority_wall_seconds_diagnostic": {
            "minimum": min(authority_walls),
            "median": statistics.median(authority_walls),
            "maximum": max(authority_walls),
            "sum": sum(authority_walls),
        },
        "hybrid_wall_seconds_diagnostic": {
            "minimum": min(hybrid_walls),
            "median": statistics.median(hybrid_walls),
            "maximum": max(hybrid_walls),
            "sum": sum(hybrid_walls),
        },
        "snapshot_file_set_exact_after_execution": True,
        "snapshot_python_bytecode_cache_count": 0,
        "retry_policy": "none",
        "replacement_retry_used": False,
        "plan_sha256": sha256_file(PLAN_PATH),
        "plan_receipt_sha256": sha256_file(PLAN_RECEIPT_PATH),
        "selection_sha256": sha256_file(SELECTION_PATH),
        "runtime_receipt_sha256": plan_receipt["runtime_receipt_sha256"],
        "runtime_epoch": plan_receipt["runtime_epoch"],
        "runtime_revision": plan_receipt["runtime_revision"],
        "runtime_commit": plan_receipt["runtime_commit"],
        "runner_commit": plan_receipt["runner_commit"],
        "execution_commit": snapshot["git_head"],
        "stage_summary_sha256": sha256_file(stage_summary_path),
        "results_sha256": sha256_bytes(results_payload),
        "raw_artifact_inventory_sha256": sha256_bytes(artifacts_payload),
        "raw_artifact_count": len(artifact_rows),
        "raw_artifact_bytes": sum(int(row["size_bytes"]) for row in artifact_rows),
        "collector_commit": collector_commit,
        "collector_sha256": sha256_file(Path(__file__).resolve()),
        "historical_phase2_decision": "verified_only_contract",
        "historical_phase3_sequential_v1_b3": "no_go",
        "historical_decisions_rewritten": False,
        "next_allowed_step": "freeze_fixed_ah_performance_pilot",
        "completed_utc": stage_summary["updated_utc"],
    }
    receipt_payload = json_bytes(receipt)
    decision_payload = decision_bytes(receipt)
    checksums = (
        f"{sha256_bytes(results_payload)}  {RESULTS_PATH.name}\n"
        f"{sha256_bytes(artifacts_payload)}  {ARTIFACTS_PATH.name}\n"
        f"{sha256_bytes(receipt_payload)}  {RECEIPT_PATH.name}\n"
        f"{sha256_bytes(decision_payload)}  {DECISION_PATH.name}\n"
    ).encode("ascii")
    return {
        RESULTS_PATH: results_payload,
        ARTIFACTS_PATH: artifacts_payload,
        RECEIPT_PATH: receipt_payload,
        DECISION_PATH: decision_payload,
        CHECKSUM_PATH: checksums,
    }


def write_payloads(payloads: dict[Path, bytes]) -> None:
    for path, payload in payloads.items():
        atomic_new(path, payload)


def check_payloads() -> dict[str, object]:
    require(RECEIPT_PATH.is_file() and not RECEIPT_PATH.is_symlink(), "holdout receipt is missing")
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    collector_commit = str(receipt["collector_commit"])
    require(git_output("merge-base", "--is-ancestor", collector_commit, "HEAD") == "", "collector commit is not an ancestor")
    frozen_collector = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{collector_commit}:{Path(__file__).resolve().relative_to(ROOT).as_posix()}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(frozen_collector.returncode == 0, "holdout collector is not committed at frozen identity")
    require(sha256_bytes(frozen_collector.stdout) == receipt["collector_sha256"], "frozen collector identity drift")
    require(sha256_file(Path(__file__).resolve()) == receipt["collector_sha256"], "current collector drift")
    expected = build_payloads(collector_commit)
    for path, payload in expected.items():
        require(path.is_file() and not path.is_symlink(), f"missing holdout evidence: {path}")
        require(path.read_bytes() == payload, f"holdout evidence drift: {path}")
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--preview", action="store_true")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if args.write:
            collector_commit = require_clean_checkout()
            payloads = build_payloads(collector_commit)
            write_payloads(payloads)
            result = json.loads(payloads[RECEIPT_PATH].decode("utf-8"))
        elif args.check:
            result = check_payloads()
        else:
            result = json.loads(build_payloads(git_output("rev-parse", "HEAD"))[RECEIPT_PATH].decode("utf-8"))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (CollectionError, OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"canonical-hybrid-v2 fresh holdout collection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
