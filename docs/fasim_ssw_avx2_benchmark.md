# Fasim SSW AVX2 Benchmark

This report compares the default SSE2 SSW path with an opt-in AVX2 SSW path for `sw_sse2_byte/word` equivalents. It keeps the current Fasim speed stack enabled and only switches the SSW runtime path when `FASIM_SSW_AVX2=1` is set.

Each workload uses 3 run(s); tables report medians.

| Workload | Records | SSE2 total s | AVX2-compiled total s | AVX2 runtime total s | Runtime vs SSE2 | SSE2 SSW align s | AVX2 SSW align s | SSW align speedup | Digest clean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 6 | 0.255482 | 0.250062 | 0.252489 | 1.01x | 0.003836 | 0.003059 | 1.25x | yes |
| window_heavy_synthetic | 192 | 0.416292 | 0.395846 | 0.363898 | 1.14x | 0.120719 | 0.095766 | 1.26x | yes |
| hg38_chr21_H19 | 6,546 | 57.991300 | 58.761500 | 53.631300 | 1.08x | 24.247900 | 19.628400 | 1.24x | yes |

| Workload | Align calls | AVX2 requested | AVX2 compiled | AVX2 active | AVX2 calls | Byte calls | Word calls | Fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 156 | 1 | 1 | 1 | 312 | 312 | 0 | 0 |
| window_heavy_synthetic | 4,992 | 1 | 1 | 1 | 9,984 | 9,984 | 0 | 0 |
| hg38_chr21_H19 | 979,282 | 1 | 1 | 1 | 1,958,564 | 1,958,564 | 0 | 0 |

| Workload | SSE2 cache hit rate | AVX2 cache hit rate | SSE2 aligner s | AVX2 aligner s | Aligner speedup |
| --- | --- | --- | --- | --- | --- |
| tiny | 99.36% | 99.36% | 0.004713 | 0.004011 | 1.18x |
| window_heavy_synthetic | 99.98% | 99.98% | 0.145956 | 0.122715 | 1.19x |
| hg38_chr21_H19 | 100.00% | 100.00% | 29.197400 | 24.966400 | 1.17x |

| Workload | SSE2 forward s | AVX2 forward s | Forward speedup | SSE2 reverse s | AVX2 reverse s | Reverse speedup | SSE2 CIGAR s | AVX2 CIGAR s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 0.002764 | 0.001751 | 1.58x | 0.000754 | 0.000997 | 0.76x | 0.000283 | 0.000303 |
| window_heavy_synthetic | 0.087790 | 0.054944 | 1.60x | 0.023444 | 0.030950 | 0.76x | 0.008748 | 0.009188 |
| hg38_chr21_H19 | 17.301200 | 10.984900 | 1.57x | 5.085730 | 6.696690 | 0.76x | 1.715220 | 1.805390 |

| Workload | SSE2 byte path s | AVX2 byte path s | Byte path speedup | SSE2 word path s | AVX2 word path s | SSE2 banded_sw s | AVX2 banded_sw s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 0.003204 | 0.002414 | 1.33x | 0.000000 | 0.000000 | 0.000278 | 0.000297 |
| window_heavy_synthetic | 0.101543 | 0.075522 | 1.34x | 0.000000 | 0.000000 | 0.008584 | 0.009013 |
| hg38_chr21_H19 | 20.228900 | 15.369800 | 1.32x | 0.000000 | 0.000000 | 1.682230 | 1.771400 |

## Decision

The AVX2 path is exact-clean and faster on tiny, window_heavy_synthetic, hg38_chr21_H19. Keep it default-off as an optional opt-in candidate.

## Boundaries

```text
default enabled: no
output semantic change: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SSW profile cache default change: no
validation relaxation: no
```
