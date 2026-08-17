# SSW-CUDA Fresh-Holdout Policy

## Status and scope

This policy is frozen in Phase 3 before any new SSW-CUDA dynamic-programming
kernel is implemented. It governs the independent correctness holdout in
Phase 11. Phase 3 freezes only policy, identities, generators, and offline
comparators; it does not select or execute that holdout.

The product contract is L1-L7. L8 full-output equality remains
`diagnostic_only` throughout this program and cannot be promoted by a holdout
result.

## Freeze order

The following order is mandatory:

1. Freeze the differential corpus, comparator, and this policy.
2. Implement and freeze the full-GPU backend commit.
3. Select a holdout from pre-execution metadata only.
4. Run the overlap checker before any holdout execution.
5. Commit the holdout manifest, commands, checksums, runtime commit, and
   selection receipt.
6. Execute the frozen holdout without tuning, replacement, or retry.

Selection before step 2, or execution before step 5, invalidates promotion
evidence. A failed overlap check cannot be waived manually.

## Authoritative exclusion registry

Every selection must load:

```text
paper/ssw_cuda/used_input_exclusion_registry.tsv
paper/ssw_cuda/used_input_exclusion_registry.sha256
```

The registry is rebuilt by the Phase 0 deterministic builder and is copied
into the Phase 3 corpus as identity-only regression rows. Ordinals are
comparable only within their recorded namespace. Pair digests use canonical
compact JSON with sorted keys and this domain:

```text
schema = ssw-cuda-exclusion-pair-v1
query/target ordinal namespaces and values
query/target IDs and SHA-256 identities
query/target regions
```

The checker rejects a candidate when any available identity overlaps:

```text
query source ordinal within its namespace
target source ordinal within its namespace
query sequence SHA-256
target sequence SHA-256
pair digest
source receipt path
```

It also rejects any candidate already tagged as correctness, performance,
pilot, debug, minimization, or fuzz-replay input. Query-only historical
exclusions remain hard exclusions by query digest. Missing identity fields,
invalid digests, duplicate candidate IDs, or an unbound pair digest fail
closed.

The checker implementation is
`reproduce/ssw_cuda/build_corpus.py --check-holdout CANDIDATES.json`. It has no
allowlist, exception flag, or manual override path.

## Static selection fields

Selection and stratification may use only information fixed before execution:

```text
role-local source ordinal and namespace
sequence length
source grouping
GC fraction
repeat-complexity proxy
static maximum-score upper bound
sequence or pair hash ordering
```

Names, gene symbols, transcript IDs, observed scores, runtime, mismatch,
fallback, CIGAR, endpoint, output rows, GPU numeric path, and prior debug
behavior must not influence selection. IDs may be retained in the frozen
manifest for provenance after ordinal/hash selection, but they cannot be
selection predicates.

The selection receipt must contain the complete eligible population, rejected
identities with machine-generated reasons, the exact static stratification
algorithm, hash seed/domain, selected source ordinals, and a checksum of both
selected and non-selected rows.

## No result-driven replacement

The frozen holdout has no replacement samples. In particular:

- a runtime byte/word path is reported after execution but never repaired by
  adding another sample;
- a timeout, OOM, fallback, technical failure, or mismatch is retained;
- a case used for debugging or minimization becomes excluded from any later
  fresh holdout;
- no query-name, gene-name, digest, result-based gate, blacklist, or allowlist
  may be introduced after implementation freeze.

Byte/word boundary coverage is forced in the preregistered adversarial
regression corpus, not by conditioning the independent holdout on an observed
numeric path.

## Independence and execution isolation

Authority and candidate arms must use independent commands and artifact roots.
Neither arm may read the other's output. Offline L0-L8 comparison begins only
after all frozen executions are complete. Resume may recognize an already
complete immutable attempt, but it may not retry or replace a failed row.

The Phase 11 manifest must bind the full-GPU implementation commit, CPU oracle
epoch, input checksums, command line, environment, worker/GPU mapping, timeout,
retry policy, artifact roots, and comparator checksum. Promotion requires zero
L1-L7 mismatch under the Phase 11 gate in `goal-ssw.md`; L8 is reported
separately as a diagnostic.

## Differential corpus tiers

`paper/ssw_cuda/corpus_manifest.tsv` has three execution tiers:

```text
identity_only  consumed historical identities; never auto-executed
compact        tiny exhaustive, focused adversarial, and compact fuzz tests
large          long boundaries and large fuzz; explicit expensive gate only
```

The normal Phase 3 checker validates all identities, generators, digests, and
compact comparator fixtures. It does not execute historical workloads or the
large corpus. A later expensive gate must name the exact frozen manifest rows
it executes and retain every result.

## Claim boundary

The known hq10/hq11 evidence is classified as:

```text
hq10_ht02: first divergence L5, then L6/L7/L8 representation differences
hq11_ht02: first divergence L4, then L5/L6/L7/L8 differences
```

The supported root-cause wording remains:

> reproducible GASAL2 GPU endpoint/CIGAR traceback divergence, consistent with
> an alternative reported-equal-score alignment path

No specific DP tie cell has been proven. Phase 2 inputs and every Phase 3
regression input are consumed evidence and cannot promote a later backend.
