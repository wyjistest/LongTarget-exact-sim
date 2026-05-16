# Fasim SIM-Close Learned Detector Corpus Expansion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand the offline SIM-close learned-detector corpus and reporting so future model work is gated on broader validate-supported data and hard negatives.

**Architecture:** Keep this PR offline-only. Reuse the existing learned-detector source TSV, negative dataset builder, and dataset expansion report, then add corpus-expansion metadata and checks around available workloads, held-out split viability, and hard-negative source diversity. Do not add a runtime model or change Fasim/SIM-close output.

**Tech Stack:** Bash check scripts, Python TSV/report generators, Makefile targets, repository FASTA fixtures and optional externally supplied real-corpus FASTA paths.

### Task 1: Establish Baseline

**Files:**
- Read: `scripts/check_fasim_sim_recovery_learned_detector_dataset_expansion.sh`
- Read: `scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py`
- Read: `scripts/benchmark_fasim_sim_recovery_learned_detector_negative_dataset.py`
- Read: `scripts/benchmark_fasim_sim_recovery_learned_detector_dataset_expansion.py`

**Step 1:** Run `./scripts/check_fasim_sim_recovery_learned_detector_dataset_expansion.sh`.

**Expected:** Exit 0 on the stacked base branch. Record current metrics: `unique_workloads=1`, `workload_heldout_degenerate=1`, and current hard-negative source mix.

### Task 2: Find Safe Corpus Inputs

**Files:**
- Read: repository FASTA fixtures via `rg --files -g '*.fa' -g '*.fasta'`
- Read: real-corpus benchmark options in `scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py`
- Modify only if needed: `scripts/check_fasim_sim_recovery_learned_detector_dataset_expansion.sh`

**Step 1:** Identify tracked FASTA inputs and optional env-driven human corpus inputs.

**Step 2:** Prefer validate-supported real-corpus cases when env paths exist. If only tracked fixtures exist, make the check/report explicit that the local smoke corpus remains single-workload and research-only.

### Task 3: Add a Failing Corpus-Gate Check

**Files:**
- Modify: `scripts/check_fasim_sim_recovery_learned_detector_dataset_expansion.sh`

**Step 1:** Add checks for new telemetry/report fields:
- `heldout_workload_available`
- `heldout_family_available`
- `hard_negative_source_count`
- a decision string that blocks runtime/model promotion when workload-heldout remains degenerate.

**Step 2:** Run the check and verify it fails because the generator does not emit those fields yet.

### Task 4: Implement Corpus Expansion Telemetry

**Files:**
- Modify: `scripts/benchmark_fasim_sim_recovery_learned_detector_dataset_expansion.py`

**Step 1:** Add metrics derived from existing rows:
- `workload_count`
- `family_count`
- `hard_negative_source_count`
- `heldout_workload_available`
- `heldout_family_available`
- `modeling_gate`

**Step 2:** Add report sections explaining the data gate and next decision:
- promote only when multiple workloads and non-degenerate held-out splits exist
- otherwise keep learned-detector work research-only.

**Step 3:** Run the check and verify it passes.

### Task 5: Optional Real-Corpus Expansion Hook

**Files:**
- Modify if needed: `scripts/check_fasim_sim_recovery_learned_detector_dataset_expansion.sh`
- Modify if needed: `Makefile`
- Document: `docs/fasim_sim_recovery_learned_detector_corpus_expansion.md` or the existing dataset expansion report.

**Step 1:** If real-corpus env vars are available, add an opt-in check path that appends those cases to the learned-detector source TSV.

**Step 2:** If env vars are not available locally, document the exact env-gated benchmark command instead of fabricating data.

### Task 6: Verify and Commit

**Files:**
- All modified files.

**Step 1:** Run `./scripts/check_fasim_sim_recovery_learned_detector_dataset_expansion.sh`.

**Step 2:** Run `git diff --stat` and inspect the patch.

**Step 3:** Commit with a message focused on offline corpus-gate reporting.

**Step 4:** Push the stacked branch.
