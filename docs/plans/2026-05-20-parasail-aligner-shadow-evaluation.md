# Parasail Aligner Shadow Evaluation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Evaluate a real, default-off Parasail aligner shadow without replacing Fasim `aligner.Align`.

**Architecture:** Keep the #106 stub gate unchanged for default builds. Add optional build discovery for explicit `FASIM_PARASAIL_ENABLE=1` builds, then run the existing side-path comparison against CPU SSW output for sampled requests and document whether score, endpoints, CIGAR, digest, and timing are viable.

**Tech Stack:** GNU Make, C++11, optional Parasail headers/libs, Python benchmark harness.

### Task 1: Add real-shadow check contract

**Files:**
- Modify: `scripts/check_fasim_parasail_aligner_shadow.py`

**Step 1: Write the failing test**

Run:

```bash
python3 scripts/check_fasim_parasail_aligner_shadow.py --help | rg -- '--expect-supported'
```

Expected before implementation: no match.

**Step 2: Implement the minimal script option**

Add `--expect-supported`. Default behavior remains the stub-gate check. When enabled, require:

- `supported=1`
- `disabled_reason=0`
- `fallbacks=0`
- `requests_compared>0`
- `uses_runtime_output=0`

Keep mismatch checks strict.

**Step 3: Verify help exposes the option**

Run:

```bash
python3 scripts/check_fasim_parasail_aligner_shadow.py --help | rg -- '--expect-supported'
```

Expected: option is listed.

### Task 2: Add optional Parasail dependency discovery

**Files:**
- Modify: `Makefile`

**Step 1: Implement `FASIM_PARASAIL_DIR` support**

When `FASIM_PARASAIL_ENABLE=1` and `FASIM_PARASAIL_DIR` is set, append:

- `-I$(FASIM_PARASAIL_DIR)/include`
- fallback include for source trees with top-level `parasail.h`
- `-L$(FASIM_PARASAIL_DIR)/lib`
- rpath to the same lib directory

Do not change default stub builds.

**Step 2: Verify default build still uses stub**

Run:

```bash
make check-fasim-parasail-aligner-shadow
```

Expected: default unsupported stub gate passes.

### Task 3: Build or locate local Parasail

**Files:**
- No repo-tracked file changes expected.

**Step 1: Build local Parasail into `.tmp/parasail-install` if needed**

Use the existing upstream source under `.tmp/parasail-src` or copy/clone into this worktree's `.tmp`.

**Step 2: Verify real binary builds**

Run:

```bash
make build-fasim-cuda FASIM_PARASAIL_ENABLE=1 FASIM_PARASAIL_DIR=$(pwd)/.tmp/parasail-install
```

Expected: binary links with real `cpu/parasail_shadow.o`.

### Task 4: Run real Parasail shadow sample

**Files:**
- Modify docs after results: `docs/fasim_parasail_aligner_shadow.md`

**Step 1: Run supported check**

Run:

```bash
python3 scripts/check_fasim_parasail_aligner_shadow.py \
  --cuda-bin ./fasim_longtarget_cuda \
  --expect-supported
```

Expected: real shadow runs; mismatches are reported by strict counters if present.

**Step 2: Refresh benchmark doc**

Run:

```bash
python3 scripts/benchmark_fasim_parasail_aligner_shadow.py \
  --cuda-bin ./fasim_longtarget_cuda \
  --output docs/fasim_parasail_aligner_shadow.md \
  --require-profile \
  --check
```

Expected: report states whether real Parasail was supported and whether mismatch counters are zero.

### Task 5: Final validation and commit

**Files:**
- All changed files.

Run:

```bash
make check-fasim-parasail-aligner-shadow
python3 -B -m py_compile scripts/check_fasim_parasail_aligner_shadow.py scripts/benchmark_fasim_parasail_aligner_shadow.py
git diff --check
git status --short
```

Then commit and push the stacked branch if validation supports the result.
