# Bioinformatics Submission Readiness v2 Protocol

## Authorization and historical boundary

This is a new, independently authorized submission-readiness epoch rooted at
commit `739ee0a8db01f77143a5c993e6c68a56a772502b`. It does not reopen, amend, or
supersede any historical state machine or decision.

The following historical facts remain immutable:

```text
biological_topk_successor Phase 4 candidate-site concordance = pass
biological_topk_successor Phase 6 biological utility = no_go
biological_topk_successor Phases 7-9 = not_authorized_previous_no_go
canonical-hybrid-v2 correctness = pass
canonical-hybrid-v2 performance = no_go
exact SSW-CUDA route = closed
legacy Bioinformatics route = closed for the latest successor contract
```

The manuscript scope was narrowed after observing the Phase 6 E4 result. This
is a transparent post hoc scope decision, not a preregistered biological
hypothesis. The new epoch may prospectively validate only the new product,
performance, external-comparison, and release claims defined below.

## Target claim and prohibited claims

The target claim is:

> GASAL2-LongTarget accelerates short-query candidate-site screening while
> highly preserving Fasim-LongTarget Top-K candidate-site sets and Top-1
> candidates, with comparable performance on five ChIRP datasets.

`accelerates` remains unsupported until the exact frozen release candidate
passes Phase 4. The target claim is limited to short queries, candidate-site
screening, the frozen operating envelope, and five ChIRP datasets. It is not a
full-output, CIGAR, strict canonical-row, full-length long-query, cross-assay,
rank-2-to-5-order, biological-superiority, or robust-enrichment claim.

The manuscript must not claim strong biological prediction, high-accuracy
triplex prediction, robust enrichment across lncRNAs, or superior biological
performance. It must state in the main text that Top-P enrichment estimates
were positive in all five datasets but the preregistered cross-lncRNA
lower-bound criterion was not met.

## Four independent identities

The release candidate binds four independent identities:

```text
execution_mode = gpu-screen
scientific_contract = biological_topk_candidate_site_v1
output_schema = gasal2_candidate_sites_tsv_v1
software_epoch = submission_rc_v2
```

Changing any identity cannot silently inherit evidence attached to another.
The scientific contract is reused byte-for-byte from the frozen predecessor.
The output schema and execution mode are new product interfaces. The software
epoch binds the exact source, binary, container, dependencies, defaults, and
scheduling behavior used by formal execution.

## Product requirements

`gpu-screen` is GPU-only. It must not run a complete CPU authority internally,
must not route by query or gene identity, and must fail closed outside the
frozen operating envelope. CPU authority is allowed only as a separate arm in
development regression, offline comparison, and formal benchmark execution.

The release candidate must emit `candidate_sites.tsv` and a schema-validated
JSON run report. Before formal performance execution, the TSV schema freezes:

- query and target coordinate systems;
- 0-based half-open interval semantics;
- strand, direction, and rule encodings;
- canonical candidate-site identity payload;
- score, stability, and nt ranking modes;
- deterministic tie and row ordering;
- the stage at which Top-K truncation occurs;
- header-only empty-result semantics;
- arm-local cluster provenance that is not a cross-arm equality key; and
- schema, scientific-contract, and software-epoch fields.

Phase 1 may label the immutable artifact
`frozen_release_candidate_under_test`; it must retain product status
`experimental` and validation status `pending` until Phase 4 passes.

## Formal performance invariant

Every planned workload and repeat must terminate. Any technical failure,
timeout, OOM, unexpected fallback, missing or malformed output, input identity
mismatch, candidate-site contract failure, or nondeterministic output forces
the complete Phase 4 correctness/performance gate to `no_go`.

The primary validated performance estimand is the 24-hour capacity ratio under
the frozen CPU and GPU resource schedules. A primary estimate is computed only
when all planned rows are technical successes and candidate-site contract
passes. Conditional speed among successful rows is diagnostic only and cannot
appear as the headline result.

For arm `X` in `{A,G}`:

```text
capacity_X_24h = 86400 * validated_work_units_X / scheduled_wall_seconds_X
capacity_ratio = capacity_G_24h / capacity_A_24h
```

The Phase 3 plan must freeze the exact makespan computation. Each bootstrap
replicate resamples paired A/G workloads as the outer unit, retains paired
timing repeats within each sampled workload, replays the frozen CPU and GPU
schedulers, recomputes both makespans, and calculates the replicate capacity
ratio. It must not substitute average workload speedup, median workload
speedup, or independently resampled arm summaries.

The decisive statistical gate is:

```text
one-sided 95% lower confidence bound of validated capacity_ratio >= 10
```

The point estimate must also be at least 10 as an internal consistency check,
not as a second independent inferential endpoint. Median paired speedup,
absolute batch saving, stage timings, and the historical 38.32x anchor are
secondary only.

## Runtime freeze and evidence denominator

Before Phase 4, the epoch freezes the Git commit, binary SHA-256, container
image digest, CUDA runtime, driver compatibility range, dependency versions,
CLI entrypoint and defaults, batching, worker counts, CPU/GPU scheduling,
fallback behavior, output schema, and scientific contract version.

After Phase 4, any runtime-affecting change creates a new software epoch and
requires Phase 4 to be rerun. Documentation-only release commits must bind:

```text
benchmark_source_commit
release_commit
runtime_path_diff_allowlist
```

They must prove that binary and container digests, runtime dependencies, CLI,
schema, contract, batching, scheduling, fallback behavior, and all runtime-path
code are identical to the Phase 4 benchmark object.

## External-method boundary

No formal external comparison is authorized before Phase 4 passes. Development
work may use excluded inputs to install tools, repair wrappers, test parsers,
and freeze semantic mappings without creating claim evidence.

Before any tool is called current state of the art, Phase 2 freezes the search
date, sources, search strings, inclusion and exclusion criteria, task-semantic
compatibility rules, software-availability criteria, versions, releases, and
licenses. PATO is a candidate current executable comparator. Triplexator is a
legacy executable comparator. TripLexicon or TriplexAligner may be landscape
resources unless a fair local runtime and output mapping is established.

The five historical Triplexator failures are output-path/harness compatibility
failures. They are not algorithm failures or scientific performance results.

## State machine

### Phase 0 - epoch authorization and scope

Freeze the independent authorization, baseline, immutable legacy boundary,
post hoc scope statement, state schema, checker, and fixed resource limits. No
runtime or prediction artifact may be created.

### Phase 1 - frozen GPU-only release candidate under test

Implement and freeze `gpu-screen`, the candidate-sites schema, run-report
schema, fail-closed envelope, exact runtime binary/container identity, and
minimum CI. No formal performance claim is produced.

### Phase 2 - excluded development harnesses and method landscape

On inputs excluded from all formal panels, debug CPU/GPU timing, scheduler,
candidate-site output, Triplexator, PATO, parsers, semantic mappings, and
failure handling. Freeze the external-method landscape. No formal claim is
produced.

### Phase 3 - formal preregistration

Freeze a fresh input-only performance panel, repeats, paired order, resources,
schedulers, makespan estimator, paired hierarchical bootstrap, threshold,
failure denominator, comparator bindings, manifests, and budgets. Formal
prediction cannot start before the Phase 3 commit passes its postcommit audit.

### Phase 4 - decisive correctness and capacity experiment

Run separate CPU authority and GPU-only arms using the exact frozen release
candidate. Compare all planned rows offline. Phase 4 has only three terminal
decisions: `performance_pass`, `performance_no_go`, or `blocked`.

Phase 4 passes only when:

```text
release_candidate_frozen
AND planned_rows_total == technical_success_rows
AND planned_rows_total == candidate_site_contract_pass_rows
AND primary_validated_24h_capacity_gate_passed
```

If Phase 4 does not pass, Phases 5-7 are not authorized, the v2 route closes,
`gpu-screen` remains experimental, and the target acceleration claim remains
unsupported.

### Phase 5 - formal external comparison

Authorized only after Phase 4 passes. Run at least one current, executable,
semantically justified comparator on real biological data and retain every
success and failure. Keep native semantics and incomparable fields explicit.

### Phase 6 - release and archive

Authorized only after Phases 4 and 5 pass. Publish the Phase 4 runtime digest,
complete CI, quick start, checksums, license inventory, release-candidate tag,
archive metadata, and owner-controlled DOI fields without inventing identifiers.

### Phase 7 - Application Note and final audit

Authorized only after Phases 4-6 pass. Produce the Application Note,
main-text E4 limitation, claim ledger, availability statement, supplement,
figure, source-data bindings, and final machine audit. Live journal rules and
owner metadata remain explicit owner-only gates.

## Fixed resources and stop-loss

The v2 artifact root is
`.paper-artifacts/bioinformatics-submission-readiness-v2`. New v2 artifacts
have a fixed 64 GiB quota. Phase 3 must set fixed CPU, GPU, wall-clock, and
per-attempt limits within that quota; no threshold or quota is raised after
formal data are observed.

The v2 state machine alone may record
`conditionally_open_performance_gated`. All historical state and evidence
remain read-only and retain their original values.
