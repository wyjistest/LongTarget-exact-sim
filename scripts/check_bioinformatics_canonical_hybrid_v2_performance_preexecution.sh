#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/tests/check_canonical_hybrid_v2_performance_freeze.py"
PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/scripts/freeze_bioinformatics_canonical_hybrid_v2_performance.py" \
  --check >/dev/null

summary="$(PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/reproduce/bioinformatics/run_canonical_hybrid_v2.py" \
  --stage performance-pilot \
  --plan-only)"

python3 - "$ROOT" "$summary" <<'PY'
import csv
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
summary = json.loads(sys.argv[2])
paper = root / "paper/bioinformatics"
receipt = json.loads((paper / "canonical_hybrid_v2_performance_plan_receipt.json").read_text(encoding="utf-8"))
selection = json.loads((paper / "canonical_hybrid_v2_performance_selection.json").read_text(encoding="utf-8"))
correctness = json.loads((paper / "canonical_hybrid_v2_holdout_selection.json").read_text(encoding="utf-8"))

if summary["attempt_count"] != 36 or summary["arm_counts"] != {"A": 18, "H": 18}:
    raise SystemExit("performance plan shape drift")
if summary["formal_source_data_count"] != 36 or summary["promotion_eligible_count"] != 36:
    raise SystemExit("performance claim-role drift")
if receipt["workload_count"] != 6 or receipt["validation_count"] != 18:
    raise SystemExit("performance workload count drift")
if receipt["performance_speedup_threshold"] != 10.0 or receipt["performance_speedup_threshold_changed"]:
    raise SystemExit("performance threshold drift")
if receipt["lower_substitute_threshold_allowed"]:
    raise SystemExit("lower substitute threshold was enabled")
if selection["prohibited_selection_input_used"] or selection["correctness_results_or_timings_read"]:
    raise SystemExit("performance input-only selection drift")

used_queries = {int(row["source_ordinal"]) for row in correctness["selected_queries"]}
used_targets = {int(row["source_ordinal"]) for row in correctness["selected_targets"]}
selected_queries = {int(row["source_ordinal"]) for row in selection["selected_queries"]}
selected_targets = {int(row["source_ordinal"]) for row in selection["selected_targets"]}
if used_queries & selected_queries or used_targets & selected_targets:
    raise SystemExit("performance/correctness input partition overlap")

with (paper / "canonical_hybrid_v2_performance_plan.tsv").open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
by_validation = {}
for row in rows:
    by_validation.setdefault(row["validation_id"], []).append(row)
if len(by_validation) != 18:
    raise SystemExit("performance validation grouping drift")
for validation_id, attempts in by_validation.items():
    if [row["arm"] for row in attempts] != ["A", "H"]:
        raise SystemExit(f"performance A/H order drift: {validation_id}")
    if attempts[1]["authority_reference"] != attempts[0]["attempt_id"]:
        raise SystemExit(f"performance paired authority drift: {validation_id}")

historical = {
    "phase2_decision.md": "44167694cc44b6e0b46cae598f4b90451806ba7ef902eebdf9858076a859b9b6",
    "phase3_postpilot_decision.json": "471898d688386f46b4e7f13b932b6b4f9874d9ed74641240b5c2fd4ad71851fe",
    "canonical_hybrid_v2_regression_receipt.json": "d75b57609eeed12761ab0e9312a1dfe7bc4826cc5a77ee8e5c2c58fe915b34ae",
    "canonical_hybrid_v2_holdout_receipt.json": "1b370b0d85f721dedf20a9eaab7ca19fa2e5245396ca3c331e88958cafe2d77c",
}
for name, expected in historical.items():
    if hashlib.sha256((paper / name).read_bytes()).hexdigest() != expected:
        raise SystemExit(f"historical evidence drift: {name}")
PY

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "Bioinformatics canonical-hybrid-v2 performance preexecution checks OK"
