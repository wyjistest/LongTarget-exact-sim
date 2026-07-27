# Modified SSW Endpoint Contract

Status: Phase 0 skeleton; exact scan and tie semantics are pending Phase 2.

The forward endpoint contract is L3:

```text
score1
ref_end1
read_end1
score2/ref_end2 when observable in the frozen call chain
```

The reverse-start contract is L4:

```text
ref_begin1
read_begin1
reverse score
reverse endpoint and ordered tie key
```

Phase 2 must derive scan direction, first-hit behavior, and every ordered tie
field from the frozen CPU source. Phase 5 provides only L1/L2; no component may
claim a GPU forward endpoint until the independent Phase 6 L3 gate passes.
