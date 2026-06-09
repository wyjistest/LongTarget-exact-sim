#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HEADER="$ROOT/cuda/prealign_cuda.h"
CUDA="$ROOT/cuda/prealign_cuda.cu"
STUB="$ROOT/cuda/prealign_cuda_stub.cpp"
FASIM="$ROOT/fasim/Fasim-LongTarget.cpp"
MAKEFILE="$ROOT/Makefile"

for path in "$HEADER" "$CUDA" "$STUB" "$FASIM" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing fused minScore prototype dependency: $path" >&2
    exit 1
  fi
done

python3 - "$HEADER" "$CUDA" "$STUB" "$FASIM" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

header = Path(sys.argv[1]).read_text(encoding="utf-8")
cuda = Path(sys.argv[2]).read_text(encoding="utf-8")
stub = Path(sys.argv[3]).read_text(encoding="utf-8")
fasim = Path(sys.argv[4]).read_text(encoding="utf-8")
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

api = "prealign_cuda_find_streaming_scoreinfo_batch_pruned_fused_minscore"
for name, text in (("header", header), ("cuda", cuda), ("stub", stub)):
    if api not in text:
        raise SystemExit(f"{name} missing fused minScore CUDA API: {api}")

required_cuda = [
    "prealign_cuda_reduce_column_max_scores_kernel",
    "prealign_cuda_scores_to_min_scores_kernel",
    "prealign_cuda_column_scoreinfo_pruned_compact_kernel",
    "outScores",
    "outMinScores",
]
for phrase in required_cuda:
    if phrase not in cuda:
        raise SystemExit(f"cuda implementation missing fused phrase: {phrase}")

required_fasim = [
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FUSED_MINSCORE_SHADOW",
    "fasim_long_query_streaming_scoreinfo_fused_minscore_runtime",
    "fused_minscore_requested",
    "fused_minscore_active",
    "fused_minscore_used",
    "fused_minscore_fallbacks",
    "fused_minscore_score_mismatches",
    "fused_minscore_min_score_mismatches",
    "fused_minscore_kernel_seconds",
    "fused_minscore_total_seconds",
    "fused_minscore_error",
    api,
]
for phrase in required_fasim:
    if phrase not in fasim:
        raise SystemExit(f"Fasim missing fused minScore prototype phrase: {phrase}")

required_metrics = [
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_requested=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_active=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_used=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_fallbacks=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_score_mismatches=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_min_score_mismatches=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_kernel_seconds=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_total_seconds=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_error=",
]
for metric in required_metrics:
    if metric not in fasim:
        raise SystemExit(f"Fasim missing fused telemetry metric: {metric}")

target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-fused-minscore-prototype:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_fused_minscore_prototype\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing fused minScore prototype target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-long-query-streaming-scoreinfo-fused-minscore-prototype" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing fused minScore prototype dependency")

phony_targets = []
lines = makefile.splitlines()
for index, line in enumerate(lines):
    if not line.startswith(".PHONY:"):
        continue
    text = line[len(".PHONY:"):]
    cursor = index
    while text.rstrip().endswith("\\") and cursor + 1 < len(lines):
        text = text.rstrip()[:-1] + " " + lines[cursor + 1]
        cursor += 1
    phony_targets.extend(text.split())
if "check-fasim-long-query-streaming-scoreinfo-fused-minscore-prototype" not in phony_targets:
    raise SystemExit("fused minScore prototype target missing from .PHONY")
PY

echo "ok"
