#!/usr/bin/env python3
"""Adjudicate the preregistered Phase 4 repair after a fixed-budget stop."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from . import analyze_fresh_holdout as base
    from . import run_fresh_holdout_repair1 as repair
except ImportError:  # pragma: no cover
    import analyze_fresh_holdout as base  # type: ignore[no-redef]
    import run_fresh_holdout_repair1 as repair  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[2]
ACTUAL_RESOURCES_PATH = ROOT / "paper/biological_topk/fresh_holdout_actual_resources.json"
RUN_SUMMARY_PATH = repair.REPAIR_ARTIFACT_ROOT / "run-summary.json"


class BudgetStopError(RuntimeError):
    """Raised when retained evidence does not prove the frozen budget-stop branch."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BudgetStopError(message)


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("ascii")


def completed_attempts(
    attempts: Sequence[Mapping[str, str]],
) -> tuple[list[dict[str, Any]], list[Mapping[str, str]]]:
    receipts: list[dict[str, Any]] = []
    missing: list[Mapping[str, str]] = []
    for row in attempts:
        destination = ROOT / row["artifact_root"]
        if not (destination / "attempt-complete.json").is_file():
            missing.append(row)
            continue
        receipt = repair.base.validate_completed_attempt(destination, row)
        require(receipt["status"] == "success", "repair contains a terminal technical failure")
        require(receipt["comparison_started"] is False, "repair attempt started a comparison")
        receipts.append(receipt)
    return receipts, missing


def partial_analysis_payloads(
    manifest: Sequence[Mapping[str, str]],
    attempts: Sequence[Mapping[str, str]],
    plan: Mapping[str, Any],
) -> dict[Path, bytes]:
    original_validator = base.runner.validate_frozen_plan
    original_comparison_root = base.COMPARISON_ROOT
    try:
        base.runner.validate_frozen_plan = lambda: (
            manifest,
            attempts,
            plan,
            repair.load_inputs_for_analysis(manifest),
        )
        base.COMPARISON_ROOT = repair.REPAIR_ARTIFACT_ROOT / "offline-comparisons"
        return base.build()
    finally:
        base.runner.validate_frozen_plan = original_validator
        base.COMPARISON_ROOT = original_comparison_root


def build() -> dict[Path, bytes]:
    manifest, attempts, plan, _ = repair.validate_repair_plan()
    summary = repair.read_json(RUN_SUMMARY_PATH)
    receipts, missing = completed_attempts(attempts)
    partials = sorted(repair.REPAIR_ARTIFACT_ROOT.glob(".*.partial.*"))

    require(summary["planned_attempt_count"] == len(attempts) == 368, "planned attempt count drift")
    require(summary["status"] == "in_progress_or_interrupted", "run summary is not a stopped partial epoch")
    require(0 < len(receipts) < len(attempts), "budget stop requires a nonempty partial epoch")
    require(summary["terminal_attempt_count"] == len(receipts), "terminal attempt count drift")
    require(summary["successful_attempt_count"] == len(receipts), "successful attempt count drift")
    require(summary["technical_failure_count"] == 0, "repair stopped for a technical failure")
    require(summary["comparison_started"] is False, "comparison started before all attempts were terminal")
    require(
        summary["missing_attempt_ids"] == [row["attempt_id"] for row in missing],
        "run-summary missing-attempt order drift",
    )
    require(not partials, "partial attempt directories remain after runner termination")
    require(
        not (repair.REPAIR_ARTIFACT_ROOT / "offline-comparisons").exists(),
        "offline comparison exists in a partial epoch",
    )

    original_bytes = repair.directory_bytes(repair.ORIGINAL_ARTIFACT_ROOT)
    repair_bytes = repair.directory_bytes(repair.REPAIR_ARTIFACT_ROOT)
    retained_bytes = original_bytes + repair_bytes
    retained_within_quota = retained_bytes <= repair.frozen.MAX_STORAGE_BYTES
    next_g_reservation_pass = (
        retained_bytes + repair.TELEMETRY_RAW_RESERVATION_BYTES
        <= repair.frozen.MAX_STORAGE_BYTES
    )
    require(
        not retained_within_quota or not next_g_reservation_pass,
        "retained evidence does not prove a fixed storage-budget stop",
    )

    started = [datetime.fromisoformat(str(item["execution"]["started_utc"])) for item in receipts]
    finished = [datetime.fromisoformat(str(item["execution"]["finished_utc"])) for item in receipts]
    cpu_wall = sum(float(item["wall_seconds"]) for item in receipts if item["arm"] == "A")
    gpu_wall = sum(float(item["wall_seconds"]) for item in receipts if item["arm"] == "G")
    elapsed = (max(finished) - min(started)).total_seconds()
    stop_reason = (
        "retained_artifact_storage_exceeded_fixed_quota"
        if not retained_within_quota
        else "next_raw_g_telemetry_reservation_exceeded_fixed_quota"
    )

    payloads = partial_analysis_payloads(manifest, attempts, plan)
    require(
        not any(repair.REPAIR_ARTIFACT_ROOT in path.parents for path in payloads),
        "partial analysis attempted to create comparison artifacts",
    )
    actual_resources = {
        "schema_version": 1,
        "phase": 4,
        "status": "blocked_fixed_budget",
        "repair_epoch": 1,
        "repair_epoch_limit": 1,
        "planned_attempt_count": len(attempts),
        "terminal_attempt_count": len(receipts),
        "successful_attempt_count": len(receipts),
        "terminal_technical_failure_count": 0,
        "unstarted_attempt_count": len(missing),
        "completed_cpu_attempt_count": sum(item["arm"] == "A" for item in receipts),
        "completed_gpu_attempt_count": sum(item["arm"] == "G" for item in receipts),
        "actual_cpu_aggregate_wall_seconds": format(cpu_wall, ".17g"),
        "actual_gpu_aggregate_wall_seconds": format(gpu_wall, ".17g"),
        "actual_gpu_hours": format(gpu_wall / 3600, ".17g"),
        "actual_scheduled_elapsed_wall_seconds": format(elapsed, ".17g"),
        "superseded_epoch0_artifact_bytes": original_bytes,
        "repair_epoch_artifact_bytes_at_stop": repair_bytes,
        "actual_total_epoch_artifact_storage_bytes": retained_bytes,
        "next_raw_g_telemetry_reservation_bytes": repair.TELEMETRY_RAW_RESERVATION_BYTES,
        "max_formal_scheduled_wall_seconds": repair.frozen.MAX_ELAPSED_SECONDS,
        "max_gpu_hours": repair.frozen.MAX_GPU_HOURS,
        "max_artifact_storage_bytes": repair.frozen.MAX_STORAGE_BYTES,
        "scheduled_elapsed_gate_pass": elapsed <= repair.frozen.MAX_ELAPSED_SECONDS,
        "gpu_hours_gate_pass": gpu_wall / 3600 <= repair.frozen.MAX_GPU_HOURS,
        "retained_artifact_storage_within_quota": retained_within_quota,
        "next_g_storage_reservation_gate_pass": next_g_reservation_pass,
        "fixed_budget_gate_pass": False,
        "fixed_budget_stop_reason": stop_reason,
        "run_summary_path": RUN_SUMMARY_PATH.relative_to(ROOT).as_posix(),
        "run_summary_sha256": sha256_file(RUN_SUMMARY_PATH),
        "comparison_started": False,
        "original_evidence_included": True,
        "technical_telemetry_lossless_gzip": True,
        "resource_values_are_performance_claims": False,
        "later_phase_authorized": False,
    }
    actual_resources_bytes = canonical_json_bytes(actual_resources)
    payloads[ACTUAL_RESOURCES_PATH] = actual_resources_bytes

    receipt = json.loads(payloads[base.RECEIPT_PATH].decode("ascii"))
    receipt.update(
        {
            "status": "fixed_budget_stop_with_missing_attempts",
            "original_attempt_plan_sha256": sha256_file(repair.ORIGINAL_ATTEMPT_PLAN_PATH),
            "attempt_plan_sha256": sha256_file(repair.REPAIR_ATTEMPT_PLAN_PATH),
            "infrastructure_repair_epoch": 1,
            "infrastructure_repair_epoch_limit": 1,
            "repair_plan_sha256": sha256_file(repair.REPAIR_PLAN_PATH),
            "infrastructure_incident_sha256": sha256_file(repair.INCIDENT_PATH),
            "artifact_root": repair.REPAIR_ARTIFACT_ROOT.relative_to(ROOT).as_posix(),
            "superseded_epoch0_artifact_root": repair.ORIGINAL_ARTIFACT_ROOT.relative_to(ROOT).as_posix(),
            "superseded_epoch0_evidence_retained": True,
            "telemetry_storage_policy": "validated_then_lossless_gzip_mtime0",
            "actual_resources_path": ACTUAL_RESOURCES_PATH.relative_to(ROOT).as_posix(),
            "actual_resources_sha256": hashlib.sha256(actual_resources_bytes).hexdigest(),
            "run_summary_path": RUN_SUMMARY_PATH.relative_to(ROOT).as_posix(),
            "run_summary_sha256": sha256_file(RUN_SUMMARY_PATH),
            "fixed_budget_stop": True,
            "fixed_budget_stop_reason": stop_reason,
            "repair_epoch_limit_exhausted": True,
            "scientific_comparison_started": False,
        }
    )
    receipt_bytes = canonical_json_bytes(receipt)
    payloads[base.RECEIPT_PATH] = receipt_bytes

    decision = json.loads(payloads[base.DECISION_PATH].decode("ascii"))
    decision.update(
        {
            "decision": "blocked_fixed_budget",
            "contract_status_if_applied": "in_validation",
            "gpu_screen_status_if_applied": "experimental",
            "bioinformatics_route_if_applied": "conditionally_reopened",
            "all_promotion_gates_pass": False,
            "fresh_holdout_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            "infrastructure_repair_epoch": 1,
            "infrastructure_repair_epoch_limit": 1,
            "repair_plan_sha256": sha256_file(repair.REPAIR_PLAN_PATH),
            "actual_resources_sha256": hashlib.sha256(actual_resources_bytes).hexdigest(),
            "fixed_budget_stop": True,
            "fixed_budget_stop_reason": stop_reason,
            "terminal_attempt_count": len(receipts),
            "unstarted_attempt_count": len(missing),
            "terminal_attempt_technical_failure_count": 0,
            "comparison_started": False,
            "scientific_decision_reached": False,
            "repair_epoch_limit_exhausted": True,
            "superseded_epoch0_evidence_retained": True,
            "no_scientific_input_or_contract_change_in_repair": True,
            "later_phase_authorized": False,
        }
    )
    payloads[base.DECISION_PATH] = canonical_json_bytes(decision)
    return payloads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--adjudicate", action="store_true")
    modes.add_argument("--check", action="store_true")
    parser.add_argument("--artifact-root", type=Path, default=repair.REPAIR_ARTIFACT_ROOT)
    args = parser.parse_args()
    try:
        require(
            args.artifact_root.resolve() == repair.REPAIR_ARTIFACT_ROOT.resolve(),
            "artifact root differs from the repair plan",
        )
        payloads = build()
        if args.check:
            stale = [
                path.relative_to(ROOT).as_posix()
                for path, payload in payloads.items()
                if not path.is_file() or path.read_bytes() != payload
            ]
            if stale:
                parser.exit(1, "stale budget-stop analysis artifacts: " + ", ".join(stale) + "\n")
            print("biological Top-K repair1 fixed-budget adjudication reproduces byte-for-byte")
            return 0
        for path, payload in payloads.items():
            base.atomic_write(path, payload)
        print(f"wrote {len(payloads)} repair1 fixed-budget adjudication artifacts")
        return 0
    except (
        BudgetStopError,
        repair.RepairError,
        base.AnalysisError,
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ) as error:
        print(f"biological Top-K repair1 fixed-budget adjudication failed: {error}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
