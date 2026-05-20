# Fasim fastSIM Align Precompute Independence

This report characterizes whether `aligner.Align` requests inside `fastSIM_extend_from_scoreinfo` can be generated from scoreInfo before the serial emit loop observes any Align result. It is shadow-only: the serial fastSIM emit path remains authority and shadow output is never used for runtime output.

Boundary: no real precompute, no default enablement, no output change, no scoring/threshold/non-overlap change, and no GPU AUTO, SSW/AVX2/ProfileContext, SIM-close, or recovery behavior change.

Workload: `hg38_chr21_softmask_compact_region`. Each mode uses 1 run(s); tables report medians.

## Modes

| Mode | Environment |
| --- | --- |
| table_only | `FASIM_TRANSFERSTRING_TABLE=1` |
| final_stack | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1` |
| precompute_independence | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1 FASIM_FASTSIM_ALIGN_PRECOMPUTE_INDEPENDENCE=1` |

## Runtime Summary

| Table-only seconds | Final stack seconds | Independence shadow seconds | Final stack speedup | Records | Digest | Final digest match | Shadow digest match |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.042892 | 0.295161 | 0.319093 | 0.15x | 0 | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | yes | yes |

## Request Generation

| Legacy requests | ScoreInfo-derived requests | Count delta | Order mismatches | Field mismatches | State-dependent / extra requests |
| --- | --- | --- | --- | --- | --- |
| 232 | 532 | 300 | 5 | 0 | 300 |

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
| 0.018589 | 0.008781 | 0.000130 | 0.004520 | 0.002325 | 0.001228 | 0.000679 | 15,847,638 |

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
