# Fasim Accelign Aligner Shadow

This report characterizes a default-off Accelign float shadow for
`aligner.Align` requests under `FASIM_TRANSFERSTRING_TABLE=1` and
`FASIM_GPU_DP_COLUMN_AUTO=1`. CPU `aligner.Align` remains the runtime
authority; Accelign output is not used for scoring, thresholding,
non-overlap, CIGAR/alignment output, SIM-close, recovery, or final output.

Build used:

```text
FASIM_ACCELIGN_ENABLE=1
FASIM_ACCELIGN_DIR=.tmp/accelign_12_5_test/Accelign
CUDA Toolkit 12.5
GPU arch sm_89
```

## Fixture Result

Workload: `hg38_chr21_softmask_compact_region` with `H19.fa`.

```text
fasim_aligner_align_calls = 232
fasim_aligner_align_seconds = 0.014113

fasim_aligner_accelign_shadow_enabled = 1
fasim_aligner_accelign_shadow_supported = 1
fasim_aligner_accelign_shadow_requests_total = 232
fasim_aligner_accelign_shadow_requests_compared = 232
fasim_aligner_accelign_shadow_cells = 57,747,232
fasim_aligner_accelign_shadow_h2d_bytes = 678,488
fasim_aligner_accelign_shadow_d2h_bytes = 2,784
fasim_aligner_accelign_shadow_kernel_seconds = 0.00610049
fasim_aligner_accelign_shadow_total_seconds = 0.026977
fasim_aligner_accelign_shadow_cpu_reference_seconds = 0.014113
fasim_aligner_accelign_shadow_score_mismatches = 0
fasim_aligner_accelign_shadow_endpoint_mismatches = 2
fasim_aligner_accelign_shadow_total_mismatches = 2
fasim_aligner_accelign_shadow_uses_runtime_output = 0
```

## Contract

| Field | Status | Notes |
| --- | --- | --- |
| score | clean on fixture | `score_mismatches=0` |
| endpoints | not clean | `endpoint_mismatches=2`; do not treat endpoint contract as ready |
| CIGAR | unsupported | Accelign does not provide full traceback/CIGAR here |
| alignment string | unsupported | CPU `aligner.Align` remains required |
| runtime output | unchanged | shadow result is never consumed |

## Timing Interpretation

Accelign kernel time is lower than the sampled CPU reference on this small
fixture, but total shadow time is slower because this first integration uses a
simple one-to-one layout that duplicates the query for every sampled request
and includes staging overhead. This is a feasibility shadow, not a runtime
speedup claim.

## Decision

Accelign is viable enough to keep as a score-only Fasim shadow candidate:
CUDA 12.5 can compile and run the float path, and the Fasim-internal score
contract is clean on the small hg38/H19 fixture.

Do not use Accelign for runtime output or as a drop-in `aligner.Align`
replacement. Endpoint mismatch taxonomy and a more efficient one-query/many-
targets layout are required before any broader performance claim.
