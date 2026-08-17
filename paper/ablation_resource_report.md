# GASAL2-LongTarget Phase 4 ablation, archive, and resources

```text
paper_runtime_epoch = 0
paper_runtime_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
artifact_root = .paper-artifacts/runtime-epoch-0-pre-freeze/phase4-ablation-resource
artifact_manifest_sha256 = 6bc1e07681db54d0c543512b835b0030b702c366a31645b480e20bf4aedf4fec
bootstrap_interval = deferred_to_phase_5
unsafe_runtime_flags_enabled = 0
full_121_segment_runs = 0
```

## Linked fast-path ablation

| contrast | workload | target | n | median paired speedup | contract |
|---|---|---|---:|---:|---|
| authority_vs_checked_gasal2 | c1_h19_chr21_chr22_fast_topk | chr21+chr22 | 5 | 38.320882x | fast_topk_score_stability_nt |
| sync_vs_two_slot | c4_h19_chr21_two_slot | chr21 | 5 | 1.143132x | fast_topk_score_stability_nt |
| sync_vs_two_slot | c4_h19_chr22_two_slot | chr22 | 5 | 1.151205x | fast_topk_score_stability_nt |

The authority-to-GASAL2 and synchronous-to-two-slot contrasts use the same fast top-K contract within each row, but not the same target scope across all three configurations. A single-workload A/B/C triad is therefore `not_available_under_checked_contract`; the contrasts are not multiplied into an invented end-to-end estimate.

## Current-epoch paired characterization

| workload | n | baseline median (s) | candidate median (s) | median speedup | range | full output | fallback/overflow |
|---|---:|---:|---:|---:|---:|---:|---:|
| c5_archive_h19_2mb | 3 | 3.274271 | 2.471505 | 1.324877x | 1.284634-1.337729 | 1 | 0/0 |
| c5_archive_large_synthetic | 3 | 1.719215 | 2.198318 | 0.791882x | 0.782059-0.794431 | 1 | 0/0 |
| c6_exact_h19_2mb | 3 | 2.521849 | 2.332665 | 1.082711x | 1.055717-1.086287 | 1 | 0/0 |
| c6_exact_kcnq_segment_chr22 | 3 | 50.558675 | 45.297502 | 1.115307x | 1.102467-1.125012 | 1 | 0/0 |

## Archive-first and bounded merge

The 2 Mb H19 archive reduced materialized bytes by 5.715078x. Median archive run wall was 2.471505 s, restore wall was 0.257280 s, and explicit run-plus-restore wall was 2.739144 s (1.195362x versus legacy text generation). Restored output was byte-identical in all three pairs.

For the 150,000-row exact merge, SQLite reduced peak RSS by 33.62% (43868 to 29120 kB) while increasing median merge wall from 1.186355 to 1.654937 s. This is a bounded-memory trade-off, not compute acceleration.

## Exact-column component

| workload | exact stage baseline/candidate (s) | stage speedup | stage share baseline/candidate | end-to-end speedup | work/requests |
|---|---:|---:|---:|---:|---:|
| c6_exact_h19_2mb | 0.329091/0.243855 | 1.348059x | 0.1304/0.1050 | 1.082711x | 1/1 |
| c6_exact_kcnq_segment_chr22 | 7.822270/4.734280 | 1.651694x | 0.1547/0.1049 | 1.115307x | 1/1 |

Stage speedup is reported separately from end-to-end speedup. Exact task, cell, GASAL2 request, and traceback request counts were unchanged in all exact-column pairs.

## Resource boundary

| resource | workers/GPUs | device peak/total/headroom (MiB) | host RSS (kB) | pinned host | OOM | status |
|---|---:|---:|---:|---:|---:|---|
| phase4_c5_archive_h19_2mb | 1/1 | 19769.0/24564.0/4795.0 | 862552.0 | NA | 0 | clean |
| phase4_c5_archive_large_synthetic | 0/0 | NA/NA/NA | 29264.0 | NA | 0 | clean |
| phase4_c6_exact_h19_2mb | 1/1 | 19697.0/24564.0/4867.0 | 830284.0 | NA | 0 | clean |
| phase4_c6_exact_kcnq_segment_chr22 | 1/1 | 14999.0/24564.0/9565.0 | 871836.0 | NA | 0 | clean |
| historical_two_slot_workers_1 | 1/1 | 19746.0/NA/NA | 1346088.0 | NA | 0 | clean |
| historical_two_slot_workers_2 | 2/2 | 39492.0/NA/NA | 2124556.0 | NA | 0 | clean |
| historical_two_slot_workers_4 | 4/2 | NA/NA/NA | NA | NA | 1 | oom |
| historical_two_slot_workers_6 | 6/2 | NA/NA/NA | NA | NA | 1 | oom |

Current-epoch GPU peaks use 250 ms `nvidia-smi` device-used samples and host RSS uses `/usr/bin/time -v`. Pinned-host peak is unavailable in current telemetry. Historical workers=4 and workers=6 OOM evidence is retained rather than rerun; the supported density remains one GASAL2 worker per 24 GB GPU.

technical failure receipts: 0

Machine-readable authority:

- `paper/source_data/ablation_resource_runs_pre_freeze.tsv`
- `paper/source_data/ablation_resource_pairs_pre_freeze.tsv`
- `paper/source_data/ablation_resource_summary_pre_freeze.tsv`
- `paper/source_data/ablation_linked_contrasts_pre_freeze.tsv`
- `paper/source_data/resource_boundary_pre_freeze.tsv`
- `paper/source_data/ablation_resource_failures_pre_freeze.tsv`
- `paper/phase4_artifact_manifest.tsv`
