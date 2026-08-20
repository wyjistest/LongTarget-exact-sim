#!/usr/bin/env python3
"""Model static SM residency for the long-query scoreInfo and F1 kernels."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List


SCHEMA_VERSION = "long_query_gpu_resource_model_v1"
DEFAULT_QUERY_LENGTHS = (8000, 11498, 12397)
DEVICE = {
    "name": "NVIDIA GeForce RTX 4090",
    "compute_capability": "8.9",
    "multiprocessors": 128,
    "warp_size": 32,
    "max_threads_per_sm": 1536,
    "max_blocks_per_sm": 24,
    "registers_per_sm": 65536,
    "shared_bytes_per_sm": 102400,
    "default_shared_bytes_per_block": 49152,
    "optin_shared_bytes_per_block": 101376,
}
KERNELS = {
    "main_scoreinfo_current_int16_3state": {
        "kernel": "prealign_cuda_column_max_legacy_byte_batch_kernel",
        "segment_width": 32,
        "state_buffers": 3,
        "state_bytes": 2,
        "state_lanes": 16,
        "threads_per_block": 32,
        "useful_lanes": 16,
        "registers_per_thread": 26,
        "spill_bytes": 0,
    },
    "main_scoreinfo_uint8_3state_candidate": {
        "kernel": "candidate_not_implemented",
        "segment_width": 32,
        "state_buffers": 3,
        "state_bytes": 1,
        "state_lanes": 16,
        "threads_per_block": 32,
        "useful_lanes": 16,
        "registers_per_thread": 26,
        "spill_bytes": 0,
    },
    "main_scoreinfo_uint8_2state_candidate": {
        "kernel": "candidate_not_implemented",
        "segment_width": 32,
        "state_buffers": 2,
        "state_bytes": 1,
        "state_lanes": 16,
        "threads_per_block": 32,
        "useful_lanes": 16,
        "registers_per_thread": 26,
        "spill_bytes": 0,
    },
    "f1_forward_current_uint8_3state": {
        "kernel": "prealign_cuda_exact_attempt_forward_byte_kernel",
        "segment_width": 16,
        "state_buffers": 3,
        "state_bytes": 1,
        "state_lanes": 16,
        "threads_per_block": 32,
        "useful_lanes": 16,
        "registers_per_thread": 38,
        "spill_bytes": 0,
    },
    "f1_forward_uint8_2state_candidate": {
        "kernel": "candidate_not_implemented",
        "segment_width": 16,
        "state_buffers": 2,
        "state_bytes": 1,
        "state_lanes": 16,
        "threads_per_block": 32,
        "useful_lanes": 16,
        "registers_per_thread": 38,
        "spill_bytes": 0,
    },
}


def ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor


def model_kernel(query_length: int, spec: Dict[str, object]) -> Dict[str, object]:
    if query_length <= 0:
        raise ValueError("query length must be positive")
    state_lanes = int(spec["state_lanes"])
    segment_width = int(spec["segment_width"])
    threads = int(spec["threads_per_block"])
    registers = int(spec["registers_per_thread"])
    segment_length = ceil_div(query_length, segment_width)
    state_elements = segment_length * state_lanes
    dynamic_shared = (
        int(spec["state_buffers"])
        * state_elements
        * int(spec["state_bytes"])
    )
    resource_fit = dynamic_shared <= DEVICE["optin_shared_bytes_per_block"]
    blocks_by_shared = (
        DEVICE["shared_bytes_per_sm"] // dynamic_shared if dynamic_shared else 0
    )
    blocks_by_threads = DEVICE["max_threads_per_sm"] // threads
    blocks_by_registers = DEVICE["registers_per_sm"] // (threads * registers)
    resident_blocks = (
        min(
            DEVICE["max_blocks_per_sm"],
            blocks_by_shared,
            blocks_by_threads,
            blocks_by_registers,
        )
        if resource_fit
        else 0
    )
    max_warps = DEVICE["max_threads_per_sm"] // DEVICE["warp_size"]
    resident_warps = resident_blocks * ceil_div(threads, DEVICE["warp_size"])
    scheduler_occupancy = resident_warps / max_warps
    useful_lane_occupancy = scheduler_occupancy * int(spec["useful_lanes"]) / threads
    return {
        **spec,
        "query_length": query_length,
        "segment_length": segment_length,
        "state_elements_per_buffer": state_elements,
        "dynamic_shared_bytes_per_block": dynamic_shared,
        "uses_optin_shared_memory": dynamic_shared
        > DEVICE["default_shared_bytes_per_block"],
        "resource_fit": resource_fit,
        "blocks_by_shared_memory": blocks_by_shared,
        "blocks_by_threads": blocks_by_threads,
        "blocks_by_registers": blocks_by_registers,
        "predicted_resident_blocks_per_sm": resident_blocks,
        "predicted_resident_warps_per_sm": resident_warps,
        "predicted_scheduler_occupancy": scheduler_occupancy,
        "predicted_useful_lane_occupancy": useful_lane_occupancy,
    }


def build_model(
    query_lengths: List[int], source_commit: str = "unbound"
) -> Dict[str, object]:
    if not query_lengths:
        raise ValueError("at least one query length is required")
    queries = []
    for query_length in query_lengths:
        kernels = {
            name: model_kernel(query_length, spec)
            for name, spec in KERNELS.items()
        }
        main_current = kernels["main_scoreinfo_current_int16_3state"]
        main_uint8 = kernels["main_scoreinfo_uint8_3state_candidate"]
        main_two_state = kernels["main_scoreinfo_uint8_2state_candidate"]
        f1_current = kernels["f1_forward_current_uint8_3state"]
        f1_two_state = kernels["f1_forward_uint8_2state_candidate"]
        queries.append(
            {
                "query_length": query_length,
                "kernels": kernels,
                "derived": {
                    "main_uint8_3state_shared_reduction": 1.0
                    - main_uint8["dynamic_shared_bytes_per_block"]
                    / main_current["dynamic_shared_bytes_per_block"],
                    "main_uint8_2state_shared_reduction": 1.0
                    - main_two_state["dynamic_shared_bytes_per_block"]
                    / main_current["dynamic_shared_bytes_per_block"],
                    "f1_2state_shared_reduction": 1.0
                    - f1_two_state["dynamic_shared_bytes_per_block"]
                    / f1_current["dynamic_shared_bytes_per_block"],
                    "main_current_to_uint8_2state_resident_block_ratio": (
                        main_two_state["predicted_resident_blocks_per_sm"]
                        / main_current["predicted_resident_blocks_per_sm"]
                    ),
                    "f1_current_to_2state_resident_block_ratio": (
                        f1_two_state["predicted_resident_blocks_per_sm"]
                        / f1_current["predicted_resident_blocks_per_sm"]
                    ),
                },
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "source_commit": source_commit,
        "device": DEVICE,
        "static_compile": {
            "cuda": "12.5.82",
            "architecture": "sm_89",
            "main_scoreinfo_registers_per_thread": 26,
            "f1_forward_registers_per_thread": 38,
            "spills": 0,
        },
        "queries": queries,
        "decisions": {
            "main_scoreinfo_uint8_state": "authorized_for_ncu_and_bounded_design_only",
            "main_scoreinfo_kernel_implementation": "not_authorized_before_ncu",
            "f1_two_state_static_footprint_gate": "pass",
            "f1_kernel_implementation": "not_authorized_until_runtime_traffic_or_stall_evidence",
            "dual_contract": "no_go",
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
    parser.add_argument("--query-length", type=int, action="append")
    parser.add_argument("--source-commit", default="unbound")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    lengths = args.query_length or list(DEFAULT_QUERY_LENGTHS)
    payload = build_model(lengths, args.source_commit)
    if args.output is not None:
        write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
