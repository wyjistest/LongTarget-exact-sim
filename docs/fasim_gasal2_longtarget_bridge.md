# Fasim GASAL2 LongTarget Bridge

This is a checkpoint for the default-off LongTarget-specific GASAL2 bridge.

## Scope

The bridge is a score-only acceleration path for the LongTarget streaming runner:

- query-resident GASAL2 score batches
- target window descriptors instead of duplicated target strings
- CPU `preAlign` remains the source of `scoreInfo`
- GASAL2 scores select candidate attempts
- CPU `aligner.Align()` remains traceback/CIGAR/output authority
- final TFO output and digest are produced by the existing Fasim CPU path

It does not make GASAL2 traceback, CIGAR, endpoint, or final output authoritative.

## Build

```bash
make build-fasim-gasal2 \
  CUDA_HOME=/usr/local/cuda-12.5 \
  CUDA_ARCH=89 \
  FASIM_GASAL2_TARGET=.tmp/fasim_longtarget_gasal2_bridge
```

The supported local GASAL2 build uses these defaults:

```text
GASAL2_GPU_SM_ARCH=sm_89
GASAL2_MAX_QUERY_LEN=2812
GASAL2_N_CODE=0x4E
```

`GASAL2_N_CODE=0x4E` is required for the current H19/LongTarget bridge. A build
with `N_CODE=4` changes GASAL2 padding behavior and can produce false
score/prepass differences. The Makefile records these values in a GASAL2 build
stamp so changing them forces a rebuild before linking `build-fasim-gasal2`.

Digest gate:

```bash
make check-fasim-gasal2-longtarget-bridge-digest \
  CUDA_HOME=/usr/local/cuda-12.5 \
  CUDA_ARCH=89
```

The gate runs CPU authority and the supported LongTarget GASAL2 bridge,
compares the `*-TFOsorted.lite` output byte-for-byte, and checks that the
bridge stays score-only (`traceback_requests=0`, `traceback_batches=0`) while
using target views and CPU traceback replay.

For a larger bounded chr22 slice:

```bash
WORK=.tmp/check_fasim_gasal2_longtarget_bridge_chr22_2mb \
DNA=.tmp/fasim_gasal2_chr22_slice_10m_12m.fa \
RULE=0 \
BIN=.tmp/fasim_longtarget_gasal2_bridge \
bash ./scripts/check_fasim_gasal2_longtarget_bridge_digest.sh
```

## Runtime

Recommended diagnostic/equivalence mode:

```bash
FASIM_ALIGN_GASAL2=1
FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1
FASIM_ALIGN_GASAL2_CPU_TRACEBACK=1
FASIM_ALIGN_GASAL2_BATCH=5000
FASIM_ALIGN_GASAL2_TASK_BATCH=4096
```

Diagnostic-only pruning probes:

```bash
FASIM_ALIGN_GASAL2_CPU_TRACEBACK_STRICT=1
FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST=1
FASIM_ALIGN_GASAL2_CPU_TRACEBACK_THRESHOLD_LAST=1
```

These pruning probes are not recommended runtime modes. They have known digest failures on current fixtures/slices.

## Equivalence Evidence

All rows below used lite TFO output and compared CPU baseline against the GASAL2 bridge.

| Workload | Digest | Lines | Missing | Extra |
| --- | --- | ---: | ---: | ---: |
| `testDNA.fa` / `H19.fa` | `ed351b98877c7c3c5f9bfeb05c0d23c36b61c20f30c6ee22f584bd18183a77c4` | 146 | 0 | 0 |
| chr22 10m-12m, 2MB | `5e20817da4bce3bfe5c20eeb250307fe1324d907320faf9002df9c343df5b886` | 2,571 | 0 | 0 |
| chr22 10m-20m, 10MB | `815dd602d7d0de55c72e1ae053dc922ee55258df0be2831ee4f18fd16fedfe2e` | 24,981 | 0 | 0 |
| chr22 20m-30m, 10MB | `019643005aa54340eeb3aed46bdbb7ad580466abb0e7e54314355f7c1a2b974a` | 47,388 | 0 | 0 |
| chr22 10m-30m, 20MB single record | `f0c69b9870ae4d3ce64df37af330548aa0b814147c68ba783f49fb46eefa8a6b` | 72,343 | 0 | 0 |
| hg38 chr22 full contig shard | `6dba31b764a48aaa9e455b2a486a9109404024f41bbf8601e48f846ee40fc59f` | 5,472 | 0 | 0 |
| hg38 chr21+chr22 combined target | `a7dc5100daf40a375c90346002c90b46628acaf423f6853c12177e5e238bbf78` | 8,489 | 0 | 0 |

## Performance Evidence

| Workload | CPU seconds | Bridge seconds | GASAL2 score seconds | Score requests | Score batches |
| --- | ---: | ---: | ---: | ---: | ---: |
| chr22 10m-12m, 2MB | 45.09 | 40.67-41.53 | 0.95-0.97 | 411,888 | 84 |
| chr22 10m-20m, 10MB | 340.78 | 333.98 | 5.06 | 2,715,316 | 554 |
| chr22 20m-30m, 10MB | 463.48 | 437.59 | 8.91 | 4,923,144 | 998 |
| chr22 10m-30m, 20MB single record | 805.80 | 775.29 | 13.80 | 7,641,760 | 1,553 |

The bridge produces modest end-to-end wins on these slices because CPU authority work remains dominant.
GASAL2 score-only time is small after LongTarget descriptor batching.

## Time Breakdown

Latest telemetry smoke after adding LongTarget bridge timing fields:

```text
workload:
  chr22 10m-12m, 2MB
  rule = 0
  output = lite

digest:
  CPU    = 5e20817da4bce3bfe5c20eeb250307fe1324d907320faf9002df9c343df5b886
  bridge = 5e20817da4bce3bfe5c20eeb250307fe1324d907320faf9002df9c343df5b886
  lines  = 2,571

wall:
  CPU    = 44.19s
  bridge = 40.57s

bridge score/replay:
  score requests                  = 411,888
  score batches                   = 84
  selected replay attempts        = 274,806
  CPU Align replay calls          = 152,404
  skipped after emit              = 122,402
  query reuse saved bytes         = 1,157,992,848

timing:
  GASAL2 score/select             = 1.009s
  GASAL2 score wait               = 0.700s
  CPU traceback replay            = 7.789s
  CPU traceback Align             = 7.742s
  CPU traceback substr            = 0.011s
  CPU traceback convert           = 0.105s
```

This breakdown is the reason the bridge is not dramatically faster end to end.
The GASAL2 score-only path is small after query reuse, but this bridge still
keeps CPU `preAlign`, conservative replay, `aligner.Align()` traceback/CIGAR,
triplex conversion, and final TFO output as authority. The remaining wall time
is therefore mostly Fasim CPU authority work, not GASAL2 kernel time.

The same workload now also passes the scripted digest gate:

```text
digest = 5e20817da4bce3bfe5c20eeb250307fe1324d907320faf9002df9c343df5b886
lines = 2,571
score requests = 411,888
CPU Align replay calls = 152,404
query reuse saved bytes = 1,157,992,848
traceback requests = 0
```

The current code also passes the scripted gate on the 20MB chr22 single-record
slice:

```text
workload:
  chr22 10m-30m, 20MB
  rule = 0
  output = lite

digest = f0c69b9870ae4d3ce64df37af330548aa0b814147c68ba783f49fb46eefa8a6b
lines = 72,343

wall:
  CPU    = 787s
  bridge = 757s

bridge:
  score requests                  = 7,641,760
  score batches                   = 1,553
  selected replay attempts        = 5,154,869
  CPU Align replay calls          = 2,830,756
  skipped after emit              = 2,324,113
  query reuse saved bytes         = 21,484,262,084
  traceback requests              = 0

timing:
  GASAL2 score/select             = 13.869s
  CPU traceback replay            = 147.999s
  CPU traceback Align             = 147.101s
  CPU traceback convert           = 2.058s
```

This confirms the intended current shape at a larger bounded scale: GASAL2 is
score-only and query-resident, target windows are descriptors/views, CPU
traceback remains authoritative, and the final TFO lite output is byte-identical
to CPU.

The current code also passes the scripted gate on the full hg38 chr22 shard used
by the sharded real-workload matrix:

```text
workload:
  hg38 chr22 full contig shard
  target length = 50,818,468
  rule = 1
  output = lite

digest = 6dba31b764a48aaa9e455b2a486a9109404024f41bbf8601e48f846ee40fc59f
lines = 5,472

wall:
  CPU    = 118s
  bridge = 125s

bridge:
  score requests                  = 1,579,552
  score batches                   = 319
  selected replay attempts        = 1,287,855
  CPU Align replay calls          = 434,665
  skipped after emit              = 853,190
  query reuse saved bytes         = 4,440,803,196
  traceback requests              = 0

timing:
  GASAL2 score/select             = 2.307s
  CPU traceback replay            = 18.555s
  CPU traceback Align             = 18.404s
  CPU traceback convert           = 0.300s
```

This is the current full-contig proof for the supported bridge shape. It is an
equivalence proof, not a performance claim: on this chr22 shard, the bridge is
slower than CPU because the score-only GPU work is too small relative to the
remaining CPU authority path.

The current code also passes the scripted gate on the combined hg38 chr21+chr22
target:

```text
workload:
  hg38 chr21+chr22 combined target
  rule = 1
  output = lite

digest = a7dc5100daf40a375c90346002c90b46628acaf423f6853c12177e5e238bbf78
lines = 8,489

wall:
  CPU    = 238s
  bridge = 251s

bridge:
  score requests                  = 3,248,344
  score batches                   = 657
  selected replay attempts        = 2,661,862
  CPU Align replay calls          = 889,284
  skipped after emit              = 1,772,578
  query reuse saved bytes         = 9,132,495,844
  traceback requests              = 0

timing:
  GASAL2 score/select             = 4.415s
  CPU traceback replay            = 37.961s
  CPU traceback Align             = 37.623s
  CPU traceback convert           = 0.615s
```

This is the current multi-contig proof for the supported bridge shape. It
preserves final TFO lite output byte-for-byte while keeping GASAL2 traceback,
endpoint, CIGAR, and output out of authority.

## Replay Shape

For chr22 10m-30m, 20MB single record:

```text
scoreInfo groups        = 1,910,440
candidate attempts      = 5,154,869
actual CPU Align calls  = 2,830,756
skipped after emit      = 2,324,113

emits:
  threshold             = 948,881
  best fallback         = 552,179
  last fallback         = 409,380

rank:
  rank1                 = 1,415,200
  rank2                 = 206,534
  rank3                 = 152,336
  rank4plus             = 136,370
```

This supports the current conservative replay policy. Fixed top-N traceback pruning is not safe with current evidence.

## Negative Pruning Results

Simple replay pruning does not preserve digest:

```text
FASIM_ALIGN_GASAL2_CPU_TRACEBACK_STRICT=1:
  fixture: clean
  chr22 10m-12m: missing=1 extra=3

FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST=1:
  fixture: missing=1

FASIM_ALIGN_GASAL2_CPU_TRACEBACK_THRESHOLD_LAST=1:
  fixture: missing=18 extra=7
```

These results show that fallback/last replay candidates are correctness-relevant, not just overhead.

## Current Conclusion

The supported bridge shape is:

```text
CPU preAlign authority
GASAL2 score-only descriptor batch
query reuse
CPU conservative traceback/replay
CPU final TFO output/digest
```

The unsupported bridge shapes are:

```text
GASAL2 traceback/CIGAR authority
GASAL2 endpoint/output authority
historical GASAL2 all-traceback runs as evidence for this bridge
fixed top-N CPU traceback pruning
using diagnostic pruning probes as real runtime modes
```

The remaining broad proof item is broader workload characterization beyond the
current hg38 chr21+chr22 gate.

## Direct GASAL2 Traceback Replacement Probe

There is now a separate diagnostic path for replacing the extension-stage CPU
`aligner.Align()` calls with GASAL2 traceback:

```bash
FASIM_ALIGN_GASAL2=1
FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1
FASIM_ALIGN_GASAL2_ALL_TRACEBACK=1
FASIM_ALIGN_GASAL2_BATCH=5000
FASIM_ALIGN_GASAL2_TASK_BATCH=4096
```

This path keeps CPU/Fasim `preAlign` as the `scoreInfo` source, but uses GASAL2
traceback for the candidate windows that would otherwise be extended by
`aligner.Align()`. It is intentionally separate from the supported
CPU-traceback bridge above.

Recent local tests used:

```bash
make build-fasim-gasal2 \
  CUDA_HOME=/usr/local/cuda-12.5 \
  CUDA_ARCH=89 \
  FASIM_GASAL2_TARGET=.tmp/fasim_longtarget_gasal2_direct
```

Fixture (`testDNA.fa` / `H19.fa`, rule 0, lite output):

```text
CPU:
  wall = 0.282s
  lines = 146
  digest = ed351b98877c7c3c5f9bfeb05c0d23c36b61c20f30c6ee22f584bd18183a77c4

GASAL2 direct traceback:
  wall = 0.558s
  lines = 145
  digest = 22291c8bf0d93fa876a2a524066414985ed626e8108803772e2227e1731b95c3
  traceback requests = 3,660
  traceback batches = 1
  CPU Align calls = 0
  missing = 2
  extra = 1
```

chr22 10m-12m, 2MB, rule 0, lite output:

```text
CPU:
  wall = 44.497s
  lines = 2,571
  digest = 5e20817da4bce3bfe5c20eeb250307fe1324d907320faf9002df9c343df5b886

GASAL2 direct traceback:
  wall = 34.569s
  lines = 2,571
  digest = 2759b63aab12b78b51bb9614856d7b2790365811a63eae579304e2b7286f367b
  traceback requests = 411,888
  traceback batches = 84
  CPU Align calls = 0
  missing = 36
  extra = 36
  top5 strength exact_equal = true
```

chr22 10m-30m, 20MB, rule 0, lite output:

```text
CPU:
  wall = 796.207s
  lines = 72,343
  digest = f0c69b9870ae4d3ce64df37af330548aa0b814147c68ba783f49fb46eefa8a6b

GASAL2 direct traceback:
  wall = 633.467s
  lines = 72,392
  digest = 628aa7cb011eb0cce154f44621d1ee4435d1929b209e3f426788337f87944dde
  traceback requests = 7,641,760
  traceback batches = 1,553
  CPU Align calls = 0
  missing = 810
  extra = 858
  top5 strength exact_equal = true
```

Current interpretation:

```text
GASAL2 direct traceback:
  replaces extension-stage aligner.Align()
  gives a measurable speedup on chr22 slices
  preserves top5 strength rows in the tested chr22 slices
  does not preserve full TFO lite digest
```

This is therefore a useful top5-focused performance probe, not an exact
drop-in Fasim output replacement.

### Direct traceback query reuse

The direct traceback path can reuse the translated query inside each GASAL2
batch instead of copying the same H19 query once per candidate target. This is a
staging/API improvement, not another end-to-end 10x optimization.

chr22 full contig, rule 0, top5 GASAL2 preset:

| Mode | Wall | GASAL2 total | GASAL2 extend wall | Traceback query bytes | Traceback target bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| no traceback query reuse | 56s | 17.7619s | 24.7129s | 12,502,073,264 | 315,197,925 |
| traceback query reuse | 56s | 15.9316s | 22.9742s | 508,972 | 315,197,680 |

Query reuse saved the expected repeated-query transfer:

```text
traceback query reuse saved bytes = 12,501,564,292
```

The full lite output digest still differs between the two GASAL2-direct runs,
but the top5 gate is clean:

```text
top5_score_equal=true
top5_stability_equal=true
top5_nt_score_equal=true
baseline_rows=185458
candidate_rows=185459
missing_rows=1
extra_rows=2
```

The wall time stays at 56s because the remaining path still includes CPU/host
staging, target encode/pack, scoreInfo handling, output work, and other
non-GASAL2 phases. Query reuse removes a large unnecessary host-to-device query
copy, but it only reduces GASAL2 total time by about 1.8s on this already
optimized top5 run.

### GPU utilization

The formal utilization script is:

```bash
WORK=.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22 \
bash scripts/characterize_fasim_gasal2_gpu_scoreinfo_utilization.sh
```

Latest full chr22 run, rule 0, top5 GASAL2 preset:

```text
wall_seconds = 55.234426
lines = 185,458
scoreInfo groups = 4,445,972
score requests = 8,894,558
traceback requests = 4,445,972
traceback batches = 181
GASAL2 total = 15.8787s
GASAL2 wait = 14.0982s
GASAL2 extend wall = 22.8892s
exact-column wall = 11.7887s
exact-column kernel = 8.55015s
traceback query bytes = 508,972
traceback target bytes = 315,197,773
traceback query reuse saved bytes = 12,501,564,292
legacy-score GPU replacement fallbacks = 0
```

GPU samples:

| GPU | Samples | SM avg | SM max | Mem util avg | Mem util max | Max memory |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 56 | 47.34% | 87% | 10.91% | 37% | 19,788 MiB |
| 1 | 56 | 0.00% | 0% | 0.00% | 0% | 272 MiB |

Largest timed phases:

| Phase | Seconds | Wall fraction |
| --- | ---: | ---: |
| flush total | 45.2587 | 81.94% |
| GASAL2 extend wall | 22.8892 | 41.44% |
| exact-column wall | 11.7887 | 21.34% |
| exact-column kernel | 8.55015 | 15.48% |
| source transform | 3.75801 | 6.80% |
| transfer string | 2.98324 | 5.40% |
| encode | 1.91416 | 3.47% |
| scoreInfo build | 1.64580 | 2.98% |

Interpretation:

```text
single process:
  uses one visible GPU
  leaves GPU1 idle

GPU0 average SM:
  around 47%, with peaks to 87%

why average SM is not near 100%:
  the run alternates GPU kernels with host staging, transforms, packing,
  scoreInfo construction, output, and synchronization.
```

So the next utilization lever is workload/process shaping or reducing host
staging and phase overhead, not simply tuning one GASAL2 kernel. To use both
GPUs on this path, run multiple worker processes with one visible GPU each or
add an explicit multi-process/multi-shard driver; the current single Fasim
process does not use GPU1.

### Process-level sharded utilization

The two-GPU sharded utilization helper is:

```bash
WORK=.tmp/characterize_fasim_gasal2_sharded_gpu_utilization_chr21_chr22 \
bash scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh
```

It builds a chr21+chr22 two-record target by default, then runs two Fasim
workers with `--gpu-ids 0,1`. The sharded runner gives each worker exactly one
visible GPU:

```text
worker 0:
  shard = chr22
  CUDA_VISIBLE_DEVICES = 0
  FASIM_CUDA_DEVICE = 0

worker 1:
  shard = chr21
  CUDA_VISIBLE_DEVICES = 1
  FASIM_CUDA_DEVICE = 0
```

Initial chr21+chr22 run, rule 0, top5 GASAL2 preset:

```text
script wall = 84.739004s
workers = 2
gpu_ids = 0,1
merged records = 288,516
duplicate records removed = 1,003

chr22 Fasim shard wall = 56.491904s
chr21 Fasim shard wall = 58.044632s

worker 0 wall = 69.080232s
worker 1 wall = 69.639790s
```

GPU samples:

| GPU | Samples | SM avg | SM max | Mem util avg | Mem util max | Max memory |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 85 | 29.38% | 100% | 5.31% | 38% | 19,788 MiB |
| 1 | 85 | 32.15% | 86% | 6.58% | 36% | 20,034 MiB |

Per-shard GPU work:

| Shard | Worker | GPU | Fasim wall | Records | Traceback requests | GASAL2 total | Exact-column kernel |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| chr21 | 1 | 1 | 58.044632s | 103,685 | 4,590,010 | 16.8055s | 8.84801s |
| chr22 | 0 | 0 | 56.491904s | 184,831 | 4,445,972 | 16.2039s | 8.54977s |

This proves process-level sharding can make both GPUs active for the GASAL2/top5
path. It does not yet prove a clean end-to-end throughput win for a two-record
workload, because the sharded runner adds nontrivial overhead:

```text
script wall:
  starts after the combined chr21+chr22 input is built.
  It includes reading that input, writing worker shard FASTAs,
  running workers, canonicalizing per-shard outputs, merging,
  and manifest/report work.

runner worker wall:
  exceeds raw Fasim shard wall by about 11-13s on this run.
```

After reusing already-canonicalized shard outputs for the final merge, the same
characterization improved:

```text
script wall:
  before = 84.739004s
  after  = 77.604289s

raw Fasim shard wall:
  chr21 = 57.933186s
  chr22 = 56.319170s

runner worker wall:
  chr21 worker = 69.008038s
  chr22 worker = 68.364316s
```

The remaining gap is therefore mostly worker-side per-shard output
canonicalization and runner bookkeeping, not the final merge reread. This is
correctness-preserving but expensive for large lite outputs.

After precomputing the canonical sort context once per output header instead of
rebuilding the header index for every row, the same characterization improved
again:

```text
script wall:
  initial           = 84.739004s
  merge-reuse only  = 77.604289s
  sort-context      = 70.839447s

raw Fasim shard wall:
  chr21 = 58.007591s
  chr22 = 56.427384s

runner worker wall:
  chr21 worker = 63.640870s
  chr22 worker = 62.709265s

runner timing:
  shard canonicalize total = 11.709380s
  final merge              = 6.000039s
```

This keeps the merged digest equal to the initial run:

```text
merged_digest = 1e530c4c8ab36abb9661722292e67d05bd0820c7747698d6cfe06ec4b9f6defe
merged_records = 288,516
duplicate_records_removed = 1,003
```

The remaining runner overhead is now explicitly measured rather than inferred.

Replacing the regex integer test with an equivalent ASCII integer check keeps
the original generic canonical sort semantics and improves the same
characterization a bit further:

```text
script wall:
  safe-sort = 69.186306s

raw Fasim shard wall:
  chr21 = 58.017826s
  chr22 = 56.465886s

runner worker wall:
  chr21 worker = 62.348482s
  chr22 worker = 61.267382s

runner timing:
  shard canonicalize total = 8.903579s
  final merge              = 5.628796s

top5 gate versus sort-context run:
  top5_score_equal = true
  top5_stability_equal = true
  top5_nt_score_equal = true
```

The safe-sort path was checked against the original generic canonical ordering
on the same output file:

```text
current digest == generic digest
```

A more aggressive typed-column conversion was tested and is intentionally not
kept. It changed canonical row ordering for values such as integer-shaped
`MeanStability=2` versus float-shaped `MeanStability=1.78167`; even though the
top5 rows stayed equal, that changed full merged digest semantics.

The sharded runner now also supports a report-only top-k summary:

```bash
--topk-summary 5
```

This does not change the default merge/output behavior. It records top-k
digests for the same ranking modes used by `compare_fasim_lite_topk.py`:

```text
score
stability
nt_score
```

Latest chr21+chr22 GASAL2/top5 sharded characterization with
`--topk-summary 5`:

```text
script wall = 73.342499s
merged_records = 288,515
duplicate_records_removed = 1,003

top5_score_digest =
  5a414c21e7b999a4b6b4931cadbd81c48b0ccdc5cd27d57b72a48c4138733d28
top5_stability_digest =
  515b4afde0eb0cc2791a2d3054a93bf1991f3b846785a953f70ca102bc5be638
top5_nt_score_digest =
  f0a011ab95797e4ee686aec8b75b3eeeaa2f2b8908f30f228b6c7a9e69a349a4

runner timing:
  shard canonicalize total = 8.228709s
  final merge              = 5.576253s
```

Compared against the earlier sort-context run, the full output still shows the
expected small GASAL2-direct variation, but top5 remains equal:

```text
missing_rows = 1
extra_rows = 0
top5_score_equal = true
top5_stability_equal = true
top5_nt_score_equal = true
```

This is a useful measurement scaffold for the actual current objective: if the
workflow only needs top5/TFO decision evidence, the next runner-side step can
be a separate default-off characterization mode that skips full merged lite
materialization and emits only top-k summary artifacts. That mode should stay
separate from the exact full-output merge path.

So the next throughput target is either:

```text
1. run enough independent shards that setup/merge overhead is amortized, or
2. reduce runner/output canonicalization overhead for large lite outputs.
```

The result is still useful: it confirms the GPU-underutilization problem is not
that GASAL2 cannot run on both GPUs. The current single-process path is
single-GPU; process-level sharding activates both GPUs, but the host/runner side
must be shaped so its overhead does not erase the GPU-side overlap.

## GPU scoreInfo / preAlign Probe

The current source also has a GPU exact-column score path:

```bash
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1
FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1
FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

When combined with GASAL2 direct traceback, this path attempts to replace both:

```text
CPU preAlign scoreInfo generation
CPU aligner.Align traceback
```

The combined diagnostic runtime is:

```bash
FASIM_TOP5_GASAL2_GPU_SCOREINFO=1
```

This preset is default-off and intentionally named as a top5-focused path. It
enables the GPU exact-column scoreInfo path, LongTarget GASAL2 target-view
bridge, GASAL2 all-traceback replacement, and the legacy-score CUDA minScore
replacement. It also enables the table-driven target-rule transform used by
`transferStringTableOptIn`. It is equivalent to the older explicit diagnostic
env stack plus `FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU=1` and
`FASIM_TRANSFERSTRING_TABLE=1`:

```bash
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1
FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1
FASIM_EXACT_COLUMN_EXTEND_BATCH=1
FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU=1
FASIM_TRANSFERSTRING_TABLE=1
FASIM_ALIGN_GASAL2=1
FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1
FASIM_ALIGN_GASAL2_ALL_TRACEBACK=1
```

Set `FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU=0` only as a diagnostic escape hatch to
reproduce the older, slower preset behavior.
Set `FASIM_TRANSFERSTRING_TABLE=0` only as a diagnostic escape hatch to
reproduce the legacy target-rule transform.

### Clean case: rule 1

Fixture, rule 1:

```text
CPU:
  wall = 0.043s
  lines = 7
  digest = b56c83fe73093f816bf5120966fd49e9ce86b38bdda13b4d8c46cc16209d237c

GASAL2 direct traceback, CPU scoreInfo:
  wall = 0.418s
  lines = 7
  digest = b56c83fe73093f816bf5120966fd49e9ce86b38bdda13b4d8c46cc16209d237c
  scoreInfo groups = 78
  traceback requests = 312
  CPU Align calls = 0

GPU scoreInfo + GASAL2 direct traceback:
  wall = 0.395s
  lines = 7
  digest = b56c83fe73093f816bf5120966fd49e9ce86b38bdda13b4d8c46cc16209d237c
  scoreInfo groups = 78
  traceback requests = 312
  CPU Align calls = 0
```

chr22 10m-12m, 2MB, rule 1:

```text
CPU:
  wall = 3.166s
  lines = 50
  digest = e21b08fd25d8cb39191e7402ba52e8914d55c72fdd6524d215a2e3e705ecdcdb

GASAL2 direct traceback, CPU scoreInfo:
  wall = 3.059s
  lines = 50
  digest = 7462c9990b36cedc39b50194bc1552ea12020805e3302b466443e566f6f1d506
  scoreInfo groups = 9,289
  traceback requests = 37,156
  CPU Align calls = 0

GPU scoreInfo + GASAL2 direct traceback:
  wall = 2.264s
  lines = 50
  digest = 7462c9990b36cedc39b50194bc1552ea12020805e3302b466443e566f6f1d506
  scoreInfo groups = 9,289
  traceback requests = 37,156
  CPU Align calls = 0
  direct_vs_gpu_equal = true
  top5 strength exact_equal = true
```

Interpretation for rule 1:

```text
GPU scoreInfo can match CPU scoreInfo for tested rule-1 workloads.
Combining GPU scoreInfo + GASAL2 direct traceback improves the chr22 2MB rule-1
slice from 3.166s CPU to 2.264s.
The remaining TFO difference is from GASAL2 traceback vs CPU Align, not from
GPU scoreInfo.
```

### Previous no-go case: rule 0

Fixture, rule 0:

```text
CPU:
  wall = 0.281s
  lines = 146
  digest = ed351b98877c7c3c5f9bfeb05c0d23c36b61c20f30c6ee22f584bd18183a77c4

GASAL2 direct traceback, CPU scoreInfo:
  wall = 0.582s
  lines = 145
  digest = 22291c8bf0d93fa876a2a524066414985ed626e8108803772e2227e1731b95c3
  scoreInfo groups = 915

GPU scoreInfo + GASAL2 direct traceback:
  wall = 0.503s
  lines = 150
  digest = e4c001567a3b7184726e2ead68c1dd3b24639742a4a41e8787de047e4899c8e6
  scoreInfo groups = 962
```

chr22 10m-12m, 2MB, rule 0:

```text
GPU scoreInfo + GASAL2 direct traceback:
  wall = 24.158s
  lines = 2,587
  scoreInfo groups = 103,806
  traceback requests = 415,224

GPU scoreInfo validate:
  wall = 118.692s
  validation found many exact-column scoreInfo mismatches
  examples:
    task=139 gpu_count=5 cpu_count=3
    task=175 gpu_count=27 cpu_count=6
    task=187 gpu_count=20 cpu_count=1
    task=1231 gpu_count=4 cpu_count=0
```

Interpretation for rule 0:

```text
The original GPU exact-column scoreInfo was not equivalent to CPU preAlign for
mixed rule-0 transforms.

Column-level debug localized the first fixture mismatches to the SSW byte
overflow boundary:
  - CPU/GPU column scores matched until the score approached 255.
  - CPU `ssw_pre_align()` returned zeroes at and after the legacy byte-overflow
    break boundary.
  - GPU exact-column continued with the full int16 DP scores.

The exact-column scoreInfo path now applies a legacy `ssw_pre_align()` byte
overflow compatibility pass before constructing scoreInfo. On the rule-0
fixture:
  CPU lite digest == GPU exact-column validate lite digest
  lines = 146

chr22 10m-12m, 2MB, rule 0 after the compatibility pass:

```text
CPU:
  wall = 44s
  lines = 2,571
  digest = 5e20817da4bce3bfe5c20eeb250307fe1324d907320faf9002df9c343df5b886

GPU exact-column validate:
  wall = 48s
  lines = 2,571
  digest = 5e20817da4bce3bfe5c20eeb250307fe1324d907320faf9002df9c343df5b886
  validate_mismatch = no

GPU exact-column, no validate:
  wall = 37s
  lines = 2,571
  digest = 5e20817da4bce3bfe5c20eeb250307fe1324d907320faf9002df9c343df5b886
```

The non-validate exact-column path is now correctness-clean on this rule-0 slice
and is about 1.19x faster than CPU for this bounded run. Validation mode remains
a guard only; it reruns CPU `preAlign()` and is not a performance mode.

### Combined GPU scoreInfo + GASAL2 direct traceback

After the byte-overflow compatibility pass, GPU scoreInfo can be combined with
GASAL2 direct traceback without adding output differences beyond the known
GASAL2 traceback replacement semantics.

chr22 10m-12m, 2MB, rule 0:

```text
CPU baseline:
  wall = 44s
  lines = 2,571
  digest = 5e20817da4bce3bfe5c20eeb250307fe1324d907320faf9002df9c343df5b886

GASAL2 direct traceback, CPU scoreInfo:
  wall = 35s
  lines = 2,571
  digest = 2759b63aab12b78b51bb9614856d7b2790365811a63eae579304e2b7286f367b
  scoreInfo groups = 102,972
  traceback requests = 411,888

GASAL2 direct traceback, GPU scoreInfo:
  wall = 24s
  lines = 2,571
  digest = 2759b63aab12b78b51bb9614856d7b2790365811a63eae579304e2b7286f367b
  scoreInfo groups = 102,972
  traceback requests = 411,888

direct CPU-scoreInfo vs GPU-scoreInfo output:
  byte-for-byte equal
```

chr22 10m-30m, 20MB, rule 0:

```text
GASAL2 direct traceback, CPU scoreInfo:
  wall = 628s
  lines = 72,392
  digest = 628aa7cb011eb0cce154f44621d1ee4435d1929b209e3f426788337f87944dde
  scoreInfo groups = 1,910,440
  traceback requests = 7,641,760

GASAL2 direct traceback, GPU scoreInfo:
  wall = 440s
  lines = 72,392
  digest = 628aa7cb011eb0cce154f44621d1ee4435d1929b209e3f426788337f87944dde
  scoreInfo groups = 1,910,443
  traceback requests = 7,641,772

direct CPU-scoreInfo vs GPU-scoreInfo output:
  byte-for-byte equal
```

The 20MB run is output-equivalent, not internally identical: the GPU scoreInfo
path produced 3 additional scoreInfo groups and 12 additional traceback
requests, but the final lite TFO output was byte-for-byte equal. Treat this as
bounded output equivalence, not as a proof that every internal candidate request
is identical.

Split-slice sanity check, chr22 10m-20m and 20m-30m, rule 0:

```text
GPU scoreInfo + GASAL2 direct traceback:
  10m-20m:
    wall = 197s
    lines = 24,996
    digest = c2bf86830daa0b33e46f797018de81b5dbc1af95bd92bcb2e2f1d428957fcf74
    scoreInfo groups = 678,828
    traceback requests = 2,715,312

  20m-30m:
    wall = 241s
    lines = 47,436
    digest = 5f2ed29a29aa10ce54ca995f06679da7443e8982b50b7c79f9b1928b6b92cd7f
    scoreInfo groups = 1,230,789
    traceback requests = 4,923,156
```

The split-slice timings line up with the single-record 20MB run (`197s + 241s`
vs `440s`), but split output is not a correctness proof for the original
20MB record. The two split outputs sum to 72,432 lines, while the single
20MB record has 72,392 lines. Complete-record boundaries matter for TFO output;
do not validate a real path by splitting a target record and comparing only
aggregate speed.

Full chr22 record, rule 0:

```text
Current-build CPU baseline:
  wall = 1,732s
  lines = 185,331
  digest = eac9fd72f3a0ee005a632310eafa6bcefcdba8538c37509359df12c7d0e159d3

GPU scoreInfo + GASAL2 direct traceback:
  wall = 941s
  lines = 185,459
  digest = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
  scoreInfo groups = 4,445,972
  traceback requests = 17,783,888
  traceback batches = 3,605
  GASAL2 total = 62.597s

full lite unique-row set difference vs the CPU baseline:
  missing = 2,039
  extra = 2,168

top5 rows:
  top5 by score: equal
  top5 by MeanStability: equal
  top5 by Nt(bp), score, MeanStability: equal
```

This full-record result is the current strongest evidence for the direct
GASAL2/GPU-scoreInfo path. It is materially faster than the current-build CPU
baseline (`941s` vs `1,732s`, about `1.84x`), and the strongest top5 rows are
unchanged under the checked orderings. It is still not an exact Fasim
replacement: the full lite output digest differs, and the GASAL2 total time is
only about 6.7% of wall time (`62.6s / 941s`). The remaining wall time is
Fasim CPU control/output work plus host-side staging around GPU bursts.

This should not be compared with the earlier MEG3 `--group-target-records`
~10x result as if they were the same optimization. The MEG3 win came from
workload shaping: grouping many tiny FASTA records removed subprocess,
scheduler, shard, and merge overhead. Full chr22 is a single large Fasim run,
so the GASAL2 path only accelerates the scoreInfo/traceback portion that it
actually replaces.

`FASIM_TOP5_GASAL2_PHASE_TIMING=1` is a default-off diagnostic switch for this
path. It prints `benchmark.fasim_top5_gasal2_phase_*` fields without changing
the preset behavior.

On the full chr22 rule-0 run, the phase-timed output was byte-identical to the
normal preset output:

```text
wall   = 945.41s
digest = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
lines  = 185,459
```

The full-chr22 phase timing explains why the speedup is limited:

```text
tasks                                = 384,816
exact-column cells                   = 1,924,080,000
scoreInfo groups                     = 4,445,972
GASAL2 traceback requests            = 17,783,888

transferStringTableOptIn             = 369.159s
exact-column scoreInfo build on CPU  = 474.645s
GASAL2 extend wall                   = 71.346s
GASAL2 total                         = 62.416s
GASAL2 wait                          = 57.183s

CUDA exact-column kernel             = 9.099s
CUDA exact-column H2D                = 0.197s
CUDA exact-column D2H                = 0.735s
CUDA topK kernel                     = 9.322s
output write                         = 0.245s
```

The GPU kernels are already small relative to the full run. The dominant costs
are CPU-side target transformation and CPU-side materialization of exact-column
scoreInfo groups from full column maxima. Therefore the next performance work,
if any, should reduce or bypass those host-side phases before spending more time
on GASAL2 kernel tuning.

Follow-up probes after this timing narrowed the bottleneck further:

```text
linear scan scoreInfo grouping:
  digest/top5 gates clean
  no material timing improvement
  reason: the measured scoreInfo build bucket is dominated by calc_score_once()

using exact-column row max as minScore source:
  top5 gate stayed clean on chr22 2MB
  rule0 digest gate failed
  not acceptable as an exact/current preset replacement

reusing precomputed source transforms per window:
  changed CPU baseline/top5 gate
  not acceptable without a deeper source/sequence convention audit
```

So the high-value remaining scoreInfo/preAlign work is not a local sort/copy
micro-optimization. It is an exact-safe replacement or cache for
`calc_score_once()` in the exact-column path, plus a safer way to avoid repeated
target-rule translation. The row-max threshold shortcut is useful as a
top5-only research signal, but it cannot be promoted without an exact-output
gate.

Regression:

```bash
make check-fasim-top5-gasal2-gpu-scoreinfo-default-off
make check-fasim-top5-gasal2-gpu-scoreinfo-env
bash scripts/check_fasim_gasal2_gpu_scoreinfo_rule0_digest.sh
make check-fasim-gasal2-gpu-scoreinfo-top5
make check-fasim-exact-column-legacy-score-gpu-replacement
```

The default-off regression verifies that the preset is not active unless
`FASIM_TOP5_GASAL2_GPU_SCOREINFO=1` is set. The env regression checks that the
binary exposes the preset and telemetry strings. The digest regression compares
direct GASAL2 traceback with CPU scoreInfo against direct GASAL2 traceback with
GPU scoreInfo on the small fixture. The top5 regression compares the top five
lite rows from CPU Fasim against GPU-scoreInfo plus GASAL2 direct traceback on
the chr22 2MB slice. The latter is intentionally not a full digest gate because
the direct GASAL2 traceback path is not exact-output equivalent.
The legacy-score replacement regression compares the current GASAL2/top5 path
against `FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU=1` on the small fixture and checks
that replacement was actually used with zero fallbacks and zero score/minScore
mismatches.

Characterization helper:

```bash
bash scripts/characterize_fasim_gasal2_gpu_scoreinfo_chr22_slices.sh
RUN_20MB=1 bash scripts/characterize_fasim_gasal2_gpu_scoreinfo_chr22_slices.sh
bash scripts/characterize_fasim_cpu_full_record.sh
```

Full-record helper:

```bash
bash scripts/characterize_fasim_gasal2_gpu_scoreinfo_full_record.sh
```

By default this runs the complete hg38 chr22 FASTA record from
`.tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/chromosomes/chr22.fa.gz`.
Use it as a long-running characterization gate, not as a quick check.

Top-k comparison helper:

```bash
python3 scripts/compare_fasim_lite_topk.py \
  --baseline .tmp/fasim_rule0_chr22_full_cpu_current/out/chr22-H19-chr22-TFOsorted.lite \
  --candidate .tmp/fasim_rule0_chr22_full_gasal2_gpu_score/out/chr22-H19-chr22-TFOsorted.lite \
  --k 5
```
```

Current scoreInfo conclusion:

```text
rule 1:
  GPU scoreInfo + GASAL2 direct traceback is a working diagnostic path.

rule 0:
  The SSW byte-overflow mismatch is fixed for the fixture and chr22 2MB slice.
  GPU scoreInfo + GASAL2 direct traceback is output-equivalent to CPU-scoreInfo
  GASAL2 direct traceback on chr22 2MB and 20MB bounded runs.
  Full chr22 rule-0 characterization shows about 1.84x wall-time speedup vs
  the current-build CPU baseline and preserves checked top5 rows, but it does
  not preserve full lite digest.

top5-focused gate:
  `make check-fasim-gasal2-gpu-scoreinfo-top5` is the quick regression for this
  non-exact path. Passing this gate does not imply full TFO equivalence.

telemetry:
  `benchmark.fasim_top5_gasal2_gpu_scoreinfo_requested=1` means the preset was
  requested. `benchmark.fasim_top5_gasal2_gpu_scoreinfo_active=1` means the
  GASAL2-enabled binary accepted the preset and the path was active.

GASAL2 native API:
  does not directly produce Fasim scoreInfo because it returns one best
  score/end per pair, not the per-target-column maxima vector required by
  Fasim preAlign.
```

### Rule-0 debug gate

The exact-column validation path now has an additional default-off column-level
diff:

```bash
FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1
FASIM_DEBUG_CUDA_PREALIGN=1
FASIM_EXACT_COLUMN_EXTEND_BATCH_DEBUG_COLUMNS=1
```

On a validation mismatch this compares the GPU exact-column vector against the
CPU `ssw_pre_align()` column vector for the same task and prints:

```text
rule / strand / Para
target length
minScore
score_mismatches
first_mismatch and first gpu/cpu scores
max_abs_diff
gpu_only_above_threshold
cpu_only_above_threshold
```

This is meant to localize the rule-0 no-go boundary. If `score_mismatches=0`
but scoreInfo differs, the problem is threshold/grouping. If column scores
differ, the CUDA DP/profile semantics are not yet equivalent to SSW
`preAlign()` for that transformed target.

Regression:

```bash
bash scripts/check_fasim_exact_column_rule0_overflow_digest.sh
```

### Exact-column minScore shadow

`FASIM_EXACT_COLUMN_MIN_SCORE_SHADOW=1` is a default-off diagnostic for the
remaining exact-column scoreInfo bottleneck. It keeps CPU `calc_score_once()` as
the minScore authority, then compares that full score against:

```text
raw GPU exact-column row max
legacy-byte-overflow row max
CUDA topK max
```

It does not change output. On the chr22 2MB slice with
`FASIM_TOP5_GASAL2_GPU_SCOREINFO=1` and phase timing enabled:

```text
digest = 2759b63aab12b78b51bb9614856d7b2790365811a63eae579304e2b7286f367b
records = 2571
tasks = 10,368

transferStringTableOptIn = 8.58s
exact-column kernel      = 0.24s
calc_score_once minScore = 12.55s
scoreInfo row build      = 0.054s
GASAL2 extend wall       = 1.71s

raw GPU row max mismatches     = 27 / 10,368
raw GPU row minScore mismatches = 27 / 10,368
topK max mismatches            = 27 / 10,368
legacy row max mismatches      = 172 / 10,368
```

The first raw mismatch is:

```text
task = 176
rule = 10
strand = 0
Para = -1
target_len = 5000
non-ACGT target symbols = 525
CPU calc_score_once = 272
GPU row max         = 269
CPU minScore        = 217
GPU minScore        = 215
```

So the big scoreInfo CPU bucket is not the row grouping logic anymore. It is
`calc_score_once()`. The raw GPU row max/topK max is close but not exact-clean,
and the legacy byte-overflow approximation is worse for threshold authority.
Therefore direct row-max threshold replacement remains exact-output no-go.

Detailed debug with `FASIM_EXACT_COLUMN_MIN_SCORE_SHADOW_DEBUG=1` shows the
reason is mostly not a CUDA exact-column DP bug. For four of the first five raw
mismatches, CPU `preAlignColumnScores()`, CPU `Align()`, and GPU row max agree,
while `calc_score_once()` is higher:

```text
task 704:
  non-ACGT target symbols = 1789
  calc_score_once = 197
  CPU Align / CPU column / GPU row = 167

task 716:
  non-ACGT target symbols = 1789
  calc_score_once = 214
  CPU Align / CPU column / GPU row = 188

task 1381:
  non-ACGT target symbols = 1618
  calc_score_once = 136
  CPU Align / CPU column / GPU row = 126
```

`calc_score_once()` uses the legacy `stats.h` 17-symbol IUPAC `npam` scoring
matrix through `cg_str()` / `init_pam2()`. The current SSW aligner, GASAL2 path,
and CUDA exact-column path use the simpler A/C/G/T/N match/mismatch scoring
model. That explains why SSW/GASAL2 row max can be top5-close while still being
wrong as the full-output minScore authority for ambiguity-heavy transformed
targets.

The next useful scoreInfo/preAlign step is an exact-safe CUDA or cached
replacement for `calc_score_once()` itself. A GPU replacement must implement
the legacy IUPAC score matrix, not the current 5-symbol SSW/GASAL2 scoring
model. It should remain shadow-only until:

```text
gpu_legacy_calc_score_mismatches = 0
gpu_legacy_minScore_mismatches = 0
full digest unchanged
```

### Legacy calc_score GPU shadow

`FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU_SHADOW=1` adds a default-off score-only
CUDA shadow for `calc_score_once()`. It builds a separate legacy query profile
and encodes target bases with the effective `cg_str()` mapping used by
`stats.h`:

```text
A/a -> 1
C/c -> 2
G/g -> 3
T/t -> 4
U/u -> 5
everything else -> 16
```

The shadow returns one max score per task. It does not replace the CPU minScore
authority yet.

chr22 2MB slice result:

```text
digest = 2759b63aab12b78b51bb9614856d7b2790365811a63eae579304e2b7286f367b
records = 2571
requests = 10,368
cells = 51,840,000

CPU calc_score_once minScore = 12.33s
GPU legacy score shadow wall = 0.227s
GPU legacy score kernel      = 0.221s
GPU legacy score H2D         = 0.0056s
GPU legacy score D2H         = 0.00005s

score mismatches    = 0
minScore mismatches = 0
```

This was the first exact-clean signal for replacing the remaining scoreInfo
minScore CPU bottleneck. It has now been promoted into the top5 GASAL2 preset,
still guarded by digest/top5 validation and CPU fallback:

```text
FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU=1

Use GPU legacy scores for minScore only when:
  legacy_score_gpu_shadow_mismatches = 0 on the validation workload
  full digest remains unchanged
  CPU calc_score_once fallback remains available
```

### Legacy calc_score GPU replacement

`FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU=1` is the default-off replacement switch.
It is also enabled by default inside `FASIM_TOP5_GASAL2_GPU_SCOREINFO=1` unless
the user explicitly sets `FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU=0`. It uses the
same legacy-score CUDA batch result as the shadow, but only for minScore. CPU
`calc_score_once()` remains the fallback when a GPU batch is not available. It
does not change scoreInfo grouping, GASAL2 traceback, CIGAR, or output
formatting.

chr22 2MB slice:

```text
digest unchanged = 2759b63aab12b78b51bb9614856d7b2790365811a63eae579304e2b7286f367b
records = 2571
requests = 10,368
replacement_used = 10,368
replacement_fallbacks = 0
CPU exact_min_score_seconds baseline = 12.33s
replacement exact_min_score_seconds  = 0
GPU legacy score wall                = 0.226s
```

chr22 10m-20m slice:

```text
digest unchanged = c2bf86830daa0b33e46f797018de81b5dbc1af95bd92bcb2e2f1d428957fcf74
records = 24,996
requests = 82,992
replacement_used = 82,992
replacement_fallbacks = 0
CPU exact_min_score_seconds baseline = 99.09s
replacement exact_min_score_seconds  = 0
GPU legacy score wall                = 1.76s
```

chr22 10m-30m slice, compared against the current GASAL2/top5 scoreInfo path:

```text
digest = 628aa7cb011eb0cce154f44621d1ee4435d1929b209e3f426788337f87944dde
records = 72,392
requests = 180,960
replacement_used = 180,960
replacement_fallbacks = 0
replacement exact_min_score_seconds = 0
GPU legacy score wall = 3.94s
GPU legacy score kernel = 3.84s
```

Full chr22 record, compared across the current optimization checkpoints:

```text
CPU full-output baseline:
  wall = 1,732s
  lines = 185,331
  digest = eac9fd72f3a0ee005a632310eafa6bcefcdba8538c37509359df12c7d0e159d3

old GASAL2/top5 preset:
  wall = 941s
  lines = 185,459
  digest = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
  tasks = 384,816
  transferStringTableOptIn = 369.159s
  exact-column scoreInfo build on CPU = 474.645s
  GASAL2 extend wall = 71.346s

legacy GPU score replacement only:
  wall = 429s
  lines = 185,459
  digest = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
  requests = 384,816
  replacement_used = 384,816
  replacement_fallbacks = 0
  score mismatches = 0
  minScore mismatches = 0
  exact_min_score_seconds = 0
  exact_scoreinfo_build_seconds = 2.108s
  GPU legacy score wall = 8.389s
  GPU legacy score kernel = 8.175s
  transferStringTableOptIn = 316.061s
  GASAL2 extend wall = 70.369s

current top5 preset with staged score-prepass:
  wall = 70s
  lines = 185,459
  digest = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
  scoreInfo groups = 4,445,972
  score requests = 11,087,681
  traceback requests = 4,445,972
  GASAL2 effective batch size = 30,000
  GASAL2 traceback batches = 181
  GASAL2 score-prepass enabled = 1
  GASAL2 staged score-prepass enabled = 1
  transferString table enabled = 1
  transferStringTableOptIn = 2.712s
  exact_min_score_seconds = 0
  exact_scoreinfo_build_seconds = 2.098s
  GPU legacy score wall = 8.357s
  replacement_used = 384,816
  replacement_fallbacks = 0
  GASAL2 extend wall = 26.431s
  GASAL2 total = 19.149s

current top5 preset with deferred topK fallback, table encoding, and parallel convert:
  wall = 58s
  lines = 185,459
  digest = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
  scoreInfo groups = 4,445,972
  score requests = 11,087,681
  traceback requests = 4,445,972
  deferred topK batches = 94
  deferred topK tasks = 384,816
  CUDA topK kernel = 0s
  target encode seconds = 1.914s
  exact-column kernel = 8.547s
  GPU legacy score kernel = 8.129s
  CPU traceback convert = 4.903s
  replacement_used = 384,816
  replacement_fallbacks = 0
  GASAL2 extend wall = 26.355s
  GASAL2 total = 19.116s

current top5 preset with staged-first fallback pruning:
  wall = 57s
  lines = 185,459
  digest = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
  scoreInfo groups = 4,445,972
  score requests = 8,894,567
  traceback requests = 4,445,972
  first-attempt threshold hits = 2,232,069
  pruned best-fallback groups = 731,038
  pruned remaining score requests = 2,193,114
  GASAL2 extend wall = 24.804s
  GASAL2 total = 17.830s

current top5 preset with traceback byte telemetry:
  wall = 56s
  lines = 185,459
  digest = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
  score requests = 8,894,567
  traceback requests = 4,445,972
  GASAL2 extend wall = 24.713s
  GASAL2 total = 17.762s
  score query bytes = 1,023,568
  score target bytes = 612,845,477
  traceback query/CIGAR bytes = 12,502,073,264
  traceback target bytes = 315,197,925
  traceback query-reuse potential saved bytes = 12,501,564,292
```

This makes the current `FASIM_TOP5_GASAL2_GPU_SCOREINFO=1` preset an
exact-clean scoreInfo/preAlign speedup candidate relative to the older
GASAL2/top5 path. It removes the legacy `calc_score_once()` minScore CPU
bottleneck and the legacy `transferString()` target-rule transform bottleneck
for the full chr22 run, with no digest change relative to that path. It also
defaults to a staged GASAL2 score-prepass so first-attempt threshold hits avoid
the remaining score-only attempts. The full chr22 wall time drops from `941s`
to `58s` (`16.2x`) relative to the old GASAL2/top5 preset and from `1,732s` to
`58s` (`29.9x`) relative to the
current-build CPU full-output baseline.

The result should still not be read as a full Fasim replacement. The current
preset is top5-focused and preserves the checked top5 rows, but its full lite
digest remains different from CPU full-output authority. The new remaining
full-chr22 bottleneck is GASAL2 extension/output, with `GASAL2 extend wall`
around `26.4s`; the old host-side scoreInfo/preAlign bottlenecks and the
redundant topK preAlign kernel are no longer dominant.

`FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1` is enabled by default inside the
top5 preset unless explicitly disabled. It is a score-prepass request reduction,
not a traceback reduction. For each scoreInfo group, the first attempt is the
longest target window ending at the scoreInfo column. If that first attempt
does not reach threshold but already has a non-zero score ending at the full
window endpoint, the staged prepass can select it as the same best-fallback
candidate without scoring the shorter suffix attempts. On full chr22 this
prunes about 2.19M second-stage score-only requests, but traceback requests
remain 4.45M, so the end-to-end gain is small (`58s` to `57s`). This is why the
remaining speedups are no longer MEG3-style 10x wins: the biggest host-side
scoreInfo/preAlign costs have already been removed, and the unchanged GASAL2
traceback plus exact-column/legacy-score kernels now dominate the residual
runtime.

The traceback byte telemetry identifies the next real GASAL2-side bottleneck.
Score-only batches are already query-resident: full chr22 fills only about 1 MB
of query sequence for score prepass. Traceback batches still copy the H19 query
once per selected alignment, about 12.5 GB on full chr22. GASAL2 also copies the
same `unpacked_query_batch` region back to host as CIGAR output, because its
current traceback API uses `query_batch_offsets` both as the query input offset
and the CIGAR output offset. Therefore a simple runner-layer query-reuse change
is unsafe: setting every traceback request to query offset zero would make the
traceback kernel write multiple CIGARs into the same output region.

The next meaningful GASAL2 design, if pursued, is a query-resident traceback API
with separate offsets:

```text
alignment input:
  query_batch_offsets
  target_batch_offsets

traceback output:
  cigar_offsets
  cigar_buffer_bytes
```

That would allow one query copy per traceback batch while preserving a distinct
CIGAR output slice per alignment. It must be validated with the existing top5
gate first, then full chr22 characterization. Until that API split exists,
GASAL2 traceback query reuse is a no-go despite the large theoretical byte
savings.

### GASAL2 traceback batch-size probe

`FASIM_ALIGN_GASAL2_BATCH` controls the GASAL2 batch size. The top5 preset uses
`30000` by default after the full-chr22 score-prepass gate below. Other GASAL2
paths keep the older `5000` default. Larger batches reduce GASAL2 wait overhead,
but overly large batches are not safe.

chr22 2MB slice:

```text
batch | wall | digest clean | gasal2_batches | gasal2_wait | gasal2_total
1000  | 6s   | yes          | 413            | 3.630s      | 3.750s
2500  | 3s   | yes          | 166            | 1.970s      | 2.092s
5000  | 3s   | yes          | 84             | 1.327s      | 1.471s
10000 | 3s   | yes          | 43             | 1.019s      | 1.180s
20000 | 2s   | yes          | 22             | 0.878s      | 1.067s
```

chr22 20MB slice:

```text
batch | wall | digest clean | lines  | gasal2_batches | gasal2_wait | gasal2_total
5000  | 51s  | yes          | 72,392 | 1,554          | 24.243s     | 26.320s
20000 | 43s  | yes          | 72,392 | 408            | 16.161s     | 18.374s
40000 | 1s   | no           | 1      | n/a            | n/a         | n/a
```

The full-chr22 all-traceback preset gate was digest/line clean and reduced wall
time from `114s` to `95s`. That historical all-traceback boundary supported
`20000`, but it is not the current formal preset default. After score-prepass
became the top5 default, the safe batch boundary was rechecked below and the
current formal preset uses `30000`. The `40000` failure shows this knob still
has a resource/correctness boundary, so larger values should remain explicit
characterization only.

After score-prepass became the top5 default, the safe batch boundary was
rechecked:

chr22 2MB score-prepass path:

```text
batch | wall | digest clean | score_batches | traceback_batches | gasal2_total
10000 | 3s   | yes          | 43            | 12                | 0.844s
20000 | 2s   | yes          | 22            | 7                 | 0.695s
30000 | 2s   | yes          | 15            | 4                 | 0.673s
40000 | fail | no           | n/a           | n/a               | OOM
```

chr22 20MB score-prepass path:

```text
batch | wall | digest clean | lines  | score_batches | traceback_batches | gasal2_total
20000 | 35s  | yes          | 72,392 | 408           | 119               | 11.277s
30000 | 34s  | yes          | 72,392 | 278           | 82                | 10.100s
```

Full chr22 score-prepass path:

```text
batch | wall | digest clean | lines   | traceback_batches | gasal2_total
20000 | 77s  | yes          | 185,459 | 267               | 25.756s
30000 | 75s  | yes          | 185,459 | 181               | 23.086s
```

The top5 preset therefore uses `30000` as its default GASAL2 batch size. This is
a small end-to-end gain, not another 10x step. `40000` remains outside the safe
resource boundary and should not be used as a default.

Characterization helper:

```bash
bash scripts/characterize_fasim_gasal2_batch_size.sh
BATCH_SIZES="5000 20000 40000" \
DNA=.tmp/fasim_gasal2_chr22_slice_10m_30m.fa \
bash scripts/characterize_fasim_gasal2_batch_size.sh
```

### GASAL2 score-prepass probe

`FASIM_ALIGN_GASAL2_SCORE_PREPASS=1` runs a GASAL2 score-only pass first, then
tracebacks only the selected attempts. It is now the default inside
`FASIM_TOP5_GASAL2_GPU_SCOREINFO=1` after the full-chr22 gate below. Set
`FASIM_ALIGN_GASAL2_SCORE_PREPASS=0` to force the previous all-traceback top5
behavior, or `FASIM_ALIGN_GASAL2_ALL_TRACEBACK=1` for an explicit all-traceback
diagnostic run.

chr22 2MB slice:

```text
mode    | wall | digest clean | traceback_requests | gasal2_wait | gasal2_total
base    | 3s   | yes          | 411,888            | 0.885s      | 1.072s
prepass | 2s   | yes          | 102,972            | 0.544s      | 0.692s
```

chr22 20MB slice:

```text
mode    | wall | digest clean | lines  | traceback_requests | gasal2_wait | gasal2_total
base    | 43s  | yes          | 72,392 | 7,641,772          | 16.212s     | 18.368s
prepass | 35s  | yes          | 72,392 | 1,910,443          | 10.122s     | 11.207s
```

Both probes are byte-identical against the previous all-traceback top5 preset
and keep the checked top5 rows equal. Full chr22 with:

```bash
FASIM_ALIGN_GASAL2_SCORE_PREPASS=1
```

also remained digest/line clean against the previous all-traceback top5 preset:

```text
previous top5 preset, all traceback:
  wall = 95s
  digest = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
  lines = 185,459
  traceback_requests = 17,783,888
  traceback_batches = 938
  GASAL2 extend wall = 51.298s
  GASAL2 total = 42.629s

score-prepass top5 preset, batch 20000:
  wall = 77s
  digest = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
  lines = 185,459
  score_requests = 4,445,972
  traceback_requests = 4,445,972
  traceback_batches = 267
  GASAL2 extend wall = 33.034s
  GASAL2 total = 25.756s

score-prepass top5 preset, batch 30000:
  wall = 75s
  digest = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
  lines = 185,459
  score_requests = 4,445,972
  traceback_requests = 4,445,972
  traceback_batches = 181
  GASAL2 extend wall = 30.384s
  GASAL2 total = 23.086s
```

Score-prepass plus the safer larger batch reduced the current top5 preset from
`95s` to `75s` (`1.27x`). The staged score-prepass below reduces it further to
`71s`. The larger `13.3x` headline remains the full change
from the old `941s`
GASAL2/top5 path to the current scoreInfo/preAlign GPU + GASAL2 preset.

### GASAL2 staged score-prepass probe

`FASIM_ALIGN_GASAL2_STAGED_SCORE_PREPASS=1` first
scores only the first attempt for each scoreInfo group. Groups that pass the
threshold skip the remaining attempts; unresolved groups score the remaining
attempts and then use the same selection logic as the default score-prepass.
It is enabled by default inside `FASIM_TOP5_GASAL2_GPU_SCOREINFO=1` after the
ordered full-chr22 gate below. Set `FASIM_ALIGN_GASAL2_STAGED_SCORE_PREPASS=0`
to force the non-staged score-prepass.

The motivation is clear from full chr22 default telemetry:

```text
scoreInfo groups = 4,445,972
score requests = 17,783,888
score requests per group = 4.0

threshold selected = 2,232,069 (50.20%)
best fallback      = 1,287,885 (28.97%)
last fallback      =   926,018 (20.83%)
none               =         0

threshold rank1 = 2,232,069
threshold rank2/rank3/rank4+ = 0
```

So about half of the groups are decided by the first attempt, and the remaining
score requests are partly avoidable.

The first implementation changed full-lite output because it returned all
first-attempt threshold groups before fallback groups. The promoted
implementation preserves the original scoreInfo group order before replay.

Bounded characterization after preserving group order:

```text
chr22 2MB:
  default digest = 2759b63aab12b78b51bb9614856d7b2790365811a63eae579304e2b7286f367b
  staged digest  = 2759b63aab12b78b51bb9614856d7b2790365811a63eae579304e2b7286f367b
  score requests = 411,888 -> 261,087
  GASAL2 total   = 0.676s -> 0.595s
  digest/top5 clean

chr22 20MB:
  default digest = 628aa7cb011eb0cce154f44621d1ee4435d1929b209e3f426788337f87944dde
  staged digest  = 628aa7cb011eb0cce154f44621d1ee4435d1929b209e3f426788337f87944dde
  lines          = 72,392 -> 72,392
  score requests = 7,641,772 -> 4,795,114
  GASAL2 total   = 10.109s -> 8.450s
  digest/top5 clean

full chr22:
  default digest = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
  staged digest  = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
  lines          = 185,459 -> 185,459
  score requests = 17,783,888 -> 11,087,681
  GASAL2 total   = 23.086s -> 19.149s
  wall           = 75s -> 70s
```

Decision: promote ordered staged score-prepass into the top5 preset. It keeps
bounded and full-chr22 digest/line gates clean while reducing score-only GASAL2
work. The switch remains explicit so `FASIM_ALIGN_GASAL2_STAGED_SCORE_PREPASS=0`
can disable it for A/B characterization.

### Deferred topK fallback and remaining GPU DP boundary

The staged preset originally launched three preAlign-related CUDA DP families
over the same task/cell shape:

```text
tasks = 384,816
cells = 1,924,080,000

CUDA topK kernel:
  kernel = 8.492s

exact-column kernel:
  kernel = 8.545s
  H2D = 0.208s
  D2H = 0.736s

legacy-score GPU replacement:
  kernel = 8.144s
  H2D = 0.208s
  D2H = 0.001s
```

The exact-column batch already constructs the scoreInfo groups used by the
top5/GASAL2 path. Therefore the CUDA topK kernel is now deferred on the
exact-column/GASAL2 success path and only runs as a fallback if exact-column or
GASAL2 replay cannot handle the batch. Full chr22 after this change:

```text
wall = 58s
digest = 162b1c3c1b17dbe561e03246e1f57760963b595aa34bf1f5fc00d517f33fa7ff
lines = 185,459
cuda_topk_deferred_batches = 94
cuda_topk_deferred_tasks = 384,816
cuda_topk_kernel_seconds = 0
target_encode_seconds = 1.914s
exact_column_kernel_seconds = 8.547s
legacy_score_gpu_kernel_seconds = 8.129s
cpu_traceback_convert_seconds = 4.903s
```

This keeps the previous top5/GASAL2 digest and line count while removing the
old topK kernel from the normal success path. The target staging loop also uses
table-driven preAlign and legacy-score encoders now, so the full-chr22 target
encode phase drops from `5.050s` to `1.914s` without changing output.
The selected-alignment convert stage is also parallelized per task while the
final write remains ordered by task; this keeps the digest stable and moves the
full-chr22 wall from `59s` to `58s`.

One tempting staging optimization is intentionally not retained: caching the
four source transforms per target window changed the checked top5 output
(`top5_score_equal=false`, `top5_nt_score_equal=false` on the 2MB gate). Source
transform reuse must therefore remain a separate correctness-first design, not
a simple safe cache.

The remaining exact-column and legacy-score outputs still are not
interchangeable:

```text
exact-column:
  returns every column max for exact scoreInfo group construction

legacy-score GPU replacement:
  uses the legacy calc_score_once scoring/profile convention for minScore
```

The legacy-score path cannot safely reuse the current exact-column result
because it uses a different scoring alphabet/profile convention and a different
target encoding. The exact-column/preAlign path encodes `A/C/G/T/other` as
`0/1/2/3/4` and builds a 5-symbol profile. The legacy `calc_score_once()`
replacement encodes `A/C/G/T/U/other` as `1/2/3/4/5/16`, uses a 17-symbol
profile, and treats A/U as a match. Earlier row-max/topK threshold shortcuts
were top5-close but not full-output exact. Therefore the next optimization is
not another simple "drop one kernel" step unless a fused kernel computes both
5-symbol exact-column outputs and 17-symbol legacy-score minScore under their
separate scoring conventions and passes digest gates.

Characterization helper:

```bash
bash scripts/characterize_fasim_gasal2_score_prepass.sh
DNA=.tmp/fasim_gasal2_chr22_slice_10m_30m.fa \
bash scripts/characterize_fasim_gasal2_score_prepass.sh
```

After promoting the table-driven target-rule transform into the same preset, a
chr22 2MB A/B with phase timing showed byte-identical output and:

```text
FASIM_TRANSFERSTRING_TABLE=0:
  transferStringTableOptIn = 8.307s

FASIM_TRANSFERSTRING_TABLE=1:
  transferStringTableOptIn = 0.077s

legacy-score GPU replacement:
  replacement_used = 10,368
  replacement_fallbacks = 0
```

This removes another CPU-side bottleneck from the top5 preset. The full-chr22
score-prepass gate above is the measured end-to-end result after this
promotion.

This still does not make the whole GASAL2 direct traceback path a full CPU-output
replacement. It removes the legacy `calc_score_once()` minScore CPU bottleneck
and the legacy target-rule transform bottleneck inside the current top5/GASAL2
scoreInfo path.

### Long-query GASAL2 boundary

The supported local GASAL2 build is intentionally kept at:

```text
GASAL2_MAX_QUERY_LEN=2812
```

This covers the current H19 query and MEG3 query shapes that have clean top5
signals. The Fasim GASAL2 bridge now has a default length guard:

```text
FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812
FASIM_ALIGN_GASAL2_MAX_TARGET_LEN=0
```

The target-length guard is disabled by default. The query-length guard is a
fail-closed boundary: over-limit query shapes return to the CPU path before
GASAL2 allocation or launch. The guard is applied both in the LongTarget batch
bridge and in the `fastSIM_extend_from_scoreinfo()` direct GASAL2 path. This
avoids both the partial-output failure observed when MALAT1 was allowed into a
GASAL2 build that did not fit its query shape and the repeated bridge
length-guard fallback overhead on long-query CPU fallback runs.

MALAT1 first8 with the default `MAX_QUERY_LEN=2812` query preflight:

```text
query_len = 8708
query_preflight_supported = 0
GASAL2 requests = 0
GASAL2 fallbacks = 0
length_guard_fallbacks = 0
rows = 799 -> 799
top5 score/stability/nt_score = clean
wall = 23.10s -> 22.06s
speedup = 1.05x
```

This is correctness-safe CPU fallback, not a GASAL2 performance mode.

NEAT1 first64 has the same long-query boundary:

```text
query_len = 22767
query_preflight_supported = 0
GASAL2 requests = 0
GASAL2 fallbacks = 0
length_guard_fallbacks = 0
rows = 2,838 -> 2,838
top5 score/stability/nt_score = clean
wall = 86.90s -> 86.12s
speedup = 1.01x
```

The matching short-query control remains on the GASAL2 path:

```text
MEG3 full:
  query_len = 1582
  query_preflight_supported = 1
  GASAL2 requests = 762,716
  length_guard_fallbacks = 0
  top5 score/stability/nt_score = clean
  wall = 49.05s -> 12.34s
  speedup = 3.98x
```

The matrix gate also extracts deterministic top5-only lite artifacts using the
same ranking modes as the comparator (`score`, `stability`, and `nt_score`) and
compares CPU vs GASAL2 output byte-for-byte. Current artifact rows:

```text
MEG3 full:       15 rows
MALAT1 first8:   12 rows
NEAT1 first64:   15 rows
top5_artifact_equal = true for all three
```

The same top5-only artifact gate also passes on the bounded H19/chr22 slice:

```text
MATRIX_PRESET=chr22_2mb

chr22 10m-12m:
  query_len = 2812
  query_preflight_supported = 1
  full lite rows = 2570 -> 2081
  missing_rows = 519
  extra_rows = 33
  top5 score/stability/nt_score = clean
  top5_artifact_equal = true
  top5_artifact_rows = 15
  scoreInfo groups = 102,972
  scoreInfo kept after prune = 85,202
  scoreInfo pruned = 17,770
  traceback requests = 85,202
  GASAL2 total = 0.424s
  wall = 44.31s -> 1.85s
  speedup = 23.95x
```

This is a top5-only result. It is not a full-output equivalence claim.
It is also different from the output-only topK-lite mode below: this gate
removes scoreInfo groups before GASAL2 traceback, so it avoids real compute.
`FASIM_OUTPUT_TOPK_LITE` only trims the emitted `.lite` artifact after the same
pipeline has already run.

The quick regression for the bounded H19/chr22 scoreInfo-prune gate is:

```bash
make check-fasim-gasal2-scoreinfo-prune-top5-chr22-2mb
```

## TopK Lite Wrapper

For consumers that explicitly want only the deterministic topK lite artifact,
the repository provides a wrapper around the default-off GASAL2/top5 path:

```bash
DNA=.tmp/fasim_gasal2_chr22_slice_10m_12m.fa \
RNA=H19.fa \
RULE=0 \
K=5 \
OUT=.tmp/fasim_gasal2_chr22_2mb_topk \
bash scripts/run_fasim_gasal2_topk_lite.sh
```

The wrapper:

```text
1. calls scripts/fasim_sharded_runner.py
2. uses --gasal2-top5-column-pruned-scoreinfo
3. writes the formal topK artifacts under $OUT
4. copies $OUT/topk-TFOsorted.lite to $OUT/top${K}.lite
5. writes $OUT/summary.tsv
```

`run_fasim_gasal2_topk_lite.sh` defaults to the formal
`--gasal2-top5-column-pruned-scoreinfo` runner preset. It is therefore the
short wrapper for the current reviewed top5 artifact surface, not the old
direct-env path. `LEGACY_DIRECT=1` keeps the older direct-env wrapper path
available for investigation only. The wrapper contract is checked by
`check-fasim-gasal2-topk-lite-wrapper-contract`.

For MEG3-like tiny-region inputs, the wrapper can use the same complete-record
grouping as the runner:

```bash
GROUP_TARGET_RECORDS=32 \
DNA=.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743-DNAseq.fa \
RNA=.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743.fa \
RULE=0 \
K=5 \
OUT=.tmp/fasim_gasal2_meg3_group32_topk \
bash scripts/run_fasim_gasal2_topk_lite.sh
```

This still uses the formal top5-only artifact contract. It is complete-record
grouping, not chunking or overlap.

The legacy direct-env mode is still available when explicitly requested:

```bash
LEGACY_DIRECT=1 \
DNA=.tmp/fasim_gasal2_chr22_slice_10m_12m.fa \
RNA=H19.fa \
RULE=0 \
K=5 \
OUT=.tmp/fasim_gasal2_chr22_2mb_topk_legacy \
bash scripts/run_fasim_gasal2_topk_lite.sh
```

That path keeps the older direct Fasim invocation and low-level env controls
such as `PRUNE_MAX_PER_TASK`, `GASAL2_BATCH`, and `IN_PROCESS_TOPK`. It remains
legacy diagnostic coverage, not the current recommended gate for the
GASAL2/top5 path.

It does not change Fasim defaults or claim full-output equivalence. This is a
topK artifact path for consumers that explicitly only need the strongest rows.

The current regression gate for the formal sharded GASAL2/top5 preset is:

```bash
make check-fasim-sharded-gasal2-top5-prune-runner
```

The legacy standalone wrapper is kept under an explicit investigation target
name:

```bash
make investigate-fasim-gasal2-topk-lite-runner-legacy
```

Do not use that legacy target as evidence for the formal column-pruned preset.
On the current source it is not top5-clean on the single-record chr22 10m-12m
fixture; the historical digest below is retained only as older context.

Current standalone-wrapper no-go signal on the single-record chr22 10m-12m
fixture:

```text
PRUNE_MAX_PER_TASK=16
exact scoreInfo GPU = off
GASAL2 requests = 378,708
length guard fallbacks = 0
top5 artifact = mismatch

missing CPU row:
  1599900-1599965 ParaMinus rule=2 score=99 nt=66 stability=3.2

extra GASAL2 row:
  928321-928390 ParaMinus rule=2 score=110 nt=70 stability=3.19571
```

Forcing `PRUNE_MAX_PER_TASK=32` plus exact-column column-pruned scoreInfo env on
this standalone wrapper also mismatched the CPU top5 artifact. That is why the
current path to trust is the sharded formal runner preset, not this wrapper.

Historical chr22 10m-12m standalone-wrapper result:

```text
cpu_rows = 15
gasal2_post_rows = 15
gasal2_inprocess_rows = 15
cpu_digest = gasal2_post_digest = gasal2_inprocess_digest =
  d3712ba8b0a509187dbd4c2cd846a0bb64722be80aabdfd0f3b7f2d5bd943854
```

The examples-level legacy investigation target is:

```bash
make investigate-fasim-gasal2-topk-lite-runner-examples-legacy
```

Historical examples-level standalone-wrapper result:

```text
MEG3 full:
  rows = 15
  query_preflight_supported = 1
  GASAL2 requests = 762,716
  CPU/postprocess/in-process topK digests match

MALAT1 first8:
  rows = 12
  query_preflight_supported = 0
  GASAL2 requests = 0
  CPU/postprocess/in-process topK digests match

NEAT1 first64:
  rows = 15
  query_preflight_supported = 0
  GASAL2 requests = 0
  CPU/postprocess/in-process topK digests match
```

### Sharded TopK Lite

The same default-off in-process topK mode can also be used with the sharded
runner when the caller requests `--topk-summary-only`. In that mode every shard
keeps only its local topK union, and the runner computes the global topK summary
from those much smaller shard outputs.

The runner-level option is:

```text
--shard-output-topk-lite K
```

It requires `--output-mode lite`, `--topk-summary-only`, and the same `K` as
`--topk-summary`. The option is included in the runner report and
`run_config_digest`, and the runner passes `FASIM_OUTPUT_TOPK_LITE=K` to each
Fasim worker. The characterization helper exposes this as `IN_PROCESS_TOPK=1`.

This is valid for the topK artifact because any row in the global topK for a
ranking mode must also be in the local topK for that mode in its source shard.
It is still not a full merged-output equivalence claim.

For top5 GASAL2 scoreInfo/preAlign compute-prune runs, the sharded runner also
has an explicit default-off preset:

```text
--gasal2-top5-scoreinfo-prune-max-per-task N
--exact-scoreinfo-gpu-max-per-task M
```

It sets the managed GASAL2/top5 env (`FASIM_TOP5_GASAL2_GPU_SCOREINFO=1`,
`FASIM_TOP5_GASAL2_PHASE_TIMING=1`,
`FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1`, and
`FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=N`) and requires
`--topk-summary 5 --topk-summary-only --output-mode lite`. It can be combined
with `--shard-output-topk-lite 5` so each shard both prunes compute before
traceback and writes only its local deterministic top5 union. The runner records
the preset in `run_config_digest` and rejects conflicting manual `--env`
overrides for those managed keys.

`--exact-scoreinfo-gpu-max-per-task M` is an optional extension to that preset.
It sets `FASIM_EXACT_COLUMN_SCOREINFO_GPU=1` and
`FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=M`, records the value in
`report.json`, and includes it in `run_config_digest`. It requires
`--gasal2-top5-scoreinfo-prune-max-per-task` because it is only a top5
GASAL2/scoreInfo artifact path, not a full-output mode.

The formal `--gasal2-top5-column-pruned-scoreinfo` preset additionally sets:

```text
FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1
FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=1
FASIM_OUTPUT_TOPK_LITE=5
```

Together with cap64 and exact max-per-task 512, those env values define the
current column-pruned top5 artifact contract. They are runner-managed and should
not be supplied manually through `--env` on the formal preset.
`FASIM_ALIGN_GASAL2_BATCH` remains an allowed diagnostic override, but the
formal preset rejects values above `30000`, non-integers, and non-positive
values before shard execution. `40000` is outside the checked resource boundary
and must stay a lower-level characterization setting.
`FASIM_ALIGN_GASAL2_STREAMS` remains an allowed diagnostic override, but the
formal preset rejects values above `16`, non-integers, and non-positive values
before shard execution.

Bounded chr22 2MB two-shard runner smoke:

```bash
make check-fasim-sharded-gasal2-top5-prune-runner
```

Current smoke metrics:

```text
run_status = completed
shards = 2
workers = 2
gpu_ids = 0,1
top5 score/stability/nt_score = CPU summary equal

shard 1:
  scoreInfo groups = 45,242
  scoreInfo kept after prune = 36,301
  scoreInfo pruned = 8,941
  GASAL2 requests = 111,287
  traceback requests = 36,301
  GASAL2 total = 0.258s

shard 2:
  scoreInfo groups = 57,261
  scoreInfo kept after prune = 48,393
  scoreInfo pruned = 8,868
  GASAL2 requests = 144,084
  traceback requests = 48,393
  GASAL2 total = 0.320s

GASAL2 fallback = 0
```

The regression gate for this runner path is:

```bash
make check-fasim-sharded-gasal2-top5-prune-runner
```

It compares CPU sharded top5 summary keys against the GASAL2 compute-prune
runner path, then verifies the shard stderr has GASAL2 active, scoreInfo prune
enabled, exact scoreInfo GPU active, non-zero score/traceback requests, and zero
GASAL2/exact-scoreInfo fallback. It also reruns the GASAL2 path with `--resume`
and verifies all raw topK shard outputs are reused from the manifest while
preserving the top5 summary and `run_config_digest`. A final changed-config
resume run bumps `--exact-scoreinfo-gpu-max-per-task` and verifies the
`run_config_digest` changes and shards rerun instead of reusing stale outputs.

The sharded GPU-utilization characterization helper also uses this runner
preset whenever `GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK` is set:

```bash
TOPK_SUMMARY_ONLY=1 \
IN_PROCESS_TOPK=1 \
GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=16 \
EXACT_COLUMN_SCOREINFO_GPU=1 \
EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=512 \
bash scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh
```

For the checked column-pruned one-DP preset, prefer the formal preset flag:

```bash
TOPK_SUMMARY_ONLY=1 \
IN_PROCESS_TOPK=1 \
GASAL2_TOP5_COLUMN_PRUNED_PRESET=1 \
bash scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh
```

This passes `--gasal2-top5-column-pruned-scoreinfo` through the runner instead
of reconstructing the preset from manual lower-level options. The helper rejects
mixing `GASAL2_TOP5_COLUMN_PRUNED_PRESET=1` with manual
`GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK`, `GASAL2_SINGLE_PASS_TOPN`,
`GASAL2_NT_SUM_SPAN_PRUNE`, `PREALIGN_CUDA_MAX_TASKS`, or exact-column
scoreInfo settings, so utilization reports map to the actual recommended runner
switch.

The helper records both `gasal2_scoreinfo_prune_max_per_task` and
`runner_gasal2_top5_scoreinfo_prune_max_per_task`, plus the exact scoreInfo GPU
env values and `runner_exact_scoreinfo_gpu_max_per_task`, in `summary.txt`, so
it is clear whether the formal runner preset and exact-scoreInfo compact-buffer
setting were used. When `GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK` is set, the helper
routes exact scoreInfo GPU through the runner option
`--exact-scoreinfo-gpu-max-per-task` instead of raw `--env`; non-prune diagnostic
runs keep the raw env path because the runner option is intentionally tied to the
top5 prune preset.
When `GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK` is set, the helper now fails closed
unless `TOPK=5`, `TOPK_SUMMARY_ONLY=1`, and `IN_PROCESS_TOPK=1`, matching the
runner preset boundary and the intended top5 artifact characterization mode.
The env regression for those checks is:

```bash
make check-fasim-gasal2-sharded-characterization-env
```

Formal column-pruned preset utilization, chr21+chr22, two workers/two GPUs:

```bash
WORK=.tmp/characterize_gasal2_column_pruned_preset_util_chr21_chr22 \
TOPK_SUMMARY_ONLY=1 \
IN_PROCESS_TOPK=1 \
TOPK=5 \
WORKERS=2 \
GPU_IDS=0,1 \
GASAL2_TOP5_COLUMN_PRUNED_PRESET=1 \
bash scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh
```

`PREALIGN_CUDA_MAX_TASKS` is no longer a formal-preset tuning knob. The current
helper rejects it with `GASAL2_TOP5_COLUMN_PRUNED_PRESET=1` because the runner's
formal artifact contract only allows a narrow diagnostic env allowlist. If that
flush-size question is revisited, use a lower-level characterization path and
compare top5 artifacts explicitly; do not label the result as the formal
`--gasal2-top5-column-pruned-scoreinfo` preset.

Historical cap32 result:

```text
script wall = 37.589210s
top5 score/stability/nt_score digests = CPU/full-artifact clean baseline
runner preset:
  --gasal2-top5-column-pruned-scoreinfo
  prune max_per_task = 32
  exact scoreInfo max_per_task = 512
  exact column-pruned output = active
  legacy score GPU requests = 0
  overflow/fallback batches = 0

GPU utilization:
  GPU0 avg = 47.61%, max = 93%
  GPU1 avg = 50.95%, max = 91%

chr21 shard:
  wall = 36.384372s
  traceback requests = 3,694,784
  scoreInfo groups = 3,694,784
  pruned input groups = 4,597,650
  pruned groups = 902,866
  GASAL2 total = 11.0376s
  GASAL2 wait = 9.46013s
  exact-column wall = 9.04743s
  exact-column kernel = 8.84395s
  source transform = 4.01358s
  transfer table = 3.11712s
  encode dual = 0s
  encode preAlign = 1.34691s

chr22 shard:
  wall = 35.821131s
  traceback requests = 3,562,792
  scoreInfo groups = 3,562,792
  pruned input groups = 4,453,027
  pruned groups = 890,235
  GASAL2 total = 10.7204s
  GASAL2 wait = 9.1158s
  exact-column wall = 8.74527s
  exact-column kernel = 8.53656s
  source transform = 3.8528s
  transfer table = 3.07001s
  encode dual = 0s
  encode preAlign = 1.32461s
```

This answers the current "can GASAL2 run the GPUs full enough?" question more
precisely: the formal preset uses both GPUs and reaches high instantaneous SM
peaks, but average SM remains about 40-53% because roughly half the run is
outside GPU kernels. The non-kernel half is dominated by GASAL2 wait/result
handling, target transform/transfer-table work, and encoding/staging around the
exact-column and GASAL2 kernels. The next useful optimization is therefore not
another real-path `aligner.Align()` GPU replacement attempt. It is reducing
host-side staging/transform and GASAL2 wait/copy overhead in the already-clean
top5 artifact path, while keeping the full-output and exact-scoreInfo boundary
explicit.

The current preset skips legacy-score GPU input preparation when the
column-pruned exact scoreInfo GPU path is active. This removes an otherwise
unused legacy target encoding pass: `encode_dual_seconds` drops to zero, while
`encode_prealign_seconds` records the single remaining preAlign encoding pass.
The effect is modest but real on chr21+chr22 (`38.396595s -> 37.589210s`) and
keeps the same top5 artifact digests. Explicit
`FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU=1` remains available for legacy-score GPU
diagnostics/fallback experiments.

Transform/transfer counters from the same chr21+chr22 preset run:

```text
chr21:
  transfer calls = 394,032
  transfer bytes = 1,970,160,000
  transfer reverse calls = 197,016
  src transform calls = 394,032
  src transform bytes = 1,970,160,000
  src transform orig/comp/rev/revcomp = 49,254 / 147,762 / 147,762 / 49,254

chr22:
  transfer calls = 384,816
  transfer bytes = 1,924,080,000
  transfer reverse calls = 192,408
  src transform calls = 384,816
  src transform bytes = 1,924,080,000
  src transform orig/comp/rev/revcomp = 48,102 / 144,306 / 144,306 / 48,102
```

This shows the next host-side opportunity clearly: the current task generator
repeatedly derives transformed source strings for the same target window/rule
shape. A future `srcSeq` transform cache or fused transfer/src construction
should target this path first, with top5 artifact gates unchanged. The expected
win is bounded by the current `src_transform_seconds` plus part of
`transfer_table_seconds`; it will not address GASAL2 wait or exact-column kernel
time.

Two-record chr22 10m-12m slice A/B:

```bash
WORK=.tmp/characterize_gasal2_sharded_topk_full_lite_2record \
TARGET=.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa \
TOPK_SUMMARY_ONLY=1 \
TOPK=5 \
WORKERS=2 \
GPU_IDS=0,1 \
GASAL2_STREAMS=1 \
GASAL2_BATCH=10000 \
bash scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh

WORK=.tmp/characterize_gasal2_sharded_topk_inprocess_2record \
TARGET=.tmp/fasim_gasal2_chr22_slice_10m_12m_two_records.fa \
TOPK_SUMMARY_ONLY=1 \
IN_PROCESS_TOPK=1 \
TOPK=5 \
WORKERS=2 \
GPU_IDS=0,1 \
GASAL2_STREAMS=1 \
GASAL2_BATCH=10000 \
bash scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh
```

Result:

```text
full-lite shard rows:
  991, 1543

in-process topK shard rows:
  15, 15

top5 score digest:
  86200a97bd5d8a3713ba6cdf60dd97effed15685f1d0bb648a41a764d3ace28b
  equal

top5 stability digest:
  30cbec341eb82a0a25a5b27de6192c100f406567affe712af233b5c8f1dcce17
  equal

top5 nt_score digest:
  80dc9e9c5dc892b3d5584e91546c6fce7ce655b02c30e5c775ee670063a2febd
  equal

topK summary seconds:
  full-lite   = 0.035529s
  in-process = 0.000639s
```

Current chr21+chr22 sharded result, compared against the existing
`TOPK_SUMMARY_ONLY=1` / `GASAL2_NT_SUM_SPAN_PRUNE=1` full-lite summary run:

```text
full-lite shard rows:
  chr21 = 103,676
  chr22 = 184,794

in-process topK shard rows:
  chr21 = 13
  chr22 = 15

shard output size:
  full-lite   = 23 MB
  in-process = 20 KB

top5 score digest:
  5a414c21e7b999a4b6b4931cadbd81c48b0ccdc5cd27d57b72a48c4138733d28
  equal

top5 stability digest:
  515b4afde0eb0cc2791a2d3054a93bf1991f3b846785a953f70ca102bc5be638
  equal

top5 nt_score digest:
  f0a011ab95797e4ee686aec8b75b3eeeaa2f2b8908f30f228b6c7a9e69a349a4
  equal

topK summary seconds:
  full-lite   = 1.240202s
  in-process = 0.000662s

wall seconds:
  full-lite   = 55.518908s
  in-process = 54.194307s
```

This confirms the in-process topK mode removes almost all shard-output and
topK-summary I/O for this two-contig top5 artifact workload. It does not make
the end-to-end run dramatically faster because the dominant costs remain
GASAL2 traceback, exact-column kernels, encoding, and host staging.
In other words, this is an artifact-size optimization, not a compute-prune
optimization. It explains why the chr21+chr22 sharded topK-lite A/B is only
`55.52s -> 54.19s` (`1.02x`), while the bounded chr22 scoreInfo-prune gate
above is `44.31s -> 1.85s` (`23.95x`): only the latter moves the top5 boundary
ahead of traceback work.

The formal runner scoreInfo-prune preset was also checked on the same
chr21+chr22 shape:

```bash
TOPK_SUMMARY_ONLY=1 \
IN_PROCESS_TOPK=1 \
TOPK=5 \
WORKERS=2 \
GPU_IDS=0,1 \
GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=16 \
bash scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh
```

Current result:

```text
wall seconds:
  in-process topK artifact only = 54.194307s
  scoreInfo-prune runner preset = 51.500425s

effective GASAL2 settings:
  streams = 2
  batch   = 30000

top5 digests:
  score     = 5a414c21e7b999a4b6b4931cadbd81c48b0ccdc5cd27d57b72a48c4138733d28
  stability = 515b4afde0eb0cc2791a2d3054a93bf1991f3b846785a953f70ca102bc5be638
  nt_score  = f0a011ab95797e4ee686aec8b75b3eeeaa2f2b8908f30f228b6c7a9e69a349a4
  all equal to the artifact-only top5 run

GPU utilization:
  GPU 0 avg = 47.04%, max = 88%
  GPU 1 avg = 48.40%, max = 89%

chr21 shard:
  scoreInfo groups = 4,590,010
  kept after prune = 3,690,224
  pruned groups    = 899,786
  GASAL2 total     = 11.071s
  exact-column     = 8.862s

chr22 shard:
  scoreInfo groups = 4,445,972
  kept after prune = 3,558,204
  pruned groups    = 887,768
  GASAL2 total     = 10.727s
  exact-column     = 8.537s
```

This is the right formal top5 preset shape, but it is still only a modest
end-to-end improvement for chr21+chr22 (`54.19s -> 51.50s`, about `1.05x`).
The reason is that the prune removes about 20% of the scoreInfo groups, not the
large majority of the work. The remaining runtime is still dominated by GASAL2
score/traceback wait, exact-column kernels, target transforms, and encoding.
Forcing smaller GASAL2 settings makes this worse: a diagnostic run with
`GASAL2_BATCH=10000` and `GASAL2_STREAMS=1` had the same top5 digests but
increased wall time to `63.34s`. Leave batch/stream defaults in place unless
the run is explicitly a batch-size characterization.

The `scoreInfo-prune max_per_task` boundary was then swept with the same formal
runner preset and GASAL2 defaults:

```bash
TARGET=.tmp/characterize_fasim_gasal2_sharded_gpu_utilization_chr21_chr22_prune16_runner_default_verify/inputs/chr21_chr22.fa \
PRUNE_VALUES="16 12 10 9 8" \
WORK=.tmp/characterize_fasim_gasal2_scoreinfo_prune_sweep_chr21_chr22 \
bash scripts/characterize_fasim_gasal2_scoreinfo_prune_sweep.sh
```

```text
mode          max_per_task  wall       top5 clean  traceback requests  pruned groups
artifact      n/a           54.200s    yes         9,035,982           0
prune16       16            51.313s    yes         7,248,428           1,787,554
prune12       12            49.758s    yes         6,241,246           2,794,736
prune10       10            48.744s    yes         5,566,603           3,469,379
prune9        9             47.947s    no          5,179,401           3,856,581
prune8        8             47.334s    no          4,756,974           4,279,008
```

`prune10` is the tightest current chr21+chr22 top5-clean point. `prune9` and
`prune8` keep the score and nt_score top5 digests unchanged but change the
stability top5 digest, so they are no-go for the current top5 artifact contract.
Even at `prune10`, this is only `54.20s -> 48.74s` (`1.11x`) because the
exact-column work remains about `17.4s` and the retained GASAL2 traceback set is
still large. Treat `10` as a workload-specific characterization candidate, not
as a universal default or a full-output equivalence setting.

The sweep helper decision for this run was:

```text
best_top5_clean_label=prune10
best_top5_clean_max_per_task=10
best_top5_clean_wall_seconds=48.744131
best_top5_clean_speedup_vs_baseline=1.111939
```

The sweep summary also reports exact-column `wall`, `kernel`, `H2D`, and `D2H`
seconds. That split is the next gate for this path: after `prune10`, traceback
work is reduced, but exact-column remains a large fixed cost. Future changes
should first prove whether exact-column time is kernel-bound or staging-bound
before changing the runtime path.

Existing chr21+chr22 sweep logs give this exact-column split:

```text
mode      exact wall  kernel   H2D     D2H     overhead  kernel share  GASAL2 total
artifact  23.340s     17.387s  0.403s  1.544s  4.006s    74.5%         25.106s
prune16   23.364s     17.409s  0.404s  1.551s  3.999s    74.5%         21.820s
prune12   23.422s     17.444s  0.407s  1.554s  4.018s    74.5%         20.130s
prune10   23.654s     17.460s  0.408s  1.570s  4.216s    73.8%         18.490s
prune9    23.455s     17.476s  0.407s  1.558s  4.015s    74.5%         18.034s
prune8    23.514s     17.482s  0.413s  1.591s  4.027s    74.4%         17.467s
```

The exact-column workload is unchanged across prune settings:

```text
exact-column batches = 191
exact-column tasks   = 778,848
exact-column cells   = 3,894,240,000
```

So this is not an H2D/D2H problem and not something `scoreInfo-prune` can
remove. `scoreInfo-prune` only reduces the later GASAL2 traceback set. After
`prune10`, any further end-to-end gain needs either a faster exact-column
kernel/launch shape, fewer exact-column tasks before the prune boundary, or a
different top5-preserving selection design. Continuing to tune
`max_per_task < 10` is already blocked by the stability-top5 gate.

The next combination run enabled the exact scoreInfo GPU path together with the
tightest top5-clean prune point:

```bash
WORK=.tmp/characterize_fasim_gasal2_sharded_gpu_utilization_chr21_chr22_scoreinfo_gpu_prune10_verify \
TARGET=.tmp/characterize_fasim_gasal2_sharded_gpu_utilization_chr21_chr22_prune16_runner_default_verify/inputs/chr21_chr22.fa \
TOPK_SUMMARY_ONLY=1 \
IN_PROCESS_TOPK=1 \
TOPK=5 \
WORKERS=2 \
GPU_IDS=0,1 \
EXACT_COLUMN_SCOREINFO_GPU=1 \
GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=10 \
bash scripts/characterize_fasim_gasal2_sharded_gpu_utilization.sh
```

```text
wall = 46.442s
top5 score digest     = 5a414c21e7b999a4b6b4931cadbd81c48b0ccdc5cd27d57b72a48c4138733d28
top5 stability digest = 515b4afde0eb0cc2791a2d3054a93bf1991f3b846785a953f70ca102bc5be638
top5 nt_score digest  = f0a011ab95797e4ee686aec8b75b3eeeaa2f2b8908f30f228b6c7a9e69a349a4

GPU 0 avg = 50.77%, max = 93%
GPU 1 avg = 51.43%, max = 94%

traceback requests = 5,566,603
GASAL2 total       = 18.385s

exact scoreInfo GPU:
  enabled shards   = 2
  tasks            = 778,848
  overflow batches = 0
  fallback batches = 0
  wall             = 22.575s
  kernel           = 17.525s
  H2D              = 0.415s
  D2H              = 1.328s

legacy exact-column:
  wall   = 0
  kernel = 0
```

This confirms that exact scoreInfo GPU + `prune10` is top5-clean for this
chr21+chr22 characterization and removes the legacy exact-column wall from the
normal path. The end-to-end gain is still modest:

```text
artifact baseline       54.200s
prune10 only            48.744s
exact scoreInfo+prune10 46.442s
```

So the combined residual gain is `54.20s -> 46.44s` (`1.17x`) against the
already optimized artifact baseline, and only `48.74s -> 46.44s` (`1.05x`)
after `prune10`. This is not another MEG3-style `10x` result. The large earlier
wins removed CPU scoreInfo/preAlign or tiny-shard overhead; this run is now
bounded by exact scoreInfo GPU kernel time, GASAL2 traceback, and host
staging/encoding around those GPU bursts.

The exact scoreInfo GPU compact-buffer limit is controlled by:

```text
FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK
```

The default is `2048`. This limit is not a top5 selection limit; it is the
per-task GPU output capacity for exact scoreInfo peaks. If the capacity is too
small, the batch overflows and falls back. If it is too large, D2H/output staging
is larger than needed.

The repository includes a focused characterization wrapper:

```bash
bash scripts/characterize_fasim_exact_scoreinfo_gpu_max_per_task_sweep.sh
make check-fasim-exact-scoreinfo-gpu-max-per-task-sweep
```

For chr21+chr22 with `prune10`, the sweep was:

```bash
WORK=.tmp/characterize_fasim_exact_scoreinfo_gpu_max_per_task_sweep_chr21_chr22 \
TARGET=.tmp/characterize_fasim_gasal2_sharded_gpu_utilization_chr21_chr22_prune16_runner_default_verify/inputs/chr21_chr22.fa \
MAX_PER_TASK_VALUES="512 1024 2048 4096" \
PRUNE_MAX_PER_TASK=10 \
WORKERS=2 \
GPU_IDS=0,1 \
bash scripts/characterize_fasim_exact_scoreinfo_gpu_max_per_task_sweep.sh
```

```text
mode     max_per_task  wall       top5 clean  overflow  fallback  exact scoreInfo wall  kernel    D2H
default  2048          46.612s    yes         0         0         22.634s              17.532s   1.360s
512      512           44.239s    yes         0         0         18.575s              17.571s   0.319s
1024     1024          45.270s    yes         0         0         20.421s              17.602s   0.740s
2048     2048          46.606s    yes         0         0         22.734s              17.621s   1.366s
4096     4096          49.314s    yes         0         0         27.218s              17.619s   2.516s
```

For this workload, `512` is the current best top5-clean compact-buffer point:

```text
best_top5_clean_label=max512
best_top5_clean_wall_seconds=44.238841
best_top5_clean_speedup_vs_baseline=1.053649
best_top5_clean_exact_scoreinfo_gpu_wall_seconds=18.574530
best_top5_clean_exact_scoreinfo_gpu_kernel_seconds=17.571330
```

This moves the combined chr21+chr22 path from `46.61s` to `44.24s`, and from the
artifact baseline `54.20s` to `44.24s` (`1.23x`). The gain comes from smaller
compact scoreInfo output/D2H staging, not from a faster DP kernel: kernel time is
still about `17.6s` across all capacities. Treat `512` as a chr21+chr22
characterization candidate, not a universal default, because other workloads can
have more scoreInfo peaks per task and may overflow at a smaller capacity.

The next default-off probe is:

```text
FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1
```

or through the sharded runner:

```text
--exact-scoreinfo-gpu-pruned-output
```

This does not change the scoreInfo prune rule. It moves the existing
`score desc, position asc` per-task top-N selection into the GPU exact scoreInfo
compact output and then returns the kept scoreInfo groups in original
position/order for GASAL2 replay. The old
`FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK` setting is still only compact
buffer capacity; it is not top-N semantics. The pruned-output path is useful only
if it remains top5-clean with `exact_scoreinfo_gpu_overflow_batches=0`,
`exact_scoreinfo_gpu_fallback_batches=0`, and reduces wall time beyond the
current `512` capacity point. It is still a top5 artifact path, not a full Fasim
output replacement.

Current same-binary chr21+chr22 A/B:

```text
max512 compact output:
  wall_seconds               = 44.421830
  exact scoreInfo GPU wall   = 18.541070s
  exact scoreInfo GPU kernel = 17.544820s
  exact scoreInfo GPU D2H    = 0.317725s
  GASAL2 total               = 18.481450s

pruned compact output:
  wall_seconds               = 43.746647
  legacy max-score GPU wall  = 16.965230s
  legacy max-score GPU kernel= 16.548190s
  exact scoreInfo GPU wall   = 17.412820s
  exact scoreInfo GPU kernel = 16.966780s
  exact scoreInfo GPU D2H    = 0.022755s
  GASAL2 total               = 18.478970s
  top5 digests               = same as max512
```

So GPU-pruned compact output is a small positive probe, not another 10x step. It
removes most of the remaining scoreInfo D2H/output staging for this run, but the
end-to-end gain is only `44.42s -> 43.75s` (`1.015x`) because exact scoreInfo DP
kernel time and GASAL2 score/traceback wait remain the dominant buckets.

This older exact pruned-output comparison still had a double-DP cost: it first
ran the legacy max-score GPU replacement to compute the per-task max score and
`minScore`, then ran the exact scoreInfo GPU pass to emit scoreInfo peaks. On
that chr21+chr22 pruned-output run, those two GPU DP kernels were each about
`16.5-17.0s` across the two shards before GASAL2 score/traceback work. That is
why compact-output pruning alone was not a large speedup: it reduced output
transfer/staging, not the two DP passes.

The current formal preset path is already column-pruned one-DP. It uses
`--gasal2-top5-column-pruned-scoreinfo` and requires `zero_legacy_score_runs =
1`; the separate legacy max-score GPU pass is not part of the checked formal
milestone. The remaining optimization headroom is therefore not "remove the
legacy max-score pass" for the formal preset. It is broader workload coverage,
long-query architecture, and further reduction of GASAL2/host work while keeping
the top5 artifact contract clean.

### Single-pass topN scoreInfo probe

`FASIM_TOP5_GASAL2_SINGLE_PASS_TOPN=1` is a default-off diagnostic path for the
top5 artifact. It forces the existing CUDA topK column-maxima kernel to feed
GASAL2 directly:

```text
one GPU DP pass:
  compute per-task topN column maxima
  use topN[0].score as maxScore
  minScore = 0.8 * maxScore
  keep topN peaks above minScore
  run GASAL2 on those bounded candidates
```

This is the explicit version of "get candidate scoreInfo from the first pass."
It is intentionally not an exact scoreInfo replacement: the complete legacy
scoreInfo contract includes every grouped column peak above the final
`minScore`, while the single-pass path only keeps a bounded topN candidate set.
It is therefore valid only as a top5 artifact probe and must pass top5 digest
gates before any performance interpretation.

The sharded runner option is:

```bash
--gasal2-single-pass-topn
```

It requires `--gasal2-top5-scoreinfo-prune-max-per-task N` and records
`gasal2_single_pass_topn` in the manifest/run-config digest. It does not change
default behavior, does not enable exact scoreInfo GPU, and should be compared
against the current exact pruned-output path with:

```bash
make check-fasim-gasal2-single-pass-topn
```

Decision gate:

```text
top5 digests clean
legacy_score_gpu_requests = 0
exact_scoreinfo_gpu_batches = 0
wall < current exact pruned-output path
```

If top5 differs, the bounded topN candidate set is not a safe substitute for
scoreInfo even though it avoids the second DP pass. If top5 is clean but wall is
not better, the remaining bottleneck is GASAL2/host work rather than duplicate
preAlign DP.

Small chr22 2MB-slice characterization:

```text
exact pruned-output:
  wall = 1.470008s
  legacy_score_gpu_requests = 10,368
  exact_scoreinfo_gpu_batches = 3
  scoreInfo groups = 66,466
  top5 digests = baseline

single-pass topN:
  wall = 1.336812s
  speedup = 1.10x
  legacy_score_gpu_requests = 0
  exact_scoreinfo_gpu_batches = 0
  scoreInfo groups = 72,378
  top5 score digest = clean
  top5 stability digest = clean
  top5 nt_score digest = mismatch
```

This proves the implementation can answer the architectural question: the first
pass can produce bounded candidates and eliminate the legacy max-score plus
exact scoreInfo double-pass. It also proves the current bounded topN candidate
set is not yet a safe substitute for the top5 artifact, because one checked
top5 ordering changes. The next probe, if pursued, should vary the topN capacity
and candidate grouping/tie policy under the same digest gate; do not promote
`FASIM_TOP5_GASAL2_SINGLE_PASS_TOPN=1` as a recommended runtime until all top5
digests are clean.

The topN capacity sweep is now explicit:

```bash
make check-fasim-gasal2-single-pass-topn-sweep
```

Current bounded chr22 2MB-slice result:

```text
mode                 topN  wall      speedup  score  stability  nt_score  scoreInfo groups
exact pruned-output  n/a   1.5025s   1.00x    clean  clean      clean     66,466
single-pass topN     64    1.3014s   1.15x    clean  clean      mismatch  72,378
single-pass topN     128   1.3194s   1.14x    clean  mismatch   mismatch  91,711
single-pass topN     256   1.3813s   1.09x    clean  mismatch   mismatch  101,228
```

So increasing topN does not recover top5 equivalence. It keeps the score-top5
artifact clean but admits a different candidate population for nt/stability
ranking, and the extra candidates increase GASAL2 traceback work. `topN=64`
already changes the nt-score top5: only the exact rank-3 nt-score row remains
in the same top5 set, while four exact nt-score rows are replaced by different
TFOs. `topN=128/256` also changes the stability top5 by admitting higher
stability rows not present in the exact pruned-output artifact.

This is the hard answer to "can the first DP pass directly produce scoreInfo?":

```text
It can produce bounded topN scoreInfo-like candidates.
It does not currently produce exact legacy scoreInfo.
It is not top5-safe for the current artifact contract.
```

The sweep writes `top5_diff.tsv` with concrete missing/extra top5 rows for every
no-go label. Treat that file as the review artifact when deciding whether a new
candidate grouping or replay policy actually restores top5 equivalence.

### Column-pruned one-DP scoreInfo probe

`FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=1` is a different
default-off diagnostic probe for the exact-scoreInfo/pruned-output path. Instead
of running the legacy max-score GPU pass and then a second exact scoreInfo GPU
pass, it runs one exact-column DP pass, keeps the full column maxima on device,
and launches a compact kernel that applies the same score-desc/position-asc
top-N pruning used by the GASAL2 top5 artifact path.

The sharded runner option is:

```bash
--exact-scoreinfo-gpu-column-pruned-output
```

It requires `--exact-scoreinfo-gpu-pruned-output` and records
`exact_scoreinfo_gpu_column_pruned_output` in the manifest/run-config digest.
For normal top5 artifact characterization, prefer the checked preset:

```bash
--gasal2-top5-column-pruned-scoreinfo
```

That preset expands to `--gasal2-top5-scoreinfo-prune-max-per-task 64`,
`--exact-scoreinfo-gpu-max-per-task 512`,
`--exact-scoreinfo-gpu-pruned-output`,
`--exact-scoreinfo-gpu-column-pruned-output`, and
`--shard-output-topk-lite 5`. It is still default-off and top5-only.
The focused regression is:

```bash
make characterize-fasim-exact-scoreinfo-gpu-column-pruned-output
make check-fasim-exact-scoreinfo-gpu-column-pruned-output
make characterize-fasim-exact-scoreinfo-gpu-column-pruned-output-matrix
make check-fasim-exact-scoreinfo-gpu-column-pruned-output-matrix
make characterize-fasim-gasal2-column-pruned-preset-top5-matrix
make check-fasim-gasal2-column-pruned-preset-top5-matrix
```

Small chr22 2MB/two-record probe, same binary:

```text
exact pruned-output:
  wall = 1.559828s
  legacy_score_gpu_requests = 10,368
  scoreInfo groups = 84,694
  top5 digests = clean

column-pruned one-DP:
  wall = 1.296523s
  legacy_score_gpu_requests = 0
  scoreInfo groups = 84,793
  top5 digests = clean
```

So this path answers a narrower question than single-pass topN: a one-DP
column-maxima path can feed a top5-clean artifact on the small chr22 fixture and
can eliminate the separate legacy score DP requests. It is still not exact
legacy scoreInfo or full-output equivalence, because exact-column row maxima are
already known to differ from legacy `calc_score_once()` on some ambiguity-heavy
targets and this probe changes the scoreInfo group population. The current
small-slice check is a positive top5 artifact smoke (`1.56s -> 1.30s`), but it
is not enough to promote the path. Treat it as an architecture probe only until
a larger run shows top5 clean output and lower wall time.

chr21+chr22 top5 artifact A/B, same binary:

```text
exact pruned-output:
  wall = 46.675012s
  top5 score/stability/nt_score digests = clean baseline
  legacy_score_gpu_requests = 778,848
  GASAL2 total = 21.806900s
  scoreInfo groups = 7,248,428

column-pruned one-DP:
  wall = 38.219571s
  speedup = 1.22x
  top5 score/stability/nt_score digests = clean vs baseline
  legacy_score_gpu_requests = 0
  GASAL2 total = 21.764000s
  scoreInfo groups = 7,257,576
```

This is the current strongest positive signal for the GASAL2/top5 path: the
column-pruned one-DP probe removes the separate legacy score GPU pass and gives
a real wall-time reduction on chr21+chr22 while preserving the checked top5
artifact. The boundary is still hard: the scoreInfo group population changes,
so this is not legacy scoreInfo equivalence, not full merged-output equivalence,
and not a direct `aligner.Align()` replacement. The next gate, if this path is
continued, is repeated larger-workload top5 characterization and then an
explicit decision about whether top5-only output change is acceptable for the
TFO use case.

The checked preset now uses `scoreInfo-prune max_per_task=64`. After lowercase
FASTA bases are normalized to uppercase and source-transform staging is reused,
current-bin chr21+chr22 cap sweeps showed that smaller caps can reduce traceback
requests, but the stricter split chr22 runner fixture rejected cap `16`: one
top5 score candidate was pruned out and replaced by a lower-score row. Cap `10`
and `12` also change the top5 stability artifact. A later MEG3 first32 formal
runner preset gate also rejected cap `32` on the nt-score rank-5 artifact while
cap `64` remained clean. That is why
`--gasal2-top5-column-pruned-scoreinfo` still expands to
`--gasal2-top5-scoreinfo-prune-max-per-task 64`, not `10`, `12`, `16`, or `32`.

The repeat/matrix wrapper records that gate explicitly:

```bash
TARGET_PRESETS="small chr21_chr22" REPEATS=1 \
make characterize-fasim-exact-scoreinfo-gpu-column-pruned-output-matrix
```

There is a stricter wrapper for the checked preset:

```bash
make characterize-fasim-gasal2-column-pruned-preset-top5-matrix
make check-fasim-gasal2-column-pruned-preset-top5-matrix
```

The formal top5 artifact gate is:

```bash
make check-fasim-gasal2-top5-formal-gate
```

The recorded chr21+chr22 milestone result artifact is verified separately with:

```bash
make check-fasim-gasal2-top5-scoreinfo-milestone-result
```

This result gate requires the saved local characterization artifact and is
therefore not a dependency of the formal gate.

The composed current-state milestone gate is:

```bash
make check-fasim-gasal2-scoreinfo-current-state
```

It ties together the recorded chr21+chr22 result, MEG3 grouped result, wrapper
result, top5 output contract, long-query boundary, and long-query no-last
scaling artifact. Its conclusion is intentionally scoped:

```text
short-query/H19 top5 scoreInfo/preAlign: milestone go
MEG3 grouped top5 wrapper: milestone go
long-query current best is marginal
long-query MALAT1/NEAT1: no real path
full replacement goal remains open
```

It starts with `check-fasim-gasal2-formal-makefile-gate`, which checks the
formal-gate dependency list, `.PHONY` coverage, and the ignored root
`fasim_longtarget_gasal2` build artifact. It then runs the milestone doc gate,
`check-fasim-gasal2-top5-output-contract` gate, the
`check-fasim-gasal2-long-query-boundary` gate, the GASAL2-enabled binary guard,
the default-off guard, the binary env/telemetry-key guard, the sharded preset
runner check, the bounded preset-vs-CPU/full top5 matrix check, the lowercase
FASTA input normalization gate, and the MEG3/MALAT1/NEAT1 examples boundary
gate. The standalone `topk_lite_runner` wrapper remains legacy diagnostic
coverage only when `LEGACY_DIRECT=1` is set and is intentionally exposed only
through `investigate-*` Makefile targets. The default wrapper path is checked by
`check-fasim-gasal2-topk-lite-wrapper-contract`. The output contract is documented in
`docs/fasim_gasal2_top5_output_contract.md`; the long-query no-go boundary is
documented in `docs/fasim_gasal2_long_query_boundary.md`.
Focused long-query segmented no-go gates are
`check-fasim-gasal2-long-query-segmented-pruned-traceback-shadow` and
`check-fasim-gasal2-long-query-segmented-replay-no-last`.
The formal preset rejects long-query segmented diagnostic env keys such as
`FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW`, so those probes cannot be
silently mixed into the formal top5 artifact contract.
Formal artifact integrity checks reject the same segmented diagnostic env keys
if they appear in `report.json` or `run_manifest.json`. They also reject
unsupported formal env extras such as `FASIM_ALIGN_GASAL2_CPU_TRACEBACK_NO_LAST`;
only the managed preset env and checked diagnostic overrides are accepted.
If `FASIM_ALIGN_GASAL2_MAX_QUERY_LEN` is present, it must match the recorded
`gasal2_top5_query_preflight_max_query_len`.

This compares the preset directly against a CPU/full top5 summary artifact, not
against the easier exact-pruned-output baseline. It reports both the sum of
per-worker shard wall seconds and the max-worker wall seconds, so the speedup is
not confused with full-output merge timing. It also fail-closes if the preset
does not expand to cap64 plus exact-column pruned scoreInfo, raw topK shard
output, `legacy_score_gpu_requests=0`, and zero exact-scoreInfo GPU
overflow/fallback batches.

Current matrix signals:

```text
small repeat=2:
  top5 clean runs = 2/2
  zero legacy-score runs = 2/2
  zero overflow/fallback runs = 2/2
  speedup_min = 1.077342x
  speedup_median = 1.120318x
  scoreInfo group delta = +99
  decision = top5_artifact_go

chr21+chr22 repeat=1:
  top5 clean runs = 1/1
  zero legacy-score runs = 1/1
  zero overflow/fallback runs = 1/1
  speedup = 1.221233x
  scoreInfo group delta = +9,148
  decision = top5_artifact_go
```

Current preset-vs-CPU/full top5 artifact signals:

```text
small chr22 2MB/two-record repeat=1:
  top5 score/stability/nt_score equal = true
  legacy_score_gpu_requests = 0
  overflow/fallback batches = 0
  CPU/full worker-wall sum = 44.907707s
  preset worker-wall sum = 2.315699s
  worker-wall-sum speedup = 19.392718x
  max-worker-wall speedup = 21.831227x

chr21+chr22 repeat=1:
  top5 score/stability/nt_score equal = true
  legacy_score_gpu_requests = 0
  overflow/fallback batches = 0
  CPU/full worker-wall sum = 3612.949899s
  preset worker-wall sum = 74.152217s
  worker-wall-sum speedup = 48.723424x
  max-worker-wall speedup = 48.993246x
  preset exact-column wall = 17.782430s
  preset exact-scoreInfo GPU wall = 0.222617s
  preset GASAL2 total = 21.924900s
  preset traceback requests = 7,257,576
```

Fresh formal Makefile gate result:

```text
make check-fasim-gasal2-top5-formal-gate

binary guard:
  non-GASAL2 fasim_longtarget_cuda rejects
  --gasal2-top5-column-pruned-scoreinfo
  GASAL2-enabled binary accepts the self-contained preset and emits
  topk_summary.tsv

default-off guard:
  ok

env/telemetry-key guard:
  ok

sharded preset/resume guard:
  topk_summary_match = true
  preset_topk_summary_match = true
  resume_topk_summary_match = true
  score_digest = 4c44c23e5fbca989d56280e2e92a7ceac4ef1387567b6d8f9ec5a48dd6985fa7
  stability_digest = 0c481927dbeffc13eb5d1bd9d14cd2e6ef07701ff4ecde7828ceb30d97c9d1d8
  nt_score_digest = aefc3b6a52861d3e88be8640d5e146dece55d7c5d67696ab71beb7128da2e2ef

bounded preset-vs-CPU/full top5 matrix:
  target_preset = small
  runs = 1
  top5_clean_runs = 1
  active_path_runs = 1
  speedup_vs_cpu_worker_wall_sum_min = 23.864777x
  speedup_vs_cpu_max_worker_wall_median = 27.165867x
  decision = top5_artifact_go

lowercase input normalization:
  lowercase_topk_summary_match = true
  score_digest = 12e568b60371b52c11a6debdcc80c4946c0242f05b494de0a20825c766f28e72
  stability_digest = 125ccdb89397ab3af9b5657b8b27d75e71225c515ed943c670083af598fb58db
  nt_score_digest = 8c794a439762ed18b4633eb16820cd28164b8ff4875da571feddc5e754d9fce3
```

Focused bounded matrix gate result from the same formal run:

```text
make check-fasim-gasal2-column-pruned-preset-top5-matrix

target_preset = small
runs = 1
top5_clean_runs = 1
active_path_runs = 1
zero_legacy_score_runs = 1
zero_overflow_runs = 1
zero_fallback_runs = 1
zero_gasal2_fallback_runs = 1
zero_length_guard_fallback_runs = 1
speedup_vs_cpu_worker_wall_sum = 23.864777x
speedup_vs_cpu_max_worker_wall = 27.165867x
decision = top5_artifact_go
```

The bounded matrix aggregate reports `active_path_runs` so top5-clean rows must
also prove active GASAL2/exact-scoreInfo coverage.

Fresh chr21+chr22 active-path characterization with the same formal preset:

```bash
TARGET_PRESETS=chr21_chr22 \
REPEATS=1 \
BUILD_BIN=0 \
WORK=.tmp/characterize_fasim_gasal2_column_pruned_preset_top5_matrix_chr21_chr22_active \
BIN=.tmp/fasim_longtarget_gasal2_direct \
bash scripts/characterize_fasim_gasal2_column_pruned_preset_top5_matrix.sh
```

Current result:

```text
target_preset = chr21_chr22
runs = 1
artifact_checked_runs = 1
top5_clean_runs = 1
active_path_runs = 1
zero_legacy_score_runs = 1
zero_overflow_runs = 1
zero_fallback_runs = 1
zero_gasal2_fallback_runs = 1
zero_length_guard_fallback_runs = 1
positive_gasal2_request_runs = 1
positive_exact_scoreinfo_task_runs = 1
decision = top5_artifact_go

CPU worker wall sum = 4565.987188s
formal preset worker wall sum = 113.810705s
speedup vs CPU worker wall sum = 40.119136x
speedup vs CPU max worker wall = 40.443813x

GASAL2 requests = 43,637,966
GASAL2 traceback requests = 13,701,121
exact scoreInfo GPU tasks = 778,848
GASAL2 fallbacks = 0
length guard fallbacks = 0
exact scoreInfo overflow/fallback batches = 0 / 0
exact scoreInfo GPU batches = 49
legacy score GPU requests = 0
```

This is the strongest current result for the short-query H19/chr21+chr22 shape:
the formal preset is not merely top5-clean; it is top5-clean with active
GASAL2/exact-scoreInfo coverage and no fallback/overflow. It remains a top5
artifact result, not full lite-output equivalence.

The concise milestone record is `docs/fasim_gasal2_top5_scoreinfo_milestone.md`.

Together with the bounded small-fixture gate, this means the default-off
`--gasal2-top5-column-pruned-scoreinfo` preset is top5-artifact clean against
the CPU/full artifact on the small split fixture and chr21+chr22, and it removes
the separate legacy score GPU pass. The boundary remains unchanged. This is not
full lite output equivalence, not exact legacy scoreInfo, and not a direct
`aligner.Align()` replacement. It is a top5-summary-only artifact candidate.
The runner writes deterministic top5 artifacts to `topk_summary.tsv`,
`topk_rows.tsv`, and `topk-TFOsorted.lite`; the TSV artifacts start with
`# result_contract=<contract>`.
`topk_summary.tsv` contains the checked score, stability, and nt-score top5 row
keys, while `topk_rows.tsv` contains the same mode/rank ordering with full
lite-output rows. `topk-TFOsorted.lite` is a deduplicated normal lite-output
file for the selected top rows. `report.json` records output paths plus full and
payload digests for the TSV artifacts, and records the direct topK lite output,
digest, and record count. Full digests cover the contract metadata where
present; payload digests are the comparable values for CPU/GASAL2 top5
equivalence checks. artifact integrity checks require the `topk_summary` report
object to match the topK summary and rows artifacts.
The same report and manifest record
`result_contract=gasal2_top5_column_pruned_scoreinfo_artifact_v1` for the
formal preset, which separates it from lower-level GASAL2 diagnostics and from
ordinary merged-output runs.
The formal `--gasal2-top5-column-pruned-scoreinfo` preset additionally sets
`FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE=1`, so every formal run
records the final topK-lite rows' scoreInfo-rank distribution for future
pruning decisions without changing pruning, output, or digest.

This moves the path from a single hand-run signal to a repeatable top5-only
candidate gate. It still does not establish full-output equivalence. A real
opt-in would need an explicit top5-only contract, because the scoreInfo group
drift means the full lite row population is not being preserved.

The examples gate checks that boundary on the existing MEG3/MALAT1/NEAT1
fixtures:

```bash
make check-fasim-exact-scoreinfo-gpu-examples-gate
```

It is included in `make check-fasim-gasal2-top5-formal-gate` so the formal
gate covers both the clean short-query MEG3 path and the expected long-query
MALAT1/NEAT1 guard path. The examples gate reports
`scoreinfo_gasal2_active` so guarded long-query CPU fallback rows cannot be
mistaken for active GASAL2/exact-scoreInfo shards.

Current examples-gate result from the formal gate:

```text
label           top5 clean  query preflight  active  GASAL2 requests  exact tasks  overflow  fallback  wall
MEG3 full       yes         supported        1       762,716          25,536       0         0         48.78s -> 12.14s
MALAT1 first8   yes         blocked          0       0                0            0         0         23.03s -> 21.92s
NEAT1 first64   yes         blocked          0       0                0            0         0         86.67s -> 85.88s
```

This gives a narrower but stronger recommendation:

```text
short-query GASAL2/top5 path:
  --gasal2-top5-scoreinfo-prune-max-per-task N
  --exact-scoreinfo-gpu-max-per-task 512
  valid characterization candidate if overflow/fallback stay 0

long-query MALAT1/NEAT1 path:
  current GASAL2 build query guard blocks the path
  exact scoreInfo GPU compact capacity is not exercised
  no GPU-fast-path claim
```

For the formal preset, `FASIM_ALIGN_GASAL2_MAX_QUERY_LEN` must stay within the
checked short-query boundary. `FASIM_ALIGN_GASAL2_MAX_QUERY_LEN` remains an
allowed diagnostic override, but the formal preset rejects values above `2812`,
non-integers, and non-positive values before shard execution. `0` or larger
query guards remain lower-level diagnostic overrides only and are rejected by
`--gasal2-top5-column-pruned-scoreinfo`.
For auditability, the formal preset records
`gasal2_top5_query_preflight_supported`,
`gasal2_top5_query_preflight_query_len`, and
`gasal2_top5_query_preflight_max_query_len` in `report.json` and
`run_manifest.json`, along with the preflight error field. Formal resume also
requires verified query preflight and reruns instead of reusing older manifests
that do not carry it. Formal resume requires the same verified query-preflight
length bounds before reusing shards. The formal artifact integrity checks
require manifest query-preflight fields to match the report. The formal artifact
integrity checks also require query length to be within the recorded max query
length. The formal artifact integrity checks require managed preset
`env_overrides`, including `FASIM_PREALIGN_CUDA_MAX_TASKS=16384`, to match the
formal preset. The formal artifact integrity checks also require manifest
`env_snapshot` to carry the same managed preset values. The formal artifact
integrity checks recompute the active-path requirement from
`fasim_benchmark_sums`: active per-shard GASAL2/exact-scoreInfo flags, positive
GASAL2 request and exact-scoreInfo task counts, and zero fallback/overflow.
The formal artifact integrity checks also require topK-lite scoreInfo-rank
observe telemetry to be enabled, non-empty, and free of unknown rows.
The formal GASAL2 top5 artifact path is not full lite-output equivalence and is
not an `aligner.Align()` replacement.

So `512` is now clean on chr21+chr22 and MEG3-like short-query workloads, but it
is still not a universal default. Any new workload should keep the gate hard:
top5 clean, `exact_scoreinfo_gpu_overflow_batches=0`, and
`exact_scoreinfo_gpu_fallback_batches=0`.

The quick regression for the sweep wrapper is:

```bash
make check-fasim-gasal2-scoreinfo-prune-sweep
```

The sweep wrapper also writes `top5_diff.tsv` for no-go prune settings. The
chr21+chr22 `prune9`/`prune8` failure is a concrete stability-top5 replacement:

```text
missing from stability top5:
  genome=27298771-27298835
  rule=2
  query=2384-2449
  score=120
  nt=66
  stability=3.23939

extra in stability top5:
  genome=17524190-17524243
  rule=5
  query=2383-2437
  score=100
  nt=56
  stability=3.15893
```

This is why `prune9`/`prune8` stay no-go even though score and nt_score digests
remain clean. It also explains why a simple "multi-mode scoreInfo prune" is not
available at this stage: `scoreInfo` only contains `(score, position)`, while
the top5 artifact modes rank final lite rows by score, stability, and nt after
GASAL2 traceback/ConvertAlignment. Stability and nt are not known before
traceback, so the current scoreInfo-stage prune can only be characterized
empirically. More aggressive pruning would need a new predictor or a later-stage
top5-preserving selection design, not just a different sort key over scoreInfo.

A separate characterization build tried to make GASAL2 fit MALAT1 by rebuilding
the static library with:

```text
GASAL2_MAX_QUERY_LEN=8708
```

The result is not a viable runtime path:

```text
batch=20000, streams=3:
  fails in GASAL2 allocation with CUDA out-of-memory

batch=128, streams=1:
  runs without length fallback
  rows = 799 -> 570
  top5_score_equal = true
  top5_stability_equal = false
  top5_nt_score_equal = true
  wall = 23.11s -> 95.31s
  GASAL2 total = 83.43s
```

Therefore long-query workloads such as MALAT1/NEAT1 should remain on the CPU
fallback path unless a different GASAL2/GPU execution design is introduced.
Increasing `GASAL2_MAX_QUERY_LEN` is not enough: it either exceeds the current
storage budget or runs much slower and breaks the top5 stability gate.

## Shared Source-Transform Reuse Checkpoint

The chr21+chr22 top5-column-pruned preset was rerun after normalizing lowercase
FASTA input to uppercase and after changing the GASAL2/top5 task payload to
reuse one transformed source sequence per target window/transform type. The
checked preset remains:

```text
--gasal2-top5-column-pruned-scoreinfo
--topk-summary-only
--shard-output-topk-lite 5
```

Comparable baseline before source-transform reuse:

```text
wall_seconds = 53.261985
top5 score digest     = 402342fbf4659a331c13b8a5d31f803b967fcfe9c1fef1b6f3498e5284bdf944
top5 stability digest = bcd4ef7804df20d9a10038df701b70f36d1b8eabbc27301f610aff551bb03d22
top5 nt_score digest  = e45b32d9033b47ec763c48362ab9d54b6ca50ee52f9add22d15fac7aa9eb0edf
GPU utilization avg   = 45.59% / 46.19%
src_transform_seconds = 7.84s / 7.72s per shard
src_transform_calls   = 394,032 / 384,816 per shard
```

Current rebuilt-binary result with shared source-transform reuse:

```text
wall_seconds = 45.923249
top5 score digest     = 402342fbf4659a331c13b8a5d31f803b967fcfe9c1fef1b6f3498e5284bdf944
top5 stability digest = bcd4ef7804df20d9a10038df701b70f36d1b8eabbc27301f610aff551bb03d22
top5 nt_score digest  = e45b32d9033b47ec763c48362ab9d54b6ca50ee52f9add22d15fac7aa9eb0edf
GPU utilization avg   = 54.39% / 53.63%
src_transform_seconds = 0.59s / 0.57s per shard
src_transform_calls   = 32,836 / 32,068 per shard
```

Current rebuilt-binary result with shared source-transform reuse and
`scoreInfo-prune max_per_task=16`:

```text
wall_seconds = 37.085567
top5 score digest     = 402342fbf4659a331c13b8a5d31f803b967fcfe9c1fef1b6f3498e5284bdf944
top5 stability digest = bcd4ef7804df20d9a10038df701b70f36d1b8eabbc27301f610aff551bb03d22
top5 nt_score digest  = e45b32d9033b47ec763c48362ab9d54b6ca50ee52f9add22d15fac7aa9eb0edf
traceback requests    = 4,588,115 / 4,458,028 per shard
```

This cap16 result is characterization-only. It is not the formal preset because
the stricter split chr22 runner gate showed a top5 score artifact mismatch: the
`score=185` CPU row was pruned out and replaced by a `score=178` row.

This is a real runtime improvement for the current GASAL2/top5 path:
shared source-transform reuse improved wall time by about `1.16x`, and the
cap16 characterization improves the same rebuilt path further to `37.085567s`.
The source-transform staging cost is no longer a major reason the GPUs sit
idle. The result is still a top5-summary artifact result only. It does not
prove full lite-output equivalence or make GASAL2 a drop-in `aligner.Align()`
replacement.

Remaining bottlenecks in this run are still:

```text
GASAL2 total          = 20.24s / 19.62s per shard
GASAL2 traceback wait = 9.25s / 9.01s per shard
exact-column wall     = 8.94s / 8.69s per shard
```

Small stream/batch tuning after the retained direct-CIGAR decode change did not
give a meaningful improvement. All rows below used the then-current formal
cap32 preset and kept the same top5 score/stability/nt-score digests:

```text
default streams=2 batch=30000:
  wall_seconds = 44.689421
  GPU utilization avg = 55.92%

streams=3 batch=20000:
  wall_seconds = 44.383549
  GPU utilization avg = 53.99%

streams=4 batch=15000:
  wall_seconds = 44.353659
  GPU utilization avg = 58.42%

streams=4 batch=15000 repeat:
  wall_seconds = 44.367033
  GPU utilization avg = 58.23%

streams=4 batch=10000:
  wall_seconds = 44.358734
  GPU utilization avg = 51.29%
```

The best repeated setting (`streams=4`, `batch=15000`) is only about `0.32s`
faster than the default retained run on a `44.69s` workload. Treat it as
noise-level optional tuning, not a new runtime default. The next useful work is
not more blind GASAL2 stream/batch tuning. It should target either fewer GASAL2
traceback requests, lower exact-column staging cost, or a more GPU-resident
scoreInfo/GASAL2 bridge while keeping the top5 artifact gate hard.

## ScoreInfo Emit-Rank Observe Checkpoint

`FASIM_TOP5_GASAL2_SCOREINFO_EMIT_RANK_OBSERVE=1` is a diagnostic-only counter
for the GASAL2/top5 path. It records the 1-based rank, within each task's
scoreInfo list, of scoreInfo groups that survive GASAL2 selection and conversion.
It does not change pruning, GASAL2 selection, output, digest, or runner defaults.

Historical cap32 preset, chr21+chr22:

```text
wall_seconds = 46.201252
top5 score/stability/nt_score digests = clean
scoreInfo emit-rank observed alignments = 12,396,001
max observed scoreInfo rank = 32

rank 1     =   766,505  ( 6.18%)
rank 2-4   = 2,170,384  (17.51%)
rank 5-8   = 2,498,359  (20.15%)
rank 9-16  = 3,610,895  (29.13%)
rank 17-32 = 3,349,858  (27.02%)
rank 33+   =         0  ( 0.00%)
```

This explains the cap16 no-go: rank `17-32` scoreInfo groups are not rare
noise; they contribute about `27%` of converted selected alignments in the
checked cap32 run. Cap32 was not arbitrary headroom on chr21+chr22: it was the
smallest observed envelope in this diagnostic run. The later MEG3 first32 gate
requires cap64 for the current preset.
Further traceback reduction should use a rank-aware or artifact-aware pruning
design, not a smaller fixed per-task cap.

`FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE=1` is the stricter
artifact-aware companion diagnostic. It records the scoreInfo rank only for rows
that survive the final in-process top5-lite artifact selection. The diagnostic
keeps the lite row text, output, digest, pruning, and GASAL2 selection unchanged.
Use it when deciding whether a future pruning design can target the final top5
artifact rather than all converted GASAL2-selected alignments.

When this diagnostic is enabled, each shard also writes a sidecar file:

```text
*-TFOsorted.lite.topk_rank.tsv
```

The sidecar contains `mode`, `rank_in_mode`, `scoreinfo_rank`, and the lite row
key for each score/stability/nt-score topK entry before cross-mode de-dup. It is
not read by the runner, merge, digest, or output path.

Historical cap32 preset, chr21+chr22, de-duped emitted top5-lite artifact rows:

```text
wall_seconds = 56.393715
top5 score digest     = 402342fbf4659a331c13b8a5d31f803b967fcfe9c1fef1b6f3498e5284bdf944
top5 stability digest = bcd4ef7804df20d9a10038df701b70f36d1b8eabbc27301f610aff551bb03d22
top5 nt_score digest  = e45b32d9033b47ec763c48362ab9d54b6ca50ee52f9add22d15fac7aa9eb0edf

de-duped top5-lite rows = 28
unknown rank rows    = 0
max scoreInfo rank   = 31

rank 1     =  6
rank 2-4   =  7
rank 5-8   = 10
rank 9-16  =  3
rank 17-32 =  2
rank 33+   =  0
```

The sidecar is intentionally larger than the de-duped emitted artifact when the
same row appears in multiple modes: it contains `3 * K` per-mode rows plus a
header. Its rows are diagnostic only. The sidecar shows the two rank `17-32`
rows are both `stability` mode rows:

```text
chr21 stability rank1:
  scoreinfo_rank = 21
  row = 41855932-41856000 ParaMinus rule=5 score=127 nt=74 stability=3.32838

chr22 stability rank1:
  scoreinfo_rank = 31
  row = 50307704-50307752 ParaPlus rule=5 score=96 nt=51 stability=3.36470
```

This confirms the cap16 no-go at the artifact level too: rank `17-32` rows can
survive into the final top5-lite set. Further pruning has to be artifact-aware
and validation-gated; a smaller fixed cap is not justified by the current
evidence.

The split chr22 runner gate now checks this sidecar as well. In that fixture,
the final top5 score list includes a row with `scoreinfo_rank=26`, and the
top5 digests remain clean:

```text
topk_summary_match=true
preset_topk_summary_match=true
score digest     = 4c44c23e5fbca989d56280e2e92a7ceac4ef1387567b6d8f9ec5a48dd6985fa7
stability digest = 0c481927dbeffc13eb5d1bd9d14cd2e6ef07701ff4ecde7828ceb30d97c9d1d8
nt_score digest  = aefc3b6a52861d3e88be8640d5e146dece55d7c5d67696ab71beb7128da2e2ef
```

So fixed caps below 32 are already contradicted by a checked artifact row, not
just by aggregate bucket counters.

A direct `cap24` probe on the split chr22 runner fixture is also no-go:

```text
artifact wall = 1.768675s
cap24 wall    = 1.568000s

score top5    = clean
nt_score top5 = clean
stability     = mismatch

missing stability rank5:
  row = 599900-599965 ParaMinus rule=2 score=99 nt=66 stability=3.20000
extra stability rank5:
  row = 928321-928390 ParaMinus rule=2 score=110 nt=70 stability=3.19571
```

This confirms that the remaining pruning opportunity is not a smaller uniform
cap. Stability rows can require candidates outside a score-oriented prefix even
when score and nt-score top5 stay clean.

The tighter-cap sweep on the same split fixture found only `cap31` clean:

```text
cap28:
  score/nt_score clean
  stability mismatch

cap30:
  score/nt_score clean
  stability mismatch

cap31:
  score/stability/nt_score clean
  traceback requests = 158,161 vs 175,642 artifact baseline
  wall = 1.643040s vs 1.759007s
```

On chr21+chr22, `cap31` also kept all three top5 digests clean:

```text
wall_seconds = 44.687435
top5 score digest     = 402342fbf4659a331c13b8a5d31f803b967fcfe9c1fef1b6f3498e5284bdf944
top5 stability digest = bcd4ef7804df20d9a10038df701b70f36d1b8eabbc27301f610aff551bb03d22
top5 nt_score digest  = e45b32d9033b47ec763c48362ab9d54b6ca50ee52f9add22d15fac7aa9eb0edf

traceback requests:
  cap32 = 12,396,001
  cap31 = 12,282,142
```

This historical cap31/cap32 comparison was clean but not useful enough to change
the then-current cap32 preset. The later MEG3 first32 formal runner preset gate
found a cap32 nt-score artifact miss; cap64 is now the conservative preset.

## Historical preAlign CUDA Max-Tasks Tuning

This section records a historical lower-level tuning run. It is not part of the
current formal `--gasal2-top5-column-pruned-scoreinfo` preset, and the current
formal helper rejects `PREALIGN_CUDA_MAX_TASKS` to keep the artifact contract
narrow and auditable.

In that lower-level experiment, the exact-column scoreInfo GPU path was flushed
by `FASIM_PREALIGN_CUDA_MAX_TASKS`, not by `FASIM_ALIGN_GASAL2_TASK_BATCH`.
`FASIM_ALIGN_GASAL2_TASK_BATCH` controlled the older GASAL2 bridge task batch
shape and did not change the exact-column batch count.

The retained historical cap32 chr21+chr22 baseline used
`runner_exact_scoreinfo_gpu_max_per_task=512`, which produced many small
exact-column flushes. A sweep of `FASIM_PREALIGN_CUDA_MAX_TASKS` kept the top5
score, stability, and nt-score digests clean while reducing exact-column batch
count:

```text
mode      wall       exact batches  exact wall  exact kernel  GASAL2 total  max GPU memory
baseline  44.689421  191            17.612990   17.208180     37.639500     19.8 / 20.0 GB
8192      43.717161   96            16.957030   16.554960     35.186600     19.9 / 20.1 GB
16384     43.005891   49            16.707770   16.308180     33.866200     20.1 / 20.3 GB
32768     43.142560   25            16.597550   16.165450     33.729000     20.5 / 20.7 GB
```

All rows used the then-current cap32 top5 GASAL2 path and kept the same artifact
digests:

```text
top5 score digest     = 402342fbf4659a331c13b8a5d31f803b967fcfe9c1fef1b6f3498e5284bdf944
top5 stability digest = bcd4ef7804df20d9a10038df701b70f36d1b8eabbc27301f610aff551bb03d22
top5 nt_score digest  = e45b32d9033b47ec763c48362ab9d54b6ca50ee52f9add22d15fac7aa9eb0edf
```

`16384` was the best observed point in this sweep:

```text
wall:          44.689421s -> 43.005891s
exact batches: 191 -> 49
top5 artifact: clean
GPU memory:    about 20.3 GB on 24 GB GPUs
```

`32768` reduces the batch count further, but it is slightly slower in wall time
and uses more memory. This historical lower-level evidence was later promoted
only after a fresh formal top5 matrix kept the CPU/full artifact gate clean.

## Managed preAlign Max-Tasks Setting

The formal `--gasal2-top5-column-pruned-scoreinfo` preset now manages
`FASIM_PREALIGN_CUDA_MAX_TASKS=16384`. Manual
`--env FASIM_PREALIGN_CUDA_MAX_TASKS=...` remains rejected by the formal preset;
use the lower-level probe when characterizing other values:

```bash
make check-fasim-gasal2-prealign-max-tasks-probe
```

The probe is intentionally not part of `make check-fasim-gasal2-top5-formal-gate`.
It compares the managed formal preset against equivalent lower-level top5 paths
with explicit `FASIM_PREALIGN_CUDA_MAX_TASKS` values and requires top5 summary,
topK-rows, and topK-lite artifacts to stay payload-clean.

Split chr22 fixture result before promotion:

```text
label           wall       speedup  exact batches  top5 payloads  overflow/fallback  max topK-lite scoreInfo rank
formal_default  1.758900   1.000x   3              clean          0/0                53
max4096         1.713112   1.027x   3              clean          0/0                53
max8192         1.681803   1.046x   2              clean          0/0                53
```

chr21+chr22 current-preset probe:

```text
label           wall       speedup  exact batches  GASAL2 requests  top5 payloads  overflow/fallback  max topK-lite scoreInfo rank
formal_default  60.437797  1.000x   191            43,637,981       clean          0/0                64
max8192         58.336248  1.036x    96            43,637,969       clean          0/0                64
```

The result is modest but repeatably useful for the current short-query top5
artifact path: fewer exact-scoreInfo GPU flushes, no overflow/fallback, and
unchanged top5 artifacts. It does not change the larger boundary: this remains a
top5-summary artifact path, not full lite-output equivalence and not a direct
`aligner.Align()` replacement.

A fresh current-preset lower-level probe on the same chr21+chr22/H19 target also
tested larger flush caps while keeping the formal `8192` preset as the artifact
reference:

```text
label           wall       speedup  exact batches  GASAL2 requests  top5 payloads  overflow/fallback  max topK-lite scoreInfo rank
formal_default  59.103306  1.000x    96            43,637,975       clean          0/0                64
max16384        57.506064  1.028x    49            43,637,960       clean          0/0                64
max32768        57.748087  1.023x    25            43,637,972       clean          0/0                64
```

`16384` was therefore promoted to the formal managed value. `32768` reduces batch
count further but is not faster in wall time. The recorded candidate result is
checked by
`make check-fasim-gasal2-prealign-max-tasks-chr21-chr22-result`.

Fresh post-promotion chr21+chr22 formal matrix:

```text
CPU worker wall sum       = 4565.987188s
formal worker wall sum    = 113.810705s
speedup vs CPU worker sum = 40.119136x
speedup vs CPU max worker = 40.443813x

GASAL2 requests           = 43,637,966
GASAL2 traceback requests = 13,701,121
exact scoreInfo GPU tasks = 778,848
exact scoreInfo batches   = 49
fallback/overflow         = 0 / 0
top5 score/stability/nt_score payloads = clean
```
