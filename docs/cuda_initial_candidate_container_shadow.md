# CUDA initial candidate container shadow

Date: 2026-05-09

Base: `cuda-initial-candidate-churn-telemetry`

This pass adds default-off, estimator-only diagnostics:

```text
LONGTARGET_SIM_CUDA_INITIAL_CANDIDATE_CONTAINER_SHADOW=1
```

The authoritative initial candidate replay remains unchanged. The diagnostic
does not add a real lazy/tombstone path, skip candidate summaries, change replay
order, change floor / `runningMin` / first-max / tie behavior, or feed output,
safe-store, locate, region, or upload work.

## Results

| Field | benchmark | sample |
| --- | ---: | ---: |
| `candidate_apply_seconds` | 0.204088 | 1.87687 |
| `events` | 4,691,334 | 44,777,038 |
| `replacements/erasures` | 3,889,333 | 40,318,731 |
| `overwritten_ratio` | 0.932373 | 0.984946 |
| `index_rebuilds` | 16,168 | 384,448 |
| `shadow_seconds` | 0.000113613 | 0.000113259 |
| `state_mismatches` | 0 | 0 |
| `floor_mismatches` | 0 | 0 |
| `digest_mismatches` | 0 | 0 |
| `order_mismatches` | 0 | 0 |
| `active_candidates` | 3,450 | 2,400 |
| `stale_entries` | 4,609,673 | 44,392,627 |
| `lazy_pops` | 3,889,333 | 40,318,731 |
| `est_saved_erasures` | 3,889,333 | 40,318,731 |
| `est_saved_index_rebuilds` | 16,168 | 384,448 |
| `high_water_entries` | 4,613,123 | 44,395,027 |

## Interpretation

The estimator shows large theoretical saved erase/index-rebuild work, but also
large stale growth: sample stale entries reach `44,392,627` for `2,400` active
candidates. The zero mismatch counters are final authoritative-container
self-checks only; they do not prove lazy-container equivalence at intermediate
floor/min query points.

Next step should be a full lazy/versioned container shadow only if intermediate
floor/min validation can remain local and reviewable. This estimator alone does
not justify a real candidate container path.
