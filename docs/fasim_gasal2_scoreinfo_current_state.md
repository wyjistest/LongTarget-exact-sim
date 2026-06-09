# Fasim GASAL2 ScoreInfo Current State

This checkpoint records the current milestone for the scoreInfo/preAlign
GPU/GASAL2 line. It is a milestone, not completion of the full replacement
goal.

The scoped milestone rollup is checked by:

```bash
make check-fasim-gasal2-scoreinfo-scoped-milestone-rollup
```

That rollup ties the top5 release smoke, MALAT1-like scoped scoreInfo release
smoke, state-machine stop gate, completion-gap audit, and full-goal decision
audit into one checkpoint. The full objective remains open.

The MALAT1-like two-contract product boundary is checked by:

```bash
make check-fasim-gasal2-malat1-two-contract-product-readiness
make check-fasim-gasal2-malat1-two-contract-recommended-runtime
```

Those gates define when
`--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32` is a
default-off scoped candidate, and when it must not be recommended.

The broad-path architecture gate is checked by:

```bash
make check-fasim-gasal2-broad-path-architecture-gate
```

That gate requires the next broad prototype to co-design scoreInfo generation
and replacement-consumer behavior. A kernel-only scoreInfo improvement or a
selected-only replay consumer is not enough. The decision is:

```text
decision = broad_path_requires_co_designed_scoreinfo_and_consumer
```

The implementation plan for that next broad-path probe is checked by:

```bash
make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan
make check-fasim-gasal2-broad-scoreinfo-consumer-shadow-env
make check-fasim-gasal2-broad-scoreinfo-consumer-triplex-export
make check-fasim-gasal2-broad-scoreinfo-attempt-planner
make check-fasim-gasal2-broad-replacement-consumer-shadow
make check-fasim-gasal2-broad-neat1-first64-result
```

It is a co-designed scoreInfo plus replacement-consumer shadow plan. It does
not change output authority, and the full objective remains open.

The first broad-path implementation checkpoint now exports a CPU authority
triplex stream for downstream GASAL2/scoreInfo consumer comparison:

```text
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW=1
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_EXPORT_CPU_TRIPLEX=1

NEAT1 first1 smoke:
  decision = cpu_triplex_export_only
  broad_path_active = 0
  broad_path_cpu_triplexes = 60
  broad_path_cpu_triplex_digest = 2d9064122f520fe9
  normal output digest = 8e157aac041d698751fd234ba88bce9226cd900aec48ab0aa1c27ce4cbbfe437
```

CPU authority triplex export is a scaffold, not broad replacement. It does not
activate a GASAL2 consumer and does not use GPU scoreInfo, endpoint, CIGAR, or
traceback output as authority.

The second broad-path implementation checkpoint now exports a scoreInfo attempt
descriptor plan from the validated streaming GPU scoreInfo feed:

```text
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW=1
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_EXPORT_CPU_TRIPLEX=1
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_PLANNER=1

NEAT1 first1 smoke:
  decision = planner_descriptors_only
  broad_path_active = 0
  broad_path_tasks = 48
  broad_path_scoreinfo_groups = 718
  broad_path_align_attempts = 3,590
  selected_attempts = 0
  broad_path_planner_descriptor_digest = 30870fb1cfea2aea
  normal output digest = 8e157aac041d698751fd234ba88bce9226cd900aec48ab0aa1c27ce4cbbfe437
```

Planner descriptors exist, but no broad replacement consumer is active. The
zero selected-attempt count means this checkpoint is descriptor/planner
plumbing only; the next required step is a stateful consumer shadow that
preserves legacy scoreInfo-local break/best-end semantics.

The third broad-path implementation checkpoint now activates a CPU-backed
replacement-consumer shadow using the existing full-replay scoreInfo state
machine:

```text
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW=1
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_EXPORT_CPU_TRIPLEX=1
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_PLANNER=1
FASIM_GASAL2_BROAD_REPLACEMENT_CONSUMER_SHADOW=1

NEAT1 first1 smoke:
  decision = replacement_consumer_shadow_active
  broad_path_active = 1
  broad_path_tasks = 48
  broad_path_scoreinfo_groups = 718
  broad_path_align_attempts = 3,590
  broad_path_triplex_mismatches = 0
  broad_path_missing_triplexes = 0
  broad_path_extra_triplexes = 0
  normal output digest = 8e157aac041d698751fd234ba88bce9226cd900aec48ab0aa1c27ce4cbbfe437
```

This proves the replacement-consumer state shadow can reproduce the checked
CPU authority task triplex stream for NEAT1 first1. It remains a diagnostic
consumer-shadow checkpoint: GPU/GASAL2 endpoint, CIGAR, traceback, output, and
digest are still not authority, and no production real path is enabled.

The NEAT1 first64 broad characterization is the current broad-path stop
checkpoint:

```text
decision = broad_path_current_architecture_no_go
digest clean
broad_path_active = 1
broad_path_tasks = 3,058
broad_path_scoreinfo_groups = 52,994
broad_path_align_attempts = 264,970
broad_path_triplex_mismatches = 0
broad_path_missing_triplexes = 0
broad_path_extra_triplexes = 0
baseline_wall_seconds = 86.932816
candidate_wall_seconds = 288.4177
candidate_vs_baseline = 0.301413x
broad_path_scoreinfo_seconds = 19.1704
broad_path_consumer_seconds = 52.0465
baseline_cpu_reference_seconds = 52.0833
realpath_extend_align_attempts = 140,087
```

The current broad state-machine consumer is correctness-clean on this gate, but
it is not a performance candidate. It increases total wall time, does not beat
the CPU reference scoreInfo/consumer time, and does not reduce extend/align
attempts. The current architecture should not proceed to a real path.

The full objective remains open.

## Milestone Decision

Current short-query/H19 GASAL2 top5 scoreInfo/preAlign: go as a top5-only
artifact path.

MEG3 tiny-region grouped runner/wrapper path: go for the same top5-only
artifact contract.

Long-query MALAT1 has a MALAT1-like, group32, external-digest-gated scoped
trust profile. Long-query NEAT1 remains performance no-go. This is not a broad
long-query real path, and the current best remains marginal.

GASAL2 / GPU scoreInfo scoped feasibility checkpoint:

```text
MALAT1 streaming scoreInfo trust path: scoped go
NEAT1 streaming scoreInfo trust path: performance no-go
MALAT1 selected-attempt replay reduction: no-go for current selector
Broad scoreInfo/preAlign replacement: not proven
```

The formal preset is top5-only contract:

```text
--gasal2-top5-column-pruned-scoreinfo
```

The formal preset expands to the managed active stack:

```text
FASIM_TOP5_GASAL2_GPU_SCOREINFO=1
FASIM_TOP5_GASAL2_PHASE_TIMING=1
FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1
FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=64
FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE=1
FASIM_PREALIGN_CUDA_MAX_TASKS=16384
FASIM_EXACT_COLUMN_SCOREINFO_GPU=1
FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=512
FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1
FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=1
FASIM_OUTPUT_TOPK_LITE=5
```

## Short-Query Evidence

chr21+chr22 formal result:

```text
decision = top5_artifact_go
active_path_runs = 1/1
top5_clean_runs = 1/1
formal FASIM_PREALIGN_CUDA_MAX_TASKS = 16384
exact scoreInfo GPU batches = 49
exact scoreInfo GPU tasks = 778,848
GASAL2 requests = 43,637,966
GASAL2 traceback requests = 13,701,121
fallback/overflow = 0 / 0
CPU worker wall sum = 4565.987188s
formal worker wall sum = 113.810705s
speedup = 40.119136x
```

This proves active GASAL2 scoreInfo/preAlign use for the checked top5 artifact
payload. It does not prove full lite-output equivalence.

## Grouped Tiny-Region Evidence

MEG3 grouped result:

```text
target records = 532
--group-target-records 32
group_target_records = 32
grouped_shard_count = 17
decision = top5_artifact_go
active_path_runs = 1/1
top5_clean_runs = 1/1
fallback/overflow = 0 / 0
CPU worker wall sum = 50.592440s
formal worker wall sum = 26.088332s
speedup = 1.939275x
GASAL2 requests = 1,034,708
GASAL2 traceback requests = 393,847
exact scoreInfo tasks = 25,536
```

The wrapper path also records:

```text
group_target_records = 32
grouped_shard_count = 17
activation_verified = true
gasal2_requests = 1,034,708
gasal2_traceback_requests = 393,847
exact_scoreinfo_gpu_tasks = 25,536
gasal2_fallbacks = 0
topk_lite_records = 15
```

This is a short-query/H19 GASAL2 top5 scoreInfo/preAlign artifact path with
complete-record grouping. It is not chunking, not overlap, and not a C++ runtime
semantic change.

## Long-Query Boundary

The current formal path is bounded by:

```text
GASAL2_MAX_QUERY_LEN=2812
FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812
MEG3 query_len=1582
MALAT1 query_len=8708
NEAT1 query_len=22767
```

MALAT1/NEAT1 are long-query guarded CPU fallback cases for the formal preset.
They can be top5-clean through CPU fallback, but they are not GASAL2-active
successes.

GASAL2 selected/expanded segment traceback: no-go for real path

```text
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_SEGMENT_TRACEBACK_SHADOW=1
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_EXPANDED_SEGMENT_TRACEBACK_SHADOW=1

selected-segment traceback is not equivalent
expanded_segment_traceback_shadow_required_max_len = 22,767
expanded_segment_traceback_shadow_required_over_gasal2_limit = 21,991
full-query traceback requirement for many attempts
```

The expanded-segment oracle is clean only when it effectively covers the full
NEAT1 query interval. That is far above the current GASAL2 2,812 bp query guard,
so it does not create a practical GASAL2 traceback replacement path.

The long-query no-last scaling artifact records the current best as marginal
across first8/first16/first32/first64/first128:

```text
malat1_first8 speedup=1.009996x
malat1_first16 speedup=1.029101x
malat1_first32 speedup=1.031832x
malat1_first64 speedup=1.034623x
malat1_first128 speedup=1.038017x
1.0 < speedup < 1.1
```

That is diagnostic only. It is not enough to justify long-query production
output.

The current long-query implementation stop checkpoint records:

```text
current segmented no-last replay line: stopped for real path
```

It is checked by:

```bash
make check-fasim-gasal2-long-query-current-stop
```

The focused MALAT1-like scoreInfo scoped release smoke is:

```bash
make check-fasim-gasal2-scoreinfo-scoped-release-smoke
```

It reruns the first8 no-probe lite and TFOsorted gates for the grouped
two-contract runtime, then rechecks the scoped-milestone, completion-gap, and
full-goal-decision static boundaries. It is not a universal replacement smoke.

The MALAT1 two-contract group32 replay diagnostics now split the replay surface
into three passive checks:

```text
expanded selected-scoreInfo replay:
  triplex_mismatches = 0
  align_attempts = 74,646

direct selected-only replay:
  triplex_mismatches = 1,174
  reason = over-emission; violates scoreInfo-level single-emission semantics

grouped selected-prefix replay:
  triplex_mismatches = 0
  align_attempts = 74,646
```

The attempted grouped-selected reduction first reduced align attempts to about
54,961 but left one same-count content mismatch. Provenance showed the mismatch
within the same scoreInfo:

```text
selected:
  scoreinfo=511; start=2166; cutlength=34; sw_score=52

legacy:
  scoreinfo=511; start=2153; cutlength=47; sw_score=55
```

Replaying the selected scoreInfo prefix restores correctness, but it also
restores the expanded replay align count. Therefore the current GASAL2 selected
attempts can be used as a diagnostic boundary, not as a CPU-align reduction
candidate.

The next allowed implementation plan is checked by:

```bash
make check-fasim-gasal2-long-query-next-architecture-plan
```

The first exact-tile next-architecture milestone is the long-query exact-tile
CPU oracle export. It keeps CPU fallback as authority, does not activate tile
implementation, and verifies that exporting the CPU scoreInfo candidate surface
does not change the lite output digest:

```text
long-query exact-tile CPU oracle export:
  requested = 1
  active = 0
  MALAT1 query_len = 8708
  tile_len = 2812
  tiles = 4
  cpu_oracle_candidates = 31,272
  output digest unchanged
```

It is checked by:

```bash
make check-fasim-gasal2-long-query-exact-tile-oracle-export
```

The second exact-tile next-architecture milestone is the long-query exact-tile
descriptor generator. It deterministically describes the query tiles that fit
the current GASAL2 query bound without changing output or activating a tile
implementation:

```text
long-query exact-tile descriptor generator:
  requested = 1
  active = 0
  MALAT1 query_len = 8708
  tile_len = 2812
  tile_descriptors = 4
  tile_max_query_len = 2812
  tile_descriptor_digest = 16919590609729549896
  output digest unchanged
```

It is checked by:

```bash
make check-fasim-gasal2-long-query-exact-tile-descriptors
```

The candidate-equivalence probe for this same non-overlap exact-tile shape is a
no-go:

```text
long-query exact-tile candidate equivalence: no-go
  cpu_oracle_candidates = 31272
  tile_candidates = 31591
  candidate_missing = 1720
  candidate_extra = 2039
  fallback = 0
  output digest unchanged
```

This means the current non-overlap exact-tile shape is not a valid long-query
scoreInfo/preAlign replacement. CPU fallback remains authority.

It is checked by:

```bash
make check-fasim-gasal2-long-query-exact-tile-candidate-equivalence-result
```

The overlap probe for exact-tile candidate equivalence is also a no-go:

```text
long-query exact-tile overlap probe: no-go
  overlap = 1406:
    tile_candidates = 33862
    candidate_missing = 1
    candidate_extra = 2591
    position_missing = 1
    position_extra = 2397
    position_score_mismatches = 0

  overlap = 2048:
    tile_candidates = 34232
    candidate_missing = 1
    candidate_extra = 2961
    position_missing = 1
    position_extra = 2644
    position_score_mismatches = 0
```

This means overlap reduces missing candidates but does not make simple tile
candidate union exact. Larger overlap increases extra candidates. The mismatch
is not a score remapping issue; tile-local DP creates positions absent from the
full-query CPU oracle.

It is checked by:

```bash
make check-fasim-gasal2-long-query-exact-tile-overlap-result
```

The isolated full-query exact-column scoreInfo shadow bypasses the failing
preAlign CUDA topK launch precondition, but the current full-query column kernel
still does not launch for MALAT1 length:

```text
long-query exact-column scoreInfo shadow: launch no-go
  query_len = 8708
  gpu_batches = 1
  active = 0
  error = invalid argument
  output digest unchanged
```

This means the earlier topK failure was not the only blocker. The current
full-query exact-column CUDA scoreInfo execution shape is also not a valid
MALAT1/NEAT1 replacement path.

It is checked by:

```bash
make check-fasim-long-query-exact-column-scoreinfo-shadow
```

The shared-memory opt-in variant confirms that the MALAT1 first8 resource shape
can launch when the kernel opts into the larger per-block dynamic shared-memory
limit, but the scoreInfo surface is not equivalent:

```text
long-query exact-column scoreInfo shadow smem opt-in: no-go
  query_len = 8708
  required_smem = 52416
  default_smem_limit = 49152
  optin_smem_limit = 101376
  resource_fit = 1
  smem_optin_active = 1
  gpu_tasks = 432
  scoreinfo_mismatches = 1
  output digest unchanged
```

This means shared-memory opt-in is only a diagnostic probe. It is not a
correctness-clean long-query scoreInfo/preAlign path.

It is checked by:

```bash
make check-fasim-long-query-exact-column-scoreinfo-shadow-smem-optin
```

## Single-Pass TopN Boundary

The single-pass topN scoreInfo probe answered whether the first DP pass can
directly produce the scoreInfo candidates:

```text
single-pass topN:
  legacy_score_gpu_requests = 0
  exact_scoreinfo_gpu_batches = 0
  topN=64 changes the nt-score top5
  topN=128/256 also change stability
```

This means the first pass can produce bounded topN scoreInfo-like candidates,
but it does not currently produce exact legacy scoreInfo and it is not top5-safe
for the current artifact contract. FASIM_TOP5_GASAL2_SINGLE_PASS_TOPN=1 is not
recommended as a runtime path.

## Forbidden Claims

This milestone does not establish:

```text
not full lite-output equivalence
not full Fasim replacement
not `aligner.Align()` replacement
not GPU endpoint/CIGAR/traceback authority
not long-query production output
not universal scoreInfo/preAlign replacement
```

Any broader claim must add fresh evidence over the relevant full scope. Narrow
top5 artifact checks cannot support a full-output or full-aligner claim.

## Gate

The composed current-state gate is:

```bash
make check-fasim-gasal2-scoreinfo-current-state
```

It requires:

```bash
make check-fasim-gasal2-formal-makefile-gate
make check-fasim-gasal2-top5-scoreinfo-milestone
make check-fasim-gasal2-top5-scoreinfo-milestone-result
make check-fasim-gasal2-top5-scoreinfo-meg3-grouped-result
make check-fasim-gasal2-top5-wrapper-meg3-grouped-result
make check-fasim-sharded-gasal2-top5-prune-runner
make check-fasim-gasal2-column-pruned-preset-top5-matrix
make check-fasim-gasal2-top5-output-contract
make check-fasim-gasal2-top5-activation-contract
make check-fasim-gasal2-topk-lite-wrapper-contract
make check-fasim-gasal2-top5-lowercase-input
make check-fasim-gasal2-top5-binary-guard
make check-fasim-gasal2-formal-preset-examples
make check-fasim-top5-gasal2-gpu-scoreinfo-default-off
make check-fasim-top5-gasal2-gpu-scoreinfo-env
make check-fasim-exact-scoreinfo-gpu-examples-gate
make check-fasim-gasal2-long-query-boundary
make check-fasim-gasal2-long-query-segmented-no-last-scaling-result
make check-fasim-gasal2-long-query-current-stop
make check-fasim-gasal2-long-query-next-architecture-plan
make check-fasim-gasal2-long-query-next-architecture-decision
make check-fasim-long-query-streaming-scoreinfo-design
make check-fasim-long-query-streaming-scoreinfo-shadow-skeleton
make check-fasim-long-query-streaming-scoreinfo-shadow-active
make check-fasim-long-query-streaming-scoreinfo-shadow-mismatch-detail
make check-fasim-gasal2-long-query-exact-tile-oracle-export
make check-fasim-gasal2-long-query-exact-tile-descriptors
make check-fasim-gasal2-long-query-exact-tile-candidate-equivalence-result
make check-fasim-gasal2-long-query-exact-tile-overlap-result
make check-fasim-long-query-exact-column-scoreinfo-shadow
make check-fasim-long-query-exact-column-scoreinfo-shadow-smem-optin
make check-fasim-gasal2-single-pass-topn-sweep
make check-fasim-gasal2-top5-broader-validation
make check-fasim-gasal2-top5-product-readiness
make check-fasim-gasal2-top5-recommended-runtime
make check-fasim-gasal2-scoreinfo-scoped-milestone
make check-fasim-gasal2-scoreinfo-completion-gap
make check-fasim-gasal2-full-goal-decision
make check-fasim-lite-full-equivalence
```

The expected conclusion is:

```text
short-query/H19 top5 scoreInfo/preAlign: milestone go
MEG3 grouped top5 wrapper: milestone go
lower-shared-memory streaming scoreInfo design: checkpointed but not broad completion
long-query current best is marginal
long-query MALAT1/NEAT1: no real path
decision = next_architecture_no_go
post-selected-replay status = scoped milestone, not completion
next universal path = accepted top5-only contract, full-output/TFO equivalence proof, or different long-query execution design
streaming_scoreinfo_shadow_not_implemented
MALAT1 first8 query_len = 8708
task/cell accounting is positive
not a streaming GPU implementation yet
streaming_scoreinfo_shadow_mismatch
low-shared-memory/global-state shadow launches for all MALAT1 first8 tasks
scoreinfo_mismatches = 1
first_mismatch task=130 global=130 diff=0
cpu scoreInfo = 228@465
gpu scoreInfo = 228@463
scalar SW matches GPU, not CPU SSW preAlign
root cause = legacy SSW byte-profile/bias/saturation compatibility
full replacement goal: still open
```

The streaming mismatch is now localized rather than unknown:

```text
column window:
  CPU SSW preAlign = 461:217,462:220,463:225,464:223,465:228,466:224,467:220,468:216,469:212
  GPU streaming   = 461:218,462:223,463:228,464:224,465:228,466:224,467:220,468:216,469:212
  scalar SW       = 461:218,462:223,463:228,464:224,465:228,466:224,467:220,468:216,469:212
```

So the current long-query blocker is not scoreInfo compact grouping or top5
tie-policy. The current GPU streaming kernel computes exact/scalar
Smith-Waterman for this window, but `aligner.preAlign` authority is the legacy
SSW byte path. A real long-query scoreInfo/preAlign replacement needs a
legacy-byte-compatible CUDA path or an authority change, not more exact 16-bit
streaming DP.

NEAT1 runtime boundary:

```text
NEAT1 first64 trust runtime:
  candidate/baseline speedup = 0.705493x

NEAT1 first128 audited replay:
  candidate/baseline speedup = 0.300675x
  segmented/full/oracle replay mismatches = 0
```

do not use audited replay wall time as real runtime speedup evidence. The audit
includes segmented/full/oracle replay probes and is a correctness diagnostic,
while the first64 trust characterization is the clean runtime no-go signal.

The next long-query implementation candidate is fused minScore:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FUSED_MINSCORE_SHADOW=1
```

It targets the current two-pass GPU DP cost by deriving full score, minScore,
and scoreInfo candidates from one column-max pass. The first default-off
prototype now exists, but it is a no-go boundary, not a real opt-in and not a
broad scoreInfo/preAlign replacement:

```text
MALAT1 first8 fused boundary:
  tasks = 1824
  fused_minscore_active = 1
  fused_minscore_score_mismatches = 97
  fused_minscore_min_score_mismatches = 97
  scoreinfo_mismatches = 92
  digest unchanged because GPU remains shadow-only
  decision = streaming_scoreinfo_shadow_mismatch
```

The root cause is that legacy calc-score minScore and byte-profile scoreInfo are
not the same column-max contract. A naive fused single-pass implementation
cannot be promoted.

The next allowed direction is now a two-contract bridge scaffold: keep legacy
calc-score minScore and byte-profile scoreInfo separate, but package them in one
bounded shadow entry point to reduce host-side orchestration. It is still
default-off and CPU output remains authority.

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1
two_contract_bridge_shadow_active
```

The first trust prototype is also available, still default-off and
external-digest-gated:

```text
--long-query-streaming-scoreinfo-gpu-two-contract-trust
result_contract = long_query_streaming_scoreinfo_gpu_two_contract_trust_experimental_v1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1
two_contract_bridge_trust_active
realpath_digest_authority = external_digest_gate
cpu_scoreinfo_groups = 0
cpu_prealign_seconds = 0
```

```bash
make check-fasim-long-query-streaming-scoreinfo-fused-minscore-design
make check-fasim-long-query-streaming-scoreinfo-fused-minscore-prototype
make check-fasim-long-query-streaming-scoreinfo-fused-minscore-boundary
make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design
make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-shadow
make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-trust
make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-runner
```

The legacy-byte streaming shadow closes that MALAT1 first8 correctness gap:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1
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

The compatibility requirement was not ordinary scalar Smith-Waterman. It needed
the legacy SSW byte-profile layout and Lazy-F semantics:

```text
16-byte striped query profile
unsigned saturating byte arithmetic
SSE2 Lazy-F signed byte compare
16-pass Lazy-F bound
```

This is a long-query scoreInfo correctness milestone, but not a real path:

```text
GPU total ~= 12.54s
CPU preAlign reference ~= 4.95s
legacy-byte streaming shadow: correctness clean, performance no-go
```

It is checked by:

```bash
make check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte
```

The shared-memory legacy-byte probe keeps that correctness result and reduces
kernel cost:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1
legacy_byte_shared = 1
scoreinfo_mismatches = 0
candidate_missing = 0
candidate_extra = 0
GPU total ~= 9.96s
kernel ~= 3.61s
```

It is still slower than CPU preAlign on MALAT1 first8, so it remains a
diagnostic/performance-shaping probe, not a real scoreInfo/preAlign path.
The current telemetry explicitly splits shadow-only overhead from the CUDA data
path:

```text
minscore_seconds:
  shadow calc_score_once() threshold recomputation

minscore_cache_hits / minscore_cache_misses:
  whether the shadow reused an existing StreamTask minScore or had to compute it
  before the GPU call

gpu_call_seconds:
  CUDA scoreInfo wall time

validation_seconds:
  CPU authority replay plus prune/compare work

cpu_prealign_seconds:
  CPU preAlign authority replay

compare_seconds:
  scoreInfo prune/equality bookkeeping
```

The default-off GPU minScore source probe now uses a lower-shared-memory
global-state legacy max-score kernel. On MALAT1 first8 it is clean against
`calc_score_once()`:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1
gpu_minscore_requested = 1
gpu_minscore_active = 1
gpu_minscore_used = 1824
gpu_minscore_fallbacks = 0
gpu_minscore_score_mismatches = 0
gpu_minscore_min_score_mismatches = 0
gpu_minscore_error = none
```

The remaining gap is no longer minScore correctness. It is turning the clean
GPU minScore source plus clean GPU scoreInfo source into a default-off
production-style shadow that does not spend the hot path on CPU
`calc_score_once()`, while keeping CPU validation/fallback. In other words,
the next prototype needs to skip CPU minScore authority on the hot path.

The production-style hot-path probe is covered by:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1
gpu_minscore_hot = 1
gpu_minscore_used = tasks
gpu_minscore_fallbacks = 0
gpu_minscore_score_mismatches = 0
gpu_minscore_min_score_mismatches = 0
minscore_seconds <= 0.05
validation_minscore_seconds > 0
```

Larger MALAT1 samples make this a real milestone, but not a production-ready
replacement:

```text
MALAT1 first64 hot-path checkpoint:
  gpu_hot_total_seconds = 45.5043
  cpu_prealign_seconds = 50.3037
  hot_path_speedup = 1.105477x
  scoreInfo correctness stays clean through first64
  performance is marginal, not production-ready
```

The first16/first32/first64 hot-path runs are all digest-clean and scoreInfo
clean with no GPU minScore fallback. The result supports continued
characterization and a validation-first default-off prototype design, not a
direct production replacement.

The first actual default-off scoreInfo/preAlign replacement prototype is:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE=1

MALAT1 first8:
  realpath_requested = 1
  realpath_used = 1824
  realpath_fallbacks = 0
  realpath_digest_authority = cpu_validated
  digest clean
```

This path feeds CPU-validated GPU streaming scoreInfo into CPU
`fastSIM_extend_from_scoreinfo()`. It does not use GASAL2 long-query traceback.
That distinction matters because forcing GASAL2 traceback at MALAT1 query_len
8708 produced a CUDA illegal-memory-access failure in GASAL2.

The real-path prototype now has a MALAT1 first8/first16/first32/first64
characterization. In every checked row, `realpath_used = tasks`, realpath
fallback is zero, GPU minScore fallback is zero, and scoreInfo comparison is
clean:

```text
record_limit  tasks  realpath_used  fallback  scoreInfo  GPU total  CPU preAlign  cpu/GPU
8             1824   1824           0         clean      5.21243s   4.95148s      0.949937x
16            4416   4416           0         clean      11.2673s   12.2928s      1.091016x
32            8160   8160           0         clean      22.264s    22.6416s      1.016960x
64            18096  18096          0         clean      45.4425s   50.2407s      1.105588x
```

This extends the milestone from a first8 smoke to a MALAT1 first64
validation-first prototype. It is still marginal and validation-heavy, not a
production runtime path.

The next default-off trust prototype removes per-task CPU `preAlign` validation
from the candidate run:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST=1

MALAT1 first8:
  realpath_requested = 1
  realpath_trust = 1
  realpath_used = 1824
  realpath_fallbacks = 0
  realpath_digest_authority = external_digest_gate
  cpu_scoreinfo_groups = 0
  cpu_prealign_seconds = 0
  compare_seconds = 0
  digest clean
```

The trust characterization extends that result through full MALAT1:

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

This is the first checked candidate run where GPU scoreInfo replaces CPU
`preAlign` scoreInfo without also replaying CPU `preAlign` for per-task
validation. The full MALAT1 run is digest-clean with:

```text
digest = 88bb4e98f43c9a48affa082a7e97e881796f161aa4beda02a25dd6a8f7a1891f
baseline Running time = 2631.57s
candidate Running time = 2532.48s
candidate/baseline speedup = 1.039128x
```

It is still external-digest-gated and only checked on MALAT1, so it is not
production authority for broader long-query workloads.

The public runner option has a separate bounded MALAT1 matrix. It preserves the
merged digest and records `result_contract =
long_query_streaming_scoreinfo_gpu_trust_experimental_v1` through first64, with
`realpath_used = tasks`, no fallback, and no candidate CPU `preAlign`/compare
validation:

```text
record_limit  tasks  realpath_used  fallback  GPU groups  CPU preAlign  runner speedup
8             1824   1824           0         31272       0s            0.914539x
16            4416   4416           0         77852       0s            0.957250x
32            8160   8160           0         144841      0s            0.934600x
64            18096  18096          0         319280      0s            0.953067x
```

That runner control surface is correctness-useful, but it is not a bounded
runner performance win.

Increasing process-level workers does not fix that for the current trust
implementation. MALAT1 first64 remains digest-clean, but the candidate slows
relative to the baseline as workers increase:

```text
workers  tasks  realpath_used  fallback  GPU groups  GPU total  runner speedup
1        18096  18096          0         319280      44.999s    0.956003x
2        18096  18096          0         319280      62.025s    0.912482x
4        18096  18096          0         319280      79.532s    0.843978x
```

This points to GPU setup/launch/contention overhead in the current per-shard
trust runner shape. More workers alone are not a route to the requested broad
scoreInfo/preAlign replacement.

Complete-record grouping is a better fit for that overhead problem. On MALAT1
first64, grouping preserves the digest and turns the bounded runner comparison
from slightly slower to slightly faster:

```text
group  shards  tasks  realpath_used  fallback  GPU total  runner speedup
null   64      18096  18096          0         45.404s    0.952645x
2      32      18096  18096          0         45.346s    0.989676x
4      16      18096  18096          0         44.835s    1.011415x
8      8       18096  18096          0         44.811s    1.022417x
16     4       18096  18096          0         45.003s    1.028119x
32     2       18096  18096          0         45.114s    1.028873x
```

This is still a scoped MALAT1 signal, not a broad scoreInfo/preAlign
replacement. It supports the next engineering direction: amortize GPU setup and
launch across larger batches or grouped shards.

Group32 scaling keeps the same external-digest-gated contract clean through
MALAT1 first256:

```text
record_limit  shards  tasks  realpath_used  fallback  GPU total  runner speedup
64            2       18096  18096          0         45.115s    1.029346x
128           4       40128  40128          0         94.845s    1.041244x
256           8       80640  80640          0         190.212s   1.040806x
```

The first256 row uses GPU scoreInfo for 80,640 tasks and 1,434,844 scoreInfo
groups with no candidate CPU `preAlign` or compare pass. The speedup is real
but small, so this remains a scoped MALAT1-like grouped path.

The two-contract group32 audited wrapper now has a real first256 gate:

```text
MALAT1 two-contract group32 audited first256:
  digest = 7f553b74ae31bed4cb7b9c312a188e2df19627ac4882c7ad7ac484d65b004a4e
  tasks = 80,640
  two_contract_used = 80,640
  realpath_used = 80,640
  two_contract_fallbacks = 0
  two_contract_score_mismatches = 0
  two_contract_min_score_mismatches = 0
  two_contract_scoreinfo_mismatches = 0
  realpath_fallbacks = 0
  gpu_scoreinfo_groups = 1,434,844
  baseline runner wall = 1058.944629s
  candidate runner wall = 1015.698961s
  candidate_vs_baseline = 1.042577x
  resume_audited = true
```

It is checked by:

```bash
make check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256
```

This is stronger than a raw characterization row because it is fail-closed:
baseline and candidate digests must match, every task must use the two-contract
real path, fallback/mismatch counters must remain zero, and resume must replay
from an accepted audit summary.

The no-probe two-contract runtime gate separates clean runtime evidence from
the audited replay/attempt diagnostics:

```bash
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted
```

That gate runs the same grouped MALAT1-like two-contract bridge through
`--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32`, rejects any
probe env leakage, and requires `probe_positive_numeric_keys=0`.

```text
result_contract = long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32_experimental_v1
long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_two_contract_runtime_group32_experimental_v1
```

```text
MALAT1 first8 no-probe:
  schema = lite
  rows = 796
  candidate_vs_baseline = 0.990695x
  tasks = 1,824
  two_contract_used = 1,824
  realpath_used = 1,824
  probe_positive_numeric_keys = 0

MALAT1 first8 TFOsorted no-probe:
  schema = tfosorted
  rows = 796
  candidate_vs_baseline = 0.990699x
  tasks = 1,824
  two_contract_used = 1,824
  realpath_used = 1,824
  probe_positive_numeric_keys = 0

MALAT1 first64 no-probe:
  schema = lite
  rows = 9,741
  candidate_vs_baseline = 1.030868x
  tasks = 18,096
  two_contract_used = 18,096
  realpath_used = 18,096
  gpu_scoreinfo_groups = 319,280
  probe_positive_numeric_keys = 0

MALAT1 first128 no-probe:
  schema = lite
  rows = 22,531
  candidate_vs_baseline = 1.043793x
  tasks = 40,128
  two_contract_used = 40,128
  realpath_used = 40,128
  gpu_scoreinfo_groups = 715,473
  probe_positive_numeric_keys = 0

MALAT1 first256 no-probe:
  schema = lite
  rows = 42,504
  candidate_vs_baseline = 1.042764x
  tasks = 80,640
  two_contract_used = 80,640
  realpath_used = 80,640
  gpu_scoreinfo_groups = 1,434,844
  probe_positive_numeric_keys = 0

MALAT1 full no-probe:
  schema = lite
  rows = 98,713
  digest = f080498ad8b9661100243e8eec89b6b54b566d7ed96fa5db7e268a8ce8513e0b
  baseline_wall_seconds = 2616.446186
  candidate_wall_seconds = 2521.276554
  candidate_vs_baseline = 1.037747x
  tasks = 200,400
  two_contract_used = 200,400
  realpath_used = 200,400
  gpu_minscore_used = 200,400
  gpu_scoreinfo_groups = 3,561,123
  two_contract_total_seconds = 486.853900
  gpu_minscore_wall_seconds = 159.007290
  realpath_extend_seconds = 1143.153600
  realpath_extend_align_seconds = 1137.801300
  probe_positive_numeric_keys = 0

MALAT1 full TFOsorted no-probe:
  schema = tfosorted
  rows = 98,713
  digest = ac667f460cd1446bc5598fa163f7fc2755265bf56e6b82c105e672873c895ffc
  baseline_wall_seconds = 2640.948210
  candidate_wall_seconds = 2545.271840
  candidate_vs_baseline = 1.037590x
  tasks = 200,400
  two_contract_used = 200,400
  realpath_used = 200,400
  gpu_minscore_used = 200,400
  gpu_scoreinfo_groups = 3,561,123
  two_contract_total_seconds = 486.866600
  gpu_minscore_wall_seconds = 159.077360
  realpath_extend_seconds = 1165.680900
  realpath_extend_align_seconds = 1139.782800
  probe_positive_numeric_keys = 0
```

This makes the two-contract group32 path a scoped milestone with repeatable
no-probe evidence. The speedup is still small and workload-specific, so it does
not close the broad scoreInfo/preAlign replacement goal.

### Full-MALAT1 Milestone Decision

```text
scoped full-MALAT1 no-probe runtime go:
  yes

not broad scoreInfo/preAlign replacement:
  yes

remaining bottleneck is CPU realpath extend/align:
  realpath_extend_seconds = 1143.153600
  realpath_extend_align_seconds = 1137.801300
  realpath_extend_align_attempts = 8,526,477

GPU scoreInfo path:
  two_contract_total_seconds = 486.853900
  two_contract_kernel_seconds = 486.154600
  gpu_minscore_wall_seconds = 159.007290
```

The full-MALAT1 gate proves the no-probe contract for this workload shape, not
universal scoreInfo/preAlign replacement. The remaining wall-time limiter is not
only GASAL2 scoreInfo; CPU realpath extend/align still dominates a large part of
the candidate run.

Full-MALAT1 TFOsorted equivalence is now also checked as a correctness gate:

```text
MALAT1 full TFOsorted:
  schema = tfosorted
  baseline_rows = 98,713
  candidate_rows = 98,713
  baseline_full_digest = ff415800b5cbc226f979eb85c7a93387b6e07f1e17dc279342a594dd6b76bdca
  candidate_full_digest = ff415800b5cbc226f979eb85c7a93387b6e07f1e17dc279342a594dd6b76bdca
  missing_rows = 0
  extra_rows = 0
  full_rows_equal = true
  tasks = 200,400
  two_contract_used = 200,400
  realpath_used = 200,400
  candidate_vs_baseline = 0.403059x
  decision = full-output correctness proof, not runtime claim
```

The full MALAT1 grouped runner result keeps the same contract:

```text
record_limit = 670
group_target_records = 32
shards = 21
tasks = 200,400
realpath_used = 200,400
fallback = 0
gpu_scoreinfo_groups = 3,561,123
cpu_scoreinfo_groups = 0
cpu_prealign_seconds = 0
gpu_total_seconds = 482.3484
baseline runner wall = 2634.969799s
candidate runner wall = 2541.655441s
runner speedup = 1.036714x
digest = f080498ad8b9661100243e8eec89b6b54b566d7ed96fa5db7e268a8ce8513e0b
```

This makes the current MALAT1-like recommended experimental profile:
`--long-query-streaming-scoreinfo-gpu-trust-group32`.

```text
result_contract = long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1
long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_group32_experimental_v1
```

The preset is equivalent to `--long-query-streaming-scoreinfo-gpu-trust
--group-target-records 32`. It is still default-off and external-digest-gated.
It should not be generalized to NEAT1 or broad long-query scoreInfo
replacement.
The group32 scaling and full-MALAT1 characterization wrappers exercise the
preset contract directly and emit the `malat1_like_group32_experimental_v1`
profile in their summaries.

The fail-closed audited entry point is
`run_fasim_long_query_streaming_scoreinfo_trust_group32_audited.sh`. It runs a
CPU-authority `--group-target-records 32` baseline plus the
`--long-query-streaming-scoreinfo-gpu-trust-group32` candidate and emits
`audited_status = accepted` only after the external digest gate and scoreInfo
coverage checks pass. A digest mismatch exits non-zero with
`digest gate failed`.
`--resume` requires an existing accepted audit summary, forwards resume to both
underlying runner invocations, and records `audited_resume = true` with
`resumed_shards` counts. It also records `baseline_runner_wall_seconds`,
`candidate_runner_wall_seconds`, and `candidate_vs_baseline` for the audited
runner wall comparison. The same summary records
`candidate_gpu_scoreinfo_total_seconds`, `candidate_gpu_scoreinfo_call_seconds`,
`candidate_gpu_scoreinfo_kernel_seconds`, `candidate_non_gpu_wall_seconds`,
`candidate_gpu_scoreinfo_wall_fraction`, and
`candidate_gpu_scoreinfo_call_fraction`, which makes the current bottleneck
explicit: an accepted run can be digest-clean while most candidate wall time is
still outside the GPU scoreInfo kernels. The audit summary also records
`candidate_realpath_extend_seconds`, `candidate_realpath_extend_calls`, and
`candidate_realpath_extend_fraction` for the CPU
`fastSIM_extend_from_scoreinfo()` consumption of trusted GPU scoreInfo. That
extend accounting now includes `candidate_realpath_extend_scoreinfo_groups`,
`candidate_realpath_extend_align_attempts`,
`candidate_realpath_extend_substr_seconds`,
`candidate_realpath_extend_align_seconds`,
`candidate_realpath_extend_align_fraction`,
`candidate_realpath_extend_convert_seconds`,
`candidate_realpath_extend_sort_seconds`, and
`candidate_realpath_extend_filter_seconds`, which makes the next bottleneck
visible at the trusted-scoreInfo consumption boundary. The audit summary also
records `candidate_realpath_extend_attempt_probe_requested`,
`candidate_realpath_extend_attempt_probe_active`,
`candidate_realpath_extend_attempt_probe_calls`,
`candidate_realpath_extend_attempt_probe_attempts`,
`candidate_realpath_extend_attempt_probe_selected_attempts`,
`candidate_realpath_extend_attempt_probe_seconds`, and
`candidate_realpath_extend_attempt_probe_fallbacks` for a default-off GASAL2
score-only/select probe over the same extend-attempt window shape. The probe is
diagnostic only; it does not feed triplex output, endpoint, CIGAR, candidate
state, or digest authority. Because the current short-query GASAL2 select API is
bounded by `FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812`, the audit summary also
records `candidate_realpath_extend_segmented_attempt_probe_requested`,
`candidate_realpath_extend_segmented_attempt_probe_active`,
`candidate_realpath_extend_segmented_attempt_probe_segments`,
`candidate_realpath_extend_segmented_attempt_probe_calls`,
`candidate_realpath_extend_segmented_attempt_probe_attempts`,
`candidate_realpath_extend_segmented_attempt_probe_selected_attempts`,
`candidate_realpath_extend_segmented_attempt_probe_seconds`, and
`candidate_realpath_extend_segmented_attempt_probe_fallbacks` for a segmented
extend-attempt probe. That segmented probe uses bounded query tiles and remains
diagnostic only. The audit summary also records
`candidate_realpath_extend_flush_segmented_attempt_probe_requested`,
`candidate_realpath_extend_flush_segmented_attempt_probe_active`,
`candidate_realpath_extend_flush_segmented_attempt_probe_flushes`,
`candidate_realpath_extend_flush_segmented_attempt_probe_segments`,
`candidate_realpath_extend_flush_segmented_attempt_probe_calls`,
`candidate_realpath_extend_flush_segmented_attempt_probe_attempts`,
`candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts`,
`candidate_realpath_extend_flush_segmented_attempt_probe_seconds`, and
`candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks` for a
flush-level segmented extend-attempt probe that batches all trusted scoreInfo
attempts for a worker flush before running bounded query segments. This probe is
also diagnostic only. The audit summary also records
`candidate_realpath_extend_flush_segmented_replay_probe_requested`,
`candidate_realpath_extend_flush_segmented_replay_probe_active`,
`candidate_realpath_extend_flush_segmented_replay_probe_tasks`,
`candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts`,
`candidate_realpath_extend_flush_segmented_replay_probe_align_attempts`,
`candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches`,
`candidate_realpath_extend_flush_segmented_replay_probe_seconds`, and
`candidate_realpath_extend_flush_segmented_replay_probe_fallbacks` for a capped
CPU replay diagnostic over flush-level selected attempts. This probe is also
diagnostic only. The audit summary also records
`candidate_post_scoreinfo_unattributed_seconds` and
`candidate_post_scoreinfo_unattributed_fraction` for remaining runner wall time
outside the GPU scoreInfo total.

The first8 real audited gate now isolates the trusted-scoreInfo consumption
subphase:

```text
digest = 093a0d693301322e027ba6f3bd760bcbde60759131f156224f3924b7478581df
tasks = 1,824
realpath_used = 1,824
gpu_scoreinfo_groups = 31,272
candidate_vs_baseline ~= 0.93x
candidate_gpu_scoreinfo_wall_fraction ~= 0.205
candidate_realpath_extend_seconds ~= 10.17
candidate_realpath_extend_fraction ~= 0.407
candidate_realpath_extend_scoreinfo_groups = 31,272
candidate_realpath_extend_align_attempts = 74,646
candidate_realpath_extend_align_seconds ~= 10.12
candidate_realpath_extend_align_fraction ~= 0.405
candidate_realpath_extend_attempt_probe_requested = 1,824
candidate_realpath_extend_attempt_probe_calls = 1,752
candidate_realpath_extend_attempt_probe_attempts = 125,088
candidate_realpath_extend_attempt_probe_active = 0
candidate_realpath_extend_attempt_probe_fallbacks = 1,752
candidate_realpath_extend_segmented_attempt_probe_requested = 0
candidate_realpath_extend_segmented_attempt_probe_active = 0
candidate_realpath_extend_segmented_attempt_probe_segments = 0
candidate_realpath_extend_segmented_attempt_probe_calls = 0
candidate_realpath_extend_segmented_attempt_probe_attempts = 0
candidate_realpath_extend_segmented_attempt_probe_selected_attempts = 0
candidate_realpath_extend_segmented_attempt_probe_seconds = 0
candidate_realpath_extend_segmented_attempt_probe_fallbacks = 0
candidate_realpath_extend_flush_segmented_attempt_probe_requested = 16
candidate_realpath_extend_flush_segmented_attempt_probe_active = 64
candidate_realpath_extend_flush_segmented_attempt_probe_flushes = 16
candidate_realpath_extend_flush_segmented_attempt_probe_segments = 64
candidate_realpath_extend_flush_segmented_attempt_probe_calls = 64
candidate_realpath_extend_flush_segmented_attempt_probe_attempts = 500,352
candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts ~= 218,570
candidate_realpath_extend_flush_segmented_attempt_probe_seconds ~= 1.44
candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks = 0
candidate_realpath_extend_flush_segmented_replay_probe_requested = 16
candidate_realpath_extend_flush_segmented_replay_probe_tasks = 16
candidate_realpath_extend_flush_segmented_replay_probe_align_attempts = 638
candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches = 0
candidate_realpath_extend_flush_segmented_replay_probe_fallbacks = 0
candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches = 0
candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches = 0
candidate_post_scoreinfo_unattributed_fraction ~= 0.795
```

The measured CPU `fastSIM_extend_from_scoreinfo()` consumption is dominated by
repeated `aligner.Align()` attempts. The next GASAL2/GPU work should therefore
target batched extend-attempt consumption, still under the external digest gate,
instead of further tuning the scoped scoreInfo kernel. The first diagnostic
GASAL2 score-only/select probe over those attempts does not become active for
MALAT1 first8 with the formal `FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812` boundary:
stderr records `GASAL2 score length guard: query_len=8708 > max_query_len=2812`.
The segmented extend-attempt probe shows the next boundary more sharply:
bounded query segments can make GASAL2 score-only active and fallback-clean
without raising the short-query limit, but the naive per-scoreInfo/per-segment
shape is performance no-go on MALAT1 first8 (`~44s` segmented probe time). The
current audited preset disables that per-call probe and uses the flush-level
segmented probe instead. A real extend-attempt consumer therefore needs a
batched/flush-level segmented selection design with task-level replay/ranking
equivalence, not the old per-call segmented probe. The current capped replay
probe is now clean on MALAT1 first8/group32. The prior one-triplex mismatch was
a diagnostic replay filtering bug: the hand replay filtered until it collected
`N` passing triplexes, while legacy `fastSIM_extend_from_scoreinfo()` only
inspects the sorted top `N` before threshold filtering. Matching that legacy
filter semantics makes segmented replay, full hand replay, and oracle replay
all report zero triplex mismatches on the capped audited gate.

The flush-level segmented extend-attempt probe gives the first positive
execution-shape signal for that direction. It keeps output CPU-authoritative and
digest-gated, but batches all trusted scoreInfo attempts in a worker flush before
running bounded query segments. On MALAT1 first8 it keeps the same 500,352
segment/attempt evaluations, but reduces GASAL2 select calls from 7,008 to 64
and reduces segmented-probe time from roughly 44s to roughly 1.3s with
fallbacks still at zero. This is not a real output path; it is evidence that the
next plausible implementation must be flush-level batched segmented selection
plus CPU replay/digest validation. The capped flush-level segmented replay probe
starts that validation by comparing selected-attempt CPU replay against the
CPU-authoritative extend triplex list without feeding output. Any replay
mismatches are diagnostic evidence that the selected-attempt shape is not yet
eligible for real output authority; the current capped first8/group32 replay
probe reports zero triplex mismatches, but it only covers one task per flush.

NEAT1 gives the opposite performance signal. The shared-memory legacy-byte
scoreInfo path fails launch for NEAT1 query_len=22767, while the lower-shared-
memory global-state path is correctness-clean but performance no-go:

```text
NEAT1 first4 global-state:
  legacy_byte_shared = 0
  scoreinfo_mismatches = 0
  gpu_hot_total_seconds = 3.12787
  cpu_prealign_seconds = 0.877741
  hot_path_speedup = 0.280619x

NEAT1 first16 global-state:
  legacy_byte_shared = 0
  scoreinfo_mismatches = 0
  gpu_hot_total_seconds = 12.5232
  cpu_prealign_seconds = 3.52635
  hot_path_speedup = 0.281585x
```

The task-level oracle replay probe now calls the legacy `fastSIM_extend_from_scoreinfo()` helper a second time for the same capped task subset. On MALAT1 first8/group32 it is clean:

```text
candidate_realpath_extend_flush_oracle_replay_probe_tasks = 16
candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches = 0
candidate_realpath_extend_flush_oracle_replay_probe_seconds ~= 0.097
```

This proves the replay comparison and legacy helper re-entry can be clean. The
selected/full hand-replay diagnostic now agrees with that oracle on the capped
MALAT1 first8/group32 audited gate. GPU/GASAL2 selected attempts still cannot
be promoted to broad triplex output authority until the same zero-mismatch gate
covers a larger/full task scope with acceptable performance.

The audited wrapper now exposes the replay cap explicitly:

```text
--replay-probe-max-tasks N
```

The default remains one task per flush, preserving the earlier fast gate.
Expanded diagnostic runs widen only the replay comparison surface and keep CPU
output/digest authority. `N=0` means all tasks in each flush. The wrapper
passes this through to
`--long-query-streaming-scoreinfo-gpu-flush-replay-probe-max-tasks`; it does
not give GPU endpoint, CIGAR, traceback, or output authority. The real audited
gate accepts `REPLAY_PROBE_MAX_TASKS=0` and fail-closes on replay mismatch or
fallback:

```text
MALAT1 first8/group32 replay cap=4:
  replay tasks = 64
  replay align attempts = 2,855
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0

MALAT1 first8/group32 replay cap=16:
  replay tasks = 256
  replay align attempts = 10,424
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0

MALAT1 first8/group32 replay cap=0:
  replay tasks = 1,824
  replay selected attempts = 218,570
  replay align attempts = 74,646
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0
  replay fallbacks = 0

MALAT1 first8/group32 selected-only replay cap=0:
  replay tasks = 1,824
  selected-only attempts = 218,570
  selected-only align attempts = 99,022
  selected-only selected scoreInfos = 31,272
  selected-only tasks with selected attempts = 1,752
  selected-only tasks with triplex = 1,348
  selected-only zero-triplex tasks = 476
  selected-only mismatch selected_empty = 5
  selected-only mismatch legacy_empty = 277
  selected-only mismatch selected_less = 28
  selected-only mismatch selected_more = 828
  selected-only mismatch same_count_diff = 36
  selected-only first mismatch task = 0
  selected-only first mismatch kind = selected_more
  selected-only first mismatch provenance = scoreinfo=7;start=4023;cutlength=37;sw_score=73;ref_begin=11;ref_end=30;query_begin=3460;query_end=3479
  selected-only scoreInfos with multiple triplexes = 845
  selected-only extra triplexes from repeated scoreInfo = 965
  selected-only triplex mismatches = 1,174
  selected-only fallbacks = 0
  decision = no-go for direct selected-only consumer

MALAT1 first16/group32 replay cap=0:
  replay tasks = 4,416
  replay align attempts = 186,488
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0

MALAT1 first32/group32 replay cap=0:
  replay tasks = 8,160
  replay align attempts = 344,974
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0

MALAT1 first64/group32 replay cap=0:
  replay tasks = 18,096
  replay align attempts = 764,324
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0
```

This strengthens the MALAT1-like selected-attempt replay equivalence evidence,
and cap 0 is a full replay of the checked first8, first16, first32, and first64
task sets. The direct selected-only consumer is a no-go: most mismatches are
selected-only extra triplexes rather than coverage misses, and the first extra
comes from an additional selected attempt inside scoreInfo 7. The
repeated-scoreInfo telemetry shows the direct consumer breaks the legacy
scoreInfo-level single-emission contract. It is still not a full-scope
scoreInfo/preAlign replacement proof across broader MALAT1, NEAT1, and other
long-query shapes.

So the current long-query scoreInfo state is split:

```text

MALAT1:
  trust correctness clean through full MALAT1
  capped flush-level segmented replay clean on first8/group32
  marginal hot-path positive signal
  selected-attempt CPU-align reduction no-go for current selector

NEAT1:
  non-shared legacy-byte replay clean through first128
  shared runner trust preset launch no-go for scoreInfo
  performance no-go for current execution shape
```

This is the post-selected-replay scoped milestone. It is enough to preserve the
MALAT1 grouped two-contract trust profile as a default-off experimental profile,
and enough to mark the direct selected-only consumer as no-go. It is not enough
to close the broad scoreInfo/preAlign GPU/GASAL2 objective. The next universal
path must be either an explicitly accepted top5-only product contract, a
full-output/TFO equivalence proof over the intended workload scope, or a
genuinely different long-query execution design rather than more tuning of the
current selector/global-state path.

The external-digest-gated non-shared trust mode keeps NEAT1 correctness clean.
The first64 audit now also replays the selected scoreInfo attempts through
CPU `aligner.Align()` and an oracle `fastSIM_extend_from_scoreinfo()` call:

```text
NEAT1 trust first4:
  tasks = 192
  realpath_used = 192
  gpu_scoreinfo_groups = 3,257
  cpu_scoreinfo_groups = 0
  cpu_prealign_seconds = 0
  gpu_total_seconds = 3.12604

NEAT1 trust first16:
  tasks = 768
  realpath_used = 768
  gpu_scoreinfo_groups = 13,492
  cpu_scoreinfo_groups = 0
  cpu_prealign_seconds = 0
  gpu_total_seconds = 12.4996

NEAT1 trust first32:
  tasks = 1,536
  realpath_used = 1,536
  gpu_scoreinfo_groups = 25,960
  cpu_scoreinfo_groups = 0
  cpu_prealign_seconds = 0
  gpu_total_seconds = 25.2269
  baseline Running time = 42.8368
  candidate Running time = 61.0602
  candidate/baseline speedup = 0.701840x

NEAT1 trust first64:
  tasks = 3,072
  realpath_used = 3,072
  gpu_scoreinfo_groups = 52,994
  cpu_scoreinfo_groups = 0
  cpu_prealign_seconds = 0
  gpu_total_seconds = 49.9507
  baseline Running time = 86.0335
  candidate Running time = 121.948
  candidate/baseline speedup = 0.705493x
  digest = 5070d390bdffe9d47c4790193a798bba256d6ec81fc8cef3682a7036f403b01f

NEAT1 first64 fresh runtime attribution:
  candidate_wall_seconds = 121.948
  baseline_wall_seconds = 86.0335
  candidate_vs_baseline = 0.705493x
  gpu_total_seconds = 49.9507 (~41.0% candidate wall)
  gpu_call_seconds = 33.6824
  kernel_seconds = 33.6745
  realpath_extend_seconds = 52.0682 (~42.7% candidate wall)
  realpath_extend_align_seconds = 51.9805
  realpath_extend_align_attempts = 140,087
  unattributed_overhead_seconds ~= 19.9291 (~16.3% candidate wall)

NEAT1 non-shared audited replay first64:
  replay tasks = 3,072
  replay align attempts = 140,087
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0

NEAT1 non-shared audited replay first128:
  digest = 6b0f50f11373ce2dcd8b86045847236d7a094bb43bfa95a0b68a3f66840f9c6e
  replay tasks = 6,144
  gpu_scoreinfo_groups = 105,845
  replay align attempts = 281,588
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0
  candidate/baseline speedup = 0.300675x
```

This is not H2D/D2H, validation, compare, or CPU fallback. H2D/D2H are
millisecond-scale, validation and compare are near zero, and CPU preAlign
fallback is zero. The current selector/global-state long-query shape is
architecture no-go for broad replacement because both the GPU scoreInfo work
and the remaining CPU realpath extend/align work are large. The next broad work
requires a different long-query execution design.

The NEAT1 speed ceiling is tracked separately:

```text
NEAT1 speed ceiling:
  ideal_zero_gpu_total_speedup = 1.1950x
  ideal_zero_gpu_call_speedup = 0.9747x
  ideal_zero_realpath_extend_speedup = 1.2312x
  next architecture must reduce both GPU scoreInfo work and CPU realpath extend/align work
```

It is checked by:

```bash
make check-fasim-gasal2-neat1-speed-ceiling
```

The resulting NEAT1 next architecture requirements are also checked:

```text
NEAT1 next architecture requirements:
  kernel-only win is not sufficient
  If the prototype cannot reduce both GPU scoreInfo and realpath extend/align, stop the NEAT1 broad path
```

```bash
make check-fasim-gasal2-neat1-next-architecture-requirements
```

The next allowed broad-path probe is a replacement consumer shadow, not a
selected-only promotion:

```text
replacement consumer shadow:
  FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REPLACEMENT_CONSUMER_SHADOW=1
  CPU fastSIM_extend_from_scoreinfo remains authority
  selected-only replay is not sufficient
  If NEAT1 remains slower than CPU fallback, do not promote
```

It is checked by:

```bash
make check-fasim-gasal2-replacement-consumer-shadow-requirements
make check-fasim-gasal2-replacement-consumer-shadow-env
make check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke
make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan
```

The runtime smoke is deliberately a stop-signal smoke, not a promotion gate:

```text
NEAT1 first1 replacement-consumer shadow smoke:
  digest clean
  segmented/full/oracle replay mismatches = 0
  selected-only replay mismatch remains visible
  replacement_consumer_shadow_first_mismatch_source = selected_only
  replacement_consumer_shadow_first_mismatch_kind = legacy_empty
```

The selected-consumer root cause is now understood. The legacy
`fastSIM_extend_from_scoreinfo()` contract is scoreInfo-local:

```text
per scoreInfo:
  sweep Iden windows in order
  break when sw_score >= scoreInfo.score
  otherwise keep only a ref_end == cutlength - 1 best alignment
  emit at most one alignment before moving to the next scoreInfo
```

Direct selected-only replay loses the scoreInfo-local break/best-end state
machine and can emit triplexes that the legacy consumer never emits. The grouped selected-prefix
probe is clean because it expands each selected scoreInfo back to its legacy
prefix, which also removes the CPU-align reduction. Therefore current
selected-attempt reduction is no-go as a broad replacement consumer.

The only remaining plausible broad consumer direction is a score-prepass
state-machine consumer:

```text
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1
select_attempts_from_scores()
CPU-align only the selected attempt per scoreInfo
```

This would use GASAL2 score-only `sw_score` and `ref_end` to apply the same
threshold / best-end / last selector before CPU traceback. It is still a
shadow-first design, not output authority.

```bash
make check-fasim-gasal2-score-prepass-state-machine-consumer
```

The segmented score-prepass state-machine shadow now exists as a default-off
runtime diagnostic. It avoids the unsafe whole-query selector by using bounded
query segments, expands selected attempts back to the required scoreInfo prefix,
and compares converted triplexes against CPU authority. Bounded characterization
is correctness-clean but performance no-go for the current shadow shape:

```text
NEAT1 first1:
  scoreinfo_mismatches = 0
  state_machine_triplex_mismatches = 0
  state_machine_cpu_align_attempts = 51
  candidate_vs_baseline = 0.530629x

NEAT1 first4:
  scoreinfo_mismatches = 0
  state_machine_triplex_mismatches = 0
  state_machine_cpu_align_attempts = 643
  candidate_vs_baseline = 0.568306x

NEAT1 first16:
  scoreinfo_mismatches = 0
  state_machine_triplex_mismatches = 0
  state_machine_cpu_align_attempts = 13,474
  candidate_vs_baseline = 0.522888x

MALAT1 first8:
  scoreinfo_mismatches = 0
  state_machine_triplex_mismatches = 0
  state_machine_cpu_align_attempts = 6,188
  candidate_vs_baseline = 0.702397x
```

Current decision:

```text
Correctness/shape:
  go as default-off shadow scaffold

Performance:
  no-go for current shadow implementation

Real path:
  no
```

This is checked by:

```bash
make check-fasim-gasal2-score-prepass-state-machine-characterization
```

The newer attempt-consumer shadow is also a default-off diagnostic scaffold:

```text
FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1
```

It uses GASAL2 score-only selection over legacy scoreInfo attempts, then
CPU-aligns the selected replay attempts in shadow and compares task triplexes
against CPU authority. The NEAT1 first64 characterization is correctness-clean
but a hard no-go for the current conservative replay shape:

```text
NEAT1 first64:
  decision = attempt_consumer_shadow_no_cpu_align_reduction_no_go
  digest clean
  triplex_mismatches = 0
  missing_triplexes = 0
  extra_triplexes = 0
  attempts = 211,976
  selected_attempts = 140,087
  cpu_align_attempts = 140,087
  realpath_extend_align_attempts = 140,087
  score_seconds = 241.768
  total_seconds = 294.821
  candidate_vs_baseline = 0.148434x
```

This is a useful milestone because it proves the attempt stream/replay scaffold
can stay output-equivalent on NEAT1 first64. It is not a performance path:
CPU replay attempts are identical to the CPU realpath reference, and the GASAL2
score-only shadow adds substantial overhead.

This is checked by:

```bash
make check-fasim-gasal2-attempt-consumer-shadow-runtime-smoke
make characterize-fasim-gasal2-attempt-consumer-neat1-first64
make check-fasim-gasal2-attempt-consumer-neat1-first64-result
```

The score-prepass state-machine trust path also exists as a default-off audited
prototype:

```text
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_TRUST=1
```

It can skip CPU realpath extend and produce digest-clean output on bounded
NEAT1 rows, but it is still performance no-go because it performs the same
amount of CPU traceback work through the state-machine consumer:

```text
NEAT1 first16:
  digest clean
  realpath_extend_align_attempts = 0
  state_machine_cpu_align_attempts = 35,152
  candidate_vs_baseline = 0.5951x
```

Current decision:

```text
score-prepass state-machine trust:
  correctness clean as audited scaffold
  performance no-go for current implementation
  real path no
```

It is checked by:

```bash
make check-fasim-gasal2-score-prepass-state-machine-trust
make check-fasim-gasal2-score-prepass-state-machine-trust-runtime-smoke
```

This rules out a broad long-query real path from the current implementation.
The runner trust preset's shared-memory legacy-byte shape is not a NEAT1
replacement path either: on NEAT1 first4 it launches GPU minScore cleanly, but
the shared scoreInfo kernel fails with `invalid argument`, leaving
`gpu_scoreinfo_groups=0`, `realpath_used=0`, and `realpath_fallbacks=4`.
Any next prototype must be workload-gated and validation-first, or must replace
the NEAT1 scoreInfo execution shape.

It is checked by:

```bash
make check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte-shared
make check-fasim-long-query-streaming-scoreinfo-shadow-gpu-minscore
make check-fasim-long-query-streaming-scoreinfo-shadow-gpu-minscore-hot
make check-fasim-long-query-streaming-scoreinfo-realpath-prototype
make check-fasim-long-query-streaming-scoreinfo-realpath-trust
make check-fasim-long-query-streaming-scoreinfo-trust-group32-runner
make check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner
make check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real
make check-fasim-long-query-streaming-scoreinfo-neat1-audited-runner-real
make check-fasim-long-query-streaming-scoreinfo-trust-runner-real
make characterize-fasim-long-query-streaming-scoreinfo-realpath
make characterize-fasim-long-query-streaming-scoreinfo-realpath-trust
make characterize-fasim-long-query-streaming-scoreinfo-malat1-full-trust
make characterize-fasim-long-query-streaming-scoreinfo-neat1-trust
make characterize-fasim-long-query-streaming-scoreinfo-neat1-first64-trust
make characterize-fasim-long-query-streaming-scoreinfo-hot
```

## Product-Readiness Boundary

The top5-only product-readiness checkpoint is:

```bash
make check-fasim-gasal2-top5-product-readiness
```

The top5 broader workload validation checkpoint is:

```bash
make check-fasim-gasal2-top5-broader-validation
```

The Full Goal Decision Audit checkpoint is:

```bash
make check-fasim-gasal2-full-goal-decision
```

The GASAL2 top5 recommended runtime checkpoint is:

```bash
make check-fasim-gasal2-top5-recommended-runtime
```

The top5 scoped completion candidate checkpoint is:

```bash
make check-fasim-gasal2-top5-scoped-completion-candidate
```

The focused top5 release smoke checkpoint is:

```bash
make check-fasim-gasal2-top5-release-smoke
```

The latest release smoke records:

```text
formal_preset_example = meg3_first32
formal_preset_topk_artifact_match = true
formal_preset_gasal2_requests = 63,035
formal_preset_exact_scoreinfo_gpu_tasks = 1,536
formal_preset_speedup_vs_cpu_worker_wall_sum < 1.0
```

This is a contract smoke, not a performance claim.

That gate records the top5-only product-readiness boundary for the formal preset.
The broader validation gate records the current short-query positive set and
long-query guard set. The recommended-runtime gate records the default-off
short-query/H19 invocation. Together they keep the scoped contract as a
default-off opt-in, keep long-query fallback policy explicit, and keep the
full objective open until broader requirements are proven. The top5 scoped
completion candidate records the conditional scope only; the full objective
remains open unless that narrowed product contract is explicitly accepted.

The next broad attempt is an emission-only scoreInfo consumer shadow:
FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1. It must use GASAL2 score/end to
choose emitted attempts and CPU-align only those emitted attempts. It is a
go only if NEAT1 first64 is triplex/digest clean and CPU align attempts are
lower than the realpath reference.
