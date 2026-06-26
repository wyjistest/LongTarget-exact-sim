#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP="$ROOT/fasim/Fasim-LongTarget.cpp"
HDR="$ROOT/fasim/gasal2_align_bridge.h"
IMPL="$ROOT/fasim/gasal2_align_bridge.cpp"
STUB="$ROOT/fasim/gasal2_align_bridge_stub.cpp"
MAKEFILE="$ROOT/Makefile"

python3 - "$CPP" "$HDR" "$IMPL" "$STUB" "$MAKEFILE" <<'PY'
from pathlib import Path
import sys

cpp = Path(sys.argv[1]).read_text(encoding="utf-8")
hdr = Path(sys.argv[2]).read_text(encoding="utf-8")
impl = Path(sys.argv[3]).read_text(encoding="utf-8")
stub = Path(sys.argv[4]).read_text(encoding="utf-8")
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

required_cpp = [
    "FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES",
    "fasim_gasal2_phase7_gate_c_gpu_candidates_runtime",
]
for needle in required_cpp:
    if needle not in cpp:
        raise SystemExit(f"missing Gate C runtime marker: {needle}")

required_stats = [
    "phase7_gate_c_requested",
    "phase7_gate_c_active",
    "phase7_gate_c_tasks",
    "phase7_gate_c_oracle_scoreinfos",
    "phase7_gate_c_oracle_attempts",
    "phase7_gate_c_gpu_candidate_scoreinfos",
    "phase7_gate_c_gpu_candidate_attempts",
    "phase7_gate_c_false_negative_scoreinfos",
    "phase7_gate_c_missing_required_attempts",
    "phase7_gate_c_extra_candidate_attempts",
    "phase7_gate_c_candidate_align_attempts",
    "phase7_gate_c_gate_b_candidate_align_attempts",
    "phase7_gate_c_scoreinfo_cpu_seconds",
    "phase7_gate_c_gpu_candidate_seconds",
    "phase7_gate_c_cpu_replay_seconds",
    "phase7_gate_c_total_seconds",
    "phase7_gate_c_digest_match",
    "phase7_gate_c_full_rows_equal",
]
for needle in required_stats:
    if needle not in hdr or needle not in impl or needle not in stub:
        raise SystemExit(f"missing Gate C telemetry marker: {needle}")

if "check-fasim-gasal2-phase7-gate-c-env:" not in makefile:
    raise SystemExit("missing Makefile Gate C env target")

print("phase7_gate_c_env=pass")
print("ok")
PY
