# Fasim Sharded Worker Density on 2 GPUs: Repeated Runs

This note repeats the local 2-GPU worker-density characterization to check
whether the `workers_per_gpu=3` signal is stable. It uses the same workload and
wrapper as the single-run density checkpoint.

## Scope

This is a docs/result PR only:

- No default scheduler policy is changed.
- No chunk splitting is added.
- No overlap heuristic is added.
- No in-process multi-GPU runtime is added.
- No Fasim C++ runtime or output semantics are changed.
- No 4-GPU scaling is claimed.

The goal is to determine whether the best local worker density is stable across
repeated runs before considering any default-off scheduler convenience option.

## Workload

```text
workload: rheMac10_nonchrom_top8_H19
target:   top 8 contigs from rheMac10NonChromosome.fa
contigs:  8
RNA:      H19.fa
rule:     1
binary:   fasim_longtarget_cuda
GPU ids:  0,1
runs:     3
```

## Command

Each run used:

```bash
timeout 1800s python3 scripts/benchmark_fasim_sharded_worker_workload_matrix.py \
  --workload rheMac10_nonchrom_top8_H19:.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa:H19.fa:1 \
  --fasim-bin ./fasim_longtarget_cuda \
  --work-dir .tmp/fasim_sharded_worker_density_2gpu_repeated/run_<n> \
  --output-mode lite \
  --workers 1,2,3,4,6,8 \
  --gpu-ids 0,1 \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

Optional SSW AVX2/ProfileContext add-ons were not enabled.


Reconciliation note: this historical run recorded final-speed-stack environment
labels. The current repo-local Fasim binary now reads
`FASIM_TRANSFERSTRING_TABLE`, `FASIM_GPU_DP_COLUMN_AUTO`,
`FASIM_SSW_PROFILE_CACHE`, and `FASIM_EXACT_COLUMN_EXTEND_BATCH` as default-off
opt-ins, but this document was not rerun after that integration. Treat the
timings as historical telemetry, not fresh evidence for the reconciled binary.

## Correctness

All 3 runs were digest clean for every worker count:

```text
all_digest_match:          true for run 1, run 2, run 3
merged_records:            1184
duplicate_records_removed: 5
```

The merged digest remained:

```text
fbc012361b80491e4b4ecca6a04735b8657b49f6b9d167763ecb9139e300ef15
```

## Per-Run Winners

| run | best workers | best wall seconds |
|---:|---:|---:|
| 1 | 6 | 5.6514 |
| 2 | 6 | 4.9807 |
| 3 | 6 | 4.9969 |

The best worker count was stable across all three runs.

## Median Density Results

| workers | workers/GPU | median wall seconds | min wall | max wall | median speedup vs 1 worker | median speedup vs 2 workers |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.5 | 21.5385 | 21.0513 | 21.8635 | 1.0000x | 0.5229x |
| 2 | 1.0 | 11.1923 | 11.1109 | 11.2615 | 1.9126x | 1.0000x |
| 3 | 1.5 | 8.4118 | 8.3241 | 9.1436 | 2.5290x | 1.3209x |
| 4 | 2.0 | 6.0151 | 5.9887 | 6.7630 | 3.5807x | 1.8553x |
| 6 | 3.0 | 4.9969 | 4.9807 | 5.6514 | 4.3244x | 2.2236x |
| 8 | 4.0 | 5.6520 | 5.3827 | 5.8137 | 3.7607x | 1.9802x |

Raw wall seconds:

| workers | run 1 | run 2 | run 3 |
|---:|---:|---:|---:|
| 1 | 21.0513 | 21.5385 | 21.8635 |
| 2 | 11.1923 | 11.2615 | 11.1109 |
| 3 | 8.3241 | 9.1436 | 8.4118 |
| 4 | 6.7630 | 6.0151 | 5.9887 |
| 6 | 5.6514 | 4.9807 | 4.9969 |
| 8 | 5.6520 | 5.3827 | 5.8137 |

## Interpretation

The repeated runs confirm the single-run signal: local oversubscription helps,
and `6 workers / 2 GPUs` was best in all three runs. This corresponds to:

```text
workers_per_gpu = 3
```

The `8 workers / 2 GPUs` mode was slower than `6 workers / 2 GPUs` by median
wall time, so oversubscription has a practical limit for this workload.

Validated here:

```text
digest-clean repeated density on one 8-contig workload
2-GPU process-level scaling
stable local best at workers_per_gpu=3 for this workload
```

Not validated here:

```text
general default worker policy
4-GPU scaling
single-contig chunking
safe-overlap chunk mode
```

## Decision

`workers_per_gpu=3` is a stronger local 2-GPU scheduling candidate after these
repeated runs. It should still not become a default policy from this PR.

Reasonable next steps:

```text
1. Repeat density characterization on a larger 8+ contig workload.
2. Add a default-off scheduler option such as --workers-per-gpu.
3. Keep explicit worker counts as the safe default until broader workload data exists.
```

If broader workloads show noisy or negative oversubscription, keep
`workers_per_gpu=1` as the safer default and leave density as a manual tuning
choice.
