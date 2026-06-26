#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_reducer"}"
REPLAY_WORK="${REPLAY_WORK:-"$WORK/replay"}"
REPLAY_REPORT="${REPLAY_REPORT:-"$REPLAY_WORK/report.tsv"}"
GLOBAL_REPLAY_REPORT="${GLOBAL_REPLAY_REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_replay/report.tsv"}"
RUN_REPLAY="${RUN_REPLAY:-auto}"

if [[ "$RUN_REPLAY" == "auto" ]]; then
  if [[ -s "$REPLAY_REPORT" ]]; then
    RUN_REPLAY=0
  elif [[ -s "$GLOBAL_REPLAY_REPORT" ]]; then
    REPLAY_REPORT="$GLOBAL_REPLAY_REPORT"
    RUN_REPLAY=0
  else
    RUN_REPLAY=1
  fi
fi

if [[ "$RUN_REPLAY" == "1" ]]; then
  WORK="$REPLAY_WORK" \
    bash "${ROOT}/scripts/characterize_fasim_gasal2_phase7_frontier_replay.sh"
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
import re
import sys
from pathlib import Path

replay_report = Path(sys.argv[1])
report = Path(sys.argv[2])


def parse_wall_seconds(path: Path) -> float:
    if not path.is_file():
        return 0.0
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^Running time is\s+([0-9.]+)$", text, flags=re.MULTILINE)
    return float(match.group(1)) if match else 0.0


columns = [
    "workload",
    "record_limit",
    "attempted",
    "digest_match",
    "full_rows_equal",
    "missing_rows",
    "extra_rows",
    "triplex_mismatches",
    "false_negative_scoreinfos",
    "candidate_align_attempts",
    "reference_align_attempts",
    "align_attempt_reduction",
    "frontier_log_rows",
    "frontier_selected_rows",
    "selected_rows",
    "candidate_wall_seconds",
    "baseline_wall_seconds",
    "candidate_vs_baseline",
    "wall_time_basis",
    "broad_gate_pass",
    "frontier_log_path",
    "reducer_output_basis",
    "decision",
    "decision_reasons",
    "run_dir",
]

rows = list(csv.DictReader(replay_report.open(newline="", encoding="utf-8"), delimiter="\t"))
if not rows:
    raise SystemExit("empty replay report")

out_rows: list[dict[str, str]] = []
for row in rows:
    workload = row.get("workload", "")
    if workload not in {"neat1_first1", "neat1_first64"}:
        continue

    reasons: list[str] = []
    attempted = row.get("attempted", "0")
    digest_match = row.get("digest_match", "0")
    full_rows_equal = row.get("full_rows_equal", "0")
    missing_rows = int(row.get("missing_rows", "0") or 0)
    extra_rows = int(row.get("extra_rows", "0") or 0)
    triplex_mismatches = int(row.get("triplex_mismatches", "0") or 0)
    false_negative_scoreinfos = int(row.get("false_negative_scoreinfos", "0") or 0)
    reference_attempts = int(row.get("reference_align_attempts", "0") or 0)
    frontier_log_rows = int(row.get("frontier_log_rows", "0") or 0)
    frontier_selected_rows = int(row.get("frontier_selected_rows", "0") or 0)

    candidate_attempts = frontier_selected_rows
    align_reduction = reference_attempts - candidate_attempts
    baseline_wall = parse_wall_seconds(Path(row.get("run_dir", "")) / "baseline" / "stdout.log")

    if attempted != "1":
        reasons.append("not_attempted")
    if digest_match != "1" and full_rows_equal != "1":
        reasons.append("replay_output_not_equal")
    if missing_rows != 0:
        reasons.append("missing_rows")
    if extra_rows != 0:
        reasons.append("extra_rows")
    if triplex_mismatches != 0:
        reasons.append("triplex_mismatches")
    if false_negative_scoreinfos != 0:
        reasons.append("false_negative_scoreinfos")
    if reference_attempts <= 0:
        reasons.append("no_reference_align_attempts")
    if frontier_log_rows <= 0:
        reasons.append("no_frontier_log_rows")
    if frontier_selected_rows <= 0:
        reasons.append("no_selected_frontier_rows")
    if candidate_attempts >= reference_attempts:
        reasons.append("no_align_attempt_reduction")

    # This is an oracle upper-bound characterization: selected frontier rows
    # are known only after CPU Align in the current log. Do not treat it as a
    # measured runtime reducer or broad completion proof.
    reasons.append("oracle_selected_rows_require_future_predictor")
    reasons.append("no_measured_runtime_reducer")

    correctness_and_reduction_clean = (
        attempted == "1"
        and (digest_match == "1" or full_rows_equal == "1")
        and missing_rows == 0
        and extra_rows == 0
        and triplex_mismatches == 0
        and false_negative_scoreinfos == 0
        and reference_attempts > 0
        and candidate_attempts > 0
        and candidate_attempts < reference_attempts
    )
    decision = (
        "phase7_frontier_reducer_exact_reduction_projected"
        if correctness_and_reduction_clean
        else "phase7_frontier_reducer_no_go"
    )

    out_rows.append(
        {
            "workload": workload,
            "record_limit": row.get("record_limit", ""),
            "attempted": attempted,
            "digest_match": digest_match,
            "full_rows_equal": full_rows_equal,
            "missing_rows": str(missing_rows),
            "extra_rows": str(extra_rows),
            "triplex_mismatches": str(triplex_mismatches),
            "false_negative_scoreinfos": str(false_negative_scoreinfos),
            "candidate_align_attempts": str(candidate_attempts),
            "reference_align_attempts": str(reference_attempts),
            "align_attempt_reduction": str(align_reduction),
            "frontier_log_rows": str(frontier_log_rows),
            "frontier_selected_rows": str(frontier_selected_rows),
            "selected_rows": str(frontier_selected_rows),
            "candidate_wall_seconds": "0.000000",
            "baseline_wall_seconds": f"{baseline_wall:.6f}",
            "candidate_vs_baseline": "0.000000",
            "wall_time_basis": "oracle_projected",
            "broad_gate_pass": "0",
            "frontier_log_path": row.get("frontier_log_path", ""),
            "reducer_output_basis": "frontier_replay_output_equal",
            "decision": decision,
            "decision_reasons": ",".join(reasons) if reasons else "none",
            "run_dir": row.get("run_dir", ""),
        }
    )

missing_workloads = {"neat1_first1", "neat1_first64"} - {row["workload"] for row in out_rows}
if missing_workloads:
    raise SystemExit("missing replay rows: " + ",".join(sorted(missing_workloads)))

with report.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(out_rows)

print(f"phase7_frontier_reducer_report={report}")
for row in out_rows:
    print(f"phase7_frontier_reducer_{row['workload']}_decision={row['decision']}")
    print(
        f"phase7_frontier_reducer_{row['workload']}_align_attempts="
        f"{row['candidate_align_attempts']}/{row['reference_align_attempts']}"
    )
PY

cat "$REPORT"
