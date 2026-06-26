#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


TRUE_VALUES = {"true", "1", "yes", "pass"}


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in TRUE_VALUES


def _float_gt_one(value: str | None) -> bool:
    try:
        return float(value or "") > 1.0
    except ValueError:
        return False


def _int_zero(value: str | None) -> bool:
    try:
        return int(value or "") == 0
    except ValueError:
        return False


def _broad_gate_row_clean(row: dict[str, str]) -> bool:
    if row.get("contract") != "broad_replacement":
        return False
    return (
        row.get("scope") == "claimed"
        and row.get("status") == "pass"
        and _truthy(row.get("row_equal"))
        and _float_gt_one(row.get("speedup"))
        and _int_zero(row.get("fallbacks"))
        and _truthy(row.get("scoreinfo_reduced"))
        and _truthy(row.get("align_side_reduced"))
    )


def _path_a_acceptance_recorded(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    text = " ".join(path.read_text(encoding="utf-8").split())
    return (
        "user_scope_acceptance_recorded = 1" in text
        and "scoped_completion_may_close_goal = 1" in text
        and "path_a_user_acceptance_recorded = 1" in text
        and "active_goal_completion_status = complete_scoped_path_a" in text
        and "not broad aligner.Align replacement" in text
        and "GASAL2 output authority = 0" in text
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Decide scoped vs broad completion for the Fasim/GASAL2 roadmap."
    )
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--acceptance", type=Path)
    args = parser.parse_args()

    with args.matrix.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    claimed = [row for row in rows if row.get("scope") == "claimed"]
    non_claimed = [row for row in rows if row.get("scope") != "claimed"]
    claimed_clean = bool(claimed) and all(row.get("status") == "pass" for row in claimed)
    broad_claims = [row for row in claimed if row.get("contract") == "broad_replacement"]
    broad_gate_rows_clean = bool(broad_claims) and all(
        _broad_gate_row_clean(row) for row in broad_claims
    )
    has_open_boundary = any(row.get("scope") in {"unclaimed", "blocked"} for row in rows)
    broad_complete = claimed_clean and broad_gate_rows_clean and not has_open_boundary
    path_a_acceptance_recorded = _path_a_acceptance_recorded(args.acceptance)
    scoped_accepted = claimed_clean and path_a_acceptance_recorded

    scoped_status = (
        "accepted"
        if scoped_accepted
        else ("ready_if_user_accepts_scope" if claimed_clean else "not_ready")
    )
    broad_status = "complete" if broad_complete else "open"
    completion_guard_cleared = broad_complete or scoped_accepted
    final_decision = (
        "complete"
        if broad_complete
        else (
            "complete_scoped_path_a"
            if scoped_accepted
            else "not_complete_without_user_scope_acceptance"
        )
    )
    scope_or_broad_design_decision_required = (
        scoped_status == "ready_if_user_accepts_scope"
        and not broad_complete
        and not scoped_accepted
    )

    output = {
        "scoped_product_status": scoped_status,
        "broad_objective_status": broad_status,
        "broad_restart_required": (
            "0" if broad_complete or scoped_accepted else "1"
        ),
        "claimed_workloads_clean": "1" if claimed_clean else "0",
        "broad_gate_rows_clean": "1" if broad_gate_rows_clean else "0",
        "blocked_or_unclaimed_workloads": str(len(non_claimed)),
        "user_scope_acceptance_recorded": "1" if path_a_acceptance_recorded else "0",
        "scoped_completion_may_close_goal": "1" if scoped_accepted else "0",
        "path_a_user_acceptance_recorded": (
            "1" if path_a_acceptance_recorded else "0"
        ),
        "path_a_scoped_completion_may_close_goal": (
            "1" if scoped_accepted else "0"
        ),
        "active_goal_completion_status": (
            "complete_scoped_path_a"
            if scoped_accepted
            else ("complete_broad_path_b" if broad_complete else "open")
        ),
        "final_goal_decision": final_decision,
        "scope_or_broad_design_decision_required": (
            "1" if scope_or_broad_design_decision_required else "0"
        ),
        "path_a_user_acceptance_required": (
            "1" if scope_or_broad_design_decision_required else "0"
        ),
        "path_b_new_broad_architecture_required": (
            "1" if not completion_guard_cleared else "0"
        ),
        "completion_guard_cleared": "1" if completion_guard_cleared else "0",
        "goal_completion_status": (
            "complete" if completion_guard_cleared else "open"
        ),
        "must_not_call_update_goal_complete": (
            "0" if completion_guard_cleared else "1"
        ),
    }
    for key, value in output.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
