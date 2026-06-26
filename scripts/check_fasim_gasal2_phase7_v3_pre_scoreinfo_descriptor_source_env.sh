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
    "FASIM_GASAL2_PHASE7_V3_PRE_SCOREINFO_DESCRIPTOR_SOURCE",
    "fasim_gasal2_phase7_v3_pre_scoreinfo_descriptor_source_runtime",
]
for needle in required_cpp:
    if needle not in cpp:
        raise SystemExit(f"missing v3 pre-scoreInfo descriptor-source runtime marker: {needle}")

required_stats = [
    "phase7_v3_descriptor_source_candidate_certificate_checked",
    "phase7_v3_descriptor_source_cpu_scoreinfo_reduced",
    "phase7_v3_descriptor_source_pre_scoreinfo_source",
    "phase7_v3_descriptor_source_after_cpu_scoreinfo_source",
    "fasim_gasal2_record_phase7_v3_descriptor_source",
]
for needle in required_stats:
    if needle not in hdr or needle not in impl or needle not in stub:
        raise SystemExit(f"missing v3 pre-scoreInfo descriptor-source marker: {needle}")

if "check-fasim-gasal2-phase7-v3-pre-scoreinfo-descriptor-source-env:" not in makefile:
    raise SystemExit("missing Makefile v3 pre-scoreInfo descriptor-source env target")

print("phase7_v3_pre_scoreinfo_descriptor_source_env=pass")
print("ok")
PY
