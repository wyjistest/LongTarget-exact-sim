# Post-shake decision

The authorized `LINC01501 x shard_0009` paired shake-down passed on the frozen
`61da9b6` binary and the harness frozen at `8feae7e`.

## Runtime evidence

```text
target length                    4,942,620 bp
forward GPU tasks                  48,432 / 48,432
GPU endpoint attempts           4,345,980 / 4,345,980
CPU all-attempt oracle                  0
CPU reference align attempts            0
selected continuation failures          0
raw complete TFOsorted SHA-256    2199bc6033f51eed498b6e692a4f7f6e95178dca631d26562828bc9181cc1075
```

CPU and exact-hybrid raw outputs are byte-identical. The observed walls were
`361.63 s` and `177.92 s` (`2.03x`), but this is diagnostic only because an
unrelated 16-thread OpenMP production worker was active.

## Scientific evidence

```text
raw rows                              44,753
unique decoded source hits            44,477
exact duplicate rows removed             276
cross-component hits rejected            268
retained source hits                  44,209
mapped promoter associations          63,368
DBD1 source hits                      15,916
threshold-zero DBS peaks               8,639
promoter affinity pairs                1,395
target-gene affinity pairs             1,395
candidate-site rows                       15
```

The two arms are byte-identical for decoded rows, mapped associations, reject
rows, retained rows, DBD1, the threshold-zero DBS set, promoter and target-gene
affinity products, and all three Top-5 candidate-site rankings.

The frozen decision is in `shake_down_decision.json`. A second live audit found
no production-target job for any of the six fresh queries, so
`formal_execution_addendum.json` authorizes the 36 planned full-concat runs.
This remains experimental execution authorization only:

```text
production_authorized = false
gpu_only_claim = false
bioinformatics_v2_state_modified = false
```
