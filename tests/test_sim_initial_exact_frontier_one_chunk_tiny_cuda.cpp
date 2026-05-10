#include <cstring>
#include <iostream>
#include <string>
#include <vector>

#include "../sim.h"

static SimScanCudaCandidateState make_state(int score,
                                            uint32_t startI,
                                            uint32_t startJ,
                                            uint32_t endI,
                                            uint32_t endJ,
                                            uint32_t top,
                                            uint32_t bot,
                                            uint32_t left,
                                            uint32_t right)
{
    SimScanCudaCandidateState state;
    std::memset(&state, 0, sizeof(state));
    state.score = score;
    state.startI = static_cast<int>(startI);
    state.startJ = static_cast<int>(startJ);
    state.endI = static_cast<int>(endI);
    state.endJ = static_cast<int>(endJ);
    state.top = static_cast<int>(top);
    state.bot = static_cast<int>(bot);
    state.left = static_cast<int>(left);
    state.right = static_cast<int>(right);
    return state;
}

static SimInitialExactFrontierOneChunkSnapshot make_snapshot(
    const std::vector<SimScanCudaCandidateState> &states,
    int runningMin)
{
    SimInitialExactFrontierOneChunkSnapshot snapshot;
    snapshot.orderedCandidates = states;
    snapshot.runningMin = runningMin;
    snapshot.minCandidateScore = runningMin;
    snapshot.firstMaxTieAvailable = true;
    snapshot.safeStoreDigestAvailable = false;
    snapshot.safeStoreEpochAvailable = false;
    refreshSimInitialExactFrontierOneChunkSnapshotDigests(snapshot);
    return snapshot;
}

int main()
{
    const SimInitialExactFrontierOneChunkSnapshot cpu =
        make_snapshot({make_state(9, 1, 1, 3, 5, 2, 5, 2, 7),
                       make_state(7, 2, 1, 4, 6, 4, 4, 6, 6)},
                      7);

    std::vector<SimScanCudaCandidateState> gpuStates;
    int gpuRunningMin = 0;
    std::string error;
    if (!sim_scan_cuda_one_chunk_exact_frontier_tiny_shadow_for_test(
            &gpuStates, &gpuRunningMin, &error))
    {
        std::cerr << "tiny cuda shadow failed: " << error << "\n";
        return 1;
    }
    const SimInitialExactFrontierOneChunkSnapshot gpu =
        make_snapshot(gpuStates, gpuRunningMin);

    const SimInitialExactFrontierOneChunkCompareResult result =
        compareSimInitialExactFrontierOneChunkSnapshots(cpu, gpu);
    if (!result.matches())
    {
        std::cerr << "tiny cuda shadow mismatch mask " << result.mismatchMask << "\n";
        return 1;
    }
    std::cout << "ok\n";
    return 0;
}
