# Fasim GASAL2 Direct Lite Archive Convert

This checkpoint evaluates a default-off prototype for reducing the CPU-side
GASAL2 lite + column archive conversion cost.

## Scope

```text
Diagnostic env:
  FASIM_GASAL2_DIRECT_LITE_ARCHIVE_CONVERT=1

Only active when:
  FASIM_OUTPUT_MODE=lite
  FASIM_TFOSORTED_COLUMN_ARCHIVE_PROBE=1
  no full/CIGAR/compact archive output
  no topk-lite collection or shadow consumer output

Not changed:
  default behavior
  GASAL2 scoring or traceback
  candidate selection
  output semantics
  scheduler/runtime policy
```

The prototype keeps the legacy GASAL2 lite + column archive path as diagnostic
authority. It is not a recommended runtime path, and it must not be used for
production output.

## Result

The small chr22 2 Mb fixture is clean:

```text
restored_equal = 1
rows = 8,291
```

The smoke gate is:

```bash
make check-fasim-gasal2-direct-lite-archive-convert
```

This gate is intentionally narrow. It proves the diagnostic path can activate
and restore the small fixture. It does not prove workload-scale equivalence.

However, larger workloads did not pass the equivalence gate. The first direct
row implementation had speed signal but changed the restored row set:

```text
chr22 full:
  legacy rows = 388,820
  direct rows = 388,820
  legacy-only rows = 1
  direct-only rows = 2
  run wall = 65.98s -> 58.76s
  convert wall = 14.51s -> 8.74s

chr1 full:
  legacy rows = 1,577,064
  direct rows = 1,577,065
  legacy-only rows = 2
  direct-only rows = 3
  run wall = 373.30s -> 332.31s
  convert wall = 80.25s -> 47.14s
```

A follow-up sidecar variant reused legacy `convertMyTriplex()` fields and wrote
the archive from sidecar CIGAR ops. It kept the small fixture clean but did not
restore large-workload equivalence or speed:

```text
chr22 full:
  legacy rows = 388,820
  direct rows = 388,819
  legacy-only rows = 1
  direct-only rows = 0
  run wall = 66.29s -> 67.75s
  convert wall = 14.51s -> 17.38s
```

## Non-Determinism Note

Repeated legacy chr22 runs are not byte-identical, although their sorted row
sets matched in one local repeat:

```text
legacy repeat:
  byte equal = 0
  sorted-set difference = 0
  rows = 388,820 / 388,820
```

Large-workload validation should therefore distinguish byte-order differences
from row-set differences. The direct prototype still failed row-set equivalence,
so this does not change the no-go decision.

## Current Implementation State

The checked-in diagnostic path is deliberately not a recommended fast path. It
uses the legacy row semantics where possible and keeps the environment
default-off. It exists to preserve the evidence and prevent this same direct-row
shape from being reintroduced as a performance path without the required gates.

If the diagnostic env is set on unsupported output shapes, it must fail closed
by leaving the legacy path as authority. The path must not be used for
production output.

## Decision

```text
Direct lite/archive convert:
  small fixture clean
  large workload row-set no-go
  not recommended
  keep diagnostic/default-off only

CPU-side next target:
  convertMyTriplex remains the main conversion cost
  further work needs an equivalence-first design
```

Do not promote `FASIM_GASAL2_DIRECT_LITE_ARCHIVE_CONVERT=1` into recommended
runtime until chr22 and chr1 restored row sets match the legacy path.

The replacement design is:

```text
docs/superpowers/specs/2026-06-11-gasal2-equivalence-first-convert-design.md
```

The next implementation should use a new equivalence-first converted-row
builder and shared sort/filter helper, not this direct-row prototype.
