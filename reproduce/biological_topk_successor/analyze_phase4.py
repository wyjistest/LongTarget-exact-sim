#!/usr/bin/env python3
"""Preflight or analyze the successor biological Top-K Phase 4 epoch."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from reproduce.biological_topk import analyze_fresh_holdout as _IMPL  # noqa: E402
from reproduce.biological_topk_successor import freeze_phase3 as frozen  # noqa: E402
from reproduce.biological_topk_successor import run_phase4 as runner  # noqa: E402


PAPER = ROOT / "paper/biological_topk_successor"
SOURCE_DATA = PAPER / "source_data"
ARTIFACT_ROOT = ROOT / ".paper-artifacts/biological-topk-successor/fresh-holdout"

_IMPL.frozen = frozen
_IMPL.runner = runner
_IMPL.PAPER = PAPER
_IMPL.SOURCE_DATA = SOURCE_DATA
_IMPL.ARTIFACT_ROOT = ARTIFACT_ROOT
_IMPL.COMPARISON_ROOT = ARTIFACT_ROOT / "offline-comparisons"
_IMPL.MATCHES_PATH = SOURCE_DATA / "fresh_candidate_matches.tsv"
_IMPL.WORKLOAD_METRICS_PATH = SOURCE_DATA / "fresh_workload_metrics.tsv"
_IMPL.EMPTY_PATH = SOURCE_DATA / "fresh_empty_workloads.tsv"
_IMPL.FAILURE_PATH = SOURCE_DATA / "fresh_failure_ledger.tsv"
_IMPL.BOUNDS_PATH = SOURCE_DATA / "fresh_exact_binomial_bounds.tsv"
_IMPL.RANK_PATH = SOURCE_DATA / "fresh_rank_diagnostics.tsv"
_IMPL.RECEIPT_PATH = PAPER / "fresh_holdout_receipt.json"
_IMPL.DECISION_PATH = PAPER / "fresh_holdout_decision.json"

for _name in _IMPL.__all__:
    globals()[_name] = getattr(_IMPL, _name)
globals().update(
    {
        "PAPER": PAPER,
        "SOURCE_DATA": SOURCE_DATA,
        "ARTIFACT_ROOT": ARTIFACT_ROOT,
        "frozen": frozen,
        "runner": runner,
    }
)


if __name__ == "__main__":
    raise SystemExit(_IMPL.main())
