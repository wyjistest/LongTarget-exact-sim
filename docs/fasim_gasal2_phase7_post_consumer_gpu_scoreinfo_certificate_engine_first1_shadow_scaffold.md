# Fasim GASAL2 Phase 7 Post-Consumer GPU ScoreInfo Certificate Engine First1 Shadow Scaffold

This checkpoint implements the first1 fail-closed shadow scaffold for the
post-consumer GPU scoreInfo certificate engine. It observes the real Fasim
runtime descriptor source and emits certificate-engine telemetry, but it does
not use the GPU result to drop work or to change output.

## Scope

```text
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold = fail_closed_shadow
previous_checkpoint = docs/fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.md
previous_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold
required_runtime_env = FASIM_GASAL2_PHASE7_POST_CONSUMER_GPU_SCOREINFO_CERT_ENGINE_FIRST1_SHADOW
telemetry_prefix = benchmark.fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_cert_engine_first1_shadow_
```

This is Path B only. Path A scoped completion remains unavailable unless the
user explicitly accepts that narrow scope in a separate checkpoint.

## Runtime Contract

When the runtime env is set on first1, this checkpoint must report:

```text
requested = 1
active = 1
scoreinfo_cert_engine_first1_shadow = 1
real_fasim_runtime_certificate_source = 1
certificate_valid_before_work_drop = 0
certificate_valid_before_d2h = 0
runtime_reduction_enabled = 0
runtime_work_drop_enabled = 0
fallback_to_full_cpu_replay = 1
gpu_scoreinfo_groups > 0
gpu_attempt_frontier_attempts > 0
gpu_selected_replay_attempts > 0
gpu_skipped_scoreinfo_groups = 0
gpu_skipped_attempts = 0
cpu_replay_attempts > 0
baseline_cpu_attempts > 0
certificate_false_negatives = 0
missing_required_attempts = 0
scoreInfo_prealign_reduced = 0
align_side_reduced = 0
fallback_accounting_clean = 0
full_rows_equal = 0
digest_match = 0
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
gate_first1_shadow_pass = 0
gate_first1_pass = 0
```

The candidate output bytes must remain identical to the baseline because this
checkpoint always falls back to full CPU replay.

## Authority Model

```text
CPU aligner.Align() authority = 1
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
```

## Non-Claims

This checkpoint does not claim:

```text
accepted certificate engine proof
valid certificate before work drop
valid certificate before D2H
enabled runtime reduction
enabled runtime work drop
clean fallback accounting
first1 shadow gate pass
first1 broad gate pass
first64 authorization
broad objective completion
```

## Decision

```text
phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold_status = fail_closed_shadow
path_b_scoreinfo_certificate_engine_first1_shadow_scaffold = 1
path_b_runtime_reduction_pr_allowed = 0
path_b_runtime_work_drop_allowed = 0
first1_runtime_reduction_gate_pass = 0
first64_runtime_allowed = 0
next_valid_gate = phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go
current_next_pr = fasim_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_or_no_go
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

The next gate must either implement a real first1 certificate consumer that
proves output-inert work drop before any work is dropped, or stop this Path B
design family as no-go. It must not proceed to first64 until a first1 reducing
runtime gate passes.
