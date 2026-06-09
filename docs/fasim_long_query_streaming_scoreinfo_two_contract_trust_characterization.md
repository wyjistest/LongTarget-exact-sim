# Fasim Long-Query Streaming ScoreInfo Two-Contract Trust Characterization

This is a characterization gate for the GASAL2 / GPU scoreInfo scoped
feasibility checkpoint. It is not completion of the full scoreInfo/preAlign
GPU/GASAL2 objective.

## Scope

The runner option under test is:

```text
--long-query-streaming-scoreinfo-gpu-two-contract-trust
result_contract = long_query_streaming_scoreinfo_gpu_two_contract_trust_experimental_v1
```

The MALAT1-like grouped preset under test is:

```text
--long-query-streaming-scoreinfo-gpu-two-contract-trust-group32
result_contract = long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1
long_query_streaming_scoreinfo_gpu_trust_profile = malat1_like_two_contract_group32_experimental_v1
```

It sets:

```text
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1
```

CPU output digest remains the external authority. GPU endpoint/CIGAR/traceback
authority remains forbidden.

The fail-closed audited wrapper for the grouped preset is:

```bash
scripts/run_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited.sh
```

It runs a CPU-authority `--group-target-records 32` baseline and the grouped
two-contract candidate. It reports `audited_status = accepted` only when the
external digest gate and two-contract coverage checks pass; otherwise it exits
non-zero with `digest gate failed` or the failing coverage counter. It does not
give GPU endpoint, CIGAR, traceback, or output authority.
`--replay-probe-max-tasks N` defaults to `1`; `N=0` means all tasks in each
flush. It is passed through to
`--long-query-streaming-scoreinfo-gpu-flush-replay-probe-max-tasks` and only
widens the diagnostic selected-attempt replay surface. The accepted summary
records `candidate_realpath_extend_flush_segmented_replay_probe_tasks` and
`candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches`
when that probe is active.
It also records
`candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks`
and
`candidate_realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos`,
`candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected`,
`candidate_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex`,
`candidate_realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks`,
and
`candidate_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches`
plus mismatch-classification and first-mismatch fields
for the stricter selected-only diagnostic, which does not expand a selected
scoreInfo group back to every legacy attempt and therefore remains output-
passive evidence.
It also records
`candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks`,
`candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_attempts`,
`candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_align_attempts`,
`candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_scoreinfos`,
`candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_selected`,
`candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_triplex`,
`candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_zero_triplex_tasks`,
`candidate_realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches`,
and first-mismatch provenance fields for the grouped selected-prefix replay
diagnostic.

Current first8 diagnostic decision:

```text
expanded selected-scoreInfo replay:
  triplex_mismatches = 0
  align_attempts = 74,646

selected-only replay:
  triplex_mismatches = 1,174
  no-go because it over-emits repeated scoreInfos

grouped selected-prefix replay:
  triplex_mismatches = 0
  align_attempts = 74,646
  no CPU-align reduction versus expanded replay
```

The grouped selected-only reduction attempt reached about 54,961 align
attempts, but left one same-count mismatch in scoreInfo 511. Replaying the
scoreInfo prefix restores correctness and shows that the current selector does
not yet provide a useful CPU-align reduction path.

The real MALAT1 smoke gate for that wrapper is:

```bash
make check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real
make check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first64
make check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first128
make check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256
```

## Characterization

Default smoke:

```bash
make characterize-fasim-long-query-streaming-scoreinfo-two-contract-trust
```

Expanded gates:

```bash
TWO_CONTRACT_CASES="MALAT1:64 NEAT1:64" \
make characterize-fasim-long-query-streaming-scoreinfo-two-contract-trust

TWO_CONTRACT_CASES="MALAT1:670" \
make characterize-fasim-long-query-streaming-scoreinfo-two-contract-trust

TWO_CONTRACT_TRUST_PRESET=group32 GROUP_TARGET_RECORDS=32 \
TWO_CONTRACT_CASES="MALAT1:670" \
make characterize-fasim-long-query-streaming-scoreinfo-two-contract-trust
```

The default smoke is intentionally small (`MALAT1 first8`) so it can act as a
repeatable runner-level gate. The expanded cases are the meaningful milestone
cases:

```text
MALAT1 first8
MALAT1 first64
NEAT1 first64
MALAT1 full
```

Current checked rows:

```text
MALAT1 first8:
  digest clean
  tasks = 1,824
  two_contract_used = 1,824
  two_contract_fallbacks = 0
  score/minScore/scoreInfo mismatches = 0/0/0
  gpu_scoreinfo_groups = 31,272
  cpu_scoreinfo_groups = 0
  gpu_minscore_hot = 8/8 shards
  minscore_seconds ~= 0
  two_contract_total_seconds ~= 5.1s
  candidate_vs_baseline = 0.92x

MALAT1 first64:
  digest clean
  tasks = 18,096
  two_contract_used = 18,096
  two_contract_fallbacks = 0
  score/minScore/scoreInfo mismatches = 0/0/0
  gpu_scoreinfo_groups = 319,280
  cpu_scoreinfo_groups = 0
  candidate_vs_baseline = 0.95x before hot-minScore runner wiring

MALAT1 first64 group32:
  digest clean
  grouped_shard_count = 2
  tasks = 18,096
  two_contract_used = 18,096
  two_contract_fallbacks = 0
  score/minScore/scoreInfo mismatches = 0/0/0
  gpu_scoreinfo_groups = 319,280
  cpu_scoreinfo_groups = 0
  gpu_minscore_hot = 2/2 shards
  minscore_seconds ~= 0
  candidate_vs_baseline = 1.03x

MALAT1 full group32:
  digest clean
  result_contract = long_query_streaming_scoreinfo_gpu_two_contract_trust_group32_experimental_v1
  trust_profile = malat1_like_two_contract_group32_experimental_v1
  grouped_shard_count = 21
  tasks = 200,400
  two_contract_used = 200,400
  two_contract_fallbacks = 0
  score/minScore/scoreInfo mismatches = 0/0/0
  gpu_scoreinfo_groups = 3,561,123
  cpu_scoreinfo_groups = 0
  cpu_prealign_seconds = 0
  gpu_minscore_hot = 21/21 shards
  minscore_seconds ~= 0
  two_contract_total_seconds = 483.9203s
  baseline_runner_wall_seconds = 2627.172906s
  candidate_runner_wall_seconds = 2531.286191s
  candidate_vs_baseline = 1.037881x
  digest = f080498ad8b9661100243e8eec89b6b54b566d7ed96fa5db7e268a8ce8513e0b

NEAT1 first64:
  digest clean through CPU fallback
  tasks = 3,072
  two_contract_active = 0/64 shards
  two_contract_fallbacks = 64/64 shards
  realpath_used = 0
  realpath_fallbacks = 64
  error = invalid argument
```

## Required Counters

The script records:

```text
tasks
two_contract_used
two_contract_fallbacks
two_contract_score_mismatches
two_contract_min_score_mismatches
two_contract_scoreinfo_mismatches
realpath_used
realpath_fallbacks
gpu_scoreinfo_groups
cpu_scoreinfo_groups
cpu_prealign_seconds
compare_seconds
two_contract_total_seconds
two_contract_h2d_seconds
two_contract_kernel_seconds
two_contract_d2h_seconds
gpu_call_seconds
kernel_seconds
baseline_runner_wall_seconds
candidate_runner_wall_seconds
candidate_vs_baseline
```

Hard correctness gate:

```text
score_mismatches = 0
min_score_mismatches = 0
scoreinfo_mismatches = 0
realpath_fallbacks = 0
cpu_scoreinfo_groups = 0
cpu_prealign_seconds = 0
digest unchanged
```

## Decision

```text
decision = two_contract_trust_characterization_gate
```

Passing the smoke gate means the two-contract trust runner remains wired and
digest-clean for the checked sample. It does not prove a production path.

The next real decision depends on the expanded cases:

```text
MALAT1 first64 / full:
  must remain digest-clean and should be no worse than the older trust path

NEAT1 first64:
  must be tested before any broad long-query claim
  if it reports two_contract_bridge_launch_failed, no broad replacement claim
  if it runs but candidate_vs_baseline remains below 1.0x, no broad replacement claim
```

Do not promote this path to default behavior unless representative workloads
show stable digest-clean output and stable runtime value.

Current NEAT1 first64 boundary:

```text
two_contract_bridge_launch_failed
64/64 fallback
error = invalid argument
digest unchanged through CPU fallback
```

This is a valid characterization result, not an active trust success.
