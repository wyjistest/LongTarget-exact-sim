#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FASTSIM="$ROOT/fasim/fastsim.h"
STATS="$ROOT/fasim/gasal2_align_bridge.h"
RUNTIME="$ROOT/fasim/Fasim-LongTarget.cpp"
MAKEFILE="$ROOT/Makefile"
SMOKE="$ROOT/scripts/check_fasim_gasal2_cpu_authority_candidate_coverage_runtime_smoke.sh"

python3 - "$FASTSIM" "$STATS" "$RUNTIME" "$MAKEFILE" "$SMOKE" <<'PY'
import re
import sys
from pathlib import Path

fastsim = Path(sys.argv[1]).read_text(encoding="utf-8")
stats = Path(sys.argv[2]).read_text(encoding="utf-8")
runtime = Path(sys.argv[3]).read_text(encoding="utf-8")
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")
smoke = Path(sys.argv[5]).read_text(encoding="utf-8")

required_fastsim = [
    "FASIM_GASAL2_CPU_AUTHORITY_CANDIDATE_COVERAGE_SHADOW",
    "fasim_gasal2_cpu_authority_candidate_coverage_shadow_runtime",
]
for needle in required_fastsim:
    if needle not in fastsim:
        raise SystemExit(f"missing fastsim coverage env marker: {needle}")

required_stats = [
    "score_prepass_state_machine_shadow_candidate_coverage_requested",
    "score_prepass_state_machine_shadow_candidate_coverage_active",
    "score_prepass_state_machine_shadow_candidate_coverage_scoreinfos",
    "score_prepass_state_machine_shadow_candidate_coverage_attempts",
    "score_prepass_state_machine_shadow_candidate_coverage_candidate_attempts",
    "score_prepass_state_machine_shadow_candidate_coverage_selected",
    "score_prepass_state_machine_shadow_candidate_coverage_covered",
    "score_prepass_state_machine_shadow_candidate_coverage_false_negative_scoreinfos",
    "score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_task",
    "score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_scoreinfo",
    "score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_reason",
    "score_prepass_state_machine_shadow_candidate_coverage_cpu_align_attempts",
    "score_prepass_state_machine_shadow_candidate_coverage_cpu_align_seconds",
]
for needle in required_stats:
    if needle not in stats:
        raise SystemExit(f"missing stats coverage field: {needle}")

required_runtime = [
    "scorePrepassStateMachineCandidateCoverageRequested",
    "stateMachineLegacySelectedAttemptCovered",
    "coverageCurrentScoreInfo",
    "flushCoverageScoreInfo",
    "score_prepass_state_machine_shadow_candidate_coverage_requested",
    "score_prepass_state_machine_shadow_candidate_coverage_attempts",
    "score_prepass_state_machine_shadow_candidate_coverage_candidate_attempts",
    "score_prepass_state_machine_shadow_candidate_coverage_covered",
    "score_prepass_state_machine_shadow_candidate_coverage_false_negative_scoreinfos",
    "score_prepass_state_machine_shadow_candidate_coverage_cpu_align_attempts",
    "score_prepass_state_machine_shadow_candidate_coverage_cpu_align_seconds",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_requested",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_covered",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_false_negative_scoreinfos",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_cpu_align_attempts",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_cpu_align_seconds",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_candidate_align_attempts",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_reference_align_attempts",
]
for needle in required_runtime:
    if needle not in runtime:
        raise SystemExit(f"missing runtime coverage marker: {needle}")

target = re.search(
    r"^check-fasim-gasal2-cpu-authority-candidate-coverage-env:\n"
    r"\tbash \./scripts/check_fasim_gasal2_cpu_authority_candidate_coverage_env\.sh$",
    makefile,
    re.M,
)
if not target:
    raise SystemExit("missing Makefile coverage env target")

runtime_target = re.search(
    r"^check-fasim-gasal2-cpu-authority-candidate-coverage-runtime-smoke:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/check_fasim_gasal2_cpu_authority_candidate_coverage_runtime_smoke\.sh$",
    makefile,
    re.M,
)
if not runtime_target:
    raise SystemExit("missing Makefile coverage runtime smoke target")

if "check-fasim-gasal2-cpu-authority-candidate-coverage-env" not in makefile:
    raise SystemExit("coverage env target missing from Makefile text")
if "check-fasim-gasal2-cpu-authority-candidate-coverage-runtime-smoke" not in makefile:
    raise SystemExit("coverage runtime smoke target missing from Makefile text")

required_smoke = [
    "FASIM_GASAL2_CPU_AUTHORITY_CANDIDATE_COVERAGE_SHADOW=1",
    "covered + false_negative != selected",
    "candidate_coverage_attempts",
    "candidate_coverage_cpu_align_attempts",
    "candidate_coverage_false_negative_scoreinfos",
    "candidate_coverage_first_false_negative_reason",
]
for needle in required_smoke:
    if needle not in smoke:
        raise SystemExit(f"missing runtime smoke marker: {needle}")

print("ok")
PY
