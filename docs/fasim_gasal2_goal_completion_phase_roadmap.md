# Fasim GASAL2 Goal Completion Phase Roadmap

This document defines the phase-by-phase route for completing the active
Fasim/GASAL2 goal. It is a close plan, not a success claim.

For the current finish plan that says exactly which phase and gate to run next,
use `docs/fasim_gasal2_goal_completion_finish_plan.md`. For the concise
phase-by-phase close plan, use
`docs/fasim_gasal2_goal_completion_close_plan.md`.

The active broad goal is still open until Phase 8 selects one of the two
completion paths below.

## Completion Paths

There are only two valid ways to complete the goal.

```text
Path A: scoped completion
  Meaning:
    The user explicitly accepts the narrowed deliverable as the goal.

  Deliverable:
    short-query/H19 top5 GASAL2 artifact
    MEG3-like grouped tiny-region workflow where claimed
    archive-first restored output where claimed

  Not claimed:
    aligner.Align replacement
    universal scoreInfo/preAlign replacement
    long-query NEAT1/MALAT1 broad replacement
    GPU endpoint/CIGAR/traceback/output/digest authority

Path B: broad completion
  Meaning:
    The original broad objective is actually completed.

  Required proof:
    full row-set/digest equality for the claimed workload
    runtime win over CPU authority
    scoreInfo/preAlign work reduced or replaced
    Align-side work reduced or replaced
    fallback accounting clean
    CPU aligner.Align() remains semantic authority unless separately proven
```

If neither path passes, keep:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Current Pointer

The current broad path is in Phase 7.

```text
Completed scoped milestones:
  short-query/H19 top5 GASAL2 artifact is a real scoped GPU path
  archive-first output restore is useful for output delivery
  MEG3-like complete-record grouping has strong runtime evidence

Stopped broad paths:
  direct GASAL2 aligner.Align replacement
  current score bridge / GPU score path
  current v3 seed/index path
  current v4 source replay broad path

Current broad restart candidate:
  Phase 7 v5 fused scoreInfo consumer design
  Phase 7 v5 true pre-scoreInfo descriptor source design
  Phase 7 v5 true pre-scoreInfo descriptor source first1 smoke pass
  Phase 7 v5 CPU-authority replay first1 smoke pass

Next gate if Path B continues:
  different_gpu_execution_design_or_path_a_scope_acceptance
```

Do not continue stopped sources as broad completion paths. They can remain as
evidence only.

## Phase Cursor

Use this cursor before starting any new GASAL2/Fasim work.

```text
Current path:
  Path B is active unless the user explicitly accepts Path A scoped completion.

Current phase:
  Phase 7, broad replacement restart.

Current executable subphase:
  Gate v5.3 first64 broad characterization completed as no-go.

Current implementation target:
  v5.3 first64 no-go, fixed-prefix no-go, and first task-frontier certificate
  no-go checkpoints are recorded. The stronger task-frontier certificate
  feasibility checkpoint is also no-go. The selected proof-family or scope
  decision checkpoint is defined. The next Path B step is a new pre-D2H
  proof-family first1 smoke, unless Path A scoped completion is accepted.

Current validation target:
  different_gpu_execution_design_or_path_a_scope_acceptance.

Current forbidden shortcut:
  Do not close the goal from top5-only, archive-only, v4 host-visible
  scoreInfo replay, output-drift, or fallback-heavy evidence.
```

Advance only one gate at a time:

```text
Phase 0:
  Keep reproducibility green before relying on any result.

Phase 1:
  Use only if the user accepts scoped completion. If not accepted, skip to
  Phase 7 and keep the broad objective open.

Phase 2:
  Keep restored full output equality as the baseline for any full-output
  speedup claim.

Phase 3:
  Try a CPU-side reducer only if it can prove missing_rows=0 and extra_rows=0
  before performance claims.

Phase 4:
  Defer until sort/top-N is shown to dominate remaining CPU time.

Phase 5:
  Keep the archive artifact restorable, but do not treat archive delivery as
  broad acceleration by itself.

Phase 6:
  Update the workload matrix after every claim. Add broad_replacement only
  after Phase 7 broad gates pass.

Phase 7:
  Execute the v5 gates in order:
    v5.0 design checkpoint
    v5.1 true pre-scoreInfo descriptor source
    v5.2 CPU-authority replay
    v5.3 first64 broad gate
    v5.4 workload-matrix promotion

Phase 8:
  Close only if Path A acceptance gates pass or Path B broad gates pass.
```

## Phase Summary

| Phase | Purpose | Exit Gate | Completion Role |
| --- | --- | --- | --- |
| 0 | Make GASAL2/Fasim reproducible | Clean checkout can rebuild GASAL2 bridge and pass setup/build checks | Required for Path A and Path B |
| 1 | Decide scoped contract | User explicitly accepts scoped product if Path A is used | Required for Path A only |
| 2 | Preserve full-output equivalence | Restored chr22/chr1 row-set or digest equality remains clean | Foundation for any full-output claim |
| 3 | Reduce pre-convert CPU work safely | Missing rows = 0, extra rows = 0, wall time beats Phase 2 | Optional Path B helper |
| 4 | Optimize sort/top-N only if needed | Same comparator/tie/top-N behavior with lower sort wall | Optional output-side helper |
| 5 | Validate archive artifact | Manifest, reference digests, and restore equality pass | Required for Path A archive delivery |
| 6 | Maintain workload matrix | Every claim is scoped, broad, fallback-heavy, blocked, or unclaimed | Required claim ledger |
| 7 | Complete original broad objective | Broad first64-equivalent gate passes with equality and speedup | Required for Path B |
| 8 | Make completion decision | Path A acceptance gates pass or Path B broad gate passes | Only close phase |

## Phase 0: Reproducibility

Purpose:

```text
Make every GASAL2/Fasim result reproducible from a clean checkout.
```

Do:

```text
track the GASAL2 local patch
pin the upstream GASAL2 commit
keep setup/build targets idempotent
record CUDA version, SM arch, GASAL2_MAX_QUERY_LEN, and GASAL2_N_CODE
remove dependence on untracked .tmp/GASAL2 edits
```

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase0-reproducibility
make check-fasim-gasal2-reproducible-setup
make setup-gasal2
make build-fasim-gasal2
```

Stop if:

```text
Any claim depends on a machine-local GASAL2 binary or untracked GASAL2 source
edit.
```

Next:

```text
If Path A is being considered, go to Phase 1.
If Path B is being pursued, keep Phase 0 green while continuing to Phase 2/7.
```

## Phase 1: Scoped Product Contract

Purpose:

```text
Decide whether the narrowed product is allowed to count as goal completion.
```

Do:

```text
present the scoped product contract
state non-claims next to claims
record explicit user acceptance before using Path A
keep all scoped features default-off unless separately accepted
```

Exit gate:

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
The user still wants the original broad scoreInfo/preAlign/Align objective.
Then Path A cannot complete the goal.
```

Next:

```text
If accepted, go to Phase 5 and Phase 6, then Phase 8.
If not accepted, go to Phase 7.
```

## Phase 2: Full-Output Equivalence Baseline

Purpose:

```text
Keep restored TFOsorted/full output correct before claiming full-output
speedup.
```

Do:

```text
preserve chr22 and chr1 restored row-set equality
separate full-output evidence from top5-only evidence
itemize convert/output time and whole-run time
keep CPU output authority
```

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase2-equivalence-first-convert
make check-fasim-gasal2-archive-first-output
make check-fasim-gasal2-convert-cpu-breakdown
```

Stop if:

```text
Rows, digest, ordering contract, or restored output semantics drift.
```

Next:

```text
Use Phase 2 as the output baseline for Phase 3 and Phase 7.
```

## Phase 3: Pre-Convert CPU Reduction

Purpose:

```text
Reduce CPU materialization/convert work without changing the complete row set.
```

Do:

```text
test only proof-first reducers
compare missing rows and extra rows before performance claims
prove task-local frontier safety
keep failed reducers stopped/default-off
```

Exit gate for a future reducer:

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
The reducer preserves top5 but changes the full row set.
The reducer reduces work but does not beat Phase 2 wall time.
The proof depends on final output rows already known only after CPU work.
```

Next:

```text
If a reducer passes, update Phase 6 and include it in Phase 8 evidence.
If no reducer passes, continue Phase 7 without treating Phase 3 as completion.
```

## Phase 4: Sort/Top-N Optimization

Purpose:

```text
Optimize ordering/top-N only after profiling shows it is a real bottleneck.
```

Do:

```text
defer until Phase 2/3 profiling says sort/filter dominates
preserve comparator behavior
preserve tie behavior
preserve unique behavior
preserve top-N boundary behavior
```

Exit gate:

```text
same kept row set
same comparator/tie behavior
materially lower sort/filter wall time
```

Stop if:

```text
Partial selection changes row identity, tie behavior, or the top-N boundary.
```

Next:

```text
Use only as an output-side helper. Phase 4 never completes the goal alone.
```

## Phase 5: Archive Artifact

Purpose:

```text
Store the smallest sufficient artifact and restore TFOsorted on demand.
```

Do:

```text
validate archive manifest
validate reference digests
document restore command
verify restored output equality for every claimed mode
keep archive format independent of rerunning Fasim
```

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase5-archive-artifact
make check-fasim-gasal2-archive-manifest-parser
make check-fasim-tfo-archive-integrity-parser
```

Stop if:

```text
The archive cannot restore the claimed output without rerunning Fasim.
The manifest omits reference identity needed for later restore.
```

Next:

```text
For Path A, combine with Phase 1 and Phase 6 before Phase 8.
For Path B, treat archive as output delivery support, not broad acceleration.
```

## Phase 6: Workload Matrix

Purpose:

```text
Prevent hidden overclaiming across workloads.
```

Do:

```text
record every claimed workload
separate scoped, unclaimed, fallback-heavy, blocked, and broad rows
add contract=broad_replacement only after Phase 7 broad gate passes
keep top5-only, archive-only, full-output, and broad-replacement rows separate
```

Path A exit gate:

```text
all scoped claimed rows pass
blocked and unclaimed rows remain explicit
no broad_replacement claim is implied
```

Path B exit gate:

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

Next:

```text
For Path A, proceed to Phase 8 after scoped acceptance.
For Path B, proceed to Phase 7 until a broad_replacement row exists.
```

## Phase 7: Broad Replacement Restart

Purpose:

```text
Complete the original broad objective if scoped completion is not accepted.
```

Do not continue as broad paths:

```text
direct GASAL2 aligner.Align replacement
current GPU score bridge
current replacement-consumer source
attempt-consumer source
emission-only source
frontier early-stop source
Gate C current source
Phase 7 v3 current seed/index source
Phase 7 v4 host-visible source replay
```

Next Path B design:

```text
Phase 7 v5 fused scoreInfo consumer:
  GPU legacy byte scoreInfo-compatible source
  fused GPU consumer state machine
  compact candidate attempt descriptors
  CPU aligner.Align() authority replay
```

Required v5 gates:

```text
Gate v5.1: first1 descriptor contract
  gpu/native descriptor attempts > 0
  cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
  missing_required_attempts = 0
  descriptor_false_negatives = 0
  candidate attempts stay below all-column replay scale

Gate v5.2: first1 CPU-authority replay
  full_rows_equal = true
  digest_match = true
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  candidate_align_attempts < reference_align_attempts

Gate v5.3: first64 broad gate
  full_rows_equal = true
  digest_match = true
  candidate_wall_seconds < baseline_wall_seconds
  candidate_vs_baseline > 1.0
  scoreInfo/preAlign work reduced or replaced
  Align-side work reduced or replaced
  fallback_accounting_clean = true
```

### Gate v5.0: Design Checkpoint

Purpose:

```text
Select the only active Path B architecture after v3/v4 stopped:
CUDA emits compact attempt descriptors before CPU scoreInfo/preAlign work.
```

Do:

```text
keep docs/fasim_gasal2_phase7_broad_restart_v5_cuda_descriptor_emission_design.md
as the design authority
keep prealign_cuda_emit_legacy_byte_attempt_descriptors as the promoted API name
expose compact attempt descriptors, not full host-visible scoreInfo rows
keep CPU aligner.Align() as replay/output authority
```

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-descriptor-emission-design
```

Stop if:

```text
The implementation source is CPU-produced scoreInfo rows.
The interface exposes PreAlignCudaPeak rows as the promoted v5 source.
GPU endpoint/CIGAR/traceback/output authority is introduced.
```

### Gate v5.1: True Pre-ScoreInfo Descriptor Source

Purpose:

```text
Prove the GPU path emits useful attempt descriptors before CPU scoreInfo or
preAlign generation.
```

Do:

```text
add or keep the descriptor struct/API in cuda/prealign_cuda.h
add the fail-closed CPU-only stub in cuda/prealign_cuda_stub.cpp
add the CUDA descriptor-emission implementation in cuda/prealign_cuda.cu
wire a default-off runner in fasim/Fasim-LongTarget.cpp
call the descriptor-emission API before normal CPU scoreInfo/preAlign work
use CPU preAlign only after GPU emission to validate descriptor coverage
do not alter candidate state, output, digest, endpoint, CIGAR, or traceback
```

Exit gate:

```bash
make check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke
```

The runtime smoke must report:

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
scoreinfo_prealign_reduced = 1
tasks > 0
reference_scoreinfos > 0
reference_attempts > 0
gpu_descriptor_scoreinfos > 0
gpu_descriptor_attempts > 0
descriptor_false_negatives = 0
missing_required_attempts = 0
candidate_attempts_below_all_column_replay_scale = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_v5_1_pass = 1
```

Stop if:

```text
active stays 0.
descriptors are derived from CPU scoreInfo rows.
false negatives or missing required attempts appear.
candidate attempts explode to all-column/all-window replay scale.
CPU scoreInfo/preAlign is not actually bypassed as the source.
```

Next:

```text
If v5.1 passes, write a runtime-pass checkpoint and advance to v5.2.
If v5.1 fails, write a no-go checkpoint and choose a new architecture or Path A.
```

### Gate v5.2: CPU-Authority Replay

Purpose:

```text
Use the v5.1 descriptors as candidate attempts while CPU Align() remains the
semantic authority, then prove output equality on first1.
```

Do:

```text
consume only GPU-emitted attempt descriptors
run CPU aligner.Align() for accepted candidate attempts
compare full rows against the CPU-authority baseline
itemize candidate attempts, reference attempts, scoreInfo/preAlign work, and
Align-side work
keep fallback and validation counters explicit
```

Exit gate:

```text
full_rows_equal = true
digest_match = true
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
scoreInfo/preAlign work reduced or replaced
CPU aligner.Align() authority = 1
GPU endpoint/CIGAR/traceback/output authority = 0
```

Stop if:

```text
Any row differs.
The descriptor source needs CPU scoreInfo rows.
Align attempts are not reduced.
The replay hides fallback or validation failures.
```

Next:

```text
If v5.2 passes, advance to v5.3 first64 broad characterization.
If v5.2 fails, stop the v5 source and keep the broad objective open.
```

### Gate v5.3: First64 Broad Gate

Purpose:

```text
Show the architecture scales beyond first1 and wins wall time on a
first64-equivalent broad workload.
```

Do:

```text
run baseline CPU-authority first64 workload
run candidate v5 descriptor-source first64 workload
compare full rows and digest
compare wall time, scoreInfo/preAlign work, Align-side work, fallback count,
and validation cost
```

Exit gate:

```text
full_rows_equal = true
digest_match = true
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
fallback_accounting_clean = true
```

Stop if:

```text
Wall time is near parity or slower.
The GPU source reduces scoreInfo/preAlign but increases Align-side work enough
to lose overall.
The path is correct only for first1.
Fallback or validation dominates the candidate wall time.
```

Next:

```text
If v5.3 passes, advance to v5.4 workload-matrix promotion.
If v5.3 fails, do not claim broad completion; choose a different architecture
or ask for Path A scope acceptance.
```

### Gate v5.4: Workload-Matrix Promotion

Purpose:

```text
Record the first broad claim only after the broad gate has passed.
```

Do:

```text
add one contract=broad_replacement row to docs/fasim_gasal2_workload_matrix.tsv
record workload, command, output contract, row equality, digest, speedup,
fallbacks, scoreInfo/preAlign reduction, Align-side reduction, and authority
model
keep scoped/top5/archive rows separate from broad_replacement rows
```

Exit gate:

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
The row depends on GPU endpoint/CIGAR/traceback/output authority.
```

Next:

```text
If v5.4 passes, run Phase 8 completion decision.
```

Stop if:

```text
Correctness changes.
False negatives or missing required attempts appear.
CPU scoreInfo/preAlign work is not reduced.
Align-side work is not reduced.
Wall time is near parity or slower.
The implementation degenerates into all-column/all-window replay.
```

Next:

```text
If Gate v5.3 passes, add a Phase 6 broad_replacement row and go to Phase 8.
If Gate v5.3 fails, keep broad_objective_status = open and choose either a
new materially different architecture or Path A scope decision.
```

## Phase 8: Completion Decision

Purpose:

```text
Close the active goal only after the selected completion path passes.
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

## Practical Execution Order

Use this order from the current state:

```text
1. Keep Phase 0 green.
2. Ask whether Path A scoped completion is acceptable.
3. If Path A is accepted:
     rerun Phase 1, Phase 5, Phase 6, and Phase 8 gates.
     close only as scoped completion.
4. If Path A is not accepted:
     continue Phase 7 with a true pre-scoreInfo v5 descriptor source.
     run the first1 runtime smoke before any larger workload.
5. If Gate v5.1 passes:
     run Gate v5.2.
6. If Gate v5.2 passes:
     run Gate v5.3 on first64-equivalent broad workload.
7. If Gate v5.3 passes:
     update Phase 6 with a broad_replacement row.
     run Phase 8.
8. If Gate v5.3 fails:
     stop that architecture; do not reclassify scoped milestones as broad
     completion.
```

## Minimal PR Units

Keep each future PR narrow enough that a reviewer can decide one gate at a
time.

```text
PR unit for Phase 0:
  docs/scripts/setup/build only
  proves clean checkout reproducibility
  no runtime behavior change

PR unit for Phase 1:
  docs-only acceptance packet update
  records user scope acceptance if provided
  no broad claim

PR unit for Phase 2:
  docs/script result checkpoint
  proves restored full-output equality and convert/output timing
  no new pruning semantics

PR unit for Phase 3:
  default-off reducer plus proof checker
  promotes only after missing_rows=0 and extra_rows=0
  stops if speed is no-go

PR unit for Phase 4:
  sort/top-N micro-optimization only after profiling
  preserves comparator and tie behavior

PR unit for Phase 5:
  archive format/checker/update
  proves restore without rerunning Fasim

PR unit for Phase 6:
  workload matrix row update plus parser/checker
  never mixes scoped and broad contracts

PR unit for Phase 7 v5.1:
  CUDA descriptor-emission API/prototype
  default-off runtime smoke
  no candidate/output/digest authority changes

PR unit for Phase 7 v5.2:
  CPU-authority replay from v5 descriptors
  first1 row/digest equality
  itemized attempt/work reduction
  docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_smoke.md

PR unit for Phase 7 v5.3:
  first64 broad characterization
  full equality plus wall-time win
  fallback accounting

PR unit for Phase 7 v5.4:
  workload matrix broad_replacement promotion only after v5.3 passes

PR unit for Phase 8:
  docs/checker decision only
  closes only if Path A accepted or Path B broad gate passed
```

## Active Next PR

The next implementation PR, if the broad objective is still being pursued, is:

```text
Title:
  fasim: design different GPU execution design or scope acceptance

Phase:
  Phase 7 post-v5.3 proof-family first1 or scope acceptance follow-up

Goal:
  Start from the first1 proof-search export and acceptance no-go checkpoint.
  Either design a new pre-D2H proof family that could pass false-negative audit
  before runtime reduction, or return to the explicit Path A scoped decision.

Evidence already recorded:
  scripts/characterize_fasim_gasal2_phase7_v5_cpu_authority_replay_first64.sh
  scripts/check_fasim_gasal2_phase7_v5_cpu_authority_replay_first64_result.sh
  docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate.md
  current v5.3 CPU-authority descriptor replay first64 gate, fixed-prefix
  consumer-summary gate, first task-frontier certificate gate, and stronger
  task-frontier feasibility gate are already recorded as no-go.

Next files expected:
  new proof-family design checkpoint, or Path A scoped decision packet update;
  do not write a reducing runtime from the current proof-search export

Must not do:
  no current stronger task-frontier runtime without a new proof
  no runtime reduction in the proof-search export
  no GPU endpoint authority
  no GPU CIGAR or traceback
  no GPU output or digest authority
  no default runtime change
  no broad_replacement matrix promotion from the v5.3 no-go result
```

Validation:

```bash
make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-first64-broad-gate
bash scripts/check_fasim_gasal2_roadmap_execution_ladder.sh
bash scripts/check_fasim_gasal2_roadmap_phase_checklist.sh
bash scripts/check_fasim_gasal2_roadmap_current_state.sh
git diff --check
```

Expected decision after this PR:

```text
If a new Path B architecture is chosen:
  write the design checkpoint before reducing runtime work

If Path A scoped completion is accepted:
  run Phase 0, Phase 1, Phase 5, Phase 6, and Phase 8 gates

If neither is chosen:
  keep broad_objective_status=open
  must_not_call_update_goal_complete=1
```
