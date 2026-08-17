# Canonical-Hybrid-v2 Bounded Rescue Protocol

## Historical decisions remain authoritative

This rescue track is versioned separately from the completed Phase 2 and
Phase 3 v1 decisions:

```text
gpu-traceback-v1 Phase 2 = verified_only_contract
sequential verified-v1 Phase 3 B3 = no_go
canonical-hybrid-v2 = unpromoted rescue candidate
```

Neither a regression pass nor a new v2 result may rewrite those records. The
old Phase 2 holdout is problem-discovery and regression evidence only.

## H execution contract

Arm H is exactly:

```text
GASAL2 GPU score prepass
+ strict GPU-score attempt selection
+ CPU SSW canonical traceback for selected attempts only
+ unchanged triplex conversion, filtering, clustering, and ranking
```

Arm H must set `FASIM_CANONICAL_HYBRID_V2=1` and
`FASIM_ALIGN_GASAL2_CPU_TRACEBACK=1`. The v2 bridge invokes its explicit strict
selection API; it does not depend on a query, gene, target, or digest list.
`FASIM_ALIGN_GASAL2_CPU_TRACEBACK_ALL` is forbidden. Arm H does not execute a complete CPU authority run.

For validation and performance measurement, arm A is a separate
`fasim_longtarget_x86` process on the same frozen input. A/H comparison is an
experimental harness operation, not hidden work inside H. Only H's own wall
time can be used as the v2 candidate time.

The following runtime parameters remain the submission-track candidate
defaults and cannot be tuned after observing regression, holdout, or pilot
results:

```text
FASIM_OUTPUT_MODE=tfosorted
FASIM_TOP5_GASAL2_GPU_SCOREINFO=1
FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1
FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=256
FASIM_ALIGN_GASAL2_STREAMS=3
FASIM_ALIGN_GASAL2_BATCH=20000
rule=0
cluster distance=15
cluster minimum Nt=50
top K=5
```

## Per-attempt telemetry

Every score-prepass attempt, selected or not, is written to the exact TSV
schema in `schemas/canonical_hybrid_v2_attempt_telemetry.schema.json`. The
record includes:

```text
batch and attempt identity
task, scoreinfo, rule, strand, para, and identity round
start, cutlength, and prealign threshold
GPU score, query endpoint, and global reference endpoint
selection decision and reason
CPU score, endpoints, and CIGAR when selected
CPU emit reason
converted and final canonical-row digests
final status
```

The digest is FNV-1a-64 over the exact UTF-8 TFOsorted data row without its
trailing newline, prefixed by `fnv1a64:`. The runner independently recomputes
all output-row digests. The set of mapped final digests must equal the set of
actual TFOsorted output rows. Duplicate attempt-to-row mappings are retained.

H fails closed if telemetry cannot be opened, already exists, is incomplete,
cannot be written, uses an unsupported conversion path, or does not show
exactly one CPU traceback for every selected attempt. It also fails if the
runtime reports fallback, OOM, timeout, a nonzero return code, or an invalid
component count.

## Runtime epoch

This implementation changes the GASAL2 bridge and production LongTarget
runtime behavior under an explicit opt-in contract. It therefore starts
`paper_runtime_epoch = 1`. All benchmark data from epoch 0 remain immutable
historical evidence. No epoch-0 performance number may be combined with an
epoch-1 v2 speedup claim.

The implementation commit, source diff, binary digest, compiler/build command,
and runtime dependencies must be frozen in
`paper/bioinformatics/canonical_hybrid_v2_runtime.json` before any regression
execution. The runner and each plan bind that receipt.

## Execution sequence

### 1. Existing Phase 2 regression

After implementation freeze, run H exactly once for all 36 primary Phase 2
attempts. Compare against the corresponding frozen authority outputs. Required
regression result:

```text
score clustered canonical TFO1-TFO5 = 36/36
stability clustered canonical TFO1-TFO5 = 36/36
Nt clustered canonical TFO1-TFO5 = 36/36
technical failures = 0
unexpected fallback = 0
```

Full-output equality is retained as a diagnostic and cannot expand the stated
contract. This regression set is not promotion evidence.

### 2. Fresh independent holdout

The v2 implementation and runtime epoch must be committed before a fresh
holdout manifest is selected. Selection must be input-only and deterministic.
Query names, gene names, target names, sequence digests, observed results,
blacklists, and allowlists cannot route an input into or out of a safe result.

The frozen fresh holdout runs separate A and H attempts. Promotion requires
zero score, stability, or Nt clustered top-five canonical-row mismatch, zero
technical failure, zero unexpected fallback, complete telemetry, and no
replacement retry.

### 3. Fixed A/H performance pilot

The performance plan is committed before execution and fixes inputs, A/H
order, repeats, GPU mapping, timeouts, and artifact roots. It records at least:

```text
GPU score-prepass time
selected attempt count
CPU SSW call count and traceback time
triplex conversion time
total H wall time
A wall time
peak RSS and physical-GPU memory
fallback, timeout, OOM, and output equality
```

No candidate-only v1 timing and no old sequential verified timing may be
reported as v2 speedup.

## Decision gate

The original B3 threshold remains unchanged. A versioned B3-v2 application run
may be authorized only if both conditions pass:

```text
fresh independent holdout: zero declared-contract mismatch
preregistered A/H performance gate: H speedup versus A >= 10x
```

No lower substitute threshold is allowed. If either condition fails, the
rescue track closes without changing Phase 2 or Phase 3 v1, and the CSBJ route
remains the fallback submission route.

Pilot, regression, and failed-attempt artifacts are append-only. There is no automatic or replacement retry. `--resume` may recognize a checksum-valid
completed attempt but must reject failed or partial attempts.
