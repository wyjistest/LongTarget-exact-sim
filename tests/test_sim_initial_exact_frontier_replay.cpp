#include <cstdlib>
#include <iostream>

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

} // namespace

int main()
{
    bool ok = true;

    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY");
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_REDUCE");
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_PROPOSAL_LOOP");
    ok = expect_false(simCudaInitialExactFrontierReplayEnabledRuntime(),
                      "exact frontier replay default disabled") && ok;

    setenv("LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_LOCATE", "1", 1);
    unsetenv("LONGTARGET_SIM_CUDA_LOCATE_FAST_SHADOW");
    ok = expect_true(simCudaInitialExactFrontierReplayEnabledRuntime(),
                     "exact frontier replay opt-in enabled") && ok;
    ok = expect_true(simCudaInitialReduceRequestEnabledRuntime(),
                     "exact frontier replay routes through initial reduce") && ok;
    ok = expect_true(simCudaInitialReducePersistOnDeviceRuntime(),
                     "exact frontier replay keeps safe-store device-resident when locate is enabled") && ok;
    ok = expect_false(simCudaInitialProposalRequestEnabledRuntime(),
                      "exact frontier replay does not opt into proposal path") && ok;

    uint64_t created = 0;
    uint64_t available = 0;
    uint64_t hostEvicted = 0;
    uint64_t skipped = 0;
    uint64_t fallback = 0;
    uint64_t rejectedFastShadow = 0;
    uint64_t rejectedProposal = 0;
    uint64_t rejectedMissingGpu = 0;
    uint64_t rejectedStaleBefore = 0;
    uint64_t rejectedStaleAfter = 0;
    getSimInitialSafeStoreHandoffCompositionStats(created,
                                                  available,
                                                  hostEvicted,
                                                  skipped,
                                                  fallback,
                                                  rejectedFastShadow,
                                                  rejectedProposal,
                                                  rejectedMissingGpu,
                                                  rejectedStaleBefore);

    SimKernelContext context(16, 16);
    context.initialSafeStoreHandoffActive = true;
    context.gpuSafeCandidateStateStore.valid = true;
    context.gpuSafeCandidateStateStore.frontierValid = false;
    context.gpuSafeCandidateStateStore.telemetryEpoch = 17;
    context.gpuFrontierCacheInSync = true;
    ok = expect_true(simInvalidateInitialSafeStoreHandoffIfStaleForLocate(context),
                     "stale initial handoff is rejected before locate") && ok;
    ok = expect_false(context.gpuSafeCandidateStateStore.valid,
                      "stale initial handoff releases gpu store") && ok;
    ok = expect_false(context.gpuFrontierCacheInSync,
                      "stale initial handoff clears frontier cache sync") && ok;
    ok = expect_false(context.initialSafeStoreHandoffActive,
                      "stale initial handoff clears active marker") && ok;
    getSimInitialSafeStoreHandoffCompositionStats(created,
                                                  available,
                                                  hostEvicted,
                                                  skipped,
                                                  fallback,
                                                  rejectedFastShadow,
                                                  rejectedProposal,
                                                  rejectedMissingGpu,
                                                  rejectedStaleAfter);
    ok = expect_equal_uint64(rejectedStaleAfter, rejectedStaleBefore + 1,
                             "stale initial handoff telemetry") && ok;

    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY");
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_LOCATE");

    if (!ok)
    {
        return 1;
    }
    std::cout << "ok\n";
    return 0;
}
