#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_long_query_final"}"
RUN_PHASE_GATES="${RUN_PHASE_GATES:-1}"
DOC="$ROOT/docs/fasim_gasal2_long_query_final_decision.md"
ADVANCED="$ROOT/docs/longtarget_advanced_runtime_details.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
GOAL="$ROOT/goal.md"

if [[ "$RUN_PHASE_GATES" != "0" && "$RUN_PHASE_GATES" != "1" ]]; then
  echo "RUN_PHASE_GATES must be 0 or 1" >&2
  exit 1
fi
for path in "$DOC" "$ADVANCED" "$MATRIX" "$GOAL"; do
  if [[ ! -s "$path" ]]; then
    echo "missing final-decision dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

if [[ "$RUN_PHASE_GATES" == "1" ]]; then
  env -u WORK make -C "$ROOT" check-fasim-gasal2-long-query-phase0 \
    >"$WORK/phase0.log" 2>&1
  env -u WORK make -C "$ROOT" check-fasim-gasal2-segmented-archive-first \
    >"$WORK/phase1.log" 2>&1
  env -u WORK make -C "$ROOT" check-fasim-gasal2-segment-ownership \
    >"$WORK/phase2.log" 2>&1
  env -u WORK make -C "$ROOT" check-fasim-gasal2-multi-segment-context-phase3 \
    >"$WORK/phase3.log" 2>&1
  env -u WORK make -C "$ROOT" check-fasim-gasal2-exact-column-phase5 \
    >"$WORK/phase5.log" 2>&1
  env -u WORK make -C "$ROOT" check-fasim-gasal2-traceback-certificate-phase6 \
    >"$WORK/phase6.log" 2>&1
  env -u WORK make -C "$ROOT" check-fasim-gasal2-long-query-integrated-phase7 \
    >"$WORK/phase7.log" 2>&1
  for phase in 0 1 2 3 5 6 7; do
    if [[ ! -s "$WORK/phase${phase}.log" ]]; then
      echo "missing aggregate phase log: $WORK/phase${phase}.log" >&2
      exit 1
    fi
  done
fi

python3 - "$DOC" "$ADVANCED" "$MATRIX" "$GOAL" \
  "$ROOT/scripts/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot.sh" \
  "$ROOT/fasim/gasal2_align_bridge.cpp" "$ROOT/Makefile" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path


doc = Path(sys.argv[1]).read_text(encoding="utf-8")
advanced = Path(sys.argv[2]).read_text(encoding="utf-8")
matrix_path = Path(sys.argv[3])
goal = Path(sys.argv[4]).read_text(encoding="utf-8")
runner = Path(sys.argv[5]).read_text(encoding="utf-8")
bridge = Path(sys.argv[6]).read_text(encoding="utf-8")
makefile = Path(sys.argv[7]).read_text(encoding="utf-8")

state: dict[str, str] = {}
for raw in goal.splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
expected_status = {
    "phase_0_status": "pass",
    "phase_1_status": "pass",
    "phase_2_status": "no_go",
    "phase_3_status": "no_go",
    "phase_4_status": "no_go",
    "phase_5_status": "pass",
    "phase_6_status": "no_go",
    "phase_7_status": "no_go",
    "phase_8_status": "pass",
}
for key, expected in expected_status.items():
    if state.get(key) != expected:
        raise SystemExit(f"final phase status mismatch: {key}={state.get(key)!r}")
if any(value == "blocked" for key, value in state.items() if key.startswith("phase_")):
    raise SystemExit("final phase ledger still contains blocked")
required_state = {
    "active_phase": "complete",
    "last_completed_phase": "8",
    "last_decision": "long_query_architecture_no_go_with_complete_evidence",
    "last_evidence_doc": "docs/fasim_gasal2_long_query_final_decision.md",
    "last_test_command": "make check-fasim-gasal2-long-query-final",
    "last_commit": "docs: close the scoped GASAL2 long-query architecture decision",
}
for key, expected in required_state.items():
    if state.get(key) != expected:
        raise SystemExit(f"final goal state mismatch: {key}={state.get(key)!r}")

required_doc = (
    "long_query_architecture_no_go_with_complete_evidence",
    "Phase 4 was not implemented",
    "What passed",
    "What was no-go",
    "All long-query additions remain default-off",
    "Supported scope",
    "Unsupported scope",
    "Resource boundary",
    "There is no recommended production invocation",
    "Fallback behavior",
    "Correctness interpretation",
    "Known limitations",
    "Next valid research question",
    "full segmented KCNQ1OT1 x chr22 integrated candidate=not run",
    "speedup=1.089028x",
    "archive/text reduction=6.377893x",
)
for phrase in required_doc:
    if phrase not in doc:
        raise SystemExit(f"final decision doc missing: {phrase}")

forbidden_claims = (
    "grid stability == full equivalence",
    "top5 clean == full output clean",
    "archive restore == aligner replacement",
    "KCNQ1OT1 result == universal long-query result",
    "kernel speedup == end-to-end speedup",
    "fallback-heavy == clean GPU fast path",
    "full KCNQ1OT1 equivalence validated",
    "full-length KCNQ1OT1 acceleration validated",
)
for claim in forbidden_claims:
    if claim in doc or claim in advanced:
        raise SystemExit(f"forbidden final claim present: {claim}")

required_advanced = (
    "There is no promoted GASAL2 preset for full-length segmented long queries.",
    "1.089028x",
    "full segmented KCNQ1OT1 x chr22 was not run",
    "it is not a production recommendation",
    "FASIM_GASAL2_TRACEBACK_CERTIFICATE_SHADOW=0",
)
for phrase in required_advanced:
    if phrase not in advanced:
        raise SystemExit(f"advanced runtime note missing: {phrase}")

with matrix_path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
by_name = {row["workload"]: row for row in rows}
max8 = by_name.get("kcnq1ot1_max8_integrated")
if not max8:
    raise SystemExit("workload matrix is missing integrated max8")
if (
    max8["status"] != "no_go"
    or max8["scope"] != "bounded_dual_grid"
    or max8["row_equal"] != "true"
    or max8["top5_equal"] != "true"
    or max8["speedup"] != "1.089028"
    or max8["fallbacks"] != "0"
):
    raise SystemExit(f"workload matrix max8 row drifted: {max8}")

for phrase in (
    'RESUME="${RESUME:-0}"',
    'EXACT_SCOREINFO_PRUNED="${EXACT_SCOREINFO_PRUNED:-0}"',
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=0",
    "FASIM_GASAL2_TRACEBACK_CERTIFICATE_SHADOW=0",
):
    if phrase not in runner:
        raise SystemExit(f"runner default/fail-closed contract missing: {phrase}")
for forbidden_runtime in (
    "FASIM_GASAL2_TRACEBACK_CERTIFICATE_REAL_SKIP",
    "fixed traceback score threshold is safe",
):
    if forbidden_runtime in runner or forbidden_runtime in bridge:
        raise SystemExit(f"forbidden runtime path present: {forbidden_runtime}")
if "check-fasim-gasal2-long-query-final:" not in makefile:
    raise SystemExit("Makefile is missing final aggregate target")

print("ok")
PY

git -C "$ROOT" diff --check
echo "GASAL2 long-query architecture final decision OK"
