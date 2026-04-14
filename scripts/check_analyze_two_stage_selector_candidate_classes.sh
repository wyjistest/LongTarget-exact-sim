#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/legacy/output" "$WORK/candidate/output"

cat >"$WORK/legacy/output/sample-TFOsorted.lite" <<'EOF'
Chr	QueryStart	QueryEnd	StartInGenome	EndInGenome	Strand	Rule	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
chr22	1	20	1000	1020	ParaPlus	1	605	620	+	92	16	90	-12
chr22	21	40	2000	2020	ParaPlus	1	705	720	+	91	16	90	-12
chr22	41	60	3000	3020	ParaPlus	1	805	820	+	90	16	90	-12
chr22	61	80	4000	4020	ParaPlus	1	905	920	+	80	16	90	-12
EOF

cat >"$WORK/candidate/output/sample-TFOsorted.lite" <<'EOF'
Chr	QueryStart	QueryEnd	StartInGenome	EndInGenome	Strand	Rule	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
EOF

cat >"$WORK/two_stage_windows.tsv" <<'EOF'
task_index	fragment_index	fragment_start_in_seq	fragment_end_in_seq	reverse_mode	parallel_mode	strand	rule	window_id	sorted_rank	window_start_in_fragment	window_end_in_fragment	window_start_in_seq	window_end_in_seq	best_seed_score	second_best_seed_score	margin	support_count	window_bp	before_gate	after_gate	peak_score_ok	support_ok	margin_ok	strong_score_ok	selective_fallback_selected	reject_reason
0	0	1	5000	0	1	ParaPlus	1	0	0	100	150	100	150	100	90	10	3	51	1	1	1	1	1	1	0	kept
0	0	1	5000	0	1	ParaPlus	1	1		600	630	600	630	92	90	2	1	31	1	0	1	0	0	0	0	low_support_or_margin
1	0	1	5000	0	1	ParaPlus	1	0	0	200	240	200	240	100	90	10	3	41	1	1	1	1	1	1	0	kept
1	0	1	5000	0	1	ParaPlus	1	1		700	730	700	730	91	90	1	2	31	1	0	1	1	0	0	0	low_support_or_margin
2	0	1	5000	0	1	ParaPlus	1	0	0	300	340	300	340	100	90	10	3	41	1	1	1	1	1	1	0	kept
2	0	1	5000	0	1	ParaPlus	1	1		800	830	800	830	90	88	2	3	31	1	0	1	1	0	0	0	low_support_or_margin
3	0	1	5000	0	1	ParaPlus	1	0	0	400	440	400	440	100	90	10	3	41	1	1	1	1	1	1	0	kept
3	0	1	5000	0	1	ParaPlus	1	1		900	930	900	930	80	78	2	1	31	1	0	1	0	0	0	0	low_support_or_margin
4	0	1	5000	0	1	ParaPlus	1	0	0	1000	1100	1000	1100	100	90	10	3	101	1	1	1	1	1	1	0	kept
4	0	1	5000	0	1	ParaPlus	1	1		1020	1050	1020	1050	89	87	1	2	31	1	0	1	1	0	0	0	low_support_or_margin
EOF

cat >"$WORK/report.json" <<EOF
{
  "compare_output_mode": "lite",
  "refine_pad_bp": 64,
  "refine_merge_gap_bp": 32,
  "runs": {
    "legacy": {
      "output_dir": "$WORK/legacy/output"
    },
    "deferred_exact_minimal_v2_selective_fallback": {
      "output_dir": "$WORK/candidate/output",
      "debug_windows_csv": "$WORK/two_stage_windows.tsv"
    }
  }
}
EOF

cat >"$WORK/panel_summary.json" <<EOF
{
  "gated_run_label": "deferred_exact_minimal_v2_selective_fallback",
  "selected_microanchors": [
    {
      "anchor_label": "anchorA",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 0,
      "start_bp": 1,
      "length_bp": 25000,
      "report_path": "$WORK/report.json"
    }
  ]
}
EOF

OUT="$WORK/out"
python3 "$ROOT/scripts/analyze_two_stage_selector_candidate_classes.py" \
  --panel-summary "$WORK/panel_summary.json" \
  --candidate-label deferred_exact_minimal_v2_selective_fallback \
  --max-kept-windows 2 \
  --non-empty-score-gap 6 \
  --singleton-override 85 \
  --output-dir "$OUT" >/dev/null

python3 - "$OUT/summary.json" <<'PY'
import json
import math
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
agg = summary["aggregate"]
assert agg["task_count_by_class"] == {
    "support1_margin_present": 1,
    "support2": 1,
    "support3plus_low_support_or_margin": 1,
    "covered_by_kept": 1,
    "score_lt_85": 1,
    "other": 0,
}
assert agg["window_count_by_class"] == {
    "support1_margin_present": 1,
    "support2": 2,
    "support3plus_low_support_or_margin": 1,
    "covered_by_kept": 0,
    "score_lt_85": 1,
    "other": 0,
}
overall = agg["missing_hit_contribution_by_class"]["overall"]
assert overall["matched_missing_count"] == 4
assert overall["count_by_class"] == {
    "support1_margin_present": 1,
    "support2": 1,
    "support3plus_low_support_or_margin": 1,
    "covered_by_kept": 0,
    "score_lt_85": 1,
    "other": 0,
}
weighted = agg["missing_hit_contribution_by_class"]["score_weighted_missing"]
assert math.isclose(weighted["weight_by_class"]["support1_margin_present"], 92.0)
assert math.isclose(weighted["weight_by_class"]["support2"], 91.0)
assert math.isclose(weighted["weight_by_class"]["support3plus_low_support_or_margin"], 90.0)
assert math.isclose(weighted["weight_by_class"]["score_lt_85"], 80.0)
assert summary["recommended_next_candidate_class"] == "support1_margin_present"
assert len(summary["per_tile"]) == 1
assert summary["per_tile"][0]["task_count_by_class"]["covered_by_kept"] == 1
PY

grep -q "Selector Candidate Classes" "$OUT/summary.md"
grep -q "recommended_next_candidate_class" "$OUT/summary.md"

mkdir -p "$WORK/band_legacy/output" "$WORK/band_candidate/output"

cat >"$WORK/band_legacy/output/sample-TFOsorted.lite" <<'EOF'
Chr	QueryStart	QueryEnd	StartInGenome	EndInGenome	Strand	Rule	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
chr22	1	20	5000	5020	ParaPlus	1	1205	1215	+	84	11	90	-12
chr22	21	40	6000	6020	ParaPlus	1	2205	2215	+	91	11	90	-12
chr22	41	60	7000	7020	ParaPlus	1	3205	3215	+	70	11	90	-12
EOF

cat >"$WORK/band_candidate/output/sample-TFOsorted.lite" <<'EOF'
Chr	QueryStart	QueryEnd	StartInGenome	EndInGenome	Strand	Rule	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
EOF

cat >"$WORK/band_two_stage_windows.tsv" <<'EOF'
task_index	fragment_index	fragment_start_in_seq	fragment_end_in_seq	reverse_mode	parallel_mode	strand	rule	window_id	sorted_rank	window_start_in_fragment	window_end_in_fragment	window_start_in_seq	window_end_in_seq	best_seed_score	second_best_seed_score	margin	support_count	window_bp	before_gate	after_gate	peak_score_ok	support_ok	margin_ok	strong_score_ok	selective_fallback_selected	reject_reason
0	0	1	5000	0	1	ParaPlus	1	0	0	1100	1160	1100	1160	100	90	10	3	61	1	1	1	1	1	1	0	kept
0	0	1	5000	0	1	ParaPlus	1	1		1200	1230	1200	1230	84	82	2	1	31	1	0	1	0	0	0	0	low_support_or_margin
1	0	1	5000	0	1	ParaPlus	1	0	0	2100	2160	2100	2160	100	90	10	3	61	1	1	1	1	1	1	0	kept
1	0	1	5000	0	1	ParaPlus	1	1		2200	2230	2200	2230	78	76	2	1	31	1	0	0	0	0	0	0	low_support_or_margin
2	0	1	5000	0	1	ParaPlus	1	0	0	3100	3160	3100	3160	100	90	10	3	61	1	1	1	1	1	1	0	kept
2	0	1	5000	0	1	ParaPlus	1	1		3200	3230	3200	3230	70	68	2	1	31	1	0	0	0	0	0	0	low_support_or_margin
EOF

cat >"$WORK/band_report.json" <<EOF
{
  "compare_output_mode": "lite",
  "runs": {
    "legacy": {
      "output_dir": "$WORK/band_legacy/output"
    },
    "deferred_exact_minimal_v2_selective_fallback": {
      "output_dir": "$WORK/band_candidate/output",
      "debug_windows_csv": "$WORK/band_two_stage_windows.tsv"
    }
  }
}
EOF

cat >"$WORK/band_panel_summary.json" <<EOF
{
  "gated_run_label": "deferred_exact_minimal_v2_selective_fallback",
  "selected_microanchors": [
    {
      "anchor_label": "anchorBand",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 0,
      "start_bp": 1,
      "length_bp": 25000,
      "report_path": "$WORK/band_report.json"
    }
  ]
}
EOF

OUT_BAND="$WORK/out_band"
python3 "$ROOT/scripts/analyze_two_stage_selector_candidate_classes.py" \
  --panel-summary "$WORK/band_panel_summary.json" \
  --candidate-label deferred_exact_minimal_v2_selective_fallback \
  --max-kept-windows 2 \
  --non-empty-score-gap 6 \
  --singleton-override 85 \
  --output-dir "$OUT_BAND" >/dev/null

python3 - "$OUT_BAND/summary.json" <<'PY'
import json
import math
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
bands = summary["aggregate"]["score_lt_85_band_breakdown"]
assert bands["task_count_by_band"] == {
    "80_84": 1,
    "75_79": 1,
    "lt_75": 1,
}
assert bands["window_count_by_band"] == {
    "80_84": 1,
    "75_79": 1,
    "lt_75": 1,
}
overall = bands["missing_hit_contribution_by_band"]["overall"]
assert overall["matched_missing_count"] == 3
assert overall["count_by_band"] == {
    "80_84": 1,
    "75_79": 1,
    "lt_75": 1,
}
weighted = bands["missing_hit_contribution_by_band"]["score_weighted_missing"]
assert math.isclose(weighted["weight_by_band"]["80_84"], 84.0)
assert math.isclose(weighted["weight_by_band"]["75_79"], 91.0)
assert math.isclose(weighted["weight_by_band"]["lt_75"], 70.0)
assert summary["recommended_score_lt_85_band"] == "75_79"
PY

grep -q "score_lt_85 Band Breakdown" "$OUT_BAND/summary.md"
grep -q "recommended_score_lt_85_band" "$OUT_BAND/summary.md"

echo "ok"
