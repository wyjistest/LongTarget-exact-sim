#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design.md"
RUNTIME_DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke.md"
MAKEFILE="$ROOT/Makefile"

python3 - "$DOC" "$RUNTIME_DOC" "$MAKEFILE" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
runtime_doc = Path(sys.argv[2])
makefile = Path(sys.argv[3])

for path in [doc, runtime_doc, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
runtime_flat = " ".join(runtime_doc.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design = defined",
    "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_status = design_only",
    "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_may_claim_completion = 0",
    "phase7_broad_restart_v5_gate_v5_1_pass = 0",
    "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate = runtime_smoke_true_pre_scoreinfo_descriptor_source_first1",
    "Do not use CPU aligner.preAlign() or any CPU legacy scoreInfo producer as the descriptor source.",
    "Do not materialize the full legacy scoreInfo row stream as a host-visible promoted interface.",
    "GPU legacy byte scoreInfo-compatible computation",
    "fused GPU scoreInfo consumer state machine",
    "compact candidate attempt descriptors",
    "source_is_pre_scoreinfo = 1",
    "scoreinfo_prealign_reduced = 1",
    "gpu_descriptor_attempts > 0",
    "descriptor_false_negatives = 0",
    "missing_required_attempts = 0",
    "candidate attempts stay below all-column replay scale",
    "CPU aligner.Align() remains endpoint, CIGAR, traceback, output, and digest authority.",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]

for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required true pre-scoreInfo design phrase: {phrase}")

for stale in [
    "post-scoreInfo descriptor mirror may pass Gate v5.1",
    "host-visible scoreInfo rows are the promoted v5 source",
    "GPU endpoint authority",
    "GPU CIGAR authority",
    "GPU traceback authority",
    "GPU output authority",
]:
    if stale in flat:
        raise SystemExit(f"true pre-scoreInfo design contains forbidden phrase: {stale}")

for phrase in [
    "phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke = post_scoreinfo_descriptor_scaffold_no_go",
    "phase7_broad_restart_v5_runtime_scaffold_next_gate = true_pre_scoreinfo_fused_descriptor_source",
    "scoreinfo_prealign_reduced = 0",
    "gate_v5_1_pass = 0",
]:
    if phrase not in runtime_flat:
        raise SystemExit(f"missing runtime no-go predecessor phrase: {phrase}")

target = (
    "check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-"
    "scoreinfo-descriptor-source-design:"
)
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

aggregate = "check-fasim-gasal2-roadmap-current-state:"
aggregate_index = makefile_text.find(aggregate)
if aggregate_index < 0:
    raise SystemExit("missing Makefile roadmap current-state target")
aggregate_line = makefile_text[aggregate_index:].splitlines()[0]
dependency = target[:-1]
if dependency not in aggregate_line:
    raise SystemExit("roadmap current-state target missing true pre-scoreInfo design dependency")

print("phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design=defined")
print("phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_status=design_only")
print("phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_may_claim_completion=0")
print("phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate=runtime_smoke_true_pre_scoreinfo_descriptor_source_first1")
print("phase7_broad_restart_v5_gate_v5_1_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
