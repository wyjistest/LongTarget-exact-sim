#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/.tmp/check_two_stage_coverage_attribution_panel"
rm -rf "$WORK"
mkdir -p "$WORK"

make_case() {
  local case_root="$1"
  local near_distance_bp="$2"
  mkdir -p "$case_root/legacy" "$case_root/candidate"

  cat >"$case_root/legacy/sample-TFOsorted.lite" <<'EOF'
Chr	StartInGenome	EndInGenome	Strand	Rule	QueryStart	QueryEnd	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
chr22	1000	1010	ParaPlus	1	1	10	10	20	R	10.0	11	100	1.0
chr22	1100	1110	ParaPlus	1	11	20	110	120	R	9.5	11	100	1.0
chr22	1200	1210	ParaPlus	1	21	30	210	220	R	9.0	11	100	1.0
chr22	1300	1305	ParaPlus	1	31	36	325	330	R	8.5	6	100	1.0
chr22	1400	1405	ParaPlus	1	41	46	510	515	R	8.0	6	100	1.0
EOF

  cat >"$case_root/candidate/sample-TFOsorted.lite" <<'EOF'
Chr	StartInGenome	EndInGenome	Strand	Rule	QueryStart	QueryEnd	StartInSeq	EndInSeq	Direction	Score	Nt(bp)	MeanIdentity(%)	MeanStability
chr22	1000	1010	ParaPlus	1	1	10	10	20	R	10.0	11	100	1.0
EOF

  cat >"$case_root/debug.tsv" <<'EOF'
task_index	fragment_index	fragment_start_in_seq	fragment_end_in_seq	reverse_mode	parallel_mode	strand	rule	window_id	sorted_rank	window_start_in_fragment	window_end_in_fragment	window_start_in_seq	window_end_in_seq	best_seed_score	second_best_seed_score	margin	support_count	window_bp	before_gate	after_gate	peak_score_ok	support_ok	margin_ok	strong_score_ok	reject_reason
0	0	1	600	0	1	ParaPlus	1	0	0	100	130	100	130	95		1	1	31	1	1	1	0	0	0	none
0	0	1	600	0	1	ParaPlus	1	1	1	200	230	200	230	90		1	1	31	1	0	1	0	0	0	support_margin
0	0	1	600	0	1	ParaPlus	1	2	2	300	320	300	320	85		1	1	21	1	1	1	0	0	0	none
EOF

  cat >"$case_root/report.json" <<EOF
{
  "compare_output_mode": "lite",
  "refine_pad_bp": $near_distance_bp,
  "refine_merge_gap_bp": 4,
  "runs": {
    "legacy": {
      "output_dir": "$case_root/legacy",
      "debug_windows_csv": ""
    },
    "deferred_exact_minimal_v2": {
      "output_dir": "$case_root/candidate",
      "debug_windows_csv": "$case_root/debug.tsv"
    }
  }
}
EOF
}

make_case "$WORK/case_a" 10
make_case "$WORK/case_b" 6

cat >"$WORK/panel_summary.json" <<EOF
{
  "gated_run_label": "deferred_exact_minimal_v2",
  "selected_microanchors": [
    {
      "anchor_label": "anchor_a",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 1,
      "length_bp": 25000,
      "start_bp": 1,
      "end_bp": 25000,
      "shard_path": "$WORK/a_1.fa",
      "report_path": "$WORK/case_a/report.json",
      "runs": {
        "deferred_exact_minimal_v2": {
          "debug_windows_csv": "$WORK/case_a/debug.tsv"
        }
      }
    },
    {
      "anchor_label": "anchor_a",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 2,
      "length_bp": 25000,
      "start_bp": 12501,
      "end_bp": 37500,
      "shard_path": "$WORK/a_2.fa",
      "report_path": "$WORK/case_b/report.json",
      "runs": {
        "deferred_exact_minimal_v2": {
          "debug_windows_csv": "$WORK/case_b/debug.tsv"
        }
      }
    },
    {
      "anchor_label": "anchor_a",
      "selection_bucket_length_bp": 25000,
      "selection_kind": "medium_shrink",
      "selection_rank": 1,
      "length_bp": 25000,
      "start_bp": 50001,
      "end_bp": 75000,
      "shard_path": "$WORK/a_3.fa",
      "report_path": "$WORK/case_b/report.json",
      "runs": {
        "deferred_exact_minimal_v2": {
          "debug_windows_csv": "$WORK/case_b/debug.tsv"
        }
      }
    },
    {
      "anchor_label": "anchor_b",
      "selection_bucket_length_bp": 50000,
      "selection_kind": "strongest_shrink",
      "selection_rank": 1,
      "length_bp": 50000,
      "start_bp": 1,
      "end_bp": 50000,
      "shard_path": "$WORK/b_1.fa",
      "report_path": "$WORK/case_b/report.json",
      "runs": {
        "deferred_exact_minimal_v2": {
          "debug_windows_csv": "$WORK/case_b/debug.tsv"
        }
      }
    }
  ]
}
EOF

python3 "$ROOT/scripts/analyze_two_stage_coverage_attribution_panel.py" \
  --panel-summary "$WORK/panel_summary.json" \
  --output-dir "$WORK/out" >/dev/null

python3 - "$WORK/out/summary.json" <<'PY'
import json
import sys

report = json.load(open(sys.argv[1], "r", encoding="utf-8"))
assert report["candidate_label"] == "deferred_exact_minimal_v2"
assert report["selected_tile_count"] == 3

tiles = report["selected_tiles"]
assert [tile["selection_rank"] for tile in tiles] == [1, 1, 1]
assert [(tile["anchor_label"], tile["selection_kind"]) for tile in tiles] == [
    ("anchor_a", "medium_shrink"),
    ("anchor_a", "strongest_shrink"),
    ("anchor_b", "strongest_shrink"),
]

overall = report["aggregate"]["overall"]["count_by_class"]
assert overall["inside_kept_window"] == 3
assert overall["inside_rejected_window"] == 3
assert overall["outside_kept_but_near_kept"] == 3
assert overall["far_outside_all_kept"] == 3

top5 = report["aggregate"]["top5_missing"]["count_by_class"]
assert top5["inside_kept_window"] == 3
assert top5["inside_rejected_window"] == 3
assert top5["outside_kept_but_near_kept"] == 3
assert top5["far_outside_all_kept"] == 3

by_kind = report["by_selection_kind"]
assert by_kind["strongest_shrink"]["selected_tile_count"] == 2
assert by_kind["medium_shrink"]["selected_tile_count"] == 1

weighted = report["aggregate"]["score_weighted_missing"]["weight_by_class"]
assert weighted["inside_kept_window"] == 28.5
assert weighted["inside_rejected_window"] == 27.0
assert weighted["outside_kept_but_near_kept"] == 25.5
assert weighted["far_outside_all_kept"] == 24.0
PY

grep -q "Two-Stage Coverage Attribution Panel Summary" "$WORK/out/summary.md"
grep -q "inside_rejected_window" "$WORK/out/summary.md"

echo "ok"
