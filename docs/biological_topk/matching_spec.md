# One-to-One Matching Specification

## Preflight and eligible edges

Matching starts only after the full A/G input-identity AND gate passes. For an
A site and G site to share an edge, all exact categorical fields must match:
input pair digest, chromosome or target ID, Direction, Strand, and Rule.

The representative query interval, cluster query span, and representative
target interval must each have reciprocal overlap at least `9/10`, where:

```text
overlap = intersection_length / max(length_A, length_G)
```

Eligibility uses integer cross multiplication. No binary float is used.

## Exact matching objective

For every complete one-to-one pair set, compare this aggregate vector
lexicographically:

1. matched edge count, maximize;
2. sum of target overlaps as exact Fractions, maximize;
3. sum of representative-query overlaps as exact Fractions, maximize;
4. sum of cluster-span overlaps as exact Fractions, maximize;
5. count of equal ungapped TFO digests, maximize;
6. count of equal ungapped TTS digests, maximize;
7. target endpoint L1 sum, minimize;
8. query endpoint L1 sum, minimize; and
9. cluster-center distance sum, minimize.

Score, Nt, stability, cluster ID, row order, backend, CIGAR, and strict-row
digest are prohibited matching tiebreakers. If distinct pair sets have the same
complete objective, `ambiguous_one_to_one_matching=1`; recall, precision,
Top-1 retention, complete-set success, and ordered diagnostic are all zero.

## Workload output

Each workload/ranking reports A and G counts, matched and unmatched counts,
recall, precision, Top-1 retention, complete-set preservation, ambiguity, the
exact objective, per-edge overlaps, rank displacement, numeric deltas, and the
strict-row diagnostic.

Binary success requires a denominator-eligible, technically valid,
unambiguous, nonempty A workload with every A and G site matched, equal A/G
counts, recall and precision one, and A rank 1 matched to G rank 1. An extra G
site fails precision and complete-set preservation. The exact implementation is
`reproduce/biological_topk/contract.py:321-469`.
