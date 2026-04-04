# Whole-Genome Exact-Safe Throughput Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the exact-safe GPU mainline measurable and optimizable toward the 24-hour whole-genome target before enabling any speed-first mode.

**Architecture:** Keep exact-safe semantics as the default path, and optimize the program in the order that current telemetry supports: first make the whole-genome harness trustworthy, then treat SIM initial scan and `calc_score` coverage as parallel P0 bottlenecks, keep `locate` as a long-tail reducer, and only then promote additional GPU lanes or speed-first modes. Do not weaken deterministic tie-breaking, do not replace ordered row-run summaries with unordered summaries, and do not mix non-byte-identical paths into the default runner.

**Tech Stack:** C++, CUDA, existing benchmark stderr telemetry, shell-based regression checks, Python runtime projection script.

### Task 1: Make The Whole-Genome Harness Explain Bottlenecks

**Files:**
- Modify: `longtarget.cpp`
- Modify: `scripts/project_whole_genome_runtime.py`
- Modify: `scripts/check_project_whole_genome_runtime.sh`
- Test: `Makefile`

**Step 1: Add window-pipeline eligibility counters**

Add benchmark counters in `longtarget.cpp` next to the existing window-pipeline telemetry so stderr can distinguish:
- tasks considered
- tasks eligible
- ineligible because `twoStage`
- ineligible because `simFast`
- ineligible because validate mode
- ineligible because query length > 8192
- ineligible because target length > 8192
- ineligible because `minScore < 0`
- batch-shape fallback count

Reuse the existing `recordSimWindowPipelineFallback(...)` path instead of inventing a second fallback mechanism.

**Step 2: Add `calc_score` fallback coverage counters**

In the exact threshold preparation path inside `longtarget.cpp`, add stderr counters for:
- total threshold tasks
- CUDA threshold tasks
- CPU fallback tasks
- CPU fallback because query length > 8192
- CPU fallback because target length > 8192
- CPU fallback because target length > 65535

If one task can trigger multiple constraints, emit a single primary reason so the totals remain interpretable.

**Step 3: Extend the runtime projection script**

Extend `scripts/project_whole_genome_runtime.py` so JSON output carries through the new telemetry fields when present, without changing existing `projected_*` keys. Keep the current projection math unchanged in this step; only expose more benchmark context.

**Step 4: Tighten the projection check**

Update `scripts/check_project_whole_genome_runtime.sh` so it validates that the script still accepts old logs and also preserves the new optional telemetry in JSON mode.

**Step 5: Verify**

Run:

```bash
make build
make check-project-whole-genome-runtime
make check-sim-cuda-window-pipeline
make check-sim-cuda-window-pipeline-overlap
```

Expected:
- build succeeds
- projection script still passes its current gate
- pipeline checks still show `.lite` equivalence

**Step 6: Commit**

```bash
git add longtarget.cpp scripts/project_whole_genome_runtime.py scripts/check_project_whole_genome_runtime.sh
git commit -m "plan: add whole-genome telemetry coverage gates"
```

### Task 2: Treat SIM Initial Scan As P0-A

**Files:**
- Modify: `cuda/sim_scan_cuda.cu`
- Modify: `cuda/sim_scan_cuda.h`
- Modify: `sim.h`
- Test: `Makefile`

**Step 1: Instrument the exact-safe initial path for profiler-guided decisions**

Add narrow telemetry around the exact-safe initial run-summary path so benchmark logs can separate:
- run-summary detection/compaction time
- grouped/segmented reduce time when enabled
- exact top-K replay time
- safe-store rebuild/compaction time

Do not change result semantics in this step.

**Step 2: Optimize run-summary kernels**

If profiler confirms long runs still serialize inside block-parallel kernels, implement the smallest exact-safe refinement that preserves row order and the “first endJ that reaches the max score” rule. Acceptable directions:
- segmented grouping by contiguous same-start runs
- warp-cooperative aggregation for long runs

Do not reintroduce raw-event handoff as the default path.

**Step 3: Optimize device-side candidate maintenance**

Work directly on `sim_scan_reduce_initial_candidate_states_kernel` and adjacent reducer code. Inputs must remain row-run summaries in original order. The goal is to split serial replay into finer chunks without changing ordered replay semantics or the exact top-K tie-breaking behavior.

**Step 4: Keep the safe-store contract intact**

Make sure the default summary-handoff path still rebuilds or mirrors a valid exact-safe safe-store for later `safe_workset` and GPU safe-window planning. No optimization is allowed to drop the safe-store mirror.

**Step 5: Verify**

Run:

```bash
make build
make check-sim-initial-cuda-merge
make check-smoke-cuda-sim-region
make check-sample-cuda-sim-region
make check-matrix-cuda-sim-region
```

Expected:
- exact-safe tests still pass
- `benchmark.sim_initial_scan_seconds` or its subcomponents improve on the target workload
- no regression in output identity

**Step 6: Commit**

```bash
git add cuda/sim_scan_cuda.cu cuda/sim_scan_cuda.h sim.h
git commit -m "perf: reduce exact-safe initial scan overhead"
```

### Task 3: Treat `calc_score` Coverage As P0-B

**Files:**
- Modify: `longtarget.cpp`
- Modify: `stats.h`
- Modify: `cuda/calc_score_cuda.cu`
- Modify: `cuda/calc_score_cuda.h`
- Test: `Makefile`

**Step 1: Make fallback coverage observable**

Reuse the counters from Task 1 to verify exactly how much work is still missing CUDA threshold coverage. Before changing kernels, capture representative logs for:
- sample
- 100–200 Mb shard
- chr22 or another long representative shard

**Step 2: Extend exact CUDA threshold coverage**

Implement the smallest exact-safe extension that reduces CPU fallback rate for long tasks. The preferred direction is tiled or streamed CUDA threshold execution that keeps results byte-identical. Do not spend this phase on SSE/AVX micro-optimizations unless fallback coverage is already high.

**Step 3: Improve batching at the task-table level**

Where the deterministic task table already groups work, batch compatible threshold requests so query/device context reuse is preserved across more tasks.

**Step 4: Verify**

Run:

```bash
make build
make check-smoke
make check-sample
make check-matrix
make check-smoke-cuda-sim-region
make check-sample-cuda-sim-region
```

Expected:
- exact checks still pass
- CUDA threshold coverage increases on representative logs
- `calc_score_seconds` and fallback ratios both improve

**Step 5: Commit**

```bash
git add longtarget.cpp stats.h cuda/calc_score_cuda.cu cuda/calc_score_cuda.h
git commit -m "perf: expand exact cuda threshold coverage"
```

### Task 4: Keep `locate` In P1 And Only Shorten The Tail

**Files:**
- Modify: `sim.h`
- Modify: `cuda/sim_locate_cuda.cu`
- Modify: `longtarget.cpp`
- Test: `Makefile`

**Step 1: Promote bounded precheck telemetry**

Run representative workloads with `LONGTARGET_SIM_CUDA_LOCATE_EXACT_PRECHECK=shadow` and log:
- no-update proofs
- expansion cells
- stop reasons
- GPU locate time inside exact fallback

Only after the data is stable should `on` be considered for a subset of workloads.

**Step 2: Batch small exact locate requests**

Use the existing locate batch substrate to reduce launch and round-trip overhead for fallback-heavy small requests. Do not redesign the locate algorithm in this phase.

**Step 3: Reduce safe-window planner tail cases**

Prioritize overflow, empty-selection, and exact-fallback tail cases. Treat this as a benchmark variance reducer, not the main throughput engine.

**Step 4: Verify**

Run:

```bash
make build
make check-sim-locate-update
make check-sim-safe-workset-cuda
make check-smoke-cuda-sim-region-locate
make check-sample-cuda-sim-region-locate
```

Expected:
- safe-workset remains exact-safe mainline
- fallback counts or tail time decrease
- no new mismatch against exact fallback

**Step 5: Commit**

```bash
git add sim.h cuda/sim_locate_cuda.cu longtarget.cpp
git commit -m "perf: trim exact locate long-tail fallback cost"
```

### Task 5: Promote Window Pipeline Only Through Measured Gates

**Files:**
- Modify: `longtarget.cpp`
- Modify: `scripts/check_sim_cuda_window_pipeline.sh`
- Modify: `scripts/check_sim_cuda_window_pipeline_overlap.sh`
- Modify: `README.md`
- Test: `Makefile`

**Step 1: Record eligibility and fallback ratios**

Use the new telemetry from Task 1 to compute, on representative shard runs:
- eligible task ratio
- eligible bp ratio
- task fallback ratio
- dominant ineligibility reasons

Do not change the runtime eligibility condition in this step.

**Step 2: Define promotion gates**

Document promotion rules in `README.md`:
- eligible ratio threshold
- fallback ratio threshold
- exactness gate on `.lite` output for pipeline and overlap modes

**Step 3: Update pipeline checks**

Extend the existing pipeline check scripts so they fail clearly when eligibility is near zero or when fallback dominates the benchmark, even if output equivalence still holds.

**Step 4: Verify**

Run:

```bash
make build
make check-sim-cuda-window-pipeline
make check-sim-cuda-window-pipeline-overlap
```

Expected:
- pipeline and overlap checks still pass
- benchmark logs now explain whether the lane is worth promotion

**Step 5: Commit**

```bash
git add longtarget.cpp scripts/check_sim_cuda_window_pipeline.sh scripts/check_sim_cuda_window_pipeline_overlap.sh README.md
git commit -m "docs: gate window pipeline promotion on eligibility telemetry"
```

### Task 6: Only After Exact-Safe Plateaus, Add Explicit Throughput Mode

**Files:**
- Modify: `README.md`
- Modify: `scripts/`
- Modify: `Makefile`

**Step 1: Freeze the exact-safe baseline**

Before adding any throughput preset, record exact-safe shard and representative runs with:
- projected total hours
- projected `calc_score` seconds
- projected SIM seconds
- projected postprocess seconds

**Step 2: Add an explicit opt-in preset**

Expose a documented throughput preset for:
- `LONGTARGET_TWO_STAGE=1`
- `LONGTARGET_PREFILTER_BACKEND=prealign_cuda`
- optional `LONGTARGET_SIM_FAST_UPDATE_BUDGET`
- optional CUDA traceback

Do not make this preset implicit or default.

**Step 3: Add a comparison script**

Add a script that runs the throughput preset and the exact-safe baseline on a shard or chr-scale subset, then reports overlap/score deltas and whether the preset is inside agreed tolerance.

**Step 4: Verify**

Run:

```bash
make build
make check-project-whole-genome-runtime
```

Expected:
- exact-safe baseline remains documented
- throughput mode is explicit and separately measured

**Step 5: Commit**

```bash
git add README.md Makefile scripts
git commit -m "docs: add explicit throughput mode preset"
```

## Acceptance Criteria

1. The default exact-safe path still passes current smoke, sample, matrix, region, safe-workset, and window-pipeline equivalence checks.
2. Benchmark logs can explain why work missed the window-pipeline lane and why threshold work fell back to CPU.
3. `benchmark.sim_initial_scan_seconds` and `calc_score` coverage both improve on representative workloads.
4. Whole-genome estimates report projected total, projected `calc_score`, projected SIM, and projected postprocess time, and those estimates are backed by sample plus shard-scale logs.
5. Any non-exact or non-byte-identical mode remains explicit opt-in and never becomes the default exact-safe runner.

## Non-Goals

- Do not move outer `k`/LIST control flow onto the GPU.
- Do not replace ordered row-run summaries with unordered summaries.
- Do not make CUDA traceback, `sim_fast`, or two-stage refinement part of the default exact-safe path.
- Do not spend the next phase primarily on `locate` unless new telemetry shows it has become the top wall-time contributor again.
