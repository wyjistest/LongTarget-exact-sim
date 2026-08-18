# Long-query consumer-driven F0 and witness audit v1

This epoch measures the physical floor of the exact long-query consumer path
and audits a conservative witness proxy. It does not change the default
all-reverse CUDA path and does not authorize a consumer-driven CUDA kernel.

## Fixture

```text
query                         LINC01501 / 4,006 nt
query sequence SHA-256        896e9e632f321c87539268390c3668baab3d40f1007cd2433b44321561ebc657
target                        promoter shard_0009 / 4,942,620 bp
target FASTA SHA-256          c448a0564c4fbfb2261071885a2f83f2631323d54a5e64b5d4ed4ce57262295f
trace SHA-256                 fcb5c9bcb8318026d7b2447016f458e7b478207242dbfad18342690747b8666f
endpoint cache SHA-256        1d9b81cb1f224de2ce298199544272842b0af791fec71b03ef3fa5305f538dce
binary SHA-256                961dacf9c3c39342308684b0bc86d22cf94ed3f0099edf9ccafe21a542d71bb8
complete TFOsorted SHA-256    2199bc6033f51eed498b6e692a4f7f6e95178dca631d26562828bc9181cc1075
selected signature SHA-256    c9ae3b400370db94e8caa57e74f2168b2ab0eca18e3414467fe7be9e546659df
```

The cache is a development-only `LQF0CACH-v1` fixed-width endpoint copy. It
contains 4,345,980 records and is never a product input. The runtime checks
task, group, round, scoreInfo-derived position, start, cutlength, threshold,
and query length for every record; mismatch fails closed. The measured wall
times include loading the cache into the replay process.

## F0 result

Three clean physical-floor repeats were completed with the final audit binary:

```text
wall seconds       140.04, 140.05, 140.46
median wall        140.05 s
task rows          48,432 on every run
endpoint records   4,345,980 on every run
selected CPU calls 1,086,495 on every run
GPU kernel         0.0 s
H2D / D2H          0.0 s / 0.0 s
continuation fail  0
CPU oracle         0
fallbacks/errors   0
```

Every run emitted the exact authority digest above. The measured F0 is below
the registered `149.801 s` engineering-margin threshold. Reusing the frozen
cell model with the measured F0 gives:

```text
F1 conservative projection = 207.23 s
nominal 1.5x budget         = 241.087 s
10% margin budget           = 216.978 s
projected speedup           = 1.745x
```

This is a planning projection, not a CUDA benchmark. It assumes the existing
forward and incremental reverse kernel rates and adds no compaction overhead.

## Round profile

The exact ordered replay has four attempts per group:

```text
scoreInfo groups             1,086,495
all attempts                 4,345,980
round 0 active groups        1,086,495
rounds 1-3 active groups       216,419 each
forward-cell fraction         38.8692%
reverse-cell fraction         25.0000%
combined DP-cell fraction     31.9346%
threshold / best / last       870,076 / 119,878 / 96,541
reverse requests by round    946,928 / 16,813 / 13,804 / 108,950
```

The ordered replay and selected signature are byte-for-byte identical to the
existing all-reverse audit. The committed compact profile is
[`round_profile.json`](round_profile.json); the detailed local profile, large
raw trace, and cache remain local evidence artifacts. The complete machine
readable epoch receipt is [`receipt.json`](receipt.json).

## Witness proxy

The independent proxy only tests a lower-bound condition for the first
attempt: observed canonical score reaches threshold, the endpoint is terminal
in the subview, and the numeric/span fields are valid. It does **not** prove
the path start, whole-target upper bound, or deterministic endpoint tie key.

```text
first-attempt threshold groups       870,076
lower-bound-only groups              648,765 (59.712%)
lower-bound weighted forward cells   14.8698%
strict certificate groups            0
strict weighted coverage             0%
first threshold groups non-terminal 221,311
```

Decision:

```text
F0 physical floor                  pass
F1 projection                     within 1.5x and margin budgets
witness certificate               not established
consumer-driven CUDA              not authorized
production_authorized             false
Bioinformatics v2 state           unchanged
```

The next useful work is a real path-start/upper-bound/tie witness engine or a
separate scoped contract. This epoch intentionally stops before writing a new
CUDA kernel.

The compact witness result is recorded in
[`witness_proxy.json`](witness_proxy.json). It is deliberately a lower-bound
proxy, not a certificate: strict coverage is zero and no consumer-driven CUDA
implementation is authorized.
