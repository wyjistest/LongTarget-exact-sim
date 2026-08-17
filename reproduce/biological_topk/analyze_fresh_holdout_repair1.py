#!/usr/bin/env python3
"""Analyze the single authorized Phase 4 infrastructure-repair epoch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from . import analyze_fresh_holdout as base
    from . import run_fresh_holdout_repair1 as repair
except ImportError:  # pragma: no cover
    import analyze_fresh_holdout as base  # type: ignore[no-redef]
    import run_fresh_holdout_repair1 as repair  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[2]
ACTUAL_RESOURCES_PATH = ROOT / "paper/biological_topk/fresh_holdout_actual_resources.json"


class RepairAnalysisError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RepairAnalysisError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def build() -> dict[Path, bytes]:
    manifest, attempts, plan, inputs = repair.validate_repair_plan()
    del inputs
    original_validator = base.runner.validate_frozen_plan
    original_comparison_root = base.COMPARISON_ROOT
    try:
        base.runner.validate_frozen_plan = lambda: (manifest, attempts, plan, repair.load_inputs_for_analysis(manifest))
        base.COMPARISON_ROOT = repair.REPAIR_ARTIFACT_ROOT / "offline-comparisons"
        payloads = base.build()
    finally:
        base.runner.validate_frozen_plan = original_validator
        base.COMPARISON_ROOT = original_comparison_root

    attempt_receipts = [
        json.loads(
            (ROOT / row["artifact_root"] / "attempt-complete.json").read_text(encoding="utf-8")
        )
        for row in attempts
    ]
    require(len(attempt_receipts) == 368, "actual resource accounting requires every terminal attempt")
    require(all(item["status"] in {"success", "technical_failure"} for item in attempt_receipts), "nonterminal attempt in resource accounting")
    cpu_wall = sum(float(item["wall_seconds"]) for item in attempt_receipts if item["arm"] == "A")
    gpu_wall = sum(float(item["wall_seconds"]) for item in attempt_receipts if item["arm"] == "G")
    started = [datetime.fromisoformat(str(item["execution"]["started_utc"])) for item in attempt_receipts]
    finished = [datetime.fromisoformat(str(item["execution"]["finished_utc"])) for item in attempt_receipts]
    current_artifact_bytes = repair.directory_bytes(repair.ORIGINAL_ARTIFACT_ROOT) + repair.directory_bytes(repair.REPAIR_ARTIFACT_ROOT)
    pending_artifact_delta = 0
    for path, payload in payloads.items():
        if repair.REPAIR_ARTIFACT_ROOT in path.parents:
            pending_artifact_delta += len(payload) - (path.stat().st_size if path.is_file() else 0)
    final_storage_bytes = current_artifact_bytes + pending_artifact_delta
    actual_resources = {
        "schema_version": 1,
        "phase": 4,
        "status": "pass" if final_storage_bytes <= repair.frozen.MAX_STORAGE_BYTES else "blocked_fixed_budget",
        "repair_epoch": 1,
        "attempt_count": len(attempt_receipts),
        "cpu_attempt_count": sum(item["arm"] == "A" for item in attempt_receipts),
        "gpu_attempt_count": sum(item["arm"] == "G" for item in attempt_receipts),
        "actual_cpu_aggregate_wall_seconds": format(cpu_wall, ".17g"),
        "actual_gpu_aggregate_wall_seconds": format(gpu_wall, ".17g"),
        "actual_gpu_hours": format(gpu_wall / 3600, ".17g"),
        "actual_scheduled_elapsed_wall_seconds": format((max(finished) - min(started)).total_seconds(), ".17g"),
        "superseded_epoch0_artifact_bytes": repair.directory_bytes(repair.ORIGINAL_ARTIFACT_ROOT),
        "repair_epoch_artifact_bytes_before_analysis": repair.directory_bytes(repair.REPAIR_ARTIFACT_ROOT),
        "offline_comparison_artifact_delta_bytes": pending_artifact_delta,
        "actual_total_epoch_artifact_storage_bytes": final_storage_bytes,
        "max_formal_scheduled_wall_seconds": repair.frozen.MAX_ELAPSED_SECONDS,
        "max_gpu_hours": repair.frozen.MAX_GPU_HOURS,
        "max_artifact_storage_bytes": repair.frozen.MAX_STORAGE_BYTES,
        "scheduled_elapsed_gate_pass": (max(finished) - min(started)).total_seconds() <= repair.frozen.MAX_ELAPSED_SECONDS,
        "gpu_hours_gate_pass": gpu_wall / 3600 <= repair.frozen.MAX_GPU_HOURS,
        "artifact_storage_gate_pass": final_storage_bytes <= repair.frozen.MAX_STORAGE_BYTES,
        "fixed_budget_gate_pass": (
            (max(finished) - min(started)).total_seconds() <= repair.frozen.MAX_ELAPSED_SECONDS
            and gpu_wall / 3600 <= repair.frozen.MAX_GPU_HOURS
            and final_storage_bytes <= repair.frozen.MAX_STORAGE_BYTES
        ),
        "original_evidence_included": True,
        "technical_telemetry_lossless_gzip": True,
        "resource_values_are_performance_claims": False,
    }
    actual_resources_bytes = canonical_json_bytes(actual_resources)
    payloads[ACTUAL_RESOURCES_PATH] = actual_resources_bytes

    receipt = json.loads(payloads[base.RECEIPT_PATH].decode("ascii"))
    receipt["original_attempt_plan_sha256"] = sha256_file(repair.ORIGINAL_ATTEMPT_PLAN_PATH)
    receipt["attempt_plan_sha256"] = sha256_file(repair.REPAIR_ATTEMPT_PLAN_PATH)
    receipt["infrastructure_repair_epoch"] = 1
    receipt["infrastructure_repair_epoch_limit"] = 1
    receipt["repair_plan_sha256"] = sha256_file(repair.REPAIR_PLAN_PATH)
    receipt["infrastructure_incident_sha256"] = sha256_file(repair.INCIDENT_PATH)
    receipt["artifact_root"] = repair.REPAIR_ARTIFACT_ROOT.relative_to(ROOT).as_posix()
    receipt["superseded_epoch0_artifact_root"] = repair.ORIGINAL_ARTIFACT_ROOT.relative_to(ROOT).as_posix()
    receipt["superseded_epoch0_evidence_retained"] = True
    receipt["telemetry_storage_policy"] = "validated_then_lossless_gzip_mtime0"
    receipt["actual_resources_path"] = ACTUAL_RESOURCES_PATH.relative_to(ROOT).as_posix()
    receipt["actual_resources_sha256"] = hashlib.sha256(actual_resources_bytes).hexdigest()
    receipt_bytes = canonical_json_bytes(receipt)
    payloads[base.RECEIPT_PATH] = receipt_bytes

    decision = json.loads(payloads[base.DECISION_PATH].decode("ascii"))
    decision["fresh_holdout_receipt_sha256"] = hashlib.sha256(receipt_bytes).hexdigest()
    decision["infrastructure_repair_epoch"] = 1
    decision["infrastructure_repair_epoch_limit"] = 1
    decision["repair_plan_sha256"] = sha256_file(repair.REPAIR_PLAN_PATH)
    decision["superseded_epoch0_evidence_retained"] = True
    decision["no_scientific_input_or_contract_change_in_repair"] = True
    payloads[base.DECISION_PATH] = canonical_json_bytes(decision)
    return payloads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--analyze", action="store_true")
    modes.add_argument("--check", action="store_true")
    parser.add_argument("--artifact-root", type=Path, default=repair.REPAIR_ARTIFACT_ROOT)
    args = parser.parse_args()
    try:
        require(args.artifact_root.resolve() == repair.REPAIR_ARTIFACT_ROOT.resolve(), "artifact root differs from repair plan")
        manifest, attempts, plan, _ = repair.validate_repair_plan()
        if args.preflight:
            print(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": "repair1_analysis_preflight_pass",
                        "read_only": True,
                        "primary_workloads": len(manifest),
                        "attempts": len(attempts),
                        "repair_epoch": plan["repair_epoch"],
                        "artifact_root_exists": repair.REPAIR_ARTIFACT_ROOT.exists(),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        payloads = build()
        if args.check:
            stale = [path.relative_to(ROOT).as_posix() for path, payload in payloads.items() if not path.is_file() or path.read_bytes() != payload]
            if stale:
                parser.exit(1, "stale repair analysis artifacts: " + ", ".join(stale) + "\n")
            print("biological Top-K repair1 analysis reproduces byte-for-byte")
            return 0
        for path, payload in payloads.items():
            base.atomic_write(path, payload)
        print(f"wrote {len(payloads)} repair1 analysis artifacts")
        return 0
    except (
        RepairAnalysisError,
        repair.RepairError,
        base.AnalysisError,
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ) as error:
        print(f"biological Top-K repair1 analysis failed: {error}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
