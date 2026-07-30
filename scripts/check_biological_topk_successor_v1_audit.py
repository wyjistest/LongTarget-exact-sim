#!/usr/bin/env python3
"""Run the original v1 phase checks against their frozen commit identities."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMIT_BY_PHASE = {
    0: "3e642db8d93fc253972104e6072e2715f52ccb19",
    1: "0daed2c4e1f181d3ce67ecba52db314a1798146e",
    2: "4d89d1cd989f50a42e7e3af56333c39219ba1803",
    3: "ca6410c1fc986e91fd855a43ed71dfeb5940f68f",
    4: "7fae3de6b13780d7cc0776038489cf2f22072339",
}


def load_checker():
    path = ROOT / "scripts/check_biological_topk_phase.py"
    spec = importlib.util.spec_from_file_location("biological_topk_pinned_v1_checker", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    checker = load_checker()
    status_before = checker.changed_paths()
    if status_before:
        print("pinned predecessor audit requires a clean tree", file=sys.stderr)
        return 1
    state = json.loads(
        (ROOT / "paper/biological_topk/PROGRAM_STATE.json").read_text(encoding="utf-8")
    )
    original_resolver = checker.phase_commit_for_postcommit
    checker.phase_commit_for_postcommit = lambda phase: COMMIT_BY_PHASE[phase]
    try:
        checker.check_phase0("postcommit", state)
        checker.check_phase1("postcommit", state)
        checker.check_phase2("postcommit", state)
        checker.check_phase3("postcommit", state)
        checker.check_phase4("postcommit", state)
    except Exception as error:  # The imported checker owns the detailed type hierarchy.
        print(f"pinned predecessor audit failed: {error}", file=sys.stderr)
        return 1
    finally:
        checker.phase_commit_for_postcommit = original_resolver
    if checker.changed_paths() != status_before:
        print("pinned predecessor audit modified the working tree", file=sys.stderr)
        return 1
    print("pinned predecessor Phase 0-4 aggregate audit OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
