#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_long_query_streaming_scoreinfo_two_contract_bridge_design.md"
FUSED_DOC="$ROOT/docs/fasim_long_query_streaming_scoreinfo_fused_minscore_design.md"
STREAMING_DOC="$ROOT/docs/fasim_long_query_streaming_scoreinfo_design.md"
CURRENT_STATE_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
FULL_GOAL_DOC="$ROOT/docs/fasim_gasal2_full_goal_decision.md"
COMPLETION_GAP_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
MAKEFILE="$ROOT/Makefile"

for path in "$DOC" "$FUSED_DOC" "$STREAMING_DOC" "$CURRENT_STATE_DOC" "$FULL_GOAL_DOC" "$COMPLETION_GAP_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing two-contract bridge design dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$FUSED_DOC" "$STREAMING_DOC" "$CURRENT_STATE_DOC" "$FULL_GOAL_DOC" "$COMPLETION_GAP_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
fused = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
streaming = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
current_state = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
full_goal = " ".join(Path(sys.argv[5]).read_text(encoding="utf-8").split())
completion_gap = " ".join(Path(sys.argv[6]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[7]).read_text(encoding="utf-8")

required_doc = [
    "Fasim Long-Query Streaming ScoreInfo Two-Contract Bridge Design",
    "default-off runtime scaffold",
    "not a real opt-in",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1",
    "fused_minscore_current_prototype_no_go",
    "MALAT1 first8 fused boundary",
    "fused_minscore_score_mismatches = 97",
    "fused_minscore_min_score_mismatches = 97",
    "scoreinfo_mismatches = 92",
    "legacy calc-score contract",
    "byte-profile scoreInfo contract",
    "do not force one column-max representation",
    "stage A: legacy calc-score GPU score/minScore",
    "stage B: byte-profile streaming scoreInfo GPU compact",
    "one bounded bridge call",
    "Current Prototype Checkpoint",
    "decision = two_contract_bridge_shadow_active",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1",
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_experimental_v1",
    "decision = two_contract_bridge_trust_active",
    "two_contract_score_mismatches = 0",
    "two_contract_min_score_mismatches = 0",
    "two_contract_scoreinfo_mismatches = 0",
    "two_contract_fallbacks = 0",
    "fused_minscore_requested = 0",
    "realpath_digest_authority = external_digest_gate",
    "cpu_scoreinfo_groups = 0",
    "cpu_prealign_seconds = 0",
    "copy target buffers once per contract",
    "reuse task descriptors",
    "copy back score/minScore, scoreInfo counts, scoreInfo groups, overflow",
    "CPU output remains authority",
    "GPU endpoint remains forbidden",
    "GPU CIGAR remains forbidden",
    "GPU traceback remains forbidden",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_requested",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_active",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_used",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_fallbacks",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_score_mismatches",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_min_score_mismatches",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_scoreinfo_mismatches",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_total_seconds",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_h2d_seconds",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_kernel_seconds",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_d2h_seconds",
    "score_mismatches = 0",
    "min_score_mismatches = 0",
    "scoreinfo_mismatches = 0",
    "candidate_missing = 0",
    "candidate_extra = 0",
    "digest unchanged",
    "NEAT1 first64",
    "candidate/baseline speedup > 1.0x",
    "GPU total < current two-pass GPU total",
    "If bridge still loses to CPU, stop long-query scoreInfo GPU real path",
    "decision = two_contract_bridge_design_ready",
    "make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design",
]
missing = [phrase for phrase in required_doc if phrase not in doc]
if missing:
    raise SystemExit("two-contract bridge design doc missing phrases: " + ", ".join(missing))

for forbidden in (
    "single-pass fused is correctness-clean;",
    "GPU output remains authority",
    "real opt-in enabled",
    "GPU endpoint authority is allowed",
    "GPU CIGAR authority is allowed",
    "GPU traceback authority is allowed",
    "full goal complete;",
):
    if forbidden in doc:
        raise SystemExit(f"two-contract bridge design doc contains forbidden phrase: {forbidden}")

for name, text in (
    ("fused", fused),
    ("streaming", streaming),
    ("current-state", current_state),
    ("full-goal", full_goal),
    ("completion-gap", completion_gap),
):
    for phrase in (
        "two-contract bridge",
        "make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing two-contract bridge phrase: {phrase}")

target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_design\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing two-contract bridge design target")

shadow_target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-shadow:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_shadow\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not shadow_target:
    raise SystemExit("Makefile missing two-contract bridge shadow target")

trust_target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-trust:\n"
    r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
    r"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_trust\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not trust_target:
    raise SystemExit("Makefile missing two-contract bridge trust target")

runner_target = re.search(
    r"^check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-runner:\n"
    r"\tbash \./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_runner\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not runner_target:
    raise SystemExit("Makefile missing two-contract bridge runner target")

current_target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not current_target:
    raise SystemExit("Makefile missing current-state target")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing two-contract bridge design dependency")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-shadow" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing two-contract bridge shadow dependency")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-trust" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing two-contract bridge trust dependency")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-runner" not in current_target.group("deps").split():
    raise SystemExit("current-state target missing two-contract bridge runner dependency")

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
if "check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design" not in phony_targets:
    raise SystemExit("two-contract bridge design target missing from .PHONY")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-shadow" not in phony_targets:
    raise SystemExit("two-contract bridge shadow target missing from .PHONY")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-trust" not in phony_targets:
    raise SystemExit("two-contract bridge trust target missing from .PHONY")
if "check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-runner" not in phony_targets:
    raise SystemExit("two-contract bridge runner target missing from .PHONY")
PY

echo "ok"
