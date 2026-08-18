#!/usr/bin/env python3
"""Replay exact long-query consumer decisions and compute host-only floors.

This tool consumes the development trace emitted by
FASIM_LONG_QUERY_GPU_CONSUMER_LOWER_BOUND_TRACE.  It never runs CUDA and it
does not invent a witness certificate: absent an explicit, independently
validated witness column, F2 is conservatively equal to F1.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Iterator


REQUIRED_COLUMNS = (
    "task_id", "scoreinfo_index", "scoreinfo_position", "scoreinfo_score",
    "attempt_index", "identity_round", "start", "cutlength", "prealign_score",
    "forward_score", "reverse_score", "canonical_score", "query_end",
    "ref_end_local", "ref_end_global", "terminal", "numeric_path",
    "padded_target_length", "query_length", "forward_cells", "reverse_cells",
)


def integer(row: dict[str, str], key: str) -> int:
    try:
        return int(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid integer {key}={row.get(key)!r}") from exc


def parse_group(rows: list[dict[str, str]]) -> dict[str, object]:
    """Replay one scoreInfo group in the original ordered consumer order."""

    if not rows:
        raise ValueError("empty scoreInfo group")
    group = integer(rows[0], "scoreinfo_index")
    expected_group = group
    full_forward_cells = 0
    full_reverse_cells = 0
    reverse_needed: set[int] = set()
    selected_index: int | None = None
    selection_reason = "empty"
    best_score = 0
    best_index: int | None = None
    processed = 0

    for index, row in enumerate(rows):
        if integer(row, "scoreinfo_index") != expected_group:
            raise ValueError("scoreInfo group changed inside group")
        forward = integer(row, "forward_score")
        reverse = integer(row, "reverse_score")
        canonical = integer(row, "canonical_score")
        prealign = integer(row, "prealign_score")
        terminal = integer(row, "terminal") != 0
        if forward < 0 or reverse < 0 or canonical < 0:
            raise ValueError("negative score in trace")
        if canonical != min(forward, reverse):
            raise ValueError(
                f"canonical score mismatch group={group} index={index}: "
                f"{canonical} != min({forward},{reverse})"
            )
        if terminal != (integer(row, "ref_end_local") == integer(row, "cutlength") - 1):
            raise ValueError(f"terminal mismatch group={group} index={index}")
        forward_cells = integer(row, "forward_cells")
        reverse_cells = integer(row, "reverse_cells")
        if forward_cells < 0 or reverse_cells < 0:
            raise ValueError("negative DP-cell proxy")
        full_forward_cells += forward_cells
        full_reverse_cells += reverse_cells

        # Once a threshold is emitted the ordered consumer does not inspect
        # later attempts.  The trace still contains them, so they remain in
        # full_* totals but not in the minimum prefix.
        if selected_index is not None:
            continue
        processed = index + 1

        if forward >= prealign:
            reverse_needed.add(index)
            if canonical >= prealign:
                selected_index = index
                selection_reason = "threshold"
                continue
            if terminal and canonical > best_score:
                best_score = canonical
                best_index = index
        elif terminal and forward > best_score:
            # Forward is an upper bound.  A terminal attempt can improve best
            # only when its upper bound is strictly above the current exact
            # best, so all other reverse requests are provably unnecessary.
            reverse_needed.add(index)
            if canonical > best_score:
                best_score = canonical
                best_index = index

    if selected_index is None:
        if best_index is not None:
            selected_index = best_index
            selection_reason = "best_fallback"
        else:
            last_index = len(rows) - 1
            if last_index not in reverse_needed:
                reverse_needed.add(last_index)
            if integer(rows[last_index], "canonical_score") != 0:
                selected_index = last_index
                selection_reason = "last"

    minimum_forward_cells = sum(
        integer(row, "forward_cells") for row in rows[:processed]
    )
    minimum_reverse_cells = sum(
        integer(rows[index], "reverse_cells") for index in sorted(reverse_needed)
    )
    return {
        "group_id": group,
        "attempt_count": len(rows),
        "processed_forward_attempts": processed,
        "selected_local_index": selected_index,
        "selected_attempt_index": (
            integer(rows[selected_index], "attempt_index")
            if selected_index is not None else None
        ),
        "selection_reason": selection_reason,
        "reverse_needed_attempts": len(reverse_needed),
        "full_forward_cells": full_forward_cells,
        "full_reverse_cells": full_reverse_cells,
        "minimum_forward_cells": minimum_forward_cells,
        "minimum_reverse_cells": minimum_reverse_cells,
        "witness_certified_forward_cells": 0,
        "witness_status": "uncertified",
    }


def iter_groups(handle: Iterable[dict[str, str]]) -> Iterator[list[dict[str, str]]]:
    current_key: tuple[int, int] | None = None
    current: list[dict[str, str]] = []
    previous_attempt: dict[int, int] = {}
    for row in handle:
        key = (integer(row, "task_id"), integer(row, "scoreinfo_index"))
        attempt_index = integer(row, "attempt_index")
        if key[0] in previous_attempt and attempt_index <= previous_attempt[key[0]]:
            raise ValueError(f"attempt order is not strictly increasing for task={key[0]}")
        previous_attempt[key[0]] = attempt_index
        if current_key is not None and key < current_key:
            raise ValueError("trace task/group order is not monotonic")
        if current_key is not None and key != current_key:
            yield current
            current = []
        current_key = key
        current.append(row)
    if current:
        yield current


def read_consumer_timing(path: Path | None) -> dict[str, float]:
    if path is None:
        return {}
    totals: dict[str, float] = defaultdict(float)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            for key in (
                "score_seconds", "gpu_kernel_seconds", "h2d_seconds",
                "d2h_seconds", "select_seconds", "traceback_seconds",
                "convert_seconds", "total_seconds",
            ):
                if row.get(key):
                    totals[key] += float(row[key])
    return dict(totals)


def read_consumer_counts(path: Path | None) -> dict[str, int]:
    if path is None:
        return {}
    totals: dict[str, int] = defaultdict(int)
    task_rows = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            task_rows += 1
            for key in (
                "scoreinfo_groups", "attempts", "gpu_scored_attempts",
                "control_selected_attempts", "threshold_groups",
                "best_fallback_groups", "last_groups", "empty_groups",
                "cpu_oracle_attempts", "cpu_reference_align_attempts",
                "cpu_continuation_failures",
            ):
                if row.get(key):
                    totals[key] += int(row[key])
    totals["task_rows"] = task_rows
    return dict(totals)


def projected_wall(
    *,
    all_reverse_wall: float | None,
    all_reverse_kernel: float | None,
    forward_kernel: float | None,
    reverse_kernel: float | None,
    forward_fraction: float,
    reverse_fraction: float,
) -> float | None:
    values = (all_reverse_wall, all_reverse_kernel, forward_kernel, reverse_kernel)
    if any(value is None for value in values):
        return None
    non_dp_floor = float(all_reverse_wall) - float(all_reverse_kernel)
    return non_dp_floor + float(forward_kernel) * forward_fraction + float(reverse_kernel) * reverse_fraction


def audit(args: argparse.Namespace) -> dict[str, object]:
    totals: dict[str, int] = defaultdict(int)
    groups = 0
    tasks: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    selected_signature: list[tuple[int, int | None, str]] = []
    with args.trace.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = tuple(reader.fieldnames or ())
        missing = [column for column in REQUIRED_COLUMNS if column not in fields]
        if missing:
            raise ValueError(f"trace schema missing columns: {missing}")
        for group_rows in iter_groups(reader):
            result = parse_group(group_rows)
            groups += 1
            task_id = integer(group_rows[0], "task_id")
            task = tasks[task_id]
            task["groups"] += 1
            for key in (
                "attempt_count", "processed_forward_attempts", "reverse_needed_attempts",
                "full_forward_cells", "full_reverse_cells", "minimum_forward_cells",
                "minimum_reverse_cells", "witness_certified_forward_cells",
            ):
                totals[key] += int(result[key])
                task[key] += int(result[key])
            reason = str(result["selection_reason"])
            totals[f"groups_{reason}"] += 1
            task[f"groups_{reason}"] += 1
            selected_signature.append((task_id, result["selected_attempt_index"], reason))

    if groups == 0:
        raise ValueError("trace contains no groups")
    totals["groups"] = groups
    totals["tasks"] = len(tasks)
    totals["witness_certified_groups"] = 0
    totals["witness_eligible_groups"] = 0

    full_dp = totals["full_forward_cells"] + totals["full_reverse_cells"]
    minimum_f1 = totals["minimum_forward_cells"] + totals["minimum_reverse_cells"]
    f1_forward_fraction = (
        totals["minimum_forward_cells"] / totals["full_forward_cells"]
        if totals["full_forward_cells"] else 0.0
    )
    f1_reverse_fraction = (
        totals["minimum_reverse_cells"] / totals["full_reverse_cells"]
        if totals["full_reverse_cells"] else 0.0
    )
    totals["minimum_f1_dp_cells"] = minimum_f1
    totals["full_dp_cells"] = full_dp
    totals["minimum_f1_dp_cell_fraction_ppm"] = int(
        round((minimum_f1 / full_dp if full_dp else 0.0) * 1_000_000)
    )

    timing = read_consumer_timing(args.consumer_report)
    consumer_counts = read_consumer_counts(args.consumer_report)
    telemetry_mismatches: list[str] = []
    count_pairs = (
        ("groups", "scoreinfo_groups"),
        ("attempt_count", "attempts"),
        ("attempt_count", "gpu_scored_attempts"),
        ("groups_threshold", "threshold_groups"),
        ("groups_best_fallback", "best_fallback_groups"),
        ("groups_last", "last_groups"),
    )
    for trace_key, consumer_key in count_pairs:
        if consumer_counts and totals[trace_key] != consumer_counts.get(consumer_key):
            telemetry_mismatches.append(
                f"{trace_key}={totals[trace_key]} != {consumer_key}={consumer_counts.get(consumer_key)}"
            )
    if consumer_counts:
        selected = totals["groups_threshold"] + totals["groups_best_fallback"] + totals["groups_last"]
        if selected != consumer_counts.get("control_selected_attempts"):
            telemetry_mismatches.append("selected outcome count mismatch")
        if consumer_counts.get("cpu_oracle_attempts", 0) != 0:
            telemetry_mismatches.append("CPU all-attempt oracle was nonzero")
        if consumer_counts.get("cpu_reference_align_attempts", 0) != 0:
            telemetry_mismatches.append("CPU reference replay was nonzero")
        if consumer_counts.get("cpu_continuation_failures", 0) != 0:
            telemetry_mismatches.append("selected continuation failed")
    all_reverse_wall = args.all_reverse_wall
    all_reverse_kernel = args.all_reverse_kernel
    forward_kernel = args.forward_only_kernel
    reverse_kernel = (
        all_reverse_kernel - forward_kernel
        if all_reverse_kernel is not None and forward_kernel is not None else None
    )
    if reverse_kernel is not None and reverse_kernel < 0:
        raise ValueError("all-reverse kernel is below forward-only kernel")
    f1_projected = projected_wall(
        all_reverse_wall=all_reverse_wall,
        all_reverse_kernel=all_reverse_kernel,
        forward_kernel=forward_kernel,
        reverse_kernel=reverse_kernel,
        forward_fraction=f1_forward_fraction,
        reverse_fraction=f1_reverse_fraction,
    )
    # No independent subview witness is emitted by this epoch.  F2 therefore
    # remains the conservative F1 work, and is explicitly not an authorization.
    f2_projected = f1_projected
    cpu_budget = (
        args.cpu_authority_wall / args.target_speedup
        if args.cpu_authority_wall is not None and args.target_speedup > 0 else None
    )
    margin_budget = cpu_budget * args.engineering_margin if cpu_budget is not None else None

    f0 = {
        "downstream_consumer_seconds": timing.get("total_seconds", 0.0) - timing.get("score_seconds", 0.0),
        "post_d2h_wall_seconds": (
            all_reverse_wall - timing.get("score_seconds", 0.0)
            if all_reverse_wall is not None and timing.get("score_seconds") is not None else None
        ),
        "zero_gpu_kernel_wall_seconds": (
            all_reverse_wall - all_reverse_kernel
            if all_reverse_wall is not None and all_reverse_kernel is not None else None
        ),
        "cached_endpoint_replay_executed": False,
        "status": "diagnostic_residual_only",
        "interpretation": "diagnostic floors; cached endpoint replay is not a product runtime",
    }
    result: dict[str, object] = {
        "schema_version": "long_query_consumer_driven_lower_bound_audit_v1",
        "trace": str(args.trace),
        "consumer_report": str(args.consumer_report) if args.consumer_report else None,
        "groups": dict(totals),
        "tasks": (
            {str(key): dict(value) for key, value in sorted(tasks.items())}
            if args.include_task_details else {"count": len(tasks)}
        ),
        "consumer_counts": consumer_counts,
        "telemetry_comparison": {
            "mismatches": telemetry_mismatches,
            "exact": not telemetry_mismatches,
        },
        "timing": timing,
        "f0": f0,
        "f1": {
            "minimum_forward_cell_fraction": f1_forward_fraction,
            "minimum_reverse_cell_fraction": f1_reverse_fraction,
            "projected_wall_seconds": f1_projected,
            "reverse_work_definition": "exact lazy reverse requests from ordered upper-bound replay",
        },
        "f2": {
            "witness_status": "uncertified",
            "weighted_forward_witness_coverage": 0.0,
            "projected_wall_seconds": f2_projected,
            "decision": "not_authorized_without_independent_subview_witness",
        },
        "gate": {
            "cpu_authority_wall_seconds": args.cpu_authority_wall,
            "target_speedup": args.target_speedup,
            "budget_wall_seconds": cpu_budget,
            "engineering_margin": args.engineering_margin,
            "conservative_budget_seconds": margin_budget,
            "f1_within_budget": f1_projected is not None and margin_budget is not None and f1_projected <= margin_budget,
            "f2_within_budget": f2_projected is not None and margin_budget is not None and f2_projected <= margin_budget,
            "f0_within_budget": None,
            "replay_vs_runtime_exact": not telemetry_mismatches,
            "cuda_authorized": False,
            "decision": "no_go_f0_or_witness_missing",
        },
        "selected_signature_sha256": hashlib.sha256(
            "".join(f"{task}:{index}:{reason}\n" for task, index, reason in selected_signature).encode()
        ).hexdigest(),
    }
    if args.output_file is not None:
        digest = hashlib.sha256(args.output_file.read_bytes()).hexdigest()
        result["output"] = {
            "path": str(args.output_file),
            "sha256": digest,
            "expected_sha256": args.expected_output_sha256,
            "matches_expected": (
                args.expected_output_sha256 is None or digest == args.expected_output_sha256
            ),
        }
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--consumer-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--expected-output-sha256")
    parser.add_argument("--include-task-details", action="store_true")
    parser.add_argument("--all-reverse-wall", type=float)
    parser.add_argument("--all-reverse-kernel", type=float)
    parser.add_argument("--forward-only-kernel", type=float)
    parser.add_argument("--cpu-authority-wall", type=float)
    parser.add_argument("--target-speedup", type=float, default=1.5)
    parser.add_argument(
        "--engineering-margin", type=float, default=0.90,
        help="fraction of the formal speedup budget required before CUDA authorization",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = audit(args)
    except (OSError, ValueError) as exc:
        print(f"lower-bound audit failed: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema_version": result["schema_version"],
        "groups": result["groups"],
        "f0": result["f0"],
        "f1": result["f1"],
        "f2": result["f2"],
        "gate": result["gate"],
        "telemetry_comparison": result["telemetry_comparison"],
        "output": result.get("output"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
