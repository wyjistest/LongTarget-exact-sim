# Fasim GASAL2 Goal Completion Roadmap

This document defines the phase plan for completing the GASAL2/Fasim work
without redefining partial milestones as full success.

The canonical execution entry point is
`docs/fasim_gasal2_goal_completion_canonical_phase_plan.md`. Use that document
to decide which phase is current, what must be proven next, and when the active
goal may close. The other roadmap documents preserve evidence and historical
gate details.

For the current single-page action roadmap that says phase by phase what must
be done to make the active goal closable, use
`docs/fasim_gasal2_goal_completion_action_roadmap.md`.

For the shortest current playbook that says phase by phase what must be done
before the active goal can close, use
`docs/fasim_gasal2_goal_completion_playbook.md`.

For the direct document that says, phase by phase, what still has to happen to
make the active goal completable from the current cursor, use
`docs/fasim_gasal2_goal_completion_phase_to_completion_plan.md`.

For the current direct entry point without the historical checkpoint trail,
use `docs/fasim_gasal2_goal_completion_direct_phase_roadmap.md`. It states
Phase 0 through Phase 8, the current Phase 7 upper-bound reject certificate
cursor, and the exact conditions under which the active goal may close.

For the current finish plan that says phase by phase what must happen before
the active goal can close, use
`docs/fasim_gasal2_goal_completion_finish_plan.md`. For the operational
runbook that says how the active goal can close, use
`docs/fasim_gasal2_goal_completion_runbook.md`. For the short execution checklist, use
`docs/fasim_gasal2_goal_completion_phase_checklist.md`. For the phase-by-phase
completion ladder, use
`docs/fasim_gasal2_goal_completion_execution_ladder.md`. For the full current
execution order, use `docs/fasim_gasal2_goal_completion_phase_plan.md`. For the
current stepwise plan that says what each phase must do next, use
`docs/fasim_gasal2_goal_completion_stepwise_plan.md`. For the
canonical goal-closure phase plan that says phase by phase what must be proven
before the active goal can close, use
`docs/fasim_gasal2_goal_closure_phase_plan.md`. For the
post-v5.3 long-query-safe Path B design after the GASAL2 score-only
host-assisted no-go, use
`docs/fasim_gasal2_phase7_post_v5_3_long_query_safe_consumer_summary_design.md`.
For the Phase 7.3 checkpoint that records why the current certificate producer
cannot support a real first1 reducing runtime, use
`docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.md`.
For the design response after that no-go, which requires the next Path B step
to be a real-source first1 spec instead of a continuation of the synthetic
certificate producer, use
`docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md`.
For the real-source first1 implementation spec that defines the runtime hook,
certificate source, certificate consumer, work-drop point, and fail-closed
telemetry before any first1 shadow runtime, use
`docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md`.
For the real-source first1 fail-closed shadow scaffold that makes that gate
observable without enabling work drop, use
`docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scaffold.md`.
For the source-only Phase 7.2 checkpoint that proves a real pre-drop Fasim
runtime certificate source exists while keeping work drop disabled, use
`docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md`.
For the Phase 7.4 fail-closed first1 shadow that observes the real source and
keeps work drop disabled while the proof is still not accepted, use
`docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow.md`.
For the Phase 7.4b proof-consumer no-go that stops the current descriptor
stream family, use
`docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md`.
For the different GPU execution design after that consumer no-go, use
`docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md`.
For the post-consumer GPU scoreInfo certificate engine spec after that design
checkpoint, use
`docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.md`.
For the post-consumer GPU scoreInfo certificate engine first1 fail-closed
shadow scaffold after that spec, use
`docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.md`.
For the no-go decision after that fail-closed shadow cannot be consumed into
pre-drop work drop, use
`docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md`.
For the fork after that scoreInfo certificate-engine no-go, which stops that
family and defines the next genuinely different Path B design family, use
`docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go.md`.
For the GPU-owned scoreInfo consumer design spec after that fork, use
`docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance.md`.
For the GPU-owned scoreInfo consumer first1 fail-closed shadow scaffold after
that spec, use
`docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold.md`.
For the GPU-owned scoreInfo consumer first1 shadow consumer no-go after that
scaffold, use
`docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go.md`.
For the fork after that GPU-owned consumer no-go, which records that Path A is
not accepted and defines the next genuinely different Path B design family,
use
`docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md`.
For the full-align verifier design spec after that fork, which defines the
GASAL2 proposal schema, CPU verifier certificate schema, failure taxonomy, and
first1 fail-closed telemetry contract, use
`docs/fasim_gasal2_phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance.md`.
For the full-align verifier first1 shadow consumer no-go after the descriptor
only scaffold produced no GASAL2 full-align proposals, use
`docs/fasim_gasal2_phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go.md`.
For the fork after that no-go, which stops the GASAL2 full-align verifier
family and defines the next non-GASAL2 Path B design family, use
`docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go.md`.
For the native CUDA/Fasim DP engine first1 shadow consumer no-go after that
scaffold produced no native DP certificates, use
`docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_no_go.md`.
For the fork after that native CUDA/Fasim DP engine no-go, which records that
Path A is not accepted and requires any further Path B work to start with a
new GPU execution design family spec, use
`docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go.md`.
For the GPU upper-bound reject certificate design spec after that fork, which
defines a negative-certificate Path B family and only allows a first1
fail-closed shadow next, use
`docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance.md`.
For the GPU upper-bound reject certificate first1 fail-closed shadow scaffold,
which records non-reducing upper-bound descriptor/certificate telemetry and
keeps CPU replay authoritative, use
`docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold.md`.
For the GPU upper-bound reject certificate first1 shadow consumer no-go, which
records that the scaffold produced no rejected work that can be consumed into
safe pre-drop work reduction, use
`docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go.md`.
For the fork after that no-go, which records that Path A is not accepted and
requires any further Path B work to start with a genuinely different GPU
execution design family spec, use
`docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go.md`.
For the exact work-unit compaction design spec after that fork, which defines
a GPU-assisted exact input-key compaction/replay family and only allows a
first1 fail-closed shadow next, use
`docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md`.
For the exact work-unit compaction first1 fail-closed shadow scaffold, which
records exact-key descriptor telemetry while keeping CPU replay authoritative
and runtime work drop disabled, use
`docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold.md`.
For the exact work-unit compaction first1 shadow consumer no-go, which records
that the shadow produced no duplicate scoreInfo/preAlign units or Align
attempts that can be consumed into safe runtime work reduction, use
`docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go.md`.
For the fork after that no-go, which records that Path A is not accepted and
requires any further Path B work to start with a genuinely different GPU
execution design family spec, use
`docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go.md`.
For the spec-or-acceptance decision after that fork, which records that no
Path A acceptance or viable new Path B design is currently available, use
`docs/fasim_gasal2_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go.md`.
For the input-required checkpoint after that decision, which records that no
Path A scope acceptance or external new Path B design input has been supplied,
use
`docs/fasim_gasal2_path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go.md`.
For the
canonical close roadmap that says which phase comes next and when the active
goal may close, use
`docs/fasim_gasal2_goal_completion_phase_roadmap.md`. For the concise
phase-by-phase close plan, use
`docs/fasim_gasal2_goal_completion_close_plan.md`. For the shortest gate plan
that says what each phase must do before the goal can close, use
`docs/fasim_gasal2_goal_completion_gate_plan.md`. For the direct execution
document that says what Phase 0 through Phase 8 must do to make the active goal
closable, use
`docs/fasim_gasal2_goal_completion_phase_execution_plan.md`. That execution
plan is the current direct entry point when continuing the active goal. For the
shortest phase driver that says exactly where the active goal cursor is and
what each phase must prove, use
`docs/fasim_gasal2_goal_completion_phase_driver.md`. This
roadmap keeps the evidence ledger; the gate plan, ladder, phase plan, and
close roadmap are the step-by-step contracts for what each phase must do before
the active goal may close.

## Current Cursor

```text
current_path = Path A scoped completion accepted
current_phase = Phase 8
current_gate = phase8_path_a_scoped_completion_accepted
current_execution_gate = phase8_path_a_scoped_completion_accepted
current_next_pr = none_goal_complete_scoped_path_a
current_gate_document = docs/fasim_gasal2_path_a_scoped_completion_acceptance.md
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
path_a_scoped_completion_status = accepted
broad_objective_status = open
active_goal_completion_status = complete_scoped_path_a
completion_guard_cleared = 1
must_not_call_update_goal_complete = 0
```

Historical pre-Path-A-acceptance cursor:

```text
current_gate = user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go
current_execution_gate = user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go
current_next_pr = none_until_user_scope_acceptance_or_external_path_b_design_input
current_gate_document = docs/fasim_gasal2_path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go.md
```

Historical post-exact-work-unit-external-design-choice cursor:

```text
current_gate = path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go
current_execution_gate = path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go
current_gate_document = docs/fasim_gasal2_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go.md
```

Historical post-exact-work-unit-new-design-spec cursor:

```text
current_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
current_execution_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
current_next_pr = fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
current_gate_document = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go.md
```

Historical post-exact-work-unit-consumer fork cursor:

```text
current_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
current_execution_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go.md
```

Historical pre-exact-work-unit-consumer cursor:

```text
current_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go
current_execution_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go
current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold.md
```

Historical pre-exact-work-unit-shadow cursor:

```text
current_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md
```

Historical pre-upper-bound-reject-shadow cursor:

```text
current_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
current_next_pr = fasim_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
current_gate_document = docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance.md
```

Historical pre-upper-bound-reject-spec cursor:

```text
current_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go
current_next_pr = fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go
current_gate_document = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go.md
```

Historical pre-post-native-DP-fork cursor:

```text
current_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go
current_gate_document = docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_no_go.md
```

Historical pre-native-DP-fork cursor:

```text
current_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
```

Historical pre-native-DP-consumer cursor:

```text
current_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
```

Historical pre-native-DP-shadow cursor:

```text
current_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
current_next_pr = fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
```

Historical pre-native-DP-spec cursor:

```text
current_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
current_next_pr = fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
```

Historical pre-consumer-no-go cursor:

```text
current_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go
```

Historical pre-scaffold cursor:

```text
current_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold
```

Historical pre-spec cursor:

```text
current_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
```

## Phase Completion Map

This is the short operational map. The detailed phase sections below preserve
the evidence, commands, and exact gate wording.

Primary closure-plan check:

```bash
make check-fasim-gasal2-roadmap-goal-closure-phase-plan
```

```text
Completion Path A: scoped product
  Use this path only if the user explicitly accepts the narrowed product:
    short-query/H19 top5 artifact
    MEG3-like complete-record grouping
    archive-first restored output where claimed

  Required phases:
    Phase 0: reproducible GASAL2/Fasim build
    Phase 1: scoped product contract accepted
    Phase 5: archive artifact can restore the claimed output
    Phase 6: workload matrix contains only clean claimed rows
    Phase 8: explicit scoped completion decision

  Result:
    goal may close as scoped completion, not broad aligner replacement.

Completion Path B: broad objective
  Use this path if the goal remains the original broad objective:
    materially accelerate or replace the scoreInfo/preAlign/Align-related
    path while preserving the required output contract.

  Required phases:
    Phase 0: reproducible GASAL2/Fasim build
    Phase 2: full-output equivalence-first baseline stays clean
    Phase 3: any pre-convert reducer must prove row-set safety before runtime
    Phase 6: workload matrix adds a passing broad_replacement row
    Phase 7: new architecture passes replay proof, then reduces both
      scoreInfo/preAlign work and Align-side work on a broad workload
    Phase 8: broad completion decision

  Result:
    goal may close as broad completion only after full row-set/digest equality,
    runtime win, fallback accounting, and CPU-authority verification pass.
```

Phase-by-phase execution:

```text
Phase 0 - Reproducibility
  Do:
    keep GASAL2 as a tracked, rebuildable dependency
    pin upstream commit, local patch, CUDA expectations, and build targets
  Output:
    clean checkout can rebuild the exact GASAL2 bridge
  Current state:
    ready
  Completion role:
    mandatory for both Path A and Path B

Phase 1 - Scoped Product Contract
  Do:
    define the short-query/top5/archive product surface and its non-claims
  Output:
    explicit scoped contract, default-off command, accepted artifact list
  Current state:
    acceptance packet defined; ready if user accepts narrowed scope
  Completion role:
    Path A gate only; cannot complete the broad objective by itself

Phase 2 - Full-Output Equivalence Baseline
  Do:
    keep restored TFOsorted/full-row delivery equivalence-first
  Output:
    chr22/chr1 restored row-set equality and convert/output timing
  Current state:
    ready
  Completion role:
    foundation for Path B and for any full-output claim

Phase 3 - Pre-Convert CPU Reduction
  Do:
    test only proof-first reducers that preserve the complete row set
  Output:
    missing rows = 0, extra rows = 0, task-frontier safety clean, faster
    convert wall than Phase 2
  Current state:
    current CIGAR NT prefilter is clean but performance no-go; keep default-off
  Completion role:
    useful for Path B only if it reduces CPU work without row drift

Phase 4 - Sort/Top-N Optimization
  Do:
    defer unless profiling shows sort/filter has become dominant
  Output:
    same comparator/tie behavior and materially lower sort/filter wall time
  Current state:
    not first priority
  Completion role:
    optional; does not complete the GPU/GASAL2 goal alone

Phase 5 - Archive Artifact
  Do:
    package the minimal reference-backed artifact and restore TFOsorted on demand
  Output:
    validated manifest, reference digests, restore command, restored equality
  Current state:
    ready
  Completion role:
    required for Path A archive delivery; useful output accelerator for Path B

Phase 6 - Workload Matrix
  Do:
    record every claim as claimed, unclaimed, blocked, fallback-heavy, or broad
  Output:
    no hidden overclaiming; broad_replacement rows only after broad gates pass
  Current state:
    claimed scoped rows only; broad objective still open
  Completion role:
    mandatory for both Path A and Path B

Phase 7 - Broad Restart
  Do:
    start from CPU-authority frontier logs, prove exact replay, then attempt
    reduction; do not let GASAL2 become endpoint/CIGAR/output authority
  Output:
    Gate A/Gate B CPU-authority reducer evidence, then Gate C or later broad
    gate with full equality, wall-time win, scoreInfo/preAlign reduction, and
    Align-side reduction
  Current state:
    current broad architecture no-go; Gate A/B are correctness-clean but near
    parity; Gate C current source is stopped; Phase 7 v3 seed/index path is
    stopped after oracle min-cover replay changed output; Phase 7 v4 source
    replay is correctness-clean but performance no-go; Phase 7 v5 fused
    scoreInfo consumer design is defined
  Completion role:
    required for original broad objective completion

Phase 8 - Completion Decision
  Do:
    close only when Path A is explicitly accepted or Path B passes
  Output:
    final decision with current-state gates rerun
  Current state:
    not complete without scoped user acceptance or broad gate pass
  Completion role:
    the only phase that may justify marking the active goal complete
```

## Current State

The original broad objective is not complete:

```text
Use GPU/GASAL2 to replace or materially accelerate the scoreInfo/preAlign /
Align-related Fasim path while preserving the required output contract.
```

The repository currently has real milestones:

```text
short-query/H19 top5 artifact:
  GASAL2/GPU active
  scoped contract clean
  strong speed signal

MEG3-like tiny-region grouping:
  complete-record grouping clean
  strong runtime win

GASAL2 archive/output compression:
  reference-backed archive can restore full TFOsorted
  archive size is small enough for downstream use

equivalence-first convert:
  full restored row-set clean on chr22 and chr1
  convert wall speedup around 1.79x
  full run speedup around 1.09x
```

The repository also has no-go boundaries:

```text
current GASAL2 scoreInfo broad long-query shape:
  no-go

current GPU score bridge:
  correctness clean but performance no-go

GASAL2 as direct aligner.Align replacement:
  not proven

GPU endpoint/CIGAR/traceback/output authority:
  not proven
```

## Completion Definitions

There are two possible completion definitions. They must not be mixed.

## How This Roadmap Completes The Goal

The active goal can close only through one of these explicit paths:

```text
Path A: scoped product accepted
  Phase 0 proves reproducibility.
  Phase 1 locks the short-query/top5/archive contract.
  Phase 5 proves the archive can restore TFOsorted on demand.
  Phase 6 proves every claimed workload passes its exact contract.
  Phase 8 records explicit user acceptance that this narrowed contract is the
    delivered goal.

Path B: broad objective proven
  Phase 0 proves reproducibility.
  Phase 2 preserves full output while reducing output/convert cost.
  Phase 3 or a later broad architecture reduces pre-convert/realpath CPU work
    without row drift.
  Phase 6 proves the claimed broad workload matrix.
  Phase 7 passes the broad restart gate: full row-set/digest equality, runtime
    better than CPU authority, and both scoreInfo/preAlign and Align-side work
    reduced or replaced.
  Phase 8 records broad completion.
```

Anything else is a milestone, not completion:

```text
top5-only speedup without scoped acceptance:
  useful milestone, not broad completion

archive/output compression without scoreInfo/preAlign or Align-side progress:
  useful milestone, not broad completion

GASAL2 launch success with output drift:
  diagnostic only

GPU endpoint/CIGAR/traceback/output authority without separate proof:
  forbidden for completion
```

Execution order:

```text
Phase 0:
  make the GASAL2 dependency reproducible.

Phase 1:
  decide whether the scoped product contract is acceptable.

Phase 2:
  keep full-output delivery equivalence-first and quantify remaining CPU cost.

Phase 3:
  only pursue pre-convert pruning with task-local frontier proof; the current
  nt-sum-span real prune is stopped.

Phase 4:
  defer sort/top-N work unless profiling shows it has become the dominant cost.

Phase 5:
  package archive-first output as a validated delivery artifact.

Phase 6:
  maintain a workload matrix that separates claimed, unclaimed, blocked, and
  fallback-heavy workloads.

Phase 7:
  restart broad GASAL2/Fasim replacement only with a narrower certificate or
  new architecture that can reduce both scoreInfo/preAlign and Align-side
  realpath work.

Phase 8:
  close the active goal only if Path A is explicitly accepted or Path B passes.
```

## Goal Completion Execution Ladder

This section is the operational checklist for moving the active goal forward.
The detailed phase sections below record evidence and commands; this ladder
defines what to do next, what qualifies as phase exit, and what must stop.

```text
Phase 0: Reproducibility foundation
  Current status:
    ready

  Purpose:
    Make every later claim rebuildable from a clean checkout.

  Next action:
    Keep the tracked GASAL2 patch, setup target, build target, CUDA version,
    SM arch, GASAL2_MAX_QUERY_LEN, and N_CODE pinned.

  Exit gate:
    make setup-gasal2
    make build-fasim-gasal2
    make check-fasim-gasal2-reproducible-setup
    make check-fasim-gasal2-equivalence-first-convert

  Stop condition:
    Any result depends on untracked .tmp/GASAL2 edits or a machine-local binary.

Phase 1: Scoped product contract
  Current status:
    ready if the user accepts the narrowed scope

  Purpose:
    Decide whether the current short-query/top5/archive product is allowed to
    count as goal completion.

  Next action:
    Present gasal2_top5_column_pruned_scoreinfo_artifact_v1 as a default-off
    scoped product. State explicitly that it is not aligner.Align replacement
    and not broad full-output replacement.

  Exit gate for Path A:
    user explicitly accepts scoped completion
    make check-fasim-gasal2-roadmap-phase1-scoped-product
    make check-fasim-gasal2-roadmap-phase5-archive-artifact
    make check-fasim-gasal2-roadmap-phase6-workload-matrix

  Stop condition:
    User requires broad full-output / aligner.Align replacement. In that case
    Path A cannot complete the goal; continue to Phase 7.

Phase 2: Full-output equivalence-first delivery
  Current status:
    ready as an authority-preserving output path

  Purpose:
    Keep the full TFOsorted path correct while reducing convert/output cost.

  Next action:
    Use equivalence-first convert and archive-first restore as the baseline
    for any full-output claim. Do not use output drift as speedup.

  Exit gate:
    chr22 and chr1 restored row-set equality remain clean
    convert/output timing is itemized

  Stop condition:
    Any speedup requires changing the restored row set or digest.

Phase 3: Pre-convert CPU reduction
  Current status:
    current nt-sum-span real prune is no-go

  Purpose:
    Reduce triplex/materialization work before expensive row construction,
    without changing the full output row set.

  Next action:
    Build only shadow or proof-first candidates:
      task-local frontier export
      full-mode task frontier comparison
      row-set equality against no-prune CPU authority

  Exit gate:
    missing rows = 0
    extra rows = 0
    task_frontier_safety = safe
    real_prune_proof_gate = pass
    chr22 and chr1 convert wall lower than Phase 2

  Stop condition:
    Any candidate changes the full row set, perturbs task-local top-N
    competition, or only proves top5 equality.

Phase 4: Sort/top-N optimization
  Current status:
    not first priority

  Purpose:
    Optimize row ordering only if sort/filter becomes a dominant cost.

  Next action:
    Defer real implementation. Keep parser/checker coverage so the decision
    can be revisited after Phase 3.

  Exit gate:
    same kept row set
    same comparator and tie behavior
    sort/filter wall is materially lower

  Stop condition:
    Partial selection changes tie behavior, unique behavior, or top-N boundary.

Phase 5: Archive artifact
  Current status:
    ready

  Purpose:
    Store the smallest sufficient artifact and restore TFOsorted on demand.

  Next action:
    Treat the archive as a delivery artifact for Path A and as a full-output
    acceleration component for Path B.

  Exit gate:
    archive manifest validates
    reference digests validate
    restore command is present
    restored output is byte-identical or row-set-identical for the claimed mode

  Stop condition:
    Archive omits information required to restore TFOsorted without rerunning
    Fasim.

Phase 6: Workload matrix
  Current status:
    claimed scoped workloads pass; broad objective remains open

  Purpose:
    Prevent accidental overclaiming by separating claimed, unclaimed, blocked,
    fallback-heavy, and broad-replacement rows.

  Next action:
    Add a matrix row for every new claim before calling it a milestone. A row
    may be claimed only for the exact contract it proves.

  Exit gate for Path A:
    all scoped claimed rows pass
    unclaimed and blocked rows remain explicit

  Exit gate for Path B:
    at least one broad_replacement claimed row passes with:
      row_equal = true
      speedup > 1.0
      fallbacks = 0
      scoreinfo_reduced = true
      align_side_reduced = true

  Stop condition:
    A fallback-heavy or output-drift workload is presented as GPU-fast-path
    clean.

Phase 7: Broad replacement restart
  Current status:
    current architecture no-go; Gate C current source stopped; Phase 7 v3
    seed/index path stopped after oracle min-cover replay changed output;
    Phase 7 v4 source replay first64 correctness clean but performance no-go

  Purpose:
    Complete the original broad goal, if scoped completion is not accepted.

  Next action:
    Use Path A scoped completion only if the user explicitly accepts that
    narrowed scope, or pursue Path B only with a different GPU execution
    design. Do not continue the current v4 source replay implementation as a
    broad path. Any new Path B attempt must keep CPU aligner.Align as semantic
    authority and must not add a broad_replacement row before first64 or
    equivalent broad evidence passes.

  Required sequence:
    1. NEAT1 first1 descriptor-source proof for a materially different source
       gpu/native candidate scoreInfos > 0
       gpu/native candidate attempts > 0
       cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
       candidate_certificate_false_negatives = 0
       missing_required_attempts = 0
       candidate attempts are narrower than all-column replay

    2. NEAT1 first1 CPU-authority replay
       digest or full row-set equality clean
       false_negative_scoreinfos = 0
       triplex_mismatches = 0
       candidate_align_attempts < reference_align_attempts

    3. NEAT1 first64 broad gate
       same correctness requirements as first1
       candidate_wall_seconds < baseline_wall_seconds
       candidate_vs_baseline > 1.0
       scoreInfo/preAlign work reduced
       Align-side attempts reduced or replaced

    4. Workload matrix update
       add contract=broad_replacement only if the NEAT1 first64 gate passes
       and the same-scope output contract is clean

  Forbidden shortcuts:
    GPU endpoint authority
    GPU CIGAR/traceback authority
    GASAL2 output/digest authority
    claiming broad completion from top5-only equality
    claiming broad completion from short-query bounded smoke

  Stop condition:
    NEAT1 remains slower than CPU baseline, false negatives appear, triplexes
    mismatch, CPU Align attempts are not reduced, or the candidate certificate
    expands to all-column/all-window replay scale.

Phase 8: Completion decision
  Current status:
    not complete without scoped user acceptance or broad gate pass

  Purpose:
    Close the active goal only when the documented completion contract is
    actually satisfied.

  Path A completion command:
    After explicit user acceptance of the scoped product, rerun Phase 0,
    Phase 1, Phase 5, Phase 6, and Phase 8 gates, then mark the goal complete
    as scoped completion.

  Path B completion command:
    After a broad_replacement matrix row passes Phase 7, rerun Phase 0 through
    Phase 8 current-state gates, then mark the goal complete as broad
    completion.

  Stop condition:
    If neither Path A nor Path B passes, keep:
      broad_objective_status = open
      must_not_call_update_goal_complete = 1
```

The shortest valid route to completion is Path A, but only if the user accepts
the narrowed scoped product. The only route to the original broad objective is
Path B through Phase 7; it requires NEAT1 first64 or equivalent broad evidence
that reduces both scoreInfo/preAlign work and Align-side work while preserving
the full claimed output contract.

### Scoped Product Completion

This is complete only if the project explicitly accepts a narrowed contract:

```text
Contract:
  short-query/H19 top5 artifact
  optional MEG3-like grouped tiny-region wrapper
  optional archive-first restored TFOsorted delivery

Non-contract:
  full aligner.Align replacement
  universal scoreInfo/preAlign replacement
  GPU endpoint/CIGAR/traceback authority
  broad MALAT1/NEAT1 long-query replacement
```

If this definition is accepted, completion means:

```text
default-off user-facing preset exists
contract artifacts are documented
full row-set or top5 artifact gates pass for the claimed scope
runtime command is reproducible
GASAL2 build is reproducible
failure modes fall back or fail closed
```

### Broad Objective Completion

This is complete only if a future architecture proves:

```text
full row-set equality or digest equality over the claimed workload scope
candidate wall time beats CPU authority
scoreInfo/preAlign and realpath Align-side work are both reduced or replaced
no GPU endpoint/CIGAR/traceback/output authority is used without separate proof
large workloads pass deterministic gates
```

For NEAT1-like broad long-query work, the minimum gate remains:

```text
NEAT1 first64:
  digest clean or full row-set equality clean
  triplex mismatches = 0
  scoreInfo mismatches = 0
  fallback = 0 for the claimed GPU path
  candidate_wall_seconds < CPU baseline
  candidate_vs_baseline > 1.0x
  realpath_extend_align_attempts materially reduced or replaced
```

## Phase Plan

### Phase 0: Freeze Evidence And Reproducibility

Goal:

```text
Make the current evidence reproducible from a clean checkout.
```

Do:

```text
track the GASAL2 patch used by Fasim
provide a setup/build target that clones, patches, and builds GASAL2
remove hard-coded local GASAL2 assumptions where possible
document CUDA version, SM arch, GASAL2_MAX_QUERY_LEN, and N_CODE
keep all GASAL2 paths default-off
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase0-reproducibility
make check-fasim-gasal2-reproducible-setup
make setup-gasal2
make build-fasim-gasal2
make check-fasim-gasal2-equivalence-first-convert
```

Exit:

```text
clean checkout can rebuild the binary and pass the small equivalence gate
```

Stop if:

```text
GASAL2 cannot be built reproducibly
local untracked GASAL2 edits are required
```

Current evidence:

```text
2026-06-12:
  dependency contract:
    repo = https://github.com/nahmedraja/GASAL2.git
    commit = 106d94ee53fc847214fb05f2f9f892538a5d3baf
    patch = patches/gasal2-fasim-bridge.patch
    setup = scripts/setup_gasal2.sh
    GASAL2_MAX_QUERY_LEN = 2812
    GASAL2_N_CODE = 0x4E
    include path = -I$(GASAL2_DIR)/include

  make check-fasim-gasal2-reproducible-setup: passed
    tracked GASAL2 patch is present
    setup script pins upstream repo and commit
    setup script applies the patch idempotently
    Makefile exposes setup-gasal2 and build-fasim-gasal2
    bridge does not hard-code ../.tmp/GASAL2 include paths

  make setup-gasal2:
    passed
    GASAL2 patch already applied from patches/gasal2-fasim-bridge.patch

  make build-fasim-gasal2:
    passed

  make check-fasim-gasal2-equivalence-first-convert:
    passed
    compare_mode = byte
    equivalence_first_active = 1
    restored_equal = 1
    legacy_only_rows = 0
    new_only_rows = 0
    legacy_restored_rows = 8,291
    new_restored_rows = 8,291
    convert_wall_speedup = 1.816168x
    run_wall_speedup = 1.103654x
```

### Phase 1: Lock The Scoped Product Contract

Goal:

```text
Define the accepted narrow product surface before more optimization.
```

Do:

```text
choose whether scoped product completion is acceptable
name the contract version
document required artifacts
document non-claims
document exact recommended command lines
```

Recommended scoped contract:

```text
gasal2_top5_column_pruned_scoreinfo_artifact_v1:
  runtime:
    default-off opt-in
    --gasal2-top5-column-pruned-scoreinfo
    --group-target-records 32 for MEG3-like tiny-region workloads

  topk_summary.tsv
  topk_rows.tsv
  topk-TFOsorted.lite
  report.json
  run_manifest.json

optional archive-first output:
  reference-backed TFO archive
  restore-on-demand TFOsorted
```

Scoped non-claims:

```text
full `.lite` output is not contract output
final all-row TFO equivalence is not claimed
not `aligner.Align()` replacement
not GPU endpoint/CIGAR/traceback authority
not broad production default
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase1-scoped-contract
make check-fasim-gasal2-roadmap-phase1-scoped-product
make check-fasim-gasal2-top5-recommended-runtime
make check-fasim-gasal2-top5-product-readiness
make check-fasim-gasal2-top5-scoped-completion-candidate
make check-fasim-gasal2-top5-release-smoke
make check-fasim-gasal2-scoreinfo-scoped-release-smoke
make check-fasim-gasal2-scoreinfo-scoped-milestone-rollup
make check-fasim-gasal2-full-goal-decision
```

Exit:

```text
the accepted contract is explicit
the full objective remains marked open unless the user accepts scoped completion
```

Stop if:

```text
the required user-facing output is full TFOsorted equivalence over broad workloads
and not only top5/short-query artifacts
```

Current evidence:

```text
2026-06-12:
  make check-fasim-gasal2-top5-release-smoke:
    passed
    formal_preset_example = meg3_first32
    formal_preset_topk_artifact_match = true
    formal_preset_gasal2_requests = 63,035
    formal_preset_exact_scoreinfo_gpu_tasks = 1,536
    formal_preset_speedup_vs_cpu_worker_wall_sum = 0.309218x
    interpretation = contract smoke, not a performance claim

  make check-fasim-gasal2-scoreinfo-scoped-release-smoke:
    passed
    MALAT1 first8 lite:
      rows = 796
      candidate_vs_baseline = 0.985431x
      two_contract_used = 1,824
      probe_positive_numeric_keys = 0
    MALAT1 first8 TFOsorted:
      rows = 796
      candidate_vs_baseline = 0.991316x
      two_contract_used = 1,824
      probe_positive_numeric_keys = 0
    interpretation = scoped correctness/product-readiness boundary, not a
      strong performance claim

  make check-fasim-gasal2-scoreinfo-scoped-milestone-rollup:
    passed

  make check-fasim-gasal2-roadmap-phase1-scoped-product:
    passed
    phase1_scoped_product_gate = ready_if_user_accepts_scope
    phase1_scoped_contract = pass
    top5_recommended_runtime = pass
    top5_product_readiness = pass
    top5_scoped_completion_candidate = pass
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make check-fasim-gasal2-full-goal-decision:
    passed
    full objective remains open unless scoped completion is explicitly accepted

  make check-fasim-gasal2-top5-recommended-runtime:
    passed
    recommended runtime is default-off opt-in
    recommended preset = --gasal2-top5-column-pruned-scoreinfo
    grouped tiny-region add-on = --group-target-records 32
    recommended artifacts = topk_summary.tsv, topk_rows.tsv,
      topk-TFOsorted.lite, report.json, run_manifest.json
    non-claims include full `.lite`, final all-row TFO, aligner.Align,
      endpoint/CIGAR/traceback, and broad production default

  make check-fasim-gasal2-top5-product-readiness:
    passed
    scoped output contract =
      gasal2_top5_column_pruned_scoreinfo_artifact_v1
    scoped product status = product-readiness candidate
    full objective remains open

  make check-fasim-gasal2-top5-scoped-completion-candidate:
    passed
    scoped_product_status = ready_if_user_accepts_scope
    full objective remains open unless the user accepts scoped completion

  docs/fasim_gasal2_path_a_scoped_completion_acceptance.md:
    path_a_scoped_completion_acceptance_packet = defined
    path_a_scoped_completion_status = ready_if_user_accepts_scope
    user_scope_acceptance_recorded = 0
    scoped_completion_may_close_goal = 0
    contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1
    runtime = default-off opt-in
    primary preset = --gasal2-top5-column-pruned-scoreinfo
    tiny-region add-on = --group-target-records 32
    accepted artifacts:
      topk_summary.tsv
      topk_rows.tsv
      topk-TFOsorted.lite
      report.json
      run_manifest.json
      reference-backed TFO archive where archive-first delivery is claimed
    non-claims:
      not broad aligner.Align replacement
      not universal scoreInfo/preAlign replacement
      not long-query NEAT1/MALAT1 GASAL2 production path
      not GPU endpoint/CIGAR/traceback authority
    required acceptance gates:
      make check-fasim-gasal2-roadmap-phase0-reproducibility
      make check-fasim-gasal2-roadmap-phase1-scoped-product
      make check-fasim-gasal2-roadmap-phase5-archive-artifact
      make check-fasim-gasal2-roadmap-phase6-workload-matrix
      make check-fasim-gasal2-roadmap-phase8-completion-decision
      make check-fasim-gasal2-roadmap-current-state
    broad_objective_status = open
    must_not_call_update_goal_complete = 1
```

### Phase 2: Make Full Output Delivery Cheap Enough

Goal:

```text
Reduce CPU-side output/convert cost without changing row semantics.
```

Current evidence:

```text
chr22:
  restored row-set equal
  convert wall speedup around 1.79x
  run wall speedup around 1.10x

chr1:
  restored row-set equal
  convert wall speedup around 1.79x
  run wall speedup around 1.09x
```

Do next:

```text
keep equivalence-first convert as the authority-preserving path
measure post-convert CPU time more finely
separate binary archive write, text restore, sort/unique/filter, and row build
avoid more archive compression unless restore/output time is still material
```

Gate:

```bash
make check-fasim-gasal2-convert-cpu-breakdown
make check-fasim-gasal2-roadmap-phase2-equivalence-first-convert
COMPARE_MODE=set TARGET=<chr22.fa> make check-fasim-gasal2-equivalence-first-convert
COMPARE_MODE=set TARGET=<chr1.fa> make check-fasim-gasal2-equivalence-first-convert
```

Exit:

```text
full restored row-set equality remains clean
convert/output bottleneck is quantified after equivalence-first convert
```

Stop if:

```text
row-set equality fails
large workload speedup only comes from changing output semantics
```

Current evidence:

```text
2026-06-12:
  make check-fasim-gasal2-convert-cpu-breakdown:
    passed
    verifies convert wall, selected-scan, triplex/alignment, span-check,
    sort, filter, rank-map, output write, output close, query release, and
    throughput telemetry are present and non-negative on the small fixture

  make check-fasim-gasal2-roadmap-phase2-equivalence-first-convert:
    passed
    phase2_equivalence_first_convert_gate = ready
    convert_cpu_breakdown = pass
    equivalence_first_convert = pass
    restored_equal = 1
    legacy_only_rows = 0
    new_only_rows = 0
    convert_wall_speedup_gt_1 = 1

  chr22 full:
    command = COMPARE_MODE=set TARGET=<chr22.fa> make
      check-fasim-gasal2-equivalence-first-convert
    passed
    equivalence_first_active = 1
    restored_equal = 1
    legacy_only_rows = 0
    new_only_rows = 0
    legacy_restored_rows = 388,821
    new_restored_rows = 388,821
    legacy_convert_wall_seconds = 15.1821
    new_convert_wall_seconds = 8.52321
    convert_wall_speedup = 1.781266x
    legacy_run_wall_seconds = 77.125211
    new_run_wall_seconds = 70.527429
    run_wall_speedup = 1.093549x

  chr1 full:
    command = COMPARE_MODE=set TARGET=<chr1.fa> make
      check-fasim-gasal2-equivalence-first-convert
    passed
    equivalence_first_active = 1
    restored_equal = 1
    legacy_only_rows = 0
    new_only_rows = 0
    legacy_restored_rows = 1,577,067
    new_restored_rows = 1,577,067
    legacy_convert_wall_seconds = 83.9617
    new_convert_wall_seconds = 47.2191
    convert_wall_speedup = 1.778130x
    legacy_run_wall_seconds = 435.288909
    new_run_wall_seconds = 398.655682
    run_wall_speedup = 1.091892x
```

### Phase 3: Reduce Pre-Convert CPU Work

Goal:

```text
Reduce the number of alignments that enter triplex conversion while preserving
the full output row set for the claimed scope.
```

Why:

```text
chr1 equivalence-first still scans about 37.9 million alignments
about 1.58 million rows survive
triplex conversion remains a major CPU-side cost
```

Do:

```text
add shadow-only counters for pre-convert reject reasons
prototype cheap pre-convert filters only in shadow mode
compare full restored row sets against CPU authority
record missing and extra rows
```

Phase 3 baseline tool:

```bash
make check-fasim-gasal2-convert-funnel-parser
make check-fasim-gasal2-roadmap-phase3-preconvert-prune
make check-fasim-gasal2-roadmap-phase3-cigar-nt-prefilter-design
make check-fasim-gasal2-phase3-cigar-nt-prefilter-shadow
make characterize-fasim-gasal2-phase3-cigar-nt-prefilter-full
make check-fasim-gasal2-phase3-cigar-nt-prefilter-full-result
make check-fasim-gasal2-preconvert-prune-shadow
make check-fasim-gasal2-prune-authority-diff-parser
make check-fasim-gasal2-prune-frontier-safety-parser
make check-fasim-gasal2-preconvert-prune-readiness
make check-fasim-gasal2-task-frontier-proof-parser
make check-fasim-gasal2-task-frontier-proof-export
python3 scripts/parse_fasim_gasal2_convert_funnel.py \
  --stderr <fasim-stderr.log> \
  --label <workload>
python3 scripts/analyze_fasim_gasal2_prune_authority_diff.py \
  --baseline <no-prune-restored-TFOsorted> \
  --candidate <prune-restored-TFOsorted>
python3 scripts/analyze_fasim_gasal2_prune_frontier_safety.py \
  --baseline <no-prune-restored-TFOsorted> \
  --candidate <prune-restored-TFOsorted> \
  --frontier-key chrom_strand_rule
python3 scripts/analyze_fasim_gasal2_task_frontier_proof.py \
  --baseline <no-prune-broad_cpu_triplex.tsv> \
  --candidate <candidate-prune-broad_cpu_triplex.tsv>
```

This parser summarizes existing post-convert funnel telemetry. It does not
change runtime behavior and does not prove a pruning strategy by itself.
The frontier safety analyzer is a proof gate: a real prune candidate must keep
the same rows inside the chosen legacy competition bucket before it can be
considered safe.
The task frontier proof analyzer is stricter for pre-convert pruning: it
compares the complete broad CPU triplex export grouped by `task_index`, so a
candidate must preserve each task-local legacy frontier before it can change
runtime pruning behavior.

The pre-convert prune shadow gate enables:

```text
FASIM_ALIGN_GASAL2_PRECONVERT_PRUNE_SHADOW=1
```

This is diagnostic only. It must not enable
`FASIM_ALIGN_GASAL2_NT_SUM_SPAN_PRUNE`, must not skip conversion, and must
report false negatives before any real pruning path is considered.

Candidate filters:

```text
impossible nt range
impossible span/range
known below-threshold score/stability when derivable without full row build
duplicate candidate identity before expensive materialization
```

Forbidden:

```text
no filter may become real until row-set equality is clean
no top5-only equality may be used as full-output proof
no GPU endpoint/CIGAR/traceback authority
```

Gate:

```text
chr22 full:
  full row-set equality clean
  missing rows = 0
  extra rows = 0
  convert wall lower than Phase 2

chr1 full:
  full row-set equality clean
  missing rows = 0
  extra rows = 0
  convert wall lower than Phase 2
```

Exit:

```text
safe pre-convert pruning reduces CPU conversion work without output drift
```

Stop if:

```text
any pre-convert filter changes full row set
the filter only helps top5 but not the accepted output contract
```

Current evidence:

```text
2026-06-12:
  make check-fasim-gasal2-convert-funnel-parser:
    passed

  make check-fasim-gasal2-roadmap-phase3-preconvert-prune:
    passed
    phase3_preconvert_prune_gate = not_ready_current_prune_no_go
    convert_funnel_parser = pass
    preconvert_prune_shadow = pass
    preconvert_prune_readiness = pass
    task_frontier_proof_parser = pass
    task_frontier_proof_export = pass
    current_real_prune_decision = no_go
    real_prune_may_be_enabled = 0
    next_required_gate = task_local_frontier_full_mode_proof

  make check-fasim-gasal2-prune-frontier-safety-parser:
    passed
    supports full row-set comparison and diff-only risk analysis

  make check-fasim-gasal2-preconvert-prune-shadow:
    passed
    restored output path remains equivalence-first
    real nt-sum-span prune active = 0
    preconvert_prune_shadow_requested = 1
    preconvert_prune_shadow_active = 1
    preconvert_prune_shadow_attempts = 25,673
    preconvert_prune_shadow_false_negatives = 0
    preconvert_prune_shadow_attempts_per_input_alignment = 0.146541
    preconvert_prune_shadow_false_negative_rate = 0.000000

  chr22 full pre-convert shadow characterization:
    command = COMPARE_MODE=set TARGET=<chr22.fa>
      FASIM_ALIGN_GASAL2_PRECONVERT_PRUNE_SHADOW=1 make
      check-fasim-gasal2-equivalence-first-convert
    passed
    restored_equal = 1
    legacy_only_rows = 0
    new_only_rows = 0
    legacy_restored_rows = 388,821
    new_restored_rows = 388,821
    real nt-sum-span prune active = 0
    preconvert_prune_shadow_requested = 1
    preconvert_prune_shadow_active = 1
    preconvert_prune_shadow_attempts = 993,703
    preconvert_prune_shadow_false_negatives = 0
    preconvert_prune_shadow_attempts_per_input_alignment = 0.143798
    preconvert_prune_shadow_false_negative_rate = 0.000000
    convert_wall_speedup = 1.786883x
    run_wall_speedup = 1.094961x

  real nt-sum-span prune authority check:
    command = FASIM_ALIGN_GASAL2_NT_SUM_SPAN_PRUNE=1 make
      check-fasim-gasal2-equivalence-first-convert
    same-config legacy/equivalence comparison = clean
    no-prune authority comparison = not clean
    no-prune restored rows = 8,291 data rows
    prune restored rows = 8,289 data rows
    decision = real prune no-go
    interpretation = the sum-span shadow is useful for opportunity accounting,
      but the current real prune changes the output row set and must not be
      promoted. Phase 3 must continue with a stricter shadow candidate, not the
      existing nt-sum-span real pruning flag.

  nt-sum-span authority diff analysis:
    command = python3 scripts/analyze_fasim_gasal2_prune_authority_diff.py
      --baseline <no-prune-restored-TFOsorted>
      --candidate <prune-restored-TFOsorted>
    baseline_rows = 8,292 including header
    candidate_rows = 8,290 including header
    baseline_only_rows = 3
    candidate_only_rows = 1
    row_set_equal = 0
    baseline_only_nt_range = 52..64
    candidate_only_nt_range = 109..109
    baseline_only_sum_span_range = 99..127
    candidate_only_sum_span_range = 210..210
    cross_overlap_pairs = 0
    cross_overlap_max_bp = 0
    cross_overlap_same_rule_pairs = 0
    baseline_only_rule_count = 3
    candidate_only_rule_count = 1
    shared_rule_count = 0
    min_cross_distance_bp = 254,209
    interpretation = pruning changes the task-local sort/unique/top-N surface,
      not merely the final low-nt filtered rows. The extra candidate does not
      genomically overlap the missing authority rows, shares no rule bucket
      with them, and is at least 254,209 bp away. The current prune can perturb
      distant top-N competition rather than just replace a local row. A future
      Phase 3 candidate must prove the kept row set is unchanged after legacy
      sort/unique/top-N, not only that pruned alignments have no direct
      emitted-row false negatives.

  nt-sum-span frontier safety analysis:
    command = python3 scripts/analyze_fasim_gasal2_prune_frontier_safety.py
      --baseline-only <no_prune_only_rows.txt>
      --candidate-only <prune_only_rows.txt>
      --frontier-key rule
    input_mode = diff_only
    baseline_only_rows = 3
    candidate_only_rows = 1
    row_set_equal = 0
    frontier_safety = unsafe
    frontier_changed_buckets = 3
    frontier_shared_changed_buckets = 1
    frontier_baseline_only_buckets = 2
    frontier_candidate_only_buckets = 0
    first_frontier_changed_bucket = 4

    command = python3 scripts/analyze_fasim_gasal2_prune_frontier_safety.py
      --baseline-only <no_prune_only_rows.txt>
      --candidate-only <prune_only_rows.txt>
      --frontier-key chrom_strand_rule
    input_mode = diff_only
    row_set_equal = 0
    frontier_safety = unsafe
    frontier_changed_buckets = 4
    frontier_shared_changed_buckets = 0
    frontier_baseline_only_buckets = 3
    frontier_candidate_only_buckets = 1
    interpretation = the current nt-sum-span real prune fails even a
      frontier-risk gate. A future real prune must provide full-mode
      frontier_safety=safe on the chosen competition key, not just diff-only
      accounting after a known mismatch.

  Phase 3 decision after nt-sum-span no-go:
    existing real pre-convert nt-sum-span prune = stop
    acceptable continuation =
      1. task-local frontier export/proof before any pre-convert pruning, or
      2. move the optimization later, after legacy sort/unique/top-N, where the
         kept row set is already known
    not acceptable =
      enabling FASIM_ALIGN_GASAL2_NT_SUM_SPAN_PRUNE as a runtime recommendation

  make check-fasim-gasal2-preconvert-prune-readiness:
    passed
    current_real_prune_decision = no_go
    current_real_prune_row_set_equal = 0
    current_real_prune_baseline_only_rows = 3
    current_real_prune_candidate_only_rows = 1
    current_real_prune_frontier_safety = unsafe
    future_frontier_full_mode_safety = safe
    future_frontier_full_mode_required = 1
    diff_only_frontier_is_sufficient = 0
    next_required_gate = task_local_frontier_full_mode_proof
    real_prune_may_be_enabled = 0

  interpretation:
    The current nt-sum-span real prune remains a no-go. Diff-only frontier
    analysis is useful for explaining a known mismatch, but it is not a proof
    gate for enabling a real prune. A future candidate must provide a
    full-mode task-local frontier proof with row_set_equal=1 and
    frontier_safety=safe before any runtime pruning flag can be recommended.

  make check-fasim-gasal2-task-frontier-proof-parser:
    passed
    safe synthetic case:
      input_mode = task_triplex_full
      baseline_rows = 3
      candidate_rows = 3
      task_row_set_equal = 1
      task_frontier_safety = safe
      task_count = 2
      changed_tasks = 0
      real_prune_proof_gate = pass

    unsafe synthetic case:
      input_mode = task_triplex_full
      baseline_rows = 3
      candidate_rows = 2
      task_row_set_equal = 0
      task_frontier_safety = unsafe
      changed_tasks = 1
      baseline_only_rows = 1
      candidate_only_rows = 0
      first_changed_task = 1
      real_prune_proof_gate = fail

    interpretation:
      The proof gate now exists independently of final TFO row sorting. A
      future pre-convert prune candidate must produce matching
      broad_cpu_triplex.tsv task frontiers with real_prune_proof_gate=pass
      before any real pruning path can be enabled or recommended.

  make check-fasim-gasal2-task-frontier-proof-export:
    passed
    real export workload = NEAT1 first1 / max_tasks=1
    broad_path_cpu_triplexes = 60
    real export same-file proof:
      input_mode = task_triplex_full
      task_row_set_equal = 1
      task_frontier_safety = safe
      changed_tasks = 0
      real_prune_proof_gate = pass
    real export one-row-removed proof:
      input_mode = task_triplex_full
      task_row_set_equal = 0
      task_frontier_safety = unsafe
      baseline_only_rows = 1
      candidate_only_rows = 0
      real_prune_proof_gate = fail

    interpretation:
      The task-local frontier analyzer now accepts a real exported
      broad_cpu_triplex.tsv artifact, not only synthetic rows. This proves the
      Phase 3 proof gate is wired to the runtime export schema. It still does
      not make the current nt-sum-span real prune safe; a future prune
      candidate must produce its own candidate broad_cpu_triplex.tsv and pass
      this full task-local frontier gate before any runtime pruning flag can
      be recommended.

  make check-fasim-gasal2-roadmap-phase3-cigar-nt-prefilter-design:
    passed
    phase3_cigar_nt_prefilter_design_gate = defined
    candidate = cigar_nt_prefilter
    requires_shadow_first = 1
    requires_disagree_lt_ntmin_zero = 1
    requires_candidate_false_negative_rows_zero = 1
    requires_task_frontier_safety_safe = 1
    requires_real_prune_proof_gate_pass = 1
    current_nt_sum_span_prune_status = no_go
    real_prune_may_be_enabled = 0
    phase3 next implementation = CIGAR NT prefilter shadow proof

    interpretation:
      The next Phase 3 candidate is deliberately narrower than the stopped
      nt-sum-span real prune. It may only start as a shadow proof that compares
      CIGAR aligned length against legacy converted nt behavior while still
      running legacy conversion. It cannot become a real prune unless
      disagree_lt_ntmin, candidate false-negative rows, and task-local frontier
      differences are all zero on the claimed full-output workloads.

  make check-fasim-gasal2-phase3-cigar-nt-prefilter-shadow:
    passed
    phase3_cigar_nt_prefilter_shadow_gate = proof_smoke_clean
    workload = NEAT1 first1 / max_tasks=1
    phase3_cigar_nt_prefilter_requested = 1
    phase3_cigar_nt_prefilter_active = 1
    phase3_cigar_nt_prefilter_alignments_seen = 718
    phase3_cigar_nt_prefilter_cigar_lt_ntmin = 53
    phase3_cigar_nt_prefilter_legacy_nt_lt_ntmin = 53
    phase3_cigar_nt_prefilter_disagree_lt_ntmin = 0
    phase3_cigar_nt_prefilter_candidate_false_negative_rows = 0
    phase3_cigar_nt_prefilter_task_frontier_equal = 1
    phase3_cigar_nt_prefilter_task_frontier_safety = safe
    phase3_cigar_nt_prefilter_real_prune_proof_gate = pass
    candidate_triplex_digest = 2d9064122f520fe9

    interpretation:
      The CIGAR NT prefilter shadow now covers the long-query realpath
      conversion path and produces a task-frontier candidate artifact. This is
      a wiring and small-proof smoke only. It does not enable a real prune and
      does not satisfy the chr22/chr1 full-output gate required for runtime
      recommendation.

  make characterize-fasim-gasal2-phase3-cigar-nt-prefilter-full:
    passed

  make check-fasim-gasal2-phase3-cigar-nt-prefilter-full-result:
    passed
    phase3_cigar_nt_prefilter_full_characterization = pass

    chr22 full:
      target = .tmp/fasim_rule0_chr22_full_gasal2_gpu_score/input/chr22.fa
      alignments_seen = 6,910,419
      cigar_lt_ntmin = 493,935
      legacy_nt_lt_ntmin = 493,935
      disagree_lt_ntmin = 0
      candidate_false_negative_rows = 0
      broad_cpu_triplexes = 824,153
      task_frontier_safety = safe
      real_prune_proof_gate = pass
      convert_wall_seconds = 13.1799
      projected_saved_seconds = 0.805121
      projected_saved_fraction = 0.061087

    chr1 full:
      target = .tmp/fasim_gasal2_chr1_full_input/chr1.fa
      alignments_seen = 37,949,280
      cigar_lt_ntmin = 2,771,080
      legacy_nt_lt_ntmin = 2,771,080
      disagree_lt_ntmin = 0
      candidate_false_negative_rows = 0
      broad_cpu_triplexes = 3,385,713
      task_frontier_safety = safe
      real_prune_proof_gate = pass
      convert_wall_seconds = 70.594
      projected_saved_seconds = 4.45219
      projected_saved_fraction = 0.063068

    interpretation:
      The CIGAR NT prefilter full-workload proof is correctness-clean on
      chr22 and chr1. It is much safer than the stopped nt-sum-span prune, but
      the projected saved conversion work is only about 6.1-6.3% of current
      convert wall. This is not a runtime win claim and does not justify
      default enablement. A real default-off prototype is only worth doing if
      validation remains exact and measured wall time actually improves.

  make check-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate:
    passed
    workload = H19 / chr22 10Mb-12Mb slice
    requested = 1
    active = 1
    real_requested = 1
    real_active = 1
    real_validate_requested = 1
    real_validate_active = 1
    real_skipped_alignments = 12,574
    real_validated_skips = 12,574
    real_validate_mismatches = 0
    real_fallbacks = 0
    real_decision = validated_clean
    restored_equal = 1
    legacy_only_rows = 0
    candidate_only_rows = 0
    baseline_rows = 8,291
    real_validate_rows = 8,291

    interpretation:
      The default-off real CIGAR NT prefilter prototype is now wired in
      fail-closed validate mode for the current convert path. This is a smoke
      gate, not a runtime recommendation. It proves that the real skip can
      remove candidate conversions while validation preserves the restored row
      set on a small H19/chr22 slice. Because the full shadow proof projected
      only about 6.1-6.3% convert-wall savings, the next decision must be based
      on measured chr22/chr1 real-validate characterization before any
      recommendation.

  make characterize-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate-full:
    passed

  make check-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate-full-result:
    passed
    phase3_cigar_nt_prefilter_real_validate_full_characterization = pass

    chr22 full:
      target = .tmp/fasim_rule0_chr22_full_gasal2_gpu_score/input/chr22.fa
      restored_equal = 1
      legacy_only_rows = 0
      candidate_only_rows = 0
      baseline_rows = 388,821
      real_validate_rows = 388,821
      real_skipped_alignments = 493,934
      real_validated_skips = 493,934
      real_validate_mismatches = 0
      real_fallbacks = 0
      real_decision = validated_clean
      baseline_run_wall_seconds = 69.779004
      real_validate_run_wall_seconds = 70.396690
      run_wall_speedup = 0.991226
      baseline_convert_wall_seconds = 8.47075
      real_validate_convert_wall_seconds = 9.15482
      convert_wall_speedup = 0.925278
      decision = real_validate_clean_no_speedup

    chr1 full:
      target = .tmp/fasim_gasal2_chr1_full_input/chr1.fa
      restored_equal = 1
      legacy_only_rows = 0
      candidate_only_rows = 0
      baseline_rows = 1,577,067
      real_validate_rows = 1,577,067
      real_skipped_alignments = 2,771,079
      real_validated_skips = 2,771,079
      real_validate_mismatches = 0
      real_fallbacks = 0
      real_decision = validated_clean
      baseline_run_wall_seconds = 396.600376
      real_validate_run_wall_seconds = 400.166834
      run_wall_speedup = 0.991088
      baseline_convert_wall_seconds = 47.3253
      real_validate_convert_wall_seconds = 51.4659
      convert_wall_speedup = 0.919547
      decision = real_validate_clean_no_speedup

    interpretation:
      The real CIGAR NT prefilter is correctness-clean in fail-closed validate
      mode on chr22 and chr1 full workloads. It preserves restored output
      exactly and has zero validation mismatches or fallbacks. However, it is
      slower than baseline: convert wall is about 0.92x baseline and run wall
      is about 0.991x baseline. The projected shadow savings were too small to
      overcome validation and branch overhead. This path should remain
      default-off and should not be recommended as a runtime optimization.

  chr22 equivalence-first funnel:
    convert_input_alignments = 6,910,419
    convert_triplexes_raw = 6,416,486
    emit_candidates = 824,152
    emit_rows = 388,821
    post_convert_filtered_total = 435,331
    emit_filtered_nt = 435,331
    triplexes_per_input_alignment = 0.928523
    rows_per_input_alignment = 0.056266
    post_convert_filtered_per_candidate = 0.528217
    selected_scan_share = 0.838026
    triplex_share = 0.774957
    sort_share = 0.111562
    filter_share = 0.035181

  chr1 equivalence-first funnel:
    convert_input_alignments = 37,949,280
    convert_triplexes_raw = 35,178,196
    emit_candidates = 3,385,713
    emit_rows = 1,577,067
    post_convert_filtered_total = 1,808,646
    emit_filtered_nt = 1,808,646
    triplexes_per_input_alignment = 0.926979
    rows_per_input_alignment = 0.041557
    post_convert_filtered_per_candidate = 0.534199
    selected_scan_share = 0.841988
    triplex_share = 0.779621
    sort_share = 0.109481
    filter_share = 0.032473

  interpretation:
    more than half of emitted candidates are removed by the nt filter after
    conversion, while selected scan and triplex build still dominate convert
    wall. The next Phase 3 implementation should test the CIGAR NT prefilter
    shadow proof and prove full row-set equality before any real pruning path
    is enabled.
```

### Phase 4: Optimize Row Ordering, Unique, And Top-N

Goal:

```text
Reduce row-set processing overhead without changing legacy ordering/filter
semantics.
```

Do:

```text
measure the three sort/unique phases separately
build a shadow partial-selection prototype if N is much smaller than row count
compare against the exact legacy sort/unique/top-N result
keep legacy comparators as the reference
```

Phase 4 baseline tool:

```bash
make check-fasim-gasal2-roadmap-phase4-sort-topn
make check-fasim-gasal2-convert-cpu-breakdown
make check-fasim-gasal2-sort-topn-breakdown-parser
python3 scripts/parse_fasim_gasal2_sort_topn_breakdown.py \
  --stderr <fasim-stderr.log> \
  --label <workload>
```

This parser summarizes the current nested convert telemetry. The selected scan
timer is inclusive: span check, triplex materialization, and rank-map work are
sub-timers within that scan. The parser does not treat those timers as
mutually exclusive wall slices, and it still does not split the three legacy
sort/unique phases.

Gate:

```text
same kept row set
same digest or sorted row-set equality
sort/filter wall lower than Phase 2 or Phase 3
no comparator/tie-policy drift
```

Exit:

```text
row processing is no longer a meaningful CPU bottleneck or is safely improved
```

Stop if:

```text
partial selection changes ties
same-row unique behavior differs
top-N boundary differs
```

Current evidence:

```text
2026-06-12:
  make check-fasim-gasal2-roadmap-phase4-sort-topn:
    passed
    phase4_sort_topn_gate = not_first_priority
    dominant_convert_stage = triplex_materialization
    sort_topn_first_priority = 0
    cpu_breakdown_decision =
      triplex_materialization_or_preconvert_frontier_first

  make check-fasim-gasal2-sort-topn-breakdown-parser:
    passed
    parser now reports selected-scan, span-check, triplex/alignment, rank-map,
    sort, filter, sort+filter, selected-scan-minus-known-children,
    accounted/unattributed convert wall, dominant convert stage, and a
    first-priority decision for sort/top-N versus triplex/pre-convert work

  chr22 equivalence-first:
    convert_triplexes_raw = 6,416,486
    emit_candidates = 824,152
    emit_rows = 388,821
    selected_scan_seconds = 7.098580
    span_check_seconds = 0.174802
    triplex_seconds = 6.564320
    alignment_seconds = 6.564320
    sort_seconds = 0.950868
    filter_seconds = 0.299851
    rank_map_seconds = 0.000000
    sort_filter_seconds = 1.250719
    selected_scan_minus_children_seconds = 0.359458
    convert_accounted_seconds = 8.349299
    convert_unattributed_seconds = 0.123911
    selected_scan_share = 0.838523
    span_check_share = 0.020649
    triplex_share = 0.775413
    alignment_share = 0.775413
    selected_scan_minus_children_share = 0.042461
    convert_unattributed_share = 0.014624
    sort_share = 0.111562
    filter_share = 0.035181
    sort_filter_share = 0.146743
    triplex_to_sort_filter_ratio = 5.248436
    dominant_convert_stage = triplex_materialization
    sort_topn_first_priority = 0
    cpu_breakdown_decision = triplex_materialization_or_preconvert_frontier_first
    rows_per_raw_triplex = 0.060597
    raw_triplexes_per_output_row = 16.502416

  chr1 equivalence-first:
    convert_triplexes_raw = 35,178,196
    emit_candidates = 3,385,713
    emit_rows = 1,577,067
    selected_scan_seconds = 39.589800
    span_check_seconds = 0.951609
    triplex_seconds = 36.654000
    alignment_seconds = 36.654000
    sort_seconds = 5.169590
    filter_seconds = 1.533350
    rank_map_seconds = 0.000000
    sort_filter_seconds = 6.702940
    selected_scan_minus_children_seconds = 1.984191
    convert_accounted_seconds = 46.292740
    convert_unattributed_seconds = 0.926360
    selected_scan_share = 0.842736
    span_check_share = 0.020257
    triplex_share = 0.780243
    alignment_share = 0.780243
    selected_scan_minus_children_share = 0.042237
    convert_unattributed_share = 0.019617
    sort_share = 0.109481
    filter_share = 0.032473
    sort_filter_share = 0.141954
    triplex_to_sort_filter_ratio = 5.468345
    dominant_convert_stage = triplex_materialization
    sort_topn_first_priority = 0
    cpu_breakdown_decision = triplex_materialization_or_preconvert_frontier_first
    rows_per_raw_triplex = 0.044831
    raw_triplexes_per_output_row = 22.306088

  interpretation:
    selected scan is inclusive and remains about 84% of convert wall, with
    triplex/alignment materialization about 78% of convert wall on chr22/chr1.
    Aggregate sort/filter is about 14-15% of convert wall. This is measurable,
    but triplex/materialization is about 5.2-5.5x larger than sort/filter and
    the dominant_convert_stage is triplex_materialization on both chr22 and
    chr1. A risky partial top-N optimization is not the first priority. The
    next CPU-side work should target triplex materialization volume through
    task-local frontier proof or move pruning later after legacy sort/unique/
    top-N has already fixed the kept row set.
```

### Phase 5: Productize Archive As A First-Class Artifact

Goal:

```text
Allow downstream workflows to consume the smallest sufficient artifact and
restore TFOsorted only when needed.
```

Do:

```text
define archive schema version
record query/target reference digests
record restore command and required references
add archive integrity checks
measure restore wall separately from Fasim run wall
```

Gate:

```bash
make check-fasim-tfo-archive-integrity-parser
make check-fasim-gasal2-archive-manifest-parser
make check-fasim-gasal2-archive-first-output
make check-fasim-gasal2-roadmap-phase5-archive-artifact
```

```text
archive restores byte-identical or row-set-identical TFOsorted for claimed mode
archive can be validated without rerunning Fasim
downstream TFO/TFOsorted consumer can use restored output unchanged
```

Exit:

```text
archive is safe as a delivery artifact
text generation is on-demand rather than mandatory fast path
```

Stop if:

```text
archive cannot restore exact output
archive omits required information for downstream TFOsorted recovery
```

Current evidence:

```text
2026-06-12:
  make check-fasim-tfo-archive-integrity-parser:
    passed
    validates FATFOC1 magic, archive version, terminator, query/target
    digests, restored output digest, restored rows, dictionary payload count,
    and byte sizes from a synthetic archive

  make check-fasim-gasal2-archive-manifest-parser:
    passed
    validates FASIM_TFO_ARCHIVE_MANIFEST_V1 schema, archive/query/target/
    restored SHA256 fields, required paths, positive row/byte counts, and a
    restore command containing --archive, --output, --query-fasta, and
    --target-fasta

  make check-fasim-gasal2-archive-first-output:
    passed
    target = .tmp/fasim_gasal2_chr22_slice_10m_12m.fa
    rna = H19.fa
    compare_mode = byte
    archive_first_requested = 1
    archive_first_active = 1
    archive_first_decision = active
    restored_equal = 1
    legacy_only_rows = 0
    archive_only_rows = 0
    restored_rows = 8,291
    legacy_run_wall_seconds = 3.471703
    archive_run_wall_seconds = 3.047224
    restore_wall_seconds = 0.222225
    legacy_text_bytes = 1,836,889
    archive_bytes = 321,411
    archive_gzip_bytes = 133,990
    archive_manifest = .tmp/check_fasim_gasal2_archive_first_output/archive/
      archive-manifest.tsv
    archive_manifest_valid = 1
    restore_command_present = 1
    restore_command_has_archive = 1
    restore_command_has_output = 1
    restore_command_has_query_fasta = 1
    restore_command_has_target_fasta = 1
    archive_manifest_decision = ready
    archive_magic = FATFOC1
    archive_version = 2
    archive_terminator_present = 1
    archive_sha256 =
      805c0e5c6400ac7afd7c6a8e7b42634a7a10e43999882d8c6c45c646a7ea5511
    query_fasta_sha256 =
      7d94fb9515b0fa63dbe8fb62e01bb50616760ce80eeef29ec9c3893af8040f4e
    target_fasta_sha256 =
      e36fd5e349179420d36f7a2cca4503dbe1e82ad4d7eecb88afd421f0f23099ea
    restored_sha256 =
      2d755d3cd9a5b3375967f18576255df2e71220d63477ac06711b00d897273f07
    query_bases = 2,812
    target_bases = 2,000,000

  interpretation:
    archive-first output now has an integrity gate, a delivery manifest gate,
    and can restore the small fixture byte-identically without rerunning
    Fasim. The manifest records the restore command and required reference
    digests, so downstream consumers can validate the archive package before
    restoring TFOsorted on demand.

  make check-fasim-gasal2-roadmap-phase5-archive-artifact:
    passed
    phase5_archive_artifact_gate = ready
    archive_integrity_parser = pass
    archive_manifest_parser = pass
    archive_first_output = pass
    archive_manifest_decision = ready
    restored_equal = 1
```

### Phase 6: Broader Workload Matrix

Goal:

```text
Make the accepted scope honest across workloads.
```

Workloads:

```text
short-query/H19:
  chr21
  chr22
  chr1
  chr21+chr22

tiny-region grouped:
  MEG3 full

fallback-heavy / long-query boundary:
  MALAT1 first8/first64 where applicable
  NEAT1 first64
```

Collect:

```text
run wall
convert wall
restore wall
GPU kernel and total time
CPU row build time
sort/filter time
row count
digest or row-set equality
fallback count
archive bytes
restored output bytes
```

Matrix artifact:

```text
docs/fasim_gasal2_workload_matrix.tsv
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase6-workload-matrix
make check-fasim-gasal2-workload-matrix-parser
make check-fasim-gasal2-workload-matrix
```

```text
all claimed workloads pass the exact contract gate
unclaimed workloads fail closed or fall back explicitly
performance claims are workload-specific
```

Exit:

```text
documentation can recommend where the mode should and should not be used
```

Stop if:

```text
performance depends on unclaimed output drift
fallback-heavy workloads are presented as GPU-fast-path clean
```

Current evidence:

```text
2026-06-12:
  make check-fasim-gasal2-roadmap-phase6-workload-matrix:
    passed
    phase6_workload_matrix_gate = claimed_scope_only
    claimed_workloads = 4
    claimed_pass = 4
    claimed_fail = 0
    broad_gate_rows_clean = 0
    align_side_reduced_claimed = 0
    decision = matrix_has_claimed_scope_only

  make check-fasim-gasal2-workload-matrix-parser:
    passed

  make check-fasim-gasal2-workload-matrix:
    passed
    workloads = 7
    claimed_workloads = 4
    claimed_pass = 4
    claimed_fail = 0
    unclaimed_workloads = 2
    blocked_workloads = 1
    performance_claims_workload_specific = 1
    broad_gate_rows = 0
    broad_gate_rows_clean = 0
    scoreinfo_reduced_claimed = 2
    align_side_reduced_claimed = 0
    decision = matrix_has_claimed_scope_only

  claimed pass:
    chr22_full:
      contract = equivalence_first_full_output
      row_equal = true
      speedup = 0.993x
      note = restored row-set equal, not a positive runtime claim on final2

    chr1_full:
      contract = equivalence_first_full_output
      row_equal = true
      speedup = 1.094x
      note = restored row-set equal, convert speedup 1.788x

    chr21_chr22_top5:
      contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1
      top5_equal = true
      speedup = 40.119x
      note = top5 artifact only, not full TFOsorted replacement

    meg3_group32_top5:
      contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1
      top5_equal = true
      speedup = 1.939x
      note = grouped tiny-region top5 artifact, not broad replacement

  unclaimed / blocked:
    neat1_first64:
      scope = unclaimed
      status = fallback
      query_len = 22,767 > GASAL2 max query 2,812
      note = top5 clean but GPU path inactive

    malat1_first8:
      scope = blocked
      status = fail
      top5_equal = true
      speedup = 0.702x
      fallback/guard count = 3,091
      note = not a recommended broad path

    malat1_first64_two_contract:
      scope = unclaimed
      status = pass
      speedup = 1.031x
      note = experimental two-contract trust, not broad aligner replacement

  interpretation:
    Phase 6 currently supports a claimed scoped matrix only. It does not close
    the broad GASAL2/Fasim replacement objective. Workload-specific claims are
    explicit, and long-query/fallback-heavy workloads are not presented as
    GPU-fast-path clean. The matrix now records scoreInfo-side and Align-side
    reduction evidence explicitly: the current claimed wins include scoped
    scoreInfo-side reductions, but no claimed workload reduces Align-side work,
    so the Phase 7 broad gate remains unsatisfied.
```

### Phase 7: Broad Architecture Restart Only If Needed

Goal:

```text
Pursue the original broad objective only with a materially different
architecture.
```

Required change:

```text
reduce both GPU scoreInfo work and CPU realpath extend/align work
avoid current replay-heavy consumer shape
preserve scoreInfo-level single-emission semantics
prove full output equivalence before performance claims
```

Allowed directions:

```text
co-designed scoreInfo plus consumer that reduces align attempts
lower-shared-memory scoreInfo only if it also reduces consumer work
new long-query execution model with equivalence proof
CPU-side realpath pruning with full row-set proof
```

Forbidden restarts:

```text
current selected-only replay
current prefix replay with unchanged align attempts
current segmented traceback
current exact tiling or overlap tiling as real path
GPU endpoint/CIGAR/traceback authority without separate proof
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase7-broad-restart
make check-fasim-gasal2-roadmap-phase7-candidate-coverage
make check-fasim-gasal2-roadmap-phase7-candidate-coverage-stop
make check-fasim-gasal2-roadmap-phase7-next-reducer-design
make check-fasim-gasal2-roadmap-phase7-next-reducer-implementation-plan
make check-fasim-gasal2-goal-completion-decision
make check-fasim-gasal2-roadmap-broad-restart-gate
```

```text
NEAT1 first64:
  full row-set equality or digest clean
  triplex mismatches = 0
  scoreInfo mismatches = 0
  candidate_vs_baseline > 1.0x
  candidate_wall_seconds < CPU baseline
  align attempts materially reduced or replaced
```

Exit:

```text
broad objective can continue to larger workload validation
```

Stop if:

```text
kernel-only optimization is the main win
CPU realpath extend/align remains unchanged
NEAT1 remains slower than CPU baseline
```

Current evidence:

```text
2026-06-12:
  make check-fasim-gasal2-roadmap-phase7-broad-restart:
    passed
    phase7_broad_restart_gate = current_architecture_no_go
    broad_objective_status = open
    broad_restart_required = 1
    broad_gate_rows_clean = 0
    phase7_next_architecture_required = 1
    must_not_call_update_goal_complete = 1

  make check-fasim-gasal2-roadmap-phase7-candidate-coverage:
    passed
    phase7_candidate_coverage_gate = defined_not_completion
    candidate_coverage_plan = pass
    candidate_coverage_env = pass
    candidate_coverage_characterization = pass
    candidate_coverage_runtime_smoke = pass
    candidate_coverage_smoke_false_negative_scoreinfos = 0
    candidate_coverage_smoke_candidate_align_attempts = 51
    candidate_coverage_smoke_reference_align_attempts = 51
    candidate_coverage_selected_only_runtime_smoke = pass
    candidate_coverage_selected_only_false_negative_scoreinfos = 0
    candidate_coverage_selected_only_candidate_attempts = 2352
    candidate_coverage_selected_only_candidate_align_attempts = 51
    candidate_coverage_selected_only_reference_align_attempts = 51
    candidate_coverage_current_decision =
      coverage_clean_no_align_reduction
    cpu_aligner_align_authority = 1
    gasal2_output_authority = 0
    requires_false_negative_scoreinfos_zero = 1
    requires_cpu_align_attempt_reduction = 1
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make check-fasim-gasal2-roadmap-phase7-candidate-coverage-stop:
    passed
    phase7_candidate_coverage_stop_gate = current_reducer_no_go
    candidate_coverage_prefix_false_negative_scoreinfos = 0
    candidate_coverage_prefix_align_reduction = 0
    candidate_coverage_selected_only_false_negative_scoreinfos = 0
    candidate_coverage_selected_only_align_reduction = 0
    candidate_coverage_stop_reason = no_cpu_align_attempt_reduction
    next_phase7_required = new_reducer_or_architecture
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make check-fasim-gasal2-roadmap-phase7-next-reducer-design:
    passed
    phase7_next_reducer_design_gate = defined
    current_candidate_reducer_status = current_reducer_no_go
    required_next_reducer = task_local_frontier_or_scoreinfo_local_state
    cpu_aligner_align_authority = 1
    gasal2_output_authority = 0
    requires_align_attempt_reduction = 1
    requires_false_negative_scoreinfos_zero = 1
    requires_neat1_first64_broad_gate = 1
    must_not_call_update_goal_complete = 1

  make check-fasim-gasal2-roadmap-phase7-next-reducer-implementation-plan:
    passed
    phase7_next_reducer_implementation_plan_gate = defined
    requires_default_off_shadow = 1
    requires_cpu_align_authority = 1
    requires_task_local_frontier = 1
    requires_scoreinfo_local_state = 1
    requires_align_attempt_reduction = 1
    requires_broad_matrix_evidence_before_completion = 1
    must_not_call_update_goal_complete = 1

  Phase 7 next reducer implementation plan:
    docs/superpowers/plans/2026-06-12-fasim-gasal2-phase7-next-reducer.md
    first implementation step is a default-off scaffold
    completion requires broad matrix evidence, not plan existence

  make check-fasim-gasal2-roadmap-phase7-next-reducer-scaffold:
    passed
    phase7_next_reducer_scaffold_gate = bounded_go_not_broad
    phase7_next_reducer_env_gate = pass
    phase7_next_reducer_runtime_smoke = pass
    phase7_next_reducer_characterization = pass
    phase7_next_reducer_digest_match = 1
    phase7_next_reducer_false_negative_scoreinfos = 0
    phase7_next_reducer_triplex_mismatches = 0
    phase7_next_reducer_candidate_align_attempts = 48
    phase7_next_reducer_reference_align_attempts = 192
    phase7_next_reducer_current_decision = bounded_go_needs_neat1_broad_gate
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  Phase 7 next reducer scaffold:
    default-off env and telemetry are wired
    bounded short-query runtime smoke is clean
    current bounded reducer preserves digest and reduces CPU Align attempts
      on the short-query smoke
    current bounded reducer is not a broad completion row
    next required step is NEAT1 first64 broad gate evidence with the same
      zero-false-negative and align-reduction requirements

  make check-fasim-gasal2-roadmap-phase7-next-reducer-broad-gate:
    passed
    phase7_next_reducer_broad_gate = correctness_no_go
    phase7_next_reducer_broad_first1_attempted = 1
    phase7_next_reducer_broad_first1_decision =
      phase7_next_reducer_broad_gate_correctness_no_go
    phase7_next_reducer_broad_first1_digest_match = 0
    phase7_next_reducer_broad_first1_full_rows_equal = 0
    phase7_next_reducer_broad_first1_baseline_only_rows = 8
    phase7_next_reducer_broad_first1_candidate_only_rows = 5
    phase7_next_reducer_broad_first1_candidate_align_attempts = 1266
    phase7_next_reducer_broad_first1_reference_align_attempts = 2696
    phase7_next_reducer_broad_first64_attempted = 0
    phase7_next_reducer_broad_first64_decision =
      phase7_next_reducer_broad_gate_skipped_first1_no_go
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  Phase 7 next reducer broad-gate interpretation:
    The bounded short-query smoke remains useful, but it does not generalize
    to the NEAT1 long-query broad gate. On NEAT1 first1 the reducer does reduce
    CPU Align attempts before output construction, but the output contract is
    already broken: digest/full row equality fail, top5 score/stability/nt-score
    equality fail, and first64 is therefore skipped. This stops the current
    segmented next-reducer shape as a broad replacement path. It does not
    invalidate the scoped top5 product or the archive/equivalence-first output
    path.

  make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-design:
    passed
    phase7_broad_restart_v2_design_gate = defined
    phase7_broad_restart_v2_current_status = design_only
    phase7_broad_restart_v2_required_first_gate = frontier_log_replay_proof
    phase7_broad_restart_v2_requires_neat1_first64 = 1
    cpu_aligner_align_authority = 1
    gasal2_output_authority = 0
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-log-scaffold:
    passed
    phase7_broad_restart_v2_frontier_log_scaffold_gate = runtime_smoke_clean
    FASIM_GASAL2_PHASE7_FRONTIER_LOG=1
    frontier log path is non-empty
    frontier log digest is non-empty
    frontier log TSV schema is present
    CPU aligner.Align() remains authority
    GASAL2 output authority = 0
    next gate = NEAT1 first1 exact replay proof
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make characterize-fasim-gasal2-phase7-frontier-replay:
    passed
    neat1_first1:
      digest_match = 1
      full_rows_equal = 1
      missing_rows = 0
      extra_rows = 0
      triplex_mismatches = 0
      false_negative_scoreinfos = 0
      frontier_log_rows = 2,872
      frontier_selected_rows = 718
      frontier_positive_align_rows = 2,872
      candidate_align_attempts = reference_align_attempts = 2,872
    neat1_first64:
      digest_match = 1
      full_rows_equal = 1
      missing_rows = 0
      extra_rows = 0
      triplex_mismatches = 0
      false_negative_scoreinfos = 0
      frontier_log_rows = 211,976
      frontier_selected_rows = 52,994
      frontier_positive_align_rows = 211,976
      candidate_align_attempts = reference_align_attempts = 211,976

  make check-fasim-gasal2-phase7-frontier-replay-result:
    passed
    phase7_broad_restart_v2_frontier_replay_gate = exact_no_reduction
    reducer-ready frontier evidence is present
    CPU aligner.Align() remains authority
    GASAL2 output authority = 0
    no measured CPU Align attempt reduction yet
    not broad completion
    next gate = reducer shadow after replay proof
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-reducer:
    passed
    phase7_broad_restart_v2_frontier_reducer =
      oracle_reduction_projected_not_broad
    neat1_first1:
      candidate_align_attempts = 718
      reference_align_attempts = 2,872
      align_attempt_reduction = 2,154
      wall_time_basis = oracle_projected
      broad_gate_pass = 0
    neat1_first64:
      candidate_align_attempts = 52,994
      reference_align_attempts = 211,976
      align_attempt_reduction = 158,982
      wall_time_basis = oracle_projected
      broad_gate_pass = 0
    interpretation:
      selected frontier rows define a useful upper bound after exact replay
      selected frontier rows are known only after CPU Align in the current log
      a future predictor or measured runtime reducer is still required
      no broad-replacement matrix row may be added yet
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-predictor:
    passed
    phase7_broad_restart_v2_frontier_predictor = no_go_current_features
    tested pre-Align frontier fields:
      scoreinfo_position
      scoreinfo_score
      scoreInfo-local attempt rank
      attempt_start
      attempt_cutlength
    neat1_first64:
      reference_attempts = 211,976
      selected_rows = 52,994
      selected_rank_set = 0,1,2,3
      group_size_set = 4
      oracle_selected align_attempt_reduction = 158,982
      oracle_selected predictor_gate_pass = 0
      keep_all false_negative_selected_rows = 0
      keep_all align_attempt_reduction = 0
      reducing pre-align predictors all have false_negative_selected_rows > 0
    decision = phase7_frontier_predictor_no_go_current_features
    interpretation:
      the current frontier fields do not contain a safe pre-Align selected-row
      predictor
      the 75% reduction remains an oracle upper bound, not a runtime path
      a future reducer needs a new signal or different measured runtime design
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-score-signal:
    passed
    phase7_broad_restart_v2_frontier_score_signal = no_go
    tested post-Align score/end fields:
      align_sw_score
      align_ref_begin
      align_ref_end
      align_query_begin
      align_query_end
    neat1_first64:
      reference_attempts = 211,976
      selected_rows = 52,994
      selected_score_rank_counts = 0:33615,1:2469,2:2240,3:14670
      oracle_selected align_attempt_reduction = 158,982
      align_sw_score_desc_top_3 false_negative_selected_rows = 14,670
      align_sw_score_desc_top_3 align_attempt_reduction = 52,994
      align_sw_score_ge_best_zero_fn false_negative_selected_rows = 0
      align_sw_score_ge_best_zero_fn align_attempt_reduction = 0
    decision = phase7_frontier_score_signal_no_go
    interpretation:
      even post-Align score/end fields do not contain a safe reducing signal
      a cheap score-only surrogate is unlikely to identify selected frontier rows
      without reproducing more of the legacy state
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop:
    passed
    phase7_broad_restart_v2_frontier_early_stop =
      candidate_not_measured
    candidate:
      scoreInfo-local early stop after the first selected attempt
      CPU aligner.Align() remains authority for attempts up to selected
      later attempts are skipped only within the same scoreInfo group
    neat1_first64:
      groups = 52,994
      reference_attempts = 211,976
      candidate_align_attempts = 103,953
      align_attempt_reduction = 108,023
      reduction_fraction = 0.509600
      selected_rows = 52,994
      selected_rank_counts = 0:33615,1:2469,2:2240,3:14670
      multi_selected_groups = 0
      no_selected_groups = 0
      skipped_after_selected_rows = 108,023
      unsafe_skipped_rows = 0
      false_negative_selected_rows = 0
    interpretation:
      this is a plausible runtime reducer because it uses state observed after
      CPU-authority Align and selection
      it remains a frontier-log characterization, not measured runtime
    runtime_candidate = 1
    measured_runtime = 0
    broad_gate_pass = 0
    next gate = measured runtime early-stop reducer
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop-runtime:
    passed
    phase7_broad_restart_v2_frontier_early_stop_runtime =
      runtime_smoke_clean_needs_neat1_first1
    runtime:
      FASIM_GASAL2_PHASE7_FRONTIER_EARLY_STOP=1
      default_off = 1
      reference_align_attempts = 192
      candidate_align_attempts = 48
      skipped_attempts = 144
      output digest unchanged
    interpretation:
      measured runtime telemetry now exists for scoreInfo-local early stop
      CPU aligner.Align() remains authority for attempted rows
      this is small-fixture runtime smoke, not broad completion
    broad_gate_pass = 0
    next gate = measured runtime NEAT1 first1 correctness gate
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make characterize-fasim-gasal2-phase7-frontier-early-stop-runtime
  make check-fasim-gasal2-phase7-frontier-early-stop-runtime-result:
    passed
    phase7_broad_restart_v2_frontier_early_stop_runtime_first1 =
      correctness_no_go
    neat1_first1:
      digest_match = 0
      full_rows_equal = 0
      missing_rows = 7
      extra_rows = 5
      triplex_mismatches = 12
      candidate_align_attempts = 1,309
      reference_align_attempts = 2,872
      align_attempt_reduction = 1,563
      candidate_vs_baseline ~= 0.97
      decision = phase7_frontier_early_stop_runtime_first1_no_go
      decision_reasons = output_rows_differ,missing_rows,extra_rows
    interpretation:
      measured runtime early-stop reduces Align attempts but changes output
      this candidate must not continue to NEAT1 first64 broad gate
    broad_gate_pass = 0
    next gate = new reducer or architecture
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make check-fasim-gasal2-roadmap-phase7-next-reducer-after-early-stop-design:
    passed
    phase7_next_reducer_after_early_stop_no_go_design = defined
    design:
      coverage-first all-attempt CPU replay
      candidate coverage before candidate reduction
      do not continue the measured early-stop candidate to NEAT1 first64
      CPU aligner.Align() remains authority
      GASAL2 output authority = 0
      no GPU endpoint authority
      no GPU CIGAR or traceback authority
    gates:
      Gate A: all-attempt early-stop runtime first1
      Gate B: all-attempt early-stop runtime first64
      Gate C: coverage-preserving GPU candidate generator
    required first gate:
      NEAT1 first1 digest or full row equality clean
      missing_rows = 0
      extra_rows = 0
      triplex_mismatches = 0
      candidate_align_attempts < reference_align_attempts
    broad completion still requires:
      scoreInfo/preAlign work must be reduced before broad completion
      Align-side work must be reduced or replaced before broad completion
    next gate = all-attempt early-stop runtime first1
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime
  make check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-result:
    passed
    phase7_all_attempt_early_stop_runtime_first1 =
      correctness_go_needs_first64
    runtime:
      FASIM_GASAL2_PHASE7_ALL_ATTEMPT_EARLY_STOP=1
    neat1_first1:
      digest_match = 1
      full_rows_equal = 1
      missing_rows = 0
      extra_rows = 0
      triplex_mismatches = 0
      false_negative_scoreinfos = 0
      candidate_align_attempts = 2,008
      reference_align_attempts = 2,872
      align_attempt_reduction = 864
      candidate_vs_baseline = near_parity_across_reruns
      decision = phase7_all_attempt_early_stop_runtime_first1_go
      decision_reasons = none
    interpretation:
      all-attempt mode keeps candidate coverage before candidate reduction
      CPU aligner.Align() remains authority
      NEAT1 first1 correctness and Align-side attempt reduction pass
      first1 wall time is near parity across reruns and is not a broad performance gate
      this is not broad completion because scoreInfo/preAlign work is not reduced
    broad_gate_pass = 0
    next gate = all-attempt early-stop runtime first64
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  make characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64
  make check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64-result:
    passed
    phase7_all_attempt_early_stop_runtime_first64 =
      correctness_go_near_parity_not_broad
    runtime:
      FASIM_GASAL2_PHASE7_ALL_ATTEMPT_EARLY_STOP=1
    neat1_first64:
      digest_match = 1
      full_rows_equal = 1
      missing_rows = 0
      extra_rows = 0
      triplex_mismatches = 0
      false_negative_scoreinfos = 0
      candidate_align_attempts = 140,087
      reference_align_attempts = 211,976
      align_attempt_reduction = 71,889
      candidate_vs_baseline = near_parity_across_reruns
      decision = phase7_all_attempt_early_stop_runtime_first64_go
      decision_reasons = none
    interpretation:
      all-attempt mode preserves the first64 output contract
      CPU aligner.Align() remains authority
      Align-side work is reduced by 71,889 attempts
      scoreInfo/preAlign work is still CPU work
      wall time is near parity across reruns, not a material broad performance win
      this is a coverage-preserving reducer milestone, not broad completion
    broad_gate_pass = 0
    next gate = coverage-preserving GPU candidate generator
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

  docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md:
    phase7_gate_c_gpu_candidate_generator_design = defined
    design:
      coverage-preserving GPU candidate generator
      candidate coverage before candidate reduction
      preserve the all-attempt early-stop frontier
      reduce or replace scoreInfo/preAlign work
    first gate:
      NEAT1 first1 coverage gate
      false_negative_scoreinfos = 0
      missing_rows = 0
      extra_rows = 0
      triplex_mismatches = 0
      candidate_align_attempts <= Gate B candidate_align_attempts
      scoreInfo/preAlign work reduced or replaced
    broad gate:
      NEAT1 first64 broad gate
      full claimed output contract clean
      candidate_wall_seconds < baseline_wall_seconds
      candidate_vs_baseline > 1.0
      scoreInfo/preAlign work reduced or replaced
      Align-side work reduced or replaced
    authority:
      CPU aligner.Align() remains authority
      GASAL2 output authority = 0
      no GPU endpoint authority
      no GPU CIGAR or traceback authority
      no real opt-in
    workload matrix broad_replacement row is forbidden until Gate C first64 passes
    broad_gate_pass = 0
    next gate = Gate C implementation plan
    broad_objective_status = open
    must_not_call_update_goal_complete = 1

	  docs/superpowers/plans/2026-06-13-fasim-gasal2-phase7-gate-c-gpu-candidate-generator.md:
	    phase7_gate_c_gpu_candidate_generator_implementation_plan = defined
	    implementation scope:
      FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES=1
      default-off shadow path
      Task 1: Gate C Env And Telemetry
      Task 2: Oracle Frontier Export Reuse
      Task 3: GPU Candidate Descriptor Shadow
      Task 4: Coverage Comparison Gate
      Task 5: CPU-Authority Replay Gate
      Task 6: NEAT1 first64 Broad Characterization
      Task 7: Roadmap And Matrix Decision
    invariants:
      CPU aligner.Align() remains authority
      GASAL2 output authority = 0
      no GPU endpoint authority
      no GPU CIGAR or traceback authority
      no real opt-in
      workload matrix broad_replacement row is forbidden until Gate C first64 passes
    gate requirements:
      NEAT1 first1 coverage gate
      NEAT1 first64 broad gate
      false_negative_scoreinfos = 0
      missing_rows = 0
      extra_rows = 0
      triplex_mismatches = 0
      candidate_align_attempts <= Gate B candidate_align_attempts
      scoreInfo/preAlign work reduced or replaced
    broad_gate_pass = 0
	    next gate = Gate C runtime prototype
	    broad_objective_status = open
	    must_not_call_update_goal_complete = 1

	  make check-fasim-gasal2-phase7-gate-c-env
	  make check-fasim-gasal2-phase7-gate-c-runtime-smoke:
	    passed
	    phase7_gate_c_runtime_smoke = pass
	    runtime:
	      FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES=1
	    default-off baseline:
	      phase7_gate_c_requested = 0
	      phase7_gate_c_active = 0
	    candidate smoke:
	      phase7_gate_c_requested = 1
	      phase7_gate_c_active = 0
	      phase7_gate_c_tasks = 48
	      phase7_gate_c_oracle_scoreinfos = 48
	      phase7_gate_c_oracle_attempts = 192
	      phase7_gate_c_gpu_candidate_scoreinfos = 0
	      phase7_gate_c_gpu_candidate_attempts = 0
	      phase7_gate_c_false_negative_scoreinfos = 0
	      phase7_gate_c_missing_required_attempts = 0
	      phase7_gate_c_extra_candidate_attempts = 0
	    interpretation:
	      Gate C env, telemetry, and runtime hook are wired
	      this is an oracle-metric scaffold smoke, not GPU candidate generation
	      no first1 or first64 coverage proof has passed yet
	    broad_gate_pass = 0
	    next gate = Gate C GPU Candidate Descriptor Shadow
	    broad_objective_status = open
	    must_not_call_update_goal_complete = 1

	  make characterize-fasim-gasal2-phase7-gate-c-first1
	  make check-fasim-gasal2-phase7-gate-c-first1-result:
	    passed
	    phase7_gate_c_first1 = no_go_no_gpu_candidate_descriptors
	    neat1_first1:
	      digest_match = 1
	      full_rows_equal = 1
	      missing_rows = 0
	      extra_rows = 0
	      triplex_mismatches = 0
	      false_negative_scoreinfos = 0
	      candidate_align_attempts = 2,008
	      gate_b_candidate_align_attempts = 2,008
	      scoreinfo_reduced = 0
	      oracle_scoreinfos = 718
	      oracle_attempts = 2,872
	      gpu_candidate_scoreinfos = 0
	      gpu_candidate_attempts = 0
	      missing_required_attempts = 0
	      extra_candidate_attempts = 0
	      gate_c_requested = 1
	      gate_c_active = 1
	      decision = phase7_gate_c_first1_no_go
	      decision_reasons = no_gpu_candidate_descriptors,scoreinfo_not_reduced
	    interpretation:
	      CPU-authority replay remains output-clean on first1
	      current Gate C does not generate GPU candidate descriptors
	      current Gate C does not reduce or replace scoreInfo/preAlign work
	      this candidate must not continue to Gate C first64 broad gate
	      no broad_replacement workload-matrix row may be added
	    broad_gate_pass = 0
	    next gate = new GPU candidate descriptor source or stop broad GASAL2 path
	    broad_objective_status = open
	    must_not_call_update_goal_complete = 1

	  docs/fasim_gasal2_phase7_gate_c_stop_checkpoint.md:
	    phase7_gate_c_stop_checkpoint = current_source_no_go
	    current_gate_c_source_status = stopped_no_gpu_candidate_descriptors
	    gate_c_first64_allowed = 0
	    restart_requires_new_gpu_candidate_descriptor_source = 1
	    restart first1 requirements:
	      gpu_candidate_scoreinfos > 0
	      gpu_candidate_attempts > 0
	      scoreinfo_reduced = 1
	      digest_match = 1 or full_rows_equal = 1
	      missing_rows = 0
	      extra_rows = 0
	      triplex_mismatches = 0
	      false_negative_scoreinfos = 0
	      missing_required_attempts = 0
	      candidate_align_attempts <= 2,008
	      CPU aligner.Align() remains authority
	      GASAL2 output authority = 0
	      no GPU endpoint authority
	      no GPU CIGAR or traceback authority
	    broad_gate_pass = 0
	    broad_objective_status = open
	    must_not_call_update_goal_complete = 1

	  docs/fasim_gasal2_phase7_current_broad_stop_decision.md:
	    phase7_current_broad_stop_decision = current_broad_sources_no_go
	    current_broad_sources_status = stopped
	    phase7_current_broad_sources_may_continue = 0
	    phase7_new_architecture_required = 1
	    stopped current sources:
	      co-designed broad replacement-consumer
	      attempt-consumer shadow
	      emission-only consumer shadow
	      frontier early-stop runtime
	      all-attempt early-stop runtime as broad completion
	      Gate C current source
	    claimed_broad_replacement_rows = 0
	    broad_gate_pass = 0
	    broad_objective_status = open
	    must_not_call_update_goal_complete = 1

	  Phase 7 broad restart v2:
    docs/fasim_gasal2_phase7_broad_restart_v2_design.md
    docs/superpowers/plans/2026-06-12-fasim-gasal2-phase7-broad-restart-v2.md
    new order = frontier log first, exact replay proof before reduction
    first required gate = NEAT1 first1 frontier-log replay proof
    broad gate remains NEAT1 first64 with full row equality or digest clean,
      align-side reduction, scoreInfo/preAlign reduction, and wall-time win
    work.

  CPU-authority candidate coverage:
    next broad-path probe toward Phase 7
    CPU aligner.Align() remains semantic authority
    GASAL2 may only propose candidate attempts
    false_negative_scoreinfos must be zero
    CPU align attempts must be reduced
    selected-only coverage reduces candidate attempts but not CPU Align attempts
      on the bounded smoke
    current prefix and selected-only candidate reducers are no-go because they
      do not reduce same-scope CPU Align attempts
    total time must beat the same-scope CPU reference before any follow-up
    runtime path can be considered

  make check-fasim-gasal2-goal-completion-decision:
    passed
    scoped_product_status = accepted
    broad_objective_status = open
    broad_restart_required = 0
    claimed_workloads_clean = 1
    broad_gate_rows_clean = 0
    blocked_or_unclaimed_workloads = 3
    user_scope_acceptance_recorded = 1
    scoped_completion_may_close_goal = 1
    path_a_user_acceptance_recorded = 1
    path_a_scoped_completion_may_close_goal = 1
    active_goal_completion_status = complete_scoped_path_a
    final_goal_decision = complete_scoped_path_a
    scope_or_broad_design_decision_required = 0
    path_a_user_acceptance_required = 0
    path_b_new_broad_architecture_required = 0
    completion_guard_cleared = 1
    goal_completion_status = complete
    must_not_call_update_goal_complete = 0
    synthetic broad weak matrix:
      broad_replacement row with row equality, speedup > 1, and fallback = 0
      but without scoreInfo and Align-side reduction evidence remains open
    synthetic broad complete matrix:
      broad_replacement row with row equality, speedup > 1, fallback = 0,
      scoreinfo_reduced = true, and align_side_reduced = true can complete

  make check-fasim-gasal2-roadmap-broad-restart-gate:
    passed
    roadmap_broad_restart_gate = current_architecture_no_go
    broad_objective_status = open
    broad_restart_required = 1
    claimed_workloads_clean = 1
    broad_gate_rows_clean = 0
    blocked_or_unclaimed_workloads = 3
    neat1_first64_status = fallback
    malat1_first8_status = fail
    forbidden_restarts_checked = 1
    phase7_next_architecture_required = 1
    must_not_call_update_goal_complete = 1

  interpretation:
    The current matrix does not satisfy the Phase 7 broad gate. The only
    valid continuation for the original broad objective is a materially
    different architecture that reduces both scoreInfo/preAlign work and
    Align-side realpath work while preserving full output equivalence.
```

### Phase 8: Completion Decision

Goal:

```text
Decide whether the goal is complete, narrowed, or stopped.
```

Scoped product completion is valid if:

```text
the user accepts the scoped contract
default-off runtime is documented
reproducible build and checks pass
claimed artifacts are equivalent under their contract
non-claims are explicit
```

Broad objective completion is valid if:

```text
full row-set/digest equality is proven over the claimed broad scope
runtime beats CPU authority
both scoreInfo/preAlign and Align-side bottlenecks are addressed
fallback and unsupported workload behavior is explicit
```

Stop or defer if:

```text
only top5 works but full output is required
only archive/output improves but GPU/scoreInfo objective remains open
long-query broad path still cannot beat CPU
correctness depends on changed endpoint/CIGAR/traceback semantics
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase8-completion-decision
make check-fasim-gasal2-goal-completion-decision
make check-fasim-gasal2-roadmap-current-state
```

Current decision:

```text
scoped product:
  accepted by the user as the narrowed scoped contract

broad objective:
  open

active goal:
  complete under Path A scoped completion

original broad objective:
  open, not claimed complete

required next action:
  no further PR required for this scoped goal closure
```

Current evidence:

```text
2026-06-12:
  make check-fasim-gasal2-roadmap-phase8-completion-decision:
    passed
    phase8_completion_decision_gate =
      complete_scoped_path_a
    scoped_product_status = accepted
    broad_objective_status = open
    broad_restart_required = 0
    broad_gate_rows_clean = 0
    final_goal_decision = complete_scoped_path_a
    scope_or_broad_design_decision_packet = defined
    current_decision = path_a_scoped_completion_accepted
    scope_or_broad_design_decision_required = 0
    path_a_user_acceptance_required = 0
    path_b_new_broad_architecture_required = 0
    current_v4_source_replay_must_not_continue = 1
    completion_guard_cleared = 1
    must_not_call_update_goal_complete = 0
```

Decision packet:

```text
document = docs/fasim_gasal2_scope_or_broad_design_decision.md
scope_or_broad_design_decision_packet = defined
current_decision = path_a_scoped_completion_accepted
path_a_choice = accept_scoped_completion
path_b_choice = pursue_different_gpu_execution_design
current_v4_source_replay_must_not_continue = 1
```

Roadmap current-state rollup:

```bash
make check-fasim-gasal2-roadmap-current-state
```

Current rollup decision:

```text
phase0_reproducibility = ready
phase1_scoped_contract = accepted
path_a_scoped_completion_acceptance_packet = defined
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
phase2_equivalence_first_convert = ready
phase3_preconvert_prune = not_ready_current_prune_no_go
phase3_cigar_nt_prefilter_design = defined_shadow_first
phase3_cigar_nt_prefilter_shadow = proof_smoke_clean
phase3_cigar_nt_prefilter_full = proof_clean_low_savings
phase3_cigar_nt_prefilter_real_validate = full_clean_no_speedup_default_off
phase4_sort_topn = not_first_priority
phase5_archive_artifact = ready
phase6_workload_matrix = claimed_scope_only
phase7_broad_restart = current_architecture_no_go
phase7_next_reducer_scaffold = bounded_go_not_broad
phase7_next_reducer_broad_gate = correctness_no_go
phase7_broad_restart_v2_design = defined_frontier_log_first
phase7_broad_restart_v2_frontier_log_scaffold =
  runtime_smoke_clean_not_replay_proof
phase7_broad_restart_v2_frontier_replay =
  exact_no_reduction_not_broad
phase7_broad_restart_v2_frontier_reducer =
  oracle_reduction_projected_not_broad
phase7_broad_restart_v2_frontier_predictor =
  no_go_current_features
phase7_broad_restart_v2_frontier_score_signal =
  no_go
phase7_broad_restart_v2_frontier_early_stop =
  candidate_not_measured
phase7_broad_restart_v2_frontier_early_stop_runtime =
  runtime_smoke_clean_needs_neat1_first1
phase7_broad_restart_v2_frontier_early_stop_runtime_first1 =
  correctness_no_go
phase7_next_reducer_after_early_stop_no_go_design = defined
phase8_completion_decision = complete_scoped_path_a
scoped_product_status = accepted
broad_objective_status = open
active_goal_completion_status = complete_scoped_path_a
scope_or_broad_design_decision_required = 0
path_a_user_acceptance_required = 0
path_b_new_broad_architecture_required = 0
completion_guard_cleared = 1
goal_completion_status = complete
must_not_call_update_goal_complete = 0
roadmap_current_state_decision = complete_scoped_path_a
```

## Recommended Immediate Next PR

No next PR is required for this scoped goal closure. The following historical
Path B note is retained as stopped evidence, not the current cursor.

The Phase 3 CIGAR NT prefilter line remains stopped as a runtime
optimization:

```text
correctness = clean
measured performance = no-go
runtime recommendation = no
default enablement = no
```

The Phase 7 v2 frontier log, replay proof, oracle reducer, predictor
no-go, score-signal no-go, early-stop runtime smoke, early-stop first1
correctness no-go, and next reducer design are now recorded.
The next implementation PR should be:

```text
fasim: prototype Phase 7 all-attempt early-stop runtime
```

Scope:

```text
Do not continue the measured early-stop candidate to NEAT1 first64.
Implement only Gate A from
docs/fasim_gasal2_phase7_next_reducer_after_early_stop_no_go_design.md:
  all-attempt early-stop runtime first1
  NEAT1 first1 full row equality or digest clean
  missing rows = 0
  extra rows = 0
  triplex mismatches = 0
  candidate_align_attempts < reference_align_attempts
  no segmented GASAL2-pruned candidate stream
  no GASAL2 endpoint/CIGAR/traceback/output authority
  no broad completion claim

CPU legacy conversion remains row/output/digest authority
no default runtime behavior change
no endpoint/CIGAR/traceback authority change
```

Required evidence:

```text
Phase 3 stop:
  phase3_cigar_nt_prefilter_real_validate_full_characterization = pass
  restored_equal = 1
  real_validate_mismatches = 0
  real_fallbacks = 0
  convert_wall_speedup < 1.0 on chr22 and chr1
  run_wall_speedup < 1.0 or not materially above 1.0 on chr22 and chr1

Phase 7 v2 frontier log:
  phase7_broad_restart_v2_frontier_log_scaffold_gate = runtime_smoke_clean
  FASIM_GASAL2_PHASE7_FRONTIER_LOG=1
  frontier log path is non-empty
  frontier log digest is non-empty
  frontier log TSV schema is present
  frontier log runtime smoke passes
  CPU aligner.Align() remains authority
  GASAL2 output authority = 0
  next gate = NEAT1 first1 exact replay proof

Phase 7 v2 replay proof, not yet complete:
  NEAT1 first1 replay proof is exact
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  candidate_align_attempts = reference_align_attempts

Phase 7 v2 reducer oracle, not yet complete:
  NEAT1 first64 projected selected frontier attempts = 52,994
  NEAT1 first64 reference frontier attempts = 211,976
  projected align_attempt_reduction = 158,982
  wall_time_basis = oracle_projected
  broad_gate_pass = 0
  next gate = measured runtime reducer or predictor

Phase 7 v2 predictor, not complete:
  NEAT1 first64 selected_rank_set = 0,1,2,3
  pre-Align frontier fields cannot safely identify selected rows
  keep_all is zero false-negative but has no reduction
  reducing pre-Align predictors have false negatives
  oracle_selected remains post-Align and cannot pass predictor gate
  decision = phase7_frontier_predictor_no_go_current_features
  next gate = new pre-Align signal or measured runtime reducer design

Phase 7 v2 score-signal, not complete:
  NEAT1 first64 selected_score_rank_counts = 0:33615,1:2469,2:2240,3:14670
  align_sw_score_desc_top_3 has 14,670 false-negative selected rows
  align_sw_score_ge_best_zero_fn has zero reduction
  post-Align score/end fields cannot safely identify selected rows
  decision = phase7_frontier_score_signal_no_go
  next gate = new non-score signal or measured runtime reducer design

Phase 7 v2 early-stop, not complete:
  scoreInfo-local early stop after selected is a runtime candidate
  NEAT1 first64 candidate_align_attempts = 103,953
  NEAT1 first64 reference_attempts = 211,976
  align_attempt_reduction = 108,023
  unsafe_skipped_rows = 0
  false_negative_selected_rows = 0
  measured runtime smoke = clean
  NEAT1 first1 measured correctness = no_go
  first1 missing_rows = 7
  first1 extra_rows = 5
  first1 candidate_align_attempts = 1,309
  first1 reference_align_attempts = 2,872
  broad_gate_pass = 0
  next gate = new reducer or architecture

Only after replay proof passes may a later PR attempt:
  scoreInfo/preAlign work reduction
  Align-side attempts reduced or replaced
  candidate wall time beating CPU authority
```

Phase 7 v3 candidate-certificate design, not yet complete:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_candidate_certificate_design.md
  phase7_broad_restart_v3_candidate_certificate_design = defined
  phase7_broad_restart_v3_current_status = design_only
  phase7_broad_restart_v3_next_gate = descriptor_source_smoke
  phase7_broad_restart_v3_may_claim_completion = 0
  requires_gpu_or_native_descriptor_source = 1
  requires_candidate_certificate = 1
  requires_cpu_authority_replay = 1
  requires_scoreinfo_prealign_reduction = 1
  requires_align_side_reduction = 1
  requires_full_output_equality = 1
  current broad sources remain stopped
  v3 must not derive descriptors only after CPU frontier logging
  Gate v3.1 requires gpu_candidate_scoreinfos > 0
  Gate v3.1 requires gpu_candidate_attempts > 0
  Gate v3.1 requires cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
  Gate v3.1 requires candidate_certificate_false_negatives = 0
  Gate v3.3 NEAT1 first64 is the first possible broad gate
  broad_gate_pass = 0
  next gate = descriptor_source_smoke

Phase 7 v3 descriptor-source smoke, not complete:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_descriptor_source_smoke.md
  phase7_broad_restart_v3_descriptor_source_smoke = current_no_pre_scoreinfo_source
  phase7_broad_restart_v3_current_status = scaffold_no_go
  phase7_v3_descriptor_source_requested = 1
  phase7_v3_descriptor_source_active = 0
  phase7_v3_descriptor_source_candidate_attempts = 0
  phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0
  gpu_candidate_scoreinfos = 0
  gpu_candidate_attempts = 0
  cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls
  pre_scoreinfo_source = 0
  after_cpu_scoreinfo_source = 1
  phase7_broad_restart_v3_gate_v3_1_pass = 0
  phase7_broad_restart_v3_may_continue_to_first64 = 0
  broad_gate_pass = 0
  next gate = real_pre_scoreinfo_descriptor_source

Phase 7 v3 pre-scoreInfo descriptor-source smoke, not complete:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke.md
  phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke = pre_scoreinfo_descriptors_no_reduction
  phase7_broad_restart_v3_current_status = pre_scoreinfo_scaffold_no_go
  phase7_v3_descriptor_source_active = 1
  phase7_v3_descriptor_source_pre_scoreinfo_source = 1
  phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
  gpu_candidate_scoreinfos > 0
  gpu_candidate_attempts > 0
  cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls
  cpu_scoreinfo_reduced = 0
  candidate_certificate_checked = 0
  phase7_broad_restart_v3_gate_v3_1_pass = 0
  phase7_broad_restart_v3_may_continue_to_first64 = 0
  broad_gate_pass = 0
  next gate = certificate_checked_scoreinfo_reducing_descriptor_source

Phase 7 v3 certificate smoke, not complete:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_certificate_smoke.md
  phase7_broad_restart_v3_certificate_smoke = certificate_checked_no_scoreinfo_reduction
  phase7_broad_restart_v3_current_status = certificate_scaffold_no_go
  phase7_v3_descriptor_source_active = 1
  phase7_v3_descriptor_source_pre_scoreinfo_source = 1
  phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
  phase7_v3_descriptor_source_candidate_certificate_checked = 1
  phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
  phase7_v3_descriptor_source_missing_required_attempts = 0
  cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls
  cpu_scoreinfo_reduced = 0
  phase7_broad_restart_v3_gate_v3_1_pass = 0
  phase7_broad_restart_v3_may_continue_to_first64 = 0
  broad_gate_pass = 0
  next gate = scoreinfo_reducing_candidate_certificate

This certificate smoke is only a task-level scaffold certificate. It does not
prove full legacy scoreInfo/attempt coverage and does not reduce CPU
scoreInfo/preAlign work.

Phase 7 v3 all-column certificate smoke, v3.1 only:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_all_column_certificate_smoke.md
  phase7_broad_restart_v3_all_column_certificate_smoke = scoreinfo_reducing_all_column_certificate
  phase7_broad_restart_v3_current_status = gate_v3_1_pass_attempt_overgenerate
  phase7_v3_descriptor_source_active = 1
  phase7_v3_descriptor_source_pre_scoreinfo_source = 1
  phase7_v3_descriptor_source_candidate_scoreinfos_gt_zero = 1
  phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
  phase7_v3_descriptor_source_candidate_certificate_checked = 1
  phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
  phase7_v3_descriptor_source_missing_required_attempts = 0
  phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
  phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
  phase7_broad_restart_v3_gate_v3_1_pass = 1
  phase7_broad_restart_v3_gate_v3_2_pass = 0
  broad_gate_pass = 0
  next gate = all_column_certificate_cpu_replay_first1

This all-column certificate reduces CPU scoreInfo in the candidate source by
overgenerating every target column and every target window. It is not a
performance candidate and cannot create a broad_replacement workload-matrix row.

Phase 7 v3 all-column replay stop, current:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_all_column_replay_stop.md
  phase7_broad_restart_v3_all_column_replay_stop = candidate_attempt_explosion_no_go
  phase7_broad_restart_v3_gate_v3_1_pass = 1
  phase7_broad_restart_v3_gate_v3_2_pass = 0
  candidate_attempts = 168,730,848
  reference_align_attempts = 2,872
  candidate_attempt_ratio = 58,750.30x
  candidate_align_attempts < reference_align_attempts cannot pass
  do_not_run_all_column_cpu_replay = 1
  phase7_broad_restart_v3_may_continue_to_first64 = 0
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  Do not add a broad_replacement workload-matrix row from this stop checkpoint.
  phase7_broad_restart_v3_next_gate = narrower_scoreinfo_reducing_certificate

This stop does not invalidate the v3.1 result. It says the all-column version
is only a proof that scoreInfo can be bypassed, not a replayable broad path.
The next valid v3 source must be narrower than all columns/all windows while
still proving zero false negatives and reducing CPU scoreInfo/preAlign calls.

Phase 7 v3 narrow certificate design, current:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_design.md
  phase7_broad_restart_v3_narrow_certificate_design = defined
  phase7_broad_restart_v3_narrow_certificate_status = design_only
  phase7_broad_restart_v3_next_gate = narrow_certificate_runtime_smoke
  phase7_broad_restart_v3_gate_v3_1_pass = 0
  phase7_broad_restart_v3_gate_v3_2_pass = 0
  must_be_narrower_than_all_column = 1
  do_not_use_all_column_or_all_window_certificate = 1
  candidate_attempts < 168,730,848
  candidate_attempts < reference_align_attempts required for v3.2
  cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
  candidate_certificate_false_negatives = 0
  missing_required_attempts = 0
  required_runtime_env = FASIM_GASAL2_PHASE7_V3_NARROW_CERTIFICATE
  no broad_replacement workload-matrix row
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

This design checkpoint turns the all-column replay stop into the next concrete
runtime gate. It still does not pass Gate v3.1 and cannot create a
broad_replacement workload-matrix row.

Phase 7 v3 narrow certificate runtime smoke, current:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_smoke.md
  phase7_broad_restart_v3_narrow_certificate_smoke = bounded_probe_no_go_missing_certificate
  phase7_broad_restart_v3_narrow_certificate_status = runtime_smoke_no_go
  phase7_v3_descriptor_source_active = 1
  phase7_v3_descriptor_source_pre_scoreinfo_source = 1
  phase7_v3_descriptor_source_candidate_scoreinfos_gt_zero = 1
  phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
  phase7_v3_descriptor_source_candidate_attempts_lt_all_column = 1
  phase7_v3_descriptor_source_candidate_certificate_checked = 1
  phase7_v3_descriptor_source_candidate_certificate_false_negatives_gt_zero = 1
  phase7_v3_descriptor_source_missing_required_attempts_gt_zero = 1
  phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
  phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
  phase7_broad_restart_v3_gate_v3_1_pass = 0
  phase7_broad_restart_v3_gate_v3_2_pass = 0
  phase7_broad_restart_v3_next_gate = real_narrow_certificate_coverage_proof
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

This runtime smoke proves only that the default-off narrow telemetry path is
wired and bounded. It is not a viable certificate because false negatives and
missing required attempts are non-zero. It must not continue to first64.

Phase 7 v3 real narrow certificate coverage proof, current:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_real_narrow_certificate_coverage_proof.md
  phase7_broad_restart_v3_real_narrow_certificate_coverage_proof = exact_column_candidate_no_go
  phase7_broad_restart_v3_exact_column_candidate_status = no_go
  phase7_broad_restart_v3_gate_v3_1_pass = 0
  phase7_broad_restart_v3_gate_v3_2_pass = 0
  non_optin_active = 0
  non_optin_error = invalid argument
  non_optin_required_smem = 52416
  non_optin_default_smem_limit = 49152
  non_optin_optin_smem_limit = 101376
  smem_optin_active = 1
  smem_optin_gpu_tasks = 432
  smem_optin_scoreinfo_mismatches = 1
  smem_optin_decision = smem_optin_scoreinfo_no_go
  exact-column GPU scoreInfo is not a valid real narrow certificate source
  phase7_broad_restart_v3_next_gate = different_exact_scoreinfo_source_or_seed_certificate
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

The existing exact-column GPU source is the most direct scoreInfo-compatible
candidate, but current evidence rules it out for this gate. Non-opt-in cannot
launch, and smem opt-in is not scoreInfo-equivalent. The next Path B attempt
must use a different exact scoreInfo-compatible execution design or a seed
certificate that proves coverage.

Phase 7 v3 next source design, current:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_next_source_design.md
  phase7_broad_restart_v3_next_source_design = defined
  phase7_broad_restart_v3_next_source_status = design_only
  phase7_broad_restart_v3_next_gate = different_exact_scoreinfo_source_or_seed_certificate_smoke
  previous_exact_column_candidate_status = no_go
  do_not_continue_all_column_replay = 1
  do_not_continue_bounded_narrow_probe = 1
  do_not_continue_existing_exact_column_gpu_scoreinfo = 1
  allowed_source_1 = different_exact_scoreinfo_compatible_gpu_execution
  allowed_source_2 = seed_or_index_certificate
  descriptor_source_before_cpu_scoreinfo = 1
  cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
  candidate_certificate_false_negatives = 0
  missing_required_attempts = 0
  candidate_attempts < 168,730,848
  candidate_attempts < reference_align_attempts required before v3.2
  first1_descriptor_smoke_before_replay = 1
  first64_broad_gate_only_after_first1_replay = 1
  CPU aligner.Align() output authority
  no GPU endpoint/CIGAR/traceback/output authority
  no broad_replacement workload-matrix row
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

This design checkpoint is the current next step for Path B. It does not pass
Gate v3.1 and does not create a broad_replacement workload-matrix row. It only
defines the next allowed source families after all-column replay, bounded
narrow probing, and the existing exact-column GPU source were stopped.

Phase 7 v3 next source smoke, current:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_next_source_smoke.md
  phase7_broad_restart_v3_next_source_smoke = seed_certificate_fail_closed
  phase7_broad_restart_v3_next_source_status = runtime_smoke_no_go
  required_runtime_env = FASIM_GASAL2_PHASE7_V3_SEED_CERTIFICATE_SOURCE
  phase7_v3_descriptor_source_candidate_scoreinfos_gt_zero = 1
  phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
  phase7_v3_descriptor_source_candidate_attempts_lt_all_column = 1
  phase7_v3_descriptor_source_candidate_certificate_checked = 1
  phase7_v3_descriptor_source_candidate_certificate_false_negatives_gt_zero = 1
  phase7_v3_descriptor_source_missing_required_attempts_gt_zero = 1
  phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
  phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
  phase7_broad_restart_v3_gate_v3_1_pass = 0
  phase7_broad_restart_v3_gate_v3_2_pass = 0
  CPU aligner.Align() output authority
  no GPU endpoint/CIGAR/traceback/output authority
  no broad_replacement workload-matrix row
  phase7_broad_restart_v3_next_gate = stronger_seed_certificate_or_different_exact_scoreinfo_source
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

This smoke proves a seed/index descriptor source can run before CPU scoreInfo
and bypass CPU scoreInfo calls in the candidate path. It still fails closed:
false negatives and missing required attempts are non-zero, so it cannot
continue to CPU-authority replay or first64 broad characterization.

Phase 7 v3 strong seed smoke, current:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_strong_seed_smoke.md
  phase7_broad_restart_v3_strong_seed_smoke = task_coverage_clean_attempt_coverage_missing
  phase7_broad_restart_v3_strong_seed_status = runtime_smoke_no_go_attempt_coverage
  required_runtime_env = FASIM_GASAL2_PHASE7_V3_STRONG_SEED_CERTIFICATE_SOURCE
  phase7_v3_descriptor_source_candidate_scoreinfos_ge_baseline = 1
  phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
  phase7_v3_descriptor_source_candidate_attempts_lt_all_column = 1
  phase7_v3_descriptor_source_candidate_certificate_checked = 1
  phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
  phase7_v3_descriptor_source_missing_required_attempts_gt_zero = 1
  phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
  phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
  phase7_broad_restart_v3_gate_v3_1_pass = 0
  phase7_broad_restart_v3_gate_v3_2_pass = 0
  CPU aligner.Align() output authority
  no GPU endpoint/CIGAR/traceback/output authority
  no broad_replacement workload-matrix row
  phase7_broad_restart_v3_next_gate = attempt_coverage_seed_certificate_or_different_exact_scoreinfo_source
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

This is progress over the first seed smoke: task-level scoreInfo coverage is
clean on NEAT1 first1. It still cannot continue to replay because required
attempt coverage is not proven.

Phase 7 v3 attempt-coverage seed smoke, current:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_attempt_coverage_seed_smoke.md
  phase7_broad_restart_v3_attempt_coverage_seed_smoke = attempt_coverage_clean_needs_replay_preflight
  phase7_broad_restart_v3_attempt_coverage_seed_status = gate_v3_1_pass_candidate_attempts_high
  required_runtime_env = FASIM_GASAL2_PHASE7_V3_ATTEMPT_COVERAGE_SEED_CERTIFICATE
  reference_scoreinfos = 718
  reference_attempts = 2,872
  candidate_scoreinfos = 718
  raw_seed_hits = 1,051,822
  candidate_attempts = 108,694
  candidate_min_cover_positions = 463
  candidate_attempts_lt_all_column = 1
  candidate_attempts_lt_raw_seed_hits = 1
  candidate_attempts_below_reference = 0
  candidate_min_cover_positions_below_reference = 1
  oracle_min_cover_uses_legacy_attempt_windows = 1
  real_pre_scoreinfo_reducer_proven = 0
  candidate_certificate_false_negatives = 0
  missing_required_attempts = 0
  cpu_scoreinfo_calls = 0
  cpu_scoreinfo_reduced = 1
  phase7_broad_restart_v3_gate_v3_1_pass = 1
  phase7_broad_restart_v3_gate_v3_2_pass = 0
  no GPU endpoint/CIGAR/traceback/output authority
  no broad_replacement workload-matrix row
  phase7_broad_restart_v3_next_gate = oracle_min_cover_replay_shape_probe_or_non_oracle_candidate_reducer
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

The attempt-coverage seed source is the first v3 seed/index source with both
task-level scoreInfo coverage and attempt-window coverage clean on NEAT1
first1. It is still not a broad completion path because candidate attempts are
much larger than reference Align attempts. The next step must either reduce
candidate attempts without oracle legacy windows or use the oracle min-cover
as a shape probe before any first64 broad gate.

Phase 7 v3 oracle min-cover replay smoke, current:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_oracle_min_cover_replay_smoke.md
  phase7_broad_restart_v3_oracle_min_cover_replay_smoke = output_no_go
  phase7_broad_restart_v3_oracle_min_cover_replay_status = oracle_shape_probe_no_go
  required_runtime_env = FASIM_GASAL2_PHASE7_V3_ORACLE_MIN_COVER_REPLAY
  reference_align_attempts = 2,872
  candidate_min_cover_positions = 463
  candidate_align_attempts = 463
  skipped_attempts = 2,409
  candidate_align_attempts_lt_reference = 1
  digest_match = 0
  full_rows_equal = 0
  missing_rows = 11
  extra_rows = 9
  phase7_broad_restart_v3_gate_v3_2_shape_probe_pass = 0
  no GPU endpoint/CIGAR/traceback/output authority
  no broad_replacement workload-matrix row
  phase7_broad_restart_v3_next_gate = non_oracle_candidate_reducer_or_stop_seed_path
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

The oracle min-cover shape proves that reducing to 463 attempts is not enough
to preserve the full output contract. Covering legacy attempt windows by seed
position is not semantically equivalent to replaying the legacy attempt
sequence. Do not continue this shape to first64.

Phase 7 v3 seed/index path stop, current:
  document = docs/fasim_gasal2_phase7_broad_restart_v3_seed_path_stop.md
  phase7_broad_restart_v3_seed_path_stop = current_seed_index_path_stopped
  phase7_broad_restart_v3_seed_path_status =
    stopped_no_output_clean_non_oracle_reducer
  phase7_broad_restart_v3_gate_v3_1_pass = 1
  phase7_broad_restart_v3_gate_v3_2_pass = 0
  phase7_broad_restart_v3_may_continue_to_first64 = 0
  no GPU endpoint/CIGAR/traceback/output authority
  no broad_replacement workload-matrix row
  phase7_broad_restart_v3_next_gate =
    different_scoreinfo_compatible_gpu_execution_design_or_path_a_scope_decision
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

The current seed/index path has no non-oracle reducer that both preserves full
output and reduces CPU-authority Align attempts. It is stopped for broad
completion. Future Path B work must use a materially different
scoreInfo-compatible GPU execution design, or the active goal must close only
through explicit Path A scoped acceptance.

Phase 7 v4 scoreInfo-native GPU design, current:
  document = docs/fasim_gasal2_phase7_broad_restart_v4_scoreinfo_native_design.md
  phase7_broad_restart_v4_scoreinfo_native_design = defined
  phase7_broad_restart_v4_status = design_only
  phase7_broad_restart_v4_next_gate = legacy_byte_scoreinfo_shadow_first1
  phase7_broad_restart_v4_may_claim_completion = 0
  phase7_broad_restart_v4_gate_v4_1_pass = 0
  phase7_broad_restart_v4_gate_v4_2_pass = 0
  phase7_broad_restart_v4_gate_v4_3_pass = 0
  no GPU endpoint/CIGAR/traceback/output authority
  no broad_replacement workload-matrix row
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

This design selects the only currently valid Path B branch after the seed path
stop: a legacy scoreInfo-compatible GPU execution source. It must reproduce
Fasim scoreInfo semantics directly, including legacy byte saturation, bias,
word upgrade, window-of-5 peak clustering, scoreInfo order, attempt-window
order, tie policy, alphabet translation, and gap configuration. The next
runtime gate is shadow-only on NEAT1 first1; GPU scoreInfo rows must not become
output authority.

Required v4 scoreInfo contract:
  legacy_ssw_byte_saturation = required
  legacy_bias_behavior = required
  legacy_word_upgrade_on_saturation = required
  legacy_window_of_5_peak_clustering = required
  legacy_scoreInfo_order = required
  legacy_attempt_window_order = required
  legacy_tie_policy = required
  scoreinfo_rows_equal = true
  scoreinfo_order_equal = true
  scoreinfo_attempt_windows_equal = true

Phase 7 v4 legacy-byte scoreInfo shadow smoke, current:
  document =
    docs/fasim_gasal2_phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke.md
  phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke =
    host_contract_clean_needs_gpu
  phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_status =
    host_reconstruction_clean_gpu_rows_zero
  required_runtime_env =
    FASIM_GASAL2_PHASE7_V4_LEGACY_BYTE_SCOREINFO_SHADOW
  runtime_default = off
  phase7_v4_legacy_byte_scoreinfo_shadow_active = 1
  phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_rows_equal = 1
  phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_order_equal = 1
  phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_attempt_windows_equal = 1
  phase7_v4_legacy_byte_scoreinfo_shadow_host_contract_pass = 1
  phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 0
  phase7_v4_legacy_byte_scoreinfo_shadow_gate_v4_1_pass = 0
  source = host_column_score_reconstruction
  phase7_broad_restart_v4_gate_v4_1_pass = 0
  phase7_broad_restart_v4_next_gate =
    gpu_legacy_byte_scoreinfo_shadow_first1
  no GPU endpoint/CIGAR/traceback/output authority
  no broad_replacement workload-matrix row
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

This smoke proves the host-side legacy scoreInfo reconstruction contract from
`aligner.preAlignColumnScores()` and legacy window-of-5 peak clustering. It
does not prove a GPU scoreInfo source because `gpu_scoreinfo_rows = 0`.

Phase 7 v4 GPU legacy-byte scoreInfo shadow smoke, current:
  document =
    docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke.md
  phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke =
    gpu_contract_clean_first1
  phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_status =
    first1_gpu_rows_equal_not_broad
  required_runtime_env =
    FASIM_GASAL2_PHASE7_V4_GPU_LEGACY_BYTE_SCOREINFO_SHADOW
  runtime_default = off
  phase7_v4_legacy_byte_scoreinfo_shadow_tasks = 48
  phase7_v4_legacy_byte_scoreinfo_shadow_cpu_scoreinfo_rows = 718
  phase7_v4_legacy_byte_scoreinfo_shadow_host_scoreinfo_rows = 718
  phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 718
  phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_rows_equal = 1
  phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_order_equal = 1
  phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_attempt_windows_equal = 1
  phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_mismatches = 0
  phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_false_negatives = 0
  phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_extra_required_attempts = 0
  phase7_v4_legacy_byte_scoreinfo_shadow_gate_v4_1_pass = 1
  source = gpu_legacy_byte_scoreinfo
  phase7_broad_restart_v4_gate_v4_1_pass = 1
  phase7_broad_restart_v4_runtime_next_gate =
    gpu_legacy_byte_scoreinfo_source_first1_cpu_authority_replay
  no GPU endpoint/CIGAR/traceback/output authority
  no broad_replacement workload-matrix row
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

This GPU first1 smoke passes Gate v4.1 only. It proves shadow equality for
scoreInfo rows, order, and attempt-window order on NEAT1 first1, but it does
not yet prove CPU-authority replay from GPU rows, Align-side work reduction, a
first64 broad gate, or a `broad_replacement` workload-matrix row. The next
valid Path B runtime gate is GPU scoreInfo source first1 CPU-authority replay.

Phase 7 v4 GPU legacy-byte scoreInfo source replay smoke, current:
  document =
    docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke.md
  phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke =
    cpu_authority_replay_clean_first1
  phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_status =
    first1_replay_clean_needs_first64_broad_gate
  required_runtime_env =
    FASIM_GASAL2_PHASE7_V4_GPU_LEGACY_BYTE_SCOREINFO_SOURCE_REPLAY
  runtime_default = off
  phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_runtime_smoke =
    cpu_authority_replay_first1
  phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_active = 1
  phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_digest_match = 1
  phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_rows_equal = 1
  phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_order_equal = 1
  phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_attempt_windows_equal = 1
  phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_gpu_scoreinfo_rows_gt_zero = 1
  phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempts = 2008
  phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_reference_align_attempts = 2872
  phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempt_reduction = 864
  phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_gate_v4_2_pass = 1
  phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_requested = 1
  phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_active = 1
  phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_streaming_ready = 1
  phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_scoreinfo_rows = 718
  phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_cpu_authority = 1
  phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_gpu_endpoint_cigar_traceback_output_authority = 0
  phase7_v4_legacy_byte_scoreinfo_shadow_gate_v4_2_pass = 1
  source = gpu_legacy_byte_scoreinfo_source_replay
  realpath_requested = 1
  realpath_fallbacks = 0
  realpath_extend_scoreinfo_groups = 718
  realpath_extend_align_attempts = 2008
  reference_align_attempts = 2872
  align_attempt_reduction = 864
  phase7_broad_restart_v4_gate_v4_1_pass = 1
  phase7_broad_restart_v4_gate_v4_2_pass = 1
  phase7_broad_restart_v4_gate_v4_3_pass = 0
  phase7_broad_restart_v4_runtime_next_gate =
    gpu_legacy_byte_scoreinfo_source_first64_broad_gate
  no GPU endpoint/CIGAR/traceback/output authority
  no broad_replacement workload-matrix row
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

This source replay smoke passes Gate v4.2 only. It proves that the GPU
legacy-byte scoreInfo source can feed the CPU-authority all-attempt early-stop
consumer on NEAT1 first1 with digest clean output and Align-side attempt
reduction. It is still not broad completion because it has no NEAT1 first64 or
equivalent broad wall-time gate and no `broad_replacement` workload-matrix row.

Phase 7 v4 GPU legacy-byte scoreInfo source first64 broad gate, current:
  document =
    docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate.md
  phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate =
    correctness_clean_performance_no_go
  phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_status =
    first64_correctness_clean_performance_no_go
  required_runtime_env =
    FASIM_GASAL2_PHASE7_V4_GPU_LEGACY_BYTE_SCOREINFO_SOURCE_REPLAY
  runtime_default = off
  runtime_authority = CPU aligner.Align()
  gpu_endpoint_cigar_traceback_output_authority = 0
  baseline_wall_seconds = 86.358386
  candidate_wall_seconds = 134.744406
  candidate_vs_baseline = 0.640905
  digest_match = 1
  candidate_gate_v4_2_pass = 1
  candidate_gpu_scoreinfo_rows = 52994
  candidate_source_replay_scoreinfo_rows = 52994
  candidate_realpath_requested = 1
  candidate_realpath_fallbacks = 0
  candidate_realpath_extend_scoreinfo_groups = 52994
  candidate_realpath_extend_align_attempts = 140087
  candidate_realpath_extend_seconds = 52.1721
  candidate_realpath_extend_align_seconds = 52.0788
  reference_align_attempts = 211976
  align_attempt_reduction = 71889
  performance_gate_pass = 0
  phase7_broad_restart_v4_gate_v4_1_pass = 1
  phase7_broad_restart_v4_gate_v4_2_pass = 1
  phase7_broad_restart_v4_gate_v4_3_pass = 0
  phase7_broad_restart_v4_runtime_next_gate =
    different_gpu_execution_design_or_path_a_scope_decision
  no GPU endpoint/CIGAR/traceback/output authority
  no broad_replacement workload-matrix row
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

This first64 broad-gate run is correctness-clean but performance no-go. It
preserves digest and reduces CPU Align attempts, but candidate wall time is
134.744406s versus an 86.358386s CPU baseline, so the measured implementation
is 0.640905x baseline. Do not add a `broad_replacement` workload-matrix row
from this first64 result. The current v4 source replay implementation is
stopped for broad completion unless a different GPU execution design changes
the wall-time profile.

Phase 7 v5 fused scoreInfo consumer design, current:
  document =
    docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_design.md
  phase7_broad_restart_v5_fused_scoreinfo_consumer_design = defined
  phase7_broad_restart_v5_status = design_only
  phase7_broad_restart_v5_design_family =
    fused_gpu_scoreinfo_to_candidate_attempt_descriptors
  phase7_broad_restart_v5_differs_from_v4_source_replay = 1
  phase7_broad_restart_v5_may_claim_completion = 0
  phase7_broad_restart_v5_gate_v5_1_pass = 1
  phase7_broad_restart_v5_gate_v5_2_pass = 1
  phase7_broad_restart_v5_gate_v5_3_pass = 0
  phase7_broad_restart_v5_next_gate =
    different_gpu_execution_design_or_path_a_scope_decision
  no GPU endpoint/CIGAR/traceback/output authority
  no broad_replacement workload-matrix row before Gate v5.3 passes
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1

Phase 7 v5 implementation plan, current:
  document =
    docs/superpowers/plans/2026-06-13-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer.md
  phase7_broad_restart_v5_implementation_plan = defined
  phase7_broad_restart_v5_runtime_first_gate =
    fused_scoreinfo_consumer_descriptor_contract_first1
  phase7_broad_restart_v5_may_claim_completion = 0
  Task 1: Env, Stats, And Default-Off Telemetry
  Task 2: Descriptor Contract Runtime Smoke
  Task 3: CPU-Authority Replay First1 Gate
  Task 4: Roadmap Checkpoint And Current-State Wiring
  Task 5: First64 Broad Gate Characterization
  make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-implementation-plan

Phase 7 v5 fused scoreInfo consumer runtime smoke, current:
  document =
    docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke.md
  phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke =
    post_scoreinfo_descriptor_scaffold_no_go
  phase7_broad_restart_v5_runtime_scaffold_requested = 1
  phase7_broad_restart_v5_runtime_scaffold_active = 1
  phase7_broad_restart_v5_runtime_scaffold_gpu_descriptor_attempts = 2872
  phase7_broad_restart_v5_runtime_scaffold_descriptor_false_negatives = 0
  phase7_broad_restart_v5_runtime_scaffold_missing_required_attempts = 0
  phase7_broad_restart_v5_runtime_scaffold_scoreinfo_prealign_reduced = 0
  phase7_broad_restart_v5_runtime_scaffold_cpu_align_authority = 1
  phase7_broad_restart_v5_runtime_scaffold_gpu_endpoint_cigar_traceback_output_authority = 0
  phase7_broad_restart_v5_runtime_scaffold_next_gate =
    true_pre_scoreinfo_fused_descriptor_source
  phase7_broad_restart_v5_may_claim_completion = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-fused-scoreinfo-consumer-runtime-smoke

Phase 7 v5 true pre-scoreInfo descriptor source design, current:
  document =
    docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design.md
  phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design =
    defined
  phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_status =
    design_only
  phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_may_claim_completion = 0
  phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate =
    runtime_smoke_true_pre_scoreinfo_descriptor_source_first1
  required_source_boundary:
    Do not use CPU aligner.preAlign() or any CPU legacy scoreInfo producer as the descriptor source.
    Do not materialize the full legacy scoreInfo row stream as a host-visible promoted interface.
    source_is_pre_scoreinfo = 1
    scoreinfo_prealign_reduced = 1
    gpu_descriptor_attempts > 0
    descriptor_false_negatives = 0
    missing_required_attempts = 0
    candidate attempts stay below all-column replay scale
    gpu_endpoint_cigar_traceback_output_authority = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-design

Phase 7 v5 true pre-scoreInfo descriptor source env scaffold, current:
  document =
    docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_env_scaffold.md
  phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_env_scaffold =
    fail_closed_no_source
  required_runtime_env =
    FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE
  phase7_v5_true_pre_scoreinfo_descriptor_source_requested = 1
  phase7_v5_true_pre_scoreinfo_descriptor_source_active = 0
  phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo = 0
  phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced = 0
  phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_attempts = 0
  phase7_v5_true_pre_scoreinfo_descriptor_source_cpu_align_authority = 1
  phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_endpoint_cigar_traceback_output_authority = 0
  phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass = 0
  phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate =
    runtime_smoke_true_pre_scoreinfo_descriptor_source_first1
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-env-scaffold

Phase 7 v5 true pre-scoreInfo descriptor source strict runtime smoke, current:
  document =
    docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.md
  phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke =
    gate_v5_1_pass_first1
  strict_gate_target =
    check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke
  phase7_v5_true_pre_scoreinfo_descriptor_source_requested = 1
  phase7_v5_true_pre_scoreinfo_descriptor_source_active = 1
  phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo = 1
  phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced = 1
  phase7_v5_true_pre_scoreinfo_descriptor_source_descriptor_false_negatives = 0
  phase7_v5_true_pre_scoreinfo_descriptor_source_missing_required_attempts = 0
  phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass = 1
  existing_v4_gpu_source_materializes_host_visible_scoreinfo_rows = 1
  existing_cuda_api_emits_prealign_cuda_peaks_not_attempt_descriptors = 1
  do_not_rebrand_v4_source_replay_as_v5 = 1
  next_required_gate = phase7_gate_v5_2_cpu_authority_replay_first1
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke

Phase 7 v5 CPU-authority replay smoke, current:
  document =
    docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_smoke.md
  phase7_broad_restart_v5_cpu_authority_replay_smoke =
    gate_v5_2_pass_first1
  strict_gate_target =
    check-fasim-gasal2-phase7-v5-cpu-authority-replay-runtime-smoke
  root_cause_fix = legacy_float_identity_cutlength_descriptor_generation
  phase7_v5_cpu_authority_replay_requested = 1
  phase7_v5_cpu_authority_replay_active = 1
  phase7_v5_cpu_authority_replay_source_is_pre_scoreinfo = 1
  phase7_v5_cpu_authority_replay_scoreinfo_prealign_reduced = 1
  phase7_v5_cpu_authority_replay_gpu_descriptor_scoreinfos = 718
  phase7_v5_cpu_authority_replay_gpu_descriptor_attempts = 2872
  phase7_v5_cpu_authority_replay_reference_align_attempts = 2872
  phase7_v5_cpu_authority_replay_candidate_align_attempts = 2008
  phase7_v5_cpu_authority_replay_descriptor_false_negatives = 0
  phase7_v5_cpu_authority_replay_missing_required_attempts = 0
  phase7_v5_cpu_authority_replay_cpu_align_authority = 1
  phase7_v5_cpu_authority_replay_gpu_endpoint_cigar_traceback_output_authority = 0
  phase7_v5_cpu_authority_replay_full_rows_equal = 1
  phase7_v5_cpu_authority_replay_digest_match = 1
  phase7_v5_cpu_authority_replay_missing_rows = 0
  phase7_v5_cpu_authority_replay_extra_rows = 0
  phase7_v5_cpu_authority_replay_triplex_mismatches = 0
  phase7_v5_cpu_authority_replay_gate_v5_2_pass = 1
  candidate_align_attempts < reference_align_attempts
  phase7_broad_restart_v5_gate_v5_2_pass = 1
  next_required_gate = different_gpu_execution_design_or_path_a_scope_decision
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-smoke

Phase 7 v5 CPU-authority replay first64 broad gate, current:
  document =
    docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate.md
  phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate =
    correctness_clean_performance_no_go
  phase7_broad_restart_v5_cpu_authority_replay_first64_status =
    first64_correctness_clean_performance_no_go
  phase7_broad_restart_v5_first64_baseline_wall_seconds = 87.827405
  phase7_broad_restart_v5_first64_candidate_wall_seconds = 124.399845
  phase7_broad_restart_v5_first64_candidate_vs_baseline = 0.706009
  phase7_broad_restart_v5_first64_digest_match = 1
  phase7_broad_restart_v5_first64_full_rows_equal = 1
  phase7_broad_restart_v5_first64_candidate_align_attempts = 115561
  phase7_broad_restart_v5_first64_reference_align_attempts = 211976
  phase7_broad_restart_v5_first64_align_attempt_reduction = 96415
  phase7_broad_restart_v5_first64_missing_required_attempts = 624
  phase7_broad_restart_v5_first64_fallback_accounting_clean = 0
  phase7_broad_restart_v5_gate_v5_3_pass = 0
  phase7_broad_restart_v5_runtime_next_gate =
    different_gpu_execution_design_or_path_a_scope_decision
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-first64-broad-gate

Phase 7 post-v5.3 architecture decision, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_architecture_decision.md
  phase7_post_v5_3_architecture_decision = defined
  phase7_post_v5_3_current_v5_status = stopped_no_go
  phase7_post_v5_3_next_gate =
    post_v5_3_task_frontier_certificate_first1_smoke
  path_a_user_acceptance_required = 1
  path_b_new_broad_architecture_required = 1
  current_decision = selected_task_frontier_certificate_or_path_a_acceptance
  next_required_gate = post_v5_3_task_frontier_certificate_first1_smoke
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-architecture-decision

Phase 7 post-v5.3 new architecture design, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_architecture_design.md
  phase7_post_v5_3_new_architecture_design = defined
  phase7_post_v5_3_design_family =
    gpu_resident_scoreinfo_consumer_summary_with_cpu_authority_replay
  phase7_post_v5_3_new_architecture_may_implement = 1
  phase7_post_v5_3_new_architecture_may_claim_completion = 0
  required_runtime_env =
    FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY
  next_required_gate = post_v5_3_gpu_consumer_summary_first1_smoke
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-architecture-design

Phase 7 post-v5.3 GPU consumer summary env scaffold, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_env_scaffold.md
  phase7_post_v5_3_gpu_consumer_summary_env_scaffold =
    fail_closed_no_source
  required_runtime_env =
    FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY
  phase7_post_v5_3_gpu_consumer_summary_requested = 1
  phase7_post_v5_3_gpu_consumer_summary_active = 0
  phase7_post_v5_3_gpu_consumer_summary_gate_first1_pass = 0
  next_required_gate = post_v5_3_gpu_consumer_summary_first1_smoke
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-gpu-consumer-summary-env-scaffold

Phase 7 post-v5.3 GPU consumer summary first-attempt no-go, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go.md
  phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go = recorded
  implementation_shape = first_descriptor_per_scoreinfo_gpu_summary
  runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1
  workload = NEAT1 first1
  gpu_consumer_reduces_before_host_transfer = 1
  gpu_selected_attempts = 718
  reference_align_attempts = 2872
  candidate_align_attempts = 718
  baseline_lite_rows = 19
  candidate_lite_rows = 25
  external_digest_match = 0
  external_full_rows_equal = 0
  phase7_post_v5_3_gpu_consumer_summary_external_digest_match = 0
  phase7_post_v5_3_gpu_consumer_summary_external_full_rows_equal = 0
  phase7_post_v5_3_gpu_consumer_summary_gpu_selected_attempts = 718
  phase7_post_v5_3_gpu_consumer_summary_candidate_align_attempts = 718
  phase7_post_v5_3_gpu_consumer_summary_reference_align_attempts = 2872
  phase7_post_v5_3_gpu_consumer_summary_next_gate =
    stronger_post_v5_3_consumer_summary_design_or_path_a_acceptance
  phase7_post_v5_3_gpu_consumer_summary_first_attempt_status = no_go
  phase7_post_v5_3_gpu_consumer_summary_first1_gate_pass = 0
  next_required_gate = stronger_post_v5_3_consumer_summary_design_or_path_a_acceptance
  do_not_run_first64_from_this_probe = 1
  do_not_add_broad_replacement_row_from_this_probe = 1
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-gpu-consumer-summary-first-attempt-no-go

Phase 7 post-v5.3 stronger consumer summary design, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_design.md
  phase7_post_v5_3_stronger_consumer_summary_design = defined
  phase7_post_v5_3_stronger_consumer_summary_status = design_only
  phase7_post_v5_3_stronger_consumer_summary_may_implement = 1
  phase7_post_v5_3_stronger_consumer_summary_may_claim_completion = 0
  previous_status = first_descriptor_per_scoreinfo_no_go
  required_next_design_property =
    prefix_boundary_or_equivalent_replay_proof
  uses_prefix_boundary_or_equivalent_replay_proof = required
  arbitrary_sparse_subset = forbidden
  first_descriptor_per_scoreinfo = forbidden
  next_required_gate =
    post_v5_3_stronger_consumer_summary_first1_smoke
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-consumer-summary-design

Phase 7 post-v5.3 stronger consumer summary prefix runtime, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_prefix_no_go.md
  phase7_post_v5_3_stronger_consumer_summary_prefix_no_go = recorded
  implementation_shape = gpu_prefix_attempt_descriptors_per_scoreinfo
  new_cuda_api = prealign_cuda_emit_legacy_byte_prefix_attempt_descriptors
  prefix_1_2_3_reduce_gpu_selected_attempts_but_change_output = 1
  prefix_4_5_preserve_output_but_do_not_reduce_gpu_selected_attempts = 1
  phase7_post_v5_3_stronger_consumer_summary_first1_gate_pass = 0
  phase7_post_v5_3_stronger_consumer_summary_may_claim_completion = 0
  phase7_post_v5_3_stronger_consumer_summary_prefix_next_gate =
    different_gpu_execution_design_or_path_a_scope_decision
  next_required_gate =
    different_gpu_execution_design_or_path_a_scope_decision
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-consumer-summary-prefix-no-go

Phase 7 post-v5.3 task-frontier certificate design, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_design.md
  phase7_post_v5_3_task_frontier_certificate_design = defined
  phase7_post_v5_3_task_frontier_certificate_status = design_only
  phase7_post_v5_3_task_frontier_certificate_may_implement = 1
  phase7_post_v5_3_task_frontier_certificate_may_claim_completion = 0
  phase7_post_v5_3_design_family =
    gpu_task_frontier_certificate_with_cpu_authority_replay
  uses_task_frontier_certificate = 1
  uses_prefix_boundary_only = 0
  next_required_gate =
    post_v5_3_task_frontier_certificate_first1_smoke
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-design

Phase 7 post-v5.3 task-frontier certificate env scaffold, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_env_scaffold.md
  phase7_post_v5_3_task_frontier_certificate_env_scaffold =
    fail_closed_no_source
  phase7_post_v5_3_task_frontier_certificate_env_scaffold_status =
    superseded_by_first_attempt_no_go
  superseded_by =
    docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go.md
  runtime_env =
    FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE=1
  phase7_post_v5_3_task_frontier_certificate_requested = 1
  phase7_post_v5_3_task_frontier_certificate_active = 0
  phase7_post_v5_3_task_frontier_certificate_gate_first1_pass = 0
  runtime_smoke =
    superseded_by_first_attempt_no_go
  next_required_gate =
    stronger_task_frontier_certificate_design_or_path_a_acceptance
  phase7_post_v5_3_task_frontier_certificate_next_gate =
    stronger_task_frontier_certificate_design_or_path_a_acceptance
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-phase7-post-v5-3-task-frontier-certificate-env-runtime-smoke
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-env-scaffold

Phase 7 post-v5.3 task-frontier certificate first attempt, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go.md
  phase7_post_v5_3_task_frontier_certificate_first_attempt_status = no_go
  runtime_env =
    FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE=1
  implementation_shape = first_scoreinfo_group_per_task_certificate_probe
  task_frontier_certificate_rows = 48
  gpu_selected_attempts = 192
  v5_candidate_align_attempts = 2872
  candidate_align_attempts = 138
  reference_align_attempts = 2872
  phase7_post_v5_3_task_frontier_certificate_gpu_selected_attempts = 192
  phase7_post_v5_3_task_frontier_certificate_candidate_align_attempts = 138
  phase7_post_v5_3_task_frontier_certificate_reference_align_attempts = 2872
  external_digest_match = 0
  external_full_rows_equal = 0
  missing_rows = 17
  phase7_post_v5_3_task_frontier_certificate_external_digest_match = 0
  phase7_post_v5_3_task_frontier_certificate_external_full_rows_equal = 0
  phase7_post_v5_3_task_frontier_certificate_missing_rows = 17
  phase7_post_v5_3_task_frontier_certificate_first1_gate_pass = 0
  phase7_post_v5_3_task_frontier_certificate_may_claim_completion = 0
  next_required_gate =
    stronger_task_frontier_certificate_design_or_path_a_acceptance
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-first-attempt-no-go

Phase 7 post-v5.3 stronger task-frontier certificate design, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_design.md
  phase7_post_v5_3_stronger_task_frontier_certificate_design = defined
  phase7_post_v5_3_stronger_task_frontier_certificate_status = design_only
  phase7_post_v5_3_stronger_task_frontier_certificate_may_implement = 1
  phase7_post_v5_3_stronger_task_frontier_certificate_may_claim_completion = 0
  previous_status = first_scoreinfo_group_per_task_certificate_no_go
  required_next_design_property =
    prove skipped scoreInfo groups are output-inert before D2H
  next_required_gate =
    stronger_task_frontier_certificate_first1_smoke
  phase7_post_v5_3_stronger_task_frontier_certificate_next_gate =
    stronger_task_frontier_certificate_first1_smoke
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-task-frontier-certificate-design

Phase 7 post-v5.3 stronger task-frontier certificate feasibility, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go.md
  phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go = recorded
  phase7_post_v5_3_stronger_task_frontier_certificate_status = feasibility_no_go
  phase7_post_v5_3_stronger_task_frontier_certificate_first1_smoke_allowed = 0
  do_not_implement_current_stronger_task_frontier_runtime = 1
  do_not_run_first64_from_current_stronger_task_frontier_design = 1
  next_required_gate =
    new_pre_d2h_output_inert_proof_or_different_gpu_execution_design_or_path_a_scope_decision
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-task-frontier-certificate-feasibility-no-go

Phase 7 post-v5.3 pre-D2H output-inert proof search first1 export, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md
  export_checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export.md
  acceptance_checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1.md
  phase7_post_v5_3_pre_d2h_output_inert_proof_search_design = defined
  phase7_post_v5_3_pre_d2h_output_inert_proof_search_status = first1_export_pass
  phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export = pass
  phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_implement = 1
  phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion = 0
  next_required_gate =
    pre_d2h_output_inert_proof_acceptance_first1
  phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1 = no_go
  phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_status =
    first1_no_accepted_proof
  accepted_pre_d2h_proof_families = 0
  reducing_runtime_allowed = 0
  first64_runtime_allowed = 0
  current_execution_gate =
    implement_new_pre_d2h_proof_family_first1_smoke_or_path_a_acceptance
  current_next_pr =
    fasim: new pre-D2H proof family first1 smoke or scope acceptance
  proof_search_rows = 2872
  task_count = 48
  scoreinfo_count = 718
  attempt_count = 2872
  runtime_reduction_enabled = 0
  gpu_output_authority = 0
  gate_first1_export_pass = 1
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-design
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-first1-export
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-acceptance-first1

Phase 7 post-v5.3 new pre-D2H proof-family or scope decision, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision.md
  phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision = defined
  previous_checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1.md
  previous_status = first1_no_accepted_proof
  path_a_user_acceptance_required = 1
  path_b_new_pre_d2h_proof_family_required = 1
  runtime_reduction_enabled = 0
  first64_runtime_allowed = 0
  gpu_endpoint_cigar_traceback_output_authority = 0
  gpu_output_authority = 0
  candidate_proof_false_negatives = 0
  candidate_proof_missing_required_attempts = 0
  candidate_selected_attempts < v5_candidate_align_attempts
  candidate_selected_attempts < reference_align_attempts
  candidate_uses_final_cpu_output_as_runtime_proof = 0
  source_is_pre_scoreinfo = 1
  source_is_legacy_byte_cuda = 1
  CPU aligner.Align() authority = 1
  do_not_reuse_failed_proof_search_aggregate_export = 1
  do_not_use_final_cpu_output_as_runtime_proof = 1
  current_execution_gate =
    implement_new_pre_d2h_proof_family_first1_smoke_or_path_a_acceptance
  current_next_pr =
    fasim: new pre-D2H proof family first1 smoke or scope acceptance
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-pre-d2h-proof-family-or-scope-decision

Phase 7 post-v5.3 new pre-D2H proof-family first1 feasibility no-go, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go.md
  phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go = recorded
  current_descriptor_stream = PreAlignCudaAttemptDescriptor
  current_descriptor_stream_can_prove_output_inert_skips = 0
  accepted_pre_d2h_proof_families = 0
  new_pre_d2h_proof_family_first1_smoke_allowed = 0
  reducing_runtime_allowed = 0
  first64_runtime_allowed = 0
  do_not_implement_reducing_runtime_from_current_descriptor_stream = 1
  different_gpu_execution_design_required = 1
  path_a_user_acceptance_required = 1
  current_execution_gate =
    different_gpu_execution_design_or_path_a_scope_acceptance
  current_next_pr =
    fasim: design different GPU execution design or scope acceptance
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-pre-d2h-proof-family-first1-feasibility-no-go

Phase 7 post-v5.3 different GPU execution design or scope acceptance, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_or_scope_acceptance.md
  phase7_post_v5_3_different_gpu_execution_design_or_scope_acceptance = recorded
  path_a_user_acceptance_required = 1
  path_b_different_gpu_execution_design_required = 1
  path_b_current_implementation_available = 0
  path_b_runtime_pr_allowed = 0
  next_valid_work =
    path_a_scoped_acceptance_or_new_engine_design_doc
  current_next_pr =
    fasim: path A scope acceptance or new GPU engine design
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-different-gpu-execution-design-or-scope-acceptance

Phase 7 post-v5.3 new GPU engine design, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design.md
  phase7_post_v5_3_new_gpu_engine_design = defined
  design_family = fasim_compatible_gpu_scoreinfo_attempt_engine
  runtime_pr_allowed = 0
  current_runtime_implementation_available = 0
  next_valid_gate =
    phase7_new_gpu_engine_spec_or_path_a_acceptance
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-design

Phase 7 post-v5.3 new GPU engine spec or Path A acceptance, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance.md
  phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance = defined
  path_a_user_acceptance_recorded = 0
  path_a_scoped_completion_may_close_goal = 0
  path_b_spec_checkpoint_defined = 1
  path_b_runtime_implementation_allowed = 0
  runtime_pr_allowed = 0
  next_valid_gate =
    phase7_new_gpu_engine_first1_spec_or_path_a_acceptance
  current_next_pr =
    fasim_new_gpu_engine_first1_spec_or_path_a_acceptance
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-spec-or-path-a-acceptance

Phase 7 post-v5.3 new GPU engine first1 spec or Path A acceptance, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance.md
  phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance = defined
  path_a_user_acceptance_recorded = 0
  path_a_scoped_completion_may_close_goal = 0
  path_b_first1_spec_defined = 1
  path_b_first1_runtime_allowed = 0
  runtime_pr_allowed = 0
  next_valid_gate =
    phase7_new_gpu_engine_first1_shadow_or_path_a_acceptance
  current_next_pr =
    fasim_new_gpu_engine_first1_shadow_or_path_a_acceptance
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-spec-or-path-a-acceptance

Phase 7 post-v5.3 new GPU engine first1 shadow redirect, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect.md
  phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect = recorded
  reviewed_existing_runtime =
    FASIM_GASAL2_PHASE7_V5_CPU_AUTHORITY_REPLAY
  reviewed_existing_source =
    PreAlignCudaAttemptDescriptor
  existing_v5_cpu_authority_replay_first1_gate_pass = 1
  existing_v5_cpu_authority_replay_matches_new_engine_spec = 0
  new_gpu_engine_first1_shadow_gate_pass = 0
  next_valid_gate =
    implement_new_gpu_engine_first1_shadow_or_path_a_acceptance
  current_next_pr =
    fasim_new_gpu_engine_first1_shadow_runtime_or_path_a_acceptance
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-shadow-redirect

Phase 7 post-v5.3 new GPU engine first1 shadow scaffold, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold.md
  phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold = fail_closed
  required_runtime_env =
    FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_FIRST1_SHADOW
  requested = 1
  active = 0
  missing_certificate_producer = 1
  certificate_valid_before_d2h = 0
  fallback_to_full_cpu_replay = 1
  cpu_align_authority = 1
  gpu_endpoint_cigar_traceback_output_authority = 0
  new_gpu_engine_first1_shadow_gate_pass = 0
  runtime_reduction_enabled = 0
  first64_runtime_allowed = 0
  next_valid_gate =
    implement_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance
  current_next_pr =
    fasim_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-shadow-scaffold

Phase 7 post-v5.3 new GPU engine certificate CUDA API, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api.md
  phase7_post_v5_3_new_gpu_engine_certificate_cuda_api =
    fail_closed_api_scaffold
  required_runtime_env =
    FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_CERTIFICATE_CUDA_API
  new_cuda_api = prealign_cuda_emit_new_engine_skipped_work_certificates
  certificate_producer_active = 0
  certificate_valid_before_d2h = 0
  final_cpu_output_membership_required_for_certificate = 0
  runtime_reduction_enabled = 0
  first1_runtime_allowed = 0
  first64_runtime_allowed = 0
  cpu_align_authority = 1
  gpu_endpoint_cigar_traceback_output_authority = 0
  certificate_cuda_api_gate_pass = 0
  next_valid_gate =
    implement_new_gpu_engine_certificate_producer_first1_or_path_a_acceptance
  current_next_pr =
    fasim_new_gpu_engine_certificate_producer_first1_or_path_a_acceptance
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-cuda-api

Phase 7 post-v5.3 new GPU engine certificate producer first1, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_producer_first1.md
  phase7_post_v5_3_new_gpu_engine_certificate_producer_first1 =
    producer_first1_synthetic_gate
  previous_checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api.md
  certificate_producer_active = 1
  certificate_valid_before_d2h = 1
  final_cpu_output_membership_required_for_certificate = 0
  certificate_false_negatives = 0
  certificate_missing_required_attempts = 0
  skipped_groups = 1
  skipped_attempts = 1
  conservative_fallback_groups = 0
  certificate_cuda_api_gate_pass = 1
  runtime_reduction_enabled = 0
  first1_runtime_reduction_allowed = 0
  first64_runtime_allowed = 0
  output_authority_changed = 0
  cpu_align_authority = 1
  gpu_endpoint_cigar_traceback_output_authority = 0
  next_valid_gate = first1_reducing_runtime_with_certificate_or_no_go
  current_next_pr = fasim_new_gpu_engine_first1_reducing_runtime_or_no_go
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-producer-first1

Phase 7 post-v5.3 new GPU engine first1 reducing runtime, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.md
  phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go = recorded
  previous_checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_producer_first1.md
  previous_gate = first1_reducing_runtime_with_certificate_or_no_go
  certificate_producer_active = 1
  certificate_valid_before_d2h = 1
  certificate_producer_is_synthetic_api_gate = 1
  real_fasim_runtime_certificate_source = 0
  real_fasim_runtime_work_drop_path = 0
  prealign_cuda_emit_new_engine_skipped_work_certificates_runtime_call_count = 0
  runtime_reduction_enabled = 0
  first1_runtime_reduction_gate_pass = 0
  first64_runtime_allowed = 0
  scoreInfo_prealign_reduced = 0
  align_side_reduced = 0
  fallback_accounting_clean = 0
  path_b_current_implementation_available = 0
  path_b_runtime_pr_allowed = 0
  path_b_different_gpu_execution_design_required = 1
  path_a_user_acceptance_required = 1
  current_execution_gate = path_a_scoped_acceptance_or_new_engine_design_doc
  current_next_pr = fasim_path_a_scope_acceptance_or_new_gpu_engine_design
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-reducing-runtime-no-go

Phase 7 post-v5.3 new GPU engine design after first1 no-go, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md
  phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go = defined
  previous_checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.md
  design_family = real_source_fasim_compatible_gpu_scoreinfo_attempt_engine
  not_synthetic_certificate_producer_continuation = 1
  not_v5_cpu_authority_replay_relabel = 1
  not_current_descriptor_stream_continuation = 1
  requires_real_fasim_runtime_certificate_source = 1
  requires_real_fasim_runtime_work_drop_point = 1
  path_b_real_source_design_checkpoint_defined = 1
  path_b_runtime_pr_allowed = 0
  current_execution_gate =
    phase7_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance
  current_next_pr =
    fasim_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-design-after-first1-no-go

Phase 7 post-v5.3 new GPU engine real-source first1 spec, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md
  phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance = defined
  previous_checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md
  real_runtime_hook_location =
    scoreInfo/preAlign task construction before CPU replay attempts are selected
  certificate_producer_location =
    GPU scoreInfo/attempt engine before D2H
  certificate_consumer_location =
    CPU replay scheduler before dropping replay work
  work_drop_decision_point =
    before CPU aligner.Align() attempts are skipped
  path_b_real_source_first1_spec_defined = 1
  path_b_first1_shadow_runtime_allowed = 0
  path_b_first64_runtime_allowed = 0
  next_valid_gate =
    phase7_new_gpu_engine_real_source_first1_shadow_or_path_a_acceptance
  current_next_pr =
    fasim_new_gpu_engine_real_source_first1_shadow_or_path_a_acceptance
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-real-source-first1-spec-or-path-a-acceptance

Phase 7 post-v5.3 new GPU engine real-source certificate source first1, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md
  phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1 =
    source_only_pre_drop_runtime_hook
  required_runtime_env =
    FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_REAL_SOURCE_CERTIFICATE_SOURCE
  telemetry_prefix =
    benchmark.fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_
  real_fasim_runtime_certificate_source = 1
  real_fasim_runtime_work_drop_path = 0
  runtime_certificate_is_synthetic = 0
  source_is_pre_drop = 1
  source_is_legacy_byte_cuda = 1
  candidate_uses_final_cpu_output_as_runtime_proof = 0
  source_task_count > 0
  source_scoreinfo_count > 0
  source_attempt_count > 0
  missing_certificate = 0
  fallback_to_full_cpu_replay = 1
  runtime_reduction_enabled = 0
  runtime_work_drop_enabled = 0
  gate_first1_source_pass = 1
  gate_first1_pass = 0
  next_valid_gate = design_pre_drop_output_inert_work_drop_proof
  current_next_pr = fasim_new_gpu_engine_pre_drop_work_drop_proof_design
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-real-source-certificate-source
  make check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-real-source-certificate-source-runtime-smoke

Phase 7 post-v5.3 new GPU engine pre-drop work-drop proof design, current:
  document =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md
  phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design =
    defined
  design_only = 1
  previous_checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md
  previous_gate = design_pre_drop_output_inert_work_drop_proof
  real_source_certificate_source_gate_pass = 1
  real_fasim_runtime_certificate_source = 1
  real_fasim_runtime_work_drop_path = 0
  runtime_certificate_is_synthetic = 0
  source_is_pre_drop = 1
  gate_first1_source_pass = 1
  gate_first1_pass = 0
  proof_must_be_pre_drop = 1
  proof_must_be_output_inert = 1
  proof_must_not_use_final_cpu_output_membership = 1
  proof_must_not_use_top5_only_contract = 1
  proof_must_cover_complete_row_set = 1
  certificate_production_separate_from_consumption = 1
  consumer_must_fail_closed = 1
  fallback_to_full_cpu_replay = 1
  runtime_reduction_enabled = 0
  runtime_work_drop_enabled = 0
  first1_runtime_reduction_gate_pass = 0
  first64_runtime_allowed = 0
  next_valid_gate =
    implement_pre_drop_output_inert_work_drop_proof_first1_shadow
  current_next_pr =
    fasim_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-design

Phase 7 v5 CUDA descriptor emission design, current:
  document =
    docs/fasim_gasal2_phase7_broad_restart_v5_cuda_descriptor_emission_design.md
  phase7_broad_restart_v5_cuda_descriptor_emission_design = defined
  phase7_broad_restart_v5_cuda_descriptor_emission_status = design_only
  phase7_broad_restart_v5_cuda_descriptor_emission_may_claim_completion = 0
  previous_checkpoint = no_go_needs_cuda_descriptor_emission_kernel
  required_runtime_env =
    FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE
  new_cuda_api = prealign_cuda_emit_legacy_byte_attempt_descriptors
  input_contract = encoded_targets_plus_min_scores_plus_task_metadata
  output_contract = compact_attempt_descriptors_not_scoreinfo_rows
  host-visible full legacy scoreInfo row stream = forbidden
  CPU aligner.Align() authority replay = 1
  GPU endpoint/CIGAR/traceback/output authority = 0
  next_gate = runtime_smoke_true_pre_scoreinfo_descriptor_source_first1
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-descriptor-emission-design

Phase 7 full-align verifier design spec, current:
  document =
    docs/fasim_gasal2_phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance.md
  phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance =
    defined
  previous_checkpoint =
    docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md
  path_b_design_family =
    gasal2_full_align_result_with_cpu_verifier_certificate
  path_b_full_align_verifier_spec_defined = 1
  path_b_full_align_verifier_first1_fail_closed_shadow_allowed = 1
  runtime_reduction_enabled = 0
  runtime_work_drop_enabled = 0
  first64_runtime_allowed = 0
  next_valid_gate =
    phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
  current_execution_gate =
    phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
  current_next_pr =
    fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
  make check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-design-spec-or-path-a-acceptance

The v5 design is the next Path B shape after the v4 performance no-go.

Required design differences:
  Do not materialize the full legacy scoreInfo row stream as a host-visible intermediate.
  Compute legacy byte scoreInfo and consume the row stream in the same GPU execution design.
  Emit compact candidate attempt descriptors, not endpoint, CIGAR, traceback, output, or digest authority.

CPU `aligner.Align()` remains the only endpoint, CIGAR, traceback, output, and
digest authority.

Required v5 broad gates:
  scoreInfo/preAlign work reduced or replaced = required
  Align-side work reduced or replaced = required
  candidate_wall_seconds < baseline_wall_seconds = required
  fallbacks = 0 for the claimed GPU path = required
  full row-set/digest equality = required

The current v4 source replay must not continue as the broad path. The next
runtime gate is `fused_scoreinfo_consumer_descriptor_contract_first1`.

If neither scoped completion is accepted nor a new Phase 7 broad architecture
passes, the active goal remains open:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

That keeps the active goal aligned with the documented completion criteria
instead of turning a bounded short-query milestone into a broad claim.

## Summary

The goal can be completed in two ways:

```text
Scoped completion:
  accept the current short-query/top5/archive product contract and document it
  as the delivered objective.

Broad completion:
  build a new architecture that preserves full output equivalence and beats CPU
  on broad workloads, especially NEAT1-like long-query gates.
```

The current repository is closest to scoped completion. The completion-decision
gate explicitly keeps the active broad goal open unless the user accepts the
narrowed scoped contract as completion. Broad completion requires a new
architecture, not more tuning of the current replay or score-only paths.

## Current Phase 7 Cursor

```text
docs/fasim_gasal2_phase7_gasal2_full_align_verifier_first1_shadow_scaffold.md
phase7_gasal2_full_align_verifier_first1_shadow_scaffold = fail_closed_shadow
phase7_full_align_verifier_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
path_b_full_align_verifier_first1_shadow_scaffold = 1
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_gasal2_full_align_verifier_first1_shadow_consumer_or_no_go
current_execution_gate = phase7_gasal2_full_align_verifier_first1_shadow_consumer_or_no_go
current_next_pr = fasim_gasal2_full_align_verifier_first1_shadow_consumer_or_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Current Phase 7 Cursor

```text
docs/fasim_gasal2_phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go.md
phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go = recorded
phase7_full_align_verifier_first1_shadow_consumer_status = no_go_no_gpu_full_align_proposals
accepted_full_align_verifier_consumer = 0
accepted_full_align_verifier_certificate = 0
path_b_full_align_verifier_family_stopped = 1
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go
current_execution_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Historical Pre-Native-DP Scaffold Cursor

```text
docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance.md
phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance = defined
phase7_native_cuda_fasim_dp_engine_design_spec_status = spec_defined
path_b_native_cuda_fasim_dp_engine_spec_defined = 1
path_b_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_allowed = 1
path_b_full_align_verifier_family_stopped = 1
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
current_execution_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Historical Pre-Native-DP Fork Cursor

```text
docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold.md
phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold = fail_closed_shadow
phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
path_b_native_cuda_fasim_dp_engine_first1_shadow_scaffold = 1
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
current_execution_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Current Phase 7 Cursor

```text
docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance.md
phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance = defined
phase7_gpu_upper_bound_reject_certificate_design_spec_status = spec_defined
design_family = gpu_upper_bound_reject_certificate_engine
path_b_gpu_upper_bound_reject_certificate_first1_fail_closed_shadow_allowed = 1
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
historical_execution_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go
historical_next_pr = fasim_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go
docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go.md
phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go = recorded
phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_status = no_go_no_rejected_work
path_b_gpu_upper_bound_reject_certificate_family_stopped = 1
docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go.md
path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go = recorded
path_b_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go_status = required_not_defined
path_b_new_design_family_after_gpu_upper_bound_reject_certificate_no_go = undefined
docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md
phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance = defined
phase7_gpu_exact_work_unit_compaction_design_spec_status = spec_defined
design_family = gpu_exact_work_unit_compaction_replay
current_execution_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Historical pre-native-DP-shadow cursor:

```text
docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go.md
path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go = recorded
path_b_different_gpu_execution_design_after_full_align_verifier_no_go_status = design_defined
path_b_new_design_family_after_full_align_verifier_no_go = native_cuda_fasim_dp_certificate_engine
next_valid_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
current_execution_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
current_next_pr = fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
```
