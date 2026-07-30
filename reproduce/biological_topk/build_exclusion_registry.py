#!/usr/bin/env python3
"""Build the biological Top-K fresh-input exclusion registry."""

from __future__ import annotations

import argparse
import csv
import io
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXECUTION_START_HEAD = "2658a98fea8f34bd295892e6236607060e2f2803"
OUTPUT = ROOT / "paper/biological_topk/fresh_input_exclusion_registry.tsv"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

FIELDS = (
    "record_type",
    "query_ordinal_namespace",
    "query_source_ordinal",
    "target_ordinal_namespace",
    "target_source_ordinal",
    "query_id",
    "target_id",
    "query_sha256",
    "target_sha256",
    "query_region",
    "target_region",
    "assembly",
    "coordinate_namespace",
    "pair_digest",
    "source_receipt_path",
    "exclusion_reason",
)


class RegistryError(RuntimeError):
    pass


def frozen_blob(path: str) -> bytes:
    completed = subprocess.run(
        ("git", "show", f"{EXECUTION_START_HEAD}:{path}"),
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RegistryError(f"cannot read frozen source blob: {path}")
    return completed.stdout


def read_frozen_tsv(path: str) -> list[dict[str, str]]:
    text = frozen_blob(path).decode("utf-8")
    return list(csv.DictReader(io.StringIO(text), delimiter="\t"))


def source_coordinate_identity(row: dict[str, str]) -> tuple[str, str]:
    namespace = row["query_ordinal_namespace"]
    if namespace in {"phase2_holdout_role_ordinal", "phase3_application_role_ordinal"}:
        return "GRCh38", "source_fasta_record_coordinates"
    if namespace == "historical_workload_manifest":
        return "as_recorded_in_historical_workload", "source_fasta_record_coordinates"
    return "NA", "NA"


def merge_value(current: str, incoming: str) -> str:
    return ";".join(sorted(set(current.split(";")) | set(incoming.split(";"))))


def build_rows() -> list[dict[str, str]]:
    merged: dict[tuple[str, ...], dict[str, str]] = {}

    def add(row: dict[str, str]) -> None:
        if row["query_sha256"] != "NA" and not SHA256_RE.fullmatch(row["query_sha256"]):
            raise RegistryError(f"invalid query digest: {row['query_id']}")
        if row["target_sha256"] != "NA" and not SHA256_RE.fullmatch(row["target_sha256"]):
            raise RegistryError(f"invalid target digest: {row['target_id']}")
        if row["pair_digest"] != "NA" and not SHA256_RE.fullmatch(row["pair_digest"]):
            raise RegistryError(f"invalid pair digest: {row['query_id']} / {row['target_id']}")
        key = tuple(row[field] for field in FIELDS[:-2])
        if key in merged:
            merged[key]["source_receipt_path"] = merge_value(
                merged[key]["source_receipt_path"], row["source_receipt_path"]
            )
            merged[key]["exclusion_reason"] = merge_value(
                merged[key]["exclusion_reason"], row["exclusion_reason"]
            )
        else:
            merged[key] = row

    base_path = "paper/ssw_cuda/used_input_exclusion_registry.tsv"
    development_lncRNAs = {"H19", "KCNQ1OT1", "MALAT1", "MEG3", "NEAT1"}
    for source in read_frozen_tsv(base_path):
        assembly, coordinate_namespace = source_coordinate_identity(source)
        reason = source["exclusion_reason"]
        if source["query_id"] in development_lncRNAs:
            reason = merge_value(reason, "historical_development_lncRNA")
        add(
            {
                **{field: source[field] for field in FIELDS[:11]},
                "assembly": assembly,
                "coordinate_namespace": coordinate_namespace,
                "pair_digest": source["pair_digest"],
                "source_receipt_path": source["source_receipt_path"],
                "exclusion_reason": reason,
            }
        )

    application_path = "paper/bioinformatics/application_manifest.tsv"
    application_rows = read_frozen_tsv(application_path)
    if len(application_rows) != 718:
        raise RegistryError("historical application universe cardinality drift")
    for source in application_rows:
        role = source["record_role"]
        if role == "query":
            row = {
                "record_type": "query_only",
                "query_ordinal_namespace": "phase3_application_role_ordinal",
                "query_source_ordinal": str(int(source["record_id"][2:])),
                "target_ordinal_namespace": "NA",
                "target_source_ordinal": "NA",
                "query_id": source["record_id"],
                "target_id": "NA",
                "query_sha256": source["sequence_sha256"],
                "target_sha256": "NA",
                "query_region": "full",
                "target_region": "NA",
                "assembly": "GRCh38",
                "coordinate_namespace": "GENCODE_v49_transcript_sequence",
                "pair_digest": "NA",
                "source_receipt_path": f"{application_path};paper/bioinformatics/application_selection.json",
                "exclusion_reason": "phase3_v1_preregistered_application_universe",
            }
        elif role == "target":
            row = {
                "record_type": "target_only",
                "query_ordinal_namespace": "NA",
                "query_source_ordinal": "NA",
                "target_ordinal_namespace": "phase3_application_role_ordinal",
                "target_source_ordinal": str(int(source["record_id"][2:])),
                "query_id": "NA",
                "target_id": source["record_id"],
                "query_sha256": "NA",
                "target_sha256": source["sequence_sha256"],
                "query_region": "NA",
                "target_region": (
                    f"{source['chromosome']}:{source['region_start']}-{source['region_end']}"
                ),
                "assembly": "GRCh38",
                "coordinate_namespace": "GRCh38_0_based_half_open",
                "pair_digest": "NA",
                "source_receipt_path": f"{application_path};paper/bioinformatics/application_selection.json",
                "exclusion_reason": "phase3_v1_preregistered_application_universe",
            }
        else:
            raise RegistryError(f"unknown application record role: {role}")
        add(row)

    corpus_path = "paper/ssw_cuda/corpus_manifest.tsv"
    for source in read_frozen_tsv(corpus_path):
        if source["corpus_partition"] == "historical_regression":
            continue
        reason = f"ssw_cuda_differential_corpus_{source['corpus_partition']}"
        add(
            {
                "record_type": "pair",
                "query_ordinal_namespace": "ssw_cuda_corpus_case_v1",
                "query_source_ordinal": source["case_id"],
                "target_ordinal_namespace": "ssw_cuda_corpus_case_v1",
                "target_source_ordinal": source["case_id"],
                "query_id": f"{source['case_id']}:query",
                "target_id": f"{source['case_id']}:reference",
                "query_sha256": source["query_sha256"],
                "target_sha256": source["reference_sha256"],
                "query_region": "full",
                "target_region": "full",
                "assembly": "synthetic",
                "coordinate_namespace": "synthetic_sequence_0_based_half_open",
                "pair_digest": source["pair_digest"],
                "source_receipt_path": f"{corpus_path};paper/ssw_cuda/corpus_receipt.json",
                "exclusion_reason": reason,
            }
        )

    return sorted(
        merged.values(),
        key=lambda row: (
            row["record_type"],
            row["query_ordinal_namespace"],
            row["query_source_ordinal"],
            row["target_ordinal_namespace"],
            row["target_source_ordinal"],
            row["query_sha256"],
            row["target_sha256"],
            row["pair_digest"],
        ),
    )


def render() -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(build_rows())
    return output.getvalue().encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = render()
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(payload)
    elif not OUTPUT.is_file() or OUTPUT.read_bytes() != payload:
        raise RegistryError("fresh-input exclusion registry does not rebuild byte-for-byte")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RegistryError as error:
        print(f"exclusion registry error: {error}", file=__import__("sys").stderr)
        raise SystemExit(1)
