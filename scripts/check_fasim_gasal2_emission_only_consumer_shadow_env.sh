#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$ROOT" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
fastsim = (root / "fasim/fastsim.h").read_text(encoding="utf-8")
bridge = (root / "fasim/gasal2_align_bridge.h").read_text(encoding="utf-8")
stub = (root / "fasim/gasal2_align_bridge_stub.cpp").read_text(encoding="utf-8")
runtime = (root / "fasim/gasal2_align_bridge.cpp").read_text(encoding="utf-8")
makefile = (root / "Makefile").read_text(encoding="utf-8")

needles = [
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW",
    "fasim_gasal2_emission_only_consumer_shadow_enabled_runtime",
    "fasim_shadow_emission_only_consumer_from_scoreinfo",
]
for needle in needles:
    if needle not in fastsim:
        raise SystemExit(f"fastsim.h missing {needle}")

fields = [
    "emission_only_consumer_shadow_requested",
    "emission_only_consumer_shadow_active",
    "emission_only_consumer_shadow_decision",
    "emission_only_consumer_shadow_tasks",
    "emission_only_consumer_shadow_scoreinfos",
    "emission_only_consumer_shadow_scored_attempts",
    "emission_only_consumer_shadow_threshold_emits",
    "emission_only_consumer_shadow_terminal_emits",
    "emission_only_consumer_shadow_last_emits",
    "emission_only_consumer_shadow_empty_emits",
    "emission_only_consumer_shadow_cpu_align_attempts",
    "emission_only_consumer_shadow_realpath_reference_align_attempts",
    "emission_only_consumer_shadow_align_attempt_reduction",
    "emission_only_consumer_shadow_score_seconds",
    "emission_only_consumer_shadow_select_seconds",
    "emission_only_consumer_shadow_cpu_align_seconds",
    "emission_only_consumer_shadow_convert_seconds",
    "emission_only_consumer_shadow_total_seconds",
    "emission_only_consumer_shadow_triplex_mismatches",
    "emission_only_consumer_shadow_missing_triplexes",
    "emission_only_consumer_shadow_extra_triplexes",
    "emission_only_consumer_shadow_first_mismatch",
    "emission_only_consumer_shadow_fallbacks",
    "emission_only_consumer_shadow_digest_match",
    "emission_only_consumer_shadow_full_rows_equal",
]
for field in fields:
    if field not in bridge:
        raise SystemExit(f"bridge header missing {field}")
    if f"benchmark.fasim_gasal2_{field}" not in stub:
        raise SystemExit(f"stub missing benchmark for {field}")
    if f"benchmark.fasim_gasal2_{field}" not in runtime:
        raise SystemExit(f"runtime missing benchmark for {field}")

for symbol in (
    "FasimGasal2ScoreOnlyAlignment",
    "fasim_gasal2_score_attempts",
    "fasim_gasal2_record_emission_only_consumer_shadow_request",
    "fasim_gasal2_record_emission_only_consumer_shadow_result",
    "fasim_gasal2_record_emission_only_consumer_shadow_comparison",
):
    if symbol not in bridge:
        raise SystemExit(f"bridge header missing {symbol}")
    if symbol not in stub:
        raise SystemExit(f"stub missing {symbol}")
    if symbol not in runtime:
        raise SystemExit(f"runtime missing {symbol}")

if "check-fasim-gasal2-emission-only-consumer-shadow-env:" not in makefile:
    raise SystemExit("Makefile missing env target")

print("ok")
PY
