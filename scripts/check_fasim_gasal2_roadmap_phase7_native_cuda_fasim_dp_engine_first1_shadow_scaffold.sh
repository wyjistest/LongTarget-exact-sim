#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md"
CANONICAL_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_canonical_phase_plan.md"
CLOSURE_PLAN="$ROOT/docs/fasim_gasal2_goal_closure_phase_plan.md"
PHASE_DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
PLAYBOOK="$ROOT/docs/fasim_gasal2_goal_completion_playbook.md"
CURRENT_STATE="$ROOT/scripts/summarize_fasim_gasal2_roadmap_current_state.py"
CURRENT_STATE_CHECK="$ROOT/scripts/check_fasim_gasal2_roadmap_current_state.sh"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV" "$ROADMAP" "$PHASE_PLAN" "$CANONICAL_PLAN" "$CLOSURE_PLAN" "$PHASE_DRIVER" "$PLAYBOOK" "$CURRENT_STATE" "$CURRENT_STATE_CHECK" "$MAKEFILE" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

(
    doc,
    prev,
    roadmap,
    phase_plan,
    canonical_plan,
    closure_plan,
    phase_driver,
    playbook,
    current_state,
    current_state_check,
    makefile,
) = [Path(arg) for arg in sys.argv[1:]]

for path in [
    doc,
    prev,
    roadmap,
    phase_plan,
    canonical_plan,
    closure_plan,
    phase_driver,
    playbook,
    current_state,
    current_state_check,
    makefile,
]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
prev_text = prev.read_text(encoding="utf-8")
current_state_text = current_state.read_text(encoding="utf-8")
current_state_check_text = current_state_check.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Phase 7 Native CUDA Fasim DP Engine First1 Shadow Scaffold",
    "phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold = fail_closed_shadow",
    "previous_checkpoint = docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance.md",
    "previous_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold",
    "required_runtime_env = FASIM_GASAL2_PHASE7_NATIVE_CUDA_FASIM_DP_ENGINE_FIRST1_SHADOW",
    "telemetry_prefix = benchmark.fasim_gasal2_phase7_native_cuda_fasim_dp_engine_",
    "requested = 1",
    "active = 1",
    "native_scoreinfo_tiles > 0",
    "forward_endpoint_witnesses = 0",
    "reverse_start_witnesses = 0",
    "traceback_cigar_witnesses = 0",
    "certificates = 0",
    "certificate_false_negatives = 0",
    "missing_required_attempts = native_scoreinfo_tiles",
    "scoreinfo_byte_mismatches = 0",
    "endpoint_mismatches = 0",
    "reverse_start_mismatches = 0",
    "cigar_mismatches = 0",
    "full_row_mismatches = 0",
    "digest_mismatches = 0",
    "full_rows_equal = 0",
    "digest_match = 0",
    "cpu_align_fallbacks = native_scoreinfo_tiles",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "scoreinfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "fallback_accounting_clean = 0",
    "CPU aligner.Align() authority = 1",
    "GPU score authority = 0",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "gpu_score_authority = 0",
    "gpu_endpoint_authority = 0",
    "gpu_cigar_traceback_output_authority = 0",
    "gpu_output_digest_authority = 0",
    "fallback_to_full_cpu_replay = 1",
    "gate_first1_shadow_pass = 0",
    "gate_first1_pass = 0",
    "path_b_native_cuda_fasim_dp_engine_first1_shadow_scaffold = 1",
    "path_b_runtime_reduction_pr_allowed = 0",
    "path_b_runtime_work_drop_allowed = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "next_valid_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go",
    "current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing native CUDA Fasim DP first1 shadow scaffold phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "scoreinfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "fallback_to_full_cpu_replay = 0",
    "gate_first1_shadow_pass = 1",
    "gate_first1_pass = 1",
    "first1_runtime_reduction_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "GPU score authority = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in text:
        raise SystemExit(f"native CUDA Fasim DP scaffold doc contains forbidden phrase: {forbidden}")

if "next_valid_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold" not in prev_text:
    raise SystemExit("previous spec doc no longer points to native CUDA Fasim DP first1 shadow scaffold")

link = "docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold.md"
for label, path in [
    ("roadmap", roadmap),
    ("phase-to-completion plan", phase_plan),
    ("canonical phase plan", canonical_plan),
    ("goal closure phase plan", closure_plan),
    ("phase driver", phase_driver),
    ("playbook", playbook),
]:
    content = path.read_text(encoding="utf-8")
    if link not in content:
        raise SystemExit(f"{label} does not link native CUDA Fasim DP first1 shadow scaffold")
    if "phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go" not in content:
        raise SystemExit(f"{label} does not record the consumer/no-go checkpoint after the scaffold")
    if "runtime_reduction_allowed = 0" not in content:
        raise SystemExit(f"{label} must keep runtime reduction disabled")
    if "runtime_work_drop_allowed = 0" not in content:
        raise SystemExit(f"{label} must keep runtime work drop disabled")
    if "first64_runtime_allowed = 0" not in content:
        raise SystemExit(f"{label} must keep first64 disabled")

for phrase in [
    "phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold",
    "phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold_status",
    "phase7_native_cuda_fasim_dp_engine_runtime_reduction_enabled",
    "phase7_native_cuda_fasim_dp_engine_runtime_work_drop_enabled",
    "phase7_native_cuda_fasim_dp_engine_gate_first1_shadow_pass",
    "phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go",
]:
    if phrase not in current_state_text:
        raise SystemExit(f"current-state summarizer missing phrase: {phrase}")

for phrase in [
    "phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold=fail_closed_shadow",
    "phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold_status=fail_closed_no_runtime_reduction",
    "phase7_native_cuda_fasim_dp_engine_runtime_reduction_enabled=0",
    "phase7_native_cuda_fasim_dp_engine_runtime_work_drop_enabled=0",
    "phase7_native_cuda_fasim_dp_engine_gate_first1_shadow_pass=0",
    "next_valid_gate=phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go",
    "current_execution_gate=phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go",
    "current_next_pr=fasim_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go",
]:
    if phrase not in current_state_check_text:
        raise SystemExit(f"current-state checker missing phrase: {phrase}")

for target in [
    "check-fasim-gasal2-phase7-native-cuda-fasim-dp-engine-first1-shadow-runtime-smoke:",
    "check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-first1-shadow-scaffold:",
]:
    if target not in makefile_text:
        raise SystemExit(f"missing Makefile target: {target}")

current_state_line = next(
    (
        line
        for line in makefile_text.splitlines()
        if line.startswith("check-fasim-gasal2-roadmap-current-state:")
    ),
    "",
)
if "check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-first1-shadow-scaffold" not in current_state_line:
    raise SystemExit("current-state aggregate does not include native CUDA Fasim DP scaffold target")

print("phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold=fail_closed_shadow")
print("phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold_status=fail_closed_no_runtime_reduction")
print("phase7_native_cuda_fasim_dp_engine_runtime_reduction_enabled=0")
print("phase7_native_cuda_fasim_dp_engine_runtime_work_drop_enabled=0")
print("phase7_native_cuda_fasim_dp_engine_gate_first1_shadow_pass=0")
print("next_valid_gate=phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
