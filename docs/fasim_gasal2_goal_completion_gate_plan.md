# Fasim GASAL2 Goal Completion Gate Plan

This is the short execution plan for making the active GASAL2/Fasim goal
closable. It is a plan, not a completion claim.

The active broad goal remains open:

```text
Use GASAL2/GPU to materially accelerate or replace the scoreInfo/preAlign /
Align-related Fasim path while preserving the required output contract.
```

The goal can close only in Phase 8. Until then:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Completion Paths

There are two valid close paths. Do not mix their evidence.

```text
Path A: scoped completion
  Use only if the user explicitly accepts the narrowed deliverable:
    short-query/H19 top5 GASAL2 artifact
    MEG3-like grouped tiny-region workflow where claimed
    archive-first restored output where claimed

  Non-claims:
    not aligner.Align replacement
    not universal scoreInfo/preAlign replacement
    not long-query NEAT1/MALAT1 broad replacement
    not GPU endpoint/CIGAR/traceback/output/digest authority

Path B: broad completion
  Use if the original goal remains active.

  Required proof:
    full row-set/digest equality for the claimed workload
    runtime win over CPU authority
    scoreInfo/preAlign work reduced or replaced
    Align-side work reduced or replaced
    fallback accounting clean
    CPU aligner.Align() remains semantic authority unless separately proven
```

Current working assumption:

```text
Path B is active unless the user explicitly accepts Path A.
```

## Current Cursor

```text
current_phase:
  Phase 7 - Post-v5.3 Broad Replacement Restart

current_gate:
  different_gpu_execution_design_or_path_a_scope_acceptance

current_next_work:
  design a different GPU execution design or record Path A scoped
  completion acceptance

current_required_contract:
  do not implement the current stronger task-frontier runtime as-is
  keep runtime_reduction_enabled = 0
  current proof acceptance audit has accepted_pre_d2h_proof_families = 0
  do not run first64 or reducing runtime from the current proof-search export
  use CPU aligner.Align() and external output only as offline labels
  do not use final CPU output as a future runtime proof

forbidden_shortcuts:
  no broad completion from top5-only evidence
  no broad completion from archive-only evidence
  no broad completion from output-drift speedups
  no broad_replacement workload row before a first64 broad gate passes
  no first64 run from the failed first-descriptor-per-scoreInfo probe
  no GPU endpoint/CIGAR/traceback/output/digest authority
```

## Phase Plan

### Phase 0: Reproducibility

Goal:

```text
Make GASAL2/Fasim results rebuildable from a clean checkout.
```

Do:

```text
track the GASAL2 local patch
pin the upstream GASAL2 commit
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
clean checkout can rebuild the exact GASAL2 bridge
```

Stop if:

```text
any result depends on a machine-local GASAL2 binary or untracked GASAL2 source
```

### Phase 1: Scoped Product Decision

Goal:

```text
Decide whether Path A is allowed to count as goal completion.
```

Do:

```text
present the scoped product contract
state claims and non-claims next to each other
record explicit user acceptance before using Path A
keep scoped features default-off unless separately accepted
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase1-scoped-product
make check-fasim-gasal2-roadmap-path-a-scoped-acceptance
```

Advance to Path A only when:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

Stop Path A if:

```text
the user still wants the original broad scoreInfo/preAlign/Align goal
```

### Phase 2: Full-Output Equivalence Baseline

Goal:

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
restored rows/digest remain clean and timing is itemized
```

Stop if:

```text
rows, digest, ordering contract, or restored output semantics drift
```

### Phase 3: Pre-Convert CPU Reduction

Goal:

```text
Reduce CPU materialization/convert work without changing the complete row set.
```

Do:

```text
test only proof-first reducers
prove missing_rows = 0 and extra_rows = 0 before performance claims
prove task-local frontier safety
keep failed reducers default-off and documented as stopped
```

Gate for any future reducer:

```text
missing_rows = 0
extra_rows = 0
task_frontier_safety = safe
real_prune_proof_gate = pass
chr22 and chr1 convert wall lower than Phase 2
```

Advance when:

```text
a reducer preserves the full row set and beats the Phase 2 convert baseline
```

Stop if:

```text
the reducer only preserves top5, changes the full row set, or reduces work
without improving wall time
```

### Phase 4: Sort/Top-N Optimization

Goal:

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

Advance when:

```text
sort/filter is measured as a real bottleneck and the optimized path is exact
```

Stop if:

```text
partial selection changes row identity, tie behavior, or top-N boundary
```

### Phase 5: Archive Artifact

Goal:

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

Gate:

```bash
make check-fasim-gasal2-roadmap-phase5-archive-artifact
make check-fasim-gasal2-archive-manifest-parser
make check-fasim-tfo-archive-integrity-parser
```

Advance when:

```text
the archive restores the claimed output without rerunning Fasim
```

Stop if:

```text
the archive omits reference identity or data required to restore TFOsorted
```

### Phase 6: Workload Matrix

Goal:

```text
Make every claim explicit and prevent scoped evidence from becoming broad
evidence by accident.
```

Do:

```text
record every claimed workload in docs/fasim_gasal2_workload_matrix.tsv
separate scoped, broad, blocked, fallback-heavy, and unclaimed rows
add contract=broad_replacement only after Phase 7 broad gates pass
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
at least one claimed broad_replacement row exists
row_equal = true
digest_match = true
speedup > 1.0
fallbacks = 0 for the claimed GPU path
scoreinfo_reduced = true
align_side_reduced = true
```

Stop if:

```text
a fallback-heavy, output-drift, or top5-only row is presented as broad clean
```

### Phase 7: Broad Replacement Restart

Goal:

```text
Complete the original broad objective if Path A is not accepted.
```

Current active design:

```text
Post-v5.3 consumer summary:
  CUDA emits compact legacy-byte attempt descriptors before CPU scoreInfo rows
  GPU reduces scoreInfo-local candidate summaries before host transfer
  CPU aligner.Align() replays selected attempts as authority
  GPU does not own endpoint, CIGAR, traceback, output, or digest
```

Already recorded gates:

```text
Gate v5.1:
  true pre-scoreInfo descriptor source first1 smoke passed

Gate v5.2:
  CPU-authority replay first1 smoke passed
  full_rows_equal = true
  digest_match = true
  candidate_align_attempts < reference_align_attempts

Gate v5.3:
  first64 CPU-authority replay was correctness-clean but performance no-go
  missing_required_attempts > 0
  do not continue this host-visible replay shape as broad completion

Gate v5.5 first attempt:
  first_descriptor_per_scoreInfo reduced attempts
  external output comparison failed
  first_descriptor_per_scoreInfo is stopped

Gate v5.5 fixed-prefix attempt:
  prefix 1/2/3 reduced GPU-selected attempts but changed output
  prefix 4/5 preserved output but did not reduce GPU-selected attempts
  fixed-prefix consumer summary is stopped
```

Next gate:

```text
pre_d2h_output_inert_proof_search_first1_export
```

Do:

```text
do not continue the fixed-prefix consumer-summary path
do not run first64 from the failed fixed-prefix probe
do not implement the current stronger task-frontier runtime without a new proof
export first1 proof-search rows from pre-D2H descriptor fields
join CPU-authority labels only for offline discovery
keep runtime_reduction_enabled = 0
```

Recommended commands:

```bash
make build-fasim-gasal2
make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-consumer-summary-design
make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-consumer-summary-prefix-no-go
make check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-design
make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-task-frontier-certificate-feasibility-no-go
make check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-design
```

Gate v5.6 task-frontier first1 passes only if:

```text
uses_task_frontier_certificate = 1
uses_prefix_boundary_only = 0
arbitrary_sparse_subset = 0
first_descriptor_per_scoreInfo = 0
fixed_prefix_per_scoreInfo = 0
external_full_rows_equal = 1
external_digest_match = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
gpu_selected_attempts < v5_candidate_align_attempts
candidate_align_attempts < reference_align_attempts
fallback_accounting_clean = true
cpu_align_authority = true
gpu_endpoint_cigar_traceback_output_authority = false
```

If Gate v5.6 task-frontier first1 passes:

```text
write a first1 pass checkpoint
run Gate v5.7 first64 broad characterization
```

Gate v5.7 first64 passes only if:

```text
external_full_rows_equal = 1
external_digest_match = 1
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
fallback_accounting_clean = true
cpu_align_authority = true
gpu_endpoint_cigar_traceback_output_authority = false
```

If Gate v5.7 passes:

```text
add exactly one contract=broad_replacement row to the workload matrix
advance to Phase 8
```

If Gate v5.6 or v5.7 fails:

```text
write a no-go checkpoint for this architecture
keep broad_objective_status = open
choose a genuinely different Phase 7 architecture or ask whether Path A
scoped completion is acceptable
```

Forbidden in Phase 7:

```text
GPU endpoint authority
GPU CIGAR/traceback authority
GASAL2 output/digest authority
claiming broad completion from top5-only equality
claiming broad completion from archive-only output delivery
claiming broad completion from first1-only evidence
```

### Phase 8: Completion Decision

Goal:

```text
Make the final completion decision after evidence gates, not before.
```

Path A may close the goal only if:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
Phase 0 gate passes
Phase 1 gate passes
Phase 5 gate passes
Phase 6 scoped matrix gate passes
Phase 8 decision records scoped completion
```

Path B may close the goal only if:

```text
Phase 0 gate passes
Phase 2 output baseline remains clean
Phase 6 has a passing broad_replacement row
Phase 7 broad gate passes
Phase 8 decision records broad completion
```

Completion command sequence:

```bash
make check-fasim-gasal2-roadmap-current-state
make check-fasim-gasal2-roadmap-phase8-completion-decision
```

Close only when the Phase 8 result says:

```text
goal_completion_status = complete
must_not_call_update_goal_complete = 0
```

Otherwise keep:

```text
goal_completion_status = not_complete
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Immediate Next Steps

Execute only one gate at a time.

```text
1. Keep Phase 0 reproducibility green.
2. Keep Phase 2 output baseline green.
3. Run Phase 7 Gate v5.3 first64 characterization.
4. If v5.3 passes, update Phase 6 with one broad_replacement row.
5. If v5.3 fails, document the no-go and do not close the goal.
6. Run Phase 8 only after Path A acceptance or a passing Path B broad row.
```
