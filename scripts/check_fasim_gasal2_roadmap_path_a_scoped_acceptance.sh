#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_path_a_scoped_completion_acceptance.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_plan.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"

python3 - "$DOC" "$ROADMAP" "$PHASE_PLAN" "$MATRIX" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])
phase_plan = Path(sys.argv[3])
matrix = Path(sys.argv[4])
for path in [doc, roadmap, phase_plan, matrix]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(
    "\n".join(
        path.read_text(encoding="utf-8")
        for path in [doc, roadmap, phase_plan]
    ).split()
)

required = [
    "path_a_scoped_completion_acceptance_packet = defined",
    "user_scope_acceptance_recorded = 1",
    "accepted_user_message = 接受path A，关闭goal",
    "path_a_user_acceptance_recorded = 1",
    "contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1",
    "runtime = default-off opt-in",
    "primary preset = --gasal2-top5-column-pruned-scoreinfo",
    "tiny-region add-on = --group-target-records 32",
    "topk_summary.tsv",
    "topk_rows.tsv",
    "topk-TFOsorted.lite",
    "report.json",
    "run_manifest.json",
    "reference-backed TFO archive",
    "not broad aligner.Align replacement",
    "not universal scoreInfo/preAlign replacement",
    "not long-query NEAT1/MALAT1 GASAL2 production path",
    "not GPU endpoint authority",
    "not GPU CIGAR authority",
    "not GPU traceback authority",
    "CPU aligner.Align() remains score/endpoint/traceback/CIGAR/output authority.",
    "GASAL2 output authority = 0",
    "make check-fasim-gasal2-roadmap-phase0-reproducibility",
    "make check-fasim-gasal2-roadmap-phase1-scoped-product",
    "make check-fasim-gasal2-roadmap-phase5-archive-artifact",
    "make check-fasim-gasal2-roadmap-phase6-workload-matrix",
    "make check-fasim-gasal2-roadmap-phase8-completion-decision",
    "make check-fasim-gasal2-roadmap-current-state",
    "user explicitly accepts scoped completion",
    "scoped_product_status = accepted",
    "final decision says complete_scoped_path_a, not broad replacement",
    "path_a_scoped_completion_status = accepted",
    "scoped_completion_may_close_goal = 1",
    "path_a_scoped_completion_may_close_goal = 1",
    "broad_objective_status = open",
    "active_goal_completion_status = complete_scoped_path_a",
    "completion_guard_cleared = 1",
    "goal_completion_status = complete",
    "must_not_call_update_goal_complete = 0",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required phrase: {phrase}")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed = [row for row in rows if row.get("scope") == "claimed"]
if not claimed:
    raise SystemExit("workload matrix has no claimed scoped rows")
if any(row.get("status") != "pass" for row in claimed):
    raise SystemExit("claimed scoped workload is not pass")
if any(row.get("scope") == "claimed" and row.get("contract") == "broad_replacement" for row in rows):
    raise SystemExit("Path A packet must not require claimed broad_replacement rows")

print("path_a_scoped_completion_acceptance_packet=defined")
print("path_a_scoped_completion_status=accepted")
print("user_scope_acceptance_recorded=1")
print("scoped_completion_may_close_goal=1")
print("path_a_user_acceptance_recorded=1")
print("path_a_scoped_completion_may_close_goal=1")
print("claimed_scoped_rows_pass=1")
print("claimed_broad_replacement_rows=0")
print("broad_objective_status=open")
print("active_goal_completion_status=complete_scoped_path_a")
print("completion_guard_cleared=1")
print("goal_completion_status=complete")
print("must_not_call_update_goal_complete=0")
print("ok")
PY
