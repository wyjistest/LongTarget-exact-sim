#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_early_stop"}"
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
from collections import Counter, defaultdict
from pathlib import Path

replay_report = Path(sys.argv[1])
report = Path(sys.argv[2])


def load_frontier(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8"), delimiter="\t"))
    required = [
        "task_id",
        "scoreinfo_index",
        "selected",
        "emitted_triplex_count_before",
        "emitted_triplex_count_after",
    ]
    for row in rows:
        missing = [key for key in required if key not in row]
        if missing:
            raise SystemExit(f"{path}: missing columns {missing}")
    return rows


def characterize(workload: str, frontier_rows: list[dict[str, str]]) -> dict[str, str]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in frontier_rows:
        groups[(row["task_id"], row["scoreinfo_index"])].append(row)

    selected_rank_counts: Counter[int] = Counter()
    candidate_attempts = 0
    selected_rows = 0
    multi_selected_groups = 0
    no_selected_groups = 0
    skipped_after_selected_rows = 0
    unsafe_skipped_rows = 0
    false_negative_selected_rows = 0

    for rows in groups.values():
        selected = [index for index, row in enumerate(rows) if row["selected"] == "1"]
        selected_rows += len(selected)
        if len(selected) > 1:
            multi_selected_groups += 1
        if not selected:
            no_selected_groups += 1
            candidate_attempts += len(rows)
            continue

        selected_rank = selected[0]
        selected_rank_counts[selected_rank] += 1
        candidate_attempts += selected_rank + 1
        emitted_after = int(rows[selected_rank]["emitted_triplex_count_after"])
        for row in rows[selected_rank + 1:]:
            skipped_after_selected_rows += 1
            if row["selected"] == "1":
                false_negative_selected_rows += 1
            if (
                row["selected"] != "0"
                or int(row["emitted_triplex_count_before"]) != emitted_after
                or int(row["emitted_triplex_count_after"]) != emitted_after
            ):
                unsafe_skipped_rows += 1

    reference_attempts = len(frontier_rows)
    reduction = reference_attempts - candidate_attempts
    return {
        "workload": workload,
        "groups": str(len(groups)),
        "reference_attempts": str(reference_attempts),
        "candidate_align_attempts": str(candidate_attempts),
        "align_attempt_reduction": str(reduction),
        "reduction_fraction": f"{(reduction / reference_attempts) if reference_attempts else 0.0:.6f}",
        "selected_rows": str(selected_rows),
        "multi_selected_groups": str(multi_selected_groups),
        "no_selected_groups": str(no_selected_groups),
        "skipped_after_selected_rows": str(skipped_after_selected_rows),
        "unsafe_skipped_rows": str(unsafe_skipped_rows),
        "false_negative_selected_rows": str(false_negative_selected_rows),
        "selected_rank_counts": ",".join(
            f"{rank}:{selected_rank_counts[rank]}"
            for rank in sorted(selected_rank_counts)
        ),
        "runtime_candidate": "1",
        "measured_runtime": "0",
        "broad_gate_pass": "0",
        "decision": "phase7_frontier_early_stop_candidate_not_measured",
    }


columns = [
    "workload",
    "groups",
    "reference_attempts",
    "candidate_align_attempts",
    "align_attempt_reduction",
    "reduction_fraction",
    "selected_rows",
    "multi_selected_groups",
    "no_selected_groups",
    "skipped_after_selected_rows",
    "unsafe_skipped_rows",
    "false_negative_selected_rows",
    "selected_rank_counts",
    "runtime_candidate",
    "measured_runtime",
    "broad_gate_pass",
    "decision",
]

replay_rows = list(csv.DictReader(replay_report.open(newline="", encoding="utf-8"), delimiter="\t"))
by_workload = {row.get("workload"): row for row in replay_rows}
missing = {"neat1_first1", "neat1_first64"} - set(by_workload)
if missing:
    raise SystemExit("missing replay workloads: " + ",".join(sorted(missing)))

out_rows = []
for workload in ["neat1_first1", "neat1_first64"]:
    frontier_path = Path(by_workload[workload].get("frontier_log_path", ""))
    out_rows.append(characterize(workload, load_frontier(frontier_path)))

with report.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(out_rows)

print(f"phase7_frontier_early_stop_report={report}")
for row in out_rows:
    print(f"phase7_frontier_early_stop_{row['workload']}_decision={row['decision']}")
    print(
        f"phase7_frontier_early_stop_{row['workload']}_align_attempts="
        f"{row['candidate_align_attempts']}/{row['reference_attempts']}"
    )
PY

cat "$REPORT"
