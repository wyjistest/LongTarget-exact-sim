#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/scripts/collect_bioinformatics_canonical_hybrid_v2_performance.py" \
  --check >/dev/null

python3 - "$ROOT" <<'PY'
import csv
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
paper = root / "paper/bioinformatics"
receipt = json.loads((paper / "canonical_hybrid_v2_performance_receipt.json").read_text(encoding="utf-8"))
decision = (paper / "canonical_hybrid_v2_performance_decision.md").read_text(encoding="utf-8")

if receipt["result_status"] != "performance_promotion_no_go" or receipt["performance_gate_passed"]:
    raise SystemExit("performance decision drift")
if receipt["primary_aggregate_speedup"] >= 10.0 or receipt["primary_gate_passed"]:
    raise SystemExit("primary performance gate drift")
if receipt["secondary_projected_two_worker_speedup"] >= 10.0 or receipt["secondary_gate_passed"]:
    raise SystemExit("secondary performance gate drift")
if receipt["performance_speedup_threshold"] != 10.0 or receipt["performance_speedup_threshold_changed"]:
    raise SystemExit("performance threshold drift")
if receipt["lower_substitute_threshold_introduced"]:
    raise SystemExit("lower substitute threshold appeared")
if receipt["b3_v2_status"] != "no_go" or receipt["large_b3_v2_application_run_authorized"]:
    raise SystemExit("large B3-v2 run was incorrectly authorized")
for field in (
    "score_clustered_top5_equal",
    "stability_clustered_top5_equal",
    "nt_clustered_top5_equal",
    "all_three_clustered_top5_equal",
    "full_output_equal_diagnostic",
):
    if receipt[field] != 18:
        raise SystemExit(f"performance correctness count drift: {field}")
if any(receipt[field] for field in ("declared_contract_mismatches", "technical_failures", "fallbacks", "timeouts", "ooms")):
    raise SystemExit("performance technical/scientific failure drift")

required_decision_text = (
    "performance_gate = no_go",
    "required speedup = 10.000000x",
    "canonical-hybrid-v2 correctness = pass",
    "canonical-hybrid-v2 performance = no_go",
    "B3-v2 = no_go",
    "large B3-v2 application run authorized = false",
    "canonical-hybrid-v2 rescue track = closed",
    "submission route = retain CSBJ fallback",
    "gpu-traceback-v1 Phase 2 = verified_only_contract",
    "sequential verified-v1 Phase 3 B3 = no_go",
)
for statement in required_decision_text:
    if statement not in decision:
        raise SystemExit(f"performance decision boundary drift: {statement}")

with (paper / "canonical_hybrid_v2_performance_results.tsv").open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
if len(rows) != 18 or sum(row["declared_contract_clean"] == "1" for row in rows) != 18:
    raise SystemExit("performance result table drift")

checksums = {}
for line in (paper / "canonical_hybrid_v2_performance.sha256").read_text(encoding="ascii").splitlines():
    digest, name = line.split()
    checksums[name] = digest
for name, expected in checksums.items():
    if hashlib.sha256((paper / name).read_bytes()).hexdigest() != expected:
        raise SystemExit(f"performance evidence checksum drift: {name}")

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

echo "Bioinformatics canonical-hybrid-v2 performance evidence checks OK"
