# Fasim Accelign Score-Only Precheck Shadow

This report characterizes a default-off Accelign score-only precheck shadow. CPU `aligner.Align` remains the runtime authority and still runs for every request; Accelign scores are used only after the fact to simulate a per-align-call score gate.

The simulated reject is call-scoped: `Accelign score < scoreInfo.score` means that individual CPU Align call could not satisfy the immediate `alignment.sw_score >= scoreInfo.score` break condition. This is not a candidate/output-level skip proof because later cut lengths, CIGAR, traceback, NT checks, and final non-overlap still remain CPU-owned.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Score-Gate Simulation

| Sample cap | Requests | Compared | Unsupported | CPU reference seconds | Accelign kernel seconds | Accelign total seconds | Predicted reject calls | True reject calls | False reject calls | False keep calls | Estimated CPU calls saved | Estimated CPU seconds saved | Net estimated seconds saved | Accelign vs CPU speedup |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10000 | 979,282 | 10,000 | 969,282 | 0.452303 | 0.110370 | 0.184157 | 4,835 | 4,835 | 0 | 0 | 4,835 | 0.201002 | 0.016846 | 2.46x |

## Contract

| Sample cap | Score mismatches | Endpoint contract | Uses runtime output | Query reuse active |
| --- | --- | --- | --- | --- |
| 10000 | 0 | 0 | 0 | 1 |

## Staging

| Sample cap | H2D bytes | D2H bytes | Query staging bytes | Target staging bytes | Query share of H2D | Target share of H2D |
| --- | --- | --- | --- | --- | --- | --- |
| 10000 | 1,698,378 | 40,000 | 902,652 | 675,726 | 53.15% | 39.79% |

## Decision

The score-gate simulation is score-clean with zero false rejects and positive net estimated savings at the largest sample. Next work can design a default-off real precheck with validation/fallback, but only for the same call-scoped score gate unless a separate candidate/output proof is added.

```text
largest_predicted_reject_calls = 4,835
largest_false_reject_calls = 0
largest_net_est_seconds_saved = 0.016846
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
