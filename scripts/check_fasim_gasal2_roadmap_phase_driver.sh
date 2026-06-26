#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_goal_completion_phase_driver.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"

python3 - "$DOC" "$ROADMAP" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])

for path in [doc, roadmap]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
roadmap_text = roadmap.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Goal Completion Phase Driver",
    "This is the direct phase driver for making the active Fasim/GASAL2 goal closable.",
    "It is not a success claim.",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "current_path = Path B",
    "current_phase = Phase 7",
    "current_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
    "current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold",
    "current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md",
    "Historical pre-upper-bound-reject-spec cursor:",
    "current_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go",
    "current_next_pr = fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go",
    "Historical pre-post-native-DP-fork cursor:",
    "current_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go",
    "current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go",
    "Historical pre-native-DP-fork cursor:",
    "current_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go",
    "current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go",
    "Historical pre-native-DP-consumer cursor:",
    "current_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold",
    "current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold",
    "Historical pre-native-DP-shadow cursor:",
    "current_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance",
    "current_next_pr = fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance",
    "Historical pre-native-DP-spec cursor:",
    "current_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold",
    "current_next_pr = fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold",
    "Historical pre-consumer-no-go cursor:",
    "current_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go",
    "current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go",
    "Historical pre-scaffold cursor:",
    "current_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold",
    "current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold",
    "docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold.md",
    "fasim_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go",
    "docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go.md",
    "docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md",
    "path_b_new_design_family = gasal2_full_align_result_with_cpu_verifier_certificate",
    "fasim_gasal2_full_align_verifier_design_spec_or_path_a_acceptance",
    "runtime_reduction_allowed = 0",
    "runtime_work_drop_allowed = 0",
    "runtime_pr_allowed = 0",
    "first1_runtime_reduction_gate_pass = 0",
    "first64_runtime_allowed = 0",
    "Path A: scoped completion",
    "Path B: broad completion",
    "Do not mix Path A evidence into Path B completion.",
    "## Current Stepwise Execution Order",
    "Step 1 - Phase 7.1:",
    "This is now fail-closed scaffolded.",
    "Step 2A - Path A if accepted:",
    "close only as scoped completion",
    "Step 2B - Path B if the spec is complete:",
    "the certificate CUDA API producer first1 synthetic gate is now present.",
    "Step 3 - Phase 7.2:",
    "the certificate producer has proved skipped work before D2H and before final CPU output membership is known for the synthetic first1 API gate.",
    "Step 4 - Phase 7.3:",
    "first1 runtime reduction no-go is recorded.",
    "Step 4B - Phase 7.3 design response:",
    "the after-first1-no-go design checkpoint is recorded.",
    "Step 4C - Phase 7.3 real-source first1 spec:",
    "the real-source first1 spec is defined.",
    "Step 4D - Phase 7.3 real runtime certificate source:",
    "real_fasim_runtime_certificate_source = 1",
    "real_fasim_runtime_work_drop_path = 0",
    "gate_first1_source_pass = 1",
    "gate_first1_pass = 0",
    "Step 4E - Phase 7.3 work-drop proof design:",
    "the pre-drop output-inert work-drop proof design checkpoint is recorded.",
    "Step 4F - Phase 7.3 first1 proof shadow:",
    "fail-closed proof shadow is recorded against the real runtime certificate",
    "Step 4G - Phase 7.3 proof consumer or no-go:",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md",
    "Step 4H - Next fork:",
    "record explicit Path A scoped acceptance, or design a genuinely different GPU execution path",
    "Step 4I - Phase 7.4c different GPU execution design:",
    "docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md",
    "Fasim-compatible GPU scoreInfo frontier certificate engine",
    "Step 4J - Phase 7.4d GPU scoreInfo certificate engine spec:",
    "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.md",
    "first1 fail-closed shadow scaffold boundary",
    "Step 4K - Phase 7.4e GPU scoreInfo certificate engine first1 shadow scaffold:",
    "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.md",
    "FASIM_GASAL2_PHASE7_POST_CONSUMER_GPU_SCOREINFO_CERT_ENGINE_FIRST1_SHADOW=1",
    "Step 4L - Phase 7.4f GPU scoreInfo certificate engine consumer no-go:",
    "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md",
    "no valid pre-drop certificate to consume",
    "Step 4M - Phase 7.4g scoreInfo certificate-engine fork:",
    "docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go.md",
    "GPU-owned Fasim scoreInfo consumer",
    "Step 5 - Phase 6:",
    "add a broad_replacement workload matrix row only after the proof consumer and broad gates pass",
    "Step 6 - Phase 8:",
    "close the goal only if Path A was explicitly accepted or Path B has a passing broad_replacement row",
    "fasim_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance",
    "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go",
    "fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance",
    "The next checkpoint must not change output authority.",
    "## Phase Driver",
    "### Phase 0 - Reproducibility",
    "### Phase 1 - Scoped Acceptance",
    "### Phase 2 - Full-Output Baseline",
    "### Phase 3 - CPU Output-Side Reduction",
    "### Phase 4 - Sort/Top-N Only If Dominant",
    "### Phase 5 - Archive Artifact",
    "### Phase 6 - Workload Matrix",
    "### Phase 7 - Broad Replacement Restart",
    "### Phase 8 - Close Decision",
    "clean checkout can rebuild the patched GASAL2/Fasim bridge",
    "user_scope_acceptance_recorded = 1",
    "scoped_completion_may_close_goal = 1",
    "restored rows and digest match CPU authority",
    "missing_rows = 0",
    "extra_rows = 0",
    "sort_or_filter_is_dominant = 1",
    "archive_restore_rows_equal = 1",
    "claimed rows have passing scoped contracts",
    "broad_replacement rows exist only after Phase 7 broad gates pass",
    "full row-set/digest equality",
    "runtime win over CPU authority",
    "scoreInfo/preAlign work reduced or replaced",
    "Align-side work reduced or replaced",
    "fallback accounting clean",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "current descriptor stream cannot prove output-inert skips",
    "accepted_pre_d2h_proof_families = 0",
    "new_pre_d2h_proof_family_first1_smoke_allowed = 0",
    "real_fasim_runtime_certificate_source = 1",
    "real_fasim_runtime_work_drop_path = 0",
    "runtime_certificate_is_synthetic = 0",
    "source_is_pre_drop = 1",
    "gate_first1_source_pass = 1",
    "gate_first1_pass = 0",
    "reducing_runtime_allowed = 0",
    "first64_runtime_allowed = 0",
    "first1_runtime_reduction_allowed = 1",
    "different_gpu_execution_design_required = 1",
    "path_a_user_acceptance_required = 1",
    "A valid different Path B design must provide a new pre-D2H proof source",
    "Do not reuse the current PreAlignCudaAttemptDescriptor-only stream",
    "Do not reuse aggregate proof-search export as runtime proof",
    "Do not use final CPU output membership as runtime proof",
    "## Immediate Next Work",
    "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scaffold.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md",
    "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md",
    "docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md",
    "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.md",
    "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.md",
    "docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md",
    "record Path A scoped acceptance if the user explicitly accepts it",
    "pre-drop output-inert work-drop proof design before any runtime reduction",
    "If Path B continues, do not implement runtime from any stopped synthetic",
    "full-align verifier first1 fail-closed shadow scaffold",
    "That scaffold must only observe GASAL2 full AlignResult proposals and CPU",
    "It must not enable runtime reduction, drop work, run first64, or change output authority.",
    "Do not relabel the existing v5 CPU-authority replay as the new full-align",
    "The current broad objective remains open until Phase 8 accepts either explicit",
    "If the user accepts Path A, move to Phase 8 scoped close packet.",
    "## Commands",
    "make check-fasim-gasal2-roadmap-phase-driver",
    "make check-fasim-gasal2-roadmap-current-state",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit("missing phase-driver phrase(s):\n" + "\n".join(missing))

phase_order = [
    "### Phase 0 - Reproducibility",
    "### Phase 1 - Scoped Acceptance",
    "### Phase 2 - Full-Output Baseline",
    "### Phase 3 - CPU Output-Side Reduction",
    "### Phase 4 - Sort/Top-N Only If Dominant",
    "### Phase 5 - Archive Artifact",
    "### Phase 6 - Workload Matrix",
    "### Phase 7 - Broad Replacement Restart",
    "### Phase 8 - Close Decision",
]
positions = [text.index(heading) for heading in phase_order]
if positions != sorted(positions):
    raise SystemExit("phase driver headings are out of order")

for forbidden in [
    "broad_objective_status = complete",
    "must_not_call_update_goal_complete = 0",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "top5-only evidence closes broad objective = 1",
    "archive-only evidence closes broad objective = 1",
    "output-drift speedup counts as success = 1",
    "first64_runtime_allowed = 1",
    "reducing_runtime_allowed = 1",
    "runtime_pr_allowed = 1",
]:
    if forbidden in text:
        raise SystemExit(f"phase driver contains forbidden phrase: {forbidden}")

link = "docs/fasim_gasal2_goal_completion_phase_driver.md"
if link not in roadmap_text:
    raise SystemExit(f"roadmap does not link {link}")

print("phase_driver_document=present")
print("phase_driver_current_phase=phase7")
print("phase_driver_current_gate=phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold")
print("phase_driver_path_a_requires_user_acceptance=1")
print("phase_driver_path_b_requires_different_design_or_broad_gate=1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
