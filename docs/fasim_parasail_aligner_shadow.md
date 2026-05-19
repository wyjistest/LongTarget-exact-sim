# Fasim Parasail Aligner Shadow

This PR adds a default-off Parasail aligner shadow gate.
It does not replace `aligner.Align` and does not use Parasail output for production output.

## Local Dependency State

| Metric | Value |
| --- | --- |
| shadow enabled | 1 |
| supported | 0 |
| disabled reason | 1 |
| requests total | 232 |
| requests compared | 128 |
| fallbacks | 128 |
| uses runtime output | 0 |

`disabled_reason=1` means Parasail support was not built into this binary.
That is the expected default in this local environment because `parasail.h`/`libparasail` are not installed.

## Correctness Guard

| Check | Value |
| --- | --- |
| table digest | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| shadow digest | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| records | 0 |
| score mismatches | 0 |
| endpoint mismatches | 0 |
| CIGAR mismatches | 0 |
| digest mismatches | 0 |

## Timers

| Timer | Seconds |
| --- | --- |
| CPU reference | 0.007651 |
| Parasail profile | 0.000000 |
| Parasail align | 0.000000 |
| Parasail CIGAR | 0.000000 |
| Parasail total | 0.000001 |

## Boundary

- Default build links the Parasail stub, so no new dependency is required.
- `FASIM_ALIGNER_PARASAIL_SHADOW=1` only records sampled side-path telemetry.
- Real Parasail comparison requires an explicit `FASIM_PARASAIL_ENABLE=1` build with include/lib flags.
- Parasail shadow is not a real-path candidate until score, endpoint, CIGAR, and digest are exact-clean.
- Secondary score is not supported by the current Parasail SSW shadow contract.
