# Fasim GASAL2 Traceback Min-Prealign H19 Calibration

## Decision

```text
decision = no_general_runtime_recommendation
artifact = H19-only traceback pruning calibration
scope    = chr21/chr22 H19 top5 contract
runtime  = not recommended as a general preset
```

The fixed threshold:

```text
FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=116
```

is useful evidence, but it is not a general runtime recommendation. It is an
H19-calibrated boundary under the current GASAL2 score-prepass and top5
score/stability/Nt-score summaries.

For another lncRNA, the number can move because the prealign-score distribution,
short-row stability behavior, and top5 stability boundary can all change. Using
`116` without same-query calibration would be tuning to H19.

## What It Proves

Full chr22/H19 boundary:

```text
baseline GASAL2 wall        = 70.154883 s
threshold 116 wall         = 48.483698 s
wall reduction             = 21.671185 s / 30.8905%
speedup                    = 1.447x

baseline traceback requests = 6,910,419
threshold 116 traceback     = 2,441,113
traceback reduction         = 4,469,306 / 64.6749%

top5_score_equal     = true
top5_stability_equal = true
top5_nt_score_equal  = true
```

The H19 boundary is tight. The next integer threshold fails stability:

```text
threshold 117:
  traceback requests     = 2,356,930
  top5_score_equal       = true
  top5_stability_equal   = false
  top5_nt_score_equal    = true
```

Merged chr21+chr22 top5 result:

```text
threshold 116:
  top5_score_equal     = true
  top5_stability_equal = true
  top5_nt_score_equal  = true

threshold 117:
  top5_score_equal     = true
  top5_stability_equal = false
  top5_nt_score_equal  = true
```

## Why This Is Not A Product Optimization

```text
not reusable across lncRNAs without calibration
not full .lite / TFOsorted row equivalent
not a full output digest contract
not GASAL2 endpoint/CIGAR/traceback authority
not a default-on policy
not a recommended preset for arbitrary targets
```

The chr22 full-row drift is large at threshold `116`; it is only clean for the
scoped top5 summaries. That is too narrow for a general runtime knob.

## What It Is Still Useful For

This artifact is useful as a design signal:

```text
traceback tail pruning has large headroom
score-only pruning is limited by stability top5
threshold 117 exposes the first H19 stability failure
future pruning needs a stability-risk feature, not a harder fixed score cutoff
```

For a different lncRNA, the right workflow is:

```text
run same-query threshold-0 GASAL2 baseline
run threshold sweep
find first failing top5 stability boundary
only use the highest passing threshold for that query, if the accepted contract is top5-only
```

The better long-term direction is not hard-coding `116`; it is a calibration
preflight or a pre-traceback stability-risk certificate.

The reusable tooling step is the query-specific estimator:

```bash
python3 scripts/estimate_fasim_gasal2_traceback_threshold.py \
  --summary sweep_summary.tsv \
  --query-label QUERY \
  --query-fasta query.fa \
  --require-failing-boundary
```

This reports a per-query boundary such as `recommended_threshold=116` and
`first_failing_threshold=117` for H19, while keeping
`runtime_recommendation=none_without_same_query_validation`.

The topK-lite wrapper can now run the calibration before the full sharded run:

```bash
TRACEBACK_THRESHOLD_CALIBRATE=1 \
TRACEBACK_THRESHOLD_CALIBRATION_MAX_BASES=2000000 \
TRACEBACK_THRESHOLD_CALIBRATION_WINDOWS=8 \
DNA=targets.fa \
RNA=query.fa \
OUT=.tmp/fasim_gasal2_top5 \
bash scripts/run_fasim_gasal2_topk_lite.sh
```

Positive `TRACEBACK_THRESHOLD_CALIBRATION_MAX_BASES` now means a fixed base
budget sampled as evenly spaced windows across the selected target records, not
a chromosome prefix. Calibration also requires a minimum amount of baseline
traceback work before it can inject a threshold.

For chr22/H19, uniform windows alone were too optimistic: they had traceback
signal, but thresholds through `120` still preserved the sampled top5 contract
and did not bracket the full-run stability boundary. Adding same-query topK
anchors to the calibration sample recovered the known boundary:

```bash
TRACEBACK_THRESHOLD_CALIBRATION_ANCHOR_TSV=baseline_topk_rows.tsv
TRACEBACK_THRESHOLD_CALIBRATION_ANCHOR_WINDOW_BASES=250000
TRACEBACK_THRESHOLD_CALIBRATION_ANCHOR_MAX_WINDOWS=8
```

Anchored chr22 calibration result:

```text
recommended_threshold = 116
first_failing_threshold = 117
first_failing_contracts = stability
```

Formal anchored-auto chr22 result:

```text
baseline wall       = 59.739062 s
auto calibrated     = 37.863297 s
wall reduction      = 36.6189%
traceback requests  = 6,835,013 -> 2,437,027
topK digest equal   = true
```

This does not make `116` general. It shows that a same-query risk-enriched
calibration can estimate the H19 boundary before the formal full run.

## Checks

Static/readiness:

```bash
make check-fasim-gasal2-traceback-min-prealign-h19-calibration
make check-fasim-gasal2-traceback-threshold-estimator
make check-fasim-gasal2-traceback-threshold-window-sampler
```

Underlying characterization gates:

```bash
make check-fasim-gasal2-traceback-min-prealign-score-chr22-boundary-result
make check-fasim-gasal2-traceback-min-prealign-score-chr21-chr22-result
```

Long benchmark artifacts:

```text
.tmp/characterize_fasim_gasal2_traceback_min_prealign_score_chr22_boundary
.tmp/characterize_fasim_gasal2_traceback_min_prealign_score_chr21
.tmp/characterize_fasim_gasal2_traceback_min_prealign_score_chr21_chr22_merge
```
