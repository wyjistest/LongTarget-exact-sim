# Fasim Accelign Shape Benchmark

This report benchmarks standalone Accelign examples on Fasim-like `aligner.Align` request shapes. It does not integrate Accelign into Fasim, does not change runtime output, and does not use Accelign results for scoring, thresholds, non-overlap, CIGAR, alignment strings, SIM-close, or recovery behavior.

## Reference

```text
Fasim hg38_chr21_H19 aligner.Align shape:
  align calls = 979,282
  avg query len = 2812
  avg target len = 67.38
  max target len = 190
  CPU reference for 50k sampled requests = 2.252500s
```

## Results

The speedup column is a kernel-level reference ratio against the previously measured 50k CPU `aligner.Align` sample. It is not an apples-to-apples Fasim end-to-end speedup, especially for the 100k random-length case.

For exact Fasim shadow work, treat the float path as the candidate path. The CUDA 12.5 smoke check reports `gpu scores ok` for float but score errors for the high-level `half2` path, so `half2` is not considered correctness-ready here.

| Case | Mode | Precision | Component | Milliseconds | GCUPS | Speedup vs 50k CPU reference | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fixed_50k_avg_shape | score-only | float | executeAlignmentMultiTile | 5.296100 | 1778.71 | 425.31x | 50k alignments, target=67, query=2812 |
| fixed_50k_avg_shape | score-only | half2 | executeAlignmentMultiTile | 7.227390 | 1303.40 | 311.66x | 50k alignments, target=67, query=2812 |
| fixed_50k_avg_shape | score+endpoint | float | executeAlignmentMultiTile | 14.516200 | 648.94 | 155.17x | 50k alignments, target=67, query=2812 |
| fixed_50k_avg_shape | score+endpoint | float | executeAlignmentSingleTile startPos | 3.240960 | 2906.61 | 695.01x | 50k alignments, target=67, query=2812 |
| random_100k_max_shape | score-only | float | executeAlignmentMultiTile | 32.318500 | 413.97 | 69.70x | 100k alignments, target<=190, query<=2812, random lengths |
| random_100k_max_shape | score-only | half2 | executeAlignmentMultiTile | 59.754500 | 223.90 | 37.70x | 100k alignments, target<=190, query<=2812, random lengths |
| random_100k_max_shape | score+endpoint | float | executeAlignmentMultiTile | 40.701800 | 328.71 | 55.34x | 100k alignments, target<=190, query<=2812, random lengths |
| random_100k_max_shape | score+endpoint | float | executeAlignmentSingleTile startPos | 7.223300 | 1852.20 | 311.84x | 100k alignments, target<=190, query<=2812, random lengths |

## Decision

Accelign float shows a strong standalone kernel-level speed signal on Fasim-like short-target, long-query request shapes. The next step is a default-off Fasim shadow that compares score and endpoints against CPU `aligner.Align`; Accelign must not feed runtime output until score/endpoints are mismatch-free and staging overhead is measured.

## Boundaries

```text
Accelign integrated into Fasim runtime: no
use Accelign result for output: no
CIGAR/alignment-string support: no
half2 exactness-ready on CUDA 12.5 smoke check: no
scoring/threshold/non-overlap change: no
SIM-close/recovery change: no
```

## CUDA 12.5 Smoke Check

```text
numAlignments 1000, subjectLength 67, queryLength 2812, randomLengths 0, randomSeqs 1, checkResults 1
float:
TIMING: 0.557056 ms 338.214 GCUPS (executeAlignmentMultiTile)
gpu scores ok
half2:
TIMING: 3.47334 ms 54.2428 GCUPS (executeAlignmentMultiTile)
Error subject 0, reference score -2616, gpu score -2010 subject length 67, query length 2812
1000 errors in total
```

## Raw Output

### fixed_50k_avg_shape score-only
```text
numAlignments 50000, subjectLength 67, queryLength 2812, randomLengths 0, randomSeqs 1, checkResults 0
float:
TIMING: 5.2961 ms 1778.71 GCUPS (executeAlignmentMultiTile)
half2:
TIMING: 7.22739 ms 1303.4 GCUPS (executeAlignmentMultiTile)
```

### fixed_50k_avg_shape endpoints
```text
numAlignments 50000, subjectLength 67, queryLength 2812, randomLengths 0, randomSeqs 1
float:
TIMING: 14.5162 ms 648.943 GCUPS (executeAlignmentMultiTile)
TIMING: 3.24096 ms 2906.61 GCUPS (executeAlignmentSingleTile startPos)
```

### random_100k_max_shape score-only
```text
numAlignments 100000, subjectLength 190, queryLength 2812, randomLengths 1, randomSeqs 1, checkResults 0
float:
TIMING: 32.3185 ms 413.974 GCUPS (executeAlignmentMultiTile)
half2:
TIMING: 59.7545 ms 223.9 GCUPS (executeAlignmentMultiTile)
```

### random_100k_max_shape endpoints
```text
numAlignments 100000, subjectLength 190, queryLength 2812, randomLengths 1, randomSeqs 1
float:
TIMING: 40.7018 ms 328.708 GCUPS (executeAlignmentMultiTile)
TIMING: 7.2233 ms 1852.2 GCUPS (executeAlignmentSingleTile startPos)
```
