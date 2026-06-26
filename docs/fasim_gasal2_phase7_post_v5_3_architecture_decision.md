# Fasim GASAL2 Phase 7 Post-v5.3 Architecture Decision

This document records the Phase 7 decision after the v5 CPU-authority
descriptor replay first64 broad gate. It does not close the active goal. It
defines what can happen next without repeating a stopped implementation.

## Current Decision

```text
phase7_post_v5_3_architecture_decision = defined
phase7_post_v5_3_current_v5_status = stopped_no_go
phase7_post_v5_3_next_gate =
  different_gpu_execution_design_or_path_a_scope_decision
path_a_user_acceptance_required = 1
path_b_new_broad_architecture_required = 1
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Evidence Behind The Decision

The current v5 path is stopped for broad completion:

```text
document =
  docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate.md
phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate =
  correctness_clean_performance_no_go
final_digest_match = 1
final_full_rows_equal = 1
candidate_align_attempts = 115561
reference_align_attempts = 211976
align_attempt_reduction = 96415
candidate_wall_seconds = 124.399845
baseline_wall_seconds = 87.827405
candidate_vs_baseline = 0.706009
missing_required_attempts = 624
fallback_accounting_clean = 0
broad_gate_pass = 0
```

The v5 path proves that a pre-scoreInfo descriptor source can reduce CPU Align
attempts on first64 while preserving final `.lite` output for that run. It does
not prove a broad replacement because wall time is slower than CPU authority
and the descriptor coverage/fallback gate is not clean.

## Stopped Paths

Do not continue these as broad-completion candidates:

```text
direct GASAL2 aligner.Align replacement
current GPU score bridge
current replacement-consumer source
attempt-consumer source
emission-only source
frontier early-stop source
Gate C current source
Phase 7 v3 seed/index source
Phase 7 v4 host-visible scoreInfo source replay
Phase 7 v5 CPU-authority descriptor replay
```

These paths remain evidence, not completion.

## Path A Option

Path A is still available only with explicit user acceptance:

```text
path_a_choice = accept_scoped_completion
path_a_acceptance_document =
  docs/fasim_gasal2_path_a_scoped_completion_acceptance.md
scoped_completion_may_close_goal requires user_scope_acceptance_recorded = 1
```

If Path A is accepted, rerun Phase 0, Phase 1, Phase 5, Phase 6, and Phase 8
gates. Path A does not claim broad `aligner.Align()` replacement, long-query
NEAT1/MALAT1 replacement, GPU endpoint authority, GPU CIGAR authority, GPU
traceback authority, or GPU output authority.

## Path B Option

Path B can continue only with a genuinely different GPU execution design. The
new design must not be another version of the v5 CPU-authority descriptor
replay unless it changes the reason v5 failed:

```text
required_design_difference:
  reduce GPU/CPU round trips or replay overhead
  avoid post-hoc CPU authority replay as the dominant path
  keep coverage accounting clean before performance claims
  reduce or replace scoreInfo/preAlign work
  reduce or replace Align-side work
  preserve final row/digest equality for the claimed workload
  keep CPU aligner.Align() as semantic authority until separately proven
```

The next valid Path B design must name which bottleneck it attacks:

```text
candidate_architecture_family:
  GPU-resident scoreInfo + consumer state machine
  or CPU frontier reducer with proof-first full-row safety
  or output-side accelerator only if paired with a broad score/Align reduction
```

Designs that only improve output/archive delivery or top5 artifacts are useful
scoped milestones, but they cannot satisfy Path B alone.

## Required Next Path B Gate

Before runtime implementation, the next Path B PR must be a design checkpoint:

```text
next_path_b_pr =
  fasim: design post-v5.3 GASAL2 broad architecture
deliverable =
  docs/fasim_gasal2_phase7_post_v5_3_new_architecture_design.md
```

That design must include:

```text
1. bottleneck target:
   scoreInfo/preAlign, Align-side work, or both

2. equivalence contract:
   full row-set/digest equality, not top5-only equality

3. authority model:
   CPU aligner.Align() remains endpoint/CIGAR/traceback/output authority
   unless the design defines a separate proof gate

4. first gate:
   first1 smoke with row/digest equality and clean accounting

5. broad gate:
   first64 or equivalent workload with:
     full_rows_equal = true
     digest_match = true
     candidate_wall_seconds < baseline_wall_seconds
     candidate_vs_baseline > 1.0
     scoreInfo/preAlign work reduced or replaced
     Align-side work reduced or replaced
     fallback_accounting_clean = true
```

## Forbidden Next Actions

```text
do_not_repeat_v5_first64 = 1
do_not_add_broad_replacement_row_from_v5_3 = 1
do_not_use_gpu_endpoint_authority = 1
do_not_use_gpu_cigar_traceback_authority = 1
do_not_use_gpu_output_digest_authority = 1
do_not_close_goal_without_phase8 = 1
```

## Decision Summary

```text
current_decision = pending_path_a_acceptance_or_new_path_b_design
next_required_gate = post_v5_3_new_architecture_design_or_path_a_acceptance
broad_objective_status = open
must_not_call_update_goal_complete = 1
```
