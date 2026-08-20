# Exact uint8 global-state min-score spike v1

## Decision

```text
per-task score exactness                    PASS
complete TFOsorted byte identity            PASS
F1 structural identity                     PASS
>= 1.5x min-score stage gate at >=8000 nt  PASS
full-concat shadow                          AUTHORIZED
production default                          OFF
production dynamic GPU queue                NOT STARTED
```

The retained candidate preserves the existing 32-lane legacy min-score
recurrence and query profile.  It stores global H/E/H state as `uint8_t` and
accepts a task only when no H value exceeds 255.  Any task whose saturation
certificate fires is discarded and replayed in full through the unchanged
word16 column-output plus reduction authority.

This is not the old 16-lane endpoint byte/Lazy-F contract, and it does not
reuse byte-profile scoreInfo column maxima.  Legacy min-score and byte-profile
scoreInfo remain separate numerical contracts.

Source and binary binding:

```text
source commit  741af2ab4d1c94cdc224a6a0f8d92a954d2281ab
binary SHA-256 6a91e8508673d29ece2e23778cc51561b45dde517b72fe2f57a00f2fd18299e2
rebuild equal  yes
```

## Runtime gate

The path is default-off and requires both the existing GPU min-score path and:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_MINSCORE_UINT8_GLOBAL=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_MINSCORE_UINT8_GLOBAL_MIN_QUERY_LENGTH=8000
```

The default length threshold is 8000 nt.  At 7999 nt, the flag is recorded as
requested but `active=0`, candidate batches and tasks are zero, and the
word16 authority runs unchanged.  At 8000 nt, `active=1` and all three bounded
batches use the candidate.  The runtime flag and the byte-overflow audit flag
are mutually exclusive and fail closed at process startup.

## Source-bound exactness and performance

All rows below used the same final binary and the 2 Mb chr22 target fixture.
The fresh-query arms ran concurrently on separate RTX 4090 devices while an
unrelated OpenMP production job remained active.  Therefore stage ratios are
development evidence; total process wall is diagnostic only.

| Query | Gate | Word16 min-score | uint8 + replay | Stage speedup | Replay tasks | Complete output |
| ---: | :---: | ---: | ---: | ---: | ---: | :---: |
| 7,999 nt | off | 4.40563 s | authority path | 1.000x | 0 / 10,368 | byte-identical |
| 8,000 nt | on | 4.37106 s | 1.97082 s | 2.218x | 8 / 10,368 | byte-identical |
| 10,451 nt | on | 6.38103 s | 3.18115 s | 2.006x | 331 / 10,368 | byte-identical |
| 11,498 nt | on | 7.09396 s | 4.19916 s | 1.689x | 705 / 10,368 | byte-identical |

The two independent fresh queries retain complete output digests:

```text
10,451 nt  e541bad07ad4fa928396928b9cc3b1c208773f4aba139396f5ff375f64de9d7c
11,498 nt  41aad1f83a6f5ea2a020525f46adddc92bd58e66c25bed8214dc0cb9ee7ba632
```

For each off/on pair, all 10,368 F1 rows have `ok=1`, continuation failures
and row errors are zero, and a canonical digest over every non-timing F1 field
is equal.  The 7999 and 8000 boundary fixture outputs both have SHA-256
`238ce9019d325d40d24c7f153b7943df2e8ace12b4ea5a1ae7074fe61bf24492`;
each on arm was also compared byte-for-byte with its own off arm.

## Supporting development panel

Before the final source checkpoint, the same recurrence was exercised on
4,006, 8,181, and 12,397 nt real-query batches.  The 4,006 nt batch reached
only 1.263x, which is why it is excluded by the conservative 8000 nt gate.
The 8,181 nt batch reached 2.334x.  Three paired 12,397 nt batch samples were
1.5227x, 1.5209x, and 1.5198x.  All task scores and complete outputs matched.

These exploratory values support the gate but are not used as source-bound
promotion evidence.  The authoritative values are in `audit.json`.

## Regression coverage

```text
uint8 API exactness: 1, 31, 32, 33, 511, 2812, 4006, 8181, 12397 nt
forced overflow and word16 replay: PASS
word16 scalar direct-output regression: PASS
CPU-only stub build: PASS
dynamic GPU pool tests: 24 / 24 PASS
known F1 legacy replay fixtures: 2 / 2 PASS
runtime/audit mutual exclusion: exit 1, expected diagnostic
git diff --check: PASS
```

## Scope limit

This checkpoint proves an exact min-score stage improvement on a 2 Mb target.
It does not yet prove the ratio on the 164.9 Mb full-concat workload and does
not change the default runtime.  The next gate is one representative
full-concat off/on shadow with the same source and binary, exact complete
output, zero fallback, and at least 1.5x min-score stage speedup.  Only after
that gate may the flag be frozen into a new dynamic-pool execution plan.
