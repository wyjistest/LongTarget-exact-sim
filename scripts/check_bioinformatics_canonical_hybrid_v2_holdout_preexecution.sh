#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/tests/check_canonical_hybrid_v2_holdout_freeze.py"
PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/scripts/freeze_bioinformatics_canonical_hybrid_v2_holdout.py" \
  --check >/dev/null

summary="$(PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/reproduce/bioinformatics/run_canonical_hybrid_v2.py" \
  --stage fresh-holdout \
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
receipt = json.loads((paper / "canonical_hybrid_v2_holdout_plan_receipt.json").read_text(encoding="utf-8"))
selection = json.loads((paper / "canonical_hybrid_v2_holdout_selection.json").read_text(encoding="utf-8"))

if summary["attempt_count"] != 120 or summary["arm_counts"] != {"A": 60, "H": 60}:
    raise SystemExit("fresh holdout plan shape drift")
if summary["formal_source_data_count"] != 120 or summary["promotion_eligible_count"] != 120:
    raise SystemExit("fresh holdout claim-role drift")
if receipt["workload_count"] != 48 or receipt["validation_count"] != 60:
    raise SystemExit("fresh holdout workload count drift")
if receipt["runtime_revision"] != 2 or receipt["scientific_runtime_changed_from_regression"]:
    raise SystemExit("fresh holdout runtime boundary drift")
if receipt["retry_policy"] != "none" or receipt["replacement_retry_allowed"]:
    raise SystemExit("fresh holdout retry policy drift")
if receipt["b3_speedup_threshold"] != 10.0 or receipt["b3_speedup_threshold_changed"]:
    raise SystemExit("B3 threshold drift")
if selection["prohibited_selection_input_used"] or selection["prior_pilot_outcomes_read"]:
    raise SystemExit("fresh holdout input-only selection drift")
if selection["prior_v1_pilot_exclusion"]["query_source_ordinal_prefix_count"] != 1:
    raise SystemExit("prior pilot query ordinal boundary drift")
if selection["prior_v1_pilot_exclusion"]["target_source_ordinal_prefix_count"] != 1:
    raise SystemExit("prior pilot target ordinal boundary drift")
if selection["prior_v1_pilot_exclusion"]["identity_list_used"]:
    raise SystemExit("prior pilot exclusion became an identity list")

with (paper / "canonical_hybrid_v2_holdout_plan.tsv").open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
by_validation = {}
for row in rows:
    by_validation.setdefault(row["validation_id"], []).append(row)
if len(by_validation) != 60:
    raise SystemExit("fresh holdout validation grouping drift")
for validation_id, attempts in by_validation.items():
    if [row["arm"] for row in attempts] != ["A", "H"]:
        raise SystemExit(f"A/H execution order drift: {validation_id}")
    authority, hybrid = attempts
    if hybrid["authority_reference"] != authority["attempt_id"]:
        raise SystemExit(f"paired authority reference drift: {validation_id}")
    if authority["query_path"] != hybrid["query_path"] or authority["target_path"] != hybrid["target_path"]:
        raise SystemExit(f"paired input drift: {validation_id}")

historical = {
    "phase2_decision.md": "44167694cc44b6e0b46cae598f4b90451806ba7ef902eebdf9858076a859b9b6",
    "phase3_postpilot_decision.json": "471898d688386f46b4e7f13b932b6b4f9874d9ed74641240b5c2fd4ad71851fe",
    "canonical_hybrid_v2_regression_receipt.json": "d75b57609eeed12761ab0e9312a1dfe7bc4826cc5a77ee8e5c2c58fe915b34ae",
}
for name, expected in historical.items():
    if hashlib.sha256((paper / name).read_bytes()).hexdigest() != expected:
        raise SystemExit(f"historical evidence drift: {name}")
PY

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "Bioinformatics canonical-hybrid-v2 fresh holdout preexecution checks OK"
