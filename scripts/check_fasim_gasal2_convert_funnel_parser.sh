#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_convert_funnel_parser"}"
PARSER="$ROOT/scripts/parse_fasim_gasal2_convert_funnel.py"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/stderr.log" <<'EOF'
benchmark.fasim_top5_gasal2_phase_gasal2_convert_input_alignments=100
benchmark.fasim_top5_gasal2_phase_gasal2_convert_triplexes_raw=80
benchmark.fasim_top5_gasal2_phase_gasal2_emit_candidates=50
benchmark.fasim_top5_gasal2_phase_gasal2_emit_filtered_score=3
benchmark.fasim_top5_gasal2_phase_gasal2_emit_filtered_identity=5
benchmark.fasim_top5_gasal2_phase_gasal2_emit_filtered_stability=7
benchmark.fasim_top5_gasal2_phase_gasal2_emit_filtered_nt=11
benchmark.fasim_top5_gasal2_phase_gasal2_emit_rows_lite=24
benchmark.fasim_top5_gasal2_phase_gasal2_convert_wall_seconds=2.5
benchmark.fasim_top5_gasal2_phase_gasal2_convert_selected_scan_seconds=1.25
benchmark.fasim_top5_gasal2_phase_gasal2_convert_triplex_seconds=1.0
benchmark.fasim_top5_gasal2_phase_gasal2_convert_sort_seconds=0.2
benchmark.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds=0.05
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
require_line "convert_input_alignments=100"
require_line "convert_triplexes_raw=80"
require_line "emit_candidates=50"
require_line "emit_rows=24"
require_line "post_convert_filtered_total=26"
require_line "triplexes_per_input_alignment=0.800000"
require_line "rows_per_input_alignment=0.240000"
require_line "post_convert_filtered_per_candidate=0.520000"
require_line "selected_scan_share=0.500000"
require_line "triplex_share=0.400000"
require_line "sort_share=0.080000"
require_line "filter_share=0.020000"

echo "ok"
