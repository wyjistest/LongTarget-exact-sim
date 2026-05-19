# Fasim Accelign Score-Only Precheck Shadow

This report characterizes a default-off Accelign score-only precheck shadow. CPU `aligner.Align` remains the runtime authority and still runs for every request; Accelign scores are used only after the fact to simulate a per-align-call score gate.

The simulated reject is call-scoped: `Accelign score < scoreInfo.score` means that individual CPU Align call could not satisfy the immediate `alignment.sw_score >= scoreInfo.score` break condition. This is not a candidate/output-level skip proof because later cut lengths, CIGAR, traceback, NT checks, and final non-overlap still remain CPU-owned.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Score-Gate Simulation

| Sample cap | Requests | Compared | Unsupported | CPU reference seconds | Accelign kernel seconds | Accelign total seconds | Predicted reject calls | True reject calls | False reject calls | False keep calls | Estimated CPU calls saved | Estimated CPU seconds saved | Net estimated seconds saved | Accelign vs CPU speedup |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10000 | 979,282 | 10,000 | 969,282 | 0.449884 | 0.115411 | 0.189680 | 4,835 | 4,835 | 0 | 0 | 4,835 | 0.199134 | 0.009454 | 2.37x |
| 50000 | 979,282 | 50,000 | 929,282 | 2.264930 | 0.527653 | 0.762224 | 28,176 | 28,176 | 0 | 0 | 28,176 | 1.181550 | 0.419322 | 2.97x |

## Contract

| Sample cap | Score mismatches | Endpoint contract | Uses runtime output | Query reuse active |
| --- | --- | --- | --- | --- |
| 10000 | 0 | 0 | 0 | 1 |
| 50000 | 0 | 0 | 0 | 1 |

## Staging

| Sample cap | H2D bytes | D2H bytes | Query staging bytes | Target staging bytes | Query share of H2D | Target share of H2D |
| --- | --- | --- | --- | --- | --- | --- |
| 10000 | 1,698,378 | 40,000 | 902,652 | 675,726 | 53.15% | 39.79% |
| 50000 | 8,271,954 | 200,000 | 4,350,164 | 3,321,790 | 52.59% | 40.16% |

## Decision

The score-gate simulation is score-clean with zero call-level false rejects and positive net estimated savings at the largest sample. The companion scaling report found candidate-level false rejects, so do not promote this to candidate/output-level filtering. Keep this as shadow unless a narrower call-level real path with validation/fallback is designed separately.

```text
largest_predicted_reject_calls = 28,176
largest_false_reject_calls = 0
largest_net_est_seconds_saved = 0.419322
candidate_level_filter_safe = no
```

## Boundaries

```text
use Accelign result for output: no
use Accelign endpoints: no
skip CPU aligner.Align in this PR: no
claim candidate/output-level filtering: no
CIGAR/alignment-string reconstruction: no
scoring/threshold/non-overlap change: no
GPU DP column AUTO policy change: no
validation relaxation: no
mandatory Accelign dependency: no
```
