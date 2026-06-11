# Fasim GASAL2 ScoreInfo Scoped Milestone

This is a scoped milestone, not completion of the full objective. It records
what is now proven for the scoreInfo/preAlign GPU/GASAL2 line and what remains
outside the current evidence.

```text
Milestone name: GASAL2 / GPU scoreInfo scoped feasibility checkpoint
```

## Decision

```text
Short-query/H19 top5 path: scoped go
MEG3 grouped top5 wrapper: scoped go
MALAT1 streaming scoreInfo trust path: scoped go for MALAT1-like workload shape
NEAT1 streaming scoreInfo trust path: performance no-go for current global-state kernel
Selected-attempt CPU-align reduction: no-go for current selector

Broad scoreInfo/preAlign replacement: not proven
Full aligner.Align replacement: not proven
GPU endpoint/CIGAR/traceback authority: not proven
```

Do not mark the active full objective complete from this milestone.

## Short-Query/H19 Evidence

The formal top5 artifact path remains:

```text
--gasal2-top5-column-pruned-scoreinfo
```

chr21+chr22 formal result:

```text
decision = top5_artifact_go
active_path_runs = 1/1
top5_clean_runs = 1/1
exact scoreInfo GPU batches = 49
exact scoreInfo GPU tasks = 778,848
GASAL2 requests = 43,637,966
GASAL2 traceback requests = 13,701,121
fallback/overflow = 0 / 0
CPU worker wall sum = 4565.987188s
formal worker wall sum = 113.810705s
speedup = 40.119136x
```

This is a real GPU/GASAL2 scoreInfo/preAlign path for the scoped top5 artifact
contract. It is not a full lite-output or full TFO equivalence claim.

## MEG3 Grouped Evidence

The complete-record grouped runner/wrapper path is also scoped-go for the same
top5 artifact contract:

```text
--group-target-records 32
group_target_records = 32
grouped_shard_count = 17
decision = top5_artifact_go
active_path_runs = 1/1
top5_clean_runs = 1/1
fallback/overflow = 0 / 0
```

This remains complete-record grouping. It is not chunking and does not change
Fasim C++ output semantics.

## MALAT1 Trust Evidence

The strongest long-query positive is the streaming scoreInfo trust path. It
feeds GPU scoreInfo/minScore into CPU `fastSIM_extend_from_scoreinfo()` and
does not use GPU endpoint, CIGAR, traceback, or GASAL2 long-query traceback.

Full MALAT1 trust result:

```text
record_limit = 670
tasks = 200,400
realpath_used = 200,400
realpath_fallbacks = 0
realpath_digest_authority = external_digest_gate
cpu_scoreinfo_groups = 0
gpu_scoreinfo_groups = 3,561,123
cpu_prealign_seconds = 0
gpu_total_seconds = 486.763
digest = 88bb4e98f43c9a48affa082a7e97e881796f161aa4beda02a25dd6a8f7a1891f
baseline Running time = 2631.57s
candidate Running time = 2532.48s
candidate/baseline speedup = 1.039128x
```

This is a scoped positive: correctness is clean for the full MALAT1 checked
workload and CPU `preAlign` is removed from the candidate hot path. The
whole-run speedup is modest, so it does not justify broad promotion by itself.

## Full Lite-Output / TFOsorted Boundary

The external digest gates above are runner-scoped authority gates for the
checked artifacts. The report-mode comparator can now check either supported
Fasim `merged_output` schema:

```text
schema=lite:
  14-column FASIM_OUTPUT_MODE=lite rows

schema=tfosorted:
  19-column full TFOsorted rows including Class/MidPoint/Center/TFO/TTS sequence
```

Existing MALAT1 report pairs are full lite-output clean under the 14-column
`schema=lite` contract:

```bash
python3 scripts/compare_fasim_lite_full_equivalence.py \
  --baseline-report .tmp/characterize_two_contract_hot_smoke/malat1_first8/baseline/report.json \
  --candidate-report .tmp/characterize_two_contract_hot_smoke/malat1_first8/candidate/report.json
```

```text
schema=lite
baseline_rows=796
candidate_rows=796
missing_rows=0
extra_rows=0
full_rows_equal=true
```

The same full lite-output row-set equality holds for the checked MALAT1
first64, full group32 two-contract, full group32 trust, and current audited
first256 report pairs:

```text
MALAT1 first64:
  schema=lite
  baseline_rows=9741
  candidate_rows=9741
  full_rows_equal=true

MALAT1 full group32 two-contract:
  schema=lite
  baseline_rows=98713
  candidate_rows=98713
  full_rows_equal=true

MALAT1 full group32 trust:
  schema=lite
  baseline_rows=98713
  candidate_rows=98713
  full_rows_equal=true

MALAT1 current audited first256:
  schema=lite
  baseline_rows=42504
  candidate_rows=42504
  full_rows_equal=true
```

This materially strengthens the scoped MALAT1 evidence: the checked candidate
does not merely match a digest summary; it matches the complete de-duplicated
14-column lite row set.

There is now one small 19-column TFOsorted equivalence probe for the same
MALAT1-like group32 two-contract runner path:

```bash
make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence
```

```text
MALAT1 first8/group32 two-contract TFOsorted:
  output_mode = tfosorted
  runner merged digest = c245a4c1e34b9c640bdd5e8e44a896f470ec9d8e83799f7de977e0716955dad5
  schema = tfosorted
  baseline_rows = 796
  candidate_rows = 796
  baseline_unique_rows = 796
  candidate_unique_rows = 796
  missing_rows = 0
  extra_rows = 0
  full_rows_equal = true
```

This proves a focused first8 19-column row-set equivalence point, including
Class/MidPoint/Center/TFO/TTS sequence fields. It still does not prove full
MALAT1 19-column TFOsorted/TFO-sequence equivalence or a broad long-query
replacement. Future full TFOsorted claims must compare `schema=tfosorted`
outputs over the intended workload scope and must show:

The same gate can run a heavier optional first64 check:

```bash
CHECK_FIRST64=1 make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence
make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full
```

That optional run has also been exercised:

```text
MALAT1 first64/group32 two-contract TFOsorted:
  output_mode = tfosorted
  runner merged digest = 2789f4bea9cef5914dfdaa9555e5f22b827b122aee0a1220b402c107dc806ba5
  schema = tfosorted
  baseline_rows = 9741
  candidate_rows = 9741
  baseline_unique_rows = 9741
  candidate_unique_rows = 9741
  missing_rows = 0
  extra_rows = 0
  full_rows_equal = true
  tasks = 18,096
  two_contract_used = 18,096
  realpath_used = 18,096
  two_contract_fallbacks = 0
  two_contract_score_mismatches = 0
  two_contract_min_score_mismatches = 0
  two_contract_scoreinfo_mismatches = 0
  realpath_fallbacks = 0
  gpu_scoreinfo_groups = 319,280
  baseline runner wall = 237.215788s
  candidate runner wall = 246.114701s
  candidate_vs_baseline = 0.963842x
```

This strengthens correctness evidence, not performance evidence: candidate wall
time remains slower than CPU baseline for the first64 `tfosorted` probe.
The first64 audit wall time must not be used as a real runtime claim because
the audited wrapper enables diagnostic replay/attempt probes:

```bash
make check-fasim-gasal2-malat1-tfosorted-runtime-breakdown
```

```text
MALAT1 first64/group32 two-contract TFOsorted runtime breakdown:
  baseline_wall = 237.215788s
  candidate_wall = 246.114701s
  wall_delta = 8.898913s
  candidate_vs_baseline = 0.963842x
  two_contract_total_seconds = 45.198600s
  gpu_minscore_wall_seconds = 14.655500s
  realpath_extend_seconds = 104.648700s
  diagnostic_probe_seconds = 22.010077s
  attempt_probe_seconds = 15.994410s
  replay_probe_seconds = 3.486750s
  grouped_replay_probe_seconds = 0.946524s
  selected_only_probe_seconds = 1.582393s
  decision = audited_wall_not_real_runtime_claim
```

The diagnostic probe time exceeds the wall-time regression, while merge and
canonicalization are essentially equal between baseline and candidate. This
keeps the first64 `tfosorted` result in the correctness-evidence bucket.

```text
schema=tfosorted
full_rows_equal=true
missing_rows=0
extra_rows=0
```

The full-MALAT1 TFOsorted gate is intentionally heavier and is tracked
separately:

```text
MALAT1 full/group32 two-contract TFOsorted:
  schema = tfosorted
  baseline_rows = 98,713
  candidate_rows = 98,713
  baseline_unique_rows = 98,713
  candidate_unique_rows = 98,713
  baseline_full_digest = ff415800b5cbc226f979eb85c7a93387b6e07f1e17dc279342a594dd6b76bdca
  candidate_full_digest = ff415800b5cbc226f979eb85c7a93387b6e07f1e17dc279342a594dd6b76bdca
  missing_rows = 0
  extra_rows = 0
  full_rows_equal = true
  tasks = 200,400
  two_contract_used = 200,400
  realpath_used = 200,400
  candidate_vs_baseline = 0.403059x
  decision = full-output correctness proof, not runtime claim
```

## No-Probe Two-Contract Runtime Gate

The audited wrappers above intentionally enable replay/attempt diagnostics, so
their wall time is not the clean runtime claim. The focused no-probe runtime
gate runs the same MALAT1-like grouped two-contract bridge through the
dedicated default-off runner option:

```bash
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted
```

The candidate runner option is:

```text
--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32
result_contract = long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32_experimental_v1
long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_two_contract_runtime_group32_experimental_v1
```

It sets `--group-target-records 32` and limits candidate env to:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1
FASIM_ALIGN_GASAL2=1
```

It explicitly rejects probe env leakage and any positive numeric probe
telemetry.

Fresh first8 result:

```text
schema = lite
rows = 796
digest = 093a0d693301322e027ba6f3bd760bcbde60759131f156224f3924b7478581df
baseline_wall_seconds = 23.093321
candidate_wall_seconds = 23.310225
candidate_vs_baseline = 0.990695x
tasks = 1,824
two_contract_used = 1,824
realpath_used = 1,824
gpu_minscore_used = 1,824
gpu_scoreinfo_groups = 31,272
probe_positive_numeric_keys = 0
```

Fresh first8 TFOsorted no-probe result:

```text
schema = tfosorted
rows = 796
digest = c245a4c1e34b9c640bdd5e8e44a896f470ec9d8e83799f7de977e0716955dad5
baseline_wall_seconds = 23.330881
candidate_wall_seconds = 23.549913
candidate_vs_baseline = 0.990699x
tasks = 1,824
two_contract_used = 1,824
realpath_used = 1,824
gpu_minscore_used = 1,824
gpu_scoreinfo_groups = 31,272
probe_positive_numeric_keys = 0
```

The focused scoped release smoke for this long-query scoreInfo milestone is:

```bash
make check-fasim-gasal2-scoreinfo-scoped-release-smoke
```

It reruns the first8 no-probe lite and first8 no-probe TFOsorted gates, then
rechecks the scoped-milestone, completion-gap, and full-goal-decision static
boundaries. This is a scoped MALAT1-like contract/runtime smoke. It is not a
universal replacement smoke and not a performance claim.

The scoped MALAT1-like product-readiness and recommended-runtime gates are:

```bash
make check-fasim-gasal2-malat1-two-contract-product-readiness
make check-fasim-gasal2-malat1-two-contract-recommended-runtime
```

They define the checked default-off scope for
`--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32` and keep
NEAT1, GPU endpoint/CIGAR/traceback authority, direct `aligner.Align()`
replacement, and default production behavior outside the contract.
The full objective remains open.

Fresh optional first64 result:

```text
schema = lite
rows = 9,741
digest = f57a418be0ec9439cf2c4c453e2e45cc9d35b03df5e2c63f60860e6575db180d
candidate_vs_baseline = 1.029812x
tasks = 18,096
two_contract_used = 18,096
realpath_used = 18,096
gpu_minscore_used = 18,096
gpu_scoreinfo_groups = 319,280
probe_positive_numeric_keys = 0
```

Fresh optional first128 result:

```text
schema = lite
rows = 22,531
digest = 91ea0b8191027916e3237fb5381c6271fc9acd03b46a5cf67826c253fe41edd1
tasks = 40,128
two_contract_used = 40,128
realpath_used = 40,128
gpu_minscore_used = 40,128
gpu_scoreinfo_groups = 715,473
candidate_vs_baseline = 1.041215x
probe_positive_numeric_keys = 0
```

Fresh optional first256 result:

```text
schema = lite
rows = 42,504
digest = 7f553b74ae31bed4cb7b9c312a188e2df19627ac4882c7ad7ac484d65b004a4e
candidate_vs_baseline = 1.040931x
tasks = 80,640
two_contract_used = 80,640
realpath_used = 80,640
gpu_minscore_used = 80,640
gpu_scoreinfo_groups = 1,434,844
probe_positive_numeric_keys = 0
```

Fresh full-MALAT1 no-probe result:

```text
schema = lite
rows = 98,713
digest = f080498ad8b9661100243e8eec89b6b54b566d7ed96fa5db7e268a8ce8513e0b
baseline_wall_seconds = 2611.940621
candidate_wall_seconds = 2514.945686
candidate_vs_baseline = 1.038567x
tasks = 200,400
two_contract_used = 200,400
realpath_used = 200,400
gpu_minscore_used = 200,400
gpu_scoreinfo_groups = 3,561,123
probe_positive_numeric_keys = 0
```

Fresh full-MALAT1 TFOsorted no-probe result:

```text
schema = tfosorted
rows = 98,713
digest = ac667f460cd1446bc5598fa163f7fc2755265bf56e6b82c105e672873c895ffc
baseline_wall_seconds = 2636.136998
candidate_wall_seconds = 2537.678266
candidate_vs_baseline = 1.038799x
tasks = 200,400
two_contract_used = 200,400
realpath_used = 200,400
gpu_minscore_used = 200,400
gpu_scoreinfo_groups = 3,561,123
two_contract_total_seconds = 481.568400
gpu_minscore_wall_seconds = 157.575680
realpath_extend_seconds = 1165.840400
realpath_extend_align_seconds = 1139.782900
probe_positive_numeric_keys = 0
```

This turns the no-probe evidence into a repeatable repository gate and a
first-class runner option.
It is still a scoped MALAT1-like result: first64 is only a slight speedup,
first8 is slightly slower, first128/first256 are clean, and the full gate is
explicitly checked as a MALAT1-like workload milestone. The path remains
default-off and externally digest-gated. It still does not grant GPU endpoint,
CIGAR, traceback, or broad `aligner.Align()` authority.

## Full-MALAT1 Milestone Decision

```text
scoped full-MALAT1 no-probe runtime go:
  yes

not broad scoreInfo/preAlign replacement:
  yes

remaining bottleneck is CPU realpath extend/align:
  realpath_extend_seconds = 1165.840400
  realpath_extend_align_seconds = 1139.782900
  realpath_extend_align_attempts = 8,526,477

GPU scoreInfo path:
  two_contract_total_seconds = 481.568400
  two_contract_kernel_seconds = 480.874600
  gpu_minscore_wall_seconds = 157.575680

decision:
  MALAT1-like grouped two-contract scoreInfo runtime is a scoped milestone.
  It is not enough to close the broad scoreInfo/preAlign objective.
  two_contract kernel remains substantial, but it is not the only wall-time limiter.
```

The next broad-goal work should therefore target either broader workload
coverage with the same no-probe contract or the remaining CPU realpath
extend/align consumption. It should not promote endpoint, CIGAR, traceback, or
`aligner.Align()` authority from this result.

## NEAT1 Boundary

The NEAT1 non-shared legacy-byte trust path is correctness-clean through a
first128 audited replay, but performance no-go for the current global-state
kernel:

```text
record_limit = 64
tasks = 3,072
realpath_used = 3,072
realpath_fallbacks = 0
cpu_scoreinfo_groups = 0
gpu_scoreinfo_groups = 52,994
cpu_prealign_seconds = 0
gpu_total_seconds = 50.0708
digest = 5070d390bdffe9d47c4790193a798bba256d6ec81fc8cef3682a7036f403b01f
baseline Running time = 87.1285s
candidate Running time = 123.041s
candidate/baseline speedup = 0.708143x

NEAT1 non-shared audited replay first64:
  replay tasks = 3,072
  replay align attempts = 140,087
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0

NEAT1 non-shared audited replay first128:
  digest = 6b0f50f11373ce2dcd8b86045847236d7a094bb43bfa95a0b68a3f66840f9c6e
  replay tasks = 6,144
  gpu_scoreinfo_groups = 105,845
  replay align attempts = 281,588
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0
  candidate/baseline speedup = 0.300675x
```

This prevents generalizing the MALAT1 trust result into a broad long-query
runtime path. The runner trust preset's shared-memory legacy-byte shape is also
not a NEAT1 replacement path: on NEAT1 first4 it launches GPU minScore cleanly
but the shared scoreInfo kernel fails with
`legacy_byte_shared_smem_exceeds_optin_limit`, so
`gpu_scoreinfo_groups=0`, `realpath_used=0`, and `realpath_fallbacks=4`.
NEAT1 needs either the non-shared path gated as a workload-specific diagnostic
or a different execution shape, not more scaling of the shared global-state
kernel.

## Gates

The Full Goal Decision Audit remains the authority for whether the original
objective can be closed.

The default-off runner control surface for the MALAT1 scoped trust path is:

```text
--long-query-streaming-scoreinfo-gpu-trust
result_contract = long_query_streaming_scoreinfo_gpu_trust_experimental_v1
default-off
experimental
external digest gate
```

This runner option only packages the checked long-query streaming scoreInfo
trust env stack. It does not make the path a broad replacement and does not
grant GPU endpoint, CIGAR, traceback, or output authority.

Runner-level MALAT1 trust characterization now covers first8/first16/first32/
first64 through the public runner option:

```text
record_limit  tasks  realpath_used  fallback  GPU groups  CPU preAlign  runner speedup
8             1824   1824           0         31272       0s            0.914539x
16            4416   4416           0         77852       0s            0.957250x
32            8160   8160           0         144841      0s            0.934600x
64            18096  18096          0         319280      0s            0.953067x
```

All rows preserve the merged digest against the baseline runner and use
`result_contract = long_query_streaming_scoreinfo_gpu_trust_experimental_v1`.
This strengthens the runner control surface evidence, but the runner-level
wall time remains slower than baseline on these bounded samples.

The first64 worker sweep keeps the same correctness contract but does not turn
the trust path into a runner-level performance win:

```text
workers  tasks  realpath_used  fallback  GPU groups  GPU total  runner speedup
1        18096  18096          0         319280      44.999s    0.956003x
2        18096  18096          0         319280      62.025s    0.912482x
4        18096  18096          0         319280      79.532s    0.843978x
```

This argues against fixing the bounded runner performance gap by simply adding
workers for the current trust path. The next performance-relevant direction is
to reduce per-shard GPU setup/launch or batch scoreInfo work across shards.

Complete-record grouping is a small positive signal for that direction on
MALAT1 first64:

```text
group  shards  tasks  realpath_used  fallback  GPU total  runner speedup
null   64      18096  18096          0         45.404s    0.952645x
2      32      18096  18096          0         45.346s    0.989676x
4      16      18096  18096          0         44.835s    1.011415x
8      8       18096  18096          0         44.811s    1.022417x
16     4       18096  18096          0         45.003s    1.028119x
32     2       18096  18096          0         45.114s    1.028873x
```

This is not a broad performance claim. It shows that reducing runner shard
count can amortize enough overhead to make the bounded MALAT1 trust path
slightly faster than baseline, while preserving the digest and keeping CPU
`preAlign` out of the candidate scoreInfo path.

Group32 scaling keeps that small positive signal through MALAT1 first256:

```text
record_limit  shards  tasks  realpath_used  fallback  GPU total  runner speedup
64            2       18096  18096          0         45.115s    1.029346x
128           4       40128  40128          0         94.845s    1.041244x
256           8       80640  80640          0         190.212s   1.040806x
```

This strengthens the MALAT1-like grouped trust path, but the effect size is
still modest. It supports setup amortization and batching work; it does not
close the broad scoreInfo/preAlign replacement goal.

## Replay Reduction Boundary

The two-contract group32 audited runner has a passive replay diagnostic for
whether GASAL2-selected attempts can reduce downstream CPU align work while
preserving legacy scoreInfo emission semantics.

MALAT1 first8 with full replay cap:

```text
expanded replay:
  tasks = 1,824
  selected_attempts = 218,571
  align_attempts = 74,646
  triplex_mismatches = 0

selected-only replay:
  align_attempts = 99,023
  triplex_mismatches = 1,174
  first mismatch = selected_more
  repeated-scoreInfo extra triplexes = 965

grouped selected-prefix replay:
  align_attempts = 74,646
  triplex_mismatches = 0
```

The one attempted reduction shape, grouped selected-only replay, reduced align
attempts to about 54,961 but left one same-count content mismatch:

```text
selected provenance:
  scoreinfo=511;start=2166;cutlength=34;sw_score=52

legacy provenance:
  scoreinfo=511;start=2153;cutlength=47;sw_score=55
```

Replaying the scoreInfo prefix fixes correctness but removes the align-attempt
savings. This is a no-go for current selected-attempt CPU-align reduction, not
a no-go for the broader scoreInfo/minScore trust scaffold.

The two-contract group32 audited wrapper now has a real first256 gate:

```text
MALAT1 two-contract group32 audited first256:
  digest = 7f553b74ae31bed4cb7b9c312a188e2df19627ac4882c7ad7ac484d65b004a4e
  tasks = 80,640
  two_contract_used = 80,640
  realpath_used = 80,640
  two_contract_fallbacks = 0
  two_contract_score_mismatches = 0
  two_contract_min_score_mismatches = 0
  two_contract_scoreinfo_mismatches = 0
  realpath_fallbacks = 0
  gpu_scoreinfo_groups = 1,434,844
  baseline runner wall = 1058.944629s
  candidate runner wall = 1015.698961s
  candidate_vs_baseline = 1.042577x
  resume_audited = true
```

This is a stronger scoped MALAT1-like gate than the bounded first64/first128
checks: it proves full coverage for 80,640 two-contract tasks and preserves the
external digest gate through resume. It still does not grant GPU endpoint,
CIGAR, traceback, or output authority.

Full MALAT1 group32 trust runner result:

```text
record_limit = 670
group_target_records = 32
shards = 21
tasks = 200,400
realpath_used = 200,400
fallback = 0
gpu_scoreinfo_groups = 3,561,123
cpu_scoreinfo_groups = 0
cpu_prealign_seconds = 0
gpu_total_seconds = 482.3484
baseline runner wall = 2634.969799s
candidate runner wall = 2541.655441s
runner speedup = 1.036714x
digest = f080498ad8b9661100243e8eec89b6b54b566d7ed96fa5db7e268a8ce8513e0b
```

This is the strongest current MALAT1-like real runner profile. The explicit
runner preset is:

```text
--long-query-streaming-scoreinfo-gpu-trust-group32
result_contract = long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1
long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_group32_experimental_v1
```

It is equivalent to `--long-query-streaming-scoreinfo-gpu-trust
--group-target-records 32`. It is still default-off, experimental, and
external-digest-gated, but it is now full-MALAT1 clean and modestly faster than
the grouped baseline.
The group32 scaling and full-MALAT1 characterization wrappers exercise this
preset contract directly, and their summaries include the
`malat1_like_group32_experimental_v1` profile.

The audited runner entry point is:

```text
run_fasim_long_query_streaming_scoreinfo_trust_group32_audited.sh
audited_status = accepted
```

It runs both the CPU-authority `--group-target-records 32` baseline and
`--long-query-streaming-scoreinfo-gpu-trust-group32`, then fails closed with
`digest gate failed` if the external digest gate does not match.
`--resume` requires an existing accepted audit summary, forwards resume to both
underlying runner invocations, and reports `audited_resume = true` plus
`resumed_shards` counts. The audit summary also records
`baseline_runner_wall_seconds`, `candidate_runner_wall_seconds`, and
`candidate_vs_baseline` so the external digest gate carries its own runner wall
comparison. It also records `candidate_gpu_scoreinfo_total_seconds`,
`candidate_gpu_scoreinfo_call_seconds`, `candidate_gpu_scoreinfo_kernel_seconds`,
`candidate_non_gpu_wall_seconds`, `candidate_gpu_scoreinfo_wall_fraction`, and
`candidate_gpu_scoreinfo_call_fraction` so the accepted artifact states how much
of candidate wall time is actually in the GPU scoreInfo path. It also records
`candidate_realpath_extend_seconds`, `candidate_realpath_extend_calls`, and
`candidate_realpath_extend_fraction` for the CPU
`fastSIM_extend_from_scoreinfo()` consumption of trusted GPU scoreInfo. That
extend accounting now includes `candidate_realpath_extend_scoreinfo_groups`,
`candidate_realpath_extend_align_attempts`,
`candidate_realpath_extend_substr_seconds`,
`candidate_realpath_extend_align_seconds`,
`candidate_realpath_extend_align_fraction`,
`candidate_realpath_extend_convert_seconds`,
`candidate_realpath_extend_sort_seconds`, and
`candidate_realpath_extend_filter_seconds` so the next GASAL2/batched-extend
candidate can target the measured CPU consumption subphase instead of the
already-scoped GPU scoreInfo kernel. It also records
`candidate_realpath_extend_attempt_probe_requested`,
`candidate_realpath_extend_attempt_probe_active`,
`candidate_realpath_extend_attempt_probe_calls`,
`candidate_realpath_extend_attempt_probe_attempts`,
`candidate_realpath_extend_attempt_probe_selected_attempts`,
`candidate_realpath_extend_attempt_probe_seconds`, and
`candidate_realpath_extend_attempt_probe_fallbacks` for a default-off GASAL2
score-only/select probe over the same extend-attempt shape. That probe is
diagnostic only: CPU `fastSIM_extend_from_scoreinfo()` remains the output and
digest authority. It also records
`candidate_realpath_extend_segmented_attempt_probe_requested`,
`candidate_realpath_extend_segmented_attempt_probe_active`,
`candidate_realpath_extend_segmented_attempt_probe_segments`,
`candidate_realpath_extend_segmented_attempt_probe_calls`,
`candidate_realpath_extend_segmented_attempt_probe_attempts`,
`candidate_realpath_extend_segmented_attempt_probe_selected_attempts`,
`candidate_realpath_extend_segmented_attempt_probe_seconds`, and
`candidate_realpath_extend_segmented_attempt_probe_fallbacks` for a segmented
extend-attempt probe that keeps the current short-query GASAL2 select API guard
intact. It also records
`candidate_realpath_extend_flush_segmented_attempt_probe_requested`,
`candidate_realpath_extend_flush_segmented_attempt_probe_active`,
`candidate_realpath_extend_flush_segmented_attempt_probe_flushes`,
`candidate_realpath_extend_flush_segmented_attempt_probe_segments`,
`candidate_realpath_extend_flush_segmented_attempt_probe_calls`,
`candidate_realpath_extend_flush_segmented_attempt_probe_attempts`,
`candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts`,
`candidate_realpath_extend_flush_segmented_attempt_probe_seconds`, and
`candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks` for a
flush-level segmented extend-attempt probe that batches trusted scoreInfo
attempts before running bounded query segments. It also records
`candidate_realpath_extend_flush_segmented_replay_probe_requested`,
`candidate_realpath_extend_flush_segmented_replay_probe_active`,
`candidate_realpath_extend_flush_segmented_replay_probe_tasks`,
`candidate_realpath_extend_flush_segmented_replay_probe_selected_attempts`,
`candidate_realpath_extend_flush_segmented_replay_probe_align_attempts`,
`candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches`,
`candidate_realpath_extend_flush_segmented_replay_probe_seconds`, and
`candidate_realpath_extend_flush_segmented_replay_probe_fallbacks` for a capped
CPU replay diagnostic over flush-level selected attempts. It also records
`candidate_post_scoreinfo_unattributed_seconds` and
`candidate_post_scoreinfo_unattributed_fraction` for the remaining accepted-run
wall time outside the GPU scoreInfo accounting.

The first8 real audited gate now uses the flush-level segmented diagnostic and
breaks the trusted-scoreInfo consumption down far enough to pick the next
target:

```text
digest = 093a0d693301322e027ba6f3bd760bcbde60759131f156224f3924b7478581df
tasks = 1,824
realpath_used = 1,824
gpu_scoreinfo_groups = 31,272
candidate_vs_baseline ~= 0.93x
candidate_gpu_scoreinfo_wall_fraction ~= 0.205
candidate_realpath_extend_seconds ~= 10.17
candidate_realpath_extend_fraction ~= 0.407
candidate_realpath_extend_scoreinfo_groups = 31,272
candidate_realpath_extend_align_attempts = 74,646
candidate_realpath_extend_align_seconds ~= 10.12
candidate_realpath_extend_align_fraction ~= 0.405
candidate_realpath_extend_attempt_probe_requested = 1,824
candidate_realpath_extend_attempt_probe_calls = 1,752
candidate_realpath_extend_attempt_probe_attempts = 125,088
candidate_realpath_extend_attempt_probe_active = 0
candidate_realpath_extend_attempt_probe_fallbacks = 1,752
candidate_realpath_extend_segmented_attempt_probe_requested = 0
candidate_realpath_extend_segmented_attempt_probe_active = 0
candidate_realpath_extend_segmented_attempt_probe_segments = 0
candidate_realpath_extend_segmented_attempt_probe_calls = 0
candidate_realpath_extend_segmented_attempt_probe_attempts = 0
candidate_realpath_extend_segmented_attempt_probe_selected_attempts = 0
candidate_realpath_extend_segmented_attempt_probe_seconds = 0
candidate_realpath_extend_segmented_attempt_probe_fallbacks = 0
candidate_realpath_extend_flush_segmented_attempt_probe_requested = 16
candidate_realpath_extend_flush_segmented_attempt_probe_active = 64
candidate_realpath_extend_flush_segmented_attempt_probe_flushes = 16
candidate_realpath_extend_flush_segmented_attempt_probe_segments = 64
candidate_realpath_extend_flush_segmented_attempt_probe_calls = 64
candidate_realpath_extend_flush_segmented_attempt_probe_attempts = 500,352
candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts ~= 218,570
candidate_realpath_extend_flush_segmented_attempt_probe_seconds ~= 1.44
candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks = 0
candidate_realpath_extend_flush_segmented_replay_probe_requested = 16
candidate_realpath_extend_flush_segmented_replay_probe_tasks = 16
candidate_realpath_extend_flush_segmented_replay_probe_align_attempts = 638
candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches = 0
candidate_realpath_extend_flush_segmented_replay_probe_fallbacks = 0
candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches = 0
candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches = 0
candidate_post_scoreinfo_unattributed_fraction ~= 0.795
```

This shows that the trusted GPU scoreInfo path is no longer the main scoped
bottleneck on first8. Almost all measured CPU
`fastSIM_extend_from_scoreinfo()` time is inside repeated `aligner.Align()`
attempts. The first diagnostic GASAL2 score-only/select attempt probe preserves
the external digest gate but is not active for MALAT1 first8 under the formal
`FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812` guard: stderr records
`GASAL2 score length guard: query_len=8708 > max_query_len=2812`. The next
segmented extend-attempt probe keeps that guard intact and is fallback-clean,
but its earlier naive per-scoreInfo/per-segment shape was performance no-go
(`~44s` segmented probe time on MALAT1 first8). The flush-level segmented
diagnostic keeps the same 500,352 segment/attempt evaluations while reducing
GASAL2 select calls from 7,008 to 64 and reducing the diagnostic time to
roughly 1.3s with fallback still zero. The next implementation direction remains
batched/GASAL2 extend attempt consumption. The capped replay probe is the first
diagnostic bridge from flush-level selected attempts back into CPU
`aligner.Align()` replay, but it is still output-passive and digest-gated; its
capped first8/group32 segmented replay is now clean. The fixed mismatch was a
diagnostic replay bug: the hand replay filtered until it collected `N` passing
triplexes, while legacy `fastSIM_extend_from_scoreinfo()` only inspects the
sorted top `N` before threshold filtering. With the replay filter matched to
legacy semantics, segmented replay, full hand replay, and oracle replay all
report zero triplex mismatches on the capped audited gate. This removes the
known selected-attempt replay mismatch, but it is not yet a full real-path
proof because the gate is capped to one task per flush.

The task-level oracle replay probe now calls the legacy `fastSIM_extend_from_scoreinfo()` helper a second time for the same capped task subset. On MALAT1 first8/group32 it is clean:

```text
candidate_realpath_extend_flush_oracle_replay_probe_tasks = 16
candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches = 0
candidate_realpath_extend_flush_oracle_replay_probe_seconds ~= 0.097
```

This proves the replay comparison and legacy helper re-entry can be clean. The
selected/full hand-replay diagnostic now agrees with that oracle on the capped
MALAT1 first8/group32 audited gate. GPU/GASAL2 selected attempts still cannot
be promoted to broad triplex output authority until the same zero-mismatch gate
covers a larger/full task scope with acceptable performance.

The replay cap is now explicit in the audited wrapper:

```text
--replay-probe-max-tasks N
```

The default remains `N=1` per flush. Expanded diagnostic runs preserve the same
CPU-output authority and only widen the replay comparison surface. `N=0` means
all tasks in each flush. The wrapper passes this through to
`--long-query-streaming-scoreinfo-gpu-flush-replay-probe-max-tasks`; it does
not give GPU endpoint, CIGAR, traceback, or output authority. The real audited
gate accepts `REPLAY_PROBE_MAX_TASKS=0` and fail-closes on replay mismatch or
fallback:

```text
MALAT1 first8/group32 replay cap=4:
  replay tasks = 64
  replay align attempts = 2,855
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0

MALAT1 first8/group32 replay cap=16:
  replay tasks = 256
  replay align attempts = 10,424
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0

MALAT1 first8/group32 replay cap=0:
  replay tasks = 1,824
  replay selected attempts = 218,570
  replay align attempts = 74,646
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0
  replay fallbacks = 0

MALAT1 first8/group32 selected-only replay cap=0:
  replay tasks = 1,824
  selected-only attempts = 218,570
  selected-only align attempts = 99,022
  selected-only selected scoreInfos = 31,272
  selected-only tasks with selected attempts = 1,752
  selected-only tasks with triplex = 1,348
  selected-only zero-triplex tasks = 476
  selected-only mismatch selected_empty = 5
  selected-only mismatch legacy_empty = 277
  selected-only mismatch selected_less = 28
  selected-only mismatch selected_more = 828
  selected-only mismatch same_count_diff = 36
  selected-only first mismatch task = 0
  selected-only first mismatch kind = selected_more
  selected-only first mismatch provenance = scoreinfo=7;start=4023;cutlength=37;sw_score=73;ref_begin=11;ref_end=30;query_begin=3460;query_end=3479
  selected-only scoreInfos with multiple triplexes = 845
  selected-only extra triplexes from repeated scoreInfo = 965
  selected-only triplex mismatches = 1,174
  selected-only fallbacks = 0
  decision = no-go for direct selected-only consumer

MALAT1 first16/group32 replay cap=0:
  replay tasks = 4,416
  replay align attempts = 186,488
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0

MALAT1 first32/group32 replay cap=0:
  replay tasks = 8,160
  replay align attempts = 344,974
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0

MALAT1 first64/group32 replay cap=0:
  replay tasks = 18,096
  replay align attempts = 764,324
  segmented replay mismatches = 0
  full hand replay mismatches = 0
  oracle replay mismatches = 0
```

This materially strengthens selected-attempt replay equivalence for the
MALAT1-like group32 gate. Cap 0 is a full replay of the checked first8,
first16, first32, and first64 task sets. The direct selected-only consumer is
not equivalent: most mismatches are selected-only extra triplexes rather than
coverage misses, and the first extra comes from an additional selected attempt
inside scoreInfo 7. The repeated-scoreInfo telemetry shows the direct consumer
breaks the legacy scoreInfo-level single-emission contract. It still does not
prove the full scoreInfo/preAlign replacement objective across broader MALAT1,
NEAT1, and other long-query shapes.

```bash
make check-fasim-gasal2-scoreinfo-scoped-milestone
make check-fasim-gasal2-scoreinfo-scoped-release-smoke
make check-fasim-gasal2-malat1-lite-equivalence-evidence
make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence
make check-fasim-long-query-streaming-scoreinfo-trust-runner
make check-fasim-long-query-streaming-scoreinfo-trust-group32-runner
make check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner
make check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real
make check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256
make check-fasim-long-query-streaming-scoreinfo-neat1-audited-runner-real
make check-fasim-long-query-streaming-scoreinfo-trust-runner-real
make check-fasim-gasal2-scoreinfo-current-state
make check-fasim-gasal2-full-goal-decision
make characterize-fasim-long-query-streaming-scoreinfo-trust-runner
make characterize-fasim-long-query-streaming-scoreinfo-trust-runner-workers
make characterize-fasim-long-query-streaming-scoreinfo-trust-runner-groups
make characterize-fasim-long-query-streaming-scoreinfo-trust-runner-group32-scaling
make characterize-fasim-long-query-streaming-scoreinfo-trust-runner-malat1-full-group32
make characterize-fasim-long-query-streaming-scoreinfo-malat1-full-trust
make characterize-fasim-long-query-streaming-scoreinfo-neat1-first64-trust
```
