# Fasim GASAL2 Phase 3 CIGAR NT Prefilter Full Characterization

This is a Phase 3 full-workload characterization result for the
`FASIM_GASAL2_PHASE3_CIGAR_NT_PREFILTER_SHADOW=1` diagnostic path.

It is not a real prune implementation and not a runtime recommendation.

## Scope

The shadow candidate compares:

```text
cigar_aligned_len < ntMin
legacy_converted_nt < ntMin
```

It still runs legacy conversion. CPU/Fasim output remains the authority.

Forbidden:

```text
no real prune
no endpoint authority
no CIGAR / traceback authority
no output or digest authority change
no resurrection of FASIM_ALIGN_GASAL2_NT_SUM_SPAN_PRUNE
```

## Command

```bash
make characterize-fasim-gasal2-phase3-cigar-nt-prefilter-full
make check-fasim-gasal2-phase3-cigar-nt-prefilter-full-result
```

The default workload paths used for this result were:

```text
chr22 = .tmp/fasim_rule0_chr22_full_gasal2_gpu_score/input/chr22.fa
chr1  = .tmp/fasim_gasal2_chr1_full_input/chr1.fa
rna   = H19.fa
```

The generated report is:

```text
.tmp/characterize_fasim_gasal2_phase3_cigar_nt_prefilter_full/report.tsv
```

## Result

```text
chr22:
  alignments_seen = 6,910,419
  cigar_lt_ntmin = 493,935
  legacy_nt_lt_ntmin = 493,935
  disagree_lt_ntmin = 0
  candidate_false_negative_rows = 0
  broad_cpu_triplexes = 824,153
  task_frontier_safety = safe
  real_prune_proof_gate = pass
  convert_wall_seconds = 13.1799
  projected_saved_seconds = 0.805121
  projected_saved_fraction = 0.061087

chr1:
  alignments_seen = 37,949,280
  cigar_lt_ntmin = 2,771,080
  legacy_nt_lt_ntmin = 2,771,080
  disagree_lt_ntmin = 0
  candidate_false_negative_rows = 0
  broad_cpu_triplexes = 3,385,713
  task_frontier_safety = safe
  real_prune_proof_gate = pass
  convert_wall_seconds = 70.594
  projected_saved_seconds = 4.45219
  projected_saved_fraction = 0.063068
```

## Decision

Correctness gate:

```text
pass
```

Projected value:

```text
low
```

Interpretation:

```text
The CIGAR NT prefilter is a much safer candidate than the stopped
nt-sum-span real prune: on chr22 and chr1 full workloads it has zero
observed CIGAR/legacy ntMin disagreement, zero false-negative rows, and
task-local frontier proof passes.

However, the projected saved conversion time is only about 6.1-6.3% of
current convert wall. This is not enough to claim a runtime win and does not
justify enabling a real prune by default.
```

## Next Gate

Only one narrow follow-up is justified:

```text
default-off real CIGAR NT prefilter prototype with validation
```

Required before any recommendation:

```text
chr22 and chr1 restored row-set equality clean
task_frontier_safety = safe
real_prune_proof_gate = pass
measured convert wall lower than Phase 2
measured run wall does not regress
validate/fallback remains available
```

Stop if:

```text
real runtime overhead eats the projected 6% convert saving
row set changes
task-local frontier changes
benefit only appears in top5 or sampled output
```
