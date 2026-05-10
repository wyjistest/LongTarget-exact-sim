# CUDA exact frontier chunk-boundary contract gap-fill

Date: 2026-05-10

Base: `cuda-exact-frontier-firstmax-tie-contract-gapfill`

This is a docs-only stop report for chunk-boundary coverage in the future GPU
exact ordered frontier replay shadow contract. It does not implement GPU
replay, does not route through `ordered_segmented_v3`, does not report
`gpu_real` authority, and does not make the clean shadow gate active.

## Inventory

| Concept | Existing key/helper | Action |
| --- | --- | --- |
| CPU chunk boundary definition | `applySimCudaInitialRunSummariesChunkedHandoff` groups summaries by row chunks when `LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF=1` | Available only on opt-in chunked host handoff, not the default whole-summary replay baseline. |
| CPU chunk count | `benchmark.sim_initial_chunked_handoff_chunks_total`, `benchmark.sim_initial_handoff_cpu_pipeline_chunks_applied`, `benchmark.sim_initial_reduce_chunks_total` | Existing count telemetry; not a state snapshot or digest. |
| CPU chunk boundary state snapshot | none on the default CPU ordered replay | Missing; adding it would require hooks inside chunk apply/replay. |
| CPU chunk boundary candidate digest | none | Missing; final candidate digest exists, but no per-boundary digest is recorded. |
| CPU chunk boundary safe-store digest | none | Missing; final safe-store digest exists, but no per-boundary digest is recorded. |
| frontier transducer aggregate mismatch | `benchmark.sim_initial_frontier_transducer_shadow_mismatches` | Aggregate final mismatch only; insufficient for chunk-boundary contract. |
| ordered_segmented_v3 chunk stats | `benchmark.sim_initial_reduce_chunks_total`, `benchmark.sim_initial_reduce_chunks_replayed_total`, `benchmark.sim_initial_reduce_chunks_skipped_total` | Experimental reducer chunk accounting only; not clean gate coverage. |
| clean gate support flag | `sim_initial_exact_frontier_shadow_gate_supported=0` | Unchanged. |
| missing CPU-vs-shadow comparison | no contract-compliant chunk-boundary backend | Do not emit chunk-boundary mismatch counters. |

## Why no telemetry fields were added

The requested chunk-boundary fields need an actual boundary definition plus
state at that boundary. The current code has several related counters, but none
of them meet that contract:

- Chunked handoff can count chunks and summaries, but it does not record a CPU
  frontier or safe-store snapshot after each boundary.
- The pinned async CPU pipeline records chunks applied/finalized, but not a
  boundary candidate digest.
- The experimental reducer records replay chunk counts, but it is not the clean
  shadow gate and does not provide default-path CPU authority.
- The frontier transducer shadow reports final aggregate mismatch, not
  per-boundary mismatch.

Adding honest CPU chunk-boundary digest availability would require new hooks in
the ordered replay/chunk apply path. That is broader than this contract
gap-fill PR and risks changing or perturbing the order-sensitive replay loop.

## Gate state

The clean gate remains:

```text
active=0
supported=0
missing_contract_counters=1
```

No chunk-boundary support flags or mismatch counters are emitted here. In
particular, this PR does not add fake zero counters such as
`chunk_boundary_mismatches=0`.

## Remaining contract gaps

The contract now has CPU final-state baselines for candidate digest,
min-candidate, safe-store digest, and first-max/tie fields. The remaining gaps
are:

- safe-store epoch design or explicit CPU/GPU epoch contract,
- chunk-boundary state/digest capture design,
- an actual clean CPU-vs-shadow backend.

The next step should be a safe-store epoch design note or a minimal one-chunk
GPU replay shadow design/stub. A real chunk-boundary mismatch counter should
wait until the implementation can capture comparable CPU and shadow state at
the same boundary without changing replay authority.
