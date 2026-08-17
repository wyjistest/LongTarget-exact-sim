# Fasim GASAL2 Long-Query Architecture Phase 0 Baseline

## Scope

This ledger freezes the pre-optimization state required by `goal.md` Phase 0.
It records evidence and contract boundaries; it does not change runtime behavior.

```text
runtime_source_commit = 9949e258861ed3852c2c9cd363c1ecec3ee6fd89
branch = gasal2-kcnq1ot1-focused-review
tracked_worktree_at_capture = clean
untracked_execution_input_at_capture = goal.md
runtime behavior change = 0
```

The Phase 0 documentation/check commit changes only `Makefile`, documentation,
the Phase 0 checker, and the execution-state file. The Fasim, CUDA, and GASAL2
runtime sources remain unchanged.

## Build And Runtime Environment

Fresh two-step build command used for the Phase 0 receipt:

```bash
make setup-gasal2 \
  GASAL2_DIR=.tmp/fasim_gasal2_long_query_phase0_clean_build/GASAL2

make build-fasim-gasal2 \
  CUDA_HOME=/usr/local/cuda-12.5 \
  CUDA_ARCH=89 \
  GASAL2_DIR=.tmp/fasim_gasal2_long_query_phase0_clean_build/GASAL2 \
  GASAL2_GPU_SM_ARCH=sm_89 \
  GASAL2_MAX_QUERY_LEN=2812 \
  GASAL2_N_CODE=0x4E \
  FASIM_GASAL2_TARGET=.tmp/fasim_gasal2_long_query_phase0_clean_build/fasim_longtarget_gasal2
```

```text
compiler = g++ 9.4.0
CUDA = 12.5 (V12.5.82)
GPU 0 = NVIDIA GeForce RTX 4090, 24,564 MiB, compute capability 8.9
GPU 1 = NVIDIA GeForce RTX 4090, 24,564 MiB, compute capability 8.9
SM arch = sm_89
CPU = Intel Core i9-10900X, 10 cores / 20 threads
GASAL2 commit = 106d94ee53fc847214fb05f2f9f892538a5d3baf
GASAL2_MAX_QUERY_LEN = 2812
GASAL2_N_CODE = 0x4E
worker/GPU binding = single worker or one worker per visible GPU
fresh_build_receipt = .tmp/fasim_gasal2_long_query_phase0_clean_build
fresh_setup_elapsed_seconds = 2.87
fresh_build_elapsed_seconds = 67.84
fresh_build_max_rss_kb = 656032
fresh_build_binary_sha256 = 9e8241405d523b5a741dffb13c8e5923bbc4f0a8f38bef4179f68006ffedf27f
earlier_phase0_work_binary_sha256 = 55923ffa73458d6a2bb3ae852b429c2ec289fed5fc95875e164345dd1f73fe44
```

The repository Makefile defaults generic `CUDA_ARCH` to 80; the recorded GASAL2
build explicitly used 89, while `GASAL2_GPU_SM_ARCH` is `sm_89`.
The fresh and earlier work binaries have different digests, so Phase 0 claims a
successful source/setup rebuild, not bit-for-bit binary reproducibility.

## Input Ledger

| Input | Path | SHA-256 | Availability |
|---|---|---|---|
| H19 query | `H19.fa` | `7d94fb9515b0fa63dbe8fb62e01bb50616760ce80eeef29ec9c3893af8040f4e` | tracked |
| small DNA fixture | `testDNA.fa` | `7c44698a4ca63482ae0ae6c2c4aca4f2f13ff43ba3a5bbcf8543aed685bbdbb1` | tracked |
| chr22 10-12 Mb fixture | `.tmp/fasim_gasal2_chr22_slice_10m_12m.fa` | `e36fd5e349179420d36f7a2cca4503dbe1e82ad4d7eecb88afd421f0f23099ea` | local benchmark input |
| KCNQ1OT1 ENST00000597346.1 | `.tmp/fasim_gasal2_query_inputs/KCNQ1OT1_ENST00000597346.fa` | `f8883e1855017b7a28576770a8c8476a8eb1adbfcbef08d55c6dc74c49a86cc4` | external/local |
| chr22 full | `.tmp/characterize_fasim_gasal2_gpu_scoreinfo_full_record/input/chr22.fa` | `ce3ee1ca39356238f7aee438a40a88b4f1b9d80b316b263e16fb12402212d10f` | external/local |

The lightweight Phase 0 runtime smoke requires the local chr22 10-12 Mb
fixture and verifies its digest through the archive manifest. It does not
silently substitute another target.

## Required Path Audit

All Phase 0 paths named by `goal.md` exist at the recorded commit:

```text
scripts/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot.sh
scripts/merge_fasim_segmented_tfosorted.py
scripts/compare_fasim_lite_offline_cluster_topk.py
docs/fasim_gasal2_archive_first_output.md
docs/fasim_gasal2_workload_matrix.tsv
docs/fasim_gasal2_two_slot_recommended_runtime_readiness.md
```

Existing implementations reused by later phases:

| Purpose | Existing implementation |
|---|---|
| archive restore | `scripts/restore_fasim_tfosorted_column_archive_probe.py` |
| archive integrity/manifest | `scripts/check_fasim_tfo_archive_integrity.py`, `scripts/check_fasim_gasal2_archive_manifest.py` |
| complete/lite row comparator | `scripts/compare_fasim_lite_full_equivalence.py` |
| raw TFO and three unclustered rankings | `scripts/compare_fasim_tfosorted_tfo_contract.py` |
| one C++-style offline clustered ordering | `scripts/compare_fasim_lite_offline_cluster_topk.py` |
| sampled RSS/GPU memory | `scripts/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu.py` |
| existing checks | `check-sample`, `check-fasim-gasal2-reproducible-setup`, `check-fasim-lite-full-equivalence`, `check-fasim-gasal2-top5-output-contract`, `check-fasim-gasal2-archive-first-output` |

## Frozen Contracts

```text
Contract A: complete output
  missing_rows = 0
  extra_rows = 0
  row_count_equal = 1
  byte identity only when the workload is deterministic and explicitly checked

Contract B: clustered top5
  score-ranked clustered TFO1-5 equality
  stability-ranked clustered TFO1-5 equality
  Nt-ranked clustered TFO1-5 equality
  overlap alone is not equality

Contract C: shifted-grid stability
  grid_0_vs_grid_256 equality is useful evidence
  it does not imply unsegmented full-length equivalence

Contract D: archive-first restore
  the archive restores the claimed TFOsorted exactly
  schema/version and input digests are recorded
  the archive-first fast path emits no full TFOsorted text
```

CPU/existing exact output remains authority. GPU endpoint, CIGAR, traceback,
output, and digest authority remain zero. Every clean fast-path claim also
requires all applicable fallback, OOM, allocation, ordering, and state counters
to be zero.

The current repository does not have one comparator that proves score-ranked,
stability-ranked, and Nt-ranked results after the same clustering pass. The raw
three-ranking comparator and the single-order offline clustered comparator are
separate evidence surfaces. Phase 0 therefore freezes Contract B as a required
future gate and does not infer it from either surface alone.

## Reproduced Small-Fixture Evidence

### H19 Archive-First, chr22 10-12 Mb

```text
source = reproduced
artifact = .tmp/fasim_gasal2_long_query_phase0/archive_first_serial
contract = Contract A byte identity + Contract D
legacy_run_wall_seconds = 3.329254
archive_run_wall_seconds = 2.461832
restore_wall_seconds = 0.260316
gasal2_requests = 564,454
traceback_requests = 175,193
exact_column_tasks = 10,368
exact_column_cells = 51,840,000
exact_column_wall_seconds = 0.317187
exact_column_kernel_seconds = 0.238053
peak_gpu_memory = NA (not captured)
peak_host_rss = NA (not captured)
legacy_text_bytes = 1,836,889
archive_bytes = 321,411
archive_gzip_bytes = 133,990
restored_rows = 8,291
restored_equal = 1
legacy_only_rows = 0
archive_only_rows = 0
archive_manifest_valid = 1
archive_version = 2
gasal2_fallbacks = 0
length_guard_fallbacks = 0
```

This is the Phase 0 archive-first exactness authority. The two GPU-heavy
smokes were run serially; the earlier accidental parallel OOM attempts are
excluded from the ledger.

### H19 Segmentation Diagnostic, chr22 10-12 Mb

```text
source = reproduced
artifact = .tmp/fasim_gasal2_long_query_phase0/h19_segmented_serial
query_len = 2812
segment_len = 2048
segments = 2
unsegmented_wall_seconds = 3.326104
segmented_wall_sum_seconds = 5.395844
segmented_flush_total_seconds = 4.230580
gasal2_requests = 1,548,224
traceback_requests = 490,924
segmented_only_exact_column_tasks = 20,736
segmented_only_exact_column_cells = 103,680,000
segmented_only_exact_column_wall_seconds = 0.421997
segmented_only_exact_column_kernel_seconds = 0.264271
gasal2_fallbacks = 0
length_guard_fallbacks = 0
top5_offline_cluster_equal = true
top5_tfo_score_equal = true
top5_tfo_stability_equal = true
top5_tfo_nt_score_equal = false
full_missing_rows = 35
full_extra_rows = 1115
```

This diagnostic does not satisfy Contract A or complete Contract B. Its
offline clustered 5/5 result is retained as evidence only and is not promoted
to segmented equivalence. The unsegmented comparator input is another GASAL2
run, not the CPU authority, so this diagnostic cannot establish GPU output
authority.

### Compound FASTA Header Archive Gap

An exploratory reuse of the archive check with tracked `testDNA.fa` found:

```text
source = reproduced
artifact = .tmp/fasim_gasal2_long_query_phase0/testdna_compound_header_archive
testDNA.fa compound-header archive probe = fail
expected_failure_exit = 2
restored_equal = 0
legacy_only_rows = 144
archive_only_rows = 144
```

The legacy rows contain `Chr=chr11` and absolute genome offsets derived from
`>hg19|chr11|2158478-2162843`; the current column-archive restore helper emits
an empty chromosome and record-local coordinates. Therefore Contract D is
currently claimed only for the reproduced simple-header chr22 fixture. Phase 1
must cover target record metadata before making a broader segmented
archive-first claim.

## Committed Artifact Ledger

These values are read from tracked documents at the runtime source commit; they
were not rerun during Phase 0.

```text
source = committed_artifact
artifact = docs/fasim_gasal2_workload_matrix.tsv

chr22_full complete row-set:
  Contract A = pass (canonical row-set; byte identity not claimed)
  speedup = 0.993x
  fallbacks = 0

chr1_full complete row-set:
  Contract A = pass (canonical row-set; byte identity not claimed)
  speedup = 1.094x
  fallbacks = 0

chr21+chr22 short-query top5:
  recorded raw three-ranking top5 = pass
  complete clustered Contract B = not established by one comparator
  speedup = 40.119x
  fallbacks = 0

NEAT1 first64:
  query_len = 22,767, GPU path inactive
  speedup = 1.009x

MALAT1 first8:
  status = fallback/fail for broad replacement
  speedup = 0.702x
  fallbacks = 3,091
```

Non-H19 short-query panel:

```text
source = committed_artifact
artifact = docs/fasim_gasal2_short_query_generalization_panel.md
completed_rows = 11
raw score/stability/Nt top5 clean supported rows = 9
raw score/stability/Nt top5 clean supported non-H19 rows = 8
median_speedup_clean = 12.567938x
negative_controls_guarded = 3
```

This is a raw-ranking contract-checked panel, not complete clustered Contract B
and not a universal short-query guarantee. MEG3 full and
KCNQ1OT1-mid-1024 retain documented ranking mismatches.

Two-slot low-density resource evidence:

```text
source = committed_artifact
artifact = docs/fasim_gasal2_flush_two_slot_multi_worker_2gpu.md
workers = 1
peak_host_rss = 1.35 GB sampled
peak_gpu_memory = 19.75 GB sampled
two_slot_wall_reduction = 9.90%

workers = 2, GPUs = 0,1
peak_host_rss = 2.12 GB sampled
peak_gpu_memory = 39.49 GB aggregate sampled
two_slot_wall_reduction = 10.71%

workers = 4 or 6
result = GASAL2 CUDA OOM in synchronous and two-slot modes
```

The frozen supported density is one worker per 24 GB GPU. These sampled peaks
are not substituted for missing KCNQ1OT1-run memory telemetry.

## User-Provided Full KCNQ1OT1 Result

The local artifact can be parsed, but the 2.4-hour run was not regenerated in
Phase 0 and is not committed as a reproducible benchmark artifact. Per the
execution contract it remains externally sourced:

```text
source = user_provided_external_result
verified_in_current_checkout = 0
artifact = .tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_chr22_full_fullquery
query_len = 91,667
target = chr22 full, 50,818,468 bp
segment_len = 2,048
segment_overlap = 512
grid_shifts = 0,256
total_segment_runs = 121
wall_sum_seconds = 8,687.413318
wall_sum_hours = 2.413170
flush_total_seconds = 8,025.737500
gasal2_extend_wall_seconds = 6,192.920800
gasal2_convert_wall_seconds = 4,286.883300
gasal2_requests = 2,189,813,851
traceback_requests = 918,240,875
exact_column_tasks = 46,562,736
exact_column_cells = 232,813,680,000
exact_column_wall_seconds = 911.212000
exact_column_kernel_seconds = 545.095930
artifact_bytes = 5,530,128,435
peak_gpu_memory = NA (not captured)
peak_host_rss = NA (not captured)
gasal2_fallbacks = 0
length_guard_fallbacks = 0
shifted_grid_offline_cluster_overlap = 5/5
```

Only Contract C is supported by this comparison. Contract A, unsegmented
full-length equivalence, all three Contract B rankings, full hg38 validation,
and archive-first output are not established by this result.

The external workdir predates the benchmark artifact schema in `goal.md`: it
has per-segment stdout/stderr/wall files and summaries, but no captured
`memory_summary.txt`, complete run manifest, or committed input bundle.

## Phase 0 Gate

The lightweight aggregate entry reuses existing checks and the known-good
archive fixture:

```bash
make check-fasim-gasal2-long-query-phase0
```

It verifies:

```text
reproducible setup contract
CPU authority sample exactness
archive integrity and manifest parsers
synthetic lite/full comparator exactness
frozen top5 output contract
short-query raw score/stability/Nt top5 fixture
archive-first runtime activation and byte-identical restore
archive schema, manifest, and input digests
baseline document/source-label consistency
goal.md Phase 0 state
```

Long KCNQ1OT1 runs are never triggered by this target.

## Phase 0 Decision

```text
clean checkout build reproducible = 1
small fixture exactness clean = 1
archive-first existing smoke clean = 1
baseline inputs have digests = 1
all claims have explicit contract = 1
external/unverified metrics labeled = 1
runtime behavior change = 0
decision = phase_0_baseline_frozen
```
