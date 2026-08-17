# Phase 2 Independent Holdout Protocol

This protocol was fixed on 2026-07-24 before any holdout execution. It is a
correctness holdout, not a performance tuning panel and not a biological
discovery study.

## Source authority

- Query annotation and transcript sequences: GENCODE v49, released on
  GRCh38.p14 and described as Ensembl 115 in the GTF header.
- Target reference sequence: the forward genomic orientation of the UCSC hg38
  per-chromosome FASTAs. Ensembl REST `info/assembly/homo_sapiens` was checked
  on 2026-07-24 and returned GRCh38 as the default coordinate system.
- Exact URLs, upstream MD5s, local sizes, SHA-256 digests, terms and download
  commands are frozen in `paper/bioinformatics/holdout_sources.tsv`.
- GENCODE states that its project data are open access. Owner review of final
  third-party redistribution wording remains required before release.

## Query selection

The fixed seed is
`gasal2-longtarget-phase2-holdout-v1-20260724`. Only GENCODE lncRNA
transcripts mapped to primary chromosomes, containing canonical A/C/G/T and
having length 200-2812 nt are eligible. H19, MALAT1, NEAT1, KCNQ1OT1 and MEG3
are excluded by stable gene ID and gene name. The eleven unique normalized
sequence digests covering all 13 development workloads are also excluded.

One transcript is selected per gene by ascending annotation level, presence of
the `basic` tag, descending eligible transcript length and transcript ID. The
representative genes are partitioned into `<=800`, `801-1600` and `1601-2812`
nt strata. The seeded SHA-256 ordering selects exactly 4 / 4 / 4 genes. No
runtime, mismatch, candidate-count or biological-result field participates in
selection.

## Target selection

Protein-coding GENCODE gene features on primary chromosomes are eligible,
except chr11, chr21 and chr22, which contain the historical development target
scopes. Genes are ordered by the same fixed seeded SHA-256 rule; the first two
on distinct chromosomes are selected. Promoters are fixed as strand-aware TSS
windows from -2000 through +500 bp, materialized in forward GRCh38 genomic
orientation. This produced the ALDH4A1 chr1 and UNC13B chr9 scopes. Both are
2,501 bp and canonical A/C/G/T.

## Frozen execution matrix

The 12 queries crossed with two targets produce 24 workloads in
`paper/bioinformatics/holdout_manifest.tsv`. Every workload runs the Fasim
authority, the GASAL2 candidate and the Phase 1 CLI in `verified` mode. All 24
receive one complete comparison. The first seeded query in each length stratum
(`hq01`, `hq05`, `hq09`) on both targets is the six-workload representative
subset and receives three complete repeats.

Score-, stability- and Nt-ranked clustered TFO1-TFO5, boundary ties, full-row
diagnostics, candidate/authority row counts, fallback, guard, OOM and timeout
state are retained. No workload may be removed after execution for mismatch,
failure, runtime or output characteristics. Technical failures remain explicit
rows and are rerun only under the predeclared retry rule with both attempts
retained.

The workload is computational prioritization only. No known-pair recall or
biological superiority claim will be made because no independent experimental
label is attached to this selection.

## Freeze

The manifest SHA-256 is
`9e293b2c3e8d0462e399fe64ff6f684e9c53f7dd428e9c88265b510909cee8c6`,
also recorded in `paper/bioinformatics/holdout_manifest.sha256`; the freeze identifier is
`bioinformatics-phase2-holdout-v1-9e293b2c`. The selection JSON, exclusions,
builder, fetcher, source ledger, derived FASTAs and manifest are committed
before any holdout execution. Contract registry entries remain `experimental`
until every preregistered row is represented and the Phase 2 decision is made.
