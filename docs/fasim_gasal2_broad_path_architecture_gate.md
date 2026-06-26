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

The emission-only scoreInfo consumer shadow is now a measured NEAT1 first64
stop checkpoint:

```text
FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1
decision = emission_only_consumer_shadow_correctness_no_go
baseline_wall_seconds = 86.781985
candidate_wall_seconds = 550.461678
candidate_vs_baseline = 0.157653x
scored_attempts = 211,976
cpu_align_attempts = 52,994
realpath_reference_align_attempts = 140,087
align_attempt_reduction = 87,093
triplex_mismatches = 4,404
missing_triplexes = 2,096
extra_triplexes = 1,460
emission_shadow_total_seconds = 262.714
score_seconds = 241.564
```

It proves the emission-only shape can reduce CPU align attempts, but it is not
semantically equivalent and is much slower than baseline. It must not be
promoted as the broad path.

The later Gate C candidate-generator branch is also stopped for the current
source:

```text
phase7_gate_c_stop_checkpoint = current_source_no_go
phase7_gate_c_first1 = no_go_no_gpu_candidate_descriptors
digest_match = 1
full_rows_equal = 1
candidate_align_attempts = 2,008
gate_b_candidate_align_attempts = 2,008
gpu_candidate_scoreinfos = 0
gpu_candidate_attempts = 0
scoreinfo_reduced = 0
current_gate_c_source_status = stopped_no_gpu_candidate_descriptors
gate_c_first64_allowed = 0
```

This proves the CPU-authority replay side remains clean on NEAT1 first1, but
the current Gate C source does not generate GPU candidate descriptors and does
not reduce scoreInfo/preAlign work. It must not continue to first64 broad
characterization.

The next allowed architecture checkpoint is v3 candidate-certificate design:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_candidate_certificate_design.md
phase7_broad_restart_v3_candidate_certificate_design = defined
phase7_broad_restart_v3_current_status = design_only
phase7_broad_restart_v3_next_gate = descriptor_source_smoke
requires_gpu_or_native_descriptor_source = 1
requires_candidate_certificate = 1
requires_cpu_authority_replay = 1
requires_scoreinfo_prealign_reduction = 1
requires_align_side_reduction = 1
requires_full_output_equality = 1
phase7_broad_restart_v3_may_claim_completion = 0
```

v3 is allowed only because it is not another run of the stopped current
sources. It must produce descriptors before CPU scoreInfo/preAlign has already
done the broad work, prove a zero-false-negative candidate certificate, and
then replay through CPU `aligner.Align()` as authority.

The first v3 descriptor-source runtime smoke is also not a broad pass:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_descriptor_source_smoke.md
phase7_broad_restart_v3_descriptor_source_smoke = current_no_pre_scoreinfo_source
phase7_broad_restart_v3_current_status = scaffold_no_go
phase7_v3_descriptor_source_requested = 1
phase7_v3_descriptor_source_active = 0
phase7_v3_descriptor_source_candidate_attempts = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate = real_pre_scoreinfo_descriptor_source
```

It proves telemetry wiring only. It does not produce pre-scoreInfo descriptors
and must not be used to create a broad replacement row.

The second v3 smoke moves the hook before CPU scoreInfo/preAlign, but still is
not a broad pass:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke.md
phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke =
  pre_scoreinfo_descriptors_no_reduction
phase7_broad_restart_v3_current_status = pre_scoreinfo_scaffold_no_go
phase7_v3_descriptor_source_active = 1
phase7_v3_descriptor_source_pre_scoreinfo_source = 1
phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0
phase7_v3_descriptor_source_candidate_certificate_checked = 0
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate =
  certificate_checked_scoreinfo_reducing_descriptor_source
```

It proves descriptor-source placement only. It does not reduce CPU
scoreInfo/preAlign work and does not prove candidate-certificate coverage.

The current certificate smoke is also not a broad pass:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_certificate_smoke.md
phase7_broad_restart_v3_certificate_smoke =
  certificate_checked_no_scoreinfo_reduction
phase7_broad_restart_v3_current_status = certificate_scaffold_no_go
phase7_v3_descriptor_source_active = 1
phase7_v3_descriptor_source_pre_scoreinfo_source = 1
phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
phase7_v3_descriptor_source_candidate_certificate_checked = 1
phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
phase7_v3_descriptor_source_missing_required_attempts = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0
cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate =
  scoreinfo_reducing_candidate_certificate
```

This smoke checks certificate plumbing only. It does not prove full legacy
scoreInfo/attempt coverage and does not reduce CPU scoreInfo/preAlign work.

The all-column certificate smoke passes Gate v3.1 only:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_all_column_certificate_smoke.md
phase7_broad_restart_v3_all_column_certificate_smoke =
  scoreinfo_reducing_all_column_certificate
phase7_broad_restart_v3_current_status =
  gate_v3_1_pass_attempt_overgenerate
phase7_v3_descriptor_source_candidate_scoreinfos_gt_zero = 1
phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
phase7_v3_descriptor_source_candidate_certificate_checked = 1
phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
phase7_v3_descriptor_source_missing_required_attempts = 0
phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
phase7_broad_restart_v3_next_gate =
  all_column_certificate_cpu_replay_first1
```

This smoke overgenerates every target column and every target window. It is
not a performance candidate and does not allow a first64 or broad claim.

The all-column replay preflight is now stopped:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_all_column_replay_stop.md
phase7_broad_restart_v3_all_column_replay_stop =
  candidate_attempt_explosion_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
candidate_attempts = 168,730,848
reference_align_attempts = 2,872
candidate_attempt_ratio = 58,750.30x
candidate_align_attempts < reference_align_attempts cannot pass
do_not_run_all_column_cpu_replay = 1
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate =
  narrower_scoreinfo_reducing_certificate
```

This keeps v3.1 as a useful proof while stopping the all-column branch before
it spends CPU replay work that cannot satisfy Gate v3.2.

The next branch is design-only:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_design.md
phase7_broad_restart_v3_narrow_certificate_design = defined
phase7_broad_restart_v3_narrow_certificate_status = design_only
phase7_broad_restart_v3_next_gate = narrow_certificate_runtime_smoke
required_runtime_env = FASIM_GASAL2_PHASE7_V3_NARROW_CERTIFICATE
must_be_narrower_than_all_column = 1
candidate_attempts < 168,730,848
candidate_attempts < reference_align_attempts required for v3.2
```

This is the only current v3 branch allowed to continue Path B, and it still
must pass runtime smoke, first1 replay, and first64 broad gates before any
broad claim.

The first narrow runtime smoke is also stopped:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_smoke.md
phase7_broad_restart_v3_narrow_certificate_smoke =
  bounded_probe_no_go_missing_certificate
phase7_broad_restart_v3_narrow_certificate_status = runtime_smoke_no_go
phase7_v3_descriptor_source_candidate_attempts_lt_all_column = 1
phase7_v3_descriptor_source_candidate_certificate_false_negatives_gt_zero = 1
phase7_v3_descriptor_source_missing_required_attempts_gt_zero = 1
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_next_gate = real_narrow_certificate_coverage_proof
```

This proves bounded telemetry only. It does not pass coverage and must not
continue to first64.

The direct exact-column scoreInfo coverage candidate is also no-go:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_real_narrow_certificate_coverage_proof.md
phase7_broad_restart_v3_real_narrow_certificate_coverage_proof =
  exact_column_candidate_no_go
phase7_broad_restart_v3_exact_column_candidate_status = no_go
non_optin_active = 0
non_optin_error = invalid argument
smem_optin_active = 1
smem_optin_scoreinfo_mismatches = 1
smem_optin_decision = smem_optin_scoreinfo_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_next_gate =
  different_exact_scoreinfo_source_or_seed_certificate
```

This leaves no current v3 runtime source that can pass Gate v3.1. Path B needs
a different exact scoreInfo-compatible execution design or a seed certificate
with a coverage proof.

## Decision

```text
previous_decision = broad_path_requires_co_designed_scoreinfo_and_consumer
decision = broad_path_current_architecture_no_go
phase7_current_broad_stop_decision = current_broad_sources_no_go
current_broad_sources_status = stopped
phase7_current_broad_sources_may_continue = 0
phase7_new_architecture_required = 1
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
full objective remains open
```

## Gate

```bash
make check-fasim-gasal2-broad-path-architecture-gate
```
