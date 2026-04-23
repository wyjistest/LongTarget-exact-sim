# Terminal First-Half AB Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add profiler-only support for `coarse / terminal / lexical_first_half` profile modes, split the dominant `terminal first_half` lexical span into `span_a / span_b`, and produce a controlled A/B artifact that can decide whether lexical timers are acceptable or still too intrusive.

**Architecture:** Extend the existing context-apply profile binary with a runtime `profile_mode` that gates fine-grained timing. Keep the lifecycle summarizer exact-safe and profiler-only by separating `intra_profile_closure_status` from `profile_mode_overhead_status`, then add a dedicated A/B summarizer that compares same-workload `coarse`, `terminal`, and `lexical_first_half` artifacts. The lifecycle decision should stay runtime-closed until both the A/B gate and the first-half lexical split are resolved.

**Tech Stack:** C++, Python, shell regression scripts, existing same-workload wrapper and candidate-index lifecycle summarizer.

### Task 1: Add failing regression for lifecycle and A/B decisions

**Files:**
- Modify: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`
- Create: `scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh`

**Step 1: Write the failing tests**

- Extend lifecycle check coverage for:
  - `run_profile_mode_ab`
  - `split_terminal_first_half_span_a`
  - `split_terminal_first_half_span_b`
  - `reduce_profiler_timer_overhead`
- Add a new A/B check script that expects:
  - matching `workload_id` and case sets across three modes
  - `profile_mode_overhead_status = ok | suspect`
  - decisions `split_terminal_first_half_span_a | split_terminal_first_half_span_b | reduce_profiler_timer_overhead`

**Step 2: Run tests to verify they fail**

Run:

```bash
bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh
bash scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh
```

Expected:
- lifecycle check fails because the new `profile_mode`/first-half fields are missing
- A/B check fails because the summarizer script does not exist yet

### Task 2: Add `profile_mode` and first-half split telemetry

**Files:**
- Modify: `sim.h`
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`

**Step 1: Implement runtime `profile_mode` parsing**

- Support `--profile-mode coarse|terminal|lexical_first_half`
- Emit `profile_mode` and timer-call counters in per-case and aggregate TSV

**Step 2: Implement minimal first-half split**

- Add:
  - `terminal_first_half_parent_seconds`
  - `terminal_first_half_span_a_seconds`
  - `terminal_first_half_span_b_seconds`
  - `terminal_first_half_child_known_seconds`
  - `terminal_first_half_unexplained_seconds`
  - `terminal_first_half_unexplained_share`
  - `terminal_first_half_dominant_span`
- Keep the split lexical and source-order based, not semantic-relabel based

**Step 3: Run focused build/test**

Run:

```bash
make tests/sim_initial_host_merge_context_apply_profile
```

Expected:
- build succeeds

### Task 3: Add profile-mode A/B summarizer

**Files:**
- Create: `scripts/summarize_sim_initial_host_merge_profile_mode_ab.py`
- Create: `scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh`
- Modify: `scripts/run_sim_initial_host_merge_same_workload_materiality_profile.sh` if mode fan-out needs wrapper help

**Step 1: Implement the A/B summary**

- Inputs:
  - `--coarse-dir`
  - `--terminal-dir`
  - `--lexical-first-half-dir`
- Outputs:
  - `profile_mode_ab_cases.tsv`
  - `profile_mode_ab_summary.json`
  - `profile_mode_ab_decision.json`
  - `profile_mode_ab_summary.md`

**Step 2: Compute decision fields**

- `candidate_index_seconds_ratio_terminal_vs_coarse`
- `candidate_index_seconds_ratio_lexical_vs_coarse`
- `terminal_parent_seconds_ratio_terminal_vs_coarse`
- `terminal_parent_seconds_ratio_lexical_vs_coarse`
- `sim_seconds_ratio_lexical_vs_coarse`
- `total_seconds_ratio_lexical_vs_coarse`
- `timer_call_count_ratio_lexical_vs_coarse`
- `profile_mode_overhead_status`

**Step 3: Run new regression**

Run:

```bash
bash scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh
```

Expected:
- PASS

### Task 4: Reconnect lifecycle decision to the new A/B gate

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_candidate_index_lifecycle.py`
- Modify: `scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh`

**Step 1: Update lifecycle decision ordering**

- If `profile_mode_overhead_status in {"unknown", "needs_coarse_vs_lexical_ab"}`:
  - `recommended_next_action = run_profile_mode_ab`
- If `profile_mode_overhead_status == "suspect"`:
  - `recommended_next_action = reduce_profiler_timer_overhead`
- Only after `profile_mode_overhead_status == "ok"` should lifecycle choose:
  - `split_terminal_first_half_span_a`
  - `split_terminal_first_half_span_b`
  - or `no_runtime_prototype_selected`

**Step 2: Run regression**

Run:

```bash
bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh
```

Expected:
- PASS

### Task 5: Run controlled same-workload artifacts

**Files:**
- Reuse existing same-workload output directory convention under `.tmp/`

**Step 1: Generate three mode artifacts on the same 5 cases**

Run the profile binary or wrapper for:
- `coarse`
- `terminal`
- `lexical_first_half`

**Step 2: Run A/B summary and refresh lifecycle summary**

Expected:
- `profile_mode_overhead_status = ok | suspect`
- lifecycle next action becomes one of:
  - `reduce_profiler_timer_overhead`
  - `split_terminal_first_half_span_a`
  - `split_terminal_first_half_span_b`
  - `no_runtime_prototype_selected`

### Task 6: Final verification

**Files:**
- Review changed files only

**Step 1: Run verification commands**

```bash
make tests/sim_initial_host_merge_context_apply_profile
bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh
bash scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh
bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh
```

Expected:
- all commands pass

**Step 2: Confirm non-goals remain closed**

- No runtime prototype
- No min-tree
- No eager erase handle
- No lazy index
- No coalescing/reorder
