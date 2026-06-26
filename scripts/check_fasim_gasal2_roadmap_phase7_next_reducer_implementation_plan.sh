#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAN="$ROOT/docs/superpowers/plans/2026-06-12-fasim-gasal2-phase7-next-reducer.md"
DESIGN="$ROOT/docs/fasim_gasal2_phase7_next_reducer_design.md"

for path in "$PLAN" "$DESIGN"; do
  if [[ ! -s "$path" ]]; then
    echo "missing Phase 7 next reducer plan dependency: $path" >&2
    exit 1
  fi
done

python3 - "$PLAN" "$DESIGN" <<'PY'
from pathlib import Path
import sys

plan = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
design = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())

required_plan = [
    "Fasim GASAL2 Phase 7 Next Reducer Implementation Plan",
    "REQUIRED SUB-SKILL",
    "Prototype a default-off Phase 7 task-local / scoreInfo-local reducer",
    "CPU `aligner.Align()` as score, endpoint, CIGAR, output, and digest authority",
    "FASIM_GASAL2_PHASE7_NEXT_REDUCER_SHADOW",
    "fasim_gasal2_phase7_next_reducer_shadow_runtime",
    "phase7_next_reducer_requested",
    "phase7_next_reducer_candidate_align_attempts",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_requested=1",
    "groups attempts by task and scoreInfo",
    "preserves legacy attempt order",
    "preserves scoreInfo-local single-emission state",
    "CPU-aligns only reduced candidates",
    "false_negative_scoreinfos > 0",
    "candidate_align_attempts >= reference_align_attempts",
    "contract = broad_replacement",
    "scoreinfo_reduced = true",
    "align_side_reduced = true",
    "must_not_call_update_goal_complete=1",
    "broad_objective_status=complete",
]
missing = [needle for needle in required_plan if needle not in plan]
if missing:
    raise SystemExit("implementation plan missing phrases: " + ", ".join(missing))

required_design = [
    "task-local frontier reducer",
    "scoreInfo-local state preservation",
    "candidate_align_attempts < reference_align_attempts",
    "NEAT1 first64 remains the broad gate",
]
missing_design = [needle for needle in required_design if needle not in design]
if missing_design:
    raise SystemExit("design doc missing phrases: " + ", ".join(missing_design))

print("phase7_next_reducer_implementation_plan_gate=defined")
print("plan_path=docs/superpowers/plans/2026-06-12-fasim-gasal2-phase7-next-reducer.md")
print("requires_default_off_shadow=1")
print("requires_cpu_align_authority=1")
print("requires_task_local_frontier=1")
print("requires_scoreinfo_local_state=1")
print("requires_align_attempt_reduction=1")
print("requires_broad_matrix_evidence_before_completion=1")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
