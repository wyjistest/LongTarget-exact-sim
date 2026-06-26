# Fasim GASAL2 Direct Goal Completion Phase Roadmap

This is the direct phase roadmap for making the active Fasim/GASAL2 goal
closable. It is a plan, not a completion claim.

The active broad goal is still open:

```text
Use GASAL2/GPU to materially accelerate or replace the scoreInfo/preAlign /
Align-related Fasim path while preserving the required output contract.

broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Non-Negotiable Contract

Until a separate equivalence proof changes the contract:

```text
CPU aligner.Align() authority = 1
GPU score authority = 0
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
default behavior unchanged = 1
```

Do not close the broad goal from:

```text
top5-only evidence
archive-only evidence
output-drift speedup
fallback-heavy GPU coverage
shadow-only telemetry
first64 from a failed first1 gate
stopped v3/v4/v5/native-DP/GASAL2-align families
```

## Completion Paths

There are only two valid close paths.

```text
Path A - scoped product completion
  Valid only if the user explicitly accepts the narrowed deliverable.

  Scope:
    short-query/H19 top5 GASAL2 artifact
    MEG3-like complete-record grouping where claimed
    archive-first restored output where claimed

  Non-claims:
    no aligner.Align() replacement
    no universal scoreInfo/preAlign replacement
    no long-query NEAT1/MALAT1 broad replacement
    no GPU endpoint/CIGAR/traceback/output/digest authority

Path B - broad objective completion
  Required while the original broad goal remains active.

  Must prove on a claimed broad workload:
    full_rows_equal = 1
    digest_match = 1
    missing_rows = 0
    extra_rows = 0
    triplex_mismatches = 0
    candidate_wall_seconds < baseline_wall_seconds
    candidate_vs_baseline > 1.0
    scoreInfo/preAlign work reduced or replaced = 1
    Align-side work reduced or replaced = 1
    fallback_accounting_clean = 1
```

Do not mix Path A evidence into Path B completion.

## Current Cursor

The current path is Path B unless the user explicitly accepts Path A.

```text
current_phase = Phase 7
current_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
```

Current checkpoint:

```text
current_checkpoint = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md
previous_checkpoint = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go.md
historical_previous_checkpoint = docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go.md
historical_previous_checkpoint = docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold.md
phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold = fail_closed_shadow
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
historical_execution_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go
historical_next_pr = fasim_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go
phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go = recorded
phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_status = no_go_no_rejected_work
path_b_gpu_upper_bound_reject_certificate_family_stopped = 1
path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go = recorded
path_b_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go_status = required_not_defined
path_b_new_design_family_after_gpu_upper_bound_reject_certificate_no_go = undefined
phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance = defined
phase7_gpu_exact_work_unit_compaction_design_spec_status = spec_defined
design_family = gpu_exact_work_unit_compaction_replay
next_valid_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold
```

The immediate work is not a real runtime path. It is a fail-closed first1
shadow for exact work-unit compaction. It may collect key/equivalence
telemetry, but CPU replay remains authoritative and no work may be dropped.

## Phase 0 - Reproducibility

Purpose:

```text
Make every GASAL2/Fasim result rebuildable from a clean checkout.
```

Do:

```text
pin the GASAL2 upstream commit
track local GASAL2 patches
make setup/build targets idempotent
record CUDA version, SM arch, GASAL2_MAX_QUERY_LEN, and GASAL2_N_CODE
remove reliance on untracked .tmp/GASAL2 source edits or local binaries
```

Exit gate:

```text
clean_checkout_rebuilds_gasal2_bridge = 1
```

Commands:

```bash
make check-fasim-gasal2-roadmap-phase0-reproducibility
make setup-gasal2
make build-fasim-gasal2
```

## Phase 1 - Scope Decision

Purpose:

```text
Decide whether Path A scoped completion is acceptable.
```

Do:

```text
present scoped claims and non-claims together
record explicit user acceptance before using Path A
keep scoped features default-off unless separately accepted
```

Path A may advance only when:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

If the user still wants the original broad objective, Path A cannot close the
goal and execution remains on Path B.

## Phase 2 - Full-Output Baseline

Purpose:

```text
Keep restored full output correct before any full-output speed claim.
```

Do:

```text
preserve complete row-set equality
preserve digest equality
itemize convert/output wall time
itemize whole-run wall time
separate full-output evidence from top5-only evidence
```

Exit gate:

```text
restored_rows_equal = 1
restored_digest_match = 1
convert_and_run_timing_itemized = 1
```

Commands:

```bash
make check-fasim-gasal2-roadmap-phase2-equivalence-first-convert
make check-fasim-gasal2-archive-first-output
make check-fasim-gasal2-convert-cpu-breakdown
```

## Phase 3 - CPU Output-Side Reduction

Purpose:

```text
Reduce CPU materialization/convert/output work without changing complete rows.
```

Allowed work:

```text
proof-first reducers
archive-backed restore improvements
row-safe materialization avoidance
```

Exit gate:

```text
missing_rows = 0
extra_rows = 0
digest_match = 1
convert_wall_seconds < Phase_2_convert_wall_seconds
```

Stop if:

```text
the reducer preserves only top5
the reducer changes complete rows
the reducer needs final CPU output membership as runtime proof
the reducer is row-safe but slower
```

## Phase 4 - Sort/Top-N Reduction

Purpose:

```text
Optimize sort/top-N only if profiling proves it is material.
```

Advance only when:

```text
sort_or_filter_is_dominant = 1
same comparator behavior = 1
same tie behavior = 1
same selected rows and order = 1
sort_filter_wall_seconds improves
```

If sort/top-N is not dominant, do not spend phase budget here.

## Phase 5 - Archive Artifact

Purpose:

```text
Store the minimal reference-backed artifact and restore claimed output on demand.
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

```text
archive_manifest_valid = 1
archive_restore_rows_equal = 1
archive_restore_digest_match = 1
```

Commands:

```bash
make check-fasim-gasal2-roadmap-phase5-archive-artifact
make check-fasim-gasal2-archive-manifest-parser
make check-fasim-tfo-archive-integrity-parser
```

## Phase 6 - Workload Matrix

Purpose:

```text
Make every claim explicit and prevent scoped evidence from closing Path B.
```

Do:

```text
label every row as claimed, unclaimed, blocked, fallback-heavy, or broad_replacement
ensure scoped claimed rows have passing scoped contracts
add broad_replacement only after Phase 7 broad gates pass
keep fallback-heavy rows out of GPU-fast-path claims
```

Path B matrix row requirements:

```text
contract = broad_replacement
full_rows_equal = true
digest_match = true
speedup > 1.0
fallback_accounting_clean = true
scoreInfo_prealign_reduced = true
align_side_reduced = true
```

## Phase 7 - Broad GPU Path

Purpose:

```text
Complete the original broad objective if a valid architecture exists.
```

Current stopped families:

```text
current GPU score bridge
GASAL2 direct aligner.Align replacement
v3 seed/index path
v4 source replay path
v5 fused descriptor-source path
post-v5.3 descriptor stream proof path
GPU-owned scoreInfo consumer path
GASAL2 full-align verifier path
native CUDA/Fasim DP path
GPU upper-bound reject certificate path
```

Current allowed family:

```text
design_family = gpu_exact_work_unit_compaction_replay
```

### Phase 7.1 - Upper-Bound Reject First1 Shadow Scaffold

Do:

```text
add default-off fail-closed telemetry
produce only shadow reject-certificate counts
fallback to full CPU replay
keep CPU aligner.Align() authority
keep runtime reduction disabled
keep work drop disabled
keep first64 disabled
```

Required telemetry:

```text
requested
active
upper_bound_descriptors
upper_bound_certificates
reject_candidates_shadow
would_reject_scoreinfo_groups
would_reject_align_attempts
certificate_false_negatives
baseline_rows_in_rejected_groups
baseline_rows_in_rejected_attempts
unsupported_descriptors
fallback_to_full_cpu_replay
scoreinfo_prealign_reduced
align_side_reduced
full_rows_equal
digest_match
runtime_reduction_enabled
runtime_work_drop_enabled
cpu_align_authority
gpu_score_authority
gpu_endpoint_authority
gpu_cigar_traceback_output_authority
gpu_output_digest_authority
gate_first1_shadow_pass
gate_first1_pass
```

Pass only if:

```text
full_rows_equal = 1
digest_match = 1
certificate_false_negatives = 0
baseline_rows_in_rejected_groups = 0
baseline_rows_in_rejected_attempts = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
fallback_to_full_cpu_replay = 1
gate_first1_shadow_pass = 1
gate_first1_pass = 0
```

### Phase 7.2 - Upper-Bound Reject Consumer Or No-Go

Do:

```text
consume the first1 shadow result without enabling runtime reduction
decide whether a pre-drop reject consumer can safely exist
record no-go if certificates are too weak or any false negative appears
```

Advance to a reducing runtime only when:

```text
first1 pre-drop certificate false negatives = 0
first1 rejected work contains no output rows
the consumer decision is available before scoreInfo/preAlign or Align work is dropped
fallback to full CPU replay is available for unsupported descriptors
```

Stop this family if:

```text
certificate coverage is negligible
certificate false negatives appear
rejected groups contain baseline rows
consumer decision is only knowable after CPU output membership
```

### Phase 7.3 - First1 Reducing Runtime

This phase is forbidden until Phase 7.2 passes.

Pass only if:

```text
first1 output bytes equal baseline
missing_rows = 0
extra_rows = 0
digest_match = 1
runtime_reduction_enabled = 1
runtime_work_drop_enabled = 1
scoreInfo/preAlign work reduced or replaced = 1
Align-side work reduced or replaced = 1
candidate_wall_seconds < baseline_wall_seconds
fallback_accounting_clean = 1
```

### Phase 7.4 - First64 Broad Gate

This phase is forbidden until Phase 7.3 passes.

Pass only if:

```text
first64 full_rows_equal = 1
first64 digest_match = 1
first64 missing_rows = 0
first64 extra_rows = 0
first64 candidate_vs_baseline > 1.0
first64 candidate_wall_seconds < baseline_wall_seconds
scoreInfo/preAlign work reduced or replaced = 1
Align-side work reduced or replaced = 1
fallback_accounting_clean = 1
```

### Phase 7.5 - Broad Workload Promotion

This phase is forbidden until Phase 7.4 passes.

Do:

```text
add exactly one broad_replacement workload matrix row for each passing workload
record workload name, row equality, digest, speedup, fallback accounting,
scoreInfo/preAlign reduction, Align-side reduction, and CPU authority status
```

Do not promote:

```text
shadow-only rows
top5-only rows
archive-only rows
fallback-heavy rows
output-drift speedups
```

## Phase 8 - Completion Decision

Purpose:

```text
Close the active goal only after Path A or Path B is actually satisfied.
```

Path A close condition:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
Phase 0 reproducibility gate passes
Phase 5 archive gate passes for archive claims
Phase 6 labels all claims as scoped
no broad replacement claim is made
```

Path B close condition:

```text
at least one Phase 6 broad_replacement row exists
Phase 7 broad gate passes for that row
full_rows_equal = 1
digest_match = 1
candidate_vs_baseline > 1.0
scoreInfo/preAlign work reduced or replaced = 1
Align-side work reduced or replaced = 1
fallback_accounting_clean = 1
CPU authority verification remains available
```

Only then may a completion packet contain:

```text
must_not_call_update_goal_complete = 0
goal_completion_status = complete
```

Until then:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Immediate Next PR

```text
Title:
  fasim: add exact work-unit compaction first1 shadow scaffold

Phase:
  Phase 7 exact-work-unit compaction first1 shadow

Goal:
  Make exact scoreInfo/preAlign and Align work-unit key compaction observable
  without enabling runtime reduction or work drop.

Do:
  consume only docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md
  collect scoreInfo and Align exact-key descriptors
  report unique and duplicate key counts
  validate CPU recomputed keys
  keep runtime work drop disabled
  keep CPU authority replay enabled

Do not:
  no runtime work drop
  no scoreInfo/preAlign reduction
  no Align-side reduction
  no first64
  no GPU endpoint/CIGAR/traceback/output/digest authority
  no default behavior change
```
