#!/usr/bin/env python3
"""Differentially audit byte scoreInfo state storage and H-buffer layouts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


SCHEMA_VERSION = "long_query_scoreinfo_state_layout_audit_v1"
LANES = 16
BIAS = 4
GAP_OPEN = 16
GAP_EXTEND = 4
PROFILE_SCORES = frozenset((-4, 0, 5))
Column = List[List[int]]


def sat_u8_add(left: int, right: int) -> int:
    value = left + right
    return 255 if value > 255 else value


def sat_u8_sub(left: int, right: int) -> int:
    value = left - right
    return value if value > 0 else 0


def signed_i8(value: int) -> int:
    if value < 0 or value > 255:
        raise ValueError("signed byte conversion requires a byte value")
    return value - 256 if value >= 128 else value


def shift_left(values: Sequence[int]) -> List[int]:
    if len(values) != LANES:
        raise ValueError("lane vector has the wrong width")
    return [0, *values[:-1]]


def validate_columns(columns: Sequence[Column]) -> int:
    if not columns:
        raise ValueError("at least one target column is required")
    segment_count = len(columns[0])
    if segment_count <= 0:
        raise ValueError("at least one profile segment is required")
    for column in columns:
        if len(column) != segment_count:
            raise ValueError("column segment count drift")
        for segment in column:
            if len(segment) != LANES:
                raise ValueError("profile segment has the wrong lane count")
            if any(score not in PROFILE_SCORES for score in segment):
                raise ValueError("profile score is outside the 5/-4 byte contract")
    return segment_count


def trace_digest(trace: Sequence[Tuple[int, Sequence[int], Sequence[int]]]) -> str:
    digest = hashlib.sha256()
    for column_maximum, e_state, h_state in trace:
        digest.update(bytes((column_maximum,)))
        digest.update(bytes(e_state))
        digest.update(bytes(h_state))
    return digest.hexdigest()


def result_from_trace(
    trace: List[Tuple[int, Tuple[int, ...], Tuple[int, ...]]],
    saturating_add_255_observed: bool,
) -> Dict[str, object]:
    return {
        "column_maxima": tuple(row[0] for row in trace),
        "final_e": trace[-1][1],
        "final_h": trace[-1][2],
        "max_observed_state": max(
            max((row[0], *row[1], *row[2])) for row in trace
        ),
        "saturating_add_255_observed": saturating_add_255_observed,
        "trace_sha256": trace_digest(trace),
    }


def run_double_buffer(
    columns: Sequence[Column], storage_bytes: int
) -> Dict[str, object]:
    if storage_bytes not in (1, 2):
        raise ValueError("storage width must be one or two bytes")
    segment_count = validate_columns(columns)
    state_count = segment_count * LANES
    e_state = [0] * state_count
    h_load = [0] * state_count
    h_store = [0] * state_count
    trace: List[Tuple[int, Tuple[int, ...], Tuple[int, ...]]] = []
    saturating_add_255_observed = False

    def store(value: int) -> int:
        if value < 0 or value > 255:
            raise AssertionError("byte recurrence escaped the uint8 range")
        return value

    for column in columns:
        v_f = [0] * LANES
        tail = h_load[(segment_count - 1) * LANES : segment_count * LANES]
        v_h = shift_left(tail)
        column_lane_maximum = [0] * LANES

        for segment_index, profile_scores in enumerate(column):
            offset = segment_index * LANES
            old_h = h_load[offset : offset + LANES]
            for lane in range(LANES):
                added = sat_u8_add(v_h[lane], profile_scores[lane])
                saturating_add_255_observed |= added == 255
                value = sat_u8_sub(added, BIAS)
                value = max(value, e_state[offset + lane], v_f[lane])
                h_store[offset + lane] = store(value)
                column_lane_maximum[lane] = max(
                    column_lane_maximum[lane], value
                )
                opened = sat_u8_sub(value, GAP_OPEN)
                extended_e = sat_u8_sub(e_state[offset + lane], GAP_EXTEND)
                e_state[offset + lane] = store(max(extended_e, opened))
                extended_f = sat_u8_sub(v_f[lane], GAP_EXTEND)
                v_f[lane] = max(extended_f, opened)
            v_h = old_h

        lazy_done = False
        for _ in range(LANES):
            if lazy_done:
                break
            v_f = shift_left(v_f)
            for segment_index in range(segment_count):
                offset = segment_index * LANES
                should_continue = []
                for lane in range(LANES):
                    stored = max(h_store[offset + lane], v_f[lane])
                    h_store[offset + lane] = store(stored)
                    column_lane_maximum[lane] = max(
                        column_lane_maximum[lane], stored
                    )
                    opened = sat_u8_sub(stored, GAP_OPEN)
                    v_f[lane] = sat_u8_sub(v_f[lane], GAP_EXTEND)
                    should_continue.append(
                        signed_i8(v_f[lane]) > signed_i8(opened)
                    )
                if not any(should_continue):
                    lazy_done = True
                    break

        h_load, h_store = h_store, h_load
        trace.append(
            (max(column_lane_maximum), tuple(e_state), tuple(h_load))
        )
    return result_from_trace(trace, saturating_add_255_observed)


def run_in_place(columns: Sequence[Column]) -> Dict[str, object]:
    segment_count = validate_columns(columns)
    state_count = segment_count * LANES
    e_state = [0] * state_count
    h_state = [0] * state_count
    trace: List[Tuple[int, Tuple[int, ...], Tuple[int, ...]]] = []
    saturating_add_255_observed = False

    def store(value: int) -> int:
        if value < 0 or value > 255:
            raise AssertionError("byte recurrence escaped the uint8 range")
        return value

    for column in columns:
        v_f = [0] * LANES
        tail = h_state[(segment_count - 1) * LANES : segment_count * LANES]
        v_h = shift_left(tail)
        column_lane_maximum = [0] * LANES

        for segment_index, profile_scores in enumerate(column):
            offset = segment_index * LANES
            old_h = h_state[offset : offset + LANES]
            for lane in range(LANES):
                added = sat_u8_add(v_h[lane], profile_scores[lane])
                saturating_add_255_observed |= added == 255
                value = sat_u8_sub(added, BIAS)
                value = max(value, e_state[offset + lane], v_f[lane])
                h_state[offset + lane] = store(value)
                column_lane_maximum[lane] = max(
                    column_lane_maximum[lane], value
                )
                opened = sat_u8_sub(value, GAP_OPEN)
                extended_e = sat_u8_sub(e_state[offset + lane], GAP_EXTEND)
                e_state[offset + lane] = store(max(extended_e, opened))
                extended_f = sat_u8_sub(v_f[lane], GAP_EXTEND)
                v_f[lane] = max(extended_f, opened)
            v_h = old_h

        lazy_done = False
        for _ in range(LANES):
            if lazy_done:
                break
            v_f = shift_left(v_f)
            for segment_index in range(segment_count):
                offset = segment_index * LANES
                should_continue = []
                for lane in range(LANES):
                    stored = max(h_state[offset + lane], v_f[lane])
                    h_state[offset + lane] = store(stored)
                    column_lane_maximum[lane] = max(
                        column_lane_maximum[lane], stored
                    )
                    opened = sat_u8_sub(stored, GAP_OPEN)
                    v_f[lane] = sat_u8_sub(v_f[lane], GAP_EXTEND)
                    should_continue.append(
                        signed_i8(v_f[lane]) > signed_i8(opened)
                    )
                if not any(should_continue):
                    lazy_done = True
                    break

        trace.append(
            (max(column_lane_maximum), tuple(e_state), tuple(h_state))
        )
    return result_from_trace(trace, saturating_add_255_observed)


def constant_columns(segment_count: int, column_count: int, score: int) -> List[Column]:
    if score not in PROFILE_SCORES:
        raise ValueError("invalid constant profile score")
    return [
        [[score for _ in range(LANES)] for _ in range(segment_count)]
        for _ in range(column_count)
    ]


def random_columns(segment_count: int, column_count: int, seed: int) -> List[Column]:
    state = seed & 0xFFFFFFFF
    choices = (-4, 0, 5)
    columns = []
    for _ in range(column_count):
        column = []
        for _ in range(segment_count):
            segment = []
            for _ in range(LANES):
                state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
                segment.append(choices[(state >> 16) % len(choices)])
            column.append(segment)
        columns.append(column)
    return columns


def derive_range_invariant() -> Dict[str, object]:
    h_storage_max = 0
    gap_storage_max = 0
    transient_add_min = 0
    transient_add_max = 0
    iterations = 0
    while True:
        iterations += 1
        transient_add_values = [
            sat_u8_add(h_value, score)
            for h_value in range(h_storage_max + 1)
            for score in PROFILE_SCORES
        ]
        transient_add_min = min(transient_add_min, min(transient_add_values))
        transient_add_max = max(transient_add_max, max(transient_add_values))
        diagonal_max = max(
            sat_u8_sub(value, BIAS) for value in transient_add_values
        )
        next_h_storage_max = max(diagonal_max, gap_storage_max)
        opened_max = max(
            sat_u8_sub(value, GAP_OPEN)
            for value in range(next_h_storage_max + 1)
        )
        extended_gap_max = sat_u8_sub(gap_storage_max, GAP_EXTEND)
        next_gap_storage_max = max(opened_max, extended_gap_max)
        if (
            next_h_storage_max == h_storage_max
            and next_gap_storage_max == gap_storage_max
        ):
            break
        h_storage_max = next_h_storage_max
        gap_storage_max = next_gap_storage_max
        if iterations > 512:
            raise AssertionError("byte recurrence range invariant did not converge")
    return {
        "base_state": 0,
        "fixed_point_iterations": iterations,
        "transient_add_min": transient_add_min,
        "transient_add_max": transient_add_max,
        "diagonal_after_bias_min": sat_u8_sub(transient_add_min, BIAS),
        "diagonal_after_bias_max": sat_u8_sub(transient_add_max, BIAS),
        "inductive_h_storage_max": h_storage_max,
        "opened_gap_max": sat_u8_sub(h_storage_max, GAP_OPEN),
        "extended_prior_gap_max": sat_u8_sub(
            gap_storage_max, GAP_EXTEND
        ),
        "inductive_e_f_storage_max": gap_storage_max,
        "uint8_storage_safe": (
            h_storage_max <= 255 and gap_storage_max <= 255
        ),
    }


def audit_case(case_id: str, columns: Sequence[Column]) -> Dict[str, object]:
    int16_result = run_double_buffer(columns, 2)
    uint8_result = run_double_buffer(columns, 1)
    inplace_result = run_in_place(columns)
    if int16_result != uint8_result:
        raise AssertionError(f"uint8 three-state mismatch in {case_id}")
    if int16_result != inplace_result:
        raise AssertionError(f"uint8 in-place mismatch in {case_id}")
    return {
        "case_id": case_id,
        "segments": len(columns[0]),
        "columns": len(columns),
        "max_observed_state": int16_result["max_observed_state"],
        "saturating_add_255_observed": int16_result[
            "saturating_add_255_observed"
        ],
        "trace_sha256": int16_result["trace_sha256"],
        "three_state_uint8_exact": True,
        "two_state_inplace_exact": True,
    }


def build_audit(source_commit: str = "unbound") -> Dict[str, object]:
    cases = [
        audit_case("all_mismatch", constant_columns(3, 97, -4)),
        audit_case("all_padding", constant_columns(2, 97, 0)),
        audit_case("all_match_byte_ceiling", constant_columns(20, 400, 5)),
        audit_case("random_1x257", random_columns(1, 257, 0x243F6A88)),
        audit_case("random_3x129", random_columns(3, 129, 0x85A308D3)),
        audit_case("random_17x96", random_columns(17, 96, 0x13198A2E)),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "source_commit": source_commit,
        "contract": {
            "lanes": LANES,
            "profile_scores": sorted(PROFILE_SCORES),
            "bias": BIAS,
            "gap_open": GAP_OPEN,
            "gap_extend": GAP_EXTEND,
            "lazy_f_signed_byte_compare": True,
            "lazy_f_max_passes": LANES,
        },
        "range_invariant": derive_range_invariant(),
        "cases": cases,
        "summary": {
            "cases": len(cases),
            "columns": sum(int(case["columns"]) for case in cases),
            "saturating_add_255_observed": any(
                bool(case["saturating_add_255_observed"]) for case in cases
            ),
            "three_state_uint8_differential_mismatches": 0,
            "two_state_inplace_differential_mismatches": 0,
        },
        "decisions": {
            "main_scoreinfo_uint8_three_state_dependency_audit": "pass",
            "main_scoreinfo_uint8_two_state_dependency_audit": "pass_bounded_cpu_model",
            "cuda_kernel_implementation": "not_authorized_before_ncu_and_cuda_shadow",
            "production_authorized": False,
        },
    }


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".tmp.", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", default="unbound")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build_audit(args.source_commit)
    if args.output is not None:
        write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
