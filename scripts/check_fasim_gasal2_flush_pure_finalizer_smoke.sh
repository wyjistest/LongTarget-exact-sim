#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_flush_pure_finalizer_smoke"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"

metric_value() {
  local file="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$file"
}

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$TARGET" "$RNA"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/baseline" "$WORK/pure"

run_case() {
  local label="$1"
  local pure_enabled="$2"
  local out_dir="$WORK/$label"
  mkdir -p "$out_dir"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256 \
    FASIM_ALIGN_GASAL2_STREAMS=3 \
    FASIM_ALIGN_GASAL2_BATCH=20000 \
    FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE=1 \
    FASIM_GASAL2_FLUSH_PURE_FINALIZER_SHADOW="$pure_enabled" \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case baseline 0
run_case pure 1

baseline_lite="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
pure_lite="$(find "$WORK/pure" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_lite" || -z "$pure_lite" ]]; then
  echo "missing lite output" >&2
  exit 1
fi
if ! cmp -s "$baseline_lite" "$pure_lite"; then
  echo "pure finalizer scaffold changed lite output" >&2
  exit 1
fi

stderr="$WORK/pure/stderr.log"
requested="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_requested)"
active="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_active)"
disabled_reason="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_disabled_reason)"
flushes="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_flushes_observed)"
ready="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_result_boundary_ready_flushes)"
missing="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_result_boundary_missing_flushes)"
eligible="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_eligible_flushes)"
ineligible="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_ineligible_flushes)"
local_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_local_rows_ready_flushes)"
direct_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_direct_rows_local_ready_flushes)"
triplex_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_triplex_rows_local_ready_flushes)"
output_blockers="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_output_side_effect_blocker_flushes)"
archive_blockers="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_archive_writer_blocker_flushes)"
triplex_blockers="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_global_task_triplex_commit_blocker_flushes)"
telemetry_blockers="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_telemetry_global_counter_blocker_flushes)"
precommit_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_precommit_rows)"
rows_compared="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_rows_compared)"
missing_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_missing_rows)"
extra_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_extra_rows)"
cigar_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_cigar_mismatches)"
digest_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_digest_mismatches)"
decision="$(metric_value "$stderr" benchmark.fasim_gasal2_flush_pure_finalizer_decision)"

if [[ "$requested" != "1" || "$active" != "1" ]]; then
  echo "unexpected requested/active: requested=$requested active=$active" >&2
  exit 1
fi
if [[ "$disabled_reason" != "ordered_commit_not_extracted" ]]; then
  echo "unexpected disabled reason: $disabled_reason" >&2
  exit 1
fi
if [[ "$decision" != "go_ordered_commit_extraction_next" ]]; then
  echo "unexpected decision: $decision" >&2
  exit 1
fi
if (( flushes < 1 || ready != flushes || missing != 0 )); then
  echo "flush/result-boundary accounting mismatch: flushes=$flushes ready=$ready missing=$missing" >&2
  exit 1
fi
if (( eligible != 0 || ineligible != flushes || local_rows != flushes )); then
  echo "unexpected readiness accounting: eligible=$eligible ineligible=$ineligible local_rows=$local_rows flushes=$flushes" >&2
  exit 1
fi
if (( direct_rows + triplex_rows != flushes )); then
  echo "unexpected local row path accounting: direct=$direct_rows triplex=$triplex_rows flushes=$flushes" >&2
  exit 1
fi
if (( output_blockers != direct_rows || archive_blockers != direct_rows || triplex_blockers != triplex_rows || telemetry_blockers != flushes )); then
  echo "unexpected blocker accounting" >&2
  exit 1
fi
if (( precommit_rows < 1 )); then
  echo "expected material precommit rows" >&2
  exit 1
fi
if (( rows_compared != 0 || missing_rows != 0 || extra_rows != 0 || cigar_mismatches != 0 || digest_mismatches != 0 )); then
  echo "comparison counters should remain zero until dual finalizer exists" >&2
  exit 1
fi

{
  printf 'pure_finalizer_requested=%s\n' "$requested"
  printf 'pure_finalizer_active=%s\n' "$active"
  printf 'pure_finalizer_disabled_reason=%s\n' "$disabled_reason"
  printf 'pure_finalizer_flushes_observed=%s\n' "$flushes"
  printf 'pure_finalizer_result_boundary_ready_flushes=%s\n' "$ready"
  printf 'pure_finalizer_local_rows_ready_flushes=%s\n' "$local_rows"
  printf 'pure_finalizer_direct_rows_local_ready_flushes=%s\n' "$direct_rows"
  printf 'pure_finalizer_triplex_rows_local_ready_flushes=%s\n' "$triplex_rows"
  printf 'pure_finalizer_precommit_rows=%s\n' "$precommit_rows"
  printf 'pure_finalizer_decision=%s\n' "$decision"
  printf 'lite_sha256=%s\n' "$(sha256sum "$pure_lite" | awk '{print $1}')"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
echo "check_fasim_gasal2_flush_pure_finalizer_smoke: ok"
