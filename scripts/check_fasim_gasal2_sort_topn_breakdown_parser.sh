#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_sort_topn_breakdown_parser"}"
PARSER="$ROOT/scripts/parse_fasim_gasal2_sort_topn_breakdown.py"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/stderr.log" <<'EOF'
benchmark.fasim_top5_gasal2_phase_gasal2_convert_input_alignments=1000
benchmark.fasim_top5_gasal2_phase_gasal2_convert_triplexes_raw=800
benchmark.fasim_top5_gasal2_phase_gasal2_emit_candidates=200
benchmark.fasim_top5_gasal2_phase_gasal2_emit_rows_lite=50
benchmark.fasim_top5_gasal2_phase_gasal2_emit_rows_full=0
benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds=10
benchmark.fasim_top5_gasal2_phase_gasal2_convert_selected_scan_seconds=8
benchmark.fasim_top5_gasal2_phase_gasal2_convert_span_check_seconds=0.5
benchmark.fasim_top5_gasal2_phase_gasal2_convert_triplex_seconds=6
benchmark.fasim_top5_gasal2_phase_gasal2_convert_alignment_seconds=6
benchmark.fasim_top5_gasal2_phase_gasal2_convert_sort_seconds=1
benchmark.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds=0.5
benchmark.fasim_top5_gasal2_phase_gasal2_convert_rank_map_seconds=0.75
EOF

python3 "$PARSER" \
  --stderr "$WORK/stderr.log" \
  --label synthetic \
  >"$WORK/summary.txt"

require_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/summary.txt"; then
    echo "missing expected line: $expected" >&2
    cat "$WORK/summary.txt" >&2
    exit 1
  fi
}

require_line "label=synthetic"
require_line "convert_triplexes_raw=800"
require_line "emit_candidates=200"
require_line "emit_rows=50"
require_line "sort_seconds=1.000000"
require_line "filter_seconds=0.500000"
require_line "selected_scan_seconds=8.000000"
require_line "span_check_seconds=0.500000"
require_line "triplex_seconds=6.000000"
require_line "alignment_seconds=6.000000"
require_line "rank_map_seconds=0.750000"
require_line "selected_scan_minus_children_seconds=0.750000"
require_line "selected_scan_share=0.800000"
require_line "span_check_share=0.050000"
require_line "triplex_share=0.600000"
require_line "alignment_share=0.600000"
require_line "selected_scan_minus_children_share=0.075000"
require_line "sort_filter_seconds=1.500000"
require_line "sort_share=0.100000"
require_line "filter_share=0.050000"
require_line "rank_map_share=0.075000"
require_line "sort_filter_share=0.150000"
require_line "convert_accounted_seconds=9.500000"
require_line "convert_unattributed_seconds=0.500000"
require_line "convert_unattributed_share=0.050000"
require_line "triplex_to_sort_filter_ratio=4.000000"
require_line "dominant_convert_stage=triplex_materialization"
require_line "sort_topn_first_priority=0"
require_line "cpu_breakdown_decision=triplex_materialization_or_preconvert_frontier_first"
require_line "rows_per_raw_triplex=0.062500"
require_line "candidates_per_raw_triplex=0.250000"
require_line "raw_triplexes_per_output_row=16.000000"

echo "ok"
