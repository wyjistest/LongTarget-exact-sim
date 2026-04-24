#include <algorithm>
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

static bool expect_equal_u64(uint64_t actual, uint64_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_equal_string(const std::string &actual, const std::string &expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected '" << expected << "', got '" << actual << "'\n";
    return false;
}

static SimScanCudaInitialRunSummary make_summary(int score,
                                                 long startI,
                                                 long startJ,
                                                 uint32_t endI,
                                                 uint32_t minEndJ,
                                                 uint32_t maxEndJ,
                                                 uint32_t scoreEndJ)
{
    SimScanCudaInitialRunSummary summary;
    summary.score = score;
    summary.startCoord = packSimCoord(startI, startJ);
    summary.endI = endI;
    summary.minEndJ = minEndJ;
    summary.maxEndJ = maxEndJ;
    summary.scoreEndJ = scoreEndJ;
    return summary;
}

static SimKernelContext make_context()
{
    SimKernelContext context(96, 192);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);
    return context;
}

static SimOrderedMaintenanceHostDigest host_digest_for_summaries(
    const std::vector<SimScanCudaInitialRunSummary> &summaries,
    bool maintainSafeStore)
{
    SimKernelContext context = make_context();
    SimOrderedMaintenanceHostDigest digest;
    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size() * 3),
                                    context,
                                    NULL,
                                    &digest);
    if (maintainSafeStore)
    {
        mergeSimCudaInitialRunSummariesIntoSafeStore(summaries, context);
        pruneSimSafeCandidateStateStore(context);
    }
    finalizeSimOrderedMaintenanceHostDigest(context, digest);
    return digest;
}

static bool expect_shadow_replay_matches(const std::string &caseId,
                                         const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                         bool maintainSafeStore = true)
{
    SimKernelContext initialContext = make_context();
    const uint64_t logicalEventCount = static_cast<uint64_t>(summaries.size() * 3);
    const SimOrderedMaintenanceHostDigest hostDigest =
        host_digest_for_summaries(summaries, maintainSafeStore);
    const SimOrderedMaintenanceHostDigest shadowDigest =
        replaySimOrderedMaintenanceIndependentShadowDigest(summaries,
                                                           logicalEventCount,
                                                           initialContext,
                                                           maintainSafeStore);
    const SimOrderedMaintenanceShadowReplayComparison comparison =
        compareSimOrderedMaintenanceShadowDigests(caseId,
                                                  static_cast<uint64_t>(summaries.size()),
                                                  hostDigest,
                                                  shadowDigest);

    bool ok = true;
    ok = expect_equal_u64(comparison.mismatchCount, 0, (caseId + " mismatch count").c_str()) && ok;
    ok = expect_equal_string(comparison.shadowStatus, "ran", (caseId + " shadow status").c_str()) && ok;
    ok = expect_equal_u64(shadowDigest.finalCandidateStateHash,
                          hostDigest.finalCandidateStateHash,
                          (caseId + " final candidate state hash").c_str()) &&
         ok;
    ok = expect_equal_u64(shadowDigest.replacementSequenceHash,
                          hostDigest.replacementSequenceHash,
                          (caseId + " replacement sequence hash").c_str()) &&
         ok;
    ok = expect_equal_u64(shadowDigest.runningMinUpdateSequenceHash,
                          hostDigest.runningMinUpdateSequenceHash,
                          (caseId + " running min hash").c_str()) &&
         ok;
    ok = expect_equal_u64(shadowDigest.safeStoreStateHash,
                          hostDigest.safeStoreStateHash,
                          (caseId + " safe store hash").c_str()) &&
         ok;
    ok = expect_equal_u64(shadowDigest.observedCandidateIndexHash,
                          hostDigest.observedCandidateIndexHash,
                          (caseId + " observed candidate index hash").c_str()) &&
         ok;
    return ok;
}

static std::vector<SimScanCudaInitialRunSummary> make_full_set_miss_sequence()
{
    std::vector<SimScanCudaInitialRunSummary> summaries;
    for (int index = 0; index < K + 6; ++index)
    {
        const int score = 10 + index;
        summaries.push_back(make_summary(score,
                                         1 + index,
                                         3 + index,
                                         static_cast<uint32_t>(1 + (index % 7)),
                                         static_cast<uint32_t>(index % 5),
                                         static_cast<uint32_t>(8 + (index % 11)),
                                         static_cast<uint32_t>(4 + (index % 13))));
    }
    summaries.push_back(make_summary(96, 2, 4, 9, 1, 12, 8));
    summaries.push_back(make_summary(97, 80, 81, 10, 2, 14, 9));
    return summaries;
}

} // namespace

int main()
{
    bool ok = true;

    ok = expect_shadow_replay_matches("empty_summaries",
                                      std::vector<SimScanCudaInitialRunSummary>()) &&
         ok;

    ok = expect_shadow_replay_matches(
             "single_insert",
             std::vector<SimScanCudaInitialRunSummary>{
                 make_summary(17, 1, 1, 2, 1, 3, 3)}) &&
         ok;

    ok = expect_shadow_replay_matches(
             "existing_candidate_hit",
             std::vector<SimScanCudaInitialRunSummary>{
                 make_summary(12, 2, 2, 2, 1, 4, 3),
                 make_summary(18, 2, 2, 5, 0, 7, 6),
                 make_summary(11, 2, 2, 7, 0, 9, 6)}) &&
         ok;

    ok = expect_shadow_replay_matches("full_set_miss_replacement",
                                      make_full_set_miss_sequence()) &&
         ok;

    ok = expect_shadow_replay_matches(
             "running_min_changes",
             std::vector<SimScanCudaInitialRunSummary>{
                 make_summary(50, 1, 4, 3, 0, 3, 3),
                 make_summary(30, 2, 4, 4, 0, 4, 4),
                 make_summary(70, 3, 4, 5, 1, 5, 5),
                 make_summary(40, 4, 4, 6, 1, 6, 6)}) &&
         ok;

    ok = expect_shadow_replay_matches(
             "tie_breaking",
             std::vector<SimScanCudaInitialRunSummary>{
                 make_summary(22, 4, 1, 2, 1, 2, 2),
                 make_summary(22, 3, 1, 2, 1, 3, 2),
                 make_summary(22, 4, 1, 5, 0, 5, 5),
                 make_summary(22, 5, 1, 1, 0, 6, 1)}) &&
         ok;

    ok = expect_shadow_replay_matches(
             "victim_key_reappears",
             std::vector<SimScanCudaInitialRunSummary>{
                 make_summary(10, 1, 1, 2, 0, 2, 2),
                 make_summary(11, 1, 2, 2, 0, 2, 2),
                 make_summary(12, 1, 3, 2, 0, 2, 2),
                 make_summary(80, 50, 50, 9, 3, 9, 9),
                 make_summary(81, 1, 1, 10, 2, 11, 10)}) &&
         ok;

    ok = expect_shadow_replay_matches(
             "mixed_ordered_sequence",
             std::vector<SimScanCudaInitialRunSummary>{
                 make_summary(17, 1, 1, 3, 2, 4, 4),
                 make_summary(13, 1, 2, 1, 4, 6, 5),
                 make_summary(8, 2, 1, 2, 1, 4, 1),
                 make_summary(16, 3, 3, 3, 3, 3, 3),
                 make_summary(11, 1, 2, 4, 0, 7, 2)}) &&
         ok;

    const std::vector<SimScanCudaInitialRunSummary> ordered = make_full_set_miss_sequence();
    std::vector<SimScanCudaInitialRunSummary> reversed = ordered;
    std::reverse(reversed.begin(), reversed.end());
    SimKernelContext initialContext = make_context();
    const SimOrderedMaintenanceHostDigest hostDigest =
        host_digest_for_summaries(ordered, true);
    const SimOrderedMaintenanceHostDigest reversedShadowDigest =
        replaySimOrderedMaintenanceIndependentShadowDigest(
            reversed,
            static_cast<uint64_t>(reversed.size() * 3),
            initialContext,
            true);
    const SimOrderedMaintenanceShadowReplayComparison mismatch =
        compareSimOrderedMaintenanceShadowDigests("intentional_reverse",
                                                  static_cast<uint64_t>(ordered.size()),
                                                  hostDigest,
                                                  reversedShadowDigest);
    ok = expect_true(mismatch.mismatchCount > 0, "intentional mismatch count") && ok;
    ok = expect_equal_string(mismatch.shadowStatus, "mismatch", "intentional mismatch status") && ok;
    ok = expect_equal_string(mismatch.firstMismatchCaseId,
                             "intentional_reverse",
                             "intentional mismatch case id") &&
         ok;
    ok = expect_true(!mismatch.firstMismatchKind.empty(),
                     "intentional mismatch kind set") &&
         ok;

    return ok ? 0 : 1;
}
