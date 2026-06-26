#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_stability_risk_attempts_parser"}"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/baseline.lite" <<'EOF'
Chr	StartInGenome	EndInGenome	Strand	Rule	QueryStart	QueryEnd	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
	100	160	ParaPlus	2	10	70	100	160	R	99	61	66.0	3.50
	300	360	ParaPlus	2	10	70	300	360	R	130	61	66.0	3.20
EOF

cat >"$WORK/attempts.tsv" <<'EOF'
batch_id	position	attempt_index	decision	prealign_score	scoreinfo_index	start	cutlength	target_size	nt_min_length	target_end_required_for_fallback	target_offset	target_length	target_global_start	target_global_end	output_global_start	output_global_end	task_strand	task_para	task_rule
0	0	0	skip	99	0	90	80	80	50	79	90	80	90	170	90	170	0	1	2
0	1	1	keep	130	1	290	80	80	50	79	290	80	290	370	290	370	0	1	2
EOF

python3 "$ROOT/scripts/analyze_fasim_gasal2_stability_risk_attempts.py" \
  --baseline-lite "$WORK/baseline.lite" \
  --attempt-export "$WORK/attempts.tsv" \
  --top-k 2 \
  >"$WORK/summary.tsv"

grep -q $'^1\t100\t160\t99\t61\t3.50\t1\t0\t1\t99\t0\t99\t' "$WORK/summary.tsv"
grep -q $'^2\t300\t360\t130\t61\t3.20\t1\t1\t0\t130\t130\t0\t' "$WORK/summary.tsv"
grep -q 'global=90-170' "$WORK/summary.tsv"

cat "$WORK/summary.tsv"
echo "ok"
