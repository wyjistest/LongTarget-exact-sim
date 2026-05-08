#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

#include "../cuda/sim_traceback_cuda.h"

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

static bool expect_equal_int(int actual, int expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
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

static bool expect_equal_size(size_t actual, size_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_ops_equal(const std::vector<unsigned char> &actual,
                             const std::vector<unsigned char> &expected,
                             const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": ops mismatch\n";
    return false;
}

static SimTracebackCudaBatchRequest make_request(const std::string &query,
                                                 const std::string &target)
{
    SimTracebackCudaBatchRequest request;
    request.A = query.c_str();
    request.B = target.c_str();
    request.queryLength = static_cast<int>(query.size()) - 1;
    request.targetLength = static_cast<int>(target.size()) - 1;
    request.matchScore = 10;
    request.mismatchScore = -10;
    request.gapOpen = 10;
    request.gapExtend = 10;
    request.globalColStart = 1;
    return request;
}

} // namespace

int main()
{
    SimTracebackCudaBatchRequest defaultRequest;
    bool ok = true;
    ok = expect_equal_bool(defaultRequest.A == NULL, true, "default batch A") && ok;
    ok = expect_equal_bool(defaultRequest.B == NULL, true, "default batch B") && ok;
    ok = expect_equal_int(defaultRequest.queryLength, 0, "default batch queryLength") && ok;
    ok = expect_equal_int(defaultRequest.targetLength, 0, "default batch targetLength") && ok;
    ok = expect_equal_bool(defaultRequest.blockedWords == NULL, true, "default batch blockedWords") && ok;

    SimTracebackCudaBatchResult emptyBatchResult;
    ok = expect_equal_bool(emptyBatchResult.usedCuda, false, "default batch usedCuda") && ok;
    ok = expect_equal_uint64(emptyBatchResult.requestCount, 0, "default batch requestCount") && ok;
    ok = expect_equal_uint64(emptyBatchResult.successCount, 0, "default batch successCount") && ok;
    ok = expect_equal_uint64(emptyBatchResult.cudaCount, 0, "default batch cudaCount") && ok;

    std::vector<SimTracebackCudaBatchRequest> emptyRequests;
    std::vector<SimTracebackCudaBatchItemResult> emptyResults;
    std::string error;
    if (!sim_traceback_cuda_traceback_global_affine_batch(emptyRequests,
                                                          &emptyResults,
                                                          &emptyBatchResult,
                                                          &error))
    {
        std::cerr << "empty batch should succeed, got error: " << error << "\n";
        return 1;
    }
    ok = expect_equal_size(emptyResults.size(), 0, "empty batch results") && ok;
    ok = expect_true(error.empty(), "empty batch error") && ok;

    const std::string emptyQuery = " ";
    const std::string emptyTarget = " ";
    const std::string insertOnlyTarget = " ACG";
    const std::string deleteOnlyQuery = " ACG";
    std::vector<SimTracebackCudaBatchRequest> gapOnlyRequests;
    gapOnlyRequests.push_back(make_request(emptyQuery, insertOnlyTarget));
    gapOnlyRequests.push_back(make_request(deleteOnlyQuery, emptyTarget));
    std::vector<SimTracebackCudaBatchItemResult> gapOnlyResults;
    SimTracebackCudaBatchResult gapOnlyBatchResult;
    error.clear();
    if (!sim_traceback_cuda_traceback_global_affine_batch(gapOnlyRequests,
                                                          &gapOnlyResults,
                                                          &gapOnlyBatchResult,
                                                          &error))
    {
        std::cerr << "gap-only batch should succeed, got error: " << error << "\n";
        return 1;
    }
    const std::vector<unsigned char> expectedInsertOnlyOps(3, 1);
    const std::vector<unsigned char> expectedDeleteOnlyOps(3, 2);
    ok = expect_equal_size(gapOnlyResults.size(), 2, "gap-only batch results") && ok;
    ok = expect_equal_uint64(gapOnlyBatchResult.requestCount, 2, "gap-only batch requestCount") && ok;
    ok = expect_equal_uint64(gapOnlyBatchResult.successCount, 2, "gap-only batch successCount") && ok;
    ok = expect_equal_uint64(gapOnlyBatchResult.cudaCount, 0, "gap-only batch cudaCount skipped") && ok;
    ok = expect_equal_bool(gapOnlyBatchResult.usedCuda, false, "gap-only batch usedCuda skipped") && ok;
    if (gapOnlyResults.size() == 2)
    {
        ok = expect_equal_bool(gapOnlyResults[0].success, true, "gap-only result 0 success") && ok;
        ok = expect_equal_bool(gapOnlyResults[1].success, true, "gap-only result 1 success") && ok;
        ok = expect_equal_bool(gapOnlyResults[0].tracebackResult.usedCuda,
                               false,
                               "gap-only result 0 usedCuda skipped") && ok;
        ok = expect_equal_bool(gapOnlyResults[1].tracebackResult.usedCuda,
                               false,
                               "gap-only result 1 usedCuda skipped") && ok;
        ok = expect_ops_equal(gapOnlyResults[0].opsReversed,
                              expectedInsertOnlyOps,
                              "gap-only result 0 ops") && ok;
        ok = expect_ops_equal(gapOnlyResults[1].opsReversed,
                              expectedDeleteOnlyOps,
                              "gap-only result 1 ops") && ok;
    }

    if (!sim_traceback_cuda_is_built())
    {
        std::cerr << "CUDA support is not built\n";
        return 2;
    }

    error.clear();
    if (!sim_traceback_cuda_init(0, &error))
    {
        std::cerr << "sim_traceback_cuda_init failed: " << error << "\n";
        return 2;
    }

    const std::string query0 = " AAAAA";
    const std::string target0 = " AAAAA";
    const std::string query1 = " ACGT";
    const std::string target1 = " AGGT";

    std::vector<unsigned char> singleInsertOnlyOps;
    std::vector<unsigned char> singleDeleteOnlyOps;
    SimTracebackCudaResult singleInsertOnlyResult;
    SimTracebackCudaResult singleDeleteOnlyResult;
    error.clear();
    if (!sim_traceback_cuda_traceback_global_affine(emptyQuery.c_str(),
                                                    insertOnlyTarget.c_str(),
                                                    static_cast<int>(emptyQuery.size()) - 1,
                                                    static_cast<int>(insertOnlyTarget.size()) - 1,
                                                    10,
                                                    -10,
                                                    10,
                                                    10,
                                                    1,
                                                    NULL,
                                                    0,
                                                    0,
                                                    0,
                                                    &singleInsertOnlyOps,
                                                    &singleInsertOnlyResult,
                                                    &error))
    {
        std::cerr << "single insert-only request failed: " << error << "\n";
        return 2;
    }
    error.clear();
    if (!sim_traceback_cuda_traceback_global_affine(deleteOnlyQuery.c_str(),
                                                    emptyTarget.c_str(),
                                                    static_cast<int>(deleteOnlyQuery.size()) - 1,
                                                    static_cast<int>(emptyTarget.size()) - 1,
                                                    10,
                                                    -10,
                                                    10,
                                                    10,
                                                    1,
                                                    NULL,
                                                    0,
                                                    0,
                                                    0,
                                                    &singleDeleteOnlyOps,
                                                    &singleDeleteOnlyResult,
                                                    &error))
    {
        std::cerr << "single delete-only request failed: " << error << "\n";
        return 2;
    }
    ok = expect_equal_bool(singleInsertOnlyResult.usedCuda,
                           false,
                           "single insert-only usedCuda skipped") && ok;
    ok = expect_equal_bool(singleDeleteOnlyResult.usedCuda,
                           false,
                           "single delete-only usedCuda skipped") && ok;
    ok = expect_ops_equal(singleInsertOnlyOps,
                          expectedInsertOnlyOps,
                          "single insert-only ops") && ok;
    ok = expect_ops_equal(singleDeleteOnlyOps,
                          expectedDeleteOnlyOps,
                          "single delete-only ops") && ok;

    std::vector<unsigned char> singleOps0;
    std::vector<unsigned char> singleOps1;
    SimTracebackCudaResult singleResult0;
    SimTracebackCudaResult singleResult1;
    error.clear();
    if (!sim_traceback_cuda_traceback_global_affine(query0.c_str(),
                                                    target0.c_str(),
                                                    static_cast<int>(query0.size()) - 1,
                                                    static_cast<int>(target0.size()) - 1,
                                                    10,
                                                    -10,
                                                    10,
                                                    10,
                                                    1,
                                                    NULL,
                                                    0,
                                                    0,
                                                    0,
                                                    &singleOps0,
                                                    &singleResult0,
                                                    &error))
    {
        std::cerr << "single request 0 failed: " << error << "\n";
        return 2;
    }
    error.clear();
    if (!sim_traceback_cuda_traceback_global_affine(query1.c_str(),
                                                    target1.c_str(),
                                                    static_cast<int>(query1.size()) - 1,
                                                    static_cast<int>(target1.size()) - 1,
                                                    10,
                                                    -10,
                                                    10,
                                                    10,
                                                    1,
                                                    NULL,
                                                    0,
                                                    0,
                                                    0,
                                                    &singleOps1,
                                                    &singleResult1,
                                                    &error))
    {
        std::cerr << "single request 1 failed: " << error << "\n";
        return 2;
    }

    std::vector<SimTracebackCudaBatchRequest> requests;
    requests.push_back(make_request(query0, target0));
    requests.push_back(make_request(query1, target1));

    std::vector<SimTracebackCudaBatchItemResult> batchResults;
    SimTracebackCudaBatchResult batchResult;
    error.clear();
    if (!sim_traceback_cuda_traceback_global_affine_batch(requests,
                                                          &batchResults,
                                                          &batchResult,
                                                          &error))
    {
        std::cerr << "valid batch failed: " << error << "\n";
        return 1;
    }

    ok = expect_equal_size(batchResults.size(), 2, "valid batch size") && ok;
    ok = expect_equal_uint64(batchResult.requestCount, 2, "valid batch requestCount") && ok;
    ok = expect_equal_uint64(batchResult.successCount, 2, "valid batch successCount") && ok;
    ok = expect_equal_uint64(batchResult.cudaCount, 2, "valid batch cudaCount") && ok;
    ok = expect_equal_bool(batchResult.usedCuda, true, "valid batch usedCuda") && ok;
    ok = expect_equal_uint64(batchResult.singleCudaRequestBatchSkips,
                             0,
                             "valid multi-request batch does not skip batch path") && ok;
    ok = expect_equal_uint64(batchResult.bulkOpsD2HCopies,
                             1,
                             "valid multi-request batch uses one bulk ops D2H") && ok;
    ok = expect_equal_uint64(batchResult.perRequestOpsD2HCopies,
                             0,
                             "valid multi-request batch skips per-request ops D2H") && ok;
    if (batchResults.size() == 2)
    {
        ok = expect_equal_bool(batchResults[0].success, true, "batch result 0 success") && ok;
        ok = expect_equal_bool(batchResults[1].success, true, "batch result 1 success") && ok;
        ok = expect_equal_bool(batchResults[0].tracebackResult.usedCuda, true, "batch result 0 usedCuda") && ok;
        ok = expect_equal_bool(batchResults[1].tracebackResult.usedCuda, true, "batch result 1 usedCuda") && ok;
        ok = expect_equal_bool(batchResults[0].tracebackResult.hadTie,
                               singleResult0.hadTie,
                               "batch result 0 hadTie") && ok;
        ok = expect_equal_bool(batchResults[1].tracebackResult.hadTie,
                               singleResult1.hadTie,
                               "batch result 1 hadTie") && ok;
        ok = expect_ops_equal(batchResults[0].opsReversed, singleOps0, "batch result 0 ops") && ok;
        ok = expect_ops_equal(batchResults[1].opsReversed, singleOps1, "batch result 1 ops") && ok;
    }

    requests.push_back(make_request(query0, target0));
    requests[1].queryLength = -1;
    batchResults.clear();
    batchResult = SimTracebackCudaBatchResult();
    error.clear();
    if (!sim_traceback_cuda_traceback_global_affine_batch(requests,
                                                          &batchResults,
                                                          &batchResult,
                                                          &error))
    {
        std::cerr << "mixed batch should succeed, got error: " << error << "\n";
        return 1;
    }
    ok = expect_equal_size(batchResults.size(), 3, "mixed batch size") && ok;
    ok = expect_equal_uint64(batchResult.requestCount, 3, "mixed batch requestCount") && ok;
    ok = expect_equal_uint64(batchResult.successCount, 2, "mixed batch successCount") && ok;
    ok = expect_equal_uint64(batchResult.cudaCount, 2, "mixed batch cudaCount") && ok;
    if (batchResults.size() == 3)
    {
        ok = expect_equal_bool(batchResults[0].success, true, "mixed batch result 0 success") && ok;
        ok = expect_equal_bool(batchResults[1].success, false, "mixed batch result 1 failure") && ok;
        ok = expect_equal_bool(batchResults[2].success, true, "mixed batch result 2 success") && ok;
        ok = expect_equal_bool(batchResults[1].tracebackResult.usedCuda,
                               false,
                               "mixed batch result 1 usedCuda") && ok;
        ok = expect_true(!batchResults[1].error.empty(), "mixed batch result 1 error") && ok;
        ok = expect_ops_equal(batchResults[0].opsReversed, singleOps0, "mixed batch result 0 ops") && ok;
        ok = expect_ops_equal(batchResults[2].opsReversed, singleOps0, "mixed batch result 2 ops") && ok;
    }

    std::vector<SimTracebackCudaBatchRequest> singlePendingRequests;
    singlePendingRequests.push_back(make_request(emptyQuery, insertOnlyTarget));
    singlePendingRequests.push_back(make_request(query0, target0));
    batchResults.clear();
    batchResult = SimTracebackCudaBatchResult();
    error.clear();
    if (!sim_traceback_cuda_traceback_global_affine_batch(singlePendingRequests,
                                                          &batchResults,
                                                          &batchResult,
                                                          &error))
    {
        std::cerr << "single-pending batch should succeed, got error: " << error << "\n";
        return 1;
    }
    ok = expect_equal_size(batchResults.size(), 2, "single-pending batch size") && ok;
    ok = expect_equal_uint64(batchResult.requestCount, 2, "single-pending batch requestCount") && ok;
    ok = expect_equal_uint64(batchResult.successCount, 2, "single-pending batch successCount") && ok;
    ok = expect_equal_uint64(batchResult.cudaCount, 1, "single-pending batch cudaCount") && ok;
    ok = expect_equal_uint64(batchResult.singleCudaRequestBatchSkips,
                             1,
                             "single-pending batch skips batch allocation path") && ok;
    ok = expect_equal_uint64(batchResult.bulkOpsD2HCopies,
                             0,
                             "single-pending batch does not bulk copy ops") && ok;
    if (batchResults.size() == 2)
    {
        ok = expect_equal_bool(batchResults[0].success, true, "single-pending gap result success") && ok;
        ok = expect_equal_bool(batchResults[1].success, true, "single-pending cuda result success") && ok;
        ok = expect_equal_bool(batchResults[0].tracebackResult.usedCuda,
                               false,
                               "single-pending gap result usedCuda") && ok;
        ok = expect_equal_bool(batchResults[1].tracebackResult.usedCuda,
                               true,
                               "single-pending cuda result usedCuda") && ok;
        ok = expect_ops_equal(batchResults[0].opsReversed,
                              expectedInsertOnlyOps,
                              "single-pending gap result ops") && ok;
        ok = expect_ops_equal(batchResults[1].opsReversed,
                              singleOps0,
                              "single-pending cuda result ops") && ok;
    }

    return ok ? 0 : 1;
}
