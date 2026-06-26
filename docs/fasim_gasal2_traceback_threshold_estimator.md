# Fasim GASAL2 Traceback Threshold Estimator

## Purpose

This checkpoint adds an offline query-specific threshold estimator for GASAL2
traceback pruning. It replaces the idea of a reusable fixed threshold with a
calibration workflow:

```text
same query / same scoring / same top5 contract
  -> threshold sweep
  -> highest passing threshold
  -> first failing stability boundary
```

It is not a runtime preset and it does not enable pruning by itself.

The intended integration point is a calibration preflight before a full
chromosome or sharded run, not a manually reused number.

## Tool

```bash
python3 scripts/estimate_fasim_gasal2_traceback_threshold.py \
  --summary sweep_summary.tsv \
  --query-label H19 \
  --query-fasta H19.fa \
  --require-failing-boundary
```

For an end-to-end calibration preflight:

```bash
BIN=./fasim_longtarget_gasal2 \
DNA=targets.fa \
RNA=query.fa \
WORK=.tmp/traceback_threshold_calibration \
bash scripts/calibrate_fasim_gasal2_traceback_threshold.sh
```

The topK-lite wrapper can run that preflight before the full run:

```bash
TRACEBACK_THRESHOLD_CALIBRATE=1 \
TRACEBACK_THRESHOLD_CALIBRATION_MAX_BASES=2000000 \
TRACEBACK_THRESHOLD_CALIBRATION_WINDOWS=8 \
DNA=targets.fa \
RNA=query.fa \
OUT=.tmp/fasim_gasal2_top5 \
bash scripts/run_fasim_gasal2_topk_lite.sh
```

When `TRACEBACK_THRESHOLD_CALIBRATION_MAX_BASES` is positive, the calibration
target is sampled as evenly spaced windows across the selected target records,
not just as a prefix. This avoids single-record chromosome cases where the
first few megabases contain no GASAL2 traceback work. The sampler writes:

```text
<calibration work>/calibration_target_windows.tsv
<calibration work>/calibration_target_sample_metrics.txt
```

The estimator also fails closed when the sampled baseline does not contain
enough traceback work. The wrapper knob is:

```bash
TRACEBACK_THRESHOLD_CALIBRATION_MIN_TRACEBACK_REQUESTS=1
```

If a same-query baseline/probe has already produced topK rows or other
coordinate anchors, the preflight can enrich the sample around those risk
coordinates:

```bash
TRACEBACK_THRESHOLD_CALIBRATION_ANCHOR_TSV=baseline_topk_rows.tsv
TRACEBACK_THRESHOLD_CALIBRATION_ANCHOR_WINDOW_BASES=250000
TRACEBACK_THRESHOLD_CALIBRATION_ANCHOR_MAX_WINDOWS=8
```

The anchor TSV is expected to contain `StartInGenome` / `EndInGenome` columns
and optionally `Chr`. Anchor windows are sampled before the remaining uniform
windows. This is still a same-query calibration workflow; the anchors must come
from the same query/scoring/top5 contract, not from a different lncRNA.

The input is the existing threshold sweep TSV shape:

```text
threshold
traceback_requests
traceback_reduction
traceback_reduction_fraction
wall_seconds
vs_baseline_gasal2_wall
top5_score_equal
top5_stability_equal
top5_nt_score_equal
missing_rows
extra_rows
```

`wall_seconds` and `vs_baseline_gasal2_wall` are optional. The top5 equality
columns are required.

## Output

The estimator emits key/value metrics:

```text
decision=query_specific_threshold_candidate
recommended_threshold=<highest passing threshold>
first_failing_threshold=<lowest failing threshold above recommendation>
first_failing_contracts=stability
recommended_threshold_is_query_specific=1
runtime_recommendation=none_without_same_query_validation
```

If the sweep has no failing threshold above the highest passing threshold, the
decision is:

```text
decision=threshold_lower_bound_only_expand_sweep
```

That means the sweep did not bracket the safety boundary and should be expanded
before making even a query-specific pruning decision.

## Interpretation

The estimator deliberately does not output a general recommended runtime.

For H19, the current boundary is:

```text
recommended_threshold = 116
first_failing_threshold = 117
first_failing_contracts = stability
```

For another lncRNA, the result can differ. The only acceptable reuse is:

```text
run same-query threshold-0 GASAL2 baseline
run a threshold sweep for that query
use this estimator to find the query-specific boundary
```

The important scientific signal is that stability top5 is the limiting
contract. A future general optimization should use a query-normalized
stability-risk feature or certificate, not a hard-coded raw prealign score.

The wrapper only injects the calibrated threshold into the formal run after the
preflight estimator emits a usable query-specific threshold. With
`TRACEBACK_THRESHOLD_CALIBRATION_REQUIRE_BOUNDARY=1`, the calibration must also
observe a failing threshold above the recommendation, so lower-bound-only sweeps
fail closed instead of becoming runtime settings. If calibration fails closed,
the wrapper continues the formal run without injecting
`FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE`.

On chr22/H19, uniform 2 Mb / 8-window sampling had traceback signal but did not
observe the stability boundary. Using same-query topK rows as anchors produced:

```text
recommended_threshold = 116
first_failing_threshold = 117
first_failing_contracts = stability
```

and the formal chr22 run preserved the topK digest while reducing traceback
requests from `6,835,013` to `2,437,027`.

## Checks

```bash
make check-fasim-gasal2-traceback-threshold-estimator
make check-fasim-gasal2-traceback-threshold-window-sampler
```
