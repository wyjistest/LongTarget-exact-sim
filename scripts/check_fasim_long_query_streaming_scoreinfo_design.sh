#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_long_query_streaming_scoreinfo_design.md"
DECISION_DOC="$ROOT/docs/fasim_gasal2_long_query_next_architecture_decision.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$DECISION_DOC" "$CURRENT_STATE_DOC" "$FULL_GOAL_DOC" "$COMPLETION_GAP_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing long-query streaming scoreInfo design dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$DECISION_DOC" "$CURRENT_STATE_DOC" "$FULL_GOAL_DOC" "$COMPLETION_GAP_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
decision = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[6]).read_text(encoding="utf-8")

required_doc = [
    "Fasim Long-Query Streaming ScoreInfo Design",
    "design checkpoint only",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1",
    "CPU fallback remains authority",
    "no output authority",
    "no endpoint authority",
    "no CIGAR authority",
    "no traceback authority",
    "not exact-tile union",
    "not shared-memory opt-in",
    "lower-shared-memory DP layout",
    "stream query stripes",
    "carry H/E/F boundary state",
    "emit scoreInfo candidates",
    "compare against CPU preAlign scoreInfo",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1",
    "Legacy-Byte Shadow Checkpoint",
    "gpu_scoreinfo_groups = 31272",
    "cpu_scoreinfo_groups = 31272",
    "scoreinfo_mismatches = 0",
    "candidate_missing = 0",
    "candidate_extra = 0",
    "SSE2 Lazy-F signed byte compare",
    "correctness-clean but performance no-go",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1",
    "legacy_byte_shared = 1",
    "kernel ~= 3.61s",
    "minscore seconds:",
    "calc_score_once() threshold recomputation",
    "minscore cache hits/misses:",
    "reused a StreamTask minScore",
    "gpu_call seconds:",
    "CUDA scoreInfo call wall time",
    "validation seconds:",
    "CPU preAlign authority replay",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_seconds",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_cache_hits",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_cache_misses",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_validation_seconds",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1",
    "gpu_minscore_requested = 1",
    "gpu_minscore_active = 1",
    "gpu_minscore_used = 1824",
    "gpu_minscore_fallbacks = 0",
    "gpu_minscore_score_mismatches = 0",
    "gpu_minscore_min_score_mismatches = 0",
    "gpu_minscore_error = none",
    "lower-shared-memory global-state legacy max-score kernel",
    "skip CPU minScore authority on the hot path",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_requested",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_active",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_hot",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1",
    "gpu_minscore_hot = 1",
    "gpu_minscore_used = tasks",
    "minscore_seconds <= 0.05",
    "validation_minscore_seconds > 0",
    "MALAT1 Hot-Path Characterization",
    "record_limit tasks scoreInfo GPU hot total CPU preAlign speedup",
    "64 18096 clean 45.5043s 50.3037s 1.105471x",
    "scoreInfo correctness stays clean through first64",
    "not production-ready",
    "make characterize-fasim-long-query-streaming-scoreinfo-hot",
    "Validation-First Real-Path Prototype",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE=1",
    "CPU fastSIM internal preAlign scoreInfo",
    "CPU-validated GPU streaming scoreInfo",
    "CPU extend / traceback / triplex conversion",
    "realpath_requested = 1",
    "realpath_used = 1824",
    "realpath_fallbacks = 0",
    "realpath_digest_authority = cpu_validated",
    "narrow scoreInfo/preAlign replacement path exists",
    "real-path prototype characterization",
    "realpath_used fallback scoreInfo GPU total CPU preAlign cpu/GPU",
    "64 18096 18096 0 clean 45.4425s 50.2407s 1.105588x",
    "make characterize-fasim-long-query-streaming-scoreinfo-realpath",
    "External-Digest-Gated Trust Prototype",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST=1",
    "realpath_trust = 1",
    "realpath_digest_authority = external_digest_gate",
    "cpu_scoreinfo_groups = 0",
    "cpu_prealign_seconds = 0",
    "compare_seconds = 0",
    "trust characterization keeps that external-digest-gated contract clean through full MALAT1",
    "64 18096 18096 0 319280 0 0s 45.1879s",
    "128 40128 40128 0 715473 0 0s 95.0452s",
    "256 80640 80640 0 1434844 0 0s 189.973s",
    "670 200400 200400 0 3561123 0 0s 486.763s",
    "digest = 88bb4e98f43c9a48affa082a7e97e881796f161aa4beda02a25dd6a8f7a1891f",
    "baseline Running time = 2631.57s",
    "candidate Running time = 2532.48s",
    "candidate/baseline speedup = 1.039128x",
    "make check-fasim-long-query-streaming-scoreinfo-realpath-trust",
    "make characterize-fasim-long-query-streaming-scoreinfo-realpath-trust",
    "make characterize-fasim-long-query-streaming-scoreinfo-malat1-full-trust",
    "not use GPU endpoint, CIGAR, traceback, or GASAL2 long-query traceback",
    "NEAT1 Global-State Boundary",
    "NEAT1 first4 with FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1",
    "query_len = 22767",
    "decision = streaming_scoreinfo_shadow_launch_failed",
    "record_limit tasks scoreInfo GPU hot total CPU preAlign speedup",
    "16 768 clean 12.5232s 3.52635s 0.281585x",
    "legacy_byte_shared = 0",
    "NEAT1 is not a correctness blocker",
    "performance no-go",
    "NEAT1 trust correctness is clean through first64",
    "16 768 768 0 13492 0 0s 12.4996s",
    "32 1536 1536 0 25960 0 0s 25.2269s",
    "64 3072 3072 0 52994 0 0s 50.0708s",
    "NEAT1 first32:",
    "digest = 7584d3531efc14c140f4018ac5b48dc82f1b18412b109e6a0ca376316a7ccb08",
    "baseline Running time = 42.8368s",
    "candidate Running time = 61.0602s",
    "candidate/baseline speedup = 0.701840x",
    "NEAT1 first64:",
    "digest = 5070d390bdffe9d47c4790193a798bba256d6ec81fc8cef3682a7036f403b01f",
    "baseline Running time = 87.1285s",
    "candidate Running time = 123.041s",
    "candidate/baseline speedup = 0.708143x",
    "make characterize-fasim-long-query-streaming-scoreinfo-neat1-trust",
    "make characterize-fasim-long-query-streaming-scoreinfo-neat1-first64-trust",
    "GPU total < CPU preAlign",
    "decision = streaming_scoreinfo_design_ready",
    "first_mismatch:",
    "cpu scoreInfo = 228@465",
    "gpu scoreInfo = 228@463",
    "scalar SW",
    "legacy-byte compatibility",
    "make check-fasim-long-query-streaming-scoreinfo-design",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("streaming scoreInfo design doc missing phrases: " + ", ".join(missing))

for forbidden in (
    "TBD",
    "TODO",
    "implement later",
    "fill in details",
    "use GPU output",
    "real opt-in",
):
    if forbidden in doc:
        raise SystemExit(f"streaming scoreInfo design doc contains forbidden phrase: {forbidden}")

for name, text in (
    ("decision", decision),
    ("current-state", current_state),
    ("full-goal", full_goal),
    ("completion-gap", completion_gap),
):
    for phrase in (
        "make check-fasim-long-query-streaming-scoreinfo-design",
        "lower-shared-memory streaming scoreInfo design",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing streaming design phrase: {phrase}")

target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-design:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_design\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-long-query-streaming-scoreinfo-design target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-long-query-streaming-scoreinfo-design" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing streaming scoreInfo design dependency")
if "check-fasim-long-query-streaming-scoreinfo-shadow-mismatch-detail" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing streaming scoreInfo mismatch-detail dependency")
if "check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing streaming scoreInfo legacy-byte dependency")
if "check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte-shared" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing streaming scoreInfo legacy-byte shared dependency")
if "check-fasim-long-query-streaming-scoreinfo-shadow-gpu-minscore" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing streaming scoreInfo GPU minScore dependency")
if "check-fasim-long-query-streaming-scoreinfo-shadow-gpu-minscore-hot" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing streaming scoreInfo GPU minScore hot dependency")
if "check-fasim-long-query-streaming-scoreinfo-realpath-prototype" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing streaming scoreInfo realpath prototype dependency")
if "check-fasim-long-query-streaming-scoreinfo-realpath-trust" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing streaming scoreInfo realpath trust dependency")
if "characterize-fasim-long-query-streaming-scoreinfo-hot:" not in makefile:
    raise SystemExit("Makefile missing hot-path characterization target")
if "characterize-fasim-long-query-streaming-scoreinfo-realpath:" not in makefile:
    raise SystemExit("Makefile missing real-path characterization target")
if "characterize-fasim-long-query-streaming-scoreinfo-realpath-trust:" not in makefile:
    raise SystemExit("Makefile missing realpath trust characterization target")
if "characterize-fasim-long-query-streaming-scoreinfo-malat1-full-trust:" not in makefile:
    raise SystemExit("Makefile missing full MALAT1 realpath trust characterization target")
if "characterize-fasim-long-query-streaming-scoreinfo-neat1-trust:" not in makefile:
    raise SystemExit("Makefile missing NEAT1 trust characterization target")
if "characterize-fasim-long-query-streaming-scoreinfo-neat1-first64-trust:" not in makefile:
    raise SystemExit("Makefile missing NEAT1 first64 trust characterization target")
if "check-fasim-long-query-streaming-scoreinfo-realpath-trust:" not in makefile:
    raise SystemExit("Makefile missing realpath trust target")
PY

echo "ok"
