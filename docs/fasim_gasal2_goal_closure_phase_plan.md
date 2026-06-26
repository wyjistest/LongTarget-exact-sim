# Fasim GASAL2 Goal Closure Phase Plan

This document is a closure plan, not a completion claim.

It exists to stop the active GASAL2/Fasim work from drifting between useful
milestones and the original broad objective. The active broad objective remains:

```text
Use GASAL2/GPU to materially accelerate or replace the scoreInfo/preAlign /
Align-related Fasim path while preserving the required output contract.
```

Until Phase 8 passes:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Completion Paths

There are two close paths. They are deliberately separate.

```text
Path A: scoped completion
  Valid only if the user explicitly accepts the narrowed deliverable:
    short-query/H19 top5 GASAL2 artifact
    MEG3-like complete-record grouping where claimed
    archive-first restored output where claimed

  It does not claim:
    aligner.Align replacement
    universal scoreInfo/preAlign replacement
    long-query NEAT1/MALAT1 broad replacement
    GPU endpoint/CIGAR/traceback/output/digest authority

Path B: broad completion
  Required while the original broad objective remains active.

  It must prove:
    full row-set/digest equality
    runtime win over CPU authority
    scoreInfo/preAlign work reduced or replaced
    Align-side work reduced or replaced
    fallback accounting clean
```

Do not mix Path A evidence into Path B completion.

## Current Cursor

```text
current_path = Path B
current_phase = Phase 7
current_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
runtime_pr_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
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

The existing v5 CPU-authority replay must not be relabelled as the new GPU
engine. It uses the old `PreAlignCudaAttemptDescriptor` stream and does not
provide the new pre-D2H skipped-work certificate required by the current Phase 7
contract.

Historical Phase 7.3 no-go cursor:

```text
current_gate = path_a_scoped_acceptance_or_new_engine_design_doc
current_next_pr = fasim_path_a_scope_acceptance_or_new_gpu_engine_design
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
```

## Authority Model

These remain true for every phase until a separate equivalence proof changes
the contract:

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

Forbidden shortcuts:

```text
Do not use final CPU output membership as runtime proof.
Do not run first64 from a failed first1 gate.
Do not promote output-drift speedups.
Do not use top5-only evidence as broad completion.
Do not use archive-only evidence as broad completion.
```

## Phase Ladder

### Phase 0 - Reproducibility

Purpose:

```text
Make every claimed GASAL2/Fasim result rebuildable from a clean checkout.
```

Do:

```text
pin the GASAL2 upstream commit
track local GASAL2 patches
keep setup/build targets idempotent
record CUDA version, SM arch, GASAL2_MAX_QUERY_LEN, and GASAL2_N_CODE
remove reliance on untracked .tmp/GASAL2 edits or local binaries
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase0-reproducibility
make check-fasim-gasal2-reproducible-setup
make setup-gasal2
make build-fasim-gasal2
```

Advance when:

```text
clean checkout can rebuild the exact GASAL2 bridge and Fasim binary.
```

Stop if:

```text
any claimed result depends on machine-local GASAL2 state.
```

### Phase 1 - Scope Decision

Purpose:

```text
Decide whether Path A scoped completion is allowed to close the active goal.
```

Do:

```text
present scoped claims and non-claims together
record explicit user acceptance before using Path A
keep scoped acceleration default-off unless separately accepted
```

Path A may proceed only when:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

Stop Path A if:

```text
the user still wants the original broad scoreInfo/preAlign/Align goal.
```

### Phase 2 - Full-Output Baseline

Purpose:

```text
Keep restored TFOsorted/full output correct before any full-output speed claim.
```

Do:

```text
preserve restored row-set equality
preserve digest equality
itemize convert/output wall time
separate full-output evidence from top5-only evidence
keep CPU output authority
```

Advance when:

```text
restored rows and digest match CPU authority for the claimed workload.
```

Stop if:

```text
row identity, order contract, digest, or restored semantics drift.
```

### Phase 3 - CPU Output-Side Reduction

Purpose:

```text
Reduce CPU materialization/convert/output work without changing complete rows.
```

Do:

```text
test only proof-first reducers
prove missing_rows = 0
prove extra_rows = 0
measure against the Phase 2 full-output baseline
keep row-safe-but-slower reducers default-off
```

Advance when:

```text
missing_rows = 0
extra_rows = 0
convert wall improves over Phase 2
```

Stop if:

```text
the reducer preserves only top5, changes complete rows, or is row-safe but slower.
```

### Phase 4 - Sort/Top-N Reduction

Purpose:

```text
Optimize sort/top-N only if profiling makes it a material bottleneck.
```

Do:

```text
measure sort/filter separately from materialization and write wall
preserve comparator behavior
preserve tie behavior
preserve selected rows and order
```

Advance when:

```text
sort/filter is dominant and the optimized path preserves exact rows/order.
```

Stop if:

```text
sort/filter is not dominant or the optimization changes tie behavior.
```

### Phase 5 - Archive Artifact

Purpose:

```text
Package minimal reference-backed data that can restore TFOsorted on demand.
```

Do:

```text
validate archive manifest
record reference digests
prove restored rows and digest match
keep archive evidence scoped unless it is paired with full-output gates
```

Advance when:

```text
archive_restore_rows_equal = 1
archive_restore_digest_match = 1
```

Stop if:

```text
restore needs hidden local files or changes the claimed full output.
```

### Phase 6 - Workload Matrix

Purpose:

```text
Keep every claim labelled as scoped, broad, blocked, fallback-heavy, or stopped.
```

Do:

```text
add rows only after matching gates pass
separate top5 artifact claims from full-output claims
separate fallback-heavy rows from GPU-fast-path-clean rows
```

Advance when:

```text
all claimed rows have passing scoped contracts
broad_replacement rows may be added only after Phase 7.5 or larger passes.
```

Stop if:

```text
a scoped/top5/archive milestone is labelled as broad replacement.
```

### Phase 7 - Broad GPU Path

Purpose:

```text
Pursue Path B only with a GPU execution path that can reduce pre-Align and
Align-side work while preserving the full output contract.
```

Do:

```text
start with first1
require full rows and digest equality before first64
require telemetry for scoreInfo/preAlign and Align-side work
keep CPU aligner.Align() as semantic authority
keep GPU endpoint/CIGAR/traceback/output/digest authority disabled
```

Phase 7 may advance only when:

```text
full_rows_equal = 1
digest_match = 1
missing_rows = 0
extra_rows = 0
candidate_wall_seconds < baseline_wall_seconds
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
```

Stop if:

```text
first1 changes rows or digest
first1 cannot prove skipped work before host-side output knowledge
first1 depends on the old v5 descriptor replay
first64 performance is slower than CPU authority
fallback accounting is incomplete
```

### Phase 8 - Closure Decision

Purpose:

```text
Make the only allowed decision to close or keep open the active goal.
```

Path A may close only when:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
Phase 0, Phase 1, Phase 5, and Phase 6 scoped gates are green
```

Path B may close only when:

```text
claimed_broad_replacement_rows > 0
Phase 7 first64 or larger broad gate passes
full output equality gates remain green
CPU authority boundaries remain green
```

Otherwise:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Only Phase 8 may justify marking the active goal complete.

## Phase 7 Breakdown

Phase 7.1 - New GPU Engine First1 Shadow or Path A Acceptance

```text
Goal:
  either record explicit Path A scoped acceptance, or add a fail-closed
  default-off first1 shadow scaffold for the new GPU engine.

Status:
  fail-closed scaffold present
  gate_first1_pass = 0
  next_valid_gate = implement_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance

Required new-engine data model:
  GpuScoreInfoTask
  GpuCandidateGroup
  GpuReplayAttempt
  skipped-work certificate

Default-off env:
  FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_FIRST1_SHADOW=1

Pass condition:
  requested telemetry appears
  active is fail-closed until the certificate producer exists
  CPU aligner.Align() authority remains 1
  GPU endpoint/CIGAR/traceback/output/digest authority remains 0

Stop condition:
  the implementation reuses the old v5 CPU-authority replay as a pass
  the implementation lacks certificate telemetry
```

Phase 7.2 - New Certificate CUDA API

```text
Goal:
  expose the CUDA-side API surface for a certificate source that can later
  prove skipped work is output-inert before D2H and before final CPU output
  membership is known.

Status:
  certificate producer first1 synthetic gate present
  certificate_producer_active = 1
  certificate_valid_before_d2h = 1
  certificate_cuda_api_gate_pass = 1
  runtime_reduction_enabled = 0
  next_valid_gate = first1_reducing_runtime_with_certificate_or_no_go
  historical_post_producer_cursor:
    current_gate = first1_reducing_runtime_with_certificate_or_no_go
    current_next_pr = fasim_new_gpu_engine_first1_reducing_runtime_or_no_go

Required telemetry:
  certificate_producer_active
  certificate_valid_before_d2h
  skipped_groups
  skipped_attempts
  conservative_fallback_groups
  certificate_false_negatives
  certificate_missing_required_attempts

Pass condition:
  certificate_valid_before_d2h = 1
  certificate_false_negatives = 0
  certificate_missing_required_attempts = 0
```

Phase 7.3 - First1 Reducing Runtime

```text
Goal:
  use the new certificate path to reduce work on first1 while preserving the
  full external output.

Status:
  no-go checkpoint recorded
  first1_runtime_reduction_gate_pass = 0
  first64_runtime_allowed = 0
  checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.md

Pass condition:
  full_rows_equal = 1
  digest_match = 1
  missing_rows = 0
  extra_rows = 0
  scoreInfo_prealign_reduced = 1
  align_side_reduced = 1
  fallback_accounting_clean = 1
	  candidate_wall_seconds < baseline_wall_seconds
```

Phase 7.3B - Real Runtime Certificate Source

```text
Goal:
  prove that a non-synthetic certificate candidate source exists in the real
  Fasim runtime path before any work is dropped.

Status:
  source-only checkpoint recorded
  real_source_certificate_source_gate_pass = 1
  real_fasim_runtime_certificate_source = 1
  real_fasim_runtime_work_drop_path = 0
  runtime_certificate_is_synthetic = 0
  source_is_pre_drop = 1
  gate_first1_source_pass = 1
  gate_first1_pass = 0
  runtime_reduction_enabled = 0
  checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md

Next valid gate:
  design_pre_drop_output_inert_work_drop_proof
  current_next_pr = fasim_new_gpu_engine_pre_drop_work_drop_proof_design
```

Phase 7.3C - Pre-Drop Work-Drop Proof Design

```text
Goal:
  define the proof contract that would let a future first1 shadow decide
  whether a skip is output-inert before the skip happens.

Status:
  design-only checkpoint recorded
  phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design = defined
  design_only = 1
  runtime_reduction_enabled = 0
  runtime_work_drop_enabled = 0
  checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md

Next valid gate:
  implement_pre_drop_output_inert_work_drop_proof_first1_shadow
  current_next_pr = fasim_new_gpu_engine_pre_drop_work_drop_proof_consumer_or_no_go
```

Phase 7.4 - First1 Proof Shadow

```text
Goal:
  observe the real runtime certificate source and print proof telemetry while
  keeping all work-drop behavior disabled.

Status:
  fail-closed shadow recorded
  checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow.md
  phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow = fail_closed_shadow
  real_fasim_runtime_certificate_source = 1
  uses_pre_drop_output_inert_proof = 0
  runtime_reduction_enabled = 0
  runtime_work_drop_enabled = 0
  real_fasim_runtime_work_drop_path = 0
  gate_first1_proof_pass = 0
  gate_first1_pass = 0

Next valid gate:
  implement_pre_drop_output_inert_work_drop_proof_consumer_or_no_go
  current_next_pr = fasim_new_gpu_engine_pre_drop_work_drop_proof_consumer_or_no_go
```

Phase 7.4b - Proof Consumer No-Go

```text
Goal:
  decide whether the current descriptor stream can support a complete-row-safe
  pre-drop proof consumer.

Status:
  no-go checkpoint recorded
  checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md
  phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_status =
    no_go_current_descriptor_stream
  accepted_pre_drop_output_inert_proof = 0
  runtime_reduction_enabled = 0
  runtime_work_drop_enabled = 0
  path_b_current_family_stopped = 1

Next valid gate:
  path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go
  current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go
```

Phase 7.4c - Different GPU Execution Design After Consumer No-Go

```text
Goal:
  define the only acceptable Path B design family after the current
  descriptor-stream proof consumer failed.

Status:
  docs-only design checkpoint recorded
  checkpoint =
    docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md
  phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go =
    defined
  phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go_status =
    design_defined
  path_b_new_design_family =
    fasim_compatible_gpu_scoreinfo_frontier_certificate_engine
  path_b_runtime_pr_allowed = 0
  path_b_docs_spec_allowed = 1
  path_b_current_descriptor_family_stopped = 1

Next valid gate:
  phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
  current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
```

Phase 7.4d - GPU ScoreInfo Certificate Engine Spec

```text
Goal:
  define the implementation-ready first1 spec for the Fasim-compatible GPU
  scoreInfo frontier certificate engine.

Status:
  docs-only spec checkpoint recorded
  checkpoint =
    docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.md
  phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance =
    defined
  phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_status =
    spec_defined
  path_b_scoreinfo_certificate_engine_spec_defined = 1
  path_b_first1_fail_closed_shadow_scaffold_allowed = 1
  path_b_runtime_reduction_pr_allowed = 0
  path_b_runtime_work_drop_allowed = 0
  path_b_first64_runtime_allowed = 0

Next valid gate:
  phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold
  current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold
```

Phase 7.4e - GPU ScoreInfo Certificate Engine First1 Shadow Scaffold

```text
Goal:
  observe the real runtime source under the post-consumer certificate-engine
  first1 shadow without dropping work.

Status:
  fail-closed runtime checkpoint recorded
  checkpoint =
    docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.md
  phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold =
    fail_closed_shadow
  phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold_status =
    fail_closed_no_runtime_reduction
  runtime_reduction_enabled = 0
  runtime_work_drop_enabled = 0
  gate_first1_shadow_pass = 0

Next valid gate:
  phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go
  current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go
```

Phase 7.4f - GPU ScoreInfo Certificate Engine Consumer No-Go

```text
Goal:
  close the post-consumer certificate-engine first1 shadow consumer gate when
  the shadow has no valid pre-drop certificate to consume.

Status:
  no-go checkpoint recorded
  checkpoint =
    docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md
  phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_status =
    no_go_no_valid_pre_drop_certificate
  accepted_scoreinfo_certificate_engine_consumer = 0
  accepted_pre_drop_output_inert_certificate = 0
  path_b_scoreinfo_certificate_engine_family_stopped = 1
  runtime_reduction_enabled = 0
  runtime_work_drop_enabled = 0

Next valid gate:
  path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go
  current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go
```

Phase 7.4g - Path A Scope Acceptance Or Different GPU Execution Design After ScoreInfo Cert Engine No-Go

```text
docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go.md
path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go = recorded
path_b_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go_status = design_defined
path_b_new_design_family = gpu_owned_fasim_scoreinfo_consumer_with_pre_drop_frontier_certificate
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
```

Phase 7.4h - GPU-Owned ScoreInfo Consumer Design Spec

```text
docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance.md
phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance = defined
phase7_gpu_owned_scoreinfo_consumer_design_spec_status = spec_defined
path_b_gpu_owned_scoreinfo_consumer_spec_defined = 1
path_b_gpu_owned_first1_fail_closed_shadow_allowed = 1
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
path_b_first64_runtime_allowed = 0
next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold
```

This checkpoint defines the GPU-owned scoreInfo state layout, GPU-owned attempt
frontier layout, pre-drop certificate field math, consumer decision point,
fallback accounting schema, first1 shadow inputs, and first1 shadow telemetry.
It is not runtime reduction.

Phase 7.4i - GPU-Owned ScoreInfo Consumer First1 Shadow Scaffold

```text
docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold.md
phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold = fail_closed_shadow
phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
path_b_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go
```

The next gate must either consume a valid pre-drop GPU-owned frontier
certificate or record no-go for this design family.

Phase 7.4j - GPU-Owned ScoreInfo Consumer First1 Shadow Consumer No-Go

```text
docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go.md
phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go = recorded
phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_status = no_go_no_valid_pre_drop_certificate
accepted_gpu_owned_scoreinfo_consumer = 0
accepted_pre_drop_frontier_certificate = 0
path_b_gpu_owned_scoreinfo_consumer_family_stopped = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go
```

The post-GPU-owned consumer fork checkpoint is now recorded:

```text
docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md
path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go = recorded
path_b_different_gpu_execution_design_after_gpu_owned_consumer_no_go_status = design_defined
path_b_new_design_family = gasal2_full_align_result_with_cpu_verifier_certificate
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance
current_next_pr = fasim_gasal2_full_align_verifier_design_spec_or_path_a_acceptance
```

The full-align verifier design/spec checkpoint is now defined:

```text
docs/fasim_gasal2_phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance.md
phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance = defined
phase7_full_align_verifier_design_spec_status = spec_defined
path_b_full_align_verifier_spec_defined = 1
path_b_full_align_verifier_first1_fail_closed_shadow_allowed = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
current_next_pr = fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
```

The next gate must implement only a first1 fail-closed shadow scaffold. It must
not continue the GPU-owned shadow as a reducing runtime.

Phase 7.5 - First64 Broad Gate

```text
Goal:
  prove the first1 result generalizes to first64 or a larger representative
  workload before any broad claim.

Pass condition:
  full_rows_equal = 1
  digest_match = 1
  candidate_wall_seconds < baseline_wall_seconds
  scoreInfo_prealign_reduced = 1
  align_side_reduced = 1
  fallback_accounting_clean = 1
```

Phase 7.6 - Scale Gate and Workload-Matrix Promotion

```text
Goal:
  add a broad_replacement row only after a representative broad workload
  passes equality, speed, and CPU-work-reduction gates.

Pass condition:
  claimed_broad_replacement_rows > 0
  row points to exact evidence docs and commands
  scoped rows remain scoped
```

## Immediate Next Actions

```text
1. Run:
     make check-fasim-gasal2-roadmap-goal-closure-phase-plan
     make check-fasim-gasal2-roadmap-phase-driver

2. If Path B continues:
     do not implement runtime from the current synthetic certificate producer
     line. The Phase 7.3 first1 reducing runtime no-go is recorded, and the
     real runtime certificate source-only checkpoint is:
       docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md
       docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md
       docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md
       docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md
       docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md
     The current proof consumer family is stopped as no-go. The next Path B artifact must be a different GPU execution design with a new proof source.
     Do not run first64 before first1 runtime reduction passes.

3. If the user accepts Path A:
     record explicit scoped acceptance, rerun scoped gates, then move to Phase 8.

4. Current execution gate:
     current_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go
     current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go
     current_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
     current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
     current_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold
     current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold
     current_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go
     current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go
     current_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go
     current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go
```

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
historical_execution_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
historical_next_pr = fasim_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold.md
phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold = fail_closed_shadow
phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
path_b_gpu_upper_bound_reject_certificate_first1_shadow_scaffold = 1
phase7_gpu_upper_bound_reject_certificate_gate_first1_shadow_pass = 1
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
