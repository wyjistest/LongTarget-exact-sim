# Biological Top-K Successor Validation Epoch

## 1. Authority and purpose

This protocol is a successor to the frozen validation epoch identified by
commit `7fae3de6b13780d7cc0776038489cf2f22072339`. The predecessor ended at
Phase 4 with `blocked_fixed_budget`; it did not reach a scientific concordance
decision. The repository owner subsequently approved the explicit proposal:

```text
64 GiB successor epoch
max_total_artifact_storage_bytes = 68719476736
```

The approval applies only to this new epoch. It does not amend, reopen, retry,
or reclassify any predecessor attempt or decision.

This protocol incorporates `goal-biological-topk.md` byte-for-byte by its
SHA-256, except for the successor deltas stated here. Unchanged scientific
objects, contract definitions, gates, endpoint order, failure accounting,
product restrictions, and Phase 5-9 requirements remain normative.

## 2. Immutable predecessor boundary

The following predecessor facts are immutable:

```text
predecessor_commit = 7fae3de6b13780d7cc0776038489cf2f22072339
predecessor_protocol_sha256 = 1cd5e5a023d53655641ba831142f489011111fd2c166d895b2a851b0f513f6c3
predecessor_phase_4_decision = blocked_fixed_budget
predecessor_comparison_started = false
predecessor_scientific_decision_reached = false
predecessor_terminal_attempts = 165
predecessor_terminal_technical_failures = 0
predecessor_unstarted_attempts = 203
```

Tracked predecessor evidence is bound in
`paper/biological_topk_successor/v1_evidence_registry.tsv`. Runtime evidence
under both predecessor artifact roots is retained and checked by the original
phase-checker logic through a successor-side read-only wrapper with the frozen
Phase 0-4 commit map:

```text
.paper-artifacts/biological-topk/fresh-holdout
.paper-artifacts/biological-topk/fresh-holdout-repair1
python3 scripts/check_biological_topk_successor_v1_audit.py
```

No successor script may delete, rename, modify, supplement, or use those roots
as an execution destination. They are development evidence for planning only.

## 3. Successor namespace and state

All successor tracked evidence lives under these new namespaces:

```text
paper/biological_topk_successor
reproduce/biological_topk_successor
tests/biological_topk_successor
schemas/biological_topk_successor_program_state.schema.json
scripts/check_biological_topk_successor_*
```

All successor runtime evidence lives under:

```text
.paper-artifacts/biological-topk-successor
```

`paper/biological_topk/PROGRAM_STATE.json` remains the terminal predecessor
state. The live successor state is
`paper/biological_topk_successor/PROGRAM_STATE.json`.

## 4. Fixed resource authorization

The fixed 64 GiB quota includes all retained predecessor artifact bytes plus
all successor Phase 0-4 runtime artifacts. It is not a quota for only the new
root. It may not be raised after successor Phase 3 selection.

The Phase 1 storage model must use the observed predecessor compressed artifact
distribution and raw telemetry peak as development data. At minimum it must
freeze and report:

```text
retained predecessor bytes
projected successor retained bytes
one raw G telemetry reservation
one-sided 95% upper bound
max-observed per-arm stress envelope
margin to 68719476736 bytes
```

The successor Phase 3 manifest-specific projection must pass before execution.
The original 48-hour scheduled-wall and 72 GPU-hour limits remain unchanged.
The successor permits one infrastructure repair epoch. No scientific retry,
replacement, supplementation, deletion, or output-informed quota adjustment is
allowed.

## 5. Phase and Git semantics

The successor has Phases 0 through 9 and preserves the dependency chain from
the predecessor protocol. Each phase uses clean start, start receipt, allowlist,
precommit receipt, one phase commit, and read-only postcommit verification.

Normative commands are:

```text
python3 scripts/check_biological_topk_successor_phase.py --phase N --mode precommit
python3 scripts/check_biological_topk_successor_phase.py --phase N --mode postcommit
bash scripts/check_biological_topk_successor_all.sh --final
```

No phase may begin before the previous phase commit passes its postcommit
check. A blocking or scientific no-go state terminates dependent later phases.

## 6. Successor Phase 0

Phase 0 freezes this protocol, the owner authorization, the predecessor
boundary, the successor state schema, the parameterized checker, and the
aggregate checker. It must prove a clean parent tree at
`7fae3de6b13780d7cc0776038489cf2f22072339` and must not run a scientific
prediction.

Phase 0 passes only if:

```text
the pinned predecessor Phase 0-4 aggregate audit passes read-only
tracked predecessor evidence reproduces from the predecessor commit
both predecessor artifact roots match their frozen byte counts and summaries
the 64 GiB authorization is exact and includes predecessor evidence
the successor artifact root does not exist
the successor state schema rejects unknown or premature promotion values
the Phase 0 diff equals its sorted allowlist
```

Commit message:

```text
docs: freeze biological Top-K successor validation epoch
```

## 7. Successor Phase 1

Phase 1 reuses the exact `biological_topk_candidate_site_v1` scientific
contract and comparator definitions. It must freeze a successor-specific source
universe, exclusion registry, information plan, corrected resource model, and
64 GiB budget decision before any successor fresh selection.

All predecessor Phase 4 queries, targets, namespaced ordinals, sequence digests,
pair digests, registered source identities, and evaluation/development lncRNAs
are excluded. The predecessor outputs may train only the resource model; they
may not train or tune scientific thresholds, matching, ranking, K, endpoints,
or sample-size requirements.

Commit message:

```text
repro: freeze successor contract, source universe, and corrected resource gates
```

## 8. Successor Phase 2

Phase 2 freezes the unchanged comparator in the successor epoch and reruns the
complete historical regression suite. It must preserve every prior mismatch and
no-go. A new comparator or contract change is prohibited.

Commit message:

```text
test: freeze successor candidate-site comparator regression
```

## 9. Successor Phase 3

Phase 3 selects a new panel using input-only metadata from the successor source
universe. It must have zero overlap with all predecessor inputs and all other
registered exclusions. The original statistical minimums, independent-unit
rules, balanced A/G order, technical-repeat handling, and exact runtime binary
bindings remain unchanged.

No prediction or scientific comparison may run during Phase 3. The corrected
manifest-specific resource projection must fit the fixed 64 GiB total quota,
including retained predecessor evidence and raw telemetry reservation.

Commit message:

```text
repro: freeze successor fresh candidate-site holdout
```

## 10. Successor Phase 4

Phase 4 executes exactly one full frozen epoch under an independent successor
artifact root. Telemetry must be validated and then stored using deterministic
lossless gzip before the next attempt. Comparison remains globally barred until
all A/G attempt receipts are terminal.

The promotion, information, identity, missing-output, fallback, ambiguity,
exact-binomial, and failure-denominator gates are exactly those in the
predecessor protocol. A budget stop remains a block, not a scientific no-go.

Commit message:

```text
bench: freeze successor fresh candidate-site concordance decision
```

## 11. Successor Phases 5-9

Phases 5-9 inherit the predecessor protocol in full. In particular:

* Phase 5 requires at least five distinct evaluation lncRNAs not used in any
  predecessor development or evaluation evidence, deterministic labels and
  negatives, a frozen external predictor, and no evaluation prediction before
  the Phase 5 commit.
* Phase 6 uses independent A/G/X execution, identical paired bootstrap indices,
  and the frozen E1-E4 intersection-union gate.
* Phase 7 uses a new input-only performance panel, contract-valid attempts, and
  a preregistered widening branch.
* Phase 8 keeps product status experimental until its checker and commit pass;
  no release or DOI may be published by the agent.
* Phase 9 uses separate audit-candidate and certification commits and retains
  all prohibited-claim scans and final-decision mappings.

The predecessor block can never be rewritten as a pass. Only complete successor
evidence can authorize successor Phase 5 and later product or manuscript claims.
