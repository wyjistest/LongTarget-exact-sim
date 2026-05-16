# Fasim SIM-Close Learned Detector Real-Corpus Hard Negatives Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand the offline SIM-close learned-detector real-corpus and hard-negative data line without adding any runtime model or changing Fasim/SIM-close behavior.

**Architecture:** Add a bounded local real-corpus discovery helper for optional marmoset paired FASTA cases, then feed the selected cases through the existing characterization, negative dataset, and dataset-expansion audit scripts. The PR reports corpus and hard-negative coverage only; it does not rerun or promote a learned model.

**Tech Stack:** Bash check scripts, Python 3 standard library, existing Fasim characterization scripts, Makefile targets, Markdown reports.

### Task 1: Add a Failing Check Target

**Files:**
- Modify: `Makefile`
- Create: `scripts/check_fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.sh`

**Step 1: Write the failing check**

Add a Makefile target named `check-fasim-sim-recovery-learned-detector-real-corpus-hard-negatives` that calls the new check script.

The check script should initially assert that a real-corpus hard-negative report command exists and emits:

```text
benchmark.fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.total.enabled=1
benchmark.fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.total.production_model=0
benchmark.fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.total.sim_labels_runtime_inputs=0
benchmark.fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.total.runtime_behavior_changed=0
```

**Step 2: Run RED**

Run:

```bash
make check-fasim-sim-recovery-learned-detector-real-corpus-hard-negatives
```

Expected: FAIL because the discovery/report helper has not been implemented.

### Task 2: Add Bounded Marmoset Case Discovery

**Files:**
- Create: `scripts/benchmark_fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.py`

**Step 1: Implement discovery**

Discover paired directories under `FASIM_SIM_RECOVERY_LEARNED_DETECTOR_MARMOSET_ROOT`:

```text
<gene>_marmoset/
<gene>_marmoset-targetDNA/
```

For each pair, select one RNA FASTA and one target DNA FASTA, excluding the three existing fixed marmoset cases by default. Limit extra selected cases with `--extra-marmoset-limit`, require a small RNA-size floor to avoid tiny no-row controls, and keep the default bounded.

**Step 2: Output shell-safe arguments**

Emit a NUL-delimited or TSV manifest that the check script can read into `--case` and `--validate-case` arguments. Include discovery metrics:

```text
discovered_marmoset_pair_count
selected_extra_case_count
selected_extra_cases
```

### Task 3: Generate Offline Dataset And Hard-Negative Audit

**Files:**
- Modify: `scripts/check_fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.sh`
- Modify or reuse: `scripts/benchmark_fasim_sim_recovery_learned_detector_dataset_expansion.py`

**Step 1: Build source dataset**

Run `benchmark_fasim_sim_recovery_real_corpus_characterization.py` with:

```text
tiny_validate
existing fixed marmoset validate-supported cases when available
existing no-legacy marmoset case when available
bounded extra discovered marmoset cases when available
```

**Step 2: Build negative dataset**

Run `benchmark_fasim_sim_recovery_learned_detector_negative_dataset.py`.

**Step 3: Render report**

Produce:

```text
docs/fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.md
```

The report must include hard-negative source counts, validate-supported/no-legacy workload counts, selected extra cases, and offline-only scope.

### Task 4: Verify No Runtime Scope Creep

**Files:**
- Check changed files only

Run:

```bash
make check-fasim-sim-recovery-learned-detector-real-corpus-hard-negatives
make check-fasim-sim-recovery-learned-detector-dataset-expansion
make check-fasim-sim-recovery-learned-detector-feature-expansion
make check-fasim-exactness
python3 -B -m py_compile scripts/benchmark_fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.py
python3 -B -m py_compile scripts/benchmark_fasim_sim_recovery_learned_detector_dataset_expansion.py
git diff --check
```

Also run changed-file bidi and forbidden route scans. The expected outcome is an offline data/report PR only.

### Task 5: Commit And Push

**Files:**
- All changed files

Commit message:

```text
fasim: expand learned detector real-corpus hard negatives
```

Push branch:

```text
fasim-sim-recovery-learned-detector-real-corpus-hard-negatives
```

Create a stacked PR against:

```text
fasim-sim-recovery-learned-detector-feature-expansion
```
