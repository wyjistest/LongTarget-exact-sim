# Fasim Current Base PreAlign Telemetry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add telemetry-only reporting for the current clean-base Fasim preAlign CUDA path and CPU extension phase.

**Architecture:** Fasim emits structured `benchmark.fasim_*` lines to stderr at process exit. The sharded runner parses those lines from each worker stderr log and adds per-run and per-worker aggregate telemetry to `report.json`. CUDA timing is expanded in the existing preAlign CUDA API result without changing scoring, output, thresholds, scheduling, or default runtime behavior.

**Tech Stack:** C++11, CUDA runtime events, Python 3 runner JSON parsing, shell check scripts, Markdown docs.

---

### Task 1: Runner Telemetry Parser Test

**Files:**
- Create: `scripts/check_fasim_sharded_runner_telemetry_parser.py`
- Modify: `Makefile`
- Read: `scripts/fasim_sharded_runner.py`

- [ ] **Step 1: Write the failing parser/report test**

Create `scripts/check_fasim_sharded_runner_telemetry_parser.py` that imports `fasim_sharded_runner`, writes synthetic stderr logs containing:

```text
benchmark.fasim_prealign_cuda_requested=1
benchmark.fasim_prealign_cuda_active=1
benchmark.fasim_prealign_cuda_tasks=12
benchmark.fasim_prealign_cuda_batches=3
benchmark.fasim_prealign_cuda_kernel_seconds=0.120000
benchmark.fasim_prealign_cuda_total_seconds=0.150000
benchmark.fasim_extend_seconds=0.500000
benchmark.fasim_output_seconds=0.020000
```

Then assert:
- `_parse_fasim_telemetry_file()` returns numeric values.
- `_sum_fasim_telemetry()` sums count/seconds fields.
- `_run_to_json()` includes a `telemetry` object.
- `_worker_telemetry_from_shards()` aggregates two shard reports.

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=./scripts python3 ./scripts/check_fasim_sharded_runner_telemetry_parser.py
```

Expected: fail because telemetry parser/helper functions do not exist.

- [ ] **Step 3: Add Makefile target**

Add:

```make
check-fasim-sharded-runner-telemetry-parser:
	PYTHONPATH=./scripts python3 ./scripts/check_fasim_sharded_runner_telemetry_parser.py
```

and include it in `.PHONY`.

### Task 2: Runner Telemetry Implementation

**Files:**
- Modify: `scripts/fasim_sharded_runner.py`
- Modify: `scripts/check_fasim_sharded_runner_telemetry_parser.py`

- [ ] **Step 1: Add parser helpers**

Implement:
- `_parse_fasim_telemetry_text(text: str) -> dict[str, object]`
- `_parse_fasim_telemetry_file(path: Path) -> dict[str, object]`
- `_sum_fasim_telemetry(items: list[dict[str, object]]) -> dict[str, object]`
- `_worker_telemetry_from_shards(shard_reports: list[dict[str, object]]) -> dict[str, object]`

Only parse lines matching `benchmark.fasim_<name>=<value>`. Convert `0/1` active/requested fields and integer count fields to `int`; convert seconds fields to `float`; keep non-numeric values as strings.

- [ ] **Step 2: Attach telemetry to reports**

Extend `RunResult` with a `telemetry` field. Parse stderr immediately after `_run_fasim()` writes the stderr log. Include `telemetry` in `_run_to_json()`, per-shard `run`, manifest completed/failed entries, and top-level `single_run`.

- [ ] **Step 3: Add per-worker/top-level aggregate telemetry**

Add `telemetry` to each `per_worker` entry by summing shard run telemetry. Add top-level `sharded_telemetry` by summing completed shard telemetry. Do not let telemetry affect digest, scheduling, resume matching, or output merging.

- [ ] **Step 4: Verify GREEN**

Run:

```bash
PYTHONPATH=./scripts python3 ./scripts/check_fasim_sharded_runner_telemetry_parser.py
python3 -m py_compile scripts/fasim_sharded_runner.py scripts/check_fasim_sharded_runner_telemetry_parser.py
```

Expected: pass.

### Task 3: CUDA Timing Fields

**Files:**
- Modify: `cuda/prealign_cuda.h`
- Modify: `cuda/prealign_cuda.cu`

- [ ] **Step 1: Extend the result struct**

Add to `PreAlignCudaBatchResult`:

```cpp
double h2dSeconds;
double kernelSeconds;
double d2hSeconds;
double totalSeconds;
```

Keep `gpuSeconds` as a compatibility alias for kernel time.

- [ ] **Step 2: Time H2D, kernel, D2H, and total**

In `prealign_cuda_find_topk_column_maxima()`:
- Use `std::chrono::steady_clock` around synchronous H2D and D2H copies.
- Use existing CUDA events for kernel seconds.
- Use total wall time around the whole function body after input validation.
- Populate all result fields on success.

- [ ] **Step 3: Verify build**

Run:

```bash
make build-fasim-cuda
```

Expected: pass.

### Task 4: Fasim Process Telemetry

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Test: `scripts/check_fasim_current_base_prealign_telemetry.sh`
- Modify: `Makefile`

- [ ] **Step 1: Write failing end-to-end telemetry test**

Create `scripts/check_fasim_current_base_prealign_telemetry.sh` that:
- Builds/runs `fasim_longtarget_cuda` on `testDNA.fa + H19.fa`.
- Uses `FASIM_OUTPUT_MODE=lite`, `FASIM_VERBOSE=0`, `FASIM_ENABLE_PREALIGN_CUDA=1`, `FASIM_EXTEND_THREADS=2`.
- Captures stderr.
- Greps for required `benchmark.fasim_*` telemetry lines.
- Asserts the output digest still matches the same run with telemetry enabled.

Run:

```bash
BIN=$PWD/fasim_longtarget_cuda bash ./scripts/check_fasim_current_base_prealign_telemetry.sh
```

Expected: fail because Fasim does not emit those telemetry lines.

- [ ] **Step 2: Implement process counters**

Add a small telemetry accumulator in `fasim/Fasim-LongTarget.cpp` that records:
- requested/active
- device count and primary device
- topK, max tasks, suppress bp, extend threads
- preAlign batches/tasks
- H2D/kernel/D2H/total seconds
- CPU extend seconds
- output write seconds
- CUDA fallback count

- [ ] **Step 3: Time extension and output phases**

Wrap calls to `fastSIM_extend_from_scoreinfo()` in CUDA paths with a timer and add elapsed time to `fasim_extend_seconds`. Time output writing blocks and add elapsed time to `fasim_output_seconds`. Do not change output contents.

- [ ] **Step 4: Emit telemetry once**

Before process exit, print stable stderr lines:

```text
benchmark.fasim_prealign_cuda_requested=<0|1>
benchmark.fasim_prealign_cuda_active=<0|1>
benchmark.fasim_prealign_cuda_device=<device>
benchmark.fasim_prealign_cuda_devices=<count>
benchmark.fasim_prealign_cuda_tasks=<count>
benchmark.fasim_prealign_cuda_batches=<count>
benchmark.fasim_prealign_cuda_topk=<value>
benchmark.fasim_prealign_cuda_max_tasks=<value>
benchmark.fasim_prealign_cuda_peak_suppress_bp=<value>
benchmark.fasim_prealign_cuda_h2d_seconds=<seconds>
benchmark.fasim_prealign_cuda_kernel_seconds=<seconds>
benchmark.fasim_prealign_cuda_d2h_seconds=<seconds>
benchmark.fasim_prealign_cuda_total_seconds=<seconds>
benchmark.fasim_extend_threads=<value>
benchmark.fasim_extend_seconds=<seconds>
benchmark.fasim_output_seconds=<seconds>
benchmark.fasim_prealign_cuda_fallbacks=<count>
```

- [ ] **Step 5: Verify GREEN**

Run:

```bash
make build-fasim-cuda
BIN=$PWD/fasim_longtarget_cuda bash ./scripts/check_fasim_current_base_prealign_telemetry.sh
```

Expected: pass.

### Task 5: Runner Integration Smoke

**Files:**
- Create: `scripts/check_fasim_sharded_runner_telemetry.sh`
- Modify: `Makefile`

- [ ] **Step 1: Write sharded telemetry smoke**

Create a small two-contig input, run `scripts/fasim_sharded_runner.py` with CUDA Fasim and:

```bash
--workers 2 --gpu-ids 0,1 --output-mode lite --validate-single
--env FASIM_ENABLE_PREALIGN_CUDA=1
--env FASIM_EXTEND_THREADS=2
```

Assert:
- `report["single_vs_sharded_digest_match"] is True`
- every completed shard `run.telemetry` has required keys
- every `per_worker[*].telemetry` has summed fields
- top-level `sharded_telemetry` exists

- [ ] **Step 2: Verify**

Run:

```bash
make check-fasim-sharded-runner-telemetry
```

Expected: pass.

### Task 6: Documentation

**Files:**
- Create: `docs/fasim_current_base_prealign_cuda_decomposition.md`
- Modify: `docs/fasim_current_base_gpu_cpu_phase_timeline.md`

- [ ] **Step 1: Document telemetry fields**

Describe:
- Current active path remains preAlign CUDA.
- Telemetry is observational and does not change runtime semantics.
- H2D/kernel/D2H/total definitions.
- Runner JSON locations: `per_shard[*].run.telemetry`, `per_worker[*].telemetry`, `sharded_telemetry`, `single_run.telemetry`.

- [ ] **Step 2: Update #143 doc next-step link**

Add a short note that #144 fills the telemetry gap identified in #143.

### Task 7: Final Verification

**Files:**
- All modified files

- [ ] **Step 1: Run targeted checks**

Run:

```bash
make build-fasim-cuda
make check-fasim-current-base-prealign-telemetry
make check-fasim-sharded-runner-telemetry-parser
make check-fasim-sharded-runner-telemetry
make check-fasim-sharded-worker-gpu-env-hygiene
make check-fasim-sharded-manifest-threadsafe
python3 -m py_compile scripts/fasim_sharded_runner.py scripts/check_fasim_sharded_runner_telemetry_parser.py
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 2: Commit and PR**

Commit:

```bash
git add cuda/prealign_cuda.h cuda/prealign_cuda.cu fasim/Fasim-LongTarget.cpp scripts/fasim_sharded_runner.py scripts/check_fasim_sharded_runner_telemetry_parser.py scripts/check_fasim_current_base_prealign_telemetry.sh scripts/check_fasim_sharded_runner_telemetry.sh docs/fasim_current_base_prealign_cuda_decomposition.md docs/fasim_current_base_gpu_cpu_phase_timeline.md docs/superpowers/plans/2026-05-25-fasim-current-base-prealign-telemetry.md Makefile
git commit -m "fasim: report current-base preAlign telemetry"
git push -u origin fasim-current-base-prealign-telemetry
gh pr create --base cuda-p0.2-initial-handoff-pipeline --head fasim-current-base-prealign-telemetry --title "fasim: report current-base preAlign telemetry"
```

Expected: PR URL is printed.

### Self-Review

- Spec coverage: active preAlign CUDA telemetry, CPU extension seconds, runner report fields, and docs are covered.
- Placeholder scan: no TBD/TODO placeholders are used.
- Type consistency: telemetry field names match between Fasim stderr, runner parser, tests, and docs.
