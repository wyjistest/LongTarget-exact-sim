#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

#include "../cuda/calc_score_cuda.h"

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

static bool expect_equal_size(size_t actual, size_t expected, const char *label)
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

static bool expect_equal_scores(const std::vector<int> &actual,
                                const std::vector<int> &expected,
                                const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": score vectors differ\n";
    std::cerr << "  expected:";
    for (size_t i = 0; i < expected.size(); ++i)
    {
        std::cerr << " " << expected[i];
    }
    std::cerr << "\n  actual:";
    for (size_t i = 0; i < actual.size(); ++i)
    {
        std::cerr << " " << actual[i];
    }
    std::cerr << "\n";
    return false;
}

static void build_profile(const std::vector<uint8_t> &queryCodes,
                          int segLen,
                          std::vector<int16_t> *profile)
{
    const int segWidth = 32;
    profile->assign(static_cast<size_t>(7) * static_cast<size_t>(segLen) * static_cast<size_t>(segWidth), 0);
    for (int targetCode = 0; targetCode < 7; ++targetCode)
    {
        for (int lane = 0; lane < segWidth; ++lane)
        {
            for (int segIndex = 0; segIndex < segLen; ++segIndex)
            {
                const int queryIndex = lane * segLen + segIndex;
                int16_t score = 0;
                if (queryIndex < static_cast<int>(queryCodes.size()))
                {
                    score = (queryCodes[static_cast<size_t>(queryIndex)] == static_cast<uint8_t>(targetCode))
                                ? static_cast<int16_t>(5)
                                : static_cast<int16_t>(-4);
                }
                (*profile)[(static_cast<size_t>(targetCode) * static_cast<size_t>(segLen) +
                            static_cast<size_t>(segIndex)) *
                               static_cast<size_t>(segWidth) +
                           static_cast<size_t>(lane)] = score;
            }
        }
    }
}

} // namespace

int main()
{
    if (!calc_score_cuda_is_built())
    {
        std::cerr << "CUDA calc_score support is not built\n";
        return 2;
    }

    std::string error;
    if (!calc_score_cuda_init(0, &error))
    {
        std::cerr << "calc_score_cuda_init failed: " << error << "\n";
        return 2;
    }

    const int queryLength = 8;
    const int segLen = 1;
    std::vector<int16_t> profileFwd;
    std::vector<int16_t> profileRev;
    build_profile(std::vector<uint8_t>{1, 2, 3, 4, 1, 2, 3, 4}, segLen, &profileFwd);
    build_profile(std::vector<uint8_t>{4, 3, 2, 1, 4, 3, 2, 1}, segLen, &profileRev);

    CalcScoreCudaQueryHandle handle;
    if (!calc_score_cuda_prepare_query(&handle,
                                       profileFwd.data(),
                                       profileRev.data(),
                                       segLen,
                                       queryLength,
                                       &error))
    {
        std::cerr << "calc_score_cuda_prepare_query failed: " << error << "\n";
        return 1;
    }

    const int taskCount = 2;
    const int targetLength = 5;
    const int pairCount = 3;
    const int permutationCount = pairCount * 2;
    const std::vector<uint8_t> encodedTargets{
        1, 2, 3, 4, 1,
        4, 3, 2, 1, 4,
    };
    const std::vector<uint16_t> permutations{
        0, 1, 2, 3, 4,
        4, 3, 2, 1, 0,
        1, 0, 3, 2, 4,
        2, 3, 4, 0, 1,
        0, 2, 4, 1, 3,
        3, 1, 4, 2, 0,
    };

    unsetenv("LONGTARGET_ENABLE_CALC_SCORE_CUDA_PIPELINE_V2");
    unsetenv("LONGTARGET_CALC_SCORE_CUDA_PIPELINE_V2_SHADOW");
    std::vector<int> baselineScores;
    CalcScoreCudaBatchResult baselineResult;
    if (!calc_score_cuda_compute_pair_max_scores(handle,
                                                 encodedTargets.data(),
                                                 taskCount,
                                                 targetLength,
                                                 permutations.data(),
                                                 permutationCount,
                                                 pairCount,
                                                 &baselineScores,
                                                 &baselineResult,
                                                 &error,
                                                 true))
    {
        calc_score_cuda_release_query(&handle);
        std::cerr << "baseline calc_score_cuda_compute_pair_max_scores failed: " << error << "\n";
        return 1;
    }

    setenv("LONGTARGET_ENABLE_CALC_SCORE_CUDA_PIPELINE_V2", "1", 1);
    unsetenv("LONGTARGET_CALC_SCORE_CUDA_PIPELINE_V2_SHADOW");
    std::vector<int> v2Scores;
    CalcScoreCudaBatchResult v2Result;
    error.clear();
    if (!calc_score_cuda_compute_pair_max_scores(handle,
                                                 encodedTargets.data(),
                                                 taskCount,
                                                 targetLength,
                                                 permutations.data(),
                                                 permutationCount,
                                                 pairCount,
                                                 &v2Scores,
                                                 &v2Result,
                                                 &error,
                                                 true))
    {
        calc_score_cuda_release_query(&handle);
        std::cerr << "v2 calc_score_cuda_compute_pair_max_scores failed: " << error << "\n";
        return 1;
    }

    calc_score_cuda_release_query(&handle);
    unsetenv("LONGTARGET_ENABLE_CALC_SCORE_CUDA_PIPELINE_V2");
    unsetenv("LONGTARGET_CALC_SCORE_CUDA_PIPELINE_V2_SHADOW");

    const size_t scoreCount = static_cast<size_t>(taskCount) * static_cast<size_t>(pairCount);
    bool ok = true;
    ok = expect_equal_size(baselineScores.size(), scoreCount, "baseline score count") && ok;
    ok = expect_equal_size(v2Scores.size(), scoreCount, "v2 score count") && ok;
    ok = expect_equal_scores(v2Scores, baselineScores, "v2 scores match v1") && ok;
    ok = expect_true(v2Result.usedCuda, "v2 usedCuda") && ok;
    ok = expect_true(v2Result.pipelineV2Enabled, "v2 enabled") && ok;
    ok = expect_true(v2Result.pipelineV2Used, "v2 used") && ok;
    ok = expect_false(v2Result.pipelineV2Fallback, "v2 fallback") && ok;
    ok = expect_equal_u64(v2Result.pipelineV2ShadowComparisons, 0, "v2 non-shadow comparisons") && ok;
    ok = expect_equal_u64(v2Result.scoreBytesD2H,
                          static_cast<uint64_t>(scoreCount * sizeof(int)),
                          "v2 device-reduced score bytes D2H") && ok;

    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
