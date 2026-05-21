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

`--cpu-core-ranges` is optional. When provided, it must include one comma-
separated range per worker, and each Fasim subprocess is launched through
`taskset -c <range>`.

## Report Fields

`report.json` extends the sharded runner report with:

```text
worker_count
gpu_ids
cpu_core_ranges
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
merged_records
merged_digest
single_digest
single_vs_sharded_digest_match
duplicate_records_removed
```

## Validation

Run:

```bash
make check-fasim-sharded-scheduler
```

The check creates the same deterministic two-contig fixture used by the base
sharded runner check. It runs baseline sharded mode and a two-worker scheduled
mode, then verifies that the scheduled merged digest and record counts match the
baseline and optional single-run digest.

## Next Step

The next step should be characterization, not new runtime behavior: compare
one, two, and four workers on representative hardware, collect per-worker wall
time and digest telemetry, and keep single-vs-sharded digest equality as the
gate before considering chunk splitting or safe-overlap work.
