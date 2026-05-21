# Fasim transferString Table Characterization

Base branch:

```text
fasim-transferstring-table-opt-in
```

This PR characterizes the default-off real table-driven `transferString` path.
It does not add optimization code and does not make the table path default.

## Scope

```text
no algorithm change
no output change
no scoring change
no threshold change
no non-overlap change
no conservative filter
no CUDA kernel
no default enablement
```

## Method

Modes:

```text
legacy:
  default path, no table env.

table:
  FASIM_TRANSFERSTRING_TABLE=1

validate:
  FASIM_TRANSFERSTRING_TABLE=1
  FASIM_TRANSFERSTRING_TABLE_VALIDATE=1
```

Each workload below uses five runs per mode. Tables report medians. The two
humanLncAtlas inputs are local FASTA copies used by earlier Fasim profiling PRs;
the corpus files are not committed.

## Median Summary

| Workload | Mode | Total seconds | Window generation seconds | transferString seconds | Table seconds | Legacy validate seconds | DP+column+local % |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| tiny | legacy | 0.040200 | 0.006723 | 0.006527 | 0 | 0 | 82.27% |
| tiny | table | 0.034295 | 0.000286 | 0.000081 | 0.000081 | 0 | 98.03% |
| tiny | validate | 0.043855 | 0.006690 | 0.000085 | 0.000085 | 0.006404 | 83.82% |
| medium_synthetic | legacy | 0.163664 | 0.023933 | 0.023104 | 0 | 0 | 84.61% |
| medium_synthetic | table | 0.146403 | 0.001143 | 0.000259 | 0.000259 | 0 | 98.69% |
| medium_synthetic | validate | 0.145265 | 0.020186 | 0.000201 | 0.000201 | 0.019231 | 85.76% |
| window_heavy_synthetic | legacy | 0.607974 | 0.086616 | 0.083369 | 0 | 0 | 85.27% |
| window_heavy_synthetic | table | 0.535241 | 0.004189 | 0.000917 | 0.000917 | 0 | 98.84% |
| window_heavy_synthetic | validate | 0.583042 | 0.081141 | 0.000847 | 0.000847 | 0.077243 | 85.79% |
| human_lnc_atlas_17kb_target | legacy | 0.061904 | 0.018234 | 0.017580 | 0 | 0 | 69.67% |
| human_lnc_atlas_17kb_target | table | 0.048763 | 0.000898 | 0.000198 | 0.000198 | 0 | 96.89% |
| human_lnc_atlas_17kb_target | validate | 0.063381 | 0.018274 | 0.000190 | 0.000190 | 0.017432 | 70.37% |
| human_lnc_atlas_508kb_target | legacy | 1.181690 | 0.310683 | 0.298157 | 0 | 0 | 72.96% |
| human_lnc_atlas_508kb_target | table | 0.885829 | 0.015694 | 0.003088 | 0.003088 | 0 | 97.51% |
| human_lnc_atlas_508kb_target | validate | 1.201010 | 0.327657 | 0.003135 | 0.003135 | 0.311957 | 72.19% |

## A/B Median Speedups

| Workload | Total speedup, legacy/table | Window generation speedup | transferString speedup | Digest stable | Mismatches | Fallbacks |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| tiny | 1.17x | 23.53x | 80.13x | yes | 0 | 0 |
| medium_synthetic | 1.12x | 20.95x | 89.34x | yes | 0 | 0 |
| window_heavy_synthetic | 1.14x | 20.68x | 90.96x | yes | 0 | 0 |
| human_lnc_atlas_17kb_target | 1.27x | 20.32x | 88.83x | yes | 0 | 0 |
| human_lnc_atlas_508kb_target | 1.33x | 19.80x | 96.56x | yes | 0 | 0 |

## Exactness

Canonical output digest stayed stable across legacy, table, and validate modes:

| Workload | Digest | Records | Windows | Candidates | Final hits |
| --- | --- | ---: | ---: | ---: | ---: |
| tiny | `sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6` | 6 | 1 | 23 | 6 |
| medium_synthetic | `sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae` | 48 | 8 | 184 | 48 |
| window_heavy_synthetic | `sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c` | 192 | 32 | 736 | 192 |
| human_lnc_atlas_17kb_target | `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 | 4 | 57 | 0 |
| human_lnc_atlas_508kb_target | `sha256:25469e60179a524dd712d7ef69ee0c8e379a17f8472be3c2843cd14eda04d221` | 34 | 104 | 1367 | 34 |

Validation mode compared every table call against legacy and stayed clean:

| Workload | Compared calls | Mismatches | Fallbacks |
| --- | ---: | ---: | ---: |
| tiny | 4 | 0 | 0 |
| medium_synthetic | 32 | 0 | 0 |
| window_heavy_synthetic | 128 | 0 | 0 |
| human_lnc_atlas_17kb_target | 16 | 0 | 0 |
| human_lnc_atlas_508kb_target | 416 | 0 | 0 |

## Decision

```text
FASIM_TRANSFERSTRING_TABLE=1:
  recommended opt-in

FASIM_TRANSFERSTRING_TABLE_VALIDATE=1:
  correctness gate only, not a performance mode

default:
  do not enable yet
```

The table real path reduced median total time and median window-generation time
on every measured workload, kept canonical output digests stable, and had zero
validation mismatches or fallbacks. This is enough to document
`FASIM_TRANSFERSTRING_TABLE=1` as a recommended opt-in.

Validation remains useful as a rollout check, but it intentionally runs legacy
conversion too; its median total time is close to legacy on the larger workloads.

The table path also moves DP+column+local to roughly 97-99% of measured runtime
on these table-mode profiles. The next performance PR can therefore be a narrow
default-off GPU batch DP+column prototype, still with CPU/Fasim output authority.
