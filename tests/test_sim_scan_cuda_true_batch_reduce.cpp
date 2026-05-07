#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>

#include "../cuda/sim_scan_cuda.h"

namespace
{

static bool expect_true(bool value, const char *label)
{
    if (value)
    {
        return true;
    }
    std::cerr << label << ": expected true, got false\n";
    return false;
}

static bool expect_equal_uint64(uint64_t actual, uint64_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_equal_int(int actual, int expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_summaries_equal(const std::vector<SimScanCudaInitialRunSummary> &actual,
                                   const std::vector<SimScanCudaInitialRunSummary> &expected,
                                   const char *label)
{
    if (actual.size() != expected.size())
    {
        std::cerr << label << ": size mismatch expected "
                  << expected.size() << ", got " << actual.size() << "\n";
        return false;
    }

    for (size_t i = 0; i < actual.size(); ++i)
    {
        if (std::memcmp(&actual[i], &expected[i], sizeof(SimScanCudaInitialRunSummary)) != 0)
        {
            std::cerr << label << ": summary mismatch at index " << i << "\n";
            return false;
        }
    }
    return true;
}

static std::vector<SimScanCudaCandidateState> sorted_candidate_states(const std::vector<SimScanCudaCandidateState> &states)
{
    std::vector<SimScanCudaCandidateState> sorted = states;
    std::sort(sorted.begin(), sorted.end(), [](const SimScanCudaCandidateState &lhs, const SimScanCudaCandidateState &rhs) {
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

static uint64_t pack_coord(uint32_t i, uint32_t j)
{
    return (static_cast<uint64_t>(i) << 32) | static_cast<uint64_t>(j);
}

static bool contains_candidate_start_coord(const std::vector<SimScanCudaCandidateState> &states,
                                           uint64_t startCoord)
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

static std::vector<SimScanCudaCandidateState> prune_safe_store_states(const std::vector<SimScanCudaCandidateState> &states,
                                                                      const std::vector<SimScanCudaCandidateState> &finalCandidates,
                                                                      int runningMin)
{
    std::vector<SimScanCudaCandidateState> kept;
    kept.reserve(states.size());
    for (size_t i = 0; i < states.size(); ++i)
    {
        const SimScanCudaCandidateState &state = states[i];
        const uint64_t startCoord = simScanCudaCandidateStateStartCoord(state);
        if (state.score > runningMin || contains_candidate_start_coord(finalCandidates, startCoord))
        {
            kept.push_back(state);
        }
    }
    return kept;
}

static std::vector<SimScanCudaCandidateState> reduce_all_candidate_states_from_summaries(const std::vector<SimScanCudaInitialRunSummary> &summaries)
{
    std::vector<SimScanCudaCandidateState> reducedStates;
    std::unordered_map<uint64_t, size_t> stateIndexByStartCoord;
    reducedStates.reserve(summaries.size());
    for (size_t i = 0; i < summaries.size(); ++i)
    {
        const SimScanCudaInitialRunSummary &summary = summaries[i];
        const std::unordered_map<uint64_t, size_t>::iterator found = stateIndexByStartCoord.find(summary.startCoord);
        if (found == stateIndexByStartCoord.end())
        {
            SimScanCudaCandidateState candidate;
            initSimScanCudaCandidateStateFromInitialRunSummary(summary, candidate);
            stateIndexByStartCoord[summary.startCoord] = reducedStates.size();
            reducedStates.push_back(candidate);
            continue;
        }
        updateSimScanCudaCandidateStateFromInitialRunSummary(summary,
                                                            reducedStates[found->second]);
    }
    return reducedStates;
}

static void merge_candidate_state(const SimScanCudaCandidateState &source,
                                  SimScanCudaCandidateState &target)
{
    if (target.score < source.score)
    {
        target.score = source.score;
        target.endI = source.endI;
        target.endJ = source.endJ;
    }
    if (target.top > source.top) target.top = source.top;
    if (target.bot < source.bot) target.bot = source.bot;
    if (target.left > source.left) target.left = source.left;
    if (target.right < source.right) target.right = source.right;
}

static std::vector<SimScanCudaCandidateState> aggregate_region_candidate_states_host(
  const std::vector<SimScanCudaRequestResult> &results)
{
    std::vector<SimScanCudaCandidateState> aggregated;
    std::unordered_map<uint64_t, size_t> stateIndexByStartCoord;
    for (size_t resultIndex = 0; resultIndex < results.size(); ++resultIndex)
    {
        const std::vector<SimScanCudaCandidateState> &candidateStates = results[resultIndex].candidateStates;
        for (size_t stateIndex = 0; stateIndex < candidateStates.size(); ++stateIndex)
        {
            const SimScanCudaCandidateState &state = candidateStates[stateIndex];
            const uint64_t startCoord = simScanCudaCandidateStateStartCoord(state);
            const std::unordered_map<uint64_t, size_t>::iterator found =
              stateIndexByStartCoord.find(startCoord);
            if (found == stateIndexByStartCoord.end())
            {
                stateIndexByStartCoord[startCoord] = aggregated.size();
                aggregated.push_back(state);
                continue;
            }
            merge_candidate_state(state, aggregated[found->second]);
        }
    }
    return aggregated;
}

static bool expect_candidate_states_equal(const std::vector<SimScanCudaCandidateState> &actual,
                                          const std::vector<SimScanCudaCandidateState> &expected,
                                          const char *label)
{
    if (actual.size() != expected.size())
    {
        std::cerr << label << ": size mismatch expected "
                  << expected.size() << ", got " << actual.size() << "\n";
        return false;
    }

    const std::vector<SimScanCudaCandidateState> lhs = sorted_candidate_states(actual);
    const std::vector<SimScanCudaCandidateState> rhs = sorted_candidate_states(expected);
    for (size_t i = 0; i < lhs.size(); ++i)
    {
        if (std::memcmp(&lhs[i], &rhs[i], sizeof(SimScanCudaCandidateState)) != 0)
        {
            std::cerr << label << ": state mismatch at index " << i << "\n";
            return false;
        }
    }
    return true;
}

static bool expect_reduce_result_equal(const SimScanCudaInitialBatchResult &actual,
                                       const SimScanCudaInitialBatchResult &expected,
                                       const char *label)
{
    bool ok = true;
    std::string prefix(label);
    ok = expect_equal_uint64(actual.eventCount, expected.eventCount, (prefix + " eventCount").c_str()) && ok;
    ok = expect_equal_uint64(actual.runSummaryCount, expected.runSummaryCount, (prefix + " runSummaryCount").c_str()) && ok;
    ok = expect_equal_uint64(actual.allCandidateStateCount,
                             expected.allCandidateStateCount,
                             (prefix + " allCandidateStateCount").c_str()) && ok;
    ok = expect_equal_int(actual.runningMin, expected.runningMin, (prefix + " runningMin").c_str()) && ok;
    ok = expect_true(actual.initialRunSummaries.empty(), (prefix + " summaries empty").c_str()) && ok;
    ok = expect_candidate_states_equal(actual.candidateStates,
                                       expected.candidateStates,
                                       (prefix + " candidateStates").c_str()) && ok;
    ok = expect_candidate_states_equal(actual.allCandidateStates,
                                       expected.allCandidateStates,
                                       (prefix + " allCandidateStates").c_str()) && ok;
    return ok;
}

static bool expect_proposal_result_equal(const SimScanCudaInitialBatchResult &actual,
                                         const SimScanCudaInitialBatchResult &expected,
                                         const char *label)
{
    bool ok = true;
    std::string prefix(label);
    ok = expect_equal_uint64(actual.eventCount, expected.eventCount, (prefix + " eventCount").c_str()) && ok;
    ok = expect_equal_uint64(actual.runSummaryCount, expected.runSummaryCount, (prefix + " runSummaryCount").c_str()) && ok;
    ok = expect_equal_uint64(actual.allCandidateStateCount,
                             expected.allCandidateStateCount,
                             (prefix + " allCandidateStateCount").c_str()) && ok;
    ok = expect_equal_int(actual.runningMin, expected.runningMin, (prefix + " runningMin").c_str()) && ok;
    ok = expect_true(actual.initialRunSummaries.empty(), (prefix + " summaries empty").c_str()) && ok;
    ok = expect_candidate_states_equal(actual.candidateStates,
                                       expected.candidateStates,
                                       (prefix + " candidateStates").c_str()) && ok;
    ok = expect_true(actual.allCandidateStates.empty(), (prefix + " allCandidateStates empty").c_str()) && ok;
    ok = expect_true(!actual.persistentSafeStoreHandle.valid,
                     (prefix + " persistent store invalid").c_str()) && ok;
    return ok;
}

static bool expect_proposal_residency_result_equal(const SimScanCudaInitialBatchResult &actual,
                                                   const SimScanCudaInitialBatchResult &expected,
                                                   const char *label)
{
    bool ok = true;
    std::string prefix(label);
    ok = expect_equal_uint64(actual.eventCount, expected.eventCount, (prefix + " eventCount").c_str()) && ok;
    ok = expect_equal_uint64(actual.runSummaryCount, expected.runSummaryCount, (prefix + " runSummaryCount").c_str()) && ok;
    ok = expect_equal_uint64(actual.allCandidateStateCount,
                             expected.allCandidateStateCount,
                             (prefix + " allCandidateStateCount").c_str()) && ok;
    ok = expect_equal_int(actual.runningMin, expected.runningMin, (prefix + " runningMin").c_str()) && ok;
    ok = expect_true(actual.initialRunSummaries.empty(), (prefix + " summaries empty").c_str()) && ok;
    ok = expect_candidate_states_equal(actual.candidateStates,
                                       expected.candidateStates,
                                       (prefix + " candidateStates").c_str()) && ok;
    ok = expect_true(actual.allCandidateStates.empty(), (prefix + " allCandidateStates empty").c_str()) && ok;
    ok = expect_true(actual.persistentSafeStoreHandle.valid,
                     (prefix + " persistent store valid").c_str()) && ok;
    return ok;
}

static SimScanCudaInitialBatchResult run_single_initial_reduce(const char *A,
                                                               const char *B,
                                                               int queryLength,
                                                               int targetLength,
                                                               int gapOpen,
                                                               int gapExtend,
                                                               const int scoreMatrix[128][128],
                                                               int eventScoreFloor,
                                                               SimScanCudaBatchResult *batchResultOut = NULL)
{
    SimScanCudaInitialBatchResult result;
    SimScanCudaBatchResult batchResult;
    std::string error;
    if (!sim_scan_cuda_enumerate_initial_events_row_major(A,
                                                          B,
                                                          queryLength,
                                                          targetLength,
                                                          gapOpen,
                                                          gapExtend,
                                                          scoreMatrix,
                                                          eventScoreFloor,
                                                          true,
                                                          false,
                                                          &result.initialRunSummaries,
                                                          &result.candidateStates,
                                                          &result.allCandidateStates,
                                                          &result.allCandidateStateCount,
                                                          &result.runningMin,
                                                          &result.eventCount,
                                                          &result.runSummaryCount,
                                                          &batchResult,
                                                          &error))
    {
        std::cerr << "single initial reduce failed: " << error << "\n";
        std::exit(2);
    }
    if (batchResultOut != NULL)
    {
        *batchResultOut = batchResult;
    }
    return result;
}

static SimScanCudaInitialBatchResult run_single_initial_reduce_residency(const char *A,
                                                                         const char *B,
                                                                         int queryLength,
                                                                         int targetLength,
                                                                         int gapOpen,
                                                                         int gapExtend,
                                                                         const int scoreMatrix[128][128],
                                                                         int eventScoreFloor,
                                                                         SimScanCudaBatchResult *batchResultOut = NULL)
{
    SimScanCudaInitialBatchResult result;
    SimScanCudaBatchResult batchResult;
    std::string error;
    if (!sim_scan_cuda_enumerate_initial_events_row_major(A,
                                                          B,
                                                          queryLength,
                                                          targetLength,
                                                          gapOpen,
                                                          gapExtend,
                                                          scoreMatrix,
                                                          eventScoreFloor,
                                                          true,
                                                          false,
                                                          &result.initialRunSummaries,
                                                          &result.candidateStates,
                                                          &result.allCandidateStates,
                                                          &result.allCandidateStateCount,
                                                          &result.runningMin,
                                                          &result.eventCount,
                                                          &result.runSummaryCount,
                                                          &batchResult,
                                                          &error,
                                                          &result.persistentSafeStoreHandle))
    {
        std::cerr << "single initial reduce residency failed: " << error << "\n";
        std::exit(2);
    }
    if (batchResultOut != NULL)
    {
        *batchResultOut = batchResult;
    }
    return result;
}

static SimScanCudaInitialBatchResult run_single_initial_reduce_backend(const char *backend,
                                                                       const char *A,
                                                                       const char *B,
                                                                       int queryLength,
                                                                       int targetLength,
                                                                       int gapOpen,
                                                                       int gapExtend,
                                                                       const int scoreMatrix[128][128],
                                                                       int eventScoreFloor,
                                                                       SimScanCudaBatchResult *batchResultOut = NULL)
{
    const char *previousBackend = getenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND");
    const bool hadPreviousBackend = previousBackend != NULL;
    const std::string previousBackendValue = hadPreviousBackend ? previousBackend : "";
    const char *previousHash = getenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE");
    const bool hadPreviousHash = previousHash != NULL;
    const std::string previousHashValue = hadPreviousHash ? previousHash : "";

    if (backend != NULL)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND", backend, 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND");
    }
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE");

    const SimScanCudaInitialBatchResult result =
      run_single_initial_reduce(A,
                                B,
                                queryLength,
                                targetLength,
                                gapOpen,
                                gapExtend,
                                scoreMatrix,
                                eventScoreFloor,
                                batchResultOut);

    if (hadPreviousBackend)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND", previousBackendValue.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND");
    }
    if (hadPreviousHash)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE", previousHashValue.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE");
    }
    return result;
}

static std::vector<SimScanCudaInitialRunSummary> run_single_initial_summaries(const char *A,
                                                                              const char *B,
                                                                              int queryLength,
                                                                              int targetLength,
                                                                              int gapOpen,
                                                                              int gapExtend,
                                                                              const int scoreMatrix[128][128],
                                                                              int eventScoreFloor,
                                                                              SimScanCudaBatchResult *batchResultOut = NULL)
{
    std::vector<SimScanCudaInitialRunSummary> summaries;
    SimScanCudaBatchResult batchResult;
    std::vector<SimScanCudaCandidateState> candidateStates;
    std::vector<SimScanCudaCandidateState> allCandidateStates;
    int runningMin = 0;
    uint64_t eventCount = 0;
    uint64_t runSummaryCount = 0;
    std::string error;
    if (!sim_scan_cuda_enumerate_initial_events_row_major(A,
                                                          B,
                                                          queryLength,
                                                          targetLength,
                                                          gapOpen,
                                                          gapExtend,
                                                          scoreMatrix,
                                                          eventScoreFloor,
                                                          false,
                                                          false,
                                                          &summaries,
                                                          &candidateStates,
                                                          &allCandidateStates,
                                                          NULL,
                                                          &runningMin,
                                                          &eventCount,
                                                          &runSummaryCount,
                                                          &batchResult,
                                                          &error))
    {
        std::cerr << "single initial summaries failed: " << error << "\n";
        std::exit(2);
    }
    if (batchResultOut != NULL)
    {
        *batchResultOut = batchResult;
    }
    return summaries;
}

static SimScanCudaInitialBatchResult run_single_initial_proposal(const char *A,
                                                                 const char *B,
                                                                 int queryLength,
                                                                 int targetLength,
                                                                 int gapOpen,
                                                                 int gapExtend,
                                                                 const int scoreMatrix[128][128],
                                                                 int eventScoreFloor,
                                                                 SimScanCudaBatchResult *batchResultOut = NULL)
{
    SimScanCudaInitialBatchResult result;
    SimScanCudaBatchResult batchResult;
    std::string error;
    if (!sim_scan_cuda_enumerate_initial_events_row_major(A,
                                                          B,
                                                          queryLength,
                                                          targetLength,
                                                          gapOpen,
                                                          gapExtend,
                                                          scoreMatrix,
                                                          eventScoreFloor,
                                                          false,
                                                          true,
                                                          &result.initialRunSummaries,
                                                          &result.candidateStates,
                                                          &result.allCandidateStates,
                                                          &result.allCandidateStateCount,
                                                          &result.runningMin,
                                                          &result.eventCount,
                                                          &result.runSummaryCount,
                                                          &batchResult,
                                                          &error))
    {
        std::cerr << "single initial proposal failed: " << error << "\n";
        std::exit(2);
    }
    if (batchResultOut != NULL)
    {
        *batchResultOut = batchResult;
    }
    return result;
}

static SimScanCudaInitialBatchResult run_single_initial_proposal_residency(const char *A,
                                                                           const char *B,
                                                                           int queryLength,
                                                                           int targetLength,
                                                                           int gapOpen,
                                                                           int gapExtend,
                                                                           const int scoreMatrix[128][128],
                                                                           int eventScoreFloor,
                                                                           SimScanCudaBatchResult *batchResultOut = NULL)
{
    SimScanCudaInitialBatchResult result;
    SimScanCudaBatchResult batchResult;
    std::string error;
    if (!sim_scan_cuda_enumerate_initial_events_row_major(A,
                                                          B,
                                                          queryLength,
                                                          targetLength,
                                                          gapOpen,
                                                          gapExtend,
                                                          scoreMatrix,
                                                          eventScoreFloor,
                                                          false,
                                                          true,
                                                          &result.initialRunSummaries,
                                                          &result.candidateStates,
                                                          &result.allCandidateStates,
                                                          &result.allCandidateStateCount,
                                                          &result.runningMin,
                                                          &result.eventCount,
                                                          &result.runSummaryCount,
                                                          &batchResult,
                                                          &error,
                                                          &result.persistentSafeStoreHandle))
    {
        std::cerr << "single initial proposal residency failed: " << error << "\n";
        std::exit(2);
    }
    if (batchResultOut != NULL)
    {
        *batchResultOut = batchResult;
    }
    return result;
}

static SimScanCudaInitialBatchResult run_single_initial_proposal_streaming(const char *A,
                                                                           const char *B,
                                                                           int queryLength,
                                                                           int targetLength,
                                                                           int gapOpen,
                                                                           int gapExtend,
                                                                           const int scoreMatrix[128][128],
                                                                           int eventScoreFloor)
{
    const char *previous = getenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_STREAMING");
    const bool hadPrevious = previous != NULL;
    const std::string previousValue = hadPrevious ? previous : "";
    setenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_STREAMING", "1", 1);
    const SimScanCudaInitialBatchResult result =
      run_single_initial_proposal(A,
                                  B,
                                  queryLength,
                                  targetLength,
                                  gapOpen,
                                  gapExtend,
                                  scoreMatrix,
                                  eventScoreFloor);
    if (hadPrevious)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_STREAMING", previousValue.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_STREAMING");
    }
    return result;
}

static SimScanCudaInitialBatchResult run_single_initial_proposal_online(const char *A,
                                                                        const char *B,
                                                                        int queryLength,
                                                                        int targetLength,
                                                                        int gapOpen,
                                                                        int gapExtend,
                                                                        const int scoreMatrix[128][128],
                                                                        int eventScoreFloor,
                                                                        const char *hashCapacity,
                                                                        SimScanCudaBatchResult *batchResultOut = NULL)
{
    const char *previousOnline = getenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_ONLINE");
    const bool hadPreviousOnline = previousOnline != NULL;
    const std::string previousOnlineValue = hadPreviousOnline ? previousOnline : "";
    const char *previousHash = getenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_HASH_CAPACITY");
    const bool hadPreviousHash = previousHash != NULL;
    const std::string previousHashValue = hadPreviousHash ? previousHash : "";

    setenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_ONLINE", "1", 1);
    if (hashCapacity != NULL)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_HASH_CAPACITY", hashCapacity, 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_HASH_CAPACITY");
    }

    const SimScanCudaInitialBatchResult result =
      run_single_initial_proposal(A,
                                  B,
                                  queryLength,
                                  targetLength,
                                  gapOpen,
                                  gapExtend,
                                  scoreMatrix,
                                  eventScoreFloor,
                                  batchResultOut);

    if (hadPreviousOnline)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_ONLINE", previousOnlineValue.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_ONLINE");
    }
    if (hadPreviousHash)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_HASH_CAPACITY", previousHashValue.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_HASH_CAPACITY");
    }
    return result;
}

static std::vector<SimScanCudaCandidateState> select_proposal_candidate_states(const std::vector<SimScanCudaCandidateState> &allStates,
                                                                               int maxProposalCount)
{
    std::vector<SimScanCudaCandidateState> proposals;
    std::string error;
    if (!sim_scan_cuda_select_top_disjoint_candidate_states(allStates,
                                                            maxProposalCount,
                                                            &proposals,
                                                            &error))
    {
        std::cerr << "proposal helper failed: " << error << "\n";
        std::exit(2);
    }
    return proposals;
}

static SimScanCudaRequestResult run_single_region_reduce_all(const SimScanCudaRequest &request,
                                                             SimScanCudaBatchResult *batchResultOut = NULL)
{
    SimScanCudaRequestResult result;
    SimScanCudaBatchResult batchResult;
    int eventCount = 0;
    std::string error;
    if (!sim_scan_cuda_enumerate_region_events_row_major(request.A,
                                                         request.B,
                                                         request.queryLength,
                                                         request.targetLength,
                                                         request.rowStart,
                                                         request.rowEnd,
                                                         request.colStart,
                                                         request.colEnd,
                                                         request.gapOpen,
                                                         request.gapExtend,
                                                         request.scoreMatrix,
                                                         request.eventScoreFloor,
                                                         request.blockedWords,
                                                         request.blockedWordStart,
                                                         request.blockedWordCount,
                                                         request.blockedWordStride,
                                                         request.reduceCandidates,
                                                         request.reduceAllCandidateStates,
                                                         request.filterStartCoords,
                                                         request.filterStartCoordCount,
                                                         request.seedCandidates,
                                                         request.seedCandidateCount,
                                                         request.seedRunningMin,
                                                         &result.candidateStates,
                                                         &result.runningMin,
                                                         &eventCount,
                                                         &result.runSummaryCount,
                                                         &result.events,
                                                         &result.rowOffsets,
                                                         &batchResult,
                                                         &error))
    {
        std::cerr << "single region reduce-all failed: " << error << "\n";
        std::exit(2);
    }
    result.eventCount = static_cast<uint64_t>(eventCount);
    if (batchResultOut != NULL)
    {
        *batchResultOut = batchResult;
    }
    return result;
}

static std::vector<SimScanCudaRequestResult> run_region_batch_reduce_all(const std::vector<SimScanCudaRequest> &requests,
                                                                         bool enableTrueBatch,
                                                                         SimScanCudaBatchResult *batchResultOut = NULL)
{
    const char *previous = getenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_TRUE_BATCH");
    const bool hadPrevious = previous != NULL;
    const std::string previousValue = hadPrevious ? previous : "";
    if (enableTrueBatch)
    {
        setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_TRUE_BATCH", "1", 1);
    }
    else
    {
        unsetenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_TRUE_BATCH");
    }

    std::vector<SimScanCudaRequestResult> results;
    SimScanCudaBatchResult batchResult;
    std::string error;
    if (!sim_scan_cuda_enumerate_events_row_major_batch(requests, &results, &batchResult, &error))
    {
        std::cerr << "region batch reduce-all failed: " << error << "\n";
        std::exit(2);
    }

    if (hadPrevious)
    {
        setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_TRUE_BATCH", previousValue.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_TRUE_BATCH");
    }

    if (batchResultOut != NULL)
    {
        *batchResultOut = batchResult;
    }
    return results;
}

static SimScanCudaRegionAggregationResult run_region_aggregated_reduce_all(const std::vector<SimScanCudaRequest> &requests,
                                                                           SimScanCudaBatchResult *batchResultOut = NULL)
{
    SimScanCudaRegionAggregationResult result;
    SimScanCudaBatchResult batchResult;
    std::string error;
    if (!sim_scan_cuda_enumerate_region_candidate_states_aggregated(requests,
                                                                    &result,
                                                                    &batchResult,
                                                                    &error))
    {
        std::cerr << "region aggregated reduce-all failed: " << error << "\n";
        std::exit(2);
    }
    if (batchResultOut != NULL)
    {
        *batchResultOut = batchResult;
    }
    return result;
}

static std::vector<SimScanCudaInitialBatchResult> run_true_batch_initial_proposal_v2(const std::vector<SimScanCudaInitialBatchRequest> &requests,
                                                                                      SimScanCudaBatchResult *batchResultOut = NULL)
{
    const char *previous = getenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V2");
    const bool hadPrevious = previous != NULL;
    const std::string previousValue = hadPrevious ? previous : "";
    setenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V2", "1", 1);

    std::vector<SimScanCudaInitialBatchResult> batchResults;
    SimScanCudaBatchResult batchResult;
    std::string error;
    if (!sim_scan_cuda_enumerate_initial_events_row_major_true_batch(requests,
                                                                     &batchResults,
                                                                     &batchResult,
                                                                     &error))
    {
        std::cerr << "proposal true batch v2 failed: " << error << "\n";
        std::exit(2);
    }

    if (hadPrevious)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V2", previousValue.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V2");
    }

    if (batchResultOut != NULL)
    {
        *batchResultOut = batchResult;
    }
    return batchResults;
}

static std::vector<SimScanCudaInitialBatchResult> run_true_batch_initial_summaries(const std::vector<SimScanCudaInitialBatchRequest> &requests,
                                                                                    SimScanCudaBatchResult *batchResultOut = NULL)
{
    std::vector<SimScanCudaInitialBatchResult> batchResults;
    SimScanCudaBatchResult batchResult;
    std::string error;
    if (!sim_scan_cuda_enumerate_initial_events_row_major_true_batch(requests,
                                                                     &batchResults,
                                                                     &batchResult,
                                                                     &error))
    {
        std::cerr << "initial true batch summaries failed: " << error << "\n";
        std::exit(2);
    }

    if (batchResultOut != NULL)
    {
        *batchResultOut = batchResult;
    }
    return batchResults;
}

static std::vector<SimScanCudaInitialBatchResult> run_true_batch_initial_reduce_hash(const std::vector<SimScanCudaInitialBatchRequest> &requests,
                                                                                     const char *hashCapacity,
                                                                                     SimScanCudaBatchResult *batchResultOut = NULL)
{
    const char *previousEnable = getenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE");
    const bool hadPreviousEnable = previousEnable != NULL;
    const std::string previousEnableValue = hadPreviousEnable ? previousEnable : "";
    const char *previousCapacity = getenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_CAPACITY");
    const bool hadPreviousCapacity = previousCapacity != NULL;
    const std::string previousCapacityValue = hadPreviousCapacity ? previousCapacity : "";
    setenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE", "1", 1);
    if (hashCapacity != NULL)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_CAPACITY", hashCapacity, 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_CAPACITY");
    }

    std::vector<SimScanCudaInitialBatchResult> batchResults;
    SimScanCudaBatchResult batchResult;
    std::string error;
    if (!sim_scan_cuda_enumerate_initial_events_row_major_true_batch(requests,
                                                                     &batchResults,
                                                                     &batchResult,
                                                                     &error))
    {
        std::cerr << "initial true batch hash reduce failed: " << error << "\n";
        std::exit(2);
    }

    if (hadPreviousEnable)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE", previousEnableValue.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE");
    }
    if (hadPreviousCapacity)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_CAPACITY", previousCapacityValue.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_CAPACITY");
    }

    if (batchResultOut != NULL)
    {
        *batchResultOut = batchResult;
    }
    return batchResults;
}

static std::vector<SimScanCudaInitialBatchResult> run_true_batch_initial_reduce_backend(
  const std::vector<SimScanCudaInitialBatchRequest> &requests,
  const char *backend,
  SimScanCudaBatchResult *batchResultOut = NULL)
{
    const char *previousBackend = getenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND");
    const bool hadPreviousBackend = previousBackend != NULL;
    const std::string previousBackendValue = hadPreviousBackend ? previousBackend : "";
    const char *previousHash = getenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE");
    const bool hadPreviousHash = previousHash != NULL;
    const std::string previousHashValue = hadPreviousHash ? previousHash : "";

    if (backend != NULL)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND", backend, 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND");
    }
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE");

    std::vector<SimScanCudaInitialBatchResult> batchResults;
    SimScanCudaBatchResult batchResult;
    std::string error;
    if (!sim_scan_cuda_enumerate_initial_events_row_major_true_batch(requests,
                                                                     &batchResults,
                                                                     &batchResult,
                                                                     &error))
    {
        std::cerr << "initial true batch reduce backend failed: " << error << "\n";
        std::exit(2);
    }

    if (hadPreviousBackend)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND", previousBackendValue.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND");
    }
    if (hadPreviousHash)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE", previousHashValue.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE");
    }

    if (batchResultOut != NULL)
    {
        *batchResultOut = batchResult;
    }
    return batchResults;
}

static std::vector<SimScanCudaCandidateState> select_top_disjoint_from_persistent_store(
  const SimCudaPersistentSafeStoreHandle &handle,
  int maxProposalCount)
{
    std::vector<SimScanCudaCandidateState> selectedStates;
    std::string error;
    if (!sim_scan_cuda_select_top_disjoint_candidate_states_from_persistent_store(handle,
                                                                                  maxProposalCount,
                                                                                  &selectedStates,
                                                                                  &error))
    {
        std::cerr << "persistent store top-k select failed: " << error << "\n";
        std::exit(2);
    }
    return selectedStates;
}

static std::vector<SimScanCudaInitialBatchResult> run_true_batch_initial_proposal_v3(const std::vector<SimScanCudaInitialBatchRequest> &requests,
                                                                                      SimScanCudaBatchResult *batchResultOut = NULL)
{
    const char *previous = getenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V3");
    const bool hadPrevious = previous != NULL;
    const std::string previousValue = hadPrevious ? previous : "";
    const char *previousV2 = getenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V2");
    const bool hadPreviousV2 = previousV2 != NULL;
    const std::string previousV2Value = hadPreviousV2 ? previousV2 : "";
    setenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V3", "1", 1);
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V2");

    std::vector<SimScanCudaInitialBatchResult> batchResults;
    SimScanCudaBatchResult batchResult;
    std::string error;
    if (!sim_scan_cuda_enumerate_initial_events_row_major_true_batch(requests,
                                                                     &batchResults,
                                                                     &batchResult,
                                                                     &error))
    {
        std::cerr << "proposal true batch v3 failed: " << error << "\n";
        std::exit(2);
    }

    if (hadPrevious)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V3", previousValue.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V3");
    }
    if (hadPreviousV2)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V2", previousV2Value.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_PROPOSAL_V2");
    }

    if (batchResultOut != NULL)
    {
        *batchResultOut = batchResult;
    }
    return batchResults;
}

} // namespace

int main()
{
    if (!sim_scan_cuda_is_built())
    {
        std::cerr << "CUDA support is not built\n";
        return 2;
    }

    setenv("LONGTARGET_SIM_CUDA_INITIAL_REDUCE_CHUNK_SIZE", "50", 1);

    std::string error;
    if (!sim_scan_cuda_init(0, &error))
    {
        std::cerr << "sim_scan_cuda_init failed: " << error << "\n";
        return 2;
    }

    int scoreMatrix[128][128] = {};
    scoreMatrix['A']['A'] = 5;
    scoreMatrix['C']['C'] = 5;
    scoreMatrix['G']['G'] = 5;
    scoreMatrix['T']['T'] = 5;
    scoreMatrix['A']['C'] = -4;
    scoreMatrix['A']['G'] = -4;
    scoreMatrix['A']['T'] = -4;
    scoreMatrix['C']['A'] = -4;
    scoreMatrix['C']['G'] = -4;
    scoreMatrix['C']['T'] = -4;
    scoreMatrix['G']['A'] = -4;
    scoreMatrix['G']['C'] = -4;
    scoreMatrix['G']['T'] = -4;
    scoreMatrix['T']['A'] = -4;
    scoreMatrix['T']['C'] = -4;
    scoreMatrix['T']['G'] = -4;

    const char *query = "ACGTACGT";
    const char *target0 = "ACGTACGT";
    const char *target1 = "ACGGACGT";
    const int queryLength = 8;
    const int targetLength = 8;
    const int gapOpen = 16;
    const int gapExtend = 4;
    const int eventScoreFloor = 5;

    SimScanCudaInitialBatchRequest request0;
    request0.A = query;
    request0.B = target0;
    request0.queryLength = queryLength;
    request0.targetLength = targetLength;
    request0.gapOpen = gapOpen;
    request0.gapExtend = gapExtend;
    request0.scoreMatrix = scoreMatrix;
    request0.eventScoreFloor = eventScoreFloor;
    request0.reduceCandidates = true;

    SimScanCudaInitialBatchRequest request1 = request0;
    request1.B = target1;

    std::vector<SimScanCudaInitialBatchRequest> requests;
    requests.push_back(request0);
    requests.push_back(request1);

    SimScanCudaInitialBatchRequest summaryRequest0 = request0;
    summaryRequest0.reduceCandidates = false;
    SimScanCudaInitialBatchRequest summaryRequest1 = request1;
    summaryRequest1.reduceCandidates = false;
    std::vector<SimScanCudaInitialBatchRequest> summaryRequests;
    summaryRequests.push_back(summaryRequest0);
    summaryRequests.push_back(summaryRequest1);

    SimScanCudaBatchResult summaryBatchResult;
    const std::vector<SimScanCudaInitialBatchResult> summaryBatchResults =
      run_true_batch_initial_summaries(summaryRequests, &summaryBatchResult);

    std::vector<SimScanCudaInitialBatchResult> batchResults;
    SimScanCudaBatchResult batchResult;
    if (!sim_scan_cuda_enumerate_initial_events_row_major_true_batch(requests,
                                                                     &batchResults,
                                                                     &batchResult,
                                                                     &error))
    {
        std::cerr << "initial true batch reduce failed: " << error << "\n";
        return 2;
    }
    SimScanCudaBatchResult hashReduceBatchResult;
    const std::vector<SimScanCudaInitialBatchResult> hashReduceBatchResults =
      run_true_batch_initial_reduce_hash(requests, NULL, &hashReduceBatchResult);
    SimScanCudaBatchResult segmentedBatchResult;
    const std::vector<SimScanCudaInitialBatchResult> segmentedBatchResults =
      run_true_batch_initial_reduce_backend(requests, "segmented", &segmentedBatchResult);
    SimScanCudaBatchResult orderedSegmentedV3BatchResult;
    const std::vector<SimScanCudaInitialBatchResult> orderedSegmentedV3BatchResults =
      run_true_batch_initial_reduce_backend(requests, "ordered_segmented_v3", &orderedSegmentedV3BatchResult);
    std::vector<SimScanCudaInitialBatchRequest> residencyRequests = requests;
    residencyRequests[0].persistAllCandidateStatesOnDevice = true;
    residencyRequests[1].persistAllCandidateStatesOnDevice = true;
    std::vector<SimScanCudaInitialBatchResult> residencyBatchResults;
    SimScanCudaBatchResult residencyBatchResult;
    if (!sim_scan_cuda_enumerate_initial_events_row_major_true_batch(residencyRequests,
                                                                     &residencyBatchResults,
                                                                     &residencyBatchResult,
                                                                     &error))
    {
        std::cerr << "initial true batch residency failed: " << error << "\n";
        return 2;
    }

    bool ok = true;
    ok = expect_true(batchResult.usedCuda, "batch usedCuda") && ok;
    ok = expect_equal_uint64(batchResult.taskCount, 2, "batch taskCount") && ok;
    ok = expect_equal_uint64(batchResult.launchCount, 1, "batch launchCount") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(batchResults.size()), 2, "batch result count") && ok;
    ok = expect_true(summaryBatchResult.usedInitialDirectSummaryPath,
                     "summary true batch used direct-summary path") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(summaryBatchResults.size()), 2, "summary batch result count") && ok;
    ok = expect_true(hashReduceBatchResult.usedInitialHashReducePath,
                     "hash reduce batch used hash path") && ok;
    ok = expect_true(!hashReduceBatchResult.initialHashReduceFallback,
                     "hash reduce batch no fallback") && ok;
    ok = expect_true(hashReduceBatchResult.initialHashReduceSeconds > 0.0,
                     "hash reduce batch recorded gpu seconds") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(hashReduceBatchResults.size()),
                             2,
                             "hash reduce batch result count") && ok;
    ok = expect_true(segmentedBatchResult.usedInitialSegmentedReducePath,
                     "segmented reduce batch used segmented path") && ok;
    ok = expect_true(!segmentedBatchResult.initialSegmentedFallback,
                     "segmented reduce batch no fallback") && ok;
    ok = expect_true(segmentedBatchResult.initialSegmentedReduceSeconds > 0.0,
                     "segmented reduce batch recorded reduce gpu seconds") && ok;
    ok = expect_true(segmentedBatchResult.initialTopKSeconds > 0.0,
                     "segmented reduce batch recorded top-k gpu seconds") && ok;
    ok = expect_true(segmentedBatchResult.initialOrderedReplaySeconds > 0.0,
                     "segmented reduce batch recorded ordered replay gpu seconds") && ok;
    ok = expect_true(segmentedBatchResult.initialSegmentedCompactSeconds > 0.0,
                     "segmented reduce batch recorded compact gpu seconds") && ok;
    ok = expect_true(segmentedBatchResult.initialSegmentedTileStateCount >=
                       segmentedBatchResult.initialSegmentedGroupedStateCount,
                     "segmented reduce batch tile/grouped count ordering") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(segmentedBatchResults.size()),
                             2,
                             "segmented reduce batch result count") && ok;
    ok = expect_true(orderedSegmentedV3BatchResult.usedInitialSegmentedReducePath,
                     "ordered_segmented_v3 batch used segmented path") && ok;
    ok = expect_true(!orderedSegmentedV3BatchResult.initialSegmentedFallback,
                     "ordered_segmented_v3 batch no fallback") && ok;
    ok = expect_true(orderedSegmentedV3BatchResult.initialSegmentedReduceSeconds > 0.0,
                     "ordered_segmented_v3 batch recorded reduce gpu seconds") && ok;
    ok = expect_true(orderedSegmentedV3BatchResult.initialTopKSeconds > 0.0,
                     "ordered_segmented_v3 batch recorded top-k gpu seconds") && ok;
    ok = expect_true(orderedSegmentedV3BatchResult.initialOrderedReplaySeconds > 0.0,
                     "ordered_segmented_v3 batch recorded ordered replay gpu seconds") && ok;
    ok = expect_true(orderedSegmentedV3BatchResult.initialSegmentedCompactSeconds > 0.0,
                     "ordered_segmented_v3 batch recorded compact gpu seconds") && ok;
    ok = expect_equal_uint64(orderedSegmentedV3BatchResult.initialOrderedSegmentedV3CountClearSkips,
                             static_cast<uint64_t>(requests.size()) * 2,
                             "ordered_segmented_v3 batch count-clear skips") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(orderedSegmentedV3BatchResults.size()),
                             2,
                             "ordered_segmented_v3 batch result count") && ok;
    ok = expect_true(!batchResult.usedInitialDeviceResidencyPath,
                     "baseline batch no device residency path") && ok;
    ok = expect_equal_uint64(batchResult.initialDeviceResidencyRequestCount,
                             0,
                             "baseline batch no device residency requests") && ok;
    ok = expect_true(residencyBatchResult.usedInitialDeviceResidencyPath,
                     "residency batch used device residency path") && ok;
    ok = expect_equal_uint64(residencyBatchResult.initialDeviceResidencyRequestCount,
                             static_cast<uint64_t>(residencyRequests.size()),
                             "residency batch request count") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(residencyBatchResults.size()),
                             static_cast<uint64_t>(residencyRequests.size()),
                             "residency batch result count") && ok;

    const SimScanCudaInitialBatchResult expected0 =
      run_single_initial_reduce(query, target0, queryLength, targetLength, gapOpen, gapExtend, scoreMatrix, eventScoreFloor);
    const SimScanCudaInitialBatchResult expected1 =
      run_single_initial_reduce(query, target1, queryLength, targetLength, gapOpen, gapExtend, scoreMatrix, eventScoreFloor);
    SimScanCudaBatchResult singleHashBatchResult;
    const SimScanCudaInitialBatchResult singleHashResult =
      run_single_initial_reduce_backend("hash",
                                        query,
                                        target0,
                                        queryLength,
                                        targetLength,
                                        gapOpen,
                                        gapExtend,
                                        scoreMatrix,
                                        eventScoreFloor,
                                        &singleHashBatchResult);
    SimScanCudaBatchResult singleSegmentedBatchResult;
    const SimScanCudaInitialBatchResult singleSegmentedResult =
      run_single_initial_reduce_backend("segmented",
                                        query,
                                        target0,
                                        queryLength,
                                        targetLength,
                                        gapOpen,
                                        gapExtend,
                                        scoreMatrix,
                                        eventScoreFloor,
                                        &singleSegmentedBatchResult);
    SimScanCudaBatchResult singleOrderedSegmentedV3BatchResult;
    const SimScanCudaInitialBatchResult singleOrderedSegmentedV3Result =
      run_single_initial_reduce_backend("ordered_segmented_v3",
                                        query,
                                        target0,
                                        queryLength,
                                        targetLength,
                                        gapOpen,
                                        gapExtend,
                                        scoreMatrix,
                                        eventScoreFloor,
                                        &singleOrderedSegmentedV3BatchResult);
    const std::vector<SimScanCudaInitialRunSummary> expectedSummary0 =
      run_single_initial_summaries(query,
                                   target0,
                                   queryLength,
                                   targetLength,
                                   gapOpen,
                                   gapExtend,
                                   scoreMatrix,
                                   eventScoreFloor);
    const std::vector<SimScanCudaInitialRunSummary> expectedSummary1 =
      run_single_initial_summaries(query,
                                   target1,
                                   queryLength,
                                   targetLength,
                                   gapOpen,
                                   gapExtend,
                                   scoreMatrix,
                                   eventScoreFloor);
    SimScanCudaBatchResult singleSummaryBatchResult0;
    SimScanCudaBatchResult singleSummaryBatchResult1;
    const std::vector<SimScanCudaInitialRunSummary> singleSummaryDirect0 =
      run_single_initial_summaries(query,
                                   target0,
                                   queryLength,
                                   targetLength,
                                   gapOpen,
                                   gapExtend,
                                   scoreMatrix,
                                   eventScoreFloor,
                                   &singleSummaryBatchResult0);
    const std::vector<SimScanCudaInitialRunSummary> singleSummaryDirect1 =
      run_single_initial_summaries(query,
                                   target1,
                                   queryLength,
                                   targetLength,
                                   gapOpen,
                                   gapExtend,
                                   scoreMatrix,
                                   eventScoreFloor,
                                   &singleSummaryBatchResult1);
    ok = expect_true(singleSummaryBatchResult0.usedInitialDirectSummaryPath,
                     "single summary 0 used direct-summary path") && ok;
    ok = expect_true(singleSummaryBatchResult1.usedInitialDirectSummaryPath,
                     "single summary 1 used direct-summary path") && ok;

    if (batchResults.size() == 2)
    {
        ok = expect_reduce_result_equal(batchResults[0], expected0, "batch result 0") && ok;
        ok = expect_reduce_result_equal(batchResults[1], expected1, "batch result 1") && ok;
    }
    if (hashReduceBatchResults.size() == 2)
    {
        ok = expect_reduce_result_equal(hashReduceBatchResults[0], expected0, "hash reduce batch result 0") && ok;
        ok = expect_reduce_result_equal(hashReduceBatchResults[1], expected1, "hash reduce batch result 1") && ok;
    }
    if (segmentedBatchResults.size() == 2)
    {
        ok = expect_reduce_result_equal(segmentedBatchResults[0], expected0, "segmented reduce batch result 0") && ok;
        ok = expect_reduce_result_equal(segmentedBatchResults[1], expected1, "segmented reduce batch result 1") && ok;
    }
    if (orderedSegmentedV3BatchResults.size() == 2)
    {
        ok = expect_reduce_result_equal(orderedSegmentedV3BatchResults[0],
                                        expected0,
                                        "ordered_segmented_v3 batch result 0") && ok;
        ok = expect_reduce_result_equal(orderedSegmentedV3BatchResults[1],
                                        expected1,
                                        "ordered_segmented_v3 batch result 1") && ok;
    }
    ok = expect_true(singleHashBatchResult.usedInitialHashReducePath,
                     "single hash backend used hash path") && ok;
    ok = expect_true(!singleHashBatchResult.initialHashReduceFallback,
                     "single hash backend no fallback") && ok;
    ok = expect_true(singleHashBatchResult.initialHashReduceSeconds > 0.0,
                     "single hash backend recorded hash gpu seconds") && ok;
    ok = expect_true(singleHashBatchResult.usedInitialDirectSummaryPath,
                     "single hash backend used batch summary path") && ok;
    ok = expect_equal_uint64(singleHashBatchResult.initialTrueBatchSingleRequestRunBaseBufferEnsureSkips,
                             1,
                             "single hash backend run-base buffer ensure skip") && ok;
    ok = expect_equal_uint64(singleHashBatchResult.initialTrueBatchSingleRequestRunBaseMaterializeSkips,
                             1,
                             "single hash backend run-base materialize skip") && ok;
    ok = expect_reduce_result_equal(singleHashResult,
                                    hashReduceBatchResults[0],
                                    "single hash backend equals batch hash result 0") && ok;
    ok = expect_true(singleSegmentedBatchResult.usedInitialSegmentedReducePath,
                     "single segmented backend used segmented path") && ok;
    ok = expect_true(!singleSegmentedBatchResult.initialSegmentedFallback,
                     "single segmented backend no fallback") && ok;
    ok = expect_true(singleSegmentedBatchResult.initialSegmentedReduceSeconds > 0.0,
                     "single segmented backend recorded reduce gpu seconds") && ok;
    ok = expect_true(singleSegmentedBatchResult.initialTopKSeconds > 0.0,
                     "single segmented backend recorded top-k gpu seconds") && ok;
    ok = expect_true(singleSegmentedBatchResult.initialOrderedReplaySeconds > 0.0,
                     "single segmented backend recorded ordered replay gpu seconds") && ok;
    ok = expect_true(singleSegmentedBatchResult.initialSegmentedCompactSeconds > 0.0,
                     "single segmented backend recorded compact gpu seconds") && ok;
    ok = expect_true(singleSegmentedBatchResult.initialSegmentedGroupedStateCount > 0,
                     "single segmented backend recorded grouped states") && ok;
    ok = expect_true(singleSegmentedBatchResult.initialSegmentedTileStateCount >=
                       singleSegmentedBatchResult.initialSegmentedGroupedStateCount,
                     "single segmented backend tile/grouped count ordering") && ok;
    ok = expect_true(singleSegmentedBatchResult.usedInitialDirectSummaryPath,
                     "single segmented backend used batch summary path") && ok;
    ok = expect_equal_uint64(singleSegmentedBatchResult.initialTrueBatchSingleRequestRunBaseBufferEnsureSkips,
                             1,
                             "single segmented backend run-base buffer ensure skip") && ok;
    ok = expect_equal_uint64(singleSegmentedBatchResult.initialTrueBatchSingleRequestRunBaseMaterializeSkips,
                             1,
                             "single segmented backend run-base materialize skip") && ok;
    ok = expect_summaries_equal(singleSummaryDirect0,
                                expectedSummary0,
                                "single summary direct 0 summaries") && ok;
    ok = expect_summaries_equal(singleSummaryDirect1,
                                expectedSummary1,
                                "single summary direct 1 summaries") && ok;
    ok = expect_reduce_result_equal(singleSegmentedResult,
                                    segmentedBatchResults[0],
                                    "single segmented backend equals batch segmented result 0") && ok;
    ok = expect_true(singleOrderedSegmentedV3BatchResult.usedInitialSegmentedReducePath,
                     "single ordered_segmented_v3 backend used segmented path") && ok;
    ok = expect_true(!singleOrderedSegmentedV3BatchResult.initialSegmentedFallback,
                     "single ordered_segmented_v3 backend no fallback") && ok;
    ok = expect_true(singleOrderedSegmentedV3BatchResult.initialSegmentedReduceSeconds > 0.0,
                     "single ordered_segmented_v3 backend recorded reduce gpu seconds") && ok;
    ok = expect_true(singleOrderedSegmentedV3BatchResult.initialTopKSeconds > 0.0,
                     "single ordered_segmented_v3 backend recorded top-k gpu seconds") && ok;
    ok = expect_true(singleOrderedSegmentedV3BatchResult.initialOrderedReplaySeconds > 0.0,
                     "single ordered_segmented_v3 backend recorded ordered replay gpu seconds") && ok;
    ok = expect_true(singleOrderedSegmentedV3BatchResult.initialSegmentedCompactSeconds > 0.0,
                     "single ordered_segmented_v3 backend recorded compact gpu seconds") && ok;
    ok = expect_equal_uint64(singleOrderedSegmentedV3BatchResult.initialOrderedSegmentedV3CountClearSkips,
                             2,
                             "single ordered_segmented_v3 backend count-clear skips") && ok;
    ok = expect_equal_uint64(singleOrderedSegmentedV3BatchResult.initialTrueBatchSingleRequestRunBaseBufferEnsureSkips,
                             1,
                             "single ordered_segmented_v3 backend run-base buffer ensure skip") && ok;
    ok = expect_equal_uint64(singleOrderedSegmentedV3BatchResult.initialTrueBatchSingleRequestRunBaseMaterializeSkips,
                             1,
                             "single ordered_segmented_v3 backend run-base materialize skip") && ok;
    ok = expect_reduce_result_equal(singleOrderedSegmentedV3Result,
                                    orderedSegmentedV3BatchResults[0],
                                    "single ordered_segmented_v3 backend equals batch result 0") && ok;
    if (residencyBatchResults.size() == 2)
    {
        const int maxProposalCount = 8;
        ok = expect_equal_uint64(residencyBatchResults[0].eventCount,
                                 expected0.eventCount,
                                 "residency batch result 0 eventCount") && ok;
        ok = expect_equal_uint64(residencyBatchResults[1].eventCount,
                                 expected1.eventCount,
                                 "residency batch result 1 eventCount") && ok;
        ok = expect_equal_uint64(residencyBatchResults[0].runSummaryCount,
                                 expected0.runSummaryCount,
                                 "residency batch result 0 runSummaryCount") && ok;
        ok = expect_equal_uint64(residencyBatchResults[1].runSummaryCount,
                                 expected1.runSummaryCount,
                                 "residency batch result 1 runSummaryCount") && ok;
        ok = expect_equal_uint64(residencyBatchResults[0].allCandidateStateCount,
                                 expected0.allCandidateStateCount,
                                 "residency batch result 0 allCandidateStateCount") && ok;
        ok = expect_equal_uint64(residencyBatchResults[1].allCandidateStateCount,
                                 expected1.allCandidateStateCount,
                                 "residency batch result 1 allCandidateStateCount") && ok;
        ok = expect_equal_int(residencyBatchResults[0].runningMin,
                              expected0.runningMin,
                              "residency batch result 0 runningMin") && ok;
        ok = expect_equal_int(residencyBatchResults[1].runningMin,
                              expected1.runningMin,
                              "residency batch result 1 runningMin") && ok;
        ok = expect_true(residencyBatchResults[0].initialRunSummaries.empty(),
                         "residency batch result 0 summaries empty") && ok;
        ok = expect_true(residencyBatchResults[1].initialRunSummaries.empty(),
                         "residency batch result 1 summaries empty") && ok;
        ok = expect_candidate_states_equal(residencyBatchResults[0].candidateStates,
                                           expected0.candidateStates,
                                           "residency batch result 0 candidateStates") && ok;
        ok = expect_candidate_states_equal(residencyBatchResults[1].candidateStates,
                                           expected1.candidateStates,
                                           "residency batch result 1 candidateStates") && ok;
        ok = expect_true(residencyBatchResults[0].allCandidateStates.empty(),
                         "residency batch result 0 allCandidateStates empty") && ok;
        ok = expect_true(residencyBatchResults[1].allCandidateStates.empty(),
                         "residency batch result 1 allCandidateStates empty") && ok;
        ok = expect_true(residencyBatchResults[0].persistentSafeStoreHandle.valid,
                         "residency batch result 0 persistent store valid") && ok;
        ok = expect_true(residencyBatchResults[1].persistentSafeStoreHandle.valid,
                         "residency batch result 1 persistent store valid") && ok;
        std::vector<SimScanCudaCandidateState> expectedTopDisjointStates0;
        error.clear();
        if (!sim_scan_cuda_select_top_disjoint_candidate_states(expected0.allCandidateStates,
                                                                maxProposalCount,
                                                                &expectedTopDisjointStates0,
                                                                &error))
        {
            std::cerr << "host top-k select failed: " << error << "\n";
            return 2;
        }
        const std::vector<SimScanCudaCandidateState> selectedResidencyStates0 =
          select_top_disjoint_from_persistent_store(residencyBatchResults[0].persistentSafeStoreHandle,
                                                    maxProposalCount);
        ok = expect_candidate_states_equal(selectedResidencyStates0,
                                           expectedTopDisjointStates0,
                                           "persistent store top-k equals host selection") && ok;
    }
    if (summaryBatchResults.size() == 2)
    {
        ok = expect_equal_uint64(summaryBatchResults[0].eventCount,
                                 expected0.eventCount,
                                 "summary batch result 0 eventCount") && ok;
        ok = expect_equal_uint64(summaryBatchResults[1].eventCount,
                                 expected1.eventCount,
                                 "summary batch result 1 eventCount") && ok;
        ok = expect_equal_uint64(summaryBatchResults[0].runSummaryCount,
                                 static_cast<uint64_t>(expectedSummary0.size()),
                                 "summary batch result 0 runSummaryCount") && ok;
        ok = expect_equal_uint64(summaryBatchResults[1].runSummaryCount,
                                 static_cast<uint64_t>(expectedSummary1.size()),
                                 "summary batch result 1 runSummaryCount") && ok;
        ok = expect_summaries_equal(summaryBatchResults[0].initialRunSummaries,
                                    expectedSummary0,
                                    "summary batch result 0 summaries") && ok;
        ok = expect_summaries_equal(summaryBatchResults[1].initialRunSummaries,
                                    expectedSummary1,
                                    "summary batch result 1 summaries") && ok;
        ok = expect_true(summaryBatchResults[0].candidateStates.empty(),
                         "summary batch result 0 candidateStates empty") && ok;
        ok = expect_true(summaryBatchResults[1].candidateStates.empty(),
                         "summary batch result 1 candidateStates empty") && ok;
        ok = expect_true(summaryBatchResults[0].allCandidateStates.empty(),
                         "summary batch result 0 allCandidateStates empty") && ok;
        ok = expect_true(summaryBatchResults[1].allCandidateStates.empty(),
                         "summary batch result 1 allCandidateStates empty") && ok;
    }

    const char *emptyTarget = "TTTTTTTT";
    SimScanCudaBatchResult emptySingleResidencyBatchResult;
    const SimScanCudaInitialBatchResult emptySingleResidency =
      run_single_initial_reduce_residency(query,
                                          emptyTarget,
                                          queryLength,
                                          targetLength,
                                          gapOpen,
                                          gapExtend,
                                          scoreMatrix,
                                          eventScoreFloor,
                                          &emptySingleResidencyBatchResult);
    SimScanCudaInitialBatchRequest emptyResidencyRequest = request0;
    emptyResidencyRequest.B = emptyTarget;
    emptyResidencyRequest.persistAllCandidateStatesOnDevice = true;
    std::vector<SimScanCudaInitialBatchRequest> emptyResidencyRequests(1, emptyResidencyRequest);
    std::vector<SimScanCudaInitialBatchResult> emptyResidencyBatchResults;
    SimScanCudaBatchResult emptyResidencyBatchResult;
    if (!sim_scan_cuda_enumerate_initial_events_row_major_true_batch(emptyResidencyRequests,
                                                                     &emptyResidencyBatchResults,
                                                                     &emptyResidencyBatchResult,
                                                                     &error))
    {
        std::cerr << "empty initial true batch residency failed: " << error << "\n";
        return 2;
    }
    ok = expect_true(emptySingleResidencyBatchResult.usedCuda,
                     "empty single residency usedCuda") && ok;
    ok = expect_true(emptyResidencyBatchResult.usedInitialDeviceResidencyPath,
                     "empty residency batch used device residency path") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(emptyResidencyBatchResults.size()),
                             1,
                             "empty residency batch result count") && ok;
    ok = expect_true(emptySingleResidency.candidateStates.empty(),
                     "empty single residency candidateStates empty") && ok;
    ok = expect_true(emptySingleResidency.allCandidateStates.empty(),
                     "empty single residency allCandidateStates empty") && ok;
    ok = expect_equal_uint64(emptySingleResidency.allCandidateStateCount,
                             0,
                             "empty single residency allCandidateStateCount") && ok;
    ok = expect_true(emptySingleResidency.persistentSafeStoreHandle.valid,
                     "empty single residency persistent store valid") && ok;
    if (emptyResidencyBatchResults.size() == 1)
    {
        ok = expect_equal_uint64(emptyResidencyBatchResults[0].eventCount,
                                 emptySingleResidency.eventCount,
                                 "empty residency batch eventCount") && ok;
        ok = expect_equal_uint64(emptyResidencyBatchResults[0].runSummaryCount,
                                 emptySingleResidency.runSummaryCount,
                                 "empty residency batch runSummaryCount") && ok;
        ok = expect_equal_uint64(emptyResidencyBatchResults[0].allCandidateStateCount,
                                 0,
                                 "empty residency batch allCandidateStateCount") && ok;
        ok = expect_equal_int(emptyResidencyBatchResults[0].runningMin,
                              emptySingleResidency.runningMin,
                              "empty residency batch runningMin") && ok;
        ok = expect_true(emptyResidencyBatchResults[0].candidateStates.empty(),
                         "empty residency batch candidateStates empty") && ok;
        ok = expect_true(emptyResidencyBatchResults[0].allCandidateStates.empty(),
                         "empty residency batch allCandidateStates empty") && ok;
        ok = expect_true(emptyResidencyBatchResults[0].persistentSafeStoreHandle.valid,
                         "empty residency batch persistent store valid") && ok;
    }

    const std::string regionQuery(16, 'A');
    const std::string regionTarget(16, 'A');
    std::vector<uint64_t> regionFilterStartCoords;
    regionFilterStartCoords.push_back(pack_coord(1, 1));
    regionFilterStartCoords.push_back(pack_coord(2, 2));
    regionFilterStartCoords.push_back(pack_coord(4, 4));

    SimScanCudaRequest regionRequest0;
    regionRequest0.kind = SIM_SCAN_CUDA_REQUEST_REGION;
    regionRequest0.A = regionQuery.c_str();
    regionRequest0.B = regionTarget.c_str();
    regionRequest0.queryLength = static_cast<int>(regionQuery.size());
    regionRequest0.targetLength = static_cast<int>(regionTarget.size());
    regionRequest0.rowStart = 1;
    regionRequest0.rowEnd = 8;
    regionRequest0.colStart = 1;
    regionRequest0.colEnd = 8;
    regionRequest0.gapOpen = gapOpen;
    regionRequest0.gapExtend = gapExtend;
    regionRequest0.scoreMatrix = scoreMatrix;
    regionRequest0.eventScoreFloor = eventScoreFloor;
    regionRequest0.reduceCandidates = false;
    regionRequest0.reduceAllCandidateStates = true;
    regionRequest0.filterStartCoords = regionFilterStartCoords.data();
    regionRequest0.filterStartCoordCount = static_cast<int>(regionFilterStartCoords.size());
    regionRequest0.seedCandidates = NULL;
    regionRequest0.seedCandidateCount = 0;
    regionRequest0.seedRunningMin = 0;

    SimScanCudaRequest regionRequest1 = regionRequest0;
    regionRequest1.rowStart = 5;
    regionRequest1.rowEnd = 16;
    regionRequest1.colStart = 4;
    regionRequest1.colEnd = 16;

    std::vector<SimScanCudaRequest> regionRequests;
    regionRequests.push_back(regionRequest0);
    regionRequests.push_back(regionRequest1);

    SimScanCudaBatchResult regionBaselineBatchResult;
    const std::vector<SimScanCudaRequestResult> regionBaselineBatchResults =
      run_region_batch_reduce_all(regionRequests, false, &regionBaselineBatchResult);
    ok = expect_true(!regionBaselineBatchResult.usedRegionTrueBatchPath,
                     "region baseline batch does not use true-batch path") && ok;
    ok = expect_equal_uint64(regionBaselineBatchResult.regionTrueBatchRequestCount,
                             0,
                             "region baseline batch true-batch request count") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(regionBaselineBatchResults.size()),
                             static_cast<uint64_t>(regionRequests.size()),
                             "region baseline batch result count") && ok;

    SimScanCudaBatchResult regionTrueBatchResult;
    const std::vector<SimScanCudaRequestResult> regionTrueBatchResults =
      run_region_batch_reduce_all(regionRequests, true, &regionTrueBatchResult);
    ok = expect_true(regionTrueBatchResult.usedRegionTrueBatchPath,
                     "region true batch uses true-batch path") && ok;
    ok = expect_equal_uint64(regionTrueBatchResult.regionTrueBatchRequestCount,
                             static_cast<uint64_t>(regionRequests.size()),
                             "region true batch request count") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(regionTrueBatchResults.size()),
                             static_cast<uint64_t>(regionRequests.size()),
                             "region true batch result count") && ok;

    for (size_t i = 0; i < regionRequests.size() &&
                       i < regionBaselineBatchResults.size() &&
                       i < regionTrueBatchResults.size(); ++i)
    {
        SimScanCudaBatchResult singleRegionBatchResult;
        const SimScanCudaRequestResult singleRegionResult =
          run_single_region_reduce_all(regionRequests[i], &singleRegionBatchResult);
        const std::string labelPrefix = "region batch result " + std::to_string(i);
        ok = expect_equal_uint64(regionBaselineBatchResults[i].eventCount,
                                 singleRegionResult.eventCount,
                                 (labelPrefix + " baseline eventCount").c_str()) && ok;
        ok = expect_equal_uint64(regionBaselineBatchResults[i].runSummaryCount,
                                 singleRegionResult.runSummaryCount,
                                 (labelPrefix + " baseline runSummaryCount").c_str()) && ok;
        ok = expect_equal_int(regionBaselineBatchResults[i].runningMin,
                              singleRegionResult.runningMin,
                              (labelPrefix + " baseline runningMin").c_str()) && ok;
        ok = expect_candidate_states_equal(regionBaselineBatchResults[i].candidateStates,
                                           singleRegionResult.candidateStates,
                                           (labelPrefix + " baseline candidateStates").c_str()) && ok;
        ok = expect_true(regionBaselineBatchResults[i].events.empty(),
                         (labelPrefix + " baseline events empty").c_str()) && ok;
        ok = expect_true(regionBaselineBatchResults[i].rowOffsets.empty(),
                         (labelPrefix + " baseline rowOffsets empty").c_str()) && ok;

        ok = expect_equal_uint64(regionTrueBatchResults[i].eventCount,
                                 singleRegionResult.eventCount,
                                 (labelPrefix + " true eventCount").c_str()) && ok;
        ok = expect_equal_uint64(regionTrueBatchResults[i].runSummaryCount,
                                 singleRegionResult.runSummaryCount,
                                 (labelPrefix + " true runSummaryCount").c_str()) && ok;
        ok = expect_equal_int(regionTrueBatchResults[i].runningMin,
                              singleRegionResult.runningMin,
                              (labelPrefix + " true runningMin").c_str()) && ok;
        ok = expect_candidate_states_equal(regionTrueBatchResults[i].candidateStates,
                                           singleRegionResult.candidateStates,
                                           (labelPrefix + " true candidateStates").c_str()) && ok;
        ok = expect_true(regionTrueBatchResults[i].events.empty(),
                         (labelPrefix + " true events empty").c_str()) && ok;
        ok = expect_true(regionTrueBatchResults[i].rowOffsets.empty(),
                         (labelPrefix + " true rowOffsets empty").c_str()) && ok;
    }

    SimScanCudaBatchResult regionAggregatedBatchResult;
    const SimScanCudaRegionAggregationResult regionAggregatedResult =
      run_region_aggregated_reduce_all(regionRequests, &regionAggregatedBatchResult);
    const std::vector<SimScanCudaCandidateState> expectedAggregatedRegionStates =
      aggregate_region_candidate_states_host(regionBaselineBatchResults);
    uint64_t expectedAggregatedEventCount = 0;
    uint64_t expectedAggregatedRunSummaryCount = 0;
    uint64_t expectedPreAggregateCandidateStateCount = 0;
    for (size_t i = 0; i < regionBaselineBatchResults.size(); ++i)
    {
        expectedAggregatedEventCount += regionBaselineBatchResults[i].eventCount;
        expectedAggregatedRunSummaryCount += regionBaselineBatchResults[i].runSummaryCount;
        expectedPreAggregateCandidateStateCount +=
          static_cast<uint64_t>(regionBaselineBatchResults[i].candidateStates.size());
    }
    ok = expect_equal_uint64(regionAggregatedResult.eventCount,
                             expectedAggregatedEventCount,
                             "region aggregated eventCount") && ok;
    ok = expect_equal_uint64(regionAggregatedResult.runSummaryCount,
                             expectedAggregatedRunSummaryCount,
                             "region aggregated runSummaryCount") && ok;
    ok = expect_equal_uint64(regionAggregatedResult.preAggregateCandidateStateCount,
                             expectedPreAggregateCandidateStateCount,
                             "region aggregated preAggregateCandidateStateCount") && ok;
    ok = expect_equal_uint64(regionAggregatedResult.postAggregateCandidateStateCount,
                             static_cast<uint64_t>(expectedAggregatedRegionStates.size()),
                             "region aggregated postAggregateCandidateStateCount") && ok;
    ok = expect_equal_uint64(regionAggregatedResult.affectedStartCount,
                             static_cast<uint64_t>(regionFilterStartCoords.size()),
                             "region aggregated affectedStartCount") && ok;
    ok = expect_candidate_states_equal(regionAggregatedResult.candidateStates,
                                       expectedAggregatedRegionStates,
                                       "region aggregated candidateStates") && ok;
    ok = expect_true(regionAggregatedBatchResult.usedCuda,
                     "region aggregated batch uses cuda") && ok;
    ok = expect_true(regionAggregatedBatchResult.usedRegionPackedAggregationPath,
                     "region aggregated batch uses packed aggregation path") && ok;
    ok = expect_equal_uint64(regionAggregatedBatchResult.regionPackedAggregationRequestCount,
                             static_cast<uint64_t>(regionRequests.size()),
                             "region aggregated batch packed aggregation request count") && ok;

    SimScanCudaRequest homogeneousRegionRequest0 = regionRequest0;
    homogeneousRegionRequest0.rowStart = 1;
    homogeneousRegionRequest0.rowEnd = 8;
    homogeneousRegionRequest0.colStart = 1;
    homogeneousRegionRequest0.colEnd = 8;
    SimScanCudaRequest homogeneousRegionRequest1 = regionRequest0;
    homogeneousRegionRequest1.rowStart = 9;
    homogeneousRegionRequest1.rowEnd = 16;
    homogeneousRegionRequest1.colStart = 9;
    homogeneousRegionRequest1.colEnd = 16;
    std::vector<SimScanCudaRequest> homogeneousRegionRequests;
    homogeneousRegionRequests.push_back(homogeneousRegionRequest0);
    homogeneousRegionRequests.push_back(homogeneousRegionRequest1);

    SimScanCudaBatchResult homogeneousBaselineBatchResult;
    const std::vector<SimScanCudaRequestResult> homogeneousBaselineResults =
      run_region_batch_reduce_all(homogeneousRegionRequests, false, &homogeneousBaselineBatchResult);
    SimScanCudaBatchResult homogeneousAggregatedBatchResult;
    const SimScanCudaRegionAggregationResult homogeneousAggregatedResult =
      run_region_aggregated_reduce_all(homogeneousRegionRequests, &homogeneousAggregatedBatchResult);
    const std::vector<SimScanCudaCandidateState> expectedHomogeneousAggregatedStates =
      aggregate_region_candidate_states_host(homogeneousBaselineResults);
    ok = expect_candidate_states_equal(homogeneousAggregatedResult.candidateStates,
                                       expectedHomogeneousAggregatedStates,
                                       "region aggregated homogeneous candidateStates") && ok;
    ok = expect_equal_uint64(homogeneousAggregatedBatchResult.taskCount,
                             1,
                             "region aggregated homogeneous taskCount fused") && ok;
    ok = expect_equal_uint64(homogeneousAggregatedBatchResult.launchCount,
                             1,
                             "region aggregated homogeneous launchCount fused") && ok;

    SimScanCudaRequest regroupedRegionRequest0 = regionRequest0;
    regroupedRegionRequest0.rowStart = 1;
    regroupedRegionRequest0.rowEnd = 8;
    regroupedRegionRequest0.colStart = 1;
    regroupedRegionRequest0.colEnd = 8;
    SimScanCudaRequest regroupedRegionRequest1 = regionRequest0;
    regroupedRegionRequest1.rowStart = 4;
    regroupedRegionRequest1.rowEnd = 7;
    regroupedRegionRequest1.colStart = 10;
    regroupedRegionRequest1.colEnd = 13;
    SimScanCudaRequest regroupedRegionRequest2 = regionRequest0;
    regroupedRegionRequest2.rowStart = 9;
    regroupedRegionRequest2.rowEnd = 16;
    regroupedRegionRequest2.colStart = 9;
    regroupedRegionRequest2.colEnd = 16;
    std::vector<SimScanCudaRequest> regroupedRegionRequests;
    regroupedRegionRequests.push_back(regroupedRegionRequest0);
    regroupedRegionRequests.push_back(regroupedRegionRequest1);
    regroupedRegionRequests.push_back(regroupedRegionRequest2);

    SimScanCudaBatchResult regroupedBaselineBatchResult;
    const std::vector<SimScanCudaRequestResult> regroupedBaselineResults =
      run_region_batch_reduce_all(regroupedRegionRequests, false, &regroupedBaselineBatchResult);
    SimScanCudaBatchResult regroupedAggregatedBatchResult;
    const SimScanCudaRegionAggregationResult regroupedAggregatedResult =
      run_region_aggregated_reduce_all(regroupedRegionRequests, &regroupedAggregatedBatchResult);
    const std::vector<SimScanCudaCandidateState> expectedRegroupedAggregatedStates =
      aggregate_region_candidate_states_host(regroupedBaselineResults);
    ok = expect_candidate_states_equal(regroupedAggregatedResult.candidateStates,
                                       expectedRegroupedAggregatedStates,
                                       "region aggregated regrouped candidateStates") && ok;
    ok = expect_equal_uint64(regroupedAggregatedBatchResult.taskCount,
                             2,
                             "region aggregated regrouped taskCount fused by size") && ok;
    ok = expect_equal_uint64(regroupedAggregatedBatchResult.launchCount,
                             2,
                             "region aggregated regrouped launchCount fused by size") && ok;
    ok = expect_equal_uint64(regroupedAggregatedBatchResult.regionTrueBatchRequestCount,
                             2,
                             "region aggregated regrouped true batch request count") && ok;

    const std::string denseQuery(64, 'A');
    const std::string denseTarget(64, 'A');
    const int denseQueryLength = static_cast<int>(denseQuery.size());
    const int denseTargetLength = static_cast<int>(denseTarget.size());
    SimScanCudaBatchResult denseBatchResult;
    const SimScanCudaInitialBatchResult denseReduced =
      run_single_initial_reduce(denseQuery.c_str(),
                                denseTarget.c_str(),
                                denseQueryLength,
                                denseTargetLength,
                                gapOpen,
                                gapExtend,
                                scoreMatrix,
                                eventScoreFloor,
                                &denseBatchResult);
    const std::vector<SimScanCudaInitialRunSummary> denseSummaries =
      run_single_initial_summaries(denseQuery.c_str(),
                                   denseTarget.c_str(),
                                   denseQueryLength,
                                   denseTargetLength,
                                   gapOpen,
                                   gapExtend,
                                   scoreMatrix,
                                   eventScoreFloor);
    const std::vector<SimScanCudaCandidateState> denseAllStates =
      reduce_all_candidate_states_from_summaries(denseSummaries);
    const std::vector<SimScanCudaCandidateState> densePrunedStates =
      prune_safe_store_states(denseAllStates, denseReduced.candidateStates, denseReduced.runningMin);
    ok = expect_true(denseAllStates.size() > densePrunedStates.size(),
                     "dense initial reduce has prunable safe-store states") && ok;
    ok = expect_true(denseBatchResult.initialReduceReplayStats.chunkCount > 0,
                     "dense initial reduce recorded chunks") && ok;
    ok = expect_true(denseBatchResult.initialReduceReplayStats.summaryReplayCount <= denseReduced.runSummaryCount,
                     "dense initial reduce replay count bounded by total summaries") && ok;
    ok = expect_candidate_states_equal(denseReduced.allCandidateStates,
                                       densePrunedStates,
                                       "dense initial reduce safe-store pruning") && ok;
    SimScanCudaInitialBatchRequest denseRequest = request0;
    denseRequest.A = denseQuery.c_str();
    denseRequest.B = denseTarget.c_str();
    denseRequest.queryLength = denseQueryLength;
    denseRequest.targetLength = denseTargetLength;
    std::vector<SimScanCudaInitialBatchRequest> denseRequests(1, denseRequest);
    SimScanCudaBatchResult denseHashFallbackBatchResult;
    const std::vector<SimScanCudaInitialBatchResult> denseHashFallbackResults =
      run_true_batch_initial_reduce_hash(denseRequests, "8", &denseHashFallbackBatchResult);
    ok = expect_true(!denseHashFallbackBatchResult.usedInitialHashReducePath,
                     "dense hash reduce tiny capacity used legacy fallback path") && ok;
    ok = expect_true(denseHashFallbackBatchResult.initialHashReduceFallback,
                     "dense hash reduce tiny capacity fallback recorded") && ok;
    if (denseHashFallbackResults.size() == 1)
    {
        ok = expect_reduce_result_equal(denseHashFallbackResults[0],
                                        denseReduced,
                                        "dense hash reduce tiny capacity result") && ok;
    }
    SimScanCudaBatchResult denseSegmentedBatchResult;
    const std::vector<SimScanCudaInitialBatchResult> denseSegmentedResults =
      run_true_batch_initial_reduce_backend(denseRequests, "segmented", &denseSegmentedBatchResult);
    ok = expect_true(denseSegmentedBatchResult.usedInitialSegmentedReducePath,
                     "dense segmented reduce used segmented path") && ok;
    ok = expect_true(denseSegmentedBatchResult.initialSegmentedGroupedStateCount < denseReduced.runSummaryCount,
                     "dense segmented reduce grouped states below raw summaries") && ok;
    if (denseSegmentedResults.size() == 1)
    {
        ok = expect_reduce_result_equal(denseSegmentedResults[0],
                                        denseReduced,
                                        "dense segmented reduce result") && ok;
    }

    std::vector<SimScanCudaInitialRunSummary> chunkSkipSummaries;
    std::vector<SimScanCudaCandidateState> expectedChunkSkipStates;
    for (int offset = 0; offset < 50; ++offset)
    {
        chunkSkipSummaries.push_back(SimScanCudaInitialRunSummary{
            static_cast<int>(100 + offset),
            pack_coord(10, static_cast<uint32_t>(offset + 1)),
            1,
            static_cast<uint32_t>(1000 + offset),
            static_cast<uint32_t>(1000 + offset),
            static_cast<uint32_t>(1000 + offset)});
        expectedChunkSkipStates.push_back(SimScanCudaCandidateState{
            static_cast<int>(100 + offset),
            10,
            offset + 1,
            1,
            1000 + offset,
            1,
            1,
            1000 + offset,
            1000 + offset});
    }
    chunkSkipSummaries.push_back(SimScanCudaInitialRunSummary{10, pack_coord(10, 1), 1, 1000, 1000, 1000});
    chunkSkipSummaries.push_back(SimScanCudaInitialRunSummary{20, pack_coord(10, 2), 1, 1001, 1001, 1001});
    std::vector<SimScanCudaCandidateState> chunkSkipStates;
    int chunkSkipRunningMin = 0;
    SimScanCudaInitialReduceReplayStats chunkSkipReplayStats;
    if (!sim_scan_cuda_reduce_initial_run_summaries_for_test(chunkSkipSummaries,
                                                             &chunkSkipStates,
                                                             &chunkSkipRunningMin,
                                                             &chunkSkipReplayStats,
                                                             &error))
    {
        std::cerr << "initial reducer test helper failed: " << error << "\n";
        return 2;
    }
    ok = expect_candidate_states_equal(chunkSkipStates,
                                       expectedChunkSkipStates,
                                       "chunk skip helper candidate states") && ok;
    ok = expect_equal_int(chunkSkipRunningMin, 100, "chunk skip helper runningMin") && ok;
    ok = expect_equal_uint64(chunkSkipReplayStats.chunkCount, 2, "chunk skip helper chunkCount") && ok;
    ok = expect_equal_uint64(chunkSkipReplayStats.chunkReplayedCount, 1, "chunk skip helper replayed chunks") && ok;
    ok = expect_equal_uint64(chunkSkipReplayStats.chunkSkippedCount, 1, "chunk skip helper skipped chunks") && ok;
    ok = expect_equal_uint64(chunkSkipReplayStats.summaryReplayCount, 50, "chunk skip helper replayed summaries") && ok;

    const std::string replayQuery(96, 'A');
    std::vector<std::string> replayTargets;
    replayTargets.push_back(std::string(96, 'A'));
    replayTargets.push_back(std::string(31, 'A') + "C" + std::string(64, 'A'));
    replayTargets.push_back("C" + std::string(95, 'A'));
    replayTargets.push_back(std::string(47, 'A') + "CC" + std::string(47, 'A'));

    std::vector<SimScanCudaInitialBatchRequest> replayRequests;
    replayRequests.reserve(replayTargets.size());
    for (size_t i = 0; i < replayTargets.size(); ++i)
    {
        SimScanCudaInitialBatchRequest replayRequest = request0;
        replayRequest.A = replayQuery.c_str();
        replayRequest.B = replayTargets[i].c_str();
        replayRequest.queryLength = static_cast<int>(replayQuery.size());
        replayRequest.targetLength = static_cast<int>(replayTargets[i].size());
        replayRequests.push_back(replayRequest);
    }

    std::vector<SimScanCudaInitialBatchResult> replayBatchResults;
    SimScanCudaBatchResult replayBatchResult;
    if (!sim_scan_cuda_enumerate_initial_events_row_major_true_batch(replayRequests,
                                                                     &replayBatchResults,
                                                                     &replayBatchResult,
                                                                     &error))
    {
        std::cerr << "replay true batch reduce failed: " << error << "\n";
        return 2;
    }
    ok = expect_equal_uint64(static_cast<uint64_t>(replayBatchResults.size()),
                             static_cast<uint64_t>(replayRequests.size()),
                             "replay batch result count") && ok;
    for (size_t i = 0; i < replayRequests.size() && i < replayBatchResults.size(); ++i)
    {
        const SimScanCudaInitialBatchResult expectedReplay =
          run_single_initial_reduce(replayRequests[i].A,
                                    replayRequests[i].B,
                                    replayRequests[i].queryLength,
                                    replayRequests[i].targetLength,
                                    replayRequests[i].gapOpen,
                                    replayRequests[i].gapExtend,
                                    replayRequests[i].scoreMatrix,
                                    replayRequests[i].eventScoreFloor);
        const std::string label = "replay batch result " + std::to_string(i);
        ok = expect_reduce_result_equal(replayBatchResults[i], expectedReplay, label.c_str()) && ok;
    }

    SimScanCudaInitialBatchRequest proposalRequest0 = request0;
    proposalRequest0.reduceCandidates = false;
    proposalRequest0.proposalCandidates = true;
    proposalRequest0.persistAllCandidateStatesOnDevice = false;

    SimScanCudaInitialBatchRequest proposalRequest1 = proposalRequest0;
    proposalRequest1.B = target1;

    std::vector<SimScanCudaInitialBatchRequest> proposalRequests;
    proposalRequests.push_back(proposalRequest0);
    proposalRequests.push_back(proposalRequest1);

    std::vector<SimScanCudaInitialBatchResult> proposalBatchResults;
    SimScanCudaBatchResult proposalBatchResult;
    if (!sim_scan_cuda_enumerate_initial_events_row_major_true_batch(proposalRequests,
                                                                     &proposalBatchResults,
                                                                     &proposalBatchResult,
                                                                     &error))
    {
        std::cerr << "proposal true batch failed: " << error << "\n";
        return 2;
    }

    ok = expect_equal_uint64(static_cast<uint64_t>(proposalBatchResults.size()), 2, "proposal batch result count") && ok;
    ok = expect_true(!proposalBatchResult.usedInitialProposalV2Path,
                     "proposal batch baseline no V2 path") && ok;
    ok = expect_true(!proposalBatchResult.usedInitialProposalV2DirectTopKPath,
                     "proposal batch baseline no direct-topK path") && ok;
    ok = expect_equal_uint64(proposalBatchResult.initialProposalV2RequestCount,
                             0,
                             "proposal batch baseline V2 request count") && ok;
    ok = expect_true(!proposalBatchResult.usedInitialProposalV3Path,
                     "proposal batch baseline no V3 path") && ok;
    ok = expect_equal_uint64(proposalBatchResult.initialProposalV3RequestCount,
                             0,
                             "proposal batch baseline V3 request count") && ok;
    ok = expect_equal_uint64(proposalBatchResult.initialProposalV3SelectedStateCount,
                             0,
                             "proposal batch baseline V3 selected count") && ok;
    ok = expect_equal_uint64(proposalBatchResult.initialProposalLogicalCandidateCount,
                             0,
                             "proposal batch baseline logical candidate count") && ok;
    ok = expect_equal_uint64(proposalBatchResult.initialProposalMaterializedCandidateCount,
                             0,
                             "proposal batch baseline materialized candidate count") && ok;
    ok = expect_true(proposalBatchResult.initialProposalDirectTopKGpuSeconds == 0.0,
                     "proposal batch baseline direct-topK gpu seconds") && ok;
    ok = expect_equal_uint64(proposalBatchResult.initialProposalDirectTopKCountClearSkips,
                             static_cast<uint64_t>(proposalRequests.size()),
                             "proposal batch baseline direct-topK count-clear skips") && ok;
    ok = expect_true(proposalBatchResult.initialBaseUploadSeconds == 0.0,
                     "proposal batch baseline base-upload seconds") && ok;
    ok = expect_equal_uint64(proposalBatchResult.initialReduceReplayStats.chunkCount, 0, "proposal batch replay chunks") && ok;
    ok = expect_equal_uint64(proposalBatchResult.initialReduceReplayStats.summaryReplayCount, 0, "proposal batch replay summaries") && ok;

    const std::vector<SimScanCudaInitialRunSummary> proposalExpectedSummaries0 =
      run_single_initial_summaries(query,
                                   target0,
                                   queryLength,
                                   targetLength,
                                   gapOpen,
                                   gapExtend,
                                   scoreMatrix,
                                   eventScoreFloor);
    const std::vector<SimScanCudaInitialRunSummary> proposalExpectedSummaries1 =
      run_single_initial_summaries(query,
                                   target1,
                                   queryLength,
                                   targetLength,
                                   gapOpen,
                                   gapExtend,
                                   scoreMatrix,
                                   eventScoreFloor);
    const std::vector<SimScanCudaCandidateState> proposalExpectedAll0 =
      reduce_all_candidate_states_from_summaries(proposalExpectedSummaries0);
    const std::vector<SimScanCudaCandidateState> proposalExpectedAll1 =
      reduce_all_candidate_states_from_summaries(proposalExpectedSummaries1);
    const std::vector<SimScanCudaCandidateState> proposalExpected0 =
      select_proposal_candidate_states(proposalExpectedAll0, 50);
    const std::vector<SimScanCudaCandidateState> proposalExpected1 =
      select_proposal_candidate_states(proposalExpectedAll1, 50);

    if (proposalBatchResults.size() == 2)
    {
        ok = expect_true(proposalBatchResults[0].initialRunSummaries.empty(), "proposal batch result 0 summaries empty") && ok;
        ok = expect_true(proposalBatchResults[1].initialRunSummaries.empty(), "proposal batch result 1 summaries empty") && ok;
        ok = expect_equal_int(proposalBatchResults[0].runningMin, 0, "proposal batch result 0 runningMin") && ok;
        ok = expect_equal_int(proposalBatchResults[1].runningMin, 0, "proposal batch result 1 runningMin") && ok;
        ok = expect_equal_uint64(proposalBatchResults[0].allCandidateStateCount,
                                 static_cast<uint64_t>(proposalExpectedAll0.size()),
                                 "proposal batch result 0 allCandidateStateCount") && ok;
        ok = expect_equal_uint64(proposalBatchResults[1].allCandidateStateCount,
                                 static_cast<uint64_t>(proposalExpectedAll1.size()),
                                 "proposal batch result 1 allCandidateStateCount") && ok;
        ok = expect_candidate_states_equal(proposalBatchResults[0].candidateStates,
                                           proposalExpected0,
                                           "proposal batch result 0 candidateStates") && ok;
        ok = expect_candidate_states_equal(proposalBatchResults[1].candidateStates,
                                           proposalExpected1,
                                           "proposal batch result 1 candidateStates") && ok;
        ok = expect_true(proposalBatchResults[0].allCandidateStates.empty(),
                         "proposal batch result 0 allCandidateStates empty") && ok;
        ok = expect_true(proposalBatchResults[1].allCandidateStates.empty(),
                         "proposal batch result 1 allCandidateStates empty") && ok;
        ok = expect_true(!proposalBatchResults[0].persistentSafeStoreHandle.valid,
                         "proposal batch result 0 persistent store invalid") && ok;
        ok = expect_true(!proposalBatchResults[1].persistentSafeStoreHandle.valid,
                         "proposal batch result 1 persistent store invalid") && ok;
    }

    SimScanCudaBatchResult proposalBatchResultV2;
    const std::vector<SimScanCudaInitialBatchResult> proposalBatchResultsV2 =
      run_true_batch_initial_proposal_v2(proposalRequests, &proposalBatchResultV2);
    ok = expect_equal_uint64(static_cast<uint64_t>(proposalBatchResultsV2.size()), 2, "proposal batch V2 result count") && ok;
    ok = expect_true(proposalBatchResultV2.usedInitialProposalV2Path,
                     "proposal batch V2 used V2 path") && ok;
    ok = expect_true(proposalBatchResultV2.usedInitialProposalV2DirectTopKPath,
                     "proposal batch V2 used direct-topK path") && ok;
    ok = expect_equal_uint64(proposalBatchResultV2.initialProposalV2RequestCount,
                             static_cast<uint64_t>(proposalRequests.size()),
                             "proposal batch V2 request count") && ok;
    ok = expect_equal_uint64(proposalBatchResultV2.initialProposalLogicalCandidateCount,
                             static_cast<uint64_t>(proposalExpectedAll0.size() + proposalExpectedAll1.size()),
                             "proposal batch V2 logical candidate count") && ok;
    ok = expect_equal_uint64(proposalBatchResultV2.initialProposalMaterializedCandidateCount,
                             0,
                             "proposal batch V2 materialized candidate count") && ok;
    ok = expect_true(proposalBatchResultV2.initialProposalDirectTopKGpuSeconds > 0.0,
                     "proposal batch V2 direct-topK gpu seconds") && ok;
    ok = expect_equal_uint64(proposalBatchResultV2.initialProposalDirectTopKCountClearSkips,
                             static_cast<uint64_t>(proposalRequests.size()),
                             "proposal batch V2 direct-topK count-clear skips") && ok;
    ok = expect_true(proposalBatchResultV2.initialBaseUploadSeconds == 0.0,
                     "proposal batch V2 base-upload seconds") && ok;
    ok = expect_true(!proposalBatchResultV2.usedInitialProposalV3Path,
                     "proposal batch V2 no V3 path") && ok;
    ok = expect_equal_uint64(proposalBatchResultV2.initialProposalV3RequestCount,
                             0,
                             "proposal batch V2 no V3 request count") && ok;
    ok = expect_equal_uint64(proposalBatchResultV2.initialProposalV3SelectedStateCount,
                             0,
                             "proposal batch V2 no V3 selected count") && ok;
    ok = expect_equal_uint64(proposalBatchResultV2.initialReduceReplayStats.chunkCount, 0, "proposal batch V2 replay chunks") && ok;
    ok = expect_equal_uint64(proposalBatchResultV2.initialReduceReplayStats.summaryReplayCount, 0, "proposal batch V2 replay summaries") && ok;
    if (proposalBatchResults.size() == proposalBatchResultsV2.size())
    {
        for (size_t i = 0; i < proposalBatchResultsV2.size(); ++i)
        {
            const std::string label = "proposal batch V2 result " + std::to_string(i);
            ok = expect_proposal_result_equal(proposalBatchResultsV2[i],
                                              proposalBatchResults[i],
                                              label.c_str()) && ok;
        }
    }

    SimScanCudaBatchResult proposalBatchResultV3;
    const std::vector<SimScanCudaInitialBatchResult> proposalBatchResultsV3 =
      run_true_batch_initial_proposal_v3(proposalRequests, &proposalBatchResultV3);
    ok = expect_equal_uint64(static_cast<uint64_t>(proposalBatchResultsV3.size()), 2, "proposal batch V3 result count") && ok;
    ok = expect_true(proposalBatchResultV3.usedInitialProposalV3Path,
                     "proposal batch V3 used V3 path") && ok;
    ok = expect_true(!proposalBatchResultV3.usedInitialProposalV2Path,
                     "proposal batch V3 no V2 path") && ok;
    ok = expect_true(!proposalBatchResultV3.usedInitialProposalV2DirectTopKPath,
                     "proposal batch V3 no direct-topK V2 path") && ok;
    ok = expect_equal_uint64(proposalBatchResultV3.initialProposalV3RequestCount,
                             static_cast<uint64_t>(proposalRequests.size()),
                             "proposal batch V3 request count") && ok;
    ok = expect_equal_uint64(proposalBatchResultV3.initialProposalV3SelectedStateCount,
                             static_cast<uint64_t>(proposalExpected0.size() + proposalExpected1.size()),
                             "proposal batch V3 selected count") && ok;
    ok = expect_equal_uint64(proposalBatchResultV3.initialProposalV3SelectedCountClearSkips,
                             static_cast<uint64_t>(proposalRequests.size()),
                             "proposal batch V3 selected-count clear skips") && ok;
    ok = expect_true(proposalBatchResultV3.initialProposalV3GpuSeconds > 0.0,
                     "proposal batch V3 gpu seconds") && ok;
    ok = expect_true(proposalBatchResultV3.initialCountCopySeconds >= 0.0,
                     "proposal batch V3 count-copy seconds") && ok;
    ok = expect_true(proposalBatchResultV3.initialBaseUploadSeconds == 0.0,
                     "proposal batch V3 base-upload seconds") && ok;
    ok = expect_true(proposalBatchResultV3.initialSyncWaitSeconds >= 0.0,
                     "proposal batch V3 sync-wait seconds") && ok;
    if (proposalBatchResults.size() == proposalBatchResultsV3.size())
    {
        for (size_t i = 0; i < proposalBatchResultsV3.size(); ++i)
        {
            const std::string label = "proposal batch V3 result " + std::to_string(i);
            ok = expect_proposal_result_equal(proposalBatchResultsV3[i],
                                              proposalBatchResults[i],
                                              label.c_str()) && ok;
        }
    }

    std::vector<SimScanCudaInitialBatchRequest> singleProposalV3Requests;
    singleProposalV3Requests.push_back(proposalRequest0);
    SimScanCudaBatchResult singleProposalV3BatchResult;
    const std::vector<SimScanCudaInitialBatchResult> singleProposalV3Results =
      run_true_batch_initial_proposal_v3(singleProposalV3Requests, &singleProposalV3BatchResult);
    ok = expect_equal_uint64(static_cast<uint64_t>(singleProposalV3Results.size()),
                             1,
                             "single proposal V3 result count") && ok;
    ok = expect_true(singleProposalV3BatchResult.usedInitialProposalV3Path,
                     "single proposal V3 used V3 path") && ok;
    ok = expect_equal_uint64(singleProposalV3BatchResult.initialProposalV3RequestCount,
                             1,
                             "single proposal V3 request count") && ok;
    ok = expect_equal_uint64(
           singleProposalV3BatchResult.initialTrueBatchSingleRequestProposalV3StateBaseBufferEnsureSkips,
           1,
           "single proposal V3 state-base buffer ensure skip") && ok;
    ok = expect_equal_uint64(
           singleProposalV3BatchResult.initialTrueBatchSingleRequestProposalV3StateBaseUploadSkips,
           1,
           "single proposal V3 state-base upload skip") && ok;
    ok = expect_equal_uint64(
           singleProposalV3BatchResult.initialTrueBatchSingleRequestProposalV3SelectedBaseUploadSkips,
           1,
           "single proposal V3 selected-base upload skip") && ok;
    ok = expect_equal_uint64(singleProposalV3BatchResult.initialProposalV3SelectedCountClearSkips,
                             1,
                             "single proposal V3 selected-count clear skip") && ok;
    if (singleProposalV3Results.size() == 1)
    {
        ok = expect_proposal_result_equal(singleProposalV3Results[0],
                                          proposalBatchResults[0],
                                          "single proposal V3 result") && ok;
    }

    std::vector<SimScanCudaInitialBatchRequest> singleProposalV2Requests;
    singleProposalV2Requests.push_back(proposalRequest0);
    SimScanCudaBatchResult singleProposalV2BatchResult;
    const std::vector<SimScanCudaInitialBatchResult> singleProposalV2Results =
      run_true_batch_initial_proposal_v2(singleProposalV2Requests, &singleProposalV2BatchResult);
    ok = expect_equal_uint64(static_cast<uint64_t>(singleProposalV2Results.size()),
                             1,
                             "single proposal V2 result count") && ok;
    ok = expect_true(singleProposalV2BatchResult.usedInitialProposalV2Path,
                     "single proposal V2 used V2 path") && ok;
    ok = expect_equal_uint64(singleProposalV2BatchResult.initialProposalV2RequestCount,
                             1,
                             "single proposal V2 request count") && ok;
    ok = expect_equal_uint64(singleProposalV2BatchResult.initialProposalDirectTopKCountClearSkips,
                             1,
                             "single proposal V2 direct-topK count-clear skip") && ok;
    if (singleProposalV2Results.size() == 1)
    {
        ok = expect_proposal_result_equal(singleProposalV2Results[0],
                                          proposalBatchResults[0],
                                          "single proposal V2 result") && ok;
    }

    const SimScanCudaInitialBatchResult singleProposal0 =
      run_single_initial_proposal(query,
                                  target0,
                                  queryLength,
                                  targetLength,
                                  gapOpen,
                                  gapExtend,
                                  scoreMatrix,
                                  eventScoreFloor);
    const SimScanCudaInitialBatchResult singleProposal1 =
      run_single_initial_proposal(query,
                                  target1,
                                  queryLength,
                                  targetLength,
                                  gapOpen,
                                  gapExtend,
                                  scoreMatrix,
                                  eventScoreFloor);
    ok = expect_true(singleProposal0.initialRunSummaries.empty(), "single proposal 0 summaries empty") && ok;
    ok = expect_true(singleProposal1.initialRunSummaries.empty(), "single proposal 1 summaries empty") && ok;
    ok = expect_equal_int(singleProposal0.runningMin, 0, "single proposal 0 runningMin") && ok;
    ok = expect_equal_int(singleProposal1.runningMin, 0, "single proposal 1 runningMin") && ok;
    ok = expect_equal_uint64(singleProposal0.runSummaryCount,
                             static_cast<uint64_t>(proposalExpectedSummaries0.size()),
                             "single proposal 0 runSummaryCount") && ok;
    ok = expect_equal_uint64(singleProposal1.runSummaryCount,
                             static_cast<uint64_t>(proposalExpectedSummaries1.size()),
                             "single proposal 1 runSummaryCount") && ok;
    ok = expect_equal_uint64(singleProposal0.allCandidateStateCount,
                             static_cast<uint64_t>(proposalExpectedAll0.size()),
                             "single proposal 0 allCandidateStateCount") && ok;
    ok = expect_equal_uint64(singleProposal1.allCandidateStateCount,
                             static_cast<uint64_t>(proposalExpectedAll1.size()),
                             "single proposal 1 allCandidateStateCount") && ok;
    ok = expect_candidate_states_equal(singleProposal0.candidateStates,
                                       proposalExpected0,
                                       "single proposal 0 candidateStates") && ok;
    ok = expect_candidate_states_equal(singleProposal1.candidateStates,
                                       proposalExpected1,
                                       "single proposal 1 candidateStates") && ok;
    ok = expect_true(singleProposal0.allCandidateStates.empty(),
                     "single proposal 0 allCandidateStates empty") && ok;
    ok = expect_true(singleProposal1.allCandidateStates.empty(),
                     "single proposal 1 allCandidateStates empty") && ok;
    ok = expect_true(!singleProposal0.persistentSafeStoreHandle.valid,
                     "single proposal 0 persistent store invalid") && ok;
    ok = expect_true(!singleProposal1.persistentSafeStoreHandle.valid,
                     "single proposal 1 persistent store invalid") && ok;

    const SimScanCudaInitialBatchResult singleProposalResidency0 =
      run_single_initial_proposal_residency(query,
                                            target0,
                                            queryLength,
                                            targetLength,
                                            gapOpen,
                                            gapExtend,
                                            scoreMatrix,
                                            eventScoreFloor);
    const SimScanCudaInitialBatchResult singleProposalResidency1 =
      run_single_initial_proposal_residency(query,
                                            target1,
                                            queryLength,
                                            targetLength,
                                            gapOpen,
                                            gapExtend,
                                            scoreMatrix,
                                            eventScoreFloor);
    ok = expect_proposal_residency_result_equal(singleProposalResidency0,
                                                expected0,
                                                "single proposal residency 0") && ok;
    ok = expect_proposal_residency_result_equal(singleProposalResidency1,
                                                expected1,
                                                "single proposal residency 1") && ok;
    const std::vector<SimScanCudaCandidateState> selectedProposalResidencyStates0 =
      select_top_disjoint_from_persistent_store(singleProposalResidency0.persistentSafeStoreHandle,
                                                50);
    const std::vector<SimScanCudaCandidateState> selectedProposalResidencyStates1 =
      select_top_disjoint_from_persistent_store(singleProposalResidency1.persistentSafeStoreHandle,
                                                50);
    ok = expect_candidate_states_equal(selectedProposalResidencyStates0,
                                       proposalExpected0,
                                       "single proposal residency 0 persistent store top-k") && ok;
    ok = expect_candidate_states_equal(selectedProposalResidencyStates1,
                                       proposalExpected1,
                                       "single proposal residency 1 persistent store top-k") && ok;

    const SimScanCudaInitialBatchResult singleProposalStreaming0 =
      run_single_initial_proposal_streaming(query,
                                            target0,
                                            queryLength,
                                            targetLength,
                                            gapOpen,
                                            gapExtend,
                                            scoreMatrix,
                                            eventScoreFloor);
    const SimScanCudaInitialBatchResult singleProposalStreaming1 =
      run_single_initial_proposal_streaming(query,
                                            target1,
                                            queryLength,
                                            targetLength,
                                            gapOpen,
                                            gapExtend,
                                            scoreMatrix,
                                            eventScoreFloor);
    ok = expect_true(singleProposalStreaming0.initialRunSummaries.empty(),
                     "single proposal streaming 0 summaries empty") && ok;
    ok = expect_true(singleProposalStreaming1.initialRunSummaries.empty(),
                     "single proposal streaming 1 summaries empty") && ok;
    ok = expect_equal_int(singleProposalStreaming0.runningMin, 0, "single proposal streaming 0 runningMin") && ok;
    ok = expect_equal_int(singleProposalStreaming1.runningMin, 0, "single proposal streaming 1 runningMin") && ok;
    ok = expect_equal_uint64(singleProposalStreaming0.runSummaryCount,
                             static_cast<uint64_t>(proposalExpectedSummaries0.size()),
                             "single proposal streaming 0 runSummaryCount") && ok;
    ok = expect_equal_uint64(singleProposalStreaming1.runSummaryCount,
                             static_cast<uint64_t>(proposalExpectedSummaries1.size()),
                             "single proposal streaming 1 runSummaryCount") && ok;
    ok = expect_equal_uint64(singleProposalStreaming0.allCandidateStateCount,
                             static_cast<uint64_t>(proposalExpectedAll0.size()),
                             "single proposal streaming 0 allCandidateStateCount") && ok;
    ok = expect_equal_uint64(singleProposalStreaming1.allCandidateStateCount,
                             static_cast<uint64_t>(proposalExpectedAll1.size()),
                             "single proposal streaming 1 allCandidateStateCount") && ok;
    ok = expect_candidate_states_equal(singleProposalStreaming0.candidateStates,
                                       proposalExpected0,
                                       "single proposal streaming 0 candidateStates") && ok;
    ok = expect_candidate_states_equal(singleProposalStreaming1.candidateStates,
                                       proposalExpected1,
                                       "single proposal streaming 1 candidateStates") && ok;
    ok = expect_true(singleProposalStreaming0.allCandidateStates.empty(),
                     "single proposal streaming 0 allCandidateStates empty") && ok;
    ok = expect_true(singleProposalStreaming1.allCandidateStates.empty(),
                     "single proposal streaming 1 allCandidateStates empty") && ok;
    ok = expect_true(!singleProposalStreaming0.persistentSafeStoreHandle.valid,
                     "single proposal streaming 0 persistent store invalid") && ok;
    ok = expect_true(!singleProposalStreaming1.persistentSafeStoreHandle.valid,
                     "single proposal streaming 1 persistent store invalid") && ok;

    SimScanCudaBatchResult singleProposalOnlineBatch0;
    SimScanCudaBatchResult singleProposalOnlineBatch1;
    const SimScanCudaInitialBatchResult singleProposalOnline0 =
      run_single_initial_proposal_online(query,
                                         target0,
                                         queryLength,
                                         targetLength,
                                         gapOpen,
                                         gapExtend,
                                         scoreMatrix,
                                         eventScoreFloor,
                                         NULL,
                                         &singleProposalOnlineBatch0);
    const SimScanCudaInitialBatchResult singleProposalOnline1 =
      run_single_initial_proposal_online(query,
                                         target1,
                                         queryLength,
                                         targetLength,
                                         gapOpen,
                                         gapExtend,
                                         scoreMatrix,
                                         eventScoreFloor,
                                         NULL,
                                         &singleProposalOnlineBatch1);
    ok = expect_true(singleProposalOnlineBatch0.usedInitialProposalOnlinePath,
                     "single proposal online 0 used online path") && ok;
    ok = expect_true(singleProposalOnlineBatch1.usedInitialProposalOnlinePath,
                     "single proposal online 1 used online path") && ok;
    ok = expect_true(!singleProposalOnlineBatch0.initialProposalOnlineFallback,
                     "single proposal online 0 no fallback") && ok;
    ok = expect_true(!singleProposalOnlineBatch1.initialProposalOnlineFallback,
                     "single proposal online 1 no fallback") && ok;
    ok = expect_equal_uint64(singleProposalOnline0.runSummaryCount,
                             static_cast<uint64_t>(proposalExpectedSummaries0.size()),
                             "single proposal online 0 runSummaryCount") && ok;
    ok = expect_equal_uint64(singleProposalOnline1.runSummaryCount,
                             static_cast<uint64_t>(proposalExpectedSummaries1.size()),
                             "single proposal online 1 runSummaryCount") && ok;
    ok = expect_equal_uint64(singleProposalOnline0.allCandidateStateCount,
                             static_cast<uint64_t>(proposalExpectedAll0.size()),
                             "single proposal online 0 allCandidateStateCount") && ok;
    ok = expect_equal_uint64(singleProposalOnline1.allCandidateStateCount,
                             static_cast<uint64_t>(proposalExpectedAll1.size()),
                             "single proposal online 1 allCandidateStateCount") && ok;
    ok = expect_candidate_states_equal(singleProposalOnline0.candidateStates,
                                       proposalExpected0,
                                       "single proposal online 0 candidateStates") && ok;
    ok = expect_candidate_states_equal(singleProposalOnline1.candidateStates,
                                       proposalExpected1,
                                       "single proposal online 1 candidateStates") && ok;

    SimScanCudaBatchResult onlineFallbackBatchResult;
    const SimScanCudaInitialBatchResult onlineFallbackDense =
      run_single_initial_proposal_online(denseQuery.c_str(),
                                         denseTarget.c_str(),
                                         denseQueryLength,
                                         denseTargetLength,
                                         gapOpen,
                                         gapExtend,
                                         scoreMatrix,
                                         eventScoreFloor,
                                         "8",
                                         &onlineFallbackBatchResult);
    const std::vector<SimScanCudaCandidateState> denseProposalExpected =
      select_proposal_candidate_states(denseAllStates, 50);
    ok = expect_true(!onlineFallbackBatchResult.usedInitialProposalOnlinePath,
                     "single proposal online tiny hash used legacy fallback path") && ok;
    ok = expect_true(onlineFallbackBatchResult.initialProposalOnlineFallback,
                     "single proposal online tiny hash fallback recorded") && ok;
    ok = expect_equal_uint64(onlineFallbackDense.allCandidateStateCount,
                             static_cast<uint64_t>(denseAllStates.size()),
                             "single proposal online tiny hash allCandidateStateCount") && ok;
    ok = expect_candidate_states_equal(onlineFallbackDense.candidateStates,
                                       denseProposalExpected,
                                       "single proposal online tiny hash candidateStates") && ok;

    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
