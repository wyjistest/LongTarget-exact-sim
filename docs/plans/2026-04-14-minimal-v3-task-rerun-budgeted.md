# Minimal V3 Task Rerun Budgeted Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add narrow runtime prototypes for `minimal_v3 + budgeted task-level exact rerun`, with explicit `budget=8` and `budget=16` lanes driven by offline-selected task keys.

**Architecture:** Keep `deferred_exact_minimal_v3_scoreband_75_79` frozen as the shortlist baseline. Add an oracle-guided task-rerun layer that reads a per-tile selected-task file, upgrades only those tasks from `after_gate` windows to `before_gate` windows, and emits dedicated telemetry so runtime-vs-offline comparisons stay causal.

**Tech Stack:** C++11 runtime in `exact_sim.h` / `longtarget.cpp`, existing shell/Python threshold benchmarking tooling, new shell runtime integration check, panel rerun helper, markdown docs.

### Task 1: Lock the benchmark surface with failing checks

**Files:**
- Modify: `scripts/check_two_stage_threshold_modes.sh`
- Create: `scripts/check_two_stage_task_rerun_runtime.sh`
- Modify: `Makefile`

**Step 1: Write the failing expectations**

- Extend the threshold-mode integration check to request:
  - `deferred_exact_minimal_v3_task_rerun_budget8`
  - `deferred_exact_minimal_v3_task_rerun_budget16`
- Add a dedicated runtime check that expects:
  - selected-task file ingestion
  - task-rerun telemetry emission
  - task matching to depend on `fragment + strand + rule`, not fragment only

**Step 2: Run checks to verify they fail**

Run:
- `make check-two-stage-threshold-modes`
- `make check-two-stage-task-rerun-runtime`

Expected:
- threshold-mode check fails because the new run labels and telemetry fields do not exist yet
- runtime check fails because the runtime does not yet read selected-task files or expose task-rerun telemetry

### Task 2: Add the minimal runtime data path

**Files:**
- Modify: `exact_sim.h`
- Modify: `tests/test_exact_sim_two_stage_threshold.cpp`

**Step 1: Write the failing unit coverage**

Add focused tests for:
- runtime config parsing of:
  - `LONGTARGET_TWO_STAGE_TASK_RERUN`
  - `LONGTARGET_TWO_STAGE_TASK_RERUN_BUDGET`
  - `LONGTARGET_TWO_STAGE_TASK_RERUN_SELECTED_TASKS_PATH`
- result upgrade logic that swaps a selected task from `after_gate` windows to `before_gate` windows and records the added windows / bp correctly

**Step 2: Run the unit test to verify it fails**

Run: `make check-exact-sim-two-stage-threshold`

Expected: compile or assertion failure because the new config/result helpers do not exist yet

**Step 3: Write the minimal implementation**

- Add a task-rerun config struct and env parsing helper
- Preserve both `windowsBeforeGateList` and `windows` in deferred prefilter results
- Add a helper that upgrades one selected task from baseline windows to `before_gate` windows while reporting added windows / bp

**Step 4: Run the unit test to verify it passes**

Run: `make check-exact-sim-two-stage-threshold`

Expected: PASS

### Task 3: Wire oracle-guided task rerun into runtime and benchmark tooling

**Files:**
- Modify: `longtarget.cpp`
- Modify: `scripts/benchmark_two_stage_threshold_modes.py`
- Modify: `scripts/check_two_stage_threshold_modes.sh`

**Step 1: Write minimal implementation**

- In `longtarget.cpp`, load a per-run selected-task TSV and match tasks by:
  - `fragment_index`
  - `fragment_start_in_seq`
  - `fragment_end_in_seq`
  - `reverse_mode`
  - `parallel_mode`
  - `strand`
  - `rule`
- For selected tasks only, replace the runtime execution windows with the stored `before_gate` windows
- Emit task-rerun telemetry:
  - enabled / budget / selected path
  - selected task count
  - effective task count
  - added window count
  - added bp total
  - rerun seconds

- In the benchmark script:
  - add the two new run labels
  - parse and expose the new telemetry fields

**Step 2: Run integration checks**

Run:
- `make check-two-stage-threshold-modes`
- `make check-two-stage-task-rerun-runtime`

Expected: PASS

### Task 4: Add the fixed-panel rerun helper and sync docs

**Files:**
- Create: `scripts/rerun_two_stage_panel_task_rerun_runtime.py`
- Modify: `README.md`
- Modify: `EXACT_SIM_PROGRESS.md`

**Step 1: Write minimal implementation**

- Materialize per-tile selected-task TSV files from the offline replay summary
- Rerun the fixed selected tiles with:
  - `deferred_exact_minimal_v3_task_rerun_budget8`
  - `deferred_exact_minimal_v3_task_rerun_budget16`
- Keep the helper output shaped like the existing panel rerun summaries

**Step 2: Update docs minimally**

- Document the runtime prototype, env knobs, telemetry, and the new panel rerun helper
- Record the new baseline assumption: `minimal_v3` remains the shortlist baseline and task rerun is an attached exact-rescue layer

### Task 5: Verify, commit, push, and run the real panel

**Files:**
- Modify: `README.md`
- Modify: `EXACT_SIM_PROGRESS.md`
- Create/Modify: real panel artifacts under `.tmp/`

**Step 1: Run verification**

Run:
- `make check-exact-sim-two-stage-threshold`
- `make check-two-stage-threshold-modes`
- `make check-two-stage-task-rerun-runtime`
- `python3 ./scripts/analyze_two_stage_task_ambiguity.py --help`
- `python3 ./scripts/replay_two_stage_task_level_rerun.py --help`
- `git diff --check`

**Step 2: Commit**

```bash
git add exact_sim.h longtarget.cpp tests/test_exact_sim_two_stage_threshold.cpp \
  scripts/benchmark_two_stage_threshold_modes.py scripts/check_two_stage_threshold_modes.sh \
  scripts/check_two_stage_task_rerun_runtime.sh scripts/rerun_two_stage_panel_task_rerun_runtime.py \
  README.md EXACT_SIM_PROGRESS.md Makefile \
  docs/plans/2026-04-14-minimal-v3-task-rerun-budgeted.md
git commit -m "Add budgeted task rerun runtime lanes"
```

**Step 3: Push and run the real panel**

Run:
- `git push origin main`
- runtime fixed-panel reruns for budget `8` and `16`
- compare runtime results against the offline replay deltas
