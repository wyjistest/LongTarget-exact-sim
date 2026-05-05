#include <algorithm>
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

static bool expect_equal_long(long actual, long expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
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

static bool expect_equal_string(const std::string &actual,
                                const std::string &expected,
                                const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected \"" << expected << "\", got \"" << actual << "\"\n";
    return false;
}

static const SimScanCudaCandidateState *find_candidate_state(const SimCandidateStateStore &store,
                                                             long startI,
                                                             long startJ)
{
    const uint64_t startCoord = packSimCoord(static_cast<uint32_t>(startI),
                                             static_cast<uint32_t>(startJ));
    for (size_t i = 0; i < store.states.size(); ++i)
    {
        if (simScanCudaCandidateStateStartCoord(store.states[i]) == startCoord)
        {
            return &store.states[i];
        }
    }
    return NULL;
}

static std::vector<SimScanCudaCandidateState> sorted_candidate_states(const std::vector<SimScanCudaCandidateState> &states)
{
    std::vector<SimScanCudaCandidateState> sorted = states;
    std::sort(sorted.begin(), sorted.end(), [](const SimScanCudaCandidateState &lhs, const SimScanCudaCandidateState &rhs) {
        const uint64_t lhsStart = simScanCudaCandidateStateStartCoord(lhs);
        const uint64_t rhsStart = simScanCudaCandidateStateStartCoord(rhs);
        if (lhsStart != rhsStart) return lhsStart < rhsStart;
        if (lhs.score != rhs.score) return lhs.score < rhs.score;
        if (lhs.endI != rhs.endI) return lhs.endI < rhs.endI;
        if (lhs.endJ != rhs.endJ) return lhs.endJ < rhs.endJ;
        if (lhs.top != rhs.top) return lhs.top < rhs.top;
        if (lhs.bot != rhs.bot) return lhs.bot < rhs.bot;
        if (lhs.left != rhs.left) return lhs.left < rhs.left;
        return lhs.right < rhs.right;
    });
    return sorted;
}

static bool expect_candidate_states_equal(const std::vector<SimScanCudaCandidateState> &actual,
                                         const std::vector<SimScanCudaCandidateState> &expected,
                                         const char *label)
{
    if (actual.size() != expected.size())
    {
        std::cerr << label << ": expected size " << expected.size() << ", got " << actual.size() << "\n";
        return false;
    }
    const std::vector<SimScanCudaCandidateState> lhs = sorted_candidate_states(actual);
    const std::vector<SimScanCudaCandidateState> rhs = sorted_candidate_states(expected);
    for (size_t i = 0; i < lhs.size(); ++i)
    {
        if (std::memcmp(&lhs[i], &rhs[i], sizeof(SimScanCudaCandidateState)) != 0)
        {
            std::cerr << label << ": mismatch at index " << i << "\n";
            return false;
        }
    }
    return true;
}

static bool expect_triplex_equal(const triplex &actual,
                                 const triplex &expected,
                                 const char *label)
{
    bool ok = true;
    std::string prefix(label);
    ok = expect_equal_int(actual.stari, expected.stari, (prefix + " stari").c_str()) && ok;
    ok = expect_equal_int(actual.endi, expected.endi, (prefix + " endi").c_str()) && ok;
    ok = expect_equal_int(actual.starj, expected.starj, (prefix + " starj").c_str()) && ok;
    ok = expect_equal_int(actual.endj, expected.endj, (prefix + " endj").c_str()) && ok;
    ok = expect_equal_int(actual.reverse, expected.reverse, (prefix + " reverse").c_str()) && ok;
    ok = expect_equal_int(actual.strand, expected.strand, (prefix + " strand").c_str()) && ok;
    ok = expect_equal_int(actual.rule, expected.rule, (prefix + " rule").c_str()) && ok;
    ok = expect_equal_int(actual.nt, expected.nt, (prefix + " nt").c_str()) && ok;
    ok = expect_equal_string(actual.stri_align, expected.stri_align, (prefix + " stri_align").c_str()) && ok;
    ok = expect_equal_string(actual.strj_align, expected.strj_align, (prefix + " strj_align").c_str()) && ok;
    return ok;
}

static bool expect_triplex_lists_equal(const std::vector<triplex> &actual,
                                       const std::vector<triplex> &expected,
                                       const char *label)
{
    bool ok = true;
    std::string prefix(label);
    ok = expect_equal_size(actual.size(), expected.size(), (prefix + " size").c_str()) && ok;
    if (actual.size() != expected.size())
    {
        return false;
    }
    for (size_t i = 0; i < actual.size(); ++i)
    {
        const std::string itemLabel = prefix + " item " + std::to_string(i);
        ok = expect_triplex_equal(actual[i], expected[i], itemLabel.c_str()) && ok;
    }
    return ok;
}

static std::vector<uint64_t> sorted_unique_start_coords(const std::vector<uint64_t> &coords)
{
    std::vector<uint64_t> sorted = coords;
    std::sort(sorted.begin(), sorted.end());
    sorted.erase(std::unique(sorted.begin(), sorted.end()), sorted.end());
    return sorted;
}

static bool expect_start_coords_equal(const std::vector<uint64_t> &actual,
                                      const std::vector<uint64_t> &expected,
                                      const char *label)
{
    const std::vector<uint64_t> lhs = sorted_unique_start_coords(actual);
    const std::vector<uint64_t> rhs = sorted_unique_start_coords(expected);
    if (lhs.size() != rhs.size())
    {
        std::cerr << label << ": expected size " << rhs.size()
                  << ", got " << lhs.size() << "\n";
        return false;
    }
    for (size_t i = 0; i < lhs.size(); ++i)
    {
        if (lhs[i] != rhs[i])
        {
            std::cerr << label << ": mismatch at index " << i
                      << ", expected " << rhs[i] << ", got " << lhs[i] << "\n";
            return false;
        }
    }
    return true;
}

static bool expect_worksets_equal(const SimPathWorkset &actual,
                                  const SimPathWorkset &expected,
                                  const char *label)
{
    bool ok = true;
    std::string prefix(label);
    ok = expect_equal_bool(actual.hasWorkset, expected.hasWorkset, (prefix + " hasWorkset").c_str()) && ok;
    ok = expect_equal_bool(actual.fallbackToRect, expected.fallbackToRect, (prefix + " fallbackToRect").c_str()) && ok;
    ok = expect_equal_u64(actual.cellCount, expected.cellCount, (prefix + " cellCount").c_str()) && ok;
    ok = expect_equal_size(actual.bands.size(), expected.bands.size(), (prefix + " bandCount").c_str()) && ok;
    if (actual.bands.size() != expected.bands.size())
    {
        return false;
    }
    for (size_t i = 0; i < actual.bands.size(); ++i)
    {
        const std::string bandPrefix = prefix + " band " + std::to_string(i);
        ok = expect_equal_long(actual.bands[i].rowStart, expected.bands[i].rowStart, (bandPrefix + " rowStart").c_str()) && ok;
        ok = expect_equal_long(actual.bands[i].rowEnd, expected.bands[i].rowEnd, (bandPrefix + " rowEnd").c_str()) && ok;
        ok = expect_equal_long(actual.bands[i].colStart, expected.bands[i].colStart, (bandPrefix + " colStart").c_str()) && ok;
        ok = expect_equal_long(actual.bands[i].colEnd, expected.bands[i].colEnd, (bandPrefix + " colEnd").c_str()) && ok;
    }
    return ok;
}

static SimPathWorkset make_workset_from_safe_windows(const std::vector<SimScanCudaSafeWindow> &windows)
{
    SimPathWorkset workset;
    if (windows.empty())
    {
        return workset;
    }
    workset.hasWorkset = true;
    workset.bands.resize(windows.size());
    for (size_t i = 0; i < windows.size(); ++i)
    {
        workset.bands[i].rowStart = windows[i].rowStart;
        workset.bands[i].rowEnd = windows[i].rowEnd;
        workset.bands[i].colStart = windows[i].colStart;
        workset.bands[i].colEnd = windows[i].colEnd;
    }
    workset.cellCount = simPathWorksetCellCountFromBands(workset.bands);
    return workset;
}

static bool expect_safe_windows_equal(const std::vector<SimScanCudaSafeWindow> &actual,
                                      const std::vector<SimScanCudaSafeWindow> &expected,
                                      const char *label)
{
    bool ok = true;
    std::string prefix(label);
    ok = expect_equal_size(actual.size(), expected.size(), (prefix + " count").c_str()) && ok;
    if (actual.size() != expected.size())
    {
        return false;
    }
    for (size_t i = 0; i < actual.size(); ++i)
    {
        const std::string windowPrefix = prefix + " window " + std::to_string(i);
        ok = expect_equal_long(actual[i].rowStart, expected[i].rowStart, (windowPrefix + " rowStart").c_str()) && ok;
        ok = expect_equal_long(actual[i].rowEnd, expected[i].rowEnd, (windowPrefix + " rowEnd").c_str()) && ok;
        ok = expect_equal_long(actual[i].colStart, expected[i].colStart, (windowPrefix + " colStart").c_str()) && ok;
        ok = expect_equal_long(actual[i].colEnd, expected[i].colEnd, (windowPrefix + " colEnd").c_str()) && ok;
    }
    return ok;
}

} // namespace

int main()
{
    setenv("LONGTARGET_ENABLE_SIM_CUDA", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_REGION", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_LOCATE", "1", 1);
    setenv("LONGTARGET_SIM_CUDA_LOCATE_MODE", "safe_workset", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_LOCATE_DEVICE_K_LOOP", "1", 1);
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_PROPOSAL_LOOP");
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_DEVICE_K_LOOP");

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

    SimTracebackPathSummary pathSummary;
    pathSummary.valid = true;
    pathSummary.rowStart = 5;
    pathSummary.rowEnd = 10;
    pathSummary.colStart = 8;
    pathSummary.colEnd = 12;
    pathSummary.stepCount = 6;
    pathSummary.rowMinCols = {8, 8, 9, 10, 11, 12};
    pathSummary.rowMaxCols = {8, 9, 10, 11, 12, 12};

    std::vector<SimScanCudaCandidateState> safeWorksetCandidates(4);
    safeWorksetCandidates[0] = SimScanCudaCandidateState{20, 5, 7, 9, 12, 5, 9, 7, 12};
    safeWorksetCandidates[1] = SimScanCudaCandidateState{18, 1, 1, 4, 6, 1, 4, 1, 6};
    safeWorksetCandidates[2] = SimScanCudaCandidateState{19, 6, 9, 10, 13, 6, 10, 9, 13};
    safeWorksetCandidates[3] = SimScanCudaCandidateState{17, 6, 13, 10, 15, 6, 10, 13, 15};

    std::vector<uint64_t> expectedAffectedStartCoords;
    const SimPathWorkset expectedWorkset =
        buildSimSafeWorksetFromCandidateStates(20,
                                               20,
                                               pathSummary,
                                               safeWorksetCandidates,
                                               &expectedAffectedStartCoords);
    const std::vector<uint64_t> expectedUniqueAffectedStartCoords =
        makeSortedUniqueSimStartCoords(expectedAffectedStartCoords);

    SimCudaPersistentSafeStoreHandle storeHandle;
    if (!uploadSimCudaPersistentSafeCandidateStateStore(safeWorksetCandidates, storeHandle, &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore failed: " << error << "\n";
        return 2;
    }

    SimPathWorkset cudaWorkset;
    std::vector<uint64_t> cudaAffectedStartCoords;
    if (!buildSimSafeWorksetFromCudaCandidateStateStore(20,
                                                        20,
                                                        pathSummary,
                                                        storeHandle,
                                                        cudaWorkset,
                                                        cudaAffectedStartCoords,
                                                        &error))
    {
        std::cerr << "buildSimSafeWorksetFromCudaCandidateStateStore failed: " << error << "\n";
        return 2;
    }
    releaseSimCudaPersistentSafeCandidateStateStore(storeHandle);

    const std::vector<uint64_t> cudaUniqueAffectedStartCoords =
        makeSortedUniqueSimStartCoords(cudaAffectedStartCoords);

    bool ok = true;
    ok = expect_worksets_equal(cudaWorkset, expectedWorkset, "gpu safe workset matches host") && ok;
    ok = expect_equal_size(cudaUniqueAffectedStartCoords.size(),
                           expectedUniqueAffectedStartCoords.size(),
                           "gpu affected start count") && ok;
    if (cudaUniqueAffectedStartCoords.size() == expectedUniqueAffectedStartCoords.size())
    {
        for (size_t i = 0; i < cudaUniqueAffectedStartCoords.size(); ++i)
        {
            const std::string label = "gpu affected start " + std::to_string(i);
            ok = expect_equal_u64(cudaUniqueAffectedStartCoords[i],
                                  expectedUniqueAffectedStartCoords[i],
                                  label.c_str()) && ok;
        }
    }
    ok = expect_true(!storeHandle.valid, "store handle released") && ok;

    if (!uploadSimCudaPersistentSafeCandidateStateStore(safeWorksetCandidates, storeHandle, &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(second) failed: " << error << "\n";
        return 2;
    }

    SimScanCudaSafeWindowResult safeWindowResult;
    if (!sim_scan_cuda_select_safe_workset_windows(storeHandle,
                                                   20,
                                                   20,
                                                   static_cast<int>(pathSummary.rowStart),
                                                   std::vector<int>(pathSummary.rowMinCols.begin(), pathSummary.rowMinCols.end()),
                                                   std::vector<int>(pathSummary.rowMaxCols.begin(), pathSummary.rowMaxCols.end()),
                                                   SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE,
                                                   32,
                                                   &safeWindowResult,
                                                   &error))
    {
        std::cerr << "sim_scan_cuda_select_safe_workset_windows failed: " << error << "\n";
        return 2;
    }
    releaseSimCudaPersistentSafeCandidateStateStore(storeHandle);

    const SimPathWorkset safeWindowWorkset =
        make_workset_from_safe_windows(safeWindowResult.windows);
    const std::vector<uint64_t> safeWindowUniqueAffectedStartCoords =
        makeSortedUniqueSimStartCoords(safeWindowResult.affectedStartCoords);

    ok = expect_equal_bool(safeWindowResult.overflowFallback,
                           false,
                           "safe window overflow fallback disabled") && ok;
    ok = expect_worksets_equal(safeWindowWorkset,
                               expectedWorkset,
                               "gpu safe windows match host workset") && ok;
    ok = expect_equal_size(safeWindowUniqueAffectedStartCoords.size(),
                           expectedUniqueAffectedStartCoords.size(),
                           "safe window affected start count") && ok;
    if (safeWindowUniqueAffectedStartCoords.size() == expectedUniqueAffectedStartCoords.size())
    {
        for (size_t i = 0; i < safeWindowUniqueAffectedStartCoords.size(); ++i)
        {
            const std::string label = "safe window affected start " + std::to_string(i);
            ok = expect_equal_u64(safeWindowUniqueAffectedStartCoords[i],
                                  expectedUniqueAffectedStartCoords[i],
                                  label.c_str()) && ok;
        }
    }
    ok = expect_true(!storeHandle.valid, "store handle released after safe window path") && ok;

    if (!uploadSimCudaPersistentSafeCandidateStateStore(safeWorksetCandidates, storeHandle, &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(execute-plan) failed: "
                  << error << "\n";
        return 2;
    }

    SimSafeWindowExecutePlan safeWindowExecutePlan;
    if (!buildSimSafeWindowExecutePlanFromCudaCandidateStateStore(20,
                                                                  20,
                                                                  pathSummary,
                                                                  storeHandle,
                                                                  safeWindowExecutePlan,
                                                                  &error))
    {
        std::cerr << "buildSimSafeWindowExecutePlanFromCudaCandidateStateStore failed: "
                  << error << "\n";
        return 2;
    }
    releaseSimCudaPersistentSafeCandidateStateStore(storeHandle);

    const SimPathWorkset expectedSafeWindowExecWorkset =
        buildSimSafeWindowExecutionWorkset(safeWindowWorkset);
    ok = expect_equal_bool(safeWindowExecutePlan.overflowFallback,
                           false,
                           "safe window execute-plan overflow fallback disabled") && ok;
    ok = expect_equal_bool(safeWindowExecutePlan.emptyPlan,
                           false,
                           "safe window execute-plan non-empty") && ok;
    ok = expect_worksets_equal(safeWindowExecutePlan.execWorkset,
                               expectedSafeWindowExecWorkset,
                               "safe window execute-plan matches expected exec workset") && ok;
    ok = expect_equal_size(safeWindowExecutePlan.uniqueAffectedStartCoords.size(),
                           expectedUniqueAffectedStartCoords.size(),
                           "safe window execute-plan affected start count") && ok;
    if (safeWindowExecutePlan.uniqueAffectedStartCoords.size() == expectedUniqueAffectedStartCoords.size())
    {
        for (size_t i = 0; i < safeWindowExecutePlan.uniqueAffectedStartCoords.size(); ++i)
        {
            const std::string label = "safe window execute-plan affected start " + std::to_string(i);
            ok = expect_equal_u64(safeWindowExecutePlan.uniqueAffectedStartCoords[i],
                                  expectedUniqueAffectedStartCoords[i],
                                  label.c_str()) && ok;
        }
    }
    ok = expect_equal_u64(safeWindowExecutePlan.execBandCount,
                          static_cast<uint64_t>(expectedSafeWindowExecWorkset.bands.size()),
                          "safe window execute-plan band count") && ok;
    ok = expect_equal_u64(safeWindowExecutePlan.execCellCount,
                          expectedSafeWindowExecWorkset.cellCount,
                          "safe window execute-plan cell count") && ok;
    ok = expect_true(!storeHandle.valid, "store handle released after execute-plan path") && ok;

    SimTracebackPathSummary emptyPlanSummary;
    emptyPlanSummary.valid = true;
    emptyPlanSummary.rowStart = 5;
    emptyPlanSummary.rowEnd = 9;
    emptyPlanSummary.colStart = 7;
    emptyPlanSummary.colEnd = 12;
    emptyPlanSummary.stepCount = 7;
    emptyPlanSummary.rowMinCols = {7, 8, 11, 11, 12};
    emptyPlanSummary.rowMaxCols = {7, 10, 11, 11, 12};

    std::vector<SimScanCudaCandidateState> emptyPlanCandidates(1);
    emptyPlanCandidates[0] = SimScanCudaCandidateState{18, 1, 1, 2, 2, 1, 2, 1, 2};
    if (!uploadSimCudaPersistentSafeCandidateStateStore(emptyPlanCandidates, storeHandle, &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(empty plan) failed: "
                  << error << "\n";
        return 2;
    }

    SimPathWorkset emptyPlanWorkset;
    std::vector<uint64_t> emptyPlanAffectedStartCoords;
    if (!buildSimSafeWorksetFromCudaCandidateStateStore(20,
                                                        20,
                                                        emptyPlanSummary,
                                                        storeHandle,
                                                        emptyPlanWorkset,
                                                        emptyPlanAffectedStartCoords,
                                                        &error))
    {
        std::cerr << "buildSimSafeWorksetFromCudaCandidateStateStore(empty plan) failed: "
                  << error << "\n";
        return 2;
    }

    SimSafeWindowExecutePlan emptyPlanExecutePlan;
    if (!buildSimSafeWindowExecutePlanFromCudaCandidateStateStore(20,
                                                                  20,
                                                                  emptyPlanSummary,
                                                                  storeHandle,
                                                                  emptyPlanExecutePlan,
                                                                  &error))
    {
        std::cerr << "buildSimSafeWindowExecutePlanFromCudaCandidateStateStore(empty plan) failed: "
                  << error << "\n";
        return 2;
    }
    releaseSimCudaPersistentSafeCandidateStateStore(storeHandle);

    SimKernelContext emptyPlanExactContext(20, 20);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, emptyPlanExactContext);
    const std::string emptyPlanQuery(20, 'A');
    const std::string emptyPlanTarget(20, 'A');
    const std::string paddedEmptyPlanQuery = " " + emptyPlanQuery;
    const std::string paddedEmptyPlanTarget = " " + emptyPlanTarget;
    const SimLocateResult emptyPlanExactLocateResult =
        locateSimUpdateRegionExact(paddedEmptyPlanQuery.c_str(),
                                   paddedEmptyPlanTarget.c_str(),
                                   5,
                                   9,
                                   7,
                                   12,
                                   emptyPlanExactContext);

    ok = expect_equal_bool(emptyPlanWorkset.hasWorkset,
                           false,
                           "empty safe-workset builder returns no workset") && ok;
    ok = expect_equal_size(emptyPlanAffectedStartCoords.size(),
                           0,
                           "empty safe-workset builder returns no affected starts") && ok;
    ok = expect_equal_bool(emptyPlanExecutePlan.emptyPlan,
                           true,
                           "empty safe-window execute-plan reports empty plan") && ok;
    ok = expect_equal_size(emptyPlanExecutePlan.uniqueAffectedStartCoords.size(),
                           0,
                           "empty safe-window execute-plan returns no affected starts") && ok;
    ok = expect_equal_bool(emptyPlanExactLocateResult.hasUpdateRegion,
                           true,
                           "empty safe-window selection can still require exact locate update") && ok;

    SimTracebackPathSummary sparsePlannerSummary;
    sparsePlannerSummary.valid = true;
    sparsePlannerSummary.rowStart = 5;
    sparsePlannerSummary.rowEnd = 7;
    sparsePlannerSummary.colStart = 4;
    sparsePlannerSummary.colEnd = 40;
    sparsePlannerSummary.stepCount = 3;
    sparsePlannerSummary.rowMinCols = {4, 4, 4};
    sparsePlannerSummary.rowMaxCols = {40, 40, 40};

    std::vector<SimScanCudaCandidateState> sparsePlannerCandidates(3);
    sparsePlannerCandidates[0] = SimScanCudaCandidateState{25, 5, 1, 7, 4, 5, 7, 1, 4};
    sparsePlannerCandidates[1] = SimScanCudaCandidateState{24, 5, 40, 7, 43, 5, 7, 40, 43};
    sparsePlannerCandidates[2] = SimScanCudaCandidateState{17, 1, 50, 3, 53, 1, 3, 50, 53};
    std::vector<uint64_t> sparseExpectedAffectedStartCoords;
    const SimPathWorkset sparseExpectedWorkset =
        buildSimSafeWorksetFromCandidateStates(20,
                                               60,
                                               sparsePlannerSummary,
                                               sparsePlannerCandidates,
                                               &sparseExpectedAffectedStartCoords);
    const std::vector<uint64_t> sparseExpectedUniqueAffectedStartCoords =
        makeSortedUniqueSimStartCoords(sparseExpectedAffectedStartCoords);
    const SimPathWorkset sparseExpectedExecWorkset =
        buildSimSafeWindowExecutionWorkset(sparseExpectedWorkset);
    std::vector<SimScanCudaSafeWindow> sparseExpectedWindows;
    sparseExpectedWindows.push_back(SimScanCudaSafeWindow(5, 7, 1, 4));
    sparseExpectedWindows.push_back(SimScanCudaSafeWindow(5, 7, 40, 43));

    ok = expect_worksets_equal(sparseExpectedWorkset,
                               make_workset_from_safe_windows(sparseExpectedWindows),
                               "host sparse safe_window workset keeps disjoint islands") && ok;
    ok = expect_equal_size(sparseExpectedExecWorkset.bands.size(),
                           2,
                           "host sparse safe_window exec keeps disjoint islands") && ok;

    if (!uploadSimCudaPersistentSafeCandidateStateStore(sparsePlannerCandidates, storeHandle, &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(sparse planner) failed: "
                  << error << "\n";
        return 2;
    }

    SimScanCudaSafeWindowResult densePlannerResult;
    if (!sim_scan_cuda_select_safe_workset_windows(storeHandle,
                                                   20,
                                                   60,
                                                   static_cast<int>(sparsePlannerSummary.rowStart),
                                                   std::vector<int>(sparsePlannerSummary.rowMinCols.begin(),
                                                                    sparsePlannerSummary.rowMinCols.end()),
                                                   std::vector<int>(sparsePlannerSummary.rowMaxCols.begin(),
                                                                    sparsePlannerSummary.rowMaxCols.end()),
                                                   SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE,
                                                   32,
                                                   &densePlannerResult,
                                                   &error))
    {
        std::cerr << "sim_scan_cuda_select_safe_workset_windows(dense planner) failed: "
                  << error << "\n";
        return 2;
    }
    ok = expect_equal_bool(densePlannerResult.overflowFallback,
                           false,
                           "dense planner overflow fallback disabled") && ok;
    ok = expect_equal_size(densePlannerResult.windows.size(),
                           1,
                           "dense planner bridges sparse islands") && ok;
    if (densePlannerResult.windows.size() == 1)
    {
        ok = expect_equal_long(densePlannerResult.windows[0].rowStart,
                               5,
                               "dense planner row start") && ok;
        ok = expect_equal_long(densePlannerResult.windows[0].rowEnd,
                               7,
                               "dense planner row end") && ok;
        ok = expect_equal_long(densePlannerResult.windows[0].colStart,
                               1,
                               "dense planner col start") && ok;
        ok = expect_equal_long(densePlannerResult.windows[0].colEnd,
                               43,
                               "dense planner col end") && ok;
    }

    SimScanCudaSafeWindowResult sparsePlannerResult;
    if (!sim_scan_cuda_select_safe_workset_windows(storeHandle,
                                                   20,
                                                   60,
                                                   static_cast<int>(sparsePlannerSummary.rowStart),
                                                   std::vector<int>(sparsePlannerSummary.rowMinCols.begin(),
                                                                    sparsePlannerSummary.rowMinCols.end()),
                                                   std::vector<int>(sparsePlannerSummary.rowMaxCols.begin(),
                                                                    sparsePlannerSummary.rowMaxCols.end()),
                                                   SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V1,
                                                   32,
                                                   &sparsePlannerResult,
                                                   &error))
    {
        std::cerr << "sim_scan_cuda_select_safe_workset_windows(sparse planner) failed: "
                  << error << "\n";
        return 2;
    }
    ok = expect_equal_bool(sparsePlannerResult.overflowFallback,
                           false,
                           "sparse planner overflow fallback disabled") && ok;
    ok = expect_safe_windows_equal(sparsePlannerResult.windows,
                                   sparseExpectedWindows,
                                   "sparse planner windows match host sparse workset") && ok;
    ok = expect_equal_size(makeSortedUniqueSimStartCoords(sparsePlannerResult.affectedStartCoords).size(),
                           sparseExpectedUniqueAffectedStartCoords.size(),
                           "sparse planner affected start count") && ok;

    SimScanCudaSafeWindowExecutePlanResult sparsePlannerExecutePlan;
    if (!sim_scan_cuda_build_safe_window_execute_plan(storeHandle,
                                                      20,
                                                      60,
                                                      static_cast<int>(sparsePlannerSummary.rowStart),
                                                      std::vector<int>(sparsePlannerSummary.rowMinCols.begin(),
                                                                       sparsePlannerSummary.rowMinCols.end()),
                                                      std::vector<int>(sparsePlannerSummary.rowMaxCols.begin(),
                                                                       sparsePlannerSummary.rowMaxCols.end()),
                                                      SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V1,
                                                      32,
                                                      &sparsePlannerExecutePlan,
                                                      &error))
    {
        std::cerr << "sim_scan_cuda_build_safe_window_execute_plan(sparse planner) failed: "
                  << error << "\n";
        return 2;
    }
    releaseSimCudaPersistentSafeCandidateStateStore(storeHandle);

    ok = expect_equal_bool(sparsePlannerExecutePlan.overflowFallback,
                           false,
                           "sparse planner execute-plan overflow fallback disabled") && ok;
    ok = expect_equal_bool(sparsePlannerExecutePlan.emptyPlan,
                           false,
                           "sparse planner execute-plan non-empty") && ok;
    ok = expect_worksets_equal(make_workset_from_safe_windows(sparsePlannerExecutePlan.execWindows),
                               sparseExpectedWorkset,
                               "sparse planner execute-plan windows match host sparse workset") && ok;
    ok = expect_equal_u64(sparsePlannerExecutePlan.execBandCount,
                          static_cast<uint64_t>(sparseExpectedExecWorkset.bands.size()),
                          "sparse planner execute-plan band count") && ok;
    ok = expect_equal_u64(sparsePlannerExecutePlan.execCellCount,
                          sparseExpectedExecWorkset.cellCount,
                          "sparse planner execute-plan cell count") && ok;
    ok = expect_true(!storeHandle.valid, "store handle released after sparse planner path") && ok;

    const char *previousInitialSafeStoreHandoff =
        getenv("LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_HANDOFF");
    const bool hadPreviousInitialSafeStoreHandoff = previousInitialSafeStoreHandoff != NULL;
    const std::string previousInitialSafeStoreHandoffValue =
        hadPreviousInitialSafeStoreHandoff ? previousInitialSafeStoreHandoff : "";
    const char *previousInitialSafeStoreHandoffAlias =
        getenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_SAFE_STORE_DEVICE_MAINTENANCE");
    const bool hadPreviousInitialSafeStoreHandoffAlias =
        previousInitialSafeStoreHandoffAlias != NULL;
    const std::string previousInitialSafeStoreHandoffAliasValue =
        hadPreviousInitialSafeStoreHandoffAlias ? previousInitialSafeStoreHandoffAlias : "";
    unsetenv("LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_HANDOFF");
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_SAFE_STORE_DEVICE_MAINTENANCE");

    std::vector<SimScanCudaInitialRunSummary> mirroredSummaries;
    mirroredSummaries.push_back(SimScanCudaInitialRunSummary{20, packSimCoord(5, 7), 9, 7, 12, 12});
    mirroredSummaries.push_back(SimScanCudaInitialRunSummary{18, packSimCoord(1, 1), 4, 1, 6, 6});
    mirroredSummaries.push_back(SimScanCudaInitialRunSummary{19, packSimCoord(6, 9), 10, 9, 13, 13});
    mirroredSummaries.push_back(SimScanCudaInitialRunSummary{17, packSimCoord(6, 13), 10, 13, 15, 15});

    SimKernelContext mirroredContext(20, 20);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, mirroredContext);
    applySimCudaInitialRunSummariesToContext(mirroredSummaries,
                                             static_cast<uint64_t>(mirroredSummaries.size()),
                                             mirroredContext,
                                             false);

    SimPathWorkset mirroredGpuWorkset;
    std::vector<uint64_t> mirroredGpuAffectedStartCoords;
    if (!buildSimSafeWorksetFromCudaCandidateStateStore(20,
                                                        20,
                                                        pathSummary,
                                                        mirroredContext.gpuSafeCandidateStateStore,
                                                        mirroredGpuWorkset,
                                                        mirroredGpuAffectedStartCoords,
                                                        &error))
    {
        std::cerr << "buildSimSafeWorksetFromCudaCandidateStateStore(mirroredContext) failed: "
                  << error << "\n";
        return 2;
    }
    const SimPathWorkset mirroredHostWorkset =
        buildSimSafeWorksetFromCandidateStates(20,
                                              20,
                                              pathSummary,
                                              mirroredContext.safeCandidateStateStore.states,
                                              NULL);
    const std::vector<uint64_t> mirroredUniqueAffectedStartCoords =
        makeSortedUniqueSimStartCoords(mirroredGpuAffectedStartCoords);
    const std::vector<uint64_t> mirroredExpectedAffectedStartCoords =
        makeSortedUniqueSimStartCoords(expectedAffectedStartCoords);

    ok = expect_true(mirroredContext.safeCandidateStateStore.valid,
                     "summary handoff host safe store valid") && ok;
    ok = expect_true(mirroredContext.gpuSafeCandidateStateStore.valid,
                     "summary handoff gpu safe store valid") && ok;
    ok = expect_worksets_equal(mirroredGpuWorkset,
                               mirroredHostWorkset,
                               "summary handoff gpu mirror workset matches host") && ok;
    ok = expect_equal_size(mirroredUniqueAffectedStartCoords.size(),
                           mirroredExpectedAffectedStartCoords.size(),
                           "summary handoff gpu affected start count") && ok;
    if (mirroredUniqueAffectedStartCoords.size() == mirroredExpectedAffectedStartCoords.size())
    {
        for (size_t i = 0; i < mirroredUniqueAffectedStartCoords.size(); ++i)
        {
            const std::string label = "summary handoff gpu affected start " + std::to_string(i);
            ok = expect_equal_u64(mirroredUniqueAffectedStartCoords[i],
                                  mirroredExpectedAffectedStartCoords[i],
                                  label.c_str()) && ok;
        }
    }

    uint64_t handoffCreatedBefore = 0;
    uint64_t handoffAvailableBefore = 0;
    uint64_t handoffHostStoreEvictedBefore = 0;
    uint64_t handoffHostMergeSkippedBefore = 0;
    uint64_t handoffHostMergeFallbacksBefore = 0;
    uint64_t handoffRejectedFastShadowBefore = 0;
    uint64_t handoffRejectedProposalLoopBefore = 0;
    uint64_t handoffRejectedMissingGpuStoreBefore = 0;
    uint64_t handoffRejectedStaleEpochBefore = 0;
    getSimInitialSafeStoreHandoffCompositionStats(handoffCreatedBefore,
                                                 handoffAvailableBefore,
                                                 handoffHostStoreEvictedBefore,
                                                 handoffHostMergeSkippedBefore,
                                                 handoffHostMergeFallbacksBefore,
                                                 handoffRejectedFastShadowBefore,
                                                 handoffRejectedProposalLoopBefore,
                                                 handoffRejectedMissingGpuStoreBefore,
                                                 handoffRejectedStaleEpochBefore);

    setenv("LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_HANDOFF", "1", 1);

    SimKernelContext mirroredDeviceContext(20, 20);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, mirroredDeviceContext);
    applySimCudaInitialRunSummariesToContext(mirroredSummaries,
                                             static_cast<uint64_t>(mirroredSummaries.size()),
                                             mirroredDeviceContext,
                                             false);

    std::vector<SimUpdateBand> mirroredAllBands(1);
    mirroredAllBands[0].rowStart = 1;
    mirroredAllBands[0].rowEnd = 20;
    mirroredAllBands[0].colStart = 1;
    mirroredAllBands[0].colEnd = 20;
    std::vector<SimScanCudaCandidateState> mirroredDeviceStoreStates;
    if (!collectSimCudaPersistentSafeCandidateStatesIntersectingBands(20,
                                                                      20,
                                                                      mirroredDeviceContext.gpuSafeCandidateStateStore,
                                                                      mirroredAllBands,
                                                                      mirroredDeviceStoreStates,
                                                                      &error))
    {
        std::cerr << "collectSimCudaPersistentSafeCandidateStatesIntersectingBands(mirroredDeviceContext) failed: "
                  << error << "\n";
        return 2;
    }

    SimPathWorkset mirroredDeviceGpuWorkset;
    std::vector<uint64_t> mirroredDeviceGpuAffectedStartCoords;
    if (!buildSimSafeWorksetFromCudaCandidateStateStore(20,
                                                        20,
                                                        pathSummary,
                                                        mirroredDeviceContext.gpuSafeCandidateStateStore,
                                                        mirroredDeviceGpuWorkset,
                                                        mirroredDeviceGpuAffectedStartCoords,
                                                        &error))
    {
        std::cerr << "buildSimSafeWorksetFromCudaCandidateStateStore(mirroredDeviceContext) failed: "
                  << error << "\n";
        return 2;
    }

    ok = expect_true(simCandidateContextsEqual(mirroredDeviceContext,
                                               mirroredContext),
                     "gated initial safe-store handoff matches baseline frontier") && ok;
    ok = expect_true(!mirroredDeviceContext.safeCandidateStateStore.valid,
                     "gated initial safe-store handoff evicts host safe store") && ok;
    ok = expect_true(mirroredDeviceContext.gpuSafeCandidateStateStore.valid,
                     "gated initial safe-store handoff keeps gpu safe store valid") && ok;
    ok = expect_true(mirroredDeviceContext.initialSafeStoreHandoffActive,
                     "gated initial safe-store handoff marks context active") && ok;
    ok = expect_true(simCanUseGpuFrontierCacheForResidency(mirroredDeviceContext),
                     "gated initial safe-store handoff marks gpu frontier cache reusable") && ok;
    ok = expect_candidate_states_equal(mirroredDeviceStoreStates,
                                       mirroredContext.safeCandidateStateStore.states,
                                       "gated initial safe-store handoff gpu store matches baseline host safe store") &&
         ok;
    ok = expect_worksets_equal(mirroredDeviceGpuWorkset,
                               mirroredHostWorkset,
                               "gated initial safe-store handoff gpu workset matches baseline host") && ok;
    ok = expect_equal_size(mirroredDeviceGpuAffectedStartCoords.size(),
                           mirroredExpectedAffectedStartCoords.size(),
                           "gated initial safe-store handoff affected start count") && ok;

    uint64_t handoffCreatedAfterBuild = 0;
    uint64_t handoffAvailableAfterBuild = 0;
    uint64_t handoffHostStoreEvictedAfterBuild = 0;
    uint64_t handoffHostMergeSkippedAfterBuild = 0;
    uint64_t handoffHostMergeFallbacksAfterBuild = 0;
    uint64_t handoffRejectedFastShadowAfterBuild = 0;
    uint64_t handoffRejectedProposalLoopAfterBuild = 0;
    uint64_t handoffRejectedMissingGpuStoreAfterBuild = 0;
    uint64_t handoffRejectedStaleEpochAfterBuild = 0;
    getSimInitialSafeStoreHandoffCompositionStats(handoffCreatedAfterBuild,
                                                 handoffAvailableAfterBuild,
                                                 handoffHostStoreEvictedAfterBuild,
                                                 handoffHostMergeSkippedAfterBuild,
                                                 handoffHostMergeFallbacksAfterBuild,
                                                 handoffRejectedFastShadowAfterBuild,
                                                 handoffRejectedProposalLoopAfterBuild,
                                                 handoffRejectedMissingGpuStoreAfterBuild,
                                                 handoffRejectedStaleEpochAfterBuild);
    ok = expect_equal_u64(handoffCreatedAfterBuild,
                          handoffCreatedBefore + 1,
                          "initial safe-store handoff telemetry created") && ok;
    ok = expect_equal_u64(handoffHostStoreEvictedAfterBuild,
                          handoffHostStoreEvictedBefore + 1,
                          "initial safe-store handoff telemetry host-store evicted") && ok;

    const std::string compositionQuery(20, 'A');
    const std::string compositionTarget(20, 'A');
    const std::string paddedCompositionQuery = " " + compositionQuery;
    const std::string paddedCompositionTarget = " " + compositionTarget;
    SimKernelContext missingGpuHandoffContext(20, 20);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, missingGpuHandoffContext);
    missingGpuHandoffContext.initialSafeStoreHandoffActive = true;
    SimSafeWorksetFallbackReason missingGpuFallback = SIM_SAFE_WORKSET_FALLBACK_NO_WORKSET;
    const bool missingGpuUpdateOk =
        applySimSafeAggregatedGpuUpdate(paddedCompositionQuery.c_str(),
                                        paddedCompositionTarget.c_str(),
                                        mirroredDeviceGpuWorkset,
                                        mirroredDeviceGpuAffectedStartCoords,
                                        missingGpuHandoffContext,
                                        false,
                                        false,
                                        false,
                                        &missingGpuFallback);
    ok = expect_true(!missingGpuUpdateOk,
                     "initial safe-store handoff composition missing-gpu update rejects") && ok;

    uint64_t handoffCreatedAfterUpdates = 0;
    uint64_t handoffAvailableAfterMissing = 0;
    uint64_t handoffHostStoreEvictedAfterUpdates = 0;
    uint64_t handoffHostMergeSkippedAfterMissing = 0;
    uint64_t handoffHostMergeFallbacksAfterUpdates = 0;
    uint64_t handoffRejectedFastShadowAfterUpdates = 0;
    uint64_t handoffRejectedProposalLoopAfterUpdates = 0;
    uint64_t handoffRejectedMissingGpuStoreAfterUpdates = 0;
    uint64_t handoffRejectedStaleEpochAfterUpdates = 0;
    getSimInitialSafeStoreHandoffCompositionStats(handoffCreatedAfterUpdates,
                                                 handoffAvailableAfterMissing,
                                                 handoffHostStoreEvictedAfterUpdates,
                                                 handoffHostMergeSkippedAfterMissing,
                                                 handoffHostMergeFallbacksAfterUpdates,
                                                 handoffRejectedFastShadowAfterUpdates,
                                                 handoffRejectedProposalLoopAfterUpdates,
                                                 handoffRejectedMissingGpuStoreAfterUpdates,
                                                 handoffRejectedStaleEpochAfterUpdates);
    ok = expect_equal_u64(handoffHostMergeFallbacksAfterUpdates,
                          handoffHostMergeFallbacksAfterBuild + 1,
                          "initial safe-store handoff telemetry host merge fallback") && ok;
    ok = expect_equal_u64(handoffRejectedMissingGpuStoreAfterUpdates,
                          handoffRejectedMissingGpuStoreAfterBuild + 1,
                          "initial safe-store handoff telemetry missing gpu store") && ok;

    if (hadPreviousInitialSafeStoreHandoff)
    {
        setenv("LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_HANDOFF",
               previousInitialSafeStoreHandoffValue.c_str(),
               1);
    }
    else
    {
        unsetenv("LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_HANDOFF");
    }
    if (hadPreviousInitialSafeStoreHandoffAlias)
    {
        setenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_SAFE_STORE_DEVICE_MAINTENANCE",
               previousInitialSafeStoreHandoffAliasValue.c_str(),
               1);
    }
    else
    {
        unsetenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_SAFE_STORE_DEVICE_MAINTENANCE");
    }

    const char *previousDeviceKLoop = getenv("LONGTARGET_ENABLE_SIM_CUDA_DEVICE_K_LOOP");
    const bool hadPreviousDeviceKLoop = previousDeviceKLoop != NULL;
    const std::string previousDeviceKLoopValue = hadPreviousDeviceKLoop ? previousDeviceKLoop : "";
    setenv("LONGTARGET_ENABLE_SIM_CUDA_DEVICE_K_LOOP", "1", 1);

    SimKernelContext proposalContext(20, 20);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, proposalContext);
    if (!uploadSimCudaPersistentSafeCandidateStateStore(safeWorksetCandidates,
                                                        proposalContext.gpuSafeCandidateStateStore,
                                                        &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(proposalContext) failed: "
                  << error << "\n";
        return 2;
    }
    proposalContext.proposalCandidateLoop = false;

    std::vector<SimScanCudaCandidateState> expectedProposalStates;
    if (!sim_scan_cuda_select_top_disjoint_candidate_states(safeWorksetCandidates,
                                                            3,
                                                            &expectedProposalStates,
                                                            &error))
    {
        std::cerr << "sim_scan_cuda_select_top_disjoint_candidate_states(expectedProposalStates) failed: "
                  << error << "\n";
        return 2;
    }

    std::vector<SimScanCudaCandidateState> collectedProposalStates;
    bool usedGpuSafeStore = false;
    if (!collectSimCudaProposalStatesForLoop(3,
                                             proposalContext,
                                             collectedProposalStates,
                                             &usedGpuSafeStore,
                                             &error))
    {
        std::cerr << "collectSimCudaProposalStatesForLoop failed: " << error << "\n";
        return 2;
    }

    if (hadPreviousDeviceKLoop)
    {
        setenv("LONGTARGET_ENABLE_SIM_CUDA_DEVICE_K_LOOP", previousDeviceKLoopValue.c_str(), 1);
    }
    else
    {
        unsetenv("LONGTARGET_ENABLE_SIM_CUDA_DEVICE_K_LOOP");
    }
    releaseSimCudaPersistentSafeCandidateStateStore(proposalContext.gpuSafeCandidateStateStore);

    ok = expect_true(usedGpuSafeStore,
                     "device_k_loop proposal path used gpu safe store") && ok;
    ok = expect_candidate_states_equal(collectedProposalStates,
                                       expectedProposalStates,
                                       "device_k_loop proposal states equal host selection") && ok;

    SimKernelContext proposalHandoffContext(20, 20);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, proposalHandoffContext);
    SimCudaPersistentSafeStoreHandle proposalHandoffStoreHandle;
    if (!uploadSimCudaPersistentSafeCandidateStateStore(safeWorksetCandidates,
                                                        proposalHandoffStoreHandle,
                                                        &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(proposalHandoffContext) failed: "
                  << error << "\n";
        return 2;
    }
    int proposalRunningMin = 0;
    for (size_t i = 0; i < expectedProposalStates.size(); ++i)
    {
        if (i == 0 || expectedProposalStates[i].score < proposalRunningMin)
        {
            proposalRunningMin = expectedProposalStates[i].score;
        }
    }
    applySimCudaInitialReduceResults(expectedProposalStates,
                                     proposalRunningMin,
                                     std::vector<SimScanCudaCandidateState>(),
                                     proposalHandoffStoreHandle,
                                     static_cast<uint64_t>(safeWorksetCandidates.size()),
                                     proposalHandoffContext,
                                     false,
                                     true);
    std::vector<SimScanCudaCandidateState> proposalHandoffStates;
    bool proposalHandoffUsedGpuSafeStore = false;
    if (!collectSimCudaProposalStatesForLoop(3,
                                             proposalHandoffContext,
                                             proposalHandoffStates,
                                             &proposalHandoffUsedGpuSafeStore,
                                             &error))
    {
        std::cerr << "collectSimCudaProposalStatesForLoop(proposalHandoffContext) failed: "
                  << error << "\n";
        return 2;
    }
    ok = expect_true(proposalHandoffContext.proposalCandidateLoop,
                     "proposal handoff keeps proposal loop enabled") && ok;
    ok = expect_true(!proposalHandoffContext.safeCandidateStateStore.valid,
                     "proposal handoff keeps host safe store evicted") && ok;
    ok = expect_true(proposalHandoffContext.gpuSafeCandidateStateStore.valid,
                     "proposal handoff preserves gpu safe store") && ok;
    ok = expect_candidate_states_equal(proposalHandoffStates,
                                       expectedProposalStates,
                                       "proposal handoff proposal states come from preserved gpu safe store") && ok;
    ok = expect_true(proposalHandoffUsedGpuSafeStore,
                     "proposal handoff uses preserved gpu safe store") && ok;

    SimKernelContext residencyPriorityContext(20, 20);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, residencyPriorityContext);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_DEVICE_K_LOOP", "1", 1);
    if (!uploadSimCudaPersistentSafeCandidateStateStore(safeWorksetCandidates,
                                                        residencyPriorityContext.gpuSafeCandidateStateStore,
                                                        &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(residencyPriorityContext) failed: "
                  << error << "\n";
        return 2;
    }
    residencyPriorityContext.proposalCandidateLoop = true;
    residencyPriorityContext.candidateCount = 0;

    std::vector<SimScanCudaCandidateState> residencyPriorityStates;
    bool residencyUsedGpuSafeStore = false;
    if (!collectSimCudaProposalStatesForLoop(3,
                                             residencyPriorityContext,
                                             residencyPriorityStates,
                                             &residencyUsedGpuSafeStore,
                                             &error))
    {
        releaseSimCudaPersistentSafeCandidateStateStore(residencyPriorityContext.gpuSafeCandidateStateStore);
        std::cerr << "collectSimCudaProposalStatesForLoop(residencyPriorityContext) failed: "
                  << error << "\n";
        return 1;
    }
    releaseSimCudaPersistentSafeCandidateStateStore(residencyPriorityContext.gpuSafeCandidateStateStore);

    ok = expect_true(residencyUsedGpuSafeStore,
                     "residency proposal path prefers gpu safe store over initial proposals") && ok;
    ok = expect_candidate_states_equal(residencyPriorityStates,
                                       expectedProposalStates,
                                       "residency proposal states come from gpu safe store") && ok;

    const std::string deviceKLoopQuery = "AAAAGGGG";
    const std::string deviceKLoopTarget = "AAAAGGGGTTTTAAAAGGGG";
    const std::string paddedDeviceKLoopQuery = " " + deviceKLoopQuery;
    const std::string paddedDeviceKLoopTarget = " " + deviceKLoopTarget;
    SimRequest deviceKLoopRequest(deviceKLoopTarget, 0, 0, 0, 0, 1, 128, -1000, 0);

    SimKernelContext deviceKLoopSeedContext(static_cast<long>(deviceKLoopQuery.size()),
                                            static_cast<long>(deviceKLoopTarget.size()));
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, deviceKLoopSeedContext);
    enumerateInitialSimCandidates(paddedDeviceKLoopQuery.c_str(),
                                  paddedDeviceKLoopTarget.c_str(),
                                  static_cast<long>(deviceKLoopQuery.size()),
                                  static_cast<long>(deviceKLoopTarget.size()),
                                  0,
                                  deviceKLoopSeedContext);

    std::vector<SimScanCudaCandidateState> deviceKLoopSeedStates;
    collectSimContextCandidateStates(deviceKLoopSeedContext, deviceKLoopSeedStates);
    ok = expect_true(!deviceKLoopSeedStates.empty(),
                     "locate device-k-loop seed states available") && ok;

    SimKernelContext expectedDeviceKLoopContext(static_cast<long>(deviceKLoopQuery.size()),
                                                static_cast<long>(deviceKLoopTarget.size()));
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, expectedDeviceKLoopContext);
    if (!uploadSimCudaPersistentSafeCandidateStateStore(deviceKLoopSeedStates,
                                                        expectedDeviceKLoopContext.gpuSafeCandidateStateStore,
                                                        &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(expectedDeviceKLoop) failed: "
                  << error << "\n";
        return 2;
    }
    expectedDeviceKLoopContext.proposalCandidateLoop = false;
    expectedDeviceKLoopContext.candidateCount = 0;
    std::vector<triplex> expectedDeviceKLoopTriplexes;
    uint64_t expectedDeviceKLoopSelectionCount = 0;
    for (int iteration = 0; iteration < K; ++iteration)
    {
        std::vector<SimScanCudaCandidateState> expectedProposalStates;
        bool expectedUsedGpuSafeStore = false;
        if (!collectSimCudaProposalStatesForLoop(1,
                                                 expectedDeviceKLoopContext,
                                                 expectedProposalStates,
                                                 &expectedUsedGpuSafeStore,
                                                 &error))
        {
            if (!error.empty())
            {
                std::cerr << "collectSimCudaProposalStatesForLoop(expectedDeviceKLoop) failed: "
                          << error << "\n";
                releaseSimCudaPersistentSafeCandidateStateStore(expectedDeviceKLoopContext.gpuSafeCandidateStateStore);
                return 2;
            }
            break;
        }
        if (!expectedUsedGpuSafeStore || expectedProposalStates.empty())
        {
            break;
        }

        ++expectedDeviceKLoopSelectionCount;
        const SimScanCudaCandidateState &proposal = expectedProposalStates[0];
        const long stari = static_cast<long>(proposal.startI) + 1;
        const long starj = static_cast<long>(proposal.startJ) + 1;
        const long endi = static_cast<long>(proposal.endI);
        const long endj = static_cast<long>(proposal.endJ);
        const long m1 = static_cast<long>(proposal.top);
        const long mm = static_cast<long>(proposal.bot);
        const long n1 = static_cast<long>(proposal.left);
        const long nn = static_cast<long>(proposal.right);
        const uint64_t proposalStartCoord = simScanCudaCandidateStateStartCoord(proposal);
        const std::vector<uint64_t> consumedStartCoords(1, proposalStartCoord);

        eraseSimCandidatesByStartCoords(consumedStartCoords, expectedDeviceKLoopContext);
        if (expectedDeviceKLoopContext.safeCandidateStateStore.valid)
        {
            eraseSimSafeCandidateStateStoreStartCoords(consumedStartCoords, expectedDeviceKLoopContext);
        }
        if (expectedDeviceKLoopContext.gpuSafeCandidateStateStore.valid &&
            !eraseSimCudaPersistentSafeCandidateStateStoreStartCoords(consumedStartCoords,
                                                                      expectedDeviceKLoopContext.gpuSafeCandidateStateStore,
                                                                      &error))
        {
            std::cerr << "eraseSimCudaPersistentSafeCandidateStateStoreStartCoords(expectedDeviceKLoop) failed: "
                      << error << "\n";
            releaseSimCudaPersistentSafeCandidateStateStore(expectedDeviceKLoopContext.gpuSafeCandidateStateStore);
            return 2;
        }

        ok = expect_equal_bool(materializeSimProposalStates(deviceKLoopRequest,
                                                            paddedDeviceKLoopQuery.c_str(),
                                                            paddedDeviceKLoopTarget.c_str(),
                                                            static_cast<long>(deviceKLoopTarget.size()),
                                                            0,
                                                            expectedProposalStates,
                                                            expectedDeviceKLoopContext,
                                                            expectedDeviceKLoopTriplexes),
                               true,
                               "locate device-k-loop sequential materialize succeeds") && ok;
        if (iteration + 1 < K)
        {
            updateSimCandidatesAfterTraceback(paddedDeviceKLoopQuery.c_str(),
                                              paddedDeviceKLoopTarget.c_str(),
                                              stari,
                                              endi,
                                              starj,
                                              endj,
                                              m1,
                                              mm,
                                              n1,
                                              nn,
                                              expectedDeviceKLoopContext);
        }
    }
    ok = expect_true(!expectedDeviceKLoopTriplexes.empty(),
                     "locate device-k-loop sequential materialize emits triplexes") && ok;
    releaseSimCudaPersistentSafeCandidateStateStore(expectedDeviceKLoopContext.gpuSafeCandidateStateStore);

    SimKernelContext actualDeviceKLoopContext(static_cast<long>(deviceKLoopQuery.size()),
                                              static_cast<long>(deviceKLoopTarget.size()));
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, actualDeviceKLoopContext);
    if (!uploadSimCudaPersistentSafeCandidateStateStore(deviceKLoopSeedStates,
                                                        actualDeviceKLoopContext.gpuSafeCandidateStateStore,
                                                        &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(deviceKLoop) failed: "
                  << error << "\n";
        return 2;
    }
    actualDeviceKLoopContext.proposalCandidateLoop = false;
    actualDeviceKLoopContext.candidateCount = 0;

    uint64_t locateDeviceKLoopAttemptsBefore = 0;
    uint64_t locateDeviceKLoopShortCircuitsBefore = 0;
    uint64_t deviceKLoopGpuSafeStoreSourcesBefore = 0;
    uint64_t deviceKLoopGpuFrontierCacheSourcesBefore = 0;
    uint64_t deviceKLoopGpuSafeStoreFullSourcesBefore = 0;
    double deviceKLoopSecondsBefore = 0.0;
    getSimLocateDeviceKLoopStats(locateDeviceKLoopAttemptsBefore,
                                 locateDeviceKLoopShortCircuitsBefore);
    getSimDeviceKLoopStats(deviceKLoopGpuSafeStoreSourcesBefore,
                           deviceKLoopGpuFrontierCacheSourcesBefore,
                           deviceKLoopGpuSafeStoreFullSourcesBefore,
                           deviceKLoopSecondsBefore);

    std::vector<triplex> actualDeviceKLoopTriplexes;
    runSimCandidateLoop(deviceKLoopRequest,
                        paddedDeviceKLoopQuery.c_str(),
                        paddedDeviceKLoopTarget.c_str(),
                        static_cast<long>(deviceKLoopTarget.size()),
                        0,
                        actualDeviceKLoopContext,
                        actualDeviceKLoopTriplexes);

    uint64_t locateDeviceKLoopAttemptsAfter = 0;
    uint64_t locateDeviceKLoopShortCircuitsAfter = 0;
    uint64_t deviceKLoopGpuSafeStoreSourcesAfter = 0;
    uint64_t deviceKLoopGpuFrontierCacheSourcesAfter = 0;
    uint64_t deviceKLoopGpuSafeStoreFullSourcesAfter = 0;
    double deviceKLoopSecondsAfter = 0.0;
    getSimLocateDeviceKLoopStats(locateDeviceKLoopAttemptsAfter,
                                 locateDeviceKLoopShortCircuitsAfter);
    getSimDeviceKLoopStats(deviceKLoopGpuSafeStoreSourcesAfter,
                           deviceKLoopGpuFrontierCacheSourcesAfter,
                           deviceKLoopGpuSafeStoreFullSourcesAfter,
                           deviceKLoopSecondsAfter);

    ok = expect_triplex_lists_equal(actualDeviceKLoopTriplexes,
                                    expectedDeviceKLoopTriplexes,
                                    "locate device-k-loop triplexes match manual materialize") && ok;
    ok = expect_equal_u64(locateDeviceKLoopAttemptsAfter - locateDeviceKLoopAttemptsBefore,
                          1,
                          "locate device-k-loop attempt count increments") && ok;
    ok = expect_equal_u64(locateDeviceKLoopShortCircuitsAfter - locateDeviceKLoopShortCircuitsBefore,
                          1,
                          "locate device-k-loop short-circuit count increments") && ok;
    ok = expect_true(deviceKLoopGpuSafeStoreSourcesAfter - deviceKLoopGpuSafeStoreSourcesBefore >=
                         expectedDeviceKLoopSelectionCount &&
                     expectedDeviceKLoopSelectionCount > 0,
                     "locate device-k-loop gpu safe-store source count increments") && ok;
    ok = expect_equal_u64(deviceKLoopGpuFrontierCacheSourcesAfter -
                          deviceKLoopGpuFrontierCacheSourcesBefore,
                          0,
                          "locate device-k-loop without cached frontier avoids frontier source count") && ok;
    ok = expect_true(deviceKLoopGpuSafeStoreFullSourcesAfter -
                         deviceKLoopGpuSafeStoreFullSourcesBefore >=
                     expectedDeviceKLoopSelectionCount &&
                     expectedDeviceKLoopSelectionCount > 0,
                     "locate device-k-loop without cached frontier uses full gpu safe-store selection") && ok;
    ok = expect_true(actualDeviceKLoopContext.gpuSafeCandidateStateStore.valid,
                     "locate device-k-loop preserves gpu safe store") && ok;
    ok = expect_true(deviceKLoopSecondsAfter >= deviceKLoopSecondsBefore,
                     "locate device-k-loop timing remains monotonic") && ok;
    releaseSimCudaPersistentSafeCandidateStateStore(actualDeviceKLoopContext.gpuSafeCandidateStateStore);

    const std::string refreshQuery(20, 'A');
    const std::string refreshTarget(20, 'A');
    const std::string paddedRefreshQuery = " " + refreshQuery;
    const std::string paddedRefreshTarget = " " + refreshTarget;
    SimLocateResult refreshLocateResult;
    refreshLocateResult.hasUpdateRegion = true;
    refreshLocateResult.rowStart = 5;
    refreshLocateResult.rowEnd = 10;
    refreshLocateResult.colStart = 7;
    refreshLocateResult.colEnd = 13;

    SimKernelContext baselineRefreshContext(20, 20);
    SimKernelContext preservedRefreshContext(20, 20);
    std::vector<SimScanCudaCandidateState> refreshSeedStates = safeWorksetCandidates;
    refreshSeedStates[1].score = 1000;
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, baselineRefreshContext);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, preservedRefreshContext);
    baselineRefreshContext.gapOpen = 10;
    baselineRefreshContext.gapExtend = 10;
    preservedRefreshContext.gapOpen = 10;
    preservedRefreshContext.gapExtend = 10;
    preservedRefreshContext.safeCandidateStateStore.valid = true;
    preservedRefreshContext.safeCandidateStateStore.states = refreshSeedStates;
    rebuildSimCandidateStateStoreIndex(preservedRefreshContext.safeCandidateStateStore);
    if (!uploadSimCudaPersistentSafeCandidateStateStore(refreshSeedStates,
                                                        preservedRefreshContext.gpuSafeCandidateStateStore,
                                                        &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(preservedRefreshContext) failed: "
                  << error << "\n";
        return 2;
    }

    std::vector<SimUpdateBand> refreshBands(1);
    refreshBands[0].rowStart = refreshLocateResult.rowStart;
    refreshBands[0].rowEnd = refreshLocateResult.rowEnd;
    refreshBands[0].colStart = refreshLocateResult.colStart;
    refreshBands[0].colEnd = refreshLocateResult.colEnd;
    std::vector<uint64_t> expectedRefreshTrackedStartCoords;
    collectSimSafeCandidateStateStoreIntersectingStartCoords(preservedRefreshContext.safeCandidateStateStore,
                                                             refreshBands,
                                                             expectedRefreshTrackedStartCoords);
    std::vector<uint64_t> gpuRefreshTrackedStartCoords;
    if (!collectSimCudaPersistentSafeCandidateStartCoordsIntersectingBands(
            20,
            20,
            preservedRefreshContext.gpuSafeCandidateStateStore,
            refreshBands,
            gpuRefreshTrackedStartCoords,
            &error))
    {
        std::cerr << "collectSimCudaPersistentSafeCandidateStartCoordsIntersectingBands failed: "
                  << error << "\n";
        return 2;
    }

    ok = expect_start_coords_equal(gpuRefreshTrackedStartCoords,
                                   expectedRefreshTrackedStartCoords,
                                   "gpu safe-store tracked start coords match host store") && ok;

    applySimLocatedUpdateRegion(paddedRefreshQuery.c_str(),
                                paddedRefreshTarget.c_str(),
                                refreshLocateResult,
                                baselineRefreshContext);
    const bool preservedSafeStore =
        applySimLocatedUpdateRegionWithSafeStoreRefresh(paddedRefreshQuery.c_str(),
                                                        paddedRefreshTarget.c_str(),
                                                        refreshLocateResult,
                                                        preservedRefreshContext);

    ok = expect_true(preservedSafeStore,
                     "exact update refresh preserves safe store") && ok;
    ok = expect_true(simCandidateContextsEqual(preservedRefreshContext,
                                               baselineRefreshContext),
                     "preserved safe-store exact update matches baseline candidates") && ok;
    ok = expect_true(preservedRefreshContext.safeCandidateStateStore.valid,
                     "preserved exact update keeps host safe store valid") && ok;
    ok = expect_true(preservedRefreshContext.gpuSafeCandidateStateStore.valid,
                     "preserved exact update keeps gpu safe store valid") && ok;
    ok = expect_true(!simCanUseGpuFrontierCacheForResidency(preservedRefreshContext),
                     "default preserved exact update keeps gpu frontier cache reuse disabled") && ok;
    ok = expect_true(find_candidate_state(preservedRefreshContext.safeCandidateStateStore, 1, 1) != NULL,
                     "preserved exact update keeps unaffected safe-store state") && ok;

    SimKernelContext gpuOnlyRefreshContext(20, 20);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, gpuOnlyRefreshContext);
    gpuOnlyRefreshContext.gapOpen = 10;
    gpuOnlyRefreshContext.gapExtend = 10;
    if (!uploadSimCudaPersistentSafeCandidateStateStore(refreshSeedStates,
                                                        gpuOnlyRefreshContext.gpuSafeCandidateStateStore,
                                                        &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(gpuOnlyRefreshContext) failed: "
                  << error << "\n";
        return 2;
    }

    const char *previousRefreshSafeWorksetDeviceMaintenance =
        getenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WORKSET_DEVICE_MAINTENANCE");
    const bool hadPreviousRefreshSafeWorksetDeviceMaintenance =
        previousRefreshSafeWorksetDeviceMaintenance != NULL;
    const std::string previousRefreshSafeWorksetDeviceMaintenanceValue =
        hadPreviousRefreshSafeWorksetDeviceMaintenance ? previousRefreshSafeWorksetDeviceMaintenance : "";
    setenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WORKSET_DEVICE_MAINTENANCE", "1", 1);

    const bool gpuOnlyPreservedSafeStore =
        applySimLocatedUpdateRegionWithSafeStoreRefresh(paddedRefreshQuery.c_str(),
                                                        paddedRefreshTarget.c_str(),
                                                        refreshLocateResult,
                                                        gpuOnlyRefreshContext);

    ok = expect_true(gpuOnlyPreservedSafeStore,
                     "gpu-only exact update refresh preserves gpu safe store") && ok;
    ok = expect_true(simCandidateContextsEqual(gpuOnlyRefreshContext,
                                               baselineRefreshContext),
                     "gpu-only exact update matches baseline candidates") && ok;
    ok = expect_true(!gpuOnlyRefreshContext.safeCandidateStateStore.valid,
                     "gpu-only exact update keeps host safe store evicted") && ok;
    ok = expect_true(gpuOnlyRefreshContext.gpuSafeCandidateStateStore.valid,
                     "gpu-only exact update keeps gpu safe store valid") && ok;
    ok = expect_true(simCanUseGpuFrontierCacheForResidency(gpuOnlyRefreshContext),
                     "gpu-only exact update marks gpu frontier cache reusable") && ok;
    if (hadPreviousRefreshSafeWorksetDeviceMaintenance)
    {
        setenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WORKSET_DEVICE_MAINTENANCE",
               previousRefreshSafeWorksetDeviceMaintenanceValue.c_str(),
               1);
    }
    else
    {
        unsetenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WORKSET_DEVICE_MAINTENANCE");
    }

    SimKernelContext seedResidencyContext(20, 20);
    SimKernelContext baselineResidencyContext(20, 20);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, seedResidencyContext);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, baselineResidencyContext);
    seedResidencyContext.gapOpen = 10;
    seedResidencyContext.gapExtend = 10;
    baselineResidencyContext.gapOpen = 10;
    baselineResidencyContext.gapExtend = 10;
    mergeSimCudaCandidateStatesIntoContext(refreshSeedStates, seedResidencyContext);
    mergeSimCudaCandidateStatesIntoContext(refreshSeedStates, baselineResidencyContext);
    baselineResidencyContext.safeCandidateStateStore.valid = true;
    baselineResidencyContext.safeCandidateStateStore.states = refreshSeedStates;
    rebuildSimCandidateStateStoreIndex(baselineResidencyContext.safeCandidateStateStore);

    std::vector<SimScanCudaCandidateState> seedFrontierStates;
    collectSimContextCandidateStates(seedResidencyContext, seedFrontierStates);
    const int seedRunningMin = static_cast<int>(seedResidencyContext.runningMin);

    std::vector<uint64_t> residencyTrackedStartCoords;
    collectSimSafeCandidateStateStoreIntersectingStartCoords(
        baselineResidencyContext.safeCandidateStateStore,
        refreshBands,
        residencyTrackedStartCoords);
    const std::vector<uint64_t> residencyUniqueTrackedStartCoords =
        makeSortedUniqueSimStartCoords(residencyTrackedStartCoords);

    int residencyScoreMatrixInt[128][128];
    fillSimScoreMatrixInt(baselineResidencyContext.scoreMatrix, residencyScoreMatrixInt);

    std::vector<SimScanCudaRequest> residencyRequests(refreshBands.size());
    std::vector<std::vector<uint64_t>> residencyBlockedDenseWords(refreshBands.size());
    for (size_t bandIndex = 0; bandIndex < refreshBands.size(); ++bandIndex)
    {
        const SimUpdateBand &band = refreshBands[bandIndex];
        const SimBlockedWordsView blockedView =
            makeSimBlockedWordsView(baselineResidencyContext.workspace,
                                    band.rowStart,
                                    band.rowEnd,
                                    band.colStart,
                                    band.colEnd,
                                    residencyBlockedDenseWords[bandIndex]);
        SimScanCudaRequest &request = residencyRequests[bandIndex];
        request.kind = SIM_SCAN_CUDA_REQUEST_REGION;
        request.A = paddedRefreshQuery.c_str();
        request.B = paddedRefreshTarget.c_str();
        request.queryLength = 20;
        request.targetLength = 20;
        request.rowStart = static_cast<int>(band.rowStart);
        request.rowEnd = static_cast<int>(band.rowEnd);
        request.colStart = static_cast<int>(band.colStart);
        request.colEnd = static_cast<int>(band.colEnd);
        request.gapOpen = static_cast<int>(baselineResidencyContext.gapOpen);
        request.gapExtend = static_cast<int>(baselineResidencyContext.gapExtend);
        request.scoreMatrix = residencyScoreMatrixInt;
        request.eventScoreFloor = seedRunningMin;
        request.blockedWords = blockedView.words;
        request.blockedWordStart = blockedView.wordStart;
        request.blockedWordCount = blockedView.wordCount;
        request.blockedWordStride = blockedView.wordStride;
        request.reduceCandidates = false;
        request.reduceAllCandidateStates = true;
        request.filterStartCoords = residencyUniqueTrackedStartCoords.data();
        request.filterStartCoordCount = static_cast<int>(residencyUniqueTrackedStartCoords.size());
        request.seedCandidates = NULL;
        request.seedCandidateCount = 0;
        request.seedRunningMin = seedRunningMin;
    }

    SimScanCudaRegionAggregationResult baselineResidencyAggregation;
    SimScanCudaBatchResult baselineResidencyBatchResult;
    if (!sim_scan_cuda_enumerate_region_candidate_states_aggregated(residencyRequests,
                                                                    &baselineResidencyAggregation,
                                                                    &baselineResidencyBatchResult,
                                                                    &error))
    {
        std::cerr << "sim_scan_cuda_enumerate_region_candidate_states_aggregated(residency) failed: "
                  << error << "\n";
        return 2;
    }

    std::vector<SimScanCudaCandidateState> baselineUpdatedStates =
        baselineResidencyAggregation.candidateStates;
    eraseSimCandidatesBySortedUniqueStartCoords(residencyUniqueTrackedStartCoords,
                                                baselineResidencyContext);
    eraseSimSafeCandidateStateStoreSortedUniqueStartCoords(residencyUniqueTrackedStartCoords,
                                                           baselineResidencyContext);
    for (size_t stateIndex = 0; stateIndex < baselineUpdatedStates.size(); ++stateIndex)
    {
        upsertSimCandidateStateStoreState(baselineUpdatedStates[stateIndex],
                                          baselineResidencyContext.safeCandidateStateStore);
    }
    mergeSimCudaCandidateStatesIntoContext(baselineUpdatedStates, baselineResidencyContext);
    pruneSimSafeCandidateStateStore(baselineResidencyContext);

    std::vector<SimScanCudaCandidateState> expectedResidencyFrontierStates;
    collectSimContextCandidateStates(baselineResidencyContext,
                                     expectedResidencyFrontierStates);

    std::vector<SimScanCudaCandidateState> expectedResidencyProposalStates;
    if (!sim_scan_cuda_select_top_disjoint_candidate_states(
            expectedResidencyFrontierStates,
            3,
            &expectedResidencyProposalStates,
            &error))
    {
        std::cerr << "sim_scan_cuda_select_top_disjoint_candidate_states(expectedResidencyProposalStates) failed: "
                  << error << "\n";
        return 2;
    }

    SimCudaPersistentSafeStoreHandle residencyStoreHandle;
    if (!uploadSimCudaPersistentSafeCandidateStateStore(refreshSeedStates,
                                                        residencyStoreHandle,
                                                        &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(residencyStoreHandle) failed: "
                  << error << "\n";
        return 2;
    }

    SimScanCudaRegionResidencyResult residencyResult;
    SimScanCudaBatchResult residencyBatchResult;
    if (!sim_scan_cuda_apply_region_candidate_states_residency(residencyRequests,
                                                               seedFrontierStates,
                                                               seedRunningMin,
                                                               &residencyStoreHandle,
                                                               &residencyResult,
                                                               &residencyBatchResult,
                                                               &error))
    {
        releaseSimCudaPersistentSafeCandidateStateStore(residencyStoreHandle);
        std::cerr << "sim_scan_cuda_apply_region_candidate_states_residency failed: "
                  << error << "\n";
        return 2;
    }

    std::vector<SimUpdateBand> residencyAllBands(1);
    residencyAllBands[0].rowStart = 1;
    residencyAllBands[0].rowEnd = 20;
    residencyAllBands[0].colStart = 1;
    residencyAllBands[0].colEnd = 20;
    std::vector<SimScanCudaCandidateState> actualResidencyStoreStates;
    if (!collectSimCudaPersistentSafeCandidateStatesIntersectingBands(
            20,
            20,
            residencyStoreHandle,
            residencyAllBands,
            actualResidencyStoreStates,
            &error))
    {
        releaseSimCudaPersistentSafeCandidateStateStore(residencyStoreHandle);
        std::cerr << "collectSimCudaPersistentSafeCandidateStatesIntersectingBands(residency) failed: "
                  << error << "\n";
        return 2;
    }

    std::vector<SimScanCudaCandidateState> actualResidencyProposalStates;
    if (!sim_scan_cuda_select_top_disjoint_candidate_states_from_persistent_store(
            residencyStoreHandle,
            3,
            &actualResidencyProposalStates,
            &error))
    {
        releaseSimCudaPersistentSafeCandidateStateStore(residencyStoreHandle);
        std::cerr << "sim_scan_cuda_select_top_disjoint_candidate_states_from_persistent_store(residency) failed: "
                  << error << "\n";
        return 2;
    }

    SimCudaPersistentSafeStoreHandle residencyNoMaterializeStoreHandle;
    if (!uploadSimCudaPersistentSafeCandidateStateStore(refreshSeedStates,
                                                        residencyNoMaterializeStoreHandle,
                                                        &error))
    {
        releaseSimCudaPersistentSafeCandidateStateStore(residencyStoreHandle);
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(residencyNoMaterializeStoreHandle) failed: "
                  << error << "\n";
        return 2;
    }

    SimScanCudaRegionResidencyResult residencyNoMaterializeResult;
    SimScanCudaBatchResult residencyNoMaterializeBatchResult;
    if (!sim_scan_cuda_apply_region_candidate_states_residency(residencyRequests,
                                                               seedFrontierStates,
                                                               seedRunningMin,
                                                               &residencyNoMaterializeStoreHandle,
                                                               &residencyNoMaterializeResult,
                                                               &residencyNoMaterializeBatchResult,
                                                               &error,
                                                               false))
    {
        releaseSimCudaPersistentSafeCandidateStateStore(residencyStoreHandle);
        releaseSimCudaPersistentSafeCandidateStateStore(residencyNoMaterializeStoreHandle);
        std::cerr << "sim_scan_cuda_apply_region_candidate_states_residency(no materialize) failed: "
                  << error << "\n";
        return 2;
    }

    std::vector<SimScanCudaCandidateState> actualResidencyNoMaterializeStoreStates;
    if (!collectSimCudaPersistentSafeCandidateStatesIntersectingBands(
            20,
            20,
            residencyNoMaterializeStoreHandle,
            residencyAllBands,
            actualResidencyNoMaterializeStoreStates,
            &error))
    {
        releaseSimCudaPersistentSafeCandidateStateStore(residencyStoreHandle);
        releaseSimCudaPersistentSafeCandidateStateStore(residencyNoMaterializeStoreHandle);
        std::cerr << "collectSimCudaPersistentSafeCandidateStatesIntersectingBands(residency no materialize) failed: "
                  << error << "\n";
        return 2;
    }
    releaseSimCudaPersistentSafeCandidateStateStore(residencyStoreHandle);
    releaseSimCudaPersistentSafeCandidateStateStore(residencyNoMaterializeStoreHandle);

    ok = expect_true(!residencyUniqueTrackedStartCoords.empty(),
                     "residency tracked start coords non-empty") && ok;
    ok = expect_candidate_states_equal(residencyResult.frontierStates,
                                       expectedResidencyFrontierStates,
                                       "region residency frontier states match host merge") && ok;
    ok = expect_equal_long(residencyResult.runningMin,
                           baselineResidencyContext.runningMin,
                           "region residency running min matches host merge") && ok;
    ok = expect_equal_u64(residencyResult.eventCount,
                          baselineResidencyAggregation.eventCount,
                          "region residency event count matches aggregated scan") && ok;
    ok = expect_equal_u64(residencyResult.runSummaryCount,
                          baselineResidencyAggregation.runSummaryCount,
                          "region residency run summary count matches aggregated scan") && ok;
    ok = expect_equal_u64(residencyResult.updatedStateCount,
                          static_cast<uint64_t>(baselineUpdatedStates.size()),
                          "region residency updated state count matches aggregated scan") && ok;
    ok = expect_candidate_states_equal(actualResidencyStoreStates,
                                       baselineResidencyContext.safeCandidateStateStore.states,
                                       "region residency persistent store matches host safe store") && ok;
    ok = expect_candidate_states_equal(actualResidencyProposalStates,
                                       expectedResidencyProposalStates,
                                       "region residency proposal states match host selection") && ok;
    ok = expect_true(residencyNoMaterializeResult.frontierStates.empty(),
                     "region residency no-materialize frontier states remain host-empty") && ok;
    ok = expect_equal_u64(residencyNoMaterializeResult.frontierStateCount,
                          static_cast<uint64_t>(expectedResidencyFrontierStates.size()),
                          "region residency no-materialize frontier count matches host merge") && ok;
    ok = expect_equal_long(residencyNoMaterializeResult.runningMin,
                           baselineResidencyContext.runningMin,
                           "region residency no-materialize running min matches host merge") && ok;
    ok = expect_equal_u64(residencyNoMaterializeResult.eventCount,
                          baselineResidencyAggregation.eventCount,
                          "region residency no-materialize event count matches aggregated scan") && ok;
    ok = expect_equal_u64(residencyNoMaterializeResult.runSummaryCount,
                          baselineResidencyAggregation.runSummaryCount,
                          "region residency no-materialize run summary count matches aggregated scan") && ok;
    ok = expect_equal_u64(residencyNoMaterializeResult.updatedStateCount,
                          static_cast<uint64_t>(baselineUpdatedStates.size()),
                          "region residency no-materialize updated state count matches aggregated scan") && ok;
    ok = expect_candidate_states_equal(actualResidencyNoMaterializeStoreStates,
                                       baselineResidencyContext.safeCandidateStateStore.states,
                                       "region residency no-materialize persistent store matches host safe store") && ok;

    const char *previousSafeWorksetDeviceMaintenance =
        getenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WORKSET_DEVICE_MAINTENANCE");
    const bool hadPreviousSafeWorksetDeviceMaintenance =
        previousSafeWorksetDeviceMaintenance != NULL;
    const std::string previousSafeWorksetDeviceMaintenanceValue =
        hadPreviousSafeWorksetDeviceMaintenance ? previousSafeWorksetDeviceMaintenance : "";
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WORKSET_DEVICE_MAINTENANCE");

    SimKernelContext baselineAggregatedUpdateContext(20, 20);
    SimKernelContext gatedAggregatedUpdateContext(20, 20);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, baselineAggregatedUpdateContext);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, gatedAggregatedUpdateContext);
    baselineAggregatedUpdateContext.gapOpen = 10;
    baselineAggregatedUpdateContext.gapExtend = 10;
    gatedAggregatedUpdateContext.gapOpen = 10;
    gatedAggregatedUpdateContext.gapExtend = 10;
    mergeSimCudaCandidateStatesIntoContext(refreshSeedStates, baselineAggregatedUpdateContext);
    mergeSimCudaCandidateStatesIntoContext(refreshSeedStates, gatedAggregatedUpdateContext);
    baselineAggregatedUpdateContext.safeCandidateStateStore.valid = true;
    baselineAggregatedUpdateContext.safeCandidateStateStore.states = refreshSeedStates;
    rebuildSimCandidateStateStoreIndex(baselineAggregatedUpdateContext.safeCandidateStateStore);
    gatedAggregatedUpdateContext.safeCandidateStateStore.valid = true;
    gatedAggregatedUpdateContext.safeCandidateStateStore.states = refreshSeedStates;
    rebuildSimCandidateStateStoreIndex(gatedAggregatedUpdateContext.safeCandidateStateStore);
    if (!uploadSimCudaPersistentSafeCandidateStateStore(refreshSeedStates,
                                                        baselineAggregatedUpdateContext.gpuSafeCandidateStateStore,
                                                        &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(baselineAggregatedUpdateContext) failed: "
                  << error << "\n";
        return 2;
    }
    if (!uploadSimCudaPersistentSafeCandidateStateStore(refreshSeedStates,
                                                        gatedAggregatedUpdateContext.gpuSafeCandidateStateStore,
                                                        &error))
    {
        std::cerr << "uploadSimCudaPersistentSafeCandidateStateStore(gatedAggregatedUpdateContext) failed: "
                  << error << "\n";
        return 2;
    }

    SimPathWorkset aggregatedUpdateWorkset;
    aggregatedUpdateWorkset.hasWorkset = true;
    aggregatedUpdateWorkset.bands = refreshBands;
    aggregatedUpdateWorkset.cellCount = simPathWorksetCellCountFromBands(refreshBands);

    SimSafeWorksetFallbackReason baselineAggregatedFallback = SIM_SAFE_WORKSET_FALLBACK_INVALID_STORE;
    const bool baselineAggregatedUpdateOk =
        applySimSafeAggregatedGpuUpdate(paddedRefreshQuery.c_str(),
                                        paddedRefreshTarget.c_str(),
                                        aggregatedUpdateWorkset,
                                        residencyUniqueTrackedStartCoords,
                                        baselineAggregatedUpdateContext,
                                        false,
                                        false,
                                        false,
                                        &baselineAggregatedFallback);
    ok = expect_true(baselineAggregatedUpdateOk,
                     "baseline aggregated gpu update succeeds") && ok;

    uint64_t handoffCreatedBeforeAggregated = 0;
    uint64_t handoffAvailableBeforeAggregated = 0;
    uint64_t handoffHostStoreEvictedBeforeAggregated = 0;
    uint64_t handoffHostMergeSkippedBeforeAggregated = 0;
    uint64_t handoffHostMergeFallbacksBeforeAggregated = 0;
    uint64_t handoffRejectedFastShadowBeforeAggregated = 0;
    uint64_t handoffRejectedProposalLoopBeforeAggregated = 0;
    uint64_t handoffRejectedMissingGpuStoreBeforeAggregated = 0;
    uint64_t handoffRejectedStaleEpochBeforeAggregated = 0;
    getSimInitialSafeStoreHandoffCompositionStats(handoffCreatedBeforeAggregated,
                                                 handoffAvailableBeforeAggregated,
                                                 handoffHostStoreEvictedBeforeAggregated,
                                                 handoffHostMergeSkippedBeforeAggregated,
                                                 handoffHostMergeFallbacksBeforeAggregated,
                                                 handoffRejectedFastShadowBeforeAggregated,
                                                 handoffRejectedProposalLoopBeforeAggregated,
                                                 handoffRejectedMissingGpuStoreBeforeAggregated,
                                                 handoffRejectedStaleEpochBeforeAggregated);
    resetSimCandidateStateStore(gatedAggregatedUpdateContext.safeCandidateStateStore, false);
    gatedAggregatedUpdateContext.initialSafeStoreHandoffActive = true;

    setenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WORKSET_DEVICE_MAINTENANCE", "1", 1);
    SimSafeWorksetFallbackReason gatedAggregatedFallback = SIM_SAFE_WORKSET_FALLBACK_INVALID_STORE;
    const bool gatedAggregatedUpdateOk =
        applySimSafeAggregatedGpuUpdate(paddedRefreshQuery.c_str(),
                                        paddedRefreshTarget.c_str(),
                                        aggregatedUpdateWorkset,
                                        residencyUniqueTrackedStartCoords,
                                        gatedAggregatedUpdateContext,
                                        false,
                                        false,
                                        false,
                                        &gatedAggregatedFallback);
    ok = expect_true(gatedAggregatedUpdateOk,
                     "gated aggregated gpu update succeeds") && ok;

    uint64_t handoffCreatedAfterAggregated = 0;
    uint64_t handoffAvailableAfterAggregated = 0;
    uint64_t handoffHostStoreEvictedAfterAggregated = 0;
    uint64_t handoffHostMergeSkippedAfterAggregated = 0;
    uint64_t handoffHostMergeFallbacksAfterAggregated = 0;
    uint64_t handoffRejectedFastShadowAfterAggregated = 0;
    uint64_t handoffRejectedProposalLoopAfterAggregated = 0;
    uint64_t handoffRejectedMissingGpuStoreAfterAggregated = 0;
    uint64_t handoffRejectedStaleEpochAfterAggregated = 0;
    getSimInitialSafeStoreHandoffCompositionStats(handoffCreatedAfterAggregated,
                                                 handoffAvailableAfterAggregated,
                                                 handoffHostStoreEvictedAfterAggregated,
                                                 handoffHostMergeSkippedAfterAggregated,
                                                 handoffHostMergeFallbacksAfterAggregated,
                                                 handoffRejectedFastShadowAfterAggregated,
                                                 handoffRejectedProposalLoopAfterAggregated,
                                                 handoffRejectedMissingGpuStoreAfterAggregated,
                                                 handoffRejectedStaleEpochAfterAggregated);
    ok = expect_equal_u64(handoffAvailableAfterAggregated,
                          handoffAvailableBeforeAggregated + 1,
                          "initial safe-store handoff telemetry aggregated available for locate") && ok;
    ok = expect_equal_u64(handoffHostMergeSkippedAfterAggregated,
                          handoffHostMergeSkippedBeforeAggregated + 1,
                          "initial safe-store handoff telemetry aggregated host merge skipped") && ok;
    ok = expect_equal_u64(handoffHostMergeFallbacksAfterAggregated,
                          handoffHostMergeFallbacksBeforeAggregated,
                          "initial safe-store handoff telemetry aggregated no host merge fallback") && ok;
    ok = expect_equal_u64(handoffRejectedStaleEpochAfterAggregated,
                          handoffRejectedStaleEpochBeforeAggregated,
                          "initial safe-store handoff telemetry aggregated no stale rejection") && ok;

    std::vector<SimScanCudaCandidateState> gatedAggregatedStoreStates;
    if (!collectSimCudaPersistentSafeCandidateStatesIntersectingBands(
            20,
            20,
            gatedAggregatedUpdateContext.gpuSafeCandidateStateStore,
            residencyAllBands,
            gatedAggregatedStoreStates,
            &error))
    {
        std::cerr << "collectSimCudaPersistentSafeCandidateStatesIntersectingBands(gated aggregated update) failed: "
                  << error << "\n";
        return 2;
    }

    ok = expect_true(simCandidateContextsEqual(gatedAggregatedUpdateContext,
                                               baselineAggregatedUpdateContext),
                     "gated aggregated gpu update matches baseline frontier") && ok;
    ok = expect_true(!gatedAggregatedUpdateContext.safeCandidateStateStore.valid,
                     "gated aggregated gpu update evicts host safe store") && ok;
    ok = expect_true(gatedAggregatedUpdateContext.gpuSafeCandidateStateStore.valid,
                     "gated aggregated gpu update keeps gpu safe store valid") && ok;
    ok = expect_true(simCanUseGpuFrontierCacheForResidency(gatedAggregatedUpdateContext),
                     "gated aggregated gpu update marks gpu frontier cache reusable") && ok;
    ok = expect_candidate_states_equal(gatedAggregatedStoreStates,
                                       baselineAggregatedUpdateContext.safeCandidateStateStore.states,
                                       "gated aggregated gpu update gpu store matches baseline host safe store") && ok;

    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WORKSET_DEVICE_MAINTENANCE");
    SimSafeWorksetFallbackReason baselineSecondAggregatedFallback = SIM_SAFE_WORKSET_FALLBACK_INVALID_STORE;
    const bool baselineSecondAggregatedUpdateOk =
        applySimSafeAggregatedGpuUpdate(paddedRefreshQuery.c_str(),
                                        paddedRefreshTarget.c_str(),
                                        aggregatedUpdateWorkset,
                                        residencyUniqueTrackedStartCoords,
                                        baselineAggregatedUpdateContext,
                                        false,
                                        false,
                                        false,
                                        &baselineSecondAggregatedFallback);
    ok = expect_true(baselineSecondAggregatedUpdateOk,
                     "baseline aggregated gpu update succeeds after prior update") && ok;

    setenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WORKSET_DEVICE_MAINTENANCE", "1", 1);
    gatedAggregatedUpdateContext.candidateCount = 0;
    gatedAggregatedUpdateContext.candidateMinHeap.clear();
    clearSimCandidateStartIndex(gatedAggregatedUpdateContext.candidateStartIndex);

    SimSafeWorksetFallbackReason gatedSecondAggregatedFallback = SIM_SAFE_WORKSET_FALLBACK_INVALID_STORE;
    const bool gatedSecondAggregatedUpdateOk =
        applySimSafeAggregatedGpuUpdate(paddedRefreshQuery.c_str(),
                                        paddedRefreshTarget.c_str(),
                                        aggregatedUpdateWorkset,
                                        residencyUniqueTrackedStartCoords,
                                        gatedAggregatedUpdateContext,
                                        false,
                                        false,
                                        false,
                                        &gatedSecondAggregatedFallback);
    ok = expect_true(gatedSecondAggregatedUpdateOk,
                     "gated aggregated gpu update succeeds after host frontier eviction") && ok;

    std::vector<SimScanCudaCandidateState> gatedAggregatedStoreStatesAfterReuse;
    if (!collectSimCudaPersistentSafeCandidateStatesIntersectingBands(
            20,
            20,
            gatedAggregatedUpdateContext.gpuSafeCandidateStateStore,
            residencyAllBands,
            gatedAggregatedStoreStatesAfterReuse,
            &error))
    {
        std::cerr << "collectSimCudaPersistentSafeCandidateStatesIntersectingBands(gated aggregated update reuse) failed: "
                  << error << "\n";
        return 2;
    }

    SimFastFallbackReason gatedReuseMismatchReason = SIM_FAST_FALLBACK_SHADOW_CANDIDATE_VALUE;
    const bool gatedReuseMatchesBaseline =
        simCandidateContextsEqual(gatedAggregatedUpdateContext,
                                  baselineAggregatedUpdateContext,
                                  &gatedReuseMismatchReason);
    ok = expect_true(gatedReuseMatchesBaseline,
                     "gated aggregated gpu update reuse matches baseline frontier") && ok;
    ok = expect_candidate_states_equal(gatedAggregatedStoreStatesAfterReuse,
                                       baselineAggregatedUpdateContext.safeCandidateStateStore.states,
                                       "gated aggregated gpu update reuse gpu store matches baseline host safe store") && ok;

    std::vector<SimScanCudaCandidateState> hostOnlyMutatedState(1);
    hostOnlyMutatedState[0] =
        makeSimScanCudaCandidateState(gatedAggregatedUpdateContext.candidates[0]);
    hostOnlyMutatedState[0].score += 17;
    mergeSimCudaCandidateStatesIntoContext(hostOnlyMutatedState,
                                           gatedAggregatedUpdateContext);
    ok = expect_true(!simCanUseGpuFrontierCacheForResidency(gatedAggregatedUpdateContext),
                     "host-only frontier mutation disables gpu frontier cache reuse") && ok;

    if (hadPreviousSafeWorksetDeviceMaintenance)
    {
        setenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WORKSET_DEVICE_MAINTENANCE",
               previousSafeWorksetDeviceMaintenanceValue.c_str(),
               1);
    }
    else
    {
        unsetenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WORKSET_DEVICE_MAINTENANCE");
    }

    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
