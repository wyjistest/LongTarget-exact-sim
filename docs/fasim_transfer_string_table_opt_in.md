# Fasim transferString Table Opt-In

Base branch:

```text
fasim-transferstring-table-shadow
```

This PR turns the table-driven `transferString` converter from a shadow into a
default-off real path with optional legacy validation.

## Scope

```text
default path unchanged
table path is opt-in only
legacy validation is opt-in only
fallback to legacy on mismatch
no output semantic change
no scoring change
no threshold change
no non-overlap change
no conservative filter
no CUDA kernel
no default/recommended opt-in claim
```

## Env

```bash
FASIM_TRANSFERSTRING_TABLE=1
FASIM_TRANSFERSTRING_TABLE_VALIDATE=1
```

Behavior:

```text
FASIM_TRANSFERSTRING_TABLE=0/unset:
  use legacy transferString path.

FASIM_TRANSFERSTRING_TABLE=1:
  use table-driven transferString as the real seq2 producer.

FASIM_TRANSFERSTRING_TABLE=1 FASIM_TRANSFERSTRING_TABLE_VALIDATE=1:
  produce seq2 with the table path.
  also run legacy transferStringProfiled(...).
  compare table seq2 against legacy seq2.
  on mismatch, count mismatch/fallback and use legacy seq2.
```

## Telemetry

The profile now emits:

```text
benchmark.fasim_transfer_string_table_requested
benchmark.fasim_transfer_string_table_active
benchmark.fasim_transfer_string_table_validate_enabled
benchmark.fasim_transfer_string_table_calls
benchmark.fasim_transfer_string_table_seconds
benchmark.fasim_transfer_string_table_legacy_validate_seconds
benchmark.fasim_transfer_string_table_compared
benchmark.fasim_transfer_string_table_mismatches
benchmark.fasim_transfer_string_table_fallbacks
benchmark.fasim_transfer_string_table_bases_converted
```

`fasim_transfer_string_seconds` and `fasim_window_generation_transfer_seconds`
measure the real path. With validation enabled, the extra legacy validation
cost is reported separately in
`fasim_transfer_string_table_legacy_validate_seconds`.

## Local humanLncAtlas Profiles

These use the same local external FASTA inputs from
`docs/fasim_transfer_string_table_shadow.md`; the corpus files are not committed.

### A/B profile without validation

```text
env = FASIM_TRANSFERSTRING_TABLE=1
repeat = 2
```

| Workload | Digest | Records | Calls | TransferString seconds | Window generation seconds | Mismatches | Fallbacks |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| human_lnc_atlas_17kb_target | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | 16 | 0.000217 | 0.001027 | 0 | 0 |
| human_lnc_atlas_508kb_target | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | 416 | 0.003211 | 0.016115 | 0 | 0 |

For comparison, the prior legacy/shadow profile recorded:

| Workload | Legacy transferString seconds | Legacy window generation seconds |
| --- | ---: | ---: |
| human_lnc_atlas_17kb_target | 0.022020 | 0.023072 |
| human_lnc_atlas_508kb_target | 0.308771 | 0.324777 |

### Validation/fallback profile

```text
env = FASIM_TRANSFERSTRING_TABLE=1 FASIM_TRANSFERSTRING_TABLE_VALIDATE=1
repeat = 2
```

| Workload | Calls | Compared | Mismatches | Fallbacks | Table seconds | Legacy validate seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| human_lnc_atlas_17kb_target | 16 | 16 | 0 | 0 | 0.000173 | 0.016186 |
| human_lnc_atlas_508kb_target | 416 | 416 | 0 | 0 | 0.003054 | 0.306236 |

The validation runs kept the canonical output digests identical:

```text
17kb:  sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
508kb: sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221
```

## Decision

```text
table real opt-in:
  exact on compared validation calls
  transferString time drops sharply
  window generation time drops sharply without validation

validate/fallback:
  compared calls > 0
  mismatches = 0
  fallbacks = 0

default path:
  unchanged
```

This supports keeping `FASIM_TRANSFERSTRING_TABLE=1` as a default-off real
opt-in. It does not yet justify making it default. The next step should be a
recommended-opt-in characterization only if repeated profiles remain clean and
show stable wall-clock benefit.
