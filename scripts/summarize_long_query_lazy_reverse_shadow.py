#!/usr/bin/env python3
"""Aggregate and gate host-only lazy canonical-reverse shadow telemetry."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REQUIRED = (
    "ok",
    "error",
    "lazy_reverse_shadow_requested",
    "lazy_reverse_shadow_active",
    "lazy_reverse_selection_equal",
    "lazy_reverse_reasons_equal",
    "lazy_reverse_full_attempts",
    "lazy_reverse_attempts",
    "lazy_reverse_threshold_attempts",
    "lazy_reverse_best_attempts",
    "lazy_reverse_last_attempts",
    "lazy_reverse_reused_for_best",
    "lazy_reverse_reused_for_last",
    "lazy_reverse_full_envelope_cells",
    "lazy_reverse_envelope_cells",
    "lazy_reverse_threshold_envelope_cells",
    "lazy_reverse_best_envelope_cells",
    "lazy_reverse_last_envelope_cells",
    "lazy_reverse_shadow_seconds",
    "first_lazy_reverse_mismatch",
)

INTEGER_TOTALS = tuple(field for field in REQUIRED if field.startswith("lazy_reverse_") and not field.endswith("seconds") and field not in {
    "lazy_reverse_shadow_requested",
    "lazy_reverse_shadow_active",
    "lazy_reverse_selection_equal",
    "lazy_reverse_reasons_equal",
})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    totals = {field: 0 for field in INTEGER_TOTALS}
    shadow_seconds = 0.0
    rows = 0
    failures: list[str] = []
    with args.consumer_report.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = [field for field in REQUIRED if field not in (reader.fieldnames or ())]
        if missing:
            raise SystemExit(f"missing lazy-reverse columns: {','.join(missing)}")
        for line_number, row in enumerate(reader, 2):
            rows += 1
            for field in INTEGER_TOTALS:
                totals[field] += int(row[field])
            shadow_seconds += float(row["lazy_reverse_shadow_seconds"])
            if row["ok"] != "1" or row["error"] != "none":
                failures.append(f"line {line_number}: task failed")
            for field in (
                "lazy_reverse_shadow_requested",
                "lazy_reverse_shadow_active",
                "lazy_reverse_selection_equal",
                "lazy_reverse_reasons_equal",
            ):
                if row[field] != "1":
                    failures.append(f"line {line_number}: {field}=0")
            if row["first_lazy_reverse_mismatch"] != "none":
                failures.append(
                    f"line {line_number}: {row['first_lazy_reverse_mismatch']}"
                )
            reasons = sum(
                int(row[field])
                for field in (
                    "lazy_reverse_threshold_attempts",
                    "lazy_reverse_best_attempts",
                    "lazy_reverse_last_attempts",
                )
            )
            if reasons != int(row["lazy_reverse_attempts"]):
                failures.append(f"line {line_number}: reverse reason conservation failed")
            if int(row["lazy_reverse_attempts"]) > int(row["lazy_reverse_full_attempts"]):
                failures.append(f"line {line_number}: lazy attempts exceed full reverse")
            if int(row["lazy_reverse_envelope_cells"]) > int(
                row["lazy_reverse_full_envelope_cells"]
            ):
                failures.append(f"line {line_number}: lazy cells exceed full reverse")

    if rows == 0:
        failures.append("consumer report has no task rows")
    full_attempts = totals["lazy_reverse_full_attempts"]
    full_cells = totals["lazy_reverse_full_envelope_cells"]
    summary = {
        "schema_version": "long_query_lazy_reverse_shadow_summary_v1",
        "status": "pass" if not failures else "fail",
        "consumer_report": str(args.consumer_report.resolve()),
        "task_rows": rows,
        **totals,
        "lazy_reverse_attempt_fraction": (
            totals["lazy_reverse_attempts"] / full_attempts if full_attempts else 0.0
        ),
        "lazy_reverse_envelope_cell_fraction": (
            totals["lazy_reverse_envelope_cells"] / full_cells if full_cells else 0.0
        ),
        "lazy_reverse_shadow_seconds": shadow_seconds,
        "failures": failures[:20],
    }
    payload = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
