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
              << " [--corpus-dir DIR] [--case CASE_ID | --all] [--verify] [--output-tsv PATH]\n";
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
    bool selectAll = false;
    bool verify = false;

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
    tsv << "case_id\tsummary_count\tlogical_event_count\tcontext_apply_seconds\tstore_materialize_seconds\tstore_prune_seconds\tfull_host_merge_seconds\tcandidate_count_after_context_apply\tstore_materialized_count\tstore_pruned_count\tstore_other_merge_seconds\tverify_ok\n";

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
            << replay.storePruneSeconds << '\t'
            << replay.fullHostMergeSeconds << '\t'
            << replay.contextCandidates.size() << '\t'
            << replay.storeMaterialized.size() << '\t'
            << replay.storePruned.size() << '\t'
            << replay.contextApplySeconds << '\t'
            << (verifyOk ? "true" : "false") << '\n';
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

    return success ? 0 : 1;
}
