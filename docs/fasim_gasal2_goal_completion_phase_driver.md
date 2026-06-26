# Fasim GASAL2 Goal Completion Phase Driver

This is the direct phase driver for making the active Fasim/GASAL2 goal
closable. It is not a success claim.

The active broad goal remains:

```text
Use GASAL2/GPU to materially accelerate or replace the scoreInfo/preAlign /
Align-related Fasim path while preserving the required output contract.
```

Until Phase 8 passes:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Current Cursor

```text
current_path = Path B
current_phase = Phase 7
current_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_gate_document = docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
runtime_pr_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
```

Historical pre-upper-bound-reject-shadow cursor:

```text
current_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
current_next_pr = fasim_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
current_gate_document = docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance.md
```

Historical pre-upper-bound-reject-spec cursor:

```text
current_gate = new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go
current_next_pr = fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go
current_gate_document = docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go.md
```

Historical pre-post-native-DP-fork cursor:

```text
current_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go
current_gate_document = docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_no_go.md
```

Historical pre-native-DP-fork cursor:

```text
current_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
```

Historical pre-native-DP-consumer cursor:

```text
current_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
```

Historical pre-native-DP-shadow cursor:

```text
current_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
current_next_pr = fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
```

Historical pre-native-DP-spec cursor:

```text
current_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
current_next_pr = fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
```

Historical pre-consumer-no-go cursor:

```text
current_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_or_no_go
```

Historical pre-scaffold cursor:

```text
current_gate = phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold
```

Historical pre-spec cursor:

```text
current_gate = phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
current_next_pr = fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance
```

Path A and Path B are separate close paths:

```text
Path A: scoped completion
  Only valid if the user explicitly accepts the narrowed deliverable:
    short-query/H19 top5 GASAL2 artifact
    MEG3-like complete-record grouping where claimed
    archive-first restored output where claimed

Path B: broad completion
  Required while the original broad goal remains active:
    full row-set/digest equality
    runtime win over CPU authority
    scoreInfo/preAlign work reduced or replaced
    Align-side work reduced or replaced
    fallback accounting clean
```

Do not mix Path A evidence into Path B completion.

Historical Phase 7.3 no-go cursor:

```text
current_gate = path_a_scoped_acceptance_or_new_engine_design_doc
current_next_pr = fasim_path_a_scope_acceptance_or_new_gpu_engine_design
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
```

## Current Stepwise Execution Order

The active goal is not closable by adding another runtime experiment to the
current descriptor stream. From the current cursor, the allowed sequence is:

```text
Step 1 - Phase 7.1:
  checkpoint the new GPU engine spec-or-Path-A decision, then write the
  first1 implementation spec, then either implement first1 shadow or record
  explicit Path A scoped acceptance. This is now fail-closed scaffolded.

Step 2A - Path A if accepted:
  rerun Phase 0, Phase 1, Phase 5, Phase 6, and Phase 8 scoped gates
  close only as scoped completion

Step 2B - Path B if the spec is complete:
  the certificate CUDA API producer first1 synthetic gate is now present.
  The Phase 7.3 first1 reducing runtime no-go is now recorded for the current
  certificate producer line.

Step 3 - Phase 7.2:
  the certificate producer has proved skipped work before D2H and before final
  CPU output membership is known for the synthetic first1 API gate.
  Historical post-producer cursor:
    current_gate = first1_reducing_runtime_with_certificate_or_no_go
    current_next_pr = fasim_new_gpu_engine_first1_reducing_runtime_or_no_go

Step 4 - Phase 7.3:
  first1 runtime reduction no-go is recorded. It has no real Fasim runtime
  certificate source and no real work-drop path.

Step 4B - Phase 7.3 design response:
  the after-first1-no-go design checkpoint is recorded. The next Path B work
  must be a real-source first1 implementation spec, not a continuation of the
  synthetic certificate producer.

Step 4C - Phase 7.3 real-source first1 spec:
  the real-source first1 spec is defined. The next Path B work may be a
  first1 shadow proposal only if it implements the real runtime hook,
  certificate source, certificate consumer, and fail-closed telemetry contract.

Step 4D - Phase 7.3 real runtime certificate source:
  the source-only checkpoint is recorded from the real Fasim runtime path.
  It proves real_fasim_runtime_certificate_source = 1 and
  gate_first1_source_pass = 1, while keeping real_fasim_runtime_work_drop_path = 0,
  runtime_reduction_enabled = 0, and gate_first1_pass = 0.

Step 4E - Phase 7.3 work-drop proof design:
  the pre-drop output-inert work-drop proof design checkpoint is recorded. It
  defines the future first1 shadow proof gate while keeping runtime reduction,
  work drop, and first64 disabled.

Step 4F - Phase 7.3 first1 proof shadow:
  fail-closed proof shadow is recorded against the real runtime certificate
  source. Runtime reduction, work drop, and first64 remain disabled.

Step 4G - Phase 7.3 proof consumer or no-go:
  this is now recorded as no-go for the current descriptor stream:
    docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.md

Step 4H - Next fork:
  record explicit Path A scoped acceptance, or design a genuinely different
  GPU execution path with a new complete-row-safe pre-drop proof source.

Step 4I - Phase 7.4c different GPU execution design:
  this docs-only checkpoint is now recorded:
    docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md
  It defines the next Path B family as a Fasim-compatible GPU scoreInfo
  frontier certificate engine and keeps runtime PRs disabled.

Step 4J - Phase 7.4d GPU scoreInfo certificate engine spec:
  this docs-only checkpoint is now recorded:
    docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.md
    fasim_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance
  It defines the first1 fail-closed shadow scaffold boundary and still forbids
  runtime reduction, work drop, first64, and GPU output authority.

Step 4K - Phase 7.4e GPU scoreInfo certificate engine first1 shadow scaffold:
  this fail-closed runtime checkpoint is now recorded:
    docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.md
  It observes the real source under
  FASIM_GASAL2_PHASE7_POST_CONSUMER_GPU_SCOREINFO_CERT_ENGINE_FIRST1_SHADOW=1
  while keeping runtime reduction, work drop, and first64 disabled.

Step 4L - Phase 7.4f GPU scoreInfo certificate engine consumer no-go:
  this no-go checkpoint is now recorded:
    docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md
  The first1 shadow has no valid pre-drop certificate to consume, so it cannot
  become a reducing runtime.

Step 4M - Phase 7.4g scoreInfo certificate-engine fork:
  this docs-only fork checkpoint is now recorded:
    docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go.md
  It stops the current scoreInfo certificate-engine family and defines the
  next allowed Path B family as a GPU-owned Fasim scoreInfo consumer with a
  pre-drop frontier certificate.

Step 4N - Phase 7.4h GPU-owned scoreInfo consumer design spec:
  this docs-only spec is now recorded:
    docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance.md
  It defines gpu-owned scoreInfo state, gpu-owned attempt frontier, pre-drop
  certificate field math, consumer decision point, fallback accounting,
  first1 shadow inputs, and expected first1 shadow telemetry.

Step 4O - Phase 7.4i GPU-owned scoreInfo consumer first1 shadow scaffold:
  this fail-closed runtime checkpoint is now recorded:
    docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold.md
  It observes GPU-owned scoreInfo state and attempt frontier telemetry while
  keeping runtime reduction, work drop, and first64 disabled.

Step 4P - Phase 7.4j GPU-owned scoreInfo consumer no-go:
  this no-go checkpoint is now recorded:
    docs/fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go.md
  The first1 shadow has no valid pre-drop frontier certificate to consume, so
  it cannot become a reducing runtime.

Step 5 - Phase 6:
  add a broad_replacement workload matrix row only after the proof consumer and broad gates pass

Step 6 - Phase 8:
  close the goal only if Path A was explicitly accepted or Path B has a
  passing broad_replacement row
```

The post-GPU-owned consumer fork checkpoint is now recorded:

```text
docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.md
path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go = recorded
path_b_different_gpu_execution_design_after_gpu_owned_consumer_no_go_status = design_defined
path_b_new_design_family = gasal2_full_align_result_with_cpu_verifier_certificate
path_b_runtime_pr_allowed = 0
path_b_docs_spec_allowed = 1
next_valid_gate = phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance
current_next_pr = fasim_gasal2_full_align_verifier_design_spec_or_path_a_acceptance
```

The full-align verifier design/spec checkpoint is now defined:

```text
docs/fasim_gasal2_phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance.md
phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance = defined
phase7_full_align_verifier_design_spec_status = spec_defined
path_b_full_align_verifier_spec_defined = 1
path_b_full_align_verifier_first1_fail_closed_shadow_allowed = 1
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
current_next_pr = fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
```

The current immediate deliverable is therefore the first1 fail-closed shadow
scaffold:

```text
fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
```

That scaffold must only observe GASAL2 full AlignResult proposals plus CPU
verifier certificates. It must not make GPU output authoritative, enable
runtime work drop, or run first64 before first1 reduction passes.

## Non-Negotiable Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

These remain true until a separate equivalence proof explicitly changes the
contract. Current GASAL2 work must not use GPU endpoint, CIGAR, traceback,
output, or digest as authority.

## Phase Driver

### Phase 0 - Reproducibility

Goal:

```text
clean checkout can rebuild the patched GASAL2/Fasim bridge
```

Do:

```text
pin GASAL2 upstream commit
track the local GASAL2 patch
record CUDA version, SM arch, GASAL2_MAX_QUERY_LEN, and GASAL2_N_CODE
remove reliance on untracked .tmp/GASAL2 source edits or local binaries
```

Advance when:

```text
clean checkout can rebuild the patched GASAL2/Fasim bridge
```

Stop if:

```text
any claimed result depends on machine-local GASAL2 state
```

### Phase 1 - Scoped Acceptance

Goal:

```text
decide whether Path A can close the goal as a narrowed scoped product
```

Do:

```text
present scoped claims and non-claims together
record explicit user acceptance before using Path A
keep scoped features default-off unless separately accepted
```

Advance to Phase 8 Path A only when:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

Stop Path A if:

```text
the user still wants the original broad scoreInfo/preAlign/Align objective
```

### Phase 2 - Full-Output Baseline

Goal:

```text
keep full restored TFOsorted output correct before any full-output speed claim
```

Do:

```text
preserve restored rows and digest match CPU authority
itemize convert/output wall and whole-run wall
separate full-output evidence from top5-only evidence
keep CPU output authority
```

Advance when:

```text
restored rows and digest match CPU authority
```

Stop if:

```text
row identity, ordering contract, digest, or restored semantics drift
```

### Phase 3 - CPU Output-Side Reduction

Goal:

```text
reduce CPU materialization/convert/output work without changing complete rows
```

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
convert wall improves over Phase 2
```

Stop if:

```text
the reducer preserves only top5
the reducer changes complete rows
the reducer needs final CPU output as runtime proof
the reducer is row-safe but slower
```

### Phase 4 - Sort/Top-N Only If Dominant

Goal:

```text
optimize sort/top-N only after profiling proves it is a material bottleneck
```

Do:

```text
preserve comparator behavior
preserve tie behavior
preserve top-N row selection
measure sort/filter separately from materialization and write wall
```

Advance only when:

```text
sort_or_filter_is_dominant = 1
same rows and order are preserved
sort/filter wall improves
```

Stop if:

```text
triplex materialization, output write, scoreInfo/preAlign, or Align-side work
remains dominant
```

### Phase 5 - Archive Artifact

Goal:

```text
store the minimum reference-backed artifact that can restore claimed output
```

Do:

```text
record archive schema version
record reference digests
validate restored row equality
keep archive delivery separate from broad runtime replacement
```

Advance when:

```text
archive_manifest_valid = 1
archive_restore_rows_equal = 1
archive_restore_digest_match = 1
```

Stop if:

```text
restore depends on hidden local files
restore changes row identity
archive evidence is used as broad runtime replacement by itself
```

### Phase 6 - Workload Matrix

Goal:

```text
make every correctness and performance claim explicit
```

Do:

```text
label every row as claimed, unclaimed, blocked, fallback-heavy, or broad_replacement
ensure claimed rows have passing scoped contracts
ensure broad_replacement rows exist only after Phase 7 broad gates pass
keep fallback-heavy rows out of GPU-fast-path claims
```

Advance when:

```text
claimed rows have passing scoped contracts
broad_replacement rows exist only after Phase 7 broad gates pass
```

Stop if:

```text
top5-only, archive-only, fallback-heavy, or output-drift evidence is labeled
broad_replacement
```

### Phase 7 - Broad Replacement Restart

Goal:

```text
complete the original broad objective, if a valid architecture exists
```

Current state:

```text
current descriptor stream cannot prove output-inert skips
accepted_pre_d2h_proof_families = 0
new_pre_d2h_proof_family_first1_smoke_allowed = 0
real_fasim_runtime_certificate_source = 1
real_fasim_runtime_work_drop_path = 0
runtime_certificate_is_synthetic = 0
source_is_pre_drop = 1
gate_first1_source_pass = 1
gate_first1_pass = 0
reducing_runtime_allowed = 0
first64_runtime_allowed = 0
first1_runtime_reduction_allowed = 1
different_gpu_execution_design_required = 1
path_a_user_acceptance_required = 1
```

The current `PreAlignCudaAttemptDescriptor` stream is useful for replay and
offline analysis. It cannot prove before D2H that skipped scoreInfo groups or
attempts are output-inert, so it cannot enable runtime reduction.

Current decision checkpoints:

```text
docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go.md
docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_or_scope_acceptance.md
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design.md
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance.md
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance.md
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect.md
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold.md
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scaffold.md
docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md
```

Do next:

```text
record Path A scoped acceptance if the user explicitly accepts it, or write the
pre-drop output-inert work-drop proof design before any runtime reduction or
first64 run
```

A valid different Path B design must provide a new pre-D2H proof source:

```text
proof source exists before runtime reduction
skipped scoreInfo groups have conservative output-inert bounds
skipped attempts have conservative score/nt/identity/stability bounds
fallback to full CPU replay exists for unproven tasks
full row-set/digest equality remains required
first1 passes before first64
```

Do not:

```text
Do not reuse the current PreAlignCudaAttemptDescriptor-only stream.
Do not reuse aggregate proof-search export as runtime proof.
Do not use final CPU output membership as runtime proof.
Do not run first64 from a failed first1 producer.
Do not promote top5/archive/output-drift evidence to broad replacement.
```

Advance to a reducing runtime only when:

```text
first1 pre-D2H proof gate passes
runtime reduction uses that proof before dropping work
missing_rows = 0
extra_rows = 0
digest_match = 1
candidate wall beats CPU authority
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
fallback accounting clean
```

Stop if:

```text
no different proof/execution design exists
the only proof comes from final CPU output
the design preserves only top5
the design cannot reduce both scoreInfo/preAlign and Align-side work
```

### Phase 8 - Close Decision

Goal:

```text
make the only allowed close decision
```

Path A may close only when:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
Phase 0 is green
Phase 5 is green where archive output is claimed
Phase 6 labels all claims correctly
non-claims are recorded next to scoped claims
```

Path B may close only when:

```text
Phase 0 is green
Phase 2 full-output baseline is green
Phase 6 has at least one passing broad_replacement row
Phase 7 first64 or larger broad gate passes
full row-set/digest equality = 1
runtime win over CPU authority = 1
scoreInfo/preAlign work reduced or replaced = 1
Align-side work reduced or replaced = 1
fallback accounting clean = 1
CPU aligner.Align() authority = 1
GPU endpoint/CIGAR/traceback/output/digest authority = 0
```

Otherwise:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Immediate Next Work

```text
Write a Phase 7 proof consumer/no-go checkpoint:
  fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go

The current first1 reducing runtime no-go checkpoint is:
  docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.md

The design response checkpoint is:
  docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.md

The real-source first1 spec checkpoint is:
  docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.md

The real-source certificate source checkpoint is:
  docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_first1.md

The pre-drop work-drop proof design checkpoint is:
  docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.md

The different GPU execution design after consumer no-go checkpoint is:
  docs/fasim_gasal2_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.md

The GPU scoreInfo certificate engine spec checkpoint is:
  docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.md

The GPU scoreInfo certificate engine first1 shadow scaffold checkpoint is:
  docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.md

The GPU scoreInfo certificate engine consumer no-go checkpoint is:
  docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.md

If Path B continues, do not implement runtime from any stopped synthetic
certificate producer, descriptor-stream, scoreInfo certificate-engine, or
GPU-owned scoreInfo consumer line. The next Path B artifact is the
full-align verifier first1 fail-closed shadow scaffold:

```text
current_gate =
  phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
current_next_pr =
  fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
```

That scaffold must only observe GASAL2 full AlignResult proposals and CPU
verifier certificates. It must not enable runtime reduction, drop work, run
first64, or change output authority.
The next checkpoint must not change output authority.
Do not relabel the existing v5 CPU-authority replay as the new full-align
verifier scaffold.

The current broad objective remains open until Phase 8 accepts either explicit
Path A scoped completion or a Path B broad gate with full output equality,
runtime win, scoreInfo/preAlign reduction, Align-side reduction, and clean
fallback accounting.

If the user accepts Path A, move to Phase 8 scoped close packet.

## Commands

```bash
make check-fasim-gasal2-roadmap-phase-driver
make check-fasim-gasal2-roadmap-current-state
```

## Current Phase 7 Cursor

```text
docs/fasim_gasal2_phase7_gasal2_full_align_verifier_first1_shadow_scaffold.md
phase7_gasal2_full_align_verifier_first1_shadow_scaffold = fail_closed_shadow
phase7_full_align_verifier_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
path_b_full_align_verifier_first1_shadow_scaffold = 1
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_gasal2_full_align_verifier_first1_shadow_consumer_or_no_go
current_execution_gate = phase7_gasal2_full_align_verifier_first1_shadow_consumer_or_no_go
current_next_pr = fasim_gasal2_full_align_verifier_first1_shadow_consumer_or_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Current Phase 7 Cursor

```text
docs/fasim_gasal2_phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go.md
phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go = recorded
phase7_full_align_verifier_first1_shadow_consumer_status = no_go_no_gpu_full_align_proposals
accepted_full_align_verifier_consumer = 0
accepted_full_align_verifier_certificate = 0
path_b_full_align_verifier_family_stopped = 1
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go
current_execution_gate = path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go
current_next_pr = fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Historical Pre-Native-DP Scaffold Cursor

```text
docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance.md
phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance = defined
phase7_native_cuda_fasim_dp_engine_design_spec_status = spec_defined
path_b_native_cuda_fasim_dp_engine_spec_defined = 1
path_b_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_allowed = 1
path_b_full_align_verifier_family_stopped = 1
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
current_execution_gate = phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Historical Pre-Native-DP Fork Cursor

```text
docs/fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold.md
phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold = fail_closed_shadow
phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
path_b_native_cuda_fasim_dp_engine_first1_shadow_scaffold = 1
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
current_execution_gate = phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
current_next_pr = fasim_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Current Phase 7 Cursor

```text
docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance.md
phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance = defined
phase7_gpu_upper_bound_reject_certificate_design_spec_status = spec_defined
design_family = gpu_upper_bound_reject_certificate_engine
path_b_gpu_upper_bound_reject_certificate_first1_fail_closed_shadow_allowed = 1
runtime_reduction_allowed = 0
runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
historical_execution_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
historical_next_pr = fasim_gpu_upper_bound_reject_certificate_first1_shadow_scaffold
docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold.md
phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold = fail_closed_shadow
phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold_status = fail_closed_no_runtime_reduction
path_b_gpu_upper_bound_reject_certificate_first1_shadow_scaffold = 1
phase7_gpu_upper_bound_reject_certificate_gate_first1_shadow_pass = 1
historical_execution_gate = phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go
historical_next_pr = fasim_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go
docs/fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go.md
phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go = recorded
phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_status = no_go_no_rejected_work
path_b_gpu_upper_bound_reject_certificate_family_stopped = 1
docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go.md
path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go = recorded
path_b_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go_status = required_not_defined
path_b_new_design_family_after_gpu_upper_bound_reject_certificate_no_go = undefined
docs/fasim_gasal2_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.md
phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance = defined
phase7_gpu_exact_work_unit_compaction_design_spec_status = spec_defined
design_family = gpu_exact_work_unit_compaction_replay
current_execution_gate = phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
current_next_pr = fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Historical pre-native-DP-shadow cursor:

```text
docs/fasim_gasal2_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go.md
path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go = recorded
path_b_different_gpu_execution_design_after_full_align_verifier_no_go_status = design_defined
path_b_new_design_family_after_full_align_verifier_no_go = native_cuda_fasim_dp_certificate_engine
next_valid_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
current_execution_gate = phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
current_next_pr = fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
```
