#!/usr/bin/env python3
"""Create label-blind multi-record FASTA inputs for the frozen Phase 5 panel."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_MANIFEST = ROOT / "paper/biological_topk_successor/experimental_benchmark_manifest.tsv"
OUTPUT_ROOT = ROOT / ".paper-artifacts/bioinformatics-submission-readiness-v2/phase3/external-frozen-inputs"
RECEIPT = ROOT / ".paper-artifacts/bioinformatics-submission-readiness-v2/phase3/external-input-generation-receipt.json"


class ExternalInputError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExternalInputError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_single_fasta(path: Path) -> str:
    lines = path.read_text(encoding="ascii").splitlines()
    require(sum(line.startswith(">") for line in lines) == 1, f"expected one source FASTA record: {path}")
    return "".join(line.strip() for line in lines if line and not line.startswith(">" )).upper()


def write_records(path: Path, records: list[tuple[str, str]]) -> None:
    with path.open("w", encoding="ascii", newline="\n") as handle:
        for header, sequence in records:
            handle.write(f">{header}\n")
            for start in range(0, len(sequence), 80):
                handle.write(sequence[start : start + 80] + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true", required=True)
    parser.parse_args()
    if OUTPUT_ROOT.exists() or RECEIPT.exists():
        print("external Phase 3 input destination already exists", file=sys.stderr)
        return 1
    with SOURCE_MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    datasets: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        datasets.setdefault(row["dataset_id"], []).append(row)
    require(len(datasets) == 5, "external dataset count drift")
    OUTPUT_ROOT.mkdir(parents=True)
    outputs = []
    try:
        for dataset_id, dataset_rows in sorted(datasets.items()):
            dataset_rows.sort(key=lambda row: int(row["fasta_order"]))
            require(len(dataset_rows) == 1000, f"region count drift: {dataset_id}")
            require([int(row["fasta_order"]) for row in dataset_rows] == list(range(1, 1001)), f"region order drift: {dataset_id}")
            target_path = ROOT / dataset_rows[0]["target_fasta_path"]
            require(all(row["target_fasta_path"] == dataset_rows[0]["target_fasta_path"] for row in dataset_rows), "dataset target path drift")
            concatenated = read_single_fasta(target_path)
            records = []
            for row in dataset_rows:
                start0 = int(row["target_concat_start0"])
                end0 = int(row["target_concat_end0"])
                sequence = concatenated[start0:end0]
                require(len(sequence) == 4097, f"region length drift: {row['region_id']}")
                require(set(sequence) <= set("ACGT"), f"region alphabet drift: {row['region_id']}")
                require(sha256_bytes(sequence.encode("ascii")) == row["region_sequence_sha256"], f"region digest drift: {row['region_id']}")
                records.append((row["region_id"], sequence))
            destination = OUTPUT_ROOT / dataset_id
            destination.mkdir()
            output = destination / "target-regions.fa"
            write_records(output, records)
            outputs.append(
                {
                    "dataset_id": dataset_id,
                    "path": str(output.relative_to(ROOT)),
                    "sha256": sha256_file(output),
                    "size_bytes": output.stat().st_size,
                    "record_count": len(records),
                    "headers_are_region_ids_only": True,
                    "labels_written_to_fasta": False,
                    "source_concatenated_target_path": str(target_path.relative_to(ROOT)),
                    "source_concatenated_target_sha256": sha256_file(target_path),
                }
            )
        receipt = {
            "schema_version": 1,
            "phase": 3,
            "input_only": True,
            "prediction_executed": False,
            "source_manifest": str(SOURCE_MANIFEST.relative_to(ROOT)),
            "source_manifest_sha256": sha256_file(SOURCE_MANIFEST),
            "mapping": "ascending frozen fasta_order; each # Duplex-ID is the label-blind region_id",
            "outputs": outputs,
        }
        RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        import shutil

        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
        raise
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
