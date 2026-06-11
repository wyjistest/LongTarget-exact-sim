#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_cpu_authority_candidate_coverage/coverage_report.json"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing CPU-authority candidate coverage report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)

decision = report.get("decision")
require(decision in {"coverage_candidate_go", "coverage_candidate_no_go"},
        f"unexpected decision={decision}")
rows = report.get("rows", [])
require(rows, "report has no rows")
require(int(report.get("row_count", 0)) == len(rows), "row_count mismatch")

false_negative_scoreinfos = int(report["false_negative_scoreinfos"])
candidate_coverage_covered = int(report["candidate_coverage_covered"])
candidate_coverage_selected = int(report["candidate_coverage_selected"])
candidate_align_attempts = int(report["candidate_align_attempts"])
candidate_coverage_reference_align_attempts = int(report["candidate_coverage_reference_align_attempts"])
realpath_extend_align_attempts = int(report["realpath_extend_align_attempts"])
same_scope_cpu_align_reduction = int(report["same_scope_cpu_align_reduction"])
same_scope_cpu_align_reduction_ratio = float(report["same_scope_cpu_align_reduction_ratio"])

require(candidate_coverage_selected > 0, "candidate coverage selected should be positive")
require(candidate_coverage_covered >= 0, "candidate coverage covered should be non-negative")
require(candidate_align_attempts > 0, "candidate align attempts should be positive")
require(candidate_coverage_reference_align_attempts > 0,
        "same-scope reference align attempts should be positive")
require(realpath_extend_align_attempts > 0, "full realpath align attempts should be positive")
require(
    same_scope_cpu_align_reduction ==
    candidate_coverage_reference_align_attempts - candidate_align_attempts,
    "same-scope CPU align reduction mismatch",
)
require(0.0 < same_scope_cpu_align_reduction_ratio <= 1.0,
        "same-scope CPU align reduction ratio outside expected range")

for row in rows:
    for key in (
        "digest_match",
        "false_negative_scoreinfos",
        "covered",
        "selected",
        "candidate_align_attempts",
        "candidate_coverage_reference_align_attempts",
        "same_scope_cpu_align_reduction_ratio",
        "triplex_mismatches",
        "decision",
    ):
        require(key in row, f"row missing {key}")
    selected = int(row["selected"])
    covered = int(row["covered"])
    false_negative = int(row["false_negative_scoreinfos"])
    require(selected > 0, "row selected should be positive")
    require(covered + false_negative == selected,
            "row selected not partitioned by covered/false_negative")
    require(int(row["candidate_attempts"]) <= int(row["attempts"]),
            "row candidate attempts exceed attempts")
    require(int(row["candidate_align_attempts"]) > 0,
            "row candidate align attempts should be positive")
    require(int(row["candidate_coverage_reference_align_attempts"]) > 0,
            "row same-scope reference align attempts should be positive")
    require(float(row["same_scope_cpu_align_reduction_ratio"]) > 0.0,
            "row same-scope CPU align reduction ratio should be positive")

if decision == "coverage_candidate_go":
    require(false_negative_scoreinfos == 0, "candidate go requires false_negative_scoreinfos=0")
    require(candidate_coverage_covered == candidate_coverage_selected,
            "candidate go requires covered=selected")
    require(candidate_align_attempts < candidate_coverage_reference_align_attempts,
            "candidate go requires same-scope CPU align attempt reduction")
    for row in rows:
        require(row["decision"] == "coverage_candidate_go", "candidate go report has no-go row")
        require(int(row["digest_match"]) == 1, "candidate go row digest mismatch")
        require(int(row["triplex_mismatches"]) == 0, "candidate go row triplex mismatch")
else:
    require(
        false_negative_scoreinfos != 0 or
        candidate_coverage_covered != candidate_coverage_selected or
        candidate_align_attempts >= candidate_coverage_reference_align_attempts or
        any(row["decision"] == "coverage_candidate_no_go" for row in rows),
        "coverage_candidate_no_go lacks a no-go reason",
    )

print("decision=" + decision)
print("false_negative_scoreinfos=" + str(false_negative_scoreinfos))
print("candidate_coverage_covered=" + str(candidate_coverage_covered))
print("candidate_coverage_selected=" + str(candidate_coverage_selected))
print("candidate_align_attempts=" + str(candidate_align_attempts))
print("candidate_coverage_reference_align_attempts=" + str(candidate_coverage_reference_align_attempts))
print("realpath_extend_align_attempts=" + str(realpath_extend_align_attempts))
print("same_scope_cpu_align_reduction_ratio=" + f"{same_scope_cpu_align_reduction_ratio:.6f}")
print("ok")
PY
