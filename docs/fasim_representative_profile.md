# Fasim Representative Profile

Base branch:

```text
fasim-acceleration-feasibility
```

This PR extends the Fasim profiling and canonical digest harness from #47 to
larger deterministic fixtures. It still does not change Fasim algorithm/output,
add CUDA kernels, add filters, change thresholds, or change non-overlap
behavior.

## Scope

The repository currently contains only the small `testDNA.fa` / `H19.fa`
fixture. To make profiling less dominated by one tiny run, this PR adds
synthetic scale-up fixtures generated from the same inputs:

| Fixture | DNA entries | DNA repeat | Purpose |
| --- | ---: | ---: | --- |
| tiny | 1 | 1 | Current #47 smoke fixture using original `testDNA.fa` / `H19.fa` |
| medium_synthetic | 8 | 1 | Multi-record scale-up for lower timing noise |
| window_heavy_synthetic | 32 | 1 | Window-heavy scale-up for DP/column fraction characterization |

These are deterministic local profiling fixtures, not a replacement for a real
production corpus. They are useful for deciding whether the next engineering
step is plausible, not for claiming production speedup.

## Targets

```bash
make build-fasim
make check-fasim-exactness
make check-fasim-profile-telemetry
make check-fasim-representative-profile
make benchmark-fasim-representative-profile
```

`check-fasim-representative-profile` runs each fixture twice, checks that the
canonical lite-output digest is stable, and verifies the digest against:

```text
tests/oracle_fasim_profile/representative/
```

## Representative Run

One `make benchmark-fasim-representative-profile` run:

| Fixture | Total seconds | Windows | DP cells | Candidates | Final hits | Digest |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| tiny | 0.020825 | 1 | 98,217,536 | 23 | 6 | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` |
| medium_synthetic | 0.146267 | 8 | 785,740,288 | 184 | 48 | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` |
| window_heavy_synthetic | 0.607846 | 32 | 3,142,961,152 | 736 | 192 | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` |

## Stage Percentages

| Fixture | DP/scoring | Column max | DP + column | Window generation | Output |
| --- | ---: | ---: | ---: | ---: | ---: |
| tiny | 58.11% | 27.65% | 85.76% | 13.18% | 0.22% |
| medium_synthetic | 60.39% | 25.25% | 85.65% | 13.99% | 0.10% |
| window_heavy_synthetic | 60.01% | 25.31% | 85.32% | 14.35% | 0.10% |

The larger synthetic fixtures reduce the tiny-fixture noise enough to show a
consistent shape: DP-only is around 58-61%, while DP + column max is around
85%. Local max, explicit non-overlap, validation, and output remain near zero in
the current instrumentation because #47 still wraps some `fastSIM` internals
inside `fasim_dp_scoring_seconds`.

## Amdahl Estimates

These are profiling estimates only. They assume the named fraction is accelerated
and all other work remains unchanged.

### DP-only

| Fixture | 5x | 10x | 20x | 50x |
| --- | ---: | ---: | ---: | ---: |
| tiny | 1.869x | 2.097x | 2.233x | 2.323x |
| medium_synthetic | 1.935x | 2.191x | 2.346x | 2.450x |
| window_heavy_synthetic | 1.923x | 2.174x | 2.326x | 2.428x |

DP-only acceleration is not enough for a 10x line. Even aggressive DP-only
speedups stay around 2-2.5x on these fixtures.

### DP + Column Max

| Fixture | 5x | 10x | 20x | 50x |
| --- | ---: | ---: | ---: | ---: |
| tiny | 3.186x | 4.383x | 5.398x | 6.269x |
| medium_synthetic | 3.177x | 4.364x | 5.367x | 6.225x |
| window_heavy_synthetic | 3.150x | 4.307x | 5.277x | 6.101x |

DP + column max is the only plausible GPU target from this profile. It is a
possible 3x-6x line on these synthetic fixtures, but still not a demonstrated
10x path.

## Decision

```text
profiling harness: pass
canonical digests: stable
DP-only CUDA path: not sufficient
DP + column CUDA path: plausible, but only weak-go from synthetic fixtures
production speedup claim: no
```

The next PR should not be a full CUDA rewrite. There are two defensible next
steps:

```text
1. run the same harness on a real larger Fasim corpus, if available; or
2. build a narrow default-off GPU batch DP + column-max prototype with CPU/Fasim
   validation remaining authoritative.
```

If real corpus profiling keeps DP + column/local near 85-90%, the GPU batch
prototype is justified. If the fraction drops toward 60-70%, optimize actual
host-side bottlenecks before investing in CUDA.

## Boundaries

```text
no algorithm change
no output change
no approximate/conservative filter
no GPU kernel
no threshold change
no non-overlap behavior change
no speedup claim
```
