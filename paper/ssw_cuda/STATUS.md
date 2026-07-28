# SSW-CUDA Program Status

```text
execution_start_head = 9f87aace6d96cf8142e3816299f04defae5710e4
execution_branch = gasal2-kcnq1ot1-focused-review
active_phase = 5
phase_0_status = pass
phase_1_status = pass
phase_1_profile_execution_epoch = 2
phase_1_analysis_epoch = 2
phase_1_v1_status = blocked_by_fixed_timeout
phase_1_recovery_status = pass
phase_2_oracle_execution_epoch = 1
phase_2_status = pass
phase_3_status = pass
phase_4_upstream_evidence_epoch = 1
phase_4_architecture = C_mixed_in_tree_checkpoint_recompute
phase_4_status = pass
phase_5_status = in_progress
ssw_cpu_oracle_epoch = 2
ssw_cuda_program_epoch = 1
bioinformatics_b3_track = closed_amdahl
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

Phase 1 profile execution epoch 2 completed all 50 attempts from the beginning
in 46,806.575 seconds, below the fixed 36-hour budget. It used a separate
artifact root, changed only the preregistered outer timeout from 1,800 to 7,200
seconds, attempted no retry, and reused no v1 observations. Every profile-off
and profile-on pair produced the same authority digest; all profile stacks
closed without errors.

The lower 95% bootstrap bounds for the addressable backend fraction were
0.619888605 for `large_h19_chr21` and 0.619448148 for
`large_h19_chr22`. The conservative fraction is therefore 0.619448148 and the
infinite-backend Amdahl ceiling is 2.627762802x. The original 10x threshold was
not lowered. `bioinformatics_b3_track` is `closed_amdahl`, while the bounded
exact SSW-CUDA engineering track remains active.

The execution runner preserved complete GNU time resource logs but its parser
did not strip their leading tab, leaving maximum RSS empty in the initial
analysis. Analysis epoch 2 reconstructed all 50 RSS values from those immutable
logs. The execution receipt and all attempt receipts remain unchanged; the
analysis receipt proves that profile statistics and the Amdahl decision did
not change. That recovery advanced the program to Phase 2. No new CUDA DP
kernel had been authored at that gate.

Phase 2 froze concrete L0-L6 DP, endpoint, banded traceback, CIGAR, emitted-row,
and telemetry contracts from implementation commit `d7c8c23`. All 20 frozen
attempts completed: two consumed mismatch cases, five observations per case,
and adjacent trace-off/trace-on executions. There were no timeouts, retries, or
technical failures. Every authority output matched its historical SHA-256;
paired output, normalized stdout, and stderr were identical; trace-off created
no trace files; and both trace records were byte-stable across all five
observations. The hq10/hq11 attempt keys, endpoints, band histories, canonical
CIGARs, and L6 emitted rows are now fixtures. No fresh holdout was consumed and
no CUDA DP kernel was authored. Phase 3 then became active.

Phase 3 froze 749 differential-corpus rows before any new CUDA/SSW
implementation change: 112 consumed historical identities, 196 tiny exhaustive
AC pairs, 45 focused adversarial cases, 128 compact deterministic fuzz cases,
and 256 large deterministic fuzz cases. Eleven long length-boundary cases make
the explicit large tier total 267; neither historical identities nor that tier
is executed by the normal checker. The exclusion registry rebuilt byte for
byte and all 112 entries are represented. The fail-closed holdout checker
rejects ordinal, sequence-digest, pair-digest, prior-receipt, debug,
minimization, and fuzz-replay overlap without an override path.

The frozen layered comparator classifies hq10 first at L5 (alternative CIGAR
gap placement) and hq11 first at L4 (reverse start), while preserving the
established root-cause wording and making no DP tie-cell claim. L8 remains
diagnostic only, no fresh holdout was selected or executed, and no new CUDA DP
kernel was authored. Phase 4 then became active.

Phase 4 pinned Accelign at `c7ecd32d59e256716cca193556110051c171570f`
(Apache-2.0) and G3SA at `f0e0c130631dc2e06f92822b66c0494683f77eef`
(GPL-3.0). Accelign built on its first attempt and passed its own affine-local
score/start/end checks at 64 and 2812 bases. Those checks establish upstream
self-consistency only; they do not establish SSW equality.

G3SA used the maximum three build attempts. Two failed because of hard-coded
CUDA 12.1 include handling; the third succeeded after a sandbox-only two-line
portability patch and an explicit host CUDA include path. Its help probe was
treated as an input and its no-argument probe exited 139 after GPU detection,
so no G3SA runtime correctness claim is made. Source inspection confirmed the
block-boundary checkpoint/recompute structure, while also confirming different
alignment, scoring, tie, and CIGAR semantics.

Architecture C is selected: L1-L5 code and semantics remain in-tree; Accelign
may influence forward batching/length-bin/tile scheduling and G3SA may influence
checkpoint layout only. No upstream implementation was copied or linked. The
four runtime probes total 1.04 seconds of wall-time upper bound, B3 remains
closed by Amdahl, and Phase 5 is active.
