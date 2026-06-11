#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
RUNNER_DOC="$ROOT/docs/fasim_sharded_runner.md"
BRIDGE_DOC="$ROOT/docs/fasim_gasal2_longtarget_bridge.md"
OUTPUT_CONTRACT_DOC="$ROOT/docs/fasim_gasal2_top5_output_contract.md"
MAKEFILE="$ROOT/Makefile"

for path in \
  "$DOC" \
  "$RUNNER_DOC" \
  "$BRIDGE_DOC" \
  "$OUTPUT_CONTRACT_DOC" \
  "$ROOT/docs/fasim_gasal2_top5_scoreinfo_milestone.md" \
  "$ROOT/docs/fasim_gasal2_top5_output_contract.md" \
  "$ROOT/docs/fasim_gasal2_top5_broader_validation.md" \
  "$ROOT/docs/fasim_gasal2_top5_product_readiness.md" \
  "$ROOT/docs/fasim_gasal2_top5_recommended_runtime.md" \
  "$ROOT/docs/fasim_gasal2_scoreinfo_scoped_milestone.md" \
  "$ROOT/docs/fasim_gasal2_scoreinfo_scoped_milestone_rollup.md" \
  "$ROOT/docs/fasim_gasal2_malat1_two_contract_product_readiness.md" \
  "$ROOT/docs/fasim_gasal2_malat1_two_contract_recommended_runtime.md" \
  "$ROOT/docs/fasim_gasal2_broad_path_architecture_gate.md" \
  "$ROOT/docs/fasim_gasal2_long_query_boundary.md" \
  "$ROOT/scripts/check_fasim_gasal2_formal_makefile_gate.sh" \
  "$ROOT/scripts/check_fasim_gasal2_top5_scoreinfo_milestone.sh" \
  "$ROOT/scripts/check_fasim_gasal2_top5_scoreinfo_meg3_grouped_result.sh" \
  "$ROOT/scripts/check_fasim_gasal2_top5_wrapper_meg3_grouped_result.sh" \
  "$ROOT/scripts/check_fasim_sharded_gasal2_top5_prune_runner.sh" \
  "$ROOT/scripts/check_fasim_gasal2_column_pruned_preset_top5_matrix.sh" \
  "$ROOT/scripts/check_fasim_gasal2_top5_activation_contract.py" \
  "$ROOT/scripts/check_fasim_gasal2_topk_lite_wrapper_contract.sh" \
  "$ROOT/scripts/check_fasim_gasal2_top5_lowercase_input.sh" \
  "$ROOT/scripts/check_fasim_gasal2_top5_binary_guard.sh" \
  "$ROOT/scripts/check_fasim_gasal2_formal_preset_examples.sh" \
  "$ROOT/scripts/check_fasim_top5_gasal2_gpu_scoreinfo_default_off.sh" \
  "$ROOT/scripts/check_fasim_top5_gasal2_gpu_scoreinfo_env.sh" \
  "$ROOT/scripts/check_fasim_exact_scoreinfo_gpu_examples_gate.sh" \
  "$ROOT/scripts/check_fasim_gasal2_top5_broader_validation.sh" \
  "$ROOT/scripts/check_fasim_gasal2_top5_product_readiness.sh" \
  "$ROOT/scripts/check_fasim_gasal2_top5_recommended_runtime.sh" \
  "$ROOT/scripts/check_fasim_gasal2_long_query_segmented_no_last_scaling_result.sh" \
  "$ROOT/scripts/check_fasim_gasal2_long_query_exact_tile_candidate_equivalence_result.sh" \
  "$ROOT/scripts/check_fasim_gasal2_long_query_exact_tile_overlap_result.sh" \
  "$ROOT/scripts/check_fasim_long_query_exact_column_scoreinfo_shadow.sh" \
  "$ROOT/scripts/check_fasim_long_query_exact_column_scoreinfo_shadow_smem_optin.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_shadow_skeleton.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_shadow_active.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_shadow_mismatch_detail.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_shadow_gpu_minscore.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_shadow.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_trust.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_runner.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_shadow_gpu_minscore_hot.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_fused_minscore_prototype.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_fused_minscore_boundary.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_design.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_realpath_prototype.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_realpath_trust.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_trust_targets.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_trust_runner.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_trust_group32_runner.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_trust_group32_audited_runner.sh" \
  "$ROOT/scripts/check_fasim_long_query_streaming_scoreinfo_trust_runner_real.sh" \
  "$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_hot.sh" \
  "$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_realpath.sh" \
  "$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_realpath_trust.sh" \
  "$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_malat1_full_trust.sh" \
  "$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_neat1_trust.sh" \
  "$ROOT/scripts/characterize_fasim_long_query_streaming_scoreinfo_neat1_first64_trust.sh" \
  "$ROOT/docs/fasim_long_query_streaming_scoreinfo_design.md" \
  "$ROOT/docs/fasim_gasal2_long_query_exact_tile_candidate_equivalence.md" \
  "$ROOT/docs/fasim_gasal2_long_query_exact_tile_overlap_probe.md" \
  "$ROOT/docs/fasim_long_query_exact_column_scoreinfo_shadow.md" \
  "$ROOT/scripts/check_fasim_gasal2_scoreinfo_completion_gap.sh" \
  "$ROOT/scripts/check_fasim_gasal2_malat1_two_contract_product_readiness.sh" \
  "$ROOT/scripts/check_fasim_gasal2_malat1_two_contract_recommended_runtime.sh" \
  "$ROOT/scripts/check_fasim_gasal2_broad_path_architecture_gate.sh" \
  "$ROOT/scripts/check_fasim_gasal2_broad_scoreinfo_consumer_triplex_export.sh" \
  "$ROOT/scripts/check_fasim_gasal2_broad_scoreinfo_attempt_planner.sh" \
  "$ROOT/scripts/check_fasim_gasal2_broad_replacement_consumer_shadow.sh" \
  "$ROOT/scripts/check_fasim_gasal2_malat1_tfosorted_equivalence_evidence.sh" \
  "$ROOT/scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime.sh" \
  "$ROOT/docs/fasim_gasal2_replacement_consumer_shadow_requirements.md" \
  "$ROOT/scripts/check_fasim_gasal2_replacement_consumer_shadow_requirements.sh" \
  "$ROOT/scripts/check_fasim_gasal2_replacement_consumer_shadow_env.sh" \
  "$ROOT/scripts/check_fasim_gasal2_replacement_consumer_shadow_runtime_smoke.sh" \
  "$ROOT/docs/fasim_gasal2_score_prepass_state_machine_characterization.md" \
  "$ROOT/scripts/characterize_fasim_gasal2_score_prepass_state_machine_consumer.sh" \
  "$ROOT/scripts/check_fasim_gasal2_score_prepass_state_machine_characterization.sh" \
  "$ROOT/docs/fasim_gasal2_score_prepass_state_machine_trust.md" \
  "$ROOT/scripts/check_fasim_gasal2_score_prepass_state_machine_trust.sh" \
  "$ROOT/scripts/check_fasim_gasal2_score_prepass_state_machine_trust_runtime_smoke.sh" \
  "$ROOT/scripts/check_fasim_gasal2_scoreinfo_scoped_milestone_rollup.sh" \
  "$ROOT/docs/fasim_gasal2_emission_only_consumer_debug.md" \
  "$ROOT/scripts/check_fasim_gasal2_emission_only_consumer_debug.sh" \
  "$ROOT/docs/fasim_gasal2_scoring_parameter_matrix.md" \
  "$ROOT/scripts/check_fasim_gasal2_scoring_parameter_matrix.sh" \
  "$ROOT/docs/fasim_gasal2_cpu_authority_candidate_coverage_plan.md" \
  "$ROOT/scripts/check_fasim_gasal2_cpu_authority_candidate_coverage_plan.sh" \
  "$ROOT/scripts/check_fasim_gasal2_full_goal_decision.sh"; do
  if [[ ! -s "$path" ]]; then
    echo "missing current-state dependency: $path" >&2
    exit 1
  fi
done

python3 - "$DOC" "$RUNNER_DOC" "$BRIDGE_DOC" "$OUTPUT_CONTRACT_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

doc = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
runner_doc = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
bridge_doc = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
output_contract_doc = " ".join(Path(sys.argv[4]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

required_doc = [
    "current milestone for the scoreInfo/preAlign GPU/GASAL2 line",
    "not completion of the full replacement goal",
    "Current short-query/H19 GASAL2 top5 scoreInfo/preAlign: go as a top5-only artifact path",
    "MEG3 tiny-region grouped runner/wrapper path: go",
    "Long-query MALAT1 has a MALAT1-like, group32, external-digest-gated scoped trust profile",
    "MALAT1 two-contract group32 audited first256",
    "digest = 7f553b74ae31bed4cb7b9c312a188e2df19627ac4882c7ad7ac484d65b004a4e",
    "tasks = 80,640",
    "two_contract_used = 80,640",
    "realpath_used = 80,640",
    "two_contract_fallbacks = 0",
    "two_contract_score_mismatches = 0",
    "two_contract_min_score_mismatches = 0",
    "two_contract_scoreinfo_mismatches = 0",
    "realpath_fallbacks = 0",
    "gpu_scoreinfo_groups = 1,434,844",
    "baseline runner wall = 1058.944629s",
    "candidate runner wall = 1015.698961s",
    "candidate_vs_baseline = 1.042577x",
    "resume_audited = true",
    "check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256",
    "Long-query NEAT1 remains performance no-go",
    "not a broad long-query real path",
    "current best remains marginal",
    "formal preset is top5-only contract",
    "--gasal2-top5-column-pruned-scoreinfo",
    "FASIM_TOP5_GASAL2_GPU_SCOREINFO=1",
    "FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK=64",
    "FASIM_PREALIGN_CUDA_MAX_TASKS=16384",
    "FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK=512",
    "FASIM_OUTPUT_TOPK_LITE=5",
    "chr21+chr22 formal result",
    "decision = top5_artifact_go",
    "active_path_runs = 1/1",
    "top5_clean_runs = 1/1",
    "exact scoreInfo GPU batches = 49",
    "exact scoreInfo GPU tasks = 778,848",
    "GASAL2 requests = 43,637,966",
    "GASAL2 traceback requests = 13,701,121",
    "fallback/overflow = 0 / 0",
    "CPU worker wall sum = 4565.987188s",
    "formal worker wall sum = 113.810705s",
    "speedup = 40.119136x",
    "does not prove full lite-output equivalence",
    "MEG3 grouped result",
    "--group-target-records 32",
    "group_target_records = 32",
    "grouped_shard_count = 17",
    "speedup = 1.939275x",
    "not chunking, not overlap",
    "GASAL2_MAX_QUERY_LEN=2812",
    "FASIM_ALIGN_GASAL2_MAX_QUERY_LEN=2812",
    "MEG3 query_len=1582",
    "MALAT1 query_len=8708",
    "NEAT1 query_len=22767",
    "GASAL2 selected/expanded segment traceback: no-go for real path",
    "FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_EXPANDED_SEGMENT_TRACEBACK_SHADOW=1",
    "expanded_segment_traceback_shadow_required_max_len = 22,767",
    "expanded_segment_traceback_shadow_required_over_gasal2_limit = 21,991",
    "selected-segment traceback is not equivalent",
    "full-query traceback requirement for many attempts",
    "long-query guarded CPU fallback",
    "malat1_first8 speedup=1.009996x",
    "malat1_first16 speedup=1.029101x",
    "malat1_first32 speedup=1.031832x",
    "malat1_first64 speedup=1.034623x",
    "malat1_first128 speedup=1.038017x",
    "1.0 < speedup < 1.1",
    "not enough to justify long-query production output",
    "single-pass topN scoreInfo probe",
    "legacy_score_gpu_requests = 0",
    "exact_scoreinfo_gpu_batches = 0",
    "topN=64 changes the nt-score top5",
    "topN=128/256 also change stability",
    "FASIM_TOP5_GASAL2_SINGLE_PASS_TOPN=1 is not recommended",
    "not full Fasim replacement",
    "not `aligner.Align()` replacement",
    "not GPU endpoint/CIGAR/traceback authority",
    "not universal scoreInfo/preAlign replacement",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FUSED_MINSCORE_SHADOW=1",
    "first default-off prototype now exists",
    "MALAT1 first8 fused boundary:",
    "fused_minscore_score_mismatches = 97",
    "fused_minscore_min_score_mismatches = 97",
    "scoreinfo_mismatches = 92",
    "not the same column-max contract",
    "cannot be promoted",
    "two-contract bridge",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW=1",
    "two_contract_bridge_shadow_active",
    "make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-shadow",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST=1",
    "two_contract_bridge_trust_active",
    "make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-trust",
    "--long-query-streaming-scoreinfo-gpu-two-contract-trust",
    "long_query_streaming_scoreinfo_gpu_two_contract_trust_experimental_v1",
    "make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-runner",
    "make check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design",
    "make check-fasim-gasal2-scoreinfo-current-state",
    "make check-fasim-gasal2-formal-makefile-gate",
    "make check-fasim-gasal2-top5-scoreinfo-milestone-result",
    "make check-fasim-gasal2-top5-scoreinfo-meg3-grouped-result",
    "make check-fasim-gasal2-top5-wrapper-meg3-grouped-result",
    "make check-fasim-sharded-gasal2-top5-prune-runner",
    "make check-fasim-gasal2-column-pruned-preset-top5-matrix",
    "make check-fasim-gasal2-top5-activation-contract",
    "make check-fasim-gasal2-topk-lite-wrapper-contract",
    "make check-fasim-gasal2-top5-lowercase-input",
    "make check-fasim-gasal2-top5-binary-guard",
    "make check-fasim-gasal2-formal-preset-examples",
    "make check-fasim-top5-gasal2-gpu-scoreinfo-default-off",
    "make check-fasim-top5-gasal2-gpu-scoreinfo-env",
    "make check-fasim-exact-scoreinfo-gpu-examples-gate",
    "make check-fasim-gasal2-long-query-segmented-no-last-scaling-result",
    "make check-fasim-gasal2-long-query-current-stop",
    "make check-fasim-gasal2-long-query-next-architecture-plan",
    "make check-fasim-gasal2-long-query-next-architecture-decision",
    "make check-fasim-long-query-streaming-scoreinfo-design",
    "make check-fasim-long-query-streaming-scoreinfo-fused-minscore-design",
    "make check-fasim-long-query-streaming-scoreinfo-fused-minscore-prototype",
    "make check-fasim-long-query-streaming-scoreinfo-fused-minscore-boundary",
    "make check-fasim-long-query-streaming-scoreinfo-shadow-skeleton",
    "make check-fasim-long-query-streaming-scoreinfo-shadow-active",
    "make check-fasim-long-query-streaming-scoreinfo-shadow-mismatch-detail",
    "make check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte",
    "make check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte-shared",
    "make check-fasim-gasal2-long-query-exact-tile-oracle-export",
    "make check-fasim-gasal2-long-query-exact-tile-descriptors",
    "make check-fasim-gasal2-long-query-exact-tile-candidate-equivalence-result",
    "make check-fasim-gasal2-long-query-exact-tile-overlap-result",
    "make check-fasim-long-query-exact-column-scoreinfo-shadow",
    "make check-fasim-long-query-exact-column-scoreinfo-shadow-smem-optin",
    "make check-fasim-gasal2-single-pass-topn-sweep",
    "make check-fasim-gasal2-top5-broader-validation",
    "make check-fasim-gasal2-top5-product-readiness",
    "make check-fasim-gasal2-top5-recommended-runtime",
    "make check-fasim-gasal2-top5-release-smoke",
    "make check-fasim-gasal2-scoreinfo-scoped-release-smoke",
    "make check-fasim-gasal2-scoreinfo-scoped-milestone-rollup",
    "make check-fasim-gasal2-malat1-two-contract-product-readiness",
    "make check-fasim-gasal2-malat1-two-contract-recommended-runtime",
    "--long-query-streaming-scoreinfo-gpu-two-contract-runtime-group32",
    "default-off scoped candidate",
    "make check-fasim-gasal2-broad-path-architecture-gate",
    "make check-fasim-gasal2-broad-scoreinfo-consumer-triplex-export",
    "make check-fasim-gasal2-broad-scoreinfo-attempt-planner",
    "make check-fasim-gasal2-broad-replacement-consumer-shadow",
    "make check-fasim-gasal2-broad-neat1-first64-result",
    "decision = broad_path_requires_co_designed_scoreinfo_and_consumer",
    "FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_EXPORT_CPU_TRIPLEX=1",
    "broad_path_cpu_triplexes = 60",
    "broad_path_cpu_triplex_digest = 2d9064122f520fe9",
    "cpu_triplex_export_only",
    "CPU authority triplex export is a scaffold, not broad replacement",
    "FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_PLANNER=1",
    "planner_descriptors_only",
    "broad_path_tasks = 48",
    "broad_path_scoreinfo_groups = 718",
    "broad_path_align_attempts = 3,590",
    "broad_path_planner_descriptor_digest = 30870fb1cfea2aea",
    "selected_attempts = 0",
    "Planner descriptors exist, but no broad replacement consumer is active",
    "FASIM_GASAL2_BROAD_REPLACEMENT_CONSUMER_SHADOW=1",
    "replacement_consumer_shadow_active",
    "broad_path_triplex_mismatches = 0",
    "broad_path_missing_triplexes = 0",
    "broad_path_extra_triplexes = 0",
    "replacement-consumer state shadow can reproduce",
    "diagnostic consumer-shadow checkpoint",
    "co-design scoreInfo generation",
    "kernel-only scoreInfo improvement",
    "selected-only replay consumer is not enough",
    "decision = broad_path_current_architecture_no_go",
    "broad_path_active = 1",
    "broad_path_tasks = 3,058",
    "broad_path_scoreinfo_groups = 52,994",
    "broad_path_align_attempts = 264,970",
    "baseline_wall_seconds = 86.932816",
    "candidate_wall_seconds = 288.4177",
    "candidate_vs_baseline = 0.301413x",
    "broad_path_scoreinfo_seconds = 19.1704",
    "broad_path_consumer_seconds = 52.0465",
    "baseline_cpu_reference_seconds = 52.0833",
    "FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1",
    "decision = attempt_consumer_shadow_no_cpu_align_reduction_no_go",
    "attempts = 211,976",
    "selected_attempts = 140,087",
    "cpu_align_attempts = 140,087",
    "score_seconds = 241.768",
    "total_seconds = 294.821",
    "candidate_vs_baseline = 0.148434x",
    "make check-fasim-gasal2-attempt-consumer-neat1-first64-result",
    "current architecture should not proceed to a real path",
    "scoped milestone rollup",
    "formal_preset_example = meg3_first32",
    "formal_preset_topk_artifact_match = true",
    "formal_preset_gasal2_requests = 63,035",
    "formal_preset_exact_scoreinfo_gpu_tasks = 1,536",
    "formal_preset_speedup_vs_cpu_worker_wall_sum < 1.0",
    "contract smoke, not a performance claim",
    "make check-fasim-gasal2-scoreinfo-scoped-milestone",
    "make check-fasim-gasal2-scoreinfo-scoped-milestone-rollup",
    "make check-fasim-gasal2-scoreinfo-completion-gap",
    "make check-fasim-gasal2-full-goal-decision",
    "make check-fasim-gasal2-replacement-consumer-shadow-requirements",
    "make check-fasim-gasal2-replacement-consumer-shadow-env",
    "make check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke",
    "replacement consumer shadow",
    "NEAT1 first1 replacement-consumer shadow smoke",
    "replacement_consumer_shadow_first_mismatch_source = selected_only",
    "replacement_consumer_shadow_first_mismatch_kind = legacy_empty",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REPLACEMENT_CONSUMER_SHADOW=1",
    "selected-only replay is not sufficient",
    "The selected-consumer root cause is now understood",
    "per scoreInfo:",
    "break when sw_score >= scoreInfo.score",
    "ref_end == cutlength - 1",
    "emit at most one alignment before moving to the next scoreInfo",
    "Direct selected-only replay loses the scoreInfo-local break/best-end state",
    "grouped selected-prefix probe is clean because it expands each selected scoreInfo back to its legacy prefix",
    "selected-attempt reduction is no-go as a broad replacement consumer",
    "If NEAT1 remains slower than CPU fallback, do not promote",
    "make check-fasim-lite-full-equivalence",
    "short-query/H19 top5 scoreInfo/preAlign: milestone go",
    "MEG3 grouped top5 wrapper: milestone go",
    "GASAL2 / GPU scoreInfo scoped feasibility checkpoint",
    "MALAT1 streaming scoreInfo trust path: scoped go",
    "NEAT1 streaming scoreInfo trust path: performance no-go",
    "Broad scoreInfo/preAlign replacement: not proven",
    "full replacement goal: still open",
    "long-query exact-tile CPU oracle export",
    "long-query exact-tile descriptor generator",
    "long-query exact-tile candidate equivalence: no-go",
    "long-query exact-tile overlap probe: no-go",
    "long-query exact-column scoreInfo shadow: launch no-go",
    "long-query exact-column scoreInfo shadow smem opt-in: no-go",
    "scoreinfo_mismatches = 1",
    "shared-memory opt-in is only a diagnostic probe",
    "post-selected-replay status = scoped milestone, not completion",
    "next universal path = accepted top5-only contract, full-output/TFO equivalence proof, or different long-query execution design",
    "MALAT1 first8 query_len = 8708",
    "task/cell accounting is positive",
    "streaming_scoreinfo_shadow_mismatch",
    "low-shared-memory/global-state shadow launches for all MALAT1 first8 tasks",
    "first_mismatch task=130 global=130 diff=0",
    "cpu scoreInfo = 228@465",
    "gpu scoreInfo = 228@463",
    "scalar SW matches GPU, not CPU SSW preAlign",
    "root cause = legacy SSW byte-profile/bias/saturation compatibility",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE=1",
    "gpu_scoreinfo_groups = 31272",
    "cpu_scoreinfo_groups = 31272",
    "scoreinfo_mismatches = 0",
    "SSE2 Lazy-F signed byte compare",
    "16-pass Lazy-F bound",
    "legacy-byte streaming shadow: correctness clean, performance no-go",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED=1",
    "legacy_byte_shared = 1",
    "kernel ~= 3.61s",
    "minscore_seconds:",
    "shadow calc_score_once() threshold recomputation",
    "minscore_cache_hits / minscore_cache_misses:",
    "reused an existing StreamTask minScore",
    "gpu_call_seconds:",
    "CUDA scoreInfo wall time",
    "validation_seconds:",
    "CPU authority replay plus prune/compare work",
    "compare_seconds:",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE=1",
    "gpu_minscore_requested = 1",
    "gpu_minscore_active = 1",
    "gpu_minscore_used = 1824",
    "gpu_minscore_fallbacks = 0",
    "gpu_minscore_score_mismatches = 0",
    "gpu_minscore_min_score_mismatches = 0",
    "gpu_minscore_error = none",
    "lower-shared-memory global-state legacy max-score kernel",
    "skip CPU minScore authority on the hot path",
    "make check-fasim-long-query-streaming-scoreinfo-shadow-gpu-minscore",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT=1",
    "gpu_minscore_hot = 1",
    "gpu_minscore_used = tasks",
    "minscore_seconds <= 0.05",
    "validation_minscore_seconds > 0",
    "MALAT1 first64 hot-path checkpoint",
    "gpu_hot_total_seconds = 45.5043",
    "cpu_prealign_seconds = 50.3037",
    "hot_path_speedup = 1.105477x",
    "scoreInfo correctness stays clean through first64",
    "performance is marginal, not production-ready",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE=1",
    "realpath_requested = 1",
    "realpath_used = 1824",
    "realpath_fallbacks = 0",
    "realpath_digest_authority = cpu_validated",
    "real-path prototype now has a MALAT1 first8/first16/first32/first64 characterization",
    "realpath_used = tasks",
    "64 18096 18096 0 clean 45.4425s 50.2407s 1.105588x",
    "FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST=1",
    "realpath_trust = 1",
    "realpath_digest_authority = external_digest_gate",
    "cpu_scoreinfo_groups = 0",
    "cpu_prealign_seconds = 0",
    "compare_seconds = 0",
    "external-digest-gated",
    "trust characterization extends that result through full MALAT1",
    "64 18096 18096 0 319280 0 0s 45.1879s",
    "128 40128 40128 0 715473 0 0s 95.0452s",
    "256 80640 80640 0 1434844 0 0s 189.973s",
    "670 200400 200400 0 3561123 0 0s 486.763s",
    "digest = 88bb4e98f43c9a48affa082a7e97e881796f161aa4beda02a25dd6a8f7a1891f",
    "baseline Running time = 2631.57s",
    "candidate Running time = 2532.48s",
    "candidate/baseline speedup = 1.039128x",
    "fastSIM_extend_from_scoreinfo()",
    "does not use GASAL2 long-query traceback",
    "CUDA illegal-memory-access failure in GASAL2",
    "NEAT1 first4 global-state",
    "gpu_hot_total_seconds = 3.12787",
    "cpu_prealign_seconds = 0.877741",
    "hot_path_speedup = 0.280619x",
    "NEAT1 first16 global-state",
    "gpu_hot_total_seconds = 12.5232",
    "cpu_prealign_seconds = 3.52635",
    "hot_path_speedup = 0.281585x",
    "NEAT1 trust first16",
    "gpu_scoreinfo_groups = 13,492",
    "gpu_total_seconds = 12.4996",
    "NEAT1 trust first32",
    "tasks = 1,536",
    "gpu_scoreinfo_groups = 25,960",
    "gpu_total_seconds = 25.2269",
    "baseline Running time = 42.8368",
    "candidate Running time = 61.0602",
    "candidate/baseline speedup = 0.701840x",
    "NEAT1 trust first64",
    "tasks = 3,072",
    "gpu_scoreinfo_groups = 52,994",
    "gpu_total_seconds = 49.9507",
    "baseline Running time = 86.0335",
    "candidate Running time = 121.948",
    "candidate/baseline speedup = 0.705493x",
    "digest = 5070d390bdffe9d47c4790193a798bba256d6ec81fc8cef3682a7036f403b01f",
    "NEAT1 first64 fresh runtime attribution",
    "candidate_wall_seconds = 121.948",
    "baseline_wall_seconds = 86.0335",
    "gpu_total_seconds = 49.9507 (~41.0% candidate wall)",
    "gpu_call_seconds = 33.6824",
    "kernel_seconds = 33.6745",
    "realpath_extend_seconds = 52.0682 (~42.7% candidate wall)",
    "realpath_extend_align_seconds = 51.9805",
    "realpath_extend_align_attempts = 140,087",
    "unattributed_overhead_seconds ~= 19.9291 (~16.3% candidate wall)",
    "not H2D/D2H, validation, compare, or CPU fallback",
    "current selector/global-state long-query shape is architecture no-go for broad replacement",
    "next broad work requires a different long-query execution design",
    "MALAT1:",
    "trust correctness clean through full MALAT1",
    "NEAT1:",
    "non-shared legacy-byte replay clean through first128",
    "shared runner trust preset launch no-go for scoreInfo",
    "performance no-go for current execution shape",
    "NEAT1 non-shared audited replay first64",
    "replay tasks = 3,072",
    "replay align attempts = 140,087",
    "NEAT1 non-shared audited replay first128",
    "digest = 6b0f50f11373ce2dcd8b86045847236d7a094bb43bfa95a0b68a3f66840f9c6e",
    "replay tasks = 6,144",
    "gpu_scoreinfo_groups = 105,845",
    "replay align attempts = 281,588",
    "candidate/baseline speedup = 0.300675x",
    "shared scoreInfo kernel fails with `legacy_byte_shared_smem_exceeds_optin_limit`",
    "`gpu_scoreinfo_groups=0`, `realpath_used=0`, and `realpath_fallbacks=4`",
    "rules out a broad long-query real path",
    "make check-fasim-long-query-streaming-scoreinfo-shadow-gpu-minscore-hot",
    "make check-fasim-long-query-streaming-scoreinfo-realpath-prototype",
    "make characterize-fasim-long-query-streaming-scoreinfo-realpath",
    "make characterize-fasim-long-query-streaming-scoreinfo-malat1-full-trust",
    "make characterize-fasim-long-query-streaming-scoreinfo-neat1-first64-trust",
    "make check-fasim-long-query-streaming-scoreinfo-neat1-audited-runner-real",
    "make check-fasim-long-query-streaming-scoreinfo-trust-runner-real",
    "Increasing process-level workers does not fix that for the current trust",
    "0.956003x",
    "0.912482x",
    "0.843978x",
    "More workers alone are not a route to the requested broad",
    "Complete-record grouping is a better fit for that overhead problem",
    "1.028873x",
    "amortize GPU setup and",
    "Group32 scaling keeps the same external-digest-gated contract clean through",
    "1.029346x",
    "1.041244x",
    "1.040806x",
    "1,434,844",
    "The full MALAT1 grouped runner result keeps the same contract",
    "The no-probe two-contract runtime gate separates clean runtime evidence",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full",
    "make check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted",
    "rejects any probe env leakage",
    "probe_positive_numeric_keys=0",
    "MALAT1 first8 no-probe:",
    "candidate_vs_baseline = 0.990695x",
    "tasks = 1,824",
    "MALAT1 first8 TFOsorted no-probe:",
    "schema = tfosorted",
    "candidate_vs_baseline = 0.990699x",
    "MALAT1 first64 no-probe:",
    "digest = f57a418be0ec9439cf2c4c453e2e45cc9d35b03df5e2c63f60860e6575db180d",
    "candidate_vs_baseline = 1.029812x",
    "tasks = 18,096",
    "MALAT1 first128 no-probe:",
    "rows = 22,531",
    "digest = 91ea0b8191027916e3237fb5381c6271fc9acd03b46a5cf67826c253fe41edd1",
    "candidate_vs_baseline = 1.041215x",
    "tasks = 40,128",
    "two_contract_used = 40,128",
    "realpath_used = 40,128",
    "gpu_scoreinfo_groups = 715,473",
    "MALAT1 first256 no-probe:",
    "rows = 42,504",
    "digest = 7f553b74ae31bed4cb7b9c312a188e2df19627ac4882c7ad7ac484d65b004a4e",
    "candidate_vs_baseline = 1.040931x",
    "tasks = 80,640",
    "MALAT1 full no-probe:",
    "baseline_wall_seconds = 2611.940621",
    "candidate_wall_seconds = 2514.945686",
    "candidate_vs_baseline = 1.038567x",
    "tasks = 200,400",
    "two_contract_used = 200,400",
    "realpath_used = 200,400",
    "gpu_scoreinfo_groups = 3,561,123",
    "MALAT1 full TFOsorted no-probe:",
    "schema = tfosorted",
    "digest = ac667f460cd1446bc5598fa163f7fc2755265bf56e6b82c105e672873c895ffc",
    "baseline_wall_seconds = 2636.136998",
    "candidate_wall_seconds = 2537.678266",
    "candidate_vs_baseline = 1.038799x",
    "Full-MALAT1 Milestone Decision",
    "remaining bottleneck is CPU realpath extend/align",
    "realpath_extend_align_attempts = 8,526,477",
    "repeatable no-probe evidence",
    "--long-query-streaming-scoreinfo-gpu-trust-group32",
    "long_query_streaming_scoreinfo_gpu_trust_group32_experimental_v1",
    "malat1_like_group32_experimental_v1",
    "characterization wrappers exercise the preset contract directly",
    "run_fasim_long_query_streaming_scoreinfo_trust_group32_audited.sh",
    "audited_status = accepted",
    "digest gate failed",
    "baseline_runner_wall_seconds",
    "candidate_runner_wall_seconds",
    "candidate_vs_baseline",
    "candidate_gpu_scoreinfo_total_seconds",
    "candidate_gpu_scoreinfo_call_seconds",
    "candidate_gpu_scoreinfo_kernel_seconds",
    "candidate_non_gpu_wall_seconds",
    "candidate_gpu_scoreinfo_wall_fraction",
    "candidate_gpu_scoreinfo_call_fraction",
    "candidate_realpath_extend_seconds",
    "candidate_realpath_extend_calls",
    "candidate_realpath_extend_fraction",
    "candidate_realpath_extend_scoreinfo_groups",
    "candidate_realpath_extend_align_attempts",
    "candidate_realpath_extend_substr_seconds",
    "candidate_realpath_extend_align_seconds",
    "candidate_realpath_extend_align_fraction",
    "candidate_realpath_extend_convert_seconds",
    "candidate_realpath_extend_sort_seconds",
    "candidate_realpath_extend_filter_seconds",
    "trusted-scoreInfo consumption boundary",
    "candidate_realpath_extend_align_attempts = 74,646",
    "candidate_vs_baseline ~= 0.93x",
    "candidate_realpath_extend_align_seconds ~= 10.12",
    "candidate_realpath_extend_align_fraction ~= 0.405",
    "candidate_realpath_extend_segmented_attempt_probe_requested = 0",
    "candidate_realpath_extend_flush_segmented_attempt_probe_requested = 16",
    "candidate_realpath_extend_flush_segmented_attempt_probe_active = 64",
    "candidate_realpath_extend_flush_segmented_attempt_probe_calls = 64",
    "candidate_realpath_extend_flush_segmented_attempt_probe_attempts = 500,352",
    "candidate_realpath_extend_flush_segmented_attempt_probe_selected_attempts ~= 218,570",
    "candidate_realpath_extend_flush_segmented_attempt_probe_seconds ~= 1.44",
    "candidate_realpath_extend_flush_segmented_attempt_probe_fallbacks = 0",
    "candidate_realpath_extend_flush_segmented_replay_probe_requested = 16",
    "candidate_realpath_extend_flush_segmented_replay_probe_tasks = 16",
    "candidate_realpath_extend_flush_segmented_replay_probe_align_attempts = 638",
    "candidate_realpath_extend_flush_segmented_replay_probe_triplex_mismatches = 0",
    "candidate_realpath_extend_flush_segmented_replay_probe_fallbacks = 0",
    "candidate_realpath_extend_flush_full_replay_probe_triplex_mismatches = 0",
    "candidate_realpath_extend_flush_oracle_replay_probe_triplex_mismatches = 0",
    "diagnostic replay filtering bug",
    "sorted top `N` before threshold filtering",
    "zero triplex mismatches on the capped audited gate",
    "legacy helper re-entry can be clean",
    "larger/full task scope",
    "--replay-probe-max-tasks N",
    "`N=0` means all tasks in each flush",
    "MALAT1 first8/group32 replay cap=4",
    "replay tasks = 64",
    "replay align attempts = 2,855",
    "MALAT1 first8/group32 replay cap=16",
    "replay tasks = 256",
    "replay align attempts = 10,424",
    "MALAT1 first8/group32 replay cap=0",
    "replay tasks = 1,824",
    "replay selected attempts = 218,570",
    "replay align attempts = 74,646",
    "MALAT1 first8/group32 selected-only replay cap=0",
    "selected-only attempts = 218,570",
    "selected-only align attempts = 99,022",
    "selected-only selected scoreInfos = 31,272",
    "selected-only tasks with selected attempts = 1,752",
    "selected-only tasks with triplex = 1,348",
    "selected-only zero-triplex tasks = 476",
    "selected-only mismatch selected_empty = 5",
    "selected-only mismatch legacy_empty = 277",
    "selected-only mismatch selected_less = 28",
    "selected-only mismatch selected_more = 828",
    "selected-only mismatch same_count_diff = 36",
    "selected-only first mismatch task = 0",
    "selected-only first mismatch kind = selected_more",
    "selected-only first mismatch provenance = scoreinfo=7;start=4023;cutlength=37;sw_score=73;ref_begin=11;ref_end=30;query_begin=3460;query_end=3479",
    "selected-only scoreInfos with multiple triplexes = 845",
    "selected-only extra triplexes from repeated scoreInfo = 965",
    "selected-only triplex mismatches = 1,174",
    "decision = no-go for direct selected-only consumer",
    "MALAT1 first16/group32 replay cap=0",
    "replay tasks = 4,416",
    "replay align attempts = 186,488",
    "MALAT1 first32/group32 replay cap=0",
    "replay tasks = 8,160",
    "replay align attempts = 344,974",
    "MALAT1 first64/group32 replay cap=0",
    "replay tasks = 18,096",
    "replay align attempts = 764,324",
    "full hand replay mismatches = 0",
    "oracle replay mismatches = 0",
    "full replay of the checked first8, first16, first32, and first64 task sets",
    "most mismatches are selected-only extra triplexes rather than coverage misses",
    "first extra comes from an additional selected attempt inside scoreInfo 7",
    "breaks the legacy scoreInfo-level single-emission contract",
    "selected-attempt CPU-align reduction no-go for current selector",
    "This is the post-selected-replay scoped milestone",
    "default-off experimental profile",
    "direct selected-only consumer as no-go",
    "full-output/TFO equivalence proof over the intended workload scope",
    "genuinely different long-query execution design",
    "GASAL2 select calls from 7,008 to 64",
    "capped flush-level segmented replay probe",
    "batched extend-attempt consumption",
    "candidate_post_scoreinfo_unattributed_seconds",
    "candidate_post_scoreinfo_unattributed_fraction",
    "2541.655441s",
    "1.036714x",
    "f080498ad8b9661100243e8eec89b6b54b566d7ed96fa5db7e268a8ce8513e0b",
    "current MALAT1-like recommended experimental profile",
    "make characterize-fasim-long-query-streaming-scoreinfo-hot",
    "diagnostic/performance-shaping probe",
    "full-query exact-column CUDA scoreInfo execution shape is also not a valid",
    "top5-only product-readiness",
    "top5 broader workload validation",
    "GASAL2 top5 recommended runtime",
    "full objective remains open",
]
missing_doc = [phrase for phrase in required_doc if phrase not in doc]
if missing_doc:
    raise SystemExit(
        "current-state doc missing phrases: " + ", ".join(missing_doc)
    )

required_runner_doc = [
    "make check-fasim-gasal2-scoreinfo-current-state",
    "short-query/H19 top5 scoreInfo/preAlign",
    "MEG3 grouped top5 wrapper",
    "long-query current best is marginal",
    "full replacement goal remains open",
]
missing_runner_doc = [
    phrase for phrase in required_runner_doc if phrase not in runner_doc
]
if missing_runner_doc:
    raise SystemExit(
        "runner doc missing current-state phrases: "
        + ", ".join(missing_runner_doc)
    )

missing_bridge_doc = [
    phrase for phrase in required_runner_doc if phrase not in bridge_doc
]
if missing_bridge_doc:
    raise SystemExit(
        "bridge doc missing current-state phrases: "
        + ", ".join(missing_bridge_doc)
    )
for phrase in (
    "formal preset path is already column-pruned one-DP",
    "zero_legacy_score_runs = 1",
):
    if phrase not in bridge_doc:
        raise SystemExit(f"bridge doc missing one-DP formal phrase: {phrase}")
if "explicit double-DP cost in this current path" in bridge_doc:
    raise SystemExit("bridge doc still describes double-DP as the current path")

required_contract_doc = [
    "make check-fasim-gasal2-scoreinfo-current-state",
    "current scoreInfo/preAlign milestone",
    "short-query/H19 top5 scoreInfo/preAlign",
    "MEG3 grouped top5 wrapper",
    "full replacement goal remains open",
]
for phrase in (
    "make check-fasim-gasal2-emission-only-consumer-debug",
    "make check-fasim-gasal2-scoring-parameter-matrix",
    "task_key=49",
    "GASAL2 score equals CPU score for attempt 26",
    "CPU ref_end = 1574, terminal = 0",
    "GASAL2 ref_end = 1575, terminal = 1",
    "shadow threshold while legacy non-threshold = 35",
    "task_key=117 scoreinfo_index=26 attempt_index=104",
    "CPU score = 68",
    "GASAL2 segmented score = 138",
    "FASIM_ALIGN_GASAL2_GAP_OPEN=16",
    "lowers the same GASAL2 score from `138` to `104`",
    "triplex_mismatches=12",
    "gap open `12` leaves that gate clean",
    "diagnostic only",
    "GASAL2 endpoint/terminal and current segmented max-score threshold must not become output authority or safe reject/accept authority",
    "task49:",
    "score matches, endpoint/terminal differs",
    "task117:",
    "gap_open=12 over-threshold segmented GASAL2 score = 138",
    "gap_open=16 introduces triplex_mismatches=12",
    "full-query-compatible score/end/tie policy or CPU-authority validation",
    "make check-fasim-gasal2-cpu-authority-candidate-coverage-plan",
    "GASAL2 may only propose candidate attempts",
    "legacy selected attempt is present in the GASAL2 candidate set",
    "false_negative_scoreinfos = 0",
    "cpu_align_attempts < realpath_reference_align_attempts",
    "total_seconds < realpath_reference_seconds",
    "If candidate coverage is not exact, this reducer stops",
):
    if phrase not in doc:
        raise SystemExit(f"current-state doc missing emission-only debug phrase: {phrase}")

missing_contract_doc = [
    phrase for phrase in required_contract_doc if phrase not in output_contract_doc
]
if missing_contract_doc:
    raise SystemExit(
        "output contract doc missing current-state phrases: "
        + ", ".join(missing_contract_doc)
    )

target = re.search(
    r"^check-fasim-gasal2-scoreinfo-current-state:(?P<deps>.*)$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-scoreinfo-current-state target")
deps = target.group("deps")
dep_tokens = set(deps.split())
required_deps = [
    "check-fasim-gasal2-top5-scoreinfo-milestone",
    "check-fasim-gasal2-formal-makefile-gate",
    "check-fasim-gasal2-top5-scoreinfo-milestone-result",
    "check-fasim-gasal2-top5-scoreinfo-meg3-grouped-result",
    "check-fasim-gasal2-top5-wrapper-meg3-grouped-result",
    "check-fasim-sharded-gasal2-top5-prune-runner",
    "check-fasim-gasal2-column-pruned-preset-top5-matrix",
    "check-fasim-gasal2-top5-output-contract",
    "check-fasim-gasal2-top5-activation-contract",
    "check-fasim-gasal2-topk-lite-wrapper-contract",
    "check-fasim-gasal2-top5-lowercase-input",
    "check-fasim-gasal2-top5-binary-guard",
    "check-fasim-gasal2-formal-preset-examples",
    "check-fasim-top5-gasal2-gpu-scoreinfo-default-off",
    "check-fasim-top5-gasal2-gpu-scoreinfo-env",
    "check-fasim-exact-scoreinfo-gpu-examples-gate",
    "check-fasim-gasal2-long-query-boundary",
    "check-fasim-gasal2-long-query-segmented-no-last-scaling-result",
    "check-fasim-gasal2-long-query-current-stop",
    "check-fasim-gasal2-long-query-next-architecture-plan",
    "check-fasim-gasal2-long-query-next-architecture-decision",
    "check-fasim-long-query-streaming-scoreinfo-design",
    "check-fasim-long-query-streaming-scoreinfo-shadow-skeleton",
    "check-fasim-long-query-streaming-scoreinfo-shadow-active",
    "check-fasim-long-query-streaming-scoreinfo-shadow-mismatch-detail",
    "check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte",
    "check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte-shared",
    "check-fasim-long-query-streaming-scoreinfo-fused-minscore-design",
    "check-fasim-long-query-streaming-scoreinfo-fused-minscore-prototype",
    "check-fasim-long-query-streaming-scoreinfo-fused-minscore-boundary",
    "check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design",
    "check-fasim-long-query-streaming-scoreinfo-shadow-gpu-minscore",
    "check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-shadow",
    "check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-trust",
    "check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-runner",
    "check-fasim-long-query-streaming-scoreinfo-shadow-gpu-minscore-hot",
    "check-fasim-long-query-streaming-scoreinfo-realpath-prototype",
    "check-fasim-long-query-streaming-scoreinfo-realpath-trust",
    "check-fasim-long-query-streaming-scoreinfo-trust-runner",
    "check-fasim-long-query-streaming-scoreinfo-trust-group32-runner",
    "check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner",
    "check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real",
    "check-fasim-long-query-streaming-scoreinfo-neat1-audited-runner-real",
    "check-fasim-long-query-streaming-scoreinfo-trust-runner-real",
    "check-fasim-gasal2-long-query-exact-tile-oracle-export",
    "check-fasim-gasal2-long-query-exact-tile-descriptors",
    "check-fasim-gasal2-long-query-exact-tile-candidate-equivalence-result",
    "check-fasim-gasal2-long-query-exact-tile-overlap-result",
    "check-fasim-long-query-exact-column-scoreinfo-shadow",
    "check-fasim-long-query-exact-column-scoreinfo-shadow-smem-optin",
    "check-fasim-gasal2-single-pass-topn-sweep",
    "check-fasim-gasal2-top5-broader-validation",
    "check-fasim-gasal2-top5-product-readiness",
    "check-fasim-gasal2-top5-recommended-runtime",
    "check-fasim-gasal2-top5-release-smoke",
    "check-fasim-gasal2-scoreinfo-scoped-release-smoke",
    "check-fasim-gasal2-scoreinfo-scoped-milestone-rollup",
    "check-fasim-gasal2-malat1-two-contract-product-readiness",
    "check-fasim-gasal2-malat1-two-contract-recommended-runtime",
    "check-fasim-gasal2-broad-path-architecture-gate",
    "check-fasim-gasal2-broad-replacement-consumer-shadow",
    "check-fasim-gasal2-attempt-consumer-shadow-plan",
    "check-fasim-gasal2-attempt-consumer-shadow-env",
    "check-fasim-gasal2-attempt-consumer-shadow-selection",
    "check-fasim-gasal2-attempt-consumer-shadow-runtime-smoke",
    "check-fasim-gasal2-scoreinfo-completion-gap",
    "check-fasim-gasal2-full-goal-decision",
    "check-fasim-gasal2-replacement-consumer-shadow-requirements",
    "check-fasim-gasal2-replacement-consumer-shadow-env",
    "check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke",
    "check-fasim-gasal2-score-prepass-state-machine-stop",
    "check-fasim-lite-full-equivalence",
    "check-fasim-gasal2-malat1-tfosorted-equivalence-evidence",
    "check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full",
    "check-fasim-gasal2-malat1-no-probe-two-contract-runtime",
    "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted",
    "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64",
    "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128",
    "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256",
    "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full",
    "check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted",
]
missing_deps = [dep for dep in required_deps if dep not in dep_tokens]
if missing_deps:
    raise SystemExit(
        "current-state Makefile target missing deps: " + ", ".join(missing_deps)
    )
recipe = "bash ./scripts/check_fasim_gasal2_scoreinfo_current_state.sh"
if recipe not in makefile:
    raise SystemExit("current-state Makefile target missing checker recipe")
if "characterize-fasim-long-query-streaming-scoreinfo-realpath:" not in makefile:
    raise SystemExit("Makefile missing realpath characterization target")
if "characterize-fasim-long-query-streaming-scoreinfo-realpath-trust:" not in makefile:
    raise SystemExit("Makefile missing realpath trust characterization target")
if "characterize-fasim-long-query-streaming-scoreinfo-malat1-full-trust:" not in makefile:
    raise SystemExit("Makefile missing full MALAT1 realpath trust characterization target")
if "characterize-fasim-long-query-streaming-scoreinfo-neat1-trust:" not in makefile:
    raise SystemExit("Makefile missing NEAT1 trust characterization target")
if "characterize-fasim-long-query-streaming-scoreinfo-neat1-first64-trust:" not in makefile:
    raise SystemExit("Makefile missing NEAT1 first64 trust characterization target")
if "check-fasim-long-query-streaming-scoreinfo-realpath-trust:" not in makefile:
    raise SystemExit("Makefile missing realpath trust target")
if "check-fasim-long-query-streaming-scoreinfo-trust-runner:" not in makefile:
    raise SystemExit("Makefile missing long-query streaming scoreInfo trust runner target")
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-runner:" not in makefile:
    raise SystemExit("Makefile missing long-query streaming scoreInfo group32 trust runner target")
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner:" not in makefile:
    raise SystemExit("Makefile missing audited long-query streaming scoreInfo group32 trust runner target")
if "check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real:" not in makefile:
    raise SystemExit("Makefile missing real audited long-query streaming scoreInfo group32 trust runner target")
if "check-fasim-long-query-streaming-scoreinfo-neat1-audited-runner-real:" not in makefile:
    raise SystemExit("Makefile missing real audited long-query streaming scoreInfo NEAT1 trust runner target")
if "check-fasim-long-query-streaming-scoreinfo-trust-runner-real:" not in makefile:
    raise SystemExit("Makefile missing long-query streaming scoreInfo trust runner real target")
if "characterize-fasim-long-query-streaming-scoreinfo-trust-runner:" not in makefile:
    raise SystemExit("Makefile missing trust runner characterization target")
if "characterize-fasim-long-query-streaming-scoreinfo-trust-runner-workers:" not in makefile:
    raise SystemExit("Makefile missing trust runner worker characterization target")
if "characterize-fasim-long-query-streaming-scoreinfo-trust-runner-groups:" not in makefile:
    raise SystemExit("Makefile missing trust runner grouping characterization target")
if "characterize-fasim-long-query-streaming-scoreinfo-trust-runner-group32-scaling:" not in makefile:
    raise SystemExit("Makefile missing trust runner group32 scaling characterization target")
if "characterize-fasim-long-query-streaming-scoreinfo-trust-runner-malat1-full-group32:" not in makefile:
    raise SystemExit("Makefile missing trust runner full MALAT1 group32 characterization target")
PY

echo "ok"
