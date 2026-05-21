# Fasim Final Speed Stack chr11 Characterization

This docs-only report records a single-run larger-chromosome smoke for the
final Fasim speed stack after the exact-column extend batch opt-in. It adds no
code, no new environment variables, and no default enablement.

This is not a repeated median and does not claim whole-genome coverage. It is a
production-like direction check on `hg38_chr11_H19`, which is larger than the
`hg38_chr21_H19` milestone workload.

## Modes

| Mode | Environment |
| --- | --- |
| table-only | `FASIM_TRANSFERSTRING_TABLE=1` |
| final stack | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1` |
| final stack + exact-column batch | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1` |
| final stack + exact-column batch + validate | `FASIM_TRANSFERSTRING_TABLE=1 FASIM_GPU_DP_COLUMN_AUTO=1 FASIM_SSW_PROFILE_CACHE=1 FASIM_SSW_AVX2=1 FASIM_SSW_PROFILE_CONTEXT=1 FASIM_EXACT_COLUMN_EXTEND_BATCH=1 FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1` |

Workload: `hg38_chr11_H19`. Each mode uses 1 run.

## Summary

| Mode | Seconds | Speedup vs table-only | Speedup vs final stack | Records | Digest clean |
| --- | ---: | ---: | ---: | ---: | --- |
| table-only | 450.345000 | 1.00x | n/a | 20,607 | yes |
| final stack | 152.325000 | 2.96x | 1.00x | 20,607 | yes |
| final stack + exact-column batch | 87.665700 | 5.14x | 1.74x | 20,607 | yes |
| final stack + exact-column batch + validate | 152.923000 | 2.94x | 1.00x | 20,607 | yes |

The clean output digest for all four modes is:

```text
sha256:0ae481985f0a060873f983cb80c2fb2b75a1fc4ff153b4492868376bb31d7310
```

`FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE=1` is a correctness audit mode, not
the recommended performance mode. Its runtime returns near the non-batch final
stack because it reruns CPU exact-column work as the comparison authority.

## Batch Telemetry

| Mode | Requests | Cells | Max cells/request | Batch total | Pack | H2D | Kernel | D2H | Unpack | Apply | CPU fallback | Validate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| final stack + exact-column batch | 6,356 | 89,365,360,000 | 14,060,000 | 0.377979 | 0.006349 | 0.005203 | 0.325436 | 0.015973 | 0.075907 | 0.001644 | 0.000000 | 0.000000 |
| final stack + exact-column batch + validate | 6,356 | 89,365,360,000 | 14,060,000 | 0.378462 | 0.006449 | 0.005158 | 0.325328 | 0.016326 | 0.080569 | 0.001558 | 0.000000 | 65.072400 |

The batch path does not show transfer or fallback pressure on this larger
chromosome workload. The remaining runtime is outside the exact-column batch
kernel and should be decomposed before any further optimization work.

## Correctness

| Mode | Score mismatches | Endpoint mismatches | ScoreInfo mismatches | Digest mismatches | Batch fallbacks | GPU fallbacks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| table-only | 0 | 0 | 0 | 0 | 0 | 0 |
| final stack | 0 | 0 | 0 | 0 | 0 | 0 |
| final stack + exact-column batch | 0 | 0 | 0 | 0 | 0 | 0 |
| final stack + exact-column batch + validate | 0 | 0 | 0 | 0 | 0 | 0 |

## Decision

This chr11 single-run characterization supports the large-workload opt-in stack:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
FASIM_EXACT_COLUMN_EXTEND_BATCH=1
```

Optional add-ons remain:

```bash
FASIM_SSW_AVX2=1
FASIM_SSW_PROFILE_CONTEXT=1
```

The result is a strong external confirmation beyond chr21, but it remains
single-run evidence. For formal production characterization, run 3-run medians
or a multi-RNA workload matrix.

## Boundaries

```text
optimization logic added: no
default enablement: no
new environment variable: no
scoring/threshold/non-overlap change: no
output semantic change: no
GPU AUTO policy change: no
SSW/AVX2/ProfileContext change: no
SIM-close/recovery change: no
validation relaxation: no
whole-genome claim: no
```

## Next Performance Step

Do not add another optimization directly from this result. If performance work
continues, first run a post-batch decomposition on chr11 and chr21 to identify
the largest remaining component inside the batch-enabled stack.
