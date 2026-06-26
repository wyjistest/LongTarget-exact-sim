#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP="$ROOT/fasim/Fasim-LongTarget.cpp"
STATS="$ROOT/fasim/gasal2_align_bridge.h"
MAKEFILE="$ROOT/Makefile"

python3 - "$CPP" "$STATS" "$MAKEFILE" <<'PY'
from pathlib import Path
import re
import sys

cpp = Path(sys.argv[1]).read_text(encoding="utf-8")
stats = Path(sys.argv[2]).read_text(encoding="utf-8")
makefile = Path(sys.argv[3]).read_text(encoding="utf-8")

for needle in [
    "FASIM_GASAL2_PHASE7_FRONTIER_LOG",
    "fasim_gasal2_phase7_frontier_log_runtime",
]:
    if needle not in cpp:
        raise SystemExit(f"missing runtime marker: {needle}")

for needle in [
    "phase7_frontier_log_requested",
    "phase7_frontier_log_active",
    "phase7_frontier_log_tasks",
    "phase7_frontier_log_scoreinfos",
    "phase7_frontier_log_align_attempts",
    "phase7_frontier_log_triplexes",
    "phase7_frontier_log_path",
    "phase7_frontier_log_digest",
]:
    if needle not in stats:
        raise SystemExit(f"missing telemetry marker: {needle}")

target = re.search(
    r"^check-fasim-gasal2-phase7-frontier-log-env:\n"
    r"\tbash \./scripts/check_fasim_gasal2_phase7_frontier_log_env\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("missing Makefile frontier-log env target")

print("ok")
PY
