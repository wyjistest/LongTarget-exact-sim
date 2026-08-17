# GASAL2-LongTarget Paper Data Freeze

```text
data_freeze_id = paper-data-v1-dccfd49-20260716
paper_runtime_epoch = 0
paper_runtime_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
collector_parent_commit = dccfd49
analysis_seed = 20260715
bootstrap_resamples = 10000
```

This freeze contains derived source data reconstructed from immutable Phase 2-4
receipts, comparator summaries, and manifests. The source-data manifest does not
hash itself or this document; each listed data file is hashed directly.

## Provenance

- Workload manifest SHA-256: `b099762257b60ce2922a7e19920bad30e05b9cdf2af4381c60596a41ca3cb7d3`
- Collector SHA-256: `23808c3bb8f085f6199e3099a9541434984833f0ad25a1414ab0963fcaab7514`
- Analyzer SHA-256: `bc35a214e01ff19ce2a7f2f49c0be437a77860c4fab02abd2528c685e15b0afc`

Artifact manifest SHA-256 values:

- `phase2`: `d6d4bd7b6ffa98f4ae510694816b4d4c906274f92a9121b6dab7adacdec05ce4`
- `phase3`: `ef16dbbb7250304a46ac28d2584bedfd1186e3497fd7bc8038b3b004edc52b40`
- `phase4`: `6bc1e07681db54d0c543512b835b0030b702c366a31645b480e20bf4aedf4fec`

## Frozen Files

- `benchmark_runs.tsv`: `d120fbce6af2170d34b124cefd31ed0192b6990faa79c1a4656762e5728777a3` (167 rows, 88313 bytes)
- `paired_speedups.tsv`: `1d28a8cb9c7acb1f2e8c7e0189ea2b7d1f5b9b7f9a440c4395e8bfb10f205ae5` (61 rows, 30445 bytes)
- `correctness.tsv`: `f169ebe401b44dc19167a7ca055219301d1793b693b9a06866dbbf66df013e2a` (64 rows, 18359 bytes)
- `generalization.tsv`: `d136e5380b9c9c40cdc96238dc07c8c07925f1ab8e1c543088259550e05bc589` (16 rows, 3243 bytes)
- `ablation.tsv`: `497e10a216071617893ea238c0fa15e66d36ddb07c91f3505af53122cd44c5f0` (7 rows, 2216 bytes)
- `resources.tsv`: `127e2c8f9bf0fad5444f86de167e806a7d19500077571a9781d0313665658c96` (8 rows, 3353 bytes)
- `archive_first.tsv`: `ff7fddde636663c59f79cc19977e0071a39738b094a37e8144a74f43860c09e0` (6 rows, 2670 bytes)
- `operating_envelope.tsv`: `4c8c0fad548dec9e224c699eee3b3f69f20ec19349ce80cce7d1e7a988d174b4` (6 rows, 2051 bytes)
- `exclusions.tsv`: `063d3a235e57c44999f35b26b02d0fa36a5b458e7f33c17c25e3b7fcc6245233` (56 rows, 18000 bytes)
- `paired_speedup_summary.tsv`: `f8bbfc76dbd7edc1855e14c25deaad96bbde44972cf930ef6834aad76236ecae` (21 rows, 11180 bytes)
- `paired_speedup_summary.json`: `927176644c4800a311f83352c7b0ebf60264d3c6c56eb57c323e34f3dd00cb0b` (21 rows, 30412 bytes)

## Statistical Contract

- Paired speedup is recomputed as baseline wall time divided by candidate wall time.
- Summaries report median, inclusive IQR, and observed range.
- Median bootstrap 95% intervals use seed `20260715` and `10000` resamples.
- Workloads with fewer than three pairs have no bootstrap interval.
- Mismatch rows remain included and are not treated as technical exclusions.

## Known Limitations

- The primary hardware evidence is from one GPU generation.
- Fast top-K equivalence is not full-output row-set equivalence.
- Three preregistered supported-query workloads retain clustered TFO1-5 mismatches.
- Full-output workloads are near parity rather than a broad acceleration result.
- KCNQ1OT1 long-query evidence is bounded to max8 dual-grid execution.
- Full KCNQ1OT1 transcript coverage was not run.
- Full hg38 was not run.
- High-density multi-worker configurations on 24 GB GPUs retain OOM evidence; one worker per GPU is the supported density.
- Raw benchmark artifacts remain external under `.paper-artifacts/` and are not tracked in Git.
