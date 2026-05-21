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

For later process-level GPU scheduling, the same runner can be launched under
`CUDA_VISIBLE_DEVICES=<id>` and `taskset -c <cores>`. Scheduler logic is not part
of this first PR.

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
```

The check builds `fasim_longtarget_x86`, creates a deterministic two-contig
fixture from `testDNA.fa`, runs Fasim once on the multi-contig target, runs Fasim
once per contig shard, merges shard output, and verifies digest equality.

Expected report fields include:

```text
shard_count
shard_ids
per_shard[*].target_name
per_shard[*].records
per_shard[*].digest
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
next PR should add a process-level worker scheduler:

- Assign shards by estimated work, preferably observed or estimated DP cells.
- Launch one Fasim process per worker.
- Set `CUDA_VISIBLE_DEVICES` per worker.
- Optionally pin CPU cores with `taskset`.
- Keep merged digest validation as the release gate.
