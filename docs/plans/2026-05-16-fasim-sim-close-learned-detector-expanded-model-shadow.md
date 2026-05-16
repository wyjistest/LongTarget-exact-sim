# Fasim SIM-Close Learned Detector Expanded Model Shadow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Evaluate an offline learned/ranked SIM-close detector shadow on the expanded corpus from #86 without changing runtime behavior.

**Architecture:** Reuse the existing learned-detector dataset export, negative dataset builder, and no-heavy-dependency model-shadow helper. Add a stacked expanded-corpus check/report that runs on the #86 corpus gate, evaluates current split plus workload-held-out and family-held-out policies when non-degenerate, and compares learned shadow metrics against the current hand-written guard. Keep SIM labels strictly offline labels and do not wire any model into Fasim or SIM-close runtime.

**Tech Stack:** Bash check scripts, Python TSV/report generators, existing `benchmark_fasim_sim_recovery_learned_detector_model_shadow.py`, generated `.tmp` TSV artifacts, Markdown docs.

### Task 1: Establish Baseline

**Files:**
- Read: `scripts/check_fasim_sim_recovery_learned_detector_dataset_expansion.sh`
- Read: `scripts/check_fasim_sim_recovery_learned_detector_model_shadow.sh`
- Read: `scripts/benchmark_fasim_sim_recovery_learned_detector_model_shadow.py`
- Read: `scripts/benchmark_fasim_sim_recovery_learned_detector_dataset_expansion.py`

**Step 1:** Run `./scripts/check_fasim_sim_recovery_learned_detector_dataset_expansion.sh`.

**Expected:** Exit 0. With local marmoset inputs, metrics include `workload_count=4`, `hard_negative_source_count=5`, and `modeling_gate=ready_for_offline_shadow`.

**Step 2:** Run `./scripts/check_fasim_sim_recovery_learned_detector_model_shadow.sh`.

**Expected:** Exit 0 on the existing small-dataset shadow. Record current output fields and reusable helpers.

### Task 2: Add a Failing Expanded-Shadow Check

**Files:**
- Create: `scripts/check_fasim_sim_recovery_learned_detector_expanded_model_shadow.sh`

**Step 1:** Create a check script that builds the expanded source TSV and negative TSV the same way #86 does.

**Step 2:** Make the check call a not-yet-existing expanded model shadow report script and assert required telemetry:
- `rows`
- `positive_rows`
- `negative_rows`
- `hard_negative_source_count`
- `workload_heldout_degenerate`
- `family_heldout_degenerate`
- `current_guard_recall`
- `current_guard_precision`
- `learned_shadow_recall`
- `learned_shadow_precision`
- `false_positives`
- `false_negatives`
- `selected_threshold`
- `candidate_eligible_recall`
- `candidate_eligible_precision`
- `production_model=0`
- `sim_labels_runtime_inputs=0`
- `runtime_behavior_changed=0`

**Step 3:** Run the check.

**Expected:** FAIL because the expanded model shadow script does not exist yet.

### Task 3: Implement Expanded Model Shadow Report

**Files:**
- Create: `scripts/benchmark_fasim_sim_recovery_learned_detector_expanded_model_shadow.py`
- Reuse helpers from: `scripts/benchmark_fasim_sim_recovery_learned_detector_model_shadow.py`
- Reuse split helpers from: `scripts/benchmark_fasim_sim_recovery_learned_detector_dataset_expansion.py`

**Step 1:** Read the negative dataset TSV and source dataset TSV.

**Step 2:** Evaluate three policies:
- current row split from the negative dataset
- workload-held-out split using `workload_id`
- family-held-out split using `family_id`

**Step 3:** For each policy, report train/validation counts and degeneracy. If a policy is non-degenerate, train on its train rows and evaluate on validation rows using existing no-heavy-ML model-shadow helpers.

**Step 4:** Compare learned-shadow validation metrics against `current_guard_metrics(source_rows, validation_split)` for the current split. For workload/family split policies, derive current guard metrics from source rows by matching their workload/family split keys.

**Step 5:** Emit total metrics for the primary decision policy. Prefer workload-held-out when non-degenerate, else family-held-out, else current split. Keep `production_model=0`, `sim_labels_runtime_inputs=0`, and `runtime_behavior_changed=0`.

### Task 4: Add Docs

**Files:**
- Create: `docs/fasim_sim_recovery_learned_detector_expanded_model_shadow.md`

**Step 1:** Document dataset size, hard-negative source count, split viability, current guard metrics, learned shadow metrics, candidate-eligible metrics, selected threshold, and decision.

**Step 2:** State explicitly that the report is offline-only, not runtime promotion, not recommended/default SIM-close, and not a production claim.

### Task 5: Wire Make Target

**Files:**
- Modify: `Makefile`

**Step 1:** Add `check-fasim-sim-recovery-learned-detector-expanded-model-shadow` to run the new check script.

**Step 2:** Do not modify existing runtime, exactness, CUDA, GPU, filter, scoring, threshold, or non-overlap targets.

### Task 6: Verification and Commit

**Files:**
- All modified files.

**Step 1:** Run:
```bash
make check-fasim-sim-recovery-learned-detector-dataset-expansion
make check-fasim-sim-recovery-learned-detector-model-shadow
make check-fasim-sim-recovery-learned-detector-expanded-model-shadow
make check-fasim-exactness
python3 -B -m py_compile scripts/benchmark_fasim_sim_recovery_learned_detector_dataset_expansion.py
python3 -B -m py_compile scripts/benchmark_fasim_sim_recovery_learned_detector_expanded_model_shadow.py
git diff --check
```

**Step 2:** Run scans:
```bash
python3 - <<'PY'
from pathlib import Path
for path in Path('.').glob('**/*'):
    if path.is_file() and '.git' not in path.parts and '.tmp' not in path.parts:
        data = path.read_bytes()
        if b'\xe2\x80\xaa' in data or b'\xe2\x80\xab' in data or b'\xe2\x80\xae' in data:
            raise SystemExit(f'bidi marker found: {path}')
PY
rg -n "CUDA|GPU|FASIM_GPU|FASIM_FILTER|non-overlap|threshold|score" scripts docs Makefile
rg -n "runtime model|production model|SIM labels.*runtime|recommended/default|default SIM-close" scripts docs Makefile
```

**Expected:** Verification commands pass. Route scans show no forbidden behavior changes outside offline docs/check/report code.

**Step 3:** Commit:
```bash
git add docs/fasim_sim_recovery_learned_detector_expanded_model_shadow.md \
  docs/plans/2026-05-16-fasim-sim-close-learned-detector-expanded-model-shadow.md \
  scripts/check_fasim_sim_recovery_learned_detector_expanded_model_shadow.sh \
  scripts/benchmark_fasim_sim_recovery_learned_detector_expanded_model_shadow.py \
  Makefile
git commit -m "fasim: evaluate expanded learned detector shadow"
```

**Step 4:** Push and create a stacked PR against `fasim-sim-recovery-learned-detector-corpus-expansion`.
