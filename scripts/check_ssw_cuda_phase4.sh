#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:---final}"
PHASE3_HEAD="21832757d3431da7e6ec8b38b0072528f228988f"

if [[ "$MODE" != "--preflight" && "$MODE" != "--final" ]]; then
  echo "usage: $0 [--preflight|--final]" >&2
  exit 2
fi

for relative in \
  Makefile \
  goal-ssw.md \
  paper/ssw_cuda/PROGRAM_STATE.json \
  paper/ssw_cuda/STATUS.md \
  paper/ssw_cuda/upstream_snapshot.tsv \
  paper/ssw_cuda/upstream_build_receipt.json \
  paper/ssw_cuda/upstream_semantic_diff.tsv \
  paper/ssw_cuda/architecture_decision.md \
  reproduce/ssw_cuda/freeze_phase4.py \
  scripts/check_ssw_cuda_phase4.sh \
  tests/ssw_cuda/test_phase4_architecture.py; do
  if [[ ! -f "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
    echo "missing or unsafe SSW-CUDA Phase 4 dependency: $relative" >&2
    exit 1
  fi
done

python3 -m json.tool "$ROOT/paper/ssw_cuda/PROGRAM_STATE.json" >/dev/null
python3 -m json.tool "$ROOT/paper/ssw_cuda/upstream_build_receipt.json" >/dev/null
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile \
  "$ROOT/reproduce/ssw_cuda/freeze_phase4.py" \
  "$ROOT/tests/ssw_cuda/test_phase4_architecture.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/reproduce/ssw_cuda/freeze_phase4.py" --check
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/ssw_cuda/test_phase4_architecture.py"

if [[ -d "$ROOT/.paper-artifacts/ssw-cuda-v1/upstream/sources/Accelign/.git" && \
      -d "$ROOT/.paper-artifacts/ssw-cuda-v1/upstream/sources/G3SA/.git" ]]; then
  PYTHONDONTWRITEBYTECODE=1 python3 \
    "$ROOT/reproduce/ssw_cuda/freeze_phase4.py" --check-artifacts
else
  echo "Phase 4 ignored upstream snapshots unavailable; committed receipt validation passed" >&2
fi

python3 - "$ROOT" "$MODE" "$PHASE3_HEAD" <<'PY'
import csv
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
mode = sys.argv[2]
phase3_head = sys.argv[3]
state = json.loads((root / "paper/ssw_cuda/PROGRAM_STATE.json").read_text(encoding="utf-8"))
receipt = json.loads((root / "paper/ssw_cuda/upstream_build_receipt.json").read_text(encoding="utf-8"))
goal = (root / "goal-ssw.md").read_text(encoding="utf-8")
status = (root / "paper/ssw_cuda/STATUS.md").read_text(encoding="utf-8")
with (root / "paper/ssw_cuda/upstream_semantic_diff.tsv").open(newline="", encoding="utf-8") as handle:
    semantic_rows = list(csv.DictReader(handle, delimiter="\t"))

if receipt["frozen_parent_head"] != phase3_head:
    raise SystemExit("Phase 4 evidence is not descended from the final Phase 3 commit")
if receipt["build_budget"]["attempt_counts"] != {"accelign": 1, "g3sa": 3}:
    raise SystemExit("Phase 4 external build-attempt budget drift")
if receipt["build_budget"]["architecture_candidate_count"] > 3:
    raise SystemExit("Phase 4 architecture-candidate budget exceeded")
if receipt["build_budget"]["observed_runtime_wall_seconds_upper_bound"] >= 28800:
    raise SystemExit("Phase 4 GPU budget exceeded")
if receipt["results"]["selected_architecture"] != "C_mixed_in_tree_checkpoint_recompute":
    raise SystemExit("Phase 4 architecture decision drift")
if receipt["results"]["third_party_code_linked_or_copied"]:
    raise SystemExit("Phase 4 illegally imported third-party implementation")
if receipt["claim_boundary"]["cpu_oracle_replaced"]:
    raise SystemExit("Phase 4 replaced the CPU oracle")
if receipt["claim_boundary"]["bioinformatics_b3_track"] != "closed_amdahl":
    raise SystemExit("Phase 4 improperly reopened B3")
for upstream in ("accelign", "g3sa"):
    layers = {row["layer"] for row in semantic_rows if row["upstream_id"] == upstream}
    if not {"L0", "L1", "L2", "L3", "L4", "L5"}.issubset(layers):
        raise SystemExit(f"incomplete semantic matrix for {upstream}")

if mode == "--preflight":
    if state["active_phase"] != 4 or state["phase_status"]["4"] != "in_progress":
        raise SystemExit("Phase 4 preflight requires in-progress state")
    required_goal = (
        "active_phase = 4",
        "phase_4_status = in_progress",
        "phase_5_status = pending",
    )
    comparison_end = "WORKTREE"
else:
    if (
        state["active_phase"] != 5
        or state["phase_status"]["4"] != "pass"
        or state["phase_status"]["5"] != "in_progress"
    ):
        raise SystemExit("Phase 4 final state has not advanced to Phase 5")
    required_goal = (
        "active_phase = 5",
        "phase_4_status = pass",
        "phase_5_status = in_progress",
        "last_completed_phase = 4",
        "last_decision = phase4_architecture_C_selected",
        "last_evidence_doc = paper/ssw_cuda/architecture_decision.md",
        "last_test_command = make check-ssw-cuda-phase4",
    )
    commits = subprocess.run(
        ["git", "log", "--format=%H", "--diff-filter=A", "--", "paper/ssw_cuda/upstream_snapshot.tsv"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()
    if len(commits) != 1:
        raise SystemExit("cannot identify unique Phase 4 architecture commit")
    comparison_end = commits[0]

for phrase in required_goal:
    if phrase not in goal:
        raise SystemExit(f"goal-ssw Phase 4 state drift: {phrase}")
for phrase in (
    f"active_phase = {state['active_phase']}",
    f"phase_4_status = {state['phase_status']['4']}",
    "bioinformatics_b3_track = closed_amdahl",
    "engineering_track = active",
):
    if phrase not in status:
        raise SystemExit(f"SSW-CUDA status drift: {phrase}")

if comparison_end == "WORKTREE":
    paths = [
        line[3:]
        for line in subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.splitlines()
        if len(line) >= 4
    ]
else:
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", phase3_head, comparison_end],
        cwd=root,
        check=False,
    ).returncode != 0:
        raise SystemExit("Phase 4 commit ancestry drift")
    paths = subprocess.run(
        ["git", "diff", "--name-only", f"{phase3_head}..{comparison_end}"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()
sensitive = sorted(path for path in paths if path.startswith(("cuda/", "fasim/", "third_party/", "vendor/")))
if sensitive:
    raise SystemExit(f"Phase 4 introduced implementation code before architecture freeze: {sensitive}")
PY

git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "SSW-CUDA Phase 4 $MODE checks OK"
echo "selected_architecture=C_mixed_in_tree_checkpoint_recompute"
echo "accelign_build_attempts=1"
echo "g3sa_build_attempts=3"
echo "third_party_code_linked_or_copied=0"
echo "bioinformatics_b3_track=closed_amdahl"
