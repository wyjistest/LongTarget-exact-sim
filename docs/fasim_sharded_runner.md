# Fasim Sharded Runner

This document describes the first process-level sharding step for Fasim. The
goal is to run existing Fasim binaries independently on target FASTA records and
merge record outputs deterministically, without changing Fasim runtime behavior.

## Scope

The first version is intentionally narrow:

- Shards are FASTA records, typically chromosomes or contigs.
- No internal chromosome chunking is implemented.
- No chunk overlap is inferred or applied.
- No in-process multi-GPU runtime is added.
- No Fasim scoring, threshold, non-overlap, output, GPU AUTO, SSW, SIM-close, or
  recovery behavior is changed.

This keeps correctness gated on a simple check:

```text
single multi-contig run canonical digest == sharded merged canonical digest
```

## Runner

Use `scripts/fasim_sharded_runner.py` with an existing Fasim binary:

```bash
python3 ./scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_x86 \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_sharded \
  --output-mode lite \
  --validate-single
```

The runner writes:

- `shard_plan.json`: contig-level shard metadata.
- `shard_outputs/<shard_id>/`: per-shard Fasim outputs.
- `merged/merged-TFOsorted.lite` or `merged/merged-TFOsorted`: canonical merged
  output.
- `single_output/`: optional single-run output when `--validate-single` is set.
- `report.json`: shard telemetry, digests, and validation result.

## Environment

The runner does not default-enable speed options. Pass worker environment
explicitly:

```bash
python3 ./scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_sharded \
  --output-mode lite \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

Optional add-ons can also be passed explicitly:

```bash
--env FASIM_SSW_AVX2=1 \
--env FASIM_SSW_PROFILE_CONTEXT=1
```

For process-level worker scheduling, pass explicit worker options. The runner
still launches ordinary Fasim subprocesses; it does not add an in-process
multi-GPU runtime.

```bash
python3 ./scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_sharded \
  --output-mode lite \
  --workers 2 \
  --gpu-ids 0,1 \
  --cpu-core-ranges 0-7,8-15 \
  --env FASIM_TRANSFERSTRING_TABLE=1 \
  --env FASIM_GPU_DP_COLUMN_AUTO=1 \
  --env FASIM_SSW_PROFILE_CACHE=1 \
  --env FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

`--gpu-ids` values are assigned to workers as `CUDA_VISIBLE_DEVICES`. CPU core
ranges are optional and use `taskset`; provide one range per worker when used.
When estimated DP cells are unavailable, shard assignment falls back to target
sequence length.

## Merge Semantics

The merge step supports `lite` and `tfosorted` record outputs. It:

1. Reads each shard output.
2. Validates that all headers match.
3. Sorts records by canonical record fields.
4. Removes exact duplicate records.
5. Writes a stable merged output and SHA-256 digest.

The merge does not depend on worker completion order.

## Validation

Run the local check:

```bash
make check-fasim-sharded-runner
make check-fasim-sharded-scheduler
```

The check builds `fasim_longtarget_x86`, creates a deterministic two-contig
fixture from `testDNA.fa`, runs Fasim once on the multi-contig target, runs Fasim
once per contig shard, merges shard output, and verifies digest equality.

The scheduler check runs both the baseline sharded mode and a two-worker
scheduled mode, then verifies that both merged outputs have the same canonical
digest and record counts.

Expected report fields include:

```text
shard_count
shard_ids
per_shard[*].target_name
per_shard[*].records
per_shard[*].digest
worker_count
gpu_ids
cpu_core_ranges
per_worker[*].worker_id
per_worker[*].gpu_id
per_worker[*].shard_ids
sharded_records
merged_records
duplicate_records_removed
single_records
single_digest
merged_digest
single_vs_sharded_digest_match
```

## Current Limits

This runner is safe for chromosome/contig-level sharding. It should not be used
for arbitrary chunk splitting yet. Chunking needs a separate safe-overlap design
derived from the window planner, maximum extension span, record coordinates, and
downstream non-overlap semantics.

If a contig-level single-vs-sharded digest differs, fix canonical merge or output
normalization before adding any scheduler or multi-GPU work.

## Next Step

After digest equality is stable on representative multi-contig fixtures, the
next PR should characterize process-level scaling:

- Compare one, two, and four workers where hardware is available.
- Record per-worker wall time, CPU/GPU assignment, records, digests, and
  fallbacks.
- Keep merged digest validation as the release gate.
