#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_design.md"
NO_GO="$ROOT/docs/fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go.md"

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
    "# Fasim GASAL2 Phase 7 Post-v5.3 Stronger Consumer Summary Design",
    "phase7_post_v5_3_stronger_consumer_summary_design = defined",
    "phase7_post_v5_3_stronger_consumer_summary_status = design_only",
    "phase7_post_v5_3_stronger_consumer_summary_may_implement = 1",
    "phase7_post_v5_3_stronger_consumer_summary_may_claim_completion = 0",
    "previous_status = first_descriptor_per_scoreinfo_no_go",
    "implementation_shape = first_descriptor_per_scoreinfo_gpu_summary",
    "external_digest_match = 0",
    "external_full_rows_equal = 0",
    "first_descriptor_per_scoreinfo_preserves_output = 0",
    "first_descriptor_per_scoreinfo_may_continue = 0",
    "required_next_design_property = prefix_boundary_or_equivalent_replay_proof",
    "legacy-byte CUDA scoreInfo / attempt descriptor stream",
    "GPU scoreInfo-local boundary analyzer",
    "compact per-scoreInfo replay certificate",
    "selected prefix boundary, or an equivalent replay-proof boundary",
    "arbitrary sparse descriptor subset",
    "gasal2_score_only_long_query_dependency = 0",
    "source_is_legacy_byte_cuda = 1",
    "source_is_pre_scoreinfo = 1",
    "selected_prefix_end_index",
    "ordered_replay_boundary",
    "skipped_suffix_safe_reason",
    "conservative_boundary_allowed = 1",
    "prefix_boundary_may_equal_full_group = 1",
    "selected_prefix_attempts < v5_candidate_align_attempts",
    "candidate_align_attempts < reference_align_attempts",
    "FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1",
    "next_required_gate = post_v5_3_stronger_consumer_summary_first1_smoke",
    "uses_prefix_boundary_or_equivalent_replay_proof = 1",
    "arbitrary_sparse_subset = 0",
    "first_descriptor_per_scoreinfo = 0",
    "descriptor_false_negatives = 0",
    "missing_required_attempts = 0",
    "fallback_accounting_clean = 1",
    "digest_match = 1",
    "full_rows_equal = 1",
    "external_output_comparison_authority = 1",
    "cpu_align_authority = 1",
    "gpu_endpoint_cigar_traceback_output_authority = 0",
    "do_not_run_first64_until_first1_gate_pass = 1",
    "full_group_fallback_scoreinfos",
    "skipped_suffix_attempts",
    "first1_gate_pass = 1",
    "candidate_vs_baseline > 1.0",
    "the implementation selects an arbitrary sparse subset",
    "first1 output rows differ",
    "phase7_post_v5_3_stronger_consumer_summary_status = design_only",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]

missing = [phrase for phrase in required if phrase not in flat]
if missing:
    raise SystemExit(
        "missing stronger consumer summary design phrase(s):\n"
        + "\n".join(missing)
    )

for phrase in [
    "phase7_post_v5_3_gpu_consumer_summary_first_attempt_status = no_go",
    "external_digest_match = 0",
    "external_full_rows_equal = 0",
    "required_next_design_property = prefix_boundary_or_equivalent_replay_proof",
]:
    if phrase not in no_go_flat:
        raise SystemExit(f"missing first-attempt no-go phrase: {phrase}")

for forbidden in [
    "phase7_post_v5_3_stronger_consumer_summary_may_claim_completion = 1",
    "gasal2_score_only_long_query_dependency = 1",
    "GPU endpoint authority = 1",
    "GPU CIGAR authority = 1",
    "GPU traceback authority = 1",
    "GPU output authority = 1",
    "GPU digest authority = 1",
    "first_descriptor_per_scoreinfo_may_continue = 1",
]:
    if forbidden in flat:
        raise SystemExit(f"stronger design contains forbidden phrase: {forbidden}")

print("phase7_post_v5_3_stronger_consumer_summary_design=defined")
print("phase7_post_v5_3_stronger_consumer_summary_status=design_only")
print("phase7_post_v5_3_stronger_consumer_summary_may_implement=1")
print("phase7_post_v5_3_stronger_consumer_summary_may_claim_completion=0")
print("next_required_gate=post_v5_3_stronger_consumer_summary_first1_smoke")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
