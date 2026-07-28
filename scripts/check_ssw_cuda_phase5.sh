#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---final}"
PHASE4_HEAD="5975cef5b2792da2a369a0d1a187fa2b9c248c25"
DRIVER="${SSW_CUDA_PHASE5_DRIVER:-$ROOT/.paper-artifacts/ssw-cuda-v1/preselect/build/ssw_cuda_preselect_driver}"
STUB="${SSW_CUDA_PHASE5_STUB_PROBE:-$ROOT/.paper-artifacts/ssw-cuda-v1/preselect/build/ssw_cuda_stub_probe}"

if [[ "$MODE" != "--preflight" && "$MODE" != "--final" ]]; then
  echo "usage: $0 [--preflight|--final]" >&2
  exit 2
fi

for relative in \
  Makefile \
  goal-ssw.md \
  fasim/ssw_cuda/ssw_cuda_api.h \
  fasim/ssw_cuda/ssw_cuda_internal.h \
  fasim/ssw_cuda/ssw_cuda_pre_align.cu \
  fasim/ssw_cuda/ssw_cuda_select.cu \
  fasim/ssw_cuda/ssw_cuda_stub.cpp \
  paper/ssw_cuda/PROGRAM_STATE.json \
  paper/ssw_cuda/STATUS.md \
  paper/ssw_cuda/corpus_manifest.tsv \
  paper/ssw_cuda/preselect_attempt_plan.tsv \
  paper/ssw_cuda/preselect_design.md \
  reproduce/ssw_cuda/run_phase5_preselect.py \
  scripts/check_ssw_cuda_phase5.sh \
  tests/ssw_cuda/fixtures/phase5_smoke.tsv \
  tests/ssw_cuda/ssw_cuda_preselect_driver.cpp \
  tests/ssw_cuda/ssw_cuda_stub_probe.cpp \
  tests/ssw_cuda/test_preselect.py; do
  if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
    echo "missing or unsafe SSW-CUDA Phase 5 dependency: $relative" >&2
    exit 1
  fi
done

make -C "$ROOT" build-fasim build-ssw-cuda-phase5-driver build-ssw-cuda-phase5-stub-probe
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  "$ROOT/reproduce/ssw_cuda/run_phase5_preselect.py" \
  "$ROOT/tests/ssw_cuda/test_preselect.py"
PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/reproduce/ssw_cuda/run_phase5_preselect.py" --check-plan
SSW_CUDA_PHASE5_DRIVER="$DRIVER" SSW_CUDA_PHASE5_STUB_PROBE="$STUB" \
  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/ssw_cuda/test_preselect.py"

python3 - "$ROOT" "$MODE" "$PHASE4_HEAD" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
mode = sys.argv[2]
phase4_head = sys.argv[3]
state = json.loads((root / "paper/ssw_cuda/PROGRAM_STATE.json").read_text(encoding="utf-8"))
goal = (root / "goal-ssw.md").read_text(encoding="utf-8")
status = (root / "paper/ssw_cuda/STATUS.md").read_text(encoding="utf-8")

if mode == "--preflight":
    if state["active_phase"] != 5 or state["phase_status"]["5"] != "in_progress":
        raise SystemExit("Phase 5 preflight requires in-progress state")
    required_goal = (
        "active_phase = 5",
        "phase_5_status = in_progress",
        "phase_6_status = pending",
    )
else:
    if (
        state["active_phase"] < 6
        or state["phase_status"]["5"] != "pass"
    ):
        raise SystemExit("Phase 5 final state has not advanced beyond Phase 5")
    required_goal = (
        "phase_5_status = pass",
    )
    receipt = json.loads((root / "paper/ssw_cuda/preselect_receipt.json").read_text(encoding="utf-8"))
    source_commit = receipt["source_commit"]
    if source_commit != state["phase5_implementation_commit"]:
        raise SystemExit("Phase 5 implementation commit drift")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", phase4_head, source_commit], cwd=root
    ).returncode != 0:
        raise SystemExit("Phase 5 implementation is not descended from Phase 4")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, "HEAD"], cwd=root
    ).returncode != 0:
        raise SystemExit("current HEAD is not descended from the frozen Phase 5 implementation")
    for relative in (
        "fasim/ssw_cuda/ssw_cuda_pre_align.cu",
        "paper/ssw_cuda/preselect_attempt_plan.tsv",
        "scripts/check_ssw_cuda_phase5.sh",
    ):
        if subprocess.run(["git", "cat-file", "-e", f"{source_commit}:{relative}"], cwd=root).returncode != 0:
            raise SystemExit(f"formal Phase 5 dependency was not committed: {relative}")

for phrase in required_goal:
    if phrase not in goal:
        raise SystemExit(f"goal-ssw Phase 5 state drift: {phrase}")
for phrase in (
    f"active_phase = {state['active_phase']}",
    f"phase_5_status = {state['phase_status']['5']}",
    "bioinformatics_b3_track = closed_amdahl",
    "l8_contract_status = diagnostic_only",
):
    if phrase not in status:
        raise SystemExit(f"SSW-CUDA status drift: {phrase}")

audit_commit = (
    state["phase5_implementation_commit"] if mode == "--final" else "HEAD"
)
changed = subprocess.run(
    ["git", "diff", "--name-only", f"{phase4_head}..{audit_commit}"],
    cwd=root, check=True, text=True, stdout=subprocess.PIPE,
).stdout.splitlines()
if mode == "--preflight":
    changed.extend(
        line[3:]
        for line in subprocess.run(
            ["git", "status", "--porcelain=v1"], cwd=root, check=True,
            text=True, stdout=subprocess.PIPE,
        ).stdout.splitlines()
        if len(line) >= 4
    )
oracle_changes = sorted(
    path for path in changed
    if path in {"fasim/sswNew.cpp", "fasim/ssw_cpp.cpp", "fasim/ssw_cpp.h"}
)
if oracle_changes:
    raise SystemExit(f"Phase 5 modified the frozen CPU oracle: {oracle_changes}")
PY

if [[ "$MODE" == "--final" ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 \
    "$ROOT/reproduce/ssw_cuda/run_phase5_preselect.py" --check-results
fi

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "SSW-CUDA Phase 5 $MODE checks OK"
echo "primary_gpu_tasks=623"
echo "total_gpu_task_executions=815"
echo "bioinformatics_b3_track=closed_amdahl"
