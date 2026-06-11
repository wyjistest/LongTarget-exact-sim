# Fasim GASAL2 Replacement Consumer Shadow Requirements

This is a requirements checkpoint, not runtime code. It records the next
allowed broad-path probe after the MALAT1 scoped milestone and NEAT1 speed
ceiling. The active objective remains open.

## Current State

MALAT1 no-probe two-contract path is a scoped milestone:

```text
MALAT1 full lite:
  tasks = 200,400
  two_contract_used = 200,400
  realpath_used = 200,400
  gpu_scoreinfo_groups = 3,561,123
  candidate_vs_baseline = 1.038567x

MALAT1 full TFOsorted:
  tasks = 200,400
  two_contract_used = 200,400
  realpath_used = 200,400
  gpu_scoreinfo_groups = 3,561,123
  candidate_vs_baseline = 1.038799x
```

This proves a MALAT1-like scoped path. It does not complete the broad
scoreInfo/preAlign GPU/GASAL2 objective.

NEAT1 first64 is the blocking broad-replacement case:

```text
baseline_wall_seconds = 86.0335
candidate_wall_seconds = 121.948
gpu_total_seconds = 49.9507
realpath_extend_seconds = 52.0682
realpath_extend_align_attempts = 140,087
```

The current path is not blocked by H2D/D2H, validation, compare, or CPU
preAlign fallback. The remaining CPU `fastSIM_extend_from_scoreinfo()` replay
is a co-equal bottleneck with GPU scoreInfo work.

## Required Shadow Shape

The next useful broad-path probe is a replacement consumer shadow. CPU
fastSIM_extend_from_scoreinfo remains authority.

The shadow must:

```text
collect per-scoreInfo align attempts
preserve scoreInfo-level single-emission semantics
compare task triplex lists against CPU authority
keep digest as external authority
```

digest remains external authority.

The shadow must not:

```text
Do not use GPU endpoint
Do not use GPU CIGAR
Do not use GPU traceback
Do not use replacement-consumer output
```

The probe should stay default-off and fail closed. It may collect or replay a
candidate replacement-consumer surface, but it cannot alter candidate state,
output, or digest.

The default-off umbrella env is:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REPLACEMENT_CONSUMER_SHADOW=1
```

This is a default-off umbrella over the existing segmented attempt, segmented
replay, selected-only replay, grouped-selected replay, full replay, and oracle
replay probes. It does not introduce output authority.

## Existing Replay Boundaries

selected-only replay is not sufficient. It over-emits repeated scoreInfos and
changes task triplex lists.

grouped selected-prefix replay restores correctness but not align-attempt
reduction. The clean prefix shape collapses back to the expanded replay cost.

full replay is correctness reference, not performance candidate. It proves
that the local hand replay can match CPU authority, but it still uses the same
CPU `aligner.Align()` work shape.

The root cause is the legacy `fastSIM_extend_from_scoreinfo()` state machine:

```text
for each scoreInfo in order:
  sweep Iden windows
  if alignment.sw_score >= scoreInfo.score:
      emit this scoreInfo and stop sweeping it
  else remember best alignment only when ref_end == cutlength - 1
  after the sweep, emit at most one best/last alignment for that scoreInfo
```

Any replacement consumer that replays only selected attempts, or that ranks
selected attempts after losing the scoreInfo-local break/best-end state, can
emit triplexes the legacy consumer would not emit. The clean grouped-selected
probe is clean because it expands selected scoreInfo groups back to the legacy
prefix, which removes the CPU-align reduction.

## Required Telemetry

telemetry must include:

```text
replacement_consumer_shadow_requested
replacement_consumer_shadow_active
replacement_consumer_shadow_tasks
replacement_consumer_shadow_scoreinfo_groups
replacement_consumer_shadow_align_attempts
replacement_consumer_shadow_selected_attempts
replacement_consumer_shadow_triplex_mismatches
replacement_consumer_shadow_segmented_triplex_mismatches
replacement_consumer_shadow_selected_only_triplex_mismatches
replacement_consumer_shadow_grouped_selected_triplex_mismatches
replacement_consumer_shadow_full_triplex_mismatches
replacement_consumer_shadow_oracle_triplex_mismatches
replacement_consumer_shadow_first_mismatch
replacement_consumer_shadow_first_mismatch_source
replacement_consumer_shadow_first_mismatch_kind
replacement_consumer_shadow_seconds
replacement_consumer_shadow_fallbacks
```

The runtime smoke keeps the stop signal visible:

```text
NEAT1 first1 replacement-consumer shadow smoke:
  digest clean
  segmented/full/oracle replay mismatches = 0
  selected-only replay mismatch remains visible
  replacement_consumer_shadow_first_mismatch_source = selected_only
  replacement_consumer_shadow_first_mismatch_kind = legacy_empty
```

## Hard Go Gate

Hard go gate:

```text
triplex_mismatches = 0
candidate_wall_seconds < 86.0335
replacement consumer plus GPU scoreInfo total beats CPU fallback
MALAT1 scoped positive remains clean
```

## Stop Gate

Stop gate:

```text
If selected-attempt reduction changes triplex output, do not promote.
If prefix replay is required and align attempts are not reduced, do not promote.
If NEAT1 remains slower than CPU fallback, do not promote.
If a consumer cannot preserve the scoreInfo-local break/best-end state machine,
do not promote.
```

No replacement-consumer shadow result may be promoted to a real path until the
claimed workload passes the external digest gate and the task triplex comparison
gate.

The broad co-designed implementation plan is checked by:

```bash
make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan
```

It keeps CPU fastSIM_extend_from_scoreinfo as authority while the new shadow
proves complete task triplex equivalence and real align-attempt reduction.

## Gate

```bash
make check-fasim-gasal2-replacement-consumer-shadow-requirements
make check-fasim-gasal2-replacement-consumer-shadow-env
make check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke
```
