#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
BASELINE="bf94dc75c5fe3e996472a1e90d242f582da361bf"
FETCHER="$ROOT/reproduce/bioinformatics/fetch_application_inputs.sh"
WORK="${WORK:-$ROOT/.tmp/check_bioinformatics_phase3_freeze}"

cached_source_count="$(python3 - "$ROOT" <<'PY'
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path


root = Path(sys.argv[1])
temporary_name = ".tmp"
cache_name = "bioinformatics_application_sources"
expected_names = {
    "gencode.v49.lncRNA_transcripts.fa.gz",
    "gencode.v49.annotation.gtf.gz",
    "chr21.fa.gz",
    "chr22.fa.gz",
}
directory_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
file_flags = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


def fail(message: str) -> None:
    raise SystemExit(f"Bioinformatics Phase 3 cache preflight failed: {message}")


def retained_directory(
    name: str,
    *,
    parent_fd: int,
    unsafe_message: str,
) -> tuple[int, os.stat_result]:
    try:
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        raise
    if not stat.S_ISDIR(named.st_mode):
        fail(unsafe_message)
    try:
        descriptor = os.open(name, directory_flags, dir_fd=parent_fd)
    except OSError:
        fail(unsafe_message)
    retained = os.fstat(descriptor)
    if not stat.S_ISDIR(retained.st_mode) or (
        retained.st_dev,
        retained.st_ino,
    ) != (named.st_dev, named.st_ino):
        os.close(descriptor)
        fail(unsafe_message)
    return descriptor, retained


try:
    root_named = os.lstat(root)
    if not stat.S_ISDIR(root_named.st_mode):
        fail("repository root is unsafe")
    root_fd = os.open(root, directory_flags)
except OSError:
    fail("repository root is unsafe")
try:
    root_retained = os.fstat(root_fd)
    if (root_retained.st_dev, root_retained.st_ino) != (
        root_named.st_dev,
        root_named.st_ino,
    ):
        fail("repository root changed during preflight")
    try:
        temporary_fd, temporary_identity = retained_directory(
            temporary_name,
            parent_fd=root_fd,
            unsafe_message="unsafe Phase 3 source-cache parent",
        )
    except FileNotFoundError:
        print(0)
        raise SystemExit(0)
    try:
        try:
            cache_fd, cache_identity = retained_directory(
                cache_name,
                parent_fd=temporary_fd,
                unsafe_message="unsafe Phase 3 source-cache directory",
            )
        except FileNotFoundError:
            print(0)
            raise SystemExit(0)
        try:
            names = set(os.listdir(cache_fd))
            unexpected = sorted(names - expected_names)
            if unexpected:
                fail(
                    "unexpected Phase 3 source-cache entry: "
                    + ", ".join(unexpected)
                )
            if names and names != expected_names:
                fail("source cache must contain zero or exactly four canonical archives")
            if not names:
                print(0)
                raise SystemExit(0)

            seen_inodes: set[tuple[int, int]] = set()
            for name in sorted(expected_names):
                try:
                    named = os.stat(name, dir_fd=cache_fd, follow_symlinks=False)
                except FileNotFoundError:
                    fail("source cache changed during archive validation")
                if not stat.S_ISREG(named.st_mode):
                    fail(f"source-cache entry is not a regular file: {name}")
                if named.st_nlink != 1:
                    fail(f"source-cache archive has a hardlink alias: {name}")
                inode = (named.st_dev, named.st_ino)
                if inode in seen_inodes:
                    fail(f"source-cache archives share an inode: {name}")
                seen_inodes.add(inode)
                try:
                    descriptor = os.open(name, file_flags, dir_fd=cache_fd)
                except OSError:
                    fail(f"source-cache archive changed while opening: {name}")
                try:
                    opened = os.fstat(descriptor)
                    if (
                        not stat.S_ISREG(opened.st_mode)
                        or opened.st_nlink != 1
                        or (opened.st_dev, opened.st_ino) != inode
                    ):
                        fail(f"source-cache archive changed while opening: {name}")
                finally:
                    os.close(descriptor)

            cache_current = os.stat(
                cache_name,
                dir_fd=temporary_fd,
                follow_symlinks=False,
            )
            if (cache_current.st_dev, cache_current.st_ino) != (
                cache_identity.st_dev,
                cache_identity.st_ino,
            ):
                fail("source-cache directory changed during preflight")
            print(4)
        finally:
            os.close(cache_fd)
    finally:
        os.close(temporary_fd)
finally:
    os.close(root_fd)
PY
)"

if [[ -L "$WORK" || ( -e "$WORK" && ! -d "$WORK" ) ]]; then
  echo "unsafe Phase 3 checker work directory: $WORK" >&2
  exit 1
fi
mkdir -p -- "$WORK"
if [[ ! -d "$WORK" || -L "$WORK" ]]; then
  echo "cannot create a safe Phase 3 checker work directory: $WORK" >&2
  exit 1
fi
WORK="$(cd "$WORK" && pwd -P)"
before_snapshot="$WORK/application-freeze.before.json"
after_snapshot="$WORK/application-freeze.after.json"

for relative in \
  paper/bioinformatics/README.md \
  paper/bioinformatics/application_input_summary.tsv \
  paper/bioinformatics/application_manifest.sha256 \
  paper/bioinformatics/application_manifest.tsv \
  paper/bioinformatics/application_protocol.md \
  paper/bioinformatics/application_selection.json \
  paper/bioinformatics/application_sources.tsv \
  paper/bioinformatics/claim_evidence.tsv \
  paper/bioinformatics/development_query_exclusions.tsv \
  paper/bioinformatics/holdout_manifest.tsv \
  paper/bioinformatics/submission_manifest.tsv \
  reproduce/bioinformatics/application_inputs \
  reproduce/bioinformatics/build_application_panel.py \
  reproduce/bioinformatics/fetch_application_inputs.sh \
  tests/check_build_bioinformatics_application_panel.py; do
  if [[ ! -e "$ROOT/$relative" || -L "$ROOT/$relative" ]]; then
    echo "missing or unsafe Bioinformatics Phase 3 freeze dependency: $relative" >&2
    exit 1
  fi
done

python3 "$ROOT/tests/check_build_bioinformatics_application_panel.py"
python3 -m py_compile \
  "$ROOT/reproduce/bioinformatics/build_application_panel.py" \
  "$ROOT/tests/check_build_bioinformatics_application_panel.py"
bash -n "$FETCHER"
bash -n "$ROOT/scripts/check_bioinformatics_phase3_freeze.sh"
python3 -m json.tool "$ROOT/paper/bioinformatics/application_selection.json" >/dev/null
python3 -m json.tool "$ROOT/config/gasal2_longtarget_contracts.json" >/dev/null
python3 -m json.tool "$ROOT/schemas/gasal2_longtarget_contracts.schema.json" >/dev/null
python3 -m json.tool "$ROOT/schemas/gasal2_longtarget_run_report.schema.json" >/dev/null
(cd "$ROOT/paper/bioinformatics" && sha256sum -c application_manifest.sha256)
git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

forbidden_paths=(
  "$ROOT/reproduce/bioinformatics/run_application.py"
  "$ROOT/reproduce/bioinformatics/application_backend.py"
  "$ROOT/reproduce/bioinformatics/application_raw"
  "$ROOT/reproduce/bioinformatics/application_outputs"
  "$ROOT/paper/bioinformatics/source_data"
  "$ROOT/paper/bioinformatics/application_attempt_results.tsv"
  "$ROOT/paper/bioinformatics/application_results.tsv"
  "$ROOT/paper/bioinformatics/application_summary.json"
  "$ROOT/paper/bioinformatics/application_retry_ledger.tsv"
  "$ROOT/paper/bioinformatics/application_exclusion_ledger.tsv"
  "$ROOT/paper/bioinformatics/phase3_decision.md"
)
for forbidden_path in "${forbidden_paths[@]}"; do
  if [[ -e "$forbidden_path" || -L "$forbidden_path" ]]; then
    echo "forbidden Phase 3 execution artifact exists: $forbidden_path" >&2
    exit 1
  fi
done
shopt -s nullglob
phase3_artifact_roots=("$ROOT"/.paper-artifacts/bioinformatics-phase3-*)
if ((${#phase3_artifact_roots[@]})); then
  echo "forbidden .paper-artifacts/bioinformatics-phase3-* root exists" >&2
  exit 1
fi
shopt -u nullglob

if ! git -C "$ROOT" diff --quiet "$BASELINE" -- \
  paper/bioinformatics \
  ':(exclude)paper/bioinformatics/README.md' \
  ':(exclude)paper/bioinformatics/submission_manifest.tsv' \
  ':(exclude)paper/bioinformatics/application_*' \
  reproduce/bioinformatics \
  ':(exclude)reproduce/bioinformatics/build_application_panel.py' \
  ':(exclude)reproduce/bioinformatics/fetch_application_inputs.sh' \
  ':(exclude)reproduce/bioinformatics/application_inputs/**' \
  scripts \
  ':(exclude)scripts/check_bioinformatics_phase3_freeze.sh' \
  tests \
  ':(exclude)tests/check_build_bioinformatics_application_panel.py' \
  config schemas fasim cuda longtarget.cpp exact_sim.h sim.h stats.h rules.h; then
  echo "Phase 2 or core runtime path changed from bf94dc7" >&2
  exit 1
fi

python3 - "$ROOT" "$BASELINE" <<'PY'
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
from collections import Counter
from pathlib import Path, PurePosixPath


root = Path(sys.argv[1])
baseline = sys.argv[2]
FREEZE_ID = "bioinformatics-phase3-application-v1-e8c5441c"
MANIFEST_SHA256 = "e8c5441c36db8fb4ae28492aee20f7e1af5f357148216ef58fae03c7f52c78bc"
SELECTION_SEED = "gasal2-longtarget-phase3-application-v1-20260724"
MANIFEST_FIELDS = (
    "record_id", "record_role", "source_release", "assembly",
    "original_gene_id", "original_gene_name", "original_transcript_id",
    "selection_rule", "sequence_length", "chromosome", "strand", "tss",
    "region_start", "region_end", "sequence_sha256", "file_sha256", "path",
    "license_note", "split", "status",
)
SUMMARY_FIELDS = (
    "freeze_id", "manifest_sha256", "query_count", "target_count", "pair_count",
    "query_total_bp", "target_total_bp", "chr21_target_count",
    "chr22_target_count", "min_query_length", "max_query_length",
    "annotation_target_candidate_count", "excluded_target_count",
)
SOURCE_FIELDS = (
    "source_id", "role", "provider", "release", "assembly", "url",
    "upstream_md5", "compressed_size_bytes", "compressed_sha256",
    "decompressed_size_bytes", "decompressed_sha256", "local_source_path",
    "license_or_terms", "redistribution_note", "download_command", "status",
)
HOLDOUT_FIELDS = (
    "workload_id", "query_id", "gene_id", "gene_name", "transcript_id",
    "query_length_nt", "length_stratum", "query_sequence_sha256",
    "query_file_sha256", "query_path", "target_id", "target_gene_id",
    "target_gene_name", "target_chromosome", "target_strand", "target_tss",
    "target_region_start", "target_region_end", "target_length_bp",
    "target_sequence_sha256", "target_file_sha256", "target_path", "assembly",
    "annotation_release", "selection_seed", "requested_contract", "run_modes",
    "repeat_count", "status",
)
SOURCE_AUTHORITIES = (
    {
        "source_id": "gencode_v49_lncrna",
        "role": "lncRNA transcript sequences", "provider": "GENCODE",
        "release": "v49", "assembly": "GRCh38.p14",
        "url": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.lncRNA_transcripts.fa.gz",
        "upstream_md5": "6d52ea2c72933c864e46a560fe0b5d4c",
        "compressed_size_bytes": "37870043",
        "compressed_sha256": "1f04e509309fa74b694ef3cc1e52c1c8173bb0e679f8a22785fa43ecadd28ef4",
        "decompressed_size_bytes": "223740848",
        "decompressed_sha256": "4c632018e0198d76fe76471baa5511a1c07af86bf7bab6ce6747edb8d5add5ae",
        "local_source_path": ".tmp/bioinformatics_application_sources/gencode.v49.lncRNA_transcripts.fa.gz",
        "license_or_terms": "GENCODE project data are open access",
        "redistribution_note": "Selected small transcript FASTAs are retained with source attribution; final redistribution approval remains owner-controlled",
        "download_command": "curl -fL --retry 3 --output .tmp/bioinformatics_application_sources/gencode.v49.lncRNA_transcripts.fa.gz.partial.$$ https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.lncRNA_transcripts.fa.gz",
        "status": "verified",
    },
    {
        "source_id": "gencode_v49_gtf", "role": "gene and transcript annotation",
        "provider": "GENCODE", "release": "v49", "assembly": "GRCh38.p14",
        "url": "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.annotation.gtf.gz",
        "upstream_md5": "0ef4a024ea2d35b1b88c12447b0b70b9",
        "compressed_size_bytes": "93374019",
        "compressed_sha256": "d6e6fe0515c95b2a8cd36a853c1989cee9115c736c60237c56ae92b9daaaf7c4",
        "decompressed_size_bytes": "3323462848",
        "decompressed_sha256": "ff32fd55c6799b3b94fe10aa17b2b5d4da952fa1de12fe44afadf32e949ec914",
        "local_source_path": ".tmp/bioinformatics_application_sources/gencode.v49.annotation.gtf.gz",
        "license_or_terms": "GENCODE project data are open access",
        "redistribution_note": "Annotation is downloaded for reconstruction and is not redistributed in this repository",
        "download_command": "curl -fL --retry 3 --output .tmp/bioinformatics_application_sources/gencode.v49.annotation.gtf.gz.partial.$$ https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.annotation.gtf.gz",
        "status": "verified",
    },
    {
        "source_id": "ucsc_hg38_chr21", "role": "forward genomic reference sequence",
        "provider": "UCSC Genome Browser / Genome Reference Consortium",
        "release": "hg38 2014-01-23", "assembly": "GRCh38",
        "url": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr21.fa.gz",
        "upstream_md5": "184df2bd9b812b6e6b6da16c6021369e",
        "compressed_size_bytes": "12709705",
        "compressed_sha256": "c979ca1e5065c2521a50773473e0d0cc018fd6f3e9bb3aa90493fe7b45d57d1b",
        "decompressed_size_bytes": "47644190",
        "decompressed_sha256": "35c71b68436d1a278ecb6a1e875af3ba4020738a028a7feac769a6d62790ae1f",
        "local_source_path": ".tmp/bioinformatics_application_sources/chr21.fa.gz",
        "license_or_terms": "UCSC data-use conditions and Genome Reference Consortium attribution apply",
        "redistribution_note": "Only selected promoter sequences are retained; final redistribution approval remains owner-controlled",
        "download_command": "curl -fL --retry 3 --output .tmp/bioinformatics_application_sources/chr21.fa.gz.partial.$$ https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr21.fa.gz",
        "status": "verified",
    },
    {
        "source_id": "ucsc_hg38_chr22", "role": "forward genomic reference sequence",
        "provider": "UCSC Genome Browser / Genome Reference Consortium",
        "release": "hg38 2014-01-23", "assembly": "GRCh38",
        "url": "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz",
        "upstream_md5": "41b47ce1cc21b558409c19b892e1c0d1",
        "compressed_size_bytes": "12255678",
        "compressed_sha256": "05f9d97d6fbfd08a44ca45b50837ca2ae9c471f35ba79dffec04d2cb5eaaf695",
        "decompressed_size_bytes": "51834845",
        "decompressed_sha256": "ce3ee1ca39356238f7aee438a40a88b4f1b9d80b316b263e16fb12402212d10f",
        "local_source_path": ".tmp/bioinformatics_application_sources/chr22.fa.gz",
        "license_or_terms": "UCSC data-use conditions and Genome Reference Consortium attribution apply",
        "redistribution_note": "Only selected promoter sequences are retained; final redistribution approval remains owner-controlled",
        "download_command": "curl -fL --retry 3 --output .tmp/bioinformatics_application_sources/chr22.fa.gz.partial.$$ https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz",
        "status": "verified",
    },
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"Bioinformatics Phase 3 freeze check failed: {message}")


def stable_id(value: str) -> str:
    return value.split(".", 1)[0]


def safe_file(path: Path, label: str) -> os.stat_result:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        raise SystemExit(f"Bioinformatics Phase 3 freeze check failed: missing {label}: {path}")
    require(stat.S_ISREG(metadata.st_mode), f"{label} is not a regular file: {path}")
    require(metadata.st_nlink == 1, f"{label} has a hardlink alias: {path}")
    return metadata


def safe_directory(path: Path, label: str) -> os.stat_result:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        raise SystemExit(f"Bioinformatics Phase 3 freeze check failed: missing {label}: {path}")
    require(stat.S_ISDIR(metadata.st_mode), f"{label} is a symlink or not a directory: {path}")
    return metadata


def read_bytes(path: Path, label: str) -> bytes:
    safe_file(path, label)
    data = path.read_bytes()
    safe_file(path, label)
    return data


def sha256(path: Path, label: str) -> str:
    return hashlib.sha256(read_bytes(path, label)).hexdigest()


def read_tsv(path: Path, fields: tuple[str, ...], label: str) -> list[dict[str, str]]:
    data = read_bytes(path, label)
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise SystemExit(f"Bioinformatics Phase 3 freeze check failed: invalid UTF-8 in {label}: {error}")
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter="\t")
    require(tuple(reader.fieldnames or ()) == fields, f"{label} schema drift")
    rows = list(reader)
    require(
        all(tuple(row) == fields and all(value is not None for value in row.values()) for row in rows),
        f"{label} contains a malformed row",
    )
    return rows


manifest_path = root / "paper/bioinformatics/application_manifest.tsv"
manifest_bytes = read_bytes(manifest_path, "application manifest")
require(hashlib.sha256(manifest_bytes).hexdigest() == MANIFEST_SHA256, "manifest checksum drift")
checksum = read_bytes(
    root / "paper/bioinformatics/application_manifest.sha256",
    "manifest checksum receipt",
)
require(
    checksum == f"{MANIFEST_SHA256}  application_manifest.tsv\n".encode("ascii"),
    "manifest checksum receipt drift",
)
rows = read_tsv(manifest_path, MANIFEST_FIELDS, "application manifest")
require(len(rows) == 718, f"expected 718 manifest records, found {len(rows)}")
queries = [row for row in rows if row["record_role"] == "query"]
targets = [row for row in rows if row["record_role"] == "target"]
require(len(queries) == 50, f"expected 50 queries, found {len(queries)}")
require(len(targets) == 668 and len(targets) >= 300, f"invalid target count: {len(targets)}")
require(queries + targets == rows, "manifest must order queries before targets")
require(
    [row["record_id"] for row in queries] == [f"aq{index:03d}" for index in range(1, 51)],
    "query IDs or order drifted",
)
require(
    [row["record_id"] for row in targets] == [f"at{index:04d}" for index in range(1, 669)],
    "target IDs or order drifted",
)
require(len({row["record_id"] for row in rows}) == 718, "record IDs are not unique")
require(len({row["path"] for row in rows}) == 718, "record paths are not unique")
require(
    len({stable_id(row["original_gene_id"]) for row in queries}) == 50
    and len({stable_id(row["original_gene_id"]) for row in targets}) == 668,
    "stable gene IDs are not unique within record role",
)
require(
    len({row["original_transcript_id"] for row in queries}) == 50
    and len({row["original_transcript_id"] for row in targets}) == 668,
    "transcript IDs are not unique within record role",
)
require(len({row["sequence_sha256"] for row in queries}) == 50, "query sequence digests are not unique")
require(
    all(
        row["source_release"] == "GENCODE v49"
        and row["assembly"] == "GRCh38"
        and row["split"] == "application"
        and row["status"] == "preregistered_not_run"
        and row["selection_rule"].strip()
        and row["license_note"].strip()
        for row in rows
    ),
    "common manifest metadata or preregistered status drifted",
)

input_root = root / "reproduce/bioinformatics/application_inputs"
safe_directory(input_root, "application input root")
safe_directory(input_root / "queries", "application query directory")
safe_directory(input_root / "targets", "application target directory")
expected_paths: set[str] = set()
query_total = 0
target_total = 0
chromosome_counts: Counter[str] = Counter()
target_digest_groups: dict[str, list[dict[str, str]]] = {}
seen_file_inodes: set[tuple[int, int]] = set()
for row in rows:
    role = row["record_role"]
    record_id = row["record_id"]
    require(role in {"query", "target"}, f"invalid record role: {record_id}")
    subdirectory = "queries" if role == "query" else "targets"
    expected_path = f"reproduce/bioinformatics/application_inputs/{subdirectory}/{record_id}.fa"
    require(row["path"] == expected_path, f"noncanonical FASTA path: {record_id}")
    relative = PurePosixPath(row["path"])
    require(
        not relative.is_absolute() and ".." not in relative.parts and "." not in relative.parts,
        f"unsafe FASTA path: {record_id}",
    )
    expected_paths.add(row["path"])
    path = root / relative
    metadata = safe_file(path, f"FASTA {record_id}")
    inode = (metadata.st_dev, metadata.st_ino)
    require(inode not in seen_file_inodes, f"aliased FASTA inode: {record_id}")
    seen_file_inodes.add(inode)
    fasta = read_bytes(path, f"FASTA {record_id}")
    require(hashlib.sha256(fasta).hexdigest() == row["file_sha256"], f"FASTA hash drift: {record_id}")
    try:
        lines = fasta.decode("ascii", errors="strict").splitlines()
    except UnicodeDecodeError as error:
        raise SystemExit(f"Bioinformatics Phase 3 freeze check failed: non-ASCII FASTA {record_id}: {error}")
    require(lines and lines[0].startswith(">") and len(lines[0]) > 1, f"invalid FASTA header: {record_id}")
    require(
        all(line and line == line.strip() and not line.startswith(">") for line in lines[1:]),
        f"FASTA is not exactly one record: {record_id}",
    )
    sequence = "".join(lines[1:])
    require(sequence and set(sequence) <= set("ACGT"), f"noncanonical FASTA: {record_id}")
    require(row["sequence_length"].isdigit() and row["sequence_length"] != "0", f"invalid length: {record_id}")
    length = int(row["sequence_length"])
    require(len(sequence) == length, f"FASTA length drift: {record_id}")
    require(
        hashlib.sha256(sequence.encode("ascii")).hexdigest() == row["sequence_sha256"],
        f"FASTA sequence hash drift: {record_id}",
    )
    if role == "query":
        require(500 <= length <= 2812, f"query length outside frozen range: {record_id}")
        require(
            all(row[field] == "NA" for field in ("chromosome", "strand", "tss", "region_start", "region_end")),
            f"query coordinate fields drifted: {record_id}",
        )
        expected_header = (
            f">{record_id}|{row['original_transcript_id']}|{row['original_gene_id']}|"
            f"{row['original_gene_name']}|GENCODE v49|GRCh38|application_query"
        )
        query_total += length
    else:
        require(row["chromosome"] in {"chr21", "chr22"}, f"target chromosome drift: {record_id}")
        require(row["strand"] in {"+", "-"}, f"target strand drift: {record_id}")
        require(
            all(row[field].isdigit() and row[field] != "0" for field in ("tss", "region_start", "region_end")),
            f"invalid target geometry: {record_id}",
        )
        tss, start, end = (int(row[field]) for field in ("tss", "region_start", "region_end"))
        require(end - start + 1 == length, f"target interval length drift: {record_id}")
        expected_geometry = (
            (max(1, tss - 2000), tss + 500)
            if row["strand"] == "+"
            else (max(1, tss - 500), tss + 2000)
        )
        require((start, end) == expected_geometry, f"target promoter geometry drift: {record_id}")
        expected_header = (
            f">{record_id}|{row['original_transcript_id']}|{row['original_gene_id']}|"
            f"{row['original_gene_name']}|GRCh38|{row['chromosome']}:{start}-{end}|"
            "promoter_forward_genomic"
        )
        target_total += length
        chromosome_counts[row["chromosome"]] += 1
        target_digest_groups.setdefault(row["sequence_sha256"], []).append(row)
    require(lines[0] == expected_header, f"FASTA header drift: {record_id}")

actual_paths: set[str] = set()
allowed_directories = {input_root, input_root / "queries", input_root / "targets"}
pending = [input_root]
while pending:
    directory = pending.pop()
    require(directory in allowed_directories, f"unexpected application input directory: {directory}")
    safe_directory(directory, "application input directory")
    with os.scandir(directory) as iterator:
        entries = list(iterator)
    for entry in entries:
        path = Path(entry.path)
        metadata = os.lstat(path)
        if stat.S_ISDIR(metadata.st_mode):
            pending.append(path)
        elif stat.S_ISREG(metadata.st_mode):
            require(metadata.st_nlink == 1, f"application FASTA has a hardlink alias: {path}")
            actual_paths.add(path.relative_to(root).as_posix())
        else:
            require(False, f"application input tree contains a symlink or special: {path}")
require(actual_paths == expected_paths and len(actual_paths) == 718, "application FASTA tree differs from manifest")

duplicate_target_groups = [group for group in target_digest_groups.values() if len(group) > 1]
require(len(duplicate_target_groups) == 2, "target duplicate digest group count drifted")
for group in duplicate_target_groups:
    require(len(group) == 2, "target digest is shared by more than one permitted pair")
    coordinates = {
        (row["chromosome"], row["strand"], row["tss"], row["region_start"], row["region_end"])
        for row in group
    }
    require(len(coordinates) == 1, "duplicate target digest does not share exact coordinates")

pair_count = len(queries) * len(targets)
require(pair_count == 33400 and pair_count >= 15000, f"pair count drifted: {pair_count}")
require(query_total == 56381, f"query total drifted: {query_total}")
require(target_total == 1670668, f"target total drifted: {target_total}")
require(chromosome_counts == {"chr21": 221, "chr22": 447}, "target chromosome counts drifted")

summary = read_tsv(
    root / "paper/bioinformatics/application_input_summary.tsv",
    SUMMARY_FIELDS,
    "application input summary",
)
expected_summary = {
    "freeze_id": FREEZE_ID, "manifest_sha256": MANIFEST_SHA256,
    "query_count": "50", "target_count": "668", "pair_count": "33400",
    "query_total_bp": "56381", "target_total_bp": "1670668",
    "chr21_target_count": "221", "chr22_target_count": "447",
    "min_query_length": "513", "max_query_length": "2709",
    "annotation_target_candidate_count": "668", "excluded_target_count": "0",
}
require(summary == [expected_summary], "application input summary drifted")
require(FREEZE_ID == f"bioinformatics-phase3-application-v1-{MANIFEST_SHA256[:8]}", "freeze derivation drifted")

development = read_tsv(
    root / "paper/bioinformatics/development_query_exclusions.tsv",
    ("exclusion_type", "value", "reason"),
    "development exclusion ledger",
)
require(
    len({(row["exclusion_type"], row["value"]) for row in development}) == len(development),
    "development exclusions contain duplicates",
)
require(
    all(
        row["exclusion_type"] in {"gene_id", "gene_name", "sequence_sha256"}
        and row["value"] and row["reason"].strip()
        for row in development
    ),
    "development exclusion row is invalid",
)
excluded_ids = {row["value"] for row in development if row["exclusion_type"] == "gene_id"}
excluded_names = {row["value"] for row in development if row["exclusion_type"] == "gene_name"}
excluded_digests = {row["value"] for row in development if row["exclusion_type"] == "sequence_sha256"}
require(
    all(
        stable_id(row["original_gene_id"]) not in excluded_ids
        and row["original_gene_name"] not in excluded_names
        and row["sequence_sha256"] not in excluded_digests
        for row in queries
    ),
    "application query overlaps development identities",
)
holdout = read_tsv(
    root / "paper/bioinformatics/holdout_manifest.tsv",
    HOLDOUT_FIELDS,
    "Phase 2 holdout manifest",
)
require(len(holdout) == 24, "Phase 2 holdout row count drifted")
holdout_ids = {stable_id(row["gene_id"]) for row in holdout}
holdout_digests = {row["query_sequence_sha256"] for row in holdout}
require(
    all(
        stable_id(row["original_gene_id"]) not in holdout_ids
        and row["sequence_sha256"] not in holdout_digests
        for row in queries
    ),
    "application query overlaps Phase 2 holdout identities",
)

selection_bytes = read_bytes(
    root / "paper/bioinformatics/application_selection.json",
    "application selection receipt",
)
selection = json.loads(selection_bytes.decode("utf-8", errors="strict"))
require(isinstance(selection, dict), "application selection receipt is not an object")
require(selection.get("schema_version") == 1, "selection schema version drifted")
require(selection.get("selection_seed") == SELECTION_SEED, "selection seed drifted")
require(selection.get("assembly") == "GRCh38", "selection assembly drifted")
require(selection.get("annotation_release") == "GENCODE v49", "selection annotation drifted")
require(selection.get("proposed_freeze_id") == FREEZE_ID, "proposed freeze ID drifted")
require(selection.get("final_freeze_id") == FREEZE_ID, "final freeze ID drifted")
require(selection.get("manifest_sha256") == MANIFEST_SHA256, "selection manifest digest drifted")
selected_queries = selection.get("selected_queries")
selected_targets = selection.get("selected_targets")
require(isinstance(selected_queries, list) and len(selected_queries) == 50, "selected query count drifted")
require(isinstance(selected_targets, list) and len(selected_targets) == 668, "selected target count drifted")
for selected, row in zip(selected_queries, queries, strict=True):
    expected_hash = hashlib.sha256(
        "|".join((
            SELECTION_SEED, stable_id(row["original_gene_id"]),
            stable_id(row["original_transcript_id"]), row["sequence_sha256"],
        )).encode("ascii")
    ).hexdigest()
    require(
        selected == {
            "query_id": row["record_id"], "original_gene_id": row["original_gene_id"],
            "original_gene_name": row["original_gene_name"],
            "original_transcript_id": row["original_transcript_id"],
            "sequence_length": int(row["sequence_length"]),
            "sequence_sha256": row["sequence_sha256"], "selection_hash": expected_hash,
        },
        f"selected query drifted: {row['record_id']}",
    )
for selected, row in zip(selected_targets, targets, strict=True):
    require(
        selected == {
            "target_id": row["record_id"], "original_gene_id": row["original_gene_id"],
            "original_gene_name": row["original_gene_name"],
            "original_transcript_id": row["original_transcript_id"],
            "sequence_length": int(row["sequence_length"]),
            "sequence_sha256": row["sequence_sha256"], "chromosome": row["chromosome"],
            "strand": row["strand"], "tss": int(row["tss"]),
            "region_start": int(row["region_start"]), "region_end": int(row["region_end"]),
        },
        f"selected target drifted: {row['record_id']}",
    )

query_counts = selection.get("query_counts")
target_counts = selection.get("target_counts")
require(isinstance(query_counts, dict) and isinstance(target_counts, dict), "selection counts are missing")
require(
    all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in query_counts.values()),
    "query exclusion count is invalid",
)
require(
    query_counts.get("selected_query_count") == 50
    and query_counts.get("input_query_record_count")
    == query_counts.get("validated_query_candidate_count")
    + query_counts.get("excluded_missing_gtf_metadata_count")
    + query_counts.get("excluded_non_lncRNA_count")
    + query_counts.get("excluded_non_primary_chromosome_count")
    + query_counts.get("excluded_noncanonical_sequence_count")
    + query_counts.get("excluded_query_length_count")
    and query_counts.get("eligible_query_transcript_count")
    == query_counts.get("validated_query_candidate_count")
    - query_counts.get("excluded_development_gene_id_count")
    - query_counts.get("excluded_development_gene_name_count")
    - query_counts.get("excluded_development_sequence_sha256_count")
    - query_counts.get("excluded_holdout_gene_id_count")
    - query_counts.get("excluded_holdout_sequence_sha256_count"),
    "selection query exclusion arithmetic drifted",
)
require(
    target_counts.get("annotation_target_candidate_count") == 668
    and target_counts.get("retained_target_count") == 668
    and target_counts.get("excluded_target_count") == 0
    and target_counts.get("chr21_annotation_target_candidate_count") == 221
    and target_counts.get("chr22_annotation_target_candidate_count") == 447
    and target_counts.get("annotation_target_candidate_count")
    == target_counts.get("retained_target_count") + target_counts.get("excluded_target_count")
    and target_counts.get("excluded_target_count")
    == target_counts.get("excluded_empty_promoter_count")
    + target_counts.get("excluded_noncanonical_promoter_count"),
    "selection target exclusion arithmetic drifted",
)

source_rows = read_tsv(
    root / "paper/bioinformatics/application_sources.tsv",
    SOURCE_FIELDS,
    "application source ledger",
)
require(len(source_rows) == 4, f"expected four source rows, found {len(source_rows)}")
require(
    all(tuple(authority) == SOURCE_FIELDS for authority in SOURCE_AUTHORITIES),
    "source authority constant schema drifted",
)
for row, authority in zip(source_rows, SOURCE_AUTHORITIES, strict=True):
    for field in SOURCE_FIELDS:
        require(
            row[field] == authority[field],
            f"source authority drifted: {authority['source_id']} {field}",
        )

authorities = {row["source_id"]: row for row in SOURCE_AUTHORITIES}
expected_source_identities = {
    "lncrna_fasta": {
        "sha256": authorities["gencode_v49_lncrna"]["compressed_sha256"],
        "size_bytes": int(authorities["gencode_v49_lncrna"]["compressed_size_bytes"]),
    },
    "annotation_gtf": {
        "sha256": authorities["gencode_v49_gtf"]["compressed_sha256"],
        "size_bytes": int(authorities["gencode_v49_gtf"]["compressed_size_bytes"]),
    },
    "chr21_fasta": {
        "sha256": authorities["ucsc_hg38_chr21"]["compressed_sha256"],
        "size_bytes": int(authorities["ucsc_hg38_chr21"]["compressed_size_bytes"]),
    },
    "chr22_fasta": {
        "sha256": authorities["ucsc_hg38_chr22"]["compressed_sha256"],
        "size_bytes": int(authorities["ucsc_hg38_chr22"]["compressed_size_bytes"]),
    },
    "development_exclusions": {
        "sha256": sha256(root / "paper/bioinformatics/development_query_exclusions.tsv", "development exclusions"),
        "size_bytes": safe_file(root / "paper/bioinformatics/development_query_exclusions.tsv", "development exclusions").st_size,
    },
    "phase2_holdout_manifest": {
        "sha256": sha256(root / "paper/bioinformatics/holdout_manifest.tsv", "Phase 2 holdout manifest"),
        "size_bytes": safe_file(root / "paper/bioinformatics/holdout_manifest.tsv", "Phase 2 holdout manifest").st_size,
    },
}
require(selection.get("source_identities") == expected_source_identities, "selection source identities drifted")

claim_fields = (
    "claim_id", "allowed_wording", "prohibited_wording", "required_evidence",
    "authoritative_source", "promotion_gate", "phase", "status",
)
claims = read_tsv(root / "paper/bioinformatics/claim_evidence.tsv", claim_fields, "claim ledger")
b3 = [row for row in claims if row["claim_id"] == "B3"]
require(len(b3) == 1 and b3[0]["phase"] == "3" and b3[0]["status"] == "pending", "claim B3 is not pending")

submission_fields = (
    "artifact_id", "path", "phase", "artifact_class", "authority",
    "freeze_or_epoch", "required", "status",
)
submission = read_tsv(
    root / "paper/bioinformatics/submission_manifest.tsv",
    submission_fields,
    "submission manifest",
)
expected_submission = (
    ("S0301", "paper/bioinformatics/application_selection.json", "application_selection", "build_application_panel.py"),
    ("S0302", "paper/bioinformatics/application_manifest.tsv", "application_manifest", "application_protocol.md"),
    ("S0303", "paper/bioinformatics/application_manifest.sha256", "application_manifest_checksum", "application_manifest.tsv"),
    ("S0304", "paper/bioinformatics/application_sources.tsv", "application_source_ledger", "provider_checksums_and_local_sha256"),
    ("S0305", "paper/bioinformatics/application_protocol.md", "application_protocol", "goal-bioinformatics.md"),
    ("S0306", "paper/bioinformatics/application_input_summary.tsv", "application_input_summary", "application_manifest.tsv"),
    ("S0307", "reproduce/bioinformatics/build_application_panel.py", "application_builder", "application_protocol.md"),
    ("S0308", "reproduce/bioinformatics/fetch_application_inputs.sh", "application_fetcher", "application_sources.tsv"),
    ("S0309", "tests/check_build_bioinformatics_application_panel.py", "application_builder_tests", "goal-bioinformatics.md"),
    ("S0310", "scripts/check_bioinformatics_phase3_freeze.sh", "preexecution_phase_gate", "goal-bioinformatics.md"),
)
phase3_rows = [row for row in submission if row["artifact_id"].startswith("S03") or row["phase"] == "3"]
require(len(phase3_rows) == 10, "submission Phase 3 row count drifted")
for row, expected in zip(phase3_rows, expected_submission, strict=True):
    artifact_id, path, artifact_class, authority = expected
    require(
        row == {
            "artifact_id": artifact_id, "path": path, "phase": "3",
            "artifact_class": artifact_class, "authority": authority,
            "freeze_or_epoch": FREEZE_ID, "required": "1", "status": "pass",
        },
        f"submission row drifted: {artifact_id}",
    )

readme = read_bytes(root / "paper/bioinformatics/README.md", "Bioinformatics README").decode("utf-8")
marker = "## Phase 3 input freeze receipt\n"
require(marker in readme, "README Phase 3 receipt missing")
receipt = readme.split(marker, 1)[1].split("\n## ", 1)[0]
for required_text in (
    f"freeze_id = {FREEZE_ID}", f"manifest_sha256 = {MANIFEST_SHA256}",
    "query_count = 50", "target_count = 668", "pair_count = 33400",
    "query_total_nt = 56381", "target_total_bp = 1670668",
    "chr21_target_count = 221", "chr22_target_count = 447",
    "fasta_file_count = 718", "record_status = preregistered_not_run",
    "application_execution_started = 0", "Phase 3 and claim B3 remain pending.",
):
    require(required_text in receipt, f"README receipt missing: {required_text}")
require(not re.search(r"\b(?:completed|decision|results?|speedup|no_go)\b", receipt.lower()), "README contains result wording")
protocol = read_bytes(
    root / "paper/bioinformatics/application_protocol.md",
    "application protocol",
).decode("utf-8")
for required_text in (FREEZE_ID, MANIFEST_SHA256, "33,400", "preregistered_not_run", "Phase 3 and B3 remain\npending"):
    require(required_text in protocol, f"protocol receipt missing: {required_text}")

allowed_paper_application = {
    "application_input_summary.tsv", "application_manifest.sha256",
    "application_manifest.tsv", "application_protocol.md",
    "application_selection.json", "application_sources.tsv",
}
for entry in (root / "paper/bioinformatics").iterdir():
    if entry.name.startswith("application_"):
        require(entry.name in allowed_paper_application, f"unexpected Phase 3 paper artifact: {entry.name}")

allowed_exact = {
    "Makefile",
    "docs/superpowers/plans/2026-07-24-bioinformatics-phase3-application-freeze.md",
    "docs/superpowers/specs/2026-07-24-bioinformatics-phase3-application-design.md",
    "paper/bioinformatics/README.md",
    "paper/bioinformatics/application_input_summary.tsv",
    "paper/bioinformatics/application_manifest.sha256",
    "paper/bioinformatics/application_manifest.tsv",
    "paper/bioinformatics/application_protocol.md",
    "paper/bioinformatics/application_selection.json",
    "paper/bioinformatics/application_sources.tsv",
    "paper/bioinformatics/submission_manifest.tsv",
    "reproduce/bioinformatics/build_application_panel.py",
    "reproduce/bioinformatics/fetch_application_inputs.sh",
    "scripts/check_bioinformatics_phase3_freeze.sh",
    "tests/check_build_bioinformatics_application_panel.py",
}


def allowed_checkpoint_path(path: str) -> bool:
    return path in allowed_exact or path.startswith("reproduce/bioinformatics/application_inputs/")


changed = subprocess.run(
    ["git", "-C", str(root), "diff", "--name-only", "-z", baseline, "--"],
    check=True,
    stdout=subprocess.PIPE,
).stdout
changed_paths = [value.decode("utf-8", errors="strict") for value in changed.split(b"\0") if value]
require(
    all(allowed_checkpoint_path(path) for path in changed_paths),
    "Phase 2 or core runtime path changed from bf94dc7: "
    + ", ".join(path for path in changed_paths if not allowed_checkpoint_path(path)),
)
status = subprocess.run(
    ["git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
    check=True,
    stdout=subprocess.PIPE,
).stdout
parts = status.split(b"\0")
status_paths: list[str] = []
index = 0
while index < len(parts) and parts[index]:
    entry = parts[index].decode("utf-8", errors="strict")
    require(len(entry) >= 4 and entry[2] == " ", f"cannot parse git status entry: {entry!r}")
    code = entry[:2]
    status_paths.append(entry[3:])
    index += 1
    if "R" in code or "C" in code:
        require(index < len(parts) and parts[index], "truncated rename in git status")
        status_paths.append(parts[index].decode("utf-8", errors="strict"))
        index += 1
require(
    all(allowed_checkpoint_path(path) for path in status_paths),
    "working tree path outside Phase 3 checkpoint: "
    + ", ".join(path for path in status_paths if not allowed_checkpoint_path(path)),
)
PY

write_application_snapshot() {
  local destination="$1"
  python3 - "$ROOT" "$destination" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path


root = Path(sys.argv[1])
destination = Path(sys.argv[2])
metadata_paths = (
    "paper/bioinformatics/application_input_summary.tsv",
    "paper/bioinformatics/application_manifest.sha256",
    "paper/bioinformatics/application_manifest.tsv",
    "paper/bioinformatics/application_protocol.md",
    "paper/bioinformatics/application_selection.json",
    "paper/bioinformatics/application_sources.tsv",
)
entries: list[dict[str, object]] = []
seen_inodes: set[tuple[int, int]] = set()


def fail(message: str) -> None:
    raise SystemExit(f"Bioinformatics Phase 3 snapshot failed: {message}")


def hash_regular(path: Path, metadata: os.stat_result) -> str:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            fail(f"unsafe regular file after open: {path}")
        if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
            fail(f"file identity changed while opening: {path}")
        digest = hashlib.sha256()
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
        after = os.fstat(descriptor)
        if (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_nlink,
            after.st_size,
            after.st_mtime_ns,
        ) != (
            opened.st_dev,
            opened.st_ino,
            opened.st_mode,
            opened.st_nlink,
            opened.st_size,
            opened.st_mtime_ns,
        ):
            fail(f"file mutated while hashing: {path}")
    finally:
        os.close(descriptor)
    current = os.lstat(path)
    if (
        current.st_dev,
        current.st_ino,
        current.st_mode,
        current.st_nlink,
        current.st_size,
        current.st_mtime_ns,
    ) != (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
    ):
        fail(f"file identity changed after hashing: {path}")
    return digest.hexdigest()


def visit(path: Path, relative: str) -> None:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        fail(f"missing frozen output: {relative}")
    common: dict[str, object] = {
        "path": relative,
        "mode": metadata.st_mode,
        "size": metadata.st_size,
        "mtime_ns": metadata.st_mtime_ns,
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "links": metadata.st_nlink,
    }
    if stat.S_ISDIR(metadata.st_mode):
        entries.append({**common, "type": "directory", "sha256": ""})
        with os.scandir(path) as iterator:
            children = sorted(iterator, key=lambda child: child.name)
        for child in children:
            visit(Path(child.path), f"{relative}/{child.name}")
        return
    if not stat.S_ISREG(metadata.st_mode):
        fail(f"symlink or special frozen output: {relative}")
    if metadata.st_nlink != 1:
        fail(f"frozen output has a hardlink alias: {relative}")
    inode = (metadata.st_dev, metadata.st_ino)
    if inode in seen_inodes:
        fail(f"frozen outputs share an inode: {relative}")
    seen_inodes.add(inode)
    entries.append(
        {**common, "type": "file", "sha256": hash_regular(path, metadata)}
    )


visit(
    root / "reproduce/bioinformatics/application_inputs",
    "reproduce/bioinformatics/application_inputs",
)
for relative in metadata_paths:
    visit(root / relative, relative)

payload = (json.dumps(entries, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("ascii")
if os.path.lexists(destination):
    existing = os.lstat(destination)
    if not stat.S_ISREG(existing.st_mode) or existing.st_nlink != 1:
        fail(f"unsafe snapshot destination: {destination}")
    flags = os.O_WRONLY | os.O_TRUNC | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
else:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
descriptor = os.open(destination, flags, 0o600)
try:
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            fail(f"short write for snapshot destination: {destination}")
        view = view[written:]
finally:
    os.close(descriptor)
PY
}

stream_cached_sources=0
write_application_snapshot "$before_snapshot"
if ((cached_source_count == 4)); then
  offline_bin="$WORK/offline-bin"
  if [[ -L "$offline_bin" || ( -e "$offline_bin" && ! -d "$offline_bin" ) ]]; then
    echo "unsafe offline command directory: $offline_bin" >&2
    exit 1
  fi
  mkdir -p -- "$offline_bin"
  if [[ -e "$offline_bin/curl" || -L "$offline_bin/curl" ]]; then
    if [[ ! -f "$offline_bin/curl" || -L "$offline_bin/curl" ]]; then
      echo "unsafe offline curl guard: $offline_bin/curl" >&2
      exit 1
    fi
    rm -f -- "$offline_bin/curl"
  fi
  printf '%s\n' \
    '#!/usr/bin/env bash' \
    'echo "Phase 3 freeze reconstruction attempted network access" >&2' \
    'exit 97' >"$offline_bin/curl"
  chmod 500 "$offline_bin/curl"
  stream_cached_sources=1
  PATH="$offline_bin:$PATH" bash "$FETCHER"
  reconstruction_status="verified_from_complete_cache"
else
  reconstruction_status="skipped_incomplete_cache"
fi
write_application_snapshot "$after_snapshot"
cmp -- "$before_snapshot" "$after_snapshot"
git -C "$ROOT" diff --check
git -C "$ROOT" diff --cached --check

echo "Bioinformatics Phase 3 application freeze checks OK"
echo "freeze_id=bioinformatics-phase3-application-v1-e8c5441c"
echo "manifest_sha256=e8c5441c36db8fb4ae28492aee20f7e1af5f357148216ef58fae03c7f52c78bc"
echo "query_count=50"
echo "target_count=668"
echo "pair_count=33400"
echo "query_total_nt=56381"
echo "target_total_bp=1670668"
echo "chr21_target_count=221"
echo "chr22_target_count=447"
echo "fasta_file_count=718"
echo "source_cache_count=$cached_source_count"
echo "source_stream_validation_delegated_to_fetcher=$stream_cached_sources"
echo "reconstruction_status=$reconstruction_status"
echo "application_execution_started=0"
