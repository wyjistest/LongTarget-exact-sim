#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAKEFILE="$ROOT/Makefile"
MALAT1_WRAPPER="$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_malat1_full_trust.sh"
NEAT1_WRAPPER="$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_neat1_first64_trust.sh"

for path in "$MAKEFILE" "$MALAT1_WRAPPER" "$NEAT1_WRAPPER"; do
  if [[ ! -s "$path" ]]; then
    echo "missing trust target dependency: $path" >&2
    exit 1
  fi
done

python3 - "$MAKEFILE" "$MALAT1_WRAPPER" "$NEAT1_WRAPPER" <<'PY'
import re
import sys
from pathlib import Path

makefile = Path(sys.argv[1]).read_text(encoding="utf-8")
malat1 = Path(sys.argv[2]).read_text(encoding="utf-8")
neat1 = Path(sys.argv[3]).read_text(encoding="utf-8")

targets = {
    "characterize-fasim-long-query-streaming-scoreinfo-malat1-full-trust": (
        "characterize_fasim_long_query_streaming_scoreinfo_malat1_full_trust.sh"
    ),
    "characterize-fasim-long-query-streaming-scoreinfo-neat1-first64-trust": (
        "characterize_fasim_long_query_streaming_scoreinfo_neat1_first64_trust.sh"
    ),
}

for target, script in targets.items():
    pattern = (
        rf"^{re.escape(target)}:\n"
        r"\t\$\(MAKE\) build-fasim-gasal2 FASIM_GASAL2_TARGET=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct\n"
        rf"\tBIN=\$\(CURDIR\)/\.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash \./scripts/{re.escape(script)}$"
    )
    if not re.search(pattern, makefile, flags=re.MULTILINE):
        raise SystemExit(f"Makefile target route is wrong for {target}")

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
required_phony = set(targets)
required_phony.add("check-fasim-long-query-streaming-scoreinfo-trust-targets")
missing_phony = sorted(required_phony - phony_targets)
if missing_phony:
    raise SystemExit("trust targets missing from .PHONY: " + ", ".join(missing_phony))

if 'MALAT1_RECORD_LIMITS="${MALAT1_RECORD_LIMITS:-670}"' not in malat1:
    raise SystemExit("MALAT1 full wrapper must default MALAT1_RECORD_LIMITS to 670")
if "characterize_fasim_long_query_streaming_scoreinfo_realpath_trust.sh" not in malat1:
    raise SystemExit("MALAT1 full wrapper must delegate to realpath trust characterization")
if 'NEAT1_RECORD_LIMITS="${NEAT1_RECORD_LIMITS:-64}"' not in neat1:
    raise SystemExit("NEAT1 first64 wrapper must default NEAT1_RECORD_LIMITS to 64")
if "characterize_fasim_long_query_streaming_scoreinfo_neat1_trust.sh" not in neat1:
    raise SystemExit("NEAT1 first64 wrapper must delegate to NEAT1 trust characterization")
PY

echo "ok"
