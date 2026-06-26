# Fasim GASAL2 Goal Completion Finish Plan

This document is the current execution plan for making the active
Fasim/GASAL2 goal closable. It is not a success claim.

The active broad objective remains open:

```text
Use GASAL2/GPU to materially accelerate or replace the scoreInfo/preAlign /
Align-related Fasim path while preserving the required output contract.
```

Until Phase 8 explicitly closes one of the paths below:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Completion Paths

There are only two valid completion paths.

```text
Path A - scoped completion:
  allowed only if the user explicitly accepts the narrowed product

Path B - broad completion:
  required if the original scoreInfo/preAlign/Align objective remains active
```

Do not mix their evidence.

## Current Cursor

```text
current_path:
  Path B remains active unless the user explicitly accepts Path A.

current_phase:
  Phase 7 - post-v5.3 broad replacement restart.

current_gate:
  different_gpu_execution_design_or_path_a_scope_acceptance.

current_runtime_env:
  FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE=1

current_status:
  first task-frontier certificate producer ran.
  first attempt reduced attempts but changed output.
  checkpoint:
    docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go.md
  next design checkpoint:
    docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_design.md
  feasibility checkpoint:
    docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go.md
  selected proof-search design:
    docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md
  proof-search export checkpoint:
    docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export.md
  proof acceptance checkpoint:
    docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1.md
  proof-family or scope decision checkpoint:
    docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision.md

current_non_completion:
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
```

The stronger task-frontier design has a feasibility no-go under the current
descriptor information. The first1 pre-D2H proof-search export is recorded,
but the proof acceptance audit found no accepted pre-D2H proof family. The
current task is now a new proof-family design or explicit Path A scoped
completion decision, without enabling any runtime reduction.

## Phase 0: Reproducibility

Job:

```text
Make GASAL2/Fasim rebuildable from a clean checkout.
```

Do:

```text
pin GASAL2 upstream commit
track the local GASAL2 patch
keep setup/build targets idempotent
record CUDA version, SM arch, GASAL2_MAX_QUERY_LEN, and GASAL2_N_CODE
avoid untracked .tmp/GASAL2 source edits or local-only binaries
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
any claimed result depends on machine-local GASAL2 source or binary state
```

## Phase 1: Scoped Product Decision

Job:

```text
Decide whether the narrowed product is allowed to count as the delivered goal.
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

Advance to Phase 8 Path A only if:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

Stop Path A if:

```text
the user still wants the original broad scoreInfo/preAlign/Align goal
```

## Phase 2: Full-Output Equivalence Baseline

Job:

```text
Keep restored TFOsorted/full output correct before any full-output speed claim.
```

Do:

```text
preserve chr22 and chr1 restored row-set equality
separate full-output evidence from top5-only evidence
itemize convert/output wall time and whole-run wall time
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
rows, digest, ordering, restored semantics, or output authority drift
```

## Phase 3: Pre-Convert CPU Reduction

Job:

```text
Reduce CPU materialization/convert work only if the complete row set is safe.
```

Do:

```text
test only proof-first reducers
prove missing_rows = 0 and extra_rows = 0 before speed claims
prove task-frontier safety when pruning is task-local
keep failed reducers default-off and documented as stopped
```

Gate:

```text
missing_rows = 0
extra_rows = 0
task_frontier_safety = safe
real_prune_proof_gate = pass
convert_wall_seconds < Phase_2_convert_wall_seconds
```

Advance when:

```text
row_set_safe = 1
convert_wall_improves = 1
```

Stop if:

```text
the reducer preserves only top5
the reducer changes complete rows
the reducer needs final CPU output to prove safety
the reducer is row-safe but slower
```

## Phase 4: Sort/Top-N Optimization

Job:

```text
Optimize sort/top-N only if profiling shows it has become a real bottleneck.
```

Do:

```text
preserve comparator behavior
preserve tie behavior
preserve unique behavior
preserve top-N boundary behavior
defer this phase unless sort/filter dominates remaining CPU time
```

Gate:

```text
same_kept_row_set = 1
same_ordering_contract = 1
sort_or_topn_wall_improves = 1
```

Stop if:

```text
partial selection changes row identity, tie behavior, or top-N boundary
```

## Phase 5: Archive Artifact

Job:

```text
Keep the compact archive artifact able to restore claimed TFOsorted output.
```

Do:

```text
validate archive manifest
validate reference digests
verify restore without rerunning Fasim
keep archive delivery separate from broad replacement claims
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
archive_restores_claimed_output = 1
```

Stop if:

```text
the archive cannot restore claimed output or omits required reference identity
```

## Phase 6: Workload Matrix

Job:

```text
Keep every workload claim explicit and prevent hidden broad overclaiming.
```

Do:

```text
record scoped, broad, blocked, fallback-heavy, and unclaimed rows separately
add contract=broad_replacement only after a Phase 7 broad gate passes
keep top5-only, archive-only, full-output, and broad-replacement rows separate
```

Path A gate:

```text
all scoped claimed rows pass
blocked and unclaimed rows remain explicit
no broad_replacement claim is implied
```

Path B gate:

```text
claimed_broad_replacement_rows > 0
row_equal = true
digest_match = true
speedup > 1.0
fallback_accounting_clean = true
scoreinfo_reduced = true
align_side_reduced = true
```

Stop if:

```text
a fallback-heavy, output-drift, archive-only, or top5-only row is presented as broad clean
```

## Phase 7: Broad Replacement Restart

Job:

```text
Complete the original broad objective if Path A is not accepted.
```

Stopped broad sources:

```text
direct GASAL2 aligner.Align replacement
current GPU score bridge
replacement-consumer source
attempt-consumer source
emission-only source
frontier early-stop source
Gate C current source
Phase 7 v3 seed/index source
Phase 7 v4 host-visible scoreInfo source replay
Phase 7 v5 post-scoreInfo descriptor scaffold
Phase 7 v5 CPU-authority first64 replay
host-assisted GASAL2 score-only consumer selector
first_descriptor_per_scoreInfo summary
fixed_prefix_per_scoreInfo summary
```

Active design:

```text
gpu_task_frontier_certificate_with_cpu_authority_replay
```

Required authority model:

```text
CPU aligner.Align() authority = 1
GPU score authority = diagnostic only
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

### Phase 7a: Task-Frontier Certificate First1

Implement the first real producer behind:

```text
FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE=1
```

Do:

```text
use a legacy-byte CUDA scoreInfo / attempt descriptor source
group attempt descriptors by legacy task
prove task-local frontier safety on GPU before D2H
emit a compact task-frontier certificate
emit only CPU-authority replay attempts covered by the certificate
fail closed to full replay when safety cannot be proven
run CPU aligner.Align() for emitted attempts
compare full rows and digest against CPU baseline
```

Gate:

```bash
make build-fasim-gasal2
make check-fasim-gasal2-phase7-post-v5-3-task-frontier-certificate-runtime-smoke
```

First1 passes only if:

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
source_is_legacy_byte_cuda = 1
gasal2_score_only_long_query_dependency = 0
uses_task_frontier_certificate = 1
uses_prefix_boundary_only = 0
arbitrary_sparse_subset = 0
first_descriptor_per_scoreinfo = 0
fixed_prefix_per_scoreinfo = 0
gpu_consumer_reduces_before_host_transfer = 1
task_frontier_certificate_rows > 0
gpu_selected_attempts > 0
gpu_selected_attempts < v5_candidate_align_attempts
candidate_align_attempts < reference_align_attempts
descriptor_false_negatives = 0
missing_required_attempts = 0
fallback_accounting_clean = 1
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_first1_pass = 1
```

Stop if:

```text
active remains 0
certificate rows remain 0
selected attempts are not reduced
candidate Align attempts are not reduced
false negatives or missing required attempts appear
fallback accounting is not clean
first1 rows or digest differ
```

If it stops:

```text
write a no-go checkpoint
keep broad_objective_status = open
choose a genuinely different Phase 7 architecture or ask for Path A acceptance
```

### Phase 7b: First64 Broad Characterization

Run only after Phase 7a passes.

Do:

```text
run a first64-equivalent CPU baseline
run the task-frontier certificate candidate
compare full rows, digest, missing rows, extra rows, and triplex fields
itemize scoreInfo/preAlign work, Align-side work, fallback count, and wall time
```

Gate passes only if:

```text
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
fallback_accounting_clean = 1
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

Stop if:

```text
correctness changes
candidate wall is slower or near parity
scoreInfo/preAlign work is not reduced
Align-side work is not reduced
fallback accounting is not clean
```

### Phase 7c: Workload-Matrix Promotion

Run only after Phase 7b passes.

Do:

```text
add exactly one contract=broad_replacement row
record workload, command, equality, digest, speedup, fallback accounting,
scoreInfo/preAlign reduction, Align-side reduction, and authority model
keep the runtime default-off until a separate production-policy decision
```

Gate:

```text
claimed_broad_replacement_rows > 0
row_equal = true
digest_match = true
speedup > 1.0
fallback_accounting_clean = true
scoreinfo_reduced = true
align_side_reduced = true
cpu_align_authority = true
gpu_endpoint_cigar_traceback_output_authority = false
```

## Phase 8: Completion Decision

Job:

```text
Close the active goal only after Path A acceptance gates pass or Path B broad
gates pass.
```

Path A close procedure:

```bash
make check-fasim-gasal2-roadmap-phase0-reproducibility
make check-fasim-gasal2-roadmap-phase1-scoped-product
make check-fasim-gasal2-roadmap-path-a-scoped-acceptance
make check-fasim-gasal2-roadmap-phase5-archive-artifact
make check-fasim-gasal2-roadmap-phase6-workload-matrix
make check-fasim-gasal2-roadmap-phase8-completion-decision
```

Close Path A only if:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
must_not_call_update_goal_complete = 0
```

Path B close procedure:

```bash
make check-fasim-gasal2-roadmap-current-state
make check-fasim-gasal2-roadmap-phase8-completion-decision
```

Close Path B only if:

```text
claimed_broad_replacement_rows > 0
broad_gate_pass = 1
must_not_call_update_goal_complete = 0
```

If neither path passes:

```text
final_goal_decision = not_complete
broad_objective_status = open
scope_or_broad_design_decision_required = 1
path_a_user_acceptance_required = 1
path_b_new_broad_architecture_required = 1
must_not_call_update_goal_complete = 1
```

## Immediate Next PR

Title:

```text
fasim: export pre-D2H output-inert proof-search data
```

Goal:

```text
Implement the default-off first1 diagnostic export described in
docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md.
It must stay CPU-authority and must not enable runtime reduction. This is the
new pre-D2H output-inert proof step after the stronger task-frontier
feasibility no-go.
```

Do:

```text
export pre-D2H descriptor fields for first1 proof search
join those fields with CPU-authority external-output labels for offline audit
record proof_search_rows, task_count, scoreinfo_count, and attempt_count
keep runtime_reduction_enabled = 0
do not implement the current stronger task-frontier runtime as-is
keep external full rows/digest as the first1 authority
validate with:
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-design
  make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-task-frontier-certificate-feasibility-no-go
```

Do not:

```text
do not run first64 before first1 passes
do not implement current stronger task-frontier runtime without a new proof
do not enable runtime reduction from the proof-search export
do not promote broad_replacement before first64 passes
do not make GPU endpoint/CIGAR/traceback/output/digest authority
do not count output drift as speedup
do not revive first-descriptor or fixed-prefix summaries as broad paths
```

Validation for this document:

```bash
make check-fasim-gasal2-roadmap-finish-plan
```
