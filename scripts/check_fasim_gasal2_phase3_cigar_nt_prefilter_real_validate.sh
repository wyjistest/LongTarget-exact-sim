#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase3_cigar_nt_prefilter_real_validate"}"
TARGET="${TARGET:-"$ROOT/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
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
  local value
  value="$(awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$file" 2>/dev/null || true)"
  if [[ -z "$value" ]]; then
    echo "missing metric $key in $file" >&2
    exit 1
  fi
  printf '%s' "$value"
}

if [[ ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
for path in "$BIN" "$TARGET" "$RNA" "$ROOT/scripts/restore_fasim_tfosorted_column_archive_probe.py"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK/baseline" "$WORK/real_validate"

run_case() {
  local label="$1"
  local real="$2"
  local validate="$3"
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
    FASIM_GASAL2_EQUIVALENCE_FIRST_CONVERT=1 \
    FASIM_GASAL2_PHASE3_CIGAR_NT_PREFILTER="$real" \
    FASIM_GASAL2_PHASE3_CIGAR_NT_PREFILTER_VALIDATE="$validate" \
    "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  end="$(now_seconds)"

  local archive_file
  archive_file="$(find "$out_dir" -maxdepth 1 -type f \( -name '*.column-archive.tfoa' -o -name '*.equivalence-first.tfoa' \) | sort | head -n 1)"
  if [[ -z "$archive_file" || ! -s "$archive_file" ]]; then
    echo "missing $label archive output" >&2
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
    printf 'run_wall_seconds=%s\n' "$(elapsed_seconds "$start" "$end")"
    printf 'restore_wall_seconds=%s\n' "$(elapsed_seconds "$restore_start" "$restore_end")"
    printf 'archive_file=%s\n' "$archive_file"
  } >"$out_dir/case_metrics.txt"
}

run_case baseline 0 0
run_case real_validate 1 1

restored_equal=0
legacy_only_rows=0
candidate_only_rows=0
if [[ "$COMPARE_MODE" == "byte" ]]; then
  if cmp -s "$WORK/baseline/restored-TFOsorted" "$WORK/real_validate/restored-TFOsorted"; then
    restored_equal=1
  else
    comm -23 \
      <(LC_ALL=C sort "$WORK/baseline/restored-TFOsorted") \
      <(LC_ALL=C sort "$WORK/real_validate/restored-TFOsorted") \
      >"$WORK/baseline_only_rows.txt"
    comm -13 \
      <(LC_ALL=C sort "$WORK/baseline/restored-TFOsorted") \
      <(LC_ALL=C sort "$WORK/real_validate/restored-TFOsorted") \
      >"$WORK/real_validate_only_rows.txt"
    legacy_only_rows="$(wc -l <"$WORK/baseline_only_rows.txt")"
    candidate_only_rows="$(wc -l <"$WORK/real_validate_only_rows.txt")"
  fi
elif [[ "$COMPARE_MODE" == "set" ]]; then
  comm -23 \
    <(LC_ALL=C sort "$WORK/baseline/restored-TFOsorted") \
    <(LC_ALL=C sort "$WORK/real_validate/restored-TFOsorted") \
    >"$WORK/baseline_only_rows.txt"
  comm -13 \
    <(LC_ALL=C sort "$WORK/baseline/restored-TFOsorted") \
    <(LC_ALL=C sort "$WORK/real_validate/restored-TFOsorted") \
    >"$WORK/real_validate_only_rows.txt"
  legacy_only_rows="$(wc -l <"$WORK/baseline_only_rows.txt")"
  candidate_only_rows="$(wc -l <"$WORK/real_validate_only_rows.txt")"
  if [[ "$legacy_only_rows" == "0" && "$candidate_only_rows" == "0" ]]; then
    restored_equal=1
  fi
else
  echo "unsupported COMPARE_MODE: $COMPARE_MODE" >&2
  exit 1
fi

prefix="benchmark.fasim_gasal2_phase3_cigar_nt_prefilter_"
requested="$(metric_value "$WORK/real_validate/stderr.log" "${prefix}requested")"
active="$(metric_value "$WORK/real_validate/stderr.log" "${prefix}active")"
real_requested="$(metric_value "$WORK/real_validate/stderr.log" "${prefix}real_requested")"
real_active="$(metric_value "$WORK/real_validate/stderr.log" "${prefix}real_active")"
validate_requested="$(metric_value "$WORK/real_validate/stderr.log" "${prefix}real_validate_requested")"
validate_active="$(metric_value "$WORK/real_validate/stderr.log" "${prefix}real_validate_active")"
skipped="$(metric_value "$WORK/real_validate/stderr.log" "${prefix}real_skipped_alignments")"
validated_skips="$(metric_value "$WORK/real_validate/stderr.log" "${prefix}real_validated_skips")"
mismatches="$(metric_value "$WORK/real_validate/stderr.log" "${prefix}real_validate_mismatches")"
fallbacks="$(metric_value "$WORK/real_validate/stderr.log" "${prefix}real_fallbacks")"
decision="$(metric_value "$WORK/real_validate/stderr.log" "${prefix}real_decision")"

baseline_real_active="$(metric_value "$WORK/baseline/stderr.log" "${prefix}real_active")"

{
  printf 'target=%s\n' "$TARGET"
  printf 'rna=%s\n' "$RNA"
  printf 'rule=%s\n' "$RULE"
  printf 'compare_mode=%s\n' "$COMPARE_MODE"
  printf 'requested=%s\n' "$requested"
  printf 'active=%s\n' "$active"
  printf 'real_requested=%s\n' "$real_requested"
  printf 'real_active=%s\n' "$real_active"
  printf 'real_validate_requested=%s\n' "$validate_requested"
  printf 'real_validate_active=%s\n' "$validate_active"
  printf 'real_skipped_alignments=%s\n' "$skipped"
  printf 'real_validated_skips=%s\n' "$validated_skips"
  printf 'real_validate_mismatches=%s\n' "$mismatches"
  printf 'real_fallbacks=%s\n' "$fallbacks"
  printf 'real_decision=%s\n' "$decision"
  printf 'baseline_real_active=%s\n' "$baseline_real_active"
  printf 'restored_equal=%s\n' "$restored_equal"
  printf 'legacy_only_rows=%s\n' "$legacy_only_rows"
  printf 'candidate_only_rows=%s\n' "$candidate_only_rows"
  printf 'baseline_rows=%s\n' "$(metric_value "$WORK/baseline/restore.log" rows)"
  printf 'real_validate_rows=%s\n' "$(metric_value "$WORK/real_validate/restore.log" rows)"
  printf 'baseline_run_wall_seconds=%s\n' "$(metric_value "$WORK/baseline/case_metrics.txt" run_wall_seconds)"
  printf 'real_validate_run_wall_seconds=%s\n' "$(metric_value "$WORK/real_validate/case_metrics.txt" run_wall_seconds)"
} >"$WORK/summary.txt"

cat "$WORK/summary.txt"

if [[ "$requested" != "1" || "$active" != "1" ]]; then
  echo "Phase 3 prefilter did not request/activate" >&2
  exit 1
fi
if [[ "$real_requested" != "1" || "$real_active" != "1" ]]; then
  echo "real Phase 3 prefilter did not request/activate" >&2
  exit 1
fi
if [[ "$validate_requested" != "1" || "$validate_active" != "1" ]]; then
  echo "real Phase 3 validate mode did not request/activate" >&2
  exit 1
fi
if [[ "$baseline_real_active" != "0" ]]; then
  echo "baseline unexpectedly activated real Phase 3 prefilter" >&2
  exit 1
fi
if [[ "$skipped" -le 0 || "$validated_skips" -le 0 ]]; then
  echo "expected validated real skips > 0" >&2
  exit 1
fi
if [[ "$mismatches" != "0" || "$fallbacks" != "0" ]]; then
  echo "real validate found mismatches/fallbacks" >&2
  exit 1
fi
if [[ "$decision" != "validated_clean" ]]; then
  echo "unexpected real prefilter decision: $decision" >&2
  exit 1
fi
if [[ "$restored_equal" != "1" ]]; then
  echo "real validate restored output differs" >&2
  exit 1
fi

echo "phase3_cigar_nt_prefilter_real_validate=pass"
echo "ok"
