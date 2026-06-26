# Fasim GASAL2 Path A Scoped Completion Acceptance

This document is the acceptance packet for Path A in the GASAL2/Fasim roadmap.
It does not mark the active goal complete by itself. It defines the exact
scoped product the user may accept instead of the original broad objective.

```text
path_a_scoped_completion_acceptance_packet = defined
user_scope_acceptance_recorded = 1
```

The user explicitly accepted Path A scoped completion in this conversation:

```text
accepted_user_message = 接受path A，关闭goal
path_a_user_acceptance_recorded = 1
```

## Accepted Scoped Product

Path A is only this scoped product:

```text
contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1
runtime = default-off opt-in
primary preset = --gasal2-top5-column-pruned-scoreinfo
tiny-region add-on = --group-target-records 32
query/workload shape = short-query/H19 and MEG3-like grouped tiny-region
archive delivery = reference-backed archive-first restored output where claimed
```

User-facing artifacts:

```text
topk_summary.tsv
topk_rows.tsv
topk-TFOsorted.lite
report.json
run_manifest.json
reference-backed TFO archive where archive-first delivery is claimed
restore command and manifest for archive restore
```

## Non-Claims

Accepting Path A must also accept these non-claims:

```text
not broad aligner.Align replacement
not universal scoreInfo/preAlign replacement
not long-query NEAT1/MALAT1 GASAL2 production path
not full `.lite` equivalence unless separately claimed by archive restore
not final all-row TFO equivalence for top5 artifact workloads
not GPU endpoint authority
not GPU CIGAR authority
not GPU traceback authority
not broad production default
```

CPU authority remains:

```text
CPU aligner.Align() remains score/endpoint/traceback/CIGAR/output authority.
GASAL2 output authority = 0
```

## Required Acceptance Gates

Before Path A can close the active goal as scoped completion, rerun:

```bash
make check-fasim-gasal2-roadmap-phase0-reproducibility
make check-fasim-gasal2-roadmap-phase1-scoped-product
make check-fasim-gasal2-roadmap-phase5-archive-artifact
make check-fasim-gasal2-roadmap-phase6-workload-matrix
make check-fasim-gasal2-roadmap-phase8-completion-decision
make check-fasim-gasal2-roadmap-current-state
```

Path A can close only if all are true:

```text
user explicitly accepts scoped completion
scoped_product_status = accepted
claimed scoped rows pass
blocked and unclaimed rows remain explicit
no claimed broad_replacement row is required
accepted non-claims are recorded
final decision says complete_scoped_path_a, not broad replacement
```

## Current Decision

```text
path_a_scoped_completion_status = accepted
user_scope_acceptance_recorded = 1
scoped_completion_may_close_goal = 1
path_a_user_acceptance_recorded = 1
path_a_scoped_completion_may_close_goal = 1
broad_objective_status = open
active_goal_completion_status = complete_scoped_path_a
completion_guard_cleared = 1
goal_completion_status = complete
must_not_call_update_goal_complete = 0
```

This closes the active goal only under the Path A scoped product contract.
It does not claim broad `aligner.Align()` replacement. A future broad Path B
would require a new architecture that passes Phase 7 and Phase 8.
