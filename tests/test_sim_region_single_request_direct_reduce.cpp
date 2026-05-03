#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
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

static bool expect_false(bool value, const char *label)
{
    if (!value)
    {
        return true;
    }
    std::cerr << label << ": expected false, got true\n";
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
    for (size_t i = 0; i < actual.size(); ++i)
    {
        if (std::memcmp(&actual[i], &expected[i], sizeof(SimScanCudaCandidateState)) != 0)
        {
            std::cerr << label << ": mismatch at index " << i << "\n";
            return false;
        }
    }
    return true;
}

static uint64_t pack_coord(uint32_t i, uint32_t j)
{
    return (static_cast<uint64_t>(i) << 32) | static_cast<uint64_t>(j);
}

static void initialize_score_matrix(int scoreMatrix[128][128])
{
    for (int i = 0; i < 128; ++i)
    {
        for (int j = 0; j < 128; ++j)
        {
            scoreMatrix[i][j] = -4;
        }
    }
    scoreMatrix['A']['A'] = 5;
    scoreMatrix['C']['C'] = 5;
    scoreMatrix['G']['G'] = 5;
    scoreMatrix['T']['T'] = 5;
}

static std::vector<uint64_t> all_start_coords(int rowCount, int colCount)
{
    std::vector<uint64_t> coords;
    coords.reserve(static_cast<size_t>(rowCount) * static_cast<size_t>(colCount));
    for (int i = 1; i <= rowCount; ++i)
    {
        for (int j = 1; j <= colCount; ++j)
        {
            coords.push_back(pack_coord(static_cast<uint32_t>(i), static_cast<uint32_t>(j)));
        }
    }
    return coords;
}

static SimScanCudaRequest make_region_request(const std::string &query,
                                              const std::string &target,
                                              const int scoreMatrix[128][128],
                                              const std::vector<uint64_t> *filter,
                                              int eventScoreFloor = 0)
{
    SimScanCudaRequest request;
    request.kind = SIM_SCAN_CUDA_REQUEST_REGION;
    request.A = query.c_str();
    request.B = target.c_str();
    request.queryLength = static_cast<int>(query.size());
    request.targetLength = static_cast<int>(target.size());
    request.rowStart = 1;
    request.rowEnd = static_cast<int>(query.size());
    request.colStart = 1;
    request.colEnd = static_cast<int>(target.size());
    request.gapOpen = 16;
    request.gapExtend = 4;
    request.scoreMatrix = scoreMatrix;
    request.eventScoreFloor = eventScoreFloor;
    request.reduceCandidates = false;
    request.reduceAllCandidateStates = true;
    request.filterStartCoords = (filter != NULL && !filter->empty()) ? filter->data() : NULL;
    request.filterStartCoordCount = (filter != NULL) ? static_cast<int>(filter->size()) : 0;
    request.seedCandidates = NULL;
    request.seedCandidateCount = 0;
    request.seedRunningMin = 0;
    return request;
}

static SimScanCudaRequest make_offset_region_request(const std::string &query,
                                                     const std::string &target,
                                                     const int scoreMatrix[128][128],
                                                     const std::vector<uint64_t> *filter,
                                                     int rowStart,
                                                     int rowEnd,
                                                     int colStart,
                                                     int colEnd,
                                                     int eventScoreFloor)
{
    SimScanCudaRequest request =
      make_region_request(query, target, scoreMatrix, filter, eventScoreFloor);
    request.rowStart = rowStart;
    request.rowEnd = rowEnd;
    request.colStart = colStart;
    request.colEnd = colEnd;
    return request;
}

static bool run_region_aggregated(const std::vector<SimScanCudaRequest> &requests,
                                  SimScanCudaRegionAggregationResult *result,
                                  SimScanCudaBatchResult *batchResult)
{
    std::string error;
    if (!sim_scan_cuda_enumerate_region_candidate_states_aggregated(requests,
                                                                    result,
                                                                    batchResult,
                                                                    &error))
    {
        std::cerr << "region aggregation failed: " << error << "\n";
        return false;
    }
    return true;
}

static void clear_direct_env()
{
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE");
    unsetenv("LONGTARGET_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE_SHADOW");
    unsetenv("LONGTARGET_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_HASH_CAPACITY");
}

static bool expect_region_results_equal(const SimScanCudaRegionAggregationResult &actual,
                                        const SimScanCudaRegionAggregationResult &expected,
                                        const char *label)
{
    bool ok = true;
    std::string prefix(label);
    ok = expect_equal_uint64(actual.eventCount, expected.eventCount, (prefix + " eventCount").c_str()) && ok;
    ok = expect_equal_uint64(actual.runSummaryCount, expected.runSummaryCount, (prefix + " runSummaryCount").c_str()) && ok;
    ok = expect_equal_uint64(actual.preAggregateCandidateStateCount,
                             expected.preAggregateCandidateStateCount,
                             (prefix + " preAggregateCandidateStateCount").c_str()) && ok;
    ok = expect_equal_uint64(actual.postAggregateCandidateStateCount,
                             expected.postAggregateCandidateStateCount,
                             (prefix + " postAggregateCandidateStateCount").c_str()) && ok;
    ok = expect_candidate_states_equal(actual.candidateStates,
                                       expected.candidateStates,
                                       (prefix + " candidateStates").c_str()) && ok;
    return ok;
}

static bool test_direct_reduce_matches_authoritative_single_request()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "ACGTAAAACGT";
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));

    clear_direct_env();
    SimScanCudaRequest baselineRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> baselineRequests(1, baselineRequest);
    SimScanCudaRegionAggregationResult baselineResult;
    SimScanCudaBatchResult baselineBatchResult;
    if (!run_region_aggregated(baselineRequests, &baselineResult, &baselineBatchResult))
    {
        return false;
    }

    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    SimScanCudaRequest directRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> directRequests(1, directRequest);
    SimScanCudaRegionAggregationResult directResult;
    SimScanCudaBatchResult directBatchResult;
    if (!run_region_aggregated(directRequests, &directResult, &directBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(directResult, baselineResult, "direct") && true;
    ok = expect_true(directBatchResult.usedRegionSingleRequestDirectReducePath,
                     "direct path used") && ok;
    ok = expect_equal_uint64(directBatchResult.regionSingleRequestDirectReduceAttempts,
                             1,
                             "direct attempts") && ok;
    ok = expect_equal_uint64(directBatchResult.regionSingleRequestDirectReduceSuccesses,
                             1,
                             "direct successes") && ok;
    ok = expect_equal_uint64(directBatchResult.regionSingleRequestDirectReduceFallbacks,
                             0,
                             "direct fallbacks") && ok;
    ok = expect_equal_uint64(directBatchResult.regionSingleRequestDirectReduceCandidateCount,
                             static_cast<uint64_t>(directResult.candidateStates.size()),
                             "direct candidate count") && ok;
    return ok;
}

static bool test_direct_reduce_shadow_matches_authoritative()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "ACGTAAAACGT";
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));

    clear_direct_env();
    SimScanCudaRequest baselineRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> baselineRequests(1, baselineRequest);
    SimScanCudaRegionAggregationResult baselineResult;
    SimScanCudaBatchResult baselineBatchResult;
    if (!run_region_aggregated(baselineRequests, &baselineResult, &baselineBatchResult))
    {
        return false;
    }

    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE_SHADOW", "1", 1);
    SimScanCudaRequest shadowRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> shadowRequests(1, shadowRequest);
    SimScanCudaRegionAggregationResult shadowResult;
    SimScanCudaBatchResult shadowBatchResult;
    if (!run_region_aggregated(shadowRequests, &shadowResult, &shadowBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(shadowResult, baselineResult, "shadow") && true;
    ok = expect_true(shadowBatchResult.usedRegionSingleRequestDirectReducePath,
                     "shadow direct path used") && ok;
    ok = expect_equal_uint64(shadowBatchResult.regionSingleRequestDirectReduceAttempts,
                             1,
                             "shadow attempts") && ok;
    ok = expect_equal_uint64(shadowBatchResult.regionSingleRequestDirectReduceSuccesses,
                             1,
                             "shadow successes") && ok;
    ok = expect_equal_uint64(shadowBatchResult.regionSingleRequestDirectReduceShadowMismatches,
                             0,
                             "shadow mismatches") && ok;
    return ok;
}

static bool test_direct_reduce_matches_gapped_event_runs()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "AAAAAAAA";
    const std::string target = "AAATAAAA";
    const int eventScoreFloor = 8;
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));

    clear_direct_env();
    SimScanCudaRequest baselineRequest =
      make_region_request(query, target, scoreMatrix, &filter, eventScoreFloor);
    std::vector<SimScanCudaRequest> baselineRequests(1, baselineRequest);
    SimScanCudaRegionAggregationResult baselineResult;
    SimScanCudaBatchResult baselineBatchResult;
    if (!run_region_aggregated(baselineRequests, &baselineResult, &baselineBatchResult))
    {
        return false;
    }

    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    SimScanCudaRequest directRequest =
      make_region_request(query, target, scoreMatrix, &filter, eventScoreFloor);
    std::vector<SimScanCudaRequest> directRequests(1, directRequest);
    SimScanCudaRegionAggregationResult directResult;
    SimScanCudaBatchResult directBatchResult;
    if (!run_region_aggregated(directRequests, &directResult, &directBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(directResult, baselineResult, "gapped direct") && true;
    ok = expect_true(directBatchResult.usedRegionSingleRequestDirectReducePath,
                     "gapped direct path used") && ok;
    ok = expect_equal_uint64(directBatchResult.regionSingleRequestDirectReduceFallbacks,
                             0,
                             "gapped direct fallbacks") && ok;
    return ok;
}

static bool test_direct_reduce_matches_offset_region()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTAAAACCCCGGGGTTTTAAAACCCCGGGG";
    const std::string target = "TTTTACGTAAAACCCCGGGGTTTTAAAACCCC";
    const int eventScoreFloor = 20;
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));

    clear_direct_env();
    SimScanCudaRequest baselineRequest =
      make_offset_region_request(query, target, scoreMatrix, &filter, 5, 28, 4, 30, eventScoreFloor);
    std::vector<SimScanCudaRequest> baselineRequests(1, baselineRequest);
    SimScanCudaRegionAggregationResult baselineResult;
    SimScanCudaBatchResult baselineBatchResult;
    if (!run_region_aggregated(baselineRequests, &baselineResult, &baselineBatchResult))
    {
        return false;
    }

    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    SimScanCudaRequest directRequest =
      make_offset_region_request(query, target, scoreMatrix, &filter, 5, 28, 4, 30, eventScoreFloor);
    std::vector<SimScanCudaRequest> directRequests(1, directRequest);
    SimScanCudaRegionAggregationResult directResult;
    SimScanCudaBatchResult directBatchResult;
    if (!run_region_aggregated(directRequests, &directResult, &directBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(directResult, baselineResult, "offset direct") && true;
    ok = expect_true(directBatchResult.usedRegionSingleRequestDirectReducePath,
                     "offset direct path used") && ok;
    return ok;
}

static bool test_direct_reduce_falls_back_without_filter()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "ACGTAAAACGT";

    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    SimScanCudaRequest request = make_region_request(query, target, scoreMatrix, NULL);
    std::vector<SimScanCudaRequest> requests(1, request);
    SimScanCudaRegionAggregationResult result;
    SimScanCudaBatchResult batchResult;
    if (!run_region_aggregated(requests, &result, &batchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_false(batchResult.usedRegionSingleRequestDirectReducePath,
                           "no-filter direct path not used") && true;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReduceAttempts,
                             0,
                             "no-filter direct attempts") && ok;
    return ok;
}

static bool test_direct_reduce_overflow_falls_back()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "ACGTAAAACGT";
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));

    clear_direct_env();
    SimScanCudaRequest baselineRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> baselineRequests(1, baselineRequest);
    SimScanCudaRegionAggregationResult baselineResult;
    SimScanCudaBatchResult baselineBatchResult;
    if (!run_region_aggregated(baselineRequests, &baselineResult, &baselineBatchResult))
    {
        return false;
    }
    if (baselineResult.candidateStates.size() < 2)
    {
        std::cerr << "overflow fixture expected at least two candidate states, got "
                  << baselineResult.candidateStates.size() << "\n";
        return false;
    }

    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_HASH_CAPACITY", "1", 1);
    SimScanCudaRequest directRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> directRequests(1, directRequest);
    SimScanCudaRegionAggregationResult directResult;
    SimScanCudaBatchResult directBatchResult;
    if (!run_region_aggregated(directRequests, &directResult, &directBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(directResult, baselineResult, "overflow fallback") && true;
    ok = expect_false(directBatchResult.usedRegionSingleRequestDirectReducePath,
                      "overflow direct path not used") && ok;
    ok = expect_equal_uint64(directBatchResult.regionSingleRequestDirectReduceAttempts,
                             1,
                             "overflow attempts") && ok;
    ok = expect_equal_uint64(directBatchResult.regionSingleRequestDirectReduceSuccesses,
                             0,
                             "overflow successes") && ok;
    ok = expect_equal_uint64(directBatchResult.regionSingleRequestDirectReduceFallbacks,
                             1,
                             "overflow fallbacks") && ok;
    ok = expect_equal_uint64(directBatchResult.regionSingleRequestDirectReduceOverflows,
                             1,
                             "overflow count") && ok;
    return ok;
}

}

int main()
{
    std::string error;
    if (!sim_scan_cuda_init(0, &error))
    {
        std::cerr << "sim_scan_cuda_init failed: " << error << "\n";
        return 1;
    }

    bool ok = true;
    ok = test_direct_reduce_matches_authoritative_single_request() && ok;
    ok = test_direct_reduce_shadow_matches_authoritative() && ok;
    ok = test_direct_reduce_matches_gapped_event_runs() && ok;
    ok = test_direct_reduce_matches_offset_region() && ok;
    ok = test_direct_reduce_falls_back_without_filter() && ok;
    ok = test_direct_reduce_overflow_falls_back() && ok;
    clear_direct_env();
    return ok ? 0 : 1;
}
