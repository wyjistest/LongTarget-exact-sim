#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_env_scaffold.md"
DESIGN="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_design.md"
NO_GO="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go.md"

python3 - "$DOC" "$DESIGN" "$NO_GO" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
design = Path(sys.argv[2])
no_go = Path(sys.argv[3])
for path in [doc, design, no_go]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
design_flat = " ".join(design.read_text(encoding="utf-8").split())
no_go_flat = " ".join(no_go.read_text(encoding="utf-8").split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 Task-Frontier Certificate Env Scaffold",
    "phase7_post_v5_3_task_frontier_certificate_env_scaffold = fail_closed_no_source",
    "phase7_post_v5_3_task_frontier_certificate_env_scaffold_status = superseded_by_first_attempt_no_go",
    "docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go.md",
    "FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE=1",
    "benchmark.fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_",
    "runtime_default = off",
    "phase7_post_v5_3_task_frontier_certificate_requested = 1",
    "phase7_post_v5_3_task_frontier_certificate_active = 0",
    "phase7_post_v5_3_task_frontier_certificate_source_is_pre_scoreinfo = 0",
    "phase7_post_v5_3_task_frontier_certificate_source_is_legacy_byte_cuda = 0",
    "phase7_post_v5_3_task_frontier_certificate_uses_task_frontier_certificate = 0",
    "phase7_post_v5_3_task_frontier_certificate_task_frontier_certificate_rows = 0",
    "phase7_post_v5_3_task_frontier_certificate_gpu_selected_attempts = 0",
    "phase7_post_v5_3_task_frontier_certificate_candidate_align_attempts = 0",
    "phase7_post_v5_3_task_frontier_certificate_fallback_accounting_clean = 0",
    "phase7_post_v5_3_task_frontier_certificate_cpu_align_authority = 1",
    "phase7_post_v5_3_task_frontier_certificate_gpu_endpoint_cigar_traceback_output_authority = 0",
    "phase7_post_v5_3_task_frontier_certificate_gate_first1_pass = 0",
    "make check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-env-scaffold",
    "next_required_gate = stronger_task_frontier_certificate_design_or_path_a_acceptance",
    "phase7_post_v5_3_task_frontier_certificate_may_claim_completion = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
missing = [phrase for phrase in required if phrase not in flat]
if missing:
    raise SystemExit(
        "missing task-frontier env scaffold phrase(s):\n"
        + "\n".join(missing)
    )

for phrase in [
    "phase7_post_v5_3_task_frontier_certificate_design = defined",
    "next_required_gate = post_v5_3_task_frontier_certificate_first1_smoke",
]:
    if phrase not in design_flat:
        raise SystemExit(f"missing task-frontier design phrase: {phrase}")

for phrase in [
    "phase7_post_v5_3_task_frontier_certificate_first_attempt_status = no_go",
    "phase7_post_v5_3_task_frontier_certificate_first1_gate_pass = 0",
]:
    if phrase not in no_go_flat:
        raise SystemExit(f"missing first-attempt no-go phrase: {phrase}")

for forbidden in [
    "phase7_post_v5_3_task_frontier_certificate_active = 1",
    "phase7_post_v5_3_task_frontier_certificate_gate_first1_pass = 1",
    "GPU endpoint/CIGAR/traceback/output authority = 1",
    "broad_objective_status = complete",
]:
    if forbidden in flat:
        raise SystemExit(f"task-frontier env scaffold contains forbidden phrase: {forbidden}")

print("phase7_post_v5_3_task_frontier_certificate_env_scaffold=superseded_by_first_attempt_no_go")
print("phase7_post_v5_3_task_frontier_certificate_gate_first1_pass=0")
print("next_required_gate=stronger_task_frontier_certificate_design_or_path_a_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
