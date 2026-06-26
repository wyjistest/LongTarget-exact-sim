# Fasim GASAL2 Goal Completion Close Plan

This document is the canonical phase plan for making the active
Fasim/GASAL2 goal closable. It is not a completion claim.

The active broad objective remains open:

```text
Use GASAL2/GPU to materially accelerate or replace the scoreInfo/preAlign /
Align-related Fasim path while preserving the required output contract.
```

The goal can close only in Phase 8, and only through one explicit path:

```text
Path A: scoped completion
  The user explicitly accepts the narrowed product as the delivered goal.

Path B: broad completion
  The original broad objective passes equality, speed, reduction, fallback,
  and authority gates on a claimed workload.
```

Until one path passes:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Current Cursor

```text
current_path:
  Path B remains active unless the user explicitly accepts Path A.

current_phase:
  Phase 7 - Post-v5.3 Broad Replacement Restart

current_gate:
  different_gpu_execution_design_or_path_a_scope_acceptance

current_next_pr:
  fasim: design different GPU execution design or scope acceptance

current_checkpoint:
  docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go.md
  docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md
  docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export.md
  docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1.md
  docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision.md

current_runtime_contract:
  current stronger task-frontier runtime is not allowed as-is
  current proof-search export must not reduce runtime
  current proof acceptance audit found no accepted pre-D2H proof family
  first64 and reducing runtime are not allowed from this proof-search export
  any later reducer must prove output-inert skipped work before D2H
  CPU aligner.Align() remains authority
  external full rows and digest remain the first1 authority

current_known_no_go:
  v5.3 first64 CPU-authority replay was correctness-clean but slower
  v5.3 first64 had missing_required_attempts > 0
  host-assisted GASAL2 score-only selector failed the NEAT1 long-query guard
  first-attempt GPU consumer summary reduced attempts but changed lite output
  first-descriptor-per-scoreInfo summary is stopped
  fixed-prefix GPU summary either changes output or requires the full v5
    descriptor set

forbidden_now:
  do not promote a broad_replacement row before a first64 broad gate passes
  do not close from top5-only or archive-only evidence
  do not count output drift as speedup
  do not rebrand v4/v5 host-visible replay as the post-v5.3 design
  do not make GASAL2/GPU endpoint/CIGAR/traceback/output/digest authority
```

## Phase Index

| Phase | Job | Exit Gate | Close Role |
| --- | --- | --- | --- |
| 0 | Reproducible GASAL2/Fasim build | Clean checkout can rebuild and run setup/build gates | Required for both paths |
| 1 | Scoped product decision | User accepts narrowed product in writing | Required for Path A only |
| 2 | Full-output equivalence baseline | Restored full output remains row/digest clean | Foundation for full-output claims |
| 3 | Pre-convert CPU reduction | Complete row set unchanged and convert wall improves | Optional Path B helper |
| 4 | Sort/top-N optimization | Same ordering/ties/top-N with lower wall time | Optional output helper |
| 5 | Archive artifact | Compact artifact restores claimed output | Required for Path A archive delivery |
| 6 | Workload matrix | Every claim is scoped, broad, blocked, or fallback-heavy | Required ledger |
| 7 | Broad replacement restart | Broad gate passes with equality and real runtime win | Required for Path B |
| 8 | Completion decision | Path A accepted or Path B broad row passes | Only close phase |

## Phase 0: Reproducibility

Purpose:

```text
Make every GASAL2/Fasim result rebuildable from a clean checkout.
```

Do:

```text
track GASAL2 local changes as a patch or setup target
pin upstream GASAL2 commit
keep setup/build targets idempotent
record CUDA version, SM arch, GASAL2_MAX_QUERY_LEN, and GASAL2_N_CODE
remove dependence on untracked .tmp/GASAL2 edits or local binaries
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase0-reproducibility
make check-fasim-gasal2-reproducible-setup
make setup-gasal2
make build-fasim-gasal2
```

Stop if:

```text
Any result depends on a machine-local GASAL2 source edit or binary.
```

## Phase 1: Scoped Product Contract

Purpose:

```text
Decide whether the narrowed product may count as completion.
```

Path A scope:

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

Path A may continue only if:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

Stop if:

```text
The user still wants the original broad objective. Then Path A cannot close
the goal.
```

## Phase 2: Full-Output Equivalence Baseline

Purpose:

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

Stop if:

```text
Rows, digest, restored output semantics, or ordering contract drift.
```

## Phase 3: Pre-Convert CPU Reduction

Purpose:

```text
Reduce CPU materialization/convert work without changing the complete row set.
```

Do:

```text
test only proof-first reducers
prove missing_rows = 0 and extra_rows = 0 before runtime claims
prove task-frontier safety
keep failed reducers stopped and default-off
```

Gate for any future reducer:

```text
missing_rows = 0
extra_rows = 0
task_frontier_safety = safe
real_prune_proof_gate = pass
chr22 and chr1 convert wall lower than Phase 2
```

Current state:

```text
current CIGAR NT prefilter is correctness-clean but performance no-go
```

Stop if:

```text
A reducer preserves top5 but changes the full row set.
A reducer reduces work but does not beat Phase 2 wall time.
The proof depends on final rows known only after CPU work.
```

## Phase 4: Sort/Top-N Optimization

Purpose:

```text
Optimize ordering/top-N only if profiling shows it has become dominant.
```

Do:

```text
defer until Phase 2 or Phase 3 profiling makes sort/filter dominant
preserve comparator behavior
preserve tie behavior
preserve unique behavior
preserve top-N boundary behavior
```

Gate:

```text
same kept row set
same comparator/tie behavior
materially lower sort/filter wall time
```

Stop if:

```text
Partial selection changes row identity, tie behavior, or the top-N boundary.
```

## Phase 5: Archive Artifact

Purpose:

```text
Store a compact reference-backed artifact and restore TFOsorted on demand.
```

Do:

```text
validate archive manifest
validate reference digests
document restore command
verify restored output equality for every claimed mode
keep archive restore independent of rerunning Fasim
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase5-archive-artifact
make check-fasim-gasal2-archive-manifest-parser
make check-fasim-tfo-archive-integrity-parser
```

Stop if:

```text
The archive cannot restore claimed output, or the manifest lacks reference
identity needed for restore.
```

## Phase 6: Workload Matrix

Purpose:

```text
Prevent scoped or fallback-heavy evidence from being presented as broad
completion.
```

Do:

```text
record every workload claim in docs/fasim_gasal2_workload_matrix.tsv
separate scoped, unclaimed, fallback-heavy, blocked, and broad rows
add contract=broad_replacement only after Phase 7 broad gate passes
keep top5-only, archive-only, full-output, and broad-replacement rows separate
```

Path A matrix gate:

```text
all scoped claimed rows pass
blocked and unclaimed rows remain explicit
no broad_replacement claim is implied
```

Path B matrix gate:

```text
at least one claimed broad_replacement row
row_equal = true
digest_match = true
speedup > 1.0
fallbacks = 0 for the claimed GPU path
scoreinfo_reduced = true
align_side_reduced = true
```

Stop if:

```text
A fallback-heavy, output-drift, or top5-only row is presented as broad clean.
```

## Phase 7: Broad Replacement Restart

Purpose:

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
```

Active post-v5.3 shape:

```text
legacy-byte CUDA scoreInfo / attempt descriptor source runs before CPU scoreInfo
GPU consumer summary reduces per-scoreInfo candidate replay work before D2H
CPU aligner.Align() replays selected attempts as authority
GPU endpoint/CIGAR/traceback/output/digest authority remains disabled
```

### Gate v5.0: Descriptor-Emission Design

Do:

```text
keep docs/fasim_gasal2_phase7_broad_restart_v5_cuda_descriptor_emission_design.md
as the descriptor-emission checkpoint
keep prealign_cuda_emit_legacy_byte_attempt_descriptors as the baseline API
expose compact attempt descriptors, not full host-visible scoreInfo rows
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-descriptor-emission-design
```

Stop if:

```text
The implementation needs CPU preAlign or CPU scoreInfo rows to create
descriptors.
```

### Gate v5.1: True Pre-ScoreInfo Descriptor Source

Status:

```text
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke =
  gate_v5_1_pass_first1
phase7_broad_restart_v5_cpu_authority_replay_smoke =
  gate_v5_2_pass_first1
```

Required metrics:

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
scoreinfo_prealign_reduced = 1
gpu_descriptor_scoreinfos > 0
gpu_descriptor_attempts > 0
descriptor_false_negatives = 0
missing_required_attempts = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_v5_1_pass = 1
```

Next:

```text
Gate v5.2 has passed for first1. The current Path B cursor is the post-v5.3
consumer-summary first1 gate, not another v5 host-visible replay.
```

### Gate v5.2: CPU-Authority Replay First1

Purpose:

```text
Use v5.1 descriptors as the attempt source, run CPU aligner.Align(), and prove
full output equality on first1.
```

Do:

```text
feed only certified GPU-emitted descriptors to the replay path
run CPU aligner.Align() for candidate attempts
compare full rows, digest, missing rows, extra rows, and triplex fields
measure candidate Align attempts versus reference Align attempts
keep fallback accounting visible
```

Required metrics:

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
scoreinfo_prealign_reduced = 1
gpu_descriptor_scoreinfos > 0
gpu_descriptor_attempts > 0
descriptor_false_negatives = 0
missing_required_attempts = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
full_rows_equal = 1
digest_match = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
gate_v5_2_pass = 1
```

Gate:

```bash
make build-fasim-gasal2
make check-fasim-gasal2-phase7-v5-cpu-authority-replay-runtime-smoke
```

Stop if:

```text
Rows or digest differ.
The descriptor source is CPU scoreInfo/preAlign.
Align-side attempts are not reduced.
Fallback hides the candidate path.
```

Next:

```text
The first1 replay gate already passed, but the first64 v5.3 broad gate failed.
Do not continue this host-visible replay shape as the broad path.
```

### Gate v5.3: First64 Broad Gate

Purpose:

```text
Show the same architecture scales past first1 and wins wall time.
```

Current result:

```text
phase7_broad_restart_v5_cpu_authority_replay_first64_status =
  first64_correctness_clean_performance_no_go
baseline_wall_seconds = 87.827405
candidate_wall_seconds = 124.399845
candidate_vs_baseline = 0.706009
digest_match = 1
full_rows_equal = 1
missing_required_attempts = 624
fallback_accounting_clean = 0
gate_v5_3_pass = 0
```

Stop decision:

```text
The v5 host-visible replay shape is stopped as a broad completion path.
Do not add contract=broad_replacement from this result.
Continue only with a materially different post-v5.3 consumer-summary design
or ask whether Path A scoped completion is acceptable.
```

### Gate v5.4: Workload-Matrix Promotion

Do:

```text
add contract=broad_replacement only after a future broad gate passes
record workload, command, equality, digest, speedup, fallbacks, scoreInfo
reduction, Align-side reduction, and authority model
```

Required fields:

```text
claimed_broad_replacement_rows > 0
row_equal = true
digest_match = true
speedup > 1.0
fallbacks = 0 for the claimed GPU path
scoreinfo_reduced = true
align_side_reduced = true
```

Stop if:

```text
The row is top5-only, archive-only, fallback-heavy, or output-drift.
```

### Gate v5.5: Post-v5.3 Long-Query-Safe Consumer Summary First1

Purpose:

```text
Prove a new Path B shape that reduces consumer work before host transfer and
does not rely on GASAL2 score-only selection for long queries.
```

Design:

```text
docs/fasim_gasal2_phase7_post_v5_3_long_query_safe_consumer_summary_design.md
```

Runtime env:

```text
FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1
```

Do:

```text
start from legacy-byte CUDA scoreInfo / attempt descriptors
run a GPU consumer-summary stage before D2H
emit only compact per-scoreInfo summaries and selected replay attempts
run CPU aligner.Align() for authoritative replay
compare full rows and digest against CPU baseline
```

Required metrics:

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
source_is_legacy_byte_cuda = 1
gasal2_score_only_long_query_dependency = 0
gpu_consumer_summary_rows > 0
gpu_consumer_reduces_before_host_transfer = 1
gpu_selected_attempts > 0
gpu_selected_attempts < v5_candidate_align_attempts
gpu_prefix_descriptor_attempts < v5_candidate_align_attempts
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

Current result:

```text
document =
  docs/fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go.md
implementation_shape = first_descriptor_per_scoreinfo_gpu_summary
gpu_consumer_reduces_before_host_transfer = 1
gpu_selected_attempts = 718
reference_align_attempts = 2872
candidate_align_attempts = 718
baseline_lite_rows = 19
candidate_lite_rows = 25
external_digest_match = 0
external_full_rows_equal = 0
gate_first1_pass = 0
phase7_post_v5_3_gpu_consumer_summary_first_attempt_status = no_go
```

Stop if:

```text
first1 rows or digest differ
the selector depends on GASAL2 score-only for a long query
the GPU does not reduce before host transfer
selected attempts are not lower than the v5 descriptor replay count
required attempts are missing
fallback accounting is not clean
```

Next:

```text
    The first-attempt summary failed Gate v5.5. Do not run first64 from this
probe. Continue only with a stronger summary design that proves prefix-boundary
or equivalent replay safety, or return to Path A scoped decision.
post_v5_3_stronger_consumer_summary_first1_smoke_or_path_a_acceptance
```

Current stronger design:

```text
document =
  docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_design.md
phase7_post_v5_3_stronger_consumer_summary_design = defined
phase7_post_v5_3_stronger_consumer_summary_status = design_only
required_next_design_property = prefix_boundary_or_equivalent_replay_proof
next_required_gate = post_v5_3_stronger_consumer_summary_first1_smoke
```

Current stronger prefix result:

```text
document =
  docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_prefix_no_go.md
phase7_post_v5_3_stronger_consumer_summary_prefix_no_go = recorded
prefix_1_2_3_reduce_gpu_selected_attempts_but_change_output = 1
prefix_4_5_preserve_output_but_do_not_reduce_gpu_selected_attempts = 1
phase7_post_v5_3_stronger_consumer_summary_first1_gate_pass = 0
next_required_gate = different_gpu_execution_design_or_path_a_scope_decision
```

### Gate v5.6: Post-v5.3 Task-Frontier Certificate First1

Purpose:

```text
Try a materially different post-v5.3 design after fixed-prefix no-go. The GPU
must emit a task-frontier certificate, not a fixed per-scoreInfo prefix.
```

Design checkpoint:

```text
document =
  docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_design.md
phase7_post_v5_3_task_frontier_certificate_design = defined
phase7_post_v5_3_task_frontier_certificate_status = design_only
next_required_gate = post_v5_3_task_frontier_certificate_first1_smoke
```

Gate passes only if:

```text
uses_task_frontier_certificate = 1
uses_prefix_boundary_only = 0
first_descriptor_per_scoreinfo = 0
fixed_prefix_per_scoreinfo = 0
arbitrary_sparse_subset = 0
external_full_rows_equal = 1
external_digest_match = 1
gpu_selected_attempts < v5_candidate_align_attempts
candidate_align_attempts < reference_align_attempts
fallback_accounting_clean = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
current_stronger_task_frontier_first1_smoke_allowed = 0
```

### Gate v5.7: Post-v5.3 First64 Broad Characterization

Purpose:

```text
Decide whether a new post-v5.3 proof or GPU execution path is a real broad
candidate.
```

Run only after a new first1 gate passes.

Required metrics:

```text
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreinfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

Required proof:

```text
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
```

Stop if:

```text
correctness changes
candidate wall is slower or near parity
scoreInfo/preAlign work is not reduced
Align-side work is not reduced
fallback accounting is not clean
```

Next:

```text
If Gate v5.7 passes, run Gate v5.8 workload-matrix promotion.
If Gate v5.7 fails, keep the stop checkpoint and choose a different
architecture or return to Path A scoped decision.
```

### Gate v5.8: Post-v5.3 Workload-Matrix Promotion

Run only after Gate v5.7 passes.

Do:

```text
add exactly one contract=broad_replacement row to docs/fasim_gasal2_workload_matrix.tsv
include command, workload, equality, digest, speedup, fallback, reduction,
and authority fields
keep the runtime default-off until a separate production-policy decision
```

Required fields:

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

Purpose:

```text
Close the active goal only after a selected completion path passes.
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
bash scripts/check_fasim_gasal2_roadmap_current_state.sh
make check-fasim-gasal2-roadmap-phase8-completion-decision
```

Close Path B only if:

```text
claimed_broad_replacement_rows > 0
broad_gate_pass = 1
digest_match = 1
full_rows_equal = 1
candidate_vs_baseline > 1.0
scoreinfo_prealign_reduced = 1
align_side_reduced = 1
fallback_accounting_clean = 1
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

## Immediate Execution Order

```text
1. Keep Phase 0 green.
2. Keep Phase 2 and Phase 5 output/archive equivalence green.
3. If the user accepts scoped completion, run Path A gates and Phase 8.
4. If the broad objective remains active, choose a genuinely different Phase 7
   architecture; the fixed-prefix Gate v5.5 probe is no-go.
5. If a future Gate v5.5 passes, run Gate v5.6 first64 broad characterization.
6. If Gate v5.6 passes, promote exactly one broad_replacement matrix row.
7. Run Phase 8 only after Path A acceptance or a passing Path B broad row.
8. If any gate fails, record a stop checkpoint and keep the goal open.
```

## Minimal PR Units

```text
Phase 0 PR:
  reproducible GASAL2 setup/build only

Phase 1 PR:
  scoped acceptance docs only, if the user accepts Path A

Phase 2 PR:
  full-output equivalence and convert/output timing checkpoint

Phase 3 PR:
  proof-first reducer only; no promotion without full row equality and speed

Phase 4 PR:
  sort/top-N optimization only after profiling makes it dominant

Phase 5 PR:
  archive manifest/restore/equality checkpoint

Phase 6 PR:
  workload matrix update plus parser/checker

Phase 7 v5.5 PR:
  pre-D2H proof-search first1 export;
  current fixed-prefix and task-frontier runtime shapes are no-go

Phase 7 v5.6 PR:
  proof acceptance audit; no reducing runtime until this passes

Phase 7 v5.7 PR:
  reducing runtime first1 only after a pre-D2H proof passes

Phase 8 PR:
  completion decision only; closes only if Path A or Path B gates pass
```
