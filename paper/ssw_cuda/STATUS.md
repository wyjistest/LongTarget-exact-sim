# SSW-CUDA Program Status

```text
execution_start_head = 9f87aace6d96cf8142e3816299f04defae5710e4
execution_branch = gasal2-kcnq1ot1-focused-review
active_phase = 1
phase_0_status = pass
phase_1_status = in_progress
phase_1_profile_execution_epoch = 2
phase_1_v1_status = blocked_by_fixed_timeout
phase_1_recovery_status = preregistered_not_run
ssw_cpu_oracle_epoch = 2
ssw_cuda_program_epoch = 1
bioinformatics_b3_track = pending_amdahl
engineering_track = active
l8_contract_status = diagnostic_only
```

Phase 0 imported 904 immutable historical evidence files and froze 112
deduplicated input exclusions. The CPU authority epoch-2 binary is bound to
the frozen source/toolchain/hardware receipt and matches the historical v2
authority binary digest. Phase 2, Phase 3 pilot, and canonical-hybrid-v2
runtime/regression/holdout/performance checks passed.

Phase 1 formal profiling stopped prospectively at execution order 21. The
first claim-relevant `large_h19_chr21` profile-off attempt reached the frozen
1,800-second timeout. The runner retained one 37,430,661-byte partial output,
recorded 20 complete attempts and one technical failure, attempted no retry,
and did not start the remaining 29 attempts.

The v1 formal panel is incomplete. No v1 source data, statistics, conservative
addressable fraction, or Amdahl ceiling is claimed. Its receipt, manifest, and
partial artifact remain immutable.

Phase 1 profile execution epoch 2 is preregistered. It repeats all 50 attempts
from the beginning in a separate artifact root and changes only the outer
per-attempt timeout from 1,800 to 7,200 seconds. Its total wall-clock budget is
36 hours and retry policy remains `none`. V1 observations cannot enter v2
statistics. The original 10x threshold is unchanged,
`bioinformatics_b3_track` remains `pending_amdahl`, and no new CUDA DP kernel
is authorized before v2 completes and passes its checker.
