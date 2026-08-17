# Phase 2 Traceback Mismatch Root-Cause Record

## Scope and historical status

This record is a post-hoc diagnostic of the two declared-contract mismatches
from the frozen Phase 2 holdout. It does not reinterpret either historical
decision:

```text
gpu-traceback-v1 Phase 2 decision = verified_only_contract
sequential verified-v1 Phase 3 B3 decision = no_go
diagnostic replay promotion eligibility = false
```

The replay plan was committed before the controlled replay as commit
`06e0310d2a35f7db2fb60c68c0ef57dd77674b12`. It pins the Phase 2 execution
snapshot at `1c07823bc3a56704415d242b3ddc937cfa03ee86`, candidate binary SHA-256
`584ff639e09ede813a645f6ef0927a183eadbf6c216a530c2ed998fe800e4759`,
the two input pairs, both frozen authority/candidate output digests, all
runtime environment overrides, and the physical replay GPU.

## Frozen mismatch observations

| Attempt | Declared mismatch | Preserved identity | Representation difference |
| --- | --- | --- | --- |
| `hq10_ht02__repeat00` | stability rank 1, cluster 2 | query 1697-1752; target 525-581; Score 68; Nt 58; identical ungapped TFO and TTS | alternative gap placement; MeanStability 2.45690 (authority) versus 2.47069 (candidate) |
| `hq11_ht02__repeat00` | score rank 3, cluster 2 | query 726-791; Score 93; Nt 66; same cluster and downstream rank | candidate target 2189-2253 versus authority 2192-2253; 62/65 target bases overlap (95.38%); different CIGAR-derived TTS and MeanStability 1.16667 versus 1.09848 |

The top-five cluster order did not change in either case. The mismatch is the
canonical representative row selected for one rank, not substitution of a
different distant top-five cluster. That distinction does not make the old
strict contract clean: the declared contract compares complete canonical
representative rows.

## Controlled replay

Each case was executed once in each of three modes from its immutable Phase 2
execution snapshot:

1. The original GASAL2 endpoint/CIGAR traceback path.
2. The same path with staged-first pruning disabled as a negative control.
3. GASAL2 score prepass plus strict selected-attempt CPU SSW traceback.

All replay processes were explicitly bound with `CUDA_VISIBLE_DEVICES=1` to:

```text
name = NVIDIA GeForce RTX 4090
uuid = GPU-9c6883e3-fe8f-1a96-ebac-c8496069cba2
pci_bus_id = 00000000:68:00.0
compute_capability = 8.9
driver = 555.42.06
memory_total_mib = 24564
```

The formal Phase 2 environment exposed two RTX 4090 devices but did not set
`CUDA_VISIBLE_DEVICES` or emit the runtime device UUID. Consequently, this
record does not overstate the formal run's physical device identity; it shows
that the frozen candidate result is byte-reproducible when explicitly replayed
on physical index 1, the non-default same-model device.

The six replay runs all returned zero with no fallback, timeout, or detected
OOM. Both GPU traceback modes reproduced the corresponding frozen candidate
file byte for byte. Disabling staged-first pruning did not change either
candidate output. Strict CPU traceback reproduced the corresponding frozen
authority file byte for byte:

| Attempt | GPU-selected attempts | CPU SSW calls | threshold | best fallback | last | Strict output |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `hq10_ht02__repeat00` | 641 | 641 | 482 | 111 | 48 | byte-equal to authority |
| `hq11_ht02__repeat00` | 827 | 827 | 570 | 163 | 94 | byte-equal to authority |

The exact commands, explicit environment, timing, device inventory, input and
output digests, telemetry, logs, and artifact-manifest identity are in
`phase2_traceback_replay_receipt.json`. The compact run table is
`phase2_traceback_replay.tsv`. Raw artifacts are indexed by the receipt under
`.paper-artifacts/bioinformatics-phase2-traceback-replay-v1`.

## Code-path consistency

The observed behavior matches the two implementation paths:

- `fasim/gasal2_align_bridge.cpp:452-527` decodes the GASAL2 CIGAR and copies
  the GPU query/reference begin and end coordinates directly into the
  alignment.
- `fasim/sswNew.cpp:2009-2200` obtains the CPU endpoint from the forward SSW,
  finds the start with a reverse pass, and generates a banded traceback over
  the resulting interval.
- `fasim/Fasim-LongTarget.cpp:15281-15485` implements the existing score
  prepass and selected-attempt CPU replay path; CPU SSW results determine the
  emitted threshold, best-fallback, or last alignment.
- `fasim/fastsim.h:3271-3374` recomputes identity, Nt, and triplex stability by
  walking the final CIGAR and sequences. Alternative endpoints or gap placement
  can therefore change MeanStability and the emitted row even when Score and Nt
  remain equal.
- `scripts/compare_fasim_segmented_contract.py:120-159` retains complete-row
  identity for each ranked cluster representative, so a CIGAR-derived row
  change remains a strict clustered top-five mismatch.

No production runtime source differs between the Phase 2 snapshot commit and
the replay-preparation commit.

## Root-cause classification

The evidence supports the following bounded classification:

> reproducible GASAL2 GPU endpoint/CIGAR traceback divergence, consistent with
> an alternative reported-equal-score alignment path

The diagnosis is stronger than an unspecified floating-point, clustering, or
random-device explanation: the divergent candidate is deterministic on the
second same-model GPU, the pruning negative control does not alter it, and
replacing only selected-attempt traceback with CPU SSW restores both authority
outputs.

It does not establish a specific tied DP cell because the frozen binary did
not export that internal state. It also does not establish behavior across GPU
architectures, estimate the population mismatch rate, prove full-output
equality, or prove that the GPU score prepass always selects every attempt
needed by CPU authority.

## Rescue implication

The replay provides mechanism evidence for a separately versioned
`canonical-hybrid-v2` rescue track:

```text
GASAL2 GPU score prepass
+ CPU SSW canonical traceback for selected attempts
+ unchanged downstream triplex conversion, clustering, and ranking
```

That path does not execute a complete CPU authority run, so the structural
timing impossibility of sequential verified-v1 does not automatically apply.
This diagnostic is not promotion evidence. The old holdout may only be used as
a regression set; score-selection completeness must pass a newly frozen
independent holdout, and B3-v2 still requires the unchanged >=10x performance
gate on preregistered workloads.
