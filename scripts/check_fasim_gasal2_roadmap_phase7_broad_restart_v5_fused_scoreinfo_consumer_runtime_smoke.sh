#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke.md"

python3 - "$DOC" <<'PY'
from pathlib import Path
import sys

doc = Path(sys.argv[1])
if not doc.exists():
    raise SystemExit(f"missing doc: {doc}")

text = doc.read_text(encoding="utf-8")
required = [
    "phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke = post_scoreinfo_descriptor_scaffold_no_go",
    "phase7_broad_restart_v5_gate_v5_1_pass = 0",
    "phase7_broad_restart_v5_may_claim_completion = 0",
    "phase7_broad_restart_v5_next_gate = true_pre_scoreinfo_fused_descriptor_source",
    "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_requested = 1",
    "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_active = 1",
    "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_attempts = 2872",
    "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_descriptor_false_negatives = 0",
    "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_missing_required_attempts = 0",
    "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_scoreinfo_prealign_reduced = 0",
    "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_cpu_align_authority = 1",
    "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]

for phrase in required:
    if phrase not in text:
        raise SystemExit(f"missing phrase: {phrase}")

print("phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke=post_scoreinfo_descriptor_scaffold_no_go")
print("phase7_broad_restart_v5_gate_v5_1_pass=0")
print("phase7_broad_restart_v5_may_claim_completion=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
