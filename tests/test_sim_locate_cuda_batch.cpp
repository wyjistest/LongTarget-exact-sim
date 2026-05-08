#include <cstring>
#include <iostream>
#include <string>
#include <vector>

#include "../cuda/sim_locate_cuda.h"

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

static bool expect_equal_bool(bool actual, bool expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << (expected ? "true" : "false")
              << ", got " << (actual ? "true" : "false") << "\n";
    return false;
}

static bool expect_equal_u64(uint64_t actual, uint64_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_equal_long(long actual, long expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_equal_size(size_t actual, size_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static void fill_score_matrix(int scoreMatrix[128][128])
{
    std::memset(scoreMatrix, 0, sizeof(int) * 128 * 128);
    scoreMatrix[static_cast<unsigned char>('A')][static_cast<unsigned char>('A')] = 2;
    scoreMatrix[static_cast<unsigned char>('C')][static_cast<unsigned char>('C')] = 2;
    scoreMatrix[static_cast<unsigned char>('G')][static_cast<unsigned char>('G')] = 2;
    scoreMatrix[static_cast<unsigned char>('T')][static_cast<unsigned char>('T')] = 2;
}

static SimLocateCudaRequest make_request(const std::string &query,
                                         const std::string &target,
                                         int scoreMatrix[128][128])
{
    SimLocateCudaRequest request;
    request.A = query.c_str();
    request.B = target.c_str();
    request.queryLength = static_cast<int>(query.size()) - 1;
    request.targetLength = static_cast<int>(target.size()) - 1;
    request.rowStart = 1;
    request.rowEnd = request.queryLength;
    request.colStart = 1;
    request.colEnd = request.targetLength;
    request.runningMin = 1;
    request.gapOpen = 3;
    request.gapExtend = 1;
    request.scoreMatrix = scoreMatrix;
    request.minRowBound = 1;
    request.minColBound = 1;
    return request;
}

} // namespace

int main()
{
    if (!sim_locate_cuda_is_built())
    {
        std::cerr << "CUDA locate support is not built\n";
        return 2;
    }

    std::string error;
    if (!sim_locate_cuda_init(0, &error))
    {
        std::cerr << "sim_locate_cuda_init failed: " << error << "\n";
        return 2;
    }

    int scoreMatrix[128][128];
    fill_score_matrix(scoreMatrix);
    const std::string query = " ACGT";
    const std::string target = " ACGT";
    const SimLocateCudaRequest request = make_request(query, target, scoreMatrix);

    SimLocateResult singleResult;
    error.clear();
    if (!sim_locate_cuda_locate_region(request, &singleResult, &error))
    {
        std::cerr << "single locate failed: " << error << "\n";
        return 1;
    }

    std::vector<SimLocateCudaRequest> batchRequests(1, request);
    std::vector<SimLocateResult> batchResults;
    SimLocateCudaBatchResult batchResult;
    error.clear();
    if (!sim_locate_cuda_locate_region_batch(batchRequests, &batchResults, &batchResult, &error))
    {
        std::cerr << "single-request locate batch failed: " << error << "\n";
        return 1;
    }

    bool ok = true;
    ok = expect_equal_size(batchResults.size(), 1, "single-request batch result size") && ok;
    ok = expect_equal_bool(batchResult.usedCuda, true, "single-request batch usedCuda") && ok;
    ok = expect_equal_u64(batchResult.taskCount, 1, "single-request batch taskCount") && ok;
    ok = expect_equal_u64(batchResult.launchCount, 1, "single-request batch launchCount") && ok;
    ok = expect_equal_bool(batchResult.usedSharedInputBatchPath,
                           false,
                           "single-request batch shared-input path") && ok;
    ok = expect_equal_u64(batchResult.singleRequestBatchSkips,
                          1,
                          "single-request batch skips batch allocation path") && ok;
    if (batchResults.size() == 1)
    {
        ok = expect_equal_bool(batchResults[0].usedCuda, true, "single-request batch result usedCuda") && ok;
        ok = expect_equal_bool(batchResults[0].hasUpdateRegion,
                               singleResult.hasUpdateRegion,
                               "single-request batch hasUpdateRegion") && ok;
        ok = expect_equal_long(batchResults[0].rowStart, singleResult.rowStart, "single-request batch rowStart") && ok;
        ok = expect_equal_long(batchResults[0].rowEnd, singleResult.rowEnd, "single-request batch rowEnd") && ok;
        ok = expect_equal_long(batchResults[0].colStart, singleResult.colStart, "single-request batch colStart") && ok;
        ok = expect_equal_long(batchResults[0].colEnd, singleResult.colEnd, "single-request batch colEnd") && ok;
        ok = expect_equal_u64(batchResults[0].locateCellCount,
                              singleResult.locateCellCount,
                              "single-request batch locateCellCount") && ok;
        ok = expect_equal_u64(batchResults[0].baseCellCount,
                              singleResult.baseCellCount,
                              "single-request batch baseCellCount") && ok;
        ok = expect_equal_u64(batchResults[0].expansionCellCount,
                              singleResult.expansionCellCount,
                              "single-request batch expansionCellCount") && ok;
    }

    return ok ? 0 : 1;
}
