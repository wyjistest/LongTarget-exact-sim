# Fasim Current-Base Aligner Internal Decomposition

This note documents the telemetry added to decompose current-base
`aligner.Align()` work. It is instrumentation only: scoring, thresholds, output
records, non-overlap behavior, sharded scheduling, GPU policy, and merge
semantics are unchanged.

## Scope

The current clean-base Fasim GPU path remains:

```text
FASIM_ENABLE_PREALIGN_CUDA=1
  -> preAlign CUDA topK peak generation
  -> CPU peak suppression
  -> CPU fastSIM extension
  -> CPU aligner.Align()
  -> output
```

#147 showed that real-workload CPU extension is dominated by `aligner.Align()`
at roughly 98.3-98.9% of measured extension time. This PR splits that alignment
bucket into current source boundaries so the next GPU decision is based on
measured work, not on coarse `nvidia-smi` averages.

This PR does not add Accelign, GPU score shadowing, GPU traceback, GPU CIGAR,
single-process multi-GPU, chunking, overlap, or any output-changing path.

## Fields

Each Fasim process now emits these additional `benchmark.fasim_*` fields:

| field | meaning |
|---|---|
| `benchmark.fasim_align_query_translate_seconds` | Wall seconds translating query bases in `Aligner::Align()`. |
| `benchmark.fasim_align_ref_translate_seconds` | Wall seconds translating per-call reference windows in `Aligner::Align(query, ref, ...)`. |
| `benchmark.fasim_align_profile_seconds` | Wall seconds building the SSW query profile with `ssw_init()`. |
| `benchmark.fasim_align_ssw_total_seconds` | Wall seconds spent inside `ssw_align()` from the C++ wrapper. |
| `benchmark.fasim_align_forward_score_end_seconds` | Wall seconds in the forward SSW byte/word score/end pass. This is the closest current proxy for score/end DP work. |
| `benchmark.fasim_align_reverse_start_seconds` | Wall seconds for reverse-start recovery, including reverse query/profile setup, reverse SSW pass, and reverse cleanup. |
| `benchmark.fasim_align_traceback_seconds` | Wall seconds in `banded_sw()` traceback/CIGAR generation. |
| `benchmark.fasim_align_convert_seconds` | Wall seconds converting `s_align` into the C++ `Alignment` object, including mismatch calculation for the reference-sequence overload. |
| `benchmark.fasim_align_cleanup_seconds` | Wall seconds freeing wrapper-owned translated buffers, SSW alignment results, and SSW profiles. |
| `benchmark.fasim_align_calls` | `Aligner::Align()` calls that passed initial validation. |
| `benchmark.fasim_align_byte_forward_calls` | Forward score/end passes that used the byte SSW path. |
| `benchmark.fasim_align_word_forward_calls` | Forward score/end passes that used the word SSW path, including byte-overflow fallback. |
| `benchmark.fasim_align_reverse_calls` | Reverse-start recovery passes. |
| `benchmark.fasim_align_traceback_calls` | `banded_sw()` traceback/CIGAR calls. |
| `benchmark.fasim_align_null_results` | `ssw_align()` calls that returned `NULL` to the wrapper. |

The fields are process-local sums. In sharded reports, the runner sums seconds
and counts across shards and workers, so seconds can exceed wall time when
workers and extension threads run concurrently.

## Measurement Boundaries

The new split follows actual current-source boundaries:

```text
Aligner::Align wrapper:
  query translation
  ref translation
  ssw_init profile setup
  ssw_align total
  ConvertAlignment / mismatch calculation
  cleanup

ssw_align:
  forward byte/word score-end pass
  reverse-start recovery
  banded_sw traceback/CIGAR
```

`fasim_align_forward_score_end_seconds` is not a full replacement for a
standalone score-only API. It includes the current forward SSW pass that finds
score and endpoint. That makes it the right first proxy for deciding whether a
future score-only GPU shadow is worth building.

`fasim_align_traceback_seconds` measures `banded_sw()` only. It does not include
the later Fasim record construction or output merge stages.

## Small Smoke Signal

The local smoke workload is intentionally tiny and should not be treated as a
large-workload performance conclusion. It shows the split is wired correctly:

```text
single process testDNA + H19:
  fasim_align_calls                       165
  fasim_align_query_translate_seconds     0.000349365
  fasim_align_ref_translate_seconds       0.000016966
  fasim_align_profile_seconds             0.006646386
  fasim_align_ssw_total_seconds           0.008645773
  fasim_align_forward_score_end_seconds   0.006476568
  fasim_align_reverse_start_seconds       0.001614263
  fasim_align_traceback_seconds           0.000494058
  fasim_align_convert_seconds             0.000094676
  fasim_align_cleanup_seconds             0.000050681
  fasim_align_byte_forward_calls          165
  fasim_align_word_forward_calls          0
  fasim_align_reverse_calls               165
  fasim_align_traceback_calls             165
  fasim_align_null_results                0

sharded smoke:
  fasim_align_calls                       239
  fasim_align_forward_score_end_seconds   0.010766392
  fasim_align_reverse_start_seconds       0.002814430
  fasim_align_traceback_seconds           0.000940090
  fasim_align_profile_seconds             0.011311143
```

On this small smoke, forward score/end and profile setup are larger than
traceback/CIGAR. That is a useful sanity check, not the final large-workload
decision.

## Decision Use

Use this telemetry as the gate before any score-only GPU work:

```text
If forward_score_end dominates:
  next PR can be a shadow-only score/end probe.
  CPU aligner output remains authoritative.

If reverse_start dominates:
  endpoint/start-end work is important.
  GPU shadow needs a separate tie-policy and false-reject gate.

If traceback dominates:
  do not GPUize full output first.
  Consider CPU traceback/CIGAR optimization while keeping CPU authority.

If translation or profile setup dominates:
  consider query/ref translation reuse or SSW profile reuse before GPU kernels.

If costs are distributed:
  stop chasing one kernel and continue broader sharding/workload validation.
```

Any future score-only GPU or Accelign-style experiment must remain diagnostic
first:

```text
CPU output remains authoritative
GPU score output cannot reject candidates
digest must remain unchanged
score mismatches and false rejects must be zero
buffer build, H2D, kernel, and D2H seconds must be reported separately
```

Do not use this telemetry to justify in-process multi-GPU, GPU CIGAR, GPU full
traceback, chunking/overlap, or historical final speed-stack claims.
