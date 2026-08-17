# Canonical-Hybrid-v2 Fresh Holdout Decision

The input-only fresh holdout completed all 60 frozen A/H validation instances
from 48 workloads. Six workloads received the preregistered three complete
repeats. No attempt was replaced or retried.

## Correctness result

```text
correctness_gate = pass
score clustered Top-5 canonical rows = 60/60
stability clustered Top-5 canonical rows = 60/60
Nt clustered Top-5 canonical rows = 60/60
all three declared rankings = 60/60
full-output diagnostic equality = 60/60
technical failures = 0
fallbacks = 0
timeouts = 0
OOMs = 0
```

This fresh result promotes the correctness evidence for the versioned
`all-ranked-top5-canonical-row-v2` contract. Arm H executed a GASAL2 score
prepass followed by CPU SSW canonical traceback only for selected attempts; it
did not execute a complete CPU authority run. The exact post-execution snapshot
file set matched its frozen manifest, and no Python bytecode cache was created.

Full-output equality is reported as a diagnostic. It does not silently expand
the preregistered clustered Top-5 contract.

## Remaining gate

```text
canonical-hybrid-v2 correctness = pass
canonical-hybrid-v2 performance = pending fixed A/H pilot
B3-v2 = pending_performance_pilot
Bioinformatics route = conditionally reopened, not submission-ready
```

The correctness-run timings are diagnostic only and cannot promote performance.
The next authorized step is to freeze and commit a separate A/H performance
pilot before execution. The original H/A speedup threshold remains `>=10x`; no
lower substitute threshold is permitted.

## Historical boundary

The historical records remain unchanged:

```text
gpu-traceback-v1 Phase 2 = verified_only_contract
sequential verified-v1 Phase 3 B3 = no_go
```

The old regression set remains regression-only. This decision neither rewrites
those results nor reports v1 candidate-only or sequential-verified timing as
canonical-hybrid-v2 speedup.

Evidence receipt SHA-256: `1b370b0d85f721dedf20a9eaab7ca19fa2e5245396ca3c331e88958cafe2d77c`.
