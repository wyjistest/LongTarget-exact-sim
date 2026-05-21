# Fasim Accelign Endpoint Mismatch Taxonomy

This report classifies endpoint mismatches from the default-off Accelign
`aligner.Align` shadow. CPU `aligner.Align` remains the runtime authority;
Accelign output is not used for Fasim output, scoring, thresholding,
non-overlap, CIGAR/alignment output, SIM-close, or recovery.

Accelign's one-to-one start/end interface returns exclusive end positions.
The Fasim shadow maps them to inclusive endpoints before comparing with SSW:

```text
accelign_ref_end_inclusive = subjectEndPositions_exclusive - 1
accelign_query_end_inclusive = queryEndPositions_exclusive - 1
```

The local Accelign endpoint kernel resolves equal-score endpoints by preferring
the smaller query end. That tie policy can legitimately differ from legacy SSW
while preserving the same alignment score.

## hg38 chr21 + H19 100k Sample

| Metric | Value |
| --- | --- |
| compared requests | 100,000 |
| score mismatches | 0 |
| endpoint mismatches | 1,140 |
| same-score endpoint mismatches | 1,140 |
| ref-end mismatches | 1,140 |
| query-end mismatches | 1,140 |
| both-end mismatches | 1,140 |
| off-by-one mismatches | 0 |
| ref-end GPU before CPU | 0 |
| ref-end GPU after CPU | 1,140 |
| query-end GPU before CPU | 1,140 |
| query-end GPU after CPU | 0 |
| max abs ref-end delta | 58 |
| max abs query-end delta | 2,333 |

## First Mismatch

| Request | CPU score | Accelign score | CPU ref_end | Accelign ref_end | CPU query_end | Accelign query_end |
| --- | --- | --- | --- | --- | --- | --- |
| 21 | 56 | 56 | 18 | 19 | 1,942 | 318 |

## Interpretation

The mismatch is not a score mismatch. Every endpoint mismatch in the 100k
sample has the same CPU and Accelign score, so Accelign is finding an equal
best local-alignment score but selecting a different optimal endpoint.

The mismatch is also not explained by the exclusive-to-inclusive endpoint
adapter. The off-by-one counter is zero, and every mismatch changes both
ref_end and query_end. The direction is consistent: Accelign's ref_end is
after the CPU/SSW endpoint, while Accelign's query_end is before the CPU/SSW
endpoint.

The working explanation is local-alignment tie policy. Accelign's endpoint
reduction explicitly prefers the smaller query end for equal-score maxima.
Legacy SSW/Fasim can choose a different equal-score optimum. That is enough
to preserve score equality while breaking endpoint equality, and endpoints
cannot be treated as a clean contract until the legacy tie policy is matched
or the downstream design avoids using Accelign endpoints as authority.

For now Accelign remains useful only as a default-off score/path feasibility
shadow. It is not endpoint-clean, does not provide CIGAR or alignment strings,
and must not replace `aligner.Align`.

## Boundaries

```text
use Accelign result for output: no
skip CPU aligner.Align: no
CIGAR/alignment-string reconstruction: no
scoring/threshold/non-overlap change: no
GPU DP column AUTO policy change: no
validation relaxation: no
SIM-close/recovery change: no
```
