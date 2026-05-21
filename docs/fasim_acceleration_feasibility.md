# Fasim Acceleration Feasibility

Base branch:

```text
main
```

This PR adds profiling and exactness infrastructure for Fasim. It does not
change the algorithm, thresholds, non-overlap selection, output semantics, add a
filter, or add a GPU kernel.

## Goal

The next acceleration decision should be based on measured Fasim structure, not
on assuming that all SIM work is GPU-friendly. This PR asks:

```text
1. How much time is spent in Fasim scoring work?
2. How much time is spent outside scoring?
3. Is a stable canonical output digest available?
4. What is the Amdahl ceiling for DP/scoring acceleration?
```

## Targets

```bash
make build-fasim
make check-fasim-exactness
make check-fasim-profile-telemetry
make benchmark-fasim-profile
```

`check-fasim-exactness` runs the small `testDNA.fa` / `H19.fa` fixture twice,
canonicalizes the lite output records, and verifies the digest against:

```text
tests/oracle_fasim_profile/sample_lite.digest
```

The canonical digest sorts non-header lite output records before hashing. This
means the check validates output content while explicitly normalizing record
order.

## Telemetry

`FASIM_PROFILE=1` enables default-off runtime profiling. The profile runner
emits:

```text
fasim_total_seconds
fasim_io_seconds
fasim_window_generation_seconds
fasim_dp_scoring_seconds
fasim_column_max_seconds
fasim_local_max_seconds
fasim_nonoverlap_seconds
fasim_validation_seconds
fasim_output_seconds
fasim_num_queries
fasim_num_windows
fasim_num_dp_cells
fasim_num_candidates
fasim_num_validated_candidates
fasim_num_final_hits
fasim_output_digest_available
fasim_output_digest
fasim_canonical_output_records
```

The first profiling pass is intentionally conservative. In the CPU Fasim path,
`dp_scoring_seconds` wraps the exact `fastSIM` / `SIM` scoring call. Some inner
sub-stages, including local-max details and the internal de-dup/non-overlap-like
selection inside `fastSIM`, are not split yet and therefore remain included in
`dp_scoring_seconds`. Their explicit fields are emitted as zero rather than
claiming precision this PR does not have.

## Fixture Result

Representative `make benchmark-fasim-profile` run:

```text
canonical output digest = sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6
canonical output records = 6
queries = 1
windows = 1
dp cells = 98,217,536
candidates = 23
validated candidates = 6
final hits = 6
```

Stage timing:

| Stage | Seconds | Percent |
| --- | ---: | ---: |
| I/O | 0.000156 | 0.71% |
| window generation | 0.005229 | 23.77% |
| DP scoring | 0.010984 | 49.93% |
| column max | 0.005341 | 24.28% |
| local max | 0.000000 | 0.00% |
| non-overlap | 0.000000 | 0.00% |
| validation | 0.000001 | 0.00% |
| output | 0.000042 | 0.19% |

Derived percentages:

```text
DP/scoring only = 49.93%
DP + column max = 74.21%
```

## Amdahl Estimate

Using only `fasim_dp_scoring_seconds` as the accelerated portion:

| DP speedup | Amdahl total speedup | Estimated total seconds |
| ---: | ---: | ---: |
| 5x | 1.665x | 0.013212 |
| 10x | 1.816x | 0.012114 |
| 20x | 1.902x | 0.011565 |
| 50x | 1.958x | 0.011235 |

If a future GPU path accelerates both DP scoring and column-max/prealign work,
the candidate accelerated fraction is higher, about `74.21%` on this fixture.
That is a reason to continue characterization, not a speedup claim.

## Decision

For this small fixture:

```text
DP/scoring only is below 60%.
DP + column max is near the 80% lower go threshold, but noisy.
canonical output digest is stable.
```

The fixture completes in only tens of milliseconds, so the stage percentages
are useful for checking the harness but too noisy for a production CUDA
investment decision. Therefore the next step should not be a blind CUDA rewrite.
The better next PR is either:

```text
1. improve stage decomposition inside fastSIM so local-max / de-dup selection
   are measured separately, or
2. run the same profiling harness on a larger representative Fasim workload.
```

Only if representative workloads show `DP + column max` near or above `80-90%`
should the line proceed to a GPU batch DP / prealign prototype. This fixture is
too small and noisy to justify CUDA work by itself. If scoring drops below 60%
on representative workloads, optimize host-side window generation, I/O/output,
or candidate handling before starting CUDA work.

## Boundaries

This PR is profiling and exactness infrastructure only:

```text
no algorithm change
no output change
no approximate filter
no GPU kernel
no threshold change
no non-overlap selection change
no speedup claim
```
