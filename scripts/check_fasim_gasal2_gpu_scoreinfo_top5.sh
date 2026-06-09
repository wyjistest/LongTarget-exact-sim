#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_gpu_scoreinfo_top5"}"
DNA="${DNA:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
EXPECTED_GASAL2_BATCH="${FASIM_ALIGN_GASAL2_BATCH:-30000}"
EXPECTED_GASAL2_STREAMS="${FASIM_ALIGN_GASAL2_STREAMS:-2}"

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
mkdir -p "$WORK/cpu" "$WORK/gpu_score_gasal2"

run_cpu() {
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$BIN" -f1 "$DNA" -f2 "$RNA" -r "$RULE" -O "$WORK/cpu" \
    >"$WORK/cpu/stdout.log" 2>"$WORK/cpu/stderr.log"
}

run_gpu_score_gasal2() {
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    "$BIN" -f1 "$DNA" -f2 "$RNA" -r "$RULE" -O "$WORK/gpu_score_gasal2" \
    >"$WORK/gpu_score_gasal2/stdout.log" 2>"$WORK/gpu_score_gasal2/stderr.log"
}

run_cpu
run_gpu_score_gasal2

cpu_out="$(find "$WORK/cpu" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
gpu_out="$(find "$WORK/gpu_score_gasal2" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$cpu_out" || -z "$gpu_out" ]]; then
  echo "expected lite outputs missing" >&2
  exit 1
fi

python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
  --baseline "$cpu_out" \
  --candidate "$gpu_out" \
  --k 5 \
  >"$WORK/top5_compare.txt"

grep -q '^top5_score_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_stability_equal=true$' "$WORK/top5_compare.txt"
grep -q '^top5_nt_score_equal=true$' "$WORK/top5_compare.txt"
grep -q '^benchmark\.fasim_top5_gasal2_gpu_scoreinfo_requested=1$' "$WORK/gpu_score_gasal2/stderr.log"
grep -q '^benchmark\.fasim_top5_gasal2_gpu_scoreinfo_active=1$' "$WORK/gpu_score_gasal2/stderr.log"
grep -q '^benchmark\.fasim_transfer_string_table_enabled=1$' "$WORK/gpu_score_gasal2/stderr.log"
grep -q "^benchmark\\.fasim_gasal2_effective_batch_size=$EXPECTED_GASAL2_BATCH$" "$WORK/gpu_score_gasal2/stderr.log"
grep -q "^benchmark\\.fasim_gasal2_effective_streams=$EXPECTED_GASAL2_STREAMS$" "$WORK/gpu_score_gasal2/stderr.log"
grep -q '^benchmark\.fasim_gasal2_score_prepass_enabled=1$' "$WORK/gpu_score_gasal2/stderr.log"
grep -q '^benchmark\.fasim_gasal2_staged_score_prepass_enabled=1$' "$WORK/gpu_score_gasal2/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_staged_score_prepass_pruned_best_fallback_groups=[1-9][0-9]*$' "$WORK/gpu_score_gasal2/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_staged_score_prepass_pruned_remaining_requests=[1-9][0-9]*$' "$WORK/gpu_score_gasal2/stderr.log"
grep -q '^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_enabled=1$' "$WORK/gpu_score_gasal2/stderr.log"
grep -Eq '^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_used=[1-9][0-9]*$' "$WORK/gpu_score_gasal2/stderr.log"
grep -q '^benchmark\.fasim_exact_column_legacy_score_gpu_replacement_fallbacks=0$' "$WORK/gpu_score_gasal2/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_score_requests=[1-9][0-9]*$' "$WORK/gpu_score_gasal2/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_traceback_requests=[1-9][0-9]*$' "$WORK/gpu_score_gasal2/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_traceback_query_bytes=[1-9][0-9]*$' "$WORK/gpu_score_gasal2/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_traceback_query_reuse_potential_saved_bytes=[1-9][0-9]*$' "$WORK/gpu_score_gasal2/stderr.log"
grep -q '^benchmark\.fasim_gasal2_cpu_traceback_align_calls=0$' "$WORK/gpu_score_gasal2/stderr.log"

cat "$WORK/top5_compare.txt"
echo "ok"
