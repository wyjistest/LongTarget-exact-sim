#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_flush_ordered_commit_smoke"}"
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
mkdir -p "$WORK/baseline" "$WORK/commit"

run_case() {
  local label="$1"
  local commit_enabled="$2"
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
    FASIM_GASAL2_FLUSH_ORDERED_COMMIT_SHADOW="$commit_enabled" \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case baseline 0
run_case commit 1

baseline_lite="$(find "$WORK/baseline" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
commit_lite="$(find "$WORK/commit" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
if [[ -z "$baseline_lite" || -z "$commit_lite" ]]; then
  echo "missing lite output" >&2
  exit 1
fi
if ! cmp -s "$baseline_lite" "$commit_lite"; then
  echo "ordered commit scaffold changed lite output" >&2
  exit 1
fi

stderr="$WORK/commit/stderr.log"
requested="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_requested)"
active="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_active)"
disabled_reason="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_disabled_reason)"
ready="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_flushes_ready)"
committed="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_flushes_committed)"
direct_committed="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_direct_flushes_committed)"
triplex_committed="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_triplex_flushes_committed)"
order_violations="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_order_violations)"
precommit_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_precommit_rows)"
appended_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_appended_rows)"
archive_records="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_archive_records)"
result_bytes_max="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_result_bytes_max)"
traceback_bytes_max="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_traceback_bytes_max)"
result_includes_traceback="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_result_bytes_includes_traceback)"
precommit_bytes_max="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_precommit_rows_bytes_max)"
projected_two_slot_peak="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_projected_two_slot_peak_bytes)"
missing_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_missing_rows)"
extra_rows="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_extra_rows)"
cigar_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_cigar_mismatches)"
counter_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_counter_mismatches)"
digest_mismatches="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_digest_mismatches)"
decision="$(metric_value "$stderr" benchmark.fasim_gasal2_ordered_commit_decision)"

if [[ "$requested" != "1" || "$active" != "1" ]]; then
  echo "unexpected requested/active: requested=$requested active=$active" >&2
  exit 1
fi
if [[ "$disabled_reason" != "none" ]]; then
  echo "unexpected disabled reason: $disabled_reason" >&2
  exit 1
fi
if [[ "$decision" != "go_same_result_dual_finalizer_shadow_next" ]]; then
  echo "unexpected decision: $decision" >&2
  exit 1
fi
if (( ready < 1 || committed != ready || direct_committed + triplex_committed != committed )); then
  echo "commit flush accounting mismatch: ready=$ready committed=$committed direct=$direct_committed triplex=$triplex_committed" >&2
  exit 1
fi
if (( order_violations != 0 )); then
  echo "unexpected order violations: $order_violations" >&2
  exit 1
fi
if (( precommit_rows < 1 || appended_rows < 1 )); then
  echo "expected material row counts: precommit=$precommit_rows appended=$appended_rows" >&2
  exit 1
fi
if (( result_bytes_max < 1 || traceback_bytes_max < 1 || precommit_bytes_max < 1 || projected_two_slot_peak < 1 )); then
  echo "expected material byte counters" >&2
  exit 1
fi
if [[ "$result_includes_traceback" != "1" ]]; then
  echo "expected result bytes to include traceback bytes" >&2
  exit 1
fi
if (( missing_rows != 0 || extra_rows != 0 || cigar_mismatches != 0 || counter_mismatches != 0 || digest_mismatches != 0 )); then
  echo "comparison counters should remain zero until dual finalizer exists" >&2
  exit 1
fi

{
  printf 'ordered_commit_requested=%s\n' "$requested"
  printf 'ordered_commit_active=%s\n' "$active"
  printf 'ordered_commit_disabled_reason=%s\n' "$disabled_reason"
  printf 'ordered_commit_flushes_ready=%s\n' "$ready"
  printf 'ordered_commit_flushes_committed=%s\n' "$committed"
  printf 'ordered_commit_direct_flushes_committed=%s\n' "$direct_committed"
  printf 'ordered_commit_triplex_flushes_committed=%s\n' "$triplex_committed"
  printf 'ordered_commit_precommit_rows=%s\n' "$precommit_rows"
  printf 'ordered_commit_appended_rows=%s\n' "$appended_rows"
  printf 'ordered_commit_result_bytes_max=%s\n' "$result_bytes_max"
  printf 'ordered_commit_traceback_bytes_max=%s\n' "$traceback_bytes_max"
  printf 'ordered_commit_result_bytes_includes_traceback=%s\n' "$result_includes_traceback"
  printf 'ordered_commit_precommit_rows_bytes_max=%s\n' "$precommit_bytes_max"
  printf 'ordered_commit_projected_two_slot_peak_bytes=%s\n' "$projected_two_slot_peak"
  printf 'ordered_commit_decision=%s\n' "$decision"
  printf 'lite_sha256=%s\n' "$(sha256sum "$commit_lite" | awk '{print $1}')"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
echo "check_fasim_gasal2_flush_ordered_commit_smoke: ok"
