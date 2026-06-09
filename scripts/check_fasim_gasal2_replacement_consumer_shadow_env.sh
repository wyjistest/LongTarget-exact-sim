#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FASTSIM="$ROOT/fasim/fastsim.h"
FASIM_MAIN="$ROOT/fasim/Fasim-LongTarget.cpp"
REQ_DOC="$ROOT/docs/fasim_gasal2_replacement_consumer_shadow_requirements.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
MAKEFILE="$ROOT/Makefile"

for path in "$FASTSIM" "$FASIM_MAIN" "$REQ_DOC" "$CURRENT_STATE_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing replacement-consumer env dependency: $path" >&2
    exit 1
  fi
done

python3 - "$FASTSIM" "$FASIM_MAIN" "$REQ_DOC" "$CURRENT_STATE_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

fastsim = Path(sys.argv[1]).read_text(encoding="utf-8")
main = Path(sys.argv[2]).read_text(encoding="utf-8")
req_doc = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

env = "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REPLACEMENT_CONSUMER_SHADOW"

required_fastsim = [
    "fasim_long_query_streaming_scoreinfo_replacement_consumer_shadow_runtime",
    env,
    "fasim_long_query_streaming_scoreinfo_flush_segmented_extend_attempt_probe_runtime",
    "fasim_long_query_streaming_scoreinfo_flush_segmented_replay_probe_runtime",
    "fasim_long_query_streaming_scoreinfo_flush_segmented_selected_only_replay_probe_runtime",
    "fasim_long_query_streaming_scoreinfo_flush_segmented_grouped_selected_replay_probe_runtime",
    "fasim_long_query_streaming_scoreinfo_flush_full_replay_probe_runtime",
]
missing = [phrase for phrase in required_fastsim if phrase not in fastsim]
if missing:
    raise SystemExit("fastsim replacement-consumer env missing phrases: " + ", ".join(missing))

for func in (
    "fasim_long_query_streaming_scoreinfo_flush_segmented_extend_attempt_probe_runtime",
    "fasim_long_query_streaming_scoreinfo_flush_segmented_replay_probe_runtime",
    "fasim_long_query_streaming_scoreinfo_flush_segmented_selected_only_replay_probe_runtime",
    "fasim_long_query_streaming_scoreinfo_flush_segmented_grouped_selected_replay_probe_runtime",
    "fasim_long_query_streaming_scoreinfo_flush_full_replay_probe_runtime",
):
    pattern = rf"{func}\(\).*?fasim_long_query_streaming_scoreinfo_replacement_consumer_shadow_runtime\(\)"
    if not re.search(pattern, fastsim, flags=re.S):
        raise SystemExit(f"{func} does not inherit replacement-consumer shadow env")

required_main = [
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_requested=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_active=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_tasks=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_scoreinfo_groups=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_align_attempts=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_selected_attempts=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_triplex_mismatches=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_segmented_triplex_mismatches=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_selected_only_triplex_mismatches=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_grouped_selected_triplex_mismatches=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_full_triplex_mismatches=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_oracle_triplex_mismatches=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_first_mismatch=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_first_mismatch_source=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_first_mismatch_kind=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_seconds=",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_fallbacks=",
    "realpath_extend_flush_segmented_replay_probe_triplex_mismatches",
    "realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches",
    "realpath_extend_flush_full_replay_probe_triplex_mismatches",
]
missing = [phrase for phrase in required_main if phrase not in main]
if missing:
    raise SystemExit("main replacement-consumer telemetry missing phrases: " + ", ".join(missing))

for phrase in (
    env,
    "default-off umbrella",
    "replacement_consumer_shadow_requested",
    "Do not use replacement-consumer output",
):
    if phrase not in req_doc:
        raise SystemExit(f"requirements doc missing replacement-consumer env phrase: {phrase}")

for phrase in (
    "make check-fasim-gasal2-replacement-consumer-shadow-env",
    "make check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke",
    env,
):
    if phrase not in current_state:
        raise SystemExit(f"current-state doc missing replacement-consumer env phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-replacement-consumer-shadow-env:\n"
    r"\tbash \./scripts/check_fasim_gasal2_replacement_consumer_shadow_env\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing replacement-consumer shadow env target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-gasal2-replacement-consumer-shadow-env" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing replacement-consumer shadow env dependency")
if "check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing replacement-consumer shadow runtime-smoke dependency")

phony_targets = []
lines = makefile.splitlines()
index = 0
while index < len(lines):
    line = lines[index]
    if line.startswith(".PHONY:"):
        text = line.split(":", 1)[1].strip()
        while text.endswith("\\") and index + 1 < len(lines):
            text = text[:-1] + " " + lines[index + 1].strip()
            index += 1
        phony_targets.extend(text.split())
    index += 1
if not phony_targets:
    raise SystemExit("Makefile missing .PHONY block")
phony_targets = set(phony_targets)
if "check-fasim-gasal2-replacement-consumer-shadow-env" not in phony_targets:
    raise SystemExit("replacement-consumer shadow env target missing from .PHONY")
if "check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke" not in phony_targets:
    raise SystemExit("replacement-consumer shadow runtime-smoke target missing from .PHONY")
PY

echo "ok"
