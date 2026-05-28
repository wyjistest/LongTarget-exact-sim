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
#include <iomanip>

#include "fastsim.h"
using namespace std;

namespace
{

typedef std::chrono::steady_clock FasimTelemetryClock;

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

struct FasimRuntimeTelemetry
{
    FasimRuntimeTelemetry() :
        prealignCudaRequested(false),
        prealignCudaActive(false),
        prealignCudaDevice(-1),
        prealignCudaDevices(0),
        prealignCudaTasks(0),
        prealignCudaBatches(0),
        prealignCudaTopK(0),
        prealignCudaMaxTasks(0),
        prealignCudaPeakSuppressBp(0),
        prealignCudaH2DSeconds(0.0),
        prealignCudaKernelSeconds(0.0),
        prealignCudaD2HSeconds(0.0),
        prealignCudaTotalSeconds(0.0),
        extendThreads(0),
        extendSeconds(0.0),
        extendCandidates(0),
        extendCutlengthAttempts(0),
        extendAlignCalls(0),
        extendAlignCells(0),
        extendAlignSeconds(0.0),
        extendConvertCalls(0),
        extendConvertSeconds(0.0),
        extendSortUniqueSeconds(0.0),
        extendRecordsBeforeFilter(0),
        extendRecordsEmitted(0),
        extendEmptyScoreInfo(0),
        outputSeconds(0.0),
        prealignCudaFallbacks(0),
        prealignCudaFallbackUnsupportedRule(0),
        prealignCudaFallbackUnsupportedSequenceAlphabet(0),
        prealignCudaFallbackTooFewTasks(0),
        prealignCudaFallbackTooManyTasks(0),
        prealignCudaFallbackTargetTooShort(0),
        prealignCudaFallbackQueryTooLongOrUnsupported(0),
        prealignCudaFallbackCudaAllocationOrLaunch(0),
        prealignCudaFallbackEmptyCandidateSet(0),
        prealignCudaFallbackUnknown(0)
    {
    }

    bool prealignCudaRequested;
    bool prealignCudaActive;
    int prealignCudaDevice;
    int prealignCudaDevices;
    long long prealignCudaTasks;
    long long prealignCudaBatches;
    int prealignCudaTopK;
    int prealignCudaMaxTasks;
    int prealignCudaPeakSuppressBp;
    double prealignCudaH2DSeconds;
    double prealignCudaKernelSeconds;
    double prealignCudaD2HSeconds;
    double prealignCudaTotalSeconds;
    int extendThreads;
    double extendSeconds;
    long long extendCandidates;
    long long extendCutlengthAttempts;
    long long extendAlignCalls;
    long long extendAlignCells;
    double extendAlignSeconds;
    long long extendConvertCalls;
    double extendConvertSeconds;
    double extendSortUniqueSeconds;
    long long extendRecordsBeforeFilter;
    long long extendRecordsEmitted;
    long long extendEmptyScoreInfo;
    double outputSeconds;
    long long prealignCudaFallbacks;
    long long prealignCudaFallbackUnsupportedRule;
    long long prealignCudaFallbackUnsupportedSequenceAlphabet;
    long long prealignCudaFallbackTooFewTasks;
    long long prealignCudaFallbackTooManyTasks;
    long long prealignCudaFallbackTargetTooShort;
    long long prealignCudaFallbackQueryTooLongOrUnsupported;
    long long prealignCudaFallbackCudaAllocationOrLaunch;
    long long prealignCudaFallbackEmptyCandidateSet;
    long long prealignCudaFallbackUnknown;
};

static FasimRuntimeTelemetry g_fasimTelemetry;
static std::mutex g_fasimTelemetryMutex;

static inline double fasim_elapsed_seconds(FasimTelemetryClock::time_point start,FasimTelemetryClock::time_point end)
{
    return std::chrono::duration<double>(end - start).count();
}

static inline void fasim_telemetry_set_requested(bool requested)
{
    lock_guard<std::mutex> lock(g_fasimTelemetryMutex);
    g_fasimTelemetry.prealignCudaRequested = g_fasimTelemetry.prealignCudaRequested || requested;
}

static inline void fasim_telemetry_config(int device,int devices,int topK,int maxTasks,int suppressBp,int extendThreads)
{
    lock_guard<std::mutex> lock(g_fasimTelemetryMutex);
    g_fasimTelemetry.prealignCudaDevice = device;
    g_fasimTelemetry.prealignCudaDevices = devices;
    g_fasimTelemetry.prealignCudaTopK = topK;
    g_fasimTelemetry.prealignCudaMaxTasks = maxTasks;
    g_fasimTelemetry.prealignCudaPeakSuppressBp = suppressBp;
    g_fasimTelemetry.extendThreads = extendThreads;
}

static inline void fasim_telemetry_add_cuda_batch(int tasks,const PreAlignCudaBatchResult &batchResult)
{
    lock_guard<std::mutex> lock(g_fasimTelemetryMutex);
    g_fasimTelemetry.prealignCudaActive = g_fasimTelemetry.prealignCudaActive || batchResult.usedCuda;
    g_fasimTelemetry.prealignCudaTasks += tasks;
    g_fasimTelemetry.prealignCudaBatches += 1;
    g_fasimTelemetry.prealignCudaH2DSeconds += batchResult.h2dSeconds;
    g_fasimTelemetry.prealignCudaKernelSeconds += batchResult.kernelSeconds;
    g_fasimTelemetry.prealignCudaD2HSeconds += batchResult.d2hSeconds;
    g_fasimTelemetry.prealignCudaTotalSeconds += batchResult.totalSeconds;
}

static void fasim_telemetry_add_extend_delta(const FasimExtendTelemetryDelta &delta)
{
    lock_guard<std::mutex> lock(g_fasimTelemetryMutex);
    g_fasimTelemetry.extendSeconds += delta.totalSeconds;
    g_fasimTelemetry.extendCandidates += delta.candidates;
    g_fasimTelemetry.extendCutlengthAttempts += delta.cutlengthAttempts;
    g_fasimTelemetry.extendAlignCalls += delta.alignCalls;
    g_fasimTelemetry.extendAlignCells += delta.alignCells;
    g_fasimTelemetry.extendAlignSeconds += delta.alignSeconds;
    g_fasimTelemetry.extendConvertCalls += delta.convertCalls;
    g_fasimTelemetry.extendConvertSeconds += delta.convertSeconds;
    g_fasimTelemetry.extendSortUniqueSeconds += delta.sortUniqueSeconds;
    g_fasimTelemetry.extendRecordsBeforeFilter += delta.recordsBeforeFilter;
    g_fasimTelemetry.extendRecordsEmitted += delta.recordsEmitted;
    g_fasimTelemetry.extendEmptyScoreInfo += delta.emptyScoreInfo;
}

static inline void fasim_telemetry_add_output_seconds(double seconds)
{
    lock_guard<std::mutex> lock(g_fasimTelemetryMutex);
    g_fasimTelemetry.outputSeconds += seconds;
}

enum FasimPrealignCudaFallbackReason
{
    FASIM_PREALIGN_CUDA_FALLBACK_UNSUPPORTED_RULE,
    FASIM_PREALIGN_CUDA_FALLBACK_UNSUPPORTED_SEQUENCE_ALPHABET,
    FASIM_PREALIGN_CUDA_FALLBACK_TOO_FEW_TASKS,
    FASIM_PREALIGN_CUDA_FALLBACK_TOO_MANY_TASKS,
    FASIM_PREALIGN_CUDA_FALLBACK_TARGET_TOO_SHORT,
    FASIM_PREALIGN_CUDA_FALLBACK_QUERY_TOO_LONG_OR_UNSUPPORTED,
    FASIM_PREALIGN_CUDA_FALLBACK_CUDA_ALLOCATION_OR_LAUNCH,
    FASIM_PREALIGN_CUDA_FALLBACK_EMPTY_CANDIDATE_SET,
    FASIM_PREALIGN_CUDA_FALLBACK_UNKNOWN
};

static inline void fasim_telemetry_add_cuda_fallback(FasimPrealignCudaFallbackReason reason)
{
    lock_guard<std::mutex> lock(g_fasimTelemetryMutex);
    g_fasimTelemetry.prealignCudaFallbacks += 1;
    switch (reason)
    {
        case FASIM_PREALIGN_CUDA_FALLBACK_UNSUPPORTED_RULE:
            g_fasimTelemetry.prealignCudaFallbackUnsupportedRule += 1;
            break;
        case FASIM_PREALIGN_CUDA_FALLBACK_UNSUPPORTED_SEQUENCE_ALPHABET:
            g_fasimTelemetry.prealignCudaFallbackUnsupportedSequenceAlphabet += 1;
            break;
        case FASIM_PREALIGN_CUDA_FALLBACK_TOO_FEW_TASKS:
            g_fasimTelemetry.prealignCudaFallbackTooFewTasks += 1;
            break;
        case FASIM_PREALIGN_CUDA_FALLBACK_TOO_MANY_TASKS:
            g_fasimTelemetry.prealignCudaFallbackTooManyTasks += 1;
            break;
        case FASIM_PREALIGN_CUDA_FALLBACK_TARGET_TOO_SHORT:
            g_fasimTelemetry.prealignCudaFallbackTargetTooShort += 1;
            break;
        case FASIM_PREALIGN_CUDA_FALLBACK_QUERY_TOO_LONG_OR_UNSUPPORTED:
            g_fasimTelemetry.prealignCudaFallbackQueryTooLongOrUnsupported += 1;
            break;
        case FASIM_PREALIGN_CUDA_FALLBACK_CUDA_ALLOCATION_OR_LAUNCH:
            g_fasimTelemetry.prealignCudaFallbackCudaAllocationOrLaunch += 1;
            break;
        case FASIM_PREALIGN_CUDA_FALLBACK_EMPTY_CANDIDATE_SET:
            g_fasimTelemetry.prealignCudaFallbackEmptyCandidateSet += 1;
            break;
        case FASIM_PREALIGN_CUDA_FALLBACK_UNKNOWN:
        default:
            g_fasimTelemetry.prealignCudaFallbackUnknown += 1;
            break;
    }
}

static FasimPrealignCudaFallbackReason fasim_prealign_cuda_reason_from_error(const string &error)
{
    string lower = error;
    std::transform(lower.begin(), lower.end(), lower.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    if (lower.find("invalid query") != string::npos ||
        lower.find("alphabet") != string::npos ||
        lower.find("query handle") != string::npos ||
        lower.find("missing profile") != string::npos)
    {
        return FASIM_PREALIGN_CUDA_FALLBACK_QUERY_TOO_LONG_OR_UNSUPPORTED;
    }
    if (lower.find("invalid target") != string::npos ||
        lower.find("missing input targets") != string::npos)
    {
        return FASIM_PREALIGN_CUDA_FALLBACK_TARGET_TOO_SHORT;
    }
    if (lower.find("topk") != string::npos || lower.find("topk too large") != string::npos)
    {
        return FASIM_PREALIGN_CUDA_FALLBACK_TOO_MANY_TASKS;
    }
    if (lower.find("out of memory") != string::npos ||
        lower.find("allocation") != string::npos ||
        lower.find("launch") != string::npos ||
        lower.find("cuda") != string::npos ||
        lower.find("device") != string::npos ||
        lower.find("driver") != string::npos)
    {
        return FASIM_PREALIGN_CUDA_FALLBACK_CUDA_ALLOCATION_OR_LAUNCH;
    }
    return FASIM_PREALIGN_CUDA_FALLBACK_UNKNOWN;
}

static void fasim_emit_runtime_telemetry()
{
    FasimRuntimeTelemetry snapshot;
    const StripedSmithWaterman::AlignerTelemetryDelta alignerSnapshot =
        StripedSmithWaterman::SnapshotAlignerTelemetry();
    {
        lock_guard<std::mutex> lock(g_fasimTelemetryMutex);
        snapshot = g_fasimTelemetry;
    }
    ios::fmtflags oldFlags = cerr.flags();
    std::streamsize oldPrecision = cerr.precision();
    cerr << std::fixed << std::setprecision(9);
    cerr << "benchmark.fasim_prealign_cuda_requested=" << (snapshot.prealignCudaRequested ? 1 : 0) << endl;
    cerr << "benchmark.fasim_prealign_cuda_active=" << (snapshot.prealignCudaActive ? 1 : 0) << endl;
    cerr << "benchmark.fasim_prealign_cuda_device=" << snapshot.prealignCudaDevice << endl;
    cerr << "benchmark.fasim_prealign_cuda_devices=" << snapshot.prealignCudaDevices << endl;
    cerr << "benchmark.fasim_prealign_cuda_tasks=" << snapshot.prealignCudaTasks << endl;
    cerr << "benchmark.fasim_prealign_cuda_batches=" << snapshot.prealignCudaBatches << endl;
    cerr << "benchmark.fasim_prealign_cuda_topk=" << snapshot.prealignCudaTopK << endl;
    cerr << "benchmark.fasim_prealign_cuda_max_tasks=" << snapshot.prealignCudaMaxTasks << endl;
    cerr << "benchmark.fasim_prealign_cuda_peak_suppress_bp=" << snapshot.prealignCudaPeakSuppressBp << endl;
    cerr << "benchmark.fasim_prealign_cuda_h2d_seconds=" << snapshot.prealignCudaH2DSeconds << endl;
    cerr << "benchmark.fasim_prealign_cuda_kernel_seconds=" << snapshot.prealignCudaKernelSeconds << endl;
    cerr << "benchmark.fasim_prealign_cuda_d2h_seconds=" << snapshot.prealignCudaD2HSeconds << endl;
    cerr << "benchmark.fasim_prealign_cuda_total_seconds=" << snapshot.prealignCudaTotalSeconds << endl;
    cerr << "benchmark.fasim_extend_threads=" << snapshot.extendThreads << endl;
    cerr << "benchmark.fasim_extend_seconds=" << snapshot.extendSeconds << endl;
    cerr << "benchmark.fasim_extend_candidates=" << snapshot.extendCandidates << endl;
    cerr << "benchmark.fasim_extend_cutlength_attempts=" << snapshot.extendCutlengthAttempts << endl;
    cerr << "benchmark.fasim_extend_align_calls=" << snapshot.extendAlignCalls << endl;
    cerr << "benchmark.fasim_extend_align_cells=" << snapshot.extendAlignCells << endl;
    cerr << "benchmark.fasim_extend_align_seconds=" << snapshot.extendAlignSeconds << endl;
    cerr << "benchmark.fasim_extend_convert_calls=" << snapshot.extendConvertCalls << endl;
    cerr << "benchmark.fasim_extend_convert_seconds=" << snapshot.extendConvertSeconds << endl;
    cerr << "benchmark.fasim_extend_sort_unique_seconds=" << snapshot.extendSortUniqueSeconds << endl;
    cerr << "benchmark.fasim_extend_records_before_filter=" << snapshot.extendRecordsBeforeFilter << endl;
    cerr << "benchmark.fasim_extend_records_emitted=" << snapshot.extendRecordsEmitted << endl;
    cerr << "benchmark.fasim_extend_empty_scoreinfo=" << snapshot.extendEmptyScoreInfo << endl;
    cerr << "benchmark.fasim_align_query_translate_seconds=" << alignerSnapshot.queryTranslateSeconds << endl;
    cerr << "benchmark.fasim_align_ref_translate_seconds=" << alignerSnapshot.refTranslateSeconds << endl;
    cerr << "benchmark.fasim_align_profile_seconds=" << alignerSnapshot.profileSeconds << endl;
    cerr << "benchmark.fasim_align_ssw_total_seconds=" << alignerSnapshot.sswTotalSeconds << endl;
    cerr << "benchmark.fasim_align_forward_score_end_seconds=" << alignerSnapshot.forwardScoreEndSeconds << endl;
    cerr << "benchmark.fasim_align_reverse_start_seconds=" << alignerSnapshot.reverseStartSeconds << endl;
    cerr << "benchmark.fasim_align_traceback_seconds=" << alignerSnapshot.tracebackSeconds << endl;
    cerr << "benchmark.fasim_align_forward_score_gpu_shadow_enabled=" << (alignerSnapshot.forwardScoreGpuShadowEnabled ? 1 : 0) << endl;
    cerr << "benchmark.fasim_align_forward_score_gpu_requests=" << alignerSnapshot.forwardScoreGpuRequests << endl;
    cerr << "benchmark.fasim_align_forward_score_gpu_cells=" << alignerSnapshot.forwardScoreGpuCells << endl;
    cerr << "benchmark.fasim_align_forward_score_gpu_cpu_seconds=" << alignerSnapshot.forwardScoreGpuCpuSeconds << endl;
    cerr << "benchmark.fasim_align_forward_score_gpu_pack_seconds=" << alignerSnapshot.forwardScoreGpuPackSeconds << endl;
    cerr << "benchmark.fasim_align_forward_score_gpu_h2d_seconds=" << alignerSnapshot.forwardScoreGpuH2DSeconds << endl;
    cerr << "benchmark.fasim_align_forward_score_gpu_kernel_seconds=" << alignerSnapshot.forwardScoreGpuKernelSeconds << endl;
    cerr << "benchmark.fasim_align_forward_score_gpu_d2h_seconds=" << alignerSnapshot.forwardScoreGpuD2HSeconds << endl;
    cerr << "benchmark.fasim_align_forward_score_gpu_unpack_seconds=" << alignerSnapshot.forwardScoreGpuUnpackSeconds << endl;
    cerr << "benchmark.fasim_align_forward_score_gpu_total_seconds=" << alignerSnapshot.forwardScoreGpuTotalSeconds << endl;
    cerr << "benchmark.fasim_align_forward_score_gpu_score_mismatches=" << alignerSnapshot.forwardScoreGpuScoreMismatches << endl;
    cerr << "benchmark.fasim_align_forward_score_gpu_endpoint_mismatches=" << alignerSnapshot.forwardScoreGpuEndpointMismatches << endl;
    cerr << "benchmark.fasim_align_forward_score_gpu_unsupported_requests=" << alignerSnapshot.forwardScoreGpuUnsupportedRequests << endl;
    cerr << "benchmark.fasim_forward_score_batch_shadow_enabled=" << (alignerSnapshot.forwardScoreBatchShadowEnabled ? 1 : 0) << endl;
    cerr << "benchmark.fasim_forward_score_batch_requests=" << alignerSnapshot.forwardScoreBatchRequests << endl;
    cerr << "benchmark.fasim_forward_score_batch_cells=" << alignerSnapshot.forwardScoreBatchCells << endl;
    cerr << "benchmark.fasim_forward_score_batch_pack_seconds=" << alignerSnapshot.forwardScoreBatchPackSeconds << endl;
    cerr << "benchmark.fasim_forward_score_batch_h2d_seconds=" << alignerSnapshot.forwardScoreBatchH2DSeconds << endl;
    cerr << "benchmark.fasim_forward_score_batch_kernel_seconds=" << alignerSnapshot.forwardScoreBatchKernelSeconds << endl;
    cerr << "benchmark.fasim_forward_score_batch_d2h_seconds=" << alignerSnapshot.forwardScoreBatchD2HSeconds << endl;
    cerr << "benchmark.fasim_forward_score_batch_unpack_seconds=" << alignerSnapshot.forwardScoreBatchUnpackSeconds << endl;
    cerr << "benchmark.fasim_forward_score_batch_total_seconds=" << alignerSnapshot.forwardScoreBatchTotalSeconds << endl;
    cerr << "benchmark.fasim_forward_score_batch_cpu_reference_seconds=" << alignerSnapshot.forwardScoreBatchCpuReferenceSeconds << endl;
    cerr << "benchmark.fasim_forward_score_batch_score_mismatches=" << alignerSnapshot.forwardScoreBatchScoreMismatches << endl;
    cerr << "benchmark.fasim_forward_score_batch_endpoint_mismatches=" << alignerSnapshot.forwardScoreBatchEndpointMismatches << endl;
    cerr << "benchmark.fasim_forward_score_batch_unsupported_requests=" << alignerSnapshot.forwardScoreBatchUnsupportedRequests << endl;
    cerr << "benchmark.fasim_score_bridge_shadow_enabled=" << (alignerSnapshot.scoreBridgeShadowEnabled ? 1 : 0) << endl;
    cerr << "benchmark.fasim_score_bridge_requests=" << alignerSnapshot.scoreBridgeRequests << endl;
    cerr << "benchmark.fasim_score_bridge_cells=" << alignerSnapshot.scoreBridgeCells << endl;
    cerr << "benchmark.fasim_score_bridge_groups=" << alignerSnapshot.scoreBridgeGroups << endl;
    cerr << "benchmark.fasim_score_bridge_descriptor_count=" << alignerSnapshot.scoreBridgeDescriptorCount << endl;
    cerr << "benchmark.fasim_score_bridge_descriptor_bytes=" << alignerSnapshot.scoreBridgeDescriptorBytes << endl;
    cerr << "benchmark.fasim_score_bridge_query_buffer_bytes=" << alignerSnapshot.scoreBridgeQueryBufferBytes << endl;
    cerr << "benchmark.fasim_score_bridge_target_buffer_bytes=" << alignerSnapshot.scoreBridgeTargetBufferBytes << endl;
    cerr << "benchmark.fasim_score_bridge_pack_seconds=" << alignerSnapshot.scoreBridgePackSeconds << endl;
    cerr << "benchmark.fasim_score_bridge_h2d_seconds=" << alignerSnapshot.scoreBridgeH2DSeconds << endl;
    cerr << "benchmark.fasim_score_bridge_kernel_seconds=" << alignerSnapshot.scoreBridgeKernelSeconds << endl;
    cerr << "benchmark.fasim_score_bridge_d2h_seconds=" << alignerSnapshot.scoreBridgeD2HSeconds << endl;
    cerr << "benchmark.fasim_score_bridge_unpack_seconds=" << alignerSnapshot.scoreBridgeUnpackSeconds << endl;
    cerr << "benchmark.fasim_score_bridge_total_seconds=" << alignerSnapshot.scoreBridgeTotalSeconds << endl;
    cerr << "benchmark.fasim_score_bridge_cpu_reference_seconds=" << alignerSnapshot.scoreBridgeCpuReferenceSeconds << endl;
    cerr << "benchmark.fasim_score_bridge_score_mismatches=" << alignerSnapshot.scoreBridgeScoreMismatches << endl;
    cerr << "benchmark.fasim_score_bridge_endpoint_mismatches=" << alignerSnapshot.scoreBridgeEndpointMismatches << endl;
    cerr << "benchmark.fasim_score_bridge_unsupported_requests=" << alignerSnapshot.scoreBridgeUnsupportedRequests << endl;
    cerr << "benchmark.fasim_align_convert_seconds=" << alignerSnapshot.convertSeconds << endl;
    cerr << "benchmark.fasim_align_cleanup_seconds=" << alignerSnapshot.cleanupSeconds << endl;
    cerr << "benchmark.fasim_align_calls=" << alignerSnapshot.alignCalls << endl;
    cerr << "benchmark.fasim_align_byte_forward_calls=" << alignerSnapshot.byteForwardCalls << endl;
    cerr << "benchmark.fasim_align_word_forward_calls=" << alignerSnapshot.wordForwardCalls << endl;
    cerr << "benchmark.fasim_align_reverse_calls=" << alignerSnapshot.reverseCalls << endl;
    cerr << "benchmark.fasim_align_traceback_calls=" << alignerSnapshot.tracebackCalls << endl;
    cerr << "benchmark.fasim_align_null_results=" << alignerSnapshot.nullResults << endl;
    cerr << "benchmark.fasim_align_profile_reuse_shadow_enabled=" << (alignerSnapshot.profileReuseShadowEnabled ? 1 : 0) << endl;
    cerr << "benchmark.fasim_align_profile_build_calls=" << alignerSnapshot.profileBuildCalls << endl;
    cerr << "benchmark.fasim_align_profile_unique_keys=" << alignerSnapshot.profileUniqueKeys << endl;
    cerr << "benchmark.fasim_align_profile_reusable_calls=" << alignerSnapshot.profileReusableCalls << endl;
    cerr << "benchmark.fasim_align_profile_build_seconds=" << alignerSnapshot.profileBuildSeconds << endl;
    cerr << "benchmark.fasim_align_profile_est_saved_seconds=" << alignerSnapshot.profileEstSavedSeconds << endl;
    cerr << "benchmark.fasim_align_query_unique_keys=" << alignerSnapshot.queryUniqueKeys << endl;
    cerr << "benchmark.fasim_align_query_reusable_calls=" << alignerSnapshot.queryReusableCalls << endl;
    cerr << "benchmark.fasim_align_profile_cache_requested=" << (alignerSnapshot.profileCacheRequested ? 1 : 0) << endl;
    cerr << "benchmark.fasim_align_profile_cache_active=" << (alignerSnapshot.profileCacheActive ? 1 : 0) << endl;
    cerr << "benchmark.fasim_align_profile_cache_validate=" << (alignerSnapshot.profileCacheValidate ? 1 : 0) << endl;
    cerr << "benchmark.fasim_align_profile_cache_calls=" << alignerSnapshot.profileCacheCalls << endl;
    cerr << "benchmark.fasim_align_profile_cache_hits=" << alignerSnapshot.profileCacheHits << endl;
    cerr << "benchmark.fasim_align_profile_cache_misses=" << alignerSnapshot.profileCacheMisses << endl;
    cerr << "benchmark.fasim_align_profile_cache_unique_keys=" << alignerSnapshot.profileCacheUniqueKeys << endl;
    cerr << "benchmark.fasim_align_profile_cache_build_seconds=" << alignerSnapshot.profileCacheBuildSeconds << endl;
    cerr << "benchmark.fasim_align_profile_cache_saved_seconds=" << alignerSnapshot.profileCacheSavedSeconds << endl;
    cerr << "benchmark.fasim_align_profile_cache_validate_seconds=" << alignerSnapshot.profileCacheValidateSeconds << endl;
    cerr << "benchmark.fasim_align_profile_cache_score_mismatches=" << alignerSnapshot.profileCacheScoreMismatches << endl;
    cerr << "benchmark.fasim_align_profile_cache_endpoint_mismatches=" << alignerSnapshot.profileCacheEndpointMismatches << endl;
    cerr << "benchmark.fasim_align_profile_cache_cigar_mismatches=" << alignerSnapshot.profileCacheCigarMismatches << endl;
    cerr << "benchmark.fasim_align_profile_cache_digest_mismatches=" << alignerSnapshot.profileCacheDigestMismatches << endl;
    cerr << "benchmark.fasim_align_profile_cache_fallbacks=" << alignerSnapshot.profileCacheFallbacks << endl;
    cerr << "benchmark.fasim_output_seconds=" << snapshot.outputSeconds << endl;
    cerr << "benchmark.fasim_prealign_cuda_fallbacks=" << snapshot.prealignCudaFallbacks << endl;
    cerr << "benchmark.fasim_prealign_cuda_fallback_unsupported_rule=" << snapshot.prealignCudaFallbackUnsupportedRule << endl;
    cerr << "benchmark.fasim_prealign_cuda_fallback_unsupported_sequence_alphabet=" << snapshot.prealignCudaFallbackUnsupportedSequenceAlphabet << endl;
    cerr << "benchmark.fasim_prealign_cuda_fallback_too_few_tasks=" << snapshot.prealignCudaFallbackTooFewTasks << endl;
    cerr << "benchmark.fasim_prealign_cuda_fallback_too_many_tasks=" << snapshot.prealignCudaFallbackTooManyTasks << endl;
    cerr << "benchmark.fasim_prealign_cuda_fallback_target_too_short=" << snapshot.prealignCudaFallbackTargetTooShort << endl;
    cerr << "benchmark.fasim_prealign_cuda_fallback_query_too_long_or_unsupported=" << snapshot.prealignCudaFallbackQueryTooLongOrUnsupported << endl;
    cerr << "benchmark.fasim_prealign_cuda_fallback_cuda_allocation_or_launch=" << snapshot.prealignCudaFallbackCudaAllocationOrLaunch << endl;
    cerr << "benchmark.fasim_prealign_cuda_fallback_empty_candidate_set=" << snapshot.prealignCudaFallbackEmptyCandidateSet << endl;
    cerr << "benchmark.fasim_prealign_cuda_fallback_unknown=" << snapshot.prealignCudaFallbackUnknown << endl;
    cerr.flags(oldFlags);
    cerr.precision(oldPrecision);
}

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

static inline bool fasim_exact_column_extend_batch_enabled_runtime()
{
    const char *env = getenv("FASIM_EXACT_COLUMN_EXTEND_BATCH");
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
    if(paraList.doFastSim==true)
    cout<<"Searching triplexes using Fasim"<<endl;
    else
    cout<<"Searching triplexes using Sim"<<endl;
    core_num = paraList.corenum;

	lncSeq = readRna(paraList.file2path, lncName);
	fileName = fasim_strip_fasta_extension(fasim_basename(paraList.file1path));
	lncName.erase(remove(lncName.begin(), lncName.end(), '\r'), lncName.end());
	lncName.erase(remove(lncName.begin(), lncName.end(), '\n'), lncName.end());
	resultDir = paraList.outpath;

	const FasimOutputMode outputMode = fasim_output_mode_runtime();
	fasim_set_extend_telemetry_callback(fasim_telemetry_add_extend_delta);
	StripedSmithWaterman::ResetAlignerTelemetry();
	fasim_telemetry_set_requested(paraList.doFastSim && fasim_prealign_cuda_enabled_runtime() && prealign_cuda_is_built());
	std::vector<int> exactColumnGuardCudaDevices;
	fasim_cuda_devices_runtime(exactColumnGuardCudaDevices);
	if (fasim_exact_column_multigpu_guard_failed(exactColumnGuardCudaDevices))
	{
		fasim_emit_runtime_telemetry();
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

		bool useCudaBatch = false;
		std::vector<int> cudaDevices;
		std::vector<PreAlignCudaQueryHandle> cudaQueries;
		std::vector<int16_t> queryProfile;
		int cachedSegLen = 0;
		if (paraList.doFastSim && fasim_prealign_cuda_enabled_runtime() && prealign_cuda_is_built())
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
		}

		const int maxTasksPerGpu = fasim_env_int_or_default("FASIM_PREALIGN_CUDA_MAX_TASKS", 4096);
		int maxTasksTotal = useCudaBatch ? (maxTasksPerGpu * static_cast<int>(cudaQueries.size())) : 1;
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
			fasim_telemetry_config(cudaDevices.empty() ? fasim_cuda_device_runtime() : cudaDevices[0],
			                       static_cast<int>(cudaDevices.size()),
			                       topK,
			                       maxTasksPerGpu,
			                       fasim_prealign_peak_suppress_bp_runtime(),
			                       extendThreadCount);

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

			auto write_task_triplexes = [&](const StreamTask &task)
			{
				const FasimTelemetryClock::time_point outputStart = FasimTelemetryClock::now();
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
					continue;
				}

				const int motif = 0;
				const int middle = static_cast<int>((atr.stari + atr.endi) / 2);
				const int center = middle;

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
				}
				fasim_telemetry_add_output_seconds(fasim_elapsed_seconds(outputStart,FasimTelemetryClock::now()));
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
					const bool ok = prealign_cuda_find_topk_column_maxima(cudaQueries[0],
					                                                    encodedTargets.data(),
					                                                    static_cast<int>(tasks.size()),
					                                                    currentTargetLength,
					                                                    topK,
					                                                    &peaks,
					                                                    &batchResult,
					                                                    &cudaError);
						if (!ok)
						{
							fasim_telemetry_add_cuda_fallback(fasim_prealign_cuda_reason_from_error(cudaError));
							useCudaBatch = false;
							maxTasksTotal = 1;
						}
						else
						{
							fasim_telemetry_add_cuda_batch(static_cast<int>(tasks.size()),batchResult);
							if (extendThreadCount <= 1 || tasks.size() <= 1)
							{
							for (size_t t = 0; t < tasks.size(); ++t)
							{
								const StreamTask &task = tasks[t];
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

										const FasimTelemetryClock::time_point outputStart = FasimTelemetryClock::now();
										{
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
										fasim_telemetry_add_output_seconds(fasim_elapsed_seconds(outputStart,FasimTelemetryClock::now()));
									}
								}));
							}
							for (size_t i = 0; i < workers.size(); ++i)
							{
								workers[i].join();
							}
						}

						tasks.clear();
						encodedTargets.clear();
						currentTargetLength = -1;
						return;
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
								fasim_telemetry_add_cuda_batch(static_cast<int>(localCount),batchResult);
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
						FasimPrealignCudaFallbackReason fallbackReason = FASIM_PREALIGN_CUDA_FALLBACK_UNKNOWN;
						for (size_t d = 0; d < cudaDeviceCount; ++d)
						{
							if (chunkCount[d] != 0 && !ok[d])
							{
								fallbackReason = fasim_prealign_cuda_reason_from_error(cudaErrors[d]);
								break;
							}
						}
						fasim_telemetry_add_cuda_fallback(fallbackReason);
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

									const FasimTelemetryClock::time_point outputStart = FasimTelemetryClock::now();
									{
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
									fasim_telemetry_add_output_seconds(fasim_elapsed_seconds(outputStart,FasimTelemetryClock::now()));
								}
							}));
						}

						for (size_t i = 0; i < workers.size(); ++i)
						{
							workers[i].join();
						}

						tasks.clear();
						encodedTargets.clear();
						currentTargetLength = -1;
						return;
					}
				}
			}

			// CPU fallback for this batch.
			for (size_t t = 0; t < tasks.size(); ++t)
			{
				StreamTask &task = tasks[t];
				const int minScore = static_cast<int>(static_cast<double>(calc_score_once(lncSeq, task.seq2, task.dnaStartPos, paraList.rule)) * 0.8);
				taskTriplexes.clear();
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
			std::string seq2 = transferString(seq1, reverseMode, paraMode, rule);
			if (reverseSeq2)
			{
				reverseSeq(seq2);
			}

			if (currentTargetLength < 0)
			{
				currentTargetLength = static_cast<int>(seq2.size());
				encodedTargets.reserve(static_cast<size_t>(maxTasksTotal) * static_cast<size_t>(currentTargetLength));
			}
			if (static_cast<int>(seq2.size()) != currentTargetLength || static_cast<int>(tasks.size()) >= maxTasksTotal)
			{
				flush_batch();
				currentTargetLength = static_cast<int>(seq2.size());
				encodedTargets.reserve(static_cast<size_t>(maxTasksTotal) * static_cast<size_t>(currentTargetLength));
			}

			StreamTask task;
			fasim_apply_src_transform(seq1, srcTransform, task.srcSeq);
			task.seq2.swap(seq2);
			task.chr = chrTag;
			task.recordStartGenome = recordStartGenome;
			task.dnaStartPos = dnaStartPos;
			task.strand = reverseMode;
			task.Para = paraMode;
			task.rule = rule;

			tasks.push_back(std::move(task));

			const std::string &storedSeq2 = tasks.back().seq2;
			for (int k = 0; k < currentTargetLength; ++k)
			{
				encodedTargets.push_back(fasim_encode_base(static_cast<unsigned char>(storedSeq2[static_cast<size_t>(k)])));
			}
		};

		string pendingHeader;
		FasimFastaRecord record;
		while (fasim_read_next_fasta_record(dnaIn, pendingHeader, record))
		{
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
			cutSequence(record.sequence, dnaSequencesVec, dnaSequencesStartPos, paraList.cutLength, paraList.overlapLength, cut_num);

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

		flush_batch();
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
		fasim_emit_runtime_telemetry();
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
	fasim_emit_runtime_telemetry();
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
				fasim_telemetry_config(cudaQuery.device,
				                       1,
				                       topK,
				                       maxTasks,
				                       fasim_prealign_peak_suppress_bp_runtime(),
				                       1);

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
						fasim_telemetry_add_cuda_fallback(fasim_prealign_cuda_reason_from_error(cudaError));
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
					fasim_telemetry_add_cuda_batch(static_cast<int>(tasks.size()),batchResult);

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
				string seq2 = transferString(seq1, reverseMode, paraMode, rule);
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
						string seq2 = transferString(seq1, 0, 1, j + 1);
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
						seq2 = transferString(seq1, 1, 1, j + 1);
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
					string seq2 = transferString(seq1, 0, 1, paraList.rule);
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

					seq2 = transferString(seq1, 1, 1, paraList.rule);
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
						string seq2 = transferString(seq1, 1, -1, j + 1);
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

						seq2 = transferString(seq1, 0, -1, j + 1);
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
					string seq2 = transferString(seq1, 1, -1, paraList.rule);
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
					seq2 = transferString(seq1, 0, -1, paraList.rule);
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
