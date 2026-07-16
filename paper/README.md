# GASAL2-LongTarget paper evidence package

This directory is the auditable handoff for paper preparation. It is not the
manuscript and it does not promote a new runtime.

```text
paper_runtime_epoch = 0
paper_runtime_commit = 0d11aa2d61b7ccda59b462ab8e0750dad17ee18f
authoritative execution state = goal-final.md
```

Phase 0 freezes scope and inventories existing evidence. Historical values are
starting evidence only. The paper estimates will be recomputed from the paired,
preregistered runs collected by later phases.

Phase 2 core paired receipts are exported without machine-specific absolute
paths to `paper/source_data/*_pre_freeze.tsv`. Their raw authority remains under
`.paper-artifacts/runtime-epoch-0-pre-freeze/phase2-core`, with every file
covered by `paper/phase2_artifact_manifest.tsv`. These tables are pre-freeze
inputs; Phase 5 assigns the final data-freeze ID and bootstrap intervals.

Phase 3 retains all 13 preregistered supported-query workloads and three
full-length guards. Ten workloads are clustered tri-ranking clean and three
repeat-consistent mismatches remain in the source data. The raw authority is
under `.paper-artifacts/runtime-epoch-0-pre-freeze/phase3-generalization`, with
every collected file covered by `paper/phase3_artifact_manifest.tsv`.

Phase 4 adds three current-epoch pairs for each frozen archive and exact-column
workload. It keeps archive run, restore, merge, exact-stage, end-to-end, RSS and
device-memory measurements separate. Existing high-density multi-worker OOM
evidence is reused by digest rather than rerun.

Phase 7 adds a digest-aware input manifest, normalized benchmark environment,
bounded reproduction commands and a CUDA user-space container definition. Its
clean-checkout gate rebuilds the frozen statistics, tables and figures without
accessing raw `.paper-artifacts` or rerunning a GPU benchmark.

Phase 8 provides a claim-mapped outline, checked Methods notes, generated result
source sheet, explicit limitations, verified related-work inventory, BibTeX and
author-owned reporting placeholders. It remains source material rather than a
generated manuscript.

Phase 9 independently rechecks pair, storage and exact-stage arithmetic, scans
claim language, composes all lightweight gates and records the final scoped
decision in `paper/PAPER_PREP_STATUS.md`.

## Layout

```text
paper/scope_and_claims.md       allowed and prohibited claim language
paper/claim_evidence.tsv        C1-C7 claim/evidence ledger
paper/artifact_inventory.tsv    immutable file metadata and provenance
paper/gap_register.tsv          open evidence and reporting gaps
paper/runtime_epoch_log.tsv     runtime freeze history
paper/core_benchmark_report.md  Phase 2 paired benchmark report
paper/phase2_artifact_manifest.tsv  Phase 2 raw/derived digest inventory
paper/generalization_report.md  Phase 3 generalization and guard report
paper/phase3_artifact_manifest.tsv  Phase 3 raw/derived digest inventory
paper/ablation_resource_report.md  Phase 4 ablation/archive/resource report
paper/phase4_artifact_manifest.tsv  Phase 4 raw/derived digest inventory
paper/source_data/              Phase 2-5 machine-readable run data
paper/figures/                  Phase 6 generated vector figures
paper/tables/                   Phase 6 generated tables
paper/supplementary/            Phase 6 supplementary outputs
reproduce/input_manifest.tsv    input provenance and reconstruction commands
reproduce/environment.md        captured environment and protocol limitations
reproduce/benchmark_commands.sh tiered bounded reproduction entry point
paper/clean_checkout_validation.log  expected quick-reproduction receipt
paper/results_claims.md         generated C1-C7 result source sheet
paper/related_work_inventory.tsv verified PubMed/DOI metadata
paper/references.bib            matching checked bibliography
paper/independent_arithmetic_audit.tsv independent ratio/median audit
paper/completion_audit.tsv       Phase 0-9 and final checklist evidence map
paper/PAPER_PREP_STATUS.md      final scoped paper-preparation decision
```

Large raw artifacts are not committed to Git. Later phases freeze them under:

```text
.paper-artifacts/<data_freeze_id>/
```

The inventory records path, size, SHA-256, runtime commit and source class.
An existing `.tmp` file is not treated as permanently archived merely because
it is available in the current workspace.

## Source classes

Only the source classes defined in `goal-final.md` are used:

```text
reproduced_current_epoch
reused_digest_verified
committed_historical_artifact
user_provided_external_result
unavailable
```

Unknown author, affiliation, funding, citation, input provenance or external
archive metadata remains in `paper/gap_register.tsv`; it is never guessed.

## Phase 0 check

```bash
make check-fasim-gasal2-paper-phase0
```

This composes the completed long-query final gate with the paper scope,
provenance, runtime-freeze and claim-language checks.

## Current phase checks

```bash
make check-fasim-gasal2-paper-phase2
make check-fasim-gasal2-paper-phase3
make check-fasim-gasal2-paper-phase4
make check-fasim-gasal2-paper-phase7
make check-fasim-gasal2-paper-phase8
make check-fasim-gasal2-paper-prep
```

The Phase 2-4 checks regenerate tracked reports and pre-freeze source tables
from digest-covered local artifacts. They do not rerun the GPU workloads.
The Phase 7 gate additionally archives the staged tree to a clean temporary
directory and regenerates the frozen statistical summaries and all paper
figures/tables there.
