#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_flush_dual_finalizer_smoke"}"
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
mkdir -p "$WORK/baseline" "$WORK/dual"

run_case() {
  local label="$1"
  local dual_enabled="$2"
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
    FASIM_GASAL2_FLUSH_DUAL_FINALIZER_SHADOW="$dual_enabled" \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case baseline 0
run_case dual 1

baseline_lite="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
dual_lite="$(find "$WORK/dual" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_lite" || -z "$dual_lite" ]]; then
  echo "missing lite output" >&2
  exit 1
fi
if ! cmp -s "$baseline_lite" "$dual_lite"; then
  echo "dual finalizer scaffold changed lite output" >&2
  exit 1
fi

stderr="$WORK/dual/stderr.log"
requested="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_requested)"
active="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_active)"
disabled_reason="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_disabled_reason)"
ready="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_result_boundary_ready_flushes)"
observed="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_flushes_observed)"
compared="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_flushes_compared)"
unsupported="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_unsupported_flushes)"
legacy_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_legacy_rows)"
extracted_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_extracted_rows)"
missing_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_missing_rows)"
extra_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_extra_rows)"
order_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_order_mismatches)"
cigar_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_cigar_mismatches)"
coordinate_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_coordinate_mismatches)"
counter_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_counter_mismatches)"
archive_descriptor_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_archive_descriptor_mismatches)"
first_mismatch_field="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_first_mismatch_field)"
decision="$(metric_value "$stderr" benchmark.fasim_gasal2_dual_finalizer_decision)"
ordered_requested="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_requested)"
ordered_ready="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_flushes_ready)"
result_includes_traceback="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_result_bytes_includes_traceback)"

if [[ "$requested" != "1" || "$active" != "1" ]]; then
  echo "unexpected requested/active: requested=$requested active=$active" >&2
  exit 1
fi
if [[ "$disabled_reason" != "none" ]]; then
  echo "unexpected disabled reason: $disabled_reason" >&2
  exit 1
fi
if [[ "$decision" != "go_real_ordered_commit_opt_in_next" ]]; then
  echo "unexpected decision: $decision" >&2
  exit 1
fi
if (( ready < 1 || observed != ready || compared != ready || unsupported != 0 )); then
  echo "unexpected comparison accounting: ready=$ready observed=$observed compared=$compared" >&2
  exit 1
fi
if (( legacy_rows < 1 || extracted_rows != legacy_rows )); then
  echo "unexpected row accounting: legacy=$legacy_rows extracted=$extracted_rows" >&2
  exit 1
fi
if (( missing_rows != 0 || extra_rows != 0 || order_mismatches != 0 || cigar_mismatches != 0 || coordinate_mismatches != 0 || counter_mismatches != 0 || archive_descriptor_mismatches != 0 )); then
  echo "dual finalizer comparison mismatch" >&2
  exit 1
fi
if [[ "$first_mismatch_field" != "none" ]]; then
  echo "unexpected first mismatch field: $first_mismatch_field" >&2
  exit 1
fi
if [[ "$ordered_requested" != "1" || "$result_includes_traceback" != "1" ]]; then
  echo "dual finalizer should enable ordered commit telemetry and result byte inclusion marker" >&2
  exit 1
fi
if (( ordered_ready != ready )); then
  echo "ordered commit ready mismatch: ordered=$ordered_ready dual=$ready" >&2
  exit 1
fi

{
  printf 'dual_finalizer_requested=%s\n' "$requested"
  printf 'dual_finalizer_active=%s\n' "$active"
  printf 'dual_finalizer_disabled_reason=%s\n' "$disabled_reason"
  printf 'dual_finalizer_result_boundary_ready_flushes=%s\n' "$ready"
  printf 'dual_finalizer_flushes_compared=%s\n' "$compared"
  printf 'dual_finalizer_unsupported_flushes=%s\n' "$unsupported"
  printf 'dual_finalizer_legacy_rows=%s\n' "$legacy_rows"
  printf 'dual_finalizer_extracted_rows=%s\n' "$extracted_rows"
  printf 'dual_finalizer_missing_rows=%s\n' "$missing_rows"
  printf 'dual_finalizer_extra_rows=%s\n' "$extra_rows"
  printf 'dual_finalizer_order_mismatches=%s\n' "$order_mismatches"
  printf 'dual_finalizer_cigar_mismatches=%s\n' "$cigar_mismatches"
  printf 'dual_finalizer_coordinate_mismatches=%s\n' "$coordinate_mismatches"
  printf 'dual_finalizer_counter_mismatches=%s\n' "$counter_mismatches"
  printf 'dual_finalizer_archive_descriptor_mismatches=%s\n' "$archive_descriptor_mismatches"
  printf 'dual_finalizer_first_mismatch_field=%s\n' "$first_mismatch_field"
  printf 'dual_finalizer_decision=%s\n' "$decision"
  printf 'ordered_commit_result_bytes_includes_traceback=%s\n' "$result_includes_traceback"
  printf 'lite_sha256=%s\n' "$(sha256sum "$dual_lite" | awk '{print $1}')"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
echo "check_fasim_gasal2_flush_dual_finalizer_smoke: ok"
