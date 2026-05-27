# Fasim Score-Only GPU Bridge Design

This note defines a possible low-copy score-only GPU bridge for the current
clean Fasim base. It is a design checkpoint, not a runtime implementation.

## Scope

The active current-base runtime remains:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
FASIM_EXTEND_THREADS=6
FASIM_ALIGN_PROFILE_CACHE=1
process-level sharding
```

This design does not add a real GPU score path and does not change output
semantics. CPU `aligner.Align()` remains authoritative for score, endpoint,
traceback, CIGAR, candidate state, output, and digest.

The design explicitly excludes:

```text
GPU output authority
GPU endpoint authority
GPU CIGAR
GPU traceback
GPU full extension replacement
Accelign or Parasail real output authority
scheduler/default policy changes
merge/chunking/in-process multi-GPU changes
historical final speed-stack env reuse
```

## Context

The current GPU score investigation has three checkpoints.

First, the per-request shadow:

```text
FASIM_ALIGN_FORWARD_SCORE_GPU_SHADOW=1
```

Local smoke showed score/end correctness alignment, but the performance result
was a hard no-go:

```text
requests: 165
cells: 31,446,596
score mismatches: 0
endpoint mismatches: 0
CPU forward score/end seconds: ~0.005s
GPU shadow total seconds: ~3.1s
```

Second, the batched shadow:

```text
FASIM_ALIGN_FORWARD_SCORE_GPU_BATCH_SHADOW=1
```

Batching reduced dispatch overhead dramatically on the smoke fixture:

```text
per-request GPU shadow total: ~3.1s
batch GPU shadow total: ~0.02s
CPU forward score/end seconds: ~0.0052s
```

That proved batching is the right diagnostic shape, but the conservative batch
kernel still did not beat CPU on the smoke fixture.

Third, real-workload characterization of the batch shadow showed mixed results:

```text
digest clean: 12/12
preAlign CUDA fallbacks: 0
batch score mismatches: 0
batch endpoint mismatches: 0

rheMac10 top8:
  GPU total / CPU reference: 0.70-0.95x

hg38 chr21+chr22 workers=4 cap=100000:
  processed about 14% of requests
  GPU total / processed CPU estimate: 1.07x
```

The current batch scaffold is useful as a correctness and architecture probe,
but it retains copied request snapshots until telemetry time and is not viable
as a real hg38-scale path. Continuing the same implementation would mostly
measure copy, allocation, staging, and snapshot-retention costs.

## Design Goal

If GPU score work continues, the next useful step is not a new real opt-in. It
is a low-copy score-only bridge prototype that answers one narrow question:

```text
Can a contiguous, query-reuse score-only bridge keep total GPU shadow time
below CPU forward score/end time without changing Fasim output?
```

The bridge must remain diagnostic until a later PR proves:

```text
score_mismatches = 0
digest unchanged
GPU total < CPU forward score/end
copy/staging costs are bounded
unsupported requests are zero or explainable
```

Endpoint comparisons may be collected as diagnostics. They must not become
output authority.

## Request Descriptor

The current snapshot collector copies per-request query/reference buffers. The
bridge should instead store compact descriptors that point into owned or
reusable contiguous buffers:

| field | purpose |
|---|---|
| `request_id` | Stable diagnostic id for mismatch reporting. |
| `query_key` | Identifies the translated query sequence and scoring context. |
| `target_buffer_offset` | Offset into the contiguous target-window buffer. |
| `target_length` | Target window length for this request. |
| `query_length` | Query length for cell accounting and kernel bounds. |
| `scoring_config_key` | Match/mismatch/gap-open/gap-extend/score-type key. |
| `orientation_key` | Strand/orientation flag if it affects translated input. |
| `cpu_score` | CPU authority forward-score result for comparison. |
| `cpu_endpoint` | Optional CPU authority endpoint for diagnostic comparison. |
| `output_slot` | Diagnostic-only result slot; not a Fasim output slot. |

Descriptors must not hold per-request string copies. They should be POD-style
records that can be copied to the device as a single contiguous descriptor
array.

## Buffer Layout

The bridge should split long-lived sequence ownership from per-batch request
metadata.

Query buffers:

```text
one translated query buffer per query_key
uploaded once per bridge flush or kept device-resident during a flush group
shared across many target windows
```

Target buffers:

```text
target windows packed contiguously
descriptor stores offset and length
no long-lived full request snapshots
```

Result buffers:

```text
score output array
optional endpoint diagnostic output array
unsupported/status output array
```

The first prototype may still pack target windows into a temporary host buffer,
but it should measure bytes and seconds separately. If host packing dominates,
the design should stop unless an existing translated/encoded target layout can
be reused directly.

## Flush Model

The bridge should flush by query/scoring group, not by individual request.

Recommended grouping key:

```text
query hash
query length
scoring config
gap open / gap extend
score type / byte-word mode
orientation / strand if relevant
alphabet / transform mode if relevant
```

Within each group:

```text
1. Append lightweight descriptors.
2. Append or reference target windows in a contiguous target buffer.
3. Upload one query buffer for the group.
4. Upload descriptor and target buffers.
5. Run one or a few score-only kernels.
6. Download score and optional endpoint diagnostics.
7. Compare against CPU authority results.
8. Discard diagnostic buffers.
```

The bridge must not wait for a full workload snapshot if doing so requires
retaining copied targets for millions of requests. It should use bounded flushes
controlled by bytes, request count, or shard completion.

## Telemetry Plan

A prototype PR should emit bridge-specific telemetry rather than reusing the
current batch-shadow fields in a way that hides the new layout. Suggested
fields:

| field | meaning |
|---|---|
| `benchmark.fasim_score_bridge_shadow_enabled` | `1` when the future bridge shadow is enabled. |
| `benchmark.fasim_score_bridge_requests` | Requests accepted into the bridge. |
| `benchmark.fasim_score_bridge_cells` | Sum of query length times target length. |
| `benchmark.fasim_score_bridge_groups` | Number of query/scoring flush groups. |
| `benchmark.fasim_score_bridge_descriptor_bytes` | Host descriptor bytes copied or retained. |
| `benchmark.fasim_score_bridge_query_bytes` | Query bytes uploaded or staged. |
| `benchmark.fasim_score_bridge_target_bytes` | Target-window bytes uploaded or staged. |
| `benchmark.fasim_score_bridge_pack_seconds` | Host descriptor/target packing seconds. |
| `benchmark.fasim_score_bridge_h2d_seconds` | Host-to-device copy seconds. |
| `benchmark.fasim_score_bridge_kernel_seconds` | CUDA event kernel seconds. |
| `benchmark.fasim_score_bridge_d2h_seconds` | Device-to-host result copy seconds. |
| `benchmark.fasim_score_bridge_unpack_seconds` | Result comparison/unpack seconds. |
| `benchmark.fasim_score_bridge_total_seconds` | End-to-end bridge shadow seconds. |
| `benchmark.fasim_score_bridge_cpu_reference_seconds` | CPU authority forward score/end seconds for compared requests. |
| `benchmark.fasim_score_bridge_score_mismatches` | GPU score mismatches versus CPU authority. |
| `benchmark.fasim_score_bridge_endpoint_mismatches` | Optional endpoint diagnostic mismatches. |
| `benchmark.fasim_score_bridge_unsupported_requests` | Requests rejected by the bridge. |
| `benchmark.fasim_score_bridge_peak_buffer_bytes` | Peak host/device staging bytes if available. |

The sharded runner parser should aggregate these fields per shard, per worker,
and at the run level before any real performance claim is made.

## Correctness Boundary

The CPU path must continue to run normally in any bridge prototype. GPU score
results must not feed:

```text
endpoint recovery
reverse-start
traceback
CIGAR construction
candidate state
record emission
digest
threshold/non-overlap decisions
```

The bridge can only compare score and optional endpoint diagnostics after CPU
authority work completes. Digest cleanliness proves the diagnostic path did not
perturb output; it does not prove GPU score is safe for output authority.

## Feasibility Gates

Continue from design to prototype only if the prototype can test a materially
different architecture from the current copy-retaining batch scaffold:

```text
lightweight descriptors
bounded flushes
query reuse
contiguous target staging
no full-workload retained request snapshots
itemized copy/kernel/readback telemetry
```

Stop the GPU score path if:

```text
projected pack/copy/staging cost remains near CPU forward score/end
the kernel remains slower without a credible parallel DP design
full-workload capture still requires copied target snapshots
score mismatches appear
score-only results cannot be evaluated without changing candidate/output state
```

Proceed beyond a prototype shadow only if:

```text
score_mismatches = 0
digest unchanged
unsupported requests are zero or explainable
bridge total < CPU forward score/end on real workloads
peak memory is bounded for hg38-scale workloads
```

Even then, the next step would still be a shadow or precheck design. It would
not be GPU endpoint/CIGAR/output authority.

## Recommended Next PR

If this design is accepted, the next PR should be a default-off prototype
shadow that implements only the bridge data path and telemetry. It should not
promote any GPU score result into real Fasim output.

Minimum workload gate:

```text
rheMac10_nonchrom_top8_H19
hg38_chr21_chr22_H19
FASIM_ENABLE_PREALIGN_CUDA=1
FASIM_EXTEND_THREADS=6
FASIM_ALIGN_PROFILE_CACHE=1
process-level sharding, one visible GPU per worker
```

Minimum decision table:

| outcome | decision |
|---|---|
| score clean and bridge total beats CPU forward score/end | Continue with a stricter shadow/precheck design. |
| score clean but bridge total is not faster | Stop GPU forward-score path. |
| pack/H2D/D2H dominates | Continue only if current source can provide reusable contiguous/device-resident input. |
| score mismatches appear | Stop and debug scoring, alphabet, gap, or score-type handling. |
| endpoint mismatches appear while scores are clean | Keep endpoint out of any proposed real path. |

The practical current-base runtime remains the recommendation unless the bridge
prototype clears these gates:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
FASIM_EXTEND_THREADS=6
FASIM_ALIGN_PROFILE_CACHE=1
process-level sharding
```
