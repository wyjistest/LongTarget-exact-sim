# Fasim GASAL2 Broad Co-Designed ScoreInfo Consumer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prototype a co-designed scoreInfo plus replacement-consumer shadow that can move the full scoreInfo/preAlign GPU/GASAL2 objective beyond the current scoped milestone.

**Architecture:** Keep CPU output and digest authoritative while adding a default-off broad shadow that generates a GASAL2/GPU scoreInfo attempt stream and consumes it with a stateful replacement-consumer shadow. The prototype must preserve legacy scoreInfo-level emission semantics, compare complete task triplex lists against CPU authority, and prove that both GPU scoreInfo work and CPU realpath extend/align replay are reduced before any performance claim.

**Tech Stack:** C++11 Fasim runtime, GASAL2/CUDA scoreInfo bridge, existing runner/report telemetry, shell/Python check gates, Makefile.

Goal: Prototype a co-designed scoreInfo plus replacement-consumer shadow.

Architecture: Keep CPU output and digest authoritative.

Tech Stack: C++11 Fasim runtime, GASAL2/CUDA scoreInfo bridge.

---

## Boundary

This plan continues the full objective, not the scoped top5 or MALAT1 milestone.

The current accepted milestone remains:

```text
short-query/H19 top5 artifact: scoped go
MEG3 grouped tiny-region top5 wrapper: scoped go
MALAT1-like group32 two-contract scoreInfo runtime: scoped go
```

The full objective remains open. The next broad-path prototype must satisfy the
existing broad-path decision:

```text
decision = broad_path_requires_co_designed_scoreinfo_and_consumer
```

Do not promote:

```text
current selector/global-state NEAT1 path
selected-only replay
prefix replay without align-attempt reduction
score-prepass state-machine consumer trust
segmented GASAL2 traceback
top5 artifact path as full-output replacement
MALAT1 scoped two-contract runtime as broad replacement
```

CPU fastSIM_extend_from_scoreinfo remains authority until this shadow proves
complete task triplex equivalence and external digest or full-row equivalence.
GPU endpoint/CIGAR/traceback remain non-authoritative.

## Diagnostic Interface

Add one default-off umbrella flag:

```text
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW=1
```

When unset, report:

```text
benchmark.fasim_gasal2_broad_path_requested=0
benchmark.fasim_gasal2_broad_path_active=0
```

When set, report at least:

```text
broad_path_requested
broad_path_active
broad_path_tasks
broad_path_scoreinfo_groups
broad_path_scoreinfo_seconds
broad_path_consumer_seconds
broad_path_align_attempts
broad_path_selected_attempts
broad_path_triplex_mismatches
broad_path_missing_triplexes
broad_path_extra_triplexes
broad_path_first_mismatch
broad_path_digest_match
broad_path_full_rows_equal
broad_path_candidate_wall_seconds
broad_path_baseline_wall_seconds
broad_path_candidate_vs_baseline
broad_path_cpu_triplex_path
broad_path_cpu_triplexes
broad_path_cpu_triplex_digest
broad_path_planner_descriptor_path
broad_path_planner_descriptors
broad_path_planner_descriptor_digest
```

Keep existing comparison counters visible:

```text
two_contract_used
two_contract_fallbacks
two_contract_score_mismatches
two_contract_min_score_mismatches
two_contract_scoreinfo_mismatches
realpath_used
realpath_fallbacks
gpu_scoreinfo_groups
cpu_scoreinfo_groups
```

## Correctness Contract

The replacement-consumer shadow must preserve scoreInfo-level single-emission
semantics and the legacy break/best-end state:

```text
for each scoreInfo in legacy order:
  sweep candidate windows in legacy order
  if alignment.sw_score >= scoreInfo.score:
      emit once and stop sweeping this scoreInfo
  else if ref_end == cutlength - 1:
      remember the best/last alignment for this scoreInfo
  after the sweep:
      emit at most one best/last alignment for this scoreInfo
```

The shadow must compare complete task triplex lists:

```text
target record id
scoreInfo identity
query start
query end
target start
target end
score
emission reason
legacy order index
```

The shadow must fail closed when:

```text
triplex_mismatches > 0
missing_triplexes > 0
extra_triplexes > 0
digest_match = 0 for the claimed scope
full_rows_equal = 0 for the claimed scope
```

## NEAT1 First64 Hard Gate

NEAT1 first64 hard gate:

NEAT1 first64 is the broad gate:

```text
digest clean or full row-set equality clean
triplex_mismatches = 0
scoreinfo_gasal2_active = 1 or explicitly scoped equivalent active path
fallback = 0
scoreInfo mismatches = 0
candidate_wall_seconds < 86.0335
candidate_vs_baseline > 1.0x
GPU scoreInfo plus replacement-consumer total beats CPU fallback
realpath_extend_align_attempts materially reduced or replaced
MALAT1 scoped product-readiness remains clean
```

The plan must reduce both GPU scoreInfo work and CPU realpath extend/align work.
Kernel-only speedup is not enough.

Stop if selected-only replay is required.
Stop if prefix replay is required and align attempts are not reduced.
Stop if NEAT1 remains slower than CPU fallback.

## Task 1: Add the plan gate

**Files:**
- Create: `scripts/check_fasim_gasal2_broad_co_designed_scoreinfo_consumer_plan.sh`
- Create: `docs/plans/2026-06-09-fasim-gasal2-broad-co-designed-scoreinfo-consumer.md`
- Modify: `Makefile`
- Modify: `docs/fasim_gasal2_broad_path_architecture_gate.md`
- Modify: `docs/fasim_gasal2_replacement_consumer_shadow_requirements.md`
- Modify: `docs/fasim_gasal2_neat1_next_architecture_requirements.md`
- Modify: `docs/fasim_gasal2_scoreinfo_current_state.md`
- Modify: `docs/fasim_gasal2_scoreinfo_completion_gap.md`
- Modify: `docs/fasim_gasal2_full_goal_decision.md`

- [x] **Step 1: Write the failing static checker**

Create `scripts/check_fasim_gasal2_broad_co_designed_scoreinfo_consumer_plan.sh`
to require this plan, the broad-path architecture gate, replacement-consumer
requirements, NEAT1 next-architecture requirements, speed ceiling, scoped
milestone rollup, current-state doc, completion-gap doc, full-goal doc, and
Makefile wiring.

- [x] **Step 2: Verify red**

Run:

```bash
bash scripts/check_fasim_gasal2_broad_co_designed_scoreinfo_consumer_plan.sh
```

Expected before the plan exists:

```text
missing broad co-designed scoreInfo/consumer plan dependency
```

- [ ] **Step 3: Add Makefile target**

Add:

```make
check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan:
	bash ./scripts/check_fasim_gasal2_broad_co_designed_scoreinfo_consumer_plan.sh
```

Add the target to `.PHONY` and to the
`check-fasim-gasal2-scoreinfo-current-state` dependency list.

- [ ] **Step 4: Cross-link the plan**

Add the plan gate to:

```text
docs/fasim_gasal2_broad_path_architecture_gate.md
docs/fasim_gasal2_replacement_consumer_shadow_requirements.md
docs/fasim_gasal2_neat1_next_architecture_requirements.md
docs/fasim_gasal2_scoreinfo_current_state.md
docs/fasim_gasal2_scoreinfo_completion_gap.md
docs/fasim_gasal2_full_goal_decision.md
```

- [ ] **Step 5: Verify green**

Run:

```bash
make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan
```

Expected:

```text
ok
```

## Task 2: Add default-off broad shadow telemetry

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `fasim/fastsim.h`
- Create: `scripts/check_fasim_gasal2_broad_scoreinfo_consumer_shadow_env.sh`
- Modify: `Makefile`

- [ ] **Step 1: Write the failing env checker**

Create a checker that runs the smallest existing Fasim fixture twice:

```bash
env -u FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW "$BIN" ...
env FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW=1 "$BIN" ...
```

Expected before implementation:

```text
missing benchmark.fasim_gasal2_broad_path_requested
```

- [ ] **Step 2: Add inactive telemetry**

Add report keys:

```text
benchmark.fasim_gasal2_broad_path_requested=0
benchmark.fasim_gasal2_broad_path_active=0
```

when the env is unset.

- [ ] **Step 3: Add requested-but-inactive telemetry**

When the env is set but no broad shadow is implemented, report:

```text
benchmark.fasim_gasal2_broad_path_requested=1
benchmark.fasim_gasal2_broad_path_active=0
benchmark.fasim_gasal2_broad_path_decision=not_implemented
```

- [ ] **Step 4: Verify env gate**

Run:

```bash
make check-fasim-gasal2-broad-scoreinfo-consumer-shadow-env
```

Expected:

```text
requested=0 active=0 without env
requested=1 active=0 decision=not_implemented with env
```

## Task 3: Export CPU authority triplex stream

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `fasim/fastsim.h`
- Create: `scripts/check_fasim_gasal2_broad_scoreinfo_consumer_triplex_export.sh`
- Modify: `Makefile`

- [x] **Step 1: Write the failing triplex export checker**

Run NEAT1 first1 or the smallest long-query fixture with:

```text
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW=1
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_EXPORT_CPU_TRIPLEX=1
```

Expected before implementation:

```text
missing broad_path_cpu_triplexes
```

- [x] **Step 2: Add a CPU authority triplex collector**

Collect the legacy output surface from `fastSIM_extend_from_scoreinfo()` without
changing emission:

```text
scoreInfo identity
legacy order index
selected align attempt index
query start/end
target start/end
score
emission reason: threshold_hit or best_last_at_cutlength
```

- [x] **Step 3: Write report artifact**

Write a deterministic TSV artifact path in the runner report:

```text
broad_path_cpu_triplex_path
broad_path_cpu_triplexes
broad_path_cpu_triplex_digest
```

- [x] **Step 4: Verify export**

Run:

```bash
make check-fasim-gasal2-broad-scoreinfo-consumer-triplex-export
```

Expected:

```text
broad_path_cpu_triplexes > 0
digest clean
normal output digest unchanged
```

## Task 4: Implement co-designed scoreInfo attempt planner

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `fasim/gasal2_align_bridge.cpp`
- Modify: `fasim/gasal2_align_bridge.h`
- Create: `scripts/check_fasim_gasal2_broad_scoreinfo_attempt_planner.sh`
- Modify: `Makefile`

- [x] **Step 1: Write the failing planner checker**

Run a long-query sample with:

```text
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW=1
FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_PLANNER=1
```

Expected before implementation:

```text
broad_path_scoreinfo_groups = 0
```

- [x] **Step 2: Add planner descriptors**

Generate descriptors that retain enough state for the consumer:

```text
scoreInfo identity
candidate window order
min score
query window bounds
target window bounds
cutlength
legacy order index
```

The planner must not reduce attempts unless it can still emulate the
scoreInfo-level break/best-end state.

- [x] **Step 3: Add GASAL2/GPU scoreInfo execution timing**

Report:

```text
broad_path_tasks
broad_path_scoreinfo_groups
broad_path_scoreinfo_seconds
broad_path_align_attempts
broad_path_selected_attempts
```

- [x] **Step 4: Verify planner gate**

Run:

```bash
make check-fasim-gasal2-broad-scoreinfo-attempt-planner
```

Expected:

```text
broad_path_scoreinfo_groups > 0
broad_path_align_attempts >= broad_path_selected_attempts
CPU output digest unchanged
```

## Task 5: Implement replacement-consumer state shadow

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `fasim/fastsim.h`
- Create: `scripts/check_fasim_gasal2_broad_replacement_consumer_shadow.sh`
- Modify: `Makefile`

- [x] **Step 1: Write the failing consumer checker**

Run the smallest long-query fixture with the planner enabled.

```text
FASIM_GASAL2_BROAD_REPLACEMENT_CONSUMER_SHADOW=1
```

Expected before implementation:

```text
expected active=1 for broad replacement consumer shadow, got 0
```

- [x] **Step 2: Implement stateful consumer shadow**

Consume planner results by scoreInfo, not by globally selected attempts:

```text
for each scoreInfo:
  preserve candidate window order
  emit threshold hit once
  otherwise emit at most one best/last-at-cutlength attempt
```

The current checkpoint uses the existing full-replay scoreInfo state machine
as a CPU-backed replacement-consumer shadow. It remains diagnostic only: CPU
output/digest stay authoritative, and GASAL2 endpoint/CIGAR/traceback are not
used as production output.

- [x] **Step 3: Compare complete task triplex lists**

Report:

```text
broad_path_triplex_mismatches
broad_path_missing_triplexes
broad_path_extra_triplexes
broad_path_first_mismatch
broad_path_consumer_seconds
```

- [x] **Step 4: Verify consumer gate**

Run:

```bash
make check-fasim-gasal2-broad-replacement-consumer-shadow
```

Expected for promotion candidate:

```text
broad_path_triplex_mismatches = 0
broad_path_missing_triplexes = 0
broad_path_extra_triplexes = 0
```

Measured NEAT1 first1 smoke:

```text
decision = replacement_consumer_shadow_active
broad_path_active = 1
broad_path_tasks = 48
broad_path_scoreinfo_groups = 718
broad_path_align_attempts = 3,590
broad_path_triplex_mismatches = 0
broad_path_missing_triplexes = 0
broad_path_extra_triplexes = 0
normal output digest = 8e157aac041d698751fd234ba88bce9226cd900aec48ab0aa1c27ce4cbbfe437
```

If the checker reports selected-only behavior or prefix replay with unchanged
align attempts, stop this architecture.

## Task 6: Add NEAT1 first64 characterization gate

**Files:**
- Create: `scripts/check_fasim_gasal2_broad_neat1_first64_result.sh`
- Create: `scripts/characterize_fasim_gasal2_broad_neat1_first64.sh`
- Modify: `Makefile`

- [x] **Step 1: Write the result checker**

The checker reads a produced report and fails unless:

```text
broad_path_active = 1
broad_path_triplex_mismatches = 0
broad_path_missing_triplexes = 0
broad_path_extra_triplexes = 0
broad_path_candidate_wall_seconds < 86.0335
broad_path_candidate_vs_baseline > 1.0
broad_path_scoreinfo_seconds + broad_path_consumer_seconds < baseline CPU fallback scoreInfo/consumer time
realpath_extend_align_attempts materially reduced or replaced
```

- [x] **Step 2: Add characterization runner**

Run NEAT1 first64 with the broad shadow enabled and write a report artifact.

- [x] **Step 3: Verify characterization gate**

Run:

```bash
make check-fasim-gasal2-broad-neat1-first64-result
```

Expected until a measured passing result exists:

```text
decision=broad_path_not_proven
```

Measured NEAT1 first64 result:

```text
decision = broad_path_current_architecture_no_go
digest clean
broad_path_active = 1
broad_path_triplex_mismatches = 0
broad_path_missing_triplexes = 0
broad_path_extra_triplexes = 0
baseline_wall_seconds = 86.932816
candidate_wall_seconds = 288.4177
candidate_vs_baseline = 0.301413x
broad_path_scoreinfo_seconds = 19.1704
broad_path_consumer_seconds = 52.0465
baseline_cpu_reference_seconds = 52.0833
broad_path_align_attempts = 264,970
realpath_extend_align_attempts = 140,087
decision_reasons:
  candidate_wall_not_below_neat1_baseline_ceiling
  candidate_vs_baseline_not_above_1
  broad_scoreinfo_consumer_not_below_cpu_reference
  align_attempts_not_reduced
```

This is a correctness-clean, performance-no-go checkpoint for the current
broad architecture.

## Task 7: Update decision docs from measured evidence

**Files:**
- Modify: `docs/fasim_gasal2_full_goal_decision.md`
- Modify: `docs/fasim_gasal2_scoreinfo_completion_gap.md`
- Modify: `docs/fasim_gasal2_scoreinfo_current_state.md`
- Modify: `docs/fasim_gasal2_broad_path_architecture_gate.md`

- [ ] **Step 1: If NEAT1 first64 passes, record scoped broad-go**

Only record a go if all hard-gate fields pass. The text must include:

```text
decision = broad_path_candidate_go
NEAT1 first64 candidate_vs_baseline > 1.0x
triplex_mismatches = 0
full objective remains open until claimed workload scope is explicit
```

- [x] **Step 2: If NEAT1 first64 fails, record stop**

If correctness or performance fails, record:

```text
decision = broad_path_current_architecture_no_go
full objective remains open
```

- [ ] **Step 3: Re-run gates**

Run:

```bash
make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan
make check-fasim-gasal2-broad-path-architecture-gate
make check-fasim-gasal2-replacement-consumer-shadow-requirements
make check-fasim-gasal2-neat1-next-architecture-requirements
make check-fasim-gasal2-scoreinfo-completion-gap
make check-fasim-gasal2-full-goal-decision
```

Expected:

```text
ok
```
