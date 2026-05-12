# Fast Safe-Store Materialization Characterization

This note records the default-off host-only fast materialization opt-in after
GPU-pruned safe-store precombine. It does not add a GPU path and does not use
packed kept-state D2H. CPU upload, locate, region, and output authority remain
unchanged.

## Path

The opt-in is enabled with:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE_FAST_MATERIALIZE=1
```

It keeps the existing GPU-resident summary reuse, GPU unique-start precombine,
GPU prune, and unpacked kept-state D2H. The only changed stage is host apply:

```text
D2H kept states
-> reserve host vector/index capacity
-> materialize states in order
-> build startCoord -> index map in the same pass
-> existing upload/locate/region handoff
```

Validation is available with:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE_FAST_MATERIALIZE_VALIDATE=1
```

Validation builds a side store with the previous materializer, compares size,
candidate content, order, and digest, and falls back to the previous
materialized store on mismatch.

## 3-Run Median

All runs used the CUDA sample region/locate exactness command with oracle diff.

| Mode | rebuild s | initial scan s | sim s | total s | D2H bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| GPU prune unpacked | 0.847133 | 6.34827 | 10.9127 | 12.9475 | 119203236 |
| GPU prune packed real | 0.828612 | 6.77546 | 10.9358 | 12.9664 | 66224020 |
| GPU prune fast materialize | 0.767155 | 6.65039 | 11.0342 | 13.2152 | 119203236 |
| GPU prune fast materialize + validate | 1.96002 | 7.92632 | 12.2115 | 14.2477 | 119203236 |

## Host Apply

| Mode | fast materialize s | fast index build s | fast validate s | mismatches | fallbacks |
| --- | ---: | ---: | ---: | ---: | ---: |
| GPU prune fast materialize | 0.295655 | 0.293684 | 0 | 0 | 0 |
| GPU prune fast materialize + validate | 0.293362 | 0.291744 | 1.15743 | 0 | 0 |

The opt-in reduces the host materialization/index portion and remains
exact-clean. It does not show a 3-run median `total_seconds` win over the
existing GPU prune path, so it should remain default-off. The useful next signal
is that index construction is now the dominant host apply cost and should be
handled before revisiting packed D2H or frontier replay performance.
