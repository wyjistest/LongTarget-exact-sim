# Phase 1 CPU Authority Profile Protocol

Status: preregistered before formal execution.

## Purpose

This profile measures the fraction of the current CPU authority wall time that
an exact SSW-CUDA backend could replace. It does not benchmark a new backend,
consume a fresh holdout, alter the authority contract, or lower the original
10x end-to-end B3 threshold.

The authority command is frozen as:

```text
{binary} -f1 {target} -f2 {query} -r 0 -cn 1 -O {attempt_output}
```

The environment is sanitized of every inherited `FASIM_*` variable and then
set to `FASIM_OUTPUT_MODE=tfosorted`, `FASIM_VERBOSE=0`, and
`FASIM_EXTEND_THREADS=1`. The only on/off difference is
`FASIM_SSW_CUDA_PHASE1_PROFILE=0|1`.

## Mutually Exclusive Stages

The default-off profiler uses a stack that pauses the parent timer while a
nested stage is active. It records:

```text
pre_align
selection
forward_alignment
reverse_alignment
banded_traceback
backend_bridge
downstream_triplex_conversion
stability_identity_nt
clustering_ranking_sort
serialization_io
wrapper_other
process_wrapper
```

`wrapper_other` is the instrumented main-process wall time not assigned to a
named in-process stage. `process_wrapper` is the independently measured outer
wall time minus the main-process timer. Thus every observation remains fully
accounted for instead of silently expanding the addressable fraction.

The addressable fractions are:

```text
p_strict_ssw =
  (pre_align + selection + forward_alignment + reverse_alignment +
   banded_traceback) / outer_wall

p_backend_addressable =
  (strict_ssw + backend_bridge) / outer_wall
```

Triplex conversion, stability/identity/Nt, clustering/ranking/sort,
serialization/I/O, and both wrapper categories are unchanged downstream and
must not enter either numerator.

## Frozen Panel

All inputs already occur in `used_input_exclusion_registry.tsv` and are
therefore development/regression evidence, not a fresh holdout.

| Workload | Role | Query | Target | Claim relevant |
| --- | --- | --- | --- | --- |
| `overhead_aq001_at0001` | small overhead | `aq001` | `at0001` | no |
| `medium_h19_chr22_2mb` | medium real | H19 | chr22 10-12 Mb slice | no |
| `large_h19_chr21` | large real | H19 | chr21 | yes |
| `large_h19_chr22` | large real | H19 | chr22 | yes |
| `application_aq005_at0199` | application-like consumed pair | `aq005` | `at0199` | no |

The machine-readable plan contains 50 immutable attempts: five observations
per workload for each of profile-off and profile-on. Observation 1 requests a
best-effort `POSIX_FADV_DONTNEED` input cache hint and is reported separately
as `cold_advisory`. Observations 2-5 are independent steady-state processes.
On/off order alternates by observation. Timeout is 1800 seconds and retry
policy is `none`.

Frozen plan SHA-256:

```text
e3901765923fb3d2d2ccf55ee61ab0c5b38d6c8b912c0a83afcc0241117724e9
```

## Correctness And Coverage Gates

- Profile-off and profile-on output manifests must be byte-identical for every
  paired observation.
- Profile-off must emit no Phase 1 telemetry.
- Every profile-on stack must finish at depth zero with zero stack errors.
- Named stages plus `wrapper_other` plus `process_wrapper` must match outer
  wall time within 2% or 2 ms, whichever is larger.
- Failures, timeouts, partial artifacts, and slow observations are retained;
  there are no automatic or replacement retries.
- Formal execution starts only from a committed clean worktree.

## Statistics And Amdahl Gate

For each steady-state metric, report the median, Q1, Q3, IQR, and a deterministic
10,000-resample percentile-bootstrap 95% CI with seed 20260727. Cold results
remain visible but do not enter the primary median.

For B3 feasibility, the conservative addressable fraction for each large
workload is the lower endpoint of the bootstrap CI for the steady-state median
`p_backend_addressable`. The program-level conservative fraction is the lower
of the chr21 and chr22 values.

```text
maximum_speedup_infinite = 1 / (1 - p_backend_addressable)

required_backend_speedup =
  p / (1/10 - (1-p))
```

The preregistered decision is:

```text
conservative p <= 0.90       -> closed_amdahl
10 < infinite ceiling < 12  -> open_low_headroom
infinite ceiling >= 12      -> open_amdahl
```

At `p=0.90`, 10x exists only at zero backend cost and is treated as
unreachable. The engineering track remains active regardless of the B3 gate.

## Execution Boundary

The plan, runner, instrumentation, tests, and preflight checker must be
committed and the worktree clean before formal execution. Formal artifacts are
written under `.paper-artifacts/ssw-cuda-v1/phase1/profile-runs`; the committed
source data and decisions are generated only after all 50 attempts complete.
