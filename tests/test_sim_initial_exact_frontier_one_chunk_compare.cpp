#include <cstring>
#include <iostream>

#include "../sim.h"

static SimScanCudaCandidateState make_state(int score)
{
    SimScanCudaCandidateState state;
    std::memset(&state, 0, sizeof(state));
    state.score = score;
    state.startI = 1;
    state.startJ = 2;
    state.endI = 3;
    state.endJ = 4;
    return state;
}

static SimInitialExactFrontierOneChunkSnapshot make_snapshot()
{
    SimInitialExactFrontierOneChunkSnapshot snapshot;
    snapshot.orderedCandidates.push_back(make_state(8));
    snapshot.runningMin = 8;
    snapshot.minCandidateScore = 8;
    snapshot.firstMaxTieAvailable = true;
    snapshot.safeStoreDigestAvailable = true;
    snapshot.safeStoreDigest = 11;
    snapshot.safeStoreEpochAvailable = true;
    snapshot.safeStoreEpoch = 3;
    refreshSimInitialExactFrontierOneChunkSnapshotDigests(snapshot);
    return snapshot;
}

int main()
{
    const SimInitialExactFrontierOneChunkSnapshot cpu = make_snapshot();
    SimInitialExactFrontierOneChunkSnapshot shadow = cpu;
    if (!compareSimInitialExactFrontierOneChunkSnapshots(cpu, shadow).matches())
    {
        std::cerr << "equal snapshots must match\n";
        return 1;
    }

    shadow.orderedCandidates[0].score = 9;
    shadow.minCandidateScore = 9;
    shadow.firstMaxTieAvailable = false;
    shadow.safeStoreDigest = 12;
    shadow.safeStoreEpoch = 4;
    refreshSimInitialExactFrontierOneChunkSnapshotDigests(shadow);
    const uint32_t expected =
        SimInitialExactFrontierOneChunkCompareResult::CANDIDATE_DIGEST |
        SimInitialExactFrontierOneChunkCompareResult::CANDIDATE_VALUE |
        SimInitialExactFrontierOneChunkCompareResult::MIN_CANDIDATE |
        SimInitialExactFrontierOneChunkCompareResult::FIRST_MAX_TIE |
        SimInitialExactFrontierOneChunkCompareResult::SAFE_STORE_DIGEST |
        SimInitialExactFrontierOneChunkCompareResult::SAFE_STORE_EPOCH;
    const SimInitialExactFrontierOneChunkCompareResult result =
        compareSimInitialExactFrontierOneChunkSnapshots(cpu, shadow);
    if (result.mismatchMask != expected)
    {
        std::cerr << "unexpected mismatch mask " << result.mismatchMask << "\n";
        return 1;
    }
    std::cout << "ok\n";
    return 0;
}
