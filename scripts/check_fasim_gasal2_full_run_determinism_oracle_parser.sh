#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_full_run_determinism_oracle_parser"}"

rm -rf "$WORK"
mkdir -p "$WORK"

header='Chr	StartInGenome	EndInGenome	Strand	Rule	QueryStart	QueryEnd	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability'
row_a='chrT	10	20	ParaPlus	3	1	11	10	20	R	100	11	90.0	2.0'
row_b='chrT	30	40	AntiPlus	2	2	12	30	40	R	80	10	85.0	1.5'
row_c='chrT	50	60	ParaMinus	4	3	13	50	60	R	70	9	80.0	1.0'

{
  printf '%s\n' "$header"
  printf '%s\n' "$row_a"
  printf '%s\n' "$row_b"
  printf '%s\n' "$row_c"
} >"$WORK/run1.lite"

{
  printf '%s\n' "$header"
  printf '%s\n' "$row_b"
  printf '%s\n' "$row_a"
  printf '%s\n' "$row_c"
} >"$WORK/run2.lite"

{
  printf '%s\n' "$header"
  printf '%s\n' "$row_a"
  printf '%s\n' "$row_b"
  printf '%s\n' "$row_c"
  printf '%s\n' "$row_c"
} >"$WORK/run3.lite"

python3 "$ROOT/scripts/compare_fasim_full_run_determinism.py" \
  --run "$WORK/run1.lite" \
  --run "$WORK/run2.lite" \
  --run "$WORK/run3.lite" \
  --k 2 \
  --output-summary "$WORK/summary.txt" \
  --output-pairs "$WORK/pairs.tsv"

grep -q '^runs=3$' "$WORK/summary.txt"
grep -q '^schema=lite$' "$WORK/summary.txt"
grep -q '^byte_stable=false$' "$WORK/summary.txt"
grep -q '^set_stable=true$' "$WORK/summary.txt"
grep -q '^multiset_stable=false$' "$WORK/summary.txt"
grep -q '^top2_score_stable=true$' "$WORK/summary.txt"
grep -q '^top2_stability_stable=true$' "$WORK/summary.txt"
grep -q '^top2_nt_score_stable=true$' "$WORK/summary.txt"
grep -q '^max_pair_set_missing=0$' "$WORK/summary.txt"
grep -q '^max_pair_set_extra=0$' "$WORK/summary.txt"
grep -q '^max_pair_multiset_missing=0$' "$WORK/summary.txt"
grep -q '^max_pair_multiset_extra=1$' "$WORK/summary.txt"
grep -q '^classification=order_or_duplicate_count_nondeterminism$' "$WORK/summary.txt"
grep -q '^1	2	false	true	true' "$WORK/pairs.tsv"
grep -q '^1	3	false	true	false' "$WORK/pairs.tsv"

echo "check_fasim_gasal2_full_run_determinism_oracle_parser: ok"
