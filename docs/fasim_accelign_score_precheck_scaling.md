# Fasim Accelign Score-Only Precheck Scaling

This report extends the Accelign score-only precheck shadow with scaling and candidate-level safety telemetry. CPU `aligner.Align` remains the runtime authority; no Align calls are skipped and Accelign endpoints are not used.

Call-level false rejects measure whether Accelign would reject a CPU score-pass Align call. Candidate-level false rejects are stricter: they flag candidates where all sampled Align calls are predicted reject but the CPU authority still reaches the candidate reconstruction path. Any candidate-level false reject is a no-go for candidate/output filtering.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Scaling Summary

| Sample size | Compared calls | Predicted reject calls | False reject calls | Predicted reject candidates | False reject candidates | Accelign total seconds | CPU saved seconds | Net saved seconds | Projected full saved seconds | Digest affected | Score mismatches |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10000 | 10,000 | 4,835 | 0 | 1,208 | 1,208 | 0.189680 | 0.199134 | 0.009454 | 0.925786 | 0 | 0 |
| 50000 | 50,000 | 28,176 | 0 | 7,044 | 7,044 | 0.762224 | 1.181550 | 0.419322 | 8.212690 | 0 | 0 |

## Decision

Candidate-level false rejects appeared. Do not promote this to a candidate/output-level filter; keep it as shadow unless a narrower call-level real path with validation is designed separately.

```text
largest_false_reject_calls = 0
largest_false_reject_candidates = 7,044
largest_projected_full_saved_seconds = 8.212690
```

## Boundaries

```text
skip CPU aligner.Align: no
use Accelign endpoints: no
use Accelign output for final records: no
change scoring/threshold/non-overlap/output: no
change GPU AUTO/SIM-close/recovery: no
relax validation: no
```
