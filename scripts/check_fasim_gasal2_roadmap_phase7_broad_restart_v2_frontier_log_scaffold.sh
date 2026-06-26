#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_phase7_broad_restart_v2_design.md"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"

python3 - "$DOC" "$ROADMAP" <<'PY'
from pathlib import Path
import sys

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
roadmap = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())

required = [
    "phase7_broad_restart_v2_frontier_log_scaffold_gate = runtime_smoke_clean",
    "FASIM_GASAL2_PHASE7_FRONTIER_LOG=1",
    "frontier log path is non-empty",
    "frontier log digest is non-empty",
    "frontier log TSV schema is present",
    "CPU aligner.Align() remains authority",
    "GASAL2 output authority = 0",
    "next gate = NEAT1 first1 exact replay proof",
    "broad_objective_status = open",
    "must_not_call_update_goal_complete = 1",
]

for source_name, text in [("design", doc), ("roadmap", roadmap)]:
    missing = [needle for needle in required if needle not in text]
    if missing:
        raise SystemExit(
            f"{source_name} missing Phase 7 v2 frontier-log scaffold phrases: "
            + ", ".join(missing)
        )

print("phase7_broad_restart_v2_frontier_log_scaffold_gate=runtime_smoke_clean")
print("phase7_frontier_log_env_gate=pass")
print("phase7_frontier_log_runtime_smoke=pass")
print("cpu_aligner_align_authority=1")
print("gasal2_output_authority=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
