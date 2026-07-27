#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_ROOT="${WORK:-$ROOT/.tmp/check_bioinformatics_phase2}"
RUNTIME_COMMIT="0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
HISTORICAL_COMPLETION="a98d80d44d4418cdb8a67dc8d83ee41b8e599023"
PHASE2_DECISION_COMMIT="bf94dc75c5fe3e996472a1e90d242f582da361bf"
FROZEN_ROOT="$ROOT/.paper-artifacts/bioinformatics-phase2-holdout-v1"

mkdir -p -- "$WORK_ROOT"
RUN_WORK="$(mktemp -d "$WORK_ROOT/run.XXXXXX")"
cleanup() {
  rm -rf -- "$RUN_WORK"
}
trap cleanup EXIT

for relative in \
  reproduce/bioinformatics/analyze_holdout_results.py \
  tests/check_analyze_bioinformatics_phase2.py \
  tests/check_bioinformatics_phase2.py \
  tests/check_analyze_bioinformatics_frozen_contracts.py \
  tests/check_gasal2_longtarget_cli.py \
  config/gasal2_longtarget_contracts.json \
  schemas/gasal2_longtarget_contracts.schema.json \
  paper/bioinformatics/holdout_summary.json \
  paper/bioinformatics/phase2_decision.md; do
  if [[ ! -s "$ROOT/$relative" ]]; then
    echo "missing Bioinformatics Phase 2 dependency: $relative" >&2
    exit 1
  fi
done

snapshot_frozen_tree() {
  python3 - "$FROZEN_ROOT" "$1" <<'PY'
from __future__ import annotations
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1])
output = Path(sys.argv[2])
rows = []

def visit(path: Path, relative: str) -> None:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        raise SystemExit(f"frozen tree contains symlink: {path}")
    row = {"path": relative, "mode": metadata.st_mode & 0o7777}
    if stat.S_ISREG(metadata.st_mode):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        row.update(kind="file", size=metadata.st_size, sha256=digest.hexdigest())
    elif stat.S_ISDIR(metadata.st_mode):
        row["kind"] = "directory"
    else:
        raise SystemExit(f"unexpected frozen tree entry: {path}")
    rows.append(row)
    if stat.S_ISDIR(metadata.st_mode):
        for child in sorted(path.iterdir(), key=lambda item: item.name):
            child_relative = child.name if relative == "." else f"{relative}/{child.name}"
            visit(child, child_relative)

visit(root, ".")
output.write_text(json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
PY
}

if [[ "${1:-}" == "--snapshot-frozen-tree" ]]; then
  if [[ "$#" -ne 3 ]]; then
    echo "usage: $0 --snapshot-frozen-tree ROOT OUTPUT" >&2
    exit 2
  fi
  FROZEN_ROOT="$2"
  snapshot_frozen_tree "$3"
  exit 0
fi

snapshot_frozen_tree "$RUN_WORK/frozen.before.json"

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/check_analyze_bioinformatics_phase2.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/check_bioinformatics_phase2.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/check_analyze_bioinformatics_frozen_contracts.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/check_gasal2_longtarget_cli.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/check_fasim_gasal2_paper_reproduction.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/check_audit_fasim_gasal2_paper_results.py"
bash "$ROOT/reproduce/check_reproduction.sh"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/audit_paper_results.py"

PYTHONDONTWRITEBYTECODE=1 python3 \
  "$ROOT/reproduce/bioinformatics/analyze_holdout_results.py" \
  --repo-root "$ROOT" \
  --output-dir "$RUN_WORK/generated"

for name in \
  holdout_attempt_results.tsv \
  holdout_workload_results.tsv \
  holdout_rank_results.tsv \
  holdout_mode_results.tsv \
  holdout_mismatch_details.tsv \
  holdout_raw_artifacts.tsv \
  holdout_summary.json \
  phase2_decision.md; do
  cmp "$ROOT/paper/bioinformatics/$name" "$RUN_WORK/generated/$name"
done

python3 -m py_compile \
  "$ROOT/reproduce/bioinformatics/analyze_holdout_results.py" \
  "$ROOT/tests/check_analyze_bioinformatics_phase2.py" \
  "$ROOT/tests/check_bioinformatics_phase2.py"
python3 -m json.tool "$ROOT/config/gasal2_longtarget_contracts.json" >/dev/null
python3 -m json.tool "$ROOT/schemas/gasal2_longtarget_contracts.schema.json" >/dev/null
python3 -m json.tool "$ROOT/paper/bioinformatics/holdout_summary.json" >/dev/null
bash -n "$ROOT/scripts/check_bioinformatics_phase2.sh"

python3 - "$ROOT" <<'PY'
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
bio = root / "paper/bioinformatics"

def rows(name: str):
    with (bio / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))

attempts = rows("holdout_attempt_results.tsv")
workloads = rows("holdout_workload_results.tsv")
ranks = rows("holdout_rank_results.tsv")
modes = rows("holdout_mode_results.tsv")
summary = json.loads((bio / "holdout_summary.json").read_text())
if (len(attempts), len(workloads), len(ranks), len(modes)) != (36, 24, 108, 108):
    raise SystemExit("Phase 2 generated row cardinality drift")
if summary["decision"] != "verified_only_contract":
    raise SystemExit("Phase 2 decision drift")
if summary["attempt_counts"]["scientific_mismatch"] != 2:
    raise SystemExit("Phase 2 mismatch count drift")
if summary["attempt_counts"]["verified_fallback"] != 3:
    raise SystemExit("Phase 2 fallback count drift")
if any(summary["attempt_counts"][key] for key in ("technical_failure", "missing", "oom", "timeout", "invalid_report", "telemetry_error")):
    raise SystemExit("Phase 2 technical failure count is nonzero")
if sum(row["boundary_ties_equal"] == "1" for row in attempts) != 36:
    raise SystemExit("Phase 2 boundary-tie count drift")

registry = json.loads((root / "config/gasal2_longtarget_contracts.json").read_text())
forbidden = {"query_ids", "gene_names", "target_ids", "digests", "result_allowlist", "blacklist", "mechanism_guard"}
def walk(value):
    if isinstance(value, dict):
        if forbidden.intersection(value) or any("allowlist" in key.lower() for key in value):
            raise SystemExit("registry contains an unsafe identifier/digest/result routing field")
        for child in value.values():
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)
walk(registry)

manifest = rows("submission_manifest.tsv")
phase2 = [row for row in manifest if row["phase"] == "2"]
if any(row["status"] != "pass" for row in phase2):
    raise SystemExit("submission manifest has a non-pass Phase 2 artifact")
if len({row["artifact_id"] for row in manifest}) != len(manifest):
    raise SystemExit("submission manifest has duplicate artifact IDs")

claims = {row["claim_id"]: row for row in rows("claim_evidence.tsv")}
if claims["B2"]["status"] != "pass" or "verified" not in claims["B2"]["allowed_wording"].lower():
    raise SystemExit("B2 claim ledger is not narrowed to verified-only evidence")

goal = (root / "goal-bioinformatics.md").read_text()
for phrase in (
    "active_phase = 4", "phase_2_status = pass", "phase_3_status = no_go",
    "last_completed_phase = 3", "last_decision = stop_after_pilot_futility",
    "last_evidence_doc = paper/bioinformatics/phase3_postpilot_decision.json",
    "last_test_command = make check-bioinformatics-phase3-pilot",
):
    if phrase not in goal:
        raise SystemExit(f"goal state drift: {phrase}")
if "`verified_only_contract`" not in (bio / "phase2_decision.md").read_text():
    raise SystemExit("historical Phase 2 decision was not preserved")
PY

if ! git -C "$ROOT" merge-base --is-ancestor "$PHASE2_DECISION_COMMIT" HEAD; then
  echo "Phase 2 decision commit is not an ancestor of HEAD" >&2
  exit 1
fi
if ! git -C "$ROOT" diff --quiet "$RUNTIME_COMMIT" "$PHASE2_DECISION_COMMIT" -- \
  fasim cuda longtarget.cpp sim.h exact_sim.h rules.h stats.h; then
  echo "Phase 2 changed immutable C/C++/CUDA/core runtime paths before its decision" >&2
  exit 1
fi

if ! git -C "$ROOT" merge-base --is-ancestor "$HISTORICAL_COMPLETION" HEAD; then
  echo "historical paper completion commit is not an ancestor of HEAD" >&2
  exit 1
fi
if ! git -C "$ROOT" diff --quiet "$HISTORICAL_COMPLETION" HEAD -- \
  paper/source_data paper/workload_manifest.tsv; then
  echo "historical frozen source data changed after paper completion" >&2
  exit 1
fi

snapshot_frozen_tree "$RUN_WORK/frozen.after.json"
cmp "$RUN_WORK/frozen.before.json" "$RUN_WORK/frozen.after.json"

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "Bioinformatics Phase 2 checks OK"
echo "phase2_decision=verified_only_contract"
echo "formal_attempts=36"
echo "formal_workloads=24"
echo "rank_rows=108"
echo "mode_rows=108"
echo "scientific_mismatches=2"
echo "verified_fallbacks=3"
echo "gpu_only_contract_promoted=0"
echo "frozen_artifact_tree_unchanged=1"
echo "runtime_behavior_change=0"
echo "historical_reproduction=pass"
