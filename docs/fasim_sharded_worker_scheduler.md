# Fasim Sharded Worker Scheduler

This note describes the second process-level sharding step. It adds worker
scheduling to the existing contig sharded runner without changing Fasim runtime
behavior.

## Scope

The scheduler is intentionally conservative:

- Shards are still FASTA records, typically chromosomes or contigs.
- Each worker runs ordinary Fasim subprocesses.
- `CUDA_VISIBLE_DEVICES` is set per worker only when requested.
- CPU pinning uses `taskset` only when `--cpu-core-ranges` is provided.
- No chunk splitting, chunk overlap, in-process multi-GPU runtime, scoring,
  threshold, non-overlap, output, GPU AUTO, SSW, SIM-close, or recovery behavior
  changes are made.

## Usage

```bash
python3 ./scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_sharded \
  --output-mode lite \
  --workers 4 \
  --gpu-ids 0,1,2,3 \
  --cpu-core-ranges 0-7,8-15,16-23,24-31 \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

Optional Fasim add-ons remain explicit:

```bash
--env FASIM_SSW_AVX2=1 \
--env FASIM_SSW_PROFILE_CONTEXT=1
```

## Scheduling

The scheduler assigns shards with static largest-first balancing. It uses
estimated DP cells when available and falls back to target sequence length
otherwise. This keeps scheduling deterministic and avoids coupling scheduler
behavior to Fasim internals.

`--gpu-ids` is a comma-separated list. Values are assigned to workers as
`CUDA_VISIBLE_DEVICES`, wrapping when there are more workers than GPU ids.

`--workers-per-gpu N` is a convenience option. When it is provided with
`--gpu-ids`, the runner derives:

```text
worker_count = len(gpu_ids) * N
```

For example, `--gpu-ids 0,1 --workers-per-gpu 3` launches six workers and
assigns GPU ids round-robin. This option is mutually exclusive with
`--workers`; passing both is an error. Passing `--workers-per-gpu` without
`--gpu-ids` is also an error.

This is not a default policy. Local repeated 2-GPU characterization found
`workers_per_gpu=3` to be the best candidate for the
`rheMac10_nonchrom_top8_H19` workload, but users should tune the value per
hardware and workload. That result is not evidence for 4-GPU scaling.

`--cpu-core-ranges` is optional. When provided, it must include one comma-
separated range per worker, and each Fasim subprocess is launched through
`taskset -c <range>`.

CPU ranges can also be derived explicitly:

```bash
python3 ./scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_sharded \
  --output-mode lite \
  --gpu-ids 0,1 \
  --workers-per-gpu 3 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-23 \
  --cpu-cores-per-worker 4
```

This derives one range per worker:

```text
worker 0: 0-3
worker 1: 4-7
worker 2: 8-11
worker 3: 12-15
worker 4: 16-19
worker 5: 20-23
```

`--auto-cpu-core-ranges` is mutually exclusive with explicit
`--cpu-core-ranges`. It requires both `--cpu-pool` and
`--cpu-cores-per-worker`, and errors if the pool does not contain enough cores.
No CPU binding is enabled unless explicit or auto CPU ranges are configured.

## Report Fields

`report.json` extends the sharded runner report with:

```text
worker_count
gpu_ids
workers_per_gpu
workers_derived_from_gpu_ids
gpu_sharing_mode
cpu_core_ranges
cpu_pool
cpu_cores_per_worker
auto_cpu_core_ranges
taskset_enabled
per_worker[*].worker_id
per_worker[*].gpu_id
per_worker[*].cpu_core_range
per_worker[*].shard_ids
per_worker[*].estimated_length
per_worker[*].estimated_cells
per_worker[*].wall_seconds
per_worker[*].records
per_worker[*].raw_records
per_shard[*].worker_id
per_shard[*].gpu_id
per_shard[*].cpu_core_range
```

The existing merged output and digest fields remain the correctness gate:

```text
run_status
merged_records
merged_digest
partial_merged_digest
single_digest
single_vs_sharded_digest_match
duplicate_records_removed
failed_shards
resumed_shards
```

When `--manifest` is provided, `run_manifest.json` also records run config and
input digests, per-shard status, per-shard stdout/stderr paths, output digests,
and whether a shard was skipped by `--resume`.

## Validation

Run:

```bash
make check-fasim-sharded-scheduler
make check-fasim-sharded-runner-resume
make check-fasim-sharded-cpu-affinity
```

The check creates the same deterministic two-contig fixture used by the base
sharded runner check. It runs baseline sharded mode and a two-worker scheduled
mode, then verifies that the scheduled merged digest and record counts match the
baseline and optional single-run digest.

The resume check covers fresh manifest creation, strict resume skipping,
missing-output rerun, `--force`, default existing-work-dir protection, and
`--keep-going` incomplete-run reporting.

The CPU affinity check covers explicit CPU ranges, auto-derived ranges,
conflicting CPU options, insufficient CPU pools, manifest CPU binding fields,
and resume incompatibility when CPU binding changes.

## Next Step

The next step should be characterization, not new runtime behavior: compare
one, two, and four workers on representative hardware, collect per-worker wall
time and digest telemetry, and keep single-vs-sharded digest equality as the
gate before considering chunk splitting or safe-overlap work.
