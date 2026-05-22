# Fasim Sharded Worker Primary-Contig Matrix

This note records a real primary-contig subset matrix using the whole-genome
readiness stack: manifest-backed runs, CPU affinity, GPU worker assignment, and
single-vs-sharded digest validation. It is a runtime characterization result
for the current repo-local `hg38_chr21_chr22_H19` input, not a full hg38 or
4-GPU scaling claim.

## Scope

Validated here:

- real hg38 primary-contig subset execution
- manifest-backed sharded runs
- automatic CPU core ranges
- 2-GPU process-level scheduling
- digest equality for 1/2/4/6 worker modes
- shard-count-limited behavior predicted by the #137 balance analysis

Out of scope:

- full hg38 primary assembly scaling
- 4-GPU scaling
- chunk splitting or overlap
- in-process multi-GPU
- Fasim C++ runtime or output semantic changes
- default worker policy changes

## Workload

```text
workload: hg38_chr21_chr22_H19
target: .tmp/fasim_sharded_worker_workload_matrix_real/inputs/hg38_chr21_chr22.fa
contigs: 2
rna: H19.fa
rule: 1
binary: ./fasim_longtarget_cuda
GPUs: 0,1
CPU pool: 0-17
CPU cores per worker: 3
auto CPU ranges: enabled
output mode: lite
```

Current-checkout input discovery found this two-contig hg38 subset and the
rheMac10 top4/top8 nonchromosomal workloads. It did not find a full hg38 primary
FASTA in the current checkout. This result therefore documents the available
primary-contig subset only.

Per-worker environment:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

Run command:

```bash
timeout 3600s python3 scripts/benchmark_fasim_sharded_worker_workload_matrix.py \
  --workload hg38_chr21_chr22_H19:.tmp/fasim_sharded_worker_workload_matrix_real/inputs/hg38_chr21_chr22.fa:H19.fa:1 \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_primary_contig_sharded_worker_matrix/run \
  --output-mode lite \
  --workers 1,2,4,6 \
  --gpu-ids 0,1 \
  --manifest \
  --auto-cpu-core-ranges \
  --cpu-pool 0-17 \
  --cpu-cores-per-worker 3 \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

## Correctness

Digest equality held for every worker count:

```text
all_digest_match: true
merged_digest: 7989c37f364067fb48e01e50c6fdc495be2c44f03b9092a880db136d15f19628
single_digest: 7989c37f364067fb48e01e50c6fdc495be2c44f03b9092a880db136d15f19628
merged_records: 8469
duplicate_records_removed: 19
failed_shards: []
resumed_shards: []
```

## Timing

`wall_seconds` is the sharded worker wall time reported by the scaling wrapper.
Each worker-count run also performs a single whole-target digest audit; that
audit is a correctness gate and is not a performance mode.

| workers | GPUs | CPU ranges | wall seconds | speedup vs 1 worker | speedup vs single whole run | digest |
| ---: | --- | --- | ---: | ---: | ---: | --- |
| 1 | 0,1 | 0-2 | 290.3157 | 1.0000x | 0.9599x | clean |
| 2 | 0,1 | 0-2,3-5 | 145.3164 | 1.9978x | 1.9178x | clean |
| 4 | 0,1 | 0-2,3-5,6-8,9-11 | 145.3926 | 1.9968x | 1.9168x | clean |
| 6 | 0,1 | 0-2,3-5,6-8,9-11,12-14,15-17 | 148.4319 | 1.9559x | 1.8775x | clean |

The best row is 2 workers on 2 GPUs. This is expected for a two-contig workload:
additional workers have no extra contig shards to run.

## Worker Utilization

The 6-worker row shows the shard-count limit directly:

| worker | GPU | CPU range | wall seconds | records | assigned shard |
| ---: | --- | --- | ---: | ---: | --- |
| 0 | 0 | 0-2 | 148.4319 | 5460 | chr22 |
| 1 | 1 | 3-5 | 146.0768 | 3009 | chr21 |
| 2 | 0 | 6-8 | 0.0000 | 0 | none |
| 3 | 1 | 9-11 | 0.0000 | 0 | none |
| 4 | 0 | 12-14 | 0.0000 | 0 | none |
| 5 | 1 | 15-17 | 0.0000 | 0 | none |

Per-shard timings were stable across worker counts:

| workers | chr21 seconds | chr22 seconds | chr21 records | chr22 records |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 145.1927 | 144.9319 | 3009 | 5460 |
| 2 | 144.5529 | 145.1743 | 3009 | 5460 |
| 4 | 139.2136 | 145.2791 | 3009 | 5460 |
| 6 | 146.0127 | 148.3128 | 3009 | 5460 |

## Interpretation

This confirms the full readiness stack on a real primary-contig subset: the
runner can use manifests, CPU affinity, explicit GPU assignment, and
single-vs-sharded digest validation while preserving output identity.

The 4/6 worker rows should not be read as failed scaling. They are
shard-count-limited diagnostics: there are only two contig shards, so workers
above two are idle by design. This matches the #137 shard-balance prediction for
`hg38_chr21_chr22_H19`.

## Decision

```text
validated:
  real primary-contig subset digest equality
  manifest-backed execution
  CPU affinity
  2 workers / 2 GPUs near 2x vs 1 worker
  4/6 worker shard-count-limited behavior

not claimed:
  full hg38 scaling
  4-GPU scaling
  default workers_per_gpu policy
  single-contig parallelism
  chunking / overlap safety
```

Next useful primary-contig matrix needs a larger current-checkout FASTA with at
least 4 primary contigs. If that input is unavailable, the next code/design step
should not be chunking by default; first add or stage a larger primary-contig
input and rerun this matrix.
