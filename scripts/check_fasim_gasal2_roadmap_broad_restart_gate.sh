#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
BROAD_GATE="$ROOT/docs/fasim_gasal2_broad_path_architecture_gate.md"
MATRIX="$ROOT/docs/fasim_gasal2_workload_matrix.tsv"
DECIDER="$ROOT/scripts/decide_fasim_gasal2_goal_completion.py"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_roadmap_broad_restart_gate"}"

for path in "$ROADMAP" "$BROAD_GATE" "$MATRIX" "$DECIDER"; do
  if [[ ! -s "$path" ]]; then
    echo "missing broad restart gate dependency: $path" >&2
    exit 1
  fi
done

rm -rf "$WORK"
mkdir -p "$WORK"

python3 "$DECIDER" --matrix "$MATRIX" >"$WORK/completion_decision.txt"

python3 - "$ROADMAP" "$BROAD_GATE" "$MATRIX" "$WORK/completion_decision.txt" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path


roadmap = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
broad_gate = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
matrix_path = Path(sys.argv[3])
decision_lines = Path(sys.argv[4]).read_text(encoding="utf-8").splitlines()
decision = dict(line.split("=", 1) for line in decision_lines if "=" in line)

with matrix_path.open(newline="") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

by_workload = {row["workload"]: row for row in rows}
claimed = [row for row in rows if row.get("scope") == "claimed"]
unclaimed_or_blocked = [
    row for row in rows if row.get("scope") in {"unclaimed", "blocked"}
]

required_decision = {
    "scoped_product_status": "ready_if_user_accepts_scope",
    "broad_objective_status": "open",
    "broad_restart_required": "1",
    "claimed_workloads_clean": "1",
    "broad_gate_rows_clean": "0",
    "blocked_or_unclaimed_workloads": "3",
    "final_goal_decision": "not_complete_without_user_scope_acceptance",
    "must_not_call_update_goal_complete": "1",
}
for key, expected in required_decision.items():
    actual = decision.get(key)
    if actual != expected:
        raise SystemExit(
            f"completion decision mismatch for {key}: expected {expected}, got {actual}"
        )

if not claimed:
    raise SystemExit("workload matrix has no claimed scoped rows")
if any(row.get("status") != "pass" for row in claimed):
    raise SystemExit("workload matrix has a failing claimed scoped row")
if any(row.get("contract") == "broad_replacement" for row in claimed):
    raise SystemExit("workload matrix already claims broad_replacement")

neat1 = by_workload.get("neat1_first64")
if not neat1:
    raise SystemExit("workload matrix missing neat1_first64 broad gate row")
if neat1.get("scope") != "unclaimed" or neat1.get("status") != "fallback":
    raise SystemExit(
        "neat1_first64 must remain unclaimed/fallback until Phase 7 is satisfied"
    )
if "query_len 22767 exceeds GASAL2 max query" not in neat1.get("notes", ""):
    raise SystemExit("neat1_first64 row missing long-query guard evidence")

malat1 = by_workload.get("malat1_first8")
if not malat1:
    raise SystemExit("workload matrix missing malat1_first8 blocked row")
if malat1.get("scope") != "blocked" or malat1.get("status") != "fail":
    raise SystemExit(
        "malat1_first8 must remain blocked/fail in the broad gate matrix"
    )

required_roadmap = [
    "Phase 7: Broad Architecture Restart Only If Needed",
    "reduce both GPU scoreInfo work and CPU realpath extend/align work",
    "avoid current replay-heavy consumer shape",
    "prove full output equivalence before performance claims",
    "current selected-only replay",
    "current prefix replay with unchanged align attempts",
    "current segmented traceback",
    "current exact tiling or overlap tiling as real path",
    "GPU endpoint/CIGAR/traceback authority without separate proof",
    "must_not_call_update_goal_complete = 1",
    "The current matrix does not satisfy the Phase 7 broad gate",
    "Broad completion requires a new architecture",
]
missing_roadmap = [phrase for phrase in required_roadmap if phrase not in roadmap]
if missing_roadmap:
    raise SystemExit(
        "roadmap missing Phase 7 broad restart phrases: "
        + ", ".join(missing_roadmap)
    )

required_broad_gate = [
    "decision = broad_path_current_architecture_no_go",
    "NEAT1 first64 is the broad-path gate",
    "candidate_vs_baseline > 1.0x",
    "realpath_extend_align_attempts materially reduced or replaced",
    "kernel-only improvement is the main change",
    "selected-only replay is the consumer",
    "prefix replay is required and align attempts are not reduced",
    "current selector/global-state NEAT1 path",
    "segmented no-last replay",
    "exact tiling",
    "overlap tiling",
    "score-prepass state-machine consumer trust",
    "MALAT1 scoped two-contract runtime as broad long-query replacement",
    "top5 artifact path as full-output replacement",
    "reduce scoreInfo/align attempts before replaying CPU aligner state",
]
missing_broad_gate = [
    phrase for phrase in required_broad_gate if phrase not in broad_gate
]
if missing_broad_gate:
    raise SystemExit(
        "broad architecture gate missing restart phrases: "
        + ", ".join(missing_broad_gate)
    )

print("roadmap_broad_restart_gate=current_architecture_no_go")
print(f"broad_objective_status={decision['broad_objective_status']}")
print(f"broad_restart_required={decision['broad_restart_required']}")
print(f"claimed_workloads_clean={decision['claimed_workloads_clean']}")
print(f"broad_gate_rows_clean={decision['broad_gate_rows_clean']}")
print(f"blocked_or_unclaimed_workloads={len(unclaimed_or_blocked)}")
print(f"neat1_first64_status={neat1['status']}")
print(f"malat1_first8_status={malat1['status']}")
print("forbidden_restarts_checked=1")
print("phase7_next_architecture_required=1")
print("must_not_call_update_goal_complete=1")
PY
