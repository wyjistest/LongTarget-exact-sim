#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_phase3_cigar_nt_prefilter_real_validate_full"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
WORKLOADS="${WORKLOADS:-chr22 chr1}"
CHR22_TARGET="${CHR22_TARGET:-"$ROOT/.tmp/fasim_rule0_chr22_full_gasal2_gpu_score/input/chr22.fa"}"
CHR1_TARGET="${CHR1_TARGET:-"$ROOT/.tmp/fasim_gasal2_chr1_full_input/chr1.fa"}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
GASAL2_STREAMS="${GASAL2_STREAMS:-1}"
COMPARE_MODE="${COMPARE_MODE:-byte}"
RESTORE="$ROOT/scripts/restore_fasim_tfosorted_column_archive_probe.py"

if [[ ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
for path in "$BIN" "$RNA" "$RESTORE"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

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
print("0.000000" if den == 0.0 else f"{num / den:.6f}")
PY
}

metric_value() {
  local file="$1"
  local key="$2"
  local default="${3:-}"
  local value
  value="$(awk -F= -v key="$key" '$1 == key {print $2; found=1} END {if (!found) exit 1}' "$file" 2>/dev/null || true)"
  if [[ -z "$value" ]]; then
    printf '%s' "$default"
  else
    printf '%s' "$value"
  fi
}

target_for_workload() {
  case "$1" in
    chr22) printf '%s\n' "$CHR22_TARGET" ;;
    chr1) printf '%s\n' "$CHR1_TARGET" ;;
    *)
      echo "unknown workload: $1" >&2
      exit 1
      ;;
  esac
}

write_tsv_row() {
  local fields=("$@")
  local i
  for ((i = 0; i < ${#fields[@]}; ++i)); do
    if ((i > 0)); then
      printf '\t'
    fi
    printf '%s' "${fields[$i]}"
  done
  printf '\n'
}

write_header() {
  printf '%s\n' \
    'workload	target	attempted	compare_mode	baseline_real_active	phase3_requested	phase3_active	real_requested	real_active	real_validate_requested	real_validate_active	real_skipped_alignments	real_validated_skips	real_validate_mismatches	real_fallbacks	real_decision	restored_equal	legacy_only_rows	candidate_only_rows	baseline_rows	real_validate_rows	baseline_run_wall_seconds	real_validate_run_wall_seconds	run_wall_speedup	baseline_convert_wall_seconds	real_validate_convert_wall_seconds	convert_wall_speedup	baseline_restore_wall_seconds	real_validate_restore_wall_seconds	baseline_archive_path	real_validate_archive_path	decision'
}

write_missing_row() {
  local workload="$1"
  local target="$2"
  write_tsv_row \
    "$workload" "$target" 0 "$COMPARE_MODE" 0 0 0 0 0 0 0 0 0 0 0 \
    missing 0 0 0 0 0 0 0 0 0 0 0 0 0 NA NA missing_target
}

run_case() {
  local workload="$1"
  local target="$2"
  local label="$3"
  local real="$4"
  local validate="$5"
  local out_dir="$WORK/$workload/$label"
  local start end restore_start restore_end

  mkdir -p "$out_dir"
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
    "$BIN" -f1 "$target" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  end="$(now_seconds)"

  local archive_file
  archive_file="$(find "$out_dir" -maxdepth 1 -type f \( -name '*.column-archive.tfoa' -o -name '*.equivalence-first.tfoa' \) | sort | head -n 1)"
  if [[ -z "$archive_file" || ! -s "$archive_file" ]]; then
    echo "missing $workload/$label archive output" >&2
    exit 1
  fi

  restore_start="$(now_seconds)"
  python3 "$RESTORE" \
    --archive "$archive_file" \
    --output "$out_dir/restored-TFOsorted" \
    --query-fasta "$RNA" \
    --target-fasta "$target" \
    >"$out_dir/restore.log"
  restore_end="$(now_seconds)"

  {
    printf 'run_wall_seconds=%s\n' "$(elapsed_seconds "$start" "$end")"
    printf 'restore_wall_seconds=%s\n' "$(elapsed_seconds "$restore_start" "$restore_end")"
    printf 'archive_file=%s\n' "$archive_file"
  } >"$out_dir/case_metrics.txt"
}

write_header >"$WORK/report.tsv"

for workload in $WORKLOADS; do
  target="$(target_for_workload "$workload")"
  if [[ ! -s "$target" ]]; then
    write_missing_row "$workload" "$target" >>"$WORK/report.tsv"
    continue
  fi

  run_case "$workload" "$target" baseline 0 0
  run_case "$workload" "$target" real_validate 1 1

  baseline_dir="$WORK/$workload/baseline"
  candidate_dir="$WORK/$workload/real_validate"
  restored_equal=0
  legacy_only_rows=0
  candidate_only_rows=0
  if [[ "$COMPARE_MODE" == "byte" ]]; then
    if cmp -s "$baseline_dir/restored-TFOsorted" "$candidate_dir/restored-TFOsorted"; then
      restored_equal=1
    else
      comm -23 \
        <(LC_ALL=C sort "$baseline_dir/restored-TFOsorted") \
        <(LC_ALL=C sort "$candidate_dir/restored-TFOsorted") \
        >"$WORK/$workload/baseline_only_rows.txt"
      comm -13 \
        <(LC_ALL=C sort "$baseline_dir/restored-TFOsorted") \
        <(LC_ALL=C sort "$candidate_dir/restored-TFOsorted") \
        >"$WORK/$workload/real_validate_only_rows.txt"
      legacy_only_rows="$(wc -l <"$WORK/$workload/baseline_only_rows.txt")"
      candidate_only_rows="$(wc -l <"$WORK/$workload/real_validate_only_rows.txt")"
    fi
  elif [[ "$COMPARE_MODE" == "set" ]]; then
    comm -23 \
      <(LC_ALL=C sort "$baseline_dir/restored-TFOsorted") \
      <(LC_ALL=C sort "$candidate_dir/restored-TFOsorted") \
      >"$WORK/$workload/baseline_only_rows.txt"
    comm -13 \
      <(LC_ALL=C sort "$baseline_dir/restored-TFOsorted") \
      <(LC_ALL=C sort "$candidate_dir/restored-TFOsorted") \
      >"$WORK/$workload/real_validate_only_rows.txt"
    legacy_only_rows="$(wc -l <"$WORK/$workload/baseline_only_rows.txt")"
    candidate_only_rows="$(wc -l <"$WORK/$workload/real_validate_only_rows.txt")"
    if [[ "$legacy_only_rows" == "0" && "$candidate_only_rows" == "0" ]]; then
      restored_equal=1
    fi
  else
    echo "unsupported COMPARE_MODE: $COMPARE_MODE" >&2
    exit 1
  fi

  prefix="benchmark.fasim_gasal2_phase3_cigar_nt_prefilter_"
  baseline_real_active="$(metric_value "$baseline_dir/stderr.log" "${prefix}real_active" 0)"
  phase3_requested="$(metric_value "$candidate_dir/stderr.log" "${prefix}requested" 0)"
  phase3_active="$(metric_value "$candidate_dir/stderr.log" "${prefix}active" 0)"
  real_requested="$(metric_value "$candidate_dir/stderr.log" "${prefix}real_requested" 0)"
  real_active="$(metric_value "$candidate_dir/stderr.log" "${prefix}real_active" 0)"
  real_validate_requested="$(metric_value "$candidate_dir/stderr.log" "${prefix}real_validate_requested" 0)"
  real_validate_active="$(metric_value "$candidate_dir/stderr.log" "${prefix}real_validate_active" 0)"
  real_skipped="$(metric_value "$candidate_dir/stderr.log" "${prefix}real_skipped_alignments" 0)"
  real_validated="$(metric_value "$candidate_dir/stderr.log" "${prefix}real_validated_skips" 0)"
  real_mismatches="$(metric_value "$candidate_dir/stderr.log" "${prefix}real_validate_mismatches" 0)"
  real_fallbacks="$(metric_value "$candidate_dir/stderr.log" "${prefix}real_fallbacks" 0)"
  real_decision="$(metric_value "$candidate_dir/stderr.log" "${prefix}real_decision" missing)"

  baseline_run="$(metric_value "$baseline_dir/case_metrics.txt" run_wall_seconds 0)"
  candidate_run="$(metric_value "$candidate_dir/case_metrics.txt" run_wall_seconds 0)"
  baseline_convert="$(metric_value "$baseline_dir/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds 0)"
  candidate_convert="$(metric_value "$candidate_dir/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds 0)"
  baseline_restore="$(metric_value "$baseline_dir/case_metrics.txt" restore_wall_seconds 0)"
  candidate_restore="$(metric_value "$candidate_dir/case_metrics.txt" restore_wall_seconds 0)"
  baseline_archive="$(metric_value "$baseline_dir/case_metrics.txt" archive_file NA)"
  candidate_archive="$(metric_value "$candidate_dir/case_metrics.txt" archive_file NA)"
  baseline_rows="$(metric_value "$baseline_dir/restore.log" rows 0)"
  candidate_rows="$(metric_value "$candidate_dir/restore.log" rows 0)"
  run_speedup="$(ratio_seconds "$baseline_run" "$candidate_run")"
  convert_speedup="$(ratio_seconds "$baseline_convert" "$candidate_convert")"

  decision="real_validate_clean_no_speedup"
  if [[ "$restored_equal" == "1" &&
        "$real_mismatches" == "0" &&
        "$real_fallbacks" == "0" &&
        "$real_decision" == "validated_clean" ]]; then
    decision="$(python3 - "$run_speedup" "$convert_speedup" <<'PY'
import sys
run = float(sys.argv[1])
convert = float(sys.argv[2])
print("real_validate_clean_speedup" if run > 1.0 and convert > 1.0 else "real_validate_clean_no_speedup")
PY
)"
  fi

  write_tsv_row \
    "$workload" "$target" 1 "$COMPARE_MODE" "$baseline_real_active" \
    "$phase3_requested" "$phase3_active" "$real_requested" "$real_active" \
    "$real_validate_requested" "$real_validate_active" "$real_skipped" \
    "$real_validated" "$real_mismatches" "$real_fallbacks" "$real_decision" \
    "$restored_equal" "$legacy_only_rows" "$candidate_only_rows" \
    "$baseline_rows" "$candidate_rows" "$baseline_run" "$candidate_run" \
    "$run_speedup" "$baseline_convert" "$candidate_convert" \
    "$convert_speedup" "$baseline_restore" "$candidate_restore" \
    "$baseline_archive" "$candidate_archive" "$decision" \
    >>"$WORK/report.tsv"
done

cat "$WORK/report.tsv"
