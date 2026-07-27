#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for relative in \
  goal-ssw.md \
  docs/ssw_cuda/DP_CONTRACT.md \
  docs/ssw_cuda/ENDPOINT_CONTRACT.md \
  docs/ssw_cuda/CIGAR_CONTRACT.md \
  docs/ssw_cuda/TELEMETRY_SPEC.md \
  docs/ssw_cuda/HOLDOUT_POLICY.md \
  docs/ssw_cuda/PERFORMANCE_PROTOCOL.md \
  paper/ssw_cuda/STATUS.md \
  paper/ssw_cuda/PROGRAM_STATE.json \
  paper/ssw_cuda/historical_evidence_inventory.tsv \
  paper/ssw_cuda/historical_evidence_receipt.json \
  paper/ssw_cuda/baseline_check_receipt.json \
  paper/ssw_cuda/used_input_exclusion_registry.tsv \
  paper/ssw_cuda/used_input_exclusion_registry.sha256 \
  paper/ssw_cuda/runtime_epochs.json \
  paper/ssw_cuda/source_inventory.tsv \
  paper/ssw_cuda/license_inventory.tsv \
  paper/ssw_cuda/claim_ledger.tsv \
  reproduce/ssw_cuda/freeze_phase0.py \
  tests/ssw_cuda/test_phase0_freeze.py; do
  if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
    echo "missing or unsafe SSW-CUDA Phase 0 dependency: $relative" >&2
    exit 1
  fi
done

python3 -m json.tool "$ROOT/paper/ssw_cuda/PROGRAM_STATE.json" >/dev/null
python3 -m json.tool "$ROOT/paper/ssw_cuda/historical_evidence_receipt.json" >/dev/null
python3 -m json.tool "$ROOT/paper/ssw_cuda/baseline_check_receipt.json" >/dev/null
python3 -m json.tool "$ROOT/paper/ssw_cuda/runtime_epochs.json" >/dev/null
python3 -m py_compile \
  "$ROOT/reproduce/ssw_cuda/freeze_phase0.py" \
  "$ROOT/tests/ssw_cuda/test_phase0_freeze.py"

(
  cd "$ROOT/paper/ssw_cuda"
  sha256sum --check --status used_input_exclusion_registry.sha256
)

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/ssw_cuda/test_phase0_freeze.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/ssw_cuda/freeze_phase0.py" --check

python3 - "$ROOT" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
state = json.loads((root / "paper/ssw_cuda/PROGRAM_STATE.json").read_text(encoding="utf-8"))
receipt = json.loads((root / "paper/ssw_cuda/historical_evidence_receipt.json").read_text(encoding="utf-8"))
goal = (root / "goal-ssw.md").read_text(encoding="utf-8")
status = (root / "paper/ssw_cuda/STATUS.md").read_text(encoding="utf-8")

if state["phase_status"]["0"] != "pass" or state["active_phase"] != 1:
    raise SystemExit("Phase 0 program state has not advanced to Phase 1")
if receipt["phase0_status"] != "pass":
    raise SystemExit("Phase 0 historical receipt is not final")
for phrase in (
    "active_phase = 1",
    "phase_0_status = pass",
    "last_completed_phase = 0",
    "last_decision = phase0_evidence_frozen",
    "last_evidence_doc = paper/ssw_cuda/historical_evidence_receipt.json",
    "last_test_command = make check-ssw-cuda-phase0",
):
    if phrase not in goal:
        raise SystemExit(f"goal-ssw state drift: {phrase}")
for phrase in (
    "active_phase = 1",
    "phase_0_status = pass",
    "bioinformatics_b3_track = pending_amdahl",
    "l8_contract_status = diagnostic_only",
):
    if phrase not in status:
        raise SystemExit(f"SSW-CUDA status drift: {phrase}")
PY

if [[ "$(sha256sum "$ROOT/goal.md" | awk '{print $1}')" != \
  "8489d7a4e37c9a2d4bdee78fcee40158230c513bfc6adcea9993abd7b8c71509" ]]; then
  echo "goal.md was overwritten" >&2
  exit 1
fi

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "SSW-CUDA Phase 0 checks OK"
echo "historical_canonical_hybrid_v2_regression_top5=36/36"
echo "historical_canonical_hybrid_v2_regression_full_output=35/36"
echo "historical_canonical_hybrid_v2_fresh_holdout=60/60"
echo "historical_canonical_hybrid_v2_performance_correct=18/18"
echo "historical_canonical_hybrid_v2_speedup=0.257592"
echo "historical_canonical_hybrid_v2_slowdown=3.882109"
echo "historical_canonical_hybrid_v2_b3=no_go"
echo "ssw_cpu_oracle_epoch=2"
echo "ssw_cuda_program_epoch=1"
