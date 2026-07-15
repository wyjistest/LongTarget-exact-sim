# GASAL2-LongTarget paper benchmark protocol

## Freeze

```text
protocol_version = 2
paper_runtime_epoch = 0
paper_runtime_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
paired_order_seed = 20260715
bootstrap_seed = 20260715
workload_manifest_sha256 = b099762257b60ce2922a7e19920bad30e05b9cdf2af4381c60596a41ca3cb7d3
```

Protocol version 2 was frozen before the first paper benchmark run. It changes
only the C1 hard timeout from 1800 to 2700 seconds because the inventoried
pre-paper CPU authority required 2304.607424 seconds on the same two-chromosome
scope. Workload selection, inputs, repeats, order seed, modes, preset and output
contract are unchanged. All other short-query and generalization rows retain
the 1800-second ceiling.

`paper/workload_manifest.tsv` and its SHA-256 receipt are committed before any
paper benchmark run. Rows are never removed after results are observed.
Additions require a protocol amendment with a new manifest digest and cannot be
pooled silently with the original preregistered panel.

## Build

The frozen build entry point is:

```bash
make build-fasim-gasal2 \
  CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-12.5}" \
  CUDA_ARCH="${CUDA_ARCH:-89}" \
  FASIM_GASAL2_TARGET=.tmp/fasim_longtarget_gasal2_direct
```

The runtime binary SHA-256 is recorded for every run. Compiler, CUDA toolkit,
driver, GPU, CPU, governors and visible-device state are captured by
`scripts/capture_fasim_gasal2_paper_environment.py`. The default supported
density is one worker per GPU. C1 requires two visible GPUs because its frozen
scope is the two-worker/two-GPU sharded configuration; no one-GPU result may be
substituted under the same workload ID.

## Inputs

Manifest `query_path` and `target_path` identify source FASTA files and include
SHA-256 digests. Query fragments are determined only by the preregistered
0-based half-open `query_start_nt/query_end_nt` interval. Target slices use the
preregistered `slice:start-end` interval. Fragment and slice materialization is
performed before timed execution and its digest is included in `run-config.json`.

Generalization uses a fixed Latin-square-like assignment across MALAT1, NEAT1
and KCNQ1OT1:

```text
lengths = 1024, 2048, 2812
positions = 5p, mid, 3p
targets = center 2-Mb slices of chr11, chr21, chr22
preset = gasal2_short_topk_v1 for every supported row
```

Coordinates are selected from source length and the declared position, not from
prediction results. H19 and MEG3 breadth rows use the same preset. Full MALAT1,
NEAT1 and KCNQ1OT1 are preflight-only negative controls; their known CPU
fallback workloads are not executed.

## Timing boundary

The primary wall interval starts immediately before the existing scientific
runner command and ends when that command exits. It includes target/query reads
performed by that runner, sharding internal to that runner, GPU work, host
finalization and declared output writing. It excludes deterministic fragment
materialization, environment capture, post-run correctness comparison, source
data collection and figure generation.

Every baseline/candidate pair uses the same boundary and output contract.
Storage characterization separately reports run wall, restore wall, merge wall
and their explicit sum. Kernel, exact-stage, merge or restore intervals are
never substituted for end-to-end wall.

## Warm-up and paired order

Each workload/mode receives one unmeasured warm-up receipt before timed pairs.
Warm-ups use the same binary, inputs and preset and are stored as:

```text
<workload_id>__warmup__<baseline|candidate>__0
```

Timed run IDs are:

```text
<workload_id>__pairNN__<baseline|candidate>__0
```

AB/BA order is reconstructed from SHA-256 of seed plus workload ID and then
alternated by pair number. This gives an ABBA-style balanced order without
examining results. Invocation order and expected warm-up receipt are recorded
in `run-config.json`.

## Repeat counts

```text
C1 H19 chr21+chr22 fast top-K = 5 valid pairs
C4 chr21 two-slot = 5 valid pairs
C4 chr22 two-slot = 5 valid pairs
C7 bounded max8 = 3 valid pairs
generalization_core = 3 valid pairs per row
breadth = 1 valid pair per row
component ablation = 3 compatible pairs
expensive descriptive = 1 run per mode or digest-verified historical evidence
negative controls = one preflight guard receipt and no fallback execution
```

Segments, target windows, CUDA batches and shards are not independent
replicates.

## Correctness contracts

Every manifest row declares exactly one of:

```text
full_tfosorted_rowset
fast_topk_score_stability_nt
shifted_grid_bounded_full_rows
archive_restore_only
preflight_guard_only
```

Fast top-K candidate runs require separate score, stability and Nt clustered
TFO1-TFO5 equality, boundary-tie accounting and zero fallback, length guard,
runtime batch fallback, overflow fallback and OOM. Full-output rows require
missing rows, extra rows and row-count equality; byte equality is required only
where the workload declares deterministic bytes. Guard rows require
`supported=0`, `reason=query_length_contract` and no GPU fast-path execution.

The harness preserves a per-run correctness status. Pair comparators are the
existing repository comparators selected by the adapter:

```text
check_topk_summary_digest_integrity.py
compare_fasim_tfosorted_tfo_contract.py
compare_fasim_lite_topk.py
compare_fasim_gasal2_long_query_integrated.py
```

Mismatch is a result, not a harness failure. Comparator execution failure is a
technical failure and must be recorded separately.

## Telemetry

When available, each run preserves:

```text
outer wall seconds
/usr/bin/time -v and peak host RSS
GPU memory/utilization sample
GASAL2 requests and traceback requests
exact tasks, cells, launches and stage seconds
traceback host-observed stage seconds
merge, restore, dedup and output-write seconds
fallback, guard, overflow, allocation and OOM counters
CPU/GPU affinity and machine state
```

Unavailable device or host metrics are `NA`/`unavailable`, never numeric zero.
No new global CUDA synchronization is added for paper telemetry.

## Resume and artifact lifecycle

Pre-freeze raw runs are written under:

```text
.paper-artifacts/runtime-epoch-0-pre-freeze/
```

The harness computes a canonical config digest from runtime epoch/commit,
binary digest, complete manifest row, mode, pair, order and seed. A run is
published by atomic directory rename only after command success, collection and
an atomic `run-complete.json` receipt. Existing run IDs are never overwritten.

`--resume` reuses only a complete receipt with the identical config digest.
Incomplete receipts and config drift fail closed. Failed runs are preserved
with a `.failed.<timestamp>` suffix. Phase 5 copies accepted raw artifacts into
`.paper-artifacts/<data_freeze_id>/` and writes the immutable manifest.

## Exclusions and reruns

Only these technical failures can be excluded from performance statistics:

```text
binary/input/config digest mismatch
machine reboot or driver reset during run
external process consumed configured GPU/CPU resources
infrastructure timeout
corrupt or incomplete log
correctness comparator could not execute
```

Slow runs, mismatch, fallback, tested-preset OOM and unexpectedly low speedup
remain in the run inventory. A rerun never deletes the original receipt. Phase
5 records exclusions in `paper/source_data/exclusions.tsv` with evidence and
rerun linkage.

## Timeouts

```text
C1 two-chromosome CPU authority mode = at most 2700 seconds
other short and generalization modes = at most 1800 seconds
two-slot chromosome mode = at most 900 seconds
bounded max8 mode = at most 2700 seconds
preflight guard = at most 60 seconds
full 121-segment KCNQ1OT1 and full hg38 = prohibited
```

An expensive descriptive row above its cap uses committed historical or
digest-verified evidence and receives no bootstrap confidence interval.

## Statistical analysis

The primary effect per valid pair is baseline wall divided by candidate wall.
Phase 5 reports median paired speedup, median baseline/candidate wall, IQR,
range and a 10,000-resample bootstrap 95% interval for the median when at least
three valid pairs exist. Bootstrap seed is `20260715`; no p-value is required.
