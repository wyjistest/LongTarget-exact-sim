#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for arg in "$@"; do
  case "$arg" in
    *=*)
      export "$arg"
      ;;
    *)
      echo "unexpected argument: $arg" >&2
      exit 1
      ;;
  esac
done

BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_long_query_segmented_shadow"}"
BUILD_BIN="${BUILD_BIN:-1}"
RULE="${RULE:-0}"
K="${K:-5}"
TILE_LEN="${TILE_LEN:-2812}"
TILE_OVERLAP="${TILE_OVERLAP:-512}"
MAX_SEGMENTS="${MAX_SEGMENTS:-4}"
SCORE_PREPASS_SHADOW="${SCORE_PREPASS_SHADOW:-0}"
SCOREINFO_MAX_PER_TASK="${SCOREINFO_MAX_PER_TASK:-0}"
SCOREINFO_PRUNE_MODE="${SCOREINFO_PRUNE_MODE:-score}"
SEGMENTED_MAX_TASKS="${SEGMENTED_MAX_TASKS:-0}"
CPU_TRACEBACK_REPLAY="${CPU_TRACEBACK_REPLAY:-0}"
CPU_TRACEBACK_NO_LAST="${CPU_TRACEBACK_NO_LAST:-0}"
CPU_TRACEBACK_THRESHOLD_LAST="${CPU_TRACEBACK_THRESHOLD_LAST:-0}"
CPU_TRACEBACK_ORDER="${CPU_TRACEBACK_ORDER:-legacy}"
MALAT1_RECORD_LIMIT="${MALAT1_RECORD_LIMIT:-8}"
MALAT1_RNA="${MALAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1.fa"}"
MALAT1_DNA="${MALAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/MALAT1/MALAT1-DNAseq.fa"}"

if [[ "$K" != "5" ]]; then
  echo "segmented shadow probe requires K=5" >&2
  exit 1
fi
if [[ "$TILE_LEN" -le 0 ]]; then
  echo "TILE_LEN must be positive" >&2
  exit 1
fi
if [[ "$TILE_OVERLAP" -lt 0 || "$TILE_OVERLAP" -ge "$TILE_LEN" ]]; then
  echo "TILE_OVERLAP must be >=0 and < TILE_LEN" >&2
  exit 1
fi
if [[ "$MAX_SEGMENTS" -lt 0 ]]; then
  echo "MAX_SEGMENTS must be >=0" >&2
  exit 1
fi
if [[ "$SCOREINFO_MAX_PER_TASK" -lt 0 ]]; then
  echo "SCOREINFO_MAX_PER_TASK must be >=0" >&2
  exit 1
fi
if [[ "$SEGMENTED_MAX_TASKS" -lt 0 ]]; then
  echo "SEGMENTED_MAX_TASKS must be >=0" >&2
  exit 1
fi
if [[ "$CPU_TRACEBACK_REPLAY" -lt 0 ]]; then
  echo "CPU_TRACEBACK_REPLAY must be >=0" >&2
  exit 1
fi
if [[ "$CPU_TRACEBACK_NO_LAST" -lt 0 ]]; then
  echo "CPU_TRACEBACK_NO_LAST must be >=0" >&2
  exit 1
fi
if [[ "$CPU_TRACEBACK_THRESHOLD_LAST" -lt 0 ]]; then
  echo "CPU_TRACEBACK_THRESHOLD_LAST must be >=0" >&2
  exit 1
fi
if [[ "$MALAT1_RECORD_LIMIT" -le 0 ]]; then
  echo "MALAT1_RECORD_LIMIT must be positive" >&2
  exit 1
fi

if [[ "$BUILD_BIN" == "1" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
elif [[ ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi

rm -rf "$WORK"
mkdir -p "$WORK/inputs"

if [[ ! -s "$MALAT1_RNA" ]]; then
  echo "missing MALAT1 RNA: $MALAT1_RNA" >&2
  exit 1
fi
if [[ ! -s "$MALAT1_DNA" ]]; then
  echo "missing MALAT1 DNA: $MALAT1_DNA" >&2
  exit 1
fi

target_label="malat1_first${MALAT1_RECORD_LIMIT}"
MALAT1_SAMPLE="$WORK/inputs/${target_label}.fa"
awk -v limit="$MALAT1_RECORD_LIMIT" '
  /^>/ {
    ++records
  }
  records <= limit {
    print
  }
' "$MALAT1_DNA" >"$MALAT1_SAMPLE"

query_len="$(
  awk '
    /^>/ { next }
    {
      gsub(/[[:space:]]/, "")
      len += length($0)
    }
    END { print len + 0 }
  ' "$MALAT1_RNA"
)"

segments="$(
  awk -v query_len="$query_len" -v tile_len="$TILE_LEN" \
      -v overlap="$TILE_OVERLAP" -v max_segments="$MAX_SEGMENTS" '
    BEGIN {
      step = tile_len - overlap
      if (query_len <= 0 || tile_len <= 0 || step <= 0) {
        print 0
        exit
      }
      start = 0
      count = 0
      while (start < query_len) {
        if (max_segments > 0 && count >= max_segments) {
          break
        }
        ++count
        if (start + tile_len >= query_len) {
          break
        }
        start += step
      }
      print count
    }
  '
)"

run_dir="$WORK/$target_label"
cpu_dir="$run_dir/cpu"
candidate_dir="$run_dir/segmented_shadow"
mkdir -p "$cpu_dir" "$candidate_dir"

cpu_start_seconds="$(date +%s.%N)"
env \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  "$BIN" \
  -f1 "$MALAT1_SAMPLE" \
  -f2 "$MALAT1_RNA" \
  -r "$RULE" \
  -O "$cpu_dir" \
  >"$cpu_dir/stdout.log" 2>"$cpu_dir/stderr.log"
cpu_end_seconds="$(date +%s.%N)"
baseline_wall_seconds="$(awk -v start="$cpu_start_seconds" -v end="$cpu_end_seconds" 'BEGIN {printf "%.6f", end - start}')"

candidate_start_seconds="$(date +%s.%N)"
env \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW=1 \
  FASIM_TOP5_GASAL2_LONG_QUERY_TILE_LEN="$TILE_LEN" \
  FASIM_TOP5_GASAL2_LONG_QUERY_TILE_OVERLAP="$TILE_OVERLAP" \
  FASIM_TOP5_GASAL2_LONG_QUERY_MAX_SEGMENTS="$MAX_SEGMENTS" \
  FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCORE_PREPASS_SHADOW="$SCORE_PREPASS_SHADOW" \
  FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_MAX_PER_TASK="$SCOREINFO_MAX_PER_TASK" \
  FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_PRUNE_MODE="$SCOREINFO_PRUNE_MODE" \
  FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_MAX_TASKS="$SEGMENTED_MAX_TASKS" \
  FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_CPU_TRACEBACK_REPLAY="$CPU_TRACEBACK_REPLAY" \
  FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_CPU_TRACEBACK_ORDER="$CPU_TRACEBACK_ORDER" \
  FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST="$CPU_TRACEBACK_NO_LAST" \
  FASIM_ALIGN_GASAL2_CPU_TRACEBACK_THRESHOLD_LAST="$CPU_TRACEBACK_THRESHOLD_LAST" \
  "$BIN" \
  -f1 "$MALAT1_SAMPLE" \
  -f2 "$MALAT1_RNA" \
  -r "$RULE" \
  -O "$candidate_dir" \
  >"$candidate_dir/stdout.log" 2>"$candidate_dir/stderr.log"
candidate_end_seconds="$(date +%s.%N)"
candidate_wall_seconds="$(awk -v start="$candidate_start_seconds" -v end="$candidate_end_seconds" 'BEGIN {printf "%.6f", end - start}')"

cpu_out="$(find "$cpu_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
candidate_out="$(find "$candidate_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$cpu_out" || -z "$candidate_out" ]]; then
  echo "expected lite outputs missing for $target_label" >&2
  exit 1
fi

compare_status=0
python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
  --baseline "$cpu_out" \
  --candidate "$candidate_out" \
  --k "$K" \
  >"$run_dir/top5_compare.txt" || compare_status=$?
if [[ "$compare_status" -gt 1 ]]; then
  echo "top5 compare failed with status $compare_status" >&2
  exit "$compare_status"
fi

metric() {
  local key="$1"
  local default_value="${2:-0}"
  local value
  value="$(awk -F= -v key="$key" '$1 == key {print $2}' "$candidate_dir/stderr.log")"
  printf '%s' "${value:-$default_value}"
}

metric_required() {
  local key="$1"
  local value
  value="$(awk -F= -v key="$key" '$1 == key {print $2}' "$candidate_dir/stderr.log")"
  if [[ -z "$value" ]]; then
    echo "missing segmented shadow metric: $key" >&2
    exit 1
  fi
  printf '%s' "$value"
}

requested="$(metric benchmark.fasim_top5_gasal2_long_query_segmented_shadow_requested 0)"
active="$(metric benchmark.fasim_top5_gasal2_long_query_segmented_shadow_active 0)"
telemetry_query_len="$(metric_required benchmark.fasim_top5_gasal2_long_query_segmented_shadow_query_len)"
telemetry_tile_len="$(metric_required benchmark.fasim_top5_gasal2_long_query_segmented_shadow_tile_len)"
telemetry_tile_overlap="$(metric_required benchmark.fasim_top5_gasal2_long_query_segmented_shadow_tile_overlap)"
telemetry_segments="$(metric_required benchmark.fasim_top5_gasal2_long_query_segmented_shadow_segments)"
telemetry_gasal2_requests="$(metric_required benchmark.fasim_top5_gasal2_long_query_segmented_shadow_gasal2_requests)"
telemetry_traceback_requests="$(metric_required benchmark.fasim_top5_gasal2_long_query_segmented_shadow_traceback_requests)"
telemetry_fallbacks="$(metric_required benchmark.fasim_top5_gasal2_long_query_segmented_shadow_fallbacks)"
telemetry_total_seconds="$(metric_required benchmark.fasim_top5_gasal2_long_query_segmented_shadow_total_seconds)"
telemetry_scoreinfo_max_per_task="$(metric benchmark.fasim_top5_gasal2_long_query_segmented_shadow_scoreinfo_max_per_task 0)"
telemetry_scoreinfo_prune_mode="$(metric benchmark.fasim_top5_gasal2_long_query_segmented_shadow_scoreinfo_prune_mode score)"
telemetry_scoreinfo_input_groups="$(metric benchmark.fasim_top5_gasal2_long_query_segmented_shadow_scoreinfo_input_groups 0)"
telemetry_scoreinfo_kept_groups="$(metric benchmark.fasim_top5_gasal2_long_query_segmented_shadow_scoreinfo_kept_groups 0)"
telemetry_scoreinfo_pruned_groups="$(metric benchmark.fasim_top5_gasal2_long_query_segmented_shadow_scoreinfo_pruned_groups 0)"
telemetry_gasal2_batches="$(metric benchmark.fasim_gasal2_batches 0)"
telemetry_gasal2_score_batches="$(metric benchmark.fasim_gasal2_score_batches 0)"
telemetry_gasal2_score_wait_seconds="$(metric benchmark.fasim_gasal2_score_wait_seconds 0)"
telemetry_cpu_replay_attempts="$(metric benchmark.fasim_gasal2_cpu_traceback_replay_attempts 0)"
telemetry_cpu_replay_selected="$(metric benchmark.fasim_gasal2_cpu_traceback_selected_attempts 0)"
telemetry_cpu_replay_align_calls="$(metric benchmark.fasim_gasal2_cpu_traceback_align_calls 0)"
baseline_rows="$(awk -F= '/^baseline_rows=/{print $2}' "$run_dir/top5_compare.txt")"
candidate_rows="$(awk -F= '/^candidate_rows=/{print $2}' "$run_dir/top5_compare.txt")"
missing_rows="$(awk -F= '/^missing_rows=/{print $2}' "$run_dir/top5_compare.txt")"
extra_rows="$(awk -F= '/^extra_rows=/{print $2}' "$run_dir/top5_compare.txt")"
top5_score_equal="$(awk -F= '/^top5_score_equal=/{print $2}' "$run_dir/top5_compare.txt")"
top5_stability_equal="$(awk -F= '/^top5_stability_equal=/{print $2}' "$run_dir/top5_compare.txt")"
top5_nt_score_equal="$(awk -F= '/^top5_nt_score_equal=/{print $2}' "$run_dir/top5_compare.txt")"
speedup_vs_baseline="$(awk -v base="$baseline_wall_seconds" -v cand="$candidate_wall_seconds" 'BEGIN {if (cand > 0) printf "%.6f", base / cand; else print "nan"}')"

decision="not_implemented"
if [[ "$active" != "0" ]]; then
  if [[ "$top5_score_equal" == "true" &&
        "$top5_stability_equal" == "true" &&
        "$top5_nt_score_equal" == "true" &&
        "$telemetry_fallbacks" == "0" ]] &&
      awk -v gpu="$telemetry_total_seconds" -v cpu="$baseline_wall_seconds" \
        'BEGIN {exit !(gpu > 0 && gpu < cpu)}'; then
    decision="top5_artifact_go"
  else
    decision="top5_artifact_no_go"
  fi
fi

summary="$WORK/summary.tsv"
printf '%s\n' \
  "decision	label	target_record_limit	query_len	tile_len	tile_overlap	max_segments	segments	requested	active	gasal2_requests	traceback_requests	fallbacks	shadow_total_seconds	scoreinfo_max_per_task	scoreinfo_prune_mode	scoreinfo_input_groups	scoreinfo_kept_groups	scoreinfo_pruned_groups	gasal2_batches	gasal2_score_batches	gasal2_score_wait_seconds	cpu_traceback_no_last	cpu_traceback_threshold_last	cpu_traceback_order	cpu_replay_attempts	cpu_replay_selected	cpu_replay_align_calls	baseline_rows	candidate_rows	missing_rows	extra_rows	top5_score_equal	top5_stability_equal	top5_nt_score_equal	baseline_wall_seconds	candidate_wall_seconds	speedup_vs_baseline	run_dir" \
  >"$summary"
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$decision" \
  "$target_label" \
  "$MALAT1_RECORD_LIMIT" \
  "$telemetry_query_len" \
  "$telemetry_tile_len" \
  "$telemetry_tile_overlap" \
  "$MAX_SEGMENTS" \
  "$telemetry_segments" \
  "$requested" \
  "$active" \
  "$telemetry_gasal2_requests" \
  "$telemetry_traceback_requests" \
  "$telemetry_fallbacks" \
  "$telemetry_total_seconds" \
  "$telemetry_scoreinfo_max_per_task" \
  "$telemetry_scoreinfo_prune_mode" \
  "$telemetry_scoreinfo_input_groups" \
  "$telemetry_scoreinfo_kept_groups" \
  "$telemetry_scoreinfo_pruned_groups" \
  "$telemetry_gasal2_batches" \
  "$telemetry_gasal2_score_batches" \
  "$telemetry_gasal2_score_wait_seconds" \
  "$CPU_TRACEBACK_NO_LAST" \
  "$CPU_TRACEBACK_THRESHOLD_LAST" \
  "$CPU_TRACEBACK_ORDER" \
  "$telemetry_cpu_replay_attempts" \
  "$telemetry_cpu_replay_selected" \
  "$telemetry_cpu_replay_align_calls" \
  "$baseline_rows" \
  "$candidate_rows" \
  "$missing_rows" \
  "$extra_rows" \
  "$top5_score_equal" \
  "$top5_stability_equal" \
  "$top5_nt_score_equal" \
  "$baseline_wall_seconds" \
  "$candidate_wall_seconds" \
  "$speedup_vs_baseline" \
  "$run_dir" \
  >>"$summary"

cat "$summary"
