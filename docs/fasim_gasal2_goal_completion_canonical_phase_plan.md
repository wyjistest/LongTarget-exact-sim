# Fasim GASAL2 Goal Completion Canonical Phase Plan

This document is the execution entry point for closing the active
Fasim/GASAL2 goal. It is a plan, not a completion claim.

The broad objective remains open until Phase 8 explicitly closes one of the
allowed paths:

```text
Use GASAL2/GPU to materially accelerate or replace the scoreInfo/preAlign /
Align-related Fasim path while preserving the required output contract.

broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Completion Paths

There are only two valid close paths.

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

Do not mix the paths. A scoped top5/archive/grouping milestone can be useful
and mergeable without closing the broad objective.

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

The current certificate producer checkpoint is useful, but it is not a runtime
reduction proof:

```text
certificate_producer_active = 1
certificate_valid_before_d2h = 1
runtime_reduction_enabled = 0
```

Historical Phase 7.3 no-go cursor:

```text
current_gate = path_a_scoped_acceptance_or_new_engine_design_doc
current_next_pr = fasim_path_a_scope_acceptance_or_new_gpu_engine_design
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
```

The Phase 7.3 first1 reducing runtime checkpoint is recorded as no-go:

```text
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.md
```

The scope/design checkpoint after that no-go is now recorded:

```text
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md
```

The current proof-consumer checkpoint is now recorded as no-go:

```text
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md
phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_status = no_go_current_descriptor_stream
path_b_current_family_stopped = 1
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_consumer_no_go
```

The different GPU execution design after that consumer no-go is now recorded:

```text
docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md
phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go = defined
phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go_status = design_defined
path_b_new_design_family = fasim_compatible_gpu_scoreinfo_frontier_certificate_engine
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
path_b_current_descriptor_family_stopped = 1
next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
```

The implementation-ready GPU scoreInfo certificate engine spec after that
design checkpoint is now recorded:

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

The first1 fail-closed shadow scaffold after that spec is now recorded:

```text
docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.md
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold = fail_closed_shadow
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
gate_first1_shadow_pass = 0
gate_first1_pass = 0
next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go
current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go
```

The consumer gate for that fail-closed shadow is now recorded as no-go:

```text
docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go = recorded
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_status = no_go_no_valid_pre_drop_certificate
accepted_scoreinfo_certificate_engine_consumer = 0
accepted_pre_drop_output_inert_certificate = 0
path_b_scoreinfo_certificate_engine_family_stopped = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go
```

The scoreInfo certificate-engine fork checkpoint is now recorded:

```text
docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go.md
path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go = recorded
path_b_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go_status = design_defined
path_b_new_design_family = gpu_owned_fasim_scoreinfo_consumer_with_pre_drop_frontier_certificate
next_valid_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
```

The GPU-owned scoreInfo consumer design spec after that fork is now recorded:

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

The GPU-owned scoreInfo consumer first1 fail-closed shadow scaffold is now
recorded:

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

## Authority Model

These invariants apply to every phase until a separate equivalence proof
changes the contract:

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
existing v5 CPU-authority replay relabelled as new engine = 0
final CPU output membership used as runtime proof = 0
```

## Phase Summary

| Phase | Purpose | Exit Gate | Completion Role |
| --- | --- | --- | --- |
| 0 | Reproducibility | Clean checkout rebuilds patched GASAL2/Fasim bridge | Required for both paths |
| 1 | Scope decision | User explicitly accepts Path A if used | Required for Path A only |
| 2 | Full-output baseline | Restored full rows and digest match CPU authority | Foundation for Path B |
| 3 | CPU output-side reduction | Missing rows = 0, extra rows = 0, CPU wall improves | Optional Path B helper |
| 4 | Sort/top-N reduction | Sort/filter is dominant and rows/order stay identical | Optional helper only |
| 5 | Archive artifact | Archive restores claimed output exactly | Required for Path A archive delivery |
| 6 | Workload matrix | Every claim is correctly scoped or broad | Required claim ledger |
| 7 | Broad GPU path | Equality, speedup, and CPU-work reductions pass | Required for Path B |
| 8 | Close decision | Path A accepted or Path B proven | Only close phase |

## Phase 0 - Reproducibility

Do:

```text
pin GASAL2 upstream commit
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
clean checkout can rebuild the exact GASAL2 bridge and Fasim binary
```

Stop if:

```text
any claimed result depends on machine-local GASAL2 state
```

## Phase 1 - Scoped Product Decision

Do:

```text
present scoped claims and non-claims together
record explicit user acceptance before using Path A
keep scoped acceleration default-off unless separately accepted
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase1-scoped-product
make check-fasim-gasal2-roadmap-path-a-scoped-acceptance
```

Path A can continue only when:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

Stop Path A if:

```text
the user still wants the original broad scoreInfo/preAlign/Align objective
```

## Phase 2 - Full-Output Baseline

Do:

```text
preserve restored TFOsorted/full row equality
preserve digest equality
itemize convert/output wall time and whole-run wall time
separate full-output evidence from top5-only evidence
keep CPU output authority
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase2-equivalence-first-convert
```

Advance when:

```text
restored rows and digest match CPU authority for the claimed workload
```

Stop if:

```text
row identity, ordering contract, digest, or restored semantics drift
```

## Phase 3 - CPU Output-Side Reduction

Do:

```text
test only proof-first reducers
prove missing_rows = 0 before speed claims
prove extra_rows = 0 before speed claims
compare against the Phase 2 full-output baseline
keep row-safe-but-slower reducers default-off
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase3-preconvert-prune
make check-fasim-gasal2-roadmap-phase3-cigar-nt-prefilter-design
```

Advance only when:

```text
missing_rows = 0
extra_rows = 0
convert wall improves over Phase 2
```

Stop if:

```text
the reducer preserves only top5
the reducer changes complete rows
the reducer requires final CPU output membership as proof
the reducer is row-safe but slower
```

## Phase 4 - Sort/Top-N Reduction

Do:

```text
measure sort/filter separately from materialization and write wall
preserve comparator behavior
preserve tie behavior
preserve selected rows and order
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase4-sort-topn
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

Do:

```text
record archive schema version
record reference digests
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

## Phase 6 - Workload Matrix

Do:

```text
label every row as claimed, unclaimed, blocked, fallback-heavy, or broad_replacement
ensure claimed rows have passing scoped contracts
ensure broad_replacement rows exist only after Phase 7 broad gates pass
keep fallback-heavy rows out of GPU-fast-path claims
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase6-workload-matrix
make check-fasim-gasal2-workload-matrix-parser
```

Advance when:

```text
claimed rows have passing scoped contracts
broad_replacement rows exist only after Phase 7 broad gates pass
```

Stop if:

```text
top5-only, archive-only, fallback-heavy, or output-drift evidence is labeled broad_replacement
```

## Phase 7 - Broad GPU Path

Purpose:

```text
complete the original broad objective, if a valid architecture exists
```

Current state:

```text
current descriptor stream cannot prove output-inert skips
accepted_pre_d2h_proof_families = 0
certificate producer synthetic first1 gate is present
real runtime certificate source is present
real_fasim_runtime_certificate_source = 1
real_fasim_runtime_work_drop_path = 0
runtime_certificate_is_synthetic = 0
source_is_pre_drop = 1
gate_first1_source_pass = 1
gate_first1_pass = 0
runtime_reduction_enabled = 0
first1_runtime_reduction_gate_pass = 0
current required gate = design_pre_drop_output_inert_work_drop_proof
```

### Phase 7.1 - New GPU Engine First1 Spec And Shadow

Do:

```text
define GpuScoreInfoTask, GpuCandidateGroup, and GpuReplayAttempt contracts
keep first1 only
keep CPU aligner.Align() as authority
fail closed when the new source is absent
```

Advance when:

```text
first1 shadow scaffold is present
the source is distinguishable from the old v5 CPU-authority replay
GPU output authority remains 0
```

### Phase 7.2 - Certificate CUDA API Producer

Do:

```text
produce conservative skipped-work certificates before D2H
keep the gate synthetic/producer-only
do not claim runtime reduction
record certificate validity telemetry
```

Advance when:

```text
certificate_producer_active = 1
certificate_valid_before_d2h = 1
CPU aligner.Align() authority = 1
GPU endpoint/CIGAR/traceback/output/digest authority = 0
```

### Phase 7.3 - First1 Reducing Runtime

This gate is a no-go for the current certificate-producer line.

Do:

```text
use the certificate-producing GPU engine before dropping work
drop only work that has a conservative pre-D2H skipped-work certificate
fallback to full CPU authority for unproven tasks
compare full external rows and digest to CPU authority
measure wall time against the CPU-authority baseline
```

Pass only when:

```text
full_rows_equal = 1
digest_match = 1
missing_rows = 0
extra_rows = 0
scoreInfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
candidate_wall_seconds < baseline_wall_seconds
CPU aligner.Align() authority = 1
GPU endpoint/CIGAR/traceback/output/digest authority = 0
```

Stop and record no-go if:

```text
the only proof comes from final CPU output
runtime reduction cannot preserve output
runtime reduction preserves output but does not reduce both work classes
candidate wall does not beat the CPU baseline
fallback accounting is dirty
```

Current result:

```text
phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go = recorded
real_fasim_runtime_certificate_source = 0
real_fasim_runtime_work_drop_path = 0
scoreInfo_prealign_reduced = 0
align_side_reduced = 0
first64_runtime_allowed = 0
```

Design response:

```text
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md
path_b_real_source_design_checkpoint_defined = 1
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md
path_b_real_source_first1_spec_defined = 1
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md
real_source_certificate_source_gate_pass = 1
real_fasim_runtime_certificate_source = 1
real_fasim_runtime_work_drop_path = 0
runtime_certificate_is_synthetic = 0
source_is_pre_drop = 1
gate_first1_source_pass = 1
gate_first1_pass = 0
next_valid_gate = design_pre_drop_output_inert_work_drop_proof
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md
phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design = defined
design_only = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
next_valid_gate = implement_pre_drop_output_inert_work_drop_proof_first1_shadow
current required gate = implement_pre_drop_output_inert_work_drop_proof_consumer_or_no_go
current_next_pr = fasim_new_gpu_engine_pre_drop_work_drop_proof_consumer_or_no_go
```

### Phase 7.4 - First1 Proof Shadow

This checkpoint is now recorded as fail-closed.

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

### Phase 7.5 - First64 Broad Gate

Run only after first1 reducing runtime passes.

Do:

```text
scale the same first1 mechanism to first64 or larger
do not introduce new authority changes
keep the same full row/digest and work-reduction gates
```

Pass only when:

```text
full_rows_equal = 1
digest_match = 1
candidate_wall_seconds < baseline_wall_seconds
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

### Phase 7.6 - Broad Promotion

Do:

```text
add a broad_replacement workload-matrix row only after Phase 7.5 passes
record workload, baseline, candidate wall, equality, fallback, and authority counters
keep scoped rows separate from broad rows
```

Advance when:

```text
claimed_broad_replacement_rows > 0
all broad rows have equality, speedup, and work-reduction evidence
```

Stop if:

```text
the only passing rows are scoped top5/archive/grouping rows
```

## Phase 8 - Close Decision

Only Phase 8 can close the active goal.

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
Phase 7.4 or larger broad gate passes
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

## Immediate Next Actions

```text
1. Run the current roadmap checks.
2. Do not run first64 from the failed Phase 7.3 first1 runtime gate.
3. If Path A is acceptable, record explicit scoped acceptance.
4. If Path B continues, implement a pre-drop output-inert proof consumer or record this family as no-go. Runtime reduction remains disabled until a proof passes.
5. Do not mark the goal complete unless Phase 8 closes Path A or Path B.
```

Required verification before the next implementation checkpoint:

```bash
make check-fasim-gasal2-roadmap-goal-closure-phase-plan
make check-fasim-gasal2-roadmap-phase-driver
make check-fasim-gasal2-roadmap-current-state
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
