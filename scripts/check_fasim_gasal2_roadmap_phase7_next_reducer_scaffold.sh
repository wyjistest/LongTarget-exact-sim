#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_next_reducer/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 next reducer characterization report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(), delimiter="\t"))
if len(rows) != 1:
    raise SystemExit(f"expected one scaffold row, got {len(rows)}")
row = rows[0]
if row.get("workload") != "phase7_short_query_smoke":
    raise SystemExit(f"unexpected workload: {row.get('workload')}")
if row.get("digest_match") != "1":
    raise SystemExit("scaffold smoke must preserve digest")
if row.get("false_negative_scoreinfos") != "0":
    raise SystemExit("scaffold smoke must have zero false negatives")
if row.get("triplex_mismatches") != "0":
    raise SystemExit("scaffold smoke must have zero triplex mismatches")
candidate = int(row.get("candidate_align_attempts", "-1"))
reference = int(row.get("reference_align_attempts", "-1"))
if candidate <= 0 or reference <= 0:
    raise SystemExit("scaffold smoke must report positive align attempts")
if candidate >= reference:
    raise SystemExit("bounded reducer smoke must reduce align attempts")
if row.get("decision") != "phase7_next_reducer_go":
    raise SystemExit(f"unexpected bounded reducer decision: {row.get('decision')}")

print("phase7_next_reducer_scaffold_gate=bounded_go_not_broad")
print("phase7_next_reducer_env_gate=pass")
print("phase7_next_reducer_runtime_smoke=pass")
print("phase7_next_reducer_characterization=pass")
print("phase7_next_reducer_digest_match=1")
print("phase7_next_reducer_false_negative_scoreinfos=0")
print("phase7_next_reducer_triplex_mismatches=0")
print(f"phase7_next_reducer_candidate_align_attempts={candidate}")
print(f"phase7_next_reducer_reference_align_attempts={reference}")
print("phase7_next_reducer_current_decision=bounded_go_needs_neat1_broad_gate")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
