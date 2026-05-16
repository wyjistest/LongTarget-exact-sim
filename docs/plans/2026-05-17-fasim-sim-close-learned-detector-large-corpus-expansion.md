# Fasim SIM-Close Learned Detector Large Corpus Expansion Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate and audit a larger offline SIM-close learned-detector real-corpus dataset without adding any runtime model or changing Fasim/SIM-close behavior.

**Architecture:** Reuse the existing #89/#90 real-corpus discovery and hard-negative extraction pipeline, but run it with a larger bounded optional marmoset case limit. Add a data-only summary script that parses the generated source/negative TSVs and the existing data-generation log, then writes a separate report for the larger corpus.

**Tech Stack:** Bash check target, Python 3 standard library, existing Fasim real-corpus characterization scripts, existing learned-detector TSV format, Markdown report.

### Task 1: Add RED Check Target

**Files:**
- Modify: `Makefile`
- Create: `scripts/check_fasim_sim_recovery_learned_detector_large_corpus_expansion.sh`

**Step 1: Add Makefile target**

Add:

```text
check-fasim-sim-recovery-learned-detector-large-corpus-expansion
```

It should build `fasim_longtarget_x86` and run the new check script.

**Step 2: Write the failing check**

The check should generate a larger corpus with:

```text
FASIM_SIM_RECOVERY_LEARNED_DETECTOR_EXTRA_MARMOSET_LIMIT=36
FASIM_SIM_RECOVERY_LEARNED_DETECTOR_EXTRA_MARMOSET_MIN_RNA_BYTES=700
```

It should call a new report script that does not exist yet and assert:

```text
enabled=1
extra_marmoset_limit=36
rows
positive_rows
negative_rows
workload_count
validate_supported_workload_count
hard_negative_source_count
growth_vs_expanded_hard_negative_rows
production_model=0
sim_labels_runtime_inputs=0
runtime_behavior_changed=0
model_training_added=0
deep_learning_dependency=0
recommended_default_sim_close=0
```

When the optional marmoset corpus exists locally, assert the generated corpus is larger than #90's 59-row corpus.

**Step 3: Run RED**

Run:

```bash
make check-fasim-sim-recovery-learned-detector-large-corpus-expansion
```

Expected: fail because `scripts/benchmark_fasim_sim_recovery_learned_detector_large_corpus_expansion.py` does not exist yet.

### Task 2: Implement Data-Only Summary Script

**Files:**
- Create: `scripts/benchmark_fasim_sim_recovery_learned_detector_large_corpus_expansion.py`

**Step 1: Read generated datasets**

Read:

```text
--source-dataset
--dataset
--data-expansion-log
--manifest
```

Use only Python standard library.

**Step 2: Emit large-corpus metrics**

Report:

```text
rows
positive_rows
negative_rows
source_rows
workload_count
validate_supported_workload_count
no_legacy_sim_records_workload_count
hard_negative_sources
hard_negative_source_count
selected_extra_case_count
selected_extra_source_rows
selected_extra_positive_rows
selected_extra_negative_rows
growth_vs_expanded_hard_negative_rows
growth_vs_expanded_hard_negative_workloads
```

The baseline for #90 is:

```text
rows=59
workload_count=7
```

**Step 3: Preserve scope markers**

Always emit:

```text
production_model=0
sim_labels_runtime_inputs=0
runtime_behavior_changed=0
model_training_added=0
deep_learning_dependency=0
recommended_default_sim_close=0
```

### Task 3: Render Report

**Files:**
- Create: `docs/fasim_sim_recovery_learned_detector_large_corpus_expansion.md`

The report must include:

```text
Large Corpus Expansion
Corpus Growth
Hard Negative Source Audit
Selected Extra Marmoset Cases
Scope
```

It must state that this is data generation only and that future model shadow work must be a separate PR.

### Task 4: Verify

Run:

```bash
make check-fasim-sim-recovery-learned-detector-large-corpus-expansion
make check-fasim-sim-recovery-learned-detector-expanded-hard-negative-model-shadow
python3 -B -m py_compile scripts/benchmark_fasim_sim_recovery_learned_detector_large_corpus_expansion.py
git diff --check
```

Also run changed-file bidi scan, source route scan, and forbidden behavior scan.

### Task 5: Commit And Push

Commit:

```text
fasim: expand learned detector large corpus data
```

Push branch:

```text
fasim-sim-recovery-learned-detector-large-corpus-expansion
```

Open a stacked PR against:

```text
fasim-sim-recovery-learned-detector-expanded-hard-negative-model-shadow
```
