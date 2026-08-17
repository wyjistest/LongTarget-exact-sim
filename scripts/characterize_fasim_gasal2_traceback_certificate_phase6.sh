#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/phase6_traceback_certificate"}"
OUTPUT="${OUTPUT:-"$WORK/analysis"}"
FULL_QUERY_ROOT="${FULL_QUERY_ROOT:-"$ROOT/.tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_chr22_full_fullquery"}"
H19_ROOT="${H19_ROOT:-"$ROOT/.tmp/check_fasim_gasal2_traceback_certificate_shadow_smoke"}"
KCNQ_FRAGMENT_ROOT="${KCNQ_FRAGMENT_ROOT:-"$WORK/kcnq_fragment_chr22_2mb"}"
CHROMOSOME_ROOT="${CHROMOSOME_ROOT:-"$WORK/h19_chr21_chr22_full"}"
MAX4_ROOT="${MAX4_ROOT:-"$WORK/kcnq_max4_chr22_full"}"
MAX8_ROOT="${MAX8_ROOT:-"$WORK/kcnq_max8_chr22_full"}"

ANALYZER="$ROOT/scripts/analyze_fasim_gasal2_traceback_long_query.py"
SUMMARIZER="$ROOT/scripts/summarize_fasim_gasal2_traceback_certificate.py"

for path in \
  "$ANALYZER" "$SUMMARIZER" "$FULL_QUERY_ROOT" "$H19_ROOT" \
  "$KCNQ_FRAGMENT_ROOT" "$CHROMOSOME_ROOT" "$MAX4_ROOT" "$MAX8_ROOT"; do
  if [[ ! -e "$path" ]]; then
    echo "missing Phase 6 characterization dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$OUTPUT"
mkdir -p "$OUTPUT/rows"

python3 "$ANALYZER" \
  --run-root "$FULL_QUERY_ROOT" \
  --details "$OUTPUT/traceback_timing_details.tsv" \
  --summary "$OUTPUT/traceback_timing_summary.txt" \
  >"$OUTPUT/traceback_timing_stdout.txt"

find_one_output() {
  local root="$1"
  local label="$2"
  local output
  output="$(find "$root/$label" -maxdepth 1 -type f -name '*-TFOsorted.lite' -print -quit)"
  if [[ -z "$output" ]]; then
    echo "missing lite output under $root/$label" >&2
    return 1
  fi
  printf '%s\n' "$output"
}

summarize_root() {
  local workload="$1"
  local root="$2"
  local query="$3"
  local target="$4"
  local scope="$5"
  local contract="$6"
  local row="$OUTPUT/rows/$workload.tsv"
  local -a logs=()
  local -a command=(
    python3 "$SUMMARIZER"
    --workload "$workload"
    --query "$query"
    --target "$target"
    --scope "$scope"
    --output-contract "$contract"
    --artifact-provenance "$root"
    --output "$row"
  )
  if [[ -f "$root/shadow/stderr.log" ]]; then
    logs=("$root/shadow/stderr.log")
  else
    mapfile -t logs < <(find "$root" -path '*/run_*/stderr.log' | sort)
  fi
  if (( ${#logs[@]} == 0 )); then
    echo "no certificate logs under $root" >&2
    return 1
  fi
  for log in "${logs[@]}"; do
    command+=(--stderr "$log")
  done
  "${command[@]}" >"$OUTPUT/rows/$workload.summary.txt"
}

h19_baseline="$(find_one_output "$H19_ROOT" baseline)"
h19_shadow="$(find_one_output "$H19_ROOT" shadow)"
cmp -s "$h19_baseline" "$h19_shadow"

kcnq_baseline="$(find_one_output "$KCNQ_FRAGMENT_ROOT" baseline)"
kcnq_shadow="$(find_one_output "$KCNQ_FRAGMENT_ROOT" shadow)"
cmp -s "$kcnq_baseline" "$kcnq_shadow"

chromosome_baseline="$(find_one_output "$CHROMOSOME_ROOT" baseline)"
chromosome_shadow="$(find_one_output "$CHROMOSOME_ROOT" shadow)"
python3 "$ROOT/scripts/compare_fasim_lite_topk.py" \
  --baseline "$chromosome_baseline" \
  --candidate "$chromosome_shadow" \
  --k 5 >"$OUTPUT/chromosome_top5_compare.txt"
for key in top5_score_equal top5_stability_equal top5_nt_score_equal; do
  grep -q "^${key}=true$" "$OUTPUT/chromosome_top5_compare.txt"
done
python3 "$ROOT/scripts/compare_fasim_lite_offline_cluster_topk.py" \
  --baseline "$chromosome_baseline" \
  --candidate "$chromosome_shadow" \
  --k 5 \
  --details "$OUTPUT/chromosome_offline_cluster.tsv" \
  >"$OUTPUT/chromosome_offline_cluster.txt"
grep -q '^top5_offline_cluster_equal=true$' "$OUTPUT/chromosome_offline_cluster.txt"
grep -q '^top5_offline_cluster_overlap=5$' "$OUTPUT/chromosome_offline_cluster.txt"

for root in "$MAX4_ROOT" "$MAX8_ROOT"; do
  grep -q '^top5_offline_cluster_equal=true$' "$root/summary.txt"
  grep -q '^top5_offline_cluster_overlap=5$' "$root/summary.txt"
  grep -q '^gasal2_fallbacks=0$' "$root/summary.txt"
  grep -q '^length_guard_fallbacks=0$' "$root/summary.txt"
done

summarize_root \
  h19_chr22_2mb "$H19_ROOT" H19.fa \
  .tmp/fasim_gasal2_chr22_slice_10m_12m.fa \
  short_query_smoke byte_equal
summarize_root \
  kcnq1ot1_fragment_chr22_2mb "$KCNQ_FRAGMENT_ROOT" \
  .tmp/characterize_fasim_gasal2_short_query_generalization_panel/inputs/KCNQ1OT1_fragment_mid_2048.fa \
  .tmp/fasim_gasal2_chr22_slice_10m_12m.fa \
  non_h19_short_query byte_equal
summarize_root \
  h19_chr21_chr22_full "$CHROMOSOME_ROOT" H19.fa \
  .tmp/characterize_fasim_gasal2_sharded_gpu_utilization_prune16/inputs/chr21_chr22.fa \
  chromosome_control top5_clean_baseline_row_variability
summarize_root \
  kcnq1ot1_max4_chr22_full "$MAX4_ROOT" \
  .tmp/fasim_gasal2_query_inputs/KCNQ1OT1_ENST00000597346.fa \
  .tmp/gasal2_hg38_archive_first_run/shards/chr22.fa \
  max_segments_4_two_shifted_grids shifted_grid_clustered_top5_equal
summarize_root \
  kcnq1ot1_max8_chr22_full "$MAX8_ROOT" \
  .tmp/fasim_gasal2_query_inputs/KCNQ1OT1_ENST00000597346.fa \
  .tmp/gasal2_hg38_archive_first_run/shards/chr22.fa \
  max_segments_8_two_shifted_grids shifted_grid_clustered_top5_equal

first=1
for row in \
  "$OUTPUT/rows/h19_chr22_2mb.tsv" \
  "$OUTPUT/rows/kcnq1ot1_fragment_chr22_2mb.tsv" \
  "$OUTPUT/rows/h19_chr21_chr22_full.tsv" \
  "$OUTPUT/rows/kcnq1ot1_max4_chr22_full.tsv" \
  "$OUTPUT/rows/kcnq1ot1_max8_chr22_full.tsv"; do
  if (( first )); then
    cat "$row" >"$OUTPUT/traceback_certificate_matrix.tsv"
    first=0
  else
    tail -n +2 "$row" >>"$OUTPUT/traceback_certificate_matrix.tsv"
  fi
done

cat "$OUTPUT/traceback_timing_summary.txt"
cat "$OUTPUT/traceback_certificate_matrix.tsv"
