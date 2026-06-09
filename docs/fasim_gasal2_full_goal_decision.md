# Fasim GASAL2 Full Goal Decision Audit

This audit records the current decision state for the active objective:
GPU-ize or GASAL2-ize scoreInfo/preAlign.

## Decision

```text
Current full-goal status: not complete
Scoped top5 status: conditional completion candidate
Universal replacement status: not proven
Long-query status: no real path
GASAL2 / GPU scoreInfo scoped feasibility checkpoint
Post-selected-replay status: scoped milestone, not completion
Current viable productized scope: short-query/H19 top5 artifact plus MEG3 grouping
MALAT1 streaming scoreInfo trust path: scoped go
MALAT1 grouped two-contract trust path: scoped/research go with modest speedup
NEAT1 streaming scoreInfo trust path: performance no-go
NEAT1 non-shared streaming scoreInfo trust path: replay clean but performance no-go
NEAT1 non-shared replay: clean through first128 but too slow for real path
Selected-attempt CPU-align reduction: no-go for current selector
Selected-attempt real output authority: not proven
Broad scoreInfo/preAlign replacement: not proven
Broad co-designed replacement-consumer shadow: correctness clean, performance no-go
Attempt-consumer shadow: correctness clean, no CPU-align reduction, performance no-go
```

Do not call update_goal complete for the original full objective from the
current evidence.

Only mark the original goal complete if universal replacement is proven or the
user explicitly accepts the narrowed top5-only product scope as the goal.

full objective remains open.

## Proven Path

The proven opt-in path is:

```text
--gasal2-top5-column-pruned-scoreinfo
```

Current positive evidence:

```text
scoreinfo_gasal2_active = 1 for short-query/H19
zero_legacy_score_runs = 1
top5 score/stability/nt_score clean
```

That path is a real scoreInfo/preAlign GPU/GASAL2 path for the scoped top5
artifact.

## Not Proven

The current evidence does not prove universal replacement:

```text
full `.lite` output is not contract output
final all-row TFO equivalence is not claimed
MALAT1/NEAT1 scoreinfo_gasal2_active = 0 via query guard
single-pass topN is not top5-safe
long-query no-last replay remains marginal through malat1_first128 speedup=1.038017x
current segmented no-last replay line: stopped for real path
full-query exact-column scoreInfo shadow is launch no-go for MALAT1 query_len=8708
shared-memory opt-in launches but is not scoreInfo-equivalent
long-query next-architecture decision = next_architecture_no_go
NEAT1 non-shared scoreInfo realpath replay is clean through first128 but candidate/baseline speedup=0.300675x
NEAT1 first64 fresh runtime attribution:
  candidate_wall_seconds = 121.948
  baseline_wall_seconds = 86.0335
  candidate_vs_baseline = 0.705493x
  gpu_total_seconds = 49.9507 (~41.0% candidate wall)
  realpath_extend_seconds = 52.0682 (~42.7% candidate wall)
  unattributed_overhead_seconds ~= 19.9291 (~16.3% candidate wall)
  current selector/global-state long-query shape is architecture no-go for broad replacement
NEAT1 speed ceiling:
  ideal_zero_gpu_total_speedup = 1.1950x
  ideal_zero_gpu_call_speedup = 0.9747x
  ideal_zero_realpath_extend_speedup = 1.2312x
  next architecture must reduce both GPU scoreInfo work and CPU realpath extend/align work
  make check-fasim-gasal2-neat1-speed-ceiling
NEAT1 next architecture requirements:
  kernel-only win is not sufficient
  If the prototype cannot reduce both GPU scoreInfo and realpath extend/align, stop the NEAT1 broad path
  make check-fasim-gasal2-neat1-next-architecture-requirements
replacement consumer shadow:
  selected-only replay is not sufficient
  If NEAT1 remains slower than CPU fallback, do not promote
  selected-only loses the scoreInfo-local break/best-end state machine
  grouped selected-prefix is clean only by expanding back to legacy prefix attempts
  make check-fasim-gasal2-replacement-consumer-shadow-requirements
  make check-fasim-gasal2-replacement-consumer-shadow-env
  make check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke
broad replacement-consumer shadow on NEAT1 first64:
  make check-fasim-gasal2-broad-neat1-first64-result
  decision = broad_path_current_architecture_no_go
  digest clean
  broad_path_active = 1
  broad_path_tasks = 3,058
  broad_path_scoreinfo_groups = 52,994
  broad_path_align_attempts = 264,970
  broad_path_triplex_mismatches = 0
  broad_path_missing_triplexes = 0
  broad_path_extra_triplexes = 0
  baseline_wall_seconds = 86.932816
  candidate_wall_seconds = 288.4177
  candidate_vs_baseline = 0.301413x
  broad_path_scoreinfo_seconds = 19.1704
  broad_path_consumer_seconds = 52.0465
  baseline_cpu_reference_seconds = 52.0833
  realpath_extend_align_attempts = 140,087
  candidate_wall_not_below_neat1_baseline_ceiling
  candidate_vs_baseline_not_above_1
  broad_scoreinfo_consumer_not_below_cpu_reference
  align_attempts_not_reduced
attempt-consumer shadow on NEAT1 first64:
  make check-fasim-gasal2-attempt-consumer-neat1-first64-result
  decision = attempt_consumer_shadow_no_cpu_align_reduction_no_go
  digest clean
  triplex_mismatches = 0
  missing_triplexes = 0
  extra_triplexes = 0
  attempts = 211,976
  selected_attempts = 140,087
  cpu_align_attempts = 140,087
  realpath_extend_align_attempts = 140,087
  score_seconds = 241.768
  total_seconds = 294.821
  candidate_vs_baseline = 0.148434x
  cpu_align_attempts_not_reduced
  candidate_vs_baseline_not_above_1
  attempt_consumer_total_not_below_cpu_reference
score-prepass state-machine consumer:
  FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1
  select_attempts_from_scores()
  CPU-align only the selected attempt per scoreInfo
  make check-fasim-gasal2-score-prepass-state-machine-consumer
NEAT1 runtime boundary: do not use audited replay wall time as real runtime speedup evidence
NEAT1 trust runtime first64 candidate/baseline speedup = 0.705493x
NEAT1 shared scoreInfo runner preset fails launch with invalid argument and does not enter scoreInfo realpath
direct selected-only replay over-emits repeated scoreInfos
selected-prefix replay clean but no CPU-align reduction
score-prepass state-machine trust traceback boundary:
  FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_SEGMENT_TRACEBACK_SHADOW=1
  FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_EXPANDED_SEGMENT_TRACEBACK_SHADOW=1
  selected-segment traceback is not equivalent
  expanded-segment oracle is clean only by requiring full NEAT1 query length
  expanded_segment_traceback_shadow_required_max_len = 22,767
  expanded_segment_traceback_shadow_required_over_gasal2_limit = 21,991
  current GASAL2 2,812 bp query guard
  GASAL2 selected/expanded segment traceback: no-go for real path
```

The guarded long-query rows are correctness-safe CPU fallback rows, not
GASAL2-active successes.

The selected-attempt CPU-align reduction line is also no-go for the current
selector. On MALAT1 first8/group32 with full replay cap:

```text
expanded selected-scoreInfo replay:
  align_attempts = 74,646
  triplex_mismatches = 0

direct selected-only replay:
  align_attempts = 99,023
  triplex_mismatches = 1,174
  reason = repeated scoreInfo over-emission

grouped selected-only reduction attempt:
  align_attempts ~= 54,961
  triplex_mismatches = 1
  first mismatch = same scoreInfo, different legacy window

grouped selected-prefix replay:
  align_attempts = 74,646
  triplex_mismatches = 0
```

So the current GASAL2-selected attempts do not provide a real CPU-align
reduction path: the reduced shape is not equivalent, and the equivalent prefix
shape collapses back to the expanded replay cost.

## Next Work

Next universal-path work must be a different long-query architecture or a
full-output/TFO equivalence proof.

The broad-path architecture gate is:

```bash
make check-fasim-gasal2-broad-path-architecture-gate
```

It records:

```text
previous_decision = broad_path_requires_co_designed_scoreinfo_and_consumer
decision = broad_path_current_architecture_no_go
```

That gate now records that the current co-designed replacement-consumer shadow
is correctness-clean but too slow on NEAT1 first64. Future broad work must use a
materially different long-query architecture that reduces both GPU scoreInfo
work and CPU realpath extend/align work. It forbids promoting the current
selector/global-state NEAT1 path, selected-only replay, score-prepass
state-machine consumer trust, segmented traceback, the current broad replay
consumer, or the scoped MALAT1 two-contract runtime as a broad replacement.

The concrete next implementation plan is:

```bash
make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan
```

It records the completed broad replacement-consumer shadow checkpoint. That
checkpoint is not a real path; the full objective remains open until a new
architecture passes the hard correctness and performance gates.

The full-output/TFO equivalence proof now has a focused local gate:

```bash
make check-fasim-lite-full-equivalence
python3 scripts/compare_fasim_lite_full_equivalence.py \
  --baseline <cpu-authority-TFOsorted.lite> \
  --candidate <gpu-or-gasal2-TFOsorted.lite>
python3 scripts/compare_fasim_lite_full_equivalence.py \
  --baseline-report <cpu-report.json> \
  --candidate-report <gpu-or-gasal2-report.json>
```

That checker compares the complete de-duplicated row set for the detected
schema, not only top5 summary payloads. It supports 14-column `schema=lite`
outputs and 19-column `schema=tfosorted` outputs, reports full-row digests,
missing/extra row counts, and the first missing/extra row. It fails closed on
unsupported schemas, mixed baseline/candidate schemas, and malformed rows with
too few or too many fields, reporting `schema_error` or `parse_error` instead
of comparing partially parsed rows. Passing this fixture gate does not prove
any workload by itself; it only makes the required full-output evidence
mechanically checkable when a candidate run exists.

For runner reports, the comparator resolves `merged_output` by default. It can
also resolve another explicit report field with `--report-output-field`, for
example `topk_lite_output`, but a topK-lite report comparison remains a top5
artifact check and must not be presented as full-output equivalence.

There is one focused MALAT1-like TFOsorted evidence gate:

```bash
make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence
```

It runs MALAT1 first8/group32 two-contract with `--output-mode tfosorted` and
checks the complete 19-column row set:

```text
schema=tfosorted
baseline_rows=796
candidate_rows=796
missing_rows=0
extra_rows=0
full_rows_equal=true
```

That is a scoped first8 proof point only. It does not prove full MALAT1,
NEAT1, or broad long-query TFOsorted equivalence, and it does not close the
full objective.

The same gate supports an optional heavier first64 run:

```bash
CHECK_FIRST64=1 make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence
make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full
```

The exercised first64 result was also row-set clean:

```text
schema=tfosorted
baseline_rows=9741
candidate_rows=9741
missing_rows=0
extra_rows=0
full_rows_equal=true
```

That strengthens the MALAT1-like TFOsorted correctness evidence, but it remains
a limited-scope probe and its candidate wall time was slower than baseline.

The full-MALAT1 TFOsorted equivalence gate is intentionally separate and heavy:

```text
MALAT1 full TFOsorted:
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

The clean runtime wall evidence for the same MALAT1-like two-contract bridge
comes from the no-probe gate:

```bash
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted
```

That gate uses
`--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32`, which does
not enable the audited replay/attempt probes; in other words, it does not use
the audited replay/attempt probes. It requires full `schema=lite` or
`schema=tfosorted` row-set
equality, digest equality, `two_contract_used == tasks`,
`realpath_used == tasks`, zero fallbacks/mismatches, and
`probe_positive_numeric_keys=0`. The candidate report records
`result_contract = long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32_experimental_v1`.

```text
MALAT1 first8 no-probe:
  rows = 796
  candidate_vs_baseline = 0.990695x
  tasks = 1,824
  probe_positive_numeric_keys = 0

MALAT1 first8 TFOsorted no-probe:
  schema = tfosorted
  rows = 796
  candidate_vs_baseline = 0.990699x
  tasks = 1,824
  probe_positive_numeric_keys = 0

MALAT1 first64 no-probe:
  rows = 9,741
  candidate_vs_baseline = 1.030868x
  tasks = 18,096
  gpu_scoreinfo_groups = 319,280
  probe_positive_numeric_keys = 0

MALAT1 first128 no-probe:
  rows = 22,531
  candidate_vs_baseline = 1.043793x
  tasks = 40,128
  gpu_scoreinfo_groups = 715,473
  probe_positive_numeric_keys = 0

MALAT1 first256 no-probe:
  rows = 42,504
  candidate_vs_baseline = 1.042764x
  tasks = 80,640
  gpu_scoreinfo_groups = 1,434,844
  probe_positive_numeric_keys = 0

MALAT1 full no-probe:
  rows = 98,713
  digest = f080498ad8b9661100243e8eec89b6b54b566d7ed96fa5db7e268a8ce8513e0b
  candidate_vs_baseline = 1.037747x
  tasks = 200,400
  two_contract_used = 200,400
  realpath_used = 200,400
  gpu_scoreinfo_groups = 3,561,123
  probe_positive_numeric_keys = 0

MALAT1 full TFOsorted no-probe:
  schema = tfosorted
  rows = 98,713
  digest = ac667f460cd1446bc5598fa163f7fc2755265bf56e6b82c105e672873c895ffc
  candidate_vs_baseline = 1.037590x
  tasks = 200,400
  two_contract_used = 200,400
  realpath_used = 200,400
  gpu_scoreinfo_groups = 3,561,123
  probe_positive_numeric_keys = 0
```

This is a scoped milestone for the MALAT1-like grouped two-contract bridge,
not broad completion of the original objective.

The current next-architecture plan gate is:

```bash
make check-fasim-gasal2-long-query-next-architecture-plan
```

The current next-architecture decision gate is:

```bash
make check-fasim-gasal2-long-query-next-architecture-decision
```

The lower-shared-memory streaming scoreInfo design is no longer just a future
direction. It has already produced these checkpoints:

```text
legacy-byte streaming scoreInfo: correctness clean, performance no-go
hot GPU minScore / realpath trust: MALAT1 scoped positive, modest speedup
fused minScore: no-go; score/minScore and scoreInfo are separate contracts
two-contract bridge: MALAT1 scoped positive, still default-off and digest-gated
selected-attempt replay reduction: no-go for current selector
NEAT1 current execution shape: correctness-clean diagnostics but performance no-go
```

The historical design and fused-minScore gates remain part of the audit:

```bash
make check-fasim-long-query-streaming-scoreinfo-design
make check-fasim-long-query-streaming-scoreinfo-fused-minscore-design
```

It showed that legacy calc-score minScore and byte-profile scoreInfo are
separate contracts. The two-contract bridge is the current scoped bridge
checkpoint, not broad completion:

```bash
make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design
make check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256
```

It keeps the two contracts separate and does not change the full-goal status.
The selected-replay diagnostics then showed that GASAL2-selected attempts cannot
currently reduce CPU `aligner.Align()` attempts while preserving the legacy
scoreInfo-level emission contract.

The already-tested no-go lines should not be promoted:

```text
do not promote single-pass topN
do not promote segmented long-query no-last replay
do not promote segmented score-prepass state-machine consumer trust
do not promote exact-tile long-query candidate union
do not promote long-query exact-column smem opt-in
do not promote fused minScore
do not promote MALAT1 grouped two-contract trust as a broad long-query path
do not promote selected-attempt CPU-align reduction from current selector
do not claim full output from the top5 artifact contract
do not use GPU endpoint/CIGAR/traceback authority
```

The scoped top5 product path now has a focused release smoke:

```bash
make check-fasim-gasal2-top5-release-smoke
```

Latest release-smoke boundary:

```text
formal_preset_example = meg3_first32
formal_preset_topk_artifact_match = true
formal_preset_gasal2_requests = 63,035
formal_preset_exact_scoreinfo_gpu_tasks = 1,536
formal_preset_speedup_vs_cpu_worker_wall_sum < 1.0
```

This is a contract smoke, not a performance claim, and it does not change the
full-goal status.

The MALAT1-like scoreInfo scoped milestone also has a focused release smoke:

```bash
make check-fasim-gasal2-scoreinfo-scoped-release-smoke
```

It reruns the first8 no-probe lite and TFOsorted checks plus the scoped/full-goal
static gates. It is a scoped MALAT1-like smoke, not a universal replacement
smoke, and it does not change the full-goal status.

Allowed continuation:

```text
accepted top5-only product scope with explicit output contract, or
full-output/TFO equivalence proof over the intended workload scope, or
a genuinely different long-query execution design, not the current selector/global-state path
```

## Gates

```bash
make check-fasim-gasal2-scoreinfo-current-state
make check-fasim-gasal2-top5-scoped-completion-candidate
make check-fasim-gasal2-full-goal-decision
make check-fasim-gasal2-long-query-current-stop
make check-fasim-gasal2-long-query-next-architecture-plan
make check-fasim-gasal2-long-query-next-architecture-decision
make check-fasim-long-query-streaming-scoreinfo-design
make check-fasim-long-query-streaming-scoreinfo-fused-minscore-design
make check-fasim-gasal2-score-prepass-state-machine-stop
```
