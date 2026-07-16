# Manuscript Outline

This outline maps sections to frozen claims and evidence. It is not manuscript
prose.

## Title Candidates

1. Contract-aware GPU acceleration for short-query Fasim-LongTarget prediction
2. GASAL2-LongTarget: operating-envelope characterization of short-query top-K acceleration
3. Preserving clustered TFO prioritization in GPU-accelerated short-query LongTarget screening

## Introduction

- LongTarget and Fasim-LongTarget context: references `longtarget2015` and
  `fasimlongtarget2022`; claim scope C1-C3.
- Triplex prediction landscape: references `triplexator2012` and `threeplex2023`.
- GPU alignment context: references `gasal2_2019`, `cudasw4_2024`, and
  `accelign2026`.

## Methods

- Fasim-LongTarget baseline: C1-C3; Figure 1; Table 1;
  `paper/benchmark_protocol.md`.
- GASAL2 fast top-K path: C1 and C3; Figure 1; Tables 1-3.
- Output and correctness contracts: C3; Figure 2; Table 3;
  `paper/source_data/correctness.tsv`.
- Two-slot scheduling: C4; Figure 3; Tables 2 and 4.
- Archive-first restore and merge: C5; Figure S1; Table 4.
- Exact-column component: C6; Figure 3; Table 4.
- Benchmark and statistics: C1-C7; Tables 1-4;
  `paper/source_data/paired_speedup_summary.tsv`.

## Results

- Contract correctness and fail-closed guards: C3; Figure 2; Table 3.
- Short-query fast top-K performance: C1; Figures 1D and 2; Tables 1 and 2.
- Non-H19 generalization: C2 and C3; Figure 2; Tables 2 and 3.
- Two-slot and exact-column ablations: C4 and C6; Figure 3; Table 4.
- Archive-first storage and bounded merge: C5; Figure S1; Table 4.
- Operating envelope and long-query boundary: C7; Figure 4; Supplementary
  operating-envelope table.

## Discussion

- Why short-query top-K benefits: C1, C4, and C6; Figures 2 and 3.
- Why full output and bounded long-query execution do not show the same gain:
  C7; Figure 4.
- Correctness boundary and retained mismatch rows: C2 and C3; Table 3.
- Resource and worker-density limits: C4, C5, and C7; Table 4.
- Future execution-contract redesign: C7; `paper/limitations.md`.

## Availability And Reproducibility

- Runtime and data freeze: C1-C7; `paper/source_data/DATA_FREEZE.md`.
- Input and environment provenance: C1-C7; `reproduce/input_manifest.tsv` and
  `reproduce/environment.md`.
- Reproduction commands: C1-C7; `reproduce/benchmark_commands.sh` and
  `paper/RELEASE_CHECKLIST.md`.
