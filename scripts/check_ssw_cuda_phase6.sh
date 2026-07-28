#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---final}"
PHASE5_HEAD="2cf9e7c9d03e2905cb1d171ed4e2056e727b87c8"
PLAN_SHA256="dbbe24ebc46282a66fdbbcab200cc83e6d7c3d7755b15d3b683f9bf00fab5e41"
DRIVER="${SSW_CUDA_PHASE6_DRIVER:-$ROOT/.paper-artifacts/ssw-cuda-v1/forward/build/ssw_cuda_forward_driver}"
STUB="${SSW_CUDA_PHASE6_STUB_PROBE:-$ROOT/.paper-artifacts/ssw-cuda-v1/preselect/build/ssw_cuda_stub_probe}"

if [[ "$MODE" != "--preflight" && "$MODE" != "--final" ]]; then
  echo "usage: $0 [--preflight|--final]" >&2
  exit 2
fi

for relative in \
  Makefile \
  goal-ssw.md \
  docs/ssw_cuda/DP_CONTRACT.md \
  docs/ssw_cuda/ENDPOINT_CONTRACT.md \
  fasim/ssw_cuda/ssw_cuda_api.h \
  fasim/ssw_cuda/ssw_cuda_internal.h \
  fasim/ssw_cuda/ssw_cuda_forward.cu \
  fasim/ssw_cuda/ssw_cuda_pre_align.cu \
  fasim/ssw_cuda/ssw_cuda_select.cu \
  fasim/ssw_cuda/ssw_cuda_striped.cuh \
  fasim/ssw_cuda/ssw_cuda_stub.cpp \
  paper/ssw_cuda/PROGRAM_STATE.json \
  paper/ssw_cuda/STATUS.md \
  paper/ssw_cuda/corpus_manifest.tsv \
  paper/ssw_cuda/forward_endpoint_attempt_plan.tsv \
  paper/ssw_cuda/forward_endpoint_design.md \
  reproduce/ssw_cuda/run_phase5_preselect.py \
  reproduce/ssw_cuda/run_phase6_forward.py \
  scripts/check_ssw_cuda_phase5.sh \
  scripts/check_ssw_cuda_phase6.sh \
  tests/ssw_cuda/fixtures/hq10_mismatch_call.json \
  tests/ssw_cuda/fixtures/hq11_mismatch_call.json \
  tests/ssw_cuda/fixtures/phase5_smoke.tsv \
  tests/ssw_cuda/ssw_cuda_forward_driver.cpp \
  tests/ssw_cuda/ssw_cuda_stub_probe.cpp \
  tests/ssw_cuda/test_forward_endpoint.py; do
  if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
    echo "missing or unsafe SSW-CUDA Phase 6 dependency: $relative" >&2
    exit 1
  fi
done

observed_plan_sha256="$(sha256sum "$ROOT/paper/ssw_cuda/forward_endpoint_attempt_plan.tsv" | awk '{print $1}')"
if [[ "$observed_plan_sha256" != "$PLAN_SHA256" ]]; then
  echo "Phase 6 attempt plan digest drift: $observed_plan_sha256" >&2
  exit 1
fi

make -C "$ROOT" build-fasim build-ssw-cuda-phase6-driver build-ssw-cuda-phase5-stub-probe
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  "$ROOT/reproduce/ssw_cuda/run_phase6_forward.py" \
  "$ROOT/tests/ssw_cuda/test_forward_endpoint.py"
PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/reproduce/ssw_cuda/run_phase6_forward.py" --check-plan
SSW_CUDA_PHASE6_DRIVER="$DRIVER" SSW_CUDA_PHASE6_STUB_PROBE="$STUB" \
  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/ssw_cuda/test_forward_endpoint.py"

python3 - "$ROOT" "$MODE" "$PHASE5_HEAD" "$PLAN_SHA256" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
mode = sys.argv[2]
phase5_head = sys.argv[3]
plan_sha256 = sys.argv[4]
state = json.loads((root / "paper/ssw_cuda/PROGRAM_STATE.json").read_text(encoding="utf-8"))
goal = (root / "goal-ssw.md").read_text(encoding="utf-8")
status = (root / "paper/ssw_cuda/STATUS.md").read_text(encoding="utf-8")
design = (root / "paper/ssw_cuda/forward_endpoint_design.md").read_text(encoding="utf-8")

if mode == "--preflight":
    if state["active_phase"] != 6 or state["phase_status"]["6"] != "in_progress":
        raise SystemExit("Phase 6 preflight requires in-progress state")
    required_goal = (
        "active_phase = 6",
        "phase_5_status = pass",
        "phase_6_status = in_progress",
        "phase_7_status = pending",
        "last_completed_phase = 5",
    )
else:
    if (
        state["active_phase"] != 7
        or state["phase_status"]["6"] != "pass"
        or state["phase_status"]["7"] != "in_progress"
    ):
        raise SystemExit("Phase 6 final state has not advanced to Phase 7")
    required_goal = (
        "active_phase = 7",
        "phase_6_status = pass",
        "phase_7_status = in_progress",
        "last_completed_phase = 6",
        "last_decision = phase6_l3_exact_forward_pass",
        "last_evidence_doc = paper/ssw_cuda/forward_endpoint_receipt.json",
        "last_test_command = make check-ssw-cuda-phase6",
    )

for phrase in required_goal:
    if phrase not in goal:
        raise SystemExit(f"goal-ssw Phase 6 state drift: {phrase}")
for phrase in (
    f"active_phase = {state['active_phase']}",
    f"phase_6_status = {state['phase_status']['6']}",
    "bioinformatics_b3_track = closed_amdahl",
    "l8_contract_status = diagnostic_only",
):
    if phrase not in status:
        raise SystemExit(f"SSW-CUDA status drift: {phrase}")
if plan_sha256 not in design:
    raise SystemExit("Phase 6 design does not freeze the attempt-plan digest")
for phrase in (
    "pre-align versus Phase 6 forward vector equality is diagnostic only",
    "No `50 x 668` application panel",
    "cpu_endpoint_calls = 0",
    "mechanism repair iterations <= 3",
):
    if phrase not in design:
        raise SystemExit(f"Phase 6 design contract drift: {phrase}")

changed = subprocess.run(
    ["git", "diff", "--name-only", f"{phase5_head}..HEAD"],
    cwd=root, check=True, text=True, stdout=subprocess.PIPE,
).stdout.splitlines()
worktree_changed = [
    line[3:]
    for line in subprocess.run(
        ["git", "status", "--porcelain=v1"], cwd=root, check=True,
        text=True, stdout=subprocess.PIPE,
    ).stdout.splitlines()
    if len(line) >= 4
]
changed.extend(worktree_changed)
oracle_changes = sorted(
    path for path in changed
    if path in {"fasim/sswNew.cpp", "fasim/ssw_cpp.cpp", "fasim/ssw_cpp.h"}
)
if oracle_changes:
    raise SystemExit(f"Phase 6 modified the frozen CPU oracle: {oracle_changes}")

makefile = (root / "Makefile").read_text(encoding="utf-8")
sources_line = next(line for line in makefile.splitlines() if line.startswith("FASIM_SOURCES :="))
if "ssw_cuda" in sources_line:
    raise SystemExit("default Fasim sources unexpectedly link SSW-CUDA")
PY

if [[ "$MODE" == "--final" ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 \
    "$ROOT/reproduce/ssw_cuda/run_phase6_forward.py" --check-results
fi

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "SSW-CUDA Phase 6 $MODE checks OK"
