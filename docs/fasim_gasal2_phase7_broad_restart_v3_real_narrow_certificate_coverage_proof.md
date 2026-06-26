# Fasim GASAL2 Phase 7 v3 Real Narrow Certificate Coverage Proof

This checkpoint evaluates the most direct real narrow certificate candidate
after the bounded narrow probe failed coverage: the existing long-query
exact-column scoreInfo GPU shadow.

It is not a broad replacement, not a performance claim, and not permission to
use GASAL2/GPU endpoint, CIGAR, traceback, output, or digest as authority.

```text
phase7_broad_restart_v3_real_narrow_certificate_coverage_proof = exact_column_candidate_no_go
phase7_broad_restart_v3_exact_column_candidate_status = no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Candidate

The candidate is:

```text
FASIM_LONG_QUERY_EXACT_COLUMN_SCOREINFO_GPU_SHADOW=1
```

This is narrower than the all-column/all-window certificate because it attempts
to generate exact legacy scoreInfo groups instead of replaying every possible
target window. If it were scoreInfo-equivalent and launchable, it could become
a plausible real narrow certificate source.

CPU aligner.Align() output authority remains required:

```text
CPU aligner.Align() output authority
no GPU endpoint/CIGAR/traceback/output authority
```

## Non-Opt-In Result

Validation command:

```bash
make check-fasim-long-query-exact-column-scoreinfo-shadow
```

Observed MALAT1 first8 result:

```text
non_optin_active = 0
non_optin_query_len = 8708
non_optin_tasks = 1824
non_optin_gpu_batches = 1
non_optin_gpu_tasks = 0
non_optin_fallback_batches = 1393
non_optin_scoreinfo_mismatches = 0
non_optin_required_smem = 52416
non_optin_default_smem_limit = 49152
non_optin_optin_smem_limit = 101376
non_optin_resource_fit = 1
non_optin_error = invalid argument
```

Interpretation:

```text
default shared-memory launch:
  no-go

reason:
  required dynamic shared memory crosses the default per-block limit
```

## Shared-Memory Opt-In Result

Validation command:

```bash
make check-fasim-long-query-exact-column-scoreinfo-shadow-smem-optin
```

Observed MALAT1 first8 result:

```text
smem_optin_active = 1
smem_optin_query_len = 8708
smem_optin_gpu_batches = 1
smem_optin_gpu_tasks = 432
smem_optin_scoreinfo_mismatches = 1
smem_optin_required_smem = 52416
smem_optin_default_smem_limit = 49152
smem_optin_optin_smem_limit = 101376
smem_optin_resource_fit = 1
smem_optin_requested = 1
smem_optin_active = 1
smem_optin_error = cuda_query_or_batch_unavailable
smem_optin_decision = smem_optin_scoreinfo_no_go
```

Interpretation:

```text
shared-memory opt-in:
  launch works

scoreInfo equivalence:
  no-go
```

Because scoreInfo mismatches are non-zero, this candidate cannot prove:

```text
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
```

## Decision

```text
phase7_broad_restart_v3_real_narrow_certificate_coverage_proof = exact_column_candidate_no_go
phase7_broad_restart_v3_exact_column_candidate_status = no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
exact-column GPU scoreInfo is not a valid real narrow certificate source
phase7_broad_restart_v3_next_gate = different_exact_scoreinfo_source_or_seed_certificate
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Do not add a broad_replacement workload-matrix row from this checkpoint.

The next Path B attempt must use a different source:

```text
different exact scoreInfo-compatible GPU execution design
or
seed/index certificate that proves coverage without CPU scoreInfo for every task
```

It must still pass:

```text
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
candidate_attempts < reference_align_attempts before v3.2 can pass
CPU aligner.Align() output authority
```
