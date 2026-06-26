# Fasim GASAL2 Dynamic Traceback Frontier Characterization

This checkpoint evaluates whether a dynamic-looking score frontier can beat the
fixed `FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=116` boundary while
preserving the scoped top5 contract.

## Scope

This is still top5-only:

```text
top5_score
top5_stability
top5_nt_score
```

It is not full `.lite` / `TFOsorted` equivalence and it is not an
`aligner.Align()` replacement.

## Prototype

The tested frontier was a high main threshold with a narrow rescue band:

```text
FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=120
FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MIN_PREALIGN_SCORE=115
FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MAX_PREALIGN_SCORE=116
FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MAX_TARGET_SIZE=120
```

This adds one diagnostic env:

```text
FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MAX_PREALIGN_SCORE
```

The purpose is to avoid rescuing every score from 115 upward. The previous guard
could express `score >= 115 && target_size <= 120`; this checkpoint can express a
narrow band like `115 <= score <= 116 && target_size <= 120`.

## Results

### chr22 slice 10m-12m

Fixed thresholds on the small slice already show why a global score cutoff is
not universal:

```text
fixed 116:
  traceback = 66,414
  top5_score_equal = true
  top5_stability_equal = false
  top5_nt_score_equal = true

fixed 120:
  traceback = 58,470
  top5_score_equal = true
  top5_stability_equal = false
  top5_nt_score_equal = true
```

Score-band rescue with threshold 120:

```text
guard score band 115..116, target_size <= 120:
  traceback = 62,705
  guard_kept = 4,235
  top5_score_equal = true
  top5_stability_equal = false
  top5_nt_score_equal = true

guard score band 115..119, target_size <= 120:
  traceback = 68,603
  guard_kept = 10,133
  top5_score_equal = true
  top5_stability_equal = false
  top5_nt_score_equal = true
```

The slice fails stability even when the rescue band is widened to all scores
below the threshold.

### chr22 full

Narrow band result:

```text
threshold 120 + rescue score 115..116, target_size <= 120:
  wall_seconds = 46.933625
  traceback_requests = 2,285,028
  traceback_skipped = 4,625,391
  guard_kept = 176,411

  top5_score_equal = true
  top5_stability_equal = false
  top5_nt_score_equal = true

  baseline_rows = 388,501
  candidate_rows = 80,663
  missing_rows = 307,727
  extra_rows = 1,459
```

This is faster than fixed 116, but it fails the top5 stability contract.

For comparison, fixed 116 on chr22 full remains the current best passing simple
rule:

```text
threshold 116:
  wall_seconds = 48.483698
  traceback_requests = 2,441,113
  top5_score_equal = true
  top5_stability_equal = true
  top5_nt_score_equal = true
```

## Decision

Simple dynamic score-band rescue is not enough:

```text
score-only frontier:
  can reduce traceback below fixed 116

stability top5:
  still fails

current best passing rule:
  fixed threshold 116 for chr22 full / chr21+chr22 merged characterization
```

The next useful design needs a pre-traceback stability risk signal or a valid
upper bound. Without that, dynamic score adjustment is just another score cutoff
and can prune low-score, high-stability rows.

## Stability Risk Backtrace

The attempt export now includes diagnostic global coordinates:

```text
target_global_start
target_global_end
output_global_start
output_global_end
task_strand
task_para
task_rule
```

`target_global_*` is the window in the transformed `task.seq2` coordinate space.
`output_global_*` is a diagnostic projection into the final output coordinate
direction using the same reverse rule as `buildConvertedTriplexRecord`. For
reverse-transformed tasks, `output_global_*` is the safer field for matching
final `.lite` rows back to pre-traceback GASAL2 attempts. The helper script is:

```bash
python3 scripts/analyze_fasim_gasal2_stability_risk_attempts.py \
  --baseline-lite BASELINE.lite \
  --attempt-export attempts.tsv \
  --top-k 10
```

On the chr22 10m-12m slice, the baseline stability top rows include low-score
rows:

```text
rank 4:
  Score=100 Nt=68 MeanStability=3.20882

rank 5:
  Score=99 Nt=66 MeanStability=3.2

rank 6:
  Score=110 Nt=70 MeanStability=3.19571
```

The score-band run prunes or fails to preserve the attempts needed for those
rows, even though overlapping higher-score attempts are often kept. Example:

```text
rank 5 row 1599900-1599965:
  row Score=99 Nt=66 MeanStability=3.2
  nearby kept attempts include prealign_score 127 and 121
  nearby skipped attempts include prealign_score 119, 113, 103
```

That means a high-score overlapping attempt is not a proof that the lower-score
attempt is irrelevant to stability top5. The missing signal is not just
`prealign_score`; it is tied to the final alignment's stability calculation.

## Stability Proxy Probe

This checkpoint also adds:

```bash
python3 scripts/analyze_fasim_gasal2_stability_upper_bound.py \
  --baseline-lite BASELINE.lite \
  --attempt-export attempts.tsv \
  --query-fasta H19.fa \
  --target-fasta TARGET.fa \
  --top-k 10
```

The script computes a deliberately loose pre-traceback stability-risk proxy from
the target window and query bases. It uses `task_para` when present and matches
rows with `output_global_*` when present. It is not a safety certificate:

```text
exact MeanStability:
  requires CIGAR-derived query/ref pairing, gap placement, and T/C repeat
  penalties

proxy:
  can identify suspicious skipped attempts near top-stability rows
  cannot prove that an attempt is irrelevant
```

On the score-band no-go slice, the proxy confirms that the failing top-stability
rows still have skipped nearby attempts with plausible stability risk:

```text
rank 4:
  row Score=100 Nt=68 MeanStability=3.20882
  skipped attempts = 35
  best skipped prealign score = 118
  risky skipped attempts = 29

rank 5:
  row Score=99 Nt=66 MeanStability=3.2
  skipped attempts = 40
  best skipped prealign score = 119
  risky skipped attempts = 7

rank 6:
  row Score=110 Nt=70 MeanStability=3.19571
  skipped attempts = 27
  best skipped prealign score = 119
  risky skipped attempts = 14
```

This is useful diagnostic evidence, but it is too broad to use as a runtime
rescue rule by itself. A proxy-based rescue would pull back many candidates and
erode the traceback reduction.

## Proxy Rule Sweep

The follow-up offline sweep asks a narrower question: can a simple combination
of `prealign_score`, loose stability upper bound, and overlap with current
top-stability rows selectively rescue the failing stability rows without
returning close to fixed-threshold traceback volume?

The helper is:

```bash
python3 scripts/analyze_fasim_gasal2_stability_proxy_rule_sweep.py \
  --baseline-lite BASELINE.lite \
  --attempt-export attempts.tsv \
  --query-fasta H19.fa \
  --target-fasta TARGET.fa \
  --top-k 10 \
  --score-min 99 \
  --score-min 108 \
  --upper-bound-min 3.5 \
  --overlap-min 55
```

The sweep reports, per candidate rule:

```text
covered_topk_rows
risky_skipped_covered
rescued_skipped_attempts
rescue_fraction_of_all_skipped
estimated_traceback_after_rescue
```

On the score-band no-go slice, the rule sweep found the same tradeoff:

```text
full top10 coverage with lowest rescue cost:
  score>=108 & ub>=3.5
    covered_topk_rows = 10/10
    risky_skipped_covered = 40/125
    rescued_skipped_attempts = 13,103
    estimated_traceback_after_rescue = 75,808

full risky-skipped coverage:
  ub>=3.2
    covered_topk_rows = 10/10
    risky_skipped_covered = 125/125
    rescued_skipped_attempts = 79,823
    estimated_traceback_after_rescue = 142,528

low-cost overlap-like rules:
  score>=108 & ub>=3.5 & overlap>=55
    covered_topk_rows = 9/10
    rescued_skipped_attempts = 14
```

This means the proxy has diagnostic signal, but the simple feature combinations
are not selective enough to become a passing runtime rescue:

```text
cheap rules:
  miss at least one top-stability row

rules covering all top-stability rows:
  rescue thousands to tens of thousands of additional tracebacks

rules covering all risky skipped attempts:
  exceed fixed 116 traceback volume on this slice
```

Current implication:

```text
score-only dynamic threshold:
  insufficient

score + target_size rescue:
  insufficient

needed before further traceback pruning:
  task-aware stability certificate, or
  a stronger pre-traceback risk feature with measured rescue selectivity

current practical rule:
  fixed threshold 116 remains the passing rule for the chr22 full /
  chr21+chr22 merged top5-only characterization
```

## Verification

```bash
make check-fasim-gasal2-traceback-guard-score-band-smoke
make check-fasim-gasal2-stability-risk-attempts-parser
make check-fasim-gasal2-stability-upper-bound-parser
make check-fasim-gasal2-stability-proxy-rule-sweep-parser
```
