#!/usr/bin/env python3
"""Freeze the balanced input-only Phase 4 attempt order."""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/bioinformatics_submission_readiness_v2"
INPUT_MANIFEST = PAPER / "phase_3_input_manifest.tsv"
OUTPUT = PAPER / "phase_3_attempt_manifest.tsv"
ORDER_SEED = "bioinformatics_submission_readiness_v2_phase4_order_20260731"
REPEATS = 5
OUTPUT_FIELDS = (
    "attempt_sequence_index",
    "pair_sequence_index",
    "pair_id",
    "attempt_id",
    "workload_id",
    "repeat_index",
    "arm_order",
    "arm_position",
    "arm",
    "query_path",
    "query_sequence_length",
    "query_sequence_sha256",
    "target_path",
    "target_sequence_length",
    "target_sequence_sha256",
    "query_ordinal_namespace",
    "query_source_ordinal",
    "target_ordinal_namespace",
    "target_source_ordinal",
    "assembly",
    "target_coordinate_namespace",
    "target_region_start0",
    "query_extraction_recipe_id",
    "target_extraction_recipe_id",
    "timeout_seconds",
    "cpu_affinity",
    "gpu_index",
    "attempt_generation",
    "formal_status",
)


def rank(workload_id: str, repeat_index: int) -> str:
    value = f"{ORDER_SEED}\t{workload_id}\t{repeat_index}".encode("ascii")
    return hashlib.sha256(value).hexdigest()


def build_rows(inputs: list[dict[str, str]]) -> list[dict[str, str]]:
    pairs = [
        (rank(row["workload_id"], repeat_index), row, repeat_index)
        for row in inputs
        for repeat_index in range(REPEATS)
    ]
    pairs.sort(key=lambda item: item[0])
    if len(pairs) != 50:
        raise ValueError("Phase 4 pair count must be 50")
    output: list[dict[str, str]] = []
    attempt_index = 0
    for pair_index, (_rank, source, repeat_index) in enumerate(pairs, 1):
        arm_order = "AG" if pair_index <= len(pairs) // 2 else "GA"
        pair_id = f"{source['workload_id']}__repeat{repeat_index:02d}"
        for arm_position, arm in enumerate(arm_order, 1):
            attempt_index += 1
            output.append(
                {
                    "attempt_sequence_index": str(attempt_index),
                    "pair_sequence_index": str(pair_index),
                    "pair_id": pair_id,
                    "attempt_id": f"v2p4_{attempt_index:03d}_{pair_id}_{arm.lower()}",
                    "workload_id": source["workload_id"],
                    "repeat_index": str(repeat_index),
                    "arm_order": arm_order,
                    "arm_position": str(arm_position),
                    "arm": arm,
                    "query_path": source["query_path"],
                    "query_sequence_length": source["query_sequence_length"],
                    "query_sequence_sha256": source["query_sequence_sha256"],
                    "target_path": source["target_path"],
                    "target_sequence_length": source["target_sequence_length"],
                    "target_sequence_sha256": source["target_sequence_sha256"],
                    "query_ordinal_namespace": source["query_ordinal_namespace"],
                    "query_source_ordinal": source["query_source_ordinal"],
                    "target_ordinal_namespace": source["target_ordinal_namespace"],
                    "target_source_ordinal": source["target_source_ordinal"],
                    "assembly": source["assembly"],
                    "target_coordinate_namespace": source["target_coordinate_namespace"],
                    "target_region_start0": source["target_region_start0"],
                    "query_extraction_recipe_id": source["query_extraction_recipe_id"],
                    "target_extraction_recipe_id": source["target_extraction_recipe_id"],
                    "timeout_seconds": "1800",
                    "cpu_affinity": "0-4,10-14",
                    "gpu_index": "0" if arm == "G" else "NA",
                    "attempt_generation": "1",
                    "formal_status": "preregistered_not_run",
                }
            )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true", required=True)
    parser.parse_args()
    if OUTPUT.exists():
        print(f"attempt manifest already exists: {OUTPUT}", file=sys.stderr)
        return 1
    with INPUT_MANIFEST.open(newline="", encoding="utf-8") as handle:
        inputs = list(csv.DictReader(handle, delimiter="\t"))
    try:
        rows = build_rows(inputs)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"froze {len(rows)} arm attempts across {len(rows) // 2} paired rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
