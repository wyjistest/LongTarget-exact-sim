#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_long_query_safe_consumer_summary_design.md"
NO_GO="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_host_assisted_consumer_feasibility_no_go.md"

python3 - "$DOC" "$NO_GO" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

doc = Path(sys.argv[1])
no_go = Path(sys.argv[2])
for path in [doc, no_go]:
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

flat = " ".join(doc.read_text(encoding="utf-8").split())
no_go_flat = " ".join(no_go.read_text(encoding="utf-8").split())

required = [
    "# Fasim GASAL2 Phase 7 Post-v5.3 Long-Query-Safe Consumer Summary Design",
    "phase7_post_v5_3_long_query_safe_consumer_summary_design = defined",
    "phase7_post_v5_3_long_query_safe_design_family = legacy_byte_cuda_scoreinfo_consumer_summary_without_gasal2_score_only",
    "previous_status = host_assisted_no_go_long_query_length_guard",
    "runtime_default = off",
    "query_len = 22767",
    "gasal2_max_query_len = 2812",
    "host_selected_attempts = 0",
    "candidate_align_attempts = 0",
    "digest_match = 0",
    "full_rows_equal = 0",
    "gasal2_score_only_long_query_dependency = 0",
    "host_assisted_gasal2_score_only_selector_may_continue = 0",
    "legacy-byte-compatible CUDA scoreInfo/attempt descriptor producer",
    "CUDA scoreInfo-local summary stage",
    "gpu_consumer_reduces_before_host_transfer = 1",
    "full_host_visible_descriptor_replay = 0",
    "emit a prefix boundary, not an arbitrary sparse subset",
    "CPU aligner.Align() authority = 1",
    "GPU endpoint authority = 0",
    "GPU CIGAR authority = 0",
    "GPU traceback authority = 0",
    "GPU output authority = 0",
    "GPU digest authority = 0",
    "FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1",
    "post_v5_3_gpu_consumer_summary_first1_smoke",
    "source_is_legacy_byte_cuda",
    "gpu_prefix_descriptor_attempts",
    "gpu_summary_kernel_seconds",
    "gpu_selected_attempts < v5_candidate_align_attempts",
    "gpu_prefix_descriptor_attempts < v5_candidate_align_attempts",
    "candidate_align_attempts < reference_align_attempts",
    "descriptor_false_negatives = 0",
    "missing_required_attempts = 0",
    "fallback_accounting_clean = 1",
    "phase7_post_v5_3_long_query_safe_consumer_summary_may_claim_completion = 0",
    "contract = broad_replacement",
    "phase7_post_v5_3_long_query_safe_consumer_summary_may_implement = 1",
    "next_required_gate = post_v5_3_gpu_consumer_summary_first1_smoke",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]

missing = [phrase for phrase in required if phrase not in flat]
if missing:
    raise SystemExit(
        "missing long-query-safe consumer summary design phrase(s):\n"
        + "\n".join(missing)
    )

for phrase in [
    "host-assisted consumer feasibility: no-go for NEAT1 first1 broad path",
    "benchmark.fasim_gasal2_length_guard_last_query_len = 22767",
    "benchmark.fasim_gasal2_length_guard_max_query_len = 2812",
]:
    if phrase not in no_go_flat:
        raise SystemExit(f"missing host-assisted no-go phrase: {phrase}")

for forbidden in [
    "gasal2_score_only_long_query_dependency = 1",
    "host_assisted_gasal2_score_only_selector_may_continue = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "phase7_post_v5_3_long_query_safe_consumer_summary_may_claim_completion = 1",
]:
    if forbidden in flat:
        raise SystemExit(f"long-query-safe design contains forbidden phrase: {forbidden}")

print("phase7_post_v5_3_long_query_safe_consumer_summary_design=defined")
print("phase7_post_v5_3_long_query_safe_design_family=legacy_byte_cuda_scoreinfo_consumer_summary_without_gasal2_score_only")
print("phase7_post_v5_3_long_query_safe_consumer_summary_may_implement=1")
print("phase7_post_v5_3_long_query_safe_consumer_summary_may_claim_completion=0")
print("next_required_gate=post_v5_3_gpu_consumer_summary_first1_smoke")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
