#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def _read_kv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def _require(values: dict[str, str], key: str, source: str) -> str:
    try:
        return values[key]
    except KeyError as exc:
        raise SystemExit(f"{source} missing required key: {key}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Decide whether the current GASAL2 pre-convert prune evidence is "
            "ready for a real runtime path."
        )
    )
    parser.add_argument("--authority-diff", required=True, type=Path)
    parser.add_argument("--frontier-full", required=True, type=Path)
    parser.add_argument("--frontier-diff", required=True, type=Path)
    args = parser.parse_args()

    authority = _read_kv(args.authority_diff)
    frontier_full = _read_kv(args.frontier_full)
    frontier_diff = _read_kv(args.frontier_diff)

    row_set_equal = _require(authority, "row_set_equal", "authority diff")
    baseline_only_rows = _require(
        authority, "baseline_only_rows", "authority diff"
    )
    candidate_only_rows = _require(
        authority, "candidate_only_rows", "authority diff"
    )
    diff_frontier_safety = _require(
        frontier_diff, "frontier_safety", "frontier diff"
    )
    full_frontier_safety = _require(
        frontier_full, "frontier_safety", "frontier full"
    )
    full_input_mode = _require(frontier_full, "input_mode", "frontier full")
    diff_input_mode = _require(frontier_diff, "input_mode", "frontier diff")

    current_real_prune_safe = (
        row_set_equal == "1" and diff_frontier_safety == "safe"
    )
    future_full_mode_ready = (
        full_input_mode == "full"
        and _require(frontier_full, "row_set_equal", "frontier full") == "1"
        and full_frontier_safety == "safe"
    )
    diff_only_sufficient = diff_input_mode == "full" and diff_frontier_safety == "safe"

    output = {
        "current_real_prune_decision": (
            "candidate" if current_real_prune_safe else "no_go"
        ),
        "current_real_prune_row_set_equal": row_set_equal,
        "current_real_prune_baseline_only_rows": baseline_only_rows,
        "current_real_prune_candidate_only_rows": candidate_only_rows,
        "current_real_prune_frontier_safety": diff_frontier_safety,
        "future_frontier_full_mode_safety": full_frontier_safety,
        "future_frontier_full_mode_required": "1",
        "diff_only_frontier_is_sufficient": "1" if diff_only_sufficient else "0",
        "next_required_gate": (
            "task_local_frontier_full_mode_proof"
            if not current_real_prune_safe
            else "full_workload_row_set_validation"
        ),
        "real_prune_may_be_enabled": (
            "1" if current_real_prune_safe and future_full_mode_ready else "0"
        ),
    }
    for key, value in output.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
