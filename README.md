# LongTarget: Predicting long noncoding RNAs' epigenetic target genes

## Contents

- [Overview](#overview)
- [Repo Contents](#repo-contents)
- [System Requirements](#system-requirements)
- [Installation Guide](#installation-guide)
    + [Compilation](#compilation)
    + [Running](#running)
    + [Help information](#help-information)
    + [Time consumption](#time-consumption)
- [Demo](#demo)
    + [Inputs and their formats](#inputs-and-their-formats)
    + [Results](#results)
    + [Example datasets](#example-datasets)
 - [Instructions for use](#instructions-for-use)
    + [How to run LongTarget on your data](#how-to-run-longtarget-on-your-data)
    + [Bug reports](#bug-reports)
- [Other codes](#other-codes)
- [License](./LICENSE)
- [Citation](#citation)

# Overview
Since the pioneering genome-wide discovery of mouse lncRNAs in the FANTOM consortium, experimental studies have identified abundant lncRNAs in humans, mice, and other mammals. Many lncRNAs can bind to both DNA sequences and DNA- and histone-modifying enzymes, thus recruiting these enzymes to specific genomic sites to epigenetically regulate the expression of genes at these sites. Genomic imprinting is a specific kind of epigeneticregulation.

LongTarget was developed to predict one or many lncRNA’s DNA binding motifs and binding sites in one or many genome regions based on all known ncRNA/DNA base pairing rules (Hoogsteen and reverse Hoogsteen base pairing rules). LongTarget consists of a few C/C++ programs, and is distributed under the AGPLv3 license. It can be used as a standalone program, and we have also integrated it into the lncRNA database LongMan at the website http://lncRNA.smu.edu.cn, making it a web service. Our use of LongTarget indicates that it can satisfactorily predict lncRNAs’ DNA binding motifs and binding sites, and multiple pipelines have been developed to seamless bridge database search and lncRNA/DNA binding prediction.

# Repo Contents
- [longtarget.cpp](./longtarget.cpp): The main program for generating the executable "LongTarget".
- [rules.h](./rules.h): Base-pairing rules and codes for handling these rules.
- [sim.h](./sim.h):   The SIM program for local alignment.
- [stats.h](./stats.h): Michael Farrar's code (with SSE2) for local alignment.
- [H19.fa](./H19.fa):  A sample lncRNA sequence.
- [testDNA.fa](./testDNA.fa): A sample DNA sequence.

# System Requirements
- OS: Linux, we compile and run the LongTarget under CentOS 6.0.
- System software:	g++.
- RAM: 16G or above, depending on the number of lncRNAs and length of genome region.
- CPU: 4 cores or above, depending on the number of lncRNAs and length of genome region.
- To use our web service, Google Chrome and Mozilla Firefox are recommended, because functions were tested under these browsers.

# Installation Guide
## Compilation
Typically, this command will generate an executable LongTarget program: 

```
g++ longtarget.cpp -O -msse2 -o LongTarget.
```

This exact-SIM branch also ships a small `Makefile` for deterministic CPU builds and exactness checks:

```
make build
make build-avx2
make check-sample
make check-smoke
make check-sample-row
make check-sample-wavefront
make oracle-matrix
make check-matrix
```

Optional CUDA builds can accelerate the exact threshold (`calc_score_with_workspace()`) while keeping oracle outputs byte-identical. CUDA stays opt-in and is enabled at runtime:

```
make build-cuda
make check-smoke-cuda
LONGTARGET_ENABLE_CUDA=1 TARGET=$PWD/longtarget_cuda ./scripts/run_sample_exactness.sh
```

Optional CUDA builds can also accelerate SIM candidate scanning (both initial scan and traceback update rescans). These toggles are opt-in at runtime:

- `LONGTARGET_ENABLE_SIM_CUDA=1`: CUDA initial scan (candidate enumeration)
- `LONGTARGET_ENABLE_SIM_CUDA_INITIAL_REDUCE=1`: experimental GPU-side candidate reduction for CUDA initial scan; default stays off because the exact-safe default path still replays row-run summaries on the host, while the current v1 GPU reducer replays those summaries serially on-device and can regress badly on large samples
- `LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND=legacy|hash|segmented`: select the experimental initial-reduce backend; `legacy` keeps the original single-request ordered replay path, `hash` routes single-request initial reduce through the shared true-batch/hash pipeline, and `segmented` keeps the exact legacy top-K replay while switching the safe-store rebuild to a grouped segmented reduce (default: `legacy`; compatibility alias: `LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE=1`)
- `LONGTARGET_ENABLE_SIM_CUDA_REGION=1`: CUDA traceback update rescan (exact / hybrid)
- `LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1`: enable the post-traceback update accelerator; the default exact-safe mainline now uses `safe_workset`, while `exact` remains available as a force-on fallback/debug mode
- `LONGTARGET_SIM_CUDA_LOCATE_MODE=safe_workset`: exact-safe default when locate acceleration is enabled; skips the old locate-first reverse-DP expansion, derives a sparse rescan workset from the materialized traceback script plus the persisted safe candidate-state store, and falls back to exact locate/update whenever the workset is not provably safe
- `LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_DIR=/abs/path`: best-effort dump the default exact-safe summary-handoff host-merge inputs/expected outputs (`meta.json`, summaries, context candidates, pre/post-prune safe-store states) so `store_materialize` / `store_prune` can be replayed offline without rerunning the full CUDA initial scan
- `LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_MAX_CASES=N`: optional cap on how many host-merge full-payload corpus cases a run will dump before capture stops (default: unlimited; when `LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_CASE_LIST` is set, the cap applies to selected payload cases rather than raw case index)
- `LONGTARGET_SIM_INITIAL_HOST_MERGE_MANIFEST_PATH=/abs/path.tsv`: append a lightweight per-case manifest row (`case_id`, counts, `prune_ratio`, lengths, mirror flag) without writing the heavy payload files; the file is now created eagerly with a header at run start so interrupted real-shard censuses still leave a usable partial manifest
- `LONGTARGET_SIM_INITIAL_HOST_MERGE_HEARTBEAT_SECONDS=N`: emit manifest-only census heartbeat lines to stderr every `N` seconds (default: `10`; `0` disables time-based heartbeat)
- `LONGTARGET_SIM_INITIAL_HOST_MERGE_HEARTBEAT_CASES=N`: emit an immediate manifest-only census heartbeat after every `N` appended cases (default: `16`; `0` disables case-based heartbeat)
- `LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_CASE_LIST=/abs/path.tsv`: optional TSV of `case_id` values to full-dump; intended for a second pass after manifest census selects a small representative set
- `LONGTARGET_ENABLE_SIM_CUDA_SAFE_WINDOW=0`: disable the GPU safe-window planner for exact-safe `safe_workset` locate; by default it is enabled whenever the locate path has a mirrored GPU safe-store to plan against
- `LONGTARGET_SIM_CUDA_SAFE_WINDOW_MAX_COUNT=N`: maximum number of safe windows the GPU planner may materialize before it reports overflow and falls back to the builder/exact path (default: 128)
- `LONGTARGET_SIM_CUDA_SAFE_WINDOW_PLANNER=dense|sparse_v1`: choose the GPU safe-window planner backend; `dense` keeps the original per-row single-range planner (default), while `sparse_v1` preserves multiple disjoint row-local islands before execution coarsening
- `LONGTARGET_SIM_CUDA_SAFE_WINDOW_COMPARE_BUILDER=1`: keep the older planner-vs-builder compare path for exact-safe locate debugging; by default a usable GPU safe-window plan is trusted directly so the builder phase can be skipped, and CUDA validate mode also forces compare-builder
- `LONGTARGET_SIM_CUDA_LOCATE_MODE=exact`: force the older locate-first exact backend, which replays CPU `locate()` semantics with one request per worker slot
- `LONGTARGET_SIM_CUDA_LOCATE_EXACT_PRECHECK=off|shadow|on`: optional exact-fallback precheck for `safe_workset`; `shadow` runs a bounded exact locate probe but still executes the legacy exact fallback, while `on` may short-circuit exact fallback when the bounded probe proves there is no update region (default: `off`)
- `LONGTARGET_SIM_CUDA_LOCATE_MODE=fast`: experimental aggressive update mode; skips reverse-DP locate and instead derives a path-local sparse workset from the materialized traceback script, then replays the region update on a row-band worklist (default: `safe_workset`)
- `LONGTARGET_SIM_CUDA_LOCATE_FAST_SHADOW=1`: in `fast` mode, also run exact CPU `locate()+update` and fall back when the sparse workset does not reproduce the exact candidate state
- `LONGTARGET_SIM_CUDA_LOCATE_FAST_PAD=N`: halo size used when dilating the traceback path into row-local work bands (default: 128)
- `LONGTARGET_ENABLE_SIM_CUDA_REGION_REDUCE=1`: experimental GPU-side candidate reduction for CUDA region rescans; the current path first coalesces row-major events into run summaries and then reduces those summaries on-device before copying back candidate states, but it remains experimental and can still regress on some workloads
- `LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK=1`: CUDA global-affine traceback for candidate materialization (not byte-identical; use for speed)
- `LONGTARGET_SIM_FAST=1`: skip traceback update rescans (non-exact, much faster)
- `LONGTARGET_SIM_FAST_UPDATE_BUDGET=N`: in fast mode, do up to `N` traceback update rescans (hybrid speed/accuracy)
- `LONGTARGET_SIM_FAST_UPDATE_ON_FAIL=1`: if a candidate fails to materialize in fast mode, spend from the budget to rescan its region and continue

Traceback CUDA tuning knobs (only when `LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK=1`):
- `LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE=1`: fallback to CPU on detected DP ties (default: 1; improves stability)
- `LONGTARGET_SIM_CUDA_TRACEBACK_MAX_DIM=8192`: only use CUDA when `rl` and `cl` are ≤ this value
- `LONGTARGET_SIM_CUDA_TRACEBACK_MAX_CELLS=67108864`: only use CUDA when `(rl+1)*(cl+1)` is ≤ this value

Optional: two-stage SIM refinement (speed-first, not exact). This mode runs a fast GPU prefilter to pick candidate windows, then runs exact SIM only inside those windows:

- `LONGTARGET_TWO_STAGE=1`: enable two-stage refinement
- `LONGTARGET_TWO_STAGE_THRESHOLD_MODE=legacy|deferred_exact`: threshold scheduling mode (default: `legacy`). `deferred_exact` prefilters first, then computes exact threshold only for surviving tasks.
- `LONGTARGET_PREFILTER_BACKEND=sim|prealign_cuda`: prefilter backend (default: `sim`)
- `LONGTARGET_PREFILTER_TOPK=N`: number of prefilter seeds per task (default: 8; `sim` backend is effectively capped by `K=50` in `sim.h`; `prealign_cuda` supports up to 256)
- `LONGTARGET_PREFILTER_PEAK_SUPPRESS_BP=N`: only for `prealign_cuda` backend; suppress peaks within N bp (default: 5)
- `LONGTARGET_PREFILTER_SCORE_FLOOR_DELTA=N`: only for `prealign_cuda` backend; keep peaks down to `minScore - delta` (default: 0)
- `LONGTARGET_REFINE_PAD_BP=N`: bp padding added to each seed window before refine (default: 64)
- `LONGTARGET_REFINE_MERGE_GAP_BP=N`: merge adjacent windows when gap ≤ N (default: 32)
- `LONGTARGET_TWO_STAGE_REJECT_MODE=off|minimal_v1`: optional Stage A.5 reject gate for `deferred_exact` (default: `off`)
- `LONGTARGET_TWO_STAGE_MIN_PEAK_SCORE`, `LONGTARGET_TWO_STAGE_MIN_SUPPORT`, `LONGTARGET_TWO_STAGE_MIN_MARGIN`, `LONGTARGET_TWO_STAGE_STRONG_SCORE_OVERRIDE`, `LONGTARGET_TWO_STAGE_MAX_WINDOWS_PER_TASK`, `LONGTARGET_TWO_STAGE_MAX_BP_PER_TASK`: `minimal_v1` gate knobs (defaults: `80`, `2`, `6`, `100`, `8`, `32768`)

Notes:
- `prealign_cuda` typically benefits from a larger `LONGTARGET_PREFILTER_TOPK` (e.g. 64–256) to recover more windows; higher values trade speed for recall.
- `deferred_exact` currently requires `LONGTARGET_PREFILTER_BACKEND=prealign_cuda` and `LONGTARGET_PREFILTER_SCORE_FLOOR_DELTA=0`; the binary will fail fast if that contract is violated.

Optional: multi-GPU exact-task scheduling (works best when SIM CUDA is enabled):

- `LONGTARGET_CUDA_DEVICES=0,1`: comma-separated CUDA device indices for SIM CUDA work distribution
- `LONGTARGET_SIM_CUDA_WORKERS_PER_DEVICE=2`: run multiple exact SIM worker threads per listed device; worker slots share the same device but use separate SIM scan/traceback CUDA contexts (default: 1)

Optional task-level OpenMP builds stay opt-in. If your toolchain needs explicit OpenMP flags, pass them through `OPENMP_FLAGS`:

```
make ENABLE_OPENMP=1 OPENMP_FLAGS='-fopenmp' build-openmp
make ENABLE_OPENMP=1 OPENMP_FLAGS='-fopenmp' check-matrix-openmp-par
```

Set `LONGTARGET_BENCHMARK=1` or use `make benchmark-sample` / `make benchmark-smoke` to print per-phase timings for `calc_score`, SIM, and post-processing.

When SIM CUDA region scan is enabled, benchmark output now also includes region-merge telemetry so you can see where time and PCIe traffic go:

- `benchmark.sim_window_pipeline_tasks_considered`: exact-SIM tasks that reached the scheduler lane-selection point
- `benchmark.sim_window_pipeline_tasks_eligible`: tasks that satisfied the current window-pipeline lane constraints and could be batched
- `benchmark.sim_window_pipeline_ineligible_two_stage` / `benchmark.sim_window_pipeline_ineligible_sim_fast` / `benchmark.sim_window_pipeline_ineligible_validate` / `benchmark.sim_window_pipeline_ineligible_runtime_disabled`: tasks kept off the lane because the current runtime mode was incompatible with the exact-safe window pipeline
- `benchmark.sim_window_pipeline_ineligible_query_gt_8192` / `benchmark.sim_window_pipeline_ineligible_target_gt_8192` / `benchmark.sim_window_pipeline_ineligible_negative_min_score`: tasks rejected by the current per-task lane constraints even though the runtime lane itself was enabled
- `benchmark.sim_window_pipeline_batch_runtime_fallbacks`: tasks that were eligible and entered the lane, but still had to fall back because batch preparation or execution failed
- `benchmark.sim_region_events_total`: raw CUDA region events emitted for CPU-side merge
- `benchmark.sim_region_candidate_summaries_total`: number of reduced candidate states copied back in the experimental reduce path
- `benchmark.sim_region_event_bytes_d2h`: raw region event bytes copied device-to-host
- `benchmark.sim_region_summary_bytes_d2h`: reduced candidate summary bytes copied device-to-host
- `benchmark.sim_region_cpu_merge_seconds`: CPU time spent replaying CUDA region events into exact candidate maintenance
- `benchmark.sim_locate_total_cells`: total cell count visited by `locate()` while updating candidates after traceback
- `benchmark.sim_locate_backend`: whether the locate phase ran on `cpu`, `cuda`, or a `mixed` fallback path
- `benchmark.sim_locate_mode`: whether locate used the exact path, the experimental `fast` path, or a mixed result because of fallbacks
- `benchmark.sim_locate_fast_passes`: number of locate calls that completed on the experimental fast path without falling back
- `benchmark.sim_locate_fast_fallbacks`: number of fast locate attempts that fell back to exact locate
- `benchmark.sim_safe_workset_passes`: number of traceback updates that completed on the exact-safe `safe_workset` path without falling back to exact locate
- `benchmark.sim_safe_workset_fallback_invalid_store` / `benchmark.sim_safe_workset_fallback_no_affected_start` / `benchmark.sim_safe_workset_fallback_no_workset` / `benchmark.sim_safe_workset_fallback_invalid_bands` / `benchmark.sim_safe_workset_fallback_scan_failure` / `benchmark.sim_safe_workset_fallback_shadow_mismatch`: why the exact-safe `safe_workset` path fell back to exact locate/update
- `benchmark.sim_safe_workset_affected_starts`: number of candidate start keys carried into the exact-safe `safe_workset` CUDA refresh
- `benchmark.sim_safe_workset_unique_affected_starts`: deduplicated start-key count actually used as the exact-safe `safe_workset` filter set
- `benchmark.sim_safe_workset_input_bands` / `benchmark.sim_safe_workset_input_cells`: sparse exact-safe workset geometry before the execution-time coarsening pass
- `benchmark.sim_safe_workset_exec_bands` / `benchmark.sim_safe_workset_exec_cells`: post-coarsening execution geometry actually dispatched to CUDA
- `benchmark.sim_safe_workset_cuda_tasks` / `benchmark.sim_safe_workset_cuda_launches`: CUDA batch cost for exact-safe `safe_workset` rescans after coarsening
- `benchmark.sim_safe_workset_returned_states`: deduplicated candidate states returned from CUDA before they are merged back into the exact host candidate structures
- `benchmark.sim_safe_workset_build_seconds` / `benchmark.sim_safe_workset_merge_seconds` / `benchmark.sim_safe_workset_total_seconds`: exact-safe `safe_workset` host build time, post-D2H host merge time, and the full locate-side umbrella time for the safe-workset path, so you can separate geometry cost, merge cost, and the end-to-end locate budget
- `benchmark.sim_safe_window_exact_fallbacks`: number of safe-window attempts that still had to fall back to exact locate/update
- `benchmark.sim_safe_window_exact_fallback_no_update_region` / `benchmark.sim_safe_window_exact_fallback_refresh_success` / `benchmark.sim_safe_window_exact_fallback_refresh_failure`: split of those exact fallbacks into “exact locate found no update region”, “exact locate found an update region and the safe-store refresh succeeded”, and “exact locate found an update region but preserving the safe-store failed”
- `benchmark.sim_safe_window_exact_fallback_base_no_update` / `benchmark.sim_safe_window_exact_fallback_expansion_no_update`: split the no-update exact fallbacks into cases that stopped inside the base traceback box versus cases that still needed outward expansion
- `benchmark.sim_safe_window_exact_fallback_stop_no_cross` / `benchmark.sim_safe_window_exact_fallback_stop_boundary`: classify where no-update exact fallbacks terminated
- `benchmark.sim_safe_window_exact_fallback_base_cells` / `benchmark.sim_safe_window_exact_fallback_expansion_cells`: total reverse-DP cells scanned in the base box vs outward expansion for those no-update exact fallbacks
- `benchmark.sim_safe_window_exact_fallback_locate_gpu_seconds`: GPU time spent inside safe-window exact fallback locate/precheck calls
- `benchmark.sim_fast_workset_bands` / `benchmark.sim_fast_workset_cells`: sparse band geometry attempted by the experimental fast locate update path before any fallback
- `benchmark.sim_fast_segments` / `benchmark.sim_fast_diagonal_segments` / `benchmark.sim_fast_horizontal_segments` / `benchmark.sim_fast_vertical_segments`: traceback-path segment totals and orientation mix seen by the fast workset builder
- `benchmark.sim_fast_fallback_no_workset` / `benchmark.sim_fast_fallback_area_cap` / `benchmark.sim_fast_fallback_shadow_running_min` / `benchmark.sim_fast_fallback_shadow_candidate_count` / `benchmark.sim_fast_fallback_shadow_candidate_value`: why the experimental fast path fell back to exact locate/update
- `benchmark.sim_initial_events_total`: logical raw initial events seen before row-run coalescing / reduction
- `benchmark.sim_initial_run_summaries_total`: contiguous same-start run summaries produced by the CUDA initial scan
- `benchmark.sim_initial_reduce_backend`: initial reduce backend selection for the experimental reducer path (`off`, `legacy`, `hash`, `segmented`, or `ordered_segmented_v3`)
- `benchmark.sim_initial_summary_bytes_d2h`: initial summary bytes copied device-to-host (0 on the experimental initial reduce path)
- `benchmark.sim_initial_reduced_candidates_total`: reduced candidate states copied back by the experimental initial reduce path
- `benchmark.sim_initial_all_candidate_states_total`: full per-start candidate states copied back to rebuild the exact-safe initial `safeCandidateStateStore`
- `benchmark.sim_initial_store_bytes_d2h`: bytes copied back for those full candidate states
- `benchmark.sim_initial_store_bytes_h2d`: bytes uploaded when the default summary-handoff path mirrors the rebuilt exact-safe `safeCandidateStateStore` back onto the GPU for `safe_workset` locate
- `benchmark.sim_initial_store_upload_seconds`: host-to-device time spent creating that initial GPU safe-store mirror
- `benchmark.sim_initial_scan_seconds`: total time spent in SIM initial candidate enumeration
- `benchmark.sim_initial_scan_gpu_seconds`: CUDA kernel time inside SIM initial scan
- `benchmark.sim_initial_scan_d2h_seconds`: result handoff time while bringing SIM initial scan data back to host
- `benchmark.sim_initial_scan_cpu_merge_seconds`: CPU time spent merging CUDA initial-scan events into exact candidate maintenance
- `benchmark.sim_initial_scan_cpu_merge_subtotal_seconds`: explicit subtotal of the CPU-side merge subphases (`context_apply + safe_store_update + safe_store_prune + safe_store_upload`) so benchmark logs can check whether the detailed merge counters still close to the total
- `benchmark.sim_initial_store_rebuild_seconds`: CPU-side safe-store rebuild subtotal (`safe_store_update + safe_store_prune`) so reducer work can separate rebuild cost from frontier sync cost
- `benchmark.sim_initial_store_materialize_seconds`: CPU-side safe-store materialization/update subtotal before prune; this is the pre-prune portion of `sim_initial_store_rebuild_seconds`
- `benchmark.sim_initial_store_prune_seconds`: CPU-side safe-store prune subtotal; this is the prune portion of `sim_initial_store_rebuild_seconds`
- `benchmark.sim_initial_frontier_sync_seconds`: CPU-side frontier upload / sync time (`safe_store_upload`) for the summary-handoff safe-store mirror path
- `benchmark.sim_initial_store_other_merge_seconds`: remaining CPU merge time after subtracting `store_rebuild` and `frontier_sync`; on the default exact-safe path this is primarily the candidate/context apply work
- `benchmark.sim_initial_store_other_merge_context_apply_seconds`: portion of `sim_initial_store_other_merge_seconds` attributable to the existing CPU `context_apply` stage
- `benchmark.sim_initial_store_other_merge_context_apply_lookup_seconds` / `benchmark.sim_initial_store_other_merge_context_apply_mutate_seconds` / `benchmark.sim_initial_store_other_merge_context_apply_finalize_seconds`: deeper `context_apply` split following the natural CPU boundaries (`ensureSimCandidateIndexForRun`, candidate mutation, trailing `refreshSimRunningMin`)
- `benchmark.sim_initial_store_other_merge_context_apply_attempted_count` / `modified_count` / `noop_count`: read-only per-summary counts for `context_apply`, used to distinguish “too many updates” from “updates are individually expensive”
- `benchmark.sim_initial_store_other_merge_context_apply_lookup_hit_count` / `lookup_miss_count` / `slot_created_count`: read-only lookup reuse counters for the `context_apply` slot-lookup path, plus the number of fresh candidate slots materialized before the 50-slot candidate set reaches capacity
- `benchmark.sim_initial_store_other_merge_context_apply_lookup_probe_steps_total` / `lookup_probe_steps_max`: probe-depth counters for the open-addressing start-index lookup path, used to separate “too many misses” from “misses are individually deep”
- `benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_open_slot_count` / `lookup_miss_candidate_set_full_count` / `eviction_selected_count` / `reused_slot_count`: read-only miss-path counters that distinguish pre-capacity slot creation from the steady-state candidate-set-full eviction/reuse path
- `benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_open_slot_seconds` / `lookup_miss_candidate_set_full_probe_seconds` / `lookup_miss_eviction_select_seconds` / `lookup_miss_reuse_writeback_seconds`: deeper miss-path timing split for `ensureSimCandidateIndexForRun()`, used to decide whether the next optimization should target probe depth, eviction selection, or reused-slot writeback
- `benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_victim_reset_seconds` / `lookup_miss_reuse_writeback_key_rebind_seconds` / `lookup_miss_reuse_writeback_candidate_copy_seconds` / `lookup_miss_reuse_writeback_aux_bookkeeping_seconds`: deeper steady-state reused-slot writeback split that separates victim-slot index reset, start-key rebind, candidate payload overwrite, and the remaining heap/rebuild bookkeeping
- `benchmark.sim_initial_store_other_merge_context_apply_lookup_miss_reuse_writeback_victim_reset_count` / `lookup_miss_reuse_writeback_candidate_copy_count` / `lookup_miss_reuse_writeback_aux_bookkeeping_count` / `lookup_miss_reuse_writeback_payload_bytes_total` / `lookup_miss_reuse_writeback_aux_updates_total`: read-only reused-slot writeback counters that quantify how often the steady-state replacement path resets a victim, copies a full candidate payload, and performs auxiliary heap/rebuild updates
- `benchmark.sim_initial_store_other_merge_residual_seconds`: remaining unattributed portion of `sim_initial_store_other_merge_seconds` after carving out `context_apply`
- `benchmark.sim_ordered_maintenance_candidate_event_count` / `ordered_segment_count` / `parallel_segment_count` / `mean_segment_length` / `p90_segment_length`: Phase 3b shape telemetry for the host ordered candidate-maintenance stage; the current producer uses context-apply attempts and existing reducer chunk counters conservatively, without changing runtime behavior
- `benchmark.sim_ordered_maintenance_full_set_miss_count` / `existing_candidate_hit_count` / `candidate_replacement_count` / `state_update_count`: coarse ordered-maintenance input/action counters used to classify host CPU merge pressure without reopening candidate-index leaf profiling
- `benchmark.sim_ordered_maintenance_floor_change_count` / `running_min_slot_change_count` / `candidate_replacement_dependency_count` / `serial_dependency_event_count` / `serial_dependency_share` / `parallelizable_event_count` / `parallelizable_event_share`: conservative ordered-dependency telemetry for deciding whether device-side ordered maintenance is plausible or blocked by serial visibility constraints
- `benchmark.sim_ordered_maintenance_estimated_d2h_bytes_avoided` / `estimated_host_rebuild_seconds_avoided` / `estimated_cpu_merge_seconds_avoidable`: Phase 3b avoidable-cost estimates consumed by `scripts/summarize_longtarget_sim_ordered_candidate_maintenance_budget.py`; they remain profiling evidence only and do not enable a runtime prototype
- `benchmark.sim_ordered_maintenance_ordered_segment_source` / `serial_dependency_source` / `parallelizable_event_source` / `ordered_shape_confidence` / `state_machine_source`: Phase 3b.1 calibration metadata. `fallback_conservative` confidence means the summarizer must refine telemetry before declaring an ordered-dependency blocker; `coarse` can still advance only when independent state-machine parallelism is material.
- `benchmark.sim_ordered_maintenance_state_machine_count` / `state_machine_nonempty_count` / `state_machine_event_count_total` / `state_machine_event_count_p50` / `p90` / `p99` / `max` / `work_imbalance_ratio` / `ideal_parallelism`: coarse independent state-machine shape telemetry used to distinguish true single-chain serialization from inter-chain parallelism potential. The current producer uses executed exact-SIM task scope (`case_rule_region_state_machine`) when reducer chunks are unavailable.
- `benchmark.sim_ordered_maintenance_intra_state_machine_serial_dependency_share` / `inter_state_machine_parallelism`: derived Phase 3b.1 gate inputs. High intra-machine serial dependency is only a blocker when inter-machine parallelism is low.
- `benchmark.sim_initial_scan_sync_wait_seconds`: synchronization wait time currently attributed to the initial scan handoff path
- `benchmark.sim_initial_reduce_chunks_total` / `benchmark.sim_initial_reduce_chunks_replayed_total` / `benchmark.sim_initial_reduce_chunks_skipped_total` / `benchmark.sim_initial_reduce_summaries_replayed_total`: ordered-replay chunk statistics from the experimental initial reducer
- `benchmark.sim_initial_run_summary_pipeline_seconds`: subtotal of the run-summary grouping stages (`hash_reduce + segmented_reduce + segmented_compact + topk`) for profiler-guided initial-scan tuning
- `benchmark.sim_initial_hash_reduce_seconds` / `benchmark.sim_initial_segmented_reduce_seconds`: time spent in the optional hash or segmented grouping stage inside the experimental initial reducer
- `benchmark.sim_initial_segmented_compact_seconds`: GPU time spent compacting the segmented safe-store candidates after the grouped reduce (device scan + compact on the `segmented` backend)
- `benchmark.sim_initial_ordered_replay_seconds`: ordered candidate-maintenance phase on the reducer path; today this is the same measured phase as `sim_initial_topk_seconds`, exposed under a more explicit name for reducer tuning
- `benchmark.sim_initial_topk_seconds`: time spent maintaining the exact top-K candidate set on the experimental initial reducer path
- `benchmark.sim_initial_segmented_tile_states_total` / `benchmark.sim_initial_segmented_grouped_states_total`: pre-group and post-group state totals reported by the segmented reducer path
- `benchmark.sim_locate_seconds`: time spent in `locate()` / disjoint region expansion after traceback
- `benchmark.sim_locate_gpu_seconds`: CUDA kernel time inside the locate backend (0 when locate stays on CPU)
- `benchmark.sim_region_scan_gpu_seconds`: CUDA kernel time inside SIM region rescans
- `benchmark.sim_region_d2h_seconds`: result handoff time while bringing SIM region-rescan data back to host
- `benchmark.sim_materialize_seconds`: total time spent materializing accepted candidates
- `benchmark.sim_traceback_dp_seconds`: traceback DP time (`diff()` or CUDA traceback kernel time)
- `benchmark.sim_traceback_post_seconds`: traceback post-processing time (identity / tri-score / optional alignment strings)
- `benchmark.calc_score_tasks_total`: number of threshold tasks seen by the exact threshold pre-pass
- `benchmark.calc_score_cuda_tasks` / `benchmark.calc_score_cpu_fallback_tasks`: split of those threshold tasks between CUDA and CPU fallback
- `benchmark.calc_score_cpu_fallback_query_gt_8192` / `benchmark.calc_score_cpu_fallback_target_gt_8192` / `benchmark.calc_score_cpu_fallback_target_gt_65535` / `benchmark.calc_score_cpu_fallback_other`: why threshold work fell back to CPU
- `benchmark.calc_score_query_length`: single-query length for the current LongTarget run
- `benchmark.calc_score_target_bin_le_8192_*` / `benchmark.calc_score_target_bin_8193_65535_*` / `benchmark.calc_score_target_bin_gt_65535_*`: target-length workload histogram by task count and bp, so whole-genome runs can distinguish “poor CUDA coverage” from “pathological workload shape”

Current exact-safe mainline note: CUDA initial scan now keeps the row-run coalescing on the GPU handoff path: host-side candidate maintenance consumes per-row contiguous same-start run summaries instead of raw initial events. Relative to the older raw-event handoff, this keeps `benchmark.sim_initial_scan_cpu_merge_seconds` lower on the benchmark path (about `0.17s` in the latest fresh run) and cuts the large-sample handoff more materially (`benchmark.sim_initial_scan_d2h_seconds` about `0.91s -> 0.51s`, `benchmark.sim_initial_scan_cpu_merge_seconds` about `1.85s -> 1.56s` on `sample_exactness_cuda_sim_region`). The latest implementation step also removes the old "one thread per row" summary kernels: run-start detection and summary compaction are now block-parallel while still preserving row order and the "first endJ that reaches the max score" exactness rule. The default summary-handoff path now also mirrors the rebuilt exact-safe safe-store back onto the GPU when `safe_workset` locate is active, so `safe_window` / GPU safe-workset builders can stay on their fast path without forcing `LONGTARGET_ENABLE_SIM_CUDA_INITIAL_REDUCE=1`. There is still an experimental `LONGTARGET_ENABLE_SIM_CUDA_INITIAL_REDUCE=1` path that replays ordered run summaries on-device, returns both the reduced top-K candidate states and the full per-start candidate-state store, and rebuilds the exact-safe `safeCandidateStateStore` on the host without falling back to an invalid initial store. `LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND=hash` keeps the single-request path on the shared true-batch/hash reducer, while `LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND=segmented` keeps the exact legacy top-K candidate replay but replaces the full safe-store rebuild with a grouped segmented reduce over `(batchIndex,startCoord)` keys. `LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND=ordered_segmented_v3` currently reuses that segmented reducer path as the stable entry point for the next ordered-replay iteration, so the default exact-safe safe-store handoff can opt into device residency without changing result semantics. That path now also keeps the post-reduce safe-store compaction on the GPU via a device-side exclusive scan + compact pass, exposing `benchmark.sim_initial_segmented_*` telemetry (including `benchmark.sim_initial_segmented_compact_seconds`) in stderr. When `LONGTARGET_ENABLE_SIM_CUDA_DEVICE_K_LOOP=1` is enabled, the proposal loop can also source top-K states directly from the persistent GPU safe-store; stderr then reports `benchmark.sim_proposal_loop_source_gpu_safe_store` and `benchmark.sim_device_k_loop_seconds`. Large-sample telemetry still shows the experimental reducer is slower than the summary-handoff default, so it remains off by default while the device-side ordered replay is being optimized further.

`scripts/project_whole_genome_runtime.py` keeps the current linear projection model, but when the new benchmark counters are present it now also reports optional derived ratios:

- `window_pipeline_eligible_ratio`
- `window_pipeline_fallback_ratio`
- `calc_score_cuda_task_ratio`
- `calc_score_cpu_fallback_ratio`
- `projected_sim_initial_scan_seconds`
- `projected_sim_initial_scan_cpu_merge_seconds`
- `projected_sim_initial_scan_cpu_merge_subtotal_seconds`
- `projected_sim_initial_run_summary_pipeline_seconds`
- `projected_sim_initial_ordered_replay_seconds`
- `projected_sim_initial_store_rebuild_seconds`
- `projected_sim_initial_store_materialize_seconds`
- `projected_sim_initial_store_prune_seconds`
- `projected_sim_initial_frontier_sync_seconds`
- `projected_sim_initial_store_other_merge_seconds`

These ratios are additive to the existing `projected_*` fields and remain optional so older benchmark logs still parse unchanged.

Validation helpers:

- `make check-benchmark-telemetry`: verify benchmark stderr includes the expected telemetry fields
- `make check-sim-cuda-region-docs`: verify this README and `EXACT_SIM_PROGRESS.md` still document the SIM CUDA region exactness constraints
- `make check-sim-initial-cuda-merge`: verify the coalesced CUDA initial-scan host merge matches per-event replay while reducing logical host updates
- `make check-sim-initial-host-merge-corpus`: verify the default exact-safe summary-handoff host-merge corpus writer, loader, and offline replay agree on context candidates plus pre/post-prune safe-store states
- `make check-sim-initial-host-merge-capture-modes`: verify manifest-only capture works without payload files and `LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_CASE_LIST` restricts full dump to the requested case IDs
- `make check-select-sim-initial-host-merge-cases`: verify the manifest selection script emits a deterministic case-list-compatible TSV with bucket metadata from a small census fixture
- `make check-analyze-sim-initial-host-merge-phase-shares`: verify the host-merge phase-share helper enforces the coverage gate and emits the expected decision summary
- `make check-analyze-sim-initial-host-merge-reference-profile`: verify the reference-only host-merge profile helper selects the anchor plus heavy cases and emits a stable hotspot-family recommendation from fixture gprof reports
- `make check-project-whole-genome-runtime`: verify the projection script preserves backward compatibility and emits the optional whole-genome ratios when the source telemetry is present

The offline replay helper for those dumped corpora is `tests/sim_initial_host_merge_replay`. Typical usage:

```bash
./tests/sim_initial_host_merge_replay \
  --corpus-dir /tmp/host-merge-corpus \
  --all \
  --verify \
  --output-tsv /tmp/host-merge-corpus/replay.tsv
```

To microbenchmark a frozen case without rerunning the CUDA initial scan, add `--warmup-iterations`, `--iterations`, and `--aggregate-tsv`:

```bash
./tests/sim_initial_host_merge_replay \
  --corpus-dir /tmp/host-merge-corpus \
  --case case-00000001 \
  --verify \
  --output-tsv /tmp/host-merge-corpus/replay.tsv \
  --warmup-iterations 1 \
  --iterations 10 \
  --aggregate-tsv /tmp/host-merge-corpus/replay-aggregate.tsv
```

The aggregate TSV now also splits `store_materialize` into `store_materialize_reset_*`, `store_materialize_insert_*`, `store_materialize_update_*`, and `store_materialize_snapshot_copy_*` timing columns, plus per-case `store_materialize_inserted_count` / `store_materialize_updated_count` and `store_materialize_peak_size` / `store_materialize_rehash_count`, so the frozen-corpus microbenchmark can separate safe-store setup, new-record append/materialization, in-place update bookkeeping, replay-only snapshot copy cost, and whether hash-map growth stayed bounded after upfront `reserve()`.

`store_other_merge` remains as the top-level residual phase in both runtime telemetry and frozen-corpus replay, but replay aggregate TSVs now further split it into `store_other_merge_context_apply_*`, `store_other_merge_context_snapshot_*`, `store_other_merge_state_snapshot_*`, and `store_other_merge_residual_*` so the same 16-case corpus can distinguish real `context_apply` work from replay-only snapshot/copy overhead before choosing the next optimization target. The deeper `context_apply` microbenchmark now also emits `store_other_merge_context_apply_lookup_*`, `store_other_merge_context_apply_mutate_*`, `store_other_merge_context_apply_finalize_*`, attempted/modified/noop/hit/miss/slot-created counts, derived lookup normalization columns (`store_other_merge_context_apply_lookup_ns_per_attempt`, `*_lookup_hit_ns_per_event`, `*_lookup_miss_ns_per_event`), and a deeper miss-path split (`*_lookup_miss_open_slot_*`, `*_lookup_miss_candidate_set_full_probe_*`, `*_lookup_miss_eviction_select_*`, `*_lookup_miss_reuse_writeback_*`). The current replay aggregate now also splits steady-state `*_lookup_miss_reuse_writeback_*` into `victim_reset`, `key_rebind`, `candidate_copy`, and `aux_bookkeeping`, plus reuse-path counters for payload bytes and auxiliary update volume. Because these deeper splits add extra per-summary timers inside `context_apply`, use them for relative attribution within the reused-slot miss path rather than for cross-run comparison against earlier unsplit top-level replay aggregates. On the current 16-case frozen corpus, `slot_created_count=800` while `lookup_miss_count=45.46M`, so the steady-state hotspot is not fresh slot creation but the candidate-set-full miss path. Within that steady-state miss path, `reuse_writeback` remained the dominant bucket in the unspecialized replay profile, which motivated the later isolated steady-state trace/replay harness described below.

For isolated steady-state experiments after `candidateCount == K`, use `tests/sim_initial_host_merge_steady_state_miss_profile` to capture post-fill traces and replay them through either the reference backend or an experimental specialized backend:

```bash
./tests/sim_initial_host_merge_steady_state_miss_profile \
  --capture-trace \
  --corpus-dir /tmp/host-merge-corpus \
  --case case-00000001 \
  --trace-dir /tmp/host-merge-steady-state \
  --output-tsv /tmp/host-merge-steady-state/capture.tsv

./tests/sim_initial_host_merge_steady_state_miss_profile \
  --replay-trace \
  --trace-dir /tmp/host-merge-steady-state \
  --backend reference \
  --case case-00000001 \
  --verify \
  --warmup-iterations 1 \
  --iterations 10 \
  --output-tsv /tmp/host-merge-steady-state/reference.tsv \
  --aggregate-tsv /tmp/host-merge-steady-state/reference-aggregate.tsv
```

The current experimental `specialized` backend is intentionally documented as a no-go baseline, not an accepted optimization. It keeps a fixed `K=50` active set with a linear victim scan and replays only the steady-state full-set miss path after the candidate set is full. On the current anchor + heavy-case campaign (`case-00000417` plus the five heaviest cases by isolated `context_apply_seconds`), both `reference` and `specialized` replays verify semantically, but the specialized backend regresses performance badly: aggregate steady-state replay time is about `+93%`, full-set miss time is about `+193%`, and `ns_per_full_set_miss` rises from about `40.8ns` to about `119.6ns`. Projected back onto the isolated `context_apply` baseline, replacing the current steady-state path with this backend would regress `context_apply` by about `+23%`. Keep the harness, trace format, and no-go benchmark as an experimental baseline, but do not route further optimization work through this exact linear-scan specialized design without a new structural hypothesis.

On real shards, do not run unbounded full-payload capture. Start with `LONGTARGET_SIM_INITIAL_HOST_MERGE_MANIFEST_PATH`, select a small set of `case_id`s, and then rerun with `LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_CASE_LIST` plus a bounded `LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_MAX_CASES`. In these capture-only modes it is expected that LongTarget's normal `output/` directory may stay empty. If you need to observe a long census in flight, set `LONGTARGET_SIM_INITIAL_HOST_MERGE_HEARTBEAT_SECONDS` / `LONGTARGET_SIM_INITIAL_HOST_MERGE_HEARTBEAT_CASES`; `SIGINT`/`SIGTERM` now stop scheduling new work and preserve the partial manifest that has already been written.

`scripts/select_sim_initial_host_merge_cases.py` keeps `case_id` as the first column so the generated TSV remains directly usable as `LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_CASE_LIST`, while also adding `bucket_key`, tertile bins, counts, and `selection_rank` / `selection_reason` metadata for later attribution. The default `legacy` strategy preserves the original logical-event-first representative selection, while `--strategy coverage_weighted --logical-weight 1 --materialized-weight 2 --coverage-report <path>` switches to coverage-driven representative ranking that intentionally prioritizes `store_materialized_count` coverage when the materialized-heavy tail is the gating metric.

Corpus replay now ignores non-case helper directories under the corpus root (for example `corpus/out/`) and only treats `case-*` subdirectories as replayable cases, so auxiliary benchmark outputs can live alongside the frozen corpus without polluting `--all` / case-list enumeration.

After replay benchmarking, use `scripts/analyze_sim_initial_host_merge_phase_shares.py` to join the manifest census, selected case list, and aggregate replay TSV into:

- `selected_joined.tsv`: selected cases with replay phase timings
- `bucket_rollup.tsv`: manifest bucket totals plus the representative case used for each covered bucket
- `summary.json` / `summary.md`: coverage-gated decision output

The helper only promotes a materialize/prune decision when both `covered_logical_event_share` and `covered_store_materialized_share` reach `0.80`; otherwise it reports `decision_status=insufficient_coverage` and `next_action=expand_corpus`.

Once the isolated `context_apply` profiler harness has emitted `context_apply.tsv`, per-case reference replay aggregates, and anchor/heavy-case gprof flat profiles, use `scripts/analyze_sim_initial_host_merge_reference_profile.py` to summarize the reference-only hotspot families into `selected_cases.tsv`, `summary.json`, and `summary.md`. The helper groups stable gprof symbols into `candidate_index_map_path`, `heap_maintenance_path`, `other_reference_path`, and `setup_or_materialize_noise`, then recommends whether the next step should target the candidate-index map path, the heap path, or whether the profile signal is still too weak.

The sampled candidate-index leaf-profiling line is now formally stopped; see `docs/plans/2026-04-23-candidate-index-leaf-profiling-stop-summary.md` for the authoritative stop summary and `docs/plans/2026-04-23-candidate-index-structural-profiling.md` for the Phase 2 structural-profiling handoff. Further work on this path should proceed as structural profiling rather than deeper leaf splitting.

The first Phase 2 batch is now wired into the repo as a summarizer-only structural lane: `scripts/summarize_sim_initial_host_merge_candidate_index_operation_rollup.py`, `scripts/summarize_sim_initial_host_merge_candidate_index_common_memory_behavior.py`, and `scripts/summarize_sim_initial_host_merge_candidate_index_structural_phase.py`, plus their matching `check_*.sh` regressions. In this batch, top-level roll-up can advance from the leaf-level stop state into structural profiling, operation roll-up can recommend common-memory follow-up, and common-memory behavior v0 reuses existing lifecycle write-path fields. New `sim.h` hot-path counters and hardware-observation harnesses are intentionally deferred, control-flow is recorded only as an optional structural hypothesis, and `runtime_prototype_allowed` remains `false`.

To refresh the authoritative Phase 2a structural artifacts from an already-completed sampled campaign, run `scripts/refresh_sim_initial_host_merge_candidate_index_structural_phase.sh` against the existing `profile_mode_ab_summary.json`, `candidate_index_lifecycle_summary.json`, the leaf-stop `branch_rollup_decision.json`, and the existing telemetry/state-update classification decisions. The wrapper emits:

- `candidate_index_operation_rollup/`
- `candidate_index_common_memory_behavior/`
- `candidate_index_structural_phase/`
- refreshed `branch_rollup/`

This wrapper is post-processing only: it does not rerun the profiler, does not reopen any leaf frontier, and does not enable runtime prototypes.

After the candidate-index leaf and structural phases have both stopped, reset optimization selection to a top-level budget instead of continuing local splits. `scripts/summarize_longtarget_top_level_perf_budget.py` consumes either an explicit component budget JSON or the existing `scripts/project_whole_genome_runtime.py` JSON report, computes each component's share of total time plus the Amdahl upper bound (`max_speedup_if_removed`), and emits `top_level_perf_budget.json`, `top_level_perf_budget_decision.json`, and `top_level_perf_budget.md`. If a candidate-index branch roll-up decision says the candidate-index line is stopped, the summarizer marks `candidate_index` as `known_material_but_no_actionable_leaf`, keeps `runtime_prototype_allowed=false`, and selects the next target only from the top-level actions: `profile_calc_score_path`, `profile_device_resident_sim_pipeline`, `profile_d2h_handoff_path`, `profile_safe_store_or_locate_path`, or `stop_candidate_index_work`.

When the top-level budget selects `sim`, `scripts/summarize_longtarget_sim_pipeline_budget.py` performs the next post-processing step for Phase 3a. It consumes the top-level budget decision plus a SIM telemetry/projection JSON and emits `sim_pipeline_budget.json`, `sim_pipeline_budget_decision.json`, `sim_pipeline_budget_cases.tsv`, and `sim_pipeline_budget.md`. Its only active next actions are `collect_sim_substage_telemetry`, `profile_device_resident_state_handoff`, `profile_device_side_ordered_candidate_maintenance`, `profile_sim_initial_scan_kernel`, `profile_locate_traceback_pipeline`, or `stop_sim_pipeline_work`; it keeps `runtime_prototype_allowed=false` and does not start a GPU implementation. Missing SIM substage fields are reported as `insufficient_sim_substage_telemetry`, not as evidence that no SIM subcomponent is stable.

To refresh the Phase 3a SIM pipeline budget from existing artifacts, run `scripts/refresh_longtarget_sim_pipeline_budget.sh --top-level-budget-decision <top_level_perf_budget_decision.json> --sim-telemetry-budget <projection-or-telemetry.json> --output-root <dir>`. The wrapper emits `sim_pipeline_budget/` under the output root and is post-processing only; it does not run a workload or enable a runtime prototype.

To aggregate multiple real workload refreshes, run `scripts/summarize_longtarget_sim_pipeline_budget_rollup.py --sim-pipeline-budget-decision <workload-a/sim_pipeline_budget_decision.json> --sim-pipeline-budget-decision <workload-b/sim_pipeline_budget_decision.json> --output-dir <dir>`. The roll-up emits `sim_pipeline_budget_rollup.json`, `sim_pipeline_budget_rollup_decision.json`, `sim_pipeline_budget_rollup_cases.tsv`, and `sim_pipeline_budget_rollup.md`. If any workload still lacks SIM substage telemetry, the roll-up preserves `selection_status=insufficient_sim_substage_telemetry` and `recommended_next_action=collect_sim_substage_telemetry`; if ready workloads disagree or mix selected and no-stable decisions, it reports `selection_status=workload_dependent_subcomponent`, `stratification_status=needed`, and `recommended_next_action=expand_or_stratify_sim_pipeline_budget`. The cases TSV carries per-workload class, SIM/total seconds, subcomponent shares, and missing-field count so the next step can expand or stratify the budget instead of choosing a global runtime direction. A stable subcomponent is authoritative only when real workload decisions agree, and `runtime_prototype_allowed` remains `false`.

When the SIM pipeline roll-up stably selects `host_cpu_merge`, Phase 3b is still profiler-only: `scripts/summarize_longtarget_sim_ordered_candidate_maintenance_budget.py --sim-pipeline-budget-rollup-decision <sim_pipeline_budget_rollup_decision.json> --output-dir <dir>` summarizes device-side ordered candidate maintenance feasibility. It emits `ordered_candidate_maintenance_budget_summary.json`, `ordered_candidate_maintenance_budget_decision.json`, `ordered_candidate_maintenance_budget_cases.tsv`, and `ordered_candidate_maintenance_budget.md`. Missing ordered-maintenance shape telemetry yields `recommended_next_action=collect_ordered_candidate_maintenance_telemetry`; `fallback_conservative` shape confidence yields `recommended_next_action=refine_ordered_maintenance_shape_telemetry` instead of treating a single long chain as a final blocker. Coarse or better evidence with `inter_state_machine_parallelism >= 8` and material avoidable CPU merge time may recommend `design_device_side_ordered_candidate_maintenance_shadow`; high intra-machine serial dependency only blocks when inter-machine parallelism is below 2. `runtime_prototype_allowed` remains `false`.

`scripts/project_whole_genome_runtime.py` also normalizes the current benchmark field names needed by Phase 3a, including `sim_initial_run_summaries_total` to `projected_sim_initial_summary_count`, `sim_initial_store_bytes_d2h` to `projected_sim_initial_candidate_state_bytes_d2h`, `sim_initial_store_rebuild_seconds` to `projected_sim_initial_host_rebuild_seconds`, and `sim_initial_store_upload_seconds` to `projected_sim_initial_state_handoff_seconds`.

To compare the bundled sample (`testDNA.fa` + `H19.fa`) against `Fasim-LongTarget` (speed + TFOsorted overlap vs LongTarget exact), run:

```
make benchmark-sample-cuda-vs-fasim
```

This repo also vendors a copy of `Fasim-LongTarget` under `fasim/` and provides build targets:

```
make build-fasim        # CPU (stubbed CUDA preAlign)
make build-fasim-cuda   # CUDA-enabled (GPU preAlign available)
```

Enable the CUDA preAlign path at runtime (useful when you have many regions to process in one run):

```
FASIM_OUTPUT_MODE=tfosorted FASIM_ENABLE_PREALIGN_CUDA=1 FASIM_VERBOSE=0 ./fasim_longtarget_cuda -f1 testDNA.fa -f2 H19.fa -r 0 -O /tmp/out
```

Tuning knobs:
- `FASIM_CUDA_DEVICE`: CUDA device index (falls back to `LONGTARGET_CUDA_DEVICE`, else 0)
- `FASIM_CUDA_DEVICES`: comma-separated CUDA devices for multi-GPU (e.g. `0,1`). When set, batches are split across devices.
- `FASIM_EXTEND_THREADS`: CPU worker threads for the extend+output stage (default: `--cn` / `-C`, else 1)
- `FASIM_PREALIGN_CUDA_MAX_TASKS`: max tasks per GPU batch call (default 4096)
- `FASIM_PREALIGN_CUDA_TOPK`: peaks per task (default 64; current max is 256)
- `FASIM_PREALIGN_PEAK_SUPPRESS_BP`: peak suppression radius in bp when converting GPU peaks to `scoreInfo` (default 5). Decreasing (e.g. `1-2`) keeps more peaks and can improve recall at the cost of more CPU extend work; increasing does the opposite.
- `FASIM_VERBOSE=0`: disable per-segment progress printing (recommended for large batches)
- `FASIM_OUTPUT_MODE=tfosorted`: only write `*-TFOsorted` and skip `TFOclass1/2` clustering output (recommended for large multi-region batches; also enables streaming + cross-record GPU batching)

Optional: skip `TFOclass1/2` for LongTarget as well:
- `LONGTARGET_OUTPUT_MODE=tfosorted`: only write `*-TFOsorted` (skip clustering/class outputs)
- `LONGTARGET_OUTPUT_MODE=lite`: only write `*-TFOsorted.lite` (skip `*-TFOsorted` and clustering/class outputs)

Optional: also write a lightweight tab-separated `*-TFOsorted.lite` alongside `*-TFOsorted` (recommended for huge batch runs; omits alignment strings and clustering fields):
- `LONGTARGET_WRITE_TFOSORTED_LITE=1`: enable lite output for LongTarget
- `FASIM_WRITE_TFOSORTED_LITE=1`: enable lite output for Fasim (`FASIM_OUTPUT_MODE=tfosorted` path)
- Lite columns: `Chr`, `StartInGenome`, `EndInGenome`, `Strand`, `Rule`, `QueryStart`, `QueryEnd`, `StartInSeq`, `EndInSeq`, `Direction`, `Score`, `Nt(bp)`, `MeanIdentity(%)`, `MeanStability`

Throughput-first local fasim lane (kept explicit and separate from the default exact-safe LongTarget runner):

```
make check-fasim-throughput-preset
make check-benchmark-throughput-comparator
make benchmark-sample-cuda-throughput-compare
```

- `scripts/run_fasim_throughput_preset.sh`: wrapper for the vendored `fasim_longtarget_cuda` throughput lane. It keeps the threshold policy explicit and currently supports only `FASIM_THRESHOLD_POLICY=fasim_peak80`.
- Default throughput preset values: `FASIM_ENABLE_PREALIGN_CUDA=1`, `FASIM_PREALIGN_CUDA_TOPK=64`, `FASIM_PREALIGN_PEAK_SUPPRESS_BP=5`, `FASIM_VERBOSE=0`, `FASIM_OUTPUT_MODE=lite`.
- The sample throughput comparator always compares the same repo revision, the same inputs, and the same output schema (`lite` or `tfosorted`). In throughput mode the default comparison schema is `.lite`.
- `report.json` now includes both aggregate comparison metrics and `per_output_comparisons`, so shard- or output-level drops are visible without losing the aggregate summary.
- The throughput lane does not implicitly enable two GPUs. Pass `FASIM_CUDA_DEVICES=0,1` (or use the sweep script below) only after checking whether the second device really improves wall time.

Throughput sweep helper (one exact baseline reused across a throughput matrix; by default it sweeps device set × `FASIM_EXTEND_THREADS`, and it can also sweep `TOPK` / `suppress_bp` when you want a small-shard quality frontier):

```
make benchmark-fasim-throughput-sweep
# or:
python3 ./scripts/benchmark_fasim_throughput_sweep.py --device-sets 0 0,1 --extend-threads 1,4,8,16,20
make check-fasim-throughput-sweep
```

- `report.json` now records `quality_gate`, `best_overall`, and `best_qualifying`.
- `best_overall` is only the wall-time winner. `best_qualifying` is the candidate to carry forward once you care about quality.
- `best` is kept as a compatibility alias of `best_overall`.
- Quality gates are controlled with `--min-relaxed-recall` and `--min-top-hit-retention`. Use `--require-qualifying-run` in CI or scripted sweeps when "no qualifying configuration" should be a hard failure.
- Recommended workflow:
  1. Start on small real shards (`200 kb` to `1 Mb`) and sweep `--topk-values` / `--suppress-bp-values` to find a speed-quality frontier.
  2. Freeze a quality-acceptable throughput preset.
  3. Then sweep `--device-sets` and `--extend-threads` on larger shards for wall-time tuning.
- To generate anchor shards from a local single-record FASTA such as `.tmp/ucsc/hg38/hg38_chr22.fa`, use:

```
python3 ./scripts/make_anchor_shards.py \
  --input-fasta .tmp/ucsc/hg38/hg38_chr22.fa \
  --output-dir .tmp/ucsc/hg38/anchors_200kb \
  --starts 10500001,20500001,30500001 \
  --length 200000
make check-make-anchor-shards
```

- The helper writes `hg38_chr22_<start>_<length>.fa` files and preserves the UCSC-style FASTA header format as `>hg38|chr22|start-end`.
- After you run multiple anchor sweeps, summarize them into one Pareto-oriented table with:

```
python3 ./scripts/summarize_throughput_frontier.py \
  .tmp/hg38_chr22_anchors/*/report.json
make check-summarize-throughput-frontier
```

- The summary groups runs by `device_set × extend_threads × topk × suppress_bp` and reports:
  - `zero_top_hit_reports` / `all_top_hit_nonzero` for the hard top-hit filter
  - `qualifying_reports` from each report's `quality_gate`
  - `pareto_optimal` using `mean_wall_seconds` vs worst-output recall / top-hit retention
- Experimental two-stage frontier calibration keeps the standalone Fasim throughput lane unchanged while measuring whether `LONGTARGET_TWO_STAGE=1` with `LONGTARGET_PREFILTER_BACKEND=prealign_cuda` is worth promoting later:

```
make benchmark-two-stage-frontier-sweep
# or:
python3 ./scripts/benchmark_two_stage_frontier_sweep.py \
  --prefilter-topk-values 64,128,256 \
  --peak-suppress-bp-values 0,1,5 \
  --score-floor-delta-values 0 \
  --refine-pad-values 64 \
  --refine-merge-gap-values 32
make check-two-stage-frontier-sweep
```

- Each run compares the same exact LongTarget baseline against a two-stage variant and records both quality metrics and prefilter/refine telemetry (`prefilter_hits`, `refine_window_count`, `refine_total_bp`).
- `best_overall` is only the wall-time winner. `best_qualifying` is the candidate to carry forward once the quality gate is set.
- Recommended workflow:
  1. Start with the bundled sample pair (`testDNA.fa` + `H19.fa`).
  2. Then run `5-8` distributed real `200 kb` anchor shards and set the quality gate from those reports.
  3. Only after a stable `best_qualifying` appears across the anchors should you try `~1 Mb` confirmation shards or consider promoting this lane.
- After you run multiple anchor sweeps, summarize them with:

```
python3 ./scripts/summarize_two_stage_frontier.py \
  .tmp/hg38_chr22_two_stage/*/report.json
make check-summarize-two-stage-frontier
```

- The summary groups runs by `prefilter_topk × peak_suppress_bp × score_floor_delta × refine_pad_bp × refine_merge_gap_bp` and reports:
  - `zero_top_hit_reports` / `all_top_hit_nonzero`
  - `qualifying_reports`
  - `mean_prefilter_hits`, `mean_refine_window_count`, `mean_refine_total_bp`
  - `pareto_optimal` using `mean_wall_seconds` vs worst-output recall / top-hit retention
- Threshold-mode calibration for the native deferred lane compares `legacy`, `deferred_exact`, `deferred_exact + minimal_v1`, `deferred_exact + minimal_v2`, and the experimental `deferred_exact + minimal_v2 + selective_fallback` lane on the same input while preserving canonicalized output diffs:

```
make benchmark-two-stage-threshold-modes
make check-two-stage-threshold-modes
```

- `scripts/benchmark_two_stage_threshold_modes.py` records:
  - `benchmark.two_stage_threshold_mode`, `benchmark.two_stage_reject_mode`
  - `benchmark.two_stage_tasks_with_any_seed`
  - `benchmark.two_stage_tasks_with_any_refine_window_before_gate`
  - `benchmark.two_stage_tasks_with_any_refine_window_after_gate`
  - `benchmark.two_stage_threshold_invoked_tasks`
  - `benchmark.two_stage_threshold_skipped_no_seed_tasks`
  - `benchmark.two_stage_threshold_skipped_no_refine_window_tasks`
  - `benchmark.two_stage_threshold_skipped_after_gate_tasks`
  - `benchmark.two_stage_threshold_batch_count`, `benchmark.two_stage_threshold_batch_tasks_total`, `benchmark.two_stage_threshold_batch_size_max`, `benchmark.two_stage_threshold_batched_seconds`
  - `benchmark.two_stage_windows_before_gate`, `benchmark.two_stage_windows_after_gate`
  - `benchmark.two_stage_windows_rejected_by_min_peak_score`, `benchmark.two_stage_windows_rejected_by_support`, `benchmark.two_stage_windows_rejected_by_margin`, `benchmark.two_stage_windows_trimmed_by_max_windows`, `benchmark.two_stage_windows_trimmed_by_max_bp`
  - `benchmark.two_stage_singleton_rescued_windows`, `benchmark.two_stage_singleton_rescued_tasks`, `benchmark.two_stage_singleton_rescue_bp_total`
  - `benchmark.two_stage_selective_fallback_enabled`, `benchmark.two_stage_selective_fallback_triggered_tasks`, `benchmark.two_stage_selective_fallback_non_empty_candidate_tasks`, `benchmark.two_stage_selective_fallback_non_empty_rejected_by_max_kept_windows_tasks`, `benchmark.two_stage_selective_fallback_non_empty_rejected_by_no_singleton_missing_margin_tasks`, `benchmark.two_stage_selective_fallback_non_empty_rejected_by_singleton_override_tasks`, `benchmark.two_stage_selective_fallback_non_empty_rejected_as_covered_by_kept_tasks`, `benchmark.two_stage_selective_fallback_non_empty_rejected_by_score_gap_tasks`, `benchmark.two_stage_selective_fallback_non_empty_triggered_tasks`, `benchmark.two_stage_selective_fallback_selected_windows`, `benchmark.two_stage_selective_fallback_selected_bp_total`
  - `benchmark.two_stage_task_rerun_enabled`, `benchmark.two_stage_task_rerun_budget`, `benchmark.two_stage_task_rerun_selected_tasks`, `benchmark.two_stage_task_rerun_effective_tasks`, `benchmark.two_stage_task_rerun_added_windows`, `benchmark.two_stage_task_rerun_refine_bp_total`, `benchmark.two_stage_task_rerun_seconds`, `benchmark.two_stage_task_rerun_selected_tasks_path`
  - report-level compare fields: `threshold_batch_size_mean`, `tolerant_equal`, `first_diff_examples`, `run_env_overrides_requested`
- `--run-env LABEL:KEY=VALUE` lets one threshold-mode rerun inject a candidate-only env override without mutating the shared baseline lanes; use it for narrow selector ablations rather than broad global gate sweeps.
- `LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK=1` enables the experimental shortlist rescue used by `deferred_exact_minimal_v2_selective_fallback` and the narrow `deferred_exact_minimal_v3_scoreband_75_79` runtime prototype:
  - scope is intentionally narrow: only deferred-exact + `minimal_v2`
  - trigger is conservative: it first rescues empty-after-gate tasks, and it can also rescue sparse non-empty tasks when a qualifying rejected `singleton_missing_margin` window stays close to the strongest kept window
  - `deferred_exact_minimal_v3_scoreband_75_79` keeps the existing singleton path intact, then adds one post-hoc non-empty rescue for the strongest uncovered rejected window in the `75-79` score band
  - action is narrow: re-admit exactly one rejected window into the exact refine pass
  - this is an experimental candidate-lane rescue, not a default semantic change and not a task-level `reject=off`
  - optional knobs for the non-empty ambiguity lane:
    - `LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_MAX_KEPT_WINDOWS` limits rescue to sparse tasks (default: `1`)
    - `LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_SCORE_GAP` caps the allowed best-seed-score gap between the strongest kept window and the rescued rejected singleton (default: `6`)
    - `LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_SCORE_BAND_75_79=1` enables the first runtime candidate-class expansion: rescue one uncovered `75-79` rejected window after the singleton path fails; the benchmark lane sets `NON_EMPTY_MAX_KEPT_WINDOWS=2` and leaves `SCORE_GAP` unchanged
- `LONGTARGET_TWO_STAGE_TASK_RERUN=1` enables the first task-level exact-rerun runtime prototype on top of `minimal_v3`:
  - scope is intentionally narrow: only deferred-exact + `minimal_v3` shortlist baseline, and only for tasks explicitly listed in `LONGTARGET_TWO_STAGE_TASK_RERUN_SELECTED_TASKS_PATH`
  - the selected-task file is a TSV with header:
    - `fragment_index`
    - `fragment_start_in_seq`
    - `fragment_end_in_seq`
    - `reverse_mode`
    - `parallel_mode`
    - `strand`
    - `rule`
  - matching is exact on that full 7-field task key; this avoids the real-panel collision bug where fragment-only joins merged different `strand/rule` tasks
  - action is conservative: selected tasks keep the same gate telemetry, but their exact execution windows are upgraded from `after_gate` to stored `before_gate` windows
  - `LONGTARGET_TWO_STAGE_TASK_RERUN_BUDGET` is recorded in telemetry and used by the benchmark lanes:
    - `deferred_exact_minimal_v3_task_rerun_budget8`
    - `deferred_exact_minimal_v3_task_rerun_budget16`
  - `LONGTARGET_TWO_STAGE_TASK_RERUN_SELECTED_TASKS_PATH` may be empty; in that case the runtime lane behaves like `minimal_v3` and reports zero selected/effective rerun tasks
  - current positioning:
    - keep `deferred_exact_minimal_v3_scoreband_75_79` as the experimental shortlist baseline
    - treat `deferred_exact_minimal_v3_task_rerun_budget16` as the current experimental runtime baseline for "candidate generator + targeted exact rescue"
    - keep `deferred_exact_minimal_v3_task_rerun_budget8` as the cheaper control lane
- Heavy-zone micro-anchor calibration uses coarse tiling plus the same 3-arm threshold-mode compare:

```
make benchmark-two-stage-threshold-heavy-microanchors
make check-two-stage-threshold-heavy-microanchors
```

- `scripts/benchmark_two_stage_threshold_heavy_microanchors.py` writes:
  - `discovery_report.json` with all tiled candidate reports
  - `summary.json` with selected micro-anchors, 3-arm run payloads, and `decision_flags`
  - `summary.md` with a compact gate/quality table for the shortlisted micro-anchors
- Selective-fallback follow-up keeps the same representative tiles, compares the fallback panel against the earlier `minimal_v2` panel, then runs residual coverage attribution on the fallback lane:

```
make check-compare-two-stage-panel-summaries

python3 ./scripts/compare_two_stage_panel_summaries.py \
  --baseline-panel-summary .tmp/panel_minimal_v2_2026-04-10_chr22_3anchor/summary.json \
  --candidate-panel-summary .tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor/summary.json \
  --output-dir .tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor/compare_vs_minimal_v2

python3 ./scripts/analyze_two_stage_coverage_attribution_panel.py \
  --panel-summary .tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor/summary.json \
  --candidate-label deferred_exact_minimal_v2_selective_fallback \
  --output-dir .tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor/coverage_attribution_panel

make check-summarize-two-stage-panel-decision

python3 ./scripts/summarize_two_stage_panel_decision.py \
  --compare-summary .tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor/compare_vs_minimal_v2/summary.json \
  --attribution-summary .tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor/coverage_attribution_panel/summary.json \
  --output-dir .tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor/panel_decision
```

- `scripts/compare_two_stage_panel_summaries.py` requires an exact selected-tile match between the two panel summaries and reports:
  - panel-level deltas for `top5_retention`, `top10_retention`, `score_weighted_recall`, `threshold_skipped_after_gate`, `threshold_batch_size_mean`, `threshold_batched_seconds`, and `refine_total_bp`
  - `difference_class` counts/transitions across the matched tiles
  - candidate-side `selective_fallback_*` totals, including non-empty selector candidate/blocker counters plus the dedicated non-empty trigger count, so the compare report shows whether fallback actually fired and which selector clause blocked sparse non-empty tasks
- `scripts/summarize_two_stage_panel_decision.py` merges the panel compare summary with the residual coverage-attribution summary and emits:
  - `recommended_next_step` (`non_empty_ambiguity_triggered_selective_fallback`, `refine_pad_merge_sweep`, `prefilter_coverage_expansion`, or `audit_inside_kept_window_classification`)
  - residual primary attribution classes for `overall`, `top5_missing`, `top10_missing`, and `score_weighted_missing`
  - selector diagnosis fields: `selector_candidate_tasks`, `selector_blocker_totals`, `dominant_selector_blocker`, `recommended_selector_ablation`
  - a compact fallback effectiveness summary keyed off the compare deltas plus `candidate_selective_fallback_totals`
- Narrow selector ablations can reuse the same selected panel tiles while injecting candidate-only env overrides:

```
make check-rerun-two-stage-panel-with-candidate-env

python3 ./scripts/rerun_two_stage_panel_with_candidate_env.py \
  --panel-summary .tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor_fastlane_nonempty/summary.json \
  --candidate-run-label deferred_exact_minimal_v2_selective_fallback \
  --candidate-env LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_SCORE_GAP=9 \
  --output-dir .tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor_fastlane_nonempty/rerun_score_gap_9
```

- `scripts/rerun_two_stage_panel_with_candidate_env.py` keeps the original tile selection fixed, reruns `legacy + candidate`, forwards candidate-only overrides through `--run-env`, and supports `--dry-run` for command preview before launching a real rerun.
- 当真实 rerun 把 `dominant_selector_blocker` 从 `max_kept_windows` 推到 `no_singleton_missing_margin` 之后，下一步不是继续盲调 gate，而是先做 candidate-class attribution + offline replay：

```
make check-analyze-two-stage-selector-candidate-classes
make check-replay-two-stage-non-empty-candidate-classes

python3 ./scripts/analyze_two_stage_selector_candidate_classes.py \
  --panel-summary .tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor_fastlane_nonempty_rerun_max_kept_windows_2/summary.json \
  --candidate-label deferred_exact_minimal_v2_selective_fallback \
  --max-kept-windows 2 \
  --non-empty-score-gap 6 \
  --singleton-override 85 \
  --output-dir .tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor_fastlane_nonempty_rerun_max_kept_windows_2/selector_candidate_classes

python3 ./scripts/replay_two_stage_non_empty_candidate_classes.py \
  --panel-summary .tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor_fastlane_nonempty_rerun_max_kept_windows_2/summary.json \
  --candidate-label deferred_exact_minimal_v2_selective_fallback \
  --max-kept-windows 2 \
  --non-empty-score-gap 6 \
  --singleton-override 85 \
  --strategy score_band_dominant \
  --strategy score_band_75_79 \
  --strategy score_band_lt_75 \
  --output-dir .tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor_fastlane_nonempty_rerun_max_kept_windows_2/candidate_class_replay
```

- `scripts/analyze_two_stage_selector_candidate_classes.py` reuses the panel summary + debug TSVs and reports:
  - which `no_singleton_missing_margin` tasks are blocked by the next candidate class (`support1_margin_present`, `support2`, `support3plus_low_support_or_margin`, `score_lt_85`, `covered_by_kept`, `other`)
  - a dedicated `score_lt_85_band_breakdown` for `80_84`, `75_79`, and `lt_75`
  - when `score_lt_85` stays dominant after a runtime expansion, an additional `score_lt_75_band_breakdown` for `70_74`, `65_69`, and `lt_65`
  - which classes actually explain the remaining missing legacy hits via `overall`, `top5_missing`, `top10_missing`, and `score_weighted_missing`
  - `recommended_next_candidate_class`, `recommended_score_lt_85_band`, and `recommended_score_lt_75_band`, so the next selector expansion can stay evidence-driven instead of widening multiple clauses at once
- On the pre-`minimal_v3` real panel, that breakdown resolved to:
  - `recommended_next_candidate_class=score_lt_85`
  - `recommended_score_lt_85_band=75_79`
  - `80_84` currently contributes `0` representative tasks and `0` missing-hit weight on the fixed selected tiles
- `scripts/replay_two_stage_non_empty_candidate_classes.py` keeps the same selected tiles and runs narrow offline ablations for candidate classes; by default it now focuses on the score-band follow-up (`score_band_dominant`, `score_band_75_79`, `score_band_lt_75`).
  - `predicted_*` fields in its `summary.json` / `summary.md` are coverage proxies derived from kept/rescued windows against legacy hits; they are not runtime-measured threshold-mode outputs.
  - On that pre-`minimal_v3` panel, `score_band_dominant` resolved to `75_79` and matched `score_band_75_79`: `predicted_rescued_task_count=286`, `delta_top10_retention=+0.1`, `delta_score_weighted_recall≈+0.0128`, with `top_hit_retention` unchanged.
  - `score_band_lt_75` improved only `score_weighted_recall` (`≈+0.0165`) while costing more rescued tasks/windows, so it stayed a comparison lane rather than the first runtime expansion target.
  - That historical replay answered the narrower question before touching runtime semantics: if we admitted one more candidate class, would `top5/top10` or `score_weighted_recall` move enough to justify a real selector change?
- `scripts/benchmark_two_stage_threshold_modes.py` now exposes the matching runtime prototype lane `deferred_exact_minimal_v3_scoreband_75_79`, which keeps `deferred_exact_minimal_v2_selective_fallback` as the baseline and adds only:
  - `LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_MAX_KEPT_WINDOWS=2`
  - `LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_SCORE_BAND_75_79=1`
  - the fixed selected-tiles real panel rerun against `deferred_exact_minimal_v2_selective_fallback` is now complete: `top_hit_retention` stayed `1.0`, `top5_retention` improved by `+0.0167`, `top10_retention` by `+0.0333`, `score_weighted_recall` by `≈+0.0185`, and `threshold_skipped_after_gate` / `threshold_batch_size_mean` stayed flat
  - the next step is analysis-first again, not another runtime edit:

```
python3 ./scripts/analyze_two_stage_selector_candidate_classes.py \
  --panel-summary .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/summary.json \
  --candidate-label deferred_exact_minimal_v3_scoreband_75_79 \
  --max-kept-windows 2 \
  --non-empty-score-gap 6 \
  --singleton-override 85 \
  --output-dir .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/selector_candidate_classes_lt75_breakdown

python3 ./scripts/replay_two_stage_non_empty_candidate_classes.py \
  --panel-summary .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/summary.json \
  --candidate-label deferred_exact_minimal_v3_scoreband_75_79 \
  --max-kept-windows 2 \
  --non-empty-score-gap 6 \
  --singleton-override 85 \
  --strategy score_band_lt_75_dominant \
  --strategy score_band_70_74 \
  --strategy score_band_65_69 \
  --strategy score_band_lt_65 \
  --output-dir .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/candidate_class_replay_lt75_breakdown
```

  - On the current `minimal_v3` panel, the residual recommendation tightens to `recommended_score_lt_85_band=lt_75` and `recommended_score_lt_75_band=70_74`.
  - The new replay confirms `70_74` is the strongest residual sub-band (`predicted_rescued_task_count=225`, `delta_score_weighted_recall≈+0.0071`), but **none** of `70_74 / 65_69 / lt_65` improves `top5/top10`; under a Top10-first objective, that means do **not** plan a `minimal_v4 score-band` runtime lane yet.
  - `minimal_v3` is therefore the current shortlist baseline; the next analysis step is **non-score-band candidate objects**, not a narrower score cut.
  - `scripts/analyze_two_stage_selector_candidate_classes.py` now also emits:
    - `aggregate.rule_strand_object_breakdown` / `per_tile[*].rule_strand_object_breakdown`
    - `recommended_next_candidate_object`
    - this tracks uncovered rejected windows grouped by `(rule, strand)` and measures how much of the residual `overall / top5 / top10 / score_weighted` miss they explain
  - `scripts/replay_two_stage_non_empty_candidate_classes.py` now supports two explicit object strategies:
    - `rule_strand_strongest`: per `no_singleton_missing_margin` task, rescue the strongest uncovered `(rule, strand)` object
    - `rule_strand_dominant`: an offline-only upper bound that picks the `(rule, strand)` object with the largest attributed `top10_missing`, then `score_weighted_missing`, then `overall_missing`
  - the intended follow-up is:

```
python3 ./scripts/analyze_two_stage_selector_candidate_classes.py \
  --panel-summary .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/summary.json \
  --candidate-label deferred_exact_minimal_v3_scoreband_75_79 \
  --max-kept-windows 2 \
  --non-empty-score-gap 6 \
  --singleton-override 85 \
  --output-dir .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/selector_candidate_objects_rule_strand

python3 ./scripts/replay_two_stage_non_empty_candidate_classes.py \
  --panel-summary .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/summary.json \
  --candidate-label deferred_exact_minimal_v3_scoreband_75_79 \
  --max-kept-windows 2 \
  --non-empty-score-gap 6 \
  --singleton-override 85 \
  --strategy rule_strand_strongest \
  --strategy rule_strand_dominant \
  --output-dir .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/candidate_object_replay_rule_strand
```

  - decision rule stays narrow:
    - if `rule_strand_strongest` also improves `top5/top10` without eating back skip/batch gains, only then is a new runtime plan justified
    - if only `rule_strand_dominant` improves, treat it as an attribution/proxy result rather than a runtime-ready selector
    - if neither improves `top5/top10`, stop expanding the selector and keep `minimal_v3` as the experimental shortlist baseline
  - the next narrower follow-up no longer changes the candidate family; it only swaps the **per-task rejected-window proxy** inside the same `no_singleton_missing_margin` task set:

```
python3 ./scripts/replay_two_stage_non_empty_candidate_classes.py \
  --panel-summary .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/summary.json \
  --candidate-label deferred_exact_minimal_v3_scoreband_75_79 \
  --max-kept-windows 2 \
  --non-empty-score-gap 6 \
  --singleton-override 85 \
  --strategy task_proxy_score_x_bp \
  --strategy task_proxy_score_x_support \
  --output-dir .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/candidate_object_replay_task_proxy
```

  - `task_proxy_score_x_bp` picks the uncovered rejected window with the largest `best_seed_score * window_bp`
  - `task_proxy_score_x_support` picks the uncovered rejected window with the largest `best_seed_score * support_count`
  - on the current real `minimal_v3` panel, both proxies still fail the Top10-first gate:
    - `task_proxy_score_x_bp`: `predicted_rescued_task_count=382`, `delta_top5=0`, `delta_top10=0`, `delta_score_weighted_recall≈+0.01726`
    - `task_proxy_score_x_support`: `predicted_rescued_task_count=382`, `delta_top5=0`, `delta_top10=0`, `delta_score_weighted_recall≈+0.01657`
  - because neither proxy improves `top5/top10`, these strategies are evidence that selector expansion is likely exhausted on the current `minimal_v3` shortlist baseline; they do **not** justify a new runtime lane.
  - the next step therefore moves **up one level** from per-window selector expansion to an **offline task-level exact rerun upper bound** on the same fixed selected tiles:

```
python3 ./scripts/rerun_two_stage_panel_with_candidate_env.py \
  --panel-summary .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/summary.json \
  --candidate-run-label deferred_exact \
  --output-dir .tmp/panel_deferred_exact_2026-04-14_chr22_3anchor_task_level_rerun

python3 ./scripts/analyze_two_stage_task_ambiguity.py \
  --baseline-panel-summary .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/summary.json \
  --rescue-panel-summary .tmp/panel_deferred_exact_2026-04-14_chr22_3anchor_task_level_rerun/summary.json \
  --baseline-label deferred_exact_minimal_v3_scoreband_75_79 \
  --rescue-label deferred_exact \
  --output-dir .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_ambiguity_deferred_exact

python3 ./scripts/replay_two_stage_task_level_rerun.py \
  --analysis-summary .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_ambiguity_deferred_exact/summary.json \
  --budget 8 --budget 16 --budget 32 --budget 64 \
  --output-dir .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_rerun_replay_deferred_exact
```

  - `scripts/analyze_two_stage_task_ambiguity.py` joins baseline `minimal_v3` tasks to the fixed-tile `deferred_exact` rerun using `(fragment_index, fragment_start/end_in_seq, reverse_mode, parallel_mode, strand, rule)` as the stable task key; on real panels, fragment-only keys collide across rule/strand task splits.
  - it reports both:
    - baseline ambiguity features (`inside_rejected_window` top5/top10 counts and score-weight mass by task)
    - rescue-gain features (which baseline-missing legacy hits would be recovered if that one task were rerun via `deferred_exact`)
    - `deployable_features`, derived only from baseline `minimal_v3` debug TSV / report telemetry:
      - `kept_window_count`, `uncovered_rejected_window_count`, `uncovered_rejected_bp_total`, `max_uncovered_rejected_window_bp`
      - `best_kept_score`, `best_rejected_score`, `best_score_gap`
      - `rejected_score_sum`, `rejected_score_mean`, `rejected_score_top3_sum`
      - `rejected_score_x_bp_sum`, `rejected_score_x_support_sum`
      - `score_band_counts` / `score_band_bp_totals` over `ge85 / 80_84 / 75_79 / 70_74 / lt70`
      - `support_bin_counts` over `support1 / support2 / support3plus`
      - `reject_reason_counts`, `reject_reason_bp_totals`
      - `rule_diversity_count`, `strand_diversity_count`, `rule_strand_object_count`, `rule_strand_entropy`
      - `tile_rank_by_best_rejected_score`, `tile_rank_by_rejected_score_x_bp_sum`
      - `selective_fallback_selected_window_count`
  - on the current real `minimal_v3` panel, the task-level upper bound resolves to:
    - `eligible_task_count=4151`
    - `rescue_gain_task_count=355`
    - `false_positive_ambiguity_task_count=0`
  - `scripts/replay_two_stage_task_level_rerun.py` now supports:
    - `--ranking oracle_rescue_gain`
    - `--ranking deployable_sparse_gap_v1`
    - `--ranking deployable_support_pressure_v1`
  - every replay budget now also reports `oracle_overlap` (`precision / recall / jaccard`) against the same-budget `oracle_rescue_gain` task set.
  - `oracle_rescue_gain` continues to define the offline upper bound and replays a small rerun-budget frontier without touching runtime semantics:
    - budget `8`: `top_hit_retention=1.0`, `top5=0.6` (flat), `top10=0.8` (`+0.1`), `score_weighted_recall≈+0.00264`, `delta_refine_total_bp_total=+3735`
    - budget `16`: `top_hit_retention=1.0`, `top5=0.6` (flat), `top10=0.8` (`+0.1`), `score_weighted_recall≈+0.00837`, `delta_refine_total_bp_total=+8097`
    - budget `32`: `top_hit_retention=1.0`, `top5=0.6` (flat), `top10=0.8` (`+0.1`), `score_weighted_recall≈+0.01583`, `delta_refine_total_bp_total=+19915`
    - budget `64`: `top_hit_retention=1.0`, `top5=0.6` (flat), `top10=0.8` (`+0.1`), `score_weighted_recall≈+0.02577`, `delta_refine_total_bp_total=+38185`
  - this is the first post-selector analysis that **does** recover head quality (`top10`) on the current `minimal_v3` shortlist baseline, but the gain saturates early and still does not move `top5`.
  - practical implication:
    - do **not** go back to broader selector tuning or `pad/merge`
    - do **not** promote a new runtime lane from this result alone
    - the next evidence-driven step is an oracle-free, deployable **task-level ambiguity trigger** that tries to approximate the budget-8/16 frontier from `minimal_v3` observables
  - the first oracle-free heuristic calibration is now complete:
    - outputs:
      - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_ambiguity_deferred_exact_deployable/summary.json`
      - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_rerun_replay_deferred_exact_deployable_sparse_gap_v1/summary.json`
      - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_rerun_replay_deferred_exact_deployable_support_pressure_v1/summary.json`
    - `deployable_sparse_gap_v1` fails to approximate the oracle frontier:
      - budget `8`: `delta_top10=0`, `delta_score_weighted_recall≈+0.00095`, `delta_refine_total_bp_total=+7189`, `oracle_overlap_jaccard=0.0`
      - budget `16`: `delta_top10=0`, `delta_score_weighted_recall≈+0.00142`, `delta_refine_total_bp_total=+12093`, `oracle_overlap_jaccard≈0.0323`
    - `deployable_support_pressure_v1` also fails:
      - budget `8`: `delta_top10=0`, `delta_score_weighted_recall≈+0.00156`, `delta_refine_total_bp_total=+9382`, `oracle_overlap_jaccard=0.0`
      - budget `16`: `delta_top10=0`, `delta_score_weighted_recall≈+0.00273`, `delta_refine_total_bp_total=+20015`, `oracle_overlap_jaccard≈0.0323`
    - because neither heuristic clears the budget-16 promotion gate, there is no runtime confirmation run for these oracle-free triggers yet; the correct next step is richer deployable feature design / calibrated trigger search, not another runtime lane.

```
python3 ./scripts/analyze_two_stage_task_ambiguity.py \
  --baseline-panel-summary .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/summary.json \
  --rescue-panel-summary .tmp/panel_deferred_exact_2026-04-14_chr22_3anchor_task_level_rerun/summary.json \
  --baseline-label deferred_exact_minimal_v3_scoreband_75_79 \
  --rescue-label deferred_exact \
  --output-dir .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_ambiguity_deferred_exact_deployable_v2

python3 ./scripts/search_two_stage_task_trigger_rankings.py \
  --analysis-summary .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_ambiguity_deferred_exact_deployable_v2/summary.json \
  --budget 8 --budget 16 \
  --target-budget 16 \
  --promotion-min-delta-top10 0.08 \
  --promotion-min-delta-score-weighted-recall 0.006 \
  --promotion-max-delta-refine-total-bp 10121.25 \
  --output-dir .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_trigger_ranking_search_v1
```

  - calibrated trigger search v1 is now complete:
    - richer deployable analysis output:
      - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_ambiguity_deferred_exact_deployable_v2/summary.json`
    - ranking search output:
      - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_trigger_ranking_search_v1/summary.json`
    - `scripts/search_two_stage_task_trigger_rankings.py` evaluates four oracle-free candidate libraries against the same `budget 8/16` offline replay frontier:
      - rule-based: `rule_score_mass_gap_v2`, `rule_support_reason_pressure_v2`
      - learned leave-anchor-out ranking: `lr_budget16_rank_v1`, `hgb_budget16_rank_v1`
    - promotion gate:
      - `delta_top_hit_retention == 0.0`
      - `delta_top10_retention >= 0.08`
      - `delta_score_weighted_recall >= 0.006`
      - `delta_refine_total_bp_total <= 10121.25`
    - real fixed-panel result:
      - no candidate clears the budget-16 promotion gate, so `recommended_candidate=null` and there is no runtime confirm
      - `rule_score_mass_gap_v2` gets the best oracle overlap (`jaccard≈0.0667`) but still has `delta_top10=0`, `delta_score_weighted_recall≈+0.00224`, `delta_refine_total_bp_total=+11242`
      - `rule_support_reason_pressure_v2` gets the highest weighted-recall among this library (`≈+0.00224`) but with `delta_top10=0`, `delta_refine_total_bp_total=+20689`, `oracle_overlap_jaccard≈0.0323`
      - `hgb_budget16_rank_v1` is the cheapest learned candidate (`delta_refine_total_bp_total=+6956`) but still only reaches `delta_score_weighted_recall≈+0.00169` and `delta_top10=0`
      - `lr_budget16_rank_v1` stays below both the oracle overlap and the weighted-recall frontier (`delta_score_weighted_recall≈+0.00106`, `oracle_overlap_jaccard=0.0`)
    - practical implication:
      - calibrated ranking search confirms that the current deployable task-trigger surface still does **not** recover head quality (`top10`) without oracle task selection
      - stop here rather than inventing more trigger names or another runtime lane
      - freeze `minimal_v3` as the experimental shortlist baseline and `budget16 oracle rerun` as the offline/runtime upper bound
      - next work should shift to stronger exact rescue design or the separate exact-safe mainline, not more oracle-free trigger tuning
  - once that offline frontier exists, the matching runtime prototype can be rerun on the identical fixed selected tiles by materializing per-tile task lists and injecting them into the new benchmark lanes:

```
python3 ./scripts/rerun_two_stage_panel_task_rerun_runtime.py \
  --panel-summary .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/summary.json \
  --replay-summary .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_rerun_replay_deferred_exact/summary.json \
  --budget 16 \
  --output-dir .tmp/panel_minimal_v3_task_rerun_budget16_runtime

python3 ./scripts/compare_two_stage_panel_summaries.py \
  --baseline-panel-summary .tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/summary.json \
  --candidate-panel-summary .tmp/panel_minimal_v3_task_rerun_budget16_runtime/summary.json \
  --output-dir .tmp/panel_minimal_v3_task_rerun_budget16_runtime/compare_vs_minimal_v3
```

  - `scripts/rerun_two_stage_panel_task_rerun_runtime.py` keeps the tile set fixed, writes one selected-task TSV per tile from the offline replay summary, and reruns `legacy + deferred_exact_minimal_v3_task_rerun_budget{8,16}` without rediscovering micro-anchors.
  - implementation note:
    - per-tile selected-task TSVs must live outside each tile `work-dir`; `benchmark_two_stage_threshold_modes.py` clears its per-tile work directory on startup, so writing TSVs inside `tiles/...` will delete the injected input before the candidate run starts
  - the fixed-tile real runtime reruns are now complete:
    - budget `8`
      - outputs:
        - `.tmp/panel_minimal_v3_task_rerun_budget8_runtime_2026-04-14/summary.json`
        - `.tmp/panel_minimal_v3_task_rerun_budget8_runtime_2026-04-14/compare_vs_minimal_v3/summary.json`
      - runtime totals: `selected/effective tasks=8/8`, `added_windows=14`, `added_bp=3735`, `task_rerun_seconds≈3.31`
      - tile-mean deltas vs `minimal_v3`: `top_hit=+0.0`, `top5≈+0.0833`, `top10≈+0.0583`, `score_weighted_recall≈+0.00317`, `threshold_skipped_after_gate=+0.0`, `threshold_batch_size_mean=+0.0`
    - budget `16`
      - outputs:
        - `.tmp/panel_minimal_v3_task_rerun_budget16_runtime_2026-04-14/summary.json`
        - `.tmp/panel_minimal_v3_task_rerun_budget16_runtime_2026-04-14/compare_vs_minimal_v3/summary.json`
      - runtime totals: `selected/effective tasks=16/16`, `added_windows=33`, `added_bp=8097`, `task_rerun_seconds≈8.23`
      - tile-mean deltas vs `minimal_v3`: `top_hit=+0.0`, `top5≈+0.0833`, `top10≈+0.0667`, `score_weighted_recall≈+0.00760`, `threshold_skipped_after_gate=+0.0`, `threshold_batch_size_mean=+0.0`
  - runtime-vs-offline replay conclusion:
    - for both budgets, the runtime totals match the offline replay aggregate exactly on `rerun_task_count`, `added_window_count`, and `delta_refine_total_bp_total`
    - the compare summary above is a tile-mean view, while the offline replay summary is a panel-global aggregate; treat `task count / added windows / added bp` as the exact fidelity check, and treat `top10 / score_weighted_recall` as the primary quality-direction signal
    - with that caveat, the runtime prototype confirms the intended direction: `top_hit` stays stable, `top10` and `score_weighted_recall` improve, and skip/batch telemetry stays flat enough to keep the lane experimental-but-viable
  - local checks:
    - `make check-analyze-two-stage-task-ambiguity`
    - `make check-replay-two-stage-task-level-rerun`
    - `make check-search-two-stage-task-trigger-rankings`
    - `make check-two-stage-task-rerun-runtime`
- Example quality-gated sweep:

```
python3 ./scripts/benchmark_fasim_throughput_sweep.py \
  --dna .tmp/ucsc/hg38/hg38_chr22_10510001_50000.fa \
  --device-sets 0 0,1 \
  --extend-threads 1,4,8,16 \
  --topk-values 64,128,256 \
  --suppress-bp-values 0,1,5 \
  --min-relaxed-recall 0.90 \
  --min-top-hit-retention 0.75
```

Batch throughput micro-benchmark (generates a multi-fasta with many entries and compares CPU vs CUDA):

```
make benchmark-fasim-batch
# or:
python3 ./scripts/benchmark_fasim_batch_throughput.py --entries 256
```

Hybrid tuning example (trade speed for accuracy in `LONGTARGET_SIM_FAST=1` mode):

```
LONGTARGET_SIM_FAST_UPDATE_BUDGET=2 make benchmark-sample-cuda-vs-fasim
```

## Running 
A simple case is:

```
./LongTarget -f1 testDNA.fa -f2 H19.fa -r 0
```

A more complex case is:

```
./LongTarget -f1 testDNA.fa -f2 H19.fa -r 0 -O /home/test/example -c 6000 -i 70 -S 1.0 -ni 25 -na 1000 -pc 1 -pt -500 -ds 10 -lg 60
```

In this command, output path is /home/test/example, cut sequence's length is 6000, identity is 70%, stability is 1.0, ntMin is 25 nt, ntMax is 1000 nt, penaltyC is 1, penaltyT is -500, distance between TFOs is 10, min length of triplexes is 60 (for more details about parameters, visit the website http://lncRNA.smu.edu.cn).

## Help information
Here is a brief explanation of the command line arguments:

```
Options   Parameters      Functions
f1   DNA sequence file  A string, indicate the DNA sequence file name.
f2   RNA sequence file  A string, indicate the RNA sequence file name.
r    rules              An integer, indicate base-pairing rules, "0" indicates all rules.
O    Output path        A string, indicate the directory into which the results are outputted.
c    Cutlength          An integer, indicate the length of each segment, the default value is 5000.
i    identity           An integer, indicate the criterion of alignment output, the default value is 60.
S    stability          A floating point, indicate the criterion of base-pairing, the default value is 1.0.
ni   ntmin              An integer, indicate the min length of triplexes, the default value is 20.
na   ntmax              An integer, indicate the max length of triplexes, the default is 100000 but is rarely used.
pc   penaltyC           An integer, indicate penalty, the default value is 0.
pt   penaltyT           An integer, indicate penalty, the default value is -1000.
ds   c_dd               An integer, indicate the distance between TFOs, the default value is 15.
lg   c_length           An integer, indicate the min length of triplexes, the default value is 50.
```

## Time consumption
This depends on the number and length of lncRNAs and the length of genome regions. The expected running time for the H19 demo should be no more than ten minutes even on a normal desktop computer.

# Demo
## Inputs and their formats
H19.fa and testDNA.fa in the directory give a demo example. To obtain more details, go to our website http://lncRNA.smu.edu.cn and/or check files in the "examples" subdirectory.

The H19.fa indicates that the lncRNA sequence file should have a title line in the format ">species_lncRNA" without any space within letters, and the lncRNA sequence should be in a new line.

The testDNA.fa indicates that the DNA sequence file should have a title line in the format ">species|chr|start-end" without any space between letters, and the DNA sequence should be in a new line.

## Results
The results include three files whose filenames ending with: (1)*TFOsorted, (2)*TFOclass1,
(3)*TFOclass2. The TFOsorted file contains the details of all triplexes, the TFOclass1 file contains the TTS distribution of TFO1 in the genome region, and the TFOclass2 file contains the TTS distribution of TFO2.

## Example datasets
An example dataset giving detailed results of examples is given in the subdirectory "examples".

# Instructions for use
## How to run LongTarget on your data
To run LongTarget using the web service, both lncRNAs and genome sequences are available in the database LongMan. To run it as a standalone program, you should obtain lncRNAs and genome sequences from websites such as https://www.gencodegenes.org/ , http://genome.ucsc.edu/ , http://www.noncode.org/ , and http://asia.ensembl.org/index.html .

## Bug reports
Please send comments and bug reports to: zhuhao@smu.edu.cn.

# Other codes
The [DatabaseScripts](./DatabaseScripts) subdirectory contains the scripts written in Python and Perl for building LongMan database. The web application of LongMan is available at http://lncrna.smu.edu.cn/show/info .

# License
The program is distributed under the AGPLv3 license.

# Citation
