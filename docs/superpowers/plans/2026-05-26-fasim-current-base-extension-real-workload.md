# Fasim Current-Base CPU Extension Real Workload Characterization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to execute this docs/result plan. This PR must not change Fasim runtime
> semantics.

**Goal:** Use #146 CPU extension telemetry to determine whether current-base
real workloads are dominated by `aligner.Align()` inside CPU extension.

**Architecture:** Run the current clean-base sharded runner on two real
workloads with active current-base envs only, validate digest against
single-process runs, aggregate the #146 telemetry, and document the decision
boundary for future GPU score-only work.

**Tech Stack:** CUDA Fasim binary, Python sharded runner, JSON telemetry reports,
Markdown docs.

---

### Task 1: Confirm Base and Inputs

- [x] Use branch `fasim-current-base-extension-real-workload` from
  `origin/cuda-p0.2-initial-handoff-pipeline` after #146.
- [x] Build `fasim_longtarget_cuda` with `make build-fasim-cuda`.
- [x] Use `H19.fa`.
- [x] Use the rheMac10 nonchrom top8 target from the existing local benchmark
  inputs.
- [x] Use the hg38 chr21+chr22 target from the existing local workload matrix
  inputs.

### Task 2: Run Real Workload Matrix

- [x] Run `rheMac10_nonchrom_top8_H19` with:
  - `FASIM_EXTEND_THREADS=4`, `workers=4`
  - `FASIM_EXTEND_THREADS=4`, `workers=6`
  - `FASIM_EXTEND_THREADS=6`, `workers=4`
  - `FASIM_EXTEND_THREADS=6`, `workers=6`
- [x] Run `hg38_chr21_chr22_H19` with the same four modes.
- [x] Use `env -u FASIM_CUDA_DEVICES`.
- [x] Use `FASIM_ENABLE_PREALIGN_CUDA=1`.
- [x] Use `--validate-single`, `--gpu-ids 0,1`, `--cpu-pool 0-19`,
  `--cpu-cores-per-worker 3`, and `--auto-cpu-core-ranges`.
- [x] Confirm all rows are digest clean and report zero preAlign CUDA fallbacks.

### Task 3: Summarize Telemetry

- [x] Collect wall seconds, single seconds, records, preAlign seconds,
  `fasim_extend_seconds`, `fasim_extend_align_seconds`, align ratio, align
  calls, align cells, conversion seconds, sort/unique seconds, output seconds,
  and fallbacks.
- [x] Inspect per-worker telemetry for the fastest rheMac10 row.
- [x] Inspect active versus idle workers for hg38 chr21+chr22.
- [x] Note that sharded telemetry seconds are summed and can exceed wall time.

### Task 4: Write Docs and Verify

- [x] Create
  `docs/fasim_current_base_cpu_extension_real_workload.md`.
- [x] Keep the conclusion scoped to current-base active envs.
- [x] State that the next GPU investigation should decompose `aligner.Align()`
  or use score-only shadowing only if the score boundary is cleanly exposed.
- [x] Run verification:

```bash
make build-fasim-cuda
python3 -m py_compile scripts/fasim_sharded_runner.py
git diff --check
```

- [x] Commit:

```text
fasim: characterize current-base extension on real workloads
```
