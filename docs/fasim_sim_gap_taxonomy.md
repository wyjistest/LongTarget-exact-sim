# Fasim SIM-Gap Taxonomy

Base branch:

```text
fasim-gpu-dp-column-post-topk-align
```

This report compares Fasim fast output against the same binary's legacy `-F` SIM path on deterministic fixtures. It is taxonomy-only: no Fasim output change, no recovery, no filter, and no GPU code.

## Settings

| Setting | Value |
| --- | --- |
| profile_set | representative |
| near_tie_delta | 1 |
| threshold_score_band | 5 |
| long_hit_nt | 80 |
| merge_gap_bp | 32 |

| Workload | SIM records | Fasim records | Shared exact | SIM region-supported | SIM-only | Fasim-only | Exact recall vs SIM | Region support vs SIM | SIM-only % | SIM digest | Fasim digest |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tiny | 9 | 6 | 0 | 9 | 9 | 6 | 0.00% | 100.00% | 100.00% | sha256:e76200220c48ddb392ad993b205d1d67c80fdaa8dccb0ac357352d3f7f9db00d | sha256:fbcd7908110386e90c452008c872a8b32f775656042e8723a258f463f5ebeff6 |
| medium_synthetic | 72 | 48 | 0 | 72 | 72 | 48 | 0.00% | 100.00% | 100.00% | sha256:b4454d7d8c29d17f5a2c9cb14ef950b66d4f8e5e8fcc483ac29b3abfcd49c962 | sha256:0eddfe1e04db4c4c15b514b410fcdce176e2841cd8d3fa3038daf83838e89dae |
| window_heavy_synthetic | 288 | 192 | 0 | 288 | 288 | 192 | 0.00% | 100.00% | 100.00% | sha256:80fb17938642804e3c5da2f5ac33612a4bb61d32e8fd53ecbae20319b01c0377 | sha256:d5a6f64790269a702e799b00fed09a9b322e3796f2b990c41ececf2deecd644c |

`Shared exact` is strict canonical lite-record identity. `SIM region-supported` is looser: a SIM record is counted when Fasim has a same-family genomic overlap. Region support is a locality signal for possible recovery boxes, not an output-equivalence claim.

## Limitations

The representative fixtures are deterministic scale-ups of the small repository fixtures. They are useful for taxonomy plumbing and local pattern checks, but they are not a production corpus. Treat the decision below as a direction for the next diagnostic PR, not as proof that SIM recovery will improve production accuracy.

## Aggregate SIM-Only Taxonomy

| Category | SIM-only records | Percent of SIM-only |
| --- | --- | --- |
| long_hit_internal_peak | 41 | 11.11% |
| nested_alignment | 123 | 33.33% |
| nonoverlap_conflict | 0 | 0.00% |
| overlap_chain | 205 | 55.56% |
| tie_near_tie | 0 | 0.00% |
| threshold_near | 0 | 0.00% |
| unknown | 0 | 0.00% |

Flag counts are non-exclusive; a SIM-only record can have multiple flags.

| Flag | Records | Percent of SIM-only |
| --- | --- | --- |
| long_hit_internal_peak | 41 | 11.11% |
| nested_alignment | 164 | 44.44% |
| nonoverlap_conflict | 0 | 0.00% |
| overlap_chain | 369 | 100.00% |
| tie_near_tie | 246 | 66.67% |
| threshold_near | 82 | 22.22% |

## Per-Workload Taxonomy

### tiny

| Category | SIM-only records | Percent of workload SIM-only |
| --- | --- | --- |
| long_hit_internal_peak | 1 | 11.11% |
| nested_alignment | 3 | 33.33% |
| nonoverlap_conflict | 0 | 0.00% |
| overlap_chain | 5 | 55.56% |
| tie_near_tie | 0 | 0.00% |
| threshold_near | 0 | 0.00% |
| unknown | 0 | 0.00% |

| Recovery estimate | Value |
| --- | --- |
| recovery_windows | 4 |
| recovery_boxes | 6 |
| recovery_cells | 28351 |

### medium_synthetic

| Category | SIM-only records | Percent of workload SIM-only |
| --- | --- | --- |
| long_hit_internal_peak | 8 | 11.11% |
| nested_alignment | 24 | 33.33% |
| nonoverlap_conflict | 0 | 0.00% |
| overlap_chain | 40 | 55.56% |
| tie_near_tie | 0 | 0.00% |
| threshold_near | 0 | 0.00% |
| unknown | 0 | 0.00% |

| Recovery estimate | Value |
| --- | --- |
| recovery_windows | 4 |
| recovery_boxes | 48 |
| recovery_cells | 226808 |

### window_heavy_synthetic

| Category | SIM-only records | Percent of workload SIM-only |
| --- | --- | --- |
| long_hit_internal_peak | 32 | 11.11% |
| nested_alignment | 96 | 33.33% |
| nonoverlap_conflict | 0 | 0.00% |
| overlap_chain | 160 | 55.56% |
| tie_near_tie | 0 | 0.00% |
| threshold_near | 0 | 0.00% |
| unknown | 0 | 0.00% |

| Recovery estimate | Value |
| --- | --- |
| recovery_windows | 4 |
| recovery_boxes | 192 |
| recovery_cells | 907232 |

## Aggregate Recovery Cost Estimate

| Metric | Value |
| --- | --- |
| sim_records | 369 |
| fasim_records | 246 |
| shared_records | 0 |
| sim_region_supported_records | 369 |
| sim_only_records | 369 |
| fasim_only_records | 246 |
| fasim_recall_vs_sim | 0.00% |
| region_support_vs_sim | 100.00% |
| recovery_windows | 12 |
| recovery_boxes | 246 |
| recovery_cells | 1162391 |

## Decision

SIM-only records concentrate in local/nested/overlap patterns. A local SIM recovery shadow is a plausible next PR.

Forbidden-scope check:

```text
Fasim output change: no
SIM recovery implementation: no
GPU code: no
filter/threshold/non-overlap behavior change: no
```

