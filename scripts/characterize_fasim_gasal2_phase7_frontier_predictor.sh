#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_predictor"}"
REPLAY_REPORT="${REPLAY_REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_replay/report.tsv"}"
RUN_REPLAY="${RUN_REPLAY:-auto}"

if [[ "$RUN_REPLAY" == "auto" ]]; then
  if [[ -s "$REPLAY_REPORT" ]]; then
    RUN_REPLAY=0
  else
    RUN_REPLAY=1
  fi
fi

if [[ "$RUN_REPLAY" == "1" ]]; then
  bash "$ROOT/scripts/characterize_fasim_gasal2_phase7_frontier_replay.sh"
fi

if [[ ! -s "$REPLAY_REPORT" ]]; then
  echo "missing Phase 7 frontier replay report: $REPLAY_REPORT" >&2
  exit 1
fi

mkdir -p "$WORK"
REPORT="$WORK/report.tsv"

python3 - "$REPLAY_REPORT" "$REPORT" <<'PY'
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Callable

replay_report = Path(sys.argv[1])
report = Path(sys.argv[2])

FieldRow = dict[str, str]


def int_field(row: FieldRow, key: str) -> int:
    return int(row[key])


def load_frontier(path: Path) -> list[FieldRow]:
    if not path.is_file():
        raise SystemExit(f"missing frontier log: {path}")
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8"), delimiter="\t"))
    required = [
        "task_id",
        "scoreinfo_index",
        "scoreinfo_position",
        "scoreinfo_score",
        "attempt_index",
        "attempt_start",
        "attempt_cutlength",
        "selected",
    ]
    for row in rows:
        missing = [key for key in required if key not in row]
        if missing:
            raise SystemExit(f"{path}: missing columns {missing}")
    return rows


def grouped(rows: list[FieldRow]) -> list[list[FieldRow]]:
    groups: dict[tuple[str, str], list[FieldRow]] = defaultdict(list)
    for row in rows:
        groups[(row["task_id"], row["scoreinfo_index"])].append(row)
    return list(groups.values())


def keep_rank_lt(limit: int) -> Callable[[list[FieldRow], int, FieldRow], bool]:
    return lambda _group, rank, _row: rank < limit


def keep_rank_ge_from_end(limit: int) -> Callable[[list[FieldRow], int, FieldRow], bool]:
    return lambda group, rank, _row: rank >= len(group) - limit


def keep_top_by(field: str, limit: int, reverse: bool) -> Callable[[list[FieldRow], int, FieldRow], bool]:
    def keep(group: list[FieldRow], rank: int, _row: FieldRow) -> bool:
        order = sorted(
            range(len(group)),
            key=lambda index: (int_field(group[index], field), -index if reverse else index),
            reverse=reverse,
        )
        return rank in set(order[:limit])

    return keep


def keep_all(_group: list[FieldRow], _rank: int, _row: FieldRow) -> bool:
    return True


def keep_selected_oracle(_group: list[FieldRow], _rank: int, row: FieldRow) -> bool:
    return row["selected"] == "1"


def evaluate(
    workload: str,
    rows: list[FieldRow],
    predictor: str,
    feature_scope: str,
    fn: Callable[[list[FieldRow], int, FieldRow], bool],
) -> dict[str, str]:
    reference_attempts = len(rows)
    selected_rows = sum(1 for row in rows if row["selected"] == "1")
    kept_attempts = 0
    false_negative_selected_rows = 0
    selected_ranks: set[int] = set()
    group_size_set: set[int] = set()
    for group in grouped(rows):
        group_size_set.add(len(group))
        for rank, row in enumerate(group):
            if row["selected"] == "1":
                selected_ranks.add(rank)
            keep = fn(group, rank, row)
            if keep:
                kept_attempts += 1
            elif row["selected"] == "1":
                false_negative_selected_rows += 1
    reduction = reference_attempts - kept_attempts
    gate_pass = (
        feature_scope == "pre_align_frontier_fields"
        and false_negative_selected_rows == 0
        and reduction > 0
    )
    if gate_pass:
        decision = "phase7_frontier_predictor_candidate_go"
    elif false_negative_selected_rows == 0 and reduction > 0:
        decision = "phase7_frontier_predictor_oracle_only"
    elif false_negative_selected_rows == 0:
        decision = "phase7_frontier_predictor_no_reduction"
    else:
        decision = "phase7_frontier_predictor_false_negative_no_go"
    return {
        "workload": workload,
        "predictor": predictor,
        "feature_scope": feature_scope,
        "reference_attempts": str(reference_attempts),
        "kept_attempts": str(kept_attempts),
        "selected_rows": str(selected_rows),
        "false_negative_selected_rows": str(false_negative_selected_rows),
        "align_attempt_reduction": str(reduction),
        "reduction_fraction": f"{(reduction / reference_attempts) if reference_attempts else 0.0:.6f}",
        "selected_rank_set": ",".join(str(rank) for rank in sorted(selected_ranks)),
        "group_size_set": ",".join(str(size) for size in sorted(group_size_set)),
        "predictor_gate_pass": "1" if gate_pass else "0",
        "decision": decision,
    }


columns = [
    "workload",
    "predictor",
    "feature_scope",
    "reference_attempts",
    "kept_attempts",
    "selected_rows",
    "false_negative_selected_rows",
    "align_attempt_reduction",
    "reduction_fraction",
    "selected_rank_set",
    "group_size_set",
    "predictor_gate_pass",
    "decision",
]

replay_rows = list(csv.DictReader(replay_report.open(newline="", encoding="utf-8"), delimiter="\t"))
by_workload = {row.get("workload"): row for row in replay_rows}
missing = {"neat1_first1", "neat1_first64"} - set(by_workload)
if missing:
    raise SystemExit("missing replay workloads: " + ",".join(sorted(missing)))

predictors: list[tuple[str, str, Callable[[list[FieldRow], int, FieldRow], bool]]] = [
    ("keep_all", "pre_align_frontier_fields", keep_all),
    ("oracle_selected", "oracle_post_align", keep_selected_oracle),
]
for limit in range(1, 4):
    predictors.append((f"keep_first_{limit}", "pre_align_frontier_fields", keep_rank_lt(limit)))
    predictors.append((f"keep_last_{limit}", "pre_align_frontier_fields", keep_rank_ge_from_end(limit)))
    predictors.append((f"start_asc_top_{limit}", "pre_align_frontier_fields", keep_top_by("attempt_start", limit, False)))
    predictors.append((f"start_desc_top_{limit}", "pre_align_frontier_fields", keep_top_by("attempt_start", limit, True)))
    predictors.append((f"cutlength_asc_top_{limit}", "pre_align_frontier_fields", keep_top_by("attempt_cutlength", limit, False)))
    predictors.append((f"cutlength_desc_top_{limit}", "pre_align_frontier_fields", keep_top_by("attempt_cutlength", limit, True)))

out_rows: list[dict[str, str]] = []
prealign_gate_pass = False
for workload in ["neat1_first1", "neat1_first64"]:
    frontier_path = Path(by_workload[workload].get("frontier_log_path", ""))
    frontier_rows = load_frontier(frontier_path)
    for predictor, feature_scope, fn in predictors:
        row = evaluate(workload, frontier_rows, predictor, feature_scope, fn)
        if row["predictor_gate_pass"] == "1":
            prealign_gate_pass = True
        out_rows.append(row)

summary_decision = (
    "phase7_frontier_predictor_candidate_go"
    if prealign_gate_pass
    else "phase7_frontier_predictor_no_go_current_features"
)
out_rows.append(
    {
        "workload": "summary",
        "predictor": "best_pre_align_frontier_fields",
        "feature_scope": "pre_align_frontier_fields",
        "reference_attempts": "0",
        "kept_attempts": "0",
        "selected_rows": "0",
        "false_negative_selected_rows": "0",
        "align_attempt_reduction": "0",
        "reduction_fraction": "0.000000",
        "selected_rank_set": "0,1,2,3",
        "group_size_set": "4",
        "predictor_gate_pass": "1" if prealign_gate_pass else "0",
        "decision": summary_decision,
    }
)

with report.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(out_rows)

print(f"phase7_frontier_predictor_report={report}")
print(f"phase7_frontier_predictor_decision={summary_decision}")
print(f"phase7_frontier_predictor_gate_pass={1 if prealign_gate_pass else 0}")
PY

cat "$REPORT"
