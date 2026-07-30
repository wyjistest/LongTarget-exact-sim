# Source Universe Specification

## Frozen inputs and construction

The universe is rebuilt input-only from GENCODE v49/GRCh38 transcript FASTA and
GTF plus GRCh38 chromosome 21 and 22 FASTA sources. Source SHA-256 values,
annotation release, assembly, parser identity, gzip and uncompressed TSV
digests are in `paper/biological_topk/source_universe_receipt.json`.

One representative transcript per stable lncRNA gene is emitted with a stable
namespace and source ordinal. Each row records transcript/gene identities,
biotype, chromosome status, sequence length and SHA-256, GC and static
complexity proxies, operating-envelope eligibility, and historical exclusion.
The build produced 27,139 rows, with 27,060 fresh unique sequence digests and
27,081 fresh namespaced ordinals.

## Target strata

Each annotation-defined chr21/chr22 anchor has a forward-genomic window centered
on its TSS, clipped only by the frozen recipe's deterministic boundary rule:

```text
short:  grch38_tss_centered_4097_v1       (4,097 bp)
medium: grch38_tss_centered_2000001_v1    (2,000,001 bp)
large:  grch38_tss_centered_10000001_v1   (10,000,001 bp)
```

The namespaces are recipe-specific. Fresh unique target digests are 666 short,
618 medium, and 539 large, exceeding quotas 60, 59, and 59. Different fixed
lengths also separate identities across strata.

## Exclusion and later selection

`paper/biological_topk/fresh_input_exclusion_registry.tsv` covers all historical
paper, development, holdout, debug, adversarial, exhaustive, and deterministic
fuzz identities. Later fresh selection must reject any match on query digest,
namespaced query ordinal, target digest, namespaced target ordinal, pair digest,
or development experimental accession. There is no override.

Rule and output Strand are post-run values and cannot be selection strata.
Their eventual coverage is report-only. Technical repeats do not add
independent sample size. Phase 1 freezes the universe and capacity only: it does
not choose a pair, produce a manifest, or run a prediction.

The deterministic builder is
`reproduce/biological_topk/build_source_universe.py`; the frozen outputs are
`query_source_universe.tsv.gz` and `target_source_universe.tsv.gz`.
