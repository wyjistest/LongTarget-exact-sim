# Fasim GASAL2 Limited Traceback Retained/Pruned Analysis

This note analyzes the chr22/H19 limited-traceback run at:

```text
FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_MAX_SCOREINFOS=65536
FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_MODE=score
```

The analysis compares the CPU baseline `.lite` output with the limited
traceback `.lite` output. It is output-level analysis, not a per-attempt dump of
all skipped traceback candidates.

The follow-up diagnostic export can now be enabled with:

```text
FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_ATTEMPT_EXPORT=/path/to/attempts.tsv
```

and summarized with:

```bash
python3 scripts/analyze_fasim_gasal2_limited_traceback_attempt_export.py \
  /path/to/attempts.tsv
```

## Counts

```text
baseline unique rows: 386,621
candidate unique rows: 380,908
retained unique rows: 376,509
missing unique rows: 10,112
extra unique rows: 4,399

baseline traceback requests: 6,910,419
limited traceback requests: 6,160,384
traceback skipped: 750,035
```

The skipped traceback candidates produce relatively little final output impact:

```text
missing rows / skipped traceback requests ~= 1.35%
candidate rows / limited traceback requests ~= 6.21%
```

This suggests that the low-priority tail selected by the current score cap has
lower output yield than the retained traceback set.

## Retained vs Missing vs Extra

```text
retained:
  count=376,509
  mean score=102.777
  median score=102
  max score=249
  mean Nt=65.19
  max Nt=224
  mean stability=1.9345
  max stability=3.3647

missing:
  count=10,112
  mean score=85.284
  median score=79
  max score=172
  mean Nt=62.29
  max Nt=196
  mean stability=1.7622
  max stability=3.2791

extra:
  count=4,399
  mean score=101.167
  median score=100
  max score=172
  mean Nt=68.52
  max Nt=196
  mean stability=1.9293
  max stability=3.2761
```

The missing rows are mostly lower-score, shorter, and lower-stability than the
retained set. The extra rows look closer to retained rows than to missing rows,
which is consistent with downstream ordering/non-overlap effects rather than a
simple one-for-one row deletion.

## Why top5 Stayed Equal

Top5 thresholds from the CPU baseline:

```text
score top5 5th row:
  Score=217 Nt=137 MeanStability=2.47445

stability top5 5th row:
  MeanStability=3.34091 Nt=66 Score=147

nt_score top5 5th row:
  Nt=201 Score=249 MeanStability=1.9403
```

The missing set stays below each top5 threshold:

```text
max missing Score=172       < 217
max missing MeanStability=3.2791 < 3.34091
max missing Nt=196          < 201
```

So this run preserves the top5 contract because the rows perturbed by limited
traceback have a clear margin below all three top5 decision boundaries.

## Missing Rate Signals

By rule:

```text
Rule 9:  25 / 40     = 62.50%
Rule 8:  1,092 / 4,006 = 27.26%
Rule 15: 343 / 2,065 = 16.61%
Rule 12: 293 / 2,176 = 13.47%
Rule 1:  889 / 12,589 = 7.06%
```

By strand:

```text
AntiPlus:  3,404 / 59,042 = 5.77%
AntiMinus: 3,243 / 57,709 = 5.62%
ParaMinus: 1,760 / 134,464 = 1.31%
ParaPlus:  1,705 / 135,406 = 1.26%
```

By score:

```text
<60:     126 / 502     = 25.10%
60-79:   5,123 / 21,513 = 23.81%
80-99:   2,696 / 148,965 = 1.81%
100-119: 1,676 / 171,554 = 0.98%
120-139: 441 / 38,248 = 1.15%
140-159: 47 / 5,166 = 0.91%
>=160:   3 / 673 = 0.45%
```

By stability:

```text
<1.2:    1,229 / 16,205 = 7.58%
1.2-1.6: 2,246 / 59,245 = 3.79%
1.6-2.0: 3,648 / 135,892 = 2.68%
2.0-2.4: 2,351 / 136,792 = 1.72%
2.4-2.8: 590 / 35,102 = 1.68%
>=2.8:   48 / 3,385 = 1.42%
```

Main pattern:

```text
missing risk is highest for low score, low stability, short alignments,
Anti strand rows, and specific low-volume/high-risk rules.
```

## Missing/Extra Relationship

Most missing rows are not directly replaced by an identical nearby extra row:

```text
same location excluding score fields: 578 / 10,112
same coordinates excluding rule and score fields: 750 / 10,112
same genome interval + strand only: 937 / 10,112

extra row within +/-10 bp start/end on same strand: 3,305 / 10,112
extra row within +/-100 bp start/end on same strand: 3,596 / 10,112
extra row within +/-1000 bp start/end on same strand: 4,007 / 10,112
```

About one third of missing rows have a nearby same-strand extra row. The rest
look like true dropped output rows rather than simple local substitutions.

## Aggressive Caps

The chr22 slice cap sweep shows why the current cap is conservative:

```text
score mode:
  cap 512..4096: score/stability/nt_score all fail
  cap 8192: score passes, stability and nt_score fail
  cap 16384: score and nt_score pass, stability fails
  cap 32768: score and nt_score pass, stability fails
  cap 65536: score/stability/nt_score all pass

score_spread mode:
  cap 512..8192: score/stability/nt_score all fail
  cap 16384: score passes, stability and nt_score fail
  cap 32768: score and nt_score pass, stability fails
```

The main blocker for a smaller cap is the stability top5 contract.

## Interpretation

Useful pruning signal exists, but a pure score cap is blunt:

```text
positive:
  dropped tail is mostly below top5 margins
  dropped tail has lower final-output yield
  low score / low stability / short Nt rows are high-risk for removal

risk:
  stability top5 is sensitive
  Anti strand and some rules are disproportionately affected
  full output is not equivalent
  missing/extra changes show downstream state can move when traceback is removed
```

The next pruning design should not simply lower the score cap. A better shape is
multi-objective retention:

```text
keep all strong score candidates
keep high stability candidates even when score is modest
keep high Nt candidates
keep small per-rule/per-strand guard bands, especially Anti and rules 8/9/12/15
then cap only the remaining low-score/low-stability/short tail
```

Any stronger reduction needs a fresh top5 gate on score, stability, and
nt_score, because the current data shows stability fails before score when the
cap becomes aggressive.

## Attempt Export Smoke Signal

The chr22 10m-12m smoke run with the current `65536` score cap exports:

```text
rows=175,193
keep_rows=167,673
skip_rows=7,520
skip_fraction=4.2924%
```

The skip distribution is sharply concentrated in the low prealign score tail:

```text
prealign_score <60:
  keep=66 skip=967 skip_fraction=93.61%

prealign_score 60-79:
  keep=5,878 skip=6,553 skip_fraction=52.72%

prealign_score >=80:
  skip=0
```

Target size shows a similar tail signal:

```text
target_size <55:
  keep=56,652 skip=1,157 skip_fraction=2.00%

target_size 55-64:
  keep=7,704 skip=1,921 skip_fraction=19.96%

target_size 65-79:
  keep=18,934 skip=4,442 skip_fraction=19.00%

target_size >=80:
  skip=0
```

This confirms that the current cap is mostly removing low-score and short-target
attempts in the smoke workload. It does not yet prove that a fixed threshold is
safe. A threshold rule still needs to protect stability and nt_score top5,
because earlier cap sweeps showed those contracts fail before score when the
cap becomes aggressive.

## Explicit Minimum Prealign Score Sweep

The diagnostic threshold:

```text
FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=N
```

was tested on the chr22 10m-12m smoke workload without the score-count cap. This
directly answers whether candidates below an absolute `prealign_score` can skip
traceback.

```text
threshold  traceback  reduction  score  stability  nt_score  missing  extra
60         174,160    1,033      true   true       true      0        0
70         171,076    4,117      true   true       true      18       0
80         161,729    13,464     true   true       true      214      0
90         141,086    34,107     true   true       true      949      1
100        110,263    64,930     true   true       true      3,150    12
110        80,859     94,334     true   false      true      5,296    1
120        58,470     116,723    true   false      true      6,623    2
130        43,673     131,520    true   false      true      7,371    1
140        33,900     141,293    true   false      true      7,766    2
160        20,841     154,352    true   false      false     8,083    0
200        6,184      169,009    false  false      false     8,180    1
```

For this smoke workload, `min_prealign_score=100` is the highest tested threshold
that preserves all three top5 contracts. `110` is the first failing point, and
the first contract to fail is stability. This matches the earlier cap sweep:
score is relatively robust, while stability is the limiting contract.

This is not enough to enable a real runtime rule. It is enough to justify the
next characterization on chr22/full workload:

```text
candidate thresholds:
  80, 90, 100

hard gate:
  top5_score_equal=true
  top5_stability_equal=true
  top5_nt_score_equal=true
```

## Full chr22 Minimum Prealign Score Sweep

The same explicit threshold was then tested on full chr22/H19:

```text
baseline GASAL2 wall: 70.154883s
baseline traceback requests: 6,910,419
```

Result:

```text
threshold  wall       wall_ratio  traceback  reduction  reduction%  score  stability  nt_score  missing  extra
80         59.545284  0.848769    6,291,508  618,911    8.9562%    true   true       true      11,421   4,378
90         56.370964  0.803522    5,502,959  1,407,460  20.3672%   true   true       true      34,764   4,205
100        53.283699  0.759515    4,276,181  2,634,238  38.1198%   true   true       true      141,840  3,034
```

For the chr22 top5 contract, `min_prealign_score=100` is a strong positive
result:

```text
top5_score_equal=true
top5_stability_equal=true
top5_nt_score_equal=true
traceback reduction=2,634,238
wall improvement vs GASAL2 baseline=70.15s -> 53.28s
```

The full output drift is large:

```text
missing rows=141,840
extra rows=3,034
```

So this threshold is only a top5-contract candidate. It is not a full output
equivalence candidate and should remain default-off unless the accepted contract
is explicitly top5-only.

## Full chr22 Boundary

The full chr22 boundary was then refined above `100`:

```text
threshold  wall       wall_ratio  traceback  reduction  reduction%  score  stability  nt_score  missing  extra
105        51.617435  0.735764    3,648,537  3,261,882  47.2024%   true   true       true      204,540  2,511
110        49.746986  0.709102    3,056,531  3,853,888  55.7692%   true   true       true      252,420  1,965
115        49.242311  0.701909    2,533,341  4,377,078  63.3403%   true   true       true      292,544  1,472
116        48.483698  0.691095    2,441,113  4,469,306  64.6749%   true   true       true      298,468  1,396
117        48.478171  0.691016    2,356,930  4,553,489  65.8931%   true   false      true      304,131  1,302
118        48.432482  0.690365    2,268,854  4,641,565  67.1676%   true   false      true      309,963  1,217
119        48.741935  0.694776    2,186,508  4,723,911  68.3593%   true   false      true      315,180  1,143
120        47.861425  0.682225    2,108,617  4,801,802  69.4864%   true   false      true      319,674  1,071
```

Current best no-guard top5-safe point:

```text
FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=116

traceback requests:
  6,910,419 -> 2,441,113

wall:
  70.154883s -> 48.483698s

top5:
  score/stability/nt_score all equal
```

The first failing threshold is `117`, and again the first failing contract is
stability. The missing baseline stability top rows at threshold `117` are:

```text
rank 3:
  Score=116 Nt=61 MeanStability=3.35574
  Rule=5 Strand=ParaPlus

rank 7:
  Score=115 Nt=50 MeanStability=3.34
  Rule=5 Strand=ParaPlus
```

This explains the boundary: the stability top list still depends on low-score
but very stable short rows.

## Short-Target Guard Probe

A narrow guard was added for characterization:

```text
FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MIN_PREALIGN_SCORE=N
FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MAX_TARGET_SIZE=M
```

It keeps candidates below the main min-score threshold when:

```text
attempt.prealign_score >= N
attempt.target_size <= M
```

Probe result:

```text
main threshold=120
guard prealign>=115, target_size<=70:
  traceback=2,314,679
  score/stability/nt_score=true/false/true

main threshold=120
guard prealign>=115, target_size<=120:
  traceback=2,533,341
  score/stability/nt_score=true/true/true

main threshold=125 or 130
guard prealign>=115, target_size<=120:
  traceback=2,533,341
  score/stability/nt_score=true/true/true
```

The wider guard repairs stability, but it collapses to the same traceback count
as `min_prealign_score=115`. It does not beat the simpler no-guard threshold
`116`. The current best candidate therefore remains the simple threshold:

```text
FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=116
```
