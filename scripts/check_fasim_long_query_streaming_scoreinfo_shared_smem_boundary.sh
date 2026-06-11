#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CUDA="$ROOT/cuda/prealign_cuda.cu"
HEADER="$ROOT/fasim/gasal2_align_bridge.h"
FASIM="$ROOT/fasim/Fasim-LongTarget.cpp"
DOC="$ROOT/docs/fasim_long_query_streaming_scoreinfo_design.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
MAKEFILE="$ROOT/Makefile"

for path in "$CUDA" "$HEADER" "$FASIM" "$DOC" "$CURRENT_STATE_DOC" "$FULL_GOAL_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing shared-smem boundary dependency: $path" >&2
    exit 1
  fi
done

python3 - "$CUDA" "$HEADER" "$FASIM" "$DOC" "$CURRENT_STATE_DOC" "$FULL_GOAL_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

cuda = Path(sys.argv[1]).read_text(encoding="utf-8")
header = Path(sys.argv[2]).read_text(encoding="utf-8")
fasim = Path(sys.argv[3]).read_text(encoding="utf-8")
doc = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[6]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[7]).read_text(encoding="utf-8")

required_cuda = [
    "prealign_cuda_shared_smem_exceeds_optin_error",
    "legacy_byte_shared_smem_exceeds_optin_limit",
    "sharedBytes > static_cast<size_t>(optinLimit)",
    "status = cudaErrorInvalidConfiguration",
    "errorOut->empty()",
]
missing = [phrase for phrase in required_cuda if phrase not in cuda]
if missing:
    raise SystemExit("CUDA shared-smem boundary missing phrases: " + ", ".join(missing))

if cuda.count("prealign_cuda_shared_smem_exceeds_optin_error(sharedBytes,") < 2:
    raise SystemExit("expected shared-smem boundary helper use in both scoreInfo launch paths")

required_stats = [
    "legacy_byte_shared_required_smem_bytes",
    "legacy_byte_shared_default_smem_limit_bytes",
    "legacy_byte_shared_optin_smem_limit_bytes",
]
for name, text in (("stats header", header), ("Fasim telemetry", fasim)):
    missing = [phrase for phrase in required_stats if phrase not in text]
    if missing:
        raise SystemExit(f"{name} missing shared-smem telemetry: " + ", ".join(missing))

required_doc = [
    "NEAT1 shared-smem boundary",
    "legacy_byte_shared_smem_exceeds_optin_limit",
    "required_smem = 136,608",
    "optin_smem_limit = 101,376",
    "launch is rejected before CUDA returns a generic invalid argument",
    "non-shared legacy-byte path remains correctness-clean but performance no-go",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("streaming scoreInfo design doc missing shared-smem boundary phrases: " + ", ".join(missing))

for name, text in (("current-state", current_state), ("full-goal", full_goal)):
    for phrase in (
        "NEAT1 shared-smem boundary",
        "legacy_byte_shared_smem_exceeds_optin_limit",
        "required_smem = 136,608",
        "optin_smem_limit = 101,376",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing shared-smem boundary phrase: {phrase}")

target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-shared-smem-boundary:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_shared_smem_boundary\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing shared-smem boundary target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-long-query-streaming-scoreinfo-shared-smem-boundary" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing shared-smem boundary dependency")

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
if "check-fasim-long-query-streaming-scoreinfo-shared-smem-boundary" not in phony_targets:
    raise SystemExit("shared-smem boundary target missing from .PHONY")
PY

echo "ok"
