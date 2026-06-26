# Fasim GASAL2 Phase-To-Completion Plan

This document is the direct phase plan for making the active Fasim/GASAL2
goal completable. It is not a completion claim.

The active broad goal remains open:

```text
Use GASAL2/GPU to materially accelerate or replace the scoreInfo/preAlign /
Align-related Fasim path while preserving the required output contract.

broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The plan has two valid close paths. They must not be mixed.

```text
Path A: scoped product completion
  Valid only if the user explicitly accepts the narrowed deliverable:
    short-query/H19 top5 GASAL2 artifact
    MEG3-like complete-record grouping where claimed
    archive-first restored output where claimed

  This does not claim:
    aligner.Align() replacement
    universal scoreInfo/preAlign replacement
    long-query NEAT1/MALAT1 broad replacement
    GPU endpoint/CIGAR/traceback/output/digest authority

Path B: broad objective completion
  Required while the original broad goal remains active.

  Must prove:
    full row-set/digest equality
    runtime win over CPU authority
    scoreInfo/preAlign work reduced or replaced
    Align-side work reduced or replaced
    fallback accounting clean
```

## Current Cursor

The current cursor is:

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
current v3/v4/v5 and post-v5.3 descriptor-stream broad paths are stopped
synthetic certificate producer is not a real runtime reduction proof
Phase 7.1 fail-closed real-source scaffold is recorded
Phase 7.2 real runtime certificate source is recorded as source-only
Phase 7.3 pre-drop output-inert work-drop proof design is recorded
Phase 7.4 pre-drop proof first1 shadow is recorded as fail-closed
Phase 7.4b proof consumer is recorded as no-go for the current descriptor stream
Phase 7.4c different GPU execution design is recorded as docs-only
Phase 7.4d GPU scoreInfo certificate engine spec is recorded as docs-only
Phase 7.4h GPU-owned scoreInfo consumer design spec is recorded as docs-only
GPU-owned scoreInfo, GASAL2 full-align verifier, and native CUDA/Fasim DP
families are now stopped
GPU upper-bound reject certificate design spec is recorded as docs-only
next Path B work must be a first1 fail-closed upper-bound reject shadow or Path A scope acceptance
```

Relevant checkpoint:

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

## Global Invariants

These invariants apply to every phase until a separate equivalence proof
explicitly changes the contract:

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
output-drift speedup counts as success = 0
fallback-heavy evidence counts as GPU-fast-path clean = 0
stopped v3/v4/v5 paths can be promoted as-is = 0
synthetic certificate producer can be relabelled as real runtime proof = 0
first64 may run before first1 broad gate passes = 0
```

## Phase Summary

| Phase | Job | Exit Gate | Completion Role |
| --- | --- | --- | --- |
| 0 | Reproducibility | Clean checkout rebuilds patched GASAL2/Fasim bridge | Required for both paths |
| 1 | Scope decision | User explicitly accepts Path A if used | Required for Path A |
| 2 | Full-output baseline | Restored rows/digest match CPU authority | Required foundation |
| 3 | CPU output-side reduction | Complete row set preserved and CPU wall improves | Optional helper |
| 4 | Sort/top-N reduction | Sort/filter dominant and exact behavior preserved | Optional helper |
| 5 | Archive artifact | Archive restores claimed output exactly | Required for Path A archive claim |
| 6 | Workload matrix | Claims are labelled correctly | Required claim ledger |
| 7 | Broad GPU path | Equality, speedup, and CPU-work reduction pass | Required for Path B |
| 8 | Close decision | Path A accepted or Path B proven | Only close phase |

## Phase 0 - Reproducibility

Purpose:

```text
Make every claimed GASAL2/Fasim result rebuildable from a clean checkout.
```

Do:

```text
pin GASAL2 upstream commit
track local GASAL2 patches
keep setup/build targets idempotent
record CUDA version, SM arch, GASAL2_MAX_QUERY_LEN, and GASAL2_N_CODE
remove reliance on untracked .tmp/GASAL2 source or local-only binaries
```

Exit gate:

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

## Phase 1 - Scope Decision

Purpose:

```text
Decide whether the narrowed scoped product is allowed to close the active goal.
```

Do:

```text
present scoped claims and non-claims together
record explicit user acceptance before using Path A
keep scoped features default-off unless separately accepted
```

Path A may advance to Phase 8 only when:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

Stop Path A if:

```text
the user still wants the original broad scoreInfo/preAlign/Align objective
```

If Path A is not explicitly accepted, continue Path B through Phase 7.

## Phase 2 - Full-Output Baseline

Purpose:

```text
Keep restored TFOsorted/full output correct before any full-output speed claim.
```

Do:

```text
preserve restored row-set equality
preserve digest equality
itemize convert/output wall time
itemize whole-run wall time
separate full-output evidence from top5-only evidence
keep CPU output authority
```

Exit gate:

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

## Phase 3 - CPU Output-Side Reduction

Purpose:

```text
Reduce CPU materialization/convert/output work without changing complete rows.
```

Do:

```text
test only proof-first reducers
prove missing_rows = 0 before speed claims
prove extra_rows = 0 before speed claims
compare against the Phase 2 full-output baseline
keep row-safe-but-slower reducers default-off
```

Exit gate:

```text
missing_rows = 0
extra_rows = 0
task_frontier_safety = safe, when pruning is task-local
real_prune_proof_gate = pass
convert_wall_seconds < Phase_2_convert_wall_seconds
```

Stop if:

```text
the reducer preserves only top5
the reducer changes complete rows
the reducer requires final CPU output membership as proof
the reducer is row-safe but slower
```

Current status:

```text
current CIGAR NT prefilter line is full-clean but performance no-go
do not promote it as a runtime recommendation
```

## Phase 4 - Sort/Top-N Reduction

Purpose:

```text
Optimize sort/top-N only if profiling shows it is a material bottleneck.
```

Do:

```text
measure sort/filter separately from materialization and write wall
preserve comparator behavior
preserve tie behavior
preserve unique behavior
preserve top-N boundary behavior
```

Advance only when:

```text
sort_or_filter_is_dominant = 1
same rows and order are preserved
sort/filter wall improves
```

Stop if:

```text
sort/filter is not dominant
tie behavior changes
selected row order changes
```

## Phase 5 - Archive Artifact

Purpose:

```text
Store the minimal reference-backed artifact and restore TFOsorted on demand.
```

Do:

```text
record archive schema version
record reference digests
validate manifest integrity
validate restored row equality
validate restored digest equality
keep archive delivery separate from broad runtime replacement
```

Exit gate:

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

## Phase 6 - Workload Matrix

Purpose:

```text
Make every claim explicit and prevent scoped evidence from closing the broad goal.
```

Do:

```text
label every row as claimed, unclaimed, blocked, fallback-heavy, or broad_replacement
ensure claimed rows have passing scoped contracts
ensure broad_replacement rows exist only after Phase 7 broad gates pass
keep fallback-heavy rows out of GPU-fast-path claims
```

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase6-workload-matrix
make check-fasim-gasal2-workload-matrix-parser
```

Path A may proceed when:

```text
all scoped claimed rows pass
unclaimed and blocked rows remain explicit
```

Path B may proceed when:

```text
at least one broad_replacement row passes with:
  row_equal = true
  digest_match = true
  speedup > 1.0
  fallback_accounting_clean = true
  scoreinfo_reduced = true
  align_side_reduced = true
```

Stop if:

```text
top5-only, archive-only, fallback-heavy, or output-drift evidence is labelled broad_replacement
```

## Phase 7 - Broad GPU Path

Purpose:

```text
Complete the original broad objective if a valid architecture exists.
```

Current Path B state:

```text
current descriptor-stream lines are stopped
current certificate producer line is synthetic or no-go
real_source_first1_spec_defined = 1
real_fasim_runtime_certificate_source = recorded
pre_drop_work_drop_proof_consumer = no_go_current_descriptor_stream
scoreinfo_certificate_engine_consumer = no_go_no_valid_pre_drop_certificate
gpu_owned_scoreinfo_consumer_design_spec_defined = 1
phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold = fail_closed_shadow
current_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go
real_fasim_runtime_work_drop_path = 0
runtime_reduction_enabled = 0
first64_runtime_allowed = 0
```

### Phase 7.1 - Real-Source First1 Shadow Or Path A Acceptance

This historical gate is recorded. It remains here as evidence for why the
current cursor moved forward.

Next PR:

```text
fasim_new_gpu_engine_real_source_first1_shadow_or_path_a_acceptance
```

Do one of:

```text
Path A:
  record explicit scoped completion acceptance, then go to Phase 8 Path A

Path B:
  add only a fail-closed first1 shadow scaffold for the real-source contract
  keep it default-off
  do not drop runtime work
  do not run first64
```

The fail-closed Path B scaffold must report:

```text
requested = 1, when the env is set
active = 0, until a real source exists
real_fasim_runtime_certificate_source = 0
real_fasim_runtime_work_drop_path = 0
runtime_certificate_is_synthetic = 0
missing_certificate = 1
fallback_to_full_cpu_replay = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_first1_pass = 0
```

Advance when:

```text
the scaffold is present and fail-closed
default output is unchanged
runtime reduction remains disabled
current_next_gate = implement_real_source_certificate_source_or_path_a_acceptance
```

Current checkpoint:

```text
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scaffold.md
real_source_first1_shadow_gate_pass = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
next_valid_gate_at_that_checkpoint = implement_real_source_certificate_source_or_path_a_acceptance
current_next_pr_at_that_checkpoint = fasim_new_gpu_engine_real_source_certificate_source_or_path_a_acceptance
```

Stop if:

```text
the scaffold uses the old v5 CPU-authority replay as a real source
the scaffold uses synthetic certificates as runtime proof
the scaffold changes output
the scaffold enables work drop
```

### Phase 7.2 - Real Runtime Certificate Source

Do:

```text
produce certificate candidates from the real Fasim runtime path
produce them before any work is dropped
keep CPU aligner.Align() as authority
do not use GPU endpoint/CIGAR/traceback/output/digest as authority
keep runtime reduction disabled
```

Required telemetry:

```text
real_fasim_runtime_certificate_source = 1
runtime_certificate_is_synthetic = 0
source_task_count > 0
source_scoreinfo_count > 0
source_attempt_count > 0
missing_certificate = 0 for covered first1 work
fallback_to_full_cpu_replay = 1
runtime_reduction_enabled = 0
gate_first1_source_pass = 1
```

Advance when:

```text
the source is real, non-empty, pre-drop, and not synthetic
the shadow comparison is clean for first1
```

Current checkpoint:

```text
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md
real_source_certificate_source_gate_pass = 1
real_fasim_runtime_certificate_source = 1
runtime_certificate_is_synthetic = 0
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
```

Stop if:

```text
the only source is final CPU output membership
the source appears only after CPU Align() has already done the work
the source cannot distinguish skipped-safe from required work
```

### Phase 7.3 - Work-Drop Proof Design

Do:

```text
define the proof that makes a skip output-inert before the skip happens
prove it without final CPU output membership
separate certificate production from certificate consumption
keep the consumer disabled until the proof passes
```

Advance when:

```text
uses_pre_drop_output_inert_proof = 1
candidate_proof_false_negatives = 0
candidate_proof_missing_required_attempts = 0
candidate_uses_final_cpu_output_as_runtime_proof = 0
gate_first1_proof_pass = 1
```

Current checkpoint:

```text
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md
phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design = defined
design_only = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
next_valid_gate = implement_pre_drop_output_inert_work_drop_proof_first1_shadow
current_next_pr = fasim_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow
```

Stop if:

```text
the proof needs final CPU output membership
the proof is only top5-safe
the proof changes the complete row set
the proof is too broad and cannot reduce work
```

### Phase 7.4 - First1 Proof Shadow

Do:

```text
observe the real runtime certificate source
print pre-drop proof telemetry
keep uses_pre_drop_output_inert_proof = 0 until a proof is accepted
keep runtime reduction disabled
keep runtime work drop disabled
fallback to full CPU replay
```

Current checkpoint:

```text
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow.md
phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow = fail_closed_shadow
real_fasim_runtime_certificate_source = 1
uses_pre_drop_output_inert_proof = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
real_fasim_runtime_work_drop_path = 0
candidate_uses_final_cpu_output_as_runtime_proof = 0
proof_must_not_use_top5_only_contract = 1
proof_must_cover_complete_row_set = 1
fallback_to_full_cpu_replay = 1
gate_first1_proof_pass = 0
gate_first1_pass = 0
next_valid_gate = implement_pre_drop_output_inert_work_drop_proof_consumer_or_no_go
current_next_pr = fasim_new_gpu_engine_pre_drop_work_drop_proof_consumer_or_no_go
```

Stop if:

```text
the next consumer still cannot produce a pre-drop output-inert proof
the consumer needs final CPU output membership
the consumer is only top5-safe
the consumer changes the complete row set
```

### Phase 7.4b - Proof Consumer No-Go

Current checkpoint:

```text
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md
phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go = recorded
phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_status = no_go_current_descriptor_stream
accepted_pre_drop_output_inert_proof = 0
uses_pre_drop_output_inert_proof = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
real_fasim_runtime_work_drop_path = 0
path_b_current_family_stopped = 1
gate_first1_proof_pass = 0
gate_first1_pass = 0
next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go
```

Stop this family because:

```text
current_descriptor_stream_can_prove_output_inert_skips = 0
complete_row_set_output_inert_certificate = missing
final CPU output membership remains forbidden as runtime proof
```

### Phase 7.4c - Different GPU Execution Design After Consumer No-Go

Current checkpoint:

```text
docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md
phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go = defined
phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go_status = design_defined
path_b_new_design_family = fasim_compatible_gpu_scoreinfo_frontier_certificate_engine
not_current_descriptor_stream_continuation = 1
not_gasal2_align_replacement = 1
not_final_cpu_output_membership_proof = 1
not_top5_only_contract = 1
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
```

The next Path B PR must be an implementation-ready first1 spec for the
Fasim-compatible GPU scoreInfo frontier certificate engine. It must define the
certificate fields, GPU/CPU replay interface, telemetry, and fail-closed
first1 checker before any runtime work-drop code.

### Phase 7.4d - GPU ScoreInfo Certificate Engine Spec

Current checkpoint:

```text
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

The next Path B PR may implement only a first1 fail-closed shadow scaffold. It
must not drop CPU work, must not run first64, and must keep CPU Align() as the
authority for score, endpoint, CIGAR, traceback, output, and digest.

### Phase 7.4e - GPU ScoreInfo Certificate Engine First1 Shadow Scaffold

Current checkpoint:

```text
docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.md
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold = fail_closed_shadow
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
path_b_scoreinfo_certificate_engine_first1_shadow_scaffold = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
fallback_to_full_cpu_replay = 1
gate_first1_shadow_pass = 0
gate_first1_pass = 0
next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go
current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go
```

The next Path B PR must either consume a first1 certificate before work is
dropped and prove full row/digest equality, or record no-go for this design
family. It must not run first64 until the first1 reducing-runtime gate passes.

### Phase 7.4f - GPU ScoreInfo Certificate Engine Consumer No-Go

Current checkpoint:

```text
docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go = recorded
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_status = no_go_no_valid_pre_drop_certificate
accepted_scoreinfo_certificate_engine_consumer = 0
accepted_pre_drop_output_inert_certificate = 0
consumer_can_drop_scoreinfo_work = 0
consumer_can_drop_align_work = 0
path_b_scoreinfo_certificate_engine_family_stopped = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go
```

The next checkpoint must either record explicit Path A scoped acceptance or
define a genuinely different Path B design. It must not continue this
fail-closed certificate-engine shadow as a reducing runtime.

### Phase 7.4g - ScoreInfo Certificate-Engine Fork

Current checkpoint:

```text
docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go.md
path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go = recorded
path_b_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go_status = design_defined
path_b_new_design_family = gpu_owned_fasim_scoreinfo_consumer_with_pre_drop_frontier_certificate
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
```

The next Path B artifact must be a docs-only spec for a GPU-owned Fasim
scoreInfo consumer with a pre-drop frontier certificate. It must not continue
the stopped scoreInfo certificate-engine shadow, and it must not add runtime
work drop until a first1 proof passes.

### Phase 7.4h - GPU-Owned ScoreInfo Consumer Design Spec

Current checkpoint:

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

The next Path B artifact may be a first1 fail-closed shadow scaffold for this
GPU-owned consumer. It must define no real output path and must not skip
scoreInfo or CPU Align() work.

Required spec elements now recorded:

```text
gpu_owned_scoreinfo_state_layout
gpu_owned_attempt_frontier_layout
pre_drop_certificate_field_math
consumer_decision_point_before_cpu_replay_selection
fallback_accounting_schema
first1_shadow_inputs
first1_shadow_expected_telemetry
```

### Phase 7.4i - GPU-Owned ScoreInfo Consumer First1 Shadow Scaffold

This fail-closed checkpoint is now recorded. It remains here as evidence for
why the current cursor moved to the consumer/no-go gate.

Next PR:

```text
fasim_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go
```

Current checkpoint:

```text
docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold.md
phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold = fail_closed_shadow
phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
path_b_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold = 1
```

### Phase 7.4j - GPU-Owned ScoreInfo Consumer First1 Shadow Consumer No-Go

This no-go checkpoint is now recorded:

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

The next checkpoint must implement only a first1 fail-closed shadow scaffold.
It must not continue this fail-closed GPU-owned shadow as a reducing runtime.

Do:

```text
add only a default-off first1 shadow scaffold for the GPU-owned consumer
observe GPU-owned scoreInfo state and attempt frontier telemetry
fallback to full CPU replay for every covered and uncovered task
keep runtime reduction disabled
keep runtime work drop disabled
keep first64 disabled
keep CPU aligner.Align() as authority
keep GPU endpoint/CIGAR/traceback/output/digest authority disabled
```

Required fail-closed telemetry:

```text
gpu_owned_scoreinfo_consumer_requested = 1
gpu_owned_scoreinfo_consumer_active = 1
gpu_owned_scoreinfo_states > 0
gpu_owned_attempt_frontier_attempts > 0
gpu_owned_replay_frontier_attempts > 0
gpu_owned_skipped_scoreinfo_groups = 0
gpu_owned_skipped_attempts = 0
cpu_replay_attempts = baseline_cpu_attempts
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
certificate_produced_before_work_drop = 0
certificate_consumed_before_cpu_replay_selection = 0
fallback_to_full_cpu_replay = 1
scoreInfo_prealign_reduced = 0
align_side_reduced = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_first1_shadow_pass = 0
gate_first1_pass = 0
```

Advance when:

```text
the scaffold is observable under its env gate
default output bytes and digest are unchanged
fallback accounting is explicit
no CPU work is skipped
no GPU result is authoritative
next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go
```

Stop if:

```text
the scaffold changes output
the scaffold drops scoreInfo or Align-side work
the scaffold uses final CPU output membership as proof
the scaffold promotes top5-only evidence into broad completion
the scaffold enables first64 before first1 reduction passes
```

### Phase 7.5 - First1 Reducing Runtime

Do:

```text
drop only work covered by the accepted real-source proof
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
candidate wall does not beat baseline
only one of scoreInfo/preAlign or Align-side work is reduced
fallback accounting is dirty
```

### Phase 7.6 - First64 Broad Characterization

Run only after the first1 reducing runtime passes.

Do:

```text
scale the same first1 mechanism to first64 or a comparable broad sample
do not change authority model
do not introduce a new proof family without returning to Phase 7.3
```

Pass only when:

```text
full_rows_equal = 1
digest_match = 1
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
```

Stop if:

```text
first1 did not pass
first64 changes output
first64 is slower than CPU authority
work reduction disappears at scale
```

### Phase 7.7 - Workload-Matrix Promotion

Do:

```text
add broad_replacement rows only after Phase 7.6 passes
record workload, baseline wall, candidate wall, equality, fallback, and authority counters
keep scoped rows separate from broad rows
```

Advance when:

```text
claimed_broad_replacement_rows > 0
all broad rows have equality, speedup, fallback-clean, and work-reduction evidence
```

Stop if:

```text
the only passing rows are scoped top5/archive/grouping rows
```

## Phase 8 - Completion Decision

Only Phase 8 may close the active goal.

Path A may close only when:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
Phase 0 is green
Phase 5 is green where archive output is claimed
Phase 6 labels all claims correctly
non-claims are recorded next to scoped claims
```

Path B may close only when:

```text
Phase 0 is green
Phase 2 full-output baseline is green
Phase 6 has at least one passing broad_replacement row
Phase 7.6 or larger broad gate passes
full row-set/digest equality = 1
runtime win over CPU authority = 1
scoreInfo/preAlign work reduced or replaced = 1
Align-side work reduced or replaced = 1
fallback accounting clean = 1
CPU aligner.Align() authority = 1
GPU endpoint/CIGAR/traceback/output/digest authority = 0
```

Otherwise keep:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Immediate Execution Order

Use this sequence from the current cursor:

```text
1. Either record explicit Path A scoped acceptance, or implement Phase 7.4j:
   GPU-owned scoreInfo consumer first1 shadow consumer/no-go.

2. If Phase 7.4j has no valid pre-drop consumer:
   either a valid pre-drop consumer exists, or the GPU-owned family stops.

3. If Phase 7.4j records no-go, do not run first64 and do not claim
   broad completion. Choose Path A acceptance or a genuinely different Path B
   design family.

4. If Phase 7.4j accepts a valid consumer, run Phase 7.5 first1 reducing
   runtime with full rows/digest equality, speedup, fallback, and work
   reduction gates.

5. If Phase 7.5 passes, run Phase 7.6 first64 or a comparable broad
   characterization with the same proof family and authority model.

6. If Phase 7.6 passes, add only then a broad_replacement row to the Phase 6
   workload matrix.

7. Before any close decision, rerun Phase 0, Phase 2, Phase 5 where archive is
   claimed, Phase 6, and the relevant Phase 7 gate checks.

8. Run Phase 8 close decision only after Path A user acceptance or Path B
   broad evidence is complete.
```

The active goal is not complete at the time this document is written.

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
