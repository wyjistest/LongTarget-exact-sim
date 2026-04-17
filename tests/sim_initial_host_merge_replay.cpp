#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "../sim.h"

namespace
{

static void print_usage(const char *argv0)
{
    std::cerr << "Usage: " << argv0
              << " [--corpus-dir DIR] [--case CASE_ID | --all] [--verify] [--output-tsv PATH]"
              << " [--warmup-iterations N] [--iterations N] [--aggregate-tsv PATH]\n";
}

static bool write_text_file(const std::string &path, const std::string &content)
{
    std::ofstream output(path.c_str(), std::ios::out | std::ios::binary | std::ios::trunc);
    if (!output)
    {
        return false;
    }
    output.write(content.data(), static_cast<std::streamsize>(content.size()));
    return output.good();
}

} // namespace

int main(int argc, char **argv)
{
    std::string corpusDir(".");
    std::string caseId;
    std::string outputTsvPath;
    std::string aggregateTsvPath;
    bool selectAll = false;
    bool verify = false;
    size_t warmupIterations = 0;
    size_t iterations = 1;

    for (int index = 1; index < argc; ++index)
    {
        const std::string argument(argv[index]);
        if (argument == "--corpus-dir")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            corpusDir = argv[++index];
        }
        else if (argument == "--case")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            caseId = argv[++index];
        }
        else if (argument == "--all")
        {
            selectAll = true;
        }
        else if (argument == "--verify")
        {
            verify = true;
        }
        else if (argument == "--output-tsv")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            outputTsvPath = argv[++index];
        }
        else if (argument == "--warmup-iterations")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            warmupIterations = static_cast<size_t>(strtoull(argv[++index], NULL, 10));
        }
        else if (argument == "--iterations")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            iterations = static_cast<size_t>(strtoull(argv[++index], NULL, 10));
        }
        else if (argument == "--aggregate-tsv")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            aggregateTsvPath = argv[++index];
        }
        else if (argument == "--help" || argument == "-h")
        {
            print_usage(argv[0]);
            return 0;
        }
        else
        {
            std::cerr << "Unknown argument: " << argument << "\n";
            print_usage(argv[0]);
            return 1;
        }
    }

    if (selectAll && !caseId.empty())
    {
        std::cerr << "--case and --all are mutually exclusive\n";
        return 1;
    }
    if ((warmupIterations > 0 || iterations != 1) && aggregateTsvPath.empty())
    {
        std::cerr << "--aggregate-tsv is required when benchmark iterations are requested\n";
        return 1;
    }

    std::vector<std::string> selectedCases;
    std::string error;
    if (selectAll || caseId.empty())
    {
        if (!listSimInitialHostMergeCorpusCases(corpusDir, selectedCases, &error))
        {
            std::cerr << error << "\n";
            return 1;
        }
    }
    else
    {
        selectedCases.push_back(caseId);
    }

    if (selectedCases.empty())
    {
        std::cerr << "No corpus cases found under " << corpusDir << "\n";
        return 1;
    }

    std::stringstream tsv;
    tsv << "case_id\tsummary_count\tlogical_event_count\tcontext_apply_seconds\tstore_materialize_seconds"
        << "\tstore_materialize_reset_seconds\tstore_materialize_insert_seconds"
        << "\tstore_materialize_update_seconds\tstore_materialize_snapshot_copy_seconds"
        << "\tstore_materialize_inserted_count\tstore_materialize_updated_count"
        << "\tstore_materialize_peak_size\tstore_materialize_rehash_count"
        << "\tstore_prune_seconds\tfull_host_merge_seconds\tcandidate_count_after_context_apply"
        << "\tstore_materialized_count\tstore_pruned_count\tstore_other_merge_seconds\tverify_ok\n";
    std::stringstream aggregateTsv;
    if (!aggregateTsvPath.empty())
    {
        aggregateTsv << "case_id\twarmup_iterations\titerations\tlogical_event_count\tstore_materialized_count\tstore_pruned_count"
                     << "\tstore_materialize_inserted_count\tstore_materialize_updated_count"
                     << "\tstore_materialize_peak_size\tstore_materialize_rehash_count"
                     << "\tcontext_apply_mean_seconds\tcontext_apply_p50_seconds\tcontext_apply_p95_seconds"
                     << "\tstore_materialize_mean_seconds\tstore_materialize_p50_seconds\tstore_materialize_p95_seconds"
                     << "\tstore_materialize_reset_mean_seconds\tstore_materialize_reset_p50_seconds\tstore_materialize_reset_p95_seconds"
                     << "\tstore_materialize_insert_mean_seconds\tstore_materialize_insert_p50_seconds\tstore_materialize_insert_p95_seconds"
                     << "\tstore_materialize_update_mean_seconds\tstore_materialize_update_p50_seconds\tstore_materialize_update_p95_seconds"
                     << "\tstore_materialize_snapshot_copy_mean_seconds\tstore_materialize_snapshot_copy_p50_seconds\tstore_materialize_snapshot_copy_p95_seconds"
                     << "\tstore_prune_mean_seconds\tstore_prune_p50_seconds\tstore_prune_p95_seconds"
                     << "\tstore_other_merge_mean_seconds\tstore_other_merge_p50_seconds\tstore_other_merge_p95_seconds"
                     << "\tfull_host_merge_mean_seconds\tfull_host_merge_p50_seconds\tfull_host_merge_p95_seconds"
                     << "\tns_per_logical_event\tns_per_materialized_record\tns_per_pruned_record\n";
    }

    bool success = true;
    for (size_t caseIndex = 0; caseIndex < selectedCases.size(); ++caseIndex)
    {
        SimInitialHostMergeCorpusCase corpus;
        if (!loadSimInitialHostMergeCorpusCase(simJoinInitialHostMergeCorpusPath(corpusDir, selectedCases[caseIndex]),
                                               corpus,
                                               &error))
        {
            std::cerr << error << "\n";
            return 1;
        }

        SimInitialHostMergeReplayResult replay;
        if (!replaySimInitialHostMergeCorpusCase(corpus, replay, &error))
        {
            std::cerr << error << "\n";
            return 1;
        }

        SimInitialHostMergeReplayBenchmarkResult benchmark;
        if (!aggregateTsvPath.empty())
        {
            if (!benchmarkSimInitialHostMergeCorpusCase(corpus,
                                                        warmupIterations,
                                                        iterations,
                                                        benchmark,
                                                        &error))
            {
                std::cerr << error << "\n";
                return 1;
            }
        }

        bool verifyOk = true;
        if (verify)
        {
            verifyOk = verifySimInitialHostMergeReplay(corpus, replay, &error);
            if (!verifyOk)
            {
                success = false;
                std::cerr << corpus.caseId << ": " << error << "\n";
            }
        }

        tsv << corpus.caseId << '\t'
            << corpus.summaries.size() << '\t'
            << corpus.logicalEventCount << '\t'
            << replay.contextApplySeconds << '\t'
            << replay.storeMaterializeSeconds << '\t'
            << replay.storeMaterializeResetSeconds << '\t'
            << replay.storeMaterializeInsertSeconds << '\t'
            << replay.storeMaterializeUpdateSeconds << '\t'
            << replay.storeMaterializeSnapshotCopySeconds << '\t'
            << replay.storeMaterializeInsertedCount << '\t'
            << replay.storeMaterializeUpdatedCount << '\t'
            << replay.storeMaterializePeakSize << '\t'
            << replay.storeMaterializeRehashCount << '\t'
            << replay.storePruneSeconds << '\t'
            << replay.fullHostMergeSeconds << '\t'
            << replay.contextCandidates.size() << '\t'
            << replay.storeMaterialized.size() << '\t'
            << replay.storePruned.size() << '\t'
            << replay.storeOtherMergeSeconds << '\t'
            << (verifyOk ? "true" : "false") << '\n';

        if (!aggregateTsvPath.empty())
        {
            aggregateTsv << corpus.caseId << '\t'
                         << benchmark.warmupIterations << '\t'
                         << benchmark.iterations << '\t'
                         << benchmark.logicalEventCount << '\t'
                         << benchmark.storeMaterializedCount << '\t'
                         << benchmark.storePrunedCount << '\t'
                         << benchmark.storeMaterializeInsertedCount << '\t'
                         << benchmark.storeMaterializeUpdatedCount << '\t'
                         << benchmark.storeMaterializePeakSize << '\t'
                         << benchmark.storeMaterializeRehashCount << '\t'
                         << benchmark.contextApply.meanSeconds << '\t'
                         << benchmark.contextApply.p50Seconds << '\t'
                         << benchmark.contextApply.p95Seconds << '\t'
                         << benchmark.storeMaterialize.meanSeconds << '\t'
                         << benchmark.storeMaterialize.p50Seconds << '\t'
                         << benchmark.storeMaterialize.p95Seconds << '\t'
                         << benchmark.storeMaterializeReset.meanSeconds << '\t'
                         << benchmark.storeMaterializeReset.p50Seconds << '\t'
                         << benchmark.storeMaterializeReset.p95Seconds << '\t'
                         << benchmark.storeMaterializeInsert.meanSeconds << '\t'
                         << benchmark.storeMaterializeInsert.p50Seconds << '\t'
                         << benchmark.storeMaterializeInsert.p95Seconds << '\t'
                         << benchmark.storeMaterializeUpdate.meanSeconds << '\t'
                         << benchmark.storeMaterializeUpdate.p50Seconds << '\t'
                         << benchmark.storeMaterializeUpdate.p95Seconds << '\t'
                         << benchmark.storeMaterializeSnapshotCopy.meanSeconds << '\t'
                         << benchmark.storeMaterializeSnapshotCopy.p50Seconds << '\t'
                         << benchmark.storeMaterializeSnapshotCopy.p95Seconds << '\t'
                         << benchmark.storePrune.meanSeconds << '\t'
                         << benchmark.storePrune.p50Seconds << '\t'
                         << benchmark.storePrune.p95Seconds << '\t'
                         << benchmark.storeOtherMerge.meanSeconds << '\t'
                         << benchmark.storeOtherMerge.p50Seconds << '\t'
                         << benchmark.storeOtherMerge.p95Seconds << '\t'
                         << benchmark.fullHostMerge.meanSeconds << '\t'
                         << benchmark.fullHostMerge.p50Seconds << '\t'
                         << benchmark.fullHostMerge.p95Seconds << '\t'
                         << benchmark.nsPerLogicalEvent << '\t'
                         << benchmark.nsPerMaterializedRecord << '\t'
                         << benchmark.nsPerPrunedRecord << '\n';
        }
    }

    if (!outputTsvPath.empty())
    {
        if (!write_text_file(outputTsvPath, tsv.str()))
        {
            std::cerr << "Failed to write TSV: " << outputTsvPath << "\n";
            return 1;
        }
    }
    else
    {
        std::cout << tsv.str();
    }

    if (!aggregateTsvPath.empty())
    {
        if (!write_text_file(aggregateTsvPath, aggregateTsv.str()))
        {
            std::cerr << "Failed to write aggregate TSV: " << aggregateTsvPath << "\n";
            return 1;
        }
    }

    return success ? 0 : 1;
}
