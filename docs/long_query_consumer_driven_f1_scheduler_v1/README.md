# Long-query consumer-driven F1 scheduler

This directory documents the development-only F1 implementation spike. It is
based on the lower-bound audit at `4bad9a6` and is intentionally independent of
the audit decision. The implementation is default-off and does not authorize a
product mode or change the production promoter contract.

## Execution shape

The scheduler keeps the existing exact forward and reverse endpoint kernels and
changes only the submission schedule. All task rows share the round barrier;
the stage API receives one descriptor vector per round rather than launching a
four-round loop independently for each task:

```text
scoreInfo groups
  -> every task's round-0 descriptors in one global forward batch
  -> reverse only when the forward upper bound can affect threshold/best
  -> retire threshold groups
  -> globally compact active groups and repeat for active rounds
  -> one deferred reverse for a final last fallback when needed
  -> selected CPU AlignFromForward continuation
  -> canonical triplex conversion and TFOsorted output
```

Here “global” means all tasks in one bounded streaming batch. The outer FASTA
loop still flushes batches at its configured task limit, so this spike does not
materialize the entire target FASTA in one scheduler call.

There is no witness shortcut, new DP recurrence, GPU traceback, full CPU oracle,
or fallback from an F1 failure. A stage or continuation contract failure exits
the process. The normal path is unchanged; enable the spike only with:

```text
FASIM_LONG_QUERY_GPU_CONSUMER_F1_SCHEDULER=1
FASIM_LONG_QUERY_GPU_CONSUMER_CPU_CONTINUATION=1
```

The stateful streaming scoreInfo flags and the legacy `2812` GASAL2 guard are
also required by the checked runner. The full-query attempt API itself does not
raise that legacy guard.

## Reproduction

The checked 4,006 nt LINC01501 fixture uses the complete 2 Mb chr22 slice and
the frozen CPU authority digests. Run the complete output check with:

```bash
BUILD=0 scripts/check_long_query_consumer_f1_scheduler_v1.sh
```

Use `MODE=lite` to check the lite artifact. `BUILD=1` (the default) rebuilds a
separate binary with `FASIM_WITH_SSW_FORWARD_CONTINUATION`; set `BIN`, `WORK`,
`QUERY`, `TARGET`, and `EXPECTED_DIGEST` to run another bounded fixture. Set
`CHECK_FROZEN_COUNTS=0` when that fixture does not have the checked LINC01501
round-count contract. The generated report and summary are physical
development artifacts under `.tmp/`.

## Observed fixture result

The first complete-output run on the checked fixture produced:

```text
task rows                         10,368 / 10,368
scoreInfo groups                  245,422
attempts                          981,688
ordered forward attempts          389,089
reverse requests/scored           245,422 / 245,422
selected CPU continuations        245,422
continuation failures             0
empty groups                      0
threshold / best / last groups    197,533 / 26,535 / 21,354
round active groups               245,422, 47,889, 47,889, 47,889, 0
round forward attempts            245,422, 47,889, 47,889, 47,889, 0
round reverse requests            214,373, 3,856, 3,090, 2,749, 21,354
complete TFOsorted rows           9,032
complete TFOsorted SHA-256        a940474a6bbf5a4e27678571206210263792da0d1f4424942554930fd72b6f3b
lite SHA-256                      6f9e95ab6209d2ea053dfdef4872b6fd5616b07a9be8950976786c0a1215c226
```

The measured wall time was 32.46 seconds while the machine was carrying a
separate 16-thread OpenMP production workload. It is retained as diagnostic
timing only and is not a clean speed claim. The exactness result is independent
of that resource contention.

The same binary was then exercised on the two frozen promotion queries. Both
complete-output runs also matched their independent CPU authority artifacts:

```text
query             length   complete TFOsorted SHA-256                         wall (diagnostic)
PCAT19            8181     b49e3fa33ec1ae5961032f420cfe1a60d5a5b12f8886828be997f7cd5219a578    60.36 s
AL035530.2       12397     714cd07a86d86eca5c2858bae5d409b569b173aca12b0db44fcda9062ad40500   108.30 s
```

The corresponding lite digests are `ad63b2887f8c3095e261ad063ffb395d9eac7fb379beaeb7fe35dd6618f9f084`
and `7739dbe484344279cdde9beeb009dfff902815c32b4e7acb85b20d81abc17b46`.
These timings were collected while the separate OpenMP queue was active and
remain diagnostic only. The 12 kb run also exercised a legitimate empty
scoreInfo task; the outer F1 contract now accepts exactly the
`scoreinfo_groups=0, attempts=0` case while still failing closed for every
other incomplete or inconsistent result.

The work reduction is query-dependent rather than a fixed envelope. The
forward-prefix fractions for the three runs were 39.6%, 43.1%, and 78.5% of
their four-round attempts; the corresponding forward-plus-reverse proxy
fractions were 32.3%, 34.0%, and 51.8%. These are accounting observations, not
speed claims.

## Boundaries

The F1 scheduler remains an engineering spike. It must not be described as
GPU-only traceback, a continuous 4--12 kb validation, a production-authorized
mode, or a 10x route. The all-reverse implementation and the F0/lower-bound
artifacts remain the correctness and accounting references. Any fresh
long-query or promoter-panel result requires a new paired authority run.
