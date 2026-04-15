#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$ROOT/.tmp/check_profile_two_stage_panel_task_rerun_runtime"
rm -rf "$WORK"
INPUT="$WORK/input"
OUTPUT="$WORK/output"
mkdir -p "$INPUT"

cat >"$INPUT/dna.fa" <<'EOF'
>chrSynthetic
ACGTACGTACGTACGT
EOF

cat >"$INPUT/rna.fa" <<'EOF'
>rnaSynthetic
UGCAUGCA
EOF

cat >"$INPUT/selected_tasks.tsv" <<'EOF'
fragment_index	fragment_start_in_seq	fragment_end_in_seq	reverse_mode	parallel_mode	strand	rule
0	1	16	0	1	ParaPlus	2
EOF

python3 - "$INPUT" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
report = {
    "compare_output_mode": "lite",
    "prefilter_topk": 64,
    "peak_suppress_bp": 5,
    "score_floor_deltas": 0,
    "score_floor_delta": 0,
    "refine_pad_bp": 64,
    "refine_merge_gap_bp": 32,
    "inputs": {
        "dna_src": str(root / "dna.fa"),
        "rna_src": str(root / "rna.fa"),
        "rule": 2,
        "strand": "parallel",
    },
    "reject_defaults": {
        "min_peak_score": 80,
        "min_support": 2,
        "min_margin": 6,
        "strong_score_override": 100,
        "max_windows_per_task": 8,
        "max_bp_per_task": 32768,
    },
}
summary = {
    "baseline_run_label": "deferred_exact_minimal_v3_scoreband_75_79",
    "candidate_run_label": "deferred_exact_minimal_v3_task_rerun_budget16",
    "selected_microanchors": [
        {
            "anchor_label": "anchorA",
            "selection_bucket_length_bp": 20000,
            "selection_kind": "top",
            "selection_rank": 0,
            "start_bp": 1000,
            "length_bp": 20000,
            "report_path": str(root / "tile_report.json"),
            "task_rerun_selected_tasks_path": str(root / "selected_tasks.tsv"),
        }
    ],
}
(root / "tile_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
(root / "panel_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
PY

python3 "$ROOT/scripts/profile_two_stage_panel_task_rerun_runtime.py" \
  --panel-summary "$INPUT/panel_summary.json" \
  --output-dir "$OUTPUT" \
  --dry-run >/dev/null

python3 - "$OUTPUT/dry_run.json" "$OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

report = json.load(open(sys.argv[1], "r", encoding="utf-8"))
work = Path(sys.argv[2]).resolve()

assert report["baseline_run_label"] == "deferred_exact_minimal_v3_scoreband_75_79"
assert report["candidate_run_label"] == "deferred_exact_minimal_v3_task_rerun_budget16"
assert report["selected_tile_count"] > 0
assert report["commands"]

expected_selected_root = work / "task_rerun_selected_tasks"
expected_profile_root = work / "task_rerun_profiles"
for command in report["commands"]:
    selected_matches = [
        item
        for item in command
        if "LONGTARGET_TWO_STAGE_TASK_RERUN_SELECTED_TASKS_PATH=" in item
    ]
    profile_matches = [
        item
        for item in command
        if "LONGTARGET_TWO_STAGE_TASK_RERUN_PROFILE_TSV=" in item
    ]
    assert len(selected_matches) == 1
    assert len(profile_matches) == 1
    selected_path = Path(selected_matches[0].split("=", 1)[1]).resolve()
    profile_path = Path(profile_matches[0].split("=", 1)[1]).resolve()
    assert selected_path.exists(), selected_path
    assert profile_path.parent.exists(), profile_path
    assert str(selected_path).startswith(str(expected_selected_root)), selected_path
    assert str(profile_path).startswith(str(expected_profile_root)), profile_path
PY

echo "ok"
