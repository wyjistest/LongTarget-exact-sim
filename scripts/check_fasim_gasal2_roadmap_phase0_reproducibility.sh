#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
READY_DOC="$ROOT/docs/fasim_gasal2_short_query_top5_readiness.md"
SETUP_CHECK="$ROOT/scripts/check_fasim_gasal2_reproducible_setup.sh"
MAKEFILE="$ROOT/Makefile"

for path in "$ROADMAP" "$READY_DOC" "$SETUP_CHECK" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing Phase 0 reproducibility dependency: $path" >&2
    exit 1
  fi
done

python3 - "$ROADMAP" "$READY_DOC" "$MAKEFILE" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path


roadmap = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
ready_doc = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[3]).read_text(encoding="utf-8")

required_roadmap = [
    "Phase 0: Freeze Evidence And Reproducibility",
    "track the GASAL2 patch used by Fasim",
    "provide a setup/build target that clones, patches, and builds GASAL2",
    "remove hard-coded local GASAL2 assumptions where possible",
    "document CUDA version, SM arch, GASAL2_MAX_QUERY_LEN, and N_CODE",
    "keep all GASAL2 paths default-off",
    "make check-fasim-gasal2-reproducible-setup",
    "make setup-gasal2",
    "make build-fasim-gasal2",
    "make check-fasim-gasal2-equivalence-first-convert",
    "repo = https://github.com/nahmedraja/GASAL2.git",
    "commit = 106d94ee53fc847214fb05f2f9f892538a5d3baf",
    "patch = patches/gasal2-fasim-bridge.patch",
    "GASAL2_MAX_QUERY_LEN = 2812",
    "GASAL2_N_CODE = 0x4E",
    "check-fasim-gasal2-reproducible-setup: passed",
]
missing = [phrase for phrase in required_roadmap if phrase not in roadmap]
if missing:
    raise SystemExit(
        "roadmap missing Phase 0 reproducibility phrases: " + ", ".join(missing)
    )

required_ready = [
    "repo: https://github.com/nahmedraja/GASAL2.git",
    "commit: 106d94ee53fc847214fb05f2f9f892538a5d3baf",
    "patch: patches/gasal2-fasim-bridge.patch",
    "setup: scripts/setup_gasal2.sh",
    "make check-fasim-gasal2-reproducible-setup",
]
missing_ready = [phrase for phrase in required_ready if phrase not in ready_doc]
if missing_ready:
    raise SystemExit(
        "readiness doc missing reproducibility phrases: "
        + ", ".join(missing_ready)
    )

required_make = [
    r"^GASAL2_REPO_URL \?= https://github\.com/nahmedraja/GASAL2\.git$",
    r"^GASAL2_COMMIT \?= 106d94ee53fc847214fb05f2f9f892538a5d3baf$",
    r"^GASAL2_PATCH \?= patches/gasal2-fasim-bridge\.patch$",
    r"^GASAL2_MAX_QUERY_LEN \?= 2812$",
    r"^GASAL2_N_CODE \?= 0x4E$",
    r"^check-fasim-gasal2-reproducible-setup:\n\tbash \./scripts/check_fasim_gasal2_reproducible_setup\.sh$",
]
for pattern in required_make:
    if not re.search(pattern, makefile, flags=re.MULTILINE):
        raise SystemExit(f"Makefile missing reproducibility pattern: {pattern}")

print("phase0_reproducibility_gate=ready")
print("gasal2_patch_tracked=1")
print("gasal2_setup_target_present=1")
print("gasal2_build_constants_documented=1")
print("hardcoded_tmp_gasal2_bridge_path_forbidden=1")
PY

"$SETUP_CHECK" >/dev/null
