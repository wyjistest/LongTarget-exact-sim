#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_long_query_streaming_scoreinfo_fused_minscore_design.md"
STREAMING_DOC="$ROOT/docs/fasim_long_query_streaming_scoreinfo_design.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$STREAMING_DOC" "$CURRENT_STATE_DOC" "$FULL_GOAL_DOC" "$COMPLETION_GAP_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing fused minScore design dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$STREAMING_DOC" "$CURRENT_STATE_DOC" "$FULL_GOAL_DOC" "$COMPLETION_GAP_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
streaming = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[6]).read_text(encoding="utf-8")

required_doc = [
    "Fasim Long-Query Streaming ScoreInfo Fused MinScore Design",
    "default-off prototype boundary",
    "runs two long-query DP passes",
    "prealign_cuda_find_max_scores_global_state_batch()",
    "prealign_cuda_find_streaming_scoreinfo_batch_pruned()",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FUSED_MINSCORE_SHADOW=1",
    "MALAT1 first8 boundary result:",
    "fused_minscore_score_mismatches = 97",
    "fused_minscore_min_score_mismatches = 97",
    "scoreinfo_mismatches = 92",
    "decision = streaming_scoreinfo_shadow_mismatch",
    "hard no-go for promoting the current fused prototype",
    "legacy calc-score profile/target encoding",
    "SSW byte-profile/Lazy-F scoreInfo path",
    "Run one column-max DP pass per batch",
    "Reduce column maxima to a per-task full score",
    "Derive minScore from that full score on device",
    "Compact scoreInfo candidates using the derived minScore",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_requested",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_active",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_used",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_fallbacks",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_score_mismatches",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_min_score_mismatches",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_kernel_seconds",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_total_seconds",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_error",
    "fused_minscore_active = 1",
    "fused_minscore_used = tasks",
    "fused_minscore_fallbacks = 0",
    "scoreinfo_mismatches = 0",
    "candidate_missing = 0",
    "candidate_extra = 0",
    "output digest unchanged",
    "NEAT1 first64 fused trust:",
    "candidate/baseline speedup > 1.0x",
    "GPU total < current non-fused GPU total",
    "gpu_minscore_wall_seconds ~= 16.30s",
    "gpu_call_seconds ~= 33.77s",
    "gpu_total_seconds ~= 50.07s",
    "fails before the performance gate",
    "do not promote it as a real path",
    "not promoting this prototype",
    "decision = fused_minscore_current_prototype_no_go",
    "make check-fasim-long-query-streaming-scoreinfo-fused-minscore-design",
    "make check-fasim-long-query-streaming-scoreinfo-fused-minscore-prototype",
    "make check-fasim-long-query-streaming-scoreinfo-fused-minscore-boundary",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("fused minScore design doc missing phrases: " + ", ".join(missing))

for forbidden in (
    "Current full-goal status: complete",
    "Universal replacement status: proven",
    "real opt-in",
):
    if forbidden in doc:
        raise SystemExit(f"fused minScore design doc contains forbidden phrase: {forbidden}")

for name, text in (
    ("streaming", streaming),
    ("current-state", current_state),
    ("full-goal", full_goal),
    ("completion-gap", completion_gap),
):
    for phrase in (
        "fused minScore",
        "make check-fasim-long-query-streaming-scoreinfo-fused-minscore-design",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing fused minScore phrase: {phrase}")

target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-fused-minscore-design:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_fused_minscore_design\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-long-query-streaming-scoreinfo-fused-minscore-design target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-long-query-streaming-scoreinfo-fused-minscore-design" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing fused minScore design dependency")

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
if "check-fasim-long-query-streaming-scoreinfo-fused-minscore-design" not in phony_targets:
    raise SystemExit("fused minScore design target missing from .PHONY")
PY

echo "ok"
