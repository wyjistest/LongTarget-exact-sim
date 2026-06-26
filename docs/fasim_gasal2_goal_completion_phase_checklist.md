# Fasim GASAL2 Goal Completion Phase Checklist

This document is the short execution checklist for closing the active
Fasim/GASAL2 goal. It is intentionally narrower than the evidence roadmap:

- Detailed evidence ledger: `docs/fasim_gasal2_goal_completion_roadmap.md`
- Operational close runbook:
  `docs/fasim_gasal2_goal_completion_runbook.md`
- Phase-by-phase completion ladder:
  `docs/fasim_gasal2_goal_completion_execution_ladder.md`
- Canonical phase roadmap:
  `docs/fasim_gasal2_goal_completion_phase_roadmap.md`
- Concise close plan:
  `docs/fasim_gasal2_goal_completion_close_plan.md`
- Full phase plan: `docs/fasim_gasal2_goal_completion_phase_plan.md`
- Current completion decision gate: `make check-fasim-gasal2-roadmap-current-state`

The active goal is not complete by default. It can close only through one of
two explicit paths.

## Completion Paths

```text
Path A: scoped completion
  Meaning:
    The user accepts the narrowed product as the delivered goal.

  Scope:
    default-off short-query/H19 top5 GASAL2 artifact
    MEG3-like complete-record grouping where claimed
    archive-first restored output where claimed

  Not included:
    broad aligner.Align replacement
    universal scoreInfo/preAlign replacement
    long-query NEAT1/MALAT1 replacement
    GPU endpoint/CIGAR/traceback/output authority

Path B: broad completion
  Meaning:
    The original broad objective is completed.

  Required proof:
    full row-set/digest equality
    runtime win over CPU authority path
    scoreInfo/preAlign work reduced or replaced
    Align-side work reduced or replaced
    fallback accounting clean
    no GPU endpoint/CIGAR/traceback/output authority
```

If neither path passes, keep:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Current Path A decision:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
active_goal_completion_status = complete_scoped_path_a
completion_guard_cleared = 1
must_not_call_update_goal_complete = 0
```

## Phase 0: Reproducibility

Purpose:

```text
Make the GASAL2/Fasim bridge rebuildable from a clean checkout.
```

Do:

- Keep GASAL2 local changes tracked as a patch or setup target.
- Keep `setup-gasal2` and `build-fasim-gasal2` rebuildable.
- Keep CUDA version, SM arch, and GASAL2 compile-time limits visible.

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase0-reproducibility
```

Stop if:

```text
Any claimed result depends on untracked .tmp/GASAL2 source edits or a
machine-local binary.
```

## Phase 1: Scoped Product Contract

Purpose:

```text
Decide whether Path A is allowed to close the active goal.
```

Do:

- Keep the scoped product contract explicit.
- Keep non-claims explicit.
- Ask for explicit user acceptance before using Path A as completion.
- If accepted, record that acceptance in the acceptance document and rerun the
  scoped gates.

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase1-scoped-product
make check-fasim-gasal2-roadmap-path-a-scoped-acceptance
```

Path A may continue only if:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

Current state:

```text
accepted
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

## Phase 2: Full-Output Equivalence Baseline

Purpose:

```text
Keep restored full output equivalent before claiming any full-output speedup.
```

Do:

- Preserve complete row-set equality for restored TFOsorted output.
- Keep chr22 and chr1 evidence separate from top5-only artifacts.
- Measure convert/output wall time separately from whole-run wall time.

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase2-equivalence-first-convert
```

Stop if:

```text
Rows, digest, ordering contract, or restored output semantics drift.
```

## Phase 3: Pre-Convert CPU Reduction

Purpose:

```text
Reduce CPU materialization/convert cost without changing the complete row set.
```

Do:

- Test only proof-first reducers.
- Compare missing rows, extra rows, and task-frontier safety before runtime
  claims.
- Keep failed reducers as stopped/default-off evidence.

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase3-preconvert-prune
make check-fasim-gasal2-roadmap-phase3-cigar-nt-prefilter-design
```

Promote only if:

```text
missing_rows = 0
extra_rows = 0
task_frontier_safe = 1
convert_wall_seconds < Phase 2 convert wall
```

Current state:

```text
current CIGAR NT prefilter line is correctness-clean but performance no-go
```

## Phase 4: Sort/Top-N Optimization

Purpose:

```text
Optimize row ordering/top-N only after profiling shows it is a real bottleneck.
```

Do:

- Defer until Phase 2/3 profiling says sort/filter dominates.
- Preserve comparator and tie behavior exactly.

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase4-sort-topn
```

Stop if:

```text
Sort/top-N is not a material share of remaining wall time.
```

## Phase 5: Archive Artifact

Purpose:

```text
Provide a compact artifact that can restore the claimed output on demand.
```

Do:

- Keep archive manifest, reference digests, and restore command explicit.
- Verify restored output equality for every claimed archive row.
- Treat archive as Path A delivery and as a possible Path B output accelerator.

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase5-archive-artifact
```

Stop if:

```text
Archive restore cannot reproduce the claimed TFOsorted/full output.
```

## Phase 6: Workload Matrix

Purpose:

```text
Prevent hidden overclaiming across workloads.
```

Do:

- Record each workload as scoped, unclaimed, fallback-heavy, blocked, or broad.
- Add `contract=broad_replacement` only after Phase 7 broad gate passes.
- Keep top5-only, archive-only, full-output, and broad-replacement rows
  separate.

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase6-workload-matrix
```

Path A matrix rule:

```text
Only scoped rows may be claimed unless the user accepts the scoped product.
```

Path B matrix rule:

```text
At least one broad_replacement row must pass all broad fields before broad
completion can be claimed.
```

## Phase 7: Broad Replacement Restart

Purpose:

```text
Complete the original broad objective if scoped completion is not accepted.
```

Do:

- Do not continue stopped broad sources.
- Start only a materially different architecture if pursuing Path B.
- Prove CPU-authority replay before accepting runtime wins.
- Reduce both scoreInfo/preAlign work and Align-side work.

Required broad gate:

```text
full_rows_equal = true
digest_match = true
runtime_speedup > 1.0
scoreinfo_reduced = true
align_side_reduced = true
fallback_accounting_clean = true
gpu_endpoint_cigar_traceback_output_authority = false
```

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase7-current-broad-stop-decision
```

Current state:

```text
current broad sources are stopped/no-go
v4 scoreInfo-native GPU design defined
v4 legacy-byte scoreInfo host-contract smoke clean
v4 GPU legacy-byte scoreInfo first1 shadow clean
v4 GPU legacy-byte scoreInfo source replay first1 clean
v4 GPU legacy-byte scoreInfo source first64 broad gate no-go
v5 fused scoreInfo consumer design defined
v5 fused scoreInfo consumer implementation plan defined
v5 post-scoreInfo descriptor scaffold no-go
v5 true pre-scoreInfo descriptor source design defined
v5 true pre-scoreInfo descriptor source env scaffold fail-closed
v5 true pre-scoreInfo descriptor source strict runtime smoke pass
v5 CPU-authority replay first1 smoke pass
v5 CPU-authority replay first64 broad gate no-go
next Path B gate = pre_d2h_output_inert_proof_search_first1_export
post-v5.3 pre-D2H proof-search design defined
v5 CUDA descriptor emission design defined
```

Do not spend more work on:

```text
current replacement-consumer source
attempt-consumer source
emission-only source
frontier early-stop source
Gate C current source
Phase 7 v3 current seed/index source
```

## Phase 8: Completion Decision

Purpose:

```text
Make the only valid close/no-close decision for the active goal.
```

Path A close procedure:

```bash
make check-fasim-gasal2-roadmap-phase0-reproducibility
make check-fasim-gasal2-roadmap-phase1-scoped-product
make check-fasim-gasal2-roadmap-path-a-scoped-acceptance
make check-fasim-gasal2-roadmap-phase5-archive-artifact
make check-fasim-gasal2-roadmap-phase6-workload-matrix
make check-fasim-gasal2-roadmap-phase8-completion-decision
```

Then close only if:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

Path B close procedure:

```bash
make check-fasim-gasal2-roadmap-current-state
make check-fasim-gasal2-roadmap-phase8-completion-decision
```

Then close only if:

```text
broad_gate_pass = 1
claimed_broad_replacement_rows > 0
must_not_call_update_goal_complete = 0
```

Current Phase 8 decision:

```text
final_goal_decision = complete_scoped_path_a
broad_objective_status = open
scoped_product_status = accepted
scope_or_broad_design_decision_required = 0
path_a_user_acceptance_required = 0
path_b_new_broad_architecture_required = 0
completion_guard_cleared = 1
goal_completion_status = complete
must_not_call_update_goal_complete = 0
```

## Recommended Next Move

The shortest valid completion route is Path A:

```text
1. Ask whether the user accepts scoped completion.
2. If accepted, record acceptance in the Path A acceptance document.
3. Rerun Phase 0, Phase 1, Phase 5, Phase 6, and Phase 8 gates.
4. Close the goal as scoped completion only if the gates allow it.
```

If the user does not accept Path A, the goal remains Path B:

```text
1. Do not continue stopped current broad sources.
2. Use docs/fasim_gasal2_phase7_broad_restart_v3_candidate_certificate_design.md
   as the v3 candidate-certificate design checkpoint.
3. Treat docs/fasim_gasal2_phase7_broad_restart_v3_descriptor_source_smoke.md
   as a stopped descriptor-source runtime checkpoint.
4. Treat docs/fasim_gasal2_phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke.md
   as a stopped pre-scoreInfo descriptor-source checkpoint.
5. Treat docs/fasim_gasal2_phase7_broad_restart_v3_certificate_smoke.md as the
   stopped first certificate checkpoint.
6. Treat docs/fasim_gasal2_phase7_broad_restart_v3_all_column_certificate_smoke.md
   as the stopped all-column scoreInfo-reducing certificate checkpoint.
7. Treat docs/fasim_gasal2_phase7_broad_restart_v3_all_column_replay_stop.md
   as the stopped all-column replay decision.
8. Do not continue to first64 because the current all-column certificate
   overgenerates attempts and has a preflight CPU replay no-go.
9. Do not run all-column CPU replay; it would require 168,730,848 candidate
   Align attempts against 2,872 reference Align attempts.
10. Treat docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_design.md
   as the stopped bounded narrow certificate design checkpoint.
11. Treat docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_smoke.md
   as the stopped bounded-probe runtime checkpoint.
12. Do not continue the bounded narrow probe to first64 because it has
   candidate certificate false negatives and missing required attempts.
13. Treat docs/fasim_gasal2_phase7_broad_restart_v3_real_narrow_certificate_coverage_proof.md
   as the stopped exact-column coverage candidate checkpoint.
14. Do not continue the existing exact-column GPU scoreInfo source because
   non-opt-in launch fails and smem opt-in has scoreInfo mismatches.
15. Treat docs/fasim_gasal2_phase7_broad_restart_v3_next_source_design.md
   as the source-family design checkpoint.
16. Treat docs/fasim_gasal2_phase7_broad_restart_v3_next_source_smoke.md
   as the stopped first seed-certificate runtime checkpoint.
17. Treat docs/fasim_gasal2_phase7_broad_restart_v3_strong_seed_smoke.md
   as the stopped strong-seed runtime checkpoint:
     task/scoreInfo coverage clean
     candidate_certificate_false_negatives = 0
     missing_required_attempts > 0
18. Do not continue the strong-seed source to replay while required attempt
   coverage is missing.
19. Treat docs/fasim_gasal2_phase7_broad_restart_v3_attempt_coverage_seed_smoke.md
   as the attempt-coverage checkpoint:
     cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
     candidate_certificate_false_negatives = 0
     missing_required_attempts = 0
     candidate_attempts below all-column replay scale
     candidate_attempts_below_reference = 0
     candidate_min_cover_positions_below_reference = 1
     oracle_min_cover_uses_legacy_attempt_windows = 1
20. Treat docs/fasim_gasal2_phase7_broad_restart_v3_oracle_min_cover_replay_smoke.md
   as the stopped oracle runtime checkpoint:
     candidate_align_attempts = 463
     reference_align_attempts = 2,872
     missing_rows = 11
     extra_rows = 9
     phase7_broad_restart_v3_gate_v3_2_shape_probe_pass = 0
21. Do not continue the oracle min-cover replay shape to first64 because full
   output rows differ.
22. Treat docs/fasim_gasal2_phase7_broad_restart_v3_seed_path_stop.md as the
   stop checkpoint for the current seed/index path:
     phase7_broad_restart_v3_seed_path_stop =
       current_seed_index_path_stopped
     phase7_broad_restart_v3_may_continue_to_first64 = 0
23. Treat docs/fasim_gasal2_phase7_broad_restart_v4_scoreinfo_native_design.md
   as the current Path B design checkpoint:
     phase7_broad_restart_v4_scoreinfo_native_design = defined
     phase7_broad_restart_v4_next_gate = legacy_byte_scoreinfo_shadow_first1
24. Treat docs/fasim_gasal2_phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke.md
   as the current host-contract checkpoint:
     phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke =
       host_contract_clean_needs_gpu
     phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_rows_equal = 1
     phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_order_equal = 1
     phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_attempt_windows_equal = 1
     phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 0
     phase7_broad_restart_v4_host_contract_pass = 1
25. Treat docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke.md
   as the current GPU first1 shadow checkpoint:
     phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke =
       gpu_contract_clean_first1
     phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 718
     phase7_broad_restart_v4_gate_v4_1_pass = 1
     phase7_broad_restart_v4_runtime_next_gate =
       gpu_legacy_byte_scoreinfo_source_first1_cpu_authority_replay
26. Treat docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke.md
   as the current GPU first1 source replay checkpoint:
     phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke =
       cpu_authority_replay_clean_first1
     phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_digest_match = 1
     phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempts = 2008
     phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_reference_align_attempts = 2872
     phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempt_reduction = 864
     phase7_broad_restart_v4_gate_v4_2_pass = 1
     phase7_broad_restart_v4_runtime_next_gate =
       gpu_legacy_byte_scoreinfo_source_first64_broad_gate
27. Treat docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate.md
   as the current v4 first64 broad-gate no-go checkpoint:
     phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate =
       correctness_clean_performance_no_go
     baseline_wall_seconds = 86.358386
     candidate_wall_seconds = 134.744406
     candidate_vs_baseline = 0.640905
     digest_match = 1
     candidate_realpath_extend_align_attempts = 140087
     reference_align_attempts = 211976
     align_attempt_reduction = 71889
     phase7_broad_restart_v4_gate_v4_3_pass = 0
     phase7_broad_restart_v4_runtime_next_gate =
       different_gpu_execution_design_or_path_a_scope_decision
28. Do not continue the current v4 source replay implementation as a broad
   completion path because first64 wall time is slower than CPU baseline.
29. Treat docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_design.md
   as the current different GPU execution design checkpoint:
     phase7_broad_restart_v5_fused_scoreinfo_consumer_design = defined
     phase7_broad_restart_v5_status = design_only
     phase7_broad_restart_v5_design_family =
       fused_gpu_scoreinfo_to_candidate_attempt_descriptors
     phase7_broad_restart_v5_differs_from_v4_source_replay = 1
     phase7_broad_restart_v5_next_gate =
       fused_scoreinfo_consumer_descriptor_contract_first1
30. Treat docs/superpowers/plans/2026-06-13-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer.md
   as the current v5 implementation plan:
     phase7_broad_restart_v5_implementation_plan = defined
     phase7_broad_restart_v5_runtime_first_gate =
       fused_scoreinfo_consumer_descriptor_contract_first1
     Task 1: Env, Stats, And Default-Off Telemetry
     Task 2: Descriptor Contract Runtime Smoke
     Task 3: CPU-Authority Replay First1 Gate
     Task 4: Roadmap Checkpoint And Current-State Wiring
     Task 5: First64 Broad Gate Characterization
     make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-implementation-plan
31. Do not continue v4 source replay as the broad path. v5 must avoid
   materializing the full host-visible scoreInfo row stream and must emit
   compact candidate attempt descriptors for CPU-authority `aligner.Align()`.
32. Treat docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.md
   as the strict Gate v5.1 runtime pass checkpoint:
     phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke =
       gate_v5_1_pass_first1
     phase7_v5_true_pre_scoreinfo_descriptor_source_active = 1
     phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo = 1
     phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced = 1
     phase7_v5_true_pre_scoreinfo_descriptor_source_descriptor_false_negatives = 0
     phase7_v5_true_pre_scoreinfo_descriptor_source_missing_required_attempts = 0
     phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass = 1
     existing_v4_gpu_source_materializes_host_visible_scoreinfo_rows = 1
     existing_cuda_api_emits_prealign_cuda_peaks_not_attempt_descriptors = 1
     do_not_rebrand_v4_source_replay_as_v5 = 1
     next_required_gate = phase7_gate_v5_2_cpu_authority_replay_first1
     make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke
33. Treat docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_smoke.md
   as the strict Gate v5.2 runtime pass checkpoint:
     phase7_broad_restart_v5_cpu_authority_replay_smoke =
       gate_v5_2_pass_first1
     root_cause_fix = legacy_float_identity_cutlength_descriptor_generation
     phase7_v5_cpu_authority_replay_source_is_pre_scoreinfo = 1
     phase7_v5_cpu_authority_replay_scoreinfo_prealign_reduced = 1
     phase7_v5_cpu_authority_replay_full_rows_equal = 1
     phase7_v5_cpu_authority_replay_digest_match = 1
     phase7_v5_cpu_authority_replay_candidate_align_attempts = 2008
     phase7_v5_cpu_authority_replay_reference_align_attempts = 2872
     phase7_broad_restart_v5_gate_v5_2_pass = 1
     next_required_gate = different_gpu_execution_design_or_path_a_scope_decision
     make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-smoke

34. Treat docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate.md
   as the strict Gate v5.3 no-go checkpoint:
     phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate =
       correctness_clean_performance_no_go
     phase7_broad_restart_v5_first64_candidate_vs_baseline = 0.706009
     phase7_broad_restart_v5_first64_missing_required_attempts = 624
     phase7_broad_restart_v5_runtime_next_gate =
       different_gpu_execution_design_or_path_a_scope_decision
     make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-first64-broad-gate
34b. Treat docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md
   and docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export.md
   as the current proof-search checkpoint:
     phase7_post_v5_3_pre_d2h_output_inert_proof_search_design = defined
     phase7_post_v5_3_pre_d2h_output_inert_proof_search_status = first1_export_pass
     phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export = pass
     phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_implement = 1
     phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion = 0
     next_required_gate = pre_d2h_output_inert_proof_acceptance_first1
     current_next_pr = fasim: audit pre-D2H output-inert proof-search first1
     runtime_reduction_enabled = 0
     make check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-design
     make check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-first1-export
35. Treat docs/fasim_gasal2_phase7_broad_restart_v5_cuda_descriptor_emission_design.md
   as the next design artifact:
     phase7_broad_restart_v5_cuda_descriptor_emission_design = defined
     phase7_broad_restart_v5_cuda_descriptor_emission_status = design_only
     new_cuda_api = prealign_cuda_emit_legacy_byte_attempt_descriptors
     output_contract = compact_attempt_descriptors_not_scoreinfo_rows
     host-visible full legacy scoreInfo row stream = forbidden
     CPU aligner.Align() authority replay = 1
     GPU endpoint/CIGAR/traceback/output authority = 0
     next_gate = runtime_smoke_true_pre_scoreinfo_descriptor_source_first1
     make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-descriptor-emission-design
35. Continue Path B only with a different GPU execution design that proves:
     scoreinfo_rows_equal = true
     scoreinfo_order_equal = true
     scoreinfo_attempt_windows_equal = true
     full_rows_equal = true
     digest_match = true
     triplex_mismatches = 0
     candidate_align_attempts < reference_align_attempts
     real_pre_scoreinfo_reducer_proven = 1 before broad promotion
     candidate_wall_seconds < baseline_wall_seconds
35. Add `contract=broad_replacement` only after a future first64 path passes with full
   equality, wall-time win, scoreInfo/preAlign reduction, Align-side
   reduction, and fallback accounting clean.
36. Keep CPU aligner.Align() as authority until the broad gate passes.
```
