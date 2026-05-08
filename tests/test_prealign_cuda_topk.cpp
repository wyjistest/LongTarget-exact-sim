#include <iostream>
#include <string>
#include <vector>

#include "../cuda/prealign_shared.h"

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

static bool expect_equal_int(int actual, int expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
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

static bool expect_equal_size(size_t actual, size_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

} // namespace

int main()
{
    if (!prealign_cuda_is_built())
    {
        std::cerr << "CUDA prealign support is not built\n";
        return 2;
    }

    std::string error;
    if (!prealign_cuda_init(0, &error))
    {
        std::cerr << "prealign_cuda_init failed: " << error << "\n";
        return 2;
    }

    std::vector<int16_t> profile;
    int segLen = 0;
    const std::string query = "ACGTACGT";
    prealign_shared_build_query_profile(query, 5, 4, profile, segLen);

    PreAlignCudaQueryHandle handle;
    if (!prealign_cuda_prepare_query(&handle,
                                     profile.data(),
                                     5,
                                     segLen,
                                     static_cast<int>(query.size()),
                                     &error))
    {
        std::cerr << "prealign_cuda_prepare_query failed: " << error << "\n";
        return 1;
    }

    std::vector<uint8_t> encodedTarget;
    prealign_shared_encode_sequence("ACGT", encodedTarget);

    std::vector<PreAlignCudaPeak> unclampedPeaks;
    PreAlignCudaBatchResult unclampedBatchResult;
    const int unclampedTopK = 3;
    error.clear();
    if (!prealign_cuda_find_topk_column_maxima(handle,
                                               encodedTarget.data(),
                                               1,
                                               4,
                                               unclampedTopK,
                                               &unclampedPeaks,
                                               &unclampedBatchResult,
                                               &error))
    {
        prealign_cuda_release_query(&handle);
        std::cerr << "unclamped prealign_cuda_find_topk_column_maxima failed: " << error << "\n";
        return 1;
    }

    std::vector<PreAlignCudaPeak> peaks;
    PreAlignCudaBatchResult batchResult;
    const int targetLength = 4;
    const int requestedTopK = 8;
    error.clear();
    const bool okCall = prealign_cuda_find_topk_column_maxima(handle,
                                                              encodedTarget.data(),
                                                              1,
                                                              targetLength,
                                                              requestedTopK,
                                                              &peaks,
                                                              &batchResult,
                                                              &error);
    if (!okCall)
    {
        prealign_cuda_release_query(&handle);
        std::cerr << "prealign_cuda_find_topk_column_maxima failed: " << error << "\n";
        return 1;
    }

    bool ok = true;
    ok = expect_true(unclampedBatchResult.usedCuda, "unclamped topK usedCuda") && ok;
    ok = expect_equal_int(unclampedBatchResult.requestedTopK, unclampedTopK, "unclamped requestedTopK") && ok;
    ok = expect_equal_int(unclampedBatchResult.effectiveTopK, unclampedTopK, "unclamped effectiveTopK") && ok;
    ok = expect_equal_u64(unclampedBatchResult.topKClampedCount, 0, "unclamped topK clamp count") && ok;
    ok = expect_equal_size(unclampedPeaks.size(), static_cast<size_t>(unclampedTopK), "unclamped output shape") && ok;

    ok = expect_true(batchResult.usedCuda, "topK clamp usedCuda") && ok;
    ok = expect_equal_int(batchResult.requestedTopK, requestedTopK, "topK clamp requestedTopK") && ok;
    ok = expect_equal_int(batchResult.effectiveTopK, targetLength, "topK clamp effectiveTopK") && ok;
    ok = expect_equal_u64(batchResult.topKClampedCount, 1, "topK clamp count") && ok;
    ok = expect_equal_size(peaks.size(), static_cast<size_t>(requestedTopK), "topK clamp output shape") && ok;

    std::vector<uint8_t> encodedTwoTargets;
    prealign_shared_encode_sequence("ACGTTGCA", encodedTwoTargets);
    std::vector<PreAlignCudaPeak> twoTaskPeaks;
    PreAlignCudaBatchResult twoTaskBatchResult;
    const int twoTaskTopK = 7;
    error.clear();
    if (!prealign_cuda_find_topk_column_maxima(handle,
                                               encodedTwoTargets.data(),
                                               2,
                                               targetLength,
                                               twoTaskTopK,
                                               &twoTaskPeaks,
                                               &twoTaskBatchResult,
                                               &error))
    {
        prealign_cuda_release_query(&handle);
        std::cerr << "two-task prealign_cuda_find_topk_column_maxima failed: " << error << "\n";
        return 1;
    }
    prealign_cuda_release_query(&handle);
    ok = expect_equal_int(twoTaskBatchResult.requestedTopK, twoTaskTopK, "two-task requestedTopK") && ok;
    ok = expect_equal_int(twoTaskBatchResult.effectiveTopK, targetLength, "two-task effectiveTopK") && ok;
    ok = expect_equal_u64(twoTaskBatchResult.topKClampedCount, 1, "two-task topK clamp count") && ok;
    ok = expect_equal_size(twoTaskPeaks.size(), static_cast<size_t>(2 * twoTaskTopK), "two-task output shape") && ok;
    for (int taskIndex = 0; taskIndex < 2; ++taskIndex)
    {
        const size_t rowBase = static_cast<size_t>(taskIndex) * static_cast<size_t>(twoTaskTopK);
        for (int k = targetLength; k < twoTaskTopK && rowBase + static_cast<size_t>(k) < twoTaskPeaks.size(); ++k)
        {
            const std::string labelPrefix = "two-task padded peak task " + std::to_string(taskIndex) +
                                            " k " + std::to_string(k);
            ok = expect_equal_int(twoTaskPeaks[rowBase + static_cast<size_t>(k)].score,
                                  -1,
                                  (labelPrefix + " score").c_str()) && ok;
            ok = expect_equal_int(twoTaskPeaks[rowBase + static_cast<size_t>(k)].position,
                                  -1,
                                  (labelPrefix + " position").c_str()) && ok;
        }
    }

    for (int k = 0; k < targetLength && k < static_cast<int>(peaks.size()); ++k)
    {
        const std::string labelPrefix = "valid peak " + std::to_string(k);
        ok = expect_true(peaks[static_cast<size_t>(k)].score >= 0, (labelPrefix + " score").c_str()) && ok;
        ok = expect_true(peaks[static_cast<size_t>(k)].position >= 0, (labelPrefix + " position lower").c_str()) && ok;
        ok = expect_true(peaks[static_cast<size_t>(k)].position < targetLength, (labelPrefix + " position upper").c_str()) && ok;
    }

    for (int k = targetLength; k < requestedTopK && k < static_cast<int>(peaks.size()); ++k)
    {
        const std::string labelPrefix = "padded peak " + std::to_string(k);
        ok = expect_equal_int(peaks[static_cast<size_t>(k)].score, -1, (labelPrefix + " score").c_str()) && ok;
        ok = expect_equal_int(peaks[static_cast<size_t>(k)].position, -1, (labelPrefix + " position").c_str()) && ok;
    }

    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
