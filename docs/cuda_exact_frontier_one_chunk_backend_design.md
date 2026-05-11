# CUDA Exact Frontier One-Chunk Backend Design

This milestone designs the move from bounded diagnostic one-chunk shadows to a production-shaped shadow backend. It is docs-only: it does not run full 44.8M all-request replay, activate the clean gate, change production authority, or route through `gpu_real` / `ordered_segmented_v3`.

## Current Evidence

The one-chunk exact frontier path has progressed through several bounded stages:

- Tiny CUDA fixture replay passed and exercised the GPU replay helper against a small comparator target.
- The production input adapter passed and proved production-shaped ordered summaries can be materialized for the one-chunk path.
- Bounded prefix replay passed, including all-request prefixes up to 65,536 summaries per request/window.
- Selected request deep-prefix replay passed up to 1,048,576 summaries.
- Selected full-request replay passed for requests 47, 24, and 0.
- All 48 individual full-request replays passed with `processed == input`, `truncated=0`, `cap_clamped=0`, and mismatch total 0.

The clean gate remains inactive: `active=0`, `supported=0`, `authority=cpu`, global `one_chunk_replay_backend_supported=0`, and production `one_chunk_compare_calls=0`.

| item | value |
|---|---:|
| total requests | 48 |
| total summaries | 44,777,038 |
| total estimated H2D | 1,432,865,216 bytes |
| largest request | 0 |
| largest request summaries | 1,720,991 |
| largest request H2D | 55,071,712 bytes |
| individual full-request mismatches | 0 / 48 |
| clean gate active | 0 |
| global backend supported | 0 |

## Scope Distinction

Individual full-request replay replays one request/window from an empty bounded-shadow state and compares that request-local GPU snapshot with the CPU reference built from the same request-local stream. It has now covered every sample summary across 48 independent runs, but it does not prove one continuous 44.8M stream.

Full all-request one-chunk replay would consume the complete ordered summary stream as one replay job. To match production semantics, it must preserve request-boundary state resets and budget for about 1.43 GB of input H2D before temporary storage.

Chunk-boundary replay is a streaming design where the CPU and GPU compare compatible snapshots at explicit boundaries. True tail/middle intermediate-state replay requires these snapshots because the candidate set, floor/runningMin, first-max/tie state, and safe-store state depend on earlier summaries.

Production authoritative replay is out of scope. CPU replay remains authoritative until a separate decision changes authority, and this design does not propose that change.

## Authority Model

CPU replay remains the only authority for output, safe-store, locate, region, and planner decisions. A future GPU backend is shadow-only and may only feed comparator telemetry.

The clean gate may become active only after a real GPU shadow backend exists and produces snapshots that satisfy the output contract below. Until then, `supported=0` and `active=0` are correct. The `gpu_real` authority remains forbidden. `ordered_segmented_v3` remains an unrelated experimental reduce path and must not satisfy the exact frontier clean gate.

Runtime `one_chunk_compare_calls` must increment only for real CPU-vs-GPU shadow comparisons. CPU-vs-CPU or bounded diagnostic comparisons must not be reported as production one-chunk compare calls.

## Replay State Model

There are three viable state models:

1. Independent per-request replay resets replay state at each request/window.
2. Continuous all-request replay carries state across the full ordered stream.
3. Batched per-request replay groups multiple request/windows per launch but still emits separate request-local snapshots.

Code audit result: request/window boundaries are semantic reset points for the initial exact frontier replay state used by the production CPU path. The non-window path creates a fresh `SimKernelContext`, initializes it, runs the initial scan, and then runs the candidate loop for that request. The window-pipeline batch path creates one `SimKernelContext` per batch entry and applies each request's initial summaries into its matching context. Batch boundaries are scheduling boundaries, but request/window contexts are independent replay states.

The audited reset evidence is:

- `SimKernelContext` construction starts with `runningMin=0`, `candidateCount=0`, and empty safe-store state.
- `initializeSimKernel` resets `runningMin`, candidate count, proposal loop state, safe-store validity, candidate start index, and candidate heap.
- `enumerateInitialSimCandidates` clears candidate count, invalidates the safe-store, clears candidate start index, and invalidates the heap before initial scan enumeration.
- `finalizeSimCudaInitialRunSummariesToContext` and `applySimCudaInitialRunSummariesToContext` operate on the request's current `SimKernelContext`; safe-store rebuild/prune is per context.
- The window-pipeline batch path stores contexts in `preparedBatch.contexts[batchOffset]`, applies each result's `initialRunSummaries` into the corresponding context, and later runs `runSimCandidateLoop` with that same context.

Therefore, candidate/floor/runningMin state and safe-store state do not carry across production request/windows. A continuous all-request replay that simply concatenates 48 streams and carries state across boundaries would not match production semantics. A true all-request backend would need explicit request-boundary resets and per-request snapshots, or it should remain a diagnostic stream experiment.

In this design, "one-chunk" for a per-request backend means one complete request/window replay unit. An all-request implementation can still be one GPU submission, but semantically it must preserve 48 reset boundaries rather than treating the sample as one process-global candidate stream.

## Input Strategy

Current sample data makes the cost visible:

- Total summaries: 44,777,038.
- Estimated continuous input H2D: 1,432,865,216 bytes.
- Largest request input H2D: 55,071,712 bytes.
- Every individual request already fits under the selected full-request cap.

A single huge H2D is conceptually simple but moves about 1.43 GB at once and makes failure localization poor. Per-request H2D is bounded by the largest request and aligns with the validated coverage. Batched multi-request H2D can reduce launch overhead but should preserve per-request snapshot boundaries. Streaming H2D is the scalable end-state, but it requires chunk-boundary/intermediate-state contracts that are not ready yet.

## GPU Memory Budget

The input buffer alone is about 1.43 GB for full all-request replay versus about 55 MB for the largest request. Temporary storage must also cover output candidate states, candidate container scratch, digest reduction scratch, and any safe-store/digest state.

The output snapshot should be small relative to input, but worst-case candidate high-water entries can make snapshot construction non-trivial. Safe-store digest/epoch coverage may require additional state or host-compatible digest material. These requirements make 44.8M all-at-once review riskier than per-request shadow even before runtime is considered.

Per-request replay keeps memory bounded by the largest request/window and gives a natural upper bound for first production shadow work. Full all-request replay should wait until the backend has a batching and snapshot budget, plus a policy for preserving request reset boundaries.

## Output Snapshot Contract

A production shadow backend must produce a GPU snapshot that can be compared with the CPU baseline. The snapshot contract includes:

- Ordered candidate digest.
- Unordered candidate digest.
- Candidate count.
- Candidate values.
- Min-candidate / runningMin.
- First-max / tie availability and values.
- Safe-store digest.
- Host safe-store epoch compatibility, or an explicit unavailable reason.
- Per-request snapshot identity if the backend uses per-request replay.

Safe-store digest and epoch must be honest. If unavailable, the backend must report that limitation instead of implying clean gate support.

## Comparison Plan

The final comparator already exists and has compared GPU-produced bounded snapshots successfully. Individual request full snapshots compare cleanly across all 48 request/windows.

A future production shadow backend should call the comparator only when a real GPU shadow snapshot exists. Runtime `one_chunk_compare_calls` should count these real comparisons. Mismatch counters must correspond to actual CPU-vs-GPU fields and must not be recycled from bounded diagnostic counters. CPU-vs-CPU fake comparisons are forbidden.

## Gate Activation Criteria

The clean gate can become active only when all of the following are true:

- `backend_supported=1` for a real one-chunk shadow backend.
- A real GPU shadow snapshot exists.
- The final comparator is called.
- Mismatch counters are meaningful CPU-vs-GPU counters.
- `authority=cpu` remains true.
- No `gpu_real` authority path is used.
- Safe-store digest/epoch contract is represented honestly.
- Request-boundary semantics are either production-equivalent or explicitly outside the gate.

Until these criteria are met, clean gate `active=0` remains the correct state.

## Initial Implementation Options

### Option A: Per-Request Shadow Backend

Pros:

- All 48 requests already validate individually with mismatch total 0.
- Memory is bounded by the largest observed request, about 55 MB H2D.
- Failures localize to a request index.
- It avoids immediate 1.43 GB input movement.
- It matches the audited production reset boundary for initial exact frontier replay.

Cons:

- It is not a single continuous 44.8M replay.
- It still needs real production shadow telemetry and safe-store digest/epoch coverage before clean gate support.

### Option B: Full All-Request One-Chunk Backend

Pros:

- It matches the simplest interpretation of one continuous one-chunk stream.

Cons:

- It requires about 1.43 GB input H2D before temporary storage.
- It has larger memory and runtime risk.
- Failure localization is harder.
- Review risk is higher because boundary reset and safe-store contracts must be solved together.

### Option C: Streaming All-Request Backend

Pros:

- It is closest to a scalable future backend.
- It can bound memory while preserving continuous stream semantics.

Cons:

- It requires chunk-boundary/intermediate-state contracts first.
- It is not ready while safe-store digest/epoch and boundary snapshot contracts are incomplete.

## Recommended Next Implementation

Prefer a default-off per-request production shadow backend first. It should process one selected request or all requests individually, produce real GPU snapshots, call the final comparator, increment production shadow compare calls, and keep CPU authority.

This is not a recommendation to activate the clean gate immediately. The first implementation should remain default-off and shadow-only while it adds real GPU snapshots, real comparator calls, and honest safe-store digest/epoch status.

Full 44.8M all-request replay is not the next step because a naive continuous carry-state stream would not match the audited production request reset semantics, and a correct all-request submission still needs boundary reset markers, per-request snapshot aggregation, and a memory policy. The next implementation should turn the already validated per-request evidence into a real default-off shadow backend with honest telemetry, not move directly to a 1.43 GB continuous replay.

## Non-Goals

- No production authority change.
- No default full replay.
- No `ordered_segmented_v3` route.
- No `gpu_real` authority.
- No hierarchical top-K.
- No unordered reduce.
- No DP/D2H overlap.
- No Layer 3 transducer.
