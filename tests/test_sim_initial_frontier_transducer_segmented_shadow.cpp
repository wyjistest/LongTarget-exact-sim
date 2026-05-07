#include <algorithm>
#include <cerrno>
#include <climits>
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

const char *kArtifactDir = ".tmp/gpu_frontier_segmented_composition_shadow_2026-04-30";

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

struct CaseReport
{
    std::string name;
    size_t summaryCount;
    size_t chunkEvalCount;
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

static void add_stats(SimScanCudaFrontierTransducerShadowStats &target,
                      const SimScanCudaFrontierTransducerShadowStats &source)
{
    target.summaryReplayCount += source.summaryReplayCount;
    target.insertCount += source.insertCount;
    target.evictionCount += source.evictionCount;
    target.revisitCount += source.revisitCount;
    target.sameStartUpdateCount += source.sameStartUpdateCount;
    target.kBoundaryReplacementCount += source.kBoundaryReplacementCount;
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
                                                size_t end)
{
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

static SimScanCudaFrontierTransducerShadowStats cpu_segmented_stats(
    const std::vector<SimScanCudaInitialRunSummary> &summaries,
    int chunkSize)
{
    SimScanCudaFrontierTransducerShadowStats total;
    total.summaryReplayCount = 0;
    total.insertCount = 0;
    total.evictionCount = 0;
    total.revisitCount = 0;
    total.sameStartUpdateCount = 0;
    total.kBoundaryReplacementCount = 0;

    FrontierState incoming;
    incoming.runningMin = 0;
    const size_t safeChunkSize = static_cast<size_t>(chunkSize > 0 ? chunkSize : 1);
    for (size_t begin = 0; begin < summaries.size(); begin += safeChunkSize)
    {
        const size_t end = std::min(begin + safeChunkSize, summaries.size());
        SimScanCudaFrontierTransducerShadowStats chunkStats;
        update_cpu_shadow_stats(incoming, summaries, begin, end, chunkStats);
        add_stats(total, chunkStats);
        incoming = apply_cpu_chunk_transducer(incoming, summaries, begin, end);
    }
    return total;
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

static std::vector<int> chunk_sizes_for_batch()
{
    std::vector<int> sizes;
    const int candidates[] = {1, 2, 3, 5, 7, K - 1, K, K + 1, 256};
    for (size_t i = 0; i < sizeof(candidates) / sizeof(candidates[0]); ++i)
    {
        if (candidates[i] > 0)
        {
            sizes.push_back(candidates[i]);
        }
    }
    return sizes;
}

static void flatten_cases(const std::vector<TestCase> &tests,
                          std::vector<SimScanCudaInitialRunSummary> &summaries,
                          std::vector<int> &runBases,
                          std::vector<int> &runTotals)
{
    summaries.clear();
    runBases.clear();
    runTotals.clear();
    for (size_t i = 0; i < tests.size(); ++i)
    {
        runBases.push_back(static_cast<int>(summaries.size()));
        runTotals.push_back(static_cast<int>(tests[i].summaries.size()));
        summaries.insert(summaries.end(),
                         tests[i].summaries.begin(),
                         tests[i].summaries.end());
    }
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

static SimScanCudaFrontierDigest digest_state_vector_sorted(
    const std::vector<SimScanCudaCandidateState> &states,
    int runningMin)
{
    FrontierState state;
    state.states = sorted_candidate_states(states);
    state.runningMin = runningMin;
    return digest_frontier_state(state);
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

static bool compare_safe_store_digest(const TestCase &test,
                                      const FrontierState &finalFrontier,
                                      std::vector<std::string> &mismatches)
{
    std::vector<SimScanCudaCandidateState> cpuAllStates;
    reduceSimCudaInitialRunSummariesToAllCandidateStates(test.summaries, NULL, cpuAllStates);

    SimCudaPersistentSafeStoreHandle handle;
    double buildSeconds = 0.0;
    double pruneSeconds = 0.0;
    double frontierUploadSeconds = 0.0;
    std::string error;
    if (!sim_scan_cuda_build_persistent_safe_candidate_state_store_from_initial_run_summaries(
            test.summaries,
            finalFrontier.states,
            finalFrontier.runningMin,
            &handle,
            &buildSeconds,
            &pruneSeconds,
            &frontierUploadSeconds,
            &error))
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"kind\":\"safe_store_call\",\"detail\":\"" +
                             json_escape(error) + "\"}");
        return false;
    }

    std::vector<SimScanCudaCandidateState> gpuStates;
    const bool downloadOk = download_persistent_store_states(handle, &gpuStates, &error);
    sim_scan_cuda_release_persistent_safe_candidate_state_store(&handle);
    if (!downloadOk)
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"kind\":\"safe_store_download\",\"detail\":\"" +
                             json_escape(error) + "\"}");
        return false;
    }

    SimKernelContext cpuContext(8192, 8192);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, cpuContext);
    SimCudaPersistentSafeStoreHandle emptyHandle;
    applySimCudaInitialReduceResults(finalFrontier.states,
                                     finalFrontier.runningMin,
                                     cpuAllStates,
                                     emptyHandle,
                                     static_cast<uint64_t>(test.summaries.size()),
                                     cpuContext,
                                     false,
                                     false);

    const SimScanCudaFrontierDigest cpuDigest =
        digest_state_vector_sorted(cpuContext.safeCandidateStateStore.states,
                                   finalFrontier.runningMin);
    const SimScanCudaFrontierDigest gpuDigest =
        digest_state_vector_sorted(gpuStates, finalFrontier.runningMin);
    if (!digests_equal(cpuDigest, gpuDigest))
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"kind\":\"safe_store_digest\",\"cpu\":" +
                             digest_json(cpuDigest) + ",\"gpu\":" +
                             digest_json(gpuDigest) + "}");
        return false;
    }
    return true;
}

static bool analyze_batch(const std::vector<TestCase> &tests,
                          std::vector<CaseReport> &caseReports,
                          std::vector<std::string> &mismatches,
                          double &totalShadowSeconds,
                          size_t &chunkEvalCount)
{
    std::vector<SimScanCudaInitialRunSummary> summaries;
    std::vector<int> runBases;
    std::vector<int> runTotals;
    flatten_cases(tests, summaries, runBases, runTotals);

    bool ok = true;
    std::vector<CaseReport> reports(tests.size());
    for (size_t i = 0; i < tests.size(); ++i)
    {
        reports[i].name = tests[i].name;
        reports[i].summaryCount = tests[i].summaries.size();
        reports[i].chunkEvalCount = 0;
        reports[i].frontierExact = true;
        reports[i].digestExact = true;
        reports[i].statsExact = true;
        reports[i].safeStoreDigestExact = true;
        reports[i].exact = true;
    }

    const std::vector<int> chunkSizes = chunk_sizes_for_batch();
    for (size_t sizeIndex = 0; sizeIndex < chunkSizes.size(); ++sizeIndex)
    {
        const int chunkSize = chunkSizes[sizeIndex];
        std::vector<SimScanCudaFrontierTransducerSegmentedShadowResult> gpuResults;
        double shadowSeconds = 0.0;
        std::string error;
        const bool callOk =
            sim_scan_cuda_reduce_frontier_chunk_transducer_segmented_shadow_for_test(
                summaries,
                runBases,
                runTotals,
                chunkSize,
                &gpuResults,
                &shadowSeconds,
                &error);
        totalShadowSeconds += shadowSeconds;
        if (!callOk)
        {
            mismatches.push_back("{\"kind\":\"gpu_segmented_shadow_call\",\"chunk_size\":" +
                                 std::to_string(chunkSize) + ",\"detail\":\"" +
                                 json_escape(error) + "\"}");
            return false;
        }
        if (gpuResults.size() != tests.size())
        {
            mismatches.push_back("{\"kind\":\"gpu_segmented_shadow_result_count\",\"chunk_size\":" +
                                 std::to_string(chunkSize) + ",\"expected\":" +
                                 std::to_string(tests.size()) + ",\"actual\":" +
                                 std::to_string(gpuResults.size()) + "}");
            return false;
        }

        for (size_t taskIndex = 0; taskIndex < tests.size(); ++taskIndex)
        {
            const FrontierState truth = replay_legacy_ordered(tests[taskIndex].summaries);
            const SimScanCudaFrontierDigest cpuDigest = digest_frontier_state(truth);
            const SimScanCudaFrontierTransducerShadowStats cpuStats =
                cpu_segmented_stats(tests[taskIndex].summaries, chunkSize);

            FrontierState gpuState;
            gpuState.states = gpuResults[taskIndex].candidateStates;
            gpuState.runningMin = gpuResults[taskIndex].runningMin;

            std::string detail;
            size_t slot = 0;
            const bool frontierOk = frontier_states_equal_ordered(gpuState, truth, &detail, &slot);
            const bool digestOk = digests_equal(gpuResults[taskIndex].digest, cpuDigest);
            const bool statsOk = stats_equal(gpuResults[taskIndex].stats, cpuStats);
            reports[taskIndex].frontierExact = reports[taskIndex].frontierExact && frontierOk;
            reports[taskIndex].digestExact = reports[taskIndex].digestExact && digestOk;
            reports[taskIndex].statsExact = reports[taskIndex].statsExact && statsOk;
            const size_t chunksForTask =
                (tests[taskIndex].summaries.size() + static_cast<size_t>(chunkSize) - 1) /
                static_cast<size_t>(chunkSize);
            reports[taskIndex].chunkEvalCount += chunksForTask;
            chunkEvalCount += chunksForTask;

            if (!frontierOk)
            {
                mismatches.push_back("{\"case\":\"" + json_escape(tests[taskIndex].name) +
                                     "\",\"task_id\":" + std::to_string(taskIndex) +
                                     ",\"chunk_size\":" + std::to_string(chunkSize) +
                                     ",\"kind\":\"frontier\",\"first_mismatch_slot\":" +
                                     std::to_string(slot) + ",\"first_mismatch_reason\":\"" +
                                     json_escape(detail) + "\",\"cpu_outgoing_frontier_state\":" +
                                     state_vector_json(truth.states) +
                                     ",\"gpu_outgoing_frontier_state\":" +
                                     state_vector_json(gpuState.states) + "}");
            }
            if (!digestOk)
            {
                mismatches.push_back("{\"case\":\"" + json_escape(tests[taskIndex].name) +
                                     "\",\"task_id\":" + std::to_string(taskIndex) +
                                     ",\"chunk_size\":" + std::to_string(chunkSize) +
                                     ",\"kind\":\"digest\",\"cpu\":" + digest_json(cpuDigest) +
                                     ",\"gpu\":" + digest_json(gpuResults[taskIndex].digest) + "}");
            }
            if (!statsOk)
            {
                mismatches.push_back("{\"case\":\"" + json_escape(tests[taskIndex].name) +
                                     "\",\"task_id\":" + std::to_string(taskIndex) +
                                     ",\"chunk_size\":" + std::to_string(chunkSize) +
                                     ",\"kind\":\"stats\",\"cpu\":" + stats_json(cpuStats) +
                                     ",\"gpu\":" + stats_json(gpuResults[taskIndex].stats) + "}");
            }
            ok = ok && frontierOk && digestOk && statsOk;
        }
    }

    for (size_t taskIndex = 0; taskIndex < tests.size(); ++taskIndex)
    {
        const FrontierState truth = replay_legacy_ordered(tests[taskIndex].summaries);
        const bool safeStoreOk = compare_safe_store_digest(tests[taskIndex], truth, mismatches);
        reports[taskIndex].safeStoreDigestExact = safeStoreOk;
        reports[taskIndex].exact = reports[taskIndex].frontierExact &&
                                   reports[taskIndex].digestExact &&
                                   reports[taskIndex].statsExact &&
                                   reports[taskIndex].safeStoreDigestExact;
        ok = ok && reports[taskIndex].exact;
    }
    caseReports = reports;
    return ok;
}

static bool check_all_zero_segmented_shadow_skips_gpu_work()
{
    const std::vector<SimScanCudaInitialRunSummary> summaries;
    const std::vector<int> runBases(3, 0);
    const std::vector<int> runTotals(3, 0);
    std::vector<SimScanCudaFrontierTransducerSegmentedShadowResult> results;
    double shadowSeconds = -1.0;
    std::string error;
    if (!sim_scan_cuda_reduce_frontier_chunk_transducer_segmented_shadow_for_test(
            summaries,
            runBases,
            runTotals,
            2,
            &results,
            &shadowSeconds,
            &error))
    {
        std::cerr << "all-zero segmented shadow call failed: " << error << "\n";
        return false;
    }
    if (shadowSeconds != 0.0)
    {
        std::cerr << "all-zero segmented shadow should skip GPU timing, got "
                  << shadowSeconds << "\n";
        return false;
    }
    if (results.size() != runTotals.size())
    {
        std::cerr << "all-zero segmented shadow result count expected "
                  << runTotals.size() << ", got " << results.size() << "\n";
        return false;
    }

    FrontierState emptyState;
    emptyState.runningMin = 0;
    const SimScanCudaFrontierDigest emptyDigest = digest_frontier_state(emptyState);
    const SimScanCudaFrontierTransducerShadowStats emptyStats =
        cpu_segmented_stats(summaries, 2);
    for (size_t i = 0; i < results.size(); ++i)
    {
        if (!results[i].candidateStates.empty() || results[i].runningMin != 0)
        {
            std::cerr << "all-zero segmented shadow result " << i
                      << " should have an empty frontier\n";
            return false;
        }
        if (!digests_equal(results[i].digest, emptyDigest))
        {
            std::cerr << "all-zero segmented shadow digest mismatch for result "
                      << i << "\n";
            return false;
        }
        if (!stats_equal(results[i].stats, emptyStats))
        {
            std::cerr << "all-zero segmented shadow stats mismatch for result "
                      << i << "\n";
            return false;
        }
    }
    return true;
}

static bool write_mismatches(const std::vector<std::string> &mismatches)
{
    const std::string path = std::string(kArtifactDir) + "/segmented_shadow_mismatches.jsonl";
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

static bool write_summary_json_to_path(const std::string &path,
                                       const std::vector<CaseReport> &caseReports,
                                       size_t mismatchCount,
                                       size_t chunkEvalCount,
                                       double totalShadowSeconds,
                                       bool ok)
{
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }
    out << "{\n";
    out << "  \"date\":\"2026-04-30\",\n";
    out << "  \"recommended_next_action\":\"gpu_frontier_segmented_composition_shadow\",\n";
    out << "  \"gate_1_cpu_reduce_form_oracle\":\"passed\",\n";
    out << "  \"gate_2_adversarial_trace_proof\":\"passed\",\n";
    out << "  \"gate_3a_gpu_local_chunk_shadow\":\"passed\",\n";
    out << "  \"gate_3b_gpu_segmented_composition_shadow\":\"" << (ok ? "passed" : "failed") << "\",\n";
    out << "  \"runtime_frontier_reduce_allowed\":false,\n";
    out << "  \"default_path_changes_allowed\":false,\n";
    out << "  \"safe_store_handoff_keep_opt_in\":true,\n";
    out << "  \"mismatch_count\":" << mismatchCount << ",\n";
    out << "  \"case_count\":" << caseReports.size() << ",\n";
    out << "  \"chunk_eval_count\":" << chunkEvalCount << ",\n";
    out << "  \"shadow_seconds_total\":" << totalShadowSeconds << ",\n";
    out << "  \"cases\":[\n";
    for (size_t i = 0; i < caseReports.size(); ++i)
    {
        const CaseReport &report = caseReports[i];
        out << "    {\"name\":\"" << json_escape(report.name) << "\""
            << ",\"summary_count\":" << report.summaryCount
            << ",\"chunk_eval_count\":" << report.chunkEvalCount
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

static bool write_summary_json(const std::vector<CaseReport> &caseReports,
                               size_t mismatchCount,
                               size_t chunkEvalCount,
                               double totalShadowSeconds,
                               bool ok)
{
    return write_summary_json_to_path(std::string(kArtifactDir) + "/segmented_shadow_summary.json",
                                      caseReports,
                                      mismatchCount,
                                      chunkEvalCount,
                                      totalShadowSeconds,
                                      ok) &&
           write_summary_json_to_path(std::string(kArtifactDir) + "/gpu_shadow_summary.json",
                                      caseReports,
                                      mismatchCount,
                                      chunkEvalCount,
                                      totalShadowSeconds,
                                      ok);
}

static bool write_adversarial_json(bool ok, size_t caseCount)
{
    const std::string path = std::string(kArtifactDir) + "/adversarial_segmented_shadow_summary.json";
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
    out << "  \"multi_task_segment_split\":true,\n";
    out << "  \"all_exact\":" << (ok ? "true" : "false") << ",\n";
    out << "  \"case_count\":" << caseCount << "\n";
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
        << (ok ? "measure_gpu_segmented_shadow_overhead_with_handoff_opt_in" : "fix_gpu_frontier_segmented_composition_shadow_mismatch")
        << "\",\n";
    out << "  \"gate_1_cpu_reduce_form_oracle\":\"passed\",\n";
    out << "  \"gate_2_adversarial_trace_proof\":\"passed\",\n";
    out << "  \"gate_3a_gpu_local_chunk_shadow\":\"passed\",\n";
    out << "  \"gate_3b_gpu_segmented_composition_shadow\":\"" << (ok ? "passed" : "failed") << "\",\n";
    out << "  \"runtime_frontier_reduce_allowed\":false,\n";
    out << "  \"default_path_changes_allowed\":false,\n";
    out << "  \"safe_store_handoff_keep_opt_in\":true\n";
    out << "}\n";
    return true;
}

static bool write_summary_md_to_path(const std::string &path,
                                     bool ok,
                                     size_t mismatchCount)
{
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }
    out << "# GPU Frontier Segmented Composition Shadow\n\n";
    out << "Date: 2026-04-30\n\n";
    out << "- Gate 3a GPU local chunk shadow: passed\n";
    out << "- Gate 3b GPU segmented composition shadow: " << (ok ? "passed" : "failed") << "\n";
    out << "- Runtime frontier reducer: blocked\n";
    out << "- Default path changes: blocked\n";
    out << "- Safe-store handoff: opt-in only\n";
    out << "- Mismatches: " << mismatchCount << "\n";
    return true;
}

static bool write_summary_md(bool ok, size_t mismatchCount)
{
    return write_summary_md_to_path(std::string(kArtifactDir) + "/segmented_shadow_summary.md",
                                    ok,
                                    mismatchCount) &&
           write_summary_md_to_path(std::string(kArtifactDir) + "/gpu_shadow_summary.md",
                                    ok,
                                    mismatchCount);
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
    if (!check_all_zero_segmented_shadow_skips_gpu_work())
    {
        return 1;
    }

    const std::vector<TestCase> tests = make_test_cases();
    std::vector<CaseReport> caseReports;
    std::vector<std::string> mismatches;
    double totalShadowSeconds = 0.0;
    size_t chunkEvalCount = 0;

    bool ok = analyze_batch(tests,
                            caseReports,
                            mismatches,
                            totalShadowSeconds,
                            chunkEvalCount);
    ok = write_mismatches(mismatches) && ok;
    ok = write_summary_json(caseReports,
                            mismatches.size(),
                            chunkEvalCount,
                            totalShadowSeconds,
                            mismatches.empty()) && ok;
    ok = write_adversarial_json(mismatches.empty(), caseReports.size()) && ok;
    ok = write_decision_json(mismatches.empty()) && ok;
    ok = write_summary_md(mismatches.empty(), mismatches.size()) && ok;

    if (!mismatches.empty())
    {
        std::cerr << "frontier segmented composition shadow mismatches: "
                  << mismatches.size() << "\n";
        std::cerr << "see " << kArtifactDir << "/segmented_shadow_mismatches.jsonl\n";
    }
    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
