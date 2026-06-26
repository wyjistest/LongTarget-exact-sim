#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_prune_authority_diff_parser"}"
PARSER="$ROOT/scripts/analyze_fasim_gasal2_prune_authority_diff.py"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/no_prune.tsv" <<'EOF'
1	10	100	109	R	chrT	100	109	1.5	70	ParaPlus	6	101	10	0	5	5	AAAAAAAAAA	TTTTTTTTTT
2	8	200	207	R	chrT	200	207	1.2	65	AntiMinus	5	88	8	0	5	5	CCCCCCCC	GGGGGGGG
EOF

cat >"$WORK/prune.tsv" <<'EOF'
1	10	100	109	R	chrT	100	109	1.5	70	ParaPlus	6	101	10	0	5	5	AAAAAAAAAA	TTTTTTTTTT
3	9	204	212	R	chrT	204	212	1.7	72	ParaMinus	4	95	9	0	6	6	ACACACACA	TGTGTGTGT
EOF

python3 "$PARSER" \
  --baseline "$WORK/no_prune.tsv" \
  --candidate "$WORK/prune.tsv" \
  >"$WORK/summary.txt"

require_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/summary.txt"; then
    echo "missing expected line: $expected" >&2
    cat "$WORK/summary.txt" >&2
    exit 1
  fi
}

require_line "baseline_rows=2"
require_line "candidate_rows=2"
require_line "baseline_only_rows=1"
require_line "candidate_only_rows=1"
require_line "baseline_only_min_nt=8"
require_line "baseline_only_min_query_span=7"
require_line "baseline_only_min_ref_span=8"
require_line "baseline_only_min_sum_span=15"
require_line "candidate_only_min_nt=9"
require_line "candidate_only_min_query_span=7"
require_line "candidate_only_min_ref_span=9"
require_line "candidate_only_min_sum_span=16"
require_line "cross_overlap_pairs=1"
require_line "cross_overlap_max_bp=4"
require_line "cross_overlap_same_rule_pairs=0"
require_line "baseline_only_rule_count=1"
require_line "candidate_only_rule_count=1"
require_line "shared_rule_count=0"
require_line "min_cross_distance_bp=0"
require_line "row_set_equal=0"

echo "ok"
