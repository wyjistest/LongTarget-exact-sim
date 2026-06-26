# Fasim GASAL2 Phase 3 CIGAR NT Prefilter Real-Validate Characterization

This is the full-workload characterization result for the default-off
`FASIM_GASAL2_PHASE3_CIGAR_NT_PREFILTER=1` path with validation enabled:

```text
FASIM_GASAL2_PHASE3_CIGAR_NT_PREFILTER_VALIDATE=1
```

It is not a default runtime recommendation.

## Scope

The real candidate skips expensive triplex conversion only when:

```text
cigar_aligned_len < ntMin
```

In validate mode, every skipped candidate is still checked against the legacy
conversion result. If legacy conversion would keep the row, the path fails
closed by counting a mismatch/fallback and preserving legacy behavior.

CPU/Fasim restored output remains the authority.

Forbidden:

```text
no default-on pruning
no endpoint authority
no CIGAR / traceback authority
no output or digest authority change
no resurrection of FASIM_ALIGN_GASAL2_NT_SUM_SPAN_PRUNE
```

## Command

```bash
make characterize-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate-full
make check-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate-full-result
```

The generated report is:

```text
.tmp/characterize_fasim_gasal2_phase3_cigar_nt_prefilter_real_validate_full/report.tsv
```

## Result

```text
chr22:
  target = .tmp/fasim_rule0_chr22_full_gasal2_gpu_score/input/chr22.fa
  restored_equal = 1
  legacy_only_rows = 0
  candidate_only_rows = 0
  baseline_rows = 388,821
  real_validate_rows = 388,821
  real_skipped_alignments = 493,934
  real_validated_skips = 493,934
  real_validate_mismatches = 0
  real_fallbacks = 0
  real_decision = validated_clean
  baseline_run_wall_seconds = 69.779004
  real_validate_run_wall_seconds = 70.396690
  run_wall_speedup = 0.991226
  baseline_convert_wall_seconds = 8.47075
  real_validate_convert_wall_seconds = 9.15482
  convert_wall_speedup = 0.925278
  decision = real_validate_clean_no_speedup

chr1:
  target = .tmp/fasim_gasal2_chr1_full_input/chr1.fa
  restored_equal = 1
  legacy_only_rows = 0
  candidate_only_rows = 0
  baseline_rows = 1,577,067
  real_validate_rows = 1,577,067
  real_skipped_alignments = 2,771,079
  real_validated_skips = 2,771,079
  real_validate_mismatches = 0
  real_fallbacks = 0
  real_decision = validated_clean
  baseline_run_wall_seconds = 396.600376
  real_validate_run_wall_seconds = 400.166834
  run_wall_speedup = 0.991088
  baseline_convert_wall_seconds = 47.3253
  real_validate_convert_wall_seconds = 51.4659
  convert_wall_speedup = 0.919547
  decision = real_validate_clean_no_speedup
```

## Decision

Correctness gate:

```text
pass
```

Measured performance gate:

```text
fail
```

Interpretation:

```text
The CIGAR NT prefilter is correctness-clean in fail-closed validate mode on
chr22 and chr1 full workloads. It preserves restored output exactly and has
zero validation mismatches or fallbacks.

However, the real-validate path is slower than baseline:
  chr22 convert wall = 0.925278x baseline
  chr1  convert wall = 0.919547x baseline
  chr22 run wall     = 0.991226x baseline
  chr1  run wall     = 0.991088x baseline

The projected shadow savings were too small to overcome validation and branch
overhead. This path should remain default-off and should not be recommended as
a runtime optimization.
```

## Stop Condition

Phase 3 CIGAR NT prefilter is now a stop checkpoint:

```text
real_validate_correctness = clean
real_validate_performance = no_go
default_enablement = no
runtime_recommendation = no
```

The full-output path should continue to use equivalence-first/archive-first
delivery. Further Phase 3 pre-convert pruning work needs a different candidate
with materially larger avoided work before another real runtime prototype is
justified.
