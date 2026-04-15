#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p \
  "$WORK/baseline/legacy/output" \
  "$WORK/baseline/candidate/output" \
  "$WORK/rescue/legacy/output" \
  "$WORK/rescue/candidate/output"

cat >"$WORK/baseline/legacy/output/sample-TFOsorted.lite" <<'EOF'
Chr	QueryStart	QueryEnd	StartInGenome	EndInGenome	Strand	Rule	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
chr22	1	20	1000	1020	ParaPlus	1	110	120	+	100	11	90	-12
chr22	21	40	2000	2020	ParaPlus	1	605	620	+	95	16	90	-12
chr22	41	60	3000	3020	ParaPlus	1	705	720	+	90	16	90	-12
chr22	61	80	4000	4020	ParaPlus	1	805	820	+	85	16	90	-12
EOF

cat >"$WORK/baseline/candidate/output/sample-TFOsorted.lite" <<'EOF'
Chr	QueryStart	QueryEnd	StartInGenome	EndInGenome	Strand	Rule	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
EOF

cat >"$WORK/rescue/legacy/output/sample-TFOsorted.lite" <<'EOF'
Chr	QueryStart	QueryEnd	StartInGenome	EndInGenome	Strand	Rule	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
chr22	1	20	1000	1020	ParaPlus	1	110	120	+	100	11	90	-12
chr22	21	40	2000	2020	ParaPlus	1	605	620	+	95	16	90	-12
chr22	41	60	3000	3020	ParaPlus	1	705	720	+	90	16	90	-12
chr22	61	80	4000	4020	ParaPlus	1	805	820	+	85	16	90	-12
EOF

cat >"$WORK/rescue/candidate/output/sample-TFOsorted.lite" <<'EOF'
Chr	QueryStart	QueryEnd	StartInGenome	EndInGenome	Strand	Rule	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
EOF

cat >"$WORK/baseline/two_stage_windows.tsv" <<'EOF'
task_index	fragment_index	fragment_start_in_seq	fragment_end_in_seq	reverse_mode	parallel_mode	strand	rule	window_id	sorted_rank	window_start_in_fragment	window_end_in_fragment	window_start_in_seq	window_end_in_seq	best_seed_score	second_best_seed_score	margin	support_count	window_bp	before_gate	after_gate	peak_score_ok	support_ok	margin_ok	strong_score_ok	selective_fallback_selected	reject_reason
10	0	1	5000	0	1	ParaPlus	1	0	0	100	140	100	140	100	90	10	3	41	1	1	1	1	1	1	0	kept
20	1	5001	10000	0	1	ParaPlus	1	0	0	500	540	500	540	100	90	10	3	41	1	1	1	1	1	1	0	kept
20	1	5001	10000	0	1	ParaPlus	1	1	1	600	630	600	630	95	92	3	2	31	1	0	1	1	1	0	0	low_support_or_margin
21	1	5001	10000	0	1	AntiPlus	2	0	0	520	560	520	560	98	90	8	3	41	1	1	1	1	1	1	0	kept
30	2	10001	15000	0	1	ParaPlus	1	0	0	660	690	660	690	100	90	10	3	31	1	1	1	1	1	1	0	kept
30	2	10001	15000	0	1	ParaPlus	1	1	1	590	625	590	625	93	90	3	2	36	1	0	1	1	1	0	0	low_support_or_margin
30	2	10001	15000	0	1	ParaPlus	1	2	2	700	730	700	730	90	88	2	2	31	1	0	1	1	1	0	0	low_support_or_margin
40	3	15001	20000	0	1	ParaPlus	1	0	0	900	930	900	930	100	90	10	3	31	1	1	1	1	1	1	0	kept
40	3	15001	20000	0	1	ParaPlus	1	1	1	800	830	800	830	85	82	3	2	31	1	0	1	1	1	0	0	low_support_or_margin
EOF

cat >"$WORK/rescue/two_stage_windows.tsv" <<'EOF'
task_index	fragment_index	fragment_start_in_seq	fragment_end_in_seq	reverse_mode	parallel_mode	strand	rule	window_id	sorted_rank	window_start_in_fragment	window_end_in_fragment	window_start_in_seq	window_end_in_seq	best_seed_score	second_best_seed_score	margin	support_count	window_bp	before_gate	after_gate	peak_score_ok	support_ok	margin_ok	strong_score_ok	selective_fallback_selected	reject_reason
101	0	1	5000	0	1	ParaPlus	1	0	0	100	140	100	140	100	90	10	3	41	1	1	1	1	1	1	0	kept
202	1	5001	10000	0	1	ParaPlus	1	0	0	500	540	500	540	100	90	10	3	41	1	1	1	1	1	1	0	kept
202	1	5001	10000	0	1	ParaPlus	1	1	1	600	630	600	630	95	92	3	2	31	1	1	1	1	1	1	0	kept
212	1	5001	10000	0	1	AntiPlus	2	0	0	520	560	520	560	98	90	8	3	41	1	1	1	1	1	1	0	kept
303	2	10001	15000	0	1	ParaPlus	1	0	0	660	690	660	690	100	90	10	3	31	1	1	1	1	1	1	0	kept
303	2	10001	15000	0	1	ParaPlus	1	2	2	700	730	700	730	90	88	2	2	31	1	1	1	1	1	1	0	kept
404	3	15001	20000	0	1	ParaPlus	1	0	0	900	930	900	930	100	90	10	3	31	1	1	1	1	1	1	0	kept
EOF

cat >"$WORK/baseline/report.json" <<EOF
{
  "compare_output_mode": "lite",
  "runs": {
    "legacy": {
      "output_dir": "$WORK/baseline/legacy/output"
    },
    "deferred_exact_minimal_v3_scoreband_75_79": {
      "output_dir": "$WORK/baseline/candidate/output",
      "debug_windows_csv": "$WORK/baseline/two_stage_windows.tsv",
      "threshold_skipped_after_gate": 0,
      "windows_after_gate": 4,
      "refine_total_bp": 144
    }
  }
}
EOF

cat >"$WORK/rescue/report.json" <<EOF
{
  "compare_output_mode": "lite",
  "runs": {
    "legacy": {
      "output_dir": "$WORK/rescue/legacy/output"
    },
    "deferred_exact": {
      "output_dir": "$WORK/rescue/candidate/output",
      "debug_windows_csv": "$WORK/rescue/two_stage_windows.tsv",
      "threshold_skipped_after_gate": 0,
      "windows_after_gate": 6,
      "refine_total_bp": 206
    }
  }
}
EOF

cat >"$WORK/baseline_panel_summary.json" <<EOF
{
  "gated_run_label": "deferred_exact_minimal_v3_scoreband_75_79",
  "selected_microanchors": [
    {
      "anchor_label": "anchorTask",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 0,
      "start_bp": 1,
      "length_bp": 25000,
      "report_path": "$WORK/baseline/report.json"
    }
  ]
}
EOF

cat >"$WORK/rescue_panel_summary.json" <<EOF
{
  "gated_run_label": "deferred_exact",
  "selected_microanchors": [
    {
      "anchor_label": "anchorTask",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 0,
      "start_bp": 1,
      "length_bp": 25000,
      "report_path": "$WORK/rescue/report.json"
    }
  ]
}
EOF

OUT="$WORK/out"
python3 "$ROOT/scripts/analyze_two_stage_task_ambiguity.py" \
  --baseline-panel-summary "$WORK/baseline_panel_summary.json" \
  --rescue-panel-summary "$WORK/rescue_panel_summary.json" \
  --baseline-label deferred_exact_minimal_v3_scoreband_75_79 \
  --rescue-label deferred_exact \
  --output-dir "$OUT" >/dev/null

python3 - "$OUT/summary.json" <<'PY'
import json
import math
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert summary["baseline_label"] == "deferred_exact_minimal_v3_scoreband_75_79"
assert summary["rescue_label"] == "deferred_exact"
assert summary["aggregate"]["tile_count"] == 1
assert summary["aggregate"]["eligible_task_count"] == 5
assert summary["aggregate"]["rescue_gain_task_count"] == 2
assert summary["aggregate"]["false_positive_ambiguity_task_count"] == 1

tile = summary["tiles"][0]
assert tile["anchor_label"] == "anchorTask"
assert tile["baseline_refine_total_bp"] == 144
assert tile["baseline_covered_key_count"] == 1
assert len(tile["legacy_strict_hits"]) == 4
assert len(tile["baseline_covered_strict_keys"]) == 1

tasks = {
    (
        item["task_key"]["fragment_index"],
        item["task_key"]["fragment_start_in_seq"],
        item["task_key"]["strand"],
        item["task_key"]["rule"],
    ): item
    for item in tile["tasks"]
}
task_b = tasks[(1, 5001, "ParaPlus", 1)]
assert task_b["baseline_task_index"] == 20
assert task_b["rescue_task_index"] == 202
assert task_b["baseline_inside_rejected_missing_count_overall"] == 1
assert task_b["baseline_inside_rejected_missing_count_top5"] == 1
assert task_b["baseline_inside_rejected_missing_count_top10"] == 1
assert math.isclose(task_b["baseline_inside_rejected_missing_weight"], 95.0)
assert task_b["rescue_gain_strict_key_count"] == 1
assert task_b["rescue_top5_gain_count"] == 1
assert task_b["rescue_top10_gain_count"] == 1
assert math.isclose(task_b["rescue_score_weighted_gain"], 95.0)
assert task_b["rescue_added_window_count"] == 1
assert task_b["rescue_added_bp_total"] == 31
features_b = task_b["deployable_features"]
assert features_b["kept_window_count"] == 1
assert features_b["uncovered_rejected_window_count"] == 1
assert features_b["uncovered_rejected_bp_total"] == 31
assert features_b["max_uncovered_rejected_window_bp"] == 31
assert features_b["best_kept_score"] == 100
assert features_b["best_rejected_score"] == 95
assert features_b["best_score_gap"] == 5
assert features_b["rejected_score_sum"] == 95
assert math.isclose(features_b["rejected_score_mean"], 95.0)
assert features_b["rejected_score_top3_sum"] == 95
assert features_b["rejected_score_x_bp_sum"] == 2945
assert features_b["rejected_score_x_support_sum"] == 190
assert features_b["score_band_counts"] == {"ge85": 1, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0}
assert features_b["score_band_bp_totals"] == {"ge85": 31, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0}
assert features_b["support_bin_counts"] == {"support1": 0, "support2": 1, "support3plus": 0}
assert features_b["reject_reason_counts"] == {"low_support_or_margin": 1}
assert features_b["reject_reason_bp_totals"] == {"low_support_or_margin": 31}
assert features_b["rule_diversity_count"] == 1
assert features_b["strand_diversity_count"] == 1
assert features_b["rule_strand_object_count"] == 1
assert math.isclose(features_b["rule_strand_entropy"], 0.0)
assert features_b["selective_fallback_selected_window_count"] == 0
assert features_b["tile_rank_by_best_rejected_score"] == 1
assert features_b["tile_rank_by_rejected_score_x_bp_sum"] == 2

task_shadow = tasks[(1, 5001, "AntiPlus", 2)]
assert task_shadow["baseline_task_index"] == 21
assert task_shadow["rescue_task_index"] == 212
assert task_shadow["baseline_inside_rejected_missing_count_overall"] == 0
assert task_shadow["rescue_gain_strict_key_count"] == 0
features_shadow = task_shadow["deployable_features"]
assert features_shadow["kept_window_count"] == 1
assert features_shadow["uncovered_rejected_window_count"] == 0
assert features_shadow["uncovered_rejected_bp_total"] == 0
assert features_shadow["max_uncovered_rejected_window_bp"] == 0
assert features_shadow["best_kept_score"] == 98
assert features_shadow["best_rejected_score"] is None
assert features_shadow["best_score_gap"] is None
assert features_shadow["rejected_score_sum"] == 0
assert math.isclose(features_shadow["rejected_score_mean"], 0.0)
assert features_shadow["rejected_score_top3_sum"] == 0
assert features_shadow["rejected_score_x_bp_sum"] == 0
assert features_shadow["rejected_score_x_support_sum"] == 0
assert features_shadow["score_band_counts"] == {"ge85": 0, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0}
assert features_shadow["score_band_bp_totals"] == {"ge85": 0, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0}
assert features_shadow["support_bin_counts"] == {"support1": 0, "support2": 0, "support3plus": 0}
assert features_shadow["reject_reason_counts"] == {}
assert features_shadow["reject_reason_bp_totals"] == {}
assert features_shadow["rule_diversity_count"] == 0
assert features_shadow["strand_diversity_count"] == 0
assert features_shadow["rule_strand_object_count"] == 0
assert math.isclose(features_shadow["rule_strand_entropy"], 0.0)
assert features_shadow["selective_fallback_selected_window_count"] == 0

task_c = tasks[(2, 10001, "ParaPlus", 1)]
assert task_c["baseline_inside_rejected_missing_count_overall"] == 1
assert math.isclose(task_c["baseline_inside_rejected_missing_weight"], 90.0)
assert task_c["rescue_gain_strict_key_count"] == 1
assert math.isclose(task_c["rescue_score_weighted_gain"], 90.0)
assert task_c["baseline_uncovered_rejected_window_count"] == 2
features_c = task_c["deployable_features"]
assert features_c["kept_window_count"] == 1
assert features_c["uncovered_rejected_window_count"] == 2
assert features_c["uncovered_rejected_bp_total"] == 67
assert features_c["max_uncovered_rejected_window_bp"] == 36
assert features_c["best_kept_score"] == 100
assert features_c["best_rejected_score"] == 93
assert features_c["best_score_gap"] == 7
assert features_c["rejected_score_sum"] == 183
assert math.isclose(features_c["rejected_score_mean"], 91.5)
assert features_c["rejected_score_top3_sum"] == 183
assert features_c["rejected_score_x_bp_sum"] == 6138
assert features_c["rejected_score_x_support_sum"] == 366
assert features_c["score_band_counts"] == {"ge85": 2, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0}
assert features_c["score_band_bp_totals"] == {"ge85": 67, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0}
assert features_c["support_bin_counts"] == {"support1": 0, "support2": 2, "support3plus": 0}
assert features_c["reject_reason_counts"] == {"low_support_or_margin": 2}
assert features_c["reject_reason_bp_totals"] == {"low_support_or_margin": 67}
assert features_c["rule_diversity_count"] == 1
assert features_c["strand_diversity_count"] == 1
assert features_c["rule_strand_object_count"] == 1
assert math.isclose(features_c["rule_strand_entropy"], 0.0)
assert features_c["selective_fallback_selected_window_count"] == 0
assert features_c["tile_rank_by_best_rejected_score"] == 2
assert features_c["tile_rank_by_rejected_score_x_bp_sum"] == 1

task_d = tasks[(3, 15001, "ParaPlus", 1)]
assert task_d["baseline_inside_rejected_missing_count_overall"] == 1
assert task_d["rescue_gain_strict_key_count"] == 0
features_d = task_d["deployable_features"]
assert features_d["score_band_counts"] == {"ge85": 1, "80_84": 0, "75_79": 0, "70_74": 0, "lt70": 0}
assert features_d["support_bin_counts"] == {"support1": 0, "support2": 1, "support3plus": 0}
assert features_d["reject_reason_counts"] == {"low_support_or_margin": 1}
assert features_d["reject_reason_bp_totals"] == {"low_support_or_margin": 31}
assert features_d["tile_rank_by_best_rejected_score"] == 3
assert features_d["tile_rank_by_rejected_score_x_bp_sum"] == 3

top_ambiguous = summary["aggregate"]["top_ambiguity_tasks"]
assert top_ambiguous[0]["task_key"]["fragment_index"] == 1
assert top_ambiguous[0]["task_key"]["rule"] == 1
assert summary["aggregate"]["high_ambiguity_zero_gain_tasks"][0]["task_key"]["fragment_index"] == 3
PY

grep -q "Task-Level Ambiguity Analysis" "$OUT/summary.md"
grep -q "anchorTask" "$OUT/summary.md"
