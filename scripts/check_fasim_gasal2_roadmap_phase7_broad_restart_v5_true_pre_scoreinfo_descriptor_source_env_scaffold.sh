#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_env_scaffold.md"
DESIGN="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design.md"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$DESIGN" "$MAKEFILE" <<'PY'
from pathlib import Path
import sys

doc = Path(sys.argv[1])
design = Path(sys.argv[2])
makefile = Path(sys.argv[3])
for path in [doc, design, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
design_flat = " ".join(design.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_env_scaffold = fail_closed_no_source",
    "required_runtime_env = FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_requested = 1",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_active = 0",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo = 0",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced = 0",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_attempts = 0",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_cpu_align_authority = 1",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_endpoint_cigar_traceback_output_authority = 0",
    "phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass = 0",
    "phase7_broad_restart_v5_gate_v5_1_pass = 0",
    "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate = runtime_smoke_true_pre_scoreinfo_descriptor_source_first1",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing env scaffold phrase: {phrase}")

for phrase in [
    "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design = defined",
    "Do not use CPU aligner.preAlign() or any CPU legacy scoreInfo producer as the descriptor source.",
]:
    if phrase not in design_flat:
        raise SystemExit(f"missing design predecessor phrase: {phrase}")

for target in [
    "check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-env:",
    "check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-env-runtime-smoke:",
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-env-scaffold:",
]:
    if target not in makefile_text:
        raise SystemExit(f"missing Makefile target: {target}")

print("phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_env_scaffold=fail_closed_no_source")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_requested=1")
print("phase7_v5_true_pre_scoreinfo_descriptor_source_active=0")
print("phase7_broad_restart_v5_gate_v5_1_pass=0")
print("phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate=runtime_smoke_true_pre_scoreinfo_descriptor_source_first1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
