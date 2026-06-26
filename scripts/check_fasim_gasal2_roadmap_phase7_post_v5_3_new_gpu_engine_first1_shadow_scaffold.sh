#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold.md"
REDIRECT="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"

python3 - "$DOC" "$REDIRECT" "$ROADMAP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
redirect = Path(sys.argv[2])
roadmap = Path(sys.argv[3])

for path in [doc, redirect, roadmap]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 New GPU Engine First1 Shadow Scaffold",
    "phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold = fail_closed",
    "previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect.md",
    "required_runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_FIRST1_SHADOW",
    "telemetry_prefix = benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_",
    "requested = 1",
    "active = 0",
    "missing_certificate_producer = 1",
    "certificate_valid_before_d2h = 0",
    "final_cpu_output_membership_required_for_certificate = 0",
    "fallback_on_missing_bound = 1",
    "fallback_to_full_cpu_replay = 1",
    "cpu_align_authority = 1",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "gate_first1_pass = 0",
    "GpuScoreInfoTask",
    "GpuCandidateGroup",
    "GpuReplayAttempt",
    "new_gpu_engine_first1_shadow_gate_pass = 0",
    "runtime_reduction_enabled = 0",
    "first64_runtime_allowed = 0",
    "next_valid_gate = implement_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance",
    "current_next_pr = fasim_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit(
        "missing new GPU engine first1 shadow scaffold phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "active = 1",
    "certificate_valid_before_d2h = 1",
    "gate_first1_pass = 1",
    "new_gpu_engine_first1_shadow_gate_pass = 1",
    "first64_runtime_allowed = 1",
    "runtime_reduction_enabled = 1",
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
            "new GPU engine first1 shadow scaffold contains forbidden phrase: "
            + forbidden
        )

redirect_text = redirect.read_text(encoding="utf-8")
if "next_valid_gate = implement_new_gpu_engine_first1_shadow_or_path_a_acceptance" not in redirect_text:
    raise SystemExit("redirect checkpoint no longer points to first1 shadow implementation")

link = "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold.md"
if link not in roadmap.read_text(encoding="utf-8"):
    raise SystemExit("roadmap does not link first1 shadow scaffold checkpoint")

print("phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold=fail_closed")
print("phase7_post_v5_3_new_gpu_engine_first1_shadow_gate_pass=0")
print("next_valid_gate=implement_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance")
print("current_next_pr=fasim_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
