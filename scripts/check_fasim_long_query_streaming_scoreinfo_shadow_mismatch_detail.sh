#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_long_query_streaming_scoreinfo_shadow_mismatch_detail"}"
BUILD_BIN="${BUILD_BIN:-1}"
EXTRA_SHADOW_ENV="${EXTRA_SHADOW_ENV:-}"
EXPECTED_SCOREINFO_MISMATCHES="${EXPECTED_SCOREINFO_MISMATCHES:-1}"

WORK="$WORK" BIN="$BIN" BUILD_BIN="$BUILD_BIN" \
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_DEBUG_COLUMNS=1 \
  EXTRA_SHADOW_ENV="$EXTRA_SHADOW_ENV" \
  EXPECTED_SCOREINFO_MISMATCHES="$EXPECTED_SCOREINFO_MISMATCHES" \
  EXPECTED_DECISION=streaming_scoreinfo_shadow_mismatch \
  bash "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_shadow_active.sh" >/dev/null

candidate_dir="$WORK/candidate"

metric() {
  local key="$1"
  awk -F= -v key="$key" '$1 == key {print $2}' "$candidate_dir/stderr.log" | tail -n 1
}

scoreinfo_mismatches="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_scoreinfo_mismatches)"
first_task_index="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_task_index)"
first_global_task="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_global_task)"
first_diff_index="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_diff_index)"
first_kind="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_kind)"
cpu_count="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_cpu_count)"
gpu_count="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_gpu_count)"
cpu_score="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_cpu_score)"
cpu_position="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_cpu_position)"
gpu_score="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_gpu_score)"
gpu_position="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_gpu_position)"
task_rule="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_rule)"
task_strand="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_strand)"
task_para="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_para)"
task_dna_start_pos="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_dna_start_pos)"
task_target_len="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_target_len)"
task_min_score="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_min_score)"
column_window_start="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_column_window_start)"
cpu_column_window="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_cpu_column_window)"
gpu_column_window="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_gpu_column_window)"
scalar_column_window="$(metric benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_scalar_column_window)"

for value_name in \
  scoreinfo_mismatches first_task_index first_global_task first_diff_index first_kind \
  cpu_count gpu_count cpu_score cpu_position gpu_score gpu_position task_rule task_strand \
  task_para task_dna_start_pos task_target_len task_min_score column_window_start \
  cpu_column_window gpu_column_window scalar_column_window; do
  if [[ -z "${!value_name}" ]]; then
    echo "missing streaming scoreInfo mismatch detail metric: $value_name" >&2
    exit 1
  fi
done

if [[ "$scoreinfo_mismatches" != "$EXPECTED_SCOREINFO_MISMATCHES" ]]; then
  echo "expected mismatch checkpoint scoreinfo_mismatches=$EXPECTED_SCOREINFO_MISMATCHES, got $scoreinfo_mismatches" >&2
  exit 1
fi
if [[ "$first_task_index" -lt 0 || "$first_global_task" -lt 0 || "$first_diff_index" -lt 0 ]]; then
  echo "expected non-negative first mismatch indexes, got task=$first_task_index global=$first_global_task diff=$first_diff_index" >&2
  exit 1
fi
if [[ "$first_kind" != "count" && "$first_kind" != "score_position" ]]; then
  echo "unexpected first mismatch kind=$first_kind" >&2
  exit 1
fi
if [[ "$cpu_count" -lt 0 || "$gpu_count" -lt 0 || "$task_target_len" -le 0 ]]; then
  echo "expected non-negative first mismatch counts and positive target length, got cpu=$cpu_count gpu=$gpu_count target=$task_target_len" >&2
  exit 1
fi
if [[ "$cpu_column_window" != *","* || "$gpu_column_window" != *","* || "$scalar_column_window" != *","* ]]; then
  echo "expected comma-separated CPU/GPU/scalar column windows, got cpu=$cpu_column_window gpu=$gpu_column_window scalar=$scalar_column_window" >&2
  exit 1
fi

printf 'scoreinfo_mismatches=%s\n' "$scoreinfo_mismatches"
printf 'first_mismatch task=%s global=%s diff=%s kind=%s\n' \
  "$first_task_index" "$first_global_task" "$first_diff_index" "$first_kind"
printf 'cpu count=%s score=%s position=%s\n' "$cpu_count" "$cpu_score" "$cpu_position"
printf 'gpu count=%s score=%s position=%s\n' "$gpu_count" "$gpu_score" "$gpu_position"
printf 'task rule=%s strand=%s para=%s dna_start=%s target_len=%s min_score=%s\n' \
  "$task_rule" "$task_strand" "$task_para" "$task_dna_start_pos" "$task_target_len" "$task_min_score"
printf 'column_window start=%s cpu=%s gpu=%s\n' \
  "$column_window_start" "$cpu_column_window" "$gpu_column_window"
printf 'scalar_column_window=%s\n' "$scalar_column_window"
printf 'ok\n'
