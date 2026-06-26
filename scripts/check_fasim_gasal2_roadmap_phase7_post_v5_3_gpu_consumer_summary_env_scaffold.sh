#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_env_scaffold.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
STEPWISE="$ROOT/docs/fasim_gasal2_goal_completion_stepwise_plan.md"

python3 - "$DOC" "$ROADMAP" "$STEPWISE" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
roadmap = Path(sys.argv[2])
stepwise = Path(sys.argv[3])

for path in [doc, roadmap, stepwise]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 GPU Consumer Summary Env Scaffold",
    "fail-closed",
    "required_runtime_env =",
    "FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY",
    "telemetry_prefix =",
    "benchmark.fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_",
    "phase7_post_v5_3_gpu_consumer_summary_env_scaffold =",
    "fail_closed_no_source",
    "phase7_post_v5_3_gpu_consumer_summary_requested = 1",
    "phase7_post_v5_3_gpu_consumer_summary_active = 0",
    "phase7_post_v5_3_gpu_consumer_summary_gpu_consumer_summary_rows = 0",
    "phase7_post_v5_3_gpu_consumer_summary_gpu_consumer_reduces_before_host_transfer = 0",
    "phase7_post_v5_3_gpu_consumer_summary_cpu_align_authority = 1",
    "phase7_post_v5_3_gpu_consumer_summary_gpu_endpoint_cigar_traceback_output_authority = 0",
    "phase7_post_v5_3_gpu_consumer_summary_gate_first1_pass = 0",
    "make check-fasim-gasal2-phase7-post-v5-3-gpu-consumer-summary-env-runtime-smoke",
    "not first1 gate pass",
    "next_required_gate =",
    "post_v5_3_gpu_consumer_summary_first1_smoke",
    "phase7_post_v5_3_gpu_consumer_summary_may_claim_completion = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]
missing = [phrase for phrase in required if phrase not in flat and phrase not in text]
if missing:
    raise SystemExit(
        "missing post-v5.3 env scaffold phrase(s):\n" + "\n".join(missing)
    )

for forbidden in [
    "phase7_post_v5_3_gpu_consumer_summary_gate_first1_pass = 1",
    "broad_objective_status = complete",
    "GPU endpoint/CIGAR/traceback/output authority = 1",
    "phase7_post_v5_3_gpu_consumer_summary_broad_replacement = 1",
]:
    if forbidden in flat:
        raise SystemExit(f"forbidden scaffold phrase present: {forbidden}")

roadmap_text = roadmap.read_text(encoding="utf-8")
stepwise_text = stepwise.read_text(encoding="utf-8")
if "docs/fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_env_scaffold.md" not in roadmap_text:
    raise SystemExit("roadmap does not mention post-v5.3 env scaffold doc")
if "post_v5_3_gpu_consumer_summary_first1_smoke" not in stepwise_text:
    raise SystemExit("stepwise plan does not keep first1 smoke as next gate")

print("phase7_post_v5_3_gpu_consumer_summary_env_scaffold=defined")
print("phase7_post_v5_3_gpu_consumer_summary_env_scaffold_status=fail_closed_no_source")
print("phase7_post_v5_3_gpu_consumer_summary_gate_first1_pass=0")
print("phase7_post_v5_3_gpu_consumer_summary_next_gate=post_v5_3_gpu_consumer_summary_first1_smoke")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
