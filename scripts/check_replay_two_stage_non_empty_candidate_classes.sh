#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/legacy/output" "$WORK/candidate/output"

cat >"$WORK/legacy/output/sample-TFOsorted.lite" <<'EOF'
Chr	QueryStart	QueryEnd	StartInGenome	EndInGenome	Strand	Rule	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
chr22	1	20	1000	1020	ParaPlus	1	110	120	+	100	11	90	-12
chr22	21	40	2000	2020	ParaPlus	1	605	620	+	95	16	90	-12
chr22	41	60	3000	3020	ParaPlus	1	705	720	+	90	16	90	-12
EOF

cat >"$WORK/candidate/output/sample-TFOsorted.lite" <<'EOF'
Chr	QueryStart	QueryEnd	StartInGenome	EndInGenome	Strand	Rule	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
EOF

cat >"$WORK/two_stage_windows.tsv" <<'EOF'
task_index	fragment_index	fragment_start_in_seq	fragment_end_in_seq	reverse_mode	parallel_mode	strand	rule	window_id	sorted_rank	window_start_in_fragment	window_end_in_fragment	window_start_in_seq	window_end_in_seq	best_seed_score	second_best_seed_score	margin	support_count	window_bp	before_gate	after_gate	peak_score_ok	support_ok	margin_ok	strong_score_ok	selective_fallback_selected	reject_reason
0	0	1	5000	0	1	ParaPlus	1	0	0	100	140	100	140	100	90	10	3	41	1	1	1	1	1	1	0	kept
1	0	1	5000	0	1	ParaPlus	1	0	0	200	240	200	240	100	90	10	3	41	1	1	1	1	1	1	0	kept
1	0	1	5000	0	1	ParaPlus	1	1		600	630	600	630	95	90	2	1	31	1	0	1	0	0	0	0	low_support_or_margin
2	0	1	5000	0	1	ParaPlus	1	0	0	300	340	300	340	100	90	10	3	41	1	1	1	1	1	1	0	kept
2	0	1	5000	0	1	ParaPlus	1	1		700	730	700	730	90	88	1	2	31	1	0	1	1	0	0	0	low_support_or_margin
EOF

cat >"$WORK/report.json" <<EOF
{
  "compare_output_mode": "lite",
  "runs": {
    "legacy": {
      "output_dir": "$WORK/legacy/output"
    },
    "deferred_exact_minimal_v2_selective_fallback": {
      "output_dir": "$WORK/candidate/output",
      "debug_windows_csv": "$WORK/two_stage_windows.tsv",
      "threshold_invoked": 3,
      "threshold_skipped_after_gate": 0,
      "windows_after_gate": 3,
      "refine_total_bp": 123
    }
  }
}
EOF

cat >"$WORK/panel_summary.json" <<EOF
{
  "gated_run_label": "deferred_exact_minimal_v2_selective_fallback",
  "selected_microanchors": [
    {
      "anchor_label": "anchorB",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "medium_shrink",
      "selection_rank": 0,
      "start_bp": 1,
      "length_bp": 25000,
      "report_path": "$WORK/report.json"
    }
  ]
}
EOF

OUT="$WORK/out"
python3 "$ROOT/scripts/replay_two_stage_non_empty_candidate_classes.py" \
  --panel-summary "$WORK/panel_summary.json" \
  --candidate-label deferred_exact_minimal_v2_selective_fallback \
  --max-kept-windows 2 \
  --non-empty-score-gap 6 \
  --singleton-override 85 \
  --strategy support1_margin_present \
  --strategy support2 \
  --strategy strongest_low_support_or_margin \
  --output-dir "$OUT" >/dev/null

python3 - "$OUT/summary.json" <<'PY'
import json
import math
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
strategies = {item["strategy"]: item for item in summary["strategies"]}
assert set(strategies) == {
    "support1_margin_present",
    "support2",
    "strongest_low_support_or_margin",
}

support1 = strategies["support1_margin_present"]["aggregate"]
assert support1["predicted_rescued_task_count"] == 1
assert support1["predicted_rescued_window_count"] == 1
assert math.isclose(support1["predicted_top_hit_retention"], 1.0)
assert math.isclose(support1["predicted_top5_retention"], 2.0 / 3.0)
assert math.isclose(support1["predicted_top10_retention"], 2.0 / 3.0)
assert math.isclose(support1["predicted_score_weighted_recall"], 195.0 / 285.0)

support2 = strategies["support2"]["aggregate"]
assert support2["predicted_rescued_task_count"] == 1
assert support2["predicted_rescued_window_count"] == 1
assert math.isclose(support2["predicted_top_hit_retention"], 1.0)
assert math.isclose(support2["predicted_top5_retention"], 2.0 / 3.0)
assert math.isclose(support2["predicted_score_weighted_recall"], 190.0 / 285.0)

strongest = strategies["strongest_low_support_or_margin"]["aggregate"]
assert strongest["predicted_rescued_task_count"] == 2
assert strongest["predicted_rescued_window_count"] == 2
assert math.isclose(strongest["predicted_top_hit_retention"], 1.0)
assert math.isclose(strongest["predicted_top5_retention"], 1.0)
assert math.isclose(strongest["predicted_top10_retention"], 1.0)
assert math.isclose(strongest["predicted_score_weighted_recall"], 1.0)
PY

grep -q "Non-Empty Candidate-Class Replay" "$OUT/summary.md"
grep -q "strongest_low_support_or_margin" "$OUT/summary.md"

mkdir -p "$WORK/band_legacy/output" "$WORK/band_candidate/output"

cat >"$WORK/band_legacy/output/sample-TFOsorted.lite" <<'EOF'
Chr	QueryStart	QueryEnd	StartInGenome	EndInGenome	Strand	Rule	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
chr22	1	20	1000	1020	ParaPlus	1	110	120	+	100	11	90	-12
chr22	21	40	2000	2020	ParaPlus	1	605	620	+	95	16	90	-12
chr22	41	60	3000	3020	ParaPlus	1	705	720	+	90	16	90	-12
chr22	61	80	4000	4020	ParaPlus	1	805	820	+	85	16	90	-12
EOF

cat >"$WORK/band_candidate/output/sample-TFOsorted.lite" <<'EOF'
Chr	QueryStart	QueryEnd	StartInGenome	EndInGenome	Strand	Rule	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
EOF

cat >"$WORK/band_two_stage_windows.tsv" <<'EOF'
task_index	fragment_index	fragment_start_in_seq	fragment_end_in_seq	reverse_mode	parallel_mode	strand	rule	window_id	sorted_rank	window_start_in_fragment	window_end_in_fragment	window_start_in_seq	window_end_in_seq	best_seed_score	second_best_seed_score	margin	support_count	window_bp	before_gate	after_gate	peak_score_ok	support_ok	margin_ok	strong_score_ok	selective_fallback_selected	reject_reason
0	0	1	5000	0	1	ParaPlus	1	0	0	100	140	100	140	100	90	10	3	41	1	1	1	1	1	1	0	kept
1	0	1	5000	0	1	ParaPlus	1	0	0	200	240	200	240	100	90	10	3	41	1	1	1	1	1	1	0	kept
1	0	1	5000	0	1	ParaPlus	1	1		600	630	600	630	77	75	2	1	31	1	0	0	0	0	0	0	low_support_or_margin
2	0	1	5000	0	1	ParaPlus	1	0	0	300	340	300	340	100	90	10	3	41	1	1	1	1	1	1	0	kept
2	0	1	5000	0	1	ParaPlus	1	1		700	730	700	730	70	68	2	1	31	1	0	0	0	0	0	0	low_support_or_margin
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
      "debug_windows_csv": "$WORK/band_two_stage_windows.tsv",
      "threshold_invoked": 3,
      "threshold_skipped_after_gate": 0,
      "windows_after_gate": 3,
      "refine_total_bp": 123
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
      "selection_kind": "medium_shrink",
      "selection_rank": 0,
      "start_bp": 1,
      "length_bp": 25000,
      "report_path": "$WORK/band_report.json"
    }
  ]
}
EOF

OUT_BAND="$WORK/out_band"
python3 "$ROOT/scripts/replay_two_stage_non_empty_candidate_classes.py" \
  --panel-summary "$WORK/band_panel_summary.json" \
  --candidate-label deferred_exact_minimal_v2_selective_fallback \
  --max-kept-windows 2 \
  --non-empty-score-gap 6 \
  --singleton-override 85 \
  --strategy score_band_dominant \
  --strategy score_band_75_79 \
  --strategy score_band_lt_75 \
  --output-dir "$OUT_BAND" >/dev/null

python3 - "$OUT_BAND/summary.json" <<'PY'
import json
import math
import sys

summary = json.load(open(sys.argv[1], "r", encoding="utf-8"))
strategies = {item["strategy"]: item for item in summary["strategies"]}
assert set(strategies) == {
    "score_band_dominant",
    "score_band_75_79",
    "score_band_lt_75",
}
dominant = strategies["score_band_dominant"]["aggregate"]
assert strategies["score_band_dominant"]["resolved_score_band"] == "75_79"
assert dominant["predicted_rescued_task_count"] == 1
assert dominant["predicted_rescued_window_count"] == 1
assert math.isclose(dominant["predicted_top_hit_retention"], 1.0)
assert math.isclose(dominant["predicted_top5_retention"], 0.5)
assert math.isclose(dominant["predicted_score_weighted_recall"], 195.0 / 370.0)

band_75_79 = strategies["score_band_75_79"]["aggregate"]
assert band_75_79["predicted_rescued_task_count"] == 1
assert band_75_79["predicted_rescued_window_count"] == 1
assert math.isclose(band_75_79["predicted_top5_retention"], 0.5)
assert math.isclose(band_75_79["predicted_score_weighted_recall"], 195.0 / 370.0)

band_lt_75 = strategies["score_band_lt_75"]["aggregate"]
assert band_lt_75["predicted_rescued_task_count"] == 1
assert band_lt_75["predicted_rescued_window_count"] == 1
assert math.isclose(band_lt_75["predicted_top5_retention"], 0.5)
assert math.isclose(band_lt_75["predicted_score_weighted_recall"], 190.0 / 370.0)
PY

grep -q "score_band_dominant" "$OUT_BAND/summary.md"
grep -q "resolved_score_band" "$OUT_BAND/summary.json"

echo "ok"
