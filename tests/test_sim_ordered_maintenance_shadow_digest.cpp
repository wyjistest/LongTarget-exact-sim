#include <cstdlib>
#include <fstream>
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

static bool expect_not_equal_u64(uint64_t actual, uint64_t expected, const char *label)
{
    if (actual != expected)
    {
        return true;
    }
    std::cerr << label << ": expected values to differ, both were " << actual << "\n";
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

static std::string make_temp_dir()
{
    char buffer[] = "/tmp/longtarget-shadow-digest-XXXXXX";
    char *created = mkdtemp(buffer);
    if (created == NULL)
    {
        return std::string();
    }
    return std::string(created);
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

static SimOrderedMaintenanceHostDigest digest_for_summaries(
    const std::vector<SimScanCudaInitialRunSummary> &summaries)
{
    SimKernelContext context(64, 128);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);

    SimOrderedMaintenanceHostDigest digest;
    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size() * 3),
                                    context,
                                    NULL,
                                    &digest);
    mergeSimCudaInitialRunSummariesIntoSafeStore(summaries, context);
    pruneSimSafeCandidateStateStore(context);
    finalizeSimOrderedMaintenanceHostDigest(context, digest);
    return digest;
}

} // namespace

int main()
{
    bool ok = true;

    std::vector<SimScanCudaInitialRunSummary> summaries;
    summaries.push_back(make_summary(17, 1, 1, 3, 2, 4, 4));
    summaries.push_back(make_summary(13, 1, 2, 1, 4, 6, 5));
    summaries.push_back(make_summary(8, 2, 1, 2, 1, 4, 1));
    summaries.push_back(make_summary(16, 3, 3, 3, 3, 3, 3));
    summaries.push_back(make_summary(11, 1, 2, 4, 0, 7, 2));

    SimOrderedMaintenanceHostDigest digestA = digest_for_summaries(summaries);
    SimOrderedMaintenanceHostDigest digestB = digest_for_summaries(summaries);
    ok = expect_equal_u64(digestA.finalCandidateStateHash,
                          digestB.finalCandidateStateHash,
                          "digest stable final candidate state") &&
         ok;
    ok = expect_equal_u64(digestA.replacementSequenceHash,
                          digestB.replacementSequenceHash,
                          "digest stable replacement sequence") &&
         ok;
    ok = expect_equal_u64(digestA.runningMinUpdateSequenceHash,
                          digestB.runningMinUpdateSequenceHash,
                          "digest stable runningMin sequence") &&
         ok;
    ok = expect_equal_u64(digestA.safeStoreStateHash,
                          digestB.safeStoreStateHash,
                          "digest stable safe-store state") &&
         ok;
    ok = expect_equal_u64(digestA.candidateCount, 4, "host digest candidate count") && ok;
    ok = expect_true(digestA.finalCandidateStateHash != 0,
                     "host digest final candidate hash recorded") &&
         ok;

    std::vector<SimScanCudaInitialRunSummary> changed = summaries;
    changed[1].score += 7;
    SimOrderedMaintenanceHostDigest digestChanged = digest_for_summaries(changed);
    ok = expect_not_equal_u64(digestChanged.finalCandidateStateHash,
                              digestA.finalCandidateStateHash,
                              "digest changes on state change") &&
         ok;
    ok = expect_not_equal_u64(digestChanged.summaryOrdinalHash,
                              digestA.summaryOrdinalHash,
                              "summary ordinal digest changes on input change") &&
         ok;

    const std::string tempDir = make_temp_dir();
    ok = expect_true(!tempDir.empty(), "temporary digest directory created") && ok;
    const std::string digestPath = tempDir + "/host_ordered_maintenance_digest.json";
    std::string error;
    ok = expect_true(writeSimOrderedMaintenanceHostDigestJson(digestPath, digestA, &error),
                     error.empty() ? "writeSimOrderedMaintenanceHostDigestJson" : error.c_str()) &&
         ok;
    std::ifstream digestInput(digestPath.c_str());
    const std::string digestJson((std::istreambuf_iterator<char>(digestInput)),
                                 std::istreambuf_iterator<char>());
    ok = expect_true(digestJson.find("\"final_candidate_state_hash\"") != std::string::npos,
                     "digest json final_candidate_state_hash") &&
         ok;
    ok = expect_true(digestJson.find("\"replacement_sequence_hash\"") != std::string::npos,
                     "digest json replacement_sequence_hash") &&
         ok;
    ok = expect_true(digestJson.find("\"running_min_update_count\"") != std::string::npos,
                     "digest json running_min_update_count") &&
         ok;
    ok = expect_true(digestJson.find("\"running_min_slot_update_count\"") != std::string::npos,
                     "digest json running_min_slot_update_count") &&
         ok;
    ok = expect_true(digestJson.find("\"floor_change_count\"") != std::string::npos,
                     "digest json floor_change_count") &&
         ok;
    ok = expect_true(digestJson.find("\"candidate_index_visibility_check_count\"") != std::string::npos,
                     "digest json candidate_index_visibility_check_count") &&
         ok;
    ok = expect_true(digestJson.find("\"candidate_index_insert_count\"") != std::string::npos,
                     "digest json candidate_index_insert_count") &&
         ok;
    ok = expect_true(digestJson.find("\"safe_store_state_hash\"") != std::string::npos,
                     "digest json safe_store_state_hash") &&
         ok;
    ok = expect_true(digestJson.find("\"safe_store_state_count\"") != std::string::npos,
                     "digest json safe_store_state_count") &&
         ok;
    ok = expect_true(digestJson.find("\"candidate_state_handoff_count\"") != std::string::npos,
                     "digest json candidate_state_handoff_count") &&
         ok;

    SimDeviceOrderedMaintenanceShadowValidationSnapshot snapshot =
        currentSimDeviceOrderedMaintenanceShadowValidationSnapshot();
    ok = expect_true(!snapshot.shadowEnabled, "shadow disabled by default") && ok;
    ok = expect_true(!snapshot.shadowValidateEnabled, "shadow validate disabled by default") && ok;
    ok = expect_equal_string(snapshot.shadowStatus, "disabled", "shadow default status") && ok;
    ok = expect_equal_u64(snapshot.shadowMismatchCount, 0, "shadow default mismatch count") && ok;

    recordSimDeviceOrderedMaintenanceShadowHostDigest(digestA, summaries.size(),
                                                      static_cast<uint64_t>(summaries.size() * 3),
                                                      0.0);
    snapshot = currentSimDeviceOrderedMaintenanceShadowValidationSnapshot();
    ok = expect_equal_u64(snapshot.shadowCaseCount, 1, "shadow host digest case count") && ok;
    ok = expect_equal_u64(snapshot.shadowSummaryCount, summaries.size(), "shadow host digest summary count") && ok;
    ok = expect_equal_u64(snapshot.hostFinalCandidateStateHash,
                          digestA.finalCandidateStateHash,
                          "snapshot host final candidate hash") &&
         ok;

    return ok ? 0 : 1;
}
