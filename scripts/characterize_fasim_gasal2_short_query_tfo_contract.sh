#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_short_query_tfo_contract"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
GPU_SAMPLE_INTERVAL_SECONDS="${GPU_SAMPLE_INTERVAL_SECONDS:-1}"
SKIP_CPU="${SKIP_CPU:-0}"
BASELINE_OUTPUT="${BASELINE_OUTPUT:-}"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$TARGET" "$RNA" "$ROOT/scripts/compare_fasim_tfosorted_tfo_contract.py"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/cpu" "$WORK/gasal2"

now_seconds() {
  python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
}

elapsed_seconds() {
  python3 - "$1" "$2" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
}

find_tfosorted_output() {
  local dir="$1"
  find "$dir" -maxdepth 1 -type f -name '*-TFOsorted' | sort | head -n 1
}

gpu_samples="$WORK/gpu_utilization.csv"
gpu_sampler_stderr="$WORK/gpu_utilization.stderr.log"
sampler_pid=""
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi \
    --query-gpu=timestamp,index,utilization.gpu,utilization.memory,memory.used,memory.total \
    --format=csv,noheader,nounits \
    -l "$GPU_SAMPLE_INTERVAL_SECONDS" \
    >"$gpu_samples" 2>"$gpu_sampler_stderr" &
  sampler_pid="$!"
fi

cleanup_sampler() {
  if [[ -n "$sampler_pid" ]]; then
    kill "$sampler_pid" >/dev/null 2>&1 || true
    wait "$sampler_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup_sampler EXIT

if [[ "$SKIP_CPU" == "1" ]]; then
  if [[ -z "$BASELINE_OUTPUT" || ! -s "$BASELINE_OUTPUT" ]]; then
    echo "SKIP_CPU=1 requires BASELINE_OUTPUT" >&2
    exit 1
  fi
  cpu_out="$BASELINE_OUTPUT"
  baseline_wall_seconds="NA"
else
  baseline_start="$(now_seconds)"
  env \
    FASIM_OUTPUT_MODE=tfosorted \
    FASIM_VERBOSE=0 \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$WORK/cpu" \
    >"$WORK/cpu/stdout.log" 2>"$WORK/cpu/stderr.log"
  baseline_end="$(now_seconds)"
  baseline_wall_seconds="$(elapsed_seconds "$baseline_start" "$baseline_end")"
  printf '%s\n' "$baseline_wall_seconds" >"$WORK/cpu/wall_seconds.txt"
  cpu_out="$(find_tfosorted_output "$WORK/cpu")"
fi
if [[ -z "$cpu_out" || ! -s "$cpu_out" ]]; then
  echo "missing CPU TFOsorted output" >&2
  exit 1
fi

candidate_start="$(now_seconds)"
env \
  FASIM_OUTPUT_MODE=tfosorted \
  FASIM_VERBOSE=0 \
  FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
  FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
  FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
  FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
  FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
  FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH" \
  "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$WORK/gasal2" \
  >"$WORK/gasal2/stdout.log" 2>"$WORK/gasal2/stderr.log"
candidate_end="$(now_seconds)"
candidate_wall_seconds="$(elapsed_seconds "$candidate_start" "$candidate_end")"
printf '%s\n' "$candidate_wall_seconds" >"$WORK/gasal2/wall_seconds.txt"
cleanup_sampler
trap - EXIT

candidate_out="$(find_tfosorted_output "$WORK/gasal2")"
if [[ -z "$candidate_out" || ! -s "$candidate_out" ]]; then
  echo "missing GASAL2 TFOsorted output" >&2
  exit 1
fi

gpu_rows_tmp="$WORK/gpu_utilization_rows.tmp"
gpu_summary="$WORK/gpu_utilization_summary.csv"
if [[ -s "$gpu_samples" ]]; then
  awk -F, '
    function trim(value) {
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      return value
    }
    NF >= 6 {
      idx = trim($2)
      gpu = trim($3) + 0
      mem = trim($4) + 0
      used = trim($5) + 0
      total = trim($6) + 0
      count[idx] += 1
      gpu_sum[idx] += gpu
      mem_sum[idx] += mem
      if (count[idx] == 1 || gpu > gpu_max[idx]) gpu_max[idx] = gpu
      if (count[idx] == 1 || mem > mem_max[idx]) mem_max[idx] = mem
      if (count[idx] == 1 || used > used_max[idx]) used_max[idx] = used
      total_mem[idx] = total
    }
    END {
      for (idx in count) {
        printf "%s,%d,%.6f,%d,%.6f,%d,%d,%d\n",
          idx,
          count[idx],
          gpu_sum[idx] / count[idx],
          gpu_max[idx],
          mem_sum[idx] / count[idx],
          mem_max[idx],
          used_max[idx],
          total_mem[idx]
      }
    }
  ' "$gpu_samples" | sort -t, -k1,1n >"$gpu_rows_tmp"
else
  : >"$gpu_rows_tmp"
fi
{
  echo "gpu_index,samples,gpu_util_avg,gpu_util_max,mem_util_avg,mem_util_max,mem_used_max_mib,mem_total_mib"
  cat "$gpu_rows_tmp"
} >"$gpu_summary"
rm -f "$gpu_rows_tmp"

python3 "$ROOT/scripts/compare_fasim_lite_full_equivalence.py" \
  --baseline "$cpu_out" \
  --candidate "$candidate_out" \
  >"$WORK/full_row_compare.txt" || true
python3 "$ROOT/scripts/compare_fasim_tfosorted_tfo_contract.py" \
  --baseline "$cpu_out" \
  --candidate "$candidate_out" \
  --require-topk-equal \
  >"$WORK/tfo_contract_compare.txt"

extract_metric() {
  local key="$1"
  local default="${2:-0}"
  local value
  value="$(awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$WORK/gasal2/stderr.log" 2>/dev/null || true)"
  if [[ -z "$value" ]]; then
    printf '%s' "$default"
  else
    printf '%s' "$value"
  fi
}

read_compare() {
  local path="$1"
  local key="$2"
  local default="${3:-}"
  local value
  value="$(awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$path" 2>/dev/null || true)"
  if [[ -z "$value" ]]; then
    printf '%s' "$default"
  else
    printf '%s' "$value"
  fi
}

speedup="NA"
if [[ "$baseline_wall_seconds" != "NA" ]]; then
  speedup="$(python3 - "$baseline_wall_seconds" "$candidate_wall_seconds" <<'PY'
import sys
baseline = float(sys.argv[1])
candidate = float(sys.argv[2])
print(f"{baseline / candidate:.6f}")
PY
)"
fi

{
  printf 'target=%s\n' "$TARGET"
  printf 'rna=%s\n' "$RNA"
  printf 'rule=%s\n' "$RULE"
  printf 'baseline_wall_seconds=%s\n' "$baseline_wall_seconds"
  printf 'candidate_wall_seconds=%s\n' "$candidate_wall_seconds"
  printf 'speedup_vs_baseline=%s\n' "$speedup"
  printf 'prune_max_per_task=%s\n' "$PRUNE_MAX_PER_TASK"
  printf 'gasal2_streams=%s\n' "$GASAL2_STREAMS"
  printf 'gasal2_batch=%s\n' "$GASAL2_BATCH"
  printf 'baseline_output=%s\n' "$cpu_out"
  printf 'candidate_output=%s\n' "$candidate_out"
  printf 'full_rows_equal=%s\n' "$(read_compare "$WORK/full_row_compare.txt" full_rows_equal)"
  printf 'full_missing_rows=%s\n' "$(read_compare "$WORK/full_row_compare.txt" missing_rows)"
  printf 'full_extra_rows=%s\n' "$(read_compare "$WORK/full_row_compare.txt" extra_rows)"
  printf 'tfo_equal=%s\n' "$(read_compare "$WORK/tfo_contract_compare.txt" tfo_equal)"
  printf 'tfo_missing=%s\n' "$(read_compare "$WORK/tfo_contract_compare.txt" tfo_missing)"
  printf 'tfo_extra=%s\n' "$(read_compare "$WORK/tfo_contract_compare.txt" tfo_extra)"
  printf 'gapless_tfo_equal=%s\n' "$(read_compare "$WORK/tfo_contract_compare.txt" gapless_tfo_equal)"
  printf 'gapless_tfo_missing=%s\n' "$(read_compare "$WORK/tfo_contract_compare.txt" gapless_tfo_missing)"
  printf 'gapless_tfo_extra=%s\n' "$(read_compare "$WORK/tfo_contract_compare.txt" gapless_tfo_extra)"
  printf 'top5_tfo_score_equal=%s\n' "$(read_compare "$WORK/tfo_contract_compare.txt" top5_tfo_score_equal)"
  printf 'top5_tfo_stability_equal=%s\n' "$(read_compare "$WORK/tfo_contract_compare.txt" top5_tfo_stability_equal)"
  printf 'top5_tfo_nt_score_equal=%s\n' "$(read_compare "$WORK/tfo_contract_compare.txt" top5_tfo_nt_score_equal)"
  printf 'gasal2_total_seconds=%s\n' "$(extract_metric benchmark.fasim_gasal2_total_seconds)"
  printf 'gasal2_wait_seconds=%s\n' "$(extract_metric benchmark.fasim_gasal2_wait_seconds)"
  printf 'gasal2_score_wait_seconds=%s\n' "$(extract_metric benchmark.fasim_gasal2_score_wait_seconds)"
  printf 'gasal2_traceback_wait_seconds=%s\n' "$(extract_metric benchmark.fasim_gasal2_traceback_wait_seconds)"
  printf 'score_prepass_first_requests=%s\n' "$(extract_metric benchmark.fasim_gasal2_staged_score_prepass_first_requests)"
  printf 'score_prepass_remaining_requests=%s\n' "$(extract_metric benchmark.fasim_gasal2_staged_score_prepass_remaining_requests)"
  printf 'score_prepass_pruned_remaining_requests=%s\n' "$(extract_metric benchmark.fasim_gasal2_staged_score_prepass_pruned_remaining_requests)"
  printf 'traceback_requests=%s\n' "$(extract_metric benchmark.fasim_gasal2_cpu_traceback_replay_attempts)"
  printf 'query_reuse_saved_bytes=%s\n' "$(extract_metric benchmark.fasim_gasal2_score_query_reuse_saved_bytes)"
  printf 'traceback_query_reuse_saved_bytes=%s\n' "$(extract_metric benchmark.fasim_gasal2_traceback_query_reuse_saved_bytes)"
  printf 'gpu_utilization_summary=%s\n' "$gpu_summary"
  printf 'full_row_compare=%s\n' "$WORK/full_row_compare.txt"
  printf 'tfo_contract_compare=%s\n' "$WORK/tfo_contract_compare.txt"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
