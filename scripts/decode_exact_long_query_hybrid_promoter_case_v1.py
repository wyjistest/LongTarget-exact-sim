#!/usr/bin/env python3
"""Decode and map one exact-hybrid real-promoter TFOsorted case."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from exact_long_query_promoter_mapping import (
    MAPPED_FIELDS,
    TFOSORTED_COLUMNS,
    PromoterMapping,
    read_single_fasta,
    sha256_file,
    validate_tfo_row,
)


class DecodeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DecodeError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".tmp.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class CompressedTsvWriter:
    def __init__(self, path: Path, fields: Sequence[str]) -> None:
        require(not path.exists(), f"refusing to overwrite output: {path}")
        self.path = path
        self.raw = path.open("wb")
        self.process = subprocess.Popen(
            ["zstd", "-T1", "-3", "-q", "-c"],
            stdin=subprocess.PIPE,
            stdout=self.raw,
            stderr=subprocess.PIPE,
        )
        require(self.process.stdin is not None, "zstd writer stdin unavailable")
        self.stream = self.process.stdin
        self.fields = tuple(fields)
        self.uncompressed_digest = hashlib.sha256()
        self.uncompressed_bytes = 0
        self.rows = 0
        self._write(self.fields, header=True)

    def _write(self, values: Iterable[object], *, header: bool = False) -> None:
        texts = [str(value) for value in values]
        require(
            all(not any(marker in value for marker in ("\t", "\r", "\n")) for value in texts),
            "TSV output value contains a delimiter",
        )
        payload = ("\t".join(texts) + "\n").encode("utf-8")
        self.stream.write(payload)
        self.uncompressed_digest.update(payload)
        self.uncompressed_bytes += len(payload)
        if not header:
            self.rows += 1

    def write(self, row: Mapping[str, object]) -> None:
        self._write(row[field] for field in self.fields)

    def close(self, final_path: Path) -> dict[str, object]:
        self.stream.close()
        stderr = ""
        if self.process.stderr is not None:
            stderr = self.process.stderr.read().decode("utf-8", errors="replace")
            self.process.stderr.close()
        code = self.process.wait()
        self.raw.flush()
        os.fsync(self.raw.fileno())
        self.raw.close()
        require(code == 0, f"zstd output failed for {self.path}: {stderr.strip()}")
        return {
            "path": str(final_path.resolve()),
            "rows": self.rows,
            "uncompressed_bytes": self.uncompressed_bytes,
            "uncompressed_sha256": self.uncompressed_digest.hexdigest(),
            "compressed_bytes": self.path.stat().st_size,
            "compressed_sha256": sha256_file(self.path),
        }

    def abort(self) -> None:
        try:
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait()
        finally:
            try:
                self.stream.close()
            except OSError:
                pass
            if self.process.stderr is not None:
                self.process.stderr.close()
            self.raw.close()


class PlainTsvWriter:
    def __init__(self, path: Path, fields: Sequence[str]) -> None:
        require(not path.exists(), f"refusing to overwrite output: {path}")
        self.path = path
        self.handle = path.open("w", encoding="utf-8", newline="")
        self.writer = csv.DictWriter(
            self.handle,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
        )
        self.writer.writeheader()
        self.rows = 0

    def write(self, row: Mapping[str, object]) -> None:
        self.writer.writerow(row)
        self.rows += 1

    def close(self, final_path: Path) -> dict[str, object]:
        self.handle.flush()
        os.fsync(self.handle.fileno())
        self.handle.close()
        return {
            "path": str(final_path.resolve()),
            "rows": self.rows,
            "bytes": self.path.stat().st_size,
            "sha256": sha256_file(self.path),
        }

    def abort(self) -> None:
        self.handle.close()


def sole_output(case_root: Path, receipt: Mapping[str, object]) -> Path:
    artifacts = receipt.get("artifacts")
    require(isinstance(artifacts, list) and len(artifacts) == 1, "case receipt artifact inventory mismatch")
    artifact = artifacts[0]
    require(isinstance(artifact, dict) and artifact.get("role") == "complete_tfosorted", "case output role mismatch")
    path = Path(str(artifact["path"]))
    require(path.is_file() and path.parent == case_root / "runtime_output", "unsafe case output binding")
    require(path.stat().st_size == int(artifact["bytes"]), "case output size mismatch")
    require(sha256_file(path) == artifact["sha256"], "case output digest mismatch")
    return path


def iter_tfo_rows(path: Path) -> Iterable[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        require(tuple(reader.fieldnames or ()) == TFOSORTED_COLUMNS, f"TFOsorted schema mismatch: {path}")
        for line_number, row in enumerate(reader, 2):
            require(None not in row and all(value is not None for value in row.values()), f"malformed TFO row {line_number}")
            yield row


def logicalize_row(row: Mapping[str, str], logical_offset0: int) -> dict[str, str]:
    require(logical_offset0 >= 0, "negative logical target offset")
    result = dict(row)
    for field in ("StartInSeq", "EndInSeq", "StartInGenome", "EndInGenome"):
        try:
            value = int(result[field])
        except (KeyError, ValueError) as error:
            raise DecodeError(f"invalid coordinate field {field}") from error
        require(value >= 0, f"negative coordinate field {field}")
        result[field] = str(value + logical_offset0)
    return result


def output_metadata(path: Path, final_path: Path, rows: int) -> dict[str, object]:
    return {
        "path": str(final_path.resolve()),
        "rows": rows,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def decode_case(case_root: Path, output_root: Path, promoter_root: Path) -> dict[str, object]:
    require(case_root.is_dir() and not case_root.is_symlink(), f"unsafe case root: {case_root}")
    receipt_path = case_root / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(
        receipt.get("status") == "complete" and receipt.get("technical_contract_pass") is True,
        "source case is not technically complete",
    )
    source_output = sole_output(case_root, receipt)
    query_info = receipt["query"]
    target_info = receipt["target"]
    require(isinstance(query_info, dict) and isinstance(target_info, dict), "case input metadata mismatch")
    query_path = Path(str(query_info["path"]))
    target_path = Path(str(target_info["path"]))
    require(sha256_file(query_path) == query_info["file_sha256"], "query FASTA digest mismatch")
    require(sha256_file(target_path) == target_info["file_sha256"], "target FASTA digest mismatch")
    _, query_sequence = read_single_fasta(query_path)
    _, target_sequence = read_single_fasta(target_path)
    require(len(query_sequence) == int(query_info["length_nt"]), "query length mismatch")
    require(len(target_sequence) == int(target_info["length_bp"]), "target length mismatch")
    require(
        hashlib.sha256(query_sequence.encode("ascii")).hexdigest() == query_info["sequence_sha256"],
        "query sequence digest mismatch",
    )

    mapping = PromoterMapping(promoter_root)
    context = mapping.target_context(str(target_info["artifact_id"]))
    require(context.path == target_path, "target path does not match promoter mapping")
    require(context.file_sha256 == target_info["file_sha256"], "target artifact digest mismatch")
    require(context.length_bp == len(target_sequence), "target artifact length mismatch")
    require(context.logical_offset0 == int(target_info["logical_offset0"]), "target logical offset mismatch")

    require(not output_root.exists(), f"refusing to overwrite decode root: {output_root}")
    partial = output_root.with_name(output_root.name + ".partial")
    require(not partial.exists(), f"stale decode partial root: {partial}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    partial.mkdir()
    started_utc = utc_now()
    started = time.perf_counter()
    decoded_fields = TFOSORTED_COLUMNS
    mapped_fields = ("source_row_number", *TFOSORTED_COLUMNS, *MAPPED_FIELDS)
    reject_fields = (
        "source_row_number",
        "reason",
        "normalized_target_local_start0",
        "normalized_target_local_end0",
        "normalized_logical_concat_start0",
        "normalized_logical_concat_end0",
        *TFOSORTED_COLUMNS,
    )
    writers: list[object] = []
    try:
        decoded = CompressedTsvWriter(partial / "decoded-TFOsorted.tsv.zst", decoded_fields)
        mapped = CompressedTsvWriter(partial / "mapped_promoter_associations.tsv.zst", mapped_fields)
        rejects = CompressedTsvWriter(partial / "rejected_hits.tsv.zst", reject_fields)
        retained = PlainTsvWriter(partial / "retained-TFOsorted", decoded_fields)
        writers.extend((decoded, mapped, rejects, retained))
        raw_rows = 0
        unique_rows = 0
        duplicate_rows = 0
        retained_source_hits = 0
        mapped_associations = 0
        reason_counts: Counter[str] = Counter()
        seen: set[tuple[str, ...]] = set()
        minimum_query_start: int | None = None
        maximum_query_end: int | None = None
        for raw_row in iter_tfo_rows(source_output):
            raw_rows += 1
            local_start0, local_end0 = validate_tfo_row(raw_row, query_sequence, target_sequence)
            query_start = int(raw_row["QueryStart"])
            query_end = int(raw_row["QueryEnd"])
            nt_bp = int(raw_row["Nt(bp)"])
            require(query_end - query_start + 1 <= nt_bp <= 512, "TFO row violates bounded Nt contract")
            key = tuple(raw_row[field] for field in TFOSORTED_COLUMNS)
            if key in seen:
                duplicate_rows += 1
                continue
            seen.add(key)
            unique_rows += 1
            source_row_number = unique_rows + 1
            minimum_query_start = query_start if minimum_query_start is None else min(minimum_query_start, query_start)
            maximum_query_end = query_end if maximum_query_end is None else max(maximum_query_end, query_end)
            logical_row = logicalize_row(raw_row, context.logical_offset0)
            decoded.write(logical_row)
            reason, associations = mapping.map_interval(
                context,
                target_sequence,
                local_start0,
                local_end0,
            )
            if reason is not None:
                reason_counts[reason] += 1
                rejects.write({
                    "source_row_number": source_row_number,
                    "reason": reason,
                    "normalized_target_local_start0": local_start0,
                    "normalized_target_local_end0": local_end0,
                    "normalized_logical_concat_start0": context.logical_offset0 + local_start0,
                    "normalized_logical_concat_end0": context.logical_offset0 + local_end0,
                    **logical_row,
                })
                continue
            require(associations, "accepted source hit has no promoter association")
            retained_source_hits += 1
            retained.write(logical_row)
            for association in associations:
                mapped.write({"source_row_number": source_row_number, **logical_row, **association})
                mapped_associations += 1

        outputs = {
            "decoded_tfosorted": decoded.close(output_root / "decoded-TFOsorted.tsv.zst"),
            "mapped_promoter_associations": mapped.close(output_root / "mapped_promoter_associations.tsv.zst"),
            "rejected_hits": rejects.close(output_root / "rejected_hits.tsv.zst"),
            "retained_tfosorted": retained.close(output_root / "retained-TFOsorted"),
        }
        writers.clear()
        require(raw_rows == unique_rows + duplicate_rows, "raw-row conservation failed")
        require(unique_rows == retained_source_hits + sum(reason_counts.values()), "mapping conservation failed")
        require(mapped_associations >= retained_source_hits, "promoter association conservation failed")
        run_plan = {
            "schema_version": "exact_long_query_promoter_decode_source_plan_v1",
            "gene_id": query_info["gene_id"],
            "gene_symbol": query_info["gene_symbol"],
            "query_path": str(query_path.resolve()),
            "query_file_sha256": query_info["file_sha256"],
            "query_sequence_sha256": query_info["sequence_sha256"],
            "query_length_nt": len(query_sequence),
            "target_artifact_id": context.artifact_id,
            "target_path": str(target_path.resolve()),
            "target_file_sha256": context.file_sha256,
            "target_length_bp": context.length_bp,
            "logical_concat_offset0": context.logical_offset0,
            "source_case_receipt": str(receipt_path.resolve()),
            "source_case_receipt_sha256": sha256_file(receipt_path),
            "source_tfosorted": str(source_output.resolve()),
            "source_tfosorted_sha256": sha256_file(source_output),
            "maximum_emitted_triplex_nt": 512,
        }
        atomic_json(partial / "run-plan.json", run_plan)
        summary = {
            "schema_version": "exact_long_query_promoter_decode_map_receipt_v1",
            "status": "complete",
            "started_utc": started_utc,
            "completed_utc": utc_now(),
            "wall_seconds": time.perf_counter() - started,
            "source_job_root": str(output_root.resolve()),
            "source_run_plan_sha256": sha256_file(partial / "run-plan.json"),
            "source_case": str(case_root.resolve()),
            "source_case_receipt_sha256": sha256_file(receipt_path),
            "source_tfosorted": str(source_output.resolve()),
            "source_tfosorted_sha256": sha256_file(source_output),
            "gene_id": query_info["gene_id"],
            "gene_symbol": query_info["gene_symbol"],
            "query_length_nt": len(query_sequence),
            "target_artifact_id": context.artifact_id,
            "target_length_bp": context.length_bp,
            "logical_concat_offset0": context.logical_offset0,
            "raw_source_rows": raw_rows,
            "exact_duplicate_rows_removed": duplicate_rows,
            "decoded_unique_source_hits": unique_rows,
            "retained_source_hits": retained_source_hits,
            "mapped_promoter_associations": mapped_associations,
            "rejected_source_hits": sum(reason_counts.values()),
            "rejection_reason_counts": dict(sorted(reason_counts.items())),
            "minimum_global_query_start1": minimum_query_start,
            "maximum_global_query_end1": maximum_query_end,
            "outputs": outputs,
            "conservation_checks": {
                "raw_equals_unique_plus_duplicates": True,
                "unique_equals_retained_plus_rejected": True,
                "mapped_associations_not_less_than_retained": True,
                "all_tfo_tts_sequences_reconstruct": True,
                "invalid_hits_rejected_before_clustering": True,
                "shard_coordinates_normalized_to_logical_concat": True,
            },
        }
        atomic_json(partial / "decode-map-summary.json", summary)
        checksum_names = (
            "run-plan.json",
            "decoded-TFOsorted.tsv.zst",
            "mapped_promoter_associations.tsv.zst",
            "rejected_hits.tsv.zst",
            "retained-TFOsorted",
            "decode-map-summary.json",
        )
        (partial / "checksums.sha256").write_text(
            "".join(f"{sha256_file(partial / name)}  {name}\n" for name in checksum_names),
            encoding="ascii",
        )
        os.replace(partial, output_root)
        return summary
    except Exception:
        for writer in writers:
            writer.abort()
        shutil.rmtree(partial, ignore_errors=True)
        raise


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--case-root", type=Path, required=True)
    result.add_argument("--output-root", type=Path, required=True)
    result.add_argument("--promoter-root", type=Path, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    value = decode_case(args.case_root, args.output_root, args.promoter_root)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DecodeError, OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        raise SystemExit(2)
