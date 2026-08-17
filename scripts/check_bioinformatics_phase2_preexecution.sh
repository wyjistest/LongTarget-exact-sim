#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for relative in \
  paper/bioinformatics/frozen_contract_matrix.tsv \
  paper/bioinformatics/mismatch_feature_matrix.tsv \
  paper/bioinformatics/mismatch_analysis.md \
  reproduce/bioinformatics/analyze_frozen_contracts.py \
  tests/check_analyze_bioinformatics_frozen_contracts.py \
  paper/bioinformatics/holdout_execution_protocol.md \
  reproduce/bioinformatics/run_holdout.py \
  tests/check_run_bioinformatics_holdout.py \
  paper/bioinformatics/submission_manifest.tsv; do
  if [[ ! -s "$ROOT/$relative" ]]; then
    echo "missing Bioinformatics Phase 2 pre-execution artifact: $relative" >&2
    exit 1
  fi
done

python3 "$ROOT/tests/check_analyze_bioinformatics_frozen_contracts.py"
python3 "$ROOT/tests/check_run_bioinformatics_holdout.py"
python3 -m py_compile \
  "$ROOT/reproduce/bioinformatics/run_holdout.py" \
  "$ROOT/tests/check_run_bioinformatics_holdout.py"

python3 - "$ROOT" <<'PY'
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path


root = Path(sys.argv[1]).resolve()
runner_path = root / "reproduce/bioinformatics/run_holdout.py"
spec = importlib.util.spec_from_file_location("phase2_holdout_preexecution", runner_path)
if spec is None or spec.loader is None:
    raise SystemExit("could not load Phase 2 holdout runner")
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)
plan = runner.build_plan(root / "paper/bioinformatics/holdout_manifest.tsv")
expected = {
    "workload_count": 24,
    "formal_attempt_count": 36,
    "top_level_run_count": 108,
    "backend_execution_count": 144,
}
for field, value in expected.items():
    if plan[field] != value:
        raise SystemExit(f"holdout plan count drift for {field}: {plan[field]}")

protocol = (root / "paper/bioinformatics/holdout_execution_protocol.md").read_text(
    encoding="utf-8"
)
for phrase in (
    "pilot workload = hq01_ht01",
    "no automatic or replacement retry",
    "formal execution requires a checksum-valid pilot receipt",
    "runtime parameters may not change after pilot or holdout results",
    "`.paper-artifacts/bioinformatics-phase2-holdout-v1`",
    "pinned runner is the execution authority",
):
    if phrase not in protocol:
        raise SystemExit(f"execution protocol is missing frozen rule: {phrase}")

expected_paths = {
    "paper/bioinformatics/frozen_contract_matrix.tsv",
    "paper/bioinformatics/mismatch_feature_matrix.tsv",
    "paper/bioinformatics/mismatch_analysis.md",
    "reproduce/bioinformatics/analyze_frozen_contracts.py",
    "tests/check_analyze_bioinformatics_frozen_contracts.py",
    "paper/bioinformatics/holdout_execution_protocol.md",
    "reproduce/bioinformatics/run_holdout.py",
    "tests/check_run_bioinformatics_holdout.py",
    "scripts/check_bioinformatics_phase2_preexecution.sh",
}
with (root / "paper/bioinformatics/submission_manifest.tsv").open(
    newline="", encoding="utf-8"
) as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    expected_schema = [
        "artifact_id",
        "path",
        "phase",
        "artifact_class",
        "authority",
        "freeze_or_epoch",
        "required",
        "status",
    ]
    if reader.fieldnames != expected_schema:
        raise SystemExit("submission manifest schema drift")
    rows = list(reader)
by_path = {row["path"]: row for row in rows}
missing = sorted(expected_paths - set(by_path))
if missing:
    raise SystemExit("submission manifest is missing: " + ",".join(missing))
if any(by_path[path]["phase"] != "2" or by_path[path]["status"] != "pass" for path in expected_paths):
    raise SystemExit("submission manifest Phase 2 runner status drift")

canonical_root = root / ".paper-artifacts/bioinformatics-phase2-holdout-v1"
if runner.CANONICAL_ARTIFACT_ROOT.resolve() != canonical_root.resolve():
    raise SystemExit("runner canonical artifact root drift")
markers = runner.execution_start_markers(canonical_root)
if markers:
    rendered = []
    for marker in markers:
        relative = marker.relative_to(canonical_root)
        if marker.name == "attempt-complete.json":
            kind = "complete-receipt"
        elif marker.name == "attempt-config.json":
            kind = "attempt-config"
        elif ".partial." in marker.name:
            kind = "partial-attempt"
        else:
            kind = "other-execution-start-marker"
        rendered.append(f"{kind}:{relative}")
    raise SystemExit(
        "canonical pilot/formal holdout execution has started: "
        + ",".join(rendered)
    )

print("workload=24")
print("attempts=36")
print("top_level=108")
print("backend=144")
print("holdout_execution_started=0")
PY

git -C "$ROOT" diff --check
