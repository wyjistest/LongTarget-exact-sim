#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FIRST8="${FIRST8:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_replay_no_last/summary.tsv"}"
FIRST16="${FIRST16:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_replay_no_last_first16/summary.tsv"}"
FIRST32="${FIRST32:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_replay_no_last_first32/summary.tsv"}"
FIRST64="${FIRST64:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_replay_no_last_first64/summary.tsv"}"
FIRST128="${FIRST128:-"$ROOT/.tmp/check_fasim_gasal2_long_query_segmented_replay_no_last_first128/summary.tsv"}"
BOUNDARY_DOC="$ROOT/docs/fasim_gasal2_long_query_boundary.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"

for path in "$FIRST8" "$FIRST16" "$FIRST32" "$FIRST64" "$FIRST128" "$BOUNDARY_DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC"; do
  if [[ ! -s "$path" ]]; then
    echo "missing no-last scaling result artifact: $path" >&2
    echo "generate with check_fasim_gasal2_long_query_segmented_replay_no_last.sh using MALAT1_RECORD_LIMIT=8/16/32/64/128" >&2
    exit 1
  fi
done

python3 - "$FIRST8" "$FIRST16" "$FIRST32" "$FIRST64" "$FIRST128" "$BOUNDARY_DOC" "$CURRENT_STATE_DOC" "$COMPLETION_GAP_DOC" <<'PY'
import csv
import sys
from pathlib import Path

expected = {
    8: Path(sys.argv[1]),
    16: Path(sys.argv[2]),
    32: Path(sys.argv[3]),
    64: Path(sys.argv[4]),
    128: Path(sys.argv[5]),
}
boundary_doc = " ".join(Path(sys.argv[6]).read_text(encoding="utf-8").split())
current_state_doc = " ".join(Path(sys.argv[7]).read_text(encoding="utf-8").split())
completion_gap_doc = " ".join(Path(sys.argv[8]).read_text(encoding="utf-8").split())

previous_align_calls = 0
observed_speedups = {}
for record_limit, path in expected.items():
    rows = list(csv.DictReader(path.open(newline="", encoding="utf-8"), delimiter="\t"))
    if len(rows) != 1:
        raise SystemExit(f"{path}: expected one summary row, got {len(rows)}")
    row = rows[0]
    label = f"malat1_first{record_limit}"
    if row.get("label") != label:
        raise SystemExit(f"{path}: expected label {label}, got {row.get('label')}: {row}")
    required = {
        "decision": "top5_artifact_go",
        "target_record_limit": str(record_limit),
        "query_len": "8708",
        "tile_len": "2812",
        "tile_overlap": "512",
        "max_segments": "4",
        "segments": "4",
        "requested": "1",
        "active": "1",
        "traceback_requests": "0",
        "fallbacks": "0",
        "scoreinfo_max_per_task": "37",
        "scoreinfo_prune_mode": "score_position_edges",
        "cpu_traceback_no_last": "1",
        "cpu_traceback_threshold_last": "0",
        "top5_score_equal": "true",
        "top5_stability_equal": "true",
        "top5_nt_score_equal": "true",
    }
    for key, value in required.items():
        if row.get(key) != value:
            raise SystemExit(f"{path}: {key}={row.get(key)!r}, expected {value!r}: {row}")

    gasal2_requests = int(row.get("gasal2_requests", "0"))
    score_batches = int(row.get("gasal2_score_batches", "0"))
    align_calls = int(row.get("cpu_replay_align_calls", "0"))
    replay_attempts = int(row.get("cpu_replay_attempts", "0"))
    replay_selected = int(row.get("cpu_replay_selected", "0"))
    speedup = float(row.get("speedup_vs_baseline", "0"))
    baseline_wall = float(row.get("baseline_wall_seconds", "0"))
    candidate_wall = float(row.get("candidate_wall_seconds", "0"))

    if gasal2_requests <= 0 or score_batches <= 0:
        raise SystemExit(f"{path}: expected GASAL2 score-prepass work: {row}")
    if replay_attempts <= 0 or replay_selected <= 0 or align_calls <= 0:
        raise SystemExit(f"{path}: expected CPU replay work: {row}")
    if align_calls <= previous_align_calls:
        raise SystemExit(
            f"{path}: expected align calls to grow with record count, "
            f"got {align_calls} after {previous_align_calls}"
        )
    previous_align_calls = align_calls
    if not (baseline_wall > 0 and candidate_wall > 0):
        raise SystemExit(f"{path}: expected positive wall times: {row}")
    if not (1.0 < speedup < 1.1):
        raise SystemExit(
            f"{path}: no-last long-query speedup must remain marginal "
            f"(1.0 < speedup < 1.1), got {speedup}: {row}"
        )
    observed_speedups[record_limit] = speedup

for name, text in (
    ("boundary doc", boundary_doc),
    ("current-state doc", current_state_doc),
    ("completion-gap doc", completion_gap_doc),
):
    for phrase in (
        "malat1_first128 speedup",
        "1.038017x",
        "first8/first16/first32/first64/first128",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} missing first128 scaling phrase: {phrase}")

print("decision=long_query_no_last_scaling_marginal")
PY
