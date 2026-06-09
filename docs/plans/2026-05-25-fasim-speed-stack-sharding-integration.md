# Fasim Speed Stack Sharding Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the final Fasim speed stack into the current sharding/hg38 branch in small default-off steps with digest-clean verification.

**Architecture:** Keep the sharded runner as outer process-level scheduling. Integrate Fasim runtime optimizations one module at a time, each behind an explicit env gate and each verified before the next module is started.

**Tech Stack:** C++11 Fasim runtime, existing Makefile test targets, shell/Python sharded runner checks, CUDA only for modules that already had CUDA implementations on the final speed stack line.

---

## Current Branch Fact

Current branch: `cuda-p0.2-initial-handoff-pipeline`.

Current integrated speed-stack status:

```text
done:
  FASIM_TRANSFERSTRING_TABLE
  FASIM_TRANSFERSTRING_TABLE_VALIDATE
  FASIM_SSW_PROFILE_CACHE
  FASIM_SSW_PROFILE_CACHE_VALIDATE
  FASIM_EXACT_COLUMN_EXTEND_BATCH
  FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE
  FASIM_GPU_DP_COLUMN_AUTO
  FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS
  FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS
  FASIM_SSW_PROFILE_CONTEXT
  FASIM_SSW_PROFILE_CONTEXT_VALIDATE
  FASIM_SSW_AVX2
  FASIM_SSW_AVX2_MODE

active before integration:
  FASIM_ENABLE_PREALIGN_CUDA
  FASIM_CUDA_DEVICE
  FASIM_CUDA_DEVICES
  FASIM_PREALIGN_CUDA_TOPK
  FASIM_PREALIGN_CUDA_MAX_TASKS
  FASIM_PREALIGN_PEAK_SUPPRESS_BP
  FASIM_EXTEND_THREADS
  FASIM_OUTPUT_MODE
```

Notes:

- `FASIM_GPU_DP_COLUMN_AUTO` remains default-off and size-gated.
- `FASIM_EXACT_COLUMN_EXTEND_BATCH` is default-off and is used with the GPU
  DP/AUTO path; it is not described as changing standalone preAlign topK
  behavior.
- `FASIM_SSW_PROFILE_CONTEXT` requires `FASIM_SSW_PROFILE_CACHE=1`.
- `FASIM_SSW_AVX2` requires a binary built with `FASIM_SIMD_FLAGS=-mavx2`; the
  default `-msse2` build reads the env but cannot activate AVX2 kernels.

Audit command:

```bash
strings ./fasim_longtarget_cuda | rg 'FASIM_[A-Z0-9_]+' | sort -u
```

## Task 1: TransferString Table Opt-In

**Files:**
- Modify: `fasim/rules.h`
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `Makefile`
- Create: `tests/test_fasim_transferstring_table.cpp`
- Modify docs that list current active envs.

- [x] **Step 1: Add failing test**

Add `tests/test_fasim_transferstring_table.cpp` that compares table-driven output to `transferString` across para/anti-para rules and checks default-off behavior.

- [x] **Step 2: Verify red**

Run:

```bash
make build-fasim-transferstring-table-test
```

Expected before implementation: compile failure for missing `transferStringTableDriven` / `transferStringTableOptIn`.

- [x] **Step 3: Implement default-off opt-in**

Add:

```text
FASIM_TRANSFERSTRING_TABLE
FASIM_TRANSFERSTRING_TABLE_VALIDATE
transferStringTableDriven(...)
transferStringTableOptIn(...)
```

Switch Fasim runtime calls from `transferString(...)` to `transferStringTableOptIn(...)`.

- [x] **Step 4: Verify green**

Run:

```bash
make build-fasim-transferstring-table-test
./tests/test_fasim_transferstring_table
FASIM_TRANSFERSTRING_TABLE=1 ./tests/test_fasim_transferstring_table
FASIM_TRANSFERSTRING_TABLE=1 FASIM_TRANSFERSTRING_TABLE_VALIDATE=1 ./tests/test_fasim_transferstring_table
make build-fasim
make build-fasim-cuda
strings ./fasim_longtarget_cuda | rg 'FASIM_TRANSFERSTRING_TABLE'
```

Expected: all commands pass and `strings` shows both table env names.

## Task 2: SSW Profile Cache

**Files:**
- Inspect from `origin/main`: `fasim/ssw_cpp.cpp`, `fasim/ssw_cpp.h`, `fasim/fastsim.h`, related benchmark/check scripts.
- Modify only the minimal runtime files needed to expose the default-off cache.
- Add a focused test or script check that verifies default-off equality and active telemetry.

- [x] **Step 1: Diff source module**

Run:

```bash
git diff HEAD..origin/main -- fasim/ssw_cpp.cpp fasim/ssw_cpp.h fasim/fastsim.h
git grep -n 'FASIM_SSW_PROFILE_CACHE' origin/main -- fasim
```

- [x] **Step 2: Add failing coverage**

Add a focused test/check that expects `FASIM_SSW_PROFILE_CACHE` to appear in `strings ./fasim_longtarget_cuda` and verifies Fasim digest equality with cache off vs on for a small fixture.

- [x] **Step 3: Port implementation default-off**

Port only the profile-cache implementation, not AVX2/ProfileContext. Keep `FASIM_SSW_PROFILE_CACHE=1` opt-in and add validate/shadow gates only if they exist cleanly in the source module.

- [x] **Step 4: Verify**

Run:

```bash
make build-fasim
make build-fasim-cuda
strings ./fasim_longtarget_cuda | rg 'FASIM_SSW_PROFILE_CACHE'
make check-fasim-sharded-runner
```

Expected: builds pass, env appears, sharded digest remains clean.

## Task 3: Exact-Column Extend Batch

**Files:**
- Inspect from `origin/main`: `fasim/Fasim-LongTarget.cpp`, `fasim/fastsim.h`, `cuda/prealign_cuda.cu`, `cuda/prealign_cuda.h`, `cuda/prealign_cuda_stub.cpp`, related tests/scripts.

- [x] **Step 1: Identify source commits**

Run:

```bash
git log --oneline --all --grep='exact-column' -i
git diff HEAD..origin/main -- fasim/Fasim-LongTarget.cpp fasim/fastsim.h cuda/prealign_cuda.cu cuda/prealign_cuda.h cuda/prealign_cuda_stub.cpp
```

- [x] **Step 2: Add failing coverage**

Add a small check that expects `FASIM_EXACT_COLUMN_EXTEND_BATCH` in the binary and validates no digest change with the env on for a fixture.

- [x] **Step 3: Port default-off implementation**

Port exact-column batch without enabling it by default. Preserve fallback and mismatch telemetry from the source stack.

- [x] **Step 4: Verify**

Run:

```bash
make build-fasim-cuda
strings ./fasim_longtarget_cuda | rg 'FASIM_EXACT_COLUMN_EXTEND_BATCH'
make check-fasim-sharded-runner
```

Expected: build passes, env appears, digest clean, fallback/mismatch telemetry clean.

## Task 4: GPU DP Column Auto

**Files:**
- Inspect from `origin/main`: `fasim/Fasim-LongTarget.cpp`, `fasim/fastsim.h`, `cuda/prealign_cuda.*`, scripts and docs for GPU DP column auto.

- [x] **Step 1: Identify source commits**

Run:

```bash
git log --oneline --all --grep='GPU DP column' -i
git grep -n 'FASIM_GPU_DP_COLUMN_AUTO' origin/main -- fasim cuda scripts
```

- [x] **Step 2: Add failing coverage**

Add a check that expects `FASIM_GPU_DP_COLUMN_AUTO` in the binary and verifies default-off digest equality.

- [x] **Step 3: Port size-gated implementation**

Port the AUTO policy default-off. Preserve min-cells/min-windows gates so small workloads stay on CPU/table paths.

- [x] **Step 4: Verify**

Run:

```bash
make build-fasim-cuda
strings ./fasim_longtarget_cuda | rg 'FASIM_GPU_DP_COLUMN_AUTO'
make check-fasim-sharded-runner
```

Expected: build passes, env appears, digest clean. Do not claim GPU utilization until telemetry shows active GPU path on a large workload.

## Task 5: AVX2 and ProfileContext

**Files:**
- Inspect from `origin/main`: `fasim/sswNew.cpp`, `fasim/ssw_cpp.cpp`, `fasim/ssw_cpp.h`, `fasim/fastsim.h`, Makefile AVX2 targets.

- [x] **Step 1: Decide split**

Integrated as two narrow steps:

```text
Task 5a: FASIM_SSW_PROFILE_CONTEXT layered on FASIM_SSW_PROFILE_CACHE
Task 5b: FASIM_SSW_AVX2 in sswNew.cpp with a dedicated -mavx2 direct test
```

- [x] **Step 2: Add coverage**

Add focused build/runtime checks for each env and compare digest off vs on for the sample fixture.

- [x] **Step 3: Port default-off implementation**

Keep both off by default. Do not change `FASIM_SIMD_FLAGS` defaults unless the source module requires it and the tests prove compatibility.

- [x] **Step 4: Verify**

Run:

```bash
make build-fasim
make build-fasim-cuda
make check-fasim-sharded-runner
```

Expected: builds pass, digest clean, active envs appear in `strings`.

## Completion Gate

Before marking the integration complete, run:

```bash
git diff --check
make build-fasim
make build-fasim-cuda
make build-fasim-transferstring-table-test
./tests/test_fasim_transferstring_table
FASIM_TRANSFERSTRING_TABLE=1 ./tests/test_fasim_transferstring_table
make build-fasim-ssw-profile-cache-test
make check-fasim-ssw-profile-cache-env
make check-fasim-exact-column-extend-batch-env
make check-fasim-exact-column-extend-batch-digest
make check-fasim-gpu-dp-column-auto-digest
make check-fasim-ssw-profile-context-env
make check-fasim-ssw-profile-context-digest
make check-fasim-ssw-avx2-direct
make check-fasim-ssw-avx2-digest
make check-fasim-sharded-runner
strings ./fasim_longtarget_cuda | rg 'FASIM_(TRANSFERSTRING_TABLE|SSW_PROFILE_CACHE|EXACT_COLUMN_EXTEND_BATCH|GPU_DP_COLUMN_AUTO|SSW_AVX2|SSW_PROFILE_CONTEXT)'
```

Completion requires all integrated envs to be present, default-off behavior to remain digest-clean, opt-in behavior to be digest-clean, and docs to match the current binary.
