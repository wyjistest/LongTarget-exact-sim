# Fasim GASAL2 Goal Completion Execution Ladder

This document is the phase-by-phase route for finishing the active
Fasim/GASAL2 goal without moving the success line after partial milestones.

It is intentionally operational:

```text
What does each phase do?
What evidence closes the phase?
What stops the phase?
Which path can finally close the goal?
```

## Phase At A Glance

Use this table as the first entry point before doing any more GASAL2 work.
Each phase has one job, one exit gate, and one reason to stop. The goal can
close only after Phase 8 says the selected path is complete.

| Phase | Job | Exit Gate | Current State | Completion Role |
| --- | --- | --- | --- | --- |
| 0 | Make GASAL2/Fasim reproducible from a clean checkout | `setup-gasal2`, `build-fasim-gasal2`, and reproducibility checks pass without machine-local edits | Ready, maintain | Required for Path A and Path B |
| 1 | Decide whether scoped delivery is acceptable | User acceptance is recorded for the scoped product contract | Not accepted yet | Can close only Path A |
| 2 | Keep full restored output equivalent | chr22/chr1 restored rows and digests match CPU-authority output | Ready, maintain | Foundation for full-output claims |
| 3 | Reduce pre-convert CPU work only if row-safe | `missing_rows=0`, `extra_rows=0`, and wall time beats Phase 2 | Current CIGAR NT prefilter is performance no-go | Optional Path B helper |
| 4 | Optimize sort/top-N only if it becomes dominant | Same comparator/tie/top-N behavior with lower sort/filter wall time | Deferred | Optional output-side helper |
| 5 | Keep compact archive restore valid | Archive manifest and restored output equality checks pass | Ready, maintain | Required for Path A archive delivery |
| 6 | Keep workload claims explicit | Matrix has only truthful scoped/broad/fallback/blocked rows | Scoped rows only; no broad row | Required claim ledger |
| 7 | Finish original broad objective if Path A is not accepted | First1 and first64 broad gates pass with equality, speedup, scoreInfo/preAlign reduction, and Align-side reduction | v4 source replay first64 is performance no-go; v5 fused scoreInfo consumer design is defined | Required for Path B |
| 8 | Make the close/no-close decision | Path A acceptance gates pass or Path B broad gate passes | Not complete | Only phase that can justify closing the active goal |

Recommended order:

```text
1. Keep Phase 0 green.
2. Ask whether Path A scoped completion is acceptable.
3. If Path A is accepted, rerun Phase 1, Phase 5, Phase 6, and Phase 8.
4. If Path A is not accepted, continue Phase 7 only with a different GPU
   execution design; the current v4 source replay first64 gate is no-go.
5. Run Phase 8 only after Path A acceptance or a passing Path B broad gate.
```

## Completion Rule

The goal can close only through one of two explicit paths.

```text
Path A: scoped completion
  The user explicitly accepts the narrowed product as the delivered goal.

  Product:
    short-query/H19 top5 GASAL2 artifact
    MEG3-like complete-record grouping where claimed
    archive-first restored output where claimed

  Not claimed:
    aligner.Align replacement
    universal scoreInfo/preAlign replacement
    long-query NEAT1/MALAT1 replacement
    GPU endpoint/CIGAR/traceback/output authority

Path B: broad completion
  The original broad objective is completed.

  Required:
    full row-set/digest equality
    runtime win over the CPU authority path
    scoreInfo/preAlign work reduced or replaced
    Align-side work reduced or replaced
    fallback accounting clean
    CPU aligner.Align() remains semantic authority unless separately proven
```

If neither path passes, keep:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Current Pointer

The active broad path is currently in Phase 7, after the v5 true
pre-scoreInfo descriptor-source strict runtime smoke and v5.2 CPU-authority
replay smoke passed first1:

```text
phase7_broad_restart_v4_scoreinfo_native_design = defined
phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate =
  correctness_clean_performance_no_go
phase7_broad_restart_v5_fused_scoreinfo_consumer_design = defined
phase7_broad_restart_v5_implementation_plan = defined
phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke =
  post_scoreinfo_descriptor_scaffold_no_go
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design = defined
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_env_scaffold =
  fail_closed_no_source
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke =
  gate_v5_1_pass_first1
phase7_broad_restart_v5_gate_v5_1_pass = 1
phase7_broad_restart_v5_cpu_authority_replay_smoke =
  gate_v5_2_pass_first1
phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate =
  correctness_clean_performance_no_go
phase7_broad_restart_v5_gate_v5_2_pass = 1
phase7_broad_restart_v5_gate_v5_3_pass = 0
phase7_broad_restart_v5_cuda_descriptor_emission_design = defined
phase7_broad_restart_v5_cuda_descriptor_emission_status = design_only
new_cuda_api = prealign_cuda_emit_legacy_byte_attempt_descriptors

What is clean:
  current v3 seed/index path is stopped
  v4 design selects a legacy scoreInfo-compatible GPU source
  host-column legacy scoreInfo reconstruction smoke is clean
  GPU legacy-byte scoreInfo first1 shadow is clean
  GPU legacy-byte scoreInfo first1 source replay is clean
  GPU legacy-byte scoreInfo first64 source replay digest is clean
  all-attempt early-stop replay remains the CPU-authority consumer target

What is not clean:
  first64 wall-time gate is no-go
  no broad_replacement matrix row
  v5 design selects the next different GPU execution shape
  v5 post-scoreInfo runtime scaffold does not reduce CPU scoreInfo/preAlign
  v5 true pre-scoreInfo descriptor-source first1 smoke is clean
  v5 CPU-authority replay first64 broad gate is no-go

Next gate:
  different_gpu_execution_design_or_path_a_scope_acceptance

Next implementation artifact:
  different GPU execution design or explicit Path A scoped acceptance
```

Do not continue the current seed/index path to first64. Do not continue the v4
source replay implementation as a broad-completion path. The next Path B
runtime must emit descriptors before CPU scoreInfo/preAlign work, or the active
goal must return to the Path A scope decision. Do not rebrand v4 host-visible
scoreInfo row replay as v5.

## Phase 0: Reproducibility Foundation

Purpose:

```text
Make every later GASAL2/Fasim claim reproducible from a clean checkout.
```

Do:

```text
track the GASAL2 local patch
pin the upstream GASAL2 commit
keep setup/build targets idempotent
make CUDA version, SM arch, GASAL2_MAX_QUERY_LEN, and N_CODE visible
remove dependence on machine-local .tmp/GASAL2 edits
```

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase0-reproducibility
make check-fasim-gasal2-reproducible-setup
make setup-gasal2
make build-fasim-gasal2
```

Stop if:

```text
Any claimed result depends on an untracked GASAL2 source edit or local binary.
```

Completion role:

```text
mandatory for Path A
mandatory for Path B
```

## Phase 1: Completion Contract

Purpose:

```text
Decide whether the current scoped product is enough, or whether the original
broad objective remains active.
```

Do for Path A:

```text
present the scoped product contract
record explicit user acceptance
record exact commands and claimed workloads
state non-claims next to claims
```

Do for Path B:

```text
record that scoped completion is not accepted
continue to Phase 7 broad restart
do not close from top5-only or archive-only evidence
```

Exit gate for Path A:

```bash
make check-fasim-gasal2-roadmap-phase1-scoped-product
make check-fasim-gasal2-roadmap-path-a-scoped-acceptance
```

Path A may close only if:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
```

Stop if:

```text
The user still wants broad scoreInfo/preAlign/Align replacement or material
broad acceleration. Then Path A cannot close the goal.
```

Completion role:

```text
Path A gate only
not sufficient for Path B
```

## Phase 2: Full-Output Equivalence Baseline

Purpose:

```text
Keep full TFOsorted/restored output correct before claiming any full-output
speedup.
```

Do:

```text
preserve chr22 and chr1 restored row-set equality
separate full-output evidence from top5-only evidence
itemize convert/output time and whole-run time
keep CPU output authority
```

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase2-equivalence-first-convert
make check-fasim-gasal2-archive-first-output
make check-fasim-gasal2-convert-cpu-breakdown
```

Stop if:

```text
Rows, digest, restored output semantics, or ordering contract drift.
```

Completion role:

```text
Path A support if scoped archive output is accepted
Path B foundation for any full-output claim
```

## Phase 3: Pre-Convert CPU Reduction

Purpose:

```text
Reduce CPU materialization/convert work without changing the complete row set.
```

Do:

```text
test only proof-first reducers
compare missing rows and extra rows before runtime claims
prove task-local frontier safety
keep failed reducers stopped/default-off
```

Exit gate for a future reducer:

```text
missing_rows = 0
extra_rows = 0
task_frontier_safety = safe
real_prune_proof_gate = pass
chr22 and chr1 convert wall lower than Phase 2
```

Stop if:

```text
The reducer preserves top5 but changes the full row set.
The reducer reduces work but does not beat Phase 2 wall time.
The proof depends on final output rows that are known only after CPU work.
```

Current status:

```text
current CIGAR NT prefilter line is correctness-clean but performance no-go
```

Completion role:

```text
optional Path B helper
not sufficient to complete the goal alone
```

## Phase 4: Sort/Top-N Optimization

Purpose:

```text
Optimize ordering/top-N only after profiling shows it is a real bottleneck.
```

Do:

```text
defer until Phase 2/3 profiling shows sort/filter dominates
preserve comparator behavior
preserve tie behavior
preserve unique behavior
preserve top-N boundary behavior
```

Exit gate:

```text
same kept row set
same comparator/tie behavior
materially lower sort/filter wall time
```

Stop if:

```text
Partial selection changes row identity, tie behavior, or the top-N boundary.
```

Completion role:

```text
optional output-side optimization
not sufficient to complete the goal alone
```

## Phase 5: Archive Artifact

Purpose:

```text
Store the smallest sufficient artifact and restore TFOsorted on demand.
```

Do:

```text
validate archive manifest
validate reference digests
document restore command
verify restored output equality for every claimed mode
keep archive format independent of rerunning Fasim
```

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase5-archive-artifact
make check-fasim-gasal2-archive-manifest-parser
make check-fasim-tfo-archive-integrity-parser
```

Stop if:

```text
The archive cannot restore the claimed output without rerunning Fasim.
The manifest omits reference identity needed for later restore.
```

Completion role:

```text
required for Path A archive delivery
useful Path B output accelerator
not a broad replacement by itself
```

## Phase 6: Workload Matrix

Purpose:

```text
Prevent hidden overclaiming across workloads.
```

Do:

```text
record every claimed workload
separate scoped, unclaimed, fallback-heavy, blocked, and broad rows
add contract=broad_replacement only after Phase 7 broad gate passes
keep top5-only, archive-only, full-output, and broad-replacement rows separate
```

Path A exit gate:

```text
all scoped claimed rows pass
blocked and unclaimed rows remain explicit
no broad_replacement claim is implied
```

Path B exit gate:

```text
at least one claimed broad_replacement row
row_equal = true
digest_match = true
speedup > 1.0
fallbacks = 0 for the claimed GPU path
scoreinfo_reduced = true
align_side_reduced = true
```

Stop if:

```text
A fallback-heavy, output-drift, or top5-only row is presented as broad clean.
```

Completion role:

```text
mandatory claim ledger for Path A
mandatory claim ledger for Path B
```

## Phase 7: Broad Replacement Restart

Purpose:

```text
Complete the original broad objective if scoped completion is not accepted.
```

Current status:

```text
current replacement-consumer source: stopped
attempt-consumer source: stopped
emission-only source: stopped
frontier early-stop source: stopped
all-attempt early-stop alone: not broad completion
Gate C current source: stopped
v3 all-column certificate: stopped by candidate-attempt explosion
v3 bounded narrow probe: stopped by missing required attempts
existing exact-column GPU scoreInfo source: stopped by launch/equivalence failure
v4 GPU legacy-byte scoreInfo source replay: correctness clean, performance no-go
v5 post-scoreInfo descriptor scaffold: no-go because CPU scoreInfo/preAlign is
  not reduced
v5 true pre-scoreInfo descriptor-source strict runtime smoke:
  no-go until CUDA descriptor emission exists
v5 CUDA descriptor-emission design:
  defined, design_only, not completion
```

The next Path B attempt must be materially different from stopped sources:

```text
compact GPU attempt-descriptor emission before CPU scoreInfo/preAlign
CPU aligner.Align() authority replay
no GPU endpoint/CIGAR/traceback/output/digest authority
measured reduction of scoreInfo/preAlign work
measured reduction of Align-side work
first64 broad wall-time win
```

### Gate v5.0: CUDA Descriptor-Emission Design

Current checkpoint:

```text
document =
  docs/fasim_gasal2_phase7_broad_restart_v5_cuda_descriptor_emission_design.md
phase7_broad_restart_v5_cuda_descriptor_emission_design = defined
phase7_broad_restart_v5_cuda_descriptor_emission_status = design_only
new_cuda_api = prealign_cuda_emit_legacy_byte_attempt_descriptors
input_contract = encoded_targets_plus_min_scores_plus_task_metadata
output_contract = compact_attempt_descriptors_not_scoreinfo_rows
host-visible full legacy scoreInfo row stream = forbidden
CPU aligner.Align() authority replay = 1
GPU endpoint/CIGAR/traceback/output authority = 0
```

Do:

```text
keep this design as the only active Path B shape
use the API name and descriptor contract from the design
keep CPU scoreInfo rows out of the promoted v5 interface
keep validation after descriptor emission, not as descriptor source
```

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-descriptor-emission-design
```

Stop if:

```text
the next implementation needs CPU preAlign or CPU scoreInfo rows to create
descriptors
the API returns endpoint, CIGAR, traceback, output, or digest authority
the API materializes a full host-visible legacy scoreInfo row stream as the
promoted interface
```

### Gate v5.1: True Pre-ScoreInfo Descriptor Source

Purpose:

```text
Prove that GPU emits compact attempt descriptors before CPU scoreInfo/preAlign
work on a small broad workload.
```

Do:

```text
add structs/API in cuda/prealign_cuda.h
add fail-closed CPU-only stub in cuda/prealign_cuda_stub.cpp
add CUDA implementation in cuda/prealign_cuda.cu
wire a default-off runner in fasim/Fasim-LongTarget.cpp
call the descriptor-emission API before CPU scoreInfo/preAlign generation
record strict telemetry under FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE
run CPU validation only after GPU descriptor emission
keep CPU aligner.Align() as replay/output authority
```

Exit gate:

```bash
make check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke
```

Required telemetry:

```text
phase7_v5_true_pre_scoreinfo_descriptor_source_requested = 1
phase7_v5_true_pre_scoreinfo_descriptor_source_active = 1
source_is_pre_scoreinfo = 1
scoreinfo_prealign_reduced = 1
gpu_descriptor_attempts > 0
descriptor_false_negatives = 0
missing_required_attempts = 0
candidate_attempts_below_all_column_replay_scale = 1
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
gate_v5_1_pass = 1
```

Stop if:

```text
active remains 0
source_is_pre_scoreinfo remains 0
scoreinfo_prealign_reduced remains 0
CPU scoreInfo rows are used as descriptor source
descriptor false negatives appear
missing required attempts appear
candidate attempts approach all-column replay scale
fallback hides the GPU descriptor path
```

### Gate v5.2: CPU-Authority Replay

Do:

```text
feed only certified candidate attempts to CPU aligner.Align()
compare full rows and digest against the CPU authority baseline
compare missing rows, extra rows, triplex mismatches, and fallback counters
measure candidate Align attempts versus reference Align attempts
keep GPU endpoint/CIGAR/traceback/output authority disabled
```

Exit gate:

```text
full_rows_equal = true
digest_match = true
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
fallback_accounting_clean = true
candidate_align_attempts < reference_align_attempts
scoreInfo/preAlign work reduced or replaced
```

Stop if:

```text
Output differs, fallbacks hide the GPU path, or Align-side attempts are not
reduced.
```

### Gate v5.3: First64 Broad Gate

Do:

```text
run the same source on NEAT1 first64 or equivalent broad workload
measure baseline wall and candidate wall
itemize GPU descriptor/source time, CPU scoreInfo/preAlign time, CPU Align time,
convert/output time, and fallback time
compare full rows and digest
```

Exit gate:

```text
full_rows_equal = true
digest_match = true
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreInfo/preAlign work reduced or replaced
Align-side work reduced or replaced
fallback_accounting_clean = true
```

Stop if:

```text
Correctness is clean but wall time is near parity.
Only one of scoreInfo/preAlign or Align-side work is reduced.
The speedup comes from output drift or skipped authority checks.
```

### Gate v5.4: Workload Matrix Promotion

Do:

```text
add a contract=broad_replacement row only after Phase 7.4 passes
record exact workload, commands, row equality, digest, speedup, fallback counts,
scoreInfo/preAlign reduction, and Align-side reduction
rerun the workload matrix parser
```

Exit gate:

```text
claimed_broad_replacement_rows > 0
broad_gate_pass = 1
phase6 workload matrix parser passes
```

Stop if:

```text
The row is top5-only, fallback-heavy, output-drift, first1-only, or missing
either scoreInfo/preAlign reduction or Align-side reduction.
```

### Phase 7 Failure Handling

If Gate v5.1 cannot pass without CPU scoreInfo as the source:

```text
record a v5 no-go checkpoint
keep broad_objective_status = open
return to Path A scoped acceptance or a new Phase 7 architecture design
must_not_call_update_goal_complete = 1
```

If Gate v5.2 passes but Gate v5.3 is slower than baseline:

```text
record correctness-clean performance no-go
do not add a broad_replacement matrix row
do not continue the same execution shape to larger workloads
must_not_call_update_goal_complete = 1
```

If Gate v5.3 passes:

```text
add a broad_replacement workload-matrix row
rerun Phase 0, Phase 2, Phase 6, and Phase 8 gates
close only if Phase 8 sets must_not_call_update_goal_complete = 0
```

Completion role:

```text
required for Path B
the only current route to original broad completion
```

## Phase 8: Completion Decision

Purpose:

```text
Close the active goal only when the documented completion contract is satisfied.
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

Close Path A only if:

```text
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
must_not_call_update_goal_complete = 0
```

Path B close procedure:

```bash
make check-fasim-gasal2-roadmap-current-state
make check-fasim-gasal2-roadmap-phase8-completion-decision
```

Close Path B only if:

```text
claimed_broad_replacement_rows > 0
broad_gate_pass = 1
must_not_call_update_goal_complete = 0
```

If neither path passes:

```text
final_goal_decision = not_complete_without_user_scope_acceptance
broad_objective_status = open
scope_or_broad_design_decision_required = 1
path_a_user_acceptance_required = 1
path_b_new_broad_architecture_required = 1
must_not_call_update_goal_complete = 1
```

## Immediate Next Work

The shortest valid route is Path A, but it requires explicit user acceptance of
the narrowed scoped product.

If the user still wants the original broad objective, do this next:

```text
1. Treat the completed oracle min-cover replay smoke as historical evidence:
     phase7_broad_restart_v3_oracle_min_cover_replay_smoke =
       output_no_go

2. Do not continue the oracle min-cover replay shape:
     candidate_align_attempts = 463
     reference_align_attempts = 2,872
     missing_rows = 11
     extra_rows = 9

3. Keep the attempt-coverage seed smoke as background evidence:
     phase7_broad_restart_v3_attempt_coverage_seed_smoke =
       attempt_coverage_clean_needs_replay_preflight
     candidate_certificate_false_negatives = 0
     missing_required_attempts = 0
     raw_seed_hits = 1,051,822
     candidate_attempts = 108,694
     candidate_min_cover_positions = 463
     reference_attempts = 2,872

4. Treat the current seed/index path as stopped:
     phase7_broad_restart_v3_seed_path_stop =
       current_seed_index_path_stopped
     phase7_broad_restart_v3_may_continue_to_first64 = 0

5. Treat docs/fasim_gasal2_phase7_broad_restart_v4_scoreinfo_native_design.md
   as a historical v4 design checkpoint:
     phase7_broad_restart_v4_scoreinfo_native_design = defined
     phase7_broad_restart_v4_next_gate = legacy_byte_scoreinfo_shadow_first1

6. Treat docs/fasim_gasal2_phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke.md
   as the v4 host-contract checkpoint:
     phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke =
       host_contract_clean_needs_gpu
     phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 0
     phase7_broad_restart_v4_host_contract_pass = 1

7. Treat docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke.md
   as the v4 GPU first1 shadow checkpoint:
     phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke =
       gpu_contract_clean_first1
     phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 718
     phase7_broad_restart_v4_gate_v4_1_pass = 1
     phase7_broad_restart_v4_runtime_next_gate =
       gpu_legacy_byte_scoreinfo_source_first1_cpu_authority_replay

8. Treat docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke.md
   as the v4 GPU first1 source replay checkpoint:
     phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke =
       cpu_authority_replay_clean_first1
     phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_digest_match = 1
     phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempts = 2008
     phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_reference_align_attempts = 2872
     phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempt_reduction = 864
     phase7_broad_restart_v4_gate_v4_2_pass = 1
     phase7_broad_restart_v4_runtime_next_gate =
       gpu_legacy_byte_scoreinfo_source_first64_broad_gate

9. Treat docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate.md
   as the v4 first64 broad-gate no-go checkpoint:
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

10. Do not continue the current v4 source replay implementation as a broad
   completion path because first64 wall time is slower than CPU baseline.

11. Treat docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_design.md
   as the v5 design-family checkpoint:
     phase7_broad_restart_v5_fused_scoreinfo_consumer_design = defined
     phase7_broad_restart_v5_status = design_only
     phase7_broad_restart_v5_design_family =
       fused_gpu_scoreinfo_to_candidate_attempt_descriptors
     phase7_broad_restart_v5_differs_from_v4_source_replay = 1
     phase7_broad_restart_v5_next_gate =
       fused_scoreinfo_consumer_descriptor_contract_first1

12. Treat docs/superpowers/plans/2026-06-13-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer.md
   as the current implementation plan:
     phase7_broad_restart_v5_implementation_plan = defined
     phase7_broad_restart_v5_runtime_first_gate =
       fused_scoreinfo_consumer_descriptor_contract_first1
     Task 1: Env, Stats, And Default-Off Telemetry
     Task 2: Descriptor Contract Runtime Smoke
     Task 3: CPU-Authority Replay First1 Gate
     Task 4: Roadmap Checkpoint And Current-State Wiring
     Task 5: First64 Broad Gate Characterization
     make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-implementation-plan

13. Treat docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.md
   as the current strict runtime pass checkpoint:
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

14. Treat docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_smoke.md
   as the current strict Gate v5.2 runtime pass checkpoint:
     phase7_broad_restart_v5_cpu_authority_replay_smoke =
       gate_v5_2_pass_first1
     root_cause_fix = legacy_float_identity_cutlength_descriptor_generation
     phase7_v5_cpu_authority_replay_full_rows_equal = 1
     phase7_v5_cpu_authority_replay_digest_match = 1
     phase7_v5_cpu_authority_replay_candidate_align_attempts = 2008
     phase7_v5_cpu_authority_replay_reference_align_attempts = 2872
     phase7_broad_restart_v5_gate_v5_2_pass = 1
     next_required_gate = different_gpu_execution_design_or_path_a_scope_decision

14b. Treat docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate.md
   as the current strict Gate v5.3 no-go checkpoint:
     phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate =
       correctness_clean_performance_no_go
     phase7_broad_restart_v5_first64_candidate_vs_baseline = 0.706009
     phase7_broad_restart_v5_first64_missing_required_attempts = 624
     phase7_broad_restart_v5_runtime_next_gate =
       different_gpu_execution_design_or_path_a_scope_decision

14c. Treat docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md,
   docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export.md,
   and docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1.md
   as the current post-v5.3 Path B proof-search checkpoint:
     phase7_post_v5_3_pre_d2h_output_inert_proof_search_design = defined
     phase7_post_v5_3_pre_d2h_output_inert_proof_search_status = first1_export_pass
     phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export = pass
     phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_implement = 1
     phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion = 0
     next_required_gate = pre_d2h_output_inert_proof_acceptance_first1
     phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1 = no_go
     accepted_pre_d2h_proof_families = 0
     reducing_runtime_allowed = 0
     first64_runtime_allowed = 0
     current_next_pr = fasim: design different GPU execution design or scope acceptance
     runtime_reduction_enabled = 0
     make check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-design
     make check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-first1-export

15. Treat docs/fasim_gasal2_phase7_broad_restart_v5_cuda_descriptor_emission_design.md
   as the current active Path B design checkpoint:
     phase7_broad_restart_v5_cuda_descriptor_emission_design = defined
     phase7_broad_restart_v5_cuda_descriptor_emission_status = design_only
     new_cuda_api = prealign_cuda_emit_legacy_byte_attempt_descriptors
     output_contract = compact_attempt_descriptors_not_scoreinfo_rows
     host-visible full legacy scoreInfo row stream = forbidden
     next_gate = runtime_smoke_true_pre_scoreinfo_descriptor_source_first1

16. Implement the minimal default-off descriptor-emission prototype:
     add API structs in cuda/prealign_cuda.h
     add fail-closed stub in cuda/prealign_cuda_stub.cpp
     add CUDA implementation in cuda/prealign_cuda.cu
     wire a pre-scoreInfo runner in fasim/Fasim-LongTarget.cpp
     keep CPU aligner.Align() as replay/output authority
     do not use CPU scoreInfo rows as descriptor source

17. Make Gate v5.1 and Gate v5.2 pass before doing any broader characterization:
     make check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke
     required: active = 1
     required: source_is_pre_scoreinfo = 1
     required: scoreinfo_prealign_reduced = 1
     required: descriptor_false_negatives = 0
     required: missing_required_attempts = 0
     required: gate_v5_1_pass = 1

17. If Gate v5.1 passes, create the Gate v5.2 CPU-authority replay checkpoint.
   It must prove full_rows_equal, digest_match, triplex_mismatches = 0,
   fallback accounting clean, scoreInfo/preAlign reduction, and Align-side
   reduction. If it fails, record no-go and keep the goal open.

18. Gate v5.3 first64 broad characterization is complete and recorded as no-go.
   It must prove candidate_wall_seconds < baseline_wall_seconds while keeping
   the full output contract and both CPU-work reductions.

19. Add a broad_replacement matrix row only after Gate v5.3 passes.

20. Run Phase 8 only after Path A acceptance or Path B broad gate pass.
```

Do not mark the active goal complete before Phase 8 allows it.
