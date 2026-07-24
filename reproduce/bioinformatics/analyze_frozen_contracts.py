#!/usr/bin/env python3
"""Decompose the immutable development evidence into Phase 2 contract matrices."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable


FREEZE_ID = "paper-data-v1-dccfd49-20260716"
RUNTIME_EPOCH = "0"
RUNTIME_COMMIT = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
RANKS = ("score", "stability", "nt")
OUTPUT_NAMES = (
    "frozen_contract_matrix.tsv",
    "mismatch_feature_matrix.tsv",
    "mismatch_analysis.md",
)
WORKLOAD_IDS = (
    "g01_malat1_5p_1024_chr11",
    "g02_malat1_mid_2048_chr21",
    "g03_malat1_3p_2812_chr22",
    "g04_neat1_5p_2048_chr22",
    "g05_neat1_mid_2812_chr11",
    "g06_neat1_3p_1024_chr21",
    "g07_kcnq1ot1_5p_2812_chr21",
    "g08_kcnq1ot1_mid_1024_chr22",
    "g09_kcnq1ot1_3p_2048_chr11",
    "g10_h19_full_chr11",
    "g11_h19_full_chr21",
    "g12_h19_full_chr22",
    "g13_meg3_full_chr11",
)
EXPECTED_MISMATCH_POSITIONS = {
    ("g02_malat1_mid_2048_chr21", "stability"): (2, 3, 4, 5),
    ("g09_kcnq1ot1_3p_2048_chr11", "nt"): (5,),
    ("g12_h19_full_chr22", "stability"): (2,),
}

SOURCE_SHA256 = {
    "paper/source_data/generalization_workloads_pre_freeze.tsv": "ae84d571aba972268b417ec6790d6cc6f5c0da2be77c6dd71599eb768fb04204",
    "paper/source_data/generalization_pairs_pre_freeze.tsv": "3086b5e0d45513a21babeb3c59b30d44ca248f3a8fed1fd2b7773f9d0b7bb449",
    "paper/source_data/generalization_runs_pre_freeze.tsv": "af77f849936b7988b2e0d075052a1bf78a409ffd22c70590195ca10ae9099942",
    "paper/source_data/generalization_mismatch_top5_pre_freeze.tsv": "8c82690b26d5c8c3714e2d659a61274f9a53d416f19c8d1a6bbb10b533231d32",
    "paper/workload_manifest.tsv": "b099762257b60ce2922a7e19920bad30e05b9cdf2af4381c60596a41ca3cb7d3",
    "paper/source_data/source_data_manifest.tsv": "55f8bc9d44d0fc63f5a111f37130a7e91684ba99e9aa00a8d3a0e3b234b57663",
}
ARTIFACT_MANIFEST_REL = (
    ".paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization/"
    "phase3-artifacts.tsv"
)
ARTIFACT_MANIFEST_SHA256 = (
    "ef16dbbb7250304a46ac28d2584bedfd1186e3497fd7bc8038b3b004edc52b40"
)
TOOL_SHA256 = {
    "scripts/compare_fasim_segmented_contract.py": "6a589d7960a69be7c84a410f1bbd9d3ea34de929f8f04943d9c7ae033d682eda",
    "scripts/compare_fasim_lite_offline_cluster_topk.py": "2765d76b6c8e742596b1072a413309a88ef415f3576c9de62be67213ee76dc80",
    "scripts/fasim_tfo_archive.py": "3fb42809c4f31b31ec05bcaf9d3249f4059a910164a6ca33d5a789fb0efab856",
}

WORKLOAD_SCHEMA = """workload_id claim_id role query_id query_length_nt fragment_position target_id target_region preset_id output_contract status repeat_consistent valid_pairs median_baseline_wall_seconds median_candidate_wall_seconds median_paired_speedup paired_speedup_q1 paired_speedup_q3 paired_speedup_min paired_speedup_max clustered_score_all_equal clustered_stability_all_equal clustered_nt_all_equal boundary_ties_all_equal raw_score_all_equal raw_stability_all_equal raw_nt_all_equal full_missing_rows_total full_extra_rows_total fallbacks_total oom_total gasal2_requests_total traceback_requests_total baseline_rss_peak_kb candidate_rss_peak_kb baseline_gpu_memory_peak_mib candidate_gpu_memory_peak_mib""".split()
PAIR_SCHEMA = """pair_id_text workload_id claim_id role query_id query_length_nt fragment_position target_id target_region preset_id pair_id pair_order runtime_epoch runtime_commit comparator_version output_contract baseline_wall_seconds candidate_wall_seconds paired_speedup baseline_max_rss_kb candidate_max_rss_kb baseline_gpu_memory_peak_mib candidate_gpu_memory_peak_mib raw_score_top5_equal raw_stability_top5_equal raw_nt_top5_equal clustered_score_top5_equal clustered_stability_top5_equal clustered_nt_top5_equal all_three_top5_equal boundary_ties_equal baseline_boundary_tie_groups candidate_boundary_tie_groups baseline_representative_conflict_clusters candidate_representative_conflict_clusters full_missing_rows full_extra_rows candidate_active_path gasal2_requests traceback_requests fallbacks length_guard_fallbacks runtime_batch_fallbacks overflow_fallbacks oom status decision details_path pair_summary_path""".split()
RUN_SCHEMA = """run_id workload_id role query_id query_length_nt fragment_position target_id target_region pair_id mode warmup status runtime_epoch config_digest_sha256 wall_seconds max_rss_kb gpu_memory_peak_mib gpu_temperature_peak_c gpu_power_peak_w receipt_path""".split()
MANIFEST_SCHEMA = """workload_id claim_id family role query_id query_path query_sha256 query_start_nt query_end_nt query_length_nt fragment_position target_id target_path target_sha256 target_region rule baseline_mode candidate_mode output_contract required_pairs requires_gpu_count max_wall_seconds preset_id preregistered adapter_id""".split()
SOURCE_MANIFEST_SCHEMA = "data_freeze_id path kind row_count size_bytes sha256".split()
ARTIFACT_MANIFEST_SCHEMA = "artifact_path size_bytes sha256".split()

TFOSORTED_COLUMNS = (
    "QueryStart", "QueryEnd", "StartInSeq", "EndInSeq", "Direction", "Chr",
    "StartInGenome", "EndInGenome", "MeanStability", "MeanIdentity(%)",
    "Strand", "Rule", "Score", "Nt(bp)", "Class", "MidPoint", "Center",
    "TFO sequence", "TTS sequence",
)
MISMATCH_SCHEMA = [
    "pair_id_text", "workload_id", "pair_status", "side", "kind", "mode",
    "rank", "cluster_id", *TFOSORTED_COLUMNS,
]

CONTRACT_FIELDS = """source_freeze_id runtime_epoch runtime_commit workload_id role query_id query_length_nt fragment_position query_start_nt query_end_nt query_a_count query_c_count query_g_count query_t_count query_normalized_sha256 target_id target_region preset_id output_contract frozen_status repeat_count repeat_contract_status_consistent baseline_repeat_top5_signature_consistent candidate_repeat_top5_signature_consistent repeat_top5_signature_consistent repeat_top5_signature_availability_reason repeat_consistency_basis score_clean score_mismatch score_clean_pairs score_mismatch_pairs stability_clean stability_mismatch stability_clean_pairs stability_mismatch_pairs nt_clean nt_mismatch nt_clean_pairs nt_mismatch_pairs all_ranked_clean all_ranked_clean_pairs all_ranked_mismatch_pairs raw_score_clean raw_stability_clean raw_nt_clean full_row_equal full_missing_rows_total full_extra_rows_total comparator_boundary_ties_all_equal baseline_comparator_tie_groups_total candidate_comparator_tie_groups_total candidate_active_path_all_pairs fallbacks_total length_guard_fallbacks_total runtime_batch_fallbacks_total overflow_fallbacks_total allocation_state allocation_state_availability_reason oom_total baseline_output_rows candidate_output_rows output_rows_pair baseline_output_digest_repeat_consistent candidate_output_digest_repeat_consistent output_digest_repeat_consistent runtime_telemetry_available runtime_telemetry_availability_reason runtime_run_count gasal2_requests_total traceback_requests_total baseline_rss_peak_kb candidate_rss_peak_kb baseline_gpu_memory_peak_mib candidate_gpu_memory_peak_mib""".split()

FEATURE_FIELDS = """source_freeze_id runtime_epoch runtime_commit workload_id query_id query_length_nt fragment_position query_a_count query_c_count query_g_count query_t_count query_normalized_sha256 target_id target_region rank rank_equal mismatch_pair_count differing_position_count differing_positions top5_details_available top5_details_availability_reason baseline_top5_identities candidate_top5_identities baseline_primary_values candidate_primary_values comparator_boundary_ties_equal baseline_comparator_tie_groups_all_ranks candidate_comparator_tie_groups_all_ranks baseline_rank5_rank6_primary_margin candidate_rank5_rank6_primary_margin baseline_rank5_rank6_primary_equal candidate_rank5_rank6_primary_equal primary_margin_availability_reason baseline_output_rows candidate_output_rows full_missing_rows full_extra_rows candidate_active_path fallbacks length_guard_fallbacks runtime_batch_fallbacks overflow_fallbacks allocation_state allocation_state_availability_reason oom runtime_telemetry_available runtime_telemetry_availability_reason gasal2_requests traceback_requests repeat_count repeat_contract_status_consistent baseline_repeat_top5_signature_consistent candidate_repeat_top5_signature_consistent repeat_top5_signature_consistent repeat_top5_signature_availability_reason repeat_consistency_basis evidence_pair_id""".split()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sha256(path: Path, expected: str) -> None:
    if not path.is_file():
        raise ValueError(f"required frozen source is missing: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(
            f"checksum drift for {path}: expected {expected}, observed {actual}"
        )


def read_tsv(path: Path, expected_schema: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != expected_schema:
            raise ValueError(
                f"schema drift for {path}: expected {expected_schema}, "
                f"observed {reader.fieldnames or []}"
            )
        rows: list[dict[str, str]] = []
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"malformed TSV row {line_number} in {path}")
            rows.append(dict(row))
    return rows


def unique_by(rows: Iterable[dict[str, str]], key: str, label: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        value = row[key]
        if value in result:
            raise ValueError(f"duplicate {label}: {value}")
        result[value] = row
    return result


def require_equal(label: str, *values: str) -> None:
    if len(set(values)) != 1:
        raise ValueError(f"join drift for {label}: {values}")


def load_fasta_sequence(path: Path) -> str:
    records = 0
    sequence: list[str] = []
    with path.open(encoding="ascii") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            if text.startswith(">"):
                records += 1
                if records > 1:
                    raise ValueError(f"multiple FASTA records in {path}")
                continue
            if records != 1:
                raise ValueError(f"sequence before FASTA header at {path}:{line_number}")
            sequence.append(text.upper())
    normalized = "".join(sequence)
    if records != 1 or not normalized:
        raise ValueError(f"empty FASTA input: {path}")
    invalid = sorted(set(normalized) - set("ACGT"))
    if invalid:
        raise ValueError(f"noncanonical FASTA bases in {path}: {''.join(invalid)}")
    return normalized


def row_identity(row: dict[str, str]) -> str:
    payload = "\t".join(row[column] for column in TFOSORTED_COLUMNS)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def row_full_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row[column] for column in TFOSORTED_COLUMNS)


def repeat_top5_signature_consistent(
    rows_by_pair: list[list[dict[str, str]]],
) -> int | None:
    if len(rows_by_pair) == 1:
        return None
    signatures = {
        tuple(row_full_key(row) for row in rows[:5]) for rows in rows_by_pair
    }
    return int(len(signatures) == 1)


def primary_value(row: dict[str, str], rank: str) -> str:
    return row[{"score": "Score", "stability": "MeanStability", "nt": "Nt(bp)"}[rank]]


def comparator_rank_values(row: dict[str, str], rank: str) -> tuple[float, float, float]:
    score = float(row["Score"])
    stability = float(row["MeanStability"])
    nt = float(row["Nt(bp)"])
    if rank == "score":
        return score, nt, stability
    if rank == "stability":
        return stability, nt, score
    if rank == "nt":
        return nt, score, stability
    raise ValueError(f"unknown ranking mode: {rank}")


def compact_ranked(values: list[str]) -> str:
    return ";".join(f"{index}:{value}" for index, value in enumerate(values, start=1))


def as_int(row: dict[str, str], field: str) -> int:
    try:
        return int(row[field])
    except ValueError as error:
        raise ValueError(f"expected integer {field} in {row}") from error


def format_margin(value: float) -> str:
    rendered = format(value, ".12g")
    return "0" if rendered in {"-0", "-0.0"} else rendered


def availability_value(value: int | None) -> str:
    return "NA" if value is None else str(value)


def render_tsv(fieldnames: list[str], rows: list[dict[str, str]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, delimiter="\t", lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_fsynced(path: Path, payload: bytes) -> None:
    with path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def publish_outputs_transactionally(
    output_dir: Path,
    outputs: dict[str, str],
    after_replace: Callable[[int, str], None] | None = None,
) -> None:
    if tuple(outputs) != OUTPUT_NAMES:
        raise ValueError(
            f"publication output set/order drift: expected {OUTPUT_NAMES}, "
            f"observed {tuple(outputs)}"
        )
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{output_dir.name}.frozen-contract-staging-",
            dir=output_dir.parent,
        )
    )
    existed: dict[str, bool] = {}
    replaced: list[str] = []
    try:
        for name in OUTPUT_NAMES:
            destination = output_dir / name
            if destination.exists() and not destination.is_file():
                raise ValueError(f"publication destination is not a file: {destination}")
            existed[name] = destination.is_file()
            _write_fsynced(staging / f"{name}.new", outputs[name].encode("utf-8"))
            if existed[name]:
                backup = staging / f"{name}.backup"
                shutil.copyfile(destination, backup)
                with backup.open("rb") as handle:
                    os.fsync(handle.fileno())
        _fsync_directory(staging)

        for step, name in enumerate(OUTPUT_NAMES, start=1):
            os.replace(staging / f"{name}.new", output_dir / name)
            replaced.append(name)
            _fsync_directory(output_dir)
            if after_replace is not None:
                after_replace(step, name)
    except BaseException:
        for name in reversed(replaced):
            destination = output_dir / name
            if existed[name]:
                os.replace(staging / f"{name}.backup", destination)
            else:
                destination.unlink(missing_ok=True)
        _fsync_directory(output_dir)
        raise
    finally:
        shutil.rmtree(staging)


def _load_comparator(repo_root: Path):
    scripts = repo_root / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from compare_fasim_segmented_contract import _analyze  # pylint: disable=import-outside-toplevel

    return _analyze


def _validate_sources(repo_root: Path) -> dict[str, list[dict[str, str]]]:
    for relative, digest in {**SOURCE_SHA256, **TOOL_SHA256}.items():
        validate_sha256(repo_root / relative, digest)
    validate_sha256(repo_root / ARTIFACT_MANIFEST_REL, ARTIFACT_MANIFEST_SHA256)

    sources = {
        "workloads": read_tsv(
            repo_root / "paper/source_data/generalization_workloads_pre_freeze.tsv",
            WORKLOAD_SCHEMA,
        ),
        "pairs": read_tsv(
            repo_root / "paper/source_data/generalization_pairs_pre_freeze.tsv",
            PAIR_SCHEMA,
        ),
        "runs": read_tsv(
            repo_root / "paper/source_data/generalization_runs_pre_freeze.tsv",
            RUN_SCHEMA,
        ),
        "mismatches": read_tsv(
            repo_root / "paper/source_data/generalization_mismatch_top5_pre_freeze.tsv",
            MISMATCH_SCHEMA,
        ),
        "manifest": read_tsv(repo_root / "paper/workload_manifest.tsv", MANIFEST_SCHEMA),
        "source_manifest": read_tsv(
            repo_root / "paper/source_data/source_data_manifest.tsv",
            SOURCE_MANIFEST_SCHEMA,
        ),
        "artifact_manifest": read_tsv(
            repo_root / ARTIFACT_MANIFEST_REL, ARTIFACT_MANIFEST_SCHEMA
        ),
    }
    freeze_ids = {row["data_freeze_id"] for row in sources["source_manifest"]}
    if freeze_ids != {FREEZE_ID}:
        raise ValueError(f"source freeze ID drift: {sorted(freeze_ids)}")
    return sources


def _validate_joins(sources: dict[str, list[dict[str, str]]]) -> dict[str, object]:
    workloads = unique_by(sources["workloads"], "workload_id", "workload")
    if tuple(workloads) != WORKLOAD_IDS:
        raise ValueError(
            f"supported workload drift: expected {WORKLOAD_IDS}, observed {tuple(workloads)}"
        )

    manifest_generalization = [
        row for row in sources["manifest"] if row["family"] == "generalization"
    ]
    manifest = unique_by(manifest_generalization, "workload_id", "manifest workload")
    if set(manifest) != set(WORKLOAD_IDS):
        raise ValueError("workload manifest generalization set drift")

    pairs_by_workload: dict[str, list[dict[str, str]]] = defaultdict(list)
    pair_ids: set[str] = set()
    for pair in sources["pairs"]:
        workload_id = pair["workload_id"]
        if workload_id not in workloads:
            raise ValueError(f"unknown pair workload: {workload_id}")
        if pair["pair_id_text"] in pair_ids:
            raise ValueError(f"duplicate pair ID: {pair['pair_id_text']}")
        pair_ids.add(pair["pair_id_text"])
        pairs_by_workload[workload_id].append(pair)
        if pair["runtime_epoch"] != RUNTIME_EPOCH or pair["runtime_commit"] != RUNTIME_COMMIT:
            raise ValueError(f"runtime provenance drift in {pair['pair_id_text']}")

    runs_by_workload: dict[str, list[dict[str, str]]] = defaultdict(list)
    run_ids: set[str] = set()
    for run in sources["runs"]:
        if run["run_id"] in run_ids:
            raise ValueError(f"duplicate run ID: {run['run_id']}")
        run_ids.add(run["run_id"])
        if run["runtime_epoch"] != RUNTIME_EPOCH:
            raise ValueError(f"runtime epoch drift in {run['run_id']}")
        if run["workload_id"] in workloads:
            runs_by_workload[run["workload_id"]].append(run)

    for workload_id in WORKLOAD_IDS:
        workload = workloads[workload_id]
        plan = manifest[workload_id]
        require_equal(f"{workload_id} query_id", workload["query_id"], plan["query_id"])
        require_equal(
            f"{workload_id} query_length_nt",
            workload["query_length_nt"], plan["query_length_nt"],
        )
        require_equal(
            f"{workload_id} fragment_position",
            workload["fragment_position"], plan["fragment_position"],
        )
        require_equal(f"{workload_id} target_id", workload["target_id"], plan["target_id"])
        require_equal(
            f"{workload_id} target_region", workload["target_region"], plan["target_region"]
        )
        require_equal(f"{workload_id} preset_id", workload["preset_id"], plan["preset_id"])
        require_equal(
            f"{workload_id} output_contract",
            workload["output_contract"], plan["output_contract"],
        )
        repeat_count = as_int(workload, "valid_pairs")
        if repeat_count != as_int(plan, "required_pairs"):
            raise ValueError(f"repeat count drift in {workload_id}")
        pairs = sorted(pairs_by_workload[workload_id], key=lambda row: as_int(row, "pair_id"))
        if [as_int(row, "pair_id") for row in pairs] != list(range(1, repeat_count + 1)):
            raise ValueError(f"pair sequence drift in {workload_id}")
        expected_runs = 2 * repeat_count + 2
        runs = runs_by_workload[workload_id]
        if len(runs) != expected_runs or any(row["status"] != "complete" for row in runs):
            raise ValueError(f"run count/status drift in {workload_id}")
        timed = [row for row in runs if row["warmup"] == "0"]
        warmups = [row for row in runs if row["warmup"] == "1"]
        if len(timed) != 2 * repeat_count or len(warmups) != 2:
            raise ValueError(f"warmup/timed run drift in {workload_id}")
        if {(row["pair_id"], row["mode"]) for row in timed} != {
            (str(pair_id), mode)
            for pair_id in range(1, repeat_count + 1)
            for mode in ("baseline", "candidate")
        }:
            raise ValueError(f"timed run join drift in {workload_id}")
        for pair in pairs:
            for field in (
                "role", "query_id", "query_length_nt", "fragment_position", "target_id",
                "target_region", "preset_id", "output_contract",
            ):
                require_equal(f"{pair['pair_id_text']} {field}", workload[field], pair[field])

    artifact_manifest = unique_by(
        sources["artifact_manifest"], "artifact_path", "artifact path"
    )
    return {
        "workloads": workloads,
        "manifest": manifest,
        "pairs_by_workload": pairs_by_workload,
        "runs_by_workload": runs_by_workload,
        "artifact_manifest": artifact_manifest,
    }


def _validate_artifact(
    archive_root: Path,
    artifact_manifest: dict[str, dict[str, str]],
    relative: str,
) -> Path:
    if relative not in artifact_manifest:
        raise ValueError(f"artifact absent from frozen manifest: {relative}")
    path = archive_root / relative
    manifest_row = artifact_manifest[relative]
    validate_sha256(path, manifest_row["sha256"])
    if path.stat().st_size != int(manifest_row["size_bytes"]):
        raise ValueError(f"artifact size drift for {relative}")
    return path


def _one_artifact_path(
    artifact_manifest: dict[str, dict[str, str]], prefix: str, suffix: str
) -> str:
    matches = sorted(
        path for path in artifact_manifest if path.startswith(prefix) and path.endswith(suffix)
    )
    if len(matches) != 1:
        raise ValueError(
            f"expected one artifact matching {prefix}*{suffix}, observed {matches}"
        )
    return matches[0]


def _mismatch_signatures(
    mismatch_rows: list[dict[str, str]],
    pairs_by_workload: dict[str, list[dict[str, str]]],
) -> dict[tuple[str, str], dict[str, object]]:
    expected_workloads = {workload for workload, _ in EXPECTED_MISMATCH_POSITIONS}
    observed_workloads = {row["workload_id"] for row in mismatch_rows}
    if observed_workloads != expected_workloads:
        raise ValueError(f"mismatch workload set drift: {sorted(observed_workloads)}")

    groups: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in mismatch_rows:
        if row["pair_status"] != "mismatch":
            raise ValueError(f"non-mismatch row in mismatch evidence: {row['pair_id_text']}")
        if row["side"] not in {"baseline", "candidate"}:
            raise ValueError(f"unknown mismatch side: {row['side']}")
        if row["kind"] not in {"raw", "clustered"} or row["mode"] not in RANKS:
            raise ValueError(f"unknown mismatch detail kind/mode: {row}")
        groups[(row["workload_id"], row["pair_id_text"], row["kind"], row["mode"], row["side"])].append(row)

    result: dict[tuple[str, str], dict[str, object]] = {}
    for workload_id in sorted(expected_workloads):
        pairs = sorted(pairs_by_workload[workload_id], key=lambda row: as_int(row, "pair_id"))
        if any(row["status"] != "mismatch" for row in pairs):
            raise ValueError(f"mismatch status drift in {workload_id}")
        for pair in pairs:
            for kind in ("raw", "clustered"):
                for rank in RANKS:
                    for side in ("baseline", "candidate"):
                        key = (workload_id, pair["pair_id_text"], kind, rank, side)
                        rows = sorted(groups.get(key, []), key=lambda row: as_int(row, "rank"))
                        if [as_int(row, "rank") for row in rows] != [1, 2, 3, 4, 5]:
                            raise ValueError(f"mismatch top-five row drift for {key}")

        for rank in RANKS:
            pair_signatures: list[
                tuple[
                    tuple[tuple[str, ...], ...],
                    tuple[tuple[str, ...], ...],
                ]
            ] = []
            pair_positions: list[tuple[int, ...]] = []
            first_baseline: list[dict[str, str]] | None = None
            first_candidate: list[dict[str, str]] | None = None
            for pair in pairs:
                baseline = sorted(
                    groups[(workload_id, pair["pair_id_text"], "clustered", rank, "baseline")],
                    key=lambda row: as_int(row, "rank"),
                )
                candidate = sorted(
                    groups[(workload_id, pair["pair_id_text"], "clustered", rank, "candidate")],
                    key=lambda row: as_int(row, "rank"),
                )
                baseline_keys = tuple(row_full_key(row) for row in baseline)
                candidate_keys = tuple(row_full_key(row) for row in candidate)
                positions = tuple(
                    index
                    for index, (baseline_key, candidate_key) in enumerate(
                        zip(baseline_keys, candidate_keys), start=1
                    )
                    if baseline_key != candidate_key
                )
                pair_signatures.append((baseline_keys, candidate_keys))
                pair_positions.append(positions)
                if first_baseline is None:
                    first_baseline = baseline
                    first_candidate = candidate
            if len(set(pair_signatures)) != 1 or len(set(pair_positions)) != 1:
                raise ValueError(f"repeat mismatch signature drift for {workload_id}/{rank}")
            positions = pair_positions[0]
            expected = EXPECTED_MISMATCH_POSITIONS.get((workload_id, rank), ())
            if positions != expected:
                raise ValueError(
                    f"mismatch position drift for {workload_id}/{rank}: "
                    f"expected {expected}, observed {positions}"
                )
            result[(workload_id, rank)] = {
                "positions": positions,
                "consistent": True,
                "baseline": first_baseline,
                "candidate": first_candidate,
            }
    return result


def _analyze_artifacts(
    repo_root: Path,
    joined: dict[str, object],
    mismatch_signatures: dict[tuple[str, str], dict[str, object]],
) -> dict[str, dict[str, object]]:
    archive_root = repo_root / ".paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization"
    artifacts = joined["artifact_manifest"]
    assert isinstance(artifacts, dict)
    analyze = _load_comparator(repo_root)
    manifest = joined["manifest"]
    pairs_by_workload = joined["pairs_by_workload"]
    assert isinstance(manifest, dict)
    assert isinstance(pairs_by_workload, dict)
    result: dict[str, dict[str, object]] = {}

    for workload_id in WORKLOAD_IDS:
        pairs = sorted(
            pairs_by_workload[workload_id], key=lambda row: as_int(row, "pair_id")
        )
        pair_prefix = f"{workload_id}__pair01__"
        query_relative = _one_artifact_path(
            artifacts, f"{pair_prefix}baseline__0/inputs/", "query.fa"
        )
        query_path = _validate_artifact(archive_root, artifacts, query_relative)
        sequence = load_fasta_sequence(query_path)
        plan = manifest[workload_id]
        if len(sequence) != as_int(plan, "query_length_nt"):
            raise ValueError(f"query length drift in raw artifact for {workload_id}")

        output_shas: dict[str, set[str]] = {
            "baseline": set(),
            "candidate": set(),
        }
        pair_analyses: list[dict[str, object]] = []
        for pair in pairs:
            analyses: dict[str, object] = {}
            for side in ("baseline", "candidate"):
                prefix = (
                    f"{workload_id}__pair{as_int(pair, 'pair_id'):02d}__"
                    f"{side}__0/output/"
                )
                relative = _one_artifact_path(artifacts, prefix, "-TFOsorted")
                path = _validate_artifact(archive_root, artifacts, relative)
                output_shas[side].add(artifacts[relative]["sha256"])
                analyses[side] = analyze(path, 6, 15, 50)
            pair_analyses.append({"pair": pair, **analyses})

        rank_details: dict[str, dict[str, object]] = {}
        for rank in RANKS:
            rows_by_side: dict[str, list[list[dict[str, str]]]] = {
                "baseline": [],
                "candidate": [],
            }
            for pair_analysis in pair_analyses:
                pair = pair_analysis["pair"]
                assert isinstance(pair, dict)
                for side in ("baseline", "candidate"):
                    analysis = pair_analysis[side]
                    rows = [row for _, row in analysis.clustered_top_rows[rank]]
                    if len(rows) < 6:
                        raise ValueError(
                            f"fewer than six clustered representatives for "
                            f"{pair['pair_id_text']}/{side}/{rank}"
                        )
                    rows_by_side[side].append(rows)
                observed_equal = int(
                    tuple(row_full_key(row) for row in rows_by_side["baseline"][-1][:5])
                    == tuple(row_full_key(row) for row in rows_by_side["candidate"][-1][:5])
                )
                expected_equal = as_int(pair, f"clustered_{rank}_top5_equal")
                if observed_equal != expected_equal:
                    raise ValueError(
                        f"recomputed contract drift for {pair['pair_id_text']}/{rank}: "
                        f"expected {expected_equal}, observed {observed_equal}"
                    )

            if (workload_id, rank) in mismatch_signatures:
                frozen = mismatch_signatures[(workload_id, rank)]
                frozen_baseline = frozen["baseline"]
                frozen_candidate = frozen["candidate"]
                assert isinstance(frozen_baseline, list)
                assert isinstance(frozen_candidate, list)
                for pair_index in range(len(pairs)):
                    if [
                        row_full_key(row)
                        for row in rows_by_side["baseline"][pair_index][:5]
                    ] != [row_full_key(row) for row in frozen_baseline]:
                        raise ValueError(
                            f"baseline raw/source top-five drift for "
                            f"{pairs[pair_index]['pair_id_text']}/{rank}"
                        )
                    if [
                        row_full_key(row)
                        for row in rows_by_side["candidate"][pair_index][:5]
                    ] != [row_full_key(row) for row in frozen_candidate]:
                        raise ValueError(
                            f"candidate raw/source top-five drift for "
                            f"{pairs[pair_index]['pair_id_text']}/{rank}"
                        )
                identity_source = "frozen_mismatch_source_table_validated_against_raw_archive"
            else:
                identity_source = "checksum_verified_pair01_raw_archive"

            representative_baseline = rows_by_side["baseline"][0]
            representative_candidate = rows_by_side["candidate"][0]
            if len(pairs) == 1:
                baseline_repeat_consistent: int | None = None
                candidate_repeat_consistent: int | None = None
                repeat_consistent: int | None = None
                repeat_availability = "single_frozen_pair_no_multi_repeat_test"
            else:
                baseline_repeat_consistent = repeat_top5_signature_consistent(
                    rows_by_side["baseline"]
                )
                candidate_repeat_consistent = repeat_top5_signature_consistent(
                    rows_by_side["candidate"]
                )
                repeat_consistent = int(
                    baseline_repeat_consistent == 1
                    and candidate_repeat_consistent == 1
                )
                repeat_availability = "all_frozen_pair_outputs_compared"

            baseline_margin = float(primary_value(representative_baseline[4], rank)) - float(
                primary_value(representative_baseline[5], rank)
            )
            candidate_margin = float(primary_value(representative_candidate[4], rank)) - float(
                primary_value(representative_candidate[5], rank)
            )
            rank_details[rank] = {
                "baseline_rows": representative_baseline[:5],
                "candidate_rows": representative_candidate[:5],
                "baseline_margin": format_margin(baseline_margin),
                "candidate_margin": format_margin(candidate_margin),
                "baseline_tied": int(baseline_margin == 0.0),
                "candidate_tied": int(candidate_margin == 0.0),
                "baseline_repeat_top5_signature_consistent": baseline_repeat_consistent,
                "candidate_repeat_top5_signature_consistent": candidate_repeat_consistent,
                "repeat_top5_signature_consistent": repeat_consistent,
                "repeat_top5_signature_availability_reason": repeat_availability,
                "identity_source": identity_source,
            }

        output_sha_consistent = {
            side: len(output_shas[side]) == 1 for side in ("baseline", "candidate")
        }
        representative_baseline = pair_analyses[0]["baseline"]
        representative_candidate = pair_analyses[0]["candidate"]
        if len(pairs) == 1:
            workload_baseline_repeat: int | None = None
            workload_candidate_repeat: int | None = None
            workload_repeat: int | None = None
            workload_repeat_availability = "single_frozen_pair_no_multi_repeat_test"
        else:
            workload_baseline_repeat = int(
                all(
                    rank_details[rank]["baseline_repeat_top5_signature_consistent"] == 1
                    for rank in RANKS
                )
            )
            workload_candidate_repeat = int(
                all(
                    rank_details[rank]["candidate_repeat_top5_signature_consistent"] == 1
                    for rank in RANKS
                )
            )
            workload_repeat = int(
                workload_baseline_repeat == 1 and workload_candidate_repeat == 1
            )
            workload_repeat_availability = "all_frozen_pair_outputs_compared_all_ranks"
        result[workload_id] = {
            "sequence": sequence,
            "normalized_sha256": hashlib.sha256(sequence.encode("ascii")).hexdigest(),
            "baseline_rows": len(representative_baseline.rows),
            "candidate_rows": len(representative_candidate.rows),
            "baseline_output_digest_repeat_consistent": int(
                output_sha_consistent["baseline"]
            ),
            "candidate_output_digest_repeat_consistent": int(
                output_sha_consistent["candidate"]
            ),
            "output_digest_repeat_consistent": int(all(output_sha_consistent.values())),
            "baseline_repeat_top5_signature_consistent": workload_baseline_repeat,
            "candidate_repeat_top5_signature_consistent": workload_candidate_repeat,
            "repeat_top5_signature_consistent": workload_repeat,
            "repeat_top5_signature_availability_reason": workload_repeat_availability,
            "rank_details": rank_details,
        }
    return result


def _repeat_basis(
    repeat_count: int,
    mismatch: bool,
    output_digest_consistent: bool,
    top5_signature_consistent: int | None,
) -> str:
    if repeat_count == 1:
        return "single_frozen_pair_no_multi_repeat_test"
    if mismatch:
        if top5_signature_consistent == 1:
            return "three_identical_frozen_top5_signatures"
        return "three_frozen_pairs_with_varying_top5_signatures"
    if output_digest_consistent:
        return "three_frozen_pairs_with_identical_contract_flags_and_output_digests"
    return (
        "three_frozen_pairs_with_identical_contract_flags_but_varying_"
        "full_output_digests"
    )


def _build_contract_rows(
    joined: dict[str, object], artifacts: dict[str, dict[str, object]]
) -> list[dict[str, str]]:
    workloads = joined["workloads"]
    manifest = joined["manifest"]
    pairs_by_workload = joined["pairs_by_workload"]
    runs_by_workload = joined["runs_by_workload"]
    assert isinstance(workloads, dict) and isinstance(manifest, dict)
    assert isinstance(pairs_by_workload, dict) and isinstance(runs_by_workload, dict)
    rows: list[dict[str, str]] = []
    for workload_id in WORKLOAD_IDS:
        workload = workloads[workload_id]
        plan = manifest[workload_id]
        pairs = pairs_by_workload[workload_id]
        sequence = artifacts[workload_id]["sequence"]
        assert isinstance(sequence, str)
        repeat_count = len(pairs)
        mismatch = workload["status"] == "mismatch"
        output_digest_consistent = bool(
            artifacts[workload_id]["output_digest_repeat_consistent"]
        )
        top5_signature_consistent = artifacts[workload_id][
            "repeat_top5_signature_consistent"
        ]
        assert top5_signature_consistent is None or isinstance(
            top5_signature_consistent, int
        )
        row: dict[str, str] = {
            "source_freeze_id": FREEZE_ID,
            "runtime_epoch": RUNTIME_EPOCH,
            "runtime_commit": RUNTIME_COMMIT,
            "workload_id": workload_id,
            "role": workload["role"],
            "query_id": workload["query_id"],
            "query_length_nt": workload["query_length_nt"],
            "fragment_position": workload["fragment_position"],
            "query_start_nt": plan["query_start_nt"],
            "query_end_nt": plan["query_end_nt"],
            "query_a_count": str(sequence.count("A")),
            "query_c_count": str(sequence.count("C")),
            "query_g_count": str(sequence.count("G")),
            "query_t_count": str(sequence.count("T")),
            "query_normalized_sha256": str(artifacts[workload_id]["normalized_sha256"]),
            "target_id": workload["target_id"],
            "target_region": workload["target_region"],
            "preset_id": workload["preset_id"],
            "output_contract": workload["output_contract"],
            "frozen_status": workload["status"],
            "repeat_count": str(repeat_count),
            "repeat_contract_status_consistent": workload["repeat_consistent"],
            "baseline_repeat_top5_signature_consistent": availability_value(
                artifacts[workload_id]["baseline_repeat_top5_signature_consistent"]
            ),
            "candidate_repeat_top5_signature_consistent": availability_value(
                artifacts[workload_id]["candidate_repeat_top5_signature_consistent"]
            ),
            "repeat_top5_signature_consistent": availability_value(
                top5_signature_consistent
            ),
            "repeat_top5_signature_availability_reason": str(
                artifacts[workload_id]["repeat_top5_signature_availability_reason"]
            ),
            "repeat_consistency_basis": _repeat_basis(
                repeat_count,
                mismatch,
                output_digest_consistent,
                top5_signature_consistent,
            ),
            "all_ranked_clean": str(int(all(workload[f"clustered_{rank}_all_equal"] == "1" for rank in RANKS))),
            "all_ranked_clean_pairs": str(sum(as_int(pair, "all_three_top5_equal") for pair in pairs)),
            "all_ranked_mismatch_pairs": str(sum(1 - as_int(pair, "all_three_top5_equal") for pair in pairs)),
            "raw_score_clean": workload["raw_score_all_equal"],
            "raw_stability_clean": workload["raw_stability_all_equal"],
            "raw_nt_clean": workload["raw_nt_all_equal"],
            "full_row_equal": str(int(all(as_int(pair, "full_missing_rows") == 0 and as_int(pair, "full_extra_rows") == 0 for pair in pairs))),
            "full_missing_rows_total": workload["full_missing_rows_total"],
            "full_extra_rows_total": workload["full_extra_rows_total"],
            "comparator_boundary_ties_all_equal": workload["boundary_ties_all_equal"],
            "baseline_comparator_tie_groups_total": str(sum(as_int(pair, "baseline_boundary_tie_groups") for pair in pairs)),
            "candidate_comparator_tie_groups_total": str(sum(as_int(pair, "candidate_boundary_tie_groups") for pair in pairs)),
            "candidate_active_path_all_pairs": str(int(all(as_int(pair, "candidate_active_path") == 1 for pair in pairs))),
            "fallbacks_total": workload["fallbacks_total"],
            "length_guard_fallbacks_total": str(sum(as_int(pair, "length_guard_fallbacks") for pair in pairs)),
            "runtime_batch_fallbacks_total": str(sum(as_int(pair, "runtime_batch_fallbacks") for pair in pairs)),
            "overflow_fallbacks_total": str(sum(as_int(pair, "overflow_fallbacks") for pair in pairs)),
            "allocation_state": "NA",
            "allocation_state_availability_reason": "not_recorded_in_frozen_development_evidence",
            "oom_total": workload["oom_total"],
            "baseline_output_rows": str(artifacts[workload_id]["baseline_rows"]),
            "candidate_output_rows": str(artifacts[workload_id]["candidate_rows"]),
            "output_rows_pair": "pair01",
            "baseline_output_digest_repeat_consistent": str(
                artifacts[workload_id]["baseline_output_digest_repeat_consistent"]
            ),
            "candidate_output_digest_repeat_consistent": str(
                artifacts[workload_id]["candidate_output_digest_repeat_consistent"]
            ),
            "output_digest_repeat_consistent": str(artifacts[workload_id]["output_digest_repeat_consistent"]),
            "runtime_telemetry_available": "1",
            "runtime_telemetry_availability_reason": "frozen_runs_and_pair_telemetry_present",
            "runtime_run_count": str(len(runs_by_workload[workload_id])),
            "gasal2_requests_total": workload["gasal2_requests_total"],
            "traceback_requests_total": workload["traceback_requests_total"],
            "baseline_rss_peak_kb": workload["baseline_rss_peak_kb"],
            "candidate_rss_peak_kb": workload["candidate_rss_peak_kb"],
            "baseline_gpu_memory_peak_mib": workload["baseline_gpu_memory_peak_mib"],
            "candidate_gpu_memory_peak_mib": workload["candidate_gpu_memory_peak_mib"],
        }
        for rank in RANKS:
            clean_pairs = sum(as_int(pair, f"clustered_{rank}_top5_equal") for pair in pairs)
            row[f"{rank}_clean"] = workload[f"clustered_{rank}_all_equal"]
            row[f"{rank}_mismatch"] = str(1 - as_int(workload, f"clustered_{rank}_all_equal"))
            row[f"{rank}_clean_pairs"] = str(clean_pairs)
            row[f"{rank}_mismatch_pairs"] = str(repeat_count - clean_pairs)
        rows.append({field: row[field] for field in CONTRACT_FIELDS})
    return rows


def _build_feature_rows(
    joined: dict[str, object],
    artifacts: dict[str, dict[str, object]],
    mismatch_signatures: dict[tuple[str, str], dict[str, object]],
) -> list[dict[str, str]]:
    workloads = joined["workloads"]
    pairs_by_workload = joined["pairs_by_workload"]
    assert isinstance(workloads, dict) and isinstance(pairs_by_workload, dict)
    rows: list[dict[str, str]] = []
    for workload_id in WORKLOAD_IDS:
        workload = workloads[workload_id]
        pairs = sorted(pairs_by_workload[workload_id], key=lambda item: as_int(item, "pair_id"))
        representative = pairs[0]
        sequence = artifacts[workload_id]["sequence"]
        assert isinstance(sequence, str)
        rank_details = artifacts[workload_id]["rank_details"]
        assert isinstance(rank_details, dict)
        for rank in RANKS:
            details = rank_details[rank]
            baseline_rows = details["baseline_rows"]
            candidate_rows = details["candidate_rows"]
            assert isinstance(baseline_rows, list) and isinstance(candidate_rows, list)
            positions = tuple(
                mismatch_signatures.get((workload_id, rank), {}).get("positions", ())
            )
            repeat_count = len(pairs)
            rank_equal = workload[f"clustered_{rank}_all_equal"]
            output_digest_consistent = bool(
                artifacts[workload_id]["output_digest_repeat_consistent"]
            )
            rank_repeat_consistent = details["repeat_top5_signature_consistent"]
            assert rank_repeat_consistent is None or isinstance(
                rank_repeat_consistent, int
            )
            mismatch_pair_count = sum(
                1 - as_int(pair, f"clustered_{rank}_top5_equal") for pair in pairs
            )
            if bool(positions) != (rank_equal == "0"):
                raise ValueError(f"rank equality/detail drift for {workload_id}/{rank}")
            if mismatch_pair_count not in {0, repeat_count}:
                raise ValueError(f"inconsistent per-pair rank result for {workload_id}/{rank}")
            row = {
                "source_freeze_id": FREEZE_ID,
                "runtime_epoch": RUNTIME_EPOCH,
                "runtime_commit": RUNTIME_COMMIT,
                "workload_id": workload_id,
                "query_id": workload["query_id"],
                "query_length_nt": workload["query_length_nt"],
                "fragment_position": workload["fragment_position"],
                "query_a_count": str(sequence.count("A")),
                "query_c_count": str(sequence.count("C")),
                "query_g_count": str(sequence.count("G")),
                "query_t_count": str(sequence.count("T")),
                "query_normalized_sha256": str(artifacts[workload_id]["normalized_sha256"]),
                "target_id": workload["target_id"],
                "target_region": workload["target_region"],
                "rank": rank,
                "rank_equal": rank_equal,
                "mismatch_pair_count": str(mismatch_pair_count),
                "differing_position_count": str(len(positions)),
                "differing_positions": ",".join(map(str, positions)) if positions else "none",
                "top5_details_available": "1",
                "top5_details_availability_reason": str(details["identity_source"]),
                "baseline_top5_identities": compact_ranked([row_identity(item) for item in baseline_rows]),
                "candidate_top5_identities": compact_ranked([row_identity(item) for item in candidate_rows]),
                "baseline_primary_values": compact_ranked([primary_value(item, rank) for item in baseline_rows]),
                "candidate_primary_values": compact_ranked([primary_value(item, rank) for item in candidate_rows]),
                "comparator_boundary_ties_equal": representative["boundary_ties_equal"],
                "baseline_comparator_tie_groups_all_ranks": representative["baseline_boundary_tie_groups"],
                "candidate_comparator_tie_groups_all_ranks": representative["candidate_boundary_tie_groups"],
                "baseline_rank5_rank6_primary_margin": str(details["baseline_margin"]),
                "candidate_rank5_rank6_primary_margin": str(details["candidate_margin"]),
                "baseline_rank5_rank6_primary_equal": str(details["baseline_tied"]),
                "candidate_rank5_rank6_primary_equal": str(details["candidate_tied"]),
                "primary_margin_availability_reason": "recomputed_with_frozen_comparator_semantics_from_checksum_verified_pair01_outputs",
                "baseline_output_rows": str(artifacts[workload_id]["baseline_rows"]),
                "candidate_output_rows": str(artifacts[workload_id]["candidate_rows"]),
                "full_missing_rows": representative["full_missing_rows"],
                "full_extra_rows": representative["full_extra_rows"],
                "candidate_active_path": representative["candidate_active_path"],
                "fallbacks": representative["fallbacks"],
                "length_guard_fallbacks": representative["length_guard_fallbacks"],
                "runtime_batch_fallbacks": representative["runtime_batch_fallbacks"],
                "overflow_fallbacks": representative["overflow_fallbacks"],
                "allocation_state": "NA",
                "allocation_state_availability_reason": "not_recorded_in_frozen_development_evidence",
                "oom": representative["oom"],
                "runtime_telemetry_available": "1",
                "runtime_telemetry_availability_reason": "frozen_pair_runtime_and_resource_telemetry_present",
                "gasal2_requests": representative["gasal2_requests"],
                "traceback_requests": representative["traceback_requests"],
                "repeat_count": str(repeat_count),
                "repeat_contract_status_consistent": workload["repeat_consistent"],
                "baseline_repeat_top5_signature_consistent": availability_value(
                    details["baseline_repeat_top5_signature_consistent"]
                ),
                "candidate_repeat_top5_signature_consistent": availability_value(
                    details["candidate_repeat_top5_signature_consistent"]
                ),
                "repeat_top5_signature_consistent": availability_value(
                    rank_repeat_consistent
                ),
                "repeat_top5_signature_availability_reason": str(
                    details["repeat_top5_signature_availability_reason"]
                ),
                "repeat_consistency_basis": _repeat_basis(
                    repeat_count,
                    rank_equal == "0",
                    output_digest_consistent,
                    rank_repeat_consistent,
                ),
                "evidence_pair_id": representative["pair_id_text"],
            }
            rows.append({field: row[field] for field in FEATURE_FIELDS})
    return rows


def _render_report(
    contract_rows: list[dict[str, str]], feature_rows: list[dict[str, str]]
) -> str:
    clean = {
        rank: sum(int(row[f"{rank}_clean"]) for row in contract_rows) for rank in RANKS
    }
    all_clean = sum(int(row["all_ranked_clean"]) for row in contract_rows)
    full_equal = sum(int(row["full_row_equal"]) for row in contract_rows)
    fallback_total = sum(int(row["fallbacks_total"]) for row in contract_rows)
    overflow_total = sum(int(row["overflow_fallbacks_total"]) for row in contract_rows)
    oom_total = sum(int(row["oom_total"]) for row in contract_rows)
    varying_output_digests = [
        row
        for row in contract_rows
        if row["repeat_count"] != "1" and row["output_digest_repeat_consistent"] == "0"
    ]
    repeated_contracts = [row for row in contract_rows if row["repeat_count"] != "1"]
    baseline_signature_clean = sum(
        row["baseline_repeat_top5_signature_consistent"] == "1"
        for row in repeated_contracts
    )
    candidate_signature_clean = sum(
        row["candidate_repeat_top5_signature_consistent"] == "1"
        for row in repeated_contracts
    )
    combined_signature_clean = sum(
        row["repeat_top5_signature_consistent"] == "1"
        for row in repeated_contracts
    )
    signature_variations = [
        row["workload_id"]
        for row in repeated_contracts
        if row["repeat_top5_signature_consistent"] != "1"
    ]
    signature_variation_text = (
        "none"
        if not signature_variations
        else ", ".join(f"`{workload_id}`" for workload_id in signature_variations)
    )
    mismatch_lines = []
    for row in feature_rows:
        if row["rank_equal"] == "0":
            mismatch_lines.append(
                f"- `{row['workload_id']}` / `{row['rank']}` differs at clustered "
                f"TFO positions `{row['differing_positions']}`; {row['repeat_count']} frozen "
                f"pair(s), consistency basis `{row['repeat_consistency_basis']}`."
            )
    return f"""# Frozen Development-Contract Mismatch Analysis

## Scope and provenance

This report is a deterministic decomposition of the immutable `{FREEZE_ID}` development evidence. It reads `paper/source_data/generalization_workloads_pre_freeze.tsv`, `paper/source_data/generalization_pairs_pre_freeze.tsv`, `paper/source_data/generalization_runs_pre_freeze.tsv`, `paper/source_data/generalization_mismatch_top5_pre_freeze.tsv`, `paper/workload_manifest.tsv`, and `paper/source_data/source_data_manifest.tsv`. Query composition, pair-01 output row counts and primary margins, and all-pair clustered top-five signatures are reconstructed only from files checked against `.paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization/phase3-artifacts.tsv` (manifest SHA-256 `{ARTIFACT_MANIFEST_SHA256}`). The established comparator uses cluster distance 15, minimum length 50, and its frozen score/stability/Nt ordering.

## Contract results

- **Score gate:** {clean['score']}/13 score-ranked workloads are clean. The score contract is unaffected by all three preserved mismatches in this development panel.
- **Stability gate:** {clean['stability']}/13 stability-ranked workloads are clean. The mismatches are g02 and g12.
- **Nt gate:** {clean['nt']}/13 Nt-ranked workloads are clean. The mismatch is g09.
- **Joint ranked result:** {all_clean}/13 workloads are clean across all three ranked contracts.
- **Full output diagnostic:** {full_equal}/13 workloads have full-row equality. Full-row equality fails for 13/13 workloads; this diagnostic is separate from the declared top-five contracts and no missing/extra row is removed.
- **Runtime outcomes:** fallbacks={fallback_total}, overflow fallbacks={overflow_total}, OOM={oom_total}. Allocation state is `NA` because no allocation-state certificate was recorded in the frozen development evidence.
- **Repeat diagnostic:** {"; ".join(f"{row['workload_id'][:3]} candidate full-output digests vary across its three frozen pairs while ranked contract flags remain consistent" for row in varying_output_digests)}.
- **Top-five repeat signatures:** baseline stable in {baseline_signature_clean}/{len(repeated_contracts)} three-pair workloads, candidate stable in {candidate_signature_clean}/{len(repeated_contracts)}, and both sides stable in {combined_signature_clean}/{len(repeated_contracts)}. Observed repeat-signature variation: {signature_variation_text}.

g05 has stable baseline and candidate clustered top-five signatures across three pairs despite varying candidate full-output digests. g12 has one frozen pair, so multi-repeat top-five signature consistency is `NA`. The historical repeat contract-status field is retained separately and is not used as a top-five signature result.

## Preserved mismatch positions

The positions below compare full TFO row identities at clustered ranks 1 through 5. A compact identity is the first 16 hexadecimal characters of SHA-256 over the canonical tab-joined TFOsorted row. Mismatch identities are derived from `paper/source_data/generalization_mismatch_top5_pre_freeze.tsv`, and the pair-01 identities are cross-checked against the checksum-verified raw archive.

{chr(10).join(mismatch_lines)}

For g02 and g09, all three frozen pairs have identical baseline/candidate top-five signatures and identical differing positions, so the observed mismatches are repeat-consistent. G12 has one frozen pair: its signature is internally consistent, but it is explicitly not a multi-repeat demonstration. Comparator tie groups are aggregate diagnostics across all three ranking modes. Comparator ties require equality of the complete score/stability/Nt ranking tuple. The per-rank rank-5/rank-6 fields report only the primary-value margin. A zero primary margin means only that rank 5 and rank 6 have equal primary values. It does not establish a comparator tuple tie or a mechanism.

## Mechanism and guard conclusion

No deterministic, query-independent pre-run or runtime mechanism certificate is established by the frozen telemetry. Query length/composition, boundary margins, output counts, resource telemetry, and repeat behavior are descriptive features of 13 development workloads; they are not mechanism evidence and are not a safety guard. The frozen evidence records no allocation-state certificate, and the observed zero fallback/overflow/OOM totals do not explain the rank-specific substitutions.

No query-name, gene-ID, or sequence-digest allowlist is proposed. This analysis neither promotes a contract nor changes CLI behavior. Promotion, if any, requires the separately preregistered independent holdout and the Phase 2 decision gate.
"""


def generate(repo_root: Path, output_dir: Path) -> dict[str, str]:
    repo_root = repo_root.resolve()
    sources = _validate_sources(repo_root)
    joined = _validate_joins(sources)
    pairs_by_workload = joined["pairs_by_workload"]
    assert isinstance(pairs_by_workload, dict)
    mismatch_signatures = _mismatch_signatures(sources["mismatches"], pairs_by_workload)
    raw_artifacts = _analyze_artifacts(repo_root, joined, mismatch_signatures)
    contract_rows = _build_contract_rows(joined, raw_artifacts)
    feature_rows = _build_feature_rows(joined, raw_artifacts, mismatch_signatures)
    outputs = {
        "frozen_contract_matrix.tsv": render_tsv(CONTRACT_FIELDS, contract_rows),
        "mismatch_feature_matrix.tsv": render_tsv(FEATURE_FIELDS, feature_rows),
        "mismatch_analysis.md": _render_report(contract_rows, feature_rows),
    }
    publish_outputs_transactionally(output_dir, outputs)
    return outputs


def main() -> int:
    default_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Generate the Phase 2 frozen development-contract decomposition."
    )
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir or args.repo_root / "paper/bioinformatics"
    outputs = generate(args.repo_root, output_dir)
    for name in outputs:
        print(f"wrote={output_dir / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
