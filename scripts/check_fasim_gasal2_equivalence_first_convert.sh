#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_equivalence_first_convert"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
COMPARE_MODE="${COMPARE_MODE:-byte}"
if [[ -z "${GASAL2_STREAMS+x}" ]]; then
  if [[ "$COMPARE_MODE" == "set" ]]; then
    GASAL2_STREAMS=1
  else
    GASAL2_STREAMS=3
  fi
fi

now_seconds() {
  python3 - <<'PY'
import time
print(f"{time.perf_counter():.9f}")
PY
}

elapsed_seconds() {
  python3 - "$1" "$2" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
}

ratio_seconds() {
  python3 - "$1" "$2" <<'PY'
import sys
num = float(sys.argv[1])
den = float(sys.argv[2])
print("nan" if den == 0.0 else f"{num / den:.6f}")
PY
}

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

for path in "$BIN" "$TARGET" "$RNA" "$ROOT/scripts/restore_fasim_tfosorted_column_archive_probe.py"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/legacy" "$WORK/equivalence"

run_case() {
  local label="$1"
  local enabled="$2"
  local out_dir="$WORK/$label"
  local start end restore_start restore_end
  start="$(now_seconds)"
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
    FASIM_GASAL2_EQUIVALENCE_FIRST_CONVERT="$enabled" \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  end="$(now_seconds)"

  local archive_file
  archive_file="$(find "$out_dir" -maxdepth 1 -type f \( -name '*.column-archive.tfoa' -o -name '*.equivalence-first.tfoa' \) | sort | head -n 1)"
  if [[ -z "$archive_file" || ! -s "$archive_file" ]]; then
    echo "missing $label column archive output" >&2
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

  gzip -c "$archive_file" >"$archive_file.gz"
  {
    printf 'run_wall_seconds=%s\n' "$(elapsed_seconds "$start" "$end")"
    printf 'restore_wall_seconds=%s\n' "$(elapsed_seconds "$restore_start" "$restore_end")"
    printf 'archive_file=%s\n' "$archive_file"
    printf 'archive_bytes=%s\n' "$(stat -c%s "$archive_file")"
    printf 'archive_gzip_bytes=%s\n' "$(stat -c%s "$archive_file.gz")"
  } >"$out_dir/case_metrics.txt"
}

run_case legacy 0
run_case equivalence 1

requested="$(metric_value "$WORK/equivalence/stderr.log" benchmark.fasim_gasal2_equivalence_first_convert_requested)"
active="$(metric_value "$WORK/equivalence/stderr.log" benchmark.fasim_gasal2_equivalence_first_convert_active)"
decision="$(metric_value "$WORK/equivalence/stderr.log" benchmark.fasim_gasal2_equivalence_first_convert_decision)"
legacy_active="$(metric_value "$WORK/legacy/stderr.log" benchmark.fasim_gasal2_equivalence_first_convert_active)"

if [[ "$requested" != "1" || "$active" != "1" || "$decision" != "active" ]]; then
  echo "equivalence-first convert did not activate: requested=$requested active=$active decision=$decision" >&2
  exit 1
fi
if [[ "$legacy_active" != "0" ]]; then
  echo "legacy run unexpectedly activated equivalence-first convert" >&2
  exit 1
fi

restored_equal=0
legacy_only_rows=0
new_only_rows=0
if [[ "$COMPARE_MODE" == "byte" ]]; then
  if cmp -s "$WORK/legacy/restored-TFOsorted" "$WORK/equivalence/restored-TFOsorted"; then
    restored_equal=1
  else
    comm -23 \
      <(LC_ALL=C sort "$WORK/legacy/restored-TFOsorted") \
      <(LC_ALL=C sort "$WORK/equivalence/restored-TFOsorted") \
      >"$WORK/legacy_only_rows.txt"
    comm -13 \
      <(LC_ALL=C sort "$WORK/legacy/restored-TFOsorted") \
      <(LC_ALL=C sort "$WORK/equivalence/restored-TFOsorted") \
      >"$WORK/new_only_rows.txt"
    legacy_only_rows="$(wc -l <"$WORK/legacy_only_rows.txt")"
    new_only_rows="$(wc -l <"$WORK/new_only_rows.txt")"
  fi
elif [[ "$COMPARE_MODE" == "set" ]]; then
  comm -23 \
    <(LC_ALL=C sort "$WORK/legacy/restored-TFOsorted") \
    <(LC_ALL=C sort "$WORK/equivalence/restored-TFOsorted") \
    >"$WORK/legacy_only_rows.txt"
  comm -13 \
    <(LC_ALL=C sort "$WORK/legacy/restored-TFOsorted") \
    <(LC_ALL=C sort "$WORK/equivalence/restored-TFOsorted") \
    >"$WORK/new_only_rows.txt"
  legacy_only_rows="$(wc -l <"$WORK/legacy_only_rows.txt")"
  new_only_rows="$(wc -l <"$WORK/new_only_rows.txt")"
  if [[ "$legacy_only_rows" == "0" && "$new_only_rows" == "0" ]]; then
    restored_equal=1
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
  printf 'gasal2_streams=%s\n' "$GASAL2_STREAMS"
  printf 'gasal2_batch=%s\n' "$GASAL2_BATCH"
  printf 'prune_max_per_task=%s\n' "$PRUNE_MAX_PER_TASK"
  printf 'equivalence_first_requested=%s\n' "$requested"
  printf 'equivalence_first_active=%s\n' "$active"
  printf 'equivalence_first_decision=%s\n' "$decision"
  printf 'restored_equal=%s\n' "$restored_equal"
  printf 'legacy_only_rows=%s\n' "$legacy_only_rows"
  printf 'new_only_rows=%s\n' "$new_only_rows"
  printf 'legacy_restored_rows=%s\n' "$(metric_value "$WORK/legacy/restore.log" rows)"
  printf 'new_restored_rows=%s\n' "$(metric_value "$WORK/equivalence/restore.log" rows)"
  printf 'legacy_run_wall_seconds=%s\n' "$(metric_value "$WORK/legacy/case_metrics.txt" run_wall_seconds)"
  printf 'new_run_wall_seconds=%s\n' "$(metric_value "$WORK/equivalence/case_metrics.txt" run_wall_seconds)"
  printf 'run_wall_speedup=%s\n' "$(ratio_seconds "$(metric_value "$WORK/legacy/case_metrics.txt" run_wall_seconds)" "$(metric_value "$WORK/equivalence/case_metrics.txt" run_wall_seconds)")"
  printf 'legacy_convert_wall_seconds=%s\n' "$(metric_value "$WORK/legacy/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds)"
  printf 'new_convert_wall_seconds=%s\n' "$(metric_value "$WORK/equivalence/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds)"
  printf 'convert_wall_speedup=%s\n' "$(ratio_seconds "$(metric_value "$WORK/legacy/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds)" "$(metric_value "$WORK/equivalence/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds)")"
  printf 'legacy_archive_bytes=%s\n' "$(metric_value "$WORK/legacy/case_metrics.txt" archive_bytes)"
  printf 'new_archive_bytes=%s\n' "$(metric_value "$WORK/equivalence/case_metrics.txt" archive_bytes)"
  printf 'legacy_archive_gzip_bytes=%s\n' "$(metric_value "$WORK/legacy/case_metrics.txt" archive_gzip_bytes)"
  printf 'new_archive_gzip_bytes=%s\n' "$(metric_value "$WORK/equivalence/case_metrics.txt" archive_gzip_bytes)"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"

if [[ "$restored_equal" != "1" ]]; then
  echo "equivalence-first restored TFOsorted differs; see $WORK/legacy_only_rows.txt and $WORK/new_only_rows.txt" >&2
  exit 1
fi
