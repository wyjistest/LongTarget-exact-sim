# Fasim Long-Query Streaming ScoreInfo Two-Contract Bridge Design

This started as a design checkpoint and now has a default-off runtime scaffold.
It is not a real opt-in and does not change output behavior.

## Context

The current long-query streaming scoreInfo path has two relevant correctness
contracts:

```text
legacy calc-score contract:
  produces task.fullScore and minScore
  uses legacy calc-score query profile / target encoding

byte-profile scoreInfo contract:
  produces scoreInfo candidate groups
  uses SSW byte-profile / Lazy-F compatibility
```

The naive fused prototype is stopped:

```text
decision = fused_minscore_current_prototype_no_go
```

MALAT1 first8 fused boundary:

```text
tasks = 1824
fused_minscore_score_mismatches = 97
fused_minscore_min_score_mismatches = 97
scoreinfo_mismatches = 92
decision = streaming_scoreinfo_shadow_mismatch
```

That result means the two contracts cannot be treated as the same column-max
representation. The rule is: do not force one column-max representation to
satisfy both.

## Proposed Direction

The next allowed implementation direction is a two-contract bridge:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1
```

The bridge should preserve both GPU contracts explicitly:

```text
stage A: legacy calc-score GPU score/minScore
stage B: byte-profile streaming scoreInfo GPU compact
```

The goal is not one DP pass. The goal is one bounded bridge call that keeps the
two semantic contracts separate while reducing host-side orchestration.

## Current Prototype Checkpoint

The first scaffold uses the existing two GPU semantic passes behind a single
shadow switch:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1
```

It deliberately disables the naive fused minScore path, requests legacy-byte
scoreInfo compatibility, requests the legacy calc-score GPU minScore pass, and
reports two-contract-specific telemetry. CPU output remains authority.

MALAT1 first8 gate:

```text
decision = two_contract_bridge_shadow_active
two_contract_score_mismatches = 0
two_contract_min_score_mismatches = 0
two_contract_scoreinfo_mismatches = 0
two_contract_fallbacks = 0
fused_minscore_requested = 0
digest unchanged
```

This proves the scaffold can preserve the two contracts on the small boundary
fixture. It does not prove performance value and is not a production path.

The next default-off trust prototype feeds the two-contract scoreInfo output
into the existing realpath scoreInfo consumer:

```text
--long-query-streaming-scoreinfo-gpu-two-contract-trust
result_contract = long_query_streaming_scoreinfo_gpu_two_contract_trust_experimental_v1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1
decision = two_contract_bridge_trust_active
realpath_digest_authority = external_digest_gate
cpu_scoreinfo_groups = 0
cpu_prealign_seconds = 0
```

MALAT1 first8 remains digest-clean with `two_contract_score_mismatches = 0`,
`two_contract_min_score_mismatches = 0`, `two_contract_scoreinfo_mismatches = 0`,
and `two_contract_fallbacks = 0`. This is a trust prototype only: it is
default-off, external-digest-gated, and still not a broad long-query production
path.

## Shape

A future implementation should:

```text
1. Build one request descriptor batch.
2. Pack target buffers once per contract.
3. Reuse task descriptors across both contracts.
4. Run legacy calc-score GPU score/minScore.
5. Feed minScores to byte-profile streaming scoreInfo compact.
6. copy back score/minScore, scoreInfo counts, scoreInfo groups, overflow
7. Compare against CPU authority.
```

Expected bridge constraints:

```text
copy target buffers once per contract
reuse task descriptors
reuse query handles
bounded flush
no long-lived copied request snapshots
```

This still uses two GPU semantic passes. It only tries to reduce duplicate
host orchestration, validation staging, and bridge overhead.

## Telemetry

Required telemetry:

```text
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_requested
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_active
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_used
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_fallbacks
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_score_mismatches
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_min_score_mismatches
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_scoreinfo_mismatches
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_total_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_h2d_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_kernel_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_d2h_seconds
```

Continue reporting existing scoreInfo counters:

```text
candidate_missing
candidate_extra
gpu_scoreinfo_groups
cpu_scoreinfo_groups
output digest
```

## Correctness Gate

Hard gate:

```text
score_mismatches = 0
min_score_mismatches = 0
scoreinfo_mismatches = 0
candidate_missing = 0
candidate_extra = 0
digest unchanged
```

CPU output remains authority. GPU endpoint remains forbidden. GPU CIGAR remains
forbidden. GPU traceback remains forbidden.

## Performance Gate

The target workload is NEAT1 first64 because it exposes the current two-pass GPU
cost:

```text
NEAT1 first64:
  candidate/baseline speedup > 1.0x
  GPU total < current two-pass GPU total
```

If bridge still loses to CPU, stop long-query scoreInfo GPU real path. Do not
promote a correctness-clean bridge unless it also gives real runtime value.

## Non-Goals

Do not:

```text
change default behavior
use GPU output
add real opt-in
use GPU endpoint authority
use GPU CIGAR authority
use GPU traceback authority
claim single-pass fused is correctness-clean
claim full goal complete
```

## Decision

```text
decision = two_contract_bridge_design_ready
```

Ready means the next implementation should preserve the two contracts instead
of trying to collapse them into one column-max pass.

## Gate

```bash
make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design
```
