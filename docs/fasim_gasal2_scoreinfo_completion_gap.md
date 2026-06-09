# Fasim GASAL2 ScoreInfo Completion Gap

This checkpoint audits the active objective:

```text
GPU-ize or GASAL2-ize scoreInfo/preAlign.
```

It exists to prevent the current top5 artifact milestone from being mistaken
for completion of the full objective.

## Current Proven Milestone

The current reviewed surface is:

```text
--gasal2-top5-column-pruned-scoreinfo
```

The current-state milestone gate is:

```bash
make check-fasim-gasal2-scoreinfo-current-state
```

That gate proves a short-query/H19 top5 artifact path:

```text
chr21+chr22:
  top5 artifact clean
  GASAL2 requests > 0
  GASAL2 traceback requests > 0
  exact scoreInfo GPU tasks > 0
  fallback/overflow = 0
  speedup vs CPU worker wall sum = 40.119136x

MEG3 grouped:
  complete-record grouped wrapper path clean
  GASAL2 requests > 0
  exact scoreInfo GPU tasks > 0
  fallback/overflow = 0

runtime examples boundary:
  MEG3 scoreinfo_gasal2_active = 1
  MALAT1/NEAT1 scoreinfo_gasal2_active = 0 via query guard
```

This is real progress toward the objective because scoreInfo/preAlign work is
active on GPU/GASAL2 for the checked short-query top5 artifact path.

The broader scoped feasibility checkpoint is:

```text
GASAL2 / GPU scoreInfo scoped feasibility checkpoint
MALAT1 streaming scoreInfo trust path: scoped go
NEAT1 non-shared streaming scoreInfo trust path: replay clean but performance no-go
Broad scoreInfo/preAlign replacement: not proven
```

That checkpoint records the full MALAT1 trust positive and the NEAT1
non-shared replay-clean boundary, but it still does not complete the broad
objective because NEAT1 is a large performance no-go and the shared runner
trust preset does not enter scoreInfo realpath.

## Not Complete

The full objective is not complete.

The current milestone does not prove:

```text
not universal scoreInfo/preAlign replacement
not full lite-output equivalence
not exact legacy scoreInfo equivalence
not final all-row TFO equivalence
not `aligner.Align()` replacement
not GPU endpoint/CIGAR/traceback authority
not broad long-query MALAT1/NEAT1 GASAL2 active path
not default production path
```

Long-query examples remain guarded:

```text
GASAL2_MAX_QUERY_LEN = 2812
MEG3 query_len = 1582
MALAT1 query_len = 8708
NEAT1 query_len = 22767
```

The current best long-query no-last scaling is diagnostic only across
first8/first16/first32/first64/first128:

```text
malat1_first8 speedup = 1.009996x
malat1_first16 speedup = 1.029101x
malat1_first32 speedup = 1.031832x
malat1_first64 speedup = 1.034623x
malat1_first128 speedup = 1.038017x
```

That is not enough to justify a long-query real path.

NEAT1 now has a stronger correctness boundary for the non-shared legacy-byte
scoreInfo realpath, but the performance result is a hard no-go:

```text
NEAT1 runtime boundary:
  do not use audited replay wall time as real runtime speedup evidence

NEAT1 non-shared trust runtime first64:
  candidate/baseline speedup = 0.705493x

NEAT1 first64 fresh runtime attribution:
  candidate_wall_seconds = 121.948
  baseline_wall_seconds = 86.0335
  candidate_vs_baseline = 0.705493x
  gpu_total_seconds = 49.9507 (~41.0% candidate wall)
  realpath_extend_seconds = 52.0682 (~42.7% candidate wall)
  unattributed_overhead_seconds ~= 19.9291 (~16.3% candidate wall)

The current selector/global-state long-query shape is architecture no-go for
broad replacement. The slowdown is not explained by H2D/D2H, validation,
compare, or CPU fallback; both the GPU scoreInfo work and CPU realpath
extend/align work remain large.

NEAT1 speed ceiling:

```text
ideal_zero_gpu_total_speedup = 1.1950x
ideal_zero_gpu_call_speedup = 0.9747x
ideal_zero_realpath_extend_speedup = 1.2312x
next architecture must reduce both GPU scoreInfo work and CPU realpath extend/align work
```

It is checked by:

```bash
make check-fasim-gasal2-neat1-speed-ceiling
```

The follow-up requirements gate is:

```text
NEAT1 next architecture requirements:
  kernel-only win is not sufficient
  If the prototype cannot reduce both GPU scoreInfo and realpath extend/align, stop the NEAT1 broad path
```

```bash
make check-fasim-gasal2-neat1-next-architecture-requirements
```

The broad-path architecture gate is:

```bash
make check-fasim-gasal2-broad-path-architecture-gate
```

```text
previous_decision = broad_path_requires_co_designed_scoreinfo_and_consumer
decision = broad_path_current_architecture_no_go
```

It records that the current co-designed broad replacement-consumer shadow is
correctness-clean but a performance no-go. Kernel-only scoreInfo work is not
enough, selected-only replay is not a valid broad consumer, and the current
replay-heavy broad state-machine consumer is not a real path.

The concrete implementation plan/checkpoint for that broad path is checked by:

```bash
make check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan
make check-fasim-gasal2-broad-neat1-first64-result
```

It defines and measures a co-designed scoreInfo plus replacement-consumer
shadow. The measured NEAT1 first64 checkpoint is:

```text
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
decision_reasons:
  candidate_wall_not_below_neat1_baseline_ceiling
  candidate_vs_baseline_not_above_1
  broad_scoreinfo_consumer_not_below_cpu_reference
  align_attempts_not_reduced
```

The full objective remains open until a new architecture passes the NEAT1
first64 hard correctness and performance gates.

The replacement consumer shadow requirements are now tracked separately:

```text
replacement consumer shadow:
  selected-only replay is not sufficient
  If NEAT1 remains slower than CPU fallback, do not promote
  selected-only loses the scoreInfo-local break/best-end state machine
  grouped selected-prefix is clean only by expanding back to legacy prefix attempts
```

```bash
make check-fasim-gasal2-replacement-consumer-shadow-requirements
make check-fasim-gasal2-replacement-consumer-shadow-env
make check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke
```

The only remaining plausible replacement-consumer design is score-prepass
state-machine consumer:

```text
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_CONSUMER_SHADOW=1
select_attempts_from_scores()
CPU-align only the selected attempt per scoreInfo
```

```bash
make check-fasim-gasal2-score-prepass-state-machine-consumer
```

NEAT1 non-shared audited replay first128:
  tasks = 6,144
  realpath_used = 6,144
  gpu_scoreinfo_groups = 105,845
  replay align attempts = 281,588
  segmented/full/oracle replay mismatches = 0
  candidate/baseline speedup = 0.300675x

NEAT1 shared runner trust preset:
  shared scoreInfo kernel error = invalid argument
  gpu_scoreinfo_groups = 0
  realpath_used = 0
  realpath_fallbacks = 4 on first4
```

The current long-query implementation stop checkpoint records:

```text
current segmented no-last replay line: stopped for real path
```

It is checked by:

```bash
make check-fasim-gasal2-long-query-current-stop
```

The single-pass topN scoreInfo probe is also not a completion path:

```text
first DP pass can produce bounded topN scoreInfo-like candidates
does not currently produce exact legacy scoreInfo
not top5-safe for the current artifact contract
```

The checked sweep is:

```bash
make check-fasim-gasal2-single-pass-topn-sweep
```

Compared with the older exact pruned-output baseline, it eliminates the legacy
max-score and exact scoreInfo double-pass, but the bounded candidate population
changes nt-score and stability top5 rows. It is therefore diagnostic only, not a
real scoreInfo/preAlign replacement. The current formal preset is instead the
column-pruned one-DP path and is tracked separately by the milestone gate.

## Completion Requirements

To mark the original objective complete, one of these scopes must be explicitly
proven.

### Universal Replacement

For a broad scoreInfo/preAlign replacement claim:

```text
short-query and long-query workloads are active-path clean
scoreinfo_gasal2_active = 1 where the path is claimed
GASAL2/exact-scoreInfo fallback = 0 where the path is claimed
overflow = 0
top5 score/stability/nt_score clean
full output or explicitly scoped output contract clean
performance wins CPU authority on representative workloads
```

For a full-output/TFO equivalence claim, use the canonical full-row comparator:

```bash
make check-fasim-lite-full-equivalence
python3 scripts/compare_fasim_lite_full_equivalence.py \
  --baseline <cpu-authority-TFOsorted.lite> \
  --candidate <gpu-or-gasal2-TFOsorted.lite>
python3 scripts/compare_fasim_lite_full_equivalence.py \
  --baseline-report <cpu-report.json> \
  --candidate-report <gpu-or-gasal2-report.json>
```

The comparator checks the complete de-duplicated row set for the detected
schema and reports missing and extra rows. It supports both 14-column
`schema=lite` outputs and 19-column `schema=tfosorted` outputs, but baseline and
candidate schemas must match. It fails closed on unsupported schemas,
mixed-schema comparisons, and malformed rows with too few or too many fields;
those are schema/parse failures, not row-set mismatches. Top5 artifact equality
is not a substitute for this gate when the claim is full output.

When report paths are provided, the comparator resolves the runner
`merged_output` field by default. Explicitly selecting `topk_lite_output` keeps
the comparison in the top5 artifact scope; it is not full-output evidence.

The current focused TFOsorted workload probe is:

```bash
make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence
```

That gate runs the MALAT1 first8/group32 two-contract path with
`--output-mode tfosorted` and requires:

```text
schema=tfosorted
baseline_rows=796
candidate_rows=796
missing_rows=0
extra_rows=0
full_rows_equal=true
```

This is meaningful 19-column row-set evidence for a small MALAT1-like slice,
but it is not full MALAT1 or broad long-query TFO equivalence.

An optional heavier form of that gate has also been exercised:

```bash
CHECK_FIRST64=1 make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence
make check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full
```

The first64 run remains 19-column clean:

```text
schema=tfosorted
baseline_rows=9741
candidate_rows=9741
missing_rows=0
extra_rows=0
full_rows_equal=true
```

It is still correctness evidence only; candidate wall time was slower than
baseline on that probe.

The full-MALAT1 TFOsorted gate is tracked separately:

```text
MALAT1 full TFOsorted:
  schema=tfosorted
  baseline_rows=98713
  candidate_rows=98713
  baseline_full_digest=ff415800b5cbc226f979eb85c7a93387b6e07f1e17dc279342a594dd6b76bdca
  candidate_full_digest=ff415800b5cbc226f979eb85c7a93387b6e07f1e17dc279342a594dd6b76bdca
  missing_rows=0
  extra_rows=0
  full_rows_equal=true
  tasks=200400
  candidate_vs_baseline=0.403059x
  decision=full-output correctness proof, not runtime claim
```

The current runtime breakdown gate for that first64 probe is:

```bash
make check-fasim-gasal2-malat1-tfosorted-runtime-breakdown
```

It records:

```text
wall_delta = 8.898913s
diagnostic_probe_seconds = 22.010077s
attempt_probe_seconds = 15.994410s
decision = audited_wall_not_real_runtime_claim
```

So the audited `tfosorted` wall time should not be interpreted as a real
runtime regression or speedup claim.

The no-probe two-contract runtime gate is separate from that audited
`tfosorted` probe:

```bash
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full
make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted
```

The focused scoped release smoke is:

```bash
make check-fasim-gasal2-scoreinfo-scoped-release-smoke
```

It reruns the first8 no-probe lite and TFOsorted checks and then rechecks the
static scoped/full-goal boundaries. It is a MALAT1-like scoped smoke, not a
universal replacement smoke.

It uses
`--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32`, records
`result_contract = long_query_streaming_scoreinfo_gpu_two_contract_runtime_group32_experimental_v1`,
rejects probe env leakage, and requires all numeric probe telemetry to remain
zero. Fresh first8 is full lite-row/digest clean but slightly slower:

```text
schema=lite
rows=796
candidate_vs_baseline=0.990695x
tasks=1,824
two_contract_used=1,824
realpath_used=1,824
probe_positive_numeric_keys=0
```

The first8 TFOsorted no-probe gate is full 19-column row-set/digest clean,
but also slightly slower:

```text
schema=tfosorted
rows=796
candidate_vs_baseline=0.990699x
tasks=1,824
two_contract_used=1,824
realpath_used=1,824
probe_positive_numeric_keys=0
```

The optional first64 form is full lite-row/digest clean and slightly faster on
the current machine:

```text
schema=lite
rows=9741
candidate_vs_baseline=1.030868x
tasks=18,096
two_contract_used=18,096
realpath_used=18,096
gpu_scoreinfo_groups=319,280
probe_positive_numeric_keys=0
```

This is the clean runtime evidence for the scoped MALAT1-like two-contract
bridge. It is not a universal scoreInfo/preAlign replacement claim.

The optional first128 form is also full lite-row/digest clean:

```text
schema=lite
rows=22531
candidate_vs_baseline=1.043793x
tasks=40,128
two_contract_used=40,128
realpath_used=40,128
gpu_scoreinfo_groups=715,473
probe_positive_numeric_keys=0

first256:
  rows=42504
  candidate_vs_baseline=1.042764x
  tasks=80,640
  two_contract_used=80,640
  realpath_used=80,640
  gpu_scoreinfo_groups=1,434,844
  probe_positive_numeric_keys=0

full MALAT1:
  rows=98713
  digest=f080498ad8b9661100243e8eec89b6b54b566d7ed96fa5db7e268a8ce8513e0b
  baseline_wall_seconds=2616.446186
  candidate_wall_seconds=2521.276554
  candidate_vs_baseline=1.037747x
  tasks=200,400
  two_contract_used=200,400
  realpath_used=200,400
  gpu_minscore_used=200,400
  gpu_scoreinfo_groups=3,561,123
  two_contract_total_seconds=486.853900
  gpu_minscore_wall_seconds=159.007290
  realpath_extend_seconds=1143.153600
  realpath_extend_align_seconds=1137.801300

full MALAT1 TFOsorted:
  schema=tfosorted
  rows=98713
  digest=ac667f460cd1446bc5598fa163f7fc2755265bf56e6b82c105e672873c895ffc
  baseline_wall_seconds=2640.948210
  candidate_wall_seconds=2545.271840
  candidate_vs_baseline=1.037590x
  tasks=200,400
  two_contract_used=200,400
  realpath_used=200,400
  gpu_minscore_used=200,400
  gpu_scoreinfo_groups=3,561,123
  two_contract_total_seconds=486.866600
  gpu_minscore_wall_seconds=159.077360
  realpath_extend_seconds=1165.680900
  realpath_extend_align_seconds=1139.782800
  probe_positive_numeric_keys=0
```

### Accepted Top5-Only Product Scope

For a narrower top5-only completion claim, the scope must be intentionally
accepted as product behavior, not inferred from this milestone:

```text
top5-only output contract accepted
full-output non-equivalence accepted
long-query fallback policy accepted
default-off or opt-in runtime policy accepted
broader workload validation completed for that scoped contract
```

The current top5-only product-readiness checkpoint is:

```bash
make check-fasim-gasal2-top5-product-readiness
```

The current top5 broader workload validation checkpoint is:

```bash
make check-fasim-gasal2-top5-broader-validation
```

The current GASAL2 top5 recommended runtime checkpoint is:

```bash
make check-fasim-gasal2-top5-recommended-runtime
```

The top5 scoped completion candidate checkpoint is:

```bash
make check-fasim-gasal2-top5-scoped-completion-candidate
```

The focused top5 release smoke checkpoint is:

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

This is a contract smoke, not a performance claim.

Those gates record the top5-only product-readiness boundary and default-off
recommended invocation, but the full objective remains open unless the accepted
scope above is explicitly chosen and verified over the intended workloads.

### Long-Query Continuation

For MALAT1/NEAT1-like long-query continuation:

```text
different long-query architecture, not current selector/global-state tuning
or full-output/TFO equivalence proof over the claimed scope
scoreinfo_gasal2_active = 1 where the path is claimed
top5 score/stability/nt_score clean
GASAL2/exact-scoreInfo fallback = 0
GPU/GASAL2 total < CPU fallback
no endpoint/CIGAR/output authority unless separately proven
```

The already-tested lower-shared-memory streaming line is now a scoped
checkpoint, not an open-ended next step:

```text
lower-shared-memory streaming scoreInfo design: checkpointed but not broad completion
legacy-byte streaming scoreInfo: correctness clean, performance no-go
hot GPU minScore / realpath trust: MALAT1 scoped positive, modest speedup
fused minScore: no-go
two-contract bridge: MALAT1 scoped/research positive, default-off and digest-gated
selected-attempt CPU-align reduction: no-go for current selector
NEAT1 current execution shape: performance no-go
```

## Current Decision

The correct current decision is:

```text
short-query/H19 top5 scoreInfo/preAlign:
  milestone go

MEG3 grouped top5 wrapper:
  milestone go

long-query MALAT1/NEAT1:
  no real path

long-query next architecture:
  decision = next_architecture_no_go

post-selected-replay status:
  scoped milestone, not completion

full objective:
  not complete
```

Do not call `update_goal complete` for the full objective from the current
evidence.

## Gate

Focused gap gate:

```bash
make check-fasim-gasal2-scoreinfo-completion-gap
```

Current-state gate includes this gap checkpoint:

```bash
make check-fasim-gasal2-scoreinfo-current-state
```

The scoped feasibility milestone gate is:

```bash
make check-fasim-gasal2-scoreinfo-scoped-milestone
```

The Full Goal Decision Audit checkpoint is:

```bash
make check-fasim-gasal2-full-goal-decision
```

The long-query next-architecture decision checkpoint is:

```bash
make check-fasim-gasal2-long-query-next-architecture-decision
```

The historical lower-shared-memory long-query design checkpoint is:

```bash
make check-fasim-long-query-streaming-scoreinfo-design
```

The fused minScore implementation candidate inside that design is a no-go
boundary:

```bash
make check-fasim-long-query-streaming-scoreinfo-fused-minscore-design
```

It showed that legacy calc-score minScore and byte-profile scoreInfo are
separate contracts. The two-contract bridge is the current scoped bridge
checkpoint:

```bash
make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design
```

The segmented score-prepass state-machine consumer is also stopped as a real
path candidate:

```bash
make check-fasim-gasal2-score-prepass-state-machine-stop
```

It is correctness-clean as a scaffold, but current trust/traceback evidence
shows that it does not reduce CPU traceback work and that selected-segment
traceback is not equivalent to full-query `aligner.Align()`.

That bridge has MALAT1 scoped evidence, but it still needs broader workload
coverage, selected-attempt/output equivalence, fallback-free operation, and
performance before it can move the full objective.

The GASAL2 attempt-consumer shadow is now a scoped milestone, not a completion
path:

```text
FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1
NEAT1 first64:
  decision = attempt_consumer_shadow_no_cpu_align_reduction_no_go
  digest clean
  triplex_mismatches = 0
  missing_triplexes = 0
  extra_triplexes = 0
  attempts = 211,976
  selected_attempts = 140,087
  cpu_align_attempts = 140,087
  realpath_extend_align_attempts = 140,087
  candidate_vs_baseline = 0.148434x
```

It proves a correctness-clean diagnostic scaffold for attempt-level replay, but
does not reduce CPU `aligner.Align()` attempts and must not be promoted as a
real path.

The next broad attempt is an emission-only scoreInfo consumer shadow:
FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1. It must use GASAL2 score/end to
choose emitted attempts and CPU-align only those emitted attempts. It is a
go only if NEAT1 first64 is triplex/digest clean and CPU align attempts are
lower than the realpath reference.
