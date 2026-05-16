# Fasim SIM-Close Learned Detector Feature Expansion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add richer Fasim-visible feature columns to the offline learned-detector trainable dataset and rerun held-out model shadow without changing runtime behavior.

**Architecture:** Keep #87's expanded model shadow as the baseline. Extend the offline negative/contrastive TSV with additional features derived from existing Fasim-visible source rows, then add a separate feature-expansion shadow report that uses the expanded feature set. Do not add a runtime model, alter Fasim output, or change SIM-close production behavior.

**Tech Stack:** Bash check scripts, Python TSV/report generators, dependency-free standardized mean-difference model-shadow helpers, generated `.tmp` artifacts, Markdown docs.

### Task 1: Add a Failing Feature Expansion Check

**Files:**
- Create: `scripts/check_fasim_sim_recovery_learned_detector_feature_expansion.sh`
- Modify: `Makefile`

**Step 1:** Create a check script that builds the same expanded learned-detector source dataset as #87 and converts it to a negative/contrastive TSV.

**Step 2:** Make the check require new TSV feature columns:
- `family_size`
- `family_span`
- `interval_overlap_ratio`
- `dominance_margin`
- `score_margin`
- `Nt_margin`
- `near_threshold_density`
- `peak_count`
- `second_peak_gap`
- `plateau_width`

**Step 3:** Make the check call a not-yet-existing feature expansion report script and assert telemetry:
- expanded feature count and feature list
- train/validation counts
- workload/family held-out degeneracy
- current guard precision/recall
- learned shadow precision/recall
- candidate-eligible precision/recall
- decision
- offline-only flags

**Step 4:** Add `check-fasim-sim-recovery-learned-detector-feature-expansion` to `Makefile`.

**Step 5:** Run the new make target.

**Expected:** FAIL because the negative TSV lacks the new columns and the feature-expansion report script does not exist yet.

### Task 2: Add Offline Feature Columns

**Files:**
- Modify: `scripts/benchmark_fasim_sim_recovery_learned_detector_negative_dataset.py`

**Step 1:** Add the new columns to `OUTPUT_FIELDS`.

**Step 2:** Derive each feature from existing source rows only:
- family-level counts/spans from workload/run/family groups
- overlap ratios against same-family Fasim records
- score/Nt/dominance margins against same-family Fasim or output rows
- near-threshold density, peak count, second peak gap, and plateau width from same-family score landscape

**Step 3:** Keep existing labels and split behavior unchanged.

**Step 4:** Run the new check.

**Expected:** The column-existence part passes; the feature-expansion report still fails until Task 3.

### Task 3: Add Feature Expansion Shadow Report

**Files:**
- Create: `scripts/benchmark_fasim_sim_recovery_learned_detector_feature_expansion.py`
- Reuse helpers from: `scripts/benchmark_fasim_sim_recovery_learned_detector_model_shadow.py`
- Reuse policy evaluation ideas from: `scripts/benchmark_fasim_sim_recovery_learned_detector_expanded_model_shadow.py`

**Step 1:** Read the expanded negative TSV and source learned-detector TSV.

**Step 2:** Evaluate current split, workload-held-out, and family-held-out using the expanded feature list.

**Step 3:** Prefer workload-held-out when non-degenerate, then family-held-out, then current split.

**Step 4:** Compare against the current hand-written guard and #87 baseline metrics.

**Step 5:** Emit `docs/fasim_sim_recovery_learned_detector_feature_expansion.md` with feature list, split metrics, comparison, decision, and offline-only scope.

### Task 4: Verification and Commit

**Files:**
- All modified files.

**Step 1:** Run:
```bash
make check-fasim-sim-recovery-learned-detector-feature-expansion
make check-fasim-sim-recovery-learned-detector-expanded-model-shadow
make check-fasim-sim-recovery-learned-detector-dataset-expansion
make check-fasim-exactness
python3 -B -m py_compile scripts/benchmark_fasim_sim_recovery_learned_detector_negative_dataset.py scripts/benchmark_fasim_sim_recovery_learned_detector_feature_expansion.py
git diff --check
```

**Step 2:** Run changed-file bidi scan plus CUDA/source and forbidden behavior route scans.

**Expected:** Checks pass. Route scans show only offline dataset/report/check mentions for model, threshold, scoring, and no runtime/default claims.

**Step 3:** Commit:
```bash
git add Makefile \
  docs/fasim_sim_recovery_learned_detector_feature_expansion.md \
  docs/plans/2026-05-16-fasim-sim-close-learned-detector-feature-expansion.md \
  scripts/check_fasim_sim_recovery_learned_detector_feature_expansion.sh \
  scripts/benchmark_fasim_sim_recovery_learned_detector_feature_expansion.py \
  scripts/benchmark_fasim_sim_recovery_learned_detector_negative_dataset.py
git commit -m "fasim: expand learned detector shadow features"
```

**Step 4:** Push and create a stacked PR against `fasim-sim-recovery-learned-detector-expanded-model-shadow`.
