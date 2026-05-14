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

#include "fastsim.h"
using namespace std;

namespace
{

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

static inline bool fasim_profile_enabled_runtime()
{
    const char *env = getenv("FASIM_PROFILE");
    if (env == NULL || env[0] == '\0')
    {
        return false;
    }
    return env[0] != '0';
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

static inline bool fasim_gpu_dp_column_mismatch_debug_enabled_runtime()
{
    return fasim_env_flag_enabled("FASIM_GPU_DP_COLUMN_MISMATCH_DEBUG");
}

static inline bool fasim_gpu_dp_column_full_scoreinfo_debug_enabled_runtime()
{
    return fasim_env_flag_enabled("FASIM_GPU_DP_COLUMN_FULL_SCOREINFO_DEBUG");
}

static inline bool fasim_gpu_dp_column_post_topk_pack_shadow_enabled_runtime()
{
    return fasim_env_flag_enabled("FASIM_GPU_DP_COLUMN_POST_TOPK_PACK_SHADOW");
}

static inline int fasim_env_int_or_default_allow_zero(const char *name, int defaultValue)
{
    const char *env = getenv(name);
    if (env == NULL || env[0] == '\0')
    {
        return defaultValue;
    }
    return atoi(env);
}

static inline uint64_t fasim_profile_now_nanoseconds()
{
    return static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count());
}

static inline double fasim_profile_seconds(uint64_t nanoseconds)
{
    return static_cast<double>(nanoseconds) / 1.0e9;
}

static inline uint64_t fasim_profile_nanoseconds_from_seconds(double seconds)
{
    if (seconds <= 0.0)
    {
        return 0;
    }
    return static_cast<uint64_t>((seconds * 1.0e9) + 0.5);
}

struct FasimProfileStats
{
    FasimProfileStats() :
        totalNanoseconds(0),
        ioNanoseconds(0),
        windowGenerationNanoseconds(0),
        windowGenerationCutSequenceNanoseconds(0),
        windowGenerationTransferNanoseconds(0),
        windowGenerationReverseNanoseconds(0),
        windowGenerationSourceTransformNanoseconds(0),
        windowGenerationEncodeNanoseconds(0),
        windowGenerationFlushNanoseconds(0),
        dpScoringNanoseconds(0),
        columnMaxNanoseconds(0),
        localMaxNanoseconds(0),
        nonoverlapNanoseconds(0),
        validationNanoseconds(0),
        outputNanoseconds(0),
        numQueries(0),
        numWindows(0),
        numDpCells(0),
        numCandidates(0),
        numValidatedCandidates(0),
        numFinalHits(0),
        gpuDpColumnActive(0),
        gpuDpColumnCalls(0),
        gpuDpColumnWindows(0),
        gpuDpColumnCells(0),
        gpuDpColumnH2DBytes(0),
        gpuDpColumnD2HBytes(0),
        gpuDpColumnKernelNanoseconds(0),
        gpuDpColumnTotalNanoseconds(0),
        gpuDpColumnValidateNanoseconds(0),
        gpuDpColumnTopKCap(0),
        gpuDpColumnScoreMismatches(0),
        gpuDpColumnColumnMaxMismatches(0),
        gpuDpColumnFallbacks(0),
        gpuDpColumnDebugWindowsExamined(0),
        gpuDpColumnFirstMismatchWindow(-1),
        gpuDpColumnFirstMismatchColumn(-1),
        gpuDpColumnFirstMismatchCpuScore(0),
        gpuDpColumnFirstMismatchGpuScore(0),
        gpuDpColumnFirstMismatchCpuPosition(-1),
        gpuDpColumnFirstMismatchGpuPosition(-1),
        gpuDpColumnFirstMismatchCpuCount(0),
        gpuDpColumnFirstMismatchGpuCount(0),
        gpuDpColumnFirstMismatchTie(0),
        gpuDpColumnScoreInfoFieldMismatchMask(0),
        gpuDpColumnScoreDeltaMax(0),
        gpuDpColumnScoreInfoMismatches(0),
        gpuDpColumnTieMismatches(0),
        gpuDpColumnPositionMismatches(0),
        gpuDpColumnTopKTruncatedWindows(0),
        gpuDpColumnTopKOverflowWindows(0),
        gpuDpColumnPreTopKMismatches(0),
        gpuDpColumnPostTopKMismatches(0),
        gpuDpColumnFullDebugWindowIndex(-1),
        gpuDpColumnFullDebugCpuRecords(0),
        gpuDpColumnFullDebugGpuPreTopKRecords(0),
        gpuDpColumnFullDebugGpuPostTopKRecords(0),
        gpuDpColumnFullDebugCpuRecordMissingPreTopK(0),
        gpuDpColumnFullDebugCpuRecordMissingPostTopK(0),
        gpuDpColumnFullDebugFirstMismatchRank(-1),
        gpuDpColumnFullDebugFirstMismatchScoreDelta(0),
        gpuDpColumnFullDebugFirstMismatchPositionDelta(0),
        gpuDpColumnFullDebugFirstMismatchCountDelta(0),
        gpuDpColumnFullDebugScoreInfoSetMismatches(0),
        gpuDpColumnFullDebugScoreInfoFieldMismatches(0),
        gpuDpColumnFullDebugColumnMismatches(0),
        gpuDpColumnFullDebugColumnScoreDeltaMax(0),
        gpuDpColumnPostTopKCpuRecords(0),
        gpuDpColumnPostTopKGpuPreRecords(0),
        gpuDpColumnPostTopKGpuPostRecords(0),
        gpuDpColumnPostTopKCpuPackMismatches(0),
        gpuDpColumnPostTopKGpuPackMismatches(0),
        gpuDpColumnPostTopKMissingRecords(0),
        gpuDpColumnPostTopKExtraRecords(0),
        gpuDpColumnPostTopKRankMismatches(0),
        gpuDpColumnPostTopKFieldMismatchMask(0),
        gpuDpColumnPostTopKCountMismatches(0),
        gpuDpColumnPostTopKPositionMismatches(0),
        gpuDpColumnPostTopKScoreMismatches(0)
    {
    }

    uint64_t totalNanoseconds;
    uint64_t ioNanoseconds;
    uint64_t windowGenerationNanoseconds;
    uint64_t windowGenerationCutSequenceNanoseconds;
    uint64_t windowGenerationTransferNanoseconds;
    uint64_t windowGenerationReverseNanoseconds;
    uint64_t windowGenerationSourceTransformNanoseconds;
    uint64_t windowGenerationEncodeNanoseconds;
    uint64_t windowGenerationFlushNanoseconds;
    uint64_t dpScoringNanoseconds;
    uint64_t columnMaxNanoseconds;
    uint64_t localMaxNanoseconds;
    uint64_t nonoverlapNanoseconds;
    uint64_t validationNanoseconds;
    uint64_t outputNanoseconds;
    uint64_t numQueries;
    uint64_t numWindows;
    uint64_t numDpCells;
    uint64_t numCandidates;
    uint64_t numValidatedCandidates;
    uint64_t numFinalHits;
    uint64_t gpuDpColumnActive;
    uint64_t gpuDpColumnCalls;
    uint64_t gpuDpColumnWindows;
    uint64_t gpuDpColumnCells;
    uint64_t gpuDpColumnH2DBytes;
    uint64_t gpuDpColumnD2HBytes;
    uint64_t gpuDpColumnKernelNanoseconds;
    uint64_t gpuDpColumnTotalNanoseconds;
    uint64_t gpuDpColumnValidateNanoseconds;
    uint64_t gpuDpColumnTopKCap;
    uint64_t gpuDpColumnScoreMismatches;
    uint64_t gpuDpColumnColumnMaxMismatches;
    uint64_t gpuDpColumnFallbacks;
    uint64_t gpuDpColumnDebugWindowsExamined;
    long long gpuDpColumnFirstMismatchWindow;
    long long gpuDpColumnFirstMismatchColumn;
    int gpuDpColumnFirstMismatchCpuScore;
    int gpuDpColumnFirstMismatchGpuScore;
    int gpuDpColumnFirstMismatchCpuPosition;
    int gpuDpColumnFirstMismatchGpuPosition;
    uint64_t gpuDpColumnFirstMismatchCpuCount;
    uint64_t gpuDpColumnFirstMismatchGpuCount;
    uint64_t gpuDpColumnFirstMismatchTie;
    uint64_t gpuDpColumnScoreInfoFieldMismatchMask;
    uint64_t gpuDpColumnScoreDeltaMax;
    uint64_t gpuDpColumnScoreInfoMismatches;
    uint64_t gpuDpColumnTieMismatches;
    uint64_t gpuDpColumnPositionMismatches;
    uint64_t gpuDpColumnTopKTruncatedWindows;
    uint64_t gpuDpColumnTopKOverflowWindows;
    uint64_t gpuDpColumnPreTopKMismatches;
    uint64_t gpuDpColumnPostTopKMismatches;
    long long gpuDpColumnFullDebugWindowIndex;
    uint64_t gpuDpColumnFullDebugCpuRecords;
    uint64_t gpuDpColumnFullDebugGpuPreTopKRecords;
    uint64_t gpuDpColumnFullDebugGpuPostTopKRecords;
    uint64_t gpuDpColumnFullDebugCpuRecordMissingPreTopK;
    uint64_t gpuDpColumnFullDebugCpuRecordMissingPostTopK;
    long long gpuDpColumnFullDebugFirstMismatchRank;
    long long gpuDpColumnFullDebugFirstMismatchScoreDelta;
    long long gpuDpColumnFullDebugFirstMismatchPositionDelta;
    long long gpuDpColumnFullDebugFirstMismatchCountDelta;
    uint64_t gpuDpColumnFullDebugScoreInfoSetMismatches;
    uint64_t gpuDpColumnFullDebugScoreInfoFieldMismatches;
    uint64_t gpuDpColumnFullDebugColumnMismatches;
    uint64_t gpuDpColumnFullDebugColumnScoreDeltaMax;
    uint64_t gpuDpColumnPostTopKCpuRecords;
    uint64_t gpuDpColumnPostTopKGpuPreRecords;
    uint64_t gpuDpColumnPostTopKGpuPostRecords;
    uint64_t gpuDpColumnPostTopKCpuPackMismatches;
    uint64_t gpuDpColumnPostTopKGpuPackMismatches;
    uint64_t gpuDpColumnPostTopKMissingRecords;
    uint64_t gpuDpColumnPostTopKExtraRecords;
    uint64_t gpuDpColumnPostTopKRankMismatches;
    uint64_t gpuDpColumnPostTopKFieldMismatchMask;
    uint64_t gpuDpColumnPostTopKCountMismatches;
    uint64_t gpuDpColumnPostTopKPositionMismatches;
    uint64_t gpuDpColumnPostTopKScoreMismatches;
    FasimTransferStringProfileStats transferStringProfile;
};

static inline void fasim_profile_add_elapsed(uint64_t &slot, uint64_t startNanoseconds)
{
    slot += fasim_profile_now_nanoseconds() - startNanoseconds;
}

static inline void fasim_profile_add_elapsed_to(uint64_t &slot,
                                                uint64_t &secondSlot,
                                                uint64_t startNanoseconds)
{
    const uint64_t elapsed = fasim_profile_now_nanoseconds() - startNanoseconds;
    slot += elapsed;
    secondSlot += elapsed;
}

static inline void fasim_print_profile_stats(const FasimProfileStats &stats)
{
    cerr << "benchmark.fasim_total_seconds=" << fasim_profile_seconds(stats.totalNanoseconds) << endl;
    cerr << "benchmark.fasim_io_seconds=" << fasim_profile_seconds(stats.ioNanoseconds) << endl;
    cerr << "benchmark.fasim_window_generation_seconds=" << fasim_profile_seconds(stats.windowGenerationNanoseconds) << endl;
    cerr << "benchmark.fasim_window_generation_cut_sequence_seconds=" << fasim_profile_seconds(stats.windowGenerationCutSequenceNanoseconds) << endl;
    cerr << "benchmark.fasim_window_generation_transfer_seconds=" << fasim_profile_seconds(stats.windowGenerationTransferNanoseconds) << endl;
    cerr << "benchmark.fasim_window_generation_reverse_seconds=" << fasim_profile_seconds(stats.windowGenerationReverseNanoseconds) << endl;
    cerr << "benchmark.fasim_window_generation_source_transform_seconds=" << fasim_profile_seconds(stats.windowGenerationSourceTransformNanoseconds) << endl;
    cerr << "benchmark.fasim_window_generation_encode_seconds=" << fasim_profile_seconds(stats.windowGenerationEncodeNanoseconds) << endl;
    cerr << "benchmark.fasim_window_generation_flush_seconds=" << fasim_profile_seconds(stats.windowGenerationFlushNanoseconds) << endl;
    cerr << "benchmark.fasim_transfer_string_seconds=" << fasim_profile_seconds(stats.transferStringProfile.totalNanoseconds) << endl;
    cerr << "benchmark.fasim_transfer_string_calls=" << stats.transferStringProfile.calls << endl;
    cerr << "benchmark.fasim_transfer_string_input_bases=" << stats.transferStringProfile.inputBases << endl;
    cerr << "benchmark.fasim_transfer_string_output_bases=" << stats.transferStringProfile.outputBases << endl;
    cerr << "benchmark.fasim_transfer_string_rule_select_seconds=" << fasim_profile_seconds(stats.transferStringProfile.ruleSelectNanoseconds) << endl;
    cerr << "benchmark.fasim_transfer_string_rule_materialize_seconds=" << fasim_profile_seconds(stats.transferStringProfile.ruleMaterializeNanoseconds) << endl;
    cerr << "benchmark.fasim_transfer_string_convert_seconds=" << fasim_profile_seconds(stats.transferStringProfile.convertNanoseconds) << endl;
    cerr << "benchmark.fasim_transfer_string_validate_seconds=" << fasim_profile_seconds(stats.transferStringProfile.validateNanoseconds) << endl;
    cerr << "benchmark.fasim_transfer_string_residual_seconds=" << fasim_profile_seconds(stats.transferStringProfile.residualNanoseconds) << endl;
    cerr << "benchmark.fasim_transfer_string_table_shadow_enabled=" << (fasim_transfer_string_table_shadow_enabled_runtime() ? 1 : 0) << endl;
    cerr << "benchmark.fasim_transfer_string_table_shadow_calls=" << stats.transferStringProfile.tableShadowCalls << endl;
    cerr << "benchmark.fasim_transfer_string_table_shadow_compared_calls=" << stats.transferStringProfile.tableShadowComparedCalls << endl;
    cerr << "benchmark.fasim_transfer_string_table_shadow_mismatches=" << stats.transferStringProfile.tableShadowMismatches << endl;
    cerr << "benchmark.fasim_transfer_string_table_shadow_fallbacks=" << stats.transferStringProfile.tableShadowFallbacks << endl;
    cerr << "benchmark.fasim_transfer_string_table_shadow_seconds=" << fasim_profile_seconds(stats.transferStringProfile.tableShadowNanoseconds) << endl;
    cerr << "benchmark.fasim_transfer_string_table_shadow_input_bases=" << stats.transferStringProfile.tableShadowInputBases << endl;
    cerr << "benchmark.fasim_transfer_string_table_requested=" << (fasim_transfer_string_table_requested_runtime() ? 1 : 0) << endl;
    cerr << "benchmark.fasim_transfer_string_table_active=" << (fasim_transfer_string_table_requested_runtime() ? 1 : 0) << endl;
    cerr << "benchmark.fasim_transfer_string_table_validate_enabled=" << (fasim_transfer_string_table_validate_enabled_runtime() ? 1 : 0) << endl;
    cerr << "benchmark.fasim_transfer_string_table_calls=" << stats.transferStringProfile.tableCalls << endl;
    cerr << "benchmark.fasim_transfer_string_table_seconds=" << fasim_profile_seconds(stats.transferStringProfile.tableNanoseconds) << endl;
    cerr << "benchmark.fasim_transfer_string_table_legacy_validate_seconds=" << fasim_profile_seconds(stats.transferStringProfile.tableLegacyValidateNanoseconds) << endl;
    cerr << "benchmark.fasim_transfer_string_table_compared=" << stats.transferStringProfile.tableComparedCalls << endl;
    cerr << "benchmark.fasim_transfer_string_table_mismatches=" << stats.transferStringProfile.tableMismatches << endl;
    cerr << "benchmark.fasim_transfer_string_table_fallbacks=" << stats.transferStringProfile.tableFallbacks << endl;
    cerr << "benchmark.fasim_transfer_string_table_bases_converted=" << stats.transferStringProfile.tableBasesConverted << endl;
    cerr << "benchmark.fasim_transfer_string_para_forward_calls=" << stats.transferStringProfile.modeCalls[0] << endl;
    cerr << "benchmark.fasim_transfer_string_para_forward_seconds=" << fasim_profile_seconds(stats.transferStringProfile.modeNanoseconds[0]) << endl;
    cerr << "benchmark.fasim_transfer_string_para_reverse_calls=" << stats.transferStringProfile.modeCalls[1] << endl;
    cerr << "benchmark.fasim_transfer_string_para_reverse_seconds=" << fasim_profile_seconds(stats.transferStringProfile.modeNanoseconds[1]) << endl;
    cerr << "benchmark.fasim_transfer_string_anti_forward_calls=" << stats.transferStringProfile.modeCalls[2] << endl;
    cerr << "benchmark.fasim_transfer_string_anti_forward_seconds=" << fasim_profile_seconds(stats.transferStringProfile.modeNanoseconds[2]) << endl;
    cerr << "benchmark.fasim_transfer_string_anti_reverse_calls=" << stats.transferStringProfile.modeCalls[3] << endl;
    cerr << "benchmark.fasim_transfer_string_anti_reverse_seconds=" << fasim_profile_seconds(stats.transferStringProfile.modeNanoseconds[3]) << endl;
    for (int rule = 1; rule <= 18; ++rule)
    {
        cerr << "benchmark.fasim_transfer_string_rule_" << rule << "_calls=" << stats.transferStringProfile.ruleCalls[rule] << endl;
        cerr << "benchmark.fasim_transfer_string_rule_" << rule << "_seconds=" << fasim_profile_seconds(stats.transferStringProfile.ruleNanoseconds[rule]) << endl;
    }
    cerr << "benchmark.fasim_dp_scoring_seconds=" << fasim_profile_seconds(stats.dpScoringNanoseconds) << endl;
    cerr << "benchmark.fasim_column_max_seconds=" << fasim_profile_seconds(stats.columnMaxNanoseconds) << endl;
    cerr << "benchmark.fasim_local_max_seconds=" << fasim_profile_seconds(stats.localMaxNanoseconds) << endl;
    cerr << "benchmark.fasim_nonoverlap_seconds=" << fasim_profile_seconds(stats.nonoverlapNanoseconds) << endl;
    cerr << "benchmark.fasim_validation_seconds=" << fasim_profile_seconds(stats.validationNanoseconds) << endl;
    cerr << "benchmark.fasim_output_seconds=" << fasim_profile_seconds(stats.outputNanoseconds) << endl;
    cerr << "benchmark.fasim_num_queries=" << stats.numQueries << endl;
    cerr << "benchmark.fasim_num_windows=" << stats.numWindows << endl;
    cerr << "benchmark.fasim_num_dp_cells=" << stats.numDpCells << endl;
    cerr << "benchmark.fasim_num_candidates=" << stats.numCandidates << endl;
    cerr << "benchmark.fasim_num_validated_candidates=" << stats.numValidatedCandidates << endl;
    cerr << "benchmark.fasim_num_final_hits=" << stats.numFinalHits << endl;
    cerr << "benchmark.fasim_gpu_dp_column_requested=" << (fasim_gpu_dp_column_requested_runtime() ? 1 : 0) << endl;
    cerr << "benchmark.fasim_gpu_dp_column_active=" << stats.gpuDpColumnActive << endl;
    cerr << "benchmark.fasim_gpu_dp_column_validate_enabled=" << (fasim_gpu_dp_column_validate_enabled_runtime() ? 1 : 0) << endl;
    cerr << "benchmark.fasim_gpu_dp_column_calls=" << stats.gpuDpColumnCalls << endl;
    cerr << "benchmark.fasim_gpu_dp_column_windows=" << stats.gpuDpColumnWindows << endl;
    cerr << "benchmark.fasim_gpu_dp_column_cells=" << stats.gpuDpColumnCells << endl;
    cerr << "benchmark.fasim_gpu_dp_column_h2d_bytes=" << stats.gpuDpColumnH2DBytes << endl;
    cerr << "benchmark.fasim_gpu_dp_column_d2h_bytes=" << stats.gpuDpColumnD2HBytes << endl;
    cerr << "benchmark.fasim_gpu_dp_column_kernel_seconds=" << fasim_profile_seconds(stats.gpuDpColumnKernelNanoseconds) << endl;
    cerr << "benchmark.fasim_gpu_dp_column_total_seconds=" << fasim_profile_seconds(stats.gpuDpColumnTotalNanoseconds) << endl;
    cerr << "benchmark.fasim_gpu_dp_column_validate_seconds=" << fasim_profile_seconds(stats.gpuDpColumnValidateNanoseconds) << endl;
    cerr << "benchmark.fasim_gpu_dp_column_topk_cap=" << stats.gpuDpColumnTopKCap << endl;
    cerr << "benchmark.fasim_gpu_dp_column_score_mismatches=" << stats.gpuDpColumnScoreMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_column_max_mismatches=" << stats.gpuDpColumnColumnMaxMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_fallbacks=" << stats.gpuDpColumnFallbacks << endl;
    cerr << "benchmark.fasim_gpu_dp_column_debug_enabled=" << (fasim_gpu_dp_column_mismatch_debug_enabled_runtime() ? 1 : 0) << endl;
    cerr << "benchmark.fasim_gpu_dp_column_first_mismatch_window=" << stats.gpuDpColumnFirstMismatchWindow << endl;
    cerr << "benchmark.fasim_gpu_dp_column_first_mismatch_column=" << stats.gpuDpColumnFirstMismatchColumn << endl;
    cerr << "benchmark.fasim_gpu_dp_column_first_mismatch_cpu_score=" << stats.gpuDpColumnFirstMismatchCpuScore << endl;
    cerr << "benchmark.fasim_gpu_dp_column_first_mismatch_gpu_score=" << stats.gpuDpColumnFirstMismatchGpuScore << endl;
    cerr << "benchmark.fasim_gpu_dp_column_first_mismatch_cpu_position=" << stats.gpuDpColumnFirstMismatchCpuPosition << endl;
    cerr << "benchmark.fasim_gpu_dp_column_first_mismatch_gpu_position=" << stats.gpuDpColumnFirstMismatchGpuPosition << endl;
    cerr << "benchmark.fasim_gpu_dp_column_first_mismatch_cpu_count=" << stats.gpuDpColumnFirstMismatchCpuCount << endl;
    cerr << "benchmark.fasim_gpu_dp_column_first_mismatch_gpu_count=" << stats.gpuDpColumnFirstMismatchGpuCount << endl;
    cerr << "benchmark.fasim_gpu_dp_column_first_mismatch_tie=" << stats.gpuDpColumnFirstMismatchTie << endl;
    cerr << "benchmark.fasim_gpu_dp_column_cpu_scoreinfo_score=" << stats.gpuDpColumnFirstMismatchCpuScore << endl;
    cerr << "benchmark.fasim_gpu_dp_column_gpu_scoreinfo_score=" << stats.gpuDpColumnFirstMismatchGpuScore << endl;
    cerr << "benchmark.fasim_gpu_dp_column_cpu_scoreinfo_position=" << stats.gpuDpColumnFirstMismatchCpuPosition << endl;
    cerr << "benchmark.fasim_gpu_dp_column_gpu_scoreinfo_position=" << stats.gpuDpColumnFirstMismatchGpuPosition << endl;
    cerr << "benchmark.fasim_gpu_dp_column_scoreinfo_field_mismatch_mask=" << stats.gpuDpColumnScoreInfoFieldMismatchMask << endl;
    cerr << "benchmark.fasim_gpu_dp_column_score_delta_max=" << stats.gpuDpColumnScoreDeltaMax << endl;
    cerr << "benchmark.fasim_gpu_dp_column_scoreinfo_mismatches=" << stats.gpuDpColumnScoreInfoMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_tie_mismatches=" << stats.gpuDpColumnTieMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_position_mismatches=" << stats.gpuDpColumnPositionMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_topk_truncated_windows=" << stats.gpuDpColumnTopKTruncatedWindows << endl;
    cerr << "benchmark.fasim_gpu_dp_column_topk_overflow_windows=" << stats.gpuDpColumnTopKOverflowWindows << endl;
    cerr << "benchmark.fasim_gpu_dp_column_pre_topk_mismatches=" << stats.gpuDpColumnPreTopKMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_mismatches=" << stats.gpuDpColumnPostTopKMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_debug_windows_examined=" << stats.gpuDpColumnDebugWindowsExamined << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_enabled=" << (fasim_gpu_dp_column_full_scoreinfo_debug_enabled_runtime() ? 1 : 0) << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_window_index=" << stats.gpuDpColumnFullDebugWindowIndex << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_cpu_records=" << stats.gpuDpColumnFullDebugCpuRecords << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_gpu_pre_topk_records=" << stats.gpuDpColumnFullDebugGpuPreTopKRecords << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_gpu_post_topk_records=" << stats.gpuDpColumnFullDebugGpuPostTopKRecords << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_cpu_record_missing_pre_topk=" << stats.gpuDpColumnFullDebugCpuRecordMissingPreTopK << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_cpu_record_missing_post_topk=" << stats.gpuDpColumnFullDebugCpuRecordMissingPostTopK << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_first_mismatch_rank=" << stats.gpuDpColumnFullDebugFirstMismatchRank << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_first_mismatch_score_delta=" << stats.gpuDpColumnFullDebugFirstMismatchScoreDelta << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_first_mismatch_position_delta=" << stats.gpuDpColumnFullDebugFirstMismatchPositionDelta << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_first_mismatch_count_delta=" << stats.gpuDpColumnFullDebugFirstMismatchCountDelta << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_scoreinfo_set_mismatches=" << stats.gpuDpColumnFullDebugScoreInfoSetMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_scoreinfo_field_mismatches=" << stats.gpuDpColumnFullDebugScoreInfoFieldMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_column_mismatches=" << stats.gpuDpColumnFullDebugColumnMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_full_debug_column_score_delta_max=" << stats.gpuDpColumnFullDebugColumnScoreDeltaMax << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_pack_shadow_enabled=" << (fasim_gpu_dp_column_post_topk_pack_shadow_enabled_runtime() ? 1 : 0) << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_cpu_records=" << stats.gpuDpColumnPostTopKCpuRecords << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_gpu_pre_records=" << stats.gpuDpColumnPostTopKGpuPreRecords << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_gpu_post_records=" << stats.gpuDpColumnPostTopKGpuPostRecords << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_cpu_pack_mismatches=" << stats.gpuDpColumnPostTopKCpuPackMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_gpu_pack_mismatches=" << stats.gpuDpColumnPostTopKGpuPackMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_missing_records=" << stats.gpuDpColumnPostTopKMissingRecords << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_extra_records=" << stats.gpuDpColumnPostTopKExtraRecords << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_rank_mismatches=" << stats.gpuDpColumnPostTopKRankMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_field_mismatch_mask=" << stats.gpuDpColumnPostTopKFieldMismatchMask << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_count_mismatches=" << stats.gpuDpColumnPostTopKCountMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_position_mismatches=" << stats.gpuDpColumnPostTopKPositionMismatches << endl;
    cerr << "benchmark.fasim_gpu_dp_column_post_topk_score_mismatches=" << stats.gpuDpColumnPostTopKScoreMismatches << endl;
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

static inline void fasim_apply_src_transform(const std::string &seq1, FasimSrcTransform transform, std::string &out)
{
    out = seq1;
    switch (transform)
    {
    case FASIM_SRC_ORIG:
        return;
    case FASIM_SRC_COMP:
        complement(out);
        return;
    case FASIM_SRC_REV:
        reverseSeq(out);
        return;
    case FASIM_SRC_REVCOMP:
        complement(out);
        reverseSeq(out);
        return;
    default:
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
	const bool profileEnabled = fasim_profile_enabled_runtime();
	const uint64_t profileTotalStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
	FasimProfileStats profileStats;
    if(paraList.doFastSim==true)
    cout<<"Searching triplexes using Fasim"<<endl;
    else
    cout<<"Searching triplexes using Sim"<<endl;
    core_num = paraList.corenum;

	uint64_t profileStageStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
	lncSeq = readRna(paraList.file2path, lncName);
	if (profileEnabled)
	{
		fasim_profile_add_elapsed(profileStats.ioNanoseconds, profileStageStart);
		profileStats.numQueries = lncSeq.empty() ? 0 : 1;
	}
	fileName = fasim_strip_fasta_extension(fasim_basename(paraList.file1path));
	lncName.erase(remove(lncName.begin(), lncName.end(), '\r'), lncName.end());
	lncName.erase(remove(lncName.begin(), lncName.end(), '\n'), lncName.end());
	resultDir = paraList.outpath;

	const FasimOutputMode outputMode = fasim_output_mode_runtime();
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
			StreamTask() : recordStartGenome(1), dnaStartPos(0), strand(0), Para(0), rule(0) {}
			std::string srcSeq;
			std::string seq2;
			std::string chr;
			long recordStartGenome;
			long dnaStartPos;
			long strand;
			long Para;
			int rule;
		};

		ofstream outFile;
		ofstream outLiteFile;
		string outFilePath;
		string outLiteFilePath;
		string outSpecies;
		bool outOpened = false;
		std::mutex outMutex;
		const bool writeFull = outputMode == FASIM_OUTPUT_TFOSORTED;
		const bool writeLite = (outputMode == FASIM_OUTPUT_LITE) || fasim_write_tfosorted_lite_enabled_runtime();

		auto ensure_output_opened = [&](const string &speciesValue)
		{
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
			outOpened = true;
		};

		const bool gpuDpColumnRequested = fasim_gpu_dp_column_requested_runtime();
		const bool gpuDpColumnValidate = fasim_gpu_dp_column_validate_enabled_runtime();
		const bool gpuDpColumnMismatchDebug = fasim_gpu_dp_column_mismatch_debug_enabled_runtime();
		const bool gpuDpColumnFullScoreInfoDebug =
			fasim_gpu_dp_column_full_scoreinfo_debug_enabled_runtime();
		const bool gpuDpColumnPostTopKPackShadow =
			fasim_gpu_dp_column_post_topk_pack_shadow_enabled_runtime();
		const int gpuDpColumnDebugMaxWindows =
			fasim_env_int_or_default_allow_zero("FASIM_GPU_DP_COLUMN_DEBUG_MAX_WINDOWS", 1);
		const int gpuDpColumnDebugWindowIndex =
			fasim_env_int_or_default_allow_zero("FASIM_GPU_DP_COLUMN_DEBUG_WINDOW_INDEX", -1);
		const int gpuDpColumnDebugMaxRecords =
			fasim_env_int_or_default_allow_zero("FASIM_GPU_DP_COLUMN_DEBUG_MAX_RECORDS", 5);
		bool useCudaBatch = false;
		std::vector<int> cudaDevices;
		std::vector<PreAlignCudaQueryHandle> cudaQueries;
		std::vector<int16_t> queryProfile;
		int cachedSegLen = 0;
		if (paraList.doFastSim &&
		    (fasim_prealign_cuda_enabled_runtime() || gpuDpColumnRequested) &&
		    prealign_cuda_is_built())
		{
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
			useCudaBatch = !cudaQueries.empty();
			if (profileEnabled && gpuDpColumnRequested && useCudaBatch)
			{
				profileStats.gpuDpColumnActive = 1;
			}
		}

		const int maxTasksPerGpu = fasim_env_int_or_default("FASIM_PREALIGN_CUDA_MAX_TASKS", 4096);
		int maxTasksTotal = useCudaBatch ? (maxTasksPerGpu * static_cast<int>(cudaQueries.size())) : 1;
		if (maxTasksTotal <= 0)
		{
			maxTasksTotal = 1;
		}
		const int extendThreadCount = fasim_extend_threads_runtime(paraList.corenum);
		const int topKDefault = gpuDpColumnRequested ? 256 : 64;
		int topK = fasim_env_int_or_default("FASIM_PREALIGN_CUDA_TOPK", topKDefault);
		if (gpuDpColumnRequested)
		{
			topK = fasim_env_int_or_default("FASIM_GPU_DP_COLUMN_TOPK_CAP", topK);
		}
		if (topK > 256)
		{
			topK = 256;
		}
		if (topK <= 0)
		{
			topK = topKDefault;
		}
		if (profileEnabled)
		{
			profileStats.gpuDpColumnTopKCap =
				gpuDpColumnRequested ? static_cast<uint64_t>(topK) : 0;
		}

		const bool debugCuda = getenv("FASIM_DEBUG_CUDA_PREALIGN") != NULL &&
		                       getenv("FASIM_DEBUG_CUDA_PREALIGN")[0] != '\0' &&
		                       getenv("FASIM_DEBUG_CUDA_PREALIGN")[0] != '0';

		StripedSmithWaterman::Aligner aligner;
		StripedSmithWaterman::Filter filter;
		StripedSmithWaterman::Alignment alignment;
		std::vector<struct StripedSmithWaterman::scoreInfo> finalScoreInfo;
		finalScoreInfo.reserve(static_cast<size_t>(topK));

		std::vector<triplex> taskTriplexes;
		taskTriplexes.reserve(64);

		std::vector<StreamTask> tasks;
		std::vector<uint8_t> encodedTargets;
		int currentTargetLength = -1;

		auto record_gpu_dp_column_batch = [&](size_t taskCount,
		                                      int targetLength,
		                                      size_t peakCount,
		                                      const PreAlignCudaBatchResult &batchResult,
		                                      uint64_t totalStart)
		{
			if (!profileEnabled || !gpuDpColumnRequested)
			{
				return;
			}
			++profileStats.gpuDpColumnCalls;
			profileStats.gpuDpColumnWindows += static_cast<uint64_t>(taskCount);
			const uint64_t cells =
				static_cast<uint64_t>(taskCount) *
				static_cast<uint64_t>(targetLength > 0 ? targetLength : 0) *
				static_cast<uint64_t>(lncSeq.size());
			profileStats.gpuDpColumnCells += cells;
			profileStats.numDpCells += cells;
			profileStats.gpuDpColumnH2DBytes +=
				static_cast<uint64_t>(taskCount) *
				static_cast<uint64_t>(targetLength > 0 ? targetLength : 0) *
				static_cast<uint64_t>(sizeof(uint8_t));
			profileStats.gpuDpColumnD2HBytes +=
				static_cast<uint64_t>(peakCount) *
				static_cast<uint64_t>(sizeof(PreAlignCudaPeak));
			profileStats.gpuDpColumnKernelNanoseconds +=
				fasim_profile_nanoseconds_from_seconds(batchResult.gpuSeconds);
			profileStats.gpuDpColumnTotalNanoseconds +=
				fasim_profile_now_nanoseconds() - totalStart;
		};

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
					candidates.push_back(StripedSmithWaterman::scoreInfo(columnScores[i],
					                                                      static_cast<int>(i)));
				}
			}
			build_scoreinfo_from_candidates(candidates, outScoreInfo);
		};

		auto build_scoreinfo_from_gpu_exact_columns = [&](
			const PreAlignCudaQueryHandle &query,
			const uint8_t *encodedTarget,
			int targetLength,
			int *maxScoreOut,
			std::vector<struct StripedSmithWaterman::scoreInfo> &outScoreInfo,
			std::vector<int> *columnScoresOut,
			const char *context)
		{
			std::vector<int> columnScores;
			PreAlignCudaBatchResult columnResult;
			string columnError;
			if (!prealign_cuda_find_column_maxima_debug(query,
			                                            encodedTarget,
			                                            targetLength,
			                                            &columnScores,
			                                            &columnResult,
			                                            &columnError))
			{
				if (debugCuda)
				{
					cerr << "[fasim.cuda.exact_scoreinfo] error"
					     << " context=" << context
					     << " error=" << columnError
					     << endl;
				}
				outScoreInfo.clear();
				if (maxScoreOut != NULL)
				{
					*maxScoreOut = 0;
				}
				return false;
			}

			int maxScore = 0;
			for (size_t i = 0; i < columnScores.size(); ++i)
			{
				if (columnScores[i] > maxScore)
				{
					maxScore = columnScores[i];
				}
			}
			const int minScore = static_cast<int>(static_cast<double>(maxScore) * 0.8);
			build_scoreinfo_from_column_scores(columnScores, minScore, outScoreInfo);
			if (maxScoreOut != NULL)
			{
				*maxScoreOut = maxScore;
			}
			if (columnScoresOut != NULL)
			{
				columnScoresOut->swap(columnScores);
			}
			return true;
		};

		auto scoreinfo_equal = [](const std::vector<struct StripedSmithWaterman::scoreInfo> &a,
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

		auto scoreinfo_contains_exact = [](
			const std::vector<struct StripedSmithWaterman::scoreInfo> &items,
			const StripedSmithWaterman::scoreInfo &needle)
		{
			for (size_t i = 0; i < items.size(); ++i)
			{
				if (items[i].score == needle.score && items[i].position == needle.position)
				{
					return true;
				}
			}
			return false;
		};

		auto scoreinfo_missing_from = [&](
			const std::vector<struct StripedSmithWaterman::scoreInfo> &expected,
			const std::vector<struct StripedSmithWaterman::scoreInfo> &observed)
		{
			uint64_t missing = 0;
			for (size_t i = 0; i < expected.size(); ++i)
			{
				if (!scoreinfo_contains_exact(observed, expected[i]))
				{
					++missing;
				}
			}
			return missing;
		};

		auto scoreinfo_first_diff_rank = [](
			const std::vector<struct StripedSmithWaterman::scoreInfo> &a,
			const std::vector<struct StripedSmithWaterman::scoreInfo> &b)
		{
			const size_t maxCount = std::max(a.size(), b.size());
			for (size_t i = 0; i < maxCount; ++i)
			{
				const bool hasA = i < a.size();
				const bool hasB = i < b.size();
				if (!hasA || !hasB)
				{
					return static_cast<long long>(i);
				}
				if (a[i].score != b[i].score || a[i].position != b[i].position)
				{
					return static_cast<long long>(i);
				}
			}
			return static_cast<long long>(-1);
		};

		auto scoreinfo_rank_mismatches = [](
			const std::vector<struct StripedSmithWaterman::scoreInfo> &expected,
			const std::vector<struct StripedSmithWaterman::scoreInfo> &observed)
		{
			uint64_t mismatches = 0;
			const size_t maxCount = std::max(expected.size(), observed.size());
			for (size_t i = 0; i < maxCount; ++i)
			{
				const bool hasExpected = i < expected.size();
				const bool hasObserved = i < observed.size();
				if (!hasExpected || !hasObserved)
				{
					++mismatches;
					continue;
				}
				if (expected[i].score != observed[i].score ||
				    expected[i].position != observed[i].position)
				{
					++mismatches;
				}
			}
			return mismatches;
		};

		size_t gpuDpColumnValidationWindowOrdinal = 0;
		uint64_t gpuDpColumnDebugPrintedWindows = 0;
		bool gpuDpColumnFullDebugRecorded = false;

		auto validate_gpu_dp_column_task = [&](const StreamTask &task,
		                                       const PreAlignCudaPeak *taskPeaks,
		                                       const PreAlignCudaQueryHandle *debugQuery,
		                                       const uint8_t *debugEncodedTarget,
		                                       int debugTargetLength)
		{
			if (!gpuDpColumnValidate)
			{
				return true;
			}
			const size_t validationWindowOrdinal = gpuDpColumnValidationWindowOrdinal++;
			const uint64_t validateStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
			bool ok = true;
			bool scoreMismatch = false;
			bool topKOverflow = false;
			bool topKTruncated = false;
			int firstColumnMismatch = -1;
			int firstCpuScore = 0;
			int firstGpuScore = 0;
			int firstCpuPosition = -1;
			int firstGpuPosition = -1;
			bool firstTieMismatch = false;

			auto update_score_delta = [&](int cpuScore, int gpuScore)
			{
				if (!profileEnabled || !gpuDpColumnRequested || !gpuDpColumnMismatchDebug)
				{
					return;
				}
				const uint64_t delta = static_cast<uint64_t>(abs(cpuScore - gpuScore));
				if (delta > profileStats.gpuDpColumnScoreDeltaMax)
				{
					profileStats.gpuDpColumnScoreDeltaMax = delta;
				}
			};

			auto record_first_mismatch = [&](int columnIndex,
			                                 int cpuScore,
			                                 int gpuScore,
			                                 int cpuPosition,
			                                 int gpuPosition,
			                                 size_t cpuCount,
			                                 size_t gpuCount,
			                                 bool tieMismatch,
			                                 uint64_t scoreInfoFieldMismatchMask)
			{
				if (!profileEnabled || !gpuDpColumnRequested || !gpuDpColumnMismatchDebug)
				{
					return;
				}
				if (profileStats.gpuDpColumnFirstMismatchWindow >= 0)
				{
					return;
				}
				profileStats.gpuDpColumnFirstMismatchWindow =
					static_cast<long long>(validationWindowOrdinal);
				profileStats.gpuDpColumnFirstMismatchColumn =
					static_cast<long long>(columnIndex);
				profileStats.gpuDpColumnFirstMismatchCpuScore = cpuScore;
				profileStats.gpuDpColumnFirstMismatchGpuScore = gpuScore;
				profileStats.gpuDpColumnFirstMismatchCpuPosition = cpuPosition;
				profileStats.gpuDpColumnFirstMismatchGpuPosition = gpuPosition;
				profileStats.gpuDpColumnFirstMismatchCpuCount = static_cast<uint64_t>(cpuCount);
				profileStats.gpuDpColumnFirstMismatchGpuCount = static_cast<uint64_t>(gpuCount);
				profileStats.gpuDpColumnFirstMismatchTie = tieMismatch ? 1 : 0;
				profileStats.gpuDpColumnScoreInfoFieldMismatchMask = scoreInfoFieldMismatchMask;
			};

			if (profileEnabled && gpuDpColumnRequested && gpuDpColumnMismatchDebug)
			{
				++profileStats.gpuDpColumnDebugWindowsExamined;
			}

			string cpuQuery = lncSeq;
			string cpuTarget = task.seq2;
			const int cpuMaxScore = calc_score_once(cpuQuery, cpuTarget, task.dnaStartPos, paraList.rule);
			int gpuMaxScore = taskPeaks[0].score;
			std::vector<struct StripedSmithWaterman::scoreInfo> gpuScoreInfo;
			std::vector<struct StripedSmithWaterman::scoreInfo> cpuScoreInfo;
			std::vector<int> gpuExactColumnScores;
			const bool needExactColumnScores =
				gpuDpColumnFullScoreInfoDebug || gpuDpColumnPostTopKPackShadow;
			bool gpuScoreInfoFromExactColumns = false;
			if (gpuDpColumnRequested)
			{
				if (debugQuery == NULL || debugEncodedTarget == NULL ||
				    !build_scoreinfo_from_gpu_exact_columns(*debugQuery,
				                                            debugEncodedTarget,
				                                            debugTargetLength,
				                                            &gpuMaxScore,
				                                            gpuScoreInfo,
				                                            needExactColumnScores ? &gpuExactColumnScores : NULL,
				                                            "validate"))
				{
					if (profileEnabled)
					{
						fasim_profile_add_elapsed(profileStats.gpuDpColumnValidateNanoseconds,
						                          validateStart);
					}
					return false;
				}
				gpuScoreInfoFromExactColumns = true;
			}
			if (cpuMaxScore != gpuMaxScore)
			{
				ok = false;
				scoreMismatch = true;
				update_score_delta(cpuMaxScore, gpuMaxScore);
				if (profileEnabled && gpuDpColumnRequested)
				{
					++profileStats.gpuDpColumnScoreMismatches;
				}
				if (profileEnabled && gpuDpColumnRequested && gpuDpColumnMismatchDebug)
				{
					++profileStats.gpuDpColumnPreTopKMismatches;
					record_first_mismatch(-1,
					                      cpuMaxScore,
					                      gpuMaxScore,
					                      -1,
					                      -1,
					                      0,
					                      0,
					                      false,
					                      0);
				}
			}

			const int minScore = static_cast<int>(static_cast<double>(gpuMaxScore) * 0.8);
			if (!gpuScoreInfoFromExactColumns)
			{
				build_scoreinfo_from_gpu_peaks(taskPeaks, minScore, gpuScoreInfo);
			}
			if (topK > 0)
			{
				const PreAlignCudaPeak &lastPeak = taskPeaks[static_cast<size_t>(topK - 1)];
				topKOverflow = lastPeak.position >= 0 && lastPeak.score > minScore;
				if (topKOverflow && profileEnabled && gpuDpColumnRequested && gpuDpColumnMismatchDebug)
				{
					++profileStats.gpuDpColumnTopKOverflowWindows;
				}
			}
			StripedSmithWaterman::Aligner cpuAligner;
			StripedSmithWaterman::Filter cpuFilter;
			StripedSmithWaterman::Alignment cpuAlignment;
			std::vector<int> cpuColumnScores;
			std::vector<int> *cpuColumnScoresOut =
				needExactColumnScores ? &cpuColumnScores : NULL;
			cpuAligner.preAlign(lncSeq.c_str(),
			                    task.seq2.c_str(),
			                    static_cast<int>(task.seq2.size()),
			                    cpuFilter,
			                    &cpuAlignment,
			                    15,
			                    minScore,
			                    cpuScoreInfo,
			                    5,
			                    -4,
			                    cpuColumnScoresOut);
			const bool gpuScoreInfoMatchesCpu = scoreinfo_equal(gpuScoreInfo, cpuScoreInfo);
			if (!gpuScoreInfoMatchesCpu)
			{
				ok = false;
				if (profileEnabled && gpuDpColumnRequested && gpuDpColumnMismatchDebug)
				{
					++profileStats.gpuDpColumnScoreInfoMismatches;
					if (!scoreMismatch)
					{
						++profileStats.gpuDpColumnPostTopKMismatches;
					}
					topKTruncated = topKOverflow && cpuScoreInfo.size() > gpuScoreInfo.size();
					if (topKTruncated)
					{
						++profileStats.gpuDpColumnTopKTruncatedWindows;
					}

					const size_t maxCount = std::max(gpuScoreInfo.size(), cpuScoreInfo.size());
					for (size_t i = 0; i < maxCount; ++i)
					{
						const bool hasGpu = i < gpuScoreInfo.size();
						const bool hasCpu = i < cpuScoreInfo.size();
						const int gpuScore = hasGpu ? gpuScoreInfo[i].score : 0;
						const int cpuScore = hasCpu ? cpuScoreInfo[i].score : 0;
						const int gpuPosition = hasGpu ? gpuScoreInfo[i].position : -1;
						const int cpuPosition = hasCpu ? cpuScoreInfo[i].position : -1;
						if (!hasGpu || !hasCpu ||
						    gpuScore != cpuScore ||
						    gpuPosition != cpuPosition)
						{
							uint64_t fieldMismatchMask = 0;
							if (gpuScore != cpuScore)
							{
								fieldMismatchMask |= 1;
							}
							if (gpuPosition != cpuPosition)
							{
								fieldMismatchMask |= 2;
							}
							if (gpuScoreInfo.size() != cpuScoreInfo.size())
							{
								fieldMismatchMask |= 4;
							}
							if (!hasGpu || !hasCpu)
							{
								fieldMismatchMask |= 8;
							}
							firstColumnMismatch = static_cast<int>(i);
							firstCpuScore = cpuScore;
							firstGpuScore = gpuScore;
							firstCpuPosition = cpuPosition;
							firstGpuPosition = gpuPosition;
							firstTieMismatch = hasGpu && hasCpu &&
							                   gpuScore == cpuScore &&
							                   gpuPosition != cpuPosition;
							update_score_delta(cpuScore, gpuScore);
							if (!hasGpu || !hasCpu || gpuPosition != cpuPosition)
							{
								++profileStats.gpuDpColumnPositionMismatches;
							}
							if (firstTieMismatch)
							{
								++profileStats.gpuDpColumnTieMismatches;
							}
							record_first_mismatch(firstColumnMismatch,
							                      firstCpuScore,
							                      firstGpuScore,
							                      firstCpuPosition,
							                      firstGpuPosition,
							                      cpuScoreInfo.size(),
							                      gpuScoreInfo.size(),
							                      firstTieMismatch,
							                      fieldMismatchMask);
							break;
						}
					}
				}

				const bool debugWindowSelected =
					gpuDpColumnMismatchDebug &&
					(gpuDpColumnDebugWindowIndex < 0 ||
					 static_cast<int>(validationWindowOrdinal) == gpuDpColumnDebugWindowIndex);
				const bool debugPrintAllowed =
					debugWindowSelected &&
					(gpuDpColumnDebugMaxWindows <= 0 ||
					 gpuDpColumnDebugPrintedWindows < static_cast<uint64_t>(gpuDpColumnDebugMaxWindows));
				if (debugCuda || debugPrintAllowed)
				{
					if (debugPrintAllowed)
					{
						++gpuDpColumnDebugPrintedWindows;
					}
					cerr << "[fasim.cuda.validate] column mismatch"
					     << " window=" << validationWindowOrdinal
					     << " gpu_count=" << gpuScoreInfo.size()
					     << " cpu_count=" << cpuScoreInfo.size()
					     << " first_column=" << firstColumnMismatch
					     << " topKOverflow=" << (topKOverflow ? 1 : 0)
					     << " topKTruncated=" << (topKTruncated ? 1 : 0)
					     << " preTopK=" << (scoreMismatch ? 1 : 0)
					     << " postTopK=" << (!scoreMismatch ? 1 : 0)
					     << " minScore=" << minScore
					     << " gpuMaxScore=" << gpuMaxScore
					     << " cpuMaxScore=" << cpuMaxScore
					     << endl;
					const size_t maxCount = std::max(gpuScoreInfo.size(), cpuScoreInfo.size());
					const size_t sampleBegin =
						firstColumnMismatch > 2 ? static_cast<size_t>(firstColumnMismatch - 2) : 0;
					const size_t sampleEnd = std::min(maxCount, sampleBegin + 5);
					for (size_t i = sampleBegin; i < sampleEnd; ++i)
					{
						cerr << "[fasim.cuda.validate] idx=" << i;
						if (i < gpuScoreInfo.size())
						{
							cerr << " gpu=(" << gpuScoreInfo[i].score << "," << gpuScoreInfo[i].position << ")";
						}
						else
						{
							cerr << " gpu=(none)";
						}
						if (i < cpuScoreInfo.size())
						{
							cerr << " cpu=(" << cpuScoreInfo[i].score << "," << cpuScoreInfo[i].position << ")";
						}
						else
						{
							cerr << " cpu=(none)";
						}
						cerr << endl;
					}
				}
				const bool fullDebugWindowSelected =
					(gpuDpColumnFullScoreInfoDebug || gpuDpColumnPostTopKPackShadow) &&
					gpuDpColumnMismatchDebug &&
					!gpuDpColumnFullDebugRecorded &&
					(gpuDpColumnDebugWindowIndex < 0 ||
					 static_cast<int>(validationWindowOrdinal) == gpuDpColumnDebugWindowIndex);
				if (fullDebugWindowSelected)
				{
					gpuDpColumnFullDebugRecorded = true;
					if (profileEnabled && gpuDpColumnRequested)
					{
						profileStats.gpuDpColumnFullDebugWindowIndex =
							static_cast<long long>(validationWindowOrdinal);
						profileStats.gpuDpColumnFullDebugCpuRecords =
							static_cast<uint64_t>(cpuScoreInfo.size());
						profileStats.gpuDpColumnFullDebugGpuPostTopKRecords =
							static_cast<uint64_t>(gpuScoreInfo.size());
					}

					std::vector<int> gpuColumnScores;
					PreAlignCudaBatchResult debugBatchResult;
					string fullDebugError;
					const bool fullDebugOk =
						debugQuery != NULL &&
						debugEncodedTarget != NULL &&
						prealign_cuda_find_column_maxima_debug(*debugQuery,
						                                       debugEncodedTarget,
						                                       debugTargetLength,
						                                       &gpuColumnScores,
						                                       &debugBatchResult,
						                                       &fullDebugError);
					if (!fullDebugOk)
					{
						cerr << "[fasim.cuda.full_scoreinfo] debug_error"
						     << " window=" << validationWindowOrdinal
						     << " error=" << fullDebugError
						     << endl;
					}
					else
					{
						std::vector<struct StripedSmithWaterman::scoreInfo> gpuPreTopKScoreInfo;
						build_scoreinfo_from_column_scores(gpuColumnScores, minScore, gpuPreTopKScoreInfo);

						uint64_t columnMismatches = 0;
						uint64_t columnScoreDeltaMax = 0;
						const size_t columnCount = std::max(cpuColumnScores.size(), gpuColumnScores.size());
						for (size_t i = 0; i < columnCount; ++i)
						{
							const int cpuScore = i < cpuColumnScores.size() ? cpuColumnScores[i] : 0;
							const int gpuScore = i < gpuColumnScores.size() ? gpuColumnScores[i] : 0;
							if (cpuScore != gpuScore)
							{
								++columnMismatches;
								const long long delta =
									static_cast<long long>(gpuScore) - static_cast<long long>(cpuScore);
								const uint64_t absDelta = static_cast<uint64_t>(delta < 0 ? -delta : delta);
								if (absDelta > columnScoreDeltaMax)
								{
									columnScoreDeltaMax = absDelta;
								}
							}
						}

						const uint64_t cpuMissingPre =
							scoreinfo_missing_from(cpuScoreInfo, gpuPreTopKScoreInfo);
						const uint64_t preMissingCpu =
							scoreinfo_missing_from(gpuPreTopKScoreInfo, cpuScoreInfo);
						const long long firstMismatchRank =
							scoreinfo_first_diff_rank(cpuScoreInfo, gpuScoreInfo);

						uint64_t missingPreTopK = 0;
						uint64_t missingPostTopK = 0;
						long long scoreDelta = 0;
						long long positionDelta = 0;
						if (firstMismatchRank >= 0 &&
						    static_cast<size_t>(firstMismatchRank) < cpuScoreInfo.size())
						{
							const StripedSmithWaterman::scoreInfo &cpuRecord =
								cpuScoreInfo[static_cast<size_t>(firstMismatchRank)];
							missingPreTopK =
								scoreinfo_contains_exact(gpuPreTopKScoreInfo, cpuRecord) ? 0 : 1;
							missingPostTopK =
								scoreinfo_contains_exact(gpuScoreInfo, cpuRecord) ? 0 : 1;

							const bool hasGpuPost =
								static_cast<size_t>(firstMismatchRank) < gpuScoreInfo.size();
							const int gpuPostScore = hasGpuPost ?
								gpuScoreInfo[static_cast<size_t>(firstMismatchRank)].score : 0;
							const int gpuPostPosition = hasGpuPost ?
								gpuScoreInfo[static_cast<size_t>(firstMismatchRank)].position : -1;
							scoreDelta =
								static_cast<long long>(gpuPostScore) -
								static_cast<long long>(cpuRecord.score);
							positionDelta =
								static_cast<long long>(gpuPostPosition) -
								static_cast<long long>(cpuRecord.position);
						}
						const long long countDelta =
							static_cast<long long>(gpuScoreInfo.size()) -
							static_cast<long long>(cpuScoreInfo.size());
						uint64_t fieldMismatches = 0;
						if (scoreDelta != 0)
						{
							++fieldMismatches;
						}
						if (positionDelta != 0)
						{
							++fieldMismatches;
						}
						if (countDelta != 0)
						{
							++fieldMismatches;
						}

						auto scoreinfo_rank_mismatches = [](
							const std::vector<struct StripedSmithWaterman::scoreInfo> &expected,
							const std::vector<struct StripedSmithWaterman::scoreInfo> &observed)
						{
							uint64_t mismatches = 0;
							const size_t maxCount = std::max(expected.size(), observed.size());
							for (size_t i = 0; i < maxCount; ++i)
							{
								const bool hasExpected = i < expected.size();
								const bool hasObserved = i < observed.size();
								if (!hasExpected || !hasObserved)
								{
									++mismatches;
									continue;
								}
								if (expected[i].score != observed[i].score ||
								    expected[i].position != observed[i].position)
								{
									++mismatches;
								}
							}
							return mismatches;
						};

						const uint64_t cpuPackMismatches =
							scoreinfo_rank_mismatches(cpuScoreInfo, gpuPreTopKScoreInfo);
						const uint64_t gpuPackMismatches =
							scoreinfo_rank_mismatches(cpuScoreInfo, gpuScoreInfo);
						const uint64_t missingPostRecords =
							scoreinfo_missing_from(cpuScoreInfo, gpuScoreInfo);
						const uint64_t extraPostRecords =
							scoreinfo_missing_from(gpuScoreInfo, cpuScoreInfo);
						uint64_t postTopKFieldMask = 0;
						uint64_t postTopKCountMismatches = 0;
						uint64_t postTopKPositionMismatches = 0;
						uint64_t postTopKScoreMismatches = 0;
						if (cpuScoreInfo.size() != gpuScoreInfo.size())
						{
							postTopKFieldMask |= 4;
							postTopKCountMismatches = 1;
						}
						if (missingPostRecords != 0 || extraPostRecords != 0)
						{
							postTopKFieldMask |= 8;
						}
						const size_t rankCompareCount = std::max(cpuScoreInfo.size(), gpuScoreInfo.size());
						for (size_t i = 0; i < rankCompareCount; ++i)
						{
							const bool hasCpu = i < cpuScoreInfo.size();
							const bool hasGpu = i < gpuScoreInfo.size();
							const int cpuScore = hasCpu ? cpuScoreInfo[i].score : 0;
							const int gpuScore = hasGpu ? gpuScoreInfo[i].score : 0;
							const int cpuPosition = hasCpu ? cpuScoreInfo[i].position : -1;
							const int gpuPosition = hasGpu ? gpuScoreInfo[i].position : -1;
							if (cpuScore != gpuScore)
							{
								postTopKFieldMask |= 1;
								++postTopKScoreMismatches;
							}
							if (cpuPosition != gpuPosition)
							{
								postTopKFieldMask |= 2;
								++postTopKPositionMismatches;
							}
						}

						if (profileEnabled && gpuDpColumnRequested)
						{
							profileStats.gpuDpColumnFullDebugGpuPreTopKRecords =
								static_cast<uint64_t>(gpuPreTopKScoreInfo.size());
							profileStats.gpuDpColumnFullDebugCpuRecordMissingPreTopK = missingPreTopK;
							profileStats.gpuDpColumnFullDebugCpuRecordMissingPostTopK = missingPostTopK;
							profileStats.gpuDpColumnFullDebugFirstMismatchRank = firstMismatchRank;
							profileStats.gpuDpColumnFullDebugFirstMismatchScoreDelta = scoreDelta;
							profileStats.gpuDpColumnFullDebugFirstMismatchPositionDelta = positionDelta;
							profileStats.gpuDpColumnFullDebugFirstMismatchCountDelta = countDelta;
							profileStats.gpuDpColumnFullDebugScoreInfoSetMismatches =
								cpuMissingPre + preMissingCpu;
							profileStats.gpuDpColumnFullDebugScoreInfoFieldMismatches =
								fieldMismatches;
							profileStats.gpuDpColumnFullDebugColumnMismatches =
								columnMismatches;
							profileStats.gpuDpColumnFullDebugColumnScoreDeltaMax =
								columnScoreDeltaMax;
							if (gpuDpColumnPostTopKPackShadow)
							{
								profileStats.gpuDpColumnPostTopKCpuRecords =
									static_cast<uint64_t>(cpuScoreInfo.size());
								profileStats.gpuDpColumnPostTopKGpuPreRecords =
									static_cast<uint64_t>(gpuPreTopKScoreInfo.size());
								profileStats.gpuDpColumnPostTopKGpuPostRecords =
									static_cast<uint64_t>(gpuScoreInfo.size());
								profileStats.gpuDpColumnPostTopKCpuPackMismatches =
									cpuPackMismatches;
								profileStats.gpuDpColumnPostTopKGpuPackMismatches =
									gpuPackMismatches;
								profileStats.gpuDpColumnPostTopKMissingRecords =
									missingPostRecords;
								profileStats.gpuDpColumnPostTopKExtraRecords =
									extraPostRecords;
								profileStats.gpuDpColumnPostTopKRankMismatches =
									gpuPackMismatches;
								profileStats.gpuDpColumnPostTopKFieldMismatchMask =
									postTopKFieldMask;
								profileStats.gpuDpColumnPostTopKCountMismatches =
									postTopKCountMismatches;
								profileStats.gpuDpColumnPostTopKPositionMismatches =
									postTopKPositionMismatches;
								profileStats.gpuDpColumnPostTopKScoreMismatches =
									postTopKScoreMismatches;
							}
						}

						cerr << "[fasim.cuda.full_scoreinfo]"
						     << " window=" << validationWindowOrdinal
						     << " cpu_records=" << cpuScoreInfo.size()
						     << " gpu_pre_topk_records=" << gpuPreTopKScoreInfo.size()
						     << " gpu_post_topk_records=" << gpuScoreInfo.size()
						     << " column_mismatches=" << columnMismatches
						     << " column_score_delta_max=" << columnScoreDeltaMax
						     << " cpu_missing_pre_topk=" << cpuMissingPre
						     << " pre_missing_cpu=" << preMissingCpu
						     << " first_mismatch_rank=" << firstMismatchRank
						     << " first_mismatch_score_delta=" << scoreDelta
						     << " first_mismatch_position_delta=" << positionDelta
						     << " first_mismatch_count_delta=" << countDelta
						     << endl;
						if (gpuDpColumnPostTopKPackShadow)
						{
							cerr << "[fasim.cuda.post_topk_pack_shadow]"
							     << " window=" << validationWindowOrdinal
							     << " cpu_records=" << cpuScoreInfo.size()
							     << " gpu_pre_records=" << gpuPreTopKScoreInfo.size()
							     << " gpu_post_records=" << gpuScoreInfo.size()
							     << " cpu_pack_mismatches=" << cpuPackMismatches
							     << " gpu_pack_mismatches=" << gpuPackMismatches
							     << " missing_records=" << missingPostRecords
							     << " extra_records=" << extraPostRecords
							     << " rank_mismatches=" << gpuPackMismatches
							     << " field_mismatch_mask=" << postTopKFieldMask
							     << " count_mismatches=" << postTopKCountMismatches
							     << " position_mismatches=" << postTopKPositionMismatches
							     << " score_mismatches=" << postTopKScoreMismatches
							     << endl;
						}

						if (gpuDpColumnDebugMaxRecords > 0)
						{
							const size_t sampleCount =
								static_cast<size_t>(gpuDpColumnDebugMaxRecords);
							auto print_scoreinfo_sample = [&](const char *label,
							                                  const std::vector<struct StripedSmithWaterman::scoreInfo> &items)
							{
								const size_t limit = std::min(items.size(), sampleCount);
								for (size_t i = 0; i < limit; ++i)
								{
									cerr << "[fasim.cuda.full_scoreinfo] "
									     << label
									     << "[" << i << "]=("
									     << items[i].score << ","
									     << items[i].position << ")"
									     << endl;
								}
							};
							print_scoreinfo_sample("cpu", cpuScoreInfo);
							print_scoreinfo_sample("gpu_pre_topk", gpuPreTopKScoreInfo);
							print_scoreinfo_sample("gpu_post_topk", gpuScoreInfo);
						}
					}
				}
				if (profileEnabled && gpuDpColumnRequested)
				{
					++profileStats.gpuDpColumnColumnMaxMismatches;
				}
			}
			const bool cleanFullDebugWindowSelected =
				gpuScoreInfoMatchesCpu &&
				(gpuDpColumnFullScoreInfoDebug || gpuDpColumnPostTopKPackShadow) &&
				gpuDpColumnMismatchDebug &&
				!gpuDpColumnFullDebugRecorded &&
				(gpuDpColumnDebugWindowIndex < 0 ||
				 static_cast<int>(validationWindowOrdinal) == gpuDpColumnDebugWindowIndex);
			if (cleanFullDebugWindowSelected)
			{
				gpuDpColumnFullDebugRecorded = true;
				std::vector<struct StripedSmithWaterman::scoreInfo> gpuPreTopKScoreInfo;
				if (!gpuExactColumnScores.empty())
				{
					build_scoreinfo_from_column_scores(gpuExactColumnScores,
					                                   minScore,
					                                   gpuPreTopKScoreInfo);
				}
				else
				{
					gpuPreTopKScoreInfo = gpuScoreInfo;
				}

				uint64_t columnMismatches = 0;
				uint64_t columnScoreDeltaMax = 0;
				const size_t columnCount =
					std::max(cpuColumnScores.size(), gpuExactColumnScores.size());
				for (size_t i = 0; i < columnCount; ++i)
				{
					const int cpuScore = i < cpuColumnScores.size() ? cpuColumnScores[i] : 0;
					const int gpuScore = i < gpuExactColumnScores.size() ? gpuExactColumnScores[i] : 0;
					if (cpuScore != gpuScore)
					{
						++columnMismatches;
						const long long delta =
							static_cast<long long>(gpuScore) - static_cast<long long>(cpuScore);
						const uint64_t absDelta = static_cast<uint64_t>(delta < 0 ? -delta : delta);
						if (absDelta > columnScoreDeltaMax)
						{
							columnScoreDeltaMax = absDelta;
						}
					}
				}

				const uint64_t cpuPackMismatches =
					scoreinfo_rank_mismatches(cpuScoreInfo, gpuPreTopKScoreInfo);
				const uint64_t gpuPackMismatches =
					scoreinfo_rank_mismatches(cpuScoreInfo, gpuScoreInfo);
				const uint64_t missingPostRecords =
					scoreinfo_missing_from(cpuScoreInfo, gpuScoreInfo);
				const uint64_t extraPostRecords =
					scoreinfo_missing_from(gpuScoreInfo, cpuScoreInfo);

				if (profileEnabled && gpuDpColumnRequested)
				{
					profileStats.gpuDpColumnFullDebugWindowIndex =
						static_cast<long long>(validationWindowOrdinal);
					profileStats.gpuDpColumnFullDebugCpuRecords =
						static_cast<uint64_t>(cpuScoreInfo.size());
					profileStats.gpuDpColumnFullDebugGpuPreTopKRecords =
						static_cast<uint64_t>(gpuPreTopKScoreInfo.size());
					profileStats.gpuDpColumnFullDebugGpuPostTopKRecords =
						static_cast<uint64_t>(gpuScoreInfo.size());
					profileStats.gpuDpColumnFullDebugCpuRecordMissingPreTopK = 0;
					profileStats.gpuDpColumnFullDebugCpuRecordMissingPostTopK = 0;
					profileStats.gpuDpColumnFullDebugFirstMismatchRank = -1;
					profileStats.gpuDpColumnFullDebugFirstMismatchScoreDelta = 0;
					profileStats.gpuDpColumnFullDebugFirstMismatchPositionDelta = 0;
					profileStats.gpuDpColumnFullDebugFirstMismatchCountDelta = 0;
					profileStats.gpuDpColumnFullDebugScoreInfoSetMismatches = 0;
					profileStats.gpuDpColumnFullDebugScoreInfoFieldMismatches = 0;
					profileStats.gpuDpColumnFullDebugColumnMismatches = columnMismatches;
					profileStats.gpuDpColumnFullDebugColumnScoreDeltaMax = columnScoreDeltaMax;
					if (gpuDpColumnPostTopKPackShadow)
					{
						profileStats.gpuDpColumnPostTopKCpuRecords =
							static_cast<uint64_t>(cpuScoreInfo.size());
						profileStats.gpuDpColumnPostTopKGpuPreRecords =
							static_cast<uint64_t>(gpuPreTopKScoreInfo.size());
						profileStats.gpuDpColumnPostTopKGpuPostRecords =
							static_cast<uint64_t>(gpuScoreInfo.size());
						profileStats.gpuDpColumnPostTopKCpuPackMismatches =
							cpuPackMismatches;
						profileStats.gpuDpColumnPostTopKGpuPackMismatches =
							gpuPackMismatches;
						profileStats.gpuDpColumnPostTopKMissingRecords =
							missingPostRecords;
						profileStats.gpuDpColumnPostTopKExtraRecords =
							extraPostRecords;
						profileStats.gpuDpColumnPostTopKRankMismatches =
							gpuPackMismatches;
						profileStats.gpuDpColumnPostTopKFieldMismatchMask = 0;
						profileStats.gpuDpColumnPostTopKCountMismatches = 0;
						profileStats.gpuDpColumnPostTopKPositionMismatches = 0;
						profileStats.gpuDpColumnPostTopKScoreMismatches = 0;
					}
				}

				cerr << "[fasim.cuda.full_scoreinfo]"
				     << " window=" << validationWindowOrdinal
				     << " cpu_records=" << cpuScoreInfo.size()
				     << " gpu_pre_topk_records=" << gpuPreTopKScoreInfo.size()
				     << " gpu_post_topk_records=" << gpuScoreInfo.size()
				     << " column_mismatches=" << columnMismatches
				     << " column_score_delta_max=" << columnScoreDeltaMax
				     << " cpu_missing_pre_topk=0"
				     << " pre_missing_cpu=0"
				     << " first_mismatch_rank=-1"
				     << " first_mismatch_score_delta=0"
				     << " first_mismatch_position_delta=0"
				     << " first_mismatch_count_delta=0"
				     << endl;
				if (gpuDpColumnPostTopKPackShadow)
				{
					cerr << "[fasim.cuda.post_topk_pack_shadow]"
					     << " window=" << validationWindowOrdinal
					     << " cpu_records=" << cpuScoreInfo.size()
					     << " gpu_pre_records=" << gpuPreTopKScoreInfo.size()
					     << " gpu_post_records=" << gpuScoreInfo.size()
					     << " cpu_pack_mismatches=" << cpuPackMismatches
					     << " gpu_pack_mismatches=" << gpuPackMismatches
					     << " missing_records=" << missingPostRecords
					     << " extra_records=" << extraPostRecords
					     << " rank_mismatches=" << gpuPackMismatches
					     << " field_mismatch_mask=0"
					     << " count_mismatches=0"
					     << " position_mismatches=0"
					     << " score_mismatches=0"
					     << endl;
				}
			}
			if (profileEnabled && gpuDpColumnRequested)
			{
				fasim_profile_add_elapsed(profileStats.gpuDpColumnValidateNanoseconds, validateStart);
			}
			return ok;
		};

		auto write_task_triplexes = [&](const StreamTask &task)
		{
			if (profileEnabled)
			{
				profileStats.numCandidates += static_cast<uint64_t>(taskTriplexes.size());
			}
			for (size_t i = 0; i < taskTriplexes.size(); ++i)
			{
				const uint64_t validationStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
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
					if (profileEnabled)
					{
						fasim_profile_add_elapsed(profileStats.validationNanoseconds, validationStart);
					}
					continue;
				}
				if (profileEnabled)
				{
					fasim_profile_add_elapsed(profileStats.validationNanoseconds, validationStart);
					++profileStats.numValidatedCandidates;
				}

				const int motif = 0;
				const int middle = static_cast<int>((atr.stari + atr.endi) / 2);
				const int center = middle;
				const uint64_t outputStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;

				if (writeLite)
				{
					outLiteFile << atr.chr << "\t"
					            << atr.genomestart << "\t"
					            << atr.genomeend << "\t"
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
					            << atr.tri_score << "\n";
				}

				if (writeFull)
				{
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
				}
				if (profileEnabled)
				{
					fasim_profile_add_elapsed(profileStats.outputNanoseconds, outputStart);
					++profileStats.numFinalHits;
				}
			}
			taskTriplexes.clear();
		};

		auto flush_batch = [&]()
		{
			if (tasks.empty())
			{
				return;
			}

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
					PreAlignCudaBatchResult batchResult;
					string cudaError;
					const uint64_t gpuTotalStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
					const bool ok = prealign_cuda_find_topk_column_maxima(cudaQueries[0],
					                                                    encodedTargets.data(),
					                                                    static_cast<int>(tasks.size()),
					                                                    currentTargetLength,
					                                                    topK,
					                                                    &peaks,
					                                                    &batchResult,
					                                                    &cudaError);
					if (profileEnabled && gpuDpColumnRequested)
					{
						record_gpu_dp_column_batch(tasks.size(),
						                           currentTargetLength,
						                           peaks.size(),
						                           batchResult,
						                           gpuTotalStart);
					}
					if (!ok)
					{
						if (profileEnabled && gpuDpColumnRequested)
						{
							profileStats.gpuDpColumnFallbacks += static_cast<uint64_t>(tasks.size());
						}
						useCudaBatch = false;
						maxTasksTotal = 1;
					}
					else
					{
						bool gpuValidationOk = true;
						if (gpuDpColumnValidate)
						{
							for (size_t t = 0; t < tasks.size(); ++t)
							{
								const size_t base = t * static_cast<size_t>(topK);
								const uint8_t *debugTarget =
									encodedTargets.data() + t * static_cast<size_t>(currentTargetLength);
								if (!validate_gpu_dp_column_task(tasks[t],
								                                  peaks.data() + base,
								                                  &cudaQueries[0],
								                                  debugTarget,
								                                  currentTargetLength))
								{
									gpuValidationOk = false;
								}
							}
						}
						if (!gpuValidationOk)
						{
							if (profileEnabled && gpuDpColumnRequested)
							{
								profileStats.gpuDpColumnFallbacks += static_cast<uint64_t>(tasks.size());
							}
						}
						else if (gpuDpColumnRequested || extendThreadCount <= 1 || tasks.size() <= 1)
						{
							for (size_t t = 0; t < tasks.size(); ++t)
							{
								const StreamTask &task = tasks[t];
								const size_t base = t * static_cast<size_t>(topK);
								int maxScore = peaks[base].score;
								int minScore = static_cast<int>(static_cast<double>(maxScore) * 0.8);
								const uint8_t *exactTarget =
									encodedTargets.data() + t * static_cast<size_t>(currentTargetLength);
								if (gpuDpColumnRequested)
								{
									if (!build_scoreinfo_from_gpu_exact_columns(cudaQueries[0],
									                                            exactTarget,
									                                            currentTargetLength,
									                                            &maxScore,
									                                            finalScoreInfo,
									                                            NULL,
									                                            "extend"))
									{
										gpuValidationOk = false;
										break;
									}
									minScore = static_cast<int>(static_cast<double>(maxScore) * 0.8);
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
								                              task.srcSeq,
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
									std::ostringstream liteBuf;

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
										                              task.srcSeq,
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
											liteBuf.str("");
											liteBuf.clear();
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
												liteBuf << chr << "\t"
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
												        << atr.tri_score << "\n";
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
										const std::string liteText = writeLite ? liteBuf.str() : std::string();
										if (outText.empty() && liteText.empty())
										{
											continue;
										}

										lock_guard<std::mutex> lock(outMutex);
										if (writeLite && !liteText.empty())
										{
											outLiteFile << liteText;
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

						if (gpuValidationOk)
						{
							tasks.clear();
							encodedTargets.clear();
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
					std::vector<PreAlignCudaBatchResult> batchResults(cudaDeviceCount);
					std::vector<uint64_t> batchTotalNanoseconds(cudaDeviceCount, 0);

					std::vector<std::thread> prealignThreads;
					prealignThreads.reserve(cudaDeviceCount);
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
							const uint64_t gpuTotalStart = (profileEnabled && gpuDpColumnRequested) ?
								fasim_profile_now_nanoseconds() : 0;
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
							batchResults[d] = batchResult;
							if (profileEnabled && gpuDpColumnRequested)
							{
								batchTotalNanoseconds[d] = fasim_profile_now_nanoseconds() - gpuTotalStart;
							}
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
						if (profileEnabled && gpuDpColumnRequested)
						{
							profileStats.gpuDpColumnFallbacks += static_cast<uint64_t>(tasks.size());
						}
						useCudaBatch = false;
						maxTasksTotal = 1;
					}
					else
					{
						if (profileEnabled && gpuDpColumnRequested)
						{
							for (size_t d = 0; d < cudaDeviceCount; ++d)
							{
								if (chunkCount[d] == 0)
								{
									continue;
								}
								++profileStats.gpuDpColumnCalls;
								profileStats.gpuDpColumnWindows += static_cast<uint64_t>(chunkCount[d]);
								const uint64_t cells =
									static_cast<uint64_t>(chunkCount[d]) *
									static_cast<uint64_t>(currentTargetLength > 0 ? currentTargetLength : 0) *
									static_cast<uint64_t>(lncSeq.size());
								profileStats.gpuDpColumnCells += cells;
								profileStats.numDpCells += cells;
								profileStats.gpuDpColumnH2DBytes +=
									static_cast<uint64_t>(chunkCount[d]) *
									static_cast<uint64_t>(currentTargetLength > 0 ? currentTargetLength : 0) *
									static_cast<uint64_t>(sizeof(uint8_t));
								profileStats.gpuDpColumnD2HBytes +=
									static_cast<uint64_t>(peaksByDevice[d].size()) *
									static_cast<uint64_t>(sizeof(PreAlignCudaPeak));
								profileStats.gpuDpColumnKernelNanoseconds +=
									fasim_profile_nanoseconds_from_seconds(batchResults[d].gpuSeconds);
								profileStats.gpuDpColumnTotalNanoseconds += batchTotalNanoseconds[d];
							}
						}
						bool gpuValidationOk = true;
						if (gpuDpColumnValidate)
						{
							for (size_t d = 0; d < cudaDeviceCount; ++d)
							{
								for (size_t local = 0; local < chunkCount[d]; ++local)
								{
									const size_t taskIndex = chunkBegin[d] + local;
									const size_t base = local * static_cast<size_t>(topK);
									const uint8_t *debugTarget =
										encodedTargets.data() +
										taskIndex * static_cast<size_t>(currentTargetLength);
									if (!validate_gpu_dp_column_task(tasks[taskIndex],
									                                  peaksByDevice[d].data() + base,
									                                  &cudaQueries[d],
									                                  debugTarget,
									                                  currentTargetLength))
									{
										gpuValidationOk = false;
									}
								}
							}
						}
						if (!gpuValidationOk)
						{
							if (profileEnabled && gpuDpColumnRequested)
							{
								profileStats.gpuDpColumnFallbacks += static_cast<uint64_t>(tasks.size());
							}
						}
						else
						{
							struct WorkItem
							{
								size_t device;
								size_t local;
							};

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
							const int suppressBp = fasim_prealign_peak_suppress_bp_runtime();
							const int requestedWorkerCount =
								gpuDpColumnRequested ? 1 : extendThreadCount;
							const int workerCount = min(static_cast<int>(work.size()), requestedWorkerCount);
							std::atomic<size_t> nextWork(0);
							std::atomic<int> debugPrinted(0);
							std::atomic<int> exactScoreInfoFailed(0);

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
									std::ostringstream liteBuf;

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

										if (exactScoreInfoFailed.load(std::memory_order_relaxed) != 0)
										{
											break;
										}

										int maxScore = taskPeaks[0].score;
										int minScore = static_cast<int>(static_cast<double>(maxScore) * 0.8);

										finalScoreInfoLocal.clear();
										if (gpuDpColumnRequested)
										{
											const uint8_t *exactTarget =
												encodedTargets.data() +
												(localBegin + local) * static_cast<size_t>(currentTargetLength);
											if (!build_scoreinfo_from_gpu_exact_columns(cudaQueries[d],
											                                            exactTarget,
											                                            currentTargetLength,
											                                            &maxScore,
											                                            finalScoreInfoLocal,
											                                            NULL,
											                                            "extend"))
											{
												exactScoreInfoFailed.store(1, std::memory_order_relaxed);
												break;
											}
											minScore = static_cast<int>(static_cast<double>(maxScore) * 0.8);
										}
										else
										{
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
										                              task.srcSeq,
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
											liteBuf.str("");
											liteBuf.clear();
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
												liteBuf << chr << "\t"
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
												        << atr.tri_score << "\n";
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
										const std::string liteText = writeLite ? liteBuf.str() : std::string();
										if (outText.empty() && liteText.empty())
										{
											continue;
										}

										lock_guard<std::mutex> lock(outMutex);
										if (writeLite && !liteText.empty())
										{
											outLiteFile << liteText;
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
							if (exactScoreInfoFailed.load(std::memory_order_relaxed) != 0)
							{
								if (profileEnabled && gpuDpColumnRequested)
								{
									profileStats.gpuDpColumnFallbacks += static_cast<uint64_t>(tasks.size());
								}
							}
							else
							{
								tasks.clear();
								encodedTargets.clear();
								currentTargetLength = -1;
								return;
							}
						}
					}
				}
			}

			// CPU fallback for this batch.
			for (size_t t = 0; t < tasks.size(); ++t)
			{
				StreamTask &task = tasks[t];
				const uint64_t taskCells =
					static_cast<uint64_t>(lncSeq.size()) *
					static_cast<uint64_t>(task.seq2.size());
				uint64_t columnStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
				const int minScore = static_cast<int>(static_cast<double>(calc_score_once(lncSeq, task.seq2, task.dnaStartPos, paraList.rule)) * 0.8);
				if (profileEnabled)
				{
					fasim_profile_add_elapsed(profileStats.columnMaxNanoseconds, columnStart);
					profileStats.numDpCells += taskCells;
				}
				taskTriplexes.clear();
				const uint64_t dpStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
				if (paraList.doFastSim)
				{
					fastSIM(lncSeq,
					        task.seq2,
					        task.srcSeq,
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
				else
				{
					SIM(lncSeq,
					    task.seq2,
					    task.srcSeq,
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
				if (profileEnabled)
				{
					fasim_profile_add_elapsed(profileStats.dpScoringNanoseconds, dpStart);
					profileStats.numDpCells += taskCells;
				}
				write_task_triplexes(task);
			}

			tasks.clear();
			encodedTargets.clear();
			currentTargetLength = -1;
		};

		auto enqueue_task = [&](const std::string &seq1,
		                        long dnaStartPos,
		                        int reverseMode,
		                        int paraMode,
		                        int rule,
		                        FasimSrcTransform srcTransform,
		                        bool reverseSeq2,
		                        long recordStartGenome,
		                        const std::string &chrTag)
		{
			uint64_t enqueueStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
			std::string seq2;
			const bool tableRequested = fasim_transfer_string_table_requested_runtime();
			const bool tableValidate = fasim_transfer_string_table_validate_enabled_runtime();
			if (profileEnabled)
			{
				auto record_transfer_distribution = [&](uint64_t transferElapsed)
				{
					const int modeIndex = fasim_transfer_mode_index(reverseMode, paraMode);
					if (modeIndex >= 0 && modeIndex < 4)
					{
						++profileStats.transferStringProfile.modeCalls[modeIndex];
						profileStats.transferStringProfile.modeNanoseconds[modeIndex] += transferElapsed;
					}
					if (rule >= 1 && rule <= 18)
					{
						++profileStats.transferStringProfile.ruleCalls[rule];
						profileStats.transferStringProfile.ruleNanoseconds[rule] += transferElapsed;
					}
				};
				if (tableRequested)
				{
					const uint64_t tableStart = fasim_profile_now_nanoseconds();
					seq2 = transferStringTableDriven(seq1, reverseMode, paraMode, rule);
					const uint64_t tableElapsed = fasim_profile_now_nanoseconds() - tableStart;
					profileStats.windowGenerationTransferNanoseconds += tableElapsed;
					profileStats.transferStringProfile.totalNanoseconds += tableElapsed;
					profileStats.transferStringProfile.convertNanoseconds += tableElapsed;
					profileStats.transferStringProfile.tableNanoseconds += tableElapsed;
					++profileStats.transferStringProfile.calls;
					++profileStats.transferStringProfile.tableCalls;
					profileStats.transferStringProfile.inputBases += static_cast<unsigned long long>(seq1.size());
					profileStats.transferStringProfile.outputBases += static_cast<unsigned long long>(seq2.size());
					profileStats.transferStringProfile.tableBasesConverted += static_cast<unsigned long long>(seq1.size());
					record_transfer_distribution(tableElapsed);
					if (tableValidate)
					{
						FasimTransferStringProfileStats legacyValidateStats;
						const uint64_t legacyValidateStart = fasim_profile_now_nanoseconds();
						const std::string legacySeq2 = transferStringProfiled(seq1, reverseMode, paraMode, rule, &legacyValidateStats);
						const uint64_t legacyValidateElapsed = fasim_profile_now_nanoseconds() - legacyValidateStart;
						profileStats.transferStringProfile.tableLegacyValidateNanoseconds += legacyValidateElapsed;
						++profileStats.transferStringProfile.tableComparedCalls;
						if (legacySeq2 != seq2)
						{
							++profileStats.transferStringProfile.tableMismatches;
							++profileStats.transferStringProfile.tableFallbacks;
							seq2 = legacySeq2;
						}
					}
				}
				else
				{
					const uint64_t transferStart = fasim_profile_now_nanoseconds();
					const unsigned long long innerBefore = fasim_transfer_profile_inner_nanoseconds(profileStats.transferStringProfile);
					seq2 = transferStringProfiled(seq1, reverseMode, paraMode, rule, &profileStats.transferStringProfile);
					const uint64_t transferElapsed = fasim_profile_now_nanoseconds() - transferStart;
					const unsigned long long innerAfter = fasim_transfer_profile_inner_nanoseconds(profileStats.transferStringProfile);
					const unsigned long long innerElapsed = innerAfter >= innerBefore ? innerAfter - innerBefore : 0;
					profileStats.windowGenerationTransferNanoseconds += transferElapsed;
					profileStats.transferStringProfile.totalNanoseconds += transferElapsed;
					if (transferElapsed > innerElapsed)
					{
						profileStats.transferStringProfile.residualNanoseconds += transferElapsed - innerElapsed;
					}
					record_transfer_distribution(transferElapsed);
					if (fasim_transfer_string_table_shadow_enabled_runtime())
					{
						++profileStats.transferStringProfile.tableShadowCalls;
						profileStats.transferStringProfile.tableShadowInputBases += static_cast<unsigned long long>(seq1.size());
						const uint64_t tableShadowStart = fasim_profile_now_nanoseconds();
						const std::string tableSeq2 = transferStringTableDriven(seq1, reverseMode, paraMode, rule);
						const uint64_t tableShadowElapsed = fasim_profile_now_nanoseconds() - tableShadowStart;
						profileStats.transferStringProfile.tableShadowNanoseconds += tableShadowElapsed;
						++profileStats.transferStringProfile.tableShadowComparedCalls;
						if (tableSeq2 != seq2)
						{
							++profileStats.transferStringProfile.tableShadowMismatches;
						}
					}
				}
			}
			else
			{
				seq2 = transferStringTableOptIn(seq1, reverseMode, paraMode, rule);
			}
			if (reverseSeq2)
			{
				const uint64_t reverseStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
				reverseSeq(seq2);
				if (profileEnabled)
				{
					fasim_profile_add_elapsed(profileStats.windowGenerationReverseNanoseconds, reverseStart);
				}
			}

			if (currentTargetLength < 0)
			{
				currentTargetLength = static_cast<int>(seq2.size());
				encodedTargets.reserve(static_cast<size_t>(maxTasksTotal) * static_cast<size_t>(currentTargetLength));
			}
			if (static_cast<int>(seq2.size()) != currentTargetLength || static_cast<int>(tasks.size()) >= maxTasksTotal)
			{
				if (profileEnabled)
				{
					fasim_profile_add_elapsed(profileStats.windowGenerationNanoseconds, enqueueStart);
				}
				const uint64_t flushStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
				flush_batch();
				if (profileEnabled)
				{
					fasim_profile_add_elapsed(profileStats.windowGenerationFlushNanoseconds, flushStart);
				}
				enqueueStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
				currentTargetLength = static_cast<int>(seq2.size());
				encodedTargets.reserve(static_cast<size_t>(maxTasksTotal) * static_cast<size_t>(currentTargetLength));
			}

			StreamTask task;
			const uint64_t sourceTransformStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
			fasim_apply_src_transform(seq1, srcTransform, task.srcSeq);
			if (profileEnabled)
			{
				fasim_profile_add_elapsed(profileStats.windowGenerationSourceTransformNanoseconds, sourceTransformStart);
			}
			task.seq2.swap(seq2);
			task.chr = chrTag;
			task.recordStartGenome = recordStartGenome;
			task.dnaStartPos = dnaStartPos;
			task.strand = reverseMode;
			task.Para = paraMode;
			task.rule = rule;

			tasks.push_back(std::move(task));

			const std::string &storedSeq2 = tasks.back().seq2;
			const uint64_t encodeStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
			for (int k = 0; k < currentTargetLength; ++k)
			{
				encodedTargets.push_back(fasim_encode_base(static_cast<unsigned char>(storedSeq2[static_cast<size_t>(k)])));
			}
			if (profileEnabled)
			{
				fasim_profile_add_elapsed(profileStats.windowGenerationEncodeNanoseconds, encodeStart);
			}
			if (profileEnabled)
			{
				fasim_profile_add_elapsed(profileStats.windowGenerationNanoseconds, enqueueStart);
			}
		};

		string pendingHeader;
		FasimFastaRecord record;
		while (true)
		{
			const uint64_t readRecordStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
			const bool haveRecord = fasim_read_next_fasta_record(dnaIn, pendingHeader, record);
			if (profileEnabled)
			{
				fasim_profile_add_elapsed(profileStats.ioNanoseconds, readRecordStart);
			}
			if (!haveRecord)
			{
				break;
			}
			if (record.sequence.empty())
			{
				continue;
			}
			string recordSpecies;
			string recordChr;
			long recordStartGenome = 1;
			fasim_parse_dna_header_fields(record.header, recordSpecies, recordChr, recordStartGenome);
			ensure_output_opened(recordSpecies);

			vector<string> dnaSequencesVec;
			vector<int> dnaSequencesStartPos;
			int cut_num = 0;
			const uint64_t cutStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
			cutSequence(record.sequence, dnaSequencesVec, dnaSequencesStartPos, paraList.cutLength, paraList.overlapLength, cut_num);
			if (profileEnabled)
			{
				fasim_profile_add_elapsed_to(profileStats.windowGenerationNanoseconds,
				                             profileStats.windowGenerationCutSequenceNanoseconds,
				                             cutStart);
			}

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
				if (profileEnabled)
				{
					++profileStats.numWindows;
				}

				if (paraList.strand >= 0)
				{
					if (paraList.rule == 0)
					{
						for (int j = 0; j < 6; j++)
						{
							enqueue_task(seq1, dnaStartPos, 0, 1, j + 1, FASIM_SRC_ORIG, false, recordStartGenome, recordChr);
							enqueue_task(seq1, dnaStartPos, 1, 1, j + 1, FASIM_SRC_REVCOMP, true, recordStartGenome, recordChr);
						}
					}
					else if (paraList.rule > 0 && paraList.rule < 7)
					{
						enqueue_task(seq1, dnaStartPos, 0, 1, paraList.rule, FASIM_SRC_ORIG, false, recordStartGenome, recordChr);
						enqueue_task(seq1, dnaStartPos, 1, 1, paraList.rule, FASIM_SRC_REVCOMP, true, recordStartGenome, recordChr);
					}
				}

				if (paraList.strand <= 0)
				{
					if (paraList.rule == 0)
					{
						for (int j = 0; j < 18; j++)
						{
							enqueue_task(seq1, dnaStartPos, 1, -1, j + 1, FASIM_SRC_COMP, false, recordStartGenome, recordChr);
							enqueue_task(seq1, dnaStartPos, 0, -1, j + 1, FASIM_SRC_REV, true, recordStartGenome, recordChr);
						}
					}
					else
					{
						enqueue_task(seq1, dnaStartPos, 1, -1, paraList.rule, FASIM_SRC_COMP, false, recordStartGenome, recordChr);
						enqueue_task(seq1, dnaStartPos, 0, -1, paraList.rule, FASIM_SRC_REV, true, recordStartGenome, recordChr);
					}
				}
			}
		}

		const uint64_t finalFlushStart = profileEnabled ? fasim_profile_now_nanoseconds() : 0;
		flush_batch();
		if (profileEnabled)
		{
			fasim_profile_add_elapsed(profileStats.windowGenerationFlushNanoseconds, finalFlushStart);
		}
		if (outOpened)
		{
			if (writeFull)
			{
				outFile.close();
			}
			if (writeLite)
			{
				outLiteFile.close();
			}
		}
		for (size_t i = 0; i < cudaQueries.size(); ++i)
		{
			prealign_cuda_release_query(&cudaQueries[i]);
		}

		end = clock();
		cout << "finished normally" << endl;
		cpu_time = ((float)(end - start)) / CLOCKS_PER_SEC;
		cout<<"Running time is "<<cpu_time<<endl;
		if (profileEnabled)
		{
			profileStats.totalNanoseconds = fasim_profile_now_nanoseconds() - profileTotalStart;
			fasim_print_profile_stats(profileStats);
		}
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
	if (profileEnabled)
	{
		profileStats.totalNanoseconds = fasim_profile_now_nanoseconds() - profileTotalStart;
		fasim_print_profile_stats(profileStats);
	}
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
