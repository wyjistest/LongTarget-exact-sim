# Fasim transferString Decomposition

Base branch:

```text
fasim-window-generation-decomposition
```

This PR decomposes the `transferString` part of Fasim window generation. It is
profiling-only:

```text
no algorithm change
no output change
no CUDA kernel
no conservative filter
no threshold change
no non-overlap behavior change
no transferString optimization
no speedup claim
```

## Telemetry

The profile now emits transferString totals:

```text
benchmark.fasim_transfer_string_seconds
benchmark.fasim_transfer_string_calls
benchmark.fasim_transfer_string_input_bases
benchmark.fasim_transfer_string_output_bases
```

It also splits transferString internals:

```text
benchmark.fasim_transfer_string_rule_select_seconds
benchmark.fasim_transfer_string_rule_materialize_seconds
benchmark.fasim_transfer_string_convert_seconds
benchmark.fasim_transfer_string_validate_seconds
benchmark.fasim_transfer_string_residual_seconds
```

`residual_seconds` is `total - measured_internal_steps`; it includes by-value
input copy, return/move overhead, function framing, and timer overhead. It is
diagnostic and should not be read as a pure allocation timer.

Mode distribution is reported for:

```text
para forward
para reverse
anti forward
anti reverse
```

Rule distribution is emitted for rules 1 through 18.

## Local External Profiles

These runs use the same local humanLncAtlas input shapes documented in
`docs/fasim_real_corpus_profile.md` and
`docs/fasim_window_generation_decomposition.md`. The corpus files are not
committed.

### human_lnc_atlas_17kb_target

```text
repeat = 2
canonical digest = sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
canonical output records = 0
windows = 4
dp_cells = 220,155,624
candidates = 57
final_hits = 0
```

| Stage | Seconds | Percent |
| --- | ---: | ---: |
| I/O | 0.000196 | 0.30% |
| window generation | 0.018052 | 27.92% |
| DP scoring | 0.028243 | 43.67% |
| column max | 0.017799 | 27.52% |
| local max | 0.000000 | 0.00% |
| non-overlap | 0.000000 | 0.00% |
| validation | 0.000004 | 0.01% |
| output | 0.000000 | 0.00% |

| Window-generation detail | Seconds | Percent of total |
| --- | ---: | ---: |
| cutSequence | 0.000014 | 0.02% |
| transferString | 0.017435 | 26.96% |
| reverse/complement | 0.000014 | 0.02% |
| source transform | 0.000425 | 0.66% |
| encoded target build | 0.000159 | 0.25% |
| flush_batch call wall | 0.046053 | 71.22% |

| transferString step | Seconds | Percent of transferString |
| --- | ---: | ---: |
| rule select | 0.000002 | 0.01% |
| rule materialize | 0.000001 | 0.00% |
| per-base convert | 0.017423 | 99.93% |
| validate | 0.000001 | 0.00% |
| copy/return residual | 0.000010 | 0.05% |

| Mode | Calls | Seconds | Percent of transferString |
| --- | ---: | ---: | ---: |
| para forward | 4 | 0.005306 | 30.43% |
| para reverse | 4 | 0.004688 | 26.89% |
| anti forward | 4 | 0.003987 | 22.87% |
| anti reverse | 4 | 0.003454 | 19.81% |

```text
transferString calls = 16
input bases = 72,372
rule 1 calls = 16
DP + column = 71.20%
DP + column + transferString = 98.16%
```

### human_lnc_atlas_508kb_target

```text
repeat = 2
canonical digest = sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221
canonical output records = 34
windows = 104
dp_cells = 6,312,369,024
candidates = 1,367
final_hits = 34
```

| Stage | Seconds | Percent |
| --- | ---: | ---: |
| I/O | 0.002645 | 0.23% |
| window generation | 0.306620 | 26.62% |
| DP scoring | 0.541449 | 47.01% |
| column max | 0.297482 | 25.83% |
| local max | 0.000000 | 0.00% |
| non-overlap | 0.000000 | 0.00% |
| validation | 0.000059 | 0.01% |
| output | 0.000146 | 0.01% |

| Window-generation detail | Seconds | Percent of total |
| --- | ---: | ---: |
| cutSequence | 0.000341 | 0.03% |
| transferString | 0.294627 | 25.58% |
| reverse/complement | 0.000241 | 0.02% |
| source transform | 0.008373 | 0.73% |
| encoded target build | 0.002962 | 0.26% |
| flush_batch call wall | 0.839252 | 72.87% |

| transferString step | Seconds | Percent of transferString |
| --- | ---: | ---: |
| rule select | 0.000020 | 0.01% |
| rule materialize | 0.000010 | 0.00% |
| per-base convert | 0.294437 | 99.94% |
| validate | 0.000009 | 0.00% |
| copy/return residual | 0.000150 | 0.05% |

| Mode | Calls | Seconds | Percent of transferString |
| --- | ---: | ---: | ---: |
| para forward | 104 | 0.075369 | 25.58% |
| para reverse | 104 | 0.074022 | 25.12% |
| anti forward | 104 | 0.073653 | 25.00% |
| anti reverse | 104 | 0.071583 | 24.30% |

```text
transferString calls = 416
input bases = 2,075,072
rule 1 calls = 416
DP + column = 72.84%
DP + column + transferString = 98.42%
```

## Decision

The prior PR identified transferString as almost all of window generation. This
PR narrows that further:

```text
transferString is dominated by per-base convert:
  17kb target: 99.93% of transferString
  508kb target: 99.94% of transferString

rule selection/materialization:
  negligible

copy/return residual:
  about 0.05% of transferString in these runs

mode distribution:
  roughly even on the 508kb target

rule distribution:
  rule 1 only for these profiled commands
```

The next optimization target is not allocator tuning or rule lookup. It is the
per-base conversion loop in `transferString`.

## Recommended Next Step

Create a narrow exactness-first optimization PR:

```text
fasim: add transferString table-driven exact shadow
```

Scope:

```text
1. Keep legacy transferString as authority.
2. Add a table-driven converter shadow or default-off opt-in.
3. Compare every produced seq2 against legacy transferString on the checked
   fixtures and local real-shaped workloads.
4. Keep canonical output digest byte-stable.
5. Do not change DP scoring, column max, thresholds, non-overlap, output, or
   CUDA paths.
```

Only after a table-driven CPU path is exact and measurably reduces the
`per-base convert` field should the Fasim line reconsider a combined
`transferString + DP + column` GPU or batching prototype.
