# Fasim GASAL2 Phase 7 Broad Restart v3 Candidate-Certificate Design

This is a design checkpoint for the next allowed Path B attempt after the
current broad GASAL2/Fasim sources were stopped.

It is not runtime code, not a completion claim, and not permission to use
GASAL2 endpoint, CIGAR, traceback, output, or digest as authority.

```text
phase7_broad_restart_v3_candidate_certificate_design = defined
phase7_broad_restart_v3_status = design_only
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Why v3 Exists

The current broad sources are stopped:

```text
replacement-consumer:
  no broad runtime win and no acceptable broad contract

attempt-consumer:
  CPU Align attempts not reduced

emission-only consumer:
  output correctness no-go

frontier early-stop runtime:
  NEAT1 first1 output rows differ

all-attempt early-stop runtime:
  output clean, Align attempts reduced, but scoreInfo/preAlign work is still CPU
  work and wall time is near parity

Gate C current source:
  output clean, but gpu_candidate_scoreinfos = 0 and gpu_candidate_attempts = 0
```

Therefore v3 must not continue those sources. It must create a new descriptor
source before CPU scoreInfo/preAlign has already done the broad work.

## v3 Architecture

The v3 architecture is candidate-certificate first:

```text
GPU/native descriptor source
  produces candidate descriptors from query/target inputs or a new exact
  scoreInfo-compatible kernel, not from completed CPU frontier logs

candidate certificate
  proves every legacy-required scoreInfo/attempt/output row remains covered
  before any CPU Align attempt is skipped

CPU-authority replay
  runs CPU aligner.Align() only for certified descriptors needed by the legacy
  output contract

full-output comparison
  compares restored rows, digest, fallback counts, scoreInfo/preAlign work, and
  Align-side work against the CPU authority baseline
```

Required descriptor fields:

```text
query_id
target_id
target_offset
target_length
scoreinfo_task_id
candidate_rank_or_bucket
legacy_order_key
scoring_config_key
certificate_group_id
output_replay_slot
```

The descriptor source may overgenerate. It may not undergenerate any legacy
required candidate.

## What Makes This Different

v3 is not:

```text
not current replacement-consumer
not current attempt-consumer
not current emission-only consumer
not current frontier early-stop
not all-attempt early-stop by itself
not current Gate C oracle-metric scaffold
not a descriptor list derived only after CPU frontier logging
not GASAL2 endpoint/CIGAR/traceback/output authority
not top5-only proof as broad proof
```

v3 is allowed to use:

```text
GASAL2 score proposals
new GPU scoreInfo-compatible kernels
CPU seed/index prefilters only if they reduce CPU scoreInfo/preAlign work
bounded CPU fallback only if fallback accounting remains below the broad gate
CPU aligner.Align() validation for output authority
```

## Non-Negotiable Correctness Contract

CPU `aligner.Align()` remains the authority for:

```text
score
endpoint
traceback
CIGAR
candidate state
output rows
digest
```

GASAL2/GPU may only affect which CPU-authority work is attempted after the
candidate certificate proves coverage.

Forbidden:

```text
gpu_endpoint_authority = 1
gpu_cigar_authority = 1
gpu_traceback_authority = 1
gpu_output_authority = 1
output drift counted as speedup
fallback-heavy row claimed as GPU-fast-path clean
contract=broad_replacement before first64 broad gate passes
```

## Required Gates

Gate v3.0: design gate

```text
phase7_broad_restart_v3_candidate_certificate_design = defined
requires_gpu_or_native_descriptor_source = 1
requires_candidate_certificate = 1
requires_cpu_authority_replay = 1
requires_scoreinfo_prealign_reduction = 1
requires_align_side_reduction = 1
requires_full_output_equality = 1
```

Gate v3.1: NEAT1 first1 descriptor-source smoke

```text
gpu_candidate_scoreinfos > 0
gpu_candidate_attempts > 0
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
fallback_accounting_clean = 1
full_output_authority = CPU aligner.Align()
```

Gate v3.2: NEAT1 first1 CPU-authority replay

```text
digest_match = 1
full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
candidate_align_attempts < reference_align_attempts
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
```

Gate v3.3: NEAT1 first64 broad gate

```text
digest_match = 1
full_rows_equal = 1
candidate_vs_baseline > 1.0x
candidate_wall_seconds < baseline_wall_seconds
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
fallback_accounting_clean = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

Only Gate v3.3 can create a `contract=broad_replacement` workload-matrix row.

## Candidate Implementation Directions

Direction A: exact scoreInfo-compatible GPU source

```text
Implement a GPU source that reproduces the Fasim scoreInfo candidate contract:
  unsigned byte-saturated SSW behavior
  bias and byte saturation behavior
  word upgrade behavior
  window-of-5 peak clustering and tie policy
  legacy order keys

This is the most direct broad route. It is also effectively a new kernel,
not direct GASAL2 aligner replacement.
```

Direction B: GASAL2 overgenerate plus certificate

```text
Use GASAL2 only to overgenerate candidate descriptors.
Use a separate certificate to prove no legacy-required scoreInfo/attempt is
lost before CPU scoreInfo/preAlign is skipped.

This direction can continue only if it reduces CPU scoreInfo/preAlign calls.
If the certificate needs CPU scoreInfo for every task, it is no-go.
```

Direction C: seed/index certificate plus CPU replay

```text
Use a target/query seed index to create a superset of legacy-required
candidates, then replay with CPU aligner.Align() for authority.

This direction can continue only if the index reduces both broad CPU
scoreInfo/preAlign work and Align-side attempts.
```

## Stop Conditions

Stop v3 before first64 if any of these happens:

```text
gpu_candidate_scoreinfos = 0
gpu_candidate_attempts = 0
candidate_certificate_false_negatives > 0
missing_required_attempts > 0
cpu_scoreinfo_calls >= baseline_cpu_scoreinfo_calls
candidate_align_attempts >= reference_align_attempts
digest_match = 0
full_rows_equal = 0
candidate_vs_baseline <= 1.0x at broad gate
```

If Gate v3.1 cannot be satisfied, Path B remains open but no current GASAL2
broad architecture is executable. The remaining completion route is Path A
scoped acceptance, unless a future architecture provides a different descriptor
source with the same gates.

## Current Runtime Smoke

The first v3 runtime smoke is recorded separately:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_descriptor_source_smoke.md
phase7_broad_restart_v3_descriptor_source_smoke = current_no_pre_scoreinfo_source
phase7_broad_restart_v3_current_status = scaffold_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate = real_pre_scoreinfo_descriptor_source
```

That smoke proves only that telemetry is wired and default-off. It does not
produce candidate descriptors, does not reduce CPU scoreInfo/preAlign work, and
does not pass Gate v3.1.

The follow-up pre-scoreInfo smoke is recorded separately:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke.md
phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke =
  pre_scoreinfo_descriptors_no_reduction
phase7_broad_restart_v3_current_status = pre_scoreinfo_scaffold_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate =
  certificate_checked_scoreinfo_reducing_descriptor_source
```

That smoke proves the descriptor hook can run before CPU scoreInfo/preAlign and
can produce diagnostic descriptors. It still does not reduce CPU scoreInfo calls
or check the candidate certificate, so it also does not pass Gate v3.1.

The certificate smoke is recorded separately:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_certificate_smoke.md
phase7_broad_restart_v3_certificate_smoke =
  certificate_checked_no_scoreinfo_reduction
phase7_broad_restart_v3_current_status = certificate_scaffold_no_go
phase7_v3_descriptor_source_candidate_certificate_checked = 1
phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
phase7_v3_descriptor_source_missing_required_attempts = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate =
  scoreinfo_reducing_candidate_certificate
```

That smoke proves only that the pre-scoreInfo descriptor hook can mark a
task-level scaffold certificate as checked. It still does not prove full legacy
scoreInfo/attempt coverage and does not reduce CPU scoreInfo/preAlign work.

The all-column certificate smoke records the first v3.1 pass:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_all_column_certificate_smoke.md
phase7_broad_restart_v3_all_column_certificate_smoke =
  scoreinfo_reducing_all_column_certificate
phase7_broad_restart_v3_current_status =
  gate_v3_1_pass_attempt_overgenerate
phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
phase7_v3_descriptor_source_missing_required_attempts = 0
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
phase7_broad_restart_v3_next_gate =
  all_column_certificate_cpu_replay_first1
```

This is not yet a viable broad architecture because it overgenerates every
target window. Gate v3.2 must prove CPU-authority replay equality and
Align-side attempt reduction before first64 is allowed.

The all-column replay preflight is now recorded as a stop checkpoint:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_all_column_replay_stop.md
phase7_broad_restart_v3_all_column_replay_stop =
  candidate_attempt_explosion_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
candidate_attempts = 168,730,848
reference_align_attempts = 2,872
candidate_attempt_ratio = 58,750.30x
candidate_align_attempts < reference_align_attempts cannot pass
do_not_run_all_column_cpu_replay = 1
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate =
  narrower_scoreinfo_reducing_certificate
```

This means the all-column certificate remains a Gate v3.1 proof only. It must
not be replayed and must not continue to first64. A future v3 source must be a
narrower scoreInfo-reducing certificate that still proves zero false negatives
and keeps CPU `aligner.Align()` as output authority.

That narrower branch is now defined separately:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_design.md
phase7_broad_restart_v3_narrow_certificate_design = defined
phase7_broad_restart_v3_narrow_certificate_status = design_only
phase7_broad_restart_v3_next_gate = narrow_certificate_runtime_smoke
required_runtime_env = FASIM_GASAL2_PHASE7_V3_NARROW_CERTIFICATE
must_be_narrower_than_all_column = 1
do_not_use_all_column_or_all_window_certificate = 1
candidate_attempts < 168,730,848
candidate_attempts < reference_align_attempts required for v3.2
```

The first runtime smoke for that branch is now also stopped:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_smoke.md
phase7_broad_restart_v3_narrow_certificate_smoke =
  bounded_probe_no_go_missing_certificate
phase7_broad_restart_v3_narrow_certificate_status = runtime_smoke_no_go
phase7_v3_descriptor_source_candidate_attempts_lt_all_column = 1
phase7_v3_descriptor_source_candidate_certificate_false_negatives_gt_zero = 1
phase7_v3_descriptor_source_missing_required_attempts_gt_zero = 1
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_next_gate = real_narrow_certificate_coverage_proof
```

The bounded probe is useful plumbing but not a viable certificate. A future
narrow source must prove zero false negatives and zero missing required
attempts before Gate v3.1 can pass.

The direct exact-column scoreInfo source has also been checked and stopped:

```text
document = docs/fasim_gasal2_phase7_broad_restart_v3_real_narrow_certificate_coverage_proof.md
phase7_broad_restart_v3_real_narrow_certificate_coverage_proof =
  exact_column_candidate_no_go
phase7_broad_restart_v3_exact_column_candidate_status = no_go
non_optin_active = 0
non_optin_error = invalid argument
smem_optin_active = 1
smem_optin_gpu_tasks = 432
smem_optin_scoreinfo_mismatches = 1
smem_optin_decision = smem_optin_scoreinfo_no_go
phase7_broad_restart_v3_next_gate =
  different_exact_scoreinfo_source_or_seed_certificate
```

This means the existing exact-column GPU scoreInfo implementation cannot serve
as the real narrow certificate source for v3.

## Decision

```text
phase7_broad_restart_v3_candidate_certificate_design = defined
phase7_broad_restart_v3_current_status = design_only
phase7_broad_restart_v3_next_gate = descriptor_source_smoke
phase7_broad_restart_v3_may_claim_completion = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```
