# Fasim GASAL2 Goal Completion Stepwise Plan

This document is the execution-facing plan for getting the active GASAL2/Fasim
goal to a real close. It is not a success claim.

The current broad objective remains open:

```text
Use GASAL2/GPU to materially accelerate or replace the scoreInfo/preAlign /
Align-related Fasim path while preserving the required output contract.
```

The goal can close only in Phase 8. Until then:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Current Cursor

```text
current_path:
  Path B remains active unless the user explicitly accepts Path A.

current_phase:
  Phase 7 - post-v5.3 broad restart

current_completed_gate:
  post-v5.3 host-assisted consumer feasibility no-go checkpoint

current_v5_3_result:
  digest_match = 1
  full_rows_equal = 1
  candidate_wall_seconds = 124.399845
  baseline_wall_seconds = 87.827405
  candidate_vs_baseline = 0.706009
  missing_required_attempts = 624
  fallback_accounting_clean = 0

current_decision:
  v5 descriptor replay is correctness-clean at final output, but performance
  and accounting are no-go. The host-assisted consumer feasibility preflight
  also failed for NEAT1 first1 because GASAL2 score-only selection hit the
  long-query length guard and selected zero attempts.

next_valid_work:
  implement the first1 pre-D2H proof-search export in
  docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md
  or ask whether Path A scoped completion is acceptable.

next_runtime_gate:
  pre_d2h_output_inert_proof_search_first1_export

next_runtime_env:
  FASIM_GASAL2_PHASE7_POST_V5_3_PRE_D2H_PROOF_SEARCH=1

recommended_preflight:
  none; the next step is a diagnostic export, not a reducing runtime

recommended_preflight_status:
  host-assisted GASAL2 score-only feasibility and current consumer-summary
  shapes are already no-go; do not retry them as the next gate.
```

## Completion Paths

There are only two valid ways to close the active goal.

```text
Path A: scoped completion
  Allowed only if the user explicitly accepts the narrowed deliverable:
    short-query/H19 top5 GASAL2 artifact
    MEG3-like grouped tiny-region workflow where claimed
    archive-first restored output where claimed

  Non-claims:
    not aligner.Align replacement
    not universal scoreInfo/preAlign replacement
    not long-query NEAT1/MALAT1 broad replacement
    not GPU endpoint/CIGAR/traceback/output/digest authority

Path B: broad completion
  Required if the original broad goal remains active.

  Required proof:
    full row-set/digest equality for the claimed workload
    runtime win over CPU authority
    scoreInfo/preAlign work reduced or replaced
    Align-side work reduced or replaced
    fallback accounting clean
    CPU aligner.Align() remains semantic authority unless separately proven
```

Do not mix these paths. Top5-only speedup, archive compression, output-drift
speedup, and fallback-heavy results are milestones only; they do not close the
broad objective.

## Invariants

Every phase must preserve these rules:

```text
CPU aligner.Align() remains score/endpoint/traceback/CIGAR/output authority.
GASAL2/GPU endpoint authority = 0
GASAL2/GPU CIGAR authority = 0
GASAL2/GPU traceback authority = 0
GASAL2/GPU output authority = 0
GASAL2/GPU digest authority = 0

No default runtime behavior changes before a separate opt-in gate.
No broad_replacement workload-matrix row before a broad gate passes.
No output drift can be counted as performance success.
No stopped v3/v4/v5 source can be retried as-is as a broad completion path.
```

## Phase Map

| Phase | Job | Exit Gate | Current Status |
| --- | --- | --- | --- |
| 0 | Reproducibility | Clean checkout can rebuild exact GASAL2/Fasim bridge | Maintain green |
| 1 | Scoped decision | User explicitly accepts Path A if used | Not accepted |
| 2 | Full-output baseline | Restored full output remains row/digest clean | Maintain green |
| 3 | Workload ledger | Every claim is scoped, broad, blocked, or fallback-heavy | Maintain green |
| 4 | Post-v5.3 architecture | Different GPU execution design is defined | Long-query-safe design exists |
| 5 | Consumer-summary first1 gate | Host-assisted feasibility may de-risk the reducer; GPU-side first1 must prove equality and real pre-host reduction | Next gate |
| 6 | First64 broad gate | Equality, speedup, and both CPU-work reductions pass | Not run |
| 7 | Scale and promotion | Passing broad row enters workload matrix | Blocked by Phase 6 |
| 8 | Completion decision | Path A accepted or Path B broad gate passes | Not complete |

## Advancement Rules

Use this document as the phase cursor:

```text
Only advance one gate at a time.
Keep failed gates as stop checkpoints.
Do not re-label scoped/top5/archive evidence as broad evidence.
Do not mark the active goal complete before Phase 8.
```

Every implementation PR must state:

```text
current_phase
gate_being_attempted
default-off env, if any
authority boundary
expected telemetry
pass criteria
stop criteria
next phase if pass
next action if fail
```

For Path B, a gate is allowed to advance only if:

```text
full_rows_equal = 1
digest_match = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

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

Advance when:

```text
clean checkout can rebuild the exact GASAL2 bridge and runtime binary
```

Stop if:

```text
any claimed result depends on a machine-local GASAL2 binary or untracked
GASAL2 source edit
```

## Phase 1: Scoped Decision

Purpose:

```text
Decide whether Path A is allowed to count as goal completion.
```

Do:

```text
present the scoped product claims and non-claims together
record explicit user acceptance before using Path A
keep scoped acceleration default-off unless separately accepted
do not call scoped evidence broad replacement evidence
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

Current decision:

```text
The user still wants to pursue the original broad objective.
Path A cannot close the goal unless the user later explicitly accepts it.
```

## Phase 2: Full-Output Baseline

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

Advance when:

```text
restored rows/digest remain clean and timing is itemized
```

Stop if:

```text
rows, digest, ordering contract, or restored output semantics drift
```

## Phase 3: Workload Ledger

Purpose:

```text
Prevent scoped evidence from becoming broad evidence by accident.
```

Do:

```text
update docs/fasim_gasal2_workload_matrix.tsv after every new claim
mark rows as scoped, broad, fallback-heavy, blocked, or unclaimed
record exact workload, command, runtime, equality, fallback, and authority
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase6-workload-matrix
```

Broad row requirements:

```text
contract = broad_replacement
row_equal = true
digest_match = true
speedup > 1.0
fallback_accounting_clean = true
scoreinfo_reduced = true
align_side_reduced = true
cpu_align_authority = true
gpu_endpoint_cigar_traceback_output_authority = false
```

Stop if:

```text
any fallback-heavy, output-drift, top5-only, or archive-only row is presented
as broad clean
```

## Phase 4: Post-v5.3 Architecture

Purpose:

```text
Define a Path B architecture that is materially different from v5 descriptor
replay.
```

Current design:

```text
document:
  docs/fasim_gasal2_phase7_post_v5_3_new_architecture_design.md

design_family:
  gpu_resident_scoreinfo_consumer_summary_with_cpu_authority_replay

required difference from v5:
  no full host-visible scoreInfo row stream
  no full descriptor replay as the main output
  GPU consumes/reduces scoreInfo-local candidates before host transfer
  host receives compact task consumer summaries plus selected CPU replay attempts
```

Gate:

```bash
make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-architecture-design
```

Advance when:

```text
phase7_post_v5_3_new_architecture_may_implement = 1
phase7_post_v5_3_new_architecture_may_claim_completion = 0
next_required_gate = post_v5_3_gpu_consumer_summary_first1_smoke
```

Stop if:

```text
the implementation repeats v5 host-visible descriptor replay
the implementation depends on GASAL2 score-only selection for NEAT1-like long queries
the implementation needs GPU endpoint/CIGAR/traceback/output authority
the implementation cannot explain how it reduces before host transfer
```

## Phase 5: Consumer Summary First1 Runtime Gate

Purpose:

```text
Prove the new post-v5.3 architecture is real on a first1 workload before
running broader tests.
```

Step 5.0, recommended preflight:

```text
Add a diagnostic host-assisted consumer feasibility path:
  FASIM_GASAL2_PHASE7_POST_V5_3_HOST_ASSISTED_CONSUMER_FEASIBILITY=1

Use v5 CUDA descriptors as the source.
Use GASAL2 score-only results to choose candidate attempts.
For each selected attempt, include the scoreInfo-local prefix required by CPU
  replay semantics.
Replay CPU aligner.Align() only on that prefix-selected descriptor subset.
Compare full rows and digest against CPU authority.
Report that this is host-assisted and that GPU pre-host reduction is still 0.
```

Step 5.0 telemetry:

```text
requested
active
host_assisted = 1
source_is_v5_descriptors = 1
gpu_consumer_reduces_before_host_transfer = 0
reference_align_attempts
v5_candidate_align_attempts
host_selected_attempts
prefix_descriptor_attempts
candidate_align_attempts
candidate_align_attempts_less_than_v5
descriptor_false_negatives
missing_required_attempts
fallback_accounting_clean
digest_match
full_rows_equal
missing_rows
extra_rows
triplex_mismatches
cpu_align_authority
gpu_endpoint_cigar_traceback_output_authority
```

Step 5.0 may continue to Step 5.1 only if:

```text
full_rows_equal = 1
digest_match = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_align_attempts < v5_candidate_align_attempts
descriptor_false_negatives = 0
missing_required_attempts = 0
fallback_accounting_clean = 1
```

Step 5.0 cannot complete Phase 5 because:

```text
gpu_consumer_reduces_before_host_transfer = 0
```

Step 5.1, strict GPU-side runtime gate:

```text
add default-off runtime env:
  FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1

add fail-closed CPU-only behavior when the path is unsupported
emit itemized telemetry
keep CPU aligner.Align() as replay/output authority
compare full rows and digest against CPU baseline
move the scoreInfo-local consumer summary onto GPU before host transfer
```

Required telemetry:

```text
requested
active
source_is_pre_scoreinfo
gpu_scoreinfo_tasks
gpu_consumer_summary_rows
gpu_consumer_reduces_before_host_transfer
gpu_selected_attempts
reference_align_attempts
candidate_align_attempts
v5_candidate_align_attempts
scoreinfo_prealign_reduced
align_side_reduced
descriptor_false_negatives
missing_required_attempts
fallback_accounting_clean
cpu_replay_seconds
candidate_wall_seconds
baseline_wall_seconds
candidate_vs_baseline
digest_match
full_rows_equal
missing_rows
extra_rows
triplex_mismatches
cpu_align_authority
gpu_endpoint_cigar_traceback_output_authority
```

First1 pass gate:

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
gpu_consumer_summary_rows > 0
gpu_consumer_reduces_before_host_transfer = 1
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
```

Advance when:

```text
post_v5_3_gpu_consumer_summary_first1_smoke = pass
```

Stop if:

```text
first1 rows differ
gpu_selected_attempts >= v5_candidate_align_attempts
missing_required_attempts > 0
descriptor_false_negatives > 0
fallback_accounting_clean = 0
the path falls back to v5 descriptor replay
```

## Phase 6: First64 Broad Gate

Purpose:

```text
Decide whether the post-v5.3 architecture is a real broad candidate.
```

Run only after Phase 5 passes.

Do:

```text
run baseline CPU authority and candidate on the same first64-equivalent broad workload
compare full output rows, digest, missing rows, extra rows, and triplex rows
compare candidate wall time against CPU baseline
measure scoreInfo/preAlign-side reduction
measure Align-side reduction
verify fallback accounting
```

Pass gate:

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

Advance when:

```text
post_v5_3_gpu_consumer_summary_first64_broad_gate = pass
```

Stop if:

```text
correctness changes
candidate wall is slower or near parity
scoreInfo/preAlign work is not reduced
Align-side work is not reduced
fallback accounting is not clean
the implementation requires GPU endpoint/CIGAR/traceback/output authority
```

Failure action:

```text
write a no-go checkpoint for this architecture
do not add broad_replacement to the workload matrix
choose a new materially different architecture or return to Path A scoped decision
```

## Phase 7: Scale And Promotion

Purpose:

```text
Promote only evidence that passed Phase 6 into a claimed broad workload.
```

Run only after Phase 6 passes.

Do:

```text
repeat the passing gate on at least one larger claimed workload
record workload size, query, target, command, runtime, equality, and fallback
record GPU/CPU breakdown where available
add exactly one contract=broad_replacement row to the workload matrix
keep runtime default-off unless a separate production-policy PR is approved
```

Promotion gate:

```text
claimed_broad_replacement_rows > 0
row_equal = true
digest_match = true
speedup > 1.0
fallback_accounting_clean = true
scoreinfo_reduced = true
align_side_reduced = true
cpu_align_authority = true
```

Stop if:

```text
the result only passes first1
the result only passes top5
the result is fallback-heavy
the result depends on output drift
the result cannot be reproduced from Phase 0 setup
```

## Phase 8: Completion Decision

Purpose:

```text
Close the active goal only after one explicit path passes.
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

Path A may close only if:

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

Path B may close only if:

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

## Immediate Next PR

If the user continues Path B, the next PR should be:

```text
Title:
  fasim: export pre-D2H output-inert proof-search data

Goal:
  Implement the default-off first1 diagnostic export from
  docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md.
  It must not reduce runtime yet.

Must prove:
  proof_search_rows > 0
  source_is_pre_scoreinfo = 1
  source_is_legacy_byte_cuda = 1
  runtime_reduction_enabled = 0
  CPU aligner.Align() remains output authority
  CPU labels are used only for offline proof discovery

Must not do:
  no real default change
  no claim that a reducing Phase 7 runtime has passed
  no current stronger task-frontier runtime without a new proof
  no runtime reduction in the proof-search export
  no GPU endpoint authority
  no GPU CIGAR/traceback
  no GPU output/digest authority
  no broad_replacement matrix promotion
  no retry of v5 descriptor replay as the main architecture
  no retry of host-assisted GASAL2 score-only selection as the main architecture
```

If a new first1 smoke passes, the next PR is first64 broad characterization.
If no new proof exists, write a no-go checkpoint and keep the broad objective
open.
