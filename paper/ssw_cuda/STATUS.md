# SSW-CUDA Program Status

```text
execution_start_head = 9f87aace6d96cf8142e3816299f04defae5710e4
execution_branch = gasal2-kcnq1ot1-focused-review
active_phase = 13
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
phase_5_implementation_commit = ce94f5bddad4c16bc995258fa7b563d4bb8a969b
phase_5_preselect_execution_epoch = 1
phase_5_status = pass
phase_6_implementation_commit = e41f76d0d67661b56bba915dd850d07849379cf6
phase_6_forward_execution_epoch = 1
phase_6_status = pass
phase_7_implementation_commit = 750fb29e7c0c989046947f86d2f5648f94fa3754
phase_7_execution_source_commit = f3ffe9b188c43ef0bff78a903176f991c493f2b8
phase_7_execution_epoch = 2
phase_7_measurement_repairs = 2
phase_7_analysis_corrections = 2
phase_7_status = no_go
phase_8_status = not_run_phase7_no_go
phase_9_status = not_run_phase7_no_go
phase_10_status = not_run_phase7_no_go
phase_11_status = not_run_phase7_no_go
phase_12_status = not_run_phase7_no_go
phase_13_status = pass
ssw_cpu_oracle_epoch = 2
ssw_cuda_program_epoch = 1
bioinformatics_b3_track = closed_amdahl
engineering_track = closed_phase7_forward_hybrid_no_go
l8_contract_status = diagnostic_only
final_decision = ssw_cuda_forward_or_reverse_checkpoint_only
final_certification = aggregate_checker_passed
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
four runtime probes total 1.04 seconds of wall-time upper bound, B3 remained
closed by Amdahl, and Phase 5 then became active.

Phase 5 implemented an in-tree int32 CUDA correctness checkpoint for the
frozen SSE2 striped L1 column frontier and deterministic L2 selection. The
first eight-case smoke exposed one scalar-versus-striped difference at the
last column of the periodic-repeat case (CPU 35, scalar 25). The single
mechanism repair reproduced the frozen stripe padding, saturation, lazy-F and
signed byte stop behavior without adding any case-specific branch.

The formal execution started from clean implementation commit `ce94f5b` and
completed all 29 preregistered batch attempts without retry. The 623 supported
primary GPU tasks had zero column-vector and scoreInfo mismatches. All four
frozen unsupported inputs and eight API capacity/configuration/OOM probes
failed closed. The fixed 16-case subset was byte-stable for ten repeats and
identical on both RTX 4090 devices. There were no technical failures,
unexpected fallbacks, false negatives, extras, order differences, or reason
differences. The hq10/hq11 CPU digests remained `4cdb83f5d1b579b4` and
`fcd5135e90526dfa`.

All 623 primary authority calls selected the byte8 final path; the frozen
boundary inputs were not supplemented after observing this result. This is
L1/L2 regression evidence only, not fresh-holdout promotion. The default CPU
binary remains unchanged, B3 remains closed by Amdahl, and Phase 6 is now
active for the independent L3 forward-endpoint implementation.

Phase 6 implemented the exact L3 forward tuple on GPU from clean implementation
commit `e41f76d`: `score1`, `ref_end1`, `read_end1`, `score2`, `ref_end2`, and
the final byte/word path. The implementation shares the frozen striped
recurrence but preserves the distinct full-forward overflow and endpoint
semantics. It contains no CPU endpoint call, fallback, or case-specific branch.

All 31 preregistered attempts completed without retry. The 625 primary cases
and all 841 supported task executions had zero endpoint and standalone-reducer
mismatch. The two Phase 2 frozen CPU full-forward vectors reduced to their
exact hq10/hq11 endpoints. All eight forward and five reducer API probes failed
closed. The fixed 18-case subset was stable across ten repeats and identical on
both RTX 4090 devices. There were zero technical failures, timeouts, OOMs,
fallbacks, and CPU endpoint calls. The conservative GPU wall upper bound was
8.468333049 seconds, below the fixed 24-hour budget.

Primary execution contained 591 byte8 and 34 word16 endpoints. There were 94
diagnostic differences between Phase 5 pre-align columns and Phase 6
full-forward columns. Those differences are expected evidence that the two
frozen CPU routines are not interchangeable; they do not weaken or overwrite
the passed L1 or L3 contracts. No fresh holdout or application panel was run,
the default CPU binary remains unchanged, B3 remains closed by Amdahl, and
Phase 7 is now active for the bounded forward-hybrid performance checkpoint.

Phase 7 combined exact GPU L1-L3 with selected-only CPU L4/L5. The v1
execution stopped before attempt 26 because its runner did not apply the
Phase 1 uppercase normalization when validating a repeat-masked FASTA. The 25
receipts remain immutable. Repair 1 froze a complete v2 epoch; no v1 result was
reused.

Epoch v2 produced 27 receipts: 26 complete attempts, one fail-closed technical
failure, and zero retries. All 24 consumed holdout regressions and the two
completed development performance observations had clean score-, stability-,
and Nt-ranked clustered Top-5 comparisons. CPU pre-align and forward calls
were zero; the 26 complete attempts made 192,095 matched reverse-start and
banded-traceback calls with no fallback.

The overhead observation took 1.179151 seconds versus its historical CPU
reference of 0.114453 seconds (`0.097064x`). The 2 Mb medium observation took
1328.082524 seconds versus 61.121143 seconds (`0.046022x`); GPU pre-align alone
used 1210.617832 seconds. The first chr21 observation ran 5233.500342 seconds,
selected 665,582 attempts, and then stopped on one reproducible continuation
contract failure after 665,562 CPU continuations. It was not a timeout, OOM,
fallback, or environment failure.

The two permitted measurement repairs are exhausted. Two offline-only
analysis corrections preserved failed comparison roots while binding the
unique TFOsorted file and the actual frozen Phase 2 segmented comparator; they
started no backend attempt and changed no measurement. Phase 7 is `no_go` with
reason `forward_hybrid_implementation_contract_failure`. Phase 8-12 were not
authorized, no fresh holdout or 50 x 668 application panel was run, B3 remains
closed, and Phase 13 entered the final audit.

Phase 13 completed the claim-to-evidence map, limitations, release checklist,
manuscript handoff, and 28-row completion audit. The aggregate checker replays
the final Phase 0-7 checkers, binds every cited evidence SHA-256, verifies the
frozen CPU oracle binary and source commit, confirms Phase 8-12 result artifacts
are absent, and requires a clean certification commit. The unique final
decision is `ssw_cuda_forward_or_reverse_checkpoint_only`.
