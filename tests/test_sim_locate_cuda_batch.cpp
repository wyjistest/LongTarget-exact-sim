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

    std::vector<SimLocateCudaRequest> sharedRequests;
    sharedRequests.push_back(request);
    sharedRequests.push_back(request);
    sharedRequests[1].rowStart = 2;
    sharedRequests[1].colStart = 2;
    std::vector<uint64_t> blockedWords(static_cast<size_t>(request.queryLength + 1), 0);
    std::vector<SimScanCudaCandidateState> candidates(1);
    candidates[0].score = 1;
    candidates[0].startI = request.queryLength + 2;
    candidates[0].startJ = request.targetLength + 2;
    candidates[0].endI = request.queryLength + 2;
    candidates[0].endJ = request.targetLength + 2;
    candidates[0].top = request.queryLength + 2;
    candidates[0].bot = request.queryLength + 2;
    candidates[0].left = request.targetLength + 2;
    candidates[0].right = request.targetLength + 2;
    for (size_t i = 0; i < sharedRequests.size(); ++i)
    {
        sharedRequests[i].blockedWords = blockedWords.data();
        sharedRequests[i].blockedWordStride = 1;
        sharedRequests[i].candidates = candidates.data();
        sharedRequests[i].candidateCount = static_cast<int>(candidates.size());
    }

    batchResults.clear();
    batchResult = SimLocateCudaBatchResult();
    error.clear();
    if (!sim_locate_cuda_locate_region_batch(sharedRequests, &batchResults, &batchResult, &error))
    {
        std::cerr << "shared-input locate batch failed: " << error << "\n";
        return 1;
    }
    ok = expect_equal_bool(batchResult.usedSharedInputBatchPath,
                           true,
                           "shared-input batch path") && ok;
    ok = expect_equal_u64(batchResult.inputH2DCopies,
                          2,
                          "first shared-input batch uploads query and target") && ok;
    ok = expect_equal_u64(batchResult.inputH2DCacheHits,
                          0,
                          "first shared-input batch has no input cache hit") && ok;
    ok = expect_equal_u64(batchResult.scoreMatrixH2DCopies,
                          1,
                          "first shared-input batch uploads score matrix") && ok;
    ok = expect_equal_u64(batchResult.scoreMatrixH2DCacheHits,
                          0,
                          "first shared-input batch has no score matrix cache hit") && ok;
    ok = expect_equal_u64(batchResult.blockedWordsH2DCopies,
                          1,
                          "first shared-input batch uploads blocked words") && ok;
    ok = expect_equal_u64(batchResult.blockedWordsH2DCacheHits,
                          0,
                          "first shared-input batch has no blocked words cache hit") && ok;
    ok = expect_equal_u64(batchResult.candidateH2DCopies,
                          1,
                          "first shared-input batch uploads candidates") && ok;
    ok = expect_equal_u64(batchResult.candidateH2DCacheHits,
                          0,
                          "first shared-input batch has no candidate cache hit") && ok;
    ok = expect_equal_u64(batchResult.requestH2DCopies,
                          1,
                          "first shared-input batch uploads request metadata") && ok;
    ok = expect_equal_u64(batchResult.requestH2DCacheHits,
                          0,
                          "first shared-input batch has no request metadata cache hit") && ok;

    batchResults.clear();
    batchResult = SimLocateCudaBatchResult();
    error.clear();
    if (!sim_locate_cuda_locate_region_batch(sharedRequests, &batchResults, &batchResult, &error))
    {
        std::cerr << "cached shared-input locate batch failed: " << error << "\n";
        return 1;
    }
    ok = expect_equal_bool(batchResult.usedSharedInputBatchPath,
                           true,
                           "cached shared-input batch path") && ok;
    ok = expect_equal_u64(batchResult.inputH2DCopies,
                          0,
                          "cached shared-input batch skips query and target uploads") && ok;
    ok = expect_equal_u64(batchResult.inputH2DCacheHits,
                          2,
                          "cached shared-input batch records input cache hits") && ok;
    ok = expect_equal_u64(batchResult.scoreMatrixH2DCopies,
                          0,
                          "cached shared-input batch skips score matrix upload") && ok;
    ok = expect_equal_u64(batchResult.scoreMatrixH2DCacheHits,
                          1,
                          "cached shared-input batch records score matrix cache hit") && ok;
    ok = expect_equal_u64(batchResult.blockedWordsH2DCopies,
                          0,
                          "cached shared-input batch skips blocked words upload") && ok;
    ok = expect_equal_u64(batchResult.blockedWordsH2DCacheHits,
                          1,
                          "cached shared-input batch records blocked words cache hit") && ok;
    ok = expect_equal_u64(batchResult.candidateH2DCopies,
                          0,
                          "cached shared-input batch skips candidate upload") && ok;
    ok = expect_equal_u64(batchResult.candidateH2DCacheHits,
                          1,
                          "cached shared-input batch records candidate cache hit") && ok;
    ok = expect_equal_u64(batchResult.requestH2DCopies,
                          0,
                          "cached shared-input batch skips request metadata upload") && ok;
    ok = expect_equal_u64(batchResult.requestH2DCacheHits,
                          1,
                          "cached shared-input batch records request metadata cache hit") && ok;

    std::vector<SimLocateCudaRequest> runningMinRequests;
    runningMinRequests.push_back(request);
    runningMinRequests.push_back(request);
    runningMinRequests[1].runningMin = request.runningMin + 1;
    batchResults.clear();
    batchResult = SimLocateCudaBatchResult();
    error.clear();
    if (!sim_locate_cuda_locate_region_batch(runningMinRequests, &batchResults, &batchResult, &error))
    {
        std::cerr << "runningMin-differing locate batch failed: " << error << "\n";
        return 1;
    }
    ok = expect_equal_bool(batchResult.usedSharedInputBatchPath,
                           true,
                           "runningMin-differing batch still shares inputs") && ok;
    ok = expect_equal_u64(batchResult.launchCount,
                          1,
                          "runningMin-differing batch uses one launch") && ok;

    std::vector<SimLocateCudaRequest> gapRequests;
    gapRequests.push_back(request);
    gapRequests.push_back(request);
    gapRequests[1].gapOpen = request.gapOpen + 1;
    gapRequests[1].gapExtend = request.gapExtend + 1;
    batchResults.clear();
    batchResult = SimLocateCudaBatchResult();
    error.clear();
    if (!sim_locate_cuda_locate_region_batch(gapRequests, &batchResults, &batchResult, &error))
    {
        std::cerr << "gap-differing locate batch failed: " << error << "\n";
        return 1;
    }
    ok = expect_equal_bool(batchResult.usedSharedInputBatchPath,
                           true,
                           "gap-differing batch still shares inputs") && ok;
    ok = expect_equal_u64(batchResult.launchCount,
                          1,
                          "gap-differing batch uses one launch") && ok;

    const std::string queryCopy = query;
    const std::string targetCopy = target;
    std::vector<SimLocateCudaRequest> copiedInputRequests;
    copiedInputRequests.push_back(request);
    copiedInputRequests.push_back(make_request(queryCopy, targetCopy, scoreMatrix));
    batchResults.clear();
    batchResult = SimLocateCudaBatchResult();
    error.clear();
    if (!sim_locate_cuda_locate_region_batch(copiedInputRequests, &batchResults, &batchResult, &error))
    {
        std::cerr << "copied-input locate batch failed: " << error << "\n";
        return 1;
    }
    ok = expect_equal_bool(batchResult.usedSharedInputBatchPath,
                           true,
                           "copied-input batch still shares input content") && ok;
    ok = expect_equal_u64(batchResult.launchCount,
                          1,
                          "copied-input batch uses one launch") && ok;

    int scoreMatrixCopy[128][128];
    fill_score_matrix(scoreMatrixCopy);
    std::vector<SimLocateCudaRequest> copiedMatrixRequests;
    copiedMatrixRequests.push_back(request);
    copiedMatrixRequests.push_back(make_request(query, target, scoreMatrixCopy));
    batchResults.clear();
    batchResult = SimLocateCudaBatchResult();
    error.clear();
    if (!sim_locate_cuda_locate_region_batch(copiedMatrixRequests, &batchResults, &batchResult, &error))
    {
        std::cerr << "copied-matrix locate batch failed: " << error << "\n";
        return 1;
    }
    ok = expect_equal_bool(batchResult.usedSharedInputBatchPath,
                           true,
                           "copied-matrix batch still shares matrix content") && ok;
    ok = expect_equal_u64(batchResult.launchCount,
                          1,
                          "copied-matrix batch uses one launch") && ok;

    std::vector<uint64_t> blockedWordsCopy(blockedWords.size(), 0);
    std::vector<SimLocateCudaRequest> copiedBlockedRequests;
    copiedBlockedRequests.push_back(request);
    copiedBlockedRequests.push_back(request);
    copiedBlockedRequests[0].blockedWords = blockedWords.data();
    copiedBlockedRequests[0].blockedWordStride = 1;
    copiedBlockedRequests[1].blockedWords = blockedWordsCopy.data();
    copiedBlockedRequests[1].blockedWordStride = 1;
    batchResults.clear();
    batchResult = SimLocateCudaBatchResult();
    error.clear();
    if (!sim_locate_cuda_locate_region_batch(copiedBlockedRequests, &batchResults, &batchResult, &error))
    {
        std::cerr << "copied-blocked locate batch failed: " << error << "\n";
        return 1;
    }
    ok = expect_equal_bool(batchResult.usedSharedInputBatchPath,
                           true,
                           "copied-blocked batch still shares blocked word content") && ok;
    ok = expect_equal_u64(batchResult.launchCount,
                          1,
                          "copied-blocked batch uses one launch") && ok;

    return ok ? 0 : 1;
}
