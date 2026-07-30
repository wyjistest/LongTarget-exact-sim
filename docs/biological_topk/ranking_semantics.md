# Ranking Semantics

## Numeric tuples

The three machine ranking modes are exactly `score`, `stability`, and `nt`.
Within each arm, the comparator selects the maximum tuple and sorts descending:

```text
score:     (Score,         Nt, MeanStability)
stability: (MeanStability, Nt, Score)
nt:        (Nt,             Score, MeanStability)
```

Score and stability are exact Decimal values and Nt is an exact integer.

After these three numeric components, the complete TFOsorted row tuple is the
descending deterministic fallback. Its column order is the frozen
`TFOSORTED_COLUMNS` order in `scripts/fasim_tfo_archive.py`. Identical full rows
are deduplicated before clustering. The same key selects one representative per
recomputed cluster and then orders cluster representatives; the first five are
Top-K.

## Scope of fallback

The full-row fallback reproduces current within-arm business behavior only. It
must not enter cross-arm biological identity, edge eligibility, edge quality,
or matching tie resolution. Numeric cluster ID and source row index are also
prohibited cross-arm tiebreakers.

If two within-arm rows remain biologically indistinguishable after
implementation-dependent fields are removed but select different records under
the legacy fallback, the candidate site is ambiguous and that ranking fails.
Top-1 retention concerns the first site only. Positions 2 through 5 contribute
to a rank-sensitive diagnostic, not a rank-order claim.

Normative implementation sources are
`scripts/compare_fasim_segmented_contract.py:30-125` for established business
ranking and `reproduce/biological_topk/contract.py:192-210` for exact numeric
parsing.
