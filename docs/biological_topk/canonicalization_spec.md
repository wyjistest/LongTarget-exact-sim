# Canonicalization Specification

## Input identity preflight

Before output canonicalization or matching, A and G must agree on every field:

```text
query_ordinal_namespace, query_source_ordinal, query_sequence_sha256,
target_ordinal_namespace, target_source_ordinal, target_sequence_sha256,
assembly, target_coordinate_namespace, query_extraction_recipe_id,
target_extraction_recipe_id, parameter_bundle_sha256, input_pair_digest
```

The logic is AND. An ordinal is identified by `(namespace, ordinal)`, never by
the bare ordinal. The pair digest is SHA-256 over UTF-8 canonical JSON with
sorted keys, compact separators, and all query/target identities, extracted
intervals, coordinate metadata, recipes, and parameter digest. Any mismatch is
a technical failure; matching does not start and all primary metrics fail.

## Raw and normalized values

The canonicalizer retains all raw query, target, genome, Strand, Direction, and
chromosome fields. It adds 0-based half-open query, forward-target, and genome
intervals according to `coordinate_mapping.md`. The legacy query midpoint is
always computed directly from raw positive query coordinates.

`Score`, `MeanStability`, and `MeanIdentity(%)` are parsed from an ASCII decimal
grammar with `decimal.Decimal`. Exponents, leading plus, locale commas, NaN,
infinities, leading-zero integer forms, quantization, tolerance comparisons,
and binary-float contract comparisons are forbidden. `Nt(bp)` is a canonical
nonnegative integer.

The Phase 1 audit covers 766,261 supported rows and found every Score integral.
Therefore `score_representation=integral_exact`: `score_decimal_string` remains
normative and `score_integer` is a required exact derivative. A future
supported nonintegral path must use `decimal_exact`, retain the decimal string,
and set `score_integer` to null rather than truncate it.

## Sequence fields

For TFO and TTS fields, strip only field-external ASCII whitespace, uppercase
ASCII letters, remove ASCII `-` characters, validate the frozen alphabet, and
preserve orientation. Internal whitespace, punctuation, unknown gap symbols,
or unsupported bases fail closed. Raw-field and ungapped-sequence digests are
distinct provenance values.

## Candidate-site record

Each arm-local ranked record carries workload and arm, ranking and rank, all
namespaced input identities, pair digest, recomputed cluster geometry and member
count, representative query/target/genome intervals, target identity,
Direction, Strand, Rule, exact numeric fields, ungapped sequence digests,
technical validity, and a strict-row diagnostic digest.

Backend, numeric Class, CIGAR, gapped byte identity, full-row digest, row order,
and wall time are not candidate-site identity. If removal of implementation
fields leaves more than one indistinguishable within-arm candidate site, set
`within_arm_ambiguous_candidate_site=1` and fail that workload/ranking.
