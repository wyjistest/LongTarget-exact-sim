# Fasim SSW AVX2 Hybrid Modes

This report compares default SSE2, full AVX2, and hybrid AVX2 SSW modes. `FASIM_SSW_AVX2_MODE=forward_only` uses AVX2 for the forward score/end pass while keeping reverse-start and CIGAR on the legacy SSE2 path.

Each workload uses 3 run(s); tables report medians.

## tiny

Records: `6`

| Mode | Total s | Total vs SSE2 | SSW align s | SSW vs SSE2 | Forward s | Forward vs SSE2 | Reverse s | Reverse vs SSE2 | CIGAR s | Digest clean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SSE2 baseline | 0.255214 | 1.00x | 0.003766 | 1.00x | 0.002707 | 1.00x | 0.000736 | 1.00x | 0.000293 | yes |
| AVX2 compiled/off | 0.252059 | 1.01x | 0.003928 | 0.96x | 0.002855 | 0.95x | 0.000756 | 0.97x | 0.000295 | yes |
| AVX2 all | 0.242948 | 1.05x | 0.003234 | 1.16x | 0.001827 | 1.48x | 0.001010 | 0.73x | 0.000303 | yes |
| AVX2 forward_only | 0.253013 | 1.01x | 0.002897 | 1.30x | 0.001748 | 1.55x | 0.000745 | 0.99x | 0.000286 | yes |
| AVX2 reverse_only | 0.249874 | 1.02x | 0.004060 | 0.93x | 0.002729 | 0.99x | 0.000952 | 0.77x | 0.000284 | yes |
| AVX2 mode=off | 0.256098 | 1.00x | 0.003877 | 0.97x | 0.002770 | 0.98x | 0.000750 | 0.98x | 0.000292 | yes |

| Mode | AVX2 requested | AVX2 compiled | AVX2 active | AVX2 calls | Byte calls | Word calls | Fallbacks | Byte path s | Byte vs SSE2 | Banded_sw s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SSE2 baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.003144 | 1.00x | 0.000287 |
| AVX2 compiled/off | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0.003297 | 0.95x | 0.000289 |
| AVX2 all | 1 | 1 | 1 | 312 | 312 | 0 | 0 | 0.002511 | 1.25x | 0.000297 |
| AVX2 forward_only | 1 | 1 | 1 | 156 | 156 | 0 | 0 | 0.002196 | 1.43x | 0.000281 |
| AVX2 reverse_only | 1 | 1 | 1 | 156 | 156 | 0 | 0 | 0.003374 | 0.93x | 0.000279 |
| AVX2 mode=off | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0.003201 | 0.98x | 0.000286 |

## window_heavy_synthetic

Records: `192`

| Mode | Total s | Total vs SSE2 | SSW align s | SSW vs SSE2 | Forward s | Forward vs SSE2 | Reverse s | Reverse vs SSE2 | CIGAR s | Digest clean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SSE2 baseline | 0.409626 | 1.00x | 0.120312 | 1.00x | 0.087351 | 1.00x | 0.023534 | 1.00x | 0.008702 | yes |
| AVX2 compiled/off | 0.414599 | 0.99x | 0.123044 | 0.98x | 0.089324 | 0.98x | 0.023924 | 0.98x | 0.009053 | yes |
| AVX2 all | 0.364614 | 1.12x | 0.098612 | 1.22x | 0.057030 | 1.53x | 0.029809 | 0.79x | 0.008882 | yes |
| AVX2 forward_only | 0.376884 | 1.09x | 0.092164 | 1.31x | 0.056638 | 1.54x | 0.023511 | 1.00x | 0.008857 | yes |
| AVX2 reverse_only | 0.431488 | 0.95x | 0.131403 | 0.92x | 0.089229 | 0.98x | 0.030154 | 0.78x | 0.008948 | yes |
| AVX2 mode=off | 0.408618 | 1.00x | 0.121751 | 0.99x | 0.087572 | 1.00x | 0.023506 | 1.00x | 0.008838 | yes |

| Mode | AVX2 requested | AVX2 compiled | AVX2 active | AVX2 calls | Byte calls | Word calls | Fallbacks | Byte path s | Byte vs SSE2 | Banded_sw s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SSE2 baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.101117 | 1.00x | 0.008538 |
| AVX2 compiled/off | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0.103249 | 0.98x | 0.008884 |
| AVX2 all | 1 | 1 | 1 | 9,984 | 9,984 | 0 | 0 | 0.077094 | 1.31x | 0.008715 |
| AVX2 forward_only | 1 | 1 | 1 | 4,992 | 4,992 | 0 | 0 | 0.070250 | 1.44x | 0.008685 |
| AVX2 reverse_only | 1 | 1 | 1 | 4,992 | 4,992 | 0 | 0 | 0.109388 | 0.92x | 0.008779 |
| AVX2 mode=off | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0.101113 | 1.00x | 0.008655 |

## hg38_chr21_H19

Records: `6,546`

| Mode | Total s | Total vs SSE2 | SSW align s | SSW vs SSE2 | Forward s | Forward vs SSE2 | Reverse s | Reverse vs SSE2 | CIGAR s | Digest clean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SSE2 baseline | 57.808100 | 1.00x | 24.145400 | 1.00x | 17.261600 | 1.00x | 5.046760 | 1.00x | 1.705110 | yes |
| AVX2 compiled/off | 58.180600 | 0.99x | 24.275300 | 0.99x | 17.347300 | 1.00x | 5.047580 | 1.00x | 1.728390 | yes |
| AVX2 all | 54.014100 | 1.07x | 19.928000 | 1.21x | 11.231400 | 1.54x | 6.332090 | 0.80x | 1.758220 | yes |
| AVX2 forward_only | 52.588800 | 1.10x | 18.604400 | 1.30x | 11.226900 | 1.54x | 5.015680 | 1.01x | 1.745820 | yes |
| AVX2 reverse_only | 60.653700 | 0.95x | 26.359200 | 0.92x | 17.536200 | 0.98x | 6.434010 | 0.78x | 1.770430 | yes |
| AVX2 mode=off | 58.967000 | 0.98x | 24.834600 | 0.97x | 17.590900 | 0.98x | 5.122010 | 0.99x | 1.761180 | yes |

| Mode | AVX2 requested | AVX2 compiled | AVX2 active | AVX2 calls | Byte calls | Word calls | Fallbacks | Byte path s | Byte vs SSE2 | Banded_sw s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SSE2 baseline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 20.151400 | 1.00x | 1.672640 |
| AVX2 compiled/off | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 20.226700 | 1.00x | 1.694700 |
| AVX2 all | 1 | 1 | 1 | 1,958,564 | 1,958,564 | 0 | 0 | 15.395600 | 1.31x | 1.725280 |
| AVX2 forward_only | 1 | 1 | 1 | 979,282 | 979,282 | 0 | 0 | 14.081100 | 1.43x | 1.712110 |
| AVX2 reverse_only | 1 | 1 | 1 | 979,282 | 979,282 | 0 | 0 | 21.758700 | 0.93x | 1.736350 |
| AVX2 mode=off | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 20.503300 | 0.98x | 1.726710 |

## Decision

All characterized AVX2 modes are digest-clean with zero fallbacks. `FASIM_SSW_AVX2_MODE=forward_only` is the fastest hg38 mode in this run: 52.588800 vs 54.014100 for full AVX2 and 57.808100 for SSE2. `reverse_only` regresses to 60.653700, so reverse-start remains SSE2-preferred.

## Boundaries

```text
default enabled: no
output semantic change: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SSW profile cache default change: no
AVX512 added: no
validation relaxation: no
```
