#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_stability_upper_bound_parser"}"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/query.fa" <<'EOF'
>query
TTTTT
EOF

cat >"$WORK/target.fa" <<'EOF'
>target
NNNNNNNNNNAAAAANNNNNTTTTT
EOF

cat >"$WORK/baseline.lite" <<'EOF'
Chr	StartInGenome	EndInGenome	Strand	Rule	QueryStart	QueryEnd	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
	10	15	ParaPlus	2	1	5	10	15	R	90	5	100.0	3.50
	20	25	ParaPlus	2	1	5	20	25	R	80	5	100.0	1.00
EOF

cat >"$WORK/attempts.tsv" <<'EOF'
batch_id	position	attempt_index	decision	prealign_score	scoreinfo_index	start	cutlength	target_size	nt_min_length	target_end_required_for_fallback	target_offset	target_length	target_global_start	target_global_end
0	0	0	skip	90	0	10	5	5	5	4	10	5	10	15
0	1	1	keep	80	1	20	5	5	5	4	20	5	20	25
EOF

python3 "$ROOT/scripts/analyze_fasim_gasal2_stability_upper_bound.py" \
  --baseline-lite "$WORK/baseline.lite" \
  --attempt-export "$WORK/attempts.tsv" \
  --query-fasta "$WORK/query.fa" \
  --target-fasta "$WORK/target.fa" \
  --top-k 2 \
  --near-bp 0 \
  --nt-min 5 \
  >"$WORK/summary.tsv"

grep -q $'^frontier_stability\t1.000000$' "$WORK/summary.tsv"
grep -q $'^rank\trow_start\trow_end\trow_score\trow_nt\trow_stability\tfrontier_stability\tmatched_attempts\tkept_attempts\tskipped_attempts\trisky_skipped_attempts\tbest_upper_bound\tbest_skipped_upper_bound\tbest_risky_skipped_prealign_score\tattempts$' "$WORK/summary.tsv"
grep -q $'^1\t10\t15\t90\t5\t3.50\t1.000000\t1\t0\t1\t1\t3.700000\t3.700000\t90\t' "$WORK/summary.tsv"
grep -q $'^2\t20\t25\t80\t5\t1.00\t1.000000\t1\t1\t0\t0\t0.000000\t0.000000\t0\t' "$WORK/summary.tsv"
grep -q 'global=10-15' "$WORK/summary.tsv"

cat "$WORK/summary.tsv"
echo "ok"
