# Experimental Biological Utility Estimand

## Independent question and units

Experimental utility asks whether G predicts independent RNA-DNA occupancy or
binding labels. It is separate from CPU-reference concordance. Historical MEG3,
MALAT1, NEAT1, H19, KCNQ1OT1, and any dataset used in development are excluded
from primary evaluation.

The outer independent unit is a distinct lncRNA. Assays, datasets, replicates,
peak callers, chromosomes, and genomic blocks within one lncRNA are nested and
do not increase outer n. Promotion requires at least five distinct evaluation
lncRNAs, each with at least one eligible primary dataset. If at least two assay
types are input-eligible, the primary panel must cover at least two.

## Query and region score

A primary query is either a complete frozen-annotation isoform within the
operating envelope or a shorter domain fixed before predictions by independent
literature, probe design, functional annotation, or an existing database. Its
citation, transcript, coordinates, rationale, digest, and selection timestamp
must be frozen. Prediction-driven segmentation is forbidden.

For each target region, retain valid rows with `Nt(bp)>50` and define the
primary score as the maximum exact Score. Integral-exact uses the exact integer;
decimal-exact uses the exact Decimal. Phase 5 must prove a below-minimum sentinel
for no-valid-row cases before reading predictions. Ties use fixed target
identity, never labels, and A/G share the same function.

For dataset `d`, let `P_d` be the frozen number of positive regions. Primary
screening recall is `recall@P_d`; AUCPR, prevalence, precision at P, and
fold/log enrichment are also computed per dataset.

## Co-primary endpoints

Dataset values are aggregated equally within lncRNA and then equally across
distinct lncRNAs. All four one-sided 95% lower-bound conditions must pass:

```text
E1: macro_lncRNA(GPU AUCPR - CPU AUCPR) >= -0.02
E2: macro_lncRNA(GPU recall@P_d - CPU recall@P_d) >= -0.05
E3: macro_lncRNA(GPU AUCPR - prevalence) > 0
E4: macro_lncRNA(log(GPU precision@P_d / prevalence)) > 0
```

This is an intersection-union gate with one-sided alpha 0.05 for each
component. Region-count-weighted or pooled analyses are diagnostics only.

If any primary dataset has `precision@P_d=0`, E4 and the global gate fail
automatically: `log_enrichment=null`; no pseudocount, infinity, omission, or
bootstrap substitution is allowed.

## Resampling and preregistration

The paired hierarchical bootstrap resamples distinct lncRNAs, then nested
dataset/assay units, then chromosome or frozen genomic blocks. A/G stay paired
at every level and all endpoints share each resample index. The frozen plan uses
10,000 replicates, seed 20260816, and a one-sided percentile interval. Simulation
inputs and seed 20260815 are recorded in
`paper/biological_topk/experimental_power_simulation_plan.json`.

Phase 1 freezes this estimand but does not inventory or download primary data.
Fewer than five eligible lncRNAs or an unidentifiable one-sided interval blocks
Phase 5; repeated assays cannot repair that deficit.
