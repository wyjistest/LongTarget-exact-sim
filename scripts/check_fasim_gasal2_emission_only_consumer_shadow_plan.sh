#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAN="$ROOT/docs/superpowers/plans/2026-06-09-fasim-gasal2-emission-only-consumer-shadow.md"
MAKEFILE="$ROOT/Makefile"
ARCH="$ROOT/docs/fasim_gasal2_broad_path_architecture_gate.md"
CURRENT="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
GAP="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
FULL="$ROOT/docs/fasim_gasal2_full_goal_decision.md"

python3 - "$PLAN" "$MAKEFILE" "$ARCH" "$CURRENT" "$GAP" "$FULL" <<'PY'
import sys
from pathlib import Path

plan, makefile, arch, current, gap, full = [Path(p) for p in sys.argv[1:]]
for path in (plan, makefile, arch, current, gap, full):
    if not path.exists():
        raise SystemExit(f"missing file: {path}")

plan_text = plan.read_text(encoding="utf-8")
required_plan = [
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1",
    "CPU `fastSIM_extend_from_scoreinfo()` remains output authority",
    "score attempts with GASAL2 score-only APIs",
    "CPU-align only the emitted attempts",
    "cpu_align_attempts < realpath_reference_align_attempts",
    "candidate_vs_baseline > 1.0x",
    "If CPU align attempts are not reduced, stop the broad GASAL2 scoreInfo/preAlign line.",
]
for needle in required_plan:
    if needle not in plan_text:
        raise SystemExit(f"plan missing required text: {needle}")

make_text = makefile.read_text(encoding="utf-8")
if "check-fasim-gasal2-emission-only-consumer-shadow-plan:" not in make_text:
    raise SystemExit("missing Makefile emission-only plan target")
if "bash ./scripts/check_fasim_gasal2_emission_only_consumer_shadow_plan.sh" not in make_text:
    raise SystemExit("missing Makefile emission-only plan recipe")

for label, path in (("arch", arch), ("current", current), ("gap", gap), ("full", full)):
    text = path.read_text(encoding="utf-8")
    if "emission-only scoreInfo consumer shadow" not in text:
        raise SystemExit(f"{label} doc missing emission-only cross-link")
    if "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1" not in text:
        raise SystemExit(f"{label} doc missing env name")

print("ok")
PY
