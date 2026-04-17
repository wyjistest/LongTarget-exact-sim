#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "../sim.h"

#if defined(__GNUC__)
extern "C" void moncontrol(int) __attribute__((weak));
#endif

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

static void set_gprof_sampling_enabled(bool enabled)
{
#if defined(__GNUC__)
    if (moncontrol)
    {
        moncontrol(enabled ? 1 : 0);
    }
#else
    (void)enabled;
#endif
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
    if (iterations == 0)
    {
        std::cerr << "--iterations must be > 0\n";
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
    tsv << "case_id\tlogical_event_count\tcontext_candidate_count_after_context_apply"
        << "\trunning_min_after_context_apply\tcontext_apply_seconds"
        << "\tcontext_apply_lookup_seconds\tcontext_apply_lookup_hit_seconds"
        << "\tcontext_apply_lookup_miss_seconds\tcontext_apply_lookup_miss_open_slot_seconds"
        << "\tcontext_apply_lookup_miss_candidate_set_full_probe_seconds"
        << "\tcontext_apply_lookup_miss_eviction_select_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_seconds"
        << "\tcontext_apply_mutate_seconds\tcontext_apply_finalize_seconds"
        << "\tcontext_apply_attempted_count\tcontext_apply_modified_count"
        << "\tcontext_apply_noop_count\tcontext_apply_lookup_hit_count"
        << "\tcontext_apply_lookup_miss_count\tcontext_apply_lookup_probe_steps_total"
        << "\tcontext_apply_lookup_probe_steps_max\tcontext_apply_lookup_miss_open_slot_count"
        << "\tcontext_apply_lookup_miss_candidate_set_full_count"
        << "\tcontext_apply_eviction_selected_count\tcontext_apply_reused_slot_count"
        << "\tverify_ok\n";

    std::stringstream aggregateTsv;
    if (!aggregateTsvPath.empty())
    {
        aggregateTsv << "case_id\twarmup_iterations\titerations\tlogical_event_count"
                     << "\tcontext_candidate_count_after_context_apply"
                     << "\tcontext_apply_attempted_count\tcontext_apply_modified_count"
                     << "\tcontext_apply_noop_count\tcontext_apply_lookup_hit_count"
                     << "\tcontext_apply_lookup_miss_count\tcontext_apply_lookup_probe_steps_total"
                     << "\tcontext_apply_lookup_probe_steps_max"
                     << "\tcontext_apply_lookup_miss_open_slot_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_count"
                     << "\tcontext_apply_eviction_selected_count\tcontext_apply_reused_slot_count"
                     << "\tcontext_apply_mean_seconds\tcontext_apply_p50_seconds\tcontext_apply_p95_seconds"
                     << "\tcontext_apply_lookup_mean_seconds\tcontext_apply_lookup_p50_seconds\tcontext_apply_lookup_p95_seconds"
                     << "\tcontext_apply_lookup_miss_mean_seconds\tcontext_apply_lookup_miss_p50_seconds\tcontext_apply_lookup_miss_p95_seconds"
                     << "\tcontext_apply_lookup_miss_open_slot_mean_seconds\tcontext_apply_lookup_miss_open_slot_p50_seconds\tcontext_apply_lookup_miss_open_slot_p95_seconds"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_mean_seconds\tcontext_apply_lookup_miss_candidate_set_full_probe_p50_seconds\tcontext_apply_lookup_miss_candidate_set_full_probe_p95_seconds"
                     << "\tcontext_apply_lookup_miss_eviction_select_mean_seconds\tcontext_apply_lookup_miss_eviction_select_p50_seconds\tcontext_apply_lookup_miss_eviction_select_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_p95_seconds"
                     << "\tcontext_apply_mutate_mean_seconds\tcontext_apply_mutate_p50_seconds\tcontext_apply_mutate_p95_seconds"
                     << "\tcontext_apply_finalize_mean_seconds\tcontext_apply_finalize_p50_seconds\tcontext_apply_finalize_p95_seconds"
                     << "\tverify_ok\n";
    }

    set_gprof_sampling_enabled(false);

    for (size_t caseIndex = 0; caseIndex < selectedCases.size(); ++caseIndex)
    {
        const std::string &selectedCase = selectedCases[caseIndex];
        SimInitialHostMergeCorpusCase corpus;
        error.clear();
        if (!loadSimInitialHostMergeCorpusCase(simJoinInitialHostMergeCorpusPath(corpusDir, selectedCase),
                                               corpus,
                                               &error))
        {
            std::cerr << error << "\n";
            return 1;
        }

        SimInitialHostMergeReplayResult replay;
        for (size_t iteration = 0; iteration < warmupIterations; ++iteration)
        {
            error.clear();
            if (!replaySimInitialHostMergeContextApplyPhase(corpus, false, replay, &error))
            {
                std::cerr << error << "\n";
                return 1;
            }
        }

        std::vector<double> contextApplySamples;
        std::vector<double> lookupSamples;
        std::vector<double> lookupMissSamples;
        std::vector<double> lookupMissOpenSlotSamples;
        std::vector<double> lookupMissCandidateSetFullProbeSamples;
        std::vector<double> lookupMissEvictionSelectSamples;
        std::vector<double> lookupMissReuseWritebackSamples;
        std::vector<double> mutateSamples;
        std::vector<double> finalizeSamples;
        contextApplySamples.reserve(iterations);
        lookupSamples.reserve(iterations);
        lookupMissSamples.reserve(iterations);
        lookupMissOpenSlotSamples.reserve(iterations);
        lookupMissCandidateSetFullProbeSamples.reserve(iterations);
        lookupMissEvictionSelectSamples.reserve(iterations);
        lookupMissReuseWritebackSamples.reserve(iterations);
        mutateSamples.reserve(iterations);
        finalizeSamples.reserve(iterations);

        set_gprof_sampling_enabled(true);
        for (size_t iteration = 0; iteration < iterations; ++iteration)
        {
            error.clear();
            if (!replaySimInitialHostMergeContextApplyPhase(corpus, false, replay, &error))
            {
                set_gprof_sampling_enabled(false);
                std::cerr << error << "\n";
                return 1;
            }
            contextApplySamples.push_back(replay.contextApplySeconds);
            lookupSamples.push_back(replay.storeOtherMergeContextApplyLookupSeconds);
            lookupMissSamples.push_back(replay.storeOtherMergeContextApplyLookupMissSeconds);
            lookupMissOpenSlotSamples.push_back(replay.storeOtherMergeContextApplyLookupMissOpenSlotSeconds);
            lookupMissCandidateSetFullProbeSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeSeconds);
            lookupMissEvictionSelectSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissEvictionSelectSeconds);
            lookupMissReuseWritebackSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackSeconds);
            mutateSamples.push_back(replay.storeOtherMergeContextApplyMutateSeconds);
            finalizeSamples.push_back(replay.storeOtherMergeContextApplyFinalizeSeconds);
        }
        set_gprof_sampling_enabled(false);

        bool verifyOk = !verify;
        if (verify)
        {
            SimInitialHostMergeReplayResult verifyReplay;
            error.clear();
            if (!replaySimInitialHostMergeContextApplyCorpusCase(corpus, verifyReplay, &error))
            {
                std::cerr << error << "\n";
                return 1;
            }
            if (!verifySimInitialHostMergeContextApplyReplay(corpus, verifyReplay, &error))
            {
                std::cerr << error << "\n";
                return 1;
            }
            verifyOk = true;
        }

        tsv << selectedCase
            << "\t" << corpus.logicalEventCount
            << "\t" << corpus.expectedContextCandidates.size()
            << "\t" << corpus.runningMinAfterContextApply
            << "\t" << replay.contextApplySeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupHitSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissOpenSlotSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissEvictionSelectSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackSeconds
            << "\t" << replay.storeOtherMergeContextApplyMutateSeconds
            << "\t" << replay.storeOtherMergeContextApplyFinalizeSeconds
            << "\t" << replay.storeOtherMergeContextApplyAttemptedCount
            << "\t" << replay.storeOtherMergeContextApplyModifiedCount
            << "\t" << replay.storeOtherMergeContextApplyNoopCount
            << "\t" << replay.storeOtherMergeContextApplyLookupHitCount
            << "\t" << replay.storeOtherMergeContextApplyLookupMissCount
            << "\t" << replay.storeOtherMergeContextApplyLookupProbeStepsTotal
            << "\t" << replay.storeOtherMergeContextApplyLookupProbeStepsMax
            << "\t" << replay.storeOtherMergeContextApplyLookupMissOpenSlotCount
            << "\t" << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullCount
            << "\t" << replay.storeOtherMergeContextApplyEvictionSelectedCount
            << "\t" << replay.storeOtherMergeContextApplyReusedSlotCount
            << "\t" << (verifyOk ? 1 : 0)
            << "\n";

        if (!aggregateTsvPath.empty())
        {
            const SimInitialHostMergeReplayTimingSummary contextApplySummary =
                summarizeSimInitialHostMergeReplaySamples(contextApplySamples);
            const SimInitialHostMergeReplayTimingSummary lookupSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissOpenSlotSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissOpenSlotSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissCandidateSetFullProbeSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissCandidateSetFullProbeSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissEvictionSelectSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissEvictionSelectSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackSamples);
            const SimInitialHostMergeReplayTimingSummary mutateSummary =
                summarizeSimInitialHostMergeReplaySamples(mutateSamples);
            const SimInitialHostMergeReplayTimingSummary finalizeSummary =
                summarizeSimInitialHostMergeReplaySamples(finalizeSamples);

            aggregateTsv << selectedCase
                         << "\t" << warmupIterations
                         << "\t" << iterations
                         << "\t" << corpus.logicalEventCount
                         << "\t" << corpus.expectedContextCandidates.size()
                         << "\t" << replay.storeOtherMergeContextApplyAttemptedCount
                         << "\t" << replay.storeOtherMergeContextApplyModifiedCount
                         << "\t" << replay.storeOtherMergeContextApplyNoopCount
                         << "\t" << replay.storeOtherMergeContextApplyLookupHitCount
                         << "\t" << replay.storeOtherMergeContextApplyLookupMissCount
                         << "\t" << replay.storeOtherMergeContextApplyLookupProbeStepsTotal
                         << "\t" << replay.storeOtherMergeContextApplyLookupProbeStepsMax
                         << "\t" << replay.storeOtherMergeContextApplyLookupMissOpenSlotCount
                         << "\t" << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullCount
                         << "\t" << replay.storeOtherMergeContextApplyEvictionSelectedCount
                         << "\t" << replay.storeOtherMergeContextApplyReusedSlotCount
                         << "\t" << contextApplySummary.meanSeconds
                         << "\t" << contextApplySummary.p50Seconds
                         << "\t" << contextApplySummary.p95Seconds
                         << "\t" << lookupSummary.meanSeconds
                         << "\t" << lookupSummary.p50Seconds
                         << "\t" << lookupSummary.p95Seconds
                         << "\t" << lookupMissSummary.meanSeconds
                         << "\t" << lookupMissSummary.p50Seconds
                         << "\t" << lookupMissSummary.p95Seconds
                         << "\t" << lookupMissOpenSlotSummary.meanSeconds
                         << "\t" << lookupMissOpenSlotSummary.p50Seconds
                         << "\t" << lookupMissOpenSlotSummary.p95Seconds
                         << "\t" << lookupMissCandidateSetFullProbeSummary.meanSeconds
                         << "\t" << lookupMissCandidateSetFullProbeSummary.p50Seconds
                         << "\t" << lookupMissCandidateSetFullProbeSummary.p95Seconds
                         << "\t" << lookupMissEvictionSelectSummary.meanSeconds
                         << "\t" << lookupMissEvictionSelectSummary.p50Seconds
                         << "\t" << lookupMissEvictionSelectSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackSummary.p95Seconds
                         << "\t" << mutateSummary.meanSeconds
                         << "\t" << mutateSummary.p50Seconds
                         << "\t" << mutateSummary.p95Seconds
                         << "\t" << finalizeSummary.meanSeconds
                         << "\t" << finalizeSummary.p50Seconds
                         << "\t" << finalizeSummary.p95Seconds
                         << "\t" << (verifyOk ? 1 : 0)
                         << "\n";
        }
    }

    if (!outputTsvPath.empty())
    {
        if (!write_text_file(outputTsvPath, tsv.str()))
        {
            std::cerr << "failed to write output TSV: " << outputTsvPath << "\n";
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
            std::cerr << "failed to write aggregate TSV: " << aggregateTsvPath << "\n";
            return 1;
        }
    }

    return 0;
}
