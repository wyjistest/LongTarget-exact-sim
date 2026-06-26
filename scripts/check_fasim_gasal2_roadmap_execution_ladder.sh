#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_goal_completion_execution_ladder.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
CHECKLIST="$ROOT/docs/fasim_gasal2_goal_completion_phase_checklist.md"
PHASE_PLAN="$ROOT/docs/fasim_gasal2_goal_completion_phase_plan.md"

python3 - "$DOC" "$ROADMAP" "$CHECKLIST" "$PHASE_PLAN" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])
checklist = Path(sys.argv[3])
phase_plan = Path(sys.argv[4])

for path in [doc, roadmap, checklist, phase_plan]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())
combined = "\n".join(
    path.read_text(encoding="utf-8") for path in [roadmap, checklist, phase_plan]
)

required = [
    "# Fasim GASAL2 Goal Completion Execution Ladder",
    "The active broad path is currently in Phase 7, after the v5 true pre-scoreInfo descriptor-source strict runtime smoke and v5.2 CPU-authority replay smoke passed first1:",
    "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke = gate_v5_1_pass_first1",
    "phase7_broad_restart_v5_gate_v5_1_pass = 1",
    "phase7_broad_restart_v5_cpu_authority_replay_smoke = gate_v5_2_pass_first1",
    "phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate = correctness_clean_performance_no_go",
    "phase7_broad_restart_v5_gate_v5_2_pass = 1",
    "phase7_broad_restart_v5_gate_v5_3_pass = 0",
    "phase7_broad_restart_v5_cuda_descriptor_emission_design = defined",
    "phase7_broad_restart_v5_cuda_descriptor_emission_status = design_only",
    "new_cuda_api = prealign_cuda_emit_legacy_byte_attempt_descriptors",
    "Next gate:",
    "different_gpu_execution_design_or_path_a_scope_acceptance",
    "different GPU execution design or explicit Path A scoped acceptance",
    "Do not rebrand v4 host-visible scoreInfo row replay as v5.",
    "### Gate v5.0: CUDA Descriptor-Emission Design",
    "docs/fasim_gasal2_phase7_broad_restart_v5_cuda_descriptor_emission_design.md",
    "output_contract = compact_attempt_descriptors_not_scoreinfo_rows",
    "host-visible full legacy scoreInfo row stream = forbidden",
    "CPU aligner.Align() authority replay = 1",
    "GPU endpoint/CIGAR/traceback/output authority = 0",
    "make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-descriptor-emission-design",
    "### Gate v5.1: True Pre-ScoreInfo Descriptor Source",
    "add structs/API in cuda/prealign_cuda.h",
    "add fail-closed CPU-only stub in cuda/prealign_cuda_stub.cpp",
    "add CUDA implementation in cuda/prealign_cuda.cu",
    "wire a default-off runner in fasim/Fasim-LongTarget.cpp",
    "call the descriptor-emission API before CPU scoreInfo/preAlign generation",
    "make check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke",
    "source_is_pre_scoreinfo = 1",
    "scoreinfo_prealign_reduced = 1",
    "gpu_descriptor_attempts > 0",
    "descriptor_false_negatives = 0",
    "missing_required_attempts = 0",
    "gate_v5_1_pass = 1",
    "CPU scoreInfo rows are used as descriptor source",
    "### Gate v5.2: CPU-Authority Replay",
    "full_rows_equal = true",
    "digest_match = true",
    "triplex_mismatches = 0",
    "candidate_align_attempts < reference_align_attempts",
    "scoreInfo/preAlign work reduced or replaced",
    "### Gate v5.3: First64 Broad Gate",
    "candidate_wall_seconds < baseline_wall_seconds",
    "### Gate v5.4: Workload Matrix Promotion",
    "add a contract=broad_replacement row only after Phase 7.4 passes",
    "If Gate v5.1 cannot pass without CPU scoreInfo as the source:",
    "record a v5 no-go checkpoint",
    "If Gate v5.3 passes:",
    "close only if Phase 8 sets must_not_call_update_goal_complete = 0",
    "Treat docs/fasim_gasal2_phase7_broad_restart_v5_cuda_descriptor_emission_design.md as the current active Path B design checkpoint:",
    "Treat docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_smoke.md as the current strict Gate v5.2 runtime pass checkpoint:",
    "Treat docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate.md as the current strict Gate v5.3 no-go checkpoint:",
    "phase7_broad_restart_v5_first64_candidate_vs_baseline = 0.706009",
    "phase7_broad_restart_v5_runtime_next_gate = different_gpu_execution_design_or_path_a_scope_decision",
    "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md",
    "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export.md",
    "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1.md",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_design = defined",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_status = first1_export_pass",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export = pass",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_implement = 1",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion = 0",
    "next_required_gate = pre_d2h_output_inert_proof_acceptance_first1",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1 = no_go",
    "accepted_pre_d2h_proof_families = 0",
    "reducing_runtime_allowed = 0",
    "first64_runtime_allowed = 0",
    "current_next_pr = fasim: design different GPU execution design or scope acceptance",
    "runtime_reduction_enabled = 0",
    "Implement the minimal default-off descriptor-emission prototype:",
    "Make Gate v5.1 and Gate v5.2 pass before doing any broader characterization:",
    "If Gate v5.1 passes, create the Gate v5.2 CPU-authority replay checkpoint.",
    "Gate v5.3 first64 broad characterization is complete and recorded as no-go.",
    "Add a broad_replacement matrix row only after Gate v5.3 passes.",
    "Run Phase 8 only after Path A acceptance or Path B broad gate pass.",
    "Do not mark the active goal complete before Phase 8 allows it.",
]

missing = [phrase for phrase in required if phrase not in flat and phrase not in text]
if missing:
    raise SystemExit(
        "missing required execution ladder phrase(s):\n" + "\n".join(missing)
    )

for stale in [
    "The next phase must run the same GPU legacy-byte scoreInfo source through first64",
    "Run only the v4 source first64 broad gate, or use Path A scoped completion",
    "promote PreAlignCudaPeak rows as v5 interface",
    "GPU endpoint/CIGAR/traceback/output authority = 1",
]:
    if stale in flat:
        raise SystemExit(f"execution ladder contains stale phrase: {stale}")

links = [
    "docs/fasim_gasal2_goal_completion_execution_ladder.md",
]
for link in links:
    if link not in combined:
        raise SystemExit(f"roadmap/checklist/phase plan do not link {link}")

print("execution_ladder_document=present")
print("execution_ladder_current_gate=v5_1_true_pre_scoreinfo_descriptor_source_passed")
print("execution_ladder_next_runtime_gate=different_gpu_execution_design_or_path_a_scope_acceptance")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
