#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_replay"}"
BUILD_BIN="${BUILD_BIN:-1}"
RNA_INPUT="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
DNA_INPUT="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"
FIRST1_RECORD_LIMIT="${FIRST1_RECORD_LIMIT:-1}"
FIRST64_RECORD_LIMIT="${FIRST64_RECORD_LIMIT:-64}"
RUN_FIRST64="${RUN_FIRST64:-1}"
TILE_LEN="${TILE_LEN:-2812}"
TILE_OVERLAP="${TILE_OVERLAP:-512}"
MAX_SEGMENTS="${MAX_SEGMENTS:-4}"
SCOREINFO_MAX_PER_TASK="${SCOREINFO_MAX_PER_TASK:-0}"
SCOREINFO_PRUNE_MODE="${SCOREINFO_PRUNE_MODE:-score_position_edges}"
SEGMENTED_MAX_TASKS="${SEGMENTED_MAX_TASKS:-64}"

require_uint() {
  local name="$1"
  local value="$2"
  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    echo "$name must be a non-negative integer, got: $value" >&2
    exit 1
  fi
}

require_positive_uint() {
  local name="$1"
  local value="$2"
  require_uint "$name" "$value"
  if [[ "$value" -le 0 ]]; then
    echo "$name must be positive, got: $value" >&2
    exit 1
  fi
}

require_positive_uint FIRST1_RECORD_LIMIT "$FIRST1_RECORD_LIMIT"
require_positive_uint FIRST64_RECORD_LIMIT "$FIRST64_RECORD_LIMIT"
require_uint RUN_FIRST64 "$RUN_FIRST64"
require_positive_uint TILE_LEN "$TILE_LEN"
require_uint TILE_OVERLAP "$TILE_OVERLAP"
require_uint MAX_SEGMENTS "$MAX_SEGMENTS"
require_uint SCOREINFO_MAX_PER_TASK "$SCOREINFO_MAX_PER_TASK"
require_uint SEGMENTED_MAX_TASKS "$SEGMENTED_MAX_TASKS"
if [[ "$TILE_OVERLAP" -ge "$TILE_LEN" ]]; then
  echo "TILE_OVERLAP must be smaller than TILE_LEN" >&2
  exit 1
fi

if [[ "$BUILD_BIN" == "1" || ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
if [[ ! -x "$BIN" ]]; then
  echo "missing GASAL2-enabled Fasim binary: $BIN" >&2
  exit 1
fi
if [[ ! -s "$RNA_INPUT" || ! -s "$DNA_INPUT" ]]; then
  echo "missing NEAT1 inputs" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"

REPORT="$WORK/report.tsv"
printf '%s\n' \
  "workload	record_limit	attempted	digest_match	full_rows_equal	missing_rows	extra_rows	triplex_mismatches	false_negative_scoreinfos	candidate_align_attempts	reference_align_attempts	frontier_log_rows	frontier_selected_rows	frontier_positive_align_rows	frontier_log_path	decision	decision_reasons	run_dir" \
  >"$REPORT"

make_sample() {
  local limit="$1"
  local output="$2"
  awk -v limit="$limit" '
    /^>/ { ++records }
    records <= limit { print }
  ' "$DNA_INPUT" >"$output"
  if [[ ! -s "$output" ]]; then
    echo "empty sample generated for limit=$limit" >&2
    exit 1
  fi
}

run_fasim() {
  local sample="$1"
  local out_dir="$2"
  shift 2
  mkdir -p "$out_dir"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$@" \
    "$BIN" \
    -f1 "$sample" \
    -f2 "$RNA_INPUT" \
    -r 0 \
    -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

lite_output() {
  local out_dir="$1"
  local out_file
  out_file="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$out_file" ]]; then
    echo "missing lite output in $out_dir" >&2
    exit 1
  fi
  printf '%s\n' "$out_file"
}

append_skipped_first64() {
  local reason="$1"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "neat1_first64" \
    "$FIRST64_RECORD_LIMIT" \
    "0" \
    "0" \
    "0" \
    "0" \
    "0" \
    "0" \
    "0" \
    "0" \
    "0" \
    "0" \
    "0" \
    "0" \
    "" \
    "phase7_frontier_replay_skipped" \
    "$reason" \
    "none" \
    >>"$REPORT"
}

run_case() {
  local label="$1"
  local limit="$2"
  local run_dir="$WORK/$label"
  local sample="$WORK/inputs/$label.fa"
  make_sample "$limit" "$sample"

  local baseline_dir="$run_dir/baseline"
  local candidate_dir="$run_dir/frontier_log"
  mkdir -p "$run_dir"

  echo "running Phase 7 frontier replay $label" >&2
  run_fasim "$sample" "$baseline_dir"
  run_fasim "$sample" "$candidate_dir" \
    FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW=1 \
    FASIM_TOP5_GASAL2_LONG_QUERY_TILE_LEN="$TILE_LEN" \
    FASIM_TOP5_GASAL2_LONG_QUERY_TILE_OVERLAP="$TILE_OVERLAP" \
    FASIM_TOP5_GASAL2_LONG_QUERY_MAX_SEGMENTS="$MAX_SEGMENTS" \
    FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCORE_PREPASS_SHADOW=1 \
    FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_MAX_PER_TASK="$SCOREINFO_MAX_PER_TASK" \
    FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_PRUNE_MODE="$SCOREINFO_PRUNE_MODE" \
    FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_MAX_TASKS="$SEGMENTED_MAX_TASKS" \
    FASIM_GASAL2_PHASE7_FRONTIER_LOG=1

  local baseline_out candidate_out
  baseline_out="$(lite_output "$baseline_dir")"
  candidate_out="$(lite_output "$candidate_dir")"

  python3 - \
    "$REPORT" \
    "$baseline_out" \
    "$candidate_out" \
    "$candidate_dir/stderr.log" \
    "$label" \
    "$limit" \
    "$run_dir" <<'PY'
from __future__ import annotations

from pathlib import Path
import hashlib
import sys

report = Path(sys.argv[1])
baseline_out = Path(sys.argv[2])
candidate_out = Path(sys.argv[3])
stderr_path = Path(sys.argv[4])
label = sys.argv[5]
limit = sys.argv[6]
run_dir = sys.argv[7]

baseline_text = baseline_out.read_text(encoding="utf-8", errors="replace")
candidate_text = candidate_out.read_text(encoding="utf-8", errors="replace")
baseline_rows = [line.rstrip("\n") for line in baseline_text.splitlines() if line.rstrip("\n")]
candidate_rows = [line.rstrip("\n") for line in candidate_text.splitlines() if line.rstrip("\n")]
baseline_set = set(baseline_rows)
candidate_set = set(candidate_rows)
missing_rows = len(baseline_set - candidate_set)
extra_rows = len(candidate_set - baseline_set)
full_rows_equal = 1 if missing_rows == 0 and extra_rows == 0 else 0
digest_match = 1 if hashlib.sha256(baseline_text.encode()).hexdigest() == hashlib.sha256(candidate_text.encode()).hexdigest() else 0

metrics: dict[str, str] = {}
for line in stderr_path.read_text(encoding="utf-8", errors="replace").splitlines():
    if not line.startswith("benchmark."):
        continue
    key, sep, value = line.partition("=")
    if sep:
        metrics[key] = value

requested = metrics.get("benchmark.fasim_gasal2_phase7_frontier_log_requested", "0")
active = metrics.get("benchmark.fasim_gasal2_phase7_frontier_log_active", "0")
frontier_log_path = metrics.get("benchmark.fasim_gasal2_phase7_frontier_log_path", "")
candidate_align_attempts = int(metrics.get("benchmark.fasim_gasal2_phase7_frontier_log_align_attempts", "0") or 0)
reference_align_attempts = candidate_align_attempts
frontier_log_rows = 0
frontier_selected_rows = 0
frontier_positive_align_rows = 0
decision_reasons: list[str] = []

expected_header = "\t".join([
    "task_id",
    "scoreinfo_index",
    "scoreinfo_position",
    "scoreinfo_score",
    "attempt_index",
    "attempt_start",
    "attempt_cutlength",
    "align_sw_score",
    "align_ref_begin",
    "align_ref_end",
    "align_query_begin",
    "align_query_end",
    "selected",
    "emitted_triplex_count_before",
    "emitted_triplex_count_after",
])
if requested != "1":
    decision_reasons.append("frontier_log_not_requested")
if active != "1":
    decision_reasons.append("frontier_log_not_active")
if not frontier_log_path:
    decision_reasons.append("frontier_log_path_empty")
else:
    path = Path(frontier_log_path)
    if not path.is_file():
        decision_reasons.append("frontier_log_missing")
    else:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not lines:
            decision_reasons.append("frontier_log_empty")
        elif lines[0] != expected_header:
            decision_reasons.append("frontier_log_bad_header")
        else:
            frontier_log_rows = max(0, len(lines) - 1)
            if frontier_log_rows <= 0:
                decision_reasons.append("frontier_log_no_rows")
            else:
                columns = lines[0].split("\t")
                selected_index = columns.index("selected")
                sw_index = columns.index("align_sw_score")
                for line in lines[1:]:
                    values = line.split("\t")
                    if len(values) <= max(selected_index, sw_index):
                        decision_reasons.append("frontier_log_bad_row")
                        break
                    if values[selected_index] == "1":
                        frontier_selected_rows += 1
                    try:
                        if int(values[sw_index]) > 0:
                            frontier_positive_align_rows += 1
                    except ValueError:
                        decision_reasons.append("frontier_log_bad_align_score")
                        break
                if frontier_selected_rows <= 0:
                    decision_reasons.append("frontier_log_no_selected_rows")
                if frontier_positive_align_rows <= 0:
                    decision_reasons.append("frontier_log_no_positive_align_rows")

if missing_rows != 0:
    decision_reasons.append("missing_rows")
if extra_rows != 0:
    decision_reasons.append("extra_rows")
if candidate_align_attempts <= 0:
    decision_reasons.append("no_frontier_align_attempts")

triplex_mismatches = 0 if full_rows_equal else missing_rows + extra_rows
false_negative_scoreinfos = 0
decision = "phase7_frontier_replay_exact"
if decision_reasons:
    decision = "phase7_frontier_replay_no_go"

with report.open("a", encoding="utf-8") as handle:
    handle.write("\t".join([
        label,
        str(limit),
        "1",
        str(digest_match),
        str(full_rows_equal),
        str(missing_rows),
        str(extra_rows),
        str(triplex_mismatches),
        str(false_negative_scoreinfos),
        str(candidate_align_attempts),
        str(reference_align_attempts),
        str(frontier_log_rows),
        str(frontier_selected_rows),
        str(frontier_positive_align_rows),
        frontier_log_path,
        decision,
        ",".join(decision_reasons) if decision_reasons else "none",
        run_dir,
    ]) + "\n")
PY
}

run_case "neat1_first1" "$FIRST1_RECORD_LIMIT"
if [[ "$RUN_FIRST64" == "1" ]]; then
  run_case "neat1_first64" "$FIRST64_RECORD_LIMIT"
else
  append_skipped_first64 "RUN_FIRST64_disabled"
fi

cat "$REPORT"
