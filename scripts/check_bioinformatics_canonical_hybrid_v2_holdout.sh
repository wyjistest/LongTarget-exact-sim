#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/scripts/collect_bioinformatics_canonical_hybrid_v2_holdout.py" \
  --check >/dev/null

python3 - "$ROOT" <<'PY'
import csv
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
paper = root / "paper/bioinformatics"
receipt = json.loads((paper / "canonical_hybrid_v2_holdout_receipt.json").read_text(encoding="utf-8"))
decision = (paper / "canonical_hybrid_v2_holdout_decision.md").read_text(encoding="utf-8")

if receipt["result_status"] != "correctness_promotion_pass" or not receipt["correctness_promotion_passed"]:
    raise SystemExit("fresh holdout correctness decision drift")
for field in (
    "score_clustered_top5_equal",
    "stability_clustered_top5_equal",
    "nt_clustered_top5_equal",
    "all_three_clustered_top5_equal",
    "full_output_equal_diagnostic",
):
    if receipt[field] != 60:
        raise SystemExit(f"fresh holdout equality count drift: {field}")
if any(receipt[field] for field in ("declared_contract_mismatches", "technical_failures", "fallbacks", "timeouts", "ooms")):
    raise SystemExit("fresh holdout failure count drift")
if not receipt["snapshot_file_set_exact_after_execution"] or receipt["snapshot_python_bytecode_cache_count"] != 0:
    raise SystemExit("fresh holdout snapshot integrity drift")
if receipt["performance_promotion_assessed"] or receipt["b3_v2_status"] != "pending_performance_pilot":
    raise SystemExit("fresh correctness evidence was used for performance promotion")
if receipt["b3_speedup_threshold"] != 10.0 or receipt["b3_speedup_threshold_changed"]:
    raise SystemExit("B3 threshold drift")

required_decision_text = (
    "correctness_gate = pass",
    "score clustered Top-5 canonical rows = 60/60",
    "stability clustered Top-5 canonical rows = 60/60",
    "Nt clustered Top-5 canonical rows = 60/60",
    "canonical-hybrid-v2 performance = pending fixed A/H pilot",
    "B3-v2 = pending_performance_pilot",
    "The original H/A speedup threshold remains `>=10x`",
    "gpu-traceback-v1 Phase 2 = verified_only_contract",
    "sequential verified-v1 Phase 3 B3 = no_go",
)
for statement in required_decision_text:
    if statement not in decision:
        raise SystemExit(f"fresh holdout decision boundary drift: {statement}")

with (paper / "canonical_hybrid_v2_holdout_results.tsv").open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
if len(rows) != 60 or sum(row["declared_contract_clean"] == "1" for row in rows) != 60:
    raise SystemExit("fresh holdout result table drift")

checksums = {}
for line in (paper / "canonical_hybrid_v2_holdout.sha256").read_text(encoding="ascii").splitlines():
    digest, name = line.split()
    checksums[name] = digest
for name, expected in checksums.items():
    if hashlib.sha256((paper / name).read_bytes()).hexdigest() != expected:
        raise SystemExit(f"fresh holdout evidence checksum drift: {name}")

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

echo "Bioinformatics canonical-hybrid-v2 fresh holdout evidence checks OK"
