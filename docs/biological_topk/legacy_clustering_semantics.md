# Legacy Clustering Semantics

## Authority

The normative source is `fasim/Fasim-LongTarget.cpp:29089-29179`. The exact
Python reproduction is `reproduce/biological_topk/contract.py:123-189` and its
golden cases are `paper/biological_topk/legacy_clustering_fixtures.tsv`.

## Row eligibility and axis

A row participates only when `Nt(bp) > 50`. Values 49 and 50 are excluded; 51
is included. For an included row, the positive-coordinate midpoint is:

```text
middle = int((raw_QueryStart + raw_QueryEnd) / 2)
       = (raw_QueryStart + raw_QueryEnd) // 2
```

This is the query/TFO axis. Target and genome coordinates do not affect cluster
membership. Input order is significant because the legacy vector is scanned in
order.

## Exact procedure

With `dd=15`, each eligible midpoint creates or updates `axis_map[middle]` and
touches every map position from `middle-dd` through `middle+dd`. Nonzero
offsets add the triangular weight `dd-abs(offset)`. The first maximum is kept:
the comparison is strict `>` and an equal later weight does not replace it.

The selected center assigns every still-unassigned row whose midpoint lies in
the inclusive center window. Those map positions are erased. The legacy rescan
then evaluates integer indexes from zero while `i < axis_map.size()`. C++
`map::operator[]` inserts missing positions during that scan, so the map size is
dynamic. The reproduction preserves this behavior; replacing it with a sorted
key scan, DBSCAN, connected components, or a simple midpoint grouping changes
the contract.

Numeric `Class` from an input artifact is ignored. Motif/class IDs and centers
are recomputed within each arm. Strict maximum ties, midpoint parity, motif
assignment order, and the 49/50/51 boundary are frozen by the TSV fixture.

Only nonzero recomputed motifs become candidate-site clusters. Numeric motif
IDs are arm-local and are never cross-arm equality keys.
