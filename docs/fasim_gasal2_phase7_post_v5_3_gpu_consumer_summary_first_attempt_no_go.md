# Fasim GASAL2 Phase 7 Post-v5.3 GPU Consumer Summary First-Attempt No-Go

This document records the first runtime attempt for the post-v5.3
long-query-safe consumer summary gate. It is a stop checkpoint, not a
completion claim.

## Scope

```text
phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go = recorded
runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1
workload = NEAT1 first1
design_family = legacy_byte_cuda_scoreinfo_consumer_summary_without_gasal2_score_only
implementation_shape = first_descriptor_per_scoreinfo_gpu_summary
runtime_default = off
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Result

The runtime path was active and reduced candidate attempts before host
transfer, but it changed the final lite output. Therefore it failed the
first1 correctness gate.

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
gpu_consumer_summary_rows = 718
gpu_consumer_reduces_before_host_transfer = 1
gpu_selected_attempts = 718
reference_align_attempts = 2872
candidate_align_attempts = 718
v5_candidate_align_attempts = 2872
scoreinfo_prealign_reduced = 1
align_side_reduced = 1
descriptor_false_negatives = 0
missing_required_attempts = 0
fallback_accounting_clean = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

External output comparison is the authority for this gate:

```text
baseline_lite_rows = 19
candidate_lite_rows = 25
baseline_lite_sha256 =
  8e157aac041d698751fd234ba88bce9226cd900aec48ab0aa1c27ce4cbbfe437
candidate_lite_sha256 =
  9658ddf83036fd501d8dc1097ccce38f2e5c5b18212f59e9e110bb46614cc5a1
external_digest_match = 0
external_full_rows_equal = 0
gate_first1_pass = 0
```

The internal telemetry from this probe reported `digest_match=1`,
`full_rows_equal=1`, and `gate_first1_pass=1`, but that was only local gate
logic and was contradicted by the actual output files. For this checkpoint,
the file digest comparison is authoritative.

```text
internal_digest_match_claim_trusted = 0
internal_full_rows_equal_claim_trusted = 0
external_output_comparison_authority = 1
```

## Why It Failed

The reducer selected one descriptor per scoreInfo. That is too aggressive for
the Fasim replay contract. It can reduce GPU-to-host data and CPU replay
attempts, but it does not preserve the complete row set:

```text
first_descriptor_per_scoreinfo_preserves_output = 0
first_descriptor_per_scoreinfo_may_continue_as_gate_v5_5 = 0
```

The diff showed both changed rows and extra rows in the candidate output. The
candidate output had 6 more lite rows than the baseline.

## Decision

```text
phase7_post_v5_3_gpu_consumer_summary_first_attempt_status = no_go
phase7_post_v5_3_gpu_consumer_summary_first1_gate_pass = 0
phase7_post_v5_3_gpu_consumer_summary_may_claim_completion = 0
do_not_run_first64_from_this_probe = 1
do_not_add_broad_replacement_row_from_this_probe = 1
```

Next Path B work must use a stronger consumer summary that preserves the
scoreInfo-local replay boundary semantics. It must not select an arbitrary
single descriptor per scoreInfo.

```text
next_required_gate = stronger_post_v5_3_consumer_summary_design_or_path_a_acceptance
required_next_design_property = prefix_boundary_or_equivalent_replay_proof
```

## Still Forbidden

```text
GPU endpoint authority = 0
GPU CIGAR authority = 0
GPU traceback authority = 0
GPU output authority = 0
GPU digest authority = 0
runtime default change = 0
broad_replacement workload matrix promotion = 0
```
