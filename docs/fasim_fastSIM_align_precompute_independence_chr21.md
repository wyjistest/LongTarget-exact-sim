# Fasim fastSIM Align Precompute Independence

This report characterizes whether `aligner.Align` requests inside `fastSIM_extend_from_scoreinfo` can be generated from scoreInfo before the serial emit loop observes any Align result. It is shadow-only: the serial fastSIM emit path remains authority and shadow output is never used for runtime output.

Boundary: no real precompute, no default enablement, no output change, no scoring/threshold/non-overlap change, and no GPU AUTO, SSW/AVX2/ProfileContext, SIM-close, or recovery behavior change.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Modes

| Mode | Environment |
| --- | --- |
| table_only | `FASIM_TRANSFERSTRING_TABLE=1` |
| final_stack | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1` |
| precompute_independence | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1 FASIM_FASTSIM_ALIGN_PRECOMPUTE_INDEPENDENCE=1` |

## Runtime Summary

| Table-only seconds | Final stack seconds | Independence shadow seconds | Final stack speedup | Records | Digest | Final digest match | Shadow digest match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 131.349000 | 28.547500 | 54.211500 | 4.60x | 6546 | `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26` | yes | yes |

## Request Generation

| Legacy requests | ScoreInfo-derived requests | Count delta | Order mismatches | Field mismatches | State-dependent / extra requests |
| --- | --- | --- | --- | --- | --- |
| 979,282 | 2,402,668 | 1,423,386 | 31,583 | 0 | 1,423,386 |

A non-zero state-dependent count means the scoreInfo-derived upfront sequence would perform Align calls that legacy serial emit skips after observing earlier Align results.

## Full Replay Correctness

| Field | Mismatches | Notes |
| --- | --- | --- |
| candidate state | 0 | Compares ordered replay against legacy candidate state. |
| emitted record | 0 | Compares reconstructed candidate records before final output filtering. |
| CIGAR | 0 | Compares side rerun CIGAR against legacy `aligner.Align` CIGAR. |
| digest | 0 | Runtime digest is unchanged because shadow output is not used. |
| fallbacks | 0 | No real-path fallback exists in this PR. |

## Timing And Memory

| Legacy emit | Side compute | Side replay | Est 2-thread | Est 4-thread | Est 8-thread | Est 16-thread | Memory bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 49.136800 | 23.157000 | 0.483351 | 12.061900 | 6.272610 | 3.377980 | 1.930670 | 65,785,361,249 |

## Decision

Full replay is clean for the legacy request sequence, but scoreInfo-derived upfront request generation differs from legacy. Do not build a real upfront precompute path from this result; consider a smaller buffered or pipeline design only after decomposing the state dependency.

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
