#!/usr/bin/env python3
"""Freeze the fresh-query production-promoter validation panel."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import statistics
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_ROOT = ROOT / "docs/exact_long_query_hybrid_checkpoint_v1"
DOC_ROOT = ROOT / "docs/exact_long_query_hybrid_promoter_panel_v1"
QUERY_ROOT = Path(
    "/data/wenyujianData/linjieData/lncrna_sequences/"
    "human_GRCh38_GENCODE_v33/gene_exon_union"
)
QUERY_UNIVERSE = QUERY_ROOT / "gene_exon_union.tsv"
PROMOTER_ROOT = Path(
    "/data/wenyujianData/linjieData/promoter_sequences/"
    "human_GRCh38_GENCODE_v33_genes20cells_tss_promoters_v1"
)
RUN_ROOT = Path(
    "/data/wenyujianData/linjieData/longtarget_runs/"
    "exact_long_query_hybrid_promoter_panel_v1"
)
BINARY = Path(
    "/data/wenyujianData/linjieData/longtarget_runs/"
    "exact_long_query_hybrid_checkpoint_v1/clean_build_61da9b6/"
    "fasim_longtarget_gasal2_61da9b6"
)
BINARY_SHA256 = "6e9d5cec5ff50c9652b9aeb05a8a5533a9d707e0799d9925b2686377cdfdd7ee"
SOURCE_COMMIT = "61da9b6f1b3d998043d512f5703dc95671d2383e"
PANEL_VERSION = "exact_long_query_hybrid_promoter_panel_v1"
SELECTION_TARGETS = (
    ("4_6kb_low", 4000, 6000, 4500),
    ("4_6kb_high", 4000, 6000, 5500),
    ("7_9kb_low", 7000, 9000, 7500),
    ("7_9kb_high", 7000, 9000, 8500),
    ("10_13kb_low", 10000, 13000, 10500),
    ("10_13kb_high", 10000, 13000, 12500),
)
EXPLICIT_EXCLUSIONS = {
    "ENSG00000179406": ("LINC00174", "independent_segment_long_query_diagnostic"),
    "ENSG00000205181": ("LINC00654", "independent_segment_long_query_diagnostic"),
    "ENSG00000224078": ("SNHG14", "initial_long_query_gpu_runtime"),
    "ENSG00000224271": ("AL117329.1", "initial_long_query_gpu_runtime"),
    "ENSG00000229613": ("LINC01501", "stateful_and_hybrid_development_fixture"),
    "ENSG00000267107": ("PCAT19", "hybrid_length_promotion_fixture"),
    "ENSG00000271913": ("AL035530.2", "hybrid_length_promotion_fixture"),
}
TRIAL52 = Path(
    "/data/wenyujianData/linjieData/longtarget_runs/"
    "human_trial52_longest_GRCh38_GENCODE_v33/all_tasks.tsv"
)
SEGMENT_GRID = Path(
    "/data/wenyujianData/linjieData/longtarget_runs/"
    "human_genes20cells_segment_grid_consistency_v1/tasks.tsv"
)
OWNER_PROBE = Path(
    "/data/wenyujianData/linjieData/longtarget_runs/"
    "segment_owner_authority_probe_v1/tasks.tsv"
)
PRODUCTION_ATTEMPT_GLOB = (
    "/data/wenyujianData/linjieData/longtarget_runs/"
    "human_genes20cells_ge2048_*/raw_jobs/ENSG*"
)
FULL_TARGET = PROMOTER_ROOT / "promoter_components_concat.fa"
SHAKE_TARGET = PROMOTER_ROOT / "shards/shard_0009.fa"
FULL_TARGET_LENGTH = 164_917_643
SHAKE_TARGET_LENGTH = 4_942_620
CHECKPOINT_TARGET_LENGTH = 2_000_000
FORMAL_REPEATS = 3
SHAKE_QUERY_ID = "ENSG00000229613"


class PreparationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PreparationError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected JSON object: {path}")
    return value


def read_tsv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
    require(reader.fieldnames is not None and rows, f"empty TSV: {path}")
    require(
        all(None not in row and all(value is not None for value in row.values()) for row in rows),
        f"malformed TSV: {path}",
    )
    return tuple(reader.fieldnames), rows


def tsv_bytes(fields: Iterable[str], rows: Iterable[Mapping[str, object]]) -> bytes:
    field_tuple = tuple(fields)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=field_tuple,
        delimiter="\t",
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".tmp.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def fasta_sequence(path: Path) -> tuple[str, str]:
    header = ""
    chunks: list[str] = []
    records = 0
    with path.open("r", encoding="ascii") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith(">"):
                records += 1
                header = line[1:]
            elif line:
                require(records == 1, f"sequence outside sole record: {path}")
                chunks.append(line.upper())
    sequence = "".join(chunks)
    require(records == 1 and header and sequence, f"expected one non-empty FASTA record: {path}")
    require(set(sequence) <= set("ACGTN"), f"invalid FASTA base: {path}")
    return header, sequence


def short_fasta_bytes(gene_id: str, sequence: str) -> bytes:
    lines = [f">{gene_id}"]
    lines.extend(sequence[index : index + 80] for index in range(0, len(sequence), 80))
    return ("\n".join(lines) + "\n").encode("ascii")


def validate_checkpoint() -> dict[str, object]:
    decision = load_json(CHECKPOINT_ROOT / "decision.json")
    contract = load_json(CHECKPOINT_ROOT / "production_promoter_contract.json")
    require(decision["status"] == "checkpoint_gate_pass", "predecessor checkpoint did not pass")
    require(decision["authorization"]["next_engineering_stage"] == "fresh_real_promoter_validation_panel", "wrong predecessor next stage")
    require(decision["evidence"]["benchmark_source_commit"] == SOURCE_COMMIT, "predecessor source mismatch")
    require(decision["evidence"]["binary_sha256"] == BINARY_SHA256, "predecessor binary mismatch")
    require(BINARY.is_file() and sha256_file(BINARY) == BINARY_SHA256, "formal binary digest mismatch")
    require(contract["target_root"] == str(PROMOTER_ROOT), "production promoter root mismatch")
    require(contract["status"] == "frozen_not_executed", "unexpected production contract state")
    for relative, digest in contract["artifact_files"].items():
        require(sha256_file(PROMOTER_ROOT / relative) == digest, f"promoter artifact drift: {relative}")
    for relative, digest in contract["shard_file_sha256"].items():
        require(sha256_file(PROMOTER_ROOT / relative) == digest, f"promoter shard drift: {relative}")
    require(sha256_file(FULL_TARGET) == contract["artifact_files"]["promoter_components_concat.fa"], "full target drift")
    require(sha256_file(SHAKE_TARGET) == contract["shard_file_sha256"]["shards/shard_0009.fa"], "shake target drift")
    return {"decision": decision, "contract": contract}


def validate_target_decomposition() -> dict[str, object]:
    _, full_sequence = fasta_sequence(FULL_TARGET)
    require(len(full_sequence) == FULL_TARGET_LENGTH, "full target length mismatch")
    _, shard_rows = read_tsv(PROMOTER_ROOT / "shards.tsv")
    shard_sequences = []
    previous_end = 0
    for ordinal, row in enumerate(shard_rows, 1):
        require(row["shard_id"] == f"shard_{ordinal:04d}", "shard order mismatch")
        start = int(row["logical_concat_start0"])
        end = int(row["logical_concat_end0"])
        require(start == previous_end and end > start, "shard logical intervals are not contiguous")
        path = PROMOTER_ROOT / row["fasta_path"]
        _, sequence = fasta_sequence(path)
        require(len(sequence) == int(row["shard_length_bp"]) == end - start, "shard length mismatch")
        require(hashlib.sha256(sequence.encode("ascii")).hexdigest() == row["sequence_sha256"], "shard sequence digest mismatch")
        shard_sequences.append(sequence)
        previous_end = end
    require(previous_end == FULL_TARGET_LENGTH, "shards do not cover full logical target")
    require("".join(shard_sequences) == full_sequence, "ordered shards do not reconstruct the full target")
    return {
        "full_target_length_bp": len(full_sequence),
        "full_target_file_sha256": sha256_file(FULL_TARGET),
        "full_target_sequence_sha256": hashlib.sha256(full_sequence.encode("ascii")).hexdigest(),
        "shard_count": len(shard_rows),
        "ordered_shards_reconstruct_full_target": True,
        "reference_n_count": full_sequence.count("N"),
    }


def add_exclusion(
    values: dict[str, dict[str, set[str]]],
    gene_id: str,
    symbol: str,
    source: str,
    reason: str,
) -> None:
    require(gene_id.startswith("ENSG") and len(gene_id) == 15, f"invalid exclusion gene ID: {gene_id}")
    entry = values.setdefault(gene_id, {"symbols": set(), "sources": set(), "reasons": set()})
    if symbol:
        entry["symbols"].add(symbol)
    entry["sources"].add(source)
    entry["reasons"].add(reason)


def live_exclusions() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    exclusions: dict[str, dict[str, set[str]]] = {}
    source_receipts: list[dict[str, object]] = []
    for gene_id, (symbol, reason) in EXPLICIT_EXCLUSIONS.items():
        add_exclusion(exclusions, gene_id, symbol, "explicit_gpu_development_ledger_v1", reason)

    sources = (
        (TRIAL52, "human_trial52_longest", "gene_id", "gene_symbol", "long_query_segmented_development_panel"),
        (SEGMENT_GRID, "segment_grid_consistency", "gene_id", "gene_symbol", "segment_grid_development_panel"),
        (OWNER_PROBE, "segment_owner_authority", "gene_id", "gene_symbol", "owner_and_full_query_oracle_development"),
    )
    for path, label, id_field, symbol_field, reason in sources:
        _, rows = read_tsv(path)
        for row in rows:
            add_exclusion(exclusions, row[id_field], row[symbol_field], label, reason)
        source_receipts.append({"source": label, "path": str(path), "sha256": sha256_file(path), "rows": len(rows)})

    production_attempts = sorted(
        path for path in Path("/data/wenyujianData/linjieData/longtarget_runs").glob(
            "human_genes20cells_ge2048_*/raw_jobs/ENSG*"
        ) if path.is_dir()
    )
    snapshot_rows = []
    for path in production_attempts:
        gene_id = path.name
        state = "completed" if (path / "completed").is_dir() else "partial_or_planned"
        add_exclusion(
            exclusions,
            gene_id,
            "",
            "prior_production_target_attempt_snapshot",
            f"prior_production_target_{state}",
        )
        snapshot_rows.append(f"{gene_id}\t{state}\t{path}\n")
    source_receipts.append({
        "source": "prior_production_target_attempt_snapshot",
        "path_glob": PRODUCTION_ATTEMPT_GLOB,
        "rows": len(snapshot_rows),
        "snapshot_sha256": sha256_bytes("".join(snapshot_rows).encode("utf-8")),
    })

    rows = []
    for gene_id in sorted(exclusions):
        value = exclusions[gene_id]
        rows.append({
            "gene_id": gene_id,
            "gene_symbols": ",".join(sorted(value["symbols"])),
            "exclusion_sources": ",".join(sorted(value["sources"])),
            "exclusion_reasons": ",".join(sorted(value["reasons"])),
        })
    return rows, source_receipts


def load_frozen_exclusions(path: Path) -> list[dict[str, object]]:
    fields, rows = read_tsv(path)
    require(fields == ("gene_id", "gene_symbols", "exclusion_sources", "exclusion_reasons"), "exclusion schema mismatch")
    return [dict(row) for row in rows]


def select_queries(exclusion_rows: Iterable[Mapping[str, object]]) -> tuple[list[dict[str, object]], dict[str, object]]:
    excluded = {str(row["gene_id"]) for row in exclusion_rows}
    _, universe = read_tsv(QUERY_UNIVERSE)
    eligible_counts: dict[str, int] = defaultdict(int)
    universe_counts: dict[str, int] = defaultdict(int)
    selected_ids: set[str] = set()
    selected: list[dict[str, object]] = []
    for label, minimum, maximum, target in SELECTION_TARGETS:
        candidates = []
        for row in universe:
            length = int(row["union_exonic_length"])
            if minimum <= length <= maximum:
                universe_counts[label] += 1
                if row["gene_id"] not in excluded and row["gene_id"] not in selected_ids:
                    candidates.append(row)
        eligible_counts[label] = len(candidates)
        require(candidates, f"no eligible query for {label}")
        chosen = min(
            candidates,
            key=lambda row: (abs(int(row["union_exonic_length"]) - target), row["gene_id"]),
        )
        gene_id = chosen["gene_id"]
        selected_ids.add(gene_id)
        source = QUERY_ROOT / chosen["individual_fasta"]
        _, sequence = fasta_sequence(source)
        length = len(sequence)
        require(length == int(chosen["union_exonic_length"]), f"query length mismatch: {gene_id}")
        require("N" not in sequence, f"fresh query contains N: {gene_id}")
        require(hashlib.sha256(sequence.encode("ascii")).hexdigest() == chosen["sequence_sha256"], f"query sequence digest mismatch: {gene_id}")
        runtime = RUN_ROOT / "inputs" / f"{gene_id}.fa"
        runtime_bytes = short_fasta_bytes(gene_id, sequence)
        required_smem = 3 * math.ceil(length / 32) * 32 * 2
        selected.append({
            "panel_version": PANEL_VERSION,
            "selection_status": "fresh_at_preexecution_freeze",
            "length_stratum": label.rsplit("_", 1)[0],
            "selection_target_nt": target,
            "selection_distance_nt": abs(length - target),
            "gene_id": gene_id,
            "gene_symbol": chosen["input_gene_symbol"],
            "gene_strand": chosen["list_strand"],
            "query_length_nt": length,
            "source_transcript_count": chosen["source_transcript_count"],
            "union_segment_count": chosen["union_segment_count"],
            "gc_percent": f"{100.0 * (sequence.count('G') + sequence.count('C')) / length:.6f}",
            "n_count": 0,
            "sequence_sha256": chosen["sequence_sha256"],
            "source_fasta": str(source),
            "source_fasta_sha256": sha256_file(source),
            "runtime_fasta": str(runtime),
            "runtime_fasta_sha256": sha256_bytes(runtime_bytes),
            "required_dynamic_smem_bytes": required_smem,
            "resource_fit_on_checkpoint_device": int(required_smem <= 101_376),
            "historical_exclusion_status": "fresh_eligible",
            "runtime_bytes": runtime_bytes,
        })
    summary = {
        "universe_rows": len(universe),
        "universe_sha256": sha256_file(QUERY_UNIVERSE),
        "excluded_gene_ids": len(excluded),
        "eligible_counts_by_selection_target": dict(eligible_counts),
        "universe_counts_by_selection_target": dict(universe_counts),
        "selection_rule": "nearest union-exonic length to each fixed target; tie by gene_id; no gene reused",
    }
    return selected, summary


def interpolate(query_length: int, points: list[tuple[int, float]]) -> float:
    require(points == sorted(points), "timing points must be sorted")
    for (left_x, left_y), (right_x, right_y) in zip(points, points[1:]):
        if left_x <= query_length <= right_x:
            fraction = (query_length - left_x) / (right_x - left_x)
            return left_y + fraction * (right_y - left_y)
    if query_length < points[0][0]:
        left, right = points[0], points[1]
    else:
        left, right = points[-2], points[-1]
    return left[1] + (query_length - left[0]) * (right[1] - left[1]) / (right[0] - left[0])


def cost_rows(selected: list[dict[str, object]]) -> tuple[list[dict[str, object]], dict[str, float]]:
    fields, results = read_tsv(CHECKPOINT_ROOT / "checkpoint_results.tsv")
    require("median_paired_speedup" in fields, "checkpoint result timing schema mismatch")
    full = sorted(
        (
            int(row["query_length_nt"]),
            float(row["median_baseline_wall_seconds"]),
            float(row["median_candidate_wall_seconds"]),
        )
        for row in results
        if row["mode"] == "tfosorted"
    )
    baseline_points = [(length, baseline) for length, baseline, _ in full]
    candidate_points = [(length, candidate) for length, _, candidate in full]
    scale = FULL_TARGET_LENGTH / CHECKPOINT_TARGET_LENGTH
    rows = []
    totals = {"baseline_core_hours": 0.0, "candidate_gpu_hours": 0.0, "paired_wall_hours_serial": 0.0}
    for query in selected:
        length = int(query["query_length_nt"])
        baseline_seconds = interpolate(length, baseline_points) * scale
        candidate_seconds = interpolate(length, candidate_points) * scale
        baseline_hours = baseline_seconds * FORMAL_REPEATS / 3600
        candidate_hours = candidate_seconds * FORMAL_REPEATS / 3600
        totals["baseline_core_hours"] += baseline_hours
        totals["candidate_gpu_hours"] += candidate_hours
        totals["paired_wall_hours_serial"] += baseline_hours + candidate_hours
        rows.append({
            "gene_id": query["gene_id"],
            "gene_symbol": query["gene_symbol"],
            "query_length_nt": length,
            "target_length_bp": FULL_TARGET_LENGTH,
            "target_scale_vs_checkpoint": f"{scale:.9f}",
            "estimated_baseline_seconds_per_run": f"{baseline_seconds:.3f}",
            "estimated_candidate_seconds_per_run": f"{candidate_seconds:.3f}",
            "formal_repeats": FORMAL_REPEATS,
            "estimated_baseline_core_hours": f"{baseline_hours:.3f}",
            "estimated_candidate_gpu_hours": f"{candidate_hours:.3f}",
            "estimate_role": "linear_target_length_planning_only",
        })
    return rows, totals


def execution_rows(selected: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for arm in ("baseline", "candidate"):
        rows.append({
            "stage": "observed_query_shard9_shake_down",
            "workload_id": f"shake_{SHAKE_QUERY_ID}_shard_0009",
            "gene_id": SHAKE_QUERY_ID,
            "target_artifact_id": "shard_0009",
            "target_path": str(SHAKE_TARGET),
            "target_length_bp": SHAKE_TARGET_LENGTH,
            "arm": arm,
            "repeat": 1,
            "scientific_sample": 0,
            "authorization": "authorized_pre_formal_gate",
        })
    for query in selected:
        for repeat in range(1, FORMAL_REPEATS + 1):
            for arm in ("baseline", "candidate"):
                rows.append({
                    "stage": "fresh_full_promoter_panel",
                    "workload_id": f"fresh_{query['gene_id']}_full_concat",
                    "gene_id": query["gene_id"],
                    "target_artifact_id": "logical_full_concat",
                    "target_path": str(FULL_TARGET),
                    "target_length_bp": FULL_TARGET_LENGTH,
                    "arm": arm,
                    "repeat": repeat,
                    "scientific_sample": 1,
                    "authorization": "pending_shake_down_gate",
                })
    return rows


def build_artifacts(
    exclusions: list[dict[str, object]],
    source_receipts: list[dict[str, object]],
    selected: list[dict[str, object]],
    selection_summary: dict[str, object],
    target: dict[str, object],
    frozen_utc: str,
) -> dict[str, bytes]:
    query_fields = tuple(key for key in selected[0] if key != "runtime_bytes")
    query_rows = [{key: value for key, value in row.items() if key != "runtime_bytes"} for row in selected]
    costs, totals = cost_rows(selected)
    matrix = execution_rows(selected)
    target_contract = {
        "schema_version": "exact_long_query_hybrid_promoter_target_execution_contract_v1",
        "status": "frozen_before_execution",
        "target_root": str(PROMOTER_ROOT),
        "scientific_target_artifact": {
            "artifact_id": "logical_full_concat",
            "path": str(FULL_TARGET),
            "length_bp": FULL_TARGET_LENGTH,
            "file_sha256": sha256_file(FULL_TARGET),
        },
        "operational_shards": {
            "count": target["shard_count"],
            "ordered_reconstruction_exact": target["ordered_shards_reconstruct_full_target"],
            "formal_scientific_execution_uses_independent_shard_runs": False,
            "reason": "no validated shard merge preserves global TFOsorted order and DBD tie semantics",
        },
        "mapping_rules": {
            "coordinate_system": "0-based half-open after strand-specific LongTarget normalization",
            "cross_component_hit": "reject before DBD clustering or ranking",
            "reference_derived_n_hit": "reject before DBD clustering or ranking",
            "component_to_genome": "genomic_start0 = component.genomic_start0 + logical_start0 - component.logical_concat_start0",
            "overlap_annotation": "retain every original promoter wholly containing the mapped hit",
        },
        "target_identity": target,
    }
    boundary = {
        "schema_version": "exact_long_query_hybrid_promoter_boundary_fixture_contract_v1",
        "status": "required_before_formal_execution",
        "fixtures": [
            "hit wholly within component at left edge",
            "hit wholly within component at right edge",
            "hit crossing adjacent component boundary is rejected",
            "hit overlapping a reference-derived N is rejected",
            "hit in an overlapping component maps to every wholly containing promoter instance",
            "plus-strand promoter transcriptional-relative coordinates",
            "minus-strand promoter transcriptional-relative coordinates",
            "ordered shards reconstruct the canonical full concat byte-for-byte",
        ],
        "positive_control_requirement": "cross-component and reference-N rejection must each be exercised; zero natural events is not a pass",
    }
    predecessor = load_json(CHECKPOINT_ROOT / "decision.json")
    preexecution = {
        "schema_version": "exact_long_query_hybrid_promoter_panel_preexecution_decision_v1",
        "status": "shake_down_authorized_formal_panel_pending",
        "panel_version": PANEL_VERSION,
        "frozen_utc": frozen_utc,
        "predecessor": {
            "checkpoint_status": predecessor["status"],
            "checkpoint_decision_sha256": sha256_file(CHECKPOINT_ROOT / "decision.json"),
            "benchmark_source_commit": SOURCE_COMMIT,
            "formal_binary_sha256": BINARY_SHA256,
        },
        "selection": {
            **selection_summary,
            "selected_query_count": len(selected),
            "selected_gene_ids": [row["gene_id"] for row in selected],
            "selection_uses_alignment_or_affinity_results": False,
            "freshness_definition": "not used in frozen long-query GPU development panels and no production-target raw job present at freeze",
            "historical_exclusion_sources": source_receipts,
        },
        "execution": {
            "shake_down_runs": 2,
            "formal_runs": 36,
            "formal_query_target_workloads": 6,
            "technical_repeats_per_arm": FORMAL_REPEATS,
            "target_execution_shape": "one canonical full concat per run",
            "output_mode": "tfosorted",
            "candidate_execution": "stateful GPU scoreInfo + all-attempt GPU endpoint + host selection + selected CPU continuation",
            "cpu_threads_per_run": 1,
            "speedup_gate": 1.5,
        },
        "planning_cost": {
            **{key: round(value, 3) for key, value in totals.items()},
            "estimate_is_authorization_or_claim": False,
        },
        "formal_entry_gates": [
            "shake-down paired raw TFOsorted byte equality",
            "complete GPU attempt coverage and zero oracle/replay/fallback/continuation failures",
            "boundary fixture contract pass including positive cross-component and reference-N controls",
            "CPU and candidate decode-map outputs exact",
            "DBD1, DBS peak set, promoter/gene affinity outputs exact at threshold zero",
            "no selected query acquires a prior external production-target result after freeze",
        ],
        "formal_panel_authorized": False,
        "production_authorized": False,
        "validated_continuous_range": False,
        "bioinformatics_v2_state_modified": False,
    }
    artifacts = {
        "historical_query_exclusions.tsv": tsv_bytes(
            ("gene_id", "gene_symbols", "exclusion_sources", "exclusion_reasons"), exclusions
        ),
        "fresh_queries.tsv": tsv_bytes(query_fields, query_rows),
        "cost_estimate.tsv": tsv_bytes(
            (
                "gene_id", "gene_symbol", "query_length_nt", "target_length_bp", "target_scale_vs_checkpoint",
                "estimated_baseline_seconds_per_run", "estimated_candidate_seconds_per_run", "formal_repeats",
                "estimated_baseline_core_hours", "estimated_candidate_gpu_hours", "estimate_role",
            ),
            costs,
        ),
        "execution_matrix.tsv": tsv_bytes(
            (
                "stage", "workload_id", "gene_id", "target_artifact_id", "target_path",
                "target_length_bp", "arm", "repeat", "scientific_sample", "authorization",
            ),
            matrix,
        ),
        "target_execution_contract.json": json_bytes(target_contract),
        "boundary_fixture_contract.json": json_bytes(boundary),
        "preexecution_decision.json": json_bytes(preexecution),
    }
    checksum_rows = [
        f"{sha256_bytes(value)}  docs/exact_long_query_hybrid_promoter_panel_v1/{name}\n"
        for name, value in sorted(artifacts.items())
    ]
    artifacts["checksums.sha256"] = "".join(checksum_rows).encode("ascii")
    return artifacts


def status_bytes(selected: list[dict[str, object]], artifacts: Mapping[str, bytes]) -> bytes:
    rows = [
        "# Exact long-query hybrid real-promoter panel v1",
        "",
        "This stage is downstream of checkpoint `500b010`. It does not modify the",
        "frozen `61da9b6` runtime or reopen Bioinformatics v2.",
        "",
        "## Preexecution state",
        "",
        "```text",
        "shake_down_authorized = true",
        "formal_panel_authorized = false",
        "production_authorized = false",
        "```",
        "",
        "Six queries were selected only by fixed length targets after applying the",
        "frozen historical-exclusion ledger:",
        "",
        "| Stratum | Gene | Length | Required dynamic shared memory |",
        "| --- | --- | ---: | ---: |",
    ]
    rows.extend(
        f"| {row['length_stratum']} | {row['gene_symbol']} ({row['gene_id']}) | "
        f"{int(row['query_length_nt']):,} nt | {int(row['required_dynamic_smem_bytes']):,} bytes |"
        for row in selected
    )
    rows.extend([
        "",
        "The formal target is the complete 164,917,643 bp canonical concat. The nine",
        "shards are identity and reconstruction artifacts only: independent shard",
        "execution is not substituted because no validated merge preserves global",
        "TFOsorted order and DBD tie semantics.",
        "",
        "Before the 36 formal runs, LINC01501 x shard_0009 must pass paired raw-output,",
        "GPU accounting, coordinate mapping, DBD/DBS/affinity, and positive boundary",
        "fixtures. Passing the shake-down permits a separate execution addendum; it",
        "does not itself authorize production.",
        "",
        "Tracked preexecution artifact SHA-256 values are in `checksums.sha256`.",
    ])
    return ("\n".join(rows) + "\n").encode("utf-8")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--write", action="store_true")
    result.add_argument("--output-dir", type=Path, default=DOC_ROOT)
    result.add_argument("--run-root", type=Path, default=RUN_ROOT)
    return result


def main() -> int:
    args = parser().parse_args()
    global RUN_ROOT
    RUN_ROOT = args.run_root
    validate_checkpoint()
    target = validate_target_decomposition()
    exclusion_path = args.output_dir / "historical_query_exclusions.tsv"
    if args.write:
        exclusions, source_receipts = live_exclusions()
        frozen_utc = datetime.now(timezone.utc).isoformat()
    else:
        exclusions = load_frozen_exclusions(exclusion_path)
        decision = load_json(args.output_dir / "preexecution_decision.json")
        source_receipts = decision["selection"]["historical_exclusion_sources"]
        frozen_utc = str(decision["frozen_utc"])
    selected, selection_summary = select_queries(exclusions)
    artifacts = build_artifacts(
        exclusions,
        source_receipts,
        selected,
        selection_summary,
        target,
        frozen_utc,
    )
    artifacts["STATUS.md"] = status_bytes(selected, artifacts)
    if args.write:
        for row in selected:
            atomic_bytes(Path(str(row["runtime_fasta"])), bytes(row["runtime_bytes"]))
        for name, value in artifacts.items():
            atomic_bytes(args.output_dir / name, value)
    else:
        for row in selected:
            runtime = Path(str(row["runtime_fasta"]))
            require(runtime.is_file() and sha256_file(runtime) == row["runtime_fasta_sha256"], f"runtime query drift: {runtime}")
        for name, value in artifacts.items():
            path = args.output_dir / name
            require(path.is_file() and path.read_bytes() == value, f"frozen preexecution artifact drift: {path}")
    print(json.dumps({
        "status": "preexecution_frozen" if args.write else "preexecution_verified",
        "selected_queries": [row["gene_id"] for row in selected],
        "formal_runs": 36,
        "formal_panel_authorized": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PreparationError, OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        raise SystemExit(2)
