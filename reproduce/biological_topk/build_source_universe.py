#!/usr/bin/env python3
"""Build the input-only Phase 1 query and target source universes."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/biological_topk"
SOURCES = ROOT / ".tmp/bioinformatics_application_sources"
QUERY_SOURCE = SOURCES / "gencode.v49.lncRNA_transcripts.fa.gz"
GTF_SOURCE = SOURCES / "gencode.v49.annotation.gtf.gz"
CHROMOSOME_SOURCES = {
    "chr21": SOURCES / "chr21.fa.gz",
    "chr22": SOURCES / "chr22.fa.gz",
}
EXCLUSION_PATH = PAPER / "fresh_input_exclusion_registry.tsv"
QUERY_OUTPUT = PAPER / "query_source_universe.tsv.gz"
TARGET_OUTPUT = PAPER / "target_source_universe.tsv.gz"
RECEIPT_OUTPUT = PAPER / "source_universe_receipt.json"

EXPECTED_SOURCE_SHA256 = {
    "gencode.v49.lncRNA_transcripts.fa.gz": "1f04e509309fa74b694ef3cc1e52c1c8173bb0e679f8a22785fa43ecadd28ef4",
    "gencode.v49.annotation.gtf.gz": "d6e6fe0515c95b2a8cd36a853c1989cee9115c736c60237c56ae92b9daaaf7c4",
    "chr21.fa.gz": "c979ca1e5065c2521a50773473e0d0cc018fd6f3e9bb3aa90493fe7b45d57d1b",
    "chr22.fa.gz": "05f9d97d6fbfd08a44ca45b50837ca2ae9c471f35ba79dffec04d2cb5eaaf695",
}
PRIMARY_CHROMOSOMES = frozenset({f"chr{index}" for index in range(1, 23)} | {"chrX"})
QUERY_NAMESPACE = "gencode_v49_representative_lncRNA_v1"
TARGET_RECIPES = (
    {
        "stratum": "short",
        "recipe_id": "grch38_tss_centered_4097_v1",
        "length": 4097,
        "namespace": "grch38_chr21_chr22_tss_short_v1",
    },
    {
        "stratum": "medium",
        "recipe_id": "grch38_tss_centered_2000001_v1",
        "length": 2_000_001,
        "namespace": "grch38_chr21_chr22_tss_medium_v1",
    },
    {
        "stratum": "large",
        "recipe_id": "grch38_tss_centered_10000001_v1",
        "length": 10_000_001,
        "namespace": "grch38_chr21_chr22_tss_large_v1",
    },
)
QUERY_FIELDS = (
    "query_ordinal_namespace",
    "source_ordinal",
    "annotation_release",
    "assembly",
    "transcript_id",
    "stable_transcript_id",
    "gene_id",
    "stable_gene_id",
    "gene_name",
    "biotype",
    "chromosome",
    "primary_chromosome_status",
    "strand",
    "sequence_length",
    "sequence_sha256",
    "gc_numerator",
    "gc_denominator",
    "gc_fraction",
    "max_base_fraction",
    "sampled_distinct_4mer_fraction",
    "operating_envelope_eligible",
    "historical_exclusion_status",
    "historical_exclusion_reasons",
)
TARGET_FIELDS = (
    "target_ordinal_namespace",
    "source_ordinal",
    "target_scale_stratum",
    "extraction_recipe_id",
    "annotation_release",
    "assembly",
    "anchor_transcript_id",
    "anchor_gene_id",
    "anchor_gene_name",
    "anchor_biotype",
    "chromosome",
    "anchor_strand",
    "anchor_tss_1based",
    "target_coordinate_namespace",
    "region_start0",
    "region_end0",
    "sequence_length",
    "sequence_orientation",
    "sequence_sha256",
    "gc_numerator",
    "gc_denominator",
    "gc_fraction",
    "n_numerator",
    "n_fraction",
    "max_base_fraction",
    "sampled_distinct_4mer_fraction",
    "operating_envelope_eligible",
    "historical_exclusion_status",
    "historical_exclusion_reasons",
)


@dataclass(frozen=True)
class Exclusions:
    query_digests: dict[str, frozenset[str]]
    target_digests: dict[str, frozenset[str]]
    query_ordinals: dict[tuple[str, str], frozenset[str]]
    target_ordinals: dict[tuple[str, str], frozenset[str]]


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_id(value: str) -> str:
    return value.split(".", 1)[0]


def load_application_module():
    path = ROOT / "reproduce/bioinformatics/build_application_panel.py"
    spec = importlib.util.spec_from_file_location("biological_topk_application_source", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fraction_string(numerator: int, denominator: int) -> str:
    if denominator <= 0 or not 0 <= numerator <= denominator:
        raise ValueError("invalid fraction")
    with localcontext() as context:
        context.prec = 40
        value = Decimal(numerator) / Decimal(denominator)
        rendered = format(value.quantize(Decimal("0.000000000001")), "f")
    return rendered.rstrip("0").rstrip(".") or "0"


def sampled_distinct_4mer_fraction(sequence: str, sample_limit: int = 4096) -> str:
    available = len(sequence) - 3
    if available <= 0:
        return "0"
    sample_count = min(available, sample_limit)
    if sample_count == 1:
        positions = (0,)
    else:
        positions = tuple(
            index * (available - 1) // (sample_count - 1)
            for index in range(sample_count)
        )
    distinct = len({sequence[position : position + 4] for position in positions})
    return fraction_string(distinct, min(625, sample_count))


def sequence_features(sequence: str) -> dict[str, str | int]:
    if not sequence:
        raise ValueError("source sequence is empty")
    counts = {base: sequence.count(base) for base in "ACGTN"}
    if sum(counts.values()) != len(sequence):
        raise ValueError("source sequence is outside the ACGTN operating alphabet")
    length = len(sequence)
    gc = counts["G"] + counts["C"]
    maximum = max(counts.values())
    return {
        "sequence_sha256": sha256_bytes(sequence.encode("ascii")),
        "gc_numerator": gc,
        "gc_denominator": length,
        "gc_fraction": fraction_string(gc, length),
        "n_numerator": counts["N"],
        "n_fraction": fraction_string(counts["N"], length),
        "max_base_fraction": fraction_string(maximum, length),
        "sampled_distinct_4mer_fraction": sampled_distinct_4mer_fraction(sequence),
    }


def read_exclusions() -> Exclusions:
    query_digests: dict[str, set[str]] = defaultdict(set)
    target_digests: dict[str, set[str]] = defaultdict(set)
    query_ordinals: dict[tuple[str, str], set[str]] = defaultdict(set)
    target_ordinals: dict[tuple[str, str], set[str]] = defaultdict(set)
    with EXCLUSION_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            reasons = set(row["exclusion_reason"].split(";"))
            query_digest = row["query_sha256"]
            target_digest = row["target_sha256"]
            if query_digest != "NA":
                query_digests[query_digest].update(reasons)
            if target_digest != "NA":
                target_digests[target_digest].update(reasons)
            if row["query_ordinal_namespace"] != "NA" and row["query_source_ordinal"] != "NA":
                query_ordinals[(row["query_ordinal_namespace"], row["query_source_ordinal"])].update(reasons)
            if row["target_ordinal_namespace"] != "NA" and row["target_source_ordinal"] != "NA":
                target_ordinals[(row["target_ordinal_namespace"], row["target_source_ordinal"])].update(reasons)
    return Exclusions(
        query_digests={key: frozenset(value) for key, value in query_digests.items()},
        target_digests={key: frozenset(value) for key, value in target_digests.items()},
        query_ordinals={key: frozenset(value) for key, value in query_ordinals.items()},
        target_ordinals={key: frozenset(value) for key, value in target_ordinals.items()},
    )


def exclusion_reasons(
    *,
    digest: str,
    namespace: str,
    ordinal: int,
    digest_registry: dict[str, frozenset[str]],
    ordinal_registry: dict[tuple[str, str], frozenset[str]],
) -> tuple[str, ...]:
    reasons = set(digest_registry.get(digest, ()))
    reasons.update(ordinal_registry.get((namespace, str(ordinal)), ()))
    return tuple(sorted(reasons))


def build_query_rows(app: Any, transcripts: dict[str, Any], exclusions: Exclusions) -> list[dict[str, Any]]:
    representatives: dict[str, tuple[dict[str, Any], str]] = {}
    for header, sequence in app._iter_fasta_records(QUERY_SOURCE):
        parts = header.split("|")
        if len(parts) != 8 or parts[-1] != "":
            raise ValueError(f"unsupported GENCODE v49 FASTA header: {header}")
        transcript_id, gene_id = parts[0], parts[1]
        metadata = transcripts.get(transcript_id)
        if metadata is None:
            continue
        if metadata.gene_id != gene_id or metadata.gene_name != parts[5]:
            raise ValueError(f"FASTA/GTF identity mismatch for {transcript_id}")
        if (
            metadata.gene_type != "lncRNA"
            or metadata.chromosome not in PRIMARY_CHROMOSOMES
            or set(sequence) - set("ACGT")
            or not 500 <= len(sequence) <= 2812
        ):
            continue
        if int(parts[6]) != len(sequence):
            raise ValueError(f"declared FASTA length mismatch for {transcript_id}")
        candidate = {
            "transcript_id": transcript_id,
            "gene_id": gene_id,
            "gene_name": metadata.gene_name,
            "chromosome": metadata.chromosome,
            "strand": metadata.strand,
            "level": metadata.level,
            "basic": "basic" in metadata.tags,
            "sequence_length": len(sequence),
            "sequence_sha256": sha256_bytes(sequence.encode("ascii")),
        }
        key = stable_id(gene_id)
        existing = representatives.get(key)
        if existing is None or app.query_representative_key(candidate) < app.query_representative_key(existing[0]):
            representatives[key] = (candidate, sequence)

    ordered = sorted(
        representatives.values(),
        key=lambda item: (stable_id(item[0]["gene_id"]), item[0]["transcript_id"]),
    )
    rows: list[dict[str, Any]] = []
    for ordinal, (representative, sequence) in enumerate(ordered, 1):
        features = sequence_features(sequence)
        reasons = exclusion_reasons(
            digest=str(features["sequence_sha256"]),
            namespace=QUERY_NAMESPACE,
            ordinal=ordinal,
            digest_registry=exclusions.query_digests,
            ordinal_registry=exclusions.query_ordinals,
        )
        rows.append(
            {
                "query_ordinal_namespace": QUERY_NAMESPACE,
                "source_ordinal": ordinal,
                "annotation_release": "GENCODE v49",
                "assembly": "GRCh38",
                "transcript_id": representative["transcript_id"],
                "stable_transcript_id": stable_id(representative["transcript_id"]),
                "gene_id": representative["gene_id"],
                "stable_gene_id": stable_id(representative["gene_id"]),
                "gene_name": representative["gene_name"],
                "biotype": "lncRNA",
                "chromosome": representative["chromosome"],
                "primary_chromosome_status": "primary",
                "strand": representative["strand"],
                "sequence_length": len(sequence),
                "sequence_sha256": features["sequence_sha256"],
                "gc_numerator": features["gc_numerator"],
                "gc_denominator": features["gc_denominator"],
                "gc_fraction": features["gc_fraction"],
                "max_base_fraction": features["max_base_fraction"],
                "sampled_distinct_4mer_fraction": features["sampled_distinct_4mer_fraction"],
                "operating_envelope_eligible": 1,
                "historical_exclusion_status": "excluded" if reasons else "fresh_eligible",
                "historical_exclusion_reasons": ";".join(reasons) if reasons else "NA",
            }
        )
    return rows


def fixed_centered_window(tss_1based: int, chromosome_length: int, length: int) -> tuple[int, int]:
    if length > chromosome_length or length % 2 != 1:
        raise ValueError("target window must be odd and fit the chromosome")
    centered_start = (tss_1based - 1) - length // 2
    start0 = min(max(centered_start, 0), chromosome_length - length)
    return start0, start0 + length


def build_target_rows(
    app: Any,
    transcripts: dict[str, Any],
    chromosomes: dict[str, str],
    exclusions: Exclusions,
) -> list[dict[str, Any]]:
    candidates_by_gene = app._validated_target_candidates(transcripts)
    anchors = [app.choose_target_representative(values) for values in candidates_by_gene.values()]
    anchors.sort(
        key=lambda tx: (
            int(tx.chromosome[3:]),
            tx.start if tx.strand == "+" else tx.end,
            stable_id(tx.gene_id),
            tx.transcript_id,
        )
    )
    rows: list[dict[str, Any]] = []
    feature_cache: dict[tuple[str, int, int], dict[str, str | int]] = {}
    for recipe in TARGET_RECIPES:
        namespace = str(recipe["namespace"])
        length = int(recipe["length"])
        for ordinal, anchor in enumerate(anchors, 1):
            chromosome_sequence = chromosomes[anchor.chromosome]
            tss = anchor.start if anchor.strand == "+" else anchor.end
            start0, end0 = fixed_centered_window(tss, len(chromosome_sequence), length)
            cache_key = (anchor.chromosome, start0, end0)
            features = feature_cache.get(cache_key)
            if features is None:
                sequence = chromosome_sequence[start0:end0]
                features = sequence_features(sequence)
                feature_cache[cache_key] = features
            reasons = exclusion_reasons(
                digest=str(features["sequence_sha256"]),
                namespace=namespace,
                ordinal=ordinal,
                digest_registry=exclusions.target_digests,
                ordinal_registry=exclusions.target_ordinals,
            )
            rows.append(
                {
                    "target_ordinal_namespace": namespace,
                    "source_ordinal": ordinal,
                    "target_scale_stratum": recipe["stratum"],
                    "extraction_recipe_id": recipe["recipe_id"],
                    "annotation_release": "GENCODE v49",
                    "assembly": "GRCh38",
                    "anchor_transcript_id": anchor.transcript_id,
                    "anchor_gene_id": anchor.gene_id,
                    "anchor_gene_name": anchor.gene_name,
                    "anchor_biotype": anchor.gene_type,
                    "chromosome": anchor.chromosome,
                    "anchor_strand": anchor.strand,
                    "anchor_tss_1based": tss,
                    "target_coordinate_namespace": "GRCh38_0_based_half_open",
                    "region_start0": start0,
                    "region_end0": end0,
                    "sequence_length": length,
                    "sequence_orientation": "forward_genomic",
                    "sequence_sha256": features["sequence_sha256"],
                    "gc_numerator": features["gc_numerator"],
                    "gc_denominator": features["gc_denominator"],
                    "gc_fraction": features["gc_fraction"],
                    "n_numerator": features["n_numerator"],
                    "n_fraction": features["n_fraction"],
                    "max_base_fraction": features["max_base_fraction"],
                    "sampled_distinct_4mer_fraction": features["sampled_distinct_4mer_fraction"],
                    "operating_envelope_eligible": 1,
                    "historical_exclusion_status": "excluded" if reasons else "fresh_eligible",
                    "historical_exclusion_reasons": ";".join(reasons) if reasons else "NA",
                }
            )
    return rows


def render_tsv(fields: tuple[str, ...], rows: Iterable[dict[str, Any]]) -> bytes:
    text = io.StringIO(newline="")
    writer = csv.DictWriter(
        text,
        fieldnames=fields,
        delimiter="\t",
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(rows)
    return text.getvalue().encode("utf-8")


def deterministic_gzip(payload: bytes) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=output, mtime=0) as handle:
        handle.write(payload)
    return output.getvalue()


def canonical_json(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("ascii")


def build() -> dict[Path, bytes]:
    source_paths = (QUERY_SOURCE, GTF_SOURCE, *CHROMOSOME_SOURCES.values())
    for path in source_paths:
        actual = sha256_file(path)
        expected = EXPECTED_SOURCE_SHA256[path.name]
        if actual != expected:
            raise ValueError(f"source digest mismatch for {path}: {actual}")

    app = load_application_module()
    transcripts = app.parse_gtf(GTF_SOURCE)
    chromosomes = {
        chromosome: app.read_chromosome_fasta(path, chromosome)
        for chromosome, path in CHROMOSOME_SOURCES.items()
    }
    exclusions = read_exclusions()
    query_rows = build_query_rows(app, transcripts, exclusions)
    target_rows = build_target_rows(app, transcripts, chromosomes, exclusions)
    query_tsv = render_tsv(QUERY_FIELDS, query_rows)
    target_tsv = render_tsv(TARGET_FIELDS, target_rows)
    query_gzip = deterministic_gzip(query_tsv)
    target_gzip = deterministic_gzip(target_tsv)

    target_summary: dict[str, dict[str, int]] = {}
    for recipe in TARGET_RECIPES:
        stratum = str(recipe["stratum"])
        stratum_rows = [row for row in target_rows if row["target_scale_stratum"] == stratum]
        fresh = [row for row in stratum_rows if row["historical_exclusion_status"] == "fresh_eligible"]
        target_summary[stratum] = {
            "row_count": len(stratum_rows),
            "fresh_eligible_row_count": len(fresh),
            "fresh_unique_sequence_digest_count": len({row["sequence_sha256"] for row in fresh}),
            "fresh_unique_namespaced_ordinal_count": len(
                {(row["target_ordinal_namespace"], row["source_ordinal"]) for row in fresh}
            ),
        }
    fresh_queries = [row for row in query_rows if row["historical_exclusion_status"] == "fresh_eligible"]
    receipt = {
        "schema_version": 1,
        "annotation_release": "GENCODE v49",
        "assembly": "GRCh38",
        "build_kind": "input_only_static_source_universe",
        "fresh_pair_selected": False,
        "new_prediction_run": False,
        "historical_exclusion_registry": {
            "path": EXCLUSION_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(EXCLUSION_PATH),
        },
        "sources": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": EXPECTED_SOURCE_SHA256[path.name],
                "size_bytes": path.stat().st_size,
            }
            for path in source_paths
        ],
        "query_universe": {
            "path": QUERY_OUTPUT.relative_to(ROOT).as_posix(),
            "gzip_sha256": sha256_bytes(query_gzip),
            "uncompressed_tsv_sha256": sha256_bytes(query_tsv),
            "row_count": len(query_rows),
            "fresh_eligible_row_count": len(fresh_queries),
            "fresh_unique_sequence_digest_count": len({row["sequence_sha256"] for row in fresh_queries}),
            "fresh_unique_namespaced_ordinal_count": len(
                {(row["query_ordinal_namespace"], row["source_ordinal"]) for row in fresh_queries}
            ),
        },
        "target_recipes": list(TARGET_RECIPES),
        "target_universe": {
            "path": TARGET_OUTPUT.relative_to(ROOT).as_posix(),
            "gzip_sha256": sha256_bytes(target_gzip),
            "uncompressed_tsv_sha256": sha256_bytes(target_tsv),
            "row_count": len(target_rows),
            "strata": target_summary,
        },
        "source_parser": {
            "path": "reproduce/bioinformatics/build_application_panel.py",
            "sha256": sha256_file(ROOT / "reproduce/bioinformatics/build_application_panel.py"),
        },
    }
    return {
        QUERY_OUTPUT: query_gzip,
        TARGET_OUTPUT: target_gzip,
        RECEIPT_OUTPUT: canonical_json(receipt),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs = build()
    if args.check:
        mismatches = [path for path, expected in outputs.items() if not path.is_file() or path.read_bytes() != expected]
        if mismatches:
            for path in mismatches:
                print(f"source universe drift: {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print("biological Top-K source universes reproduce byte-for-byte")
        return 0
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    print(f"wrote {len(outputs)} Phase 1 source-universe artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
