# Fasim GASAL2 Phase 7 Post-v5.3 Task-Frontier Certificate First-Attempt No-Go

This document records the first runtime attempt for the post-v5.3
task-frontier certificate gate. It is a stop checkpoint, not a completion
claim.

## Scope

```text
phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go = recorded
runtime_env = FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE=1
workload = NEAT1 first1
design_family = gpu_task_frontier_certificate_with_cpu_authority_replay
implementation_shape = first_scoreinfo_group_per_task_certificate_probe
new_cuda_api =
  prealign_cuda_emit_legacy_byte_task_frontier_certificate_descriptors
runtime_default = off
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## What Ran

The env scaffold was advanced from fail-closed to a real producer probe. The
CUDA stage emitted a task-local certificate row for each task and selected the
first scoreInfo descriptor group per task. CPU `aligner.Align()` remained the
only replay authority.

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
source_is_legacy_byte_cuda = 1
gasal2_score_only_long_query_dependency = 0
uses_task_frontier_certificate = 1
uses_prefix_boundary_only = 0
arbitrary_sparse_subset = 0
first_descriptor_per_scoreinfo = 0
fixed_prefix_per_scoreinfo = 0
gpu_consumer_reduces_before_host_transfer = 1
task_frontier_certificate_rows = 48
gpu_selected_attempts = 192
reference_align_attempts = 2872
candidate_align_attempts = 138
v5_candidate_align_attempts = 2872
descriptor_false_negatives = 0
missing_required_attempts = 0
fallback_accounting_clean = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

## External Output Result

External output comparison is the correctness authority for this gate. The
candidate reduced attempts, but it did not preserve the complete lite output.

```text
baseline_lite_rows = 19
candidate_lite_rows = 2
missing_rows = 17
extra_rows = 0
baseline_lite_sha256 =
  8e157aac041d698751fd234ba88bce9226cd900aec48ab0aa1c27ce4cbbfe437
candidate_lite_sha256 =
  10ca758a91e6f793891b9b21c3bde4a8bcb3293ef9e2c9de27acfeb7485321c8
external_digest_match = 0
external_full_rows_equal = 0
gate_first1_pass = 0
```

The first missing row was:

```text
chr11	40149305	40149363	AntiMinus	12	17668	17722	506	564	R	124	59	74.5763	1.71186
```

## Decision

The first task-frontier certificate producer is a no-go for the Phase 7a
first1 gate.

```text
phase7_post_v5_3_task_frontier_certificate_first_attempt_status = no_go
phase7_post_v5_3_task_frontier_certificate_first1_gate_pass = 0
phase7_post_v5_3_task_frontier_certificate_may_claim_completion = 0
do_not_run_first64_from_this_probe = 1
do_not_add_broad_replacement_row_from_this_probe = 1
```

The probe proves that a task-level producer can reduce descriptor transfer and
CPU replay attempts, but the selected frontier is not sufficient to preserve
the complete output. The next broad attempt must use a stronger task-local
certificate that proves skipped scoreInfo groups cannot affect the task output,
or the work must return to Path A scoped acceptance.

```text
next_required_gate =
  stronger_task_frontier_certificate_design_or_path_a_acceptance
required_next_design_property =
  prove skipped scoreInfo groups are output-inert before D2H
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
goal completion claim = 0
```
