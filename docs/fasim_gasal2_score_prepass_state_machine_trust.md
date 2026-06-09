# Fasim GASAL2 Score-Prepass State-Machine Trust

This is a default-off audited trust checkpoint. It tests whether the segmented
score-prepass state-machine consumer can replace the CPU realpath extend path
under an external digest gate.

It is not a production recommendation.

## Env

```text
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_TRUST=1
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_ALIGN_CACHE=1
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_GASAL2_TRACEBACK_SHADOW=1
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_SEGMENT_TRACEBACK_SHADOW=1
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_EXPANDED_SEGMENT_TRACEBACK_SHADOW=1
```

The trust path:

```text
1. runs the segmented GASAL2 score-prepass state-machine consumer
2. skips CPU realpath extend if every task is covered
3. writes state-machine triplexes to the candidate output
4. requires external baseline digest equality
5. falls back to CPU if coverage/fallback checks fail
```

It still does not use GPU endpoint, GPU CIGAR, or GPU traceback authority.
CPU `aligner.Align()` is still used for selected/fallback traceback.

`FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_ALIGN_CACHE=1` is a default-off
align cache probe for this trust path. It caches CPU traceback alignments inside
one state-machine flush by `(task, target start, cutlength)`, then reports cache
lookups / hits / misses / unique keys. It is diagnostic unless broad digest and
performance evidence show that reuse materially reduces CPU traceback work.

`FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_GASAL2_TRACEBACK_SHADOW=1` is a
default-off GASAL2 traceback shadow for the same state-machine attempts. It runs
GASAL2 traceback beside the CPU `aligner.Align()` authority and reports
`gasal2_traceback_shadow_alignment_mismatches` and
`gasal2_traceback_shadow_triplex_mismatches`. It does not feed GASAL2 endpoint,
CIGAR, traceback, candidate state, output, or digest.

For NEAT1, this shadow fails closed at the GASAL2 long-query guard:

```text
gasal2_traceback_shadow_attempts = 2,008
gasal2_traceback_shadow_selected = 0
gasal2_traceback_shadow_fallbacks = 1
gasal2_length_guard_last_query_len = 22,767
gasal2_length_guard_max_query_len = 2,812
```

Raising the guard for this full-query traceback probe is not safe: a diagnostic
run with `FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=30000` hit GASAL2 CUDA illegal memory
access at `src/gasal_align.cu:343`. Therefore full-query GASAL2 traceback cannot
replace the state-machine CPU `Align()` path.

`FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_SEGMENT_TRACEBACK_SHADOW=1` is a
default-off segmented-query traceback shadow. It reruns CPU `Align()` on the
selected query segment, offsets query coordinates back to the global query, and
compares both the alignment key and converted triplexes against the full-query
CPU `Align()` authority. It does not use segment traceback output for Fasim
output or digest.

The segment traceback shadow also reports a mismatch taxonomy:

```text
segment_traceback_shadow_cpu_query_outside_segment
segment_traceback_shadow_score_mismatches
segment_traceback_shadow_endpoint_mismatches
segment_traceback_shadow_cigar_mismatches
```

`FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_EXPANDED_SEGMENT_TRACEBACK_SHADOW=1`
is a default-off expanded-segment traceback oracle. It reruns CPU `Align()` on a
query window that covers the full legacy query interval, compares the result
against the full-query CPU `Align()` authority, and reports:

```text
expanded_segment_traceback_shadow_attempts
expanded_segment_traceback_shadow_alignment_mismatches
expanded_segment_traceback_shadow_triplex_mismatches
expanded_segment_traceback_shadow_cpu_query_outside_expanded_segment
expanded_segment_traceback_shadow_required_max_len
expanded_segment_traceback_shadow_required_over_gasal2_limit
```

It is diagnostic only and does not feed Fasim output or digest.

## Results

```text
NEAT1 first1:
  digest clean
  tasks = 48
  realpath_extend_align_attempts = 0
  state_machine_cpu_align_attempts = 2,008
  align_cache_lookups = 2,008
  align_cache_hits = 0
  align_cache_misses = 2,008
  gasal2_traceback_shadow_attempts = 2,008
  gasal2_traceback_shadow_fallbacks = 1
  segment_traceback_shadow_attempts = 2,008
  segment_traceback_shadow_alignment_mismatches = 1,288
  segment_traceback_shadow_triplex_mismatches = 1,288
  segment_traceback_shadow_missing_segment = 0
  segment_traceback_shadow_cpu_query_outside_segment = 1,288
  segment_traceback_shadow_score_mismatches = 1,263
  segment_traceback_shadow_endpoint_mismatches = 1,288
  segment_traceback_shadow_cigar_mismatches = 1,281
  expanded_segment_traceback_shadow_attempts = 2,008
  expanded_segment_traceback_shadow_alignment_mismatches = 0
  expanded_segment_traceback_shadow_triplex_mismatches = 0
  expanded_segment_traceback_shadow_required_max_len = 22,767
  expanded_segment_traceback_shadow_required_over_gasal2_limit = 1,288
  state_machine_triplex_mismatches = 0

NEAT1 first4:
  digest clean
  tasks = 192
  realpath_extend_align_attempts = 0
  state_machine_cpu_align_attempts = 8,480
  align_cache_lookups = 8,480
  align_cache_hits = 0
  align_cache_misses = 8,480
  gasal2_traceback_shadow_attempts = 8,480
  gasal2_traceback_shadow_fallbacks = 4
  segment_traceback_shadow_attempts = 8,480
  segment_traceback_shadow_alignment_mismatches = 5,337
  segment_traceback_shadow_triplex_mismatches = 5,337
  segment_traceback_shadow_missing_segment = 0
  segment_traceback_shadow_cpu_query_outside_segment = 5,337
  segment_traceback_shadow_score_mismatches = 5,253
  segment_traceback_shadow_endpoint_mismatches = 5,337
  segment_traceback_shadow_cigar_mismatches = 5,304
  expanded_segment_traceback_shadow_attempts = 8,480
  expanded_segment_traceback_shadow_alignment_mismatches = 0
  expanded_segment_traceback_shadow_triplex_mismatches = 0
  expanded_segment_traceback_shadow_required_max_len = 22,767
  expanded_segment_traceback_shadow_required_over_gasal2_limit = 5,336
  state_machine_triplex_mismatches = 0
  baseline_wall_seconds = 5.31076
  candidate_wall_seconds = 9.14084
  candidate_vs_baseline = 0.5810x

NEAT1 first16:
  digest clean
  tasks = 768
  realpath_extend_align_attempts = 0
  state_machine_cpu_align_attempts = 35,152
  align_cache_lookups = 35,152
  align_cache_hits = 0
  align_cache_misses = 35,152
  gasal2_traceback_shadow_attempts = 35,152
  gasal2_traceback_shadow_fallbacks = 16
  segment_traceback_shadow_attempts = 35,152
  segment_traceback_shadow_alignment_mismatches = 22,000
  segment_traceback_shadow_triplex_mismatches = 22,000
  segment_traceback_shadow_missing_segment = 0
  segment_traceback_shadow_cpu_query_outside_segment = 22,000
  segment_traceback_shadow_score_mismatches = 21,626
  segment_traceback_shadow_endpoint_mismatches = 22,000
  segment_traceback_shadow_cigar_mismatches = 21,823
  expanded_segment_traceback_shadow_attempts = 35,152
  expanded_segment_traceback_shadow_alignment_mismatches = 0
  expanded_segment_traceback_shadow_triplex_mismatches = 0
  expanded_segment_traceback_shadow_required_max_len = 22,767
  expanded_segment_traceback_shadow_required_over_gasal2_limit = 21,991
  state_machine_triplex_mismatches = 0
  baseline_wall_seconds = 21.493
  candidate_wall_seconds = 36.1157
  candidate_vs_baseline = 0.5951x
```

## Interpretation

Correctness is clean for the bounded NEAT1 rows, and the trust path proves the
state-machine output can replace CPU realpath output under an external digest
gate.

Performance is no-go for the current implementation. The trust path removes
`realpath_extend_align_attempts`, but the state-machine consumer performs the
same amount of CPU traceback work:

```text
NEAT1 first16:
  old realpath align attempts ~= 35,152
  trust state-machine CPU align attempts = 35,152
```

So this path does not reduce the dominant CPU traceback work. It adds segmented
GASAL2 score-prepass overhead on top, making the candidate slower than baseline.

The align cache probe quantifies whether repeated selected/fallback windows
exist. On the bounded NEAT1 rows above, cache hits are zero and unique keys equal
misses, so a local same-flush CPU alignment cache does not reduce the work. This
confirms the current state-machine trust path needs a different traceback
replacement rather than a local cache.

The GASAL2 traceback shadow is the next boundary check: if alignment or triplex
mismatches are non-zero, GASAL2 traceback cannot replace the CPU traceback in
this state-machine path without a separate equivalence fix. For the current
NEAT1 state-machine path the boundary is earlier: full-query GASAL2 traceback is
guarded out, and bypassing the guard crashes inside GASAL2.

The segmented-query CPU traceback shadow gives a second no-go boundary for the
direct replacement shape. On NEAT1 first1, selected segment traceback differs
from full-query CPU `Align()` on 1,288 of 2,008 attempts after global query
coordinate repair; on NEAT1 first4 the same shadow differs on 5,337 of 8,480
attempts, and on NEAT1 first16 it differs on 22,000 of 35,152 attempts. The
converted triplexes differ on the same attempts.
Therefore directly replacing full-query CPU traceback with traceback on the
selected query segment is not equivalent. Any future segmented GASAL2 traceback
work needs a separate tie/overlap/segment-provenance repair design before it can
be considered a real path.

The mismatch taxonomy shows the root shape: `missing_segment = 0`, while
`cpu_query_outside_segment` equals the alignment mismatch count on first1,
first4, and first16. This is not primarily a lost-provenance issue. The selected
query segment often does not contain the full-query CPU traceback interval, so
direct selected-segment traceback cannot reproduce legacy `Align()` even before
GASAL2-specific traceback differences are considered.

The expanded-segment oracle confirms this boundary. When the probe uses a query
window that covers the full legacy interval, alignment and triplex mismatches are
zero on first1, first4, and first16. But the required max query window is 22,767
bp, equal to the NEAT1 query length and far above the current GASAL2 guard of
2,812 bp. The required-over-limit counts are 1,288 / 5,336 / 21,991 for
first1 / first4 / first16. This means the equivalence repair is effectively a
full-query traceback requirement for many attempts, not a small overlap around
the selected segment.

## Decision

```text
Correctness/shape:
  go as audited trust scaffold

Performance:
  no-go for current implementation

Real path:
  no
```

Do not promote this env as a recommended runtime. Further work only makes sense
if the next design reduces selected/fallback CPU traceback attempts materially
or replaces traceback with a digest-clean faster implementation.

## Gate

```bash
make check-fasim-gasal2-score-prepass-state-machine-trust-runtime-smoke
```
