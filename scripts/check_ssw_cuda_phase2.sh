#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---final}"
BIN="${SSW_CUDA_PHASE2_BIN:-$ROOT/.paper-artifacts/ssw-cuda-v1/phase2/fasim_cpu_oracle}"
ARTIFACT_ROOT="$ROOT/.paper-artifacts/ssw-cuda-v1/phase2/formal"

if [[ "$MODE" != "--preflight" && "$MODE" != "--final" ]]; then
  echo "usage: $0 [--preflight|--final]" >&2
  exit 2
fi

for relative in \
  Makefile \
  goal-ssw.md \
  fasim/fastsim.h \
  fasim/ssw.h \
  fasim/ssw_cpp.h \
  fasim/ssw_cpp.cpp \
  fasim/sswNew.cpp \
  fasim/ssw_oracle_trace.h \
  fasim/ssw_oracle_trace.cpp \
  docs/ssw_cuda/DP_CONTRACT.md \
  docs/ssw_cuda/ENDPOINT_CONTRACT.md \
  docs/ssw_cuda/CIGAR_CONTRACT.md \
  docs/ssw_cuda/TELEMETRY_SPEC.md \
  schemas/ssw_oracle_call.schema.json \
  paper/ssw_cuda/cpu_oracle_protocol.md \
  paper/ssw_cuda/cpu_oracle_attempt_plan.tsv \
  reproduce/ssw_cuda/scalar_ssw_reference.py \
  reproduce/ssw_cuda/run_phase2_oracle.py \
  tests/ssw_cuda/test_phase2_oracle.py; do
  if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
    echo "missing or unsafe SSW-CUDA Phase 2 dependency: $relative" >&2
    exit 1
  fi
done

if [[ ! -x "$BIN" || -L "$BIN" ]]; then
  echo "missing or unsafe SSW-CUDA Phase 2 binary: $BIN" >&2
  exit 1
fi

PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  "$ROOT/reproduce/ssw_cuda/scalar_ssw_reference.py" \
  "$ROOT/reproduce/ssw_cuda/run_phase2_oracle.py" \
  "$ROOT/tests/ssw_cuda/test_phase2_oracle.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/ssw_cuda/run_phase2_oracle.py" --check-schema
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/ssw_cuda/test_phase2_oracle.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/ssw_cuda/run_phase2_oracle.py" \
  --smoke --binary "$BIN"

python3 - "$ROOT" "$MODE" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
mode = sys.argv[2]
state = json.loads((root / "paper/ssw_cuda/PROGRAM_STATE.json").read_text(encoding="utf-8"))
goal = (root / "goal-ssw.md").read_text(encoding="utf-8")

if state["active_phase"] not in (2, 3) or state["phase_status"]["0"] != "pass" or state["phase_status"]["1"] != "pass":
    raise SystemExit("Phase 2 prerequisite state is invalid")
if "phase_2_status = in_progress" not in goal and "phase_2_status = pass" not in goal:
    raise SystemExit("goal-ssw Phase 2 status is missing")
if mode == "--preflight":
    if state["active_phase"] != 2 or state["phase_status"]["2"] != "in_progress":
        raise SystemExit("Phase 2 preflight requires in-progress state")
else:
    if state["active_phase"] != 3 or state["phase_status"]["2"] != "pass":
        raise SystemExit("Phase 2 final state has not advanced to Phase 3")
PY

if [[ "$MODE" == "--preflight" ]]; then
  if [[ -e "$ARTIFACT_ROOT" ]]; then
    echo "unexpected Phase 2 formal artifact root: $ARTIFACT_ROOT" >&2
    exit 1
  fi
  for relative in \
    paper/ssw_cuda/cpu_oracle_trace_source_data.tsv \
    paper/ssw_cuda/cpu_oracle_trace_artifacts.tsv \
    paper/ssw_cuda/cpu_oracle_binary_receipt.json \
    tests/ssw_cuda/fixtures/hq10_prealign.json \
    tests/ssw_cuda/fixtures/hq10_mismatch_call.json \
    tests/ssw_cuda/fixtures/hq11_prealign.json \
    tests/ssw_cuda/fixtures/hq11_mismatch_call.json; do
    if [[ -e "$ROOT/$relative" ]]; then
      echo "unexpected preexecution Phase 2 result: $relative" >&2
      exit 1
    fi
  done
else
  for relative in \
    paper/ssw_cuda/cpu_oracle_trace_source_data.tsv \
    paper/ssw_cuda/cpu_oracle_trace_artifacts.tsv \
    paper/ssw_cuda/cpu_oracle_binary_receipt.json \
    tests/ssw_cuda/fixtures/hq10_prealign.json \
    tests/ssw_cuda/fixtures/hq10_mismatch_call.json \
    tests/ssw_cuda/fixtures/hq11_prealign.json \
    tests/ssw_cuda/fixtures/hq11_mismatch_call.json; do
    if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
      echo "missing final Phase 2 evidence: $relative" >&2
      exit 1
    fi
  done
  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/ssw_cuda/run_phase2_oracle.py" \
    --check-results --binary "$BIN"
fi

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "SSW-CUDA Phase 2 $MODE checks OK"
