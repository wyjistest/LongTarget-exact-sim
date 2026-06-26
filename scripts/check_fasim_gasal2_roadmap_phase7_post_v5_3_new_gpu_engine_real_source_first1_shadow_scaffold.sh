#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scaffold.md"
SPEC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"

python3 - "$DOC" "$SPEC" "$PHASE_PLAN" "$ROADMAP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc, spec, phase_plan, roadmap = [Path(arg) for arg in sys.argv[1:]]
for path in [doc, spec, phase_plan, roadmap]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Real-Source First1 Shadow Scaffold",
    "phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scaffold = fail_closed_no_real_source",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md",
    "previous_gate = phase7_new_gpu_engine_real_source_first1_shadow_or_path_a_acceptance",
    "required_runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_FIRST1_SHADOW",
    "telemetry_prefix = benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "requested = 1",
    "active = 0",
    "real_fasim_runtime_certificate_source = 0",
    "real_fasim_runtime_work_drop_path = 0",
    "runtime_certificate_is_synthetic = 0",
    "missing_certificate = 1",
    "fallback_to_full_cpu_replay = 1",
    "scoreinfo_prealign_reduced = 0",
    "align_side_reduced = 0",
    "fallback_accounting_clean = 0",
    "cpu_align_authority = 1",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "gate_first1_pass = 0",
    "real_source_first1_shadow_gate_pass = 0",
    "next_valid_gate = implement_real_source_certificate_source_or_path_a_acceptance",
    "current_next_pr = fasim_new_gpu_engine_real_source_certificate_source_or_path_a_acceptance",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing real-source first1 shadow scaffold phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "active = 1",
    "real_fasim_runtime_certificate_source = 1",
    "real_fasim_runtime_work_drop_path = 1",
    "runtime_certificate_is_synthetic = 1",
    "gate_first1_pass = 1",
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "first64_runtime_allowed = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in text:
        raise SystemExit(
            "real-source first1 shadow scaffold contains forbidden phrase: "
            + forbidden
        )

spec_text = spec.read_text(encoding="utf-8")
if "next_valid_gate = phase7_new_gpu_engine_real_source_first1_shadow_or_path_a_acceptance" not in spec_text:
    raise SystemExit("real-source first1 spec no longer points to shadow gate")

doc_link = "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scaffold.md"
for name, source in [
    ("phase-to-completion plan", phase_plan.read_text(encoding="utf-8")),
    ("roadmap", roadmap.read_text(encoding="utf-8")),
]:
    if doc_link not in source:
        raise SystemExit(f"{name} does not link real-source first1 shadow scaffold")

print("phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scaffold=fail_closed_no_real_source")
print("real_source_first1_shadow_gate_pass=0")
print("next_valid_gate=implement_real_source_certificate_source_or_path_a_acceptance")
print("current_next_pr=fasim_new_gpu_engine_real_source_certificate_source_or_path_a_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
