#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_bridge"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_longtarget_bridge_digest"}"
DNA="${DNA:-"$ROOT/testDNA.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
BATCH="${FASIM_ALIGN_GASAL2_BATCH:-5000}"
TASK_BATCH="${FASIM_ALIGN_GASAL2_TASK_BATCH:-4096}"

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
mkdir -p "$WORK/cpu" "$WORK/bridge"

run_case() {
  local out_dir="$1"
  shift
  local start_seconds
  local end_seconds
  start_seconds="$(date +%s)"
  env "$@" \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$BIN" -f1 "$DNA" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  end_seconds="$(date +%s)"
  printf '%s\n' "$((end_seconds - start_seconds))" >"$out_dir/wall_seconds.txt"
}

run_case "$WORK/cpu"
run_case "$WORK/bridge" \
  FASIM_ALIGN_GASAL2=1 \
  FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
  FASIM_ALIGN_GASAL2_CPU_TRACEBACK=1 \
  FASIM_ALIGN_GASAL2_BATCH="$BATCH" \
  FASIM_ALIGN_GASAL2_TASK_BATCH="$TASK_BATCH"

mapfile -t cpu_outputs < <(find "$WORK/cpu" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort)
mapfile -t bridge_outputs < <(find "$WORK/bridge" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort)

if [[ "${#cpu_outputs[@]}" -ne 1 || "${#bridge_outputs[@]}" -ne 1 ]]; then
  echo "expected one lite output per run" >&2
  printf 'cpu outputs: %s\n' "${cpu_outputs[*]}" >&2
  printf 'bridge outputs: %s\n' "${bridge_outputs[*]}" >&2
  exit 1
fi

cpu_out="${cpu_outputs[0]}"
bridge_out="${bridge_outputs[0]}"

cmp -s "$cpu_out" "$bridge_out"

cpu_digest="$(sha256sum "$cpu_out" | awk '{print $1}')"
bridge_digest="$(sha256sum "$bridge_out" | awk '{print $1}')"
cpu_lines="$(wc -l < "$cpu_out")"
bridge_lines="$(wc -l < "$bridge_out")"
cpu_wall_seconds="$(cat "$WORK/cpu/wall_seconds.txt")"
bridge_wall_seconds="$(cat "$WORK/bridge/wall_seconds.txt")"

if [[ "$cpu_digest" != "$bridge_digest" || "$cpu_lines" != "$bridge_lines" ]]; then
  echo "digest or line count mismatch after cmp" >&2
  exit 1
fi

grep -q '^benchmark\.fasim_gasal2_enabled=1$' "$WORK/bridge/stderr.log"
grep -q '^benchmark\.fasim_gasal2_built=1$' "$WORK/bridge/stderr.log"
grep -q '^benchmark\.fasim_gasal2_traceback_requests=0$' "$WORK/bridge/stderr.log"
grep -q '^benchmark\.fasim_gasal2_traceback_batches=0$' "$WORK/bridge/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_score_requests=[1-9][0-9]*$' "$WORK/bridge/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_target_view_requests=[1-9][0-9]*$' "$WORK/bridge/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_cpu_traceback_align_calls=[1-9][0-9]*$' "$WORK/bridge/stderr.log"
grep -Eq '^benchmark\.fasim_gasal2_score_query_reuse_saved_bytes=[1-9][0-9]*$' "$WORK/bridge/stderr.log"

cat >"$WORK/summary.txt" <<EOF
digest=$cpu_digest
lines=$cpu_lines
dna=$DNA
rna=$RNA
rule=$RULE
batch=$BATCH
task_batch=$TASK_BATCH
cpu_wall_seconds=$cpu_wall_seconds
bridge_wall_seconds=$bridge_wall_seconds
EOF

{
  echo "ok"
  cat "$WORK/summary.txt"
  grep -E '^benchmark\.fasim_gasal2_(score_requests|score_batches|target_view_requests|score_query_reuse_saved_bytes|score_selected_attempts|cpu_traceback_replay_attempts|cpu_traceback_selected_attempts|cpu_traceback_align_calls|cpu_traceback_skipped_after_emit|cpu_traceback_emit_threshold|cpu_traceback_emit_best_fallback|cpu_traceback_emit_last|cpu_traceback_emit_rank1|cpu_traceback_emit_rank2|cpu_traceback_emit_rank3|cpu_traceback_emit_rank4plus|longtarget_attempt_build_seconds|longtarget_score_select_seconds|cpu_traceback_replay_seconds|cpu_traceback_align_seconds|cpu_traceback_convert_seconds|total_seconds)=' "$WORK/bridge/stderr.log"
} >"$WORK/report.txt"

cat "$WORK/report.txt"
