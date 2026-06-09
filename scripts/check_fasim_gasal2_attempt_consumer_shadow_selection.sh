#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRIDGE_H="$ROOT/fasim/gasal2_align_bridge.h"
BRIDGE_CPP="$ROOT/fasim/gasal2_align_bridge.cpp"
STUB="$ROOT/fasim/gasal2_align_bridge_stub.cpp"
MAKEFILE="$ROOT/Makefile"

for path in "$BRIDGE_H" "$BRIDGE_CPP" "$STUB" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing attempt consumer selection dependency: $path" >&2
    exit 1
  fi
done

python3 - "$BRIDGE_H" "$BRIDGE_CPP" "$STUB" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

bridge_h = Path(sys.argv[1]).read_text(encoding="utf-8")
bridge_cpp = Path(sys.argv[2]).read_text(encoding="utf-8")
stub = Path(sys.argv[3]).read_text(encoding="utf-8")
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")

for phrase in (
    "fasim_gasal2_select_attempt_indexes_from_scores",
    "std::vector<size_t> *selectedAttemptIndexes",
    "fasim_gasal2_record_attempt_consumer_shadow_request",
    "fasim_gasal2_record_attempt_consumer_shadow_replay",
    "fasim_gasal2_record_attempt_consumer_shadow_comparison",
):
    if phrase not in bridge_h:
        raise SystemExit(f"bridge header missing {phrase}")

for phrase in (
    "bool fasim_gasal2_select_attempt_indexes_from_scores",
    "run_score_only(&g_score_state",
    "select_attempts_from_scores(attempts, scoreResults",
    "void fasim_gasal2_record_attempt_consumer_shadow_request",
    "void fasim_gasal2_record_attempt_consumer_shadow_replay",
    "void fasim_gasal2_record_attempt_consumer_shadow_comparison",
    "attempt_consumer_shadow_score_seconds",
    "attempt_consumer_shadow_select_seconds",
):
    if phrase not in bridge_cpp:
        raise SystemExit(f"bridge implementation missing {phrase}")

if "bool fasim_gasal2_select_attempt_indexes_from_scores" not in stub:
    raise SystemExit("stub missing fasim_gasal2_select_attempt_indexes_from_scores")
if "fasim_gasal2_record_attempt_consumer_shadow_request" not in stub:
    raise SystemExit("stub missing attempt consumer stats record API")

target = re.search(
    r"^check-fasim-gasal2-attempt-consumer-shadow-selection:\n"
    r"\tbash \./scripts/check_fasim_gasal2_attempt_consumer_shadow_selection\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing selection checker target")
PY

echo "ok"
