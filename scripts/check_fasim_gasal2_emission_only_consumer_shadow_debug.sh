#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FASTSIM="$ROOT/fasim/fastsim.h"
MAKEFILE="$ROOT/Makefile"

python3 - "$FASTSIM" "$MAKEFILE" <<'PY'
import sys
from pathlib import Path

fastsim = Path(sys.argv[1])
makefile = Path(sys.argv[2])

text = fastsim.read_text(encoding="utf-8")
make = makefile.read_text(encoding="utf-8")

required = [
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_DEBUG",
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_DEBUG_LIMIT",
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_DEBUG_TASK",
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_DEBUG_SCOREINFO",
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_NO_GPU_TERMINAL",
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW_VERIFY_TERMINAL",
    "fasim_gasal2_emission_only_consumer_shadow_debug_runtime",
    "fasim_gasal2_emission_only_consumer_shadow_debug_task_runtime",
    "fasim_gasal2_emission_only_consumer_shadow_debug_scoreinfo_runtime",
    "fasim_gasal2_emission_only_consumer_shadow_no_gpu_terminal_runtime",
    "fasim_gasal2_emission_only_consumer_shadow_verify_terminal_runtime",
    "const bool noGpuTerminal",
    "const bool verifyGpuTerminal",
    "verified_terminal",
    "!noGpuTerminal",
    "score.ref_end == attempt.start + attempt.cutlength - 1",
    "FasimEmissionOnlyDebugDecision",
    "debug.fasim_gasal2_emission_only_consumer_shadow",
    "debug.fasim_gasal2_emission_only_consumer_shadow_attempt",
    "legacy_emit_reason",
    "shadow_emit_reason",
    "legacy_align_score",
    "shadow_score",
    "scoreinfo_index",
    "task_key",
]
for needle in required:
    if needle not in text:
        raise SystemExit(f"missing fastsim debug marker: {needle}")

if "check-fasim-gasal2-emission-only-consumer-shadow-debug:" not in make:
    raise SystemExit("missing Makefile debug target")
if "bash ./scripts/check_fasim_gasal2_emission_only_consumer_shadow_debug.sh" not in make:
    raise SystemExit("missing Makefile debug recipe")

print("ok")
PY
