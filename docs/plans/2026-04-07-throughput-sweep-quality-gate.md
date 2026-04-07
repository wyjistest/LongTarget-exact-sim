# Throughput Sweep Quality Gate Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the fasim throughput sweep from "fastest run wins" to "fastest run that clears a quality gate wins", while keeping the default exact-safe runner untouched.

**Architecture:** Keep one exact LongTarget baseline per sweep, compare each throughput run against the same baseline/output schema, and record both the overall fastest run and the fastest run that meets configurable quality thresholds. Preserve backward compatibility by keeping the legacy `best` field as the overall fastest run.

**Tech Stack:** Python 3 CLI tooling, bash check scripts, JSON reports, README documentation

### Task 1: Lock the new report contract in the sweep check

**Files:**
- Modify: `/data/wenyujianData/LongTarget-exact-sim/scripts/check_fasim_throughput_sweep.sh`

**Step 1: Write the failing check**

Extend the JSON assertions so the script requires:
- `quality_gate`
- `best_overall`
- `best_qualifying`
- a permissive gate that produces a non-null `best_qualifying`
- a strict gate variant that allows `best_qualifying` to be `null`

**Step 2: Run check to verify it fails**

Run: `bash ./scripts/check_fasim_throughput_sweep.sh`
Expected: FAIL because the current report has only `best`

**Step 3: Commit**

Wait until implementation and verification are complete.

### Task 2: Add quality-gated selection to the sweep CLI

**Files:**
- Modify: `/data/wenyujianData/LongTarget-exact-sim/scripts/benchmark_fasim_throughput_sweep.py`

**Step 1: Write minimal implementation**

Add CLI/config/report support for:
- `--min-relaxed-recall`
- `--min-top-hit-retention`
- `--require-qualifying-run`
- `quality_gate`, `best_overall`, `best_qualifying`

Keep `best` as an alias of `best_overall` for compatibility.

**Step 2: Keep output understandable**

Print both overall-fastest and qualifying-fastest summaries, and make it explicit when no run passes the gate.

**Step 3: Optional forward prep**

If the diff stays small, let the sweep record `topk` / `suppress_bp` so the script can evolve into a small-shard quality frontier runner without another structural rewrite. Do not expand defaults yet.

### Task 3: Update documentation

**Files:**
- Modify: `/data/wenyujianData/LongTarget-exact-sim/README.md`

**Step 1: Rewrite throughput sweep guidance**

Document that:
- `best_overall` is just the fastest run
- `best_qualifying` is the candidate to carry forward
- recommended workflow is small real shards first, then larger device/thread sweeps

### Task 4: Verify and keep the branch honest

**Files:**
- Modify if needed: `/data/wenyujianData/LongTarget-exact-sim/scripts/check_benchmark_throughput_comparator.sh`

**Step 1: Run targeted validation**

Run:
- `python3 -m py_compile scripts/benchmark_fasim_throughput_sweep.py scripts/benchmark_sample_vs_fasim.py`
- `bash ./scripts/check_fasim_throughput_sweep.sh`
- `bash ./scripts/check_benchmark_throughput_comparator.sh`

**Step 2: Run aggregated validation**

Run:
- `make check-fasim-throughput-sweep`

**Step 3: Commit**

```bash
git add docs/plans/2026-04-07-throughput-sweep-quality-gate.md scripts/check_fasim_throughput_sweep.sh scripts/benchmark_fasim_throughput_sweep.py README.md
git commit -m "Add quality-gated throughput sweep selection"
```

### Risks and Notes

- Sample smoke inputs may not differentiate quality across `extend_threads`; the check should validate schema/behavior, not performance conclusions.
- `best_qualifying` can legitimately be null on strict gates; the report must encode that explicitly instead of throwing away the sweep.
- Keep the throughput lane explicit and isolated from LongTarget default semantics.
