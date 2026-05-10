# CUDA Exact Frontier One-Chunk Final Compare

This PR adds a comparator for two already materialized one-chunk final replay
snapshots. It is not a replay backend and does not run at benchmark time.

| Concept | Existing field/helper | Action |
| --- | --- | --- |
| CPU candidate digests | `contract_cpu_*_digest_available`, `digestSimCudaFrontierStatesForTransducerShadow` | Compare once a real shadow snapshot exists. |
| CPU min-candidate | `contract_cpu_min_candidate_available` | Represent in the snapshot. |
| CPU first-max/tie | `contract_cpu_first_max_tie_available` | Represent in the snapshot. |
| CPU safe-store digest/epoch | `contract_cpu_safe_store_*` | Represent availability plus value. |
| real shadow replay backend | missing | Keep `one_chunk_replay_backend_supported=0`. |
| clean gate active | `benchmark.sim_initial_exact_frontier_shadow_gate_active=0` | Keep false. |

Runtime telemetry reports:

```text
benchmark.sim_initial_exact_frontier_shadow_one_chunk_final_compare_supported=1
benchmark.sim_initial_exact_frontier_shadow_one_chunk_replay_backend_supported=0
benchmark.sim_initial_exact_frontier_shadow_one_chunk_compare_calls=0
```

`compare_calls` stays `0` because no real shadow replay source exists. The
synthetic unit test exercises the comparator with equal and mismatching
snapshots, but benchmark telemetry emits no mismatch counters.

Non-goals: no GPU replay kernel, no `ordered_segmented_v3` route, no `gpu_real`
authority, no CPU-vs-CPU runtime self-comparison, no fake mismatch counters, and
no replay or safe-store behavior changes.
