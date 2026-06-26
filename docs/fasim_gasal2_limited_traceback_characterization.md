# Fasim GASAL2 Limited Traceback Characterization

This checkpoint characterizes a default-off GASAL2 top5 path optimization:

```text
FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_MAX_SCOREINFOS=N
FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_MODE=score|score_spread
FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_ATTEMPT_EXPORT=/path/to/attempts.tsv
FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=N
FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MIN_PREALIGN_SCORE=N
FASIM_TOP5_GASAL2_TRACEBACK_GUARD_MAX_TARGET_SIZE=N
```

The option limits how many scoreInfo-selected GASAL2 attempts proceed to
traceback after the GASAL2 score prepass. It is evaluated only under the scoped
top5 contract.

## Scope

This is not a replacement for `aligner.Align()`.

It does not claim full `.lite` / `TFOsorted` row equivalence. It does not make
GASAL2 endpoint, CIGAR, traceback, scoring, digest, or output authoritative.
The path remains default-off and diagnostic until a broader contract is defined
and validated.

The scoped contract checked here is:

```text
top5 score summary equal
top5 stability summary equal
top5 nt_score summary equal
GASAL2 fallbacks = 0
length guard fallbacks = 0
traceback request count reduced
```

## Implementation Shape

After the GASAL2 score prepass chooses traceback candidates, the limited
traceback pass caps the candidate list before `run_traceback`.

Current modes:

```text
score:
  keep the highest prealign_score candidates, with deterministic tie-breaks

score_spread:
  keep a mix of high-score candidates and positions spread through the original
  candidate order
```

The active characterized setting is:

```text
FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_MAX_SCOREINFOS=65536
FASIM_TOP5_GASAL2_LIMITED_TRACEBACK_MODE=score
```

The optional attempt export is diagnostic only. It writes one TSV row for each
pre-traceback candidate considered by the limited traceback cap and marks the
candidate as `keep` or `skip`. The export uses only pre-traceback fields:

```text
batch_id
position
attempt_index
decision
prealign_score
scoreinfo_index
start
cutlength
target_size
nt_min_length
target_end_required_for_fallback
target_offset
target_length
```

Smaller caps were tried during characterization and failed the top5 contract for
this workload shape. The cap is therefore conservative.

The `FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE` threshold is also
default-off and diagnostic. It skips traceback candidates whose pre-traceback
`attempt.prealign_score` is below `N`. It is intended for characterization only;
it is not a production rule.

The guard envs are a diagnostic escape hatch for testing whether short,
near-threshold candidates can preserve stability top5 while the main threshold
is raised. Current chr22 characterization did not find a guard that beats the
simple no-guard threshold.

## Smoke Result

Workload:

```text
chr22 slice 10m-12m
query: H19
mode: GASAL2 top5 scoreInfo + staged first prune
limited traceback max scoreInfos: 65536
limited traceback mode: score
```

Result:

```text
baseline traceback requests: 175,193
limited traceback requests: 167,673
traceback reduction: 7,520

top5_score_equal: true
top5_stability_equal: true
top5_nt_score_equal: true

baseline rows: 8,291
candidate rows: 8,213
missing rows: 78
extra rows: 0
```

The smoke confirms the scoped top5 contract and also shows that full row output
already drifts.

## Full chr22 Result

Workload:

```text
target: chr22
query: H19
mode: GASAL2 top5 scoreInfo + staged first prune
limited traceback max scoreInfos: 65536
limited traceback mode: score
```

Result:

```text
baseline GASAL2 wall: 70.154883s
limited traceback wall: 60.340401s
limited / baseline GASAL2 wall: 0.860103
speedup vs baseline GASAL2: 1.16x

baseline traceback requests: 6,910,419
limited traceback requests: 6,160,384
traceback reduction: 750,035
traceback reduction fraction: 10.8537%

top5_score_equal: true
top5_stability_equal: true
top5_nt_score_equal: true

GASAL2 fallbacks: 0
length guard fallbacks: 0

missing rows: 10,112
extra rows: 4,399
```

Phase telemetry from the limited run:

```text
fasim_gasal2_total_seconds: 20.6218
flush_total_seconds: 54.7833
gasal2_extend_wall_seconds: 30.8496
gasal2_convert_wall_seconds: 7.5042
output_write_seconds: 0.542172
```

## Decision

Limited traceback is a real but modest positive result for the current GASAL2
top5 path:

```text
top5 contract:
  clean for the characterized chr22 run

traceback work:
  reduced by 10.85%

wall time:
  70.15s -> 60.34s against the GASAL2 full-plain baseline
  about 1.16x faster than baseline GASAL2

full output:
  not equivalent
```

This does not solve the remaining CPU-side overhead and does not turn GASAL2
into a full Fasim output replacement. It is best treated as a default-off
milestone for reducing traceback work under the already-scoped top5 contract.

## Min Prealign Score Boundary

The stronger diagnostic rule is:

```text
FASIM_TOP5_GASAL2_TRACEBACK_MIN_PREALIGN_SCORE=116
```

This rule skips traceback for candidates whose GASAL2 score-prepass
`prealign_score` is below the threshold. It is still top5-only and
default-off. It is not a full `.lite` / `TFOsorted` equivalence rule.

Full chr22/H19 boundary:

```text
baseline GASAL2 wall: 70.154883s
threshold 116 wall: 48.483698s
threshold 116 / baseline GASAL2 wall: 0.691095
speedup vs baseline GASAL2: 1.45x

baseline traceback requests: 6,910,419
threshold 116 traceback requests: 2,441,113
traceback reduction: 4,469,306
traceback reduction fraction: 64.6749%

top5_score_equal: true
top5_stability_equal: true
top5_nt_score_equal: true

threshold 117:
  top5_score_equal: true
  top5_stability_equal: false
  top5_nt_score_equal: true
```

The first observed chr22 failure at threshold 117 is the stability top5. The
missing stability rows include low-score but high-stability short rows, so the
boundary is not captured by score alone once the threshold exceeds 116.

Chr21/H19 was also checked against a same-run GASAL2 threshold-0 baseline,
because older chr21 CPU-summary artifacts were not generated by the same direct
GASAL2 configuration:

```text
threshold 0 wall: 61.096863s
threshold 0 traceback requests: 6,927,591

threshold 116 wall: 49.746864s
threshold 116 speedup vs threshold 0: 1.228x
threshold 116 traceback requests: 2,495,254
threshold 116 traceback reduction vs threshold 0: 4,432,337

threshold 117 wall: 49.356235s
threshold 117 speedup vs threshold 0: 1.238x
threshold 117 traceback requests: 2,417,109
threshold 117 traceback reduction vs threshold 0: 4,510,482

threshold 116 and 117 both preserve chr21 local GASAL2-baseline top5 score,
stability, and nt_score.
```

Merged chr21+chr22 GASAL2-baseline top5 result:

```text
threshold 116:
  baseline rows: 669,033
  candidate rows: 149,497
  missing rows: 517,066
  extra rows: 208
  top5_score_equal: true
  top5_stability_equal: true
  top5_nt_score_equal: true

threshold 117:
  baseline rows: 669,033
  candidate rows: 139,831
  missing rows: 526,670
  extra rows: 201
  top5_score_equal: true
  top5_stability_equal: false
  top5_nt_score_equal: true
```

Current interpretation:

```text
threshold 116:
  best observed simple fixed-threshold top5-only candidate for chr21+chr22

threshold 117:
  not safe for the top5 stability contract

full output:
  intentionally not equivalent
```

The practical ceiling of this specific pruning line is bounded by the remaining
non-traceback cost. On chr22, threshold 116 removes about 65% of traceback
requests but only improves wall time from about 70.15s to 48.48s. Pushing the
threshold higher gives little wall-time headroom and breaks the stability top5
contract unless a stronger stability-aware guard is added.

This is not a recommendation to hard-code `116` as a universal runtime
threshold. A follow-up score-band frontier probe showed that
`threshold=120 + rescue score 115..116,target_size<=120` reduces chr22 traceback
further to 2,285,028 and wall to 46.933625s, but fails `top5_stability_equal`.
See `docs/fasim_gasal2_dynamic_traceback_frontier_characterization.md`.

## Verification

Relevant gates:

```bash
make check-fasim-gasal2-limited-traceback-smoke
make characterize-fasim-gasal2-limited-traceback-chr22
make check-fasim-gasal2-limited-traceback-chr22-result
make check-fasim-gasal2-traceback-min-prealign-score-chr22-boundary-result
make check-fasim-gasal2-traceback-min-prealign-score-chr21-chr22-result
```
