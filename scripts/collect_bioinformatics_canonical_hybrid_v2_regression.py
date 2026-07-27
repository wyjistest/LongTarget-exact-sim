#!/usr/bin/env python3
"""Validate and freeze canonical-hybrid-v2 Phase 2 regression evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import statistics
import sys
import tempfile
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "reproduce/bioinformatics/run_canonical_hybrid_v2.py"
STAGE_ROOT = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/regression"
RESULTS_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_regression_results.tsv"
ARTIFACTS_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_regression_artifacts.tsv"
RECEIPT_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_regression_receipt.json"
CHECKSUM_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_regression.sha256"
FROZEN_COLLECTOR_SHA256 = "e25b8e6137bc295f7bf1f8295083a3600a146ea0b7ec9761d22da5a145c435ae"
RESULT_FIELDS = (
    "attempt_id",
    "validation_id",
    "query_id",
    "target_id",
    "repeat_id",
    "gpu_physical_index",
    "returncode",
    "timed_out",
    "oom_detected",
    "fallbacks",
    "attempt_rows",
    "selected_attempts",
    "cpu_traceback_calls",
    "final_row_mappings",
    "output_rows",
    "output_sha256",
    "score_equal",
    "stability_equal",
    "nt_equal",
    "all_three_equal",
    "boundary_ties_equal",
    "full_output_equal",
    "full_missing_rows",
    "full_extra_rows",
    "declared_contract_clean",
    "score_prepass_seconds",
    "cpu_traceback_replay_seconds",
    "cpu_traceback_align_seconds",
    "triplex_convert_seconds",
    "total_wall_seconds",
    "max_rss_kib",
    "gpu_measurement_status",
    "gpu_sample_count",
    "gpu_memory_peak_mib",
    "selection_reasons_json",
    "cpu_emit_reasons_json",
    "final_statuses_json",
    "artifact_count",
    "artifact_manifest_sha256",
    "attempt_receipt_sha256",
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


def compact_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def tsv_bytes(fieldnames: Sequence[str], rows: list[dict[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, delimiter="\t", lineterminator="\n", extrasaction="raise"
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def atomic_new(path: Path, payload: bytes) -> None:
    require(not path.exists(), f"refusing to replace frozen regression evidence: {path}")
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


def load_runner():
    snapshot = STAGE_ROOT / "execution-snapshot"
    frozen_runner = snapshot / RUNNER_PATH.name
    spec = importlib.util.spec_from_file_location("canonical_hybrid_v2_regression_collector_runner", RUNNER_PATH)
    require(spec is not None and spec.loader is not None, "cannot load canonical hybrid runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    module.RUNNER_PATH = frozen_runner
    module.RUNTIME_RECEIPT_PATH = snapshot / "canonical_hybrid_v2_runtime.json"
    module.CANONICAL_ARTIFACT_ROOT = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2"
    module.PLAN_PATHS = {
        "regression": snapshot / "canonical_hybrid_v2_regression_plan.tsv",
    }
    module.PLAN_CHECKSUM_PATHS = {
        "regression": snapshot / "canonical_hybrid_v2_regression_plan.sha256",
    }

    def read_frozen_runtime_receipt(path: Path = module.RUNTIME_RECEIPT_PATH):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        identities = {
            "runner_sha256": frozen_runner,
            "telemetry_validator_sha256": snapshot / "canonical_hybrid_v2_telemetry.py",
            "telemetry_schema_sha256": snapshot / "canonical_hybrid_v2_attempt_telemetry.schema.json",
            "comparator_sha256": snapshot / "compare_fasim_segmented_contract.py",
        }
        for field, source in identities.items():
            require(receipt.get(field) == sha256_file(source), f"frozen runtime {field} drift")
        for relative, expected in receipt["comparator_dependency_sha256"].items():
            require(expected == sha256_file(snapshot / Path(relative).name), f"frozen comparator dependency drift: {relative}")
        return receipt

    module.read_runtime_receipt = read_frozen_runtime_receipt
    return module


def artifact_role(relative: str) -> str:
    if relative.startswith("execution-snapshot/"):
        return "execution_snapshot"
    if relative == "stage-summary.json":
        return "stage_summary"
    if relative.endswith("attempt-telemetry.tsv"):
        return "per_attempt_telemetry"
    if "/output/" in relative:
        return "hybrid_output"
    if relative.endswith("authority-reference.tfosorted"):
        return "frozen_authority_copy"
    if relative.endswith("comparison.json") or relative.endswith("comparison-details.tsv"):
        return "comparison"
    if relative.endswith("attempt-complete.json"):
        return "attempt_receipt"
    return "supporting_raw_artifact"


def build_payloads() -> tuple[bytes, bytes, bytes, bytes]:
    runner = load_runner()
    rows = runner.read_plan("regression")
    require(STAGE_ROOT.is_dir() and not STAGE_ROOT.is_symlink(), "regression artifact root is missing")
    snapshot_root = STAGE_ROOT / "execution-snapshot"
    snapshot_path = snapshot_root / "snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    require(snapshot["schema_version"] == 1 and snapshot["stage"] == "regression", "snapshot identity drift")
    require(snapshot["plan_sha256"] == sha256_file(runner.PLAN_PATHS["regression"]), "snapshot plan drift")
    require(
        snapshot["runtime_receipt_sha256"] == sha256_file(runner.RUNTIME_RECEIPT_PATH),
        "snapshot runtime receipt drift",
    )
    observed_snapshot_files: set[str] = set()
    for path in sorted(snapshot_root.rglob("*")):
        require(not path.is_symlink(), f"snapshot artifact is a symlink: {path}")
        if path.is_file():
            observed_snapshot_files.add(path.relative_to(snapshot_root).as_posix())
    expected_snapshot_files = set(snapshot["files"]) | {"snapshot.json"}
    missing_snapshot_files = expected_snapshot_files - observed_snapshot_files
    extra_snapshot_files = observed_snapshot_files - expected_snapshot_files
    require(not missing_snapshot_files, "snapshot is missing frozen files")
    allowed_bytecode_cache = {
        "__pycache__/compare_fasim_lite_offline_cluster_topk.cpython-311.pyc",
        "__pycache__/fasim_tfo_archive.cpython-311.pyc",
    }
    require(
        extra_snapshot_files == allowed_bytecode_cache,
        f"unexpected post-freeze snapshot files: {sorted(extra_snapshot_files)}",
    )
    for relative, identity in snapshot["files"].items():
        path = snapshot_root / relative
        require(path.stat().st_size == identity["size_bytes"], f"snapshot size drift: {relative}")
        require(sha256_file(path) == identity["sha256"], f"snapshot digest drift: {relative}")
    runtime = runner.read_runtime_receipt()
    snapshot_hybrid = snapshot_root / snapshot["tool_names"]["hybrid_binary"]
    require(sha256_file(snapshot_hybrid) == runtime["hybrid_binary_sha256"], "snapshot hybrid drift")
    stage_summary_path = STAGE_ROOT / "stage-summary.json"
    stage_summary = json.loads(stage_summary_path.read_text(encoding="utf-8"))
    require(stage_summary["stage_status"] == "complete_clean", "regression stage is not complete-clean")
    require(stage_summary["complete_representation"] is True, "regression representation is incomplete")
    require(stage_summary["planned_attempts"] == 36, "regression attempt count drift")
    require(stage_summary["declared_contract_mismatches"] == 0, "declared regression mismatch")
    require(stage_summary["technical_failures"] == 0, "regression technical failure")
    require(stage_summary["fallbacks"] == 0, "regression fallback")
    require(stage_summary["timeouts"] == 0 and stage_summary["ooms"] == 0, "regression timeout or OOM")
    require(not list(STAGE_ROOT.glob(".*.partial.*")), "regression contains a partial attempt")

    result_rows: list[dict[str, object]] = []
    receipts: list[dict[str, object]] = []
    for row in rows:
        attempt_root = STAGE_ROOT / row["attempt_id"]
        receipt = runner.validate_attempt_receipt(attempt_root, row)
        receipts.append(receipt)
        telemetry = receipt["telemetry_summary"]
        comparison = receipt["comparison"]
        metrics = comparison["metrics"]
        execution = receipt["execution"]
        resources = execution["resources"]
        timings = telemetry["component_timings"]
        result_rows.append(
            {
                "attempt_id": row["attempt_id"],
                "validation_id": row["validation_id"],
                "query_id": row["query_id"],
                "target_id": row["target_id"],
                "repeat_id": row["repeat_id"],
                "gpu_physical_index": row["gpu_physical_index"],
                "returncode": execution["returncode"],
                "timed_out": int(execution["timed_out"]),
                "oom_detected": int(execution["oom_detected"]),
                "fallbacks": telemetry["fallbacks"],
                "attempt_rows": telemetry["attempt_rows"],
                "selected_attempts": telemetry["selected_attempts"],
                "cpu_traceback_calls": telemetry["cpu_traceback_calls"],
                "final_row_mappings": telemetry["final_row_mappings"],
                "output_rows": receipt["output_rows"],
                "output_sha256": receipt["output_sha256"],
                "score_equal": metrics["clustered_score_top5_equal"],
                "stability_equal": metrics["clustered_stability_top5_equal"],
                "nt_equal": metrics["clustered_nt_top5_equal"],
                "all_three_equal": metrics["all_three_top5_equal"],
                "boundary_ties_equal": metrics["boundary_ties_equal"],
                "full_output_equal": int(
                    metrics["full_missing_rows"] == 0 and metrics["full_extra_rows"] == 0
                ),
                "full_missing_rows": metrics["full_missing_rows"],
                "full_extra_rows": metrics["full_extra_rows"],
                "declared_contract_clean": int(comparison["declared_contract_clean"]),
                "score_prepass_seconds": timings["fasim_gasal2_longtarget_score_select_seconds"],
                "cpu_traceback_replay_seconds": timings["fasim_gasal2_cpu_traceback_replay_seconds"],
                "cpu_traceback_align_seconds": timings["fasim_gasal2_cpu_traceback_align_seconds"],
                "triplex_convert_seconds": timings["fasim_gasal2_cpu_traceback_convert_seconds"],
                "total_wall_seconds": execution["wall_seconds"],
                "max_rss_kib": resources["max_rss_kib"],
                "gpu_measurement_status": resources["gpu_measurement_status"],
                "gpu_sample_count": resources["gpu_sample_count"],
                "gpu_memory_peak_mib": resources["gpu_memory_peak_mib"],
                "selection_reasons_json": compact_json(telemetry["selection_reasons"]),
                "cpu_emit_reasons_json": compact_json(telemetry["cpu_emit_reasons"]),
                "final_statuses_json": compact_json(telemetry["final_statuses"]),
                "artifact_count": receipt["artifact_count"],
                "artifact_manifest_sha256": receipt["artifact_manifest_sha256"],
                "attempt_receipt_sha256": sha256_file(attempt_root / "attempt-complete.json"),
            }
        )

    results_payload = tsv_bytes(RESULT_FIELDS, result_rows)
    artifact_rows: list[dict[str, object]] = []
    for path in sorted(STAGE_ROOT.rglob("*")):
        require(not path.is_symlink(), f"raw regression artifact is a symlink: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        stage_relative = path.relative_to(STAGE_ROOT).as_posix()
        artifact_rows.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "role": artifact_role(stage_relative),
                "formal_source_data": 0,
            }
        )
    artifacts_payload = tsv_bytes(ARTIFACT_FIELDS, artifact_rows)

    full_mismatches = [
        row
        for row in result_rows
        if not bool(row["full_output_equal"])
    ]
    wall_seconds = [float(row["total_wall_seconds"]) for row in result_rows]
    receipt_payload = {
        "schema_version": 1,
        "stage": "regression",
        "result_status": "regression_pass_not_promotion",
        "declared_contract": "all-ranked-top5-canonical-row-v2",
        "attempt_count": len(result_rows),
        "score_clustered_top5_equal": sum(int(row["score_equal"]) for row in result_rows),
        "stability_clustered_top5_equal": sum(int(row["stability_equal"]) for row in result_rows),
        "nt_clustered_top5_equal": sum(int(row["nt_equal"]) for row in result_rows),
        "all_three_clustered_top5_equal": sum(int(row["all_three_equal"]) for row in result_rows),
        "declared_contract_mismatches": sum(
            not bool(row["declared_contract_clean"]) for row in result_rows
        ),
        "technical_failures": 0,
        "fallbacks": sum(int(row["fallbacks"]) for row in result_rows),
        "timeouts": sum(int(row["timed_out"]) for row in result_rows),
        "ooms": sum(int(row["oom_detected"]) for row in result_rows),
        "score_prepass_attempts": sum(int(row["attempt_rows"]) for row in result_rows),
        "selected_attempts": sum(int(row["selected_attempts"]) for row in result_rows),
        "cpu_traceback_calls": sum(int(row["cpu_traceback_calls"]) for row in result_rows),
        "selected_cpu_traceback_count_equal": all(
            row["selected_attempts"] == row["cpu_traceback_calls"] for row in result_rows
        ),
        "complete_cpu_authority_inside_hybrid": False,
        "full_output_equal": sum(int(row["full_output_equal"]) for row in result_rows),
        "full_output_contract_claimed": False,
        "full_output_mismatches": [
            {
                "attempt_id": row["attempt_id"],
                "validation_id": row["validation_id"],
                "baseline_rows": next(
                    receipt["comparison"]["metrics"]["baseline_rows"]
                    for receipt in receipts
                    if receipt["attempt_id"] == row["attempt_id"]
                ),
                "hybrid_rows": row["output_rows"],
                "missing_rows": row["full_missing_rows"],
                "extra_rows": row["full_extra_rows"],
                "declared_contract_clean": bool(row["declared_contract_clean"]),
            }
            for row in full_mismatches
        ],
        "wall_seconds_diagnostic_only": {
            "minimum": min(wall_seconds),
            "median": statistics.median(wall_seconds),
            "maximum": max(wall_seconds),
            "sum": sum(wall_seconds),
        },
        "resource_measurements_claim_role": "diagnostic_only_not_performance_promotion",
        "snapshot_frozen_files_intact": True,
        "snapshot_file_set_exact_after_execution": False,
        "snapshot_postfreeze_extra_file_class": "python_bytecode_cache_only",
        "snapshot_postfreeze_extra_files": [
            {
                "path": relative,
                "size_bytes": (snapshot_root / relative).stat().st_size,
                "sha256": sha256_file(snapshot_root / relative),
            }
            for relative in sorted(extra_snapshot_files)
        ],
        "snapshot_cache_scientific_contract_impact": "none",
        "snapshot_cache_future_runner_hardening_required": True,
        "regression_is_promotion_evidence": False,
        "fresh_holdout_required_for_correctness_promotion": True,
        "performance_pilot_required_for_b3_v2": True,
        "b3_speedup_threshold_changed": False,
        "b3_speedup_threshold": 10.0,
        "next_allowed_step": "freeze_fresh_independent_holdout",
        "runtime_epoch": runtime["runtime_epoch"],
        "runtime_commit": runtime["runtime_commit"],
        "runner_commit": runtime["runner_commit"],
        "hybrid_binary_sha256": runtime["hybrid_binary_sha256"],
        "runtime_receipt_sha256": sha256_file(runner.RUNTIME_RECEIPT_PATH),
        "plan_sha256": sha256_file(runner.PLAN_PATHS["regression"]),
        "execution_commit": snapshot["git_head"],
        "stage_summary_sha256": sha256_file(stage_summary_path),
        "results_sha256": sha256_bytes(results_payload),
        "raw_artifact_inventory_sha256": sha256_bytes(artifacts_payload),
        "raw_artifact_count": len(artifact_rows),
        "raw_artifact_bytes": sum(int(row["size_bytes"]) for row in artifact_rows),
        "collector_sha256": FROZEN_COLLECTOR_SHA256,
        "historical_phase2_decision": "verified_only_contract",
        "historical_phase3_sequential_v1_b3": "no_go",
        "historical_decisions_rewritten": False,
        "completed_utc": stage_summary["updated_utc"],
    }
    require(receipt_payload["attempt_count"] == 36, "collected attempt count drift")
    require(receipt_payload["score_clustered_top5_equal"] == 36, "score regression mismatch")
    require(receipt_payload["stability_clustered_top5_equal"] == 36, "stability regression mismatch")
    require(receipt_payload["nt_clustered_top5_equal"] == 36, "Nt regression mismatch")
    require(receipt_payload["selected_cpu_traceback_count_equal"] is True, "CPU traceback count drift")
    require(receipt_payload["full_output_equal"] == 35, "full-output diagnostic count drift")
    receipt_bytes = json_bytes(receipt_payload)
    checksums = (
        f"{sha256_bytes(results_payload)}  {RESULTS_PATH.name}\n"
        f"{sha256_bytes(artifacts_payload)}  {ARTIFACTS_PATH.name}\n"
        f"{sha256_bytes(receipt_bytes)}  {RECEIPT_PATH.name}\n"
    ).encode("ascii")
    return results_payload, artifacts_payload, receipt_bytes, checksums


def write_payloads(payloads: tuple[bytes, bytes, bytes, bytes]) -> None:
    for path, payload in zip(
        (RESULTS_PATH, ARTIFACTS_PATH, RECEIPT_PATH, CHECKSUM_PATH), payloads
    ):
        atomic_new(path, payload)


def check_payloads(payloads: tuple[bytes, bytes, bytes, bytes]) -> None:
    for path, payload in zip(
        (RESULTS_PATH, ARTIFACTS_PATH, RECEIPT_PATH, CHECKSUM_PATH), payloads
    ):
        require(path.is_file() and not path.is_symlink(), f"missing frozen evidence: {path}")
        require(path.read_bytes() == payload, f"frozen evidence drift: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        payloads = build_payloads()
        write_payloads(payloads) if args.write else check_payloads(payloads)
        receipt = json.loads(payloads[2].decode("utf-8"))
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0
    except (CollectionError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"canonical-hybrid-v2 regression collection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
