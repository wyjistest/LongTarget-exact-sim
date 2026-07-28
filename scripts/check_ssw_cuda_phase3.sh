#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---final}"
PHASE2_HEAD="3f2bf535b9b322949e09db966e7128a5d6fc4414"

if [[ "$MODE" != "--preflight" && "$MODE" != "--final" ]]; then
  echo "usage: $0 [--preflight|--final]" >&2
  exit 2
fi

for relative in \
  Makefile \
  goal-ssw.md \
  docs/ssw_cuda/HOLDOUT_POLICY.md \
  paper/ssw_cuda/PROGRAM_STATE.json \
  paper/ssw_cuda/STATUS.md \
  paper/ssw_cuda/used_input_exclusion_registry.tsv \
  paper/ssw_cuda/used_input_exclusion_registry.sha256 \
  paper/ssw_cuda/corpus_manifest.tsv \
  paper/ssw_cuda/corpus_manifest.sha256 \
  paper/ssw_cuda/corpus_receipt.json \
  reproduce/ssw_cuda/freeze_phase0.py \
  reproduce/ssw_cuda/build_corpus.py \
  reproduce/ssw_cuda/compare_layers.py \
  tests/ssw_cuda/fixtures/hq10_prealign.json \
  tests/ssw_cuda/fixtures/hq10_mismatch_call.json \
  tests/ssw_cuda/fixtures/hq11_prealign.json \
  tests/ssw_cuda/fixtures/hq11_mismatch_call.json \
  tests/ssw_cuda/test_layered_comparator.py; do
  if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
    echo "missing or unsafe SSW-CUDA Phase 3 dependency: $relative" >&2
    exit 1
  fi
done

python3 -m json.tool "$ROOT/paper/ssw_cuda/PROGRAM_STATE.json" >/dev/null
python3 -m json.tool "$ROOT/paper/ssw_cuda/corpus_receipt.json" >/dev/null
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  "$ROOT/reproduce/ssw_cuda/build_corpus.py" \
  "$ROOT/reproduce/ssw_cuda/compare_layers.py" \
  "$ROOT/tests/ssw_cuda/test_layered_comparator.py"

(
  cd "$ROOT/paper/ssw_cuda"
  sha256sum --check --status used_input_exclusion_registry.sha256
  sha256sum --check --status corpus_manifest.sha256
)

PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/ssw_cuda/build_corpus.py" --check
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/ssw_cuda/test_layered_comparator.py"

python3 - "$ROOT" "$MODE" "$PHASE2_HEAD" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
mode = sys.argv[2]
phase2_head = sys.argv[3]
state = json.loads((root / "paper/ssw_cuda/PROGRAM_STATE.json").read_text(encoding="utf-8"))
receipt = json.loads((root / "paper/ssw_cuda/corpus_receipt.json").read_text(encoding="utf-8"))
goal = (root / "goal-ssw.md").read_text(encoding="utf-8")
status = (root / "paper/ssw_cuda/STATUS.md").read_text(encoding="utf-8")

if receipt["frozen_parent_head"] != phase2_head:
    raise SystemExit("Phase 3 corpus parent is not the frozen Phase 2 evidence HEAD")
if receipt["manifest"]["row_count"] != 749:
    raise SystemExit("Phase 3 corpus row-count drift")
if receipt["manifest"]["counts_by_execution_tier"] != {
    "compact": 370,
    "identity_only": 112,
    "large": 267,
}:
    raise SystemExit("Phase 3 execution-tier drift")
if receipt["registry_coverage"]["registry_rows"] != 112:
    raise SystemExit("Phase 3 registry coverage drift")
if receipt["execution_policy"]["normal_checker_runs_large_corpus"]:
    raise SystemExit("normal Phase 3 checker must not run the large corpus")
if receipt["execution_policy"]["fresh_holdout_consumed"]:
    raise SystemExit("Phase 3 must not consume a fresh holdout")
if receipt["execution_policy"]["l8_contract_status"] != "diagnostic_only":
    raise SystemExit("Phase 3 L8 contract drift")
if state["l8_contract_status"] != "diagnostic_only":
    raise SystemExit("program L8 contract drift")

if mode == "--preflight":
    if state["active_phase"] != 3 or state["phase_status"]["3"] != "in_progress":
        raise SystemExit("Phase 3 preflight requires in-progress state")
    required_goal = (
        "active_phase = 3",
        "phase_3_status = in_progress",
        "phase_4_status = pending",
    )
    comparison_end = "WORKTREE"
else:
    if (
        state["active_phase"] < 4
        or state["phase_status"]["3"] != "pass"
    ):
        raise SystemExit("Phase 3 final state is invalid")
    required_goal = (
        "phase_3_status = pass",
    )
    completed = subprocess.run(
        [
            "git",
            "log",
            "--format=%H",
            "--diff-filter=A",
            "--",
            "paper/ssw_cuda/corpus_manifest.tsv",
        ],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    commits = completed.stdout.splitlines()
    if len(commits) != 1:
        raise SystemExit("cannot identify unique Phase 3 corpus freeze commit")
    comparison_end = commits[0]

for phrase in required_goal:
    if phrase not in goal:
        raise SystemExit(f"goal-ssw Phase 3 state drift: {phrase}")
for phrase in (
    f"active_phase = {state['active_phase']}",
    f"phase_3_status = {state['phase_status']['3']}",
    "l8_contract_status = diagnostic_only",
):
    if phrase not in status:
        raise SystemExit(f"SSW-CUDA status drift: {phrase}")

sensitive_prefixes = (
    "cuda/",
    "fasim/sswNew.cpp",
    "fasim/ssw_cpp.cpp",
    "fasim/ssw_cpp.h",
    "fasim/fastsim.h",
    "fasim/gasal2_align_bridge.cpp",
    "fasim/gasal2_align_bridge.h",
)
if comparison_end == "WORKTREE":
    changed = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()
    paths = [line[3:] for line in changed if len(line) >= 4]
else:
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", phase2_head, comparison_end],
        cwd=root,
        check=False,
    )
    if ancestry.returncode != 0:
        raise SystemExit("Phase 3 freeze commit is not descended from Phase 2 evidence")
    paths = subprocess.run(
        ["git", "diff", "--name-only", f"{phase2_head}..{comparison_end}"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()
violations = sorted(path for path in paths if path.startswith(sensitive_prefixes))
if violations:
    raise SystemExit(f"CUDA/SSW implementation changed before corpus freeze: {violations}")
PY

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "SSW-CUDA Phase 3 $MODE checks OK"
echo "corpus_rows=749"
echo "identity_only_rows=112"
echo "compact_rows=370"
echo "large_explicit_gate_rows=267"
echo "fresh_holdout_consumed=0"
echo "l8_contract_status=diagnostic_only"
