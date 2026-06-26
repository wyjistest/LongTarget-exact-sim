#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROADMAP="$ROOT/docs/fasim_gasal2_goal_completion_roadmap.md"
RECOMMENDED="$ROOT/docs/fasim_gasal2_top5_recommended_runtime.md"
PRODUCT="$ROOT/docs/fasim_gasal2_top5_product_readiness.md"
MAKEFILE="$ROOT/Makefile"

for path in "$ROADMAP" "$RECOMMENDED" "$PRODUCT" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing Phase 1 scoped contract dependency: $path" >&2
    exit 1
  fi
done

python3 - "$ROADMAP" "$RECOMMENDED" "$PRODUCT" "$MAKEFILE" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path


roadmap = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
recommended = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
product = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")

required_roadmap = [
    "Phase 1: Lock The Scoped Product Contract",
    "gasal2_top5_column_pruned_scoreinfo_artifact_v1",
    "topk_summary.tsv",
    "topk_rows.tsv",
    "topk-TFOsorted.lite",
    "report.json",
    "run_manifest.json",
    "reference-backed TFO archive",
    "restore-on-demand TFOsorted",
    "make check-fasim-gasal2-top5-recommended-runtime",
    "make check-fasim-gasal2-top5-product-readiness",
    "make check-fasim-gasal2-top5-scoped-completion-candidate",
    "default-off opt-in",
    "--gasal2-top5-column-pruned-scoreinfo",
    "--group-target-records 32",
    "full `.lite` output is not contract output",
    "final all-row TFO equivalence is not claimed",
    "not `aligner.Align()` replacement",
    "not GPU endpoint/CIGAR/traceback authority",
    "not broad production default",
    "scoped_product_status = ready_if_user_accepts_scope",
    "full objective remains open unless the user accepts scoped completion",
]
missing = [phrase for phrase in required_roadmap if phrase not in roadmap]
if missing:
    raise SystemExit(
        "roadmap missing Phase 1 scoped contract phrases: " + ", ".join(missing)
    )

for name, text in (("recommended", recommended), ("product", product)):
    for phrase in (
        "--gasal2-top5-column-pruned-scoreinfo",
        "result_contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1",
        "default-off opt-in",
        "topk_summary.tsv",
        "topk_rows.tsv",
        "topk-TFOsorted.lite",
        "report.json",
        "run_manifest.json",
        "full objective remains open",
    ):
        if phrase not in text:
            raise SystemExit(f"{name} doc missing scoped phrase: {phrase}")

for target in (
    "check-fasim-gasal2-top5-recommended-runtime",
    "check-fasim-gasal2-top5-product-readiness",
    "check-fasim-gasal2-top5-scoped-completion-candidate",
    "check-fasim-gasal2-top5-release-smoke",
):
    if not re.search(rf"^{re.escape(target)}:", makefile, flags=re.MULTILINE):
        raise SystemExit(f"Makefile missing scoped contract target: {target}")

print("phase1_scoped_contract_gate=ready")
print("scoped_contract_named=1")
print("default_off_runtime_documented=1")
print("contract_artifacts_documented=1")
print("non_claims_documented=1")
print("full_objective_still_open=1")
PY
