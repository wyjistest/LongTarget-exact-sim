# Fasim GASAL2 Goal Completion Phase Execution Plan

This document is the phase-by-phase execution plan for making the active
Fasim/GASAL2 goal closable. It is not a success claim.

The active broad goal remains:

```text
Use GASAL2/GPU to materially accelerate or replace the scoreInfo/preAlign /
Align-related Fasim path while preserving the required output contract.
```

Until Phase 8 passes:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Completion Model

The goal can close only through one of two paths.

```text
Path A: scoped completion
  Allowed only if the user explicitly accepts the narrowed deliverable.
  It can package the short-query/H19 top5 artifact, MEG3-like grouped
  tiny-region workflow, and archive-first restored output where claimed.
  It does not complete the original broad aligner/scoreInfo objective.

Path B: broad completion
  Required while the original broad goal remains active.
  It must preserve full output equality, reduce measured CPU-side work, and
  beat the CPU-authority baseline on the claimed workload.
```

Do not mix these paths. A scoped milestone can be useful and mergeable without
closing the broad objective.

## Current Cursor

```text
current_path = Path B unless Path A is explicitly accepted
current_phase = Phase 7
current_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md
current_status = broad objective still open
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
current_checkpoint = docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold.md
```

Historical pre-upper-bound-reject-fork cursor:

```text
current_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go
current_gate_document = docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go.md
current_checkpoint = docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go.md
fork_checkpoint = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go.md
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

## Direct Completion Driver

Use this section as the execution cursor. It is intentionally stricter than
the milestone docs: each phase may create a useful checkpoint, but the active
goal can close only after Phase 8 accepts either Path A or Path B.

```text
Phase 0 - make the GASAL2 bridge reproducible
  Must prove:
    clean checkout can rebuild the patched GASAL2/Fasim bridge
  Then:
    keep this gate green for every later performance or correctness claim

Phase 1 - decide whether scoped completion is allowed
  Must prove:
    user explicitly accepts the narrowed short-query/top5/archive product
  Then:
    Path A can go to Phase 8
  Otherwise:
    stay on Path B

Phase 2 - keep full-output equality as the baseline
  Must prove:
    restored TFOsorted/full rows and digest match CPU authority
    convert/output timing is itemized
  Then:
    use this as the baseline for any full-output speed claim

Phase 3 - reduce CPU output-side work only with full row safety
  Must prove:
    missing_rows = 0
    extra_rows = 0
    convert wall improves over Phase 2
  Then:
    keep the reducer as a helper for Path B
  Otherwise:
    record no-go and leave it default-off

Phase 4 - optimize sort/top-N only if it becomes dominant
  Must prove:
    sort/filter is a material remaining bottleneck
    comparator and tie behavior stay identical
  Then:
    optimize sort/top-N as a helper only

Phase 5 - preserve archive-first restored output
  Must prove:
    archive manifest is valid
    restored rows and digest match
  Then:
    use archive as a scoped artifact or output-side accelerator

Phase 6 - keep every claim scoped in the workload matrix
  Must prove:
    every claimed row has the right contract label
    broad_replacement rows exist only after Phase 7 broad gates pass
  Then:
    use the matrix as the claim ledger for Phase 8

Phase 7 - prove or stop the broad GASAL2 path
  Current gate:
    phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
  Current next PR:
    fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
  Must prove before runtime reduction:
    GASAL2 full AlignResult proposals can be checked by a CPU verifier
    certificate before any runtime work is dropped
  Must prove before broad promotion:
    full rows/digest equal
    wall time beats CPU authority
    scoreInfo/preAlign work is reduced or replaced
    Align-side work is reduced or replaced
    fallback accounting is clean
  Otherwise:
    record no-go and either design a genuinely different proof/execution path
    or ask whether Path A scoped completion is acceptable

Phase 8 - make the only allowed close decision
  Close Path A only if:
    user_scope_acceptance_recorded = 1
    scoped_completion_may_close_goal = 1
    scoped gates are green
  Close Path B only if:
    broad_replacement workload rows exist
    Phase 7 first64 or larger broad gate passes
    CPU authority and output equality gates remain green
  Otherwise:
    keep broad_objective_status = open
    keep must_not_call_update_goal_complete = 1
```

The current broad-replacement ledger is:

```text
post_v5_3 task-frontier certificate:
  no-go, external output changed
  baseline_rows = 19
  candidate_rows = 2
  missing_rows = 17
  external_digest_match = 0
  external_full_rows_equal = 0

pre-D2H output-inert proof family:
  no-go, accepted_pre_d2h_proof_families = 0
  current_descriptor_stream_can_prove_output_inert_skips = 0

post-consumer GPU scoreInfo certificate engine:
  no-go, accepted_scoreinfo_certificate_engine_consumer = 0
  accepted_pre_drop_output_inert_certificate = 0

GPU-owned scoreInfo consumer:
  no-go, accepted_gpu_owned_scoreinfo_consumer = 0
  accepted_pre_drop_frontier_certificate = 0
  path_b_gpu_owned_scoreinfo_consumer_family_stopped = 1

current_execution_gate =
  path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go
```

## Global Invariants

Every phase must preserve these invariants:

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
stopped v3/v4/v5 sources can be promoted as-is = 0
```

## Phase Overview

| Phase | Job | Advance Gate | Can Close Goal |
| --- | --- | --- | --- |
| 0 | Reproducibility | clean checkout rebuilds GASAL2/Fasim bridge | No, but required |
| 1 | Scoped decision | user explicitly accepts Path A if used | Only Path A |
| 2 | Full-output baseline | restored row-set/digest equality stays clean | No, foundation only |
| 3 | CPU output-side reduction | complete row set preserved and CPU wall improves | No, helper only |
| 4 | Sort/top-N optimization | sort/filter shown dominant, then optimized safely | No, helper only |
| 5 | Archive artifact | archive restores claimed output exactly | Path A component |
| 6 | Workload matrix | every claim has the right scope label | No, claim ledger |
| 7 | Broad restart | equality, speedup, and CPU-work reduction pass | Path B evidence |
| 8 | Completion decision | Path A accepted or Path B proven | Yes |

## Phase 0: Reproducibility

Purpose:

```text
Make every GASAL2/Fasim result rebuildable from a clean checkout.
```

Do:

```text
pin the GASAL2 upstream commit
track the local GASAL2 patch
keep setup/build idempotent
record CUDA version, SM arch, GASAL2_MAX_QUERY_LEN, and GASAL2_N_CODE
remove dependence on machine-local .tmp/GASAL2 edits or binaries
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
any claimed result depends on untracked GASAL2 source or a local-only binary
```

## Phase 1: Scoped Decision

Purpose:

```text
Decide whether Path A is allowed to close the active goal.
```

Do:

```text
present scoped claims and non-claims together
require explicit user acceptance before Path A can close
keep scoped features default-off unless separately accepted
do not call scoped top5/archive evidence broad replacement
```

Path A claims:

```text
short-query/H19 top5 GASAL2 artifact
MEG3-like complete-record grouping where claimed
archive-first restored output where claimed
```

Path A non-claims:

```text
not aligner.Align replacement
not universal scoreInfo/preAlign replacement
not long-query NEAT1/MALAT1 broad replacement
not GPU endpoint/CIGAR/traceback/output/digest authority
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase1-scoped-product
make check-fasim-gasal2-roadmap-path-a-scoped-acceptance
```

Advance to Phase 8 Path A only when:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

Stop Path A if:

```text
the user still wants the original broad scoreInfo/preAlign/Align objective
```

## Phase 2: Full-Output Equivalence Baseline

Purpose:

```text
Keep restored TFOsorted/full output correct before any full-output speed claim.
```

Do:

```text
preserve chr22 and chr1 restored row-set equality
itemize convert/output wall time and whole-run wall time
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
rows, ordering, digest, restored semantics, or output authority drift
```

## Phase 3: CPU Output-Side Reduction

Purpose:

```text
Reduce CPU materialization/convert/output work only when complete rows stay safe.
```

Do:

```text
test only proof-first reducers
prove missing_rows = 0 before speed claims
prove extra_rows = 0 before speed claims
keep failed reducers default-off and documented as stopped
compare against Phase 2 convert/output baseline
```

Gate for any future reducer:

```text
missing_rows = 0
extra_rows = 0
task_frontier_safety = safe
real_prune_proof_gate = pass
convert_wall_seconds < phase2_convert_wall_seconds
```

Stop if:

```text
the reducer preserves only top5
the reducer changes complete rows
the reducer needs final CPU output to prove safety
the reducer is row-safe but slower
```

## Phase 4: Sort/Top-N Optimization

Purpose:

```text
Optimize sort/top-N only after profiling shows it is the dominant remaining
CPU output bottleneck.
```

Do:

```text
preserve comparator behavior
preserve tie behavior
preserve top-N row selection
measure sort/filter wall separately from materialization and write wall
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase4-sort-topn
```

Advance only if:

```text
sort_or_filter_is_dominant = 1
same_rows_and_order = 1
sort_filter_wall_improves = 1
```

Stop if:

```text
triplex materialization, write, or align-side work remains dominant
```

## Phase 5: Archive Artifact

Purpose:

```text
Keep a small reference-backed artifact that can restore the claimed output on
demand.
```

Do:

```text
store the minimum information required to restore claimed TFOsorted output
record reference digests
record archive schema version
validate restore equality
keep archive delivery separate from broad runtime replacement
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase5-archive-artifact
make check-fasim-gasal2-archive-first-output
```

Advance when:

```text
archive_manifest_valid = 1
archive_restore_rows_equal = 1
archive_restore_digest_match = 1
```

Stop if:

```text
restore requires hidden local files
restore changes row identity
archive claim is used as broad runtime replacement
```

## Phase 6: Workload Matrix

Purpose:

```text
Make every performance or correctness claim explicit and scoped.
```

Every row must be labeled as one of:

```text
claimed
unclaimed
blocked
fallback-heavy
broad_replacement
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase6-workload-matrix
make check-fasim-gasal2-workload-matrix-parser
make check-fasim-gasal2-workload-matrix
```

Advance when:

```text
claimed rows have passing contracts
broad_replacement rows exist only after Phase 7 broad gates pass
blocked and fallback-heavy rows are not described as clean GPU fast paths
```

Stop if:

```text
top5-only, archive-only, or output-drift evidence is labeled broad_replacement
```

## Phase 7: Broad Replacement Restart

Purpose:

```text
Complete the original broad objective, if it is possible.
```

This phase must prove a broad path in order. Do not skip first1, do not run
first64 from a failed first1 producer, and do not keep extending a stopped
design family. The current cursor is after the post-GPU-owned-consumer fork
checkpoint:

```text
current_gate =
  phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
current_next_pr =
  fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
```

### Phase 7a: Historical No-Go Ledger

Status:

```text
Stopped broad families:
  docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go.md
  docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md
  docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go.md
  docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md
  docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md
  docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go.md
```

Why they are stopped:

```text
current descriptor streams do not provide a valid pre-drop proof
certificate_produced_before_work_drop = 0
certificate_consumed_before_cpu_replay_selection = 0
scoreInfo_prealign_reduced = 0
align_side_reduced = 0
CPU replay attempts remain the baseline attempts
```

Stop rule:

```text
do not continue any stopped family as a reducing runtime
do not re-label fail-closed telemetry as broad replacement evidence
do not run first64 from a failed first1 consumer
```

### Phase 7b: Post-No-Go Fork Checkpoint

This docs-only checkpoint is now recorded:

```text
docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md
path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go = recorded
path_b_different_gpu_execution_design_after_gpu_owned_consumer_no_go_status = design_defined
path_b_new_design_family = gasal2_full_align_result_with_cpu_verifier_certificate
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
next_valid_gate = phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance
current_execution_gate = phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance
current_next_pr = fasim_gasal2_full_align_verifier_design_spec_or_path_a_acceptance
```

It chose Path B because Path A was not explicitly accepted:

```text
Path A:
  not accepted in this checkpoint.

Path B:
  gasal2_full_align_result_with_cpu_verifier_certificate
```

Required Path B design properties:

```text
GASAL2 proposal is treated as untrusted alignment result data
certificate is checkable by CPU before CPU Align work is skipped
certificate can prove score/end/start/CIGAR compatibility or fail closed
consumer decision point is before any CPU Align work is dropped
scoreInfo/preAlign replacement remains required before broad promotion
CPU aligner.Align() remains replay authority
GPU endpoint/CIGAR/traceback/output/digest authority remains 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first64_runtime_allowed = 0
```

Advance when:

```text
Path A accepted:
  go to Phase 8 scoped close packet.

Path B design accepted:
  go to Phase 7c with a full-align verifier first1 fail-closed shadow spec.
```

Stop if:

```text
the proposal is only a new name for a stopped descriptor/certificate family
the proposal needs final CPU output as its runtime safety proof
the proposal makes GPU output authoritative
the proposal enables runtime work drop before a first1 proof passes
```

### Phase 7b.1: Full-Align Verifier Design Spec

This docs-only checkpoint is now defined:

```text
docs/fasim_gasal2_phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance.md
phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance = defined
phase7_full_align_verifier_design_spec_status = spec_defined
path_b_design_family = gasal2_full_align_result_with_cpu_verifier_certificate
path_b_full_align_verifier_spec_defined = 1
path_b_full_align_verifier_first1_fail_closed_shadow_allowed = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
current_execution_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
current_next_pr = fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
```

The spec defines untrusted GASAL2 full-align proposal fields, CPU verifier
certificate fields, fail-closed failure taxonomy, and first1 shadow telemetry.
It does not allow runtime reduction or GASAL2 endpoint/CIGAR/traceback/output
authority.

### Phase 7c: Full-Align Verifier First1 Fail-Closed Shadow

Do:

```text
implement only observable first1 telemetry for the full-align verifier design
emit GASAL2 score/end/start/CIGAR proposals
run the CPU verifier and CPU aligner.Align() comparison
keep runtime_reduction_enabled = 0
keep runtime_work_drop_enabled = 0
keep CPU aligner.Align() replay authority
export enough fields to audit score, endpoint, CIGAR, full-row, and digest drift
```

Pass gate:

```text
requested = 1
active = 1
proposals > 0
verifier_pass > 0 or verifier failure taxonomy complete
score_mismatches = 0
endpoint_mismatches = 0
cigar_mismatches = 0
full_rows_equal = 1
digest_match = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
gpu_endpoint_cigar_traceback_output_authority = 0
gpu_output_digest_authority = 0
gate_first1_shadow_pass = 1
```

Advance when:

```text
first1 fail-closed shadow proves a CPU-checkable alignment certificate exists
GASAL2 proposals match CPU aligner.Align() on full rows and digest
```

Stop if:

```text
score, endpoint, CIGAR, full row, or digest drift appears
the CPU verifier cannot prove the proposal without rerunning full CPU Align
the design has no plausible scoreInfo/preAlign replacement path for broad gate
```

### Phase 7d: Reducing Runtime First1

Do:

```text
enable a separate default-off first1 reducing runtime only after Phase 7c
consume the accepted verifier certificate before skipping CPU Align work
fallback to CPU aligner.Align() for unverified proposals
compare external full rows and digest against baseline
```

Pass gate:

```text
requested = 1
active = 1
uses_cpu_verifier_certificate = 1
verifier_consumed_before_cpu_align_skip = 1
candidate_align_attempts < reference_align_attempts
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
external_digest_match = 1
external_full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
fallback_accounting_clean = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_first1_pass = 1
```

Stop if:

```text
external output changes
missing rows or extra rows appear
candidate attempts are not reduced
CPU scoreInfo/preAlign work is not reduced
the implementation needs final CPU output as its runtime proof
```

### Phase 7e: First64 Broad Characterization

Do:

```text
run first64 only after Phase 7d passes
measure baseline wall and candidate wall
measure scoreInfo/preAlign reduction
measure Align-side reduction
preserve full output equality
```

Pass gate:

```text
external_digest_match = 1
external_full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
```

Advance when:

```text
first64_broad_gate = pass
```

Stop if:

```text
first64 is correctness-clean but slower
first64 reduces only one bottleneck
fallback accounting is not clean
```

### Phase 7f: Scale Gate

Do:

```text
repeat the passing first64 broad path on larger representative workloads
include chr22 or another agreed broad workload
keep all output and authority gates identical
record GPU/CPU timing breakdown
```

Pass gate:

```text
scale_digest_match = 1
scale_full_rows_equal = 1
scale_wall_speedup > 1.0
scale_scoreInfo_prealign_reduced = 1
scale_align_side_reduced = 1
scale_fallback_accounting_clean = 1
```

Stop if:

```text
the path only works on first1/first64 but not on the representative workload
```

### Phase 7g: Workload-Matrix Promotion

Do:

```text
add broad_replacement rows only for workloads that passed Phase 7e or 7f
record exact env, binary, command, commit, workload, wall time, and output gate
do not promote stopped sources
```

Gate:

```text
claimed_broad_replacement_rows > 0
all_broad_rows_have_equality = 1
all_broad_rows_have_speedup = 1
all_broad_rows_have_cpu_authority = 1
```

Stop if:

```text
the workload matrix would need a broad row from top5-only, archive-only,
fallback-heavy, or output-drift evidence
```

Phase 7 completion condition:

```text
Phase 7 may feed Phase 8 Path B only after Phase 7e or Phase 7f passes and
Phase 7g adds at least one clean broad_replacement row.
```

Stop if:

```text
Path A is not accepted and no genuinely different Path B design can be written
without reusing a stopped proof/consumer family.
```

## Phase 8: Completion Decision

Purpose:

```text
Make the only allowed decision that can close the active goal.
```

Path A close packet:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
Phase 0 green
Phase 5 archive restore green where claimed
Phase 6 workload matrix clean for scoped rows
clear non-claims recorded
```

Path B close packet:

```text
Phase 0 green
Phase 2 full-output baseline green
Phase 6 workload matrix has at least one passing broad_replacement row
Phase 7 first64 or larger broad gate passes
full_rows_equal = 1
digest_match = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_wall_seconds < baseline_wall_seconds
scoreInfo/preAlign work reduced or replaced = 1
Align-side work reduced or replaced = 1
fallback_accounting_clean = 1
CPU aligner.Align() authority = 1
GPU endpoint/CIGAR/traceback/output/digest authority = 0
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase8-completion-decision
make check-fasim-gasal2-roadmap-current-state
```

The active goal may be marked complete only if:

```text
path_a_close_packet_pass = 1
```

or:

```text
path_b_close_packet_pass = 1
```

Otherwise keep:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Immediate Next PR

Title:

```text
fasim: design GASAL2 full-align verifier certificate shadow
```

Phase:

```text
Phase 7c / full-align verifier spec
```

Goal:

```text
Define the fail-closed first1 shadow spec for the
gasal2_full_align_result_with_cpu_verifier_certificate design. Do not enable
runtime reduction.
```

Must do:

```text
use docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md as input
define the GPU proposal schema for score/end/start/CIGAR/request identity
define the CPU verifier certificate schema
define verifier failure taxonomy and fallback accounting
define first1 fail-closed telemetry
keep runtime_reduction_enabled = 0
keep runtime_work_drop_enabled = 0
keep first64_runtime_allowed = 0
preserve CPU aligner.Align() replay authority
```

Must not do:

```text
no runtime reduction in the verifier spec checkpoint
no GASAL2 endpoint authority
no GASAL2 CIGAR or traceback authority
no GASAL2 output or digest authority
no continuation of the stopped GPU-owned shadow as a reducing runtime
no continuation of the stopped scoreInfo certificate-engine family
no continuation of the stopped post-v5.3 descriptor-stream family
no first64 before first1 passes
no first64 before first1 runtime reduction passes
no broad_replacement matrix promotion before first64 or larger gate passes
no GPU endpoint authority
no GPU CIGAR or traceback authority
no GPU output or digest authority
no default runtime change
no Path A scoped completion unless the user explicitly accepts Path A
```

Expected decision after the next PR:

```text
If the verifier spec is coherent and keeps all authority gates fail-closed:
  implement only a Phase 7c first1 fail-closed shadow next.

If the verifier spec cannot define a CPU-checkable certificate:
  keep broad_objective_status = open and do not mark the active goal complete.
```
