# Fasim GASAL2 Goal Completion Playbook

This document is the single-page execution playbook for making the active
GASAL2/Fasim goal completable. It is not a completion claim.

The active broad goal remains open:

```text
Use GASAL2/GPU to materially accelerate or replace the scoreInfo/preAlign /
Align-related Fasim path while preserving the required output contract.

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

## Completion Rule

There are only two valid ways to close the active goal.

```text
Path A - scoped product completion:
  Valid only if the user explicitly accepts the narrowed deliverable:
    short-query/H19 top5 GASAL2 artifact
    MEG3-like complete-record grouping where claimed
    archive-first restored output where claimed

  This path does not claim:
    aligner.Align() replacement
    universal scoreInfo/preAlign replacement
    long-query NEAT1/MALAT1 broad replacement
    GPU endpoint/CIGAR/traceback/output/digest authority

Path B - original broad completion:
  Required while the user still wants the original objective.

  This path must prove:
    full row-set equality
    digest equality
    runtime win over CPU authority
    scoreInfo/preAlign work reduction or replacement
    Align-side work reduction or replacement
    fallback accounting clean
```

Do not mix the paths. A short-query top5 milestone, grouping milestone, archive
milestone, or output-drift speedup can be useful and mergeable without closing
the broad objective.

## Current Cursor

The current cursor is Path B:

```text
current_path = Path B unless Path A is explicitly accepted
current_phase = Phase 7
current_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
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

Why this is the cursor:

```text
Phase 0 reproducibility is required before any final claim
Path A scoped product exists but has not been accepted as goal closure
full-output/archive work is useful but does not replace broad Path B
current broad descriptor-stream and score bridge families are stopped
real runtime certificate source exists for first1
pre-drop output-inert work-drop proof is designed
Phase 7.4 first1 proof shadow is recorded as fail-closed
Phase 7.4b proof consumer is recorded as no-go for the current descriptor stream
Phase 7.4c different GPU execution design is recorded as docs-only
Phase 7.4d GPU scoreInfo certificate engine spec is recorded as docs-only
Phase 7.4h GPU-owned scoreInfo consumer design spec is recorded as docs-only
GPU-owned scoreInfo, GASAL2 full-align verifier, and native CUDA/Fasim DP
families are now stopped
GPU upper-bound reject certificate design spec is recorded as docs-only
the next missing step is a first1 fail-closed upper-bound reject shadow or explicit Path A scope acceptance
```

The current checkpoint chain is:

```text
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scaffold.md
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow.md
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md
docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md
docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.md
docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.md
docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md
docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go.md
docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance.md
```

## Non-Negotiable Invariants

These remain true until a separate equivalence proof explicitly changes them:

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
default behavior unchanged = 1
```

Forbidden shortcuts:

```text
top5-only evidence closes broad objective = 0
archive-only evidence closes broad objective = 0
grouping-only evidence closes broad objective = 0
output-drift speedup counts as success = 0
fallback-heavy evidence counts as GPU-fast-path clean = 0
final CPU output membership can be used as runtime skip proof = 0
synthetic certificate producer can be relabelled as real runtime proof = 0
first64 may run before first1 broad gate passes = 0
```

## Phase Plan

### Phase 0 - Reproducibility

Do:

```text
pin GASAL2 upstream commit
track local GASAL2 patches
make setup/build targets idempotent
record CUDA version, SM arch, GASAL2_MAX_QUERY_LEN, and GASAL2_N_CODE
remove reliance on untracked .tmp/GASAL2 edits or local-only binaries
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
clean_checkout_rebuilds_gasal2_bridge = 1
```

Stop if:

```text
any claimed result depends on machine-local GASAL2 state
```

### Phase 1 - Scope Decision

Do:

```text
present scoped claims and non-claims together
record explicit user acceptance before using Path A
keep scoped acceleration default-off unless separately accepted
```

Path A can proceed to Phase 8 only when:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

Stop Path A if:

```text
the user still wants the original broad scoreInfo/preAlign/Align objective
```

### Phase 2 - Full-Output Baseline

Do:

```text
preserve restored TFOsorted/full-row equality
preserve digest equality
itemize convert/output wall time
itemize whole-run wall time
separate full-output evidence from top5-only evidence
keep CPU output authority
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase2-equivalence-first-convert
make check-fasim-gasal2-archive-first-output
make check-fasim-gasal2-convert-cpu-breakdown
```

Advance when:

```text
restored_rows_equal = 1
restored_digest_match = 1
convert_and_run_timing_itemized = 1
```

Stop if:

```text
row identity, ordering contract, digest, or restored semantics drift
```

### Phase 3 - CPU Output-Side Reduction

Do:

```text
test only proof-first reducers
prove missing_rows = 0 before speed claims
prove extra_rows = 0 before speed claims
compare against the Phase 2 full-output baseline
keep row-safe-but-slower reducers default-off
```

Advance only when:

```text
missing_rows = 0
extra_rows = 0
complete_row_set_preserved = 1
convert_wall_seconds < phase2_convert_wall_seconds
```

Stop if:

```text
the reducer preserves only top5
the reducer changes complete rows
the reducer requires final CPU output membership as proof
the reducer is row-safe but slower
```

### Phase 4 - Sort/Top-N Reduction

Do:

```text
measure sort/filter separately from materialization and write wall
optimize only if sort/filter is a material bottleneck
preserve comparator behavior
preserve tie behavior
preserve selected rows and order
```

Advance only when:

```text
sort_or_filter_is_dominant = 1
same_rows_and_order = 1
sort_filter_wall_improves = 1
```

Stop if:

```text
sort/filter is not dominant
tie behavior changes
selected row order changes
```

### Phase 5 - Archive Artifact

Do:

```text
record archive schema version
record reference digests
validate manifest integrity
validate restored row equality
validate restored digest equality
keep archive delivery separate from broad runtime replacement
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase5-archive-artifact
make check-fasim-gasal2-archive-manifest-parser
make check-fasim-tfo-archive-integrity-parser
```

Advance when:

```text
archive_manifest_valid = 1
archive_restore_rows_equal = 1
archive_restore_digest_match = 1
```

Stop if:

```text
restore depends on hidden local files
restore changes row identity
archive evidence is used as broad runtime replacement by itself
```

### Phase 6 - Workload Matrix

Do:

```text
label every workload as scoped_claim, unclaimed, blocked, fallback_heavy, or broad_replacement
ensure scoped_claim rows have passing scoped contracts
ensure broad_replacement rows exist only after Phase 7 broad gates pass
keep fallback-heavy rows out of GPU-fast-path claims
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase6-workload-matrix
make check-fasim-gasal2-workload-matrix-parser
```

Path B may proceed to Phase 8 only when at least one broad_replacement row has:

```text
full_rows_equal = 1
digest_match = 1
speedup > 1.0
fallback_accounting_clean = 1
scoreinfo_prealign_reduced = 1
align_side_reduced = 1
```

Stop if:

```text
top5-only, archive-only, fallback-heavy, or output-drift evidence is labelled broad_replacement
```

### Phase 7 - Broad GPU Path

Purpose:

```text
Complete the original broad objective if a valid architecture exists.
```

#### Phase 7.1 - Real-Source First1 Shadow

Status:

```text
checkpoint_recorded = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
```

Required behavior:

```text
requested = 1 when env is set
fallback_to_full_cpu_replay = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_first1_pass = 0
```

#### Phase 7.2 - Real Runtime Certificate Source

Status:

```text
checkpoint_recorded = 1
real_fasim_runtime_certificate_source = 1
runtime_certificate_is_synthetic = 0
source_task_count > 0
source_scoreinfo_count > 0
source_attempt_count > 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
gate_first1_source_pass = 1
gate_first1_pass = 0
```

#### Phase 7.3 - Pre-Drop Output-Inert Proof Design

Status:

```text
checkpoint_recorded = 1
design_only = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
next_valid_gate = implement_pre_drop_output_inert_work_drop_proof_first1_shadow
```

#### Phase 7.4 - First1 Proof Shadow

Status:

```text
checkpoint_recorded = 1
real_fasim_runtime_certificate_source = 1
uses_pre_drop_output_inert_proof = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
real_fasim_runtime_work_drop_path = 0
fallback_to_full_cpu_replay = 1
gate_first1_proof_pass = 0
gate_first1_pass = 0
next_valid_gate = implement_pre_drop_output_inert_work_drop_proof_consumer_or_no_go
```

What this phase proved:

```text
the real source can be observed from the fail-closed shadow path
the current path still has no accepted pre-drop output-inert proof
no scoreInfo/preAlign work was dropped
no Align-side work was dropped
CPU output remains the replay authority
```

#### Phase 7.4b - Proof Consumer No-Go

Status:

```text
checkpoint_recorded = 1
phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_status = no_go_current_descriptor_stream
accepted_pre_drop_output_inert_proof = 0
uses_pre_drop_output_inert_proof = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
real_fasim_runtime_work_drop_path = 0
path_b_current_family_stopped = 1
next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go
```

What this phase proved:

```text
the current descriptor stream can support replay but not skipped-work proof
final CPU output membership remains forbidden as runtime proof
no complete-row-safe pre-drop output-inert proof exists in this family
first1 reducing runtime and first64 remain forbidden from this family
```

#### Phase 7.4c - Different GPU Execution Design After Consumer No-Go

This docs-only design checkpoint is now recorded:

```text
checkpoint =
  docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md
phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go = defined
phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go_status = design_defined
path_b_new_design_family = fasim_compatible_gpu_scoreinfo_frontier_certificate_engine
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
```

The next action must be one of:

```text
Path A:
  record explicit scoped completion acceptance from the user

Path B:
  write an implementation-ready first1 spec for the Fasim-compatible GPU
  scoreInfo frontier certificate engine before any new runtime code
```

#### Phase 7.4d - GPU ScoreInfo Certificate Engine Spec

This docs-only spec checkpoint is now recorded:

```text
checkpoint =
  docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.md
phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance = defined
phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_status = spec_defined
path_b_scoreinfo_certificate_engine_spec_defined = 1
path_b_first1_fail_closed_shadow_scaffold_allowed = 1
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
path_b_first64_runtime_allowed = 0
next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold
current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold
```

The next Path B work may be only a first1 fail-closed shadow scaffold. It must
not reduce runtime work yet, must not run first64, and must not give GPU
endpoint, CIGAR, traceback, output, or digest authority.

#### Phase 7.4e - GPU ScoreInfo Certificate Engine First1 Shadow Scaffold

This fail-closed runtime checkpoint is now recorded:

```text
checkpoint =
  docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.md
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold =
  fail_closed_shadow
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold_status =
  fail_closed_no_runtime_reduction
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
fallback_to_full_cpu_replay = 1
gate_first1_shadow_pass = 0
gate_first1_pass = 0
next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go
current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go
```

The next Path B work must either prove a real first1 certificate consumer
before dropping work or record no-go for this design family.

#### Phase 7.4f - GPU ScoreInfo Certificate Engine Consumer No-Go

This consumer no-go checkpoint is now recorded:

```text
checkpoint =
  docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go =
  recorded
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_status =
  no_go_no_valid_pre_drop_certificate
accepted_scoreinfo_certificate_engine_consumer = 0
accepted_pre_drop_output_inert_certificate = 0
path_b_scoreinfo_certificate_engine_family_stopped = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go
```

The next work must either record explicit Path A scoped acceptance or define a
genuinely different Path B design.

The scoreInfo certificate-engine fork checkpoint is now recorded and advances
the next Path B step to a docs-only GPU-owned scoreInfo consumer design spec:

```text
docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go.md
path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go = recorded
path_b_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go_status = design_defined
path_b_new_design_family = gpu_owned_fasim_scoreinfo_consumer_with_pre_drop_frontier_certificate
next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
```

The GPU-owned scoreInfo consumer design spec is now recorded and advances the
next Path B step to a first1 fail-closed shadow scaffold:

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

The GPU-owned scoreInfo consumer first1 shadow scaffold is now recorded:

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

The GPU-owned scoreInfo consumer first1 shadow consumer gate is now recorded
as no-go:

```text
docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go.md
phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go = recorded
phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_status =
  no_go_no_valid_pre_drop_certificate
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

The full-align verifier first1 fail-closed shadow scaffold is now recorded:

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

It defines:

```text
gpu_owned_scoreinfo_state_layout
gpu_owned_attempt_frontier_layout
pre_drop_certificate_field_math
consumer_decision_point_before_cpu_replay_selection
fallback_accounting_schema
first1_shadow_inputs
first1_shadow_expected_telemetry
```

Stop if:

```text
the proof needs final CPU output membership
the proof is only top5-safe
the proof changes the complete row set
the proof cannot identify skippable work before the skip point
the only honest result is no-go for this proof family
```

#### Phase 7.5 - First1 Reducing Runtime

Do only after Phase 7.4b passes:

```text
drop only work covered by the accepted pre-drop proof
fallback to full CPU authority for uncovered work
compare full external rows and digest to CPU authority
measure against the CPU-authority first1 baseline
```

Pass only when:

```text
full_rows_equal = 1
digest_match = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
CPU aligner.Align() authority = 1
GPU endpoint/CIGAR/traceback/output/digest authority = 0
gate_first1_pass = 1
```

Stop if:

```text
rows or digest differ
runtime is slower
only scoreInfo/preAlign work is reduced
only Align-side work is reduced
fallback accounting is not clean
```

#### Phase 7.6 - First64 Broad Characterization

Do only after Phase 7.5 passes:

```text
run first64 with the same accepted proof
keep CPU authority validation
measure wall time and work reduction
record fallback accounting
```

Pass only when:

```text
full_rows_equal = 1
digest_match = 1
candidate_vs_baseline > 1.0
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
```

Stop if:

```text
first64 is attempted before first1 passes
first64 preserves correctness but loses performance
first64 depends on output-drift acceptance
```

#### Phase 7.7 - Workload-Matrix Promotion

Do:

```text
promote only rows that pass Phase 7.5 or Phase 7.6 gates
record scoped rows separately from broad rows
keep stopped/no-go rows labelled stopped or blocked
```

Advance when:

```text
claimed_broad_replacement_rows > 0
every broad row has equality, digest, speedup, reduced work, and clean fallback accounting
```

### Phase 8 - Completion Decision

Close Path A only when:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
scoped claims are explicitly labelled non-broad
```

Close Path B only when:

```text
Phase 0 reproducibility passes
Phase 2 full-output baseline is clean
Phase 6 workload matrix has at least one valid broad_replacement row
Phase 7 broad gate passes on that row
CPU authority validation remains enabled
GPU endpoint/CIGAR/traceback/output/digest authority remains 0
```

Do not close when:

```text
only top5 is clean
only archive restore is clean
only grouping is fast
only output-drift TFO overlap is high
the broad path is correctness-clean but slower
the broad path is faster but rows or digest differ
```

## Immediate Next PR

The next PR should be:

```text
fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go
```

It must not add runtime work drop:

```text
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
fallback_to_full_cpu_replay = 1
gate_first1_proof_pass = 0
gate_first1_pass = 0
```

It should either record explicit Path A scoped acceptance or define a new Path
B design that is not a continuation of the stopped descriptor-stream proof
consumer family.

## Current Decision

```text
goal_completion_playbook = defined
current_path = Path B unless Path A is explicitly accepted
current_phase = Phase 7
current_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
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
