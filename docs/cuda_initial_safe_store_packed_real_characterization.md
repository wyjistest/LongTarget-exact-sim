# Packed Kept-State Materialization Characterization

This note records a 3-run sample A/B for the default-off packed kept-state real
path. It does not recommend making packed D2H default. The path remains opt-in,
CPU-authoritative after host materialization, and separate from candidate/frontier
replay and the exact-frontier clean gate.

## Modes

All runs used the CUDA sample region/locate exactness command with oracle diff.

| Mode | Extra environment |
| --- | --- |
| legacy | none |
| resident precombine | `LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1`, `LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1` |
| resident precombine + prune | resident precombine plus `LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1` |
| packed real | resident precombine + prune plus `LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE_PACKED_D2H_REAL=1` |
| packed real + validate | packed real plus `LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE_PACKED_D2H_VALIDATE=1` |

## 3-Run Median

| Mode | rebuild s | initial scan s | sim s | total s | prune D2H bytes | packed D2H bytes | elided unpacked bytes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| legacy | 3.19556 | 8.87031 | 13.6016 | 15.8249 | 0 | 0 | 0 |
| resident precombine | 2.37773 | 7.85234 | 12.8142 | 14.8997 | 0 | 0 | 0 |
| resident precombine + prune | 0.996799 | 6.55499 | 10.9051 | 12.9552 | 119203236 | 0 | 0 |
| packed real | 0.979591 | 6.87525 | 11.4086 | 13.4649 | 66224020 | 66224020 | 119203236 |
| packed real + validate | 1.14291 | 6.96845 | 11.5241 | 13.5661 | 66224020 | 66224020 | 119203236 |

## Host Breakdown

| Mode | pack s | unpack s | packed materialize s | packed index rebuild s | packed host apply s | upload/sync s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| resident precombine + prune | 0 | 0 | 0 | 0 | 0 | 0.0249786 |
| packed real | 0.000376896 | 0.0283469 | 0.444769 | 0.418059 | 0.473116 | 0.0191805 |
| packed real + validate | 0.000389664 | 0.0298777 | 0.421651 | 0.396317 | 0.450552 | 0.0188685 |

`packed_host_apply_seconds` is `packed_unpack_seconds` plus
`packed_materialize_seconds`. The index rebuild slice dominates the packed host
apply cost in this sample; unpack is small and pack is negligible.

## Interpretation

Packed real is exact-clean in these runs:

```text
packed_fallbacks = 0
packed size/candidate/order/digest mismatches = 0
```

It also cuts kept-state transfer from `119203236` bytes to `66224020` bytes.
However, the 3-run median does not show a stable wall-clock win over resident
precombine + GPU prune:

```text
resident precombine + prune total median = 12.9552s
packed real total median                 = 13.4649s
packed real + validate total median      = 13.5661s
```

The next optimization target should be host materialization/index rebuild cost,
not another packed-byte change or default activation. Packed real should remain
default-off until a later path reduces the host apply cost or shows stable
multi-run `sim_seconds` and `total_seconds` improvement.
