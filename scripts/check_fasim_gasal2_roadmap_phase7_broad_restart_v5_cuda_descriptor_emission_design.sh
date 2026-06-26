#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v5_cuda_descriptor_emission_design.md"
PREV="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$PREV" "$ROADMAP" "$MAKEFILE" <<'PY'
from pathlib import Path
import sys

doc = Path(sys.argv[1])
prev = Path(sys.argv[2])
roadmap = Path(sys.argv[3])
makefile = Path(sys.argv[4])

for path in [doc, prev, roadmap, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
prev_flat = " ".join(prev.read_text(encoding="utf-8").split())
roadmap_flat = " ".join(roadmap.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v5_cuda_descriptor_emission_design = defined",
    "phase7_broad_restart_v5_cuda_descriptor_emission_status = design_only",
    "phase7_broad_restart_v5_cuda_descriptor_emission_may_claim_completion = 0",
    "previous_checkpoint = no_go_needs_cuda_descriptor_emission_kernel",
    "current_runtime_checkpoint = gate_v5_1_pass_first1",
    "next_required_gate = phase7_gate_v5_2_cpu_authority_replay_first1",
    "required_runtime_env = FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE",
    "new_cuda_api = prealign_cuda_emit_legacy_byte_attempt_descriptors",
    "input_contract = encoded_targets_plus_min_scores_plus_task_metadata",
    "output_contract = compact_attempt_descriptors_not_scoreinfo_rows",
    "Descriptor fields:",
    "task_index",
    "scoreinfo_position",
    "scoreinfo_score",
    "attempt_order",
    "target_start",
    "cutlength",
    "target_end_required_for_fallback",
    "GPU endpoint/CIGAR/traceback/output authority = 0",
    "CPU aligner.Align() authority replay = 1",
    "host-visible full legacy scoreInfo row stream = forbidden",
    "validation compares after descriptor emission",
    "descriptor_false_negatives = 0",
    "missing_required_attempts = 0",
    "candidate_attempts_below_all_column_replay_scale = 1",
    "next_gate = runtime_smoke_true_pre_scoreinfo_descriptor_source_first1",
    "current_next_gate = phase7_gate_v5_2_cpu_authority_replay_first1",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing descriptor-emission design phrase: {phrase}")

for stale in [
    "allowed: use CPU preAlign as descriptor source",
    "allowed: promote PreAlignCudaPeak rows as v5 interface",
    "GPU output authority = 1",
    "broad_replacement row may be added from design checkpoint",
]:
    if stale in flat:
        raise SystemExit(f"descriptor-emission design contains forbidden phrase: {stale}")

if "next_required_artifact = cuda_descriptor_emission_kernel_or_api_design" not in prev_flat:
    current_runtime_pass = all(
        phrase in prev_flat
        for phrase in [
            "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke = gate_v5_1_pass_first1",
            "next_required_gate = phase7_gate_v5_2_cpu_authority_replay_first1",
        ]
    )
    if not current_runtime_pass:
        raise SystemExit(
            "previous checkpoint is neither descriptor-emission design request "
            "nor v5.1 runtime pass"
        )

link = "docs/fasim_gasal2_phase7_broad_restart_v5_cuda_descriptor_emission_design.md"
if link not in roadmap_flat:
    raise SystemExit("roadmap does not link descriptor-emission design")

target = (
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-"
    "descriptor-emission-design:"
)
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

print("phase7_broad_restart_v5_cuda_descriptor_emission_design=defined")
print("phase7_broad_restart_v5_cuda_descriptor_emission_status=design_only")
print("phase7_broad_restart_v5_cuda_descriptor_emission_current_runtime_checkpoint=gate_v5_1_pass_first1")
print("phase7_broad_restart_v5_next_gate=phase7_gate_v5_2_cpu_authority_replay_first1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
