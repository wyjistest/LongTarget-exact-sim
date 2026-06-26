#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def _flat_text(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def _require(text: str, phrase: str, source: str) -> None:
    if phrase not in text:
        raise SystemExit(f"{source} missing required roadmap phrase: {phrase}")


def _forbid(text: str, phrase: str, source: str) -> None:
    if phrase in text:
        raise SystemExit(f"{source} contains stale forbidden roadmap phrase: {phrase}")


def _matrix_summary(path: Path) -> dict[str, str]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    claimed = [row for row in rows if row.get("scope") == "claimed"]
    blocked_or_unclaimed = [
        row for row in rows if row.get("scope") in {"blocked", "unclaimed"}
    ]
    claimed_clean = bool(claimed) and all(
        row.get("status") == "pass" for row in claimed
    )
    has_broad_claim = any(row.get("contract") == "broad_replacement" for row in claimed)
    return {
        "claimed_clean": "1" if claimed_clean else "0",
        "blocked_or_unclaimed": str(len(blocked_or_unclaimed)),
        "has_broad_claim": "1" if has_broad_claim else "0",
    }


def _path_a_acceptance_recorded(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    text = _flat_text(path)
    return (
        "user_scope_acceptance_recorded = 1" in text
        and "scoped_completion_may_close_goal = 1" in text
        and "path_a_user_acceptance_recorded = 1" in text
        and "active_goal_completion_status = complete_scoped_path_a" in text
        and "not broad aligner.Align replacement" in text
        and "GASAL2 output authority = 0" in text
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize the executable Fasim/GASAL2 roadmap current state."
    )
    parser.add_argument("--roadmap", required=True, type=Path)
    parser.add_argument("--phase-checklist", required=True, type=Path)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--acceptance", type=Path)
    args = parser.parse_args()

    roadmap = _flat_text(args.roadmap)
    phase_checklist = _flat_text(args.phase_checklist)
    matrix = _matrix_summary(args.matrix)
    path_a_accepted = _path_a_acceptance_recorded(args.acceptance)

    required_phrases = [
        "make check-fasim-gasal2-roadmap-phase0-reproducibility",
        "make check-fasim-gasal2-roadmap-phase1-scoped-contract",
        "make check-fasim-gasal2-roadmap-phase1-scoped-product",
        "docs/fasim_gasal2_goal_closure_phase_plan.md",
        "docs/fasim_gasal2_goal_completion_canonical_phase_plan.md",
        "make check-fasim-gasal2-roadmap-goal-closure-phase-plan",
        "phase1_scoped_product_gate = ready_if_user_accepts_scope",
        "docs/fasim_gasal2_path_a_scoped_completion_acceptance.md",
        "path_a_scoped_completion_acceptance_packet = defined",
        "path_a_scoped_completion_status = accepted",
        "user_scope_acceptance_recorded = 1",
        "scoped_completion_may_close_goal = 1",
        "active_goal_completion_status = complete_scoped_path_a",
        "completion_guard_cleared = 1",
        "contract = gasal2_top5_column_pruned_scoreinfo_artifact_v1",
        "primary preset = --gasal2-top5-column-pruned-scoreinfo",
        "tiny-region add-on = --group-target-records 32",
        "make check-fasim-gasal2-roadmap-phase2-equivalence-first-convert",
        "phase2_equivalence_first_convert_gate = ready",
        "convert_wall_speedup = 1.778130x",
        "sort, filter, rank-map, output write, output close, query release",
        "make check-fasim-gasal2-roadmap-phase3-preconvert-prune",
        "phase3_preconvert_prune_gate = not_ready_current_prune_no_go",
        "current_real_prune_decision = no_go",
        "real_prune_may_be_enabled = 0",
        "make check-fasim-gasal2-task-frontier-proof-export",
        "broad_path_cpu_triplexes = 60",
        "real export same-file proof:",
        "real export one-row-removed proof:",
        "make check-fasim-gasal2-roadmap-phase3-cigar-nt-prefilter-design",
        "phase3_cigar_nt_prefilter_design_gate = defined",
        "candidate = cigar_nt_prefilter",
        "requires_shadow_first = 1",
        "requires_disagree_lt_ntmin_zero = 1",
        "requires_task_frontier_safety_safe = 1",
        "phase3 next implementation = CIGAR NT prefilter shadow proof",
        "make check-fasim-gasal2-phase3-cigar-nt-prefilter-shadow",
        "phase3_cigar_nt_prefilter_shadow_gate = proof_smoke_clean",
        "phase3_cigar_nt_prefilter_alignments_seen = 718",
        "phase3_cigar_nt_prefilter_cigar_lt_ntmin = 53",
        "phase3_cigar_nt_prefilter_legacy_nt_lt_ntmin = 53",
        "phase3_cigar_nt_prefilter_disagree_lt_ntmin = 0",
        "phase3_cigar_nt_prefilter_real_prune_proof_gate = pass",
        "make characterize-fasim-gasal2-phase3-cigar-nt-prefilter-full",
        "make check-fasim-gasal2-phase3-cigar-nt-prefilter-full-result",
        "phase3_cigar_nt_prefilter_full_characterization = pass",
        "projected_saved_fraction = 0.061087",
        "projected_saved_fraction = 0.063068",
        "make check-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate",
        "real_skipped_alignments = 12,574",
        "real_validated_skips = 12,574",
        "real_validate_mismatches = 0",
        "real_fallbacks = 0",
        "real_decision = validated_clean",
        "make characterize-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate-full",
        "make check-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate-full-result",
        "phase3_cigar_nt_prefilter_real_validate_full_characterization = pass",
        "chr22 full:",
        "real_skipped_alignments = 493,934",
        "convert_wall_speedup = 0.925278",
        "run_wall_speedup = 0.991226",
        "chr1 full:",
        "real_skipped_alignments = 2,771,079",
        "convert_wall_speedup = 0.919547",
        "run_wall_speedup = 0.991088",
        "phase3_cigar_nt_prefilter_real_validate = full_clean_no_speedup_default_off",
        "measured performance = no-go",
        "runtime recommendation = no",
        "make check-fasim-gasal2-roadmap-phase4-sort-topn",
        "phase4_sort_topn_gate = not_first_priority",
        "dominant_convert_stage = triplex_materialization",
        "sort_topn_first_priority = 0",
        "archive_manifest_decision = ready",
        "make check-fasim-gasal2-roadmap-phase5-archive-artifact",
        "phase5_archive_artifact_gate = ready",
        "make check-fasim-gasal2-roadmap-phase6-workload-matrix",
        "phase6_workload_matrix_gate = claimed_scope_only",
        "decision = matrix_has_claimed_scope_only",
        "scoreinfo_reduced_claimed = 2",
        "align_side_reduced_claimed = 0",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart",
        "phase7_broad_restart_gate = current_architecture_no_go",
        "Phase 7 v4 source replay first64 correctness clean but performance no-go",
        "pursue Path B only with a different GPU execution design",
        "make check-fasim-gasal2-roadmap-phase7-candidate-coverage",
        "phase7_candidate_coverage_gate = defined_not_completion",
        "candidate_coverage_runtime_smoke = pass",
        "candidate_coverage_smoke_false_negative_scoreinfos = 0",
        "candidate_coverage_smoke_candidate_align_attempts = 51",
        "candidate_coverage_smoke_reference_align_attempts = 51",
        "candidate_coverage_selected_only_runtime_smoke = pass",
        "candidate_coverage_selected_only_false_negative_scoreinfos = 0",
        "candidate_coverage_selected_only_candidate_attempts = 2352",
        "candidate_coverage_selected_only_candidate_align_attempts = 51",
        "candidate_coverage_selected_only_reference_align_attempts = 51",
        "candidate_coverage_current_decision = coverage_clean_no_align_reduction",
        "make check-fasim-gasal2-roadmap-phase7-candidate-coverage-stop",
        "phase7_candidate_coverage_stop_gate = current_reducer_no_go",
        "candidate_coverage_prefix_align_reduction = 0",
        "candidate_coverage_selected_only_align_reduction = 0",
        "candidate_coverage_stop_reason = no_cpu_align_attempt_reduction",
        "next_phase7_required = new_reducer_or_architecture",
        "make check-fasim-gasal2-roadmap-phase7-next-reducer-design",
        "phase7_next_reducer_design_gate = defined",
        "current_candidate_reducer_status = current_reducer_no_go",
        "required_next_reducer = task_local_frontier_or_scoreinfo_local_state",
        "requires_align_attempt_reduction = 1",
        "requires_neat1_first64_broad_gate = 1",
        "make check-fasim-gasal2-roadmap-phase7-next-reducer-implementation-plan",
        "phase7_next_reducer_implementation_plan_gate = defined",
        "requires_default_off_shadow = 1",
        "requires_task_local_frontier = 1",
        "requires_scoreinfo_local_state = 1",
        "requires_broad_matrix_evidence_before_completion = 1",
        "make check-fasim-gasal2-roadmap-phase7-next-reducer-scaffold",
        "phase7_next_reducer_scaffold_gate = bounded_go_not_broad",
        "phase7_next_reducer_env_gate = pass",
        "phase7_next_reducer_runtime_smoke = pass",
        "phase7_next_reducer_characterization = pass",
        "phase7_next_reducer_digest_match = 1",
        "phase7_next_reducer_false_negative_scoreinfos = 0",
        "phase7_next_reducer_triplex_mismatches = 0",
        "phase7_next_reducer_candidate_align_attempts = 48",
        "phase7_next_reducer_reference_align_attempts = 192",
        "phase7_next_reducer_current_decision = bounded_go_needs_neat1_broad_gate",
        "make check-fasim-gasal2-roadmap-phase7-next-reducer-broad-gate",
        "phase7_next_reducer_broad_gate = correctness_no_go",
        "phase7_next_reducer_broad_first1_attempted = 1",
        "phase7_next_reducer_broad_first1_decision = phase7_next_reducer_broad_gate_correctness_no_go",
        "phase7_next_reducer_broad_first1_digest_match = 0",
        "phase7_next_reducer_broad_first1_full_rows_equal = 0",
        "phase7_next_reducer_broad_first1_baseline_only_rows = 8",
        "phase7_next_reducer_broad_first1_candidate_only_rows = 5",
        "phase7_next_reducer_broad_first1_candidate_align_attempts = 1266",
        "phase7_next_reducer_broad_first1_reference_align_attempts = 2696",
        "phase7_next_reducer_broad_first64_attempted = 0",
        "phase7_next_reducer_broad_first64_decision = phase7_next_reducer_broad_gate_skipped_first1_no_go",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-design",
        "phase7_broad_restart_v2_design_gate = defined",
        "phase7_broad_restart_v2_current_status = design_only",
        "phase7_broad_restart_v2_required_first_gate = frontier_log_replay_proof",
        "phase7_broad_restart_v2_requires_neat1_first64 = 1",
        "new order = frontier log first, exact replay proof before reduction",
        "fasim: prototype Phase 7 all-attempt early-stop runtime",
        "FASIM_GASAL2_PHASE7_FRONTIER_LOG=1",
        "phase7_broad_restart_v2_frontier_log_scaffold_gate = runtime_smoke_clean",
        "frontier log path is non-empty",
        "frontier log digest is non-empty",
        "frontier log TSV schema is present",
        "next gate = NEAT1 first1 exact replay proof",
        "make characterize-fasim-gasal2-phase7-frontier-replay",
        "make check-fasim-gasal2-phase7-frontier-replay-result",
        "phase7_broad_restart_v2_frontier_replay_gate = exact_no_reduction",
        "frontier_log_rows = 2,872",
        "frontier_selected_rows = 718",
        "frontier_positive_align_rows = 2,872",
        "candidate_align_attempts = reference_align_attempts = 2,872",
        "frontier_log_rows = 211,976",
        "frontier_selected_rows = 52,994",
        "frontier_positive_align_rows = 211,976",
        "candidate_align_attempts = reference_align_attempts = 211,976",
        "reducer-ready frontier evidence is present",
        "next gate = reducer shadow after replay proof",
        "no measured CPU Align attempt reduction yet",
        "not broad completion",
        "cpu_aligner_align_authority = 1",
        "gasal2_output_authority = 0",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-reducer",
        "phase7_broad_restart_v2_frontier_reducer = oracle_reduction_projected_not_broad",
        "candidate_align_attempts = 52,994",
        "reference_align_attempts = 211,976",
        "align_attempt_reduction = 158,982",
        "wall_time_basis = oracle_projected",
        "broad_gate_pass = 0",
        "selected frontier rows are known only after CPU Align in the current log",
        "next gate = measured runtime reducer or predictor",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-predictor",
        "phase7_broad_restart_v2_frontier_predictor = no_go_current_features",
        "selected_rank_set = 0,1,2,3",
        "oracle_selected align_attempt_reduction = 158,982",
        "oracle_selected predictor_gate_pass = 0",
        "keep_all false_negative_selected_rows = 0",
        "keep_all align_attempt_reduction = 0",
        "reducing pre-align predictors all have false_negative_selected_rows > 0",
        "decision = phase7_frontier_predictor_no_go_current_features",
        "the current frontier fields do not contain a safe pre-Align selected-row predictor",
        "next gate = new pre-Align signal or measured runtime reducer design",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-score-signal",
        "phase7_broad_restart_v2_frontier_score_signal = no_go",
        "selected_score_rank_counts = 0:33615,1:2469,2:2240,3:14670",
        "align_sw_score_desc_top_3 false_negative_selected_rows = 14,670",
        "align_sw_score_ge_best_zero_fn align_attempt_reduction = 0",
        "decision = phase7_frontier_score_signal_no_go",
        "even post-Align score/end fields do not contain a safe reducing signal",
        "next gate = new non-score signal or measured runtime reducer design",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop",
        "phase7_broad_restart_v2_frontier_early_stop = candidate_not_measured",
        "candidate_align_attempts = 103,953",
        "align_attempt_reduction = 108,023",
        "unsafe_skipped_rows = 0",
        "false_negative_selected_rows = 0",
        "runtime_candidate = 1",
        "measured_runtime = 0",
        "next gate = measured runtime early-stop reducer",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop-runtime",
        "phase7_broad_restart_v2_frontier_early_stop_runtime = runtime_smoke_clean_needs_neat1_first1",
        "FASIM_GASAL2_PHASE7_FRONTIER_EARLY_STOP=1",
        "default_off = 1",
        "reference_align_attempts = 192",
        "candidate_align_attempts = 48",
        "skipped_attempts = 144",
        "output digest unchanged",
        "next gate = measured runtime NEAT1 first1 correctness gate",
        "make characterize-fasim-gasal2-phase7-frontier-early-stop-runtime",
        "make check-fasim-gasal2-phase7-frontier-early-stop-runtime-result",
        "phase7_broad_restart_v2_frontier_early_stop_runtime_first1 = correctness_no_go",
        "missing_rows = 7",
        "extra_rows = 5",
        "triplex_mismatches = 12",
        "candidate_align_attempts = 1,309",
        "reference_align_attempts = 2,872",
        "align_attempt_reduction = 1,563",
        "decision = phase7_frontier_early_stop_runtime_first1_no_go",
        "decision_reasons = output_rows_differ,missing_rows,extra_rows",
        "this candidate must not continue to NEAT1 first64 broad gate",
        "next gate = new reducer or architecture",
        "make check-fasim-gasal2-roadmap-phase7-next-reducer-after-early-stop-design",
        "phase7_next_reducer_after_early_stop_no_go_design = defined",
        "coverage-first all-attempt CPU replay",
        "candidate coverage before candidate reduction",
        "Gate A: all-attempt early-stop runtime first1",
        "Gate B: all-attempt early-stop runtime first64",
        "Gate C: coverage-preserving GPU candidate generator",
        "scoreInfo/preAlign work must be reduced before broad completion",
        "fasim: prototype Phase 7 all-attempt early-stop runtime",
        "make characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime",
        "make check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-result",
        "phase7_all_attempt_early_stop_runtime_first1 = correctness_go_needs_first64",
        "FASIM_GASAL2_PHASE7_ALL_ATTEMPT_EARLY_STOP=1",
        "all-attempt mode keeps candidate coverage before candidate reduction",
        "NEAT1 first1 correctness and Align-side attempt reduction pass",
        "first1 wall time is near parity across reruns and is not a broad performance gate",
        "candidate_align_attempts = 2,008",
        "reference_align_attempts = 2,872",
        "align_attempt_reduction = 864",
        "candidate_vs_baseline = near_parity_across_reruns",
        "decision = phase7_all_attempt_early_stop_runtime_first1_go",
        "make characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64",
        "make check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64-result",
        "phase7_all_attempt_early_stop_runtime_first64 = correctness_go_near_parity_not_broad",
        "candidate_align_attempts = 140,087",
        "reference_align_attempts = 211,976",
        "align_attempt_reduction = 71,889",
        "candidate_vs_baseline = near_parity_across_reruns",
        "decision = phase7_all_attempt_early_stop_runtime_first64_go",
        "scoreInfo/preAlign work is still CPU work",
        "wall time is near parity across reruns, not a material broad performance win",
        "next gate = coverage-preserving GPU candidate generator",
        "docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md",
        "phase7_gate_c_gpu_candidate_generator_design = defined",
        "coverage-preserving GPU candidate generator",
        "preserve the all-attempt early-stop frontier",
        "NEAT1 first1 coverage gate",
        "NEAT1 first64 broad gate",
        "candidate_align_attempts <= Gate B candidate_align_attempts",
        "workload matrix broad_replacement row is forbidden until Gate C first64 passes",
        "no real opt-in",
        "phase7_gate_c_gpu_candidate_generator_implementation_plan = defined",
        "Task 1: Gate C Env And Telemetry",
        "Task 2: Oracle Frontier Export Reuse",
        "Task 3: GPU Candidate Descriptor Shadow",
        "Task 4: Coverage Comparison Gate",
        "Task 5: CPU-Authority Replay Gate",
        "Task 6: NEAT1 first64 Broad Characterization",
        "Task 7: Roadmap And Matrix Decision",
        "next gate = Gate C runtime prototype",
        "make check-fasim-gasal2-phase7-gate-c-env",
        "make check-fasim-gasal2-phase7-gate-c-runtime-smoke",
        "phase7_gate_c_runtime_smoke = pass",
        "phase7_gate_c_requested = 1",
        "phase7_gate_c_active = 0",
        "phase7_gate_c_tasks = 48",
        "phase7_gate_c_oracle_scoreinfos = 48",
        "phase7_gate_c_oracle_attempts = 192",
        "phase7_gate_c_gpu_candidate_scoreinfos = 0",
        "phase7_gate_c_gpu_candidate_attempts = 0",
        "this is an oracle-metric scaffold smoke, not GPU candidate generation",
        "next gate = Gate C GPU Candidate Descriptor Shadow",
        "make characterize-fasim-gasal2-phase7-gate-c-first1",
        "make check-fasim-gasal2-phase7-gate-c-first1-result",
        "phase7_gate_c_first1 = no_go_no_gpu_candidate_descriptors",
        "gate_b_candidate_align_attempts = 2,008",
        "scoreinfo_reduced = 0",
        "oracle_scoreinfos = 718",
        "oracle_attempts = 2,872",
        "gpu_candidate_scoreinfos = 0",
        "gpu_candidate_attempts = 0",
        "decision = phase7_gate_c_first1_no_go",
        "decision_reasons = no_gpu_candidate_descriptors,scoreinfo_not_reduced",
        "current Gate C does not generate GPU candidate descriptors",
        "current Gate C does not reduce or replace scoreInfo/preAlign work",
        "this candidate must not continue to Gate C first64 broad gate",
        "next gate = new GPU candidate descriptor source or stop broad GASAL2 path",
        "docs/fasim_gasal2_phase7_gate_c_stop_checkpoint.md",
        "phase7_gate_c_stop_checkpoint = current_source_no_go",
        "current_gate_c_source_status = stopped_no_gpu_candidate_descriptors",
        "gate_c_first64_allowed = 0",
        "restart_requires_new_gpu_candidate_descriptor_source = 1",
        "gpu_candidate_scoreinfos > 0",
        "gpu_candidate_attempts > 0",
        "candidate_align_attempts <= 2,008",
        "docs/fasim_gasal2_phase7_current_broad_stop_decision.md",
        "phase7_current_broad_stop_decision = current_broad_sources_no_go",
        "current_broad_sources_status = stopped",
        "phase7_current_broad_sources_may_continue = 0",
        "phase7_new_architecture_required = 1",
        "claimed_broad_replacement_rows = 0",
        "docs/fasim_gasal2_phase7_broad_restart_v3_candidate_certificate_design.md",
        "phase7_broad_restart_v3_candidate_certificate_design = defined",
        "phase7_broad_restart_v3_current_status = design_only",
        "phase7_broad_restart_v3_next_gate = descriptor_source_smoke",
        "phase7_broad_restart_v3_may_claim_completion = 0",
        "requires_gpu_or_native_descriptor_source = 1",
        "requires_candidate_certificate = 1",
        "requires_cpu_authority_replay = 1",
        "requires_scoreinfo_prealign_reduction = 1",
        "requires_align_side_reduction = 1",
        "requires_full_output_equality = 1",
        "Gate v3.1 requires gpu_candidate_scoreinfos > 0",
        "Gate v3.1 requires gpu_candidate_attempts > 0",
        "Gate v3.1 requires cpu_scoreinfo_calls < baseline_cpu_scoreinfo_calls",
        "Gate v3.1 requires candidate_certificate_false_negatives = 0",
        "next gate = descriptor_source_smoke",
        "docs/fasim_gasal2_phase7_broad_restart_v3_descriptor_source_smoke.md",
        "phase7_broad_restart_v3_descriptor_source_smoke = current_no_pre_scoreinfo_source",
        "phase7_broad_restart_v3_current_status = scaffold_no_go",
        "phase7_v3_descriptor_source_requested = 1",
        "phase7_v3_descriptor_source_active = 0",
        "phase7_v3_descriptor_source_candidate_attempts = 0",
        "phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 0",
        "gpu_candidate_scoreinfos = 0",
        "gpu_candidate_attempts = 0",
        "cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls",
        "pre_scoreinfo_source = 0",
        "after_cpu_scoreinfo_source = 1",
        "phase7_broad_restart_v3_gate_v3_1_pass = 0",
        "phase7_broad_restart_v3_may_continue_to_first64 = 0",
        "next gate = real_pre_scoreinfo_descriptor_source",
        "docs/fasim_gasal2_phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke.md",
        "phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke = pre_scoreinfo_descriptors_no_reduction",
        "phase7_broad_restart_v3_current_status = pre_scoreinfo_scaffold_no_go",
        "phase7_v3_descriptor_source_active = 1",
        "phase7_v3_descriptor_source_pre_scoreinfo_source = 1",
        "phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1",
        "cpu_scoreinfo_reduced = 0",
        "candidate_certificate_checked = 0",
        "next gate = certificate_checked_scoreinfo_reducing_descriptor_source",
        "docs/fasim_gasal2_phase7_broad_restart_v3_certificate_smoke.md",
        "phase7_broad_restart_v3_certificate_smoke = certificate_checked_no_scoreinfo_reduction",
        "phase7_broad_restart_v3_current_status = certificate_scaffold_no_go",
        "phase7_v3_descriptor_source_candidate_certificate_checked = 1",
        "phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0",
        "phase7_v3_descriptor_source_missing_required_attempts = 0",
        "cpu_scoreinfo_calls = baseline_cpu_scoreinfo_calls",
        "next gate = scoreinfo_reducing_candidate_certificate",
        "docs/fasim_gasal2_phase7_broad_restart_v3_all_column_certificate_smoke.md",
        "phase7_broad_restart_v3_all_column_certificate_smoke = scoreinfo_reducing_all_column_certificate",
        "phase7_broad_restart_v3_current_status = gate_v3_1_pass_attempt_overgenerate",
        "phase7_v3_descriptor_source_candidate_scoreinfos_gt_zero = 1",
        "phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1",
        "phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0",
        "phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1",
        "phase7_broad_restart_v3_gate_v3_2_pass = 0",
        "next gate = all_column_certificate_cpu_replay_first1",
        "docs/fasim_gasal2_phase7_broad_restart_v3_all_column_replay_stop.md",
        "phase7_broad_restart_v3_all_column_replay_stop = candidate_attempt_explosion_no_go",
        "candidate_attempts = 168,730,848",
        "reference_align_attempts = 2,872",
        "candidate_attempt_ratio = 58,750.30x",
        "candidate_align_attempts < reference_align_attempts cannot pass",
        "do_not_run_all_column_cpu_replay = 1",
        "phase7_broad_restart_v3_next_gate = narrower_scoreinfo_reducing_certificate",
        "docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_design.md",
        "phase7_broad_restart_v3_narrow_certificate_design = defined",
        "phase7_broad_restart_v3_narrow_certificate_status = design_only",
        "phase7_broad_restart_v3_next_gate = narrow_certificate_runtime_smoke",
        "required_runtime_env = FASIM_GASAL2_PHASE7_V3_NARROW_CERTIFICATE",
        "must_be_narrower_than_all_column = 1",
        "do_not_use_all_column_or_all_window_certificate = 1",
        "candidate_attempts < 168,730,848",
        "candidate_attempts < reference_align_attempts required for v3.2",
        "docs/fasim_gasal2_phase7_broad_restart_v3_narrow_certificate_smoke.md",
        "phase7_broad_restart_v3_narrow_certificate_smoke = bounded_probe_no_go_missing_certificate",
        "phase7_broad_restart_v3_narrow_certificate_status = runtime_smoke_no_go",
        "phase7_v3_descriptor_source_candidate_attempts_lt_all_column = 1",
        "phase7_v3_descriptor_source_candidate_certificate_false_negatives_gt_zero = 1",
        "phase7_v3_descriptor_source_missing_required_attempts_gt_zero = 1",
        "phase7_broad_restart_v3_next_gate = real_narrow_certificate_coverage_proof",
        "docs/fasim_gasal2_phase7_broad_restart_v3_real_narrow_certificate_coverage_proof.md",
        "phase7_broad_restart_v3_real_narrow_certificate_coverage_proof = exact_column_candidate_no_go",
        "phase7_broad_restart_v3_exact_column_candidate_status = no_go",
        "non_optin_active = 0",
        "non_optin_error = invalid argument",
        "smem_optin_active = 1",
        "smem_optin_scoreinfo_mismatches = 1",
        "smem_optin_decision = smem_optin_scoreinfo_no_go",
        "phase7_broad_restart_v3_next_gate = different_exact_scoreinfo_source_or_seed_certificate",
        "docs/fasim_gasal2_phase7_broad_restart_v3_next_source_design.md",
        "phase7_broad_restart_v3_next_source_design = defined",
        "phase7_broad_restart_v3_next_source_status = design_only",
        "phase7_broad_restart_v3_next_gate = different_exact_scoreinfo_source_or_seed_certificate_smoke",
        "previous_exact_column_candidate_status = no_go",
        "do_not_continue_all_column_replay = 1",
        "do_not_continue_bounded_narrow_probe = 1",
        "do_not_continue_existing_exact_column_gpu_scoreinfo = 1",
        "allowed_source_1 = different_exact_scoreinfo_compatible_gpu_execution",
        "allowed_source_2 = seed_or_index_certificate",
        "descriptor_source_before_cpu_scoreinfo = 1",
        "candidate_attempts < reference_align_attempts required before v3.2",
        "first1_descriptor_smoke_before_replay = 1",
        "first64_broad_gate_only_after_first1_replay = 1",
        "docs/fasim_gasal2_phase7_broad_restart_v3_next_source_smoke.md",
        "phase7_broad_restart_v3_next_source_smoke = seed_certificate_fail_closed",
        "phase7_broad_restart_v3_next_source_status = runtime_smoke_no_go",
        "required_runtime_env = FASIM_GASAL2_PHASE7_V3_SEED_CERTIFICATE_SOURCE",
        "phase7_v3_descriptor_source_candidate_scoreinfos_gt_zero = 1",
        "phase7_v3_descriptor_source_candidate_attempts_gt_zero = 1",
        "phase7_v3_descriptor_source_candidate_attempts_lt_all_column = 1",
        "phase7_v3_descriptor_source_candidate_certificate_checked = 1",
        "phase7_v3_descriptor_source_candidate_certificate_false_negatives_gt_zero = 1",
        "phase7_v3_descriptor_source_missing_required_attempts_gt_zero = 1",
        "phase7_v3_descriptor_source_cpu_scoreinfo_calls = 0",
        "phase7_v3_descriptor_source_cpu_scoreinfo_reduced = 1",
        "phase7_broad_restart_v3_next_gate = stronger_seed_certificate_or_different_exact_scoreinfo_source",
        "docs/fasim_gasal2_phase7_broad_restart_v3_strong_seed_smoke.md",
        "phase7_broad_restart_v3_strong_seed_smoke = task_coverage_clean_attempt_coverage_missing",
        "phase7_broad_restart_v3_strong_seed_status = runtime_smoke_no_go_attempt_coverage",
        "required_runtime_env = FASIM_GASAL2_PHASE7_V3_STRONG_SEED_CERTIFICATE_SOURCE",
        "phase7_v3_descriptor_source_candidate_scoreinfos_ge_baseline = 1",
        "phase7_v3_descriptor_source_candidate_certificate_false_negatives = 0",
        "phase7_broad_restart_v3_next_gate = attempt_coverage_seed_certificate_or_different_exact_scoreinfo_source",
        "docs/fasim_gasal2_phase7_broad_restart_v3_attempt_coverage_seed_smoke.md",
        "phase7_broad_restart_v3_attempt_coverage_seed_smoke = attempt_coverage_clean_needs_replay_preflight",
        "phase7_broad_restart_v3_attempt_coverage_seed_status = gate_v3_1_pass_candidate_attempts_high",
        "required_runtime_env = FASIM_GASAL2_PHASE7_V3_ATTEMPT_COVERAGE_SEED_CERTIFICATE",
        "reference_scoreinfos = 718",
        "reference_attempts = 2,872",
        "candidate_scoreinfos = 718",
        "raw_seed_hits = 1,051,822",
        "candidate_attempts = 108,694",
        "candidate_min_cover_positions = 463",
        "candidate_attempts_lt_all_column = 1",
        "candidate_attempts_lt_raw_seed_hits = 1",
        "candidate_attempts_below_reference = 0",
        "candidate_min_cover_positions_below_reference = 1",
        "oracle_min_cover_uses_legacy_attempt_windows = 1",
        "real_pre_scoreinfo_reducer_proven = 0",
        "candidate_certificate_false_negatives = 0",
        "missing_required_attempts = 0",
        "phase7_broad_restart_v3_gate_v3_1_pass = 1",
        "phase7_broad_restart_v3_gate_v3_2_pass = 0",
        "phase7_broad_restart_v3_next_gate = oracle_min_cover_replay_shape_probe_or_non_oracle_candidate_reducer",
        "docs/fasim_gasal2_phase7_broad_restart_v3_oracle_min_cover_replay_smoke.md",
        "phase7_broad_restart_v3_oracle_min_cover_replay_smoke = output_no_go",
        "phase7_broad_restart_v3_oracle_min_cover_replay_status = oracle_shape_probe_no_go",
        "required_runtime_env = FASIM_GASAL2_PHASE7_V3_ORACLE_MIN_COVER_REPLAY",
        "reference_align_attempts = 2,872",
        "candidate_min_cover_positions = 463",
        "candidate_align_attempts = 463",
        "skipped_attempts = 2,409",
        "candidate_align_attempts_lt_reference = 1",
        "digest_match = 0",
        "full_rows_equal = 0",
        "missing_rows = 11",
        "extra_rows = 9",
        "phase7_broad_restart_v3_gate_v3_2_shape_probe_pass = 0",
        "phase7_broad_restart_v3_next_gate = non_oracle_candidate_reducer_or_stop_seed_path",
        "docs/fasim_gasal2_phase7_broad_restart_v3_seed_path_stop.md",
        "phase7_broad_restart_v3_seed_path_stop = current_seed_index_path_stopped",
        "phase7_broad_restart_v3_seed_path_status = stopped_no_output_clean_non_oracle_reducer",
        "phase7_broad_restart_v3_may_continue_to_first64 = 0",
        "phase7_broad_restart_v3_next_gate = different_scoreinfo_compatible_gpu_execution_design_or_path_a_scope_decision",
        "docs/fasim_gasal2_phase7_broad_restart_v4_scoreinfo_native_design.md",
        "phase7_broad_restart_v4_scoreinfo_native_design = defined",
        "phase7_broad_restart_v4_status = design_only",
        "phase7_broad_restart_v4_next_gate = legacy_byte_scoreinfo_shadow_first1",
        "phase7_broad_restart_v4_may_claim_completion = 0",
        "phase7_broad_restart_v4_gate_v4_1_pass = 0",
        "phase7_broad_restart_v4_gate_v4_2_pass = 0",
        "phase7_broad_restart_v4_gate_v4_3_pass = 0",
        "legacy_ssw_byte_saturation = required",
        "legacy_word_upgrade_on_saturation = required",
        "legacy_window_of_5_peak_clustering = required",
        "scoreinfo_rows_equal = true",
        "docs/fasim_gasal2_phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke.md",
        "phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke = host_contract_clean_needs_gpu",
        "phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_status = host_reconstruction_clean_gpu_rows_zero",
        "required_runtime_env = FASIM_GASAL2_PHASE7_V4_LEGACY_BYTE_SCOREINFO_SHADOW",
        "phase7_v4_legacy_byte_scoreinfo_shadow_active = 1",
        "phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_rows_equal = 1",
        "phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_order_equal = 1",
        "phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_attempt_windows_equal = 1",
        "phase7_v4_legacy_byte_scoreinfo_shadow_host_contract_pass = 1",
        "phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 0",
        "phase7_v4_legacy_byte_scoreinfo_shadow_gate_v4_1_pass = 0",
        "source = host_column_score_reconstruction",
        "phase7_broad_restart_v4_next_gate = gpu_legacy_byte_scoreinfo_shadow_first1",
        "docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke.md",
        "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke = gpu_contract_clean_first1",
        "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_status = first1_gpu_rows_equal_not_broad",
        "required_runtime_env = FASIM_GASAL2_PHASE7_V4_GPU_LEGACY_BYTE_SCOREINFO_SHADOW",
        "phase7_v4_legacy_byte_scoreinfo_shadow_tasks = 48",
        "phase7_v4_legacy_byte_scoreinfo_shadow_cpu_scoreinfo_rows = 718",
        "phase7_v4_legacy_byte_scoreinfo_shadow_host_scoreinfo_rows = 718",
        "phase7_v4_legacy_byte_scoreinfo_shadow_gpu_scoreinfo_rows = 718",
        "phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_mismatches = 0",
        "phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_false_negatives = 0",
        "phase7_v4_legacy_byte_scoreinfo_shadow_scoreinfo_extra_required_attempts = 0",
        "phase7_v4_legacy_byte_scoreinfo_shadow_gate_v4_1_pass = 1",
        "source = gpu_legacy_byte_scoreinfo",
        "phase7_broad_restart_v4_runtime_next_gate = gpu_legacy_byte_scoreinfo_source_first1_cpu_authority_replay",
        "docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke.md",
        "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke = cpu_authority_replay_clean_first1",
        "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_status = first1_replay_clean_needs_first64_broad_gate",
        "required_runtime_env = FASIM_GASAL2_PHASE7_V4_GPU_LEGACY_BYTE_SCOREINFO_SOURCE_REPLAY",
        "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_runtime_smoke = cpu_authority_replay_first1",
        "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_active = 1",
        "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_digest_match = 1",
        "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_rows_equal = 1",
        "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_order_equal = 1",
        "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_scoreinfo_attempt_windows_equal = 1",
        "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempts = 2008",
        "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_reference_align_attempts = 2872",
        "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_align_attempt_reduction = 864",
        "phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_gate_v4_2_pass = 1",
        "phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_scoreinfo_rows = 718",
        "phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_cpu_authority = 1",
        "phase7_v4_legacy_byte_scoreinfo_shadow_source_replay_gpu_endpoint_cigar_traceback_output_authority = 0",
        "realpath_requested = 1",
        "realpath_fallbacks = 0",
        "realpath_extend_align_attempts = 2008",
        "reference_align_attempts = 2872",
        "align_attempt_reduction = 864",
        "phase7_broad_restart_v4_gate_v4_2_pass = 1",
        "phase7_broad_restart_v4_runtime_next_gate = gpu_legacy_byte_scoreinfo_source_first64_broad_gate",
        "requires_false_negative_scoreinfos_zero = 1",
        "requires_cpu_align_attempt_reduction = 1",
        "docs/fasim_gasal2_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate.md",
        "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate = correctness_clean_performance_no_go",
        "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_status = first64_correctness_clean_performance_no_go",
        "baseline_wall_seconds = 86.358386",
        "candidate_wall_seconds = 134.744406",
        "candidate_vs_baseline = 0.640905",
        "digest_match = 1",
        "candidate_gate_v4_2_pass = 1",
        "candidate_gpu_scoreinfo_rows = 52994",
        "candidate_source_replay_scoreinfo_rows = 52994",
        "candidate_realpath_requested = 1",
        "candidate_realpath_fallbacks = 0",
        "candidate_realpath_extend_scoreinfo_groups = 52994",
        "candidate_realpath_extend_align_attempts = 140087",
        "candidate_realpath_extend_seconds = 52.1721",
        "candidate_realpath_extend_align_seconds = 52.0788",
        "reference_align_attempts = 211976",
        "align_attempt_reduction = 71889",
        "performance_gate_pass = 0",
        "phase7_broad_restart_v4_gate_v4_3_pass = 0",
        "phase7_broad_restart_v4_runtime_next_gate = different_gpu_execution_design_or_path_a_scope_decision",
        "docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_design.md",
        "phase7_broad_restart_v5_fused_scoreinfo_consumer_design = defined",
        "phase7_broad_restart_v5_status = design_only",
        "phase7_broad_restart_v5_design_family = fused_gpu_scoreinfo_to_candidate_attempt_descriptors",
        "phase7_broad_restart_v5_differs_from_v4_source_replay = 1",
        "phase7_broad_restart_v5_gate_v5_1_pass = 1",
        "phase7_broad_restart_v5_gate_v5_2_pass = 1",
        "phase7_broad_restart_v5_gate_v5_3_pass = 0",
        "phase7_broad_restart_v5_next_gate = different_gpu_execution_design_or_path_a_scope_decision",
        "Do not materialize the full legacy scoreInfo row stream as a host-visible intermediate.",
        "Compute legacy byte scoreInfo and consume the row stream in the same GPU execution design.",
        "Emit compact candidate attempt descriptors, not endpoint, CIGAR, traceback, output, or digest authority.",
        "docs/superpowers/plans/2026-06-13-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer.md",
        "Task 1: Env, Stats, And Default-Off Telemetry",
        "Task 2: Descriptor Contract Runtime Smoke",
        "Task 3: CPU-Authority Replay First1 Gate",
        "Task 4: Roadmap Checkpoint And Current-State Wiring",
        "Task 5: First64 Broad Gate Characterization",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-implementation-plan",
        "docs/fasim_gasal2_phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke.md",
        "phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke = post_scoreinfo_descriptor_scaffold_no_go",
        "phase7_broad_restart_v5_runtime_scaffold_requested = 1",
        "phase7_broad_restart_v5_runtime_scaffold_active = 1",
        "phase7_broad_restart_v5_runtime_scaffold_gpu_descriptor_attempts = 2872",
        "phase7_broad_restart_v5_runtime_scaffold_descriptor_false_negatives = 0",
        "phase7_broad_restart_v5_runtime_scaffold_missing_required_attempts = 0",
        "phase7_broad_restart_v5_runtime_scaffold_scoreinfo_prealign_reduced = 0",
        "phase7_broad_restart_v5_runtime_scaffold_cpu_align_authority = 1",
        "phase7_broad_restart_v5_runtime_scaffold_gpu_endpoint_cigar_traceback_output_authority = 0",
        "phase7_broad_restart_v5_runtime_scaffold_next_gate = true_pre_scoreinfo_fused_descriptor_source",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-fused-scoreinfo-consumer-runtime-smoke",
        "docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design.md",
        "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design = defined",
        "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_status = design_only",
        "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_may_claim_completion = 0",
        "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate = runtime_smoke_true_pre_scoreinfo_descriptor_source_first1",
        "Do not use CPU aligner.preAlign() or any CPU legacy scoreInfo producer as the descriptor source.",
        "source_is_pre_scoreinfo = 1",
        "scoreinfo_prealign_reduced = 1",
        "gpu_descriptor_attempts > 0",
        "candidate attempts stay below all-column replay scale",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-design",
        "docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_env_scaffold.md",
        "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_env_scaffold = fail_closed_no_source",
        "FASIM_GASAL2_PHASE7_V5_TRUE_PRE_SCOREINFO_DESCRIPTOR_SOURCE",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_requested = 1",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_active = 0",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo = 0",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced = 0",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_gpu_descriptor_attempts = 0",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass = 0",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-env-scaffold",
        "docs/fasim_gasal2_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.md",
        "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke = gate_v5_1_pass_first1",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_active = 1",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_source_is_pre_scoreinfo = 1",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_scoreinfo_prealign_reduced = 1",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_descriptor_false_negatives = 0",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_missing_required_attempts = 0",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass = 1",
        "next_required_gate = phase7_gate_v5_2_cpu_authority_replay_first1",
        "docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_smoke.md",
        "phase7_broad_restart_v5_cpu_authority_replay_smoke = gate_v5_2_pass_first1",
        "root_cause_fix = legacy_float_identity_cutlength_descriptor_generation",
        "phase7_v5_cpu_authority_replay_source_is_pre_scoreinfo = 1",
        "phase7_v5_cpu_authority_replay_scoreinfo_prealign_reduced = 1",
        "phase7_v5_cpu_authority_replay_gpu_descriptor_scoreinfos = 718",
        "phase7_v5_cpu_authority_replay_gpu_descriptor_attempts = 2872",
        "phase7_v5_cpu_authority_replay_reference_align_attempts = 2872",
        "phase7_v5_cpu_authority_replay_candidate_align_attempts = 2008",
        "phase7_v5_cpu_authority_replay_full_rows_equal = 1",
        "phase7_v5_cpu_authority_replay_digest_match = 1",
        "phase7_v5_cpu_authority_replay_gate_v5_2_pass = 1",
        "next_required_gate = different_gpu_execution_design_or_path_a_scope_decision",
        "docs/fasim_gasal2_phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate.md",
        "phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate = correctness_clean_performance_no_go",
        "phase7_broad_restart_v5_cpu_authority_replay_first64_status = first64_correctness_clean_performance_no_go",
        "phase7_broad_restart_v5_first64_baseline_wall_seconds = 87.827405",
        "phase7_broad_restart_v5_first64_candidate_wall_seconds = 124.399845",
        "phase7_broad_restart_v5_first64_candidate_vs_baseline = 0.706009",
        "phase7_broad_restart_v5_first64_digest_match = 1",
        "phase7_broad_restart_v5_first64_full_rows_equal = 1",
        "phase7_broad_restart_v5_first64_candidate_align_attempts = 115561",
        "phase7_broad_restart_v5_first64_reference_align_attempts = 211976",
        "phase7_broad_restart_v5_first64_align_attempt_reduction = 96415",
        "phase7_broad_restart_v5_first64_missing_required_attempts = 624",
        "phase7_broad_restart_v5_first64_fallback_accounting_clean = 0",
        "phase7_broad_restart_v5_runtime_next_gate = different_gpu_execution_design_or_path_a_scope_decision",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-first64-broad-gate",
        "docs/fasim_gasal2_phase7_post_v5_3_architecture_decision.md",
        "phase7_post_v5_3_architecture_decision = defined",
        "phase7_post_v5_3_current_v5_status = stopped_no_go",
        "phase7_post_v5_3_next_gate = post_v5_3_task_frontier_certificate_first1_smoke",
        "current_decision = selected_task_frontier_certificate_or_path_a_acceptance",
        "next_required_gate = post_v5_3_task_frontier_certificate_first1_smoke",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-architecture-decision",
        "docs/fasim_gasal2_phase7_post_v5_3_new_architecture_design.md",
        "phase7_post_v5_3_new_architecture_design = defined",
        "phase7_post_v5_3_design_family = gpu_resident_scoreinfo_consumer_summary_with_cpu_authority_replay",
        "phase7_post_v5_3_new_architecture_may_implement = 1",
        "phase7_post_v5_3_new_architecture_may_claim_completion = 0",
        "FASIM_GASAL2_PHASE7_POST_V5_3_GPU_CONSUMER_SUMMARY",
        "next_required_gate = post_v5_3_gpu_consumer_summary_first1_smoke",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-architecture-design",
        "docs/fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_env_scaffold.md",
        "phase7_post_v5_3_gpu_consumer_summary_env_scaffold = fail_closed_no_source",
        "phase7_post_v5_3_gpu_consumer_summary_requested = 1",
        "phase7_post_v5_3_gpu_consumer_summary_active = 0",
        "phase7_post_v5_3_gpu_consumer_summary_gate_first1_pass = 0",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-gpu-consumer-summary-env-scaffold",
        "docs/fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go.md",
        "phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go = recorded",
        "phase7_post_v5_3_gpu_consumer_summary_first_attempt_status = no_go",
        "phase7_post_v5_3_gpu_consumer_summary_first1_gate_pass = 0",
        "phase7_post_v5_3_gpu_consumer_summary_external_digest_match = 0",
        "phase7_post_v5_3_gpu_consumer_summary_external_full_rows_equal = 0",
        "phase7_post_v5_3_gpu_consumer_summary_gpu_selected_attempts = 718",
        "phase7_post_v5_3_gpu_consumer_summary_candidate_align_attempts = 718",
        "phase7_post_v5_3_gpu_consumer_summary_reference_align_attempts = 2872",
        "phase7_post_v5_3_gpu_consumer_summary_next_gate = stronger_post_v5_3_consumer_summary_design_or_path_a_acceptance",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-gpu-consumer-summary-first-attempt-no-go",
        "docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_design.md",
        "phase7_post_v5_3_stronger_consumer_summary_design = defined",
        "phase7_post_v5_3_stronger_consumer_summary_status = design_only",
        "phase7_post_v5_3_stronger_consumer_summary_may_implement = 1",
        "phase7_post_v5_3_stronger_consumer_summary_may_claim_completion = 0",
        "previous_status = first_descriptor_per_scoreinfo_no_go",
        "required_next_design_property = prefix_boundary_or_equivalent_replay_proof",
        "next_required_gate = post_v5_3_stronger_consumer_summary_first1_smoke",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-consumer-summary-design",
        "docs/fasim_gasal2_phase7_post_v5_3_stronger_consumer_summary_prefix_no_go.md",
        "phase7_post_v5_3_stronger_consumer_summary_prefix_no_go = recorded",
        "phase7_post_v5_3_stronger_consumer_summary_first1_gate_pass = 0",
        "prefix_1_2_3_reduce_gpu_selected_attempts_but_change_output = 1",
        "prefix_4_5_preserve_output_but_do_not_reduce_gpu_selected_attempts = 1",
        "phase7_post_v5_3_stronger_consumer_summary_prefix_next_gate = different_gpu_execution_design_or_path_a_scope_decision",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-consumer-summary-prefix-no-go",
        "docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_design.md",
        "phase7_post_v5_3_task_frontier_certificate_design = defined",
        "phase7_post_v5_3_task_frontier_certificate_status = design_only",
        "phase7_post_v5_3_task_frontier_certificate_may_implement = 1",
        "phase7_post_v5_3_task_frontier_certificate_may_claim_completion = 0",
        "phase7_post_v5_3_design_family = gpu_task_frontier_certificate_with_cpu_authority_replay",
        "uses_task_frontier_certificate = 1",
        "uses_prefix_boundary_only = 0",
        "next_required_gate = post_v5_3_task_frontier_certificate_first1_smoke",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-design",
        "docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_env_scaffold.md",
        "phase7_post_v5_3_task_frontier_certificate_env_scaffold = fail_closed_no_source",
        "phase7_post_v5_3_task_frontier_certificate_env_scaffold_status = superseded_by_first_attempt_no_go",
        "FASIM_GASAL2_PHASE7_POST_V5_3_TASK_FRONTIER_CERTIFICATE=1",
        "phase7_post_v5_3_task_frontier_certificate_requested = 1",
        "phase7_post_v5_3_task_frontier_certificate_active = 0",
        "phase7_post_v5_3_task_frontier_certificate_gate_first1_pass = 0",
        "superseded_by_first_attempt_no_go",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-env-scaffold",
        "docs/fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go.md",
        "phase7_post_v5_3_task_frontier_certificate_first_attempt_status = no_go",
        "phase7_post_v5_3_task_frontier_certificate_first1_gate_pass = 0",
        "phase7_post_v5_3_task_frontier_certificate_external_digest_match = 0",
        "phase7_post_v5_3_task_frontier_certificate_external_full_rows_equal = 0",
        "phase7_post_v5_3_task_frontier_certificate_missing_rows = 17",
        "phase7_post_v5_3_task_frontier_certificate_gpu_selected_attempts = 192",
        "phase7_post_v5_3_task_frontier_certificate_candidate_align_attempts = 138",
        "phase7_post_v5_3_task_frontier_certificate_reference_align_attempts = 2872",
        "phase7_post_v5_3_task_frontier_certificate_next_gate = stronger_task_frontier_certificate_design_or_path_a_acceptance",
        "docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_design.md",
        "phase7_post_v5_3_stronger_task_frontier_certificate_design = defined",
        "phase7_post_v5_3_stronger_task_frontier_certificate_status = design_only",
        "phase7_post_v5_3_stronger_task_frontier_certificate_may_implement = 1",
        "phase7_post_v5_3_stronger_task_frontier_certificate_may_claim_completion = 0",
        "phase7_post_v5_3_stronger_task_frontier_certificate_next_gate = stronger_task_frontier_certificate_first1_smoke",
        "docs/fasim_gasal2_phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go.md",
        "phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go = recorded",
        "phase7_post_v5_3_stronger_task_frontier_certificate_status = feasibility_no_go",
        "phase7_post_v5_3_stronger_task_frontier_certificate_first1_smoke_allowed = 0",
        "do_not_implement_current_stronger_task_frontier_runtime = 1",
        "next_required_gate = new_pre_d2h_output_inert_proof_or_different_gpu_execution_design_or_path_a_scope_decision",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-task-frontier-certificate-feasibility-no-go",
        "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.md",
        "phase7_post_v5_3_pre_d2h_output_inert_proof_search_design = defined",
        "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export.md",
        "phase7_post_v5_3_pre_d2h_output_inert_proof_search_status = first1_export_pass",
        "phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export = pass",
        "phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_implement = 1",
        "phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion = 0",
        "next_required_gate = pre_d2h_output_inert_proof_acceptance_first1",
        "docs/fasim_gasal2_phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1.md",
        "phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1 = no_go",
        "phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_status = first1_no_accepted_proof",
        "docs/fasim_gasal2_phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision.md",
        "phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision = defined",
        "path_a_user_acceptance_required = 1",
        "path_b_new_pre_d2h_proof_family_required = 1",
        "candidate_proof_false_negatives = 0",
        "candidate_proof_missing_required_attempts = 0",
        "candidate_selected_attempts < v5_candidate_align_attempts",
        "candidate_selected_attempts < reference_align_attempts",
        "candidate_uses_final_cpu_output_as_runtime_proof = 0",
        "do_not_reuse_failed_proof_search_aggregate_export = 1",
        "do_not_use_final_cpu_output_as_runtime_proof = 1",
        "accepted_pre_d2h_proof_families = 0",
        "reducing_runtime_allowed = 0",
        "first64_runtime_allowed = 0",
        "current_execution_gate = implement_new_pre_d2h_proof_family_first1_smoke_or_path_a_acceptance",
        "current_next_pr = fasim: new pre-D2H proof family first1 smoke or scope acceptance",
        "proof_search_rows = 2872",
        "task_count = 48",
        "scoreinfo_count = 718",
        "attempt_count = 2872",
        "runtime_reduction_enabled = 0",
        "gpu_output_authority = 0",
        "gate_first1_export_pass = 1",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-design",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-first1-export",
        "existing_v4_gpu_source_materializes_host_visible_scoreinfo_rows = 1",
        "existing_cuda_api_emits_prealign_cuda_peaks_not_attempt_descriptors = 1",
        "do_not_rebrand_v4_source_replay_as_v5 = 1",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke",
        "docs/fasim_gasal2_phase7_broad_restart_v5_cuda_descriptor_emission_design.md",
        "phase7_broad_restart_v5_cuda_descriptor_emission_design = defined",
        "phase7_broad_restart_v5_cuda_descriptor_emission_status = design_only",
        "new_cuda_api = prealign_cuda_emit_legacy_byte_attempt_descriptors",
        "output_contract = compact_attempt_descriptors_not_scoreinfo_rows",
        "host-visible full legacy scoreInfo row stream = forbidden",
        "CPU aligner.Align() authority replay = 1",
        "GPU endpoint/CIGAR/traceback/output authority = 0",
        "make check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-descriptor-emission-design",
        "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold.md",
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold = fail_closed",
        "FASIM_GASAL2_PHASE7_POST_V5_3_NEW_GPU_ENGINE_FIRST1_SHADOW",
        "missing_certificate_producer = 1",
        "certificate_valid_before_d2h = 0",
        "next_valid_gate = implement_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-shadow-scaffold",
        "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api.md",
        "phase7_post_v5_3_new_gpu_engine_certificate_cuda_api = fail_closed_api_scaffold",
        "new_cuda_api = prealign_cuda_emit_new_engine_skipped_work_certificates",
        "certificate_producer_active = 0",
        "certificate_cuda_api_gate_pass = 0",
        "next_valid_gate = implement_new_gpu_engine_certificate_producer_first1_or_path_a_acceptance",
        "current_next_pr = fasim_new_gpu_engine_certificate_producer_first1_or_path_a_acceptance",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-cuda-api",
        "docs/fasim_gasal2_phase7_post_v5_3_new_gpu_engine_certificate_producer_first1.md",
        "phase7_post_v5_3_new_gpu_engine_certificate_producer_first1 = producer_first1_synthetic_gate",
        "certificate_producer_active = 1",
        "certificate_valid_before_d2h = 1",
        "certificate_false_negatives = 0",
        "certificate_missing_required_attempts = 0",
        "skipped_groups = 1",
        "skipped_attempts = 1",
        "conservative_fallback_groups = 0",
        "certificate_cuda_api_gate_pass = 1",
        "first1_runtime_reduction_allowed = 0",
        "output_authority_changed = 0",
        "next_valid_gate = first1_reducing_runtime_with_certificate_or_no_go",
        "current_next_pr = fasim_new_gpu_engine_first1_reducing_runtime_or_no_go",
        "make check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-producer-first1",
        "roadmap_broad_restart_gate = current_architecture_no_go",
        "broad_gate_rows_clean = 0",
        "synthetic broad weak matrix:",
        "synthetic broad complete matrix:",
        "make check-fasim-gasal2-roadmap-phase8-completion-decision",
        "phase8_completion_decision_gate = complete_scoped_path_a",
        "final_goal_decision = complete_scoped_path_a",
        "scope_or_broad_design_decision_packet = defined",
        "current_decision = path_a_scoped_completion_accepted",
        "current_v4_source_replay_must_not_continue = 1",
        "scope_or_broad_design_decision_required = 0",
        "path_a_user_acceptance_required = 0",
        "path_b_new_broad_architecture_required = 0",
        "must_not_call_update_goal_complete = 0",
    ]
    for phrase in required_phrases:
        _require(roadmap, phrase, "roadmap")

    forbidden_current_state_phrases = [
        "Run only the v4 source first64 broad gate, or use Path A scoped completion",
        "The next phase must run the same GPU legacy-byte scoreInfo source through first64",
    ]
    for phrase in forbidden_current_state_phrases:
        _forbid(roadmap, phrase, "roadmap")
        _forbid(phase_checklist, phrase, "phase checklist")

    phase_checklist_required = [
        "Path A: scoped completion",
        "Path B: broad completion",
        "Phase 0: Reproducibility",
        "Phase 1: Scoped Product Contract",
        "Phase 2: Full-Output Equivalence Baseline",
        "Phase 3: Pre-Convert CPU Reduction",
        "Phase 4: Sort/Top-N Optimization",
        "Phase 5: Archive Artifact",
        "Phase 6: Workload Matrix",
        "Phase 7: Broad Replacement Restart",
        "Phase 8: Completion Decision",
        "broad_objective_status = open",
        "Current Path A decision:",
        "scope_or_broad_design_decision_required = 0",
        "path_a_user_acceptance_required = 0",
        "path_b_new_broad_architecture_required = 0",
        "completion_guard_cleared = 1",
        "goal_completion_status = complete",
        "must_not_call_update_goal_complete = 0",
        "current broad sources are stopped/no-go",
        "v4 scoreInfo-native GPU design defined",
        "v4 legacy-byte scoreInfo host-contract smoke clean",
        "v4 GPU legacy-byte scoreInfo first1 shadow clean",
        "v4 GPU legacy-byte scoreInfo source replay first1 clean",
        "v4 GPU legacy-byte scoreInfo source first64 broad gate no-go",
        "v5 fused scoreInfo consumer design defined",
        "v5 post-scoreInfo descriptor scaffold no-go",
        "v5 true pre-scoreInfo descriptor source design defined",
        "v5 true pre-scoreInfo descriptor source env scaffold fail-closed",
        "v5 true pre-scoreInfo descriptor source strict runtime smoke pass",
        "v5 CPU-authority replay first1 smoke pass",
        "v5 CPU-authority replay first64 broad gate no-go",
        "next Path B gate = pre_d2h_output_inert_proof_search_first1_export",
        "post-v5.3 pre-D2H proof-search design defined",
        "v5 CUDA descriptor emission design defined",
    ]
    for phrase in phase_checklist_required:
        _require(phase_checklist, phrase, "phase checklist")

    scoped_ready = matrix["claimed_clean"] == "1"
    broad_open = matrix["has_broad_claim"] == "0" and matrix["blocked_or_unclaimed"] != "0"
    scoped_accepted = scoped_ready and path_a_accepted

    output = {
        "phase_checklist": "defined",
        "canonical_phase_plan": "defined",
        "goal_closure_phase_plan": "defined",
        "phase0_reproducibility": "ready",
        "phase1_scoped_contract": (
            "accepted"
            if scoped_accepted
            else ("ready_if_user_accepts_scope" if scoped_ready else "not_ready")
        ),
        "path_a_scoped_completion_acceptance_packet": "defined",
        "user_scope_acceptance_recorded": "1" if path_a_accepted else "0",
        "scoped_completion_may_close_goal": "1" if scoped_accepted else "0",
        "phase2_equivalence_first_convert": "ready",
        "phase3_preconvert_prune": "not_ready_current_prune_no_go",
        "phase3_cigar_nt_prefilter_design": "defined_shadow_first",
        "phase3_cigar_nt_prefilter_shadow": "proof_smoke_clean",
        "phase3_cigar_nt_prefilter_full": "proof_clean_low_savings",
        "phase3_cigar_nt_prefilter_real_validate": (
            "full_clean_no_speedup_default_off"
        ),
        "phase4_sort_topn": "not_first_priority",
        "phase5_archive_artifact": "ready",
        "phase6_workload_matrix": "claimed_scope_only",
        "phase7_broad_restart": "current_architecture_no_go",
        "phase7_next_reducer_scaffold": "bounded_go_not_broad",
        "phase7_next_reducer_broad_gate": "correctness_no_go",
        "phase7_broad_restart_v2_design": "defined_frontier_log_first",
        "phase7_broad_restart_v2_frontier_log_scaffold": (
            "runtime_smoke_clean_not_replay_proof"
        ),
        "phase7_broad_restart_v2_frontier_replay": (
            "exact_no_reduction_not_broad"
        ),
        "phase7_broad_restart_v2_frontier_reducer": (
            "oracle_reduction_projected_not_broad"
        ),
        "phase7_broad_restart_v2_frontier_predictor": (
            "no_go_current_features"
        ),
        "phase7_broad_restart_v2_frontier_score_signal": "no_go",
        "phase7_broad_restart_v2_frontier_early_stop": (
            "candidate_not_measured"
        ),
        "phase7_broad_restart_v2_frontier_early_stop_runtime": (
            "runtime_smoke_clean_needs_neat1_first1"
        ),
        "phase7_broad_restart_v2_frontier_early_stop_runtime_first1": (
            "correctness_no_go"
        ),
        "phase7_next_reducer_after_early_stop_no_go_design": "defined",
        "phase7_all_attempt_early_stop_runtime_first1": (
            "correctness_go_needs_first64"
        ),
        "phase7_all_attempt_early_stop_runtime_first64": (
            "correctness_go_near_parity_not_broad"
        ),
        "phase7_gate_c_gpu_candidate_generator_design": "defined",
        "phase7_gate_c_gpu_candidate_generator_implementation_plan": "defined",
        "phase7_gate_c_runtime_smoke": "oracle_metric_scaffold_clean_not_first1",
        "phase7_gate_c_first1": "no_go_no_gpu_candidate_descriptors",
        "phase7_gate_c_stop_checkpoint": "current_source_no_go",
        "phase7_current_broad_stop_decision": "current_broad_sources_no_go",
        "phase7_broad_restart_v3_candidate_certificate_design": "defined",
        "phase7_broad_restart_v3_current_status": "design_only",
        "phase7_broad_restart_v3_next_gate": "descriptor_source_smoke",
        "phase7_broad_restart_v3_may_claim_completion": "0",
        "phase7_broad_restart_v3_descriptor_source_smoke": (
            "current_no_pre_scoreinfo_source"
        ),
        "phase7_broad_restart_v3_gate_v3_1_pass": "0",
        "phase7_broad_restart_v3_may_continue_to_first64": "0",
        "phase7_broad_restart_v3_runtime_next_gate": (
            "real_pre_scoreinfo_descriptor_source"
        ),
        "phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke": (
            "pre_scoreinfo_descriptors_no_reduction"
        ),
        "phase7_broad_restart_v3_pre_scoreinfo_current_status": (
            "pre_scoreinfo_scaffold_no_go"
        ),
        "phase7_broad_restart_v3_pre_scoreinfo_next_gate": (
            "certificate_checked_scoreinfo_reducing_descriptor_source"
        ),
        "phase7_broad_restart_v3_certificate_smoke": (
            "certificate_checked_no_scoreinfo_reduction"
        ),
        "phase7_broad_restart_v3_certificate_current_status": (
            "certificate_scaffold_no_go"
        ),
        "phase7_broad_restart_v3_certificate_next_gate": (
            "scoreinfo_reducing_candidate_certificate"
        ),
        "phase7_broad_restart_v3_all_column_certificate_smoke": (
            "scoreinfo_reducing_all_column_certificate"
        ),
        "phase7_broad_restart_v3_all_column_current_status": (
            "gate_v3_1_pass_attempt_overgenerate"
        ),
        "phase7_broad_restart_v3_gate_v3_2_pass": "0",
        "phase7_broad_restart_v3_all_column_next_gate": (
            "narrower_scoreinfo_reducing_certificate"
        ),
        "phase7_broad_restart_v3_all_column_replay_stop": (
            "candidate_attempt_explosion_no_go"
        ),
        "phase7_broad_restart_v3_do_not_run_all_column_cpu_replay": "1",
        "phase7_broad_restart_v3_candidate_attempt_ratio": "58750.30x",
        "phase7_broad_restart_v3_current_next_gate": (
            "different_exact_scoreinfo_source_or_seed_certificate"
        ),
        "phase7_broad_restart_v3_narrow_certificate_design": "defined",
        "phase7_broad_restart_v3_narrow_certificate_status": "design_only",
        "phase7_broad_restart_v3_narrow_certificate_next_gate": (
            "real_narrow_certificate_coverage_proof"
        ),
        "phase7_broad_restart_v3_narrow_certificate_smoke": (
            "bounded_probe_no_go_missing_certificate"
        ),
        "phase7_broad_restart_v3_narrow_certificate_runtime_status": (
            "runtime_smoke_no_go"
        ),
        "phase7_broad_restart_v3_real_narrow_certificate_coverage_proof": (
            "exact_column_candidate_no_go"
        ),
        "phase7_broad_restart_v3_exact_column_candidate_status": "no_go",
        "phase7_broad_restart_v3_real_narrow_next_gate": (
            "different_exact_scoreinfo_source_or_seed_certificate"
        ),
        "phase7_broad_restart_v3_next_source_design": "defined",
        "phase7_broad_restart_v3_next_source_status": "design_only",
        "phase7_broad_restart_v3_next_source_next_gate": (
            "different_exact_scoreinfo_source_or_seed_certificate_smoke"
        ),
        "phase7_broad_restart_v3_next_source_smoke": (
            "seed_certificate_fail_closed"
        ),
        "phase7_broad_restart_v3_next_source_runtime_status": (
            "runtime_smoke_no_go"
        ),
        "phase7_broad_restart_v3_next_source_runtime_next_gate": (
            "stronger_seed_certificate_or_different_exact_scoreinfo_source"
        ),
        "phase7_broad_restart_v3_strong_seed_smoke": (
            "task_coverage_clean_attempt_coverage_missing"
        ),
        "phase7_broad_restart_v3_strong_seed_status": (
            "runtime_smoke_no_go_attempt_coverage"
        ),
        "phase7_broad_restart_v3_strong_seed_next_gate": (
            "attempt_coverage_seed_certificate_or_different_exact_scoreinfo_source"
        ),
        "phase7_broad_restart_v3_attempt_coverage_seed_smoke": (
            "attempt_coverage_clean_needs_replay_preflight"
        ),
        "phase7_broad_restart_v3_attempt_coverage_seed_status": (
            "gate_v3_1_pass_candidate_attempts_high"
        ),
        "phase7_broad_restart_v3_attempt_coverage_seed_next_gate": (
            "oracle_min_cover_replay_shape_probe_or_non_oracle_candidate_reducer"
        ),
        "phase7_broad_restart_v3_oracle_min_cover_replay_smoke": "output_no_go",
        "phase7_broad_restart_v3_oracle_min_cover_replay_status": (
            "oracle_shape_probe_no_go"
        ),
        "phase7_broad_restart_v3_oracle_min_cover_replay_next_gate": (
            "non_oracle_candidate_reducer_or_stop_seed_path"
        ),
        "phase7_broad_restart_v3_seed_path_stop": (
            "current_seed_index_path_stopped"
        ),
        "phase7_broad_restart_v3_seed_path_status": (
            "stopped_no_output_clean_non_oracle_reducer"
        ),
        "phase7_broad_restart_v3_final_next_gate": (
            "different_scoreinfo_compatible_gpu_execution_design_or_path_a_scope_decision"
        ),
        "phase7_broad_restart_v4_scoreinfo_native_design": "defined",
        "phase7_broad_restart_v4_status": "design_only",
        "phase7_broad_restart_v4_next_gate": (
            "legacy_byte_scoreinfo_shadow_first1"
        ),
        "phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke": (
            "host_contract_clean_needs_gpu"
        ),
        "phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_status": (
            "host_reconstruction_clean_gpu_rows_zero"
        ),
        "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke": (
            "gpu_contract_clean_first1"
        ),
        "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_status": (
            "first1_gpu_rows_equal_not_broad"
        ),
        "phase7_broad_restart_v4_gpu_scoreinfo_rows": "718",
        "phase7_broad_restart_v4_runtime_next_gate": (
            "different_gpu_execution_design_or_path_a_scope_decision"
        ),
        "phase7_broad_restart_v4_gate_v4_1_pass": "1",
        "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke": (
            "cpu_authority_replay_clean_first1"
        ),
        "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_status": (
            "first1_replay_clean_needs_first64_broad_gate"
        ),
        "phase7_broad_restart_v4_source_replay_align_attempts": "2008",
        "phase7_broad_restart_v4_source_replay_reference_align_attempts": "2872",
        "phase7_broad_restart_v4_source_replay_align_attempt_reduction": "864",
        "phase7_broad_restart_v4_gate_v4_2_pass": "1",
        "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate": (
            "correctness_clean_performance_no_go"
        ),
        "phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_status": (
            "first64_correctness_clean_performance_no_go"
        ),
        "phase7_broad_restart_v4_source_first64_baseline_wall_seconds": (
            "86.358386"
        ),
        "phase7_broad_restart_v4_source_first64_candidate_wall_seconds": (
            "134.744406"
        ),
        "phase7_broad_restart_v4_source_first64_candidate_vs_baseline": (
            "0.640905"
        ),
        "phase7_broad_restart_v4_source_first64_digest_match": "1",
        "phase7_broad_restart_v4_source_first64_align_attempts": "140087",
        "phase7_broad_restart_v4_source_first64_reference_align_attempts": (
            "211976"
        ),
        "phase7_broad_restart_v4_source_first64_align_attempt_reduction": (
            "71889"
        ),
        "phase7_broad_restart_v4_gate_v4_3_pass": "0",
        "phase7_broad_restart_v5_fused_scoreinfo_consumer_design": "defined",
        "phase7_broad_restart_v5_status": "design_only",
        "phase7_broad_restart_v5_design_family": (
            "fused_gpu_scoreinfo_to_candidate_attempt_descriptors"
        ),
        "phase7_broad_restart_v5_differs_from_v4_source_replay": "1",
        "phase7_broad_restart_v5_gate_v5_1_pass": "1",
        "phase7_broad_restart_v5_gate_v5_2_pass": "1",
        "phase7_broad_restart_v5_gate_v5_3_pass": "0",
        "phase7_broad_restart_v5_next_gate": (
            "different_gpu_execution_design_or_path_a_scope_decision"
        ),
        "phase7_broad_restart_v5_implementation_plan": "defined",
        "phase7_broad_restart_v5_runtime_first_gate": (
            "fused_scoreinfo_consumer_descriptor_contract_first1"
        ),
        "phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke": (
            "post_scoreinfo_descriptor_scaffold_no_go"
        ),
        "phase7_broad_restart_v5_runtime_scaffold_requested": "1",
        "phase7_broad_restart_v5_runtime_scaffold_active": "1",
        "phase7_broad_restart_v5_runtime_scaffold_gpu_descriptor_attempts": "2872",
        "phase7_broad_restart_v5_runtime_scaffold_descriptor_false_negatives": "0",
        "phase7_broad_restart_v5_runtime_scaffold_missing_required_attempts": "0",
        "phase7_broad_restart_v5_runtime_scaffold_scoreinfo_prealign_reduced": "0",
        "phase7_broad_restart_v5_runtime_scaffold_cpu_align_authority": "1",
        "phase7_broad_restart_v5_runtime_scaffold_gpu_endpoint_cigar_traceback_output_authority": "0",
        "phase7_broad_restart_v5_runtime_scaffold_next_gate": (
            "true_pre_scoreinfo_fused_descriptor_source"
        ),
        "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design": (
            "defined"
        ),
        "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_status": (
            "design_only"
        ),
        "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_next_gate": (
            "runtime_smoke_true_pre_scoreinfo_descriptor_source_first1"
        ),
        "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_env_scaffold": (
            "fail_closed_no_source"
        ),
        "phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke": (
            "gate_v5_1_pass_first1"
        ),
        "phase7_broad_restart_v5_next_required_gate": (
            "different_gpu_execution_design_or_path_a_scope_decision"
        ),
        "phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate": (
            "correctness_clean_performance_no_go"
        ),
        "phase7_broad_restart_v5_cpu_authority_replay_first64_status": (
            "first64_correctness_clean_performance_no_go"
        ),
        "phase7_broad_restart_v5_first64_candidate_vs_baseline": "0.706009",
        "phase7_broad_restart_v5_first64_digest_match": "1",
        "phase7_broad_restart_v5_first64_full_rows_equal": "1",
        "phase7_broad_restart_v5_first64_missing_required_attempts": "624",
        "phase7_broad_restart_v5_first64_fallback_accounting_clean": "0",
        "phase7_broad_restart_v5_runtime_next_gate": (
            "different_gpu_execution_design_or_path_a_scope_decision"
        ),
        "phase7_post_v5_3_architecture_decision": "defined",
        "phase7_post_v5_3_current_v5_status": "stopped_no_go",
        "phase7_post_v5_3_next_gate": (
            "post_v5_3_task_frontier_certificate_first1_smoke"
        ),
        "phase7_post_v5_3_next_required_gate": (
            "post_v5_3_task_frontier_certificate_first1_smoke"
        ),
        "phase7_post_v5_3_new_architecture_design": "defined",
        "phase7_post_v5_3_design_family": (
            "gpu_resident_scoreinfo_consumer_summary_with_cpu_authority_replay"
        ),
        "phase7_post_v5_3_new_architecture_may_implement": "1",
        "phase7_post_v5_3_new_architecture_may_claim_completion": "0",
        "phase7_post_v5_3_new_architecture_next_gate": (
            "post_v5_3_gpu_consumer_summary_first1_smoke"
        ),
        "phase7_post_v5_3_gpu_consumer_summary_env_scaffold": (
            "fail_closed_no_source"
        ),
        "phase7_post_v5_3_gpu_consumer_summary_active": "0",
        "phase7_post_v5_3_gpu_consumer_summary_gate_first1_pass": "0",
        "phase7_post_v5_3_gpu_consumer_summary_next_gate": (
            "stronger_post_v5_3_consumer_summary_design_or_path_a_acceptance"
        ),
        "phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go": "recorded",
        "phase7_post_v5_3_gpu_consumer_summary_first_attempt_status": "no_go",
        "phase7_post_v5_3_gpu_consumer_summary_first1_gate_pass": "0",
        "phase7_post_v5_3_gpu_consumer_summary_external_digest_match": "0",
        "phase7_post_v5_3_gpu_consumer_summary_external_full_rows_equal": "0",
        "phase7_post_v5_3_gpu_consumer_summary_gpu_selected_attempts": "718",
        "phase7_post_v5_3_gpu_consumer_summary_candidate_align_attempts": "718",
        "phase7_post_v5_3_gpu_consumer_summary_reference_align_attempts": "2872",
        "phase7_post_v5_3_stronger_consumer_summary_design": "defined",
        "phase7_post_v5_3_stronger_consumer_summary_status": "design_only",
        "phase7_post_v5_3_stronger_consumer_summary_may_implement": "1",
        "phase7_post_v5_3_stronger_consumer_summary_may_claim_completion": "0",
        "phase7_post_v5_3_stronger_consumer_summary_next_gate": (
            "post_v5_3_stronger_consumer_summary_first1_smoke"
        ),
        "phase7_post_v5_3_stronger_consumer_summary_prefix_no_go": (
            "recorded"
        ),
        "phase7_post_v5_3_stronger_consumer_summary_first1_gate_pass": "0",
        "phase7_post_v5_3_stronger_consumer_summary_prefix_next_gate": (
            "different_gpu_execution_design_or_path_a_scope_decision"
        ),
        "phase7_post_v5_3_task_frontier_certificate_design": "defined",
        "phase7_post_v5_3_task_frontier_certificate_status": "design_only",
        "phase7_post_v5_3_task_frontier_certificate_may_implement": "1",
        "phase7_post_v5_3_task_frontier_certificate_may_claim_completion": "0",
        "phase7_post_v5_3_task_frontier_certificate_next_gate": (
            "post_v5_3_task_frontier_certificate_first1_smoke"
        ),
        "phase7_post_v5_3_task_frontier_certificate_env_scaffold": (
            "superseded_by_first_attempt_no_go"
        ),
        "phase7_post_v5_3_task_frontier_certificate_requested": "1",
        "phase7_post_v5_3_task_frontier_certificate_active": "0",
        "phase7_post_v5_3_task_frontier_certificate_gate_first1_pass": "0",
        "phase7_post_v5_3_task_frontier_certificate_env_runtime_smoke": (
            "superseded_by_first_attempt_no_go"
        ),
        "phase7_post_v5_3_task_frontier_certificate_first_attempt_status": (
            "no_go"
        ),
        "phase7_post_v5_3_task_frontier_certificate_external_digest_match": (
            "0"
        ),
        "phase7_post_v5_3_task_frontier_certificate_external_full_rows_equal": (
            "0"
        ),
        "phase7_post_v5_3_task_frontier_certificate_missing_rows": "17",
        "phase7_post_v5_3_task_frontier_certificate_gpu_selected_attempts": (
            "192"
        ),
        "phase7_post_v5_3_task_frontier_certificate_candidate_align_attempts": (
            "138"
        ),
        "phase7_post_v5_3_task_frontier_certificate_reference_align_attempts": (
            "2872"
        ),
        "phase7_post_v5_3_stronger_task_frontier_certificate_design": (
            "defined"
        ),
        "phase7_post_v5_3_stronger_task_frontier_certificate_status": (
            "feasibility_no_go"
        ),
        "phase7_post_v5_3_stronger_task_frontier_certificate_may_implement": (
            "1"
        ),
        "phase7_post_v5_3_stronger_task_frontier_certificate_may_claim_completion": (
            "0"
        ),
        "phase7_post_v5_3_stronger_task_frontier_certificate_next_gate": (
            "new_pre_d2h_output_inert_proof_or_different_gpu_execution_design_or_path_a_scope_decision"
        ),
        "phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go": (
            "recorded"
        ),
        "phase7_post_v5_3_stronger_task_frontier_certificate_first1_smoke_allowed": (
            "0"
        ),
        "phase7_post_v5_3_stronger_task_frontier_certificate_do_not_implement_current_runtime": (
            "1"
        ),
        "phase7_post_v5_3_pre_d2h_output_inert_proof_search_design": (
            "defined"
        ),
        "phase7_post_v5_3_pre_d2h_output_inert_proof_search_status": (
            "first1_export_pass"
        ),
        "phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export": (
            "pass"
        ),
        "phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_implement": (
            "1"
        ),
        "phase7_post_v5_3_pre_d2h_output_inert_proof_search_may_claim_completion": (
            "0"
        ),
        "phase7_post_v5_3_pre_d2h_output_inert_proof_search_next_gate": (
            "pre_d2h_output_inert_proof_acceptance_first1"
        ),
        "phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1": (
            "no_go"
        ),
        "phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_status": (
            "first1_no_accepted_proof"
        ),
        "phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_accepted_families": (
            "0"
        ),
        "phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_reducing_runtime_allowed": (
            "0"
        ),
        "phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first64_runtime_allowed": (
            "0"
        ),
        "phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision": (
            "defined"
        ),
        "phase7_post_v5_3_new_pre_d2h_path_a_user_acceptance_required": "1",
        "phase7_post_v5_3_new_pre_d2h_path_b_new_proof_family_required": "1",
        "phase7_post_v5_3_new_pre_d2h_runtime_reduction_enabled": "0",
        "phase7_post_v5_3_new_pre_d2h_first64_runtime_allowed": "0",
        "phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go": (
            "recorded"
        ),
        "phase7_post_v5_3_new_pre_d2h_current_descriptor_stream_can_prove_output_inert_skips": (
            "0"
        ),
        "phase7_post_v5_3_new_pre_d2h_first1_smoke_allowed": "0",
        "phase7_post_v5_3_new_pre_d2h_different_gpu_execution_design_required": (
            "1"
        ),
        "phase7_post_v5_3_different_gpu_execution_design_or_scope_acceptance": (
            "recorded"
        ),
        "phase7_post_v5_3_path_b_different_gpu_execution_design_required": (
            "1"
        ),
        "phase7_post_v5_3_path_b_current_implementation_available": "0",
        "phase7_post_v5_3_path_b_runtime_pr_allowed": "0",
        "phase7_post_v5_3_next_valid_work": (
            "path_a_scoped_acceptance_or_new_engine_design_doc"
        ),
        "phase7_post_v5_3_new_gpu_engine_design": "defined",
        "phase7_post_v5_3_new_gpu_engine_design_family": (
            "fasim_compatible_gpu_scoreinfo_attempt_engine"
        ),
        "phase7_post_v5_3_new_gpu_engine_runtime_pr_allowed": "0",
        "phase7_post_v5_3_new_gpu_engine_current_runtime_available": "0",
        "phase7_post_v5_3_new_gpu_engine_next_gate": (
            "phase7_new_gpu_engine_spec_or_path_a_acceptance"
        ),
        "phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance": (
            "defined"
        ),
        "phase7_post_v5_3_new_gpu_engine_spec_path_a_user_acceptance_recorded": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_spec_path_a_scoped_completion_may_close_goal": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_spec_path_b_spec_checkpoint_defined": (
            "1"
        ),
        "phase7_post_v5_3_new_gpu_engine_spec_path_b_runtime_implementation_allowed": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_spec_runtime_pr_allowed": "0",
        "phase7_post_v5_3_new_gpu_engine_spec_next_gate": (
            "phase7_new_gpu_engine_first1_spec_or_path_a_acceptance"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance": (
            "defined"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_path_a_user_acceptance_recorded": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_path_a_scoped_completion_may_close_goal": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_path_b_first1_spec_defined": (
            "1"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_path_b_first1_runtime_allowed": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_runtime_pr_allowed": "0",
        "phase7_post_v5_3_new_gpu_engine_first1_next_gate": (
            "phase7_new_gpu_engine_first1_shadow_or_path_a_acceptance"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect": (
            "recorded"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_reviewed_runtime": (
            "FASIM_GASAL2_PHASE7_V5_CPU_AUTHORITY_REPLAY"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_reviewed_source": (
            "PreAlignCudaAttemptDescriptor"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_existing_v5_gate_pass": (
            "1"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_v5_matches_new_spec": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_gate_pass": "0",
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_next_gate": (
            "implement_new_gpu_engine_first1_shadow_or_path_a_acceptance"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold": (
            "fail_closed"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold_requested": "1",
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold_active": "0",
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold_missing_certificate_producer": (
            "1"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold_certificate_valid_before_d2h": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold_gate_pass": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold_next_gate": (
            "implement_new_gpu_engine_certificate_cuda_api_or_path_a_acceptance"
        ),
        "phase7_post_v5_3_new_gpu_engine_certificate_cuda_api": (
            "fail_closed_api_scaffold"
        ),
        "phase7_post_v5_3_new_gpu_engine_certificate_cuda_api_gate_pass": "0",
        "phase7_post_v5_3_new_gpu_engine_certificate_producer_first1": (
            "producer_first1_synthetic_gate"
        ),
        "certificate_producer_active": "1",
        "certificate_valid_before_d2h": "1",
        "certificate_false_negatives": "0",
        "certificate_missing_required_attempts": "0",
        "phase7_post_v5_3_new_gpu_engine_certificate_producer_first1_gate_pass": "1",
        "phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go": (
            "recorded"
        ),
        "first1_runtime_reduction_gate_pass": "0",
        "real_fasim_runtime_certificate_source": "1",
        "real_fasim_runtime_work_drop_path": "0",
        "path_b_runtime_pr_allowed": "0",
        "phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go": (
            "defined"
        ),
        "phase7_post_v5_3_new_gpu_engine_after_no_go_design_family": (
            "real_source_fasim_compatible_gpu_scoreinfo_attempt_engine"
        ),
        "phase7_post_v5_3_new_gpu_engine_after_no_go_real_source_required": (
            "1"
        ),
        "phase7_post_v5_3_new_gpu_engine_after_no_go_work_drop_point_required": (
            "1"
        ),
        "phase7_post_v5_3_new_gpu_engine_after_no_go_runtime_pr_allowed": "0",
        "phase7_post_v5_3_new_gpu_engine_real_source_first1_spec": (
            "defined"
        ),
        "phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_hook": (
            "scoreInfo/preAlign_task_construction"
        ),
        "phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_certificate_source": (
            "gpu_scoreinfo_attempt_engine_before_d2h"
        ),
        "phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_work_drop_point": (
            "before_cpu_aligner_align_attempt_skip"
        ),
        "phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_defined": "1",
        "phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scaffold": (
            "fail_closed_no_real_source"
        ),
        "phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_gate_pass": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_real_source_first1_first64_runtime_allowed": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_real_source_certificate_source": (
            "source_only_pre_drop_runtime_hook"
        ),
        "phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_pass": (
            "1"
        ),
        "phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_reduction_enabled": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_gate_first1_pass": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design": (
            "defined"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design_status": (
            "design_only"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design_runtime_reduction_enabled": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design_runtime_work_drop_enabled": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow": (
            "fail_closed_shadow"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_status": (
            "fail_closed_no_runtime_reduction"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_reduction_enabled": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_work_drop_enabled": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_gate_first1_proof_pass": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go": (
            "recorded"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_status": (
            "no_go_current_descriptor_stream"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_runtime_reduction_enabled": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_runtime_work_drop_enabled": (
            "0"
        ),
        "phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_gate_first1_proof_pass": (
            "0"
        ),
        "path_b_current_family_stopped": "1",
        "phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go": (
            "defined"
        ),
        "phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go_status": (
            "design_defined"
        ),
        "phase7_post_v5_3_path_b_new_design_family": (
            "fasim_compatible_gpu_scoreinfo_frontier_certificate_engine"
        ),
        "path_b_runtime_pr_allowed": "0",
        "path_b_docs_spec_allowed": "1",
        "path_b_current_descriptor_family_stopped": "1",
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance": (
            "defined"
        ),
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_status": (
            "spec_defined"
        ),
        "path_b_scoreinfo_certificate_engine_spec_defined": "1",
        "path_b_first1_fail_closed_shadow_scaffold_allowed": "1",
        "path_b_runtime_reduction_pr_allowed": "0",
        "path_b_runtime_work_drop_allowed": "0",
        "path_b_first64_runtime_allowed": "0",
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold": (
            "fail_closed_shadow"
        ),
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold_status": (
            "fail_closed_no_runtime_reduction"
        ),
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_runtime_reduction_enabled": "0",
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_runtime_work_drop_enabled": "0",
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_gate_first1_shadow_pass": "0",
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go": (
            "recorded"
        ),
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_status": (
            "no_go_no_valid_pre_drop_certificate"
        ),
        "path_b_scoreinfo_certificate_engine_family_stopped": "1",
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_runtime_reduction_enabled": "0",
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_runtime_work_drop_enabled": "0",
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_gate_first1_pass": "0",
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_next_valid_gate": (
            "path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go"
        ),
        "phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_current_next_pr": (
            "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go"
        ),
        "path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go": (
            "recorded"
        ),
        "path_b_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go_status": (
            "design_defined"
        ),
        "path_b_new_design_family_after_scoreinfo_cert_engine_no_go": (
            "gpu_owned_fasim_scoreinfo_consumer_with_pre_drop_frontier_certificate"
        ),
        "path_b_runtime_pr_allowed": "0",
        "path_b_docs_spec_allowed": "1",
        "path_b_scoreinfo_certificate_engine_family_stopped": "1",
        "phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance": (
            "defined"
        ),
        "phase7_gpu_owned_scoreinfo_consumer_design_spec_status": "spec_defined",
        "phase7_gpu_owned_scoreinfo_consumer_design_spec_previous_next_pr": (
            "fasim_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance"
        ),
        "path_b_gpu_owned_scoreinfo_consumer_spec_defined": "1",
        "path_b_gpu_owned_first1_fail_closed_shadow_allowed": "1",
        "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold": (
            "fail_closed_shadow"
        ),
        "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold_status": (
            "fail_closed_no_runtime_reduction"
        ),
        "path_b_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold": "1",
        "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_reduction_enabled": "0",
        "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_work_drop_enabled": "0",
        "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_gate_first1_shadow_pass": "0",
        "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go": (
            "recorded"
        ),
        "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_status": (
            "no_go_no_valid_pre_drop_certificate"
        ),
        "accepted_gpu_owned_scoreinfo_consumer": "0",
        "accepted_pre_drop_frontier_certificate": "0",
        "path_b_gpu_owned_scoreinfo_consumer_family_stopped": "1",
        "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_runtime_reduction_enabled": "0",
        "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_runtime_work_drop_enabled": "0",
        "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_gate_first1_pass": "0",
        "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_next_valid_gate": (
            "path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go"
        ),
        "phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_current_next_pr": (
            "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go"
        ),
        "path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go": (
            "recorded"
        ),
        "path_b_different_gpu_execution_design_after_gpu_owned_consumer_no_go_status": (
            "design_defined"
        ),
        "path_b_new_design_family": (
            "gasal2_full_align_result_with_cpu_verifier_certificate"
        ),
        "path_b_differs_from_gpu_owned_scoreinfo_consumer": "1",
        "path_b_differs_from_scoreinfo_certificate_engine": "1",
        "path_b_differs_from_post_v5_3_descriptor_stream": "1",
        "path_b_runtime_pr_allowed": "0",
        "path_b_docs_spec_allowed": "1",
        "phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance": (
            "defined"
        ),
        "phase7_full_align_verifier_design_spec_status": "spec_defined",
        "path_b_design_family": (
            "gasal2_full_align_result_with_cpu_verifier_certificate"
        ),
        "path_b_full_align_verifier_spec_defined": "1",
        "path_b_full_align_verifier_first1_fail_closed_shadow_allowed": "1",
        "phase7_gasal2_full_align_verifier_first1_shadow_scaffold": (
            "fail_closed_shadow"
        ),
        "phase7_full_align_verifier_first1_shadow_scaffold_status": (
            "fail_closed_no_runtime_reduction"
        ),
        "path_b_full_align_verifier_first1_shadow_scaffold": "1",
        "phase7_full_align_verifier_runtime_reduction_enabled": "0",
        "phase7_full_align_verifier_runtime_work_drop_enabled": "0",
        "phase7_full_align_verifier_gate_first1_shadow_pass": "0",
        "phase7_full_align_verifier_first64_runtime_allowed": "0",
        "phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go": (
            "recorded"
        ),
        "phase7_full_align_verifier_first1_shadow_consumer_status": (
            "no_go_no_gpu_full_align_proposals"
        ),
        "accepted_full_align_verifier_consumer": "0",
        "accepted_full_align_verifier_certificate": "0",
        "accepted_gasal2_full_align_proposals": "0",
        "path_b_full_align_verifier_family_stopped": "1",
        "phase7_full_align_verifier_first1_shadow_consumer_runtime_reduction_enabled": "0",
        "phase7_full_align_verifier_first1_shadow_consumer_runtime_work_drop_enabled": "0",
        "phase7_full_align_verifier_first1_shadow_consumer_gate_first1_pass": "0",
        "phase7_full_align_verifier_first1_shadow_consumer_next_valid_gate": (
            "path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go"
        ),
        "phase7_full_align_verifier_first1_shadow_consumer_current_next_pr": (
            "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go"
        ),
        "path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go": (
            "recorded"
        ),
        "path_b_different_gpu_execution_design_after_full_align_verifier_no_go_status": (
            "design_defined"
        ),
        "path_b_new_design_family_after_full_align_verifier_no_go": (
            "native_cuda_fasim_dp_certificate_engine"
        ),
        "path_b_differs_from_gasal2_full_align_verifier": "1",
        "path_b_differs_from_gasal2_align_replacement": "1",
        "path_b_differs_from_gpu_owned_scoreinfo_consumer": "1",
        "path_b_differs_from_scoreinfo_certificate_engine": "1",
        "path_b_differs_from_post_v5_3_descriptor_stream": "1",
        "path_b_full_align_verifier_family_stopped": "1",
        "path_b_runtime_pr_allowed": "0",
        "path_b_docs_spec_allowed": "1",
        "phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance": (
            "defined"
        ),
        "phase7_native_cuda_fasim_dp_engine_design_spec_status": (
            "spec_defined"
        ),
        "path_b_native_cuda_fasim_dp_engine_spec_defined": "1",
        "path_b_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_allowed": (
            "1"
        ),
        "phase7_native_cuda_fasim_dp_engine_runtime_reduction_enabled": "0",
        "phase7_native_cuda_fasim_dp_engine_runtime_work_drop_enabled": "0",
        "phase7_native_cuda_fasim_dp_engine_first64_runtime_allowed": "0",
        "phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold": (
            "fail_closed_shadow"
        ),
        "phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold_status": (
            "fail_closed_no_runtime_reduction"
        ),
        "phase7_native_cuda_fasim_dp_engine_gate_first1_shadow_pass": "0",
        "phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_no_go": (
            "recorded"
        ),
        "phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_status": (
            "no_go_no_native_dp_certificates"
        ),
        "accepted_native_cuda_fasim_dp_engine_consumer": "0",
        "accepted_native_dp_certificate": "0",
        "path_b_native_cuda_fasim_dp_engine_family_stopped": "1",
        "phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_next_valid_gate": (
            "path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go"
        ),
        "phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_current_next_pr": (
            "fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go"
        ),
        "path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go": (
            "recorded"
        ),
        "path_b_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go_status": (
            "required_not_defined"
        ),
        "path_b_new_design_family_after_native_cuda_fasim_dp_engine_no_go": (
            "undefined"
        ),
        "path_b_new_design_family_spec_required_after_native_cuda_fasim_dp_engine_no_go": (
            "1"
        ),
        "path_b_native_cuda_fasim_dp_engine_family_stopped": "1",
        "path_b_runtime_pr_allowed": "0",
        "path_b_docs_spec_allowed": "1",
        "phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance": (
            "defined"
        ),
        "phase7_gpu_upper_bound_reject_certificate_design_spec_status": (
            "spec_defined"
        ),
        "path_b_gpu_upper_bound_reject_certificate_spec_defined": "1",
        "path_b_gpu_upper_bound_reject_certificate_design_family": (
            "gpu_upper_bound_reject_certificate_engine"
        ),
        "path_b_gpu_upper_bound_reject_certificate_first1_fail_closed_shadow_allowed": (
            "1"
        ),
        "phase7_gpu_upper_bound_reject_certificate_runtime_reduction_enabled": "0",
        "phase7_gpu_upper_bound_reject_certificate_runtime_work_drop_enabled": "0",
        "phase7_gpu_upper_bound_reject_certificate_first64_runtime_allowed": "0",
        "phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold": (
            "fail_closed_shadow"
        ),
        "phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold_status": (
            "fail_closed_no_runtime_reduction"
        ),
        "path_b_gpu_upper_bound_reject_certificate_first1_shadow_scaffold": "1",
        "phase7_gpu_upper_bound_reject_certificate_gate_first1_shadow_pass": "1",
        "phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go": (
            "recorded"
        ),
        "phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_status": (
            "no_go_no_rejected_work"
        ),
        "accepted_gpu_upper_bound_reject_certificate_consumer": "0",
        "accepted_pre_drop_reject_certificate": "0",
        "path_b_gpu_upper_bound_reject_certificate_family_stopped": "1",
        "path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go": (
            "recorded"
        ),
        "path_b_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go_status": (
            "required_not_defined"
        ),
        "path_b_new_design_family_after_gpu_upper_bound_reject_certificate_no_go": (
            "undefined"
        ),
        "path_b_new_design_family_spec_required_after_gpu_upper_bound_reject_certificate_no_go": (
            "1"
        ),
        "phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance": (
            "defined"
        ),
        "phase7_gpu_exact_work_unit_compaction_design_spec_status": (
            "spec_defined"
        ),
        "path_b_gpu_exact_work_unit_compaction_spec_defined": "1",
        "design_family": "gpu_exact_work_unit_compaction_replay",
        "path_b_gpu_exact_work_unit_compaction_first1_fail_closed_shadow_allowed": (
            "1"
        ),
        "phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold": (
            "fail_closed_shadow"
        ),
        "phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold_status": (
            "fail_closed_no_runtime_reduction"
        ),
        "path_b_gpu_exact_work_unit_compaction_first1_shadow_scaffold": "1",
        "phase7_gpu_exact_work_unit_compaction_gate_first1_shadow_pass": "1",
        "phase7_gpu_exact_work_unit_compaction_gate_first1_pass": "0",
        "phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go": (
            "recorded"
        ),
        "phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_status": (
            "no_go_no_duplicate_work"
        ),
        "accepted_exact_work_unit_compaction_consumer": "0",
        "accepted_exact_work_unit_compaction_reduction": "0",
        "accepted_scoreinfo_prealign_compaction": "0",
        "accepted_align_side_compaction": "0",
        "path_b_gpu_exact_work_unit_compaction_family_stopped": "1",
        "path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go": (
            "recorded"
        ),
        "path_b_different_gpu_execution_design_after_exact_work_unit_compaction_no_go_status": (
            "required_not_defined"
        ),
        "path_b_new_design_family_after_exact_work_unit_compaction_no_go": (
            "undefined"
        ),
        "path_b_new_design_family_spec_required_after_exact_work_unit_compaction_no_go": (
            "1"
        ),
        "new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go": (
            "recorded"
        ),
        "path_b_no_viable_new_design_family_after_exact_work_unit_compaction_no_go": (
            "1"
        ),
        "path_b_external_design_input_required_after_exact_work_unit_compaction_no_go": (
            "1"
        ),
        "path_b_docs_spec_allowed_without_new_design_input": "0",
        "path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go": (
            "recorded"
        ),
        "path_b_external_design_input_received": "0",
        "next_valid_gate": (
            "phase8_path_a_scoped_completion_accepted"
            if scoped_accepted
            else "user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go"
        ),
        "current_execution_gate": (
            "phase8_path_a_scoped_completion_accepted"
            if scoped_accepted
            else "user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go"
        ),
        "current_next_pr": (
            "none_goal_complete_scoped_path_a"
            if scoped_accepted
            else "none_until_user_scope_acceptance_or_external_path_b_design_input"
        ),
        # Current exact work-unit compaction consumer no-go anchor:
        # phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go
        # phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_status
        # no_go_no_duplicate_work
        # accepted_exact_work_unit_compaction_consumer
        # accepted_exact_work_unit_compaction_reduction
        # accepted_scoreinfo_prealign_compaction
        # accepted_align_side_compaction
        # path_b_gpu_exact_work_unit_compaction_family_stopped
        # path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
        # fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
        # Historical checker anchor retained for the GPU upper-bound reject
        # certificate scaffold checker:
        # phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go
        # fasim_gpu_upper_bound_reject_certificate_first1_shadow_consumer_or_no_go
        # Current post-no-go fork anchor:
        # path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go
        # fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go
        # Current post-upper-bound-reject fork next-gate anchor:
        # new_gpu_execution_design_family_spec_or_path_a_acceptance_after_gpu_upper_bound_reject_certificate_no_go
        # fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_gpu_upper_bound_reject_certificate_no_go
        # Current exact work-unit compaction next-gate anchor:
        # phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold
        # fasim_gpu_exact_work_unit_compaction_first1_shadow_scaffold
        # Current exact work-unit compaction consumer/no-go anchor:
        # phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go
        # fasim_gpu_exact_work_unit_compaction_first1_shadow_consumer_or_no_go
        # Current post-exact-work-unit-consumer fork anchor:
        # path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
        # fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go
        # path_b_different_gpu_execution_design_after_exact_work_unit_compaction_no_go_status
        # path_b_new_design_family_after_exact_work_unit_compaction_no_go
        # path_b_new_design_family_spec_required_after_exact_work_unit_compaction_no_go
        # new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
        # fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go
        # path_b_no_viable_new_design_family_after_exact_work_unit_compaction_no_go
        # path_b_external_design_input_required_after_exact_work_unit_compaction_no_go
        # path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go
        # fasim_path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go
        # path_b_external_design_input_received
        # user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go
        # none_until_user_scope_acceptance_or_external_path_b_design_input
        # Historical checker anchor retained for the GPU upper-bound reject
        # certificate spec checker and post-native-DP fork checker:
        # new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go
        # fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go
        # Historical current-gate anchor retained for the post-native-DP fork
        # checker:
        # current_execution_gate=new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go
        # current_next_pr=fasim_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_native_cuda_fasim_dp_engine_no_go
        # Historical checker anchor retained for the post-native-DP fork
        # checker, which scans this source after its own checkpoint:
        # path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go
        # fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go
        # Historical current-gate anchor retained for the native CUDA Fasim
        # DP first1-shadow consumer no-go checker:
        # current_execution_gate=path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go
        # current_next_pr=fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go
        # Historical checker anchor retained for the native CUDA Fasim DP
        # first1-shadow consumer no-go checker and previous scaffold checker:
        # phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
        # fasim_native_cuda_fasim_dp_engine_first1_shadow_consumer_or_no_go
        # Historical checker anchor retained for the native CUDA Fasim DP
        # first1-shadow scaffold checker, which scans this source after its own
        # checkpoint:
        # phase7_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
        # fasim_native_cuda_fasim_dp_engine_first1_fail_closed_shadow_scaffold
        # Historical checker anchor retained for the native CUDA Fasim DP
        # design-spec checker, which scans this source after its own
        # checkpoint:
        # phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
        # fasim_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance
        # Historical checker anchor retained for the full-align verifier
        # consumer no-go checker, which scans this source after its own
        # checkpoint:
        # path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go
        # fasim_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go
        # Historical checker anchor retained for the full-align verifier
        # scaffold checker, which scans this source after its own checkpoint:
        # phase7_gasal2_full_align_verifier_first1_shadow_consumer_or_no_go
        # fasim_gasal2_full_align_verifier_first1_shadow_consumer_or_no_go
        # Historical checker anchor retained for the GPU-owned-consumer fork
        # checker, which scans this source after its own checkpoint:
        # phase7_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
        # fasim_gasal2_full_align_verifier_first1_fail_closed_shadow_scaffold
        "phase7_broad_restart_v5_cpu_authority_replay_smoke": (
            "gate_v5_2_pass_first1"
        ),
        "phase7_v5_cpu_authority_replay_requested": "1",
        "phase7_v5_cpu_authority_replay_active": "1",
        "phase7_v5_cpu_authority_replay_gate_v5_2_pass": "1",
        "phase7_broad_restart_v5_cuda_descriptor_emission_design": "defined",
        "phase7_broad_restart_v5_cuda_descriptor_emission_status": (
            "design_only"
        ),
        "phase7_v5_true_pre_scoreinfo_descriptor_source_requested": "1",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_active": "1",
        "phase7_v5_true_pre_scoreinfo_descriptor_source_gate_v5_1_pass": "1",
        "phase8_completion_decision": (
            "complete_scoped_path_a"
            if scoped_accepted
            else ("not_complete_without_user_scope_acceptance" if broad_open else "complete")
        ),
        "scoped_product_status": (
            "accepted"
            if scoped_accepted
            else ("ready_if_user_accepts_scope" if scoped_ready else "not_ready")
        ),
        "broad_objective_status": "open" if broad_open else "complete",
        "broad_replacement_claimed": matrix["has_broad_claim"],
        "scope_or_broad_design_decision_required": (
            "1" if scoped_ready and broad_open and not scoped_accepted else "0"
        ),
        "scope_or_broad_design_decision_packet": "defined",
        "current_decision": (
            "complete_scoped_path_a"
            if scoped_accepted
            else (
                "user_scope_acceptance_or_external_path_b_design_input_required_after_exact_work_unit_compaction_no_go"
                if broad_open
                else "complete"
            )
        ),
        "current_v4_source_replay_must_not_continue": "1" if broad_open else "0",
        "path_a_user_acceptance_required": (
            "1" if scoped_ready and broad_open and not scoped_accepted else "0"
        ),
        "path_a_user_acceptance_recorded": "1" if path_a_accepted else "0",
        "path_a_scoped_completion_may_close_goal": (
            "1" if scoped_accepted else "0"
        ),
        "path_b_new_broad_architecture_required": (
            "1" if broad_open and not scoped_accepted else "0"
        ),
        "active_goal_completion_status": (
            "complete_scoped_path_a"
            if scoped_accepted
            else ("complete_broad_path_b" if not broad_open else "open")
        ),
        "completion_guard_cleared": "1" if scoped_accepted or not broad_open else "0",
        "goal_completion_status": (
            "complete" if scoped_accepted or not broad_open else "open"
        ),
        "must_not_call_update_goal_complete": (
            "0" if scoped_accepted or not broad_open else "1"
        ),
        "roadmap_current_state_decision": (
            "complete_scoped_path_a"
            if scoped_accepted
            else ("continue_goal_broad_open" if broad_open else "complete")
        ),
    }
    for key, value in output.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
