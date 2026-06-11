# Fasim GASAL2 Archive-First Output

This checkpoint adds a default-off archive-first output mechanism for the
GASAL2 path.

## Scope

```text
Env:
  FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT=1

Initial behavior:
  - supported only for FASIM_OUTPUT_MODE=tfosorted
  - writes a reference-backed `.archive-first.tfoa`
  - does not write full `.TFOsorted` text in the fast path
  - restores full `TFOsorted` with the existing column archive restore schema

Not changed:
  scoring
  traceback selection
  candidate selection
  sort / unique / filter semantics
  default output behavior
```

This is not a full `aligner.Align()` replacement and it does not promote GASAL2
endpoint, CIGAR, score, or digest authority. It only changes the runtime output
artifact when explicitly requested.

## Smoke Gate

```bash
make check-fasim-gasal2-archive-first-output
```

The gate runs the small chr22 2 Mb fixture twice:

```text
legacy:
  FASIM_OUTPUT_MODE=tfosorted

archive-first:
  FASIM_OUTPUT_MODE=tfosorted
  FASIM_GASAL2_ARCHIVE_FIRST_OUTPUT=1
```

It requires:

```text
archive_first_requested = 1
archive_first_active = 1
archive_first_decision = active
no full TFOsorted text emitted by archive-first run
restored TFOsorted byte-identical to legacy
legacy_only_rows = 0
archive_only_rows = 0
```

Current small-fixture result:

```text
restored_equal = 1
rows = 8,291
legacy_run_wall_seconds ~= 3.28
archive_run_wall_seconds ~= 2.36
restore_wall_seconds ~= 0.25
legacy_text_bytes = 1,836,889
archive_bytes = 321,411
archive_gzip_bytes = 133,990
```

## Large-Workload Gate

Large GASAL2 runs can be byte-order nondeterministic, so use sorted row-set
comparison:

```bash
COMPARE_MODE=set \
TARGET=.tmp/characterize_fasim_gasal2_gpu_scoreinfo_utilization_full_chr22/input/chr22.fa \
WORK=.tmp/characterize_fasim_gasal2_archive_first_output_chr22 \
make check-fasim-gasal2-archive-first-output
```

The large gate is clean only if:

```text
legacy_only_rows = 0
archive_only_rows = 0
restored_equal = 1
```

Speed should not be interpreted before the row-set gate is clean.

## Decision

```text
Archive-first output:
  mechanism smoke clean
  default off
  restore-on-demand full TFOsorted

Next:
  chr22/chr1 sorted row-set characterization
  then typed-builder refactor if row-set gates remain clean

Do not claim:
  full GASAL2 aligner replacement
  output equivalence on large workloads before set gates
  final archive format
```
