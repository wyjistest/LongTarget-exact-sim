#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_next_reducer/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 next reducer report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(), delimiter="\t"))
if not rows:
    raise SystemExit("empty report")

for row in rows:
    required = [
        "workload",
        "digest_match",
        "false_negative_scoreinfos",
        "triplex_mismatches",
        "candidate_align_attempts",
        "reference_align_attempts",
        "candidate_vs_baseline",
        "decision",
    ]
    for key in required:
        if key not in row:
            raise SystemExit(f"missing column: {key}")

go_rows = [row for row in rows if row["decision"] == "phase7_next_reducer_go"]
if go_rows:
    for row in go_rows:
        if int(row["digest_match"]) != 1:
            raise SystemExit("go row requires digest_match=1")
        if int(row["false_negative_scoreinfos"]) != 0:
            raise SystemExit("go row requires false_negative_scoreinfos=0")
        if int(row["triplex_mismatches"]) != 0:
            raise SystemExit("go row requires triplex_mismatches=0")
        if int(row["candidate_align_attempts"]) >= int(row["reference_align_attempts"]):
            raise SystemExit("go row requires align attempt reduction")
    print("phase7_next_reducer_result=go")
else:
    print("phase7_next_reducer_result=no_go")
print("ok")
PY
