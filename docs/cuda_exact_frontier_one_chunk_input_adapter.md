# CUDA Exact Frontier One-Chunk Input Adapter

This PR adds a default-off dry-run adapter for the production one-chunk exact
frontier shadow input. It inspects the host `vector<SimScanCudaInitialRunSummary>`
already materialized by the default summary-handoff path.

Inventory:

| Concept | Existing source/helper | Action |
| --- | --- | --- |
| production ordered summary stream | `SimScanCudaInitialRunSummary` vector | dry-run telemetry |
| summary count | `summaries.size()` | report |
| summary bytes | `sizeof(SimScanCudaInitialRunSummary)` | report |
| stable order key | vector order from row-run compaction | report ordered |
| start key | `startCoord` | covered |
| score field | `score` | covered |
| end position field | `endI`, `scoreEndJ` | covered |
| bounds | `minEndJ`, `maxEndJ` | covered |
| first-max/tie fields | `scoreEndJ` plus ordered same-start replay | covered as input |
| safe-store update fields | not part of the input stream | missing |
| input digest helper | ordered summary digest | added |
| unsupported records | none detected locally | report count |
| one-chunk backend connection | missing | unchanged |

The adapter is not replay. It does not feed a GPU kernel, call the final
comparator, emit mismatch counters, or affect locate/region/planner authority.
The clean gate remains inactive, production `compare_calls` remains `0`, and
production replay backend support remains `0`.

Before a production replay backend, the next PR still needs a backend that
consumes this ordered summary stream and produces a non-authoritative shadow
snapshot with candidate, min-candidate, first-max/tie, safe-store digest, and
host-epoch fields.
