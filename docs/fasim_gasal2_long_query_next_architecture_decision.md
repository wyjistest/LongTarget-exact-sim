# Fasim GASAL2 Long-Query Next Architecture Decision

This checkpoint records the current decision for the long-query
scoreInfo/preAlign next-architecture work.

## Decision

```text
decision = next_architecture_no_go
```

CPU fallback remains authority. The current segmented/no-last implementation
remains stopped. The checked next-architecture probes do not use GPU/GASAL2
results for candidate state, endpoint, CIGAR, traceback, output, or digest.

## Evidence

non-overlap exact-tile candidate equivalence failed:

```text
cpu_oracle_candidates = 31272
tile_candidates = 31591
candidate_missing = 1720
candidate_extra = 2039
fallback = 0
output digest unchanged
```

overlap exact-tile candidate equivalence failed:

```text
overlap = 1406
candidate_missing = 1
candidate_extra = 2591

overlap = 2048
candidate_missing = 1
candidate_extra = 2961
```

exact-column non-opt-in cannot launch for MALAT1 first8:

```text
query_len = 8708
required_smem = 52416
default_smem_limit = 49152
optin_smem_limit = 101376
resource_fit = 1
active = 0
error = invalid argument
```

shared-memory opt-in launches but is not scoreInfo-equivalent:

```text
active = 1
gpu_tasks = 432
scoreinfo_mismatches = 1
output digest unchanged
decision = smem_optin_scoreinfo_no_go
```

## Boundary

The current long-query next-architecture line is not a valid MALAT1/NEAT1
scoreInfo/preAlign replacement.

do not promote exact tiling.
do not promote overlap tiling.
do not promote smem opt-in.
do not mark the full objective complete from this evidence.

Further long-query work needs a different execution design, such as a
lower-shared-memory DP layout, a candidate-equivalent stitching design, or
another candidate generation strategy that proves equivalence before
performance characterization.

The next allowed design checkpoint is the lower-shared-memory streaming
scoreInfo design:

```bash
make check-fasim-long-query-streaming-scoreinfo-design
```

## Gate

```bash
make check-fasim-gasal2-long-query-next-architecture-decision
```
