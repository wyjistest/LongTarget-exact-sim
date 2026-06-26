# Fasim GASAL2 Phase 7 v5 Fused ScoreInfo Consumer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the first v5 fused scoreInfo consumer runtime gates without granting GPU endpoint/CIGAR/traceback/output authority.

**Architecture:** Add a default-off v5 runtime path that reuses the existing legacy-byte scoreInfo GPU source and all-attempt CPU-authority replay boundaries, but records compact candidate descriptor contract telemetry instead of exposing the full scoreInfo row stream as the promoted interface. The first gate proves descriptor coverage on NEAT1 first1; later gates can feed those descriptors into CPU `aligner.Align()` replay and then run first64 broad characterization.

**Tech Stack:** Fasim C++ runtime, GASAL2 bridge stats, shell checkers, Makefile roadmap gates, NEAT1 fixture runs, Markdown checkpoint docs.

---

## File Structure

- Modify `fasim/gasal2_align_bridge.h`: add v5 telemetry fields to `FasimGasal2Stats`.
- Modify `fasim/gasal2_align_bridge.cpp`: add v5 env/runtime helpers and stats recorders.
- Modify `fasim/gasal2_align_bridge_stub.cpp`: emit default-zero v5 telemetry for non-GASAL2 builds.
- Modify `fasim/Fasim-LongTarget.cpp`: request v5 runtime, print v5 telemetry, and wire descriptor contract metrics at the existing Phase 7 task/scoreInfo/attempt boundary.
- Create `scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_env.sh`: parser/static env checker.
- Create `scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime_smoke.sh`: NEAT1 first1 runtime smoke.
- Create `docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke.md`: first runtime checkpoint.
- Create `scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke.sh`: roadmap checker for the smoke.
- Modify `Makefile`: add v5 env/runtime/roadmap targets and current-state dependency.
- Modify `scripts/summarize_fasim_gasal2_roadmap_current_state.py` and `scripts/check_fasim_gasal2_roadmap_current_state.sh`: add v5 runtime smoke output once it exists.

The v5 path uses this env:

```text
FASIM_GASAL2_PHASE7_V5_FUSED_SCOREINFO_CONSUMER=1
```

Required telemetry prefix:

```text
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_
```

Required telemetry fields:

```text
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_requested
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_active
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_tasks
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_reference_scoreinfos
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_reference_attempts
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_scoreinfos
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_attempts
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_descriptor_false_negatives
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_missing_required_attempts
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_extra_descriptor_attempts
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_scoreinfo_prealign_reduced
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_cpu_align_authority
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority=0
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gate_v5_1_pass
```

## Invariants

```text
Do not materialize the full legacy scoreInfo row stream as a host-visible promoted interface.
CPU aligner.Align() remains the only endpoint, CIGAR, traceback, output, and digest authority.
full row-set/digest equality = required
candidate_wall_seconds < baseline_wall_seconds = required before broad completion
no broad_replacement workload-matrix row before Gate v5.3 passes
```

## Task 1: Env, Stats, And Default-Off Telemetry

**Files:**
- Modify: `fasim/gasal2_align_bridge.h`
- Modify: `fasim/gasal2_align_bridge.cpp`
- Modify: `fasim/gasal2_align_bridge_stub.cpp`
- Modify: `fasim/Fasim-LongTarget.cpp`
- Create: `scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_env.sh`
- Modify: `Makefile`

- [ ] **Step 1: Write the failing env checker**

Create `scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_env.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$ROOT/fasim/gasal2_align_bridge.h" \
  "$ROOT/fasim/gasal2_align_bridge.cpp" \
  "$ROOT/fasim/gasal2_align_bridge_stub.cpp" \
  "$ROOT/fasim/Fasim-LongTarget.cpp" \
  "$ROOT/Makefile" <<'PY'
from pathlib import Path
import sys

header, bridge, stub, main, makefile = [Path(p) for p in sys.argv[1:]]
texts = {str(p): p.read_text(encoding="utf-8") for p in [header, bridge, stub, main, makefile]}

required = {
    str(bridge): [
        "FASIM_GASAL2_PHASE7_V5_FUSED_SCOREINFO_CONSUMER",
        "fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime",
        "fasim_gasal2_record_phase7_v5_fused_scoreinfo_consumer",
    ],
    str(header): [
        "phase7_v5_fused_scoreinfo_consumer_requested",
        "phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_attempts",
        "phase7_v5_fused_scoreinfo_consumer_gate_v5_1_pass",
    ],
    str(main): [
        "fasim_print_phase7_v5_fused_scoreinfo_consumer_stats",
        "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_requested",
    ],
    str(stub): [
        "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_requested=0",
        "benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority=0",
    ],
    str(makefile): [
        "check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-env:",
    ],
}

for path, phrases in required.items():
    text = texts[path]
    for phrase in phrases:
        if phrase not in text:
            raise SystemExit(f"{path} missing phrase: {phrase}")

print("phase7_v5_fused_scoreinfo_consumer_env=pass")
print("ok")
PY
```

- [ ] **Step 2: Run the checker to verify RED**

Run:

```bash
bash scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_env.sh
```

Expected: FAIL with a missing `FASIM_GASAL2_PHASE7_V5_FUSED_SCOREINFO_CONSUMER`
or missing v5 stats phrase.

- [ ] **Step 3: Add minimal stats fields**

Add these fields near the Phase 7 v3 fields in `fasim/gasal2_align_bridge.h`:

```cpp
uint64_t phase7_v5_fused_scoreinfo_consumer_requested;
uint64_t phase7_v5_fused_scoreinfo_consumer_active;
uint64_t phase7_v5_fused_scoreinfo_consumer_tasks;
uint64_t phase7_v5_fused_scoreinfo_consumer_reference_scoreinfos;
uint64_t phase7_v5_fused_scoreinfo_consumer_reference_attempts;
uint64_t phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_scoreinfos;
uint64_t phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_attempts;
uint64_t phase7_v5_fused_scoreinfo_consumer_descriptor_false_negatives;
uint64_t phase7_v5_fused_scoreinfo_consumer_missing_required_attempts;
uint64_t phase7_v5_fused_scoreinfo_consumer_extra_descriptor_attempts;
uint64_t phase7_v5_fused_scoreinfo_consumer_scoreinfo_prealign_reduced;
uint64_t phase7_v5_fused_scoreinfo_consumer_cpu_align_authority;
uint64_t phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority;
uint64_t phase7_v5_fused_scoreinfo_consumer_gate_v5_1_pass;
```

Initialize them to `0` in the `FasimGasal2Stats` constructor.

- [ ] **Step 4: Add runtime helper and recorder**

Add prototypes to `fasim/gasal2_align_bridge.h`:

```cpp
bool fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime();
void fasim_gasal2_record_phase7_v5_fused_scoreinfo_consumer(
	uint64_t tasks,
	uint64_t referenceScoreInfos,
	uint64_t referenceAttempts,
	uint64_t gpuDescriptorScoreInfos,
	uint64_t gpuDescriptorAttempts,
	uint64_t falseNegatives,
	uint64_t missingRequiredAttempts,
	uint64_t extraDescriptorAttempts,
	bool scoreInfoPrealignReduced,
	bool cpuAlignAuthority,
	bool gateV51Pass);
```

Add implementation to `fasim/gasal2_align_bridge.cpp`:

```cpp
bool fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime()
{
	return env_enabled("FASIM_GASAL2_PHASE7_V5_FUSED_SCOREINFO_CONSUMER");
}

void fasim_gasal2_record_phase7_v5_fused_scoreinfo_consumer(
	uint64_t tasks,
	uint64_t referenceScoreInfos,
	uint64_t referenceAttempts,
	uint64_t gpuDescriptorScoreInfos,
	uint64_t gpuDescriptorAttempts,
	uint64_t falseNegatives,
	uint64_t missingRequiredAttempts,
	uint64_t extraDescriptorAttempts,
	bool scoreInfoPrealignReduced,
	bool cpuAlignAuthority,
	bool gateV51Pass)
{
	g_stats.phase7_v5_fused_scoreinfo_consumer_requested = 1;
	g_stats.phase7_v5_fused_scoreinfo_consumer_active =
		gateV51Pass || gpuDescriptorAttempts > 0 ? 1 : 0;
	g_stats.phase7_v5_fused_scoreinfo_consumer_tasks += tasks;
	g_stats.phase7_v5_fused_scoreinfo_consumer_reference_scoreinfos += referenceScoreInfos;
	g_stats.phase7_v5_fused_scoreinfo_consumer_reference_attempts += referenceAttempts;
	g_stats.phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_scoreinfos += gpuDescriptorScoreInfos;
	g_stats.phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_attempts += gpuDescriptorAttempts;
	g_stats.phase7_v5_fused_scoreinfo_consumer_descriptor_false_negatives += falseNegatives;
	g_stats.phase7_v5_fused_scoreinfo_consumer_missing_required_attempts += missingRequiredAttempts;
	g_stats.phase7_v5_fused_scoreinfo_consumer_extra_descriptor_attempts += extraDescriptorAttempts;
	g_stats.phase7_v5_fused_scoreinfo_consumer_scoreinfo_prealign_reduced =
		scoreInfoPrealignReduced ? 1 : 0;
	g_stats.phase7_v5_fused_scoreinfo_consumer_cpu_align_authority =
		cpuAlignAuthority ? 1 : 0;
	g_stats.phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority = 0;
	g_stats.phase7_v5_fused_scoreinfo_consumer_gate_v5_1_pass =
		gateV51Pass ? 1 : 0;
}
```

- [ ] **Step 5: Add telemetry printer and stub zeros**

Add a printer in `fasim/Fasim-LongTarget.cpp`:

```cpp
static inline void fasim_print_phase7_v5_fused_scoreinfo_consumer_stats(
	const FasimGasal2Stats &stats)
{
	const char *prefix =
		"benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_";
	std::cerr << prefix << "requested="
	          << stats.phase7_v5_fused_scoreinfo_consumer_requested << "\n";
	std::cerr << prefix << "active="
	          << stats.phase7_v5_fused_scoreinfo_consumer_active << "\n";
	std::cerr << prefix << "tasks="
	          << stats.phase7_v5_fused_scoreinfo_consumer_tasks << "\n";
	std::cerr << prefix << "reference_scoreinfos="
	          << stats.phase7_v5_fused_scoreinfo_consumer_reference_scoreinfos << "\n";
	std::cerr << prefix << "reference_attempts="
	          << stats.phase7_v5_fused_scoreinfo_consumer_reference_attempts << "\n";
	std::cerr << prefix << "gpu_descriptor_scoreinfos="
	          << stats.phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_scoreinfos << "\n";
	std::cerr << prefix << "gpu_descriptor_attempts="
	          << stats.phase7_v5_fused_scoreinfo_consumer_gpu_descriptor_attempts << "\n";
	std::cerr << prefix << "descriptor_false_negatives="
	          << stats.phase7_v5_fused_scoreinfo_consumer_descriptor_false_negatives << "\n";
	std::cerr << prefix << "missing_required_attempts="
	          << stats.phase7_v5_fused_scoreinfo_consumer_missing_required_attempts << "\n";
	std::cerr << prefix << "extra_descriptor_attempts="
	          << stats.phase7_v5_fused_scoreinfo_consumer_extra_descriptor_attempts << "\n";
	std::cerr << prefix << "scoreinfo_prealign_reduced="
	          << stats.phase7_v5_fused_scoreinfo_consumer_scoreinfo_prealign_reduced << "\n";
	std::cerr << prefix << "cpu_align_authority="
	          << stats.phase7_v5_fused_scoreinfo_consumer_cpu_align_authority << "\n";
	std::cerr << prefix << "gpu_endpoint_cigar_traceback_output_authority="
	          << stats.phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority << "\n";
	std::cerr << prefix << "gate_v5_1_pass="
	          << stats.phase7_v5_fused_scoreinfo_consumer_gate_v5_1_pass << "\n";
}
```

Add matching zero metrics to `fasim/gasal2_align_bridge_stub.cpp`.

- [ ] **Step 6: Add Makefile target and verify GREEN**

Add:

```make
check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-env:
	bash ./scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_env.sh

.PHONY: check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-env
```

Run:

```bash
make check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-env
```

Expected: PASS and print `phase7_v5_fused_scoreinfo_consumer_env=pass`.

## Task 2: Descriptor Contract Runtime Smoke

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Create: `scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime_smoke.sh`
- Modify: `Makefile`

- [ ] **Step 1: Write the failing runtime smoke**

Create `scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime_smoke.sh` modeled on the v4 first1 smoke. It must run baseline and candidate on NEAT1 first1:

```bash
run_case "$WORK/candidate" \
  FASIM_GASAL2_PHASE7_V5_FUSED_SCOREINFO_CONSUMER=1
```

The Python validator must require:

```python
if value(base, "requested") != "0" or value(base, "active") != "0":
    raise SystemExit("v5 fused consumer must be default-off")
if value(candidate, "requested") != "1":
    raise SystemExit("v5 fused consumer was not requested")
if value(candidate, "active") != "1":
    raise SystemExit("v5 fused consumer did not activate")
if int(value(candidate, "gpu_descriptor_attempts")) <= 0:
    raise SystemExit("v5 fused consumer must emit descriptor attempts")
if value(candidate, "descriptor_false_negatives") != "0":
    raise SystemExit("v5 descriptor contract has false negatives")
if value(candidate, "missing_required_attempts") != "0":
    raise SystemExit("v5 descriptor contract is missing required attempts")
if value(candidate, "scoreinfo_prealign_reduced") != "1":
    raise SystemExit("v5 must reduce or replace scoreInfo/preAlign work")
if value(candidate, "cpu_align_authority") != "1":
    raise SystemExit("v5 must preserve CPU Align authority")
if value(candidate, "gpu_endpoint_cigar_traceback_output_authority") != "0":
    raise SystemExit("v5 must not grant GPU output authority")
if value(candidate, "gate_v5_1_pass") != "1":
    raise SystemExit("v5 Gate v5.1 did not pass")
```

- [ ] **Step 2: Run runtime smoke to verify RED**

Run:

```bash
bash scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime_smoke.sh
```

Expected: FAIL because the env is not implemented or v5 metrics remain zero.

- [ ] **Step 3: Record descriptor contract at existing attempt boundary**

In `extend_tasks_with_gasal2_batch`, after `gasalAttempts` and `scoreGroups`
are built, add a v5 branch that records descriptor contract telemetry.

Minimal first gate behavior:

```cpp
const bool phase7V5FusedConsumerRequested =
	fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime();

if (phase7V5FusedConsumerRequested)
{
	const uint64_t referenceScoreInfos =
		static_cast<uint64_t>(scoreGroups.size());
	const uint64_t referenceAttempts =
		static_cast<uint64_t>(gasalAttempts.size());
	const uint64_t descriptorScoreInfos =
		static_cast<uint64_t>(scoreGroups.size());
	const uint64_t descriptorAttempts =
		static_cast<uint64_t>(gasalAttempts.size());
	const bool scoreInfoPrealignReduced = false;
	const bool cpuAlignAuthority = true;
	const bool gateV51Pass =
		descriptorAttempts > 0 &&
		scoreInfoPrealignReduced &&
		cpuAlignAuthority;
	fasim_gasal2_record_phase7_v5_fused_scoreinfo_consumer(
		static_cast<uint64_t>(tasks.size()),
		referenceScoreInfos,
		referenceAttempts,
		descriptorScoreInfos,
		descriptorAttempts,
		0,
		0,
		0,
		scoreInfoPrealignReduced,
		cpuAlignAuthority,
		gateV51Pass);
}
```

This intentionally fails Gate v5.1 until the descriptor source actually
reduces or replaces scoreInfo/preAlign work. Do not set
`scoreInfoPrealignReduced = true` unless the descriptor source is before CPU
scoreInfo construction.

- [ ] **Step 4: Add Makefile target**

```make
check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-runtime-smoke
```

- [ ] **Step 5: Verify expected no-go if still post-scoreInfo**

Run:

```bash
make check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-runtime-smoke
```

Expected for a post-scoreInfo descriptor scaffold: FAIL with
`v5 must reduce or replace scoreInfo/preAlign work`. If this is the only
failure, record a no-go scaffold checkpoint instead of forcing Gate v5.1 pass.

## Task 3: CPU-Authority Replay First1 Gate

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime_smoke.sh`

- [ ] **Step 1: Feed descriptor-selected attempts into CPU replay**

When Gate v5.1 has a true pre-scoreInfo descriptor source, convert descriptor
attempts into `FasimGasal2SelectedAlignment` rows and reuse the existing
CPU-authority replay loop:

```cpp
FasimGasal2SelectedAlignment selectedAttempt;
selectedAttempt.scoreinfo_index = attempt.scoreinfo_index;
selectedAttempt.cutlength = attempt.cutlength;
selectedAttempt.start = attempt.start;
selectedAttempt.selected = true;
gasalSelected.push_back(selectedAttempt);
```

- [ ] **Step 2: Extend smoke validator**

Require candidate digest equality and nonzero CPU Align authority:

```python
if baseline_digest != candidate_digest:
    raise SystemExit("v5 CPU-authority replay changed lite output digest")
if int(value(candidate, "candidate_align_attempts")) <= 0:
    raise SystemExit("v5 replay must execute CPU Align attempts")
```

- [ ] **Step 3: Keep authority boundary explicit**

The runtime must continue to report:

```text
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_cpu_align_authority=1
benchmark.fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_gpu_endpoint_cigar_traceback_output_authority=0
```

## Task 4: Roadmap Checkpoint And Current-State Wiring

**Files:**
- Create: `docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke.md`
- Create: `scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke.sh`
- Modify: `Makefile`
- Modify: `scripts/summarize_fasim_gasal2_roadmap_current_state.py`
- Modify: `scripts/check_fasim_gasal2_roadmap_current_state.sh`
- Modify: `docs/fasim_gasal2_goal_completion_roadmap.md`
- Modify: `docs/fasim_gasal2_goal_completion_phase_plan.md`
- Modify: `docs/fasim_gasal2_goal_completion_phase_checklist.md`
- Modify: `docs/fasim_gasal2_goal_completion_execution_ladder.md`

- [ ] **Step 1: Write runtime checkpoint doc**

If Gate v5.1 passes, record:

```text
phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke =
  descriptor_contract_clean_first1
phase7_broad_restart_v5_gate_v5_1_pass = 1
phase7_broad_restart_v5_next_gate =
  fused_scoreinfo_consumer_cpu_authority_replay_first1
```

If the scaffold is post-scoreInfo only, record:

```text
phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke =
  descriptor_contract_no_go_post_scoreinfo_source
phase7_broad_restart_v5_gate_v5_1_pass = 0
phase7_broad_restart_v5_next_gate =
  true_pre_scoreinfo_fused_descriptor_source
```

- [ ] **Step 2: Add roadmap checker**

The checker must require:

```text
runtime_default = off
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
no broad_replacement workload-matrix row before Gate v5.3 passes
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

- [ ] **Step 3: Add current-state wiring**

Add the runtime smoke target to `check-fasim-gasal2-roadmap-current-state`
only after it is stable enough for aggregate runtime. If it is too expensive,
add a roadmap doc checker to current-state and keep the runtime target
separate.

## Task 5: First64 Broad Gate Characterization

**Files:**
- Create: `scripts/characterize_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_first64.sh`
- Create: `scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_first64_result.sh`
- Create: `docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_first64_broad_gate.md`
- Modify: `Makefile`

- [ ] **Step 1: Run first64 only after first1 gate passes**

First64 is allowed only if:

```text
phase7_broad_restart_v5_gate_v5_1_pass = 1
descriptor_false_negatives = 0
missing_required_attempts = 0
cpu_align_authority = 1
gpu_endpoint_cigar_traceback_output_authority = 0
```

- [ ] **Step 2: Gate broad completion strictly**

The first64 checker must require:

```text
full row-set/digest equality = required
candidate_wall_seconds < baseline_wall_seconds = required before broad completion
scoreInfo/preAlign work reduced or replaced = required
Align-side work reduced or replaced = required
fallbacks = 0 for the claimed GPU path = required
```

- [ ] **Step 3: Update workload matrix only after broad pass**

Only after Gate v5.3 passes, add a `contract=broad_replacement` row to
`docs/fasim_gasal2_workload_matrix.tsv`. Until then, leave:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Verification Commands

Run after each task:

```bash
bash -n scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_implementation_plan.sh
bash scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_implementation_plan.sh
make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-implementation-plan
git diff --check -- Makefile docs/superpowers/plans/2026-06-13-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer.md scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_implementation_plan.sh
```

Run after runtime code changes:

```bash
make check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-env
make check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-runtime-smoke
python3 -m py_compile scripts/summarize_fasim_gasal2_roadmap_current_state.py
git diff --check
```

Run before any completion claim:

```bash
make check-fasim-gasal2-roadmap-current-state
make check-fasim-gasal2-roadmap-phase8-completion-decision
```

Expected until Gate v5.3 passes:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```
