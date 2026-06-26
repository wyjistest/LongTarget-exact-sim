# Fasim GASAL2 Goal Completion Action Roadmap

This document is the single-page execution roadmap for making the active
Fasim/GASAL2 goal closable. It is a plan, not a completion claim.

The active broad replacement objective remains open, but the active goal is
closable through the user-accepted Path A scoped product contract:

```text
Use GASAL2/GPU to materially accelerate or replace the scoreInfo/preAlign /
Align-related Fasim path while preserving the required output contract.

broad_objective_status = open
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
active_goal_completion_status = complete_scoped_path_a
completion_guard_cleared = 1
must_not_call_update_goal_complete = 0
```

## Authority Contract

These invariants apply until a separate equivalence proof changes them:

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
shadow-only telemetry
fallback-heavy GPU coverage
first64 evidence after a failed first1 gate
any stopped v3/v4/v5/GASAL2-align/native-DP/upper-bound family
```

## Close Paths

There are only two valid ways to close the active goal.

```text
Path A - scoped product completion
  Valid only if the user explicitly accepts a narrowed deliverable.

  Allowed scope:
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

  Required proof:
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

The current path is Path A scoped completion. The user explicitly accepted the
narrowed Path A contract.

```text
current_phase = Phase 8
current_gate = phase8_path_a_scoped_completion_accepted
current_execution_gate = phase8_path_a_scoped_completion_accepted
current_next_pr = none_goal_complete_scoped_path_a
current_gate_document = docs/fasim_gasal2_path_a_scoped_completion_acceptance.md
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

Historical pre-Path-A-acceptance cursor:

```text
current_gate = user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go
current_execution_gate = user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go
current_next_pr = none_until_user_scope_acceptance_or_external_path_b_design_input
current_gate_document = docs/fasim_gasal2_path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go.md
```

Historical post-exact-work-unit-external-design-choice cursor:

```text
current_gate = path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go
current_execution_gate = path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go
current_gate_document = docs/fasim_gasal2_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go.md
```

Historical post-exact-work-unit-new-design-spec cursor:

```text
current_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
current_execution_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
current_next_pr = fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
current_gate_document = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go.md
```

Historical post-exact-work-unit-consumer fork cursor:

```text
current_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
current_execution_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go.md
```

Historical pre-exact-work-unit-consumer cursor:

```text
current_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go
current_execution_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go
current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold.md
```

Historical pre-exact-work-unit-shadow cursor:

```text
current_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md
```

The most recently stopped design family is:

```text
design_family = gpu_exact_work_unit_compaction_replay
path_b_gpu_exact_work_unit_compaction_family_stopped = 1
```

Its intent is narrow:

```text
GPU helps form exact input-equivalence keys for legacy scoreInfo/preAlign and
Align work units.

CPU authority computes the semantic result once per exact class.

Ordered CPU replay expands duplicates.

GPU does not score, accept/reject, produce endpoint, produce CIGAR, emit output,
or change digest.
```

## Phase Summary

| Phase | Job | Exit Gate | Close Role |
| --- | --- | --- | --- |
| 0 | Reproducibility | Clean checkout rebuilds patched GASAL2/Fasim bridge | Required for both paths |
| 1 | Scope decision | User explicitly accepts Path A if used | Required for Path A |
| 2 | Full-output baseline | Restored rows and digest match CPU authority | Required foundation |
| 3 | CPU output-side reduction | Complete rows preserved and CPU wall improves | Optional helper |
| 4 | Sort/top-N reduction | Sort/filter is dominant and exact behavior is preserved | Optional helper |
| 5 | Archive artifact | Archive restores claimed output exactly | Required for archive claims |
| 6 | Workload matrix | Claims are labelled correctly | Required claim ledger |
| 7 | Broad GPU path | Equality, speedup, and CPU-work reduction pass | Required for Path B |
| 8 | Close decision | Path A accepted or Path B proven | Only close phase |

## Phase 0 - Reproducibility

Do:

```text
pin GASAL2 upstream commit
track local GASAL2 patches
keep setup/build targets idempotent
record CUDA version, SM arch, GASAL2_MAX_QUERY_LEN, and GASAL2_N_CODE
remove reliance on untracked .tmp/GASAL2 source edits or local binaries
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

Do:

```text
present scoped claims and non-claims together
ask whether Path A scoped completion is acceptable
record explicit user acceptance before using Path A
keep scoped features default-off unless separately accepted
```

Path A can close only when:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

If the user still wants the original broad objective, continue Path B.

## Phase 2 - Full-Output Baseline

Do:

```text
preserve complete row-set equality
preserve digest equality
itemize convert/output wall time
itemize whole-run wall time
separate full-output evidence from top5-only evidence
```

Advance when:

```text
restored_rows_equal = 1
restored_digest_match = 1
convert_and_run_timing_itemized = 1
```

Stop if row identity, ordering, digest, or restore semantics drift.

## Phase 3 - CPU Output-Side Reduction

Do:

```text
test only proof-first reducers
prove missing_rows = 0 before speed claims
prove extra_rows = 0 before speed claims
compare against the Phase 2 full-output baseline
keep row-safe-but-slower reducers default-off
```

Advance only when:

```text
missing_rows = 0
extra_rows = 0
digest_match = 1
convert_wall_seconds < Phase_2_convert_wall_seconds
```

Stop if the reducer preserves only top5, changes complete rows, depends on
final CPU output membership as runtime proof, or is clean but slower.

## Phase 4 - Sort/Top-N Reduction

Do this only after profiling proves sort/filter is material.

Advance only when:

```text
sort_or_filter_is_dominant = 1
same comparator behavior = 1
same tie behavior = 1
same selected rows and order = 1
sort_filter_wall_seconds improves
```

If triplex materialization, output write, scoreInfo/preAlign, or Align-side
work remains dominant, skip this phase.

## Phase 5 - Archive Artifact

Do:

```text
record archive schema version
record reference digests
validate archive manifest integrity
validate restored row equality
validate restored digest equality
keep archive delivery separate from broad runtime replacement
```

Advance when:

```text
archive_manifest_valid = 1
archive_restore_rows_equal = 1
archive_restore_digest_match = 1
```

Stop if restore depends on hidden local files or archive evidence is used by
itself as broad runtime replacement.

## Phase 6 - Workload Matrix

Do:

```text
label every row as claimed, unclaimed, blocked, fallback-heavy, or broad_replacement
ensure scoped claimed rows have passing scoped contracts
add broad_replacement only after Phase 7 broad gates pass
keep fallback-heavy rows out of GPU-fast-path claims
```

Path B rows must have:

```text
contract = broad_replacement
full_rows_equal = true
digest_match = true
speedup > 1.0
fallback_accounting_clean = true
scoreinfo_reduced = true
align_side_reduced = true
```

## Phase 7 - Broad GPU Path

This phase is the only Path B route to broad completion.

Stopped families:

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
GPU exact work-unit compaction path
```

Current allowed family:

```text
none until Path A is explicitly accepted or a genuinely different Path B GPU
execution design family is defined
```

### Phase 7.1 - Exact Work-Unit Compaction First1 Shadow

Status:

```text
phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold = fail_closed_shadow
phase7_gpu_exact_work_unit_compaction_gate_first1_shadow_pass = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
```

Checkpoint:

```text
docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold.md
```

Do:

```text
add default-off fail-closed telemetry
collect scoreInfo/preAlign exact-key descriptors
collect Align exact-key descriptors
report unique and duplicate key counts
validate CPU recomputed keys
fallback to full CPU replay
keep CPU aligner.Align() authority
keep runtime reduction disabled
keep work drop disabled
keep first64 disabled
```

Required telemetry:

```text
requested = 1
active = 1
scoreinfo_key_descriptors > 0
scoreinfo_unique_keys
scoreinfo_duplicate_units
align_key_descriptors > 0
align_unique_keys
align_duplicate_attempts
key_collisions = 0
cpu_key_validation_mismatches = 0
unsupported_key_descriptors
fallback_to_full_cpu_replay = 1
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
full_rows_equal = 1
digest_match = 1
gate_first1_shadow_pass = 1
```

Pass only if:

```text
requested = 1
active = 1
scoreinfo_key_descriptors > 0
align_key_descriptors > 0
key_collisions = 0
cpu_key_validation_mismatches = 0
full_rows_equal = 1
digest_match = 1
scoreinfo_prealign_reduced = 0
align_side_reduced = 0
```

This phase does not reduce runtime work. It only proves that descriptor
telemetry exists and that the fail-closed CPU authority path is unchanged.

### Phase 7.2 - Exact Work-Unit Compaction Consumer Or No-Go

Status:

```text
phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go = recorded
phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_status = no_go_no_duplicate_work
accepted_exact_work_unit_compaction_consumer = 0
accepted_exact_work_unit_compaction_reduction = 0
path_b_gpu_exact_work_unit_compaction_family_stopped = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first64_runtime_allowed = 0
```

Checkpoint:

```text
docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go.md
```

Decision evidence:

```text
scoreinfo_duplicate_units = 0
align_duplicate_attempts = 0
key collisions = 0
cpu_key_validation_mismatches = 0
fallback to full CPU replay exists for unsupported work
full_rows_equal = 1
digest_match = 1
```

This stops the current exact work-unit compaction family because there is no
non-trivial duplicate work to consume into either required CPU path.

Next gate:

```text
path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
```

### Phase 7.2b - Post Exact Work-Unit Fork

Status:

```text
path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go = recorded
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_different_gpu_execution_design_after_exact_work_unit_compaction_no_go_status = required_not_defined
path_b_new_design_family_after_exact_work_unit_compaction_no_go = undefined
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
```

Checkpoint:

```text
docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go.md
```

Next gate:

```text
new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
```

### Phase 7.2c - New Design Spec Or Path A Acceptance Decision

Status:

```text
new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go = recorded
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_new_design_family_after_exact_work_unit_compaction_no_go = undefined
path_b_no_viable_new_design_family_after_exact_work_unit_compaction_no_go = 1
path_b_external_design_input_required_after_exact_work_unit_compaction_no_go = 1
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed_without_new_design_input = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
```

Checkpoint:

```text
docs/fasim_gasal2_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go.md
```

Next gate:

```text
path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go
```

### Phase 7.2d - Input Required Stop-Before-Guessing Gate

Status:

```text
path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go = recorded
path_a_user_acceptance_recorded = 0
path_a_scoped_completion_may_close_goal = 0
path_b_external_design_input_received = 0
path_b_new_design_family_after_exact_work_unit_compaction_no_go = undefined
path_b_no_viable_new_design_family_after_exact_work_unit_compaction_no_go = 1
path_b_external_design_input_required_after_exact_work_unit_compaction_no_go = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
```

Checkpoint:

```text
docs/fasim_gasal2_path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go.md
```

Next gate:

```text
user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go
```

### Phase 7.3 - First1 Reducing Runtime

Forbidden because Phase 7.2 through Phase 7.2d did not produce a reducing
runtime, a Path A acceptance, or a new Path B design family.

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

Forbidden until Phase 7.3 passes.

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

Forbidden until Phase 7.4 passes.

Do:

```text
add one broad_replacement workload matrix row for each passing workload
record workload name, row equality, digest, speedup, fallback accounting,
scoreInfo/preAlign reduction, Align-side reduction, and CPU authority status
```

Do not promote shadow-only, top5-only, archive-only, fallback-heavy, or
output-drift rows.

## Phase 8 - Completion Decision

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

Only then may a close packet clear the no-completion guard and contain a
completion status:

```text
completion_guard_cleared = 1
goal_completion_status = complete
```

Current Path A close packet:

```text
broad_objective_status = open
scoped_product_status = accepted
active_goal_completion_status = complete_scoped_path_a
scope_or_broad_design_decision_required = 0
path_a_user_acceptance_required = 0
path_b_new_broad_architecture_required = 0
must_not_call_update_goal_complete = 0
```

## Execution Rule

When continuing the active goal:

```text
1. Start at Current Cursor.
2. Execute only the next gate.
3. Verify the gate with a dedicated checker or runtime smoke.
4. If the gate passes, update the cursor to the next phase.
5. If the gate no-goes, stop that family and choose Path A acceptance or a
   genuinely different Path B design family.
6. Do not skip from first1 to first64.
7. Do not mark the active goal complete until Phase 8 passes.
```
