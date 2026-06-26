#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_phase3_cigar_nt_prefilter_full"}"
RNA="${RNA:-"$ROOT/H19.fa"}"
RULE="${RULE:-0}"
WORKLOADS="${WORKLOADS:-chr22 chr1}"
CHR22_TARGET="${CHR22_TARGET:-"$ROOT/.tmp/fasim_rule0_chr22_full_gasal2_gpu_score/input/chr22.fa"}"
CHR1_TARGET="${CHR1_TARGET:-"$ROOT/.tmp/fasim_gasal2_chr1_full_input/chr1.fa"}"
PRUNE_MAX_PER_TASK="${PRUNE_MAX_PER_TASK:-256}"
GASAL2_BATCH="${GASAL2_BATCH:-20000}"
GASAL2_STREAMS="${GASAL2_STREAMS:-1}"
ANALYZER="$ROOT/scripts/analyze_fasim_gasal2_task_frontier_proof.py"

if [[ ! -x "$BIN" ]]; then
  make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
fi
for path in "$BIN" "$RNA" "$ANALYZER"; do
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

write_header() {
  printf '%s\n' \
    'workload	target	attempted	run_wall_seconds	phase3_requested	phase3_active	alignments_seen	cigar_lt_ntmin	legacy_nt_lt_ntmin	agree_lt_ntmin	disagree_lt_ntmin	candidate_skippable	candidate_false_negative_rows	task_frontier_equal	task_frontier_safety	real_prune_proof_gate	analyzer_task_row_set_equal	analyzer_task_frontier_safety	analyzer_real_prune_proof_gate	broad_cpu_triplexes	candidate_triplexes	projected_saved_seconds	convert_wall_seconds	projected_saved_fraction	baseline_triplex_path	candidate_triplex_path	candidate_triplex_digest	output_path	output_rows	decision'
}

write_missing_row() {
  local workload="$1"
  local target="$2"
  local fields=(
    "$workload" "$target" 0 0 0 0 0 0 0 0 0 0 0 0 missing fail
    0 missing fail 0 0 0 0 0 NA NA NA NA 0 missing_target
  )
  local i
  for ((i = 0; i < ${#fields[@]}; ++i)); do
    if ((i > 0)); then
      printf '\t'
    fi
    printf '%s' "${fields[$i]}"
  done
  printf '\n'
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

write_header >"$WORK/report.tsv"

for workload in $WORKLOADS; do
  target="$(target_for_workload "$workload")"
  run_dir="$WORK/$workload"
  mkdir -p "$run_dir"
  if [[ ! -s "$target" ]]; then
    write_missing_row "$workload" "$target" >>"$WORK/report.tsv"
    continue
  fi

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
    FASIM_GASAL2_PHASE3_CIGAR_NT_PREFILTER_SHADOW=1 \
    "$BIN" -f1 "$target" -f2 "$RNA" -r "$RULE" -O "$run_dir" \
    >"$run_dir/stdout.log" 2>"$run_dir/stderr.log"
  end="$(now_seconds)"
  run_wall="$(elapsed_seconds "$start" "$end")"

  phase3_prefix="benchmark.fasim_gasal2_phase3_cigar_nt_prefilter_"
  requested="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}requested" 0)"
  active="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}active" 0)"
  alignments_seen="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}alignments_seen" 0)"
  cigar_lt="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}cigar_lt_ntmin" 0)"
  legacy_lt="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}legacy_nt_lt_ntmin" 0)"
  agree="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}agree_lt_ntmin" 0)"
  disagree="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}disagree_lt_ntmin" 0)"
  candidate_skippable="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}candidate_skippable" 0)"
  false_negative_rows="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}candidate_false_negative_rows" 0)"
  frontier_equal="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}task_frontier_equal" 0)"
  frontier_safety="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}task_frontier_safety" unsafe)"
  proof_gate="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}real_prune_proof_gate" fail)"
  projected_saved="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}convert_seconds_projected_saved" 0)"
  baseline_path="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}baseline_triplex_path" NA)"
  candidate_path="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}candidate_triplex_path" NA)"
  candidate_digest="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}candidate_triplex_digest" NA)"
  broad_triplexes="$(metric_value "$run_dir/stderr.log" benchmark.fasim_gasal2_broad_path_cpu_triplexes 0)"
  candidate_triplexes="$(metric_value "$run_dir/stderr.log" "${phase3_prefix}candidate_triplexes" 0)"
  convert_wall="$(metric_value "$run_dir/stderr.log" benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds 0)"
  projected_fraction="$(ratio_seconds "$projected_saved" "$convert_wall")"

  output_path="$(find "$run_dir" -maxdepth 1 -type f -name '*-TFOsorted.lite' | sort | head -n 1)"
  output_rows=0
  if [[ -n "$output_path" && -s "$output_path" ]]; then
    output_rows="$(wc -l <"$output_path")"
  else
    output_path="NA"
  fi

  analyzer_task_equal=0
  analyzer_safety="missing"
  analyzer_gate="fail"
  if [[ -s "$baseline_path" && -s "$candidate_path" ]]; then
    python3 "$ANALYZER" \
      --baseline "$baseline_path" \
      --candidate "$candidate_path" \
      >"$run_dir/task_frontier_proof.txt"
    analyzer_task_equal="$(metric_value "$run_dir/task_frontier_proof.txt" task_row_set_equal 0)"
    analyzer_safety="$(metric_value "$run_dir/task_frontier_proof.txt" task_frontier_safety unsafe)"
    analyzer_gate="$(metric_value "$run_dir/task_frontier_proof.txt" real_prune_proof_gate fail)"
  fi

  decision="phase3_cigar_nt_prefilter_shadow_no_go"
  if [[ "$requested" == "1" &&
        "$active" == "1" &&
        "$alignments_seen" != "0" &&
        "$cigar_lt" == "$legacy_lt" &&
        "$candidate_skippable" == "$cigar_lt" &&
        "$disagree" == "0" &&
        "$false_negative_rows" == "0" &&
        "$frontier_equal" == "1" &&
        "$frontier_safety" == "safe" &&
        "$proof_gate" == "pass" &&
        "$analyzer_task_equal" == "1" &&
        "$analyzer_safety" == "safe" &&
        "$analyzer_gate" == "pass" ]]; then
    decision="phase3_cigar_nt_prefilter_shadow_clean"
  fi

  write_tsv_row \
    "$workload" "$target" 1 "$run_wall" "$requested" "$active" \
    "$alignments_seen" "$cigar_lt" "$legacy_lt" "$agree" "$disagree" \
    "$candidate_skippable" "$false_negative_rows" "$frontier_equal" \
    "$frontier_safety" "$proof_gate" "$analyzer_task_equal" \
    "$analyzer_safety" "$analyzer_gate" "$broad_triplexes" \
    "$candidate_triplexes" "$projected_saved" "$convert_wall" \
    "$projected_fraction" "$baseline_path" "$candidate_path" \
    "$candidate_digest" "$output_path" "$output_rows" "$decision" \
    >>"$WORK/report.tsv"
done

cat "$WORK/report.tsv"
