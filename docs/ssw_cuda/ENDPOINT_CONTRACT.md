# Modified-SSW Endpoint Contract

## Forward endpoint (L3)

The forward pass scans reference columns from low to high. A new best endpoint
is saved only when the reduced score is strictly greater than the prior global
maximum. Consequently an equal score in a later reference column does not
replace the earlier endpoint.

Within the saved best column, striped lanes are mapped back to logical query
coordinates by:

```text
byte8 logical_read = flat_index / 16 + (flat_index % 16) * segment_length
word16 logical_read = flat_index / 8  + (flat_index % 8)  * segment_length
```

Padding lanes are ignored because they cannot exceed a valid positive best.
Among lanes equal to the best score, the smallest logical query coordinate is
selected. The observable tuple is:

```text
score1, ref_end1, read_end1
```

The next-best reference endpoint is selected outside the `maskLen` region by
a low-to-high scan and strict `>` replacement, so equal next-best values keep
the earliest scanned position. The historical byte and word loops differ at
the upper mask boundary: byte resumes at `edge + 1`, while word resumes at
`edge`. This difference is part of the frozen source behavior.

## Reverse start (L4)

When begin positions are requested, the authority:

1. reverses query bases through `read_end1`;
2. scans reference positions from `ref_end1` down to zero;
3. uses the forward `score1` as the exact terminate value;
4. stops at the first reverse-scanned column whose maximum equals that value;
5. chooses the smallest logical coordinate in the reversed query best column;
6. maps back with `read_begin1 = read_end1 - reverse_read_end`;
7. uses the reverse reference endpoint directly as `ref_begin1`;
8. publishes `score1 = min(forward_score1, reverse_score1)`.

Thus equal-score starts favor the first endpoint encountered in descending
reference order, subject to the query-lane rule. This is not interchangeable
with choosing a lexicographically smallest CIGAR or a smallest genomic start.

### Phase 7 continuation boundary

`ssw_cuda_forward_hybrid_v1` passes the exact L3 tuple into the candidate-only
`AlignFromForward` entry point:

```text
score1, score2, ref_end1, read_end1, ref_end2, numeric_path
```

The entry point validates all coordinates, score widths, and the byte/word
profile before allocating a result. It does not execute `ssw_align` or any CPU
forward recurrence. It begins at the frozen reverse-start algorithm above,
then enters the existing banded traceback routine. The API is compiled only
with `FASIM_WITH_SSW_CUDA_FORWARD_HYBRID`; it is absent from the default CPU
binary. CPU call counters must prove zero forward calls and exactly one reverse
call for each nonzero selected continuation.

## Filters and coordinates

Fasim's default `Filter` requests begin positions and CIGAR, producing flag
`0x0f`. Reverse and traceback are skipped only when the source flag/filter
conditions in `ssw_align` say so. The Phase 2 fixtures use the default filter.

All SSW fields are zero-based and inclusive in the local target window.
Fasim's attempt layer adds `target_start` to `ref_begin1` and `ref_end1` before
triplex conversion. Query coordinates remain local to the complete query. A
TFOsorted row displays one-based coordinates, so fixture coordinate checks use:

```text
display_query_start = read_begin1 + 1
display_query_end   = read_end1 + 1
display_target_start = target_start + ref_begin1 + 1
display_target_end   = target_start + ref_end1 + 1
```

## Attempt identity and threshold/best/last

For each scoreInfo, Fasim evaluates identity-derived windows in fixed round
order starting at 0.6 and incrementing by 0.1. The stable attempt key includes
the transformed workload digest, rule, strand, scoreInfo index, identity round,
target start, and cut length.

Selection is:

```text
threshold     first attempt with alignment.score >= prealign score
best_fallback highest-scoring attempted alignment ending at cutlength - 1
last          final nonzero attempt when no threshold or terminal best exists
```

The best fallback updates only on strict score improvement. Every other call
is recorded as `not_selected`. This selection layer is downstream of the
pre-align scoreInfo grouping and upstream of triplex conversion.
