#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_direct_lite_archive_convert"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
COMPARE_MODE="${COMPARE_MODE:-byte}"

now_seconds() {
  python3 - <<'PY'
import time
print(f"{time.perf_counter():.9f}")
PY
}

elapsed_seconds() {
  python3 - "$1" "$2" <<'PY'
import sys
start = float(sys.argv[1])
end = float(sys.argv[2])
print(f"{end - start:.6f}")
PY
}

ratio_seconds() {
  python3 - "$1" "$2" <<'PY'
import sys
num = float(sys.argv[1])
den = float(sys.argv[2])
if den == 0.0:
    print("nan")
else:
    print(f"{num / den:.6f}")
PY
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

for path in "$BIN" "$TARGET" "$RNA" "$ROOT/scripts/restore_fasim_tfosorted_column_archive_probe.py"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/legacy" "$WORK/direct"

run_case() {
  local label="$1"
  local direct="$2"
  local out_dir="$WORK/$label"
  local run_start run_end restore_start restore_end
  run_start="$(now_seconds)"
  env \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
    FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
    FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH" \
    FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE=1 \
    FASIM_GASAL2_DIRECT_LITE_ARCHIVE_CONVERT="$direct" \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  run_end="$(now_seconds)"

  local archive_file
  archive_file="$(find "$out_dir" -maxdepth 1 -type f -name '*.column-archive.tfoa' | sort | head -n 1)"
  if [[ -z "$archive_file" || ! -s "$archive_file" ]]; then
    echo "missing $label column archive probe output" >&2
    exit 1
  fi
  restore_start="$(now_seconds)"
  python3 "$ROOT/scripts/restore_fasim_tfosorted_column_archive_probe.py" \
    --archive "$archive_file" \
    --output "$out_dir/restored-TFOsorted" \
    --query-fasta "$RNA" \
    --target-fasta "$TARGET" \
    >"$out_dir/restore.log"
  restore_end="$(now_seconds)"

  {
    printf 'run_wall_seconds=%s\n' "$(elapsed_seconds "$run_start" "$run_end")"
    printf 'restore_wall_seconds=%s\n' "$(elapsed_seconds "$restore_start" "$restore_end")"
    printf 'archive_file=%s\n' "$archive_file"
    printf 'archive_bytes=%s\n' "$(wc -c <"$archive_file")"
    printf 'archive_gzip_bytes=%s\n' "$(gzip -c "$archive_file" | wc -c)"
  } >"$out_dir/case_metrics.txt"
}

metric_value() {
  local file="$1"
  local key="$2"
  awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$file"
}

run_case legacy 0
run_case direct 1

direct_active="$(metric_value "$WORK/direct/stderr.log" benchmark.fasim_gasal2_direct_lite_archive_convert_active)"
if [[ "$direct_active" != "1" ]]; then
  echo "direct lite/archive convert did not activate: $direct_active" >&2
  exit 1
fi

legacy_active="$(metric_value "$WORK/legacy/stderr.log" benchmark.fasim_gasal2_direct_lite_archive_convert_active)"
if [[ "$legacy_active" != "0" ]]; then
  echo "legacy run unexpectedly activated direct convert: $legacy_active" >&2
  exit 1
fi

restored_equal=0
if [[ "$COMPARE_MODE" == "set" ]]; then
  comm -23 \
    <(LC_ALL=C sort "$WORK/legacy/restored-TFOsorted") \
    <(LC_ALL=C sort "$WORK/direct/restored-TFOsorted") \
    >"$WORK/legacy_only_rows.txt"
  comm -13 \
    <(LC_ALL=C sort "$WORK/legacy/restored-TFOsorted") \
    <(LC_ALL=C sort "$WORK/direct/restored-TFOsorted") \
    >"$WORK/direct_only_rows.txt"
  if [[ ! -s "$WORK/legacy_only_rows.txt" && ! -s "$WORK/direct_only_rows.txt" ]]; then
    restored_equal=1
  fi
elif [[ "$COMPARE_MODE" == "byte" ]]; then
  if cmp -s "$WORK/legacy/restored-TFOsorted" "$WORK/direct/restored-TFOsorted"; then
    restored_equal=1
  else
    comm -23 \
      <(LC_ALL=C sort "$WORK/legacy/restored-TFOsorted") \
      <(LC_ALL=C sort "$WORK/direct/restored-TFOsorted") \
      >"$WORK/legacy_only_rows.txt"
    comm -13 \
      <(LC_ALL=C sort "$WORK/legacy/restored-TFOsorted") \
      <(LC_ALL=C sort "$WORK/direct/restored-TFOsorted") \
      >"$WORK/direct_only_rows.txt"
  fi
else
  echo "unsupported COMPARE_MODE: $COMPARE_MODE" >&2
  exit 1
fi

{
  printf 'target=%s\n' "$TARGET"
  printf 'rna=%s\n' "$RNA"
  printf 'rule=%s\n' "$RULE"
  printf 'compare_mode=%s\n' "$COMPARE_MODE"
  printf 'legacy_restored_rows=%s\n' "$(metric_value "$WORK/legacy/restore.log" rows)"
  printf 'direct_restored_rows=%s\n' "$(metric_value "$WORK/direct/restore.log" rows)"
  printf 'direct_active=%s\n' "$direct_active"
  printf 'restored_equal=%s\n' "$restored_equal"
  if [[ "$restored_equal" != "1" ]]; then
    printf 'legacy_only_rows=%s\n' "$(wc -l <"$WORK/legacy_only_rows.txt")"
    printf 'direct_only_rows=%s\n' "$(wc -l <"$WORK/direct_only_rows.txt")"
  fi
  printf 'legacy_run_wall_seconds=%s\n' "$(metric_value "$WORK/legacy/case_metrics.txt" run_wall_seconds)"
  printf 'direct_run_wall_seconds=%s\n' "$(metric_value "$WORK/direct/case_metrics.txt" run_wall_seconds)"
  printf 'run_wall_speedup=%s\n' "$(ratio_seconds "$(metric_value "$WORK/legacy/case_metrics.txt" run_wall_seconds)" "$(metric_value "$WORK/direct/case_metrics.txt" run_wall_seconds)")"
  printf 'legacy_restore_wall_seconds=%s\n' "$(metric_value "$WORK/legacy/case_metrics.txt" restore_wall_seconds)"
  printf 'direct_restore_wall_seconds=%s\n' "$(metric_value "$WORK/direct/case_metrics.txt" restore_wall_seconds)"
  printf 'legacy_archive_bytes=%s\n' "$(metric_value "$WORK/legacy/case_metrics.txt" archive_bytes)"
  printf 'direct_archive_bytes=%s\n' "$(metric_value "$WORK/direct/case_metrics.txt" archive_bytes)"
  printf 'legacy_archive_gzip_bytes=%s\n' "$(metric_value "$WORK/legacy/case_metrics.txt" archive_gzip_bytes)"
  printf 'direct_archive_gzip_bytes=%s\n' "$(metric_value "$WORK/direct/case_metrics.txt" archive_gzip_bytes)"
  printf 'legacy_convert_wall_seconds=%s\n' "$(metric_value "$WORK/legacy/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds)"
  printf 'direct_convert_wall_seconds=%s\n' "$(metric_value "$WORK/direct/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds)"
  printf 'convert_wall_speedup=%s\n' "$(ratio_seconds "$(metric_value "$WORK/legacy/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds)" "$(metric_value "$WORK/direct/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds)")"
  printf 'legacy_convert_triplex_seconds=%s\n' "$(metric_value "$WORK/legacy/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_triplex_seconds)"
  printf 'direct_convert_triplex_seconds=%s\n' "$(metric_value "$WORK/direct/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_triplex_seconds)"
  printf 'convert_triplex_speedup=%s\n' "$(ratio_seconds "$(metric_value "$WORK/legacy/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_triplex_seconds)" "$(metric_value "$WORK/direct/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_triplex_seconds)")"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"

if [[ "$restored_equal" != "1" ]]; then
  echo "restored TFOsorted differs; see $WORK/legacy_only_rows.txt and $WORK/direct_only_rows.txt" >&2
  exit 1
fi
