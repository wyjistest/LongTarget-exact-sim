#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_prune_frontier_safety_parser"}"
PARSER="$ROOT/scripts/analyze_fasim_gasal2_prune_frontier_safety.py"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/baseline.tsv" <<'EOF'
QueryStart	QueryEnd	StartInSeq	EndInSeq	Direction	Chr	StartInGenome	EndInGenome	MeanStability	MeanIdentity(%)	Strand	Rule	Score	Nt(bp)
1	10	100	110	F	chr1	100	110	2.0	70.0	ParaPlus	1	120	11
20	30	200	212	F	chr1	200	212	2.0	70.0	ParaPlus	1	90	13
40	50	400	410	F	chr1	400	410	2.0	70.0	ParaMinus	2	80	11
EOF

cat >"$WORK/candidate.tsv" <<'EOF'
QueryStart	QueryEnd	StartInSeq	EndInSeq	Direction	Chr	StartInGenome	EndInGenome	MeanStability	MeanIdentity(%)	Strand	Rule	Score	Nt(bp)
1	10	100	110	F	chr1	100	110	2.0	70.0	ParaPlus	1	120	11
20	30	220	232	F	chr1	220	232	2.0	70.0	ParaPlus	1	91	13
40	50	400	410	F	chr1	400	410	2.0	70.0	ParaMinus	2	80	11
EOF

python3 "$PARSER" \
  --baseline "$WORK/baseline.tsv" \
  --candidate "$WORK/candidate.tsv" \
  --frontier-key rule \
  >"$WORK/summary.txt"

tail -n +3 "$WORK/baseline.tsv" | head -1 >"$WORK/baseline_only.tsv"
tail -n +3 "$WORK/candidate.tsv" | head -1 >"$WORK/candidate_only.tsv"
python3 "$PARSER" \
  --baseline-only "$WORK/baseline_only.tsv" \
  --candidate-only "$WORK/candidate_only.tsv" \
  --frontier-key rule \
  >"$WORK/diff_only_summary.txt"

require_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/summary.txt"; then
    echo "missing expected line: $expected" >&2
    cat "$WORK/summary.txt" >&2
    exit 1
  fi
}

require_line "baseline_only_rows=1"
require_line "candidate_only_rows=1"
require_line "row_set_equal=0"
require_line "frontier_key=rule"
require_line "frontier_safety=unsafe"
require_line "frontier_changed_buckets=1"
require_line "frontier_shared_changed_buckets=1"
require_line "frontier_baseline_only_buckets=0"
require_line "frontier_candidate_only_buckets=0"
require_line "first_frontier_changed_bucket=1"

require_diff_line() {
  local expected="$1"
  if ! grep -Fxq "$expected" "$WORK/diff_only_summary.txt"; then
    echo "missing expected diff-only line: $expected" >&2
    cat "$WORK/diff_only_summary.txt" >&2
    exit 1
  fi
}

require_diff_line "input_mode=diff_only"
require_diff_line "baseline_only_rows=1"
require_diff_line "candidate_only_rows=1"
require_diff_line "row_set_equal=0"
require_diff_line "frontier_key=rule"
require_diff_line "frontier_safety=unsafe"
require_diff_line "frontier_changed_buckets=1"
require_diff_line "frontier_shared_changed_buckets=1"
require_diff_line "first_frontier_changed_bucket=1"

echo "ok"
