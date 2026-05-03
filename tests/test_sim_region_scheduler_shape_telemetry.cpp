#include <cstdlib>
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

static bool expect_equal_u64(uint64_t actual, uint64_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static SimPathWorkset make_workset(long rowStart, long rowEnd, long colStart, long colEnd)
{
    std::vector<SimUpdateBand> bands(1);
    bands[0].rowStart = rowStart;
    bands[0].rowEnd = rowEnd;
    bands[0].colStart = colStart;
    bands[0].colEnd = colEnd;
    return makeSimPathWorksetFromBands(bands);
}

static SimKernelContext make_context(long runningMin,
                                     int safeStoreScore,
                                     long scoreMatrixDelta)
{
    SimKernelContext context(20, 20);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);
    context.runningMin = runningMin;
    context.scoreMatrix['A']['A'] += scoreMatrixDelta;

    resetSimCandidateStateStore(context.safeCandidateStateStore, true);
    SimScanCudaCandidateState state;
    state.score = safeStoreScore;
    state.startI = 1;
    state.startJ = 1;
    state.endI = 2;
    state.endJ = 3;
    state.top = 1;
    state.bot = 2;
    state.left = 1;
    state.right = 3;
    context.safeCandidateStateStore.states.push_back(state);
    rebuildSimCandidateStateStoreIndex(context.safeCandidateStateStore);
    return context;
}

static SimRegionSchedulerShapeTelemetryStats current_stats()
{
    SimRegionSchedulerShapeTelemetryStats stats;
    getSimRegionSchedulerShapeTelemetryStats(stats);
    return stats;
}

} // namespace

int main()
{
    setenv("LONGTARGET_SIM_CUDA_REGION_SCHEDULER_SHAPE_TELEMETRY", "1", 1);

    bool ok = true;
    ok = expect_true(simRegionSchedulerShapeTelemetryRuntime(),
                     "scheduler shape telemetry runtime flag") && ok;

    const SimPathWorkset workset = make_workset(2, 3, 4, 6);
    const std::vector<uint64_t> affected = {packSimCoord(1, 1), packSimCoord(2, 2)};
    const std::vector<uint64_t> differentAffected = {packSimCoord(3, 3)};

    SimKernelContext firstContext = make_context(0, 12, 0);
    recordSimRegionSchedulerShapeTelemetry(workset, affected, firstContext);
    SimRegionSchedulerShapeTelemetryStats stats = current_stats();
    ok = expect_equal_u64(stats.calls, 1, "single safe-window call count") && ok;
    ok = expect_equal_u64(stats.bands, 1, "single safe-window band count") && ok;
    ok = expect_equal_u64(stats.singleBandCalls, 1, "single band calls") && ok;
    ok = expect_equal_u64(stats.affectedStarts, 2, "affected start count") && ok;
    ok = expect_equal_u64(stats.cells, 6, "cell count") && ok;
    ok = expect_equal_u64(stats.maxBandRows, 2, "max band rows") && ok;
    ok = expect_equal_u64(stats.maxBandCols, 3, "max band columns") && ok;
    ok = expect_equal_u64(stats.mergeableCalls, 0, "single call is not mergeable") && ok;
    ok = expect_equal_u64(stats.estimatedLaunchReduction, 0, "single call launch reduction") && ok;

    SimKernelContext compatibleContext = make_context(0, 12, 0);
    recordSimRegionSchedulerShapeTelemetry(workset, affected, compatibleContext);
    stats = current_stats();
    ok = expect_equal_u64(stats.calls, 2, "compatible safe-window total calls") && ok;
    ok = expect_equal_u64(stats.mergeableCalls, 2, "compatible calls become mergeable") && ok;
    ok = expect_equal_u64(stats.mergeableCells, 12, "compatible cells become mergeable") && ok;
    ok = expect_equal_u64(stats.estimatedLaunchReduction, 1, "compatible calls launch reduction") && ok;

    SimKernelContext runningMinContext = make_context(5, 12, 0);
    recordSimRegionSchedulerShapeTelemetry(workset, affected, runningMinContext);
    stats = current_stats();
    ok = expect_equal_u64(stats.rejectedRunningMin, 1, "runningMin change rejects merge") && ok;
    ok = expect_equal_u64(stats.estimatedLaunchReduction, 1, "runningMin reject keeps launch reduction") && ok;

    SimKernelContext filterContext = make_context(5, 12, 0);
    recordSimRegionSchedulerShapeTelemetry(workset, differentAffected, filterContext);
    stats = current_stats();
    ok = expect_equal_u64(stats.rejectedFilter, 1, "filter change rejects merge") && ok;

    SimKernelContext safeStoreContext = make_context(5, 13, 0);
    recordSimRegionSchedulerShapeTelemetry(workset, differentAffected, safeStoreContext);
    stats = current_stats();
    ok = expect_equal_u64(stats.rejectedSafeStoreEpoch, 1, "safe-store epoch change rejects merge") && ok;

    SimKernelContext scoreMatrixContext = make_context(5, 13, 1);
    recordSimRegionSchedulerShapeTelemetry(workset, differentAffected, scoreMatrixContext);
    stats = current_stats();
    ok = expect_equal_u64(stats.rejectedScoreMatrix, 1, "score matrix change rejects merge") && ok;

    if (!ok)
    {
        return 1;
    }
    std::cout << "ok\n";
    return 0;
}
