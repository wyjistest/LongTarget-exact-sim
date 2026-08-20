# Long-query scoreInfo state-layout dependency audit v1

## Scope

This is a CPU-only dependency audit for the main legacy-byte scoreInfo
recurrence. It does not launch CUDA, change a runtime flag, modify the active
full-concat AB/BA shadow, or authorize a production kernel.

The implementation is bound to:

```text
443d32ee68865d4df96fd029f70cfdaf4f5a6530
```

## Contract

The model mirrors `prealign_cuda_column_max_legacy_byte_batch_kernel`:

```text
active lanes                 16
profile scores               -4, 0, 5
bias                          4
gap open                     16
gap extend                    4
Lazy-F comparison             signed int8
maximum Lazy-F passes        16
```

It compares the complete per-column H/E state and column maximum under three
layouts:

```text
current:       int16 E + int16 H0 + int16 H1
candidate A:   uint8 E + uint8 H0 + uint8 H1
candidate B:   uint8 E + one in-place uint8 H
```

## Value-range closure

Starting from zero state, monotone bound iteration reaches a fixed point after
252 iterations:

| Value | Closed range |
| --- | ---: |
| transient saturating add | -4 to 255 |
| diagonal after bias | 0 to 251 |
| stored H | 0 to 251 |
| opened gap | 0 to 235 |
| stored E / register F | 0 to 235 |

Therefore the existing byte recurrence never needs more than one byte for a
persisted H or E value. The all-match case also observes the transient
sat-add value 255 and a persisted H value of 251, so the upper boundary is
exercised rather than inferred only from low-score random inputs.

This closes the storage-width dependency for candidate A. It does not prove
that a particular CUDA implementation preserves output ordering, shared-memory
bank behavior, or wall time.

## H dependency

The current column loop reads the previous column tail before any H write. At
each segment it then loads `oldH`, writes the new value at that same offset,
and carries the saved `oldH` in a register to the next segment. After the main
pass, Lazy-F reads and updates only the new column.

The audit models that order independently with one in-place H array. It matches
the double-buffer reference for every complete E/H trace in the bounded panel.
This supports candidate B as a later CUDA shadow, but it is not a formal proof
of compiled warp behavior and does not authorize combining it with candidate A
in the first performance experiment.

## Differential panel

```text
cases                                      6
target columns                         1,076
uint8 three-state mismatches               0
uint8 in-place mismatches                  0
sat-add 255 observed                     yes
```

The panel includes all mismatch, all padding, an all-match byte-ceiling case,
and deterministic random inputs with 1, 3, and 17 striped segments. Exact trace
digests are stored in `audit.json`.

## Decision

```text
uint8 three-state dependency audit     PASS
uint8 in-place dependency audit        PASS_BOUNDED_CPU_MODEL
CUDA implementation                    NOT_AUTHORIZED_BEFORE_NCU_AND_SHADOW
production authorization               false
```

The corrected resource model predicts that candidate A reduces the 11,498 nt
main scoreInfo shared footprint from 34,560 B to 17,280 B and raises the static
residency ceiling from two to five blocks per SM. That makes it the first CUDA
candidate after hardware profiling. Candidate B would reduce the footprint to
11,520 B and eight blocks per SM, but it should be evaluated only after the
storage-width-only candidate establishes an exact baseline.

Reproduce the audit with:

```bash
make check-long-query-scoreinfo-state-layout-audit-v1

python3 scripts/audit_long_query_scoreinfo_state_layout_v1.py \
  --source-commit 443d32ee68865d4df96fd029f70cfdaf4f5a6530 \
  --output docs/long_query_scoreinfo_state_layout_audit_v1/audit.json
```
