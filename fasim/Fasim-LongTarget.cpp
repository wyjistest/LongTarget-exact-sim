/*
* 2021-09-25 21:38:09: This is a new version of LongTarget which contains some
* new features:
*	 1) now both Sim and fastSIM is available.
*	 2) threshold is determined based on maxScore of the DNA sequence.
* Need to check the performance of fastSim.
* Note that cutSequence has been moved to fastSim.h.
*/
/*
* 2021-12-22 21:38:09: This is a new version of LongTarget which contains some
* new features:
*	 1) TT penalty is operated on sequence with no gaps.
*	 2) threshold is determined based on 0.8*average_maxScore of the 48 DNA transformed sequences.
* Need to check the performance of fastSim.
* Note that cutSequence has been moved to fastSim.h.
*/
//#include <seqan/score.h>
//#include <seqan/align.h>
#include <iostream>
#include <string>
#include <sstream>
#include <fstream>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>
#include <getopt.h>
#include <unistd.h>
#include <vector>
#include <map>
#include <algorithm>
#include <omp.h>
#include <ctype.h>
#include <utility>
#include <thread>
#include <mutex>
#include <atomic>
#include <chrono>
#include <memory>
#include <limits>
#include <stdint.h>
#include <iomanip>
#include <cstring>

#include "fastsim.h"
using namespace std;

string getStrand(int reverse, int strand);

namespace
{

static inline double fasim_seconds_since(const std::chrono::steady_clock::time_point &start)
{
	return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
}

struct FasimScopedSeconds
{
	FasimScopedSeconds(bool enabledValue, double *secondsOutValue) :
		enabled(enabledValue),
		secondsOut(secondsOutValue),
		start()
	{
		if (enabled)
		{
			start = std::chrono::steady_clock::now();
		}
	}

	~FasimScopedSeconds()
	{
		if (enabled && secondsOut != NULL)
		{
			*secondsOut += fasim_seconds_since(start);
		}
	}

	bool enabled;
	double *secondsOut;
	std::chrono::steady_clock::time_point start;
};

static inline uint64_t fasim_fnv1a_update(uint64_t digest, const std::string &text)
{
	for (size_t i = 0; i < text.size(); ++i)
	{
		digest ^= static_cast<unsigned char>(text[i]);
		digest *= 1099511628211ULL;
	}
	return digest;
}

static inline std::string fasim_hex_u64(uint64_t value)
{
	std::ostringstream out;
	out << std::hex << std::setw(16) << std::setfill('0') << value;
	return out.str();
}

struct FasimTop5PhaseTimingStats
{
	FasimTop5PhaseTimingStats() :
		records(0),
		windows(0),
		tasks(0),
		flushes(0),
		flush_tasks(0),
		cuda_topk_batches(0),
		cuda_topk_tasks(0),
		cuda_topk_deferred_batches(0),
		cuda_topk_deferred_tasks(0),
		single_pass_topn_enabled(false),
		single_pass_topn_batches(0),
		single_pass_topn_tasks(0),
		single_pass_topn_scoreinfo_groups(0),
		exact_scoreinfo_gpu_enabled(false),
		exact_scoreinfo_gpu_pruned_output_enabled(false),
		exact_scoreinfo_gpu_column_pruned_output_enabled(false),
		exact_scoreinfo_gpu_batches(0),
		exact_scoreinfo_gpu_tasks(0),
		exact_scoreinfo_gpu_overflow_batches(0),
		exact_scoreinfo_gpu_fallback_batches(0),
		exact_scoreinfo_gpu_pruned_output_batches(0),
		exact_scoreinfo_gpu_pruned_output_input_groups(0),
		exact_scoreinfo_gpu_pruned_output_kept_groups(0),
		exact_scoreinfo_gpu_pruned_output_pruned_groups(0),
		exact_scoreinfo_gpu_pruned_output_pruned_tasks(0),
		exact_column_batches(0),
		exact_column_tasks(0),
		exact_column_cells(0),
		exact_scoreinfo_groups(0),
		scoreinfo_prune_enabled(false),
		scoreinfo_prune_max_per_task(0),
		scoreinfo_prune_input_groups(0),
		scoreinfo_prune_kept_groups(0),
		scoreinfo_prune_pruned_groups(0),
		scoreinfo_prune_pruned_tasks(0),
		scoreinfo_emit_rank_observe_enabled(false),
		scoreinfo_emit_rank_observe_alignments(0),
		scoreinfo_emit_rank_observe_max_rank(0),
		scoreinfo_emit_rank_observe_rank1(0),
		scoreinfo_emit_rank_observe_rank2_4(0),
		scoreinfo_emit_rank_observe_rank5_8(0),
		scoreinfo_emit_rank_observe_rank9_16(0),
		scoreinfo_emit_rank_observe_rank17_32(0),
		scoreinfo_emit_rank_observe_rank33_plus(0),
		scoreinfo_topk_lite_rank_observe_enabled(false),
		scoreinfo_topk_lite_rank_observe_rows(0),
		scoreinfo_topk_lite_rank_observe_unknown_rows(0),
		scoreinfo_topk_lite_rank_observe_max_rank(0),
		scoreinfo_topk_lite_rank_observe_rank1(0),
		scoreinfo_topk_lite_rank_observe_rank2_4(0),
		scoreinfo_topk_lite_rank_observe_rank5_8(0),
		scoreinfo_topk_lite_rank_observe_rank9_16(0),
		scoreinfo_topk_lite_rank_observe_rank17_32(0),
		scoreinfo_topk_lite_rank_observe_rank33_plus(0),
		gasal2_selected_alignments(0),
		gasal2_convert_input_alignments(0),
		gasal2_convert_triplexes_raw(0),
		gasal2_convert_tasks(0),
		gasal2_convert_tasks_with_input(0),
		gasal2_emit_candidates(0),
		gasal2_emit_filtered_score(0),
		gasal2_emit_filtered_identity(0),
		gasal2_emit_filtered_stability(0),
		gasal2_emit_filtered_nt(0),
		gasal2_emit_rows_lite(0),
		gasal2_emit_rows_full(0),
		gasal2_nt_shadow_query_span_lt_clength(0),
		gasal2_nt_shadow_ref_span_lt_clength(0),
		gasal2_nt_shadow_min_span_lt_clength(0),
		gasal2_nt_shadow_max_span_lt_clength(0),
		gasal2_nt_shadow_sum_span_lt_clength(0),
		gasal2_nt_shadow_query_span_false_negative(0),
		gasal2_nt_shadow_ref_span_false_negative(0),
		gasal2_nt_shadow_min_span_false_negative(0),
		gasal2_nt_shadow_max_span_false_negative(0),
		gasal2_nt_shadow_sum_span_false_negative(0),
			gasal2_nt_sum_span_prune_active(0),
			gasal2_extend_batches(0),
			gasal2_extend_tasks(0),
			gasal2_query_preflight_supported(false),
			gasal2_query_preflight_query_len(0),
			gasal2_query_preflight_max_query_len(0),
			read_rna_seconds(0.0),
		output_open_seconds(0.0),
		auto_observe_seconds(0.0),
		cuda_query_init_seconds(0.0),
		fasta_read_seconds(0.0),
		cut_sequence_seconds(0.0),
		enqueue_seconds(0.0),
		transfer_string_seconds(0.0),
		transfer_table_seconds(0.0),
		transfer_reverse_seconds(0.0),
			src_transform_seconds(0.0),
			transfer_calls(0),
			transfer_bytes(0),
			transfer_reverse_calls(0),
			src_transform_calls(0),
			src_transform_bytes(0),
			src_transform_orig(0),
			src_transform_comp(0),
			src_transform_rev(0),
			src_transform_revcomp(0),
			encode_seconds(0.0),
			encode_dual_seconds(0.0),
			encode_prealign_seconds(0.0),
			encode_legacy_seconds(0.0),
		flush_total_seconds(0.0),
		cuda_topk_wall_seconds(0.0),
		cuda_topk_kernel_seconds(0.0),
		exact_scoreinfo_gpu_wall_seconds(0.0),
		exact_scoreinfo_gpu_kernel_seconds(0.0),
		exact_scoreinfo_gpu_h2d_seconds(0.0),
		exact_scoreinfo_gpu_d2h_seconds(0.0),
		exact_column_wall_seconds(0.0),
		exact_column_kernel_seconds(0.0),
		exact_column_h2d_seconds(0.0),
		exact_column_d2h_seconds(0.0),
		exact_min_score_seconds(0.0),
		exact_scoreinfo_build_seconds(0.0),
		gasal2_extend_wall_seconds(0.0),
		gasal2_convert_alignment_seconds(0.0),
		gasal2_convert_sort_seconds(0.0),
		gasal2_convert_filter_seconds(0.0),
		gasal2_convert_rank_map_seconds(0.0),
		cpu_fallback_scoreinfo_seconds(0.0),
		cpu_fallback_extend_seconds(0.0),
		output_write_seconds(0.0),
		output_close_seconds(0.0),
		query_release_seconds(0.0)
	{
	}

	uint64_t records;
	uint64_t windows;
	uint64_t tasks;
	uint64_t flushes;
	uint64_t flush_tasks;
	uint64_t cuda_topk_batches;
	uint64_t cuda_topk_tasks;
	uint64_t cuda_topk_deferred_batches;
	uint64_t cuda_topk_deferred_tasks;
	bool single_pass_topn_enabled;
	uint64_t single_pass_topn_batches;
	uint64_t single_pass_topn_tasks;
	uint64_t single_pass_topn_scoreinfo_groups;
	bool exact_scoreinfo_gpu_enabled;
	bool exact_scoreinfo_gpu_pruned_output_enabled;
	bool exact_scoreinfo_gpu_column_pruned_output_enabled;
	uint64_t exact_scoreinfo_gpu_batches;
	uint64_t exact_scoreinfo_gpu_tasks;
	uint64_t exact_scoreinfo_gpu_overflow_batches;
	uint64_t exact_scoreinfo_gpu_fallback_batches;
	uint64_t exact_scoreinfo_gpu_pruned_output_batches;
	uint64_t exact_scoreinfo_gpu_pruned_output_input_groups;
	uint64_t exact_scoreinfo_gpu_pruned_output_kept_groups;
	uint64_t exact_scoreinfo_gpu_pruned_output_pruned_groups;
	uint64_t exact_scoreinfo_gpu_pruned_output_pruned_tasks;
	uint64_t exact_column_batches;
	uint64_t exact_column_tasks;
	uint64_t exact_column_cells;
	uint64_t exact_scoreinfo_groups;
	bool scoreinfo_prune_enabled;
	int scoreinfo_prune_max_per_task;
	uint64_t scoreinfo_prune_input_groups;
	uint64_t scoreinfo_prune_kept_groups;
	uint64_t scoreinfo_prune_pruned_groups;
	uint64_t scoreinfo_prune_pruned_tasks;
	bool scoreinfo_emit_rank_observe_enabled;
	uint64_t scoreinfo_emit_rank_observe_alignments;
	uint64_t scoreinfo_emit_rank_observe_max_rank;
	uint64_t scoreinfo_emit_rank_observe_rank1;
	uint64_t scoreinfo_emit_rank_observe_rank2_4;
	uint64_t scoreinfo_emit_rank_observe_rank5_8;
	uint64_t scoreinfo_emit_rank_observe_rank9_16;
	uint64_t scoreinfo_emit_rank_observe_rank17_32;
	uint64_t scoreinfo_emit_rank_observe_rank33_plus;
	bool scoreinfo_topk_lite_rank_observe_enabled;
	uint64_t scoreinfo_topk_lite_rank_observe_rows;
	uint64_t scoreinfo_topk_lite_rank_observe_unknown_rows;
	uint64_t scoreinfo_topk_lite_rank_observe_max_rank;
	uint64_t scoreinfo_topk_lite_rank_observe_rank1;
	uint64_t scoreinfo_topk_lite_rank_observe_rank2_4;
	uint64_t scoreinfo_topk_lite_rank_observe_rank5_8;
	uint64_t scoreinfo_topk_lite_rank_observe_rank9_16;
	uint64_t scoreinfo_topk_lite_rank_observe_rank17_32;
	uint64_t scoreinfo_topk_lite_rank_observe_rank33_plus;
	uint64_t gasal2_selected_alignments;
	uint64_t gasal2_convert_input_alignments;
	uint64_t gasal2_convert_triplexes_raw;
	uint64_t gasal2_convert_tasks;
	uint64_t gasal2_convert_tasks_with_input;
	uint64_t gasal2_emit_candidates;
	uint64_t gasal2_emit_filtered_score;
	uint64_t gasal2_emit_filtered_identity;
	uint64_t gasal2_emit_filtered_stability;
	uint64_t gasal2_emit_filtered_nt;
	uint64_t gasal2_emit_rows_lite;
	uint64_t gasal2_emit_rows_full;
	uint64_t gasal2_nt_shadow_query_span_lt_clength;
	uint64_t gasal2_nt_shadow_ref_span_lt_clength;
	uint64_t gasal2_nt_shadow_min_span_lt_clength;
	uint64_t gasal2_nt_shadow_max_span_lt_clength;
	uint64_t gasal2_nt_shadow_sum_span_lt_clength;
	uint64_t gasal2_nt_shadow_query_span_false_negative;
	uint64_t gasal2_nt_shadow_ref_span_false_negative;
	uint64_t gasal2_nt_shadow_min_span_false_negative;
	uint64_t gasal2_nt_shadow_max_span_false_negative;
	uint64_t gasal2_nt_shadow_sum_span_false_negative;
	uint64_t gasal2_nt_sum_span_prune_active;
	uint64_t gasal2_extend_batches;
	uint64_t gasal2_extend_tasks;
	bool gasal2_query_preflight_supported;
	uint64_t gasal2_query_preflight_query_len;
	uint64_t gasal2_query_preflight_max_query_len;
	double read_rna_seconds;
	double output_open_seconds;
	double auto_observe_seconds;
	double cuda_query_init_seconds;
	double fasta_read_seconds;
	double cut_sequence_seconds;
	double enqueue_seconds;
	double transfer_string_seconds;
	double transfer_table_seconds;
	double transfer_reverse_seconds;
		double src_transform_seconds;
	uint64_t transfer_calls;
	uint64_t transfer_bytes;
	uint64_t transfer_reverse_calls;
	uint64_t src_transform_calls;
	uint64_t src_transform_bytes;
	uint64_t src_transform_orig;
	uint64_t src_transform_comp;
	uint64_t src_transform_rev;
	uint64_t src_transform_revcomp;
	double encode_seconds;
		double encode_dual_seconds;
		double encode_prealign_seconds;
		double encode_legacy_seconds;
	double flush_total_seconds;
	double cuda_topk_wall_seconds;
	double cuda_topk_kernel_seconds;
	double exact_scoreinfo_gpu_wall_seconds;
	double exact_scoreinfo_gpu_kernel_seconds;
	double exact_scoreinfo_gpu_h2d_seconds;
	double exact_scoreinfo_gpu_d2h_seconds;
	double exact_column_wall_seconds;
	double exact_column_kernel_seconds;
	double exact_column_h2d_seconds;
	double exact_column_d2h_seconds;
	double exact_min_score_seconds;
	double exact_scoreinfo_build_seconds;
	double gasal2_extend_wall_seconds;
	double gasal2_convert_alignment_seconds;
	double gasal2_convert_sort_seconds;
	double gasal2_convert_filter_seconds;
	double gasal2_convert_rank_map_seconds;
	double cpu_fallback_scoreinfo_seconds;
	double cpu_fallback_extend_seconds;
	double output_write_seconds;
	double output_close_seconds;
	double query_release_seconds;
};

enum FasimMinScoreShadowSource
{
	FASIM_MIN_SCORE_SHADOW_SOURCE_NONE = 0,
	FASIM_MIN_SCORE_SHADOW_SOURCE_GPU_ROW = 1,
	FASIM_MIN_SCORE_SHADOW_SOURCE_GPU_LEGACY_ROW = 2,
	FASIM_MIN_SCORE_SHADOW_SOURCE_TOPK = 3,
};

struct FasimExactColumnMinScoreShadowStats
{
	FasimExactColumnMinScoreShadowStats() :
		tasks(0),
		gpu_row_score_mismatches(0),
		gpu_row_min_score_mismatches(0),
		gpu_row_gt_cpu(0),
		gpu_row_lt_cpu(0),
		gpu_row_max_abs_diff(0),
		gpu_legacy_row_score_mismatches(0),
		gpu_legacy_row_min_score_mismatches(0),
		gpu_legacy_row_gt_cpu(0),
		gpu_legacy_row_lt_cpu(0),
		gpu_legacy_row_max_abs_diff(0),
		topk_score_mismatches(0),
		topk_min_score_mismatches(0),
		topk_gt_cpu(0),
		topk_lt_cpu(0),
		topk_max_abs_diff(0),
		first_source(FASIM_MIN_SCORE_SHADOW_SOURCE_NONE),
		first_task_ordinal(0),
		first_rule(0),
		first_strand(0),
		first_para(0),
		first_target_len(0),
		first_cpu_score(0),
		first_cpu_min_score(0),
		first_gpu_row_score(0),
		first_gpu_row_min_score(0),
		first_gpu_legacy_row_score(0),
		first_gpu_legacy_row_min_score(0),
		first_topk_score(0),
		first_topk_min_score(0),
		first_gpu_row_task(0),
		first_gpu_row_rule(0),
		first_gpu_row_strand(0),
		first_gpu_row_para(0),
		first_gpu_row_target_len(0),
		first_gpu_row_cpu_score(0),
		first_gpu_row_cpu_min_score(0),
		first_gpu_row_score_value(0),
		first_gpu_row_min_score_value(0),
		first_gpu_legacy_row_task(0),
		first_gpu_legacy_row_rule(0),
		first_gpu_legacy_row_strand(0),
		first_gpu_legacy_row_para(0),
		first_gpu_legacy_row_target_len(0),
		first_gpu_legacy_row_cpu_score(0),
		first_gpu_legacy_row_cpu_min_score(0),
		first_gpu_legacy_row_score_value(0),
		first_gpu_legacy_row_min_score_value(0),
		first_topk_task(0),
		first_topk_rule(0),
		first_topk_strand(0),
		first_topk_para(0),
		first_topk_target_len(0),
		first_topk_cpu_score(0),
		first_topk_cpu_min_score(0),
		first_topk_score_value(0),
		first_topk_min_score_value(0),
		seconds(0.0)
	{
	}

	uint64_t tasks;
	uint64_t gpu_row_score_mismatches;
	uint64_t gpu_row_min_score_mismatches;
	uint64_t gpu_row_gt_cpu;
	uint64_t gpu_row_lt_cpu;
	int gpu_row_max_abs_diff;
	uint64_t gpu_legacy_row_score_mismatches;
	uint64_t gpu_legacy_row_min_score_mismatches;
	uint64_t gpu_legacy_row_gt_cpu;
	uint64_t gpu_legacy_row_lt_cpu;
	int gpu_legacy_row_max_abs_diff;
	uint64_t topk_score_mismatches;
	uint64_t topk_min_score_mismatches;
	uint64_t topk_gt_cpu;
	uint64_t topk_lt_cpu;
	int topk_max_abs_diff;
	FasimMinScoreShadowSource first_source;
	uint64_t first_task_ordinal;
	int first_rule;
	long first_strand;
	long first_para;
	size_t first_target_len;
	int first_cpu_score;
	int first_cpu_min_score;
	int first_gpu_row_score;
	int first_gpu_row_min_score;
	int first_gpu_legacy_row_score;
	int first_gpu_legacy_row_min_score;
	int first_topk_score;
	int first_topk_min_score;
	uint64_t first_gpu_row_task;
	int first_gpu_row_rule;
	long first_gpu_row_strand;
	long first_gpu_row_para;
	size_t first_gpu_row_target_len;
	int first_gpu_row_cpu_score;
	int first_gpu_row_cpu_min_score;
	int first_gpu_row_score_value;
	int first_gpu_row_min_score_value;
	uint64_t first_gpu_legacy_row_task;
	int first_gpu_legacy_row_rule;
	long first_gpu_legacy_row_strand;
	long first_gpu_legacy_row_para;
	size_t first_gpu_legacy_row_target_len;
	int first_gpu_legacy_row_cpu_score;
	int first_gpu_legacy_row_cpu_min_score;
	int first_gpu_legacy_row_score_value;
	int first_gpu_legacy_row_min_score_value;
	uint64_t first_topk_task;
	int first_topk_rule;
	long first_topk_strand;
	long first_topk_para;
	size_t first_topk_target_len;
	int first_topk_cpu_score;
	int first_topk_cpu_min_score;
	int first_topk_score_value;
	int first_topk_min_score_value;
	double seconds;
};

struct FasimLegacyScoreGpuShadowStats
{
	FasimLegacyScoreGpuShadowStats() :
		enabled(false),
		replacement_enabled(false),
		requests(0),
		batches(0),
		cells(0),
		replacement_used(0),
		replacement_fallbacks(0),
		mismatches(0),
		min_score_mismatches(0),
		gpu_gt_cpu(0),
		gpu_lt_cpu(0),
		max_abs_diff(0),
		first_task(0),
		first_rule(0),
		first_strand(0),
		first_para(0),
		first_target_len(0),
		first_cpu_score(0),
		first_gpu_score(0),
		first_cpu_min_score(0),
		first_gpu_min_score(0),
		wall_seconds(0.0),
		kernel_seconds(0.0),
		h2d_seconds(0.0),
		d2h_seconds(0.0)
	{
	}

	bool enabled;
	bool replacement_enabled;
	uint64_t requests;
	uint64_t batches;
	uint64_t cells;
	uint64_t replacement_used;
	uint64_t replacement_fallbacks;
	uint64_t mismatches;
	uint64_t min_score_mismatches;
	uint64_t gpu_gt_cpu;
	uint64_t gpu_lt_cpu;
	int max_abs_diff;
	uint64_t first_task;
	int first_rule;
	long first_strand;
	long first_para;
	size_t first_target_len;
	int first_cpu_score;
	int first_gpu_score;
	int first_cpu_min_score;
	int first_gpu_min_score;
	double wall_seconds;
	double kernel_seconds;
	double h2d_seconds;
	double d2h_seconds;
};

struct FasimBroadScoreInfoConsumerShadowStats
{
	FasimBroadScoreInfoConsumerShadowStats() :
		broad_path_requested(0),
		broad_path_active(0),
		broad_path_decision("disabled"),
		broad_path_tasks(0),
		broad_path_scoreinfo_groups(0),
		broad_path_scoreinfo_seconds(0.0),
		broad_path_consumer_seconds(0.0),
		broad_path_align_attempts(0),
		broad_path_selected_attempts(0),
		broad_path_triplex_mismatches(0),
		broad_path_missing_triplexes(0),
		broad_path_extra_triplexes(0),
		broad_path_first_mismatch("none"),
		broad_path_digest_match(0),
		broad_path_full_rows_equal(0),
		broad_path_candidate_wall_seconds(0.0),
		broad_path_baseline_wall_seconds(0.0),
		broad_path_candidate_vs_baseline(0.0),
		broad_path_cpu_triplex_path(""),
		broad_path_cpu_triplexes(0),
		broad_path_cpu_triplex_digest("0000000000000000"),
		broad_path_planner_descriptor_path(""),
		broad_path_planner_descriptors(0),
		broad_path_planner_descriptor_digest("0000000000000000")
	{
	}

	uint64_t broad_path_requested;
	uint64_t broad_path_active;
	std::string broad_path_decision;
	uint64_t broad_path_tasks;
	uint64_t broad_path_scoreinfo_groups;
	double broad_path_scoreinfo_seconds;
	double broad_path_consumer_seconds;
	uint64_t broad_path_align_attempts;
	uint64_t broad_path_selected_attempts;
	uint64_t broad_path_triplex_mismatches;
	uint64_t broad_path_missing_triplexes;
	uint64_t broad_path_extra_triplexes;
	std::string broad_path_first_mismatch;
	uint64_t broad_path_digest_match;
	uint64_t broad_path_full_rows_equal;
	double broad_path_candidate_wall_seconds;
	double broad_path_baseline_wall_seconds;
	double broad_path_candidate_vs_baseline;
	std::string broad_path_cpu_triplex_path;
	uint64_t broad_path_cpu_triplexes;
	std::string broad_path_cpu_triplex_digest;
	std::string broad_path_planner_descriptor_path;
	uint64_t broad_path_planner_descriptors;
	std::string broad_path_planner_descriptor_digest;
};

enum FasimSrcTransform
{
    FASIM_SRC_ORIG = 0,
    FASIM_SRC_COMP = 1,
    FASIM_SRC_REV = 2,
    FASIM_SRC_REVCOMP = 3,
};

enum FasimOutputMode
{
    FASIM_OUTPUT_FULL = 0,
    FASIM_OUTPUT_TFOSORTED = 1,
    FASIM_OUTPUT_LITE = 2,
};

struct FasimPrealignCudaTask
{
    FasimPrealignCudaTask() :
        seq1(NULL),
        dnaStartPos(0),
        strand(0),
        Para(0),
        rule(0),
        srcTransform(FASIM_SRC_ORIG)
    {
    }

    const std::string *seq1;
    std::string seq2;
    long dnaStartPos;
    long strand;
    long Para;
    int rule;
    FasimSrcTransform srcTransform;
};

static inline bool fasim_verbose_enabled_runtime()
{
    const char *env = getenv("FASIM_VERBOSE");
    if (env == NULL || env[0] == '\0')
    {
        return true;
    }
    return env[0] != '0';
}

static inline bool fasim_write_tfosorted_lite_enabled_runtime()
{
    const char *env = getenv("FASIM_WRITE_TFOSORTED_LITE");
    if (env == NULL || env[0] == '\0')
    {
        return false;
    }
    return env[0] != '0';
}

static inline bool fasim_tfosorted_cigar_archive_probe_runtime()
{
	const char *env = getenv("FASIM_TFOSORTED_CIGAR_ARCHIVE_PROBE");
	if (env == NULL || env[0] == '\0')
	{
		return false;
	}
	return env[0] != '0';
}

static inline bool fasim_tfosorted_compact_archive_probe_runtime()
{
	const char *env = getenv("FASIM_TFOSORTED_COMPACT_ARCHIVE_PROBE");
	if (env == NULL || env[0] == '\0')
	{
		return false;
	}
	return env[0] != '0';
}

static inline FasimOutputMode fasim_output_mode_runtime()
{
    static const FasimOutputMode mode = []()
    {
        const char *env = getenv("FASIM_OUTPUT_MODE");
        if (env == NULL || env[0] == '\0')
        {
            return FASIM_OUTPUT_FULL;
        }
        std::string value(env);
        for (size_t i = 0; i < value.size(); ++i)
        {
            value[i] = static_cast<char>(tolower(static_cast<unsigned char>(value[i])));
        }
        if (value == "tfosorted" || value == "tfo")
        {
            return FASIM_OUTPUT_TFOSORTED;
        }
        if (value == "lite" || value == "tfosorted_lite" || value == "tfo_lite" || value == "tfosorted-lite" || value == "tfo-lite" ||
            value == "liteonly" || value == "lite-only")
        {
            return FASIM_OUTPUT_LITE;
        }
        if (value == "full")
        {
            return FASIM_OUTPUT_FULL;
        }
        return FASIM_OUTPUT_FULL;
    }();
    return mode;
}

static inline bool fasim_env_flag_enabled(const char *name)
{
	const char *env = getenv(name);
	if (env == NULL || env[0] == '\0')
	{
        return false;
    }
	return env[0] != '0';
}

static inline bool fasim_top5_gasal2_phase_timing_enabled_runtime()
{
	return fasim_env_flag_enabled("FASIM_TOP5_GASAL2_PHASE_TIMING");
}

static inline bool fasim_gasal2_long_query_segmented_shadow_requested_runtime()
{
	return fasim_env_flag_enabled("FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SHADOW");
}

static inline bool fasim_gasal2_long_query_segmented_score_prepass_shadow_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCORE_PREPASS_SHADOW");
}

static inline bool fasim_gasal2_long_query_segmented_cpu_traceback_replay_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_CPU_TRACEBACK_REPLAY");
}

static inline bool fasim_gasal2_long_query_exact_tile_shadow_requested_runtime()
{
	return fasim_env_flag_enabled("FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_SHADOW");
}

static inline bool fasim_gasal2_long_query_exact_tile_oracle_export_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_ORACLE_EXPORT");
}

static inline bool fasim_gasal2_long_query_exact_tile_candidate_equivalence_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_CANDIDATE_EQUIVALENCE");
}

static inline bool fasim_long_query_exact_column_scoreinfo_shadow_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_LONG_QUERY_EXACT_COLUMN_SCOREINFO_GPU_SHADOW");
}

static inline bool fasim_long_query_exact_column_scoreinfo_shadow_smem_optin_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_LONG_QUERY_EXACT_COLUMN_SCOREINFO_GPU_SHADOW_SMEM_OPTIN");
}

static inline bool fasim_long_query_streaming_scoreinfo_shadow_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW");
}

static inline bool fasim_gasal2_broad_scoreinfo_consumer_shadow_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_SHADOW");
}

static inline bool fasim_gasal2_broad_scoreinfo_consumer_export_cpu_triplex_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_EXPORT_CPU_TRIPLEX");
}

static inline bool fasim_gasal2_broad_scoreinfo_consumer_planner_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_GASAL2_BROAD_SCOREINFO_CONSUMER_PLANNER");
}

static inline bool fasim_gasal2_broad_replacement_consumer_shadow_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_GASAL2_BROAD_REPLACEMENT_CONSUMER_SHADOW");
}

static inline bool fasim_gasal2_attempt_consumer_shadow_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW");
}

static inline std::string fasim_gasal2_long_query_segmented_cpu_traceback_order_runtime()
{
	const char *env = getenv(
		"FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_CPU_TRACEBACK_ORDER");
	if (env == NULL || env[0] == '\0')
	{
		return "legacy";
	}
	std::string order(env);
	for (size_t i = 0; i < order.size(); ++i)
	{
		order[i] = static_cast<char>(tolower(static_cast<unsigned char>(order[i])));
	}
	if (order == "score" || order == "score_prepass" || order == "gasal2_score")
	{
		return "score";
	}
	if (order == "threshold_score" ||
	    order == "threshold-first" ||
	    order == "threshold_first")
	{
		return "threshold_score";
	}
	return "legacy";
}

static inline bool fasim_gasal2_nt_sum_span_prune_enabled_runtime()
{
	return fasim_env_flag_enabled("FASIM_ALIGN_GASAL2_NT_SUM_SPAN_PRUNE");
}

static inline bool fasim_exact_column_min_score_shadow_enabled_runtime()
{
	return fasim_env_flag_enabled("FASIM_EXACT_COLUMN_MIN_SCORE_SHADOW");
}

static inline bool fasim_exact_column_min_score_shadow_debug_enabled_runtime()
{
	return fasim_env_flag_enabled("FASIM_EXACT_COLUMN_MIN_SCORE_SHADOW_DEBUG");
}

static inline bool fasim_exact_column_legacy_score_gpu_shadow_enabled_runtime()
{
	return fasim_env_flag_enabled("FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU_SHADOW");
}

static inline bool fasim_exact_column_legacy_score_gpu_enabled_runtime()
{
	const char *env = getenv("FASIM_EXACT_COLUMN_LEGACY_SCORE_GPU");
	if (env != NULL && env[0] != '\0')
	{
		return env[0] != '0';
	}
	if (fasim_env_flag_enabled("FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT") &&
	    fasim_env_flag_enabled("FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT"))
	{
		return false;
	}
	return fasim_top5_gasal2_gpu_scoreinfo_enabled_runtime();
}

static inline bool fasim_exact_column_extend_batch_enabled_runtime()
{
	return fasim_env_flag_enabled("FASIM_EXACT_COLUMN_EXTEND_BATCH") ||
	       fasim_top5_gasal2_gpu_scoreinfo_enabled_runtime();
}

static inline bool fasim_exact_column_extend_batch_validate_enabled_runtime()
{
    return fasim_env_flag_enabled("FASIM_EXACT_COLUMN_EXTEND_BATCH_VALIDATE");
}

static inline bool fasim_exact_column_extend_batch_debug_columns_runtime()
{
    return fasim_env_flag_enabled("FASIM_EXACT_COLUMN_EXTEND_BATCH_DEBUG_COLUMNS");
}

static inline bool fasim_long_query_streaming_scoreinfo_debug_columns_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_DEBUG_COLUMNS");
}

static inline bool fasim_long_query_streaming_scoreinfo_legacy_byte_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE");
}

static inline bool fasim_long_query_streaming_scoreinfo_legacy_byte_shared_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_LEGACY_BYTE_SHARED");
}

static inline bool fasim_long_query_streaming_scoreinfo_gpu_minscore_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE");
}

static inline bool fasim_long_query_streaming_scoreinfo_gpu_minscore_hot_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_GPU_MINSCORE_HOT");
}

static inline bool fasim_long_query_streaming_scoreinfo_fused_minscore_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_FUSED_MINSCORE_SHADOW");
}

static inline bool fasim_long_query_streaming_scoreinfo_two_contract_bridge_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_SHADOW");
}

static inline bool fasim_long_query_streaming_scoreinfo_two_contract_bridge_trust_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_TWO_CONTRACT_BRIDGE_TRUST");
}

static inline bool fasim_long_query_streaming_scoreinfo_realpath_prototype_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_PROTOTYPE");
}

static inline bool fasim_long_query_streaming_scoreinfo_realpath_trust_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_REALPATH_TRUST");
}

static inline bool fasim_exact_column_scoreinfo_gpu_enabled_runtime()
{
	return fasim_env_flag_enabled("FASIM_EXACT_COLUMN_SCOREINFO_GPU");
}

static inline bool fasim_exact_column_scoreinfo_gpu_pruned_output_enabled_runtime()
{
	return fasim_env_flag_enabled("FASIM_EXACT_COLUMN_SCOREINFO_GPU_PRUNED_OUTPUT");
}

static inline bool fasim_exact_column_scoreinfo_gpu_column_pruned_output_enabled_runtime()
{
	return fasim_env_flag_enabled("FASIM_EXACT_COLUMN_SCOREINFO_GPU_COLUMN_PRUNED_OUTPUT");
}

static inline bool fasim_top5_gasal2_single_pass_topn_enabled_runtime()
{
	return fasim_env_flag_enabled("FASIM_TOP5_GASAL2_SINGLE_PASS_TOPN");
}

static inline bool fasim_gpu_dp_column_auto_requested_runtime()
{
	return fasim_env_flag_enabled("FASIM_GPU_DP_COLUMN_AUTO") ||
           fasim_top5_gasal2_gpu_scoreinfo_enabled_runtime();
}

static inline uint64_t fasim_env_uint64_or_default(const char *name, uint64_t defaultValue)
{
    const char *env = getenv(name);
    if (env == NULL || env[0] == '\0')
    {
        return defaultValue;
    }
    char *parseEnd = NULL;
    const unsigned long long value = strtoull(env, &parseEnd, 10);
    if (parseEnd == env || value == 0ULL)
    {
        return defaultValue;
    }
    return static_cast<uint64_t>(value);
}

static inline uint64_t fasim_env_uint64_or_default_allow_zero(const char *name,
                                                              uint64_t defaultValue)
{
	const char *env = getenv(name);
	if (env == NULL || env[0] == '\0' || env[0] == '-')
	{
		return defaultValue;
	}
	char *parseEnd = NULL;
	const unsigned long long value = strtoull(env, &parseEnd, 10);
	if (parseEnd == env || (parseEnd != NULL && *parseEnd != '\0'))
	{
		return defaultValue;
	}
	return static_cast<uint64_t>(value);
}

static inline uint64_t fasim_gasal2_cpu_traceback_max_rank_runtime()
{
	return fasim_env_uint64_or_default_allow_zero(
		"FASIM_ALIGN_GASAL2_CPU_TRACEBACK_MAX_RANK",
		0ULL);
}

static inline size_t fasim_gasal2_long_query_segmented_tile_len_runtime()
{
	return static_cast<size_t>(
		fasim_env_uint64_or_default("FASIM_TOP5_GASAL2_LONG_QUERY_TILE_LEN",
		                            2812ULL));
}

static inline size_t fasim_gasal2_long_query_segmented_tile_overlap_runtime()
{
	return static_cast<size_t>(
		fasim_env_uint64_or_default_allow_zero(
			"FASIM_TOP5_GASAL2_LONG_QUERY_TILE_OVERLAP",
			512ULL));
}

static inline size_t fasim_gasal2_long_query_segmented_max_segments_runtime()
{
	return static_cast<size_t>(
		fasim_env_uint64_or_default_allow_zero(
			"FASIM_TOP5_GASAL2_LONG_QUERY_MAX_SEGMENTS",
			0ULL));
}

static inline size_t fasim_gasal2_long_query_exact_tile_len_runtime()
{
	return static_cast<size_t>(
		fasim_env_uint64_or_default("FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_LEN",
		                            2812ULL));
}

static inline size_t fasim_gasal2_long_query_exact_tile_overlap_runtime()
{
	return static_cast<size_t>(
		fasim_env_uint64_or_default_allow_zero(
			"FASIM_TOP5_GASAL2_LONG_QUERY_EXACT_TILE_OVERLAP",
			0ULL));
}

static inline size_t fasim_long_query_streaming_scoreinfo_stripe_len_runtime()
{
	return static_cast<size_t>(
		fasim_env_uint64_or_default(
			"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_STRIPE_LEN",
			2812ULL));
}

static inline uint64_t fasim_gpu_dp_column_auto_min_cells_runtime()
{
    if (fasim_top5_gasal2_gpu_scoreinfo_enabled_runtime() &&
        !fasim_env_flag_enabled("FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS"))
    {
        return 1ULL;
    }
    return fasim_env_uint64_or_default("FASIM_GPU_DP_COLUMN_AUTO_MIN_CELLS",
                                       1500000000ULL);
}

static inline uint64_t fasim_gpu_dp_column_auto_min_windows_runtime()
{
    if (fasim_top5_gasal2_gpu_scoreinfo_enabled_runtime() &&
        !fasim_env_flag_enabled("FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS"))
    {
        return 1ULL;
    }
    return fasim_env_uint64_or_default("FASIM_GPU_DP_COLUMN_AUTO_MIN_WINDOWS",
                                       128ULL);
}

static inline int fasim_env_int_or_default(const char *name, int defaultValue)
{
    const char *env = getenv(name);
    if (env == NULL || env[0] == '\0')
    {
        return defaultValue;
    }
    const int value = atoi(env);
    return value > 0 ? value : defaultValue;
}

static inline int fasim_exact_column_scoreinfo_gpu_max_per_task_runtime()
{
	return fasim_env_int_or_default("FASIM_EXACT_COLUMN_SCOREINFO_GPU_MAX_PER_TASK", 2048);
}

static inline int fasim_top5_gasal2_scoreinfo_prune_max_per_task_runtime()
{
	return fasim_env_int_or_default("FASIM_TOP5_GASAL2_SCOREINFO_PRUNE_MAX_PER_TASK", 0);
}

static inline int fasim_gasal2_long_query_segmented_scoreinfo_max_per_task_runtime()
{
	return fasim_env_int_or_default(
		"FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_MAX_PER_TASK",
		0);
}

static inline std::string fasim_gasal2_long_query_segmented_scoreinfo_prune_mode_runtime()
{
	const char *env = getenv(
		"FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_SCOREINFO_PRUNE_MODE");
	if (env == NULL || env[0] == '\0')
	{
		return "score";
	}
	std::string mode(env);
	for (size_t i = 0; i < mode.size(); ++i)
	{
		mode[i] = static_cast<char>(tolower(static_cast<unsigned char>(mode[i])));
	}
	if (mode == "score_position_spread" ||
	    mode == "position_spread" ||
	    mode == "spread")
	{
		return "score_position_spread";
	}
	if (mode == "score_position_edges" ||
	    mode == "position_edges" ||
	    mode == "edges")
	{
		return "score_position_edges";
	}
	return "score";
}

static inline int fasim_gasal2_long_query_segmented_max_tasks_runtime()
{
	return fasim_env_int_or_default(
		"FASIM_TOP5_GASAL2_LONG_QUERY_SEGMENTED_MAX_TASKS",
		0);
}

static inline bool fasim_top5_gasal2_scoreinfo_emit_rank_observe_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char *env = getenv("FASIM_TOP5_GASAL2_SCOREINFO_EMIT_RANK_OBSERVE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

static inline bool fasim_top5_gasal2_scoreinfo_topk_lite_rank_observe_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char *env = getenv("FASIM_TOP5_GASAL2_SCOREINFO_TOPK_LITE_RANK_OBSERVE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

static inline int fasim_output_topk_lite_runtime()
{
	return fasim_env_int_or_default("FASIM_OUTPUT_TOPK_LITE", 0);
}

static inline int fasim_gasal2_max_query_len_runtime()
{
	return fasim_env_int_or_default("FASIM_ALIGN_GASAL2_MAX_QUERY_LEN", 2812);
}

static inline bool fasim_gasal2_query_length_supported_runtime(size_t queryLen)
{
	const int maxQueryLen = fasim_gasal2_max_query_len_runtime();
	return maxQueryLen <= 0 || queryLen <= static_cast<size_t>(maxQueryLen);
}

static inline int fasim_extend_threads_runtime(int corenum)
{
    int threads = fasim_env_int_or_default("FASIM_EXTEND_THREADS", corenum);
    if (threads <= 0)
    {
        threads = 1;
    }
    if (threads > 256)
    {
        threads = 256;
    }
    return threads;
}

static inline void fasim_cuda_devices_runtime(std::vector<int> &devicesOut)
{
    devicesOut.clear();

    const char *env = getenv("FASIM_CUDA_DEVICES");
    if (env != NULL && env[0] != '\0')
    {
        std::string value(env);
        size_t pos = 0;
        while (pos < value.size())
        {
            const size_t comma = value.find(',', pos);
            std::string token = (comma == std::string::npos) ? value.substr(pos) : value.substr(pos, comma - pos);
            pos = (comma == std::string::npos) ? value.size() : comma + 1;

            size_t begin = 0;
            while (begin < token.size() && isspace(static_cast<unsigned char>(token[begin])))
            {
                ++begin;
            }
            size_t end = token.size();
            while (end > begin && isspace(static_cast<unsigned char>(token[end - 1])))
            {
                --end;
            }
            if (end <= begin)
            {
                continue;
            }

            const std::string trimmed = token.substr(begin, end - begin);
            char *parseEnd = NULL;
            const long parsed = strtol(trimmed.c_str(), &parseEnd, 10);
            if (parseEnd == trimmed.c_str())
            {
                continue;
            }
            const int device = static_cast<int>(parsed);

            bool already = false;
            for (size_t i = 0; i < devicesOut.size(); ++i)
            {
                if (devicesOut[i] == device)
                {
                    already = true;
                    break;
                }
            }
            if (!already)
            {
                devicesOut.push_back(device);
            }
        }
    }

    if (devicesOut.empty())
    {
        int device = fasim_cuda_device_runtime();
        if (device < 0)
        {
            device = 0;
        }
        devicesOut.push_back(device);
    }
}

static inline bool fasim_exact_column_multigpu_guard_failed(const std::vector<int> &devices)
{
    if (!fasim_exact_column_extend_batch_enabled_runtime() || devices.size() <= 1)
    {
        return false;
    }

    cerr << "error: exact-column batch requires a single visible CUDA device per Fasim process. "
         << "Single-process multi-GPU FASIM_CUDA_DEVICES is unsupported because it can bypass "
         << "exact-column batch and produce digest-incorrect topK-only output. "
         << "Use process-level sharding with CUDA_VISIBLE_DEVICES per worker." << endl;
    return true;
}

static inline bool fasim_append_complement_base(char base, std::string &out)
{
	switch (base)
	{
	case 'A':
	case 'a':
		out += 'T';
		return true;
	case 'C':
	case 'c':
		out += 'G';
		return true;
	case 'G':
	case 'g':
		out += 'C';
		return true;
	case 'T':
	case 't':
		out += 'A';
		return true;
	case 'N':
	case 'n':
		out += 'N';
		return true;
	default:
		return false;
	}
}

static inline void fasim_apply_src_transform(const std::string &seq1, FasimSrcTransform transform, std::string &out)
{
	out.clear();
	switch (transform)
	{
	case FASIM_SRC_ORIG:
		out = seq1;
		return;
	case FASIM_SRC_COMP:
		out.reserve(seq1.size());
		for (size_t i = 0; i < seq1.size(); ++i)
		{
			fasim_append_complement_base(seq1[i], out);
		}
		return;
	case FASIM_SRC_REV:
		out.assign(seq1.rbegin(), seq1.rend());
		return;
	case FASIM_SRC_REVCOMP:
		out.reserve(seq1.size());
		for (std::string::const_reverse_iterator it = seq1.rbegin(); it != seq1.rend(); ++it)
		{
			fasim_append_complement_base(*it, out);
		}
		return;
	default:
		out = seq1;
		return;
	}
}

struct FasimFastaRecord
{
    std::string header;
    std::string sequence;
};

static inline void fasim_strip_crlf(std::string &line)
{
    line.erase(std::remove(line.begin(), line.end(), '\r'), line.end());
    line.erase(std::remove(line.begin(), line.end(), '\n'), line.end());
}

static inline void fasim_normalize_sequence_uppercase(std::string &sequence)
{
	for (size_t i = 0; i < sequence.size(); ++i)
	{
		sequence[i] = static_cast<char>(toupper(static_cast<unsigned char>(sequence[i])));
	}
}

static inline bool fasim_read_next_fasta_record(std::ifstream &in,
                                                std::string &pendingHeader,
                                                FasimFastaRecord &out)
{
    out.header.clear();
    out.sequence.clear();

    std::string line;
    if (pendingHeader.empty())
    {
        while (std::getline(in, line))
        {
            fasim_strip_crlf(line);
            if (!line.empty() && line[0] == '>')
            {
                pendingHeader.swap(line);
                break;
            }
        }
        if (pendingHeader.empty())
        {
            return false;
        }
    }

    out.header.swap(pendingHeader);
    while (std::getline(in, line))
    {
        fasim_strip_crlf(line);
        if (!line.empty() && line[0] == '>')
        {
            pendingHeader.swap(line);
            break;
        }
        out.sequence += line;
    }
    fasim_normalize_sequence_uppercase(out.sequence);
    return true;
}

static inline void fasim_parse_dna_header_fields(const std::string &header,
                                                 std::string &speciesOut,
                                                 std::string &chroTagOut,
                                                 long &startGenomeOut)
{
    speciesOut.clear();
    chroTagOut.clear();
    startGenomeOut = 1;

    if (header.empty() || header[0] != '>')
    {
        return;
    }

    const size_t p1 = header.find('|', 1);
    if (p1 == std::string::npos)
    {
        speciesOut = header.substr(1);
        return;
    }
    const size_t p2 = header.find('|', p1 + 1);
    if (p2 == std::string::npos)
    {
        speciesOut = header.substr(1, p1 - 1);
        chroTagOut = header.substr(p1 + 1);
        return;
    }
    const size_t p3 = header.find('-', p2 + 1);
    speciesOut = header.substr(1, p1 - 1);
    chroTagOut = header.substr(p1 + 1, p2 - p1 - 1);
    if (p3 == std::string::npos)
    {
        startGenomeOut = atol(header.substr(p2 + 1).c_str());
        return;
    }
    startGenomeOut = atol(header.substr(p2 + 1, p3 - p2 - 1).c_str());
}

static inline std::string fasim_strip_fasta_extension(const std::string &path)
{
    if (path.size() >= 6 && path.compare(path.size() - 6, 6, ".fasta") == 0)
    {
        return path.substr(0, path.size() - 6);
    }
    if (path.size() >= 3 && path.compare(path.size() - 3, 3, ".fa") == 0)
    {
        return path.substr(0, path.size() - 3);
    }
    return path;
}

static inline std::string fasim_basename(const std::string &path)
{
    const size_t pos = path.find_last_of("/\\");
    if (pos == std::string::npos)
    {
        return path;
    }
    if (pos + 1 >= path.size())
    {
        return std::string();
    }
    return path.substr(pos + 1);
}

static inline void fasim_write_tfosorted_header(std::ofstream &out)
{
    out << "QueryStart\t"
        << "QueryEnd\t"
        << "StartInSeq\t"
        << "EndInSeq\t"
        << "Direction\t"
        << "Chr\t"
        << "StartInGenome\t"
        << "EndInGenome\t"
        << "MeanStability\t"
        << "MeanIdentity(%)\t"
        << "Strand\t"
        << "Rule\t"
        << "Score\t"
        << "Nt(bp)\t"
        << "Class\t"
        << "MidPoint\t"
        << "Center\t"
        << "TFO sequence\t"
        << "TTS sequence"
        << std::endl;
}

static inline void fasim_write_tfosorted_lite_header(std::ofstream &out)
{
    out << "Chr\t"
        << "StartInGenome\t"
        << "EndInGenome\t"
        << "Strand\t"
        << "Rule\t"
        << "QueryStart\t"
        << "QueryEnd\t"
        << "StartInSeq\t"
        << "EndInSeq\t"
        << "Direction\t"
        << "Score\t"
        << "Nt(bp)\t"
        << "MeanIdentity(%)\t"
        << "MeanStability"
	        << std::endl;
}

static inline void fasim_write_tfosorted_cigar_archive_probe_header(std::ofstream &out)
{
	out << "QueryStart\t"
	    << "QueryEnd\t"
	    << "StartInSeq\t"
	    << "EndInSeq\t"
	    << "Direction\t"
	    << "Chr\t"
	    << "StartInGenome\t"
	    << "EndInGenome\t"
	    << "MeanStability\t"
	    << "MeanIdentity(%)\t"
	    << "Strand\t"
	    << "Rule\t"
	    << "Score\t"
	    << "Nt(bp)\t"
	    << "Class\t"
	    << "MidPoint\t"
	    << "Center\t"
	    << "CIGAR"
	    << std::endl;
}

static inline void fasim_put_varint(std::string &out, uint64_t value)
{
	while (value >= 0x80)
	{
		out.push_back(static_cast<char>((value & 0x7f) | 0x80));
		value >>= 7;
	}
	out.push_back(static_cast<char>(value));
}

static inline uint64_t fasim_zigzag_i64(int64_t value)
{
	return value >= 0 ?
		static_cast<uint64_t>(value) << 1 :
		(static_cast<uint64_t>(-value) << 1) - 1;
}

static inline void fasim_put_delta_varint(std::string &out,
                                          int64_t value,
                                          int64_t &previous)
{
	const int64_t delta = value - previous;
	fasim_put_varint(out, fasim_zigzag_i64(delta));
	previous = value;
}

static inline void fasim_put_bytes(std::string &out, const std::string &value)
{
	fasim_put_varint(out, static_cast<uint64_t>(value.size()));
	out.append(value);
}

struct FasimCigarOp
{
	FasimCigarOp(uint64_t lenValue, char opValue) :
		len(lenValue),
		op(opValue)
	{
	}
	uint64_t len;
	char op;
};

static inline std::vector<FasimCigarOp> fasim_parse_cigar_probe(const std::string &cigar)
{
	std::vector<FasimCigarOp> ops;
	uint64_t len = 0;
	bool haveLen = false;
	for (size_t i = 0; i < cigar.size(); ++i)
	{
		const char ch = cigar[i];
		if (ch >= '0' && ch <= '9')
		{
			len = len * 10 + static_cast<uint64_t>(ch - '0');
			haveLen = true;
			continue;
		}
		if (!haveLen || len == 0)
		{
			cerr << "compact archive probe bad CIGAR: " << cigar << endl;
			abort();
		}
		ops.push_back(FasimCigarOp(len, ch));
		len = 0;
		haveLen = false;
	}
	if (haveLen)
	{
		cerr << "compact archive probe bad trailing CIGAR length: " << cigar << endl;
		abort();
	}
	return ops;
}

static inline uint64_t fasim_cigar_query_len(const std::vector<FasimCigarOp> &cigar)
{
	uint64_t len = 0;
	for (size_t i = 0; i < cigar.size(); ++i)
	{
		const char op = cigar[i].op;
		if (op == 'M' || op == '=' || op == 'X' || op == 'I' || op == 'S')
		{
			len += cigar[i].len;
		}
	}
	return len;
}

static inline uint64_t fasim_cigar_target_len(const std::vector<FasimCigarOp> &cigar)
{
	uint64_t len = 0;
	for (size_t i = 0; i < cigar.size(); ++i)
	{
		const char op = cigar[i].op;
		if (op == 'M' || op == '=' || op == 'X' || op == 'D')
		{
			len += cigar[i].len;
		}
	}
	return len;
}

static inline std::string fasim_cigar_gap_mask(const std::vector<FasimCigarOp> &cigar,
                                               bool queryMask)
{
	uint64_t alignedLen = 0;
	for (size_t i = 0; i < cigar.size(); ++i)
	{
		const char op = cigar[i].op;
		if (op == 'M' || op == '=' || op == 'X' || op == 'I' || op == 'D')
		{
			alignedLen += cigar[i].len;
		}
	}
	std::string mask(static_cast<size_t>((alignedLen + 7) / 8), '\0');
	uint64_t pos = 0;
	for (size_t i = 0; i < cigar.size(); ++i)
	{
		const char op = cigar[i].op;
		const uint64_t len = cigar[i].len;
		if (op != 'M' && op != '=' && op != 'X' && op != 'I' && op != 'D')
		{
			continue;
		}
		const bool gap = queryMask ? op == 'D' : op == 'I';
		if (gap)
		{
			for (uint32_t j = 0; j < len; ++j)
			{
				const uint64_t bit = pos + j;
				mask[static_cast<size_t>(bit / 8)] =
					static_cast<char>(
						static_cast<unsigned char>(
							mask[static_cast<size_t>(bit / 8)]) |
						static_cast<unsigned char>(1u << (bit % 8)));
			}
		}
		pos += len;
	}
	return mask;
}

static inline uint64_t fasim_cigar_aligned_len(const std::vector<FasimCigarOp> &cigar)
{
	uint64_t len = 0;
	for (size_t i = 0; i < cigar.size(); ++i)
	{
		const char op = cigar[i].op;
		if (op == 'M' || op == '=' || op == 'X' || op == 'I' || op == 'D')
		{
			len += cigar[i].len;
		}
	}
	return len;
}

static inline int fasim_compact_strand_code(int reverse, int strand)
{
	const std::string value = getStrand(reverse, strand);
	if (value == "ParaPlus")
	{
		return 0;
	}
	if (value == "ParaMinus")
	{
		return 1;
	}
	if (value == "AntiPlus")
	{
		return 2;
	}
	if (value == "AntiMinus")
	{
		return 3;
	}
	return -1;
}

struct FasimCompactArchiveProbeWriter
{
	FasimCompactArchiveProbeWriter() :
		opened(false),
		previousQueryStart(0),
		previousSeqStart(0),
		previousScore(0)
	{
	}

	void open(const std::string &path)
	{
		file.open(path.c_str(), ios::binary | ios::trunc);
		if (!file.is_open())
		{
			cerr << "failed to open compact archive probe: " << path << endl;
			abort();
		}
		static const char magic[] = "FATFOD1";
		file.write(magic, 8);
		const uint32_t version = 1;
		file.write(reinterpret_cast<const char*>(&version), sizeof(version));
		opened = true;
	}

	void write_row(const triplex &atr,
	               int motif,
	               int middle,
	               int center)
	{
		if (!opened)
		{
			return;
		}
		const int strandCode =
			fasim_compact_strand_code(atr.reverse, atr.strand);
		if (strandCode < 0 ||
		    atr.starj >= atr.endj ||
		    !atr.chr.empty() ||
		    atr.genomestart != atr.starj ||
		    atr.genomeend != atr.endj ||
		    motif != 0 ||
		    middle != center)
		{
			cerr << "compact archive probe unsupported row shape" << endl;
			abort();
		}
		if (atr.cigar_probe.empty())
		{
			cerr << "compact archive probe missing CIGAR" << endl;
			abort();
		}
		const std::vector<FasimCigarOp> cigar =
			fasim_parse_cigar_probe(atr.cigar_probe);
		const uint64_t alignedLen = fasim_cigar_aligned_len(cigar);
		const uint64_t queryLen = fasim_cigar_query_len(cigar);
		const uint64_t targetLen = fasim_cigar_target_len(cigar);
		if (queryLen == 0 || targetLen == 0 ||
		    atr.endi != atr.stari + static_cast<int>(queryLen) - 1 ||
		    atr.endj != atr.starj + static_cast<int>(targetLen) - 1 ||
		    atr.nt != static_cast<int>(alignedLen))
		{
			cerr << "compact archive probe unsupported CIGAR-derived row"
			     << endl;
			abort();
		}
		std::string row;
		fasim_put_delta_varint(row, atr.stari, previousQueryStart);
		fasim_put_delta_varint(row, atr.starj, previousSeqStart);
		fasim_put_delta_varint(row, static_cast<int64_t>(atr.score), previousScore);
		fasim_put_varint(row, alignedLen);
		fasim_put_varint(row, queryLen);
		fasim_put_varint(row, targetLen);
		fasim_put_varint(row, static_cast<uint64_t>(atr.rule));
		fasim_put_varint(row, static_cast<uint64_t>(atr.nt));
		const uint64_t flags = static_cast<uint64_t>(strandCode << 1);
		fasim_put_varint(row, flags);
		{
			std::ostringstream value;
			value << atr.tri_score;
			fasim_put_bytes(row, value.str());
		}
		{
			std::ostringstream value;
			value << atr.identity;
			fasim_put_bytes(row, value.str());
		}
		fasim_put_bytes(row, fasim_cigar_gap_mask(cigar, true));
		fasim_put_bytes(row, fasim_cigar_gap_mask(cigar, false));
		std::string prefix;
		fasim_put_varint(prefix, static_cast<uint64_t>(row.size()));
		file.write(prefix.data(), static_cast<std::streamsize>(prefix.size()));
		file.write(row.data(), static_cast<std::streamsize>(row.size()));
	}

	void close()
	{
		if (opened)
		{
			file.close();
			opened = false;
		}
	}

	bool opened;
	ofstream file;
	int64_t previousQueryStart;
	int64_t previousSeqStart;
	int64_t previousScore;
};

struct FasimLiteRow
{
	std::string text;
	std::string key;
	double score;
	double nt;
	double identity;
	double stability;
	uint64_t scoreinfo_rank;
};

struct FasimScoreInfoRankBuckets
{
	FasimScoreInfoRankBuckets() :
		rows(0),
		unknown_rows(0),
		max_rank(0),
		rank1(0),
		rank2_4(0),
		rank5_8(0),
		rank9_16(0),
		rank17_32(0),
		rank33_plus(0)
	{
	}

	uint64_t rows;
	uint64_t unknown_rows;
	uint64_t max_rank;
	uint64_t rank1;
	uint64_t rank2_4;
	uint64_t rank5_8;
	uint64_t rank9_16;
	uint64_t rank17_32;
	uint64_t rank33_plus;
};

static inline void fasim_record_scoreinfo_rank_bucket(FasimScoreInfoRankBuckets &buckets,
                                                      uint64_t rank)
{
	++buckets.rows;
	if (rank == 0)
	{
		++buckets.unknown_rows;
		return;
	}
	buckets.max_rank = std::max(buckets.max_rank, rank);
	if (rank <= 1)
	{
		++buckets.rank1;
	}
	else if (rank <= 4)
	{
		++buckets.rank2_4;
	}
	else if (rank <= 8)
	{
		++buckets.rank5_8;
	}
	else if (rank <= 16)
	{
		++buckets.rank9_16;
	}
	else if (rank <= 32)
	{
		++buckets.rank17_32;
	}
	else
	{
		++buckets.rank33_plus;
	}
}

static inline FasimLiteRow fasim_make_lite_row(const std::string &chr,
                                               long genomestart,
                                               long genomeend,
                                               const triplex &atr,
                                               uint64_t scoreinfoRank = 0)
{
	if (scoreinfoRank == 0 && atr.neartriplex < 0)
	{
		scoreinfoRank = static_cast<uint64_t>(-atr.neartriplex);
	}
	std::ostringstream out;
	out << chr << "\t"
	    << genomestart << "\t"
	    << genomeend << "\t"
	    << getStrand(atr.reverse, atr.strand) << "\t"
	    << atr.rule << "\t"
	    << atr.stari << "\t"
	    << atr.endi << "\t"
	    << atr.starj << "\t"
	    << atr.endj << "\t"
	    << (atr.starj < atr.endj ? "R" : "L") << "\t"
	    << atr.score << "\t"
	    << atr.nt << "\t"
	    << atr.identity << "\t"
	    << atr.tri_score;
	FasimLiteRow row;
	row.text = out.str();
	row.key = row.text;
	row.score = static_cast<double>(atr.score);
	row.nt = static_cast<double>(atr.nt);
	row.identity = static_cast<double>(atr.identity);
	row.stability = static_cast<double>(atr.tri_score);
	row.scoreinfo_rank = scoreinfoRank;
	return row;
}

enum FasimLiteTopkMode
{
	FASIM_LITE_TOPK_SCORE = 0,
	FASIM_LITE_TOPK_STABILITY = 1,
	FASIM_LITE_TOPK_NT_SCORE = 2,
};

static inline bool fasim_lite_row_less_for_mode(const FasimLiteRow &lhs,
                                                const FasimLiteRow &rhs,
                                                FasimLiteTopkMode mode)
{
	if (mode == FASIM_LITE_TOPK_SCORE)
	{
		if (lhs.score != rhs.score) return lhs.score > rhs.score;
		if (lhs.nt != rhs.nt) return lhs.nt > rhs.nt;
		if (lhs.stability != rhs.stability) return lhs.stability > rhs.stability;
	}
	else if (mode == FASIM_LITE_TOPK_STABILITY)
	{
		if (lhs.stability != rhs.stability) return lhs.stability > rhs.stability;
		if (lhs.nt != rhs.nt) return lhs.nt > rhs.nt;
		if (lhs.score != rhs.score) return lhs.score > rhs.score;
	}
	else
	{
		if (lhs.nt != rhs.nt) return lhs.nt > rhs.nt;
		if (lhs.score != rhs.score) return lhs.score > rhs.score;
		if (lhs.stability != rhs.stability) return lhs.stability > rhs.stability;
	}
	return lhs.key > rhs.key;
}

static inline void fasim_write_topk_lite_rows(std::ofstream &out,
                                              const std::vector<FasimLiteRow> &rows,
                                              int topk,
                                              FasimScoreInfoRankBuckets *rankBuckets = NULL)
{
	std::map<std::string, FasimLiteRow> selected;
	const FasimLiteTopkMode modes[] = {
		FASIM_LITE_TOPK_SCORE,
		FASIM_LITE_TOPK_STABILITY,
		FASIM_LITE_TOPK_NT_SCORE,
	};
	for (size_t modeIndex = 0; modeIndex < sizeof(modes) / sizeof(modes[0]); ++modeIndex)
	{
		std::vector<size_t> order(rows.size());
		for (size_t i = 0; i < rows.size(); ++i)
		{
			order[i] = i;
		}
		std::sort(order.begin(), order.end(),
		          [&](size_t lhs, size_t rhs)
		          {
			          return fasim_lite_row_less_for_mode(rows[lhs], rows[rhs], modes[modeIndex]);
		          });
		const size_t take = std::min(static_cast<size_t>(topk), order.size());
			for (size_t i = 0; i < take; ++i)
			{
				selected[rows[order[i]].key] = rows[order[i]];
			}
	}
	for (std::map<std::string, FasimLiteRow>::const_iterator it = selected.begin();
	     it != selected.end();
	     ++it)
	{
		if (rankBuckets != NULL)
		{
			fasim_record_scoreinfo_rank_bucket(*rankBuckets, it->second.scoreinfo_rank);
		}
		out << it->second.text << "\n";
	}
}

static inline const char *fasim_lite_topk_mode_name(FasimLiteTopkMode mode)
{
	if (mode == FASIM_LITE_TOPK_SCORE)
	{
		return "score";
	}
	if (mode == FASIM_LITE_TOPK_STABILITY)
	{
		return "stability";
	}
	return "nt_score";
}

static inline void fasim_write_topk_lite_rank_dump(const std::string &path,
                                                   const std::vector<FasimLiteRow> &rows,
                                                   int topk)
{
	std::ofstream out(path.c_str(), ios::trunc);
	if (!out.is_open())
	{
		cerr << "failed to open topk rank dump file: " << path << endl;
		abort();
	}
	out << "mode\trank_in_mode\tscoreinfo_rank\tkey\n";
	const FasimLiteTopkMode modes[] = {
		FASIM_LITE_TOPK_SCORE,
		FASIM_LITE_TOPK_STABILITY,
		FASIM_LITE_TOPK_NT_SCORE,
	};
	for (size_t modeIndex = 0; modeIndex < sizeof(modes) / sizeof(modes[0]); ++modeIndex)
	{
		std::vector<size_t> order(rows.size());
		for (size_t i = 0; i < rows.size(); ++i)
		{
			order[i] = i;
		}
		const FasimLiteTopkMode mode = modes[modeIndex];
		std::sort(order.begin(), order.end(),
		          [&](size_t lhs, size_t rhs)
		          {
			          return fasim_lite_row_less_for_mode(rows[lhs], rows[rhs], mode);
		          });
		const size_t take = std::min(static_cast<size_t>(topk), order.size());
		for (size_t i = 0; i < take; ++i)
		{
			const FasimLiteRow &row = rows[order[i]];
			out << fasim_lite_topk_mode_name(mode) << "\t"
			    << (i + 1) << "\t"
			    << row.scoreinfo_rank << "\t"
			    << row.key << "\n";
		}
	}
}

} // namespace

struct lgInfo
{
	lgInfo() {};
	lgInfo(const string &s1, const string &s2, const string &s3, const string &s4,
		const string &s5, const string &s6, int s7, const string &s8) :
		lncName(s1), lncSeq(s2), species(s3), dnaChroTag(s4), fileName(s5),
		dnaSeq(s6), startGenome(s7), resultDir(s8) {};
	string lncName;
	string lncSeq;
	string species;
	string dnaChroTag;
	string fileName;
	string dnaSeq;
	int startGenome;
	string resultDir;
};


struct axis
{
	axis(int n1 = 0, int n2 = 0) :
		triplexnum(n1), neartriplex(n2) {};
	int triplexnum;
	int neartriplex;
};

void show_help();
void initEnv(int argc, char * const *argv, struct para &paraList);
void LongTarget(struct para &paraList, string rnaSequence, string dnaSequence,
	vector<struct triplex> &sort_triplex_list);

bool comp(const triplex &a, const triplex &b);
string getStrand(int reverse, int strand);
int same_seq(const string &w_str);
void printResult(string &species, struct para paraList, string &lncName,
	string &dnaFile, vector<struct triplex> &sort_triplex_list,
	string &chroTag, string &dnaSequence, int start_genome,
	string &c_tmp_dd, string &c_tmp_length, string &resultDir,string lncSeq);
void readDna(string dnaFileName, vector<string> &speciess, vector<string> &chroTags,vector<long> &startGenomes,vector<string> &dnaSeqs);
string readRna(string rnaFileName, string &lncName);
void cluster_triplex(int dd, int length, vector<struct triplex>& triplex_list, map<size_t, size_t> class1[], map<size_t, size_t> class1a[], map<size_t, size_t> class1b[], int class_level);
void print_cluster(int c_level, map<size_t, size_t> class1[], int start_genome, string &chro_info, int dna_size, string &rna_name, int distance, int length, string &outFilePath, string &c_tmp_dd, string &c_tmp_length, vector<struct tmp_class> &w_tmp_class);

struct FasimGpuDpColumnAutoObservation
{
	uint64_t cells;
	uint64_t windows;
};

static inline uint64_t fasim_saturating_add_uint64(uint64_t lhs, uint64_t rhs)
{
	const uint64_t maxValue = ~static_cast<uint64_t>(0);
	if (maxValue - lhs < rhs)
	{
		return maxValue;
	}
	return lhs + rhs;
}

static inline uint64_t fasim_saturating_mul_uint64(uint64_t lhs, uint64_t rhs)
{
	const uint64_t maxValue = ~static_cast<uint64_t>(0);
	if (lhs != 0 && rhs > maxValue / lhs)
	{
		return maxValue;
	}
	return lhs * rhs;
}

static inline void fasim_print_top5_phase_timing_stats(const FasimTop5PhaseTimingStats &stats)
{
	std::cerr << "benchmark.fasim_top5_gasal2_phase_timing_enabled=1\n";
	std::cerr << "benchmark.fasim_transfer_string_table_enabled="
	          << (fasim_transfer_string_table_requested_runtime() ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_records=" << stats.records << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_windows=" << stats.windows << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_tasks=" << stats.tasks << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_flushes=" << stats.flushes << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_flush_tasks=" << stats.flush_tasks << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_cuda_topk_batches=" << stats.cuda_topk_batches << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_cuda_topk_tasks=" << stats.cuda_topk_tasks << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_cuda_topk_deferred_batches=" << stats.cuda_topk_deferred_batches << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_cuda_topk_deferred_tasks=" << stats.cuda_topk_deferred_tasks << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_single_pass_topn_enabled=" << (stats.single_pass_topn_enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_single_pass_topn_batches=" << stats.single_pass_topn_batches << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_single_pass_topn_tasks=" << stats.single_pass_topn_tasks << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_single_pass_topn_scoreinfo_groups=" << stats.single_pass_topn_scoreinfo_groups << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_enabled=" << (stats.exact_scoreinfo_gpu_enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_enabled=" << (stats.exact_scoreinfo_gpu_pruned_output_enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_column_pruned_output_enabled=" << (stats.exact_scoreinfo_gpu_column_pruned_output_enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_batches=" << stats.exact_scoreinfo_gpu_batches << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_tasks=" << stats.exact_scoreinfo_gpu_tasks << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_overflow_batches=" << stats.exact_scoreinfo_gpu_overflow_batches << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_fallback_batches=" << stats.exact_scoreinfo_gpu_fallback_batches << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_batches=" << stats.exact_scoreinfo_gpu_pruned_output_batches << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_input_groups=" << stats.exact_scoreinfo_gpu_pruned_output_input_groups << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_kept_groups=" << stats.exact_scoreinfo_gpu_pruned_output_kept_groups << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_pruned_groups=" << stats.exact_scoreinfo_gpu_pruned_output_pruned_groups << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_pruned_output_pruned_tasks=" << stats.exact_scoreinfo_gpu_pruned_output_pruned_tasks << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_column_batches=" << stats.exact_column_batches << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_column_tasks=" << stats.exact_column_tasks << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_column_cells=" << stats.exact_column_cells << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_groups=" << stats.exact_scoreinfo_groups << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_prune_enabled=" << (stats.scoreinfo_prune_enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_prune_max_per_task=" << stats.scoreinfo_prune_max_per_task << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_prune_input_groups=" << stats.scoreinfo_prune_input_groups << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_prune_kept_groups=" << stats.scoreinfo_prune_kept_groups << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_prune_pruned_groups=" << stats.scoreinfo_prune_pruned_groups << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_prune_pruned_tasks=" << stats.scoreinfo_prune_pruned_tasks << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_enabled=" << (stats.scoreinfo_emit_rank_observe_enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_alignments=" << stats.scoreinfo_emit_rank_observe_alignments << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_max_rank=" << stats.scoreinfo_emit_rank_observe_max_rank << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_rank1=" << stats.scoreinfo_emit_rank_observe_rank1 << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_rank2_4=" << stats.scoreinfo_emit_rank_observe_rank2_4 << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_rank5_8=" << stats.scoreinfo_emit_rank_observe_rank5_8 << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_rank9_16=" << stats.scoreinfo_emit_rank_observe_rank9_16 << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_rank17_32=" << stats.scoreinfo_emit_rank_observe_rank17_32 << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_emit_rank_observe_rank33_plus=" << stats.scoreinfo_emit_rank_observe_rank33_plus << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_enabled=" << (stats.scoreinfo_topk_lite_rank_observe_enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rows=" << stats.scoreinfo_topk_lite_rank_observe_rows << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_unknown_rows=" << stats.scoreinfo_topk_lite_rank_observe_unknown_rows << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_max_rank=" << stats.scoreinfo_topk_lite_rank_observe_max_rank << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rank1=" << stats.scoreinfo_topk_lite_rank_observe_rank1 << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rank2_4=" << stats.scoreinfo_topk_lite_rank_observe_rank2_4 << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rank5_8=" << stats.scoreinfo_topk_lite_rank_observe_rank5_8 << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rank9_16=" << stats.scoreinfo_topk_lite_rank_observe_rank9_16 << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rank17_32=" << stats.scoreinfo_topk_lite_rank_observe_rank17_32 << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_scoreinfo_topk_lite_rank_observe_rank33_plus=" << stats.scoreinfo_topk_lite_rank_observe_rank33_plus << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_selected_alignments=" << stats.gasal2_selected_alignments << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_convert_input_alignments=" << stats.gasal2_convert_input_alignments << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_convert_triplexes_raw=" << stats.gasal2_convert_triplexes_raw << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_convert_tasks=" << stats.gasal2_convert_tasks << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_convert_tasks_with_input=" << stats.gasal2_convert_tasks_with_input << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_emit_candidates=" << stats.gasal2_emit_candidates << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_emit_filtered_score=" << stats.gasal2_emit_filtered_score << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_emit_filtered_identity=" << stats.gasal2_emit_filtered_identity << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_emit_filtered_stability=" << stats.gasal2_emit_filtered_stability << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_emit_filtered_nt=" << stats.gasal2_emit_filtered_nt << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_emit_rows_lite=" << stats.gasal2_emit_rows_lite << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_emit_rows_full=" << stats.gasal2_emit_rows_full << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_query_span_lt_clength=" << stats.gasal2_nt_shadow_query_span_lt_clength << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_ref_span_lt_clength=" << stats.gasal2_nt_shadow_ref_span_lt_clength << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_min_span_lt_clength=" << stats.gasal2_nt_shadow_min_span_lt_clength << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_max_span_lt_clength=" << stats.gasal2_nt_shadow_max_span_lt_clength << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_sum_span_lt_clength=" << stats.gasal2_nt_shadow_sum_span_lt_clength << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_query_span_false_negative=" << stats.gasal2_nt_shadow_query_span_false_negative << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_ref_span_false_negative=" << stats.gasal2_nt_shadow_ref_span_false_negative << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_min_span_false_negative=" << stats.gasal2_nt_shadow_min_span_false_negative << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_max_span_false_negative=" << stats.gasal2_nt_shadow_max_span_false_negative << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_nt_shadow_sum_span_false_negative=" << stats.gasal2_nt_shadow_sum_span_false_negative << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_nt_sum_span_prune_active=" << stats.gasal2_nt_sum_span_prune_active << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_extend_batches=" << stats.gasal2_extend_batches << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_extend_tasks=" << stats.gasal2_extend_tasks << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_supported=" << (stats.gasal2_query_preflight_supported ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_query_len=" << stats.gasal2_query_preflight_query_len << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_query_preflight_max_query_len=" << stats.gasal2_query_preflight_max_query_len << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_read_rna_seconds=" << stats.read_rna_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_output_open_seconds=" << stats.output_open_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_auto_observe_seconds=" << stats.auto_observe_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_cuda_query_init_seconds=" << stats.cuda_query_init_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_fasta_read_seconds=" << stats.fasta_read_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_cut_sequence_seconds=" << stats.cut_sequence_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_enqueue_seconds=" << stats.enqueue_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_transfer_string_seconds=" << stats.transfer_string_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_transfer_table_seconds=" << stats.transfer_table_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_transfer_reverse_seconds=" << stats.transfer_reverse_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_src_transform_seconds=" << stats.src_transform_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_transfer_calls=" << stats.transfer_calls << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_transfer_bytes=" << stats.transfer_bytes << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_transfer_reverse_calls=" << stats.transfer_reverse_calls << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_src_transform_calls=" << stats.src_transform_calls << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_src_transform_bytes=" << stats.src_transform_bytes << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_src_transform_orig=" << stats.src_transform_orig << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_src_transform_comp=" << stats.src_transform_comp << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_src_transform_rev=" << stats.src_transform_rev << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_src_transform_revcomp=" << stats.src_transform_revcomp << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_encode_seconds=" << stats.encode_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_encode_dual_seconds=" << stats.encode_dual_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_encode_prealign_seconds=" << stats.encode_prealign_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_encode_legacy_seconds=" << stats.encode_legacy_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_flush_total_seconds=" << stats.flush_total_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_cuda_topk_wall_seconds=" << stats.cuda_topk_wall_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_cuda_topk_kernel_seconds=" << stats.cuda_topk_kernel_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_wall_seconds=" << stats.exact_scoreinfo_gpu_wall_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_kernel_seconds=" << stats.exact_scoreinfo_gpu_kernel_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_h2d_seconds=" << stats.exact_scoreinfo_gpu_h2d_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_gpu_d2h_seconds=" << stats.exact_scoreinfo_gpu_d2h_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_column_wall_seconds=" << stats.exact_column_wall_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_column_kernel_seconds=" << stats.exact_column_kernel_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_column_h2d_seconds=" << stats.exact_column_h2d_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_column_d2h_seconds=" << stats.exact_column_d2h_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_min_score_seconds=" << stats.exact_min_score_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_exact_scoreinfo_build_seconds=" << stats.exact_scoreinfo_build_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_extend_wall_seconds=" << stats.gasal2_extend_wall_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_convert_alignment_seconds=" << stats.gasal2_convert_alignment_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_convert_sort_seconds=" << stats.gasal2_convert_sort_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_convert_filter_seconds=" << stats.gasal2_convert_filter_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_gasal2_convert_rank_map_seconds=" << stats.gasal2_convert_rank_map_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_cpu_fallback_scoreinfo_seconds=" << stats.cpu_fallback_scoreinfo_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_cpu_fallback_extend_seconds=" << stats.cpu_fallback_extend_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_output_write_seconds=" << stats.output_write_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_output_close_seconds=" << stats.output_close_seconds << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_phase_query_release_seconds=" << stats.query_release_seconds << "\n";
}

static inline const char *fasim_min_score_shadow_source_name(FasimMinScoreShadowSource source)
{
	switch (source)
	{
	case FASIM_MIN_SCORE_SHADOW_SOURCE_GPU_ROW:
		return "gpu_row";
	case FASIM_MIN_SCORE_SHADOW_SOURCE_GPU_LEGACY_ROW:
		return "gpu_legacy_row";
	case FASIM_MIN_SCORE_SHADOW_SOURCE_TOPK:
		return "topk";
	case FASIM_MIN_SCORE_SHADOW_SOURCE_NONE:
	default:
		return "none";
	}
}

static inline void fasim_print_exact_column_min_score_shadow_stats(
	const FasimExactColumnMinScoreShadowStats &stats)
{
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_enabled=1\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_tasks=" << stats.tasks << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_gpu_row_score_mismatches=" << stats.gpu_row_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_gpu_row_min_score_mismatches=" << stats.gpu_row_min_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_gpu_row_gt_cpu=" << stats.gpu_row_gt_cpu << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_gpu_row_lt_cpu=" << stats.gpu_row_lt_cpu << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_gpu_row_max_abs_diff=" << stats.gpu_row_max_abs_diff << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_gpu_legacy_row_score_mismatches=" << stats.gpu_legacy_row_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_gpu_legacy_row_min_score_mismatches=" << stats.gpu_legacy_row_min_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_gpu_legacy_row_gt_cpu=" << stats.gpu_legacy_row_gt_cpu << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_gpu_legacy_row_lt_cpu=" << stats.gpu_legacy_row_lt_cpu << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_gpu_legacy_row_max_abs_diff=" << stats.gpu_legacy_row_max_abs_diff << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_topk_score_mismatches=" << stats.topk_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_topk_min_score_mismatches=" << stats.topk_min_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_topk_gt_cpu=" << stats.topk_gt_cpu << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_topk_lt_cpu=" << stats.topk_lt_cpu << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_topk_max_abs_diff=" << stats.topk_max_abs_diff << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_source="
	          << fasim_min_score_shadow_source_name(stats.first_source) << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_task=" << stats.first_task_ordinal << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_rule=" << stats.first_rule << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_strand=" << stats.first_strand << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_para=" << stats.first_para << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_target_len=" << stats.first_target_len << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_cpu_score=" << stats.first_cpu_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_cpu_min_score=" << stats.first_cpu_min_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_row_score=" << stats.first_gpu_row_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_row_min_score=" << stats.first_gpu_row_min_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_legacy_row_score=" << stats.first_gpu_legacy_row_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_legacy_row_min_score=" << stats.first_gpu_legacy_row_min_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_topk_score=" << stats.first_topk_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_topk_min_score=" << stats.first_topk_min_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_row_task=" << stats.first_gpu_row_task << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_row_rule=" << stats.first_gpu_row_rule << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_row_strand=" << stats.first_gpu_row_strand << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_row_para=" << stats.first_gpu_row_para << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_row_target_len=" << stats.first_gpu_row_target_len << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_row_cpu_score=" << stats.first_gpu_row_cpu_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_row_cpu_min_score=" << stats.first_gpu_row_cpu_min_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_row_score_value=" << stats.first_gpu_row_score_value << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_row_min_score_value=" << stats.first_gpu_row_min_score_value << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_legacy_row_task=" << stats.first_gpu_legacy_row_task << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_legacy_row_rule=" << stats.first_gpu_legacy_row_rule << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_legacy_row_strand=" << stats.first_gpu_legacy_row_strand << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_legacy_row_para=" << stats.first_gpu_legacy_row_para << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_legacy_row_target_len=" << stats.first_gpu_legacy_row_target_len << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_legacy_row_cpu_score=" << stats.first_gpu_legacy_row_cpu_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_legacy_row_cpu_min_score=" << stats.first_gpu_legacy_row_cpu_min_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_legacy_row_score_value=" << stats.first_gpu_legacy_row_score_value << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_gpu_legacy_row_min_score_value=" << stats.first_gpu_legacy_row_min_score_value << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_topk_task=" << stats.first_topk_task << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_topk_rule=" << stats.first_topk_rule << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_topk_strand=" << stats.first_topk_strand << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_topk_para=" << stats.first_topk_para << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_topk_target_len=" << stats.first_topk_target_len << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_topk_cpu_score=" << stats.first_topk_cpu_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_topk_cpu_min_score=" << stats.first_topk_cpu_min_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_topk_score_value=" << stats.first_topk_score_value << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_first_topk_min_score_value=" << stats.first_topk_min_score_value << "\n";
	std::cerr << "benchmark.fasim_exact_column_min_score_shadow_seconds=" << stats.seconds << "\n";
}

static inline void fasim_prepare_gasal2_long_query_segmented_shadow_stats(
	const std::string &query,
	FasimGasal2LongQueryShadowStats *stats)
{
	if (stats == NULL)
	{
		return;
	}
	stats->requested =
		fasim_gasal2_long_query_segmented_shadow_requested_runtime() ? 1ULL : 0ULL;
	stats->active = 0;
	if (stats->requested == 0)
	{
		return;
	}

	const std::chrono::steady_clock::time_point begin =
		std::chrono::steady_clock::now();
	const size_t tileLen = fasim_gasal2_long_query_segmented_tile_len_runtime();
	const size_t tileOverlap =
		fasim_gasal2_long_query_segmented_tile_overlap_runtime();
	const size_t maxSegments =
		fasim_gasal2_long_query_segmented_max_segments_runtime();
	const std::vector<FasimGasal2LongQuerySegment> segments =
		fasim_build_gasal2_long_query_segments(query,
		                                       tileLen,
		                                       tileOverlap,
		                                       maxSegments);

	stats->query_len = static_cast<uint64_t>(query.size());
	stats->tile_len = static_cast<uint64_t>(tileLen);
	stats->tile_overlap = static_cast<uint64_t>(tileOverlap);
	stats->segments = static_cast<uint64_t>(segments.size());
	stats->gasal2_requests = 0;
	stats->traceback_requests = 0;
	stats->fallbacks = 0;
	stats->total_seconds = fasim_seconds_since(begin);
}

static inline void fasim_print_gasal2_long_query_segmented_shadow_stats(
	const FasimGasal2LongQueryShadowStats &stats)
{
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_requested="
	          << stats.requested << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_active="
	          << stats.active << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_query_len="
	          << stats.query_len << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_tile_len="
	          << stats.tile_len << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_tile_overlap="
	          << stats.tile_overlap << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_segments="
	          << stats.segments << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_gasal2_requests="
	          << stats.gasal2_requests << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_traceback_requests="
	          << stats.traceback_requests << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_fallbacks="
	          << stats.fallbacks << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_scoreinfo_max_per_task="
	          << stats.scoreinfo_max_per_task << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_scoreinfo_prune_mode="
	          << fasim_gasal2_long_query_segmented_scoreinfo_prune_mode_runtime() << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_scoreinfo_input_groups="
	          << stats.scoreinfo_input_groups << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_scoreinfo_kept_groups="
	          << stats.scoreinfo_kept_groups << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_scoreinfo_pruned_groups="
	          << stats.scoreinfo_pruned_groups << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_segmented_shadow_total_seconds="
	          << stats.total_seconds << "\n";
}

static inline void fasim_prepare_gasal2_long_query_exact_tile_shadow_stats(
	const std::string &query,
	FasimGasal2LongQueryExactTileShadowStats *stats)
{
	if (stats == NULL)
	{
		return;
	}
	stats->requested =
		fasim_gasal2_long_query_exact_tile_shadow_requested_runtime() ? 1ULL : 0ULL;
	stats->active = 0;
	if (stats->requested == 0)
	{
		return;
	}

	const size_t tileLen = fasim_gasal2_long_query_exact_tile_len_runtime();
	size_t tileOverlap = fasim_gasal2_long_query_exact_tile_overlap_runtime();
	if (tileOverlap >= tileLen)
	{
		tileOverlap = 0;
	}
	const std::vector<FasimGasal2LongQuerySegment> tiles =
		fasim_build_gasal2_long_query_segments(query,
		                                       tileLen,
		                                       tileOverlap,
		                                       0);
	stats->query_len = static_cast<uint64_t>(query.size());
	stats->tile_len = static_cast<uint64_t>(tileLen);
	stats->tile_overlap = static_cast<uint64_t>(tileOverlap);
	stats->tiles = static_cast<uint64_t>(tiles.size());
	stats->tile_descriptors = static_cast<uint64_t>(tiles.size());
	uint64_t descriptorDigest = 1469598103934665603ULL;
	uint64_t tileMaxQueryLen = 0;
	for (size_t i = 0; i < tiles.size(); ++i)
	{
		const FasimGasal2LongQuerySegment &tile = tiles[i];
		const uint64_t tileQueryLen =
			static_cast<uint64_t>(tile.query_segment.size());
		tileMaxQueryLen = std::max(tileMaxQueryLen, tileQueryLen);
		descriptorDigest ^=
			static_cast<uint64_t>(i) + 0x9e3779b97f4a7c15ULL +
			(descriptorDigest << 6) + (descriptorDigest >> 2);
		descriptorDigest ^=
			static_cast<uint64_t>(tile.global_query_start) +
			0x9e3779b97f4a7c15ULL + (descriptorDigest << 6) +
			(descriptorDigest >> 2);
		descriptorDigest ^=
			static_cast<uint64_t>(tile.global_query_end) +
			0x9e3779b97f4a7c15ULL + (descriptorDigest << 6) +
			(descriptorDigest >> 2);
		descriptorDigest ^=
			tileQueryLen + 0x9e3779b97f4a7c15ULL +
			(descriptorDigest << 6) + (descriptorDigest >> 2);
	}
	stats->tile_max_query_len = tileMaxQueryLen;
	stats->tile_descriptor_digest = descriptorDigest;
}

static inline void fasim_print_gasal2_long_query_exact_tile_shadow_stats(
	const FasimGasal2LongQueryExactTileShadowStats &stats)
{
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_requested="
	          << stats.requested << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_active="
	          << stats.active << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_query_len="
	          << stats.query_len << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_len="
	          << stats.tile_len << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_overlap="
	          << stats.tile_overlap << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tiles="
	          << stats.tiles << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_descriptors="
	          << stats.tile_descriptors << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_max_query_len="
	          << stats.tile_max_query_len << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_descriptor_digest="
	          << stats.tile_descriptor_digest << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_cpu_oracle_candidates="
	          << stats.cpu_oracle_candidates << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_tile_candidates="
	          << stats.tile_candidates << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_candidate_missing="
	          << stats.candidate_missing << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_candidate_extra="
	          << stats.candidate_extra << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_position_missing="
	          << stats.position_missing << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_position_extra="
	          << stats.position_extra << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_position_score_mismatches="
	          << stats.position_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_fallback="
	          << stats.fallback << "\n";
	std::cerr << "benchmark.fasim_top5_gasal2_long_query_exact_tile_shadow_total_seconds="
	          << stats.total_seconds << "\n";
}

static inline void fasim_prepare_long_query_exact_column_scoreinfo_shadow_stats(
	const std::string &query,
	FasimLongQueryExactColumnScoreInfoShadowStats *stats)
{
	if (stats == NULL)
	{
		return;
	}
	stats->requested =
		fasim_long_query_exact_column_scoreinfo_shadow_runtime() ? 1ULL : 0ULL;
	stats->active = 0;
	stats->query_len = static_cast<uint64_t>(query.size());
	stats->max_per_task =
		static_cast<uint64_t>(fasim_top5_gasal2_scoreinfo_prune_max_per_task_runtime());
	if (stats->max_per_task == 0)
	{
		stats->max_per_task =
			static_cast<uint64_t>(fasim_exact_column_scoreinfo_gpu_max_per_task_runtime());
	}
}

static inline void fasim_print_long_query_exact_column_scoreinfo_shadow_stats(
	const FasimLongQueryExactColumnScoreInfoShadowStats &stats)
{
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_requested="
	          << stats.requested << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_active="
	          << stats.active << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_query_len="
	          << stats.query_len << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_tasks="
	          << stats.tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_cells="
	          << stats.cells << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_gpu_batches="
	          << stats.gpu_batches << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_gpu_tasks="
	          << stats.gpu_tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_overflow_batches="
	          << stats.overflow_batches << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_fallback_batches="
	          << stats.fallback_batches << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_scoreinfo_mismatches="
	          << stats.scoreinfo_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_gpu_scoreinfo_groups="
	          << stats.gpu_scoreinfo_groups << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_cpu_scoreinfo_groups="
	          << stats.cpu_scoreinfo_groups << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_max_per_task="
	          << stats.max_per_task << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_required_smem="
	          << stats.required_smem_bytes << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_default_smem_limit="
	          << stats.default_smem_limit_bytes << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_optin_smem_limit="
	          << stats.optin_smem_limit_bytes << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_resource_fit="
	          << stats.resource_fit << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_smem_optin_requested="
	          << stats.smem_optin_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_smem_optin_active="
	          << stats.smem_optin_active << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_total_seconds="
	          << stats.total_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_kernel_seconds="
	          << stats.kernel_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_h2d_seconds="
	          << stats.h2d_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_d2h_seconds="
	          << stats.d2h_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_exact_column_scoreinfo_shadow_error="
	          << stats.error << "\n";
}

static inline void fasim_prepare_long_query_streaming_scoreinfo_shadow_stats(
	const std::string &query,
	FasimLongQueryStreamingScoreInfoShadowStats *stats)
{
	if (stats == NULL)
	{
		return;
	}
	stats->requested =
		(fasim_long_query_streaming_scoreinfo_shadow_runtime() ||
		 fasim_long_query_streaming_scoreinfo_two_contract_bridge_runtime() ||
		 fasim_gasal2_score_prepass_state_machine_consumer_shadow_runtime()) ?
			1ULL : 0ULL;
	stats->active = 0;
	stats->query_len = static_cast<uint64_t>(query.size());
	stats->two_contract_requested =
		fasim_long_query_streaming_scoreinfo_two_contract_bridge_runtime() ?
			1ULL : 0ULL;
	stats->score_prepass_state_machine_shadow_requested =
		fasim_gasal2_score_prepass_state_machine_consumer_shadow_runtime() ?
			1ULL : 0ULL;
	if (stats->requested == 0)
	{
		stats->decision = "streaming_scoreinfo_shadow_not_requested";
		return;
	}

	size_t stripeLen = fasim_long_query_streaming_scoreinfo_stripe_len_runtime();
	if (stripeLen == 0)
	{
		stripeLen = 2812;
	}
	stats->stripe_len = static_cast<uint64_t>(stripeLen);
	stats->stripes =
		static_cast<uint64_t>((query.size() + stripeLen - 1) / stripeLen);
	stats->decision = "streaming_scoreinfo_shadow_not_implemented";
}

static inline void fasim_print_long_query_streaming_scoreinfo_shadow_stats(
	const FasimLongQueryStreamingScoreInfoShadowStats &stats)
{
	const bool replacementConsumerShadowRequested =
		fasim_long_query_streaming_scoreinfo_replacement_consumer_shadow_runtime();
	const uint64_t replacementConsumerShadowActive =
		(stats.realpath_extend_flush_segmented_replay_probe_active > 0 ||
		 stats.realpath_extend_flush_segmented_selected_only_replay_probe_active > 0 ||
		 stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_active > 0 ||
		 stats.realpath_extend_flush_full_replay_probe_active > 0 ||
		 stats.realpath_extend_flush_oracle_replay_probe_active > 0) ? 1ULL : 0ULL;
	const uint64_t replacementConsumerShadowTriplexMismatches =
		stats.realpath_extend_flush_segmented_replay_probe_triplex_mismatches +
		stats.realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches +
		stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches +
		stats.realpath_extend_flush_full_replay_probe_triplex_mismatches +
		stats.realpath_extend_flush_oracle_replay_probe_triplex_mismatches;
	int64_t replacementConsumerShadowFirstMismatch = -1;
	std::string replacementConsumerShadowFirstMismatchSource = "none";
	std::string replacementConsumerShadowFirstMismatchKind = "none";
	if (stats.realpath_extend_flush_segmented_replay_probe_triplex_mismatches > 0)
	{
		replacementConsumerShadowFirstMismatch =
			stats.realpath_extend_flush_segmented_replay_probe_first_mismatch_task;
		replacementConsumerShadowFirstMismatchSource = "segmented_replay";
		replacementConsumerShadowFirstMismatchKind = "triplex_mismatch";
	}
	else if (stats.realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches > 0)
	{
		replacementConsumerShadowFirstMismatch =
			stats.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task;
		replacementConsumerShadowFirstMismatchSource = "selected_only";
		replacementConsumerShadowFirstMismatchKind =
			stats.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind;
	}
	else if (stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches > 0)
	{
		replacementConsumerShadowFirstMismatch =
			stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_task;
		replacementConsumerShadowFirstMismatchSource = "grouped_selected";
		replacementConsumerShadowFirstMismatchKind =
			stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_kind;
	}
	else if (stats.realpath_extend_flush_full_replay_probe_triplex_mismatches > 0)
	{
		replacementConsumerShadowFirstMismatchSource = "full_replay";
		replacementConsumerShadowFirstMismatchKind = "triplex_mismatch";
	}
	else if (stats.realpath_extend_flush_oracle_replay_probe_triplex_mismatches > 0)
	{
		replacementConsumerShadowFirstMismatchSource = "oracle_replay";
		replacementConsumerShadowFirstMismatchKind = "triplex_mismatch";
	}
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_requested="
	          << stats.requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_active="
	          << stats.active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_query_len="
	          << stats.query_len << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_stripe_len="
	          << stats.stripe_len << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_stripes="
	          << stats.stripes << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_tasks="
	          << stats.tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cells="
	          << stats.cells << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_unsupported="
	          << stats.unsupported << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_batches="
	          << stats.gpu_batches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_tasks="
	          << stats.gpu_tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_overflow_batches="
	          << stats.overflow_batches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fallback_batches="
	          << stats.fallback_batches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_boundary_state_bytes="
	          << stats.boundary_state_bytes << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared="
	          << stats.legacy_byte_shared << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared_required_smem_bytes="
	          << stats.legacy_byte_shared_required_smem_bytes << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared_default_smem_limit_bytes="
	          << stats.legacy_byte_shared_default_smem_limit_bytes << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_legacy_byte_shared_optin_smem_limit_bytes="
	          << stats.legacy_byte_shared_optin_smem_limit_bytes << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_requested="
	          << stats.gpu_minscore_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_active="
	          << stats.gpu_minscore_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_hot="
	          << stats.gpu_minscore_hot << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_used="
	          << stats.gpu_minscore_used << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_fallbacks="
	          << stats.gpu_minscore_fallbacks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_score_mismatches="
	          << stats.gpu_minscore_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_min_score_mismatches="
	          << stats.gpu_minscore_min_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_wall_seconds="
	          << stats.gpu_minscore_wall_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_kernel_seconds="
	          << stats.gpu_minscore_kernel_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_h2d_seconds="
	          << stats.gpu_minscore_h2d_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_d2h_seconds="
	          << stats.gpu_minscore_d2h_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_minscore_error="
	          << stats.gpu_minscore_error << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_requested="
	          << stats.fused_minscore_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_active="
	          << stats.fused_minscore_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_used="
	          << stats.fused_minscore_used << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_fallbacks="
	          << stats.fused_minscore_fallbacks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_score_mismatches="
	          << stats.fused_minscore_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_min_score_mismatches="
	          << stats.fused_minscore_min_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_kernel_seconds="
	          << stats.fused_minscore_kernel_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_total_seconds="
	          << stats.fused_minscore_total_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_fused_minscore_error="
	          << stats.fused_minscore_error << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_requested="
	          << stats.two_contract_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_active="
	          << stats.two_contract_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_used="
	          << stats.two_contract_used << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_fallbacks="
	          << stats.two_contract_fallbacks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_score_mismatches="
	          << stats.two_contract_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_min_score_mismatches="
	          << stats.two_contract_min_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_scoreinfo_mismatches="
	          << stats.two_contract_scoreinfo_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_total_seconds="
	          << stats.two_contract_total_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_h2d_seconds="
	          << stats.two_contract_h2d_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_kernel_seconds="
	          << stats.two_contract_kernel_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_d2h_seconds="
	          << stats.two_contract_d2h_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_two_contract_error="
	          << stats.two_contract_error << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_scoreinfo_groups="
	          << stats.gpu_scoreinfo_groups << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_scoreinfo_groups="
	          << stats.cpu_scoreinfo_groups << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_scoreinfo_mismatches="
	          << stats.scoreinfo_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_missing="
	          << stats.candidate_missing << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_candidate_extra="
	          << stats.candidate_extra << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_task_index="
	          << stats.first_mismatch_task_index << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_global_task="
	          << stats.first_mismatch_global_task << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_diff_index="
	          << stats.first_mismatch_diff_index << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_kind="
	          << stats.first_mismatch_kind << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_cpu_count="
	          << stats.first_mismatch_cpu_count << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_gpu_count="
	          << stats.first_mismatch_gpu_count << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_cpu_score="
	          << stats.first_mismatch_cpu_score << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_cpu_position="
	          << stats.first_mismatch_cpu_position << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_gpu_score="
	          << stats.first_mismatch_gpu_score << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_gpu_position="
	          << stats.first_mismatch_gpu_position << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_rule="
	          << stats.first_mismatch_rule << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_strand="
	          << stats.first_mismatch_strand << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_para="
	          << stats.first_mismatch_para << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_dna_start_pos="
	          << stats.first_mismatch_dna_start_pos << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_target_len="
	          << stats.first_mismatch_target_len << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_min_score="
	          << stats.first_mismatch_min_score << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_column_window_start="
	          << stats.first_mismatch_column_window_start << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_cpu_column_window="
	          << stats.first_mismatch_cpu_column_window << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_gpu_column_window="
	          << stats.first_mismatch_gpu_column_window << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_first_mismatch_scalar_column_window="
	          << stats.first_mismatch_scalar_column_window << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_pack_seconds="
	          << stats.pack_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_h2d_seconds="
	          << stats.h2d_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_kernel_seconds="
	          << stats.kernel_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_d2h_seconds="
	          << stats.d2h_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_total_seconds="
	          << stats.total_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_cache_hits="
	          << stats.minscore_cache_hits << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_cache_misses="
	          << stats.minscore_cache_misses << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_minscore_seconds="
	          << stats.minscore_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_gpu_call_seconds="
	          << stats.gpu_call_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_validation_seconds="
	          << stats.validation_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_validation_minscore_seconds="
	          << stats.validation_minscore_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_cpu_prealign_seconds="
	          << stats.cpu_prealign_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_compare_seconds="
	          << stats.compare_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_requested="
	          << stats.realpath_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_trust="
	          << stats.realpath_trust << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_used="
	          << stats.realpath_used << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_fallbacks="
	          << stats.realpath_fallbacks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_calls="
	          << stats.realpath_extend_calls << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_seconds="
	          << stats.realpath_extend_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_scoreinfo_groups="
	          << stats.realpath_extend_scoreinfo_groups << "\n";
std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_attempts="
	          << stats.realpath_extend_align_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_requested="
	          << stats.realpath_extend_attempt_probe_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_active="
	          << stats.realpath_extend_attempt_probe_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_calls="
	          << stats.realpath_extend_attempt_probe_calls << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_attempts="
	          << stats.realpath_extend_attempt_probe_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_selected_attempts="
	          << stats.realpath_extend_attempt_probe_selected_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_seconds="
	          << stats.realpath_extend_attempt_probe_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_fallbacks="
	          << stats.realpath_extend_attempt_probe_fallbacks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_attempt_probe_error="
	          << stats.realpath_extend_attempt_probe_error << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_requested="
	          << stats.realpath_extend_segmented_attempt_probe_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_active="
	          << stats.realpath_extend_segmented_attempt_probe_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_segments="
	          << stats.realpath_extend_segmented_attempt_probe_segments << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_calls="
	          << stats.realpath_extend_segmented_attempt_probe_calls << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_attempts="
	          << stats.realpath_extend_segmented_attempt_probe_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_selected_attempts="
	          << stats.realpath_extend_segmented_attempt_probe_selected_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_seconds="
	          << stats.realpath_extend_segmented_attempt_probe_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_segmented_attempt_probe_fallbacks="
	          << stats.realpath_extend_segmented_attempt_probe_fallbacks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_requested="
	          << stats.realpath_extend_flush_segmented_attempt_probe_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_active="
	          << stats.realpath_extend_flush_segmented_attempt_probe_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_flushes="
	          << stats.realpath_extend_flush_segmented_attempt_probe_flushes << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_segments="
	          << stats.realpath_extend_flush_segmented_attempt_probe_segments << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_calls="
	          << stats.realpath_extend_flush_segmented_attempt_probe_calls << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_attempts="
	          << stats.realpath_extend_flush_segmented_attempt_probe_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_selected_attempts="
	          << stats.realpath_extend_flush_segmented_attempt_probe_selected_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_seconds="
	          << stats.realpath_extend_flush_segmented_attempt_probe_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_attempt_probe_fallbacks="
	          << stats.realpath_extend_flush_segmented_attempt_probe_fallbacks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_requested="
	          << stats.realpath_extend_flush_segmented_replay_probe_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_active="
	          << stats.realpath_extend_flush_segmented_replay_probe_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_tasks="
	          << stats.realpath_extend_flush_segmented_replay_probe_tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_selected_attempts="
	          << stats.realpath_extend_flush_segmented_replay_probe_selected_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_align_attempts="
	          << stats.realpath_extend_flush_segmented_replay_probe_align_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_triplex_mismatches="
	          << stats.realpath_extend_flush_segmented_replay_probe_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_seconds="
	          << stats.realpath_extend_flush_segmented_replay_probe_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_fallbacks="
	          << stats.realpath_extend_flush_segmented_replay_probe_fallbacks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_task="
	          << stats.realpath_extend_flush_segmented_replay_probe_first_mismatch_task << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_diff_index="
	          << stats.realpath_extend_flush_segmented_replay_probe_first_mismatch_diff_index << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_count="
	          << stats.realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_count << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_count="
	          << stats.realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_count << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_key="
	          << stats.realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_key << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_key="
	          << stats.realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_key << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_provenance="
	          << stats.realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_provenance << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_requested="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_active="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_tasks="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_selected_attempts="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_selected_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_align_attempts="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_align_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_empty="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_empty << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_legacy_empty="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_legacy_empty << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_less="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_less << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_more="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_more << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_same_count_diff="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_same_count_diff << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_diff_index="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_diff_index << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_count="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_count << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_count="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_count << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_key="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_key << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_key="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_key << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_provenance="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_provenance << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_scoreinfos_with_multiple_triplexes="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_scoreinfos_with_multiple_triplexes << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_seconds="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_requested="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_active="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_attempts="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_align_attempts="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_align_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_scoreinfos="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_selected="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_selected << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_triplex="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_triplex << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_zero_triplex_tasks="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_zero_triplex_tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_empty="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_empty << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_legacy_empty="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_legacy_empty << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_less="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_less << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_more="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_more << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_same_count_diff="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_same_count_diff << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_task="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_task << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_kind="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_kind << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_diff_index="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_diff_index << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_count="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_count << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_count="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_count << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_key="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_key << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_key="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_key << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_provenance="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_provenance << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_provenance="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_provenance << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_seconds="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_requested="
	          << stats.realpath_extend_flush_full_replay_probe_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_active="
	          << stats.realpath_extend_flush_full_replay_probe_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_tasks="
	          << stats.realpath_extend_flush_full_replay_probe_tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_align_attempts="
	          << stats.realpath_extend_flush_full_replay_probe_align_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_triplex_mismatches="
	          << stats.realpath_extend_flush_full_replay_probe_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_fallbacks="
	          << stats.realpath_extend_flush_full_replay_probe_fallbacks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_full_replay_probe_seconds="
	          << stats.realpath_extend_flush_full_replay_probe_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_requested="
	          << stats.realpath_extend_flush_oracle_replay_probe_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_active="
	          << stats.realpath_extend_flush_oracle_replay_probe_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_tasks="
	          << stats.realpath_extend_flush_oracle_replay_probe_tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_triplex_mismatches="
	          << stats.realpath_extend_flush_oracle_replay_probe_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_flush_oracle_replay_probe_seconds="
	          << stats.realpath_extend_flush_oracle_replay_probe_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_requested="
	          << (replacementConsumerShadowRequested ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_active="
	          << replacementConsumerShadowActive << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_tasks="
	          << stats.realpath_extend_flush_segmented_replay_probe_tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_scoreinfo_groups="
	          << stats.realpath_extend_scoreinfo_groups << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_align_attempts="
	          << stats.realpath_extend_flush_segmented_replay_probe_align_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_selected_attempts="
	          << stats.realpath_extend_flush_segmented_replay_probe_selected_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_triplex_mismatches="
	          << replacementConsumerShadowTriplexMismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_segmented_triplex_mismatches="
	          << stats.realpath_extend_flush_segmented_replay_probe_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_selected_only_triplex_mismatches="
	          << stats.realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_grouped_selected_triplex_mismatches="
	          << stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_full_triplex_mismatches="
	          << stats.realpath_extend_flush_full_replay_probe_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_oracle_triplex_mismatches="
	          << stats.realpath_extend_flush_oracle_replay_probe_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_first_mismatch="
	          << replacementConsumerShadowFirstMismatch << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_first_mismatch_source="
	          << replacementConsumerShadowFirstMismatchSource << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_first_mismatch_kind="
	          << replacementConsumerShadowFirstMismatchKind << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_seconds="
	          << (stats.realpath_extend_flush_segmented_replay_probe_seconds +
	              stats.realpath_extend_flush_segmented_selected_only_replay_probe_seconds +
	              stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_seconds +
	              stats.realpath_extend_flush_full_replay_probe_seconds +
	              stats.realpath_extend_flush_oracle_replay_probe_seconds) << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_replacement_consumer_shadow_fallbacks="
	          << (stats.realpath_extend_flush_segmented_replay_probe_fallbacks +
	              stats.realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks +
	              stats.realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks +
	              stats.realpath_extend_flush_full_replay_probe_fallbacks) << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_requested="
	          << stats.score_prepass_state_machine_shadow_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_active="
	          << stats.score_prepass_state_machine_shadow_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_tasks="
	          << stats.score_prepass_state_machine_shadow_tasks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_scoreinfos="
	          << stats.score_prepass_state_machine_shadow_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_attempts="
	          << stats.score_prepass_state_machine_shadow_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_selected_attempts="
	          << stats.score_prepass_state_machine_shadow_selected_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_cpu_align_attempts="
	          << stats.score_prepass_state_machine_shadow_cpu_align_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_cpu_align_cache_requested="
	          << stats.score_prepass_state_machine_shadow_cpu_align_cache_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_cpu_align_cache_lookups="
	          << stats.score_prepass_state_machine_shadow_cpu_align_cache_lookups << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_cpu_align_cache_hits="
	          << stats.score_prepass_state_machine_shadow_cpu_align_cache_hits << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_cpu_align_cache_misses="
	          << stats.score_prepass_state_machine_shadow_cpu_align_cache_misses << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_cpu_align_cache_unique_keys="
	          << stats.score_prepass_state_machine_shadow_cpu_align_cache_unique_keys << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_gasal2_traceback_requested="
	          << stats.score_prepass_state_machine_shadow_gasal2_traceback_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_gasal2_traceback_attempts="
	          << stats.score_prepass_state_machine_shadow_gasal2_traceback_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_gasal2_traceback_selected="
	          << stats.score_prepass_state_machine_shadow_gasal2_traceback_selected << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_gasal2_traceback_fallbacks="
	          << stats.score_prepass_state_machine_shadow_gasal2_traceback_fallbacks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_gasal2_traceback_alignment_mismatches="
	          << stats.score_prepass_state_machine_shadow_gasal2_traceback_alignment_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_gasal2_traceback_triplex_mismatches="
	          << stats.score_prepass_state_machine_shadow_gasal2_traceback_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_gasal2_traceback_seconds="
	          << stats.score_prepass_state_machine_shadow_gasal2_traceback_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_segment_traceback_requested="
	          << stats.score_prepass_state_machine_shadow_segment_traceback_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_segment_traceback_attempts="
	          << stats.score_prepass_state_machine_shadow_segment_traceback_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_segment_traceback_alignment_mismatches="
	          << stats.score_prepass_state_machine_shadow_segment_traceback_alignment_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_segment_traceback_triplex_mismatches="
	          << stats.score_prepass_state_machine_shadow_segment_traceback_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_segment_traceback_missing_segment="
	          << stats.score_prepass_state_machine_shadow_segment_traceback_missing_segment << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_segment_traceback_cpu_query_outside_segment="
	          << stats.score_prepass_state_machine_shadow_segment_traceback_cpu_query_outside_segment << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_segment_traceback_score_mismatches="
	          << stats.score_prepass_state_machine_shadow_segment_traceback_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_segment_traceback_endpoint_mismatches="
	          << stats.score_prepass_state_machine_shadow_segment_traceback_endpoint_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_segment_traceback_cigar_mismatches="
	          << stats.score_prepass_state_machine_shadow_segment_traceback_cigar_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_segment_traceback_seconds="
	          << stats.score_prepass_state_machine_shadow_segment_traceback_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_expanded_segment_traceback_requested="
	          << stats.score_prepass_state_machine_shadow_expanded_segment_traceback_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_expanded_segment_traceback_attempts="
	          << stats.score_prepass_state_machine_shadow_expanded_segment_traceback_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_expanded_segment_traceback_alignment_mismatches="
	          << stats.score_prepass_state_machine_shadow_expanded_segment_traceback_alignment_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_expanded_segment_traceback_triplex_mismatches="
	          << stats.score_prepass_state_machine_shadow_expanded_segment_traceback_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_expanded_segment_traceback_cpu_query_outside_expanded_segment="
	          << stats.score_prepass_state_machine_shadow_expanded_segment_traceback_cpu_query_outside_expanded_segment << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_expanded_segment_traceback_score_mismatches="
	          << stats.score_prepass_state_machine_shadow_expanded_segment_traceback_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_expanded_segment_traceback_endpoint_mismatches="
	          << stats.score_prepass_state_machine_shadow_expanded_segment_traceback_endpoint_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_expanded_segment_traceback_cigar_mismatches="
	          << stats.score_prepass_state_machine_shadow_expanded_segment_traceback_cigar_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_expanded_segment_traceback_required_max_len="
	          << stats.score_prepass_state_machine_shadow_expanded_segment_traceback_required_max_len << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_expanded_segment_traceback_required_over_gasal2_limit="
	          << stats.score_prepass_state_machine_shadow_expanded_segment_traceback_required_over_gasal2_limit << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_expanded_segment_traceback_seconds="
	          << stats.score_prepass_state_machine_shadow_expanded_segment_traceback_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_triplex_mismatches="
	          << stats.score_prepass_state_machine_shadow_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_requested="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_requested << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_active="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_active << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_scoreinfos="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_attempts="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_candidate_attempts="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_candidate_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_selected="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_selected << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_covered="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_covered << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_false_negative_scoreinfos="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_false_negative_scoreinfos << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_task="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_task << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_scoreinfo="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_scoreinfo << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_reason="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_reason << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_cpu_align_attempts="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_cpu_align_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_cpu_align_seconds="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_cpu_align_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_candidate_align_attempts="
	          << stats.score_prepass_state_machine_shadow_cpu_align_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_candidate_align_seconds="
	          << stats.score_prepass_state_machine_shadow_cpu_align_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_reference_align_attempts="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_cpu_align_attempts << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_candidate_coverage_reference_align_seconds="
	          << stats.score_prepass_state_machine_shadow_candidate_coverage_cpu_align_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_first_mismatch="
	          << stats.score_prepass_state_machine_shadow_first_mismatch_task << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_first_mismatch_source="
	          << stats.score_prepass_state_machine_shadow_first_mismatch_source << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_first_mismatch_kind="
	          << stats.score_prepass_state_machine_shadow_first_mismatch_kind << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_score_seconds="
	          << stats.score_prepass_state_machine_shadow_score_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_select_seconds="
	          << stats.score_prepass_state_machine_shadow_select_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_cpu_align_seconds="
	          << stats.score_prepass_state_machine_shadow_cpu_align_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_convert_seconds="
	          << stats.score_prepass_state_machine_shadow_convert_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_total_seconds="
	          << stats.score_prepass_state_machine_shadow_total_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_score_prepass_state_machine_shadow_fallbacks="
	          << stats.score_prepass_state_machine_shadow_fallbacks << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_substr_seconds="
	          << stats.realpath_extend_substr_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_align_seconds="
	          << stats.realpath_extend_align_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_convert_seconds="
	          << stats.realpath_extend_convert_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_sort_seconds="
	          << stats.realpath_extend_sort_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_extend_filter_seconds="
	          << stats.realpath_extend_filter_seconds << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_realpath_digest_authority="
	          << stats.realpath_digest_authority << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_decision="
	          << stats.decision << "\n";
	std::cerr << "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_error="
	          << stats.error << "\n";
}

static inline void fasim_print_broad_scoreinfo_consumer_shadow_stats(
	const FasimBroadScoreInfoConsumerShadowStats &stats)
{
	std::cerr << "benchmark.fasim_gasal2_broad_path_requested="
	          << stats.broad_path_requested << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_active="
	          << stats.broad_path_active << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_decision="
	          << stats.broad_path_decision << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_tasks="
	          << stats.broad_path_tasks << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_scoreinfo_groups="
	          << stats.broad_path_scoreinfo_groups << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_scoreinfo_seconds="
	          << stats.broad_path_scoreinfo_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_consumer_seconds="
	          << stats.broad_path_consumer_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_align_attempts="
	          << stats.broad_path_align_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_selected_attempts="
	          << stats.broad_path_selected_attempts << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_triplex_mismatches="
	          << stats.broad_path_triplex_mismatches << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_missing_triplexes="
	          << stats.broad_path_missing_triplexes << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_extra_triplexes="
	          << stats.broad_path_extra_triplexes << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_first_mismatch="
	          << stats.broad_path_first_mismatch << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_digest_match="
	          << stats.broad_path_digest_match << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_full_rows_equal="
	          << stats.broad_path_full_rows_equal << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_candidate_wall_seconds="
	          << stats.broad_path_candidate_wall_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_baseline_wall_seconds="
	          << stats.broad_path_baseline_wall_seconds << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_candidate_vs_baseline="
	          << stats.broad_path_candidate_vs_baseline << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_cpu_triplex_path="
	          << stats.broad_path_cpu_triplex_path << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_cpu_triplexes="
	          << stats.broad_path_cpu_triplexes << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_cpu_triplex_digest="
	          << stats.broad_path_cpu_triplex_digest << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_planner_descriptor_path="
	          << stats.broad_path_planner_descriptor_path << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_planner_descriptors="
	          << stats.broad_path_planner_descriptors << "\n";
	std::cerr << "benchmark.fasim_gasal2_broad_path_planner_descriptor_digest="
	          << stats.broad_path_planner_descriptor_digest << "\n";
}

static inline void fasim_print_legacy_score_gpu_shadow_stats(
	const FasimLegacyScoreGpuShadowStats &stats)
{
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_enabled="
	          << (stats.enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_replacement_enabled="
	          << (stats.replacement_enabled ? 1 : 0) << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_requests=" << stats.requests << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_batches=" << stats.batches << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_cells=" << stats.cells << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_replacement_used=" << stats.replacement_used << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_replacement_fallbacks=" << stats.replacement_fallbacks << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_mismatches=" << stats.mismatches << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_min_score_mismatches=" << stats.min_score_mismatches << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_gpu_gt_cpu=" << stats.gpu_gt_cpu << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_gpu_lt_cpu=" << stats.gpu_lt_cpu << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_max_abs_diff=" << stats.max_abs_diff << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_first_task=" << stats.first_task << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_first_rule=" << stats.first_rule << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_first_strand=" << stats.first_strand << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_first_para=" << stats.first_para << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_first_target_len=" << stats.first_target_len << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_first_cpu_score=" << stats.first_cpu_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_first_gpu_score=" << stats.first_gpu_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_first_cpu_min_score=" << stats.first_cpu_min_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_first_gpu_min_score=" << stats.first_gpu_min_score << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_wall_seconds=" << stats.wall_seconds << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_kernel_seconds=" << stats.kernel_seconds << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_h2d_seconds=" << stats.h2d_seconds << "\n";
	std::cerr << "benchmark.fasim_exact_column_legacy_score_gpu_shadow_d2h_seconds=" << stats.d2h_seconds << "\n";
}

static inline int fasim_min_score_from_full_score(int score)
{
	return static_cast<int>(static_cast<double>(score) * 0.8);
}

static inline int fasim_row_max_raw(const int *columnScores, size_t columnCount)
{
	int maxScore = 0;
	if (columnScores == NULL)
	{
		return maxScore;
	}
	for (size_t i = 0; i < columnCount; ++i)
	{
		if (columnScores[i] > maxScore)
		{
			maxScore = columnScores[i];
		}
	}
	return maxScore;
}

static inline int fasim_row_max_position_raw(const int *columnScores, size_t columnCount)
{
	int maxScore = 0;
	int maxPosition = -1;
	if (columnScores == NULL)
	{
		return maxPosition;
	}
	for (size_t i = 0; i < columnCount; ++i)
	{
		if (columnScores[i] > maxScore)
		{
			maxScore = columnScores[i];
			maxPosition = static_cast<int>(i);
		}
	}
	return maxPosition;
}

static inline int fasim_vector_row_max(const std::vector<int> &scores)
{
	return scores.empty() ? 0 : *std::max_element(scores.begin(), scores.end());
}

static inline int fasim_vector_row_max_position(const std::vector<int> &scores)
{
	if (scores.empty())
	{
		return -1;
	}
	return static_cast<int>(std::distance(scores.begin(),
	                                      std::max_element(scores.begin(), scores.end())));
}

static inline bool fasim_is_acgt_base(char base)
{
	switch (base)
	{
	case 'A':
	case 'C':
	case 'G':
	case 'T':
	case 'a':
	case 'c':
	case 'g':
	case 't':
		return true;
	default:
		return false;
	}
}

static inline size_t fasim_count_non_acgt_bases(const std::string &seq)
{
	size_t count = 0;
	for (size_t i = 0; i < seq.size(); ++i)
	{
		if (!fasim_is_acgt_base(seq[i]))
		{
			++count;
		}
	}
	return count;
}

static inline int fasim_row_max_with_legacy_byte_overflow(const int *columnScores,
                                                          size_t columnCount)
{
	int maxScore = 0;
	if (columnScores == NULL)
	{
		return maxScore;
	}
	const int sswByteBias = 4;
	for (size_t i = 0; i < columnCount; ++i)
	{
		if (columnScores[i] > maxScore)
		{
			maxScore = columnScores[i];
			if (maxScore + sswByteBias >= 255)
			{
				break;
			}
		}
	}
	return maxScore;
}

static inline void fasim_note_min_score_shadow_first(
	FasimExactColumnMinScoreShadowStats &stats,
	FasimMinScoreShadowSource source,
	uint64_t taskOrdinal,
	int rule,
	long strand,
	long para,
	size_t targetLen,
	int cpuScore,
	int cpuMinScore,
	int gpuRowScore,
	int gpuRowMinScore,
	int gpuLegacyRowScore,
	int gpuLegacyRowMinScore,
	int topkScore,
	int topkMinScore)
{
	if (stats.first_source != FASIM_MIN_SCORE_SHADOW_SOURCE_NONE)
	{
		return;
	}
	stats.first_source = source;
	stats.first_task_ordinal = taskOrdinal;
	stats.first_rule = rule;
	stats.first_strand = strand;
	stats.first_para = para;
	stats.first_target_len = targetLen;
	stats.first_cpu_score = cpuScore;
	stats.first_cpu_min_score = cpuMinScore;
	stats.first_gpu_row_score = gpuRowScore;
	stats.first_gpu_row_min_score = gpuRowMinScore;
	stats.first_gpu_legacy_row_score = gpuLegacyRowScore;
	stats.first_gpu_legacy_row_min_score = gpuLegacyRowMinScore;
	stats.first_topk_score = topkScore;
	stats.first_topk_min_score = topkMinScore;
}

static inline void fasim_note_min_score_shadow_source_first(
	FasimExactColumnMinScoreShadowStats &stats,
	FasimMinScoreShadowSource source,
	uint64_t taskOrdinal,
	int rule,
	long strand,
	long para,
	size_t targetLen,
	int cpuScore,
	int cpuMinScore,
	int candidateScore,
	int candidateMinScore)
{
	switch (source)
	{
	case FASIM_MIN_SCORE_SHADOW_SOURCE_GPU_ROW:
		if (stats.first_gpu_row_task != 0)
		{
			return;
		}
		stats.first_gpu_row_task = taskOrdinal;
		stats.first_gpu_row_rule = rule;
		stats.first_gpu_row_strand = strand;
		stats.first_gpu_row_para = para;
		stats.first_gpu_row_target_len = targetLen;
		stats.first_gpu_row_cpu_score = cpuScore;
		stats.first_gpu_row_cpu_min_score = cpuMinScore;
		stats.first_gpu_row_score_value = candidateScore;
		stats.first_gpu_row_min_score_value = candidateMinScore;
		return;
	case FASIM_MIN_SCORE_SHADOW_SOURCE_GPU_LEGACY_ROW:
		if (stats.first_gpu_legacy_row_task != 0)
		{
			return;
		}
		stats.first_gpu_legacy_row_task = taskOrdinal;
		stats.first_gpu_legacy_row_rule = rule;
		stats.first_gpu_legacy_row_strand = strand;
		stats.first_gpu_legacy_row_para = para;
		stats.first_gpu_legacy_row_target_len = targetLen;
		stats.first_gpu_legacy_row_cpu_score = cpuScore;
		stats.first_gpu_legacy_row_cpu_min_score = cpuMinScore;
		stats.first_gpu_legacy_row_score_value = candidateScore;
		stats.first_gpu_legacy_row_min_score_value = candidateMinScore;
		return;
	case FASIM_MIN_SCORE_SHADOW_SOURCE_TOPK:
		if (stats.first_topk_task != 0)
		{
			return;
		}
		stats.first_topk_task = taskOrdinal;
		stats.first_topk_rule = rule;
		stats.first_topk_strand = strand;
		stats.first_topk_para = para;
		stats.first_topk_target_len = targetLen;
		stats.first_topk_cpu_score = cpuScore;
		stats.first_topk_cpu_min_score = cpuMinScore;
		stats.first_topk_score_value = candidateScore;
		stats.first_topk_min_score_value = candidateMinScore;
		return;
	case FASIM_MIN_SCORE_SHADOW_SOURCE_NONE:
	default:
		return;
	}
}

static inline uint8_t fasim_encode_legacy_calc_score_base(unsigned char base)
{
	switch (base)
	{
	case 'A':
	case 'a':
		return 1;
	case 'C':
	case 'c':
		return 2;
	case 'G':
	case 'g':
		return 3;
	case 'T':
	case 't':
		return 4;
	case 'U':
	case 'u':
		return 5;
	default:
		return 16;
	}
}

static inline const uint8_t *fasim_prealign_encode_table()
{
	static const uint8_t table[256] = {
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 0, 4, 1, 4, 4, 4, 2, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 0, 4, 1, 4, 4, 4, 2, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
	};
	return table;
}

static inline const uint8_t *fasim_ssw_prealign_encode_table()
{
	static const uint8_t table[256] = {
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 0, 4, 1, 4, 4, 4, 2, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 3, 0, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 0, 4, 1, 4, 4, 4, 2, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 3, 0, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
		4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
	};
	return table;
}

static inline const uint8_t *fasim_legacy_calc_score_encode_table()
{
	static const uint8_t table[256] = {
		16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 1, 16, 2, 16, 16, 16, 3, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 16, 16, 16, 4, 5, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 1, 16, 2, 16, 16, 16, 3, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 16, 16, 16, 4, 5, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
		16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16, 16,
	};
	return table;
}

static inline int fasim_legacy_calc_score_matrix_value(uint8_t queryCode, uint8_t targetCode)
{
	if (queryCode == 16 || targetCode == 16)
	{
		return -1;
	}
	if (queryCode == targetCode)
	{
		return 5;
	}
	if ((queryCode == 1 && targetCode == 5) || (queryCode == 5 && targetCode == 1))
	{
		return 5;
	}
	return -4;
}

static inline uint8_t fasim_ssw_prealign_code(unsigned char base)
{
	switch (base)
	{
	case 'A':
	case 'a':
	case 'U':
	case 'u':
		return 0;
	case 'C':
	case 'c':
		return 1;
	case 'G':
	case 'g':
		return 2;
	case 'T':
	case 't':
		return 3;
	default:
		return 4;
	}
}

static inline void fasim_build_ssw_byte_query_profile(
	const std::string &query,
	std::vector<int16_t> &profile,
	int &segLen)
{
	const int lanes = 16;
	const int storageLanes = 32;
	const int alphabetSize = 5;
	const int bias = 4;
	segLen = static_cast<int>((query.size() + static_cast<size_t>(lanes - 1)) /
	                          static_cast<size_t>(lanes));
	profile.assign(static_cast<size_t>(alphabetSize) *
	               static_cast<size_t>(segLen) *
	               static_cast<size_t>(storageLanes),
	               static_cast<int16_t>(bias));
	for (int targetCode = 0; targetCode < alphabetSize; ++targetCode)
	{
		for (int lane = 0; lane < lanes; ++lane)
		{
			for (int seg = 0; seg < segLen; ++seg)
			{
				const size_t queryIndex =
					static_cast<size_t>(lane) * static_cast<size_t>(segLen) +
					static_cast<size_t>(seg);
				int score = 0;
				if (queryIndex < query.size())
				{
					const uint8_t queryCode =
						fasim_ssw_prealign_code(
							static_cast<unsigned char>(query[queryIndex]));
					if (queryCode < 4 &&
					    targetCode < 4 &&
					    static_cast<int>(queryCode) == targetCode)
					{
						score = 5;
					}
					else
					{
						score = -4;
					}
				}
				profile[(static_cast<size_t>(targetCode) *
				         static_cast<size_t>(segLen) +
				         static_cast<size_t>(seg)) *
				        static_cast<size_t>(storageLanes) +
				        static_cast<size_t>(lane)] =
					static_cast<int16_t>(score + bias);
			}
		}
	}
}

static inline void fasim_build_legacy_calc_score_query_profile(
	const std::string &query,
	std::vector<int16_t> &profile,
	int &segLen)
{
	const int lanes = 32;
	const int alphabetSize = 17;
	segLen = static_cast<int>((query.size() + static_cast<size_t>(lanes - 1)) /
	                          static_cast<size_t>(lanes));
	profile.assign(static_cast<size_t>(alphabetSize) *
	               static_cast<size_t>(segLen) *
	               static_cast<size_t>(lanes),
	               0);
	for (int code = 0; code < alphabetSize; ++code)
	{
		for (int seg = 0; seg < segLen; ++seg)
		{
			for (int lane = 0; lane < lanes; ++lane)
			{
				const size_t queryIndex =
					static_cast<size_t>(seg) + static_cast<size_t>(lane) * static_cast<size_t>(segLen);
				int score = 0;
				if (queryIndex < query.size())
				{
					const uint8_t queryCode =
						fasim_encode_legacy_calc_score_base(
							static_cast<unsigned char>(query[queryIndex]));
					score = fasim_legacy_calc_score_matrix_value(
						queryCode,
						static_cast<uint8_t>(code));
				}
				profile[(static_cast<size_t>(code) * static_cast<size_t>(segLen) +
				         static_cast<size_t>(seg)) *
				        static_cast<size_t>(lanes) +
				        static_cast<size_t>(lane)] =
					static_cast<int16_t>(score);
			}
		}
	}
}

static inline void fasim_note_legacy_score_gpu_shadow_first(
	FasimLegacyScoreGpuShadowStats &stats,
	uint64_t taskOrdinal,
	int rule,
	long strand,
	long para,
	size_t targetLen,
	int cpuScore,
	int gpuScore)
{
	if (stats.first_task != 0)
	{
		return;
	}
	stats.first_task = taskOrdinal;
	stats.first_rule = rule;
	stats.first_strand = strand;
	stats.first_para = para;
	stats.first_target_len = targetLen;
	stats.first_cpu_score = cpuScore;
	stats.first_gpu_score = gpuScore;
	stats.first_cpu_min_score = fasim_min_score_from_full_score(cpuScore);
	stats.first_gpu_min_score = fasim_min_score_from_full_score(gpuScore);
}

static inline uint64_t fasim_gpu_dp_column_tasks_per_window(const struct para &paraList)
{
	uint64_t taskCount = 0;
	if (paraList.strand >= 0)
	{
		if (paraList.rule == 0)
		{
			taskCount += 12;
		}
		else if (paraList.rule > 0 && paraList.rule < 7)
		{
			taskCount += 2;
		}
	}
	if (paraList.strand <= 0)
	{
		if (paraList.rule == 0)
		{
			taskCount += 36;
		}
		else
		{
			taskCount += 2;
		}
	}
	return taskCount;
}

static inline FasimGpuDpColumnAutoObservation
fasim_observe_gpu_dp_column_auto_workload(ifstream &dnaIn,
                                          const struct para &paraList,
                                          uint64_t queryLength)
{
	FasimGpuDpColumnAutoObservation observation;
	observation.cells = 0;
	observation.windows = 0;
	if (queryLength == 0)
	{
		return observation;
	}

	const uint64_t tasksPerWindow = fasim_gpu_dp_column_tasks_per_window(paraList);
	if (tasksPerWindow == 0)
	{
		return observation;
	}

	dnaIn.clear();
	dnaIn.seekg(0, ios::beg);
	string pendingHeader;
	FasimFastaRecord record;
	while (fasim_read_next_fasta_record(dnaIn, pendingHeader, record))
	{
		if (record.sequence.empty())
		{
			continue;
		}
		vector<string> dnaSequencesVec;
		vector<int> dnaSequencesStartPos;
		int cutNum = 0;
		cutSequence(record.sequence, dnaSequencesVec, dnaSequencesStartPos,
		            paraList.cutLength, paraList.overlapLength, cutNum);
		for (size_t i = 0; i < dnaSequencesVec.size(); ++i)
		{
			const string &seq1 = dnaSequencesVec[i];
			if (same_seq(seq1))
			{
				continue;
			}
			observation.windows =
				fasim_saturating_add_uint64(observation.windows, tasksPerWindow);
			const uint64_t taskCells =
				fasim_saturating_mul_uint64(
					fasim_saturating_mul_uint64(tasksPerWindow,
					                            static_cast<uint64_t>(seq1.size())),
					queryLength);
			observation.cells =
				fasim_saturating_add_uint64(observation.cells, taskCells);
		}
	}
	dnaIn.clear();
	dnaIn.seekg(0, ios::beg);
	return observation;
}

int main(int argc, char* const* argv)
{
	struct para paraList;
	vector<struct	lgInfo>	lgList;
	initEnv(argc, argv, paraList);
	char c_dd_tmp[10];
	char c_length_tmp[10];
	int c_loop_tmp = 0;
	int core_num;
	string c_tmp_dd;
	string c_tmp_length;
	sprintf(c_dd_tmp, "%d", paraList.cDistance);
	sprintf(c_length_tmp, "%d", paraList.cLength);
	for (c_loop_tmp = 0; c_loop_tmp < strlen(c_dd_tmp); c_loop_tmp++)
	{
		c_tmp_dd += c_dd_tmp[c_loop_tmp];
	}
	for (c_loop_tmp = 0; c_loop_tmp < strlen(c_length_tmp); c_loop_tmp++)
	{
		c_tmp_length += c_length_tmp[c_loop_tmp];
	}
	string lncName;
	string lncSeq;
//	string species;
//	string dnaChroTag;
	string fileName;
//	string dnaSeq;
	string resultDir;
//	string startGenomeTmp;
    vector<string> species;
    int thread_num = 0;
    vector<string> dnaChroTag;
    vector<long> startGenomeTmp;
    vector<string> dnaSeq;
	long startGenome;
	clock_t start, end;
	float cpu_time;
	start = clock();
	const bool phaseTimingEnabled = fasim_top5_gasal2_phase_timing_enabled_runtime();
	const bool minScoreShadowEnabled = fasim_exact_column_min_score_shadow_enabled_runtime();
	const bool streamingScoreInfoTwoContractRequested =
		fasim_long_query_streaming_scoreinfo_two_contract_bridge_runtime();
	const bool streamingScoreInfoGpuMinScoreRequested =
		fasim_long_query_streaming_scoreinfo_gpu_minscore_runtime() ||
		streamingScoreInfoTwoContractRequested;
	const bool legacyScoreGpuReplacementEnabled =
		fasim_exact_column_legacy_score_gpu_enabled_runtime();
	const bool legacyScoreGpuShadowEnabled =
		fasim_exact_column_legacy_score_gpu_shadow_enabled_runtime() ||
		legacyScoreGpuReplacementEnabled ||
		streamingScoreInfoGpuMinScoreRequested;
	const bool minScoreShadowDebugEnabled =
		fasim_exact_column_min_score_shadow_debug_enabled_runtime();
	const int minScoreShadowDebugLimit =
		fasim_env_int_or_default("FASIM_EXACT_COLUMN_MIN_SCORE_SHADOW_DEBUG_LIMIT", 3);
	int minScoreShadowDebugPrinted = 0;
	FasimTop5PhaseTimingStats phaseTiming;
	FasimExactColumnMinScoreShadowStats minScoreShadowStats;
	FasimLegacyScoreGpuShadowStats legacyScoreGpuShadowStats;
	FasimGasal2LongQueryShadowStats gasal2LongQuerySegmentedShadowStats;
	FasimGasal2LongQueryExactTileShadowStats gasal2LongQueryExactTileShadowStats;
	FasimLongQueryExactColumnScoreInfoShadowStats longQueryExactColumnScoreInfoShadowStats;
	FasimLongQueryStreamingScoreInfoShadowStats longQueryStreamingScoreInfoShadowStats;
	FasimBroadScoreInfoConsumerShadowStats broadScoreInfoConsumerShadowStats;
	legacyScoreGpuShadowStats.enabled = legacyScoreGpuShadowEnabled;
	legacyScoreGpuShadowStats.replacement_enabled = legacyScoreGpuReplacementEnabled;
    if(paraList.doFastSim==true)
    cout<<"Searching triplexes using Fasim"<<endl;
    else
    cout<<"Searching triplexes using Sim"<<endl;
    core_num = paraList.corenum;

	{
		FasimScopedSeconds scoped(phaseTimingEnabled, &phaseTiming.read_rna_seconds);
		lncSeq = readRna(paraList.file2path, lncName);
	}
	fasim_prepare_gasal2_long_query_segmented_shadow_stats(
		lncSeq,
		&gasal2LongQuerySegmentedShadowStats);
	fasim_prepare_gasal2_long_query_exact_tile_shadow_stats(
		lncSeq,
		&gasal2LongQueryExactTileShadowStats);
	fasim_prepare_long_query_exact_column_scoreinfo_shadow_stats(
		lncSeq,
		&longQueryExactColumnScoreInfoShadowStats);
	fasim_prepare_long_query_streaming_scoreinfo_shadow_stats(
		lncSeq,
		&longQueryStreamingScoreInfoShadowStats);
	if (fasim_gasal2_broad_scoreinfo_consumer_shadow_runtime() ||
	    fasim_gasal2_broad_replacement_consumer_shadow_runtime())
	{
		broadScoreInfoConsumerShadowStats.broad_path_requested = 1;
		broadScoreInfoConsumerShadowStats.broad_path_decision = "not_implemented";
		if (fasim_gasal2_broad_scoreinfo_consumer_export_cpu_triplex_runtime())
		{
			broadScoreInfoConsumerShadowStats.broad_path_decision =
				"cpu_triplex_export_only";
		}
		if (fasim_gasal2_broad_scoreinfo_consumer_planner_runtime())
		{
			broadScoreInfoConsumerShadowStats.broad_path_decision =
				"planner_requested";
		}
		if (fasim_gasal2_broad_replacement_consumer_shadow_runtime())
		{
			broadScoreInfoConsumerShadowStats.broad_path_decision =
				"replacement_consumer_shadow_requested";
		}
	}
	fileName = fasim_strip_fasta_extension(fasim_basename(paraList.file1path));
	lncName.erase(remove(lncName.begin(), lncName.end(), '\r'), lncName.end());
	lncName.erase(remove(lncName.begin(), lncName.end(), '\n'), lncName.end());
	resultDir = paraList.outpath;

	const FasimOutputMode outputMode = fasim_output_mode_runtime();
	std::vector<int> exactColumnGuardCudaDevices;
	fasim_cuda_devices_runtime(exactColumnGuardCudaDevices);
	if (fasim_exact_column_multigpu_guard_failed(exactColumnGuardCudaDevices))
	{
		return 2;
	}
	if (outputMode == FASIM_OUTPUT_TFOSORTED || outputMode == FASIM_OUTPUT_LITE)
	{
		const bool verbose = fasim_verbose_enabled_runtime();

		ifstream dnaIn(paraList.file1path.c_str());
		if (!dnaIn.is_open())
		{
			cerr << "failed to open DNA fasta: " << paraList.file1path << endl;
			return 1;
		}

		struct StreamTask
		{
			StreamTask() :
				taskIndex(0),
				recordStartGenome(1),
				dnaStartPos(0),
				strand(0),
				Para(0),
				rule(0),
				fullScore(0),
				minScore(0),
				minScoreReady(false)
			{
			}
			uint64_t taskIndex;
			std::shared_ptr<const std::string> srcSeq;
			std::string seq2;
			std::string chr;
			long recordStartGenome;
			long dnaStartPos;
			long strand;
			long Para;
			int rule;
			int fullScore;
			int minScore;
			bool minScoreReady;
		};

			ofstream outFile;
			ofstream outLiteFile;
			ofstream cigarArchiveProbeFile;
			FasimCompactArchiveProbeWriter compactArchiveProbeWriter;
			ofstream broadCpuTriplexFile;
		ofstream broadPlannerDescriptorFile;
		string outFilePath;
			string outLiteFilePath;
			string cigarArchiveProbePath;
			string compactArchiveProbePath;
		string broadCpuTriplexPath;
		string broadPlannerDescriptorPath;
		string outSpecies;
			bool outOpened = false;
			bool cigarArchiveProbeOpened = false;
			bool compactArchiveProbeOpened = false;
		bool broadCpuTriplexOpened = false;
		bool broadPlannerDescriptorOpened = false;
		uint64_t broadCpuTriplexDigest = 1469598103934665603ULL;
		uint64_t broadPlannerDescriptorDigest = 1469598103934665603ULL;
		std::mutex outMutex;
			const bool writeFull = outputMode == FASIM_OUTPUT_TFOSORTED;
			const bool writeLite = (outputMode == FASIM_OUTPUT_LITE) || fasim_write_tfosorted_lite_enabled_runtime();
			const bool writeCigarArchiveProbe =
				fasim_tfosorted_cigar_archive_probe_runtime();
			const bool writeCompactArchiveProbe =
				fasim_tfosorted_compact_archive_probe_runtime();
		const int outputTopkLite = fasim_output_topk_lite_runtime();
		const bool collectTopkLite = writeLite && outputTopkLite > 0;
		const bool broadCpuTriplexExportEnabled =
			fasim_gasal2_broad_scoreinfo_consumer_shadow_runtime() &&
			fasim_gasal2_broad_scoreinfo_consumer_export_cpu_triplex_runtime();
		const bool broadPlannerEnabled =
			fasim_gasal2_broad_scoreinfo_consumer_shadow_runtime() &&
			fasim_gasal2_broad_scoreinfo_consumer_planner_runtime();
			const bool broadReplacementConsumerEnabled =
				broadPlannerEnabled &&
				fasim_gasal2_broad_replacement_consumer_shadow_runtime();
			const bool attemptConsumerShadowEnabled =
				fasim_gasal2_attempt_consumer_shadow_runtime();
			const bool emissionOnlyConsumerShadowEnabled =
				fasim_gasal2_emission_only_consumer_shadow_enabled_runtime();
			std::vector<FasimLiteRow> topkLiteRows;
			std::map<uint64_t, std::vector<triplex> > broadReplacementTriplexesByTask;
			std::map<uint64_t, std::vector<triplex> > attemptConsumerTriplexesByTask;
			std::map<uint64_t, std::vector<triplex> > emissionOnlyTriplexesByTask;
			uint64_t attemptConsumerShadowTaskMismatches = 0;
			uint64_t attemptConsumerShadowMissingTriplexes = 0;
			uint64_t attemptConsumerShadowExtraTriplexes = 0;
			std::string attemptConsumerShadowFirstMismatch = "none";
			uint64_t emissionOnlyShadowTaskMismatches = 0;
			uint64_t emissionOnlyShadowMissingTriplexes = 0;
			uint64_t emissionOnlyShadowExtraTriplexes = 0;
			std::string emissionOnlyShadowFirstMismatch = "none";

			auto ensure_output_opened = [&](const string &speciesValue)
			{
				FasimScopedSeconds scoped(phaseTimingEnabled, &phaseTiming.output_open_seconds);
				if (outOpened)
				{
					return;
				}
			outSpecies = speciesValue.empty() ? string("unknown") : speciesValue;
			outFilePath = resultDir + "/" + outSpecies + "-" + lncName + "-" + fileName + "-TFOsorted";
			outLiteFilePath = outFilePath + ".lite";
			if (writeFull)
			{
				outFile.open(outFilePath.c_str(), ios::trunc);
				if (!outFile.is_open())
				{
					cerr << "failed to open output file: " << outFilePath << endl;
					abort();
				}
				fasim_write_tfosorted_header(outFile);
			}
				if (writeLite)
				{
					outLiteFile.open(outLiteFilePath.c_str(), ios::trunc);
				if (!outLiteFile.is_open())
				{
					cerr << "failed to open output file: " << outLiteFilePath << endl;
					abort();
				}
					fasim_write_tfosorted_lite_header(outLiteFile);
				}
				if (writeCigarArchiveProbe)
				{
					cigarArchiveProbePath =
						outFilePath + ".cigar-archive.tsv";
					cigarArchiveProbeFile.open(
						cigarArchiveProbePath.c_str(), ios::trunc);
					if (!cigarArchiveProbeFile.is_open())
					{
						cerr << "failed to open CIGAR archive probe: "
						     << cigarArchiveProbePath << endl;
						abort();
					}
					fasim_write_tfosorted_cigar_archive_probe_header(
						cigarArchiveProbeFile);
					cigarArchiveProbeOpened = true;
				}
				if (writeCompactArchiveProbe)
				{
					compactArchiveProbePath =
						outFilePath + ".compact-archive.tfoa";
					compactArchiveProbeWriter.open(compactArchiveProbePath);
					compactArchiveProbeOpened = true;
				}
				if (broadCpuTriplexExportEnabled)
			{
				broadCpuTriplexPath = outFilePath + ".broad_cpu_triplex.tsv";
				broadCpuTriplexFile.open(broadCpuTriplexPath.c_str(), ios::trunc);
				if (!broadCpuTriplexFile.is_open())
				{
					cerr << "failed to open broad CPU triplex export: "
					     << broadCpuTriplexPath << endl;
					abort();
				}
				const std::string header =
					"task_index\tlegacy_order_index\tselected_align_attempt_index\t"
					"scoreinfo_identity\temission_reason\tchr\tgenome_start\tgenome_end\t"
					"query_start\tquery_end\ttarget_start\ttarget_end\tscore\t"
					"identity\ttri_score\tnt\trule\tstrand\tpara\tdna_start_pos\n";
				broadCpuTriplexFile << header;
				broadCpuTriplexDigest =
					fasim_fnv1a_update(broadCpuTriplexDigest, header);
				broadScoreInfoConsumerShadowStats.broad_path_cpu_triplex_path =
					broadCpuTriplexPath;
				broadCpuTriplexOpened = true;
			}
			if (broadPlannerEnabled)
			{
				broadPlannerDescriptorPath =
					outFilePath + ".broad_scoreinfo_attempt_plan.tsv";
				broadPlannerDescriptorFile.open(
					broadPlannerDescriptorPath.c_str(),
					ios::trunc);
				if (!broadPlannerDescriptorFile.is_open())
				{
					cerr << "failed to open broad scoreInfo attempt plan: "
					     << broadPlannerDescriptorPath << endl;
					abort();
				}
				const std::string header =
					"task_index\tscoreinfo_index\tcandidate_window_order\t"
					"min_score\tprealign_score\tprealign_position\t"
					"target_start\ttarget_length\tcutlength\tlegacy_order_index\t"
					"query_start\tquery_end\ttarget_end_required_for_fallback\t"
					"rule\tstrand\tpara\tdna_start_pos\n";
				broadPlannerDescriptorFile << header;
				broadPlannerDescriptorDigest =
					fasim_fnv1a_update(broadPlannerDescriptorDigest, header);
				broadScoreInfoConsumerShadowStats
					.broad_path_planner_descriptor_path =
					broadPlannerDescriptorPath;
				broadPlannerDescriptorOpened = true;
			}
			outOpened = true;
		};

		auto emit_lite_row = [&](const FasimLiteRow &row)
		{
			if (!writeLite)
			{
				return;
			}
			if (collectTopkLite)
			{
				topkLiteRows.push_back(row);
			}
			else
			{
				outLiteFile << row.text << "\n";
			}
			if (phaseTimingEnabled)
			{
				++phaseTiming.gasal2_emit_rows_lite;
			}
		};

		FasimGpuDpColumnAutoObservation gpuDpColumnAutoObservation;
		gpuDpColumnAutoObservation.cells = 0;
		gpuDpColumnAutoObservation.windows = 0;
		const bool gpuDpColumnAutoRequested = fasim_gpu_dp_column_auto_requested_runtime();
		const uint64_t gpuDpColumnAutoMinCells = fasim_gpu_dp_column_auto_min_cells_runtime();
		const uint64_t gpuDpColumnAutoMinWindows = fasim_gpu_dp_column_auto_min_windows_runtime();
			bool gpuDpColumnAutoEffective = false;
			if (paraList.doFastSim && gpuDpColumnAutoRequested)
			{
				FasimScopedSeconds scoped(phaseTimingEnabled, &phaseTiming.auto_observe_seconds);
				gpuDpColumnAutoObservation =
					fasim_observe_gpu_dp_column_auto_workload(dnaIn,
					                                          paraList,
				                                          static_cast<uint64_t>(lncSeq.size()));
			gpuDpColumnAutoEffective =
				gpuDpColumnAutoObservation.cells >= gpuDpColumnAutoMinCells &&
				gpuDpColumnAutoObservation.windows >= gpuDpColumnAutoMinWindows &&
				prealign_cuda_is_built();
		}

		bool useCudaBatch = false;
		std::vector<int> cudaDevices;
		std::vector<PreAlignCudaQueryHandle> cudaQueries;
		std::vector<int16_t> queryProfile;
		PreAlignCudaQueryHandle legacyScoreCudaQuery;
		bool legacyScoreCudaQueryReady = false;
		PreAlignCudaQueryHandle streamingScoreInfoLegacyByteCudaQuery;
		bool streamingScoreInfoLegacyByteCudaQueryReady = false;
		PreAlignCudaQueryHandle streamingScoreInfoGpuMinScoreCudaQuery;
		bool streamingScoreInfoGpuMinScoreCudaQueryReady = false;
		int cachedSegLen = 0;
		const bool streamingScoreInfoShadowRequested =
			longQueryStreamingScoreInfoShadowStats.requested != 0;
		const bool streamingScoreInfoLegacyByteRequested =
			streamingScoreInfoShadowRequested &&
			(fasim_long_query_streaming_scoreinfo_legacy_byte_runtime() ||
			 streamingScoreInfoTwoContractRequested);
		if (paraList.doFastSim &&
			    (fasim_prealign_cuda_enabled_runtime() ||
			     gpuDpColumnAutoEffective ||
			     streamingScoreInfoShadowRequested) &&
			    prealign_cuda_is_built())
			{
				FasimScopedSeconds scoped(phaseTimingEnabled, &phaseTiming.cuda_query_init_seconds);
				fasim_cuda_devices_runtime(cudaDevices);
				fasim_build_query_profile(lncSeq, 5, 4, queryProfile, cachedSegLen);

			std::vector<int> okDevices;
			std::vector<PreAlignCudaQueryHandle> okQueries;
			for (size_t i = 0; i < cudaDevices.size(); ++i)
			{
				const int device = cudaDevices[i];
				string cudaError;
				if (!prealign_cuda_init(device, &cudaError))
				{
					continue;
				}
				PreAlignCudaQueryHandle handle;
				if (!prealign_cuda_prepare_query(&handle, queryProfile.data(), 5, cachedSegLen, static_cast<int>(lncSeq.size()), &cudaError))
				{
					continue;
				}
				okDevices.push_back(device);
				okQueries.push_back(handle);
			}
			cudaDevices.swap(okDevices);
			cudaQueries.swap(okQueries);
			useCudaBatch =
				!cudaQueries.empty() &&
				(fasim_prealign_cuda_enabled_runtime() || gpuDpColumnAutoEffective);
			if (legacyScoreGpuShadowEnabled && !cudaQueries.empty())
			{
				std::vector<int16_t> legacyQueryProfile;
				int legacySegLen = 0;
				fasim_build_legacy_calc_score_query_profile(lncSeq,
				                                            legacyQueryProfile,
				                                            legacySegLen);
				string legacyCudaError;
				if (prealign_cuda_prepare_query(&legacyScoreCudaQuery,
				                                legacyQueryProfile.data(),
				                                17,
				                                legacySegLen,
				                                static_cast<int>(lncSeq.size()),
				                                &legacyCudaError))
					{
						legacyScoreCudaQueryReady = true;
					}
				else
					{
						cerr << "[fasim.legacy_score_gpu_shadow] prepare error="
						     << legacyCudaError << endl;
				}
			}
			if (streamingScoreInfoLegacyByteRequested && !cudaQueries.empty())
			{
				std::vector<int16_t> streamingLegacyByteProfile;
				int streamingLegacyByteSegLen = 0;
				fasim_build_ssw_byte_query_profile(lncSeq,
				                                   streamingLegacyByteProfile,
				                                   streamingLegacyByteSegLen);
				string streamingLegacyByteError;
				if (prealign_cuda_prepare_query(
					    &streamingScoreInfoLegacyByteCudaQuery,
					    streamingLegacyByteProfile.data(),
					    5,
					    streamingLegacyByteSegLen,
					    static_cast<int>(lncSeq.size()),
					    &streamingLegacyByteError))
				{
					streamingScoreInfoLegacyByteCudaQueryReady = true;
				}
				else
				{
					cerr << "[fasim.long_query_streaming_scoreinfo_shadow] "
					     << "legacy byte prepare error="
				     << streamingLegacyByteError << endl;
				}
			}
			if (streamingScoreInfoGpuMinScoreRequested && !cudaQueries.empty())
			{
				std::vector<int16_t> streamingGpuMinScoreProfile;
				int streamingGpuMinScoreSegLen = 0;
				fasim_build_legacy_calc_score_query_profile(
					lncSeq,
					streamingGpuMinScoreProfile,
					streamingGpuMinScoreSegLen);
				string streamingGpuMinScoreError;
				if (prealign_cuda_prepare_query(
					    &streamingScoreInfoGpuMinScoreCudaQuery,
					    streamingGpuMinScoreProfile.data(),
					    17,
					    streamingGpuMinScoreSegLen,
					    static_cast<int>(lncSeq.size()),
					    &streamingGpuMinScoreError))
				{
					streamingScoreInfoGpuMinScoreCudaQueryReady = true;
				}
				else
				{
					cerr << "[fasim.long_query_streaming_scoreinfo_shadow] "
					     << "GPU minScore prepare error="
					     << streamingGpuMinScoreError << endl;
				}
			}
		}

			const bool gasal2QueryLengthSupported =
				fasim_gasal2_query_length_supported_runtime(lncSeq.size());
			if (phaseTimingEnabled)
			{
				phaseTiming.gasal2_query_preflight_supported = gasal2QueryLengthSupported;
				phaseTiming.gasal2_query_preflight_query_len =
					static_cast<uint64_t>(lncSeq.size());
				phaseTiming.gasal2_query_preflight_max_query_len =
					static_cast<uint64_t>(fasim_gasal2_max_query_len_runtime());
			}

			const bool gasal2LongtargetBatch =
				paraList.doFastSim &&
				gasal2QueryLengthSupported &&
				fasim_gasal2_enabled() &&
				fasim_gasal2_is_built() &&
				fasim_gasal2_longtarget_bridge_enabled() &&
			!fasim_gasal2_cpu_traceback_all_enabled_runtime();
		const bool gasal2LongtargetCpuTracebackBatch =
			gasal2LongtargetBatch &&
			fasim_gasal2_cpu_traceback_enabled_runtime();
		const bool streamingScoreInfoShadowCudaReady =
			streamingScoreInfoShadowRequested && !cudaQueries.empty();

		const int maxTasksPerGpu = fasim_env_int_or_default("FASIM_PREALIGN_CUDA_MAX_TASKS", 4096);
		int maxTasksTotal = useCudaBatch ? (maxTasksPerGpu * static_cast<int>(cudaQueries.size())) : 1;
		if (!useCudaBatch && streamingScoreInfoShadowCudaReady)
		{
			maxTasksTotal =
				fasim_env_int_or_default(
					"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_MAX_TASKS",
					4096);
		}
		else if (!useCudaBatch && gasal2LongtargetBatch)
		{
			maxTasksTotal = fasim_env_int_or_default("FASIM_ALIGN_GASAL2_TASK_BATCH", 4096);
		}
		if (!useCudaBatch &&
		    !gasal2LongtargetBatch &&
		    paraList.doFastSim &&
		    !gasal2QueryLengthSupported &&
		    fasim_gasal2_long_query_segmented_shadow_requested_runtime() &&
		    fasim_gasal2_long_query_segmented_score_prepass_shadow_runtime())
		{
			const int segmentedShadowMaxTasks =
				fasim_gasal2_long_query_segmented_max_tasks_runtime();
			if (segmentedShadowMaxTasks > 0)
			{
				maxTasksTotal = segmentedShadowMaxTasks;
			}
		}
		if (maxTasksTotal <= 0)
		{
			maxTasksTotal = 1;
		}
		const int extendThreadCount = fasim_extend_threads_runtime(paraList.corenum);
				int topK = fasim_env_int_or_default("FASIM_PREALIGN_CUDA_TOPK", 64);
				if (topK > 256)
				{
					topK = 256;
				}
				if (topK <= 0)
				{
					topK = 64;
				}

		const bool debugCuda = getenv("FASIM_DEBUG_CUDA_PREALIGN") != NULL &&
		                       getenv("FASIM_DEBUG_CUDA_PREALIGN")[0] != '\0' &&
		                       getenv("FASIM_DEBUG_CUDA_PREALIGN")[0] != '0';
			const bool exactColumnBatchRequested = fasim_exact_column_extend_batch_enabled_runtime();
			const bool exactColumnBatchValidate = fasim_exact_column_extend_batch_validate_enabled_runtime();
			const bool exactColumnBatchDebugColumns = fasim_exact_column_extend_batch_debug_columns_runtime();
			const bool exactScoreInfoGpuRequested = fasim_exact_column_scoreinfo_gpu_enabled_runtime();
			phaseTiming.exact_scoreinfo_gpu_enabled = exactScoreInfoGpuRequested;
			const bool singlePassTopNRequested =
				fasim_top5_gasal2_single_pass_topn_enabled_runtime();
			phaseTiming.single_pass_topn_enabled = singlePassTopNRequested;
			const int gasal2ScoreInfoPruneMaxPerTask =
				fasim_top5_gasal2_scoreinfo_prune_max_per_task_runtime();
			const bool exactScoreInfoGpuPrunedOutputRequested =
				exactScoreInfoGpuRequested &&
				fasim_exact_column_scoreinfo_gpu_pruned_output_enabled_runtime() &&
				gasal2ScoreInfoPruneMaxPerTask > 0;
			phaseTiming.exact_scoreinfo_gpu_pruned_output_enabled =
				exactScoreInfoGpuPrunedOutputRequested;
			const bool exactScoreInfoGpuColumnPrunedOutputRequested =
				exactScoreInfoGpuPrunedOutputRequested &&
				fasim_exact_column_scoreinfo_gpu_column_pruned_output_enabled_runtime();
			phaseTiming.exact_scoreinfo_gpu_column_pruned_output_enabled =
				exactScoreInfoGpuColumnPrunedOutputRequested;

		StripedSmithWaterman::Aligner aligner;
		StripedSmithWaterman::Filter filter;
		StripedSmithWaterman::Alignment alignment;
		std::vector<struct StripedSmithWaterman::scoreInfo> finalScoreInfo;
		finalScoreInfo.reserve(static_cast<size_t>(topK));

		std::vector<triplex> taskTriplexes;
		taskTriplexes.reserve(64);

		std::vector<StreamTask> tasks;
		uint64_t nextStreamTaskIndex = 0;
		std::vector<uint8_t> encodedTargets;
		std::vector<uint8_t> legacyEncodedTargets;
		int currentTargetLength = -1;

		auto build_scoreinfo_from_candidates = [](
			std::vector<struct StripedSmithWaterman::scoreInfo> &candidates,
			std::vector<struct StripedSmithWaterman::scoreInfo> &outScoreInfo)
		{
			outScoreInfo.clear();
			std::sort(candidates.begin(),
			          candidates.end(),
			          [](const StripedSmithWaterman::scoreInfo &a,
			             const StripedSmithWaterman::scoreInfo &b)
			          {
				          if (a.position != b.position)
				          {
					          return a.position < b.position;
				          }
				          return a.score > b.score;
			          });

			const int suppressBp = 5;
			size_t groupBegin = 0;
			while (groupBegin < candidates.size())
			{
				size_t groupEnd = groupBegin + 1;
				while (groupEnd < candidates.size())
				{
					const int positionDelta =
						candidates[groupEnd].position - candidates[groupEnd - 1].position;
					if (positionDelta <= 0 || positionDelta >= suppressBp)
					{
						break;
					}
					++groupEnd;
				}
				size_t best = groupBegin;
				for (size_t i = groupBegin + 1; i < groupEnd; ++i)
				{
					if (candidates[i].score > candidates[best].score)
					{
						best = i;
					}
				}
				outScoreInfo.push_back(candidates[best]);
				groupBegin = groupEnd;
			}
		};

			auto build_scoreinfo_from_column_scores = [&](
				const std::vector<int> &columnScores,
				int minScore,
				std::vector<struct StripedSmithWaterman::scoreInfo> &outScoreInfo)
			{
			std::vector<struct StripedSmithWaterman::scoreInfo> candidates;
			candidates.reserve(columnScores.size());
			for (size_t i = 0; i < columnScores.size(); ++i)
			{
				if (columnScores[i] > minScore)
				{
					candidates.push_back(
						StripedSmithWaterman::scoreInfo(columnScores[i],
						                                static_cast<int>(i)));
				}
			}
				build_scoreinfo_from_candidates(candidates, outScoreInfo);
			};

			auto build_scoreinfo_from_column_scores_row = [](
				const int *columnScores,
				size_t columnCount,
				int minScore,
				std::vector<struct StripedSmithWaterman::scoreInfo> &outScoreInfo)
			{
				outScoreInfo.clear();
				if (columnScores == NULL || columnCount == 0)
				{
					return;
				}

				const int suppressBp = 5;
				const int sswByteBias = 4;
				int maxScore = 0;
				bool haveGroup = false;
				int previousCandidatePosition = -1;
				StripedSmithWaterman::scoreInfo bestInGroup;

				for (size_t i = 0; i < columnCount; ++i)
				{
					const int score = columnScores[i];
					if (score > maxScore)
					{
						maxScore = score;
						if (maxScore + sswByteBias >= 255)
						{
							break;
						}
					}
					if (score <= minScore)
					{
						continue;
					}

					const int position = static_cast<int>(i);
					if (!haveGroup)
					{
						bestInGroup = StripedSmithWaterman::scoreInfo(score, position);
						previousCandidatePosition = position;
						haveGroup = true;
						continue;
					}

					const int positionDelta = position - previousCandidatePosition;
					if (positionDelta <= 0 || positionDelta >= suppressBp)
					{
						outScoreInfo.push_back(bestInGroup);
						bestInGroup = StripedSmithWaterman::scoreInfo(score, position);
					}
					else if (score > bestInGroup.score)
					{
						bestInGroup = StripedSmithWaterman::scoreInfo(score, position);
					}
					previousCandidatePosition = position;
				}

				if (haveGroup)
				{
					outScoreInfo.push_back(bestInGroup);
				}
			};

			auto apply_legacy_prealign_byte_overflow = [](
				std::vector<int> &columnScores)
			{
			const int sswByteBias = 4;
			int maxScore = 0;
			for (size_t i = 0; i < columnScores.size(); ++i)
			{
				if (columnScores[i] > maxScore)
				{
					maxScore = columnScores[i];
					if (maxScore + sswByteBias >= 255)
					{
						std::fill(columnScores.begin() + static_cast<std::vector<int>::difference_type>(i),
						          columnScores.end(),
						          0);
						break;
					}
				}
			}
		};

			auto scoreinfo_equal = [](
				const std::vector<struct StripedSmithWaterman::scoreInfo> &a,
				const std::vector<struct StripedSmithWaterman::scoreInfo> &b)
			{
			if (a.size() != b.size())
			{
				return false;
			}
			for (size_t i = 0; i < a.size(); ++i)
			{
				if (a[i].score != b[i].score || a[i].position != b[i].position)
				{
					return false;
				}
				}
				return true;
			};

			auto prune_scoreinfo_for_gasal2_top5 = [](
				const std::vector<struct StripedSmithWaterman::scoreInfo> &input,
				int maxPerTask,
				std::vector<struct StripedSmithWaterman::scoreInfo> &output)
			{
				output.clear();
				if (maxPerTask <= 0 ||
				    input.size() <= static_cast<size_t>(maxPerTask))
				{
					output = input;
					return;
				}

				const size_t limit = static_cast<size_t>(maxPerTask);
				const std::string pruneMode =
					fasim_gasal2_long_query_segmented_scoreinfo_prune_mode_runtime();
				std::vector<size_t> scoreOrder(input.size());
				for (size_t i = 0; i < scoreOrder.size(); ++i)
				{
					scoreOrder[i] = i;
				}
				std::sort(scoreOrder.begin(),
				          scoreOrder.end(),
				                  [&](size_t lhs, size_t rhs)
				                  {
					                  const StripedSmithWaterman::scoreInfo &a = input[lhs];
					                  const StripedSmithWaterman::scoreInfo &b = input[rhs];
					                  if (a.score != b.score)
					                  {
						                  return a.score > b.score;
					                  }
					                  return a.position < b.position;
				                  });
				if (pruneMode == "score")
				{
					scoreOrder.resize(limit);
					std::sort(scoreOrder.begin(), scoreOrder.end());
					output.reserve(scoreOrder.size());
					for (size_t i = 0; i < scoreOrder.size(); ++i)
					{
						output.push_back(input[scoreOrder[i]]);
					}
					return;
				}

				std::vector<char> selected(input.size(), 0);
				std::vector<size_t> selectedIndexes;
				selectedIndexes.reserve(limit);
				auto add_index = [&](size_t idx)
				{
					if (idx >= input.size() || selected[idx] || selectedIndexes.size() >= limit)
					{
						return false;
					}
					selected[idx] = 1;
					selectedIndexes.push_back(idx);
					return true;
				};

				const size_t scoreQuota = std::max<size_t>(1, limit / 2);
				for (size_t i = 0; i < scoreOrder.size() && i < scoreQuota; ++i)
				{
					add_index(scoreOrder[i]);
				}

				std::vector<size_t> positionOrder(input.size());
				for (size_t i = 0; i < positionOrder.size(); ++i)
				{
					positionOrder[i] = i;
				}
				std::sort(positionOrder.begin(),
				          positionOrder.end(),
				          [&](size_t lhs, size_t rhs)
				          {
					          const StripedSmithWaterman::scoreInfo &a = input[lhs];
					          const StripedSmithWaterman::scoreInfo &b = input[rhs];
					          if (a.position != b.position)
					          {
						          return a.position < b.position;
					          }
					          return a.score > b.score;
				          });

				if (pruneMode == "score_position_edges")
				{
					size_t left = 0;
					size_t right = positionOrder.empty() ? 0 : positionOrder.size() - 1;
					bool takeLeft = true;
					while (selectedIndexes.size() < limit && left <= right && !positionOrder.empty())
					{
						if (takeLeft)
						{
							add_index(positionOrder[left]);
							++left;
						}
						else
						{
							add_index(positionOrder[right]);
							if (right == 0)
							{
								break;
							}
							--right;
						}
						takeLeft = !takeLeft;
					}
				}
				else
				{
					const size_t spreadSlots = limit - selectedIndexes.size();
					if (spreadSlots > 0 && !positionOrder.empty())
					{
						for (size_t slot = 0;
						     slot < spreadSlots && selectedIndexes.size() < limit;
						     ++slot)
						{
							const size_t denom = spreadSlots > 1 ? spreadSlots - 1 : 1;
							const size_t target =
								spreadSlots > 1 ?
									(slot * (positionOrder.size() - 1) + denom / 2) / denom :
									positionOrder.size() / 2;
							for (size_t radius = 0; radius < positionOrder.size(); ++radius)
							{
								bool added = false;
								if (target >= radius)
								{
									added = add_index(positionOrder[target - radius]);
								}
								if (!added && target + radius < positionOrder.size())
								{
									added = add_index(positionOrder[target + radius]);
								}
								if (added)
								{
									break;
								}
							}
						}
					}
				}

				for (size_t i = 0; i < scoreOrder.size() && selectedIndexes.size() < limit; ++i)
				{
					add_index(scoreOrder[i]);
				}

				std::sort(selectedIndexes.begin(), selectedIndexes.end());
				output.reserve(selectedIndexes.size());
				for (size_t i = 0; i < selectedIndexes.size(); ++i)
				{
					output.push_back(input[selectedIndexes[i]]);
				}
			};

			auto build_scoreinfo_from_gpu_peaks = [&](const PreAlignCudaPeak *taskPeaks,
			                                          int minScore,
			                                          std::vector<struct StripedSmithWaterman::scoreInfo> &outScoreInfo)
		{
			std::vector<struct StripedSmithWaterman::scoreInfo> candidates;
			candidates.reserve(static_cast<size_t>(topK));
			for (int k = 0; k < topK; ++k)
			{
				const PreAlignCudaPeak &p = taskPeaks[static_cast<size_t>(k)];
				if (p.position < 0 || p.score <= minScore)
				{
					continue;
				}
				candidates.push_back(StripedSmithWaterman::scoreInfo(p.score, p.position));
			}
			build_scoreinfo_from_candidates(candidates, outScoreInfo);
		};

			auto task_min_score = [&](StreamTask &task) -> int
			{
				if (!task.minScoreReady)
			{
				FasimScopedSeconds minScoreScoped(phaseTimingEnabled,
				                                  &phaseTiming.exact_min_score_seconds);
				task.fullScore = calc_score_once(lncSeq,
				                                 task.seq2,
				                                 task.dnaStartPos,
				                                 task.rule);
				task.minScore = fasim_min_score_from_full_score(task.fullScore);
				task.minScoreReady = true;
			}
				return task.minScore;
			};

			auto broad_triplex_probe_key = [](const triplex &atr) -> std::string
			{
				std::ostringstream out;
				out << atr.stari << ':' << atr.endi << ':'
				    << atr.starj << ':' << atr.endj << ':'
				    << atr.reverse << ':' << atr.strand << ':'
				    << atr.rule << ':' << atr.nt << ':'
				    << static_cast<int>(atr.score * 1000.0f) << ':'
				    << static_cast<int>(atr.identity * 1000.0f) << ':'
				    << static_cast<int>(atr.tri_score * 1000.0f);
				return out.str();
			};

			auto record_broad_replacement_consumer_mismatch =
				[&](const StreamTask &task,
				    const std::vector<triplex> &shadowTriplexes,
				    const std::vector<triplex> &legacyTriplexes)
			{
				if (shadowTriplexes.size() < legacyTriplexes.size())
				{
					broadScoreInfoConsumerShadowStats.broad_path_missing_triplexes +=
						static_cast<uint64_t>(legacyTriplexes.size() - shadowTriplexes.size());
				}
				else if (shadowTriplexes.size() > legacyTriplexes.size())
				{
					broadScoreInfoConsumerShadowStats.broad_path_extra_triplexes +=
						static_cast<uint64_t>(shadowTriplexes.size() - legacyTriplexes.size());
				}
				const size_t minCount =
					std::min(shadowTriplexes.size(), legacyTriplexes.size());
				size_t diffIndex = 0;
				while (diffIndex < minCount &&
				       broad_triplex_probe_key(shadowTriplexes[diffIndex]) ==
				           broad_triplex_probe_key(legacyTriplexes[diffIndex]))
				{
					++diffIndex;
				}
				if (diffIndex < minCount)
				{
					++broadScoreInfoConsumerShadowStats.broad_path_triplex_mismatches;
				}
				if (broadScoreInfoConsumerShadowStats.broad_path_first_mismatch == "none")
				{
					std::ostringstream first;
					first << "task:" << task.taskIndex
					      << ":index:" << diffIndex
					      << ":shadow_count:" << shadowTriplexes.size()
					      << ":legacy_count:" << legacyTriplexes.size();
					if (diffIndex < shadowTriplexes.size())
					{
						first << ":shadow:" <<
							broad_triplex_probe_key(shadowTriplexes[diffIndex]);
					}
					if (diffIndex < legacyTriplexes.size())
					{
						first << ":legacy:" <<
							broad_triplex_probe_key(legacyTriplexes[diffIndex]);
					}
					broadScoreInfoConsumerShadowStats.broad_path_first_mismatch =
						first.str();
				}
			};

			auto record_broad_scoreinfo_attempt_plan =
				[&](const StreamTask &task,
				    const std::vector<struct StripedSmithWaterman::scoreInfo> &scoreInfos)
		{
			if (!broadPlannerDescriptorOpened || scoreInfos.empty())
			{
				return;
			}
			const std::chrono::steady_clock::time_point planStart =
				std::chrono::steady_clock::now();
			const int minScore =
				const_cast<StreamTask &>(task).minScoreReady ?
					task.minScore :
					task_min_score(const_cast<StreamTask &>(task));
			std::vector<FasimGasal2Attempt> attempts;
			attempts.reserve(scoreInfos.size() * 5);
			uint64_t localAttemptIndex = 0;
			for (size_t scoreInfoIndex = 0;
			     scoreInfoIndex < scoreInfos.size();
			     ++scoreInfoIndex)
			{
				const struct StripedSmithWaterman::scoreInfo &scoreInfo =
					scoreInfos[scoreInfoIndex];
				float identity = 0.6f;
				int attemptOffset = 0;
				while (identity <= 1.0001f)
				{
					int cutlength =
						static_cast<int>(scoreInfo.score + 24) /
							(9 * identity - 4) +
						1;
					cutlength =
						scoreInfo.position - cutlength + 1 > 0 ?
							cutlength :
							scoreInfo.position + 1;
					const int start = scoreInfo.position - cutlength + 1;
					FasimGasal2Attempt attempt;
					attempt.scoreinfo_index = static_cast<int>(scoreInfoIndex);
					attempt.cutlength = cutlength;
					attempt.start = start;
					attempt.prealign_score = scoreInfo.score;
					attempt.target_end_required_for_fallback = cutlength - 1;
					attempt.nt_min_length = paraList.ntMin;
					attempt.set_target_view(
						&task.seq2,
						static_cast<size_t>(std::max(0, start)),
						static_cast<size_t>(std::max(0, cutlength)));
					attempts.push_back(attempt);

					std::ostringstream row;
					row << task.taskIndex << '\t'
					    << scoreInfoIndex << '\t'
					    << attemptOffset << '\t'
					    << minScore << '\t'
					    << scoreInfo.score << '\t'
					    << scoreInfo.position << '\t'
					    << start << '\t'
					    << cutlength << '\t'
					    << cutlength << '\t'
					    << localAttemptIndex << '\t'
					    << "0\t"
					    << (lncSeq.empty() ? 0 : static_cast<int>(lncSeq.size()) - 1) << '\t'
					    << (cutlength - 1) << '\t'
					    << task.rule << '\t'
					    << task.strand << '\t'
					    << task.Para << '\t'
					    << task.dnaStartPos << '\n';
					const std::string rowText = row.str();
					broadPlannerDescriptorFile << rowText;
					broadPlannerDescriptorDigest =
						fasim_fnv1a_update(broadPlannerDescriptorDigest, rowText);
					++localAttemptIndex;
					++broadScoreInfoConsumerShadowStats
						.broad_path_planner_descriptors;
					identity += 0.1f;
					++attemptOffset;
				}
			}
			broadScoreInfoConsumerShadowStats.broad_path_tasks += 1;
			broadScoreInfoConsumerShadowStats.broad_path_scoreinfo_groups +=
				static_cast<uint64_t>(scoreInfos.size());
				broadScoreInfoConsumerShadowStats.broad_path_align_attempts +=
					static_cast<uint64_t>(attempts.size());
				if (!attempts.empty())
				{
					std::vector<FasimGasal2SelectedAlignment> selected;
				std::string selectError;
				const bool selectedOk =
					fasim_gasal2_select_attempts(lncSeq,
					                             attempts,
					                             &selected,
					                             &selectError);
				if (selectedOk)
				{
					broadScoreInfoConsumerShadowStats
						.broad_path_selected_attempts +=
						static_cast<uint64_t>(selected.size());
				}
			}
				broadScoreInfoConsumerShadowStats.broad_path_scoreinfo_seconds +=
					fasim_seconds_since(planStart);
				if (!broadReplacementConsumerEnabled)
				{
					broadScoreInfoConsumerShadowStats.broad_path_decision =
						"planner_descriptors_only";
				}
			};

			auto write_task_triplexes = [&](const StreamTask &task)
			{
			if (broadReplacementConsumerEnabled &&
			    broadScoreInfoConsumerShadowStats.broad_path_active != 0)
			{
				std::map<uint64_t, std::vector<triplex> >::iterator shadowIt =
					broadReplacementTriplexesByTask.find(task.taskIndex);
				if (shadowIt == broadReplacementTriplexesByTask.end())
				{
					broadScoreInfoConsumerShadowStats.broad_path_missing_triplexes +=
						static_cast<uint64_t>(taskTriplexes.size());
					if (broadScoreInfoConsumerShadowStats.broad_path_first_mismatch ==
					    "none")
					{
						std::ostringstream first;
						first << "task:" << task.taskIndex
						      << ":missing_shadow"
						      << ":legacy_count:" << taskTriplexes.size();
						broadScoreInfoConsumerShadowStats.broad_path_first_mismatch =
							first.str();
					}
				}
				else
				{
					bool equal = shadowIt->second.size() == taskTriplexes.size();
					if (equal)
					{
						for (size_t i = 0; i < taskTriplexes.size(); ++i)
						{
							if (broad_triplex_probe_key(shadowIt->second[i]) !=
							    broad_triplex_probe_key(taskTriplexes[i]))
							{
								equal = false;
								break;
							}
						}
					}
					if (!equal)
					{
						record_broad_replacement_consumer_mismatch(
							task,
							shadowIt->second,
							taskTriplexes);
					}
					broadReplacementTriplexesByTask.erase(shadowIt);
				}
			}
			if (attemptConsumerShadowEnabled)
			{
				std::map<uint64_t, std::vector<triplex> >::iterator shadowIt =
					attemptConsumerTriplexesByTask.find(task.taskIndex);
				if (shadowIt == attemptConsumerTriplexesByTask.end())
				{
					attemptConsumerShadowMissingTriplexes +=
						static_cast<uint64_t>(taskTriplexes.size());
					if (attemptConsumerShadowFirstMismatch == "none")
					{
						std::ostringstream first;
						first << "task:" << task.taskIndex
						      << ":missing_shadow"
						      << ":legacy_count:" << taskTriplexes.size();
						attemptConsumerShadowFirstMismatch = first.str();
					}
				}
				else
				{
					bool equal = shadowIt->second.size() == taskTriplexes.size();
					size_t diffIndex = 0;
					const size_t minCount =
						std::min(shadowIt->second.size(), taskTriplexes.size());
					if (equal)
					{
						while (diffIndex < minCount)
						{
							if (broad_triplex_probe_key(shadowIt->second[diffIndex]) !=
							    broad_triplex_probe_key(taskTriplexes[diffIndex]))
							{
								equal = false;
								break;
							}
							++diffIndex;
						}
					}
					if (!equal)
					{
						if (shadowIt->second.size() < taskTriplexes.size())
						{
							attemptConsumerShadowMissingTriplexes +=
								static_cast<uint64_t>(
									taskTriplexes.size() - shadowIt->second.size());
						}
						else if (shadowIt->second.size() > taskTriplexes.size())
						{
							attemptConsumerShadowExtraTriplexes +=
								static_cast<uint64_t>(
									shadowIt->second.size() - taskTriplexes.size());
						}
						if (diffIndex < minCount)
						{
							++attemptConsumerShadowTaskMismatches;
						}
						if (attemptConsumerShadowFirstMismatch == "none")
						{
							std::ostringstream first;
							first << "task:" << task.taskIndex
							      << ":index:" << diffIndex
							      << ":shadow_count:" << shadowIt->second.size()
							      << ":legacy_count:" << taskTriplexes.size();
							if (diffIndex < shadowIt->second.size())
							{
								first << ":shadow:"
								      << broad_triplex_probe_key(
									      shadowIt->second[diffIndex]);
							}
							if (diffIndex < taskTriplexes.size())
							{
								first << ":legacy:"
								      << broad_triplex_probe_key(taskTriplexes[diffIndex]);
							}
							attemptConsumerShadowFirstMismatch = first.str();
						}
					}
					attemptConsumerTriplexesByTask.erase(shadowIt);
				}
			}
			if (emissionOnlyConsumerShadowEnabled)
			{
				std::map<uint64_t, std::vector<triplex> >::iterator shadowIt =
					emissionOnlyTriplexesByTask.find(task.taskIndex);
				if (shadowIt == emissionOnlyTriplexesByTask.end())
				{
					emissionOnlyShadowMissingTriplexes +=
						static_cast<uint64_t>(taskTriplexes.size());
					if (emissionOnlyShadowFirstMismatch == "none")
					{
						std::ostringstream first;
						first << "task:" << task.taskIndex
						      << ":missing_shadow"
						      << ":legacy_count:" << taskTriplexes.size();
						emissionOnlyShadowFirstMismatch = first.str();
					}
				}
				else
				{
					bool equal = shadowIt->second.size() == taskTriplexes.size();
					size_t diffIndex = 0;
					const size_t minCount =
						std::min(shadowIt->second.size(), taskTriplexes.size());
					if (equal)
					{
						while (diffIndex < minCount)
						{
							if (broad_triplex_probe_key(shadowIt->second[diffIndex]) !=
							    broad_triplex_probe_key(taskTriplexes[diffIndex]))
							{
								equal = false;
								break;
							}
							++diffIndex;
						}
					}
					if (!equal)
					{
						if (shadowIt->second.size() < taskTriplexes.size())
						{
							emissionOnlyShadowMissingTriplexes +=
								static_cast<uint64_t>(
									taskTriplexes.size() - shadowIt->second.size());
						}
						else if (shadowIt->second.size() > taskTriplexes.size())
						{
							emissionOnlyShadowExtraTriplexes +=
								static_cast<uint64_t>(
									shadowIt->second.size() - taskTriplexes.size());
						}
						if (diffIndex < minCount)
						{
							++emissionOnlyShadowTaskMismatches;
						}
						if (emissionOnlyShadowFirstMismatch == "none")
						{
							std::ostringstream first;
							first << "task:" << task.taskIndex
							      << ":index:" << diffIndex
							      << ":shadow_count:" << shadowIt->second.size()
							      << ":legacy_count:" << taskTriplexes.size();
							if (diffIndex < shadowIt->second.size())
							{
								first << ":shadow:"
								      << broad_triplex_probe_key(
									      shadowIt->second[diffIndex]);
							}
							if (diffIndex < taskTriplexes.size())
							{
								first << ":legacy:"
								      << broad_triplex_probe_key(taskTriplexes[diffIndex]);
							}
							emissionOnlyShadowFirstMismatch = first.str();
						}
					}
					emissionOnlyTriplexesByTask.erase(shadowIt);
				}
			}
			if (broadCpuTriplexOpened)
			{
				for (size_t i = 0; i < taskTriplexes.size(); ++i)
				{
					triplex atr = taskTriplexes[i];
					if (atr.chr.empty())
					{
						atr.chr = task.chr;
					}
					if (atr.genomestart == 0)
					{
						atr.genomestart = atr.starj + task.recordStartGenome - 1;
					}
					if (atr.genomeend == 0)
					{
						atr.genomeend = atr.endj + task.recordStartGenome - 1;
					}
					std::ostringstream row;
					row << task.taskIndex << '\t'
					    << i << '\t'
					    << "-1\t"
					    << "task:" << task.taskIndex << ":row:" << i << '\t'
					    << "legacy_output\t"
					    << atr.chr << '\t'
					    << atr.genomestart << '\t'
					    << atr.genomeend << '\t'
					    << atr.stari << '\t'
					    << atr.endi << '\t'
					    << atr.starj << '\t'
					    << atr.endj << '\t'
					    << atr.score << '\t'
					    << atr.identity << '\t'
					    << atr.tri_score << '\t'
					    << atr.nt << '\t'
					    << atr.rule << '\t'
					    << atr.strand << '\t'
					    << task.Para << '\t'
					    << task.dnaStartPos << '\n';
					const std::string rowText = row.str();
					broadCpuTriplexFile << rowText;
					broadCpuTriplexDigest =
						fasim_fnv1a_update(broadCpuTriplexDigest, rowText);
					++broadScoreInfoConsumerShadowStats.broad_path_cpu_triplexes;
				}
			}
			for (size_t i = 0; i < taskTriplexes.size(); ++i)
				{
					triplex atr = taskTriplexes[i];
				if (atr.chr.empty())
				{
					atr.chr = task.chr;
				}
				if (atr.genomestart == 0)
				{
					atr.genomestart = atr.starj + task.recordStartGenome - 1;
				}
				if (atr.genomeend == 0)
				{
					atr.genomeend = atr.endj + task.recordStartGenome - 1;
				}

				if (atr.score < paraList.scoreMin ||
				    atr.identity < paraList.minIdentity ||
				    atr.tri_score < paraList.minStability ||
				    atr.nt < paraList.cLength)
				{
					if (phaseTimingEnabled)
					{
						++phaseTiming.gasal2_emit_candidates;
						if (atr.score < paraList.scoreMin)
						{
							++phaseTiming.gasal2_emit_filtered_score;
						}
						if (atr.identity < paraList.minIdentity)
						{
							++phaseTiming.gasal2_emit_filtered_identity;
						}
						if (atr.tri_score < paraList.minStability)
						{
							++phaseTiming.gasal2_emit_filtered_stability;
						}
						if (atr.nt < paraList.cLength)
						{
							++phaseTiming.gasal2_emit_filtered_nt;
						}
					}
					continue;
				}
				if (phaseTimingEnabled)
				{
					++phaseTiming.gasal2_emit_candidates;
					const int querySpan = std::abs(atr.endi - atr.stari) + 1;
					const int refSpan = std::abs(atr.endj - atr.starj) + 1;
					if (querySpan < paraList.cLength)
					{
						++phaseTiming.gasal2_nt_shadow_query_span_false_negative;
					}
					if (refSpan < paraList.cLength)
					{
						++phaseTiming.gasal2_nt_shadow_ref_span_false_negative;
					}
					if (std::min(querySpan, refSpan) < paraList.cLength)
					{
						++phaseTiming.gasal2_nt_shadow_min_span_false_negative;
					}
					if (std::max(querySpan, refSpan) < paraList.cLength)
					{
						++phaseTiming.gasal2_nt_shadow_max_span_false_negative;
					}
					if (querySpan + refSpan < paraList.cLength)
					{
						++phaseTiming.gasal2_nt_shadow_sum_span_false_negative;
					}
				}

				const int motif = 0;
				const int middle = static_cast<int>((atr.stari + atr.endi) / 2);
				const int center = middle;

					if (writeLite)
					{
						FasimScopedSeconds scoped(phaseTimingEnabled,
						                          &phaseTiming.output_write_seconds);
						emit_lite_row(fasim_make_lite_row(atr.chr,
						                                  atr.genomestart,
						                                  atr.genomeend,
						                                  atr));
				}

						if (writeFull)
						{
							FasimScopedSeconds scoped(phaseTimingEnabled,
							                          &phaseTiming.output_write_seconds);
						if (atr.starj < atr.endj)
						{
						outFile << atr.stari << "\t" << atr.endi << "\t" << atr.starj << "\t" << atr.endj << "\t"
						        << "R\t" << atr.chr << "\t" << atr.genomestart << "\t" << atr.genomeend << "\t"
						        << atr.tri_score << "\t" << atr.identity << "\t" << getStrand(atr.reverse, atr.strand) << "\t"
						        << atr.rule << "\t" << atr.score << "\t" << atr.nt << "\t"
						        << motif << "\t" << middle << "\t" << center << "\t"
						        << atr.stri_align << "\t" << atr.strj_align << "\n";
					}
					else
					{
						outFile << atr.stari << "\t" << atr.endi << "\t" << atr.starj << "\t" << atr.endj << "\t"
						        << "L\t" << atr.chr << "\t" << atr.genomestart << "\t" << atr.genomeend << "\t"
						        << atr.tri_score << "\t" << atr.identity << "\t" << getStrand(atr.reverse, atr.strand) << "\t"
						        << atr.rule << "\t" << atr.score << "\t" << atr.nt << "\t"
						        << motif << "\t" << middle << "\t" << center << "\t"
						        << atr.stri_align << "\t" << atr.strj_align << "\n";
					}
						if (phaseTimingEnabled)
						{
							++phaseTiming.gasal2_emit_rows_full;
						}
					}
					if (writeCigarArchiveProbe)
					{
						if (atr.cigar_probe.empty())
						{
							cerr << "CIGAR archive probe missing CIGAR for emitted row"
							     << endl;
							abort();
						}
						FasimScopedSeconds scoped(phaseTimingEnabled,
						                          &phaseTiming.output_write_seconds);
						cigarArchiveProbeFile << atr.stari << "\t"
						                      << atr.endi << "\t"
						                      << atr.starj << "\t"
						                      << atr.endj << "\t"
						                      << (atr.starj < atr.endj ? "R" : "L")
						                      << "\t" << atr.chr << "\t"
						                      << atr.genomestart << "\t"
						                      << atr.genomeend << "\t"
						                      << atr.tri_score << "\t"
						                      << atr.identity << "\t"
						                      << getStrand(atr.reverse, atr.strand)
						                      << "\t" << atr.rule << "\t"
						                      << atr.score << "\t"
						                      << atr.nt << "\t"
						                      << motif << "\t"
						                      << middle << "\t"
						                      << center << "\t"
						                      << atr.cigar_probe << "\n";
					}
					if (writeCompactArchiveProbe)
					{
						FasimScopedSeconds scoped(phaseTimingEnabled,
						                          &phaseTiming.output_write_seconds);
						compactArchiveProbeWriter.write_row(atr,
						                                    motif,
						                                    middle,
						                                    center);
					}
				}
				taskTriplexes.clear();
			};

		auto finalize_attempt_consumer_shadow = [&]()
		{
			if (!attemptConsumerShadowEnabled)
			{
				return;
			}
			if (!attemptConsumerTriplexesByTask.empty())
			{
				for (std::map<uint64_t, std::vector<triplex> >::const_iterator it =
				         attemptConsumerTriplexesByTask.begin();
				     it != attemptConsumerTriplexesByTask.end();
				     ++it)
				{
					attemptConsumerShadowExtraTriplexes +=
						static_cast<uint64_t>(it->second.size());
					if (attemptConsumerShadowFirstMismatch == "none")
					{
						std::ostringstream first;
						first << "task:" << it->first
						      << ":unconsumed_shadow"
						      << ":shadow_count:" << it->second.size();
						attemptConsumerShadowFirstMismatch = first.str();
					}
				}
				attemptConsumerTriplexesByTask.clear();
			}
			const bool attemptConsumerClean =
				attemptConsumerShadowTaskMismatches == 0 &&
				attemptConsumerShadowMissingTriplexes == 0 &&
				attemptConsumerShadowExtraTriplexes == 0 &&
				attemptConsumerShadowFirstMismatch == "none";
			fasim_gasal2_record_attempt_consumer_shadow_comparison(
				attemptConsumerShadowTaskMismatches,
				attemptConsumerShadowMissingTriplexes,
				attemptConsumerShadowExtraTriplexes,
				attemptConsumerShadowFirstMismatch.c_str(),
				attemptConsumerClean,
				attemptConsumerClean,
				attemptConsumerClean ?
					"attempt_consumer_shadow_active" :
					"attempt_consumer_shadow_no_go");
		};

		auto finalize_emission_only_consumer_shadow = [&]()
		{
			if (!emissionOnlyConsumerShadowEnabled)
			{
				return;
			}
			if (!emissionOnlyTriplexesByTask.empty())
			{
				for (std::map<uint64_t, std::vector<triplex> >::const_iterator it =
				         emissionOnlyTriplexesByTask.begin();
				     it != emissionOnlyTriplexesByTask.end();
				     ++it)
				{
					emissionOnlyShadowExtraTriplexes +=
						static_cast<uint64_t>(it->second.size());
					if (emissionOnlyShadowFirstMismatch == "none")
					{
						std::ostringstream first;
						first << "task:" << it->first
						      << ":unconsumed_shadow"
						      << ":shadow_count:" << it->second.size();
						emissionOnlyShadowFirstMismatch = first.str();
					}
				}
				emissionOnlyTriplexesByTask.clear();
			}
			const bool emissionOnlyClean =
				emissionOnlyShadowTaskMismatches == 0 &&
				emissionOnlyShadowMissingTriplexes == 0 &&
				emissionOnlyShadowExtraTriplexes == 0 &&
				emissionOnlyShadowFirstMismatch == "none";
			fasim_gasal2_record_emission_only_consumer_shadow_comparison(
				emissionOnlyShadowTaskMismatches,
				emissionOnlyShadowMissingTriplexes,
				emissionOnlyShadowExtraTriplexes,
				emissionOnlyShadowFirstMismatch.c_str(),
				emissionOnlyClean,
				emissionOnlyClean,
				emissionOnlyClean ?
					"emission_only_consumer_shadow_active" :
					"emission_only_consumer_shadow_mismatch_no_go");
		};

		auto triplex_probe_key = [](const triplex &atr) -> std::string
		{
			std::ostringstream out;
			out << atr.stari << ':' << atr.endi << ':'
			    << atr.starj << ':' << atr.endj << ':'
			    << atr.reverse << ':' << atr.strand << ':'
			    << atr.rule << ':' << atr.nt << ':'
			    << static_cast<int>(atr.score * 1000.0f) << ':'
			    << static_cast<int>(atr.identity * 1000.0f) << ':'
			    << static_cast<int>(atr.tri_score * 1000.0f);
			return out.str();
		};

		auto triplex_probe_equal = [&](const std::vector<triplex> &a,
		                              const std::vector<triplex> &b) -> bool
		{
			if (a.size() != b.size())
			{
				return false;
			}
			for (size_t i = 0; i < a.size(); ++i)
			{
				if (triplex_probe_key(a[i]) != triplex_probe_key(b[i]))
				{
					return false;
				}
			}
			return true;
		};

			auto record_triplex_probe_first_mismatch =
				[&](size_t taskIndex,
				    const std::vector<triplex> &replayTriplexes,
			    const std::vector<triplex> &legacyTriplexes,
			    const std::vector<std::string> *replayProvenance)
		{
			if (longQueryStreamingScoreInfoShadowStats
			        .realpath_extend_flush_segmented_replay_probe_first_mismatch_task >= 0)
			{
				return;
			}
			size_t diffIndex = 0;
			const size_t minCount =
				std::min(replayTriplexes.size(), legacyTriplexes.size());
			while (diffIndex < minCount &&
			       triplex_probe_key(replayTriplexes[diffIndex]) ==
			           triplex_probe_key(legacyTriplexes[diffIndex]))
			{
				++diffIndex;
			}
			longQueryStreamingScoreInfoShadowStats
				.realpath_extend_flush_segmented_replay_probe_first_mismatch_task =
					static_cast<int64_t>(taskIndex);
			longQueryStreamingScoreInfoShadowStats
				.realpath_extend_flush_segmented_replay_probe_first_mismatch_diff_index =
					static_cast<int64_t>(diffIndex);
			longQueryStreamingScoreInfoShadowStats
				.realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_count =
					static_cast<int64_t>(replayTriplexes.size());
			longQueryStreamingScoreInfoShadowStats
				.realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_count =
					static_cast<int64_t>(legacyTriplexes.size());
			if (diffIndex < replayTriplexes.size())
			{
				longQueryStreamingScoreInfoShadowStats
					.realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_key =
						triplex_probe_key(replayTriplexes[diffIndex]);
				if (replayProvenance != NULL &&
				    diffIndex < replayProvenance->size())
				{
					longQueryStreamingScoreInfoShadowStats
						.realpath_extend_flush_segmented_replay_probe_first_mismatch_replay_provenance =
							(*replayProvenance)[diffIndex];
				}
			}
			if (diffIndex < legacyTriplexes.size())
			{
				longQueryStreamingScoreInfoShadowStats
					.realpath_extend_flush_segmented_replay_probe_first_mismatch_legacy_key =
						triplex_probe_key(legacyTriplexes[diffIndex]);
				}
			};

				auto record_selected_only_triplex_mismatch =
					[&](size_t taskIndex,
					    const std::vector<triplex> &selectedTriplexes,
					    const std::vector<triplex> &legacyTriplexes,
					    const std::vector<std::string> *selectedProvenance)
			{
				std::string mismatchKind;
				if (selectedTriplexes.empty() && !legacyTriplexes.empty())
				{
					++longQueryStreamingScoreInfoShadowStats
						.realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_empty;
					mismatchKind = "selected_empty";
				}
				else if (!selectedTriplexes.empty() && legacyTriplexes.empty())
				{
					++longQueryStreamingScoreInfoShadowStats
						.realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_legacy_empty;
					mismatchKind = "legacy_empty";
				}
				else if (selectedTriplexes.size() < legacyTriplexes.size())
				{
					++longQueryStreamingScoreInfoShadowStats
						.realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_less;
					mismatchKind = "selected_less";
				}
				else if (selectedTriplexes.size() > legacyTriplexes.size())
				{
					++longQueryStreamingScoreInfoShadowStats
						.realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_selected_more;
					mismatchKind = "selected_more";
				}
				else
				{
					++longQueryStreamingScoreInfoShadowStats
						.realpath_extend_flush_segmented_selected_only_replay_probe_mismatch_same_count_diff;
					mismatchKind = "same_count_diff";
				}
				if (longQueryStreamingScoreInfoShadowStats
				        .realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task >= 0)
				{
					return;
				}
				size_t diffIndex = 0;
				const size_t minCount =
					std::min(selectedTriplexes.size(), legacyTriplexes.size());
				while (diffIndex < minCount &&
				       triplex_probe_key(selectedTriplexes[diffIndex]) ==
				           triplex_probe_key(legacyTriplexes[diffIndex]))
				{
					++diffIndex;
				}
				longQueryStreamingScoreInfoShadowStats
					.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_task =
						static_cast<int64_t>(taskIndex);
				longQueryStreamingScoreInfoShadowStats
					.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_kind =
						mismatchKind;
				longQueryStreamingScoreInfoShadowStats
					.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_diff_index =
						static_cast<int64_t>(diffIndex);
				longQueryStreamingScoreInfoShadowStats
					.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_count =
						static_cast<int64_t>(selectedTriplexes.size());
				longQueryStreamingScoreInfoShadowStats
					.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_count =
						static_cast<int64_t>(legacyTriplexes.size());
				if (diffIndex < selectedTriplexes.size())
				{
					longQueryStreamingScoreInfoShadowStats
						.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_key =
							triplex_probe_key(selectedTriplexes[diffIndex]);
					if (selectedProvenance != NULL &&
					    diffIndex < selectedProvenance->size())
					{
						longQueryStreamingScoreInfoShadowStats
							.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_selected_provenance =
								(*selectedProvenance)[diffIndex];
					}
				}
				if (diffIndex < legacyTriplexes.size())
				{
					longQueryStreamingScoreInfoShadowStats
						.realpath_extend_flush_segmented_selected_only_replay_probe_first_mismatch_legacy_key =
							triplex_probe_key(legacyTriplexes[diffIndex]);
					}
				};

				auto record_grouped_selected_triplex_mismatch =
					[&](size_t taskIndex,
					    const std::vector<triplex> &selectedTriplexes,
					    const std::vector<triplex> &legacyTriplexes,
					    const std::vector<std::string> *selectedProvenance,
					    const std::vector<std::string> *legacyProvenance)
				{
					std::string mismatchKind;
					if (selectedTriplexes.empty() && !legacyTriplexes.empty())
					{
						++longQueryStreamingScoreInfoShadowStats
							.realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_empty;
						mismatchKind = "selected_empty";
					}
					else if (!selectedTriplexes.empty() && legacyTriplexes.empty())
					{
						++longQueryStreamingScoreInfoShadowStats
							.realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_legacy_empty;
						mismatchKind = "legacy_empty";
					}
					else if (selectedTriplexes.size() < legacyTriplexes.size())
					{
						++longQueryStreamingScoreInfoShadowStats
							.realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_less;
						mismatchKind = "selected_less";
					}
					else if (selectedTriplexes.size() > legacyTriplexes.size())
					{
						++longQueryStreamingScoreInfoShadowStats
							.realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_selected_more;
						mismatchKind = "selected_more";
					}
					else
					{
						++longQueryStreamingScoreInfoShadowStats
							.realpath_extend_flush_segmented_grouped_selected_replay_probe_mismatch_same_count_diff;
						mismatchKind = "same_count_diff";
					}
					if (longQueryStreamingScoreInfoShadowStats
					        .realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_task >= 0)
					{
						return;
					}
					size_t diffIndex = 0;
					const size_t minCount =
						std::min(selectedTriplexes.size(), legacyTriplexes.size());
					while (diffIndex < minCount &&
					       triplex_probe_key(selectedTriplexes[diffIndex]) ==
					           triplex_probe_key(legacyTriplexes[diffIndex]))
					{
						++diffIndex;
					}
					longQueryStreamingScoreInfoShadowStats
						.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_task =
							static_cast<int64_t>(taskIndex);
					longQueryStreamingScoreInfoShadowStats
						.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_kind =
							mismatchKind;
					longQueryStreamingScoreInfoShadowStats
						.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_diff_index =
							static_cast<int64_t>(diffIndex);
					longQueryStreamingScoreInfoShadowStats
						.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_count =
							static_cast<int64_t>(selectedTriplexes.size());
					longQueryStreamingScoreInfoShadowStats
						.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_count =
							static_cast<int64_t>(legacyTriplexes.size());
					if (diffIndex < selectedTriplexes.size())
					{
						longQueryStreamingScoreInfoShadowStats
							.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_key =
								triplex_probe_key(selectedTriplexes[diffIndex]);
						if (selectedProvenance != NULL &&
						    diffIndex < selectedProvenance->size())
						{
							longQueryStreamingScoreInfoShadowStats
								.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_selected_provenance =
									(*selectedProvenance)[diffIndex];
						}
					}
					if (diffIndex < legacyTriplexes.size())
					{
						longQueryStreamingScoreInfoShadowStats
							.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_key =
								triplex_probe_key(legacyTriplexes[diffIndex]);
						if (legacyProvenance != NULL &&
						    diffIndex < legacyProvenance->size())
						{
							longQueryStreamingScoreInfoShadowStats
								.realpath_extend_flush_segmented_grouped_selected_replay_probe_first_mismatch_legacy_provenance =
									(*legacyProvenance)[diffIndex];
						}
					}
				};

				auto gasal2_batched_cpu_traceback_enabled = [&]() -> bool
			{
			return gasal2LongtargetCpuTracebackBatch && !useCudaBatch;
		};

		auto gasal2_batched_traceback_enabled = [&]() -> bool
		{
			return gasal2LongtargetBatch && !useCudaBatch;
		};

		struct Gasal2BatchScoreGroup
		{
			Gasal2BatchScoreGroup() : taskIndex(0), scoreInfoIndex(0) {}
			Gasal2BatchScoreGroup(size_t task, size_t scoreInfo) :
				taskIndex(task),
				scoreInfoIndex(scoreInfo)
			{
			}

			size_t taskIndex;
			size_t scoreInfoIndex;
		};

			auto extend_tasks_with_gasal2_batch = [&](
				const std::vector< std::vector<struct StripedSmithWaterman::scoreInfo> > &scoreInfosByTask,
				std::vector< std::vector<triplex> > &triplexesByTask,
				bool allowCudaBatch,
				bool scoreInfosAlreadyPruned) -> bool
			{
				FasimScopedSeconds scoped(phaseTimingEnabled, &phaseTiming.gasal2_extend_wall_seconds);
				if (phaseTimingEnabled)
				{
					++phaseTiming.gasal2_extend_batches;
					phaseTiming.gasal2_extend_tasks += static_cast<uint64_t>(tasks.size());
				}
				triplexesByTask.clear();
				triplexesByTask.resize(tasks.size());
			const bool gasal2CanRun =
				allowCudaBatch ? gasal2LongtargetBatch : gasal2_batched_traceback_enabled();
			const bool segmentedLongQueryShadowCanRun =
				gasal2LongQuerySegmentedShadowStats.requested != 0 &&
				!gasal2QueryLengthSupported &&
				fasim_gasal2_is_built();
			if ((!gasal2CanRun && !segmentedLongQueryShadowCanRun) ||
			    scoreInfosByTask.size() != tasks.size())
			{
				return false;
			}
			const bool segmentedLongQueryReplayRequested =
				segmentedLongQueryShadowCanRun &&
				fasim_gasal2_long_query_segmented_score_prepass_shadow_runtime() &&
				fasim_gasal2_long_query_segmented_cpu_traceback_replay_runtime();
			const bool useCpuTracebackReplay =
				gasal2LongtargetCpuTracebackBatch ||
				segmentedLongQueryReplayRequested;
			const bool ntSumSpanPrune = fasim_gasal2_nt_sum_span_prune_enabled_runtime();
			if (phaseTimingEnabled && ntSumSpanPrune)
			{
				++phaseTiming.gasal2_nt_sum_span_prune_active;
			}

			const int segmentedLongQueryScoreInfoPruneMaxPerTask =
				segmentedLongQueryShadowCanRun ?
					fasim_gasal2_long_query_segmented_scoreinfo_max_per_task_runtime() :
					0;
			const int top5ScoreInfoPruneMaxPerTask =
				fasim_top5_gasal2_scoreinfo_prune_max_per_task_runtime();
			const int scoreInfoPruneMaxPerTask =
				segmentedLongQueryScoreInfoPruneMaxPerTask > 0 ?
					segmentedLongQueryScoreInfoPruneMaxPerTask :
					top5ScoreInfoPruneMaxPerTask;
			const bool scoreInfoPruneEnabled =
				!scoreInfosAlreadyPruned &&
				((fasim_top5_gasal2_gpu_scoreinfo_enabled_runtime() &&
				  top5ScoreInfoPruneMaxPerTask > 0) ||
				 segmentedLongQueryScoreInfoPruneMaxPerTask > 0) &&
				scoreInfoPruneMaxPerTask > 0;
			if (segmentedLongQueryScoreInfoPruneMaxPerTask > 0)
			{
				gasal2LongQuerySegmentedShadowStats.scoreinfo_max_per_task =
					static_cast<uint64_t>(segmentedLongQueryScoreInfoPruneMaxPerTask);
			}
			std::vector< std::vector<struct StripedSmithWaterman::scoreInfo> > scoreInfosForGasal2;
			const std::vector< std::vector<struct StripedSmithWaterman::scoreInfo> > *activeScoreInfos =
				&scoreInfosByTask;
			if (scoreInfoPruneEnabled)
			{
				scoreInfosForGasal2.resize(scoreInfosByTask.size());
				for (size_t t = 0; t < scoreInfosByTask.size(); ++t)
				{
					const std::vector<struct StripedSmithWaterman::scoreInfo> &input =
						scoreInfosByTask[t];
					if (phaseTimingEnabled)
					{
						phaseTiming.scoreinfo_prune_input_groups +=
							static_cast<uint64_t>(input.size());
					}
					if (segmentedLongQueryScoreInfoPruneMaxPerTask > 0)
					{
						gasal2LongQuerySegmentedShadowStats.scoreinfo_input_groups +=
							static_cast<uint64_t>(input.size());
					}
						if (input.size() <= static_cast<size_t>(scoreInfoPruneMaxPerTask))
						{
							scoreInfosForGasal2[t] = input;
							if (phaseTimingEnabled)
							{
							phaseTiming.scoreinfo_prune_kept_groups +=
								static_cast<uint64_t>(input.size());
							}
							if (segmentedLongQueryScoreInfoPruneMaxPerTask > 0)
							{
								gasal2LongQuerySegmentedShadowStats.scoreinfo_kept_groups +=
									static_cast<uint64_t>(input.size());
							}
							continue;
						}

						prune_scoreinfo_for_gasal2_top5(input,
						                                scoreInfoPruneMaxPerTask,
						                                scoreInfosForGasal2[t]);
						if (phaseTimingEnabled)
						{
							phaseTiming.scoreinfo_prune_kept_groups +=
								static_cast<uint64_t>(scoreInfosForGasal2[t].size());
						phaseTiming.scoreinfo_prune_pruned_groups +=
							static_cast<uint64_t>(input.size() - scoreInfosForGasal2[t].size());
						++phaseTiming.scoreinfo_prune_pruned_tasks;
					}
					if (segmentedLongQueryScoreInfoPruneMaxPerTask > 0)
					{
						gasal2LongQuerySegmentedShadowStats.scoreinfo_kept_groups +=
							static_cast<uint64_t>(scoreInfosForGasal2[t].size());
						gasal2LongQuerySegmentedShadowStats.scoreinfo_pruned_groups +=
							static_cast<uint64_t>(input.size() - scoreInfosForGasal2[t].size());
					}
				}
				activeScoreInfos = &scoreInfosForGasal2;
				if (phaseTimingEnabled)
				{
					phaseTiming.scoreinfo_prune_enabled = true;
					phaseTiming.scoreinfo_prune_max_per_task = scoreInfoPruneMaxPerTask;
				}
			}

			size_t reserveAttempts = 0;
			for (size_t t = 0; t < activeScoreInfos->size(); ++t)
			{
				reserveAttempts += (*activeScoreInfos)[t].size() * 5;
			}
			fasim_gasal2_record_longtarget_task_batch(static_cast<uint64_t>(tasks.size()),
			                                          static_cast<uint64_t>(reserveAttempts / 5));

			std::vector<FasimGasal2Attempt> gasalAttempts;
			std::vector<Gasal2BatchScoreGroup> scoreGroups;
			gasalAttempts.reserve(reserveAttempts);
			scoreGroups.reserve(reserveAttempts / 5 + 1);

			const auto attemptBuildStart = std::chrono::steady_clock::now();
			int gasalScoreGroup = 0;
			for (size_t t = 0; t < tasks.size(); ++t)
			{
				const StreamTask &task = tasks[t];
				const std::vector<struct StripedSmithWaterman::scoreInfo> &taskScoreInfos = (*activeScoreInfos)[t];
				for (size_t si = 0; si < taskScoreInfos.size(); ++si)
				{
					const StripedSmithWaterman::scoreInfo &scoreInfo = taskScoreInfos[si];
					scoreGroups.push_back(Gasal2BatchScoreGroup(t, si));
					float Iden = 0.6;
					while (Iden <= 1)
					{
						int cutlength = static_cast<int>(scoreInfo.score + 24) / (9 * Iden - 4) + 1;
						cutlength = scoreInfo.position - cutlength + 1 > 0 ? cutlength : scoreInfo.position + 1;
						const int targetStart = scoreInfo.position - cutlength + 1;
						if (targetStart >= 0 && cutlength > 0)
						{
							FasimGasal2Attempt attempt;
							attempt.scoreinfo_index = gasalScoreGroup;
							attempt.cutlength = cutlength;
							attempt.start = targetStart;
							attempt.prealign_score = scoreInfo.score;
							attempt.target_end_required_for_fallback = cutlength - 1;
							attempt.nt_min_length = paraList.cLength;
							attempt.set_target_view(&task.seq2,
							                        static_cast<size_t>(targetStart),
							                        static_cast<size_t>(cutlength));
							gasalAttempts.push_back(std::move(attempt));
						}
						Iden += 0.1;
					}
					++gasalScoreGroup;
				}
			}
			const double attemptBuildSeconds = fasim_seconds_since(attemptBuildStart);

			if (gasalAttempts.empty())
			{
				fasim_gasal2_record_longtarget_bridge_timing(attemptBuildSeconds,
				                                             0.0,
				                                             0.0,
				                                             0.0,
				                                             0.0,
				                                             0.0);
				if (segmentedLongQueryShadowCanRun && !gasal2CanRun)
				{
					return false;
				}
				return true;
			}

			std::vector<FasimGasal2SelectedAlignment> segmentedLongQueryReplaySelected;
			auto run_segmented_long_query_shadow = [&]() -> bool
			{
				if (!segmentedLongQueryShadowCanRun)
				{
					return true;
				}
				const auto shadowStart = std::chrono::steady_clock::now();
				std::vector<FasimGasal2LongQuerySegment> segments =
					fasim_build_gasal2_long_query_segments(
						lncSeq,
						fasim_gasal2_long_query_segmented_tile_len_runtime(),
						fasim_gasal2_long_query_segmented_tile_overlap_runtime(),
						fasim_gasal2_long_query_segmented_max_segments_runtime());
				gasal2LongQuerySegmentedShadowStats.query_len =
					static_cast<uint64_t>(lncSeq.size());
				gasal2LongQuerySegmentedShadowStats.segments =
					static_cast<uint64_t>(segments.size());
				if (segments.empty())
				{
					++gasal2LongQuerySegmentedShadowStats.fallbacks;
					gasal2LongQuerySegmentedShadowStats.total_seconds +=
						fasim_seconds_since(shadowStart);
					return false;
				}

				gasal2LongQuerySegmentedShadowStats.active = 1;
				bool ok = true;
				uint64_t translatedAlignments = 0;
				const bool scorePrepassOnly =
					fasim_gasal2_long_query_segmented_score_prepass_shadow_runtime();
				for (size_t segIndex = 0; segIndex < segments.size(); ++segIndex)
				{
					const FasimGasal2LongQuerySegment &segment = segments[segIndex];
					FasimGasal2Stats before = fasim_gasal2_snapshot_stats();
					std::vector<FasimGasal2SelectedAlignment> segmentSelected;
					std::string segmentError;
					const bool segmentOk = scorePrepassOnly ?
						fasim_gasal2_select_attempts(segment.query_segment,
						                            gasalAttempts,
						                            &segmentSelected,
						                            &segmentError) :
						fasim_gasal2_align_attempts(segment.query_segment,
						                           gasalAttempts,
						                           &segmentSelected,
						                           &segmentError);
					FasimGasal2Stats after = fasim_gasal2_snapshot_stats();
					if (after.requests >= before.requests)
					{
						gasal2LongQuerySegmentedShadowStats.gasal2_requests +=
							after.requests - before.requests;
					}
					if (after.traceback_requests >= before.traceback_requests)
					{
						gasal2LongQuerySegmentedShadowStats.traceback_requests +=
							after.traceback_requests - before.traceback_requests;
					}
					if (after.fallbacks >= before.fallbacks)
					{
						gasal2LongQuerySegmentedShadowStats.fallbacks +=
							after.fallbacks - before.fallbacks;
					}
					if (!segmentOk)
					{
						ok = false;
						if (after.fallbacks == before.fallbacks)
						{
							++gasal2LongQuerySegmentedShadowStats.fallbacks;
						}
						continue;
					}

					for (size_t i = 0; i < segmentSelected.size(); ++i)
					{
						FasimGasal2SelectedAlignment translated = segmentSelected[i];
						if (translated.alignment.query_begin >= 0)
						{
							translated.alignment.query_begin +=
								static_cast<int32_t>(segment.global_query_start);
						}
						if (translated.alignment.query_end >= 0)
						{
							translated.alignment.query_end +=
								static_cast<int32_t>(segment.global_query_start);
						}
						++translatedAlignments;
						if (segmentedLongQueryReplayRequested)
						{
							segmentedLongQueryReplaySelected.push_back(translated);
						}
					}
				}
				if (segmentedLongQueryReplayRequested)
				{
					const std::string replayOrder =
						fasim_gasal2_long_query_segmented_cpu_traceback_order_runtime();
					std::stable_sort(segmentedLongQueryReplaySelected.begin(),
					                 segmentedLongQueryReplaySelected.end(),
					                 [&](const FasimGasal2SelectedAlignment &lhs,
					                    const FasimGasal2SelectedAlignment &rhs)
					                 {
						                 if (lhs.scoreinfo_index != rhs.scoreinfo_index)
						                 {
							                 return lhs.scoreinfo_index < rhs.scoreinfo_index;
						                 }
						                 if (replayOrder == "threshold_score")
						                 {
							                 if (lhs.score_prepass_threshold_candidate !=
							                     rhs.score_prepass_threshold_candidate)
							                 {
								                 return lhs.score_prepass_threshold_candidate &&
								                        !rhs.score_prepass_threshold_candidate;
							                 }
							                 if (lhs.score_prepass_fallback_candidate !=
							                     rhs.score_prepass_fallback_candidate)
							                 {
								                 return lhs.score_prepass_fallback_candidate &&
								                        !rhs.score_prepass_fallback_candidate;
							                 }
						                 }
						                 if (replayOrder == "score")
						                 {
							                 if (lhs.score_prepass_score != rhs.score_prepass_score)
							                 {
								                 return lhs.score_prepass_score > rhs.score_prepass_score;
							                 }
							                 if (lhs.score_prepass_ref_end != rhs.score_prepass_ref_end)
							                 {
								                 return lhs.score_prepass_ref_end > rhs.score_prepass_ref_end;
							                 }
						                 }
						                 if (replayOrder == "threshold_score")
						                 {
							                 if (lhs.score_prepass_score != rhs.score_prepass_score)
							                 {
								                 return lhs.score_prepass_score > rhs.score_prepass_score;
							                 }
							                 if (lhs.score_prepass_ref_end != rhs.score_prepass_ref_end)
							                 {
								                 return lhs.score_prepass_ref_end > rhs.score_prepass_ref_end;
							                 }
						                 }
						                 if (lhs.start != rhs.start)
						                 {
							                 return lhs.start < rhs.start;
						                 }
						                 return lhs.cutlength < rhs.cutlength;
					                 });
				}
				(void)translatedAlignments;
				gasal2LongQuerySegmentedShadowStats.total_seconds +=
					fasim_seconds_since(shadowStart);
				return ok;
			};

			if (segmentedLongQueryShadowCanRun)
			{
				const bool segmentedLongQueryShadowOk = run_segmented_long_query_shadow();
				if (!gasal2CanRun && !segmentedLongQueryReplayRequested)
				{
					fasim_gasal2_record_longtarget_bridge_timing(attemptBuildSeconds,
					                                             0.0,
					                                             0.0,
					                                             0.0,
					                                             0.0,
					                                             0.0);
					return false;
				}
				if (!gasal2CanRun && segmentedLongQueryReplayRequested && !segmentedLongQueryShadowOk)
				{
					fasim_gasal2_record_longtarget_bridge_timing(attemptBuildSeconds,
					                                             0.0,
					                                             0.0,
					                                             0.0,
					                                             0.0,
					                                             0.0);
					return false;
				}
			}

			std::vector<FasimGasal2SelectedAlignment> gasalSelected;
			std::string gasalError;
			bool gasalOk = true;
			double scoreSelectSeconds = 0.0;
			if (segmentedLongQueryReplayRequested && !gasal2CanRun)
			{
				gasalSelected.swap(segmentedLongQueryReplaySelected);
			}
			else
			{
				const auto scoreSelectStart = std::chrono::steady_clock::now();
				gasalOk = useCpuTracebackReplay ?
					fasim_gasal2_select_attempts(lncSeq, gasalAttempts, &gasalSelected, &gasalError) :
					fasim_gasal2_align_attempts(lncSeq, gasalAttempts, &gasalSelected, &gasalError);
				scoreSelectSeconds = fasim_seconds_since(scoreSelectStart);
			}
			if (!gasalOk)
			{
				return false;
			}

			std::vector< std::vector<FasimGasal2SelectedAlignment> > replaySelectedByTask(tasks.size());
			uint64_t replaySelectedCount = 0;
			uint64_t cpuTracebackAlignCalls = 0;
			uint64_t cpuTracebackSkippedAfterEmit = 0;
			uint64_t cpuTracebackThresholdEmits = 0;
			uint64_t cpuTracebackBestFallbackEmits = 0;
			uint64_t cpuTracebackLastEmits = 0;
			uint64_t cpuTracebackRank1Emits = 0;
			uint64_t cpuTracebackRank2Emits = 0;
			uint64_t cpuTracebackRank3Emits = 0;
			uint64_t cpuTracebackRank4PlusEmits = 0;
			uint64_t cpuTracebackRankCutoffSkipped = 0;
			const uint64_t cpuTracebackMaxRank =
				fasim_gasal2_cpu_traceback_max_rank_runtime();
			double cpuTracebackSubstrSeconds = 0.0;
			double cpuTracebackAlignSeconds = 0.0;
			const auto replayStart = std::chrono::steady_clock::now();

			auto recordReplayRank = [&](uint64_t rank)
			{
				if (rank <= 1)
				{
					++cpuTracebackRank1Emits;
				}
				else if (rank == 2)
				{
					++cpuTracebackRank2Emits;
				}
				else if (rank == 3)
				{
					++cpuTracebackRank3Emits;
				}
				else
				{
					++cpuTracebackRank4PlusEmits;
				}
			};

			if (useCpuTracebackReplay)
			{
				StripedSmithWaterman::Aligner replayAligner;
				StripedSmithWaterman::Filter replayFilter;
				StripedSmithWaterman::Alignment bestAlignment;
				StripedSmithWaterman::Alignment lastAlignment;
				FasimGasal2SelectedAlignment bestSelected;
				FasimGasal2SelectedAlignment lastSelected;
				std::string smallSeq;
				int currentScoreGroup = -1;
				bool haveBest = false;
				bool haveLast = false;
				bool emitted = false;
				uint64_t currentGroupAlignRank = 0;

				auto flushCpuReplay = [&]()
				{
					if (currentScoreGroup >= 0 && static_cast<size_t>(currentScoreGroup) < scoreGroups.size() && !emitted)
					{
						const size_t taskIndex = scoreGroups[static_cast<size_t>(currentScoreGroup)].taskIndex;
						if (haveBest)
						{
							bestSelected.alignment = bestAlignment;
							replaySelectedByTask[taskIndex].push_back(bestSelected);
							++replaySelectedCount;
							++cpuTracebackBestFallbackEmits;
							recordReplayRank(currentGroupAlignRank);
						}
						else if (haveLast)
						{
							lastSelected.alignment = lastAlignment;
							if (lastSelected.alignment.sw_score != 0)
							{
								replaySelectedByTask[taskIndex].push_back(lastSelected);
								++replaySelectedCount;
								++cpuTracebackLastEmits;
								recordReplayRank(currentGroupAlignRank);
							}
						}
					}
					haveBest = false;
					haveLast = false;
					emitted = false;
					bestSelected = FasimGasal2SelectedAlignment();
					lastSelected = FasimGasal2SelectedAlignment();
					bestAlignment.Clear();
					lastAlignment.Clear();
					currentGroupAlignRank = 0;
				};

				for (size_t gi = 0; gi < gasalSelected.size(); ++gi)
				{
					FasimGasal2SelectedAlignment candidate = gasalSelected[gi];
					if (candidate.scoreinfo_index != currentScoreGroup)
					{
						flushCpuReplay();
						currentScoreGroup = candidate.scoreinfo_index;
					}
					if (emitted ||
					    candidate.scoreinfo_index < 0 ||
					    static_cast<size_t>(candidate.scoreinfo_index) >= scoreGroups.size())
					{
						if (emitted)
						{
							++cpuTracebackSkippedAfterEmit;
						}
						continue;
					}
					if (cpuTracebackMaxRank > 0 &&
					    currentGroupAlignRank >= cpuTracebackMaxRank)
					{
						++cpuTracebackRankCutoffSkipped;
						continue;
					}

					const Gasal2BatchScoreGroup &group = scoreGroups[static_cast<size_t>(candidate.scoreinfo_index)];
					if (group.taskIndex >= tasks.size() ||
					    group.scoreInfoIndex >= (*activeScoreInfos)[group.taskIndex].size())
					{
						continue;
					}

					const StreamTask &task = tasks[group.taskIndex];
					const StripedSmithWaterman::scoreInfo &scoreInfo =
						(*activeScoreInfos)[group.taskIndex][group.scoreInfoIndex];
					const int targetStart = candidate.start;
					const int cutlength = candidate.cutlength;
					if (targetStart < 0 || cutlength <= 0)
					{
						continue;
					}

					const auto substrStart = std::chrono::steady_clock::now();
					smallSeq = task.seq2.substr(static_cast<size_t>(targetStart),
					                            static_cast<size_t>(cutlength));
					cpuTracebackSubstrSeconds += fasim_seconds_since(substrStart);
					StripedSmithWaterman::Alignment cpuCandidateAlignment;
					const auto alignStart = std::chrono::steady_clock::now();
					replayAligner.Align(lncSeq.c_str(),
					                    smallSeq.c_str(),
					                    static_cast<int>(smallSeq.size()),
					                    replayFilter,
					                    &cpuCandidateAlignment,
					                    15);
					cpuTracebackAlignSeconds += fasim_seconds_since(alignStart);
					++cpuTracebackAlignCalls;
					++currentGroupAlignRank;

					if (!emitted)
					{
						lastSelected = candidate;
						lastAlignment = cpuCandidateAlignment;
						haveLast = true;
					}
					if (!emitted && cpuCandidateAlignment.sw_score >= scoreInfo.score)
					{
						candidate.alignment = cpuCandidateAlignment;
						replaySelectedByTask[group.taskIndex].push_back(candidate);
						++replaySelectedCount;
						++cpuTracebackThresholdEmits;
						recordReplayRank(currentGroupAlignRank);
						emitted = true;
						continue;
					}
					if (!emitted &&
					    cpuCandidateAlignment.sw_score > bestAlignment.sw_score &&
					    cpuCandidateAlignment.ref_end == cutlength - 1)
					{
						bestSelected = candidate;
						bestAlignment = cpuCandidateAlignment;
						haveBest = true;
					}
				}
				flushCpuReplay();
			}
			else
			{
				for (size_t gi = 0; gi < gasalSelected.size(); ++gi)
				{
					FasimGasal2SelectedAlignment candidate = gasalSelected[gi];
					if (!candidate.selected ||
					    candidate.alignment.sw_score == 0 ||
					    candidate.scoreinfo_index < 0 ||
					    static_cast<size_t>(candidate.scoreinfo_index) >= scoreGroups.size())
					{
						continue;
					}
					const Gasal2BatchScoreGroup &group = scoreGroups[static_cast<size_t>(candidate.scoreinfo_index)];
					if (group.taskIndex >= tasks.size())
					{
						continue;
					}
					replaySelectedByTask[group.taskIndex].push_back(candidate);
					++replaySelectedCount;
					++cpuTracebackThresholdEmits;
					recordReplayRank(1);
				}
			}
			const double cpuTracebackReplaySeconds = fasim_seconds_since(replayStart);
			if (phaseTimingEnabled)
			{
				phaseTiming.gasal2_selected_alignments += replaySelectedCount;
			}
			fasim_gasal2_record_cpu_traceback_replay(gasalSelected.size(), replaySelectedCount);
			fasim_gasal2_record_cpu_traceback_aligns(cpuTracebackAlignCalls,
			                                         cpuTracebackSkippedAfterEmit,
			                                         cpuTracebackRankCutoffSkipped);
			fasim_gasal2_record_cpu_traceback_outcomes(cpuTracebackThresholdEmits,
			                                           cpuTracebackBestFallbackEmits,
			                                           cpuTracebackLastEmits,
			                                           0,
			                                           0,
			                                           0,
			                                           cpuTracebackRank1Emits,
			                                           cpuTracebackRank2Emits,
			                                           cpuTracebackRank3Emits,
			                                           cpuTracebackRank4PlusEmits);

										const int8_t nt_table[128] = {
											4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
			4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
			4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
			4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
			4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
			4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
			4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
			4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4
				};

				const auto convertStart = std::chrono::steady_clock::now();
				const bool replayUsesCpuTraceback = useCpuTracebackReplay;
				std::atomic<uint64_t> convertInputAlignments(0);
				std::atomic<uint64_t> convertRawTriplexes(0);
				std::atomic<uint64_t> convertTasks(0);
				std::atomic<uint64_t> convertTasksWithInput(0);
				std::atomic<uint64_t> convertAlignmentNanos(0);
				std::atomic<uint64_t> convertSortNanos(0);
				std::atomic<uint64_t> convertFilterNanos(0);
				std::atomic<uint64_t> convertRankMapNanos(0);
				std::atomic<uint64_t> shadowQuerySpanLtCLength(0);
				std::atomic<uint64_t> shadowRefSpanLtCLength(0);
				std::atomic<uint64_t> shadowMinSpanLtCLength(0);
					std::atomic<uint64_t> shadowMaxSpanLtCLength(0);
					std::atomic<uint64_t> shadowSumSpanLtCLength(0);
					const bool observeEmitRank =
						fasim_top5_gasal2_scoreinfo_emit_rank_observe_enabled_runtime();
					std::atomic<uint64_t> emitRankObservedAlignments(0);
					std::atomic<uint64_t> emitRankMax(0);
					std::atomic<uint64_t> emitRank1(0);
					std::atomic<uint64_t> emitRank2To4(0);
					std::atomic<uint64_t> emitRank5To8(0);
					std::atomic<uint64_t> emitRank9To16(0);
				std::atomic<uint64_t> emitRank17To32(0);
				std::atomic<uint64_t> emitRank33Plus(0);
				const bool collectLiteRankMap =
					fasim_top5_gasal2_scoreinfo_topk_lite_rank_observe_enabled_runtime();
				auto scoreInfoRankForSelected = [&](const FasimGasal2SelectedAlignment &selectedAlignment) -> uint64_t
				{
					if (selectedAlignment.scoreinfo_index < 0 ||
					    static_cast<size_t>(selectedAlignment.scoreinfo_index) >= scoreGroups.size())
					{
						return 0;
					}
					return static_cast<uint64_t>(
						scoreGroups[static_cast<size_t>(selectedAlignment.scoreinfo_index)].scoreInfoIndex) + 1;
				};
				auto observeScoreInfoRank = [&](const FasimGasal2SelectedAlignment &selectedAlignment)
				{
					if (!observeEmitRank)
					{
						return;
					}
					const uint64_t rank = scoreInfoRankForSelected(selectedAlignment);
					if (rank == 0)
					{
						return;
					}
					emitRankObservedAlignments.fetch_add(1, std::memory_order_relaxed);
						uint64_t currentMax = emitRankMax.load(std::memory_order_relaxed);
						while (rank > currentMax &&
						       !emitRankMax.compare_exchange_weak(currentMax,
						                                          rank,
						                                          std::memory_order_relaxed,
						                                          std::memory_order_relaxed))
						{
						}
						if (rank <= 1)
						{
							emitRank1.fetch_add(1, std::memory_order_relaxed);
						}
						else if (rank <= 4)
						{
							emitRank2To4.fetch_add(1, std::memory_order_relaxed);
						}
						else if (rank <= 8)
						{
							emitRank5To8.fetch_add(1, std::memory_order_relaxed);
						}
						else if (rank <= 16)
						{
							emitRank9To16.fetch_add(1, std::memory_order_relaxed);
						}
						else if (rank <= 32)
						{
							emitRank17To32.fetch_add(1, std::memory_order_relaxed);
						}
						else
						{
							emitRank33Plus.fetch_add(1, std::memory_order_relaxed);
						}
					};
					auto convertOneTask = [&](size_t t)
					{
					const StreamTask &task = tasks[t];
					std::vector<triplex> myTriplexList;
					myTriplexList.reserve(replaySelectedByTask[t].size());
					if (phaseTimingEnabled)
					{
						convertTasks.fetch_add(1, std::memory_order_relaxed);
						if (!replaySelectedByTask[t].empty())
						{
							convertTasksWithInput.fetch_add(1, std::memory_order_relaxed);
						}
					}
					std::map<std::string, uint64_t> liteRowScoreInfoRanks;
					for (size_t si = 0; si < replaySelectedByTask[t].size(); ++si)
					{
						const FasimGasal2SelectedAlignment &selectedAlignment = replaySelectedByTask[t][si];
						const StripedSmithWaterman::Alignment *alignmentForTriplex =
							&selectedAlignment.alignment;
						StripedSmithWaterman::Alignment cpuReplayAdjustedAlignment;
					if (replayUsesCpuTraceback && selectedAlignment.selected)
					{
						cpuReplayAdjustedAlignment = selectedAlignment.alignment;
						cpuReplayAdjustedAlignment.ref_begin += selectedAlignment.start;
						cpuReplayAdjustedAlignment.ref_end += selectedAlignment.start;
						alignmentForTriplex = &cpuReplayAdjustedAlignment;
						}
							if (selectedAlignment.selected && alignmentForTriplex->sw_score != 0)
							{
								observeScoreInfoRank(selectedAlignment);
								const uint64_t selectedScoreInfoRank = scoreInfoRankForSelected(selectedAlignment);
								const size_t beforeTriplexCount = myTriplexList.size();
								if (phaseTimingEnabled)
								{
								convertInputAlignments.fetch_add(1, std::memory_order_relaxed);
							const int querySpan = alignmentForTriplex->query_end - alignmentForTriplex->query_begin + 1;
							const int refSpan = alignmentForTriplex->ref_end - alignmentForTriplex->ref_begin + 1;
							if (querySpan < paraList.cLength)
							{
								shadowQuerySpanLtCLength.fetch_add(1, std::memory_order_relaxed);
							}
							if (refSpan < paraList.cLength)
							{
								shadowRefSpanLtCLength.fetch_add(1, std::memory_order_relaxed);
							}
							if (std::min(querySpan, refSpan) < paraList.cLength)
							{
								shadowMinSpanLtCLength.fetch_add(1, std::memory_order_relaxed);
							}
							if (std::max(querySpan, refSpan) < paraList.cLength)
							{
								shadowMaxSpanLtCLength.fetch_add(1, std::memory_order_relaxed);
							}
							if (querySpan + refSpan < paraList.cLength)
							{
								shadowSumSpanLtCLength.fetch_add(1, std::memory_order_relaxed);
								if (ntSumSpanPrune)
								{
									continue;
								}
							}
						}
							const auto convertAlignmentStart = std::chrono::steady_clock::now();
							convertMyTriplex(*alignmentForTriplex,
							                 myTriplexList,
						                 lncSeq,
						                 task.seq2,
							                 *task.srcSeq,
						                 nt_table,
						                 task.dnaStartPos,
						                 task.rule,
						                 task.strand,
						                 task.Para,
						                 paraList.penaltyT,
							                 paraList.penaltyC,
							                 paraList.ntMin,
							                 paraList.ntMax,
							                 writeFull);
							if (phaseTimingEnabled)
							{
								convertAlignmentNanos.fetch_add(
									static_cast<uint64_t>(
										std::chrono::duration_cast<std::chrono::nanoseconds>(
											std::chrono::steady_clock::now() -
											convertAlignmentStart).count()),
									std::memory_order_relaxed);
							}
							if (collectLiteRankMap && selectedScoreInfoRank != 0)
							{
								const auto rankMapStart = std::chrono::steady_clock::now();
								for (size_t rankIndex = beforeTriplexCount;
								     rankIndex < myTriplexList.size();
								     ++rankIndex)
								{
									FasimLiteRow rankRow =
										fasim_make_lite_row(myTriplexList[rankIndex].chr.empty() ?
										                    task.chr :
										                    myTriplexList[rankIndex].chr,
										                    myTriplexList[rankIndex].genomestart != 0 ?
										                    myTriplexList[rankIndex].genomestart :
										                    myTriplexList[rankIndex].starj + task.recordStartGenome - 1,
										                    myTriplexList[rankIndex].genomeend != 0 ?
										                    myTriplexList[rankIndex].genomeend :
										                    myTriplexList[rankIndex].endj + task.recordStartGenome - 1,
										                    myTriplexList[rankIndex],
										                    selectedScoreInfoRank);
									std::map<std::string, uint64_t>::iterator existingRank =
										liteRowScoreInfoRanks.find(rankRow.key);
									if (existingRank == liteRowScoreInfoRanks.end() ||
									    selectedScoreInfoRank < existingRank->second)
									{
										liteRowScoreInfoRanks[rankRow.key] = selectedScoreInfoRank;
									}
								}
								if (phaseTimingEnabled)
								{
									convertRankMapNanos.fetch_add(
										static_cast<uint64_t>(
											std::chrono::duration_cast<std::chrono::nanoseconds>(
												std::chrono::steady_clock::now() -
												rankMapStart).count()),
										std::memory_order_relaxed);
								}
							}
						}
					}
				if (phaseTimingEnabled)
				{
					convertRawTriplexes.fetch_add(
						static_cast<uint64_t>(myTriplexList.size()),
						std::memory_order_relaxed);
				}

				const auto sortStart = std::chrono::steady_clock::now();
				std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple);
				myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
				std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple2);
				myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
				std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexSingle);
				if (phaseTimingEnabled)
				{
					convertSortNanos.fetch_add(
						static_cast<uint64_t>(
							std::chrono::duration_cast<std::chrono::nanoseconds>(
								std::chrono::steady_clock::now() - sortStart).count()),
						std::memory_order_relaxed);
				}
				const auto filterStart = std::chrono::steady_clock::now();
				for (int i = 0; i < (myTriplexList.size() > N ? N : myTriplexList.size()); i++)
				{
							triplex atr = myTriplexList[static_cast<size_t>(i)];
							if (atr.identity >= paraList.minIdentity &&
							    atr.tri_score >= paraList.minStability &&
							    atr.nt >= paraList.ntMin)
							{
								triplexesByTask[t].push_back(atr);
							}
						}
						if (phaseTimingEnabled)
						{
							convertFilterNanos.fetch_add(
								static_cast<uint64_t>(
									std::chrono::duration_cast<std::chrono::nanoseconds>(
										std::chrono::steady_clock::now() -
										filterStart).count()),
								std::memory_order_relaxed);
						}
						if (!liteRowScoreInfoRanks.empty())
						{
							const auto rankApplyStart = std::chrono::steady_clock::now();
							for (size_t i = 0; i < triplexesByTask[t].size(); ++i)
							{
								triplex &atr = triplexesByTask[t][i];
								const std::string &chrForRank = atr.chr.empty() ? task.chr : atr.chr;
								const long genomeStartForRank = (atr.genomestart != 0) ?
									atr.genomestart :
									(atr.starj + task.recordStartGenome - 1);
								const long genomeEndForRank = (atr.genomeend != 0) ?
									atr.genomeend :
									(atr.endj + task.recordStartGenome - 1);
								FasimLiteRow rankRow = fasim_make_lite_row(chrForRank,
								                                           genomeStartForRank,
								                                           genomeEndForRank,
								                                           atr);
								std::map<std::string, uint64_t>::const_iterator rankIt =
									liteRowScoreInfoRanks.find(rankRow.key);
								if (rankIt != liteRowScoreInfoRanks.end() &&
								    rankIt->second > 0 &&
								    rankIt->second <= static_cast<uint64_t>(std::numeric_limits<int>::max()))
								{
									atr.neartriplex = -static_cast<int>(rankIt->second);
								}
							}
							if (phaseTimingEnabled)
							{
								convertRankMapNanos.fetch_add(
									static_cast<uint64_t>(
										std::chrono::duration_cast<std::chrono::nanoseconds>(
											std::chrono::steady_clock::now() -
											rankApplyStart).count()),
									std::memory_order_relaxed);
							}
						}
					};
				const int convertWorkerCount =
					std::min(static_cast<int>(tasks.size()),
					         std::max(1, extendThreadCount));
				if (convertWorkerCount <= 1 || tasks.size() <= 1)
				{
					for (size_t t = 0; t < tasks.size(); ++t)
					{
						convertOneTask(t);
					}
				}
				else
				{
					std::atomic<size_t> nextConvertTask(0);
					std::vector<std::thread> convertWorkers;
					convertWorkers.reserve(static_cast<size_t>(convertWorkerCount));
					for (int w = 0; w < convertWorkerCount; ++w)
					{
						convertWorkers.push_back(std::thread([&]()
						{
							while (true)
							{
								const size_t t =
									nextConvertTask.fetch_add(1, std::memory_order_relaxed);
								if (t >= tasks.size())
								{
									break;
								}
								convertOneTask(t);
							}
						}));
					}
					for (size_t i = 0; i < convertWorkers.size(); ++i)
					{
						convertWorkers[i].join();
					}
				}
				const double cpuTracebackConvertSeconds = fasim_seconds_since(convertStart);
			if (phaseTimingEnabled)
			{
				phaseTiming.gasal2_convert_input_alignments +=
					convertInputAlignments.load(std::memory_order_relaxed);
				phaseTiming.gasal2_convert_triplexes_raw +=
					convertRawTriplexes.load(std::memory_order_relaxed);
				phaseTiming.gasal2_convert_tasks +=
					convertTasks.load(std::memory_order_relaxed);
				phaseTiming.gasal2_convert_tasks_with_input +=
					convertTasksWithInput.load(std::memory_order_relaxed);
				phaseTiming.gasal2_convert_alignment_seconds +=
					static_cast<double>(convertAlignmentNanos.load(std::memory_order_relaxed)) / 1000000000.0;
				phaseTiming.gasal2_convert_sort_seconds +=
					static_cast<double>(convertSortNanos.load(std::memory_order_relaxed)) / 1000000000.0;
				phaseTiming.gasal2_convert_filter_seconds +=
					static_cast<double>(convertFilterNanos.load(std::memory_order_relaxed)) / 1000000000.0;
				phaseTiming.gasal2_convert_rank_map_seconds +=
					static_cast<double>(convertRankMapNanos.load(std::memory_order_relaxed)) / 1000000000.0;
				phaseTiming.gasal2_nt_shadow_query_span_lt_clength +=
					shadowQuerySpanLtCLength.load(std::memory_order_relaxed);
				phaseTiming.gasal2_nt_shadow_ref_span_lt_clength +=
					shadowRefSpanLtCLength.load(std::memory_order_relaxed);
				phaseTiming.gasal2_nt_shadow_min_span_lt_clength +=
					shadowMinSpanLtCLength.load(std::memory_order_relaxed);
				phaseTiming.gasal2_nt_shadow_max_span_lt_clength +=
					shadowMaxSpanLtCLength.load(std::memory_order_relaxed);
					phaseTiming.gasal2_nt_shadow_sum_span_lt_clength +=
						shadowSumSpanLtCLength.load(std::memory_order_relaxed);
					if (observeEmitRank)
					{
						phaseTiming.scoreinfo_emit_rank_observe_enabled = true;
						phaseTiming.scoreinfo_emit_rank_observe_alignments +=
							emitRankObservedAlignments.load(std::memory_order_relaxed);
						phaseTiming.scoreinfo_emit_rank_observe_max_rank =
							std::max(phaseTiming.scoreinfo_emit_rank_observe_max_rank,
							         emitRankMax.load(std::memory_order_relaxed));
						phaseTiming.scoreinfo_emit_rank_observe_rank1 +=
							emitRank1.load(std::memory_order_relaxed);
						phaseTiming.scoreinfo_emit_rank_observe_rank2_4 +=
							emitRank2To4.load(std::memory_order_relaxed);
						phaseTiming.scoreinfo_emit_rank_observe_rank5_8 +=
							emitRank5To8.load(std::memory_order_relaxed);
						phaseTiming.scoreinfo_emit_rank_observe_rank9_16 +=
							emitRank9To16.load(std::memory_order_relaxed);
						phaseTiming.scoreinfo_emit_rank_observe_rank17_32 +=
							emitRank17To32.load(std::memory_order_relaxed);
						phaseTiming.scoreinfo_emit_rank_observe_rank33_plus +=
							emitRank33Plus.load(std::memory_order_relaxed);
					}
				}
			fasim_gasal2_record_longtarget_bridge_timing(attemptBuildSeconds,
			                                             scoreSelectSeconds,
			                                             cpuTracebackReplaySeconds,
			                                             cpuTracebackSubstrSeconds,
			                                             cpuTracebackAlignSeconds,
			                                             cpuTracebackConvertSeconds);
			return true;
		};

			auto flush_batch = [&]()
			{
				if (tasks.empty())
				{
					return;
				}
				std::vector< std::vector<struct StripedSmithWaterman::scoreInfo> >
					streamingRealpathScoreInfos;
				std::vector<unsigned char> streamingRealpathReady;
				FasimScopedSeconds flushScoped(phaseTimingEnabled, &phaseTiming.flush_total_seconds);
				if (phaseTimingEnabled)
				{
					++phaseTiming.flushes;
					phaseTiming.flush_tasks += static_cast<uint64_t>(tasks.size());
				}

				auto run_long_query_streaming_scoreinfo_shadow = [&]()
				{
					if (longQueryStreamingScoreInfoShadowStats.requested == 0 ||
					    gasal2QueryLengthSupported ||
					    !paraList.doFastSim)
						{
							return;
						}
						const bool twoContractRequested =
							fasim_long_query_streaming_scoreinfo_two_contract_bridge_runtime();
						const bool fusedMinScoreRequested =
							!twoContractRequested &&
							fasim_long_query_streaming_scoreinfo_fused_minscore_runtime();
						const bool twoContractTrustRequested =
							twoContractRequested &&
							fasim_long_query_streaming_scoreinfo_two_contract_bridge_trust_runtime();
						const bool scorePrepassStateMachineShadowRequested =
							fasim_gasal2_score_prepass_state_machine_consumer_shadow_runtime() ||
							fasim_gasal2_score_prepass_state_machine_consumer_trust_runtime();
						const bool scorePrepassStateMachineTrustRequested =
							fasim_gasal2_score_prepass_state_machine_consumer_trust_runtime();
							const bool streamingRealpathRequested =
								fasim_long_query_streaming_scoreinfo_realpath_prototype_runtime() ||
								scorePrepassStateMachineShadowRequested;
						const bool streamingRealpathAllowed =
							(streamingRealpathRequested && !twoContractRequested) ||
							twoContractTrustRequested;
						const bool streamingRealpathTrust =
							((streamingRealpathRequested && !twoContractRequested) ||
							 twoContractTrustRequested) &&
							!fusedMinScoreRequested &&
							(twoContractTrustRequested ||
							 fasim_long_query_streaming_scoreinfo_realpath_trust_runtime());
						if (streamingRealpathAllowed)
						{
							longQueryStreamingScoreInfoShadowStats.realpath_requested = 1;
							longQueryStreamingScoreInfoShadowStats.realpath_trust =
								streamingRealpathTrust ? 1ULL : 0ULL;
							longQueryStreamingScoreInfoShadowStats.realpath_digest_authority =
								streamingRealpathTrust ?
									"external_digest_gate" :
									"cpu_validated";
							streamingRealpathScoreInfos.clear();
							streamingRealpathScoreInfos.resize(tasks.size());
							streamingRealpathReady.assign(tasks.size(), 0);
						}
						const uint64_t globalTaskBegin =
							longQueryStreamingScoreInfoShadowStats.tasks;
						longQueryStreamingScoreInfoShadowStats.tasks +=
							static_cast<uint64_t>(tasks.size());
					if (currentTargetLength > 0)
					{
						longQueryStreamingScoreInfoShadowStats.cells +=
							static_cast<uint64_t>(tasks.size()) *
							static_cast<uint64_t>(currentTargetLength);
					}
					else
					{
						for (size_t taskIndex = 0; taskIndex < tasks.size(); ++taskIndex)
						{
							longQueryStreamingScoreInfoShadowStats.cells +=
								static_cast<uint64_t>(tasks[taskIndex].seq2.size());
						}
					}
					if (cudaQueries.empty() ||
					    encodedTargets.empty() ||
					    currentTargetLength <= 0 ||
					    tasks.empty())
					{
						longQueryStreamingScoreInfoShadowStats.unsupported = 1;
						++longQueryStreamingScoreInfoShadowStats.fallback_batches;
						if (twoContractRequested)
						{
							++longQueryStreamingScoreInfoShadowStats
								.two_contract_fallbacks;
						}
						if (longQueryStreamingScoreInfoShadowStats.error == "none")
						{
							longQueryStreamingScoreInfoShadowStats.error =
								"cuda_query_or_batch_unavailable";
						}
						if (twoContractRequested)
						{
							longQueryStreamingScoreInfoShadowStats.two_contract_error =
								longQueryStreamingScoreInfoShadowStats.error;
							longQueryStreamingScoreInfoShadowStats.decision =
								"two_contract_bridge_shadow_launch_failed";
						}
						return;
					}
					const bool legacyByteMode =
						streamingScoreInfoLegacyByteRequested &&
						streamingScoreInfoLegacyByteCudaQueryReady;
					const bool legacyByteSharedMemoryMode =
						legacyByteMode &&
						fasim_long_query_streaming_scoreinfo_legacy_byte_shared_runtime();
						longQueryStreamingScoreInfoShadowStats.legacy_byte_shared =
							legacyByteSharedMemoryMode ? 1ULL : 0ULL;
						if (legacyByteSharedMemoryMode)
						{
							PreAlignCudaResourceLimits sharedResourceLimits;
							std::string sharedResourceError;
							if (prealign_cuda_query_resource_limits(
								    streamingScoreInfoLegacyByteCudaQuery,
								    &sharedResourceLimits,
								    &sharedResourceError))
							{
								longQueryStreamingScoreInfoShadowStats
									.legacy_byte_shared_required_smem_bytes =
									static_cast<uint64_t>(
										sharedResourceLimits.requiredDynamicSmemBytes / 2);
								longQueryStreamingScoreInfoShadowStats
									.legacy_byte_shared_default_smem_limit_bytes =
									static_cast<uint64_t>(
										sharedResourceLimits.defaultDynamicSmemLimitBytes);
								longQueryStreamingScoreInfoShadowStats
									.legacy_byte_shared_optin_smem_limit_bytes =
									static_cast<uint64_t>(
										sharedResourceLimits.optinDynamicSmemLimitBytes);
							}
							else if (!sharedResourceError.empty() &&
							         longQueryStreamingScoreInfoShadowStats.error == "none")
							{
								longQueryStreamingScoreInfoShadowStats.error =
									sharedResourceError;
							}
						}
						if (streamingScoreInfoLegacyByteRequested && !legacyByteMode)
					{
						longQueryStreamingScoreInfoShadowStats.unsupported = 1;
						++longQueryStreamingScoreInfoShadowStats.fallback_batches;
						if (twoContractRequested)
						{
							++longQueryStreamingScoreInfoShadowStats
								.two_contract_fallbacks;
						}
						longQueryStreamingScoreInfoShadowStats.error =
							"legacy_byte_query_unavailable";
						if (twoContractRequested)
						{
							longQueryStreamingScoreInfoShadowStats.two_contract_error =
								"legacy_byte_query_unavailable";
							longQueryStreamingScoreInfoShadowStats.decision =
								"two_contract_bridge_shadow_launch_failed";
						}
						return;
					}

					int maxPerTask =
						fasim_env_int_or_default(
							"FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_SHADOW_MAX_PER_TASK",
							256);
					if (maxPerTask > 256)
					{
						maxPerTask = 256;
					}
					if (maxPerTask <= 0)
					{
						longQueryStreamingScoreInfoShadowStats.unsupported = 1;
						++longQueryStreamingScoreInfoShadowStats.fallback_batches;
						if (twoContractRequested)
						{
							++longQueryStreamingScoreInfoShadowStats
								.two_contract_fallbacks;
						}
						longQueryStreamingScoreInfoShadowStats.error = "invalid_max_per_task";
						if (twoContractRequested)
						{
							longQueryStreamingScoreInfoShadowStats.two_contract_error =
								"invalid_max_per_task";
							longQueryStreamingScoreInfoShadowStats.decision =
								"two_contract_bridge_shadow_launch_failed";
						}
						return;
					}

					const auto shadowStart = std::chrono::steady_clock::now();
					std::vector<PreAlignCudaPeak> compactScoreInfos;
					std::vector<int> compactCounts;
					std::vector<int> compactInputCounts;
					std::vector<int> compactMinScores(tasks.size(), 0);
					std::vector<int> gpuMinScoreSourceScores;
					longQueryStreamingScoreInfoShadowStats.two_contract_requested =
						twoContractRequested ? 1ULL : 0ULL;
					longQueryStreamingScoreInfoShadowStats.fused_minscore_requested =
						fusedMinScoreRequested ? 1ULL : 0ULL;
					longQueryStreamingScoreInfoShadowStats.gpu_minscore_requested =
						streamingScoreInfoGpuMinScoreRequested ? 1ULL : 0ULL;
					const bool gpuMinScoreHotRequested =
						streamingScoreInfoGpuMinScoreRequested &&
						fasim_long_query_streaming_scoreinfo_gpu_minscore_hot_runtime();
					longQueryStreamingScoreInfoShadowStats.gpu_minscore_hot =
						gpuMinScoreHotRequested ? 1ULL : 0ULL;
					bool gpuMinScoreOk = false;
					double gpuMinScoreWallSeconds = 0.0;
					double gpuMinScoreKernelSeconds = 0.0;
					double gpuMinScoreH2DSeconds = 0.0;
					double gpuMinScoreD2HSeconds = 0.0;
					if (!fusedMinScoreRequested &&
					    streamingScoreInfoGpuMinScoreRequested &&
					    streamingScoreInfoGpuMinScoreCudaQueryReady &&
					    legacyEncodedTargets.size() == encodedTargets.size())
					{
						PreAlignCudaBatchResult gpuMinScoreResult;
						PreAlignCudaBatchResult gpuMinScoreReduceResult;
						std::string gpuMinScoreError;
						const auto gpuMinScoreStart =
							std::chrono::steady_clock::now();
						gpuMinScoreOk =
							prealign_cuda_find_max_scores_global_state_batch(
								streamingScoreInfoGpuMinScoreCudaQuery,
								legacyEncodedTargets.data(),
								static_cast<int>(tasks.size()),
								currentTargetLength,
								false,
								&gpuMinScoreSourceScores,
								&gpuMinScoreResult,
								&gpuMinScoreReduceResult,
								&gpuMinScoreError);
						gpuMinScoreWallSeconds = fasim_seconds_since(gpuMinScoreStart);
						gpuMinScoreKernelSeconds =
							gpuMinScoreResult.gpuSeconds +
							gpuMinScoreReduceResult.gpuSeconds;
						gpuMinScoreH2DSeconds =
							gpuMinScoreResult.h2dSeconds +
							gpuMinScoreReduceResult.h2dSeconds;
						gpuMinScoreD2HSeconds =
							gpuMinScoreResult.d2hSeconds +
							gpuMinScoreReduceResult.d2hSeconds;
						longQueryStreamingScoreInfoShadowStats
							.gpu_minscore_wall_seconds +=
							gpuMinScoreWallSeconds;
						longQueryStreamingScoreInfoShadowStats
							.gpu_minscore_kernel_seconds +=
							gpuMinScoreKernelSeconds;
						longQueryStreamingScoreInfoShadowStats
							.gpu_minscore_h2d_seconds +=
							gpuMinScoreH2DSeconds;
						longQueryStreamingScoreInfoShadowStats
							.gpu_minscore_d2h_seconds +=
							gpuMinScoreD2HSeconds;
						if (gpuMinScoreOk)
						{
							longQueryStreamingScoreInfoShadowStats.gpu_minscore_active = 1;
							longQueryStreamingScoreInfoShadowStats.gpu_minscore_error =
								"none";
						}
						else
						{
							++longQueryStreamingScoreInfoShadowStats
								.gpu_minscore_fallbacks;
							if (twoContractRequested)
							{
								++longQueryStreamingScoreInfoShadowStats
									.two_contract_fallbacks;
							}
							if (!gpuMinScoreError.empty())
							{
								longQueryStreamingScoreInfoShadowStats
									.gpu_minscore_error =
									gpuMinScoreError;
								if (twoContractRequested)
								{
									longQueryStreamingScoreInfoShadowStats
										.two_contract_error =
										gpuMinScoreError;
								}
							}
							gpuMinScoreSourceScores.clear();
						}
					}
					else if (!fusedMinScoreRequested &&
					         streamingScoreInfoGpuMinScoreRequested)
					{
						++longQueryStreamingScoreInfoShadowStats
							.gpu_minscore_fallbacks;
						if (twoContractRequested)
						{
							++longQueryStreamingScoreInfoShadowStats
								.two_contract_fallbacks;
						}
						if (longQueryStreamingScoreInfoShadowStats
							    .gpu_minscore_error == "none")
						{
							longQueryStreamingScoreInfoShadowStats
								.gpu_minscore_error =
								"legacy_score_query_or_targets_unavailable";
						}
						if (twoContractRequested &&
						    longQueryStreamingScoreInfoShadowStats.two_contract_error == "none")
						{
							longQueryStreamingScoreInfoShadowStats.two_contract_error =
								"legacy_score_query_or_targets_unavailable";
						}
					}
					const auto minScoreStart = std::chrono::steady_clock::now();
					if (!fusedMinScoreRequested)
					{
						for (size_t t = 0; t < tasks.size(); ++t)
						{
							StreamTask &task = tasks[t];
							if (task.minScoreReady)
							{
								++longQueryStreamingScoreInfoShadowStats
									.minscore_cache_hits;
							}
							else
							{
								++longQueryStreamingScoreInfoShadowStats
									.minscore_cache_misses;
							}
							if (gpuMinScoreHotRequested &&
							    gpuMinScoreOk &&
							    t < gpuMinScoreSourceScores.size())
							{
								const int gpuScore = gpuMinScoreSourceScores[t];
								compactMinScores[t] =
									fasim_min_score_from_full_score(gpuScore);
								++longQueryStreamingScoreInfoShadowStats
									.gpu_minscore_used;
								if (twoContractRequested)
								{
									++longQueryStreamingScoreInfoShadowStats
										.two_contract_used;
								}
								continue;
							}
							const int cpuMinScore = task_min_score(task);
							int minScore = cpuMinScore;
							if (gpuMinScoreOk && t < gpuMinScoreSourceScores.size())
							{
								const int gpuScore = gpuMinScoreSourceScores[t];
								const int gpuMinScore =
									fasim_min_score_from_full_score(gpuScore);
								if (gpuScore == task.fullScore &&
								    gpuMinScore == cpuMinScore)
								{
									minScore = gpuMinScore;
									++longQueryStreamingScoreInfoShadowStats
										.gpu_minscore_used;
									if (twoContractRequested)
									{
										++longQueryStreamingScoreInfoShadowStats
											.two_contract_used;
									}
								}
								else
								{
									if (gpuScore != task.fullScore)
									{
										++longQueryStreamingScoreInfoShadowStats
											.gpu_minscore_score_mismatches;
										if (twoContractRequested)
										{
											++longQueryStreamingScoreInfoShadowStats
												.two_contract_score_mismatches;
										}
									}
									if (gpuMinScore != cpuMinScore)
									{
										++longQueryStreamingScoreInfoShadowStats
											.gpu_minscore_min_score_mismatches;
										if (twoContractRequested)
										{
											++longQueryStreamingScoreInfoShadowStats
												.two_contract_min_score_mismatches;
										}
									}
									++longQueryStreamingScoreInfoShadowStats
										.gpu_minscore_fallbacks;
									if (twoContractRequested)
									{
										++longQueryStreamingScoreInfoShadowStats
											.two_contract_fallbacks;
									}
								}
							}
							compactMinScores[t] = minScore;
						}
					}
					longQueryStreamingScoreInfoShadowStats.minscore_seconds +=
						fasim_seconds_since(minScoreStart);
					bool compactOverflow = false;
					PreAlignCudaBatchResult columnResult;
					PreAlignCudaBatchResult reduceResult;
					PreAlignCudaBatchResult compactResult;
					std::string compactError;
					std::vector<int> debugColumnMaxima;
					const bool debugStreamingColumns =
						fasim_long_query_streaming_scoreinfo_debug_columns_runtime();
					auto build_scalar_column_scores = [](
						const std::string &query,
						const std::string &target,
						std::vector<int> &columnScores)
					{
						const int matchScore = 5;
						const int mismatchPenalty = 4;
						const int gapOpen = 16;
						const int gapExtend = 4;
						columnScores.assign(target.size(), 0);
						std::vector<int> prev(query.size() + 1, 0);
						std::vector<int> curr(query.size() + 1, 0);
						std::vector<int> e(query.size() + 1, 0);
						for (size_t j = 1; j <= target.size(); ++j)
						{
							int f = 0;
							int colMax = 0;
							curr[0] = 0;
							for (size_t i = 1; i <= query.size(); ++i)
							{
								const char q =
									static_cast<char>(toupper(static_cast<unsigned char>(
										query[i - 1])));
								const char tbase =
									static_cast<char>(toupper(static_cast<unsigned char>(
										target[j - 1])));
								const bool match =
									q == tbase || (q == 'U' && tbase == 'T') ||
									(q == 'T' && tbase == 'U');
								const int subScore = match ? matchScore : -mismatchPenalty;
								e[i] = std::max(0, std::max(e[i] - gapExtend,
								                         prev[i] - gapOpen));
								f = std::max(0, std::max(f - gapExtend,
								                         curr[i - 1] - gapOpen));
								const int h = std::max(
									0,
									std::max(prev[i - 1] + subScore, std::max(e[i], f)));
								curr[i] = h;
								if (h > colMax)
								{
									colMax = h;
								}
							}
							columnScores[j - 1] = colMax;
							prev.swap(curr);
							std::fill(curr.begin(), curr.end(), 0);
						}
					};
					const auto gpuCallStart = std::chrono::steady_clock::now();
					bool compactOk = false;
					bool fusedMinScoreOk = false;
					if (fusedMinScoreRequested)
					{
						const auto fusedStart = std::chrono::steady_clock::now();
						compactOk =
							prealign_cuda_find_streaming_scoreinfo_batch_pruned_fused_minscore(
								legacyByteMode ?
									streamingScoreInfoLegacyByteCudaQuery :
									cudaQueries[0],
								encodedTargets.data(),
								static_cast<int>(tasks.size()),
								currentTargetLength,
								maxPerTask,
								&compactScoreInfos,
								&compactCounts,
								&compactInputCounts,
								&gpuMinScoreSourceScores,
								&compactMinScores,
								&compactOverflow,
								&columnResult,
								&reduceResult,
								&compactResult,
								legacyByteMode,
								legacyByteSharedMemoryMode,
								debugStreamingColumns ? &debugColumnMaxima : NULL,
								&compactError);
						longQueryStreamingScoreInfoShadowStats
							.fused_minscore_total_seconds +=
							fasim_seconds_since(fusedStart);
						longQueryStreamingScoreInfoShadowStats
							.fused_minscore_kernel_seconds +=
							columnResult.gpuSeconds +
							reduceResult.gpuSeconds +
							compactResult.gpuSeconds;
						if (compactOk && !compactOverflow)
						{
							fusedMinScoreOk = true;
							gpuMinScoreOk = true;
							longQueryStreamingScoreInfoShadowStats
								.fused_minscore_active = 1;
							longQueryStreamingScoreInfoShadowStats
								.fused_minscore_error = "none";
							longQueryStreamingScoreInfoShadowStats
								.gpu_minscore_active = 1;
							longQueryStreamingScoreInfoShadowStats
								.gpu_minscore_error = "none";
						}
						else
						{
							++longQueryStreamingScoreInfoShadowStats
								.fused_minscore_fallbacks;
							longQueryStreamingScoreInfoShadowStats
								.fused_minscore_error =
								compactError.empty() ?
									(compactOverflow ? "overflow" : "launch_failed") :
									compactError;
							compactScoreInfos.clear();
							compactCounts.clear();
							compactInputCounts.clear();
							gpuMinScoreSourceScores.clear();
							compactMinScores.assign(tasks.size(), 0);
							compactOverflow = false;
							columnResult = PreAlignCudaBatchResult();
							reduceResult = PreAlignCudaBatchResult();
							compactResult = PreAlignCudaBatchResult();
							compactError.clear();
						}
					}
					if (!fusedMinScoreOk)
					{
						if (fusedMinScoreRequested)
						{
							const auto fallbackMinScoreStart =
								std::chrono::steady_clock::now();
							for (size_t t = 0; t < tasks.size(); ++t)
							{
								StreamTask &task = tasks[t];
								if (task.minScoreReady)
								{
									++longQueryStreamingScoreInfoShadowStats
										.minscore_cache_hits;
								}
								else
								{
									++longQueryStreamingScoreInfoShadowStats
										.minscore_cache_misses;
								}
								compactMinScores[t] = task_min_score(task);
							}
							longQueryStreamingScoreInfoShadowStats
								.minscore_seconds +=
								fasim_seconds_since(fallbackMinScoreStart);
						}
						compactOk =
							prealign_cuda_find_streaming_scoreinfo_batch_pruned(
								legacyByteMode ?
									streamingScoreInfoLegacyByteCudaQuery :
									cudaQueries[0],
								encodedTargets.data(),
								compactMinScores.data(),
								static_cast<int>(tasks.size()),
								currentTargetLength,
								maxPerTask,
								&compactScoreInfos,
								&compactCounts,
								&compactInputCounts,
								&compactOverflow,
								&columnResult,
								&compactResult,
								legacyByteMode,
								legacyByteSharedMemoryMode,
								debugStreamingColumns ? &debugColumnMaxima : NULL,
								&compactError);
					}
					longQueryStreamingScoreInfoShadowStats.gpu_call_seconds +=
						fasim_seconds_since(gpuCallStart);

					++longQueryStreamingScoreInfoShadowStats.gpu_batches;
					longQueryStreamingScoreInfoShadowStats.total_seconds +=
						fasim_seconds_since(shadowStart);
					longQueryStreamingScoreInfoShadowStats.kernel_seconds +=
						columnResult.gpuSeconds +
						reduceResult.gpuSeconds +
						compactResult.gpuSeconds;
					longQueryStreamingScoreInfoShadowStats.h2d_seconds +=
						columnResult.h2dSeconds +
						reduceResult.h2dSeconds +
						compactResult.h2dSeconds;
					longQueryStreamingScoreInfoShadowStats.d2h_seconds +=
						columnResult.d2hSeconds +
						reduceResult.d2hSeconds +
						compactResult.d2hSeconds;
					if (twoContractRequested)
					{
						longQueryStreamingScoreInfoShadowStats
							.two_contract_total_seconds +=
							gpuMinScoreWallSeconds +
							fasim_seconds_since(gpuCallStart);
						longQueryStreamingScoreInfoShadowStats
							.two_contract_kernel_seconds +=
							gpuMinScoreKernelSeconds +
							columnResult.gpuSeconds +
							reduceResult.gpuSeconds +
							compactResult.gpuSeconds;
						longQueryStreamingScoreInfoShadowStats
							.two_contract_h2d_seconds +=
							gpuMinScoreH2DSeconds +
							columnResult.h2dSeconds +
							reduceResult.h2dSeconds +
							compactResult.h2dSeconds;
						longQueryStreamingScoreInfoShadowStats
							.two_contract_d2h_seconds +=
							gpuMinScoreD2HSeconds +
							columnResult.d2hSeconds +
							reduceResult.d2hSeconds +
							compactResult.d2hSeconds;
					}

					if (!compactOk || compactOverflow)
					{
						longQueryStreamingScoreInfoShadowStats.unsupported = 1;
						++longQueryStreamingScoreInfoShadowStats.fallback_batches;
						if (twoContractRequested)
						{
							++longQueryStreamingScoreInfoShadowStats
								.two_contract_fallbacks;
						}
						if (compactOverflow)
						{
							++longQueryStreamingScoreInfoShadowStats.overflow_batches;
							longQueryStreamingScoreInfoShadowStats.error = "overflow";
						}
						else if (!compactError.empty())
						{
							longQueryStreamingScoreInfoShadowStats.error = compactError;
						}
						else
						{
							longQueryStreamingScoreInfoShadowStats.error = "launch_failed";
						}
						longQueryStreamingScoreInfoShadowStats.decision =
							"streaming_scoreinfo_shadow_launch_failed";
						if (twoContractRequested)
						{
							longQueryStreamingScoreInfoShadowStats
								.two_contract_error =
								longQueryStreamingScoreInfoShadowStats.error;
							longQueryStreamingScoreInfoShadowStats.decision =
								"two_contract_bridge_shadow_launch_failed";
						}
						return;
					}

					longQueryStreamingScoreInfoShadowStats.active = 1;
					longQueryStreamingScoreInfoShadowStats.unsupported = 0;
					longQueryStreamingScoreInfoShadowStats.gpu_tasks +=
						static_cast<uint64_t>(tasks.size());
					longQueryStreamingScoreInfoShadowStats.error = "none";
					longQueryStreamingScoreInfoShadowStats.decision =
						"streaming_scoreinfo_shadow_active";
					if (twoContractRequested)
					{
						longQueryStreamingScoreInfoShadowStats.two_contract_active = 1;
						longQueryStreamingScoreInfoShadowStats.two_contract_error = "none";
						longQueryStreamingScoreInfoShadowStats.decision =
							twoContractTrustRequested ?
								"two_contract_bridge_trust_active" :
								"two_contract_bridge_shadow_active";
					}
					const auto validationStart = std::chrono::steady_clock::now();
					for (size_t t = 0; t < tasks.size(); ++t)
					{
						const int count = t < compactCounts.size() ? compactCounts[t] : -1;
						if (count < 0 || count > maxPerTask)
						{
							++longQueryStreamingScoreInfoShadowStats.scoreinfo_mismatches;
							continue;
						}
						std::vector<struct StripedSmithWaterman::scoreInfo> gpuScoreInfo;
						gpuScoreInfo.reserve(static_cast<size_t>(count));
						const size_t base = t * static_cast<size_t>(maxPerTask);
						for (int i = 0; i < count; ++i)
						{
							const PreAlignCudaPeak &peak =
								compactScoreInfos[base + static_cast<size_t>(i)];
							gpuScoreInfo.push_back(
								StripedSmithWaterman::scoreInfo(peak.score,
								                                peak.position));
						}
						longQueryStreamingScoreInfoShadowStats.gpu_scoreinfo_groups +=
							static_cast<uint64_t>(gpuScoreInfo.size());

						StreamTask &task = tasks[t];
						int minScore =
							t < compactMinScores.size() ? compactMinScores[t] : 0;
						if (!streamingRealpathTrust && fusedMinScoreOk)
						{
							const auto validationMinScoreStart =
								std::chrono::steady_clock::now();
							minScore = task_min_score(task);
							longQueryStreamingScoreInfoShadowStats
								.validation_minscore_seconds +=
								fasim_seconds_since(validationMinScoreStart);
						}
						if (!streamingRealpathTrust &&
						    (gpuMinScoreHotRequested || fusedMinScoreOk) &&
						    gpuMinScoreOk &&
						    t < gpuMinScoreSourceScores.size())
						{
							const auto validationMinScoreStart =
								std::chrono::steady_clock::now();
							const int cpuMinScore = task_min_score(task);
							longQueryStreamingScoreInfoShadowStats
								.validation_minscore_seconds +=
								fasim_seconds_since(validationMinScoreStart);
							const int gpuScore = gpuMinScoreSourceScores[t];
							const int gpuMinScore =
								(fusedMinScoreOk && t < compactMinScores.size()) ?
									compactMinScores[t] :
									fasim_min_score_from_full_score(gpuScore);
							if (gpuScore != task.fullScore)
							{
								++longQueryStreamingScoreInfoShadowStats
									.gpu_minscore_score_mismatches;
								if (twoContractRequested)
								{
									++longQueryStreamingScoreInfoShadowStats
										.two_contract_score_mismatches;
								}
								if (fusedMinScoreOk)
								{
									++longQueryStreamingScoreInfoShadowStats
										.fused_minscore_score_mismatches;
								}
							}
							if (gpuMinScore != cpuMinScore)
							{
								++longQueryStreamingScoreInfoShadowStats
									.gpu_minscore_min_score_mismatches;
								if (twoContractRequested)
								{
									++longQueryStreamingScoreInfoShadowStats
										.two_contract_min_score_mismatches;
								}
								if (fusedMinScoreOk)
								{
									++longQueryStreamingScoreInfoShadowStats
										.fused_minscore_min_score_mismatches;
								}
							}
							if (fusedMinScoreOk &&
							    gpuScore == task.fullScore &&
							    gpuMinScore == cpuMinScore)
							{
								++longQueryStreamingScoreInfoShadowStats
									.gpu_minscore_used;
								++longQueryStreamingScoreInfoShadowStats
									.fused_minscore_used;
							}
						}
						if (streamingRealpathTrust &&
						    streamingRealpathAllowed &&
						    t < streamingRealpathScoreInfos.size())
						{
							record_broad_scoreinfo_attempt_plan(task, gpuScoreInfo);
							streamingRealpathScoreInfos[t] = gpuScoreInfo;
							streamingRealpathReady[t] = 1;
							continue;
						}
						std::vector<struct StripedSmithWaterman::scoreInfo> cpuScoreInfo;
						std::vector<struct StripedSmithWaterman::scoreInfo> cpuScoreInfoExpected;
						StripedSmithWaterman::Aligner cpuAligner;
						StripedSmithWaterman::Filter cpuFilter;
						StripedSmithWaterman::Alignment cpuAlignment;
						const std::chrono::steady_clock::time_point cpuStart =
							std::chrono::steady_clock::now();
						cpuAligner.preAlign(lncSeq.c_str(),
						                    task.seq2.c_str(),
						                    static_cast<int>(task.seq2.size()),
						                    cpuFilter,
						                    &cpuAlignment,
						                    15,
						                    minScore,
						                    cpuScoreInfo,
						                    5,
						                    -4);
						longQueryStreamingScoreInfoShadowStats.cpu_prealign_seconds +=
							fasim_seconds_since(cpuStart);
						const auto compareStart = std::chrono::steady_clock::now();
						prune_scoreinfo_for_gasal2_top5(cpuScoreInfo,
						                                maxPerTask,
						                                cpuScoreInfoExpected);
						longQueryStreamingScoreInfoShadowStats.cpu_scoreinfo_groups +=
							static_cast<uint64_t>(cpuScoreInfoExpected.size());
							if (!scoreinfo_equal(gpuScoreInfo, cpuScoreInfoExpected))
							{
								++longQueryStreamingScoreInfoShadowStats.scoreinfo_mismatches;
								if (twoContractRequested)
								{
									++longQueryStreamingScoreInfoShadowStats
										.two_contract_scoreinfo_mismatches;
								}
								if (longQueryStreamingScoreInfoShadowStats.first_mismatch_task_index < 0)
								{
									size_t diffIndex = 0;
									const size_t sharedCount =
										std::min(gpuScoreInfo.size(), cpuScoreInfoExpected.size());
									while (diffIndex < sharedCount &&
									       gpuScoreInfo[diffIndex].score ==
										       cpuScoreInfoExpected[diffIndex].score &&
									       gpuScoreInfo[diffIndex].position ==
										       cpuScoreInfoExpected[diffIndex].position)
									{
										++diffIndex;
									}
									const bool countMismatch =
										gpuScoreInfo.size() != cpuScoreInfoExpected.size() &&
										diffIndex == sharedCount;
									longQueryStreamingScoreInfoShadowStats.first_mismatch_task_index =
										static_cast<int64_t>(t);
									longQueryStreamingScoreInfoShadowStats.first_mismatch_global_task =
										static_cast<int64_t>(globalTaskBegin + t);
									longQueryStreamingScoreInfoShadowStats.first_mismatch_diff_index =
										static_cast<int64_t>(diffIndex);
									longQueryStreamingScoreInfoShadowStats.first_mismatch_cpu_count =
										static_cast<int64_t>(cpuScoreInfoExpected.size());
									longQueryStreamingScoreInfoShadowStats.first_mismatch_gpu_count =
										static_cast<int64_t>(gpuScoreInfo.size());
									longQueryStreamingScoreInfoShadowStats.first_mismatch_kind =
										countMismatch ? "count" : "score_position";
									if (diffIndex < cpuScoreInfoExpected.size())
									{
										longQueryStreamingScoreInfoShadowStats.first_mismatch_cpu_score =
											cpuScoreInfoExpected[diffIndex].score;
										longQueryStreamingScoreInfoShadowStats.first_mismatch_cpu_position =
											cpuScoreInfoExpected[diffIndex].position;
									}
									if (diffIndex < gpuScoreInfo.size())
									{
										longQueryStreamingScoreInfoShadowStats.first_mismatch_gpu_score =
											gpuScoreInfo[diffIndex].score;
										longQueryStreamingScoreInfoShadowStats.first_mismatch_gpu_position =
											gpuScoreInfo[diffIndex].position;
									}
									longQueryStreamingScoreInfoShadowStats.first_mismatch_rule =
										static_cast<int64_t>(task.rule);
									longQueryStreamingScoreInfoShadowStats.first_mismatch_strand =
										static_cast<int64_t>(task.strand);
									longQueryStreamingScoreInfoShadowStats.first_mismatch_para =
										static_cast<int64_t>(task.Para);
									longQueryStreamingScoreInfoShadowStats.first_mismatch_dna_start_pos =
										static_cast<int64_t>(task.dnaStartPos);
									longQueryStreamingScoreInfoShadowStats.first_mismatch_target_len =
										static_cast<int64_t>(task.seq2.size());
									longQueryStreamingScoreInfoShadowStats.first_mismatch_min_score =
										static_cast<int64_t>(minScore);
									if (debugStreamingColumns &&
									    !debugColumnMaxima.empty() &&
									    debugColumnMaxima.size() >=
										    (t + 1) * static_cast<size_t>(currentTargetLength))
									{
										std::vector<int> cpuColumnScores;
										std::vector<int> scalarColumnScores;
										StripedSmithWaterman::Aligner cpuColumnAligner;
										StripedSmithWaterman::Filter cpuColumnFilter;
										if (cpuColumnAligner.preAlignColumnScores(
											    lncSeq.c_str(),
											    task.seq2.c_str(),
											    static_cast<int>(task.seq2.size()),
											    cpuColumnFilter,
											    15,
											    minScore,
											    cpuColumnScores))
										{
											build_scalar_column_scores(lncSeq,
											                           task.seq2,
											                           scalarColumnScores);
											const int centerPosition =
												diffIndex < cpuScoreInfoExpected.size() ?
													cpuScoreInfoExpected[diffIndex].position :
													(diffIndex < gpuScoreInfo.size() ?
														gpuScoreInfo[diffIndex].position :
														0);
											int windowStart = centerPosition - 4;
											if (windowStart < 0)
											{
												windowStart = 0;
											}
											int windowEnd = centerPosition + 4;
											if (windowEnd >= static_cast<int>(task.seq2.size()))
											{
												windowEnd = static_cast<int>(task.seq2.size()) - 1;
											}
											auto format_window =
												[&](const std::vector<int> &scores,
												    size_t baseOffset) -> std::string
												{
													std::ostringstream out;
													for (int pos = windowStart; pos <= windowEnd; ++pos)
													{
														if (pos > windowStart)
														{
															out << ",";
														}
														int value = -1;
														if (baseOffset == 0)
														{
															if (pos < static_cast<int>(scores.size()))
															{
																value = scores[static_cast<size_t>(pos)];
															}
														}
														else
														{
															const size_t index =
																baseOffset + static_cast<size_t>(pos);
															if (index < scores.size())
															{
																value = scores[index];
															}
														}
														out << pos << ":" << value;
													}
													return out.str();
												};
											longQueryStreamingScoreInfoShadowStats
												.first_mismatch_column_window_start =
												static_cast<int64_t>(windowStart);
											longQueryStreamingScoreInfoShadowStats
												.first_mismatch_cpu_column_window =
												format_window(cpuColumnScores, 0);
											longQueryStreamingScoreInfoShadowStats
												.first_mismatch_gpu_column_window =
												format_window(debugColumnMaxima,
												              t * static_cast<size_t>(currentTargetLength));
											longQueryStreamingScoreInfoShadowStats
												.first_mismatch_scalar_column_window =
												format_window(scalarColumnScores, 0);
										}
									}
								}
							}
							else if (streamingRealpathAllowed &&
							         t < streamingRealpathScoreInfos.size())
							{
								record_broad_scoreinfo_attempt_plan(task, gpuScoreInfo);
								streamingRealpathScoreInfos[t] = gpuScoreInfo;
								streamingRealpathReady[t] = 1;
							}
						longQueryStreamingScoreInfoShadowStats.compare_seconds +=
							fasim_seconds_since(compareStart);
					}
					longQueryStreamingScoreInfoShadowStats.validation_seconds +=
						fasim_seconds_since(validationStart);
					if (longQueryStreamingScoreInfoShadowStats.scoreinfo_mismatches != 0)
					{
						longQueryStreamingScoreInfoShadowStats.decision =
							"streaming_scoreinfo_shadow_mismatch";
						if (twoContractRequested)
						{
							longQueryStreamingScoreInfoShadowStats.decision =
								"two_contract_bridge_shadow_mismatch";
						}
						if (streamingRealpathAllowed)
						{
							++longQueryStreamingScoreInfoShadowStats.realpath_fallbacks;
							streamingRealpathScoreInfos.clear();
							streamingRealpathReady.clear();
						}
					}
					else if (fusedMinScoreOk &&
					         (longQueryStreamingScoreInfoShadowStats
					              .fused_minscore_score_mismatches != 0 ||
					          longQueryStreamingScoreInfoShadowStats
					              .fused_minscore_min_score_mismatches != 0))
					{
						longQueryStreamingScoreInfoShadowStats.decision =
							"streaming_scoreinfo_fused_minscore_mismatch";
						if (streamingRealpathAllowed)
						{
							++longQueryStreamingScoreInfoShadowStats.realpath_fallbacks;
							streamingRealpathScoreInfos.clear();
							streamingRealpathReady.clear();
						}
					}
					else if (twoContractRequested &&
					         (longQueryStreamingScoreInfoShadowStats
					              .two_contract_score_mismatches != 0 ||
					          longQueryStreamingScoreInfoShadowStats
					              .two_contract_min_score_mismatches != 0))
					{
						longQueryStreamingScoreInfoShadowStats.decision =
							"two_contract_bridge_shadow_mismatch";
					}
				};

				auto run_long_query_exact_column_scoreinfo_shadow = [&]()
				{
					if (longQueryExactColumnScoreInfoShadowStats.requested == 0 ||
					    gasal2QueryLengthSupported ||
					    !paraList.doFastSim)
					{
						return;
					}
					longQueryExactColumnScoreInfoShadowStats.tasks +=
						static_cast<uint64_t>(tasks.size());
					if (currentTargetLength > 0)
					{
						longQueryExactColumnScoreInfoShadowStats.cells +=
							static_cast<uint64_t>(tasks.size()) *
							static_cast<uint64_t>(currentTargetLength);
					}
					if (cudaQueries.empty() ||
					    encodedTargets.empty() ||
					    currentTargetLength <= 0 ||
					    tasks.empty())
					{
						++longQueryExactColumnScoreInfoShadowStats.fallback_batches;
						if (longQueryExactColumnScoreInfoShadowStats.error == "none")
						{
							longQueryExactColumnScoreInfoShadowStats.error = "cuda_query_or_batch_unavailable";
						}
						return;
					}

					const int maxPerTask =
						fasim_top5_gasal2_scoreinfo_prune_max_per_task_runtime() > 0 ?
							fasim_top5_gasal2_scoreinfo_prune_max_per_task_runtime() :
							fasim_exact_column_scoreinfo_gpu_max_per_task_runtime();
					longQueryExactColumnScoreInfoShadowStats.max_per_task =
						static_cast<uint64_t>(maxPerTask);
					if (maxPerTask <= 0)
					{
						++longQueryExactColumnScoreInfoShadowStats.fallback_batches;
						longQueryExactColumnScoreInfoShadowStats.error = "invalid_max_per_task";
						return;
					}

					PreAlignCudaResourceLimits resourceLimits;
					std::string resourceError;
					if (prealign_cuda_query_resource_limits(cudaQueries[0],
					                                        &resourceLimits,
					                                        &resourceError))
					{
						longQueryExactColumnScoreInfoShadowStats.required_smem_bytes =
							static_cast<uint64_t>(resourceLimits.requiredDynamicSmemBytes);
						longQueryExactColumnScoreInfoShadowStats.default_smem_limit_bytes =
							static_cast<uint64_t>(resourceLimits.defaultDynamicSmemLimitBytes);
						longQueryExactColumnScoreInfoShadowStats.optin_smem_limit_bytes =
							static_cast<uint64_t>(resourceLimits.optinDynamicSmemLimitBytes);
						longQueryExactColumnScoreInfoShadowStats.resource_fit =
							resourceLimits.resourceFit ? 1ULL : 0ULL;
					}
					else if (!resourceError.empty())
					{
						longQueryExactColumnScoreInfoShadowStats.error = resourceError;
					}
					const bool shadowSmemOptinRequested =
						fasim_long_query_exact_column_scoreinfo_shadow_smem_optin_runtime();
					longQueryExactColumnScoreInfoShadowStats.smem_optin_requested =
						shadowSmemOptinRequested ? 1ULL : 0ULL;
					if (shadowSmemOptinRequested &&
					    longQueryExactColumnScoreInfoShadowStats.required_smem_bytes != 0 &&
					    longQueryExactColumnScoreInfoShadowStats.required_smem_bytes >
						longQueryExactColumnScoreInfoShadowStats.default_smem_limit_bytes &&
					    longQueryExactColumnScoreInfoShadowStats.required_smem_bytes <=
						longQueryExactColumnScoreInfoShadowStats.optin_smem_limit_bytes)
					{
						longQueryExactColumnScoreInfoShadowStats.smem_optin_active = 1;
					}

					const auto shadowStart = std::chrono::steady_clock::now();
					std::vector<PreAlignCudaPeak> compactScoreInfos;
					std::vector<int> compactCounts;
					std::vector<int> compactInputCounts;
					bool compactOverflow = false;
					PreAlignCudaBatchResult columnResult;
					PreAlignCudaBatchResult compactResult;
					std::string compactError;
					const bool compactOk =
						prealign_cuda_find_column_scoreinfo_batch_pruned(
							cudaQueries[0],
							encodedTargets.data(),
							static_cast<int>(tasks.size()),
							currentTargetLength,
							maxPerTask,
							shadowSmemOptinRequested,
							&compactScoreInfos,
							&compactCounts,
							&compactInputCounts,
							&compactOverflow,
							&columnResult,
							&compactResult,
							&compactError);

					++longQueryExactColumnScoreInfoShadowStats.gpu_batches;
					longQueryExactColumnScoreInfoShadowStats.total_seconds +=
						fasim_seconds_since(shadowStart);
					longQueryExactColumnScoreInfoShadowStats.kernel_seconds +=
						columnResult.gpuSeconds + compactResult.gpuSeconds;
					longQueryExactColumnScoreInfoShadowStats.h2d_seconds +=
						columnResult.h2dSeconds + compactResult.h2dSeconds;
					longQueryExactColumnScoreInfoShadowStats.d2h_seconds +=
						columnResult.d2hSeconds + compactResult.d2hSeconds;

					if (!compactOk || compactOverflow)
					{
						++longQueryExactColumnScoreInfoShadowStats.fallback_batches;
						if (compactOverflow)
						{
							++longQueryExactColumnScoreInfoShadowStats.overflow_batches;
							longQueryExactColumnScoreInfoShadowStats.error = "overflow";
						}
						else if (!compactError.empty())
						{
							longQueryExactColumnScoreInfoShadowStats.error = compactError;
						}
						else
						{
							longQueryExactColumnScoreInfoShadowStats.error = "launch_failed";
						}
						return;
					}

					longQueryExactColumnScoreInfoShadowStats.active = 1;
					longQueryExactColumnScoreInfoShadowStats.gpu_tasks +=
						static_cast<uint64_t>(tasks.size());
					longQueryExactColumnScoreInfoShadowStats.error = "none";
					for (size_t t = 0; t < tasks.size(); ++t)
					{
						const int count = t < compactCounts.size() ? compactCounts[t] : -1;
						if (count < 0 || count > maxPerTask)
						{
							++longQueryExactColumnScoreInfoShadowStats.scoreinfo_mismatches;
							continue;
						}
						std::vector<struct StripedSmithWaterman::scoreInfo> gpuScoreInfo;
						gpuScoreInfo.reserve(static_cast<size_t>(count));
						const size_t base = t * static_cast<size_t>(maxPerTask);
						for (int i = 0; i < count; ++i)
						{
							const PreAlignCudaPeak &peak =
								compactScoreInfos[base + static_cast<size_t>(i)];
							gpuScoreInfo.push_back(
								StripedSmithWaterman::scoreInfo(peak.score,
								                                peak.position));
						}
						longQueryExactColumnScoreInfoShadowStats.gpu_scoreinfo_groups +=
							static_cast<uint64_t>(gpuScoreInfo.size());

						StreamTask &task = tasks[t];
						const int minScore = task_min_score(task);
						std::vector<struct StripedSmithWaterman::scoreInfo> cpuScoreInfo;
						std::vector<struct StripedSmithWaterman::scoreInfo> cpuScoreInfoExpected;
						StripedSmithWaterman::Aligner cpuAligner;
						StripedSmithWaterman::Filter cpuFilter;
						StripedSmithWaterman::Alignment cpuAlignment;
						cpuAligner.preAlign(lncSeq.c_str(),
						                    task.seq2.c_str(),
						                    static_cast<int>(task.seq2.size()),
						                    cpuFilter,
						                    &cpuAlignment,
						                    15,
						                    minScore,
						                    cpuScoreInfo,
						                    5,
						                    -4);
						prune_scoreinfo_for_gasal2_top5(cpuScoreInfo,
						                                maxPerTask,
						                                cpuScoreInfoExpected);
						longQueryExactColumnScoreInfoShadowStats.cpu_scoreinfo_groups +=
							static_cast<uint64_t>(cpuScoreInfoExpected.size());
						if (!scoreinfo_equal(gpuScoreInfo, cpuScoreInfoExpected))
						{
							++longQueryExactColumnScoreInfoShadowStats.scoreinfo_mismatches;
						}
					}
				};

				run_long_query_streaming_scoreinfo_shadow();
				run_long_query_exact_column_scoreinfo_shadow();

				if (useCudaBatch)
				{
				const size_t cudaDeviceCount = cudaQueries.size();
				if (cudaDeviceCount == 0)
				{
					useCudaBatch = false;
					maxTasksTotal = 1;
				}
					else if (cudaDeviceCount == 1)
					{
						std::vector<PreAlignCudaPeak> peaks;
						auto run_topk_batch = [&]() -> bool
						{
							PreAlignCudaBatchResult batchResult;
							string cudaError;
							const auto cudaTopkStart = std::chrono::steady_clock::now();
							const bool ok = prealign_cuda_find_topk_column_maxima(cudaQueries[0],
							                                                    encodedTargets.data(),
							                                                    static_cast<int>(tasks.size()),
							                                                    currentTargetLength,
							                                                    topK,
							                                                    &peaks,
							                                                    &batchResult,
							                                                    &cudaError);
							if (phaseTimingEnabled)
							{
								++phaseTiming.cuda_topk_batches;
								phaseTiming.cuda_topk_tasks += static_cast<uint64_t>(tasks.size());
								phaseTiming.cuda_topk_wall_seconds += fasim_seconds_since(cudaTopkStart);
								phaseTiming.cuda_topk_kernel_seconds += batchResult.gpuSeconds;
							}
							if (!ok && debugCuda)
							{
								cerr << "[fasim.cuda.topk] error"
								     << " requests=" << tasks.size()
								     << " error=" << cudaError
								     << endl;
							}
							return ok;
						};
						const bool gpuDpColumnModeActive = gpuDpColumnAutoEffective;
						const bool exactBatchCanRun =
							exactColumnBatchRequested &&
							gpuDpColumnModeActive &&
							!singlePassTopNRequested &&
							cudaDeviceCount == 1;
						const bool deferTopkForExactGasal2 =
							exactBatchCanRun &&
							gasal2LongtargetBatch &&
							!singlePassTopNRequested &&
							!minScoreShadowEnabled;
						if (deferTopkForExactGasal2 && phaseTimingEnabled)
						{
							++phaseTiming.cuda_topk_deferred_batches;
							phaseTiming.cuda_topk_deferred_tasks += static_cast<uint64_t>(tasks.size());
						}
						const bool ok = deferTopkForExactGasal2 || run_topk_batch();
						if (!ok)
						{
							useCudaBatch = false;
						maxTasksTotal = 1;
					}
					else
					{
						std::vector<unsigned char> exactBatchReady;
						std::vector< std::vector<struct StripedSmithWaterman::scoreInfo> > exactBatchScoreInfos;
						if (exactBatchCanRun)
						{
							exactBatchReady.assign(tasks.size(), 0);
							exactBatchScoreInfos.resize(tasks.size());

							bool exactScoreInfoGpuUsed = false;
							const int maxScoreInfosPerTask =
								fasim_exact_column_scoreinfo_gpu_max_per_task_runtime();
							const bool columnPrunedScoreInfoRequested =
								exactScoreInfoGpuColumnPrunedOutputRequested;
							const bool legacyScoreInputsReady =
								legacyScoreGpuReplacementEnabled &&
								legacyScoreCudaQueryReady &&
								legacyEncodedTargets.size() == encodedTargets.size();
								if (exactScoreInfoGpuRequested &&
								    !singlePassTopNRequested &&
								    !minScoreShadowEnabled &&
								    (columnPrunedScoreInfoRequested || legacyScoreInputsReady))
								{
									std::vector<int> legacyGpuScores;
									bool legacyScoreOk = false;
								bool compactOk = false;
								bool compactOverflow = false;
								std::vector<PreAlignCudaPeak> compactScoreInfos;
								std::vector<int> compactCounts;
								std::vector<int> compactInputCounts;
								PreAlignCudaBatchResult compactResult;
								string compactError;
								auto accept_compact_scoreinfos = [&](int compactCapacity,
								                                      const std::vector<int> *minScoresForValidate) -> bool
								{
									if (!compactOk || compactOverflow)
									{
										return false;
									}
									std::vector< std::vector<struct StripedSmithWaterman::scoreInfo> > compactBatchScoreInfos(tasks.size());
									bool compactValid = true;
									{
										FasimScopedSeconds scoreinfoScoped(phaseTimingEnabled,
										                                   &phaseTiming.exact_scoreinfo_build_seconds);
										for (size_t t = 0; t < tasks.size(); ++t)
										{
											const int count = compactCounts[t];
											if (count < 0 || count > compactCapacity)
											{
												compactValid = false;
												break;
											}
											compactBatchScoreInfos[t].reserve(static_cast<size_t>(count));
											const size_t base =
												t * static_cast<size_t>(compactCapacity);
											for (int i = 0; i < count; ++i)
											{
												const PreAlignCudaPeak &peak =
													compactScoreInfos[base + static_cast<size_t>(i)];
												compactBatchScoreInfos[t].push_back(
													StripedSmithWaterman::scoreInfo(peak.score,
													                                peak.position));
											}
										}
									}
									if (compactValid &&
									    exactColumnBatchValidate &&
									    minScoresForValidate != NULL)
									{
										for (size_t t = 0; t < tasks.size(); ++t)
										{
											const StreamTask &task = tasks[t];
											std::vector<struct StripedSmithWaterman::scoreInfo> cpuScoreInfo;
											std::vector<struct StripedSmithWaterman::scoreInfo> cpuScoreInfoExpected;
											StripedSmithWaterman::Aligner cpuAligner;
											StripedSmithWaterman::Filter cpuFilter;
											StripedSmithWaterman::Alignment cpuAlignment;
											cpuAligner.preAlign(lncSeq.c_str(),
											                    task.seq2.c_str(),
											                    static_cast<int>(task.seq2.size()),
											                    cpuFilter,
											                    &cpuAlignment,
											                    15,
											                    (*minScoresForValidate)[t],
											                    cpuScoreInfo,
											                    5,
											                    -4);
											if (exactScoreInfoGpuPrunedOutputRequested)
											{
												prune_scoreinfo_for_gasal2_top5(cpuScoreInfo,
												                                gasal2ScoreInfoPruneMaxPerTask,
												                                cpuScoreInfoExpected);
											}
											else
											{
												cpuScoreInfoExpected = cpuScoreInfo;
											}
											if (!scoreinfo_equal(compactBatchScoreInfos[t], cpuScoreInfoExpected))
											{
												compactValid = false;
												if (debugCuda)
												{
													cerr << "[fasim.cuda.scoreinfo_gpu] validate mismatch"
													     << " task=" << t
													     << " gpu_count=" << compactBatchScoreInfos[t].size()
													     << " cpu_count=" << cpuScoreInfoExpected.size()
													     << " cpu_input_count=" << cpuScoreInfo.size()
													     << endl;
												}
												break;
											}
										}
									}
									if (!compactValid)
									{
										return false;
									}
									if (phaseTimingEnabled &&
									    exactScoreInfoGpuPrunedOutputRequested &&
									    compactInputCounts.size() == tasks.size())
									{
										++phaseTiming.exact_scoreinfo_gpu_pruned_output_batches;
										phaseTiming.scoreinfo_prune_enabled = true;
										phaseTiming.scoreinfo_prune_max_per_task =
											gasal2ScoreInfoPruneMaxPerTask;
										for (size_t t = 0; t < compactBatchScoreInfos.size(); ++t)
										{
											const uint64_t inputGroups =
												static_cast<uint64_t>(std::max(0, compactInputCounts[t]));
											const uint64_t keptGroups =
												static_cast<uint64_t>(compactBatchScoreInfos[t].size());
											const uint64_t prunedGroups =
												inputGroups > keptGroups ? inputGroups - keptGroups : 0;
											phaseTiming.exact_scoreinfo_gpu_pruned_output_input_groups += inputGroups;
											phaseTiming.exact_scoreinfo_gpu_pruned_output_kept_groups += keptGroups;
											phaseTiming.exact_scoreinfo_gpu_pruned_output_pruned_groups += prunedGroups;
											if (prunedGroups > 0)
											{
												++phaseTiming.exact_scoreinfo_gpu_pruned_output_pruned_tasks;
											}
											phaseTiming.scoreinfo_prune_input_groups += inputGroups;
											phaseTiming.scoreinfo_prune_kept_groups += keptGroups;
											phaseTiming.scoreinfo_prune_pruned_groups += prunedGroups;
											if (prunedGroups > 0)
											{
												++phaseTiming.scoreinfo_prune_pruned_tasks;
											}
										}
									}
									exactBatchScoreInfos.swap(compactBatchScoreInfos);
									std::fill(exactBatchReady.begin(), exactBatchReady.end(), 1);
									if (phaseTimingEnabled)
									{
										for (size_t t = 0; t < exactBatchScoreInfos.size(); ++t)
										{
											phaseTiming.exact_scoreinfo_groups +=
												static_cast<uint64_t>(exactBatchScoreInfos[t].size());
										}
									}
									exactScoreInfoGpuUsed = true;
									return true;
								};
								if (columnPrunedScoreInfoRequested)
								{
									PreAlignCudaBatchResult columnResult;
									const auto compactStart = std::chrono::steady_clock::now();
									compactOk =
										prealign_cuda_find_column_scoreinfo_batch_pruned(
											cudaQueries[0],
											encodedTargets.data(),
											static_cast<int>(tasks.size()),
											currentTargetLength,
											gasal2ScoreInfoPruneMaxPerTask,
											false,
											&compactScoreInfos,
											&compactCounts,
											&compactInputCounts,
											&compactOverflow,
											&columnResult,
											&compactResult,
											&compactError);
									if (phaseTimingEnabled)
									{
										++phaseTiming.exact_column_batches;
										phaseTiming.exact_column_tasks += static_cast<uint64_t>(tasks.size());
										phaseTiming.exact_column_cells +=
											static_cast<uint64_t>(tasks.size()) *
											static_cast<uint64_t>(currentTargetLength);
										phaseTiming.exact_column_wall_seconds +=
											columnResult.gpuSeconds + columnResult.h2dSeconds + columnResult.d2hSeconds;
										phaseTiming.exact_column_kernel_seconds += columnResult.gpuSeconds;
										phaseTiming.exact_column_h2d_seconds += columnResult.h2dSeconds;
										phaseTiming.exact_column_d2h_seconds += columnResult.d2hSeconds;
										++phaseTiming.exact_scoreinfo_gpu_batches;
										phaseTiming.exact_scoreinfo_gpu_tasks +=
											static_cast<uint64_t>(tasks.size());
										phaseTiming.exact_scoreinfo_gpu_wall_seconds +=
											fasim_seconds_since(compactStart) -
											(columnResult.gpuSeconds + columnResult.h2dSeconds + columnResult.d2hSeconds);
										phaseTiming.exact_scoreinfo_gpu_kernel_seconds +=
											compactResult.gpuSeconds;
										phaseTiming.exact_scoreinfo_gpu_h2d_seconds +=
											compactResult.h2dSeconds;
										phaseTiming.exact_scoreinfo_gpu_d2h_seconds +=
											compactResult.d2hSeconds;
									}
									if (!accept_compact_scoreinfos(gasal2ScoreInfoPruneMaxPerTask, NULL))
									{
										if (phaseTimingEnabled)
										{
											++phaseTiming.exact_scoreinfo_gpu_fallback_batches;
											if (compactOverflow)
											{
												++phaseTiming.exact_scoreinfo_gpu_overflow_batches;
											}
										}
										if (debugCuda)
										{
											cerr << "[fasim.cuda.column_scoreinfo_gpu] error"
											     << " requests=" << tasks.size()
											     << " overflow=" << (compactOverflow ? 1 : 0)
											     << " error=" << compactError
											     << endl;
										}
										}
									}
									if (!exactScoreInfoGpuUsed &&
									    !legacyScoreOk &&
									    exactScoreInfoGpuRequested &&
									    legacyScoreInputsReady)
									{
										PreAlignCudaBatchResult legacyScoreResult;
										string legacyScoreError;
										const auto legacyScoreStart = std::chrono::steady_clock::now();
										legacyScoreOk =
											prealign_cuda_find_max_scores_batch(
												legacyScoreCudaQuery,
												legacyEncodedTargets.data(),
												static_cast<int>(tasks.size()),
												currentTargetLength,
												&legacyGpuScores,
												&legacyScoreResult,
												&legacyScoreError);
										if (!exactScoreInfoGpuUsed && legacyScoreOk)
										{
											++legacyScoreGpuShadowStats.batches;
											legacyScoreGpuShadowStats.requests +=
												static_cast<uint64_t>(tasks.size());
											legacyScoreGpuShadowStats.cells +=
												static_cast<uint64_t>(tasks.size()) *
												static_cast<uint64_t>(currentTargetLength);
											legacyScoreGpuShadowStats.wall_seconds +=
												fasim_seconds_since(legacyScoreStart);
											legacyScoreGpuShadowStats.kernel_seconds +=
												legacyScoreResult.gpuSeconds;
											legacyScoreGpuShadowStats.h2d_seconds +=
												legacyScoreResult.h2dSeconds;
											legacyScoreGpuShadowStats.d2h_seconds +=
												legacyScoreResult.d2hSeconds;
										}
										else if (debugCuda)
										{
											cerr << "[fasim.legacy_score_gpu_shadow] score error"
											     << " requests=" << tasks.size()
											     << " error=" << legacyScoreError
											     << endl;
										}
									}
									if (legacyScoreOk)
									{
										std::vector<int> minScores(tasks.size(), 0);
										for (size_t t = 0; t < tasks.size(); ++t)
										{
											minScores[t] =
												fasim_min_score_from_full_score(legacyGpuScores[t]);
										}
											if (!compactOk)
											{
												const auto compactStart = std::chrono::steady_clock::now();
												if (exactScoreInfoGpuPrunedOutputRequested)
												{
													compactOk =
														prealign_cuda_find_scoreinfo_batch_pruned(
															cudaQueries[0],
															encodedTargets.data(),
															minScores.data(),
															static_cast<int>(tasks.size()),
															currentTargetLength,
															gasal2ScoreInfoPruneMaxPerTask,
															&compactScoreInfos,
															&compactCounts,
															&compactInputCounts,
															&compactOverflow,
															&compactResult,
															&compactError);
												}
												else
												{
													compactOk =
														prealign_cuda_find_scoreinfo_batch(
															cudaQueries[0],
															encodedTargets.data(),
															minScores.data(),
															static_cast<int>(tasks.size()),
															currentTargetLength,
															maxScoreInfosPerTask,
															&compactScoreInfos,
															&compactCounts,
															&compactOverflow,
															&compactResult,
															&compactError);
												}
												if (phaseTimingEnabled)
												{
													++phaseTiming.exact_scoreinfo_gpu_batches;
													phaseTiming.exact_scoreinfo_gpu_tasks +=
														static_cast<uint64_t>(tasks.size());
												phaseTiming.exact_scoreinfo_gpu_wall_seconds +=
													fasim_seconds_since(compactStart);
												phaseTiming.exact_scoreinfo_gpu_kernel_seconds +=
													compactResult.gpuSeconds;
												phaseTiming.exact_scoreinfo_gpu_h2d_seconds +=
													compactResult.h2dSeconds;
												phaseTiming.exact_scoreinfo_gpu_d2h_seconds +=
													compactResult.d2hSeconds;
											}
										}
											if (compactOk && !compactOverflow)
											{
												std::vector< std::vector<struct StripedSmithWaterman::scoreInfo> > compactBatchScoreInfos(tasks.size());
											bool compactValid = true;
											{
												FasimScopedSeconds scoreinfoScoped(phaseTimingEnabled,
												                                   &phaseTiming.exact_scoreinfo_build_seconds);
												for (size_t t = 0; t < tasks.size(); ++t)
												{
													const int count = compactCounts[t];
													const int compactCapacity = exactScoreInfoGpuPrunedOutputRequested ?
														gasal2ScoreInfoPruneMaxPerTask :
														maxScoreInfosPerTask;
													if (count < 0 || count > compactCapacity)
													{
														compactValid = false;
														break;
													}
													compactBatchScoreInfos[t].reserve(static_cast<size_t>(count));
													const size_t base =
														t * static_cast<size_t>(compactCapacity);
													for (int i = 0; i < count; ++i)
													{
														const PreAlignCudaPeak &peak =
															compactScoreInfos[base + static_cast<size_t>(i)];
														compactBatchScoreInfos[t].push_back(
														StripedSmithWaterman::scoreInfo(peak.score,
														                                peak.position));
												}
											}
										}
											if (compactValid && exactColumnBatchValidate)
											{
												for (size_t t = 0; t < tasks.size(); ++t)
												{
													const StreamTask &task = tasks[t];
													std::vector<struct StripedSmithWaterman::scoreInfo> cpuScoreInfo;
													std::vector<struct StripedSmithWaterman::scoreInfo> cpuScoreInfoExpected;
													StripedSmithWaterman::Aligner cpuAligner;
													StripedSmithWaterman::Filter cpuFilter;
													StripedSmithWaterman::Alignment cpuAlignment;
													cpuAligner.preAlign(lncSeq.c_str(),
													                    task.seq2.c_str(),
												                    static_cast<int>(task.seq2.size()),
												                    cpuFilter,
												                    &cpuAlignment,
												                    15,
												                    minScores[t],
													                    cpuScoreInfo,
													                    5,
													                    -4);
													if (exactScoreInfoGpuPrunedOutputRequested)
													{
														prune_scoreinfo_for_gasal2_top5(cpuScoreInfo,
														                                gasal2ScoreInfoPruneMaxPerTask,
														                                cpuScoreInfoExpected);
													}
													else
													{
														cpuScoreInfoExpected = cpuScoreInfo;
													}
													if (!scoreinfo_equal(compactBatchScoreInfos[t], cpuScoreInfoExpected))
													{
														compactValid = false;
														if (debugCuda)
														{
															cerr << "[fasim.cuda.scoreinfo_gpu] validate mismatch"
															     << " task=" << t
															     << " gpu_count=" << compactBatchScoreInfos[t].size()
															     << " cpu_count=" << cpuScoreInfoExpected.size()
															     << " cpu_input_count=" << cpuScoreInfo.size()
															     << endl;
														}
														break;
													}
												}
											}
											if (compactValid)
											{
												if (phaseTimingEnabled &&
												    exactScoreInfoGpuPrunedOutputRequested &&
												    compactInputCounts.size() == tasks.size())
												{
													++phaseTiming.exact_scoreinfo_gpu_pruned_output_batches;
													phaseTiming.scoreinfo_prune_enabled = true;
													phaseTiming.scoreinfo_prune_max_per_task =
														gasal2ScoreInfoPruneMaxPerTask;
													for (size_t t = 0; t < compactBatchScoreInfos.size(); ++t)
													{
														const uint64_t inputGroups =
															static_cast<uint64_t>(std::max(0, compactInputCounts[t]));
														const uint64_t keptGroups =
															static_cast<uint64_t>(compactBatchScoreInfos[t].size());
														const uint64_t prunedGroups =
															inputGroups > keptGroups ? inputGroups - keptGroups : 0;
														phaseTiming.exact_scoreinfo_gpu_pruned_output_input_groups += inputGroups;
														phaseTiming.exact_scoreinfo_gpu_pruned_output_kept_groups += keptGroups;
														phaseTiming.exact_scoreinfo_gpu_pruned_output_pruned_groups += prunedGroups;
														if (prunedGroups > 0)
														{
															++phaseTiming.exact_scoreinfo_gpu_pruned_output_pruned_tasks;
														}
														phaseTiming.scoreinfo_prune_input_groups += inputGroups;
														phaseTiming.scoreinfo_prune_kept_groups += keptGroups;
														phaseTiming.scoreinfo_prune_pruned_groups += prunedGroups;
														if (prunedGroups > 0)
														{
															++phaseTiming.scoreinfo_prune_pruned_tasks;
														}
													}
												}
												exactBatchScoreInfos.swap(compactBatchScoreInfos);
												std::fill(exactBatchReady.begin(), exactBatchReady.end(), 1);
											legacyScoreGpuShadowStats.replacement_used +=
												static_cast<uint64_t>(tasks.size());
											if (phaseTimingEnabled)
											{
												for (size_t t = 0; t < exactBatchScoreInfos.size(); ++t)
												{
													phaseTiming.exact_scoreinfo_groups +=
														static_cast<uint64_t>(exactBatchScoreInfos[t].size());
												}
											}
											exactScoreInfoGpuUsed = true;
										}
										else if (phaseTimingEnabled)
										{
											++phaseTiming.exact_scoreinfo_gpu_fallback_batches;
										}
									}
									else
									{
										if (phaseTimingEnabled)
										{
											++phaseTiming.exact_scoreinfo_gpu_fallback_batches;
											if (compactOverflow)
											{
												++phaseTiming.exact_scoreinfo_gpu_overflow_batches;
											}
										}
										if (debugCuda)
										{
											cerr << "[fasim.cuda.scoreinfo_gpu] error"
											     << " requests=" << tasks.size()
											     << " overflow=" << (compactOverflow ? 1 : 0)
											     << " error=" << compactError
											     << endl;
										}
									}
									}
								}
							if (!exactScoreInfoGpuUsed)
							{
								std::vector<int> batchColumnScores;
								PreAlignCudaBatchResult exactBatchResult;
								string exactBatchError;
								const auto exactBatchStart = std::chrono::steady_clock::now();
								const bool exactBatchOk =
									prealign_cuda_find_column_maxima_batch(cudaQueries[0],
									                                        encodedTargets.data(),
									                                        static_cast<int>(tasks.size()),
									                                        currentTargetLength,
									                                        &batchColumnScores,
									                                        &exactBatchResult,
									                                        &exactBatchError);
								if (phaseTimingEnabled)
								{
									++phaseTiming.exact_column_batches;
									phaseTiming.exact_column_tasks += static_cast<uint64_t>(tasks.size());
									phaseTiming.exact_column_cells +=
										static_cast<uint64_t>(tasks.size()) * static_cast<uint64_t>(currentTargetLength);
									phaseTiming.exact_column_wall_seconds += fasim_seconds_since(exactBatchStart);
									phaseTiming.exact_column_kernel_seconds += exactBatchResult.gpuSeconds;
									phaseTiming.exact_column_h2d_seconds += exactBatchResult.h2dSeconds;
									phaseTiming.exact_column_d2h_seconds += exactBatchResult.d2hSeconds;
								}
								if (!exactBatchOk)
								{
								if (debugCuda)
								{
									cerr << "[fasim.cuda.exact_batch] error"
									     << " requests=" << tasks.size()
									     << " error=" << exactBatchError
									     << endl;
									}
								}
									else
									{
										std::vector<int> legacyGpuScores;
										if (legacyScoreGpuShadowEnabled &&
										    legacyScoreCudaQueryReady &&
										    legacyEncodedTargets.size() == encodedTargets.size())
										{
											PreAlignCudaBatchResult legacyScoreResult;
											string legacyScoreError;
											const auto legacyScoreStart = std::chrono::steady_clock::now();
											const bool legacyScoreOk =
												prealign_cuda_find_max_scores_batch(
													legacyScoreCudaQuery,
													legacyEncodedTargets.data(),
													static_cast<int>(tasks.size()),
													currentTargetLength,
													&legacyGpuScores,
													&legacyScoreResult,
													&legacyScoreError);
											if (legacyScoreOk)
											{
												++legacyScoreGpuShadowStats.batches;
												legacyScoreGpuShadowStats.requests +=
													static_cast<uint64_t>(tasks.size());
												legacyScoreGpuShadowStats.cells +=
													static_cast<uint64_t>(tasks.size()) *
													static_cast<uint64_t>(currentTargetLength);
												legacyScoreGpuShadowStats.wall_seconds +=
													fasim_seconds_since(legacyScoreStart);
												legacyScoreGpuShadowStats.kernel_seconds +=
													legacyScoreResult.gpuSeconds;
												legacyScoreGpuShadowStats.h2d_seconds +=
													legacyScoreResult.h2dSeconds;
												legacyScoreGpuShadowStats.d2h_seconds +=
													legacyScoreResult.d2hSeconds;
											}
											else
											{
												legacyGpuScores.clear();
												if (debugCuda)
												{
													cerr << "[fasim.legacy_score_gpu_shadow] score error"
													     << " requests=" << tasks.size()
													     << " error=" << legacyScoreError
													     << endl;
												}
											}
										}
										for (size_t t = 0; t < tasks.size(); ++t)
											{
												StreamTask &task = tasks[t];
												int cpuScore = 0;
												const bool haveLegacyGpuScore = t < legacyGpuScores.size();
												int effectiveScore = 0;
												{
													if (legacyScoreGpuReplacementEnabled && haveLegacyGpuScore)
													{
														effectiveScore = legacyGpuScores[t];
														++legacyScoreGpuShadowStats.replacement_used;
													}
													else
													{
														if (legacyScoreGpuReplacementEnabled)
														{
															++legacyScoreGpuShadowStats.replacement_fallbacks;
														}
														FasimScopedSeconds minScoreScoped(phaseTimingEnabled,
														                                  &phaseTiming.exact_min_score_seconds);
														cpuScore = calc_score_once(lncSeq,
														                           task.seq2,
														                           task.dnaStartPos,
														                           task.rule);
														effectiveScore = cpuScore;
													}
												}
												const int minScore = fasim_min_score_from_full_score(effectiveScore);
												if (legacyScoreGpuShadowEnabled &&
												    !legacyScoreGpuReplacementEnabled &&
												    haveLegacyGpuScore)
												{
													const int gpuLegacyScore = legacyGpuScores[t];
													const int gpuLegacyMinScore =
														fasim_min_score_from_full_score(gpuLegacyScore);
													if (gpuLegacyScore != cpuScore)
													{
														++legacyScoreGpuShadowStats.mismatches;
														if (gpuLegacyScore > cpuScore)
														{
															++legacyScoreGpuShadowStats.gpu_gt_cpu;
														}
														else
														{
															++legacyScoreGpuShadowStats.gpu_lt_cpu;
														}
														legacyScoreGpuShadowStats.max_abs_diff =
															std::max(legacyScoreGpuShadowStats.max_abs_diff,
															         abs(gpuLegacyScore - cpuScore));
														fasim_note_legacy_score_gpu_shadow_first(
															legacyScoreGpuShadowStats,
															legacyScoreGpuShadowStats.requests -
																static_cast<uint64_t>(tasks.size()) +
																static_cast<uint64_t>(t) + 1,
															task.rule,
															task.strand,
															task.Para,
															task.seq2.size(),
															cpuScore,
															gpuLegacyScore);
													}
													if (gpuLegacyMinScore != minScore)
													{
														++legacyScoreGpuShadowStats.min_score_mismatches;
													}
												}
												const int *rowBegin =
													batchColumnScores.data() + t * static_cast<size_t>(currentTargetLength);
												if (minScoreShadowEnabled)
												{
													FasimScopedSeconds shadowScoped(true, &minScoreShadowStats.seconds);
													const size_t columnCount =
														static_cast<size_t>(currentTargetLength);
													const int gpuRowScore =
														fasim_row_max_raw(rowBegin, columnCount);
													const int gpuLegacyRowScore =
														fasim_row_max_with_legacy_byte_overflow(rowBegin, columnCount);
													const size_t peakBase = t * static_cast<size_t>(topK);
													const int topkScore = peaks.empty() ? 0 : peaks[peakBase].score;
													const int gpuRowMinScore =
														fasim_min_score_from_full_score(gpuRowScore);
													const int gpuLegacyRowMinScore =
														fasim_min_score_from_full_score(gpuLegacyRowScore);
													const int topkMinScore =
														fasim_min_score_from_full_score(topkScore);
													++minScoreShadowStats.tasks;

													if (gpuRowScore != cpuScore)
													{
														++minScoreShadowStats.gpu_row_score_mismatches;
														if (gpuRowScore > cpuScore)
														{
															++minScoreShadowStats.gpu_row_gt_cpu;
														}
														else
														{
															++minScoreShadowStats.gpu_row_lt_cpu;
														}
														minScoreShadowStats.gpu_row_max_abs_diff =
															std::max(minScoreShadowStats.gpu_row_max_abs_diff,
															         abs(gpuRowScore - cpuScore));
														fasim_note_min_score_shadow_source_first(
															minScoreShadowStats,
															FASIM_MIN_SCORE_SHADOW_SOURCE_GPU_ROW,
															minScoreShadowStats.tasks,
															task.rule,
															task.strand,
															task.Para,
															task.seq2.size(),
															cpuScore,
															minScore,
															gpuRowScore,
															gpuRowMinScore);
														fasim_note_min_score_shadow_first(
															minScoreShadowStats,
															FASIM_MIN_SCORE_SHADOW_SOURCE_GPU_ROW,
															minScoreShadowStats.tasks,
															task.rule,
															task.strand,
															task.Para,
															task.seq2.size(),
															cpuScore,
															minScore,
															gpuRowScore,
															gpuRowMinScore,
															gpuLegacyRowScore,
															gpuLegacyRowMinScore,
															topkScore,
															topkMinScore);
														if (minScoreShadowDebugEnabled &&
														    minScoreShadowDebugPrinted < minScoreShadowDebugLimit)
														{
															++minScoreShadowDebugPrinted;
															StripedSmithWaterman::Aligner debugAligner;
															StripedSmithWaterman::Filter debugFilter;
															StripedSmithWaterman::Alignment debugAlignment;
															debugAligner.Align(lncSeq.c_str(),
															                   task.seq2.c_str(),
															                   static_cast<int>(task.seq2.size()),
															                   debugFilter,
															                   &debugAlignment,
															                   15);
															std::vector<int> cpuColumnScores;
															const bool cpuColumnsOk =
																debugAligner.preAlignColumnScores(
																	lncSeq.c_str(),
																	task.seq2.c_str(),
																	static_cast<int>(task.seq2.size()),
																	debugFilter,
																	15,
																	minScore,
																	cpuColumnScores);
															const int gpuRowPosition =
																fasim_row_max_position_raw(rowBegin, columnCount);
															const size_t nonAcgtCount =
																fasim_count_non_acgt_bases(task.seq2);
															const int cpuColumnMax =
																cpuColumnsOk ? fasim_vector_row_max(cpuColumnScores) : -1;
															const int cpuColumnMaxPosition =
																cpuColumnsOk ? fasim_vector_row_max_position(cpuColumnScores) : -1;
															size_t comparedColumns = 0;
															size_t columnMismatches = 0;
															int firstColumnMismatch = -1;
															int firstColumnGpu = 0;
															int firstColumnCpu = 0;
															int maxColumnAbsDiff = 0;
															int maxColumnAbsDiffPosition = -1;
															if (cpuColumnsOk)
															{
																comparedColumns = std::min(columnCount, cpuColumnScores.size());
																for (size_t ci = 0; ci < comparedColumns; ++ci)
																{
																	const int gpuScore = rowBegin[ci];
																	const int cpuColumnScore = cpuColumnScores[ci];
																	if (gpuScore != cpuColumnScore)
																	{
																		if (firstColumnMismatch < 0)
																		{
																			firstColumnMismatch = static_cast<int>(ci);
																			firstColumnGpu = gpuScore;
																			firstColumnCpu = cpuColumnScore;
																		}
																		++columnMismatches;
																		const int absDiff = abs(gpuScore - cpuColumnScore);
																		if (absDiff > maxColumnAbsDiff)
																		{
																			maxColumnAbsDiff = absDiff;
																			maxColumnAbsDiffPosition = static_cast<int>(ci);
																		}
																	}
																}
															}
															cerr << "[fasim.min_score_shadow] raw mismatch"
															     << " ordinal=" << minScoreShadowStats.tasks
															     << " local_task=" << t
															     << " rule=" << task.rule
															     << " strand=" << task.strand
															     << " para=" << task.Para
															     << " target_len=" << task.seq2.size()
															     << " non_acgt=" << nonAcgtCount
															     << " cpu_calc_score_once=" << cpuScore
															     << " cpu_align_score=" << debugAlignment.sw_score
															     << " cpu_column_ok=" << (cpuColumnsOk ? 1 : 0)
															     << " cpu_column_max=" << cpuColumnMax
															     << " cpu_column_max_pos=" << cpuColumnMaxPosition
															     << " gpu_row_max=" << gpuRowScore
															     << " gpu_row_max_pos=" << gpuRowPosition
															     << " topk_score=" << topkScore
															     << " topk_minScore=" << topkMinScore
															     << " cpu_minScore=" << minScore
															     << " compared_columns=" << comparedColumns
															     << " column_mismatches=" << columnMismatches
															     << " first_column_mismatch=" << firstColumnMismatch
															     << " first_column_gpu=" << firstColumnGpu
															     << " first_column_cpu=" << firstColumnCpu
															     << " max_column_abs_diff=" << maxColumnAbsDiff
															     << " max_column_abs_diff_pos=" << maxColumnAbsDiffPosition
															     << endl;
														}
													}
													if (gpuRowMinScore != minScore)
													{
														++minScoreShadowStats.gpu_row_min_score_mismatches;
													}

													if (gpuLegacyRowScore != cpuScore)
													{
														++minScoreShadowStats.gpu_legacy_row_score_mismatches;
														if (gpuLegacyRowScore > cpuScore)
														{
															++minScoreShadowStats.gpu_legacy_row_gt_cpu;
														}
														else
														{
															++minScoreShadowStats.gpu_legacy_row_lt_cpu;
														}
														minScoreShadowStats.gpu_legacy_row_max_abs_diff =
															std::max(minScoreShadowStats.gpu_legacy_row_max_abs_diff,
															         abs(gpuLegacyRowScore - cpuScore));
														fasim_note_min_score_shadow_source_first(
															minScoreShadowStats,
															FASIM_MIN_SCORE_SHADOW_SOURCE_GPU_LEGACY_ROW,
															minScoreShadowStats.tasks,
															task.rule,
															task.strand,
															task.Para,
															task.seq2.size(),
															cpuScore,
															minScore,
															gpuLegacyRowScore,
															gpuLegacyRowMinScore);
														fasim_note_min_score_shadow_first(
															minScoreShadowStats,
															FASIM_MIN_SCORE_SHADOW_SOURCE_GPU_LEGACY_ROW,
															minScoreShadowStats.tasks,
															task.rule,
															task.strand,
															task.Para,
															task.seq2.size(),
															cpuScore,
															minScore,
															gpuRowScore,
															gpuRowMinScore,
															gpuLegacyRowScore,
															gpuLegacyRowMinScore,
															topkScore,
															topkMinScore);
													}
													if (gpuLegacyRowMinScore != minScore)
													{
														++minScoreShadowStats.gpu_legacy_row_min_score_mismatches;
													}

													if (topkScore != cpuScore)
													{
														++minScoreShadowStats.topk_score_mismatches;
														if (topkScore > cpuScore)
														{
															++minScoreShadowStats.topk_gt_cpu;
														}
														else
														{
															++minScoreShadowStats.topk_lt_cpu;
														}
														minScoreShadowStats.topk_max_abs_diff =
															std::max(minScoreShadowStats.topk_max_abs_diff,
															         abs(topkScore - cpuScore));
														fasim_note_min_score_shadow_source_first(
															minScoreShadowStats,
															FASIM_MIN_SCORE_SHADOW_SOURCE_TOPK,
															minScoreShadowStats.tasks,
															task.rule,
															task.strand,
															task.Para,
															task.seq2.size(),
															cpuScore,
															minScore,
															topkScore,
															topkMinScore);
														fasim_note_min_score_shadow_first(
															minScoreShadowStats,
															FASIM_MIN_SCORE_SHADOW_SOURCE_TOPK,
															minScoreShadowStats.tasks,
															task.rule,
															task.strand,
															task.Para,
															task.seq2.size(),
															cpuScore,
															minScore,
															gpuRowScore,
															gpuRowMinScore,
															gpuLegacyRowScore,
															gpuLegacyRowMinScore,
															topkScore,
															topkMinScore);
													}
													if (topkMinScore != minScore)
													{
														++minScoreShadowStats.topk_min_score_mismatches;
													}
												}
												{
													FasimScopedSeconds scoreinfoScoped(phaseTimingEnabled,
													                                   &phaseTiming.exact_scoreinfo_build_seconds);
													build_scoreinfo_from_column_scores_row(rowBegin,
													                                      static_cast<size_t>(currentTargetLength),
													                                      minScore,
													                                      exactBatchScoreInfos[t]);
												}
												if (phaseTimingEnabled)
												{
													phaseTiming.exact_scoreinfo_groups +=
												static_cast<uint64_t>(exactBatchScoreInfos[t].size());
										}

										if (exactColumnBatchValidate)
									{
										std::vector<struct StripedSmithWaterman::scoreInfo> cpuScoreInfo;
										StripedSmithWaterman::Aligner cpuAligner;
										StripedSmithWaterman::Filter cpuFilter;
										StripedSmithWaterman::Alignment cpuAlignment;
										cpuAligner.preAlign(lncSeq.c_str(),
										                    task.seq2.c_str(),
										                    static_cast<int>(task.seq2.size()),
										                    cpuFilter,
										                    &cpuAlignment,
										                    15,
										                    minScore,
										                    cpuScoreInfo,
										                    5,
										                    -4);
										if (!scoreinfo_equal(exactBatchScoreInfos[t], cpuScoreInfo))
										{
											if (debugCuda)
											{
												cerr << "[fasim.cuda.exact_batch] validate mismatch"
												     << " task=" << t
												     << " gpu_count=" << exactBatchScoreInfos[t].size()
												     << " cpu_count=" << cpuScoreInfo.size()
												     << endl;
											}
												if (debugCuda && exactColumnBatchDebugColumns)
												{
													std::vector<int> rowScores(rowBegin, rowBegin + currentTargetLength);
													apply_legacy_prealign_byte_overflow(rowScores);
													std::vector<int> cpuColumnScores;
												const bool cpuColumnsOk =
													cpuAligner.preAlignColumnScores(lncSeq.c_str(),
													                               task.seq2.c_str(),
													                               static_cast<int>(task.seq2.size()),
													                               cpuFilter,
													                               15,
													                               minScore,
													                               cpuColumnScores);
												if (!cpuColumnsOk)
												{
													cerr << "[fasim.cuda.exact_batch] column debug failed"
													     << " task=" << t
													     << endl;
												}
												else
												{
													const size_t compareCount =
														std::min(rowScores.size(), cpuColumnScores.size());
													size_t scoreMismatchCount = 0;
													size_t gpuOnlyAboveThreshold = 0;
													size_t cpuOnlyAboveThreshold = 0;
													int firstMismatch = -1;
													int firstMismatchGpu = 0;
													int firstMismatchCpu = 0;
													int maxAbsDiff = 0;
													int maxAbsDiffPosition = -1;
													for (size_t ci = 0; ci < compareCount; ++ci)
													{
														const int gpuScore = rowScores[ci];
														const int cpuScore = cpuColumnScores[ci];
														if (gpuScore != cpuScore)
														{
															if (firstMismatch < 0)
															{
																firstMismatch = static_cast<int>(ci);
																firstMismatchGpu = gpuScore;
																firstMismatchCpu = cpuScore;
															}
															++scoreMismatchCount;
															const int absDiff = abs(gpuScore - cpuScore);
															if (absDiff > maxAbsDiff)
															{
																maxAbsDiff = absDiff;
																maxAbsDiffPosition = static_cast<int>(ci);
															}
														}
														if (gpuScore > minScore && cpuScore <= minScore)
														{
															++gpuOnlyAboveThreshold;
														}
														if (cpuScore > minScore && gpuScore <= minScore)
														{
															++cpuOnlyAboveThreshold;
														}
													}
													cerr << "[fasim.cuda.exact_batch] column diff"
													     << " task=" << t
													     << " rule=" << task.rule
													     << " strand=" << task.strand
													     << " para=" << task.Para
													     << " target_len=" << task.seq2.size()
													     << " minScore=" << minScore
													     << " compared_columns=" << compareCount
													     << " gpu_columns=" << rowScores.size()
													     << " cpu_columns=" << cpuColumnScores.size()
													     << " score_mismatches=" << scoreMismatchCount
													     << " first_mismatch=" << firstMismatch
													     << " first_gpu=" << firstMismatchGpu
													     << " first_cpu=" << firstMismatchCpu
													     << " max_abs_diff=" << maxAbsDiff
													     << " max_abs_diff_position=" << maxAbsDiffPosition
													     << " gpu_only_above_threshold=" << gpuOnlyAboveThreshold
													     << " cpu_only_above_threshold=" << cpuOnlyAboveThreshold
													     << endl;
													if (firstMismatch >= 0)
													{
														const int begin = std::max(0, firstMismatch - 4);
														const int end = std::min(static_cast<int>(compareCount), firstMismatch + 5);
														for (int ci = begin; ci < end; ++ci)
														{
															cerr << "[fasim.cuda.exact_batch] column"
															     << " task=" << t
															     << " pos=" << ci
															     << " gpu=" << rowScores[static_cast<size_t>(ci)]
															     << " cpu=" << cpuColumnScores[static_cast<size_t>(ci)]
															     << endl;
														}
													}
												}
											}
											continue;
										}
										}
										exactBatchReady[t] = 1;
									}
								}
							}
							}

								if (exactBatchCanRun &&
							    !exactBatchReady.empty() &&
							    gasal2LongtargetBatch &&
							    std::find(exactBatchReady.begin(), exactBatchReady.end(), 0) == exactBatchReady.end())
						{
							std::vector< std::vector<triplex> > gasalExactTriplexes;
							if (extend_tasks_with_gasal2_batch(exactBatchScoreInfos,
							                                   gasalExactTriplexes,
							                                   true,
							                                   exactScoreInfoGpuPrunedOutputRequested))
							{
				for (size_t t = 0; t < tasks.size(); ++t)
				{
					taskTriplexes = gasalExactTriplexes[t];
					write_task_triplexes(tasks[t]);
				}
				finalize_attempt_consumer_shadow();
				finalize_emission_only_consumer_shadow();
				tasks.clear();
				encodedTargets.clear();
				legacyEncodedTargets.clear();
				currentTargetLength = -1;
				return;
								}
							}

							if (peaks.empty() && !run_topk_batch())
							{
								useCudaBatch = false;
								maxTasksTotal = 1;
							}
							else
							{
								if (singlePassTopNRequested && gasal2LongtargetBatch)
								{
									std::vector< std::vector<struct StripedSmithWaterman::scoreInfo> > topnScoreInfos(tasks.size());
									{
										FasimScopedSeconds scoreinfoScoped(phaseTimingEnabled,
										                                   &phaseTiming.exact_scoreinfo_build_seconds);
										for (size_t t = 0; t < tasks.size(); ++t)
										{
											const size_t base = t * static_cast<size_t>(topK);
											const int maxScore = peaks[base].score;
											const int minScore = fasim_min_score_from_full_score(maxScore);
											build_scoreinfo_from_gpu_peaks(peaks.data() + base,
											                               minScore,
											                               topnScoreInfos[t]);
										}
									}
									if (phaseTimingEnabled)
									{
										++phaseTiming.single_pass_topn_batches;
										phaseTiming.single_pass_topn_tasks +=
											static_cast<uint64_t>(tasks.size());
										for (size_t t = 0; t < topnScoreInfos.size(); ++t)
										{
											const uint64_t groups =
												static_cast<uint64_t>(topnScoreInfos[t].size());
											phaseTiming.single_pass_topn_scoreinfo_groups += groups;
											phaseTiming.exact_scoreinfo_groups += groups;
										}
									}
									std::vector< std::vector<triplex> > gasalTopnTriplexes;
									if (extend_tasks_with_gasal2_batch(topnScoreInfos,
									                                   gasalTopnTriplexes,
									                                   true,
									                                   true))
									{
										for (size_t t = 0; t < tasks.size(); ++t)
										{
											taskTriplexes = gasalTopnTriplexes[t];
											write_task_triplexes(tasks[t]);
										}
										tasks.clear();
										encodedTargets.clear();
										legacyEncodedTargets.clear();
										currentTargetLength = -1;
										return;
									}
								}
							if (extendThreadCount <= 1 || tasks.size() <= 1)
							{
								for (size_t t = 0; t < tasks.size(); ++t)
								{
								const StreamTask &task = tasks[t];
								const size_t base = t * static_cast<size_t>(topK);
								const int maxScore = peaks[base].score;
								const int minScore = static_cast<int>(static_cast<double>(maxScore) * 0.8);

								if (!exactBatchReady.empty() && exactBatchReady[t])
								{
									finalScoreInfo = exactBatchScoreInfos[t];
								}
								else
								{
									build_scoreinfo_from_gpu_peaks(peaks.data() + base, minScore, finalScoreInfo);
								}

								if (debugCuda && t == 0)
								{
									StripedSmithWaterman::Alignment fullAlignment;
									aligner.Align(lncSeq.c_str(), task.seq2.c_str(), static_cast<int>(task.seq2.size()), filter, &fullAlignment, 15);
									cerr << "[fasim.cuda] batch taskCount=" << tasks.size()
									     << " targetLength=" << currentTargetLength
									     << " topK=" << topK
									     << " maxScore=" << maxScore
									     << " cpu_full_sw=" << fullAlignment.sw_score
									     << " minScore=" << minScore
									     << " peaksKept=" << finalScoreInfo.size()
									     << endl;
								}

								if (finalScoreInfo.empty())
								{
									continue;
								}

								taskTriplexes.clear();
								fastSIM_extend_from_scoreinfo(aligner,
								                              filter,
								                              alignment,
								                              15,
								                              lncSeq,
								                              task.seq2,
								                              *task.srcSeq,
								                              task.dnaStartPos,
								                              finalScoreInfo,
								                              taskTriplexes,
								                              task.strand,
								                              task.Para,
								                              task.rule,
								                              paraList.ntMin,
								                              paraList.ntMax,
								                              paraList.penaltyT,
								                              paraList.penaltyC,
								                              paraList,
								                              writeFull);
								write_task_triplexes(task);
							}
						}
						else
						{
							const int suppressBp = fasim_prealign_peak_suppress_bp_runtime();
							const int workerCount = min(static_cast<int>(tasks.size()), extendThreadCount);
							std::atomic<size_t> nextTask(0);
							std::atomic<int> debugPrinted(0);

							std::vector<std::thread> workers;
							workers.reserve(static_cast<size_t>(workerCount));
							for (int w = 0; w < workerCount; ++w)
							{
								workers.push_back(std::thread([&, w]()
								{
									(void)w;
									StripedSmithWaterman::Aligner alignerLocal;
									StripedSmithWaterman::Filter filterLocal;
									StripedSmithWaterman::Alignment alignmentLocal;
									std::vector<struct StripedSmithWaterman::scoreInfo> finalScoreInfoLocal;
									finalScoreInfoLocal.reserve(static_cast<size_t>(topK));
									std::vector<triplex> taskTriplexesLocal;
									taskTriplexesLocal.reserve(64);
									std::ostringstream outBuf;
									std::vector<FasimLiteRow> liteRowsLocal;

									while (true)
									{
										const size_t t = nextTask.fetch_add(1, std::memory_order_relaxed);
										if (t >= tasks.size())
										{
											break;
										}

										const StreamTask &task = tasks[t];
										const size_t base = t * static_cast<size_t>(topK);
										const PreAlignCudaPeak *taskPeaks = peaks.data() + base;
										const int maxScore = taskPeaks[0].score;
										const int minScore = static_cast<int>(static_cast<double>(maxScore) * 0.8);

										finalScoreInfoLocal.clear();
										for (int k = 0; k < topK; ++k)
										{
											const PreAlignCudaPeak &p = taskPeaks[static_cast<size_t>(k)];
											if (p.position < 0 || p.score <= minScore)
											{
												continue;
											}
											bool suppressed = false;
											for (size_t s = 0; s < finalScoreInfoLocal.size(); ++s)
											{
												if (abs(finalScoreInfoLocal[s].position - p.position) < suppressBp)
												{
													suppressed = true;
													break;
												}
											}
											if (!suppressed)
											{
												finalScoreInfoLocal.push_back(StripedSmithWaterman::scoreInfo(p.score, p.position));
											}
										}

										if (debugCuda && t == 0 && debugPrinted.exchange(1) == 0)
										{
											StripedSmithWaterman::Alignment fullAlignment;
											alignerLocal.Align(lncSeq.c_str(), task.seq2.c_str(), static_cast<int>(task.seq2.size()), filterLocal, &fullAlignment, 15);
											cerr << "[fasim.cuda] batch taskCount=" << tasks.size()
											     << " targetLength=" << currentTargetLength
											     << " topK=" << topK
											     << " maxScore=" << maxScore
											     << " cpu_full_sw=" << fullAlignment.sw_score
											     << " minScore=" << minScore
											     << " peaksKept=" << finalScoreInfoLocal.size()
											     << endl;
										}

										if (finalScoreInfoLocal.empty())
										{
											continue;
										}

										taskTriplexesLocal.clear();
										fastSIM_extend_from_scoreinfo(alignerLocal,
										                              filterLocal,
										                              alignmentLocal,
										                              15,
										                              lncSeq,
										                              task.seq2,
											                              *task.srcSeq,
										                              task.dnaStartPos,
										                              finalScoreInfoLocal,
										                              taskTriplexesLocal,
										                              task.strand,
										                              task.Para,
										                              task.rule,
										                              paraList.ntMin,
										                              paraList.ntMax,
										                              paraList.penaltyT,
										                              paraList.penaltyC,
									                              paraList,
									                              writeFull);
										if (taskTriplexesLocal.empty())
										{
											continue;
										}

											outBuf.str("");
											outBuf.clear();
					if (writeLite)
					{
												liteRowsLocal.clear();
											}

										for (size_t i = 0; i < taskTriplexesLocal.size(); ++i)
										{
											const triplex &atr = taskTriplexesLocal[i];
											const string &chr = atr.chr.empty() ? task.chr : atr.chr;
											const long genomestart = (atr.genomestart != 0) ? atr.genomestart : (atr.starj + task.recordStartGenome - 1);
											const long genomeend = (atr.genomeend != 0) ? atr.genomeend : (atr.endj + task.recordStartGenome - 1);

											if (atr.score < paraList.scoreMin ||
											    atr.identity < paraList.minIdentity ||
											    atr.tri_score < paraList.minStability ||
											    atr.nt < paraList.cLength)
											{
												continue;
											}

											const int motif = 0;
											const int middle = static_cast<int>((atr.stari + atr.endi) / 2);
											const int center = middle;

											if (writeLite)
											{
												liteRowsLocal.push_back(fasim_make_lite_row(chr,
												                                            genomestart,
												                                            genomeend,
												                                            atr));
											}

											if (atr.starj < atr.endj)
											{
												outBuf << atr.stari << "\t" << atr.endi << "\t" << atr.starj << "\t" << atr.endj << "\t"
												       << "R\t" << chr << "\t" << genomestart << "\t" << genomeend << "\t"
												       << atr.tri_score << "\t" << atr.identity << "\t" << getStrand(atr.reverse, atr.strand) << "\t"
												       << atr.rule << "\t" << atr.score << "\t" << atr.nt << "\t"
												       << motif << "\t" << middle << "\t" << center << "\t"
												       << atr.stri_align << "\t" << atr.strj_align << "\n";
											}
											else
											{
												outBuf << atr.stari << "\t" << atr.endi << "\t" << atr.starj << "\t" << atr.endj << "\t"
												       << "L\t" << chr << "\t" << genomestart << "\t" << genomeend << "\t"
												       << atr.tri_score << "\t" << atr.identity << "\t" << getStrand(atr.reverse, atr.strand) << "\t"
												       << atr.rule << "\t" << atr.score << "\t" << atr.nt << "\t"
												       << motif << "\t" << middle << "\t" << center << "\t"
												       << atr.stri_align << "\t" << atr.strj_align << "\n";
											}
										}

										const std::string outText = outBuf.str();
										if (outText.empty() && liteRowsLocal.empty())
										{
											continue;
										}

											lock_guard<std::mutex> lock(outMutex);
											FasimScopedSeconds scoped(phaseTimingEnabled,
											                          &phaseTiming.output_write_seconds);
											if (writeLite && !liteRowsLocal.empty())
											{
												for (size_t rowIndex = 0; rowIndex < liteRowsLocal.size(); ++rowIndex)
												{
													emit_lite_row(liteRowsLocal[rowIndex]);
												}
										}
										if (!outText.empty())
										{
											outFile << outText;
										}
									}
								}));
							}
							for (size_t i = 0; i < workers.size(); ++i)
							{
								workers[i].join();
						}
					}

					if (broadReplacementConsumerEnabled &&
					    !broadReplacementTriplexesByTask.empty())
					{
					for (std::map<uint64_t, std::vector<triplex> >::const_iterator it =
					         broadReplacementTriplexesByTask.begin();
					     it != broadReplacementTriplexesByTask.end();
					     ++it)
					{
						broadScoreInfoConsumerShadowStats.broad_path_extra_triplexes +=
							static_cast<uint64_t>(it->second.size());
						if (broadScoreInfoConsumerShadowStats.broad_path_first_mismatch ==
						    "none")
						{
							std::ostringstream first;
							first << "task:" << it->first
							      << ":unconsumed_shadow"
							      << ":shadow_count:" << it->second.size();
							broadScoreInfoConsumerShadowStats.broad_path_first_mismatch =
								first.str();
						}
						}
						broadReplacementTriplexesByTask.clear();
					}
					finalize_attempt_consumer_shadow();
					finalize_emission_only_consumer_shadow();
					tasks.clear();
					encodedTargets.clear();
					legacyEncodedTargets.clear();
							currentTargetLength = -1;
							return;
							}
						}
					}
				else
				{
					// Phase A: preAlign on multiple GPUs in parallel.
					const size_t taskCount = tasks.size();
					const size_t baseChunk = taskCount / cudaDeviceCount;
					const size_t extra = taskCount % cudaDeviceCount;
					std::vector<size_t> chunkBegin(cudaDeviceCount, 0);
					std::vector<size_t> chunkCount(cudaDeviceCount, 0);
					size_t beginIndex = 0;
					for (size_t d = 0; d < cudaDeviceCount; ++d)
					{
						const size_t count = baseChunk + (d < extra ? 1u : 0u);
						chunkBegin[d] = beginIndex;
						chunkCount[d] = count;
						beginIndex += count;
					}

					std::vector< std::vector<PreAlignCudaPeak> > peaksByDevice(cudaDeviceCount);
					std::vector<bool> ok(cudaDeviceCount, true);
					std::vector<string> cudaErrors(cudaDeviceCount);

						std::vector<std::thread> prealignThreads;
						prealignThreads.reserve(cudaDeviceCount);
						const auto cudaTopkStart = std::chrono::steady_clock::now();
						for (size_t d = 0; d < cudaDeviceCount; ++d)
						{
						if (chunkCount[d] == 0)
						{
							continue;
						}
						prealignThreads.push_back(std::thread([&, d]()
						{
							const size_t localBegin = chunkBegin[d];
							const size_t localCount = chunkCount[d];
							const uint8_t *targetsPtr =
								encodedTargets.data() + localBegin * static_cast<size_t>(currentTargetLength);

							std::vector<PreAlignCudaPeak> peaks;
							PreAlignCudaBatchResult batchResult;
							string cudaError;
							const bool okLocal = prealign_cuda_find_topk_column_maxima(cudaQueries[d],
							                                                          targetsPtr,
							                                                          static_cast<int>(localCount),
							                                                          currentTargetLength,
							                                                          topK,
							                                                          &peaks,
							                                                          &batchResult,
							                                                          &cudaError);
							ok[d] = okLocal;
							cudaErrors[d] = cudaError;
							if (okLocal)
							{
								peaksByDevice[d].swap(peaks);
							}
						}));
					}
						for (size_t i = 0; i < prealignThreads.size(); ++i)
						{
							prealignThreads[i].join();
						}
						if (phaseTimingEnabled)
						{
							++phaseTiming.cuda_topk_batches;
							phaseTiming.cuda_topk_tasks += static_cast<uint64_t>(tasks.size());
							phaseTiming.cuda_topk_wall_seconds += fasim_seconds_since(cudaTopkStart);
							for (size_t d = 0; d < cudaDeviceCount; ++d)
							{
								if (chunkCount[d] == 0)
								{
									continue;
								}
								// Per-device kernel events are folded into the multi-GPU wall bucket here;
								// this path is not used by the top5 GASAL2 preset guard.
							}
						}

					bool allOk = true;
					for (size_t d = 0; d < cudaDeviceCount; ++d)
					{
						if (chunkCount[d] != 0 && !ok[d])
						{
							allOk = false;
							break;
						}
					}
					if (!allOk)
					{
						useCudaBatch = false;
						maxTasksTotal = 1;
					}
					else
					{
						struct WorkItem
						{
							size_t device;
							size_t local;
						};

						const int suppressBp = fasim_prealign_peak_suppress_bp_runtime();
						std::vector<WorkItem> work;
						work.reserve(tasks.size());
						for (size_t d = 0; d < cudaDeviceCount; ++d)
						{
							const size_t localCount = chunkCount[d];
							for (size_t local = 0; local < localCount; ++local)
							{
								work.push_back(WorkItem{d, local});
							}
						}

						const int workerCount = min(static_cast<int>(work.size()), extendThreadCount);
						std::atomic<size_t> nextWork(0);
						std::atomic<int> debugPrinted(0);

						std::vector<std::thread> workers;
						workers.reserve(static_cast<size_t>(workerCount));
						for (int w = 0; w < workerCount; ++w)
						{
							workers.push_back(std::thread([&, w]()
							{
								(void)w;
								StripedSmithWaterman::Aligner alignerLocal;
								StripedSmithWaterman::Filter filterLocal;
								StripedSmithWaterman::Alignment alignmentLocal;
								std::vector<struct StripedSmithWaterman::scoreInfo> finalScoreInfoLocal;
								finalScoreInfoLocal.reserve(static_cast<size_t>(topK));
								std::vector<triplex> taskTriplexesLocal;
								taskTriplexesLocal.reserve(64);
								std::ostringstream outBuf;
								std::vector<FasimLiteRow> liteRowsLocal;

								while (true)
								{
									const size_t wi = nextWork.fetch_add(1, std::memory_order_relaxed);
									if (wi >= work.size())
									{
										break;
									}

									const WorkItem item = work[wi];
									const size_t d = item.device;
									const size_t local = item.local;
									const size_t localBegin = chunkBegin[d];
									const StreamTask &task = tasks[localBegin + local];
									const std::vector<PreAlignCudaPeak> &peaks = peaksByDevice[d];
									const size_t base = local * static_cast<size_t>(topK);
									const PreAlignCudaPeak *taskPeaks = peaks.data() + base;

									const int maxScore = taskPeaks[0].score;
									const int minScore = static_cast<int>(static_cast<double>(maxScore) * 0.8);

									finalScoreInfoLocal.clear();
									for (int k = 0; k < topK; ++k)
									{
										const PreAlignCudaPeak &p = taskPeaks[static_cast<size_t>(k)];
										if (p.position < 0 || p.score <= minScore)
										{
											continue;
										}
										bool suppressed = false;
										for (size_t s = 0; s < finalScoreInfoLocal.size(); ++s)
										{
											if (abs(finalScoreInfoLocal[s].position - p.position) < suppressBp)
											{
												suppressed = true;
												break;
											}
										}
										if (!suppressed)
										{
											finalScoreInfoLocal.push_back(StripedSmithWaterman::scoreInfo(p.score, p.position));
										}
									}

									if (debugCuda && d == 0 && local == 0 && debugPrinted.exchange(1) == 0)
									{
										StripedSmithWaterman::Alignment fullAlignment;
										alignerLocal.Align(lncSeq.c_str(), task.seq2.c_str(), static_cast<int>(task.seq2.size()), filterLocal, &fullAlignment, 15);
										cerr << "[fasim.cuda] batch taskCount=" << tasks.size()
										     << " targetLength=" << currentTargetLength
										     << " devices=" << cudaDeviceCount
										     << " topK=" << topK
										     << " maxScore=" << maxScore
										     << " cpu_full_sw=" << fullAlignment.sw_score
										     << " minScore=" << minScore
										     << " peaksKept=" << finalScoreInfoLocal.size()
										     << endl;
									}

									if (finalScoreInfoLocal.empty())
									{
										continue;
									}

									taskTriplexesLocal.clear();
									fastSIM_extend_from_scoreinfo(alignerLocal,
									                              filterLocal,
									                              alignmentLocal,
									                              15,
									                              lncSeq,
									                              task.seq2,
										                              *task.srcSeq,
									                              task.dnaStartPos,
									                              finalScoreInfoLocal,
									                              taskTriplexesLocal,
									                              task.strand,
									                              task.Para,
									                              task.rule,
									                              paraList.ntMin,
									                              paraList.ntMax,
									                              paraList.penaltyT,
									                              paraList.penaltyC,
									                              paraList,
									                              writeFull);
									if (taskTriplexesLocal.empty())
									{
										continue;
									}

									outBuf.str("");
									outBuf.clear();
									if (writeLite)
									{
										liteRowsLocal.clear();
									}

									for (size_t i = 0; i < taskTriplexesLocal.size(); ++i)
									{
										const triplex &atr = taskTriplexesLocal[i];
										const string &chr = atr.chr.empty() ? task.chr : atr.chr;
										const long genomestart = (atr.genomestart != 0) ? atr.genomestart : (atr.starj + task.recordStartGenome - 1);
										const long genomeend = (atr.genomeend != 0) ? atr.genomeend : (atr.endj + task.recordStartGenome - 1);

										if (atr.score < paraList.scoreMin ||
										    atr.identity < paraList.minIdentity ||
										    atr.tri_score < paraList.minStability ||
										    atr.nt < paraList.cLength)
										{
											continue;
										}

										const int motif = 0;
										const int middle = static_cast<int>((atr.stari + atr.endi) / 2);
										const int center = middle;

										if (writeLite)
										{
											liteRowsLocal.push_back(fasim_make_lite_row(chr,
											                                            genomestart,
											                                            genomeend,
											                                            atr));
										}

										if (atr.starj < atr.endj)
										{
											outBuf << atr.stari << "\t" << atr.endi << "\t" << atr.starj << "\t" << atr.endj << "\t"
											       << "R\t" << chr << "\t" << genomestart << "\t" << genomeend << "\t"
											       << atr.tri_score << "\t" << atr.identity << "\t" << getStrand(atr.reverse, atr.strand) << "\t"
											       << atr.rule << "\t" << atr.score << "\t" << atr.nt << "\t"
											       << motif << "\t" << middle << "\t" << center << "\t"
											       << atr.stri_align << "\t" << atr.strj_align << "\n";
										}
										else
										{
											outBuf << atr.stari << "\t" << atr.endi << "\t" << atr.starj << "\t" << atr.endj << "\t"
											       << "L\t" << chr << "\t" << genomestart << "\t" << genomeend << "\t"
											       << atr.tri_score << "\t" << atr.identity << "\t" << getStrand(atr.reverse, atr.strand) << "\t"
											       << atr.rule << "\t" << atr.score << "\t" << atr.nt << "\t"
											       << motif << "\t" << middle << "\t" << center << "\t"
											       << atr.stri_align << "\t" << atr.strj_align << "\n";
										}
									}

									const std::string outText = outBuf.str();
									if (outText.empty() && liteRowsLocal.empty())
									{
										continue;
									}

										lock_guard<std::mutex> lock(outMutex);
										FasimScopedSeconds scoped(phaseTimingEnabled,
										                          &phaseTiming.output_write_seconds);
										if (writeLite && !liteRowsLocal.empty())
										{
											for (size_t rowIndex = 0; rowIndex < liteRowsLocal.size(); ++rowIndex)
											{
												emit_lite_row(liteRowsLocal[rowIndex]);
											}
									}
									if (!outText.empty())
									{
										if (writeFull)
										{
											outFile << outText;
										}
									}
								}
							}));
						}

						for (size_t i = 0; i < workers.size(); ++i)
						{
							workers[i].join();
					}

				finalize_attempt_consumer_shadow();
				finalize_emission_only_consumer_shadow();
				tasks.clear();
				encodedTargets.clear();
						legacyEncodedTargets.clear();
						currentTargetLength = -1;
						return;
					}
				}
			}

			// CPU fallback for this batch.
			std::vector< std::vector<struct StripedSmithWaterman::scoreInfo> > gasalCpuScoreInfos;
			std::vector< std::vector<triplex> > gasalCpuTriplexes;
			const bool segmentedLongQueryShadowFallbackRequested =
				gasal2LongQuerySegmentedShadowStats.requested != 0 &&
				!gasal2QueryLengthSupported &&
				paraList.doFastSim &&
				fasim_gasal2_is_built();
			const bool exactTileOracleExportRequested =
				gasal2LongQueryExactTileShadowStats.requested != 0 &&
				fasim_gasal2_long_query_exact_tile_oracle_export_runtime() &&
				!gasal2QueryLengthSupported &&
				paraList.doFastSim;
			const bool exactTileCandidateEquivalenceRequested =
				gasal2LongQueryExactTileShadowStats.requested != 0 &&
				fasim_gasal2_long_query_exact_tile_candidate_equivalence_runtime() &&
				!gasal2QueryLengthSupported &&
				paraList.doFastSim;
			if (exactTileOracleExportRequested ||
			    exactTileCandidateEquivalenceRequested)
			{
				const std::chrono::steady_clock::time_point oracleStart =
					std::chrono::steady_clock::now();
				uint64_t oracleCandidates = 0;
				uint64_t tileCandidates = 0;
				uint64_t candidateMissing = 0;
				uint64_t candidateExtra = 0;
				uint64_t positionMissing = 0;
				uint64_t positionExtra = 0;
				uint64_t positionScoreMismatches = 0;
				std::vector<FasimGasal2LongQuerySegment> exactTiles;
				if (exactTileCandidateEquivalenceRequested)
				{
					size_t tileOverlap =
						fasim_gasal2_long_query_exact_tile_overlap_runtime();
					const size_t tileLen =
						fasim_gasal2_long_query_exact_tile_len_runtime();
					if (tileOverlap >= tileLen)
					{
						tileOverlap = 0;
					}
					exactTiles = fasim_build_gasal2_long_query_segments(
						lncSeq,
						tileLen,
						tileOverlap,
						0);
					if (exactTiles.empty())
					{
						++gasal2LongQueryExactTileShadowStats.fallback;
					}
					else
					{
						gasal2LongQueryExactTileShadowStats.active = 1;
					}
				}
				for (size_t t = 0; t < tasks.size(); ++t)
				{
					StreamTask &task = tasks[t];
					const int minScore = task_min_score(task);
					std::vector<struct StripedSmithWaterman::scoreInfo> oracleScoreInfo;
					aligner.preAlign(lncSeq.c_str(),
					                 task.seq2.c_str(),
					                 static_cast<int>(task.seq2.size()),
					                 filter,
					                 &alignment,
					                 15,
					                 minScore,
					                 oracleScoreInfo,
					                 5,
					                 -4);
					oracleCandidates +=
						static_cast<uint64_t>(oracleScoreInfo.size());
					if (exactTileCandidateEquivalenceRequested &&
					    !exactTiles.empty())
					{
						std::vector< std::pair<int, int> > oracleKeys;
						std::vector< std::pair<int, int> > tileKeys;
						oracleKeys.reserve(oracleScoreInfo.size());
						for (size_t i = 0; i < oracleScoreInfo.size(); ++i)
						{
							oracleKeys.push_back(
								std::make_pair(oracleScoreInfo[i].score,
								               oracleScoreInfo[i].position));
						}
						for (size_t tileIndex = 0; tileIndex < exactTiles.size(); ++tileIndex)
						{
							const FasimGasal2LongQuerySegment &tile =
								exactTiles[tileIndex];
							std::vector<struct StripedSmithWaterman::scoreInfo> tileScoreInfo;
							StripedSmithWaterman::Alignment tileAlignment;
							aligner.preAlign(tile.query_segment.c_str(),
							                 task.seq2.c_str(),
							                 static_cast<int>(task.seq2.size()),
							                 filter,
							                 &tileAlignment,
							                 15,
							                 minScore,
							                 tileScoreInfo,
							                 5,
							                 -4);
							for (size_t i = 0; i < tileScoreInfo.size(); ++i)
							{
								tileKeys.push_back(
									std::make_pair(tileScoreInfo[i].score,
									               tileScoreInfo[i].position));
							}
						}
						std::sort(oracleKeys.begin(), oracleKeys.end());
						oracleKeys.erase(std::unique(oracleKeys.begin(),
						                             oracleKeys.end()),
						                 oracleKeys.end());
						std::sort(tileKeys.begin(), tileKeys.end());
						tileKeys.erase(std::unique(tileKeys.begin(),
						                           tileKeys.end()),
						               tileKeys.end());
						tileCandidates += static_cast<uint64_t>(tileKeys.size());
						std::map<int, int> oraclePositionScores;
						for (size_t i = 0; i < oracleKeys.size(); ++i)
						{
							std::map<int, int>::iterator posIt =
								oraclePositionScores.find(oracleKeys[i].second);
							if (posIt == oraclePositionScores.end() ||
							    oracleKeys[i].first > posIt->second)
							{
								oraclePositionScores[oracleKeys[i].second] =
									oracleKeys[i].first;
							}
						}
						std::map<int, int> tilePositionScores;
						for (size_t i = 0; i < tileKeys.size(); ++i)
						{
							std::map<int, int>::iterator posIt =
								tilePositionScores.find(tileKeys[i].second);
							if (posIt == tilePositionScores.end() ||
							    tileKeys[i].first > posIt->second)
							{
								tilePositionScores[tileKeys[i].second] =
									tileKeys[i].first;
							}
						}
						for (size_t i = 0; i < oracleKeys.size(); ++i)
						{
							if (!std::binary_search(tileKeys.begin(),
							                        tileKeys.end(),
							                        oracleKeys[i]))
							{
								++candidateMissing;
							}
						}
						for (std::map<int, int>::const_iterator posIt =
						         oraclePositionScores.begin();
						     posIt != oraclePositionScores.end();
						     ++posIt)
						{
							std::map<int, int>::const_iterator tilePosIt =
								tilePositionScores.find(posIt->first);
							if (tilePosIt == tilePositionScores.end())
							{
								++positionMissing;
							}
							else if (tilePosIt->second != posIt->second)
							{
								++positionScoreMismatches;
							}
						}
						for (size_t i = 0; i < tileKeys.size(); ++i)
						{
							if (!std::binary_search(oracleKeys.begin(),
							                        oracleKeys.end(),
							                        tileKeys[i]))
							{
								++candidateExtra;
							}
						}
						for (std::map<int, int>::const_iterator posIt =
						         tilePositionScores.begin();
						     posIt != tilePositionScores.end();
						     ++posIt)
						{
							if (oraclePositionScores.find(posIt->first) ==
							    oraclePositionScores.end())
							{
								++positionExtra;
							}
						}
					}
				}
				gasal2LongQueryExactTileShadowStats.cpu_oracle_candidates +=
					oracleCandidates;
				gasal2LongQueryExactTileShadowStats.tile_candidates +=
					tileCandidates;
				gasal2LongQueryExactTileShadowStats.candidate_missing +=
					candidateMissing;
				gasal2LongQueryExactTileShadowStats.candidate_extra +=
					candidateExtra;
				gasal2LongQueryExactTileShadowStats.position_missing +=
					positionMissing;
				gasal2LongQueryExactTileShadowStats.position_extra +=
					positionExtra;
				gasal2LongQueryExactTileShadowStats.position_score_mismatches +=
					positionScoreMismatches;
				gasal2LongQueryExactTileShadowStats.total_seconds +=
					fasim_seconds_since(oracleStart);
				}
					if (gasal2_batched_traceback_enabled() ||
				    segmentedLongQueryShadowFallbackRequested)
				{
					const bool streamingRealpathRequested =
						(fasim_long_query_streaming_scoreinfo_realpath_prototype_runtime() &&
						 !fasim_long_query_streaming_scoreinfo_two_contract_bridge_runtime()) ||
						(fasim_long_query_streaming_scoreinfo_two_contract_bridge_runtime() &&
						 fasim_long_query_streaming_scoreinfo_two_contract_bridge_trust_runtime());
					if (streamingRealpathRequested)
					{
						++longQueryStreamingScoreInfoShadowStats.realpath_fallbacks;
					}
					gasalCpuScoreInfos.resize(tasks.size());
					{
						FasimScopedSeconds scoped(phaseTimingEnabled,
						                          &phaseTiming.cpu_fallback_scoreinfo_seconds);
						for (size_t t = 0; t < tasks.size(); ++t)
						{
							StreamTask &task = tasks[t];
							const int minScore = task_min_score(task);
							if (paraList.doFastSim)
							{
								StripedSmithWaterman::Alignment cpuAlignment;
								aligner.preAlign(lncSeq.c_str(),
								                 task.seq2.c_str(),
								                 static_cast<int>(task.seq2.size()),
								                 filter,
								                 &cpuAlignment,
								                 15,
								                 minScore,
								                 gasalCpuScoreInfos[t],
								                 5,
								                 -4);
							}
						}
					}
					if (extend_tasks_with_gasal2_batch(gasalCpuScoreInfos,
					                                   gasalCpuTriplexes,
					                                   false,
					                                   false))
					{
						for (size_t t = 0; t < tasks.size(); ++t)
						{
							taskTriplexes = gasalCpuTriplexes[t];
							write_task_triplexes(tasks[t]);
						}
						finalize_attempt_consumer_shadow();
						finalize_emission_only_consumer_shadow();
						tasks.clear();
						encodedTargets.clear();
						legacyEncodedTargets.clear();
					currentTargetLength = -1;
					return;
				}
			}

				{
					FasimScopedSeconds scoped(phaseTimingEnabled,
					                          &phaseTiming.cpu_fallback_extend_seconds);
					const bool scorePrepassStateMachineShadowRequested =
						fasim_gasal2_score_prepass_state_machine_consumer_shadow_runtime() ||
						fasim_gasal2_score_prepass_state_machine_consumer_trust_runtime();
					const bool scorePrepassStateMachineTrustRequested =
						fasim_gasal2_score_prepass_state_machine_consumer_trust_runtime();
					const bool streamingRealpathRequested =
						(fasim_long_query_streaming_scoreinfo_realpath_prototype_runtime() &&
						 !fasim_long_query_streaming_scoreinfo_two_contract_bridge_runtime()) ||
						(fasim_long_query_streaming_scoreinfo_two_contract_bridge_runtime() &&
						 fasim_long_query_streaming_scoreinfo_two_contract_bridge_trust_runtime()) ||
						scorePrepassStateMachineShadowRequested;
					const bool streamingRealpathCanUse =
						streamingRealpathRequested &&
						streamingRealpathScoreInfos.size() == tasks.size() &&
						streamingRealpathReady.size() == tasks.size() &&
						std::find(streamingRealpathReady.begin(),
						          streamingRealpathReady.end(),
						          static_cast<unsigned char>(0)) ==
							streamingRealpathReady.end();
						if (streamingRealpathRequested && !streamingRealpathCanUse)
						{
							++longQueryStreamingScoreInfoShadowStats.realpath_fallbacks;
						}
						std::vector<std::vector<triplex> > flushReplayTriplexesByTask;
						std::vector<std::vector<std::string> > flushReplayTriplexProvenanceByTask;
							std::vector<unsigned char> flushReplayTaskCovered;
								std::vector<std::vector<triplex> > flushSelectedOnlyReplayTriplexesByTask;
								std::vector<std::vector<std::string> > flushSelectedOnlyReplayTriplexProvenanceByTask;
								std::vector<std::vector<int> > flushSelectedOnlyReplayTriplexScoreInfoByTask;
								std::vector<unsigned char> flushSelectedOnlyReplayTaskCovered;
								std::vector<std::vector<triplex> > flushGroupedSelectedReplayTriplexesByTask;
								std::vector<std::vector<std::string> > flushGroupedSelectedReplayTriplexProvenanceByTask;
								std::vector<unsigned char> flushGroupedSelectedReplayTaskCovered;
							std::vector<std::vector<triplex> > flushFullReplayTriplexesByTask;
						std::vector<unsigned char> flushFullReplayTaskCovered;
						std::vector<std::vector<triplex> > flushOracleReplayTriplexesByTask;
						std::vector<unsigned char> flushOracleReplayTaskCovered;
						std::vector<std::vector<triplex> >
							scorePrepassStateMachineTriplexesByTask;
						std::vector<unsigned char>
							scorePrepassStateMachineTaskCovered;
						if (streamingRealpathCanUse &&
						    fasim_long_query_streaming_scoreinfo_flush_segmented_replay_probe_runtime())
						{
							flushReplayTriplexesByTask.resize(tasks.size());
							flushReplayTriplexProvenanceByTask.resize(tasks.size());
							flushReplayTaskCovered.assign(tasks.size(), static_cast<unsigned char>(0));
						}
							if (streamingRealpathCanUse &&
							    fasim_long_query_streaming_scoreinfo_flush_segmented_selected_only_replay_probe_runtime())
								{
									flushSelectedOnlyReplayTriplexesByTask.resize(tasks.size());
									flushSelectedOnlyReplayTriplexProvenanceByTask.resize(tasks.size());
									flushSelectedOnlyReplayTriplexScoreInfoByTask.resize(tasks.size());
									flushSelectedOnlyReplayTaskCovered.assign(tasks.size(), static_cast<unsigned char>(0));
								}
							if (streamingRealpathCanUse &&
							    fasim_long_query_streaming_scoreinfo_flush_segmented_grouped_selected_replay_probe_runtime())
								{
									flushGroupedSelectedReplayTriplexesByTask.resize(tasks.size());
									flushGroupedSelectedReplayTriplexProvenanceByTask.resize(tasks.size());
									flushGroupedSelectedReplayTaskCovered.assign(tasks.size(), static_cast<unsigned char>(0));
								}
							if (streamingRealpathCanUse &&
							    (fasim_long_query_streaming_scoreinfo_flush_full_replay_probe_runtime() ||
							     broadReplacementConsumerEnabled))
							{
								flushFullReplayTriplexesByTask.resize(tasks.size());
								flushFullReplayTaskCovered.assign(tasks.size(), static_cast<unsigned char>(0));
								flushOracleReplayTriplexesByTask.resize(tasks.size());
								flushOracleReplayTaskCovered.assign(tasks.size(), static_cast<unsigned char>(0));
							}
							if (streamingRealpathCanUse &&
							    (fasim_long_query_streaming_scoreinfo_flush_segmented_extend_attempt_probe_runtime() ||
							     broadReplacementConsumerEnabled))
							{
							const std::chrono::steady_clock::time_point flushProbeStart =
								std::chrono::steady_clock::now();
							std::vector<FasimGasal2Attempt> flushProbeAttempts;
							std::vector<size_t> flushProbeAttemptTaskIndexes;
							std::vector<size_t> flushProbeScoreInfoTaskIndexes;
							std::vector<int> flushProbeScoreInfoScores;
							size_t reserveAttempts = 0;
							for (size_t rt = 0; rt < streamingRealpathScoreInfos.size(); ++rt)
							{
								reserveAttempts += streamingRealpathScoreInfos[rt].size() * 5;
							}
							flushProbeAttempts.reserve(reserveAttempts);
							flushProbeAttemptTaskIndexes.reserve(reserveAttempts);
							flushProbeScoreInfoTaskIndexes.reserve(reserveAttempts / 5);
							flushProbeScoreInfoScores.reserve(reserveAttempts / 5);
						int flushScoreInfoIndex = 0;
							for (size_t rt = 0; rt < tasks.size(); ++rt)
							{
								StreamTask &probeTask = tasks[rt];
								const std::vector<struct StripedSmithWaterman::scoreInfo> &scoreInfos =
									streamingRealpathScoreInfos[rt];
								for (size_t si = 0; si < scoreInfos.size(); ++si)
									{
										flushProbeScoreInfoTaskIndexes.push_back(rt);
										const StripedSmithWaterman::scoreInfo &scoreInfo = scoreInfos[si];
										flushProbeScoreInfoScores.push_back(scoreInfo.score);
								float Iden = 0.6;
								while (Iden <= 1)
								{
									int cutlength =
										static_cast<int>(scoreInfo.score + 24) /
										(9 * Iden - 4) + 1;
									cutlength =
										scoreInfo.position - cutlength + 1 > 0 ?
										cutlength : scoreInfo.position + 1;
									const int targetStart =
										scoreInfo.position - cutlength + 1;
									if (targetStart >= 0 && cutlength > 0)
									{
										FasimGasal2Attempt attempt;
										attempt.scoreinfo_index = flushScoreInfoIndex;
										attempt.cutlength = cutlength;
										attempt.start = targetStart;
										attempt.prealign_score = scoreInfo.score;
										attempt.target_end_required_for_fallback =
											cutlength - 1;
										attempt.nt_min_length = paraList.ntMin;
											attempt.set_target_view(
												&probeTask.seq2,
												static_cast<size_t>(targetStart),
												static_cast<size_t>(cutlength));
											flushProbeAttempts.push_back(attempt);
											flushProbeAttemptTaskIndexes.push_back(rt);
										}
									Iden += 0.1;
								}
								++flushScoreInfoIndex;
							}
						}
						longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_attempt_probe_requested += 1;
						longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_attempt_probe_flushes += 1;
						std::vector<FasimGasal2LongQuerySegment> flushProbeSegments =
							fasim_build_gasal2_long_query_segments(
								lncSeq,
								fasim_long_query_streaming_scoreinfo_segmented_probe_tile_len_runtime(),
								fasim_long_query_streaming_scoreinfo_segmented_probe_tile_overlap_runtime(),
								fasim_long_query_streaming_scoreinfo_segmented_probe_max_segments_runtime());
						longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_attempt_probe_segments +=
							static_cast<uint64_t>(flushProbeSegments.size());
						if (flushProbeAttempts.empty() || flushProbeSegments.empty())
						{
							++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_attempt_probe_fallbacks;
						}
						else
						{
							std::map<std::pair<int, std::pair<int, int> >, size_t>
								flushProbeAttemptOrdinalByKey;
									std::vector<unsigned char> flushReplayAttemptSelected;
									std::vector<size_t> flushReplaySelectedAttemptOrdinals;
									std::vector<size_t> flushReplaySelectedAttemptSegmentIndexes;
									std::vector<size_t> flushReplayAttemptSegmentIndexes;
									uint64_t flushReplayRawSelectedAttempts = 0;
									const bool scorePrepassStateMachineShadowRequested =
										fasim_gasal2_score_prepass_state_machine_consumer_shadow_runtime();
										const bool flushSelectedReplayNeeded =
										!flushReplayTriplexesByTask.empty() ||
										!flushSelectedOnlyReplayTriplexesByTask.empty() ||
										!flushGroupedSelectedReplayTriplexesByTask.empty() ||
										scorePrepassStateMachineShadowRequested;
							if (flushSelectedReplayNeeded)
							{
								flushReplayAttemptSelected.assign(
									flushProbeAttempts.size(),
									static_cast<unsigned char>(0));
									flushReplayAttemptSegmentIndexes.assign(
										flushProbeAttempts.size(),
										static_cast<size_t>(-1));
									flushReplaySelectedAttemptOrdinals.reserve(
										flushProbeAttempts.size());
									flushReplaySelectedAttemptSegmentIndexes.reserve(
										flushProbeAttempts.size());
								for (size_t attemptIndex = 0;
								     attemptIndex < flushProbeAttempts.size();
								     ++attemptIndex)
								{
									const FasimGasal2Attempt &attempt =
										flushProbeAttempts[attemptIndex];
									const std::pair<int, std::pair<int, int> > key =
										std::make_pair(
											attempt.scoreinfo_index,
											std::make_pair(attempt.start,
											               attempt.cutlength));
									if (flushProbeAttemptOrdinalByKey.find(key) ==
									    flushProbeAttemptOrdinalByKey.end())
									{
										flushProbeAttemptOrdinalByKey[key] = attemptIndex;
										}
									}
								}
								if (scorePrepassStateMachineShadowRequested)
								{
									scorePrepassStateMachineTriplexesByTask.resize(tasks.size());
									scorePrepassStateMachineTaskCovered.assign(
										tasks.size(),
										static_cast<unsigned char>(0));
									longQueryStreamingScoreInfoShadowStats
										.score_prepass_state_machine_shadow_requested = 1;
									longQueryStreamingScoreInfoShadowStats
										.score_prepass_state_machine_shadow_scoreinfos +=
										static_cast<uint64_t>(
											flushProbeScoreInfoTaskIndexes.size());
									longQueryStreamingScoreInfoShadowStats
										.score_prepass_state_machine_shadow_attempts +=
										static_cast<uint64_t>(flushProbeAttempts.size());
								}
								for (size_t segIndex = 0; segIndex < flushProbeSegments.size(); ++segIndex)
							{
								std::vector<FasimGasal2SelectedAlignment> flushProbeSelected;
								std::string flushProbeError;
								const bool flushProbeOk =
									fasim_gasal2_select_attempts(
										flushProbeSegments[segIndex].query_segment,
										flushProbeAttempts,
										&flushProbeSelected,
										&flushProbeError);
								++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_attempt_probe_calls;
								longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_attempt_probe_attempts +=
									static_cast<uint64_t>(flushProbeAttempts.size());
								if (flushProbeOk)
								{
									++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_attempt_probe_active;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_attempt_probe_selected_attempts +=
										static_cast<uint64_t>(flushProbeSelected.size());
									if (flushSelectedReplayNeeded)
									{
										flushReplayRawSelectedAttempts +=
											static_cast<uint64_t>(flushProbeSelected.size());
										for (size_t selectedIndex = 0;
										     selectedIndex < flushProbeSelected.size();
										     ++selectedIndex)
										{
											const FasimGasal2SelectedAlignment &selected =
												flushProbeSelected[selectedIndex];
											const std::pair<int, std::pair<int, int> > key =
												std::make_pair(
													selected.scoreinfo_index,
													std::make_pair(selected.start,
													               selected.cutlength));
											std::map<std::pair<int, std::pair<int, int> >,
											         size_t>::const_iterator ordinalIt =
												flushProbeAttemptOrdinalByKey.find(key);
											if (ordinalIt == flushProbeAttemptOrdinalByKey.end())
											{
												++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_replay_probe_fallbacks;
												continue;
											}
											const size_t attemptOrdinal = ordinalIt->second;
											if (attemptOrdinal < flushReplayAttemptSelected.size() &&
											    flushReplayAttemptSelected[attemptOrdinal] == 0)
											{
												flushReplayAttemptSelected[attemptOrdinal] =
													static_cast<unsigned char>(1);
													flushReplaySelectedAttemptOrdinals.push_back(
														attemptOrdinal);
													flushReplaySelectedAttemptSegmentIndexes.push_back(
														segIndex);
													if (attemptOrdinal <
													    flushReplayAttemptSegmentIndexes.size())
													{
														flushReplayAttemptSegmentIndexes[
															attemptOrdinal] = segIndex;
													}
												}
											}
									}
								}
									else
									{
										++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_attempt_probe_fallbacks;
									}
								}
								if (scorePrepassStateMachineShadowRequested)
								{
									const std::chrono::steady_clock::time_point
										stateMachineStart =
											std::chrono::steady_clock::now();
									size_t shadowTaskCount =
										fasim_long_query_streaming_scoreinfo_flush_segmented_replay_probe_max_tasks_runtime();
									if (shadowTaskCount == 0 ||
									    shadowTaskCount > tasks.size())
									{
										shadowTaskCount = tasks.size();
									}
									longQueryStreamingScoreInfoShadowStats
										.score_prepass_state_machine_shadow_tasks +=
										static_cast<uint64_t>(shadowTaskCount);
									const std::chrono::steady_clock::time_point
										selectStart =
											std::chrono::steady_clock::now();
									std::sort(flushReplaySelectedAttemptOrdinals.begin(),
									          flushReplaySelectedAttemptOrdinals.end());
									std::vector<unsigned char>
										stateMachinePrefixAttemptSelected(
											flushProbeAttempts.size(),
											static_cast<unsigned char>(0));
									std::vector<size_t>
										stateMachinePrefixAttemptOrdinals;
									stateMachinePrefixAttemptOrdinals.reserve(
										flushReplaySelectedAttemptOrdinals.size() * 2);
									for (size_t selectedOrdinalIndex = 0;
									     selectedOrdinalIndex <
									     flushReplaySelectedAttemptOrdinals.size();
									     ++selectedOrdinalIndex)
									{
										const size_t selectedOrdinal =
											flushReplaySelectedAttemptOrdinals[
												selectedOrdinalIndex];
										if (selectedOrdinal >= flushProbeAttempts.size())
										{
											continue;
										}
										const int selectedScoreInfo =
											flushProbeAttempts[
												selectedOrdinal].scoreinfo_index;
										size_t groupBegin = selectedOrdinal;
										while (groupBegin > 0 &&
										       flushProbeAttempts[
											       groupBegin - 1].scoreinfo_index ==
											       selectedScoreInfo)
										{
											--groupBegin;
										}
										for (size_t attemptOrdinal = groupBegin;
										     attemptOrdinal <= selectedOrdinal &&
										     attemptOrdinal < flushProbeAttempts.size();
										     ++attemptOrdinal)
										{
											if (stateMachinePrefixAttemptSelected[
												    attemptOrdinal] == 0)
											{
												stateMachinePrefixAttemptSelected[
													attemptOrdinal] =
													static_cast<unsigned char>(1);
												stateMachinePrefixAttemptOrdinals.push_back(
													attemptOrdinal);
											}
										}
									}
									std::sort(stateMachinePrefixAttemptOrdinals.begin(),
									          stateMachinePrefixAttemptOrdinals.end());
									const double selectSeconds =
										fasim_seconds_since(selectStart);
									longQueryStreamingScoreInfoShadowStats
										.score_prepass_state_machine_shadow_select_seconds +=
										selectSeconds;
									if (flushReplaySelectedAttemptOrdinals.empty() ||
									    stateMachinePrefixAttemptOrdinals.empty())
									{
										++longQueryStreamingScoreInfoShadowStats
											.score_prepass_state_machine_shadow_fallbacks;
										if (longQueryStreamingScoreInfoShadowStats.error ==
										    "none")
										{
											longQueryStreamingScoreInfoShadowStats.error =
												"score_prepass_state_machine_no_segmented_selected_attempts";
										}
									}
									else
									{
										longQueryStreamingScoreInfoShadowStats
											.score_prepass_state_machine_shadow_active = 1;
										longQueryStreamingScoreInfoShadowStats
											.score_prepass_state_machine_shadow_selected_attempts +=
											flushReplayRawSelectedAttempts;
										const int8_t nt_table[128] = {
											4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4
										};
										int currentStateMachineScoreInfo = -1;
										size_t currentStateMachineTask = 0;
										FasimGasal2Attempt stateMachineBestAttempt;
										FasimGasal2Attempt stateMachineLastAttempt;
										StripedSmithWaterman::Alignment
											stateMachineBestAlignment;
										StripedSmithWaterman::Alignment
											stateMachineLastAlignment;
											bool stateMachineHaveBest = false;
											bool stateMachineHaveLast = false;
											bool stateMachineEmitted = false;
											const bool stateMachineAlignCacheRequested =
												fasim_gasal2_score_prepass_state_machine_align_cache_runtime();
											const bool stateMachineGasal2TracebackShadowRequested =
												fasim_gasal2_score_prepass_state_machine_gasal2_traceback_shadow_runtime();
											const bool stateMachineSegmentTracebackShadowRequested =
												fasim_gasal2_score_prepass_state_machine_segment_traceback_shadow_runtime();
											const bool stateMachineExpandedSegmentTracebackShadowRequested =
												fasim_gasal2_score_prepass_state_machine_expanded_segment_traceback_shadow_runtime();
												const bool scorePrepassStateMachineCandidateCoverageRequested =
													fasim_gasal2_cpu_authority_candidate_coverage_shadow_runtime();
												const bool scorePrepassStateMachineSelectedOnlyCoverageRequested =
													fasim_gasal2_cpu_authority_selected_only_coverage_shadow_runtime();
											if (stateMachineAlignCacheRequested)
											{
												longQueryStreamingScoreInfoShadowStats
													.score_prepass_state_machine_shadow_cpu_align_cache_requested = 1;
											}
											if (stateMachineGasal2TracebackShadowRequested)
											{
												longQueryStreamingScoreInfoShadowStats
													.score_prepass_state_machine_shadow_gasal2_traceback_requested = 1;
											}
											if (stateMachineSegmentTracebackShadowRequested)
											{
												longQueryStreamingScoreInfoShadowStats
													.score_prepass_state_machine_shadow_segment_traceback_requested = 1;
											}
											if (stateMachineExpandedSegmentTracebackShadowRequested)
											{
												longQueryStreamingScoreInfoShadowStats
													.score_prepass_state_machine_shadow_expanded_segment_traceback_requested = 1;
											}
												if (scorePrepassStateMachineCandidateCoverageRequested)
												{
													const uint64_t coverageCandidateAttemptCount =
														scorePrepassStateMachineSelectedOnlyCoverageRequested ?
														static_cast<uint64_t>(
															flushReplaySelectedAttemptOrdinals.size()) :
														static_cast<uint64_t>(
															stateMachinePrefixAttemptOrdinals.size());
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_candidate_coverage_requested = 1;
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_candidate_coverage_active = 1;
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_candidate_coverage_scoreinfos +=
														static_cast<uint64_t>(flushProbeScoreInfoTaskIndexes.size());
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_candidate_coverage_attempts +=
														static_cast<uint64_t>(flushProbeAttempts.size());
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_candidate_coverage_candidate_attempts +=
														coverageCandidateAttemptCount;
												}
											std::map<std::pair<size_t, std::pair<int, int> >,
											         StripedSmithWaterman::Alignment>
												stateMachineAlignCache;
											std::vector<FasimGasal2Attempt>
												stateMachineGasal2TracebackAttempts;
											std::vector<size_t>
												stateMachineGasal2TracebackTaskIndexes;
											std::vector<StripedSmithWaterman::Alignment>
												stateMachineGasal2TracebackCpuAlignments;
											std::vector<size_t> stateMachineAttemptSegmentIndexes(
												flushProbeAttempts.size(),
												static_cast<size_t>(-1));
											if (stateMachineSegmentTracebackShadowRequested)
											{
												for (size_t selectedOrdinalIndex = 0;
												     selectedOrdinalIndex <
												     flushReplaySelectedAttemptOrdinals.size();
												     ++selectedOrdinalIndex)
												{
													const size_t selectedOrdinal =
														flushReplaySelectedAttemptOrdinals[
															selectedOrdinalIndex];
													if (selectedOrdinal >= flushProbeAttempts.size() ||
													    selectedOrdinal >=
													    flushReplayAttemptSegmentIndexes.size())
													{
														continue;
													}
													const size_t selectedSegmentIndex =
														flushReplayAttemptSegmentIndexes[
															selectedOrdinal];
													if (selectedSegmentIndex ==
													        static_cast<size_t>(-1) ||
													    selectedSegmentIndex >=
													        flushProbeSegments.size())
													{
														continue;
													}
													const int selectedScoreInfo =
														flushProbeAttempts[
															selectedOrdinal].scoreinfo_index;
													size_t groupBegin = selectedOrdinal;
													while (groupBegin > 0 &&
													       flushProbeAttempts[
														       groupBegin - 1].scoreinfo_index ==
														       selectedScoreInfo)
													{
														--groupBegin;
													}
													for (size_t attemptOrdinal = groupBegin;
													     attemptOrdinal <= selectedOrdinal &&
													     attemptOrdinal < flushProbeAttempts.size();
													     ++attemptOrdinal)
													{
														if (stateMachineAttemptSegmentIndexes[
															    attemptOrdinal] ==
														    static_cast<size_t>(-1))
														{
															stateMachineAttemptSegmentIndexes[
																attemptOrdinal] =
																selectedSegmentIndex;
														}
													}
												}
											}
											if (stateMachineGasal2TracebackShadowRequested)
											{
												stateMachineGasal2TracebackAttempts.reserve(
													stateMachinePrefixAttemptOrdinals.size());
												stateMachineGasal2TracebackTaskIndexes.reserve(
													stateMachinePrefixAttemptOrdinals.size());
												stateMachineGasal2TracebackCpuAlignments.reserve(
													stateMachinePrefixAttemptOrdinals.size());
											}
											std::vector<unsigned char> stateMachinePrefixAttemptOrdinalSet;
											if (scorePrepassStateMachineCandidateCoverageRequested)
											{
												stateMachinePrefixAttemptOrdinalSet.assign(
													flushProbeAttempts.size(),
													static_cast<unsigned char>(0));
												const std::vector<size_t> &coverageAttemptOrdinals =
													scorePrepassStateMachineSelectedOnlyCoverageRequested ?
													flushReplaySelectedAttemptOrdinals :
													stateMachinePrefixAttemptOrdinals;
												for (size_t prefixIndex = 0;
												     prefixIndex < coverageAttemptOrdinals.size();
												     ++prefixIndex)
												{
													const size_t prefixOrdinal =
														coverageAttemptOrdinals[prefixIndex];
													if (prefixOrdinal <
													    stateMachinePrefixAttemptOrdinalSet.size())
													{
														stateMachinePrefixAttemptOrdinalSet[
															prefixOrdinal] =
															static_cast<unsigned char>(1);
													}
												}
											}

												auto recordStateMachineCandidateCoverage =
													[&](size_t taskIndex,
													    int scoreInfoIndex,
													    size_t attemptOrdinal,
												    const char *reason)
											{
												if (!scorePrepassStateMachineCandidateCoverageRequested)
												{
														return;
													}
													++longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_candidate_coverage_selected;
													const bool stateMachineLegacySelectedAttemptCovered =
														attemptOrdinal <
														    stateMachinePrefixAttemptOrdinalSet.size() &&
														stateMachinePrefixAttemptOrdinalSet[attemptOrdinal] != 0;
													if (stateMachineLegacySelectedAttemptCovered)
													{
														++longQueryStreamingScoreInfoShadowStats
															.score_prepass_state_machine_shadow_candidate_coverage_covered;
													return;
												}
												++longQueryStreamingScoreInfoShadowStats
													.score_prepass_state_machine_shadow_candidate_coverage_false_negative_scoreinfos;
												if (longQueryStreamingScoreInfoShadowStats
												        .score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_task < 0)
												{
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_task =
														static_cast<int64_t>(taskIndex);
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_scoreinfo =
														static_cast<int64_t>(scoreInfoIndex);
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_candidate_coverage_first_false_negative_reason =
														reason != NULL ? reason : "unknown";
													}
												};

												if (scorePrepassStateMachineCandidateCoverageRequested)
												{
													int coverageCurrentScoreInfo = -1;
													size_t coverageCurrentTask = 0;
													FasimGasal2Attempt coverageBestAttempt;
													FasimGasal2Attempt coverageLastAttempt;
													size_t coverageBestAttemptOrdinal =
														static_cast<size_t>(-1);
													size_t coverageLastAttemptOrdinal =
														static_cast<size_t>(-1);
													StripedSmithWaterman::Alignment
														coverageBestAlignment;
													StripedSmithWaterman::Alignment
														coverageLastAlignment;
													bool coverageHaveBest = false;
													bool coverageHaveLast = false;
													bool coverageEmitted = false;

													auto flushCoverageScoreInfo = [&]()
													{
														if (coverageCurrentScoreInfo < 0 ||
														    coverageCurrentTask >= shadowTaskCount)
														{
															coverageHaveBest = false;
															coverageHaveLast = false;
															coverageEmitted = false;
															coverageBestAlignment.Clear();
															coverageLastAlignment.Clear();
															return;
														}
														if (!coverageEmitted &&
														    coverageHaveBest)
														{
															recordStateMachineCandidateCoverage(
																coverageCurrentTask,
																coverageCurrentScoreInfo,
																coverageBestAttemptOrdinal,
																"best_fallback");
														}
														else if (!coverageEmitted &&
														         coverageHaveLast &&
														         coverageLastAlignment.sw_score != 0)
														{
															recordStateMachineCandidateCoverage(
																coverageCurrentTask,
																coverageCurrentScoreInfo,
																coverageLastAttemptOrdinal,
																"last_nonzero");
														}
														coverageHaveBest = false;
														coverageHaveLast = false;
														coverageEmitted = false;
														coverageBestAttempt = FasimGasal2Attempt();
														coverageLastAttempt = FasimGasal2Attempt();
														coverageBestAttemptOrdinal =
															static_cast<size_t>(-1);
														coverageLastAttemptOrdinal =
															static_cast<size_t>(-1);
														coverageBestAlignment.Clear();
														coverageLastAlignment.Clear();
													};

													for (size_t attemptOrdinal = 0;
													     attemptOrdinal < flushProbeAttempts.size();
													     ++attemptOrdinal)
													{
														const FasimGasal2Attempt &attempt =
															flushProbeAttempts[attemptOrdinal];
														if (attempt.scoreinfo_index < 0 ||
														    static_cast<size_t>(attempt.scoreinfo_index) >=
														    flushProbeScoreInfoTaskIndexes.size() ||
														    static_cast<size_t>(attempt.scoreinfo_index) >=
														    flushProbeScoreInfoScores.size())
														{
															continue;
														}
														const size_t taskIndex =
															flushProbeScoreInfoTaskIndexes[
																static_cast<size_t>(
																	attempt.scoreinfo_index)];
														if (taskIndex >= shadowTaskCount)
														{
															if (attempt.scoreinfo_index !=
															    coverageCurrentScoreInfo)
															{
																flushCoverageScoreInfo();
															}
															continue;
														}
														if (attempt.scoreinfo_index !=
														    coverageCurrentScoreInfo)
														{
															flushCoverageScoreInfo();
															coverageCurrentScoreInfo =
																attempt.scoreinfo_index;
															coverageCurrentTask = taskIndex;
														}
														if (coverageEmitted)
														{
															continue;
														}
														StreamTask &coverageTask = tasks[taskIndex];
														if (attempt.start < 0 ||
														    attempt.cutlength <= 0 ||
														    attempt.start + attempt.cutlength >
														        static_cast<int>(coverageTask.seq2.size()))
														{
															continue;
														}
														const std::pair<size_t, std::pair<int, int> >
															alignCacheKey =
																std::make_pair(
																	taskIndex,
																	std::make_pair(
																		attempt.start,
																		attempt.cutlength));
														StripedSmithWaterman::Alignment
															coverageAlignment;
														bool alignCacheHit = false;
														if (!alignCacheHit)
														{
															const std::string smallSeq =
																coverageTask.seq2.substr(
																	static_cast<size_t>(
																		attempt.start),
																	static_cast<size_t>(
																		attempt.cutlength));
															const std::chrono::steady_clock::time_point
																alignStart =
																	std::chrono::steady_clock::now();
															aligner.Align(lncSeq.c_str(),
															              smallSeq.c_str(),
															              smallSeq.size(),
															              filter,
															              &coverageAlignment,
															              15);
															longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_candidate_coverage_cpu_align_seconds +=
																fasim_seconds_since(alignStart);
															++longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_candidate_coverage_cpu_align_attempts;
														}
														coverageLastAttempt = attempt;
														coverageLastAttemptOrdinal = attemptOrdinal;
														coverageLastAlignment = coverageAlignment;
														coverageHaveLast = true;
														if (coverageAlignment.sw_score >=
														    flushProbeScoreInfoScores[
															    static_cast<size_t>(
																    attempt.scoreinfo_index)])
														{
															recordStateMachineCandidateCoverage(
																taskIndex,
																attempt.scoreinfo_index,
																attemptOrdinal,
																"threshold");
															coverageEmitted = true;
															continue;
														}
														if (coverageAlignment.sw_score >
														        coverageBestAlignment.sw_score &&
														    coverageAlignment.ref_end ==
														        attempt.cutlength - 1)
														{
															coverageBestAttempt = attempt;
															coverageBestAttemptOrdinal =
																attemptOrdinal;
															coverageBestAlignment =
																coverageAlignment;
															coverageHaveBest = true;
														}
													}
													flushCoverageScoreInfo();
												}

												auto alignmentProbeKey =
													[](const StripedSmithWaterman::Alignment &alignment) -> std::string
												{
												std::ostringstream out;
												out << alignment.sw_score << ':'
												    << alignment.query_begin << ':'
												    << alignment.query_end << ':'
												    << alignment.ref_begin << ':'
												    << alignment.ref_end << ':'
												    << alignment.cigar.size();
												for (size_t cigarIndex = 0;
												     cigarIndex < alignment.cigar.size();
												     ++cigarIndex)
												{
													out << ':' << alignment.cigar[cigarIndex];
												}
												return out.str();
											};

										auto appendStateMachineTriplexes =
											[&](size_t taskIndex,
											    const FasimGasal2Attempt &attempt,
											    const StripedSmithWaterman::Alignment
												    &localAlignment)
										{
											if (taskIndex >=
											    scorePrepassStateMachineTriplexesByTask.size())
											{
												return;
											}
											if (localAlignment.sw_score == 0)
											{
												return;
											}
											StreamTask &emitTask = tasks[taskIndex];
											StripedSmithWaterman::Alignment emitAlignment =
												localAlignment;
											emitAlignment.ref_begin += attempt.start;
											emitAlignment.ref_end += attempt.start;
											const std::chrono::steady_clock::time_point
												convertStart =
													std::chrono::steady_clock::now();
											convertMyTriplex(
												emitAlignment,
												scorePrepassStateMachineTriplexesByTask[
													taskIndex],
												lncSeq,
												emitTask.seq2,
												*emitTask.srcSeq,
												nt_table,
												emitTask.dnaStartPos,
												emitTask.rule,
												emitTask.strand,
												emitTask.Para,
												paraList.penaltyT,
												paraList.penaltyC,
												paraList.ntMin,
												paraList.ntMax,
												writeFull);
											longQueryStreamingScoreInfoShadowStats
												.score_prepass_state_machine_shadow_convert_seconds +=
												fasim_seconds_since(convertStart);
										};

										auto flushStateMachineScoreInfo = [&]()
										{
											if (currentStateMachineScoreInfo < 0 ||
											    currentStateMachineTask >= shadowTaskCount)
											{
												stateMachineHaveBest = false;
												stateMachineHaveLast = false;
												stateMachineEmitted = false;
												stateMachineBestAlignment.Clear();
												stateMachineLastAlignment.Clear();
												return;
											}
												if (!stateMachineEmitted &&
												    stateMachineHaveBest)
												{
													appendStateMachineTriplexes(
														currentStateMachineTask,
														stateMachineBestAttempt,
													stateMachineBestAlignment);
											}
												else if (!stateMachineEmitted &&
												         stateMachineHaveLast &&
												         stateMachineLastAlignment.sw_score != 0)
												{
													appendStateMachineTriplexes(
														currentStateMachineTask,
														stateMachineLastAttempt,
													stateMachineLastAlignment);
											}
											stateMachineHaveBest = false;
											stateMachineHaveLast = false;
											stateMachineEmitted = false;
											stateMachineBestAttempt = FasimGasal2Attempt();
											stateMachineLastAttempt = FasimGasal2Attempt();
											stateMachineBestAlignment.Clear();
											stateMachineLastAlignment.Clear();
										};

										for (size_t selectedIndex = 0;
										     selectedIndex <
										     stateMachinePrefixAttemptOrdinals.size();
										     ++selectedIndex)
										{
											const size_t attemptOrdinal =
												stateMachinePrefixAttemptOrdinals[
													selectedIndex];
											if (attemptOrdinal >= flushProbeAttempts.size())
											{
												continue;
											}
											const FasimGasal2Attempt &attempt =
												flushProbeAttempts[attemptOrdinal];
											if (attempt.scoreinfo_index < 0 ||
											    static_cast<size_t>(attempt.scoreinfo_index) >=
											    flushProbeScoreInfoTaskIndexes.size())
											{
												++longQueryStreamingScoreInfoShadowStats
													.score_prepass_state_machine_shadow_fallbacks;
												continue;
											}
											const size_t taskIndex =
												flushProbeScoreInfoTaskIndexes[
													static_cast<size_t>(
														attempt.scoreinfo_index)];
											if (taskIndex >= shadowTaskCount ||
											    taskIndex >=
											    scorePrepassStateMachineTriplexesByTask.size())
											{
												continue;
											}
											if (attempt.scoreinfo_index !=
											    currentStateMachineScoreInfo)
											{
												flushStateMachineScoreInfo();
												currentStateMachineScoreInfo =
													attempt.scoreinfo_index;
												currentStateMachineTask = taskIndex;
											}
											if (stateMachineEmitted)
											{
												continue;
											}
											StreamTask &shadowTask = tasks[taskIndex];
											if (attempt.start < 0 ||
											    attempt.cutlength <= 0 ||
											    attempt.start + attempt.cutlength >
											    static_cast<int>(shadowTask.seq2.size()))
											{
												++longQueryStreamingScoreInfoShadowStats
													.score_prepass_state_machine_shadow_fallbacks;
												continue;
											}
											const std::string smallSeq =
												shadowTask.seq2.substr(
													static_cast<size_t>(attempt.start),
													static_cast<size_t>(attempt.cutlength));
												StripedSmithWaterman::Alignment shadowAlignment;
												const std::pair<size_t, std::pair<int, int> >
													alignCacheKey =
														std::make_pair(
															taskIndex,
															std::make_pair(attempt.start,
															               attempt.cutlength));
												bool alignCacheHit = false;
												if (stateMachineAlignCacheRequested)
												{
													++longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_cpu_align_cache_lookups;
													std::map<std::pair<size_t, std::pair<int, int> >,
													         StripedSmithWaterman::Alignment>::const_iterator
														cacheIt = stateMachineAlignCache.find(alignCacheKey);
													if (cacheIt != stateMachineAlignCache.end())
													{
														shadowAlignment = cacheIt->second;
														alignCacheHit = true;
														++longQueryStreamingScoreInfoShadowStats
															.score_prepass_state_machine_shadow_cpu_align_cache_hits;
													}
												}
												if (!alignCacheHit)
												{
													const std::chrono::steady_clock::time_point
														alignStart =
															std::chrono::steady_clock::now();
													aligner.Align(lncSeq.c_str(),
													              smallSeq.c_str(),
													              smallSeq.size(),
													              filter,
													              &shadowAlignment,
													              15);
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_cpu_align_seconds +=
														fasim_seconds_since(alignStart);
													++longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_cpu_align_attempts;
													if (stateMachineAlignCacheRequested)
													{
														++longQueryStreamingScoreInfoShadowStats
															.score_prepass_state_machine_shadow_cpu_align_cache_misses;
														stateMachineAlignCache[alignCacheKey] =
															shadowAlignment;
													}
												}
												if (stateMachineGasal2TracebackShadowRequested)
												{
													stateMachineGasal2TracebackAttempts.push_back(
														attempt);
													stateMachineGasal2TracebackTaskIndexes.push_back(
														taskIndex);
													stateMachineGasal2TracebackCpuAlignments.push_back(
														shadowAlignment);
												}
												if (stateMachineSegmentTracebackShadowRequested)
												{
													++longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_segment_traceback_attempts;
													const std::chrono::steady_clock::time_point
														segmentTracebackStart =
															std::chrono::steady_clock::now();
													bool segmentTracebackMismatch = false;
													if (attemptOrdinal >=
													        stateMachineAttemptSegmentIndexes.size() ||
													    stateMachineAttemptSegmentIndexes[attemptOrdinal] ==
													        static_cast<size_t>(-1) ||
													    stateMachineAttemptSegmentIndexes[attemptOrdinal] >=
													        flushProbeSegments.size())
													{
														++longQueryStreamingScoreInfoShadowStats
															.score_prepass_state_machine_shadow_segment_traceback_missing_segment;
														segmentTracebackMismatch = true;
													}
													else
													{
														const FasimGasal2LongQuerySegment &segment =
															flushProbeSegments[
																stateMachineAttemptSegmentIndexes[
																	attemptOrdinal]];
														StripedSmithWaterman::Alignment
															segmentAlignment;
														aligner.Align(
															segment.query_segment.c_str(),
															smallSeq.c_str(),
															smallSeq.size(),
															filter,
															&segmentAlignment,
															15);
														if (segmentAlignment.query_begin >= 0)
														{
															segmentAlignment.query_begin +=
																static_cast<int32_t>(
																	segment.global_query_start);
														}
														if (segmentAlignment.query_end >= 0)
														{
															segmentAlignment.query_end +=
																static_cast<int32_t>(
																	segment.global_query_start);
														}
														const int32_t segmentQueryBegin =
															static_cast<int32_t>(
																segment.global_query_start);
														const int32_t segmentQueryEnd =
															segmentQueryBegin +
															static_cast<int32_t>(
																segment.query_segment.size()) - 1;
														if ((shadowAlignment.query_begin >= 0 &&
														     shadowAlignment.query_begin <
														     segmentQueryBegin) ||
														    (shadowAlignment.query_end >= 0 &&
														     shadowAlignment.query_end >
														     segmentQueryEnd))
														{
															++longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_segment_traceback_cpu_query_outside_segment;
														}
														if (shadowAlignment.sw_score !=
														    segmentAlignment.sw_score)
														{
															++longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_segment_traceback_score_mismatches;
														}
														if (shadowAlignment.query_begin !=
														        segmentAlignment.query_begin ||
														    shadowAlignment.query_end !=
														        segmentAlignment.query_end ||
														    shadowAlignment.ref_begin !=
														        segmentAlignment.ref_begin ||
														    shadowAlignment.ref_end !=
														        segmentAlignment.ref_end)
														{
															++longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_segment_traceback_endpoint_mismatches;
														}
														if (shadowAlignment.cigar !=
														    segmentAlignment.cigar)
														{
															++longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_segment_traceback_cigar_mismatches;
														}
														if (alignmentProbeKey(shadowAlignment) !=
														    alignmentProbeKey(segmentAlignment))
														{
															++longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_segment_traceback_alignment_mismatches;
															segmentTracebackMismatch = true;
														}
														std::vector<triplex> cpuTriplexes;
														std::vector<triplex> segmentTriplexes;
														convertMyTriplex(
															shadowAlignment,
															cpuTriplexes,
															lncSeq,
															shadowTask.seq2,
															*shadowTask.srcSeq,
															nt_table,
															shadowTask.dnaStartPos,
															shadowTask.rule,
															shadowTask.strand,
															shadowTask.Para,
															paraList.penaltyT,
															paraList.penaltyC,
															paraList.ntMin,
															paraList.ntMax,
															false);
														convertMyTriplex(
															segmentAlignment,
															segmentTriplexes,
															lncSeq,
															shadowTask.seq2,
															*shadowTask.srcSeq,
															nt_table,
															shadowTask.dnaStartPos,
															shadowTask.rule,
															shadowTask.strand,
															shadowTask.Para,
															paraList.penaltyT,
															paraList.penaltyC,
															paraList.ntMin,
															paraList.ntMax,
															false);
														if (!triplex_probe_equal(cpuTriplexes,
														                         segmentTriplexes))
														{
															segmentTracebackMismatch = true;
														}
													}
													if (segmentTracebackMismatch)
													{
														++longQueryStreamingScoreInfoShadowStats
															.score_prepass_state_machine_shadow_segment_traceback_triplex_mismatches;
													}
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_segment_traceback_seconds +=
														fasim_seconds_since(segmentTracebackStart);
												}
												if (stateMachineExpandedSegmentTracebackShadowRequested)
												{
													++longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_expanded_segment_traceback_attempts;
													const std::chrono::steady_clock::time_point
														expandedSegmentTracebackStart =
															std::chrono::steady_clock::now();
													StripedSmithWaterman::Alignment
														expandedSegmentAlignment;
													aligner.Align(
														lncSeq.c_str(),
														smallSeq.c_str(),
														smallSeq.size(),
														filter,
														&expandedSegmentAlignment,
														15);
													if (shadowAlignment.query_begin < 0 ||
													    shadowAlignment.query_end < 0)
													{
														++longQueryStreamingScoreInfoShadowStats
															.score_prepass_state_machine_shadow_expanded_segment_traceback_cpu_query_outside_expanded_segment;
													}
													else if (attemptOrdinal <
													             stateMachineAttemptSegmentIndexes.size() &&
													         stateMachineAttemptSegmentIndexes[attemptOrdinal] !=
													             static_cast<size_t>(-1) &&
													         stateMachineAttemptSegmentIndexes[attemptOrdinal] <
													             flushProbeSegments.size())
													{
														const FasimGasal2LongQuerySegment &segment =
															flushProbeSegments[
																stateMachineAttemptSegmentIndexes[
																	attemptOrdinal]];
														const size_t segmentBegin =
															segment.global_query_start;
														const size_t segmentEnd =
															segmentBegin +
															segment.query_segment.size() - 1;
														const size_t cpuBegin =
															static_cast<size_t>(
																shadowAlignment.query_begin);
														const size_t cpuEnd =
															static_cast<size_t>(
																shadowAlignment.query_end);
														const size_t requiredBegin =
															std::min(segmentBegin, cpuBegin);
														const size_t requiredEnd =
															std::max(segmentEnd, cpuEnd);
														const size_t requiredLen =
															requiredEnd - requiredBegin + 1;
														if (requiredLen >
														    longQueryStreamingScoreInfoShadowStats
														        .score_prepass_state_machine_shadow_expanded_segment_traceback_required_max_len)
														{
															longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_expanded_segment_traceback_required_max_len =
																static_cast<uint64_t>(requiredLen);
														}
														if (requiredLen >
														    static_cast<size_t>(
														        fasim_gasal2_max_query_len_runtime()))
														{
															++longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_expanded_segment_traceback_required_over_gasal2_limit;
														}
													}
													if (shadowAlignment.sw_score !=
													    expandedSegmentAlignment.sw_score)
													{
														++longQueryStreamingScoreInfoShadowStats
															.score_prepass_state_machine_shadow_expanded_segment_traceback_score_mismatches;
													}
													if (shadowAlignment.query_begin !=
													        expandedSegmentAlignment.query_begin ||
													    shadowAlignment.query_end !=
													        expandedSegmentAlignment.query_end ||
													    shadowAlignment.ref_begin !=
													        expandedSegmentAlignment.ref_begin ||
													    shadowAlignment.ref_end !=
													        expandedSegmentAlignment.ref_end)
													{
														++longQueryStreamingScoreInfoShadowStats
															.score_prepass_state_machine_shadow_expanded_segment_traceback_endpoint_mismatches;
													}
													if (shadowAlignment.cigar !=
													    expandedSegmentAlignment.cigar)
													{
														++longQueryStreamingScoreInfoShadowStats
															.score_prepass_state_machine_shadow_expanded_segment_traceback_cigar_mismatches;
													}
													if (alignmentProbeKey(shadowAlignment) !=
													    alignmentProbeKey(expandedSegmentAlignment))
													{
														++longQueryStreamingScoreInfoShadowStats
															.score_prepass_state_machine_shadow_expanded_segment_traceback_alignment_mismatches;
													}
													std::vector<triplex> cpuTriplexes;
													std::vector<triplex> expandedSegmentTriplexes;
													convertMyTriplex(
														shadowAlignment,
														cpuTriplexes,
														lncSeq,
														shadowTask.seq2,
														*shadowTask.srcSeq,
														nt_table,
														shadowTask.dnaStartPos,
														shadowTask.rule,
														shadowTask.strand,
														shadowTask.Para,
														paraList.penaltyT,
														paraList.penaltyC,
														paraList.ntMin,
														paraList.ntMax,
														false);
													convertMyTriplex(
														expandedSegmentAlignment,
														expandedSegmentTriplexes,
														lncSeq,
														shadowTask.seq2,
														*shadowTask.srcSeq,
														nt_table,
														shadowTask.dnaStartPos,
														shadowTask.rule,
														shadowTask.strand,
														shadowTask.Para,
														paraList.penaltyT,
														paraList.penaltyC,
														paraList.ntMin,
														paraList.ntMax,
														false);
													if (!triplex_probe_equal(cpuTriplexes,
													                         expandedSegmentTriplexes))
													{
														++longQueryStreamingScoreInfoShadowStats
															.score_prepass_state_machine_shadow_expanded_segment_traceback_triplex_mismatches;
													}
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_expanded_segment_traceback_seconds +=
														fasim_seconds_since(expandedSegmentTracebackStart);
												}
												stateMachineLastAttempt = attempt;
											stateMachineLastAlignment = shadowAlignment;
											stateMachineHaveLast = true;
												if (shadowAlignment.sw_score >=
												    flushProbeScoreInfoScores[
													    static_cast<size_t>(
														    attempt.scoreinfo_index)])
												{
													appendStateMachineTriplexes(
														taskIndex,
														attempt,
													shadowAlignment);
												stateMachineEmitted = true;
												continue;
											}
											if (shadowAlignment.sw_score >
											        stateMachineBestAlignment.sw_score &&
											    shadowAlignment.ref_end ==
											        attempt.cutlength - 1)
											{
												stateMachineBestAttempt = attempt;
												stateMachineBestAlignment = shadowAlignment;
												stateMachineHaveBest = true;
											}
										}
											flushStateMachineScoreInfo();
											if (stateMachineAlignCacheRequested)
											{
												longQueryStreamingScoreInfoShadowStats
													.score_prepass_state_machine_shadow_cpu_align_cache_unique_keys +=
													static_cast<uint64_t>(stateMachineAlignCache.size());
											}
											if (stateMachineGasal2TracebackShadowRequested &&
											    !stateMachineGasal2TracebackAttempts.empty())
											{
												const std::chrono::steady_clock::time_point
													gasal2TracebackStart =
														std::chrono::steady_clock::now();
												std::vector<FasimGasal2SelectedAlignment>
													gasal2TracebackSelected;
												std::string gasal2TracebackError;
												longQueryStreamingScoreInfoShadowStats
													.score_prepass_state_machine_shadow_gasal2_traceback_attempts +=
													static_cast<uint64_t>(
														stateMachineGasal2TracebackAttempts.size());
												const bool gasal2TracebackOk =
													fasim_gasal2_align_attempts(
														lncSeq,
														stateMachineGasal2TracebackAttempts,
														&gasal2TracebackSelected,
														&gasal2TracebackError);
												longQueryStreamingScoreInfoShadowStats
													.score_prepass_state_machine_shadow_gasal2_traceback_seconds +=
													fasim_seconds_since(gasal2TracebackStart);
												if (!gasal2TracebackOk)
												{
													++longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_gasal2_traceback_fallbacks;
												}
												else
												{
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_gasal2_traceback_selected +=
														static_cast<uint64_t>(
															gasal2TracebackSelected.size());
													std::map<std::pair<int, std::pair<int, int> >,
													         StripedSmithWaterman::Alignment>
														gasal2AlignmentByAttempt;
													for (size_t gasalIndex = 0;
													     gasalIndex < gasal2TracebackSelected.size();
													     ++gasalIndex)
													{
														const FasimGasal2SelectedAlignment &selected =
															gasal2TracebackSelected[gasalIndex];
														gasal2AlignmentByAttempt[
															std::make_pair(
																selected.scoreinfo_index,
																std::make_pair(selected.start,
																               selected.cutlength))] =
															selected.alignment;
													}
													for (size_t ai = 0;
													     ai < stateMachineGasal2TracebackAttempts.size();
													     ++ai)
													{
														const FasimGasal2Attempt &attempt =
															stateMachineGasal2TracebackAttempts[ai];
														std::map<std::pair<int, std::pair<int, int> >,
														         StripedSmithWaterman::Alignment>::const_iterator
															gasalIt =
																gasal2AlignmentByAttempt.find(
																	std::make_pair(
																		attempt.scoreinfo_index,
																		std::make_pair(attempt.start,
																		               attempt.cutlength)));
														if (gasalIt == gasal2AlignmentByAttempt.end())
														{
															++longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_gasal2_traceback_alignment_mismatches;
															++longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_gasal2_traceback_triplex_mismatches;
															continue;
														}
														const StripedSmithWaterman::Alignment &cpuAlignment =
															stateMachineGasal2TracebackCpuAlignments[ai];
														const StripedSmithWaterman::Alignment &gasalAlignment =
															gasalIt->second;
														if (alignmentProbeKey(cpuAlignment) !=
														    alignmentProbeKey(gasalAlignment))
														{
															++longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_gasal2_traceback_alignment_mismatches;
														}
														const size_t taskIndex =
															stateMachineGasal2TracebackTaskIndexes[ai];
														if (taskIndex >= tasks.size())
														{
															++longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_gasal2_traceback_triplex_mismatches;
															continue;
														}
														StreamTask &compareTask = tasks[taskIndex];
														std::vector<triplex> cpuTriplexes;
														std::vector<triplex> gasalTriplexes;
														convertMyTriplex(
															cpuAlignment,
															cpuTriplexes,
															lncSeq,
															compareTask.seq2,
															*compareTask.srcSeq,
															nt_table,
															compareTask.dnaStartPos,
															compareTask.rule,
															compareTask.strand,
															compareTask.Para,
															paraList.penaltyT,
															paraList.penaltyC,
															paraList.ntMin,
															paraList.ntMax,
															false);
														convertMyTriplex(
															gasalAlignment,
															gasalTriplexes,
															lncSeq,
															compareTask.seq2,
															*compareTask.srcSeq,
															nt_table,
															compareTask.dnaStartPos,
															compareTask.rule,
															compareTask.strand,
															compareTask.Para,
															paraList.penaltyT,
															paraList.penaltyC,
															paraList.ntMin,
															paraList.ntMax,
															false);
														if (!triplex_probe_equal(cpuTriplexes,
														                         gasalTriplexes))
														{
															++longQueryStreamingScoreInfoShadowStats
																.score_prepass_state_machine_shadow_gasal2_traceback_triplex_mismatches;
														}
													}
												}
											}
											const std::chrono::steady_clock::time_point
											filterStart =
												std::chrono::steady_clock::now();
										for (size_t taskIndex = 0;
										     taskIndex < shadowTaskCount;
										     ++taskIndex)
										{
											std::vector<triplex> &shadowTriplexes =
												scorePrepassStateMachineTriplexesByTask[taskIndex];
											std::sort(shadowTriplexes.begin(),
											          shadowTriplexes.end(),
											          compMyTriplexMultiple);
											shadowTriplexes.erase(
												std::unique(shadowTriplexes.begin(),
												            shadowTriplexes.end(),
												            sameMyTriplex),
												shadowTriplexes.end());
											std::sort(shadowTriplexes.begin(),
											          shadowTriplexes.end(),
											          compMyTriplexMultiple2);
											shadowTriplexes.erase(
												std::unique(shadowTriplexes.begin(),
												            shadowTriplexes.end(),
												            sameMyTriplex),
												shadowTriplexes.end());
											std::sort(shadowTriplexes.begin(),
											          shadowTriplexes.end(),
											          compMyTriplexSingle);
											std::vector<triplex> filteredTriplexes;
											filteredTriplexes.reserve(shadowTriplexes.size());
											const size_t topLimit =
												std::min(shadowTriplexes.size(),
												         static_cast<size_t>(N));
											for (size_t replayIndex = 0;
											     replayIndex < topLimit;
											     ++replayIndex)
											{
												const triplex &atr =
													shadowTriplexes[replayIndex];
												if (atr.identity >= paraList.minIdentity &&
												    atr.tri_score >= paraList.minStability &&
												    atr.nt >= paraList.ntMin)
												{
													filteredTriplexes.push_back(atr);
												}
											}
											shadowTriplexes.swap(filteredTriplexes);
											scorePrepassStateMachineTaskCovered[taskIndex] =
												static_cast<unsigned char>(1);
										}
										longQueryStreamingScoreInfoShadowStats
											.score_prepass_state_machine_shadow_convert_seconds +=
											fasim_seconds_since(filterStart);
									}
									longQueryStreamingScoreInfoShadowStats
										.score_prepass_state_machine_shadow_total_seconds +=
										fasim_seconds_since(stateMachineStart);
								}
								if (!flushReplayTriplexesByTask.empty())
								{
								const std::chrono::steady_clock::time_point replayStart =
									std::chrono::steady_clock::now();
								longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_replay_probe_requested += 1;
								size_t replayTaskCount =
									fasim_long_query_streaming_scoreinfo_flush_segmented_replay_probe_max_tasks_runtime();
								if (replayTaskCount == 0 ||
								    replayTaskCount > tasks.size())
								{
									replayTaskCount = tasks.size();
								}
								longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_replay_probe_tasks +=
									static_cast<uint64_t>(replayTaskCount);
								longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_replay_probe_selected_attempts +=
									flushReplayRawSelectedAttempts;
								std::sort(flushReplaySelectedAttemptOrdinals.begin(),
								          flushReplaySelectedAttemptOrdinals.end());
								if (!flushSelectedOnlyReplayTriplexesByTask.empty())
								{
									const std::chrono::steady_clock::time_point selectedOnlyReplayStart =
										std::chrono::steady_clock::now();
									longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_selected_only_replay_probe_requested += 1;
									size_t selectedOnlyReplayTaskCount =
										fasim_long_query_streaming_scoreinfo_flush_segmented_replay_probe_max_tasks_runtime();
									if (selectedOnlyReplayTaskCount == 0 ||
									    selectedOnlyReplayTaskCount > tasks.size())
									{
										selectedOnlyReplayTaskCount = tasks.size();
									}
									longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_selected_only_replay_probe_tasks +=
										static_cast<uint64_t>(selectedOnlyReplayTaskCount);
									longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_selected_only_replay_probe_selected_attempts +=
										flushReplayRawSelectedAttempts;
									std::vector<unsigned char> selectedOnlyTaskHasSelected(
										tasks.size(),
										static_cast<unsigned char>(0));
									std::vector<unsigned char> selectedOnlyScoreInfoSeen(
										flushProbeScoreInfoTaskIndexes.size(),
										static_cast<unsigned char>(0));
									const int8_t nt_table[128] = {
										4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
										4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
										4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
										4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
										4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
										4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
										4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4
										};
										auto selectedOnlyReplayAttemptProvenance =
											[](const FasimGasal2Attempt &attempt,
											   const StripedSmithWaterman::Alignment &alignment)
										{
											std::ostringstream out;
											out << "scoreinfo=" << attempt.scoreinfo_index
											    << ";start=" << attempt.start
											    << ";cutlength=" << attempt.cutlength
											    << ";sw_score=" << alignment.sw_score
											    << ";ref_begin=" << alignment.ref_begin
											    << ";ref_end=" << alignment.ref_end
											    << ";query_begin=" << alignment.query_begin
											    << ";query_end=" << alignment.query_end;
											return out.str();
										};
										for (size_t selectedIndex = 0;
									     selectedIndex < flushReplaySelectedAttemptOrdinals.size();
									     ++selectedIndex)
									{
										const size_t attemptOrdinal =
											flushReplaySelectedAttemptOrdinals[selectedIndex];
										if (attemptOrdinal >= flushProbeAttempts.size() ||
										    attemptOrdinal >= flushProbeAttemptTaskIndexes.size())
										{
											++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks;
											continue;
										}
										const size_t taskIndex =
											flushProbeAttemptTaskIndexes[attemptOrdinal];
										if (taskIndex >= selectedOnlyReplayTaskCount ||
										    taskIndex >= flushSelectedOnlyReplayTriplexesByTask.size())
										{
											continue;
										}
										const FasimGasal2Attempt &attempt =
											flushProbeAttempts[attemptOrdinal];
										if (attempt.scoreinfo_index >= 0 &&
										    static_cast<size_t>(attempt.scoreinfo_index) <
										    selectedOnlyScoreInfoSeen.size() &&
										    selectedOnlyScoreInfoSeen[
											    static_cast<size_t>(attempt.scoreinfo_index)] == 0)
										{
											selectedOnlyScoreInfoSeen[
												static_cast<size_t>(attempt.scoreinfo_index)] =
												static_cast<unsigned char>(1);
											++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_selected_only_replay_probe_selected_scoreinfos;
										}
										StreamTask &replayTask = tasks[taskIndex];
										if (selectedOnlyTaskHasSelected[taskIndex] == 0)
										{
											selectedOnlyTaskHasSelected[taskIndex] =
												static_cast<unsigned char>(1);
											++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_selected;
										}
										if (attempt.start < 0 ||
										    attempt.cutlength <= 0 ||
										    attempt.start + attempt.cutlength >
										    static_cast<int>(replayTask.seq2.size()))
										{
											++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_selected_only_replay_probe_fallbacks;
											continue;
										}
										std::string replaySmallSeq =
											replayTask.seq2.substr(
												static_cast<size_t>(attempt.start),
												static_cast<size_t>(attempt.cutlength));
										StripedSmithWaterman::Alignment replayAlignment;
										aligner.Align(lncSeq.c_str(),
										              replaySmallSeq.c_str(),
										              replaySmallSeq.size(),
										              filter,
										              &replayAlignment,
										              15);
										++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_selected_only_replay_probe_align_attempts;
										if (replayAlignment.sw_score == 0)
										{
											continue;
										}
											StripedSmithWaterman::Alignment emitAlignment =
												replayAlignment;
											emitAlignment.ref_begin += attempt.start;
											emitAlignment.ref_end += attempt.start;
											const size_t selectedOnlyBefore =
												flushSelectedOnlyReplayTriplexesByTask[taskIndex].size();
											convertMyTriplex(emitAlignment,
											                 flushSelectedOnlyReplayTriplexesByTask[taskIndex],
											                 lncSeq,
										                 replayTask.seq2,
										                 *replayTask.srcSeq,
										                 nt_table,
										                 replayTask.dnaStartPos,
										                 replayTask.rule,
										                 replayTask.strand,
										                 replayTask.Para,
										                 paraList.penaltyT,
										                 paraList.penaltyC,
										                 paraList.ntMin,
											                 paraList.ntMax,
											                 writeFull);
											const size_t selectedOnlyAfter =
												flushSelectedOnlyReplayTriplexesByTask[taskIndex].size();
											if (taskIndex < flushSelectedOnlyReplayTriplexProvenanceByTask.size())
											{
												for (size_t provenanceIndex = selectedOnlyBefore;
												     provenanceIndex < selectedOnlyAfter;
												     ++provenanceIndex)
												{
													flushSelectedOnlyReplayTriplexProvenanceByTask[taskIndex]
														.push_back(
															selectedOnlyReplayAttemptProvenance(
																attempt,
																replayAlignment));
												}
											}
											if (taskIndex < flushSelectedOnlyReplayTriplexScoreInfoByTask.size())
											{
												for (size_t scoreInfoIndex = selectedOnlyBefore;
												     scoreInfoIndex < selectedOnlyAfter;
												     ++scoreInfoIndex)
												{
													flushSelectedOnlyReplayTriplexScoreInfoByTask[taskIndex]
														.push_back(attempt.scoreinfo_index);
												}
											}
										}
										for (size_t taskIndex = 0;
										     taskIndex < selectedOnlyReplayTaskCount;
										     ++taskIndex)
										{
											std::vector<triplex> &selectedOnlyTriplexes =
												flushSelectedOnlyReplayTriplexesByTask[taskIndex];
											std::vector<std::string> &selectedOnlyProvenance =
												flushSelectedOnlyReplayTriplexProvenanceByTask[taskIndex];
											std::vector<int> &selectedOnlyScoreInfos =
												flushSelectedOnlyReplayTriplexScoreInfoByTask[taskIndex];
											struct SelectedOnlyAnnotatedTriplex
											{
												triplex value;
												std::string provenance;
												int scoreinfo;
											};
											std::vector<SelectedOnlyAnnotatedTriplex>
												selectedOnlyAnnotatedTriplexes;
											selectedOnlyAnnotatedTriplexes.reserve(selectedOnlyTriplexes.size());
											for (size_t replayIndex = 0;
											     replayIndex < selectedOnlyTriplexes.size();
											     ++replayIndex)
											{
												selectedOnlyAnnotatedTriplexes.push_back(
													SelectedOnlyAnnotatedTriplex{
														selectedOnlyTriplexes[replayIndex],
														replayIndex < selectedOnlyProvenance.size() ?
															selectedOnlyProvenance[replayIndex] :
															std::string("unknown"),
														replayIndex < selectedOnlyScoreInfos.size() ?
															selectedOnlyScoreInfos[replayIndex] : -1});
											}
											std::sort(
												selectedOnlyAnnotatedTriplexes.begin(),
												selectedOnlyAnnotatedTriplexes.end(),
												[](const SelectedOnlyAnnotatedTriplex &lhs,
												   const SelectedOnlyAnnotatedTriplex &rhs)
												{
													return compMyTriplexMultiple(lhs.value, rhs.value);
												});
											selectedOnlyAnnotatedTriplexes.erase(
												std::unique(
													selectedOnlyAnnotatedTriplexes.begin(),
													selectedOnlyAnnotatedTriplexes.end(),
													[](const SelectedOnlyAnnotatedTriplex &lhs,
													   const SelectedOnlyAnnotatedTriplex &rhs)
													{
														return sameMyTriplex(lhs.value, rhs.value);
													}),
												selectedOnlyAnnotatedTriplexes.end());
											std::sort(
												selectedOnlyAnnotatedTriplexes.begin(),
												selectedOnlyAnnotatedTriplexes.end(),
												[](const SelectedOnlyAnnotatedTriplex &lhs,
												   const SelectedOnlyAnnotatedTriplex &rhs)
												{
													return compMyTriplexMultiple2(lhs.value, rhs.value);
												});
											selectedOnlyAnnotatedTriplexes.erase(
												std::unique(
													selectedOnlyAnnotatedTriplexes.begin(),
													selectedOnlyAnnotatedTriplexes.end(),
													[](const SelectedOnlyAnnotatedTriplex &lhs,
													   const SelectedOnlyAnnotatedTriplex &rhs)
													{
														return sameMyTriplex(lhs.value, rhs.value);
													}),
												selectedOnlyAnnotatedTriplexes.end());
											std::sort(
												selectedOnlyAnnotatedTriplexes.begin(),
												selectedOnlyAnnotatedTriplexes.end(),
												[](const SelectedOnlyAnnotatedTriplex &lhs,
												   const SelectedOnlyAnnotatedTriplex &rhs)
												{
													return compMyTriplexSingle(lhs.value, rhs.value);
												});
											std::vector<triplex> selectedOnlyFilteredTriplexes;
											std::vector<std::string> selectedOnlyFilteredProvenance;
											std::vector<int> selectedOnlyFilteredScoreInfos;
											selectedOnlyFilteredTriplexes.reserve(
												selectedOnlyAnnotatedTriplexes.size());
											selectedOnlyFilteredProvenance.reserve(
												selectedOnlyAnnotatedTriplexes.size());
											selectedOnlyFilteredScoreInfos.reserve(
												selectedOnlyAnnotatedTriplexes.size());
											const size_t replayTopLimit =
												std::min(selectedOnlyAnnotatedTriplexes.size(),
												         static_cast<size_t>(N));
											for (size_t replayIndex = 0;
											     replayIndex < replayTopLimit;
											     ++replayIndex)
											{
												const triplex &atr =
													selectedOnlyAnnotatedTriplexes[replayIndex].value;
												if (atr.identity >= paraList.minIdentity &&
												    atr.tri_score >= paraList.minStability &&
												    atr.nt >= paraList.ntMin)
												{
													selectedOnlyFilteredTriplexes.push_back(atr);
													selectedOnlyFilteredProvenance.push_back(
														selectedOnlyAnnotatedTriplexes[replayIndex].provenance);
													selectedOnlyFilteredScoreInfos.push_back(
														selectedOnlyAnnotatedTriplexes[replayIndex].scoreinfo);
												}
											}
											selectedOnlyTriplexes.swap(selectedOnlyFilteredTriplexes);
											selectedOnlyProvenance.swap(selectedOnlyFilteredProvenance);
											selectedOnlyScoreInfos.swap(selectedOnlyFilteredScoreInfos);
											std::map<int, size_t> selectedOnlyTriplexesPerScoreInfo;
											for (size_t replayIndex = 0;
											     replayIndex < selectedOnlyScoreInfos.size();
											     ++replayIndex)
											{
												if (selectedOnlyScoreInfos[replayIndex] >= 0)
												{
													++selectedOnlyTriplexesPerScoreInfo[
														selectedOnlyScoreInfos[replayIndex]];
												}
											}
											for (std::map<int, size_t>::const_iterator scoreInfoIt =
											         selectedOnlyTriplexesPerScoreInfo.begin();
											     scoreInfoIt != selectedOnlyTriplexesPerScoreInfo.end();
											     ++scoreInfoIt)
											{
												if (scoreInfoIt->second > 1)
												{
													++longQueryStreamingScoreInfoShadowStats
														.realpath_extend_flush_segmented_selected_only_replay_probe_scoreinfos_with_multiple_triplexes;
													longQueryStreamingScoreInfoShadowStats
														.realpath_extend_flush_segmented_selected_only_replay_probe_extra_triplexes_from_repeated_scoreinfo +=
															static_cast<uint64_t>(scoreInfoIt->second - 1);
												}
											}
										if (selectedOnlyTriplexes.empty())
										{
											++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_selected_only_replay_probe_zero_triplex_tasks;
										}
										else
										{
											++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_selected_only_replay_probe_tasks_with_triplex;
										}
										flushSelectedOnlyReplayTaskCovered[taskIndex] =
											static_cast<unsigned char>(1);
										++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_selected_only_replay_probe_active;
									}
										longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_selected_only_replay_probe_seconds +=
											fasim_seconds_since(selectedOnlyReplayStart);
									}
									if (!flushGroupedSelectedReplayTriplexesByTask.empty())
									{
										const std::chrono::steady_clock::time_point groupedReplayStart =
											std::chrono::steady_clock::now();
										longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_grouped_selected_replay_probe_requested += 1;
										size_t groupedReplayTaskCount =
											fasim_long_query_streaming_scoreinfo_flush_segmented_replay_probe_max_tasks_runtime();
										if (groupedReplayTaskCount == 0 ||
										    groupedReplayTaskCount > tasks.size())
										{
											groupedReplayTaskCount = tasks.size();
										}
										longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks +=
											static_cast<uint64_t>(groupedReplayTaskCount);
										longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_attempts +=
											flushReplayRawSelectedAttempts;
										std::vector<unsigned char> groupedSelectedTaskHasSelected(
											tasks.size(),
											static_cast<unsigned char>(0));
										std::vector<unsigned char> groupedSelectedScoreInfoSeen(
											flushProbeScoreInfoTaskIndexes.size(),
											static_cast<unsigned char>(0));
										const int8_t nt_table[128] = {
											4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
											4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4
										};
										int currentGroupedScoreInfo = -1;
										size_t currentGroupedTask = 0;
										FasimGasal2SelectedAlignment groupedBestSelected;
										FasimGasal2SelectedAlignment groupedLastSelected;
										StripedSmithWaterman::Alignment groupedBestAlignment;
										StripedSmithWaterman::Alignment groupedLastAlignment;
										bool groupedHaveBest = false;
										bool groupedHaveLast = false;
										bool groupedEmitted = false;

										auto appendGroupedSelectedTriplexes =
											[&](size_t taskIndex,
											    StripedSmithWaterman::Alignment emitAlignment,
											    const FasimGasal2SelectedAlignment &emitSelected,
											    const StripedSmithWaterman::Alignment &localAlignment)
										{
											if (taskIndex >= flushGroupedSelectedReplayTriplexesByTask.size() ||
											    taskIndex >= flushGroupedSelectedReplayTriplexProvenanceByTask.size())
											{
												return;
											}
											StreamTask &emitTask = tasks[taskIndex];
											emitAlignment.ref_begin += emitSelected.start;
											emitAlignment.ref_end += emitSelected.start;
											const size_t before =
												flushGroupedSelectedReplayTriplexesByTask[taskIndex].size();
											convertMyTriplex(emitAlignment,
											                 flushGroupedSelectedReplayTriplexesByTask[taskIndex],
											                 lncSeq,
											                 emitTask.seq2,
											                 *emitTask.srcSeq,
											                 nt_table,
											                 emitTask.dnaStartPos,
											                 emitTask.rule,
											                 emitTask.strand,
											                 emitTask.Para,
											                 paraList.penaltyT,
											                 paraList.penaltyC,
											                 paraList.ntMin,
											                 paraList.ntMax,
											                 writeFull);
											const size_t after =
												flushGroupedSelectedReplayTriplexesByTask[taskIndex].size();
											for (size_t provenanceIndex = before;
											     provenanceIndex < after;
											     ++provenanceIndex)
											{
												std::ostringstream out;
												out << "scoreinfo=" << emitSelected.scoreinfo_index
												    << ";start=" << emitSelected.start
												    << ";cutlength=" << emitSelected.cutlength
												    << ";sw_score=" << localAlignment.sw_score
												    << ";ref_begin=" << localAlignment.ref_begin
												    << ";ref_end=" << localAlignment.ref_end
												    << ";query_begin=" << localAlignment.query_begin
												    << ";query_end=" << localAlignment.query_end;
												flushGroupedSelectedReplayTriplexProvenanceByTask[taskIndex]
													.push_back(out.str());
											}
										};

										auto flushGroupedSelectedScoreInfo = [&]()
										{
											if (currentGroupedScoreInfo < 0 ||
											    currentGroupedTask >= groupedReplayTaskCount)
											{
												groupedHaveBest = false;
												groupedHaveLast = false;
												groupedEmitted = false;
												groupedBestAlignment.Clear();
												groupedLastAlignment.Clear();
												return;
											}
											if (!groupedEmitted && groupedHaveBest)
											{
												appendGroupedSelectedTriplexes(
													currentGroupedTask,
													groupedBestAlignment,
													groupedBestSelected,
													groupedBestAlignment);
											}
											else if (!groupedEmitted &&
											         groupedHaveLast &&
											         groupedLastAlignment.sw_score != 0)
											{
												appendGroupedSelectedTriplexes(
													currentGroupedTask,
													groupedLastAlignment,
													groupedLastSelected,
													groupedLastAlignment);
											}
											groupedHaveBest = false;
											groupedHaveLast = false;
											groupedEmitted = false;
											groupedBestSelected = FasimGasal2SelectedAlignment();
											groupedLastSelected = FasimGasal2SelectedAlignment();
											groupedBestAlignment.Clear();
											groupedLastAlignment.Clear();
										};

										std::sort(flushReplaySelectedAttemptOrdinals.begin(),
										          flushReplaySelectedAttemptOrdinals.end());
										std::vector<unsigned char> groupedPrefixAttemptSelected(
											flushProbeAttempts.size(),
											static_cast<unsigned char>(0));
										std::vector<size_t> groupedPrefixAttemptOrdinals;
										groupedPrefixAttemptOrdinals.reserve(
											flushReplaySelectedAttemptOrdinals.size() * 2);
										for (size_t selectedOrdinalIndex = 0;
										     selectedOrdinalIndex < flushReplaySelectedAttemptOrdinals.size();
										     ++selectedOrdinalIndex)
										{
											const size_t selectedOrdinal =
												flushReplaySelectedAttemptOrdinals[selectedOrdinalIndex];
											if (selectedOrdinal >= flushProbeAttempts.size())
											{
												continue;
											}
											const int selectedScoreInfo =
												flushProbeAttempts[selectedOrdinal].scoreinfo_index;
											size_t groupBegin = selectedOrdinal;
											while (groupBegin > 0 &&
											       flushProbeAttempts[groupBegin - 1].scoreinfo_index ==
											           selectedScoreInfo)
											{
												--groupBegin;
											}
											for (size_t attemptOrdinal = groupBegin;
											     attemptOrdinal <= selectedOrdinal &&
											     attemptOrdinal < flushProbeAttempts.size();
											     ++attemptOrdinal)
											{
												if (groupedPrefixAttemptSelected[attemptOrdinal] == 0)
												{
													groupedPrefixAttemptSelected[attemptOrdinal] =
														static_cast<unsigned char>(1);
													groupedPrefixAttemptOrdinals.push_back(attemptOrdinal);
												}
											}
										}
										std::sort(groupedPrefixAttemptOrdinals.begin(),
										          groupedPrefixAttemptOrdinals.end());
										for (size_t selectedIndex = 0;
										     selectedIndex < groupedPrefixAttemptOrdinals.size();
										     ++selectedIndex)
										{
											const size_t attemptOrdinal =
												groupedPrefixAttemptOrdinals[selectedIndex];
											if (attemptOrdinal >= flushProbeAttempts.size())
											{
												continue;
											}
											const FasimGasal2Attempt &attempt =
												flushProbeAttempts[attemptOrdinal];
											if (attempt.scoreinfo_index < 0 ||
											    static_cast<size_t>(attempt.scoreinfo_index) >=
											    flushProbeScoreInfoTaskIndexes.size())
											{
												continue;
											}
											const size_t taskIndex =
												flushProbeScoreInfoTaskIndexes[
													static_cast<size_t>(attempt.scoreinfo_index)];
											if (taskIndex >= groupedReplayTaskCount)
											{
												continue;
											}
											if (attempt.scoreinfo_index != currentGroupedScoreInfo)
											{
												flushGroupedSelectedScoreInfo();
												currentGroupedScoreInfo = attempt.scoreinfo_index;
												currentGroupedTask = taskIndex;
											}
											if (groupedEmitted)
											{
												continue;
											}
											if (static_cast<size_t>(attempt.scoreinfo_index) <
											    groupedSelectedScoreInfoSeen.size() &&
											    groupedSelectedScoreInfoSeen[
												    static_cast<size_t>(attempt.scoreinfo_index)] == 0)
											{
												groupedSelectedScoreInfoSeen[
													static_cast<size_t>(attempt.scoreinfo_index)] =
													static_cast<unsigned char>(1);
												++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_grouped_selected_replay_probe_selected_scoreinfos;
											}
											if (groupedSelectedTaskHasSelected[taskIndex] == 0)
											{
												groupedSelectedTaskHasSelected[taskIndex] =
													static_cast<unsigned char>(1);
												++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_selected;
											}
											StreamTask &replayTask = tasks[taskIndex];
											if (attempt.start < 0 ||
											    attempt.cutlength <= 0 ||
											    attempt.start + attempt.cutlength >
											    static_cast<int>(replayTask.seq2.size()))
											{
												++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_grouped_selected_replay_probe_fallbacks;
												continue;
											}
											std::string replaySmallSeq =
												replayTask.seq2.substr(
													static_cast<size_t>(attempt.start),
													static_cast<size_t>(attempt.cutlength));
											StripedSmithWaterman::Alignment replayAlignment;
											aligner.Align(lncSeq.c_str(),
											              replaySmallSeq.c_str(),
											              replaySmallSeq.size(),
											              filter,
											              &replayAlignment,
											              15);
											++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_grouped_selected_replay_probe_align_attempts;
											FasimGasal2SelectedAlignment selected;
											selected.scoreinfo_index = attempt.scoreinfo_index;
											selected.cutlength = attempt.cutlength;
											selected.start = attempt.start;
											selected.selected = true;
											groupedLastSelected = selected;
											groupedLastAlignment = replayAlignment;
											groupedHaveLast = true;
											if (replayAlignment.sw_score >=
											    flushProbeScoreInfoScores[
												    static_cast<size_t>(attempt.scoreinfo_index)])
											{
												appendGroupedSelectedTriplexes(taskIndex,
												                              replayAlignment,
												                              selected,
												                              replayAlignment);
												groupedEmitted = true;
												continue;
											}
											if (replayAlignment.sw_score >
											    groupedBestAlignment.sw_score &&
											    replayAlignment.ref_end ==
											    attempt.cutlength - 1)
											{
												groupedBestSelected = selected;
												groupedBestAlignment = replayAlignment;
												groupedHaveBest = true;
											}
										}
										flushGroupedSelectedScoreInfo();
										for (size_t taskIndex = 0;
										     taskIndex < groupedReplayTaskCount;
										     ++taskIndex)
											{
												std::vector<triplex> &groupedTriplexes =
													flushGroupedSelectedReplayTriplexesByTask[taskIndex];
												std::vector<std::string> &groupedProvenance =
													flushGroupedSelectedReplayTriplexProvenanceByTask[taskIndex];
												std::vector<std::pair<triplex, std::string> >
													groupedAnnotatedTriplexes;
												groupedAnnotatedTriplexes.reserve(groupedTriplexes.size());
												for (size_t replayIndex = 0;
												     replayIndex < groupedTriplexes.size();
												     ++replayIndex)
												{
													groupedAnnotatedTriplexes.push_back(
														std::make_pair(
															groupedTriplexes[replayIndex],
															replayIndex < groupedProvenance.size() ?
																groupedProvenance[replayIndex] :
																std::string("unknown")));
												}
												std::sort(groupedAnnotatedTriplexes.begin(),
												          groupedAnnotatedTriplexes.end(),
												          [](const std::pair<triplex, std::string> &lhs,
												             const std::pair<triplex, std::string> &rhs)
												          {
													          return compMyTriplexMultiple(lhs.first,
													                                      rhs.first);
												          });
												groupedAnnotatedTriplexes.erase(
													std::unique(groupedAnnotatedTriplexes.begin(),
													            groupedAnnotatedTriplexes.end(),
													            [](const std::pair<triplex, std::string> &lhs,
													               const std::pair<triplex, std::string> &rhs)
													            {
														            return sameMyTriplex(lhs.first,
														                                 rhs.first);
													            }),
													groupedAnnotatedTriplexes.end());
												std::sort(groupedAnnotatedTriplexes.begin(),
												          groupedAnnotatedTriplexes.end(),
												          [](const std::pair<triplex, std::string> &lhs,
												             const std::pair<triplex, std::string> &rhs)
												          {
													          return compMyTriplexMultiple2(lhs.first,
													                                       rhs.first);
												          });
												groupedAnnotatedTriplexes.erase(
													std::unique(groupedAnnotatedTriplexes.begin(),
													            groupedAnnotatedTriplexes.end(),
													            [](const std::pair<triplex, std::string> &lhs,
													               const std::pair<triplex, std::string> &rhs)
													            {
														            return sameMyTriplex(lhs.first,
														                                 rhs.first);
													            }),
													groupedAnnotatedTriplexes.end());
												std::sort(groupedAnnotatedTriplexes.begin(),
												          groupedAnnotatedTriplexes.end(),
												          [](const std::pair<triplex, std::string> &lhs,
												             const std::pair<triplex, std::string> &rhs)
												          {
													          return compMyTriplexSingle(lhs.first,
													                                   rhs.first);
												          });
												std::vector<triplex> groupedFilteredTriplexes;
												std::vector<std::string> groupedFilteredProvenance;
												groupedFilteredTriplexes.reserve(
													groupedAnnotatedTriplexes.size());
												groupedFilteredProvenance.reserve(
													groupedAnnotatedTriplexes.size());
												const size_t replayTopLimit =
													std::min(groupedAnnotatedTriplexes.size(),
													         static_cast<size_t>(N));
												for (size_t replayIndex = 0;
												     replayIndex < replayTopLimit;
												     ++replayIndex)
												{
													const triplex &atr =
														groupedAnnotatedTriplexes[replayIndex].first;
													if (atr.identity >= paraList.minIdentity &&
													    atr.tri_score >= paraList.minStability &&
													    atr.nt >= paraList.ntMin)
													{
														groupedFilteredTriplexes.push_back(atr);
														groupedFilteredProvenance.push_back(
															groupedAnnotatedTriplexes[replayIndex].second);
													}
												}
												groupedTriplexes.swap(groupedFilteredTriplexes);
												groupedProvenance.swap(groupedFilteredProvenance);
											if (groupedTriplexes.empty())
											{
												++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_grouped_selected_replay_probe_zero_triplex_tasks;
											}
											else
											{
												++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_grouped_selected_replay_probe_tasks_with_triplex;
											}
											flushGroupedSelectedReplayTaskCovered[taskIndex] =
												static_cast<unsigned char>(1);
											++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_grouped_selected_replay_probe_active;
										}
										longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_grouped_selected_replay_probe_seconds +=
											fasim_seconds_since(groupedReplayStart);
									}
									std::vector<unsigned char> flushReplayExpandedAttemptSelected(
										flushProbeAttempts.size(),
									static_cast<unsigned char>(0));
								std::vector<size_t> flushReplayExpandedAttemptOrdinals;
								flushReplayExpandedAttemptOrdinals.reserve(
									flushProbeAttempts.size());
								for (size_t selectedOrdinalIndex = 0;
								     selectedOrdinalIndex <
								     flushReplaySelectedAttemptOrdinals.size();
								     ++selectedOrdinalIndex)
								{
									const size_t selectedOrdinal =
										flushReplaySelectedAttemptOrdinals[selectedOrdinalIndex];
									if (selectedOrdinal >= flushProbeAttempts.size())
									{
										continue;
									}
									const int selectedScoreInfo =
										flushProbeAttempts[selectedOrdinal].scoreinfo_index;
									size_t groupBegin = selectedOrdinal;
									while (groupBegin > 0 &&
									       flushProbeAttempts[groupBegin - 1].scoreinfo_index ==
									           selectedScoreInfo)
									{
										--groupBegin;
									}
									size_t groupEnd = selectedOrdinal + 1;
									while (groupEnd < flushProbeAttempts.size() &&
									       flushProbeAttempts[groupEnd].scoreinfo_index ==
									           selectedScoreInfo)
									{
										++groupEnd;
									}
									for (size_t attemptOrdinal = groupBegin;
									     attemptOrdinal < groupEnd;
									     ++attemptOrdinal)
									{
										if (flushReplayExpandedAttemptSelected[attemptOrdinal] == 0)
										{
											flushReplayExpandedAttemptSelected[attemptOrdinal] =
												static_cast<unsigned char>(1);
											flushReplayExpandedAttemptOrdinals.push_back(
												attemptOrdinal);
										}
									}
								}
								std::sort(flushReplayExpandedAttemptOrdinals.begin(),
								          flushReplayExpandedAttemptOrdinals.end());
								const int8_t nt_table[128] = {
									4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4
								};
								int currentReplayScoreInfo = -1;
								size_t currentReplayTask = 0;
								FasimGasal2SelectedAlignment replayBestSelected;
								FasimGasal2SelectedAlignment replayLastSelected;
								StripedSmithWaterman::Alignment replayBestAlignment;
								StripedSmithWaterman::Alignment replayLastAlignment;
								bool replayHaveBest = false;
								bool replayHaveLast = false;
								bool replayEmitted = false;

								auto replayAttemptProvenance =
									[](const FasimGasal2Attempt &attempt,
									   const StripedSmithWaterman::Alignment &alignment)
								{
									std::ostringstream out;
									out << "scoreinfo=" << attempt.scoreinfo_index
									    << ";start=" << attempt.start
									    << ";cutlength=" << attempt.cutlength
									    << ";sw_score=" << alignment.sw_score
									    << ";ref_begin=" << alignment.ref_begin
									    << ";ref_end=" << alignment.ref_end
									    << ";query_begin=" << alignment.query_begin
									    << ";query_end=" << alignment.query_end;
									return out.str();
								};

								auto appendReplayTriplexes =
									[&](size_t taskIndex,
									    StripedSmithWaterman::Alignment emitAlignment,
									    const FasimGasal2Attempt &attempt,
									    const StripedSmithWaterman::Alignment &localAlignment)
								{
									if (taskIndex >= flushReplayTriplexesByTask.size() ||
									    taskIndex >= flushReplayTriplexProvenanceByTask.size())
									{
										return;
									}
									StreamTask &emitTask = tasks[taskIndex];
									const size_t before =
										flushReplayTriplexesByTask[taskIndex].size();
									convertMyTriplex(emitAlignment,
									                 flushReplayTriplexesByTask[taskIndex],
									                 lncSeq,
									                 emitTask.seq2,
									                 *emitTask.srcSeq,
									                 nt_table,
									                 emitTask.dnaStartPos,
									                 emitTask.rule,
									                 emitTask.strand,
									                 emitTask.Para,
									                 paraList.penaltyT,
									                 paraList.penaltyC,
									                 paraList.ntMin,
									                 paraList.ntMax,
									                 writeFull);
									const size_t after =
										flushReplayTriplexesByTask[taskIndex].size();
									for (size_t provenanceIndex = before;
									     provenanceIndex < after;
									     ++provenanceIndex)
									{
										flushReplayTriplexProvenanceByTask[taskIndex]
											.push_back(
												replayAttemptProvenance(
													attempt,
													localAlignment));
									}
								};

								auto flushReplayScoreInfo = [&]()
								{
									if (currentReplayScoreInfo < 0 ||
									    currentReplayTask >= replayTaskCount)
									{
										replayHaveBest = false;
										replayHaveLast = false;
										replayEmitted = false;
										replayBestAlignment.Clear();
										replayLastAlignment.Clear();
										return;
									}
									StripedSmithWaterman::Alignment emitAlignment;
									FasimGasal2SelectedAlignment emitSelected;
									bool shouldEmit = false;
									if (!replayEmitted && replayHaveBest)
									{
										emitAlignment = replayBestAlignment;
										emitSelected = replayBestSelected;
										shouldEmit = true;
									}
									else if (!replayEmitted &&
									         replayHaveLast &&
									         replayLastAlignment.sw_score != 0)
									{
										emitAlignment = replayLastAlignment;
										emitSelected = replayLastSelected;
										shouldEmit = true;
									}
									if (shouldEmit)
									{
										emitAlignment.ref_begin += emitSelected.start;
										emitAlignment.ref_end += emitSelected.start;
										FasimGasal2Attempt provenanceAttempt;
										provenanceAttempt.scoreinfo_index =
											emitSelected.scoreinfo_index;
										provenanceAttempt.start = emitSelected.start;
										provenanceAttempt.cutlength =
											emitSelected.cutlength;
										appendReplayTriplexes(currentReplayTask,
										                     emitAlignment,
										                     provenanceAttempt,
										                     emitAlignment);
									}
									replayHaveBest = false;
									replayHaveLast = false;
									replayEmitted = false;
									replayBestSelected = FasimGasal2SelectedAlignment();
									replayLastSelected = FasimGasal2SelectedAlignment();
									replayBestAlignment.Clear();
									replayLastAlignment.Clear();
								};

								for (size_t selectedIndex = 0;
								     selectedIndex < flushReplayExpandedAttemptOrdinals.size();
								     ++selectedIndex)
								{
									const size_t attemptOrdinal =
										flushReplayExpandedAttemptOrdinals[selectedIndex];
									if (attemptOrdinal >= flushProbeAttempts.size())
									{
										continue;
									}
									const FasimGasal2Attempt &attempt =
										flushProbeAttempts[attemptOrdinal];
									if (attempt.scoreinfo_index < 0 ||
									    static_cast<size_t>(attempt.scoreinfo_index) >=
									    flushProbeScoreInfoTaskIndexes.size())
									{
										continue;
									}
									const size_t taskIndex =
										flushProbeScoreInfoTaskIndexes[
											static_cast<size_t>(attempt.scoreinfo_index)];
									if (taskIndex >= replayTaskCount)
									{
										continue;
									}
									if (attempt.scoreinfo_index != currentReplayScoreInfo)
									{
										flushReplayScoreInfo();
										currentReplayScoreInfo = attempt.scoreinfo_index;
										currentReplayTask = taskIndex;
									}
									if (replayEmitted)
									{
										continue;
									}
									StreamTask &replayTask = tasks[taskIndex];
									if (attempt.start < 0 ||
									    attempt.cutlength <= 0 ||
									    attempt.start + attempt.cutlength >
									    static_cast<int>(replayTask.seq2.size()))
									{
										++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_replay_probe_fallbacks;
										continue;
									}
									std::string replaySmallSeq =
										replayTask.seq2.substr(
											static_cast<size_t>(attempt.start),
											static_cast<size_t>(attempt.cutlength));
									StripedSmithWaterman::Alignment replayAlignment;
									aligner.Align(lncSeq.c_str(),
									              replaySmallSeq.c_str(),
									              replaySmallSeq.size(),
									              filter,
									              &replayAlignment,
									              15);
									++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_replay_probe_align_attempts;
									FasimGasal2SelectedAlignment selected;
									selected.scoreinfo_index = attempt.scoreinfo_index;
									selected.cutlength = attempt.cutlength;
									selected.start = attempt.start;
									selected.selected = true;
									replayLastSelected = selected;
									replayLastAlignment = replayAlignment;
									replayHaveLast = true;
									if (replayAlignment.sw_score >=
									    flushProbeScoreInfoScores[
										    static_cast<size_t>(attempt.scoreinfo_index)])
									{
										StripedSmithWaterman::Alignment emitAlignment =
											replayAlignment;
										emitAlignment.ref_begin += attempt.start;
										emitAlignment.ref_end += attempt.start;
										appendReplayTriplexes(taskIndex,
										                     emitAlignment,
										                     attempt,
										                     replayAlignment);
										replayEmitted = true;
										continue;
									}
									if (replayAlignment.sw_score >
									    replayBestAlignment.sw_score &&
									    replayAlignment.ref_end ==
									    attempt.cutlength - 1)
									{
										replayBestSelected = selected;
										replayBestAlignment = replayAlignment;
										replayHaveBest = true;
									}
								}
								flushReplayScoreInfo();
								for (size_t taskIndex = 0;
								     taskIndex < replayTaskCount;
								     ++taskIndex)
								{
									flushReplayTaskCovered[taskIndex] =
										static_cast<unsigned char>(1);
									std::vector<triplex> &replayTriplexes =
										flushReplayTriplexesByTask[taskIndex];
									std::vector<std::string> &replayProvenance =
										flushReplayTriplexProvenanceByTask[taskIndex];
									std::vector<std::pair<triplex, std::string> >
										replayAnnotatedTriplexes;
									replayAnnotatedTriplexes.reserve(replayTriplexes.size());
									for (size_t replayIndex = 0;
									     replayIndex < replayTriplexes.size();
									     ++replayIndex)
									{
										const std::string provenance =
											replayIndex < replayProvenance.size() ?
											replayProvenance[replayIndex] :
											std::string("unknown");
										replayAnnotatedTriplexes.push_back(
											std::make_pair(replayTriplexes[replayIndex],
											               provenance));
									}
									std::sort(
										replayAnnotatedTriplexes.begin(),
										replayAnnotatedTriplexes.end(),
										[](const std::pair<triplex, std::string> &lhs,
										   const std::pair<triplex, std::string> &rhs)
										{
											return compMyTriplexMultiple(lhs.first,
											                             rhs.first);
										});
									replayAnnotatedTriplexes.erase(
										std::unique(
											replayAnnotatedTriplexes.begin(),
											replayAnnotatedTriplexes.end(),
											[](const std::pair<triplex, std::string> &lhs,
											   const std::pair<triplex, std::string> &rhs)
											{
												return sameMyTriplex(lhs.first,
												                     rhs.first);
											}),
										replayAnnotatedTriplexes.end());
									std::sort(
										replayAnnotatedTriplexes.begin(),
										replayAnnotatedTriplexes.end(),
										[](const std::pair<triplex, std::string> &lhs,
										   const std::pair<triplex, std::string> &rhs)
										{
											return compMyTriplexMultiple2(lhs.first,
											                              rhs.first);
										});
									replayAnnotatedTriplexes.erase(
										std::unique(
											replayAnnotatedTriplexes.begin(),
											replayAnnotatedTriplexes.end(),
											[](const std::pair<triplex, std::string> &lhs,
											   const std::pair<triplex, std::string> &rhs)
											{
												return sameMyTriplex(lhs.first,
												                     rhs.first);
											}),
										replayAnnotatedTriplexes.end());
									std::sort(
										replayAnnotatedTriplexes.begin(),
										replayAnnotatedTriplexes.end(),
										[](const std::pair<triplex, std::string> &lhs,
										   const std::pair<triplex, std::string> &rhs)
										{
											return compMyTriplexSingle(lhs.first,
											                           rhs.first);
										});
									std::vector<triplex> replayFilteredTriplexes;
									std::vector<std::string> replayFilteredProvenance;
									replayFilteredTriplexes.reserve(
										replayAnnotatedTriplexes.size());
									replayFilteredProvenance.reserve(
										replayAnnotatedTriplexes.size());
									const size_t replayTopLimit =
										std::min(replayAnnotatedTriplexes.size(),
										         static_cast<size_t>(N));
									for (size_t replayIndex = 0;
									     replayIndex < replayTopLimit;
									     ++replayIndex)
									{
										const triplex &atr =
											replayAnnotatedTriplexes[replayIndex].first;
										if (atr.identity >= paraList.minIdentity &&
										    atr.tri_score >= paraList.minStability &&
										    atr.nt >= paraList.ntMin)
										{
											replayFilteredTriplexes.push_back(atr);
											replayFilteredProvenance.push_back(
												replayAnnotatedTriplexes[replayIndex].second);
										}
									}
									replayTriplexes.swap(replayFilteredTriplexes);
									replayProvenance.swap(replayFilteredProvenance);
									++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_replay_probe_active;
								}
								longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_replay_probe_seconds +=
									fasim_seconds_since(replayStart);
							}
							if (!flushFullReplayTriplexesByTask.empty())
							{
								const std::chrono::steady_clock::time_point fullReplayStart =
									std::chrono::steady_clock::now();
								longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_full_replay_probe_requested += 1;
								size_t replayTaskCount =
									fasim_long_query_streaming_scoreinfo_flush_segmented_replay_probe_max_tasks_runtime();
								if (replayTaskCount == 0 ||
								    replayTaskCount > tasks.size())
								{
									replayTaskCount = tasks.size();
								}
								longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_full_replay_probe_tasks +=
									static_cast<uint64_t>(replayTaskCount);
								const int8_t nt_table[128] = {
									4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
									4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4
								};
								for (size_t taskIndex = 0;
								     taskIndex < replayTaskCount;
								     ++taskIndex)
								{
									StreamTask &replayTask = tasks[taskIndex];
									std::vector<triplex> &replayTriplexes =
										flushFullReplayTriplexesByTask[taskIndex];
									int currentFullReplayScoreInfo = -1;
									StripedSmithWaterman::Alignment fullReplayBestAlignment;
									StripedSmithWaterman::Alignment fullReplayLastAlignment;
									FasimGasal2Attempt fullReplayBestAttempt;
									FasimGasal2Attempt fullReplayLastAttempt;
									bool fullReplayHaveBest = false;
									bool fullReplayHaveLast = false;
									bool fullReplayEmitted = false;
									auto emitFullReplayAlignment =
										[&](const FasimGasal2Attempt &emitAttempt,
										    const StripedSmithWaterman::Alignment &alignment)
									{
										if (alignment.sw_score == 0)
										{
											return;
										}
										StripedSmithWaterman::Alignment emitAlignment =
											alignment;
										emitAlignment.ref_begin += emitAttempt.start;
										emitAlignment.ref_end += emitAttempt.start;
										convertMyTriplex(emitAlignment,
										                 replayTriplexes,
										                 lncSeq,
										                 replayTask.seq2,
										                 *replayTask.srcSeq,
										                 nt_table,
										                 replayTask.dnaStartPos,
										                 replayTask.rule,
										                 replayTask.strand,
										                 replayTask.Para,
										                 paraList.penaltyT,
										                 paraList.penaltyC,
										                 paraList.ntMin,
										                 paraList.ntMax,
										                 writeFull);
									};
									auto flushFullReplayScoreInfo = [&]()
									{
										if (currentFullReplayScoreInfo >= 0 &&
										    !fullReplayEmitted)
										{
											if (fullReplayHaveBest)
											{
												emitFullReplayAlignment(
													fullReplayBestAttempt,
													fullReplayBestAlignment);
											}
											else if (fullReplayHaveLast &&
											         fullReplayLastAlignment.sw_score != 0)
											{
												emitFullReplayAlignment(
													fullReplayLastAttempt,
													fullReplayLastAlignment);
											}
										}
										fullReplayHaveBest = false;
										fullReplayHaveLast = false;
										fullReplayEmitted = false;
										fullReplayBestAlignment.Clear();
										fullReplayLastAlignment.Clear();
										fullReplayBestAttempt = FasimGasal2Attempt();
										fullReplayLastAttempt = FasimGasal2Attempt();
									};
									for (size_t attemptIndex = 0;
									     attemptIndex < flushProbeAttempts.size();
									     ++attemptIndex)
									{
										if (attemptIndex >= flushProbeAttemptTaskIndexes.size() ||
										    flushProbeAttemptTaskIndexes[attemptIndex] != taskIndex)
										{
											continue;
										}
										const FasimGasal2Attempt &attempt =
											flushProbeAttempts[attemptIndex];
										if (attempt.scoreinfo_index !=
										    currentFullReplayScoreInfo)
										{
											flushFullReplayScoreInfo();
											currentFullReplayScoreInfo =
												attempt.scoreinfo_index;
										}
										if (fullReplayEmitted)
										{
											continue;
										}
										if (attempt.start < 0 ||
										    attempt.cutlength <= 0 ||
										    attempt.start + attempt.cutlength >
										    static_cast<int>(replayTask.seq2.size()))
										{
											++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_full_replay_probe_fallbacks;
											continue;
										}
										std::string replaySmallSeq =
											replayTask.seq2.substr(
												static_cast<size_t>(attempt.start),
												static_cast<size_t>(attempt.cutlength));
										StripedSmithWaterman::Alignment replayAlignment;
										aligner.Align(lncSeq.c_str(),
										              replaySmallSeq.c_str(),
										              replaySmallSeq.size(),
										              filter,
										              &replayAlignment,
										              15);
										++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_full_replay_probe_align_attempts;
										fullReplayLastAttempt = attempt;
										fullReplayLastAlignment = replayAlignment;
										fullReplayHaveLast = true;
										if (replayAlignment.sw_score >=
										    attempt.prealign_score)
										{
											emitFullReplayAlignment(attempt,
											                        replayAlignment);
											fullReplayEmitted = true;
											continue;
										}
										if (replayAlignment.sw_score >
										        fullReplayBestAlignment.sw_score &&
										    replayAlignment.ref_end ==
										        attempt.cutlength - 1)
										{
											fullReplayBestAttempt = attempt;
											fullReplayBestAlignment = replayAlignment;
											fullReplayHaveBest = true;
										}
									}
									flushFullReplayScoreInfo();
									std::sort(replayTriplexes.begin(),
									          replayTriplexes.end(),
									          compMyTriplexMultiple);
									replayTriplexes.erase(
										std::unique(replayTriplexes.begin(),
										            replayTriplexes.end(),
										            sameMyTriplex),
										replayTriplexes.end());
									std::sort(replayTriplexes.begin(),
									          replayTriplexes.end(),
									          compMyTriplexMultiple2);
									replayTriplexes.erase(
										std::unique(replayTriplexes.begin(),
										            replayTriplexes.end(),
										            sameMyTriplex),
										replayTriplexes.end());
									std::sort(replayTriplexes.begin(),
									          replayTriplexes.end(),
									          compMyTriplexSingle);
									std::vector<triplex> replayFilteredTriplexes;
									replayFilteredTriplexes.reserve(replayTriplexes.size());
									const size_t replayTopLimit =
										std::min(replayTriplexes.size(),
										         static_cast<size_t>(N));
									for (size_t replayIndex = 0;
									     replayIndex < replayTopLimit;
									     ++replayIndex)
									{
										const triplex &atr = replayTriplexes[replayIndex];
										if (atr.identity >= paraList.minIdentity &&
										    atr.tri_score >= paraList.minStability &&
										    atr.nt >= paraList.ntMin)
										{
											replayFilteredTriplexes.push_back(atr);
										}
									}
									replayTriplexes.swap(replayFilteredTriplexes);
									flushFullReplayTaskCovered[taskIndex] =
										static_cast<unsigned char>(1);
									++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_full_replay_probe_active;
								}
									longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_full_replay_probe_seconds +=
										fasim_seconds_since(fullReplayStart);
									if (broadReplacementConsumerEnabled)
									{
										for (size_t taskIndex = 0;
										     taskIndex < replayTaskCount;
										     ++taskIndex)
										{
											if (taskIndex < flushFullReplayTaskCovered.size() &&
											    flushFullReplayTaskCovered[taskIndex] != 0)
											{
												broadReplacementTriplexesByTask[
													tasks[taskIndex].taskIndex] =
													flushFullReplayTriplexesByTask[taskIndex];
											}
										}
										broadScoreInfoConsumerShadowStats
											.broad_path_consumer_seconds +=
											fasim_seconds_since(fullReplayStart);
										broadScoreInfoConsumerShadowStats.broad_path_active = 1;
										broadScoreInfoConsumerShadowStats.broad_path_decision =
											"replacement_consumer_shadow_active";
									}
								}
							if (!flushOracleReplayTriplexesByTask.empty())
							{
								const std::chrono::steady_clock::time_point oracleReplayStart =
									std::chrono::steady_clock::now();
								longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_oracle_replay_probe_requested += 1;
								size_t replayTaskCount =
									fasim_long_query_streaming_scoreinfo_flush_segmented_replay_probe_max_tasks_runtime();
								if (replayTaskCount == 0 ||
								    replayTaskCount > tasks.size())
								{
									replayTaskCount = tasks.size();
								}
								longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_oracle_replay_probe_tasks +=
									static_cast<uint64_t>(replayTaskCount);
								for (size_t taskIndex = 0;
								     taskIndex < replayTaskCount;
								     ++taskIndex)
								{
									StreamTask &replayTask = tasks[taskIndex];
									StripedSmithWaterman::Alignment oracleAlignment;
									fastSIM_extend_from_scoreinfo(
										aligner,
										filter,
										oracleAlignment,
										15,
										lncSeq,
										replayTask.seq2,
										*replayTask.srcSeq,
										replayTask.dnaStartPos,
										streamingRealpathScoreInfos[taskIndex],
										flushOracleReplayTriplexesByTask[taskIndex],
										replayTask.strand,
										replayTask.Para,
										replayTask.rule,
										paraList.ntMin,
										paraList.ntMax,
										paraList.penaltyT,
										paraList.penaltyC,
										paraList,
										writeFull,
										NULL);
									flushOracleReplayTaskCovered[taskIndex] =
										static_cast<unsigned char>(1);
									++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_oracle_replay_probe_active;
								}
								longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_oracle_replay_probe_seconds +=
									fasim_seconds_since(oracleReplayStart);
							}
						}
						longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_attempt_probe_seconds +=
							fasim_seconds_since(flushProbeStart);
					}
					for (size_t t = 0; t < tasks.size(); ++t)
					{
						StreamTask &task = tasks[t];
						const int minScore = task_min_score(task);
							taskTriplexes.clear();
							if (paraList.doFastSim)
							{
									if (scorePrepassStateMachineTrustRequested &&
									    streamingRealpathCanUse &&
									    t < scorePrepassStateMachineTriplexesByTask.size() &&
									    t < scorePrepassStateMachineTaskCovered.size() &&
									    scorePrepassStateMachineTaskCovered[t] != 0 &&
									    longQueryStreamingScoreInfoShadowStats
										    .score_prepass_state_machine_shadow_fallbacks == 0 &&
									    longQueryStreamingScoreInfoShadowStats
										    .score_prepass_state_machine_shadow_triplex_mismatches == 0)
									{
										taskTriplexes =
											scorePrepassStateMachineTriplexesByTask[t];
										write_task_triplexes(task);
										continue;
									}
									if (streamingRealpathCanUse)
									{
									const std::chrono::steady_clock::time_point realpathExtendStart =
										std::chrono::steady_clock::now();
									FasimFastsimExtendScoreInfoTiming extendTiming;
									fastSIM_extend_from_scoreinfo(aligner,
									                              filter,
									                              alignment,
								                              15,
								                              lncSeq,
								                              task.seq2,
								                              *task.srcSeq,
								                              task.dnaStartPos,
								                              streamingRealpathScoreInfos[t],
								                              taskTriplexes,
								                              task.strand,
								                              task.Para,
								                              task.rule,
								                              paraList.ntMin,
								                              paraList.ntMax,
									                              paraList.penaltyT,
									                              paraList.penaltyC,
									                              paraList,
									                              writeFull,
									                              &extendTiming);
									longQueryStreamingScoreInfoShadowStats.realpath_extend_seconds +=
										fasim_seconds_since(realpathExtendStart);
									longQueryStreamingScoreInfoShadowStats.realpath_extend_scoreinfo_groups +=
										extendTiming.scoreinfo_groups;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_align_attempts +=
										extendTiming.align_attempts;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_attempt_probe_requested +=
										extendTiming.attempt_probe_requested;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_attempt_probe_active +=
										extendTiming.attempt_probe_active;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_attempt_probe_calls +=
										extendTiming.attempt_probe_calls;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_attempt_probe_attempts +=
										extendTiming.attempt_probe_attempts;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_attempt_probe_selected_attempts +=
										extendTiming.attempt_probe_selected_attempts;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_attempt_probe_fallbacks +=
										extendTiming.attempt_probe_fallbacks;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_segmented_attempt_probe_requested +=
										extendTiming.segmented_attempt_probe_requested;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_segmented_attempt_probe_active +=
										extendTiming.segmented_attempt_probe_active;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_segmented_attempt_probe_segments +=
										extendTiming.segmented_attempt_probe_segments;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_segmented_attempt_probe_calls +=
										extendTiming.segmented_attempt_probe_calls;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_segmented_attempt_probe_attempts +=
										extendTiming.segmented_attempt_probe_attempts;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_segmented_attempt_probe_selected_attempts +=
										extendTiming.segmented_attempt_probe_selected_attempts;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_segmented_attempt_probe_fallbacks +=
										extendTiming.segmented_attempt_probe_fallbacks;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_substr_seconds +=
										extendTiming.substr_seconds;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_align_seconds +=
										extendTiming.align_seconds;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_convert_seconds +=
										extendTiming.convert_seconds;
									longQueryStreamingScoreInfoShadowStats.realpath_extend_sort_seconds +=
										extendTiming.sort_seconds;
										longQueryStreamingScoreInfoShadowStats.realpath_extend_filter_seconds +=
											extendTiming.filter_seconds;
										longQueryStreamingScoreInfoShadowStats.realpath_extend_attempt_probe_seconds +=
											extendTiming.attempt_probe_seconds;
											longQueryStreamingScoreInfoShadowStats.realpath_extend_segmented_attempt_probe_seconds +=
												extendTiming.segmented_attempt_probe_seconds;
											if (attemptConsumerShadowEnabled)
											{
												std::vector<triplex> attemptConsumerTriplexes;
												std::string attemptConsumerError;
												const bool attemptConsumerOk =
													fasim_shadow_attempt_consumer_from_scoreinfo(
														aligner,
														filter,
														15,
														lncSeq,
														task.seq2,
														*task.srcSeq,
														task.dnaStartPos,
														streamingRealpathScoreInfos[t],
														attemptConsumerTriplexes,
														task.strand,
														task.Para,
														task.rule,
														paraList.ntMin,
														paraList.ntMax,
														paraList.penaltyT,
														paraList.penaltyC,
														paraList,
														writeFull,
														&attemptConsumerError);
												if (attemptConsumerOk)
												{
													attemptConsumerTriplexesByTask[
														task.taskIndex] =
														attemptConsumerTriplexes;
												}
											else if (attemptConsumerShadowFirstMismatch == "none")
											{
												std::ostringstream first;
												first << "task:" << task.taskIndex
												      << ":shadow_error:"
													      << (attemptConsumerError.empty() ?
														      "unknown" :
														      attemptConsumerError);
												attemptConsumerShadowFirstMismatch =
													first.str();
											}
										}
											if (emissionOnlyConsumerShadowEnabled)
											{
												std::vector<triplex> emissionOnlyTriplexes;
												std::string emissionOnlyError;
												const bool emissionOnlyOk =
													fasim_shadow_emission_only_consumer_from_scoreinfo(
														aligner,
														filter,
														15,
														lncSeq,
														task.seq2,
														*task.srcSeq,
															task.dnaStartPos,
															streamingRealpathScoreInfos[t],
															extendTiming.align_attempts,
															task.taskIndex,
															emissionOnlyTriplexes,
														task.strand,
														task.Para,
														task.rule,
														paraList.ntMin,
														paraList.ntMax,
														paraList.penaltyT,
														paraList.penaltyC,
														paraList,
														writeFull,
														&emissionOnlyError);
												if (emissionOnlyOk)
												{
													emissionOnlyTriplexesByTask[
														task.taskIndex] =
														emissionOnlyTriplexes;
												}
												else if (emissionOnlyShadowFirstMismatch == "none")
												{
													std::ostringstream first;
													first << "task:" << task.taskIndex
													      << ":shadow_error:"
													      << (emissionOnlyError.empty() ?
														      "unknown" :
														      emissionOnlyError);
													emissionOnlyShadowFirstMismatch =
														first.str();
												}
											}
											if (!flushReplayTriplexesByTask.empty() &&
											    t < flushReplayTriplexesByTask.size() &&
											    t < flushReplayTaskCovered.size() &&
										    flushReplayTaskCovered[t] != 0 &&
										    !triplex_probe_equal(flushReplayTriplexesByTask[t],
										                         taskTriplexes))
										{
											record_triplex_probe_first_mismatch(
												t,
												flushReplayTriplexesByTask[t],
												taskTriplexes,
												t < flushReplayTriplexProvenanceByTask.size() ?
													&flushReplayTriplexProvenanceByTask[t] :
													NULL);
											++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_replay_probe_triplex_mismatches;
										}
										if (!flushSelectedOnlyReplayTriplexesByTask.empty() &&
										    t < flushSelectedOnlyReplayTriplexesByTask.size() &&
										    t < flushSelectedOnlyReplayTaskCovered.size() &&
										    flushSelectedOnlyReplayTaskCovered[t] != 0 &&
										    !triplex_probe_equal(flushSelectedOnlyReplayTriplexesByTask[t],
										                         taskTriplexes))
										{
											record_selected_only_triplex_mismatch(
												t,
												flushSelectedOnlyReplayTriplexesByTask[t],
												taskTriplexes,
												t < flushSelectedOnlyReplayTriplexProvenanceByTask.size() ?
													&flushSelectedOnlyReplayTriplexProvenanceByTask[t] :
													NULL);
											++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_selected_only_replay_probe_triplex_mismatches;
											}
											if (!flushGroupedSelectedReplayTriplexesByTask.empty() &&
											    t < flushGroupedSelectedReplayTriplexesByTask.size() &&
											    t < flushGroupedSelectedReplayTaskCovered.size() &&
											    flushGroupedSelectedReplayTaskCovered[t] != 0 &&
											    !triplex_probe_equal(flushGroupedSelectedReplayTriplexesByTask[t],
											                         taskTriplexes))
											{
												record_grouped_selected_triplex_mismatch(
													t,
													flushGroupedSelectedReplayTriplexesByTask[t],
													taskTriplexes,
													t < flushGroupedSelectedReplayTriplexProvenanceByTask.size() ?
														&flushGroupedSelectedReplayTriplexProvenanceByTask[t] :
														NULL,
													t < flushReplayTriplexProvenanceByTask.size() ?
														&flushReplayTriplexProvenanceByTask[t] :
														NULL);
												++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_segmented_grouped_selected_replay_probe_triplex_mismatches;
											}
											if (!flushFullReplayTriplexesByTask.empty() &&
										    t < flushFullReplayTriplexesByTask.size() &&
										    t < flushFullReplayTaskCovered.size() &&
										    flushFullReplayTaskCovered[t] != 0 &&
										    !triplex_probe_equal(flushFullReplayTriplexesByTask[t],
										                         taskTriplexes))
										{
											++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_full_replay_probe_triplex_mismatches;
										}
										if (!flushOracleReplayTriplexesByTask.empty() &&
										    t < flushOracleReplayTriplexesByTask.size() &&
										    t < flushOracleReplayTaskCovered.size() &&
										    flushOracleReplayTaskCovered[t] != 0 &&
										    !triplex_probe_equal(flushOracleReplayTriplexesByTask[t],
										                         taskTriplexes))
										{
											++longQueryStreamingScoreInfoShadowStats.realpath_extend_flush_oracle_replay_probe_triplex_mismatches;
										}
										if (!scorePrepassStateMachineTriplexesByTask.empty() &&
										    t < scorePrepassStateMachineTriplexesByTask.size() &&
										    t < scorePrepassStateMachineTaskCovered.size() &&
										    scorePrepassStateMachineTaskCovered[t] != 0 &&
										    !triplex_probe_equal(
											    scorePrepassStateMachineTriplexesByTask[t],
											    taskTriplexes))
										{
											++longQueryStreamingScoreInfoShadowStats
												.score_prepass_state_machine_shadow_triplex_mismatches;
											if (longQueryStreamingScoreInfoShadowStats
											        .score_prepass_state_machine_shadow_first_mismatch_task < 0)
											{
												longQueryStreamingScoreInfoShadowStats
													.score_prepass_state_machine_shadow_first_mismatch_task =
													static_cast<int64_t>(t);
												longQueryStreamingScoreInfoShadowStats
													.score_prepass_state_machine_shadow_first_mismatch_source =
													"score_prepass_state_machine";
												if (scorePrepassStateMachineTriplexesByTask[t].empty() &&
												    !taskTriplexes.empty())
												{
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_first_mismatch_kind =
														"shadow_empty";
												}
												else if (!scorePrepassStateMachineTriplexesByTask[t].empty() &&
												         taskTriplexes.empty())
												{
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_first_mismatch_kind =
														"legacy_empty";
												}
												else if (scorePrepassStateMachineTriplexesByTask[t].size() <
												         taskTriplexes.size())
												{
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_first_mismatch_kind =
														"shadow_less";
												}
												else if (scorePrepassStateMachineTriplexesByTask[t].size() >
												         taskTriplexes.size())
												{
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_first_mismatch_kind =
														"shadow_more";
												}
												else
												{
													longQueryStreamingScoreInfoShadowStats
														.score_prepass_state_machine_shadow_first_mismatch_kind =
														"same_count_diff";
												}
											}
										}
										if (longQueryStreamingScoreInfoShadowStats.realpath_extend_attempt_probe_error == "none" &&
										    extendTiming.attempt_probe_error != "none")
									{
										longQueryStreamingScoreInfoShadowStats.realpath_extend_attempt_probe_error =
											extendTiming.attempt_probe_error;
									}
									++longQueryStreamingScoreInfoShadowStats.realpath_extend_calls;
									++longQueryStreamingScoreInfoShadowStats.realpath_used;
								}
							else
							{
								std::string srcSeq = *task.srcSeq;
								fastSIM(lncSeq,
								        task.seq2,
								        srcSeq,
								        task.dnaStartPos,
								        minScore,
								        5,
								        -4,
								        -12,
								        -4,
								        taskTriplexes,
								        task.strand,
								        task.Para,
								        task.rule,
								        paraList.ntMin,
								        paraList.ntMax,
								        paraList.penaltyT,
								        paraList.penaltyC,
								        paraList,
								        writeFull);
							}
						}
						else
						{
							std::string srcSeq = *task.srcSeq;
							SIM(lncSeq,
							    task.seq2,
							    srcSeq,
							    task.dnaStartPos,
							    minScore,
							    5,
							    -4,
							    -12,
							    -4,
							    taskTriplexes,
							    task.strand,
							    task.Para,
							    task.rule,
							    paraList.ntMin,
							    paraList.ntMax,
							    paraList.penaltyT,
							    paraList.penaltyC);
						}
						write_task_triplexes(task);
					}
				}

			finalize_attempt_consumer_shadow();
			finalize_emission_only_consumer_shadow();
			tasks.clear();
			encodedTargets.clear();
			legacyEncodedTargets.clear();
			currentTargetLength = -1;
		};

			auto enqueue_precomputed_task = [&](std::string seq2,
			                                    const std::shared_ptr<const std::string> &srcSeq,
			                                    long dnaStartPos,
			                                    int reverseMode,
			                                    int paraMode,
			                                    int rule,
			                                    long recordStartGenome,
			                                    const std::string &chrTag)
				{
				if (useCudaBatch || streamingScoreInfoShadowCudaReady)
				{
					if (currentTargetLength < 0)
				{
					currentTargetLength = static_cast<int>(seq2.size());
					encodedTargets.reserve(static_cast<size_t>(maxTasksTotal) * static_cast<size_t>(currentTargetLength));
					legacyEncodedTargets.reserve(static_cast<size_t>(maxTasksTotal) * static_cast<size_t>(currentTargetLength));
				}
				if (static_cast<int>(seq2.size()) != currentTargetLength || static_cast<int>(tasks.size()) >= maxTasksTotal)
				{
					flush_batch();
					currentTargetLength = static_cast<int>(seq2.size());
					encodedTargets.reserve(static_cast<size_t>(maxTasksTotal) * static_cast<size_t>(currentTargetLength));
					legacyEncodedTargets.reserve(static_cast<size_t>(maxTasksTotal) * static_cast<size_t>(currentTargetLength));
				}
			}
			else if (static_cast<int>(tasks.size()) >= maxTasksTotal)
			{
				flush_batch();
				}

						StreamTask task;
						{
							FasimScopedSeconds scoped(phaseTimingEnabled,
							                          &phaseTiming.enqueue_seconds);
							task.taskIndex = nextStreamTaskIndex++;
							task.seq2.swap(seq2);
							task.srcSeq = srcSeq;
							task.chr = chrTag;
					task.recordStartGenome = recordStartGenome;
				task.dnaStartPos = dnaStartPos;
				task.strand = reverseMode;
				task.Para = paraMode;
				task.rule = rule;

				tasks.push_back(std::move(task));
				if (phaseTimingEnabled)
				{
					++phaseTiming.tasks;
				}
				}

				if (useCudaBatch || streamingScoreInfoShadowCudaReady)
					{
						FasimScopedSeconds scoped(phaseTimingEnabled,
						                          &phaseTiming.encode_seconds);
						const std::string &storedSeq2 = tasks.back().seq2;
						const size_t oldSize = encodedTargets.size();
						const size_t appendLength = static_cast<size_t>(currentTargetLength);
							const uint8_t *prealignTable =
								streamingScoreInfoLegacyByteRequested ?
									fasim_ssw_prealign_encode_table() :
									fasim_prealign_encode_table();
							encodedTargets.resize(oldSize + appendLength);
							uint8_t *encodedOut = encodedTargets.data() + oldSize;
							uint8_t *legacyOut = NULL;
							const uint8_t *legacyTable = NULL;
						if (legacyScoreGpuShadowEnabled)
						{
							legacyEncodedTargets.resize(oldSize + appendLength);
								legacyOut = legacyEncodedTargets.data() + oldSize;
								legacyTable = fasim_legacy_calc_score_encode_table();
							}
							if (legacyOut != NULL)
							{
								FasimScopedSeconds dualScoped(phaseTimingEnabled,
								                              &phaseTiming.encode_dual_seconds);
								for (int k = 0; k < currentTargetLength; ++k)
								{
									const unsigned char base =
										static_cast<unsigned char>(storedSeq2[static_cast<size_t>(k)]);
									encodedOut[k] = prealignTable[base];
									legacyOut[k] = legacyTable[base];
								}
							}
							else
							{
								FasimScopedSeconds encodeScoped(phaseTimingEnabled,
								                                &phaseTiming.encode_prealign_seconds);
								for (int k = 0; k < currentTargetLength; ++k)
								{
									const unsigned char base =
										static_cast<unsigned char>(storedSeq2[static_cast<size_t>(k)]);
									encodedOut[k] = prealignTable[base];
								}
							}
						}
			};

			auto make_transferred_seq = [&](const std::string &seq1,
			                                int reverseMode,
			                                int paraMode,
			                                int rule,
			                                bool reverseSeq2) -> std::string
			{
				std::string seq2;
					{
						FasimScopedSeconds scoped(phaseTimingEnabled,
						                          &phaseTiming.transfer_string_seconds);
						FasimScopedSeconds tableScoped(phaseTimingEnabled,
						                               &phaseTiming.transfer_table_seconds);
						seq2 = transferStringTableOptIn(seq1, reverseMode, paraMode, rule);
						if (phaseTimingEnabled)
						{
							++phaseTiming.transfer_calls;
							phaseTiming.transfer_bytes +=
								static_cast<uint64_t>(seq1.size());
						}
					}
					if (reverseSeq2)
					{
						FasimScopedSeconds reverseScoped(phaseTimingEnabled,
						                                 &phaseTiming.transfer_reverse_seconds);
						reverseSeq(seq2);
						if (phaseTimingEnabled)
						{
							++phaseTiming.transfer_reverse_calls;
						}
					}
				return seq2;
			};

			string pendingHeader;
			FasimFastaRecord record;
			while (true)
			{
				{
					FasimScopedSeconds scoped(phaseTimingEnabled,
					                          &phaseTiming.fasta_read_seconds);
					if (!fasim_read_next_fasta_record(dnaIn, pendingHeader, record))
					{
						break;
					}
				}
				if (record.sequence.empty())
				{
					continue;
				}
				if (phaseTimingEnabled)
				{
					++phaseTiming.records;
				}
				string recordSpecies;
				string recordChr;
			long recordStartGenome = 1;
			fasim_parse_dna_header_fields(record.header, recordSpecies, recordChr, recordStartGenome);
			ensure_output_opened(recordSpecies);

				vector<string> dnaSequencesVec;
				vector<int> dnaSequencesStartPos;
				int cut_num = 0;
				{
					FasimScopedSeconds scoped(phaseTimingEnabled,
					                          &phaseTiming.cut_sequence_seconds);
					cutSequence(record.sequence, dnaSequencesVec, dnaSequencesStartPos, paraList.cutLength, paraList.overlapLength, cut_num);
				}

				for (int i = 0; i < dnaSequencesVec.size(); i++)
				{
					if (phaseTimingEnabled)
					{
						++phaseTiming.windows;
					}
					long dnaStartPos = dnaSequencesStartPos[i];
				if (verbose)
				{
					cout << "dnaPos = " << dnaStartPos << endl;
				}
					string &seq1 = dnaSequencesVec[i];
						if (same_seq(seq1))
						{
							continue;
						}
						std::vector< std::shared_ptr<const std::string> > srcTransformCache(4);
						auto get_src_transform = [&](FasimSrcTransform srcTransform) -> std::shared_ptr<const std::string>
						{
							const size_t index = static_cast<size_t>(srcTransform);
							if (index >= srcTransformCache.size())
							{
								std::shared_ptr<std::string> fallback(new std::string(seq1));
								return fallback;
							}
							if (!srcTransformCache[index])
							{
								std::shared_ptr<std::string> transformed(new std::string());
								{
									FasimScopedSeconds scoped(phaseTimingEnabled,
									                          &phaseTiming.src_transform_seconds);
									fasim_apply_src_transform(seq1, srcTransform, *transformed);
								}
								if (phaseTimingEnabled)
								{
									++phaseTiming.src_transform_calls;
									phaseTiming.src_transform_bytes +=
										static_cast<uint64_t>(seq1.size());
									switch (srcTransform)
									{
									case FASIM_SRC_ORIG:
										++phaseTiming.src_transform_orig;
										break;
									case FASIM_SRC_COMP:
										++phaseTiming.src_transform_comp;
										break;
									case FASIM_SRC_REV:
										++phaseTiming.src_transform_rev;
										break;
									case FASIM_SRC_REVCOMP:
										++phaseTiming.src_transform_revcomp;
										break;
									default:
										break;
									}
								}
								srcTransformCache[index] = transformed;
							}
							return srcTransformCache[index];
						};

						if (paraList.strand >= 0)
						{
							if (paraList.rule == 0)
							{
								for (int j = 0; j < 6; j++)
								{
									enqueue_precomputed_task(
										make_transferred_seq(seq1, 0, 1, j + 1, false),
										get_src_transform(FASIM_SRC_ORIG),
										dnaStartPos,
										0,
										1,
									j + 1,
									recordStartGenome,
									recordChr);
									enqueue_precomputed_task(
										make_transferred_seq(seq1, 1, 1, j + 1, true),
										get_src_transform(FASIM_SRC_REVCOMP),
										dnaStartPos,
										1,
										1,
									j + 1,
									recordStartGenome,
									recordChr);
							}
						}
						else if (paraList.rule > 0 && paraList.rule < 7)
							{
								enqueue_precomputed_task(
									make_transferred_seq(seq1, 0, 1, paraList.rule, false),
									get_src_transform(FASIM_SRC_ORIG),
									dnaStartPos,
									0,
									1,
								paraList.rule,
								recordStartGenome,
								recordChr);
								enqueue_precomputed_task(
									make_transferred_seq(seq1, 1, 1, paraList.rule, true),
									get_src_transform(FASIM_SRC_REVCOMP),
									dnaStartPos,
									1,
									1,
								paraList.rule,
								recordStartGenome,
								recordChr);
						}
					}

				if (paraList.strand <= 0)
				{
						if (paraList.rule == 0)
						{
							for (int j = 0; j < 18; j++)
								{
									enqueue_precomputed_task(
										make_transferred_seq(seq1, 1, -1, j + 1, false),
										get_src_transform(FASIM_SRC_COMP),
										dnaStartPos,
										1,
										-1,
									j + 1,
									recordStartGenome,
									recordChr);
									enqueue_precomputed_task(
										make_transferred_seq(seq1, 0, -1, j + 1, true),
										get_src_transform(FASIM_SRC_REV),
										dnaStartPos,
										0,
										-1,
									j + 1,
									recordStartGenome,
									recordChr);
							}
						}
						else
							{
								enqueue_precomputed_task(
									make_transferred_seq(seq1, 1, -1, paraList.rule, false),
									get_src_transform(FASIM_SRC_COMP),
									dnaStartPos,
									1,
									-1,
								paraList.rule,
								recordStartGenome,
								recordChr);
								enqueue_precomputed_task(
									make_transferred_seq(seq1, 0, -1, paraList.rule, true),
									get_src_transform(FASIM_SRC_REV),
									dnaStartPos,
									0,
									-1,
								paraList.rule,
								recordStartGenome,
								recordChr);
						}
				}
			}
		}

			flush_batch();
			if (outOpened)
			{
				FasimScopedSeconds scoped(phaseTimingEnabled,
				                          &phaseTiming.output_close_seconds);
				if (writeFull)
				{
					outFile.close();
			}
				if (writeLite)
				{
					if (collectTopkLite)
					{
						FasimScoreInfoRankBuckets topkLiteRankBuckets;
						FasimScoreInfoRankBuckets *rankBuckets =
							fasim_top5_gasal2_scoreinfo_topk_lite_rank_observe_enabled_runtime() ?
							&topkLiteRankBuckets :
							NULL;
						fasim_write_topk_lite_rows(outLiteFile,
						                           topkLiteRows,
						                           outputTopkLite,
						                           rankBuckets);
						if (rankBuckets != NULL)
						{
							fasim_write_topk_lite_rank_dump(outLiteFilePath + ".topk_rank.tsv",
							                                topkLiteRows,
							                                outputTopkLite);
						}
						if (rankBuckets != NULL && phaseTimingEnabled)
						{
							phaseTiming.scoreinfo_topk_lite_rank_observe_enabled = true;
							phaseTiming.scoreinfo_topk_lite_rank_observe_rows +=
								topkLiteRankBuckets.rows;
							phaseTiming.scoreinfo_topk_lite_rank_observe_unknown_rows +=
								topkLiteRankBuckets.unknown_rows;
							phaseTiming.scoreinfo_topk_lite_rank_observe_max_rank =
								std::max(phaseTiming.scoreinfo_topk_lite_rank_observe_max_rank,
								         topkLiteRankBuckets.max_rank);
							phaseTiming.scoreinfo_topk_lite_rank_observe_rank1 +=
								topkLiteRankBuckets.rank1;
							phaseTiming.scoreinfo_topk_lite_rank_observe_rank2_4 +=
								topkLiteRankBuckets.rank2_4;
							phaseTiming.scoreinfo_topk_lite_rank_observe_rank5_8 +=
								topkLiteRankBuckets.rank5_8;
							phaseTiming.scoreinfo_topk_lite_rank_observe_rank9_16 +=
								topkLiteRankBuckets.rank9_16;
							phaseTiming.scoreinfo_topk_lite_rank_observe_rank17_32 +=
								topkLiteRankBuckets.rank17_32;
							phaseTiming.scoreinfo_topk_lite_rank_observe_rank33_plus +=
								topkLiteRankBuckets.rank33_plus;
						}
					}
						outLiteFile.close();
					}
					if (cigarArchiveProbeOpened)
					{
						cigarArchiveProbeFile.close();
						cigarArchiveProbeOpened = false;
					}
					if (compactArchiveProbeOpened)
					{
						compactArchiveProbeWriter.close();
						compactArchiveProbeOpened = false;
					}
					if (broadCpuTriplexOpened)
				{
					broadCpuTriplexFile.close();
					broadScoreInfoConsumerShadowStats.broad_path_cpu_triplex_digest =
						fasim_hex_u64(broadCpuTriplexDigest);
					broadCpuTriplexOpened = false;
				}
				if (broadPlannerDescriptorOpened)
				{
					broadPlannerDescriptorFile.close();
					broadScoreInfoConsumerShadowStats
						.broad_path_planner_descriptor_digest =
						fasim_hex_u64(broadPlannerDescriptorDigest);
					broadPlannerDescriptorOpened = false;
				}
			}
			for (size_t i = 0; i < cudaQueries.size(); ++i)
			{
				FasimScopedSeconds scoped(phaseTimingEnabled,
				                          &phaseTiming.query_release_seconds);
				prealign_cuda_release_query(&cudaQueries[i]);
			}
				if (legacyScoreCudaQueryReady)
				{
					FasimScopedSeconds scoped(phaseTimingEnabled,
					                          &phaseTiming.query_release_seconds);
					prealign_cuda_release_query(&legacyScoreCudaQuery);
				}
				if (streamingScoreInfoLegacyByteCudaQueryReady)
				{
					FasimScopedSeconds scoped(phaseTimingEnabled,
					                          &phaseTiming.query_release_seconds);
					prealign_cuda_release_query(
						&streamingScoreInfoLegacyByteCudaQuery);
				}
				if (streamingScoreInfoGpuMinScoreCudaQueryReady)
				{
					FasimScopedSeconds scoped(phaseTimingEnabled,
					                          &phaseTiming.query_release_seconds);
					prealign_cuda_release_query(
						&streamingScoreInfoGpuMinScoreCudaQuery);
				}

			end = clock();
		cout << "finished normally" << endl;
			cpu_time = ((float)(end - start)) / CLOCKS_PER_SEC;
			cout<<"Running time is "<<cpu_time<<endl;
			if (phaseTimingEnabled)
			{
				fasim_print_top5_phase_timing_stats(phaseTiming);
			}
			if (minScoreShadowEnabled)
			{
				fasim_print_exact_column_min_score_shadow_stats(minScoreShadowStats);
			}
				if (legacyScoreGpuShadowEnabled ||
				    legacyScoreGpuReplacementEnabled ||
				    fasim_top5_gasal2_gpu_scoreinfo_enabled_runtime())
				{
					fasim_print_legacy_score_gpu_shadow_stats(legacyScoreGpuShadowStats);
				}
			fasim_print_gasal2_long_query_segmented_shadow_stats(
				gasal2LongQuerySegmentedShadowStats);
			fasim_print_gasal2_long_query_exact_tile_shadow_stats(
				gasal2LongQueryExactTileShadowStats);
			fasim_print_long_query_exact_column_scoreinfo_shadow_stats(
				longQueryExactColumnScoreInfoShadowStats);
			fasim_print_long_query_streaming_scoreinfo_shadow_stats(
				longQueryStreamingScoreInfoShadowStats);
			fasim_print_broad_scoreinfo_consumer_shadow_stats(
				broadScoreInfoConsumerShadowStats);
			fasim_gasal2_print_stats();
			return 0;
	}

	readDna(paraList.file1path, species, dnaChroTag, startGenomeTmp, dnaSeq);
	struct lgInfo algInfo;
	triplex atriplex;
	vector<struct triplex> cut_triplex_list[core_num+1];
	vector<struct triplex> collect_triplex[core_num+1];
	vector<struct triplex> sort_triplex_list;
	vector<struct triplex> swap_list;
	for(int i=0;i<species.size();i++){
	    thread_num = i%core_num;
        if(core_num==1){
            thread_num==0;
        }
		algInfo = lgInfo(lncName, lncSeq, species[i], dnaChroTag[i], fileName, dnaSeq[i],startGenomeTmp[i], resultDir);
	    lgList.push_back(algInfo);
	    LongTarget(paraList, lgList[i].lncSeq, lgList[i].dnaSeq, cut_triplex_list[thread_num]);
	    for(int j=0;j<cut_triplex_list[thread_num].size();j++)
	    {
	        atriplex = cut_triplex_list[thread_num][j];
	        if(atriplex.genomestart==0){
                cut_triplex_list[thread_num][j].chr = dnaChroTag[i];
                cut_triplex_list[thread_num][j].genomestart = atriplex.starj+startGenomeTmp[i]-1;
                cut_triplex_list[thread_num][j].genomeend = atriplex.endj+startGenomeTmp[i]-1;
	        }
	    }
	    for(int j=0;j<cut_triplex_list[thread_num].size();j++){
	        atriplex = cut_triplex_list[thread_num][j];
	        collect_triplex[thread_num].push_back(atriplex);
	    }
	    cut_triplex_list[thread_num].clear();
	}
	  for(int r_num=0;r_num<core_num;r_num++)
    {
        for(int k_num=0;k_num<collect_triplex[r_num].size();k_num++)
        {
            triplex btr=collect_triplex[r_num][k_num];
            sort_triplex_list.push_back(btr);
        }
    }
	printResult(lgList[0].species, paraList, lncName,
		fileName, sort_triplex_list, lgList[0].dnaChroTag,
		lgList[0].dnaSeq, lgList[0].startGenome, c_tmp_dd, c_tmp_length,resultDir,lncSeq);
	end = clock();
	cout << "finished normally" << endl;
	cpu_time = ((float)(end - start)) / CLOCKS_PER_SEC;
	cout<<"Running time is "<<cpu_time<<endl;
	fasim_print_gasal2_long_query_segmented_shadow_stats(
		gasal2LongQuerySegmentedShadowStats);
	fasim_print_gasal2_long_query_exact_tile_shadow_stats(
		gasal2LongQueryExactTileShadowStats);
	fasim_print_long_query_exact_column_scoreinfo_shadow_stats(
		longQueryExactColumnScoreInfoShadowStats);
	fasim_print_long_query_streaming_scoreinfo_shadow_stats(
		longQueryStreamingScoreInfoShadowStats);
	fasim_print_broad_scoreinfo_consumer_shadow_stats(
		broadScoreInfoConsumerShadowStats);
	fasim_gasal2_print_stats();
	return 0;
}

string readRna(string rnaFileName, string &lncName)
{
	ifstream rnaFile;
	string tmpRNA;
	string tmpStr;
	rnaFile.open(rnaFileName.c_str());
	getline(rnaFile, tmpStr);
	int i = 0;
	string tmpInfo;
	for (i = 0; i < tmpStr.size(); i++)
	{
		if (tmpStr[i] == '>')
		{
			continue;
		}
		tmpInfo = tmpInfo + tmpStr[i];
	}
	lncName = tmpInfo;
	cout << lncName << endl;
	while (getline(rnaFile, tmpStr))
	{
	    tmpStr.erase(remove(tmpStr.begin(), tmpStr.end(), '\r'), tmpStr.end());
	    tmpStr.erase(remove(tmpStr.begin(), tmpStr.end(), '\n'), tmpStr.end());
		tmpRNA = tmpRNA + tmpStr;
	}
	fasim_normalize_sequence_uppercase(tmpRNA);
	return tmpRNA;
}

void readDna(string dnaFileName, vector<string> &speciess, vector<string> &chroTags,vector<long> &startGenomes,vector<string> &dnaSeqs)
{
	ifstream dnaFile(dnaFileName.c_str());
	if (!dnaFile.is_open())
	{
		cerr << "failed to open DNA fasta: " << dnaFileName << endl;
		return;
	}

	string pendingHeader;
	FasimFastaRecord record;
	while (fasim_read_next_fasta_record(dnaFile, pendingHeader, record))
	{
		if (record.sequence.empty())
		{
			continue;
		}
		string species;
		string chroTag;
		long startGenome = 1;
		fasim_parse_dna_header_fields(record.header, species, chroTag, startGenome);
		speciess.push_back(species);
		chroTags.push_back(chroTag);
		startGenomes.push_back(startGenome);
		dnaSeqs.push_back(record.sequence);
	}
}

void initEnv(int argc, char * const *argv, struct para &paraList)
{
	const char* optstring = "f:s:r:O:c:m:t:i:S:z:Y:Z:h:C:D:E:o:y:Fd";
	struct option long_options[] = {
		{"f1", required_argument, NULL, 'f'},
		{"f2", required_argument, NULL, 's'},
		{"ni", required_argument, NULL, 'y'},
		{"na", required_argument, NULL, 'z'},
		{"pc", required_argument, NULL, 'Y'},
		{"pt", required_argument, NULL, 'Z'},
		{"cn", required_argument, NULL, 'C'},
		{"ds", required_argument, NULL, 'D'},
		{"lg", required_argument, NULL, 'E'},
		{0, 0, 0, 0}
	};
	paraList.file1path = "./";
	paraList.file2path = "./";
	paraList.outpath = "./";
	paraList.rule = 0;
	paraList.cutLength = 5000;
	paraList.strand = 0;
	paraList.overlapLength = 100;
	paraList.minScore = 0;
	paraList.detailOutput = false;
	paraList.ntMin = 20;
	paraList.ntMax = 100000;
	paraList.scoreMin = 0.0;
	paraList.minIdentity = 60.0;
	paraList.minStability = 1;
	paraList.penaltyT = -1000;
	paraList.penaltyC = 0;
	paraList.cDistance = 15;
	paraList.cLength = 50;
	paraList.doFastSim = true;
	paraList.corenum = 1;
	int opt;
	bool boolvalue;
	if (argc == 1)
	{
		show_help();
	}
	while ((opt = getopt_long_only(argc, argv, optstring, long_options, NULL))
		!= -1)
	{
		switch (opt)
		{
		case 'f':
			paraList.file1path = optarg;
			break;
		case 's':
			paraList.file2path = optarg;
			break;
		case 'r':
			paraList.rule = atoi(optarg);
			break;
		case 'O':
			paraList.outpath = optarg;
			break;
		case 'c':
			paraList.cutLength = atoi(optarg);
			break;
		case 'm':
			paraList.minScore = atoi(optarg);
			break;
		case 't':
			paraList.strand = atoi(optarg);
			break;
		case 'd':
			paraList.detailOutput = true;
			break;
		case 'i':
			paraList.minIdentity = atoi(optarg);
			break;
		case 'S':
			paraList.minStability = atoi(optarg);
			break;
		case 'y':
			paraList.ntMin = atoi(optarg);
			break;
		case 'z':
			paraList.ntMax = atoi(optarg);
			break;
		case 'Y':
			paraList.penaltyC = atoi(optarg);
			break;
		case 'Z':
			paraList.penaltyT = atoi(optarg);
			break;
		case 'o':
			paraList.overlapLength = atoi(optarg);
			break;
        case 'F':
            paraList.doFastSim = false;
            break;
		case 'h':
			show_help();
			break;
		case 'D':
			paraList.cDistance = atoi(optarg);
			break;
		case 'E':
			paraList.cLength = atoi(optarg);
			break;
		case 'C':
		    paraList.corenum=atoi(optarg);//define how many core in parallel work
            break;
		}
	}
}

void LongTarget(struct para &paraList, string rnaSequence, string dnaSequence,
	vector<struct triplex> &sort_triplex_list)
{
	vector< string> dnaSequencesVec;
	vector< int> dnaSequencesStartPos;
	int cut_num = 0;
	cutSequence(dnaSequence, dnaSequencesVec,dnaSequencesStartPos, paraList.cutLength,paraList.overlapLength, cut_num);
	vector<struct triplex> triplex_list;
	const bool verbose = fasim_verbose_enabled_runtime();

	bool useCudaBatch = false;
	if (paraList.doFastSim && fasim_prealign_cuda_enabled_runtime() && prealign_cuda_is_built())
	{
		static bool cudaInitDone = false;
		static bool cudaInitOk = false;
		static string cachedQuery;
		static PreAlignCudaQueryHandle cudaQuery;
		static std::vector<int16_t> queryProfile;
		static int cachedSegLen = 0;

		if (!cudaInitDone)
		{
			cudaInitDone = true;
			string cudaError;
			cudaInitOk = prealign_cuda_init(fasim_cuda_device_runtime(), &cudaError);
		}

		if (cudaInitOk)
		{
			if (cachedQuery != rnaSequence)
			{
				prealign_cuda_release_query(&cudaQuery);
				fasim_build_query_profile(rnaSequence, 5, 4, queryProfile, cachedSegLen);
				string cudaError;
				if (!prealign_cuda_prepare_query(&cudaQuery, queryProfile.data(), 5, cachedSegLen, static_cast<int>(rnaSequence.size()), &cudaError))
				{
					cudaInitOk = false;
				}
				else
				{
					cachedQuery = rnaSequence;
				}
			}
		}

		useCudaBatch = cudaInitOk && cudaQuery.profileDevice != 0;
		if (useCudaBatch)
		{
			const int maxTasks = fasim_env_int_or_default("FASIM_PREALIGN_CUDA_MAX_TASKS", 4096);
			int topK = fasim_env_int_or_default("FASIM_PREALIGN_CUDA_TOPK", 64);
			if (topK > 256)
			{
				topK = 256;
			}
			if (topK <= 0)
			{
				topK = 64;
			}

			std::vector<FasimPrealignCudaTask> tasks;
			std::vector<uint8_t> encodedTargets;
			int currentTargetLength = -1;

			auto flush_batch = [&]()
			{
				if (tasks.empty())
				{
					return;
				}
				const bool debugCuda = getenv("FASIM_DEBUG_CUDA_PREALIGN") != NULL && getenv("FASIM_DEBUG_CUDA_PREALIGN")[0] != '\0' && getenv("FASIM_DEBUG_CUDA_PREALIGN")[0] != '0';

				std::vector<PreAlignCudaPeak> peaks;
				PreAlignCudaBatchResult batchResult;
				string cudaError;
				const bool ok = prealign_cuda_find_topk_column_maxima(cudaQuery,
				                                                    encodedTargets.data(),
				                                                    static_cast<int>(tasks.size()),
				                                                    currentTargetLength,
				                                                    topK,
				                                                    &peaks,
				                                                    &batchResult,
				                                                    &cudaError);
				if (!ok)
				{
					// Fallback to CPU fastSIM for this batch, then keep using CPU.
					useCudaBatch = false;
					for (size_t t = 0; t < tasks.size(); ++t)
					{
						FasimPrealignCudaTask &task = tasks[t];
						string srcSeq;
						fasim_apply_src_transform(*task.seq1, task.srcTransform, srcSeq);
						const int minScore = static_cast<int>(calc_score_once(rnaSequence, task.seq2, task.dnaStartPos, paraList.rule) * 0.8);
						fastSIM(rnaSequence,
						        task.seq2,
						        srcSeq,
						        task.dnaStartPos,
						        minScore,
						        5,
						        -4,
						        -12,
						        -4,
						        triplex_list,
						        task.strand,
						        task.Para,
						        task.rule,
						        paraList.ntMin,
						        paraList.ntMax,
						        paraList.penaltyT,
						        paraList.penaltyC,
						        paraList);
					}
					tasks.clear();
					encodedTargets.clear();
					currentTargetLength = -1;
					return;
				}

				StripedSmithWaterman::Aligner aligner;
				StripedSmithWaterman::Filter filter;
				StripedSmithWaterman::Alignment alignment;

				std::vector<struct StripedSmithWaterman::scoreInfo> finalScoreInfo;
				finalScoreInfo.reserve(static_cast<size_t>(topK));

				for (size_t t = 0; t < tasks.size(); ++t)
				{
					FasimPrealignCudaTask &task = tasks[t];
					const size_t base = t * static_cast<size_t>(topK);
					const int maxScore = peaks[base].score;
					const int minScore = static_cast<int>(static_cast<double>(maxScore) * 0.8);

					finalScoreInfo.clear();
					const int suppressBp = fasim_prealign_peak_suppress_bp_runtime();
					for (int k = 0; k < topK; ++k)
					{
						const PreAlignCudaPeak &p = peaks[base + static_cast<size_t>(k)];
						if (p.position < 0 || p.score <= minScore)
						{
							continue;
						}
						bool suppressed = false;
						for (size_t s = 0; s < finalScoreInfo.size(); ++s)
						{
							if (abs(finalScoreInfo[s].position - p.position) < suppressBp)
							{
								suppressed = true;
								break;
							}
						}
						if (!suppressed)
						{
							finalScoreInfo.push_back(StripedSmithWaterman::scoreInfo(p.score, p.position));
						}
					}

					if (debugCuda && t == 0)
					{
						StripedSmithWaterman::Alignment fullAlignment;
						aligner.Align(rnaSequence.c_str(), task.seq2.c_str(), static_cast<int>(task.seq2.size()), filter, &fullAlignment, 15);

						cerr << "[fasim.cuda] batch taskCount=" << tasks.size()
						     << " targetLength=" << currentTargetLength
						     << " topK=" << topK
						     << " maxScore=" << maxScore
						     << " cpu_full_sw=" << fullAlignment.sw_score
						     << " minScore=" << minScore
						     << " peaksKept=" << finalScoreInfo.size()
						     << endl;
						const int toPrint = std::min(8, topK);
						for (int k = 0; k < toPrint; ++k)
						{
							const PreAlignCudaPeak &p = peaks[base + static_cast<size_t>(k)];
							cerr << "[fasim.cuda] peak[" << k << "] score=" << p.score << " pos=" << p.position << endl;
						}
					}

					if (finalScoreInfo.empty())
					{
						continue;
					}

					string srcSeq;
					fasim_apply_src_transform(*task.seq1, task.srcTransform, srcSeq);
					fastSIM_extend_from_scoreinfo(aligner,
					                              filter,
					                              alignment,
					                              15,
					                              rnaSequence,
					                              task.seq2,
					                              srcSeq,
					                              task.dnaStartPos,
					                              finalScoreInfo,
					                              triplex_list,
					                              task.strand,
					                              task.Para,
					                              task.rule,
					                              paraList.ntMin,
					                              paraList.ntMax,
					                              paraList.penaltyT,
					                              paraList.penaltyC,
					                              paraList);
				}

					tasks.clear();
					encodedTargets.clear();
					currentTargetLength = -1;
			};

			auto enqueue_task = [&](string &seq1, long dnaStartPos, int reverseMode, int paraMode, int rule, FasimSrcTransform srcTransform, bool reverseSeq2)
			{
				string seq2 = transferStringTableOptIn(seq1, reverseMode, paraMode, rule);
				if (reverseSeq2)
				{
					reverseSeq(seq2);
				}

				if (currentTargetLength < 0)
				{
					currentTargetLength = static_cast<int>(seq2.size());
					encodedTargets.reserve(static_cast<size_t>(maxTasks) * static_cast<size_t>(currentTargetLength));
				}
				if (static_cast<int>(seq2.size()) != currentTargetLength || static_cast<int>(tasks.size()) >= maxTasks)
				{
					flush_batch();
					if (!useCudaBatch)
					{
						return;
					}
					currentTargetLength = static_cast<int>(seq2.size());
					encodedTargets.reserve(static_cast<size_t>(maxTasks) * static_cast<size_t>(currentTargetLength));
				}

				FasimPrealignCudaTask task;
				task.seq1 = &seq1;
				task.seq2.swap(seq2);
				task.dnaStartPos = dnaStartPos;
				task.strand = reverseMode;
				task.Para = paraMode;
				task.rule = rule;
				task.srcTransform = srcTransform;
				tasks.push_back(std::move(task));

				const string &storedSeq2 = tasks.back().seq2;
				for (int k = 0; k < currentTargetLength; ++k)
				{
					encodedTargets.push_back(fasim_encode_base(static_cast<unsigned char>(storedSeq2[static_cast<size_t>(k)])));
				}
			};

			for (int i = 0; i < dnaSequencesVec.size(); i++)
			{
				long dnaStartPos = dnaSequencesStartPos[i];
				if (verbose)
				{
					cout << "dnaPos = " << dnaStartPos << endl;
				}
				string &seq1 = dnaSequencesVec[i];
				if (same_seq(seq1))
				{
					continue;
				}

				if (paraList.strand >= 0)
				{
					if (paraList.rule == 0)
					{
						for (int j = 0; j < 6; j++)
						{
							enqueue_task(seq1, dnaStartPos, 0, 1, j + 1, FASIM_SRC_ORIG, false);
							if (!useCudaBatch)
							{
								break;
							}
							enqueue_task(seq1, dnaStartPos, 1, 1, j + 1, FASIM_SRC_REVCOMP, true);
							if (!useCudaBatch)
							{
								break;
							}
						}
					}
					if (paraList.rule > 0 && paraList.rule < 7 && useCudaBatch)
					{
						enqueue_task(seq1, dnaStartPos, 0, 1, paraList.rule, FASIM_SRC_ORIG, false);
						if (useCudaBatch)
						{
							enqueue_task(seq1, dnaStartPos, 1, 1, paraList.rule, FASIM_SRC_REVCOMP, true);
						}
					}
				}

				if (paraList.strand <= 0 && useCudaBatch)
				{
					if (paraList.rule == 0)
					{
						for (int j = 0; j < 18; j++)
						{
							enqueue_task(seq1, dnaStartPos, 1, -1, j + 1, FASIM_SRC_COMP, false);
							if (!useCudaBatch)
							{
								break;
							}
							enqueue_task(seq1, dnaStartPos, 0, -1, j + 1, FASIM_SRC_REV, true);
							if (!useCudaBatch)
							{
								break;
							}
						}
					}
					else if (useCudaBatch)
					{
						enqueue_task(seq1, dnaStartPos, 1, -1, paraList.rule, FASIM_SRC_COMP, false);
						if (useCudaBatch)
						{
							enqueue_task(seq1, dnaStartPos, 0, -1, paraList.rule, FASIM_SRC_REV, true);
						}
					}
				}

				if (!useCudaBatch)
				{
					break;
				}
			}

			if (useCudaBatch)
			{
				flush_batch();
			}
		}
	}

	if (!useCudaBatch)
	{
		int minScore = 0, minscore;
		string seqrev;
		for (int i = 0; i < dnaSequencesVec.size(); i++)
		{
			long dnaStartPos = dnaSequencesStartPos[i];
			if (verbose)
			{
				cout << "dnaPos = " << dnaStartPos << endl;
			}
			string seq1 = dnaSequencesVec[i];
			if (same_seq(seq1))
			{
				continue;
			}
			if (paraList.strand >= 0)
			{
				if (paraList.rule == 0)
				{
					for (int j = 0; j < 6; j++)
					{
						string seq2 = transferStringTableOptIn(seq1, 0, 1, j + 1);
						if (paraList.doFastSim)
						{
							minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
							minScore = minscore;
							fastSIM(rnaSequence, seq2, seq1, dnaStartPos, minScore, 5, -4,
								-12, -4, triplex_list, 0, 1, j + 1, paraList.ntMin,
								paraList.ntMax, paraList.penaltyT, paraList.penaltyC, paraList);
						}
						else
						{
							minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
							minScore = minscore;
							SIM(rnaSequence, seq2, seq1, dnaStartPos, minScore, 5, -4,
								-12, -4, triplex_list, 0, 1, j + 1, paraList.ntMin,
								paraList.ntMax, paraList.penaltyT, paraList.penaltyC);
						}
						seq2 = transferStringTableOptIn(seq1, 1, 1, j + 1);
						reverseSeq(seq2);
						seqrev = seq1;
						complement(seqrev);
						reverseSeq(seqrev);
						if (paraList.doFastSim)
						{
							minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
							minScore = minscore;
							fastSIM(rnaSequence, seq2, seqrev, dnaStartPos, minScore, 5, -4,
								-12, -4, triplex_list, 1, 1, j + 1, paraList.ntMin,
								paraList.ntMax, paraList.penaltyT, paraList.penaltyC, paraList);
						}
						else
						{
							minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
							minScore = minscore;
							SIM(rnaSequence, seq2, seqrev, dnaStartPos, minScore, 5, -4,
								-12, -4, triplex_list, 1, 1, j + 1, paraList.ntMin,
								paraList.ntMax, paraList.penaltyT, paraList.penaltyC);
						}
					}
				}
				if (paraList.rule > 0 && paraList.rule < 7)
				{
					string seq2 = transferStringTableOptIn(seq1, 0, 1, paraList.rule);
					if (paraList.doFastSim)
					{
						minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
						minScore = minscore;
						fastSIM(rnaSequence, seq2, seq1, dnaStartPos, minScore, 5, -4,
							-12, -4, triplex_list, 0, 1, paraList.rule, paraList.ntMin,
							paraList.ntMax, paraList.penaltyT, paraList.penaltyC, paraList);
					}
					else
					{
						minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
						minScore = minscore;
						SIM(rnaSequence, seq2, seq1, dnaStartPos, minScore, 5, -4,
							-12, -4, triplex_list, 0, 1, paraList.rule, paraList.ntMin,
							paraList.ntMax, paraList.penaltyT, paraList.penaltyC);
					}

					seq2 = transferStringTableOptIn(seq1, 1, 1, paraList.rule);
					reverseSeq(seq2);
					seqrev = seq1;
					complement(seqrev);
					reverseSeq(seqrev);
					if (paraList.doFastSim)
					{
						minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
						minScore = minscore;
						fastSIM(rnaSequence, seq2, seqrev, dnaStartPos, minScore, 5, -4, -12,
							-4, triplex_list, 1, 1, paraList.rule, paraList.ntMin,
							paraList.ntMax, paraList.penaltyT, paraList.penaltyC, paraList);
					}
					else
					{
						minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
						minScore = minscore;
						SIM(rnaSequence, seq2, seqrev, dnaStartPos, minScore, 5, -4, -12,
							-4, triplex_list, 1, 1, paraList.rule, paraList.ntMin,
							paraList.ntMax, paraList.penaltyT, paraList.penaltyC);
					}
				}
			}
			if (paraList.strand <= 0)
			{
				if (paraList.rule == 0)
				{
					for (int j = 0; j < 18; j++)
					{
						string seq2 = transferStringTableOptIn(seq1, 1, -1, j + 1);
						seqrev = seq1;
						complement(seqrev);
						if (paraList.doFastSim)
						{
							minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
							minScore = minscore;
							fastSIM(rnaSequence, seq2, seqrev, dnaStartPos, minScore, 5, -4,
								-12, -4, triplex_list, 1, -1, j + 1, paraList.ntMin,
								paraList.ntMax, paraList.penaltyT, paraList.penaltyC, paraList);
						}
						else
						{
							minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
							minScore = minscore;
							SIM(rnaSequence, seq2, seqrev, dnaStartPos, minScore, 5, -4,
								-12, -4, triplex_list, 1, -1, j + 1, paraList.ntMin,
								paraList.ntMax, paraList.penaltyT, paraList.penaltyC);
						}

						seq2 = transferStringTableOptIn(seq1, 0, -1, j + 1);
						reverseSeq(seq2);
						seqrev = seq1;
						reverseSeq(seqrev);
						if (paraList.doFastSim)
						{
							minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
							minScore = minscore;
							fastSIM(rnaSequence, seq2, seqrev, dnaStartPos, minScore, 5, -4,
								-12, -4, triplex_list, 0, -1, j + 1, paraList.ntMin,
								paraList.ntMax, paraList.penaltyT, paraList.penaltyC, paraList);
						}
						else
						{
							minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
							minScore = minscore;
							SIM(rnaSequence, seq2, seqrev, dnaStartPos, minScore, 5, -4,
								-12, -4, triplex_list, 0, -1, j + 1, paraList.ntMin,
								paraList.ntMax, paraList.penaltyT, paraList.penaltyC);
						}

					}
				}
				else
				{
					string seq2 = transferStringTableOptIn(seq1, 1, -1, paraList.rule);
					seqrev = seq1;
					complement(seqrev);
					if (paraList.doFastSim)
					{
						minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
						minScore = minscore;
						fastSIM(rnaSequence, seq2, seqrev, dnaStartPos, minScore, 5, -4, -12,
							-4, triplex_list, 1, -1, paraList.rule, paraList.ntMin,
							paraList.ntMax, paraList.penaltyT, paraList.penaltyC, paraList);
					}
					else
					{
						minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
						minScore = minscore;
						SIM(rnaSequence, seq2, seqrev, dnaStartPos, minScore, 5, -4, -12,
							-4, triplex_list, 1, -1, paraList.rule, paraList.ntMin,
							paraList.ntMax, paraList.penaltyT, paraList.penaltyC);
					}
					seq2 = transferStringTableOptIn(seq1, 0, -1, paraList.rule);
					reverseSeq(seq2);
					seqrev = seq1;
					reverseSeq(seqrev);
					if (paraList.doFastSim)
					{
						minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
						minScore = minscore;
						fastSIM(rnaSequence, seq2, seqrev, dnaStartPos, minScore, 5, -4, -12,
							-4, triplex_list, 0, -1, paraList.rule, paraList.ntMin,
							paraList.ntMax, paraList.penaltyT, paraList.penaltyC, paraList);
					}
					else
					{
						minscore = calc_score_once(rnaSequence, seq2, dnaStartPos, paraList.rule) * 0.8;
						minScore = minscore;
						SIM(rnaSequence, seq2, seqrev, dnaStartPos, minScore, 5, -4, -12,
							-4, triplex_list, 0, -1, paraList.rule, paraList.ntMin,
							paraList.ntMax, paraList.penaltyT, paraList.penaltyC);
					}

				}
			}
		}
	}

	for (int i = 0; i < triplex_list.size(); i++)
	{
		triplex atr = triplex_list[i];
		if (atr.score >= paraList.scoreMin && atr.identity >= paraList.minIdentity
			&& atr.tri_score >= paraList.minStability && atr.nt >= paraList.cLength)
		{
			sort_triplex_list.push_back(atr);
		}
	}
}

void cluster_triplex(int dd, int length, vector<struct triplex>& triplex_list, map<size_t, size_t> class1[], map<size_t, size_t> class1a[], map<size_t, size_t> class1b[], int class_level)
{
	int i, j;
	int find = 0;
	map<size_t, struct axis> axis_map;
	int max_neartriplexnum = 0, max_pos = 0;
	int middle = 0;
	int count = 0;
	for (vector<struct triplex>::iterator it = triplex_list.begin(); it != triplex_list.end(); it++)
	{
	    //cout<< it->stari <<"-------"<<it->endi<<"  "<< it->nt <<endl;
		if (it->nt > length)
		{
			count++;
			middle = (int)((it->stari + it->endi) / 2);
			it->middle = middle;
			it->motif = 0;
			axis_map[middle].triplexnum++;

			for (i = -dd; i <= dd; i++)
			{
				if (i > 0)
				{
					axis_map[middle + i].neartriplex = axis_map[middle + i].neartriplex + (dd - i);
				}
				else if (i < 0)
				{
					axis_map[middle + i].neartriplex = axis_map[middle + i].neartriplex + (dd + i);
				}
				else
				{
				}
				if (axis_map[middle].triplexnum > 0)
				{
				    //cout<< middle+i << " hit>1  " << axis_map[middle + i].neartriplex <<endl;
					if (axis_map[middle + i].neartriplex > max_neartriplexnum)
					{
						max_neartriplexnum = axis_map[middle + i].neartriplex;
						max_pos = middle + i;
						find = 1;
					}
				}
			}
			it->neartriplex = axis_map[middle].neartriplex;
		}
	}
	int theclass = 1;
	while (find)
	{
		for (i = max_pos - dd; i <= max_pos + dd; i++)
		{
			for (vector<struct triplex>::iterator it = triplex_list.begin(); it != triplex_list.end(); it++)
			{
				if (it->middle == i && it->motif == 0)
				{
					it->motif = theclass;
					it->center = max_pos;
					if (theclass > class_level)
					{
						continue;
					}
					if (it->endj > it->starj)
						for (j = it->starj; j < it->endj; j++)
						{
							class1[theclass][j]++;
							class1a[theclass][j]++;
						}
					else
						for (j = it->endj; j < it->starj; j++)
						{
							class1[theclass][j]++;
							class1b[theclass][j]--;
						}
				}
			}
			//cout<<"axis_map.erase  "<< axis_map[i].neartriplex << "  pos "<< i <<endl;
			axis_map.erase(i);
		}
		max_neartriplexnum = 0;
		find = 0;
		for (i = 0 ; i<axis_map.size(); i++)
		{
			if (axis_map[i].neartriplex > max_neartriplexnum)
			{
				max_neartriplexnum = axis_map[i].neartriplex;
				max_pos = i;
				find = 1;
			}
		}
		++theclass;
	}
}


void print_cluster(int c_level, map<size_t, size_t> class1[], int start_genome, string &chro_info, int dna_size, string &rna_name, int distance, int length, string &outFilePath, string &c_tmp_dd, string &c_tmp_length, vector<struct tmp_class> &w_tmp_class)
{
	struct tmp_class a_tmp_class;
	char c_level_tmp[3];
	cout << c_level_tmp << c_level << endl;
	sprintf(c_level_tmp, "%d", c_level);
	string c_tmp_level;
	int c_level_loop = 0;
	for (c_level_loop = 0; c_level_loop < strlen(c_level_tmp); c_level_loop++)
	{
		c_tmp_level += c_level_tmp[c_level_loop];
	}
	string class_name = outFilePath.substr(0, outFilePath.size() - 10) + "-TFOclass" + c_tmp_level+"-"+c_tmp_dd+"-"+c_tmp_length;
	ofstream outfile(class_name.c_str(), ios::trunc);
	int map_tmp0 = 0, map_tmp1 = 0, map_tmp2 = 0, map_tmp3 = 0, map_count = 0, map_count1 = 0;
	int map_first1 = 0, map_second1 = 0;
	int map_first0 = 0, map_second0 = 0;
	int if_map1 = 0, if_map2 = 0, if_map3 = 0, if_map4 = 0;
	int if_map_flag = 0;
	outfile << "browser position " << chro_info << ":" << start_genome << "-" << start_genome + dna_size << endl;
	outfile << "browser hide all" << endl;
	outfile << "browser pack refGene encodeRegions" << endl;
	outfile << "browser full altGraph" << endl;
	outfile << "# 300 base wide bar graph, ausoScale is on by default == graphing" << endl;
	outfile << "# limits will dynamically change to always show full range of data" << endl;
	outfile << "# in viewing window, priority = 20 position this as the second graph" << endl;
	outfile << "# Note, zero-relative, half-open coordinate system in use for bedGraph format" << endl;
	outfile << "track type=bedGraph name='" << rna_name << " TTS (" << c_level << ")' description='" << distance << "-" << length << "' visibility=full color=200,100,0 altColor=0,100,200 priority=20" << endl;
	int final_genome = 0;
	for (map<size_t, size_t>::iterator it = class1[c_level].begin(); it != class1[c_level].end(); it++)
	{
		final_genome = it->first + start_genome;
	}
	for (map<size_t, size_t>::iterator it = class1[c_level].begin(); it != class1[c_level].end(); )
	{
		map_first0 = it->first;
		map_tmp1 = it->first;
		map_tmp2 = it->second;
		if ((it->first + start_genome) == final_genome || it == class1[c_level].end())
		{
			a_tmp_class = tmp_class(map_first0 + start_genome - 1, map_tmp1 + start_genome, map_tmp2, 0, 0);
			w_tmp_class.push_back(a_tmp_class);
			break;
		}
		it++;
		while (abs((long)(it->first - map_tmp1)) == 1 && (it->second == map_tmp2))
		{
			if ((it->first + start_genome) == final_genome)
			{
				break;
			}
			map_tmp1 = it->first;
			map_tmp2 = it->second;
			it++;
		}
		if (map_count == 0)
		{
			a_tmp_class = tmp_class(map_first0 + start_genome - 2, map_tmp1 + start_genome, map_tmp2, 0, 0);
			w_tmp_class.push_back(a_tmp_class);
			map_count++;
		}
		else
		{
			a_tmp_class = tmp_class(map_first0 + start_genome - 1, map_tmp1 + start_genome, map_tmp2, 0, 0);
			w_tmp_class.push_back(a_tmp_class);
		}
		if (abs((long)(it->first - map_tmp1)) != 1)
		{
			a_tmp_class = tmp_class(map_tmp1 + start_genome, it->first + start_genome - 1, 0, 0, 0);
			w_tmp_class.push_back(a_tmp_class);

		}
	}
	int w_class_loop = 0;
	for (w_class_loop = 0; w_class_loop < w_tmp_class.size(); w_class_loop++)
	{
		tmp_class btc = w_tmp_class[w_class_loop];
		outfile << chro_info << "\t" << btc.genome_start << "\t" << btc.genome_end << "\t" << btc.signal_level << endl;

		/*tmp_class ctc = w_tmp_class[w_class_loop + 1];
		if (btc.genome_start == final_genome)
		{
			break;
		}
		if (w_class_loop + 1 == w_tmp_class.size())
		{
		}
		if (btc.genome_start == ctc.genome_start)
		{
			if (1)
			{
				outfile << chro_info << "\t" << btc.genome_start << "\t" << ctc.genome_end << "\t" << ctc.signal_level << endl;
			}
			w_class_loop += 1;
		}
		else
		{
			outfile << chro_info << "\t" << btc.genome_start << "\t" << btc.genome_end << "\t" << btc.signal_level << endl;

		}*/
	}
}

void printResult(string &species, struct para paraList, string &lncName, string &dnaFile, vector<struct triplex> &sort_triplex_list, string &chroTag, string &dnaSequence, int start_genome, string &c_tmp_dd, string &c_tmp_length, string &resultDir,string lncSeq)
{
	vector<struct tmp_class> w_tmp_class;
	string pre_file2 = resultDir + "/" + species + "-" + lncName;
	string pre_file1=dnaFile;
	string outFilePath = pre_file2+"-"+pre_file1+"-TFOsorted";
//	string outFilePath = pre_file2 + "-fastSim-TFOsorted";
//	if(paraList.doFastSim==true)
//	    outFilePath = pre_file2 + "-fastSim-TFOsorted";
//	else
//	    outFilePath = pre_file2 + "-Sim-TFOsorted"
	ofstream outFile(outFilePath.c_str(), ios::trunc);
	outFile << "QueryStart\t" << "QueryEnd\t" << "StartInSeq\t" << "EndInSeq\t" << "Direction\t" << "Chr\t" <<"StartInGenome\t" << "EndInGenome\t" << "MeanStability\t" << "MeanIdentity(%)\t" << "Strand\t" << "Rule\t" << "Score\t" << "Nt(bp)\t" << "Class\t" << "MidPoint\t" << "Center\t" << "TFO sequence\t" << "TTS sequence"<< endl;

	const FasimOutputMode outputMode = fasim_output_mode_runtime();
	const bool doCluster = (outputMode == FASIM_OUTPUT_FULL);
	map<size_t, size_t> class1[6], class1a[6], class1b[6];
	int class_level = 5;
	if (doCluster)
	{
		cluster_triplex(paraList.cDistance, paraList.cLength, sort_triplex_list, class1, class1a, class1b, class_level);
		sort(sort_triplex_list.begin(), sort_triplex_list.end(), comp);
	}
	for (int i = 0; i < sort_triplex_list.size(); i++)
	{
		triplex atr = sort_triplex_list[i];
		if (doCluster && sort_triplex_list[i].motif == 0)
		{
			continue;
		}
		const int motif = doCluster ? atr.motif : 0;
		const int middle = doCluster ? atr.middle : static_cast<int>((atr.stari + atr.endi) / 2);
		const int center = doCluster ? atr.center : middle;
		if (atr.starj < atr.endj)
			outFile << atr.stari << "\t" << atr.endi << "\t" << atr.starj << "\t" << atr.endj << "\t" << "R\t" << atr.chr << "\t"  <<atr.genomestart  << "\t" << atr.genomeend << "\t" << atr.tri_score << "\t" << atr.identity << "\t" << getStrand(atr.reverse, atr.strand) << "\t" << atr.rule << "\t" << atr.score << "\t" << atr.nt << "\t" << motif << "\t" << middle << "\t" << center << "\t" << atr.stri_align << "\t" << atr.strj_align<< endl;
		else
			outFile << atr.stari << "\t" << atr.endi << "\t" << atr.starj << "\t" << atr.endj << "\t" << "L\t" << atr.chr << "\t"  <<atr.genomestart << "\t" << atr.genomeend << "\t" << atr.tri_score << "\t" << atr.identity << "\t" << getStrand(atr.reverse, atr.strand) << "\t" << atr.rule << "\t" << atr.score << "\t" << atr.nt << "\t" << motif << "\t" << middle << "\t" << center << "\t" << atr.stri_align << "\t" << atr.strj_align<< endl;

	}
	outFile.close();

	int pr_loop = 0;
	if (doCluster)
	{
		for (pr_loop = 1; pr_loop < 3; pr_loop++)
		{
			print_cluster(pr_loop, class1, start_genome - 1, chroTag, dnaSequence.size(), lncName, paraList.cDistance, paraList.cLength, outFilePath, c_tmp_dd, c_tmp_length, w_tmp_class);
			w_tmp_class.clear();
		}
	}
	vector<struct tmp_class>tmpClass;
	tmpClass.swap(w_tmp_class);
	for (pr_loop = 0; pr_loop < 6; pr_loop++)
	{
		class1[pr_loop].clear();
		class1a[pr_loop].clear();
		class1b[pr_loop].clear();
	}
}

bool comp(const triplex &a, const triplex &b)
{
	return a.motif < b.motif;
}
string getStrand(int reverse, int strand)
{
	string Strand;
	if (reverse == 1 && strand == 0)
	{
		Strand = "ParaPlus";
	}
	else if (reverse == 1 && strand == 1)
	{
		Strand = "ParaMinus";
	}
	else if (reverse == -1 && strand == 1)
	{
		Strand = "AntiMinus";
	}
	else if (reverse == -1 && strand == 0)
	{
		Strand = "AntiPlus";
	}
	return Strand;
}

int same_seq(const string &w_str)
{
	const string &A = w_str;
	int a = 0, c = 0, g = 0, t = 0, u = 0, n = 0;
	for (size_t i = 0; i < A.size(); i++)
	{
		switch (A[i])
		{
		case 'A':
		case 'a':
			a++;
			break;
		case 'C':
		case 'c':
			c++;
			break;
		case 'G':
		case 'g':
			g++;
			break;
		case 'T':
		case 't':
			t++;
			break;
		case 'U':
		case 'u':
			u++;
			break;
		case 'N':
		case 'n':
			n++;
			break;
		default:
			return 0;
		}
	}
	if (a == A.size())
	{
		return 1;
	}
	else if (c == A.size())
	{
		return 1;
	}
	else if (g == A.size())
	{
		return 1;
	}
	else if (t == A.size())
	{
		return 1;
	}
	else if (u == A.size())
	{
		return 1;
	}
	else if (n == A.size())
	{
		return 1;
	}
	else
	{
		return 0;
	}
}

void show_help()
{
	cout << "This is the help page." << endl;
	cout << "options	 Parameters			functions" << endl;
	cout << "f1	 DNA sequence file	used to get the DNA sequence" << endl;
	cout << "f2	 RNA sequence file	used to get the RNA sequence" << endl;
	cout << "r		rules							rules used to construct triplexes.int type.0 is all." << endl;
	cout << "O		Output path				if you define this,output result will be in the path.default is pwd" << endl;
	cout << "c		Cutlength					Cut sequence's length." << endl;
	cout << "m		min_score					Min_score...this option maybe useless.keep it for now." << endl;
	cout << "d		detailoutut				if you choose -d option,it will generate a triplex.detail file which describes the sequence-alignment." << endl;
	cout << "i		identity					 a condition used to pick up triplexes.default is 60.this should be int type such as 60,not 0.6.default is 60." << endl;
	cout << "S		stability					a condition like identity,should be float type such as 1.0.default is 1.0." << endl;
	cout << "ni	 ntmin							triplexes' min length.default is 20." << endl;
	cout << "na	 ntmax							triplexes' max length.default is 100." << endl;
	cout << "pc	 penaltyC					 penalty about GG.default is 0." << endl;
	cout << "pt	 penaltyT					 penalty about AA.default is -1000." << endl;
	cout << "ds	 c_dd							 distance used by cluster function.default is 15." << endl;
	cout << "lg	 c_length					 triplexes' length threshold used in cluster function.default is 50." << endl;
	cout << "F     doFastSim     if true, fastSIM function will be used instead of SIM function." << endl;
	cout << "all parameters are listed.If you want to run a simple example,type ./LongTarget -f1 DNAseq.fa -f2 RNAseq.fa -r 0 will be OK" << endl;
	cout << "any problems or bugs found please send email to us:zhuhao@smu.edu.cn." << endl;
	exit(1);
}
