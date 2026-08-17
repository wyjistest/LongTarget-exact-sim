# Reporting Checklist

## Software And Environment

- [x] Paper runtime epoch and commit recorded.
- [x] GASAL2 commit and checked compile constants recorded.
- [x] OS, CPU, RAM, GPU model/count/memory, driver, CUDA, compiler and Python recorded.
- [x] Uncontrolled affinity, clocks, governor and persistence state declared.

## Inputs And Protocol

- [x] Input authority, license note, path, size and SHA-256 recorded.
- [x] Query coordinates, target region, rule, preset and output contract frozen.
- [x] Repeat counts, AB/BA order, seed, warm-up and timeout policy recorded.
- [x] Worker density and visible GPU assignment recorded.

## Correctness And Failures

- [x] Score, stability and Nt clustered TFO1-TFO5 compared separately.
- [x] Full-output equality kept separate from fast top-K equality.
- [x] Boundary ties, guards, fallback, overflow, allocation and OOM evidence retained.
- [x] Seven mismatch pairs and three mismatch workloads remain visible.
- [x] Exclusions and warm-ups are machine-readable.

## Statistics And Figures

- [x] Paired speedups computed per compatible pair.
- [x] Median, IQR, range, seed and bootstrap resamples reported.
- [x] `n < 3` rows do not receive inferential intervals.
- [x] Figures and tables generated from frozen source data.
- [x] SVG/PDF and direct 600 DPI PNG outputs available.

## Availability

- [x] Quick clean-checkout reproduction validated.
- [x] Core GPU and bounded max8 commands documented separately.
- [x] Raw artifact manifests retained by SHA-256.
- [ ] Publish raw artifact archive and permanent DOI after owner/license approval.
- [ ] Add approved citation metadata for this software release.
- [ ] Record final repository URL, release tag and DOI in the manuscript.
