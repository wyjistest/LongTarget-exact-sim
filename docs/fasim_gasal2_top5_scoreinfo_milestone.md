# Fasim GASAL2 Top5 ScoreInfo Milestone

This milestone covers the short-query / H19 formal GASAL2 top5
scoreInfo/preAlign artifact path.

## Milestone

The default-off formal runner preset is:

```text
--gasal2-top5-column-pruned-scoreinfo
```

The preset is the reviewed surface for this milestone. It expands to the
current short-query top5 artifact stack:

```text
FASIM_TOP5_GASAL2_GPU_SCOREINFO=1
FASIM_TOP5_GASAL2_PHASE_TIMING=1
FASIM_ALIGN_GASAL2_STAGED_FIRST_PRUNE=1
FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=64
FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE=1
FASIM_PREALIGN_CUDA_MAX_TASKS=16384
FASIM_EXACT_COLUMN_SCOREINFO_GPU=1
FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=512
FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT=1
FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT=1
FASIM_OUTPUT_TOPK_LITE=5
```

The verified contract is top5 artifact equivalence with active GASAL2 and
active exact scoreInfo GPU coverage. It is not a full-output contract.

## Verified Result

Fresh chr21+chr22 characterization:

```bash
TARGET_PRESETS=chr21_chr22 \
REPEATS=1 \
BUILD_BIN=0 \
WORK=.tmp/characterize_fasim_gasal2_column_pruned_preset_top5_matrix_chr21_chr22_active \
BIN=.tmp/fasim_longtarget_gasal2_direct \
bash scripts/characterize_fasim_gasal2_column_pruned_preset_top5_matrix.sh
```

Result:

```text
target_preset = chr21_chr22
decision = top5_artifact_go
runs = 1
artifact_checked_runs = 1/1
top5_clean_runs = 1/1
active_path_runs = 1/1
zero_legacy_score_runs = 1/1
zero_overflow_runs = 1/1
zero_fallback_runs = 1/1
zero_gasal2_fallback_runs = 1/1
zero_length_guard_fallback_runs = 1/1
positive_gasal2_request_runs = 1/1
positive_exact_scoreinfo_task_runs = 1/1

CPU worker wall sum = 4565.987188s
formal preset worker wall sum = 113.810705s
speedup vs CPU worker wall sum = 40.119136x
speedup vs CPU max worker wall = 40.443813x

GASAL2 requests = 43,637,966
GASAL2 traceback requests = 13,701,121
exact scoreInfo GPU tasks = 778,848
GASAL2 fallbacks = 0
length guard fallbacks = 0
exact scoreInfo overflow/fallback batches = 0 / 0
legacy score GPU requests = 0
exact scoreInfo GPU batches = 49
```

The checked top5 artifact modes are:

```text
score
stability
nt_score
```

All three modes match the CPU/full top5 artifact payload for this workload.

### Tiny-Region Grouping Evidence

MEG3 full is a many-record tiny-region shape. Without runner grouping, the
formal GASAL2 candidate is dominated by one-record shard overhead. With
complete-record grouping:

```bash
TARGET_PRESETS=.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743-DNAseq.fa \
REPEATS=1 \
BUILD_BIN=0 \
WORK=.tmp/characterize_fasim_gasal2_column_pruned_preset_top5_matrix_meg3_full_formal_group32 \
BIN=.tmp/fasim_longtarget_gasal2_direct \
RNA=.tmp/Fasim-LongTarget/example/MEG3/MEG3-ENST00000451743.fa \
WORKERS=2 \
GPU_IDS=0,1 \
GROUP_TARGET_RECORDS=32 \
bash scripts/characterize_fasim_gasal2_column_pruned_preset_top5_matrix.sh
```

Result:

```text
target records = 532
group_target_records = 32
grouped shards = 17
decision = top5_artifact_go
top5_clean_runs = 1/1
active_path_runs = 1/1
fallback/overflow = 0/0

CPU worker wall sum = 50.592440s
formal preset worker wall sum = 26.088332s
speedup vs CPU worker wall sum = 1.939275x
speedup vs CPU max worker wall = 1.833061x

GASAL2 requests = 1,034,708
GASAL2 traceback requests = 393,847
exact scoreInfo GPU tasks = 25,536
```

The grouped CPU top5 artifact payload was also checked against the earlier
ungrouped MEG3 CPU top5 artifact payload. They match, so grouping is workload
shaping, not a top5 semantic change.

### Focused Release Smoke

The focused release smoke for this milestone is:

```bash
make check-fasim-gasal2-top5-release-smoke
```

Latest local smoke boundary:

```text
formal_preset_example = meg3_first32
formal_preset_topk_artifact_match = true
cap32_nt_score_artifact_match = false
formal_preset_gasal2_requests = 63,035
formal_preset_exact_scoreinfo_gpu_tasks = 1,536
formal_preset_speedup_vs_cpu_worker_wall_sum < 1.0
```

This smoke proves that the preset activates and matches the scoped top5
artifact contract on the tiny example. It is a contract smoke, not a
performance claim.

## Scope

This milestone establishes:

```text
short-query H19/chr21+chr22:
  formal GASAL2 top5 scoreInfo/preAlign artifact path is active-path clean
  GASAL2 score/traceback requests are non-zero
  exact scoreInfo GPU tasks are non-zero
  GASAL2 fallback is zero
  exact scoreInfo GPU overflow/fallback is zero
  topK-lite rank-observe telemetry is enabled, non-empty, and free of unknown rows
  top5 artifact payload matches CPU/full top5 artifact
short-query MEG3 tiny-region:
  complete-record grouping can make the same formal top5 artifact path practical
  grouping preserves the checked top5 payload
```

Accepted evidence for this milestone is:

```text
active_path_runs = runs
positive_gasal2_request_runs = runs
positive_exact_scoreinfo_task_runs = runs
zero_legacy_score_runs = runs
zero_gasal2_fallback_runs = runs
zero_length_guard_fallback_runs = runs
zero_overflow_runs = runs
zero_fallback_runs = runs
topK-lite rank-observe telemetry is enabled, non-empty, and free of unknown rows
top5 score/stability/nt_score payloads match CPU/full top5 artifacts
```

This milestone does not establish:

```text
not full lite-output equivalence
not full scoreInfo/preAlign universal replacement
not exact legacy scoreInfo equivalence
not an `aligner.Align()` replacement
not GPU endpoint/CIGAR/traceback authority
```

MALAT1/NEAT1 long-query GASAL2 path remains guarded out by the current verified
query-length boundary. Those rows can be top5-clean via CPU fallback, but they
are not GASAL2-active under this milestone.

The segmented GASAL2 long-query probes are documented no-go in the long-query
boundary. The direct segmented traceback shadow is correctness-clean but
performance no-go, and the pruned segmented traceback shadow is
correctness-clean but performance no-go. The score-prepass batched shadow is
stage-only: it has no endpoint, CIGAR, traceback, candidate state, output, or
digest authority. CPU replay with no-last remains marginal and is not enough to
justify a long-query real path.

The next expansion point is not another claim over this milestone. To move the
larger goal forward, a follow-up has to either extend GASAL2/exact-scoreInfo
coverage beyond the current `GASAL2_MAX_QUERY_LEN=2812` short-query boundary or
define an explicit top5-only output contract that Fasim can use intentionally.

## Gates

Focused gates:

```bash
make check-fasim-gasal2-top5-scoreinfo-milestone
make check-fasim-gasal2-top5-scoreinfo-milestone-result
make check-fasim-gasal2-top5-output-contract
make check-fasim-gasal2-top5-activation-contract
make check-fasim-gasal2-top5-release-smoke
make check-fasim-gasal2-long-query-boundary
make check-fasim-gasal2-long-query-segmented-pruned-traceback-shadow
make check-fasim-gasal2-long-query-segmented-replay-no-last
make check-fasim-gasal2-column-pruned-preset-top5-matrix
make check-fasim-exact-scoreinfo-gpu-examples-gate
make check-fasim-sharded-gasal2-top5-prune-runner
```

Formal gate:

```bash
make check-fasim-gasal2-top5-formal-gate
```

The formal gate requires the bounded matrix aggregate to report
`active_path_runs`, so top5-clean rows must also prove active GASAL2/exact
scoreInfo GPU coverage.

To verify the recorded local chr21+chr22 result artifact as well as the static
milestone text, run:

```bash
make check-fasim-gasal2-top5-scoreinfo-milestone-result
```

To verify the recorded local MEG3 complete-record grouped result artifact, run:

```bash
make check-fasim-gasal2-top5-scoreinfo-meg3-grouped-result
```

To verify the same MEG3 grouped path through the formal topK-lite wrapper, run:

```bash
make check-fasim-gasal2-top5-wrapper-meg3-grouped-result
```
