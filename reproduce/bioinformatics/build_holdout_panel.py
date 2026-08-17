#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, TextIO


ROOT = Path(__file__).resolve().parents[2]
SELECTION_SEED = "gasal2-longtarget-phase2-holdout-v1-20260724"
ASSEMBLY = "GRCh38"
ANNOTATION_RELEASE = "GENCODE v49"
DEVELOPMENT_TARGET_CHROMOSOMES = {"chr11", "chr21", "chr22"}
PRIMARY_CHROMOSOMES = {f"chr{index}" for index in range(1, 23)} | {"chrX"}
ATTRIBUTE_PATTERN = re.compile(r'(\S+)\s+"([^"]*)"')
STRATA = (
    ("le_800", 200, 800),
    ("801_1600", 801, 1600),
    ("1601_2812", 1601, 2812),
)


def open_text(path: Path) -> TextIO:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="strict", newline="")
    return path.open("r", encoding="utf-8", errors="strict", newline="")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sequence_sha256(sequence: str) -> str:
    return hashlib.sha256(sequence.encode("ascii")).hexdigest()


def stable_id(value: str) -> str:
    return value.split(".", 1)[0]


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.partial.{os.getpid()}"
    try:
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def path_exists(path: Path) -> bool:
    return os.path.lexists(path)


def tree_signature(root: Path) -> list[tuple[str, str, int, str]]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"artifact tree is not a regular directory: {root}")
    signature: list[tuple[str, str, int, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f"artifact tree contains a symbolic link: {path}")
        if path.is_dir():
            signature.append((relative, "directory", 0, ""))
        elif path.is_file():
            signature.append((relative, "file", path.stat().st_size, sha256_file(path)))
        else:
            raise ValueError(f"artifact tree contains a non-regular entry: {path}")
    return signature


def require_existing_match(destination: Path, staged: Path, label: str) -> None:
    if not path_exists(destination):
        return
    if staged.is_dir():
        matches = (
            destination.is_dir()
            and not destination.is_symlink()
            and tree_signature(destination) == tree_signature(staged)
        )
    else:
        matches = (
            destination.is_file()
            and not destination.is_symlink()
            and destination.read_bytes() == staged.read_bytes()
        )
    if not matches:
        raise ValueError(f"existing {label} drifted from the fully staged freeze: {destination}")


def publish_file_if_missing(staged: Path, destination: Path) -> None:
    if path_exists(destination):
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.parent / f".{destination.name}.partial.{os.getpid()}"
    try:
        with staged.open("rb") as source, temporary.open("xb") as target:
            shutil.copyfileobj(source, target)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def parse_fasta(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    header: str | None = None
    sequence: list[str] = []
    with open_text(path) as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    records.append((header, "".join(sequence).upper()))
                header = line[1:]
                sequence = []
            elif header is None:
                raise ValueError(f"sequence before FASTA header in {path}")
            else:
                sequence.append(line)
    if header is not None:
        records.append((header, "".join(sequence).upper()))
    if not records or any(not sequence for _, sequence in records):
        raise ValueError(f"empty FASTA record in {path}")
    return records


def parse_attributes(text: str) -> dict[str, str]:
    return {match.group(1): match.group(2) for match in ATTRIBUTE_PATTERN.finditer(text)}


def parse_annotation(path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    transcripts: dict[str, dict[str, Any]] = {}
    protein_genes: list[dict[str, Any]] = []
    with open_text(path) as handle:
        for line_number, raw in enumerate(handle, 1):
            if raw.startswith("#"):
                continue
            fields = raw.rstrip("\n").split("\t")
            if len(fields) != 9:
                raise ValueError(f"malformed GTF row {line_number} in {path}")
            chromosome, source, feature, start, end, _, strand, _, attribute_text = fields
            attributes = parse_attributes(attribute_text)
            if feature == "transcript" and attributes.get("gene_type") == "lncRNA":
                transcript_id = attributes.get("transcript_id")
                gene_id = attributes.get("gene_id")
                gene_name = attributes.get("gene_name")
                if not transcript_id or not gene_id or not gene_name:
                    raise ValueError(f"missing lncRNA identifiers at GTF row {line_number}")
                level_match = re.search(r"(?:^|;\s*)level\s+(\d+)(?:;|$)", attribute_text)
                level = int(level_match.group(1)) if level_match else 99
                tags = set(re.findall(r'tag\s+"([^"]+)"', attribute_text))
                transcripts[transcript_id] = {
                    "transcript_id": transcript_id,
                    "gene_id": gene_id,
                    "gene_name": gene_name,
                    "chromosome": chromosome,
                    "source": source,
                    "level": level,
                    "basic": "basic" in tags,
                }
            elif feature == "gene" and attributes.get("gene_type") == "protein_coding":
                gene_id = attributes.get("gene_id")
                gene_name = attributes.get("gene_name")
                if not gene_id or not gene_name:
                    raise ValueError(f"missing protein-coding identifiers at GTF row {line_number}")
                protein_genes.append(
                    {
                        "gene_id": gene_id,
                        "gene_name": gene_name,
                        "chromosome": chromosome,
                        "start": int(start),
                        "end": int(end),
                        "strand": strand,
                    }
                )
    return transcripts, protein_genes


def read_exclusions(path: Path) -> dict[str, set[str]]:
    exclusions = {"gene_id": set(), "gene_name": set(), "sequence_sha256": set()}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != ["exclusion_type", "value", "reason"]:
            raise ValueError("development exclusions must have exclusion_type, value and reason columns")
        for row in reader:
            exclusion_type = row["exclusion_type"]
            if exclusion_type not in exclusions:
                raise ValueError(f"unsupported exclusion type: {exclusion_type}")
            value = stable_id(row["value"]) if exclusion_type == "gene_id" else row["value"]
            exclusions[exclusion_type].add(value)
    return exclusions


def length_stratum(length: int) -> str | None:
    for name, minimum, maximum in STRATA:
        if minimum <= length <= maximum:
            return name
    return None


def seeded_key(*values: str) -> str:
    return hashlib.sha256("|".join((SELECTION_SEED, *values)).encode("utf-8")).hexdigest()


def select_queries(
    fasta_path: Path,
    transcript_metadata: dict[str, dict[str, Any]],
    exclusions: dict[str, set[str]],
) -> list[dict[str, Any]]:
    per_gene: dict[str, list[dict[str, Any]]] = {}
    for header, sequence in parse_fasta(fasta_path):
        parts = header.split("|")
        if len(parts) < 7:
            raise ValueError(f"unsupported GENCODE FASTA header: {header}")
        transcript_id, gene_id = parts[0], parts[1]
        metadata = transcript_metadata.get(transcript_id)
        if metadata is None or metadata["chromosome"] not in PRIMARY_CHROMOSOMES:
            continue
        if metadata["gene_id"] != gene_id:
            raise ValueError(f"GENCODE FASTA/GTF gene mismatch for {transcript_id}")
        if set(sequence) - set("ACGT"):
            continue
        stratum = length_stratum(len(sequence))
        digest = sequence_sha256(sequence)
        if stratum is None:
            continue
        if stable_id(gene_id) in exclusions["gene_id"]:
            continue
        if metadata["gene_name"] in exclusions["gene_name"]:
            continue
        if digest in exclusions["sequence_sha256"]:
            continue
        row = {
            **metadata,
            "transcript_id": transcript_id,
            "gene_id": gene_id,
            "sequence_length_nt": len(sequence),
            "sequence_sha256": digest,
            "length_stratum": stratum,
        }
        per_gene.setdefault(stable_id(gene_id), []).append(row)

    representatives: list[dict[str, Any]] = []
    for rows in per_gene.values():
        representatives.append(
            min(
                rows,
                key=lambda row: (
                    row["level"],
                    0 if row["basic"] else 1,
                    -row["sequence_length_nt"],
                    row["transcript_id"],
                ),
            )
        )

    selected: list[dict[str, Any]] = []
    for stratum, _, _ in STRATA:
        eligible = [row for row in representatives if row["length_stratum"] == stratum]
        eligible.sort(
            key=lambda row: (
                seeded_key(
                    stable_id(row["gene_id"]),
                    stable_id(row["transcript_id"]),
                    row["sequence_sha256"],
                ),
                row["gene_id"],
            )
        )
        if len(eligible) < 4:
            raise ValueError(f"length stratum {stratum} has only {len(eligible)} eligible genes; 4 required")
        selected.extend(eligible[:4])
    for index, row in enumerate(selected, 1):
        row["query_id"] = f"hq{index:02d}"
        row["selection_hash"] = seeded_key(
            stable_id(row["gene_id"]),
            stable_id(row["transcript_id"]),
            row["sequence_sha256"],
        )
    return selected


def promoter_region(gene: dict[str, Any]) -> tuple[int, int, int]:
    if gene["strand"] == "+":
        tss = gene["start"]
        start = max(1, tss - 2000)
        end = tss + 500
    elif gene["strand"] == "-":
        tss = gene["end"]
        start = max(1, tss - 500)
        end = tss + 2000
    else:
        raise ValueError(f"unsupported target gene strand: {gene['strand']}")
    return tss, start, end


def select_targets(protein_genes: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible: list[dict[str, Any]] = []
    for gene in protein_genes:
        if gene["chromosome"] not in PRIMARY_CHROMOSOMES:
            continue
        if gene["chromosome"] in DEVELOPMENT_TARGET_CHROMOSOMES:
            continue
        tss, start, end = promoter_region(gene)
        if end - start + 1 != 2501:
            continue
        eligible.append(
            {
                **gene,
                "tss": tss,
                "region_start": start,
                "region_end": end,
                "region_length_bp": 2501,
                "selection_hash": seeded_key(stable_id(gene["gene_id"]), gene["chromosome"]),
            }
        )
    eligible.sort(key=lambda row: (row["selection_hash"], row["gene_id"]))
    if not eligible:
        raise ValueError("no eligible protein-coding promoter targets")
    selected = [eligible[0]]
    for row in eligible[1:]:
        if row["chromosome"] != selected[0]["chromosome"]:
            selected.append(row)
            break
    if len(selected) != 2:
        raise ValueError("fewer than two eligible promoter targets on distinct chromosomes")
    for index, row in enumerate(selected, 1):
        row["target_id"] = f"ht{index:02d}"
    return selected


def select_command(args: argparse.Namespace) -> None:
    transcript_metadata, protein_genes = parse_annotation(args.annotation_gtf)
    exclusions = read_exclusions(args.development_exclusions)
    queries = select_queries(args.lncrna_fasta, transcript_metadata, exclusions)
    targets = select_targets(protein_genes)
    payload = {
        "schema_version": 1,
        "selection_seed": SELECTION_SEED,
        "assembly": ASSEMBLY,
        "annotation_release": ANNOTATION_RELEASE,
        "source_digests": {
            "lncrna_fasta_sha256": sha256_file(args.lncrna_fasta),
            "annotation_gtf_sha256": sha256_file(args.annotation_gtf),
            "development_exclusions_sha256": sha256_file(args.development_exclusions),
        },
        "query_selection_rule": (
            "primary-chromosome canonical ACGT GENCODE lncRNA transcripts; one per gene by "
            "annotation level, basic tag, descending eligible length and transcript ID; four per "
            "fixed length stratum by seeded SHA-256"
        ),
        "target_selection_rule": (
            "protein-coding promoters on primary chromosomes excluding chr11/chr21/chr22; "
            "seeded SHA-256 order with distinct chromosomes; strand-aware TSS window -2000/+500"
        ),
        "queries": queries,
        "targets": targets,
    }
    atomic_json(args.output, payload)
    print(f"selected_queries={len(queries)}")
    print(f"selected_targets={len(targets)}")


def fasta_text(header: str, sequence: str) -> str:
    lines = [f">{header}"]
    lines.extend(sequence[index : index + 80] for index in range(0, len(sequence), 80))
    return "\n".join(lines) + "\n"


def manifest_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return str(resolved)


def read_single_chromosome(path: Path, expected_name: str) -> str:
    records = parse_fasta(path)
    if len(records) != 1:
        raise ValueError(f"chromosome FASTA must contain one record: {path}")
    header, sequence = records[0]
    if header.split()[0] != expected_name:
        raise ValueError(f"expected chromosome {expected_name}, found {header}")
    return sequence


def write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "workload_id",
        "query_id",
        "gene_id",
        "gene_name",
        "transcript_id",
        "query_length_nt",
        "length_stratum",
        "query_sequence_sha256",
        "query_file_sha256",
        "query_path",
        "target_id",
        "target_gene_id",
        "target_gene_name",
        "target_chromosome",
        "target_strand",
        "target_tss",
        "target_region_start",
        "target_region_end",
        "target_length_bp",
        "target_sequence_sha256",
        "target_file_sha256",
        "target_path",
        "assembly",
        "annotation_release",
        "selection_seed",
        "requested_contract",
        "run_modes",
        "repeat_count",
        "status",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.partial.{os.getpid()}"
    try:
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def materialize_command(args: argparse.Namespace) -> None:
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    if selection.get("schema_version") != 1:
        raise ValueError("unsupported selection schema version")
    fasta_by_transcript = {
        header.split("|", 1)[0]: sequence for header, sequence in parse_fasta(args.lncrna_fasta)
    }
    args.output_root.parent.mkdir(parents=True, exist_ok=True)
    staging_root = Path(
        tempfile.mkdtemp(
            prefix=f".{args.output_root.name}.staging.",
            dir=args.output_root.parent,
        )
    )
    staged_output_root = staging_root / "artifacts"
    staged_manifest = staging_root / "holdout_manifest.tsv"
    staged_manifest_sha256 = staging_root / "holdout_manifest.sha256"
    query_dir = staged_output_root / "queries"
    target_dir = staged_output_root / "targets"

    try:
        query_dir.mkdir(parents=True)
        target_dir.mkdir(parents=True)
        query_artifacts: list[dict[str, Any]] = []
        representative_queries: set[str] = set()
        seen_strata: set[str] = set()
        query_ids: set[str] = set()
        expected_artifacts: set[str] = set()
        for row in selection["queries"]:
            transcript_id = row["transcript_id"]
            if row["query_id"] in query_ids:
                raise ValueError(f"duplicate selected query ID: {row['query_id']}")
            query_ids.add(row["query_id"])
            sequence = fasta_by_transcript.get(transcript_id)
            if sequence is None or sequence_sha256(sequence) != row["sequence_sha256"]:
                raise ValueError(f"selected query digest is unavailable or drifted: {transcript_id}")
            if set(sequence) - set("ACGT"):
                raise ValueError(f"selected query is not canonical ACGT: {transcript_id}")
            filename = f"{row['query_id']}_{stable_id(row['gene_id'])}_{stable_id(transcript_id)}.fa"
            path = query_dir / filename
            atomic_text(
                path,
                fasta_text(
                    f"{transcript_id}|{row['gene_id']}|{row['gene_name']}|{ANNOTATION_RELEASE}|{ASSEMBLY}",
                    sequence,
                ),
            )
            expected_artifacts.add(f"queries/{filename}")
            if row["length_stratum"] not in seen_strata:
                representative_queries.add(row["query_id"])
                seen_strata.add(row["length_stratum"])
            query_artifacts.append(
                {
                    **row,
                    "query_path": manifest_path(args.output_root / "queries" / filename),
                    "query_file_sha256": sha256_file(path),
                }
            )

        chromosome_cache: dict[str, str] = {}
        target_artifacts: list[dict[str, Any]] = []
        target_ids: set[str] = set()
        for row in selection["targets"]:
            if row["target_id"] in target_ids:
                raise ValueError(f"duplicate selected target ID: {row['target_id']}")
            target_ids.add(row["target_id"])
            chromosome = row["chromosome"]
            chromosome_path = args.chromosome_dir / f"{chromosome}.fa"
            chromosome_sequence = chromosome_cache.setdefault(
                chromosome, read_single_chromosome(chromosome_path, chromosome)
            )
            start = int(row["region_start"])
            end = int(row["region_end"])
            if start < 1 or end > len(chromosome_sequence):
                raise ValueError(f"target region is outside {chromosome}: {start}-{end}")
            sequence = chromosome_sequence[start - 1 : end]
            if len(sequence) != row["region_length_bp"] or set(sequence) - set("ACGT"):
                raise ValueError(f"target region is not a canonical {row['region_length_bp']}-bp scope")
            filename = f"{row['target_id']}_{stable_id(row['gene_id'])}_{chromosome}_{start}_{end}.fa"
            path = target_dir / filename
            atomic_text(
                path,
                fasta_text(
                    f"{ASSEMBLY}|{chromosome}|{start}-{end}|{row['gene_id']}|promoter_forward_genomic",
                    sequence,
                ),
            )
            expected_artifacts.add(f"targets/{filename}")
            target_artifacts.append(
                {
                    **row,
                    "target_sequence_sha256": sequence_sha256(sequence),
                    "target_file_sha256": sha256_file(path),
                    "target_path": manifest_path(args.output_root / "targets" / filename),
                }
            )

        actual_artifacts = {
            path.relative_to(staged_output_root).as_posix()
            for path in staged_output_root.rglob("*")
            if path.is_file()
        }
        if actual_artifacts != expected_artifacts:
            raise ValueError("staged holdout artifact tree is not the exact selected file set")

        rows: list[dict[str, Any]] = []
        for query in query_artifacts:
            for target in target_artifacts:
                rows.append(
                    {
                        "workload_id": f"{query['query_id']}_{target['target_id']}",
                        "query_id": query["query_id"],
                        "gene_id": query["gene_id"],
                        "gene_name": query["gene_name"],
                        "transcript_id": query["transcript_id"],
                        "query_length_nt": query["sequence_length_nt"],
                        "length_stratum": query["length_stratum"],
                        "query_sequence_sha256": query["sequence_sha256"],
                        "query_file_sha256": query["query_file_sha256"],
                        "query_path": query["query_path"],
                        "target_id": target["target_id"],
                        "target_gene_id": target["gene_id"],
                        "target_gene_name": target["gene_name"],
                        "target_chromosome": target["chromosome"],
                        "target_strand": target["strand"],
                        "target_tss": target["tss"],
                        "target_region_start": target["region_start"],
                        "target_region_end": target["region_end"],
                        "target_length_bp": target["region_length_bp"],
                        "target_sequence_sha256": target["target_sequence_sha256"],
                        "target_file_sha256": target["target_file_sha256"],
                        "target_path": target["target_path"],
                        "assembly": ASSEMBLY,
                        "annotation_release": ANNOTATION_RELEASE,
                        "selection_seed": SELECTION_SEED,
                        "requested_contract": "all-ranked-top5",
                        "run_modes": "authority,candidate,verified",
                        "repeat_count": 3 if query["query_id"] in representative_queries else 1,
                        "status": "preregistered_not_run",
                    }
                )
        if len({row["workload_id"] for row in rows}) != len(rows):
            raise ValueError("staged manifest workload IDs are not unique")
        write_manifest(staged_manifest, rows)
        atomic_text(
            staged_manifest_sha256,
            f"{sha256_file(staged_manifest)}  {args.manifest.name}\n",
        )

        require_existing_match(args.output_root, staged_output_root, "holdout artifact tree")
        require_existing_match(args.manifest, staged_manifest, "holdout manifest")
        require_existing_match(
            args.manifest_sha256,
            staged_manifest_sha256,
            "holdout manifest checksum",
        )

        if not path_exists(args.output_root):
            os.replace(staged_output_root, args.output_root)
        publish_file_if_missing(staged_manifest, args.manifest)
        publish_file_if_missing(staged_manifest_sha256, args.manifest_sha256)
        print(f"manifest_workloads={len(rows)}")
        print(f"manifest_queries={len(query_artifacts)}")
        print(f"manifest_targets={len(target_artifacts)}")
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Build the preregistered Phase 2 holdout panel.")
    subparsers = result.add_subparsers(dest="command", required=True)

    select = subparsers.add_parser("select", help="Select query transcripts and promoter targets.")
    select.add_argument("--lncrna-fasta", type=Path, required=True)
    select.add_argument("--annotation-gtf", type=Path, required=True)
    select.add_argument("--development-exclusions", type=Path, required=True)
    select.add_argument("--output", type=Path, required=True)

    materialize = subparsers.add_parser("materialize", help="Write FASTA inputs and workload manifest.")
    materialize.add_argument("--selection", type=Path, required=True)
    materialize.add_argument("--lncrna-fasta", type=Path, required=True)
    materialize.add_argument("--chromosome-dir", type=Path, required=True)
    materialize.add_argument("--output-root", type=Path, required=True)
    materialize.add_argument("--manifest", type=Path, required=True)
    materialize.add_argument("--manifest-sha256", type=Path, required=True)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "select":
            select_command(args)
        else:
            materialize_command(args)
    except (OSError, UnicodeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"holdout panel build failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
