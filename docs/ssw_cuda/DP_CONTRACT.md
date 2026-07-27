# Modified SSW DP Contract

Status: Phase 0 skeleton; field-level semantics freeze is pending Phase 2.

The only semantic authority is the CPU call chain frozen at
`9f87aace6d96cf8142e3816299f04defae5710e4`. The source and binary identities
are recorded in `paper/ssw_cuda/source_inventory.tsv` and
`paper/ssw_cuda/runtime_epochs.json`.

Phase 2 must replace this skeleton with source-derived definitions for the
local affine recurrence, zero floor, substitution matrix, gap-open/extend
interpretation, byte-first/word-recompute behavior, and the exact observable
per-reference-column maximum vector. No CUDA implementation is authorized by
this skeleton.

The contract layers are fixed as follows:

```text
L0 = encoded inputs and parameters
L1 = final per-reference-column maxima
L2 = stable retained-attempt descriptors
```

All scores and tie keys are exact integers. Floating-point tolerance, reduced
precision, and result-specific exceptions are outside the program.
