#include <cstdlib>
#include <cstring>
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

static bool expect_equal_size(size_t actual, size_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_state_equal(const SimScanCudaCandidateState &actual,
                               const SimScanCudaCandidateState &expected,
                               const char *label)
{
    if (std::memcmp(&actual, &expected, sizeof(SimScanCudaCandidateState)) == 0)
    {
        return true;
    }
    std::cerr << label << ": state mismatch\n";
    return false;
}

static SimScanCudaCandidateState make_state(int score,
                                            int startI,
                                            int startJ,
                                            int endI,
                                            int endJ,
                                            int top,
                                            int bot,
                                            int left,
                                            int right)
{
    SimScanCudaCandidateState state;
    state.score = score;
    state.startI = startI;
    state.startJ = startJ;
    state.endI = endI;
    state.endJ = endJ;
    state.top = top;
    state.bot = bot;
    state.left = left;
    state.right = right;
    return state;
}

static void set_required_residency_env()
{
    setenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_REDUCE", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_PROPOSAL_LOOP", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_DEVICE_K_LOOP", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_LOCATE", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_LOCATE_MODE", "safe_workset", 1);
}

} // namespace

int main()
{
    set_required_residency_env();

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

    SimKernelContext context(32, 32);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);

    std::vector<SimScanCudaCandidateState> frontierStates;
    frontierStates.push_back(make_state(120, 8, 8, 14, 14, 8, 14, 8, 14));
    frontierStates.push_back(make_state(110, 2, 2, 6, 6, 2, 6, 2, 6));
    applySimCudaReducedCandidates(frontierStates,
                                  110,
                                  context);

    std::vector<SimScanCudaCandidateState> warehouseStates = frontierStates;
    warehouseStates.push_back(make_state(150, 20, 20, 25, 25, 20, 25, 20, 25));
    resetSimCandidateStateStore(context.safeCandidateStateStore, true);
    context.safeCandidateStateStore.states = warehouseStates;
    rebuildSimCandidateStateStoreIndex(context.safeCandidateStateStore);
    if (!uploadSimCudaPersistentSafeCandidateStateStore(warehouseStates,
                                                        context.gpuSafeCandidateStateStore,
                                                        &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore failed: " << error << "\n";
        return 2;
    }

    std::vector<SimScanCudaCandidateState> proposalStates;
    bool usedGpuSafeStore = false;
    if (!collectSimCudaProposalStatesForLoop(1,
                                             context,
                                             proposalStates,
                                             &usedGpuSafeStore,
                                             &error))
    {
        releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
        std::cerr << "collectSimCudaProposalStatesForLoop failed: " << error << "\n";
        return 2;
    }

    releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);

    ok = expect_equal_size(proposalStates.size(),
                           1,
                           "residency proposal count") && ok;
    if (!proposalStates.empty())
    {
        ok = expect_state_equal(proposalStates[0],
                                warehouseStates[2],
                                "residency proposal prefers gpu safe-store top candidate") && ok;
    }
    ok = expect_equal_bool(usedGpuSafeStore,
                           true,
                           "residency proposal uses gpu safe store") && ok;
    ok = expect_true(simCudaMainlineResidencyEnabledRuntime(),
                     "residency runtime enabled") && ok;

    return ok ? 0 : 1;
}
