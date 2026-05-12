# Initial Safe-Store GPU Best-Path A/B

This note consolidates the current best default-off initial safe-store GPU path:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
```

Packed kept-state D2H and fast materialize are intentionally off for this path.
The path is still opt-in. It does not change candidate/frontier replay, CPU
upload/locate/region authority, clean-gate status, `gpu_real`,
`ordered_segmented_v3`, or `EXACT_FRONTIER_REPLAY`.

## 3-Run Median

All runs used the CUDA sample region/locate exactness command with oracle diff.

| Mode | total s | sim s | initial scan s | rebuild s | update s | prune s | GPU precombine s | D2H bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| legacy | 15.8349 | 13.7844 | 9.02808 | 3.19147 | 2.44365 | 0.751932 | 0 | 0 |
| resident GPU precombine | 14.7726 | 12.7549 | 7.95158 | 2.30742 | 1.57355 | 0.708097 | 0.351394 | 317919276 |
| resident GPU precombine + GPU prune | 12.6598 | 10.6354 | 6.27427 | 0.699733 | 0.699733 | 0 | 0.316527 | 119203236 |
| resident GPU precombine + GPU prune + packed real | 13.1878 | 11.1486 | 6.85908 | 1.02084 | 1.02084 | 0 | 0.62634 | 66224020 |
| resident GPU precombine + GPU prune + fast materialize | 12.9951 | 10.869 | 6.56624 | 0.692826 | 0.692826 | 0 | 0.406964 | 119203236 |

## Decision

The current best path is resident GPU precombine + GPU prune with unpacked
kept-state D2H. Relative to legacy median, it improves:

```text
total_seconds:              -3.1751s
sim_seconds:                -3.1490s
sim_initial_scan_seconds:   -2.75381s
initial_store_rebuild:      -2.491737s
```

It also beats the packed-real and fast-materialize variants in this 3-run
sample median. Packed real saves D2H bytes, and fast materialize reduces a host
apply/index slice, but neither is the median wall-clock winner here.

Recommended current opt-in:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
```

Do not default it yet. Keep packed real and fast materialize as diagnostic or
specialized opt-ins until a separate A/B shows a stable wall-clock win.

## Exactness And Guards

Across the 15 sample A/B runs:

```text
size/candidate/order/digest mismatches = 0
fallbacks = 0
```

The best-path target also asserts that packed D2H and fast materialize remain
off:

```bash
make check-sim-initial-safe-store-gpu-best-path
```
