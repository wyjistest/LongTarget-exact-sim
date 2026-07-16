#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-$ROOT/.tmp/check_fasim_gasal2_paper_phase7}"
GOAL="$ROOT/goal-final.md"
EXPECTED_LOG="$ROOT/paper/clean_checkout_validation.log"
RUNTIME_COMMIT="0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"

required=(
  "$GOAL"
  "$ROOT/reproduce/input_manifest.tsv"
  "$ROOT/reproduce/environment_manifest.json"
  "$ROOT/reproduce/environment.md"
  "$ROOT/reproduce/Dockerfile"
  "$ROOT/reproduce/benchmark_commands.sh"
  "$ROOT/reproduce/check_reproduction.sh"
  "$ROOT/reproduce/prepare_inputs.py"
  "$ROOT/tests/check_fasim_gasal2_paper_reproduction.py"
  "$ROOT/paper/RELEASE_CHECKLIST.md"
  "$EXPECTED_LOG"
  "$ROOT/paper/phase2_artifact_manifest.tsv"
  "$ROOT/paper/phase3_artifact_manifest.tsv"
  "$ROOT/paper/phase4_artifact_manifest.tsv"
)
for path in "${required[@]}"; do
  if [[ ! -s "$path" ]]; then
    echo "missing paper Phase 7 dependency: $path" >&2
    exit 1
  fi
done

if [[ -n "$(git -C "$ROOT" diff --name-only "$RUNTIME_COMMIT" -- fasim)" ]]; then
  echo "paper runtime changed under fasim/ after frozen runtime commit" >&2
  exit 1
fi

python3 "$ROOT/tests/check_fasim_gasal2_paper_reproduction.py"
python3 -m py_compile \
  "$ROOT/reproduce/prepare_inputs.py" \
  "$ROOT/tests/check_fasim_gasal2_paper_reproduction.py"

rm -rf "$WORK"
mkdir -p "$WORK/current" "$WORK/clean"
bash "$ROOT/reproduce/check_reproduction.sh" >"$WORK/current/quick.log"
cmp "$EXPECTED_LOG" "$WORK/current/quick.log"

python3 - "$ROOT" "$GOAL" <<'PY'
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path


root = Path(sys.argv[1]).resolve()
goal_path = Path(sys.argv[2]).resolve()
runtime_commit = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
freeze_id = "paper-data-v1-dccfd49-20260716"


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"missing TSV header: {path}")
        return reader.fieldnames, list(reader)


state: dict[str, str] = {}
for raw in goal_path.read_text(encoding="utf-8").splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
if state.get("paper_runtime_epoch") != "0" or state.get("paper_runtime_commit") != runtime_commit:
    raise SystemExit("paper runtime freeze drifted")
if state.get("data_freeze_id") != freeze_id:
    raise SystemExit("paper data freeze ID drifted")
if state.get("active_phase") not in {"8", "9", "complete"}:
    raise SystemExit("goal state has not completed paper Phase 7")
if state.get("phase_7_status") != "pass":
    raise SystemExit("goal-final.md does not record phase_7_status = pass")

input_fields, inputs = read_tsv(root / "reproduce/input_manifest.tsv")
if len(inputs) != 13 or len({row["input_id"] for row in inputs}) != 13:
    raise SystemExit("input provenance manifest count or IDs drifted")
for row in inputs:
    if not row["source"] or not row["license"] or not row["reconstruction_command"]:
        raise SystemExit(f"input provenance incomplete: {row['input_id']}")
    if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
        raise SystemExit(f"input digest invalid: {row['input_id']}")
    if Path(row["path_convention"]).is_absolute():
        raise SystemExit(f"input path is machine-specific: {row['input_id']}")

environment = json.loads((root / "reproduce/environment_manifest.json").read_text(encoding="utf-8"))
if environment.get("gasal2_max_query_len") != 2812 or len(environment.get("gpus", [])) != 2:
    raise SystemExit("environment contract drifted")

expected_raw = {
    "phase2_artifact_manifest.tsv": 1819,
    "phase3_artifact_manifest.tsv": 1367,
    "phase4_artifact_manifest.tsv": 539,
}
for name, expected_count in expected_raw.items():
    fields, rows = read_tsv(root / "paper" / name)
    if fields != ["artifact_path", "size_bytes", "sha256"] or len(rows) != expected_count:
        raise SystemExit(f"raw artifact manifest schema/count drifted: {name}")
    if len({row["artifact_path"] for row in rows}) != len(rows):
        raise SystemExit(f"raw artifact manifest has duplicate paths: {name}")
    for row in rows:
        if Path(row["artifact_path"]).is_absolute() or int(row["size_bytes"]) < 0:
            raise SystemExit(f"invalid raw artifact row in {name}: {row['artifact_path']}")
        if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise SystemExit(f"invalid raw artifact digest in {name}: {row['artifact_path']}")

machine_path_patterns = ("/data/", "/home/", "/Users/", "$HOME")
for relative in (
    "reproduce/input_manifest.tsv",
    "reproduce/environment_manifest.json",
    "reproduce/environment.md",
    "reproduce/benchmark_commands.sh",
    "reproduce/check_reproduction.sh",
    "paper/RELEASE_CHECKLIST.md",
):
    text = (root / relative).read_text(encoding="utf-8")
    if any(pattern in text for pattern in machine_path_patterns):
        raise SystemExit(f"undocumented machine path in {relative}")

commands = (root / "reproduce/benchmark_commands.sh").read_text(encoding="utf-8").lower()
for forbidden in ("121-segment", "full kcnq1ot1", "full hg38"):
    if forbidden in commands:
        raise SystemExit(f"forbidden expensive reproduction command: {forbidden}")
if "c7_kcnq_max8_chr22" not in commands:
    raise SystemExit("bounded max8 reproduction command missing")

print("paper_phase7_metadata=pass")
print("input_manifest_rows=13")
print("raw_manifest_rows=3725")
print("runtime_epoch=0")
PY

phase7_paths=(
  .gitignore Makefile goal-final.md
  paper/README.md paper/RELEASE_CHECKLIST.md paper/artifact_inventory.tsv
  paper/clean_checkout_validation.log paper/gap_register.tsv
  reproduce/Dockerfile reproduce/benchmark_commands.sh reproduce/check_reproduction.sh
  reproduce/environment.md reproduce/environment_manifest.json reproduce/input_manifest.tsv
  reproduce/prepare_inputs.py scripts/check_fasim_gasal2_paper_phase7.sh
  tests/check_fasim_gasal2_paper_reproduction.py
)
if ! git -C "$ROOT" diff --quiet -- "${phase7_paths[@]}"; then
  echo "Phase 7 files must be staged before the clean-checkout gate" >&2
  exit 1
fi
for path in "${phase7_paths[@]}"; do
  if ! git -C "$ROOT" ls-files --error-unmatch "$path" >/dev/null 2>&1; then
    echo "Phase 7 file is not staged/tracked: $path" >&2
    exit 1
  fi
done

tree="$(git -C "$ROOT" write-tree)"
commit="$(
  printf '%s\n' 'paper Phase 7 clean-checkout validation' |
    GIT_AUTHOR_NAME='paper-reproduction' \
    GIT_AUTHOR_EMAIL='paper-reproduction@invalid' \
    GIT_COMMITTER_NAME='paper-reproduction' \
    GIT_COMMITTER_EMAIL='paper-reproduction@invalid' \
    git -C "$ROOT" commit-tree "$tree" -p HEAD
)"
git -C "$ROOT" archive "$commit" | tar -x -C "$WORK/clean"

(
  cd "$WORK/clean"
  bash reproduce/check_reproduction.sh
) >"$WORK/clean/quick.log"
cmp "$EXPECTED_LOG" "$WORK/clean/quick.log"

if find "$WORK/clean" -type d \( -name .tmp -o -name .paper-artifacts \) -print -quit | grep -q .; then
  echo "clean quick reproduction created an undocumented artifact root" >&2
  exit 1
fi

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "GASAL2 paper Phase 7 checks OK"
echo "clean_checkout_quick_reproduction=pass"
echo "external_inputs_documented=13"
echo "raw_artifact_manifests_complete=1"
echo "gpu_benchmarks_rerun=0"
