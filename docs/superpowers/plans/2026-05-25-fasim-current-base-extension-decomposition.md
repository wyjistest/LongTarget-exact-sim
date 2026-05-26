# Fasim Current-Base CPU Extension Decomposition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add telemetry-only decomposition for current-base Fasim CPU extension work so we can tell whether score-only alignment is the right next GPU candidate.

**Architecture:** Extend the existing `benchmark.fasim_*` stderr telemetry with counters/timers from `fastSIM_extend_from_scoreinfo()`, parse/aggregate those fields through the existing sharded runner, and document how to interpret the split. Authority remains CPU output; no Accelign, scoring, output, scheduling, or runtime semantics change.

**Tech Stack:** C++ Fasim telemetry in `fasim/Fasim-LongTarget.cpp` / `fasim/fastsim.h`, Python runner telemetry parser, Bash/Python smoke checks, Markdown docs.

---

### Task 1: Test New Telemetry Fields

**Files:**
- Modify: `scripts/check_fasim_sharded_runner_telemetry_parser.py`
- Modify: `scripts/check_fasim_current_base_prealign_telemetry.sh`
- Modify: `scripts/check_fasim_sharded_runner_telemetry.sh`

- [x] **Step 1: Add parser expectations**

Require synthetic stderr to include new fields:

```text
benchmark.fasim_extend_candidates=4
benchmark.fasim_extend_cutlength_attempts=7
benchmark.fasim_extend_align_calls=7
benchmark.fasim_extend_align_cells=7000
benchmark.fasim_extend_align_seconds=0.300000
benchmark.fasim_extend_convert_calls=3
benchmark.fasim_extend_convert_seconds=0.040000
benchmark.fasim_extend_sort_unique_seconds=0.010000
benchmark.fasim_extend_records_before_filter=5
benchmark.fasim_extend_records_emitted=2
benchmark.fasim_extend_empty_scoreinfo=1
```

The parser test must assert these fields parse and aggregate correctly.

- [x] **Step 2: Add e2e grep expectations**

Both current-base telemetry smoke scripts must require the new
`benchmark.fasim_extend_*` lines and ensure sharded reports carry them.

- [x] **Step 3: Run red tests**

Run:

```bash
make check-fasim-sharded-runner-telemetry-parser
```

Expected before implementation: fail because aggregate counters are not summed
or Fasim does not emit the new fields.

### Task 2: Implement Extension Telemetry

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `fasim/fastsim.h`

- [x] **Step 1: Add telemetry fields**

Add process-level counters/timers:

```text
extendCandidates
extendCutlengthAttempts
extendAlignCalls
extendAlignCells
extendAlignSeconds
extendConvertCalls
extendConvertSeconds
extendSortUniqueSeconds
extendRecordsBeforeFilter
extendRecordsEmitted
extendEmptyScoreInfo
```

- [x] **Step 2: Add callback hooks in `fastSIM_extend_from_scoreinfo()`**

Record:

```text
candidate count = finalScoreInfo.size()
empty scoreinfo count when finalScoreInfo is empty
one cutlength attempt per Iden loop iteration
one align call and approximate cells = strA.size() * smallSeq.size()
align seconds around `aligner.Align()`
convert calls/seconds around `convertMyTriplex()`
sort/unique seconds around the sort/unique block
records before final filter = myTriplexList.size() after de-dup
records emitted = pushed triplex count
```

Do not change output records or ordering.

- [x] **Step 3: Emit fields**

Emit new `benchmark.fasim_extend_*` lines in `fasim_emit_runtime_telemetry()`.

### Task 3: Runner Aggregation and Docs

**Files:**
- Modify: `scripts/fasim_sharded_runner.py`
- Modify: `docs/fasim_current_base_prealign_cuda_decomposition.md`
- Create: `docs/fasim_current_base_cpu_extension_decomposition.md`

- [x] **Step 1: Sum new count fields**

Add new count keys to `_sum_fasim_telemetry()`.

- [x] **Step 2: Document fields**

Document that seconds are summed across workers and can exceed wall time.
Explain that this is a decision gate for future score-only GPU shadow work.

### Task 4: Verify and PR

**Files:**
- Modify: `Makefile`
- Modify: implementation/test/doc files above

- [x] **Step 1: Add/refresh checks**

Run:

```bash
make build-fasim-cuda
make check-fasim-sharded-runner-telemetry-parser
make check-fasim-current-base-prealign-telemetry
make check-fasim-sharded-runner-telemetry
python3 -m py_compile scripts/fasim_sharded_runner.py scripts/check_fasim_sharded_runner_telemetry_parser.py
git diff --check
```

- [x] **Step 2: Commit and PR**

Commit message:

```text
fasim: decompose current-base CPU extension telemetry
```
