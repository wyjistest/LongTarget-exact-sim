# CUDA Exact Frontier Transducer Feasibility

Base branch:

```text
cuda-region-kernel-cell-work-profile
```

Base commit:

```text
0610446
```

This is a research/diagnostic PR. It does not implement production replay,
change CPU authority, activate the clean gate, change replay semantics, feed
transducer output into production, or route through `ordered_segmented_v3`,
`EXACT_FRONTIER_REPLAY`, or `gpu_real`.

## Goal

The question is not whether an observed replay trace can be compressed after
the exact state is already known. The 10x architecture question is stricter:

```text
Can an ordered chunk be represented as a reusable transform:

  T_chunk(state_in) -> state_out

without replaying that chunk from the full prior candidate/safe-store state?
```

This PR separates two cases:

```text
observed delta:
  replay with known state_in, then record a compact boundary-state log.
  Useful for churn/compression analysis.
  Not evidence for a 10x transducer architecture.

independent transform:
  build T_chunk without full prior state, then compose transforms.
  This is the required gate for continuing the 10x architecture line.
```

## Telemetry

Default-off env:

```text
LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_TRANSDUCER_FEASIBILITY=1
```

Optional selectors:

```text
LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_TRANSDUCER_FEASIBILITY_REQUEST_INDEX=<idx>
LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_TRANSDUCER_FEASIBILITY_CHUNK_SIZE=<n>
```

The diagnostic emits:

```text
sim_initial_exact_frontier_transducer_feas_enabled
sim_initial_exact_frontier_transducer_feas_request_index
sim_initial_exact_frontier_transducer_feas_chunk_size
sim_initial_exact_frontier_transducer_feas_chunks
sim_initial_exact_frontier_transducer_feas_raw_summaries
sim_initial_exact_frontier_transducer_feas_raw_bytes
sim_initial_exact_frontier_transducer_feas_transition_entries
sim_initial_exact_frontier_transducer_feas_transition_bytes
sim_initial_exact_frontier_transducer_feas_compression_ratio
sim_initial_exact_frontier_transducer_feas_build_seconds
sim_initial_exact_frontier_transducer_feas_compose_seconds
sim_initial_exact_frontier_transducer_feas_compare_seconds
sim_initial_exact_frontier_transducer_feas_build_requires_prior_state
sim_initial_exact_frontier_transducer_feas_state_dependency_bytes
sim_initial_exact_frontier_transducer_feas_guard_count
sim_initial_exact_frontier_transducer_feas_observed_delta_only
sim_initial_exact_frontier_transducer_feas_independent_chunk_build_supported
sim_initial_exact_frontier_transducer_feas_build_order_randomized
sim_initial_exact_frontier_transducer_feas_build_order_mismatches
sim_initial_exact_frontier_transducer_feas_candidate_mismatches
sim_initial_exact_frontier_transducer_feas_ordered_digest_mismatches
sim_initial_exact_frontier_transducer_feas_unordered_digest_mismatches
sim_initial_exact_frontier_transducer_feas_min_candidate_mismatches
sim_initial_exact_frontier_transducer_feas_first_max_tie_mismatches
sim_initial_exact_frontier_transducer_feas_safe_store_digest_mismatches
sim_initial_exact_frontier_transducer_feas_total_mismatches
sim_initial_exact_frontier_transducer_feas_left_fold_compose_seconds
sim_initial_exact_frontier_transducer_feas_tree_compose_seconds
sim_initial_exact_frontier_transducer_feas_composition_grouping_mismatches
sim_initial_exact_frontier_transducer_feas_compose_requires_replay
```

The current diagnostic uses the existing exact frontier transducer shadow
backend. That backend produces an observed trace result from known incoming
state. It does not build independent reusable chunk transforms.

## Runs

All runs used the recommended safe-store GPU best path:

```bash
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_RESIDENT_SOURCE=1
LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_GPU_PRECOMBINE_PRUNE=1
LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_TRANSDUCER_FEASIBILITY=1
LONGTARGET_ENABLE_SIM_CUDA=1
LONGTARGET_ENABLE_SIM_CUDA_REGION=1
LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1
EXPECTED_SIM_INITIAL_BACKEND=cuda
EXPECTED_SIM_REGION_BACKEND=cuda
EXPECTED_SIM_LOCATE_MODE=safe_workset
TARGET=$PWD/longtarget_cuda
./scripts/run_sample_exactness_cuda.sh
```

Logs:

```text
.tmp/cuda_exact_frontier_transducer_feasibility_4096/stderr.log
.tmp/cuda_exact_frontier_transducer_feasibility_request4_16384/stderr.log
```

A 65,536-summary sanity run on request 4 was attempted but stopped before
telemetry because the diagnostic had already failed the build-independence gate
and the replay path remained excessively slow.

## Results

| Field | request 47 / 4K | request 4 / 16K |
| --- | ---: | ---: |
| raw summaries | 1,091,537 | 116,515 |
| raw bytes | 34,929,184 | 3,728,480 |
| chunks | 267 | 8 |
| transition entries | 13,350 | 400 |
| transition bytes | 505,164 | 15,136 |
| compression ratio | 0.0144625 | 0.00405956 |
| build seconds | 96.9109 | 40.1639 |
| compose seconds | 96.9109 | 40.1639 |
| compare seconds | 0.0530679 | 0.00319987 |
| candidate mismatches | 0 | 0 |
| ordered digest mismatches | 0 | 0 |
| unordered digest mismatches | 0 | 0 |
| min-candidate mismatches | 0 | 0 |
| first-max/tie mismatches | 0 | 0 |
| safe-store digest mismatches | 0 | 0 |
| build requires prior state | 1 | 1 |
| state dependency bytes | 1,804 | 1,804 |
| observed delta only | 1 | 1 |
| independent chunk build supported | 0 | 0 |
| build order randomized | 0 | 0 |
| compose requires replay | 1 | 1 |
| total mismatches / no-go flag | 1 | 1 |

The observed boundary-state log is compact by bytes. For request 47 at chunk
size 4K, the observed log is about `1.45%` of raw summary bytes. That is useful
evidence that the executed trace has compressible structure.

However, this is not a reusable transform:

```text
build_requires_prior_state = 1
observed_delta_only = 1
independent_chunk_build_supported = 0
compose_requires_replay = 1
```

Composition is not cheaper than replay in the current diagnostic because the
"compose" step is still the replay path. Request 47 spends `96.9109s` in the
build/compose replay, pushing the full sample to `total_seconds=110.387`.

## Go / No-Go

Strong go requires:

```text
total_mismatches = 0
transition_bytes <= 10% raw_bytes
compose_seconds << sequential replay time
independent_chunk_build_supported = 1
build_requires_prior_state = 0
```

This PR does not meet that bar.

Weak go allows exact and compressed observed deltas, but only if the result is
clearly framed as not validating the 10x path. The observed delta is exact and
compact, but runtime is high and composition requires replay, so even the weak
signal is useful only as churn/compression evidence.

No-go conditions hit:

```text
build_requires_prior_state = 1
observed_delta_only = 1
independent_chunk_build_supported = 0
compose_requires_replay = 1
compose_seconds ~= replay/build seconds
```

## Conclusion

Do not continue the 10x architecture line as an engineering implementation
track from this evidence.

Current evidence supports this narrower statement:

```text
observed replay traces can be compactly summarized after replay.
```

It does not support the required 10x statement:

```text
ordered chunks can be independently built into reusable exact transforms.
```

The 10x architecture research should only continue if the next proposal changes
the core representation so that independent chunk construction is plausible.
Continuing to GPU-ize the current replay/shadow path is not justified: it is
exact-clean for the measured fields, but it is observed-delta-only, requires
prior state, and is much too slow.

Recommended next direction:

```text
pause exact ordered replay transducer implementation
keep this as churn/compression evidence
return to region launch/per-call overhead or calc_score side lane
```

If a future design can set:

```text
independent_chunk_build_supported = 1
build_requires_prior_state = 0
compose_requires_replay = 0
```

then the 10x transducer research can be reopened.
