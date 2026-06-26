#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAN="$ROOT/docs/superpowers/plans/2026-06-13-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer.md"
DESIGN="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_design.md"
MAKEFILE="$ROOT/Makefile"

python3 - "$PLAN" "$DESIGN" "$MAKEFILE" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

plan = Path(sys.argv[1])
design = Path(sys.argv[2])
makefile = Path(sys.argv[3])
for path in [plan, design, makefile]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

plan_text = plan.read_text(encoding="utf-8")
flat = " ".join(plan_text.split())
design_flat = " ".join(design.read_text(encoding="utf-8").split())
makefile_text = makefile.read_text(encoding="utf-8")

required = [
    "# Fasim GASAL2 Phase 7 v5 Fused ScoreInfo Consumer Implementation Plan",
    "REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development",
    "**Goal:** Implement the first v5 fused scoreInfo consumer runtime gates without granting GPU endpoint/CIGAR/traceback/output authority.",
    "**Architecture:** Add a default-off v5 runtime path that reuses the existing legacy-byte scoreInfo GPU source and all-attempt CPU-authority replay boundaries, but records compact candidate descriptor contract telemetry instead of exposing the full scoreInfo row stream as the promoted interface.",
    "FASIM_GASAL2_PHASE7_V5_FUSED_SCOREINFO_CONSUMER=1",
    "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_requested",
    "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_active",
    "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_attempts",
    "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_descriptor_false_negatives",
    "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority=0",
    "Task 1: Env, Stats, And Default-Off Telemetry",
    "Task 2: Descriptor Contract Runtime Smoke",
    "Task 3: CPU-Authority Replay First1 Gate",
    "Task 4: Roadmap Checkpoint And Current-State Wiring",
    "Task 5: First64 Broad Gate Characterization",
    "Do not materialize the full legacy scoreInfo row stream as a host-visible promoted interface.",
    "CPU aligner.Align() remains the only endpoint, CIGAR, traceback, output, and digest authority.",
    "full row-set/digest equality = required",
    "candidate_wall_seconds < baseline_wall_seconds = required before broad completion",
    "no broad_replacement workload-matrix row before Gate v5.3 passes",
    "make check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-env",
    "make check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-runtime-smoke",
    "make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-implementation-plan",
]
for phrase in required:
    if phrase not in flat:
        raise SystemExit(f"missing required v5 implementation-plan phrase: {phrase}")

for stale in [
    "TODO",
    "TBD",
    "GPU endpoint authority",
    "GPU CIGAR authority",
    "GPU traceback authority",
]:
    if stale in flat:
        raise SystemExit(f"v5 implementation plan contains forbidden placeholder/stale phrase: {stale}")

for phrase in [
    "phase7_broad_restart_v5_fused_scoreinfo_consumer_design = defined",
    "phase7_broad_restart_v5_next_gate = fused_scoreinfo_consumer_descriptor_contract_first1",
]:
    if phrase not in design_flat:
        raise SystemExit(f"design doc missing required predecessor phrase: {phrase}")

target = "check-fasim-gasal2-roadmap-phase7-broad-restart-v5-implementation-plan:"
if target not in makefile_text:
    raise SystemExit(f"missing Makefile target: {target}")

aggregate = "check-fasim-gasal2-roadmap-current-state:"
aggregate_index = makefile_text.find(aggregate)
if aggregate_index < 0:
    raise SystemExit("missing Makefile roadmap current-state target")
aggregate_line = makefile_text[aggregate_index:].splitlines()[0]
if target[:-1] not in aggregate_line:
    raise SystemExit("roadmap current-state target missing v5 implementation-plan dependency")

print("phase7_broad_restart_v5_implementation_plan=defined")
print("phase7_broad_restart_v5_runtime_first_gate=fused_scoreinfo_consumer_descriptor_contract_first1")
print("phase7_broad_restart_v5_may_claim_completion=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
