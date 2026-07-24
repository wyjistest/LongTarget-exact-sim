#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_ROOT="${WORK:-$ROOT/.tmp/check_bioinformatics_phase1}"
RUNTIME_COMMIT="0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"

mkdir -p -- "$WORK_ROOT"
RUN_WORK="$(mktemp -d "$WORK_ROOT/run.XXXXXX")"
cleanup() {
  rm -rf -- "$RUN_WORK"
}
trap cleanup EXIT
WORK="$RUN_WORK"

for relative in \
  goal-bioinformatics.md README.md \
  scripts/gasal2_longtarget.py \
  schemas/gasal2_longtarget_run_report.schema.json \
  tests/check_gasal2_longtarget_cli.py \
  docs/gasal2_longtarget_cli.md \
  examples/gasal2_longtarget/README.md \
  paper/bioinformatics/phase1_validation.md \
  paper/bioinformatics/gap_register.tsv \
  paper/bioinformatics/submission_manifest.tsv; do
  if [[ ! -s "$ROOT/$relative" ]]; then
    echo "missing Bioinformatics Phase 1 dependency: $relative" >&2
    exit 1
  fi
done

python3 "$ROOT/tests/check_gasal2_longtarget_cli.py"
python3 -m py_compile \
  "$ROOT/scripts/gasal2_longtarget.py" \
  "$ROOT/tests/check_gasal2_longtarget_cli.py"
python3 -m json.tool "$ROOT/schemas/gasal2_longtarget_run_report.schema.json" >/dev/null
python3 "$ROOT/scripts/gasal2_longtarget.py" --help >/dev/null
python3 "$ROOT/scripts/gasal2_longtarget.py" --version | grep -Eq '^gasal2-longtarget 0\.0\.0\+submission\.1\.dev$'

python3 "$ROOT/scripts/gasal2_longtarget.py" \
  --mode cpu-authority \
  --query "$ROOT/H19.fa" \
  --target "$ROOT/testDNA.fa" \
  --output "$WORK/output" \
  --report "$WORK/report.json" \
  --authority-binary "$ROOT/fasim_longtarget_x86" \
  --candidate-binary "$ROOT/fasim_longtarget_gasal2" \
  --timeout 120

printf '>query1\nACGT\n>query2\nTGCA\n' >"$WORK/multi-query.fa"
set +e
python3 "$ROOT/scripts/gasal2_longtarget.py" \
  --mode cpu-authority \
  --query "$WORK/multi-query.fa" \
  --target "$ROOT/testDNA.fa" \
  --output "$WORK/multi-output" \
  --report "$WORK/multi-report.json" \
  --authority-binary "$ROOT/fasim_longtarget_x86" \
  --timeout 120
multi_exit=$?
set -e
if [[ "$multi_exit" != "2" || -e "$WORK/multi-output" ]]; then
  echo "multi-query input did not fail closed before authority output" >&2
  exit 1
fi

python3 - "$ROOT" "$WORK" "$RUNTIME_COMMIT" <<'PY'
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path


root = Path(sys.argv[1])
work = Path(sys.argv[2])
runtime_commit = sys.argv[3]


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"missing TSV header: {path}")
        return reader.fieldnames, list(reader)


def require(path: Path, phrases: tuple[str, ...]) -> str:
    text = path.read_text(encoding="utf-8")
    for phrase in phrases:
        if phrase not in text:
            raise SystemExit(f"{path.relative_to(root)} missing: {phrase}")
    return text


goal = require(
    root / "goal-bioinformatics.md",
    (
        "phase_0_status = pass",
        "phase_1_status = pass",
    ),
)
state: dict[str, str] = {}
for raw in goal.splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
active = state.get("active_phase", "")
if active != "complete" and (not active.isdigit() or int(active) < 2):
    raise SystemExit(f"Bioinformatics Phase 1 is not complete: active_phase={active!r}")
last_completed = state.get("last_completed_phase", "")
if not last_completed.isdigit() or int(last_completed) < 1:
    raise SystemExit("Bioinformatics last_completed_phase has regressed below Phase 1")
if subprocess.run(
    [
        "git", "-C", str(root), "diff", "--quiet", runtime_commit, "--",
        "fasim", "cuda", "longtarget.cpp", "sim.h", "exact_sim.h", "rules.h", "stats.h",
    ],
    check=False,
).returncode != 0:
    raise SystemExit("Phase 1 changed frozen runtime behavior paths")

cli = require(
    root / "scripts/gasal2_longtarget.py",
    (
        "cpu-authority",
        "fast-experimental",
        "cpu_fallback_after_mismatch",
        "experimental_unverified",
        "start_new_session=True",
        "os.replace",
        "MAX_GPU_QUERY_LENGTH = 2812",
    ),
)
for unsafe in ("shell=True", "os.system(", "subprocess.getoutput("):
    if unsafe in cli:
        raise SystemExit(f"unsafe command construction in user CLI: {unsafe}")

readme = require(
    root / "README.md",
    ("Contract-Aware GASAL2 Workflow", "--mode safe", "--mode cpu-authority", "--dry-run"),
)
safe_position = readme.index("--mode safe")
advanced_gpu_position = readme.index("## Accelerated Builds")
if safe_position > advanced_gpu_position:
    raise SystemExit("README first GPU workflow is not safe mode")

require(
    root / "docs/gasal2_longtarget_cli.md",
    (
        "safe",
        "verified",
        "fast-experimental",
        "cpu-authority",
        "Atomic publication",
        "Run report",
        "Exit codes",
        "query length at most 2812",
        "owner-approved release version",
    ),
)

_, gaps = read_tsv(root / "paper/bioinformatics/gap_register.tsv")
gap_by_id = {row["gap_id"]: row for row in gaps}
for gap_id in ("G01_user_cli", "G02_input_guard", "G03_comparator", "G04_json_report"):
    row = gap_by_id.get(gap_id)
    if row is None or row["classification"] != "available" or row["status"] != "pass":
        raise SystemExit(f"Phase 1 capability is not closed: {gap_id}")

_, manifest = read_tsv(root / "paper/bioinformatics/submission_manifest.tsv")
phase1_paths = {row["path"] for row in manifest if row["phase"] == "1"}
expected_phase1 = {
    "scripts/gasal2_longtarget.py",
    "schemas/gasal2_longtarget_run_report.schema.json",
    "tests/check_gasal2_longtarget_cli.py",
    "docs/gasal2_longtarget_cli.md",
    "examples/gasal2_longtarget/README.md",
    "README.md",
    "paper/bioinformatics/phase1_validation.md",
    "scripts/check_bioinformatics_phase1.sh",
}
if phase1_paths != expected_phase1:
    raise SystemExit("submission manifest Phase 1 artifact set drifted")
if any(row["status"] != "pass" for row in manifest if row["phase"] == "1"):
    raise SystemExit("submission manifest has a non-pass Phase 1 artifact")

schema = json.loads((root / "schemas/gasal2_longtarget_run_report.schema.json").read_text())
report = json.loads((work / "report.json").read_text())
sys.path.insert(0, str(root / "scripts"))
from gasal2_longtarget import validate_report
validate_report(report)
for field in schema["required"]:
    if field not in report:
        raise SystemExit(f"CPU smoke report missing schema field: {field}")
if report["result_status"] != "authority_complete" or report["published_source"] != "authority":
    raise SystemExit("real CPU authority smoke did not publish authority")
tfosorted = [row for row in report["published_outputs"] if row["relative_path"].endswith("-TFOsorted")]
if len(tfosorted) != 1 or tfosorted[0]["record_count"] is None:
    raise SystemExit("real CPU authority smoke lacks one counted TFOsorted output")
multi_report = json.loads((work / "multi-report.json").read_text())
validate_report(multi_report)
if multi_report["result_status"] != "invalid_input":
    raise SystemExit("real-binary multi-query preflight did not report invalid_input")

print("Bioinformatics Phase 1 checks OK")
print("cli_contract_tests=31")
print("cpu_authority_smoke=pass")
print("multi_query_fail_closed=1")
print("default_mode_fail_closed=1")
print("verified_mismatch_publishes_authority=1")
print("fast_experimental_explicit=1")
print("report_schema_validation=pass")
print("atomic_output_tests=pass")
print("runtime_behavior_change=0")
PY

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check
