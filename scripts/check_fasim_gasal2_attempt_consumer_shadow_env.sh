#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAIN="$ROOT/fasim/Fasim-LongTarget.cpp"
BRIDGE_H="$ROOT/fasim/gasal2_align_bridge.h"
BRIDGE_CPP="$ROOT/fasim/gasal2_align_bridge.cpp"
STUB="$ROOT/fasim/gasal2_align_bridge_stub.cpp"
MAKEFILE="$ROOT/Makefile"

for path in "$MAIN" "$BRIDGE_H" "$BRIDGE_CPP" "$STUB" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing attempt consumer env dependency: $path" >&2
    exit 1
  fi
done

python3 - "$MAIN" "$BRIDGE_H" "$BRIDGE_CPP" "$STUB" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

main = Path(sys.argv[1]).read_text(encoding="utf-8")
bridge_h = Path(sys.argv[2]).read_text(encoding="utf-8")
bridge_cpp = Path(sys.argv[3]).read_text(encoding="utf-8")
stub = Path(sys.argv[4]).read_text(encoding="utf-8")
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

env = "FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW"
required = [
    "attempt_consumer_shadow_requested",
    "attempt_consumer_shadow_active",
    "attempt_consumer_shadow_decision",
    "attempt_consumer_shadow_tasks",
    "attempt_consumer_shadow_scoreinfos",
    "attempt_consumer_shadow_attempts",
    "attempt_consumer_shadow_selected_attempts",
    "attempt_consumer_shadow_cpu_align_attempts",
    "attempt_consumer_shadow_triplex_mismatches",
    "attempt_consumer_shadow_missing_triplexes",
    "attempt_consumer_shadow_extra_triplexes",
    "attempt_consumer_shadow_first_mismatch",
    "attempt_consumer_shadow_fallbacks",
]
for phrase in required:
    if phrase not in bridge_h:
        raise SystemExit(f"bridge header missing {phrase}")

for phrase in (
    env,
    "attempt_consumer_shadow_decision",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_requested=",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_active=",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_selected_attempts=",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_cpu_align_attempts=",
):
    if phrase not in bridge_cpp and phrase not in main:
        raise SystemExit(f"runtime missing {phrase}")

for phrase in (
    "benchmark.fasim_gasal2_attempt_consumer_shadow_requested=0",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_active=0",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_decision=not_requested",
):
    if phrase not in stub:
        raise SystemExit(f"stub missing {phrase}")

target = re.search(
    r"^check-fasim-gasal2-attempt-consumer-shadow-env:\n"
    r"\tbash \./scripts/check_fasim_gasal2_attempt_consumer_shadow_env\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-attempt-consumer-shadow-env target")
PY

echo "ok"
