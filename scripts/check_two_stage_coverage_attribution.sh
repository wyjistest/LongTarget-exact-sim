#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/.tmp/check_two_stage_coverage_attribution"
rm -rf "$WORK"
mkdir -p "$WORK/legacy" "$WORK/candidate"

cat >"$WORK/legacy/sample-TFOsorted.lite" <<'EOF'
Chr	StartInGenome	EndInGenome	Strand	Rule	QueryStart	QueryEnd	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
chr22	1000	1010	ParaPlus	1	1	10	10	20	R	10.0	11	100	1.0
chr22	1100	1110	ParaPlus	1	11	20	110	120	R	9.5	11	100	1.0
chr22	1200	1210	ParaPlus	1	21	30	210	220	R	9.0	11	100	1.0
chr22	1300	1305	ParaPlus	1	31	36	325	330	R	8.5	6	100	1.0
chr22	1400	1405	ParaPlus	1	41	46	510	515	R	8.0	6	100	1.0
EOF

cat >"$WORK/candidate/sample-TFOsorted.lite" <<'EOF'
Chr	StartInGenome	EndInGenome	Strand	Rule	QueryStart	QueryEnd	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
chr22	1000	1010	ParaPlus	1	1	10	10	20	R	10.0	11	100	1.0
EOF

cat >"$WORK/debug.tsv" <<'EOF'
task_index	fragment_index	fragment_start_in_seq	fragment_end_in_seq	reverse_mode	parallel_mode	strand	rule	window_id	sorted_rank	window_start_in_fragment	window_end_in_fragment	window_start_in_seq	window_end_in_seq	best_seed_score	second_best_seed_score	margin	support_count	window_bp	before_gate	after_gate	peak_score_ok	support_ok	margin_ok	strong_score_ok	reject_reason
0	0	1	600	0	1	ParaPlus	1	0	0	100	130	100	130	95		1	1	31	1	1	1	0	0	0	none
0	0	1	600	0	1	ParaPlus	1	1	1	200	230	200	230	90		1	1	31	1	0	1	0	0	0	support_margin
0	0	1	600	0	1	ParaPlus	1	2	2	300	320	300	320	85		1	1	21	1	1	1	0	0	0	none
EOF

cat >"$WORK/report.json" <<EOF
{
  "compare_output_mode": "lite",
  "refine_pad_bp": 10,
  "refine_merge_gap_bp": 4,
  "runs": {
    "legacy": {
      "output_dir": "$WORK/legacy",
      "debug_windows_csv": ""
    },
    "deferred_exact_minimal_v2": {
      "output_dir": "$WORK/candidate",
      "debug_windows_csv": "$WORK/debug.tsv"
    }
  }
}
EOF

python3 "$ROOT/scripts/analyze_two_stage_coverage_attribution.py" \
  --report "$WORK/report.json" \
  --candidate-label deferred_exact_minimal_v2 \
  --output "$WORK/coverage.json" >/dev/null

python3 - "$WORK/coverage.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert report["candidate_label"] == "deferred_exact_minimal_v2"
assert report["near_distance_bp"] == 10
assert report["missing_strict_hit_count"] == 4

overall = report["summary"]["overall"]["count_by_class"]
assert overall["inside_kept_window"] == 1
assert overall["inside_rejected_window"] == 1
assert overall["outside_kept_but_near_kept"] == 1
assert overall["far_outside_all_kept"] == 1

top5 = report["summary"]["top5_missing"]["count_by_class"]
assert top5["inside_kept_window"] == 1
assert top5["inside_rejected_window"] == 1
assert top5["outside_kept_but_near_kept"] == 1
assert top5["far_outside_all_kept"] == 1

weighted = report["summary"]["score_weighted_missing"]
assert weighted["weight_by_class"]["inside_kept_window"] == 9.5
assert weighted["weight_by_class"]["inside_rejected_window"] == 9.0
assert weighted["weight_by_class"]["outside_kept_but_near_kept"] == 8.5
assert weighted["weight_by_class"]["far_outside_all_kept"] == 8.0

examples = report["examples_by_class"]
assert examples["inside_kept_window"][0]["hit"]["start_in_seq"] == 110
assert examples["inside_rejected_window"][0]["hit"]["start_in_seq"] == 210
assert examples["outside_kept_but_near_kept"][0]["nearest_kept_distance_bp"] == 5
assert examples["far_outside_all_kept"][0]["nearest_kept_distance_bp"] == 190
PY

echo "ok"
