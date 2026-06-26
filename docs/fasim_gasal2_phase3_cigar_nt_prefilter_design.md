# Fasim GASAL2 Phase 3 CIGAR NT Prefilter Design

This is a Phase 3 design gate for the next CPU-side reduction candidate after
the current `FASIM_ALIGN_GASAL2_NT_SUM_SPAN_PRUNE` path stopped.

It is not runtime code, not a completion claim, and not permission to enable a
real prune.

## Current Stop Evidence

The current real nt-sum-span prune is stopped:

```text
current_real_prune_decision = no_go
current_real_prune_row_set_equal = 0
current_real_prune_baseline_only_rows = 3
current_real_prune_candidate_only_rows = 1
current_real_prune_frontier_safety = unsafe
real_prune_may_be_enabled = 0
```

The failure mode matters:

```text
nt-sum-span pruning can perturb task-local sort/unique/top-N competition.
It is not enough to show that directly emitted rows have no false negatives.
Any future candidate must preserve the complete task-local frontier.
```

## Candidate

The next candidate is an exact CIGAR aligned-length prefilter:

```text
candidate name:
  cigar_nt_prefilter

future shadow env:
  FASIM_GASAL2_PHASE3_CIGAR_NT_PREFILTER_SHADOW=1

future real env, only after proof:
  FASIM_GASAL2_PHASE3_CIGAR_NT_PREFILTER=1
```

The candidate computes:

```text
aligned_len = fasim_cigar_aligned_len(alignment.cigar)
```

before calling the expensive full triplex conversion. If:

```text
aligned_len < ntMin
```

then the alignment should be safe to skip, because legacy conversion rejects
rows whose exact `nt` is below `ntMin`.

This is deliberately narrower than nt-sum-span pruning:

```text
not based on query span
not based on ref span
not based on query+ref span
not based on scoreInfo rank
not based on GASAL2 endpoint
not based on top5 output
```

## Required Shadow Proof

The first implementation must be diagnostic-only. It must run legacy conversion
and candidate accounting side by side.

Required telemetry:

```text
phase3_cigar_nt_prefilter_requested
phase3_cigar_nt_prefilter_active
phase3_cigar_nt_prefilter_alignments_seen
phase3_cigar_nt_prefilter_cigar_lt_ntmin
phase3_cigar_nt_prefilter_legacy_nt_lt_ntmin
phase3_cigar_nt_prefilter_agree_lt_ntmin
phase3_cigar_nt_prefilter_disagree_lt_ntmin
phase3_cigar_nt_prefilter_candidate_skippable
phase3_cigar_nt_prefilter_candidate_false_negative_rows
phase3_cigar_nt_prefilter_task_frontier_equal
phase3_cigar_nt_prefilter_task_frontier_safety
phase3_cigar_nt_prefilter_convert_seconds_projected_saved
```

The shadow gate must prove:

```text
disagree_lt_ntmin = 0
candidate_false_negative_rows = 0
task_row_set_equal = 1
task_frontier_safety = safe
real_prune_proof_gate = pass
```

## Candidate Artifact

The shadow implementation should write a candidate task-frontier export:

```text
candidate_broad_cpu_triplex.tsv
```

using the same schema as the current authority export:

```text
broad_cpu_triplex.tsv
```

The candidate file must represent the output that would remain if the CIGAR NT
prefilter were real. The proof command is:

```bash
python3 scripts/analyze_fasim_gasal2_task_frontier_proof.py \
  --baseline <no-prune-broad_cpu_triplex.tsv> \
  --candidate <candidate_broad_cpu_triplex.tsv>
```

## Go Gate

The candidate may move from shadow to a default-off real path only if the
following pass on chr22 and chr1:

```text
full restored row-set equality clean
missing rows = 0
extra rows = 0
task_frontier_safety = safe
real_prune_proof_gate = pass
disagree_lt_ntmin = 0
candidate_false_negative_rows = 0
convert wall lower than Phase 2
```

The first small fixture gate may use the existing chr22 slice, but that only
proves wiring. It cannot justify a real path.

## Stop Conditions

Stop the candidate if any of these occur:

```text
aligned_len < ntMin disagrees with legacy converted nt < ntMin
task-local frontier differs
restored row set differs
projected saved work is too small to matter
speedup appears only on top5 and not full output
```

## Non-Goals

Do not add:

```text
default-on pruning
GASAL2 endpoint authority
GPU CIGAR or traceback authority
top5-only proof as full-output proof
nt-sum-span real prune resurrection
scoreInfo rank pruning
sort/top-N partial selection
```

## Decision

```text
If the CIGAR NT prefilter shadow proves exact and saves material convert work:
  next PR may implement a default-off real opt-in with validate/fallback.

If the proof fails:
  stop Phase 3 pre-convert pruning and keep equivalence-first/archive-first
  output as the full-output path.

If the proof passes but saved work is small:
  do not add a real runtime path; keep the telemetry as a boundary result.
```
