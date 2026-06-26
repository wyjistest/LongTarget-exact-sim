# Fasim GASAL2 Phase 7 Post-v5.3 Pre-D2H Proof Search First1 Export

This checkpoint implements the first diagnostic export gate from
`docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md`.
It is not a reducing runtime and not a broad completion claim.

## Scope

```text
phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export = pass
phase7_post_v5_3_pre_d2h_output_inert_proof_search_status = first1_export_pass
phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion = 0
runtime_default = off
runtime_reduction_enabled = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Runtime Env

```text
FASIM_GASAL2_PHASE7_POST_V5_3_PRE_D2H_PROOF_SEARCH=1
```

The env only records pre-D2H proof-search telemetry. It does not skip
scoreInfo groups, reduce Align attempts, replace endpoint/CIGAR/traceback, or
change output authority.

## First1 Smoke Result

Command:

```bash
bash scripts/check_fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_runtime_smoke.sh
```

Observed first1 gate:

```text
requested = 1
active = 1
source_is_pre_scoreinfo = 1
source_is_legacy_byte_cuda = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gpu_output_authority = 0
runtime_reduction_enabled = 0
proof_search_rows = 2872
task_count = 48
scoreinfo_count = 718
attempt_count = 2872
label_source_cpu_authority_external_output = 1
gate_first1_export_pass = 1
external_digest_match = 1
external_full_rows_equal = 1
```

## Boundaries

This checkpoint does not authorize:

```text
runtime reduction
first64 runtime
broad_replacement workload matrix promotion
GPU endpoint authority
GPU CIGAR authority
GPU traceback authority
GPU output authority
GPU digest authority
```

## Next Gate

```text
current_execution_gate = pre_d2h_output_inert_proof_acceptance_first1
current_next_pr = fasim_audit_pre_d2h_output_inert_proof_search_first1
```

The next PR must analyze the exported proof-search telemetry and decide
whether any proof family can safely reduce work before D2H. If no proof has
zero false negatives, record a no-go checkpoint instead of writing a reducing
runtime.
