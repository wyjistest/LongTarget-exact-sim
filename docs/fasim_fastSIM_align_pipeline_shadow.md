# Fasim fastSIM Align Pipeline Shadow

This report characterizes whether the legacy `aligner.Align` stream inside `fastSIM_extend_from_scoreinfo` contains post-hoc segments large enough for a future bounded buffered or pipelined precompute. It is shadow-only: serial fastSIM emit remains authority and shadow output is never used for runtime output. Segment length is measured from the observed legacy stream; it is not a real-path contract because early-break decisions are only known after prior Align results.

Boundary: no real precompute, no default enablement, no output change, no scoring/threshold/non-overlap change, and no GPU AUTO, SSW/AVX2/ProfileContext, SIM-close, or recovery behavior change.

Workload: `hg38_chr21_softmask_compact_region`. Each mode uses 1 run(s); tables report medians.

## Modes

| Mode | Environment |
| --- | --- |
| table_only | `FASIM_TRANSFERSTRING_TABLE=1` |
| final_stack | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1` |
| pipeline_shadow | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1 FASIM_FASTSIM_ALIGN_PIPELINE_SHADOW=1` |

## Runtime Summary

| Table-only seconds | Final stack seconds | Pipeline shadow seconds | Final stack speedup | Records | Digest | Final digest match | Shadow digest match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.054880 | 0.208703 | 0.221387 | 0.26x | 0 | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | yes | yes |

## Segment Shape

| Legacy requests | Segments | Barriers | p50 | p90 | p99 | max | Avg requests/segment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 232 | 133 | 133 | 1 | 4 | 4 | 4 | 1.74 |

## Bounded Lookahead

| Segment length | Segments |
| --- | --- |
| 1 | 100 |
| 2 | 0 |
| 3 | 0 |
| 4 | 33 |
| 5+ | 0 |

| Lookahead | Requests in segments | Share of legacy requests |
| --- | --- | --- |
| 2 | 132 | 56.90% |
| 4 | 132 | 56.90% |
| 8 | 0 | 0.00% |
| 16 | 0 | 0.00% |

## Replay Correctness

| Field | Mismatches | Notes |
| --- | --- | --- |
| candidate state | 0 | Reuses legacy ordered replay comparison. |
| emitted record | 0 | Compares reconstructed candidate records before final output filtering. |
| CIGAR | 0 | Compares side rerun CIGAR against legacy `aligner.Align` CIGAR. |
| digest | 0 | Runtime digest is unchanged because shadow output is not used. |

## Timing Estimate

| Legacy emit | Align CPU seconds | Est 2-thread | Est 4-thread | Est 8-thread |
| --- | --- | --- | --- | --- |
| 0.017498 | 0.008577 | 0.004289 | 0.002144 | 0.001072 |

## Decision

The legacy stream has short post-hoc length-4 groups, but no large lookahead-8/16 opportunity on this workload. A naive lookahead-4 path would still need to avoid #121-style overcompute, because many candidates break after the first Align call. Do not build a real pipeline opt-in from this result.

## Boundaries

```text
real precompute added: no
uses shadow output for runtime output: no
replaces fastSIM emit: no
default enabled: no
scoring/threshold/non-overlap/output changed: no
GPU AUTO / SSW / AVX2 / ProfileContext changed: no
SIM-close / recovery changed: no
```
