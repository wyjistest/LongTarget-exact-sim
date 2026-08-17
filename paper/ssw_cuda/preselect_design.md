# Phase 5 Exact SSW-CUDA Preselection Design

## Scope and claim boundary

Phase 5 implements only L1 and L2 of the frozen modified-SSW contract:

```text
L1 = final per-reference-column maxima
L2 = stable scoreInfo and threshold/best/last selection
```

It does not implement or claim a forward endpoint, reverse start, traceback,
CIGAR, emitted-row equality, safe application acceleration, or a fresh-holdout
promotion. The CPU SSE2 implementation remains the sole authority and the
default Fasim build does not link this backend. The Bioinformatics B3 track
remains closed by the Phase 1 Amdahl gate.

## Reference kernel

The first in-tree CUDA implementation assigns one complete task to one GPU
thread. This is a correctness checkpoint, not the final scheduling design.
All DP state is stored as exact `int32` values. The implementation explicitly
reproduces the observable SSE2 striped execution rather than substituting the
diagnostic scalar recurrence:

- 16 byte-path lanes and 8 word-path lanes;
- the frozen query stripe and padding layout;
- unsigned byte saturation and bias 4;
- nonnegative gap subtraction;
- E/F/H update order;
- lazy-F propagation without an E update;
- the byte path's signed lane comparison in its lazy-F stop test;
- padded-lane participation in the recorded column maximum;
- byte-first and full word-recompute decision semantics.

The initial smoke implementation used the conceptual scalar affine recurrence.
`adv-periodic-repeat` exposed its first difference at reference column 7:
CPU 35 versus scalar 25. The single mechanism repair replaced that recurrence
with the frozen striped observable semantics. No case identity, digest, gene,
query, target, allowlist, or result-dependent branch exists in production code.

## Deterministic L2 compaction

Selection is performed on device in three explicit kernels:

```text
strict threshold and run-maximum flags
-> per-task stable exclusive scan
-> stable scatter in reference-column order
```

A run continues only when consecutive retained positions differ by 1-4 nt.
Strictly larger scores replace the run winner; equal scores retain the first,
lowest reference coordinate. There is no atomic winner and no dependence on
block completion order.

The pure downstream attempt selector preserves group and attempt order. It
selects the first threshold success, otherwise the strictly best terminal
fallback, otherwise the final nonzero attempt. Nonselected observations remain
auditable and no automatic or replacement retry exists.

## Fail-closed boundary

The CUDA entry point rejects empty batches, empty sequences, translated bases
outside 0-4, negative thresholds, query lengths above 2,812, references above
1,048,576, non-frozen scoring, invalid devices, cell-capacity overflow, CUDA
allocation failure, and CUDA runtime failure. A non-CUDA build links
`ssw_cuda_stub.cpp`, reports `not_built`, and never executes a CPU fallback
under the CUDA backend name.

## Frozen formal matrix

The committed attempt plan is
`paper/ssw_cuda/preselect_attempt_plan.tsv`. It contains 29 non-retry batch
attempts:

| Evidence block | Unique cases | Repeats / GPUs | GPU task executions |
| --- | ---: | ---: | ---: |
| Tiny exhaustive | 196 | 1 | 196 |
| Compact adversarial | 30 | 1 | 30 |
| Compact deterministic fuzz | 128 | 1 | 128 |
| Frozen hq10/hq11 calls | 2 | 1 | 2 |
| Large deterministic/adversarial | 267 | 1 | 267 |
| Determinism subset | 16 | 10 | 160 |
| Same-model cross-device subset | 16 | 2 GPUs | 32 |
| **Total DP task executions** |  |  | **815** |

Four additional generated corpus cases must fail closed before DP. Eight
capacity/configuration/OOM probes test the CUDA API boundary, while a separate
preflight probe tests the non-CUDA stub. The primary L1/L2
contract therefore contains 623 supported DP tasks plus four frozen
unsupported inputs.

The 112 historical identity rows and ten historical annotations without a
bounded executable L1/L2 payload are checked as frozen identities, not silently
invented workloads. The exact hq10 rule-5/strand-0 and hq11
rule-12/strand-1 transformed calls are reconstructed from their frozen inputs;
their CPU column digests must remain `4cdb83f5d1b579b4` and
`fcd5135e90526dfa`.

Thresholds use only the static score upper bound and lengths:

```text
min(65, 5 * min(query_length, reference_length) - 1)
```

The two historical calls retain their frozen thresholds, 65 and 80. No output
is inspected to choose a threshold or a case.

## Budgets and execution discipline

```text
mechanism repair iterations <= 3
observed mechanism repair iterations before formal run = 1
GPU budget <= 24 hours
retry policy = none
large formal batch timeout = 1800 seconds
all other DP batch timeouts = 300 seconds
```

Code, plan, budget, tests, runner, and checker must be committed and the worktree
must be clean before `--run-formal`. Every attempt receives an independent,
non-overwriting artifact root with input, stdout, stderr, GNU-time resource
log, receipt, and checksummed artifact manifest. No `50 x 668` biological
application panel belongs to Phase 5 or is authorized by this design.
