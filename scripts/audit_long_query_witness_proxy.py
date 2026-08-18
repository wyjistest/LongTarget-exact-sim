#!/usr/bin/env python3
"""Audit a conservative whole-target-to-subview witness proxy.

This intentionally computes only a lower-bound eligibility signal from the
frozen endpoint trace.  It does not claim a certificate: no target-start path
or deterministic tie upper bound is present in the trace, so strict coverage
remains zero.  The output is useful for deciding whether a future witness
engine is worth implementing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


REQUIRED = {
    "task_id", "scoreinfo_index", "attempt_index", "identity_round", "start",
    "cutlength", "prealign_score", "forward_score", "canonical_score",
    "query_end", "ref_end_local", "numeric_path", "forward_cells",
}


def integer(row: dict[str, str], key: str) -> int:
    return int(row[key])


def iter_groups(reader):
    current = []
    key = None
    for row in reader:
        next_key = (integer(row, "task_id"), integer(row, "scoreinfo_index"))
        if key is not None and next_key != key:
            yield current
            current = []
        key = next_key
        current.append(row)
    if current:
        yield current


def audit(trace: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    with trace.open("rb") as raw:
        for block in iter(lambda: raw.read(8 * 1024 * 1024), b""):
            digest.update(block)
    trace_digest = digest.hexdigest()
    groups = 0
    total_forward_cells = 0
    lower_bound_cells = 0
    lower_bound_groups = 0
    first_attempt_threshold_groups = 0
    ambiguous_groups = 0
    invalid_groups = 0
    not_terminal_groups = 0
    invalid_numeric_path_groups = 0
    invalid_span_groups = 0
    by_path = Counter()
    by_cutlength = Counter()
    with trace.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = set(reader.fieldnames or ())
        missing = sorted(REQUIRED - fields)
        if missing:
            raise ValueError(f"trace schema missing columns: {missing}")
        for rows in iter_groups(reader):
            groups += 1
            total_forward_cells += sum(integer(row, "forward_cells") for row in rows)
            first = rows[0]
            threshold = integer(first, "prealign_score")
            first_forward = integer(first, "forward_score")
            first_canonical = integer(first, "canonical_score")
            terminal = integer(first, "ref_end_local") == integer(first, "cutlength") - 1
            valid_path = integer(first, "numeric_path") in (1, 2)
            valid_span = integer(first, "start") >= 0 and integer(first, "cutlength") > 0
            if first_canonical >= threshold:
                first_attempt_threshold_groups += 1
            # This is a lower-bound-only witness candidate.  It establishes
            # that the observed endpoint score reaches threshold and is
            # terminal in the requested subview, but lacks path-start/tie proof.
            if first_canonical >= threshold and terminal and valid_path and valid_span:
                lower_bound_groups += 1
                lower_bound_cells += integer(first, "forward_cells")
                by_path[str(integer(first, "numeric_path"))] += 1
                by_cutlength[str(integer(first, "cutlength"))] += integer(first, "forward_cells")
            else:
                invalid_groups += 1
                if first_canonical >= threshold and not terminal:
                    not_terminal_groups += 1
                if first_canonical >= threshold and not valid_path:
                    invalid_numeric_path_groups += 1
                if first_canonical >= threshold and not valid_span:
                    invalid_span_groups += 1
            if first_forward != first_canonical:
                ambiguous_groups += 1
    return {
        "schema_version": "long_query_witness_proxy_audit_v1",
        "trace": str(trace),
        "trace_sha256": trace_digest,
        "groups": groups,
        "first_attempt_threshold_groups": first_attempt_threshold_groups,
        "lower_bound_only_groups": lower_bound_groups,
        "lower_bound_only_group_fraction": lower_bound_groups / groups if groups else 0.0,
        "full_forward_cells": total_forward_cells,
        "lower_bound_only_forward_cells": lower_bound_cells,
        "lower_bound_only_weighted_forward_fraction": lower_bound_cells / total_forward_cells if total_forward_cells else 0.0,
        "strict_certificate_groups": 0,
        "strict_certificate_weighted_forward_fraction": 0.0,
        "endpoint_path_start_proof": "missing",
        "whole_target_upper_bound_proof": "missing",
        "tie_break_proof": "missing",
        "ambiguous_forward_reverse_groups": ambiguous_groups,
        "groups_not_lower_bound_eligible": invalid_groups,
        "threshold_groups_not_terminal": not_terminal_groups,
        "threshold_groups_invalid_numeric_path": invalid_numeric_path_groups,
        "threshold_groups_invalid_span": invalid_span_groups,
        "lower_bound_numeric_path_groups": dict(sorted(by_path.items())),
        "lower_bound_cutlength_forward_cells": dict(sorted(by_cutlength.items(), key=lambda item: int(item[0]))),
        "decision": "witness_not_authorized_strict_proof_missing",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.trace)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
