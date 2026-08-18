#!/usr/bin/env python3
"""Assess the exact forward-only floor and lazy-reverse stop gate.

This script consumes already completed receipts.  It never starts a Fasim
process or changes a run directory.  The reverse-work estimate is deliberately
explicit: it scales the measured all-reverse minus forward-only wall delta by
the host-only lazy reverse endpoint-cell fraction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wall_seconds(path: Path) -> float:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    if "wall_seconds" not in values:
        raise ValueError(f"missing wall_seconds in {path}")
    return float(values["wall_seconds"])


def report_summary(path: Path) -> dict[str, object]:
    required = {
        "ok",
        "error",
        "attempts",
        "gpu_scored_attempts",
        "cpu_oracle_attempts",
        "cpu_reference_align_attempts",
        "cpu_continuation_failures",
        "exact_forward_only",
    }
    numeric = (
        "attempts",
        "gpu_scored_attempts",
        "cpu_oracle_attempts",
        "cpu_reference_align_attempts",
        "cpu_continuation_calls",
        "cpu_continuation_failures",
        "score_seconds",
        "gpu_kernel_seconds",
        "h2d_seconds",
        "d2h_seconds",
        "traceback_seconds",
        "convert_seconds",
        "total_seconds",
    )
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = set(reader.fieldnames or ())
        missing = sorted(required - fields)
        if missing:
            raise ValueError(f"missing report fields in {path}: {','.join(missing)}")
        rows.extend(reader)
    if not rows:
        raise ValueError(f"empty consumer report: {path}")

    failures: list[str] = []
    totals = {field: 0.0 for field in numeric}
    for index, row in enumerate(rows, 2):
        if row["ok"] != "1" or row["error"] != "none":
            failures.append(f"line {index}: task failure")
        if row["exact_forward_only"] != "1":
            failures.append(f"line {index}: exact_forward_only=0")
        for field in numeric:
            totals[field] += float(row[field])
        if int(row["attempts"]) != int(row["gpu_scored_attempts"]):
            failures.append(f"line {index}: incomplete GPU attempt coverage")
        if int(row["cpu_oracle_attempts"]) != 0:
            failures.append(f"line {index}: CPU all-attempt oracle was used")
        if int(row["cpu_reference_align_attempts"]) != 0:
            failures.append(f"line {index}: CPU reference alignment was used")
        if int(row["cpu_continuation_failures"]) != 0:
            failures.append(f"line {index}: continuation failure")

    return {
        "report": str(path.resolve()),
        "task_rows": len(rows),
        "failures": failures[:20],
        "status": "pass" if not failures else "fail",
        "totals": {
            field: (int(value) if field not in {
                "score_seconds",
                "gpu_kernel_seconds",
                "h2d_seconds",
                "d2h_seconds",
                "traceback_seconds",
                "convert_seconds",
                "total_seconds",
            } else value)
            for field, value in totals.items()
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lazy-summary", type=Path, required=True)
    parser.add_argument("--forward-report", type=Path, required=True)
    parser.add_argument("--forward-time", type=Path, required=True)
    parser.add_argument("--all-reverse-time", type=Path, required=True)
    parser.add_argument("--cpu-time", type=Path, required=True)
    parser.add_argument("--forward-output", type=Path, required=True)
    parser.add_argument("--cpu-output", type=Path, required=True)
    parser.add_argument("--source-commit", default="unknown")
    parser.add_argument("--binary-sha256", default="unknown")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lazy = json.loads(args.lazy_summary.read_text(encoding="utf-8"))
    if lazy.get("status") != "pass":
        raise SystemExit("lazy reverse summary is not pass")
    forward = report_summary(args.forward_report)
    cpu_digest = sha256(args.cpu_output)
    forward_digest = sha256(args.forward_output)
    cpu_wall = wall_seconds(args.cpu_time)
    forward_wall = wall_seconds(args.forward_time)
    all_reverse_wall = wall_seconds(args.all_reverse_time)
    cell_fraction = float(lazy["lazy_reverse_envelope_cell_fraction"])
    reverse_delta = all_reverse_wall - forward_wall
    predicted_lazy_wall = forward_wall + reverse_delta * cell_fraction
    forward_speedup = cpu_wall / forward_wall if forward_wall else 0.0
    all_reverse_speedup = cpu_wall / all_reverse_wall if all_reverse_wall else 0.0
    predicted_lazy_speedup = (
        cpu_wall / predicted_lazy_wall if predicted_lazy_wall else 0.0
    )
    output_equal = cpu_digest == forward_digest
    floor_blocks_gate = forward_wall > cpu_wall / 1.5
    payload = {
        "schema_version": "long_query_exact_reverse_floor_audit_v1",
        "status": "pass" if forward["status"] == "pass" and output_equal else "fail",
        "source_commit": args.source_commit,
        "binary_sha256": args.binary_sha256,
        "lazy_shadow": lazy,
        "forward_only": forward,
        "output": {
            "cpu_sha256": cpu_digest,
            "forward_only_sha256": forward_digest,
            "byte_equal": output_equal,
        },
        "timing_seconds": {
            "cpu_authority": cpu_wall,
            "exact_forward_only": forward_wall,
            "all_reverse_exact": all_reverse_wall,
            "all_reverse_increment": reverse_delta,
            "predicted_lazy_reverse": predicted_lazy_wall,
        },
        "speedup": {
            "exact_forward_only": forward_speedup,
            "all_reverse_exact": all_reverse_speedup,
            "predicted_lazy_reverse": predicted_lazy_speedup,
        },
        "decision": {
            "target_speedup": 1.5,
            "forward_only_floor_blocks_target": floor_blocks_gate,
            "compact_reverse_kernel_authorized": predicted_lazy_speedup >= 1.5,
            "performance_no_go": predicted_lazy_speedup < 1.5,
            "reason": (
                "forward-only floor already exceeds the 1.5x wall budget"
                if floor_blocks_gate
                else "lazy reverse prediction below the 1.5x gate"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
