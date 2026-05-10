# CUDA ordered segmented shadow gate cleanup

Date: 2026-05-10

Base: `cuda-gpu-exact-frontier-replay-contract`

This pass inventories the existing ordered segmented / exact frontier replay
telemetry and stops short of adding a new activation gate. It is docs-only: no
new GPU replay kernel, no real GPU authority path, no default
`ordered_segmented_v3`, and no behavior change.

## Finding

The currently named exact frontier replay env is not a clean shadow gate:

```text
LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY=1
```

When the experimental initial reducer is enabled, that scaffold can report
`benchmark.sim_initial_replay_authority=gpu_real`. It is therefore not suitable
as the contract shadow gate.

The existing ordered segmented shadow env is diagnostic, but it is not an
independent default-path shadow gate:

```text
LONGTARGET_SIM_CUDA_INITIAL_ORDERED_SEGMENTED_V3_SHADOW=1
```

It compares `ordered_segmented_v3` reduce output against CPU oracle replay only
after the experimental `reduceCandidates` path has produced candidate states.
Using it as the new clean shadow-only gate would still couple the gate to the
experimental reducer path.

The existing default-path shadow-only shape is closer to:

```text
LONGTARGET_SIM_CUDA_INITIAL_FRONTIER_TRANSDUCER_SHADOW=1
```

That path runs after CPU replay and keeps CPU authority, but it currently
reports one aggregate mismatch counter rather than the full contract mismatch
set.

## Inventory

| Concept | Existing key / location | Action |
| --- | --- | --- |
| shadow requested / active | `LONGTARGET_SIM_CUDA_INITIAL_ORDERED_SEGMENTED_V3_SHADOW`, `sim.h:3556`; CUDA runtime mirror at `cuda/sim_scan_cuda.cu:266` | Do not reuse as the clean default-path gate; it is tied to ordered segmented reduce output. |
| shadow authority | `benchmark.sim_initial_replay_authority`, `longtarget.cpp:1752` | Keep. `EXACT_FRONTIER_REPLAY=1` can report `gpu_real`, so it must not define shadow authority. |
| disabled reason | none for ordered replay shadow | Missing. A future gate needs explicit `disabled_reason`. |
| ordered summary input | `SimScanCudaInitialRunSummary`, `cuda/sim_scan_cuda.h:24` | Present. |
| frontier mismatch | `benchmark.sim_initial_ordered_segmented_v3_shadow_frontier_mismatches`, `longtarget.cpp:2736` | Present for `ordered_segmented_v3` compare. |
| runningMin mismatch | `benchmark.sim_initial_ordered_segmented_v3_shadow_running_min_mismatches`, `longtarget.cpp:2738` | Present for `ordered_segmented_v3` compare. |
| safe-store mismatch | `benchmark.sim_initial_ordered_segmented_v3_shadow_safe_store_mismatches`, `longtarget.cpp:2740` | Present as set equality, not named digest/epoch mismatch. |
| candidate count mismatch | `benchmark.sim_initial_ordered_segmented_v3_shadow_candidate_count_mismatches`, `longtarget.cpp:2742` | Present for `ordered_segmented_v3` compare. |
| candidate value mismatch | `benchmark.sim_initial_ordered_segmented_v3_shadow_candidate_value_mismatches`, `longtarget.cpp:2744` | Present for `ordered_segmented_v3` compare. |
| frontier transducer aggregate mismatch | `benchmark.sim_initial_frontier_transducer_shadow_mismatches`, `longtarget.cpp:2732` | Present, but too coarse for the full contract. |
| first-max / tie mismatch | no GPU-vs-CPU mismatch counter | Missing; do not fake zero. |
| min-candidate mismatch | no GPU replay shadow counter | Missing; do not fake zero. |
| ordered candidate digest | transducer digest helper exists at `sim.h:15521` | Missing as benchmark field. |
| unordered candidate digest | no exact replay shadow counter | Missing. |
| safe-store digest / epoch mismatch | stale epoch rejection exists for other handoff/scheduler paths | Missing as exact replay shadow mismatch. |
| chunk-boundary mismatch | reduce chunk stats exist as `benchmark.sim_initial_reduce_chunks_*` | Missing as a shadow compare counter. |

## Existing counter mapping

The ordered segmented v3 counters can be mapped into a future clean shadow
report only as final-boundary comparison fields:

```text
frontier_mismatches
running_min_mismatches
safe_store_mismatches
candidate_count_mismatches
candidate_value_mismatches
```

They do not cover first-max/tie, min-candidate, ordered/unordered candidate
digest, safe-store digest/epoch, or chunk-boundary mismatches. They also do not
define a shadow-only activation model by themselves.

## Stop reason

This PR does not add:

```text
LONGTARGET_SIM_CUDA_INITIAL_ORDERED_REPLAY_SHADOW_ONLY=1
```

Adding that env cleanly would require choosing which existing mechanism owns
the shadow:

1. Reusing `ORDERED_SEGMENTED_V3_SHADOW` keeps the gate tied to the experimental
   ordered segmented reducer path.
2. Reusing `FRONTIER_TRANSDUCER_SHADOW` keeps CPU authority but exposes only an
   aggregate mismatch counter.
3. Reusing `EXACT_FRONTIER_REPLAY` is not acceptable because it can report
   `gpu_real`.

That is a design choice, not a benchmark-field alias. The next code PR should
make the gate explicit rather than mixing these paths.

## Required next gate shape

A future shadow-only gate should report:

```text
benchmark.sim_initial_ordered_replay_shadow_requested
benchmark.sim_initial_ordered_replay_shadow_active
benchmark.sim_initial_ordered_replay_shadow_authority=cpu
benchmark.sim_initial_ordered_replay_shadow_disabled_reason
benchmark.sim_initial_ordered_replay_shadow_calls
benchmark.sim_initial_ordered_replay_shadow_chunks
```

If the experimental reducer path would be required, it should report
`active=0` with `disabled_reason=unsupported_path`, not silently route through
`gpu_real`.

## Recommendation

Do not implement GPU replay next. The next PR should be a narrow shadow-stub or
counter gap-fill PR that chooses one of these paths explicitly:

| Next PR | Purpose |
| --- | --- |
| first-max/tie counter gap-fill | Define GPU-vs-CPU comparison for score/end tie behavior. |
| digest/epoch counter gap-fill | Split aggregate/set equality into ordered digest, unordered digest, safe-store digest, and safe-store epoch counters. |
| shadow-only gate stub | Add requested/active/disabled_reason/authority telemetry without running a new kernel. |
| minimal one-chunk CUDA replay shadow | Only after the missing counters are explicit and authority remains CPU. |

Default behavior, CPU replay authority, safe-store behavior, locate/region
dispatch, and planner authority remain unchanged.
