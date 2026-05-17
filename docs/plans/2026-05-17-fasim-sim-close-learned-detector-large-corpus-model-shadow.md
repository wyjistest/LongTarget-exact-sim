# Fasim SIM-Close Learned Detector Large Corpus Model Shadow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Evaluate the offline learned/ranked detector shadow on the #91 large corpus without adding a runtime model or changing Fasim/SIM-close behavior.

**Architecture:** Reuse the #91 large-corpus data-generation flow to regenerate source and hard-negative TSVs with the bounded 36-case marmoset expansion. Reuse the existing dependency-free #90 shadow evaluation helpers for split policies, scoring, threshold selection, and error attribution, but render a separate large-corpus report and compare against the #90 shadow result.

**Tech Stack:** Bash check target, Python 3 standard library, existing learned-detector TSV format, existing dependency-free shadow helper module, Markdown report.

### Task 1: Add RED Check Target

**Files:**
- Modify: `Makefile`
- Create: `scripts/check_fasim_sim_recovery_learned_detector_large_corpus_model_shadow.sh`

**Step 1: Add Makefile target**

Add:

```text
check-fasim-sim-recovery-learned-detector-large-corpus-model-shadow
```

It should build `fasim_longtarget_x86` and run the new check script.

**Step 2: Write the failing check**

The check should regenerate the #91 large corpus with:

```text
FASIM_SIM_RECOVERY_LEARNED_DETECTOR_LARGE_CORPUS_EXTRA_MARMOSET_LIMIT=36
```

Then it should call the new report script and assert:

```text
enabled=1
rows
positive_rows
negative_rows
workload_count
validate_supported_workload_count
hard_negative_source_count
train_positive
train_negative
validation_positive
validation_negative
workload_heldout_degenerate
family_heldout_degenerate
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
decision
production_model=0
sim_labels_runtime_inputs=0
runtime_behavior_changed=0
model_training_added=0
deep_learning_dependency=0
recommended_default_sim_close=0
```

**Step 3: Run RED**

Run:

```bash
make check-fasim-sim-recovery-learned-detector-large-corpus-model-shadow
```

Expected: fail because `scripts/benchmark_fasim_sim_recovery_learned_detector_large_corpus_model_shadow.py` does not exist yet.

### Task 2: Implement Large-Corpus Shadow Evaluator

**Files:**
- Create: `scripts/benchmark_fasim_sim_recovery_learned_detector_large_corpus_model_shadow.py`

**Step 1: Reuse #90 evaluator helpers**

Import:

```text
benchmark_fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow
```

Use its split/evaluation/model helper functions rather than duplicating the scoring logic.

**Step 2: Add #90 comparison**

Parse `docs/fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow.md` and report:

```text
baseline_90_rows
baseline_90_current_guard_recall
baseline_90_current_guard_precision
baseline_90_learned_shadow_recall
baseline_90_learned_shadow_precision
```

**Step 3: Render report**

Create:

```text
docs/fasim_sim_recovery_learned_detector_large_corpus_model_shadow.md
```

Include:

```text
Large Corpus Model Shadow
Split Evaluation
Negative-Source Held-Out
Error Attribution
Leave-One-Workload-Out
Baseline Comparison
Decision
Scope
```

### Task 3: Verify

Run:

```bash
make check-fasim-sim-recovery-learned-detector-large-corpus-expansion
make check-fasim-sim-recovery-learned-detector-large-corpus-model-shadow
make check-fasim-sim-recovery-learned-detector-expanded-hard-negative-model-shadow
make check-fasim-exactness
python3 -B -m py_compile scripts/benchmark_fasim_sim_recovery_learned_detector_large_corpus_expansion.py
python3 -B -m py_compile scripts/benchmark_fasim_sim_recovery_learned_detector_large_corpus_model_shadow.py
git diff --check
```

Also run changed-file bidi scan, source route scan, forbidden behavior scan, and heavy ML dependency scan.

### Task 4: Commit And Push

Commit:

```text
fasim: evaluate large-corpus learned detector shadow
```

Push branch:

```text
fasim-sim-recovery-learned-detector-large-corpus-model-shadow
```

Open a stacked PR against:

```text
fasim-sim-recovery-learned-detector-large-corpus-expansion
```
