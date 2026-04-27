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

static bool expect_equal_i64(long actual, long expected, const char *label)
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

static bool expect_ge_u64(uint64_t actual, uint64_t expected, const char *label)
{
    if (actual >= expected)
    {
        return true;
    }
    std::cerr << label << ": expected at least " << expected << ", got " << actual << "\n";
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
    const std::vector<SimScanCudaInitialRunSummary> &summaries)
{
    SimKernelContext context = make_context();
    SimOrderedMaintenanceHostDigest digest;
    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size() * 3),
                                    context,
                                    NULL,
                                    &digest);
    finalizeSimOrderedMaintenanceHostDigest(context, digest);
    return digest;
}

static std::vector<SimScanCudaInitialRunSummary> make_full_set_miss_sequence()
{
    std::vector<SimScanCudaInitialRunSummary> summaries;
    for (int index = 0; index < K + 6; ++index)
    {
        summaries.push_back(make_summary(10 + index,
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

static std::vector<SimScanCudaInitialRunSummary> make_full_candidate_seed_sequence(
    int scoreBase,
    bool tieScores)
{
    std::vector<SimScanCudaInitialRunSummary> summaries;
    for (int index = 0; index < K; ++index)
    {
        const int score = tieScores ? scoreBase : scoreBase + index;
        summaries.push_back(make_summary(score,
                                         100 + index,
                                         200 + index,
                                         static_cast<uint32_t>(3 + (index % 9)),
                                         static_cast<uint32_t>(1 + (index % 5)),
                                         static_cast<uint32_t>(8 + (index % 13)),
                                         static_cast<uint32_t>(6 + (index % 17))));
    }
    return summaries;
}

static std::vector<SimScanCudaInitialRunSummary> make_single_replacement_sequence()
{
    std::vector<SimScanCudaInitialRunSummary> summaries =
        make_full_candidate_seed_sequence(30, false);
    summaries.push_back(make_summary(120, 500, 600, 11, 2, 16, 14));
    return summaries;
}

static std::vector<SimScanCudaInitialRunSummary> make_multiple_replacement_sequence()
{
    std::vector<SimScanCudaInitialRunSummary> summaries =
        make_full_candidate_seed_sequence(40, false);
    for (int index = 0; index < 4; ++index)
    {
        summaries.push_back(make_summary(140 + index,
                                         700 + index,
                                         800 + index,
                                         static_cast<uint32_t>(12 + index),
                                         static_cast<uint32_t>(2 + index),
                                         static_cast<uint32_t>(18 + index),
                                         static_cast<uint32_t>(15 + index)));
    }
    return summaries;
}

static std::vector<SimScanCudaInitialRunSummary> make_tie_replacement_sequence()
{
    std::vector<SimScanCudaInitialRunSummary> summaries =
        make_full_candidate_seed_sequence(55, true);
    summaries.push_back(make_summary(55, 900, 901, 13, 3, 19, 16));
    return summaries;
}

static std::vector<SimScanCudaInitialRunSummary> make_victim_reappears_replacement_sequence()
{
    std::vector<SimScanCudaInitialRunSummary> summaries =
        make_full_candidate_seed_sequence(60, false);
    const SimScanCudaInitialRunSummary victim = summaries.front();
    summaries.push_back(make_summary(180, 1000, 1001, 14, 4, 20, 17));
    summaries.push_back(make_summary(181,
                                     static_cast<long>(victim.startCoord >> 32),
                                     static_cast<long>(victim.startCoord & 0xffffffffULL),
                                     15,
                                     5,
                                     21,
                                     18));
    return summaries;
}

static std::vector<SimScanCudaInitialRunSummary> make_running_min_changes_multiple_sequence()
{
    return std::vector<SimScanCudaInitialRunSummary>{
        make_summary(40, 10, 10, 2, 1, 3, 3),
        make_summary(20, 11, 10, 3, 1, 4, 4),
        make_summary(60, 12, 10, 4, 1, 5, 5),
        make_summary(10, 13, 10, 5, 1, 6, 6)};
}

static std::vector<SimScanCudaInitialRunSummary> make_running_min_slot_changes_after_replacement_sequence()
{
    std::vector<SimScanCudaInitialRunSummary> summaries =
        make_full_candidate_seed_sequence(70, false);
    summaries.push_back(make_summary(180, 1100, 1101, 16, 6, 22, 19));
    return summaries;
}

static std::vector<SimScanCudaInitialRunSummary> make_running_min_slot_tie_break_sequence()
{
    std::vector<SimScanCudaInitialRunSummary> summaries =
        make_full_candidate_seed_sequence(55, true);
    summaries.push_back(make_summary(75, 100, 200, 17, 7, 23, 20));
    return summaries;
}

static std::vector<SimScanCudaInitialRunSummary> make_replacement_without_running_min_change_sequence()
{
    std::vector<SimScanCudaInitialRunSummary> summaries =
        make_full_candidate_seed_sequence(65, true);
    summaries.push_back(make_summary(65, 1200, 1201, 18, 8, 24, 21));
    return summaries;
}

static std::vector<SimScanCudaInitialRunSummary> make_mixed_running_min_and_replacement_sequence()
{
    std::vector<SimScanCudaInitialRunSummary> summaries =
        make_running_min_changes_multiple_sequence();
    std::vector<SimScanCudaInitialRunSummary> seed =
        make_full_candidate_seed_sequence(90, false);
    summaries.insert(summaries.end(), seed.begin(), seed.end());
    summaries.push_back(make_summary(95, 100, 200, 19, 9, 25, 22));
    summaries.push_back(make_summary(210, 1300, 1301, 20, 10, 26, 23));
    return summaries;
}

static std::vector<SimScanCudaInitialRunSummary> make_insert_then_existing_hit_sequence()
{
    return std::vector<SimScanCudaInitialRunSummary>{
        make_summary(20, 1400, 1401, 21, 11, 27, 24),
        make_summary(25, 1400, 1401, 22, 10, 28, 25)};
}

static std::vector<SimScanCudaInitialRunSummary> make_victim_key_not_visible_after_eviction_sequence()
{
    std::vector<SimScanCudaInitialRunSummary> summaries =
        make_full_candidate_seed_sequence(100, false);
    const SimScanCudaInitialRunSummary victim = summaries.front();
    summaries.push_back(make_summary(220, 1500, 1501, 23, 12, 29, 26));
    summaries.push_back(make_summary(221,
                                     static_cast<long>(victim.startCoord >> 32),
                                     static_cast<long>(victim.startCoord & 0xffffffffULL),
                                     24,
                                     13,
                                     30,
                                     27));
    return summaries;
}

static std::vector<SimScanCudaInitialRunSummary> make_hit_miss_interleaving_sequence()
{
    return std::vector<SimScanCudaInitialRunSummary>{
        make_summary(31, 1600, 1601, 25, 14, 31, 28),
        make_summary(32, 1601, 1602, 26, 15, 32, 29),
        make_summary(33, 1600, 1601, 27, 13, 33, 30),
        make_summary(34, 1602, 1603, 28, 16, 34, 31),
        make_summary(35, 1601, 1602, 29, 14, 35, 32)};
}

static bool expect_device_candidate_digest_matches(
    const std::string &caseId,
    const std::vector<SimScanCudaInitialRunSummary> &summaries,
    uint64_t minRunningMinUpdateCount = 0,
    uint64_t minRunningMinSlotUpdateCount = 0,
    uint64_t minFloorChangeCount = 0,
    uint64_t minVisibilityHitCount = 0,
    uint64_t minVisibilityMissCount = 0,
    uint64_t minVisibilityInsertCount = 0,
    uint64_t minVisibilityEraseCount = 0)
{
    const uint64_t logicalEventCount = static_cast<uint64_t>(summaries.size() * 3);
    SimKernelContext initialContext = make_context();
    const SimOrderedMaintenanceHostDigest hostDigest =
        host_digest_for_summaries(summaries);
    const SimOrderedMaintenanceHostDigest cpuShadowDigest =
        replaySimOrderedMaintenanceIndependentShadowDigest(summaries,
                                                           logicalEventCount,
                                                           initialContext,
                                                           false);
    SimOrderedMaintenanceHostDigest deviceShadowDigest;
    std::string error;
    bool ok = expect_true(
        replaySimOrderedMaintenanceDeviceShadowCandidateDigestForTest(summaries,
                                                                      logicalEventCount,
                                                                      &deviceShadowDigest,
                                                                      &error),
        error.empty() ? (caseId + " device shadow replay").c_str() : error.c_str());

    ok = expect_equal_u64(cpuShadowDigest.finalCandidateStateHash,
                          hostDigest.finalCandidateStateHash,
                          (caseId + " CPU shadow final hash").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.replacementSequenceHash,
                          hostDigest.replacementSequenceHash,
                          (caseId + " CPU shadow replacement sequence hash").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.candidateReplacementCount,
                          hostDigest.candidateReplacementCount,
                          (caseId + " CPU shadow replacement count").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.runningMinUpdateSequenceHash,
                          hostDigest.runningMinUpdateSequenceHash,
                          (caseId + " CPU shadow running min sequence hash").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.runningMinSlotUpdateSequenceHash,
                          hostDigest.runningMinSlotUpdateSequenceHash,
                          (caseId + " CPU shadow running min slot sequence hash").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.floorChangeSequenceHash,
                          hostDigest.floorChangeSequenceHash,
                          (caseId + " CPU shadow floor change sequence hash").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.runningMinUpdateCount,
                          hostDigest.runningMinUpdateCount,
                          (caseId + " CPU shadow running min update count").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.runningMinSlotUpdateCount,
                          hostDigest.runningMinSlotUpdateCount,
                          (caseId + " CPU shadow running min slot update count").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.floorChangeCount,
                          hostDigest.floorChangeCount,
                          (caseId + " CPU shadow floor change count").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.candidateIndexVisibilityHash,
                          hostDigest.candidateIndexVisibilityHash,
                          (caseId + " CPU shadow candidate-index visibility hash").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.candidateIndexExistingHitCount,
                          hostDigest.candidateIndexExistingHitCount,
                          (caseId + " CPU shadow candidate-index hit count").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.candidateIndexMissCount,
                          hostDigest.candidateIndexMissCount,
                          (caseId + " CPU shadow candidate-index miss count").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.candidateIndexInsertCount,
                          hostDigest.candidateIndexInsertCount,
                          (caseId + " CPU shadow candidate-index insert count").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.candidateIndexEraseCount,
                          hostDigest.candidateIndexEraseCount,
                          (caseId + " CPU shadow candidate-index erase count").c_str()) &&
         ok;
    ok = expect_equal_u64(cpuShadowDigest.candidateIndexVisibilityCheckCount,
                          hostDigest.candidateIndexVisibilityCheckCount,
                          (caseId + " CPU shadow candidate-index visibility check count").c_str()) &&
         ok;
    ok = expect_ge_u64(hostDigest.runningMinUpdateCount,
                       minRunningMinUpdateCount,
                       (caseId + " host running min update coverage").c_str()) &&
         ok;
    ok = expect_ge_u64(hostDigest.runningMinSlotUpdateCount,
                       minRunningMinSlotUpdateCount,
                       (caseId + " host running min slot update coverage").c_str()) &&
         ok;
    ok = expect_ge_u64(hostDigest.floorChangeCount,
                       minFloorChangeCount,
                       (caseId + " host floor change coverage").c_str()) &&
         ok;
    ok = expect_ge_u64(hostDigest.candidateIndexExistingHitCount,
                       minVisibilityHitCount,
                       (caseId + " host candidate-index hit coverage").c_str()) &&
         ok;
    ok = expect_ge_u64(hostDigest.candidateIndexMissCount,
                       minVisibilityMissCount,
                       (caseId + " host candidate-index miss coverage").c_str()) &&
         ok;
    ok = expect_ge_u64(hostDigest.candidateIndexInsertCount,
                       minVisibilityInsertCount,
                       (caseId + " host candidate-index insert coverage").c_str()) &&
         ok;
    ok = expect_ge_u64(hostDigest.candidateIndexEraseCount,
                       minVisibilityEraseCount,
                       (caseId + " host candidate-index erase coverage").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.candidateCount,
                          hostDigest.candidateCount,
                          (caseId + " device candidate count").c_str()) &&
         ok;
    ok = expect_equal_i64(deviceShadowDigest.runningMin,
                          hostDigest.runningMin,
                          (caseId + " device runningMin").c_str()) &&
         ok;
    ok = expect_equal_i64(deviceShadowDigest.runningMinSlot,
                          hostDigest.runningMinSlot,
                          (caseId + " device runningMinSlot").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.finalCandidateStateHash,
                          hostDigest.finalCandidateStateHash,
                          (caseId + " device final candidate state hash").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.replacementSequenceHash,
                          hostDigest.replacementSequenceHash,
                          (caseId + " device replacement sequence hash").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.candidateReplacementCount,
                          hostDigest.candidateReplacementCount,
                          (caseId + " device replacement count").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.candidateSlotKeyHash,
                          hostDigest.candidateSlotKeyHash,
                          (caseId + " device candidate slot key hash").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.candidateSlotScoreHash,
                          hostDigest.candidateSlotScoreHash,
                          (caseId + " device candidate slot score hash").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.candidateSlotGenerationHash,
                          hostDigest.candidateSlotGenerationHash,
                          (caseId + " device candidate slot generation hash").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.summaryOrdinalHash,
                          hostDigest.summaryOrdinalHash,
                          (caseId + " device summary ordinal hash").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.runningMinUpdateSequenceHash,
                          hostDigest.runningMinUpdateSequenceHash,
                          (caseId + " device running min sequence hash").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.runningMinSlotUpdateSequenceHash,
                          hostDigest.runningMinSlotUpdateSequenceHash,
                          (caseId + " device running min slot sequence hash").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.floorChangeSequenceHash,
                          hostDigest.floorChangeSequenceHash,
                          (caseId + " device floor change sequence hash").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.runningMinUpdateCount,
                          hostDigest.runningMinUpdateCount,
                          (caseId + " device running min update count").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.runningMinSlotUpdateCount,
                          hostDigest.runningMinSlotUpdateCount,
                          (caseId + " device running min slot update count").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.floorChangeCount,
                          hostDigest.floorChangeCount,
                          (caseId + " device floor change count").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.candidateIndexVisibilityHash,
                          hostDigest.candidateIndexVisibilityHash,
                          (caseId + " device candidate-index visibility hash").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.candidateIndexExistingHitCount,
                          hostDigest.candidateIndexExistingHitCount,
                          (caseId + " device candidate-index hit count").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.candidateIndexMissCount,
                          hostDigest.candidateIndexMissCount,
                          (caseId + " device candidate-index miss count").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.candidateIndexInsertCount,
                          hostDigest.candidateIndexInsertCount,
                          (caseId + " device candidate-index insert count").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.candidateIndexEraseCount,
                          hostDigest.candidateIndexEraseCount,
                          (caseId + " device candidate-index erase count").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.candidateIndexVisibilityCheckCount,
                          hostDigest.candidateIndexVisibilityCheckCount,
                          (caseId + " device candidate-index visibility check count").c_str()) &&
         ok;
    ok = expect_equal_u64(deviceShadowDigest.candidateStateHandoffHash,
                          hostDigest.candidateStateHandoffHash,
                          (caseId + " device handoff hash").c_str()) &&
         ok;
    return ok;
}

} // namespace

int main()
{
    bool ok = true;

    ok = expect_device_candidate_digest_matches(
             "running_min_no_change",
             std::vector<SimScanCudaInitialRunSummary>()) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "running_min_changes_once",
             std::vector<SimScanCudaInitialRunSummary>{
                 make_summary(17, 1, 1, 2, 1, 3, 3)},
             1,
             1,
             1) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "running_min_changes_multiple_times",
             make_running_min_changes_multiple_sequence(),
             3,
             2,
             3) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "running_min_slot_changes_after_replacement",
             make_running_min_slot_changes_after_replacement_sequence(),
             2,
             2,
             2) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "running_min_slot_tie_break",
             make_running_min_slot_tie_break_sequence(),
             1,
             2,
             1) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "replacement_without_running_min_change",
             make_replacement_without_running_min_change_sequence()) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "victim_reappears_with_floor_change",
             make_victim_reappears_replacement_sequence(),
             2,
             2,
             2) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "mixed_sequence_running_min_and_replacement",
             make_mixed_running_min_and_replacement_sequence(),
             3,
             3,
             3,
             1,
             55,
             55,
             5) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "insert_then_existing_hit",
             make_insert_then_existing_hit_sequence(),
             1,
             1,
             1,
             1,
             1,
             1,
             0) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "victim_key_not_visible_after_eviction",
             make_victim_key_not_visible_after_eviction_sequence(),
             2,
             2,
             2,
             0,
             52,
             52,
             2) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "hit_miss_interleaving",
             make_hit_miss_interleaving_sequence(),
             1,
             1,
             1,
             2,
             3,
             3,
             0) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "empty_summaries",
             std::vector<SimScanCudaInitialRunSummary>()) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "single_insert",
             std::vector<SimScanCudaInitialRunSummary>{
                 make_summary(17, 1, 1, 2, 1, 3, 3)}) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "existing_candidate_hit",
             std::vector<SimScanCudaInitialRunSummary>{
                 make_summary(12, 2, 2, 2, 1, 4, 3),
                 make_summary(18, 2, 2, 5, 0, 7, 6),
                 make_summary(11, 2, 2, 7, 0, 9, 6)}) &&
         ok;
    ok = expect_device_candidate_digest_matches("full_set_miss_replacement",
                                                make_full_set_miss_sequence()) &&
         ok;
    ok = expect_device_candidate_digest_matches("replacement_sequence_single_miss",
                                                make_single_replacement_sequence()) &&
         ok;
    ok = expect_device_candidate_digest_matches("replacement_sequence_multiple_misses",
                                                make_multiple_replacement_sequence()) &&
         ok;
    ok = expect_device_candidate_digest_matches("replacement_sequence_tie_break",
                                                make_tie_replacement_sequence()) &&
         ok;
    ok = expect_device_candidate_digest_matches("replacement_sequence_victim_reappears",
                                                make_victim_reappears_replacement_sequence()) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "running_min_changes",
             std::vector<SimScanCudaInitialRunSummary>{
                 make_summary(50, 1, 4, 3, 0, 3, 3),
                 make_summary(30, 2, 4, 4, 0, 4, 4),
                 make_summary(70, 3, 4, 5, 1, 5, 5),
                 make_summary(40, 4, 4, 6, 1, 6, 6)}) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "tie_breaking",
             std::vector<SimScanCudaInitialRunSummary>{
                 make_summary(22, 4, 1, 2, 1, 2, 2),
                 make_summary(22, 3, 1, 2, 1, 3, 2),
                 make_summary(22, 4, 1, 5, 0, 5, 5),
                 make_summary(22, 5, 1, 1, 0, 6, 1)}) &&
         ok;
    ok = expect_device_candidate_digest_matches(
             "victim_key_reappears",
             std::vector<SimScanCudaInitialRunSummary>{
                 make_summary(10, 1, 1, 2, 0, 2, 2),
                 make_summary(11, 1, 2, 2, 0, 2, 2),
                 make_summary(12, 1, 3, 2, 0, 2, 2),
                 make_summary(80, 50, 50, 9, 3, 9, 9),
                 make_summary(81, 1, 1, 10, 2, 11, 10)}) &&
         ok;

    return ok ? 0 : 1;
}
