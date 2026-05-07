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

static bool expect_positive_double(double value, const char *label)
{
    if (value > 0.0)
    {
        return true;
    }
    std::cerr << label << ": expected positive value, got " << value << "\n";
    return false;
}

static bool expect_nonnegative_double(double value, const char *label)
{
    if (value >= 0.0)
    {
        return true;
    }
    std::cerr << label << ": expected non-negative value, got " << value << "\n";
    return false;
}

static bool expect_zero_double(double value, const char *label)
{
    if (value == 0.0)
    {
        return true;
    }
    std::cerr << label << ": expected zero value, got " << value << "\n";
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
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS");
    unsetenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY");
    unsetenv("LONGTARGET_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE_SHADOW");
    unsetenv("LONGTARGET_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_HASH_CAPACITY");
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP");
    unsetenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP_SHADOW");
    unsetenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP_MAX_CELLS");
    unsetenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP_MAX_DIAG_LEN");
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP");
    unsetenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP_SHADOW");
    unsetenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP_MAX_CELLS");
    unsetenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP_MAX_DIAG_LEN");
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

static bool test_direct_reduce_records_profile_telemetry()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "ACGTAAAACGT";
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));

    clear_direct_env();
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    SimScanCudaRequest request = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> requests(1, request);
    SimScanCudaRegionAggregationResult result;
    SimScanCudaBatchResult batchResult;
    if (!run_region_aggregated(requests, &result, &batchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    const uint64_t expectedWorkItems =
      batchResult.regionSingleRequestDirectReduceAffectedStartCount *
      batchResult.regionSingleRequestDirectReduceRunSummaryCount;
    bool ok = expect_true(batchResult.usedRegionSingleRequestDirectReducePath,
                          "profile direct path used") && true;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReduceAffectedStartCount,
                             static_cast<uint64_t>(filter.size()),
                             "profile affected start count") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReduceReduceWorkItems,
                             expectedWorkItems,
                             "profile reduce work items") && ok;
    ok = expect_positive_double(batchResult.regionSingleRequestDirectReduceDpGpuSeconds,
                                "profile dp gpu seconds") && ok;
    ok = expect_positive_double(batchResult.regionSingleRequestDirectReduceFilterReduceGpuSeconds,
                                "profile filter reduce gpu seconds") && ok;
    ok = expect_nonnegative_double(batchResult.regionSingleRequestDirectReduceCompactGpuSeconds,
                                   "profile compact gpu seconds") && ok;
    ok = expect_nonnegative_double(batchResult.regionSingleRequestDirectReduceCountD2HSeconds,
                                   "profile count d2h seconds") && ok;
    ok = expect_nonnegative_double(batchResult.regionSingleRequestDirectReduceCandidateCountD2HSeconds,
                                   "profile candidate-count d2h seconds") && ok;
    return ok;
}

static bool test_direct_reduce_pipeline_telemetry_disabled_by_default()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "ACGTAAAACGT";
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));

    clear_direct_env();
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    SimScanCudaRequest request = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> requests(1, request);
    SimScanCudaRegionAggregationResult result;
    SimScanCudaBatchResult batchResult;
    if (!run_region_aggregated(requests, &result, &batchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_true(batchResult.usedRegionSingleRequestDirectReducePath,
                          "pipeline disabled direct path used") && true;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineRequestCount,
                             0,
                             "pipeline disabled request count") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineDiagLaunchCount,
                             0,
                             "pipeline disabled diag launches") && ok;
    ok = expect_zero_double(batchResult.regionSingleRequestDirectReducePipelineDiagGpuSeconds,
                            "pipeline disabled diag seconds") && ok;
    return ok;
}

static bool test_direct_reduce_records_pipeline_telemetry()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "ACGTAAAACGT";
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));
    const uint64_t rowCount = static_cast<uint64_t>(query.size());
    const uint64_t colCount = static_cast<uint64_t>(target.size());
    const uint64_t diagCount = rowCount + colCount - 1;

    clear_direct_env();
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY", "1", 1);
    SimScanCudaRequest request = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> requests(1, request);
    SimScanCudaRegionAggregationResult result;
    SimScanCudaBatchResult batchResult;
    if (!run_region_aggregated(requests, &result, &batchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    const uint64_t dpBucketTotal =
      batchResult.regionSingleRequestDirectReducePipelineDpLt1msCount +
      batchResult.regionSingleRequestDirectReducePipelineDp1To5msCount +
      batchResult.regionSingleRequestDirectReducePipelineDp5To10msCount +
      batchResult.regionSingleRequestDirectReducePipelineDp10To50msCount +
      batchResult.regionSingleRequestDirectReducePipelineDpGte50msCount;
    bool ok = expect_true(batchResult.usedRegionSingleRequestDirectReducePath,
                          "pipeline telemetry direct path used") && true;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineRequestCount,
                             1,
                             "pipeline request count") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineRowCountTotal,
                             rowCount,
                             "pipeline row total") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineRowCountMax,
                             rowCount,
                             "pipeline row max") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineColCountTotal,
                             colCount,
                             "pipeline col total") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineCellCountTotal,
                             rowCount * colCount,
                             "pipeline cell total") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineDiagCountTotal,
                             diagCount,
                             "pipeline diag total") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineDiagLaunchCount,
                             diagCount,
                             "pipeline diag launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineFilterStartCountTotal,
                             static_cast<uint64_t>(filter.size()),
                             "pipeline filter total") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineEventCountLaunchCount,
                             1,
                             "pipeline event count launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineEventPrefixLaunchCount,
                             1,
                             "pipeline event prefix launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineRunCountLaunchCount,
                             1,
                             "pipeline run count launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineRunPrefixLaunchCount,
                             1,
                             "pipeline run prefix launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineRunCompactLaunchCount,
                             1,
                             "pipeline run compact launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineFilterReduceLaunchCount,
                             1,
                             "pipeline filter reduce launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineCandidatePrefixLaunchCount,
                             1,
                             "pipeline candidate prefix launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineCandidateCompactLaunchCount,
                             1,
                             "pipeline candidate compact launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineCountSnapshotLaunchCount,
                             0,
                             "pipeline count snapshot launches") && ok;
    ok = expect_equal_uint64(dpBucketTotal,
                             1,
                             "pipeline dp bucket total") && ok;
    ok = expect_positive_double(batchResult.regionSingleRequestDirectReducePipelineDiagGpuSeconds,
                                "pipeline diag seconds") && ok;
    ok = expect_nonnegative_double(batchResult.regionSingleRequestDirectReducePipelineEventCountGpuSeconds,
                                   "pipeline event count seconds") && ok;
    ok = expect_nonnegative_double(batchResult.regionSingleRequestDirectReducePipelineRunCompactGpuSeconds,
                                   "pipeline run compact seconds") && ok;
    ok = expect_nonnegative_double(batchResult.regionSingleRequestDirectReducePipelineUnaccountedGpuSeconds,
                                   "pipeline unaccounted seconds") && ok;
    return ok;
}

static bool test_direct_reduce_pipeline_telemetry_records_deferred_snapshot()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "ACGTAAAACGT";
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));

    clear_direct_env();
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY", "1", 1);
    SimScanCudaRequest request = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> requests(1, request);
    SimScanCudaRegionAggregationResult result;
    SimScanCudaBatchResult batchResult;
    if (!run_region_aggregated(requests, &result, &batchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_true(batchResult.usedRegionSingleRequestDirectReduceDeferredCounts,
                          "pipeline deferred path used") && true;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineRequestCount,
                             1,
                             "pipeline deferred request count") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineCountSnapshotLaunchCount,
                             1,
                             "pipeline deferred snapshot launches") && ok;
    ok = expect_nonnegative_double(
           batchResult.regionSingleRequestDirectReducePipelineCountSnapshotD2HSeconds,
           "pipeline deferred snapshot d2h seconds") && ok;
    return ok;
}

static bool test_direct_reduce_deferred_counts_match_authoritative()
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
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS", "1", 1);
    SimScanCudaRequest deferredRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> deferredRequests(1, deferredRequest);
    SimScanCudaRegionAggregationResult deferredResult;
    SimScanCudaBatchResult deferredBatchResult;
    if (!run_region_aggregated(deferredRequests, &deferredResult, &deferredBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(deferredResult, baselineResult, "deferred") && true;
    ok = expect_true(deferredBatchResult.usedRegionSingleRequestDirectReducePath,
                     "deferred direct path used") && ok;
    ok = expect_true(deferredBatchResult.usedRegionSingleRequestDirectReduceDeferredCounts,
                     "deferred count path used") && ok;
    ok = expect_zero_double(deferredBatchResult.regionSingleRequestDirectReduceCandidateCountD2HSeconds,
                            "deferred candidate-count d2h seconds") && ok;
    ok = expect_nonnegative_double(
           deferredBatchResult.regionSingleRequestDirectReduceDeferredCountSnapshotD2HSeconds,
           "deferred count snapshot d2h seconds") && ok;
    ok = expect_equal_uint64(deferredBatchResult.regionSingleRequestDirectReduceCandidateCount,
                             static_cast<uint64_t>(deferredResult.candidateStates.size()),
                             "deferred candidate count") && ok;
    return ok;
}

static bool test_direct_reduce_deferred_counts_handles_zero_candidates()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "TTTTTTTT";
    const int eventScoreFloor = 1000000;
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));

    clear_direct_env();
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY", "1", 1);
    SimScanCudaRequest request =
      make_region_request(query, target, scoreMatrix, &filter, eventScoreFloor);
    std::vector<SimScanCudaRequest> requests(1, request);
    SimScanCudaRegionAggregationResult result;
    SimScanCudaBatchResult batchResult;
    if (!run_region_aggregated(requests, &result, &batchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_true(batchResult.usedRegionSingleRequestDirectReducePath,
                          "zero deferred direct path used") && true;
    ok = expect_true(batchResult.usedRegionSingleRequestDirectReduceDeferredCounts,
                     "zero deferred count path used") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(result.candidateStates.size()),
                             0,
                             "zero deferred candidate state size") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReduceCandidateCount,
                             0,
                             "zero deferred candidate count") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineFilterReduceLaunchCount,
                             0,
                             "zero deferred filter-reduce launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineCandidatePrefixLaunchCount,
                             0,
                             "zero deferred candidate-prefix launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineCandidateCompactLaunchCount,
                             0,
                             "zero deferred candidate-compact launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineCountSnapshotLaunchCount,
                             0,
                             "zero deferred count-snapshot launches") && ok;
    ok = expect_zero_double(batchResult.regionSingleRequestDirectReduceCandidateCountD2HSeconds,
                            "zero deferred candidate-count d2h seconds") && ok;
    return ok;
}

static bool test_direct_reduce_zero_candidates_skips_compact_buffer_ensure()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "TTTTTTTT";
    const int eventScoreFloor = 1000000;
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));

    clear_direct_env();
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY", "1", 1);
    SimScanCudaRequest request =
      make_region_request(query, target, scoreMatrix, &filter, eventScoreFloor);
    std::vector<SimScanCudaRequest> requests(1, request);
    SimScanCudaRegionAggregationResult result;
    SimScanCudaBatchResult batchResult;
    if (!run_region_aggregated(requests, &result, &batchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_true(batchResult.usedRegionSingleRequestDirectReducePath,
                          "zero direct path used") && true;
    ok = expect_false(batchResult.usedRegionSingleRequestDirectReduceDeferredCounts,
                      "zero direct deferred count path not used") && ok;
    ok = expect_equal_uint64(static_cast<uint64_t>(result.candidateStates.size()),
                             0,
                             "zero direct candidate state size") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReduceCandidateCount,
                             0,
                             "zero direct candidate count") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReduceRunSummaryCount,
                             0,
                             "zero direct run summary count") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineRequestCount,
                             1,
                             "zero direct pipeline request count") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineEventCountLaunchCount,
                             0,
                             "zero direct event-count launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineEventPrefixLaunchCount,
                             0,
                             "zero direct event-prefix launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineRunCompactLaunchCount,
                             0,
                             "zero direct run-compact launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineFilterReduceLaunchCount,
                             0,
                             "zero direct filter-reduce launches") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineCandidatePrefixLaunchCount,
                             0,
                             "zero direct candidate-prefix launches") && ok;
    ok = expect_equal_uint64(
           batchResult.regionSingleRequestDirectReduceZeroRunEventCountD2HSkips,
           1,
           "zero direct event-count d2h skip") && ok;
    ok = expect_equal_uint64(
           batchResult.regionSingleRequestDirectReduceZeroCandidateCompactBufferEnsureSkips,
           1,
           "zero direct compact buffer ensure skip") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineCandidateCompactLaunchCount,
                             0,
                             "zero direct candidate compact launches") && ok;
    ok = expect_zero_double(batchResult.regionSingleRequestDirectReduceFilterReduceGpuSeconds,
                            "zero direct filter-reduce gpu seconds") && ok;
    ok = expect_zero_double(batchResult.regionSingleRequestDirectReduceCandidateCountD2HSeconds,
                            "zero direct candidate-count d2h seconds") && ok;
    ok = expect_zero_double(batchResult.regionSingleRequestDirectReducePipelineCandidatePrefixGpuSeconds,
                            "zero direct candidate-prefix gpu seconds") && ok;
    ok = expect_zero_double(batchResult.regionSingleRequestDirectReducePipelineCandidateCompactGpuSeconds,
                            "zero direct candidate compact gpu seconds") && ok;
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
    ok = expect_equal_uint64(directBatchResult.regionSingleRequestDirectReducePipelineRequestCount,
                             0,
                             "overflow pipeline request count") && ok;
    return ok;
}

static bool test_fused_dp_counters_disabled_by_default()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "ACGTAAAACGT";
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));

    clear_direct_env();
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY", "1", 1);
    SimScanCudaRequest request = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> requests(1, request);
    SimScanCudaRegionAggregationResult result;
    SimScanCudaBatchResult batchResult;
    if (!run_region_aggregated(requests, &result, &batchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    const uint64_t diagCount =
      static_cast<uint64_t>(query.size()) + static_cast<uint64_t>(target.size()) - 1;
    bool ok = expect_true(batchResult.usedRegionSingleRequestDirectReducePath,
                          "fused disabled direct path used") && true;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReduceFusedDpAttempts,
                             0,
                             "fused disabled attempts") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReduceFusedDpSuccesses,
                             0,
                             "fused disabled successes") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReduceFusedDpDiagLaunchesReplaced,
                             0,
                             "fused disabled diag launches replaced") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReducePipelineDiagLaunchCount,
                             diagCount,
                             "fused disabled pipeline diag launches") && ok;
    ok = expect_zero_double(batchResult.regionSingleRequestDirectReduceFusedDpGpuSeconds,
                            "fused disabled dp seconds") && ok;
    return ok;
}

static bool test_fused_dp_matches_authoritative_small_request()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "ACGTAAAACGT";
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));
    const uint64_t rowCount = static_cast<uint64_t>(query.size());
    const uint64_t colCount = static_cast<uint64_t>(target.size());
    const uint64_t diagCount = rowCount + colCount - 1;

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
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY", "1", 1);
    SimScanCudaRequest fusedRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> fusedRequests(1, fusedRequest);
    SimScanCudaRegionAggregationResult fusedResult;
    SimScanCudaBatchResult fusedBatchResult;
    if (!run_region_aggregated(fusedRequests, &fusedResult, &fusedBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(fusedResult, baselineResult, "fused small") && true;
    ok = expect_true(fusedBatchResult.usedRegionSingleRequestDirectReducePath,
                     "fused small direct path used") && ok;
    ok = expect_equal_uint64(fusedBatchResult.regionSingleRequestDirectReduceFusedDpAttempts,
                             1,
                             "fused small attempts") && ok;
    ok = expect_equal_uint64(fusedBatchResult.regionSingleRequestDirectReduceFusedDpEligible,
                             1,
                             "fused small eligible") && ok;
    ok = expect_equal_uint64(fusedBatchResult.regionSingleRequestDirectReduceFusedDpSuccesses,
                             1,
                             "fused small successes") && ok;
    ok = expect_equal_uint64(fusedBatchResult.regionSingleRequestDirectReduceFusedDpFallbacks,
                             0,
                             "fused small fallbacks") && ok;
    ok = expect_equal_uint64(fusedBatchResult.regionSingleRequestDirectReduceFusedDpRequests,
                             1,
                             "fused small requests") && ok;
    ok = expect_equal_uint64(fusedBatchResult.regionSingleRequestDirectReduceFusedDpCells,
                             rowCount * colCount,
                             "fused small cells") && ok;
    ok = expect_equal_uint64(fusedBatchResult.regionSingleRequestDirectReduceFusedDpDiagLaunchesReplaced,
                             diagCount,
                             "fused small diag launches replaced") && ok;
    ok = expect_equal_uint64(fusedBatchResult.regionSingleRequestDirectReducePipelineDiagLaunchCount,
                             1,
                             "fused small pipeline diag launches") && ok;
    ok = expect_positive_double(fusedBatchResult.regionSingleRequestDirectReduceFusedDpGpuSeconds,
                                "fused small dp seconds") && ok;
    ok = expect_positive_double(fusedBatchResult.regionSingleRequestDirectReduceFusedTotalGpuSeconds,
                                "fused small total seconds") && ok;
    return ok;
}

static bool test_fused_dp_deferred_counts_match_authoritative()
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
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS", "1", 1);
    SimScanCudaRequest fusedRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> fusedRequests(1, fusedRequest);
    SimScanCudaRegionAggregationResult fusedResult;
    SimScanCudaBatchResult fusedBatchResult;
    if (!run_region_aggregated(fusedRequests, &fusedResult, &fusedBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(fusedResult, baselineResult, "fused deferred") && true;
    ok = expect_true(fusedBatchResult.usedRegionSingleRequestDirectReduceDeferredCounts,
                     "fused deferred count path used") && ok;
    ok = expect_equal_uint64(fusedBatchResult.regionSingleRequestDirectReduceFusedDpSuccesses,
                             1,
                             "fused deferred successes") && ok;
    ok = expect_zero_double(fusedBatchResult.regionSingleRequestDirectReduceCandidateCountD2HSeconds,
                            "fused deferred candidate-count d2h seconds") && ok;
    return ok;
}

static bool test_fused_dp_threshold_rejections_fall_back()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "ACGTAAAACGT";
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));
    const uint64_t diagCount =
      static_cast<uint64_t>(query.size()) + static_cast<uint64_t>(target.size()) - 1;

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
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP_MAX_CELLS", "1", 1);
    SimScanCudaRequest cellsRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> cellsRequests(1, cellsRequest);
    SimScanCudaRegionAggregationResult cellsResult;
    SimScanCudaBatchResult cellsBatchResult;
    if (!run_region_aggregated(cellsRequests, &cellsResult, &cellsBatchResult))
    {
        clear_direct_env();
        return false;
    }

    unsetenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP_MAX_CELLS");
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP_MAX_DIAG_LEN", "1", 1);
    SimScanCudaRequest diagRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> diagRequests(1, diagRequest);
    SimScanCudaRegionAggregationResult diagResult;
    SimScanCudaBatchResult diagBatchResult;
    if (!run_region_aggregated(diagRequests, &diagResult, &diagBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(cellsResult, baselineResult, "fused max-cells fallback") && true;
    ok = expect_region_results_equal(diagResult, baselineResult, "fused max-diag fallback") && ok;
    ok = expect_equal_uint64(cellsBatchResult.regionSingleRequestDirectReduceFusedDpAttempts,
                             1,
                             "fused max-cells attempts") && ok;
    ok = expect_equal_uint64(cellsBatchResult.regionSingleRequestDirectReduceFusedDpEligible,
                             0,
                             "fused max-cells eligible") && ok;
    ok = expect_equal_uint64(cellsBatchResult.regionSingleRequestDirectReduceFusedDpFallbacks,
                             1,
                             "fused max-cells fallbacks") && ok;
    ok = expect_equal_uint64(cellsBatchResult.regionSingleRequestDirectReduceFusedDpRejectedByCells,
                             1,
                             "fused max-cells rejection") && ok;
    ok = expect_equal_uint64(cellsBatchResult.regionSingleRequestDirectReducePipelineDiagLaunchCount,
                             diagCount,
                             "fused max-cells pipeline diag launches") && ok;
    ok = expect_equal_uint64(diagBatchResult.regionSingleRequestDirectReduceFusedDpRejectedByDiagLen,
                             1,
                             "fused max-diag rejection") && ok;
    ok = expect_equal_uint64(diagBatchResult.regionSingleRequestDirectReducePipelineDiagLaunchCount,
                             diagCount,
                             "fused max-diag pipeline diag launches") && ok;
    return ok;
}

static bool test_fused_dp_shadow_matches_direct_oracle()
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
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP_SHADOW", "1", 1);
    SimScanCudaRequest shadowRequest =
      make_region_request(query, target, scoreMatrix, &filter, eventScoreFloor);
    std::vector<SimScanCudaRequest> shadowRequests(1, shadowRequest);
    SimScanCudaRegionAggregationResult shadowResult;
    SimScanCudaBatchResult shadowBatchResult;
    if (!run_region_aggregated(shadowRequests, &shadowResult, &shadowBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(shadowResult, baselineResult, "fused shadow") && true;
    ok = expect_equal_uint64(shadowBatchResult.regionSingleRequestDirectReduceFusedDpAttempts,
                             1,
                             "fused shadow attempts") && ok;
    ok = expect_equal_uint64(shadowBatchResult.regionSingleRequestDirectReduceFusedDpSuccesses,
                             1,
                             "fused shadow successes") && ok;
    ok = expect_equal_uint64(shadowBatchResult.regionSingleRequestDirectReduceFusedDpShadowMismatches,
                             0,
                             "fused shadow mismatches") && ok;
    ok = expect_positive_double(
           shadowBatchResult.regionSingleRequestDirectReduceFusedOracleDpGpuSecondsShadow,
           "fused shadow oracle dp seconds") && ok;
    return ok;
}

static bool test_coop_dp_counters_disabled_by_default()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGT";
    const std::string target = "ACGTAAAACGT";
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));

    clear_direct_env();
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY", "1", 1);
    SimScanCudaRequest request = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> requests(1, request);
    SimScanCudaRegionAggregationResult result;
    SimScanCudaBatchResult batchResult;
    if (!run_region_aggregated(requests, &result, &batchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_true(batchResult.usedRegionSingleRequestDirectReducePath,
                          "coop disabled direct path used") && true;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReduceCoopDpAttempts,
                             0,
                             "coop disabled attempts") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReduceCoopDpSuccesses,
                             0,
                             "coop disabled successes") && ok;
    ok = expect_equal_uint64(batchResult.regionSingleRequestDirectReduceCoopDpDiagLaunchesReplaced,
                             0,
                             "coop disabled diag launches replaced") && ok;
    ok = expect_zero_double(batchResult.regionSingleRequestDirectReduceCoopDpGpuSeconds,
                            "coop disabled dp seconds") && ok;
    return ok;
}

static bool test_coop_dp_matches_authoritative_when_single_block_rejects()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGTACGTACGT";
    const std::string target = "ACGTAAAACGTACGTG";
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));
    const uint64_t rowCount = static_cast<uint64_t>(query.size());
    const uint64_t colCount = static_cast<uint64_t>(target.size());
    const uint64_t diagCount = rowCount + colCount - 1;

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
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_FUSED_DP_MAX_DIAG_LEN", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY", "1", 1);
    SimScanCudaRequest coopRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> coopRequests(1, coopRequest);
    SimScanCudaRegionAggregationResult coopResult;
    SimScanCudaBatchResult coopBatchResult;
    if (!run_region_aggregated(coopRequests, &coopResult, &coopBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(coopResult, baselineResult, "coop") && true;
    ok = expect_equal_uint64(coopBatchResult.regionSingleRequestDirectReduceFusedDpSuccesses,
                             0,
                             "coop fused successes") && ok;
    ok = expect_equal_uint64(coopBatchResult.regionSingleRequestDirectReduceCoopDpAttempts,
                             1,
                             "coop attempts") && ok;
    ok = expect_equal_uint64(coopBatchResult.regionSingleRequestDirectReduceCoopDpEligible,
                             1,
                             "coop eligible") && ok;
    ok = expect_equal_uint64(coopBatchResult.regionSingleRequestDirectReduceCoopDpSuccesses,
                             1,
                             "coop successes") && ok;
    ok = expect_equal_uint64(coopBatchResult.regionSingleRequestDirectReduceCoopDpFallbacks,
                             0,
                             "coop fallbacks") && ok;
    ok = expect_equal_uint64(coopBatchResult.regionSingleRequestDirectReduceCoopDpRequests,
                             1,
                             "coop requests") && ok;
    ok = expect_equal_uint64(coopBatchResult.regionSingleRequestDirectReduceCoopDpCells,
                             rowCount * colCount,
                             "coop cells") && ok;
    ok = expect_equal_uint64(coopBatchResult.regionSingleRequestDirectReduceCoopDpDiagLaunchesReplaced,
                             diagCount,
                             "coop diag launches replaced") && ok;
    ok = expect_equal_uint64(coopBatchResult.regionSingleRequestDirectReducePipelineDiagLaunchCount,
                             1,
                             "coop pipeline diag launches") && ok;
    ok = expect_positive_double(coopBatchResult.regionSingleRequestDirectReduceCoopDpGpuSeconds,
                                "coop dp seconds") && ok;
    ok = expect_positive_double(coopBatchResult.regionSingleRequestDirectReduceCoopTotalGpuSeconds,
                                "coop total seconds") && ok;
    return ok;
}

static bool test_coop_dp_deferred_counts_match_authoritative()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGTACGTACGT";
    const std::string target = "ACGTAAAACGTACGTG";
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
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS", "1", 1);
    SimScanCudaRequest coopRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> coopRequests(1, coopRequest);
    SimScanCudaRegionAggregationResult coopResult;
    SimScanCudaBatchResult coopBatchResult;
    if (!run_region_aggregated(coopRequests, &coopResult, &coopBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(coopResult, baselineResult, "coop deferred") && true;
    ok = expect_true(coopBatchResult.usedRegionSingleRequestDirectReduceDeferredCounts,
                     "coop deferred count path used") && ok;
    ok = expect_equal_uint64(coopBatchResult.regionSingleRequestDirectReduceCoopDpSuccesses,
                             1,
                             "coop deferred successes") && ok;
    ok = expect_zero_double(coopBatchResult.regionSingleRequestDirectReduceCandidateCountD2HSeconds,
                            "coop deferred candidate-count d2h seconds") && ok;
    return ok;
}

static bool test_coop_dp_threshold_rejections_fall_back()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "ACGTACGTACGTACGT";
    const std::string target = "ACGTAAAACGTACGTG";
    const std::vector<uint64_t> filter =
      all_start_coords(static_cast<int>(query.size()), static_cast<int>(target.size()));
    const uint64_t diagCount =
      static_cast<uint64_t>(query.size()) + static_cast<uint64_t>(target.size()) - 1;

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
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_PIPELINE_TELEMETRY", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP_MAX_CELLS", "1", 1);
    SimScanCudaRequest cellsRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> cellsRequests(1, cellsRequest);
    SimScanCudaRegionAggregationResult cellsResult;
    SimScanCudaBatchResult cellsBatchResult;
    if (!run_region_aggregated(cellsRequests, &cellsResult, &cellsBatchResult))
    {
        clear_direct_env();
        return false;
    }

    unsetenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP_MAX_CELLS");
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP_MAX_DIAG_LEN", "1", 1);
    SimScanCudaRequest diagRequest = make_region_request(query, target, scoreMatrix, &filter);
    std::vector<SimScanCudaRequest> diagRequests(1, diagRequest);
    SimScanCudaRegionAggregationResult diagResult;
    SimScanCudaBatchResult diagBatchResult;
    if (!run_region_aggregated(diagRequests, &diagResult, &diagBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(cellsResult, baselineResult, "coop max-cells fallback") && true;
    ok = expect_region_results_equal(diagResult, baselineResult, "coop max-diag fallback") && ok;
    ok = expect_equal_uint64(cellsBatchResult.regionSingleRequestDirectReduceCoopDpAttempts,
                             1,
                             "coop max-cells attempts") && ok;
    ok = expect_equal_uint64(cellsBatchResult.regionSingleRequestDirectReduceCoopDpEligible,
                             0,
                             "coop max-cells eligible") && ok;
    ok = expect_equal_uint64(cellsBatchResult.regionSingleRequestDirectReduceCoopDpFallbacks,
                             1,
                             "coop max-cells fallbacks") && ok;
    ok = expect_equal_uint64(cellsBatchResult.regionSingleRequestDirectReduceCoopDpRejectedByCells,
                             1,
                             "coop max-cells rejection") && ok;
    ok = expect_equal_uint64(cellsBatchResult.regionSingleRequestDirectReducePipelineDiagLaunchCount,
                             diagCount,
                             "coop max-cells pipeline diag launches") && ok;
    ok = expect_equal_uint64(diagBatchResult.regionSingleRequestDirectReduceCoopDpRejectedByDiagLen,
                             1,
                             "coop max-diag rejection") && ok;
    ok = expect_equal_uint64(diagBatchResult.regionSingleRequestDirectReducePipelineDiagLaunchCount,
                             diagCount,
                             "coop max-diag pipeline diag launches") && ok;
    return ok;
}

static bool test_coop_dp_shadow_matches_direct_oracle()
{
    int scoreMatrix[128][128];
    initialize_score_matrix(scoreMatrix);
    const std::string query = "AAAAAAAAAAAAAAAA";
    const std::string target = "AAAAATAAAAAAAAAA";
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
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_REGION_DIRECT_REDUCE_COOP_DP_SHADOW", "1", 1);
    SimScanCudaRequest shadowRequest =
      make_region_request(query, target, scoreMatrix, &filter, eventScoreFloor);
    std::vector<SimScanCudaRequest> shadowRequests(1, shadowRequest);
    SimScanCudaRegionAggregationResult shadowResult;
    SimScanCudaBatchResult shadowBatchResult;
    if (!run_region_aggregated(shadowRequests, &shadowResult, &shadowBatchResult))
    {
        clear_direct_env();
        return false;
    }
    clear_direct_env();

    bool ok = expect_region_results_equal(shadowResult, baselineResult, "coop shadow") && true;
    ok = expect_equal_uint64(shadowBatchResult.regionSingleRequestDirectReduceCoopDpAttempts,
                             1,
                             "coop shadow attempts") && ok;
    ok = expect_equal_uint64(shadowBatchResult.regionSingleRequestDirectReduceCoopDpSuccesses,
                             1,
                             "coop shadow successes") && ok;
    ok = expect_equal_uint64(shadowBatchResult.regionSingleRequestDirectReduceCoopDpShadowMismatches,
                             0,
                             "coop shadow mismatches") && ok;
    ok = expect_positive_double(
           shadowBatchResult.regionSingleRequestDirectReduceCoopOracleDpGpuSecondsShadow,
           "coop shadow oracle dp seconds") && ok;
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
    ok = test_direct_reduce_records_profile_telemetry() && ok;
    ok = test_direct_reduce_pipeline_telemetry_disabled_by_default() && ok;
    ok = test_direct_reduce_records_pipeline_telemetry() && ok;
    ok = test_direct_reduce_pipeline_telemetry_records_deferred_snapshot() && ok;
    ok = test_direct_reduce_deferred_counts_match_authoritative() && ok;
    ok = test_direct_reduce_deferred_counts_handles_zero_candidates() && ok;
    ok = test_direct_reduce_zero_candidates_skips_compact_buffer_ensure() && ok;
    ok = test_direct_reduce_shadow_matches_authoritative() && ok;
    ok = test_direct_reduce_matches_gapped_event_runs() && ok;
    ok = test_direct_reduce_matches_offset_region() && ok;
    ok = test_direct_reduce_falls_back_without_filter() && ok;
    ok = test_direct_reduce_overflow_falls_back() && ok;
    ok = test_fused_dp_counters_disabled_by_default() && ok;
    ok = test_fused_dp_matches_authoritative_small_request() && ok;
    ok = test_fused_dp_deferred_counts_match_authoritative() && ok;
    ok = test_fused_dp_threshold_rejections_fall_back() && ok;
    ok = test_fused_dp_shadow_matches_direct_oracle() && ok;
    ok = test_coop_dp_counters_disabled_by_default() && ok;
    ok = test_coop_dp_matches_authoritative_when_single_block_rejects() && ok;
    ok = test_coop_dp_deferred_counts_match_authoritative() && ok;
    ok = test_coop_dp_threshold_rejections_fall_back() && ok;
    ok = test_coop_dp_shadow_matches_direct_oracle() && ok;
    clear_direct_env();
    return ok ? 0 : 1;
}
