#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_plan.md"
RUNBOOK="$ROOT/docs/fasim_gasal2_goal_completion_runbook.md"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$ROADMAP" "$PHASE_PLAN" "$RUNBOOK" "$MAKEFILE" <<'PY'
from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])
phase_plan = Path(sys.argv[3])
runbook = Path(sys.argv[4])
makefile = Path(sys.argv[5])

for path in [doc, roadmap, phase_plan, runbook, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
roadmap_flat = " ".join(roadmap.read_text(encoding="utf-8").split())
phase_plan_flat = " ".join(phase_plan.read_text(encoding="utf-8").split())
runbook_flat = " ".join(runbook.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke = gate_v5_1_pass_first1",
    "strict_gate_target = check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_requested = 1",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_active = 1",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo = 1",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced = 1",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_scoreinfos > 0",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_attempts > 0",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_descriptor_false_negatives = 0",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_missing_required_attempts = 0",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_candidate_attempts_below_all_column_replay_scale = 1",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_cpu_align_authority = 1",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_endpoint_cigar_traceback_output_authority = 0",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass = 1",
    "next_required_gate = phase7_gate_v5_2_cpu_authority_replay_first1",
    "full_rows_equal = true",
    "digest_match = true",
    "candidate_align_attempts < reference_align_attempts",
    "broad_objective_status = open",
    "phase7_broad_restart_v5_gate_v5_1_pass = 1",
    "phase7_broad_restart_v5_gate_v5_2_pass = 0",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing runtime smoke checkpoint phrase: {phrase}")

for stale in [
    "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke = no_go_needs_cuda_descriptor_emission_kernel",
    "strict_gate_observed_failure = candidate active: expected 1, observed 0",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_active = 0",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass = 0",
    "next_required_artifact = cuda_descriptor_emission_kernel_or_api_design",
]:
    if stale in flat:
        raise SystemExit(f"runtime smoke checkpoint contains stale phrase: {stale}")

for target in [
    "check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke:",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke:",
]:
    if target not in makefile_text:
        raise SystemExit(f"missing Makefile target: {target}")

link = "docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.md"
for name, text in [
    ("roadmap", roadmap_flat),
    ("phase plan", phase_plan_flat),
    ("runbook", runbook_flat),
]:
    if link not in text:
        raise SystemExit(f"{name} does not link runtime smoke checkpoint")

print("phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke=gate_v5_1_pass_first1")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_active=1")
print("phase7_broad_restart_v5_gate_v5_1_pass=1")
print("phase7_broad_restart_v5_next_required_gate=phase7_gate_v5_2_cpu_authority_replay_first1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
