# Fasim GASAL2 Phase 7 Post-v5.3 Stronger Consumer Summary Prefix No-Go

This document records the first implementation of the stronger post-v5.3
consumer-summary design. It is a stop checkpoint, not a completion claim.

## Scope

```text
phase7_post_v5_3_stronger_consumer_summary_prefix_no_go = recorded
runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY=1
workload = NEAT1 first1
implementation_shape = gpu_prefix_attempt_descriptors_per_scoreinfo
runtime_default = off
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## What Changed

The previous runtime probe used one descriptor per scoreInfo and changed the
external lite output. This checkpoint replaced that hard-coded shape with a
GPU prefix selector:

```text
new_cuda_api = prealign_cuda_emit_legacy_byte_prefix_attempt_descriptors
prefix_env =
  FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY_PREFIX_ATTEMPTS
uses_prefix_boundary_or_equivalent_replay_proof = 1
arbitrary_sparse_subset = 0
first_descriptor_per_scoreinfo = 0 for prefix >= 2
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

The smoke checker was also corrected to treat external output files as the
first1 correctness authority:

```text
external_output_comparison_authority = 1
internal_digest_match_claim_trusted = 0
internal_full_rows_equal_claim_trusted = 0
```

## Prefix Sweep Result

The first1 prefix sweep shows a hard boundary:

```text
prefix = 1:
  external_digest_match = 0
  external_full_rows_equal = 0
  candidate_lite_rows = 25
  gpu_selected_attempts = 718
  candidate_align_attempts = 718

prefix = 2:
  external_digest_match = 0
  external_full_rows_equal = 0
  candidate_lite_rows = 23
  gpu_selected_attempts = 1436
  candidate_align_attempts = 1148

prefix = 3:
  external_digest_match = 0
  external_full_rows_equal = 0
  candidate_lite_rows = 20
  gpu_selected_attempts = 2154
  candidate_align_attempts = 1578

prefix = 4:
  external_digest_match = 1
  external_full_rows_equal = 1
  candidate_lite_rows = 19
  gpu_selected_attempts = 2872
  selected_prefix_attempts = 2872
  candidate_align_attempts = 2008
  v5_candidate_align_attempts = 2872

prefix = 5:
  external_digest_match = 1
  external_full_rows_equal = 1
  candidate_lite_rows = 19
  gpu_selected_attempts = 2872
  selected_prefix_attempts = 2872
  candidate_align_attempts = 2008
  v5_candidate_align_attempts = 2872
```

## Decision

The stronger prefix implementation does not pass the post-v5.3 first1 gate.

```text
correctness_clean_requires_prefix_attempts = 4
prefix_1_2_3_reduce_gpu_selected_attempts_but_change_output = 1
prefix_4_5_preserve_output_but_do_not_reduce_gpu_selected_attempts = 1
gpu_selected_attempts < v5_candidate_align_attempts = 0
selected_prefix_attempts < v5_candidate_align_attempts = 0
phase7_post_v5_3_stronger_consumer_summary_first1_gate_pass = 0
phase7_post_v5_3_stronger_consumer_summary_may_claim_completion = 0
do_not_run_first64_from_this_probe = 1
do_not_add_broad_replacement_row_from_this_probe = 1
```

This result is still useful: it proves that a pure fixed-prefix boundary is not
enough. The only output-clean prefix is effectively the full v5 descriptor set,
so it does not reduce GPU-to-host descriptor transfer.

## Next Valid Work

Continue Path B only with a materially different architecture, or return to
Path A scoped acceptance.

```text
next_required_gate =
  different_gpu_execution_design_or_path_a_scope_decision

valid_next_architecture_must_do_one_of:
  prove a non-fixed replay certificate that skips suffix attempts safely
  reduce Align-side work without requiring all v5 descriptors to cross D2H
  change the GPU execution shape enough to reduce both scoreInfo/preAlign and
    Align-side work while preserving external output

still_forbidden:
  GPU endpoint authority
  GPU CIGAR authority
  GPU traceback authority
  GPU output authority
  GPU digest authority
  broad_replacement workload matrix promotion
  goal completion claim
```
