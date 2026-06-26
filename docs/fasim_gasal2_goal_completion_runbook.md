# Fasim GASAL2 Goal Completion Runbook

This is the operational document for closing the active Fasim/GASAL2 goal.
It does not claim completion. It defines what each phase must do, which gate
must pass, and when the goal may be marked complete.

For the canonical phase cursor and the per-phase advance contract, use
`docs/fasim_gasal2_goal_completion_phase_roadmap.md`. For the concise
phase-by-phase close plan, use
`docs/fasim_gasal2_goal_completion_close_plan.md`.

The broad objective remains open until Phase 8 closes one of the two explicit
paths below.

## Completion Rule

There are only two valid completion paths.

```text
Path A: scoped completion
  The user explicitly accepts the narrowed deliverable as the goal.

  Claimed scope:
    short-query/H19 top5 GASAL2 artifact
    MEG3-like complete-record grouping where claimed
    archive-first restored output where claimed

  Not claimed:
    aligner.Align replacement
    universal scoreInfo/preAlign replacement
    long-query NEAT1/MALAT1 replacement
    GPU endpoint/CIGAR/traceback/output/digest authority

Path B: broad completion
  The original broad objective is actually completed.

  Required proof:
    full row-set/digest equality for the claimed workload
    runtime win over the CPU authority path
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

The current broad path is Phase 7.

```text
Completed scoped milestones:
  short-query/H19 top5 GASAL2 artifact
  archive-first restored output artifact
  MEG3-like complete-record grouping

Stopped broad paths:
  direct GASAL2 aligner.Align replacement
  current GPU score bridge
  v3 seed/index certificate path
  v4 host-visible GPU legacy-byte scoreInfo source replay
  v5 post-scoreInfo descriptor scaffold

Current next Path B gate:
  post_v5_3_stronger_consumer_summary_first1_smoke

Required next implementation shape:
  GPU legacy byte scoreInfo-compatible source
  fused GPU scoreInfo consumer state machine
  prefix-boundary or equivalent replay proof
  compact candidate attempt descriptors
  CPU aligner.Align() authority replay
```

The strict runtime checkpoint is:

```text
document =
  docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_smoke.md
phase7_broad_restart_v5_cpu_authority_replay_smoke =
  gate_v5_2_pass_first1
next_required_gate =
  post_v5_3_stronger_consumer_summary_first1_smoke
design =
  docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_design.md
```

The next broad attempt must produce descriptors before CPU scoreInfo/preAlign
work. A source that reads CPU-produced scoreInfo rows cannot pass Phase 7, and
the existing v4 host-visible scoreInfo source replay must not be rebranded as
v5.

## Phase Map

| Phase | Purpose | Exit Gate | Status | Can Close Goal |
| --- | --- | --- | --- | --- |
| 0 | Make GASAL2/Fasim reproducible | Clean checkout rebuilds GASAL2 bridge and passes setup/build checks | Maintain | No, but required |
| 1 | Decide scoped contract | User acceptance recorded for Path A | Pending user decision | Path A only |
| 2 | Preserve full-output equivalence | Restored chr22/chr1 output equality stays clean | Maintain | No, foundation only |
| 3 | Reduce pre-convert CPU work safely | Missing rows = 0, extra rows = 0, faster than Phase 2 | Current reducer no-go | No, helper only |
| 4 | Optimize sort/top-N if dominant | Same comparator/tie/top-N behavior, lower wall time | Deferred | No, helper only |
| 5 | Validate archive artifact | Manifest/reference digests/restore equality pass | Maintain | Path A support |
| 6 | Maintain workload matrix | Every claim is scoped, broad, fallback-heavy, blocked, or unclaimed | Scoped rows only | Required ledger |
| 7 | Complete broad objective | Equality, speedup, scoreInfo/preAlign reduction, Align-side reduction | Active | Path B only |
| 8 | Decide close/no-close | Path A accepted or Path B broad gate passes | Not complete | Yes |

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
remove dependence on untracked .tmp/GASAL2 edits or local binaries
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
Any claimed result depends on a machine-local GASAL2 binary or untracked
GASAL2 source edit.
```

Next:

```text
Keep Phase 0 green throughout Path A and Path B.
```

## Phase 1: Scoped Product Contract

Purpose:

```text
Decide whether the existing scoped product is allowed to count as goal
completion.
```

Do:

```text
present the scoped product contract
state claims and non-claims side by side
record explicit user acceptance before using Path A
rerun scoped readiness gates before Phase 8
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
Then Path A cannot close the goal.
```

Next:

```text
If accepted, go to Phase 5, Phase 6, and Phase 8.
If not accepted, go to Phase 7.
```

## Phase 2: Full-Output Equivalence Baseline

Purpose:

```text
Keep restored TFOsorted/full output correct before claiming any full-output
speedup.
```

Do:

```text
preserve chr22 and chr1 restored row-set equality
separate full-output evidence from top5-only evidence
itemize convert/output wall time and whole-run wall time
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
Rows, digest, restored output semantics, or ordering contract drift.
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
compare missing rows and extra rows before runtime claims
prove task-local frontier safety
keep failed reducers stopped and default-off
```

Exit gate for any future reducer:

```text
missing_rows = 0
extra_rows = 0
task_frontier_safety = safe
real_prune_proof_gate = pass
chr22 and chr1 convert wall lower than Phase 2
```

Current status:

```text
The current CIGAR NT prefilter line is correctness-clean but performance
no-go, so it must stay default-off.
```

Stop if:

```text
The reducer preserves top5 but changes the complete row set.
The reducer reduces work but does not beat Phase 2 wall time.
The proof depends on final output rows known only after CPU work.
```

Next:

```text
If a reducer passes, add it to Phase 6 and include it in Phase 8 evidence.
If no reducer passes, continue Phase 7 without treating Phase 3 as completion.
```

## Phase 4: Sort/Top-N Optimization

Purpose:

```text
Optimize ordering/top-N only after profiling shows sort/filter is a material
bottleneck.
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
Partial selection changes row identity, tie behavior, or top-N boundary.
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

Do not continue these stopped sources as broad paths:

```text
direct GASAL2 aligner.Align replacement
current GPU score bridge
v3 seed/index certificate source
v4 host-visible GPU legacy-byte scoreInfo source replay
v5 post-scoreInfo descriptor scaffold
```

Required v5 architecture:

```text
GPU legacy byte scoreInfo-compatible computation
fused GPU scoreInfo consumer state machine
compact candidate attempt descriptors
CPU aligner.Align() authority replay
no GPU endpoint/CIGAR/traceback/output authority
```

### Gate v5.1: True Pre-ScoreInfo Descriptor Source

Do:

```text
run a first1 runtime smoke
emit descriptor attempts before CPU scoreInfo/preAlign work
compare against CPU authority only after descriptor emission
fail closed if no real source ran
```

Required metrics:

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
scoreinfo_prealign_reduced = 1
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
The descriptor source is post-scoreInfo.
CPU scoreInfo/preAlign work is not reduced.
False negatives or missing required attempts appear.
The descriptor count degenerates into all-column/all-window replay.
```

Next:

```text
If v5.1 passes, run Gate v5.2.
If v5.1 fails, stop this implementation and choose a materially different
GPU execution design or return to the Path A scope decision.
```

### Gate v5.2: CPU-Authority Replay First1

Do:

```text
replay candidate descriptors through CPU aligner.Align()
compare full rows, digest, missing rows, extra rows, and triplex fields
measure Align-side attempt reduction
```

Required metrics:

```text
full_rows_equal = true
digest_match = true
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
```

Stop if:

```text
Rows change.
Digest changes.
Triplex fields change.
Align-side attempts are not reduced.
```

Next:

```text
If v5.2 passes, run Gate v5.3.
```

### Gate v5.3: First64 Broad Gate

Do:

```text
run the same design on a first64-equivalent broad workload
measure total wall time against the CPU authority baseline
itemize GPU time, CPU scoreInfo/preAlign time, and CPU Align-side time
record fallback accounting
```

Required metrics:

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
The design is slower or near parity.
The design only reduces Align-side work but leaves scoreInfo/preAlign on CPU.
Fallback-heavy rows are required for the speed claim.
```

Next:

```text
If v5.3 passes, add a Phase 6 broad_replacement row and proceed to Phase 8.
If v5.3 fails, keep broad_objective_status = open.
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

## Execution Order From Current State

Use this order now:

```text
1. Keep Phase 0 green.
2. Ask whether Path A scoped completion is acceptable.
3. If Path A is accepted:
     rerun Phase 1, Phase 5, Phase 6, and Phase 8.
     close only as scoped completion.
4. If Path A is not accepted:
     continue Phase 7 with a true pre-scoreInfo v5 descriptor source.
     run the first1 runtime smoke before any larger workload.
     checkpoint:
       docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.md
5. If Gate v5.1 passes:
     run Gate v5.2.
6. If Gate v5.2 passes:
     run Gate v5.3 on a first64-equivalent broad workload.
7. If Gate v5.3 passes:
     update Phase 6 with a broad_replacement row.
     run Phase 8.
8. If Gate v5.3 fails:
     stop that architecture; do not reclassify scoped milestones as broad
     completion.
```

## Forbidden Shortcuts

Do not mark the active goal complete from:

```text
top5-only speedup without Path A acceptance
archive compression without scoreInfo/preAlign or Align-side reduction
GASAL2 launch success with output drift
post-scoreInfo descriptor scaffolds
v3/v4 stopped broad paths
GPU endpoint/CIGAR/traceback/output authority
fallback-heavy rows presented as GPU-fast-path clean
```
