# Phase 3 Biological Application Protocol

This protocol freezes the real biological application inputs before any
application backend, pilot, or formal workload is run. The checkpoint status is
`preregistered_not_run`. It is an input and execution preregistration, not an
application result.

## Source authority

The assembly is GRCh38. Transcript sequence and annotation use GENCODE v49
(GRCh38.p14); promoter sequence uses the forward-genomic UCSC hg38 chromosome
FASTA. The four reconstruction sources are fixed as follows:

| Source | Exact URL | Compressed bytes | Upstream MD5 | Compressed SHA-256 | Decompressed bytes | Decompressed SHA-256 |
| --- | --- | ---: | --- | --- | ---: | --- |
| GENCODE v49 lncRNA transcripts | `https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.lncRNA_transcripts.fa.gz` | 37,870,043 | `6d52ea2c72933c864e46a560fe0b5d4c` | `1f04e509309fa74b694ef3cc1e52c1c8173bb0e679f8a22785fa43ecadd28ef4` | 223,740,848 | `4c632018e0198d76fe76471baa5511a1c07af86bf7bab6ce6747edb8d5add5ae` |
| GENCODE v49 annotation | `https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_49/gencode.v49.annotation.gtf.gz` | 93,374,019 | `0ef4a024ea2d35b1b88c12447b0b70b9` | `d6e6fe0515c95b2a8cd36a853c1989cee9115c736c60237c56ae92b9daaaf7c4` | 3,323,462,848 | `ff32fd55c6799b3b94fe10aa17b2b5d4da952fa1de12fe44afadf32e949ec914` |
| UCSC hg38 chr21 | `https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr21.fa.gz` | 12,709,705 | `184df2bd9b812b6e6b6da16c6021369e` | `c979ca1e5065c2521a50773473e0d0cc018fd6f3e9bb3aa90493fe7b45d57d1b` | 47,644,190 | `35c71b68436d1a278ecb6a1e875af3ba4020738a028a7feac769a6d62790ae1f` |
| UCSC hg38 chr22 | `https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz` | 12,255,678 | `41b47ce1cc21b558409c19b892e1c0d1` | `05f9d97d6fbfd08a44ca45b50837ca2ae9c471f35ba79dffec04d2cb5eaaf695` | 51,834,845 | `ce3ee1ca39356238f7aee438a40a88b4f1b9d80b316b263e16fb12402212d10f` |

The development exclusion ledger is 1,761 bytes with SHA-256
`da31259ed67480770ad0d7094a63e9fad772eccc608a45e8fa2730c14ecde2b8`.
The Phase 2 holdout manifest is 17,807 bytes with SHA-256
`9e293b2c3e8d0462e399fe64ff6f684e9c53f7dd428e9c88265b510909cee8c6`.
The source ledger records the exact download commands, terms, redistribution
notes, and `verified` status. Final third-party redistribution approval remains
owner-controlled.

## Frozen selection

The selection seed is
`gasal2-longtarget-phase3-application-v1-20260724`. No biological label,
candidate count, runtime, mismatch, fallback, or application result participates
in selection.

An eligible query is a GENCODE v49 lncRNA transcript on chr1-chr22 or chrX,
contains only A/C/G/T, and is 500-2812 nt long. Development stable gene IDs,
exact gene names, and sequence digests are excluded, followed by Phase 2
holdout stable gene IDs and sequence digests. One transcript per stable gene is
chosen by ascending annotation level, presence of the `basic` tag, descending
sequence length, and full transcript ID. Representatives are ordered by the
SHA-256 of
`selection_seed|stable_gene_id|stable_transcript_id|sequence_sha256`; the first
50 become `aq001` through `aq050`.

Targets are protein-coding GENCODE v49 transcripts on chr21 or chr22. One
transcript per stable gene is chosen by the following ascending priority:
`MANE_Select`, `Ensembl_canonical`, `appris_principal_1`, any other
`appris_principal` tag, `basic`, annotation level, descending transcript span,
and full transcript ID. Plus-strand TSS is transcript start and minus-strand TSS
is transcript end. The -2000/+500 transcription-oriented window is clipped to
chromosome bounds and retained in forward-genomic orientation only when it is
non-empty and canonical A/C/G/T. Retained targets are ordered by chromosome,
TSS, stable gene ID, and transcript ID and become `at0001` onward.

The complete query selection flow is:

| Count | Value |
| --- | ---: |
| Input query records | 197,211 |
| Excluded: missing GTF metadata | 6,132 |
| Excluded: non-lncRNA annotation | 1,038 |
| Excluded: non-primary chromosome | 1,090 |
| Excluded: noncanonical sequence | 0 |
| Excluded: outside 500-2812 nt | 36,692 |
| Validated query candidates before identity exclusions | 152,259 |
| Excluded: development stable gene ID | 171 |
| Excluded: development exact gene name | 0 |
| Excluded: development sequence SHA-256 | 0 |
| Excluded: Phase 2 holdout stable gene ID | 113 |
| Excluded: Phase 2 holdout sequence SHA-256 | 0 |
| Eligible query transcripts | 151,975 |
| Stable-gene representatives | 27,125 |
| Selected queries | 50 |

The complete target selection flow is:

| Count | All | chr21 | chr22 |
| --- | ---: | ---: | ---: |
| Annotation candidates | 668 | 221 | 447 |
| Excluded: empty promoter | 0 | 0 | 0 |
| Excluded: noncanonical promoter | 0 | 0 | 0 |
| Total excluded targets | 0 | 0 | 0 |
| Retained targets | 668 | 221 | 447 |

## Frozen workload scale

The manifest contains 50 queries and 668 targets, for 33,400 query-target
pairs. Selected queries contain 56,381 nt in total and range from 513 to 2,709
nt. Targets contain 1,670,668 bp in total: 221 chr21 promoters and 447 chr22
promoters. The record manifest therefore contains 718 input records.

The manifest SHA-256 is
`e8c5441c36db8fb4ae28492aee20f7e1af5f357148216ef58fae03c7f52c78bc`.
The freeze identifier is
`bioinformatics-phase3-application-v1-e8c5441c`. Every manifest record has
`split=application` and `status=preregistered_not_run`.

There is no positive-control arm and no independent experimental label in this
panel. The application is computational prioritization only. It will not be
used for a known-pair recall or biological-superiority claim.

## Preregistered execution design

Execution remains planned, not run. Every formal pair will use these three
user-visible arms:

- A: `cpu-authority --contract all-ranked-top5`
- B: `fast-experimental --contract auto`
- C: `safe --contract all-ranked-top5`

The Phase 2 decision is `verified_only_contract`. Accordingly, C must include
candidate and authority execution plus comparison for eligible inputs. It may
publish candidate output only after a clean declared-contract comparison;
mismatch or comparator/candidate failure publishes authority output. B measures
experimental candidate capability only and cannot stand in for user-safe C.

Worker density is exactly two. Worker 0 is pinned to GPU 0 and worker 1 to GPU
1, with at most one process per GPU. The complete 50 by 668 panel will run once
in full A, B, and C arm blocks so that each arm has an observed batch makespan.

After the separately committed runner and attempt plan exist, exactly one fixed
first-pair pilot (`aq001` by `at0001`) will run A, B, and C once. It is an
operational check and is excluded from all formal source data. It cannot change
the panel, subset, runtime parameters, or claim boundary.

A deterministic 10x20 repeat subset will contain 10 queries spanning the frozen
query-length distribution and 20 targets, with 10 targets from each chromosome.
Only frozen input metadata and the Phase 3 seed may select it. The subset will
receive six AB/BA-balanced paired repeats: even repeats use A-B-C and odd
repeats use C-B-A, yielding three observations in each order. The per-mode
backend timeout is 3,600 seconds.

The fixed application execution budget is 24 hours. The preregistered shape is
one full descriptive run plus the six-repeat 10x20 subset; the scale may not
be reduced after observing runtime, correctness, fallback, candidate output, or
any other result. Result-based scale reduction is prohibited.

There are no automatic or replacement retries, post-start exclusions, or
parameter changes. Every failure, mismatch, fallback, timeout, OOM, return
code, and partial artifact is retained. Any later adjudicated supplemental run
must be additive and cannot replace a primary attempt.

The primary B3 claim, if supported after formal analysis, must use the complete
safe C pipeline and its final contract-safe output. Candidate-only B speedup
cannot establish, rescue, or be reported as a B3 widening claim. Until the
runner checkpoint and formal execution are complete, Phase 3 and B3 remain
pending and this application remains `preregistered_not_run`.
