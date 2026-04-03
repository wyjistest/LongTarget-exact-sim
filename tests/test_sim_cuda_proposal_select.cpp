#include <cstdlib>
#include <cstring>
#include <iostream>
#include <vector>

#include "../cuda/sim_scan_cuda.h"

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

static bool expect_equal_size(size_t actual, size_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
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

static bool set_frontier_cache(SimCudaPersistentSafeStoreHandle &handle,
                               const std::vector<SimScanCudaCandidateState> &frontierStates,
                               int runningMin,
                               std::string *errorOut)
{
    if (handle.frontierStatesDevice != 0)
    {
        SimCudaPersistentSafeStoreHandle frontierReleaseHandle = handle;
        frontierReleaseHandle.statesDevice = frontierReleaseHandle.frontierStatesDevice;
        frontierReleaseHandle.stateCount = frontierReleaseHandle.frontierCount;
        frontierReleaseHandle.frontierStatesDevice = 0;
        frontierReleaseHandle.frontierCapacity = 0;
        frontierReleaseHandle.frontierCount = 0;
        sim_scan_cuda_release_persistent_safe_candidate_state_store(&frontierReleaseHandle);
        handle.frontierStatesDevice = 0;
        handle.frontierCapacity = 0;
    }

    handle.frontierValid = true;
    handle.frontierRunningMin = runningMin;
    handle.frontierCount = frontierStates.size();
    if (frontierStates.empty())
    {
        if (errorOut != NULL)
        {
            errorOut->clear();
        }
        return true;
    }

    SimCudaPersistentSafeStoreHandle frontierUploadHandle;
    if (!sim_scan_cuda_upload_persistent_safe_candidate_state_store(frontierStates.data(),
                                                                    frontierStates.size(),
                                                                    &frontierUploadHandle,
                                                                    errorOut))
    {
        return false;
    }
    handle.frontierStatesDevice = frontierUploadHandle.statesDevice;
    handle.frontierCapacity = frontierStates.size();
    frontierUploadHandle.statesDevice = 0;
    frontierUploadHandle.stateCount = 0;
    sim_scan_cuda_release_persistent_safe_candidate_state_store(&frontierUploadHandle);
    if (errorOut != NULL)
    {
        errorOut->clear();
    }
    return true;
}

} // namespace

int main()
{
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

    std::vector<SimScanCudaCandidateState> candidateStates;
    candidateStates.push_back(make_state(120, 2, 100, 20, 108, 10, 20, 100, 110));
    candidateStates.push_back(make_state(118, 3, 103, 18, 112, 12, 18, 105, 115));
    candidateStates.push_back(make_state(117, 6, 120, 25, 104, 21, 25, 100, 105));
    candidateStates.push_back(make_state(116, 1, 90, 9, 95, 5, 9, 90, 99));
    candidateStates.push_back(make_state(115, 7, 121, 24, 106, 22, 24, 103, 107));
    candidateStates.push_back(make_state(114, 9, 130, 35, 104, 30, 35, 100, 105));
    candidateStates.push_back(make_state(114, 10, 140, 42, 115, 36, 42, 111, 115));
    candidateStates.push_back(make_state(113, 2, 92, 8, 98, 6, 8, 92, 98));

    std::vector<SimScanCudaCandidateState> proposals;
    if (!sim_scan_cuda_select_top_disjoint_candidate_states(candidateStates,
                                                            5,
                                                            &proposals,
                                                            &error))
    {
        std::cerr << "proposal helper failed: " << error << "\n";
        return 2;
    }

    bool ok = true;
    ok = expect_equal_size(proposals.size(), 5, "proposal count") && ok;
    if (proposals.size() == 5)
    {
        ok = expect_state_equal(proposals[0], candidateStates[0], "proposal[0]") && ok;
        ok = expect_state_equal(proposals[1], candidateStates[2], "proposal[1]") && ok;
        ok = expect_state_equal(proposals[2], candidateStates[3], "proposal[2]") && ok;
        ok = expect_state_equal(proposals[3], candidateStates[5], "proposal[3]") && ok;
        ok = expect_state_equal(proposals[4], candidateStates[6], "proposal[4]") && ok;
    }

    for (size_t i = 0; i < proposals.size(); ++i)
    {
        for (size_t j = i + 1; j < proposals.size(); ++j)
        {
            const bool disjoint = !simScanCudaCandidateStateBoxesOverlap(proposals[i], proposals[j]);
            ok = expect_true(disjoint, "selected proposals are pairwise disjoint") && ok;
        }
    }

    std::vector<SimScanCudaCandidateState> tiedCandidateStates;
    tiedCandidateStates.push_back(make_state(200, 40, 400, 60, 430, 40, 60, 400, 430));
    tiedCandidateStates.push_back(make_state(200, 20, 380, 58, 420, 20, 58, 380, 420));
    tiedCandidateStates.push_back(make_state(150, 80, 500, 100, 540, 80, 100, 500, 540));

    std::vector<SimScanCudaCandidateState> tiedProposals;
    if (!sim_scan_cuda_select_top_disjoint_candidate_states(tiedCandidateStates,
                                                            2,
                                                            &tiedProposals,
                                                            &error))
    {
        std::cerr << "proposal helper tied-score case failed: " << error << "\n";
        return 2;
    }

    ok = expect_equal_size(tiedProposals.size(), 2, "tied proposal count") && ok;
    if (tiedProposals.size() == 2)
    {
        ok = expect_state_equal(tiedProposals[0], tiedCandidateStates[1], "tied proposal[0] stable tie-break") && ok;
        ok = expect_state_equal(tiedProposals[1], tiedCandidateStates[2], "tied proposal[1] stable tie-break") && ok;
    }

    SimCudaPersistentSafeStoreHandle persistentStoreHandle;
    if (!sim_scan_cuda_upload_persistent_safe_candidate_state_store(candidateStates.data(),
                                                                    candidateStates.size(),
                                                                    &persistentStoreHandle,
                                                                    &error))
    {
        std::cerr << "persistent store upload failed: " << error << "\n";
        return 2;
    }

    std::vector<SimScanCudaCandidateState> frontierSubsetStates;
    frontierSubsetStates.push_back(candidateStates[5]);
    frontierSubsetStates.push_back(candidateStates[6]);
    frontierSubsetStates.push_back(candidateStates[7]);
    if (!set_frontier_cache(persistentStoreHandle, frontierSubsetStates, 0, &error))
    {
        sim_scan_cuda_release_persistent_safe_candidate_state_store(&persistentStoreHandle);
        std::cerr << "set_frontier_cache(frontierSubsetStates) failed: " << error << "\n";
        return 2;
    }

    std::vector<SimScanCudaCandidateState> frontierSubsetProposals;
    bool usedFrontierSubsetCache = false;
    if (!sim_scan_cuda_select_top_disjoint_candidate_states_from_persistent_store(
            persistentStoreHandle,
            3,
            &frontierSubsetProposals,
            &error,
            &usedFrontierSubsetCache))
    {
        sim_scan_cuda_release_persistent_safe_candidate_state_store(&persistentStoreHandle);
        std::cerr << "persistent store selector with frontier subset failed: " << error << "\n";
        return 2;
    }

    ok = expect_equal_bool(usedFrontierSubsetCache,
                           true,
                           "persistent selector uses frontier cache when available") && ok;
    ok = expect_equal_size(frontierSubsetProposals.size(),
                           3,
                           "persistent selector uses frontier subset count") && ok;
    if (frontierSubsetProposals.size() == 3)
    {
        ok = expect_state_equal(frontierSubsetProposals[0],
                                candidateStates[5],
                                "persistent selector frontier subset proposal[0]") && ok;
        ok = expect_state_equal(frontierSubsetProposals[1],
                                candidateStates[6],
                                "persistent selector frontier subset proposal[1]") && ok;
        ok = expect_state_equal(frontierSubsetProposals[2],
                                candidateStates[7],
                                "persistent selector frontier subset proposal[2]") && ok;
    }

    if (!set_frontier_cache(persistentStoreHandle,
                            std::vector<SimScanCudaCandidateState>(),
                            0,
                            &error))
    {
        sim_scan_cuda_release_persistent_safe_candidate_state_store(&persistentStoreHandle);
        std::cerr << "set_frontier_cache(empty) failed: " << error << "\n";
        return 2;
    }

    std::vector<SimScanCudaCandidateState> emptyFrontierProposals;
    bool usedEmptyFrontierCache = false;
    if (!sim_scan_cuda_select_top_disjoint_candidate_states_from_persistent_store(
            persistentStoreHandle,
            3,
            &emptyFrontierProposals,
            &error,
            &usedEmptyFrontierCache))
    {
        sim_scan_cuda_release_persistent_safe_candidate_state_store(&persistentStoreHandle);
        std::cerr << "persistent store selector with empty frontier failed: " << error << "\n";
        return 2;
    }

    ok = expect_equal_bool(usedEmptyFrontierCache,
                           true,
                           "persistent selector treats empty frontier cache as authoritative") && ok;
    ok = expect_equal_size(emptyFrontierProposals.size(),
                           0,
                           "persistent selector honors empty frontier cache") && ok;

    std::vector<uint64_t> erasedStartCoords(1, simScanCudaCandidateStateStartCoord(frontierSubsetStates[0]));
    if (!set_frontier_cache(persistentStoreHandle, frontierSubsetStates, 0, &error))
    {
        sim_scan_cuda_release_persistent_safe_candidate_state_store(&persistentStoreHandle);
        std::cerr << "set_frontier_cache(before erase) failed: " << error << "\n";
        return 2;
    }
    if (!sim_scan_cuda_erase_persistent_safe_candidate_state_store_start_coords(
            erasedStartCoords.data(),
            erasedStartCoords.size(),
            &persistentStoreHandle,
            &error))
    {
        sim_scan_cuda_release_persistent_safe_candidate_state_store(&persistentStoreHandle);
        std::cerr << "persistent store erase failed: " << error << "\n";
        return 2;
    }

    std::vector<SimScanCudaCandidateState> proposalsAfterErase;
    bool usedFrontierAfterErase = false;
    if (!sim_scan_cuda_select_top_disjoint_candidate_states_from_persistent_store(
            persistentStoreHandle,
            3,
            &proposalsAfterErase,
            &error,
            &usedFrontierAfterErase))
    {
        sim_scan_cuda_release_persistent_safe_candidate_state_store(&persistentStoreHandle);
        std::cerr << "persistent store selector after erase failed: " << error << "\n";
        return 2;
    }

    ok = expect_equal_bool(usedFrontierAfterErase,
                           true,
                           "persistent erase preserves frontier cache") && ok;
    ok = expect_equal_size(proposalsAfterErase.size(),
                           2,
                           "persistent erase keeps filtered frontier proposal count") && ok;
    if (proposalsAfterErase.size() == 2)
    {
        ok = expect_state_equal(proposalsAfterErase[0],
                                frontierSubsetStates[1],
                                "persistent erase frontier proposal[0]") && ok;
        ok = expect_state_equal(proposalsAfterErase[1],
                                frontierSubsetStates[2],
                                "persistent erase frontier proposal[1]") && ok;
    }

    std::vector<SimScanCudaCandidateState> rebuiltFrontierStates;
    rebuiltFrontierStates.push_back(candidateStates[2]);
    rebuiltFrontierStates.push_back(candidateStates[5]);
    if (!sim_scan_cuda_update_persistent_safe_candidate_state_store(std::vector<SimScanCudaCandidateState>(),
                                                                    rebuiltFrontierStates,
                                                                    0,
                                                                    &persistentStoreHandle,
                                                                    &error))
    {
        sim_scan_cuda_release_persistent_safe_candidate_state_store(&persistentStoreHandle);
        std::cerr << "persistent store update failed: " << error << "\n";
        return 2;
    }

    std::vector<SimScanCudaCandidateState> proposalsAfterUpdate;
    bool usedFrontierAfterUpdate = false;
    if (!sim_scan_cuda_select_top_disjoint_candidate_states_from_persistent_store(
            persistentStoreHandle,
            2,
            &proposalsAfterUpdate,
            &error,
            &usedFrontierAfterUpdate))
    {
        sim_scan_cuda_release_persistent_safe_candidate_state_store(&persistentStoreHandle);
        std::cerr << "persistent store selector after update failed: " << error << "\n";
        return 2;
    }

    ok = expect_equal_bool(usedFrontierAfterUpdate,
                           true,
                           "persistent update rebuilds frontier cache") && ok;
    ok = expect_equal_size(proposalsAfterUpdate.size(),
                           2,
                           "persistent update frontier proposal count") && ok;
    if (proposalsAfterUpdate.size() == 2)
    {
        ok = expect_state_equal(proposalsAfterUpdate[0],
                                rebuiltFrontierStates[0],
                                "persistent update frontier proposal[0]") && ok;
        ok = expect_state_equal(proposalsAfterUpdate[1],
                                rebuiltFrontierStates[1],
                                "persistent update frontier proposal[1]") && ok;
    }

    sim_scan_cuda_release_persistent_safe_candidate_state_store(&persistentStoreHandle);

    return ok ? 0 : 1;
}
