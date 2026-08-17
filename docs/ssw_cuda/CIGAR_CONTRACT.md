# Modified-SSW Banded Traceback and CIGAR Contract

## Banded DP and canonical CIGAR (L5)

After forward and reverse endpoints are fixed, the authority aligns exactly
the inclusive endpoint rectangle. Its initial half-band width is:

```text
abs(reference_span - query_span) + 1
```

For each iteration the allocated score width is `2 * band_width + 3` and the
direction width is `2 * band_width + 1`. If the maximum score found in the
band is below the endpoint score, the half-band width doubles and the matrix
is recomputed. The first iteration with `maximum_score >= endpoint_score` is
used for traceback. The trace records every attempted width, observed maximum,
and target score.

The scalar cells use local zero and affine E/F values. Equal-value decisions
are source-defined:

```text
E open versus extend:       extend wins equality
F open versus extend:       extend wins equality
E versus F for gap H:       F wins equality
diagonal versus best gap:   diagonal wins equality
```

Direction codes are:

```text
1 diagonal/M
2 extend E/I
3 open E/I from H
4 extend F/D
5 open F/D from H
```

These rules, including their order, are contract fields. “Same as SSW” is not
a sufficient replacement specification.

## Traceback and merge (L5)

Traceback begins at the lower-right corner of the endpoint rectangle with H
state and proceeds while the query-row index is greater than zero. Direction
codes update the query/reference coordinates and next state exactly as above.
Consecutive identical operations are run-length merged while traversing in
reverse. At the stop boundary:

- if the active operation is M, its run receives one additional base;
- otherwise the active I/D run is emitted and a terminal `1M` is appended.

The operation vector is then reversed to forward order. Fasim's active
`Align(query, ref, ...)` overload does not call `mark_mismatch`, so the
authority CIGAR used by triplex conversion contains M/I/D rather than a
postprocessed `=/X/S` representation.

Each operation is stored in BAM form:

```text
encoded = (length << 4) | opcode
M=0, I=1, D=2
```

Adjacent equal operations are represented by one encoded element. The JSON
trace reports the printable CIGAR, operation count, and an FNV-1a-64 identity
digest of the printable bytes.

## LongTarget emitted row (L6)

After threshold/best/last selection, the selected L5 alignment is converted by
`convertMyTriplex`. Every converted row carries its source attempt key through
the existing local sort, deduplication, top-N and identity/stability/Nt filters.
Only a row actually appended to the caller's `triplex_list` is an L6 emitted
row. A selected alignment that fails conversion or those filters has an empty
`emitted_rows` array.

Each emitted-row record contains the one-based query and target coordinates,
direction, strand/reverse/rule, Score, Nt, MeanIdentity, MeanStability, aligned
TFO/TTS, their gap-stripped forms, and a complete `triplex_l6_v1` row digest.
The digest is FNV-1a-64 over a tab-separated payload beginning with the literal
`triplex_l6_v1` and continuing with those fields in schema order. It binds the
float values at `std::numeric_limits<float>::max_digits10` precision. Outer
file metadata such as chromosome and genomic offsets is not yet available at
this call boundary and is not part of L6.

## Failure behavior

An invalid direction emits the existing traceback error and returns null.
When tracing is enabled the call record is marked failed; tracing does not
replace, repair, or retry the authority result. No automatic band or alignment
retry exists outside the source-defined width doubling above.

For the Phase 7 forward hybrid, a nonzero selected L3 tuple must enter this
same reverse-start and banded traceback implementation exactly once. The
continuation is a candidate-only entry point around frozen L4/L5 code; it does
not define a second CIGAR tie policy. A null path, score/endpoint drift, call
counter drift, or invalid externally supplied tuple is a hard candidate
failure. It cannot trigger a complete CPU authority fallback.
