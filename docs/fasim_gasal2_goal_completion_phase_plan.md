# Fasim GASAL2 Goal Completion Phase Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define the remaining phases required to complete the active Fasim/GASAL2 goal without reclassifying partial milestones as broad success.

**Architecture:** The plan keeps CPU `aligner.Align()` as the semantic authority until a phase explicitly proves otherwise. GASAL2 may accelerate scoped scoreInfo/top5/archive paths, and future broad work must first replay the CPU-authority frontier exactly, then reduce measured CPU work while preserving the claimed output contract.

**Tech Stack:** Fasim C++ runtime, GASAL2 CUDA bridge, shell characterization scripts, Makefile gates, TSV workload matrix, Markdown evidence docs.

---

For the short phase-by-phase execution entry point, see
`docs/fasim_gasal2_goal_completion_phase_checklist.md`. For the operational
completion ladder that says what each phase must do, stop, or close, see
`docs/fasim_gasal2_goal_completion_execution_ladder.md`. For the canonical
phase roadmap that says the current phase, next gate, and per-phase advance
contract, see `docs/fasim_gasal2_goal_completion_phase_roadmap.md`. For the
concise phase-by-phase close plan, see
`docs/fasim_gasal2_goal_completion_close_plan.md`.

## Completion Rule

The active goal can be marked complete only by one of these paths:

```text
Path A: scoped completion
  Allowed only if the user explicitly accepts the narrowed product:
    short-query/H19 top5 artifact
    MEG3-like complete-record grouping where claimed
    archive-first restored output where claimed

Path B: broad completion
  Required if the original broad goal remains active:
    materially accelerate or replace the scoreInfo/preAlign/Align-related
    path while preserving the required output contract.
```

If neither path passes, keep:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Non-Negotiable Invariants

Every phase must preserve these rules:

```text
CPU aligner.Align() remains score/endpoint/traceback/CIGAR/output authority.
GASAL2 endpoint/CIGAR/traceback/output/digest authority is forbidden.
Output drift cannot be counted as speedup.
Default runtime behavior must not change without a separate opt-in gate.
Every claimed workload must have an explicit workload-matrix row.
Fallback-heavy rows must not be described as GPU-fast-path clean.
```

## Phase Status Map

```text
Phase 0: Reproducibility
  Status: ready, maintain
  Role: mandatory for Path A and Path B

Phase 1: Scoped product contract
  Status: acceptance packet defined; ready only if the user accepts scope
  Role: can close Path A, cannot close Path B

Phase 2: Full-output equivalence-first delivery
  Status: ready, maintain
  Role: output authority foundation for Path B

Phase 3: Pre-convert CPU reduction
  Status: current CIGAR NT prefilter is correctness-clean but performance no-go
  Role: optional future Path B helper only if it reduces wall time

Phase 4: Sort/top-N optimization
  Status: defer
  Role: optional only if profiling makes sort/filter dominant

Phase 5: Archive artifact
  Status: ready, maintain
  Role: Path A delivery artifact and Path B output accelerator

Phase 6: Workload matrix
  Status: claimed scoped rows only; no broad_replacement row yet
  Role: mandatory claim ledger for both paths

Phase 7: Broad restart
  Status: active broad path; current v3 seed/index path is stopped, v4
    source replay first64 is performance no-go, and v5 fused scoreInfo
    consumer design is defined
  Role: required for original broad completion

Phase 8: Completion decision
  Status: not complete
  Role: only phase that may justify marking the active goal complete
```

## Phase 0: Reproducibility

Purpose:

```text
Make every later GASAL2/Fasim claim reproducible from a clean checkout.
```

Required work:

- [ ] Keep `patches/gasal2-fasim-bridge.patch` as the tracked local GASAL2 delta.
- [ ] Keep `scripts/setup_gasal2.sh` idempotent and pinned to the upstream GASAL2 commit.
- [ ] Keep `make setup-gasal2` and `make build-fasim-gasal2` working without untracked `.tmp/GASAL2` edits.
- [ ] Keep CUDA version, SM arch, `GASAL2_MAX_QUERY_LEN`, and `GASAL2_N_CODE` visible in Makefile/config output.

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase0-reproducibility
make check-fasim-gasal2-reproducible-setup
make setup-gasal2
make build-fasim-gasal2
```

Stop if:

```text
Any claimed result depends on a machine-local GASAL2 binary or untracked source edit.
```

## Phase 1: Scoped Product Contract

Purpose:

```text
Decide whether the existing scoped product is allowed to close the active goal.
```

Scoped product:

```text
short-query/H19 top5 artifact
MEG3-like grouped tiny-region top5 where claimed
archive-first restored output where claimed
```

Non-claims:

```text
not aligner.Align replacement
not full universal TFOsorted replacement
not GPU endpoint/CIGAR/traceback authority
not long-query NEAT1/MALAT1 broad replacement
```

Required work:

- [x] Define the Path A acceptance packet.
- [ ] Ask for explicit user acceptance before using Path A.
- [ ] If accepted, record the accepted contract and exact commands in docs.
- [ ] Rerun scoped readiness gates before Phase 8.

Exit gate for Path A:

```bash
make check-fasim-gasal2-roadmap-phase1-scoped-product
make check-fasim-gasal2-roadmap-phase5-archive-artifact
make check-fasim-gasal2-roadmap-phase6-workload-matrix
```

Stop if:

```text
The user still wants the original broad objective. Then Path A cannot close
the goal, and Phase 7 remains required.
```

Acceptance packet:

```text
Document:
  docs/fasim_gasal2_path_a_scoped_completion_acceptance.md

path_a_scoped_completion_acceptance_packet = defined
path_a_scoped_completion_status = ready_if_user_accepts_scope
user_scope_acceptance_recorded = 0
scoped_completion_may_close_goal = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Phase 2: Full-Output Equivalence-First Delivery

Purpose:

```text
Keep full TFOsorted/restored output correct while measuring output-side CPU cost.
```

Required work:

- [ ] Preserve chr22 and chr1 restored row-set equality.
- [ ] Keep convert/output timing itemized.
- [ ] Use this phase as the output baseline for any broad claim.

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase2-equivalence-first-convert
make check-fasim-gasal2-archive-first-output
make check-fasim-gasal2-convert-cpu-breakdown
```

Stop if:

```text
The speedup requires changing restored rows, ordering semantics, or digest.
```

## Phase 3: Pre-Convert CPU Reduction

Purpose:

```text
Reduce CPU materialization/convert work without changing the complete row set.
```

Current evidence:

```text
CIGAR NT prefilter:
  shadow proof clean
  real validate clean
  full chr22/chr1 performance no-go
  default recommendation = no
```

Required work:

- [ ] Do not enable the current CIGAR NT prefilter as a performance path.
- [ ] Only test new reducers in shadow/proof-first form.
- [ ] Require full row equality before measuring a real prune.

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
A reducer preserves top5 but changes the full row set, or reduces work without
beating Phase 2 wall time.
```

## Phase 4: Sort/Top-N Optimization

Purpose:

```text
Optimize ordering only if profiling proves sort/filter is now dominant.
```

Required work:

- [ ] Keep this deferred until Phase 2/3 profiling shows sort/filter dominates.
- [ ] Preserve comparator, tie behavior, unique behavior, and top-N boundary.

Exit gate:

```text
same kept row set
same comparator/tie behavior
materially lower sort/filter wall time
```

Stop if:

```text
Partial selection changes row identity, tie behavior, or top-N boundary.
```

## Phase 5: Archive Artifact

Purpose:

```text
Store the smallest sufficient artifact and restore TFOsorted on demand.
```

Required work:

- [ ] Keep archive manifest validation.
- [ ] Keep reference digest validation.
- [ ] Keep restore command documented.
- [ ] Keep restored output equality checks.

Exit gate:

```bash
make check-fasim-gasal2-roadmap-phase5-archive-artifact
make check-fasim-gasal2-archive-manifest-parser
make check-fasim-tfo-archive-integrity-parser
```

Stop if:

```text
The archive cannot restore the claimed output without rerunning Fasim, or the
manifest omits reference identity needed for later restore.
```

## Phase 6: Workload Matrix

Purpose:

```text
Make every claim explicit and prevent scoped evidence from becoming broad
evidence by accident.
```

Required work:

- [ ] Add or update `docs/fasim_gasal2_workload_matrix.tsv` for every new claim.
- [ ] Use `scope=claimed` only for the exact contract that passed.
- [ ] Use `contract=broad_replacement` only after Phase 7 broad gate passes.

Path A matrix exit gate:

```text
all scoped claimed rows pass
blocked and unclaimed rows remain explicit
no broad_replacement claim is implied
```

Path B matrix exit gate:

```text
at least one claimed broad_replacement row
row_equal = true
speedup > 1.0
fallbacks = 0 for the claimed GPU path
scoreinfo_reduced = true
align_side_reduced = true
```

Stop if:

```text
Any fallback-heavy, output-drift, or top5-only row is presented as broad clean.
```

## Phase 7: Broad Restart

Purpose:

```text
Complete the original broad objective if scoped completion is not accepted.
```

Current evidence:

```text
frontier replay:
  NEAT1 first1 exact
  NEAT1 first64 exact
  no reduction

oracle selected-row reducer:
  projected Align attempt reduction exists
  not a runtime path because selected rows are known only after CPU Align

pre-Align predictor:
  no-go with current fields

post-Align score/end signal:
  no-go as a reducing signal

scoreInfo-local early stop:
  first runtime candidate changed NEAT1 first1 output and stopped
  all-attempt variant is correctness-clean on first1/first64
  all-attempt variant reduces Align attempts but keeps scoreInfo/preAlign on CPU
  first64 wall time is near parity, so it is not broad completion

Gate C:
  next required broad-path gate
  coverage-preserving GPU candidate generator
  must reduce or replace scoreInfo/preAlign work
  must keep CPU aligner.Align() as authority
  first1 must pass before first64
  no broad_replacement matrix row until first64 passes
```

Required subphases:

### Phase 7.1: Measured Early-Stop Runtime Smoke

- [x] Add default-off env `FASIM_GASAL2_PHASE7_FRONTIER_EARLY_STOP=1`.
- [x] Verify default behavior remains unchanged when env is absent.
- [x] Emit telemetry for requested/active/skipped/reference attempts.
- [x] Preserve CPU `aligner.Align()` authority for every attempted row.

Current evidence:

```text
phase7_broad_restart_v2_frontier_early_stop_runtime =
  runtime_smoke_clean_needs_neat1_first1

make check-fasim-gasal2-phase7-frontier-early-stop-runtime-smoke:
  default_off = 1
  reference_align_attempts = 192
  candidate_align_attempts = 48
  skipped_attempts = 144
  output digest unchanged
```

Gate:

```text
default_off = 1
runtime_smoke = pass
output contract unchanged on small fixture
candidate_align_attempts <= reference_align_attempts
```

### Phase 7.2: NEAT1 first1 Runtime Correctness Gate

- [x] Run baseline and early-stop candidate on NEAT1 first1.
- [x] Compare full rows, digest, missing rows, extra rows, and triplex mismatches.
- [x] Record candidate and reference Align attempt counts.

Current evidence:

```text
phase7_broad_restart_v2_frontier_early_stop_runtime_first1 =
  correctness_no_go

neat1_first1:
  digest_match = 0
  full_rows_equal = 0
  missing_rows = 7
  extra_rows = 5
  triplex_mismatches = 12
  candidate_align_attempts = 1,309
  reference_align_attempts = 2,872
  align_attempt_reduction = 1,563
```

Gate:

```text
digest_match = 1 or full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
false_negative_scoreinfos = 0
candidate_align_attempts < reference_align_attempts
```

Stop if:

```text
NEAT1 first1 changes output or fails to reduce Align attempts.
```

Current stop decision:

```text
stop_this_candidate = 1
reason = first1 output drift
next_gate = new reducer or architecture
next_reducer_design = coverage-first all-attempt CPU replay
```

### Phase 7.2b: All-Attempt Early-Stop Runtime First1 Gate

- [x] Add default-off env `FASIM_GASAL2_PHASE7_ALL_ATTEMPT_EARLY_STOP=1`.
- [x] Route the all-attempt mode through CPU fallback scoreInfo and
  CPU-authority replay when GASAL2 query length guard blocks long-query
  direct batch.
- [x] Run baseline and all-attempt candidate on NEAT1 first1.
- [x] Compare full rows, digest, missing rows, extra rows, triplex mismatches,
  false-negative scoreInfos, and Align attempt counts.

Current evidence:

```text
phase7_all_attempt_early_stop_runtime_first1 =
  correctness_go_needs_first64

Command:
  make characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime
  make check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-result

neat1_first1:
  digest_match = 1
  full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  candidate_align_attempts = 2,008
  reference_align_attempts = 2,872
  align_attempt_reduction = 864
  candidate_vs_baseline = near_parity_across_reruns
  decision = phase7_all_attempt_early_stop_runtime_first1_go
  decision_reasons = none
```

Gate:

```text
digest_match = 1 or full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
false_negative_scoreinfos = 0
candidate_align_attempts < reference_align_attempts
```

Current decision:

```text
Gate A passes for correctness and Align-side attempt reduction.
This is not broad completion because first1 wall time is near parity and
scoreInfo/preAlign work is still CPU work.
next_gate = all-attempt early-stop runtime first64
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

### Phase 7.3: NEAT1 first64 Broad Gate

- [x] Run baseline and all-attempt early-stop candidate on NEAT1 first64.
- [x] Measure wall time and itemized CPU/GPU timings.
- [ ] Update workload matrix only if this gate passes.

Current evidence:

```text
phase7_all_attempt_early_stop_runtime_first64 =
  correctness_go_near_parity_not_broad

Command:
  make characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64
  make check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64-result

neat1_first64:
  digest_match = 1
  full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  candidate_align_attempts = 140,087
  reference_align_attempts = 211,976
  align_attempt_reduction = 71,889
  candidate_vs_baseline = near_parity_across_reruns
  decision = phase7_all_attempt_early_stop_runtime_first64_go
  decision_reasons = none
```

Gate:

```text
digest_match = 1 or full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
false_negative_scoreinfos = 0
candidate_align_attempts < reference_align_attempts
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0
scoreInfo/preAlign work reduced or unchanged with documented reason
Align-side attempts reduced
```

Stop if:

```text
Candidate wall time does not beat baseline, output differs, or Align-side work
is not reduced.
```

Current decision:

```text
Gate B passes for correctness and Align-side attempt reduction.
It does not complete Path B because scoreInfo/preAlign work is still CPU work
and first64 wall time is only near parity.
next_gate = coverage-preserving GPU candidate generator
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

### Phase 7.4: Broad Matrix Promotion

- [ ] Add a `contract=broad_replacement` row only if Phase 7.3 passes.
- [ ] Record workload name, row equality, speedup, fallbacks, scoreInfo reduction, and Align-side reduction.
- [ ] Do not call the broad objective complete from first1-only or top5-only evidence.

Gate:

```text
phase6 matrix parser passes
broad_replacement row exists
all broad row fields satisfy Path B exit gate
```

## Phase 8: Completion Decision

Purpose:

```text
Make the final completion decision after evidence gates, not before.
```

Path A close procedure:

- [ ] Confirm the user explicitly accepted scoped completion.
- [ ] Confirm `user_scope_acceptance_recorded = 1` has been recorded after that acceptance.
- [ ] Rerun Phase 0, Phase 1, Phase 5, and Phase 6 gates.
- [ ] Record final decision as scoped completion, not broad replacement.
- [ ] Only then mark the active goal complete.

Path B close procedure:

- [ ] Rerun Phase 0 through Phase 7 current-state gates.
- [ ] Confirm at least one broad_replacement row passes in the workload matrix.
- [ ] Confirm CPU-authority verification remains clean.
- [ ] Record final decision as broad completion.
- [ ] Only then mark the active goal complete.

Gate:

```bash
make check-fasim-gasal2-roadmap-current-state
make check-fasim-gasal2-roadmap-phase8-completion-decision
```

Stop if:

```text
Path A was not accepted and Path B does not have a passing broad_replacement
matrix row.
```

## Immediate Execution Order

The next work should proceed in this order:

```text
1. Keep this phase plan as the execution contract.
2. Do not continue the stopped frontier early-stop candidate to first64.
3. Use docs/fasim_gasal2_phase7_next_reducer_after_early_stop_no_go_design.md
   as the next reducer contract.
4. Gate A is complete: all-attempt early-stop runtime first1 is correctness clean.
5. Gate B is complete: all-attempt early-stop runtime first64 is correctness
   clean and near-parity, but not broad completion.
6. Do not update Phase 6 with a broad_replacement row yet.
7. Gate C design and implementation plan define the next work.
8. Gate C runtime scaffold must pass env/smoke before first1 characterization.
9. Gate C first1 must prove coverage and CPU-authority replay before first64.
10. Gate C first64 must reduce or replace scoreInfo/preAlign work, keep
   Align-side reduction, and beat baseline wall time before matrix promotion.
11. Run Phase 8 completion decision only after Path A acceptance or a future
   Path B broad_replacement row.
```

## Phase 7 Gate C: GPU Candidate Generator Design

Current evidence:

```text
phase7_gate_c_gpu_candidate_generator_design = defined

Document:
  docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md

Design:
  coverage-preserving GPU candidate generator
  candidate coverage before candidate reduction
  preserve the all-attempt early-stop frontier
  reduce or replace scoreInfo/preAlign work

Authority:
  CPU aligner.Align() remains authority
  GASAL2 output authority = 0
  no GPU endpoint authority
  no GPU CIGAR or traceback authority
  no real opt-in

Gate:
  NEAT1 first1 coverage gate before first64
  NEAT1 first64 broad gate before workload-matrix promotion
  workload matrix broad_replacement row is forbidden until Gate C first64 passes

Current status:
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
```

## Phase 7 Gate C: Implementation Plan

Current evidence:

```text
phase7_gate_c_gpu_candidate_generator_implementation_plan = defined

Document:
  docs/superpowers/plans/2026-06-13-fasim-gasal2-phase7-gate-c-gpu-candidate-generator.md

Plan tasks:
  Task 1: Gate C Env And Telemetry
  Task 2: Oracle Frontier Export Reuse
  Task 3: GPU Candidate Descriptor Shadow
  Task 4: Coverage Comparison Gate
  Task 5: CPU-Authority Replay Gate
  Task 6: NEAT1 first64 Broad Characterization
  Task 7: Roadmap And Matrix Decision

Current status:
  design and implementation plan are defined
  runtime env/smoke is clean for the oracle-metric scaffold
  first1 and first64 Gate C evidence are still required
  broad_gate_pass = 0
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
```

## Phase 7 Gate C: Runtime Scaffold Smoke

Current evidence:

```text
phase7_gate_c_runtime_smoke = pass

Command:
  make check-fasim-gasal2-phase7-gate-c-env
  make check-fasim-gasal2-phase7-gate-c-runtime-smoke

baseline:
  phase7_gate_c_requested = 0
  phase7_gate_c_active = 0

candidate:
  FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES = 1
  phase7_gate_c_requested = 1
  phase7_gate_c_active = 0
  phase7_gate_c_tasks = 48
  phase7_gate_c_oracle_scoreinfos = 48
  phase7_gate_c_oracle_attempts = 192
  phase7_gate_c_gpu_candidate_scoreinfos = 0
  phase7_gate_c_gpu_candidate_attempts = 0
  phase7_gate_c_false_negative_scoreinfos = 0
  phase7_gate_c_missing_required_attempts = 0
  phase7_gate_c_extra_candidate_attempts = 0

Interpretation:
  Task 1/2 scaffold is wired and default-off.
  This is not a GPU candidate descriptor path yet.
  No first1 or first64 coverage gate has passed.
  next_gate = Gate C GPU Candidate Descriptor Shadow
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
```

## Phase 7 Gate C: First1 Descriptor Shadow

Current evidence:

```text
phase7_gate_c_first1 = no_go_no_gpu_candidate_descriptors

Command:
  make characterize-fasim-gasal2-phase7-gate-c-first1
  make check-fasim-gasal2-phase7-gate-c-first1-result

neat1_first1:
  digest_match = 1
  full_rows_equal = 1
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  candidate_align_attempts = 2,008
  gate_b_candidate_align_attempts = 2,008
  scoreinfo_reduced = 0
  oracle_scoreinfos = 718
  oracle_attempts = 2,872
  gpu_candidate_scoreinfos = 0
  gpu_candidate_attempts = 0
  missing_required_attempts = 0
  extra_candidate_attempts = 0
  gate_c_requested = 1
  gate_c_active = 1
  decision = phase7_gate_c_first1_no_go
  decision_reasons = no_gpu_candidate_descriptors,scoreinfo_not_reduced

Interpretation:
  CPU-authority replay remains output-clean on first1.
  Current Gate C does not generate GPU candidate descriptors.
  Current Gate C does not reduce or replace scoreInfo/preAlign work.
  Do not run Gate C first64 broad characterization from this candidate.
  Do not add a broad_replacement workload-matrix row.
  next_gate = new GPU candidate descriptor source or stop broad GASAL2 path
  broad_objective_status = open
  must_not_call_update_goal_complete = 1
```

Stop checkpoint:

```text
Document:
  docs/fasim_gasal2_phase7_gate_c_stop_checkpoint.md

phase7_gate_c_stop_checkpoint = current_source_no_go
current_gate_c_source_status = stopped_no_gpu_candidate_descriptors
gate_c_first64_allowed = 0
restart_requires_new_gpu_candidate_descriptor_source = 1
```

## Phase 7: Current Broad Stop Decision

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_current_broad_stop_decision.md

phase7_current_broad_stop_decision = current_broad_sources_no_go
current_broad_sources_status = stopped
phase7_current_broad_sources_may_continue = 0
phase7_new_architecture_required = 1
claimed_broad_replacement_rows = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
The current broad GASAL2/Fasim architecture family is stopped.
This does not complete the goal.
Path B can resume only with a materially different architecture that reduces
or replaces both scoreInfo/preAlign work and Align-side work while preserving
the claimed full output contract.
Path A remains available only if the user explicitly accepts scoped completion.
```

Do not spend more work on these stopped paths before Phase 7.1:

```text
direct GASAL2 aligner.Align replacement
GPU endpoint/CIGAR/traceback authority
current score-only GPU bridge
current CIGAR NT prefilter as a recommended runtime path
pre-Align selected-row prediction with the already-tested fields
post-Align score/end ranking as the reducing signal
```

## Phase 7 v3: Candidate-Certificate Design

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_candidate_certificate_design.md

phase7_broad_restart_v3_candidate_certificate_design = defined
phase7_broad_restart_v3_current_status = design_only
phase7_broad_restart_v3_next_gate = descriptor_source_smoke
phase7_broad_restart_v3_may_claim_completion = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
v3 is the next allowed Path B architecture after the current broad sources
stopped. It is candidate-certificate first: a GPU/native descriptor source must
produce candidate descriptors before CPU scoreInfo/preAlign has already done the
broad work, then a certificate must prove no legacy-required candidate is lost.

v3 can continue only if the next descriptor-source smoke shows:
  gpu_candidate_scoreinfos > 0
  gpu_candidate_attempts > 0
  cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
  candidate_certificate_false_negatives = 0
  missing_required_attempts = 0
```

It still cannot close Path B. Broad completion requires the later NEAT1 first64
broad gate with full output equality, runtime win, scoreInfo/preAlign
reduction, and Align-side reduction.

## Phase 7 v3: Descriptor-Source Smoke

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_descriptor_source_smoke.md

phase7_broad_restart_v3_descriptor_source_smoke =
  current_no_pre_scoreinfo_source
phase7_broad_restart_v3_current_status = scaffold_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate = real_pre_scoreinfo_descriptor_source
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
The runtime telemetry path is wired and default-off. The smoke proves current
code can account the absence of a v3 descriptor source, but it does not yet
produce candidate descriptors before CPU scoreInfo/preAlign work.

Current smoke:
  phase7_v3_descriptor_source_requested = 1
  phase7_v3_descriptor_source_active = 0
  phase7_v3_descriptor_source_candidate_attempts = 0
  phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0
```

Do not continue to first64 from this smoke. The next gate must add a real
pre-scoreInfo descriptor source with candidate descriptors and CPU scoreInfo
call reduction.

## Phase 7 v3: Pre-ScoreInfo Descriptor-Source Smoke

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke.md

phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke =
  pre_scoreinfo_descriptors_no_reduction
phase7_broad_restart_v3_current_status = pre_scoreinfo_scaffold_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate =
  certificate_checked_scoreinfo_reducing_descriptor_source
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
The v3 hook now runs before CPU scoreInfo/preAlign and can produce diagnostic
candidate descriptors. This is progress beyond the previous after-CPU
descriptor-source smoke.

Current smoke:
  phase7_v3_descriptor_source_active = 1
  phase7_v3_descriptor_source_pre_scoreinfo_source = 1
  phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
  phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0
  phase7_v3_descriptor_source_candidate_certificate_checked = 0
```

Do not continue to first64 from this smoke. The next gate must check candidate
coverage and reduce CPU scoreInfo/preAlign calls.

## Phase 7 v3: Certificate Smoke

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_certificate_smoke.md

phase7_broad_restart_v3_certificate_smoke =
  certificate_checked_no_scoreinfo_reduction
phase7_broad_restart_v3_current_status = certificate_scaffold_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate =
  scoreinfo_reducing_candidate_certificate
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
The v3 hook can now mark a task-level scaffold certificate as checked.
The smoke still keeps CPU scoreInfo/preAlign work unchanged.
It does not prove full legacy scoreInfo/attempt coverage.
It does not pass Gate v3.1.

Current smoke:
  phase7_v3_descriptor_source_active = 1
  phase7_v3_descriptor_source_pre_scoreinfo_source = 1
  phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
  phase7_v3_descriptor_source_candidate_certificate_checked = 1
  phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
  phase7_v3_descriptor_source_missing_required_attempts = 0
  phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0
  cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls
```

Do not continue to first64 from this smoke. The next gate must make the
certificate scoreInfo-reducing while preserving zero false negatives and CPU
output authority.

## Phase 7 v3: All-Column Certificate Smoke

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_all_column_certificate_smoke.md

phase7_broad_restart_v3_all_column_certificate_smoke =
  scoreinfo_reducing_all_column_certificate
phase7_broad_restart_v3_current_status =
  gate_v3_1_pass_attempt_overgenerate
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
phase7_broad_restart_v3_next_gate =
  all_column_certificate_cpu_replay_first1
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
The v3 source can now avoid CPU scoreInfo calls in the candidate source by
overgenerating every target end column and every target window.

Current smoke:
  phase7_v3_descriptor_source_active = 1
  phase7_v3_descriptor_source_pre_scoreinfo_source = 1
  phase7_v3_descriptor_source_candidate_scoreinfos_gt_zero = 1
  phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
  phase7_v3_descriptor_source_candidate_certificate_checked = 1
  phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
  phase7_v3_descriptor_source_missing_required_attempts = 0
  phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
  phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
```

Do not continue to first64 from this smoke. The next gate must run
CPU-authority replay on NEAT1 first1 and prove full output equality plus
Align-side attempt reduction.

## Phase 7 v3: All-Column Replay Stop

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_all_column_replay_stop.md

phase7_broad_restart_v3_all_column_replay_stop =
  candidate_attempt_explosion_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
phase7_broad_restart_v3_next_gate =
  narrower_scoreinfo_reducing_certificate
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
The all-column certificate is a real Gate v3.1 pass, but it is not a viable
Gate v3.2 replay source.

candidate_attempts = 168,730,848
reference_align_attempts = 2,872
candidate_attempt_ratio = 58,750.30x
candidate_align_attempts < reference_align_attempts cannot pass
do_not_run_all_column_cpu_replay = 1
```

Do not run all-column CPU replay and do not continue to first64 from this
branch. The next valid v3 step must design a narrower scoreInfo-reducing
certificate that keeps zero false negatives while reducing CPU Align attempts.

## Phase 7 v3: Narrow Certificate Design

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_design.md

phase7_broad_restart_v3_narrow_certificate_design = defined
phase7_broad_restart_v3_narrow_certificate_status = design_only
phase7_broad_restart_v3_next_gate =
  narrow_certificate_runtime_smoke
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
The next v3 runtime attempt must be default-off:
  required_runtime_env = FASIM_GASAL2_PHASE7_V3_NARROW_CERTIFICATE

It must not reuse the all-column/all-window certificate:
  must_be_narrower_than_all_column = 1
  do_not_use_all_column_or_all_window_certificate = 1
  candidate_attempts < 168,730,848

It must still preserve the certificate contract:
  cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
  candidate_certificate_false_negatives = 0
  missing_required_attempts = 0
  CPU aligner.Align() output authority
```

This design checkpoint does not pass Gate v3.1. It only defines the next
runtime smoke needed to continue Path B.

## Phase 7 v3: Narrow Certificate Runtime Smoke

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_smoke.md

phase7_broad_restart_v3_narrow_certificate_smoke =
  bounded_probe_no_go_missing_certificate
phase7_broad_restart_v3_narrow_certificate_status =
  runtime_smoke_no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
phase7_broad_restart_v3_next_gate =
  real_narrow_certificate_coverage_proof
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
The runtime env is wired and default-off:
  required_runtime_env = FASIM_GASAL2_PHASE7_V3_NARROW_CERTIFICATE

The bounded probe is narrower than all-column replay:
  phase7_v3_descriptor_source_candidate_attempts_lt_all_column = 1
  phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
  phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1

But it does not prove coverage:
  phase7_v3_descriptor_source_candidate_certificate_false_negatives_gt_zero = 1
  phase7_v3_descriptor_source_missing_required_attempts_gt_zero = 1
```

Do not continue this bounded probe to first64. The next valid v3 step must be a
real narrow certificate coverage proof with zero false negatives and zero
missing required attempts.

## Phase 7 v3: Real Narrow Certificate Coverage Proof

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_real_narrow_certificate_coverage_proof.md

phase7_broad_restart_v3_real_narrow_certificate_coverage_proof =
  exact_column_candidate_no_go
phase7_broad_restart_v3_exact_column_candidate_status = no_go
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
phase7_broad_restart_v3_next_gate =
  different_exact_scoreinfo_source_or_seed_certificate
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
Existing long-query exact-column scoreInfo GPU shadow:
  non-opt-in launch no-go:
    active = 0
    error = invalid argument

  shared-memory opt-in:
    active = 1
    gpu_tasks = 432
    scoreinfo_mismatches = 1
    decision = smem_optin_scoreinfo_no_go
```

This exact-column source cannot be the v3 real narrow certificate. Continue
Path B only with a different exact scoreInfo-compatible execution design or a
seed/index certificate that proves coverage without CPU scoreInfo for every
task.

## Phase 7 v3: Next Source Design

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_next_source_design.md

phase7_broad_restart_v3_next_source_design = defined
phase7_broad_restart_v3_next_source_status = design_only
phase7_broad_restart_v3_next_gate =
  different_exact_scoreinfo_source_or_seed_certificate_smoke
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
previous_exact_column_candidate_status = no_go
do_not_continue_all_column_replay = 1
do_not_continue_bounded_narrow_probe = 1
do_not_continue_existing_exact_column_gpu_scoreinfo = 1
allowed_source_1 = different_exact_scoreinfo_compatible_gpu_execution
allowed_source_2 = seed_or_index_certificate
descriptor_source_before_cpu_scoreinfo = 1
cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
candidate_attempts < 168,730,848
candidate_attempts < reference_align_attempts required before v3.2
first1_descriptor_smoke_before_replay = 1
first64_broad_gate_only_after_first1_replay = 1
CPU aligner.Align() output authority
no GPU endpoint/CIGAR/traceback/output authority
no broad_replacement workload-matrix row
```

This design checkpoint is now the next Path B execution contract. It does not
claim Gate v3.1, Gate v3.2, or broad completion.

## Phase 7 v3: Next Source Runtime Smoke

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_next_source_smoke.md

phase7_broad_restart_v3_next_source_smoke = seed_certificate_fail_closed
phase7_broad_restart_v3_next_source_status = runtime_smoke_no_go
required_runtime_env = FASIM_GASAL2_PHASE7_V3_SEED_CERTIFICATE_SOURCE
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
phase7_v3_descriptor_source_candidate_scoreinfos_gt_zero = 1
phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
phase7_v3_descriptor_source_candidate_attempts_lt_all_column = 1
phase7_v3_descriptor_source_candidate_certificate_checked = 1
phase7_v3_descriptor_source_candidate_certificate_false_negatives_gt_zero = 1
phase7_v3_descriptor_source_missing_required_attempts_gt_zero = 1
phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
CPU aligner.Align() output authority
no GPU endpoint/CIGAR/traceback/output authority
no broad_replacement workload-matrix row
phase7_broad_restart_v3_next_gate =
  stronger_seed_certificate_or_different_exact_scoreinfo_source
```

The seed/index source is real pre-scoreInfo plumbing, but the certificate does
not prove coverage. Do not continue it to first1 CPU-authority replay or
first64 broad characterization until false negatives and missing attempts are
zero.

## Phase 7 v3: Strong Seed Runtime Smoke

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_strong_seed_smoke.md

phase7_broad_restart_v3_strong_seed_smoke =
  task_coverage_clean_attempt_coverage_missing
phase7_broad_restart_v3_strong_seed_status =
  runtime_smoke_no_go_attempt_coverage
required_runtime_env = FASIM_GASAL2_PHASE7_V3_STRONG_SEED_CERTIFICATE_SOURCE
phase7_broad_restart_v3_gate_v3_1_pass = 0
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
phase7_v3_descriptor_source_candidate_scoreinfos_ge_baseline = 1
phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1
phase7_v3_descriptor_source_candidate_attempts_lt_all_column = 1
phase7_v3_descriptor_source_candidate_certificate_checked = 1
phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0
phase7_v3_descriptor_source_missing_required_attempts_gt_zero = 1
phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0
phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1
CPU aligner.Align() output authority
no GPU endpoint/CIGAR/traceback/output authority
no broad_replacement workload-matrix row
phase7_broad_restart_v3_next_gate =
  attempt_coverage_seed_certificate_or_different_exact_scoreinfo_source
```

The strong seed source is the first v3 seed/index source with task-level
false negatives at zero on NEAT1 first1. It still cannot continue to replay
because required attempt coverage is missing.

## Phase 7 v3: Attempt-Coverage Seed Runtime Smoke

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_attempt_coverage_seed_smoke.md

phase7_broad_restart_v3_attempt_coverage_seed_smoke =
  attempt_coverage_clean_needs_replay_preflight
phase7_broad_restart_v3_attempt_coverage_seed_status =
  gate_v3_1_pass_candidate_attempts_high
required_runtime_env =
  FASIM_GASAL2_PHASE7_V3_ATTEMPT_COVERAGE_SEED_CERTIFICATE
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

NEAT1 first1 smoke:

```text
reference_scoreinfos = 718
reference_attempts = 2,872
candidate_scoreinfos = 718
raw_seed_hits = 1,051,822
candidate_attempts = 108,694
candidate_min_cover_positions = 463
candidate_certificate_false_negatives = 0
missing_required_attempts = 0
cpu_scoreinfo_calls = 0
cpu_scoreinfo_reduced = 1
candidate_attempts_lt_all_column = 1
candidate_attempts_lt_raw_seed_hits = 1
candidate_attempts_below_reference = 0
candidate_min_cover_positions_below_reference = 1
oracle_min_cover_uses_legacy_attempt_windows = 1
real_pre_scoreinfo_reducer_proven = 0
```

Interpretation:

```text
The seed/index source now proves scoreInfo and attempt-window coverage on
NEAT1 first1, so Gate v3.1 passes.

It does not pass Gate v3.2 because unique seed-position candidates remain much
larger than reference Align attempts. The oracle min-cover lower bound is
promising, but it uses legacy attempt windows, so it is not a real pre-scoreInfo
reducer. Do not continue to first64 or broad_replacement matrix promotion from
this checkpoint.
```

Next gate:

```text
phase7_broad_restart_v3_next_gate =
  oracle_min_cover_replay_shape_probe_or_non_oracle_candidate_reducer
```

## Phase 7 v3: Oracle Min-Cover Replay Smoke

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_oracle_min_cover_replay_smoke.md

phase7_broad_restart_v3_oracle_min_cover_replay_smoke = output_no_go
phase7_broad_restart_v3_oracle_min_cover_replay_status =
  oracle_shape_probe_no_go
required_runtime_env = FASIM_GASAL2_PHASE7_V3_ORACLE_MIN_COVER_REPLAY
phase7_broad_restart_v3_gate_v3_2_shape_probe_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

NEAT1 first1 smoke:

```text
reference_align_attempts = 2,872
candidate_min_cover_positions = 463
candidate_align_attempts = 463
skipped_attempts = 2,409
candidate_align_attempts_lt_reference = 1
digest_match = 0
full_rows_equal = 0
missing_rows = 11
extra_rows = 9
```

Interpretation:

```text
The oracle min-cover shape reduces Align attempts but changes output rows.
It is a no-go shape and must not continue to first64.
```

Next gate:

```text
phase7_broad_restart_v3_next_gate =
  non_oracle_candidate_reducer_or_stop_seed_path
```

## Phase 7 v3: Seed/Index Path Stop

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v3_seed_path_stop.md

phase7_broad_restart_v3_seed_path_stop = current_seed_index_path_stopped
phase7_broad_restart_v3_seed_path_status =
  stopped_no_output_clean_non_oracle_reducer
phase7_broad_restart_v3_gate_v3_1_pass = 1
phase7_broad_restart_v3_gate_v3_2_pass = 0
phase7_broad_restart_v3_may_continue_to_first64 = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
The current seed/index path has useful attempt coverage evidence, but the only
low-attempt replay shape is oracle-only and changes output. There is no current
non-oracle reducer that preserves full output and reduces CPU-authority Align
attempts, so this seed/index path is stopped for broad completion.
```

Next gate:

```text
phase7_broad_restart_v3_next_gate =
  different_scoreinfo_compatible_gpu_execution_design_or_path_a_scope_decision
```

## Phase 7 v4: ScoreInfo-Native GPU Design

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v4_scoreinfo_native_design.md

phase7_broad_restart_v4_scoreinfo_native_design = defined
phase7_broad_restart_v4_status = design_only
phase7_broad_restart_v4_next_gate = legacy_byte_scoreinfo_shadow_first1
phase7_broad_restart_v4_may_claim_completion = 0
phase7_broad_restart_v4_gate_v4_1_pass = 0
phase7_broad_restart_v4_gate_v4_2_pass = 0
phase7_broad_restart_v4_gate_v4_3_pass = 0
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Interpretation:

```text
The next Path B design is no longer GASAL2 standard SW, seed/index min-cover,
all-column replay, bounded-probe certificate, or the existing exact-column GPU
scoreInfo source. It must reproduce Fasim legacy scoreInfo semantics on GPU and
feed the already-clean all-attempt early-stop CPU-authority replay.
```

Next gate:

```text
phase7_broad_restart_v4_next_gate = legacy_byte_scoreinfo_shadow_first1
```

## Phase 7 v4: Legacy-Byte ScoreInfo Host-Contract Smoke

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke.md

Command:
  make check-fasim-gasal2-phase7-v4-legacy-byte-scoreinfo-shadow-runtime-smoke

phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke =
  host_contract_clean_needs_gpu
phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_status =
  host_reconstruction_clean_gpu_rows_zero
phase7_v4_legacy_byte_scoreinfo_shadow_active = 1
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_rows_equal = 1
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_order_equal = 1
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_attempt_windows_equal = 1
phase7_v4_legacy_byte_scoreinfo_shadow_host_contract_pass = 1
phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 0
phase7_v4_legacy_byte_scoreinfo_shadow_gate_v4_1_pass = 0
phase7_broad_restart_v4_broad_gate_pass = 0
```

Interpretation:

```text
host legacy scoreInfo reconstruction:
  clean

GPU legacy scoreInfo source:
  first1 shadow clean

Gate v4.1:
  pass

Next gate:
  gpu_legacy_byte_scoreinfo_source_first1_cpu_authority_replay
```

This checkpoint cannot close Path B because the source is
`host_column_score_reconstruction`, not a GPU/native scoreInfo source.

## Phase 7 v4: GPU Legacy-Byte ScoreInfo First1 Shadow

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke.md

Command:
  make check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-shadow-runtime-smoke

phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke =
  gpu_contract_clean_first1
phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_status =
  first1_gpu_rows_equal_not_broad
phase7_v4_legacy_byte_scoreinfo_shadow_tasks = 48
phase7_v4_legacy_byte_scoreinfo_shadow_cpu_scoreinfo_rows = 718
phase7_v4_legacy_byte_scoreinfo_shadow_host_scoreinfo_rows = 718
phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 718
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_rows_equal = 1
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_order_equal = 1
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_attempt_windows_equal = 1
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_mismatches = 0
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_false_negatives = 0
phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_extra_required_attempts = 0
phase7_v4_legacy_byte_scoreinfo_shadow_gate_v4_1_pass = 1
phase7_broad_restart_v4_broad_gate_pass = 0
```

Interpretation:

```text
GPU legacy-byte scoreInfo shadow on NEAT1 first1:
  clean

Broad completion:
  still open

Next gate:
  gpu_legacy_byte_scoreinfo_source_first1_cpu_authority_replay
```

This checkpoint cannot close Path B because GPU rows are still shadow-only.
The next phase must feed GPU scoreInfo rows through a CPU-authority replay,
prove full row/digest equality, and reduce Align-side work before any first64
broad gate.

## Phase 7 v4: GPU Legacy-Byte ScoreInfo Source Replay First1

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke.md

Command:
  make check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-source-replay-runtime-smoke

phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke =
  cpu_authority_replay_clean_first1
phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_status =
  first1_replay_clean_needs_first64_broad_gate
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_digest_match = 1
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_rows_equal = 1
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_order_equal = 1
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_attempt_windows_equal = 1
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempts = 2008
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_reference_align_attempts = 2872
phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempt_reduction = 864
phase7_broad_restart_v4_gate_v4_2_pass = 1
phase7_broad_restart_v4_broad_gate_pass = 0
```

Interpretation:

```text
GPU legacy-byte scoreInfo source replay on NEAT1 first1:
  clean

CPU-authority replay:
  aligner.Align remains endpoint/CIGAR/output authority

Broad completion:
  still open

Next gate:
  gpu_legacy_byte_scoreinfo_source_first64_broad_gate
```

This first1 checkpoint cannot close Path B by itself. Its required follow-up
was a first64 or equivalent broad workload with full equality and a wall-time
win before adding a `broad_replacement` workload-matrix row. That follow-up is
now recorded in the next section as a correctness-clean but performance no-go
checkpoint, so the current v4 source replay implementation must not continue as
the active broad path.

## Phase 7 v4: GPU Legacy-Byte ScoreInfo Source First64 Broad Gate

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate.md

phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate =
  correctness_clean_performance_no_go
phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_status =
  first64_correctness_clean_performance_no_go
baseline_wall_seconds = 86.358386
candidate_wall_seconds = 134.744406
candidate_vs_baseline = 0.640905
digest_match = 1
candidate_gpu_scoreinfo_rows = 52994
candidate_source_replay_scoreinfo_rows = 52994
candidate_realpath_extend_align_attempts = 140087
reference_align_attempts = 211976
align_attempt_reduction = 71889
performance_gate_pass = 0
phase7_broad_restart_v4_gate_v4_3_pass = 0
phase7_broad_restart_v4_runtime_next_gate =
  different_gpu_execution_design_or_path_a_scope_decision
```

Interpretation:

```text
Correctness:
  clean digest and clean v4.2 source replay contract

Align side:
  attempts reduced from 211,976 to 140,087

Performance:
  no-go, because candidate wall time is slower than CPU baseline

Broad completion:
  still open
```

The current v4 source replay implementation must not be promoted to
`broad_replacement`. It does useful CPU Align attempt reduction, but it does
not reduce total wall time on the first64 broad gate. Any further Path B work
requires a different GPU execution design, not another promotion of this
source replay implementation.

## Phase 7 v5: Fused ScoreInfo Consumer Design

Current evidence:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_design.md

phase7_broad_restart_v5_fused_scoreinfo_consumer_design = defined
phase7_broad_restart_v5_status = design_only
phase7_broad_restart_v5_design_family =
  fused_gpu_scoreinfo_to_candidate_attempt_descriptors
phase7_broad_restart_v5_differs_from_v4_source_replay = 1
phase7_broad_restart_v5_may_claim_completion = 0
phase7_broad_restart_v5_gate_v5_1_pass = 1
phase7_broad_restart_v5_gate_v5_2_pass = 1
phase7_broad_restart_v5_gate_v5_3_pass = 0
phase7_broad_restart_v5_next_gate =
  phase7_gate_v5_3_first64_broad_gate
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

Implementation plan:

```text
Document:
  docs/superpowers/plans/2026-06-13-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer.md

phase7_broad_restart_v5_implementation_plan = defined
phase7_broad_restart_v5_runtime_first_gate =
  fused_scoreinfo_consumer_descriptor_contract_first1
Task 1: Env, Stats, And Default-Off Telemetry
Task 2: Descriptor Contract Runtime Smoke
Task 3: CPU-Authority Replay First1 Gate
Task 4: Roadmap Checkpoint And Current-State Wiring
Task 5: First64 Broad Gate Characterization
make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-implementation-plan
```

Runtime scaffold checkpoint:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke.md

phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke =
  post_scoreinfo_descriptor_scaffold_no_go
phase7_broad_restart_v5_runtime_scaffold_scoreinfo_prealign_reduced = 0
phase7_broad_restart_v5_gate_v5_1_pass = 0
phase7_broad_restart_v5_runtime_scaffold_next_gate =
  true_pre_scoreinfo_fused_descriptor_source
make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-fused-scoreinfo-consumer-runtime-smoke
```

True pre-scoreInfo descriptor source design:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design.md

phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design = defined
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_status =
  design_only
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate =
  runtime_smoke_true_pre_scoreinfo_descriptor_source_first1
make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-design
```

True pre-scoreInfo descriptor source env scaffold:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_env_scaffold.md

phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_env_scaffold =
  fail_closed_no_source
required_runtime_env =
  FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE
phase7_v5_true_pre_scoreinfo_descriptor_source_requested = 1
phase7_v5_true_pre_scoreinfo_descriptor_source_active = 0
phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass = 0
make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-env-scaffold
```

True pre-scoreInfo descriptor source strict runtime smoke:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.md

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
```

CPU-authority replay smoke:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_smoke.md

phase7_broad_restart_v5_cpu_authority_replay_smoke =
  gate_v5_2_pass_first1
root_cause_fix = legacy_float_identity_cutlength_descriptor_generation
phase7_v5_cpu_authority_replay_full_rows_equal = 1
phase7_v5_cpu_authority_replay_digest_match = 1
phase7_v5_cpu_authority_replay_candidate_align_attempts = 2008
phase7_v5_cpu_authority_replay_reference_align_attempts = 2872
phase7_broad_restart_v5_gate_v5_2_pass = 1
next_required_gate = phase7_gate_v5_3_first64_broad_gate
make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-smoke
```

CUDA descriptor emission design:

```text
Document:
  docs/fasim_gasal2_phase7_broad_restart_v5_cuda_descriptor_emission_design.md

phase7_broad_restart_v5_cuda_descriptor_emission_design = defined
phase7_broad_restart_v5_cuda_descriptor_emission_status = design_only
phase7_broad_restart_v5_cuda_descriptor_emission_may_claim_completion = 0
new_cuda_api = prealign_cuda_emit_legacy_byte_attempt_descriptors
output_contract = compact_attempt_descriptors_not_scoreinfo_rows
host-visible full legacy scoreInfo row stream = forbidden
CPU aligner.Align() authority replay = 1
GPU endpoint/CIGAR/traceback/output authority = 0
next_gate = runtime_smoke_true_pre_scoreinfo_descriptor_source_first1
make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-descriptor-emission-design
```

Interpretation:

```text
The next Path B runtime must be different from v4 source replay:
  Do not materialize the full legacy scoreInfo row stream as a host-visible intermediate.
  Compute legacy byte scoreInfo and consume the row stream in the same GPU execution design.
  Emit compact candidate attempt descriptors, not endpoint, CIGAR, traceback, output, or digest authority.

CPU aligner.Align() remains the only endpoint/CIGAR/traceback/output/digest
authority.
```

Next gate:

```text
phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate =
  runtime_smoke_true_pre_scoreinfo_descriptor_source_first1
```

## Minimal Evidence Needed To Finish

For scoped completion:

```text
user accepts Path A
Phase 0 reproducibility clean
Phase 1 scoped product gates clean
Phase 5 archive gates clean
Phase 6 scoped matrix clean
Phase 8 decision records scoped completion
```

For broad completion:

```text
Phase 0 reproducibility clean
Phase 2 full-output authority clean
Phase 7 v3 or a later architecture passes NEAT1 first64
scoreInfo/preAlign work is reduced or replaced
Align-side work is reduced or replaced
candidate wall time beats CPU authority
Phase 6 has passing broad_replacement row
Phase 8 decision records broad completion
```
