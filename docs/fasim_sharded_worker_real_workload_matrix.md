# Fasim Sharded Worker Real Workload Matrix

This note records a real multi-contig characterization run for the process-level
sharded worker path. It uses the workload-matrix wrapper added in the previous
checkpoint and does not change runner behavior.

## Scope

This is a characterization result only:

- No chunk splitting is added.
- No overlap heuristic is added.
- No in-process multi-GPU runtime is added.
- No Fasim C++ runtime or output semantics are changed.
- Speed environment variables remain explicit.
- Digest equality is the correctness gate before any scaling interpretation.

The measured workload has two contigs, so only 1-worker and 2-worker modes are
meaningful. A 4-worker run would leave workers idle and is not claimed here.

## Workload

```text
workload: hg38_chr21_chr22_H19
target:   hg38 chr21 + chr22 combined FASTA
contigs:  2
RNA:      H19.fa
rule:     1
binary:   fasim_longtarget_cuda
GPU ids:  0,1
```

The target FASTA used for this run was a local combined file:

```text
.tmp/fasim_sharded_worker_workload_matrix_real/inputs/hg38_chr21_chr22.fa
```

## Command

```bash
timeout 1800s python3 scripts/benchmark_fasim_sharded_worker_workload_matrix.py \
  --workload hg38_chr21_chr22_H19:.tmp/fasim_sharded_worker_workload_matrix_real/inputs/hg38_chr21_chr22.fa:H19.fa:1 \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_sharded_worker_real_workload_matrix/run \
  --output-mode lite \
  --workers 1,2 \
  --gpu-ids 0,1 \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

Optional SSW AVX2/ProfileContext add-ons were not enabled for this run.


Reconciliation note: this historical run recorded final-speed-stack environment
labels. The current repo-local Fasim binary now reads
`FASIM_TRANSFERSTRING_TABLE`, `FASIM_GPU_DP_COLUMN_AUTO`,
`FASIM_SSW_PROFILE_CACHE`, and `FASIM_EXACT_COLUMN_EXTEND_BATCH` as default-off
opt-ins, but this document was not rerun after that integration. Treat the
timings as historical telemetry, not fresh evidence for the reconciled binary.

## Correctness

Digest equality held for both worker counts:

```text
single_digest == merged_digest: yes
all_digest_match:              true
merged_records:                8469
duplicate_records_removed:     19
digest:                        7989c37f364067fb48e01e50c6fdc495be2c44f03b9092a880db136d15f19628
```

## Timing

`wall_seconds` is the sharded worker wall time reported by the scaling wrapper.
`runner_total_seconds` includes the validation single-run audit for that worker
count, so it is useful for end-to-end benchmark cost but should not be used as
the sharded execution speedup numerator.

| workers | wall seconds | speedup vs 1 worker | speedup vs single whole run | runner total seconds | digest match |
|---:|---:|---:|---:|---:|:---|
| 1 | 265.9265 | 1.0000x | 0.9997x | 533.2415 | yes |
| 2 | 135.0982 | 1.9684x | 1.9677x | 401.6237 | yes |

Per-shard timing was balanced:

| worker mode | chr21 seconds | chr22 seconds | chr21 records | chr22 records |
|---:|---:|---:|---:|---:|
| 1 worker | 133.5987 | 132.1391 | 3009 | 5460 |
| 2 workers | 135.0087 | 132.5594 | 3009 | 5460 |

Per-worker timing in the 2-worker run:

| worker | seconds | records |
|---:|---:|---:|
| 0 | 132.7377 | 5460 |
| 1 | 135.0982 | 3009 |

## Interpretation

The two-contig workload shows near-linear 1-to-2 worker scaling while preserving
the single-run digest. This supports process-level contig sharding as the right
outer-parallel direction for multi-contig workloads.

This does not prove 4-worker or whole-genome scaling. A 4-worker claim needs a
4+ contig workload. Whole-genome claims need a larger workload matrix with the
same digest gate.

Single-contig workloads such as only chr11 or only chr21 still cannot scale via
contig-level sharding. Scaling those requires a separate chunking and
safe-overlap design.

## Next Steps

Use the same wrapper on:

```text
4+ chromosome hg38 subset
larger multi-contig target
whole-genome FASTA, if feasible
```

If digest equality remains clean and scaling is limited by imbalance, improve
estimated-cells assignment before changing runtime behavior. If digest differs,
fix merge/canonicalization before making any performance claim.
