# Modified-SSW DP Contract

## Scope

This document freezes the observable CPU authority used by the SSW-CUDA
program. The executable and exact source hashes are bound by
`paper/ssw_cuda/cpu_oracle_binary_receipt.json`. The authority implementation
is `fasim/sswNew.cpp`; `reproduce/ssw_cuda/scalar_ssw_reference.py` is a small
diagnostic model and never replaces that implementation.

The Phase 2 authority is the SSE2 build (`-msse2`) with the optional AVX2
runtime disabled. Coordinates are zero based and inclusive unless stated
otherwise.

## L0: inputs and scoring

`StripedSmithWaterman::Aligner` translates ASCII bases using the fixed table in
`fasim/ssw_cpp.cpp`:

```text
A/a -> 0
C/c -> 1
G/g -> 2
T/t -> 3
U/u -> 0
all other bytes in the 128-entry table -> 4 (N/unknown)
```

Bytes outside the table are unsupported. The default Fasim authority creates
`Aligner` without calling `ReBuild`, so the effective values are:

```text
match              = +5
mismatch and N     = -4
gap opening        = 16
gap extension      = 4
maskLen            = 15
score_size         = 2 (byte profile plus word profile)
```

The `parm_O = -12` argument visible at the `fastSIM` call site does not mutate
the `Aligner`; it must not be reported as the SSW gap-opening value. This
contract records the observed value 16.

## Affine local recurrence

For query row `i` and reference column `j`, the conceptual score relation is:

```text
E(i,j) = max(H(i,j-1) - gap_open, E(i,j-1) - gap_extend)
F(i,j) = max(H(i-1,j) - gap_open, F(i-1,j) - gap_extend)
H(i,j) = max(0, H(i-1,j-1) + substitution(i,j), E(i,j), F(i,j))
```

The executable contract is the striped Farrar update order in
`sw_sse2_byte*` and `sw_sse2_word*`, not an arbitrary scalar implementation:

1. diagonal score is formed from the prior H stripe and the query profile;
2. H takes maxima with the stored E and current F;
3. E and F are updated from that H;
4. the lazy-F loop propagates F without updating E, intentionally disallowing
   an adjacent insertion/deletion transition through that correction loop;
5. the column maximum includes values introduced by lazy-F.

The scalar tool models the mathematical frontier for tiny diagnostics. A
scalar/vector disagreement is evidence to inspect, not permission to replace
the vector result.

## L1: per-column maxima

For every reference position, `maxColumn[j]` is the maximum logical H value in
that column after lazy-F. Pre-align returns this complete vector. Selection
uses the vector in increasing reference order.

Trace records always contain:

```text
column_count
maximum_score
column_max_digest_fnv1a64
```

When `FASIM_SSW_ORACLE_TRACE_FULL_COLUMNS=1`, the same record also contains the
integer vector. Its digest is FNV-1a-64 over each value encoded as an unsigned
64-bit little-endian integer, followed by the column count encoded the same
way. This digest is an identity checksum, not a cryptographic claim.

## Byte-first and word-recompute semantics

The score profile is constructed for both numeric paths:

```text
byte8:  unsigned saturating 8-bit lanes, substitution values shifted by bias 4
word16: signed 16-bit substitution addition with nonnegative saturating gaps
```

Pre-align executes byte8 first. If any byte column reaches 255, it recomputes
the entire frontier with word16 and uses only word16 values for downstream
selection. `ssw_align` similarly executes byte8 first and recomputes the full
forward alignment with word16 when the byte best reports 255. The reverse pass
uses the same final numeric width as the forward pass.

Therefore byte8 output in an overflow record is diagnostic; `final_numeric_path`
identifies the contract result. Word scores above the signed 16-bit range are
unsupported by this epoch.

## L2: scoreInfo selection

`Aligner::preAlign` applies these operations in order:

1. retain a column only when `score > threshold` (strict, not `>=`);
2. preserve increasing reference position;
3. form runs while each consecutive retained position differs by 1-4 bases;
4. choose the largest score in each run;
5. on equal maxima, choose the first occurrence, hence the lowest reference
   position;
6. emit scoreInfo records in run order.

No name, digest, query-specific list, or downstream result participates in
this selection.

## Supported authority boundary

The Phase 2 contract is the current Fasim default CPU path with nonempty DNA
inputs, query lengths within the SSW-CUDA program scope, and scores representable
by the byte/word scheme above. AVX2 functions are instrumented for diagnostics,
but Phase 2 fixtures and promotion authority remain the frozen SSE2 binary.
