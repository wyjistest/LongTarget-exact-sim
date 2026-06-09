#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/chromosomes/chr22.fa.gz"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
GPU_SAMPLE_INTERVAL_SECONDS="${GPU_SAMPLE_INTERVAL_SECONDS:-1}"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

rm -rf "$WORK"
mkdir -p "$WORK/input" "$WORK/out"

DNA_RUN="$DNA"
case "$DNA" in
  *.gz)
    DNA_RUN="$WORK/input/$(basename "${DNA%.gz}")"
    gzip -dc "$DNA" >"$DNA_RUN"
    ;;
esac

sampler_pid=""
gpu_samples="$WORK/gpu_utilization.csv"
gpu_sampler_stderr="$WORK/gpu_utilization.stderr.log"
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

start_seconds="$(date +%s.%N)"
env \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
  FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
  "$BIN" -f1 "$DNA_RUN" -f2 "$RNA" -r "$RULE" -O "$WORK/out" \
  >"$WORK/stdout.log" 2>"$WORK/stderr.log"
end_seconds="$(date +%s.%N)"
cleanup_sampler
trap - EXIT

wall_seconds="$(awk -v start="$start_seconds" -v end="$end_seconds" 'BEGIN {printf "%.6f", end - start}')"
printf '%s\n' "$wall_seconds" >"$WORK/wall_seconds.txt"

out_path="$(find "$WORK/out" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$out_path" ]]; then
  echo "expected one lite output" >&2
  exit 1
fi

benchmark_metrics="$WORK/benchmark_metrics.txt"
awk -F= '/^benchmark\./ {print}' "$WORK/stderr.log" >"$benchmark_metrics"

metric() {
  local key="$1"
  awk -F= -v key="$key" '$1 == key {value=$2} END {print value}' "$WORK/stderr.log"
}

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

phase_breakdown="$WORK/phase_breakdown.tsv"
awk -F= -v wall="$wall_seconds" '
  /^benchmark\.fasim_top5_gasal2_phase_/ && $1 ~ /_seconds$/ {
    name = $1
    sub(/^benchmark\.fasim_top5_gasal2_phase_/, "", name)
    seconds = $2 + 0
    fraction = wall > 0 ? seconds / wall : 0
    printf "%s\t%.9f\t%.9f\n", name, seconds, fraction
  }
' "$WORK/stderr.log" | sort -k2,2nr >"$phase_breakdown"

digest="$(sha256sum "$out_path" | awk '{print $1}')"
lines="$(wc -l < "$out_path")"

cat >"$WORK/summary.txt" <<EOF
dna=$DNA
dna_run=$DNA_RUN
rna=$RNA
rule=$RULE
wall_seconds=$wall_seconds
digest=$digest
lines=$lines
scoreinfos=$(metric benchmark.fasim_gasal2_longtarget_task_batch_scoreinfos)
score_requests=$(metric benchmark.fasim_gasal2_score_requests)
traceback_requests=$(metric benchmark.fasim_gasal2_traceback_requests)
traceback_batches=$(metric benchmark.fasim_gasal2_traceback_batches)
gasal2_total_seconds=$(metric benchmark.fasim_gasal2_total_seconds)
gasal2_fill_seconds=$(metric benchmark.fasim_gasal2_fill_seconds)
gasal2_wait_seconds=$(metric benchmark.fasim_gasal2_wait_seconds)
gasal2_score_wait_seconds=$(metric benchmark.fasim_gasal2_score_wait_seconds)
gasal2_traceback_wait_seconds=$(metric benchmark.fasim_gasal2_traceback_wait_seconds)
gasal2_extend_wall_seconds=$(metric benchmark.fasim_top5_gasal2_phase_gasal2_extend_wall_seconds)
exact_column_kernel_seconds=$(metric benchmark.fasim_top5_gasal2_phase_exact_column_kernel_seconds)
exact_column_wall_seconds=$(metric benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds)
exact_column_h2d_seconds=$(metric benchmark.fasim_top5_gasal2_phase_exact_column_h2d_seconds)
exact_column_d2h_seconds=$(metric benchmark.fasim_top5_gasal2_phase_exact_column_d2h_seconds)
transfer_string_seconds=$(metric benchmark.fasim_top5_gasal2_phase_transfer_string_seconds)
transfer_table_seconds=$(metric benchmark.fasim_top5_gasal2_phase_transfer_table_seconds)
transfer_reverse_seconds=$(metric benchmark.fasim_top5_gasal2_phase_transfer_reverse_seconds)
src_transform_seconds=$(metric benchmark.fasim_top5_gasal2_phase_src_transform_seconds)
encode_seconds=$(metric benchmark.fasim_top5_gasal2_phase_encode_seconds)
encode_prealign_seconds=$(metric benchmark.fasim_top5_gasal2_phase_encode_prealign_seconds)
encode_legacy_seconds=$(metric benchmark.fasim_top5_gasal2_phase_encode_legacy_seconds)
exact_scoreinfo_build_seconds=$(metric benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_build_seconds)
output_write_seconds=$(metric benchmark.fasim_top5_gasal2_phase_output_write_seconds)
traceback_query_bytes=$(metric benchmark.fasim_gasal2_traceback_query_bytes)
traceback_target_bytes=$(metric benchmark.fasim_gasal2_traceback_target_bytes)
traceback_query_reuse_saved_bytes=$(metric benchmark.fasim_gasal2_traceback_query_reuse_saved_bytes)
legacy_score_replacement_used=$(metric benchmark.fasim_exact_column_legacy_score_gpu_replacement_used)
legacy_score_replacement_fallbacks=$(metric benchmark.fasim_exact_column_legacy_score_gpu_replacement_fallbacks)
gpu_utilization_summary=$gpu_summary
phase_breakdown=$phase_breakdown
benchmark_metrics=$benchmark_metrics
output=$out_path
stdout=$WORK/stdout.log
stderr=$WORK/stderr.log
EOF

cat "$WORK/summary.txt"
echo
cat "$gpu_summary"
echo
echo -e "phase\tseconds\twall_fraction"
cat "$phase_breakdown"
