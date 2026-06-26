# Fasim GASAL2 Phase 7 Post-v5.3 New Pre-D2H Proof Family Or Scope Decision

This checkpoint defines the only valid next move after the first1 pre-D2H
proof-search export failed the proof-acceptance audit. It does not add a
runtime path and does not complete the active goal.

## Scope

```text
phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision = defined
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1.md
previous_status = first1_no_accepted_proof
path_a_user_acceptance_required = 1
path_b_new_pre_d2h_proof_family_required = 1
runtime_reduction_enabled = 0
first64_runtime_allowed = 0
gpu_endpoint_cigar_traceback_output_authority = 0
gpu_output_authority = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The previous proof-search export is evidence, not a reducing proof. It records
aggregate first1 telemetry, but it does not prove which skipped work is
output-inert before host transfer.

## Path A Decision

Path A can close only if the user explicitly accepts the scoped product:

```text
path_a_user_acceptance_required = 1
scoped_product_can_close_without_user_acceptance = 0
```

The scoped product may package the short-query/top5 artifact, MEG3-like grouped
tiny-region workflow, and archive-first restored output where claimed. It still
does not become a broad aligner or universal scoreInfo/preAlign replacement.

## Path B Requirement

If the original broad goal remains active, the next Path B design must be a new
pre-D2H proof family. The first1 gate for that family must prove:

```text
candidate_proof_false_negatives = 0
candidate_proof_missing_required_attempts = 0
candidate_selected_attempts < v5_candidate_align_attempts
candidate_selected_attempts < reference_align_attempts
candidate_uses_final_cpu_output_as_runtime_proof = 0
source_is_pre_scoreinfo = 1
source_is_legacy_byte_cuda = 1
CPU aligner.Align() authority = 1
```

The proof may use CPU-authority output as an offline label for validation, but
it must not depend on final CPU output at runtime to decide which work to skip.

## Forbidden

```text
runtime reduction = forbidden
first64 runtime = forbidden
broad_replacement workload matrix promotion = forbidden
do_not_reuse_failed_proof_search_aggregate_export = 1
do_not_use_final_cpu_output_as_runtime_proof = 1
```

This checkpoint also continues to forbid GPU endpoint, CIGAR, traceback,
output, or digest authority. CPU `aligner.Align()` remains the semantic
authority until a separate equivalence proof changes that contract.

## Decision

```text
current_execution_gate = implement_new_pre_d2h_proof_family_first1_smoke_or_path_a_acceptance
current_next_pr = fasim_new_pre_d2h_proof_family_first1_smoke_or_scope_acceptance
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The next turn can either implement a new proof-family first1 smoke or record an
explicit Path A scoped-acceptance decision. It must not write a reducing runtime
from the current proof-search export.
