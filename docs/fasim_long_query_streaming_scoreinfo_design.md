# Fasim Long-Query Streaming ScoreInfo Design

This is a design checkpoint only. It records the next plausible long-query
scoreInfo/preAlign GPU direction after the exact-tile and exact-column probes
were stopped.

GASAL2 / GPU scoreInfo scoped feasibility checkpoint:

```text
MALAT1 streaming scoreInfo trust path: scoped go
NEAT1 streaming scoreInfo trust path: performance no-go
Broad scoreInfo/preAlign replacement: not proven
```

## Scope

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1
```

CPU fallback remains authority. The shadow has no output authority, no endpoint
authority, no CIGAR authority, and no traceback authority. It must not affect
candidate state, output, digest, scheduler policy, or default behavior.

This is not exact-tile union and not shared-memory opt-in. It is a different
lower-shared-memory DP layout.

## Historical Skeleton Checkpoint

The first skeleton checkpoint was telemetry-only:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1:
  requested = 1
  active = 0
  unsupported = 1
  decision = streaming_scoreinfo_shadow_not_implemented
```

For MALAT1 first8 the skeleton records the long-query shape without changing
the lite output digest:

```text
query_len = 8708
stripe_len = 2812
stripes = 4
tasks > 0
cells > 0
```

This checkpoint only establishes the default-off control surface and accounting
for the next architecture. It does not run a streaming GPU kernel and does not
compare scoreInfo candidates yet.

## Active Shadow Checkpoint

The first low-shared-memory/global-state shadow can launch on MALAT1 first8 and
cover the full request surface, but the exact/scalar DP variant is not
scoreInfo-equivalent:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1:
  requested = 1
  active = 1
  unsupported = 0
  query_len = 8708
  tasks = 1824
  cells = 8121408
  gpu_batches = 16
  gpu_tasks = 1824
  gpu_scoreinfo_groups = 31272
  cpu_scoreinfo_groups = 31272
  scoreinfo_mismatches = 1
  candidate_missing = 0
  candidate_extra = 0
  GPU total ~= 1.95s
  CPU preAlign reference ~= 4.95s
  decision = streaming_scoreinfo_shadow_mismatch
```

This is progress over the exact-column shared-memory resource failure because
the long-query GPU path launches and covers all MALAT1 first8 tasks. It is still
shadow-only and no-go for real output.

The first mismatch is now localized:

```text
first_mismatch:
  task = 130
  global_task = 130
  rule = 12
  strand = 1
  Para = -1
  dna_start_pos = 9800
  target_len = 5000
  min_score = 202
  diff_index = 0
  cpu scoreInfo = 228@465
  gpu scoreInfo = 228@463

column window:
  CPU SSW preAlign = 461:217,462:220,463:225,464:223,465:228,466:224,467:220,468:216,469:212
  GPU streaming   = 461:218,462:223,463:228,464:224,465:228,466:224,467:220,468:216,469:212
  scalar SW       = 461:218,462:223,463:228,464:224,465:228,466:224,467:220,468:216,469:212
```

That proves the current mismatch is not a scoreInfo compact tie-policy issue.
The GPU streaming path matches scalar Smith-Waterman in this window, while
legacy CPU `preAlign` follows the SSW byte-profile/bias/saturation path. The
next implementation gate is therefore legacy-byte compatibility, not another
exact 16-bit SW kernel.

## Legacy-Byte Shadow Checkpoint

The legacy-byte variant adds an SSW byte-profile-compatible shadow:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1
```

On MALAT1 first8 it now matches the CPU `aligner.preAlign` scoreInfo surface:

```text
requested = 1
active = 1
unsupported = 0
query_len = 8708
tasks = 1824
gpu_batches = 16
gpu_tasks = 1824
gpu_scoreinfo_groups = 31272
cpu_scoreinfo_groups = 31272
scoreinfo_mismatches = 0
candidate_missing = 0
candidate_extra = 0
decision = streaming_scoreinfo_shadow_active
```

The root compatibility fix is CPU SSW byte semantics, not ordinary scalar SW:
the legacy CUDA shadow uses 16-byte striped query profile layout, unsigned
saturating byte arithmetic, and the SSE2 Lazy-F signed byte compare with a
16-pass bound.

This is a correctness milestone for MALAT1 first8 scoreInfo shadowing. It is
not a production replacement yet:

```text
GPU total ~= 12.54s
CPU preAlign reference ~= 4.95s
```

So the legacy-byte shadow is correctness-clean but performance no-go for the
current implementation.

The shared-memory legacy-byte variant reduces the current kernel cost while
preserving the same scoreInfo surface:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1
legacy_byte_shared = 1
scoreinfo_mismatches = 0
candidate_missing = 0
candidate_extra = 0
GPU total ~= 9.96s
kernel ~= 3.61s
```

This is better than the global-state legacy-byte kernel, but it is still slower
than the CPU preAlign reference for MALAT1 first8 and remains shadow-only.
The shadow telemetry now splits the wall time so the production-path question is
not conflated with validation work:

```text
minscore seconds:
  calc_score_once() threshold recomputation done only by this shadow.

minscore cache hits/misses:
  whether the shadow reused a StreamTask minScore computed earlier in the same
  batch or had to compute it before the GPU call.

gpu_call seconds:
  CUDA scoreInfo call wall time, including launch, H2D, kernels, D2H, and host
  result materialization inside the bridge.

validation seconds:
  CPU preAlign authority replay plus pruning/compare work used only to prove
  scoreInfo equivalence.

cpu_prealign seconds:
  the CPU preAlign part of validation.

compare seconds:
  scoreInfo prune/equality bookkeeping after CPU preAlign.
```

A default-off GPU minScore source probe exists:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1
```

It uses a lower-shared-memory global-state legacy max-score kernel as a
shadow-side source for scoreInfo thresholds. On MALAT1 first8 the source is
score/minScore-clean against `calc_score_once()`:

```text
gpu_minscore_requested = 1
gpu_minscore_active = 1
gpu_minscore_used = 1824
gpu_minscore_fallbacks = 0
gpu_minscore_score_mismatches = 0
gpu_minscore_min_score_mismatches = 0
gpu_minscore_error = none
```

The current shadow still computes CPU `calc_score_once()` for validation, so
`minscore_seconds` is not yet a production-path estimate. The remaining
production-path question is whether a shadow/prototype can skip CPU minScore
authority on the hot path while keeping CPU validation/fallback default-off.

The production-style hot-path probe is:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1
```

In that mode the GPU minScore feeds the GPU scoreInfo call before CPU
`calc_score_once()` validation runs. The gate requires:

```text
gpu_minscore_hot = 1
gpu_minscore_used = tasks
gpu_minscore_fallbacks = 0
gpu_minscore_score_mismatches = 0
gpu_minscore_min_score_mismatches = 0
minscore_seconds <= 0.05
validation_minscore_seconds > 0
```

### MALAT1 Hot-Path Characterization

The hot-path probe remains shadow-only, but the larger MALAT1 samples now give a
cleaner performance boundary than first8 alone:

```text
record_limit  tasks  scoreInfo  GPU hot total  CPU preAlign  speedup
8             1824   clean      5.22283s       4.94896s      0.947563x
16            4416   clean      11.2088s       12.3032s      1.097638x
32            8160   clean      22.0937s       22.6672s      1.025958x
64            18096  clean      45.5043s       50.3037s      1.105471x
```

For first16/first32/first64:

```text
scoreinfo_mismatches = 0
candidate_missing = 0
candidate_extra = 0
gpu_minscore_fallbacks = 0
gpu_minscore_score_mismatches = 0
gpu_minscore_min_score_mismatches = 0
```

This is a real milestone: scoreInfo correctness stays clean through first64,
and the production-style hot path is approximately at parity to 1.1x faster
than the CPU preAlign reference once the sample grows beyond first8. It is still
not production-ready. The speedup is marginal, CPU validation/fallback remains
the authority, and the path still needs broader MALAT1/NEAT1/workload coverage
before any default-off production-path prototype can be justified.

The heavy characterization command is:

```bash
make characterize-fasim-long-query-streaming-scoreinfo-hot
```

### Validation-First Real-Path Prototype

The first default-off real-path prototype is:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE=1
```

It does not use GPU endpoint, CIGAR, traceback, or GASAL2 long-query traceback.
The only production-path substitution is:

```text
CPU fastSIM internal preAlign scoreInfo
  -> CPU-validated GPU streaming scoreInfo

CPU extend / traceback / triplex conversion
  remains authority
```

On MALAT1 first8 with legacy-byte shared mode and GPU minScore hot path:

```text
realpath_requested = 1
realpath_used = 1824
realpath_fallbacks = 0
realpath_digest_authority = cpu_validated
digest = b51800fd831dd50fe8ea994e91e8b55c421b36f0c4550328b74316152fbf77cd
```

This proves a narrow scoreInfo/preAlign replacement path exists for the checked
MALAT1 first8 shape. It is still validation-first and default-off. It is not a
broad long-query runtime path because NEAT1 remains performance no-go and
GASAL2 traceback is not used for long-query replacement.

The broader real-path prototype characterization keeps that contract clean
through MALAT1 first64:

```text
record_limit  tasks  realpath_used  fallback  scoreInfo  GPU total  CPU preAlign  cpu/GPU
8             1824   1824           0         clean      5.21243s   4.95148s      0.949937x
16            4416   4416           0         clean      11.2673s   12.2928s      1.091016x
32            8160   8160           0         clean      22.264s    22.6416s      1.016960x
64            18096  18096          0         clean      45.4425s   50.2407s      1.105588x
```

This is stronger than the first8 smoke: GPU scoreInfo is actually fed into
`fastSIM_extend_from_scoreinfo()` for every checked MALAT1 task through first64.
The performance signal is still marginal and validation-heavy, so this remains
a default-off prototype/characterization path rather than a production runtime.

The real-path characterization command is:

```bash
make characterize-fasim-long-query-streaming-scoreinfo-realpath
```

### External-Digest-Gated Trust Prototype

The next default-off step removes per-task CPU `preAlign` validation from the
candidate run and relies on the checker to compare baseline/candidate output
digest:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST=1
```

On MALAT1 first8:

```text
realpath_requested = 1
realpath_trust = 1
realpath_used = 1824
realpath_fallbacks = 0
realpath_digest_authority = external_digest_gate
cpu_scoreinfo_groups = 0
cpu_prealign_seconds = 0
compare_seconds = 0
digest = b51800fd831dd50fe8ea994e91e8b55c421b36f0c4550328b74316152fbf77cd
```

The trust characterization keeps that external-digest-gated contract clean
through full MALAT1:

```text
record_limit  tasks  realpath_used  fallback  GPU groups  CPU groups  CPU preAlign  GPU total
8             1824   1824           0         31272       0           0s            5.13374s
16            4416   4416           0         77852       0           0s            11.1182s
32            8160   8160           0         144841      0           0s            22.07s
64            18096  18096          0         319280      0           0s            45.1879s
128           40128  40128          0         715473      0           0s            95.0452s
256           80640  80640          0         1434844     0           0s            189.973s
670           200400 200400         0         3561123     0           0s            486.763s
```

This is closer to a true GPU scoreInfo/preAlign replacement because the
candidate run no longer computes CPU `preAlign` scoreInfo for validation. It is
still not production authority: correctness is proven externally by the
baseline/candidate digest gate. The full MALAT1 run records:

```text
digest = 88bb4e98f43c9a48affa082a7e97e881796f161aa4beda02a25dd6a8f7a1891f
baseline Running time = 2631.57s
candidate Running time = 2532.48s
candidate/baseline speedup = 1.039128x
```

The trust prototype gate is:

```bash
make check-fasim-long-query-streaming-scoreinfo-realpath-trust
```

The trust characterization command is:

```bash
make characterize-fasim-long-query-streaming-scoreinfo-realpath-trust
make characterize-fasim-long-query-streaming-scoreinfo-malat1-full-trust
```

### NEAT1 Global-State Boundary

NEAT1 is too long for the shared-memory legacy-byte scoreInfo column kernel:

```text
NEAT1 first4 with FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1:
  query_len = 22767
  stripes = 9
  tasks = 192
  decision = streaming_scoreinfo_shadow_launch_failed
  error = invalid argument
```

The lower-shared-memory legacy-byte global-state scoreInfo path launches and is
correctness-clean, but it is much slower than CPU preAlign on the tested NEAT1
samples:

```text
record_limit  tasks  scoreInfo  GPU hot total  CPU preAlign  speedup
4             192    clean      3.12787s       0.877741s     0.280619x
16            768    clean      12.5232s       3.52635s      0.281585x
```

For NEAT1 first4/first16 global-state:

```text
legacy_byte_shared = 0
scoreinfo_mismatches = 0
candidate_missing = 0
candidate_extra = 0
gpu_minscore_fallbacks = 0
gpu_minscore_score_mismatches = 0
gpu_minscore_min_score_mismatches = 0
```

This means NEAT1 is not a correctness blocker for the streaming scoreInfo
contract, but the current global-state execution shape is a performance no-go.
Do not generalize a real runtime path from the MALAT1 result to NEAT1.

The external-digest-gated trust path reaches the same boundary without
per-task CPU `preAlign` validation:

```text
record_limit  tasks  realpath_used  fallback  GPU groups  CPU groups  CPU preAlign  GPU total
4             192    192            0         3257        0           0s            3.12604s
16            768    768            0         13492       0           0s            12.4996s
32            1536   1536           0         25960       0           0s            25.2269s
64            3072   3072           0         52994       0           0s            50.0708s
```

The first32 and first64 digest-gated runs record whole-run slowdowns:

```text
NEAT1 first32:
  digest = 7584d3531efc14c140f4018ac5b48dc82f1b18412b109e6a0ca376316a7ccb08
  baseline Running time = 42.8368s
  candidate Running time = 61.0602s
  candidate/baseline speedup = 0.701840x

NEAT1 first64:
digest = 5070d390bdffe9d47c4790193a798bba256d6ec81fc8cef3682a7036f403b01f
baseline Running time = 87.1285s
candidate Running time = 123.041s
candidate/baseline speedup = 0.708143x
```

So NEAT1 trust correctness is clean through first64, but performance remains a
hard no-go for the current global-state execution shape.

NEAT1 shared-smem boundary:

```text
query_len = 22,767
legacy-byte segLen = 1,423
required_smem = 136,608
default_smem_limit = 49,152
optin_smem_limit = 101,376
error = legacy_byte_shared_smem_exceeds_optin_limit
```

The shared legacy-byte scoreInfo kernel is now rejected by a preflight when its
dynamic shared-memory requirement exceeds the device opt-in limit, so the
launch is rejected before CUDA returns a generic invalid argument. This is a
resource-shape boundary for the shared kernel, not a scoreInfo correctness
failure. The non-shared legacy-byte path remains correctness-clean but
performance no-go for NEAT1.

### NEAT1 Runtime Boundary

Runtime characterization is distinct from audited replay. The audited replay
wall time includes segmented/full/oracle replay probes and is intentionally
heavier than a trust runtime characterization; do not use audited replay wall
time as real runtime speedup evidence.

The clean runtime boundary remains the digest-gated trust characterization:

```text
NEAT1 first64 runtime trust:
  baseline Running time = 86.0335s
  candidate Running time = 121.948s
  candidate/baseline speedup = 0.705493x
```

The replay audit answers a different question:

```text
NEAT1 first128 audited replay:
  baseline_runner_wall_seconds = 173.527502s
  candidate_runner_wall_seconds = 577.125576s
  replay tasks = 6,144
  replay align attempts = 281,588
  segmented/full/oracle replay mismatches = 0
```

This proves the selected-attempt replay is clean, but replay diagnostic overhead
is expected. It should not be interpreted as the real trust runtime cost.

The NEAT1 trust characterization command is:

```bash
make characterize-fasim-long-query-streaming-scoreinfo-neat1-trust
make characterize-fasim-long-query-streaming-scoreinfo-neat1-first64-trust
```

The fused minScore implementation candidate was tested first:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FUSED_MINSCORE_SHADOW=1
```

It is a no-go boundary: legacy calc-score minScore and byte-profile scoreInfo
are separate contracts, and the naive single-column-max fused prototype is not
correctness-clean. The next allowed direction is a two-contract bridge that
keeps those contracts separate inside one bounded bridge.

The design gates are:

```bash
make check-fasim-long-query-streaming-scoreinfo-fused-minscore-design
make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design
```

## Design

The current exact-column CUDA kernel keeps full-query DP state in per-block
dynamic shared memory:

```text
required_smem = 3 * segLen * 32 * sizeof(int16_t)
```

For MALAT1 first8 this either cannot launch without opt-in or launches with a
scoreInfo mismatch. The next design must stream query stripes instead of
requiring the whole long-query state in one block.

The proposed shadow shape:

```text
1. Build the same CPU preAlign request surface.
2. Pack target windows contiguously.
3. stream query stripes through a lower-shared-memory DP kernel.
4. carry H/E/F boundary state between stripes.
5. emit scoreInfo candidates with global target positions.
6. compare against CPU preAlign scoreInfo.
7. never use GPU candidates for output.
```

The key technical requirement is boundary correctness. Local stripe maxima are
not enough. The kernel must preserve the DP recurrence across stripe boundaries
so the emitted scoreInfo candidates match full-query CPU preAlign, not a union
of tile-local approximations.

## Telemetry

The shadow should report:

```text
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_requested
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_active
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_query_len
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_stripe_len
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_stripes
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cells
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_boundary_state_bytes
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_requested
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_active
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_hot
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_score_mismatches
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_min_score_mismatches
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_scoreinfo_groups
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_scoreinfo_mismatches
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_missing
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_extra
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_pack_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_h2d_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_kernel_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_d2h_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_total_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_cache_hits
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_cache_misses
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_validation_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_validation_minscore_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds
```

## Decision Gate

The design can only continue to implementation if the prototype proves:

```text
scoreinfo_mismatches = 0
candidate_missing = 0
candidate_extra = 0
GPU total < CPU preAlign
output digest unchanged
```

If scoreInfo equality fails, stop and debug the DP boundary state. If GPU total
does not beat CPU preAlign after equality is clean, stop the long-query GPU
scoreInfo path. If equality and performance both pass, the next PR may
characterize MALAT1/NEAT1 samples, still shadow-only.

## Decision

```text
decision = streaming_scoreinfo_design_ready
```

Ready means this is the next allowed design direction. It does not mean a real
runtime path exists.

## Gate

```bash
make check-fasim-long-query-streaming-scoreinfo-design
make check-fasim-long-query-streaming-scoreinfo-shadow-skeleton
BUILD_BIN=0 bash scripts/check_fasim_long_query_streaming_scoreinfo_shadow_active.sh
make check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte
make check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte-shared
```
