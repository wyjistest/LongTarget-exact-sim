# Independent Experimental Benchmark Specification

This Phase 5 freeze contains five distinct primary lncRNA outer units and one
ChIRP dataset per unit. All source labels, query identities, target regions,
negative matches, tool bindings, endpoint definitions, and resampling rules
were fixed before any evaluation prediction.

Each dataset has exactly 100 positive and 900 negative 4097-bp GRCh38 windows.
Author peaks are selected by deterministic input-only hash ranking after unique
center liftOver. LINC01116 positives are the strongest 100 eligible fixed bins
under the frozen two-replicate versus Input/LacZ normalized 8x rule. Negatives
are on the same chromosome as their matched positive, differ in GC fraction by
at most 0.05, do not overlap any eligible source-positive window or blacklist,
contain no N, and do not overlap another selected region in that dataset.

Region IDs are label-blind and FASTA order is ascending region ID. Because the
frozen Fasim interface reads only the first target FASTA record, each dataset's
target is one record containing the ordered regions separated by 4097 Ns. The
manifest freezes every region's concatenated offset. The analyzer rejects any
row not wholly contained in one region. Prediction backends receive only query
and target FASTA files; they do not receive the experimental manifest. Labels
are read only by the offline analyzer after all 15 A/G/X attempts are terminal.

For A and G, the primary region score is the maximum exact integer Score among
valid emitted rows with Nt(bp)>50. A region with no valid row receives -1. The
emission source filters at scoreMin=0, so -1 is strictly below the legal emitted
minimum. Ties are ordered by the fixed region ID. X is an external diagnostic
and is not substituted for either primary arm.

Per dataset, the primary metrics are AUCPR, recall@P_d, precision@P_d,
prevalence, and natural-log top-P enrichment, where P_d=100. Dataset values are
aggregated equally within lncRNA and then equally across the five distinct
lncRNAs. Here each lncRNA has one primary dataset.

All four endpoints use the same 10,000 paired hierarchical bootstrap indices,
seed 20260816, and an inverted-CDF one-sided 5th percentile lower bound. The
outer unit is lncRNA and the nested block is chromosome. A and G remain paired
at every level. A bootstrap resample with zero top-P precision receives
negative-infinity E4, so it cannot improve the lower bound; no pseudocount,
resample deletion, or replacement is allowed. E1 requires LCB(G-A
AUCPR)>=-0.02, E2 requires LCB(G-A
recall@P)>=-0.05, E3 requires LCB(G AUCPR-prevalence)>0, and E4 requires
LCB(log(G precision@P/prevalence))>0. All four must pass. Any primary dataset
with zero precision forces E4 and the global gate to fail without a pseudocount
or bootstrap replacement.

Only ChIRP met the frozen input/data availability definition. Therefore
cross_assay_generality_claim=not_supported.
