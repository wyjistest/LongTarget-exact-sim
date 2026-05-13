# Fasim transferString Table Shadow

Base branch:

```text
fasim-transferstring-decomposition
```

This PR adds a default-off exact shadow for a table-driven `transferString`
converter. It is diagnostic-only:

```text
legacy transferString remains authority
no real table-driven path
no output change
no algorithm change
no CUDA kernel
no conservative filter
no threshold change
no non-overlap behavior change
no speedup claim
```

## Env

Enable the shadow only while profiling:

```bash
FASIM_TRANSFERSTRING_TABLE_SHADOW=1 make check-fasim-profile-telemetry
```

The profiling path still uses the legacy `transferStringProfiled(...)` result as
the real `seq2`. When the shadow is enabled, it also computes
`transferStringTableDriven(...)` and compares that diagnostic result against the
legacy string.

## Telemetry

The profile emits:

```text
benchmark.fasim_transfer_string_table_shadow_enabled
benchmark.fasim_transfer_string_table_shadow_calls
benchmark.fasim_transfer_string_table_shadow_compared_calls
benchmark.fasim_transfer_string_table_shadow_mismatches
benchmark.fasim_transfer_string_table_shadow_fallbacks
benchmark.fasim_transfer_string_table_shadow_seconds
benchmark.fasim_transfer_string_table_shadow_input_bases
```

`fallbacks` is currently expected to stay zero because this PR does not route
production work through the table path.

## Checked Fixtures

### Built-in and representative profiles

```text
env = FASIM_TRANSFERSTRING_TABLE_SHADOW=1
```

| Fixture | Calls | Compared | Mismatches | Fallbacks | Input bases | Table shadow seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| tiny | 4 | 4 | 0 | 0 | 17,464 | 0.000066 |
| medium_synthetic | 32 | 32 | 0 | 0 | 139,712 | 0.000200 |
| window_heavy_synthetic | 128 | 128 | 0 | 0 | 558,848 | 0.000873 |

The tiny profile digest stayed stable:

```text
sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6
```

### Local humanLncAtlas profiles

These use local external FASTA inputs; the corpus files are not committed.

#### human_lnc_atlas_17kb_target

```text
repeat = 2
canonical digest = sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
canonical output records = 0
calls = 16
compared calls = 16
mismatches = 0
fallbacks = 0
input bases = 72,372
legacy transferString seconds = 0.022020
table shadow seconds = 0.000223
```

#### human_lnc_atlas_508kb_target

```text
repeat = 2
canonical digest = sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221
canonical output records = 34
calls = 416
compared calls = 416
mismatches = 0
fallbacks = 0
input bases = 2,075,072
legacy transferString seconds = 0.308771
table shadow seconds = 0.003159
```

## Decision

The table-driven converter is exact on the compared profiling calls:

```text
compared calls: clean
mismatches: 0
fallbacks: 0
real/default path: no
```

This is a strong shadow signal for a narrow table-driven `transferString`
implementation. It is not a production speedup claim because the legacy path
still produces the authoritative output and the table path only runs as extra
diagnostic work.

## Recommended Next Step

If this shadow is reviewed cleanly, the next PR can add a default-off real opt-in
with validation:

```text
FASIM_TRANSFERSTRING_TABLE=1
FASIM_TRANSFERSTRING_TABLE_VALIDATE=1
```

That follow-up should keep legacy validation available, fail closed on mismatch,
and rerun representative plus real-corpus profiles before making any broader
Fasim GPU decision.
