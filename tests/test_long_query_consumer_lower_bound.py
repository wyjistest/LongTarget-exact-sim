#!/usr/bin/env python3
"""Small deterministic tests for the host-only lower-bound replay."""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "audit_long_query_consumer_lower_bound.py"
SPEC = importlib.util.spec_from_file_location("lower_bound", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def row(
    group: int,
    index: int,
    forward: int,
    reverse: int,
    prealign: int,
    terminal: int,
) -> dict[str, str]:
    cutlength = 10
    return {
        "task_id": "0",
        "scoreinfo_index": str(group),
        "scoreinfo_position": "9",
        "scoreinfo_score": str(prealign),
        "attempt_index": str(group * 4 + index),
        "identity_round": str(index),
        "start": "0",
        "cutlength": str(cutlength),
        "prealign_score": str(prealign),
        "forward_score": str(forward),
        "reverse_score": str(reverse),
        "canonical_score": str(min(forward, reverse)),
        "query_end": "9",
        "ref_end_local": "9" if terminal else "8",
        "ref_end_global": "9" if terminal else "8",
        "terminal": str(terminal),
        "numeric_path": "1",
        "padded_target_length": str(cutlength),
        "query_length": "20",
        "forward_cells": "200",
        "reverse_cells": "200",
    }


def main() -> int:
    threshold = [
        row(0, 0, 9, 9, 10, 1),
        row(0, 1, 12, 11, 10, 1),
        row(0, 2, 50, 50, 10, 1),
        row(0, 3, 50, 50, 10, 1),
    ]
    result = MODULE.parse_group(threshold)
    assert result["selection_reason"] == "threshold"
    assert result["selected_local_index"] == 1
    assert result["processed_forward_attempts"] == 2
    assert result["minimum_forward_cells"] == 400
    assert result["reverse_needed_attempts"] == 2

    best = [
        row(1, 0, 7, 7, 10, 1),
        row(1, 1, 8, 8, 10, 1),
        row(1, 2, 9, 9, 10, 1),
        row(1, 3, 8, 8, 10, 0),
    ]
    result = MODULE.parse_group(best)
    assert result["selection_reason"] == "best_fallback"
    assert result["selected_local_index"] == 2
    assert result["processed_forward_attempts"] == 4
    assert result["reverse_needed_attempts"] == 3

    last = [
        row(2, 0, 4, 4, 10, 0),
        row(2, 1, 3, 3, 10, 0),
        row(2, 2, 2, 2, 10, 0),
        row(2, 3, 1, 1, 10, 0),
    ]
    result = MODULE.parse_group(last)
    assert result["selection_reason"] == "last"
    assert result["selected_local_index"] == 3
    assert result["reverse_needed_attempts"] == 1

    malformed = dict(threshold[0])
    malformed["canonical_score"] = "8"
    try:
        MODULE.parse_group([malformed])
    except ValueError as error:
        assert "canonical score mismatch" in str(error)
    else:
        raise AssertionError("canonical mismatch was not rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
