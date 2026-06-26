#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_smoke.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_phase_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_plan.md"
RUNBOOK="$ROOT/docs/fasim_gasal2_goal_completion_runbook.md"
CHECKLIST="$ROOT/docs/fasim_gasal2_goal_completion_phase_checklist.md"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$ROADMAP" "$PHASE_ROADMAP" "$PHASE_PLAN" "$RUNBOOK" "$CHECKLIST" "$MAKEFILE" <<'PY'
from pathlib import Path
import sys

doc = Path(sys.argv[1])
linked = [Path(path) for path in sys.argv[2:6]]
checklist = Path(sys.argv[6])
makefile = Path(sys.argv[7])

for path in [doc, *linked, checklist, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
linked_flat = "\n".join(
    " ".join(path.read_text(encoding="utf-8").split())
    for path in [*linked, checklist]
)
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v5_cpu_authority_replay_smoke = gate_v5_2_pass_first1",
    "strict_gate_target = check-fasim-gasal2-phase7-v5-cpu-authority-replay-runtime-smoke",
    "root_cause_fix = legacy_float_identity_cutlength_descriptor_generation",
    "phase7_v5_cpu_authority_replay_requested = 1",
    "phase7_v5_cpu_authority_replay_active = 1",
    "phase7_v5_cpu_authority_replay_source_is_pre_scoreinfo = 1",
    "phase7_v5_cpu_authority_replay_scoreinfo_prealign_reduced = 1",
    "phase7_v5_cpu_authority_replay_gpu_descriptor_scoreinfos = 718",
    "phase7_v5_cpu_authority_replay_gpu_descriptor_attempts = 2872",
    "phase7_v5_cpu_authority_replay_reference_align_attempts = 2872",
    "phase7_v5_cpu_authority_replay_candidate_align_attempts = 2008",
    "phase7_v5_cpu_authority_replay_descriptor_false_negatives = 0",
    "phase7_v5_cpu_authority_replay_missing_required_attempts = 0",
    "phase7_v5_cpu_authority_replay_cpu_align_authority = 1",
    "phase7_v5_cpu_authority_replay_gpu_endpoint_cigar_traceback_output_authority = 0",
    "phase7_v5_cpu_authority_replay_full_rows_equal = 1",
    "phase7_v5_cpu_authority_replay_digest_match = 1",
    "phase7_v5_cpu_authority_replay_missing_rows = 0",
    "phase7_v5_cpu_authority_replay_extra_rows = 0",
    "phase7_v5_cpu_authority_replay_triplex_mismatches = 0",
    "phase7_v5_cpu_authority_replay_gate_v5_2_pass = 1",
    "candidate_align_attempts < reference_align_attempts",
    "next_required_gate = phase7_gate_v5_3_first64_broad_gate",
    "phase7_broad_restart_v5_gate_v5_1_pass = 1",
    "phase7_broad_restart_v5_gate_v5_2_pass = 1",
    "phase7_broad_restart_v5_gate_v5_3_pass = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing v5.2 checkpoint phrase: {phrase}")

for forbidden in [
    "phase7_broad_restart_v5_cpu_authority_replay_smoke = no_go",
    "phase7_v5_cpu_authority_replay_digest_match = 0",
    "phase7_v5_cpu_authority_replay_full_rows_equal = 0",
    "GPU endpoint/CIGAR/traceback/output authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in flat:
        raise SystemExit(f"v5.2 checkpoint contains forbidden phrase: {forbidden}")

link = "docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_smoke.md"
for path in [*linked, checklist]:
    if link not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"{path} does not link v5.2 checkpoint")

for target in [
    "check-fasim-gasal2-phase7-v5-cpu-authority-replay-runtime-smoke:",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-smoke:",
]:
    if target not in makefile_text:
        raise SystemExit(f"missing Makefile target: {target}")

print("phase7_broad_restart_v5_cpu_authority_replay_smoke=gate_v5_2_pass_first1")
print("phase7_broad_restart_v5_gate_v5_2_pass=1")
print("phase7_broad_restart_v5_next_required_gate=phase7_gate_v5_3_first64_broad_gate")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
