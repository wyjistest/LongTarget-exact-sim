# Phase 1 Validation Receipt

```text
checked_at = 2026-07-24
submission_software_epoch = 1
paper_runtime_epoch = 0
paper_runtime_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
runtime_behavior_change = 0
```

## Automated contract tests

Command:

```bash
python3 tests/check_gasal2_longtarget_cli.py
```

Result: 31 tests passed. The suite covers CPU authority, default safe routing,
no-GPU authority selection, verified clean publication, mismatch fallback,
candidate OOM/failure fallback, explicit experimental warning, query-length
guard, multi-record rejection, malformed and non-UTF-8 FASTA, unsupported
contract, output collision, dry-run, shared recursive JSON Schema validation,
spaces and shell metacharacters, relative paths, interruption cleanup,
comparator timeout/abnormal exit, missing/inconsistent/fabricated details and
invalid metrics, empty/structurally or semantically malformed backend output, canonical
top-5 publication, experimental-native output labelling, nested schema
rejection, checker workspace safety, score-only contract behavior, help and
version.

The fake backends require the same pre-existing `-O` directory as Fasim and
write current 19-column TFOsorted fixtures. Verified tests invoke the real
`scripts/compare_fasim_segmented_contract.py` implementation.

## Real binary smokes

The CPU Fasim authority was rebuilt with `make build-fasim`. The bundled
`H19.fa` / `testDNA.fa` workflow completed with:

```text
result_status = authority_complete
published_source = authority
TFOsorted outputs = 1
```

A local diagnostic, not retained as submission evidence, used the current
aggregate-built GASAL2 binary and observed:

```text
result_status = candidate_clean
published_source = candidate
score_top5_equal = 1
stability_top5_equal = 1
nt_top5_equal = 1
fallback = 0
```

The real CPU smoke and reproducible automated verified fixtures are the Phase 1
gate evidence. The local GPU observation is recorded only as a development
diagnostic because its ignored temporary report is not frozen. None of these
are performance measurements or a promoted contract. No Phase 2 holdout or
Phase 3 application benchmark was started.

## Gate summary

```text
single documented user entrypoint = 1
default mode fail-closed = 1
verified mismatch publishes authority = 1
fast-experimental explicit opt-in = 1
run report validates against schema = 1
atomic output tests pass = 1
historical aggregate check still passes = 1
core runtime behavior change = 0
```

Formal gate command: `make check-bioinformatics-phase1` (exit 0 on 2026-07-24).
