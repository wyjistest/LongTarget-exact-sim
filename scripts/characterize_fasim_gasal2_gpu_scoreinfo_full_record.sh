#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_gpu_scoreinfo_full_record"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/chromosomes/chr22.fa.gz"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"

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

start_seconds="$(date +%s)"
env \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
  FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
  "$BIN" -f1 "$DNA_RUN" -f2 "$RNA" -r "$RULE" -O "$WORK/out" \
  >"$WORK/stdout.log" 2>"$WORK/stderr.log"
end_seconds="$(date +%s)"
wall_seconds="$((end_seconds - start_seconds))"
printf '%s\n' "$wall_seconds" >"$WORK/wall_seconds.txt"

out_path="$(find "$WORK/out" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$out_path" ]]; then
  echo "expected one lite output" >&2
  exit 1
fi

digest="$(sha256sum "$out_path" | awk '{print $1}')"
lines="$(wc -l < "$out_path")"
scoreinfos="$(awk -F= '/^benchmark\.fasim_gasal2_longtarget_task_batch_scoreinfos=/{print $2}' "$WORK/stderr.log")"
score_requests="$(awk -F= '/^benchmark\.fasim_gasal2_score_requests=/{print $2}' "$WORK/stderr.log")"
traceback_requests="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_requests=/{print $2}' "$WORK/stderr.log")"
traceback_batches="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_batches=/{print $2}' "$WORK/stderr.log")"
gasal2_total_seconds="$(awk -F= '/^benchmark\.fasim_gasal2_total_seconds=/{print $2}' "$WORK/stderr.log")"
gasal2_effective_batch_size="$(awk -F= '/^benchmark\.fasim_gasal2_effective_batch_size=/{print $2}' "$WORK/stderr.log")"
gasal2_score_prepass_enabled="$(awk -F= '/^benchmark\.fasim_gasal2_score_prepass_enabled=/{print $2}' "$WORK/stderr.log")"
gasal2_staged_score_prepass_enabled="$(awk -F= '/^benchmark\.fasim_gasal2_staged_score_prepass_enabled=/{print $2}' "$WORK/stderr.log")"
gasal2_staged_score_prepass_first_requests="$(awk -F= '/^benchmark\.fasim_gasal2_staged_score_prepass_first_requests=/{print $2}' "$WORK/stderr.log")"
gasal2_staged_score_prepass_remaining_requests="$(awk -F= '/^benchmark\.fasim_gasal2_staged_score_prepass_remaining_requests=/{print $2}' "$WORK/stderr.log")"
gasal2_staged_score_prepass_first_threshold="$(awk -F= '/^benchmark\.fasim_gasal2_staged_score_prepass_first_threshold=/{print $2}' "$WORK/stderr.log")"
gasal2_staged_score_prepass_pruned_zero_groups="$(awk -F= '/^benchmark\.fasim_gasal2_staged_score_prepass_pruned_zero_groups=/{print $2}' "$WORK/stderr.log")"
gasal2_staged_score_prepass_pruned_best_fallback_groups="$(awk -F= '/^benchmark\.fasim_gasal2_staged_score_prepass_pruned_best_fallback_groups=/{print $2}' "$WORK/stderr.log")"
gasal2_staged_score_prepass_pruned_remaining_requests="$(awk -F= '/^benchmark\.fasim_gasal2_staged_score_prepass_pruned_remaining_requests=/{print $2}' "$WORK/stderr.log")"
gasal2_score_query_bytes="$(awk -F= '/^benchmark\.fasim_gasal2_score_query_bytes=/{print $2}' "$WORK/stderr.log")"
gasal2_score_target_bytes="$(awk -F= '/^benchmark\.fasim_gasal2_score_target_bytes=/{print $2}' "$WORK/stderr.log")"
gasal2_traceback_query_bytes="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_query_bytes=/{print $2}' "$WORK/stderr.log")"
gasal2_traceback_target_bytes="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_target_bytes=/{print $2}' "$WORK/stderr.log")"
gasal2_traceback_query_reuse_saved_bytes="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_query_reuse_saved_bytes=/{print $2}' "$WORK/stderr.log")"
gasal2_traceback_query_reuse_potential_saved_bytes="$(awk -F= '/^benchmark\.fasim_gasal2_traceback_query_reuse_potential_saved_bytes=/{print $2}' "$WORK/stderr.log")"
transfer_string_table_enabled="$(awk -F= '/^benchmark\.fasim_transfer_string_table_enabled=/{print $2}' "$WORK/stderr.log")"
transfer_string_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_transfer_string_seconds=/{print $2}' "$WORK/stderr.log")"
transfer_table_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_transfer_table_seconds=/{print $2}' "$WORK/stderr.log")"
transfer_reverse_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_transfer_reverse_seconds=/{print $2}' "$WORK/stderr.log")"
src_transform_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_src_transform_seconds=/{print $2}' "$WORK/stderr.log")"
encode_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_encode_seconds=/{print $2}' "$WORK/stderr.log")"
encode_prealign_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_encode_prealign_seconds=/{print $2}' "$WORK/stderr.log")"
encode_legacy_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_encode_legacy_seconds=/{print $2}' "$WORK/stderr.log")"
exact_scoreinfo_build_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_exact_scoreinfo_build_seconds=/{print $2}' "$WORK/stderr.log")"
exact_min_score_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_exact_min_score_seconds=/{print $2}' "$WORK/stderr.log")"
gasal2_extend_wall_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_gasal2_extend_wall_seconds=/{print $2}' "$WORK/stderr.log")"
exact_column_kernel_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_exact_column_kernel_seconds=/{print $2}' "$WORK/stderr.log")"
cuda_topk_kernel_seconds="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_cuda_topk_kernel_seconds=/{print $2}' "$WORK/stderr.log")"
cuda_topk_deferred_batches="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_cuda_topk_deferred_batches=/{print $2}' "$WORK/stderr.log")"
cuda_topk_deferred_tasks="$(awk -F= '/^benchmark\.fasim_top5_gasal2_phase_cuda_topk_deferred_tasks=/{print $2}' "$WORK/stderr.log")"
legacy_score_replacement_used="$(awk -F= '/^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_used=/{print $2}' "$WORK/stderr.log")"
legacy_score_replacement_fallbacks="$(awk -F= '/^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_fallbacks=/{print $2}' "$WORK/stderr.log")"
legacy_score_gpu_wall_seconds="$(awk -F= '/^benchmark\.fasim_exact_column_legacy_score_gpu_shadow_wall_seconds=/{print $2}' "$WORK/stderr.log")"
legacy_score_gpu_kernel_seconds="$(awk -F= '/^benchmark\.fasim_exact_column_legacy_score_gpu_shadow_kernel_seconds=/{print $2}' "$WORK/stderr.log")"

cat >"$WORK/summary.txt" <<EOF
dna=$DNA
dna_run=$DNA_RUN
rna=$RNA
rule=$RULE
wall_seconds=$wall_seconds
digest=$digest
lines=$lines
scoreinfos=$scoreinfos
score_requests=$score_requests
traceback_requests=$traceback_requests
traceback_batches=$traceback_batches
gasal2_total_seconds=$gasal2_total_seconds
gasal2_effective_batch_size=$gasal2_effective_batch_size
gasal2_score_prepass_enabled=$gasal2_score_prepass_enabled
gasal2_staged_score_prepass_enabled=$gasal2_staged_score_prepass_enabled
gasal2_staged_score_prepass_first_requests=$gasal2_staged_score_prepass_first_requests
gasal2_staged_score_prepass_remaining_requests=$gasal2_staged_score_prepass_remaining_requests
gasal2_staged_score_prepass_first_threshold=$gasal2_staged_score_prepass_first_threshold
gasal2_staged_score_prepass_pruned_zero_groups=$gasal2_staged_score_prepass_pruned_zero_groups
gasal2_staged_score_prepass_pruned_best_fallback_groups=$gasal2_staged_score_prepass_pruned_best_fallback_groups
gasal2_staged_score_prepass_pruned_remaining_requests=$gasal2_staged_score_prepass_pruned_remaining_requests
gasal2_score_query_bytes=$gasal2_score_query_bytes
gasal2_score_target_bytes=$gasal2_score_target_bytes
gasal2_traceback_query_bytes=$gasal2_traceback_query_bytes
gasal2_traceback_target_bytes=$gasal2_traceback_target_bytes
gasal2_traceback_query_reuse_saved_bytes=$gasal2_traceback_query_reuse_saved_bytes
gasal2_traceback_query_reuse_potential_saved_bytes=$gasal2_traceback_query_reuse_potential_saved_bytes
transfer_string_table_enabled=$transfer_string_table_enabled
transfer_string_seconds=$transfer_string_seconds
transfer_table_seconds=$transfer_table_seconds
transfer_reverse_seconds=$transfer_reverse_seconds
src_transform_seconds=$src_transform_seconds
encode_seconds=$encode_seconds
encode_prealign_seconds=$encode_prealign_seconds
encode_legacy_seconds=$encode_legacy_seconds
exact_scoreinfo_build_seconds=$exact_scoreinfo_build_seconds
exact_min_score_seconds=$exact_min_score_seconds
gasal2_extend_wall_seconds=$gasal2_extend_wall_seconds
exact_column_kernel_seconds=$exact_column_kernel_seconds
cuda_topk_kernel_seconds=$cuda_topk_kernel_seconds
cuda_topk_deferred_batches=$cuda_topk_deferred_batches
cuda_topk_deferred_tasks=$cuda_topk_deferred_tasks
legacy_score_replacement_used=$legacy_score_replacement_used
legacy_score_replacement_fallbacks=$legacy_score_replacement_fallbacks
legacy_score_gpu_wall_seconds=$legacy_score_gpu_wall_seconds
legacy_score_gpu_kernel_seconds=$legacy_score_gpu_kernel_seconds
output=$out_path
stdout=$WORK/stdout.log
stderr=$WORK/stderr.log
EOF

cat "$WORK/summary.txt"
