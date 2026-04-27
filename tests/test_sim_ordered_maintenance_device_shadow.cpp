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

static bool expect_device_candidate_digest_matches(
    const std::string &caseId,
    const std::vector<SimScanCudaInitialRunSummary> &summaries)
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
                          (caseId + " device running min hash").c_str()) &&
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
