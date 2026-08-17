# Frozen Development-Contract Mismatch Analysis

## Scope and provenance

This report is a deterministic decomposition of the immutable `paper-data-v1-dccfd49-20260716` development evidence. It reads `paper/source_data/generalization_workloads_pre_freeze.tsv`, `paper/source_data/generalization_pairs_pre_freeze.tsv`, `paper/source_data/generalization_runs_pre_freeze.tsv`, `paper/source_data/generalization_mismatch_top5_pre_freeze.tsv`, `paper/workload_manifest.tsv`, and `paper/source_data/source_data_manifest.tsv`. Query composition, pair-01 output row counts and primary margins, and all-pair clustered top-five signatures are reconstructed only from files checked against `.paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization/phase3-artifacts.tsv` (manifest SHA-256 `ef16dbbb7250304a46ac28d2584bedfd1186e3497fd7bc8038b3b004edc52b40`). The established comparator uses cluster distance 15, minimum length 50, and its frozen score/stability/Nt ordering.

## Contract results

- **Score gate:** 13/13 score-ranked workloads are clean. The score contract is unaffected by all three preserved mismatches in this development panel.
- **Stability gate:** 11/13 stability-ranked workloads are clean. The mismatches are g02 and g12.
- **Nt gate:** 12/13 Nt-ranked workloads are clean. The mismatch is g09.
- **Joint ranked result:** 10/13 workloads are clean across all three ranked contracts.
- **Full output diagnostic:** 0/13 workloads have full-row equality. Full-row equality fails for 13/13 workloads; this diagnostic is separate from the declared top-five contracts and no missing/extra row is removed.
- **Runtime outcomes:** fallbacks=0, overflow fallbacks=0, OOM=0. Allocation state is `NA` because no allocation-state certificate was recorded in the frozen development evidence.
- **Repeat diagnostic:** g05 candidate full-output digests vary across its three frozen pairs while ranked contract flags remain consistent.
- **Top-five repeat signatures:** baseline stable in 9/9 three-pair workloads, candidate stable in 9/9, and both sides stable in 9/9. Observed repeat-signature variation: none.

g05 has stable baseline and candidate clustered top-five signatures across three pairs despite varying candidate full-output digests. g12 has one frozen pair, so multi-repeat top-five signature consistency is `NA`. The historical repeat contract-status field is retained separately and is not used as a top-five signature result.

## Preserved mismatch positions

The positions below compare full TFO row identities at clustered ranks 1 through 5. A compact identity is the first 16 hexadecimal characters of SHA-256 over the canonical tab-joined TFOsorted row. Mismatch identities are derived from `paper/source_data/generalization_mismatch_top5_pre_freeze.tsv`, and the pair-01 identities are cross-checked against the checksum-verified raw archive.

- `g02_malat1_mid_2048_chr21` / `stability` differs at clustered TFO positions `2,3,4,5`; 3 frozen pair(s), consistency basis `three_identical_frozen_top5_signatures`.
- `g09_kcnq1ot1_3p_2048_chr11` / `nt` differs at clustered TFO positions `5`; 3 frozen pair(s), consistency basis `three_identical_frozen_top5_signatures`.
- `g12_h19_full_chr22` / `stability` differs at clustered TFO positions `2`; 1 frozen pair(s), consistency basis `single_frozen_pair_no_multi_repeat_test`.

For g02 and g09, all three frozen pairs have identical baseline/candidate top-five signatures and identical differing positions, so the observed mismatches are repeat-consistent. G12 has one frozen pair: its signature is internally consistent, but it is explicitly not a multi-repeat demonstration. Comparator tie groups are aggregate diagnostics across all three ranking modes. Comparator ties require equality of the complete score/stability/Nt ranking tuple. The per-rank rank-5/rank-6 fields report only the primary-value margin. A zero primary margin means only that rank 5 and rank 6 have equal primary values. It does not establish a comparator tuple tie or a mechanism.

## Mechanism and guard conclusion

No deterministic, query-independent pre-run or runtime mechanism certificate is established by the frozen telemetry. Query length/composition, boundary margins, output counts, resource telemetry, and repeat behavior are descriptive features of 13 development workloads; they are not mechanism evidence and are not a safety guard. The frozen evidence records no allocation-state certificate, and the observed zero fallback/overflow/OOM totals do not explain the rank-specific substitutions.

No query-name, gene-ID, or sequence-digest allowlist is proposed. This analysis neither promotes a contract nor changes CLI behavior. Promotion, if any, requires the separately preregistered independent holdout and the Phase 2 decision gate.
