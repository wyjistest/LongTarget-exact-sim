#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_roadmap_phase4_sort_topn"}"

rm -rf "$WORK"
mkdir -p "$WORK"

make -C "$ROOT" check-fasim-gasal2-sort-topn-breakdown-parser \
  >"$WORK/sort_topn_parser.log"

require_line() {
  local file="$1"
  local expected="$2"
  if ! grep -Fxq "$expected" "$file"; then
    echo "missing expected line in $file: $expected" >&2
    cat "$file" >&2
    exit 1
  fi
}

require_line "$WORK/sort_topn_parser.log" "ok"

cat >"$WORK/phase4_chr22_breakdown.log" <<'EOF'
benchmark.fasim_top5_gasal2_phase_gasal2_convert_input_alignments=824152
benchmark.fasim_top5_gasal2_phase_gasal2_convert_triplexes_raw=6416486
benchmark.fasim_top5_gasal2_phase_gasal2_emit_candidates=824152
benchmark.fasim_top5_gasal2_phase_gasal2_emit_rows_lite=388821
benchmark.fasim_top5_gasal2_phase_gasal2_emit_rows_full=0
benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds=8.473210
benchmark.fasim_top5_gasal2_phase_gasal2_convert_selected_scan_seconds=7.098580
benchmark.fasim_top5_gasal2_phase_gasal2_convert_span_check_seconds=0.174802
benchmark.fasim_top5_gasal2_phase_gasal2_convert_triplex_seconds=6.564320
benchmark.fasim_top5_gasal2_phase_gasal2_convert_alignment_seconds=6.564320
benchmark.fasim_top5_gasal2_phase_gasal2_convert_sort_seconds=0.950868
benchmark.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds=0.299851
benchmark.fasim_top5_gasal2_phase_gasal2_convert_rank_map_seconds=0.000000
EOF

python3 "$ROOT/scripts/parse_fasim_gasal2_sort_topn_breakdown.py" \
  --stderr "$WORK/phase4_chr22_breakdown.log" \
  --label chr22_equivalence_first \
  >"$WORK/phase4_summary.txt"

require_line "$WORK/phase4_summary.txt" "dominant_convert_stage=triplex_materialization"
require_line "$WORK/phase4_summary.txt" "sort_topn_first_priority=0"
require_line "$WORK/phase4_summary.txt" "cpu_breakdown_decision=triplex_materialization_or_preconvert_frontier_first"

echo "phase4_sort_topn_gate=not_first_priority"
echo "sort_topn_breakdown_parser=pass"
echo "dominant_convert_stage=triplex_materialization"
echo "sort_topn_first_priority=0"
echo "cpu_breakdown_decision=triplex_materialization_or_preconvert_frontier_first"
echo "ok"
