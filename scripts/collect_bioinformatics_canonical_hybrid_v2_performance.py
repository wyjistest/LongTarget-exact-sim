#!/usr/bin/env python3
"""Validate and freeze canonical-hybrid-v2 A/H performance pilot evidence."""

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
STAGE_ROOT = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/performance-pilot"
PLAN_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_plan.tsv"
PLAN_RECEIPT_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_plan_receipt.json"
SELECTION_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_selection.json"
WORKLOAD_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_workloads.tsv"
RESULTS_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_results.tsv"
ARTIFACTS_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_artifacts.tsv"
RECEIPT_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_receipt.json"
DECISION_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance_decision.md"
CHECKSUM_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_performance.sha256"
RESULT_FIELDS = (
    "validation_id",
    "workload_id",
    "repeat_id",
    "query_id",
    "target_id",
    "query_stratum",
    "target_chromosome",
    "logical_worker",
    "gpu_physical_index",
    "authority_output_rows",
    "hybrid_output_rows",
    "authority_output_sha256",
    "hybrid_output_sha256",
    "declared_contract_clean",
    "full_output_equal",
    "authority_wall_seconds",
    "hybrid_wall_seconds",
    "paired_authority_over_hybrid",
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
    require(not path.exists(), f"refusing to replace frozen performance evidence: {path}")
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
    require(not status, f"performance evidence freeze requires a clean checkout: {status}")
    return git_output("rev-parse", "HEAD")


def load_runner():
    spec = importlib.util.spec_from_file_location("canonical_hybrid_v2_performance_collector_runner", RUNNER_PATH)
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
    require(snapshot_path.is_file() and not snapshot_path.is_symlink(), "performance snapshot is missing")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    require(snapshot.get("schema_version") == 1 and snapshot.get("stage") == "performance-pilot", "snapshot identity drift")
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
    require(not any("__pycache__" in path.parts for path in snapshot_root.rglob("*")), "snapshot bytecode cache detected")
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
    primary = float(receipt["primary_aggregate_speedup"])
    secondary = float(receipt["secondary_projected_two_worker_speedup"])
    slowdown = float(receipt["hybrid_slowdown_vs_authority"])
    text = f"""# Canonical-Hybrid-v2 Performance Decision

The fixed A/H pilot completed all 18 preregistered validation instances from
six input-only workloads with three complete repeats. All score-, stability-,
and Nt-ranked clustered Top-5 canonical rows matched, full-output diagnostics
were 18/18, and there were no technical failures, fallbacks, timeouts, OOMs,
or replacement retries.

## Performance result

```text
performance_gate = no_go
primary aggregate A/H speedup = {primary:.6f}x
secondary projected two-worker A/H speedup = {secondary:.6f}x
required speedup = 10.000000x
hybrid slowdown versus authority = {slowdown:.6f}x
```

The primary metric is the preregistered sum of isolated authority wall seconds
divided by the sum of isolated hybrid wall seconds. The secondary metric uses
the maximum fixed-worker sum for each arm under the frozen modulo-2 mapping.
Both had to reach `>=10x`; neither did. The threshold was not changed and no
lower substitute threshold was introduced.

## Rescue decision

```text
canonical-hybrid-v2 correctness = pass
canonical-hybrid-v2 performance = no_go
B3-v2 = no_go
large B3-v2 application run authorized = false
canonical-hybrid-v2 rescue track = closed
submission route = retain CSBJ fallback
```

Canonical-hybrid-v2 remains valid evidence that GPU score selection plus
selected CPU canonical traceback can preserve the frozen correctness contract.
It is not a safe acceleration result on the fixed application-shaped pilot.
No v1 candidate-only timing, sequential verified timing, correctness-run timing,
or lower threshold is substituted for this result.

## Historical boundary

The historical records remain unchanged:

```text
gpu-traceback-v1 Phase 2 = verified_only_contract
sequential verified-v1 Phase 3 B3 = no_go
```

The versioned v2 correctness pass and performance no-go are additive evidence;
they do not rewrite either historical decision.

Evidence receipt SHA-256: `{sha256_bytes(json_bytes(receipt))}`.
"""
    return text.encode("utf-8")


def build_payloads(collector_commit: str) -> dict[Path, bytes]:
    runner = load_runner()
    rows = runner.read_plan("performance-pilot")
    require(len(rows) == 36, "performance plan count drift")
    snapshot = validate_snapshot()
    require(snapshot["git_head"] == "b37d26aeafdaf3bba2deda0b88b3b79213a1c94c", "performance execution commit drift")
    stage_summary_path = STAGE_ROOT / "stage-summary.json"
    stage_summary = json.loads(stage_summary_path.read_text(encoding="utf-8"))
    require(stage_summary["stage_status"] == "complete_clean", "performance stage is not complete-clean")
    require(stage_summary["complete_representation"] is True, "performance representation is incomplete")
    for field in (
        "clustered_score_top5_equal",
        "clustered_stability_top5_equal",
        "clustered_nt_top5_equal",
        "all_three_top5_equal",
        "full_output_equal",
    ):
        require(stage_summary[field] == 18, f"performance {field} drift")
    require(stage_summary["technical_failures"] == 0, "performance technical failure")
    require(stage_summary["fallbacks"] == 0, "performance fallback")
    require(stage_summary["timeouts"] == 0 and stage_summary["ooms"] == 0, "performance timeout or OOM")
    require(not list(STAGE_ROOT.glob(".*.partial.*")), "performance stage contains a partial attempt")

    workloads = {row["workload_id"]: row for row in read_tsv(WORKLOAD_PATH)}
    grouped: dict[str, dict[str, tuple[dict[str, str], dict[str, object]]]] = {}
    for row in rows:
        receipt = runner.validate_attempt_receipt(STAGE_ROOT / row["attempt_id"], row)
        grouped.setdefault(row["validation_id"], {})[row["arm"]] = (row, receipt)
    require(len(grouped) == 18, "performance validation grouping drift")

    result_rows: list[dict[str, object]] = []
    authority_walls: list[float] = []
    hybrid_walls: list[float] = []
    worker_totals = {0: {"authority": 0.0, "hybrid": 0.0}, 1: {"authority": 0.0, "hybrid": 0.0}}
    component_totals = {"score_prepass": 0.0, "cpu_traceback_replay": 0.0, "cpu_traceback_align": 0.0, "triplex_convert": 0.0}
    for validation_id, attempts in sorted(grouped.items()):
        require(set(attempts) == {"A", "H"}, f"incomplete performance pair: {validation_id}")
        authority_row, authority = attempts["A"]
        hybrid_row, hybrid = attempts["H"]
        comparison = hybrid["comparison"]
        metrics = comparison["metrics"]
        telemetry = hybrid["telemetry_summary"]
        timings = telemetry["component_timings"]
        authority_execution = authority["execution"]
        hybrid_execution = hybrid["execution"]
        authority_wall = float(authority_execution["wall_seconds"])
        hybrid_wall = float(hybrid_execution["wall_seconds"])
        worker = int(hybrid_row["gpu_physical_index"])
        authority_walls.append(authority_wall)
        hybrid_walls.append(hybrid_wall)
        worker_totals[worker]["authority"] += authority_wall
        worker_totals[worker]["hybrid"] += hybrid_wall
        component_totals["score_prepass"] += float(timings["fasim_gasal2_longtarget_score_select_seconds"])
        component_totals["cpu_traceback_replay"] += float(timings["fasim_gasal2_cpu_traceback_replay_seconds"])
        component_totals["cpu_traceback_align"] += float(timings["fasim_gasal2_cpu_traceback_align_seconds"])
        component_totals["triplex_convert"] += float(timings["fasim_gasal2_cpu_traceback_convert_seconds"])
        workload_id = validation_id.split("__", 1)[0]
        workload = workloads[workload_id]
        require(comparison["declared_contract_clean"] is True, f"performance declared mismatch: {validation_id}")
        require(comparison["command"][1] == "-B", f"performance comparator isolation drift: {validation_id}")
        result_rows.append(
            {
                "validation_id": validation_id,
                "workload_id": workload_id,
                "repeat_id": authority_row["repeat_id"],
                "query_id": authority_row["query_id"],
                "target_id": authority_row["target_id"],
                "query_stratum": workload["query_stratum"],
                "target_chromosome": workload["target_chromosome"],
                "logical_worker": worker,
                "gpu_physical_index": hybrid_row["gpu_physical_index"],
                "authority_output_rows": authority["output_rows"],
                "hybrid_output_rows": hybrid["output_rows"],
                "authority_output_sha256": authority["output_sha256"],
                "hybrid_output_sha256": hybrid["output_sha256"],
                "declared_contract_clean": int(comparison["declared_contract_clean"]),
                "full_output_equal": int(metrics["full_missing_rows"] == 0 and metrics["full_extra_rows"] == 0),
                "authority_wall_seconds": authority_wall,
                "hybrid_wall_seconds": hybrid_wall,
                "paired_authority_over_hybrid": authority_wall / hybrid_wall,
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

    authority_total = sum(authority_walls)
    hybrid_total = sum(hybrid_walls)
    primary_speedup = authority_total / hybrid_total
    authority_makespan = max(values["authority"] for values in worker_totals.values())
    hybrid_makespan = max(values["hybrid"] for values in worker_totals.values())
    secondary_speedup = authority_makespan / hybrid_makespan
    plan_receipt = json.loads(PLAN_RECEIPT_PATH.read_text(encoding="utf-8"))
    threshold = float(plan_receipt["performance_speedup_threshold"])
    correctness_clean = all(bool(row["declared_contract_clean"]) for row in result_rows)
    gate_pass = correctness_clean and primary_speedup >= threshold and secondary_speedup >= threshold

    artifact_rows: list[dict[str, object]] = []
    for path in sorted(STAGE_ROOT.rglob("*")):
        require(not path.is_symlink(), f"raw performance artifact is a symlink: {path}")
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
    receipt = {
        "schema_version": 1,
        "stage": "performance-pilot",
        "result_status": "performance_promotion_pass" if gate_pass else "performance_promotion_no_go",
        "performance_gate_passed": gate_pass,
        "performance_gate_rule": plan_receipt["performance_gate_rule"],
        "performance_speedup_threshold": threshold,
        "performance_speedup_threshold_changed": False,
        "lower_substitute_threshold_introduced": False,
        "workload_count": 6,
        "validation_count": 18,
        "attempt_count": 36,
        "arm_counts": {"A": 18, "H": 18},
        "score_clustered_top5_equal": 18,
        "stability_clustered_top5_equal": 18,
        "nt_clustered_top5_equal": 18,
        "all_three_clustered_top5_equal": 18,
        "full_output_equal_diagnostic": 18,
        "declared_contract_mismatches": 0,
        "technical_failures": 0,
        "fallbacks": 0,
        "timeouts": 0,
        "ooms": 0,
        "authority_wall_seconds": {
            "minimum": min(authority_walls),
            "median": statistics.median(authority_walls),
            "maximum": max(authority_walls),
            "sum": authority_total,
        },
        "hybrid_wall_seconds": {
            "minimum": min(hybrid_walls),
            "median": statistics.median(hybrid_walls),
            "maximum": max(hybrid_walls),
            "sum": hybrid_total,
        },
        "primary_aggregate_speedup": primary_speedup,
        "primary_gate_passed": primary_speedup >= threshold,
        "logical_worker_totals": {str(worker): values for worker, values in worker_totals.items()},
        "authority_projected_two_worker_makespan_seconds": authority_makespan,
        "hybrid_projected_two_worker_makespan_seconds": hybrid_makespan,
        "secondary_projected_two_worker_speedup": secondary_speedup,
        "secondary_gate_passed": secondary_speedup >= threshold,
        "hybrid_slowdown_vs_authority": hybrid_total / authority_total,
        "hybrid_component_seconds": component_totals,
        "score_prepass_attempts": sum(int(row["attempt_rows"]) for row in result_rows),
        "selected_attempts": sum(int(row["selected_attempts"]) for row in result_rows),
        "cpu_traceback_calls": sum(int(row["cpu_traceback_calls"]) for row in result_rows),
        "selected_cpu_traceback_count_equal": all(row["selected_attempts"] == row["cpu_traceback_calls"] for row in result_rows),
        "complete_cpu_authority_inside_hybrid": False,
        "selection_input_only": selection["prohibited_selection_input_used"] is False,
        "correctness_results_or_timings_read_for_selection": selection["correctness_results_or_timings_read"],
        "snapshot_file_set_exact_after_execution": True,
        "snapshot_python_bytecode_cache_count": 0,
        "retry_policy": "none",
        "replacement_retry_used": False,
        "correctness_promotion_status": "pass",
        "b3_v2_status": "pass" if gate_pass else "no_go",
        "large_b3_v2_application_run_authorized": gate_pass,
        "rescue_track_status": "open_for_formal_application" if gate_pass else "closed_performance_no_go",
        "submission_route": "Bioinformatics_conditionally_reopened" if gate_pass else "retain_CSBJ_fallback",
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
        "next_allowed_step": "authorize_formal_b3_v2_application" if gate_pass else "close_rescue_track_retain_csbj",
        "completed_utc": stage_summary["updated_utc"],
    }
    require(receipt["result_status"] == "performance_promotion_no_go", "unexpected performance gate result")
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
    require(RECEIPT_PATH.is_file() and not RECEIPT_PATH.is_symlink(), "performance receipt is missing")
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    collector_commit = str(receipt["collector_commit"])
    require(git_output("merge-base", "--is-ancestor", collector_commit, "HEAD") == "", "collector commit is not an ancestor")
    frozen_collector = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{collector_commit}:{Path(__file__).resolve().relative_to(ROOT).as_posix()}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(frozen_collector.returncode == 0, "performance collector is not committed at frozen identity")
    require(sha256_bytes(frozen_collector.stdout) == receipt["collector_sha256"], "frozen collector identity drift")
    require(sha256_file(Path(__file__).resolve()) == receipt["collector_sha256"], "current collector drift")
    expected = build_payloads(collector_commit)
    for path, payload in expected.items():
        require(path.is_file() and not path.is_symlink(), f"missing performance evidence: {path}")
        require(path.read_bytes() == payload, f"performance evidence drift: {path}")
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
        print(f"canonical-hybrid-v2 performance collection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
