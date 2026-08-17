# Phase 2 Holdout Execution Protocol

This supplement was frozen before any pilot or formal Phase 2 execution. It
governs execution of the independent panel in `holdout_manifest.tsv`; it does
not change the selection, runtime, comparator, or publication contracts.

## Frozen execution design

- pilot workload = hq01_ht01
- The pilot identifier is `pilot__hq01_ht01__repeat00`; the pilot is excluded from formal source data.
- Formal execution comprises all 36 primary attempts from all 24 workloads.
  It cannot be subset by query, gene, target, digest, or observed result.
- Each attempt runs CPU authority under `all-ranked-top5`, experimental GPU
  candidate under `auto`, and verified mode under `all-ranked-top5`, all with
  rule 0, top K 5, GRCh38, and GENCODE v49.
- Direct authority and direct candidate raw TFOsorted outputs are compared
  independently with `compare_fasim_segmented_contract.py --k 5 --details`.
- formal execution requires a checksum-valid pilot receipt.
- Production pilot and formal execution are pinned to
  `.paper-artifacts/bioinformatics-phase2-holdout-v1`. The pinned runner is the execution authority for this gate and does not claim to detect manual executions outside the runner.
- Each attempt config binds the runner path, runner SHA-256, and Git HEAD, and
  every mode receives the same explicitly bound comparator path.
- production pilot/formal execution requires a clean tracked and untracked checkout;
  ignored canonical artifacts are permitted, but all other tracked or untracked
  changes fail closed before planning or execution.

## Failure and retry policy

There is no automatic or replacement retry. Any later supplemental retries are additive and cannot replace a primary attempt; all technical failures, mismatches, fallback, OOM and timeout outcomes remain represented. A mode failure never suppresses either of the other two top-level modes.

Attempts are built in partial directories and atomically published to
immutable destinations. Resume is permitted only when the configuration,
complete receipt, and every retained artifact checksum validate. Missing or
altered artifacts fail closed.

stale primary-attempt partials require manual adjudication. The partials are
preserved exactly and never cleaned, replaced, or automatically rerun. Any later
adjudicated retry remains additive and cannot replace the primary attempt.

## Analysis boundary

runtime parameters may not change after pilot or holdout results. The pilot
may identify operational readiness but cannot create a query, gene, target,
digest, or result allowlist and cannot tune the runtime. Formal primary
attempts remain the preregistered analysis basis regardless of outcome.
