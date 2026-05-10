# CUDA Exact Frontier One-Chunk Tiny GPU Shadow

This PR adds a test-only CUDA fixture for one-chunk exact frontier shadow. It
does not connect to production initial replay, benchmark telemetry, locate,
region, planner authority, or safe-store upload.

The fixture replays 4 synthetic ordered summaries on one CUDA thread, returns
GPU-produced candidate states plus `runningMin`, maps them into
`SimInitialExactFrontierOneChunkSnapshot`, and feeds the result to the existing
final comparator.

Covered: insertion, same-start replacement/update, min-candidate / `runningMin`,
first-max/tie availability as a contract flag, and candidate digest/value
comparison.

Not covered: production summary shape or scale, production dispatch, safe-store
digest or host epoch comparison, chunk-boundary snapshots, or runtime mismatch
telemetry. This does not prove production replay exactness.

Production remains unchanged: the clean gate stays inactive,
`one_chunk_compare_calls` stays `0`, replay backend support stays `0`, and no
`gpu_real` or `ordered_segmented_v3` route is added. Next step: define a
production one-chunk snapshot input adapter before wiring any production backend.
