# Fasim Parasail Aligner Shadow

This PR evaluates a default-off Parasail aligner shadow.
It does not replace `aligner.Align` and does not use Parasail output for production output.

## Local Dependency State

| Metric | Value |
| --- | --- |
| shadow enabled | 1 |
| supported | 1 |
| disabled reason | 0 |
| requests total | 232 |
| requests compared | 128 |
| fallbacks | 0 |
| uses runtime output | 0 |

`disabled_reason=1` means Parasail support was not built into this binary.
This run used a binary built with optional Parasail headers/libs.

## Correctness Guard

| Check | Value |
| --- | --- |
| table digest | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| shadow digest | sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| records | 0 |
| score mismatches | 0 |
| endpoint mismatches | 0 |
| CIGAR mismatches | 128 |
| normalized CIGAR mismatches | 128 |
| digest mismatches | 128 |

## Timers

| Timer | Seconds |
| --- | --- |
| CPU reference | 0.007837 |
| Parasail profile | 0.004488 |
| Parasail align | 0.004403 |
| Parasail CIGAR | 0.000205 |
| Parasail total | 0.009236 |

## Boundary

- Default build links the Parasail stub, so no new dependency is required.
- `FASIM_ALIGNER_PARASAIL_SHADOW=1` only records sampled side-path telemetry.
- Real Parasail comparison requires an explicit `FASIM_PARASAIL_ENABLE=1` build with include/lib flags or `FASIM_PARASAIL_DIR`.
- Parasail shadow is not a real-path candidate until score, endpoint, CIGAR, and digest are exact-clean.
- Secondary score is not supported by the current Parasail SSW shadow contract.
- Current real Parasail shadow is not CIGAR-clean, so it is not a real-path candidate.
- Normalizing `=`/`X` to `M` does not remove the CIGAR mismatch, so this is not only an operator spelling difference.
