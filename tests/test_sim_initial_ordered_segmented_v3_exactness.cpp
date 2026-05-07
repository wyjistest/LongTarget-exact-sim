#include <algorithm>
#include <cstring>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "../sim.h"

namespace
{

struct FrontierState
{
    std::vector<SimScanCudaCandidateState> states;
    int runningMin;
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

static FrontierState replay_cpu_ordered(const std::vector<SimScanCudaInitialRunSummary> &summaries)
{
    SimKernelContext context(8192, 8192);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);
    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size()),
                                    context);
    FrontierState state;
    collectSimContextCandidateStates(context, state.states);
    state.runningMin = static_cast<int>(context.runningMin);
    return state;
}

static std::vector<SimScanCudaCandidateState> sorted_states(std::vector<SimScanCudaCandidateState> states)
{
    std::sort(states.begin(), states.end(),
              [](const SimScanCudaCandidateState &lhs, const SimScanCudaCandidateState &rhs) {
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
    return states;
}

static std::string state_string(const SimScanCudaCandidateState &state)
{
    std::ostringstream out;
    out << "{score=" << state.score
        << ",start=(" << state.startI << "," << state.startJ << ")"
        << ",end=(" << state.endI << "," << state.endJ << ")"
        << ",box=(" << state.top << "," << state.bot << ","
        << state.left << "," << state.right << ")}";
    return out.str();
}

static bool expect_frontier_equal(const std::vector<SimScanCudaCandidateState> &actual,
                                  int actualRunningMin,
                                  const FrontierState &expected,
                                  const std::string &label)
{
    if (actualRunningMin != expected.runningMin)
    {
        std::cerr << label << " runningMin expected " << expected.runningMin
                  << ", got " << actualRunningMin << "\n";
        return false;
    }
    if (actual.size() != expected.states.size())
    {
        std::cerr << label << " candidate count expected " << expected.states.size()
                  << ", got " << actual.size() << "\n";
        return false;
    }
    for (size_t i = 0; i < expected.states.size(); ++i)
    {
        if (std::memcmp(&actual[i], &expected.states[i], sizeof(SimScanCudaCandidateState)) != 0)
        {
            std::cerr << label << " candidate[" << i << "] expected "
                      << state_string(expected.states[i]) << ", got "
                      << state_string(actual[i]) << "\n";
            return false;
        }
    }
    return true;
}

static bool contains_start(const std::vector<SimScanCudaCandidateState> &states, uint64_t startCoord)
{
    for (size_t i = 0; i < states.size(); ++i)
    {
        if (simScanCudaCandidateStateStartCoord(states[i]) == startCoord)
        {
            return true;
        }
    }
    return false;
}

static bool expect_safe_store_equal(std::vector<SimScanCudaCandidateState> actual,
                                    std::vector<SimScanCudaCandidateState> expected,
                                    const std::string &label)
{
    actual = sorted_states(actual);
    expected = sorted_states(expected);
    if (actual.size() != expected.size())
    {
        std::cerr << label << " safe-store count expected " << expected.size()
                  << ", got " << actual.size() << "\n";
        return false;
    }
    for (size_t i = 0; i < expected.size(); ++i)
    {
        if (std::memcmp(&actual[i], &expected[i], sizeof(SimScanCudaCandidateState)) != 0)
        {
            std::cerr << label << " safe-store[" << i << "] expected "
                      << state_string(expected[i]) << ", got "
                      << state_string(actual[i]) << "\n";
            return false;
        }
    }
    return true;
}

static std::vector<SimScanCudaCandidateState> expected_pruned_safe_store(
    const std::vector<SimScanCudaInitialRunSummary> &summaries,
    const FrontierState &frontier)
{
    std::vector<SimScanCudaCandidateState> allStates;
    reduceSimCudaInitialRunSummariesToAllCandidateStates(summaries, NULL, allStates);
    std::vector<SimScanCudaCandidateState> kept;
    for (size_t i = 0; i < allStates.size(); ++i)
    {
        const uint64_t startCoord = simScanCudaCandidateStateStartCoord(allStates[i]);
        if (allStates[i].score > frontier.runningMin || contains_start(frontier.states, startCoord))
        {
            kept.push_back(allStates[i]);
        }
    }
    return kept;
}

static std::vector<SimScanCudaInitialRunSummary> make_same_start_boundary_revisit_case()
{
    std::vector<SimScanCudaInitialRunSummary> summaries;
    summaries.push_back(make_summary(40, 9, 9, 1, 100));
    summaries.push_back(make_summary(30, 9, 9, 2, 90, 110, 105));
    for (int offset = 0; offset < K - 1; ++offset)
    {
        summaries.push_back(make_summary(100 + offset,
                                         11,
                                         static_cast<uint32_t>(offset + 1),
                                         1,
                                         static_cast<uint32_t>(500 + offset)));
    }
    summaries.push_back(make_summary(41, 12, 1, 1, 700));
    summaries.push_back(make_summary(42, 9, 9, 3, 300));
    return summaries;
}

static std::vector<SimScanCudaInitialRunSummary> make_same_score_k_boundary_case()
{
    std::vector<SimScanCudaInitialRunSummary> summaries;
    for (int i = 0; i < K; ++i)
    {
        summaries.push_back(make_summary(100,
                                         10,
                                         static_cast<uint32_t>(i + 1),
                                         1,
                                         static_cast<uint32_t>(1000 + i)));
    }
    summaries.push_back(make_summary(100, 20, 1, 1, 2000));
    return summaries;
}

static bool run_case(const std::string &name,
                     const std::vector<SimScanCudaInitialRunSummary> &summaries,
                     bool expectSameStartUpdate,
                     bool expectRevisit,
                     bool expectKBoundaryReplacement)
{
    const FrontierState expected = replay_cpu_ordered(summaries);
    const std::vector<SimScanCudaCandidateState> expectedStore =
        expected_pruned_safe_store(summaries, expected);

    std::vector<SimScanCudaInitialBatchResult> results;
    SimScanCudaBatchResult batchResult;
    std::string error;
    const std::vector<int> runBases(1, 0);
    const std::vector<int> runTotals(1, static_cast<int>(summaries.size()));
    if (!sim_scan_cuda_reduce_initial_ordered_segmented_v3_for_test(summaries,
                                                                    runBases,
                                                                    runTotals,
                                                                    &results,
                                                                    &batchResult,
                                                                    &error))
    {
        std::cerr << name << " ordered_segmented_v3 reducer failed: " << error << "\n";
        return false;
    }
    if (results.size() != 1)
    {
        std::cerr << name << " expected one result, got " << results.size() << "\n";
        return false;
    }

    bool ok = true;
    std::vector<SimScanCudaFrontierTransducerSegmentedShadowResult> shadowResults;
    double shadowSeconds = 0.0;
    error.clear();
    if (!sim_scan_cuda_reduce_frontier_chunk_transducer_segmented_shadow_for_test(
            summaries,
            runBases,
            runTotals,
            8,
            &shadowResults,
            &shadowSeconds,
            &error))
    {
        std::cerr << name << " ordered_segmented_v3 shadow failed: " << error << "\n";
        ok = false;
    }
    else if (shadowResults.size() != 1)
    {
        std::cerr << name << " expected one shadow result, got "
                  << shadowResults.size() << "\n";
        ok = false;
    }
    else
    {
        const SimScanCudaFrontierTransducerSegmentedShadowResult &shadow =
            shadowResults[0];
        ok = expect_frontier_equal(shadow.candidateStates,
                                   shadow.runningMin,
                                   expected,
                                   name + " shadow") && ok;
        if (expectSameStartUpdate && shadow.stats.sameStartUpdateCount == 0)
        {
            std::cerr << name << " expected same-start updates in v3 shadow stats\n";
            ok = false;
        }
        if (expectRevisit && shadow.stats.revisitCount == 0)
        {
            std::cerr << name << " expected revisit updates in v3 shadow stats\n";
            ok = false;
        }
        if (expectKBoundaryReplacement && shadow.stats.kBoundaryReplacementCount == 0)
        {
            std::cerr << name << " expected K-boundary replacements in v3 shadow stats\n";
            ok = false;
        }
    }

    ok = expect_frontier_equal(results[0].candidateStates,
                               results[0].runningMin,
                               expected,
                               name) && ok;
    ok = expect_safe_store_equal(results[0].allCandidateStates,
                                 expectedStore,
                                 name) && ok;
    if (batchResult.initialReduceReplayStats.chunkCount != 0 ||
        batchResult.initialReduceReplayStats.summaryReplayCount != 0)
    {
        std::cerr << name
                  << " ordered_segmented_v3 unexpectedly used legacy ordered replay stats"
                  << " chunks=" << batchResult.initialReduceReplayStats.chunkCount
                  << " summaries="
                  << batchResult.initialReduceReplayStats.summaryReplayCount << "\n";
        ok = false;
    }
    ok = batchResult.usedInitialSegmentedReducePath && ok;
    ok = batchResult.initialSegmentedGroupedStateCount <=
         batchResult.initialSegmentedTileStateCount && ok;
    return ok;
}

static bool check_empty_spans_skip_ordered_segmented_v3_gpu_work()
{
    const std::vector<SimScanCudaInitialRunSummary> summaries = {
        make_summary(17, 3, 4, 5, 6),
        make_summary(18, 7, 8, 9, 10)
    };
    const std::vector<int> runBases(3, 0);
    const std::vector<int> runTotals(3, 0);
    std::vector<SimScanCudaInitialBatchResult> results;
    SimScanCudaBatchResult batchResult;
    std::string error;
    if (!sim_scan_cuda_reduce_initial_ordered_segmented_v3_for_test(summaries,
                                                                    runBases,
                                                                    runTotals,
                                                                    &results,
                                                                    &batchResult,
                                                                    &error))
    {
        std::cerr << "empty-span ordered_segmented_v3 reducer failed: "
                  << error << "\n";
        return false;
    }
    bool ok = true;
    if (results.size() != runTotals.size())
    {
        std::cerr << "empty-span ordered_segmented_v3 result count expected "
                  << runTotals.size() << ", got " << results.size() << "\n";
        return false;
    }
    for (size_t i = 0; i < results.size(); ++i)
    {
        const std::string label = "empty-span ordered_segmented_v3 result " +
                                  std::to_string(i);
        if (results[i].eventCount != 0 || results[i].runSummaryCount != 0 ||
            results[i].allCandidateStateCount != 0)
        {
            std::cerr << label << " should report zero counts\n";
            ok = false;
        }
        if (!results[i].candidateStates.empty() ||
            !results[i].allCandidateStates.empty() ||
            results[i].runningMin != 0)
        {
            std::cerr << label << " should keep an empty frontier\n";
            ok = false;
        }
    }
    if (!batchResult.usedCuda || !batchResult.usedInitialSegmentedReducePath)
    {
        std::cerr << "empty-span ordered_segmented_v3 should still report the requested path\n";
        ok = false;
    }
    if (batchResult.taskCount != runTotals.size())
    {
        std::cerr << "empty-span ordered_segmented_v3 taskCount expected "
                  << runTotals.size() << ", got " << batchResult.taskCount << "\n";
        ok = false;
    }
    if (batchResult.launchCount != 0)
    {
        std::cerr << "empty-span ordered_segmented_v3 should skip GPU launches, got "
                  << batchResult.launchCount << "\n";
        ok = false;
    }
    if (batchResult.gpuSeconds != 0.0 ||
        batchResult.initialSegmentedReduceSeconds != 0.0 ||
        batchResult.initialOrderedReplaySeconds != 0.0 ||
        batchResult.initialTopKSeconds != 0.0 ||
        batchResult.initialSegmentedCompactSeconds != 0.0)
    {
        std::cerr << "empty-span ordered_segmented_v3 should report zero GPU seconds\n";
        ok = false;
    }
    if (batchResult.initialSegmentedTileStateCount != 0 ||
        batchResult.initialSegmentedGroupedStateCount != 0)
    {
        std::cerr << "empty-span ordered_segmented_v3 should report zero reduced state counts\n";
        ok = false;
    }
    return ok;
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

    bool ok = true;
    ok = run_case("same_start_boundary_revisit",
                  make_same_start_boundary_revisit_case(),
                  true,
                  true,
                  true) && ok;
    ok = run_case("same_score_k_boundary",
                  make_same_score_k_boundary_case(),
                  false,
                  false,
                  true) && ok;
    ok = check_empty_spans_skip_ordered_segmented_v3_gpu_work() && ok;

    if (!ok)
    {
        return 1;
    }
    std::cout << "ok\n";
    return 0;
}
