#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export.md"

python3 - "$DOC" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
if not doc.exists():
    raise SystemExit(f"missing required file: {doc}")

text = doc.read_text(encoding="utf-8")
flat = " ".join(text.split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 Pre-D2H Proof Search First1 Export",
    "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export = pass",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_status = first1_export_pass",
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion = 0",
    "runtime_default = off",
    "runtime_reduction_enabled = 0",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
    "FASIM_GASAL2_PHASE7_POST_V5_3_PRE_D2H_PROOF_SEARCH=1",
    "bash scripts/check_fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_runtime_smoke.sh",
    "requested = 1",
    "active = 1",
    "source_is_pre_scoreinfo = 1",
    "source_is_legacy_byte_cuda = 1",
    "cpu_align_authority = 1",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "gpu_output_authority = 0",
    "proof_search_rows = 2872",
    "task_count = 48",
    "scoreinfo_count = 718",
    "attempt_count = 2872",
    "label_source_cpu_authority_external_output = 1",
    "gate_first1_export_pass = 1",
    "external_digest_match = 1",
    "external_full_rows_equal = 1",
    "current_execution_gate = pre_d2h_output_inert_proof_acceptance_first1",
    "current_next_pr = fasim_audit_pre_d2h_output_inert_proof_search_first1",
]

missing = [phrase for phrase in required if phrase not in text and phrase not in flat]
if missing:
    raise SystemExit("missing first1 export phrase(s):\n" + "\n".join(missing))

for forbidden in [
    "phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion = 1",
    "runtime_reduction_enabled = 1",
    "gpu_endpoint_cigar_traceback_output_authority = 1",
    "gpu_output_authority = 1",
    "GPU digest authority = 1",
    "broad_replacement workload matrix promotion = allowed",
]:
    if forbidden in text:
        raise SystemExit(f"first1 export checkpoint contains forbidden phrase: {forbidden}")

print("phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export=pass")
print("phase7_post_v5_3_pre_d2h_output_inert_proof_search_status=first1_export_pass")
print("phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion=0")
print("current_execution_gate=pre_d2h_output_inert_proof_acceptance_first1")
print("current_next_pr=fasim_audit_pre_d2h_output_inert_proof_search_first1")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
