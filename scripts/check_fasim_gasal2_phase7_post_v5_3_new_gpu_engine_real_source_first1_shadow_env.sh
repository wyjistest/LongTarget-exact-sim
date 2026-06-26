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

text_by_file = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
text = "\n".join(text_by_file.values())

required = [
    "FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_FIRST1_SHADOW",
    "fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime",
    "fasim_gasal2_record_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_requested",
    "fasim_record_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_requested_if_needed",
    "fasim_print_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_stats",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_requested",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_active",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_fasim_runtime_certificate_source",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_fasim_runtime_work_drop_path",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime_certificate_is_synthetic",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_missing_certificate",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_fallback_to_full_cpu_replay",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scoreinfo_prealign_reduced",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_align_side_reduced",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_fallback_accounting_clean",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_cpu_align_authority",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_endpoint_cigar_traceback_output_authority",
    "benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gate_first1_pass",
]

missing = [phrase for phrase in required if phrase not in text]
if missing:
    raise SystemExit(
        "missing real-source first1 shadow runtime phrase(s):\n"
        + "\n".join(missing)
    )

for phrase in [
    "g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_requested = 1",
    "g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_active = 0",
    "g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_certificate_source = 0",
    "g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_work_drop_path = 0",
    "g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime_certificate_is_synthetic = 0",
    "g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_missing_certificate = 1",
    "g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_fallback_to_full_cpu_replay = 1",
    "g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_cpu_align_authority = 1",
    "g_stats.phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gate_first1_pass = 0",
]:
    if phrase not in text_by_file["bridge_cpp"]:
        raise SystemExit(f"bridge cpp missing fail-closed assignment: {phrase}")

if text_by_file["longtarget"].count(
    "fasim_print_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_stats"
) < 3:
    raise SystemExit("Fasim final stats paths are not wired to real-source first1 shadow stats")

for forbidden in [
    "phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gate_first1_pass = 1",
    "phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_certificate_source = 1",
    "phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_real_work_drop_path = 1",
    "phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime_certificate_is_synthetic = 1",
    "phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gpu_endpoint_cigar_traceback_output_authority = 1",
]:
    if forbidden in text:
        raise SystemExit(f"forbidden real-source first1 shadow phrase present: {forbidden}")

print("phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_env=present")
print("phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime=fail_closed_no_real_source")
print("ok")
PY
