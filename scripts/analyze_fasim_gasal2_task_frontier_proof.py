#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


REQUIRED_COLUMNS = {
    "task_index",
    "legacy_order_index",
    "scoreinfo_identity",
    "emission_reason",
    "chr",
    "genome_start",
    "genome_end",
    "query_start",
    "query_end",
    "target_start",
    "target_end",
    "score",
    "identity",
    "tri_score",
    "nt",
    "rule",
    "strand",
}


def _task_sort_key(task: str) -> tuple[int, str]:
    try:
        return (int(task), task)
    except ValueError:
        return (2**63 - 1, task)


def _read_task_rows(path: Path) -> dict[str, set[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"empty task triplex file: {path}")
        missing = sorted(REQUIRED_COLUMNS - set(reader.fieldnames))
        if missing:
            raise SystemExit(
                f"{path} missing task triplex columns: " + ", ".join(missing)
            )
        buckets: dict[str, set[str]] = defaultdict(set)
        for row in reader:
            task = row["task_index"]
            # The broad CPU triplex export is the task-local frontier artifact.
            # Preserve row identity exactly, but ignore column order by using
            # the parsed dictionary and the known header order.
            row_key = "\t".join(row.get(name, "") for name in reader.fieldnames)
            buckets[task].add(row_key)
    return dict(buckets)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Prove whether a candidate pre-convert prune preserves complete "
            "task-local broad CPU triplex frontiers."
        )
    )
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()

    baseline = _read_task_rows(args.baseline)
    candidate = _read_task_rows(args.candidate)
    all_tasks = set(baseline) | set(candidate)
    changed_tasks = []
    baseline_only_rows = 0
    candidate_only_rows = 0
    for task in sorted(all_tasks, key=_task_sort_key):
        baseline_rows = baseline.get(task, set())
        candidate_rows = candidate.get(task, set())
        if baseline_rows == candidate_rows:
            continue
        changed_tasks.append(task)
        baseline_only_rows += len(baseline_rows - candidate_rows)
        candidate_only_rows += len(candidate_rows - baseline_rows)

    row_set_equal = not changed_tasks
    first_task = changed_tasks[0] if changed_tasks else "none"
    first_baseline_rows = len(baseline.get(first_task, set())) if changed_tasks else 0
    first_candidate_rows = len(candidate.get(first_task, set())) if changed_tasks else 0

    output = {
        "input_mode": "task_triplex_full",
        "baseline_rows": str(sum(len(rows) for rows in baseline.values())),
        "candidate_rows": str(sum(len(rows) for rows in candidate.values())),
        "task_row_set_equal": "1" if row_set_equal else "0",
        "task_frontier_safety": "safe" if row_set_equal else "unsafe",
        "task_count": str(len(all_tasks)),
        "changed_tasks": str(len(changed_tasks)),
        "baseline_only_rows": str(baseline_only_rows),
        "candidate_only_rows": str(candidate_only_rows),
        "first_changed_task": first_task,
        "first_changed_task_baseline_rows": str(first_baseline_rows),
        "first_changed_task_candidate_rows": str(first_candidate_rows),
        "real_prune_proof_gate": "pass" if row_set_equal else "fail",
    }
    for key, value in output.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
