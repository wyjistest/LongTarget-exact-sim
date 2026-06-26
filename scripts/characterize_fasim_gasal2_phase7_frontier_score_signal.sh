#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_score_signal"}"
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
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8"), delimiter="\t"))
    required = [
        "task_id",
        "scoreinfo_index",
        "align_sw_score",
        "align_ref_begin",
        "align_ref_end",
        "align_query_begin",
        "align_query_end",
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


def keep_top_by(field: str, limit: int, reverse: bool) -> Callable[[list[FieldRow], int, FieldRow], bool]:
    def keep(group: list[FieldRow], rank: int, _row: FieldRow) -> bool:
        order = sorted(
            range(len(group)),
            key=lambda index: (int_field(group[index], field), -index if reverse else index),
            reverse=reverse,
        )
        return rank in set(order[:limit])

    return keep


def keep_threshold(field: str, threshold: int) -> Callable[[list[FieldRow], int, FieldRow], bool]:
    return lambda _group, _rank, row: int_field(row, field) >= threshold


def keep_selected_oracle(_group: list[FieldRow], _rank: int, row: FieldRow) -> bool:
    return row["selected"] == "1"


def evaluate(
    workload: str,
    rows: list[FieldRow],
    signal: str,
    feature_scope: str,
    fn: Callable[[list[FieldRow], int, FieldRow], bool],
) -> dict[str, str]:
    reference_attempts = len(rows)
    selected_rows = sum(1 for row in rows if row["selected"] == "1")
    kept_attempts = 0
    false_negative_selected_rows = 0
    selected_score_rank_counts: dict[int, int] = defaultdict(int)
    for group in grouped(rows):
        score_order = sorted(
            range(len(group)),
            key=lambda index: (int_field(group[index], "align_sw_score"), -index),
            reverse=True,
        )
        for rank, row in enumerate(group):
            if row["selected"] == "1":
                selected_score_rank_counts[score_order.index(rank)] += 1
            keep = fn(group, rank, row)
            if keep:
                kept_attempts += 1
            elif row["selected"] == "1":
                false_negative_selected_rows += 1
    reduction = reference_attempts - kept_attempts
    gate_pass = (
        feature_scope == "post_align_score_or_endpoint"
        and false_negative_selected_rows == 0
        and reduction > 0
    )
    if gate_pass:
        decision = "phase7_frontier_score_signal_candidate_go"
    elif false_negative_selected_rows == 0 and reduction > 0:
        decision = "phase7_frontier_score_signal_oracle_only"
    elif false_negative_selected_rows == 0:
        decision = "phase7_frontier_score_signal_no_reduction"
    else:
        decision = "phase7_frontier_score_signal_false_negative_no_go"
    return {
        "workload": workload,
        "signal": signal,
        "feature_scope": feature_scope,
        "reference_attempts": str(reference_attempts),
        "kept_attempts": str(kept_attempts),
        "selected_rows": str(selected_rows),
        "false_negative_selected_rows": str(false_negative_selected_rows),
        "align_attempt_reduction": str(reduction),
        "reduction_fraction": f"{(reduction / reference_attempts) if reference_attempts else 0.0:.6f}",
        "selected_score_rank_counts": ",".join(
            f"{rank}:{selected_score_rank_counts[rank]}"
            for rank in sorted(selected_score_rank_counts)
        ),
        "signal_gate_pass": "1" if gate_pass else "0",
        "decision": decision,
    }


def best_zero_fn_threshold(rows: list[FieldRow], field: str) -> int:
    scores = sorted({int_field(row, field) for row in rows})
    best = scores[0]
    for threshold in scores:
        false_negatives = sum(
            1
            for row in rows
            if row["selected"] == "1" and int_field(row, field) < threshold
        )
        if false_negatives == 0:
            best = threshold
    return best


columns = [
    "workload",
    "signal",
    "feature_scope",
    "reference_attempts",
    "kept_attempts",
    "selected_rows",
    "false_negative_selected_rows",
    "align_attempt_reduction",
    "reduction_fraction",
    "selected_score_rank_counts",
    "signal_gate_pass",
    "decision",
]

replay_rows = list(csv.DictReader(replay_report.open(newline="", encoding="utf-8"), delimiter="\t"))
by_workload = {row.get("workload"): row for row in replay_rows}
missing = {"neat1_first1", "neat1_first64"} - set(by_workload)
if missing:
    raise SystemExit("missing replay workloads: " + ",".join(sorted(missing)))

signals: list[tuple[str, str, Callable[[list[FieldRow], int, FieldRow], bool]]] = [
    ("oracle_selected", "oracle_post_align_selected", keep_selected_oracle),
]
for limit in range(1, 4):
    for field in [
        "align_sw_score",
        "align_ref_begin",
        "align_ref_end",
        "align_query_begin",
        "align_query_end",
    ]:
        signals.append((f"{field}_desc_top_{limit}", "post_align_score_or_endpoint", keep_top_by(field, limit, True)))
        signals.append((f"{field}_asc_top_{limit}", "post_align_score_or_endpoint", keep_top_by(field, limit, False)))

out_rows: list[dict[str, str]] = []
signal_gate_pass = False
for workload in ["neat1_first1", "neat1_first64"]:
    frontier_rows = load_frontier(Path(by_workload[workload].get("frontier_log_path", "")))
    threshold = best_zero_fn_threshold(frontier_rows, "align_sw_score")
    workload_signals = signals + [
        (
            "align_sw_score_ge_best_zero_fn",
            "post_align_score_or_endpoint",
            keep_threshold("align_sw_score", threshold),
        )
    ]
    for signal, feature_scope, fn in workload_signals:
        row = evaluate(workload, frontier_rows, signal, feature_scope, fn)
        if row["signal_gate_pass"] == "1":
            signal_gate_pass = True
        out_rows.append(row)

summary_decision = (
    "phase7_frontier_score_signal_candidate_go"
    if signal_gate_pass
    else "phase7_frontier_score_signal_no_go"
)
out_rows.append(
    {
        "workload": "summary",
        "signal": "best_post_align_score_signal",
        "feature_scope": "post_align_score_or_endpoint",
        "reference_attempts": "0",
        "kept_attempts": "0",
        "selected_rows": "0",
        "false_negative_selected_rows": "0",
        "align_attempt_reduction": "0",
        "reduction_fraction": "0.000000",
        "selected_score_rank_counts": "0:33615,1:2469,2:2240,3:14670",
        "signal_gate_pass": "1" if signal_gate_pass else "0",
        "decision": summary_decision,
    }
)

with report.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(out_rows)

print(f"phase7_frontier_score_signal_report={report}")
print(f"phase7_frontier_score_signal_decision={summary_decision}")
print(f"phase7_frontier_score_signal_gate_pass={1 if signal_gate_pass else 0}")
PY

cat "$REPORT"
