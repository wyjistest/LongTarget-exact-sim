#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRIDGE_H="$ROOT/fasim/gasal2_align_bridge.h"
BRIDGE_CPP="$ROOT/fasim/gasal2_align_bridge.cpp"
BRIDGE_STUB="$ROOT/fasim/gasal2_align_bridge_stub.cpp"
FASIM_CPP="$ROOT/fasim/Fasim-LongTarget.cpp"
MAKEFILE="$ROOT/Makefile"

for path in "$BRIDGE_H" "$BRIDGE_CPP" "$BRIDGE_STUB" "$FASIM_CPP" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing span-prune shadow dependency: $path" >&2
    exit 1
  fi
done

python3 - "$BRIDGE_H" "$BRIDGE_CPP" "$BRIDGE_STUB" "$FASIM_CPP" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

bridge_h = Path(sys.argv[1]).read_text(encoding="utf-8")
bridge_cpp = Path(sys.argv[2]).read_text(encoding="utf-8")
bridge_stub = Path(sys.argv[3]).read_text(encoding="utf-8")
fasim_cpp = Path(sys.argv[4]).read_text(encoding="utf-8")
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

for phrase in (
    "fasim_gasal2_align_attempt_indexes",
    "const std::vector<size_t> &attemptIndexes",
    "fasim_gasal2_select_attempt_indexes_for_span_prune_shadow",
    "std::vector<size_t> *spanPruneAttemptIndexes",
):
    if phrase not in bridge_h:
        raise SystemExit(f"bridge header missing {phrase}")
    if phrase not in bridge_cpp:
        raise SystemExit(f"bridge implementation missing {phrase}")
    if phrase not in bridge_stub:
        raise SystemExit(f"bridge stub missing {phrase}")

for phrase in (
    "FASIM_GASAL2_PRETRACEBACK_SPAN_PRUNE_SHADOW",
    "FasimGasal2PretracebackSpanPruneShadowStats",
    "fasim_print_gasal2_pretraceback_span_prune_shadow_stats",
    "fasim_gasal2_pretraceback_span_prune_shadow_",
    "authority_skipped_invalid_span",
    "false_prune",
):
    if phrase not in fasim_cpp:
        raise SystemExit(f"Fasim-LongTarget.cpp missing {phrase}")

target = re.search(
    r"^check-fasim-gasal2-pretraceback-span-prune-shadow-parser:\n"
    r"\tbash \./scripts/check_fasim_gasal2_pretraceback_span_prune_shadow_parser\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing parser target")

target = re.search(
    r"^check-fasim-gasal2-pretraceback-span-prune-shadow-api:\n"
    r"\tbash \./scripts/check_fasim_gasal2_pretraceback_span_prune_shadow_api\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing api target")
PY

echo "ok"
