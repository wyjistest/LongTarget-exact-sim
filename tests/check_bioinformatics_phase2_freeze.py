#!/usr/bin/env python3
from __future__ import annotations

import csv
import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from gasal2_longtarget import validate_schema_value  # noqa: E402


SELECTION_SEED = "gasal2-longtarget-phase2-holdout-v1-20260724"
QUERY_STRATA = (
    ("le_800", 200, 800),
    ("801_1600", 801, 1600),
    ("1601_2812", 1601, 2812),
)
PRIMARY_CHROMOSOMES = {f"chr{index}" for index in range(1, 23)} | {"chrX"}
DEVELOPMENT_TARGET_CHROMOSOMES = {"chr11", "chr21", "chr22"}
SOURCE_AUTHORITIES = {
    "gencode_v49_lncrna": {
        "role": "lncRNA transcript sequences",
        "provider": "GENCODE",
        "release": "v49",
        "assembly": "GRCh38.p14",
        "url": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.lncRNA_transcripts.fa.gz",
        "upstream_checksum_algorithm": "MD5",
        "upstream_checksum": "6d52ea2c72933c864e46a560fe0b5d4c",
        "local_source_path": ".tmp/bioinformatics_holdout_sources/gencode.v49.lncRNA_transcripts.fa.gz",
        "size_bytes": "37870043",
        "sha256": "1f04e509309fa74b694ef3cc1e52c1c8173bb0e679f8a22785fa43ecadd28ef4",
    },
    "gencode_v49_gtf": {
        "role": "gene and transcript annotation",
        "provider": "GENCODE",
        "release": "v49",
        "assembly": "GRCh38.p14",
        "url": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.annotation.gtf.gz",
        "upstream_checksum_algorithm": "MD5",
        "upstream_checksum": "0ef4a024ea2d35b1b88c12447b0b70b9",
        "local_source_path": ".tmp/bioinformatics_holdout_sources/gencode.v49.annotation.gtf.gz",
        "size_bytes": "93374019",
        "sha256": "d6e6fe0515c95b2a8cd36a853c1989cee9115c736c60237c56ae92b9daaaf7c4",
    },
    "ucsc_hg38_chr1": {
        "role": "forward genomic reference sequence",
        "provider": "UCSC Genome Browser / Genome Reference Consortium",
        "release": "hg38 2014-01-23",
        "assembly": "GRCh38",
        "url": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr1.fa.gz",
        "upstream_checksum_algorithm": "MD5 of gzip",
        "upstream_checksum": "f069c41e7cc8c2d3a7655cbb2d4186b8",
        "local_source_path": ".tmp/bioinformatics_holdout_sources/chromosomes/chr1.fa",
        "size_bytes": "253935557",
        "sha256": "04ee6db2e94ccc4daddc168453189d8c17a01454ba67ac0443a73a0401408ee0",
    },
    "ucsc_hg38_chr9": {
        "role": "forward genomic reference sequence",
        "provider": "UCSC Genome Browser / Genome Reference Consortium",
        "release": "hg38 2014-01-23",
        "assembly": "GRCh38",
        "url": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr9.fa.gz",
        "upstream_checksum_algorithm": "MD5 of gzip",
        "upstream_checksum": "f7e98217b35f5a7451f1166196b4b33c",
        "local_source_path": ".tmp/bioinformatics_holdout_sources/chromosomes/chr9.fa",
        "size_bytes": "141162618",
        "sha256": "2a7cc20841202497a89700a4e6f9a342f138bad761fab64c673fa95d3f773a1f",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def stable_id(value: str) -> str:
    return value.split(".", 1)[0]


def frozen_selection_hash(*values: str) -> str:
    encoded = "|".join((SELECTION_SEED, *values)).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_selection_semantics(selection: dict[str, object]) -> None:
    require(selection["selection_seed"] == SELECTION_SEED, "selection seed drift")
    require(selection["assembly"] == "GRCh38", "selection assembly drift")
    require(selection["annotation_release"] == "GENCODE v49", "selection annotation drift")
    queries = selection["queries"]
    targets = selection["targets"]
    require(isinstance(queries, list) and len(queries) == 12, "selection must contain 12 queries")
    require(isinstance(targets, list) and len(targets) == 2, "selection must contain two targets")
    require(
        [row["query_id"] for row in queries] == [f"hq{index:02d}" for index in range(1, 13)],
        "selection query IDs or order drifted",
    )
    expected_strata = [name for name, _, _ in QUERY_STRATA for _ in range(4)]
    require(
        [row["length_stratum"] for row in queries] == expected_strata,
        "selection query strata are not the ordered 4/4/4 groups",
    )
    bounds = {name: (minimum, maximum) for name, minimum, maximum in QUERY_STRATA}
    for row in queries:
        require(
            row["chromosome"] in PRIMARY_CHROMOSOMES,
            f"selected query chromosome is not primary: {row['query_id']}",
        )
        length = row["sequence_length_nt"]
        minimum, maximum = bounds[row["length_stratum"]]
        require(
            isinstance(length, int) and not isinstance(length, bool) and minimum <= length <= maximum,
            f"query length is outside declared stratum: {row['query_id']}",
        )
        sequence_digest = row["sequence_sha256"]
        require(
            isinstance(sequence_digest, str)
            and len(sequence_digest) == 64
            and set(sequence_digest) <= set("0123456789abcdef"),
            f"query sequence digest is invalid: {row['query_id']}",
        )
        expected_hash = frozen_selection_hash(
            stable_id(row["gene_id"]),
            stable_id(row["transcript_id"]),
            sequence_digest,
        )
        require(row["selection_hash"] == expected_hash, f"query selection hash drift: {row['query_id']}")
    for offset in range(0, 12, 4):
        group = queries[offset : offset + 4]
        keys = [(row["selection_hash"], row["gene_id"]) for row in group]
        require(keys == sorted(keys), f"query selection order drift in {group[0]['length_stratum']}")

    require(
        [row["target_id"] for row in targets] == ["ht01", "ht02"],
        "selection target IDs or order drifted",
    )
    require(
        len({row["chromosome"] for row in targets}) == 2,
        "selected targets are not on distinct chromosomes",
    )
    target_keys: list[tuple[str, str]] = []
    for row in targets:
        chromosome = row["chromosome"]
        require(
            chromosome in PRIMARY_CHROMOSOMES
            and chromosome not in DEVELOPMENT_TARGET_CHROMOSOMES,
            f"selected target chromosome is outside the holdout scope: {row['target_id']}",
        )
        expected_hash = frozen_selection_hash(stable_id(row["gene_id"]), chromosome)
        require(row["selection_hash"] == expected_hash, f"target selection hash drift: {row['target_id']}")
        target_keys.append((row["selection_hash"], row["gene_id"]))
        require(row["strand"] in {"+", "-"}, f"target strand is invalid: {row['target_id']}")
        expected_tss = row["start"] if row["strand"] == "+" else row["end"]
        require(row["tss"] == expected_tss, f"target TSS geometry drift: {row['target_id']}")
        if row["strand"] == "+":
            expected_start = max(1, expected_tss - 2000)
            expected_end = expected_tss + 500
        else:
            expected_start = max(1, expected_tss - 500)
            expected_end = expected_tss + 2000
        require(
            row["region_start"] == expected_start and row["region_end"] == expected_end,
            f"target promoter window geometry drift: {row['target_id']}",
        )
        require(
            row["region_length_bp"] == 2501
            and row["region_end"] - row["region_start"] + 1 == 2501,
            f"target promoter length drift: {row['target_id']}",
        )
    require(target_keys == sorted(target_keys), "target seeded selection order drift")


def parse_single_canonical_fasta(path: Path) -> tuple[str, str]:
    lines = path.read_text(encoding="ascii").splitlines()
    require(bool(lines), f"empty FASTA: {path}")
    require(lines[0].startswith(">") and len(lines[0]) > 1, f"invalid FASTA header: {path}")
    require(all(not line.startswith(">") for line in lines[1:]), f"multiple FASTA records: {path}")
    require(all(line and line == line.strip() for line in lines[1:]), f"invalid FASTA line: {path}")
    sequence = "".join(lines[1:])
    require(bool(sequence) and not (set(sequence) - set("ACGT")), f"non-canonical FASTA: {path}")
    return lines[0][1:], sequence


def parse_manifest_checksum(root: Path) -> tuple[str, str]:
    checksum_path = root / "paper/bioinformatics/holdout_manifest.sha256"
    parts = checksum_path.read_text(encoding="ascii").strip().split("  ", 1)
    require(len(parts) == 2, "holdout manifest checksum must use sha256sum format")
    digest, name = parts
    require(name == "holdout_manifest.tsv", "holdout manifest checksum names the wrong file")
    require(len(digest) == 64 and set(digest) <= set("0123456789abcdef"), "invalid manifest digest")
    manifest = root / "paper/bioinformatics/holdout_manifest.tsv"
    require(digest == sha256(manifest), "holdout manifest digest drift")
    return digest, f"bioinformatics-phase2-holdout-v1-{digest[:8]}"


def manifest_rows_by_id(
    rows: list[dict[str, str]], field: str
) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        result.setdefault(row[field], []).append(row)
    return result


def validate_manifest_and_inputs(root: Path, selection: dict[str, object]) -> None:
    manifest_path = root / "paper/bioinformatics/holdout_manifest.tsv"
    rows = read_tsv(manifest_path)
    queries = selection["queries"]
    targets = selection["targets"]
    require(isinstance(queries, list) and len(queries) == 12, "selection must contain 12 queries")
    require(isinstance(targets, list) and len(targets) == 2, "selection must contain two targets")

    query_by_id = {row["query_id"]: row for row in queries}
    target_by_id = {row["target_id"]: row for row in targets}
    require(len(query_by_id) == len(queries), "selection query IDs are not unique")
    require(len(target_by_id) == len(targets), "selection target IDs are not unique")
    require(
        len({stable_id(row["gene_id"]) for row in queries}) == len(queries),
        "selection contains more than one query per stable gene",
    )

    expected_pairs = {
        (query_id, target_id)
        for query_id in query_by_id
        for target_id in target_by_id
    }
    actual_pairs = [(row["query_id"], row["target_id"]) for row in rows]
    require(len(rows) == len(expected_pairs) == 24, "manifest must contain the 12x2 matrix")
    require(len(set(actual_pairs)) == len(actual_pairs), "manifest query-target pairs are not unique")
    require(set(actual_pairs) == expected_pairs, "manifest is not the exact query-target Cartesian product")
    workload_ids = [row["workload_id"] for row in rows]
    require(len(set(workload_ids)) == len(workload_ids), "manifest workload IDs are not unique")
    require(
        all(row["workload_id"] == f"{row['query_id']}_{row['target_id']}" for row in rows),
        "manifest workload ID does not match its query-target pair",
    )

    rows_by_query = manifest_rows_by_id(rows, "query_id")
    rows_by_target = manifest_rows_by_id(rows, "target_id")
    input_root = root / "reproduce/bioinformatics/holdout_inputs"
    expected_files: set[str] = set()
    representative_queries: set[str] = set()
    seen_strata: set[str] = set()
    exclusions = read_tsv(root / "paper/bioinformatics/development_query_exclusions.tsv")
    require(
        len({(row["exclusion_type"], row["value"]) for row in exclusions}) == len(exclusions),
        "development exclusions contain duplicates",
    )
    require(
        all(
            row["exclusion_type"] in {"gene_id", "gene_name", "sequence_sha256"}
            and row["value"]
            and row["reason"].strip()
            for row in exclusions
        ),
        "development exclusions contain an invalid row",
    )
    excluded_ids = {row["value"] for row in exclusions if row["exclusion_type"] == "gene_id"}
    excluded_names = {row["value"] for row in exclusions if row["exclusion_type"] == "gene_name"}
    excluded_digests = {
        row["value"] for row in exclusions if row["exclusion_type"] == "sequence_sha256"
    }

    for query in queries:
        query_id = query["query_id"]
        if query["length_stratum"] not in seen_strata:
            representative_queries.add(query_id)
            seen_strata.add(query["length_stratum"])
        expected_relative = (
            "reproduce/bioinformatics/holdout_inputs/queries/"
            f"{query_id}_{stable_id(query['gene_id'])}_{stable_id(query['transcript_id'])}.fa"
        )
        expected_files.add(str(Path(expected_relative).relative_to("reproduce/bioinformatics/holdout_inputs")))
        query_rows = rows_by_query.get(query_id, [])
        require(len(query_rows) == len(targets), f"manifest query multiplicity drift: {query_id}")
        expected = {
            "gene_id": str(query["gene_id"]),
            "gene_name": str(query["gene_name"]),
            "transcript_id": str(query["transcript_id"]),
            "query_length_nt": str(query["sequence_length_nt"]),
            "length_stratum": str(query["length_stratum"]),
            "query_sequence_sha256": str(query["sequence_sha256"]),
            "query_path": expected_relative,
        }
        for row in query_rows:
            require(all(row[field] == value for field, value in expected.items()), f"query metadata drift: {query_id}")
        path = root / expected_relative
        require(path.is_file() and not path.is_symlink(), f"missing regular query FASTA: {query_id}")
        header, sequence = parse_single_canonical_fasta(path)
        require(len(sequence) == query["sequence_length_nt"], f"query length drift: {query_id}")
        require(
            hashlib.sha256(sequence.encode("ascii")).hexdigest() == query["sequence_sha256"],
            f"query normalized digest drift: {query_id}",
        )
        require(all(row["query_file_sha256"] == sha256(path) for row in query_rows), f"query file digest drift: {query_id}")
        require(
            header
            == f"{query['transcript_id']}|{query['gene_id']}|{query['gene_name']}|{selection['annotation_release']}|{selection['assembly']}",
            f"query FASTA header drift: {query_id}",
        )
        require(stable_id(query["gene_id"]) not in excluded_ids, f"excluded query gene selected: {query_id}")
        require(query["gene_name"] not in excluded_names, f"excluded query name selected: {query_id}")
        require(query["sequence_sha256"] not in excluded_digests, f"excluded query digest selected: {query_id}")

    stratum_counts: dict[str, int] = {}
    for query in queries:
        stratum_counts[query["length_stratum"]] = stratum_counts.get(query["length_stratum"], 0) + 1
    require(stratum_counts == {"le_800": 4, "801_1600": 4, "1601_2812": 4}, "query strata drift")

    for target in targets:
        target_id = target["target_id"]
        expected_relative = (
            "reproduce/bioinformatics/holdout_inputs/targets/"
            f"{target_id}_{stable_id(target['gene_id'])}_{target['chromosome']}_"
            f"{target['region_start']}_{target['region_end']}.fa"
        )
        expected_files.add(str(Path(expected_relative).relative_to("reproduce/bioinformatics/holdout_inputs")))
        target_rows = rows_by_target.get(target_id, [])
        require(len(target_rows) == len(queries), f"manifest target multiplicity drift: {target_id}")
        expected = {
            "target_gene_id": str(target["gene_id"]),
            "target_gene_name": str(target["gene_name"]),
            "target_chromosome": str(target["chromosome"]),
            "target_strand": str(target["strand"]),
            "target_tss": str(target["tss"]),
            "target_region_start": str(target["region_start"]),
            "target_region_end": str(target["region_end"]),
            "target_length_bp": str(target["region_length_bp"]),
            "target_path": expected_relative,
        }
        for row in target_rows:
            require(all(row[field] == value for field, value in expected.items()), f"target metadata drift: {target_id}")
        path = root / expected_relative
        require(path.is_file() and not path.is_symlink(), f"missing regular target FASTA: {target_id}")
        header, sequence = parse_single_canonical_fasta(path)
        require(len(sequence) == target["region_length_bp"], f"target length drift: {target_id}")
        sequence_digest = hashlib.sha256(sequence.encode("ascii")).hexdigest()
        require(all(row["target_sequence_sha256"] == sequence_digest for row in target_rows), f"target normalized digest drift: {target_id}")
        require(all(row["target_file_sha256"] == sha256(path) for row in target_rows), f"target file digest drift: {target_id}")
        require(
            header
            == f"{selection['assembly']}|{target['chromosome']}|{target['region_start']}-{target['region_end']}|{target['gene_id']}|promoter_forward_genomic",
            f"target FASTA header drift: {target_id}",
        )

    actual_files: set[str] = set()
    for path in input_root.rglob("*"):
        require(not path.is_symlink(), f"holdout input tree contains a symbolic link: {path}")
        require(path.is_dir() or path.is_file(), f"holdout input tree contains a special file: {path}")
        if path.is_file():
            actual_files.add(path.relative_to(input_root).as_posix())
    require(actual_files == expected_files, "holdout input file set contains a missing or stale artifact")

    for row in rows:
        require(row["assembly"] == selection["assembly"], "manifest assembly drift")
        require(row["annotation_release"] == selection["annotation_release"], "manifest annotation drift")
        require(row["selection_seed"] == selection["selection_seed"], "manifest selection seed drift")
        require(row["requested_contract"] == "all-ranked-top5", "manifest contract drift")
        require(row["run_modes"] == "authority,candidate,verified", "manifest run-mode drift")
        require(row["status"] == "preregistered_not_run", "holdout execution state is not frozen")
        expected_repeat = "3" if row["query_id"] in representative_queries else "1"
        require(row["repeat_count"] == expected_repeat, "manifest representative-repeat drift")


def fetcher_pins(fetch_text: str) -> dict[str, tuple[str, str, str]]:
    logical = fetch_text.replace("\\\n", " ")
    gencode_base_match = re.search(r'^GENCODE_BASE="([^"]+)"$', fetch_text, re.MULTILINE)
    ucsc_base_match = re.search(r'^UCSC_BASE="([^"]+)"$', fetch_text, re.MULTILINE)
    require(gencode_base_match is not None and ucsc_base_match is not None, "fetcher source bases are missing")
    pins: dict[str, tuple[str, str, str]] = {}
    for match in re.finditer(
        r'download\s+"\$GENCODE_BASE/([^"]+)"\s+"\$SOURCE_DIR/[^"]+"\s+"([0-9a-f]+)"\s+"([0-9a-f]+)"\s+"([0-9]+)"',
        logical,
    ):
        url = f"{gencode_base_match.group(1)}/{match.group(1)}"
        pins[url] = (match.group(2), match.group(3), match.group(4))
    for match in re.finditer(
        r'download_chromosome\s+(\S+)\s+"([0-9a-f]+)"\s+"([0-9a-f]+)"\s+"([0-9]+)"',
        logical,
    ):
        url = f"{ucsc_base_match.group(1)}/{match.group(1)}"
        pins[url] = (match.group(2), match.group(3), match.group(4))
    return pins


def validate_sources(root: Path, selection: dict[str, object]) -> None:
    rows = read_tsv(root / "paper/bioinformatics/holdout_sources.tsv")
    required_ids = {"gencode_v49_lncrna", "gencode_v49_gtf"} | {
        f"ucsc_hg38_{target['chromosome']}" for target in selection["targets"]
    }
    by_id = {row["source_id"]: row for row in rows}
    require(len(by_id) == len(rows) and set(by_id) == required_ids, "source ledger row set drift")
    require(set(by_id) == set(SOURCE_AUTHORITIES), "source ledger does not contain the four authorities")
    for row in rows:
        expected = SOURCE_AUTHORITIES[row["source_id"]]
        require(
            all(row[field] == value for field, value in expected.items()),
            f"source authority metadata drift: {row['source_id']}",
        )
        require(row["status"] == "verified", f"unverified source ledger row: {row['source_id']}")
        require(row["url"].startswith("https://"), f"non-HTTPS source URL: {row['source_id']}")
        require(len(row["sha256"]) == 64 and set(row["sha256"]) <= set("0123456789abcdef"), f"invalid source digest: {row['source_id']}")
        require(int(row["size_bytes"]) > 0, f"invalid source size: {row['source_id']}")
        require(all(row[field].strip() for field in ("license_or_terms", "redistribution_note", "download_command")), f"incomplete source attribution: {row['source_id']}")

    protocol = (root / "paper/bioinformatics/holdout_protocol.md").read_text(encoding="utf-8")
    require("GENCODE v49" in protocol and "GRCh38.p14" in protocol, "protocol GENCODE authority drift")
    require("UCSC hg38" in protocol and "GRCh38" in protocol, "protocol UCSC authority drift")
    require(
        selection["annotation_release"] == "GENCODE v49" and selection["assembly"] == "GRCh38",
        "selection authority metadata drift",
    )

    source_digests = selection["source_digests"]
    require(
        by_id["gencode_v49_lncrna"]["sha256"] == source_digests["lncrna_fasta_sha256"],
        "selection/source-ledger lncRNA digest drift",
    )
    require(
        by_id["gencode_v49_gtf"]["sha256"] == source_digests["annotation_gtf_sha256"],
        "selection/source-ledger annotation digest drift",
    )
    require(
        source_digests["development_exclusions_sha256"]
        == sha256(root / "paper/bioinformatics/development_query_exclusions.tsv"),
        "selection/exclusion-ledger digest drift",
    )

    fetch_text = (root / "reproduce/bioinformatics/fetch_holdout_inputs.sh").read_text(encoding="utf-8")
    pins = fetcher_pins(fetch_text)
    require(set(pins) == {row["url"] for row in rows}, "fetcher URL pins drift from source ledger")
    for row in rows:
        require(
            pins[row["url"]]
            == (row["upstream_checksum"], row["sha256"], row["size_bytes"]),
            f"fetcher checksum or size pin drift: {row['source_id']}",
        )


def validate_contract_registry(
    schema: dict[str, object],
    registry: dict[str, object],
    freeze_id: str,
    query_count: int,
    workload_count: int,
) -> None:
    validate_schema_value(schema, registry, "registry")

    def require_meaningful_strings(value: object, path: str) -> None:
        if isinstance(value, str):
            require(bool(value.strip()), f"blank registry string: {path}")
        elif isinstance(value, dict):
            for field, child in value.items():
                require_meaningful_strings(child, f"{path}.{field}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                require_meaningful_strings(child, f"{path}[{index}]")

    require_meaningful_strings(registry, "registry")
    expected_contract_ids = {"score_top5_v1", "all_ranked_top5_v1", "full_output_v1"}
    contracts = registry["contracts"]
    contract_ids = [row["contract_id"] for row in contracts]
    require(len(contract_ids) == 3 and set(contract_ids) == expected_contract_ids, "registry must contain exactly the three unique contract IDs")
    require(registry["registry_state"] == "pre_holdout_freeze", "registry is not in pre-holdout state")
    require(registry["holdout_freeze_id"] == freeze_id, "registry holdout freeze ID drift")
    for contract in contracts:
        require(contract["status"] == "experimental", "pre-holdout contract is not experimental")
        require(contract["output_definition"].strip(), "contract output definition is blank")
        require(all(value.strip() for value in contract["known_limitations"]), "contract limitation is blank")
        require(all(value.strip() for value in contract["runtime_guards"]["compute_capability"]), "compute capability is blank")
        datasets = contract["validation_datasets"]
        by_role = {dataset["role"]: dataset for dataset in datasets}
        require(len(by_role) == len(datasets) == 2, "contract validation dataset roles are not unique")
        require(set(by_role) == {"development", "independent_holdout"}, "contract dataset roles drift")
        development = by_role["development"]
        holdout = by_role["independent_holdout"]
        require(development["dataset_id"] == registry["paper_data_freeze"], "development dataset freeze drift")
        require(development["status"] == "complete", "development dataset is not complete")
        require(development["query_count"] == 5 and development["workload_count"] == 13, "development dataset counts drift")
        require(holdout["dataset_id"] == freeze_id, "holdout dataset freeze drift")
        require(holdout["status"] == "preregistered_not_run", "holdout registry status is not preregistered")
        require(holdout["query_count"] == query_count and holdout["workload_count"] == workload_count, "holdout registry counts drift")

        counts = contract["clean_mismatch_counts"]
        development_counts = counts["development"]
        require(development_counts["clean"] + development_counts["mismatch"] == 13, "development contract counts drift")
        for rank_counts in development_counts["rank_counts"].values():
            require(rank_counts["clean"] + rank_counts["mismatch"] == 13, "development rank counts drift")
        holdout_counts = counts["holdout"]
        holdout_values = [holdout_counts["clean"], holdout_counts["mismatch"]]
        for rank_counts in holdout_counts["rank_counts"].values():
            holdout_values.extend((rank_counts["clean"], rank_counts["mismatch"]))
        require(all(value is None for value in holdout_values), "preregistered holdout counts must remain null")


def validate_phase2_freeze(root: Path) -> None:
    selection = json.loads(
        (root / "paper/bioinformatics/holdout_selection.json").read_text(encoding="utf-8")
    )
    require(selection["schema_version"] == 1, "unsupported holdout selection schema")
    validate_selection_semantics(selection)
    validate_manifest_and_inputs(root, selection)
    validate_sources(root, selection)
    digest, freeze_id = parse_manifest_checksum(root)
    protocol = (root / "paper/bioinformatics/holdout_protocol.md").read_text(encoding="utf-8")
    require(digest in protocol, "protocol does not record the full manifest digest")
    require(freeze_id in protocol, "protocol freeze ID drift")
    require(selection["selection_seed"] in protocol, "protocol selection seed drift")
    schema = json.loads(
        (root / "schemas/gasal2_longtarget_contracts.schema.json").read_text(encoding="utf-8")
    )
    registry = json.loads(
        (root / "config/gasal2_longtarget_contracts.json").read_text(encoding="utf-8")
    )
    validate_contract_registry(schema, registry, freeze_id, len(selection["queries"]), 24)


class BioinformaticsPhase2FreezeTests(unittest.TestCase):
    @contextlib.contextmanager
    def freeze_fixture(self):
        global ROOT
        fixture_paths = (
            "config/gasal2_longtarget_contracts.json",
            "schemas/gasal2_longtarget_contracts.schema.json",
            "paper/bioinformatics/development_query_exclusions.tsv",
            "paper/bioinformatics/holdout_selection.json",
            "paper/bioinformatics/holdout_manifest.tsv",
            "paper/bioinformatics/holdout_manifest.sha256",
            "paper/bioinformatics/holdout_sources.tsv",
            "paper/bioinformatics/holdout_protocol.md",
            "reproduce/bioinformatics/fetch_holdout_inputs.sh",
            "reproduce/bioinformatics/holdout_inputs",
        )
        with tempfile.TemporaryDirectory(prefix="bioinformatics-phase2-freeze-") as temp_name:
            fixture_root = Path(temp_name)
            for relative in fixture_paths:
                source = ROOT / relative
                destination = fixture_root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                if source.is_dir():
                    shutil.copytree(source, destination)
                else:
                    shutil.copy2(source, destination)
            previous_root = ROOT
            ROOT = fixture_root
            try:
                yield fixture_root
            finally:
                ROOT = previous_root

    def rewrite_manifest_checksum(self, root: Path) -> None:
        manifest = root / "paper/bioinformatics/holdout_manifest.tsv"
        checksum = root / "paper/bioinformatics/holdout_manifest.sha256"
        checksum.write_text(f"{sha256(manifest)}  holdout_manifest.tsv\n", encoding="utf-8")

    def refreeze_fixture(self, root: Path) -> None:
        checksum = root / "paper/bioinformatics/holdout_manifest.sha256"
        old_digest = checksum.read_text(encoding="ascii").split()[0]
        old_freeze_id = f"bioinformatics-phase2-holdout-v1-{old_digest[:8]}"
        self.rewrite_manifest_checksum(root)
        new_digest = checksum.read_text(encoding="ascii").split()[0]
        new_freeze_id = f"bioinformatics-phase2-holdout-v1-{new_digest[:8]}"

        protocol_path = root / "paper/bioinformatics/holdout_protocol.md"
        protocol = protocol_path.read_text(encoding="utf-8")
        protocol_path.write_text(
            protocol.replace(old_digest, new_digest).replace(old_freeze_id, new_freeze_id),
            encoding="utf-8",
        )
        registry_path = root / "config/gasal2_longtarget_contracts.json"
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["holdout_freeze_id"] = new_freeze_id
        for contract in registry["contracts"]:
            for dataset in contract["validation_datasets"]:
                if dataset["role"] == "independent_holdout":
                    dataset["dataset_id"] = new_freeze_id
        registry_path.write_text(json.dumps(registry), encoding="utf-8")

    def test_contract_registry_is_schema_valid_and_initially_experimental(self) -> None:
        validate_phase2_freeze(ROOT)
        schema = json.loads(
            (ROOT / "schemas/gasal2_longtarget_contracts.schema.json").read_text(encoding="utf-8")
        )
        registry = json.loads(
            (ROOT / "config/gasal2_longtarget_contracts.json").read_text(encoding="utf-8")
        )
        validate_schema_value(schema, registry, "registry")
        self.assertEqual(registry["schema_version"], "1.0.0")
        self.assertEqual(registry["paper_data_freeze"], "paper-data-v1-dccfd49-20260716")
        contracts = {row["contract_id"]: row for row in registry["contracts"]}
        self.assertEqual(
            set(contracts), {"score_top5_v1", "all_ranked_top5_v1", "full_output_v1"}
        )
        self.assertTrue(all(row["status"] == "experimental" for row in contracts.values()))
        for row in contracts.values():
            self.assertTrue(row["output_definition"])
            self.assertTrue(row["required_preset"])
            self.assertTrue(row["input_guards"])
            self.assertTrue(row["runtime_guards"])
            self.assertTrue(row["authority_definition"])
            self.assertTrue(row["validation_datasets"])
            self.assertTrue(row["known_limitations"])

    def test_holdout_manifest_is_frozen_stratified_and_nonoverlapping(self) -> None:
        validate_phase2_freeze(ROOT)
        manifest_path = ROOT / "paper/bioinformatics/holdout_manifest.tsv"
        rows = read_tsv(manifest_path)
        self.assertEqual(len(rows), 24)
        query_rows = {row["query_id"]: row for row in rows}
        self.assertEqual(len(query_rows), 12)
        counts: dict[str, int] = {}
        for row in query_rows.values():
            counts[row["length_stratum"]] = counts.get(row["length_stratum"], 0) + 1
            self.assertLessEqual(int(row["query_length_nt"]), 2812)
        self.assertEqual(counts, {"le_800": 4, "801_1600": 4, "1601_2812": 4})
        self.assertEqual(len({row["gene_id"].split(".", 1)[0] for row in rows}), 12)
        self.assertEqual(len({row["target_id"] for row in rows}), 2)
        self.assertEqual(len({row["target_chromosome"] for row in rows}), 2)
        self.assertTrue(
            {row["target_chromosome"] for row in rows}.isdisjoint({"chr11", "chr21", "chr22"})
        )
        self.assertTrue(all(row["target_length_bp"] == "2501" for row in rows))
        self.assertTrue(all(row["status"] == "preregistered_not_run" for row in rows))
        self.assertTrue(all(row["run_modes"] == "authority,candidate,verified" for row in rows))
        self.assertEqual(sum(row["repeat_count"] == "3" for row in rows), 6)

        exclusions = read_tsv(ROOT / "paper/bioinformatics/development_query_exclusions.tsv")
        excluded_ids = {
            row["value"] for row in exclusions if row["exclusion_type"] == "gene_id"
        }
        excluded_names = {
            row["value"] for row in exclusions if row["exclusion_type"] == "gene_name"
        }
        excluded_digests = {
            row["value"] for row in exclusions if row["exclusion_type"] == "sequence_sha256"
        }
        for row in query_rows.values():
            self.assertNotIn(row["gene_id"].split(".", 1)[0], excluded_ids)
            self.assertNotIn(row["gene_name"], excluded_names)
            self.assertNotIn(row["query_sequence_sha256"], excluded_digests)
            query_path = ROOT / row["query_path"]
            self.assertEqual(sha256(query_path), row["query_file_sha256"])
        for row in {row["target_id"]: row for row in rows}.values():
            target_path = ROOT / row["target_path"]
            self.assertEqual(sha256(target_path), row["target_file_sha256"])

        recorded_digest, name = (
            ROOT / "paper/bioinformatics/holdout_manifest.sha256"
        ).read_text(encoding="utf-8").strip().split("  ", 1)
        self.assertEqual(name, "holdout_manifest.tsv")
        self.assertEqual(recorded_digest, sha256(manifest_path))

    def test_source_ledger_and_protocol_capture_reproduction_contract(self) -> None:
        validate_phase2_freeze(ROOT)
        sources = read_tsv(ROOT / "paper/bioinformatics/holdout_sources.tsv")
        self.assertEqual(
            {row["source_id"] for row in sources},
            {"gencode_v49_lncrna", "gencode_v49_gtf", "ucsc_hg38_chr1", "ucsc_hg38_chr9"},
        )
        for row in sources:
            self.assertEqual(row["status"], "verified")
            self.assertTrue(row["url"].startswith("https://"))
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(int(row["size_bytes"]), 0)
            self.assertTrue(row["license_or_terms"])
            self.assertTrue(row["redistribution_note"])
            self.assertTrue(row["download_command"])

        protocol = (ROOT / "paper/bioinformatics/holdout_protocol.md").read_text(
            encoding="utf-8"
        )
        manifest_digest = (
            ROOT / "paper/bioinformatics/holdout_manifest.sha256"
        ).read_text(encoding="utf-8").split()[0]
        self.assertIn(manifest_digest, protocol)
        for phrase in (
            "GENCODE v49",
            "GRCh38.p14",
            "gasal2-longtarget-phase2-holdout-v1-20260724",
            "4 / 4 / 4",
            "before any holdout execution",
            "No workload may be removed",
            "computational prioritization only",
        ):
            self.assertIn(phrase, protocol)

        fetch = (ROOT / "reproduce/bioinformatics/fetch_holdout_inputs.sh").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "gencode.v49.lncRNA_transcripts.fa.gz",
            "gencode.v49.annotation.gtf.gz",
            "chr1.fa.gz",
            "chr9.fa.gz",
            "holdout_manifest.sha256",
        ):
            self.assertIn(phrase, fetch)
        for unsafe in ('rm -rf "$SOURCE_DIR"', "curl | sh", "eval "):
            self.assertNotIn(unsafe, fetch)

    def test_fetcher_cleans_partial_chromosome_after_decompression_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            bin_dir = temp_dir / "bin"
            source_dir = temp_dir / "sources"
            bin_dir.mkdir()

            stubs = {
                "curl": """#!/usr/bin/env bash
while (($#)); do
  if [[ "$1" == "--output" ]]; then
    printf payload >"$2"
    exit 0
  fi
  shift
done
exit 2
""",
                "md5sum": """#!/usr/bin/env bash
case "$1" in
  *lncRNA*) digest=6d52ea2c72933c864e46a560fe0b5d4c ;;
  *annotation*) digest=0ef4a024ea2d35b1b88c12447b0b70b9 ;;
  *chr1*) digest=f069c41e7cc8c2d3a7655cbb2d4186b8 ;;
  *) exit 2 ;;
esac
printf '%s  %s\n' "$digest" "$1"
""",
                "sha256sum": """#!/usr/bin/env bash
case "$1" in
  *lncRNA*) digest=1f04e509309fa74b694ef3cc1e52c1c8173bb0e679f8a22785fa43ecadd28ef4 ;;
  *annotation*) digest=d6e6fe0515c95b2a8cd36a853c1989cee9115c736c60237c56ae92b9daaaf7c4 ;;
  *) exit 2 ;;
esac
printf '%s  %s\n' "$digest" "$1"
""",
                "stat": """#!/usr/bin/env bash
case "$3" in
  *lncRNA*) printf '37870043\n' ;;
  *annotation*) printf '93374019\n' ;;
  *) exit 2 ;;
esac
""",
                "gzip": """#!/usr/bin/env bash
printf partial-sequence
exit 9
""",
            }
            for name, contents in stubs.items():
                path = bin_dir / name
                path.write_text(contents, encoding="utf-8")
                path.chmod(0o755)

            environment = os.environ.copy()
            environment["PATH"] = f"{bin_dir}:{environment['PATH']}"
            environment["SOURCE_DIR"] = str(source_dir)
            completed = subprocess.run(
                ["bash", str(ROOT / "reproduce/bioinformatics/fetch_holdout_inputs.sh")],
                cwd=ROOT,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(list(source_dir.rglob("*.partial.*")), [])

    def test_freeze_is_integrated_as_a_preexecution_repository_gate(self) -> None:
        checker_path = ROOT / "scripts/check_bioinformatics_phase2_freeze.sh"
        self.assertTrue(checker_path.is_file())
        checker = checker_path.read_text(encoding="utf-8")
        for phrase in (
            "check_bioinformatics_phase2_freeze.py",
            "check_build_bioinformatics_holdout_panel.py",
            "build_holdout_panel.py",
            "holdout_manifest.sha256",
            "preregistered_not_run",
        ):
            self.assertIn(phrase, checker)
        for forbidden in (
            "fasim_longtarget_x86",
            "fasim_longtarget_gasal2",
            "--mode verified",
        ):
            self.assertNotIn(forbidden, checker)

        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("check-bioinformatics-phase2-freeze:\n", makefile)
        self.assertNotIn(
            "check-bioinformatics-phase2-freeze: check-bioinformatics-phase1", makefile
        )
        self.assertIn("bash ./scripts/check_bioinformatics_phase2_freeze.sh", makefile)

        manifest = read_tsv(ROOT / "paper/bioinformatics/submission_manifest.tsv")
        phase2_paths = {row["path"] for row in manifest if row["phase"] == "2"}
        expected_freeze_paths = {
            "config/gasal2_longtarget_contracts.json",
            "paper/bioinformatics/development_query_exclusions.tsv",
            "paper/bioinformatics/holdout_manifest.sha256",
            "paper/bioinformatics/holdout_manifest.tsv",
            "paper/bioinformatics/holdout_protocol.md",
            "paper/bioinformatics/holdout_selection.json",
            "paper/bioinformatics/holdout_sources.tsv",
            "reproduce/bioinformatics/build_holdout_panel.py",
            "reproduce/bioinformatics/fetch_holdout_inputs.sh",
            "schemas/gasal2_longtarget_contracts.schema.json",
            "scripts/check_bioinformatics_phase2_freeze.sh",
            "tests/check_bioinformatics_phase2_freeze.py",
            "tests/check_build_bioinformatics_holdout_panel.py",
        }
        self.assertTrue(expected_freeze_paths.issubset(phase2_paths))
        self.assertTrue(
            all(
                row["status"] == "pass"
                for row in manifest
                if row["path"] in expected_freeze_paths
            )
        )

    def test_manifest_validator_rejects_duplicate_pair_with_missing_cartesian_pair(self) -> None:
        with self.freeze_fixture() as root:
            manifest = root / "paper/bioinformatics/holdout_manifest.tsv"
            rows = read_tsv(manifest)
            rows[1] = dict(rows[0])
            write_tsv(manifest, rows)
            self.rewrite_manifest_checksum(root)
            with self.assertRaises((AssertionError, ValueError)):
                self.test_holdout_manifest_is_frozen_stratified_and_nonoverlapping()

    def test_manifest_validator_rejects_stale_artifact_file(self) -> None:
        with self.freeze_fixture() as root:
            stale = root / "reproduce/bioinformatics/holdout_inputs/queries/stale.fa"
            stale.write_text(">stale\nACGT\n", encoding="utf-8")
            with self.assertRaises((AssertionError, ValueError)):
                self.test_holdout_manifest_is_frozen_stratified_and_nonoverlapping()

    def test_manifest_validator_rejects_selection_metadata_drift(self) -> None:
        with self.freeze_fixture() as root:
            selection_path = root / "paper/bioinformatics/holdout_selection.json"
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            selection["queries"][0]["gene_name"] = "DRIFTED_GENE_NAME"
            selection_path.write_text(json.dumps(selection), encoding="utf-8")
            with self.assertRaises((AssertionError, ValueError)):
                self.test_holdout_manifest_is_frozen_stratified_and_nonoverlapping()

    def test_source_validator_rejects_selection_ledger_digest_drift(self) -> None:
        with self.freeze_fixture() as root:
            sources_path = root / "paper/bioinformatics/holdout_sources.tsv"
            sources = read_tsv(sources_path)
            sources[0]["sha256"] = "0" * 64
            write_tsv(sources_path, sources)
            with self.assertRaises((AssertionError, ValueError)):
                self.test_source_ledger_and_protocol_capture_reproduction_contract()

    def test_selection_validator_rejects_hash_order_stratum_and_geometry_drift(self) -> None:
        def query_hash(selection: dict[str, object], _root: Path) -> None:
            selection["queries"][0]["selection_hash"] = "0" * 64

        def target_hash(selection: dict[str, object], _root: Path) -> None:
            selection["targets"][1]["selection_hash"] = "f" * 64

        def query_chromosome(selection: dict[str, object], _root: Path) -> None:
            selection["queries"][0]["chromosome"] = "chrM"

        def query_order(selection: dict[str, object], _root: Path) -> None:
            selection["queries"][0], selection["queries"][1] = (
                selection["queries"][1],
                selection["queries"][0],
            )
            manifest_path = _root / "paper/bioinformatics/holdout_manifest.tsv"
            rows = read_tsv(manifest_path)
            for row in rows:
                row["repeat_count"] = "3" if row["query_id"] in {"hq02", "hq05", "hq09"} else "1"
            write_tsv(manifest_path, rows)
            self.refreeze_fixture(_root)

        def stratum(selection: dict[str, object], root: Path) -> None:
            first = selection["queries"][1]
            second = selection["queries"][5]
            first["length_stratum"], second["length_stratum"] = (
                second["length_stratum"],
                first["length_stratum"],
            )
            manifest_path = root / "paper/bioinformatics/holdout_manifest.tsv"
            rows = read_tsv(manifest_path)
            for row in rows:
                if row["query_id"] == first["query_id"]:
                    row["length_stratum"] = first["length_stratum"]
                elif row["query_id"] == second["query_id"]:
                    row["length_stratum"] = second["length_stratum"]
                row["repeat_count"] = "3" if row["query_id"] in {"hq01", "hq02", "hq09"} else "1"
            write_tsv(manifest_path, rows)
            self.refreeze_fixture(root)

        def target_geometry(selection: dict[str, object], root: Path) -> None:
            target = selection["targets"][0]
            target["tss"] += 1
            manifest_path = root / "paper/bioinformatics/holdout_manifest.tsv"
            rows = read_tsv(manifest_path)
            for row in rows:
                if row["target_id"] == target["target_id"]:
                    row["target_tss"] = str(target["tss"])
            write_tsv(manifest_path, rows)
            self.refreeze_fixture(root)

        mutations = {
            "query_selection_hash": query_hash,
            "target_selection_hash": target_hash,
            "query_primary_chromosome": query_chromosome,
            "query_id_order": query_order,
            "query_length_stratum": stratum,
            "target_promoter_geometry": target_geometry,
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), self.freeze_fixture() as root:
                selection_path = root / "paper/bioinformatics/holdout_selection.json"
                selection = json.loads(selection_path.read_text(encoding="utf-8"))
                mutate(selection, root)
                selection_path.write_text(json.dumps(selection), encoding="utf-8")
                with self.assertRaises((AssertionError, ValueError)):
                    self.test_holdout_manifest_is_frozen_stratified_and_nonoverlapping()

    def test_source_validator_rejects_gencode_authority_metadata_drift(self) -> None:
        with self.freeze_fixture() as root:
            sources_path = root / "paper/bioinformatics/holdout_sources.tsv"
            sources = read_tsv(sources_path)
            gencode = next(row for row in sources if row["source_id"] == "gencode_v49_lncrna")
            gencode["release"] = "v48"
            gencode["assembly"] = "GRCh37"
            gencode["provider"] = "unreviewed mirror"
            write_tsv(sources_path, sources)
            with self.assertRaises((AssertionError, ValueError)):
                self.test_source_ledger_and_protocol_capture_reproduction_contract()

    def test_registry_validator_rejects_unsafe_or_inconsistent_mutations(self) -> None:
        mutations = {
            "duplicate_contract": lambda registry: registry["contracts"].append(
                json.loads(json.dumps(registry["contracts"][0]))
            ),
            "missing_contract": lambda registry: registry["contracts"].pop(),
            "negative_resource": lambda registry: registry["contracts"][0][
                "runtime_guards"
            ].update(minimum_gpu_memory_mib=-1),
            "negative_count": lambda registry: registry["contracts"][0][
                "clean_mismatch_counts"
            ]["development"].update(clean=-1),
            "false_input_guard": lambda registry: registry["contracts"][0][
                "input_guards"
            ].update(canonical_acgt=False),
            "false_runtime_guard": lambda registry: registry["contracts"][0][
                "runtime_guards"
            ].update(fallback_on_unknown_state=False),
            "unexpected_field": lambda registry: registry["contracts"][0].update(
                unreviewed=True
            ),
            "blank_authority": lambda registry: registry["contracts"][0][
                "authority_definition"
            ].update(comparator=" "),
            "wrong_preset": lambda registry: registry["contracts"][0][
                "required_preset"
            ].update(top_k=4),
            "promotion_state_inconsistent": lambda registry: registry.update(
                registry_state="promotion_decided"
            ),
            "preregistered_holdout_has_results": lambda registry: registry["contracts"][0][
                "clean_mismatch_counts"
            ]["holdout"].update(clean=24, mismatch=0),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), self.freeze_fixture() as root:
                registry_path = root / "config/gasal2_longtarget_contracts.json"
                registry = json.loads(registry_path.read_text(encoding="utf-8"))
                mutate(registry)
                registry_path.write_text(json.dumps(registry), encoding="utf-8")
                with self.assertRaises((AssertionError, ValueError)):
                    self.test_contract_registry_is_schema_valid_and_initially_experimental()


if __name__ == "__main__":
    unittest.main(verbosity=2)
