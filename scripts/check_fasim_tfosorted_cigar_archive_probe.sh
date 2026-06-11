#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_tfosorted_cigar_archive_probe"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
ARCHIVE_OUTPUT_MODE="${ARCHIVE_OUTPUT_MODE:-tfosorted}"
SKIP_FULL="${SKIP_FULL:-0}"
BASELINE_OUTPUT="${BASELINE_OUTPUT:-}"
BASELINE_WALL_SECONDS="${BASELINE_WALL_SECONDS:-NA}"

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 \
      CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
      CUDA_ARCH="${CUDA_ARCH:-89}" \
      FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$TARGET" "$RNA" "$ROOT/scripts/restore_fasim_tfosorted_cigar_archive_probe.py"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/full" "$WORK/archive"

find_tfosorted_output() {
  local dir="$1"
  find "$dir" -maxdepth 1 -type f -name '*-TFOsorted' ! -name 'restored-TFOsorted' | sort | head -n 1
}

now_seconds() {
  python3 - <<'PY'
import time
print(f"{time.time():.9f}")
PY
}

elapsed_seconds() {
  python3 - "$1" "$2" <<'PY'
import sys
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
PY
}

if [[ "$SKIP_FULL" == "1" ]]; then
  if [[ -z "$BASELINE_OUTPUT" || ! -s "$BASELINE_OUTPUT" ]]; then
    echo "SKIP_FULL=1 requires BASELINE_OUTPUT" >&2
    exit 1
  fi
  full_out="$BASELINE_OUTPUT"
  full_wall_seconds="$BASELINE_WALL_SECONDS"
  : >"$WORK/full/stderr.log"
else
  full_start="$(now_seconds)"
  env \
    FASIM_OUTPUT_MODE=tfosorted \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
    FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
    FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH" \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$WORK/full" \
    >"$WORK/full/stdout.log" 2>"$WORK/full/stderr.log"
  full_end="$(now_seconds)"
  full_wall_seconds="$(elapsed_seconds "$full_start" "$full_end")"
  full_out="$(find_tfosorted_output "$WORK/full")"
fi
if [[ -z "$full_out" || ! -s "$full_out" ]]; then
  echo "missing full TFOsorted output" >&2
  exit 1
fi

archive_start="$(now_seconds)"
env \
  FASIM_OUTPUT_MODE="$ARCHIVE_OUTPUT_MODE" \
  FASIM_VERBOSE=0 \
  FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
  FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
  FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
  FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
  FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
  FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH" \
  FASIM_TFOSORTED_CIGAR_ARCHIVE_PROBE=1 \
  "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$WORK/archive" \
  >"$WORK/archive/stdout.log" 2>"$WORK/archive/stderr.log"
archive_end="$(now_seconds)"
archive_wall_seconds="$(elapsed_seconds "$archive_start" "$archive_end")"

archive_file="$(find "$WORK/archive" -maxdepth 1 -type f -name '*.cigar-archive.tsv' | sort | head -n 1)"
if [[ -z "$archive_file" || ! -s "$archive_file" ]]; then
  echo "missing CIGAR archive probe output" >&2
  exit 1
fi

restore_start="$(now_seconds)"
python3 "$ROOT/scripts/restore_fasim_tfosorted_cigar_archive_probe.py" \
  --archive "$archive_file" \
  --output "$WORK/archive/restored-TFOsorted" \
  --query-fasta "$RNA" \
  --target-fasta "$TARGET" \
  >"$WORK/archive/restore.log"
restore_end="$(now_seconds)"
restore_wall_seconds="$(elapsed_seconds "$restore_start" "$restore_end")"

baseline_restored_match=0
if cmp -s "$full_out" "$WORK/archive/restored-TFOsorted"; then
  baseline_restored_match=1
fi

archive_full_out="$(find_tfosorted_output "$WORK/archive")"
archive_full_restored_match="NA"
if [[ "$ARCHIVE_OUTPUT_MODE" == "tfosorted" ]]; then
  if [[ -z "$archive_full_out" || ! -s "$archive_full_out" ]]; then
    echo "missing archive-run full TFOsorted output" >&2
    exit 1
  fi
  cmp "$archive_full_out" "$WORK/archive/restored-TFOsorted"
  archive_full_restored_match=1
fi

extract_metric() {
  local file="$1"
  local key="$2"
  local default="${3:-0}"
  local value
  value="$(awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$file" 2>/dev/null || true)"
  if [[ -z "$value" ]]; then
    printf '%s' "$default"
  else
    printf '%s' "$value"
  fi
}

{
  printf 'target=%s\n' "$TARGET"
  printf 'rna=%s\n' "$RNA"
  printf 'rule=%s\n' "$RULE"
  printf 'full_wall_seconds=%s\n' "$full_wall_seconds"
  printf 'archive_wall_seconds=%s\n' "$archive_wall_seconds"
  printf 'archive_output_mode=%s\n' "$ARCHIVE_OUTPUT_MODE"
  printf 'restore_wall_seconds=%s\n' "$restore_wall_seconds"
  printf 'full_output=%s\n' "$full_out"
  printf 'archive_output=%s\n' "$archive_file"
  printf 'archive_full_output=%s\n' "${archive_full_out:-}"
  printf 'restored_output=%s\n' "$WORK/archive/restored-TFOsorted"
  printf 'baseline_restored_match=%s\n' "$baseline_restored_match"
  printf 'archive_full_restored_match=%s\n' "$archive_full_restored_match"
  printf 'full_bytes=%s\n' "$(stat -c%s "$full_out")"
  printf 'archive_bytes=%s\n' "$(stat -c%s "$archive_file")"
  printf 'restored_bytes=%s\n' "$(stat -c%s "$WORK/archive/restored-TFOsorted")"
  printf 'full_convert_alignment_seconds=%s\n' "$(extract_metric "$WORK/full/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_alignment_seconds NA)"
  printf 'archive_convert_alignment_seconds=%s\n' "$(extract_metric "$WORK/archive/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_alignment_seconds)"
  printf 'full_cpu_traceback_convert_seconds=%s\n' "$(extract_metric "$WORK/full/stderr.log" benchmark.fasim_gasal2_cpu_traceback_convert_seconds NA)"
  printf 'archive_cpu_traceback_convert_seconds=%s\n' "$(extract_metric "$WORK/archive/stderr.log" benchmark.fasim_gasal2_cpu_traceback_convert_seconds)"
  printf 'full_output_write_seconds=%s\n' "$(extract_metric "$WORK/full/stderr.log" benchmark.fasim_top5_gasal2_phase_output_write_seconds NA)"
  printf 'archive_output_write_seconds=%s\n' "$(extract_metric "$WORK/archive/stderr.log" benchmark.fasim_top5_gasal2_phase_output_write_seconds)"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"
