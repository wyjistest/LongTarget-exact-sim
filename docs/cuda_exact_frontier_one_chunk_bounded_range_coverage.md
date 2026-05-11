# CUDA Exact Frontier One-Chunk Bounded Range Coverage

This PR extends the default-off bounded shadow with deterministic range modes over already materialized `SimScanCudaInitialRunSummary` vectors. The clean gate remains inactive and CPU output authority is unchanged.

Implemented modes:
- `prefix`: true prefix replay from empty state for each request/window.
- `request`: true prefix replay for one zero-based request/window index.
- `tail`, `middle`, `offset`: standalone subrange replay from empty state.

Tail/middle/offset intentionally do not claim true production intermediate-state exactness because they do not receive the candidate set, running floor, or safe-store state produced by earlier summaries. They only exercise production-shaped records at later positions through GPU snapshot production and the final comparator.

Telemetry reports mode, selected request index, range start min/max, max range length, ranges tested, processed/input coverage ratio, truncation, H2D/D2H bytes, and bounded mismatch counters. Compared fields remain ordered/unordered candidate digest, candidate values, min-candidate, and first-max/tie availability; safe-store digest/epoch and chunk-boundary state remain uncovered.

With `MAX_SUMMARIES=4096`, sample prefix coverage is 196,608 / 44,777,038 summaries, about 0.439%, with `truncated=1`. This does not validate full one-chunk production replay.
