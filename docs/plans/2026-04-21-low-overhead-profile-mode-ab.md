# Low-Overhead Profile Mode AB Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current high-overhead full lexical timer flow with low-perturbation profiler-only modes that can safely decide whether `first_half` should be split further, while persisting benchmark provenance in the resulting artifacts.

**Architecture:** Keep the runtime path exact and closed. Extend the profile binary with two lower-overhead modes: `lexical_first_half_count_only` and `lexical_first_half_sampled`. Persist benchmark provenance through the wrapper and aggregate outputs so shared-workload A/B runs can be validated from the artifact alone. Update the A/B summarizer to compare low-overhead modes against `coarse`/`terminal` and only trust span timing when overhead gates pass.

**Tech Stack:** C++, Python, shell regression scripts, existing same-workload materiality wrapper and profile-mode A/B summarizer.

### Task 1: Add failing regression coverage for low-overhead modes

**Files:**
- Modify: `scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh`
- Modify: `scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh`

**Step 1: Write the failing tests**

- Extend wrapper checks to require persisted benchmark provenance fields.
- Extend A/B checks to cover:
  - `lexical_first_half_count_only`
  - `lexical_first_half_sampled`
  - `profile_mode_overhead_status = suspect_count_bookkeeping | suspect_sampled_timer | ok`
  - `trusted_span_timing = false | true`
  - `recommended_next_action = reduce_profiler_timer_overhead | lower_sampling_rate | split_terminal_first_half_span_a | split_terminal_first_half_span_b`

**Step 2: Run the checks to verify they fail**

Run:

```bash
bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh
bash scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh
```

Expected:
- checks fail because provenance fields and low-overhead profile modes do not exist yet

### Task 2: Persist benchmark provenance through wrapper outputs

**Files:**
- Modify: `scripts/run_sim_initial_host_merge_same_workload_materiality_profile.sh`
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`

**Step 1: Add persisted benchmark provenance fields**

- Carry these through wrapper output and aggregate TSV:
  - `benchmark_source_original_path`
  - `benchmark_source_copied_path`
  - `benchmark_source_sha256`
  - `benchmark_source_size_bytes`
  - `benchmark_identity_basis`

**Step 2: Verify aggregate validation enforces the new fields**

Run:

```bash
bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh
```

Expected:
- PASS

### Task 3: Add low-overhead profile modes to the profile binary

**Files:**
- Modify: `sim.h`
- Modify: `tests/sim_initial_host_merge_context_apply_profile.cpp`

**Step 1: Add new modes**

- Support:
  - `lexical_first_half_count_only`
  - `lexical_first_half_sampled`
- Add `--profile-sample-log2 N` CLI support for sampled mode.

**Step 2: Emit low-overhead fields**

- `count_only` should emit count-only span coverage and timer-call counters.
- `sampled` should emit:
  - sample rate metadata
  - sampled counts
  - sampled span seconds
  - sampled unexplained seconds

**Step 3: Keep lexical full-timing behavior unchanged for the existing mode**

Run:

```bash
make tests/sim_initial_host_merge_context_apply_profile
```

Expected:
- build succeeds

### Task 4: Update A/B summarizer to classify low-overhead profiler states

**Files:**
- Modify: `scripts/summarize_sim_initial_host_merge_profile_mode_ab.py`
- Modify: `scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh`

**Step 1: Add low-overhead inputs and outputs**

- Accept directories for:
  - `coarse`
  - `terminal`
  - `lexical_first_half_count_only`
  - `lexical_first_half_sampled`
- Emit:
  - `trusted_span_timing`
  - `trusted_span_source`
  - `profile_mode_overhead_status`
  - `benchmark_scope`
  - `benchmark_identity_basis`

**Step 2: Add decision logic**

- `count_only` suspect → `reduce_profiler_timer_overhead`
- `sampled` suspect → `lower_sampling_rate`
- low-overhead modes ok + dominant span known → `split_terminal_first_half_span_a|b`

**Step 3: Run regression**

Run:

```bash
bash scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh
```

Expected:
- PASS

### Task 5: Final verification

**Step 1: Run verification commands**

```bash
make tests/sim_initial_host_merge_context_apply_profile
bash scripts/check_run_sim_initial_host_merge_same_workload_materiality_profile.sh
bash scripts/check_summarize_sim_initial_host_merge_profile_mode_ab.sh
bash scripts/check_summarize_sim_initial_host_merge_candidate_index_lifecycle.sh
```

Expected:
- all commands pass

**Step 2: Preserve non-goals**

- No runtime prototype
- No exactness relaxation
- No reopen of min maintenance / eager erase / lazy index / coalescing / reorder / GPU rewrite
