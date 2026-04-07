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
- `LONGTARGET_PREFILTER_BACKEND=sim|prealign_cuda`: prefilter backend (default: `sim`)
- `LONGTARGET_PREFILTER_TOPK=N`: number of prefilter seeds per task (default: 8; `sim` backend is effectively capped by `K=50` in `sim.h`; `prealign_cuda` supports up to 256)
- `LONGTARGET_PREFILTER_PEAK_SUPPRESS_BP=N`: only for `prealign_cuda` backend; suppress peaks within N bp (default: 5)
- `LONGTARGET_PREFILTER_SCORE_FLOOR_DELTA=N`: only for `prealign_cuda` backend; keep peaks down to `minScore - delta` (default: 0)
- `LONGTARGET_REFINE_PAD_BP=N`: bp padding added to each seed window before refine (default: 64)
- `LONGTARGET_REFINE_MERGE_GAP_BP=N`: merge adjacent windows when gap ≤ N (default: 32)

Notes:
- `prealign_cuda` typically benefits from a larger `LONGTARGET_PREFILTER_TOPK` (e.g. 64–256) to recover more windows; higher values trade speed for recall.

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
- `benchmark.sim_initial_scan_sync_wait_seconds`: synchronization wait time currently attributed to the initial scan handoff path
- `benchmark.sim_initial_reduce_chunks_total` / `benchmark.sim_initial_reduce_chunks_replayed_total` / `benchmark.sim_initial_reduce_chunks_skipped_total` / `benchmark.sim_initial_reduce_summaries_replayed_total`: ordered-replay chunk statistics from the experimental initial reducer
- `benchmark.sim_initial_run_summary_pipeline_seconds`: subtotal of the run-summary grouping stages (`hash_reduce + segmented_reduce + segmented_compact + topk`) for profiler-guided initial-scan tuning
- `benchmark.sim_initial_hash_reduce_seconds` / `benchmark.sim_initial_segmented_reduce_seconds`: time spent in the optional hash or segmented grouping stage inside the experimental initial reducer
- `benchmark.sim_initial_segmented_compact_seconds`: GPU time spent compacting the segmented safe-store candidates after the grouped reduce (device scan + compact on the `segmented` backend)
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

These ratios are additive to the existing `projected_*` fields and remain optional so older benchmark logs still parse unchanged.

Validation helpers:

- `make check-benchmark-telemetry`: verify benchmark stderr includes the expected telemetry fields
- `make check-sim-cuda-region-docs`: verify this README and `EXACT_SIM_PROGRESS.md` still document the SIM CUDA region exactness constraints
- `make check-sim-initial-cuda-merge`: verify the coalesced CUDA initial-scan host merge matches per-event replay while reducing logical host updates
- `make check-project-whole-genome-runtime`: verify the projection script preserves backward compatibility and emits the optional whole-genome ratios when the source telemetry is present

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

Throughput sweep helper (device set × `FASIM_EXTEND_THREADS`, with one exact baseline run reused across the matrix):

```
make benchmark-fasim-throughput-sweep
# or:
python3 ./scripts/benchmark_fasim_throughput_sweep.py --device-sets 0 0,1 --extend-threads 1,4,8,16,20
make check-fasim-throughput-sweep
```

- The sweep currently keeps threshold policy and prealign knobs fixed (`fasim_peak80`, `TOPK=64`, `suppress_bp=5`) and only sweeps device placement plus CPU extend/output threads.
- `report.json` records the exact baseline, each throughput configuration, overlap/score deltas (including `per_output_comparisons`), and the fastest configuration selected by wall time.

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
