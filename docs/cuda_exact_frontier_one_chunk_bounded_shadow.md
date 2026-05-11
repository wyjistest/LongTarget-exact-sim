# CUDA Exact Frontier One-Chunk Bounded Shadow

This PR adds a default-off bounded prefix shadow for production-shaped `SimScanCudaInitialRunSummary` input. It is a diagnostic, not production replay.

It consumes the already materialized ordered production summaries, processes only the first `MAX_SUMMARIES` per request/window (hard-capped at 65536), builds a GPU candidate/`runningMin` snapshot, and compares it against a CPU prefix reference with the existing one-chunk final comparator.

Covered: ordered/unordered candidate digest, candidate values, min-candidate, and
the first-max/tie availability flag. Not covered: safe-store digest/epoch, chunk
boundaries, or full stream scale.

With `MAX_SUMMARIES=4096`, the sample smoke processes 196,608 prefix summaries across 48 calls while the full input has 44,777,038 summaries, so `truncated=1`.
The clean gate remains inactive, full one-chunk `compare_calls` remains `0`, and the GPU snapshot is never used for output, safe-store handoff, locate, region, or planner authority.
