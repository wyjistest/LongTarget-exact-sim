# Fasim Score-Only GPU Bridge Prototype

This note documents the default-off low-copy score-only GPU bridge prototype
for the current clean Fasim base.

## Scope

This PR adds a diagnostic shadow path:

```text
FASIM_ALIGN_SCORE_BRIDGE_GPU_SHADOW=1
```

The active current-base runtime remains:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
FASIM_EXTEND_THREADS=6
FASIM_ALIGN_PROFILE_CACHE=1
process-level sharding
```

The bridge prototype does not change runtime semantics. CPU `aligner.Align()`
remains authoritative for score, endpoint, traceback, CIGAR, candidate state,
output, threshold decisions, non-overlap decisions, and digest.

The GPU bridge result is diagnostic only:

```text
no GPU score in production output
no GPU endpoint authority
no GPU CIGAR
no GPU traceback
no candidate/output/digest integration
no scheduler/default policy change
```

## Design Difference From #157/#158

The earlier batch shadow retained copied query/reference buffers per request
until telemetry snapshot time. That was useful for correctness probing, but it
was not a credible real path for hg38-scale request counts.

This prototype changes the collection shape:

```text
same query/scoring/gap config -> one bridge group
one translated query copy per group
one score matrix copy per group
one descriptor per request
one contiguous target-window buffer
bounded request cap
```

Descriptors record the diagnostic metadata needed to compare GPU score/end
against CPU authority:

```text
group index
target buffer offset
target length
CPU score
CPU ref/read end
CPU forward-score seconds
```

The first prototype still calls the existing conservative batch score kernel at
flush time. This PR is therefore a descriptor/buffer architecture prototype, not
a final GPU score implementation.

## Env

```text
FASIM_ALIGN_SCORE_BRIDGE_GPU_SHADOW=1
```

Optional diagnostic cap:

```text
FASIM_ALIGN_SCORE_BRIDGE_GPU_SHADOW_MAX_REQUESTS=<N>
```

The cap defaults to 100,000 requests per Fasim process. Requests beyond the cap
are counted as unsupported and are not sent through the bridge. CPU alignment
and output are unaffected.

## Telemetry

Fasim emits these fields on stderr:

| field | meaning |
|---|---|
| `benchmark.fasim_score_bridge_shadow_enabled` | `1` when the bridge shadow was requested or collected requests. |
| `benchmark.fasim_score_bridge_requests` | Forward score/end requests accepted by the bridge collector. |
| `benchmark.fasim_score_bridge_cells` | Sum of query length times target length for accepted requests. |
| `benchmark.fasim_score_bridge_groups` | Query/scoring/gap groups flushed by the bridge. |
| `benchmark.fasim_score_bridge_descriptor_count` | Number of descriptors retained. |
| `benchmark.fasim_score_bridge_descriptor_bytes` | Host bytes used by descriptor records. |
| `benchmark.fasim_score_bridge_query_buffer_bytes` | Query bytes retained once per group. |
| `benchmark.fasim_score_bridge_target_buffer_bytes` | Contiguous target-window bytes retained. |
| `benchmark.fasim_score_bridge_pack_seconds` | Host descriptor/group/target packing seconds. |
| `benchmark.fasim_score_bridge_h2d_seconds` | Host-to-device copy seconds from the score batch kernel call. |
| `benchmark.fasim_score_bridge_kernel_seconds` | CUDA event kernel seconds. |
| `benchmark.fasim_score_bridge_d2h_seconds` | Device-to-host result copy seconds. |
| `benchmark.fasim_score_bridge_unpack_seconds` | Result comparison/unpack seconds. |
| `benchmark.fasim_score_bridge_total_seconds` | End-to-end GPU bridge batch seconds from the CUDA helper. |
| `benchmark.fasim_score_bridge_cpu_reference_seconds` | CPU authority forward score/end seconds for accepted requests. |
| `benchmark.fasim_score_bridge_score_mismatches` | GPU score mismatches versus CPU authority. |
| `benchmark.fasim_score_bridge_endpoint_mismatches` | Optional endpoint diagnostic mismatches. |
| `benchmark.fasim_score_bridge_unsupported_requests` | Requests rejected by cap, invalid input, or CUDA helper failure. |

The sharded runner aggregates these fields into per-shard, per-worker, and
top-level telemetry.

## Smoke Signal

Run:

```bash
make check-fasim-score-bridge-shadow
```

Observed local small-fixture signal:

```text
requests: 165
cells: 31,446,596
groups: 1
descriptor_count: 165
descriptor_bytes: 5,280
query_buffer_bytes: 2,812
target_buffer_bytes: 11,183
CPU forward score/end seconds: ~0.0071s
bridge GPU total seconds: ~0.0175s
score mismatches: 0
endpoint mismatches: 0
unsupported requests: 0
```

This confirms the descriptor/query-reuse shape works on the smoke fixture and
keeps output unchanged. It is not a performance claim. The current kernel is
still the conservative batch score kernel from #157, so the small fixture
remains slower than CPU forward score/end.

## Decision Use

Use this PR as a narrow prototype of the low-copy bridge data path. Do not
promote it to a real path.

Continue only if real-workload characterization shows:

```text
score_mismatches = 0
digest unchanged
unsupported requests are zero or explainable
bridge total < CPU forward score/end
pack/H2D/kernel/D2H/unpack costs are clearly itemized
peak retained bytes are bounded
```

Stop the GPU score path if:

```text
bridge total remains slower than CPU forward score/end
pack/copy/staging remains close to CPU forward score/end
the conservative kernel remains the dominant cost without a better DP design
full workload still requires too much target-window retention
score mismatches appear
score-only results cannot be evaluated without changing candidate/output state
```

Do not use this prototype to justify:

```text
GPU endpoint authority
GPU CIGAR
GPU traceback
GPU full extension replacement
Accelign or Parasail real output authority
single-process multi-GPU policy
historical final speed-stack env claims
```
