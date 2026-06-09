# Fasim GASAL2 Broad Path Architecture Gate

This checkpoint defines the next allowed architecture direction for the active
scoreInfo/preAlign GPU/GASAL2 objective.

It is a design gate, not runtime code. It exists because the current scoped
paths are useful milestones, but the broad objective remains open.

## Current State

The current positive paths are scoped:

```text
short-query/H19 top5 artifact:
  scoped product candidate

MALAT1-like group32 two-contract runtime:
  scoped product-readiness candidate
```

The current broad long-query lines are no-go:

```text
NEAT1 non-shared trust runtime first64:
  candidate_vs_baseline = 0.705493x
  gpu_total_seconds = 49.9507
  realpath_extend_seconds = 52.0682

NEAT1 speed ceiling:
  ideal_zero_gpu_call_speedup = 0.9747x
  ideal_zero_gpu_total_speedup = 1.1950x
  ideal_zero_realpath_extend_speedup = 1.2312x

score-prepass state-machine consumer:
  candidate_vs_baseline = 0.5951x on NEAT1 first16
  selected-segment traceback mismatches = 22,000 / 35,152 on first16
  expanded-segment oracle requires full query length for many attempts

co-designed broad replacement-consumer shadow on NEAT1 first64:
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
  decision_reasons:
    candidate_wall_not_below_neat1_baseline_ceiling
    candidate_vs_baseline_not_above_1
    broad_scoreinfo_consumer_not_below_cpu_reference
    align_attempts_not_reduced
```

This means a kernel-only scoreInfo improvement cannot close the broad goal, and
the current co-designed broad replacement-consumer shadow is also a measured
performance no-go. The next architecture must be materially different and must
reduce both GPU scoreInfo work and CPU realpath extend/align work.

## Required Future Architecture Shape

Any future broad-path prototype must still be a co-designed scoreInfo plus
replacement consumer architecture, but not the current replay-heavy broad
state-machine shape:

```text
1. produce legacy-byte-compatible scoreInfo or prove an explicitly scoped output contract
2. preserve scoreInfo-level single-emission semantics
3. avoid current CPU preAlign replay
4. reduce or replace current CPU realpath extend/align replay
5. compare complete task triplex lists against CPU authority
6. keep external digest or full row-set equality as output authority
7. keep GPU endpoint/CIGAR/traceback out of authority unless separately proven
```

The replacement consumer must not be selected-only replay. It must preserve the
legacy scoreInfo-local break/best-end state:

```text
for each scoreInfo:
  sweep candidate windows in legacy order
  emit once when sw_score >= scoreInfo.score
  otherwise emit at most one best/last alignment when ref_end == cutlength - 1
```

Any design that loses that state must stop before performance characterization.

## Required Telemetry

Future prototypes must report:

```text
broad_path_requested
broad_path_active
broad_path_tasks
broad_path_scoreinfo_groups
broad_path_scoreinfo_seconds
broad_path_consumer_seconds
broad_path_align_attempts
broad_path_selected_attempts
broad_path_triplex_mismatches
broad_path_missing_triplexes
broad_path_extra_triplexes
broad_path_first_mismatch
broad_path_digest_match
broad_path_full_rows_equal
broad_path_candidate_wall_seconds
broad_path_baseline_wall_seconds
broad_path_candidate_vs_baseline
```

Existing two-contract counters must remain visible for comparison:

```text
two_contract_used
two_contract_fallbacks
two_contract_score_mismatches
two_contract_min_score_mismatches
two_contract_scoreinfo_mismatches
realpath_used
realpath_fallbacks
gpu_scoreinfo_groups
cpu_scoreinfo_groups
```

## Hard Go Gate

NEAT1 first64 is the broad-path gate:

```text
digest clean or full row-set equality clean
triplex_mismatches = 0
scoreinfo_gasal2_active = 1 or explicitly scoped equivalent active path
fallback = 0
scoreInfo mismatches = 0
candidate_wall_seconds < 86.0335
candidate_vs_baseline > 1.0x
GPU scoreInfo plus replacement-consumer total beats CPU fallback
realpath_extend_align_attempts materially reduced or replaced
MALAT1 scoped product-readiness remains clean
```

If the prototype cannot reduce both GPU scoreInfo work and realpath
extend/align, stop the NEAT1 broad path.

## Stop Conditions

Stop the broad path if any of these are true:

```text
kernel-only improvement is the main change
selected-only replay is the consumer
prefix replay is required and align attempts are not reduced
triplex output changes
full row-set equality fails for the claimed scope
NEAT1 remains slower than CPU fallback
GPU endpoint/CIGAR/traceback authority is required before separate proof
MALAT1 scoped product-readiness regresses
```

## Forbidden Promotions

Do not promote:

```text
current selector/global-state NEAT1 path
segmented no-last replay
single-pass topN
exact tiling
overlap tiling
smem opt-in exact-column
score-prepass state-machine consumer trust
selected-segment GASAL2 traceback
MALAT1 scoped two-contract runtime as broad long-query replacement
top5 artifact path as full-output replacement
```

## Allowed Continuation

Allowed next work:

```text
prototype a materially different scoreInfo plus replacement consumer architecture
reduce scoreInfo/align attempts before replaying CPU aligner state
prototype a lower-shared-memory scoreInfo design only if it also reduces consumer work
prove full-output/TFO equivalence over an explicitly claimed scope
productize an accepted scoped contract without claiming broad replacement
```

The implementation plan for the allowed broad shadow is checked by:

```bash
make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan
```

That plan is now a completed checkpoint for the current broad architecture: the
replacement-consumer shadow is correctness-clean on the checked NEAT1 first64
gate, but its performance is no-go. It remains useful evidence, not a real path.

The attempt-consumer shadow is a later, narrower milestone with the same hard
boundary:

```text
FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1
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

It proves the attempt-level shadow can be output-equivalent on NEAT1 first64,
but it does not reduce CPU realpath align attempts and is therefore not a real
path candidate.

The next broad attempt is an emission-only scoreInfo consumer shadow:
FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1. It must use GASAL2 score/end to
choose emitted attempts and CPU-align only those emitted attempts. It is a
go only if NEAT1 first64 is triplex/digest clean and CPU align attempts are
lower than the realpath reference.

## Decision

```text
previous_decision = broad_path_requires_co_designed_scoreinfo_and_consumer
decision = broad_path_current_architecture_no_go
full objective remains open
```

## Gate

```bash
make check-fasim-gasal2-broad-path-architecture-gate
```
