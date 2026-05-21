# Fasim Accelign Score Precheck Contract Shadow

This report characterizes a call-level Accelign score-only precheck contract. CPU `aligner.Align` remains the runtime authority. The shadow simulates skipping only individual Align calls whose Accelign score is below the CPU score threshold, then compares the side candidate state against the legacy CPU path.

Candidate/output-level filtering is not evaluated as a viable real path here; earlier scaling showed candidate-level false rejects. This shadow asks only whether call-level skips preserve the legacy candidate/emission/output contract.

Workload: `hg38_chr21_H19`. Each mode uses 1 run(s); tables report medians.

## Contract Summary

| Sample size | Requests | Compared requests | Predicted skip calls | False reject calls | False reject candidates | Candidate state mismatches | Emitted record mismatches | Output digest mismatches | Accelign seconds | CPU saved seconds | Net saved seconds | Projected full saved seconds | Score mismatches |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1000 | 979,282 | 1,000 | 553 | 0 | 138 | 138 | 105 | 53 | 0.050577 | 0.023298 | -0.027279 | -26.714000 | 0 |

## Decision

The call-level side replay diverged from the CPU legacy path. Do not implement a real call-level skip without first explaining and eliminating these mismatches.

```text
largest_score_mismatches = 0
largest_false_reject_calls = 0
largest_candidate_state_mismatches = 138
largest_emitted_record_mismatches = 105
largest_output_digest_mismatches = 53
largest_projected_full_saved_seconds = -26.714000
```

## Boundaries

```text
skip CPU aligner.Align in this PR: no
use Accelign endpoints: no
use Accelign for CIGAR/alignment string: no
use Accelign output for final records: no
candidate/output-level filtering: no
change scoring/threshold/non-overlap/output: no
change GPU AUTO/SIM-close/recovery: no
relax validation: no
mandatory Accelign dependency: no
```
