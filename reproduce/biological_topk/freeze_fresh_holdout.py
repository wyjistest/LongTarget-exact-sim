#!/usr/bin/env python3
"""Freeze the input-only Phase 3 biological Top-K fresh holdout."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
import tempfile
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk"
QUERY_UNIVERSE_PATH = PAPER / "query_source_universe.tsv.gz"
TARGET_UNIVERSE_PATH = PAPER / "target_source_universe.tsv.gz"
EXCLUSION_PATH = PAPER / "fresh_input_exclusion_registry.tsv"
SAMPLE_SIZE_PATH = PAPER / "sample_size_plan.json"
CONTRACT_PATH = PAPER / "contract_spec.json"
OPERATING_ENVELOPE_PATH = PAPER / "operating_envelope.json"
COMPARATOR_FREEZE_PATH = PAPER / "phase2_comparator_freeze.json"
RESOURCE_MODEL_PATH = PAPER / "resource_projection_model.json"
RESOURCE_PLAN_PATH = PAPER / "fresh_budget_projection_plan.json"
OWNER_QUOTA_PATH = PAPER / "owner_storage_quota_approval.json"
RUNTIME_RECEIPT_PATH = ROOT / "paper/bioinformatics/canonical_hybrid_v2_runtime.json"
AUTHORITY_BINARY_PATH = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/runtime-epoch1/fasim_longtarget_x86"
CANDIDATE_BINARY_PATH = ROOT / ".paper-artifacts/bioinformatics-canonical-hybrid-v2/runtime-epoch1/fasim_longtarget_gasal2"
COMPARATOR_PATH = ROOT / "reproduce/biological_topk/compare_candidate_topk.py"
RUNNER_PATH = ROOT / "reproduce/biological_topk/run_fresh_holdout.py"
ANALYZER_PATH = ROOT / "reproduce/biological_topk/analyze_fresh_holdout.py"

PLAN_PATH = PAPER / "fresh_holdout_plan.json"
MANIFEST_PATH = PAPER / "fresh_holdout_manifest.tsv"
ATTEMPT_PLAN_PATH = PAPER / "fresh_holdout_attempt_plan.tsv"
MANIFEST_CHECKSUM_PATH = PAPER / "fresh_holdout_manifest.sha256"
RESOURCE_PROJECTION_PATH = PAPER / "fresh_holdout_resource_projection.json"
RESOURCE_DECISION_PATH = PAPER / "fresh_holdout_resource_decision.json"

SELECTION_SEED = "biological_topk_phase3_panel_v1_20260730"
RESOURCE_MODEL_SHA256 = "8fb81ff5de6c51015954e1891a8e5cf96001e6a7fdd182debee3b922c2672286"
AUTHORITY_BINARY_SHA256 = "75c59f80ee329fe913edce71ea8a0ec1a63620a978b15d3673f636d62268822e"
CANDIDATE_BINARY_SHA256 = "ec40144f172711347068443f99f2ff1de02a192051cb2ada4f2c2476d4ff0cd9"
PARAMETER_BUNDLE_SHA256 = "110752c4078bc2b300ad4e92e2495ea868c365486e540da7002fc3e19a18241a"
PANEL_QUOTAS = {"short": 60, "medium": 59, "large": 59}
PAIRING_MATRIX = {
    "short": {"short": 20, "medium": 20, "large": 20},
    "medium": {"short": 20, "medium": 20, "large": 19},
    "large": {"short": 20, "medium": 19, "large": 20},
}
QUERY_LENGTH_BOUNDS = {
    "short": (500, 800),
    "medium": (801, 1600),
    "large": (1601, 2812),
}
QUERY_RECIPE = "gencode_v49_full_transcript_v1"
QUERY_SOURCE_PATH = ".tmp/bioinformatics_application_sources/gencode.v49.lncRNA_transcripts.fa.gz"
TARGET_SOURCE_PATHS = {
    "chr21": ".tmp/bioinformatics_application_sources/chr21.fa.gz",
    "chr22": ".tmp/bioinformatics_application_sources/chr22.fa.gz",
}
TECHNICAL_REPEATS_PER_TARGET_STRATUM = 2
CPU_AFFINITY = {0: "0-4,10-14", 1: "5-9,15-19"}
TIMEOUT_SECONDS = {"short": 3600, "medium": 14400, "large": 43200}
MAX_ADDRESS_SPACE_BYTES = 96 * 1024**3
MAX_GPU_MEMORY_MIB = 24564
MAX_ELAPSED_SECONDS = 172800
MAX_GPU_HOURS = 72
MAX_STORAGE_BYTES = 8589934592

MANIFEST_FIELDS = (
    "workload_id",
    "evidence_role",
    "primary_unit",
    "query_length_stratum",
    "target_scale_stratum",
    "query_ordinal_namespace",
    "query_source_ordinal",
    "query_transcript_id",
    "query_gene_id",
    "query_source_path",
    "query_extraction_recipe_id",
    "query_extracted_start0",
    "query_extracted_end0",
    "query_sequence_length",
    "query_sequence_sha256",
    "query_gc_fraction",
    "query_complexity_proxy",
    "query_gc_quartile",
    "query_complexity_quartile",
    "target_ordinal_namespace",
    "target_source_ordinal",
    "target_source_path",
    "target_extraction_recipe_id",
    "target_chromosome",
    "target_anchor_strand",
    "target_anchor_transcript_id",
    "target_anchor_gene_id",
    "target_region_start0",
    "target_region_end0",
    "target_sequence_length",
    "target_sequence_sha256",
    "target_gc_fraction",
    "target_complexity_proxy",
    "target_gc_quartile",
    "target_complexity_quartile",
    "assembly",
    "target_coordinate_namespace",
    "parameter_bundle_sha256",
    "input_pair_digest",
    "selection_hash",
    "technical_repeat_count",
    "status",
)

ATTEMPT_FIELDS = (
    "attempt_id",
    "execution_index",
    "validation_instance_id",
    "workload_id",
    "repeat_id",
    "primary_instance",
    "independent_sample",
    "arm",
    "pair_order",
    "arm_launch_order",
    "worker_index",
    "query_ordinal_namespace",
    "query_source_ordinal",
    "query_sequence_sha256",
    "target_ordinal_namespace",
    "target_source_ordinal",
    "target_sequence_sha256",
    "assembly",
    "target_coordinate_namespace",
    "query_extraction_recipe_id",
    "target_extraction_recipe_id",
    "input_pair_digest",
    "parameter_bundle_sha256",
    "binary_path",
    "binary_sha256",
    "runtime_receipt_path",
    "runtime_receipt_sha256",
    "contract_spec_path",
    "contract_spec_sha256",
    "comparator_path",
    "comparator_sha256",
    "runner_path",
    "runner_sha256",
    "analyzer_path",
    "analyzer_sha256",
    "gpu_physical_index",
    "cpu_affinity",
    "workers_per_gpu",
    "timeout_seconds",
    "max_address_space_bytes",
    "max_gpu_memory_mib",
    "retry_policy",
    "comparison_policy",
    "artifact_root",
    "evidence_role",
    "status",
)

FEATURE_NAMES = (
    "intercept",
    "log1p_query_length",
    "log1p_target_length",
    "log1p_query_times_target",
    "query_complexity_proxy",
    "target_complexity_proxy",
    "stratum_medium",
    "stratum_large",
    "config_paper_direct_v1",
    "config_paper_sharded_v1",
)
RESPONSES = ("cpu_wall_seconds", "gpu_wall_seconds", "artifact_storage_bytes")


class FreezeError(RuntimeError):
    """Raised for a fail-closed Phase 3 freeze error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FreezeError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def compact_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def canonical_digest(value: Any) -> str:
    return sha256_bytes(compact_json_bytes(value))


def seeded_hash(label: str, *values: object) -> str:
    return canonical_digest({"seed": SELECTION_SEED, "label": label, "values": [str(value) for value in values]})


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe JSON: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def read_gzip_tsv(path: Path) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe gzip TSV: {path}")
    with gzip.open(path, "rt", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    require(reader.fieldnames is not None, f"missing TSV header: {path}")
    require(all(None not in row and all(value is not None for value in row.values()) for row in rows), f"malformed TSV: {path}")
    return rows


def read_tsv(path: Path) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"missing or unsafe TSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    require(reader.fieldnames is not None, f"missing TSV header: {path}")
    require(all(None not in row and all(value is not None for value in row.values()) for row in rows), f"malformed TSV: {path}")
    return rows


def render_tsv(fields: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def query_length_stratum(length: int) -> str:
    for name, (minimum, maximum) in QUERY_LENGTH_BOUNDS.items():
        if minimum <= length <= maximum:
            return name
    raise FreezeError(f"query length outside frozen strata: {length}")


def assign_rank_quartiles(rows: list[dict[str, Any]], source_field: str, output_field: str) -> None:
    ordered = sorted(
        rows,
        key=lambda row: (
            Decimal(str(row[source_field])),
            row["_selection_hash"],
        ),
    )
    count = len(ordered)
    require(count >= 4, f"insufficient rows for quartiles: {source_field}")
    for index, row in enumerate(ordered):
        row[output_field] = min(3, index * 4 // count) + 1


def exclusion_indexes() -> dict[str, set[Any]]:
    indexes: dict[str, set[Any]] = {
        "query_digest": set(),
        "target_digest": set(),
        "query_ordinal": set(),
        "target_ordinal": set(),
        "pair_digest": set(),
        "query_id": set(),
        "target_id": set(),
    }
    for row in read_tsv(EXCLUSION_PATH):
        if row["query_sha256"] != "NA":
            indexes["query_digest"].add(row["query_sha256"])
        if row["target_sha256"] != "NA":
            indexes["target_digest"].add(row["target_sha256"])
        if row["query_ordinal_namespace"] != "NA" and row["query_source_ordinal"] != "NA":
            indexes["query_ordinal"].add((row["query_ordinal_namespace"], row["query_source_ordinal"]))
        if row["target_ordinal_namespace"] != "NA" and row["target_source_ordinal"] != "NA":
            indexes["target_ordinal"].add((row["target_ordinal_namespace"], row["target_source_ordinal"]))
        if row["pair_digest"] != "NA":
            indexes["pair_digest"].add(row["pair_digest"])
        if row["query_id"] != "NA":
            indexes["query_id"].add(row["query_id"])
        if row["target_id"] != "NA":
            indexes["target_id"].add(row["target_id"])
    return indexes


def query_candidates(indexes: Mapping[str, set[Any]]) -> dict[str, list[dict[str, Any]]]:
    rows = []
    for source in read_gzip_tsv(QUERY_UNIVERSE_PATH):
        if source["operating_envelope_eligible"] != "1" or source["historical_exclusion_status"] != "fresh_eligible":
            continue
        ordinal = (source["query_ordinal_namespace"], source["source_ordinal"])
        identity_values = {
            source["transcript_id"],
            source["stable_transcript_id"],
            source["gene_id"],
            source["stable_gene_id"],
            source["gene_name"],
        }
        if (
            source["sequence_sha256"] in indexes["query_digest"]
            or ordinal in indexes["query_ordinal"]
            or identity_values & indexes["query_id"]
        ):
            continue
        row: dict[str, Any] = dict(source)
        row["_length_stratum"] = query_length_stratum(int(source["sequence_length"]))
        row["_selection_hash"] = seeded_hash(
            "query",
            source["query_ordinal_namespace"],
            source["source_ordinal"],
            source["sequence_sha256"],
        )
        rows.append(row)

    by_digest: dict[str, dict[str, Any]] = {}
    for row in rows:
        digest = row["sequence_sha256"]
        if digest not in by_digest or row["_selection_hash"] < by_digest[digest]["_selection_hash"]:
            by_digest[digest] = row
    result: dict[str, list[dict[str, Any]]] = {}
    for stratum in PANEL_QUOTAS:
        candidates = [row for row in by_digest.values() if row["_length_stratum"] == stratum]
        assign_rank_quartiles(candidates, "gc_fraction", "_gc_quartile")
        assign_rank_quartiles(candidates, "sampled_distinct_4mer_fraction", "_complexity_quartile")
        result[stratum] = candidates
    return result


def cell_quotas(total: int, cells: Sequence[tuple[int, int]], label: str) -> dict[tuple[int, int], int]:
    base, remainder = divmod(total, len(cells))
    order = sorted(cells, key=lambda cell: seeded_hash(label, *cell))
    return {cell: base + int(cell in set(order[:remainder])) for cell in cells}


def select_queries(candidates: Mapping[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    cells = tuple((gc, complexity) for gc in range(1, 5) for complexity in range(1, 5))
    selected: dict[str, list[dict[str, Any]]] = {}
    for stratum, quota in PANEL_QUOTAS.items():
        allocations = cell_quotas(quota, cells, f"query-cell-allocation-{stratum}")
        by_cell: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
        for row in candidates[stratum]:
            by_cell[(row["_gc_quartile"], row["_complexity_quartile"])].append(row)
        chosen: list[dict[str, Any]] = []
        for cell in cells:
            ordered = sorted(by_cell[cell], key=lambda row: row["_selection_hash"])
            require(len(ordered) >= allocations[cell], f"insufficient query capacity in {stratum} cell {cell}")
            chosen.extend(ordered[: allocations[cell]])
        require(len(chosen) == quota, f"query quota drift in {stratum}")
        selected[stratum] = sorted(chosen, key=lambda row: row["_selection_hash"])
    return selected


def target_candidates(indexes: Mapping[str, set[Any]]) -> dict[str, list[dict[str, Any]]]:
    rows_by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for source in read_gzip_tsv(TARGET_UNIVERSE_PATH):
        if source["operating_envelope_eligible"] != "1" or source["historical_exclusion_status"] != "fresh_eligible":
            continue
        ordinal = (source["target_ordinal_namespace"], source["source_ordinal"])
        identity_values = {
            source["anchor_transcript_id"],
            source["anchor_gene_id"],
            source["anchor_gene_name"],
        }
        if (
            source["sequence_sha256"] in indexes["target_digest"]
            or ordinal in indexes["target_ordinal"]
            or identity_values & indexes["target_id"]
        ):
            continue
        row: dict[str, Any] = dict(source)
        row["_selection_hash"] = seeded_hash(
            "target",
            source["target_ordinal_namespace"],
            source["source_ordinal"],
            source["sequence_sha256"],
        )
        rows_by_stratum[source["target_scale_stratum"]].append(row)

    result: dict[str, list[dict[str, Any]]] = {}
    for stratum in PANEL_QUOTAS:
        by_digest: dict[str, dict[str, Any]] = {}
        for row in rows_by_stratum[stratum]:
            digest = row["sequence_sha256"]
            if digest not in by_digest or row["_selection_hash"] < by_digest[digest]["_selection_hash"]:
                by_digest[digest] = row
        candidates = list(by_digest.values())
        assign_rank_quartiles(candidates, "gc_fraction", "_gc_quartile")
        assign_rank_quartiles(candidates, "sampled_distinct_4mer_fraction", "_complexity_quartile")
        result[stratum] = candidates
    return result


def select_targets(candidates: Mapping[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    groups = (("chr21", "+"), ("chr21", "-"), ("chr22", "+"), ("chr22", "-"))
    cells = tuple((gc, complexity) for gc in range(1, 5) for complexity in range(1, 5))
    selected: dict[str, list[dict[str, Any]]] = {}
    for stratum, quota in PANEL_QUOTAS.items():
        base, remainder = divmod(quota, len(groups))
        group_order = sorted(groups, key=lambda group: seeded_hash(f"target-group-allocation-{stratum}", *group))
        allocations = {group: base + int(group in set(group_order[:remainder])) for group in groups}
        chosen: list[dict[str, Any]] = []
        for group in groups:
            buckets: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
            for row in candidates[stratum]:
                if (row["chromosome"], row["anchor_strand"]) == group:
                    buckets[(row["_gc_quartile"], row["_complexity_quartile"])].append(row)
            for bucket in buckets.values():
                bucket.sort(key=lambda row: row["_selection_hash"])
            cell_order = sorted(cells, key=lambda cell: seeded_hash(f"target-cell-order-{stratum}", *group, *cell))
            group_chosen: list[dict[str, Any]] = []
            cursor = 0
            while len(group_chosen) < allocations[group]:
                made_progress = False
                for offset in range(len(cell_order)):
                    cell = cell_order[(cursor + offset) % len(cell_order)]
                    if buckets[cell]:
                        group_chosen.append(buckets[cell].pop(0))
                        cursor = (cursor + offset + 1) % len(cell_order)
                        made_progress = True
                        break
                require(made_progress, f"insufficient target capacity in {stratum} group {group}")
            chosen.extend(group_chosen)
        require(len(chosen) == quota, f"target quota drift in {stratum}")
        selected[stratum] = sorted(chosen, key=lambda row: row["_selection_hash"])
    return selected


def pair_identity(query: Mapping[str, Any], target: Mapping[str, Any]) -> dict[str, Any]:
    identity: dict[str, Any] = {
        "schema_version": 1,
        "query_ordinal_namespace": query["query_ordinal_namespace"],
        "query_source_ordinal": int(query["source_ordinal"]),
        "query_sequence_sha256": query["sequence_sha256"],
        "query_extracted_interval": {"start0": 0, "end0": int(query["sequence_length"])},
        "target_ordinal_namespace": target["target_ordinal_namespace"],
        "target_source_ordinal": int(target["source_ordinal"]),
        "target_sequence_sha256": target["sequence_sha256"],
        "target_extracted_interval": {
            "start0": int(target["region_start0"]),
            "end0": int(target["region_end0"]),
        },
        "assembly": "GRCh38",
        "target_coordinate_namespace": target["target_coordinate_namespace"],
        "query_extraction_recipe_id": QUERY_RECIPE,
        "target_extraction_recipe_id": target["extraction_recipe_id"],
        "parameter_bundle_sha256": PARAMETER_BUNDLE_SHA256,
    }
    identity["input_pair_digest"] = canonical_digest(identity)
    return identity


def build_manifest(
    queries: Mapping[str, list[dict[str, Any]]],
    targets: Mapping[str, list[dict[str, Any]]],
    indexes: Mapping[str, set[Any]],
) -> list[dict[str, Any]]:
    query_assignments: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for query_stratum in PANEL_QUOTAS:
        cursor = 0
        for target_stratum in PANEL_QUOTAS:
            count = PAIRING_MATRIX[query_stratum][target_stratum]
            rows = queries[query_stratum][cursor : cursor + count]
            require(len(rows) == count, f"query pairing capacity drift: {query_stratum}/{target_stratum}")
            query_assignments[target_stratum].extend((query_stratum, row) for row in rows)
            cursor += count
        require(cursor == len(queries[query_stratum]), f"unused selected queries in {query_stratum}")

    raw_pairs: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for target_stratum in PANEL_QUOTAS:
        assigned_queries = sorted(
            query_assignments[target_stratum],
            key=lambda item: seeded_hash("pair-query-order", target_stratum, item[1]["_selection_hash"]),
        )
        target_rows = sorted(
            targets[target_stratum],
            key=lambda row: seeded_hash("pair-target-order", target_stratum, row["_selection_hash"]),
        )
        require(len(assigned_queries) == len(target_rows) == PANEL_QUOTAS[target_stratum], f"pairing quota drift in {target_stratum}")
        raw_pairs.extend((query_stratum, query, target) for (query_stratum, query), target in zip(assigned_queries, target_rows))

    raw_pairs.sort(key=lambda item: seeded_hash("workload-order", item[1]["_selection_hash"], item[2]["_selection_hash"]))
    manifest: list[dict[str, Any]] = []
    for index, (query_stratum, query, target) in enumerate(raw_pairs, 1):
        identity = pair_identity(query, target)
        require(identity["input_pair_digest"] not in indexes["pair_digest"], "selected pair digest overlaps historical registry")
        selection_hash = seeded_hash("pair", identity["input_pair_digest"])
        manifest.append(
            {
                "workload_id": f"bt3_w{index:03d}",
                "evidence_role": "fresh_concordance_promotion",
                "primary_unit": 1,
                "query_length_stratum": query_stratum,
                "target_scale_stratum": target["target_scale_stratum"],
                "query_ordinal_namespace": query["query_ordinal_namespace"],
                "query_source_ordinal": query["source_ordinal"],
                "query_transcript_id": query["transcript_id"],
                "query_gene_id": query["gene_id"],
                "query_source_path": QUERY_SOURCE_PATH,
                "query_extraction_recipe_id": QUERY_RECIPE,
                "query_extracted_start0": 0,
                "query_extracted_end0": query["sequence_length"],
                "query_sequence_length": query["sequence_length"],
                "query_sequence_sha256": query["sequence_sha256"],
                "query_gc_fraction": query["gc_fraction"],
                "query_complexity_proxy": query["sampled_distinct_4mer_fraction"],
                "query_gc_quartile": query["_gc_quartile"],
                "query_complexity_quartile": query["_complexity_quartile"],
                "target_ordinal_namespace": target["target_ordinal_namespace"],
                "target_source_ordinal": target["source_ordinal"],
                "target_source_path": TARGET_SOURCE_PATHS[target["chromosome"]],
                "target_extraction_recipe_id": target["extraction_recipe_id"],
                "target_chromosome": target["chromosome"],
                "target_anchor_strand": target["anchor_strand"],
                "target_anchor_transcript_id": target["anchor_transcript_id"],
                "target_anchor_gene_id": target["anchor_gene_id"],
                "target_region_start0": target["region_start0"],
                "target_region_end0": target["region_end0"],
                "target_sequence_length": target["sequence_length"],
                "target_sequence_sha256": target["sequence_sha256"],
                "target_gc_fraction": target["gc_fraction"],
                "target_complexity_proxy": target["sampled_distinct_4mer_fraction"],
                "target_gc_quartile": target["_gc_quartile"],
                "target_complexity_quartile": target["_complexity_quartile"],
                "assembly": identity["assembly"],
                "target_coordinate_namespace": identity["target_coordinate_namespace"],
                "parameter_bundle_sha256": identity["parameter_bundle_sha256"],
                "input_pair_digest": identity["input_pair_digest"],
                "selection_hash": selection_hash,
                "technical_repeat_count": 0,
                "status": "preregistered_not_run",
            }
        )

    repeat_ids: set[str] = set()
    for stratum in PANEL_QUOTAS:
        eligible = [row for row in manifest if row["target_scale_stratum"] == stratum]
        eligible.sort(key=lambda row: seeded_hash("technical-repeat", stratum, row["input_pair_digest"]))
        repeat_ids.update(row["workload_id"] for row in eligible[:TECHNICAL_REPEATS_PER_TARGET_STRATUM])
    for row in manifest:
        row["technical_repeat_count"] = int(row["workload_id"] in repeat_ids)
    validate_manifest(manifest, indexes)
    return manifest


def validate_manifest(rows: Sequence[Mapping[str, Any]], indexes: Mapping[str, set[Any]]) -> None:
    require(len(rows) == sum(PANEL_QUOTAS.values()) == 178, "manifest panel size drift")
    require(Counter(row["query_length_stratum"] for row in rows) == Counter(PANEL_QUOTAS), "query stratum quotas drift")
    require(Counter(row["target_scale_stratum"] for row in rows) == Counter(PANEL_QUOTAS), "target stratum quotas drift")
    observed_matrix = Counter((row["query_length_stratum"], row["target_scale_stratum"]) for row in rows)
    expected_matrix = Counter({(query, target): count for query, targets in PAIRING_MATRIX.items() for target, count in targets.items()})
    require(observed_matrix == expected_matrix, "query/target pairing matrix drift")
    unique_fields = (
        "workload_id",
        "query_sequence_sha256",
        "target_sequence_sha256",
        "input_pair_digest",
    )
    for field in unique_fields:
        require(len({row[field] for row in rows}) == len(rows), f"manifest {field} is not globally unique")
    query_ordinals = {(row["query_ordinal_namespace"], str(row["query_source_ordinal"])) for row in rows}
    target_ordinals = {(row["target_ordinal_namespace"], str(row["target_source_ordinal"])) for row in rows}
    require(len(query_ordinals) == len(rows), "query namespaced ordinals are not globally unique")
    require(len(target_ordinals) == len(rows), "target namespaced ordinals are not globally unique")
    require(not ({row["query_sequence_sha256"] for row in rows} & indexes["query_digest"]), "query digest exclusion overlap")
    require(not ({row["target_sequence_sha256"] for row in rows} & indexes["target_digest"]), "target digest exclusion overlap")
    require(not (query_ordinals & indexes["query_ordinal"]), "query ordinal exclusion overlap")
    require(not (target_ordinals & indexes["target_ordinal"]), "target ordinal exclusion overlap")
    require(not ({row["input_pair_digest"] for row in rows} & indexes["pair_digest"]), "pair digest exclusion overlap")
    repeat_counts = Counter(row["target_scale_stratum"] for row in rows if int(row["technical_repeat_count"]) == 1)
    require(repeat_counts == Counter({stratum: 2 for stratum in PANEL_QUOTAS}), "technical repeat subset drift")
    for row in rows:
        identity = manifest_identity(row)
        require(canonical_digest({key: value for key, value in identity.items() if key != "input_pair_digest"}) == row["input_pair_digest"], f"pair digest drift: {row['workload_id']}")


def manifest_identity(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "query_ordinal_namespace": row["query_ordinal_namespace"],
        "query_source_ordinal": int(row["query_source_ordinal"]),
        "query_sequence_sha256": row["query_sequence_sha256"],
        "query_extracted_interval": {"start0": int(row["query_extracted_start0"]), "end0": int(row["query_extracted_end0"])},
        "target_ordinal_namespace": row["target_ordinal_namespace"],
        "target_source_ordinal": int(row["target_source_ordinal"]),
        "target_sequence_sha256": row["target_sequence_sha256"],
        "target_extracted_interval": {"start0": int(row["target_region_start0"]), "end0": int(row["target_region_end0"])},
        "assembly": row["assembly"],
        "target_coordinate_namespace": row["target_coordinate_namespace"],
        "query_extraction_recipe_id": row["query_extraction_recipe_id"],
        "target_extraction_recipe_id": row["target_extraction_recipe_id"],
        "parameter_bundle_sha256": row["parameter_bundle_sha256"],
        "input_pair_digest": row["input_pair_digest"],
    }


def build_attempt_plan(manifest: Sequence[Mapping[str, Any]], manifest_sha256: str) -> list[dict[str, Any]]:
    required_paths = (RUNNER_PATH, ANALYZER_PATH, AUTHORITY_BINARY_PATH, CANDIDATE_BINARY_PATH)
    for path in required_paths:
        require(path.is_file() and not path.is_symlink(), f"Phase 3 attempt dependency missing: {path}")
    runtime_sha = sha256_file(RUNTIME_RECEIPT_PATH)
    contract_sha = sha256_file(CONTRACT_PATH)
    comparator_sha = sha256_file(COMPARATOR_PATH)
    runner_sha = sha256_file(RUNNER_PATH)
    analyzer_sha = sha256_file(ANALYZER_PATH)
    require(sha256_file(AUTHORITY_BINARY_PATH) == AUTHORITY_BINARY_SHA256, "archived authority binary digest drift")
    require(sha256_file(CANDIDATE_BINARY_PATH) == CANDIDATE_BINARY_SHA256, "archived candidate binary digest drift")
    rows: list[dict[str, Any]] = []
    execution_index = 0
    validation_index = 0
    for workload in manifest:
        repeat_count = 1 + int(workload["technical_repeat_count"])
        for repeat_id in range(repeat_count):
            validation_index += 1
            pair_order = "AG" if validation_index % 2 == 1 else "GA"
            worker_index = (validation_index - 1) % 2
            validation_id = f"{workload['workload_id']}__repeat{repeat_id:02d}"
            for launch_order, arm in enumerate(pair_order, 1):
                execution_index += 1
                binary_path = AUTHORITY_BINARY_PATH if arm == "A" else CANDIDATE_BINARY_PATH
                binary_sha = AUTHORITY_BINARY_SHA256 if arm == "A" else CANDIDATE_BINARY_SHA256
                rows.append(
                    {
                        "attempt_id": f"{validation_id}_{arm.lower()}",
                        "execution_index": execution_index,
                        "validation_instance_id": validation_id,
                        "workload_id": workload["workload_id"],
                        "repeat_id": repeat_id,
                        "primary_instance": int(repeat_id == 0),
                        "independent_sample": int(repeat_id == 0),
                        "arm": arm,
                        "pair_order": pair_order,
                        "arm_launch_order": launch_order,
                        "worker_index": worker_index,
                        "query_ordinal_namespace": workload["query_ordinal_namespace"],
                        "query_source_ordinal": workload["query_source_ordinal"],
                        "query_sequence_sha256": workload["query_sequence_sha256"],
                        "target_ordinal_namespace": workload["target_ordinal_namespace"],
                        "target_source_ordinal": workload["target_source_ordinal"],
                        "target_sequence_sha256": workload["target_sequence_sha256"],
                        "assembly": workload["assembly"],
                        "target_coordinate_namespace": workload["target_coordinate_namespace"],
                        "query_extraction_recipe_id": workload["query_extraction_recipe_id"],
                        "target_extraction_recipe_id": workload["target_extraction_recipe_id"],
                        "input_pair_digest": workload["input_pair_digest"],
                        "parameter_bundle_sha256": workload["parameter_bundle_sha256"],
                        "binary_path": binary_path.relative_to(ROOT).as_posix(),
                        "binary_sha256": binary_sha,
                        "runtime_receipt_path": RUNTIME_RECEIPT_PATH.relative_to(ROOT).as_posix(),
                        "runtime_receipt_sha256": runtime_sha,
                        "contract_spec_path": CONTRACT_PATH.relative_to(ROOT).as_posix(),
                        "contract_spec_sha256": contract_sha,
                        "comparator_path": COMPARATOR_PATH.relative_to(ROOT).as_posix(),
                        "comparator_sha256": comparator_sha,
                        "runner_path": RUNNER_PATH.relative_to(ROOT).as_posix(),
                        "runner_sha256": runner_sha,
                        "analyzer_path": ANALYZER_PATH.relative_to(ROOT).as_posix(),
                        "analyzer_sha256": analyzer_sha,
                        "gpu_physical_index": "NA" if arm == "A" else worker_index,
                        "cpu_affinity": CPU_AFFINITY[worker_index],
                        "workers_per_gpu": 1,
                        "timeout_seconds": TIMEOUT_SECONDS[workload["target_scale_stratum"]],
                        "max_address_space_bytes": MAX_ADDRESS_SPACE_BYTES,
                        "max_gpu_memory_mib": MAX_GPU_MEMORY_MIB,
                        "retry_policy": "none",
                        "comparison_policy": "offline_after_both_arms_terminal",
                        "artifact_root": f".paper-artifacts/biological-topk/fresh-holdout/{validation_id}_{arm.lower()}",
                        "evidence_role": "fresh_concordance_promotion",
                        "status": "preregistered_not_run",
                    }
                )
    require(len(rows) == 368 and validation_index == 184, "attempt/validation instance count drift")
    require([int(row["execution_index"]) for row in rows] == list(range(1, 369)), "attempt execution indexes drift")
    by_validation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_validation[row["validation_instance_id"]].append(row)
    for validation_id, pair in by_validation.items():
        require({row["arm"] for row in pair} == {"A", "G"}, f"A/G pair missing: {validation_id}")
        identity_fields = (
            "query_ordinal_namespace", "query_source_ordinal", "query_sequence_sha256",
            "target_ordinal_namespace", "target_source_ordinal", "target_sequence_sha256",
            "assembly", "target_coordinate_namespace", "query_extraction_recipe_id",
            "target_extraction_recipe_id", "input_pair_digest", "parameter_bundle_sha256",
        )
        require(all(len({str(row[field]) for row in pair}) == 1 for field in identity_fields), f"A/G identity drift: {validation_id}")
        require(sorted(int(row["arm_launch_order"]) for row in pair) == [1, 2], f"launch order drift: {validation_id}")
    require(Counter(row["pair_order"] for row in rows) == Counter({"AG": 184, "GA": 184}), "balanced A/G order drift")
    del manifest_sha256
    return rows


def feature_vector(row: Mapping[str, Any]) -> np.ndarray:
    query_length = float(row["query_length"])
    target_length = float(row["target_length"])
    stratum = str(row["target_scale_stratum"])
    configuration = str(row["execution_configuration"])
    return np.asarray(
        [
            1.0,
            math.log1p(query_length),
            math.log1p(target_length),
            math.log1p(query_length * target_length),
            float(row["query_complexity_proxy"]),
            float(row["target_complexity_proxy"]),
            float(stratum == "medium"),
            float(stratum == "large"),
            float(configuration == "paper_direct_v1"),
            float(configuration == "paper_sharded_v1"),
        ],
        dtype=np.float64,
    )


def nearest_rank(values: Sequence[float], quantile: float) -> float:
    require(values, "nearest-rank input is empty")
    return sorted(values)[math.ceil(quantile * len(values)) - 1]


def fit_coefficients(matrix: np.ndarray, values: np.ndarray, ridge_lambda: float) -> np.ndarray:
    penalty = np.eye(matrix.shape[1], dtype=np.float64) * ridge_lambda
    penalty[0, 0] = 0.0
    return np.linalg.solve(matrix.T @ matrix + penalty, matrix.T @ np.log1p(values))


def predict(matrix: np.ndarray, coefficients: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, np.expm1(matrix @ coefficients))


def manifest_resource_rows(manifest: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in manifest:
        for _ in range(1 + int(row["technical_repeat_count"])):
            rows.append(
                {
                    "target_scale_stratum": row["target_scale_stratum"],
                    "execution_configuration": "canonical_hybrid_v2",
                    "query_length": int(row["query_sequence_length"]),
                    "target_length": int(row["target_sequence_length"]),
                    "query_complexity_proxy": row["query_complexity_proxy"],
                    "target_complexity_proxy": row["target_complexity_proxy"],
                }
            )
    require(len(rows) == 184, "resource rows do not include exactly six technical repeats")
    return rows


def resource_projection(manifest: Sequence[Mapping[str, Any]], manifest_sha256: str) -> dict[str, Any]:
    require(sha256_file(RESOURCE_MODEL_PATH) == RESOURCE_MODEL_SHA256, "frozen resource model digest drift")
    model = load_json(RESOURCE_MODEL_PATH)
    require(model["schema_version"] == 1, "resource model schema drift")
    require(model["bootstrap"]["replicates"] == 10000, "resource bootstrap replicate drift")
    require(model["bootstrap"]["seed"] == 20260810, "resource bootstrap seed drift")
    require(model["ridge_lambda"] == "0.01", "resource ridge lambda drift")
    historical = model["historical_observations"]
    require(isinstance(historical, list) and len(historical) == 62, "resource observation set drift")
    historical_matrix = np.vstack([feature_vector(row) for row in historical])
    historical_values = {
        response: np.asarray([float(row[response]) for row in historical], dtype=np.float64)
        for response in RESPONSES
    }
    strata_indexes = {
        stratum: np.asarray([index for index, row in enumerate(historical) if row["target_scale_stratum"] == stratum], dtype=np.int64)
        for stratum in PANEL_QUOTAS
    }
    resource_rows = manifest_resource_rows(manifest)
    manifest_matrix = np.vstack([feature_vector(row) for row in resource_rows])
    manifest_strata = np.asarray([row["target_scale_stratum"] for row in resource_rows], dtype=object)
    point: dict[str, float] = {}
    for response in RESPONSES:
        coefficients = np.asarray([float(model["point_coefficients"][response][feature]) for feature in FEATURE_NAMES], dtype=np.float64)
        point[response] = float(predict(manifest_matrix, coefficients).sum())

    replicates = int(model["bootstrap"]["replicates"])
    rng = np.random.default_rng(int(model["bootstrap"]["seed"]))
    samples = {response: np.empty(replicates, dtype=np.float64) for response in RESPONSES}
    ridge_lambda = float(model["ridge_lambda"])
    for replicate in range(replicates):
        sampled_indexes = np.concatenate(
            [indexes[rng.integers(0, len(indexes), size=len(indexes))] for indexes in strata_indexes.values()]
        )
        sampled_matrix = historical_matrix[sampled_indexes]
        sampled_strata = [historical[int(index)]["target_scale_stratum"] for index in sampled_indexes]
        for response in RESPONSES:
            sampled_values = historical_values[response][sampled_indexes]
            coefficients = fit_coefficients(sampled_matrix, sampled_values, ridge_lambda)
            historical_prediction = predict(sampled_matrix, coefficients)
            residuals = np.log1p(sampled_values) - np.log1p(historical_prediction)
            residual_by_stratum = {
                stratum: max(
                    0.0,
                    nearest_rank(
                        [float(residuals[index]) for index, observed in enumerate(sampled_strata) if observed == stratum],
                        0.95,
                    ),
                )
                for stratum in PANEL_QUOTAS
            }
            base_prediction = predict(manifest_matrix, coefficients)
            adjusted = np.expm1(
                np.log1p(base_prediction)
                + np.asarray([residual_by_stratum[str(stratum)] for stratum in manifest_strata], dtype=np.float64)
            )
            samples[response][replicate] = float(adjusted.sum())

    quantile = float(model["bootstrap"]["upper_bound_quantile"])
    upper = {
        response: nearest_rank([float(value) for value in samples[response]], quantile)
        for response in RESPONSES
    }
    logical_workers = int(model["scheduler_simulation"]["logical_workers"])
    inefficiency = float(model["scheduler_simulation"]["inefficiency_factor"])
    scheduled_point = (point["cpu_wall_seconds"] + point["gpu_wall_seconds"]) / logical_workers * inefficiency
    scheduled_samples = (
        samples["cpu_wall_seconds"] + samples["gpu_wall_seconds"]
    ) / logical_workers * inefficiency
    scheduled_upper = nearest_rank([float(value) for value in scheduled_samples], quantile)
    return {
        "schema_version": 1,
        "status": "manifest_specific_projection_frozen",
        "evidence_role": "resource_planning_control",
        "performance_claim": False,
        "manifest_path": MANIFEST_PATH.relative_to(ROOT).as_posix(),
        "manifest_sha256": manifest_sha256,
        "resource_model_path": RESOURCE_MODEL_PATH.relative_to(ROOT).as_posix(),
        "resource_model_sha256": RESOURCE_MODEL_SHA256,
        "model_unchanged_from_phase_1": True,
        "primary_workload_count": 178,
        "technical_repeat_instance_count": 6,
        "projected_validation_instance_count": 184,
        "projected_attempt_count": 368,
        "bootstrap": model["bootstrap"],
        "scheduler_simulation": model["scheduler_simulation"],
        "projection": {
            "projected_cpu_aggregate_wall_seconds_point": format(point["cpu_wall_seconds"], ".17g"),
            "projected_cpu_aggregate_wall_seconds_upper_95": format(upper["cpu_wall_seconds"], ".17g"),
            "projected_gpu_aggregate_wall_seconds_point": format(point["gpu_wall_seconds"], ".17g"),
            "projected_gpu_aggregate_wall_seconds_upper_95": format(upper["gpu_wall_seconds"], ".17g"),
            "projected_gpu_hours_point": format(point["gpu_wall_seconds"] / 3600, ".17g"),
            "projected_gpu_hours_upper_95": format(upper["gpu_wall_seconds"] / 3600, ".17g"),
            "projected_scheduled_elapsed_wall_seconds_point": format(scheduled_point, ".17g"),
            "projected_scheduled_elapsed_wall_seconds_upper_95": format(scheduled_upper, ".17g"),
            "projected_artifact_storage_bytes_point": str(math.ceil(point["artifact_storage_bytes"])),
            "projected_artifact_storage_bytes_upper_95": str(math.ceil(upper["artifact_storage_bytes"])),
        },
        "technical_repeats_included": True,
    }


def resource_decision(projection: Mapping[str, Any], manifest_sha256: str) -> dict[str, Any]:
    frozen_plan = load_json(RESOURCE_PLAN_PATH)
    owner = load_json(OWNER_QUOTA_PATH)
    require(frozen_plan["max_formal_scheduled_wall_seconds"] == MAX_ELAPSED_SECONDS, "Phase 1 elapsed budget drift")
    require(frozen_plan["max_gpu_hours"] == MAX_GPU_HOURS, "Phase 1 GPU-hour budget drift")
    require(frozen_plan["max_artifact_storage_bytes"] == MAX_STORAGE_BYTES, "Phase 1 storage budget drift")
    require(owner["max_artifact_storage_bytes"] == MAX_STORAGE_BYTES, "owner storage quota drift")
    require(owner["quota_may_be_raised_after_manifest_projection"] is False, "owner quota mutability drift")
    values = projection["projection"]
    elapsed_pass = Decimal(values["projected_scheduled_elapsed_wall_seconds_upper_95"]) <= Decimal(MAX_ELAPSED_SECONDS)
    gpu_pass = Decimal(values["projected_gpu_hours_upper_95"]) <= Decimal(MAX_GPU_HOURS)
    storage_pass = int(values["projected_artifact_storage_bytes_upper_95"]) <= MAX_STORAGE_BYTES
    return {
        "schema_version": 1,
        "status": "pass" if elapsed_pass and gpu_pass and storage_pass else "blocked_fixed_budget",
        "manifest_sha256": manifest_sha256,
        "resource_projection_path": RESOURCE_PROJECTION_PATH.relative_to(ROOT).as_posix(),
        "resource_projection_sha256": canonical_digest(projection),
        "resource_model_sha256": RESOURCE_MODEL_SHA256,
        "max_formal_scheduled_wall_seconds": MAX_ELAPSED_SECONDS,
        "max_gpu_hours": MAX_GPU_HOURS,
        "max_artifact_storage_bytes": MAX_STORAGE_BYTES,
        "projected_scheduled_elapsed_wall_seconds_upper_95": values["projected_scheduled_elapsed_wall_seconds_upper_95"],
        "projected_gpu_hours_upper_95": values["projected_gpu_hours_upper_95"],
        "projected_artifact_storage_bytes_upper_95": values["projected_artifact_storage_bytes_upper_95"],
        "scheduled_elapsed_gate_pass": elapsed_pass,
        "gpu_hours_gate_pass": gpu_pass,
        "artifact_storage_gate_pass": storage_pass,
        "fixed_budget_gate_pass": elapsed_pass and gpu_pass and storage_pass,
        "owner_quota_may_be_raised_after_manifest_projection": False,
        "phase_4_execution_authorized": elapsed_pass and gpu_pass and storage_pass,
    }


def build() -> dict[Path, bytes]:
    sample_size = load_json(SAMPLE_SIZE_PATH)
    operating = load_json(OPERATING_ENVELOPE_PATH)
    runtime = load_json(RUNTIME_RECEIPT_PATH)
    require(sample_size["N_panel"] == 178 and sample_size["stratum_quotas"] == PANEL_QUOTAS, "sample-size plan drift")
    require(operating["parameter_bundle_sha256"] == PARAMETER_BUNDLE_SHA256, "parameter bundle drift")
    require(runtime["authority_binary_sha256"] == AUTHORITY_BINARY_SHA256, "runtime authority digest drift")
    require(runtime["hybrid_binary_sha256"] == CANDIDATE_BINARY_SHA256, "runtime candidate digest drift")
    indexes = exclusion_indexes()
    selected_queries = select_queries(query_candidates(indexes))
    selected_targets = select_targets(target_candidates(indexes))
    manifest = build_manifest(selected_queries, selected_targets, indexes)
    manifest_bytes = render_tsv(MANIFEST_FIELDS, manifest)
    manifest_sha = sha256_bytes(manifest_bytes)
    attempt_rows = build_attempt_plan(manifest, manifest_sha)
    attempt_bytes = render_tsv(ATTEMPT_FIELDS, attempt_rows)
    projection = resource_projection(manifest, manifest_sha)
    projection_bytes = canonical_json_bytes(projection)
    decision = resource_decision(projection, manifest_sha)
    decision["resource_projection_sha256"] = sha256_bytes(projection_bytes)
    decision_bytes = canonical_json_bytes(decision)
    require(decision["fixed_budget_gate_pass"] is True, "manifest-specific resource gate failed")
    query_counts = Counter(row["query_length_stratum"] for row in manifest)
    target_counts = Counter(row["target_scale_stratum"] for row in manifest)
    target_group_counts = Counter(
        (row["target_scale_stratum"], row["target_chromosome"], row["target_anchor_strand"])
        for row in manifest
    )
    plan = {
        "schema_version": 1,
        "status": "frozen_not_run",
        "phase": 3,
        "selection_kind": "input_only_static_source_metadata",
        "selection_seed": SELECTION_SEED,
        "allowed_selection_fields": [
            "namespaced_source_ordinal", "sequence_length", "GC_fraction",
            "static_repeat_or_complexity_proxy", "chromosome", "transcript_biotype",
            "assembly", "target_scale_stratum", "hash_ordering",
        ],
        "prohibited_selection_fields_used": [],
        "fresh_pair_selected": True,
        "new_prediction_run": False,
        "scientific_output_created": False,
        "N_panel": len(manifest),
        "primary_workload_count": len(manifest),
        "technical_repeat_workload_count": sum(int(row["technical_repeat_count"]) for row in manifest),
        "validation_instance_count": len(manifest) + sum(int(row["technical_repeat_count"]) for row in manifest),
        "attempt_count": len(attempt_rows),
        "query_length_bounds": {key: list(value) for key, value in QUERY_LENGTH_BOUNDS.items()},
        "query_length_stratum_quotas": dict(query_counts),
        "target_scale_stratum_quotas": dict(target_counts),
        "query_target_pairing_matrix": PAIRING_MATRIX,
        "query_balancing": "rank quartiles of GC fraction x sampled distinct 4-mer fraction within length stratum",
        "target_balancing": "chromosome x anchor strand quotas with round-robin GC x complexity quartile cells",
        "target_group_counts": {"|".join(key): value for key, value in sorted(target_group_counts.items())},
        "technical_repeat_rule": "two seed-hash-selected workloads per target scale; one additional repeat each; excluded from independent n",
        "execution_order": "balanced alternating AG and GA over validation instances",
        "worker_configuration": {
            "logical_workers": 2,
            "gpu_assignment": {"0": 0, "1": 1},
            "cpu_affinity": {str(key): value for key, value in CPU_AFFINITY.items()},
            "workers_per_gpu": 1,
            "no_automatic_retries": True,
            "comparison_starts_only_after_both_arms_terminal": True,
        },
        "memory_limits": {
            "max_address_space_bytes_per_attempt": MAX_ADDRESS_SPACE_BYTES,
            "max_gpu_memory_mib_per_gpu": MAX_GPU_MEMORY_MIB,
        },
        "timeouts_seconds_by_target_scale": TIMEOUT_SECONDS,
        "exact_analysis_command": [
            "python3", "reproduce/biological_topk/analyze_fresh_holdout.py", "--analyze",
            "--artifact-root", ".paper-artifacts/biological-topk/fresh-holdout",
        ],
        "runtime_binding": {
            "runtime_receipt_path": RUNTIME_RECEIPT_PATH.relative_to(ROOT).as_posix(),
            "runtime_receipt_sha256": sha256_file(RUNTIME_RECEIPT_PATH),
            "authority_binary_path": AUTHORITY_BINARY_PATH.relative_to(ROOT).as_posix(),
            "authority_binary_sha256": AUTHORITY_BINARY_SHA256,
            "candidate_binary_path": CANDIDATE_BINARY_PATH.relative_to(ROOT).as_posix(),
            "candidate_binary_sha256": CANDIDATE_BINARY_SHA256,
        },
        "contract_binding": {
            "contract_spec_sha256": sha256_file(CONTRACT_PATH),
            "comparator_freeze_sha256": sha256_file(COMPARATOR_FREEZE_PATH),
            "comparator_sha256": sha256_file(COMPARATOR_PATH),
            "parameter_bundle_sha256": PARAMETER_BUNDLE_SHA256,
        },
        "input_sha256": {
            path.relative_to(ROOT).as_posix(): sha256_file(path)
            for path in (
                QUERY_UNIVERSE_PATH, TARGET_UNIVERSE_PATH, EXCLUSION_PATH,
                SAMPLE_SIZE_PATH, CONTRACT_PATH, OPERATING_ENVELOPE_PATH,
                RESOURCE_MODEL_PATH, RESOURCE_PLAN_PATH, OWNER_QUOTA_PATH,
            )
        },
        "output_sha256": {
            MANIFEST_PATH.relative_to(ROOT).as_posix(): manifest_sha,
            ATTEMPT_PLAN_PATH.relative_to(ROOT).as_posix(): sha256_bytes(attempt_bytes),
            RESOURCE_PROJECTION_PATH.relative_to(ROOT).as_posix(): sha256_bytes(projection_bytes),
            RESOURCE_DECISION_PATH.relative_to(ROOT).as_posix(): sha256_bytes(decision_bytes),
        },
        "exclusion_checks": {
            "query_digest_overlap": 0,
            "query_namespaced_ordinal_overlap": 0,
            "query_accession_or_debug_identity_overlap": 0,
            "target_digest_overlap": 0,
            "target_namespaced_ordinal_overlap": 0,
            "target_accession_or_debug_identity_overlap": 0,
            "pair_digest_overlap": 0,
            "hard_gate_pass": True,
        },
        "resource_decision": decision["status"],
        "resource_decision_sha256": sha256_bytes(decision_bytes),
        "post_freeze_quota_raise_allowed": False,
    }
    return {
        MANIFEST_PATH: manifest_bytes,
        ATTEMPT_PLAN_PATH: attempt_bytes,
        MANIFEST_CHECKSUM_PATH: f"{manifest_sha}  {MANIFEST_PATH.name}\n".encode("ascii"),
        RESOURCE_PROJECTION_PATH: projection_bytes,
        RESOURCE_DECISION_PATH: decision_bytes,
        PLAN_PATH: canonical_json_bytes(plan),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify frozen outputs byte-for-byte")
    args = parser.parse_args()
    try:
        payloads = build()
    except (FreezeError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.exit(1, f"Phase 3 fresh holdout freeze failed: {error}\n")
    if args.check:
        stale = [path.relative_to(ROOT).as_posix() for path, payload in payloads.items() if not path.is_file() or path.read_bytes() != payload]
        if stale:
            parser.exit(1, "stale Phase 3 fresh holdout artifacts: " + ", ".join(stale) + "\n")
        print("biological Top-K Phase 3 fresh holdout reproduces byte-for-byte")
        return 0
    for path, payload in payloads.items():
        atomic_write(path, payload)
    print(f"wrote {len(payloads)} deterministic Phase 3 holdout artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [name for name in globals() if not name.startswith("_")]
