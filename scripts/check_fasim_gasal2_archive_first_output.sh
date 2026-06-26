#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_archive_first_output"}"
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
print(f"{float(sys.argv[2]) - float(sys.argv[1]):.6f}")
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

for path in "$BIN" "$TARGET" "$RNA" \
  "$ROOT/scripts/restore_fasim_tfosorted_column_archive_probe.py" \
  "$ROOT/scripts/check_fasim_tfo_archive_integrity.py"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/legacy" "$WORK/archive"

run_case() {
  local label="$1"
  local archive_first="$2"
  local out_dir="$WORK/$label"
  local start end
  start="$(now_seconds)"
  env \
    FASIM_OUTPUT_MODE=tfosorted \
    FASIM_VERBOSE=0 \
    FASIM_TOP5_GASAL2_PHASE_TIMING=1 \
    FASIM_TOP5_GASAL2_GPU_SCOREINFO=1 \
    FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1 \
    FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK="$PRUNE_MAX_PER_TASK" \
    FASIM_ALIGN_GASAL2_STREAMS="$GASAL2_STREAMS" \
    FASIM_ALIGN_GASAL2_BATCH="$GASAL2_BATCH" \
    FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT="$archive_first" \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  end="$(now_seconds)"
  printf 'run_wall_seconds=%s\n' "$(elapsed_seconds "$start" "$end")" >"$out_dir/case_metrics.txt"
}

run_case legacy 0
run_case archive 1

requested="$(metric_value "$WORK/archive/stderr.log" benchmark.fasim_gasal2_archive_first_output_requested)"
active="$(metric_value "$WORK/archive/stderr.log" benchmark.fasim_gasal2_archive_first_output_active)"
decision="$(metric_value "$WORK/archive/stderr.log" benchmark.fasim_gasal2_archive_first_output_decision)"
legacy_active="$(metric_value "$WORK/legacy/stderr.log" benchmark.fasim_gasal2_archive_first_output_active)"

if [[ "$requested" != "1" || "$active" != "1" || "$decision" != "active" ]]; then
  echo "archive-first output did not activate: requested=$requested active=$active decision=$decision" >&2
  exit 1
fi
if [[ "$legacy_active" != "0" ]]; then
  echo "legacy run unexpectedly activated archive-first output" >&2
  exit 1
fi

legacy_out="$(find "$WORK/legacy" -maxdepth 1 -type f -name '*-TFOsorted' | sort | head -n 1)"
if [[ -z "$legacy_out" || ! -s "$legacy_out" ]]; then
  echo "missing legacy TFOsorted output" >&2
  exit 1
fi

archive_text_out="$(find "$WORK/archive" -maxdepth 1 -type f -name '*-TFOsorted' | sort | head -n 1)"
if [[ -n "$archive_text_out" ]]; then
  echo "archive-first fast path unexpectedly wrote full TFOsorted: $archive_text_out" >&2
  exit 1
fi

archive_file="$(find "$WORK/archive" -maxdepth 1 -type f -name '*.archive-first.tfoa' | sort | head -n 1)"
if [[ -z "$archive_file" || ! -s "$archive_file" ]]; then
  echo "missing archive-first tfoa output" >&2
  exit 1
fi

restore_start="$(now_seconds)"
restore_command=(
  python3 "$ROOT/scripts/restore_fasim_tfosorted_column_archive_probe.py"
  --archive "$archive_file"
  --output "$WORK/archive/restored-TFOsorted"
  --query-fasta "$RNA"
  --target-fasta "$TARGET"
)
"${restore_command[@]}" \
  >"$WORK/archive/restore.log"
restore_end="$(now_seconds)"

python3 "$ROOT/scripts/check_fasim_tfo_archive_integrity.py" \
  --archive "$archive_file" \
  --query-fasta "$RNA" \
  --target-fasta "$TARGET" \
  --restore-log "$WORK/archive/restore.log" \
  --restored-output "$WORK/archive/restored-TFOsorted" \
  >"$WORK/archive/integrity.txt"

manifest="$WORK/archive/archive-manifest.tsv"
{
  printf 'archive_manifest_schema\tFASIM_TFO_ARCHIVE_MANIFEST_V1\n'
  printf 'archive_path\t%s\n' "$archive_file"
  awk -F= '
    $1 == "archive_sha256" { printf "archive_sha256\t%s\n", $2 }
    $1 == "archive_magic" { printf "archive_magic\t%s\n", $2 }
    $1 == "archive_version" { printf "archive_version\t%s\n", $2 }
    $1 == "archive_terminator_present" { printf "archive_terminator_present\t%s\n", $2 }
  ' "$WORK/archive/integrity.txt"
  printf 'query_fasta_path\t%s\n' "$RNA"
  awk -F= '$1 == "query_fasta_sha256" { printf "query_fasta_sha256\t%s\n", $2 }' "$WORK/archive/integrity.txt"
  printf 'target_fasta_path\t%s\n' "$TARGET"
  awk -F= '$1 == "target_fasta_sha256" { printf "target_fasta_sha256\t%s\n", $2 }' "$WORK/archive/integrity.txt"
  printf 'restored_output_path\t%s\n' "$WORK/archive/restored-TFOsorted"
  awk -F= '$1 == "restored_sha256" { printf "restored_sha256\t%s\n", $2 }' "$WORK/archive/integrity.txt"
  printf 'restore_command\t'
  printf '%q ' "${restore_command[@]}"
  printf '\n'
  awk -F= '
    $1 == "restore_rows" { printf "restore_rows\t%s\n", $2 }
    $1 == "archive_bytes" { printf "archive_bytes\t%s\n", $2 }
    $1 == "restored_bytes" { printf "restored_bytes\t%s\n", $2 }
  ' "$WORK/archive/integrity.txt"
} >"$manifest"

python3 "$ROOT/scripts/check_fasim_gasal2_archive_manifest.py" \
  --manifest "$manifest" \
  >"$WORK/archive/manifest_check.txt"

restored_equal=0
legacy_only_rows=0
archive_only_rows=0
if [[ "$COMPARE_MODE" == "byte" ]]; then
  if cmp -s "$legacy_out" "$WORK/archive/restored-TFOsorted"; then
    restored_equal=1
  else
    comm -23 \
      <(LC_ALL=C sort "$legacy_out") \
      <(LC_ALL=C sort "$WORK/archive/restored-TFOsorted") \
      >"$WORK/legacy_only_rows.txt"
    comm -13 \
      <(LC_ALL=C sort "$legacy_out") \
      <(LC_ALL=C sort "$WORK/archive/restored-TFOsorted") \
      >"$WORK/archive_only_rows.txt"
    legacy_only_rows="$(wc -l <"$WORK/legacy_only_rows.txt")"
    archive_only_rows="$(wc -l <"$WORK/archive_only_rows.txt")"
  fi
elif [[ "$COMPARE_MODE" == "set" ]]; then
  comm -23 \
    <(LC_ALL=C sort "$legacy_out") \
    <(LC_ALL=C sort "$WORK/archive/restored-TFOsorted") \
    >"$WORK/legacy_only_rows.txt"
  comm -13 \
    <(LC_ALL=C sort "$legacy_out") \
    <(LC_ALL=C sort "$WORK/archive/restored-TFOsorted") \
    >"$WORK/archive_only_rows.txt"
  legacy_only_rows="$(wc -l <"$WORK/legacy_only_rows.txt")"
  archive_only_rows="$(wc -l <"$WORK/archive_only_rows.txt")"
  if [[ "$legacy_only_rows" == "0" && "$archive_only_rows" == "0" ]]; then
    restored_equal=1
  fi
else
  echo "unsupported COMPARE_MODE: $COMPARE_MODE" >&2
  exit 1
fi

gzip -c "$archive_file" >"$archive_file.gz"

{
  printf 'target=%s\n' "$TARGET"
  printf 'rna=%s\n' "$RNA"
  printf 'rule=%s\n' "$RULE"
  printf 'compare_mode=%s\n' "$COMPARE_MODE"
  printf 'archive_first_requested=%s\n' "$requested"
  printf 'archive_first_active=%s\n' "$active"
  printf 'archive_first_decision=%s\n' "$decision"
  printf 'restored_equal=%s\n' "$restored_equal"
  printf 'legacy_only_rows=%s\n' "$legacy_only_rows"
  printf 'archive_only_rows=%s\n' "$archive_only_rows"
  printf 'restored_rows=%s\n' "$(metric_value "$WORK/archive/restore.log" rows)"
  printf 'legacy_run_wall_seconds=%s\n' "$(metric_value "$WORK/legacy/case_metrics.txt" run_wall_seconds)"
  printf 'archive_run_wall_seconds=%s\n' "$(metric_value "$WORK/archive/case_metrics.txt" run_wall_seconds)"
  printf 'restore_wall_seconds=%s\n' "$(elapsed_seconds "$restore_start" "$restore_end")"
  printf 'legacy_text_bytes=%s\n' "$(stat -c%s "$legacy_out")"
  printf 'archive_bytes=%s\n' "$(stat -c%s "$archive_file")"
  printf 'archive_gzip_bytes=%s\n' "$(stat -c%s "$archive_file.gz")"
  printf 'archive_manifest=%s\n' "$manifest"
  awk -F= '
    $1 == "archive_manifest_valid" ||
    $1 == "restore_command_present" ||
    $1 == "restore_command_has_archive" ||
    $1 == "restore_command_has_output" ||
    $1 == "restore_command_has_query_fasta" ||
    $1 == "restore_command_has_target_fasta" ||
    $1 == "archive_manifest_decision" {
      print
    }
  ' "$WORK/archive/manifest_check.txt"
  awk -F= '
    $1 == "archive_magic" ||
    $1 == "archive_version" ||
    $1 == "archive_terminator_present" ||
    $1 == "archive_sha256" ||
    $1 == "query_fasta_sha256" ||
    $1 == "target_fasta_sha256" ||
    $1 == "restored_sha256" ||
    $1 == "query_bases" ||
    $1 == "target_bases" {
      print
    }
  ' "$WORK/archive/integrity.txt"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"

if [[ "$restored_equal" != "1" ]]; then
  echo "archive-first restored TFOsorted differs; see $WORK/legacy_only_rows.txt and $WORK/archive_only_rows.txt" >&2
  exit 1
fi
