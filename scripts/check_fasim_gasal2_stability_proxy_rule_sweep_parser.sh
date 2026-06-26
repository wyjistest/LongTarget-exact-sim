#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_stability_proxy_rule_sweep_parser"}"

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
0	2	2	skip	118	2	500	100	100	50	99	500	100	500	600	500	600	0	1	2
0	3	3	skip	115	3	95	50	50	50	49	95	50	95	145	95	145	0	1	2
EOF

cat >"$WORK/proxy.tsv" <<'EOF'
frontier_stability	3.200000
rank	row_start	row_end	row_score	row_nt	row_stability	frontier_stability	matched_attempts	kept_attempts	skipped_attempts	risky_skipped_attempts	best_upper_bound	best_skipped_upper_bound	best_risky_skipped_prealign_score	attempts
1	100	160	99	61	3.50	3.200000	2	0	2	1	3.600000	3.600000	99	d=0,ov=60,decision=skip,score=99,size=80,ub=3.600000,global=90-170,si=0; d=0,ov=45,decision=skip,score=115,size=50,ub=2.900000,global=95-145,si=3
2	300	360	130	61	3.20	3.200000	1	1	0	0	0.000000	0.000000	0	d=0,ov=60,decision=keep,score=130,size=80,ub=3.400000,global=290-370,si=1
EOF

python3 "$ROOT/scripts/analyze_fasim_gasal2_stability_proxy_rule_sweep.py" \
  --baseline-lite "$WORK/baseline.lite" \
  --attempt-export "$WORK/attempts.tsv" \
  --proxy-summary "$WORK/proxy.tsv" \
  --baseline-traceback 10 \
  --top-k 2 \
  --near-bp 0 \
  --score-min 99 \
  --score-min 115 \
  --upper-bound-min 3.2 \
  --upper-bound-min 3.5 \
  --overlap-min 50 \
  >"$WORK/summary.tsv"

grep -q $'^rule\tcovered_topk_rows\ttotal_topk_rows\trisky_skipped_covered\ttotal_risky_skipped\trescued_skipped_attempts\ttotal_skipped_attempts\trescue_fraction_of_all_skipped\testimated_traceback_after_rescue$' "$WORK/summary.tsv"
grep -q $'^score>=99\t1\t2\t1\t1\t3\t3\t1.000000\t13$' "$WORK/summary.tsv"
grep -q $'^score>=115\t0\t2\t0\t1\t2\t3\t0.666667\t12$' "$WORK/summary.tsv"
grep -q $'^ub>=3.200000\t1\t2\t1\t1\t1\t3\t0.333333\t11$' "$WORK/summary.tsv"
grep -q $'^ub>=3.500000\t1\t2\t1\t1\t1\t3\t0.333333\t11$' "$WORK/summary.tsv"
grep -q $'^overlap>=50\t1\t2\t1\t1\t1\t3\t0.333333\t11$' "$WORK/summary.tsv"
grep -q $'^score>=115&ub>=3.200000\t0\t2\t0\t1\t0\t3\t0.000000\t10$' "$WORK/summary.tsv"
grep -q $'^score>=99&ub>=3.200000\t1\t2\t1\t1\t1\t3\t0.333333\t11$' "$WORK/summary.tsv"

cat "$WORK/summary.tsv"
echo "ok"
