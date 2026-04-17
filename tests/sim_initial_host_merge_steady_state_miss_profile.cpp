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
              << " (--capture-trace --corpus-dir DIR --trace-dir DIR | --replay-trace --trace-dir DIR --backend reference|specialized)"
              << " [--case CASE_ID | --all] [--verify] [--output-tsv PATH]"
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

static const char *backend_name(SimInitialHostMergeSteadyStateReplayBackend backend)
{
    switch (backend)
    {
    case SIM_INITIAL_HOST_MERGE_STEADY_STATE_REPLAY_BACKEND_REFERENCE:
        return "reference";
    case SIM_INITIAL_HOST_MERGE_STEADY_STATE_REPLAY_BACKEND_SPECIALIZED:
        return "specialized";
    }
    return "unknown";
}

} // namespace

int main(int argc, char **argv)
{
    bool captureTrace = false;
    bool replayTrace = false;
    bool selectAll = false;
    bool verify = false;
    bool backendExplicit = false;
    std::string corpusDir(".");
    std::string traceDir;
    std::string caseId;
    std::string outputTsvPath;
    std::string aggregateTsvPath;
    size_t warmupIterations = 0;
    size_t iterations = 1;
    SimInitialHostMergeSteadyStateReplayBackend backend =
        SIM_INITIAL_HOST_MERGE_STEADY_STATE_REPLAY_BACKEND_SPECIALIZED;

    for (int index = 1; index < argc; ++index)
    {
        const std::string argument(argv[index]);
        if (argument == "--capture-trace")
        {
            captureTrace = true;
        }
        else if (argument == "--replay-trace")
        {
            replayTrace = true;
        }
        else if (argument == "--corpus-dir")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            corpusDir = argv[++index];
        }
        else if (argument == "--trace-dir")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            traceDir = argv[++index];
        }
        else if (argument == "--backend")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            const std::string backendArg(argv[++index]);
            if (backendArg == "reference")
            {
                backend = SIM_INITIAL_HOST_MERGE_STEADY_STATE_REPLAY_BACKEND_REFERENCE;
            }
            else if (backendArg == "specialized")
            {
                backend = SIM_INITIAL_HOST_MERGE_STEADY_STATE_REPLAY_BACKEND_SPECIALIZED;
            }
            else
            {
                std::cerr << "Unsupported backend: " << backendArg << "\n";
                return 1;
            }
            backendExplicit = true;
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

    if (captureTrace == replayTrace)
    {
        std::cerr << "exactly one of --capture-trace or --replay-trace is required\n";
        return 1;
    }
    if (traceDir.empty())
    {
        std::cerr << "--trace-dir is required\n";
        return 1;
    }
    if (selectAll && !caseId.empty())
    {
        std::cerr << "--case and --all are mutually exclusive\n";
        return 1;
    }
    if (iterations == 0)
    {
        std::cerr << "--iterations must be > 0\n";
        return 1;
    }
    if (replayTrace && !backendExplicit)
    {
        std::cerr << "--backend is required for --replay-trace\n";
        return 1;
    }
    if (captureTrace && (warmupIterations > 0 || iterations != 1 || !aggregateTsvPath.empty()))
    {
        std::cerr << "benchmark iteration flags are only valid for --replay-trace\n";
        return 1;
    }

    std::vector<std::string> selectedCases;
    std::string error;
    const std::string listRoot = captureTrace ? corpusDir : traceDir;
    if (selectAll || caseId.empty())
    {
        if (!listSimInitialHostMergeCorpusCases(listRoot, selectedCases, &error))
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
        std::cerr << "No cases found under " << listRoot << "\n";
        return 1;
    }

    std::stringstream tsv;
    std::stringstream aggregateTsv;
    if (captureTrace)
    {
        tsv << "case_id\tlogical_event_count\tseed_candidate_count\tpost_fill_event_count"
            << "\tpost_fill_full_set_miss_count\texpected_final_candidate_count\n";
    }
    else
    {
        tsv << "case_id\tbackend\tpost_fill_event_count\tfull_set_miss_count\thit_update_count"
            << "\thit_noop_count\tseed_candidate_count\texpected_final_candidate_count"
            << "\ttotal_seconds\tfull_set_miss_seconds\tverify_ok\n";
        if (!aggregateTsvPath.empty())
        {
            aggregateTsv << "case_id\tbackend\twarmup_iterations\titerations\tpost_fill_event_count"
                         << "\tfull_set_miss_count\ttotal_mean_seconds\ttotal_p50_seconds"
                         << "\ttotal_p95_seconds\tfull_set_miss_mean_seconds"
                         << "\tfull_set_miss_p50_seconds\tfull_set_miss_p95_seconds\tverify_ok\n";
        }
    }

    set_gprof_sampling_enabled(false);

    for (size_t caseIndex = 0; caseIndex < selectedCases.size(); ++caseIndex)
    {
        const std::string &selectedCase = selectedCases[caseIndex];
        if (captureTrace)
        {
            SimInitialHostMergeCorpusCase corpus;
            error.clear();
            if (!loadSimInitialHostMergeCorpusCase(simJoinInitialHostMergeCorpusPath(corpusDir, selectedCase),
                                                   corpus,
                                                   &error))
            {
                std::cerr << error << "\n";
                return 1;
            }

            SimInitialHostMergeSteadyStateTraceCase trace;
            error.clear();
            if (!captureSimInitialHostMergeSteadyStateTraceCase(corpus, trace, &error))
            {
                std::cerr << error << "\n";
                return 1;
            }
            error.clear();
            if (!writeSimInitialHostMergeSteadyStateTraceCase(traceDir, trace, &error))
            {
                std::cerr << error << "\n";
                return 1;
            }

            tsv << trace.caseId << '\t'
                << trace.logicalEventCount << '\t'
                << trace.seedContextCandidates.size() << '\t'
                << trace.events.size() << '\t'
                << trace.postFillFullSetMissCount << '\t'
                << trace.expectedFinalContextCandidates.size() << '\n';
            continue;
        }

        SimInitialHostMergeSteadyStateTraceCase trace;
        error.clear();
        if (!loadSimInitialHostMergeSteadyStateTraceCase(simJoinInitialHostMergeCorpusPath(traceDir, selectedCase),
                                                         trace,
                                                         &error))
        {
            std::cerr << error << "\n";
            return 1;
        }

        SimInitialHostMergeSteadyStateReplayResult replay;
        for (size_t iteration = 0; iteration < warmupIterations; ++iteration)
        {
            error.clear();
            if (!replaySimInitialHostMergeSteadyStateTraceCase(trace, backend, replay, &error))
            {
                std::cerr << error << "\n";
                return 1;
            }
        }

        std::vector<double> totalSamples;
        std::vector<double> fullSetMissSamples;
        totalSamples.reserve(iterations);
        fullSetMissSamples.reserve(iterations);

        set_gprof_sampling_enabled(true);
        for (size_t iteration = 0; iteration < iterations; ++iteration)
        {
            error.clear();
            if (!replaySimInitialHostMergeSteadyStateTraceCase(trace, backend, replay, &error))
            {
                set_gprof_sampling_enabled(false);
                std::cerr << error << "\n";
                return 1;
            }
            totalSamples.push_back(replay.totalSeconds);
            fullSetMissSamples.push_back(replay.fullSetMissSeconds);
        }
        set_gprof_sampling_enabled(false);

        bool verifyOk = true;
        if (verify)
        {
            error.clear();
            verifyOk = verifySimInitialHostMergeSteadyStateTraceReplay(trace, replay, &error);
            if (!verifyOk)
            {
                std::cerr << error << "\n";
                return 1;
            }
        }

        tsv << trace.caseId << '\t'
            << backend_name(backend) << '\t'
            << trace.events.size() << '\t'
            << replay.fullSetMissCount << '\t'
            << replay.hitUpdateCount << '\t'
            << replay.hitNoopCount << '\t'
            << trace.seedContextCandidates.size() << '\t'
            << trace.expectedFinalContextCandidates.size() << '\t'
            << replay.totalSeconds << '\t'
            << replay.fullSetMissSeconds << '\t'
            << (verifyOk ? 1 : 0) << '\n';

        if (!aggregateTsvPath.empty())
        {
            const SimInitialHostMergeReplayTimingSummary totalSummary =
                summarizeSimInitialHostMergeReplaySamples(totalSamples);
            const SimInitialHostMergeReplayTimingSummary fullSetMissSummary =
                summarizeSimInitialHostMergeReplaySamples(fullSetMissSamples);
            aggregateTsv << trace.caseId << '\t'
                         << backend_name(backend) << '\t'
                         << warmupIterations << '\t'
                         << iterations << '\t'
                         << trace.events.size() << '\t'
                         << replay.fullSetMissCount << '\t'
                         << totalSummary.meanSeconds << '\t'
                         << totalSummary.p50Seconds << '\t'
                         << totalSummary.p95Seconds << '\t'
                         << fullSetMissSummary.meanSeconds << '\t'
                         << fullSetMissSummary.p50Seconds << '\t'
                         << fullSetMissSummary.p95Seconds << '\t'
                         << (verifyOk ? 1 : 0) << '\n';
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
