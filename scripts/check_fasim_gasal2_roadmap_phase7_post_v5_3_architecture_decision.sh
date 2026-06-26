#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_architecture_decision.md"
V5_DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"

python3 - "$DOC" "$V5_DOC" "$MATRIX" <<'PY'
from __future__ import annotations

import csv
from pathlib import Path
import sys

doc = Path(sys.argv[1])
v5_doc = Path(sys.argv[2])
matrix = Path(sys.argv[3])
for path in [doc, v5_doc, matrix]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
v5_flat = " ".join(v5_doc.read_text(encoding="utf-8").split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 Architecture Decision",
    "phase7_post_v5_3_architecture_decision = defined",
    "phase7_post_v5_3_current_v5_status = stopped_no_go",
    "phase7_post_v5_3_next_gate = different_gpu_execution_design_or_path_a_scope_decision",
    "path_a_user_acceptance_required = 1",
    "path_b_new_broad_architecture_required = 1",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate = correctness_clean_performance_no_go",
    "candidate_vs_baseline = 0.706009",
    "missing_required_attempts = 624",
    "fallback_accounting_clean = 0",
    "Phase 7 v5 CPU-authority descriptor replay",
    "path_a_choice = accept_scoped_completion",
    "path_b_new_broad_architecture_required = 1",
    "required_design_difference:",
    "reduce or replace scoreInfo/preAlign work",
    "reduce or replace Align-side work",
    "full row-set/digest equality, not top5-only equality",
    "next_path_b_pr = fasim: design post-v5.3 GASAL2 broad architecture",
    "docs/fasim_gasal2_phase7_post_v5_3_new_architecture_design.md",
    "do_not_repeat_v5_first64 = 1",
    "do_not_add_broad_replacement_row_from_v5_3 = 1",
    "do_not_use_gpu_endpoint_authority = 1",
    "do_not_use_gpu_cigar_traceback_authority = 1",
    "do_not_use_gpu_output_digest_authority = 1",
    "do_not_close_goal_without_phase8 = 1",
    "current_decision = pending_path_a_acceptance_or_new_path_b_design",
    "next_required_gate = post_v5_3_new_architecture_design_or_path_a_acceptance",
]
missing = [phrase for phrase in required if phrase not in flat]
if missing:
    raise SystemExit("missing post-v5.3 decision phrase(s):\n" + "\n".join(missing))

for phrase in [
    "phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate = correctness_clean_performance_no_go",
    "candidate_vs_baseline = 0.706009",
    "missing_required_attempts = 624",
    "fallback_accounting_clean = 0",
]:
    if phrase not in v5_flat:
        raise SystemExit(f"missing v5 no-go evidence phrase: {phrase}")

with matrix.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
claimed_broad = [
    row for row in rows
    if row.get("scope") == "claimed" and row.get("contract") == "broad_replacement"
]
if claimed_broad:
    raise SystemExit("post-v5.3 decision must not add broad_replacement rows")

print("phase7_post_v5_3_architecture_decision=defined")
print("phase7_post_v5_3_current_v5_status=stopped_no_go")
print("phase7_post_v5_3_next_gate=different_gpu_execution_design_or_path_a_scope_decision")
print("path_a_user_acceptance_required=1")
print("path_b_new_broad_architecture_required=1")
print("claimed_broad_replacement_rows=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
