# Fasim SIM-Close Learned Detector Expanded Hard-Negative Model Shadow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Evaluate the offline learned/ranked detector shadow on the expanded hard-negative corpus from #89 without adding a runtime model or changing Fasim/SIM-close behavior.

**Architecture:** Reuse #89's bounded real-corpus hard-negative check to regenerate the expanded source and negative datasets, then run a new dependency-free shadow evaluator. The evaluator extends existing workload/family held-out reporting with negative-source-heldout and leave-one-workload-out error summaries while keeping SIM labels offline-only.

**Tech Stack:** Bash check scripts, Python 3 standard library, existing learned-detector TSV format, existing dependency-free ranked shadow helpers, Markdown reports.

### Task 1: Add RED Check Target

**Files:**
- Modify: `Makefile`
- Create: `scripts/check_fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow.sh`

**Step 1: Write the failing check**

Add a Makefile target:

```text
check-fasim-sim-recovery-learned-detector-expanded-hard-negative-model-shadow
```

The check should regenerate the #89 dataset, then call the new report script and assert these telemetry keys:

```text
enabled=1
rows>0
positive_rows>0
negative_rows>0
workload_count>0
hard_negative_source_count>0
workload_heldout_degenerate=[01]
family_heldout_degenerate=[01]
current_guard_recall
current_guard_precision
learned_shadow_recall
learned_shadow_precision
candidate_eligible_recall
candidate_eligible_precision
false_positives
false_negatives
false_positives_by_negative_source
false_negatives_by_workload
selected_threshold
production_model=0
sim_labels_runtime_inputs=0
runtime_behavior_changed=0
deep_learning_dependency=0
```

**Step 2: Run RED**

Run:

```bash
make check-fasim-sim-recovery-learned-detector-expanded-hard-negative-model-shadow
```

Expected: fail because the new Python report script does not exist yet.

### Task 2: Implement Offline Shadow Evaluator

**Files:**
- Create: `scripts/benchmark_fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow.py`

**Step 1: Reuse existing ranked-shadow helpers**

Import the existing model-shadow helpers for feature stats, scores, threshold selection, and basic evaluation. Do not add any heavy ML dependency.

**Step 2: Evaluate split policies**

Add policy summaries for:

```text
current_split
workload_heldout
family_heldout
negative_source_heldout
```

Select workload-heldout as primary when non-degenerate; otherwise record the degenerate state.

**Step 3: Add leave-one-workload-out summary**

For each workload, train on all other workloads if train/validation labels are non-degenerate. Report per-workload precision/recall/error counts and aggregate skipped count.

**Step 4: Add error attribution**

For the primary held-out policy, report:

```text
false_positives_by_negative_source
false_negatives_by_workload
no_legacy_proxy_false_positives
```

### Task 3: Render Report

**Files:**
- Create: `docs/fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow.md`

The report must include:

```text
Expanded hard-negative model shadow metrics
Split evaluation table
Negative-source held-out table
Leave-one-workload-out table
Baseline comparison against #84/#87/#88
Decision block
Scope block forbidding runtime/model promotion
```

### Task 4: Verify Scope And Regressions

Run:

```bash
make check-fasim-sim-recovery-learned-detector-real-corpus-hard-negatives
make check-fasim-sim-recovery-learned-detector-expanded-hard-negative-model-shadow
make check-fasim-sim-recovery-learned-detector-model-shadow
make check-fasim-exactness
python3 -B -m py_compile scripts/benchmark_fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.py
python3 -B -m py_compile scripts/benchmark_fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow.py
git diff --check
```

Also run changed-file bidi scan, CUDA/source route scan, added-line runtime/model scan, and forbidden behavior scan.

### Task 5: Commit And Push

Commit message:

```text
fasim: evaluate expanded hard-negative learned detector shadow
```

Push branch:

```text
fasim-sim-recovery-learned-detector-expanded-hard-negative-model-shadow
```

Open a stacked PR against:

```text
fasim-sim-recovery-learned-detector-real-corpus-hard-negatives
```
