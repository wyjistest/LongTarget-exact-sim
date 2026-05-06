#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <vector>

#include "../sim.h"

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

static bool expect_equal_long(long actual, long expected, const char *label)
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

static std::vector<SimCandidate> raw_candidates(const SimKernelContext &context)
{
    std::vector<SimCandidate> candidates;
    candidates.reserve(static_cast<size_t>(context.candidateCount));
    for (long index = 0; index < context.candidateCount; ++index)
    {
        candidates.push_back(context.candidates[static_cast<size_t>(index)]);
    }
    return candidates;
}

static bool expect_raw_candidates_equal(const SimKernelContext &actual,
                                        const SimKernelContext &expected,
                                        const char *label)
{
    if (actual.candidateCount != expected.candidateCount)
    {
        std::cerr << label << ": candidateCount mismatch expected "
                  << expected.candidateCount << ", got " << actual.candidateCount << "\n";
        return false;
    }

    const std::vector<SimCandidate> lhs = raw_candidates(actual);
    const std::vector<SimCandidate> rhs = raw_candidates(expected);
    for (size_t index = 0; index < lhs.size(); ++index)
    {
        if (std::memcmp(&lhs[index], &rhs[index], sizeof(SimCandidate)) != 0)
        {
            std::cerr << label << ": raw candidate mismatch at slot " << index
                      << " expected(score=" << rhs[index].SCORE
                      << ", start=" << rhs[index].STARI << "," << rhs[index].STARJ
                      << ", end=" << rhs[index].ENDI << "," << rhs[index].ENDJ
                      << ", box=" << rhs[index].TOP << "," << rhs[index].BOT
                      << "," << rhs[index].LEFT << "," << rhs[index].RIGHT
                      << ") got(score=" << lhs[index].SCORE
                      << ", start=" << lhs[index].STARI << "," << lhs[index].STARJ
                      << ", end=" << lhs[index].ENDI << "," << lhs[index].ENDJ
                      << ", box=" << lhs[index].TOP << "," << lhs[index].BOT
                      << "," << lhs[index].LEFT << "," << lhs[index].RIGHT << ")\n";
            return false;
        }
    }
    return true;
}

static void init_context(SimKernelContext &context)
{
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);
}

static bool run_fast_case(const char *label,
                          const std::vector<SimScanCudaInitialRunSummary> &summaries)
{
    SimKernelContext baseline(8192, 8192);
    SimKernelContext fast(8192, 8192);
    init_context(baseline);
    init_context(fast);

    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size()),
                                    baseline);

    SimInitialCpuFrontierFastApplyStats stats;
    const bool applied =
        applySimCudaInitialRunSummariesCpuFrontierFastApply(summaries,
                                                            static_cast<uint64_t>(summaries.size()),
                                                            fast,
                                                            &stats);

    bool ok = true;
    ok = expect_true(applied, label) && ok;
    ok = expect_raw_candidates_equal(fast, baseline, label) && ok;
    ok = expect_equal_long(fast.runningMin, baseline.runningMin, "runningMin") && ok;
    ok = expect_equal_uint64(stats.summariesReplayed,
                             static_cast<uint64_t>(summaries.size()),
                             "fast stats summaries") &&
         ok;
    ok = expect_equal_uint64(stats.candidatesOut,
                             static_cast<uint64_t>(baseline.candidateCount),
                             "fast stats candidates") &&
         ok;

    for (long candidateIndex = 0; candidateIndex < fast.candidateCount; ++candidateIndex)
    {
        const SimCandidate &candidate = fast.candidates[static_cast<size_t>(candidateIndex)];
        const long found = findSimCandidateIndex(fast.candidateStartIndex,
                                                 candidate.STARI,
                                                 candidate.STARJ);
        ok = expect_equal_long(found, candidateIndex, "fast materialized start index") && ok;
    }
    return ok;
}

static std::vector<SimScanCudaInitialRunSummary> make_k_boundary_summaries()
{
    std::vector<SimScanCudaInitialRunSummary> summaries;
    for (int offset = 0; offset < K; ++offset)
    {
        summaries.push_back(SimScanCudaInitialRunSummary{
            100 + offset,
            packSimCoord(10, static_cast<uint32_t>(offset + 1)),
            1,
            static_cast<uint32_t>(100 + offset),
            static_cast<uint32_t>(100 + offset),
            static_cast<uint32_t>(100 + offset)});
    }
    summaries.push_back(SimScanCudaInitialRunSummary{1, packSimCoord(20, 1), 2, 200, 200, 200});
    summaries.push_back(SimScanCudaInitialRunSummary{500, packSimCoord(10, 1), 3, 300, 300, 300});
    summaries.push_back(SimScanCudaInitialRunSummary{499, packSimCoord(30, 1), 4, 400, 400, 400});
    return summaries;
}

static std::vector<SimScanCudaInitialRunSummary> make_tombstone_rebuild_summaries()
{
    std::vector<SimScanCudaInitialRunSummary> summaries;
    for (int offset = 0; offset < K; ++offset)
    {
        summaries.push_back(SimScanCudaInitialRunSummary{
            1000 + offset,
            packSimCoord(100, static_cast<uint32_t>(offset + 1)),
            1,
            static_cast<uint32_t>(500 + offset),
            static_cast<uint32_t>(500 + offset),
            static_cast<uint32_t>(500 + offset)});
    }
    for (int offset = 0; offset < K + 17; ++offset)
    {
        summaries.push_back(SimScanCudaInitialRunSummary{
            10 + offset,
            packSimCoord(200, static_cast<uint32_t>(offset + 1)),
            2,
            static_cast<uint32_t>(700 + offset),
            static_cast<uint32_t>(700 + offset),
            static_cast<uint32_t>(700 + offset)});
    }
    summaries.push_back(SimScanCudaInitialRunSummary{2000, packSimCoord(100, 1), 3, 900, 901, 900});
    return summaries;
}

static std::vector<SimScanCudaInitialRunSummary> make_random_summaries()
{
    std::vector<SimScanCudaInitialRunSummary> summaries;
    uint32_t state = 0x12345678u;
    for (int index = 0; index < 4096; ++index)
    {
        state = state * 1664525u + 1013904223u;
        const uint32_t startI = 1u + (state % 97u);
        state = state * 1664525u + 1013904223u;
        const uint32_t startJ = 1u + (state % 101u);
        state = state * 1664525u + 1013904223u;
        const int score = static_cast<int>(1u + (state % 700u));
        state = state * 1664525u + 1013904223u;
        const uint32_t endI = 1u + (state % 113u);
        state = state * 1664525u + 1013904223u;
        const uint32_t minEndJ = 1u + (state % 3000u);
        state = state * 1664525u + 1013904223u;
        const uint32_t width = state % 11u;
        state = state * 1664525u + 1013904223u;
        const uint32_t scoreEndJ = minEndJ + (state % (width + 1u));
        summaries.push_back(SimScanCudaInitialRunSummary{
            score,
            packSimCoord(startI, startJ),
            endI,
            minEndJ,
            minEndJ + width,
            scoreEndJ});
    }
    return summaries;
}

static bool test_top_level_enable_and_shadow()
{
    const std::vector<SimScanCudaInitialRunSummary> summaries = make_random_summaries();

    SimInitialCpuFrontierFastApplyTelemetry before;
    getSimInitialCpuFrontierFastApplyStats(before);

    setenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_CPU_FRONTIER_FAST_APPLY", "1", 1);
    SimKernelContext baseline(8192, 8192);
    SimKernelContext fast(8192, 8192);
    init_context(baseline);
    init_context(fast);
    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size()),
                                    baseline);
    applySimCudaInitialRunSummariesToContext(summaries,
                                             static_cast<uint64_t>(summaries.size()),
                                             fast,
                                             false);
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_CPU_FRONTIER_FAST_APPLY");

    bool ok = true;
    ok = expect_raw_candidates_equal(fast, baseline, "top-level fast enable") && ok;
    ok = expect_equal_long(fast.runningMin, baseline.runningMin, "top-level fast runningMin") && ok;

    SimInitialCpuFrontierFastApplyTelemetry afterFast;
    getSimInitialCpuFrontierFastApplyStats(afterFast);
    ok = expect_true(afterFast.enabledCount > before.enabledCount, "fast telemetry enabled") && ok;
    ok = expect_true(afterFast.attempts > before.attempts, "fast telemetry attempts") && ok;
    ok = expect_true(afterFast.successes > before.successes, "fast telemetry successes") && ok;
    ok = expect_true(afterFast.summariesReplayed > before.summariesReplayed, "fast telemetry summaries") && ok;
    ok = expect_true(afterFast.candidatesOut > before.candidatesOut, "fast telemetry candidates") && ok;

    setenv("LONGTARGET_SIM_CUDA_INITIAL_CPU_FRONTIER_FAST_APPLY_SHADOW", "1", 1);
    SimKernelContext shadowBaseline(8192, 8192);
    SimKernelContext shadowContext(8192, 8192);
    init_context(shadowBaseline);
    init_context(shadowContext);
    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size()),
                                    shadowBaseline);
    applySimCudaInitialRunSummariesToContext(summaries,
                                             static_cast<uint64_t>(summaries.size()),
                                             shadowContext,
                                             false);
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_CPU_FRONTIER_FAST_APPLY_SHADOW");

    SimInitialCpuFrontierFastApplyTelemetry afterShadow;
    getSimInitialCpuFrontierFastApplyStats(afterShadow);
    ok = expect_raw_candidates_equal(shadowContext, shadowBaseline, "top-level fast shadow") && ok;
    ok = expect_equal_long(shadowContext.runningMin, shadowBaseline.runningMin, "shadow runningMin") && ok;
    ok = expect_equal_uint64(afterShadow.shadowMismatches,
                             afterFast.shadowMismatches,
                             "shadow mismatch remains zero") &&
         ok;
    ok = expect_true(afterShadow.oracleApplyNanosecondsShadow >= afterFast.oracleApplyNanosecondsShadow,
                     "shadow oracle telemetry present") &&
         ok;

    return ok;
}

static bool test_rejected_paths()
{
    const std::vector<SimScanCudaInitialRunSummary> summaries{
        SimScanCudaInitialRunSummary{10, packSimCoord(1, 1), 1, 10, 10, 10},
        SimScanCudaInitialRunSummary{20, packSimCoord(2, 1), 1, 20, 20, 20}};

    SimInitialCpuFrontierFastApplyTelemetry before;
    getSimInitialCpuFrontierFastApplyStats(before);

    setenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_CPU_FRONTIER_FAST_APPLY", "1", 1);

    SimKernelContext statsBaseline(64, 64);
    SimKernelContext statsContext(64, 64);
    init_context(statsBaseline);
    init_context(statsContext);
    statsContext.statsEnabled = true;
    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size()),
                                    statsBaseline);
    applySimCudaInitialRunSummariesToContext(summaries,
                                             static_cast<uint64_t>(summaries.size()),
                                             statsContext,
                                             false);

    SimKernelContext nonemptyBaseline(64, 64);
    SimKernelContext nonemptyContext(64, 64);
    init_context(nonemptyBaseline);
    init_context(nonemptyContext);
    const std::vector<SimScanCudaInitialRunSummary> seed{
        SimScanCudaInitialRunSummary{100, packSimCoord(5, 5), 1, 50, 50, 50}};
    mergeSimCudaInitialRunSummaries(seed, static_cast<uint64_t>(seed.size()), nonemptyBaseline);
    mergeSimCudaInitialRunSummaries(seed, static_cast<uint64_t>(seed.size()), nonemptyContext);
    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size()),
                                    nonemptyBaseline);
    applySimCudaInitialRunSummariesToContext(summaries,
                                             static_cast<uint64_t>(summaries.size()),
                                             nonemptyContext,
                                             false);

    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_CPU_FRONTIER_FAST_APPLY");

    SimInitialCpuFrontierFastApplyTelemetry after;
    getSimInitialCpuFrontierFastApplyStats(after);

    bool ok = true;
    ok = expect_raw_candidates_equal(statsContext, statsBaseline, "stats-enabled fallback") && ok;
    ok = expect_raw_candidates_equal(nonemptyContext, nonemptyBaseline, "nonempty fallback") && ok;
    ok = expect_true(after.rejectedByStats > before.rejectedByStats, "stats rejection telemetry") && ok;
    ok = expect_true(after.rejectedByNonemptyContext > before.rejectedByNonemptyContext,
                     "nonempty rejection telemetry") &&
         ok;
    ok = expect_true(after.fallbacks >= before.fallbacks + 2, "fallback telemetry") && ok;
    return ok;
}

} // namespace

int main()
{
    bool ok = true;

    SimInitialCpuFrontierFastApplyTelemetry initialTelemetry;
    getSimInitialCpuFrontierFastApplyStats(initialTelemetry);
    ok = expect_equal_uint64(initialTelemetry.enabledCount, 0, "default enabled count") && ok;
    ok = expect_equal_uint64(initialTelemetry.attempts, 0, "default attempts") && ok;
    ok = expect_equal_uint64(initialTelemetry.successes, 0, "default successes") && ok;
    ok = expect_equal_uint64(initialTelemetry.fallbacks, 0, "default fallbacks") && ok;
    ok = expect_equal_uint64(initialTelemetry.shadowMismatches, 0, "default shadow mismatches") && ok;

    ok = run_fast_case("empty summaries", std::vector<SimScanCudaInitialRunSummary>()) && ok;
    ok = run_fast_case("repeated starts",
                       std::vector<SimScanCudaInitialRunSummary>{
                           SimScanCudaInitialRunSummary{10, packSimCoord(1, 1), 5, 10, 10, 10},
                           SimScanCudaInitialRunSummary{12, packSimCoord(1, 1), 6, 8, 12, 11},
                           SimScanCudaInitialRunSummary{11, packSimCoord(1, 1), 4, 6, 14, 14},
                           SimScanCudaInitialRunSummary{13, packSimCoord(1, 2), 6, 20, 21, 20}}) &&
         ok;
    ok = run_fast_case("score ties preserve first max endpoint",
                       std::vector<SimScanCudaInitialRunSummary>{
                           SimScanCudaInitialRunSummary{20, packSimCoord(2, 2), 3, 30, 30, 30},
                           SimScanCudaInitialRunSummary{20, packSimCoord(2, 2), 4, 25, 35, 35},
                           SimScanCudaInitialRunSummary{19, packSimCoord(2, 2), 5, 24, 36, 36}}) &&
         ok;
    ok = run_fast_case("K-boundary eviction", make_k_boundary_summaries()) && ok;
    ok = run_fast_case("tombstone rebuild", make_tombstone_rebuild_summaries()) && ok;
    ok = run_fast_case("random summaries", make_random_summaries()) && ok;
    ok = test_top_level_enable_and_shadow() && ok;
    ok = test_rejected_paths() && ok;

    if (!ok)
    {
        return 1;
    }
    std::cout << "ok\n";
    return 0;
}
