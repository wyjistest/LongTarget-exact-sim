#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"

python3 - "$DOC" "$PHASE_PLAN" "$ROADMAP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
phase_plan = Path(sys.argv[2])
roadmap = Path(sys.argv[3])
for path in (doc, phase_plan, roadmap):
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
phase_text = phase_plan.read_text(encoding="utf-8")
roadmap_text = roadmap.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Real-Source Certificate Source First1",
    "phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1 =",
    "source_only_pre_drop_runtime_hook",
    "FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_CERTIFICATE_SOURCE",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_",
    "runtime_reduction_enabled = 0",
    "runtime_work_drop_enabled = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "source_is_pre_drop = 1",
    "source_is_legacy_byte_cuda = 1",
    "runtime_certificate_is_synthetic = 0",
    "candidate_uses_final_cpu_output_as_runtime_proof = 0",
    "real_fasim_runtime_certificate_source = 1",
    "real_fasim_runtime_work_drop_path = 0",
    "source_task_count > 0",
    "source_scoreinfo_count > 0",
    "source_attempt_count > 0",
    "reference_scoreinfo_count > 0",
    "reference_attempt_count > 0",
    "missing_certificate = 0",
    "fallback_to_full_cpu_replay = 1",
    "fallback_accounting_clean = 1",
    "certificate_false_negatives = 0",
    "missing_required_attempts = 0",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "gate_first1_source_pass = 1",
    "gate_first1_pass = 0",
    "real_source_certificate_source_gate_pass = 1",
    "next_valid_gate = design_pre_drop_output_inert_work_drop_proof",
    "current_next_pr = fasim_new_gpu_engine_pre_drop_work_drop_proof_design",
    "Do not run first64 from this checkpoint.",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing real-source certificate-source phrase(s):\n" + "\n".join(missing)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "runtime_work_drop_enabled = 1",
    "first64_runtime_allowed = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "candidate_uses_final_cpu_output_as_runtime_proof = 1",
    "gate_first1_pass = 1",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in text:
        raise SystemExit(f"real-source certificate-source doc contains forbidden phrase: {forbidden}")

if str(doc.relative_to(roadmap.parent.parent)) not in roadmap_text:
    raise SystemExit("roadmap does not link real-source certificate-source checkpoint")
if "### Phase 7.2 - Real Runtime Certificate Source" not in phase_text:
    raise SystemExit("phase-to-completion plan no longer contains Phase 7.2")
if "next_valid_gate = design_pre_drop_output_inert_work_drop_proof" not in phase_text:
    raise SystemExit("phase-to-completion plan no longer records the Phase 7.3 next gate")
if (
    "current_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance"
    not in phase_text
):
    raise SystemExit("phase-to-completion plan no longer records the current GPU-owned scoreInfo consumer spec cursor")
if "first64_runtime_allowed = 0" not in phase_text:
    raise SystemExit("phase-to-completion plan must keep first64 disabled")

print("phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_doc=present")
print("phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate=source_only")
print("phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_reduction_enabled=0")
print("phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_next_gate=design_pre_drop_output_inert_work_drop_proof")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
