#include <cstdlib>
#include <iostream>
#include <string>
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

static SimTracebackPathSummary make_summary(long rowStart,
                                            long rowEnd,
                                            long minCol,
                                            long maxCol)
{
    SimTracebackPathSummary summary;
    summary.valid = true;
    summary.rowStart = rowStart;
    summary.rowEnd = rowEnd;
    summary.colStart = minCol;
    summary.colEnd = maxCol;
    summary.stepCount = rowEnd >= rowStart ? rowEnd - rowStart + 1 : 0;
    const size_t rowCount = static_cast<size_t>(summary.stepCount);
    summary.rowMinCols.assign(rowCount, minCol);
    summary.rowMaxCols.assign(rowCount, maxCol);
    return summary;
}

static bool build_plan(const std::vector<SimScanCudaCandidateState> &candidateStates,
                       const SimTracebackPathSummary &summary,
                       SimScanCudaSafeWindowPlannerMode plannerMode,
                       int maxWindowCount,
                       SimSafeWindowExecutePlan &plan)
{
    std::string error;
    SimCudaPersistentSafeStoreHandle handle;
    if (!uploadSimCudaPersistentSafeCandidateStateStore(candidateStates, handle, &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore failed: " << error << "\n";
        return false;
    }
    const bool ok = buildSimSafeWindowExecutePlanFromCudaCandidateStateStoreWithPlanner(
        20,
        60,
        summary,
        handle,
        plannerMode,
        maxWindowCount,
        plan,
        &error);
    releaseSimCudaPersistentSafeCandidateStateStore(handle);
    if (!ok)
    {
        std::cerr << "buildSimSafeWindowExecutePlanFromCudaCandidateStateStoreWithPlanner failed: "
                  << error << "\n";
        return false;
    }
    return true;
}

} // namespace

int main()
{
    setenv("LONGTARGET_ENABLE_SIM_CUDA", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_LOCATE", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_LOCATE_MODE", "safe_workset", 1);

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
    ok = expect_equal_int(static_cast<int>(parseSimSafeWindowPlannerMode("sparse_v2")),
                          static_cast<int>(SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2),
                          "parse sparse_v2 planner") && ok;

    const SimTracebackPathSummary sparseSummary = make_summary(5, 7, 3, 40);
    std::vector<SimScanCudaCandidateState> sparseCandidates(3);
    sparseCandidates[0] = SimScanCudaCandidateState{25, 5, 1, 7, 4, 5, 7, 1, 4};
    sparseCandidates[1] = SimScanCudaCandidateState{24, 5, 40, 7, 43, 5, 7, 40, 43};
    sparseCandidates[2] = SimScanCudaCandidateState{17, 1, 50, 3, 53, 1, 3, 50, 53};

    SimSafeWindowExecutePlan densePlan;
    SimSafeWindowExecutePlan sparsePlan;
    SimSafeWindowExecutePlan sparseV2Plan;
    ok = build_plan(sparseCandidates,
                    sparseSummary,
                    SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE,
                    32,
                    densePlan) && ok;
    ok = build_plan(sparseCandidates,
                    sparseSummary,
                    SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V1,
                    32,
                    sparsePlan) && ok;
    ok = build_plan(sparseCandidates,
                    sparseSummary,
                    SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2,
                    32,
                    sparseV2Plan) && ok;
    ok = expect_true(sparsePlan.execCellCount < densePlan.execCellCount,
                     "fixture sparse plan reduces execution cells") && ok;
    ok = expect_equal_u64(sparseV2Plan.execCellCount,
                          sparsePlan.execCellCount,
                          "sparse_v2 selects sparse plan when cells shrink") && ok;
    ok = expect_equal_int(static_cast<int>(sparseV2Plan.plannerModeUsed),
                          static_cast<int>(SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2),
                          "sparse_v2 records sparse planner use") && ok;
    ok = expect_equal_u64(sparseV2Plan.sparseV2SavedCells,
                          densePlan.execCellCount - sparsePlan.execCellCount,
                          "sparse_v2 saved cells") && ok;

    const SimTracebackPathSummary denseEquivalentSummary = make_summary(5, 7, 1, 4);
    std::vector<SimScanCudaCandidateState> denseEquivalentCandidates(1);
    denseEquivalentCandidates[0] = SimScanCudaCandidateState{25, 5, 1, 7, 4, 5, 7, 1, 4};

    SimSafeWindowExecutePlan denseEquivalentPlan;
    SimSafeWindowExecutePlan denseEquivalentV2Plan;
    ok = build_plan(denseEquivalentCandidates,
                    denseEquivalentSummary,
                    SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE,
                    32,
                    denseEquivalentPlan) && ok;
    ok = build_plan(denseEquivalentCandidates,
                    denseEquivalentSummary,
                    SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2,
                    32,
                    denseEquivalentV2Plan) && ok;
    ok = expect_equal_u64(denseEquivalentV2Plan.execCellCount,
                          denseEquivalentPlan.execCellCount,
                          "sparse_v2 preserves dense-equivalent cells") && ok;
    ok = expect_equal_int(static_cast<int>(denseEquivalentV2Plan.plannerModeUsed),
                          static_cast<int>(SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE),
                          "sparse_v2 falls back to dense on cell tie") && ok;

    SimSafeWindowExecutePlan overflowV2Plan;
    ok = build_plan(sparseCandidates,
                    sparseSummary,
                    SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2,
                    1,
                    overflowV2Plan) && ok;
    ok = expect_equal_int(static_cast<int>(overflowV2Plan.plannerModeUsed),
                          static_cast<int>(SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE),
                          "sparse_v2 falls back to dense when sparse overflows") && ok;
    ok = expect_true(!overflowV2Plan.overflowFallback,
                     "sparse_v2 dense fallback avoids overflow") && ok;

    uint64_t rawWindowCellsBefore = 0;
    uint64_t rawMaxWindowCellsBefore = 0;
    uint64_t execMaxBandCellsBefore = 0;
    uint64_t coarseningInflatedCellsBefore = 0;
    uint64_t sparseV2ConsideredBefore = 0;
    uint64_t sparseV2SelectedBefore = 0;
    uint64_t sparseV2RejectedBefore = 0;
    uint64_t sparseV2SavedCellsBefore = 0;
    const SimSafeWindowGeometryDistributionStats distributionBefore =
        getSimSafeWindowGeometryDistributionStats();
    getSimSafeWindowGeometryTelemetryStats(rawWindowCellsBefore,
                                           rawMaxWindowCellsBefore,
                                           execMaxBandCellsBefore,
                                           coarseningInflatedCellsBefore,
                                           sparseV2ConsideredBefore,
                                           sparseV2SelectedBefore,
                                           sparseV2RejectedBefore,
                                           sparseV2SavedCellsBefore);
    recordSimSafeWindowGeometryTelemetry(sparseV2Plan);

    uint64_t rawWindowCellsAfter = 0;
    uint64_t rawMaxWindowCellsAfter = 0;
    uint64_t execMaxBandCellsAfter = 0;
    uint64_t coarseningInflatedCellsAfter = 0;
    uint64_t sparseV2ConsideredAfter = 0;
    uint64_t sparseV2SelectedAfter = 0;
    uint64_t sparseV2RejectedAfter = 0;
    uint64_t sparseV2SavedCellsAfter = 0;
    const SimSafeWindowGeometryDistributionStats distributionAfter =
        getSimSafeWindowGeometryDistributionStats();
    getSimSafeWindowGeometryTelemetryStats(rawWindowCellsAfter,
                                           rawMaxWindowCellsAfter,
                                           execMaxBandCellsAfter,
                                           coarseningInflatedCellsAfter,
                                           sparseV2ConsideredAfter,
                                           sparseV2SelectedAfter,
                                           sparseV2RejectedAfter,
                                           sparseV2SavedCellsAfter);
    ok = expect_true(rawWindowCellsAfter > rawWindowCellsBefore,
                     "geometry telemetry records raw window cells") && ok;
    ok = expect_true(rawMaxWindowCellsAfter >= rawMaxWindowCellsBefore,
                     "geometry telemetry records raw max window cells") && ok;
    ok = expect_true(execMaxBandCellsAfter >= execMaxBandCellsBefore,
                     "geometry telemetry records exec max band cells") && ok;
    ok = expect_true(coarseningInflatedCellsAfter >= coarseningInflatedCellsBefore,
                     "geometry telemetry records coarsening inflation") && ok;
    ok = expect_equal_u64(sparseV2ConsideredAfter,
                          sparseV2ConsideredBefore + 1,
                          "geometry telemetry records sparse_v2 consideration") && ok;
    ok = expect_equal_u64(sparseV2SelectedAfter,
                          sparseV2SelectedBefore + 1,
                          "geometry telemetry records sparse_v2 selection") && ok;
    ok = expect_equal_u64(sparseV2RejectedAfter,
                          sparseV2RejectedBefore,
                          "geometry telemetry leaves rejected count unchanged on selection") && ok;
    ok = expect_equal_u64(sparseV2SavedCellsAfter,
                          sparseV2SavedCellsBefore + sparseV2Plan.sparseV2SavedCells,
                          "geometry telemetry records sparse_v2 saved cells") && ok;
    ok = expect_equal_u64(distributionAfter.geometryCallCount,
                          distributionBefore.geometryCallCount + 1,
                          "geometry distribution records call count") && ok;
    ok = expect_true(distributionAfter.maxInflatedCellCount >= sparseV2Plan.coarseningInflatedCellCount,
                     "geometry distribution records max inflated cells") && ok;
    ok = expect_true(distributionAfter.topInflated[0].inflatedCellCount >=
                       sparseV2Plan.coarseningInflatedCellCount,
                     "geometry distribution records top inflated call") && ok;
    ok = expect_true(distributionAfter.smallWindowCallCount +
                       distributionAfter.largeWindowCallCount >=
                       distributionBefore.smallWindowCallCount +
                       distributionBefore.largeWindowCallCount + 1,
                     "geometry distribution classifies window size") && ok;

    const SimSafeWindowLargeGeometryShadowStats largeShadowBefore =
        getSimSafeWindowLargeGeometryShadowStats();
    SimSafeWindowExecutePlan largeShadowPlan;
    largeShadowPlan.rawWindowCellCount = 2000001;
    largeShadowPlan.execCellCount = 3000000;
    largeShadowPlan.coarseningInflatedCellCount = 999999;
    recordSimSafeWindowLargeGeometryShadowEstimate(largeShadowPlan);
    const SimSafeWindowLargeGeometryShadowStats largeShadowAfter =
        getSimSafeWindowLargeGeometryShadowStats();
    ok = expect_equal_u64(largeShadowAfter.callCount,
                          largeShadowBefore.callCount + 1,
                          "large geometry shadow records selected call") && ok;
    ok = expect_equal_u64(largeShadowAfter.largeCallCount,
                          largeShadowBefore.largeCallCount + 1,
                          "large geometry shadow records large call") && ok;
    ok = expect_equal_u64(largeShadowAfter.currentExecCellCount,
                          largeShadowBefore.currentExecCellCount + 3000000,
                          "large geometry shadow records current exec cells") && ok;
    ok = expect_equal_u64(largeShadowAfter.shadowExecCellCount,
                          largeShadowBefore.shadowExecCellCount + 2000001,
                          "large geometry shadow records estimated shadow cells") && ok;
    ok = expect_equal_u64(largeShadowAfter.estSavedCellCount,
                          largeShadowBefore.estSavedCellCount + 999999,
                          "large geometry shadow records estimated saved cells") && ok;
    ok = expect_equal_u64(largeShadowAfter.estimatorOnly,
                          1,
                          "large geometry shadow is estimator-only") && ok;

    if (!ok)
    {
        return 1;
    }
    std::cout << "ok\n";
    return 0;
}
