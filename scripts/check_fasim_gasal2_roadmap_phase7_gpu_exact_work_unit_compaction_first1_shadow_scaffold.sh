#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
ACTION="$ROOT/docs/fasim_gasal2_goal_completion_action_roadmap.md"
CURRENT_STATE="$ROOT/scripts/summarize_fasim_gasal2_roadmap_current_state.py"
CURRENT_STATE_CHECK="$ROOT/scripts/check_fasim_gasal2_roadmap_current_state.sh"
RUNTIME_SMOKE="$ROOT/scripts/check_fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_smoke.sh"
MAKEFILE="$ROOT/Makefile"
BRIDGE_H="$ROOT/fasim/gasal2_align_bridge.h"
BRIDGE_CPP="$ROOT/fasim/gasal2_align_bridge.cpp"
STUB_CPP="$ROOT/fasim/gasal2_align_bridge_stub.cpp"
RUNTIME_CPP="$ROOT/fasim/Fasim-LongTarget.cpp"

python3 - "$DOC" "$PREV" "$ROADMAP" "$ACTION" "$CURRENT_STATE" "$CURRENT_STATE_CHECK" "$RUNTIME_SMOKE" "$MAKEFILE" "$BRIDGE_H" "$BRIDGE_CPP" "$STUB_CPP" "$RUNTIME_CPP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

(
    doc,
    prev,
    roadmap,
    action,
    current_state,
    current_state_check,
    runtime_smoke,
    makefile,
    bridge_h,
    bridge_cpp,
    stub_cpp,
    runtime_cpp,
) = [Path(arg) for arg in sys.argv[1:]]

for path in [
    doc,
    prev,
    roadmap,
    action,
    current_state,
    current_state_check,
    runtime_smoke,
    makefile,
    bridge_h,
    bridge_cpp,
    stub_cpp,
    runtime_cpp,
]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
prev_text = prev.read_text(encoding="utf-8")
roadmap_text = roadmap.read_text(encoding="utf-8")
action_text = action.read_text(encoding="utf-8")
current_state_text = current_state.read_text(encoding="utf-8")
current_state_check_text = current_state_check.read_text(encoding="utf-8")
runtime_smoke_text = runtime_smoke.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")
source_text = "\n".join(
    path.read_text(encoding="utf-8")
    for path in [bridge_h, bridge_cpp, stub_cpp, runtime_cpp]
)

required = [
    "# Fasim GASAL2 Phase 7 GPU Exact Work-Unit Compaction First1 Shadow Scaffold",
    "phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold = fail_closed_shadow",
    "phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction",
    "previous_checkpoint = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md",
    "previous_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
    "required_runtime_env = FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW",
    "telemetry_prefix = benchmark.fasim_gasal2_phase7_gpu_exact_work_unit_compaction_",
    "runtime_default = off",
    "requested = 1",
    "active = 1",
    "scoreinfo_key_descriptors > 0",
    "scoreinfo_unique_keys > 0",
    "scoreinfo_duplicate_units = 0",
    "align_key_descriptors > 0",
    "align_unique_keys > 0",
    "align_duplicate_attempts = 0",
    "key_collisions = 0",
    "cpu_key_validation_mismatches = 0",
    "unsupported_key_descriptors = 0",
    "fallback_to_full_cpu_replay = 1",
    "scoreinfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "full_rows_equal = 1",
    "digest_match = 1",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "cpu_align_authority = 1",
    "gpu_score_authority = 0",
    "gpu_endpoint_authority = 0",
    "gpu_cigar_traceback_output_authority = 0",
    "gpu_output_digest_authority = 0",
    "gate_first1_shadow_pass = 1",
    "gate_first1_pass = 0",
    "CPU aligner.Align() authority = 1",
    "GPU score authority = 0",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "path_b_gpu_exact_work_unit_compaction_first1_shadow_scaffold = 1",
    "phase7_gpu_exact_work_unit_compaction_gate_first1_shadow_pass = 1",
    "phase7_gpu_exact_work_unit_compaction_gate_first1_pass = 0",
    "path_b_runtime_reduction_pr_allowed = 0",
    "path_b_runtime_work_drop_allowed = 0",
    "path_b_first64_runtime_allowed = 0",
    "next_valid_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go",
    "current_execution_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go",
    "current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "no real opt-in",
    "no runtime reduction in this scaffold",
    "no runtime work drop in this scaffold",
    "no first64 before first1 reducing runtime passes",
    "no GPU accept decision",
    "no GPU reject decision",
    "no final CPU output membership proof",
    "no top5-only contract",
]
missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing exact work-unit first1 shadow scaffold phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "scoreinfo_prealign_reduced = 1",
    "align_side_reduced = 1",
    "fallback_to_full_cpu_replay = 0",
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
        raise SystemExit(f"exact work-unit shadow doc contains forbidden phrase: {forbidden}")

if "next_valid_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold" not in prev_text:
    raise SystemExit("previous exact-work-unit spec no longer points to first1 shadow scaffold")

doc_link = "docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold.md"
for label, content in [
    ("roadmap", roadmap_text),
    ("action roadmap", action_text),
]:
    if doc_link not in content:
        raise SystemExit(f"{label} does not link exact-work-unit first1 shadow scaffold")
    if "current_execution_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go" not in content:
        raise SystemExit(f"{label} cursor was not advanced to exact-work-unit consumer/no-go")
    if "current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go" not in content:
        raise SystemExit(f"{label} next PR was not advanced to exact-work-unit consumer/no-go")

for phrase in [
    "FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW",
    "benchmark.fasim_gasal2_phase7_gpu_exact_work_unit_compaction_",
    "scoreinfo_key_descriptors",
    "align_key_descriptors",
    "gate_first1_shadow_pass",
]:
    if phrase not in runtime_smoke_text:
        raise SystemExit(f"runtime smoke missing phrase: {phrase}")

for phrase in [
    "check-fasim-gasal2-phase7-gpu-exact-work-unit-compaction-first1-shadow-runtime-smoke",
    "check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-first1-shadow-scaffold",
]:
    if phrase not in makefile_text:
        raise SystemExit(f"Makefile missing target: {phrase}")

for phrase in [
    "fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime",
    "fasim_gasal2_record_phase7_gpu_exact_work_unit_compaction_first1_shadow_requested",
    "fasim_gasal2_record_phase7_gpu_exact_work_unit_compaction_first1_shadow(",
    "FASIM_GASAL2_PHASE7_GPU_EXACT_WORK_UNIT_COMPACTION_FIRST1_SHADOW",
    "phase7_gpu_exact_work_unit_compaction_first1_shadow_scoreinfo_key_descriptors",
    "phase7_gpu_exact_work_unit_compaction_first1_shadow_align_key_descriptors",
]:
    if phrase not in source_text:
        raise SystemExit(f"source missing phrase: {phrase}")

for phrase in [
    "phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold=fail_closed_shadow",
    "phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold_status=fail_closed_no_runtime_reduction",
    "path_b_gpu_exact_work_unit_compaction_first1_shadow_scaffold=1",
    "phase7_gpu_exact_work_unit_compaction_gate_first1_shadow_pass=1",
    "next_valid_gate=phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go",
    "current_execution_gate=phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go",
    "current_next_pr=fasim_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go",
]:
    if phrase not in current_state_text and phrase not in current_state_check_text:
        raise SystemExit(f"current-state sources missing phrase: {phrase}")

print("phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold_doc=present")
print("phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_smoke=defined")
print("phase7_gpu_exact_work_unit_compaction_current_gate=consumer_or_no_go")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
