#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_flush_extracted_finalizer_smoke"}"
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
mkdir -p "$WORK/baseline" "$WORK/validate_only" "$WORK/extracted" "$WORK/extracted_validate"

run_case() {
  local label="$1"
  local extracted_enabled="$2"
  local validate_enabled="$3"
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
    FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER="$extracted_enabled" \
    FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER_VALIDATE="$validate_enabled" \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case baseline 0 0
run_case validate_only 0 1
run_case extracted 1 0
run_case extracted_validate 1 1

baseline_lite="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
validate_only_lite="$(find "$WORK/validate_only" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
extracted_lite="$(find "$WORK/extracted" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
extracted_validate_lite="$(find "$WORK/extracted_validate" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_lite" || -z "$validate_only_lite" || -z "$extracted_lite" || -z "$extracted_validate_lite" ]]; then
  echo "missing lite output" >&2
  exit 1
fi
for lite in "$validate_only_lite" "$extracted_lite" "$extracted_validate_lite"; do
  if ! cmp -s "$baseline_lite" "$lite"; then
    echo "extracted finalizer changed lite output: $lite" >&2
    exit 1
  fi
done

check_common_clean() {
  local stderr="$1"
  local expected_validate_active="$2"
  local requested active validate_requested validate_active disabled ready observed eligible committed unsupported fallback
  local legacy_finalizer_executed extracted_finalizer_executed comparison_performed extracted_active_flushes
  local legacy_rows extracted_rows committed_rows missing_rows extra_rows order_mismatches cigar_mismatches
  local coordinate_mismatches counter_mismatches archive_descriptor_mismatches first_mismatch_field decision
  local ordered_requested ordered_ready result_includes_traceback

  requested="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_requested)"
  active="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_active)"
  validate_requested="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_validate_requested)"
  validate_active="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_validate_active)"
  disabled="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_disabled_reason)"
  ready="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_result_boundary_ready_flushes)"
  observed="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_flushes_observed)"
  eligible="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_eligible_flushes)"
  committed="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_committed_flushes)"
  unsupported="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_unsupported_finalizer_shape_flushes)"
  fallback="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_legacy_fallback_flushes)"
  legacy_finalizer_executed="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_legacy_finalizer_executed)"
  extracted_finalizer_executed="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_extracted_finalizer_executed)"
  comparison_performed="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_comparison_performed)"
  extracted_active_flushes="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_extracted_active_flushes)"
  legacy_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_legacy_rows)"
  extracted_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_extracted_rows)"
  committed_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_committed_rows)"
  missing_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_missing_rows)"
  extra_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_extra_rows)"
  order_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_order_mismatches)"
  cigar_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_cigar_mismatches)"
  coordinate_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_coordinate_mismatches)"
  counter_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_counter_mismatches)"
  archive_descriptor_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_archive_descriptor_mismatches)"
  first_mismatch_field="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_first_mismatch_field)"
  decision="$(metric_value "$stderr" benchmark.fasim_gasal2_extracted_finalizer_decision)"
  ordered_requested="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_requested)"
  ordered_ready="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_flushes_ready)"
  result_includes_traceback="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_result_bytes_includes_traceback)"

  if [[ "$requested" != "1" || "$active" != "1" ]]; then
    echo "unexpected requested/active: requested=$requested active=$active" >&2
    exit 1
  fi
  if [[ "$validate_active" != "$expected_validate_active" ]]; then
    echo "unexpected validate_active: got=$validate_active expected=$expected_validate_active" >&2
    exit 1
  fi
  if [[ "$disabled" != "none" || "$decision" != "real_extracted_active_clean_no_fallback" ]]; then
    echo "unexpected extracted finalizer state: disabled=$disabled decision=$decision" >&2
    exit 1
  fi
  if (( ready < 1 || observed != ready || eligible != ready || committed != ready || unsupported != 0 || fallback != 0 )); then
    echo "unexpected flush accounting: ready=$ready observed=$observed eligible=$eligible committed=$committed unsupported=$unsupported fallback=$fallback" >&2
    exit 1
  fi
  if (( committed_rows < 1 || extracted_rows < committed_rows )); then
    echo "unexpected row accounting: extracted=$extracted_rows committed=$committed_rows" >&2
    exit 1
  fi
  if [[ "$expected_validate_active" == "1" ]]; then
    if (( legacy_finalizer_executed != ready || extracted_finalizer_executed != ready || comparison_performed != ready || extracted_active_flushes != ready )); then
      echo "validate execution accounting mismatch: legacy_exec=$legacy_finalizer_executed extracted_exec=$extracted_finalizer_executed comparison=$comparison_performed active_flushes=$extracted_active_flushes ready=$ready" >&2
      exit 1
    fi
    if (( legacy_rows < 1 || legacy_rows != extracted_rows )); then
      echo "validate comparison row mismatch: legacy=$legacy_rows extracted=$extracted_rows" >&2
      exit 1
    fi
  else
    if (( legacy_finalizer_executed != 0 || comparison_performed != 0 || extracted_finalizer_executed != ready || extracted_active_flushes != ready )); then
      echo "non-validate execution accounting mismatch: legacy_exec=$legacy_finalizer_executed extracted_exec=$extracted_finalizer_executed comparison=$comparison_performed active_flushes=$extracted_active_flushes ready=$ready" >&2
      exit 1
    fi
    if (( legacy_rows != 0 )); then
      echo "non-validate real path should not run legacy finalizer: legacy=$legacy_rows" >&2
      exit 1
    fi
  fi
  if (( missing_rows != 0 || extra_rows != 0 || order_mismatches != 0 || cigar_mismatches != 0 || coordinate_mismatches != 0 || counter_mismatches != 0 || archive_descriptor_mismatches != 0 )); then
    echo "extracted finalizer mismatch" >&2
    exit 1
  fi
  if [[ "$first_mismatch_field" != "none" ]]; then
    echo "unexpected first mismatch field: $first_mismatch_field" >&2
    exit 1
  fi
  if [[ "$ordered_requested" != "1" || "$result_includes_traceback" != "1" ]]; then
    echo "extracted finalizer should enable ordered commit telemetry and result byte inclusion marker" >&2
    exit 1
  fi
  if (( ordered_ready != ready )); then
    echo "ordered commit ready mismatch: ordered=$ordered_ready extracted=$ready" >&2
    exit 1
  fi

  {
    printf 'requested=%s\n' "$requested"
    printf 'active=%s\n' "$active"
    printf 'validate_requested=%s\n' "$validate_requested"
    printf 'validate_active=%s\n' "$validate_active"
    printf 'ready=%s\n' "$ready"
    printf 'eligible=%s\n' "$eligible"
    printf 'committed=%s\n' "$committed"
    printf 'legacy_rows=%s\n' "$legacy_rows"
    printf 'extracted_rows=%s\n' "$extracted_rows"
    printf 'committed_rows=%s\n' "$committed_rows"
    printf 'legacy_finalizer_executed=%s\n' "$legacy_finalizer_executed"
    printf 'extracted_finalizer_executed=%s\n' "$extracted_finalizer_executed"
    printf 'comparison_performed=%s\n' "$comparison_performed"
    printf 'extracted_active_flushes=%s\n' "$extracted_active_flushes"
    printf 'decision=%s\n' "$decision"
  }
}

validate_only_stderr="$WORK/validate_only/stderr.log"
validate_only_requested="$(metric_value "$validate_only_stderr" benchmark.fasim_gasal2_extracted_finalizer_requested)"
validate_only_active="$(metric_value "$validate_only_stderr" benchmark.fasim_gasal2_extracted_finalizer_active)"
validate_only_validate_requested="$(metric_value "$validate_only_stderr" benchmark.fasim_gasal2_extracted_finalizer_validate_requested)"
validate_only_validate_active="$(metric_value "$validate_only_stderr" benchmark.fasim_gasal2_extracted_finalizer_validate_active)"
validate_only_decision="$(metric_value "$validate_only_stderr" benchmark.fasim_gasal2_extracted_finalizer_decision)"
if [[ "$validate_only_requested" != "0" || "$validate_only_active" != "0" || "$validate_only_validate_requested" != "1" || "$validate_only_validate_active" != "0" || "$validate_only_decision" != "not_requested" ]]; then
  echo "validate-only mode should not activate real extracted finalizer" >&2
  exit 1
fi

check_common_clean "$WORK/extracted/stderr.log" 0 >"$WORK/extracted_summary.txt"
check_common_clean "$WORK/extracted_validate/stderr.log" 1 >"$WORK/extracted_validate_summary.txt"

{
  printf 'validate_only_requested=%s\n' "$validate_only_requested"
  printf 'validate_only_active=%s\n' "$validate_only_active"
  printf 'validate_only_validate_requested=%s\n' "$validate_only_validate_requested"
  printf 'validate_only_validate_active=%s\n' "$validate_only_validate_active"
  printf 'validate_only_decision=%s\n' "$validate_only_decision"
  printf 'extracted_lite_sha256=%s\n' "$(sha256sum "$extracted_lite" | awk '{print $1}')"
  printf 'extracted_validate_lite_sha256=%s\n' "$(sha256sum "$extracted_validate_lite" | awk '{print $1}')"
} >"$WORK/summary.txt"

cat "$WORK/extracted_summary.txt"
cat "$WORK/extracted_validate_summary.txt"
cat "$WORK/summary.txt"
echo "check_fasim_gasal2_flush_extracted_finalizer_smoke: ok"
