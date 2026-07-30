# Biological Top-K Scientific Object

## Frozen object

`biological_topk_candidate_site_v1` operates on a clustered TFO/query-target
candidate site. Clustering is performed on the raw query/TFO coordinate axis,
not on target genomic coordinates. A contract object consists of:

1. one cluster produced by the exact legacy `cluster_triplex` procedure; and
2. one query-target representative selected from that cluster under one frozen
   ranking mode.

The machine value is
`clustered_TFO_query_target_candidate_site`. The contract claim is limited to
`set_preservation_with_top1_retention`. It does not assert complete rank-order,
endpoint, CIGAR, strict-row, or full-output equality. Rank order below Top-1 is
a diagnostic only.

## Arms and evidence

Arm A is the complete CPU Fasim authority. Arm G is the isolated GASAL2
candidate screen. The matcher may compare A and G only after all input-identity
fields pass the frozen AND gate. CPU-reference concordance and experimental
biological utility answer different questions and neither substitutes for the
other.

The scientific object excludes backend name, implementation cluster number,
CIGAR, gapped byte identity, row order, and wall time. Those values may remain
as arm-local provenance or diagnostics.

## Claim boundary

The formal wording is "Top-K candidate-site set preservation with Top-1
retention." The following are outside v1: pure genomic-coordinate clustering,
complete ranking equivalence, exact CPU replacement, full-output replacement,
and generality beyond the frozen operating envelope.

The product remains `experimental`. Phase 1 selects no fresh pair and runs no
new A/G prediction.
