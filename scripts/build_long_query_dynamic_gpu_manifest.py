#!/usr/bin/env python3
"""Build a dynamic-pool manifest from canceled static GPU partitions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUTPUT_FIELDS = (
    "job_id",
    "original_rank",
    "gene_id",
    "gene_symbol",
    "listing_gene_symbol",
    "query_length_nt",
    "estimated_seconds",
    "query_path",
    "query_file_sha256",
    "query_sequence_sha256",
    "source_output_dir",
)
REQUIRED_INPUT_FIELDS = tuple(field for field in OUTPUT_FIELDS if field not in {"job_id", "source_output_dir"}) + ("output_dir",)


class ManifestError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ManifestError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def read_manifest(path: Path) -> list[dict[str, str]]:
    require(path.is_file() and not path.is_symlink(), f"unsafe manifest: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = tuple(reader.fieldnames or ())
        for required in REQUIRED_INPUT_FIELDS:
            require(required in fields, f"manifest {path} lacks {required}")
        rows = list(reader)
    require(rows, f"manifest is empty: {path}")
    return rows


def fasta_sequence(path: Path) -> str:
    pieces: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(">"):
                continue
            pieces.append("".join(line.split()).upper())
    sequence = "".join(pieces)
    require(bool(sequence), f"query sequence is empty: {path}")
    try:
        sequence.encode("ascii")
    except UnicodeEncodeError as error:
        raise ManifestError(f"query sequence is not ASCII: {path}") from error
    return sequence


def validate_sha256(value: str, label: str) -> None:
    require(
        len(value) == 64 and value == value.lower() and all(character in "0123456789abcdef" for character in value),
        f"invalid SHA-256 for {label}",
    )


def validate_source_row(row: dict[str, str], manifest: Path) -> None:
    gene_id = row["gene_id"]
    require(bool(gene_id), f"empty gene_id in {manifest}")
    for field in REQUIRED_INPUT_FIELDS:
        value = row[field]
        require("\t" not in value and "\n" not in value and "\r" not in value, f"unsafe {field} for {gene_id}")

    require(int(row["original_rank"]) > 0, f"invalid original rank for {gene_id}")
    query_length = int(row["query_length_nt"])
    estimated_seconds = float(row["estimated_seconds"])
    require(query_length > 0, f"invalid query length for {gene_id}")
    require(math.isfinite(estimated_seconds) and estimated_seconds > 0.0, f"invalid estimate for {gene_id}")

    query = Path(row["query_path"])
    require(query.is_absolute(), f"query path is not absolute for {gene_id}: {query}")
    require(query.is_file() and not query.is_symlink(), f"unsafe query: {query}")
    validate_sha256(row["query_file_sha256"], f"{gene_id} query file")
    validate_sha256(row["query_sequence_sha256"], f"{gene_id} query sequence")
    require(sha256_file(query) == row["query_file_sha256"], f"query digest drift: {gene_id}")
    sequence = fasta_sequence(query)
    require(len(sequence) == query_length, f"query length drift: {gene_id}")
    require(
        hashlib.sha256(sequence.encode("ascii")).hexdigest() == row["query_sequence_sha256"],
        f"query sequence digest drift: {gene_id}",
    )

    output = Path(row["output_dir"])
    require(output.is_absolute(), f"output path is not absolute for {gene_id}: {output}")
    require(not output.is_symlink(), f"output path must not be a symlink for {gene_id}: {output}")


def read_key_value_tsv(path: Path) -> dict[str, str]:
    require(path.is_file() and not path.is_symlink(), f"unsafe receipt file: {path}")
    values: dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if len(row) < 2 or row[0] in {"field", ""}:
                continue
            require(row[0] not in values, f"duplicate field {row[0]} in {path}")
            values[row[0]] = row[1]
    return values


def validate_f1_runtime_contract(output: Path) -> dict[str, int]:
    stdout_path = output / "completed" / "stdout.log"
    stderr_path = output / "completed" / "stderr.log"
    report_path = output / "completed" / "f1.tsv"
    require(stdout_path.is_file() and not stdout_path.is_symlink(), f"completed stdout is missing: {output}")
    require(stderr_path.is_file() and not stderr_path.is_symlink(), f"completed stderr is missing: {output}")
    require(report_path.is_file() and not report_path.is_symlink(), f"completed F1 report is missing: {output}")
    require(
        "finished normally" in stdout_path.read_text(encoding="utf-8", errors="replace").splitlines(),
        f"completed stdout lacks success marker: {output}",
    )
    required_markers = {
        "benchmark.fasim_long_query_gpu_consumer_f1_pipeline_active=1",
        "benchmark.fasim_long_query_gpu_consumer_f1_pipeline_failures=0",
        "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fallback_batches=0",
        "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks=0",
        "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks=0",
        "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared_auto_fallbacks=0",
    }
    observed_markers = set(stderr_path.read_text(encoding="utf-8", errors="replace").splitlines())
    missing = sorted(required_markers - observed_markers)
    require(not missing, f"completed runtime markers missing for {output}: {missing}")

    rows = 0
    bad_rows = 0
    continuation_failures = 0
    with report_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = set(reader.fieldnames or ())
        require("ok" in fields and "cpu_continuation_failures" in fields, f"completed F1 report schema drift: {output}")
        for row in reader:
            rows += 1
            bad_rows += int(row["ok"] != "1")
            continuation_failures += int(row["cpu_continuation_failures"])
    require(rows > 0, f"completed F1 report is empty: {output}")
    require(bad_rows == 0, f"completed F1 report has failed rows: {output}")
    require(continuation_failures == 0, f"completed F1 report has continuation failures: {output}")
    return {
        "f1_rows": rows,
        "f1_bad_rows": bad_rows,
        "cpu_continuation_failures": continuation_failures,
    }


def validate_completed(
    row: dict[str, str],
    allowed_completed_binary_sha256: set[str],
    required_target_sha256: str,
) -> dict[str, Any] | None:
    output = Path(row["output_dir"])
    require(output.is_absolute(), f"completed output path is not absolute: {output}")
    require(not output.is_symlink(), f"completed output path is a symlink: {output}")
    status_path = output / "status.tsv"
    if not status_path.exists():
        return None
    status = read_key_value_tsv(status_path)
    if status.get("status") != "complete":
        return None

    summary = read_key_value_tsv(output / "summary.tsv")
    run_plan = read_key_value_tsv(output / "run-plan.tsv")
    require(summary.get("status") == "complete", f"completed summary status drift: {output}")
    require(summary.get("gene_id") == row["gene_id"], f"completed gene drift: {output}")
    require(run_plan.get("gene_id") == row["gene_id"], f"completed plan gene drift: {output}")
    require(run_plan.get("query_file_sha256") == row["query_file_sha256"], f"completed query-file digest drift: {output}")
    require(run_plan.get("query_sequence_sha256") == row["query_sequence_sha256"], f"completed query-sequence digest drift: {output}")
    completed_binary_sha256 = run_plan.get("binary_sha256", "")
    require(completed_binary_sha256 in allowed_completed_binary_sha256, f"completed binary digest is not allowed: {output}")
    require(run_plan.get("target_sha256") == required_target_sha256, f"completed target digest drift: {output}")

    raw_artifact = summary.get("artifact_path", "")
    require(bool(raw_artifact), f"completed artifact path missing: {output}")
    artifact = Path(raw_artifact)
    require(artifact.is_absolute(), f"completed artifact path is not absolute: {artifact}")
    artifact_resolved = artifact.resolve()
    output_resolved = output.resolve()
    require(output_resolved in artifact_resolved.parents, f"completed artifact escapes output: {artifact}")
    require(artifact.is_file() and not artifact.is_symlink(), f"completed artifact missing or unsafe: {artifact}")
    artifact_sha256 = sha256_file(artifact)
    require(artifact_sha256 == summary.get("artifact_sha256"), f"completed artifact digest drift: {artifact}")
    if summary.get("artifact_bytes"):
        require(artifact.stat().st_size == int(summary["artifact_bytes"]), f"completed artifact size drift: {artifact}")
    runtime_contract = validate_f1_runtime_contract(output)
    result = {
        "gene_id": row["gene_id"],
        "output_dir": str(output),
        "source_commit": run_plan.get("source_commit"),
        "binary_sha256": completed_binary_sha256,
        "artifact_path": str(artifact),
        "artifact_sha256": artifact_sha256,
        "wall_seconds": float(summary.get("wall_seconds") or 0.0),
    }
    result.update(runtime_contract)
    return result


def build_manifest(
    inputs: list[Path],
    reserved: list[Path],
    output: Path,
    receipt_path: Path,
    required_binary_sha256: str,
    allowed_completed_binary_sha256: set[str],
    required_target_sha256: str,
) -> dict[str, Any]:
    validate_sha256(required_binary_sha256, "required binary")
    validate_sha256(required_target_sha256, "required target")
    require(bool(allowed_completed_binary_sha256), "no allowed completed binaries")
    for digest in allowed_completed_binary_sha256:
        validate_sha256(digest, "allowed completed binary")
    require(output.resolve() != receipt_path.resolve(), "output manifest and receipt must differ")

    input_paths = [path.resolve() for path in inputs]
    reserved_paths = [path.resolve() for path in reserved]
    require(len(input_paths) == len(set(input_paths)), "duplicate input manifest path")
    require(len(reserved_paths) == len(set(reserved_paths)), "duplicate reserved manifest path")
    require(not set(input_paths) & set(reserved_paths), "manifest cannot be both input and reserved")

    reserved_ids: set[str] = set()
    reserved_receipts: list[dict[str, str]] = []
    for path in reserved:
        rows = read_manifest(path)
        for row in rows:
            validate_source_row(row, path)
            gene_id = row["gene_id"]
            require(gene_id not in reserved_ids, f"duplicate reserved gene: {gene_id}")
            reserved_ids.add(gene_id)
        reserved_receipts.append({"path": str(path), "sha256": sha256_file(path), "rows": str(len(rows))})

    source_receipts: list[dict[str, str]] = []
    rows_by_gene: dict[str, dict[str, str]] = {}
    for path in inputs:
        rows = read_manifest(path)
        for row in rows:
            validate_source_row(row, path)
            gene_id = row["gene_id"]
            require(gene_id not in reserved_ids, f"GPU/OpenMP ownership overlap: {gene_id}")
            require(gene_id not in rows_by_gene, f"duplicate GPU job: {gene_id}")
            rows_by_gene[gene_id] = row
        source_receipts.append({"path": str(path), "sha256": sha256_file(path), "rows": str(len(rows))})
    require(rows_by_gene, "no GPU jobs found")

    pending: list[dict[str, str]] = []
    completed: list[dict[str, Any]] = []
    for row in rows_by_gene.values():
        completion = validate_completed(
            row, allowed_completed_binary_sha256, required_target_sha256
        )
        if completion is not None:
            completed.append(completion)
            continue
        pending.append(
            {
                "job_id": row["gene_id"],
                "original_rank": row["original_rank"],
                "gene_id": row["gene_id"],
                "gene_symbol": row["gene_symbol"],
                "listing_gene_symbol": row["listing_gene_symbol"],
                "query_length_nt": row["query_length_nt"],
                "estimated_seconds": row["estimated_seconds"],
                "query_path": row["query_path"],
                "query_file_sha256": row["query_file_sha256"],
                "query_sequence_sha256": row["query_sequence_sha256"],
                "source_output_dir": row["output_dir"],
            }
        )
    pending.sort(key=lambda row: (int(row["original_rank"]), row["gene_id"]))
    require(pending, "all source GPU jobs are already complete")

    output_lines = ["\t".join(OUTPUT_FIELDS)]
    for row in pending:
        output_lines.append("\t".join(row[field] for field in OUTPUT_FIELDS))
    payload = ("\n".join(output_lines) + "\n").encode("utf-8")
    atomic_bytes(output, payload)
    receipt = {
        "schema_version": "long_query_dynamic_gpu_manifest_receipt_v1",
        "created_utc": utc_now(),
        "source_manifests": source_receipts,
        "reserved_manifests": reserved_receipts,
        "required_binary_sha256": required_binary_sha256,
        "allowed_completed_binary_sha256": sorted(allowed_completed_binary_sha256),
        "required_target_sha256": required_target_sha256,
        "source_gpu_jobs": len(rows_by_gene),
        "validated_completed_jobs": len(completed),
        "pending_jobs": len(pending),
        "output_manifest": str(output),
        "output_manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "completed": completed,
        "pending_gene_ids": [row["gene_id"] for row in pending],
    }
    atomic_bytes(receipt_path, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, action="append", required=True)
    parser.add_argument("--reserved-manifest", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--required-binary-sha256", required=True)
    parser.add_argument("--allowed-completed-binary-sha256", action="append", default=[])
    parser.add_argument("--required-target-sha256", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        receipt = build_manifest(
            args.input_manifest,
            args.reserved_manifest,
            args.output,
            args.receipt,
            args.required_binary_sha256,
            set(args.allowed_completed_binary_sha256) | {args.required_binary_sha256},
            args.required_target_sha256,
        )
        print(json.dumps({key: receipt[key] for key in ("source_gpu_jobs", "validated_completed_jobs", "pending_jobs", "output_manifest_sha256")}, sort_keys=True))
        return 0
    except (ManifestError, OSError, ValueError, KeyError, csv.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
