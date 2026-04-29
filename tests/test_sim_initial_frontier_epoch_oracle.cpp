#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "sim_frontier_epoch_oracle_helpers.h"

namespace
{

static const char *kArtifactDir = ".tmp/gpu_candidate_frontier_epoch_oracle_2026-04-29";

using sim_frontier_epoch_test::CaseReport;
using sim_frontier_epoch_test::json_escape;

static bool write_mismatches(const std::vector<std::string> &mismatches)
{
    const std::string path = std::string(kArtifactDir) + "/frontier_epoch_mismatches.jsonl";
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

static bool write_summary(const std::vector<CaseReport> &reports,
                          size_t mismatchCount,
                          bool allExact,
                          bool allChunkable)
{
    const std::string path = std::string(kArtifactDir) + "/frontier_epoch_summary.json";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }

    size_t totalSummaries = 0;
    size_t totalTrace = 0;
    size_t totalEpochs = 0;
    size_t totalLiveEpochs = 0;
    for (size_t i = 0; i < reports.size(); ++i)
    {
        totalSummaries += reports[i].summaryCount;
        totalTrace += reports[i].traceCount;
        totalEpochs += reports[i].epochCount;
        totalLiveEpochs += reports[i].liveEpochCount;
    }

    out << "{\n";
    out << "  \"artifact\":\"frontier_epoch_oracle\",\n";
    out << "  \"truth_source\":\"mergeSimCudaInitialRunSummaries\",\n";
    out << "  \"safe_store_truth\":\"reduceSimCudaInitialRunSummariesToAllCandidateStates\",\n";
    out << "  \"runtime_prototype_allowed\":false,\n";
    out << "  \"default_path_changes_allowed\":false,\n";
    out << "  \"gpu_shadow_implemented\":false,\n";
    out << "  \"cases_total\":" << reports.size() << ",\n";
    out << "  \"summaries_total\":" << totalSummaries << ",\n";
    out << "  \"trace_events_total\":" << totalTrace << ",\n";
    out << "  \"epochs_total\":" << totalEpochs << ",\n";
    out << "  \"live_epochs_total\":" << totalLiveEpochs << ",\n";
    out << "  \"mismatch_count\":" << mismatchCount << ",\n";
    out << "  \"all_exact\":" << (allExact ? "true" : "false") << ",\n";
    out << "  \"chunkability_gate_passed\":" << (allChunkable ? "true" : "false") << ",\n";
    out << "  \"revisit_after_eviction_explanation\":\"frontier states are reduced only from the final live epoch for a start; all-state safe-store states are grouped across every epoch for that start, so an evicted and later reinserted start resets frontier bounds while retaining historical safe-store bounds.\",\n";
    out << "  \"cases\":[\n";
    for (size_t i = 0; i < reports.size(); ++i)
    {
        const CaseReport &report = reports[i];
        out << "    {"
            << "\"name\":\"" << json_escape(report.name) << "\","
            << "\"summary_count\":" << report.summaryCount << ","
            << "\"trace_count\":" << report.traceCount << ","
            << "\"epoch_count\":" << report.epochCount << ","
            << "\"live_epoch_count\":" << report.liveEpochCount << ","
            << "\"frontier_count\":" << report.frontierCount << ","
            << "\"safe_store_count\":" << report.safeStoreCount << ","
            << "\"running_min\":" << report.runningMin << ","
            << "\"exact\":" << (report.exact ? "true" : "false") << ","
            << "\"chunkable\":" << (report.chunkable ? "true" : "false") << ","
            << "\"saw_insert\":" << (report.sawInsert ? "true" : "false") << ","
            << "\"saw_hit\":" << (report.sawHit ? "true" : "false") << ","
            << "\"saw_evict_insert\":" << (report.sawEvictInsert ? "true" : "false") << ","
            << "\"saw_reinsert\":" << (report.sawReinsert ? "true" : "false") << ","
            << "\"saw_lower_score_full_set_miss\":" << (report.sawLowerScoreFullSetMiss ? "true" : "false") << ","
            << "\"saw_slot_tie_eviction\":" << (report.sawSlotTieEviction ? "true" : "false") << ","
            << "\"reinsert_bounds_split\":" << (report.reinsertBoundsSplit ? "true" : "false")
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

static bool write_decision(size_t mismatchCount, bool allChunkable)
{
    const std::string path = std::string(kArtifactDir) + "/anti_loop_decision.json";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }

    std::string decision;
    std::string reason;
    if (mismatchCount != 0)
    {
        decision = "fix_frontier_epoch_oracle_mismatch";
        reason = "frontier epoch oracle produced mismatches against ordered CPU truth";
    }
    else if (allChunkable)
    {
        decision = "design_gpu_frontier_epoch_shadow";
        reason = "CPU epoch oracle matched ordered truth and epoch-labeled chunk reduce matched live epochs";
    }
    else
    {
        decision = "stop_gpu_segmented_frontier_reduce_return_to_context_apply_or_partial_safe_store";
        reason = "CPU frontier oracle matched ordered truth, but chunkability gate failed";
    }

    out << "{\n";
    out << "  \"decision\":\"" << decision << "\",\n";
    out << "  \"allowed_decisions\":["
        << "\"fix_frontier_epoch_oracle_mismatch\","
        << "\"design_gpu_frontier_epoch_shadow\","
        << "\"stop_gpu_segmented_frontier_reduce_return_to_context_apply_or_partial_safe_store\"],\n";
    out << "  \"reason\":\"" << json_escape(reason) << "\",\n";
    out << "  \"runtime_prototype_allowed\":false,\n";
    out << "  \"default_path_changes_allowed\":false,\n";
    out << "  \"gpu_shadow_implemented\":false,\n";
    out << "  \"next_step_only\":true\n";
    out << "}\n";
    return true;
}

} // namespace

int main()
{
    std::vector<sim_frontier_epoch_test::TestCase> tests =
        sim_frontier_epoch_test::make_frontier_epoch_test_cases();

    bool ok = true;
    std::vector<std::string> mismatches;
    std::vector<CaseReport> reports;
    reports.reserve(tests.size());

    if (!sim_frontier_epoch_test::ensure_directory(".tmp") ||
        !sim_frontier_epoch_test::ensure_directory(kArtifactDir))
    {
        return 1;
    }

    for (size_t i = 0; i < tests.size(); ++i)
    {
        CaseReport report;
        const bool caseOk = sim_frontier_epoch_test::analyze_case(tests[i], report, mismatches);
        reports.push_back(report);
        ok = caseOk && ok;
    }

    bool allChunkable = true;
    for (size_t i = 0; i < reports.size(); ++i)
    {
        allChunkable = reports[i].chunkable && allChunkable;
    }

    ok = write_mismatches(mismatches) && ok;
    ok = write_summary(reports, mismatches.size(), mismatches.empty(), allChunkable) && ok;
    ok = write_decision(mismatches.size(), allChunkable) && ok;

    if (!mismatches.empty())
    {
        std::cerr << "frontier epoch oracle mismatches: " << mismatches.size() << "\n";
        std::cerr << "see " << kArtifactDir << "/frontier_epoch_mismatches.jsonl\n";
    }
    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
