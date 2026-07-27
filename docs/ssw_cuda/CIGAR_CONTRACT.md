# Modified SSW CIGAR Contract

Status: Phase 0 skeleton; canonical traceback semantics are pending Phase 2.

L5 comprises the exact CPU-selected banded traceback representation:

```text
initial and expanded band history
traceback stop condition
packed operation sequence
expanded operation sequence
adjacent-operation merging
CIGAR digest
```

L6 comprises the LongTarget row derived from that alignment, including exact
coordinates, aligned and ungapped sequences, Score, Nt, MeanIdentity,
MeanStability, and canonical row digest.

An equal-score alternative CIGAR is not equal under this contract. Phase 9
must use an independent replay validator that does not call the GPU code under
test.
