# Fasim Sharded Worker Scaling

This note describes the characterization step for the process-level sharded
worker scheduler. It measures one, two, and four worker modes using the existing
contig sharded runner and deterministic merge gate.

## Scope

This is a measurement wrapper only:

- No Fasim C++ runtime behavior is changed.
- No chunk splitting or chunk overlap is added.
- No in-process multi-GPU runtime is added.
- Fasim runtime environment variables remain explicit.
- Validation mode is used for digest audit, not as a performance setting.

## Usage

For a local smoke characterization:

```bash
make benchmark-fasim-sharded-worker-scaling
```

For a larger workload, call the script directly:

```bash
python3 ./scripts/benchmark_fasim_sharded_worker_scaling.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_sharded_worker_scaling \
  --output-mode lite \
  --workers 1,2,4 \
  --gpu-ids 0,1,2,3 \
  --cpu-core-ranges 0-7,8-15,16-23,24-31 \
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_PREALIGN_CUDA_TOPK=64 \
  --env FASIM_VERBOSE=0
```

Pass runtime add-ons only when the binary was built for them and the run is
intended to characterize them. The current repo-local Fasim code reads
`FASIM_TRANSFERSTRING_TABLE`, `FASIM_SSW_PROFILE_CACHE`,
`FASIM_GPU_DP_COLUMN_AUTO`, `FASIM_EXACT_COLUMN_EXTEND_BATCH`,
`FASIM_SSW_PROFILE_CONTEXT`, and `FASIM_SSW_AVX2`; `FASIM_SSW_AVX2` only
activates in binaries built with `FASIM_SIMD_FLAGS=-mavx2`.

## Report

The script writes `report.json` in the chosen work directory. The top-level
fields include:

```text
worker_counts
baseline.single_seconds
baseline.sharded_wall_seconds
runs[*].worker_count
runs[*].runner_total_seconds
runs[*].wall_seconds
runs[*].worker_seconds_sum
runs[*].speedup_vs_single
runs[*].speedup_vs_1_worker
runs[*].per_worker
runs[*].per_shard
runs[*].merged_records
runs[*].merged_digest
runs[*].single_digest
runs[*].single_vs_sharded_digest_match
runs[*].duplicate_records_removed
runs[*].fallbacks
runs[*].mismatches
summary.all_digest_match
summary.best_worker_count
summary.best_wall_seconds
```

`wall_seconds` is the sharded worker phase estimate, computed from the maximum
per-worker wall time reported by the sharded runner. `runner_total_seconds`
includes script overhead and validation audit time, so it is reported separately.

## Correctness Gate

Every worker-count run must satisfy:

```text
single_vs_sharded_digest_match = true
merged_digest == 1-worker merged_digest
```

If either check fails, fix deterministic merge or shard output handling before
making scaling claims.

## Interpretation

This PR should not claim production scaling by itself. The fixture target is
small and exists to verify the report contract. Larger characterization should
run on representative chromosome or multi-RNA workloads after the scheduler PR
is merged.
