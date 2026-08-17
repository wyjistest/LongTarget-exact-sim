#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---final}"
BIN="${SSW_CUDA_PHASE1_BIN:-$ROOT/.paper-artifacts/ssw-cuda-v1/phase1/fasim_authority_profile}"
ARTIFACT_ROOT="${SSW_CUDA_PHASE1_ARTIFACT_ROOT:-$ROOT/.paper-artifacts/ssw-cuda-v1/phase1/profile-runs}"
RECOVERY_ARTIFACT_ROOT="$ROOT/.paper-artifacts/ssw-cuda-v1/phase1/profile-runs-v2"

if [[ "$MODE" != "--preflight" && "$MODE" != "--final" && "$MODE" != "--blocked" && \
      "$MODE" != "--recovery-preflight" && "$MODE" != "--recovery-final" ]]; then
  echo "usage: $0 [--preflight|--final|--blocked|--recovery-preflight|--recovery-final]" >&2
  exit 2
fi

for relative in \
  Makefile \
  goal-ssw.md \
  fasim/Fasim-LongTarget.cpp \
  fasim/fastsim.h \
  fasim/ssw.h \
  fasim/sswNew.cpp \
  fasim/ssw_cpp.cpp \
  paper/ssw_cuda/cpu_profile_protocol.md \
  paper/ssw_cuda/cpu_profile_attempt_plan.tsv \
  paper/ssw_cuda/cpu_profile_recovery_protocol.md \
  paper/ssw_cuda/cpu_profile_recovery_attempt_plan.tsv \
  paper/ssw_cuda/used_input_exclusion_registry.tsv \
  reproduce/ssw_cuda/run_cpu_profile.py \
  tests/ssw_cuda/test_phase1_profile.py; do
  if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
    echo "missing or unsafe SSW-CUDA Phase 1 dependency: $relative" >&2
    exit 1
  fi
done

if [[ ! -x "$BIN" || -L "$BIN" ]]; then
  echo "missing or unsafe Phase 1 profile binary: $BIN" >&2
  exit 1
fi

PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  "$ROOT/reproduce/ssw_cuda/run_cpu_profile.py" \
  "$ROOT/tests/ssw_cuda/test_phase1_profile.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/ssw_cuda/run_cpu_profile.py" --check-plan
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/ssw_cuda/run_cpu_profile.py" --check-recovery-plan
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/ssw_cuda/test_phase1_profile.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/ssw_cuda/run_cpu_profile.py" \
  --smoke --binary "$BIN"

python3 - "$ROOT" "$MODE" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
mode = sys.argv[2]
state = json.loads((root / "paper/ssw_cuda/PROGRAM_STATE.json").read_text(encoding="utf-8"))
goal = (root / "goal-ssw.md").read_text(encoding="utf-8")

if state["active_phase"] < 1 or state["phase_status"]["0"] != "pass":
    raise SystemExit("Phase 1 program state is invalid")
if not any(
    marker in goal
    for marker in (
        "phase_1_status = in_progress",
        "phase_1_status = pass",
        "phase_1_status = blocked",
    )
):
    raise SystemExit("goal-ssw Phase 1 status is missing")
if mode == "--preflight":
    if state["active_phase"] != 1 or state["phase_status"]["1"] != "in_progress":
        raise SystemExit("Phase 1 preflight requires in-progress state")
elif mode in ("--final", "--recovery-final"):
    if state["active_phase"] < 2 or state["phase_status"]["1"] != "pass":
        raise SystemExit("Phase 1 final state is invalid")
elif mode == "--blocked":
    if state["active_phase"] != 1 or state["phase_status"]["1"] != "blocked":
        raise SystemExit("Phase 1 blocked state is invalid")
else:
    if state["active_phase"] != 1 or state["phase_status"]["1"] != "in_progress":
        raise SystemExit("Phase 1 recovery preflight requires in-progress state")
    if state.get("phase1_profile_execution_epoch") != 2:
        raise SystemExit("Phase 1 recovery execution epoch is invalid")
    if state.get("phase1_v1_status") != "blocked_by_fixed_timeout":
        raise SystemExit("Phase 1 v1 blocked status was not preserved")
PY

if [[ "$MODE" == "--final" ]]; then
  for relative in \
    paper/ssw_cuda/cpu_profile_source_data.tsv \
    paper/ssw_cuda/cpu_profile_statistics.json \
    paper/ssw_cuda/amdahl_decision.json \
    paper/ssw_cuda/amdahl_decision.md \
    paper/ssw_cuda/cpu_profile_execution_receipt.json; do
    if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
      echo "missing final Phase 1 evidence: $relative" >&2
      exit 1
    fi
  done
  python3 -m json.tool "$ROOT/paper/ssw_cuda/cpu_profile_statistics.json" >/dev/null
  python3 -m json.tool "$ROOT/paper/ssw_cuda/amdahl_decision.json" >/dev/null
  python3 -m json.tool "$ROOT/paper/ssw_cuda/cpu_profile_execution_receipt.json" >/dev/null
  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/ssw_cuda/run_cpu_profile.py" \
    --check-results --artifact-root "$ARTIFACT_ROOT"
elif [[ "$MODE" == "--blocked" ]]; then
  for relative in \
    paper/ssw_cuda/cpu_profile_blocked_artifact_manifest.tsv \
    paper/ssw_cuda/cpu_profile_execution_receipt.json \
    paper/ssw_cuda/amdahl_decision.json \
    paper/ssw_cuda/amdahl_decision.md; do
    if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
      echo "missing blocked Phase 1 evidence: $relative" >&2
      exit 1
    fi
  done
  python3 -m json.tool "$ROOT/paper/ssw_cuda/cpu_profile_execution_receipt.json" >/dev/null
  python3 -m json.tool "$ROOT/paper/ssw_cuda/amdahl_decision.json" >/dev/null
  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/ssw_cuda/run_cpu_profile.py" \
    --check-blocked --artifact-root "$ARTIFACT_ROOT"
elif [[ "$MODE" == "--recovery-preflight" ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/ssw_cuda/run_cpu_profile.py" \
    --check-blocked --artifact-root "$ARTIFACT_ROOT"
  if [[ -e "$RECOVERY_ARTIFACT_ROOT" ]]; then
    echo "Phase 1 recovery artifact root already exists: $RECOVERY_ARTIFACT_ROOT" >&2
    exit 1
  fi
  for relative in \
    paper/ssw_cuda/cpu_profile_v2_source_data.tsv \
    paper/ssw_cuda/cpu_profile_v2_statistics.json \
    paper/ssw_cuda/amdahl_v2_decision.json \
    paper/ssw_cuda/amdahl_v2_decision.md \
    paper/ssw_cuda/cpu_profile_v2_execution_receipt.json \
    paper/ssw_cuda/cpu_profile_v2_resource_logs.tsv \
    paper/ssw_cuda/cpu_profile_v2_analysis_receipt.json; do
    if [[ -e "$ROOT/$relative" ]]; then
      echo "unexpected preexecution Phase 1 recovery result: $relative" >&2
      exit 1
    fi
  done
elif [[ "$MODE" == "--recovery-final" ]]; then
  for relative in \
    paper/ssw_cuda/cpu_profile_v2_source_data.tsv \
    paper/ssw_cuda/cpu_profile_v2_statistics.json \
    paper/ssw_cuda/amdahl_v2_decision.json \
    paper/ssw_cuda/amdahl_v2_decision.md \
    paper/ssw_cuda/cpu_profile_v2_execution_receipt.json \
    paper/ssw_cuda/cpu_profile_v2_resource_logs.tsv \
    paper/ssw_cuda/cpu_profile_v2_analysis_receipt.json; do
    if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
      echo "missing final Phase 1 recovery evidence: $relative" >&2
      exit 1
    fi
  done
  python3 -m json.tool "$ROOT/paper/ssw_cuda/cpu_profile_v2_statistics.json" >/dev/null
  python3 -m json.tool "$ROOT/paper/ssw_cuda/amdahl_v2_decision.json" >/dev/null
  python3 -m json.tool "$ROOT/paper/ssw_cuda/cpu_profile_v2_execution_receipt.json" >/dev/null
  python3 -m json.tool "$ROOT/paper/ssw_cuda/cpu_profile_v2_analysis_receipt.json" >/dev/null
  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/ssw_cuda/run_cpu_profile.py" \
    --check-recovery-results
fi

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "SSW-CUDA Phase 1 $MODE checks OK"
