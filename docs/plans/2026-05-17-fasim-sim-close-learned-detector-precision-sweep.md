# Fasim SIM-Close Learned Detector Precision Sweep Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Evaluate whether the #92 large-corpus learned detector can beat the current hand-written guard under high-precision constraints, without adding runtime behavior.

**Architecture:** Reuse the #92 large-corpus dataset generation and model-score helpers. Train the existing dependency-free ranked shadow on the workload-heldout train split, sweep thresholds over held-out validation scores, report precision/recall targets, and evaluate offline hybrid policies against the current guard.

**Tech Stack:** Bash check target, Python 3 standard library, existing TSV datasets, existing learned-detector helper modules, Markdown report.

### Task 1: Add RED Check Target

**Files:**
- Modify: `Makefile`
- Create: `scripts/check_fasim_sim_recovery_learned_detector_precision_sweep.sh`

**Step 1: Add Makefile target**

Add:

```text
check-fasim-sim-recovery-learned-detector-precision-sweep
```

It should build `fasim_longtarget_x86` and run the new check script.

**Step 2: Write the failing check**

The check should regenerate the #92 large-corpus model shadow artifacts, then call:

```text
scripts/benchmark_fasim_sim_recovery_learned_detector_precision_sweep.py
```

It must assert metrics for rows, labels, held-out counts, current guard, learned shadow, precision target summaries, hybrid policies, error attribution, and strict no-runtime boundaries.

**Step 3: Run RED**

Run:

```bash
make check-fasim-sim-recovery-learned-detector-precision-sweep
```

Expected: fail because `scripts/benchmark_fasim_sim_recovery_learned_detector_precision_sweep.py` does not exist yet.

### Task 2: Implement Precision Sweep Evaluator

**Files:**
- Create: `scripts/benchmark_fasim_sim_recovery_learned_detector_precision_sweep.py`

**Step 1: Reuse #92 helpers**

Import:

```text
benchmark_fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow
```

Use its workload split, source split, current guard metrics, score training, and error attribution helpers.

**Step 2: Sweep thresholds**

Train on workload-heldout train rows and score validation rows. Enumerate thresholds from validation scores plus empty/all sentinels. For each threshold, compute candidate-eligible precision, recall, false positives, and false negatives.

**Step 3: Report precision targets**

For precision targets `90`, `95`, and `99`, report the max recall threshold that satisfies the target. This is an offline validation characterization, not a deployable runtime threshold.

**Step 4: Evaluate hybrid policies**

For the primary precision target, report:

```text
current_guard only
learned only
current_guard OR learned_high_precision
current_guard AND learned_high_precision
```

The hybrid analysis stays offline and must not change runtime guard behavior.

### Task 3: Verify

Run:

```bash
make check-fasim-sim-recovery-learned-detector-precision-sweep
make check-fasim-sim-recovery-learned-detector-large-corpus-model-shadow
make check-fasim-exactness
python3 -B -m py_compile scripts/benchmark_fasim_sim_recovery_learned_detector_precision_sweep.py
git diff --check
```

Also run changed-file bidi scan, CUDA/source route scan, forbidden behavior scan, and heavy ML dependency scan.

### Task 4: Commit And Push

Commit:

```text
fasim: characterize learned detector precision sweep
```

Push branch:

```text
fasim-sim-recovery-learned-detector-precision-sweep
```

Open a stacked PR against:

```text
fasim-sim-recovery-learned-detector-large-corpus-model-shadow
```
