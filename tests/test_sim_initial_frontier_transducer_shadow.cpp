#include <algorithm>
#include <climits>
#include <cerrno>
#include <cstring>
#include <fstream>
#include <iostream>
#include <set>
#include <sstream>
#include <string>
#include <sys/stat.h>
#include <sys/types.h>
#include <vector>

#include <cuda_runtime.h>

#include "../sim.h"

namespace
{

const char *kArtifactDir = ".tmp/gpu_frontier_chunk_transducer_shadow_2026-04-30";

struct FrontierState
{
    std::vector<SimScanCudaCandidateState> states;
    int runningMin;
};

struct TestCase
{
    std::string name;
    std::vector<SimScanCudaInitialRunSummary> summaries;
};

struct ChunkReport
{
    std::string caseName;
    int chunkSize;
    size_t chunkIndex;
    size_t beginOrdinal;
    size_t endOrdinal;
    size_t incomingCount;
    size_t outgoingCount;
    int cpuRunningMin;
    int gpuRunningMin;
    bool frontierExact;
    bool digestExact;
    bool statsExact;
    bool exact;
};

struct CaseReport
{
    std::string name;
    size_t summaryCount;
    size_t chunkCount;
    bool frontierExact;
    bool digestExact;
    bool statsExact;
    bool safeStoreDigestExact;
    bool exact;
};

static SimScanCudaInitialRunSummary make_summary(int score,
                                                uint32_t startI,
                                                uint32_t startJ,
                                                uint32_t endI,
                                                uint32_t minEndJ,
                                                uint32_t maxEndJ,
                                                uint32_t scoreEndJ)
{
    SimScanCudaInitialRunSummary summary;
    summary.score = score;
    summary.startCoord = packSimCoord(startI, startJ);
    summary.endI = endI;
    summary.minEndJ = minEndJ;
    summary.maxEndJ = maxEndJ;
    summary.scoreEndJ = scoreEndJ;
    return summary;
}

static SimScanCudaInitialRunSummary make_summary(int score,
                                                uint32_t startI,
                                                uint32_t startJ,
                                                uint32_t endI,
                                                uint32_t endJ)
{
    return make_summary(score, startI, startJ, endI, endJ, endJ, endJ);
}

static bool ensure_directory(const char *path)
{
    if (mkdir(path, 0755) == 0)
    {
        return true;
    }
    if (errno == EEXIST)
    {
        return true;
    }
    std::cerr << "mkdir failed for " << path << ": " << std::strerror(errno) << "\n";
    return false;
}

static std::string json_escape(const std::string &value)
{
    std::ostringstream out;
    for (size_t i = 0; i < value.size(); ++i)
    {
        const char ch = value[i];
        switch (ch)
        {
            case '\\': out << "\\\\"; break;
            case '"': out << "\\\""; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default: out << ch; break;
        }
    }
    return out.str();
}

static std::string state_json(const SimScanCudaCandidateState &state)
{
    std::ostringstream out;
    out << "{\"score\":" << state.score
        << ",\"startI\":" << state.startI
        << ",\"startJ\":" << state.startJ
        << ",\"endI\":" << state.endI
        << ",\"endJ\":" << state.endJ
        << ",\"top\":" << state.top
        << ",\"bot\":" << state.bot
        << ",\"left\":" << state.left
        << ",\"right\":" << state.right << "}";
    return out.str();
}

static std::string state_vector_json(const std::vector<SimScanCudaCandidateState> &states)
{
    std::ostringstream out;
    out << "[";
    for (size_t i = 0; i < states.size(); ++i)
    {
        if (i > 0) out << ",";
        out << state_json(states[i]);
    }
    out << "]";
    return out.str();
}

static std::string summaries_json(const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                  size_t begin,
                                  size_t end)
{
    std::ostringstream out;
    out << "[";
    for (size_t i = begin; i < end; ++i)
    {
        if (i > begin) out << ",";
        const SimScanCudaInitialRunSummary &summary = summaries[i];
        out << "{\"ordinal\":" << i
            << ",\"score\":" << summary.score
            << ",\"startI\":" << unpackSimCoordI(summary.startCoord)
            << ",\"startJ\":" << unpackSimCoordJ(summary.startCoord)
            << ",\"endI\":" << summary.endI
            << ",\"minEndJ\":" << summary.minEndJ
            << ",\"maxEndJ\":" << summary.maxEndJ
            << ",\"scoreEndJ\":" << summary.scoreEndJ << "}";
    }
    out << "]";
    return out.str();
}

static bool states_equal(const SimScanCudaCandidateState &lhs,
                         const SimScanCudaCandidateState &rhs)
{
    return std::memcmp(&lhs, &rhs, sizeof(SimScanCudaCandidateState)) == 0;
}

static bool frontier_states_equal_ordered(const FrontierState &actual,
                                          const FrontierState &expected,
                                          std::string *detail,
                                          size_t *slotOut)
{
    if (actual.runningMin != expected.runningMin)
    {
        if (detail != NULL)
        {
            std::ostringstream out;
            out << "runningMin expected " << expected.runningMin << ", got " << actual.runningMin;
            *detail = out.str();
        }
        if (slotOut != NULL) *slotOut = 0;
        return false;
    }
    if (actual.states.size() != expected.states.size())
    {
        if (detail != NULL)
        {
            std::ostringstream out;
            out << "frontier count expected " << expected.states.size()
                << ", got " << actual.states.size();
            *detail = out.str();
        }
        if (slotOut != NULL) *slotOut = 0;
        return false;
    }
    for (size_t i = 0; i < actual.states.size(); ++i)
    {
        if (!states_equal(actual.states[i], expected.states[i]))
        {
            if (detail != NULL)
            {
                std::ostringstream out;
                out << "slot " << i << " expected " << state_json(expected.states[i])
                    << ", got " << state_json(actual.states[i]);
                *detail = out.str();
            }
            if (slotOut != NULL) *slotOut = i;
            return false;
        }
    }
    return true;
}

static std::vector<SimScanCudaCandidateState> sorted_candidate_states(
    const std::vector<SimScanCudaCandidateState> &states)
{
    std::vector<SimScanCudaCandidateState> sorted = states;
    std::sort(sorted.begin(), sorted.end(), [](const SimScanCudaCandidateState &lhs,
                                               const SimScanCudaCandidateState &rhs) {
        const uint64_t lhsStart = simScanCudaCandidateStateStartCoord(lhs);
        const uint64_t rhsStart = simScanCudaCandidateStateStartCoord(rhs);
        if (lhsStart != rhsStart) return lhsStart < rhsStart;
        if (lhs.score != rhs.score) return lhs.score < rhs.score;
        if (lhs.endI != rhs.endI) return lhs.endI < rhs.endI;
        if (lhs.endJ != rhs.endJ) return lhs.endJ < rhs.endJ;
        if (lhs.top != rhs.top) return lhs.top < rhs.top;
        if (lhs.bot != rhs.bot) return lhs.bot < rhs.bot;
        if (lhs.left != rhs.left) return lhs.left < rhs.left;
        return lhs.right < rhs.right;
    });
    return sorted;
}

static FrontierState state_from_context(const SimKernelContext &context)
{
    FrontierState state;
    collectSimContextCandidateStates(context, state.states);
    state.runningMin = static_cast<int>(context.runningMin);
    return state;
}

static FrontierState replay_legacy_ordered(const std::vector<SimScanCudaInitialRunSummary> &summaries)
{
    SimKernelContext context(8192, 8192);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);
    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size()),
                                    context);
    return state_from_context(context);
}

static void update_cpu_shadow_stats(const FrontierState &incoming,
                                    const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                    size_t begin,
                                    size_t end,
                                    SimScanCudaFrontierTransducerShadowStats &stats)
{
    stats.summaryReplayCount = static_cast<uint64_t>(end - begin);
    stats.insertCount = 0;
    stats.evictionCount = 0;
    stats.revisitCount = 0;
    stats.sameStartUpdateCount = 0;
    stats.kBoundaryReplacementCount = 0;

    SimKernelContext context(8192, 8192);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);
    applySimCudaReducedCandidates(incoming.states, incoming.runningMin, context);

    std::set<uint64_t> seenStarts;
    for (size_t i = 0; i < incoming.states.size(); ++i)
    {
        seenStarts.insert(simScanCudaCandidateStateStartCoord(incoming.states[i]));
    }

    for (size_t i = begin; i < end; ++i)
    {
        const SimScanCudaInitialRunSummary &summary = summaries[i];
        const long startI = static_cast<long>(unpackSimCoordI(summary.startCoord));
        const long startJ = static_cast<long>(unpackSimCoordJ(summary.startCoord));
        const long found = findSimCandidateIndex(context.candidateStartIndex, startI, startJ);
        if (found >= 0)
        {
            ++stats.sameStartUpdateCount;
        }
        else
        {
            ++stats.insertCount;
            if (seenStarts.find(summary.startCoord) != seenStarts.end())
            {
                ++stats.revisitCount;
            }
            if (context.candidateCount == K)
            {
                ++stats.evictionCount;
                ++stats.kBoundaryReplacementCount;
            }
        }
        applySimCudaInitialRunSummary(summary, context, NULL);
        seenStarts.insert(summary.startCoord);
    }
}

static FrontierState apply_cpu_chunk_transducer(const FrontierState &incoming,
                                                const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                                size_t begin,
                                                size_t end,
                                                SimScanCudaFrontierTransducerShadowStats *statsOut)
{
    if (statsOut != NULL)
    {
        update_cpu_shadow_stats(incoming, summaries, begin, end, *statsOut);
    }

    SimKernelContext context(8192, 8192);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);
    applySimCudaReducedCandidates(incoming.states, incoming.runningMin, context);
    std::vector<SimScanCudaInitialRunSummary> chunk(summaries.begin() + static_cast<std::ptrdiff_t>(begin),
                                                    summaries.begin() + static_cast<std::ptrdiff_t>(end));
    mergeSimCudaInitialRunSummaries(chunk,
                                    static_cast<uint64_t>(chunk.size()),
                                    context);
    return state_from_context(context);
}

static SimScanCudaFrontierDigest digest_frontier_state(const FrontierState &state)
{
    SimScanCudaFrontierDigest digest;
    resetSimScanCudaFrontierDigest(digest,
                                   static_cast<int>(state.states.size()),
                                   state.runningMin);
    for (size_t i = 0; i < state.states.size(); ++i)
    {
        updateSimScanCudaFrontierDigest(digest,
                                        state.states[i],
                                        static_cast<int>(i));
    }
    return digest;
}

static bool digests_equal(const SimScanCudaFrontierDigest &lhs,
                          const SimScanCudaFrontierDigest &rhs)
{
    return lhs.candidateCount == rhs.candidateCount &&
           lhs.runningMin == rhs.runningMin &&
           lhs.slotOrderHash == rhs.slotOrderHash &&
           lhs.candidateIdentityHash == rhs.candidateIdentityHash &&
           lhs.scoreHash == rhs.scoreHash &&
           lhs.boundsHash == rhs.boundsHash;
}

static bool stats_equal(const SimScanCudaFrontierTransducerShadowStats &lhs,
                        const SimScanCudaFrontierTransducerShadowStats &rhs)
{
    return lhs.summaryReplayCount == rhs.summaryReplayCount &&
           lhs.insertCount == rhs.insertCount &&
           lhs.evictionCount == rhs.evictionCount &&
           lhs.revisitCount == rhs.revisitCount &&
           lhs.sameStartUpdateCount == rhs.sameStartUpdateCount &&
           lhs.kBoundaryReplacementCount == rhs.kBoundaryReplacementCount;
}

static std::string digest_json(const SimScanCudaFrontierDigest &digest)
{
    std::ostringstream out;
    out << "{\"candidateCount\":" << digest.candidateCount
        << ",\"runningMin\":" << digest.runningMin
        << ",\"slotOrderHash\":" << digest.slotOrderHash
        << ",\"candidateIdentityHash\":" << digest.candidateIdentityHash
        << ",\"scoreHash\":" << digest.scoreHash
        << ",\"boundsHash\":" << digest.boundsHash << "}";
    return out.str();
}

static std::string stats_json(const SimScanCudaFrontierTransducerShadowStats &stats)
{
    std::ostringstream out;
    out << "{\"summaryReplayCount\":" << stats.summaryReplayCount
        << ",\"insertCount\":" << stats.insertCount
        << ",\"evictionCount\":" << stats.evictionCount
        << ",\"revisitCount\":" << stats.revisitCount
        << ",\"sameStartUpdateCount\":" << stats.sameStartUpdateCount
        << ",\"kBoundaryReplacementCount\":" << stats.kBoundaryReplacementCount << "}";
    return out.str();
}

static std::vector<int> chunk_sizes_for_case(size_t summaryCount)
{
    std::vector<int> sizes;
    const int candidates[] = {1, 2, 3, 5, 7, K - 1, K, K + 1};
    for (size_t i = 0; i < sizeof(candidates) / sizeof(candidates[0]); ++i)
    {
        if (candidates[i] > 0 &&
            static_cast<size_t>(candidates[i]) <= std::max<size_t>(summaryCount, 1))
        {
            sizes.push_back(candidates[i]);
        }
    }
    sizes.push_back(static_cast<int>(std::max<size_t>(summaryCount, 1)));
    std::sort(sizes.begin(), sizes.end());
    sizes.erase(std::unique(sizes.begin(), sizes.end()), sizes.end());
    return sizes;
}

static TestCase make_production_k_eviction_revisit_case()
{
    TestCase test;
    test.name = "production_k_eviction_revisit";
    test.summaries.push_back(make_summary(40, 9, 9, 1, 100));
    test.summaries.push_back(make_summary(30, 9, 9, 2, 90, 110, 105));
    for (int offset = 0; offset < K - 1; ++offset)
    {
        test.summaries.push_back(make_summary(100 + offset,
                                              11,
                                              static_cast<uint32_t>(offset + 1),
                                              1,
                                              static_cast<uint32_t>(500 + offset)));
    }
    test.summaries.push_back(make_summary(41, 12, 1, 1, 700));
    test.summaries.push_back(make_summary(42, 9, 9, 3, 300));
    return test;
}

static TestCase make_same_score_tie_case()
{
    TestCase test;
    test.name = "same_score_tie";
    test.summaries.push_back(make_summary(30, 7, 7, 1, 70, 72, 71));
    test.summaries.push_back(make_summary(30, 7, 7, 2, 68, 75, 74));
    test.summaries.push_back(make_summary(29, 8, 7, 1, 80));
    return test;
}

static TestCase make_same_start_update_case()
{
    TestCase test;
    test.name = "same_start_update";
    test.summaries.push_back(make_summary(20, 5, 5, 1, 50));
    test.summaries.push_back(make_summary(18, 6, 5, 1, 60));
    test.summaries.push_back(make_summary(25, 5, 5, 2, 45, 55, 47));
    test.summaries.push_back(make_summary(24, 5, 5, 4, 40, 58, 52));
    return test;
}

static TestCase make_k_boundary_case()
{
    TestCase test;
    test.name = "k_boundary_slot_tie";
    for (int i = 0; i < K; ++i)
    {
        test.summaries.push_back(make_summary(100,
                                              10,
                                              static_cast<uint32_t>(i + 1),
                                              1,
                                              static_cast<uint32_t>(1000 + i)));
    }
    test.summaries.push_back(make_summary(100, 20, 1, 1, 2000));
    return test;
}

static TestCase make_row_order_conflict_case()
{
    TestCase test;
    test.name = "row_order_conflict";
    for (int i = 0; i < K; ++i)
    {
        test.summaries.push_back(make_summary(100,
                                              30,
                                              static_cast<uint32_t>(i + 1),
                                              1,
                                              static_cast<uint32_t>(3000 + i)));
    }
    test.summaries.push_back(make_summary(100, 40, 1, 1, 4000));
    test.summaries.push_back(make_summary(100, 40, 2, 1, 4001));
    return test;
}

static TestCase make_block_split_case()
{
    TestCase test;
    test.name = "block_split";
    for (int i = 0; i < K - 1; ++i)
    {
        test.summaries.push_back(make_summary(120 + i,
                                              50,
                                              static_cast<uint32_t>(i + 1),
                                              1,
                                              static_cast<uint32_t>(5000 + i)));
    }
    test.summaries.push_back(make_summary(90, 61, 1, 1, 6100));
    test.summaries.push_back(make_summary(89, 62, 1, 1, 6200));
    test.summaries.push_back(make_summary(130, 61, 1, 2, 6090, 6110, 6105));
    test.summaries.push_back(make_summary(131, 63, 1, 1, 6300));
    return test;
}

static std::vector<TestCase> make_test_cases()
{
    std::vector<TestCase> tests;
    tests.push_back(make_production_k_eviction_revisit_case());
    tests.push_back(make_same_score_tie_case());
    tests.push_back(make_same_start_update_case());
    tests.push_back(make_k_boundary_case());
    tests.push_back(make_block_split_case());
    tests.push_back(make_row_order_conflict_case());
    return tests;
}

static bool download_persistent_store_states(const SimCudaPersistentSafeStoreHandle &handle,
                                             std::vector<SimScanCudaCandidateState> *outStates,
                                             std::string *errorOut)
{
    if (outStates == NULL)
    {
        if (errorOut != NULL) *errorOut = "missing persistent store output";
        return false;
    }
    outStates->clear();
    if (!handle.valid || handle.stateCount == 0)
    {
        return true;
    }
    if (handle.statesDevice == 0)
    {
        if (errorOut != NULL) *errorOut = "persistent store has no device states";
        return false;
    }
    outStates->resize(handle.stateCount);
    const cudaError_t status = cudaMemcpy(outStates->data(),
                                          reinterpret_cast<const void *>(handle.statesDevice),
                                          handle.stateCount * sizeof(SimScanCudaCandidateState),
                                          cudaMemcpyDeviceToHost);
    if (status != cudaSuccess)
    {
        outStates->clear();
        if (errorOut != NULL) *errorOut = cudaGetErrorString(status);
        return false;
    }
    return true;
}

static SimScanCudaFrontierDigest digest_state_vector_sorted(
    const std::vector<SimScanCudaCandidateState> &states,
    int runningMin)
{
    const std::vector<SimScanCudaCandidateState> sorted = sorted_candidate_states(states);
    FrontierState state;
    state.states = sorted;
    state.runningMin = runningMin;
    return digest_frontier_state(state);
}

static bool compare_safe_store_digest(const TestCase &test,
                                      const FrontierState &finalFrontier,
                                      std::vector<std::string> &mismatches)
{
    std::vector<SimScanCudaCandidateState> cpuAllStates;
    reduceSimCudaInitialRunSummariesToAllCandidateStates(test.summaries, NULL, cpuAllStates);

    SimCudaPersistentSafeStoreHandle materializedHandle;
    double buildSeconds = 0.0;
    double pruneSeconds = 0.0;
    double frontierUploadSeconds = 0.0;
    std::string error;
    if (!sim_scan_cuda_build_persistent_safe_candidate_state_store_from_initial_run_summaries(
            test.summaries,
            std::vector<SimScanCudaCandidateState>(),
            INT_MIN,
            &materializedHandle,
            &buildSeconds,
            &pruneSeconds,
            &frontierUploadSeconds,
            &error))
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"kind\":\"safe_store_materialized_call\",\"detail\":\"" +
                             json_escape(error) + "\"}");
        return false;
    }

    std::vector<SimScanCudaCandidateState> gpuAllStates;
    const bool materializedDownloadOk =
        download_persistent_store_states(materializedHandle, &gpuAllStates, &error);
    sim_scan_cuda_release_persistent_safe_candidate_state_store(&materializedHandle);
    if (!materializedDownloadOk)
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"kind\":\"safe_store_materialized_download\",\"detail\":\"" +
                             json_escape(error) + "\"}");
        return false;
    }

    const SimScanCudaFrontierDigest cpuAllDigest =
        digest_state_vector_sorted(cpuAllStates, INT_MIN);
    const SimScanCudaFrontierDigest gpuAllDigest =
        digest_state_vector_sorted(gpuAllStates, INT_MIN);
    if (!digests_equal(cpuAllDigest, gpuAllDigest))
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"kind\":\"safe_store_materialized_digest\",\"cpu\":" +
                             digest_json(cpuAllDigest) + ",\"gpu\":" +
                             digest_json(gpuAllDigest) + "}");
        return false;
    }

    SimCudaPersistentSafeStoreHandle cpuPrunedHandle;
    SimKernelContext cpuPrunedContext(8192, 8192);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, cpuPrunedContext);
    applySimCudaInitialReduceResults(finalFrontier.states,
                                     finalFrontier.runningMin,
                                     cpuAllStates,
                                     cpuPrunedHandle,
                                     static_cast<uint64_t>(test.summaries.size()),
                                     cpuPrunedContext,
                                     false,
                                     false);

    SimCudaPersistentSafeStoreHandle gpuPrunedHandle;
    if (!sim_scan_cuda_build_persistent_safe_candidate_state_store_from_initial_run_summaries(
            test.summaries,
            finalFrontier.states,
            finalFrontier.runningMin,
            &gpuPrunedHandle,
            &buildSeconds,
            &pruneSeconds,
            &frontierUploadSeconds,
            &error))
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"kind\":\"safe_store_pruned_call\",\"detail\":\"" +
                             json_escape(error) + "\"}");
        return false;
    }

    std::vector<SimScanCudaCandidateState> gpuPrunedStates;
    const bool prunedDownloadOk =
        download_persistent_store_states(gpuPrunedHandle, &gpuPrunedStates, &error);
    sim_scan_cuda_release_persistent_safe_candidate_state_store(&gpuPrunedHandle);
    if (!prunedDownloadOk)
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"kind\":\"safe_store_pruned_download\",\"detail\":\"" +
                             json_escape(error) + "\"}");
        return false;
    }

    const SimScanCudaFrontierDigest cpuPrunedDigest =
        digest_state_vector_sorted(cpuPrunedContext.safeCandidateStateStore.states,
                                   finalFrontier.runningMin);
    const SimScanCudaFrontierDigest gpuPrunedDigest =
        digest_state_vector_sorted(gpuPrunedStates, finalFrontier.runningMin);
    if (!digests_equal(cpuPrunedDigest, gpuPrunedDigest))
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"kind\":\"safe_store_pruned_digest\",\"cpu\":" +
                             digest_json(cpuPrunedDigest) + ",\"gpu\":" +
                             digest_json(gpuPrunedDigest) + "}");
        return false;
    }
    return true;
}

static bool analyze_case(const TestCase &test,
                         CaseReport &caseReport,
                         std::vector<ChunkReport> &chunkReports,
                         std::vector<std::string> &mismatches)
{
    bool caseOk = true;
    bool frontierExact = true;
    bool digestExact = true;
    bool statsExact = true;
    size_t totalChunks = 0;

    const std::vector<int> chunkSizes = chunk_sizes_for_case(test.summaries.size());
    for (size_t sizeIndex = 0; sizeIndex < chunkSizes.size(); ++sizeIndex)
    {
        const int chunkSize = chunkSizes[sizeIndex];
        FrontierState incoming;
        incoming.runningMin = 0;
        size_t chunkIndex = 0;
        for (size_t begin = 0; begin < test.summaries.size(); begin += static_cast<size_t>(chunkSize))
        {
            const size_t end = std::min(begin + static_cast<size_t>(chunkSize), test.summaries.size());
            SimScanCudaFrontierTransducerShadowStats cpuStats;
            const FrontierState cpuOutgoing =
                apply_cpu_chunk_transducer(incoming, test.summaries, begin, end, &cpuStats);
            const SimScanCudaFrontierDigest cpuDigest = digest_frontier_state(cpuOutgoing);

            std::vector<SimScanCudaInitialRunSummary> chunk(test.summaries.begin() + static_cast<std::ptrdiff_t>(begin),
                                                            test.summaries.begin() + static_cast<std::ptrdiff_t>(end));
            std::vector<SimScanCudaCandidateState> gpuOutgoingStates;
            int gpuRunningMin = 0;
            SimScanCudaFrontierDigest gpuDigest;
            SimScanCudaFrontierTransducerShadowStats gpuStats;
            std::string error;
            const bool callOk =
                sim_scan_cuda_apply_frontier_chunk_transducer_shadow_for_test(incoming.states,
                                                                              incoming.runningMin,
                                                                              chunk,
                                                                              &gpuOutgoingStates,
                                                                              &gpuRunningMin,
                                                                              &gpuDigest,
                                                                              &gpuStats,
                                                                              &error);

            FrontierState gpuOutgoing;
            gpuOutgoing.states = gpuOutgoingStates;
            gpuOutgoing.runningMin = gpuRunningMin;

            std::string detail;
            size_t mismatchSlot = 0;
            const bool frontierOk =
                callOk &&
                frontier_states_equal_ordered(gpuOutgoing, cpuOutgoing, &detail, &mismatchSlot);
            const bool digestOk = callOk && digests_equal(gpuDigest, cpuDigest);
            const bool statsOk = callOk && stats_equal(gpuStats, cpuStats);
            const bool chunkOk = callOk && frontierOk && digestOk && statsOk;

            if (!callOk)
            {
                mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                                     "\",\"chunk_size\":" + std::to_string(chunkSize) +
                                     ",\"chunk_index\":" + std::to_string(chunkIndex) +
                                     ",\"kind\":\"gpu_shadow_call\",\"detail\":\"" +
                                     json_escape(error) + "\"}");
            }
            if (callOk && !frontierOk)
            {
                std::ostringstream mismatch;
                mismatch << "{\"case\":\"" << json_escape(test.name)
                         << "\",\"chunk_size\":" << chunkSize
                         << ",\"chunk_index\":" << chunkIndex
                         << ",\"first_mismatch_chunk\":" << chunkIndex
                         << ",\"first_mismatch_slot\":" << mismatchSlot
                         << ",\"first_mismatch_reason\":\"" << json_escape(detail) << "\""
                         << ",\"incoming_frontier_state\":" << state_vector_json(incoming.states)
                         << ",\"ordered_summaries\":" << summaries_json(test.summaries, begin, end)
                         << ",\"cpu_outgoing_frontier_state\":" << state_vector_json(cpuOutgoing.states)
                         << ",\"gpu_outgoing_frontier_state\":" << state_vector_json(gpuOutgoing.states)
                         << "}";
                mismatches.push_back(mismatch.str());
            }
            if (callOk && !digestOk)
            {
                mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                                     "\",\"chunk_size\":" + std::to_string(chunkSize) +
                                     ",\"chunk_index\":" + std::to_string(chunkIndex) +
                                     ",\"kind\":\"frontier_digest\",\"cpu\":" +
                                     digest_json(cpuDigest) + ",\"gpu\":" +
                                     digest_json(gpuDigest) + "}");
            }
            if (callOk && !statsOk)
            {
                mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                                     "\",\"chunk_size\":" + std::to_string(chunkSize) +
                                     ",\"chunk_index\":" + std::to_string(chunkIndex) +
                                     ",\"kind\":\"frontier_stats\",\"cpu\":" +
                                     stats_json(cpuStats) + ",\"gpu\":" +
                                     stats_json(gpuStats) + "}");
            }

            ChunkReport report;
            report.caseName = test.name;
            report.chunkSize = chunkSize;
            report.chunkIndex = chunkIndex;
            report.beginOrdinal = begin;
            report.endOrdinal = end;
            report.incomingCount = incoming.states.size();
            report.outgoingCount = gpuOutgoing.states.size();
            report.cpuRunningMin = cpuOutgoing.runningMin;
            report.gpuRunningMin = gpuOutgoing.runningMin;
            report.frontierExact = frontierOk;
            report.digestExact = digestOk;
            report.statsExact = statsOk;
            report.exact = chunkOk;
            chunkReports.push_back(report);

            frontierExact = frontierExact && frontierOk;
            digestExact = digestExact && digestOk;
            statsExact = statsExact && statsOk;
            caseOk = caseOk && chunkOk;
            incoming = cpuOutgoing;
            ++chunkIndex;
            ++totalChunks;
        }

        const FrontierState truth = replay_legacy_ordered(test.summaries);
        std::string finalDetail;
        size_t finalSlot = 0;
        if (!frontier_states_equal_ordered(incoming, truth, &finalDetail, &finalSlot))
        {
            mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                                 "\",\"chunk_size\":" + std::to_string(chunkSize) +
                                 ",\"kind\":\"cpu_composition_truth\",\"detail\":\"" +
                                 json_escape(finalDetail) + "\"}");
            caseOk = false;
            frontierExact = false;
        }
    }

    const FrontierState finalTruth = replay_legacy_ordered(test.summaries);
    const bool safeStoreDigestExact = compare_safe_store_digest(test, finalTruth, mismatches);
    caseOk = caseOk && safeStoreDigestExact;

    caseReport.name = test.name;
    caseReport.summaryCount = test.summaries.size();
    caseReport.chunkCount = totalChunks;
    caseReport.frontierExact = frontierExact;
    caseReport.digestExact = digestExact;
    caseReport.statsExact = statsExact;
    caseReport.safeStoreDigestExact = safeStoreDigestExact;
    caseReport.exact = caseOk;
    return caseOk;
}

static bool write_mismatches(const std::vector<std::string> &mismatches)
{
    const std::string path = std::string(kArtifactDir) + "/gpu_shadow_mismatches.jsonl";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }
    for (size_t i = 0; i < mismatches.size(); ++i)
    {
        out << mismatches[i] << "\n";
    }
    return true;
}

static bool write_summary_json(const std::vector<CaseReport> &caseReports,
                               const std::vector<ChunkReport> &chunkReports,
                               size_t mismatchCount,
                               bool ok)
{
    const std::string path = std::string(kArtifactDir) + "/gpu_shadow_summary.json";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }
    out << "{\n";
    out << "  \"date\":\"2026-04-30\",\n";
    out << "  \"recommended_next_action\":\"gpu_frontier_chunk_transducer_shadow\",\n";
    out << "  \"gate_1_cpu_reduce_form_oracle\":\"passed\",\n";
    out << "  \"gate_2_adversarial_trace_proof\":\"passed\",\n";
    out << "  \"gate_3a_gpu_local_chunk_shadow\":\"" << (ok ? "passed" : "failed") << "\",\n";
    out << "  \"gpu_shadow_allowed\":true,\n";
    out << "  \"runtime_frontier_reduce_allowed\":false,\n";
    out << "  \"default_path_changes_allowed\":false,\n";
    out << "  \"safe_store_handoff_keep_opt_in\":true,\n";
    out << "  \"mismatch_count\":" << mismatchCount << ",\n";
    out << "  \"case_count\":" << caseReports.size() << ",\n";
    out << "  \"chunk_eval_count\":" << chunkReports.size() << ",\n";
    out << "  \"cases\":[\n";
    for (size_t i = 0; i < caseReports.size(); ++i)
    {
        const CaseReport &report = caseReports[i];
        out << "    {\"name\":\"" << json_escape(report.name) << "\""
            << ",\"summary_count\":" << report.summaryCount
            << ",\"chunk_count\":" << report.chunkCount
            << ",\"frontier_exact\":" << (report.frontierExact ? "true" : "false")
            << ",\"digest_exact\":" << (report.digestExact ? "true" : "false")
            << ",\"stats_exact\":" << (report.statsExact ? "true" : "false")
            << ",\"safe_store_digest_exact\":" << (report.safeStoreDigestExact ? "true" : "false")
            << ",\"exact\":" << (report.exact ? "true" : "false") << "}";
        if (i + 1 < caseReports.size()) out << ",";
        out << "\n";
    }
    out << "  ]\n";
    out << "}\n";
    return true;
}

static bool write_adversarial_json(const std::vector<CaseReport> &caseReports,
                                   bool ok)
{
    const std::string path = std::string(kArtifactDir) + "/adversarial_gpu_shadow_summary.json";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }
    out << "{\n";
    out << "  \"production_k_eviction_revisit\":true,\n";
    out << "  \"same_score_tie\":true,\n";
    out << "  \"same_start_update\":true,\n";
    out << "  \"k_boundary\":true,\n";
    out << "  \"block_split\":true,\n";
    out << "  \"row_order_conflict\":true,\n";
    out << "  \"all_exact\":" << (ok ? "true" : "false") << ",\n";
    out << "  \"case_count\":" << caseReports.size() << "\n";
    out << "}\n";
    return true;
}

static bool write_decision_json(bool ok)
{
    const std::string path = std::string(kArtifactDir) + "/decision.json";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }
    out << "{\n";
    out << "  \"recommended_next_action\":\""
        << (ok ? "gpu_frontier_segmented_composition_shadow" : "fix_gpu_frontier_chunk_transducer_shadow_mismatch")
        << "\",\n";
    out << "  \"gate_1_cpu_reduce_form_oracle\":\"passed\",\n";
    out << "  \"gate_2_adversarial_trace_proof\":\"passed\",\n";
    out << "  \"gate_3_gpu_shadow_allowed\":true,\n";
    out << "  \"gate_3a_gpu_local_chunk_shadow\":\"" << (ok ? "passed" : "failed") << "\",\n";
    out << "  \"gate_3b_gpu_segmented_composition_shadow_allowed\":" << (ok ? "true" : "false") << ",\n";
    out << "  \"runtime_frontier_reduce_allowed\":false,\n";
    out << "  \"default_path_changes_allowed\":false,\n";
    out << "  \"safe_store_handoff_keep_opt_in\":true\n";
    out << "}\n";
    return true;
}

static bool write_summary_md(bool ok, size_t mismatchCount)
{
    const std::string path = std::string(kArtifactDir) + "/gpu_shadow_summary.md";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }
    out << "# GPU Frontier Chunk Transducer Shadow\n\n";
    out << "Date: 2026-04-30\n\n";
    out << "- Gate 1 CPU reduce-form oracle: passed\n";
    out << "- Gate 2 adversarial trace proof: passed\n";
    out << "- Gate 3a GPU local chunk shadow: " << (ok ? "passed" : "failed") << "\n";
    out << "- Runtime frontier reducer: blocked\n";
    out << "- Default path changes: blocked\n";
    out << "- Safe-store handoff: opt-in only\n";
    out << "- Mismatches: " << mismatchCount << "\n";
    return true;
}

} // namespace

int main()
{
    if (!sim_scan_cuda_is_built())
    {
        std::cerr << "CUDA support is not built\n";
        return 2;
    }

    std::string error;
    if (!sim_scan_cuda_init(0, &error))
    {
        std::cerr << "sim_scan_cuda_init failed: " << error << "\n";
        return 2;
    }

    if (!ensure_directory(".tmp") || !ensure_directory(kArtifactDir))
    {
        return 1;
    }

    const std::vector<TestCase> tests = make_test_cases();
    std::vector<std::string> mismatches;
    std::vector<CaseReport> caseReports;
    std::vector<ChunkReport> chunkReports;

    bool ok = true;
    for (size_t i = 0; i < tests.size(); ++i)
    {
        CaseReport report;
        const bool caseOk = analyze_case(tests[i], report, chunkReports, mismatches);
        ok = caseOk && ok;
        caseReports.push_back(report);
    }

    ok = write_mismatches(mismatches) && ok;
    ok = write_summary_json(caseReports, chunkReports, mismatches.size(), mismatches.empty()) && ok;
    ok = write_adversarial_json(caseReports, mismatches.empty()) && ok;
    ok = write_decision_json(mismatches.empty()) && ok;
    ok = write_summary_md(mismatches.empty(), mismatches.size()) && ok;

    if (!mismatches.empty())
    {
        std::cerr << "frontier chunk transducer shadow mismatches: " << mismatches.size() << "\n";
        std::cerr << "see " << kArtifactDir << "/gpu_shadow_mismatches.jsonl\n";
    }
    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
