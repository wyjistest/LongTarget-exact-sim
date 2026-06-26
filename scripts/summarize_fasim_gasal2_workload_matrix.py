#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


TRUE_VALUES = {"true", "1", "yes", "pass"}


def _truthy(value: str) -> bool:
    return value.strip().lower() in TRUE_VALUES


def _float_gt_one(value: str) -> bool:
    try:
        return float(value) > 1.0
    except ValueError:
        return False


def _int_zero(value: str) -> bool:
    try:
        return int(value) == 0
    except ValueError:
        return False


def _broad_gate_clean(row: dict[str, str]) -> bool:
    return (
        row.get("contract") == "broad_replacement"
        and row.get("scope") == "claimed"
        and row.get("status") == "pass"
        and _truthy(row.get("row_equal", ""))
        and _float_gt_one(row.get("speedup", ""))
        and _int_zero(row.get("fallbacks", ""))
        and _truthy(row.get("scoreinfo_reduced", ""))
        and _truthy(row.get("align_side_reduced", ""))
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize the Fasim/GASAL2 workload evidence matrix."
    )
    parser.add_argument("--matrix", required=True, type=Path)
    args = parser.parse_args()

    with args.matrix.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    claimed = [row for row in rows if row.get("scope") == "claimed"]
    unclaimed = [row for row in rows if row.get("scope") == "unclaimed"]
    blocked = [row for row in rows if row.get("scope") == "blocked"]

    claimed_pass = [row for row in claimed if row.get("status") == "pass"]
    claimed_fail = [row for row in claimed if row.get("status") != "pass"]
    broad_gate_rows = [row for row in rows if row.get("contract") == "broad_replacement"]
    broad_gate_rows_clean = [row for row in broad_gate_rows if _broad_gate_clean(row)]
    scoreinfo_reduced_claimed = [
        row for row in claimed if _truthy(row.get("scoreinfo_reduced", ""))
    ]
    align_side_reduced_claimed = [
        row for row in claimed if _truthy(row.get("align_side_reduced", ""))
    ]
    performance_specific = all(row.get("workload") for row in rows if row.get("speedup"))
    explicit_nonclaimed = all(
        row.get("status") in {"fallback", "fail", "no_go", "blocked", "pass"}
        for row in unclaimed + blocked
    )

    if claimed_fail:
        decision = "matrix_has_claimed_failures"
    elif not explicit_nonclaimed:
        decision = "matrix_has_implicit_nonclaimed_scope"
    else:
        decision = "matrix_has_claimed_scope_only"

    output = {
        "workloads": str(len(rows)),
        "claimed_workloads": str(len(claimed)),
        "claimed_pass": str(len(claimed_pass)),
        "claimed_fail": str(len(claimed_fail)),
        "unclaimed_workloads": str(len(unclaimed)),
        "blocked_workloads": str(len(blocked)),
        "performance_claims_workload_specific": (
            "1" if performance_specific else "0"
        ),
        "broad_gate_rows": str(len(broad_gate_rows)),
        "broad_gate_rows_clean": str(len(broad_gate_rows_clean)),
        "scoreinfo_reduced_claimed": str(len(scoreinfo_reduced_claimed)),
        "align_side_reduced_claimed": str(len(align_side_reduced_claimed)),
        "decision": decision,
    }
    for key, value in output.items():
        print(f"{key}={value}")

    for row in rows:
        workload = row.get("workload", "")
        scope = row.get("scope", "")
        status = row.get("status", "")
        row_equal = row.get("row_equal", "NA")
        top5_equal = row.get("top5_equal", "NA")
        if scope == "claimed" and status == "pass":
            row_decision = "claimed_pass"
        elif scope == "claimed":
            row_decision = "claimed_fail"
        elif status == "fallback":
            row_decision = f"{scope}_fallback"
        elif status in {"fail", "blocked", "no_go"}:
            row_decision = f"{scope}_fail"
        elif _truthy(row_equal) or _truthy(top5_equal):
            row_decision = f"{scope}_clean"
        else:
            row_decision = f"{scope}_unknown"
        print(f"workload.{workload}={row_decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
