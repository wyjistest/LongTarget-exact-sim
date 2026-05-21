# Fasim fastSIM Align Precompute Shadow

This report characterizes a default-off `fastSIM_extend_from_scoreinfo` aligner precompute shadow. The serial fastSIM emit path remains the runtime authority; the shadow collects bounded `aligner.Align` requests, reruns them in a side path, replays candidate decisions in legacy order, and compares diagnostic state. It does not feed shadow output into final Fasim output.

Boundary: no default enablement, no output change, no scoring/threshold/non-overlap change, and no GPU AUTO, SSW/AVX2/ProfileContext, SIM-close, or recovery behavior change.

Workload: `hg38_chr21_softmask_compact_region`. Each mode uses 1 run(s); tables report medians. Shadow cap: `10000` requests, stride `1`.

## Modes

| Mode | Environment |
| --- | --- |
| table_only | `FASIM_TRANSFERSTRING_TABLE=1` |
| final_stack | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1` |
| precompute_shadow | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS=1 FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1 FASIM_FASTSIM_ALIGN_PRECOMPUTE_SHADOW=1 FASIM_FASTSIM_ALIGN_PRECOMPUTE_SHADOW_MAX_REQUESTS=10000 FASIM_FASTSIM_ALIGN_PRECOMPUTE_SHADOW_REQUEST_STRIDE=1` |

## Runtime Summary

| Table-only seconds | Final stack seconds | Precompute shadow seconds | Final stack speedup | Shadow speedup | Records | Digest | Final digest match | Shadow digest match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.055880 | 0.354583 | 0.367659 | 0.16x | 0.15x | 0 | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | yes | yes |

## Request Independence

| Requests | Independent | State-dependent / unsampled | Notes |
| --- | --- | --- | --- |
| 232 | 232 | 0 | Independent means every align call for that candidate was sampled and replayed. |

## Correctness

| Field | Mismatches | First mismatch | Notes |
| --- | --- | --- | --- |
| candidate state | 0 | n/a | Compares replayed myflag, score, endpoints, cutlength, and selected call for sampled candidates. |
| emitted record | 0 | n/a | Compares candidate triplex records reconstructed by side replay before global final output filtering. |
| CIGAR | 0 | n/a | Compares side rerun CIGAR against legacy aligner.Align CIGAR for sampled requests. |
| digest | 0 | n/a | Runtime digest is unchanged because shadow output is not used for final output. |
| fallbacks | 0 | n/a | No real-path fallback exists in this PR; CPU serial emit remains authority. |

## Timing

| Legacy emit | CPU reference sample | Side compute | Side replay | Estimated 2-thread | Estimated 4-thread | Estimated 8-thread |
| --- | --- | --- | --- | --- | --- | --- |
| 0.033228 | 0.016269 | 0.016126 | 0.000240 | 0.008303 | 0.004272 | 0.002256 |

## Decision

The sampled shadow is clean. This is evidence that aligner requests can be collected and replayed diagnostically for the sampled workload; it is not a real runtime precompute path yet.

Next PR, if pursued, should broaden sampled workload coverage before any real opt-in.

The check target also runs a tiny emitted-record smoke (`testDNA.fa` + `H19.fa`) so the side replay compares reconstructed candidate records in addition to this compact no-record fixture.

## Boundaries

```text
uses shadow output for runtime output: no
replaces fastSIM emit: no
default enabled: no
scoring/threshold/non-overlap/output changed: no
GPU AUTO / SSW / SIM-close / recovery changed: no
```
