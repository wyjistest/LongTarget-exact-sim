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
explicitly. For the current clean-base CUDA path, the usual local opt-in shape
is preAlign CUDA plus CPU extension threads and the align profile cache:

```bash
env -u FASIM_CUDA_DEVICES \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=6 \
FASIM_ALIGN_PROFILE_CACHE=1 \
python3 ./scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_sharded \
  --output-mode lite
```

Equivalent per-worker env overrides can also be passed with repeated `--env`
arguments:

```bash
--env FASIM_ENABLE_PREALIGN_CUDA=1 \
--env FASIM_EXTEND_THREADS=6 \
--env FASIM_ALIGN_PROFILE_CACHE=1
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
  --env FASIM_ENABLE_PREALIGN_CUDA=1 \
  --env FASIM_EXTEND_THREADS=6 \
  --env FASIM_ALIGN_PROFILE_CACHE=1
```

With `--gpu-ids`, each worker is intentionally made a single-visible-GPU
process: the runner sets `CUDA_VISIBLE_DEVICES=<assigned physical GPU>`, sets
`FASIM_CUDA_DEVICE=0`, and strips inherited `FASIM_CUDA_DEVICES` from the
worker environment. This keeps multi-GPU use at the process-sharding layer:
each worker sees one GPU, while the parent runner schedules independent shard
processes. CPU core ranges are optional and use `taskset`; provide one range
per worker when used. When estimated DP cells are unavailable, shard assignment
falls back to target sequence length.

Do not use parent-level `FASIM_CUDA_DEVICES=0,1` as the recommended current-base
multi-GPU mode. The current runner policy is process-level sharding, one visible
GPU per worker.

Use `--workers-per-gpu N` with `--gpu-ids` to derive the worker count as
`len(gpu_ids) * N`. This is a default-off convenience option and is mutually
exclusive with `--workers`; it does not change scheduler defaults.

Use `--auto-cpu-core-ranges` with `--cpu-pool` and
`--cpu-cores-per-worker` to derive one `taskset` range per worker. Explicit
`--cpu-core-ranges` still works and remains mutually exclusive with auto CPU
range derivation. Without these CPU options, worker CPU binding remains off.

## Grouped Target Records

`--group-target-records N` is a default-off option for tiny-region workloads
with many small FASTA records. It groups up to `N` complete target records into
one worker shard FASTA, reducing subprocess, scheduling, and merge overhead:

```bash
python3 ./scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target tiny_regions.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_grouped \
  --output-mode lite \
  --workers 4 \
  --gpu-ids 0,1 \
  --group-target-records 16
```

This is record grouping, not chunking:

```text
does:     record1 + record2 + ... + recordN in one shard FASTA
does not: split one target record, add overlap, or rewrite coordinates
```

Grouped shard file names may use a synthetic group label, but the FASTA records
inside each grouped shard preserve the original headers and sequences. The
canonical merge still sorts and de-duplicates exact output records, independent
of worker completion order.

Grouped runs report:

```text
target_record_count
group_target_records
grouped_shard_count
per_shard[*].group_member_count
per_shard[*].group_member_headers
per_shard[*].group_member_names
per_shard[*].group_member_ranges
per_shard[*].group_member_input_digests
```

When manifests are enabled, the run config digest includes the grouping mode,
group size, grouped shard count, shard plan, and group member metadata. Changing
`--group-target-records` under `--resume` is treated as an incompatible run
config and reruns the affected shards instead of reusing stale grouped outputs.

## Manifest and Resume

Long sharded runs can write an auditable manifest:

```bash
python3 ./scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_sharded \
  --manifest .tmp/fasim_sharded/run_manifest.json \
  --output-mode lite \
  --workers-per-gpu 3 \
  --gpu-ids 0,1
```

When `--manifest` is used, an existing run directory with a manifest requires
either `--resume` or `--force`. `--resume` only skips a shard when the previous
manifest entry is compatible with the current run config, the shard input digest
matches, the output file exists, and the recorded output digest still matches.
Otherwise the shard is rerun. `--force` clears the old work directory and starts
a new run id.

`--keep-going` records failed shards and continues other workers. A run with any
failed shard is marked `run_status=incomplete`; it writes only
`partial_merged_digest`, leaving the final `merged_digest` unset so partial
outputs cannot be mistaken for a complete whole-target result.

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
make check-fasim-group-target-records
```

The check builds `fasim_longtarget_x86`, creates a deterministic two-contig
fixture from `testDNA.fa`, runs Fasim once on the multi-contig target, runs Fasim
once per contig shard, merges shard output, and verifies digest equality.

The scheduler check runs both the baseline sharded mode and a two-worker
scheduled mode, then verifies that both merged outputs have the same canonical
digest and record counts.

The grouped target-record check creates a deterministic three-record target
fixture, verifies default sharding still produces one shard per record, verifies
`--group-target-records 2` preserves the single-run digest and original FASTA
headers, verifies same-config resume reuses grouped shards, and verifies a
changed group size is rejected by the manifest digest and rerun.

Expected report fields include:

```text
shard_count
target_record_count
group_target_records
grouped_shard_count
shard_ids
per_shard[*].target_name
per_shard[*].group_member_count
per_shard[*].group_member_headers
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
