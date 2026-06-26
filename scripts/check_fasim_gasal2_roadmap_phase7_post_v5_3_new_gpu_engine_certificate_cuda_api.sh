#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
CLOSURE="$ROOT/docs/fasim_gasal2_goal_closure_phase_plan.md"
DRIVER="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
MAKEFILE="$ROOT/Makefile"
CUDA_H="$ROOT/cuda/prealign_cuda.h"
CUDA_CU="$ROOT/cuda/prealign_cuda.cu"
CUDA_STUB="$ROOT/cuda/prealign_cuda_stub.cpp"
BRIDGE_H="$ROOT/fasim/gasal2_align_bridge.h"
BRIDGE_CPP="$ROOT/fasim/gasal2_align_bridge.cpp"
BRIDGE_STUB="$ROOT/fasim/gasal2_align_bridge_stub.cpp"
LONGTARGET="$ROOT/fasim/Fasim-LongTarget.cpp"

python3 - "$DOC" "$PREV" "$ROADMAP" "$CLOSURE" "$DRIVER" "$MAKEFILE" \
  "$CUDA_H" "$CUDA_CU" "$CUDA_STUB" "$BRIDGE_H" "$BRIDGE_CPP" "$BRIDGE_STUB" "$LONGTARGET" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

(
    doc,
    prev,
    roadmap,
    closure,
    driver,
    makefile,
    cuda_h,
    cuda_cu,
    cuda_stub,
    bridge_h,
    bridge_cpp,
    bridge_stub,
    longtarget,
) = [Path(arg) for arg in sys.argv[1:]]

for path in [
    doc,
    prev,
    roadmap,
    closure,
    driver,
    makefile,
    cuda_h,
    cuda_cu,
    cuda_stub,
    bridge_h,
    bridge_cpp,
    bridge_stub,
    longtarget,
]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

doc_text = doc.read_text(encoding="utf-8")
doc_flat = " ".join(doc_text.split())
prev_text = prev.read_text(encoding="utf-8")
roadmap_text = roadmap.read_text(encoding="utf-8")
roadmap_flat = " ".join(roadmap_text.split())
closure_text = closure.read_text(encoding="utf-8")
driver_text = driver.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")
cuda_text = "\n".join(
    path.read_text(encoding="utf-8") for path in [cuda_h, cuda_cu, cuda_stub]
)
bridge_text = "\n".join(
    path.read_text(encoding="utf-8") for path in [bridge_h, bridge_cpp, bridge_stub, longtarget]
)

required_doc = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Certificate CUDA API",
    "phase7_post_v5_3_new_gpu_engine_certificate_cuda_api = fail_closed_api_scaffold",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold.md",
    "previous_gate = implement_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance",
    "required_runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_CERTIFICATE_CUDA_API",
    "telemetry_prefix = benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_",
    "new_cuda_api = prealign_cuda_emit_new_engine_skipped_work_certificates",
    "GpuScoreInfoTask",
    "GpuCandidateGroup",
    "GpuReplayAttempt",
    "PreAlignCudaNewEngineSkippedWorkCertificate",
    "skipped_scoreinfo_upper_bound_score",
    "skipped_attempt_upper_bound_score",
    "skipped_attempt_upper_bound_nt",
    "skipped_attempt_upper_bound_identity",
    "skipped_attempt_upper_bound_stability",
    "task_output_capacity_exhausted",
    "scoreinfo_local_break_state",
    "certificate_producer_active = 0",
    "certificate_valid_before_d2h = 0",
    "final_cpu_output_membership_required_for_certificate = 0",
    "runtime_reduction_enabled = 0",
    "first1_runtime_allowed = 0",
    "first64_runtime_allowed = 0",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "cpu_align_authority = 1",
    "certificate_cuda_api_gate_pass = 0",
    "next_valid_gate = implement_new_gpu_engine_certificate_producer_first1_or_path_a_acceptance",
    "current_next_pr = fasim_new_gpu_engine_certificate_producer_first1_or_path_a_acceptance",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
missing_doc = [phrase for phrase in required_doc if phrase not in doc_text and phrase not in doc_flat]
if missing_doc:
    raise SystemExit(
        "missing new GPU engine certificate CUDA API doc phrase(s):\n"
        + "\n".join(missing_doc)
    )

for forbidden in [
    "certificate_producer_active = 1",
    "certificate_valid_before_d2h = 1",
    "certificate_cuda_api_gate_pass = 1",
    "runtime_reduction_enabled = 1",
    "first1_runtime_allowed = 1",
    "first64_runtime_allowed = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
]:
    if forbidden in doc_text:
        raise SystemExit(
            "new GPU engine certificate CUDA API doc contains forbidden phrase: "
            + forbidden
        )

if "next_valid_gate = implement_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance" not in prev_text:
    raise SystemExit("previous first1 shadow scaffold no longer points to certificate CUDA API gate")

required_cuda = [
    "struct PreAlignCudaNewEngineScoreInfoTask",
    "struct PreAlignCudaNewEngineCandidateGroup",
    "struct PreAlignCudaNewEngineReplayAttempt",
    "struct PreAlignCudaNewEngineSkippedWorkCertificate",
    "struct PreAlignCudaNewEngineCertificateResult",
    "skippedScoreInfoUpperBoundScore",
    "skippedAttemptUpperBoundScore",
    "skippedAttemptUpperBoundNt",
    "skippedAttemptUpperBoundIdentity",
    "skippedAttemptUpperBoundStability",
    "taskOutputCapacityExhausted",
    "scoreInfoLocalBreakState",
    "prealign_cuda_emit_new_engine_skipped_work_certificates",
]
missing_cuda = [phrase for phrase in required_cuda if phrase not in cuda_text]
if missing_cuda:
    raise SystemExit(
        "missing new GPU engine certificate CUDA API phrase(s):\n"
        + "\n".join(missing_cuda)
    )

required_bridge = [
    "FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_CERTIFICATE_CUDA_API",
    "fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_runtime",
    "fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_requested",
    "fasim_print_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_stats",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_requested",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_active",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_producer_active",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_valid_before_d2h",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_scoreinfo_upper_bound_score",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_score",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_nt",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_identity",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_skipped_attempt_upper_bound_stability",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_task_output_capacity_exhausted",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_scoreinfo_local_break_state",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_runtime_reduction_enabled",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_cuda_api_gate_pass",
]
missing_bridge = [phrase for phrase in required_bridge if phrase not in bridge_text]
if missing_bridge:
    raise SystemExit(
        "missing new GPU engine certificate CUDA API runtime phrase(s):\n"
        + "\n".join(missing_bridge)
    )

link = "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api.md"
if link not in roadmap_text:
    raise SystemExit("roadmap does not link certificate CUDA API checkpoint")

if "next_valid_gate = implement_new_gpu_engine_certificate_producer_first1_or_path_a_acceptance" not in roadmap_flat:
    raise SystemExit("roadmap no longer records certificate CUDA API historical next gate")

for path_name, text in [("closure plan", closure_text), ("phase driver", driver_text)]:
    if "current_gate = first1_reducing_runtime_with_certificate_or_no_go" not in text:
        raise SystemExit(f"{path_name} does not point to the post-producer first1 runtime gate")
    if "current_next_pr = fasim_new_gpu_engine_first1_reducing_runtime_or_no_go" not in text:
        raise SystemExit(f"{path_name} does not point to the post-producer next PR")

target = "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-cuda-api:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

if "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-cuda-api" not in makefile_text:
    raise SystemExit("current-state aggregate does not include certificate CUDA API target")

print("phase7_post_v5_3_new_gpu_engine_certificate_cuda_api=fail_closed_api_scaffold")
print("phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_gate_pass=0")
print("certificate_producer_active=0")
print("certificate_valid_before_d2h=0")
print("historical_next_valid_gate=implement_new_gpu_engine_certificate_producer_first1_or_path_a_acceptance")
print("current_next_pr=fasim_new_gpu_engine_first1_reducing_runtime_or_no_go")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
