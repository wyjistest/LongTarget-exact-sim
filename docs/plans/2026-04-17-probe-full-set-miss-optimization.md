# Probe Full-Set Miss Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce `probeSimCandidateIndexSlot()` cost on steady-state `candidate_set_full` misses by reusing the current eviction victim's index slot when the probe chain permits it, without changing host-merge semantics.

**Architecture:** Keep the existing candidate index and heap structures. Add a narrow probe helper that can treat one occupied slot as a reusable tombstone candidate during a miss lookup, then wire `ensureSimCandidateIndexForRun()` to use that helper only when `candidateCount == K` and `candidateMinHeap.valid` is already true. Lock the behavior with a small unit test instead of adding more telemetry.

**Tech Stack:** C++11, existing `sim.h` inline helpers, repo-local test binaries built from `Makefile`.

### Task 1: Add a failing probe-slot reuse test

**Files:**
- Create: `tests/test_sim_candidate_index_probe.cpp`
- Modify: `Makefile`

**Step 1: Write the failing test**

Add a small test that:
1. Builds a `SimKernelContext` with `candidateCount == K`.
2. Places three colliding candidates into one probe cluster and makes candidate `0` the current heap minimum.
3. Calls `ensureSimCandidateIndexForRun()` with a new key hashing into the same cluster.
4. Expects the new key to reuse candidate `0`'s original index slot and keep `tombstoneCount == 0`.

The pre-change code should fail because it inserts at the later empty slot and leaves one tombstone behind.

**Step 2: Run test to verify it fails**

Run: `make -C .worktrees/feat-initial-store-telemetry-split tests/test_sim_candidate_index_probe && .worktrees/feat-initial-store-telemetry-split/tests/test_sim_candidate_index_probe`

Expected: FAIL on reused-slot / tombstone assertion.

### Task 2: Implement the minimal reusable-slot probe path

**Files:**
- Modify: `sim.h`

**Step 3: Write minimal implementation**

Implement a helper that probes like the current linear scan, but can treat one occupied slot as a reusable insertion candidate while still searching to the true end of the probe chain. Then change `ensureSimCandidateIndexForRun()` so that:
1. When `candidateCount < K`, behavior is unchanged.
2. When `candidateCount == K` and `candidateMinHeap.valid` is true, it peeks the current victim once, derives the victim's index slot, and uses the reusable-slot probe helper.
3. On miss, it reuses the cached victim candidate index instead of peeking the heap again.

Do not change public telemetry shape or unrelated heap/update paths.

**Step 4: Run test to verify it passes**

Run: `make -C .worktrees/feat-initial-store-telemetry-split tests/test_sim_candidate_index_probe && .worktrees/feat-initial-store-telemetry-split/tests/test_sim_candidate_index_probe`

Expected: PASS.

### Task 3: Verify no host-merge regression

**Files:**
- Reuse existing tests and isolated harness only

**Step 5: Run focused regression checks**

Run:
- `make -C .worktrees/feat-initial-store-telemetry-split tests/test_sim_initial_host_merge_corpus tests/sim_initial_host_merge_context_apply_profile`
- `cd .worktrees/feat-initial-store-telemetry-split && tests/test_sim_initial_host_merge_corpus`
- `cd .worktrees/feat-initial-store-telemetry-split && tests/sim_initial_host_merge_context_apply_profile --corpus-dir .tmp/sim_initial_host_merge_real_census_cuda_2026-04-16_16-47-25/coverage_weighted_16_real/corpus --case case-00000417 --verify`

Expected:
- regression tests stay green
- isolated replay still reports `verify_ok=1`

### Task 4: Measure the first optimization cut

**Files:**
- Reuse existing isolated harness outputs under `.tmp/`

**Step 6: Run a small profiler/benchmark spot-check**

Run the isolated harness on `case-00000417` and the existing heavy cases, compare:
- `context_apply_lookup_miss_candidate_set_full_probe_seconds`
- gprof flat ranking for `probeSimCandidateIndexSlot()`

Only continue deeper on probe if `probe` still leads and the cut shows real improvement.

### Task 5: Commit the isolated optimization cut

**Files:**
- Commit only the new test, `Makefile`, and the narrow `sim.h` changes

**Step 7: Commit**

```bash
git -C .worktrees/feat-initial-store-telemetry-split add Makefile sim.h tests/test_sim_candidate_index_probe.cpp docs/plans/2026-04-17-probe-full-set-miss-optimization.md
git -C .worktrees/feat-initial-store-telemetry-split commit -m "Optimize probe full-set miss slot reuse"
```

### Risks and Notes

- The reusable-slot probe must still return `found` if the victim slot already stores the requested key.
- Do not normalize or rewrite unrelated lines in `sim.h`.
- Keep the first cut narrow: no heap algorithm rewrite, no telemetry additions, no selector/runtime workflow changes.

### References

- `sim.h:7810`
- `sim.h:8410`
- `tests/test_sim_initial_host_merge_corpus.cpp:539`
- `tests/sim_initial_host_merge_context_apply_profile.cpp:175`
