# GASAL2 long-query traceback certificate

## Decision

Phase 6 is an evidence-complete `no_go`.

```text
rank-independent exact certificate:
  correctness-clean in shadow
  request reduction is not material

rank-aware global top5 certificate:
  score bound alone is insufficient
  stability and Nt admissible upper bounds are unavailable
  conservative union skips zero requests

real traceback skip:
  disabled

production defaults:
  unchanged
```

The default-off shadow and timing analyzer remain useful diagnostics. This
phase does not enable a runtime reduction and does not restart fixed score
threshold pruning.

## Timing entry profile

The timing receipt aggregates the 121 process logs from the existing full
segmented KCNQ1OT1 x chr22, two-grid artifact:

```text
source=.tmp/characterize_fasim_gasal2_segmented_query_kcnq1ot1_chr22_full_fullquery
runs=121
grid_shifts=0,256
end_to_end_seconds=8687.413318
traceback_requests=918240875
fallbacks=0
length_guard_fallbacks=0
```

The tracked receipt is
`docs/fasim_gasal2_traceback_long_query_timing.tsv`.

| Timing component | Seconds | Percent of wall | Scope |
|---|---:|---:|---|
| score prepass | 495.873617 | 5.71% | score fill + submit + wait |
| traceback pack + submit + host wait | 686.746206 | 7.91% | host-observed GASAL2 traceback |
| CPU convert | 4286.883300 | 49.35% | inclusive conversion wall |
| host-observed traceback stage | 4973.629506 | 57.25% | pack + submit + wait + convert |
| per-run filter + sort | 144.606516 | 1.66% | nested inside convert |

The following values are nested and are not added again:

```text
traceback_host_wait_seconds=651.482220
  traceback_host_poll_wait_seconds=474.241690
  traceback_result_copy_seconds=177.240549
    traceback_cigar_materialize_seconds=145.245684

traceback_convert_seconds=4286.883300
  filter_plus_sort_seconds=144.606516
```

GASAL2 does not expose independent asynchronous traceback H2D, kernel and D2H
timing through the current bridge. They are recorded as `unavailable`, not
zero. No CUDA synchronization was added for timing.

```text
traceback_h2d_seconds=unavailable
traceback_kernel_seconds=unavailable
traceback_d2h_seconds=unavailable
device_timing_supported=0
```

The segmented offline merge does not expose cluster wall timing in these old
121 logs. `traceback_filter_dedup_cluster_seconds` therefore has the explicit
scope `per_run_filter_sort_only`; it is not presented as full global clustering
time.

## Exact pre-drop shadow

The new default-off mode is:

```bash
FASIM_GASAL2_TRACEBACK_CERTIFICATE_SHADOW=1
```

It runs after the authority score prepass has selected traceback candidates.
For characterization only, it performs an additional score/end probe over
those selected candidates and classifies three mutually exclusive exact
reasons:

```text
exact_descriptor_duplicate
static_span
score_endpoint_span
```

`exact_descriptor_duplicate` is deliberately narrow: only a repeated identical
selected attempt index is eligible. It does not infer that different scoreInfo
groups or different segment descriptors are interchangeable.

`static_span` proves that the full query length plus full target-view length is
below `cLength`. `score_endpoint_span` proves:

```text
(score_query_end + 1) +
(score_ref_end - target_start + 1) < cLength
```

The score/end values exist before traceback. Actual local traceback begins can
only shorten these spans. The shadow still runs every authority traceback and
checks each certified candidate against the resulting endpoints. It never
uses final output membership as the proof and never drops runtime work.

Counters use:

```text
benchmark.fasim_gasal2_traceback_certificate_shadow_*
proof_version=phase6_exact_v1
real_skip_enabled=0
```

The probe is intentionally extra work. Its measured time is shadow overhead,
not a production performance result. A future implementation could carry
selected score results forward instead of probing twice, but the request-count
ceiling below makes that refactor unjustified.

## Shadow matrix

The tracked matrix is
`docs/fasim_gasal2_traceback_certificate_long_query.tsv`.

| Workload | Authority traceback | Certified | Fraction | False rejects | Output gate |
|---|---:|---:|---:|---:|---|
| H19 x chr22 2 Mb | 175,193 | 22 | 0.0126% | 0 | byte-equal |
| KCNQ1OT1 2048 bp x chr22 2 Mb | 188,726 | 25 | 0.0132% | 0 | byte-equal |
| H19 x chr21+chr22 full | 13,838,010 | 1,261 | 0.0091% | 0 | three top5 + clustered top5 clean |
| KCNQ1OT1 max4 x chr22 full | 62,807,605 | 16,875 | 0.0269% | 0 | shifted-grid clustered top5 5/5 |
| KCNQ1OT1 max8 x chr22 full | 128,054,052 | 64,990 | 0.0508% | 0 | shifted-grid clustered top5 5/5 |

Across every current row:

```text
exact_descriptor_duplicate_skips=0
static_span_skips=0
all certified candidates are score_endpoint_span
shadow_false_rejects=0
certificate_fallbacks=0
authority_fallbacks=0
length_guard_fallbacks=0
real_skip_enabled=0
```

The rows are not summed into an independent global percentage because max4 is
a bounded subset of the max8 coverage and the controls have different query and
target scopes.

### Correctness boundaries

The two 2-Mb controls are byte-identical between baseline and shadow.

The chr21+chr22 control has the known large-workload row variability:

```text
baseline_unique_rows=665763
shadow_unique_rows=665759
missing_rows=4
extra_rows=0
score top5 equal=true
stability top5 equal=true
Nt-score top5 equal=true
offline clustered top5 equal=true
```

Because no shadow request is actually dropped, this 4-row difference is
reported under the existing baseline variability contract. It is not claimed
as full row-set equality.

The KCNQ1OT1 max4 and max8 rows compare shifted grids. They support bounded
grid stability, not unsegmented full-length equivalence and not full row-set
equivalence.

## Rejected certificate families

### Generic descriptor dedup

The earlier pruning-eligibility taxonomy showed that most apparent duplicate
or removed rows depend on CIGAR, representative selection or final sort. The
current exact descriptor definition finds zero safe duplicates in all five
rows. Phase 2 ownership is `no_go` and is not reused to drop traceback work.

### Broader cutlength span predicate

A prior physical shadow showed that `cutlength < cLength` is not safe:

```text
certified candidates=51701
false rejects=11
missing rows=11
```

The current implementation uses only the stricter score-end upper bound and
revalidates it against authority traceback endpoints.

### Rank-aware global top5

Prior tie-complete telemetry (`a487168`) established:

```text
score_certificate_supported=true
stability_certificate_supported=false
nt_score_certificate_supported=false
tracebacks_skipped=0
false_prune=0
all three top5 equal=true
```

The physical candidate set must be the union required by score, stability and
Nt ranking, with all boundary ties retained. Missing stability/Nt upper bounds
therefore force the conservative full set. A score-only frontier is not a safe
substitute, so rank-aware counters remain zero in the current matrix.

## Gate evaluation

| Phase 6 gate | Result |
|---|---|
| pre-drop proof | pass for `phase6_exact_v1` shadow candidates |
| shadow false rejects | pass: 0 |
| fallback accounting | pass: 0 |
| small full output | pass: byte-equal |
| chromosome three top5 | pass |
| KCNQ1OT1 max4/max8 shifted-grid clustered top5 | pass |
| traceback request reduction >=20% | fail: maximum 0.0508% |
| traceback stage wall reduction >=15% | not run; request gate failed |
| end-to-end reduction >=8% | not run; request gate failed |

The best observed request fraction is approximately 394 times smaller than the
20% promotion threshold. Implementing a real skip path cannot satisfy the
Phase 6 gate, even before proof overhead and pipeline effects. Phase 6 therefore
stops as `no_go_below_request_reduction_gate`.

## Artifact provenance

```text
entry artifact summary SHA-256:
  a6b72c3f2fff1e691e9c6cb12823705b4c2818a9d46096412e37be61540665f3

timing summary SHA-256:
  d67e5127eeb77a7d0d1fe6b0e5b5e82310b1e2ac49bcd9ba31674be7f54fff8a

generated matrix SHA-256 before path normalization:
  5884620db9be093fc9611c77e99aaf361aee0ae23072a5f3e0c2f14715daad6c

KCNQ1OT1 query SHA-256:
  f8883e1855017b7a28576770a8c8476a8eb1adbfcbef08d55c6dc74c49a86cc4

chr22 target SHA-256:
  ce3ee1ca39356238f7aee438a40a88b4f1b9d80b316b263e16fb12402212d10f

H19 query SHA-256:
  7d94fb9515b0fa63dbe8fb62e01bb50616760ce80eeef29ec9c3893af8040f4e
```

## Validation

```bash
python3 tests/check_analyze_fasim_gasal2_traceback_long_query.py
python3 tests/check_summarize_fasim_gasal2_traceback_certificate.py
bash scripts/check_fasim_gasal2_traceback_certificate_unit.sh
bash scripts/check_fasim_gasal2_traceback_certificate_shadow_smoke.sh
bash scripts/characterize_fasim_gasal2_traceback_certificate_phase6.sh
make check-fasim-gasal2-traceback-certificate-phase6
```

Phase 7 may integrate the Phase 5 exact-scoreInfo candidate. It must leave the
Phase 6 real traceback skip disabled.
