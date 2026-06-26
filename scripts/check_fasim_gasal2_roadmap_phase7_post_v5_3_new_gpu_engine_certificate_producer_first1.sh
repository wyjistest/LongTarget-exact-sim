#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_producer_first1.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api.md"
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
closure_text = closure.read_text(encoding="utf-8")
driver_text = driver.read_text(encoding="utf-8")
makefile_text = makefile.read_text(encoding="utf-8")
cuda_text = "\n".join(
    path.read_text(encoding="utf-8") for path in [cuda_h, cuda_cu, cuda_stub]
)
bridge_text = "\n".join(
    path.read_text(encoding="utf-8")
    for path in [bridge_h, bridge_cpp, bridge_stub, longtarget]
)

required_doc = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine Certificate Producer First1",
    "phase7_post_v5_3_new_gpu_engine_certificate_producer_first1 = producer_first1_synthetic_gate",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api.md",
    "previous_gate = implement_new_gpu_engine_certificate_producer_first1_or_path_a_acceptance",
    "runtime_reduction_enabled = 0",
    "first1_runtime_reduction_allowed = 0",
    "first64_runtime_allowed = 0",
    "certificate_producer_active = 1",
    "certificate_valid_before_d2h = 1",
    "final_cpu_output_membership_required_for_certificate = 0",
    "certificate_false_negatives = 0",
    "certificate_missing_required_attempts = 0",
    "skipped_groups = 1",
    "skipped_attempts = 1",
    "conservative_fallback_groups = 0",
    "certificate_cuda_api_gate_pass = 1",
    "output_authority_changed = 0",
    "cpu_align_authority = 1",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "next_valid_gate = first1_reducing_runtime_with_certificate_or_no_go",
    "current_next_pr = fasim_new_gpu_engine_first1_reducing_runtime_or_no_go",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
missing_doc = [phrase for phrase in required_doc if phrase not in doc_text and phrase not in doc_flat]
if missing_doc:
    raise SystemExit(
        "missing certificate producer first1 doc phrase(s):\n" + "\n".join(missing_doc)
    )

for forbidden in [
    "runtime_reduction_enabled = 1",
    "first1_runtime_reduction_allowed = 1",
    "first64_runtime_allowed = 1",
    "final_cpu_output_membership_required_for_certificate = 1",
    "certificate_false_negatives = 1",
    "certificate_missing_required_attempts = 1",
    "output_authority_changed = 1",
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
            "certificate producer first1 doc contains forbidden phrase: " + forbidden
        )

if "next_valid_gate = implement_new_gpu_engine_certificate_producer_first1_or_path_a_acceptance" not in prev_text:
    raise SystemExit("previous certificate CUDA API doc no longer points to producer first1 gate")

required_cuda = [
    "prealign_cuda_emit_new_engine_skipped_work_certificates",
    "prealign_cuda_new_engine_certificate_kernel",
    "certificateProducerActive = true",
    "certificateValidBeforeD2h = true",
    "finalCpuOutputMembershipRequiredForCertificate = false",
    "skippedGroups",
    "skippedAttempts",
    "certificateFalseNegatives = 0",
    "certificateMissingRequiredAttempts = 0",
    "missing output buffer",
    "invalid new GPU engine certificate dimensions",
]
missing_cuda = [phrase for phrase in required_cuda if phrase not in cuda_text]
if missing_cuda:
    raise SystemExit(
        "missing certificate producer CUDA phrase(s):\n" + "\n".join(missing_cuda)
    )

required_bridge = [
    "fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_producer_first1_pass",
    "phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_producer_active = 1",
    "phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_valid_before_d2h = 1",
    "phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_final_cpu_output_membership_required_for_certificate = 0",
    "phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_false_negatives = 0",
    "phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_missing_required_attempts = 0",
    "phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_cuda_api_gate_pass = 1",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_producer_active",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_valid_before_d2h",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_certificate_cuda_api_gate_pass",
]
missing_bridge = [phrase for phrase in required_bridge if phrase not in bridge_text]
if missing_bridge:
    raise SystemExit(
        "missing certificate producer bridge phrase(s):\n" + "\n".join(missing_bridge)
    )

doc_link = "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_producer_first1.md"
if doc_link not in roadmap_text:
    raise SystemExit("roadmap does not link certificate producer first1 checkpoint")

for path_name, text in [("closure plan", closure_text), ("phase driver", driver_text)]:
    if "current_gate = first1_reducing_runtime_with_certificate_or_no_go" not in text:
        raise SystemExit(f"{path_name} does not point to first1 reducing runtime gate")
    if "current_next_pr = fasim_new_gpu_engine_first1_reducing_runtime_or_no_go" not in text:
        raise SystemExit(f"{path_name} does not point to first1 reducing runtime next PR")

target = "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-producer-first1:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

if "check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-producer-first1" not in makefile_text:
    raise SystemExit("current-state aggregate does not include certificate producer first1 target")

print("phase7_post_v5_3_new_gpu_engine_certificate_producer_first1=producer_first1_synthetic_gate")
print("certificate_producer_active=1")
print("certificate_valid_before_d2h=1")
print("certificate_false_negatives=0")
print("certificate_missing_required_attempts=0")
print("runtime_reduction_enabled=0")
print("next_valid_gate=first1_reducing_runtime_with_certificate_or_no_go")
print("current_next_pr=fasim_new_gpu_engine_first1_reducing_runtime_or_no_go")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
