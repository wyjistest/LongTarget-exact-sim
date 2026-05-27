# Fasim Score Bridge Stop Checkpoint

This note records the current decision for the GPU score bridge line after the
score-only bridge prototype and real-workload characterization.

## Scope

This is a docs-only checkpoint:

- No runtime code is changed.
- No env is added or defaulted.
- No GPU score result is used for production output.
- No GPU endpoint authority is added.
- No GPU CIGAR or traceback is added.
- No scoring, threshold, non-overlap, scheduler, merge, chunking, or
  in-process multi-GPU behavior is changed.

CPU `aligner.Align()` remains authoritative for score, endpoint, traceback,
CIGAR, candidate state, output, and digest.

## Evidence

The current score-only GPU bridge path is:

```text
FASIM_ALIGN_SCORE_BRIDGE_GPU_SHADOW=1
FASIM_ALIGN_SCORE_BRIDGE_GPU_SHADOW_MAX_REQUESTS=<cap>
```

It is a default-off diagnostic shadow. It does not feed GPU score, endpoint, or
any alignment result into the real Fasim path.

The real-workload characterization on rheMac10 top8 and hg38 chr21+chr22 found
the contract shape clean:

```text
digest clean: 12/12
preAlign CUDA fallbacks: 0
bridge score mismatches: 0
bridge endpoint mismatches: 0
```

The performance result is no-go for the current implementation:

```text
rheMac10 top8 full processed rows:
  workers=4: 2.06-2.12x CPU forward score/end
  workers=6: 2.88-3.07x CPU forward score/end

hg38 chr21+chr22 capped processed-only estimate:
  cap 1,000:   1.51x CPU
  cap 10,000:  1.21x CPU
  cap 50,000:  1.16x CPU
  cap 100,000: 1.16x CPU
```

The low-copy bridge reduced retained request data compared with the older
copied snapshot scaffold, but the conservative batch DP kernel now dominates
total time. This is not a copy-only failure.

## Decision

Stop the current GPU score bridge implementation as a performance path.

Keep the bridge and related telemetry as diagnostic/research scaffolding only:

```text
allowed:
  score/end contract smoke
  diagnostic telemetry
  future comparison against a different DP execution design

not allowed:
  real opt-in
  endpoint authority
  CIGAR / traceback
  production output integration
  performance claims for the current conservative batch DP kernel
```

Do not continue by tuning the current score bridge scaffold. It has already
answered the current question:

```text
score/end contract:
  clean

current bridge performance:
  slower than CPU forward score/end
```

## Restart Criteria

Only restart the GPU score line with a materially different DP execution design,
for example:

```text
warp/diagonal/striped GPU DP
query/profile resident execution
contiguous target-window staging
minimal H2D/D2H
bounded flushes
no copied request snapshots
```

A restart still must stay shadow-first and pass hard gates before any further
promotion:

```text
score_mismatches = 0
digest unchanged
GPU total < CPU forward score/end on real workloads
pack/H2D/kernel/D2H/unpack costs are itemized
endpoint remains diagnostic only
no GPU CIGAR or traceback
no GPU production output authority
```

If a different GPU DP design cannot beat CPU forward score/end as a score-only
shadow, do not pursue full `aligner.Align()` GPU replacement.

## Current Practical Runtime

The current clean-base practical runtime remains:

```bash
env -u FASIM_CUDA_DEVICES \
FASIM_ENABLE_PREALIGN_CUDA=1 \
FASIM_EXTEND_THREADS=6 \
FASIM_ALIGN_PROFILE_CACHE=1 \
python3 scripts/fasim_sharded_runner.py \
  --fasim-bin ./fasim_longtarget_cuda \
  --target targets.fa \
  --rna H19.fa \
  --rule 1 \
  --work-dir .tmp/fasim_current_base_run \
  --output-mode lite \
  --gpu-ids 0,1 \
  --workers 4 \
  --auto-cpu-core-ranges \
  --cpu-pool 0-19 \
  --cpu-cores-per-worker 3 \
  --manifest run_manifest.json
```

Use `--workers 6` only when the workload has enough shards and host CPU headroom.
`FASIM_ALIGN_PROFILE_CACHE_VALIDATE=1` remains a correctness audit mode, not a
performance mode.
