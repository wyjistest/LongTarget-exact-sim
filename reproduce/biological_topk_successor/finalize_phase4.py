#!/usr/bin/env python3
"""Finalize and reproduce successor Phase 4 analysis and resource evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from reproduce.biological_topk_successor import analyze_phase4 as analyzer  # noqa: E402
from reproduce.biological_topk_successor import freeze_phase3 as frozen  # noqa: E402
from reproduce.biological_topk_successor import run_phase4 as runner  # noqa: E402


PAPER = ROOT / "paper/biological_topk_successor"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk-successor/fresh-holdout"
ACTUAL_RESOURCES_PATH = PAPER / "fresh_holdout_actual_resources.json"
PHASE3_COMMIT = "7e3f46ee94df6651240052f5f317202129f73d05"
PREDECESSOR_BYTES = 7_142_325_727
TRACKED_PHASE4_RESERVATION_BYTES = 256 * 1024**2
FIXED_TOTAL_STORAGE_BYTES = 64 * 1024**3


class FinalizeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FinalizeError(message)


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def directory_file_bytes(path: Path) -> int:
    require(path.is_dir() and not path.is_symlink(), f"missing or unsafe artifact root: {path}")
    total = 0
    for child in path.rglob("*"):
        require(not child.is_symlink(), f"artifact root contains symlink: {child}")
        if child.is_file():
            total += child.stat().st_size
    return total


def tracked_successor_bytes_at_phase3() -> int:
    completed = subprocess.run(
        ("git", "ls-tree", "-r", "-l", PHASE3_COMMIT),
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(completed.returncode == 0, completed.stderr.strip() or "cannot inventory successor Phase 3 tree")
    total = 0
    for line in completed.stdout.splitlines():
        metadata, relative = line.split("\t", 1)
        included = (
            relative == "goal-biological-topk-successor.md"
            or relative == "schemas/biological_topk_successor_program_state.schema.json"
            or relative.startswith("paper/biological_topk_successor/")
            or relative.startswith("reproduce/biological_topk_successor/")
            or relative.startswith("tests/biological_topk_successor/")
            or relative.startswith("scripts/check_biological_topk_successor_")
        )
        if included:
            total += int(metadata.split()[3])
    require(total > 0, "empty successor Phase 3 tracked inventory")
    return total


def attempt_rows() -> list[dict[str, str]]:
    with frozen.ATTEMPT_PLAN_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    require(len(rows) == 368, "successor Phase 4 attempt plan count drift")
    return rows


def terminal_receipts(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    receipts = []
    for row in rows:
        destination = ROOT / row["artifact_root"]
        receipt = runner.validate_completed_attempt(destination, row)
        require(receipt["status"] == "success", f"successor Phase 4 terminal failure: {row['attempt_id']}")
        require(receipt["source_commit"] == PHASE3_COMMIT, f"successor Phase 4 source commit drift: {row['attempt_id']}")
        receipts.append(receipt)
    return receipts


def build_actual_resources(rows: list[dict[str, str]], receipts: list[dict[str, Any]]) -> dict[str, Any]:
    summary_path = ARTIFACT_ROOT / "run-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    require(summary["status"] == "complete_success", "successor Phase 4 run summary is not complete_success")
    require(summary["planned_attempt_count"] == summary["terminal_attempt_count"] == summary["successful_attempt_count"] == 368, "successor Phase 4 run summary count drift")
    require(summary["technical_failure_count"] == 0 and summary["missing_attempt_ids"] == [], "successor Phase 4 run summary contains failures/missing attempts")
    require(summary["comparison_started"] is False, "successor runner started scientific comparison")
    started = [datetime.fromisoformat(str(receipt["execution"]["started_utc"])) for receipt in receipts]
    finished = [datetime.fromisoformat(str(receipt["execution"]["finished_utc"])) for receipt in receipts]
    cpu_wall = sum(float(receipt["wall_seconds"]) for receipt in receipts if receipt["arm"] == "A")
    gpu_wall = sum(float(receipt["wall_seconds"]) for receipt in receipts if receipt["arm"] == "G")
    elapsed = (max(finished) - min(started)).total_seconds()
    runtime_bytes = directory_file_bytes(ARTIFACT_ROOT)
    tracked_phase3 = tracked_successor_bytes_at_phase3()
    total_with_reservation = PREDECESSOR_BYTES + tracked_phase3 + TRACKED_PHASE4_RESERVATION_BYTES + runtime_bytes
    telemetry_archives = list(ARTIFACT_ROOT.glob("*/telemetry.json.gz"))
    raw_telemetry = list(ARTIFACT_ROOT.glob("*/telemetry.json"))
    require(len(telemetry_archives) == 184 and not raw_telemetry, "successor telemetry final storage count drift")
    return {
        "schema_version": 1,
        "phase": 4,
        "status": "pass" if elapsed <= 172800 and gpu_wall / 3600 <= 72 and total_with_reservation <= FIXED_TOTAL_STORAGE_BYTES else "blocked_fixed_budget",
        "planned_attempt_count": len(rows),
        "terminal_attempt_count": len(receipts),
        "successful_attempt_count": len(receipts),
        "terminal_technical_failure_count": 0,
        "completed_cpu_attempt_count": sum(receipt["arm"] == "A" for receipt in receipts),
        "completed_gpu_attempt_count": sum(receipt["arm"] == "G" for receipt in receipts),
        "actual_cpu_aggregate_wall_seconds": format(cpu_wall, ".17g"),
        "actual_gpu_aggregate_wall_seconds": format(gpu_wall, ".17g"),
        "actual_gpu_hours": format(gpu_wall / 3600, ".17g"),
        "actual_scheduled_elapsed_wall_seconds": format(elapsed, ".17g"),
        "predecessor_retained_artifact_bytes": PREDECESSOR_BYTES,
        "successor_tracked_bytes_through_phase3": tracked_phase3,
        "successor_phase4_tracked_reservation_bytes": TRACKED_PHASE4_RESERVATION_BYTES,
        "successor_runtime_artifact_bytes": runtime_bytes,
        "actual_total_artifact_storage_bytes_with_tracked_reservation": total_with_reservation,
        "fixed_total_artifact_storage_bytes": FIXED_TOTAL_STORAGE_BYTES,
        "artifact_storage_margin_bytes": FIXED_TOTAL_STORAGE_BYTES - total_with_reservation,
        "max_formal_scheduled_wall_seconds": 172800,
        "max_gpu_hours": 72,
        "scheduled_elapsed_gate_pass": elapsed <= 172800,
        "gpu_hours_gate_pass": gpu_wall / 3600 <= 72,
        "artifact_storage_gate_pass": total_with_reservation <= FIXED_TOTAL_STORAGE_BYTES,
        "fixed_budget_gate_pass": elapsed <= 172800 and gpu_wall / 3600 <= 72 and total_with_reservation <= FIXED_TOTAL_STORAGE_BYTES,
        "telemetry_archive_count": len(telemetry_archives),
        "raw_telemetry_file_count": len(raw_telemetry),
        "telemetry_storage_policy": "validated_then_deterministic_lossless_gzip_mtime0_before_next_attempt",
        "run_summary_path": summary_path.relative_to(ROOT).as_posix(),
        "run_summary_sha256": sha256_file(summary_path),
        "comparison_started_by_runner": False,
        "resource_values_are_performance_claims": False,
        "infrastructure_repair_epochs_used": 0,
    }


def build() -> dict[Path, bytes]:
    rows = attempt_rows()
    receipts = terminal_receipts(rows)
    payloads = analyzer.build()
    resources = build_actual_resources(rows, receipts)
    resources_bytes = canonical_json_bytes(resources)
    payloads[ACTUAL_RESOURCES_PATH] = resources_bytes

    receipt = json.loads(payloads[analyzer.RECEIPT_PATH].decode("ascii"))
    receipt.update(
        {
            "artifact_root": ARTIFACT_ROOT.relative_to(ROOT).as_posix(),
            "actual_resources_path": ACTUAL_RESOURCES_PATH.relative_to(ROOT).as_posix(),
            "actual_resources_sha256": sha256_bytes(resources_bytes),
            "run_summary_path": resources["run_summary_path"],
            "run_summary_sha256": resources["run_summary_sha256"],
            "telemetry_storage_policy": resources["telemetry_storage_policy"],
            "telemetry_archive_count": resources["telemetry_archive_count"],
            "raw_telemetry_file_count": resources["raw_telemetry_file_count"],
            "infrastructure_repair_epochs_used": 0,
            "scientific_comparison_started_only_after_all_attempts_terminal": True,
            "fixed_budget_gate_pass": resources["fixed_budget_gate_pass"],
        }
    )
    receipt_bytes = canonical_json_bytes(receipt)
    payloads[analyzer.RECEIPT_PATH] = receipt_bytes

    decision = json.loads(payloads[analyzer.DECISION_PATH].decode("ascii"))
    if not resources["fixed_budget_gate_pass"]:
        decision["decision"] = "blocked_fixed_budget"
        decision["all_promotion_gates_pass"] = False
        decision["contract_status_if_applied"] = "in_validation"
    decision.update(
        {
            "fresh_holdout_receipt_sha256": sha256_bytes(receipt_bytes),
            "actual_resources_sha256": sha256_bytes(resources_bytes),
            "fixed_budget_gate_pass": resources["fixed_budget_gate_pass"],
            "comparison_started": True,
            "scientific_decision_reached": decision["decision"] in {"pass", "no_go"},
            "no_post_run_supplementation": True,
            "infrastructure_repair_epochs_used": 0,
            "later_phase_authorized": decision["decision"] == "pass",
        }
    )
    payloads[analyzer.DECISION_PATH] = canonical_json_bytes(decision)
    return payloads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        payloads = build()
        if args.write:
            for path, payload in payloads.items():
                analyzer.atomic_write(path, payload)
            print(f"wrote {len(payloads)} successor Phase 4 analysis artifacts")
            return 0
        stale = [path.relative_to(ROOT).as_posix() for path, payload in payloads.items() if not path.is_file() or path.read_bytes() != payload]
        require(not stale, f"successor Phase 4 analysis artifacts do not reproduce: {stale}")
        print("successor Phase 4 analysis artifacts reproduce byte-for-byte")
        return 0
    except (FinalizeError, analyzer.AnalysisError, runner.RunnerError, frozen.FreezeError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"successor Phase 4 finalization failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
