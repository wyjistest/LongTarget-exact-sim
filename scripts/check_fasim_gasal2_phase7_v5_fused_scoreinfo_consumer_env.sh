#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$ROOT/fasim/gasal2_align_bridge.h" \
  "$ROOT/fasim/gasal2_align_bridge.cpp" \
  "$ROOT/fasim/gasal2_align_bridge_stub.cpp" \
  "$ROOT/fasim/Fasim-LongTarget.cpp" \
  "$ROOT/Makefile" <<'PY'
from pathlib import Path
import sys

header, bridge, stub, main, makefile = [Path(p) for p in sys.argv[1:]]
texts = {str(p): p.read_text(encoding="utf-8") for p in [header, bridge, stub, main, makefile]}

required = {
    str(bridge): [
        "FASIM_GASAL2_PHASE7_V5_FUSED_SCOREINFO_CONSUMER",
        "fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime",
        "fasim_gasal2_record_phase7_v5_fused_scoreinfo_consumer",
    ],
    str(header): [
        "phase7_v5_fused_scoreinfo_consumer_requested",
        "phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_attempts",
        "phase7_v5_fused_scoreinfo_consumer_gate_v5_1_pass",
    ],
    str(main): [
        "fasim_print_phase7_v5_fused_scoreinfo_consumer_stats",
        "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_requested",
    ],
    str(stub): [
        "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_requested=0",
        "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority=0",
    ],
    str(makefile): [
        "check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-env:",
    ],
}

for path, phrases in required.items():
    text = texts[path]
    for phrase in phrases:
        if phrase not in text:
            raise SystemExit(f"{path} missing phrase: {phrase}")

print("phase7_v5_fused_scoreinfo_consumer_env=pass")
print("ok")
PY
