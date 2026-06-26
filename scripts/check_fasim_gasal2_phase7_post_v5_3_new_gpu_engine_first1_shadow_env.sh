#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$ROOT" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

root = Path(sys.argv[1])
files = {
    "bridge_h": root / "fasim/gasal2_align_bridge.h",
    "bridge_cpp": root / "fasim/gasal2_align_bridge.cpp",
    "bridge_stub": root / "fasim/gasal2_align_bridge_stub.cpp",
    "longtarget": root / "fasim/Fasim-LongTarget.cpp",
}

for path in files.values():
    if not path.exists():
        raise SystemExit(f"missing required file: {path}")

text = "\n".join(path.read_text(encoding="utf-8") for path in files.values())

required = [
    "FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_FIRST1_SHADOW",
    "fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_runtime",
    "fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_first1_shadow_requested",
    "fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_first1_shadow",
    "fasim_print_phase7_post_v5_3_new_gpu_engine_first1_shadow_stats",
    "fasim_record_phase7_post_v5_3_new_gpu_engine_first1_shadow_requested_if_needed",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_requested",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_active",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_scoreinfo_tasks",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_candidate_groups",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_replay_attempts",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_skipped_groups",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_skipped_attempts",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_cpu_replay_attempts",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_baseline_cpu_attempts",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_certificate_producer",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_certificate_valid_before_d2h",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_final_cpu_output_membership_required_for_certificate",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_on_missing_bound",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_to_full_cpu_replay",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_certificate_false_negatives",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_required_attempts",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_scoreinfo_prealign_reduced",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_align_side_reduced",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_fallback_accounting_clean",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_cpu_align_authority",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_endpoint_cigar_traceback_output_authority",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_full_rows_equal",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_digest_match",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_missing_rows",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_extra_rows",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_triplex_mismatches",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_gate_first1_pass",
]

missing = [phrase for phrase in required if phrase not in text]
if missing:
    raise SystemExit(
        "missing new GPU engine first1 shadow runtime phrase(s):\n"
        + "\n".join(missing)
    )

for forbidden in [
    "phase7_post_v5_3_new_gpu_engine_first1_shadow_gate_first1_pass = 1",
    "phase7_post_v5_3_new_gpu_engine_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 1",
    "phase7_post_v5_3_new_gpu_engine_first1_shadow_certificate_valid_before_d2h = 1",
]:
    if forbidden in text:
        raise SystemExit(f"forbidden new-engine shadow phrase present: {forbidden}")

print("phase7_post_v5_3_new_gpu_engine_first1_shadow_env=present")
print("phase7_post_v5_3_new_gpu_engine_first1_shadow_runtime=fail_closed")
print("ok")
PY
