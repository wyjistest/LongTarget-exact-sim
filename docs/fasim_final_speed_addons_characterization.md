# Fasim Final Speed Add-ons Characterization

This report compares the core large-workload opt-in stack with optional AVX2 and SSW ProfileContext add-ons. It does not add optimization logic or default any optional path.

Core stack:

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_GPU_DP_COLUMN_AUTO=1
FASIM_SSW_PROFILE_CACHE=1
```

Each workload uses 3 run(s); tables report medians.

## tiny

Records: `6`
Digest: `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6`

| Mode | Total s | Delta vs core s | Speedup vs core | SSW align s | SSW speedup | Forward s | Forward speedup | Reverse s | Reverse speedup | CIGAR s | Digest clean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| core | 0.255808 | 0.000000 | 1.00x | 0.003907 | 1.00x | 0.002805 | 1.00x | 0.000785 | 1.00x | 0.000276 | yes |
| core + AVX2 | 0.250439 | 0.005369 | 1.02x | 0.002975 | 1.31x | 0.001775 | 1.58x | 0.000814 | 0.96x | 0.000290 | yes |
| core + ProfileContext | 0.256445 | -0.000637 | 1.00x | 0.004028 | 0.97x | 0.002900 | 0.97x | 0.000780 | 1.01x | 0.000285 | yes |
| core + AVX2 + ProfileContext | 0.253918 | 0.001890 | 1.01x | 0.002974 | 1.31x | 0.001796 | 1.56x | 0.000800 | 0.98x | 0.000287 | yes |

| Mode | AVX2 mode | AVX2 calls | AVX2 forward | AVX2 reverse | AVX2 fallbacks | ProfileContext active | ProfileContext hits | ProfileContext misses | ProfileContext hit rate | ProfileContext fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| core | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | 0 |
| core + AVX2 | 2 | 156 | 156 | 0 | 0 | 0 | 0 | 0 | n/a | 0 |
| core + ProfileContext | 0 | 0 | 0 | 0 | 0 | 1 | 155 | 1 | 99.36% | 0 |
| core + AVX2 + ProfileContext | 2 | 156 | 156 | 0 | 0 | 1 | 155 | 1 | 99.36% | 0 |

## window_heavy_synthetic

Records: `192`
Digest: `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c`

| Mode | Total s | Delta vs core s | Speedup vs core | SSW align s | SSW speedup | Forward s | Forward speedup | Reverse s | Reverse speedup | CIGAR s | Digest clean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| core | 0.412989 | 0.000000 | 1.00x | 0.125298 | 1.00x | 0.090953 | 1.00x | 0.024619 | 1.00x | 0.008858 | yes |
| core + AVX2 | 0.383055 | 0.029934 | 1.08x | 0.091869 | 1.36x | 0.055357 | 1.64x | 0.024588 | 1.00x | 0.008915 | yes |
| core + ProfileContext | 0.402453 | 0.010536 | 1.03x | 0.125498 | 1.00x | 0.091280 | 1.00x | 0.024641 | 1.00x | 0.008888 | yes |
| core + AVX2 + ProfileContext | 0.366060 | 0.046929 | 1.13x | 0.092558 | 1.35x | 0.055919 | 1.63x | 0.024605 | 1.00x | 0.008944 | yes |

| Mode | AVX2 mode | AVX2 calls | AVX2 forward | AVX2 reverse | AVX2 fallbacks | ProfileContext active | ProfileContext hits | ProfileContext misses | ProfileContext hit rate | ProfileContext fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| core | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | 0 |
| core + AVX2 | 2 | 4,992 | 4,992 | 0 | 0 | 0 | 0 | 0 | n/a | 0 |
| core + ProfileContext | 0 | 0 | 0 | 0 | 0 | 1 | 4,991 | 1 | 99.98% | 0 |
| core + AVX2 + ProfileContext | 2 | 4,992 | 4,992 | 0 | 0 | 1 | 4,991 | 1 | 99.98% | 0 |

## hg38_chr21_H19

Records: `6,546`
Digest: `sha256:81b9c5e23d63534b27f0742d512323ff678bbf648e5ae5e6ea03aab1c4717d26`

| Mode | Total s | Delta vs core s | Speedup vs core | SSW align s | SSW speedup | Forward s | Forward speedup | Reverse s | Reverse speedup | CIGAR s | Digest clean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| core | 59.029300 | 0.000000 | 1.00x | 25.254500 | 1.00x | 18.072700 | 1.00x | 5.302200 | 1.00x | 1.726840 | yes |
| core + AVX2 | 52.157400 | 6.871900 | 1.13x | 18.568200 | 1.36x | 10.962300 | 1.65x | 5.295830 | 1.00x | 1.738160 | yes |
| core + ProfileContext | 57.804100 | 1.225200 | 1.02x | 25.357800 | 1.00x | 18.171500 | 0.99x | 5.306920 | 1.00x | 1.736610 | yes |
| core + AVX2 + ProfileContext | 51.156000 | 7.873300 | 1.15x | 18.720800 | 1.35x | 11.064400 | 1.63x | 5.279570 | 1.00x | 1.744540 | yes |

| Mode | AVX2 mode | AVX2 calls | AVX2 forward | AVX2 reverse | AVX2 fallbacks | ProfileContext active | ProfileContext hits | ProfileContext misses | ProfileContext hit rate | ProfileContext fallbacks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| core | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | 0 |
| core + AVX2 | 2 | 979,282 | 979,282 | 0 | 0 | 0 | 0 | 0 | n/a | 0 |
| core + ProfileContext | 0 | 0 | 0 | 0 | 0 | 1 | 979,281 | 1 | 100.00% | 0 |
| core + AVX2 + ProfileContext | 2 | 979,282 | 979,282 | 0 | 0 | 1 | 979,281 | 1 | 100.00% | 0 |

## Decision

All optional add-on modes are digest-clean relative to core. hg38 medians: core 59.029300, core+AVX2 52.157400, core+ProfileContext 57.804100, core+AVX2+ProfileContext 51.156000.

## Boundaries

```text
new optimization logic: no
default AVX2: no
default ProfileContext: no
output semantic change: no
scoring/threshold/non-overlap change: no
GPU AUTO policy change: no
SIM-close/recovery change: no
validation relaxation: no
```
