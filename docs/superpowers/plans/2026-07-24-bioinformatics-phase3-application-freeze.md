# Bioinformatics Phase 3 Application Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, validate, and commit the deterministic Phase 3 50-query by all-eligible-chr21/chr22-promoter input freeze without executing any application backend.

**Architecture:** A new self-contained Python builder streams pinned GENCODE/UCSC inputs, selects records from input metadata only, and publishes an immutable record-level manifest plus derived FASTAs transactionally. A shell fetcher reconstructs the freeze from exact source identities, while an offline checker proves counts, non-overlap, hashes, provenance, status, and the absence of Phase 3 execution artifacts. The Phase 2 builder and prior frozen evidence remain untouched.

**Tech Stack:** Python 3 standard library (`argparse`, `csv`, `gzip`, `hashlib`, `json`, `pathlib`, `tempfile`, `unittest`), Bash, GNU coreutils, Git, Make.

---

## Preconditions And File Map

Start from design commit `2dc456b`. Do not invoke `scripts/gasal2_longtarget.py`, any Fasim/GASAL2 binary, or a future `run_application.py` command in this plan. Do not create `.paper-artifacts/bioinformatics-phase3-*`.

New responsibilities:

- `reproduce/bioinformatics/build_application_panel.py`: strict parsing, deterministic selection, and staged publication.
- `tests/check_build_bioinformatics_application_panel.py`: synthetic red-green tests and committed-freeze invariants.
- `reproduce/bioinformatics/fetch_application_inputs.sh`: pinned acquisition and reconstruction.
- `reproduce/bioinformatics/application_inputs/`: selected query/promoter FASTAs only.
- `paper/bioinformatics/application_selection.json`: selection receipt and source/exclusion bindings.
- `paper/bioinformatics/application_sources.tsv`: upstream provenance.
- `paper/bioinformatics/application_manifest.tsv`: one row per query or target.
- `paper/bioinformatics/application_manifest.sha256`: manifest checksum receipt.
- `paper/bioinformatics/application_input_summary.tsv`: manifest-derived totals.
- `paper/bioinformatics/application_protocol.md`: human-readable preregistration.
- `scripts/check_bioinformatics_phase3_freeze.sh`: offline freeze checker.
- `Makefile`: `check-bioinformatics-phase3-freeze` target only.
- `paper/bioinformatics/submission_manifest.tsv`: Phase 3 freeze inventory.
- `paper/bioinformatics/README.md`: preregistered-not-run receipt.

### Task 1: Strict Source Parsing Foundation

**Files:**
- Create: `reproduce/bioinformatics/build_application_panel.py`
- Create: `tests/check_build_bioinformatics_application_panel.py`

- [ ] **Step 1: Write failing parser tests**

Create the test module with an import guard, temporary fixture writer, and these parser assertions:

```python
class ApplicationPanelBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location("build_application_panel", BUILDER)
        if spec is None or spec.loader is None:
            raise AssertionError("cannot load application builder")
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_gtf_parser_retains_required_tags_and_strand(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            gtf = Path(name) / "fixture.gtf"
            gtf.write_text(
                "chr21\tHAVANA\ttranscript\t100\t900\t.\t+\t.\t"
                'gene_id "ENSGQ.1"; transcript_id "ENSTQ.1"; gene_name "Q"; '
                'gene_type "lncRNA"; level 2; tag "basic";\n'
                "chr22\tHAVANA\ttranscript\t2000\t4000\t.\t-\t.\t"
                'gene_id "ENSGT.1"; transcript_id "ENSTT.1"; gene_name "T"; '
                'gene_type "protein_coding"; level 1; tag "MANE_Select"; '
                'tag "Ensembl_canonical";\n',
                encoding="utf-8",
            )
            transcripts = self.module.parse_gtf(gtf)
        self.assertEqual(transcripts["ENSTQ.1"].tags, frozenset({"basic"}))
        self.assertEqual(transcripts["ENSTT.1"].strand, "-")
        self.assertIn("MANE_Select", transcripts["ENSTT.1"].tags)

    def test_fasta_parser_rejects_sequence_before_header(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            fasta = Path(name) / "bad.fa"
            fasta.write_text("ACGT\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "before FASTA header"):
                self.module.parse_fasta(fasta)
```

- [ ] **Step 2: Run parser tests and capture RED**

Run:

```bash
python3 tests/check_build_bioinformatics_application_panel.py -v -k test_gtf_parser_retains_required_tags_and_strand -k test_fasta_parser_rejects_sequence_before_header
```

Expected: import or attribute failure because the builder/parser does not exist.

- [ ] **Step 3: Implement the parser foundation**

Create a Python CLI with these constants and public data shape:

```python
ROOT = Path(__file__).resolve().parents[2]
SELECTION_SEED = "gasal2-longtarget-phase3-application-v1-20260724"
ASSEMBLY = "GRCh38"
ANNOTATION_RELEASE = "GENCODE v49"
PRIMARY_CHROMOSOMES = {f"chr{i}" for i in range(1, 23)} | {"chrX"}
TARGET_CHROMOSOMES = ("chr21", "chr22")
MANIFEST_FIELDS = (
    "record_id", "record_role", "source_release", "assembly",
    "original_gene_id", "original_gene_name", "original_transcript_id",
    "selection_rule", "sequence_length", "chromosome", "strand", "tss",
    "region_start", "region_end", "sequence_sha256", "file_sha256", "path",
    "license_note", "split", "status",
)

@dataclass(frozen=True)
class Transcript:
    transcript_id: str
    gene_id: str
    gene_name: str
    gene_type: str
    chromosome: str
    start: int
    end: int
    strand: str
    level: int
    tags: frozenset[str]
```

Implement `open_text`, `sha256_file`, `sha256_stream`, `stable_id`, `sequence_sha256`, `parse_attributes`, `parse_fasta`, and streaming `parse_gtf`. Require nine GTF columns, positive coordinates, `start <= end`, strand in `{+, -}`, required IDs/names, and no duplicate transcript IDs with differing metadata. Parse every `tag` occurrence and the unquoted `level` field. FASTA parsing rejects invalid UTF-8, duplicate headers, sequence before header, and empty records.

- [ ] **Step 4: Run parser tests GREEN and existing Phase 2 builder tests**

```bash
python3 tests/check_build_bioinformatics_application_panel.py
python3 tests/check_build_bioinformatics_holdout_panel.py
```

Expected: new parser tests and all existing holdout tests pass.

- [ ] **Step 5: Commit the parsing foundation**

```bash
git add reproduce/bioinformatics/build_application_panel.py tests/check_build_bioinformatics_application_panel.py
git commit -m "feat: parse Phase 3 application sources"
```

### Task 2: Deterministic Query Selection And Exclusion

**Files:**
- Modify: `reproduce/bioinformatics/build_application_panel.py`
- Modify: `tests/check_build_bioinformatics_application_panel.py`

- [ ] **Step 1: Add failing query-selection tests**

Add fixture helpers that write five versions of one gene plus 55 additional eligible genes. Test the exact representative key and both exclusion sources:

```python
def test_query_selection_uses_priority_hash_and_both_exclusion_ledgers(self) -> None:
    selected, counts = self.module.select_queries(
        fasta_records=self.query_records,
        transcripts=self.query_transcripts,
        development_exclusions={
            "gene_id": {"ENSGDEV"}, "gene_name": set(),
            "sequence_sha256": set(),
        },
        holdout_gene_ids={"ENSGHOLD"},
        holdout_sequence_sha256={self.module.sequence_sha256("A" * 700)},
    )
    self.assertEqual(len(selected), 50)
    self.assertEqual([row["query_id"] for row in selected], [f"aq{i:03d}" for i in range(1, 51)])
    self.assertNotIn("ENSGDEV", {self.module.stable_id(row["gene_id"]) for row in selected})
    self.assertNotIn("ENSGHOLD", {self.module.stable_id(row["gene_id"]) for row in selected})
    self.assertEqual(counts["selected_query_count"], 50)

def test_query_representative_prefers_level_basic_length_then_id(self) -> None:
    representative = self.module.choose_query_representative(self.same_gene_rows)
    self.assertEqual(representative["transcript_id"], "ENST_LEVEL1_BASIC_LONG.1")
```

Also test failure with fewer than 50 eligible stable genes, noncanonical sequences, lengths 499 and 2813, duplicate selected sequence digests, and a holdout manifest with the wrong schema.

- [ ] **Step 2: Run query tests and capture RED**

```bash
python3 tests/check_build_bioinformatics_application_panel.py -v -k test_query_selection_uses_priority_hash_and_both_exclusion_ledgers -k test_query_representative_prefers_level_basic_length_then_id
```

Expected: `select_queries` and `choose_query_representative` are absent.

- [ ] **Step 3: Implement query selection exactly**

```python
def query_representative_key(row: dict[str, object]) -> tuple[object, ...]:
    return (
        int(row["level"]),
        0 if row["basic"] else 1,
        -int(row["sequence_length"]),
        str(row["transcript_id"]),
    )

def query_selection_hash(row: dict[str, object]) -> str:
    payload = "|".join((
        SELECTION_SEED,
        stable_id(str(row["gene_id"])),
        stable_id(str(row["transcript_id"])),
        str(row["sequence_sha256"]),
    ))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()
```

Parse `development_query_exclusions.tsv` with exact columns `exclusion_type,value,reason`; parse the Phase 2 manifest with its committed schema and derive stable holdout gene IDs and sequence digests. Filter before representative selection, choose one row per stable gene, sort by `(selection_hash, stable_gene_id, transcript_id)`, take exactly 50, require 50 unique stable genes and sequence digests, and assign `aq001-aq050`. Return candidate/exclusion counts for the receipt.

- [ ] **Step 4: Run full builder tests GREEN**

```bash
python3 tests/check_build_bioinformatics_application_panel.py
```

Expected: every parser and query-selection test passes.

- [ ] **Step 5: Commit query selection**

```bash
git add reproduce/bioinformatics/build_application_panel.py tests/check_build_bioinformatics_application_panel.py
git commit -m "feat: select independent Phase 3 lncRNA queries"
```

### Task 3: Representative TSS And Promoter Selection

**Files:**
- Modify: `reproduce/bioinformatics/build_application_panel.py`
- Modify: `tests/check_build_bioinformatics_application_panel.py`

- [ ] **Step 1: Add failing target-priority and coordinate tests**

Use 30-kb synthetic chr21/chr22 sequences and transcript fixtures that exercise every priority term:

```python
def test_target_representative_priority_is_exact(self) -> None:
    chosen = self.module.choose_target_representative(self.same_target_gene)
    self.assertEqual(chosen.transcript_id, "ENST_MANE.1")

def test_promoter_is_strand_aware_clipped_and_forward_genomic(self) -> None:
    plus = self.module.materialize_promoter(self.plus_transcript, "ACGT" * 7500)
    minus = self.module.materialize_promoter(self.minus_transcript, "ACGT" * 7500)
    clipped = self.module.materialize_promoter(self.near_start_transcript, "ACGT" * 7500)
    self.assertEqual((plus["region_start"], plus["region_end"]), (8000, 10500))
    self.assertEqual((minus["region_start"], minus["region_end"]), (9500, 12000))
    self.assertEqual(clipped["region_start"], 1)
    self.assertEqual(plus["sequence"], ("ACGT" * 7500)[7999:10500])
```

Add tests for `MANE_Select > Ensembl_canonical > appris_principal_1 > other appris_principal > basic > level > span > transcript_id`, one gene once, chr21/chr22 only, noncanonical promoter exclusion with counted reason, deterministic ordering, and hard failure below 300 targets.

- [ ] **Step 2: Run target tests and capture RED**

```bash
python3 tests/check_build_bioinformatics_application_panel.py -v -k test_target_representative_priority_is_exact -k test_promoter_is_strand_aware_clipped_and_forward_genomic
```

Expected: target-selection APIs are absent.

- [ ] **Step 3: Implement target selection**

```python
def target_representative_key(tx: Transcript) -> tuple[object, ...]:
    tags = tx.tags
    return (
        0 if "MANE_Select" in tags else 1,
        0 if "Ensembl_canonical" in tags else 1,
        0 if "appris_principal_1" in tags else 1,
        0 if any(tag.startswith("appris_principal") for tag in tags) else 1,
        0 if "basic" in tags else 1,
        tx.level,
        -(tx.end - tx.start + 1),
        tx.transcript_id,
    )

def promoter_bounds(tx: Transcript, chromosome_length: int) -> tuple[int, int, int]:
    tss = tx.start if tx.strand == "+" else tx.end
    start = max(1, tss - (2000 if tx.strand == "+" else 500))
    end = min(chromosome_length, tss + (500 if tx.strand == "+" else 2000))
    return tss, start, end
```

Read each chromosome as one strict FASTA record named exactly `chr21` or `chr22`. Choose one representative per stable protein-coding gene, extract forward-genomic sequence with one-based inclusive coordinates, retain non-empty canonical sequences, count every exclusion, require at least 300 targets and at least one per chromosome, sort by `(chromosome_number, tss, stable_gene_id, transcript_id)`, and assign `at0001` onward.

- [ ] **Step 4: Run full builder tests GREEN**

```bash
python3 tests/check_build_bioinformatics_application_panel.py
```

Expected: all parser, query, and target tests pass.

- [ ] **Step 5: Commit target selection**

```bash
git add reproduce/bioinformatics/build_application_panel.py tests/check_build_bioinformatics_application_panel.py
git commit -m "feat: select Phase 3 chr21 chr22 promoters"
```

### Task 4: Immutable Materialization And Record Manifest

**Files:**
- Modify: `reproduce/bioinformatics/build_application_panel.py`
- Modify: `tests/check_build_bioinformatics_application_panel.py`

- [ ] **Step 1: Add failing freeze-publication tests**

Test the exact 20-column manifest, query `NA` coordinates, repository-relative paths, FASTA/file hashes, pair/base totals, freeze-ID derivation, and publication immutability:

```python
def test_materialize_writes_exact_record_manifest_and_summary(self) -> None:
    result = self.module.build_freeze(self.synthetic_inputs, self.output_paths)
    rows = read_tsv(self.output_paths.manifest)
    self.assertEqual(tuple(rows[0]), self.module.MANIFEST_FIELDS)
    self.assertEqual(sum(row["record_role"] == "query" for row in rows), 50)
    self.assertGreaterEqual(sum(row["record_role"] == "target" for row in rows), 300)
    self.assertTrue(all(row["status"] == "preregistered_not_run" for row in rows))
    self.assertEqual(result["pair_count"], 50 * result["target_count"])

def test_existing_different_freeze_is_rejected_without_mutation(self) -> None:
    self.output_paths.manifest.write_text("drift\n", encoding="utf-8")
    before = fingerprint_tree_no_follow(self.sandbox)
    with self.assertRaisesRegex(ValueError, "existing .* drift"):
        self.module.build_freeze(self.synthetic_inputs, self.output_paths)
    self.assertEqual(fingerprint_tree_no_follow(self.sandbox), before)
```

Also inject failure after every publish step and prove rollback/no partial tree; reject symlinked destinations and parent components; rerun against an identical existing freeze and prove byte stability.

- [ ] **Step 2: Run publication tests and capture RED**

```bash
python3 tests/check_build_bioinformatics_application_panel.py -v -k test_materialize_writes_exact_record_manifest_and_summary -k test_existing_different_freeze_is_rejected_without_mutation
```

Expected: missing `build_freeze` and output schema.

- [ ] **Step 3: Implement staged freeze publication**

Define frozen `SourceInputs` and `FreezePaths` dataclasses containing every input and destination path. Expose `build_freeze(inputs: SourceInputs, outputs: FreezePaths, after_publish: Callable[[int, Path], None] | None = None) -> dict[str, object]` so tests can inject failures without invoking a subprocess. Test `setUp` constructs `self.synthetic_inputs` and `self.output_paths` from its temporary fixture tree.

Add `select` and `materialize` subcommands over the same APIs. `select` writes canonical, sort-keyed JSON through create-or-byte-identical publication. `materialize` revalidates selection against source data, stages the exact FASTA tree and tabular outputs, computes the manifest digest and freeze ID, then publishes only when every destination is absent or byte-identical.

Use these exact manifest constants:

```python
COMMON = {
    "source_release": "GENCODE v49",
    "assembly": "GRCh38",
    "split": "application",
    "status": "preregistered_not_run",
}
QUERY_LICENSE = (
    "GENCODE project data are open access; selected derived FASTA retained with "
    "source attribution; final redistribution approval remains owner-controlled"
)
TARGET_LICENSE = (
    "UCSC data-use conditions and Genome Reference Consortium attribution apply; "
    "selected promoter FASTA retained; final redistribution approval remains owner-controlled"
)
SUMMARY_FIELDS = (
    "freeze_id", "manifest_sha256", "query_count", "target_count", "pair_count",
    "query_total_bp", "target_total_bp", "chr21_target_count", "chr22_target_count",
    "min_query_length", "max_query_length", "annotation_target_candidate_count",
    "excluded_target_count",
)
```

Require `query_count == 50`, `target_count >= 300`, `pair_count >= 15000`, unique IDs/paths/query genes/query sequence digests/target genes, and exact FASTA hashes. Use `lstat` and no-follow traversal throughout. Stage into a sibling directory, fsync files/directories, and restore pre-existing files after injected exceptions.

- [ ] **Step 4: Run all builder tests and static checks GREEN**

```bash
python3 tests/check_build_bioinformatics_application_panel.py
python3 -m py_compile reproduce/bioinformatics/build_application_panel.py tests/check_build_bioinformatics_application_panel.py
git diff --check
```

Expected: all pass with no mutation on negative cases.

- [ ] **Step 5: Commit immutable materialization**

```bash
git add reproduce/bioinformatics/build_application_panel.py tests/check_build_bioinformatics_application_panel.py
git commit -m "feat: materialize immutable Phase 3 application inputs"
```

### Task 5: Pin Upstream Sources And Reconstruction

**Files:**
- Create: `reproduce/bioinformatics/fetch_application_inputs.sh`
- Modify: `reproduce/bioinformatics/build_application_panel.py`
- Modify: `tests/check_build_bioinformatics_application_panel.py`

- [ ] **Step 1: Add failing source-identity and fetch-boundary tests**

Assert the builder exposes exactly these four source identities:

```text
gencode_v49_lncrna md5=6d52ea2c72933c864e46a560fe0b5d4c compressed_sha256=1f04e509309fa74b694ef3cc1e52c1c8173bb0e679f8a22785fa43ecadd28ef4 compressed_bytes=37870043 decompressed_sha256=4c632018e0198d76fe76471baa5511a1c07af86bf7bab6ce6747edb8d5add5ae decompressed_bytes=223740848
gencode_v49_gtf md5=0ef4a024ea2d35b1b88c12447b0b70b9 compressed_sha256=d6e6fe0515c95b2a8cd36a853c1989cee9115c736c60237c56ae92b9daaaf7c4 compressed_bytes=93374019 decompressed_sha256=ff32fd55c6799b3b94fe10aa17b2b5d4da952fa1de12fe44afadf32e949ec914 decompressed_bytes=3323462848
ucsc_hg38_chr21 md5=184df2bd9b812b6e6b6da16c6021369e compressed_sha256=c979ca1e5065c2521a50773473e0d0cc018fd6f3e9bb3aa90493fe7b45d57d1b compressed_bytes=12709705 decompressed_sha256=35c71b68436d1a278ecb6a1e875af3ba4020738a028a7feac769a6d62790ae1f decompressed_bytes=47644190
ucsc_hg38_chr22 md5=41b47ce1cc21b558409c19b892e1c0d1 compressed_sha256=05f9d97d6fbfd08a44ca45b50837ca2ae9c471f35ba79dffec04d2cb5eaaf695 compressed_bytes=12255678 decompressed_sha256=ce3ee1ca39356238f7aee438a40a88b4f1b9d80b316b263e16fb12402212d10f decompressed_bytes=51834845
```

Test that `--create-freeze` is the only creation flag, default mode requires committed outputs, partial downloads are cleaned, valid cached files are reused, and no command string contains a workflow/backend invocation.

- [ ] **Step 2: Run source tests and capture RED**

```bash
python3 tests/check_build_bioinformatics_application_panel.py -v -k test_exact_upstream_source_identities -k test_fetch_script_has_no_execution_command
```

Expected: source identities and fetch script are absent.

- [ ] **Step 3: Implement source ledger rendering and fetch script**

Add immutable `SourceSpec` constants for these URLs:

```text
https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.lncRNA_transcripts.fa.gz
https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.annotation.gtf.gz
https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr21.fa.gz
https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz
```

Render `application_sources.tsv` with exact fields:

```text
source_id role provider release assembly url upstream_md5 compressed_size_bytes
compressed_sha256 decompressed_size_bytes decompressed_sha256 local_source_path
license_or_terms redistribution_note download_command status
```

The Bash script uses `set -euo pipefail`, `curl -fL --retry 3`, a PID-specific partial, MD5/SHA/size validation before `mv`, and a cleanup trap. It stores four gzip files in `.tmp/bioinformatics_application_sources`, verifies each uncompressed stream without retaining whole chromosomes, runs builder `select` into a temporary receipt, compares that receipt in default mode, and runs `materialize` to prove byte identity. With `--create-freeze`, it publishes only absent destinations through the builder.

- [ ] **Step 4: Run unit tests and shell syntax GREEN**

```bash
python3 tests/check_build_bioinformatics_application_panel.py
bash -n reproduce/bioinformatics/fetch_application_inputs.sh
git diff --check
```

Expected: pass; no application execution artifact exists.

- [ ] **Step 5: Commit pinned reconstruction code**

```bash
git add reproduce/bioinformatics/build_application_panel.py reproduce/bioinformatics/fetch_application_inputs.sh tests/check_build_bioinformatics_application_panel.py
git commit -m "repro: pin Phase 3 application input sources"
```

### Task 6: Generate And Inspect The Real Input Freeze

**Files:**
- Create: `reproduce/bioinformatics/application_inputs/queries/*.fa`
- Create: `reproduce/bioinformatics/application_inputs/targets/*.fa`
- Create: `paper/bioinformatics/application_selection.json`
- Create: `paper/bioinformatics/application_sources.tsv`
- Create: `paper/bioinformatics/application_manifest.tsv`
- Create: `paper/bioinformatics/application_manifest.sha256`
- Create: `paper/bioinformatics/application_input_summary.tsv`
- Create: `paper/bioinformatics/application_protocol.md`

- [ ] **Step 1: Acquire/verify sources and create only the freeze**

```bash
bash reproduce/bioinformatics/fetch_application_inputs.sh --create-freeze
```

Expected: exactly 50 queries, at least 300 targets, at least 15,000 pairs, and no backend command. Record the printed exact target count, pair count, manifest SHA-256, and freeze ID. Do not change selection rules in response to counts.

- [ ] **Step 2: Independently inspect generated records**

```bash
(cd paper/bioinformatics && sha256sum -c application_manifest.sha256)
find reproduce/bioinformatics/application_inputs -type f | sort | wc -l
python3 tests/check_build_bioinformatics_application_panel.py
git status --short
```

Independently recompute from TSV/FASTAs: 50 unique query genes and digests, target count/chromosome split, pair/base totals, coordinate-derived FASTA sequences, no development or holdout overlap, and every path/hash/length.

- [ ] **Step 3: Write protocol with exact frozen values**

Create `application_protocol.md` from the design and generated summary. It must name four sources/hashes, selection seed, exact query/target/pair/base counts, representative rules, all exclusion counts, manifest hash/freeze ID, no-positive-control decision, planned A/B/C modes, two-worker policy, one excluded pilot, full run, 10x20 six-repeat subset, 24 h budget, no-retry policy, and `preregistered_not_run` status. It prohibits result-based scale reduction and candidate-only B3 claims.

- [ ] **Step 4: Prove default reconstruction is byte-stable**

```bash
before=$(git status --porcelain=v1); bash reproduce/bioinformatics/fetch_application_inputs.sh; after=$(git status --porcelain=v1); test "$before" = "$after"
```

Expected: reconstruction succeeds and changes no repository file.

- [ ] **Step 5: Leave the freeze uncommitted for gate wiring**

Do not commit yet. Checkpoint 1 is not frozen until Task 7 adds and passes the offline gate in the same final freeze commit.

### Task 7: Offline Freeze Gate And Preregistration Commit

**Files:**
- Create: `scripts/check_bioinformatics_phase3_freeze.sh`
- Modify: `Makefile`
- Modify: `paper/bioinformatics/submission_manifest.tsv`
- Modify: `paper/bioinformatics/README.md`
- Modify: `tests/check_build_bioinformatics_application_panel.py`
- Include: all Task 6 freeze files

- [ ] **Step 1: Add failing checkpoint tests**

```python
def test_phase3_freeze_has_no_execution_artifacts(self) -> None:
    forbidden = (
        ROOT / ".paper-artifacts/bioinformatics-phase3-application-v1",
        ROOT / "reproduce/bioinformatics/run_application.py",
        ROOT / "paper/bioinformatics/source_data/application_runs.tsv",
    )
    self.assertTrue(all(not path.exists() for path in forbidden))
    self.assertTrue(all(row["status"] == "preregistered_not_run" for row in read_manifest()))

def test_make_target_wires_offline_freeze_checker(self) -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    self.assertIn("check-bioinformatics-phase3-freeze:", makefile)
    self.assertIn("scripts/check_bioinformatics_phase3_freeze.sh", makefile)
```

Add `read_manifest()` beside the existing TSV fixture reader; it must assert the exact `MANIFEST_FIELDS` header before returning rows.

- [ ] **Step 2: Run checkpoint tests and capture RED**

```bash
python3 tests/check_build_bioinformatics_application_panel.py
```

Expected: checker/Make/submission receipt tests fail.

- [ ] **Step 3: Implement offline checker and metadata wiring**

The checker must:

1. run the full builder test module;
2. run Python/Bash/JSON syntax checks and both Git whitespace checks;
3. verify manifest checksum, exact schema/summary, every FASTA path/hash/length,
   50 queries, targets >=300, pairs >=15000, chr21+chr22 only, canonical
   sequence, and unique required IDs/digests;
4. recompute development and holdout non-overlap;
5. validate the four-row source ledger against exact constants;
6. require every record `preregistered_not_run` and B3 `pending`;
7. reject result/source-data rows, Phase 3 raw roots, runner, execution receipt,
   retry/exclusion ledger, or completed state;
8. prove all Phase 2 files and core runtime paths unchanged from `bf94dc7`;
9. snapshot the application input tree before/after with recursive `lstat` and
   SHA-256, rejecting symlinks and mutation.

Wire this target:

```make
check-bioinformatics-phase3-freeze:
	WORK=$(or $(WORK),$(CURDIR)/.tmp/check_bioinformatics_phase3_freeze) bash ./scripts/check_bioinformatics_phase3_freeze.sh
```

Add sequential `S0301...S0310` rows for selection receipt, manifest, manifest checksum, source ledger, protocol, input summary, builder, fetcher, builder tests, and freeze checker. Use the generated freeze ID, `required=1`, and `status=pass`, matching the Phase 2 logical-artifact precedent rather than listing every derived FASTA separately. Add a Phase 3 receipt to `paper/bioinformatics/README.md` with exact counts/hash and `application_execution_started = 0`; do not mark Phase 3 or B3 complete.

- [ ] **Step 4: Run complete freeze gate**

```bash
make check-bioinformatics-phase3-freeze
git diff --check
git diff --cached --check
```

Expected: exit 0; exact counts printed; `application_execution_started=0`; Phase 2/runtime unchanged.

- [ ] **Step 5: Stage only checkpoint-1 files, inspect, and commit**

```bash
git add Makefile paper/bioinformatics/README.md paper/bioinformatics/application_input_summary.tsv paper/bioinformatics/application_manifest.sha256 paper/bioinformatics/application_manifest.tsv paper/bioinformatics/application_protocol.md paper/bioinformatics/application_selection.json paper/bioinformatics/application_sources.tsv paper/bioinformatics/submission_manifest.tsv reproduce/bioinformatics/application_inputs scripts/check_bioinformatics_phase3_freeze.sh tests/check_build_bioinformatics_application_panel.py
git diff --cached --name-status
git diff --cached --check
git commit -m "data: freeze Phase 3 biological application panel"
```

The builder/fetcher should already be committed by Tasks 1-5; include them here only if review fixes changed them after Task 5.

### Task 8: Exact-Tree Reviews And Handoff

**Files:**
- Review: all changes from `2dc456b` through the checkpoint-1 freeze commit

- [ ] **Step 1: Run specification review**

Compare every committed file/count against `goal-bioinformatics.md` Phase 3.1-3.3, the design spec, and this plan. Reject under-scale panels, missing fields, weaker exclusion, result-dependent choice, positive-control overclaim, or any execution before the manifest commit.

- [ ] **Step 2: Fix and re-review specification findings test-first**

For each finding, add the smallest failing regression, confirm RED, implement one focused fix, run GREEN, and repeat until no Critical or Important finding remains.

- [ ] **Step 3: Run code-quality and evidence-integrity review**

Probe transactional publication, symlinks, path traversal, duplicate IDs, coherently mutated receipts, source drift, omitted/extra FASTAs, manifest/summary mismatch, Phase 2 guards, and accidental backend invocation. Reject any open Critical or Important finding.

- [ ] **Step 4: Run final verification on reviewed commit**

```bash
make check-bioinformatics-phase3-freeze
git status --short --branch
git show --stat --oneline HEAD
git diff HEAD^ --check
```

Expected: exit 0, clean worktree, only checkpoint-1 files in the freeze commit, and no Phase 3 execution artifact.

- [ ] **Step 5: Record runner-design boundary**

Update the active plan: checkpoint 1 complete; checkpoint 2 runner preregistration in progress. Do not run a pilot or formal pair until the runner and exact attempt plan receive their own reviewed commit.
