# Fasim GPU AUTO Threshold And TopK Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add evidence-driven optimization support for GPU DP+column AUTO by quantifying CPU threshold fallback, sweeping TopK, and shadowing N-aware GPU threshold equivalence without changing default behavior.

**Architecture:** Keep GPU AUTO default-off and validation strict. Add profile counters around threshold-source selection and compact TopK overflow handling. Extend the hg38 taxonomy benchmark to optionally run a TopK sweep and report whether N-containing windows can safely use GPU peak thresholds in shadow mode.

**Tech Stack:** C++17 Fasim code, CUDA prealign existing APIs, Python benchmark scripts, Makefile check targets.

### Task 1: Threshold Telemetry

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Test: `scripts/check_fasim_gpu_auto_threshold_topk_telemetry.py`
- Modify: `Makefile`

**Step 1: Write the failing test**

Create a Python check that runs the existing small hg38 mismatch fixtures and requires these metrics to exist:

```text
fasim_gpu_dp_column_threshold_gpu_windows
fasim_gpu_dp_column_threshold_cpu_windows
fasim_gpu_dp_column_threshold_cpu_seconds
fasim_gpu_dp_column_threshold_shadow_enabled
fasim_gpu_dp_column_threshold_shadow_compared_windows
fasim_gpu_dp_column_threshold_shadow_mismatches
```

**Step 2: Run test to verify it fails**

Run:

```bash
make check-fasim-gpu-auto-threshold-topk-telemetry
```

Expected: fails because metrics are missing.

**Step 3: Implement minimal telemetry**

Add profile fields and print benchmark metrics. Count threshold source inside the helper that decides whether to use GPU peak max or `calc_score_once()`. Track CPU threshold elapsed time separately.

**Step 4: Verify green**

Run:

```bash
make check-fasim-gpu-auto-threshold-topk-telemetry
make check-fasim-gpu-dp-column-hg38-score-mismatch-fix
```

### Task 2: N-Aware Threshold Shadow

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Test: `scripts/check_fasim_gpu_auto_threshold_topk_telemetry.py`

**Step 1: Extend the failing test**

Run AUTO+validate with:

```text
FASIM_GPU_DP_COLUMN_THRESHOLD_SHADOW=1
```

Require shadow counters to show comparisons and zero mismatches on the fixed hg38 fixtures.

**Step 2: Implement shadow mode**

When CPU threshold is selected because transformed target contains true non-ACGT, compute both CPU `calc_score_once()` and GPU peak max in shadow mode. Keep production threshold on CPU. Count mismatches and max absolute delta.

**Step 3: Verify**

Run the telemetry check and full hg38 taxonomy with shadow enabled when optional hg38 inputs are present.

### Task 3: TopK Sweep And Dynamic TopK Gate

**Files:**
- Modify: `scripts/benchmark_fasim_gpu_dp_column_auto_hg38_validation_taxonomy.py`
- Modify: `docs/fasim_gpu_dp_column_auto_hg38_validation_taxonomy.md`
- Test: `scripts/check_fasim_gpu_auto_threshold_topk_telemetry.py`

**Step 1: Write failing sweep expectation**

Add a test that runs the small hg38 fixtures with a tiny TopK sweep and requires a generated table containing:

```text
topK
auto_seconds
exact_extends
compact_fallback_windows
digest_match
validation_failed_windows
```

**Step 2: Implement benchmark sweep**

Add `--topk-sweep` to the hg38 taxonomy script. For each TopK value, run AUTO+validate with `FASIM_GPU_DP_COLUMN_TOPK_CAP=<value>`, keep digest validation strict, and append a TopK sweep section to the report.

**Step 3: Dynamic TopK decision**

Do not change runtime policy in this PR unless the sweep demonstrates a clean win. Document dynamic TopK as the next implementation candidate if higher TopK lowers exact extends without digest or validation regressions.

**Step 4: Verify**

Run:

```bash
make check-fasim-gpu-auto-threshold-topk-telemetry
make check-fasim-gpu-dp-column-hg38-score-mismatch-fix
make check-fasim-gpu-dp-column-auto-policy
python3 -B -m py_compile scripts/benchmark_fasim_gpu_dp_column_auto_hg38_validation_taxonomy.py scripts/check_fasim_gpu_auto_threshold_topk_telemetry.py
git diff --check
```
