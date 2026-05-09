#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

#include "../cuda/sim_locate_cuda.h"
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

static bool expect_close_double(double actual, double expected, double tolerance, const char *label)
{
    if (std::fabs(actual - expected) <= tolerance)
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

static std::vector<SimCandidate> sorted_candidates(const SimKernelContext &context)
{
    std::vector<SimCandidate> candidates(static_cast<size_t>(context.candidateCount));
    for (long i = 0; i < context.candidateCount; ++i)
    {
        candidates[static_cast<size_t>(i)] = context.candidates[static_cast<size_t>(i)];
    }
    std::sort(candidates.begin(), candidates.end(), [](const SimCandidate &lhs, const SimCandidate &rhs) {
        if (lhs.SCORE != rhs.SCORE) return lhs.SCORE < rhs.SCORE;
        if (lhs.STARI != rhs.STARI) return lhs.STARI < rhs.STARI;
        if (lhs.STARJ != rhs.STARJ) return lhs.STARJ < rhs.STARJ;
        if (lhs.ENDI != rhs.ENDI) return lhs.ENDI < rhs.ENDI;
        if (lhs.ENDJ != rhs.ENDJ) return lhs.ENDJ < rhs.ENDJ;
        if (lhs.TOP != rhs.TOP) return lhs.TOP < rhs.TOP;
        if (lhs.BOT != rhs.BOT) return lhs.BOT < rhs.BOT;
        if (lhs.LEFT != rhs.LEFT) return lhs.LEFT < rhs.LEFT;
        return lhs.RIGHT < rhs.RIGHT;
    });
    return candidates;
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

static bool expect_candidates_equal(const SimKernelContext &actual,
                                    const SimKernelContext &expected,
                                    const char *label)
{
    if (actual.candidateCount != expected.candidateCount)
    {
        std::cerr << label << ": candidateCount mismatch expected "
                  << expected.candidateCount << ", got " << actual.candidateCount << "\n";
        return false;
    }

    const std::vector<SimCandidate> lhs = sorted_candidates(actual);
    const std::vector<SimCandidate> rhs = sorted_candidates(expected);
    for (size_t i = 0; i < lhs.size(); ++i)
    {
        if (memcmp(&lhs[i], &rhs[i], sizeof(SimCandidate)) != 0)
        {
            std::cerr << label << ": candidate mismatch at index " << i << "\n";
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

static void setup_materialized_context(const std::string &query,
                                       const std::string &target,
                                       long minScore,
                                       SimKernelContext &context,
                                       SimCandidate &candidateOut)
{
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);

    const std::string paddedQuery = " " + query;
    const std::string paddedTarget = " " + target;
    const char *A = paddedQuery.c_str();
    const char *B = paddedTarget.c_str();
    enumerateInitialSimCandidates(A,
                                  B,
                                  static_cast<long>(query.size()),
                                  static_cast<long>(target.size()),
                                  minScore,
                                  context);
    if (!popHighestScoringSimCandidate(context, candidateOut))
    {
        std::cerr << "failed to pop initial candidate\n";
        std::exit(1);
    }

    std::vector<triplex> triplexes;
    SimRequest request(target, 0, minScore, 0, 0, 1, 128, -1000, 0);
    if (!materializeSimCandidate(request,
                                 A,
                                 B,
                                 static_cast<long>(target.size()),
                                 candidateOut.SCORE,
                                 candidateOut.STARI + 1,
                                 candidateOut.STARJ + 1,
                                 candidateOut.ENDI,
                                 candidateOut.ENDJ,
                                 0,
                                 context,
                                 triplexes))
    {
        std::cerr << "failed to materialize candidate\n";
        std::exit(1);
    }
}

} // namespace

int main()
{
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA");
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_REGION");
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK");
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_LOCATE");
    unsetenv("LONGTARGET_SIM_CUDA_LOCATE_EXACT_PRECHECK");
    unsetenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WINDOW");
    unsetenv("LONGTARGET_SIM_CUDA_SAFE_WINDOW_MAX_COUNT");
    unsetenv("LONGTARGET_SIM_CUDA_SAFE_WINDOW_COMPARE_BUILDER");
    unsetenv("LONGTARGET_SIM_CUDA_SAFE_WINDOW_PLANNER");

    bool ok = true;

    ok = expect_equal_int(static_cast<int>(parseSimLocateCudaMode(NULL)),
                          static_cast<int>(SIM_LOCATE_CUDA_MODE_SAFE_WORKSET),
                          "default locate mode safe_workset") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimLocateCudaMode("fast")),
                          static_cast<int>(SIM_LOCATE_CUDA_MODE_FAST),
                          "parse fast locate mode") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimLocateCudaMode("safe_workset")),
                          static_cast<int>(SIM_LOCATE_CUDA_MODE_SAFE_WORKSET),
                          "parse safe_workset locate mode") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimLocateCudaMode("unexpected")),
                          static_cast<int>(SIM_LOCATE_CUDA_MODE_EXACT),
                          "invalid locate mode falls back to exact") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimLocateExactPrecheckMode(NULL)),
                          static_cast<int>(SIM_LOCATE_EXACT_PRECHECK_OFF),
                          "default locate exact precheck mode off") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimLocateExactPrecheckMode("shadow")),
                          static_cast<int>(SIM_LOCATE_EXACT_PRECHECK_SHADOW),
                          "parse locate exact precheck shadow mode") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimLocateExactPrecheckMode("on")),
                          static_cast<int>(SIM_LOCATE_EXACT_PRECHECK_ON),
                          "parse locate exact precheck on mode") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimLocateExactPrecheckMode("unexpected")),
                          static_cast<int>(SIM_LOCATE_EXACT_PRECHECK_OFF),
                          "invalid locate exact precheck mode falls back to off") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimProposalMaterializeBackend(NULL)),
                          static_cast<int>(SIM_PROPOSAL_MATERIALIZE_BACKEND_CPU),
                          "default proposal materialize backend cpu") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimProposalMaterializeBackend("cuda_batch_traceback")),
                          static_cast<int>(SIM_PROPOSAL_MATERIALIZE_BACKEND_CUDA_BATCH_TRACEBACK),
                          "parse proposal cuda batch traceback backend") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimProposalMaterializeBackend("hybrid")),
                          static_cast<int>(SIM_PROPOSAL_MATERIALIZE_BACKEND_HYBRID),
                          "parse proposal hybrid backend") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimProposalMaterializeBackend("unexpected")),
                          static_cast<int>(SIM_PROPOSAL_MATERIALIZE_BACKEND_CPU),
                          "invalid proposal materialize backend falls back to cpu") && ok;
    ok = expect_equal_long(simParseProposalTracebackMinCells(NULL),
                           65536,
                           "default proposal traceback min cells") && ok;
    ok = expect_equal_long(simParseProposalTracebackMinCells("131072"),
                           131072,
                           "parse proposal traceback min cells") && ok;
    ok = expect_equal_long(simParseProposalTracebackMinCells("0"),
                           65536,
                           "invalid proposal traceback min cells falls back to default") && ok;
    ok = expect_equal_bool(simSafeWindowCudaEnabledRuntime(),
                           true,
                           "default safe_window runtime enabled") && ok;
    ok = expect_equal_int(simSafeWindowCudaMaxCountRuntime(),
                          128,
                          "default safe_window max count") && ok;
    ok = expect_equal_bool(parseSimSafeWindowCompareBuilder(NULL, false),
                           false,
                           "default safe_window compare-builder policy disabled") && ok;
    ok = expect_equal_bool(parseSimSafeWindowCompareBuilder("1", false),
                           true,
                           "explicit safe_window compare-builder policy enabled") && ok;
    ok = expect_equal_bool(parseSimSafeWindowCompareBuilder("0", false),
                           false,
                           "explicit safe_window compare-builder policy disabled") && ok;
    ok = expect_equal_bool(parseSimSafeWindowCompareBuilder("0", true),
                           true,
                           "validate mode forces safe_window compare-builder policy") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimSafeWindowPlannerMode(NULL)),
                          static_cast<int>(SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE),
                          "default safe_window planner mode dense") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimSafeWindowPlannerMode("sparse_v1")),
                          static_cast<int>(SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V1),
                          "parse sparse_v1 safe_window planner mode") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimSafeWindowPlannerMode("unexpected")),
                          static_cast<int>(SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE),
                          "invalid safe_window planner mode falls back to dense") && ok;
    ok = expect_equal_string(simSafeWindowCudaPlannerModeName(SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE),
                             "dense",
                             "dense planner mode name") && ok;
    ok = expect_equal_string(simSafeWindowCudaPlannerModeName(SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V1),
                             "sparse_v1",
                             "sparse_v1 planner mode name") && ok;
    ok = expect_equal_bool(shouldBuildSimSafeWorksetBuilderAfterSafeWindow(true, false),
                           false,
                           "usable safe_window plan skips builder by default") && ok;
    ok = expect_equal_bool(shouldBuildSimSafeWorksetBuilderAfterSafeWindow(false, false),
                           true,
                           "unusable safe_window plan still builds builder") && ok;
    ok = expect_equal_bool(shouldBuildSimSafeWorksetBuilderAfterSafeWindow(true, true),
                           true,
                           "compare-builder mode keeps builder even for usable safe_window plan") && ok;

    SimLocateResult defaultResult;
    ok = expect_equal_bool(defaultResult.hasUpdateRegion, false, "default hasUpdateRegion") && ok;
    ok = expect_equal_bool(defaultResult.usedCuda, false, "default usedCuda") && ok;
    ok = expect_equal_long(defaultResult.rowStart, 0, "default rowStart") && ok;
    ok = expect_equal_long(defaultResult.rowEnd, 0, "default rowEnd") && ok;
    ok = expect_equal_long(defaultResult.colStart, 0, "default colStart") && ok;
    ok = expect_equal_long(defaultResult.colEnd, 0, "default colEnd") && ok;
    ok = expect_equal_long(static_cast<long>(defaultResult.locateCellCount), 0, "default locateCellCount") && ok;
    ok = expect_equal_long(static_cast<long>(defaultResult.baseCellCount), 0, "default baseCellCount") && ok;
    ok = expect_equal_long(static_cast<long>(defaultResult.expansionCellCount), 0, "default expansionCellCount") && ok;
    ok = expect_equal_bool(defaultResult.stopByNoCross, false, "default stopByNoCross") && ok;
    ok = expect_equal_bool(defaultResult.stopByBoundary, false, "default stopByBoundary") && ok;

    SimLocatePrecheckResult defaultPrecheckResult;
    ok = expect_equal_bool(defaultPrecheckResult.attempted, false, "default precheck attempted") && ok;
    ok = expect_equal_bool(defaultPrecheckResult.confirmedNoUpdate, false, "default precheck confirmedNoUpdate") && ok;
    ok = expect_equal_bool(defaultPrecheckResult.needsFullLocate, true, "default precheck needsFullLocate") && ok;
    ok = expect_equal_bool(defaultPrecheckResult.usedCuda, false, "default precheck usedCuda") && ok;
    ok = expect_equal_long(defaultPrecheckResult.minRowBound, 0, "default precheck minRowBound") && ok;
    ok = expect_equal_long(defaultPrecheckResult.minColBound, 0, "default precheck minColBound") && ok;
    ok = expect_equal_long(static_cast<long>(defaultPrecheckResult.baseCellCount), 0, "default precheck baseCellCount") && ok;
    ok = expect_equal_long(static_cast<long>(defaultPrecheckResult.expansionCellCount), 0, "default precheck expansionCellCount") && ok;
    ok = expect_equal_long(static_cast<long>(defaultPrecheckResult.scannedCellCount), 0, "default precheck scannedCellCount") && ok;
    ok = expect_equal_bool(defaultPrecheckResult.stopByNoCross, false, "default precheck stopByNoCross") && ok;
    ok = expect_equal_bool(defaultPrecheckResult.stopByBoundary, false, "default precheck stopByBoundary") && ok;

    SimLocateCudaBatchResult defaultBatchResult;
    ok = expect_equal_bool(defaultBatchResult.usedCuda, false, "default locate batch usedCuda") && ok;
    ok = expect_equal_bool(defaultBatchResult.usedSharedInputBatchPath,
                           false,
                           "default locate batch shared-input path") && ok;
    ok = expect_equal_u64(defaultBatchResult.taskCount, 0, "default locate batch taskCount") && ok;
    ok = expect_equal_u64(defaultBatchResult.launchCount, 0, "default locate batch launchCount") && ok;
    ok = expect_equal_u64(defaultBatchResult.sharedInputRequestCount,
                          0,
                          "default locate batch shared-input request count") && ok;
    ok = expect_equal_u64(defaultBatchResult.serialFallbackRequestCount,
                          0,
                          "default locate batch serial fallback request count") && ok;

    std::string error;
    SimLocateCudaRequest stubRequest;
    stubRequest.A = " A";
    stubRequest.B = " A";
    stubRequest.queryLength = 1;
    stubRequest.targetLength = 1;
    stubRequest.rowStart = 1;
    stubRequest.rowEnd = 1;
    stubRequest.colStart = 1;
    stubRequest.colEnd = 1;
    if (sim_locate_cuda_init(0, &error))
    {
        std::cerr << "stub locate init should fail when CUDA is unavailable\n";
        return 1;
    }
    ok = expect_true(error == "CUDA support not built", "stub init error") && ok;
    error.clear();
    if (sim_locate_cuda_locate_region(stubRequest, &defaultResult, &error))
    {
        std::cerr << "stub locate should fail when CUDA is unavailable\n";
        return 1;
    }
    ok = expect_true(error == "CUDA support not built", "stub locate error") && ok;
    std::vector<SimLocateCudaRequest> emptyLocateBatchRequests;
    std::vector<SimLocateResult> emptyLocateBatchResults;
    error.clear();
    defaultBatchResult = SimLocateCudaBatchResult();
    if (!sim_locate_cuda_locate_region_batch(emptyLocateBatchRequests,
                                             &emptyLocateBatchResults,
                                             &defaultBatchResult,
                                             &error))
    {
        std::cerr << "empty locate batch should succeed, got error: " << error << "\n";
        return 1;
    }
    ok = expect_equal_bool(emptyLocateBatchResults.empty(), true, "empty locate batch results") && ok;
    ok = expect_equal_bool(error.empty(), true, "empty locate batch error") && ok;
    ok = expect_equal_u64(defaultBatchResult.taskCount, 0, "empty locate batch taskCount") && ok;
    ok = expect_equal_u64(defaultBatchResult.launchCount, 0, "empty locate batch launchCount") && ok;
    ok = expect_equal_bool(defaultBatchResult.usedSharedInputBatchPath,
                           false,
                           "empty locate batch shared-input path") && ok;
    ok = expect_equal_u64(defaultBatchResult.sharedInputRequestCount,
                          0,
                          "empty locate batch shared-input request count") && ok;
    ok = expect_equal_u64(defaultBatchResult.serialFallbackRequestCount,
                          0,
                          "empty locate batch serial fallback request count") && ok;

    std::vector<SimLocateCudaRequest> locateBatchRequests(2, stubRequest);
    emptyLocateBatchResults.push_back(SimLocateResult());
    error.clear();
    defaultBatchResult = SimLocateCudaBatchResult();
    if (sim_locate_cuda_locate_region_batch(locateBatchRequests,
                                            &emptyLocateBatchResults,
                                            &defaultBatchResult,
                                            &error))
    {
        std::cerr << "stub locate batch should fail when CUDA is unavailable\n";
        return 1;
    }
    ok = expect_equal_bool(emptyLocateBatchResults.empty(), true, "failed locate batch clears results") && ok;
    ok = expect_equal_bool(defaultBatchResult.usedCuda, false, "failed locate batch usedCuda") && ok;
    ok = expect_equal_bool(defaultBatchResult.usedSharedInputBatchPath,
                           false,
                           "failed locate batch shared-input path") && ok;
    ok = expect_equal_u64(defaultBatchResult.taskCount, 0, "failed locate batch taskCount") && ok;
    ok = expect_equal_u64(defaultBatchResult.launchCount, 0, "failed locate batch launchCount") && ok;
    ok = expect_equal_u64(defaultBatchResult.sharedInputRequestCount,
                          0,
                          "failed locate batch shared-input request count") && ok;
    ok = expect_equal_u64(defaultBatchResult.serialFallbackRequestCount,
                          0,
                          "failed locate batch serial fallback request count") && ok;
    ok = expect_true(error == "CUDA support not built", "stub locate batch error") && ok;

    std::vector<SimScanCudaCandidateState> fastBoundsCandidates(2);
    fastBoundsCandidates[0].startI = 7;
    fastBoundsCandidates[0].startJ = 9;
    fastBoundsCandidates[0].bot = 12;
    fastBoundsCandidates[0].right = 14;
    fastBoundsCandidates[1].startI = 5;
    fastBoundsCandidates[1].startJ = 6;
    fastBoundsCandidates[1].bot = 8;
    fastBoundsCandidates[1].right = 10;
    const SimLocateFastBounds fastBounds =
        computeSimLocateFastBounds(30,
                                   30,
                                   10,
                                   20,
                                   10,
                                   20,
                                   fastBoundsCandidates.data(),
                                   static_cast<int>(fastBoundsCandidates.size()),
                                   3);
    ok = expect_equal_long(fastBounds.minRowStart, 2, "fast bounds row start") && ok;
    ok = expect_equal_long(fastBounds.minColStart, 3, "fast bounds col start") && ok;
    ok = expect_equal_bool(fastBounds.expandedByCandidates, true, "fast bounds candidate expansion") && ok;
    const SimLocateFastBounds exactPrecheckBounds =
        computeSimLocateExactPrecheckBounds(30,
                                            30,
                                            10,
                                            20,
                                            10,
                                            20,
                                            fastBoundsCandidates.data(),
                                            static_cast<int>(fastBoundsCandidates.size()));
    ok = expect_equal_long(exactPrecheckBounds.minRowStart, 5, "exact precheck bounds row start") && ok;
    ok = expect_equal_long(exactPrecheckBounds.minColStart, 6, "exact precheck bounds col start") && ok;
    ok = expect_equal_bool(exactPrecheckBounds.expandedByCandidates, true, "exact precheck bounds candidate expansion") && ok;
    const SimLocateResult fastLocateResult =
        computeSimLocateFastResult(30,
                                   30,
                                   10,
                                   20,
                                   10,
                                   20,
                                   fastBoundsCandidates.data(),
                                   static_cast<int>(fastBoundsCandidates.size()),
                                   3);
    ok = expect_equal_bool(fastLocateResult.hasUpdateRegion, true, "fast locate result present") && ok;
    ok = expect_equal_long(fastLocateResult.rowStart, 2, "fast locate row start") && ok;
    ok = expect_equal_long(fastLocateResult.rowEnd, 20, "fast locate row end") && ok;
    ok = expect_equal_long(fastLocateResult.colStart, 3, "fast locate col start") && ok;
    ok = expect_equal_long(fastLocateResult.colEnd, 20, "fast locate col end") && ok;
    ok = expect_equal_long(static_cast<long>(fastLocateResult.locateCellCount), 0, "fast locate skips DP cells") && ok;
    ok = expect_equal_bool(fastLocateResult.usedCuda, false, "fast locate result stays host-side") && ok;
    std::vector<SimScanCudaCandidateState> explodingFastBoundsCandidates(1);
    explodingFastBoundsCandidates[0].startI = 1;
    explodingFastBoundsCandidates[0].startJ = 1;
    explodingFastBoundsCandidates[0].bot = 50;
    explodingFastBoundsCandidates[0].right = 50;
    const SimLocateResult cappedFastLocateResult =
        computeSimLocateFastResult(80,
                                   80,
                                   40,
                                   50,
                                   40,
                                   50,
                                   explodingFastBoundsCandidates.data(),
                                   static_cast<int>(explodingFastBoundsCandidates.size()),
                                   2);
    ok = expect_equal_long(cappedFastLocateResult.rowStart, 38, "fast locate caps row expansion") && ok;
    ok = expect_equal_long(cappedFastLocateResult.colStart, 38, "fast locate caps col expansion") && ok;

    {
        const std::string precheckQuery = "AAAAAA";
        const std::string precheckTarget = "AAAAAA";
        const long minScore = 5;
        const std::string paddedPrecheckQuery = " " + precheckQuery;
        const std::string paddedPrecheckTarget = " " + precheckTarget;
        SimKernelContext precheckNoUpdateContext(static_cast<long>(precheckQuery.size()),
                                                 static_cast<long>(precheckTarget.size()));
        SimKernelContext precheckNeedsLocateContext(static_cast<long>(precheckQuery.size()),
                                                    static_cast<long>(precheckTarget.size()));
        SimCandidate noUpdateCandidate;
        SimCandidate needsLocateCandidate;
        setup_materialized_context(precheckQuery,
                                   precheckTarget,
                                   minScore,
                                   precheckNoUpdateContext,
                                   noUpdateCandidate);
        setup_materialized_context(precheckQuery,
                                   precheckTarget,
                                   minScore,
                                   precheckNeedsLocateContext,
                                   needsLocateCandidate);
        precheckNoUpdateContext.runningMin = 1000;

        const SimLocatePrecheckResult noUpdatePrecheck =
            locateSimUpdateRegionExactPrecheck(paddedPrecheckQuery.c_str(),
                                               paddedPrecheckTarget.c_str(),
                                               noUpdateCandidate.TOP,
                                               noUpdateCandidate.BOT,
                                               noUpdateCandidate.LEFT,
                                               noUpdateCandidate.RIGHT,
                                               precheckNoUpdateContext);
        ok = expect_equal_bool(noUpdatePrecheck.attempted, true, "precheck no-update attempted") && ok;
        ok = expect_equal_bool(noUpdatePrecheck.confirmedNoUpdate, true, "precheck no-update confirmed") && ok;
        ok = expect_equal_bool(noUpdatePrecheck.needsFullLocate, false, "precheck no-update avoids full locate") && ok;
        ok = expect_true(noUpdatePrecheck.scannedCellCount >= noUpdatePrecheck.baseCellCount,
                         "precheck no-update scanned cells recorded") && ok;

        const SimLocatePrecheckResult needsLocatePrecheck =
            locateSimUpdateRegionExactPrecheck(paddedPrecheckQuery.c_str(),
                                               paddedPrecheckTarget.c_str(),
                                               needsLocateCandidate.TOP,
                                               needsLocateCandidate.BOT,
                                               needsLocateCandidate.LEFT,
                                               needsLocateCandidate.RIGHT,
                                               precheckNeedsLocateContext);
        ok = expect_equal_bool(needsLocatePrecheck.attempted, true, "precheck update attempted") && ok;
        ok = expect_equal_bool(needsLocatePrecheck.confirmedNoUpdate, false, "precheck update does not confirm no-update") && ok;
        ok = expect_equal_bool(needsLocatePrecheck.needsFullLocate, true, "precheck update requires full locate") && ok;
    }

    const long tracebackScript[] = {0, 0, 2, 0, -1, 0};
    const SimTracebackPathSummary pathSummary =
        summarizeSimTracebackPath(5,
                                  7,
                                  5,
                                  6,
                                  tracebackScript);
    ok = expect_equal_bool(pathSummary.valid, true, "path summary valid") && ok;
    ok = expect_equal_long(pathSummary.rowStart, 5, "path summary row start") && ok;
    ok = expect_equal_long(pathSummary.rowEnd, 9, "path summary row end") && ok;
    ok = expect_equal_long(pathSummary.colStart, 7, "path summary col start") && ok;
    ok = expect_equal_long(pathSummary.colEnd, 12, "path summary col end") && ok;
    ok = expect_equal_u64(pathSummary.stepCount, 7, "path summary step count") && ok;
    ok = expect_equal_size(pathSummary.rowMinCols.size(), 5, "path summary row count") && ok;
    ok = expect_equal_size(pathSummary.segments.size(), 5, "path summary segment count") && ok;
    ok = expect_equal_int(static_cast<int>(pathSummary.segments[0].kind),
                          static_cast<int>(SIM_TRACEBACK_SEGMENT_DIAGONAL),
                          "path summary segment0 kind") && ok;
    ok = expect_equal_long(pathSummary.segments[0].rowStart, 5, "path summary segment0 row start") && ok;
    ok = expect_equal_long(pathSummary.segments[0].rowEnd, 6, "path summary segment0 row end") && ok;
    ok = expect_equal_long(pathSummary.segments[0].colStart, 7, "path summary segment0 col start") && ok;
    ok = expect_equal_long(pathSummary.segments[0].colEnd, 8, "path summary segment0 col end") && ok;
    ok = expect_equal_int(static_cast<int>(pathSummary.segments[1].kind),
                          static_cast<int>(SIM_TRACEBACK_SEGMENT_HORIZONTAL),
                          "path summary segment1 kind") && ok;
    ok = expect_equal_long(pathSummary.segments[1].rowStart, 6, "path summary segment1 row start") && ok;
    ok = expect_equal_long(pathSummary.segments[1].rowEnd, 6, "path summary segment1 row end") && ok;
    ok = expect_equal_long(pathSummary.segments[1].colStart, 9, "path summary segment1 col start") && ok;
    ok = expect_equal_long(pathSummary.segments[1].colEnd, 10, "path summary segment1 col end") && ok;
    ok = expect_equal_int(static_cast<int>(pathSummary.segments[3].kind),
                          static_cast<int>(SIM_TRACEBACK_SEGMENT_VERTICAL),
                          "path summary segment3 kind") && ok;
    ok = expect_equal_long(pathSummary.segments[3].rowStart, 8, "path summary segment3 row start") && ok;
    ok = expect_equal_long(pathSummary.segments[3].rowEnd, 8, "path summary segment3 row end") && ok;
    ok = expect_equal_long(pathSummary.segments[3].colStart, 11, "path summary segment3 col start") && ok;
    ok = expect_equal_long(pathSummary.segments[3].colEnd, 11, "path summary segment3 col end") && ok;
    ok = expect_equal_long(pathSummary.rowMinCols[0], 7, "path summary row0 min col") && ok;
    ok = expect_equal_long(pathSummary.rowMaxCols[0], 7, "path summary row0 max col") && ok;
    ok = expect_equal_long(pathSummary.rowMinCols[1], 8, "path summary row1 min col") && ok;
    ok = expect_equal_long(pathSummary.rowMaxCols[1], 10, "path summary row1 max col") && ok;
    ok = expect_equal_long(pathSummary.rowMinCols[2], 11, "path summary row2 min col") && ok;
    ok = expect_equal_long(pathSummary.rowMaxCols[2], 11, "path summary row2 max col") && ok;
    ok = expect_equal_long(pathSummary.rowMinCols[3], 11, "path summary row3 min col") && ok;
    ok = expect_equal_long(pathSummary.rowMaxCols[3], 11, "path summary row3 max col") && ok;
    ok = expect_equal_long(pathSummary.rowMinCols[4], 12, "path summary row4 min col") && ok;
    ok = expect_equal_long(pathSummary.rowMaxCols[4], 12, "path summary row4 max col") && ok;

    const SimPathWorkset pathWorkset =
        buildSimPathWorkset(20,
                            20,
                            pathSummary,
                            0,
                            2,
                            9999);
    ok = expect_equal_bool(pathWorkset.hasWorkset, true, "path workset present") && ok;
    ok = expect_equal_bool(pathWorkset.fallbackToRect, false, "path workset stays sparse") && ok;
    ok = expect_equal_u64(pathWorkset.cellCount, 11, "path workset cell count") && ok;
    ok = expect_equal_size(pathWorkset.bands.size(), 3, "path workset band count") && ok;
    ok = expect_equal_long(pathWorkset.bands[0].rowStart, 5, "path workset band0 row start") && ok;
    ok = expect_equal_long(pathWorkset.bands[0].rowEnd, 6, "path workset band0 row end") && ok;
    ok = expect_equal_long(pathWorkset.bands[0].colStart, 7, "path workset band0 col start") && ok;
    ok = expect_equal_long(pathWorkset.bands[0].colEnd, 10, "path workset band0 col end") && ok;
    ok = expect_equal_long(pathWorkset.bands[1].rowStart, 7, "path workset band1 row start") && ok;
    ok = expect_equal_long(pathWorkset.bands[1].rowEnd, 8, "path workset band1 row end") && ok;
    ok = expect_equal_long(pathWorkset.bands[1].colStart, 11, "path workset band1 col start") && ok;
    ok = expect_equal_long(pathWorkset.bands[1].colEnd, 11, "path workset band1 col end") && ok;
    ok = expect_equal_long(pathWorkset.bands[2].rowStart, 9, "path workset band2 row start") && ok;
    ok = expect_equal_long(pathWorkset.bands[2].rowEnd, 9, "path workset band2 row end") && ok;
    ok = expect_equal_long(pathWorkset.bands[2].colStart, 12, "path workset band2 col start") && ok;
    ok = expect_equal_long(pathWorkset.bands[2].colEnd, 12, "path workset band2 col end") && ok;

    const SimPathWorkset fallbackWorkset =
        buildSimPathWorkset(20,
                            20,
                            pathSummary,
                            2,
                            8,
                            40);
    ok = expect_equal_bool(fallbackWorkset.hasWorkset, true, "fallback workset present") && ok;
    ok = expect_equal_bool(fallbackWorkset.fallbackToRect, true, "fallback workset requests rectangle") && ok;

    std::vector<SimScanCudaCandidateState> safeWorksetCandidates(3);
    safeWorksetCandidates[0].startI = 5;
    safeWorksetCandidates[0].startJ = 7;
    safeWorksetCandidates[0].bot = 9;
    safeWorksetCandidates[0].right = 12;
    safeWorksetCandidates[1].startI = 1;
    safeWorksetCandidates[1].startJ = 1;
    safeWorksetCandidates[1].bot = 4;
    safeWorksetCandidates[1].right = 6;
    safeWorksetCandidates[2].startI = 6;
    safeWorksetCandidates[2].startJ = 9;
    safeWorksetCandidates[2].bot = 10;
    safeWorksetCandidates[2].right = 13;
    std::vector<uint64_t> affectedStartCoords;
    const SimPathWorkset safeWorkset =
        buildSimSafeWorksetFromCandidateStates(20,
                                               20,
                                               pathSummary,
                                               safeWorksetCandidates,
                                               &affectedStartCoords);
    ok = expect_equal_bool(safeWorkset.hasWorkset, true, "safe workset present") && ok;
    ok = expect_equal_bool(safeWorkset.fallbackToRect, false, "safe workset stays sparse") && ok;
    ok = expect_equal_size(affectedStartCoords.size(), 2, "safe workset affected start count") && ok;
    ok = expect_equal_size(safeWorkset.bands.size(), 3, "safe workset band count") && ok;
    ok = expect_equal_long(safeWorkset.bands[0].rowStart, 5, "safe workset band0 row start") && ok;
    ok = expect_equal_long(safeWorkset.bands[0].rowEnd, 5, "safe workset band0 row end") && ok;
    ok = expect_equal_long(safeWorkset.bands[0].colStart, 7, "safe workset band0 col start") && ok;
    ok = expect_equal_long(safeWorkset.bands[0].colEnd, 12, "safe workset band0 col end") && ok;
    ok = expect_equal_long(safeWorkset.bands[1].rowStart, 6, "safe workset band1 row start") && ok;
    ok = expect_equal_long(safeWorkset.bands[1].rowEnd, 9, "safe workset band1 row end") && ok;
    ok = expect_equal_long(safeWorkset.bands[1].colStart, 7, "safe workset band1 col start") && ok;
    ok = expect_equal_long(safeWorkset.bands[1].colEnd, 13, "safe workset band1 col end") && ok;
    ok = expect_equal_long(safeWorkset.bands[2].rowStart, 10, "safe workset band2 row start") && ok;
    ok = expect_equal_long(safeWorkset.bands[2].rowEnd, 10, "safe workset band2 row end") && ok;
    ok = expect_equal_long(safeWorkset.bands[2].colStart, 9, "safe workset band2 col start") && ok;
    ok = expect_equal_long(safeWorkset.bands[2].colEnd, 13, "safe workset band2 col end") && ok;

    std::vector<SimScanCudaCandidateState> closureSafeWorksetCandidates = safeWorksetCandidates;
    closureSafeWorksetCandidates.resize(4);
    closureSafeWorksetCandidates[3].startI = 6;
    closureSafeWorksetCandidates[3].startJ = 13;
    closureSafeWorksetCandidates[3].bot = 10;
    closureSafeWorksetCandidates[3].right = 15;
    std::vector<uint64_t> closureAffectedStartCoords;
    const SimPathWorkset closureSafeWorkset =
        buildSimSafeWorksetFromCandidateStates(20,
                                               20,
                                               pathSummary,
                                               closureSafeWorksetCandidates,
                                               &closureAffectedStartCoords);
    const std::vector<uint64_t> uniqueClosureAffectedStartCoords =
        makeSortedUniqueSimStartCoords(closureAffectedStartCoords);
    ok = expect_equal_bool(closureSafeWorkset.hasWorkset, true, "safe workset closure present") && ok;
    ok = expect_equal_size(uniqueClosureAffectedStartCoords.size(),
                           3,
                           "safe workset closure affected start count") && ok;
    if (uniqueClosureAffectedStartCoords.size() == 3)
    {
        ok = expect_equal_u64(uniqueClosureAffectedStartCoords[0],
                              packSimCoord(5, 7),
                              "safe workset closure affected start0") && ok;
        ok = expect_equal_u64(uniqueClosureAffectedStartCoords[1],
                              packSimCoord(6, 9),
                              "safe workset closure affected start1") && ok;
        ok = expect_equal_u64(uniqueClosureAffectedStartCoords[2],
                              packSimCoord(6, 13),
                              "safe workset closure affected start2") && ok;
    }
    ok = expect_equal_size(closureSafeWorkset.bands.size(), 3, "safe workset closure band count") && ok;
    if (closureSafeWorkset.bands.size() == 3)
    {
        ok = expect_equal_long(closureSafeWorkset.bands[0].rowStart, 5, "safe workset closure band0 row start") && ok;
        ok = expect_equal_long(closureSafeWorkset.bands[0].rowEnd, 5, "safe workset closure band0 row end") && ok;
        ok = expect_equal_long(closureSafeWorkset.bands[0].colStart, 7, "safe workset closure band0 col start") && ok;
        ok = expect_equal_long(closureSafeWorkset.bands[0].colEnd, 12, "safe workset closure band0 col end") && ok;
        ok = expect_equal_long(closureSafeWorkset.bands[1].rowStart, 6, "safe workset closure band1 row start") && ok;
        ok = expect_equal_long(closureSafeWorkset.bands[1].rowEnd, 9, "safe workset closure band1 row end") && ok;
        ok = expect_equal_long(closureSafeWorkset.bands[1].colStart, 7, "safe workset closure band1 col start") && ok;
        ok = expect_equal_long(closureSafeWorkset.bands[1].colEnd, 15, "safe workset closure band1 col end") && ok;
        ok = expect_equal_long(closureSafeWorkset.bands[2].rowStart, 10, "safe workset closure band2 row start") && ok;
        ok = expect_equal_long(closureSafeWorkset.bands[2].rowEnd, 10, "safe workset closure band2 row end") && ok;
        ok = expect_equal_long(closureSafeWorkset.bands[2].colStart, 9, "safe workset closure band2 col start") && ok;
        ok = expect_equal_long(closureSafeWorkset.bands[2].colEnd, 15, "safe workset closure band2 col end") && ok;
    }

    uint64_t fastWorksetBandCount = 0;
    uint64_t fastWorksetCellCount = 0;
    uint64_t fastSegmentCount = 0;
    uint64_t fastDiagonalSegmentCount = 0;
    uint64_t fastHorizontalSegmentCount = 0;
    uint64_t fastVerticalSegmentCount = 0;
    uint64_t fastFallbackNoWorksetCount = 0;
    uint64_t fastFallbackAreaCapCount = 0;
    uint64_t fastFallbackShadowRunningMinCount = 0;
    uint64_t fastFallbackShadowCandidateCountCount = 0;
    uint64_t fastFallbackShadowCandidateValueCount = 0;
    getSimFastPathStats(fastWorksetBandCount,
                        fastWorksetCellCount,
                        fastSegmentCount,
                        fastDiagonalSegmentCount,
                        fastHorizontalSegmentCount,
                        fastVerticalSegmentCount,
                        fastFallbackNoWorksetCount,
                        fastFallbackAreaCapCount,
                        fastFallbackShadowRunningMinCount,
                        fastFallbackShadowCandidateCountCount,
                        fastFallbackShadowCandidateValueCount);
    const uint64_t fastWorksetBandCountBefore = fastWorksetBandCount;
    const uint64_t fastWorksetCellCountBefore = fastWorksetCellCount;
    const uint64_t fastSegmentCountBefore = fastSegmentCount;
    const uint64_t fastDiagonalSegmentCountBefore = fastDiagonalSegmentCount;
    const uint64_t fastHorizontalSegmentCountBefore = fastHorizontalSegmentCount;
    const uint64_t fastVerticalSegmentCountBefore = fastVerticalSegmentCount;
    const uint64_t fastFallbackNoWorksetCountBefore = fastFallbackNoWorksetCount;
    const uint64_t fastFallbackAreaCapCountBefore = fastFallbackAreaCapCount;
    const uint64_t fastFallbackShadowRunningMinCountBefore = fastFallbackShadowRunningMinCount;
    const uint64_t fastFallbackShadowCandidateCountCountBefore = fastFallbackShadowCandidateCountCount;
    const uint64_t fastFallbackShadowCandidateValueCountBefore = fastFallbackShadowCandidateValueCount;

    recordSimFastPathSummary(pathSummary);
    recordSimFastWorkset(pathWorkset);
    recordSimFastFallbackReason(SIM_FAST_FALLBACK_NO_WORKSET);
    recordSimFastFallbackReason(SIM_FAST_FALLBACK_AREA_CAP);
    recordSimFastFallbackReason(SIM_FAST_FALLBACK_SHADOW_RUNNING_MIN);
    recordSimFastFallbackReason(SIM_FAST_FALLBACK_SHADOW_CANDIDATE_COUNT);
    recordSimFastFallbackReason(SIM_FAST_FALLBACK_SHADOW_CANDIDATE_VALUE);

    getSimFastPathStats(fastWorksetBandCount,
                        fastWorksetCellCount,
                        fastSegmentCount,
                        fastDiagonalSegmentCount,
                        fastHorizontalSegmentCount,
                        fastVerticalSegmentCount,
                        fastFallbackNoWorksetCount,
                        fastFallbackAreaCapCount,
                        fastFallbackShadowRunningMinCount,
                        fastFallbackShadowCandidateCountCount,
                        fastFallbackShadowCandidateValueCount);
    ok = expect_equal_u64(fastWorksetBandCount,
                          fastWorksetBandCountBefore + pathWorkset.bands.size(),
                          "fast telemetry band count") && ok;
    ok = expect_equal_u64(fastWorksetCellCount,
                          fastWorksetCellCountBefore + pathWorkset.cellCount,
                          "fast telemetry workset cells") && ok;
    ok = expect_equal_u64(fastSegmentCount,
                          fastSegmentCountBefore + pathSummary.segments.size(),
                          "fast telemetry segment count") && ok;
    ok = expect_equal_u64(fastDiagonalSegmentCount,
                          fastDiagonalSegmentCountBefore + 3,
                          "fast telemetry diagonal segment count") && ok;
    ok = expect_equal_u64(fastHorizontalSegmentCount,
                          fastHorizontalSegmentCountBefore + 1,
                          "fast telemetry horizontal segment count") && ok;
    ok = expect_equal_u64(fastVerticalSegmentCount,
                          fastVerticalSegmentCountBefore + 1,
                          "fast telemetry vertical segment count") && ok;
    ok = expect_equal_u64(fastFallbackNoWorksetCount,
                          fastFallbackNoWorksetCountBefore + 1,
                          "fast telemetry no-workset fallback count") && ok;
    ok = expect_equal_u64(fastFallbackAreaCapCount,
                          fastFallbackAreaCapCountBefore + 1,
                          "fast telemetry area-cap fallback count") && ok;
    ok = expect_equal_u64(fastFallbackShadowRunningMinCount,
                          fastFallbackShadowRunningMinCountBefore + 1,
                          "fast telemetry shadow runningMin fallback count") && ok;
    ok = expect_equal_u64(fastFallbackShadowCandidateCountCount,
                          fastFallbackShadowCandidateCountCountBefore + 1,
                          "fast telemetry shadow candidateCount fallback count") && ok;
    ok = expect_equal_u64(fastFallbackShadowCandidateValueCount,
                          fastFallbackShadowCandidateValueCountBefore + 1,
                          "fast telemetry shadow candidateValue fallback count") && ok;

    uint64_t locateExactCalls = 0;
    uint64_t locateFastCalls = 0;
    uint64_t locateSafeWorksetCalls = 0;
    uint64_t locateFastFallbacks = 0;
    getSimLocateModeCounts(locateExactCalls,
                           locateFastCalls,
                           locateSafeWorksetCalls,
                           locateFastFallbacks);
    const uint64_t locateExactCallsBefore = locateExactCalls;
    const uint64_t locateFastCallsBefore = locateFastCalls;
    const uint64_t locateSafeWorksetCallsBefore = locateSafeWorksetCalls;
    const uint64_t locateFastFallbacksBefore = locateFastFallbacks;
    recordSimLocateMode(SIM_LOCATE_CUDA_MODE_SAFE_WORKSET);
    uint64_t locateBatchCalls = 0;
    uint64_t locateBatchRequestCount = 0;
    uint64_t locateBatchSharedInputRequests = 0;
    uint64_t locateBatchSerialFallbackRequests = 0;
    uint64_t locateBatchLaunches = 0;
    getSimLocateBatchTelemetryStats(locateBatchCalls,
                                    locateBatchRequestCount,
                                    locateBatchSharedInputRequests,
                                    locateBatchSerialFallbackRequests,
                                    locateBatchLaunches);
    const uint64_t locateBatchCallsBefore = locateBatchCalls;
    const uint64_t locateBatchRequestsBefore = locateBatchRequestCount;
    const uint64_t locateBatchSharedInputRequestsBefore = locateBatchSharedInputRequests;
    const uint64_t locateBatchSerialFallbackRequestsBefore = locateBatchSerialFallbackRequests;
    const uint64_t locateBatchLaunchesBefore = locateBatchLaunches;
    SimLocateCudaBatchResult locateBatchTelemetry;
    locateBatchTelemetry.taskCount = 5;
    locateBatchTelemetry.launchCount = 2;
    locateBatchTelemetry.usedSharedInputBatchPath = true;
    locateBatchTelemetry.sharedInputRequestCount = 5;
    locateBatchTelemetry.serialFallbackRequestCount = 0;
    recordSimLocateBatchTelemetry(locateBatchTelemetry);
    locateBatchTelemetry = SimLocateCudaBatchResult();
    locateBatchTelemetry.taskCount = 3;
    locateBatchTelemetry.launchCount = 3;
    locateBatchTelemetry.usedSharedInputBatchPath = false;
    locateBatchTelemetry.sharedInputRequestCount = 0;
    locateBatchTelemetry.serialFallbackRequestCount = 3;
    recordSimLocateBatchTelemetry(locateBatchTelemetry);
    getSimLocateBatchTelemetryStats(locateBatchCalls,
                                    locateBatchRequestCount,
                                    locateBatchSharedInputRequests,
                                    locateBatchSerialFallbackRequests,
                                    locateBatchLaunches);
    ok = expect_equal_u64(locateBatchCalls,
                          locateBatchCallsBefore + 2,
                          "locate batch telemetry call count") && ok;
    ok = expect_equal_u64(locateBatchRequestCount,
                          locateBatchRequestsBefore + 8,
                          "locate batch telemetry request count") && ok;
    ok = expect_equal_u64(locateBatchSharedInputRequests,
                          locateBatchSharedInputRequestsBefore + 5,
                          "locate batch telemetry shared-input request count") && ok;
    ok = expect_equal_u64(locateBatchSerialFallbackRequests,
                          locateBatchSerialFallbackRequestsBefore + 3,
                          "locate batch telemetry serial fallback request count") && ok;
    ok = expect_equal_u64(locateBatchLaunches,
                          locateBatchLaunchesBefore + 5,
                          "locate batch telemetry launch count") && ok;

    uint64_t regionCalls = 0;
    uint64_t regionRequests = 0;
    uint64_t regionLaunches = 0;
    uint64_t regionBatchCalls = 0;
    uint64_t regionBatchRequests = 0;
    uint64_t regionSerialFallbackRequests = 0;
    getSimRegionScanTelemetryStats(regionCalls,
                                   regionRequests,
                                   regionLaunches,
                                   regionBatchCalls,
                                   regionBatchRequests,
                                   regionSerialFallbackRequests);
    const uint64_t regionCallsBefore = regionCalls;
    const uint64_t regionRequestsBefore = regionRequests;
    const uint64_t regionLaunchesBefore = regionLaunches;
    const uint64_t regionBatchCallsBefore = regionBatchCalls;
    const uint64_t regionBatchRequestsBefore = regionBatchRequests;
    const uint64_t regionSerialFallbackRequestsBefore = regionSerialFallbackRequests;
    recordSimRegionScanBackend(true, 4, 2);
    recordSimRegionScanBackend(false, 1, 1);
    getSimRegionScanTelemetryStats(regionCalls,
                                   regionRequests,
                                   regionLaunches,
                                   regionBatchCalls,
                                   regionBatchRequests,
                                   regionSerialFallbackRequests);
    ok = expect_equal_u64(regionCalls,
                          regionCallsBefore + 2,
                          "region telemetry call count") && ok;
    ok = expect_equal_u64(regionRequests,
                          regionRequestsBefore + 5,
                          "region telemetry request count") && ok;
    ok = expect_equal_u64(regionLaunches,
                          regionLaunchesBefore + 3,
                          "region telemetry launch count") && ok;
    ok = expect_equal_u64(regionBatchCalls,
                          regionBatchCallsBefore + 1,
                          "region telemetry batch call count") && ok;
    ok = expect_equal_u64(regionBatchRequests,
                          regionBatchRequestsBefore + 4,
                          "region telemetry batch request count") && ok;
    ok = expect_equal_u64(regionSerialFallbackRequests,
                          regionSerialFallbackRequestsBefore + 1,
                          "region telemetry serial fallback request count") && ok;
    getSimLocateModeCounts(locateExactCalls,
                           locateFastCalls,
                           locateSafeWorksetCalls,
                           locateFastFallbacks);
    ok = expect_equal_u64(locateExactCalls,
                          locateExactCallsBefore,
                          "safe_workset telemetry exact count unchanged") && ok;
    ok = expect_equal_u64(locateFastCalls,
                          locateFastCallsBefore,
                          "safe_workset telemetry fast count unchanged") && ok;
    ok = expect_equal_u64(locateSafeWorksetCalls,
                          locateSafeWorksetCallsBefore + 1,
                          "safe_workset telemetry count increments") && ok;
    ok = expect_equal_u64(locateFastFallbacks,
                          locateFastFallbacksBefore,
                          "safe_workset telemetry fast fallback unchanged") && ok;

    uint64_t safeWorksetPassCount = 0;
    uint64_t safeWorksetFallbackInvalidStoreCount = 0;
    uint64_t safeWorksetFallbackNoAffectedStartCount = 0;
    uint64_t safeWorksetFallbackNoWorksetCount = 0;
    uint64_t safeWorksetFallbackInvalidBandsCount = 0;
    uint64_t safeWorksetFallbackScanFailureCount = 0;
    uint64_t safeWorksetFallbackShadowMismatchCount = 0;
    getSimSafeWorksetStats(safeWorksetPassCount,
                           safeWorksetFallbackInvalidStoreCount,
                           safeWorksetFallbackNoAffectedStartCount,
                           safeWorksetFallbackNoWorksetCount,
                           safeWorksetFallbackInvalidBandsCount,
                           safeWorksetFallbackScanFailureCount,
                           safeWorksetFallbackShadowMismatchCount);
    const uint64_t safeWorksetPassCountBefore = safeWorksetPassCount;
    const uint64_t safeWorksetFallbackInvalidStoreCountBefore = safeWorksetFallbackInvalidStoreCount;
    const uint64_t safeWorksetFallbackNoAffectedStartCountBefore = safeWorksetFallbackNoAffectedStartCount;
    const uint64_t safeWorksetFallbackNoWorksetCountBefore = safeWorksetFallbackNoWorksetCount;
    const uint64_t safeWorksetFallbackInvalidBandsCountBefore = safeWorksetFallbackInvalidBandsCount;
    const uint64_t safeWorksetFallbackScanFailureCountBefore = safeWorksetFallbackScanFailureCount;
    const uint64_t safeWorksetFallbackShadowMismatchCountBefore = safeWorksetFallbackShadowMismatchCount;
    recordSimSafeWorksetPass();
    recordSimSafeWorksetFallbackReason(SIM_SAFE_WORKSET_FALLBACK_INVALID_STORE);
    recordSimSafeWorksetFallbackReason(SIM_SAFE_WORKSET_FALLBACK_NO_AFFECTED_START);
    recordSimSafeWorksetFallbackReason(SIM_SAFE_WORKSET_FALLBACK_NO_WORKSET);
    recordSimSafeWorksetFallbackReason(SIM_SAFE_WORKSET_FALLBACK_INVALID_BANDS);
    recordSimSafeWorksetFallbackReason(SIM_SAFE_WORKSET_FALLBACK_SCAN_FAILURE);
    recordSimSafeWorksetFallbackReason(SIM_SAFE_WORKSET_FALLBACK_SHADOW_MISMATCH);
    getSimSafeWorksetStats(safeWorksetPassCount,
                           safeWorksetFallbackInvalidStoreCount,
                           safeWorksetFallbackNoAffectedStartCount,
                           safeWorksetFallbackNoWorksetCount,
                           safeWorksetFallbackInvalidBandsCount,
                           safeWorksetFallbackScanFailureCount,
                           safeWorksetFallbackShadowMismatchCount);
    ok = expect_equal_u64(safeWorksetPassCount,
                          safeWorksetPassCountBefore + 1,
                          "safe_workset pass count increments") && ok;
    ok = expect_equal_u64(safeWorksetFallbackInvalidStoreCount,
                          safeWorksetFallbackInvalidStoreCountBefore + 1,
                          "safe_workset invalid-store fallback count") && ok;
    ok = expect_equal_u64(safeWorksetFallbackNoAffectedStartCount,
                          safeWorksetFallbackNoAffectedStartCountBefore + 1,
                          "safe_workset no-affected-start fallback count") && ok;
    ok = expect_equal_u64(safeWorksetFallbackNoWorksetCount,
                          safeWorksetFallbackNoWorksetCountBefore + 1,
                          "safe_workset no-workset fallback count") && ok;
    ok = expect_equal_u64(safeWorksetFallbackInvalidBandsCount,
                          safeWorksetFallbackInvalidBandsCountBefore + 1,
                          "safe_workset invalid-bands fallback count") && ok;
    ok = expect_equal_u64(safeWorksetFallbackScanFailureCount,
                          safeWorksetFallbackScanFailureCountBefore + 1,
                          "safe_workset scan-failure fallback count") && ok;
    ok = expect_equal_u64(safeWorksetFallbackShadowMismatchCount,
                          safeWorksetFallbackShadowMismatchCountBefore + 1,
                          "safe_workset shadow-mismatch fallback count") && ok;

    SimPathWorkset safeWorksetInput;
    safeWorksetInput.hasWorkset = true;
    safeWorksetInput.cellCount = 6;
    safeWorksetInput.bands.resize(2);
    safeWorksetInput.bands[0].rowStart = 1;
    safeWorksetInput.bands[0].rowEnd = 1;
    safeWorksetInput.bands[0].colStart = 10;
    safeWorksetInput.bands[0].colEnd = 12;
    safeWorksetInput.bands[1].rowStart = 2;
    safeWorksetInput.bands[1].rowEnd = 2;
    safeWorksetInput.bands[1].colStart = 11;
    safeWorksetInput.bands[1].colEnd = 13;
    const SimPathWorkset safeWorksetExecMerged =
        coarsenSimSafeWorksetForExecution(safeWorksetInput);
    ok = expect_equal_bool(safeWorksetExecMerged.hasWorkset, true, "safe_workset exec merged present") && ok;
    ok = expect_equal_size(safeWorksetExecMerged.bands.size(), 1, "safe_workset exec merged band count") && ok;
    ok = expect_equal_u64(safeWorksetExecMerged.cellCount, 8, "safe_workset exec merged cells") && ok;
    ok = expect_equal_long(safeWorksetExecMerged.bands[0].rowStart, 1, "safe_workset exec merged row start") && ok;
    ok = expect_equal_long(safeWorksetExecMerged.bands[0].rowEnd, 2, "safe_workset exec merged row end") && ok;
    ok = expect_equal_long(safeWorksetExecMerged.bands[0].colStart, 10, "safe_workset exec merged col start") && ok;
    ok = expect_equal_long(safeWorksetExecMerged.bands[0].colEnd, 13, "safe_workset exec merged col end") && ok;

    SimPathWorkset sparseSafeWorksetInput;
    sparseSafeWorksetInput.hasWorkset = true;
    sparseSafeWorksetInput.cellCount = 2;
    sparseSafeWorksetInput.bands.resize(2);
    sparseSafeWorksetInput.bands[0].rowStart = 1;
    sparseSafeWorksetInput.bands[0].rowEnd = 1;
    sparseSafeWorksetInput.bands[0].colStart = 1;
    sparseSafeWorksetInput.bands[0].colEnd = 1;
    sparseSafeWorksetInput.bands[1].rowStart = 2;
    sparseSafeWorksetInput.bands[1].rowEnd = 2;
    sparseSafeWorksetInput.bands[1].colStart = 10;
    sparseSafeWorksetInput.bands[1].colEnd = 10;
    const SimPathWorkset sparseSafeWorksetExec =
        coarsenSimSafeWorksetForExecution(sparseSafeWorksetInput);
    ok = expect_equal_size(sparseSafeWorksetExec.bands.size(), 2, "safe_workset sparse exec keeps bands") && ok;
    ok = expect_equal_u64(sparseSafeWorksetExec.cellCount, 2, "safe_workset sparse exec keeps cells") && ok;

    SimPathWorkset collapseSafeWorksetInput;
    collapseSafeWorksetInput.hasWorkset = true;
    collapseSafeWorksetInput.cellCount = 36;
    collapseSafeWorksetInput.bands.resize(9);
    for (size_t bandIndex = 0; bandIndex < collapseSafeWorksetInput.bands.size(); ++bandIndex)
    {
        SimUpdateBand &band = collapseSafeWorksetInput.bands[bandIndex];
        const long row = static_cast<long>(bandIndex) * 2 + 1;
        band.rowStart = row;
        band.rowEnd = row;
        band.colStart = 1;
        band.colEnd = 4;
    }
    const SimPathWorkset collapseSafeWorksetExec =
        coarsenSimSafeWorksetForExecution(collapseSafeWorksetInput);
    ok = expect_equal_size(collapseSafeWorksetExec.bands.size(), 1, "safe_workset global collapse band count") && ok;
    ok = expect_equal_u64(collapseSafeWorksetExec.cellCount, 68, "safe_workset global collapse cells") && ok;
    ok = expect_equal_long(collapseSafeWorksetExec.bands[0].rowStart, 1, "safe_workset global collapse row start") && ok;
    ok = expect_equal_long(collapseSafeWorksetExec.bands[0].rowEnd, 17, "safe_workset global collapse row end") && ok;

    SimPathWorkset denseSafeWorksetInput;
    denseSafeWorksetInput.hasWorkset = true;
    denseSafeWorksetInput.cellCount = 20;
    denseSafeWorksetInput.bands.resize(10);
    for (size_t bandIndex = 0; bandIndex < denseSafeWorksetInput.bands.size(); ++bandIndex)
    {
        SimUpdateBand &band = denseSafeWorksetInput.bands[bandIndex];
        band.rowStart = static_cast<long>(bandIndex) + 1;
        band.rowEnd = band.rowStart;
        band.colStart = static_cast<long>(bandIndex) * 3 + 1;
        band.colEnd = band.colStart + 1;
    }
    const SimPathWorkset denseSafeWorksetExec =
        coarsenSimSafeWorksetForExecution(denseSafeWorksetInput);
    ok = expect_equal_size(denseSafeWorksetExec.bands.size(), 5, "safe_workset dense exec reduces band count") && ok;
    ok = expect_equal_u64(denseSafeWorksetExec.cellCount, 50, "safe_workset dense exec merged cells") && ok;
    ok = expect_equal_long(denseSafeWorksetExec.bands[0].rowStart, 1, "safe_workset dense exec first row start") && ok;
    ok = expect_equal_long(denseSafeWorksetExec.bands[0].rowEnd, 2, "safe_workset dense exec first row end") && ok;
    ok = expect_equal_long(denseSafeWorksetExec.bands[0].colStart, 1, "safe_workset dense exec first col start") && ok;
    ok = expect_equal_long(denseSafeWorksetExec.bands[0].colEnd, 5, "safe_workset dense exec first col end") && ok;

    SimPathWorkset safeWindowInput;
    safeWindowInput.hasWorkset = true;
    safeWindowInput.cellCount = 36;
    safeWindowInput.bands.resize(9);
    for (size_t bandIndex = 0; bandIndex < safeWindowInput.bands.size(); ++bandIndex)
    {
        SimUpdateBand &band = safeWindowInput.bands[bandIndex];
        const long row = static_cast<long>(bandIndex) * 2 + 1;
        band.rowStart = row;
        band.rowEnd = row;
        band.colStart = 1;
        band.colEnd = 4;
    }
    const SimPathWorkset safeWindowExec =
        buildSimSafeWindowExecutionWorkset(safeWindowInput);
    ok = expect_equal_bool(safeWindowExec.hasWorkset, true, "safe_window exec present") && ok;
    ok = expect_equal_size(safeWindowExec.bands.size(), 1, "safe_window exec coarsens dense windows") && ok;
    ok = expect_equal_u64(safeWindowExec.cellCount, 68, "safe_window exec expands to execution-safe cells") && ok;
    ok = expect_equal_long(safeWindowExec.bands[0].rowStart, 1, "safe_window exec row start") && ok;
    ok = expect_equal_long(safeWindowExec.bands[0].rowEnd, 17, "safe_window exec row end") && ok;
    ok = expect_equal_long(safeWindowExec.bands[0].colStart, 1, "safe_window exec col start") && ok;
    ok = expect_equal_long(safeWindowExec.bands[0].colEnd, 4, "safe_window exec col end") && ok;

    std::vector<int> sparseWindowRowOffsets;
    sparseWindowRowOffsets.push_back(0);
    sparseWindowRowOffsets.push_back(0);
    sparseWindowRowOffsets.push_back(2);
    sparseWindowRowOffsets.push_back(4);
    sparseWindowRowOffsets.push_back(5);
    std::vector<SimScanCudaColumnInterval> sparseWindowIntervals;
    sparseWindowIntervals.push_back(SimScanCudaColumnInterval(10, 12));
    sparseWindowIntervals.push_back(SimScanCudaColumnInterval(20, 22));
    sparseWindowIntervals.push_back(SimScanCudaColumnInterval(10, 12));
    sparseWindowIntervals.push_back(SimScanCudaColumnInterval(20, 22));
    sparseWindowIntervals.push_back(SimScanCudaColumnInterval(10, 12));
    const std::vector<SimScanCudaSafeWindow> sparseWindows =
        buildSimSafeWindowsFromSparseRowIntervals(3,
                                                  sparseWindowRowOffsets,
                                                  sparseWindowIntervals);
    ok = expect_equal_size(sparseWindows.size(),
                           2,
                           "sparse safe_window builder keeps disjoint islands") && ok;
    if (sparseWindows.size() == 2)
    {
        ok = expect_equal_long(sparseWindows[0].rowStart,
                               1,
                               "sparse safe_window first row start") && ok;
        ok = expect_equal_long(sparseWindows[0].rowEnd,
                               3,
                               "sparse safe_window first row end") && ok;
        ok = expect_equal_long(sparseWindows[0].colStart,
                               10,
                               "sparse safe_window first col start") && ok;
        ok = expect_equal_long(sparseWindows[0].colEnd,
                               12,
                               "sparse safe_window first col end") && ok;
        ok = expect_equal_long(sparseWindows[1].rowStart,
                               1,
                               "sparse safe_window second row start") && ok;
        ok = expect_equal_long(sparseWindows[1].rowEnd,
                               2,
                               "sparse safe_window second row end") && ok;
        ok = expect_equal_long(sparseWindows[1].colStart,
                               20,
                               "sparse safe_window second col start") && ok;
        ok = expect_equal_long(sparseWindows[1].colEnd,
                               22,
                               "sparse safe_window second col end") && ok;
    }

    SimPathWorkset preferredSafeWindowWorkset;
    preferredSafeWindowWorkset.hasWorkset = true;
    preferredSafeWindowWorkset.cellCount = 12;
    preferredSafeWindowWorkset.bands.resize(2);
    preferredSafeWindowWorkset.bands[0].rowStart = 1;
    preferredSafeWindowWorkset.bands[0].rowEnd = 2;
    preferredSafeWindowWorkset.bands[0].colStart = 10;
    preferredSafeWindowWorkset.bands[0].colEnd = 12;
    preferredSafeWindowWorkset.bands[1].rowStart = 3;
    preferredSafeWindowWorkset.bands[1].rowEnd = 4;
    preferredSafeWindowWorkset.bands[1].colStart = 11;
    preferredSafeWindowWorkset.bands[1].colEnd = 13;
    SimPathWorkset preferredSafeWorksetExec;
    preferredSafeWorksetExec.hasWorkset = true;
    preferredSafeWorksetExec.cellCount = 20;
    preferredSafeWorksetExec.bands.resize(1);
    preferredSafeWorksetExec.bands[0].rowStart = 1;
    preferredSafeWorksetExec.bands[0].rowEnd = 4;
    preferredSafeWorksetExec.bands[0].colStart = 10;
    preferredSafeWorksetExec.bands[0].colEnd = 14;
    ok = expect_equal_bool(shouldPreferSimSafeWindowExecution(preferredSafeWindowWorkset,
                                                              2,
                                                              preferredSafeWorksetExec),
                           true,
                           "safe_window preferred when cells shrink") && ok;
    ok = expect_equal_bool(shouldPreferSimSafeWindowExecution(preferredSafeWindowWorkset,
                                                              1,
                                                              preferredSafeWindowWorkset,
                                                              2),
                           true,
                           "safe_window preferred when cells tie and affected starts shrink") && ok;
    ok = expect_equal_bool(shouldPreferSimSafeWindowExecution(preferredSafeWindowWorkset,
                                                              3,
                                                              preferredSafeWindowWorkset,
                                                              2),
                           false,
                           "safe_window not preferred when cells tie and affected starts grow") && ok;
    ok = expect_equal_bool(shouldPreferSimSafeWindowExecution(preferredSafeWindowWorkset,
                                                              2,
                                                              preferredSafeWindowWorkset,
                                                              2),
                           false,
                           "safe_window not preferred when cells and affected starts tie") && ok;
    ok = expect_equal_bool(shouldPreferSimSafeWindowExecution(preferredSafeWindowWorkset,
                                                              0,
                                                              preferredSafeWorksetExec),
                           false,
                           "safe_window requires affected starts") && ok;
    ok = expect_equal_bool(shouldPreferSimSafeWindowExecution(preferredSafeWorksetExec,
                                                              2,
                                                              preferredSafeWorksetExec),
                           false,
                           "safe_window requires smaller cell count") && ok;

    uint64_t safeWorksetAffectedStartCount = 0;
    uint64_t safeWorksetUniqueAffectedStartCount = 0;
    uint64_t safeWorksetInputBandCount = 0;
    uint64_t safeWorksetInputCellCount = 0;
    uint64_t safeWorksetExecBandCount = 0;
    uint64_t safeWorksetExecCellCount = 0;
    uint64_t safeWorksetCudaTaskCount = 0;
    uint64_t safeWorksetCudaLaunchCount = 0;
    uint64_t safeWorksetCudaTrueBatchRequestCount = getSimSafeWorksetCudaTrueBatchRequestCount();
    uint64_t safeWorksetReturnedStateCount = 0;
    uint64_t safeWorksetBuildNanoseconds = 0;
    uint64_t safeWorksetMergeNanoseconds = 0;
    uint64_t safeWorksetTotalNanoseconds = 0;
    uint64_t safeWindowCount = 0;
    uint64_t safeWindowAffectedStartCount = 0;
    uint64_t safeWindowCoordBytesD2H = 0;
    uint64_t safeWindowFallbackCount = 0;
    uint64_t safeWindowGpuNanoseconds = 0;
    uint64_t safeWindowD2hNanoseconds = 0;
    uint64_t safeWindowExecBandCount = 0;
    uint64_t safeWindowExecCellCount = 0;
    uint64_t safeWindowAttemptCount = 0;
    uint64_t safeWindowSkippedUnconvertibleCount = 0;
    uint64_t safeWindowSelectedWorksetCount = 0;
    uint64_t safeWindowAppliedCount = 0;
    uint64_t safeWindowGpuBuilderFallbackCount = 0;
    uint64_t safeWindowGpuBuilderPassCount = 0;
    uint64_t safeWindowExactFallbackCount = 0;
    uint64_t safeWindowExactFallbackNoUpdateRegionCount = 0;
    uint64_t safeWindowExactFallbackRefreshSuccessCount = 0;
    uint64_t safeWindowExactFallbackRefreshFailureCount = 0;
    uint64_t safeWindowExactFallbackBaseNoUpdateCount = 0;
    uint64_t safeWindowExactFallbackExpansionNoUpdateCount = 0;
    uint64_t safeWindowExactFallbackStopNoCrossCount = 0;
    uint64_t safeWindowExactFallbackStopBoundaryCount = 0;
    uint64_t safeWindowExactFallbackBaseCellCount = 0;
    uint64_t safeWindowExactFallbackExpansionCellCount = 0;
    uint64_t safeWindowExactFallbackLocateGpuNanoseconds = 0;
    uint64_t safeWindowStoreInvalidationCount = 0;
    uint64_t safeWindowFallbackSelectorErrorCount = 0;
    uint64_t safeWindowFallbackOverflowCount = 0;
    uint64_t safeWindowFallbackEmptySelectionCount = 0;
    uint64_t safeWindowPlanBandCount = 0;
    uint64_t safeWindowPlanCellCount = 0;
    uint64_t safeWindowPlanGpuNanoseconds = 0;
    uint64_t safeWindowPlanD2hNanoseconds = 0;
    uint64_t safeWindowPlanFallbackCount = 0;
    uint64_t safeWindowPlanBetterThanBuilderCount = 0;
    uint64_t safeWindowPlanWorseThanBuilderCount = 0;
    uint64_t safeWindowPlanEqualToBuilderCount = 0;
    uint64_t safeStoreRefreshAttemptCount = 0;
    uint64_t safeStoreRefreshSuccessCount = 0;
    uint64_t safeStoreRefreshFailureCount = 0;
    uint64_t safeStoreRefreshTrackedStartCount = 0;
    uint64_t safeStoreRefreshGpuNanoseconds = 0;
    uint64_t safeStoreRefreshD2hNanoseconds = 0;
    uint64_t safeStoreInvalidatedAfterExactFallbackCount = 0;
    uint64_t frontierInvalidateProposalEraseCount = 0;
    uint64_t frontierInvalidateStoreUpdateCount = 0;
    uint64_t frontierInvalidateReleaseOrErrorCount = 0;
    uint64_t frontierRebuildFromResidencyCount = 0;
    uint64_t frontierRebuildFromHostFinalCandidatesCount = 0;
    uint64_t safeWorksetBuilderCallsAfterSafeWindow =
        getSimSafeWorksetBuilderCallsAfterSafeWindow();
    uint64_t regionPackedRequestCount = getSimRegionPackedRequestCount();
    getSimSafeWorksetExecutionStats(safeWorksetAffectedStartCount,
                                    safeWorksetUniqueAffectedStartCount,
                                    safeWorksetInputBandCount,
                                    safeWorksetInputCellCount,
                                    safeWorksetExecBandCount,
                                    safeWorksetExecCellCount,
                                    safeWorksetCudaTaskCount,
                                    safeWorksetCudaLaunchCount,
                                    safeWorksetReturnedStateCount);
    getSimSafeWorksetTimingStats(safeWorksetBuildNanoseconds,
                                 safeWorksetMergeNanoseconds,
                                 safeWorksetTotalNanoseconds);
    const SimSafeWorksetMergeBreakdownStats safeWorksetMergeBreakdownBefore =
        getSimSafeWorksetMergeBreakdownStats();
    const SimSafeStoreMergeStructureShadowStats safeStoreMergeStructureShadowBefore =
        getSimSafeStoreMergeStructureShadowStats();
    const SimRegionDeferredCountValidateStats regionDeferredCountValidateBefore =
        getSimRegionDeferredCountValidateStats();
    getSimSafeWindowStats(safeWindowCount,
                          safeWindowAffectedStartCount,
                          safeWindowCoordBytesD2H,
                          safeWindowFallbackCount,
                          safeWindowGpuNanoseconds,
                          safeWindowD2hNanoseconds);
    getSimSafeWindowExecutionStats(safeWindowExecBandCount,
                                   safeWindowExecCellCount);
    getSimSafeWindowPathStats(safeWindowAttemptCount,
                              safeWindowSkippedUnconvertibleCount,
                              safeWindowSelectedWorksetCount,
                              safeWindowAppliedCount,
                              safeWindowGpuBuilderFallbackCount,
                              safeWindowGpuBuilderPassCount,
                              safeWindowExactFallbackCount,
                              safeWindowStoreInvalidationCount);
    getSimSafeWindowExactFallbackOutcomeStats(safeWindowExactFallbackNoUpdateRegionCount,
                                              safeWindowExactFallbackRefreshSuccessCount,
                                              safeWindowExactFallbackRefreshFailureCount);
    getSimSafeWindowExactFallbackPrecheckStats(safeWindowExactFallbackBaseNoUpdateCount,
                                               safeWindowExactFallbackExpansionNoUpdateCount,
                                               safeWindowExactFallbackStopNoCrossCount,
                                               safeWindowExactFallbackStopBoundaryCount,
                                               safeWindowExactFallbackBaseCellCount,
                                               safeWindowExactFallbackExpansionCellCount,
                                               safeWindowExactFallbackLocateGpuNanoseconds);
    getSimSafeWindowFallbackReasonStats(safeWindowFallbackSelectorErrorCount,
                                        safeWindowFallbackOverflowCount,
                                        safeWindowFallbackEmptySelectionCount);
    getSimSafeWindowPlanStats(safeWindowPlanBandCount,
                              safeWindowPlanCellCount,
                              safeWindowPlanGpuNanoseconds,
                              safeWindowPlanD2hNanoseconds,
                              safeWindowPlanFallbackCount);
    getSimSafeWindowPlanComparisonStats(safeWindowPlanBetterThanBuilderCount,
                                        safeWindowPlanWorseThanBuilderCount,
                                        safeWindowPlanEqualToBuilderCount);
    getSimSafeStoreRefreshStats(safeStoreRefreshAttemptCount,
                                safeStoreRefreshSuccessCount,
                                safeStoreRefreshFailureCount,
                                safeStoreRefreshTrackedStartCount,
                                safeStoreRefreshGpuNanoseconds,
                                safeStoreRefreshD2hNanoseconds,
                                safeStoreInvalidatedAfterExactFallbackCount);
    getSimFrontierCacheTransitionStats(frontierInvalidateProposalEraseCount,
                                       frontierInvalidateStoreUpdateCount,
                                       frontierInvalidateReleaseOrErrorCount,
                                       frontierRebuildFromResidencyCount,
                                       frontierRebuildFromHostFinalCandidatesCount);
    const uint64_t safeWorksetAffectedStartCountBefore = safeWorksetAffectedStartCount;
    const uint64_t safeWorksetUniqueAffectedStartCountBefore = safeWorksetUniqueAffectedStartCount;
    const uint64_t safeWorksetInputBandCountBefore = safeWorksetInputBandCount;
    const uint64_t safeWorksetInputCellCountBefore = safeWorksetInputCellCount;
    const uint64_t safeWorksetExecBandCountBefore = safeWorksetExecBandCount;
    const uint64_t safeWorksetExecCellCountBefore = safeWorksetExecCellCount;
    const uint64_t safeWorksetCudaTaskCountBefore = safeWorksetCudaTaskCount;
    const uint64_t safeWorksetCudaLaunchCountBefore = safeWorksetCudaLaunchCount;
    const uint64_t safeWorksetCudaTrueBatchRequestCountBefore = safeWorksetCudaTrueBatchRequestCount;
    const uint64_t safeWorksetReturnedStateCountBefore = safeWorksetReturnedStateCount;
    const uint64_t safeWorksetBuildNanosecondsBefore = safeWorksetBuildNanoseconds;
    const uint64_t safeWorksetMergeNanosecondsBefore = safeWorksetMergeNanoseconds;
    const uint64_t safeWorksetTotalNanosecondsBefore = safeWorksetTotalNanoseconds;
    const uint64_t safeWindowCountBefore = safeWindowCount;
    const uint64_t safeWindowAffectedStartCountBefore = safeWindowAffectedStartCount;
    const uint64_t safeWindowCoordBytesD2HBefore = safeWindowCoordBytesD2H;
    const uint64_t safeWindowFallbackCountBefore = safeWindowFallbackCount;
    const uint64_t safeWindowGpuNanosecondsBefore = safeWindowGpuNanoseconds;
    const uint64_t safeWindowD2hNanosecondsBefore = safeWindowD2hNanoseconds;
    const uint64_t safeWindowExecBandCountBefore = safeWindowExecBandCount;
    const uint64_t safeWindowExecCellCountBefore = safeWindowExecCellCount;
    const uint64_t safeWindowAttemptCountBefore = safeWindowAttemptCount;
    const uint64_t safeWindowSkippedUnconvertibleCountBefore = safeWindowSkippedUnconvertibleCount;
    const uint64_t safeWindowSelectedWorksetCountBefore = safeWindowSelectedWorksetCount;
    const uint64_t safeWindowAppliedCountBefore = safeWindowAppliedCount;
    const uint64_t safeWindowGpuBuilderFallbackCountBefore = safeWindowGpuBuilderFallbackCount;
    const uint64_t safeWindowGpuBuilderPassCountBefore = safeWindowGpuBuilderPassCount;
    const uint64_t safeWindowExactFallbackCountBefore = safeWindowExactFallbackCount;
    const uint64_t safeWindowExactFallbackNoUpdateRegionCountBefore =
        safeWindowExactFallbackNoUpdateRegionCount;
    const uint64_t safeWindowExactFallbackRefreshSuccessCountBefore =
        safeWindowExactFallbackRefreshSuccessCount;
    const uint64_t safeWindowExactFallbackRefreshFailureCountBefore =
        safeWindowExactFallbackRefreshFailureCount;
    const uint64_t safeWindowExactFallbackBaseNoUpdateCountBefore =
        safeWindowExactFallbackBaseNoUpdateCount;
    const uint64_t safeWindowExactFallbackExpansionNoUpdateCountBefore =
        safeWindowExactFallbackExpansionNoUpdateCount;
    const uint64_t safeWindowExactFallbackStopNoCrossCountBefore =
        safeWindowExactFallbackStopNoCrossCount;
    const uint64_t safeWindowExactFallbackStopBoundaryCountBefore =
        safeWindowExactFallbackStopBoundaryCount;
    const uint64_t safeWindowExactFallbackBaseCellCountBefore =
        safeWindowExactFallbackBaseCellCount;
    const uint64_t safeWindowExactFallbackExpansionCellCountBefore =
        safeWindowExactFallbackExpansionCellCount;
    const uint64_t safeWindowExactFallbackLocateGpuNanosecondsBefore =
        safeWindowExactFallbackLocateGpuNanoseconds;
    const uint64_t safeWindowStoreInvalidationCountBefore = safeWindowStoreInvalidationCount;
    const uint64_t safeWindowFallbackSelectorErrorCountBefore = safeWindowFallbackSelectorErrorCount;
    const uint64_t safeWindowFallbackOverflowCountBefore = safeWindowFallbackOverflowCount;
    const uint64_t safeWindowFallbackEmptySelectionCountBefore = safeWindowFallbackEmptySelectionCount;
    const uint64_t safeWindowPlanBandCountBefore = safeWindowPlanBandCount;
    const uint64_t safeWindowPlanCellCountBefore = safeWindowPlanCellCount;
    const uint64_t safeWindowPlanGpuNanosecondsBefore = safeWindowPlanGpuNanoseconds;
    const uint64_t safeWindowPlanD2hNanosecondsBefore = safeWindowPlanD2hNanoseconds;
    const uint64_t safeWindowPlanFallbackCountBefore = safeWindowPlanFallbackCount;
    const uint64_t safeWindowPlanBetterThanBuilderCountBefore = safeWindowPlanBetterThanBuilderCount;
    const uint64_t safeWindowPlanWorseThanBuilderCountBefore = safeWindowPlanWorseThanBuilderCount;
    const uint64_t safeWindowPlanEqualToBuilderCountBefore = safeWindowPlanEqualToBuilderCount;
    const uint64_t safeStoreRefreshAttemptCountBefore = safeStoreRefreshAttemptCount;
    const uint64_t safeStoreRefreshSuccessCountBefore = safeStoreRefreshSuccessCount;
    const uint64_t safeStoreRefreshFailureCountBefore = safeStoreRefreshFailureCount;
    const uint64_t safeStoreRefreshTrackedStartCountBefore = safeStoreRefreshTrackedStartCount;
    const uint64_t safeStoreRefreshGpuNanosecondsBefore = safeStoreRefreshGpuNanoseconds;
    const uint64_t safeStoreRefreshD2hNanosecondsBefore = safeStoreRefreshD2hNanoseconds;
    const uint64_t safeStoreInvalidatedAfterExactFallbackCountBefore =
        safeStoreInvalidatedAfterExactFallbackCount;
    const uint64_t frontierInvalidateProposalEraseCountBefore =
        frontierInvalidateProposalEraseCount;
    const uint64_t frontierInvalidateStoreUpdateCountBefore =
        frontierInvalidateStoreUpdateCount;
    const uint64_t frontierInvalidateReleaseOrErrorCountBefore =
        frontierInvalidateReleaseOrErrorCount;
    const uint64_t frontierRebuildFromResidencyCountBefore =
        frontierRebuildFromResidencyCount;
    const uint64_t frontierRebuildFromHostFinalCandidatesCountBefore =
        frontierRebuildFromHostFinalCandidatesCount;
    const uint64_t safeWorksetBuilderCallsAfterSafeWindowBefore =
        safeWorksetBuilderCallsAfterSafeWindow;
    const uint64_t regionPackedRequestCountBefore = regionPackedRequestCount;
    recordSimSafeWorksetGeometry(3, safeWorksetInput, safeWorksetExecMerged);
    recordSimSafeWorksetBuild(2, 11);
    recordSimSafeWorksetCudaBatch(5, 2);
    recordSimSafeWorksetCudaTrueBatch(7);
    recordSimSafeWorksetMerge(4, 17);
    SimSafeWorksetMergeBreakdownStats safeWorksetMergeBreakdownDelta;
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_MATERIALIZE_NANOSECONDS, 3);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_CANDIDATE_ERASE_NANOSECONDS, 5);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_UPSERT_NANOSECONDS, 7);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_CANDIDATE_APPLY_NANOSECONDS, 11);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_PRUNE_NANOSECONDS, 13);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_UPLOAD_NANOSECONDS, 17);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_UNIQUE_START_KEY_COUNT, 19);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_DUPLICATE_STATE_COUNT, 23);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_CANDIDATE_UPDATE_COUNT, 29);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_UPDATE_COUNT, 31);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_RESIDENCY_UPDATE_COUNT, 37);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_ERASE_NANOSECONDS, 41);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_UPSERT_LOOP_NANOSECONDS, 43);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_AFFECTED_START_KEY_COUNT, 47);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_SIZE_BEFORE_COUNT, 53);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_SIZE_AFTER_ERASE_COUNT, 59);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_SIZE_AFTER_UPSERT_COUNT, 61);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_SAFE_STORE_SIZE_AFTER_PRUNE_COUNT, 67);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_PRUNE_SCANNED_STATE_COUNT, 71);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_PRUNE_REMOVED_STATE_COUNT, 73);
    safeWorksetMergeBreakdownDelta.add(SIM_SAFE_WORKSET_MERGE_PRUNE_KEPT_STATE_COUNT, 79);
    recordSimSafeWorksetMergeBreakdown(safeWorksetMergeBreakdownDelta);
    SimSafeStoreMergeStructureShadowStats safeStoreMergeStructureShadowDelta;
    safeStoreMergeStructureShadowDelta.calls = 2;
    safeStoreMergeStructureShadowDelta.nanoseconds = 3;
    safeStoreMergeStructureShadowDelta.digestMismatches = 5;
    safeStoreMergeStructureShadowDelta.sizeMismatches = 7;
    safeStoreMergeStructureShadowDelta.candidateMismatches = 11;
    safeStoreMergeStructureShadowDelta.orderMismatches = 13;
    safeStoreMergeStructureShadowDelta.estCurrentScannedStates = 13;
    safeStoreMergeStructureShadowDelta.estCompactScannedStates = 17;
    safeStoreMergeStructureShadowDelta.estSavedScans = 19;
    safeStoreMergeStructureShadowDelta.pruneScannedStates = 23;
    safeStoreMergeStructureShadowDelta.pruneRemovedStates = 29;
    recordSimSafeStoreMergeStructureShadow(safeStoreMergeStructureShadowDelta);
    SimRegionDeferredCountValidateStats regionDeferredCountValidateDelta;
    regionDeferredCountValidateDelta.calls = 3;
    regionDeferredCountValidateDelta.nanoseconds = 5;
    regionDeferredCountValidateDelta.eventMismatches = 7;
    regionDeferredCountValidateDelta.runMismatches = 11;
    regionDeferredCountValidateDelta.candidateMismatches = 13;
    regionDeferredCountValidateDelta.totalMismatches = 17;
    regionDeferredCountValidateDelta.fallbacks = 19;
    regionDeferredCountValidateDelta.scalarCopies = 23;
    regionDeferredCountValidateDelta.snapshotCopies = 29;
    recordSimRegionDeferredCountValidate(regionDeferredCountValidateDelta);
    recordSimSafeWorksetTotalNanoseconds(29);
    recordSimSafeWindowExecGeometry(safeWindowExec);
    recordSimSafeWindowAttempt();
    recordSimSafeWindowSkippedUnconvertible();
    recordSimSafeWindowSelectedWorkset();
    recordSimSafeWindowApplied();
    recordSimSafeWindowGpuBuilderFallback();
    recordSimSafeWindowGpuBuilderPass();
    recordSimSafeWindowExactFallback();
    recordSimSafeWindowExactFallbackNoUpdateRegion();
    recordSimSafeWindowExactFallbackRefreshSuccess();
    recordSimSafeWindowExactFallbackRefreshFailure();
    recordSimSafeWindowExactFallbackBaseNoUpdate();
    recordSimSafeWindowExactFallbackExpansionNoUpdate();
    recordSimSafeWindowExactFallbackStopNoCross();
    recordSimSafeWindowExactFallbackStopBoundary();
    recordSimSafeWindowExactFallbackBaseCells(41);
    recordSimSafeWindowExactFallbackExpansionCells(17);
    recordSimSafeWindowExactFallbackLocateGpuNanoseconds(29);
    recordSimSafeWindowStoreInvalidation();
    recordSimSafeWindowExecution(3, 5, 64, 19, 23);
    recordSimSafeWindowFallbackReason(SIM_SAFE_WINDOW_FALLBACK_SELECTOR_ERROR);
    recordSimSafeWindowFallbackReason(SIM_SAFE_WINDOW_FALLBACK_OVERFLOW);
    recordSimSafeWindowFallbackReason(SIM_SAFE_WINDOW_FALLBACK_EMPTY_SELECTION);
    recordSimSafeWindowFallback();
    recordSimSafeWindowPlan(safeWindowExec, 31, 37);
    recordSimSafeWindowPlanFallback();
    recordSimSafeWindowPlanComparison(SIM_SAFE_WINDOW_PLAN_COMPARISON_BETTER);
    recordSimSafeWindowPlanComparison(SIM_SAFE_WINDOW_PLAN_COMPARISON_WORSE);
    recordSimSafeWindowPlanComparison(SIM_SAFE_WINDOW_PLAN_COMPARISON_EQUAL);
    recordSimSafeStoreRefreshAttempt(5);
    recordSimSafeStoreRefreshSuccess(19, 23);
    recordSimSafeStoreRefreshFailure();
    recordSimSafeStoreInvalidatedAfterExactFallback();
    recordSimFrontierCacheInvalidateProposalErase();
    recordSimFrontierCacheInvalidateStoreUpdate();
    recordSimFrontierCacheInvalidateReleaseOrError();
    recordSimFrontierCacheRebuildFromResidency();
    recordSimFrontierCacheRebuildFromHostFinalCandidates();
    recordSimSafeWorksetBuilderCallAfterSafeWindow();
    recordSimRegionPackedRequests(11);
    safeWorksetCudaTrueBatchRequestCount = getSimSafeWorksetCudaTrueBatchRequestCount();
    safeWorksetBuilderCallsAfterSafeWindow =
        getSimSafeWorksetBuilderCallsAfterSafeWindow();
    regionPackedRequestCount = getSimRegionPackedRequestCount();
    getSimSafeWorksetExecutionStats(safeWorksetAffectedStartCount,
                                    safeWorksetUniqueAffectedStartCount,
                                    safeWorksetInputBandCount,
                                    safeWorksetInputCellCount,
                                    safeWorksetExecBandCount,
                                    safeWorksetExecCellCount,
                                    safeWorksetCudaTaskCount,
                                    safeWorksetCudaLaunchCount,
                                    safeWorksetReturnedStateCount);
    getSimSafeWorksetTimingStats(safeWorksetBuildNanoseconds,
                                 safeWorksetMergeNanoseconds,
                                 safeWorksetTotalNanoseconds);
    const SimSafeWorksetMergeBreakdownStats safeWorksetMergeBreakdownAfter =
        getSimSafeWorksetMergeBreakdownStats();
    const SimSafeStoreMergeStructureShadowStats safeStoreMergeStructureShadowAfter =
        getSimSafeStoreMergeStructureShadowStats();
    const SimRegionDeferredCountValidateStats regionDeferredCountValidateAfter =
        getSimRegionDeferredCountValidateStats();
    getSimSafeWindowStats(safeWindowCount,
                          safeWindowAffectedStartCount,
                          safeWindowCoordBytesD2H,
                          safeWindowFallbackCount,
                          safeWindowGpuNanoseconds,
                          safeWindowD2hNanoseconds);
    getSimSafeWindowExecutionStats(safeWindowExecBandCount,
                                   safeWindowExecCellCount);
    getSimSafeWindowPathStats(safeWindowAttemptCount,
                              safeWindowSkippedUnconvertibleCount,
                              safeWindowSelectedWorksetCount,
                              safeWindowAppliedCount,
                              safeWindowGpuBuilderFallbackCount,
                              safeWindowGpuBuilderPassCount,
                              safeWindowExactFallbackCount,
                              safeWindowStoreInvalidationCount);
    getSimSafeWindowExactFallbackOutcomeStats(safeWindowExactFallbackNoUpdateRegionCount,
                                              safeWindowExactFallbackRefreshSuccessCount,
                                              safeWindowExactFallbackRefreshFailureCount);
    getSimSafeWindowExactFallbackPrecheckStats(safeWindowExactFallbackBaseNoUpdateCount,
                                               safeWindowExactFallbackExpansionNoUpdateCount,
                                               safeWindowExactFallbackStopNoCrossCount,
                                               safeWindowExactFallbackStopBoundaryCount,
                                               safeWindowExactFallbackBaseCellCount,
                                               safeWindowExactFallbackExpansionCellCount,
                                               safeWindowExactFallbackLocateGpuNanoseconds);
    getSimSafeWindowFallbackReasonStats(safeWindowFallbackSelectorErrorCount,
                                        safeWindowFallbackOverflowCount,
                                        safeWindowFallbackEmptySelectionCount);
    getSimSafeWindowPlanStats(safeWindowPlanBandCount,
                              safeWindowPlanCellCount,
                              safeWindowPlanGpuNanoseconds,
                              safeWindowPlanD2hNanoseconds,
                              safeWindowPlanFallbackCount);
    getSimSafeWindowPlanComparisonStats(safeWindowPlanBetterThanBuilderCount,
                                        safeWindowPlanWorseThanBuilderCount,
                                        safeWindowPlanEqualToBuilderCount);
    getSimSafeStoreRefreshStats(safeStoreRefreshAttemptCount,
                                safeStoreRefreshSuccessCount,
                                safeStoreRefreshFailureCount,
                                safeStoreRefreshTrackedStartCount,
                                safeStoreRefreshGpuNanoseconds,
                                safeStoreRefreshD2hNanoseconds,
                                safeStoreInvalidatedAfterExactFallbackCount);
    getSimFrontierCacheTransitionStats(frontierInvalidateProposalEraseCount,
                                       frontierInvalidateStoreUpdateCount,
                                       frontierInvalidateReleaseOrErrorCount,
                                       frontierRebuildFromResidencyCount,
                                       frontierRebuildFromHostFinalCandidatesCount);
    ok = expect_equal_u64(safeWorksetAffectedStartCount,
                          safeWorksetAffectedStartCountBefore + 3,
                          "safe_workset affected-start count increments") && ok;
    ok = expect_equal_u64(safeWorksetUniqueAffectedStartCount,
                          safeWorksetUniqueAffectedStartCountBefore + 2,
                          "safe_workset unique affected-start count increments") && ok;
    ok = expect_equal_u64(safeWorksetInputBandCount,
                          safeWorksetInputBandCountBefore + safeWorksetInput.bands.size(),
                          "safe_workset input-band count increments") && ok;
    ok = expect_equal_u64(safeWorksetInputCellCount,
                          safeWorksetInputCellCountBefore + safeWorksetInput.cellCount,
                          "safe_workset input-cell count increments") && ok;
    ok = expect_equal_u64(safeWorksetExecBandCount,
                          safeWorksetExecBandCountBefore + safeWorksetExecMerged.bands.size(),
                          "safe_workset exec-band count increments") && ok;
    ok = expect_equal_u64(safeWorksetExecCellCount,
                          safeWorksetExecCellCountBefore + safeWorksetExecMerged.cellCount,
                          "safe_workset exec-cell count increments") && ok;
    ok = expect_equal_u64(safeWorksetCudaTaskCount,
                          safeWorksetCudaTaskCountBefore + 5,
                          "safe_workset cuda-task count increments") && ok;
    ok = expect_equal_u64(safeWorksetCudaLaunchCount,
                          safeWorksetCudaLaunchCountBefore + 2,
                          "safe_workset cuda-launch count increments") && ok;
    ok = expect_equal_u64(safeWorksetCudaTrueBatchRequestCount,
                          safeWorksetCudaTrueBatchRequestCountBefore + 7,
                          "safe_workset cuda true-batch request count increments") && ok;
    ok = expect_equal_u64(safeWorksetReturnedStateCount,
                          safeWorksetReturnedStateCountBefore + 4,
                          "safe_workset returned-state count increments") && ok;
    ok = expect_equal_u64(safeWorksetBuildNanoseconds,
                          safeWorksetBuildNanosecondsBefore + 11,
                          "safe_workset build timing increments") && ok;
    ok = expect_equal_u64(safeWorksetMergeNanoseconds,
                          safeWorksetMergeNanosecondsBefore + 17,
                          "safe_workset merge timing increments") && ok;
    ok = expect_equal_u64(safeWorksetTotalNanoseconds,
                          safeWorksetTotalNanosecondsBefore + 29,
                          "safe_workset total timing increments") && ok;
    for(size_t fieldIndex = 0;
        fieldIndex < SIM_SAFE_WORKSET_MERGE_BREAKDOWN_FIELD_COUNT;
        ++fieldIndex)
    {
      const SimSafeWorksetMergeBreakdownField field =
          static_cast<SimSafeWorksetMergeBreakdownField>(fieldIndex);
      ok = expect_equal_u64(safeWorksetMergeBreakdownAfter.get(field),
                            safeWorksetMergeBreakdownBefore.get(field) +
                                safeWorksetMergeBreakdownDelta.get(field),
                            "safe_workset merge breakdown increments") && ok;
    }
    ok = expect_equal_u64(safeStoreMergeStructureShadowAfter.calls,
                          safeStoreMergeStructureShadowBefore.calls + 2,
                          "safe-store merge structure shadow calls increment") && ok;
    ok = expect_equal_u64(safeStoreMergeStructureShadowAfter.nanoseconds,
                          safeStoreMergeStructureShadowBefore.nanoseconds + 3,
                          "safe-store merge structure shadow timing increments") && ok;
    ok = expect_equal_u64(safeStoreMergeStructureShadowAfter.digestMismatches,
                          safeStoreMergeStructureShadowBefore.digestMismatches + 5,
                          "safe-store merge structure shadow digest mismatches increment") && ok;
    ok = expect_equal_u64(safeStoreMergeStructureShadowAfter.sizeMismatches,
                          safeStoreMergeStructureShadowBefore.sizeMismatches + 7,
                          "safe-store merge structure shadow size mismatches increment") && ok;
    ok = expect_equal_u64(safeStoreMergeStructureShadowAfter.candidateMismatches,
                          safeStoreMergeStructureShadowBefore.candidateMismatches + 11,
                          "safe-store merge structure shadow candidate mismatches increment") && ok;
    ok = expect_equal_u64(safeStoreMergeStructureShadowAfter.orderMismatches,
                          safeStoreMergeStructureShadowBefore.orderMismatches + 13,
                          "safe-store merge structure shadow order mismatches increment") && ok;
    ok = expect_equal_u64(safeStoreMergeStructureShadowAfter.estCurrentScannedStates,
                          safeStoreMergeStructureShadowBefore.estCurrentScannedStates + 13,
                          "safe-store merge structure shadow current scan estimate increments") && ok;
    ok = expect_equal_u64(safeStoreMergeStructureShadowAfter.estCompactScannedStates,
                          safeStoreMergeStructureShadowBefore.estCompactScannedStates + 17,
                          "safe-store merge structure shadow compact scan estimate increments") && ok;
    ok = expect_equal_u64(safeStoreMergeStructureShadowAfter.estSavedScans,
                          safeStoreMergeStructureShadowBefore.estSavedScans + 19,
                          "safe-store merge structure shadow saved scan estimate increments") && ok;
    ok = expect_equal_u64(safeStoreMergeStructureShadowAfter.pruneScannedStates,
                          safeStoreMergeStructureShadowBefore.pruneScannedStates + 23,
                          "safe-store merge structure shadow prune scanned states increment") && ok;
    ok = expect_equal_u64(safeStoreMergeStructureShadowAfter.pruneRemovedStates,
                          safeStoreMergeStructureShadowBefore.pruneRemovedStates + 29,
                          "safe-store merge structure shadow prune removed states increment") && ok;
    ok = expect_equal_u64(regionDeferredCountValidateAfter.calls,
                          regionDeferredCountValidateBefore.calls + 3,
                          "region deferred-count validation calls increment") && ok;
    ok = expect_equal_u64(regionDeferredCountValidateAfter.nanoseconds,
                          regionDeferredCountValidateBefore.nanoseconds + 5,
                          "region deferred-count validation timing increments") && ok;
    ok = expect_equal_u64(regionDeferredCountValidateAfter.eventMismatches,
                          regionDeferredCountValidateBefore.eventMismatches + 7,
                          "region deferred-count validation event mismatches increment") && ok;
    ok = expect_equal_u64(regionDeferredCountValidateAfter.runMismatches,
                          regionDeferredCountValidateBefore.runMismatches + 11,
                          "region deferred-count validation run mismatches increment") && ok;
    ok = expect_equal_u64(regionDeferredCountValidateAfter.candidateMismatches,
                          regionDeferredCountValidateBefore.candidateMismatches + 13,
                          "region deferred-count validation candidate mismatches increment") && ok;
    ok = expect_equal_u64(regionDeferredCountValidateAfter.totalMismatches,
                          regionDeferredCountValidateBefore.totalMismatches + 17,
                          "region deferred-count validation total mismatches increment") && ok;
    ok = expect_equal_u64(regionDeferredCountValidateAfter.fallbacks,
                          regionDeferredCountValidateBefore.fallbacks + 19,
                          "region deferred-count validation fallback increments") && ok;
    ok = expect_equal_u64(regionDeferredCountValidateAfter.scalarCopies,
                          regionDeferredCountValidateBefore.scalarCopies + 23,
                          "region deferred-count validation scalar copy increments") && ok;
    ok = expect_equal_u64(regionDeferredCountValidateAfter.snapshotCopies,
                          regionDeferredCountValidateBefore.snapshotCopies + 29,
                          "region deferred-count validation snapshot copy increments") && ok;
    ok = expect_equal_u64(safeWindowCount,
                          safeWindowCountBefore + 3,
                          "safe window count increments") && ok;
    ok = expect_equal_u64(safeWindowAffectedStartCount,
                          safeWindowAffectedStartCountBefore + 5,
                          "safe window affected-start count increments") && ok;
    ok = expect_equal_u64(safeWindowCoordBytesD2H,
                          safeWindowCoordBytesD2HBefore + 64,
                          "safe window d2h bytes increment") && ok;
    ok = expect_equal_u64(safeWindowFallbackCount,
                          safeWindowFallbackCountBefore + 4,
                          "safe window fallback count increments") && ok;
    ok = expect_equal_u64(safeWindowGpuNanoseconds,
                          safeWindowGpuNanosecondsBefore + 19,
                          "safe window gpu timing increments") && ok;
    ok = expect_equal_u64(safeWindowD2hNanoseconds,
                          safeWindowD2hNanosecondsBefore + 23,
                          "safe window d2h timing increments") && ok;
    ok = expect_equal_u64(safeWindowExecBandCount,
                          safeWindowExecBandCountBefore + safeWindowExec.bands.size(),
                          "safe window exec band count increments") && ok;
    ok = expect_equal_u64(safeWindowExecCellCount,
                          safeWindowExecCellCountBefore + safeWindowExec.cellCount,
                          "safe window exec cell count increments") && ok;
    ok = expect_equal_u64(safeWindowAttemptCount,
                          safeWindowAttemptCountBefore + 1,
                          "safe window attempt count increments") && ok;
    ok = expect_equal_u64(safeWindowSkippedUnconvertibleCount,
                          safeWindowSkippedUnconvertibleCountBefore + 1,
                          "safe window skipped-unconvertible count increments") && ok;
    ok = expect_equal_u64(safeWindowSelectedWorksetCount,
                          safeWindowSelectedWorksetCountBefore + 1,
                          "safe window selected-workset count increments") && ok;
    ok = expect_equal_u64(safeWindowAppliedCount,
                          safeWindowAppliedCountBefore + 1,
                          "safe window applied count increments") && ok;
    ok = expect_equal_u64(safeWindowGpuBuilderFallbackCount,
                          safeWindowGpuBuilderFallbackCountBefore + 1,
                          "safe window gpu-builder fallback count increments") && ok;
    ok = expect_equal_u64(safeWindowGpuBuilderPassCount,
                          safeWindowGpuBuilderPassCountBefore + 1,
                          "safe window gpu-builder pass count increments") && ok;
    ok = expect_equal_u64(safeWindowExactFallbackCount,
                          safeWindowExactFallbackCountBefore + 1,
                          "safe window exact fallback count increments") && ok;
    ok = expect_equal_u64(safeWindowExactFallbackNoUpdateRegionCount,
                          safeWindowExactFallbackNoUpdateRegionCountBefore + 1,
                          "safe window exact fallback no-update-region count increments") && ok;
    ok = expect_equal_u64(safeWindowExactFallbackRefreshSuccessCount,
                          safeWindowExactFallbackRefreshSuccessCountBefore + 1,
                          "safe window exact fallback refresh-success count increments") && ok;
    ok = expect_equal_u64(safeWindowExactFallbackRefreshFailureCount,
                          safeWindowExactFallbackRefreshFailureCountBefore + 1,
                          "safe window exact fallback refresh-failure count increments") && ok;
    ok = expect_equal_u64(safeWindowExactFallbackBaseNoUpdateCount,
                          safeWindowExactFallbackBaseNoUpdateCountBefore + 1,
                          "safe window exact fallback base-no-update count increments") && ok;
    ok = expect_equal_u64(safeWindowExactFallbackExpansionNoUpdateCount,
                          safeWindowExactFallbackExpansionNoUpdateCountBefore + 1,
                          "safe window exact fallback expansion-no-update count increments") && ok;
    ok = expect_equal_u64(safeWindowExactFallbackStopNoCrossCount,
                          safeWindowExactFallbackStopNoCrossCountBefore + 1,
                          "safe window exact fallback stop-no-cross count increments") && ok;
    ok = expect_equal_u64(safeWindowExactFallbackStopBoundaryCount,
                          safeWindowExactFallbackStopBoundaryCountBefore + 1,
                          "safe window exact fallback stop-boundary count increments") && ok;
    ok = expect_equal_u64(safeWindowExactFallbackBaseCellCount,
                          safeWindowExactFallbackBaseCellCountBefore + 41,
                          "safe window exact fallback base-cell count increments") && ok;
    ok = expect_equal_u64(safeWindowExactFallbackExpansionCellCount,
                          safeWindowExactFallbackExpansionCellCountBefore + 17,
                          "safe window exact fallback expansion-cell count increments") && ok;
    ok = expect_equal_u64(safeWindowExactFallbackLocateGpuNanoseconds,
                          safeWindowExactFallbackLocateGpuNanosecondsBefore + 29,
                          "safe window exact fallback locate gpu timing increments") && ok;
    ok = expect_equal_u64(safeWindowStoreInvalidationCount,
                          safeWindowStoreInvalidationCountBefore + 1,
                          "safe window store invalidation count increments") && ok;
    ok = expect_equal_u64(safeWindowFallbackSelectorErrorCount,
                          safeWindowFallbackSelectorErrorCountBefore + 1,
                          "safe window selector-error fallback count increments") && ok;
    ok = expect_equal_u64(safeWindowFallbackOverflowCount,
                          safeWindowFallbackOverflowCountBefore + 1,
                          "safe window overflow fallback count increments") && ok;
    ok = expect_equal_u64(safeWindowFallbackEmptySelectionCount,
                          safeWindowFallbackEmptySelectionCountBefore + 1,
                          "safe window empty-selection fallback count increments") && ok;
    ok = expect_equal_u64(safeWindowPlanBandCount,
                          safeWindowPlanBandCountBefore + safeWindowExec.bands.size(),
                          "safe window plan band count increments") && ok;
    ok = expect_equal_u64(safeWindowPlanCellCount,
                          safeWindowPlanCellCountBefore + safeWindowExec.cellCount,
                          "safe window plan cell count increments") && ok;
    ok = expect_equal_u64(safeWindowPlanGpuNanoseconds,
                          safeWindowPlanGpuNanosecondsBefore + 31,
                          "safe window plan gpu timing increments") && ok;
    ok = expect_equal_u64(safeWindowPlanD2hNanoseconds,
                          safeWindowPlanD2hNanosecondsBefore + 37,
                          "safe window plan d2h timing increments") && ok;
    ok = expect_equal_u64(safeWindowPlanFallbackCount,
                          safeWindowPlanFallbackCountBefore + 1,
                          "safe window plan fallback count increments") && ok;
    ok = expect_equal_u64(safeWindowPlanBetterThanBuilderCount,
                          safeWindowPlanBetterThanBuilderCountBefore + 1,
                          "safe window plan better-than-builder count increments") && ok;
    ok = expect_equal_u64(safeWindowPlanWorseThanBuilderCount,
                          safeWindowPlanWorseThanBuilderCountBefore + 1,
                          "safe window plan worse-than-builder count increments") && ok;
    ok = expect_equal_u64(safeWindowPlanEqualToBuilderCount,
                          safeWindowPlanEqualToBuilderCountBefore + 1,
                          "safe window plan equal-to-builder count increments") && ok;
    ok = expect_equal_u64(safeStoreRefreshAttemptCount,
                          safeStoreRefreshAttemptCountBefore + 1,
                          "safe store refresh attempt count increments") && ok;
    ok = expect_equal_u64(safeStoreRefreshSuccessCount,
                          safeStoreRefreshSuccessCountBefore + 1,
                          "safe store refresh success count increments") && ok;
    ok = expect_equal_u64(safeStoreRefreshFailureCount,
                          safeStoreRefreshFailureCountBefore + 1,
                          "safe store refresh failure count increments") && ok;
    ok = expect_equal_u64(safeStoreRefreshTrackedStartCount,
                          safeStoreRefreshTrackedStartCountBefore + 5,
                          "safe store refresh tracked-start count increments") && ok;
    ok = expect_equal_u64(safeStoreRefreshGpuNanoseconds,
                          safeStoreRefreshGpuNanosecondsBefore + 19,
                          "safe store refresh gpu timing increments") && ok;
    ok = expect_equal_u64(safeStoreRefreshD2hNanoseconds,
                          safeStoreRefreshD2hNanosecondsBefore + 23,
                          "safe store refresh d2h timing increments") && ok;
    ok = expect_equal_u64(safeStoreInvalidatedAfterExactFallbackCount,
                          safeStoreInvalidatedAfterExactFallbackCountBefore + 1,
                          "safe store invalidated-after-fallback count increments") && ok;
    ok = expect_equal_u64(frontierInvalidateProposalEraseCount,
                          frontierInvalidateProposalEraseCountBefore + 1,
                          "frontier invalidate proposal-erase count increments") && ok;
    ok = expect_equal_u64(frontierInvalidateStoreUpdateCount,
                          frontierInvalidateStoreUpdateCountBefore + 1,
                          "frontier invalidate store-update count increments") && ok;
    ok = expect_equal_u64(frontierInvalidateReleaseOrErrorCount,
                          frontierInvalidateReleaseOrErrorCountBefore + 1,
                          "frontier invalidate release-or-error count increments") && ok;
    ok = expect_equal_u64(frontierRebuildFromResidencyCount,
                          frontierRebuildFromResidencyCountBefore + 1,
                          "frontier rebuild-from-residency count increments") && ok;
    ok = expect_equal_u64(frontierRebuildFromHostFinalCandidatesCount,
                          frontierRebuildFromHostFinalCandidatesCountBefore + 1,
                          "frontier rebuild-from-host-final-candidates count increments") && ok;
    ok = expect_equal_u64(safeWorksetBuilderCallsAfterSafeWindow,
                          safeWorksetBuilderCallsAfterSafeWindowBefore + 1,
                          "safe workset builder-after-safe-window count increments") && ok;
    ok = expect_equal_u64(regionPackedRequestCount,
                          regionPackedRequestCountBefore + 11,
                          "region packed request count increments") && ok;

    const SimInitialContextApplyBreakdownStats contextApplyBreakdownBefore =
        getSimInitialContextApplyBreakdownStats();
    SimInitialContextApplyBreakdownStats contextApplyBreakdownDelta;
    contextApplyBreakdownDelta.add(SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_NANOSECONDS,17);
    contextApplyBreakdownDelta.add(SIM_INITIAL_CONTEXT_APPLY_FLOOR_NANOSECONDS,19);
    contextApplyBreakdownDelta.add(SIM_INITIAL_CONTEXT_APPLY_FRONTIER_NANOSECONDS,23);
    contextApplyBreakdownDelta.add(SIM_INITIAL_CONTEXT_APPLY_SAFE_STORE_HANDOFF_NANOSECONDS,29);
    contextApplyBreakdownDelta.add(SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_ERASE_NANOSECONDS,31);
    contextApplyBreakdownDelta.add(SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_INSERT_NANOSECONDS,37);
    contextApplyBreakdownDelta.add(SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_SORT_NANOSECONDS,41);
    contextApplyBreakdownDelta.add(SIM_INITIAL_CONTEXT_APPLY_RUNNING_MIN_UPDATE_COUNT,2);
    contextApplyBreakdownDelta.add(SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_UPDATE_COUNT,5);
    contextApplyBreakdownDelta.add(SIM_INITIAL_CONTEXT_APPLY_FRONTIER_UPDATE_COUNT,3);
    contextApplyBreakdownDelta.add(SIM_INITIAL_CONTEXT_APPLY_SAFE_STORE_HANDOFF_COUNT,1);
    contextApplyBreakdownDelta.add(SIM_INITIAL_CONTEXT_APPLY_NOOP_EVENT_COUNT,7);
    recordSimInitialContextApplyBreakdown(contextApplyBreakdownDelta);
    const SimInitialContextApplyBreakdownStats contextApplyBreakdownAfter =
        getSimInitialContextApplyBreakdownStats();
    ok = expect_equal_u64(contextApplyBreakdownAfter.get(
                              SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_NANOSECONDS) -
                              contextApplyBreakdownBefore.get(
                                  SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_NANOSECONDS),
                          17,
                          "initial context-apply candidate timing increments") && ok;
    ok = expect_equal_u64(contextApplyBreakdownAfter.get(
                              SIM_INITIAL_CONTEXT_APPLY_FLOOR_NANOSECONDS) -
                              contextApplyBreakdownBefore.get(
                                  SIM_INITIAL_CONTEXT_APPLY_FLOOR_NANOSECONDS),
                          19,
                          "initial context-apply floor timing increments") && ok;
    ok = expect_equal_u64(contextApplyBreakdownAfter.get(
                              SIM_INITIAL_CONTEXT_APPLY_FRONTIER_NANOSECONDS) -
                              contextApplyBreakdownBefore.get(
                                  SIM_INITIAL_CONTEXT_APPLY_FRONTIER_NANOSECONDS),
                          23,
                          "initial context-apply frontier timing increments") && ok;
    ok = expect_equal_u64(contextApplyBreakdownAfter.get(
                              SIM_INITIAL_CONTEXT_APPLY_SAFE_STORE_HANDOFF_NANOSECONDS) -
                              contextApplyBreakdownBefore.get(
                                  SIM_INITIAL_CONTEXT_APPLY_SAFE_STORE_HANDOFF_NANOSECONDS),
                          29,
                          "initial context-apply safe-store handoff timing increments") && ok;
    ok = expect_equal_u64(contextApplyBreakdownAfter.get(
                              SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_ERASE_NANOSECONDS) -
                              contextApplyBreakdownBefore.get(
                                  SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_ERASE_NANOSECONDS),
                          31,
                          "initial context-apply candidate erase timing increments") && ok;
    ok = expect_equal_u64(contextApplyBreakdownAfter.get(
                              SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_INSERT_NANOSECONDS) -
                              contextApplyBreakdownBefore.get(
                                  SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_INSERT_NANOSECONDS),
                          37,
                          "initial context-apply candidate insert timing increments") && ok;
    ok = expect_equal_u64(contextApplyBreakdownAfter.get(
                              SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_SORT_NANOSECONDS) -
                              contextApplyBreakdownBefore.get(
                                  SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_SORT_NANOSECONDS),
                          41,
                          "initial context-apply candidate sort timing increments") && ok;
    ok = expect_equal_u64(contextApplyBreakdownAfter.get(
                              SIM_INITIAL_CONTEXT_APPLY_RUNNING_MIN_UPDATE_COUNT) -
                              contextApplyBreakdownBefore.get(
                                  SIM_INITIAL_CONTEXT_APPLY_RUNNING_MIN_UPDATE_COUNT),
                          2,
                          "initial context-apply runningMin update count increments") && ok;
    ok = expect_equal_u64(contextApplyBreakdownAfter.get(
                              SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_UPDATE_COUNT) -
                              contextApplyBreakdownBefore.get(
                                  SIM_INITIAL_CONTEXT_APPLY_CANDIDATE_UPDATE_COUNT),
                          5,
                          "initial context-apply candidate update count increments") && ok;
    ok = expect_equal_u64(contextApplyBreakdownAfter.get(
                              SIM_INITIAL_CONTEXT_APPLY_FRONTIER_UPDATE_COUNT) -
                              contextApplyBreakdownBefore.get(
                                  SIM_INITIAL_CONTEXT_APPLY_FRONTIER_UPDATE_COUNT),
                          3,
                          "initial context-apply frontier update count increments") && ok;
    ok = expect_equal_u64(contextApplyBreakdownAfter.get(
                              SIM_INITIAL_CONTEXT_APPLY_SAFE_STORE_HANDOFF_COUNT) -
                              contextApplyBreakdownBefore.get(
                                  SIM_INITIAL_CONTEXT_APPLY_SAFE_STORE_HANDOFF_COUNT),
                          1,
                          "initial context-apply safe-store handoff count increments") && ok;
	    ok = expect_equal_u64(contextApplyBreakdownAfter.get(
	                              SIM_INITIAL_CONTEXT_APPLY_NOOP_EVENT_COUNT) -
	                              contextApplyBreakdownBefore.get(
	                                  SIM_INITIAL_CONTEXT_APPLY_NOOP_EVENT_COUNT),
	                          7,
	                          "initial context-apply no-op event count increments") && ok;

	    const SimInitialCandidateReplayStructureStats candidateReplayBefore =
	        getSimInitialCandidateReplayStructureStats();
	    SimInitialCandidateReplayStructureStats candidateReplayDelta;
	    candidateReplayDelta.add(SIM_INITIAL_CANDIDATE_REPLAY_SUMMARY_COUNT,13);
	    candidateReplayDelta.add(SIM_INITIAL_CANDIDATE_REPLAY_PROCESSED_COUNT,11);
	    candidateReplayDelta.add(SIM_INITIAL_CANDIDATE_REPLAY_ACCEPTED_UPDATE_COUNT,7);
	    candidateReplayDelta.add(SIM_INITIAL_CANDIDATE_REPLAY_REJECTED_BELOW_FLOOR_COUNT,2);
	    candidateReplayDelta.add(SIM_INITIAL_CANDIDATE_REPLAY_INSERTION_COUNT,3);
	    candidateReplayDelta.add(SIM_INITIAL_CANDIDATE_REPLAY_REPLACEMENT_COUNT,4);
	    candidateReplayDelta.add(SIM_INITIAL_CANDIDATE_REPLAY_ERASURE_COUNT,5);
	    candidateReplayDelta.add(SIM_INITIAL_CANDIDATE_REPLAY_TIE_UPDATE_COUNT,6);
	    candidateReplayDelta.add(SIM_INITIAL_CANDIDATE_REPLAY_FIRST_MAX_UPDATE_COUNT,8);
	    candidateReplayDelta.add(SIM_INITIAL_CANDIDATE_REPLAY_FINAL_CANDIDATE_COUNT,9);
	    recordSimInitialCandidateReplayStructure(candidateReplayDelta);
	    const SimInitialCandidateReplayStructureStats candidateReplayAfter =
	        getSimInitialCandidateReplayStructureStats();
	    ok = expect_equal_u64(candidateReplayAfter.get(
	                              SIM_INITIAL_CANDIDATE_REPLAY_SUMMARY_COUNT) -
	                              candidateReplayBefore.get(
	                                  SIM_INITIAL_CANDIDATE_REPLAY_SUMMARY_COUNT),
	                          13,
	                          "initial candidate replay summary count increments") && ok;
	    ok = expect_equal_u64(candidateReplayAfter.get(
	                              SIM_INITIAL_CANDIDATE_REPLAY_PROCESSED_COUNT) -
	                              candidateReplayBefore.get(
	                                  SIM_INITIAL_CANDIDATE_REPLAY_PROCESSED_COUNT),
	                          11,
	                          "initial candidate replay processed count increments") && ok;
	    ok = expect_equal_u64(candidateReplayAfter.get(
	                              SIM_INITIAL_CANDIDATE_REPLAY_ACCEPTED_UPDATE_COUNT) -
	                              candidateReplayBefore.get(
	                                  SIM_INITIAL_CANDIDATE_REPLAY_ACCEPTED_UPDATE_COUNT),
	                          7,
	                          "initial candidate replay accepted count increments") && ok;
	    ok = expect_equal_u64(candidateReplayAfter.get(
	                              SIM_INITIAL_CANDIDATE_REPLAY_REJECTED_BELOW_FLOOR_COUNT) -
	                              candidateReplayBefore.get(
	                                  SIM_INITIAL_CANDIDATE_REPLAY_REJECTED_BELOW_FLOOR_COUNT),
	                          2,
	                          "initial candidate replay rejected-below-floor count increments") && ok;
	    ok = expect_equal_u64(candidateReplayAfter.get(
	                              SIM_INITIAL_CANDIDATE_REPLAY_INSERTION_COUNT) -
	                              candidateReplayBefore.get(
	                                  SIM_INITIAL_CANDIDATE_REPLAY_INSERTION_COUNT),
	                          3,
	                          "initial candidate replay insertion count increments") && ok;
	    ok = expect_equal_u64(candidateReplayAfter.get(
	                              SIM_INITIAL_CANDIDATE_REPLAY_REPLACEMENT_COUNT) -
	                              candidateReplayBefore.get(
	                                  SIM_INITIAL_CANDIDATE_REPLAY_REPLACEMENT_COUNT),
	                          4,
	                          "initial candidate replay replacement count increments") && ok;
	    ok = expect_equal_u64(candidateReplayAfter.get(
	                              SIM_INITIAL_CANDIDATE_REPLAY_ERASURE_COUNT) -
	                              candidateReplayBefore.get(
	                                  SIM_INITIAL_CANDIDATE_REPLAY_ERASURE_COUNT),
	                          5,
	                          "initial candidate replay erasure count increments") && ok;
	    ok = expect_equal_u64(candidateReplayAfter.get(
	                              SIM_INITIAL_CANDIDATE_REPLAY_TIE_UPDATE_COUNT) -
	                              candidateReplayBefore.get(
	                                  SIM_INITIAL_CANDIDATE_REPLAY_TIE_UPDATE_COUNT),
	                          6,
	                          "initial candidate replay tie update count increments") && ok;
	    ok = expect_equal_u64(candidateReplayAfter.get(
	                              SIM_INITIAL_CANDIDATE_REPLAY_FIRST_MAX_UPDATE_COUNT) -
	                              candidateReplayBefore.get(
	                                  SIM_INITIAL_CANDIDATE_REPLAY_FIRST_MAX_UPDATE_COUNT),
	                          8,
	                          "initial candidate replay first-max update count increments") && ok;
	    ok = expect_equal_u64(candidateReplayAfter.get(
	                              SIM_INITIAL_CANDIDATE_REPLAY_FINAL_CANDIDATE_COUNT) -
	                              candidateReplayBefore.get(
	                                  SIM_INITIAL_CANDIDATE_REPLAY_FINAL_CANDIDATE_COUNT),
	                          9,
	                          "initial candidate replay final candidate count increments") && ok;

	    const SimInitialCandidateChurnStats candidateChurnBefore =
	        getSimInitialCandidateChurnStats();
	    SimInitialCandidateChurnStats candidateChurnDelta;
	    struct ChurnCounterExpectation
	    {
	      SimInitialContextApplyBreakdownField field;
	      uint64_t value;
	      const char *label;
	    };
	    const ChurnCounterExpectation churnExpectations[] = {
	      {SIM_INITIAL_CANDIDATE_CHURN_CONTAINER_HIGH_WATER,50,"high-water"},
	      {SIM_INITIAL_CANDIDATE_CHURN_CONTAINER_FINAL_SIZE,7,"final size"},
	      {SIM_INITIAL_CANDIDATE_CHURN_CUMULATIVE_CONTAINER_SIZE,101,"cumulative size"},
	      {SIM_INITIAL_CANDIDATE_CHURN_REPLACEMENT_CHAINS,13,"replacement chain"},
	      {SIM_INITIAL_CANDIDATE_CHURN_MAX_REPLACEMENT_CHAIN,17,"max replacement chain"},
	      {SIM_INITIAL_CANDIDATE_CHURN_OVERWRITTEN_UPDATES,19,"overwritten update"},
	      {SIM_INITIAL_CANDIDATE_CHURN_FINAL_SURVIVOR_UPDATES,23,"final survivor"},
	      {SIM_INITIAL_CANDIDATE_CHURN_ORDER_SENSITIVE_UPDATES,29,"order-sensitive"},
	      {SIM_INITIAL_CANDIDATE_CHURN_FIRST_MAX_UPDATES,31,"first-max"},
	      {SIM_INITIAL_CANDIDATE_CHURN_TIE_UPDATES,37,"tie"},
	      {SIM_INITIAL_CANDIDATE_CHURN_HEAP_BUILDS,41,"heap build"},
	      {SIM_INITIAL_CANDIDATE_CHURN_HEAP_UPDATES,43,"heap update"},
	      {SIM_INITIAL_CANDIDATE_CHURN_INDEX_REBUILDS,47,"index rebuild"}
	    };
	    for(size_t expectationIndex = 0;
	        expectationIndex < sizeof(churnExpectations) / sizeof(churnExpectations[0]);
	        ++expectationIndex)
	    {
	      candidateChurnDelta.add(churnExpectations[expectationIndex].field,
	                              churnExpectations[expectationIndex].value);
	    }
	    recordSimInitialCandidateChurn(candidateChurnDelta);
	    const SimInitialCandidateChurnStats candidateChurnAfter =
	        getSimInitialCandidateChurnStats();
	    for(size_t expectationIndex = 0;
	        expectationIndex < sizeof(churnExpectations) / sizeof(churnExpectations[0]);
	        ++expectationIndex)
	    {
	      const string label =
	        string("initial candidate churn ") +
	        churnExpectations[expectationIndex].label +
	        " count increments";
	      ok = expect_equal_u64(candidateChurnAfter.get(churnExpectations[expectationIndex].field) -
	                                candidateChurnBefore.get(churnExpectations[expectationIndex].field),
	                            churnExpectations[expectationIndex].value,
	                            label.c_str()) && ok;
	    }

	    const SimInitialCandidateContainerShadowStats containerShadowBefore =
	        getSimInitialCandidateContainerShadowStats();
	    SimInitialCandidateContainerShadowStats containerShadowDelta;
	    containerShadowDelta.add(SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_CALLS,1);
	    containerShadowDelta.add(SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_NANOSECONDS,11);
	    containerShadowDelta.add(SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_STATE_MISMATCHES,13);
	    containerShadowDelta.add(SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_EST_SAVED_ERASURES,53);
	    containerShadowDelta.add(SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_HIGH_WATER_ENTRIES,61);
	    recordSimInitialCandidateContainerShadow(containerShadowDelta);
	    const SimInitialCandidateContainerShadowStats containerShadowAfter =
	        getSimInitialCandidateContainerShadowStats();
	    ok = expect_equal_u64(containerShadowAfter.get(
	                              SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_CALLS) -
	                              containerShadowBefore.get(
	                                  SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_CALLS),
	                          1,
	                          "initial candidate container shadow call count increments") && ok;
	    ok = expect_equal_u64(containerShadowAfter.get(
	                              SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_NANOSECONDS) -
	                              containerShadowBefore.get(
	                                  SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_NANOSECONDS),
	                          11,
	                          "initial candidate container shadow timing increments") && ok;
	    ok = expect_equal_u64(containerShadowAfter.get(
	                              SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_STATE_MISMATCHES) -
	                              containerShadowBefore.get(
	                                  SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_STATE_MISMATCHES),
	                          13,
	                          "initial candidate container shadow state mismatch increments") && ok;
	    ok = expect_equal_u64(containerShadowAfter.get(
	                              SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_EST_SAVED_ERASURES) -
	                              containerShadowBefore.get(
	                                  SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_EST_SAVED_ERASURES),
	                          53,
	                          "initial candidate container shadow saved erasure increments") && ok;
	    ok = expect_equal_u64(containerShadowAfter.get(
	                              SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_HIGH_WATER_ENTRIES) -
	                              containerShadowBefore.get(
	                                  SIM_INITIAL_CANDIDATE_CONTAINER_SHADOW_HIGH_WATER_ENTRIES),
	                          61,
	                          "initial candidate container shadow high-water increments") && ok;

	    SimKernelContext safeStoreContext(16, 16);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, safeStoreContext);
    addnodeIndexed(20, 1, 1, 4, 4, safeStoreContext);
    addnodeIndexed(25, 2, 2, 6, 6, safeStoreContext);
    std::vector<SimScanCudaInitialRunSummary> safeStoreSummaries(5);
    safeStoreSummaries[0].startCoord = packSimCoord(1, 1);
    safeStoreSummaries[0].endI = 4;
    safeStoreSummaries[0].minEndJ = 4;
    safeStoreSummaries[0].maxEndJ = 4;
    safeStoreSummaries[0].score = 20;
    safeStoreSummaries[0].scoreEndJ = 4;
    safeStoreSummaries[1].startCoord = packSimCoord(2, 2);
    safeStoreSummaries[1].endI = 6;
    safeStoreSummaries[1].minEndJ = 6;
    safeStoreSummaries[1].maxEndJ = 6;
    safeStoreSummaries[1].score = 25;
    safeStoreSummaries[1].scoreEndJ = 6;
    safeStoreSummaries[2].startCoord = packSimCoord(3, 3);
    safeStoreSummaries[2].endI = 7;
    safeStoreSummaries[2].minEndJ = 7;
    safeStoreSummaries[2].maxEndJ = 8;
    safeStoreSummaries[2].score = 21;
    safeStoreSummaries[2].scoreEndJ = 8;
    safeStoreSummaries[3].startCoord = packSimCoord(3, 3);
    safeStoreSummaries[3].endI = 8;
    safeStoreSummaries[3].minEndJ = 3;
    safeStoreSummaries[3].maxEndJ = 9;
    safeStoreSummaries[3].score = 18;
    safeStoreSummaries[3].scoreEndJ = 4;
    safeStoreSummaries[4].startCoord = packSimCoord(4, 4);
    safeStoreSummaries[4].endI = 9;
    safeStoreSummaries[4].minEndJ = 4;
    safeStoreSummaries[4].maxEndJ = 5;
    safeStoreSummaries[4].score = 19;
    safeStoreSummaries[4].scoreEndJ = 4;
    const SimInitialSafeStoreRebuildStats initialSafeStoreStatsBefore =
        getSimInitialSafeStoreRebuildStats();
    SimInitialSafeStoreRebuildStats safeStoreMergeStats;
    mergeSimCudaInitialRunSummariesIntoSafeStore(safeStoreSummaries,
                                                safeStoreContext,
                                                &safeStoreMergeStats);
    recordSimInitialSafeStoreRebuildStats(safeStoreMergeStats);
    const SimInitialSafeStoreRebuildStats initialSafeStoreStatsAfterMerge =
        getSimInitialSafeStoreRebuildStats();
    ok = expect_equal_u64(initialSafeStoreStatsAfterMerge.updateCalls -
                              initialSafeStoreStatsBefore.updateCalls,
                          1,
                          "initial safe-store update call count increments") && ok;
    ok = expect_equal_u64(initialSafeStoreStatsAfterMerge.updateSummaries -
                              initialSafeStoreStatsBefore.updateSummaries,
                          5,
                          "initial safe-store update summary count increments") && ok;
    ok = expect_equal_u64(initialSafeStoreStatsAfterMerge.updateInsertedStates -
                              initialSafeStoreStatsBefore.updateInsertedStates,
                          4,
                          "initial safe-store update inserted-state count increments") && ok;
    ok = expect_equal_u64(initialSafeStoreStatsAfterMerge.updateMergedSummaries -
                              initialSafeStoreStatsBefore.updateMergedSummaries,
                          1,
                          "initial safe-store update merged-summary count increments") && ok;
    ok = expect_equal_u64(initialSafeStoreStatsAfterMerge.updateStoreSizeBefore -
                              initialSafeStoreStatsBefore.updateStoreSizeBefore,
                          0,
                          "initial safe-store update size-before count records empty store") && ok;
    ok = expect_equal_u64(initialSafeStoreStatsAfterMerge.updateStoreSizeAfter -
                              initialSafeStoreStatsBefore.updateStoreSizeAfter,
                          4,
                          "initial safe-store update size-after count records unique starts") && ok;
    ok = expect_equal_bool(safeStoreContext.safeCandidateStateStore.valid,
                           true,
                           "safe store marked valid after merge") && ok;
    ok = expect_equal_size(safeStoreContext.safeCandidateStateStore.states.size(),
                           4,
                           "safe store merges duplicate starts") && ok;
    const SimScanCudaCandidateState *mergedStoreState =
        find_candidate_state(safeStoreContext.safeCandidateStateStore, 3, 3);
    ok = expect_true(mergedStoreState != NULL, "merged safe store state present") && ok;
    if (mergedStoreState != NULL)
    {
        ok = expect_equal_int(mergedStoreState->score, 21, "safe store keeps best score") && ok;
        ok = expect_equal_int(mergedStoreState->endI, 7, "safe store keeps best end row") && ok;
        ok = expect_equal_int(mergedStoreState->endJ, 8, "safe store keeps best end col") && ok;
        ok = expect_equal_int(mergedStoreState->top, 7, "safe store merges top bound") && ok;
        ok = expect_equal_int(mergedStoreState->bot, 8, "safe store merges bottom bound") && ok;
        ok = expect_equal_int(mergedStoreState->left, 3, "safe store merges left bound") && ok;
        ok = expect_equal_int(mergedStoreState->right, 9, "safe store merges right bound") && ok;
    }
    const SimInitialSafeStorePrecombineShadowStats precombineShadowBefore =
        getSimInitialSafeStorePrecombineShadowStats();
    const SimInitialSafeStorePrecombineShadowStats precombineShadowDelta =
        runSimInitialSafeStorePrecombineShadow(
            safeStoreSummaries,
            safeStoreContext.safeCandidateStateStore);
    ok = expect_equal_u64(precombineShadowDelta.calls,
                          1,
                          "initial safe-store precombine shadow runs once") && ok;
    ok = expect_equal_u64(precombineShadowDelta.inputSummaries,
                          5,
                          "initial safe-store precombine shadow records input summaries") && ok;
    ok = expect_equal_u64(precombineShadowDelta.uniqueStates,
                          4,
                          "initial safe-store precombine shadow records unique states") && ok;
    ok = expect_equal_u64(precombineShadowDelta.duplicateSummaries,
                          1,
                          "initial safe-store precombine shadow records duplicate summaries") && ok;
    ok = expect_equal_u64(precombineShadowDelta.estSavedUpserts,
                          1,
                          "initial safe-store precombine shadow estimates saved upserts") && ok;
    ok = expect_equal_u64(precombineShadowDelta.sizeMismatches,
                          0,
                          "initial safe-store precombine shadow size matches") && ok;
    ok = expect_equal_u64(precombineShadowDelta.candidateMismatches,
                          0,
                          "initial safe-store precombine shadow candidates match") && ok;
    ok = expect_equal_u64(precombineShadowDelta.orderMismatches,
                          0,
                          "initial safe-store precombine shadow order matches") && ok;
    ok = expect_equal_u64(precombineShadowDelta.digestMismatches,
                          0,
                          "initial safe-store precombine shadow digest matches") && ok;
    recordSimInitialSafeStorePrecombineShadow(precombineShadowDelta);
    const SimInitialSafeStorePrecombineShadowStats precombineShadowAfter =
        getSimInitialSafeStorePrecombineShadowStats();
    ok = expect_equal_u64(precombineShadowAfter.calls - precombineShadowBefore.calls,
                          1,
                          "initial safe-store precombine shadow call count increments") && ok;
    ok = expect_equal_u64(precombineShadowAfter.inputSummaries -
                              precombineShadowBefore.inputSummaries,
                          5,
                          "initial safe-store precombine shadow input summary count increments") && ok;
    ok = expect_equal_u64(precombineShadowAfter.uniqueStates -
                              precombineShadowBefore.uniqueStates,
                          4,
                          "initial safe-store precombine shadow unique-state count increments") && ok;
    ok = expect_equal_u64(precombineShadowAfter.duplicateSummaries -
                              precombineShadowBefore.duplicateSummaries,
                          1,
                          "initial safe-store precombine shadow duplicate-summary count increments") && ok;
    ok = expect_equal_u64(precombineShadowAfter.estSavedUpserts -
                              precombineShadowBefore.estSavedUpserts,
                          1,
                          "initial safe-store precombine shadow saved-upsert estimate increments") && ok;
    ok = expect_true(precombineShadowAfter.nanoseconds >= precombineShadowBefore.nanoseconds,
                     "initial safe-store precombine shadow timing is monotonic") && ok;
    ok = expect_true(precombineShadowDelta.buildNanoseconds >=
                         precombineShadowDelta.groupBuildNanoseconds,
                     "initial safe-store precombine shadow build includes group build") && ok;
    ok = expect_true(precombineShadowDelta.buildNanoseconds >=
                         precombineShadowDelta.allocNanoseconds,
                     "initial safe-store precombine shadow build includes allocation timing") && ok;
    ok = expect_true(precombineShadowDelta.compareNanoseconds >=
                         precombineShadowDelta.digestNanoseconds,
                     "initial safe-store precombine shadow compare includes digest timing") && ok;
    ok = expect_true(precombineShadowDelta.compareNanoseconds >=
                         precombineShadowDelta.orderCompareNanoseconds,
                     "initial safe-store precombine shadow compare includes order compare timing") && ok;
    ok = expect_true(precombineShadowAfter.buildNanoseconds -
                         precombineShadowBefore.buildNanoseconds >=
                     precombineShadowDelta.buildNanoseconds,
                     "initial safe-store precombine shadow build timing increments") && ok;
    ok = expect_true(precombineShadowAfter.groupBuildNanoseconds -
                         precombineShadowBefore.groupBuildNanoseconds >=
                     precombineShadowDelta.groupBuildNanoseconds,
                     "initial safe-store precombine shadow group build timing increments") && ok;
    ok = expect_true(precombineShadowAfter.allocNanoseconds -
                         precombineShadowBefore.allocNanoseconds >=
                     precombineShadowDelta.allocNanoseconds,
                     "initial safe-store precombine shadow allocation timing increments") && ok;
    ok = expect_true(precombineShadowAfter.compareNanoseconds -
                         precombineShadowBefore.compareNanoseconds >=
                     precombineShadowDelta.compareNanoseconds,
                     "initial safe-store precombine shadow compare timing increments") && ok;
    ok = expect_true(precombineShadowAfter.digestNanoseconds -
                         precombineShadowBefore.digestNanoseconds >=
                     precombineShadowDelta.digestNanoseconds,
                     "initial safe-store precombine shadow digest timing increments") && ok;
    ok = expect_true(precombineShadowAfter.orderCompareNanoseconds -
                         precombineShadowBefore.orderCompareNanoseconds >=
                     precombineShadowDelta.orderCompareNanoseconds,
                     "initial safe-store precombine shadow order compare timing increments") && ok;
    ok = expect_equal_u64(precombineShadowAfter.sizeMismatches -
                              precombineShadowBefore.sizeMismatches,
                          0,
                          "initial safe-store precombine shadow size mismatch count stays zero") && ok;
    ok = expect_equal_u64(precombineShadowAfter.candidateMismatches -
                              precombineShadowBefore.candidateMismatches,
                          0,
                          "initial safe-store precombine shadow candidate mismatch count stays zero") && ok;
    ok = expect_equal_u64(precombineShadowAfter.orderMismatches -
                              precombineShadowBefore.orderMismatches,
                          0,
                          "initial safe-store precombine shadow order mismatch count stays zero") && ok;
    ok = expect_equal_u64(precombineShadowAfter.digestMismatches -
                              precombineShadowBefore.digestMismatches,
                          0,
                          "initial safe-store precombine shadow digest mismatch count stays zero") && ok;
    SimKernelContext safeStoreContextBeforePrune = safeStoreContext;
    SimInitialSafeStoreRebuildStats safeStorePruneStats;
    pruneSimSafeCandidateStateStore(safeStoreContext, &safeStorePruneStats);
    recordSimInitialSafeStoreRebuildStats(safeStorePruneStats);
    const SimInitialSafeStoreRebuildStats initialSafeStoreStatsAfterPrune =
        getSimInitialSafeStoreRebuildStats();
    ok = expect_equal_u64(initialSafeStoreStatsAfterPrune.pruneCalls -
                              initialSafeStoreStatsAfterMerge.pruneCalls,
                          1,
                          "initial safe-store prune call count increments") && ok;
    ok = expect_equal_u64(initialSafeStoreStatsAfterPrune.pruneScannedStates -
                              initialSafeStoreStatsAfterMerge.pruneScannedStates,
                          4,
                          "initial safe-store prune scanned-state count increments") && ok;
    ok = expect_equal_u64(initialSafeStoreStatsAfterPrune.pruneKeptStates -
                              initialSafeStoreStatsAfterMerge.pruneKeptStates,
                          3,
                          "initial safe-store prune kept-state count increments") && ok;
    ok = expect_equal_u64(initialSafeStoreStatsAfterPrune.pruneRemovedStates -
                              initialSafeStoreStatsAfterMerge.pruneRemovedStates,
                          1,
                          "initial safe-store prune removed-state count increments") && ok;
    ok = expect_equal_u64(initialSafeStoreStatsAfterPrune.pruneKeptAboveFloor -
                              initialSafeStoreStatsAfterMerge.pruneKeptAboveFloor,
                          2,
                          "initial safe-store prune above-floor kept count increments") && ok;
    ok = expect_equal_u64(initialSafeStoreStatsAfterPrune.pruneKeptFrontier -
                              initialSafeStoreStatsAfterMerge.pruneKeptFrontier,
                          1,
                          "initial safe-store prune frontier kept count increments") && ok;
    ok = expect_equal_size(safeStoreContext.safeCandidateStateStore.states.size(),
                           3,
                           "safe store prunes below-floor extras") && ok;
    ok = expect_true(find_candidate_state(safeStoreContext.safeCandidateStateStore, 1, 1) != NULL,
                     "safe store keeps floor top-k state") && ok;
    ok = expect_true(find_candidate_state(safeStoreContext.safeCandidateStateStore, 2, 2) != NULL,
                     "safe store keeps best top-k state") && ok;
    ok = expect_true(find_candidate_state(safeStoreContext.safeCandidateStateStore, 3, 3) != NULL,
                     "safe store keeps extra above floor") && ok;
    ok = expect_true(find_candidate_state(safeStoreContext.safeCandidateStateStore, 4, 4) == NULL,
                     "safe store drops extra below floor") && ok;
    const SimInitialSafeStorePruneIndexShadowStats pruneIndexShadowBefore =
        getSimInitialSafeStorePruneIndexShadowStats();
    const SimInitialSafeStorePruneIndexShadowStats pruneIndexShadowDelta =
        runSimInitialSafeStorePruneIndexShadow(
            safeStoreContextBeforePrune,
            safeStoreContext.safeCandidateStateStore,
            safeStorePruneStats);
    ok = expect_equal_u64(pruneIndexShadowDelta.calls,
                          1,
                          "initial prune/index shadow runs once") && ok;
    ok = expect_equal_u64(pruneIndexShadowDelta.statesScanned,
                          4,
                          "initial prune/index shadow records scanned states") && ok;
    ok = expect_equal_u64(pruneIndexShadowDelta.statesKept,
                          3,
                          "initial prune/index shadow records kept states") && ok;
    ok = expect_equal_u64(pruneIndexShadowDelta.statesRemoved,
                          1,
                          "initial prune/index shadow records removed states") && ok;
    ok = expect_equal_u64(pruneIndexShadowDelta.sizeMismatches,
                          0,
                          "initial prune/index shadow size matches") && ok;
    ok = expect_equal_u64(pruneIndexShadowDelta.candidateMismatches,
                          0,
                          "initial prune/index shadow candidates match") && ok;
    ok = expect_equal_u64(pruneIndexShadowDelta.orderMismatches,
                          0,
                          "initial prune/index shadow order matches") && ok;
    ok = expect_equal_u64(pruneIndexShadowDelta.digestMismatches,
                          0,
                          "initial prune/index shadow digest matches") && ok;
    recordSimInitialSafeStorePruneIndexShadow(pruneIndexShadowDelta);
    const SimInitialSafeStorePruneIndexShadowStats pruneIndexShadowAfter =
        getSimInitialSafeStorePruneIndexShadowStats();
    ok = expect_equal_u64(pruneIndexShadowAfter.calls -
                              pruneIndexShadowBefore.calls,
                          1,
                          "initial prune/index shadow call count increments") && ok;
    ok = expect_equal_u64(pruneIndexShadowAfter.statesScanned -
                              pruneIndexShadowBefore.statesScanned,
                          4,
                          "initial prune/index shadow scanned-state count increments") && ok;
    ok = expect_equal_u64(pruneIndexShadowAfter.statesKept -
                              pruneIndexShadowBefore.statesKept,
                          3,
                          "initial prune/index shadow kept-state count increments") && ok;
    ok = expect_equal_u64(pruneIndexShadowAfter.statesRemoved -
                              pruneIndexShadowBefore.statesRemoved,
                          1,
                          "initial prune/index shadow removed-state count increments") && ok;
    ok = expect_true(pruneIndexShadowAfter.nanoseconds >= pruneIndexShadowBefore.nanoseconds,
                     "initial prune/index shadow timing is monotonic") && ok;

    std::vector<uint64_t> erasedStartCoords(1, packSimCoord(2, 2));
    eraseSimSafeCandidateStateStoreStartCoords(erasedStartCoords, safeStoreContext);
    ok = expect_equal_size(safeStoreContext.safeCandidateStateStore.states.size(),
                           2,
                           "safe store erase removes affected start") && ok;
    ok = expect_true(find_candidate_state(safeStoreContext.safeCandidateStateStore, 2, 2) == NULL,
                     "safe store erase removes matching coord") && ok;
    eraseSimCandidatesByStartCoords(erasedStartCoords, safeStoreContext);
    ok = expect_equal_long(safeStoreContext.candidateCount, 1, "context erase removes matching candidate") && ok;
    ok = expect_equal_long(safeStoreContext.candidates[0].STARI, 1, "context erase keeps remaining start row") && ok;
    ok = expect_equal_long(safeStoreContext.candidates[0].STARJ, 1, "context erase keeps remaining start col") && ok;
    ok = expect_equal_long(safeStoreContext.runningMin, 20, "context erase refreshes runningMin") && ok;

    SimKernelContext reduceContext(8, 8);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, reduceContext);
    reduceContext.runningMin = addnodeIndexed(12, 1, 1, 3, 3, reduceContext);
    std::vector<SimScanCudaInitialRunSummary> regionRunSummaries(3);
    regionRunSummaries[0].startCoord = packSimCoord(2, 2);
    regionRunSummaries[0].endI = 5;
    regionRunSummaries[0].minEndJ = 4;
    regionRunSummaries[0].maxEndJ = 6;
    regionRunSummaries[0].score = 20;
    regionRunSummaries[0].scoreEndJ = 5;
    regionRunSummaries[1].startCoord = packSimCoord(2, 2);
    regionRunSummaries[1].endI = 6;
    regionRunSummaries[1].minEndJ = 7;
    regionRunSummaries[1].maxEndJ = 8;
    regionRunSummaries[1].score = 18;
    regionRunSummaries[1].scoreEndJ = 8;
    regionRunSummaries[2].startCoord = packSimCoord(3, 1);
    regionRunSummaries[2].endI = 7;
    regionRunSummaries[2].minEndJ = 2;
    regionRunSummaries[2].maxEndJ = 3;
    regionRunSummaries[2].score = 11;
    regionRunSummaries[2].scoreEndJ = 2;
    applySimCudaRegionRunSummaries(regionRunSummaries, reduceContext);
    ok = expect_equal_long(reduceContext.candidateCount, 2, "region summary reduce candidate count") && ok;
    ok = expect_equal_long(reduceContext.runningMin, 12, "region summary reduce runningMin") && ok;
    const std::vector<SimCandidate> reducedCandidates = sorted_candidates(reduceContext);
    ok = expect_equal_long(reducedCandidates[0].SCORE, 12, "seed candidate score preserved") && ok;
    ok = expect_equal_long(reducedCandidates[0].STARI, 1, "seed candidate start row preserved") && ok;
    ok = expect_equal_long(reducedCandidates[0].STARJ, 1, "seed candidate start col preserved") && ok;
    ok = expect_equal_long(reducedCandidates[1].SCORE, 20, "region summary best score") && ok;
    ok = expect_equal_long(reducedCandidates[1].STARI, 2, "region summary start row") && ok;
    ok = expect_equal_long(reducedCandidates[1].STARJ, 2, "region summary start col") && ok;
    ok = expect_equal_long(reducedCandidates[1].ENDI, 5, "region summary best end row") && ok;
    ok = expect_equal_long(reducedCandidates[1].ENDJ, 5, "region summary best end col") && ok;
    ok = expect_equal_long(reducedCandidates[1].TOP, 5, "region summary top bound") && ok;
    ok = expect_equal_long(reducedCandidates[1].BOT, 6, "region summary bottom bound") && ok;
    ok = expect_equal_long(reducedCandidates[1].LEFT, 4, "region summary left bound") && ok;
    ok = expect_equal_long(reducedCandidates[1].RIGHT, 8, "region summary right bound") && ok;

    const std::string query = "AAAAAA";
    const std::string target = "AAAAAA";
    const long minScore = 5;
    const std::string paddedQuery = " " + query;
    const std::string paddedTarget = " " + target;

    SimKernelContext legacyContext(static_cast<long>(query.size()), static_cast<long>(target.size()));
    SimKernelContext splitContext(static_cast<long>(query.size()), static_cast<long>(target.size()));
    SimCandidate legacyCandidate;
    SimCandidate splitCandidate;
    setup_materialized_context(query, target, minScore, legacyContext, legacyCandidate);
    setup_materialized_context(query, target, minScore, splitContext, splitCandidate);

    ok = expect_true(memcmp(&legacyCandidate, &splitCandidate, sizeof(SimCandidate)) == 0,
                     "same materialized candidate") && ok;

    updateSimCandidatesAfterTraceback(paddedQuery.c_str(),
                                      paddedTarget.c_str(),
                                      legacyCandidate.TOP,
                                      legacyCandidate.BOT,
                                      legacyCandidate.LEFT,
                                      legacyCandidate.RIGHT,
                                      legacyContext);

    const SimLocateResult locateResult =
        locateSimUpdateRegionCpu(paddedQuery.c_str(),
                                 paddedTarget.c_str(),
                                 splitCandidate.TOP,
                                 splitCandidate.BOT,
                                 splitCandidate.LEFT,
                                 splitCandidate.RIGHT,
                                 splitContext);
    ok = expect_true(locateResult.locateCellCount > 0, "locate cell count recorded") && ok;
    ok = expect_equal_bool(locateResult.hasUpdateRegion, true, "locate produced update region") && ok;
    applySimLocatedUpdateRegion(paddedQuery.c_str(),
                                paddedTarget.c_str(),
                                locateResult,
                                splitContext);

    ok = expect_candidates_equal(splitContext, legacyContext, "split locate/update matches legacy") && ok;
    ok = expect_equal_long(splitContext.runningMin, legacyContext.runningMin, "runningMin matches legacy") && ok;
    ok = expect_equal_size(splitContext.workspace.blocked.size(),
                           legacyContext.workspace.blocked.size(),
                           "blocked row vector size") && ok;

    const std::string proposalQuery = "AAAACCCC";
    const std::string proposalTarget = "AAAAGGGGCCCC";
    const std::string paddedProposalQuery = " " + proposalQuery;
    const std::string paddedProposalTarget = " " + proposalTarget;
    std::vector<SimScanCudaCandidateState> proposalStates(2);
    proposalStates[0].score = 120;
    proposalStates[0].startI = 1;
    proposalStates[0].startJ = 0;
    proposalStates[0].endI = 4;
    proposalStates[0].endJ = 4;
    proposalStates[1].score = 120;
    proposalStates[1].startI = 5;
    proposalStates[1].startJ = 8;
    proposalStates[1].endI = 8;
    proposalStates[1].endJ = 12;
    {
        SimKernelContext manualProposalContext(static_cast<long>(proposalQuery.size()), static_cast<long>(proposalTarget.size()));
        SimKernelContext helperProposalContext(static_cast<long>(proposalQuery.size()), static_cast<long>(proposalTarget.size()));
        initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, manualProposalContext);
        initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, helperProposalContext);

        std::vector<triplex> manualTriplexes;
        std::vector<triplex> helperTriplexes;
        SimRequest proposalRequest(proposalTarget, 0, minScore, 0, 0, 1, 128, -1000, 0);

        bool manualSuccess = true;
        for (size_t i = 0; i < proposalStates.size(); ++i)
        {
            const SimScanCudaCandidateState &proposal = proposalStates[i];
            if (!materializeSimCandidate(proposalRequest,
                                         paddedProposalQuery.c_str(),
                                         paddedProposalTarget.c_str(),
                                         static_cast<long>(proposalTarget.size()),
                                         static_cast<long>(proposal.score),
                                         static_cast<long>(proposal.startI) + 1,
                                         static_cast<long>(proposal.startJ) + 1,
                                         static_cast<long>(proposal.endI),
                                         static_cast<long>(proposal.endJ),
                                         0,
                                         manualProposalContext,
                                         manualTriplexes))
            {
                manualSuccess = false;
                break;
            }
        }

        setenv("LONGTARGET_SIM_CUDA_PROPOSAL_MATERIALIZE_BACKEND", "cuda_batch_traceback", 1);
        uint64_t batchRequestsBefore = 0;
        uint64_t batchCountBefore = 0;
        uint64_t batchSuccessBefore = 0;
        uint64_t batchFallbackBefore = 0;
        uint64_t batchTieFallbackBefore = 0;
        double batchGpuSecondsBefore = 0.0;
        double proposalPostSecondsBefore = 0.0;
        uint64_t proposalTracebackCudaEligibleBefore = 0;
        uint64_t proposalTracebackCudaSizeFilteredBefore = 0;
        uint64_t proposalTracebackCudaBatchFailedBefore = 0;
        uint64_t proposalTracebackCpuDirectBefore = 0;
        uint64_t proposalPostScoreRejectsBefore = 0;
        uint64_t proposalPostNtRejectsBefore = 0;
        uint64_t proposalTracebackCpuCellsBefore = 0;
        uint64_t proposalTracebackCudaCellsBefore = 0;
        uint64_t proposalAllCandidateStatesBefore = 0;
        uint64_t proposalBytesD2HBefore = 0;
        uint64_t proposalSelectedBefore = 0;
        uint64_t proposalSelectedBoxCellsBefore = 0;
        uint64_t proposalMaterializedBefore = 0;
        uint64_t proposalMaterializedQueryBasesBefore = 0;
        uint64_t proposalMaterializedTargetBasesBefore = 0;
        double proposalGpuSecondsBefore = 0.0;
        getSimProposalMaterializeBatchStats(batchRequestsBefore,
                                            batchCountBefore,
                                            batchSuccessBefore,
                                            batchFallbackBefore,
                                            batchTieFallbackBefore,
                                            batchGpuSecondsBefore,
                                            proposalPostSecondsBefore);
        getSimProposalTracebackRoutingStats(proposalTracebackCudaEligibleBefore,
                                            proposalTracebackCudaSizeFilteredBefore,
                                            proposalTracebackCudaBatchFailedBefore,
                                            proposalTracebackCpuDirectBefore,
                                            proposalPostScoreRejectsBefore,
                                            proposalPostNtRejectsBefore,
                                            proposalTracebackCpuCellsBefore,
                                            proposalTracebackCudaCellsBefore);
        getSimProposalStats(proposalAllCandidateStatesBefore,
                            proposalBytesD2HBefore,
                            proposalSelectedBefore,
                            proposalSelectedBoxCellsBefore,
                            proposalMaterializedBefore,
                            proposalMaterializedQueryBasesBefore,
                            proposalMaterializedTargetBasesBefore,
                            proposalGpuSecondsBefore);
        ok = expect_equal_bool(materializeSimProposalStates(proposalRequest,
                                                            paddedProposalQuery.c_str(),
                                                            paddedProposalTarget.c_str(),
                                                            static_cast<long>(proposalTarget.size()),
                                                            0,
                                                            proposalStates,
                                                            helperProposalContext,
                                                            helperTriplexes),
                              manualSuccess,
                              "proposal materialize dispatcher success") && ok;
        uint64_t batchRequestsAfter = 0;
        uint64_t batchCountAfter = 0;
        uint64_t batchSuccessAfter = 0;
        uint64_t batchFallbackAfter = 0;
        uint64_t batchTieFallbackAfter = 0;
        double batchGpuSecondsAfter = 0.0;
        double proposalPostSecondsAfter = 0.0;
        uint64_t proposalTracebackCudaEligibleAfter = 0;
        uint64_t proposalTracebackCudaSizeFilteredAfter = 0;
        uint64_t proposalTracebackCudaBatchFailedAfter = 0;
        uint64_t proposalTracebackCpuDirectAfter = 0;
        uint64_t proposalPostScoreRejectsAfter = 0;
        uint64_t proposalPostNtRejectsAfter = 0;
        uint64_t proposalTracebackCpuCellsAfter = 0;
        uint64_t proposalTracebackCudaCellsAfter = 0;
        uint64_t proposalAllCandidateStatesAfter = 0;
        uint64_t proposalBytesD2HAfter = 0;
        uint64_t proposalSelectedAfter = 0;
        uint64_t proposalSelectedBoxCellsAfter = 0;
        uint64_t proposalMaterializedAfter = 0;
        uint64_t proposalMaterializedQueryBasesAfter = 0;
        uint64_t proposalMaterializedTargetBasesAfter = 0;
        double proposalGpuSecondsAfter = 0.0;
        getSimProposalMaterializeBatchStats(batchRequestsAfter,
                                            batchCountAfter,
                                            batchSuccessAfter,
                                            batchFallbackAfter,
                                            batchTieFallbackAfter,
                                            batchGpuSecondsAfter,
                                            proposalPostSecondsAfter);
        getSimProposalTracebackRoutingStats(proposalTracebackCudaEligibleAfter,
                                            proposalTracebackCudaSizeFilteredAfter,
                                            proposalTracebackCudaBatchFailedAfter,
                                            proposalTracebackCpuDirectAfter,
                                            proposalPostScoreRejectsAfter,
                                            proposalPostNtRejectsAfter,
                                            proposalTracebackCpuCellsAfter,
                                            proposalTracebackCudaCellsAfter);
        getSimProposalStats(proposalAllCandidateStatesAfter,
                            proposalBytesD2HAfter,
                            proposalSelectedAfter,
                            proposalSelectedBoxCellsAfter,
                            proposalMaterializedAfter,
                            proposalMaterializedQueryBasesAfter,
                            proposalMaterializedTargetBasesAfter,
                            proposalGpuSecondsAfter);
        uint64_t expectedProposalSelectedBoxCells = 0;
        uint64_t expectedProposalMaterializedQueryBases = 0;
        uint64_t expectedProposalMaterializedTargetBases = 0;
        for (size_t i = 0; i < proposalStates.size(); ++i)
        {
            const SimScanCudaCandidateState &proposal = proposalStates[i];
            const uint64_t queryBases =
              static_cast<uint64_t>(static_cast<long>(proposal.endI) - (static_cast<long>(proposal.startI) + 1) + 1);
            const uint64_t targetBases =
              static_cast<uint64_t>(static_cast<long>(proposal.endJ) - (static_cast<long>(proposal.startJ) + 1) + 1);
            expectedProposalMaterializedQueryBases += queryBases;
            expectedProposalMaterializedTargetBases += targetBases;
            expectedProposalSelectedBoxCells += queryBases * targetBases;
        }
        ok = expect_triplex_lists_equal(helperTriplexes,
                                        manualTriplexes,
                                        "proposal materialize dispatcher triplexes") && ok;
        ok = expect_true(helperProposalContext.workspace.blocked == manualProposalContext.workspace.blocked,
                         "proposal materialize dispatcher blocked grid") && ok;
        ok = expect_equal_u64(batchRequestsAfter - batchRequestsBefore,
                              0,
                              "proposal materialize batch requests") && ok;
        ok = expect_equal_u64(batchCountAfter - batchCountBefore,
                              0,
                              "proposal materialize batch count") && ok;
        ok = expect_equal_u64(batchSuccessAfter - batchSuccessBefore,
                              0,
                              "proposal materialize batch success count") && ok;
        ok = expect_equal_u64(batchFallbackAfter - batchFallbackBefore,
                              0,
                              "proposal materialize batch fallback count") && ok;
        ok = expect_equal_u64(batchTieFallbackAfter - batchTieFallbackBefore,
                              0,
                              "proposal materialize batch tie fallback count") && ok;
        ok = expect_equal_u64(proposalTracebackCudaEligibleAfter - proposalTracebackCudaEligibleBefore,
                              0,
                              "proposal materialize cuda eligible count") && ok;
        ok = expect_equal_u64(proposalTracebackCudaSizeFilteredAfter - proposalTracebackCudaSizeFilteredBefore,
                              0,
                              "proposal materialize cuda size filtered count") && ok;
        ok = expect_equal_u64(proposalTracebackCudaBatchFailedAfter - proposalTracebackCudaBatchFailedBefore,
                              0,
                              "proposal materialize cuda batch failed count") && ok;
        ok = expect_equal_u64(proposalTracebackCpuDirectAfter - proposalTracebackCpuDirectBefore,
                              static_cast<uint64_t>(proposalStates.size()),
                              "proposal materialize cpu direct count") && ok;
        ok = expect_equal_u64(proposalPostScoreRejectsAfter - proposalPostScoreRejectsBefore,
                              0,
                              "proposal materialize post score rejects") && ok;
        ok = expect_equal_u64(proposalPostNtRejectsAfter - proposalPostNtRejectsBefore,
                              0,
                              "proposal materialize post nt rejects") && ok;
        ok = expect_equal_u64(proposalTracebackCpuCellsAfter - proposalTracebackCpuCellsBefore,
                              40,
                              "proposal materialize cpu traceback cells") && ok;
        ok = expect_equal_u64(proposalTracebackCudaCellsAfter - proposalTracebackCudaCellsBefore,
                              0,
                              "proposal materialize cuda traceback cells") && ok;
        ok = expect_equal_u64(proposalSelectedBoxCellsAfter - proposalSelectedBoxCellsBefore,
                              expectedProposalSelectedBoxCells,
                              "proposal materialize selected box cells") && ok;
        ok = expect_equal_u64(proposalMaterializedAfter - proposalMaterializedBefore,
                              static_cast<uint64_t>(proposalStates.size()),
                              "proposal materialize materialized count") && ok;
        ok = expect_equal_u64(proposalMaterializedQueryBasesAfter - proposalMaterializedQueryBasesBefore,
                              expectedProposalMaterializedQueryBases,
                              "proposal materialize query bases") && ok;
        ok = expect_equal_u64(proposalMaterializedTargetBasesAfter - proposalMaterializedTargetBasesBefore,
                              expectedProposalMaterializedTargetBases,
                              "proposal materialize target bases") && ok;

        uint64_t proposalLoopAttemptsBefore = 0;
        uint64_t proposalLoopShortCircuitBefore = 0;
        uint64_t proposalLoopInitialSourceBefore = 0;
        uint64_t proposalLoopSafeStoreSourceBefore = 0;
        uint64_t proposalLoopFallbackNoStoreBefore = 0;
        uint64_t proposalLoopFallbackSelectorFailureBefore = 0;
        uint64_t proposalLoopFallbackEmptySelectionBefore = 0;
        uint64_t proposalLoopGpuSafeStoreSourceBefore = 0;
        uint64_t proposalLoopGpuFrontierCacheSourceBefore = 0;
        uint64_t proposalLoopGpuSafeStoreFullSourceBefore = 0;
        uint64_t proposalMaterializeCpuBackendBefore = 0;
        uint64_t proposalMaterializeCudaBatchBackendBefore = 0;
        uint64_t proposalMaterializeHybridBackendBefore = 0;
        double deviceKLoopSecondsBefore = 0.0;
        getSimProposalLoopStats(proposalLoopAttemptsBefore,
                                proposalLoopShortCircuitBefore,
                                proposalLoopInitialSourceBefore,
                                proposalLoopSafeStoreSourceBefore,
                                proposalLoopFallbackNoStoreBefore,
                                proposalLoopFallbackSelectorFailureBefore,
                                proposalLoopFallbackEmptySelectionBefore);
        getSimDeviceKLoopStats(proposalLoopGpuSafeStoreSourceBefore,
                               proposalLoopGpuFrontierCacheSourceBefore,
                               proposalLoopGpuSafeStoreFullSourceBefore,
                               deviceKLoopSecondsBefore);
        getSimProposalMaterializeBackendStats(proposalMaterializeCpuBackendBefore,
                                              proposalMaterializeCudaBatchBackendBefore,
                                              proposalMaterializeHybridBackendBefore);
        recordSimProposalLoopAttempt();
        recordSimProposalLoopShortCircuit();
        recordSimProposalLoopSourceFromInitial();
        recordSimProposalLoopSourceFromSafeStore();
        recordSimProposalLoopSourceFromGpuSafeStore();
        recordSimProposalLoopSourceFromGpuFrontierCache();
        recordSimProposalLoopSourceFromGpuSafeStoreFull();
        recordSimProposalLoopFallbackReason(SIM_PROPOSAL_LOOP_FALLBACK_NO_STORE);
        recordSimProposalLoopFallbackReason(SIM_PROPOSAL_LOOP_FALLBACK_SELECTOR_FAILURE);
        recordSimProposalLoopFallbackReason(SIM_PROPOSAL_LOOP_FALLBACK_EMPTY_SELECTION);
        recordSimProposalMaterializeBackendCall(SIM_PROPOSAL_MATERIALIZE_BACKEND_CPU);
        recordSimProposalMaterializeBackendCall(SIM_PROPOSAL_MATERIALIZE_BACKEND_CUDA_BATCH_TRACEBACK);
        recordSimProposalMaterializeBackendCall(SIM_PROPOSAL_MATERIALIZE_BACKEND_HYBRID);
        uint64_t proposalLoopAttemptsAfter = 0;
        uint64_t proposalLoopShortCircuitAfter = 0;
        uint64_t proposalLoopInitialSourceAfter = 0;
        uint64_t proposalLoopSafeStoreSourceAfter = 0;
        uint64_t proposalLoopFallbackNoStoreAfter = 0;
        uint64_t proposalLoopFallbackSelectorFailureAfter = 0;
        uint64_t proposalLoopFallbackEmptySelectionAfter = 0;
        uint64_t proposalLoopGpuSafeStoreSourceAfter = 0;
        uint64_t proposalLoopGpuFrontierCacheSourceAfter = 0;
        uint64_t proposalLoopGpuSafeStoreFullSourceAfter = 0;
        uint64_t proposalMaterializeCpuBackendAfter = 0;
        uint64_t proposalMaterializeCudaBatchBackendAfter = 0;
        uint64_t proposalMaterializeHybridBackendAfter = 0;
        double deviceKLoopSecondsAfter = 0.0;
        getSimProposalLoopStats(proposalLoopAttemptsAfter,
                                proposalLoopShortCircuitAfter,
                                proposalLoopInitialSourceAfter,
                                proposalLoopSafeStoreSourceAfter,
                                proposalLoopFallbackNoStoreAfter,
                                proposalLoopFallbackSelectorFailureAfter,
                                proposalLoopFallbackEmptySelectionAfter);
        getSimDeviceKLoopStats(proposalLoopGpuSafeStoreSourceAfter,
                               proposalLoopGpuFrontierCacheSourceAfter,
                               proposalLoopGpuSafeStoreFullSourceAfter,
                               deviceKLoopSecondsAfter);
        getSimProposalMaterializeBackendStats(proposalMaterializeCpuBackendAfter,
                                              proposalMaterializeCudaBatchBackendAfter,
                                              proposalMaterializeHybridBackendAfter);
        ok = expect_equal_u64(proposalLoopAttemptsAfter - proposalLoopAttemptsBefore,
                              1,
                              "proposal loop attempt count increments") && ok;
        ok = expect_equal_u64(proposalLoopShortCircuitAfter - proposalLoopShortCircuitBefore,
                              1,
                              "proposal loop short-circuit count increments") && ok;
        ok = expect_equal_u64(proposalLoopInitialSourceAfter - proposalLoopInitialSourceBefore,
                              1,
                              "proposal loop initial-source count increments") && ok;
        ok = expect_equal_u64(proposalLoopSafeStoreSourceAfter - proposalLoopSafeStoreSourceBefore,
                              1,
                              "proposal loop safe-store source count increments") && ok;
        ok = expect_equal_u64(proposalLoopGpuSafeStoreSourceAfter - proposalLoopGpuSafeStoreSourceBefore,
                              1,
                              "proposal loop gpu safe-store source count increments") && ok;
        ok = expect_equal_u64(proposalLoopGpuFrontierCacheSourceAfter -
                              proposalLoopGpuFrontierCacheSourceBefore,
                              1,
                              "proposal loop gpu frontier-cache source count increments") && ok;
        ok = expect_equal_u64(proposalLoopGpuSafeStoreFullSourceAfter -
                              proposalLoopGpuSafeStoreFullSourceBefore,
                              1,
                              "proposal loop gpu full-safe-store source count increments") && ok;
        ok = expect_equal_u64(proposalLoopFallbackNoStoreAfter - proposalLoopFallbackNoStoreBefore,
                              1,
                              "proposal loop no-store fallback count increments") && ok;
        ok = expect_equal_u64(proposalLoopFallbackSelectorFailureAfter - proposalLoopFallbackSelectorFailureBefore,
                              1,
                              "proposal loop selector-failure fallback count increments") && ok;
        ok = expect_equal_u64(proposalLoopFallbackEmptySelectionAfter - proposalLoopFallbackEmptySelectionBefore,
                              1,
                              "proposal loop empty-selection fallback count increments") && ok;
        ok = expect_equal_u64(proposalMaterializeCpuBackendAfter - proposalMaterializeCpuBackendBefore,
                              1,
                              "proposal materialize cpu backend hit count increments") && ok;
        ok = expect_equal_u64(proposalMaterializeCudaBatchBackendAfter - proposalMaterializeCudaBatchBackendBefore,
                              1,
                              "proposal materialize cuda-batch backend hit count increments") && ok;
        ok = expect_equal_u64(proposalMaterializeHybridBackendAfter - proposalMaterializeHybridBackendBefore,
                              1,
                              "proposal materialize hybrid backend hit count increments") && ok;

        std::vector<SimScanCudaCandidateState> emptyProposalStates;
        SimKernelContext emptyProposalContext(static_cast<long>(proposalQuery.size()), static_cast<long>(proposalTarget.size()));
        initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, emptyProposalContext);
        std::vector<triplex> emptyProposalTriplexes;
        ok = expect_equal_bool(materializeSimProposalStates(proposalRequest,
                                                            paddedProposalQuery.c_str(),
                                                            paddedProposalTarget.c_str(),
                                                            static_cast<long>(proposalTarget.size()),
                                                            0,
                                                            emptyProposalStates,
                                                            emptyProposalContext,
                                                            emptyProposalTriplexes),
                               false,
                               "proposal materialize empty states falls back") && ok;
        ok = expect_equal_size(emptyProposalTriplexes.size(),
                               static_cast<size_t>(0),
                               "proposal materialize empty states no triplexes") && ok;
        unsetenv("LONGTARGET_SIM_CUDA_PROPOSAL_MATERIALIZE_BACKEND");
    }

    {
        double initialScanSecondsBefore = 0.0;
        double initialScanGpuSecondsBefore = 0.0;
        double initialScanD2HSecondsBefore = 0.0;
        double initialScanCpuMergeSecondsBefore = 0.0;
        double initialScanDiagSecondsBefore = 0.0;
        double initialScanOnlineReduceSecondsBefore = 0.0;
        double initialScanWaitSecondsBefore = 0.0;
        double initialScanCountCopySecondsBefore = 0.0;
        double initialScanBaseUploadSecondsBefore = 0.0;
        double initialProposalSelectD2HSecondsBefore = 0.0;
        double initialScanSyncWaitSecondsBefore = 0.0;
        double initialScanTailSecondsBefore = 0.0;
        double locateSecondsBefore = 0.0;
        double locateGpuSecondsBefore = 0.0;
        double regionScanGpuSecondsBefore = 0.0;
        double regionD2HSecondsBefore = 0.0;
        double materializeSecondsBefore = 0.0;
        double tracebackDpSecondsBefore = 0.0;
        double tracebackPostSecondsBefore = 0.0;
        getSimPhaseTimingStats(initialScanSecondsBefore,
                               initialScanGpuSecondsBefore,
                               initialScanD2HSecondsBefore,
                               initialScanCpuMergeSecondsBefore,
                               initialScanDiagSecondsBefore,
                               initialScanOnlineReduceSecondsBefore,
                               initialScanWaitSecondsBefore,
                               initialScanCountCopySecondsBefore,
                               initialScanBaseUploadSecondsBefore,
                               initialProposalSelectD2HSecondsBefore,
                               initialScanSyncWaitSecondsBefore,
                               initialScanTailSecondsBefore,
                               locateSecondsBefore,
                               locateGpuSecondsBefore,
                               regionScanGpuSecondsBefore,
                               regionD2HSecondsBefore,
                               materializeSecondsBefore,
                               tracebackDpSecondsBefore,
                               tracebackPostSecondsBefore);
        recordSimInitialScanDiagNanoseconds(2000000000ull);
        recordSimInitialScanOnlineReduceNanoseconds(3000000000ull);
        recordSimInitialScanWaitNanoseconds(4000000000ull);
        recordSimInitialScanCountCopyNanoseconds(5000000000ull);
        recordSimInitialScanBaseUploadNanoseconds(6000000000ull);
        recordSimInitialScanSyncWaitNanoseconds(7000000000ull);
        double initialScanSecondsAfter = 0.0;
        double initialScanGpuSecondsAfter = 0.0;
        double initialScanD2HSecondsAfter = 0.0;
        double initialScanCpuMergeSecondsAfter = 0.0;
        double initialScanDiagSecondsAfter = 0.0;
        double initialScanOnlineReduceSecondsAfter = 0.0;
        double initialScanWaitSecondsAfter = 0.0;
        double initialScanCountCopySecondsAfter = 0.0;
        double initialScanBaseUploadSecondsAfter = 0.0;
        double initialProposalSelectD2HSecondsAfter = 0.0;
        double initialScanSyncWaitSecondsAfter = 0.0;
        double initialScanTailSecondsAfter = 0.0;
        double locateSecondsAfter = 0.0;
        double locateGpuSecondsAfter = 0.0;
        double regionScanGpuSecondsAfter = 0.0;
        double regionD2HSecondsAfter = 0.0;
        double materializeSecondsAfter = 0.0;
        double tracebackDpSecondsAfter = 0.0;
        double tracebackPostSecondsAfter = 0.0;
        getSimPhaseTimingStats(initialScanSecondsAfter,
                               initialScanGpuSecondsAfter,
                               initialScanD2HSecondsAfter,
                               initialScanCpuMergeSecondsAfter,
                               initialScanDiagSecondsAfter,
                               initialScanOnlineReduceSecondsAfter,
                               initialScanWaitSecondsAfter,
                               initialScanCountCopySecondsAfter,
                               initialScanBaseUploadSecondsAfter,
                               initialProposalSelectD2HSecondsAfter,
                               initialScanSyncWaitSecondsAfter,
                               initialScanTailSecondsAfter,
                               locateSecondsAfter,
                               locateGpuSecondsAfter,
                               regionScanGpuSecondsAfter,
                               regionD2HSecondsAfter,
                               materializeSecondsAfter,
                               tracebackDpSecondsAfter,
                               tracebackPostSecondsAfter);
        ok = expect_close_double(initialScanDiagSecondsAfter - initialScanDiagSecondsBefore,
                                 2.0,
                                 1.0e-9,
                                 "initial scan diag seconds") && ok;
        ok = expect_close_double(initialScanOnlineReduceSecondsAfter - initialScanOnlineReduceSecondsBefore,
                                 3.0,
                                 1.0e-9,
                                 "initial scan online reduce seconds") && ok;
        ok = expect_close_double(initialScanWaitSecondsAfter - initialScanWaitSecondsBefore,
                                 4.0,
                                 1.0e-9,
                                 "initial scan wait seconds") && ok;
        ok = expect_close_double(initialScanCountCopySecondsAfter - initialScanCountCopySecondsBefore,
                                 5.0,
                                 1.0e-9,
                                 "initial scan count-copy seconds") && ok;
        ok = expect_close_double(initialScanBaseUploadSecondsAfter - initialScanBaseUploadSecondsBefore,
                                 6.0,
                                 1.0e-9,
                                 "initial scan base-upload seconds") && ok;
        ok = expect_close_double(initialScanSyncWaitSecondsAfter - initialScanSyncWaitSecondsBefore,
                                 7.0,
                                 1.0e-9,
                                 "initial scan sync-wait seconds") && ok;
    }

    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
