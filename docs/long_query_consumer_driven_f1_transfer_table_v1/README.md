# F1 table-driven target transform

This checkpoint makes the existing table-driven target-rule transform the
default when the development F1 scheduler is explicitly enabled. It does not
change the global default path, DP recurrence, consumer order, continuation,
or output contract. An explicit `FASIM_TRANSFERSTRING_TABLE=0` still restores
the legacy converter.

Implementation commit:

```text
e829f28bedca91f5ccdcb8b3bacff5fdeb8828c8
```

## Bottleneck attribution

Full-process phase timing on LINC01501 against promoter shard_0009 accounted
for the previously unexplained outer wall time:

```text
legacy transferStringTableOptIn     49.0707 s
FASTA read                           0.0171 s
cut sequence                         0.0013 s
task enqueue                         0.0041 s
source transforms                    0.0773 s
target encoding                      0.2937 s
output writes                        0.0850 s
```

The legacy transform processed 48,432 task strings and 242,084,160 input
bytes through `toupper`, a five-way comparison, and repeated string append.
The already-tested table implementation performs one indexed lookup per byte.

## Exactness

The table implementation's unit test passed in five runtime configurations:

```text
global default
explicit table enable
explicit table enable + validation shadow
F1 implicit table enable
F1 implicit enable + explicit table disable
```

The rebuilt full binary also passed the frozen 2 Mb F1 scheduler fixture:

```text
complete TFOsorted SHA-256:
a940474a6bbf5a4e27678571206210263792da0d1f4424942554930fd72b6f3b

task rows:                 10,368
scoreInfo groups:         245,422
attempts:                 981,688
F1 forward attempts:      389,089
reverse requests:         245,422
continuation failures:          0
row contract failures:          0
```

On the real promoter shard, one same-binary legacy control and two F1-default
runs all produced:

```text
complete TFOsorted SHA-256:
2199bc6033f51eed498b6e692a4f7f6e95178dca631d26562828bc9181cc1075

scheduler structural signature SHA-256:
6659cbdc18137d95089342c5971559d8626b0f1eff0f538282c7def4957ef036
```

The structural signature covers every task's group, attempt, selection,
fallback, round, continuation, and error accounting while excluding timing
columns.

## Performance

The same binary, CPU 19, GPU 1, input, and complete-output mode measured:

| Mode | Wall seconds | Transform seconds |
| --- | ---: | ---: |
| Explicit legacy control | 115.71 | 48.7316 |
| F1 default, repeat 1 | 67.19 | 0.2128 |
| F1 default, repeat 2 | 67.23 | 0.2126 |

Using the center of the two table runs:

```text
table wall                         67.21 s
legacy / table                     1.722x
wall reduction                     41.92%
transform speedup                 229.1x
contextual frozen CPU / table       5.43x
```

The CPU comparison uses the separately frozen 364.75 second authority median;
it is contextual rather than a fresh paired CPU run in this checkpoint.

## Next bottleneck

After removing target-rule conversion, almost all wall is inside two exact
stages:

```text
whole-query scoreInfo                         25.64-25.67 s
complete F1 batch calls                       39.74-39.81 s
  selected continuation outer region          27.79-27.83 s
    SSW                                        19.29 s
      reverse-start                            15.83 s
      banded traceback                          3.31 s
    triplex conversion                          7.30 s
  forward + reverse endpoint stages            10.87 s
```

The next optimization must target scoreInfo or selected continuation. Outer
task construction and output serialization are no longer material. A
continuation thread pool or CPU/GPU pipeline still requires a separate
deterministic-order implementation and performance gate.

## Boundaries

```text
global default path changed:          no
F1 development default changed:       yes
explicit legacy escape hatch:         yes
complete-output exactness:            pass on one query x one promoter shard
consumer_cuda_authorized:             false
production_authorized:                false
bioinformatics_v2_state:              unchanged
full promoter concat:                 not measured
continuous 4-12 kb envelope:          not established
```

Machine-readable evidence is in `performance_receipt.json`. Full artifacts
remain under
`/data/wenyujianData/linjieData/longtarget_runs/exact_long_query_hybrid_f1_outer_profile_v1`.
