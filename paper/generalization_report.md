# GASAL2-LongTarget Phase 3 short-query generalization

This report retains every preregistered supported workload, mismatch, and full-length guard.

```text
paper_runtime_epoch = 0
paper_runtime_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
artifact_root = .paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization
artifact_manifest_sha256 = ef16dbbb7250304a46ac28d2584bedfd1186e3497fd7bc8038b3b004edc52b40
decision = generalization_supported
clean_workloads = 10/13
clean_fraction = 0.769231
bootstrap_interval = deferred_to_phase_5
```

## Supported-query results

| workload | query | length | position | target | role | n | median speedup | clustered score/stability/Nt | ties | status | full-row missing/extra |
|---|---|---:|---|---|---|---:|---:|---|---:|---|---:|
| g01_malat1_5p_1024_chr11 | MALAT1 | 1024 | 5p | chr11_center_2mb | generalization_core | 3 | 11.924442x | 1/1/1 | 1 | clean | 132/129 |
| g02_malat1_mid_2048_chr21 | MALAT1 | 2048 | mid | chr21_center_2mb | generalization_core | 3 | 16.235978x | 1/0/1 | 1 | mismatch | 54/54 |
| g03_malat1_3p_2812_chr22 | MALAT1 | 2812 | 3p | chr22_center_2mb | generalization_core | 3 | 17.420779x | 1/1/1 | 1 | clean | 114/138 |
| g04_neat1_5p_2048_chr22 | NEAT1 | 2048 | 5p | chr22_center_2mb | generalization_core | 3 | 17.073503x | 1/1/1 | 1 | clean | 123/141 |
| g05_neat1_mid_2812_chr11 | NEAT1 | 2812 | mid | chr11_center_2mb | generalization_core | 3 | 17.721834x | 1/1/1 | 1 | clean | 453/496 |
| g06_neat1_3p_1024_chr21 | NEAT1 | 1024 | 3p | chr21_center_2mb | generalization_core | 3 | 13.877246x | 1/1/1 | 1 | clean | 3/12 |
| g07_kcnq1ot1_5p_2812_chr21 | KCNQ1OT1 | 2812 | 5p | chr21_center_2mb | generalization_core | 3 | 23.044489x | 1/1/1 | 1 | clean | 27/27 |
| g08_kcnq1ot1_mid_1024_chr22 | KCNQ1OT1 | 1024 | mid | chr22_center_2mb | generalization_core | 3 | 13.975727x | 1/1/1 | 1 | clean | 81/60 |
| g09_kcnq1ot1_3p_2048_chr11 | KCNQ1OT1 | 2048 | 3p | chr11_center_2mb | generalization_core | 3 | 20.362261x | 1/1/0 | 1 | mismatch | 129/153 |
| g10_h19_full_chr11 | H19 | 2812 | full | chr11_center_2mb | breadth | 1 | 19.893861x | 1/1/1 | 1 | clean | 238/268 |
| g11_h19_full_chr21 | H19 | 2812 | full | chr21_center_2mb | breadth | 1 | 20.438587x | 1/1/1 | 1 | clean | 106/106 |
| g12_h19_full_chr22 | H19 | 2812 | full | chr22_center_2mb | breadth | 1 | 20.366780x | 1/0/1 | 1 | mismatch | 217/235 |
| g13_meg3_full_chr11 | MEG3 | 1582 | full | chr11_center_2mb | breadth | 1 | 15.528139x | 1/1/1 | 1 | clean | 75/64 |

The authority contract is equality of score-, stability-, and Nt-ranked clustered TFO1-5 plus boundary ties. Raw top5 and full-row missing/extra counts are retained as diagnostics and are not promoted to a full-output claim.

## Retained mismatches

- `g02_malat1_mid_2048_chr21`: status=mismatch; repeat_consistent=1; clustered score/stability/Nt=1/0/1; full missing/extra=54/54.
- `g09_kcnq1ot1_3p_2048_chr11`: status=mismatch; repeat_consistent=1; clustered score/stability/Nt=1/1/0; full missing/extra=129/153.
- `g12_h19_full_chr22`: status=mismatch; repeat_consistent=1; clustered score/stability/Nt=1/0/1; full missing/extra=217/235.

All mismatch representative rows, ranks, cluster IDs, and full TFOsorted columns are retained in `paper/source_data/generalization_mismatch_top5_pre_freeze.tsv`.

## Full-length guards

| workload | query | length | supported | reason | GPU fast path executed | status |
|---|---|---:|---:|---|---:|---|
| n01_malat1_full_guard | MALAT1 | 8708 | 0 | query_length_contract | 0 | guarded |
| n02_neat1_full_guard | NEAT1 | 22767 | 0 | query_length_contract | 0 | guarded |
| n03_kcnq1ot1_full_guard | KCNQ1OT1 | 91667 | 0 | query_length_contract | 0 | guarded |

technical failure receipts: 0

All three full-length negative controls were rejected by `query_length_contract` before GPU execution. Across supported rows, fallback and OOM totals were zero.

## Decision

`generalization_supported`: 10 of 13 preregistered supported workloads were clean (76.92%). Each included non-H19 identity and each target region has at least one clean row, and one preset was used across all supported rows.

The three mismatch workloads remain part of the evidence package. This result supports non-H19 generalization under a workload-level contract gate; it does not guarantee that every short query is clean.

Machine-readable authority:

- `paper/source_data/generalization_runs_pre_freeze.tsv`
- `paper/source_data/generalization_pairs_pre_freeze.tsv`
- `paper/source_data/generalization_workloads_pre_freeze.tsv`
- `paper/source_data/generalization_guards_pre_freeze.tsv`
- `paper/source_data/generalization_failures_pre_freeze.tsv`
- `paper/source_data/generalization_mismatch_top5_pre_freeze.tsv`
- `paper/phase3_artifact_manifest.tsv`
