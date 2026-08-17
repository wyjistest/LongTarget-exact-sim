#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for relative in \
  config/gasal2_longtarget_contracts.json \
  schemas/gasal2_longtarget_contracts.schema.json \
  paper/bioinformatics/development_query_exclusions.tsv \
  paper/bioinformatics/holdout_selection.json \
  paper/bioinformatics/holdout_manifest.tsv \
  paper/bioinformatics/holdout_manifest.sha256 \
  paper/bioinformatics/holdout_sources.tsv \
  paper/bioinformatics/holdout_protocol.md \
  reproduce/bioinformatics/build_holdout_panel.py \
  reproduce/bioinformatics/fetch_holdout_inputs.sh \
  tests/check_build_bioinformatics_holdout_panel.py \
  tests/check_bioinformatics_phase2_freeze.py; do
  if [[ ! -s "$ROOT/$relative" ]]; then
    echo "missing Bioinformatics Phase 2 freeze dependency: $relative" >&2
    exit 1
  fi
done

python3 "$ROOT/tests/check_build_bioinformatics_holdout_panel.py"
python3 "$ROOT/tests/check_bioinformatics_phase2_freeze.py"
python3 -m py_compile \
  "$ROOT/reproduce/bioinformatics/build_holdout_panel.py" \
  "$ROOT/tests/check_build_bioinformatics_holdout_panel.py" \
  "$ROOT/tests/check_bioinformatics_phase2_freeze.py"
bash -n "$ROOT/reproduce/bioinformatics/fetch_holdout_inputs.sh"
python3 -m json.tool "$ROOT/config/gasal2_longtarget_contracts.json" >/dev/null
python3 -m json.tool "$ROOT/schemas/gasal2_longtarget_contracts.schema.json" >/dev/null
(cd "$ROOT/paper/bioinformatics" && sha256sum -c holdout_manifest.sha256)

python3 - "$ROOT" <<'PY'
from __future__ import annotations

import csv
import sys
from pathlib import Path


root = Path(sys.argv[1])
with (root / "paper/bioinformatics/holdout_manifest.tsv").open(
    newline="", encoding="utf-8"
) as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))
if len(rows) != 24:
    raise SystemExit(f"expected 24 preregistered holdout rows, found {len(rows)}")
if any(row["status"] != "preregistered_not_run" for row in rows):
    raise SystemExit("holdout freeze contains a row that is not preregistered_not_run")
if {row["run_modes"] for row in rows} != {"authority,candidate,verified"}:
    raise SystemExit("holdout freeze run-mode contract drifted")

print("Bioinformatics Phase 2 holdout freeze checks OK")
print("holdout_workloads=24")
print("holdout_queries=12")
print("representative_repeat_workloads=6")
print("holdout_execution_started=0")
PY

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check
