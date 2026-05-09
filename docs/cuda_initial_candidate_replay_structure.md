# CUDA initial candidate replay structure

Date: 2026-05-09

Base: `cuda-initial-context-apply-decomposition`

This pass characterizes the existing initial context-apply candidate replay
loop. It adds telemetry only. It does not skip candidate summaries, change
candidate replay order, change `runningMin` / floor semantics, change
first-max / tie behavior, change safe-store update/prune/upload behavior,
change dispatch, or change output behavior.

## Question

The previous context-apply decomposition showed that the covered initial
context apply path is almost entirely per-summary candidate replay. This pass
asks whether those summaries are mostly rejected after comparison, mostly
mutate candidate state, or collapse to a tiny final candidate frontier.

## New telemetry

The new fields are:

```text
benchmark.sim_initial_candidate_replay_summaries
benchmark.sim_initial_candidate_replay_processed
benchmark.sim_initial_candidate_replay_accepted
benchmark.sim_initial_candidate_replay_rejected_below_floor
benchmark.sim_initial_candidate_replay_insertions
benchmark.sim_initial_candidate_replay_replacements
benchmark.sim_initial_candidate_replay_erasures
benchmark.sim_initial_candidate_replay_tie_updates
benchmark.sim_initial_candidate_replay_first_max_updates
benchmark.sim_initial_candidate_replay_final_candidates
benchmark.sim_initial_candidate_replay_survival_ratio
```

`accepted` means the replayed summary changed the candidate slot, including a
new insertion, a full-frontier replacement, a score/end update, or a bounds
update. `first_max_updates` counts insertions, replacements, and score/end
updates. `rejected_below_floor` remains zero for the covered default summary
replay because the path has no local floor rejection before replay. The pass did
not add per-summary compare/mutation timers because wrapping 4.7M to 44.8M
summaries with `chrono` would materially perturb the path being measured.

## Commands

Small benchmark path:

```text
make check-benchmark-telemetry
```

Sample region-locate exactness path:

```text
LONGTARGET_BENCHMARK=1 \
LONGTARGET_ENABLE_SIM_CUDA=1 \
LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
EXPECTED_SIM_INITIAL_BACKEND=cuda \
EXPECTED_SIM_REGION_BACKEND=cuda \
EXPECTED_SIM_LOCATE_MODE=safe_workset \
OUTPUT_SUBDIR=cuda_initial_candidate_replay_structure_sample \
TARGET=$(pwd)/longtarget_cuda \
./scripts/run_sample_exactness_cuda.sh
```

Both runs passed exactness / telemetry gates.

## Results

| Field | benchmark | sample |
| --- | ---: | ---: |
| `candidate_apply_seconds` | 0.187481 | 1.70861 |
| `processed_summaries` | 4,691,334 | 44,777,038 |
| `accepted_updates` | 4,613,123 | 44,395,027 |
| `rejected_below_floor` | 0 | 0 |
| `insertions` | 3,450 | 2,400 |
| `replacements` | 3,889,333 | 40,318,731 |
| `erasures` | 3,889,333 | 40,318,731 |
| `tie_updates` | 0 | 0 |
| `first_max_updates` | 4,005,536 | 41,581,067 |
| `final_candidates` | 3,450 | 2,400 |
| `survival_ratio` | 0.000735399 | 0.0000535989 |
| `compare_seconds` | not instrumented | not instrumented |
| `mutation_seconds` | not instrumented | not instrumented |

Derived shape:

| workload | accepted / processed | first-max / processed | replacements / processed |
| --- | ---: | ---: | ---: |
| benchmark | 98.33% | 85.39% | 82.91% |
| sample | 99.15% | 92.86% | 90.04% |

## Interpretation

The default initial candidate replay path is not a rejection-heavy or no-op
heavy path under these workloads. On the sample path, `44,395,027` of
`44,777,038` processed summaries changed candidate state. Only `2,400` final
candidates survive, but the intermediate replay is highly mutating and heavily
replacement-driven.

The covered path does not expose a local rejected-below-floor prefilter target:
`rejected_below_floor=0` because the default summary replay applies every
summary and refreshes `runningMin` after replay. Tie updates are also not
material in the covered path.

The main structural signal is churn. Sample replay performs `40,318,731`
frontier replacements/erasures while ending with only `2,400` candidates. That
does not justify a host no-op skip or rejected-below-floor skip. It suggests any
future win needs a deeper exact replay structure, such as a default-off
GPU-resident ordered frontier replay shadow or a candidate container churn
shadow, before attempting a real optimization.

## Answers

| question | answer |
| --- | --- |
| Are most summaries rejected after comparison, or do they mutate candidate state? | They mostly mutate state: `99.15%` accepted on sample and `98.33%` on benchmark. |
| Is candidate replay dominated by comparisons or container mutation? | This pass does not safely time compare vs mutation. The counters show heavy mutation/replacement churn, not a rejection-heavy shape. |
| Are tie/first-max updates material? | Tie updates are zero in covered runs. First-max/score-end updates are material: `41,581,067` on sample. |
| Is there an exact-safe shadow opportunity? | Not a rejected-below-floor or no-op skip. The evidence points to candidate container churn shadow or GPU-resident ordered replay shadow. |
| Does this suggest a local host optimization? | Not yet. Host skip/filter work lacks evidence; a future PR should remain shadow/diagnostic unless it can prove exact replay structure savings. |

## Recommendation

Do not implement a candidate no-op skip, rejected-below-floor prefilter, or
host replay shortcut from this data. The covered workloads show high mutation
and replacement rates. The next useful PR is either:

```text
candidate container churn shadow
GPU-resident exact ordered frontier replay shadow
```

The latter is more likely to matter if the goal is to reduce the per-summary
authoritative replay cost without changing exact replay semantics.
