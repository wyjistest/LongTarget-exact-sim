#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAN="$ROOT/paper/bioinformatics/phase2_traceback_replay_plan.json"
RUNNER="$ROOT/reproduce/bioinformatics/replay_phase2_traceback_cases.py"
TABLE="$ROOT/paper/bioinformatics/phase2_traceback_replay.tsv"
RECEIPT="$ROOT/paper/bioinformatics/phase2_traceback_replay_receipt.json"
ROOT_CAUSE="$ROOT/paper/bioinformatics/phase2_traceback_root_cause.md"
CHECKSUMS="$ROOT/paper/bioinformatics/phase2_traceback_replay.sha256"
ARTIFACT_ROOT="$ROOT/.paper-artifacts/bioinformatics-phase2-traceback-replay-v1"

for path in "$PLAN" "$RUNNER" \
  "$ROOT/scripts/replay_phase2_traceback_cases.sh" \
  "$ROOT/scripts/check_bioinformatics_traceback_replay.sh" \
  "$ROOT/tests/check_replay_bioinformatics_phase2_traceback.py"; do
  if [[ ! -f "$path" || -L "$path" ]]; then
    echo "missing or unsafe traceback replay dependency: $path" >&2
    exit 1
  fi
done

python3 -m json.tool "$PLAN" >/dev/null
python3 -m py_compile "$RUNNER" "$ROOT/tests/check_replay_bioinformatics_phase2_traceback.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/check_replay_bioinformatics_phase2_traceback.py"
python3 "$RUNNER" --plan-only >/dev/null

if [[ "${REPLAY_PREEXECUTION_ONLY:-0}" == "1" ]]; then
  if [[ -e "$TABLE" || -e "$RECEIPT" || -e "$ARTIFACT_ROOT" ]]; then
    echo "preexecution check found replay results" >&2
    exit 1
  fi
  echo "Bioinformatics Phase 2 traceback replay preexecution checks OK"
  exit 0
fi

for path in "$TABLE" "$RECEIPT" "$ROOT_CAUSE" "$CHECKSUMS"; do
  if [[ ! -f "$path" || -L "$path" ]]; then
    echo "missing or unsafe traceback replay evidence: $path" >&2
    exit 1
  fi
done
python3 -m json.tool "$RECEIPT" >/dev/null
(
  cd "$ROOT/paper/bioinformatics"
  sha256sum --check --status phase2_traceback_replay.sha256
)

python3 - "$ROOT" <<'PY'
import csv
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
bio = root / "paper/bioinformatics"
receipt = json.loads((bio / "phase2_traceback_replay_receipt.json").read_text(encoding="utf-8"))
with (bio / "phase2_traceback_replay.tsv").open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle, delimiter="\t"))

if receipt["historical_phase2_decision"] != "verified_only_contract":
    raise SystemExit("historical Phase 2 decision drift")
if receipt["historical_phase3_v1_decision"] != "no_go":
    raise SystemExit("historical Phase 3 decision drift")
if receipt["promotion_eligible"] is not False:
    raise SystemExit("diagnostic replay was admitted for promotion")
if receipt["run_count"] != 6 or len(rows) != 6:
    raise SystemExit("traceback replay representation count drift")
if receipt["technical_failures"] or receipt["fallbacks"] or receipt["timeouts"] or receipt["ooms"]:
    raise SystemExit("traceback replay contains a technical failure")
if receipt["all_outputs_byte_equal"] is not True:
    raise SystemExit("traceback replay output equality drift")
if any(row["byte_equal_to_expected"] != "True" for row in rows):
    raise SystemExit("traceback replay table equality drift")

artifact_root = root / receipt["artifact_root"]
if artifact_root.exists():
    manifest = artifact_root / "artifact-manifest.tsv"
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    if digest != receipt["artifact_manifest_sha256"]:
        raise SystemExit("raw replay artifact manifest digest drift")
    with manifest.open(newline="", encoding="utf-8") as handle:
        artifact_rows = list(csv.DictReader(handle, delimiter="\t"))
    if len(artifact_rows) != receipt["artifact_count"]:
        raise SystemExit("raw replay artifact count drift")
    expected_paths = set()
    for row in artifact_rows:
        relative = Path(row["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise SystemExit("unsafe raw replay artifact path")
        path = artifact_root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"missing or unsafe raw replay artifact: {relative}")
        if path.stat().st_size != int(row["size_bytes"]):
            raise SystemExit(f"raw replay artifact size drift: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise SystemExit(f"raw replay artifact digest drift: {relative}")
        expected_paths.add(relative.as_posix())
    observed_paths = {
        path.relative_to(artifact_root).as_posix()
        for path in artifact_root.rglob("*")
        if path.is_file() and path != manifest
    }
    if observed_paths != expected_paths:
        raise SystemExit("unindexed raw replay artifact detected")

phase2 = (bio / "phase2_decision.md").read_text(encoding="utf-8")
if "`verified_only_contract`" not in phase2:
    raise SystemExit("Phase 2 historical decision document changed")
phase3 = json.loads((bio / "phase3_postpilot_decision.json").read_text(encoding="utf-8"))
if phase3["b3_status"] != "no_go":
    raise SystemExit("Phase 3 historical B3 decision changed")
PY

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "Bioinformatics Phase 2 traceback replay checks OK"
echo "historical_phase2_decision=verified_only_contract"
echo "historical_phase3_v1_b3=no_go"
echo "replay_promotion_eligible=0"
echo "replay_runs=6"
