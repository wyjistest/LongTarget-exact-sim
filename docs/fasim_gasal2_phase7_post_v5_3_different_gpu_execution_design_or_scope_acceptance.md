# Fasim GASAL2 Phase 7 Post-v5.3 Different GPU Execution Design Or Scope Acceptance

This checkpoint records the design decision after the current pre-D2H
descriptor stream failed to support any accepted proof family. It is not a
runtime implementation and not a completion claim.

## Scope

```text
phase7_post_v5_3_different_gpu_execution_design_or_scope_acceptance = recorded
previous_checkpoint = docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go.md
previous_gate = different_gpu_execution_design_or_path_a_scope_acceptance
runtime_reduction_enabled = 0
first64_runtime_allowed = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The previous feasibility review found:

```text
current_descriptor_stream_can_prove_output_inert_skips = 0
accepted_pre_d2h_proof_families = 0
```

Therefore the next move cannot be a reducing runtime from the current
descriptor stream.

Forbidden carry-forward:

```text
Do not reuse the current PreAlignCudaAttemptDescriptor-only stream.
Do not reuse aggregate proof-search export as runtime proof.
Do not use final CPU output membership as runtime proof.
```

## Designs Reviewed

### Design A: GPU-resident scoreInfo plus conservative skip certificate

This design would keep scoreInfo generation and candidate-attempt filtering on
GPU long enough to emit a conservative certificate for skipped work before D2H.
It would need new certificate inputs that the current descriptor stream does
not provide:

```text
skipped_scoreinfo_score_upper_bound
skipped_attempt_score_upper_bound
skipped_attempt_nt_upper_bound
skipped_attempt_identity_upper_bound
skipped_attempt_stability_upper_bound
task_output_capacity
scoreInfo-local break-state
```

Decision:

```text
requires_new_cuda_kernel_family = 1
requires_new_certificate_fields = 1
requires_scoreInfo_compatible_semantics = 1
requires_align_side_reduction = 1
requires_full_row_digest_equality = 1
current_code_can_implement_safely_now = 0
```

This remains a possible future Path B design family, but it is not a safe next
runtime PR. It first needs a docs/spec checkpoint that defines the exact
certificate fields, fail-closed behavior, and first1 gate.

### Design B: GPU full scoreInfo/Align-compatible engine with CPU authority replay

This design would replace more of the current scoreInfo/preAlign/Align-side
work by making the GPU produce a Fasim-compatible candidate stream, then replay
the selected work through CPU `aligner.Align()` as authority until a separate
endpoint/CIGAR/traceback proof exists.

It would need:

```text
byte/saturation/tie semantics compatible with Fasim scoreInfo
candidate ordering compatible with existing output
bounded fallback for unsupported query/target shapes
measured reduction in scoreInfo/preAlign work
measured reduction in Align-side work
full row-set/digest equality before any performance claim
```

Decision:

```text
requires_new_cuda_kernel_family = 1
requires_new_certificate_fields = 1
requires_scoreInfo_compatible_semantics = 1
requires_align_side_reduction = 1
requires_full_row_digest_equality = 1
current_code_can_implement_safely_now = 0
```

This is a larger new-engine design, not a continuation of the current
`PreAlignCudaAttemptDescriptor` replay path.

### Design C: Scoped product acceptance path

This path does not complete the original broad objective. It can close the
active goal only if the user explicitly accepts the narrowed product:

```text
short-query/H19 top5 GASAL2 artifact
MEG3-like grouped tiny-region workflow where claimed
archive-first restored output where claimed
```

Non-claims remain:

```text
not aligner.Align replacement
not universal scoreInfo/preAlign replacement
not long-query NEAT1/MALAT1 broad replacement
not GPU endpoint/CIGAR/traceback/output/digest authority
```

Decision:

```text
path_a_user_acceptance_required = 1
```

## Decision

The current broad Path B implementation line has no safe reducing runtime step:

```text
path_b_different_gpu_execution_design_required = 1
path_b_current_implementation_available = 0
path_b_runtime_pr_allowed = 0
path_b_docs_only_design_allowed = 1
```

The next valid work is:

```text
next_valid_work = path_a_scoped_acceptance_or_new_engine_design_doc
current_next_pr = fasim_path_a_scope_acceptance_or_new_gpu_engine_design
```

If Path B continues, the next PR must be docs/spec first. It must define a
genuinely different GPU execution design with a new pre-D2H proof source or a
new Fasim-compatible GPU scoreInfo engine. It must not change runtime behavior.

If Path A is chosen, the next PR must record explicit user scoped acceptance
and keep the original broad objective out of the completion claim.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

## Non-Completion

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

This checkpoint advances the roadmap by narrowing the next valid work. It does
not complete Path A or Path B.
