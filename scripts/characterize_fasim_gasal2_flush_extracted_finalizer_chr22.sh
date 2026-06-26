#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_flush_extracted_finalizer_chr22"}"
TARGET="${TARGET:-"$ROOT/.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
REPEATS="${REPEATS:-3}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_STREAMS="${GASAL2_STREAMS:-3}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"

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

metric_or_default() {
  local file="$1"
  local key="$2"
  local default="$3"
  awk -F= -v key="$key" -v default="$default" '
    $1 == key {print $2; found=1}
    END {if (!found) print default}
  ' "$file"
}

time_metric_or_default() {
  local file="$1"
  local label="$2"
  local default="$3"
  if [[ ! -s "$file" ]]; then
    printf '%s\n' "$default"
    return
  fi
  awk -F: -v label="$label" -v default="$default" '
    $1 ~ label {
      value=$2
      gsub(/^[ \t]+/, "", value)
      print value
      found=1
    }
    END {if (!found) print default}
  ' "$file"
}

if [[ ! -x "$BIN" ]]; then
  (
    cd "$ROOT"
    make build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
  )
fi

for path in "$BIN" "$TARGET" "$RNA" "$ROOT/scripts/compare_fasim_lite_topk.py" "$ROOT/scripts/compare_fasim_full_run_determinism.py"; do
  if [[ ! -e "$path" ]]; then
    echo "missing dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

runs_tsv="$WORK/runs.tsv"
topk_tsv="$WORK/topk_compare.tsv"

printf '%s\n' \
  "case	repeat	wall_seconds	max_rss_kb	lite	lines	bytes	sha256	phase_flushes	gasal2_requests	gasal2_traceback_requests	gasal2_fallbacks	gasal2_length_guard_fallbacks	gasal2_total_seconds	gasal2_extend_wall_seconds	gasal2_convert_wall_seconds	exact_column_wall_seconds	output_write_seconds	extracted_requested	extracted_active	extracted_validate_requested	extracted_validate_active	extracted_ready_flushes	extracted_observed_flushes	extracted_eligible_flushes	extracted_committed_flushes	extracted_unsupported_flushes	extracted_legacy_fallback_flushes	extracted_legacy_finalizer_executed	extracted_extracted_finalizer_executed	extracted_comparison_performed	extracted_extracted_active_flushes	extracted_legacy_rows	extracted_extracted_rows	extracted_committed_rows	extracted_missing_rows	extracted_extra_rows	extracted_order_mismatches	extracted_cigar_mismatches	extracted_coordinate_mismatches	extracted_counter_mismatches	extracted_archive_descriptor_mismatches	extracted_legacy_seconds	extracted_extracted_seconds	extracted_compare_seconds	extracted_decision	ordered_ready_flushes	ordered_committed_flushes	ordered_order_violations	ordered_precommit_rows	ordered_appended_rows	ordered_result_bytes_p50	ordered_result_bytes_p90	ordered_result_bytes_max	ordered_traceback_bytes_p50	ordered_traceback_bytes_p90	ordered_traceback_bytes_max	ordered_result_bytes_includes_traceback	ordered_precommit_rows_bytes_p50	ordered_precommit_rows_bytes_p90	ordered_precommit_rows_bytes_max	ordered_projected_two_slot_peak_bytes	ordered_finalize_seconds	ordered_write_task_seconds	ordered_archive_seconds	ordered_counter_seconds	ordered_total_seconds	result_boundary_materialized_flushes	result_boundary_result_bytes	result_boundary_traceback_bytes	result_boundary_result_bytes_includes_traceback	result_boundary_materialize_seconds	result_boundary_finalize_seconds	result_boundary_commit_seconds" \
  >"$runs_tsv"

printf '%s\n' \
  "case	repeat	baseline	case_lite	top5_score_equal	top5_stability_equal	top5_nt_score_equal	missing_rows	extra_rows	baseline_unique_rows	candidate_unique_rows	status" \
  >"$topk_tsv"

run_paths=()
run_cases=()
run_repeats=()

run_case() {
  local case_name="$1"
  local repeat="$2"
  local extracted_enabled="$3"
  local validate_enabled="$4"
  local out_dir="$WORK/$case_name/run_$repeat"
  local start end lite time_log status

  mkdir -p "$out_dir"
  start="$(now_seconds)"
  if [[ -x /usr/bin/time ]]; then
    /usr/bin/time -v -o "$out_dir/time.txt" \
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
        FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER="$extracted_enabled" \
        FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER_VALIDATE="$validate_enabled" \
        "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
        >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
  else
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
      FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER="$extracted_enabled" \
      FASIM_GASAL2_FLUSH_EXTRACTED_FINALIZER_VALIDATE="$validate_enabled" \
      "$BIN" -f1 "$TARGET" -f2 "$RNA" -r "$RULE" -O "$out_dir" \
      >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
    : >"$out_dir/time.txt"
  fi
  end="$(now_seconds)"

  lite="$(find "$out_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  if [[ -z "$lite" || ! -s "$lite" ]]; then
    echo "missing lite output for $case_name repeat $repeat" >&2
    exit 1
  fi

  run_paths+=("$lite")
  run_cases+=("$case_name")
  run_repeats+=("$repeat")
  time_log="$out_dir/time.txt"

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s' \
    "$case_name" \
    "$repeat" \
    "$(elapsed_seconds "$start" "$end")" \
    "$(time_metric_or_default "$time_log" "Maximum resident set size" 0)" \
    "$lite" \
    "$(wc -l <"$lite")" \
    "$(stat -c%s "$lite")" \
    "$(sha256sum "$lite" | awk '{print $1}')" \
    >>"$runs_tsv"
  for key_default in \
    "benchmark.fasim_top5_gasal2_phase_flushes 0" \
    "benchmark.fasim_gasal2_requests 0" \
    "benchmark.fasim_gasal2_traceback_requests 0" \
    "benchmark.fasim_gasal2_fallbacks 0" \
    "benchmark.fasim_gasal2_length_guard_fallbacks 0" \
    "benchmark.fasim_gasal2_total_seconds 0" \
    "benchmark.fasim_top5_gasal2_phase_gasal2_extend_wall_seconds 0" \
    "benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds 0" \
    "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds 0" \
    "benchmark.fasim_top5_gasal2_phase_output_write_seconds 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_requested 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_active 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_validate_requested 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_validate_active 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_result_boundary_ready_flushes 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_flushes_observed 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_eligible_flushes 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_committed_flushes 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_unsupported_finalizer_shape_flushes 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_legacy_fallback_flushes 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_legacy_finalizer_executed 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_extracted_finalizer_executed 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_comparison_performed 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_extracted_active_flushes 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_legacy_rows 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_extracted_rows 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_committed_rows 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_missing_rows 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_extra_rows 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_order_mismatches 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_cigar_mismatches 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_coordinate_mismatches 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_counter_mismatches 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_archive_descriptor_mismatches 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_legacy_seconds 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_extracted_seconds 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_compare_seconds 0" \
    "benchmark.fasim_gasal2_extracted_finalizer_decision none" \
    "benchmark.fasim_gasal2_ordered_commit_flushes_ready 0" \
    "benchmark.fasim_gasal2_ordered_commit_flushes_committed 0" \
    "benchmark.fasim_gasal2_ordered_commit_order_violations 0" \
    "benchmark.fasim_gasal2_ordered_commit_precommit_rows 0" \
    "benchmark.fasim_gasal2_ordered_commit_appended_rows 0" \
    "benchmark.fasim_gasal2_ordered_commit_result_bytes_p50 0" \
    "benchmark.fasim_gasal2_ordered_commit_result_bytes_p90 0" \
    "benchmark.fasim_gasal2_ordered_commit_result_bytes_max 0" \
    "benchmark.fasim_gasal2_ordered_commit_traceback_bytes_p50 0" \
    "benchmark.fasim_gasal2_ordered_commit_traceback_bytes_p90 0" \
    "benchmark.fasim_gasal2_ordered_commit_traceback_bytes_max 0" \
    "benchmark.fasim_gasal2_ordered_commit_result_bytes_includes_traceback 0" \
    "benchmark.fasim_gasal2_ordered_commit_precommit_rows_bytes_p50 0" \
    "benchmark.fasim_gasal2_ordered_commit_precommit_rows_bytes_p90 0" \
    "benchmark.fasim_gasal2_ordered_commit_precommit_rows_bytes_max 0" \
    "benchmark.fasim_gasal2_ordered_commit_projected_two_slot_peak_bytes 0" \
    "benchmark.fasim_gasal2_ordered_commit_finalize_seconds 0" \
    "benchmark.fasim_gasal2_ordered_commit_write_task_seconds 0" \
    "benchmark.fasim_gasal2_ordered_commit_archive_seconds 0" \
    "benchmark.fasim_gasal2_ordered_commit_counter_seconds 0" \
    "benchmark.fasim_gasal2_ordered_commit_total_seconds 0" \
    "benchmark.fasim_gasal2_flush_result_boundary_materialized_flushes 0" \
    "benchmark.fasim_gasal2_flush_result_boundary_result_bytes 0" \
    "benchmark.fasim_gasal2_flush_result_boundary_traceback_bytes 0" \
    "benchmark.fasim_gasal2_flush_result_boundary_result_bytes_includes_traceback 0" \
    "benchmark.fasim_gasal2_flush_result_boundary_materialize_seconds 0" \
    "benchmark.fasim_gasal2_flush_result_boundary_finalize_seconds 0" \
    "benchmark.fasim_gasal2_flush_result_boundary_commit_seconds 0"; do
    read -r key default <<<"$key_default"
    printf '\t%s' "$(metric_or_default "$out_dir/stderr.log" "$key" "$default")" >>"$runs_tsv"
  done
  printf '\n' >>"$runs_tsv"

  printf '%s\n' "completed $case_name repeat $repeat: $lite"
}

for repeat in $(seq 1 "$REPEATS"); do
  run_case legacy "$repeat" 0 0
  run_case extracted "$repeat" 1 0
  run_case extracted_validate "$repeat" 1 1
done

baseline_lite="${run_paths[0]}"
for i in "${!run_paths[@]}"; do
  case_name="${run_cases[$i]}"
  repeat="${run_repeats[$i]}"
  lite="${run_paths[$i]}"
  compare_out="$WORK/${case_name}_run_${repeat}_topk_compare.txt"
  status="clean"
  if ! python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
      --baseline "$baseline_lite" \
      --candidate "$lite" \
      --k 5 \
      >"$compare_out"; then
    status="mismatch"
  fi
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$case_name" \
    "$repeat" \
    "$baseline_lite" \
    "$lite" \
    "$(metric_or_default "$compare_out" top5_score_equal false)" \
    "$(metric_or_default "$compare_out" top5_stability_equal false)" \
    "$(metric_or_default "$compare_out" top5_nt_score_equal false)" \
    "$(metric_or_default "$compare_out" missing_rows 0)" \
    "$(metric_or_default "$compare_out" extra_rows 0)" \
    "$(metric_or_default "$compare_out" baseline_unique_rows 0)" \
    "$(metric_or_default "$compare_out" candidate_unique_rows 0)" \
    "$status" \
    >>"$topk_tsv"
done

compare_args=()
for path in "${run_paths[@]}"; do
  compare_args+=(--run "$path")
done
python3 "$ROOT/scripts/compare_fasim_full_run_determinism.py" \
  "${compare_args[@]}" \
  --k 5 \
  --output-summary "$WORK/determinism_summary.txt" \
  --output-pairs "$WORK/determinism_pairs.tsv"

python3 - "$runs_tsv" "$WORK/summary.txt" <<'PY'
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

runs_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
rows = list(csv.DictReader(runs_path.open(), delimiter="\t"))
cases = sorted({row["case"] for row in rows})

def as_float(row: dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, "0") or "0")
    except ValueError:
        return 0.0

def median_for(case: str) -> float:
    values = [as_float(row, "wall_seconds") for row in rows if row["case"] == case]
    return statistics.median(values) if values else 0.0

def fmt(value: float) -> str:
    return f"{value:.6f}"

out: list[tuple[str, str]] = []
out.append(("runs", str(len(rows))))
out.append(("cases", ",".join(cases)))
for case in cases:
    values = [as_float(row, "wall_seconds") for row in rows if row["case"] == case]
    out.append((f"{case}_runs", str(len(values))))
    if values:
        out.append((f"{case}_wall_min_seconds", fmt(min(values))))
        out.append((f"{case}_wall_median_seconds", fmt(statistics.median(values))))
        out.append((f"{case}_wall_max_seconds", fmt(max(values))))
legacy = median_for("legacy")
for case in ("extracted", "extracted_validate"):
    value = median_for(case)
    overhead = 0.0 if legacy == 0.0 else (value - legacy) / legacy
    ratio = 0.0 if legacy == 0.0 else value / legacy
    out.append((f"{case}_wall_overhead_fraction_vs_legacy", fmt(overhead)))
    out.append((f"{case}_wall_ratio_vs_legacy", fmt(ratio)))
out.append(("decision", "chr22_extracted_finalizer_characterization_recorded"))
summary_path.write_text("\n".join(f"{k}={v}" for k, v in out) + "\n")
PY

{
  printf 'target=%s\n' "$TARGET"
  printf 'rna=%s\n' "$RNA"
  printf 'rule=%s\n' "$RULE"
  printf 'repeats=%s\n' "$REPEATS"
  printf 'gasal2_streams=%s\n' "$GASAL2_STREAMS"
  printf 'gasal2_batch=%s\n' "$GASAL2_BATCH"
  printf 'prune_max_per_task=%s\n' "$PRUNE_MAX_PER_TASK"
  cat "$WORK/summary.txt"
  cat "$WORK/determinism_summary.txt"
} >"$WORK/report.txt"

cat "$WORK/report.txt"
