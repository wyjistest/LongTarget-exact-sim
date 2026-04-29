#include <climits>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "../cuda/sim_scan_cuda.h"
#include "sim_frontier_epoch_oracle_helpers.h"

namespace
{

static const char *kArtifactDir = ".tmp/gpu_candidate_frontier_epoch_shadow_2026-04-29";

struct ShadowCaseReport
{
    std::string name;
    size_t summaryCount;
    size_t epochCount;
    size_t liveEpochCount;
    size_t candidateCount;
    size_t materializedSafeStoreCount;
    size_t prunedSafeStoreCount;
    int runningMin;
    bool candidateExact;
    bool runningMinExact;
    bool materializedSafeStoreExact;
    bool prunedSafeStoreExact;
    bool exact;
};

static void make_full_row_interval_filter(int queryLength,
                                          int targetLength,
                                          std::vector<int> &rowOffsets,
                                          std::vector<SimScanCudaColumnInterval> &intervals)
{
    rowOffsets.assign(static_cast<size_t>(queryLength + 2), 0);
    intervals.clear();
    intervals.reserve(static_cast<size_t>(queryLength));
    for (int row = 1; row <= queryLength; ++row)
    {
        rowOffsets[static_cast<size_t>(row)] = static_cast<int>(intervals.size());
        intervals.push_back(SimScanCudaColumnInterval(1, targetLength));
    }
    rowOffsets[static_cast<size_t>(queryLength + 1)] = static_cast<int>(intervals.size());
}

static bool download_persistent_store_states(const SimCudaPersistentSafeStoreHandle &handle,
                                             std::vector<SimScanCudaCandidateState> *outStates,
                                             std::string *errorOut)
{
    if (outStates == NULL)
    {
        if (errorOut != NULL)
        {
            *errorOut = "missing persistent store download output";
        }
        return false;
    }
    outStates->clear();
    if (!handle.valid || handle.stateCount == 0)
    {
        return true;
    }

    std::vector<int> rowOffsets;
    std::vector<SimScanCudaColumnInterval> intervals;
    make_full_row_interval_filter(4096, 4096, rowOffsets, intervals);
    return sim_scan_cuda_filter_persistent_safe_candidate_state_store_by_row_intervals(
        handle,
        4096,
        4096,
        rowOffsets,
        intervals,
        outStates,
        errorOut);
}

static bool build_gpu_safe_store_states(const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                        const std::vector<SimScanCudaCandidateState> &finalCandidates,
                                        int runningMin,
                                        std::vector<SimScanCudaCandidateState> *outStates,
                                        std::string *errorOut)
{
    SimCudaPersistentSafeStoreHandle handle;
    double buildSeconds = 0.0;
    double pruneSeconds = 0.0;
    double frontierUploadSeconds = 0.0;
    if (!sim_scan_cuda_build_persistent_safe_candidate_state_store_from_initial_run_summaries(
            summaries,
            finalCandidates,
            runningMin,
            &handle,
            &buildSeconds,
            &pruneSeconds,
            &frontierUploadSeconds,
            errorOut))
    {
        return false;
    }

    const bool ok = download_persistent_store_states(handle, outStates, errorOut);
    sim_scan_cuda_release_persistent_safe_candidate_state_store(&handle);
    return ok;
}

static bool analyze_shadow_case(const sim_frontier_epoch_test::TestCase &test,
                                ShadowCaseReport &report,
                                std::vector<std::string> &mismatches)
{
    const sim_frontier_epoch_test::FrontierOracleResult oracle =
        sim_frontier_epoch_test::build_frontier_epoch_oracle(test.summaries);

    std::vector<uint64_t> summaryEpochIds;
    std::vector<uint64_t> liveEpochIds;
    sim_frontier_epoch_test::collect_summary_epoch_ids(oracle,
                                                       test.summaries.size(),
                                                       summaryEpochIds);
    sim_frontier_epoch_test::collect_live_epoch_ids(oracle, liveEpochIds);

    bool ok = true;
    for (size_t i = 0; i < summaryEpochIds.size(); ++i)
    {
        if (summaryEpochIds[i] == 0)
        {
            std::ostringstream detail;
            detail << "summary " << i << " did not receive an epoch id";
            sim_frontier_epoch_test::add_mismatch(mismatches, test.name, "summary_epoch_ids", detail.str());
            ok = false;
        }
    }

    std::vector<SimScanCudaCandidateState> gpuFrontierStates;
    int gpuRunningMin = 0;
    std::string error;
    if (!sim_scan_cuda_reduce_frontier_epoch_shadow_for_test(test.summaries,
                                                             summaryEpochIds,
                                                             liveEpochIds,
                                                             &gpuFrontierStates,
                                                             &gpuRunningMin,
                                                             &error))
    {
        sim_frontier_epoch_test::add_mismatch(mismatches, test.name, "gpu_shadow_call", error);
        ok = false;
    }

    const bool candidateExact =
        sim_frontier_epoch_test::expect_state_vectors_equal(gpuFrontierStates,
                                                            oracle.frontierStates,
                                                            test.name,
                                                            "candidateStates",
                                                            mismatches);
    ok = candidateExact && ok;

    const bool runningMinExact = gpuRunningMin == oracle.runningMin;
    if (!runningMinExact)
    {
        std::ostringstream detail;
        detail << "runningMin expected " << oracle.runningMin
               << ", got " << gpuRunningMin;
        sim_frontier_epoch_test::add_mismatch(mismatches, test.name, "runningMin", detail.str());
        ok = false;
    }

    std::vector<SimScanCudaCandidateState> expectedMaterializedSafeStoreStates;
    reduceSimCudaInitialRunSummariesToAllCandidateStates(test.summaries,
                                                         NULL,
                                                         expectedMaterializedSafeStoreStates);

    SimCudaPersistentSafeStoreHandle expectedPersistentHandle;
    SimKernelContext expectedHandoffContext(4096, 4096);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, expectedHandoffContext);
    applySimCudaInitialReduceResults(oracle.frontierStates,
                                     oracle.runningMin,
                                     expectedMaterializedSafeStoreStates,
                                     expectedPersistentHandle,
                                     static_cast<uint64_t>(test.summaries.size()),
                                     expectedHandoffContext,
                                     false,
                                     false);

    std::vector<SimScanCudaCandidateState> gpuMaterializedSafeStoreStates;
    if (!build_gpu_safe_store_states(test.summaries,
                                     std::vector<SimScanCudaCandidateState>(),
                                     INT_MIN,
                                     &gpuMaterializedSafeStoreStates,
                                     &error))
    {
        sim_frontier_epoch_test::add_mismatch(mismatches, test.name, "safe_store_materialized_call", error);
        ok = false;
    }

    const bool materializedSafeStoreExact =
        sim_frontier_epoch_test::expect_state_vectors_equal(gpuMaterializedSafeStoreStates,
                                                            expectedMaterializedSafeStoreStates,
                                                            test.name,
                                                            "safe_store_materialized",
                                                            mismatches);
    ok = materializedSafeStoreExact && ok;

    std::vector<SimScanCudaCandidateState> gpuPrunedSafeStoreStates;
    if (!build_gpu_safe_store_states(test.summaries,
                                     gpuFrontierStates,
                                     gpuRunningMin,
                                     &gpuPrunedSafeStoreStates,
                                     &error))
    {
        sim_frontier_epoch_test::add_mismatch(mismatches, test.name, "safe_store_pruned_call", error);
        ok = false;
    }

    const bool prunedSafeStoreExact =
        sim_frontier_epoch_test::expect_state_vectors_equal(gpuPrunedSafeStoreStates,
                                                            expectedHandoffContext.safeCandidateStateStore.states,
                                                            test.name,
                                                            "safe_store_pruned",
                                                            mismatches);
    ok = prunedSafeStoreExact && ok;

    report.name = test.name;
    report.summaryCount = test.summaries.size();
    report.epochCount = oracle.epochs.size();
    report.liveEpochCount = oracle.liveEpochCount;
    report.candidateCount = gpuFrontierStates.size();
    report.materializedSafeStoreCount = gpuMaterializedSafeStoreStates.size();
    report.prunedSafeStoreCount = gpuPrunedSafeStoreStates.size();
    report.runningMin = gpuRunningMin;
    report.candidateExact = candidateExact;
    report.runningMinExact = runningMinExact;
    report.materializedSafeStoreExact = materializedSafeStoreExact;
    report.prunedSafeStoreExact = prunedSafeStoreExact;
    report.exact = ok;
    return ok;
}

static bool write_mismatches(const std::vector<std::string> &mismatches)
{
    const std::string path = std::string(kArtifactDir) + "/frontier_epoch_shadow_mismatches.jsonl";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }
    for (size_t i = 0; i < mismatches.size(); ++i)
    {
        out << mismatches[i] << "\n";
    }
    return true;
}

static bool write_summary(const std::vector<ShadowCaseReport> &reports,
                          size_t mismatchCount,
                          bool allExact)
{
    const std::string path = std::string(kArtifactDir) + "/frontier_epoch_shadow_summary.json";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }

    size_t totalSummaries = 0;
    size_t totalEpochs = 0;
    size_t totalLiveEpochs = 0;
    for (size_t i = 0; i < reports.size(); ++i)
    {
        totalSummaries += reports[i].summaryCount;
        totalEpochs += reports[i].epochCount;
        totalLiveEpochs += reports[i].liveEpochCount;
    }

    out << "{\n";
    out << "  \"artifact\":\"frontier_epoch_shadow\",\n";
    out << "  \"truth_source\":\"cpu_frontier_epoch_oracle\",\n";
    out << "  \"gpu_shadow_implemented\":true,\n";
    out << "  \"runtime_prototype_allowed\":false,\n";
    out << "  \"default_path_changes_allowed\":false,\n";
    out << "  \"cases_total\":" << reports.size() << ",\n";
    out << "  \"summaries_total\":" << totalSummaries << ",\n";
    out << "  \"epochs_total\":" << totalEpochs << ",\n";
    out << "  \"live_epochs_total\":" << totalLiveEpochs << ",\n";
    out << "  \"mismatch_count\":" << mismatchCount << ",\n";
    out << "  \"all_exact\":" << (allExact ? "true" : "false") << ",\n";
    out << "  \"frontier_shadow_scope\":\"summary_epoch_ids_to_live_frontier_states_only\",\n";
    out << "  \"safe_store_scope\":\"existing_all_state_grouped_reducer_only\",\n";
    out << "  \"cases\":[\n";
    for (size_t i = 0; i < reports.size(); ++i)
    {
        const ShadowCaseReport &report = reports[i];
        out << "    {"
            << "\"name\":\"" << sim_frontier_epoch_test::json_escape(report.name) << "\","
            << "\"summary_count\":" << report.summaryCount << ","
            << "\"epoch_count\":" << report.epochCount << ","
            << "\"live_epoch_count\":" << report.liveEpochCount << ","
            << "\"candidate_count\":" << report.candidateCount << ","
            << "\"materialized_safe_store_count\":" << report.materializedSafeStoreCount << ","
            << "\"pruned_safe_store_count\":" << report.prunedSafeStoreCount << ","
            << "\"running_min\":" << report.runningMin << ","
            << "\"candidate_exact\":" << (report.candidateExact ? "true" : "false") << ","
            << "\"running_min_exact\":" << (report.runningMinExact ? "true" : "false") << ","
            << "\"materialized_safe_store_exact\":" << (report.materializedSafeStoreExact ? "true" : "false") << ","
            << "\"pruned_safe_store_exact\":" << (report.prunedSafeStoreExact ? "true" : "false") << ","
            << "\"exact\":" << (report.exact ? "true" : "false")
            << "}";
        if (i + 1 != reports.size())
        {
            out << ",";
        }
        out << "\n";
    }
    out << "  ]\n";
    out << "}\n";
    return true;
}

static bool write_decision(size_t mismatchCount)
{
    const std::string path = std::string(kArtifactDir) + "/anti_loop_decision.json";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }

    const std::string decision =
        mismatchCount == 0 ?
        "design_epoch_labeling_strategy" :
        "fix_gpu_frontier_epoch_shadow_mismatch";
    const std::string reason =
        mismatchCount == 0 ?
        "GPU frontier epoch shadow matched CPU truth for candidateStates, runningMin, and safe-store composition" :
        "GPU frontier epoch shadow or safe-store composition mismatched CPU truth";

    out << "{\n";
    out << "  \"decision\":\"" << decision << "\",\n";
    out << "  \"allowed_decisions\":["
        << "\"fix_gpu_frontier_epoch_shadow_mismatch\","
        << "\"design_epoch_labeling_strategy\","
        << "\"stop_gpu_frontier_epoch_reduce_return_to_context_apply_or_partial_safe_store\"],\n";
    out << "  \"reason\":\"" << sim_frontier_epoch_test::json_escape(reason) << "\",\n";
    out << "  \"runtime_prototype_allowed\":false,\n";
    out << "  \"default_path_changes_allowed\":false,\n";
    out << "  \"next_step_only\":true\n";
    out << "}\n";
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

    if (!sim_frontier_epoch_test::ensure_directory(".tmp") ||
        !sim_frontier_epoch_test::ensure_directory(kArtifactDir))
    {
        return 1;
    }

    const std::vector<sim_frontier_epoch_test::TestCase> tests =
        sim_frontier_epoch_test::make_frontier_epoch_test_cases();
    std::vector<std::string> mismatches;
    std::vector<ShadowCaseReport> reports;
    reports.reserve(tests.size());

    bool ok = true;
    for (size_t i = 0; i < tests.size(); ++i)
    {
        ShadowCaseReport report;
        const bool caseOk = analyze_shadow_case(tests[i], report, mismatches);
        reports.push_back(report);
        ok = caseOk && ok;
    }

    ok = write_mismatches(mismatches) && ok;
    ok = write_summary(reports, mismatches.size(), mismatches.empty()) && ok;
    ok = write_decision(mismatches.size()) && ok;

    if (!mismatches.empty())
    {
        std::cerr << "frontier epoch shadow mismatches: " << mismatches.size() << "\n";
        std::cerr << "see " << kArtifactDir << "/frontier_epoch_shadow_mismatches.jsonl\n";
    }
    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
