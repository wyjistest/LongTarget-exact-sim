#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/scripts/collect_bioinformatics_canonical_hybrid_v2_regression.py" \
  --check >/dev/null

python3 - "$ROOT" <<'PY'
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
paper = root / "paper/bioinformatics"
receipt = json.loads((paper / "canonical_hybrid_v2_regression_receipt.json").read_text(encoding="utf-8"))
decision = (paper / "canonical_hybrid_v2_regression_decision.md").read_text(encoding="utf-8")
if receipt["result_status"] != "regression_pass_not_promotion":
    raise SystemExit("regression result status drift")
if any(receipt[key] != 36 for key in (
    "score_clustered_top5_equal",
    "stability_clustered_top5_equal",
    "nt_clustered_top5_equal",
    "all_three_clustered_top5_equal",
)):
    raise SystemExit("declared regression count drift")
if receipt["full_output_equal"] != 35 or receipt["full_output_contract_claimed"]:
    raise SystemExit("full-output diagnostic boundary drift")
if receipt["regression_is_promotion_evidence"]:
    raise SystemExit("regression was promoted")
if not receipt["snapshot_frozen_files_intact"]:
    raise SystemExit("frozen snapshot source identity drift")
if receipt["snapshot_file_set_exact_after_execution"]:
    raise SystemExit("snapshot bytecode-cache audit note disappeared")
if receipt["snapshot_postfreeze_extra_file_class"] != "python_bytecode_cache_only":
    raise SystemExit("snapshot extra-file classification drift")
if len(receipt["snapshot_postfreeze_extra_files"]) != 2:
    raise SystemExit("snapshot bytecode-cache file count drift")
if receipt["b3_speedup_threshold"] != 10.0 or receipt["b3_speedup_threshold_changed"]:
    raise SystemExit("B3 threshold drift")

frozen_collector = subprocess.run(
    [
        "git",
        "-C",
        str(root),
        "show",
        "5d0c833a8dad7e2e081346951b89c56d3ad0183b:scripts/collect_bioinformatics_canonical_hybrid_v2_regression.py",
    ],
    check=True,
    stdout=subprocess.PIPE,
).stdout
if hashlib.sha256(frozen_collector).hexdigest() != receipt["collector_sha256"]:
    raise SystemExit("frozen regression collector identity drift")

required_decision_text = (
    "decision = regression_pass_not_promotion",
    "score clustered Top-5 canonical rows = 36/36",
    "stability clustered Top-5 canonical rows = 36/36",
    "Nt clustered Top-5 canonical rows = 36/36",
    "Full TFOsorted output was identical in 35/36 attempts.",
    "Canonical-hybrid-v2 is therefore not a validated full-output replacement.",
    "The next authorized correctness step is a frozen fresh independent holdout.",
    "gpu-traceback-v1 Phase 2 = verified_only_contract",
    "sequential verified-v1 Phase 3 B3 = no_go",
    "The original B3 threshold remains H/A speedup `>=10x`",
)
for statement in required_decision_text:
    if statement not in decision:
        raise SystemExit(f"regression decision boundary drift: {statement}")

checksum_rows = {}
for line in (paper / "canonical_hybrid_v2_regression.sha256").read_text(encoding="ascii").splitlines():
    digest, name = line.split()
    checksum_rows[name] = digest
for name, expected in checksum_rows.items():
    digest = hashlib.sha256((paper / name).read_bytes()).hexdigest()
    if digest != expected:
        raise SystemExit(f"regression evidence checksum drift: {name}")

with (paper / "canonical_hybrid_v2_regression_results.tsv").open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
if len(rows) != 36:
    raise SystemExit("regression result row count drift")
if sum(row["full_output_equal"] == "1" for row in rows) != 35:
    raise SystemExit("full-output result count drift")

historical = {
    "phase2_decision.md": "44167694cc44b6e0b46cae598f4b90451806ba7ef902eebdf9858076a859b9b6",
    "phase3_postpilot_decision.json": "471898d688386f46b4e7f13b932b6b4f9874d9ed74641240b5c2fd4ad71851fe",
}
for name, expected in historical.items():
    if hashlib.sha256((paper / name).read_bytes()).hexdigest() != expected:
        raise SystemExit(f"historical decision drift: {name}")
PY

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "Bioinformatics canonical-hybrid-v2 regression evidence checks OK"
