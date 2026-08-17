# Canonical-Hybrid-v2 Regression Decision

The frozen canonical-hybrid-v2 implementation completed exactly one H-arm
execution for each of the 36 existing Phase 2 primary attempts. Frozen Phase 2
CPU authority output was used only as the comparison reference; no authority
attempt was rerun inside or alongside H.

## Result

```text
decision = regression_pass_not_promotion
score clustered Top-5 canonical rows = 36/36
stability clustered Top-5 canonical rows = 36/36
Nt clustered Top-5 canonical rows = 36/36
all three declared rankings = 36/36
technical failures = 0
fallbacks = 0
timeouts = 0
OOMs = 0
GPU score-prepass attempts = 97,944
selected attempts = 24,486
CPU canonical traceback calls = 24,486
complete CPU authority runs inside H = 0
```

This result establishes that canonical-hybrid-v2 repairs the declared
clustered Top-5 canonical-row mismatches on the evidence set that exposed the
v1 traceback problem. It does not promote v2: these workloads have already
participated in discovery and implementation validation.

The next authorized correctness step is a frozen fresh independent holdout.
Its selection must be input-only, deterministic, and performed after the
implementation and execution harness are frozen. No query name, gene name,
target name, sequence digest, observed result, blacklist, or allowlist may be
used for selection or routing.

## Full-output boundary

Full TFOsorted output was identical in 35/36 attempts. The sole diagnostic
difference was `v2reg_hq04_ht02__repeat00`: authority contained 10 data rows,
H contained 8, with two authority rows missing and no extra H rows. Its
declared score-, stability-, and Nt-ranked clustered Top-5 contracts were all
clean.

Canonical-hybrid-v2 is therefore not a validated full-output replacement.
Only `all-ranked-top5-canonical-row-v2` is carried into fresh validation.

## Snapshot audit note

All files present when the regression execution snapshot was frozen retain
their recorded sizes and SHA-256 digests. During comparison, Python 3.11 wrote
two additional bytecode cache files inside that snapshot:

```text
__pycache__/compare_fasim_lite_offline_cluster_topk.cpython-311.pyc
__pycache__/fasim_tfo_archive.cpython-311.pyc
```

These files do not alter the frozen sources, binaries, inputs, outputs, or
scientific comparison. They are retained in the raw artifact inventory and
the regression is not rerun. Before any fresh holdout, the runner must prevent
bytecode writes with isolated Python execution (`-B` and/or
`PYTHONDONTWRITEBYTECODE=1`), add a test for an exact post-execution snapshot
file set, and freeze a new runner/runtime/plan identity.

## Decision boundary

The historical decisions remain unchanged:

```text
gpu-traceback-v1 Phase 2 = verified_only_contract
sequential verified-v1 Phase 3 B3 = no_go
```

The original B3 threshold remains H/A speedup `>=10x`; no substitute threshold
is introduced. Regression timings are diagnostic only. A v2 promotion remains
conditional on both a zero-mismatch fresh holdout and a separately frozen A/H
performance pilot that passes the original threshold.
