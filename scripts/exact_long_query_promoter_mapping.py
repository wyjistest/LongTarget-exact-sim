#!/usr/bin/env python3
"""Fail-closed component and genomic mapping for promoter-concat targets."""

from __future__ import annotations

import bisect
import csv
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


SUPPORTED_STRANDS = frozenset({"ParaPlus", "ParaMinus", "AntiPlus", "AntiMinus"})
PLUS_COORDINATE_STRANDS = frozenset({"ParaPlus", "AntiMinus"})
COMPLEMENT = str.maketrans("ACGTN", "TGCAN")
TFOSORTED_COLUMNS = (
    "QueryStart",
    "QueryEnd",
    "StartInSeq",
    "EndInSeq",
    "Direction",
    "Chr",
    "StartInGenome",
    "EndInGenome",
    "MeanStability",
    "MeanIdentity(%)",
    "Strand",
    "Rule",
    "Score",
    "Nt(bp)",
    "Class",
    "MidPoint",
    "Center",
    "TFO sequence",
    "TTS sequence",
)
MAPPED_FIELDS = (
    "target_artifact_id",
    "component_id",
    "target_local_start0",
    "target_local_end0",
    "logical_concat_start0",
    "logical_concat_end0",
    "chromosome",
    "genomic_start0",
    "genomic_end0",
    "genomic_start1",
    "genomic_end1",
    "promoter_id",
    "promoter_gene_id",
    "promoter_gene_name",
    "promoter_biotype",
    "promoter_gene_strand",
    "promoter_tss1",
    "relative_to_tss_transcriptional_start",
    "relative_to_tss_transcriptional_end",
)


class MappingError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MappingError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def read_single_fasta(path: Path) -> tuple[str, str]:
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
                require(records == 1, f"sequence outside sole FASTA record: {path}")
                chunks.append(line.upper())
    sequence = "".join(chunks)
    require(records == 1 and header and sequence, f"expected one non-empty FASTA record: {path}")
    require(set(sequence) <= set("ACGTN"), f"invalid FASTA base: {path}")
    return header, sequence


@dataclass(frozen=True)
class Component:
    component_id: str
    chromosome: str
    genomic_start0: int
    genomic_end0: int
    logical_start0: int
    logical_end0: int
    shard_id: str
    shard_start0: int
    shard_end0: int
    n_count: int


@dataclass(frozen=True)
class Promoter:
    promoter_id: str
    gene_id: str
    gene_name: str
    biotype: str
    gene_strand: str
    tss1: int
    genomic_start0: int
    genomic_end0: int


@dataclass(frozen=True)
class TargetContext:
    artifact_id: str
    path: Path
    file_sha256: str
    length_bp: int
    logical_offset0: int
    components: tuple[Component, ...]
    component_local_starts: tuple[int, ...]

    def local_interval(self, component: Component) -> tuple[int, int]:
        if self.artifact_id == "logical_full_concat":
            return component.logical_start0, component.logical_end0
        return component.shard_start0, component.shard_end0


class PromoterMapping:
    def __init__(self, root: Path) -> None:
        require(root.is_dir() and not root.is_symlink(), f"unsafe promoter root: {root}")
        self.root = root
        _, component_rows = read_tsv(root / "promoter_components.tsv")
        self.components = tuple(
            Component(
                component_id=row["component_id"],
                chromosome=row["chromosome"],
                genomic_start0=int(row["genomic_start0"]),
                genomic_end0=int(row["genomic_end0"]),
                logical_start0=int(row["logical_concat_start0"]),
                logical_end0=int(row["logical_concat_end0"]),
                shard_id=row["shard_id"],
                shard_start0=int(row["shard_start0"]),
                shard_end0=int(row["shard_end0"]),
                n_count=int(row["n_count"]),
            )
            for row in component_rows
        )
        require(
            self.components[0].logical_start0 == 0
            and all(left.logical_end0 == right.logical_start0 for left, right in zip(self.components, self.components[1:])),
            "components are not contiguous in logical-concat order",
        )
        self.component_by_id = {component.component_id: component for component in self.components}
        require(len(self.component_by_id) == len(self.components), "duplicate component ID")

        self.memberships: dict[str, list[Promoter]] = defaultdict(list)
        self.promoters: dict[str, Promoter] = {}
        _, membership_rows = read_tsv(root / "promoter_membership.tsv")
        for row in membership_rows:
            promoter = Promoter(
                promoter_id=row["promoter_id"],
                gene_id=row["gene_id"],
                gene_name=row["gene_name"],
                biotype=row["biotype"],
                gene_strand=row["gene_strand"],
                tss1=int(row["tss1"]),
                genomic_start0=int(row["promoter_genomic_start0"]),
                genomic_end0=int(row["promoter_genomic_end0"]),
            )
            require(promoter.promoter_id not in self.promoters, f"duplicate promoter ID: {promoter.promoter_id}")
            self.promoters[promoter.promoter_id] = promoter
            self.memberships[row["component_id"]].append(promoter)
        require(set(self.memberships) == set(self.component_by_id), "component/membership identity mismatch")
        for values in self.memberships.values():
            values.sort(key=lambda value: value.promoter_id)

        _, shard_rows = read_tsv(root / "shards.tsv")
        self.shards = {row["shard_id"]: row for row in shard_rows}
        require(len(self.shards) == len(shard_rows), "duplicate shard ID")

    def target_context(self, artifact_id: str) -> TargetContext:
        if artifact_id == "logical_full_concat":
            path = self.root / "promoter_components_concat.fa"
            return TargetContext(
                artifact_id=artifact_id,
                path=path,
                file_sha256=sha256_file(path),
                length_bp=self.components[-1].logical_end0,
                logical_offset0=0,
                components=self.components,
                component_local_starts=tuple(component.logical_start0 for component in self.components),
            )
        require(artifact_id in self.shards, f"unknown target artifact: {artifact_id}")
        row = self.shards[artifact_id]
        components = tuple(component for component in self.components if component.shard_id == artifact_id)
        require(components and components[0].component_id == row["first_component_id"], "shard first component mismatch")
        require(components[-1].component_id == row["last_component_id"], "shard last component mismatch")
        require(
            components[0].shard_start0 == 0
            and all(left.shard_end0 == right.shard_start0 for left, right in zip(components, components[1:])),
            "components are not contiguous in shard order",
        )
        path = self.root / row["fasta_path"]
        require(sha256_file(path) == row["file_sha256"], "shard file digest mismatch")
        return TargetContext(
            artifact_id=artifact_id,
            path=path,
            file_sha256=row["file_sha256"],
            length_bp=int(row["shard_length_bp"]),
            logical_offset0=int(row["logical_concat_start0"]),
            components=components,
            component_local_starts=tuple(component.shard_start0 for component in components),
        )

    def map_interval(
        self,
        context: TargetContext,
        target_sequence: str,
        local_start0: int,
        local_end0: int,
    ) -> tuple[str | None, list[dict[str, object]]]:
        require(len(target_sequence) == context.length_bp, "target sequence/context length mismatch")
        require(0 <= local_start0 < local_end0 <= context.length_bp, "target interval outside artifact")
        position = bisect.bisect_right(context.component_local_starts, local_start0) - 1
        if position < 0:
            return "cross_component_boundary", []
        component = context.components[position]
        component_start, component_end = context.local_interval(component)
        if local_start0 < component_start or local_end0 > component_end:
            return "cross_component_boundary", []
        if "N" in target_sequence[local_start0:local_end0]:
            return "overlaps_reference_N", []
        logical_start0 = context.logical_offset0 + local_start0
        logical_end0 = context.logical_offset0 + local_end0
        require(
            component.logical_start0 <= logical_start0 < logical_end0 <= component.logical_end0,
            "artifact-local and logical component coordinates disagree",
        )
        genomic_start0 = component.genomic_start0 + logical_start0 - component.logical_start0
        genomic_end0 = component.genomic_start0 + logical_end0 - component.logical_start0
        promoters = [
            promoter
            for promoter in self.memberships[component.component_id]
            if promoter.genomic_start0 <= genomic_start0 and genomic_end0 <= promoter.genomic_end0
        ]
        if not promoters:
            return "not_wholly_contained_in_any_original_promoter", []
        associations = []
        for promoter in promoters:
            if promoter.gene_strand == "+":
                relative_start = genomic_start0 - (promoter.tss1 - 1)
                relative_end = genomic_end0 - 1 - (promoter.tss1 - 1)
            else:
                relative_start = (promoter.tss1 - 1) - (genomic_end0 - 1)
                relative_end = (promoter.tss1 - 1) - genomic_start0
            associations.append({
                "target_artifact_id": context.artifact_id,
                "component_id": component.component_id,
                "target_local_start0": local_start0,
                "target_local_end0": local_end0,
                "logical_concat_start0": logical_start0,
                "logical_concat_end0": logical_end0,
                "chromosome": component.chromosome,
                "genomic_start0": genomic_start0,
                "genomic_end0": genomic_end0,
                "genomic_start1": genomic_start0 + 1,
                "genomic_end1": genomic_end0,
                "promoter_id": promoter.promoter_id,
                "promoter_gene_id": promoter.gene_id,
                "promoter_gene_name": promoter.gene_name,
                "promoter_biotype": promoter.biotype,
                "promoter_gene_strand": promoter.gene_strand,
                "promoter_tss1": promoter.tss1,
                "relative_to_tss_transcriptional_start": relative_start,
                "relative_to_tss_transcriptional_end": relative_end,
            })
        return None, associations


def normalized_target_interval(row: Mapping[str, str], target_length: int) -> tuple[int, int]:
    try:
        start = int(row["StartInSeq"])
        end = int(row["EndInSeq"])
    except (KeyError, ValueError) as error:
        raise MappingError("invalid target coordinate") from error
    strand = row["Strand"]
    require(strand in SUPPORTED_STRANDS, f"unsupported LongTarget strand: {strand}")
    if strand in PLUS_COORDINATE_STRANDS:
        start0, end0 = start - 1, end
    else:
        start0, end0 = start, end + 1
    require(0 <= start0 < end0 <= target_length, f"invalid normalized target interval: {start0}-{end0}")
    return start0, end0


def target_transform(sequence: str, strand: str) -> str:
    if strand == "ParaPlus":
        return sequence
    if strand == "ParaMinus":
        return sequence.translate(COMPLEMENT)[::-1]
    if strand == "AntiMinus":
        return sequence.translate(COMPLEMENT)
    if strand == "AntiPlus":
        return sequence[::-1]
    raise MappingError(f"unsupported LongTarget strand: {strand}")


def validate_tfo_row(
    row: Mapping[str, str], query_sequence: str, target_sequence: str
) -> tuple[int, int]:
    query_start1 = int(row["QueryStart"])
    query_end1 = int(row["QueryEnd"])
    require(1 <= query_start1 <= query_end1 <= len(query_sequence), "query interval outside source")
    observed_tfo = row["TFO sequence"].replace("-", "").upper()
    require(observed_tfo == query_sequence[query_start1 - 1 : query_end1], "TFO does not reconstruct from query")
    start0, end0 = normalized_target_interval(row, len(target_sequence))
    observed_tts = row["TTS sequence"].replace("-", "").upper()
    require(
        observed_tts == target_transform(target_sequence[start0:end0], row["Strand"]),
        "TTS does not reconstruct from target",
    )
    return start0, end0
