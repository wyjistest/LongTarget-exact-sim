# Fasim GASAL2 ScoreInfo Scoped Milestone Rollup

This rollup makes the current milestone status explicit for the active
scoreInfo/preAlign GPU/GASAL2 objective.

```text
Milestone status: yes, scoped milestone
Full objective status: not complete
```

## What This Milestone Proves

The current repository evidence supports a scoped milestone:

```text
short-query/H19 top5 artifact:
  scoped go

MEG3 grouped tiny-region top5 wrapper:
  scoped go

MALAT1-like group32 two-contract scoreInfo runtime:
  scoped go

NEAT1/current broad long-query shape:
  no-go for real path

score-prepass state-machine consumer:
  stopped for real path
```

The scoped positive paths are default-off and externally checked. They do not
grant broad output authority.

## Required Evidence Gates

The milestone depends on these repository gates:

```bash
make check-fasim-gasal2-top5-release-smoke
make check-fasim-gasal2-scoreinfo-scoped-release-smoke
make check-fasim-gasal2-malat1-two-contract-product-readiness
make check-fasim-gasal2-malat1-two-contract-recommended-runtime
make check-fasim-gasal2-score-prepass-state-machine-stop
make check-fasim-gasal2-scoreinfo-completion-gap
make check-fasim-gasal2-full-goal-decision
```

The top5 release smoke proves the formal top5 artifact contract is wired and
active on a bounded short-query example. It is a contract smoke, not a
performance claim.

The scoreInfo scoped release smoke proves the MALAT1-like first8 no-probe lite
and TFOsorted runtime gates, then rechecks the scoped milestone and full-goal
boundary. It is a scoped MALAT1-like smoke, not a universal replacement smoke.

The MALAT1-like product-readiness and recommended-runtime gates record the
default-off scope for
`--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32`, including
the requirement that full row-set equality, digest equality, coverage counters,
and zero probe leakage hold for the claimed schema.

The state-machine stop gate records that the current segmented score-prepass
state-machine consumer is not a real-path candidate.

The completion-gap and full-goal decision gates prevent this milestone from
being mistaken for completion of the original goal.

## Explicit Non-Claims

This milestone does not prove:

```text
universal scoreInfo/preAlign replacement
full aligner.Align replacement
GPU endpoint authority
GPU CIGAR authority
GPU traceback authority
full .lite equivalence for the top5 artifact path
all-row TFO equivalence for the top5 artifact path
NEAT1 broad long-query real path
default production path
```

Do not call `update_goal complete` for the original objective from this
milestone. The full objective remains open unless universal replacement is
proven, or the user explicitly accepts a narrowed scoped product contract as
the goal.

## Allowed Continuation

Valid continuation is limited to:

```text
accepted scoped productization of the top5 artifact contract
broader full-output/TFO equivalence proof over an explicitly claimed scope
different long-query execution architecture
remaining CPU realpath extend/align reduction
```

Invalid continuation:

```text
promote current score-prepass state-machine trust
promote selected-segment GASAL2 traceback
promote GPU endpoint/CIGAR/traceback authority
claim broad GASAL2 aligner.Align replacement from top5 or MALAT1 scoped gates
```

## Gate

```bash
make check-fasim-gasal2-scoreinfo-scoped-milestone-rollup
```
