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
              << " [--candidate-index-backend tombstone|backward_shift]"
              << " [--profile-mode coarse|terminal|lexical_first_half|lexical_first_half_count_only|lexical_first_half_sampled|lexical_first_half_sampled_no_terminal_telemetry|lexical_first_half_sampled_no_state_update_bookkeeping]"
              << " [--terminal-telemetry-overhead auto|on|off]"
              << " [--profile-sample-log2 N]"
              << " [--warmup-iterations N] [--iterations N] [--aggregate-tsv PATH]"
              << " [--benchmark-stderr PATH] [--workload-id ID]"
              << " [--benchmark-source-original-path PATH]"
              << " [--benchmark-source-copied-path PATH]"
              << " [--benchmark-source-sha256 HEX]"
              << " [--benchmark-source-size-bytes N]"
              << " [--benchmark-identity-basis BASIS]\n";
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


static const char *candidate_index_backend_name(SimCandidateIndexBackend backend)
{
    switch (backend)
    {
    case SIM_CANDIDATE_INDEX_BACKEND_TOMBSTONE:
        return "tombstone";
    case SIM_CANDIDATE_INDEX_BACKEND_BACKWARD_SHIFT:
        return "backward_shift";
    }
    return "unknown";
}

static bool parse_candidate_index_backend(const std::string &argument,
                                          SimCandidateIndexBackend &backend)
{
    if (argument == "tombstone")
    {
        backend = SIM_CANDIDATE_INDEX_BACKEND_TOMBSTONE;
        return true;
    }
    if (argument == "backward_shift")
    {
        backend = SIM_CANDIDATE_INDEX_BACKEND_BACKWARD_SHIFT;
        return true;
    }
    return false;
}

static const char *profile_mode_name(SimInitialProfilerMode mode)
{
    switch (mode)
    {
    case SIM_INITIAL_PROFILER_MODE_COARSE:
        return "coarse";
    case SIM_INITIAL_PROFILER_MODE_TERMINAL:
        return "terminal";
    case SIM_INITIAL_PROFILER_MODE_LEXICAL_FIRST_HALF:
        return "lexical_first_half";
    case SIM_INITIAL_PROFILER_MODE_LEXICAL_FIRST_HALF_COUNT_ONLY:
        return "lexical_first_half_count_only";
    case SIM_INITIAL_PROFILER_MODE_LEXICAL_FIRST_HALF_SAMPLED:
        return "lexical_first_half_sampled";
    case SIM_INITIAL_PROFILER_MODE_LEXICAL_FIRST_HALF_SAMPLED_NO_TERMINAL_TELEMETRY:
        return "lexical_first_half_sampled_no_terminal_telemetry";
    case SIM_INITIAL_PROFILER_MODE_LEXICAL_FIRST_HALF_SAMPLED_NO_STATE_UPDATE_BOOKKEEPING:
        return "lexical_first_half_sampled_no_state_update_bookkeeping";
    }
    return "unknown";
}

static bool parse_profile_mode(const std::string &argument, SimInitialProfilerMode &mode)
{
    if (argument == "coarse")
    {
        mode = SIM_INITIAL_PROFILER_MODE_COARSE;
        return true;
    }
    if (argument == "terminal")
    {
        mode = SIM_INITIAL_PROFILER_MODE_TERMINAL;
        return true;
    }
    if (argument == "lexical_first_half")
    {
        mode = SIM_INITIAL_PROFILER_MODE_LEXICAL_FIRST_HALF;
        return true;
    }
    if (argument == "lexical_first_half_count_only")
    {
        mode = SIM_INITIAL_PROFILER_MODE_LEXICAL_FIRST_HALF_COUNT_ONLY;
        return true;
    }
    if (argument == "lexical_first_half_sampled")
    {
        mode = SIM_INITIAL_PROFILER_MODE_LEXICAL_FIRST_HALF_SAMPLED;
        return true;
    }
    if (argument == "lexical_first_half_sampled_no_terminal_telemetry")
    {
        mode = SIM_INITIAL_PROFILER_MODE_LEXICAL_FIRST_HALF_SAMPLED_NO_TERMINAL_TELEMETRY;
        return true;
    }
    if (argument == "lexical_first_half_sampled_no_state_update_bookkeeping")
    {
        mode = SIM_INITIAL_PROFILER_MODE_LEXICAL_FIRST_HALF_SAMPLED_NO_STATE_UPDATE_BOOKKEEPING;
        return true;
    }
    return false;
}

static const char *terminal_telemetry_overhead_mode_name(
    SimInitialTerminalTelemetryOverheadMode mode)
{
    switch (mode)
    {
    case SIM_INITIAL_TERMINAL_TELEMETRY_OVERHEAD_AUTO:
        return "auto";
    case SIM_INITIAL_TERMINAL_TELEMETRY_OVERHEAD_ON:
        return "on";
    case SIM_INITIAL_TERMINAL_TELEMETRY_OVERHEAD_OFF:
        return "off";
    }
    return "unknown";
}

static bool parse_terminal_telemetry_overhead_mode(
    const std::string &argument,
    SimInitialTerminalTelemetryOverheadMode &mode)
{
    if (argument == "auto")
    {
        mode = SIM_INITIAL_TERMINAL_TELEMETRY_OVERHEAD_AUTO;
        return true;
    }
    if (argument == "on")
    {
        mode = SIM_INITIAL_TERMINAL_TELEMETRY_OVERHEAD_ON;
        return true;
    }
    if (argument == "off")
    {
        mode = SIM_INITIAL_TERMINAL_TELEMETRY_OVERHEAD_OFF;
        return true;
    }
    return false;
}

static const char *state_update_bookkeeping_mode_name(
    SimInitialStateUpdateBookkeepingMode mode)
{
    switch (mode)
    {
    case SIM_INITIAL_STATE_UPDATE_BOOKKEEPING_AUTO:
        return "auto";
    case SIM_INITIAL_STATE_UPDATE_BOOKKEEPING_ON:
        return "on";
    case SIM_INITIAL_STATE_UPDATE_BOOKKEEPING_OFF:
        return "off";
    }
    return "unknown";
}

struct TerminalPathDerivedMetrics
{
    TerminalPathDerivedMetrics()
        : parentSeconds(0.0),
          childKnownSeconds(0.0),
          lexicalParentSeconds(0.0),
          spanFirstHalfSeconds(0.0),
          spanSecondHalfSeconds(0.0),
          firstHalfParentSeconds(0.0),
          firstHalfSpanASeconds(0.0),
          firstHalfSpanAParentSeconds(0.0),
          firstHalfSpanA0Seconds(0.0),
          firstHalfSpanA1Seconds(0.0),
          firstHalfSpanA0ParentSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Seconds(0.0),
          firstHalfSpanA0GapBeforeA00ParentSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0Seconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0ParentSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0Child0Seconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0Child1Seconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltParentSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltLeftSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltRightSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltRightParentSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltRightChild0Seconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltRightChild1Seconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span1Seconds(0.0),
          firstHalfSpanA00Seconds(0.0),
          firstHalfSpanA0GapBetweenA00A01Seconds(0.0),
          firstHalfSpanA01Seconds(0.0),
          firstHalfSpanA0GapAfterA01Seconds(0.0),
          firstHalfSpanA0GapBeforeA00ChildKnownSeconds(0.0),
          firstHalfSpanA0GapBeforeA00UnexplainedSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0ChildKnownSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0UnexplainedSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltChildKnownSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltUnexplainedSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltRightUnexplainedSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSeconds(0.0),
          firstHalfSpanA0GapBeforeA00Span0AltRightRepartUnexplainedSeconds(0.0),
          firstHalfSpanA0ChildKnownSeconds(0.0),
          firstHalfSpanA0UnexplainedSeconds(0.0),
          firstHalfSpanAChildKnownSeconds(0.0),
          firstHalfSpanAUnexplainedSeconds(0.0),
          firstHalfSpanBSeconds(0.0),
          firstHalfChildKnownSeconds(0.0),
          firstHalfUnexplainedSeconds(0.0),
          candidateSlotWriteSeconds(0.0),
          startIndexWriteSeconds(0.0),
          startIndexWriteParentSeconds(0.0),
          startIndexWriteLeftSeconds(0.0),
          startIndexWriteRightSeconds(0.0),
          startIndexWriteChildKnownSeconds(0.0),
          startIndexWriteUnexplainedSeconds(0.0),
          startIndexStoreParentSeconds(0.0),
          startIndexStoreInsertSeconds(0.0),
          startIndexStoreClearSeconds(0.0),
          startIndexStoreOverwriteSeconds(0.0),
          startIndexStoreChildKnownSeconds(0.0),
          startIndexStoreUnexplainedSeconds(0.0),
          stateUpdateSeconds(0.0),
          stateUpdateParentSeconds(0.0),
          stateUpdateHeapBuildSeconds(0.0),
          stateUpdateHeapUpdateSeconds(0.0),
          stateUpdateStartIndexRebuildSeconds(0.0),
          stateUpdateTraceOrProfileBookkeepingSeconds(0.0),
          stateUpdateChildKnownSeconds(0.0),
          stateUpdateUnexplainedSeconds(0.0),
          telemetryOverheadSeconds(0.0),
          residualSeconds(0.0),
          eventCount(0),
          firstHalfEventCount(0),
          firstHalfSpanAEventCount(0),
          firstHalfSpanA0EventCount(0),
          firstHalfSpanA1EventCount(0),
          firstHalfSpanA00EventCount(0),
          firstHalfSpanA01EventCount(0),
          firstHalfSpanBEventCount(0),
          firstHalfSampledEventCount(0),
          firstHalfSpanA0SampledEventCount(0),
          firstHalfSpanA0CoveredSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00SampledEventCount(0),
          firstHalfSpanA0GapBeforeA00CoveredSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0SampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0CoveredSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0Child0SampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0Child1SampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltCoveredSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltLeftSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltRightSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltRightCoveredSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltRightChild0SampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltRightChild1SampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltRightRepartSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltRightRepartCoveredSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span1SampledEventCount(0),
          firstHalfSpanA00SampledEventCount(0),
          firstHalfSpanA0GapBetweenA00A01SampledEventCount(0),
          firstHalfSpanA01SampledEventCount(0),
          firstHalfSpanA0GapAfterA01SampledEventCount(0),
          firstHalfSpanA0GapBeforeA00UnclassifiedSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00MultiChildSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0UnclassifiedSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0MultiChildSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltUnclassifiedSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltMultiChildSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltRightUnclassifiedSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltRightMultiChildSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltRightRepartUnclassifiedSampledEventCount(0),
          firstHalfSpanA0GapBeforeA00Span0AltRightRepartMultiChildSampledEventCount(0),
          firstHalfSpanA0UnclassifiedSampledEventCount(0),
          firstHalfSpanA0MultiChildSampledEventCount(0),
          firstHalfSpanA0OverlapSampledEventCount(0),
          candidateSlotWriteCount(0),
          startIndexWriteCount(0),
          startIndexWriteSampledEventCount(0),
          startIndexWriteCoveredSampledEventCount(0),
          startIndexWriteUnclassifiedSampledEventCount(0),
          startIndexWriteMultiChildSampledEventCount(0),
          startIndexWriteLeftSampledEventCount(0),
          startIndexWriteRightSampledEventCount(0),
          startIndexWriteInsertCount(0),
          startIndexWriteUpdateExistingCount(0),
          startIndexWriteClearCount(0),
          startIndexWriteOverwriteCount(0),
          startIndexWriteIdempotentCount(0),
          startIndexWriteValueChangedCount(0),
          startIndexWriteProbeCount(0),
          startIndexWriteProbeStepsTotal(0),
          startIndexStoreSampledEventCount(0),
          startIndexStoreCoveredSampledEventCount(0),
          startIndexStoreUnclassifiedSampledEventCount(0),
          startIndexStoreMultiChildSampledEventCount(0),
          startIndexStoreInsertSampledEventCount(0),
          startIndexStoreClearSampledEventCount(0),
          startIndexStoreOverwriteSampledEventCount(0),
          startIndexStoreInsertCount(0),
          startIndexStoreClearCount(0),
          startIndexStoreOverwriteCount(0),
          startIndexStoreInsertBytes(0),
          startIndexStoreClearBytes(0),
          startIndexStoreOverwriteBytes(0),
          startIndexStoreUniqueEntryCount(0),
          startIndexStoreUniqueSlotCount(0),
          startIndexStoreUniqueKeyCount(0),
          startIndexStoreSameEntryRewriteCount(0),
          startIndexStoreSameCachelineRewriteCount(0),
          startIndexStoreBackToBackSameEntryWriteCount(0),
          startIndexStoreClearThenOverwriteSameEntryCount(0),
          startIndexStoreOverwriteThenInsertSameEntryCount(0),
          startIndexStoreInsertThenClearSameEntryCount(0),
          stateUpdateCount(0),
          stateUpdateSampledEventCount(0),
          stateUpdateCoveredSampledEventCount(0),
          stateUpdateUnclassifiedSampledEventCount(0),
          stateUpdateMultiChildSampledEventCount(0),
          stateUpdateHeapBuildSampledEventCount(0),
          stateUpdateHeapUpdateSampledEventCount(0),
          stateUpdateStartIndexRebuildSampledEventCount(0),
          stateUpdateTraceOrProfileBookkeepingSampledEventCount(0),
          stateUpdateCoverageSource("placeholder"),
          stateUpdateEventCount(0),
          stateUpdateHeapBuildCount(0),
          stateUpdateHeapUpdateCount(0),
          stateUpdateStartIndexRebuildCount(0),
          stateUpdateTraceOrProfileBookkeepingCount(0),
          stateUpdateAuxUpdatesTotal(0),
          productionStateUpdateParentSeconds(0.0),
          productionStateUpdateBenchmarkCounterSeconds(0.0),
          productionStateUpdateTraceReplayRequiredStateSeconds(0.0),
          productionStateUpdateChildKnownSeconds(0.0),
          productionStateUpdateUnexplainedSeconds(0.0),
          productionStateUpdateSampledEventCount(0),
          productionStateUpdateCoveredSampledEventCount(0),
          productionStateUpdateUnclassifiedSampledEventCount(0),
          productionStateUpdateMultiChildSampledEventCount(0),
          productionStateUpdateBenchmarkCounterSampledEventCount(0),
          productionStateUpdateTraceReplayRequiredStateSampledEventCount(0),
          productionStateUpdateCoverageSource("placeholder"),
          productionStateUpdateEventCount(0),
          productionStateUpdateBenchmarkCounterCount(0),
          productionStateUpdateTraceReplayRequiredStateCount(0),
          timerCallCount(0),
          terminalTimerCallCount(0),
          lexicalTimerCallCount(0),
          candidateBytesWritten(0),
          startIndexBytesWritten(0),
          startIndexWriteDominantChild("unknown"),
          firstHalfSpanADominantChild("unknown"),
          firstHalfSpanA0DominantChild("unknown"),
          firstHalfSpanA0GapBeforeA00DominantChild("unknown"),
          firstHalfSpanA0GapBeforeA00Span0DominantChild("unknown"),
          firstHalfSpanA0GapBeforeA00Span0AltDominantChild("unknown"),
          firstHalfSpanA0GapBeforeA00Span0AltRightDominantChild("unknown"),
          firstHalfSpanA0GapBeforeA00Span0AltRightRepartDominantChild("unknown")
    {
    }

    double parentSeconds;
    double childKnownSeconds;
    double lexicalParentSeconds;
    double spanFirstHalfSeconds;
    double spanSecondHalfSeconds;
    double firstHalfParentSeconds;
    double firstHalfSpanASeconds;
    double firstHalfSpanAParentSeconds;
    double firstHalfSpanA0Seconds;
    double firstHalfSpanA1Seconds;
    double firstHalfSpanA0ParentSeconds;
    double firstHalfSpanA0GapBeforeA00Seconds;
    double firstHalfSpanA0GapBeforeA00ParentSeconds;
    double firstHalfSpanA0GapBeforeA00Span0Seconds;
    double firstHalfSpanA0GapBeforeA00Span0ParentSeconds;
    double firstHalfSpanA0GapBeforeA00Span0Child0Seconds;
    double firstHalfSpanA0GapBeforeA00Span0Child1Seconds;
    double firstHalfSpanA0GapBeforeA00Span0AltParentSeconds;
    double firstHalfSpanA0GapBeforeA00Span0AltLeftSeconds;
    double firstHalfSpanA0GapBeforeA00Span0AltRightSeconds;
    double firstHalfSpanA0GapBeforeA00Span0AltRightParentSeconds;
    double firstHalfSpanA0GapBeforeA00Span0AltRightChild0Seconds;
    double firstHalfSpanA0GapBeforeA00Span0AltRightChild1Seconds;
    double firstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSeconds;
    double firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSeconds;
    double firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSeconds;
    double firstHalfSpanA0GapBeforeA00Span1Seconds;
    double firstHalfSpanA00Seconds;
    double firstHalfSpanA0GapBetweenA00A01Seconds;
    double firstHalfSpanA01Seconds;
    double firstHalfSpanA0GapAfterA01Seconds;
    double firstHalfSpanA0GapBeforeA00ChildKnownSeconds;
    double firstHalfSpanA0GapBeforeA00UnexplainedSeconds;
    double firstHalfSpanA0GapBeforeA00Span0ChildKnownSeconds;
    double firstHalfSpanA0GapBeforeA00Span0UnexplainedSeconds;
    double firstHalfSpanA0GapBeforeA00Span0AltChildKnownSeconds;
    double firstHalfSpanA0GapBeforeA00Span0AltUnexplainedSeconds;
    double firstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSeconds;
    double firstHalfSpanA0GapBeforeA00Span0AltRightUnexplainedSeconds;
    double firstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSeconds;
    double firstHalfSpanA0GapBeforeA00Span0AltRightRepartUnexplainedSeconds;
    double firstHalfSpanA0ChildKnownSeconds;
    double firstHalfSpanA0UnexplainedSeconds;
    double firstHalfSpanAChildKnownSeconds;
    double firstHalfSpanAUnexplainedSeconds;
    double firstHalfSpanBSeconds;
    double firstHalfChildKnownSeconds;
    double firstHalfUnexplainedSeconds;
    double candidateSlotWriteSeconds;
    double startIndexWriteSeconds;
    double startIndexWriteParentSeconds;
    double startIndexWriteLeftSeconds;
    double startIndexWriteRightSeconds;
    double startIndexWriteChildKnownSeconds;
    double startIndexWriteUnexplainedSeconds;
    double startIndexStoreParentSeconds;
    double startIndexStoreInsertSeconds;
    double startIndexStoreClearSeconds;
    double startIndexStoreOverwriteSeconds;
    double startIndexStoreChildKnownSeconds;
    double startIndexStoreUnexplainedSeconds;
    double stateUpdateSeconds;
    double stateUpdateParentSeconds;
    double stateUpdateHeapBuildSeconds;
    double stateUpdateHeapUpdateSeconds;
    double stateUpdateStartIndexRebuildSeconds;
    double stateUpdateTraceOrProfileBookkeepingSeconds;
    double stateUpdateChildKnownSeconds;
    double stateUpdateUnexplainedSeconds;
    double telemetryOverheadSeconds;
    double residualSeconds;
    size_t eventCount;
    size_t firstHalfEventCount;
    size_t firstHalfSpanAEventCount;
    size_t firstHalfSpanA0EventCount;
    size_t firstHalfSpanA1EventCount;
    size_t firstHalfSpanA00EventCount;
    size_t firstHalfSpanA01EventCount;
    size_t firstHalfSpanBEventCount;
    size_t firstHalfSampledEventCount;
    size_t firstHalfSpanA0SampledEventCount;
    size_t firstHalfSpanA0CoveredSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00SampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00CoveredSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0SampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0CoveredSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0Child0SampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0Child1SampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltCoveredSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltLeftSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltRightSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltRightCoveredSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltRightChild0SampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltRightChild1SampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltRightRepartSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltRightRepartCoveredSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span1SampledEventCount;
    size_t firstHalfSpanA00SampledEventCount;
    size_t firstHalfSpanA0GapBetweenA00A01SampledEventCount;
    size_t firstHalfSpanA01SampledEventCount;
    size_t firstHalfSpanA0GapAfterA01SampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00UnclassifiedSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00MultiChildSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0UnclassifiedSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0MultiChildSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltUnclassifiedSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltMultiChildSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltRightUnclassifiedSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltRightMultiChildSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltRightRepartUnclassifiedSampledEventCount;
    size_t firstHalfSpanA0GapBeforeA00Span0AltRightRepartMultiChildSampledEventCount;
    size_t firstHalfSpanA0UnclassifiedSampledEventCount;
    size_t firstHalfSpanA0MultiChildSampledEventCount;
    size_t firstHalfSpanA0OverlapSampledEventCount;
    size_t candidateSlotWriteCount;
    size_t startIndexWriteCount;
    size_t startIndexWriteSampledEventCount;
    size_t startIndexWriteCoveredSampledEventCount;
    size_t startIndexWriteUnclassifiedSampledEventCount;
    size_t startIndexWriteMultiChildSampledEventCount;
    size_t startIndexWriteLeftSampledEventCount;
    size_t startIndexWriteRightSampledEventCount;
    size_t startIndexWriteInsertCount;
    size_t startIndexWriteUpdateExistingCount;
    size_t startIndexWriteClearCount;
    size_t startIndexWriteOverwriteCount;
    size_t startIndexWriteIdempotentCount;
    size_t startIndexWriteValueChangedCount;
    size_t startIndexWriteProbeCount;
    size_t startIndexWriteProbeStepsTotal;
    size_t startIndexStoreSampledEventCount;
    size_t startIndexStoreCoveredSampledEventCount;
    size_t startIndexStoreUnclassifiedSampledEventCount;
    size_t startIndexStoreMultiChildSampledEventCount;
    size_t startIndexStoreInsertSampledEventCount;
    size_t startIndexStoreClearSampledEventCount;
    size_t startIndexStoreOverwriteSampledEventCount;
    size_t startIndexStoreInsertCount;
    size_t startIndexStoreClearCount;
    size_t startIndexStoreOverwriteCount;
    size_t startIndexStoreInsertBytes;
    size_t startIndexStoreClearBytes;
    size_t startIndexStoreOverwriteBytes;
    size_t startIndexStoreUniqueEntryCount;
    size_t startIndexStoreUniqueSlotCount;
    size_t startIndexStoreUniqueKeyCount;
    size_t startIndexStoreSameEntryRewriteCount;
    size_t startIndexStoreSameCachelineRewriteCount;
    size_t startIndexStoreBackToBackSameEntryWriteCount;
    size_t startIndexStoreClearThenOverwriteSameEntryCount;
    size_t startIndexStoreOverwriteThenInsertSameEntryCount;
    size_t startIndexStoreInsertThenClearSameEntryCount;
    size_t stateUpdateCount;
    size_t stateUpdateSampledEventCount;
    size_t stateUpdateCoveredSampledEventCount;
    size_t stateUpdateUnclassifiedSampledEventCount;
    size_t stateUpdateMultiChildSampledEventCount;
    size_t stateUpdateHeapBuildSampledEventCount;
    size_t stateUpdateHeapUpdateSampledEventCount;
    size_t stateUpdateStartIndexRebuildSampledEventCount;
    size_t stateUpdateTraceOrProfileBookkeepingSampledEventCount;
    std::string stateUpdateCoverageSource;
    size_t stateUpdateEventCount;
    size_t stateUpdateHeapBuildCount;
    size_t stateUpdateHeapUpdateCount;
    size_t stateUpdateStartIndexRebuildCount;
    size_t stateUpdateTraceOrProfileBookkeepingCount;
    size_t stateUpdateAuxUpdatesTotal;
    double productionStateUpdateParentSeconds;
    double productionStateUpdateBenchmarkCounterSeconds;
    double productionStateUpdateTraceReplayRequiredStateSeconds;
    double productionStateUpdateChildKnownSeconds;
    double productionStateUpdateUnexplainedSeconds;
    size_t productionStateUpdateSampledEventCount;
    size_t productionStateUpdateCoveredSampledEventCount;
    size_t productionStateUpdateUnclassifiedSampledEventCount;
    size_t productionStateUpdateMultiChildSampledEventCount;
    size_t productionStateUpdateBenchmarkCounterSampledEventCount;
    size_t productionStateUpdateTraceReplayRequiredStateSampledEventCount;
    std::string productionStateUpdateCoverageSource;
    size_t productionStateUpdateEventCount;
    size_t productionStateUpdateBenchmarkCounterCount;
    size_t productionStateUpdateTraceReplayRequiredStateCount;
    size_t timerCallCount;
    size_t terminalTimerCallCount;
    size_t lexicalTimerCallCount;
    size_t candidateBytesWritten;
    size_t startIndexBytesWritten;
    std::string startIndexWriteDominantChild;
    std::string firstHalfSpanADominantChild;
    std::string firstHalfSpanA0DominantChild;
    std::string firstHalfSpanA0GapBeforeA00DominantChild;
    std::string firstHalfSpanA0GapBeforeA00Span0DominantChild;
    std::string firstHalfSpanA0GapBeforeA00Span0AltDominantChild;
    std::string firstHalfSpanA0GapBeforeA00Span0AltRightDominantChild;
    std::string firstHalfSpanA0GapBeforeA00Span0AltRightRepartDominantChild;
};

static size_t sim_candidate_start_index_entry_bytes()
{
    SimCandidateStartIndex index;
    return sizeof(index.slotState[0]) + sizeof(index.startI[0]) + sizeof(index.startJ[0]) +
           sizeof(index.candidateIndex[0]);
}

static TerminalPathDerivedMetrics derive_terminal_path_metrics(
    const SimInitialHostMergeReplayResult &replay)
{
    TerminalPathDerivedMetrics metrics;
    metrics.candidateSlotWriteSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackCandidateCopySeconds;
    metrics.startIndexWriteSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackKeyRebindSeconds;
    metrics.startIndexWriteParentSeconds = metrics.startIndexWriteSeconds;
    metrics.startIndexWriteLeftSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteLeftSeconds;
    metrics.startIndexWriteRightSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteRightSeconds;
    metrics.startIndexWriteChildKnownSeconds =
        metrics.startIndexWriteLeftSeconds + metrics.startIndexWriteRightSeconds;
    metrics.startIndexWriteUnexplainedSeconds =
        (metrics.startIndexWriteParentSeconds > metrics.startIndexWriteChildKnownSeconds)
            ? (metrics.startIndexWriteParentSeconds - metrics.startIndexWriteChildKnownSeconds)
            : 0.0;
    metrics.startIndexStoreParentSeconds = metrics.startIndexWriteRightSeconds;
    metrics.startIndexStoreInsertSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreInsertSeconds;
    metrics.startIndexStoreClearSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreClearSeconds;
    metrics.startIndexStoreOverwriteSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreOverwriteSeconds;
    metrics.startIndexStoreChildKnownSeconds =
        metrics.startIndexStoreInsertSeconds + metrics.startIndexStoreClearSeconds +
        metrics.startIndexStoreOverwriteSeconds;
    metrics.startIndexStoreUnexplainedSeconds =
        (metrics.startIndexStoreParentSeconds > metrics.startIndexStoreChildKnownSeconds)
            ? (metrics.startIndexStoreParentSeconds - metrics.startIndexStoreChildKnownSeconds)
            : 0.0;
    metrics.stateUpdateSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxHeapBuildSeconds +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxHeapUpdateSeconds +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxStartIndexRebuildSeconds;
    metrics.stateUpdateParentSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxBookkeepingSeconds;
    metrics.stateUpdateHeapBuildSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxHeapBuildSeconds;
    metrics.stateUpdateHeapUpdateSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxHeapUpdateSeconds;
    metrics.stateUpdateStartIndexRebuildSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxStartIndexRebuildSeconds;
    metrics.stateUpdateTraceOrProfileBookkeepingSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherSeconds;
    metrics.stateUpdateChildKnownSeconds =
        metrics.stateUpdateHeapBuildSeconds + metrics.stateUpdateHeapUpdateSeconds +
        metrics.stateUpdateStartIndexRebuildSeconds +
        metrics.stateUpdateTraceOrProfileBookkeepingSeconds;
    metrics.stateUpdateUnexplainedSeconds =
        (metrics.stateUpdateParentSeconds > metrics.stateUpdateChildKnownSeconds)
            ? (metrics.stateUpdateParentSeconds - metrics.stateUpdateChildKnownSeconds)
            : 0.0;
    metrics.telemetryOverheadSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherHeapUpdateAccountingSeconds +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherStartIndexRebuildAccountingSeconds +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherTraceFinalizeSeconds +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualHeapBuildAccountingSeconds +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualHeapUpdateTraceRecordSeconds +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualStartIndexRebuildTraceRecordSeconds;
    metrics.residualSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualResidualSeconds;
    metrics.parentSeconds =
        metrics.candidateSlotWriteSeconds + metrics.startIndexWriteSeconds +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxBookkeepingSeconds;
    metrics.childKnownSeconds =
        metrics.candidateSlotWriteSeconds + metrics.startIndexWriteSeconds +
        metrics.stateUpdateSeconds + metrics.telemetryOverheadSeconds + metrics.residualSeconds;
    metrics.lexicalParentSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalLexicalParentSeconds;
    metrics.spanFirstHalfSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalSpanFirstHalfSeconds;
    metrics.spanSecondHalfSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalSpanSecondHalfSeconds;
    metrics.firstHalfParentSeconds = metrics.spanFirstHalfSeconds;
    metrics.firstHalfSpanASeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanASeconds;
    metrics.firstHalfSpanAParentSeconds = metrics.firstHalfSpanASeconds;
    metrics.firstHalfSpanA0Seconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0Seconds;
    metrics.firstHalfSpanA1Seconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA1Seconds;
    metrics.firstHalfSpanA0ParentSeconds = metrics.firstHalfSpanA0Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Seconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Seconds;
    metrics.firstHalfSpanA0GapBeforeA00ParentSeconds =
        metrics.firstHalfSpanA0GapBeforeA00Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0Seconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span0Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0ParentSeconds =
        metrics.firstHalfSpanA0GapBeforeA00Span0Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0Child0Seconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span0Child0Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0Child1Seconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span0Child1Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltParentSeconds =
        metrics.firstHalfSpanA0GapBeforeA00ParentSeconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltLeftSeconds =
        metrics.firstHalfSpanA0GapBeforeA00Span0Child0Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Span1Seconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span1Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSeconds =
        metrics.firstHalfSpanA0GapBeforeA00Span0Child1Seconds +
        metrics.firstHalfSpanA0GapBeforeA00Span1Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightParentSeconds =
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSeconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild0Seconds =
        metrics.firstHalfSpanA0GapBeforeA00Span0Child1Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild1Seconds =
        metrics.firstHalfSpanA0GapBeforeA00Span1Seconds;
    metrics.firstHalfSpanA00Seconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA00Seconds;
    metrics.firstHalfSpanA0GapBetweenA00A01Seconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBetweenA00A01Seconds;
    metrics.firstHalfSpanA01Seconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA01Seconds;
    metrics.firstHalfSpanA0GapAfterA01Seconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapAfterA01Seconds;
    metrics.firstHalfSpanA0GapBeforeA00ChildKnownSeconds =
        metrics.firstHalfSpanA0GapBeforeA00Span0Seconds +
        metrics.firstHalfSpanA0GapBeforeA00Span1Seconds;
    metrics.firstHalfSpanA0GapBeforeA00UnexplainedSeconds =
        (metrics.firstHalfSpanA0GapBeforeA00ParentSeconds >
         metrics.firstHalfSpanA0GapBeforeA00ChildKnownSeconds)
            ? (metrics.firstHalfSpanA0GapBeforeA00ParentSeconds -
               metrics.firstHalfSpanA0GapBeforeA00ChildKnownSeconds)
            : 0.0;
    metrics.firstHalfSpanA0GapBeforeA00Span0ChildKnownSeconds =
        metrics.firstHalfSpanA0GapBeforeA00Span0Child0Seconds +
        metrics.firstHalfSpanA0GapBeforeA00Span0Child1Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0UnexplainedSeconds =
        (metrics.firstHalfSpanA0GapBeforeA00Span0ParentSeconds >
         metrics.firstHalfSpanA0GapBeforeA00Span0ChildKnownSeconds)
            ? (metrics.firstHalfSpanA0GapBeforeA00Span0ParentSeconds -
               metrics.firstHalfSpanA0GapBeforeA00Span0ChildKnownSeconds)
            : 0.0;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltChildKnownSeconds =
        metrics.firstHalfSpanA0GapBeforeA00Span0AltLeftSeconds +
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSeconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltUnexplainedSeconds =
        (metrics.firstHalfSpanA0GapBeforeA00Span0AltParentSeconds >
         metrics.firstHalfSpanA0GapBeforeA00Span0AltChildKnownSeconds)
            ? (metrics.firstHalfSpanA0GapBeforeA00Span0AltParentSeconds -
               metrics.firstHalfSpanA0GapBeforeA00Span0AltChildKnownSeconds)
            : 0.0;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSeconds =
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild0Seconds +
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild1Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightUnexplainedSeconds =
        (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightParentSeconds >
         metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSeconds)
            ? (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightParentSeconds -
               metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSeconds)
            : 0.0;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSeconds =
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSeconds + metrics.firstHalfSpanA00Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSeconds =
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSeconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSeconds =
        metrics.firstHalfSpanA00Seconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSeconds =
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSeconds +
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSeconds;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartUnexplainedSeconds =
        (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSeconds >
         metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSeconds)
            ? (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSeconds -
               metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSeconds)
            : 0.0;
    metrics.firstHalfSpanA0ChildKnownSeconds =
        metrics.firstHalfSpanA0GapBeforeA00Seconds + metrics.firstHalfSpanA00Seconds +
        metrics.firstHalfSpanA0GapBetweenA00A01Seconds + metrics.firstHalfSpanA01Seconds +
        metrics.firstHalfSpanA0GapAfterA01Seconds;
    metrics.firstHalfSpanA0UnexplainedSeconds =
        (metrics.firstHalfSpanA0ParentSeconds > metrics.firstHalfSpanA0ChildKnownSeconds)
            ? (metrics.firstHalfSpanA0ParentSeconds - metrics.firstHalfSpanA0ChildKnownSeconds)
            : 0.0;
    metrics.firstHalfSpanAChildKnownSeconds =
        metrics.firstHalfSpanA0Seconds + metrics.firstHalfSpanA1Seconds;
    metrics.firstHalfSpanAUnexplainedSeconds =
        (metrics.firstHalfSpanAParentSeconds > metrics.firstHalfSpanAChildKnownSeconds)
            ? (metrics.firstHalfSpanAParentSeconds - metrics.firstHalfSpanAChildKnownSeconds)
            : 0.0;
    metrics.firstHalfSpanBSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanBSeconds;
    metrics.firstHalfChildKnownSeconds =
        metrics.firstHalfSpanASeconds + metrics.firstHalfSpanBSeconds;
    metrics.firstHalfUnexplainedSeconds =
        (metrics.firstHalfParentSeconds > metrics.firstHalfChildKnownSeconds)
            ? (metrics.firstHalfParentSeconds - metrics.firstHalfChildKnownSeconds)
            : 0.0;
    metrics.eventCount = replay.storeOtherMergeContextApplyFullSetMissCount;
    metrics.firstHalfEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfEventCount;
    metrics.firstHalfSpanAEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanAEventCount;
    metrics.firstHalfSpanA0EventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0EventCount;
    metrics.firstHalfSpanA1EventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA1EventCount;
    metrics.firstHalfSpanA00EventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA00EventCount;
    metrics.firstHalfSpanA01EventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA01EventCount;
    metrics.firstHalfSpanBEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanBEventCount;
    metrics.firstHalfSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSampledEventCount;
    metrics.firstHalfSpanA0SampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0Count;
    metrics.firstHalfSpanA0CoveredSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0CoveredSampledEventCount;
    metrics.firstHalfSpanA0GapBeforeA00SampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Count;
    metrics.firstHalfSpanA0GapBeforeA00CoveredSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00CoveredSampledEventCount;
    metrics.firstHalfSpanA0GapBeforeA00Span0SampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span0Count;
    metrics.firstHalfSpanA0GapBeforeA00Span0CoveredSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span0CoveredSampledEventCount;
    metrics.firstHalfSpanA0GapBeforeA00Span0Child0SampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span0Child0Count;
    metrics.firstHalfSpanA0GapBeforeA00Span0Child1SampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span0Child1Count;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltSampledEventCount =
        metrics.firstHalfSpanA0GapBeforeA00SampledEventCount;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltCoveredSampledEventCount =
        metrics.firstHalfSpanA0GapBeforeA00CoveredSampledEventCount;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltLeftSampledEventCount =
        metrics.firstHalfSpanA0GapBeforeA00Span0Child0SampledEventCount;
    metrics.firstHalfSpanA0GapBeforeA00Span1SampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span1Count;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSampledEventCount =
        std::max(metrics.firstHalfSpanA0GapBeforeA00Span0Child1SampledEventCount,
                 metrics.firstHalfSpanA0GapBeforeA00Span1SampledEventCount);
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild0SampledEventCount =
        metrics.firstHalfSpanA0GapBeforeA00Span0Child1SampledEventCount;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild1SampledEventCount =
        metrics.firstHalfSpanA0GapBeforeA00Span1SampledEventCount;
    metrics.firstHalfSpanA00SampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA00Count;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartSampledEventCount =
        std::max(metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSampledEventCount,
                 metrics.firstHalfSpanA00SampledEventCount);
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSampledEventCount =
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSampledEventCount;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSampledEventCount =
        metrics.firstHalfSpanA00SampledEventCount;
    metrics.firstHalfSpanA0GapBetweenA00A01SampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBetweenA00A01Count;
    metrics.firstHalfSpanA01SampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA01Count;
    metrics.firstHalfSpanA0GapAfterA01SampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapAfterA01Count;
    metrics.firstHalfSpanA0GapBeforeA00UnclassifiedSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00UnclassifiedSampledEventCount;
    metrics.firstHalfSpanA0GapBeforeA00MultiChildSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00MultiChildSampledEventCount;
    metrics.firstHalfSpanA0GapBeforeA00Span0UnclassifiedSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span0UnclassifiedSampledEventCount;
    metrics.firstHalfSpanA0GapBeforeA00Span0MultiChildSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span0MultiChildSampledEventCount;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltUnclassifiedSampledEventCount =
        metrics.firstHalfSpanA0GapBeforeA00UnclassifiedSampledEventCount;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltMultiChildSampledEventCount =
        std::min(metrics.firstHalfSpanA0GapBeforeA00Span0AltCoveredSampledEventCount,
                 std::min(metrics.firstHalfSpanA0GapBeforeA00Span0AltLeftSampledEventCount,
                          metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSampledEventCount));
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightCoveredSampledEventCount =
        std::min(metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSampledEventCount,
                 std::max(metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild0SampledEventCount,
                          metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild1SampledEventCount));
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightUnclassifiedSampledEventCount =
        (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSampledEventCount >
         metrics.firstHalfSpanA0GapBeforeA00Span0AltRightCoveredSampledEventCount)
            ? (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSampledEventCount -
               metrics.firstHalfSpanA0GapBeforeA00Span0AltRightCoveredSampledEventCount)
            : 0;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightMultiChildSampledEventCount =
        std::min(metrics.firstHalfSpanA0GapBeforeA00Span0AltRightCoveredSampledEventCount,
                 std::min(metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild0SampledEventCount,
                          metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild1SampledEventCount));
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartCoveredSampledEventCount =
        std::min(metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartSampledEventCount,
                 std::max(metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSampledEventCount,
                          metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSampledEventCount));
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartUnclassifiedSampledEventCount =
        (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartSampledEventCount >
         metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartCoveredSampledEventCount)
            ? (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartSampledEventCount -
               metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartCoveredSampledEventCount)
            : 0;
    metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartMultiChildSampledEventCount =
        std::min(metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartCoveredSampledEventCount,
                 std::min(metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSampledEventCount,
                          metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSampledEventCount));
    metrics.firstHalfSpanA0UnclassifiedSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0UnclassifiedSampledEventCount;
    metrics.firstHalfSpanA0MultiChildSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0MultiChildSampledEventCount;
    metrics.firstHalfSpanA0OverlapSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0OverlapSampledEventCount;
    metrics.candidateSlotWriteCount = replay.storeOtherMergeContextApplyFullSetMissCount;
    metrics.startIndexWriteCount = replay.storeOtherMergeContextApplyFullSetMissCount;
    metrics.startIndexWriteSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteSampledEventCount;
    metrics.startIndexWriteCoveredSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteCoveredSampledEventCount;
    metrics.startIndexWriteUnclassifiedSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteUnclassifiedSampledEventCount;
    metrics.startIndexWriteMultiChildSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteMultiChildSampledEventCount;
    metrics.startIndexWriteLeftSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteLeftSampledEventCount;
    metrics.startIndexWriteRightSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteRightSampledEventCount;
    metrics.startIndexWriteInsertCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteInsertCount;
    metrics.startIndexWriteUpdateExistingCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteUpdateExistingCount;
    metrics.startIndexWriteClearCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteClearCount;
    metrics.startIndexWriteOverwriteCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteOverwriteCount;
    metrics.startIndexWriteIdempotentCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteIdempotentCount;
    metrics.startIndexWriteValueChangedCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteValueChangedCount;
    metrics.startIndexWriteProbeCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteProbeCount;
    metrics.startIndexWriteProbeStepsTotal =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexWriteProbeStepsTotal;
    metrics.startIndexStoreSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreSampledEventCount;
    metrics.startIndexStoreCoveredSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreCoveredSampledEventCount;
    metrics.startIndexStoreUnclassifiedSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreUnclassifiedSampledEventCount;
    metrics.startIndexStoreMultiChildSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreMultiChildSampledEventCount;
    metrics.startIndexStoreInsertSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreInsertSampledEventCount;
    metrics.startIndexStoreClearSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreClearSampledEventCount;
    metrics.startIndexStoreOverwriteSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreOverwriteSampledEventCount;
    metrics.startIndexStoreInsertCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreInsertCount;
    metrics.startIndexStoreClearCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreClearCount;
    metrics.startIndexStoreOverwriteCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreOverwriteCount;
    metrics.startIndexStoreInsertBytes =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreInsertBytes;
    metrics.startIndexStoreClearBytes =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreClearBytes;
    metrics.startIndexStoreOverwriteBytes =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreOverwriteBytes;
    metrics.startIndexStoreUniqueEntryCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreUniqueEntryCount;
    metrics.startIndexStoreUniqueSlotCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreUniqueSlotCount;
    metrics.startIndexStoreUniqueKeyCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreUniqueKeyCount;
    metrics.startIndexStoreSameEntryRewriteCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreSameEntryRewriteCount;
    metrics.startIndexStoreSameCachelineRewriteCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreSameCachelineRewriteCount;
    metrics.startIndexStoreBackToBackSameEntryWriteCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreBackToBackSameEntryWriteCount;
    metrics.startIndexStoreClearThenOverwriteSameEntryCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreClearThenOverwriteSameEntryCount;
    metrics.startIndexStoreOverwriteThenInsertSameEntryCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreOverwriteThenInsertSameEntryCount;
    metrics.startIndexStoreInsertThenClearSameEntryCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStartIndexStoreInsertThenClearSameEntryCount;
    metrics.stateUpdateSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStateUpdateSampledEventCount;
    metrics.stateUpdateCoveredSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStateUpdateCoveredSampledEventCount;
    metrics.stateUpdateUnclassifiedSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStateUpdateUnclassifiedSampledEventCount;
    metrics.stateUpdateMultiChildSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStateUpdateMultiChildSampledEventCount;
    metrics.stateUpdateHeapBuildSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStateUpdateHeapBuildSampledEventCount;
    metrics.stateUpdateHeapUpdateSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStateUpdateHeapUpdateSampledEventCount;
    metrics.stateUpdateStartIndexRebuildSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStateUpdateStartIndexRebuildSampledEventCount;
    metrics.stateUpdateTraceOrProfileBookkeepingSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalStateUpdateTraceOrProfileBookkeepingSampledEventCount;
    metrics.stateUpdateCoverageSource = "event_level_sampled";
    metrics.stateUpdateHeapBuildCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxHeapBuildCount;
    metrics.stateUpdateHeapUpdateCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxHeapUpdateCount;
    metrics.stateUpdateStartIndexRebuildCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxStartIndexRebuildCount;
    metrics.stateUpdateTraceOrProfileBookkeepingCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherHeapUpdateAccountingCount +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherStartIndexRebuildAccountingCount +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherTraceFinalizeCount +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualHeapBuildAccountingCount +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualHeapUpdateTraceRecordCount +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualStartIndexRebuildTraceRecordCount;
    metrics.stateUpdateCount =
        metrics.stateUpdateHeapBuildCount + metrics.stateUpdateHeapUpdateCount +
        metrics.stateUpdateStartIndexRebuildCount;
    metrics.stateUpdateEventCount = metrics.stateUpdateCount;
    metrics.stateUpdateAuxUpdatesTotal = metrics.stateUpdateCount;
    metrics.productionStateUpdateBenchmarkCounterSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxProductionBenchmarkCounterSeconds;
    metrics.productionStateUpdateTraceReplayRequiredStateSeconds =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxProductionTraceReplayStateSeconds;
    metrics.productionStateUpdateParentSeconds =
        metrics.productionStateUpdateBenchmarkCounterSeconds +
        metrics.productionStateUpdateTraceReplayRequiredStateSeconds;
    metrics.productionStateUpdateChildKnownSeconds =
        metrics.productionStateUpdateParentSeconds;
    metrics.productionStateUpdateUnexplainedSeconds = 0.0;
    metrics.productionStateUpdateSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalProductionStateUpdateSampledEventCount;
    metrics.productionStateUpdateCoveredSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalProductionStateUpdateCoveredSampledEventCount;
    metrics.productionStateUpdateUnclassifiedSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalProductionStateUpdateUnclassifiedSampledEventCount;
    metrics.productionStateUpdateMultiChildSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalProductionStateUpdateMultiChildSampledEventCount;
    metrics.productionStateUpdateBenchmarkCounterSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalProductionStateUpdateBenchmarkCounterSampledEventCount;
    metrics.productionStateUpdateTraceReplayRequiredStateSampledEventCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalProductionStateUpdateTraceReplayStateSampledEventCount;
    metrics.productionStateUpdateCoverageSource = "event_level_sampled";
    metrics.productionStateUpdateBenchmarkCounterCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxProductionBenchmarkCounterCount;
    metrics.productionStateUpdateTraceReplayRequiredStateCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxProductionTraceReplayStateCount;
    metrics.productionStateUpdateEventCount = std::max(
        metrics.productionStateUpdateBenchmarkCounterCount,
        metrics.productionStateUpdateTraceReplayRequiredStateCount);
    metrics.terminalTimerCallCount =
        (metrics.parentSeconds > 0.0 || metrics.childKnownSeconds > 0.0)
            ? (replay.storeOtherMergeContextApplyLookupMissReuseWritebackCandidateCopyCount +
               replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxBookkeepingCount +
               replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxHeapBuildCount +
               replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxHeapUpdateCount +
               replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxStartIndexRebuildCount +
               replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherHeapUpdateAccountingCount +
               replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherStartIndexRebuildAccountingCount +
               replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherTraceFinalizeCount +
               replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualHeapBuildAccountingCount +
               replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualHeapUpdateTraceRecordCount +
               replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualStartIndexRebuildTraceRecordCount)
            : 0;
    metrics.lexicalTimerCallCount =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalLexicalParentCount +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalSpanFirstHalfCount +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalSpanSecondHalfCount +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanACount +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0Count +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA1Count +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Count +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span0Count +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span0Child0Count +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBeforeA00Span0Child1Count +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA00Count +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapBetweenA00A01Count +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA01Count +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanA0GapAfterA01Count +
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackTerminalFirstHalfSpanBCount;
    metrics.timerCallCount = metrics.terminalTimerCallCount + metrics.lexicalTimerCallCount;
    metrics.candidateBytesWritten =
        replay.storeOtherMergeContextApplyLookupMissReuseWritebackPayloadBytesTotal;
    metrics.startIndexBytesWritten =
        replay.storeOtherMergeContextApplyFullSetMissCount * sim_candidate_start_index_entry_bytes();
    if (metrics.startIndexWriteLeftSeconds > metrics.startIndexWriteRightSeconds)
    {
        metrics.startIndexWriteDominantChild = "left";
    }
    else if (metrics.startIndexWriteRightSeconds > metrics.startIndexWriteLeftSeconds)
    {
        metrics.startIndexWriteDominantChild = "right";
    }
    if (metrics.firstHalfSpanA0Seconds > metrics.firstHalfSpanA1Seconds)
    {
        metrics.firstHalfSpanADominantChild = "span_a0";
    }
    else if (metrics.firstHalfSpanA1Seconds > metrics.firstHalfSpanA0Seconds)
    {
        metrics.firstHalfSpanADominantChild = "span_a1";
    }
    else if (metrics.firstHalfSpanAParentSeconds > 0.0)
    {
        metrics.firstHalfSpanADominantChild = "mixed";
    }
    if (metrics.firstHalfSpanA0GapBeforeA00Seconds > metrics.firstHalfSpanA00Seconds &&
        metrics.firstHalfSpanA0GapBeforeA00Seconds > metrics.firstHalfSpanA0GapBetweenA00A01Seconds &&
        metrics.firstHalfSpanA0GapBeforeA00Seconds > metrics.firstHalfSpanA01Seconds &&
        metrics.firstHalfSpanA0GapBeforeA00Seconds > metrics.firstHalfSpanA0GapAfterA01Seconds)
    {
        metrics.firstHalfSpanA0DominantChild = "gap_before_a00";
    }
    else if (metrics.firstHalfSpanA00Seconds > metrics.firstHalfSpanA0GapBetweenA00A01Seconds &&
             metrics.firstHalfSpanA00Seconds > metrics.firstHalfSpanA01Seconds &&
             metrics.firstHalfSpanA00Seconds > metrics.firstHalfSpanA0GapAfterA01Seconds)
    {
        metrics.firstHalfSpanA0DominantChild = "span_a00";
    }
    else if (metrics.firstHalfSpanA0GapBetweenA00A01Seconds > metrics.firstHalfSpanA01Seconds &&
             metrics.firstHalfSpanA0GapBetweenA00A01Seconds > metrics.firstHalfSpanA0GapAfterA01Seconds)
    {
        metrics.firstHalfSpanA0DominantChild = "gap_between_a00_a01";
    }
    else if (metrics.firstHalfSpanA01Seconds > metrics.firstHalfSpanA0GapAfterA01Seconds)
    {
        metrics.firstHalfSpanA0DominantChild = "span_a01";
    }
    else if (metrics.firstHalfSpanA0GapAfterA01Seconds > 0.0)
    {
        metrics.firstHalfSpanA0DominantChild = "gap_after_a01";
    }
    else if (metrics.firstHalfSpanA0ParentSeconds > 0.0)
    {
        metrics.firstHalfSpanA0DominantChild = "mixed";
    }
    if (metrics.firstHalfSpanA0GapBeforeA00Span0Seconds >
        metrics.firstHalfSpanA0GapBeforeA00Span1Seconds)
    {
        metrics.firstHalfSpanA0GapBeforeA00DominantChild = "span_0";
    }
    else if (metrics.firstHalfSpanA0GapBeforeA00Span1Seconds >
             metrics.firstHalfSpanA0GapBeforeA00Span0Seconds)
    {
        metrics.firstHalfSpanA0GapBeforeA00DominantChild = "span_1";
    }
    else if (metrics.firstHalfSpanA0GapBeforeA00ParentSeconds > 0.0)
    {
        metrics.firstHalfSpanA0GapBeforeA00DominantChild = "mixed";
    }
    if (metrics.firstHalfSpanA0GapBeforeA00Span0Child0Seconds >
        metrics.firstHalfSpanA0GapBeforeA00Span0Child1Seconds)
    {
        metrics.firstHalfSpanA0GapBeforeA00Span0DominantChild = "child_0";
    }
    else if (metrics.firstHalfSpanA0GapBeforeA00Span0Child1Seconds >
             metrics.firstHalfSpanA0GapBeforeA00Span0Child0Seconds)
    {
        metrics.firstHalfSpanA0GapBeforeA00Span0DominantChild = "child_1";
    }
    else if (metrics.firstHalfSpanA0GapBeforeA00Span0ParentSeconds > 0.0)
    {
        metrics.firstHalfSpanA0GapBeforeA00Span0DominantChild = "mixed";
    }
    if (metrics.firstHalfSpanA0GapBeforeA00Span0AltLeftSeconds >
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSeconds)
    {
        metrics.firstHalfSpanA0GapBeforeA00Span0AltDominantChild = "alt_left";
    }
    else if (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightSeconds >
             metrics.firstHalfSpanA0GapBeforeA00Span0AltLeftSeconds)
    {
        metrics.firstHalfSpanA0GapBeforeA00Span0AltDominantChild = "alt_right";
    }
    else if (metrics.firstHalfSpanA0GapBeforeA00Span0AltParentSeconds > 0.0)
    {
        metrics.firstHalfSpanA0GapBeforeA00Span0AltDominantChild = "mixed";
    }
    if (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild0Seconds >
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild1Seconds)
    {
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightDominantChild = "child_0";
    }
    else if (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild1Seconds >
             metrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild0Seconds)
    {
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightDominantChild = "child_1";
    }
    else if (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightParentSeconds > 0.0)
    {
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightDominantChild = "mixed";
    }
    if (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSeconds >
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSeconds)
    {
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartDominantChild = "repart_left";
    }
    else if (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSeconds >
             metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSeconds)
    {
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartDominantChild = "repart_right";
    }
    else if (metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSeconds > 0.0)
    {
        metrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartDominantChild = "mixed";
    }
    return metrics;
}

struct HostMergeWorkloadBenchmarkMetrics
{
    HostMergeWorkloadBenchmarkMetrics()
        : hasSimInitialScanSeconds(false),
          hasSimInitialScanCpuMergeSeconds(false),
          hasSimInitialScanCpuMergeSubtotalSeconds(false),
          hasSimSeconds(false),
          hasTotalSeconds(false),
          simInitialScanSeconds(0.0),
          simInitialScanCpuMergeSeconds(0.0),
          simInitialScanCpuMergeSubtotalSeconds(0.0),
          simSeconds(0.0),
          totalSeconds(0.0)
    {
    }

    bool hasSimInitialScanSeconds;
    bool hasSimInitialScanCpuMergeSeconds;
    bool hasSimInitialScanCpuMergeSubtotalSeconds;
    bool hasSimSeconds;
    bool hasTotalSeconds;
    double simInitialScanSeconds;
    double simInitialScanCpuMergeSeconds;
    double simInitialScanCpuMergeSubtotalSeconds;
    double simSeconds;
    double totalSeconds;
};

static bool parse_prefixed_metric(const std::string &line,
                                  const char *prefix,
                                  double &value)
{
    const std::string prefixText(prefix);
    if (line.compare(0, prefixText.size(), prefixText) != 0)
    {
        return false;
    }
    try
    {
        value = std::stod(line.substr(prefixText.size()));
    }
    catch (const std::exception &)
    {
        return false;
    }
    return true;
}

static bool load_workload_benchmark_metrics(const std::string &path,
                                            HostMergeWorkloadBenchmarkMetrics &metrics,
                                            std::string *errorOut)
{
    metrics = HostMergeWorkloadBenchmarkMetrics();
    if (path.empty())
    {
        return true;
    }

    std::ifstream input(path.c_str());
    if (!input)
    {
        if (errorOut != NULL)
        {
            *errorOut = "Unable to open benchmark stderr log: " + path;
        }
        return false;
    }

    std::string line;
    while (std::getline(input, line))
    {
        double value = 0.0;
        if (parse_prefixed_metric(line, "benchmark.sim_initial_scan_seconds=", value))
        {
            metrics.hasSimInitialScanSeconds = true;
            metrics.simInitialScanSeconds = value;
            continue;
        }
        if (parse_prefixed_metric(line, "benchmark.sim_initial_scan_cpu_merge_seconds=", value))
        {
            metrics.hasSimInitialScanCpuMergeSeconds = true;
            metrics.simInitialScanCpuMergeSeconds = value;
            continue;
        }
        if (parse_prefixed_metric(line, "benchmark.sim_initial_scan_cpu_merge_subtotal_seconds=", value))
        {
            metrics.hasSimInitialScanCpuMergeSubtotalSeconds = true;
            metrics.simInitialScanCpuMergeSubtotalSeconds = value;
            continue;
        }
        if (parse_prefixed_metric(line, "benchmark.sim_seconds=", value))
        {
            metrics.hasSimSeconds = true;
            metrics.simSeconds = value;
            continue;
        }
        if (parse_prefixed_metric(line, "benchmark.total_seconds=", value))
        {
            metrics.hasTotalSeconds = true;
            metrics.totalSeconds = value;
            continue;
        }
    }
    return true;
}

static void write_optional_metric(std::ostream &output, bool hasValue, double value)
{
    if (hasValue)
    {
        output << value;
    }
}
} // namespace

int main(int argc, char **argv)
{
    std::string corpusDir(".");
    std::string caseId;
    std::string outputTsvPath;
    std::string aggregateTsvPath;
    std::string benchmarkStderrPath;
    std::string workloadId;
    std::string benchmarkSourceOriginalPath;
    std::string benchmarkSourceCopiedPath;
    std::string benchmarkSourceSha256;
    std::string benchmarkIdentityBasis;
    bool selectAll = false;
    bool verify = false;
    SimCandidateIndexBackend candidateIndexBackend = SIM_CANDIDATE_INDEX_BACKEND_TOMBSTONE;
    SimInitialProfilerMode profileMode = SIM_INITIAL_PROFILER_MODE_LEXICAL_FIRST_HALF;
    SimInitialTerminalTelemetryOverheadMode terminalTelemetryOverheadMode =
        SIM_INITIAL_TERMINAL_TELEMETRY_OVERHEAD_AUTO;
    unsigned profileSampleLog2 = simInitialProfilerSampleLog2();
    size_t benchmarkSourceSizeBytes = 0;
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
        else if (argument == "--candidate-index-backend")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            if (!parse_candidate_index_backend(argv[++index], candidateIndexBackend))
            {
                std::cerr << "Unsupported candidate-index backend: " << argv[index] << "\n";
                return 1;
            }
        }
        else if (argument == "--profile-mode")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            if (!parse_profile_mode(argv[++index], profileMode))
            {
                std::cerr << "Unsupported profile mode: " << argv[index] << "\n";
                return 1;
            }
        }
        else if (argument == "--profile-sample-log2")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            profileSampleLog2 = static_cast<unsigned>(strtoul(argv[++index], NULL, 10));
        }
        else if (argument == "--terminal-telemetry-overhead")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            if (!parse_terminal_telemetry_overhead_mode(argv[++index],
                                                        terminalTelemetryOverheadMode))
            {
                std::cerr << "Unsupported terminal telemetry overhead mode: "
                          << argv[index] << "\n";
                return 1;
            }
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
        else if (argument == "--benchmark-stderr")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            benchmarkStderrPath = argv[++index];
        }
        else if (argument == "--workload-id")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            workloadId = argv[++index];
        }
        else if (argument == "--benchmark-source-original-path")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            benchmarkSourceOriginalPath = argv[++index];
        }
        else if (argument == "--benchmark-source-copied-path")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            benchmarkSourceCopiedPath = argv[++index];
        }
        else if (argument == "--benchmark-source-sha256")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            benchmarkSourceSha256 = argv[++index];
        }
        else if (argument == "--benchmark-source-size-bytes")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            benchmarkSourceSizeBytes = static_cast<size_t>(strtoull(argv[++index], NULL, 10));
        }
        else if (argument == "--benchmark-identity-basis")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            benchmarkIdentityBasis = argv[++index];
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

    if (benchmarkSourceOriginalPath.empty())
    {
        benchmarkSourceOriginalPath = benchmarkStderrPath;
    }
    if (benchmarkSourceCopiedPath.empty())
    {
        benchmarkSourceCopiedPath = benchmarkStderrPath;
    }
    if (benchmarkIdentityBasis.empty() && !benchmarkSourceSha256.empty())
    {
        benchmarkIdentityBasis = "content_sha256";
    }
    else if (benchmarkIdentityBasis.empty() && !benchmarkStderrPath.empty())
    {
        benchmarkIdentityBasis = "source_path";
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

    HostMergeWorkloadBenchmarkMetrics workloadBenchmarkMetrics;
    if (!load_workload_benchmark_metrics(benchmarkStderrPath, workloadBenchmarkMetrics, &error))
    {
        std::cerr << error << "\n";
        return 1;
    }

    simSetInitialProfilerMode(profileMode);
    simSetInitialProfilerSampleLog2(profileSampleLog2);
    simSetInitialTerminalTelemetryOverheadMode(terminalTelemetryOverheadMode);

    std::stringstream tsv;
    tsv << "case_id\tcandidate_index_backend\tprofile_mode\tprofile_sample_log2\tprofile_sample_rate"
        << "\tterminal_telemetry_overhead_mode_requested\tterminal_telemetry_overhead_mode_effective"
        << "\tstate_update_bookkeeping_mode_requested\tstate_update_bookkeeping_mode_effective"
        << "\tlogical_event_count\tcontext_candidate_count_after_context_apply"
        << "\trunning_min_after_context_apply\tcontext_apply_seconds"
        << "\tcontext_apply_full_set_miss_seconds"
        << "\tcontext_apply_refresh_min_seconds"
        << "\tcontext_apply_candidate_index_seconds"
        << "\tcontext_apply_candidate_index_erase_seconds"
        << "\tcontext_apply_candidate_index_insert_seconds"
        << "\tcontext_apply_lookup_seconds\tcontext_apply_lookup_hit_seconds"
        << "\tcontext_apply_lookup_miss_seconds\tcontext_apply_lookup_miss_open_slot_seconds"
        << "\tcontext_apply_lookup_miss_candidate_set_full_probe_seconds"
        << "\tcontext_apply_lookup_miss_eviction_select_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_victim_reset_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_key_rebind_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_candidate_copy_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_aux_bookkeeping_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_build_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_update_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_aux_start_index_rebuild_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_parent_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_child_known_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_candidate_slot_write_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_parent_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_child_known_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_unexplained_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_parent_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_child_known_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_unexplained_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_telemetry_overhead_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_residual_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_lexical_parent_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_span_first_half_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_span_second_half_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_parent_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_parent_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a1_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_parent_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_parent_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_parent_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_0_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_1_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_1_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_child_known_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_unexplained_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_known_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child_known_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_known_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unexplained_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_known_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unexplained_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a00_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_between_a00_a01_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a01_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_after_a01_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_child_known_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_unexplained_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_child_known_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_unexplained_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_b_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_child_known_seconds"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_unexplained_seconds"
        << "\tdominant_terminal_first_half_span_a_child"
        << "\tdominant_terminal_first_half_span_a0_child"
        << "\tdominant_terminal_first_half_span_a0_gap_before_a00_child"
        << "\tdominant_terminal_first_half_span_a0_gap_before_a00_span_0_child"
        << "\tdominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child"
        << "\tdominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child"
        << "\tdominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child"
        << "\tcontext_apply_mutate_seconds\tcontext_apply_finalize_seconds"
        << "\tcontext_apply_attempted_count\tcontext_apply_modified_count"
        << "\tcontext_apply_noop_count\tcontext_apply_lookup_hit_count"
        << "\tcontext_apply_full_set_miss_count"
        << "\tcontext_apply_floor_changed_count"
        << "\tcontext_apply_floor_changed_share"
        << "\tcontext_apply_running_min_slot_changed_count"
        << "\tcontext_apply_running_min_slot_changed_share"
        << "\tcontext_apply_victim_was_running_min_count"
        << "\tcontext_apply_victim_was_running_min_share"
        << "\tcontext_apply_refresh_min_calls"
        << "\tcontext_apply_refresh_min_slots_scanned"
        << "\tcontext_apply_refresh_min_slots_scanned_per_call"
        << "\tcontext_apply_candidate_index_lookup_count"
        << "\tcontext_apply_candidate_index_hit_count"
        << "\tcontext_apply_candidate_index_miss_count"
        << "\tcontext_apply_candidate_index_erase_count"
        << "\tcontext_apply_candidate_index_insert_count"
        << "\tcontext_apply_lookup_miss_count\tcontext_apply_lookup_probe_steps_total"
        << "\tcontext_apply_lookup_probe_steps_max\tcontext_apply_lookup_miss_open_slot_count"
        << "\tcontext_apply_lookup_miss_candidate_set_full_count"
        << "\tcontext_apply_eviction_selected_count\tcontext_apply_reused_slot_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a1_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a00_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a01_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_b_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_covered_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_covered_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_covered_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_0_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_1_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_covered_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_covered_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_1_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a00_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_between_a00_a01_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a01_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_after_a01_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_unclassified_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_multi_child_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_unclassified_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_multi_child_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_unclassified_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_multi_child_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_unclassified_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_multi_child_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_overlap_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_candidate_slot_write_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_covered_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_unclassified_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_multi_child_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_coverage_source"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_covered_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_unclassified_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_multi_child_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_sampled_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_coverage_source"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_aux_updates_total"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_event_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_count"
        << "\tcontext_apply_timer_call_count"
        << "\tcontext_apply_terminal_timer_call_count"
        << "\tcontext_apply_lexical_timer_call_count"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_candidate_bytes_written"
        << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_bytes_written"
        << "\tbenchmark_source_original_path"
        << "\tbenchmark_source_copied_path"
        << "\tbenchmark_source_sha256"
        << "\tbenchmark_source_size_bytes"
        << "\tbenchmark_identity_basis"
        << "\tverify_ok\n";

    std::stringstream aggregateTsv;
    if (!aggregateTsvPath.empty())
    {
        aggregateTsv << "case_id\tcandidate_index_backend\tprofile_mode\tprofile_sample_log2\tprofile_sample_rate"
                     << "\tterminal_telemetry_overhead_mode_requested\tterminal_telemetry_overhead_mode_effective"
                     << "\tstate_update_bookkeeping_mode_requested\tstate_update_bookkeeping_mode_effective"
                     << "\twarmup_iterations\titerations\tlogical_event_count"
                     << "\tcontext_candidate_count_after_context_apply"
                     << "\tcontext_apply_attempted_count\tcontext_apply_modified_count"
                     << "\tcontext_apply_noop_count\tcontext_apply_lookup_hit_count"
                     << "\tcontext_apply_full_set_miss_count"
                     << "\tcontext_apply_floor_changed_count"
                     << "\tcontext_apply_floor_changed_share"
                     << "\tcontext_apply_running_min_slot_changed_count"
                     << "\tcontext_apply_running_min_slot_changed_share"
                     << "\tcontext_apply_victim_was_running_min_count"
                     << "\tcontext_apply_victim_was_running_min_share"
                     << "\tcontext_apply_refresh_min_calls"
                     << "\tcontext_apply_refresh_min_slots_scanned"
                     << "\tcontext_apply_refresh_min_slots_scanned_per_call"
                     << "\tcontext_apply_candidate_index_lookup_count"
                     << "\tcontext_apply_candidate_index_hit_count"
                     << "\tcontext_apply_candidate_index_miss_count"
                     << "\tcontext_apply_candidate_index_erase_count"
                     << "\tcontext_apply_candidate_index_insert_count"
                     << "\tcontext_apply_lookup_miss_count\tcontext_apply_lookup_probe_steps_total"
                     << "\tcontext_apply_lookup_probe_steps_max"
                     << "\tcontext_apply_lookup_miss_open_slot_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_covered_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_unclassified_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_multi_child_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_slots_scanned_total"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_slots_scanned_per_probe_mean"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_slots_scanned_p50"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_slots_scanned_p90"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_slots_scanned_p99"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_full_scan_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_early_exit_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_found_existing_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_confirmed_absent_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_redundant_reprobe_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_same_key_reprobe_count"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_same_event_reprobe_count"
                     << "\tcontext_apply_eviction_selected_count\tcontext_apply_reused_slot_count"
                     << "\tcontext_apply_mean_seconds\tcontext_apply_p50_seconds\tcontext_apply_p95_seconds"
                     << "\tcontext_apply_full_set_miss_mean_seconds\tcontext_apply_full_set_miss_p50_seconds\tcontext_apply_full_set_miss_p95_seconds"
                     << "\tcontext_apply_refresh_min_mean_seconds\tcontext_apply_refresh_min_p50_seconds\tcontext_apply_refresh_min_p95_seconds"
                     << "\tcontext_apply_candidate_index_mean_seconds\tcontext_apply_candidate_index_p50_seconds\tcontext_apply_candidate_index_p95_seconds"
                     << "\tcontext_apply_candidate_index_erase_mean_seconds\tcontext_apply_candidate_index_erase_p50_seconds\tcontext_apply_candidate_index_erase_p95_seconds"
                     << "\tcontext_apply_candidate_index_insert_mean_seconds\tcontext_apply_candidate_index_insert_p50_seconds\tcontext_apply_candidate_index_insert_p95_seconds"
                     << "\tcontext_apply_lookup_mean_seconds\tcontext_apply_lookup_p50_seconds\tcontext_apply_lookup_p95_seconds"
                     << "\tcontext_apply_lookup_miss_mean_seconds\tcontext_apply_lookup_miss_p50_seconds\tcontext_apply_lookup_miss_p95_seconds"
                     << "\tcontext_apply_lookup_miss_open_slot_mean_seconds\tcontext_apply_lookup_miss_open_slot_p50_seconds\tcontext_apply_lookup_miss_open_slot_p95_seconds"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_mean_seconds\tcontext_apply_lookup_miss_candidate_set_full_probe_p50_seconds\tcontext_apply_lookup_miss_candidate_set_full_probe_p95_seconds"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_parent_mean_seconds"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_scan_mean_seconds"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_compare_mean_seconds"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_branch_or_guard_mean_seconds"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_bookkeeping_mean_seconds"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_child_known_mean_seconds"
                     << "\tcontext_apply_lookup_miss_candidate_set_full_probe_unexplained_mean_seconds"
                     << "\tcontext_apply_lookup_miss_eviction_select_mean_seconds\tcontext_apply_lookup_miss_eviction_select_p50_seconds\tcontext_apply_lookup_miss_eviction_select_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_victim_reset_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_victim_reset_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_victim_reset_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_key_rebind_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_key_rebind_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_key_rebind_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_candidate_copy_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_candidate_copy_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_candidate_copy_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_bookkeeping_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_bookkeeping_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_build_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_build_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_build_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_update_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_update_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_heap_update_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_aux_start_index_rebuild_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_start_index_rebuild_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_start_index_rebuild_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_heap_update_accounting_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_start_index_rebuild_accounting_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_trace_finalize_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_build_accounting_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_heap_update_trace_record_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_start_index_rebuild_trace_record_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_residual_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_residual_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_aux_other_residual_residual_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_child_known_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_child_known_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_child_known_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_candidate_slot_write_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_candidate_slot_write_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_candidate_slot_write_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_left_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_left_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_left_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_right_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_right_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_right_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_child_known_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_child_known_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_child_known_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_unexplained_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_unexplained_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_unexplained_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_child_known_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_child_known_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_child_known_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unexplained_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unexplained_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unexplained_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_child_known_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_child_known_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_child_known_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_unexplained_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_unexplained_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_unexplained_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_child_known_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_child_known_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_child_known_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_unexplained_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_unexplained_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_unexplained_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_telemetry_overhead_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_telemetry_overhead_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_telemetry_overhead_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_residual_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_residual_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_residual_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_lexical_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_lexical_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_lexical_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_span_first_half_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_span_first_half_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_span_first_half_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_span_second_half_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_span_second_half_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_span_second_half_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a1_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a1_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a1_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_0_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_0_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_0_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_1_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_1_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_1_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_parent_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_1_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_1_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_1_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_child_known_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_child_known_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_child_known_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_unexplained_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_unexplained_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_unexplained_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_known_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_known_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_known_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_unexplained_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child_known_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child_known_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child_known_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_unexplained_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_known_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_known_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_known_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unexplained_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unexplained_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unexplained_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_known_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_known_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child_known_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unexplained_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unexplained_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unexplained_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a00_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a00_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a00_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_between_a00_a01_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_between_a00_a01_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_between_a00_a01_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a01_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a01_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a01_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_after_a01_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_after_a01_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_after_a01_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_child_known_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_child_known_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_child_known_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_unexplained_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_unexplained_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_unexplained_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_child_known_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_child_known_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_child_known_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_unexplained_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_unexplained_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_unexplained_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_b_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_b_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_b_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_child_known_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_child_known_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_child_known_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_unexplained_mean_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_unexplained_p50_seconds\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_unexplained_p95_seconds"
                     << "\tcontext_apply_mutate_mean_seconds\tcontext_apply_mutate_p50_seconds\tcontext_apply_mutate_p95_seconds"
                     << "\tcontext_apply_finalize_mean_seconds\tcontext_apply_finalize_p50_seconds\tcontext_apply_finalize_p95_seconds"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a1_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a00_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a01_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_b_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_covered_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_covered_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_covered_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_0_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_child_1_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_covered_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_left_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_covered_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_0_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child_1_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_covered_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_left_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_right_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_1_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a00_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_between_a00_a01_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a01_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_after_a01_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_unclassified_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_multi_child_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_unclassified_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_multi_child_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_unclassified_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_multi_child_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_unclassified_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_multi_child_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_unclassified_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_multi_child_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_unclassified_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_multi_child_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_first_half_span_a0_overlap_sampled_event_count"
                     << "\tdominant_terminal_first_half_span_a_child"
                     << "\tdominant_terminal_first_half_span_a0_child"
                     << "\tdominant_terminal_first_half_span_a0_gap_before_a00_child"
                     << "\tdominant_terminal_first_half_span_a0_gap_before_a00_span_0_child"
                     << "\tdominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_child"
                     << "\tdominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_child"
                     << "\tdominant_terminal_first_half_span_a0_gap_before_a00_span_0_alt_right_repart_child"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_candidate_slot_write_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_covered_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_unclassified_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_multi_child_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_left_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_right_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_insert_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_update_existing_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_clear_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_overwrite_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_idempotent_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_value_changed_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_probe_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_write_probe_steps_total"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_covered_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unclassified_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_multi_child_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_bytes"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_bytes"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_bytes"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_entry_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_slot_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_unique_key_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_same_entry_rewrite_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_same_cacheline_rewrite_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_back_to_back_same_entry_write_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_clear_then_overwrite_same_entry_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_overwrite_then_insert_same_entry_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_store_insert_then_clear_same_entry_count"
                     << "\tdominant_terminal_start_index_write_child"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_covered_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_unclassified_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_multi_child_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_coverage_source"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_covered_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_unclassified_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_multi_child_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_sampled_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_coverage_source"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_build_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_heap_update_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_start_index_rebuild_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_trace_or_profile_bookkeeping_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_state_update_aux_updates_total"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_event_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_benchmark_counter_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_production_state_update_trace_replay_required_state_count"
                     << "\tcontext_apply_timer_call_count"
                     << "\tcontext_apply_terminal_timer_call_count"
                     << "\tcontext_apply_lexical_timer_call_count"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_candidate_bytes_written"
                     << "\tcontext_apply_lookup_miss_reuse_writeback_terminal_start_index_bytes_written"
                     << "\tsim_initial_scan_seconds_mean_seconds"
                     << "\tsim_initial_scan_cpu_merge_seconds_mean_seconds"
                     << "\tsim_initial_scan_cpu_merge_subtotal_seconds_mean_seconds"
                     << "\tsim_seconds_mean_seconds"
                     << "\ttotal_seconds_mean_seconds"
                     << "\tworkload_id"
                     << "\tbenchmark_source"
                     << "\tbenchmark_source_original_path"
                     << "\tbenchmark_source_copied_path"
                     << "\tbenchmark_source_sha256"
                     << "\tbenchmark_source_size_bytes"
                     << "\tbenchmark_identity_basis"
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
            if (!replaySimInitialHostMergeContextApplyPhase(corpus, false, candidateIndexBackend, replay, &error))
            {
                std::cerr << error << "\n";
                return 1;
            }
        }

        std::vector<double> contextApplySamples;
        std::vector<double> fullSetMissSamples;
        std::vector<double> refreshMinSamples;
        std::vector<double> candidateIndexSamples;
        std::vector<double> candidateIndexEraseSamples;
        std::vector<double> candidateIndexInsertSamples;
        std::vector<double> lookupSamples;
        std::vector<double> lookupMissSamples;
        std::vector<double> lookupMissOpenSlotSamples;
        std::vector<double> lookupMissCandidateSetFullProbeSamples;
        std::vector<double> lookupMissCandidateSetFullProbeScanSamples;
        std::vector<double> lookupMissCandidateSetFullProbeCompareSamples;
        std::vector<double> lookupMissCandidateSetFullProbeBranchOrGuardSamples;
        std::vector<double> lookupMissCandidateSetFullProbeBookkeepingSamples;
        std::vector<double> lookupMissCandidateSetFullProbeChildKnownSamples;
        std::vector<double> lookupMissCandidateSetFullProbeUnexplainedSamples;
        std::vector<double> lookupMissEvictionSelectSamples;
        std::vector<double> lookupMissReuseWritebackSamples;
        std::vector<double> lookupMissReuseWritebackVictimResetSamples;
        std::vector<double> lookupMissReuseWritebackKeyRebindSamples;
        std::vector<double> lookupMissReuseWritebackCandidateCopySamples;
        std::vector<double> lookupMissReuseWritebackAuxBookkeepingSamples;
        std::vector<double> lookupMissReuseWritebackAuxHeapBuildSamples;
        std::vector<double> lookupMissReuseWritebackAuxHeapUpdateSamples;
        std::vector<double> lookupMissReuseWritebackAuxStartIndexRebuildSamples;
        std::vector<double> lookupMissReuseWritebackAuxOtherSamples;
        std::vector<double> lookupMissReuseWritebackAuxOtherHeapUpdateAccountingSamples;
        std::vector<double> lookupMissReuseWritebackAuxOtherStartIndexRebuildAccountingSamples;
        std::vector<double> lookupMissReuseWritebackAuxOtherTraceFinalizeSamples;
        std::vector<double> lookupMissReuseWritebackAuxOtherResidualSamples;
        std::vector<double> lookupMissReuseWritebackAuxOtherResidualHeapBuildAccountingSamples;
        std::vector<double> lookupMissReuseWritebackAuxOtherResidualHeapUpdateTraceRecordSamples;
        std::vector<double> lookupMissReuseWritebackAuxOtherResidualStartIndexRebuildTraceRecordSamples;
        std::vector<double> lookupMissReuseWritebackAuxOtherResidualResidualSamples;
        std::vector<double> terminalPathParentSamples;
        std::vector<double> terminalPathChildKnownSamples;
        std::vector<double> terminalPathCandidateSlotWriteSamples;
        std::vector<double> terminalPathStartIndexWriteSamples;
        std::vector<double> terminalPathStartIndexWriteParentSamples;
        std::vector<double> terminalPathStartIndexWriteLeftSamples;
        std::vector<double> terminalPathStartIndexWriteRightSamples;
        std::vector<double> terminalPathStartIndexWriteChildKnownSamples;
        std::vector<double> terminalPathStartIndexWriteUnexplainedSamples;
        std::vector<double> terminalPathStartIndexStoreParentSamples;
        std::vector<double> terminalPathStartIndexStoreInsertSamples;
        std::vector<double> terminalPathStartIndexStoreClearSamples;
        std::vector<double> terminalPathStartIndexStoreOverwriteSamples;
        std::vector<double> terminalPathStartIndexStoreChildKnownSamples;
        std::vector<double> terminalPathStartIndexStoreUnexplainedSamples;
        std::vector<double> terminalPathStateUpdateSamples;
        std::vector<double> terminalPathStateUpdateParentSamples;
        std::vector<double> terminalPathStateUpdateHeapBuildSamples;
        std::vector<double> terminalPathStateUpdateHeapUpdateSamples;
        std::vector<double> terminalPathStateUpdateStartIndexRebuildSamples;
        std::vector<double> terminalPathStateUpdateTraceOrProfileBookkeepingSamples;
        std::vector<double> terminalPathStateUpdateChildKnownSamples;
        std::vector<double> terminalPathStateUpdateUnexplainedSamples;
        std::vector<double> productionStateUpdateParentSamples;
        std::vector<double> productionStateUpdateBenchmarkCounterSamples;
        std::vector<double> productionStateUpdateTraceReplayRequiredStateSamples;
        std::vector<double> productionStateUpdateChildKnownSamples;
        std::vector<double> productionStateUpdateUnexplainedSamples;
        std::vector<double> terminalPathTelemetryOverheadSamples;
        std::vector<double> terminalPathResidualSamples;
        std::vector<double> terminalLexicalParentSamples;
        std::vector<double> terminalSpanFirstHalfSamples;
        std::vector<double> terminalSpanSecondHalfSamples;
        std::vector<double> terminalFirstHalfParentSamples;
        std::vector<double> terminalFirstHalfSpanASamples;
        std::vector<double> terminalFirstHalfSpanAParentSamples;
        std::vector<double> terminalFirstHalfSpanA0Samples;
        std::vector<double> terminalFirstHalfSpanA1Samples;
        std::vector<double> terminalFirstHalfSpanA0ParentSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Samples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00ParentSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0Samples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0ParentSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0Child0Samples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0Child1Samples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0AltParentSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0AltLeftSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0AltRightSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0AltRightUnexplainedSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartUnexplainedSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span1Samples;
        std::vector<double> terminalFirstHalfSpanA00Samples;
        std::vector<double> terminalFirstHalfSpanA0GapBetweenA00A01Samples;
        std::vector<double> terminalFirstHalfSpanA01Samples;
        std::vector<double> terminalFirstHalfSpanA0GapAfterA01Samples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00ChildKnownSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00UnexplainedSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0ChildKnownSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0UnexplainedSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0AltChildKnownSamples;
        std::vector<double> terminalFirstHalfSpanA0GapBeforeA00Span0AltUnexplainedSamples;
        std::vector<double> terminalFirstHalfSpanA0ChildKnownSamples;
        std::vector<double> terminalFirstHalfSpanA0UnexplainedSamples;
        std::vector<double> terminalFirstHalfSpanAChildKnownSamples;
        std::vector<double> terminalFirstHalfSpanAUnexplainedSamples;
        std::vector<double> terminalFirstHalfSpanBSamples;
        std::vector<double> terminalFirstHalfChildKnownSamples;
        std::vector<double> terminalFirstHalfUnexplainedSamples;
        std::vector<double> mutateSamples;
        std::vector<double> finalizeSamples;
        contextApplySamples.reserve(iterations);
        fullSetMissSamples.reserve(iterations);
        refreshMinSamples.reserve(iterations);
        candidateIndexSamples.reserve(iterations);
        candidateIndexEraseSamples.reserve(iterations);
        candidateIndexInsertSamples.reserve(iterations);
        lookupSamples.reserve(iterations);
        lookupMissSamples.reserve(iterations);
        lookupMissOpenSlotSamples.reserve(iterations);
        lookupMissCandidateSetFullProbeSamples.reserve(iterations);
        lookupMissCandidateSetFullProbeScanSamples.reserve(iterations);
        lookupMissCandidateSetFullProbeCompareSamples.reserve(iterations);
        lookupMissCandidateSetFullProbeBranchOrGuardSamples.reserve(iterations);
        lookupMissCandidateSetFullProbeBookkeepingSamples.reserve(iterations);
        lookupMissCandidateSetFullProbeChildKnownSamples.reserve(iterations);
        lookupMissCandidateSetFullProbeUnexplainedSamples.reserve(iterations);
        lookupMissEvictionSelectSamples.reserve(iterations);
        lookupMissReuseWritebackSamples.reserve(iterations);
        lookupMissReuseWritebackVictimResetSamples.reserve(iterations);
        lookupMissReuseWritebackKeyRebindSamples.reserve(iterations);
        lookupMissReuseWritebackCandidateCopySamples.reserve(iterations);
        lookupMissReuseWritebackAuxBookkeepingSamples.reserve(iterations);
        lookupMissReuseWritebackAuxHeapBuildSamples.reserve(iterations);
        lookupMissReuseWritebackAuxHeapUpdateSamples.reserve(iterations);
        lookupMissReuseWritebackAuxStartIndexRebuildSamples.reserve(iterations);
        lookupMissReuseWritebackAuxOtherSamples.reserve(iterations);
        lookupMissReuseWritebackAuxOtherHeapUpdateAccountingSamples.reserve(iterations);
        lookupMissReuseWritebackAuxOtherStartIndexRebuildAccountingSamples.reserve(iterations);
        lookupMissReuseWritebackAuxOtherTraceFinalizeSamples.reserve(iterations);
        lookupMissReuseWritebackAuxOtherResidualSamples.reserve(iterations);
        lookupMissReuseWritebackAuxOtherResidualHeapBuildAccountingSamples.reserve(iterations);
        lookupMissReuseWritebackAuxOtherResidualHeapUpdateTraceRecordSamples.reserve(iterations);
        lookupMissReuseWritebackAuxOtherResidualStartIndexRebuildTraceRecordSamples.reserve(iterations);
        lookupMissReuseWritebackAuxOtherResidualResidualSamples.reserve(iterations);
        terminalPathParentSamples.reserve(iterations);
        terminalPathChildKnownSamples.reserve(iterations);
        terminalPathCandidateSlotWriteSamples.reserve(iterations);
        terminalPathStartIndexWriteSamples.reserve(iterations);
        terminalPathStartIndexWriteParentSamples.reserve(iterations);
        terminalPathStartIndexWriteLeftSamples.reserve(iterations);
        terminalPathStartIndexWriteRightSamples.reserve(iterations);
        terminalPathStartIndexWriteChildKnownSamples.reserve(iterations);
        terminalPathStartIndexWriteUnexplainedSamples.reserve(iterations);
        terminalPathStartIndexStoreParentSamples.reserve(iterations);
        terminalPathStartIndexStoreInsertSamples.reserve(iterations);
        terminalPathStartIndexStoreClearSamples.reserve(iterations);
        terminalPathStartIndexStoreOverwriteSamples.reserve(iterations);
        terminalPathStartIndexStoreChildKnownSamples.reserve(iterations);
        terminalPathStartIndexStoreUnexplainedSamples.reserve(iterations);
        terminalPathStateUpdateSamples.reserve(iterations);
        terminalPathStateUpdateParentSamples.reserve(iterations);
        terminalPathStateUpdateHeapBuildSamples.reserve(iterations);
        terminalPathStateUpdateHeapUpdateSamples.reserve(iterations);
        terminalPathStateUpdateStartIndexRebuildSamples.reserve(iterations);
        terminalPathStateUpdateTraceOrProfileBookkeepingSamples.reserve(iterations);
        terminalPathStateUpdateChildKnownSamples.reserve(iterations);
        terminalPathStateUpdateUnexplainedSamples.reserve(iterations);
        productionStateUpdateParentSamples.reserve(iterations);
        productionStateUpdateBenchmarkCounterSamples.reserve(iterations);
        productionStateUpdateTraceReplayRequiredStateSamples.reserve(iterations);
        productionStateUpdateChildKnownSamples.reserve(iterations);
        productionStateUpdateUnexplainedSamples.reserve(iterations);
        terminalPathTelemetryOverheadSamples.reserve(iterations);
        terminalPathResidualSamples.reserve(iterations);
        terminalLexicalParentSamples.reserve(iterations);
        terminalSpanFirstHalfSamples.reserve(iterations);
        terminalSpanSecondHalfSamples.reserve(iterations);
        terminalFirstHalfParentSamples.reserve(iterations);
        terminalFirstHalfSpanASamples.reserve(iterations);
        terminalFirstHalfSpanA0Samples.reserve(iterations);
        terminalFirstHalfSpanA1Samples.reserve(iterations);
        terminalFirstHalfSpanA0ParentSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Samples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00ParentSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0Samples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0ParentSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0Child0Samples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0Child1Samples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0AltParentSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0AltLeftSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0AltRightSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0AltRightUnexplainedSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartUnexplainedSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span1Samples.reserve(iterations);
        terminalFirstHalfSpanA00Samples.reserve(iterations);
        terminalFirstHalfSpanA0GapBetweenA00A01Samples.reserve(iterations);
        terminalFirstHalfSpanA01Samples.reserve(iterations);
        terminalFirstHalfSpanA0GapAfterA01Samples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00ChildKnownSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00UnexplainedSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0ChildKnownSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0UnexplainedSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0AltChildKnownSamples.reserve(iterations);
        terminalFirstHalfSpanA0GapBeforeA00Span0AltUnexplainedSamples.reserve(iterations);
        terminalFirstHalfSpanA0ChildKnownSamples.reserve(iterations);
        terminalFirstHalfSpanA0UnexplainedSamples.reserve(iterations);
        terminalFirstHalfSpanAChildKnownSamples.reserve(iterations);
        terminalFirstHalfSpanAUnexplainedSamples.reserve(iterations);
        terminalFirstHalfSpanBSamples.reserve(iterations);
        terminalFirstHalfChildKnownSamples.reserve(iterations);
        terminalFirstHalfUnexplainedSamples.reserve(iterations);
        mutateSamples.reserve(iterations);
        finalizeSamples.reserve(iterations);

        set_gprof_sampling_enabled(true);
        for (size_t iteration = 0; iteration < iterations; ++iteration)
        {
            error.clear();
            if (!replaySimInitialHostMergeContextApplyPhase(corpus, false, candidateIndexBackend, replay, &error))
            {
                set_gprof_sampling_enabled(false);
                std::cerr << error << "\n";
                return 1;
            }
            contextApplySamples.push_back(replay.contextApplySeconds);
            fullSetMissSamples.push_back(replay.storeOtherMergeContextApplyFullSetMissSeconds);
            refreshMinSamples.push_back(replay.storeOtherMergeContextApplyRefreshMinSeconds);
            candidateIndexSamples.push_back(replay.storeOtherMergeContextApplyCandidateIndexSeconds);
            candidateIndexEraseSamples.push_back(
                replay.storeOtherMergeContextApplyCandidateIndexEraseSeconds);
            candidateIndexInsertSamples.push_back(
                replay.storeOtherMergeContextApplyCandidateIndexInsertSeconds);
            lookupSamples.push_back(replay.storeOtherMergeContextApplyLookupSeconds);
            lookupMissSamples.push_back(replay.storeOtherMergeContextApplyLookupMissSeconds);
            lookupMissOpenSlotSamples.push_back(replay.storeOtherMergeContextApplyLookupMissOpenSlotSeconds);
            lookupMissCandidateSetFullProbeSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeSeconds);
            lookupMissCandidateSetFullProbeScanSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeScanSeconds);
            lookupMissCandidateSetFullProbeCompareSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeCompareSeconds);
            lookupMissCandidateSetFullProbeBranchOrGuardSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeBranchOrGuardSeconds);
            lookupMissCandidateSetFullProbeBookkeepingSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeBookkeepingSeconds);
            lookupMissCandidateSetFullProbeChildKnownSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeChildKnownSeconds);
            lookupMissCandidateSetFullProbeUnexplainedSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeUnexplainedSeconds);
            lookupMissEvictionSelectSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissEvictionSelectSeconds);
            lookupMissReuseWritebackSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackSeconds);
            lookupMissReuseWritebackVictimResetSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackVictimResetSeconds);
            lookupMissReuseWritebackKeyRebindSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackKeyRebindSeconds);
            lookupMissReuseWritebackCandidateCopySamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackCandidateCopySeconds);
            lookupMissReuseWritebackAuxBookkeepingSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxBookkeepingSeconds);
            lookupMissReuseWritebackAuxHeapBuildSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxHeapBuildSeconds);
            lookupMissReuseWritebackAuxHeapUpdateSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxHeapUpdateSeconds);
            lookupMissReuseWritebackAuxStartIndexRebuildSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxStartIndexRebuildSeconds);
            lookupMissReuseWritebackAuxOtherSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherSeconds);
            lookupMissReuseWritebackAuxOtherHeapUpdateAccountingSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherHeapUpdateAccountingSeconds);
            lookupMissReuseWritebackAuxOtherStartIndexRebuildAccountingSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherStartIndexRebuildAccountingSeconds);
            lookupMissReuseWritebackAuxOtherTraceFinalizeSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherTraceFinalizeSeconds);
            lookupMissReuseWritebackAuxOtherResidualSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualSeconds);
            lookupMissReuseWritebackAuxOtherResidualHeapBuildAccountingSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualHeapBuildAccountingSeconds);
            lookupMissReuseWritebackAuxOtherResidualHeapUpdateTraceRecordSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualHeapUpdateTraceRecordSeconds);
            lookupMissReuseWritebackAuxOtherResidualStartIndexRebuildTraceRecordSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualStartIndexRebuildTraceRecordSeconds);
            lookupMissReuseWritebackAuxOtherResidualResidualSamples.push_back(
                replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualResidualSeconds);
            const TerminalPathDerivedMetrics terminalMetrics =
                derive_terminal_path_metrics(replay);
            terminalPathParentSamples.push_back(terminalMetrics.parentSeconds);
            terminalPathChildKnownSamples.push_back(terminalMetrics.childKnownSeconds);
            terminalPathCandidateSlotWriteSamples.push_back(
                terminalMetrics.candidateSlotWriteSeconds);
            terminalPathStartIndexWriteSamples.push_back(
                terminalMetrics.startIndexWriteSeconds);
            terminalPathStartIndexWriteParentSamples.push_back(
                terminalMetrics.startIndexWriteParentSeconds);
            terminalPathStartIndexWriteLeftSamples.push_back(
                terminalMetrics.startIndexWriteLeftSeconds);
            terminalPathStartIndexWriteRightSamples.push_back(
                terminalMetrics.startIndexWriteRightSeconds);
            terminalPathStartIndexWriteChildKnownSamples.push_back(
                terminalMetrics.startIndexWriteChildKnownSeconds);
            terminalPathStartIndexWriteUnexplainedSamples.push_back(
                terminalMetrics.startIndexWriteUnexplainedSeconds);
            terminalPathStartIndexStoreParentSamples.push_back(
                terminalMetrics.startIndexStoreParentSeconds);
            terminalPathStartIndexStoreInsertSamples.push_back(
                terminalMetrics.startIndexStoreInsertSeconds);
            terminalPathStartIndexStoreClearSamples.push_back(
                terminalMetrics.startIndexStoreClearSeconds);
            terminalPathStartIndexStoreOverwriteSamples.push_back(
                terminalMetrics.startIndexStoreOverwriteSeconds);
            terminalPathStartIndexStoreChildKnownSamples.push_back(
                terminalMetrics.startIndexStoreChildKnownSeconds);
            terminalPathStartIndexStoreUnexplainedSamples.push_back(
                terminalMetrics.startIndexStoreUnexplainedSeconds);
            terminalPathStateUpdateSamples.push_back(terminalMetrics.stateUpdateSeconds);
            terminalPathStateUpdateParentSamples.push_back(
                terminalMetrics.stateUpdateParentSeconds);
            terminalPathStateUpdateHeapBuildSamples.push_back(
                terminalMetrics.stateUpdateHeapBuildSeconds);
            terminalPathStateUpdateHeapUpdateSamples.push_back(
                terminalMetrics.stateUpdateHeapUpdateSeconds);
            terminalPathStateUpdateStartIndexRebuildSamples.push_back(
                terminalMetrics.stateUpdateStartIndexRebuildSeconds);
            terminalPathStateUpdateTraceOrProfileBookkeepingSamples.push_back(
                terminalMetrics.stateUpdateTraceOrProfileBookkeepingSeconds);
            terminalPathStateUpdateChildKnownSamples.push_back(
                terminalMetrics.stateUpdateChildKnownSeconds);
            terminalPathStateUpdateUnexplainedSamples.push_back(
                terminalMetrics.stateUpdateUnexplainedSeconds);
            productionStateUpdateParentSamples.push_back(
                terminalMetrics.productionStateUpdateParentSeconds);
            productionStateUpdateBenchmarkCounterSamples.push_back(
                terminalMetrics.productionStateUpdateBenchmarkCounterSeconds);
            productionStateUpdateTraceReplayRequiredStateSamples.push_back(
                terminalMetrics.productionStateUpdateTraceReplayRequiredStateSeconds);
            productionStateUpdateChildKnownSamples.push_back(
                terminalMetrics.productionStateUpdateChildKnownSeconds);
            productionStateUpdateUnexplainedSamples.push_back(
                terminalMetrics.productionStateUpdateUnexplainedSeconds);
            terminalPathTelemetryOverheadSamples.push_back(
                terminalMetrics.telemetryOverheadSeconds);
            terminalPathResidualSamples.push_back(terminalMetrics.residualSeconds);
            terminalLexicalParentSamples.push_back(terminalMetrics.lexicalParentSeconds);
            terminalSpanFirstHalfSamples.push_back(terminalMetrics.spanFirstHalfSeconds);
            terminalSpanSecondHalfSamples.push_back(terminalMetrics.spanSecondHalfSeconds);
            terminalFirstHalfParentSamples.push_back(terminalMetrics.firstHalfParentSeconds);
            terminalFirstHalfSpanASamples.push_back(terminalMetrics.firstHalfSpanASeconds);
            terminalFirstHalfSpanAParentSamples.push_back(
                terminalMetrics.firstHalfSpanAParentSeconds);
            terminalFirstHalfSpanA0Samples.push_back(terminalMetrics.firstHalfSpanA0Seconds);
            terminalFirstHalfSpanA1Samples.push_back(terminalMetrics.firstHalfSpanA1Seconds);
            terminalFirstHalfSpanA0ParentSamples.push_back(
                terminalMetrics.firstHalfSpanA0ParentSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Samples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Seconds);
            terminalFirstHalfSpanA0GapBeforeA00ParentSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00ParentSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0Samples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0Seconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0ParentSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0ParentSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0Child0Samples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0Child0Seconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0Child1Samples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0Child1Seconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0AltParentSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltParentSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0AltLeftSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltLeftSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0AltRightSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0AltRightUnexplainedSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightUnexplainedSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartUnexplainedSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartUnexplainedSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span1Samples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span1Seconds);
            terminalFirstHalfSpanA00Samples.push_back(terminalMetrics.firstHalfSpanA00Seconds);
            terminalFirstHalfSpanA0GapBetweenA00A01Samples.push_back(
                terminalMetrics.firstHalfSpanA0GapBetweenA00A01Seconds);
            terminalFirstHalfSpanA01Samples.push_back(terminalMetrics.firstHalfSpanA01Seconds);
            terminalFirstHalfSpanA0GapAfterA01Samples.push_back(
                terminalMetrics.firstHalfSpanA0GapAfterA01Seconds);
            terminalFirstHalfSpanA0GapBeforeA00ChildKnownSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00ChildKnownSeconds);
            terminalFirstHalfSpanA0GapBeforeA00UnexplainedSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00UnexplainedSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0ChildKnownSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0ChildKnownSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0UnexplainedSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0UnexplainedSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0AltChildKnownSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltChildKnownSeconds);
            terminalFirstHalfSpanA0GapBeforeA00Span0AltUnexplainedSamples.push_back(
                terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltUnexplainedSeconds);
            terminalFirstHalfSpanA0ChildKnownSamples.push_back(
                terminalMetrics.firstHalfSpanA0ChildKnownSeconds);
            terminalFirstHalfSpanA0UnexplainedSamples.push_back(
                terminalMetrics.firstHalfSpanA0UnexplainedSeconds);
            terminalFirstHalfSpanAChildKnownSamples.push_back(
                terminalMetrics.firstHalfSpanAChildKnownSeconds);
            terminalFirstHalfSpanAUnexplainedSamples.push_back(
                terminalMetrics.firstHalfSpanAUnexplainedSeconds);
            terminalFirstHalfSpanBSamples.push_back(terminalMetrics.firstHalfSpanBSeconds);
            terminalFirstHalfChildKnownSamples.push_back(terminalMetrics.firstHalfChildKnownSeconds);
            terminalFirstHalfUnexplainedSamples.push_back(terminalMetrics.firstHalfUnexplainedSeconds);
            mutateSamples.push_back(replay.storeOtherMergeContextApplyMutateSeconds);
            finalizeSamples.push_back(replay.storeOtherMergeContextApplyFinalizeSeconds);
        }
        set_gprof_sampling_enabled(false);

        bool verifyOk = !verify;
        if (verify)
        {
            SimInitialHostMergeReplayResult verifyReplay;
            error.clear();
            if (!replaySimInitialHostMergeContextApplyCorpusCase(corpus, candidateIndexBackend, verifyReplay, &error))
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

        const TerminalPathDerivedMetrics terminalMetrics = derive_terminal_path_metrics(replay);

        tsv << selectedCase
            << "\t" << candidate_index_backend_name(candidateIndexBackend)
            << "\t" << profile_mode_name(profileMode)
            << "\t" << profileSampleLog2
            << "\t" << simInitialProfilerSampleRate()
            << "\t"
            << terminal_telemetry_overhead_mode_name(
                   simInitialTerminalTelemetryOverheadRequestedMode())
            << "\t"
            << terminal_telemetry_overhead_mode_name(
                   simInitialTerminalTelemetryOverheadEffectiveMode())
            << "\t"
            << state_update_bookkeeping_mode_name(
                   simInitialStateUpdateBookkeepingRequestedMode())
            << "\t"
            << state_update_bookkeeping_mode_name(
                   simInitialStateUpdateBookkeepingEffectiveMode())
            << "\t" << corpus.logicalEventCount
            << "\t" << corpus.expectedContextCandidates.size()
            << "\t" << corpus.runningMinAfterContextApply
            << "\t" << replay.contextApplySeconds
            << "\t" << replay.storeOtherMergeContextApplyFullSetMissSeconds
            << "\t" << replay.storeOtherMergeContextApplyRefreshMinSeconds
            << "\t" << replay.storeOtherMergeContextApplyCandidateIndexSeconds
            << "\t" << replay.storeOtherMergeContextApplyCandidateIndexEraseSeconds
            << "\t" << replay.storeOtherMergeContextApplyCandidateIndexInsertSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupHitSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissOpenSlotSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissEvictionSelectSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackVictimResetSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackKeyRebindSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackCandidateCopySeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxBookkeepingSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxHeapBuildSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxHeapUpdateSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxStartIndexRebuildSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherHeapUpdateAccountingSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherStartIndexRebuildAccountingSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherTraceFinalizeSeconds
            << "\t" << replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxOtherResidualSeconds
            << "\t" << terminalMetrics.parentSeconds
            << "\t" << terminalMetrics.childKnownSeconds
            << "\t" << terminalMetrics.candidateSlotWriteSeconds
            << "\t" << terminalMetrics.startIndexWriteSeconds
            << "\t" << terminalMetrics.stateUpdateSeconds
            << "\t" << terminalMetrics.stateUpdateParentSeconds
            << "\t" << terminalMetrics.stateUpdateHeapBuildSeconds
            << "\t" << terminalMetrics.stateUpdateHeapUpdateSeconds
            << "\t" << terminalMetrics.stateUpdateStartIndexRebuildSeconds
            << "\t" << terminalMetrics.stateUpdateTraceOrProfileBookkeepingSeconds
            << "\t" << terminalMetrics.stateUpdateChildKnownSeconds
            << "\t" << terminalMetrics.stateUpdateUnexplainedSeconds
            << "\t" << terminalMetrics.productionStateUpdateParentSeconds
            << "\t" << terminalMetrics.productionStateUpdateParentSeconds
            << "\t" << terminalMetrics.productionStateUpdateBenchmarkCounterSeconds
            << "\t" << terminalMetrics.productionStateUpdateTraceReplayRequiredStateSeconds
            << "\t" << terminalMetrics.productionStateUpdateChildKnownSeconds
            << "\t" << terminalMetrics.productionStateUpdateUnexplainedSeconds
            << "\t" << terminalMetrics.telemetryOverheadSeconds
            << "\t" << terminalMetrics.residualSeconds
            << "\t" << terminalMetrics.lexicalParentSeconds
            << "\t" << terminalMetrics.spanFirstHalfSeconds
            << "\t" << terminalMetrics.spanSecondHalfSeconds
            << "\t" << terminalMetrics.firstHalfParentSeconds
            << "\t" << terminalMetrics.firstHalfSpanASeconds
            << "\t" << terminalMetrics.firstHalfSpanAParentSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0Seconds
            << "\t" << terminalMetrics.firstHalfSpanA1Seconds
            << "\t" << terminalMetrics.firstHalfSpanA0ParentSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Seconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00ParentSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0Seconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0ParentSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0Child0Seconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0Child1Seconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltParentSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltLeftSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightParentSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild0Seconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild1Seconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span1Seconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00ChildKnownSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00UnexplainedSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0ChildKnownSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0UnexplainedSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltChildKnownSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltUnexplainedSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightUnexplainedSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartUnexplainedSeconds
            << "\t" << terminalMetrics.firstHalfSpanA00Seconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapBetweenA00A01Seconds
            << "\t" << terminalMetrics.firstHalfSpanA01Seconds
            << "\t" << terminalMetrics.firstHalfSpanA0GapAfterA01Seconds
            << "\t" << terminalMetrics.firstHalfSpanA0ChildKnownSeconds
            << "\t" << terminalMetrics.firstHalfSpanA0UnexplainedSeconds
            << "\t" << terminalMetrics.firstHalfSpanAChildKnownSeconds
            << "\t" << terminalMetrics.firstHalfSpanAUnexplainedSeconds
            << "\t" << terminalMetrics.firstHalfSpanBSeconds
            << "\t" << terminalMetrics.firstHalfChildKnownSeconds
            << "\t" << terminalMetrics.firstHalfUnexplainedSeconds
            << "\t" << terminalMetrics.firstHalfSpanADominantChild
            << "\t" << terminalMetrics.firstHalfSpanA0DominantChild
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00DominantChild
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0DominantChild
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltDominantChild
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightDominantChild
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartDominantChild
            << "\t" << replay.storeOtherMergeContextApplyMutateSeconds
            << "\t" << replay.storeOtherMergeContextApplyFinalizeSeconds
            << "\t" << replay.storeOtherMergeContextApplyAttemptedCount
            << "\t" << replay.storeOtherMergeContextApplyModifiedCount
            << "\t" << replay.storeOtherMergeContextApplyNoopCount
            << "\t" << replay.storeOtherMergeContextApplyLookupHitCount
            << "\t" << replay.storeOtherMergeContextApplyFullSetMissCount
            << "\t" << replay.storeOtherMergeContextApplyFloorChangedCount
            << "\t" << replay.storeOtherMergeContextApplyFloorChangedShare
            << "\t" << replay.storeOtherMergeContextApplyRunningMinSlotChangedCount
            << "\t" << replay.storeOtherMergeContextApplyRunningMinSlotChangedShare
            << "\t" << replay.storeOtherMergeContextApplyVictimWasRunningMinCount
            << "\t" << replay.storeOtherMergeContextApplyVictimWasRunningMinShare
            << "\t" << replay.storeOtherMergeContextApplyRefreshMinCalls
            << "\t" << replay.storeOtherMergeContextApplyRefreshMinSlotsScanned
            << "\t" << replay.storeOtherMergeContextApplyRefreshMinSlotsScannedPerCall
            << "\t" << replay.storeOtherMergeContextApplyCandidateIndexLookupCount
            << "\t" << replay.storeOtherMergeContextApplyCandidateIndexHitCount
            << "\t" << replay.storeOtherMergeContextApplyCandidateIndexMissCount
            << "\t" << replay.storeOtherMergeContextApplyCandidateIndexEraseCount
            << "\t" << replay.storeOtherMergeContextApplyCandidateIndexInsertCount
            << "\t" << replay.storeOtherMergeContextApplyLookupMissCount
            << "\t" << replay.storeOtherMergeContextApplyLookupProbeStepsTotal
            << "\t" << replay.storeOtherMergeContextApplyLookupProbeStepsMax
            << "\t" << replay.storeOtherMergeContextApplyLookupMissOpenSlotCount
            << "\t" << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullCount
            << "\t" << replay.storeOtherMergeContextApplyEvictionSelectedCount
            << "\t" << replay.storeOtherMergeContextApplyReusedSlotCount
            << "\t" << terminalMetrics.eventCount
            << "\t" << terminalMetrics.firstHalfEventCount
            << "\t" << terminalMetrics.firstHalfSpanAEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0EventCount
            << "\t" << terminalMetrics.firstHalfSpanA1EventCount
            << "\t" << terminalMetrics.firstHalfSpanA00EventCount
            << "\t" << terminalMetrics.firstHalfSpanA01EventCount
            << "\t" << terminalMetrics.firstHalfSpanBEventCount
            << "\t" << terminalMetrics.firstHalfSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0SampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0CoveredSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00SampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00CoveredSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0SampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0CoveredSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0Child0SampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0Child1SampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltCoveredSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltLeftSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightCoveredSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild0SampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild1SampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartCoveredSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span1SampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA00SampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBetweenA00A01SampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA01SampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapAfterA01SampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00UnclassifiedSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00MultiChildSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0UnclassifiedSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0MultiChildSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltUnclassifiedSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltMultiChildSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightUnclassifiedSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightMultiChildSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartUnclassifiedSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartMultiChildSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0UnclassifiedSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0MultiChildSampledEventCount
            << "\t" << terminalMetrics.firstHalfSpanA0OverlapSampledEventCount
            << "\t" << terminalMetrics.candidateSlotWriteCount
            << "\t" << terminalMetrics.startIndexWriteCount
            << "\t" << terminalMetrics.stateUpdateCount
            << "\t" << terminalMetrics.stateUpdateSampledEventCount
            << "\t" << terminalMetrics.stateUpdateCoveredSampledEventCount
            << "\t" << terminalMetrics.stateUpdateUnclassifiedSampledEventCount
            << "\t" << terminalMetrics.stateUpdateMultiChildSampledEventCount
            << "\t" << terminalMetrics.stateUpdateHeapBuildSampledEventCount
            << "\t" << terminalMetrics.stateUpdateHeapUpdateSampledEventCount
            << "\t" << terminalMetrics.stateUpdateStartIndexRebuildSampledEventCount
            << "\t" << terminalMetrics.stateUpdateTraceOrProfileBookkeepingSampledEventCount
            << "\t" << terminalMetrics.stateUpdateCoverageSource
            << "\t" << terminalMetrics.productionStateUpdateSampledEventCount
            << "\t" << terminalMetrics.productionStateUpdateCoveredSampledEventCount
            << "\t" << terminalMetrics.productionStateUpdateUnclassifiedSampledEventCount
            << "\t" << terminalMetrics.productionStateUpdateMultiChildSampledEventCount
            << "\t" << terminalMetrics.productionStateUpdateBenchmarkCounterSampledEventCount
            << "\t" << terminalMetrics.productionStateUpdateTraceReplayRequiredStateSampledEventCount
            << "\t" << terminalMetrics.productionStateUpdateCoverageSource
            << "\t" << terminalMetrics.stateUpdateEventCount
            << "\t" << terminalMetrics.stateUpdateHeapBuildCount
            << "\t" << terminalMetrics.stateUpdateHeapUpdateCount
            << "\t" << terminalMetrics.stateUpdateStartIndexRebuildCount
            << "\t" << terminalMetrics.stateUpdateTraceOrProfileBookkeepingCount
            << "\t" << terminalMetrics.stateUpdateAuxUpdatesTotal
            << "\t" << terminalMetrics.productionStateUpdateEventCount
            << "\t" << terminalMetrics.productionStateUpdateBenchmarkCounterCount
            << "\t" << terminalMetrics.productionStateUpdateTraceReplayRequiredStateCount
            << "\t" << terminalMetrics.timerCallCount
            << "\t" << terminalMetrics.terminalTimerCallCount
            << "\t" << terminalMetrics.lexicalTimerCallCount
            << "\t" << terminalMetrics.candidateBytesWritten
            << "\t" << terminalMetrics.startIndexBytesWritten
            << "\t" << benchmarkSourceOriginalPath
            << "\t" << benchmarkSourceCopiedPath
            << "\t" << benchmarkSourceSha256
            << "\t" << benchmarkSourceSizeBytes
            << "\t" << benchmarkIdentityBasis
            << "\t" << (verifyOk ? 1 : 0)
            << "\n";

        if (!aggregateTsvPath.empty())
        {
            const SimInitialHostMergeReplayTimingSummary contextApplySummary =
                summarizeSimInitialHostMergeReplaySamples(contextApplySamples);
            const SimInitialHostMergeReplayTimingSummary fullSetMissSummary =
                summarizeSimInitialHostMergeReplaySamples(fullSetMissSamples);
            const SimInitialHostMergeReplayTimingSummary refreshMinSummary =
                summarizeSimInitialHostMergeReplaySamples(refreshMinSamples);
            const SimInitialHostMergeReplayTimingSummary candidateIndexSummary =
                summarizeSimInitialHostMergeReplaySamples(candidateIndexSamples);
            const SimInitialHostMergeReplayTimingSummary candidateIndexEraseSummary =
                summarizeSimInitialHostMergeReplaySamples(candidateIndexEraseSamples);
            const SimInitialHostMergeReplayTimingSummary candidateIndexInsertSummary =
                summarizeSimInitialHostMergeReplaySamples(candidateIndexInsertSamples);
            const SimInitialHostMergeReplayTimingSummary lookupSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissOpenSlotSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissOpenSlotSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissCandidateSetFullProbeSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissCandidateSetFullProbeSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissCandidateSetFullProbeScanSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    lookupMissCandidateSetFullProbeScanSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissCandidateSetFullProbeCompareSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    lookupMissCandidateSetFullProbeCompareSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissCandidateSetFullProbeBranchOrGuardSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    lookupMissCandidateSetFullProbeBranchOrGuardSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissCandidateSetFullProbeBookkeepingSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    lookupMissCandidateSetFullProbeBookkeepingSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissCandidateSetFullProbeChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    lookupMissCandidateSetFullProbeChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissCandidateSetFullProbeUnexplainedSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    lookupMissCandidateSetFullProbeUnexplainedSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissEvictionSelectSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissEvictionSelectSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackVictimResetSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackVictimResetSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackKeyRebindSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackKeyRebindSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackCandidateCopySummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackCandidateCopySamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackAuxBookkeepingSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackAuxBookkeepingSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackAuxHeapBuildSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackAuxHeapBuildSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackAuxHeapUpdateSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackAuxHeapUpdateSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackAuxStartIndexRebuildSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackAuxStartIndexRebuildSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackAuxOtherSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackAuxOtherSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackAuxOtherHeapUpdateAccountingSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackAuxOtherHeapUpdateAccountingSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackAuxOtherStartIndexRebuildAccountingSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackAuxOtherStartIndexRebuildAccountingSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackAuxOtherTraceFinalizeSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackAuxOtherTraceFinalizeSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackAuxOtherResidualSummary =
                summarizeSimInitialHostMergeReplaySamples(lookupMissReuseWritebackAuxOtherResidualSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackAuxOtherResidualHeapBuildAccountingSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    lookupMissReuseWritebackAuxOtherResidualHeapBuildAccountingSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackAuxOtherResidualHeapUpdateTraceRecordSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    lookupMissReuseWritebackAuxOtherResidualHeapUpdateTraceRecordSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackAuxOtherResidualStartIndexRebuildTraceRecordSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    lookupMissReuseWritebackAuxOtherResidualStartIndexRebuildTraceRecordSamples);
            const SimInitialHostMergeReplayTimingSummary lookupMissReuseWritebackAuxOtherResidualResidualSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    lookupMissReuseWritebackAuxOtherResidualResidualSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathParentSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathParentSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathCandidateSlotWriteSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathCandidateSlotWriteSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStartIndexWriteSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStartIndexWriteSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStartIndexWriteParentSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStartIndexWriteParentSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStartIndexWriteLeftSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStartIndexWriteLeftSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStartIndexWriteRightSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStartIndexWriteRightSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStartIndexWriteChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStartIndexWriteChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStartIndexWriteUnexplainedSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStartIndexWriteUnexplainedSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStartIndexStoreParentSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStartIndexStoreParentSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStartIndexStoreInsertSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStartIndexStoreInsertSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStartIndexStoreClearSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStartIndexStoreClearSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStartIndexStoreOverwriteSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStartIndexStoreOverwriteSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStartIndexStoreChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStartIndexStoreChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStartIndexStoreUnexplainedSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStartIndexStoreUnexplainedSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStateUpdateSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStateUpdateSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStateUpdateParentSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathStateUpdateParentSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStateUpdateHeapBuildSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalPathStateUpdateHeapBuildSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStateUpdateHeapUpdateSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalPathStateUpdateHeapUpdateSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStateUpdateStartIndexRebuildSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalPathStateUpdateStartIndexRebuildSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStateUpdateTraceOrProfileBookkeepingSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalPathStateUpdateTraceOrProfileBookkeepingSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStateUpdateChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalPathStateUpdateChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathStateUpdateUnexplainedSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalPathStateUpdateUnexplainedSamples);
            const SimInitialHostMergeReplayTimingSummary productionStateUpdateParentSummary =
                summarizeSimInitialHostMergeReplaySamples(productionStateUpdateParentSamples);
            const SimInitialHostMergeReplayTimingSummary productionStateUpdateBenchmarkCounterSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    productionStateUpdateBenchmarkCounterSamples);
            const SimInitialHostMergeReplayTimingSummary productionStateUpdateTraceReplayRequiredStateSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    productionStateUpdateTraceReplayRequiredStateSamples);
            const SimInitialHostMergeReplayTimingSummary productionStateUpdateChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    productionStateUpdateChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary productionStateUpdateUnexplainedSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    productionStateUpdateUnexplainedSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathTelemetryOverheadSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathTelemetryOverheadSamples);
            const SimInitialHostMergeReplayTimingSummary terminalPathResidualSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalPathResidualSamples);
            const SimInitialHostMergeReplayTimingSummary terminalLexicalParentSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalLexicalParentSamples);
            const SimInitialHostMergeReplayTimingSummary terminalSpanFirstHalfSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalSpanFirstHalfSamples);
            const SimInitialHostMergeReplayTimingSummary terminalSpanSecondHalfSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalSpanSecondHalfSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfParentSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfParentSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanASummary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanASamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanAParentSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanAParentSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0Summary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanA0Samples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA1Summary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanA1Samples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0ParentSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanA0ParentSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Summary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanA0GapBeforeA00Samples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00ParentSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00ParentSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0Summary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0Samples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0ParentSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0ParentSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0Child0Summary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0Child0Samples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0Child1Summary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0Child1Samples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0AltParentSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0AltParentSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0AltLeftSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0AltLeftSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0AltRightSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0AltRightSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0AltRightUnexplainedSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0AltRightUnexplainedSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartUnexplainedSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartUnexplainedSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span1Summary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span1Samples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA00Summary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanA00Samples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBetweenA00A01Summary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanA0GapBetweenA00A01Samples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA01Summary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanA01Samples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapAfterA01Summary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanA0GapAfterA01Samples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00ChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00ChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00UnexplainedSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00UnexplainedSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0ChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0ChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0UnexplainedSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0UnexplainedSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0AltChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0AltChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0GapBeforeA00Span0AltUnexplainedSummary =
                summarizeSimInitialHostMergeReplaySamples(
                    terminalFirstHalfSpanA0GapBeforeA00Span0AltUnexplainedSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0ChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanA0ChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanA0UnexplainedSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanA0UnexplainedSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanAChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanAChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanAUnexplainedSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanAUnexplainedSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfSpanBSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfSpanBSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfChildKnownSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfChildKnownSamples);
            const SimInitialHostMergeReplayTimingSummary terminalFirstHalfUnexplainedSummary =
                summarizeSimInitialHostMergeReplaySamples(terminalFirstHalfUnexplainedSamples);
            const SimInitialHostMergeReplayTimingSummary mutateSummary =
                summarizeSimInitialHostMergeReplaySamples(mutateSamples);
            const SimInitialHostMergeReplayTimingSummary finalizeSummary =
                summarizeSimInitialHostMergeReplaySamples(finalizeSamples);

            aggregateTsv << selectedCase
                         << "\t" << candidate_index_backend_name(candidateIndexBackend)
                         << "\t" << profile_mode_name(profileMode)
                         << "\t" << profileSampleLog2
                         << "\t" << simInitialProfilerSampleRate()
                         << "\t"
                         << terminal_telemetry_overhead_mode_name(
                                simInitialTerminalTelemetryOverheadRequestedMode())
                         << "\t"
                         << terminal_telemetry_overhead_mode_name(
                                simInitialTerminalTelemetryOverheadEffectiveMode())
                         << "\t"
                         << state_update_bookkeeping_mode_name(
                                simInitialStateUpdateBookkeepingRequestedMode())
                         << "\t"
                         << state_update_bookkeeping_mode_name(
                                simInitialStateUpdateBookkeepingEffectiveMode())
                         << "\t" << warmupIterations
                         << "\t" << iterations
                         << "\t" << corpus.logicalEventCount
                         << "\t" << corpus.expectedContextCandidates.size()
                         << "\t" << replay.storeOtherMergeContextApplyAttemptedCount
                         << "\t" << replay.storeOtherMergeContextApplyModifiedCount
                         << "\t" << replay.storeOtherMergeContextApplyNoopCount
                         << "\t" << replay.storeOtherMergeContextApplyLookupHitCount
                         << "\t" << replay.storeOtherMergeContextApplyFullSetMissCount
                         << "\t" << replay.storeOtherMergeContextApplyFloorChangedCount
                         << "\t" << replay.storeOtherMergeContextApplyFloorChangedShare
                         << "\t" << replay.storeOtherMergeContextApplyRunningMinSlotChangedCount
                         << "\t" << replay.storeOtherMergeContextApplyRunningMinSlotChangedShare
                         << "\t" << replay.storeOtherMergeContextApplyVictimWasRunningMinCount
                         << "\t" << replay.storeOtherMergeContextApplyVictimWasRunningMinShare
                         << "\t" << replay.storeOtherMergeContextApplyRefreshMinCalls
                         << "\t" << replay.storeOtherMergeContextApplyRefreshMinSlotsScanned
                         << "\t" << replay.storeOtherMergeContextApplyRefreshMinSlotsScannedPerCall
                         << "\t" << replay.storeOtherMergeContextApplyCandidateIndexLookupCount
                         << "\t" << replay.storeOtherMergeContextApplyCandidateIndexHitCount
                         << "\t" << replay.storeOtherMergeContextApplyCandidateIndexMissCount
                         << "\t" << replay.storeOtherMergeContextApplyCandidateIndexEraseCount
                         << "\t" << replay.storeOtherMergeContextApplyCandidateIndexInsertCount
                         << "\t" << replay.storeOtherMergeContextApplyLookupMissCount
                         << "\t" << replay.storeOtherMergeContextApplyLookupProbeStepsTotal
                         << "\t" << replay.storeOtherMergeContextApplyLookupProbeStepsMax
                         << "\t" << replay.storeOtherMergeContextApplyLookupMissOpenSlotCount
                         << "\t" << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullCount
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeSampledEventCount
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeCoveredSampledEventCount
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeUnclassifiedSampledEventCount
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeMultiChildSampledEventCount
                         << "\t" << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeCount
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeSlotsScannedTotal
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeSlotsScannedPerProbeMean
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeSlotsScannedP50
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeSlotsScannedP90
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeSlotsScannedP99
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeFullScanCount
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeEarlyExitCount
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeFoundExistingCount
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeConfirmedAbsentCount
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeRedundantReprobeCount
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeSameKeyReprobeCount
                         << "\t"
                         << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeSameEventReprobeCount
                         << "\t" << replay.storeOtherMergeContextApplyEvictionSelectedCount
                         << "\t" << replay.storeOtherMergeContextApplyReusedSlotCount
                         << "\t" << contextApplySummary.meanSeconds
                         << "\t" << contextApplySummary.p50Seconds
                         << "\t" << contextApplySummary.p95Seconds
                         << "\t" << fullSetMissSummary.meanSeconds
                         << "\t" << fullSetMissSummary.p50Seconds
                         << "\t" << fullSetMissSummary.p95Seconds
                         << "\t" << refreshMinSummary.meanSeconds
                         << "\t" << refreshMinSummary.p50Seconds
                         << "\t" << refreshMinSummary.p95Seconds
                         << "\t" << candidateIndexSummary.meanSeconds
                         << "\t" << candidateIndexSummary.p50Seconds
                         << "\t" << candidateIndexSummary.p95Seconds
                         << "\t" << candidateIndexEraseSummary.meanSeconds
                         << "\t" << candidateIndexEraseSummary.p50Seconds
                         << "\t" << candidateIndexEraseSummary.p95Seconds
                         << "\t" << candidateIndexInsertSummary.meanSeconds
                         << "\t" << candidateIndexInsertSummary.p50Seconds
                         << "\t" << candidateIndexInsertSummary.p95Seconds
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
                         << "\t" << lookupMissCandidateSetFullProbeSummary.meanSeconds
                         << "\t" << lookupMissCandidateSetFullProbeScanSummary.meanSeconds
                         << "\t" << lookupMissCandidateSetFullProbeCompareSummary.meanSeconds
                         << "\t" << lookupMissCandidateSetFullProbeBranchOrGuardSummary.meanSeconds
                         << "\t" << lookupMissCandidateSetFullProbeBookkeepingSummary.meanSeconds
                         << "\t" << lookupMissCandidateSetFullProbeChildKnownSummary.meanSeconds
                         << "\t" << lookupMissCandidateSetFullProbeUnexplainedSummary.meanSeconds
                         << "\t" << lookupMissEvictionSelectSummary.meanSeconds
                         << "\t" << lookupMissEvictionSelectSummary.p50Seconds
                         << "\t" << lookupMissEvictionSelectSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackVictimResetSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackVictimResetSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackVictimResetSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackKeyRebindSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackKeyRebindSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackKeyRebindSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackCandidateCopySummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackCandidateCopySummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackCandidateCopySummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackAuxBookkeepingSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackAuxBookkeepingSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackAuxBookkeepingSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackAuxHeapBuildSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackAuxHeapBuildSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackAuxHeapBuildSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackAuxHeapUpdateSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackAuxHeapUpdateSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackAuxHeapUpdateSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackAuxStartIndexRebuildSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackAuxStartIndexRebuildSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackAuxStartIndexRebuildSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackAuxOtherSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherHeapUpdateAccountingSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackAuxOtherHeapUpdateAccountingSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherHeapUpdateAccountingSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherStartIndexRebuildAccountingSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackAuxOtherStartIndexRebuildAccountingSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherStartIndexRebuildAccountingSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherTraceFinalizeSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackAuxOtherTraceFinalizeSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherTraceFinalizeSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualHeapBuildAccountingSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualHeapBuildAccountingSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualHeapBuildAccountingSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualHeapUpdateTraceRecordSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualHeapUpdateTraceRecordSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualHeapUpdateTraceRecordSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualStartIndexRebuildTraceRecordSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualStartIndexRebuildTraceRecordSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualStartIndexRebuildTraceRecordSummary.p95Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualResidualSummary.meanSeconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualResidualSummary.p50Seconds
                         << "\t" << lookupMissReuseWritebackAuxOtherResidualResidualSummary.p95Seconds
                         << "\t" << terminalPathParentSummary.meanSeconds
                         << "\t" << terminalPathParentSummary.p50Seconds
                         << "\t" << terminalPathParentSummary.p95Seconds
                         << "\t" << terminalPathChildKnownSummary.meanSeconds
                         << "\t" << terminalPathChildKnownSummary.p50Seconds
                         << "\t" << terminalPathChildKnownSummary.p95Seconds
                         << "\t" << terminalPathCandidateSlotWriteSummary.meanSeconds
                         << "\t" << terminalPathCandidateSlotWriteSummary.p50Seconds
                         << "\t" << terminalPathCandidateSlotWriteSummary.p95Seconds
                         << "\t" << terminalPathStartIndexWriteSummary.meanSeconds
                         << "\t" << terminalPathStartIndexWriteSummary.p50Seconds
                         << "\t" << terminalPathStartIndexWriteSummary.p95Seconds
                         << "\t" << terminalPathStartIndexWriteParentSummary.meanSeconds
                         << "\t" << terminalPathStartIndexWriteParentSummary.p50Seconds
                         << "\t" << terminalPathStartIndexWriteParentSummary.p95Seconds
                         << "\t" << terminalPathStartIndexWriteLeftSummary.meanSeconds
                         << "\t" << terminalPathStartIndexWriteLeftSummary.p50Seconds
                         << "\t" << terminalPathStartIndexWriteLeftSummary.p95Seconds
                         << "\t" << terminalPathStartIndexWriteRightSummary.meanSeconds
                         << "\t" << terminalPathStartIndexWriteRightSummary.p50Seconds
                         << "\t" << terminalPathStartIndexWriteRightSummary.p95Seconds
                         << "\t" << terminalPathStartIndexWriteChildKnownSummary.meanSeconds
                         << "\t" << terminalPathStartIndexWriteChildKnownSummary.p50Seconds
                         << "\t" << terminalPathStartIndexWriteChildKnownSummary.p95Seconds
                         << "\t" << terminalPathStartIndexWriteUnexplainedSummary.meanSeconds
                         << "\t" << terminalPathStartIndexWriteUnexplainedSummary.p50Seconds
                         << "\t" << terminalPathStartIndexWriteUnexplainedSummary.p95Seconds
                         << "\t" << terminalPathStartIndexStoreParentSummary.meanSeconds
                         << "\t" << terminalPathStartIndexStoreParentSummary.p50Seconds
                         << "\t" << terminalPathStartIndexStoreParentSummary.p95Seconds
                         << "\t" << terminalPathStartIndexStoreInsertSummary.meanSeconds
                         << "\t" << terminalPathStartIndexStoreInsertSummary.p50Seconds
                         << "\t" << terminalPathStartIndexStoreInsertSummary.p95Seconds
                         << "\t" << terminalPathStartIndexStoreClearSummary.meanSeconds
                         << "\t" << terminalPathStartIndexStoreClearSummary.p50Seconds
                         << "\t" << terminalPathStartIndexStoreClearSummary.p95Seconds
                         << "\t" << terminalPathStartIndexStoreOverwriteSummary.meanSeconds
                         << "\t" << terminalPathStartIndexStoreOverwriteSummary.p50Seconds
                         << "\t" << terminalPathStartIndexStoreOverwriteSummary.p95Seconds
                         << "\t" << terminalPathStartIndexStoreChildKnownSummary.meanSeconds
                         << "\t" << terminalPathStartIndexStoreChildKnownSummary.p50Seconds
                         << "\t" << terminalPathStartIndexStoreChildKnownSummary.p95Seconds
                         << "\t" << terminalPathStartIndexStoreUnexplainedSummary.meanSeconds
                         << "\t" << terminalPathStartIndexStoreUnexplainedSummary.p50Seconds
                         << "\t" << terminalPathStartIndexStoreUnexplainedSummary.p95Seconds
                         << "\t" << terminalPathStateUpdateSummary.meanSeconds
                         << "\t" << terminalPathStateUpdateSummary.p50Seconds
                         << "\t" << terminalPathStateUpdateSummary.p95Seconds
                         << "\t" << terminalPathStateUpdateParentSummary.meanSeconds
                         << "\t" << terminalPathStateUpdateParentSummary.p50Seconds
                         << "\t" << terminalPathStateUpdateParentSummary.p95Seconds
                         << "\t" << terminalPathStateUpdateHeapBuildSummary.meanSeconds
                         << "\t" << terminalPathStateUpdateHeapBuildSummary.p50Seconds
                         << "\t" << terminalPathStateUpdateHeapBuildSummary.p95Seconds
                         << "\t" << terminalPathStateUpdateHeapUpdateSummary.meanSeconds
                         << "\t" << terminalPathStateUpdateHeapUpdateSummary.p50Seconds
                         << "\t" << terminalPathStateUpdateHeapUpdateSummary.p95Seconds
                         << "\t" << terminalPathStateUpdateStartIndexRebuildSummary.meanSeconds
                         << "\t" << terminalPathStateUpdateStartIndexRebuildSummary.p50Seconds
                         << "\t" << terminalPathStateUpdateStartIndexRebuildSummary.p95Seconds
                         << "\t" << terminalPathStateUpdateTraceOrProfileBookkeepingSummary.meanSeconds
                         << "\t" << terminalPathStateUpdateTraceOrProfileBookkeepingSummary.p50Seconds
                         << "\t" << terminalPathStateUpdateTraceOrProfileBookkeepingSummary.p95Seconds
                         << "\t" << terminalPathStateUpdateChildKnownSummary.meanSeconds
                         << "\t" << terminalPathStateUpdateChildKnownSummary.p50Seconds
                         << "\t" << terminalPathStateUpdateChildKnownSummary.p95Seconds
                         << "\t" << terminalPathStateUpdateUnexplainedSummary.meanSeconds
                         << "\t" << terminalPathStateUpdateUnexplainedSummary.p50Seconds
                         << "\t" << terminalPathStateUpdateUnexplainedSummary.p95Seconds
                         << "\t" << productionStateUpdateParentSummary.meanSeconds
                         << "\t" << productionStateUpdateParentSummary.p50Seconds
                         << "\t" << productionStateUpdateParentSummary.p95Seconds
                         << "\t" << productionStateUpdateParentSummary.meanSeconds
                         << "\t" << productionStateUpdateParentSummary.p50Seconds
                         << "\t" << productionStateUpdateParentSummary.p95Seconds
                         << "\t" << productionStateUpdateBenchmarkCounterSummary.meanSeconds
                         << "\t" << productionStateUpdateBenchmarkCounterSummary.p50Seconds
                         << "\t" << productionStateUpdateBenchmarkCounterSummary.p95Seconds
                         << "\t" << productionStateUpdateTraceReplayRequiredStateSummary.meanSeconds
                         << "\t" << productionStateUpdateTraceReplayRequiredStateSummary.p50Seconds
                         << "\t" << productionStateUpdateTraceReplayRequiredStateSummary.p95Seconds
                         << "\t" << productionStateUpdateChildKnownSummary.meanSeconds
                         << "\t" << productionStateUpdateChildKnownSummary.p50Seconds
                         << "\t" << productionStateUpdateChildKnownSummary.p95Seconds
                         << "\t" << productionStateUpdateUnexplainedSummary.meanSeconds
                         << "\t" << productionStateUpdateUnexplainedSummary.p50Seconds
                         << "\t" << productionStateUpdateUnexplainedSummary.p95Seconds
                         << "\t" << terminalPathTelemetryOverheadSummary.meanSeconds
                         << "\t" << terminalPathTelemetryOverheadSummary.p50Seconds
                         << "\t" << terminalPathTelemetryOverheadSummary.p95Seconds
                         << "\t" << terminalPathResidualSummary.meanSeconds
                         << "\t" << terminalPathResidualSummary.p50Seconds
                         << "\t" << terminalPathResidualSummary.p95Seconds
                         << "\t" << terminalLexicalParentSummary.meanSeconds
                         << "\t" << terminalLexicalParentSummary.p50Seconds
                         << "\t" << terminalLexicalParentSummary.p95Seconds
                         << "\t" << terminalSpanFirstHalfSummary.meanSeconds
                         << "\t" << terminalSpanFirstHalfSummary.p50Seconds
                         << "\t" << terminalSpanFirstHalfSummary.p95Seconds
                         << "\t" << terminalSpanSecondHalfSummary.meanSeconds
                         << "\t" << terminalSpanSecondHalfSummary.p50Seconds
                         << "\t" << terminalSpanSecondHalfSummary.p95Seconds
                         << "\t" << terminalFirstHalfParentSummary.meanSeconds
                         << "\t" << terminalFirstHalfParentSummary.p50Seconds
                         << "\t" << terminalFirstHalfParentSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanASummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanASummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanASummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanAParentSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanAParentSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanAParentSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0Summary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0Summary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0Summary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA1Summary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA1Summary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA1Summary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0ParentSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0ParentSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0ParentSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Summary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Summary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Summary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00ParentSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00ParentSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00ParentSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0Summary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0Summary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0Summary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0ParentSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0ParentSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0ParentSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0Child0Summary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0Child0Summary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0Child0Summary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0Child1Summary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0Child1Summary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0Child1Summary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltParentSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltParentSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltParentSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltLeftSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltLeftSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltLeftSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0Child1Summary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0Child1Summary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0Child1Summary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span1Summary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span1Summary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span1Summary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartParentSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span1Summary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span1Summary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span1Summary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00ChildKnownSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00ChildKnownSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00ChildKnownSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00UnexplainedSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00UnexplainedSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00UnexplainedSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0ChildKnownSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0ChildKnownSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0ChildKnownSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0UnexplainedSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0UnexplainedSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0UnexplainedSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltChildKnownSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltChildKnownSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltChildKnownSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltUnexplainedSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltUnexplainedSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltUnexplainedSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightChildKnownSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightUnexplainedSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightUnexplainedSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightUnexplainedSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartChildKnownSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartUnexplainedSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartUnexplainedSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBeforeA00Span0AltRightRepartUnexplainedSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA00Summary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA00Summary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA00Summary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBetweenA00A01Summary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapBetweenA00A01Summary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapBetweenA00A01Summary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA01Summary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA01Summary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA01Summary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0GapAfterA01Summary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0GapAfterA01Summary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0GapAfterA01Summary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0ChildKnownSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0ChildKnownSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0ChildKnownSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanA0UnexplainedSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanA0UnexplainedSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanA0UnexplainedSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanAChildKnownSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanAChildKnownSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanAChildKnownSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanAUnexplainedSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanAUnexplainedSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanAUnexplainedSummary.p95Seconds
                         << "\t" << terminalFirstHalfSpanBSummary.meanSeconds
                         << "\t" << terminalFirstHalfSpanBSummary.p50Seconds
                         << "\t" << terminalFirstHalfSpanBSummary.p95Seconds
                         << "\t" << terminalFirstHalfChildKnownSummary.meanSeconds
                         << "\t" << terminalFirstHalfChildKnownSummary.p50Seconds
                         << "\t" << terminalFirstHalfChildKnownSummary.p95Seconds
                         << "\t" << terminalFirstHalfUnexplainedSummary.meanSeconds
                         << "\t" << terminalFirstHalfUnexplainedSummary.p50Seconds
                         << "\t" << terminalFirstHalfUnexplainedSummary.p95Seconds
                         << "\t" << mutateSummary.meanSeconds
                         << "\t" << mutateSummary.p50Seconds
                         << "\t" << mutateSummary.p95Seconds
                         << "\t" << finalizeSummary.meanSeconds
                         << "\t" << finalizeSummary.p50Seconds
                         << "\t" << finalizeSummary.p95Seconds
                         << "\t" << terminalMetrics.eventCount
                         << "\t" << terminalMetrics.firstHalfEventCount
                         << "\t" << terminalMetrics.firstHalfSpanAEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0EventCount
                         << "\t" << terminalMetrics.firstHalfSpanA1EventCount
                         << "\t" << terminalMetrics.firstHalfSpanA00EventCount
                         << "\t" << terminalMetrics.firstHalfSpanA01EventCount
                         << "\t" << terminalMetrics.firstHalfSpanBEventCount
                         << "\t" << terminalMetrics.firstHalfSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0SampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0CoveredSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00SampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00CoveredSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0SampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0CoveredSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0Child0SampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0Child1SampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltCoveredSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltLeftSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightCoveredSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild0SampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightChild1SampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartCoveredSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartLeftSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartRightSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span1SampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA00SampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBetweenA00A01SampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA01SampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapAfterA01SampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00UnclassifiedSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00MultiChildSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0UnclassifiedSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0MultiChildSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltUnclassifiedSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltMultiChildSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightUnclassifiedSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightMultiChildSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartUnclassifiedSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartMultiChildSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0UnclassifiedSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0MultiChildSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanA0OverlapSampledEventCount
                         << "\t" << terminalMetrics.firstHalfSpanADominantChild
                         << "\t" << terminalMetrics.firstHalfSpanA0DominantChild
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00DominantChild
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0DominantChild
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltDominantChild
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightDominantChild
                         << "\t" << terminalMetrics.firstHalfSpanA0GapBeforeA00Span0AltRightRepartDominantChild
                         << "\t" << terminalMetrics.candidateSlotWriteCount
                         << "\t" << terminalMetrics.startIndexWriteCount
                         << "\t" << terminalMetrics.startIndexWriteSampledEventCount
                         << "\t" << terminalMetrics.startIndexWriteCoveredSampledEventCount
                         << "\t" << terminalMetrics.startIndexWriteUnclassifiedSampledEventCount
                         << "\t" << terminalMetrics.startIndexWriteMultiChildSampledEventCount
                         << "\t" << terminalMetrics.startIndexWriteLeftSampledEventCount
                         << "\t" << terminalMetrics.startIndexWriteRightSampledEventCount
                         << "\t" << terminalMetrics.startIndexWriteInsertCount
                         << "\t" << terminalMetrics.startIndexWriteUpdateExistingCount
                         << "\t" << terminalMetrics.startIndexWriteClearCount
                         << "\t" << terminalMetrics.startIndexWriteOverwriteCount
                         << "\t" << terminalMetrics.startIndexWriteIdempotentCount
                         << "\t" << terminalMetrics.startIndexWriteValueChangedCount
                         << "\t" << terminalMetrics.startIndexWriteProbeCount
                         << "\t" << terminalMetrics.startIndexWriteProbeStepsTotal
                         << "\t" << terminalMetrics.startIndexStoreSampledEventCount
                         << "\t" << terminalMetrics.startIndexStoreCoveredSampledEventCount
                         << "\t" << terminalMetrics.startIndexStoreUnclassifiedSampledEventCount
                         << "\t" << terminalMetrics.startIndexStoreMultiChildSampledEventCount
                         << "\t" << terminalMetrics.startIndexStoreInsertSampledEventCount
                         << "\t" << terminalMetrics.startIndexStoreClearSampledEventCount
                         << "\t" << terminalMetrics.startIndexStoreOverwriteSampledEventCount
                         << "\t" << terminalMetrics.startIndexStoreInsertCount
                         << "\t" << terminalMetrics.startIndexStoreClearCount
                         << "\t" << terminalMetrics.startIndexStoreOverwriteCount
                         << "\t" << terminalMetrics.startIndexStoreInsertBytes
                         << "\t" << terminalMetrics.startIndexStoreClearBytes
                         << "\t" << terminalMetrics.startIndexStoreOverwriteBytes
                         << "\t" << terminalMetrics.startIndexStoreUniqueEntryCount
                         << "\t" << terminalMetrics.startIndexStoreUniqueSlotCount
                         << "\t" << terminalMetrics.startIndexStoreUniqueKeyCount
                         << "\t" << terminalMetrics.startIndexStoreSameEntryRewriteCount
                         << "\t" << terminalMetrics.startIndexStoreSameCachelineRewriteCount
                         << "\t" << terminalMetrics.startIndexStoreBackToBackSameEntryWriteCount
                         << "\t" << terminalMetrics.startIndexStoreClearThenOverwriteSameEntryCount
                         << "\t" << terminalMetrics.startIndexStoreOverwriteThenInsertSameEntryCount
                         << "\t" << terminalMetrics.startIndexStoreInsertThenClearSameEntryCount
                         << "\t" << terminalMetrics.startIndexWriteDominantChild
                         << "\t" << terminalMetrics.stateUpdateCount
                         << "\t" << terminalMetrics.stateUpdateSampledEventCount
                         << "\t" << terminalMetrics.stateUpdateCoveredSampledEventCount
                         << "\t" << terminalMetrics.stateUpdateUnclassifiedSampledEventCount
                         << "\t" << terminalMetrics.stateUpdateMultiChildSampledEventCount
                         << "\t" << terminalMetrics.stateUpdateHeapBuildSampledEventCount
                         << "\t" << terminalMetrics.stateUpdateHeapUpdateSampledEventCount
                         << "\t" << terminalMetrics.stateUpdateStartIndexRebuildSampledEventCount
                         << "\t" << terminalMetrics.stateUpdateTraceOrProfileBookkeepingSampledEventCount
                         << "\t" << terminalMetrics.stateUpdateCoverageSource
                         << "\t" << terminalMetrics.productionStateUpdateSampledEventCount
                         << "\t" << terminalMetrics.productionStateUpdateCoveredSampledEventCount
                         << "\t" << terminalMetrics.productionStateUpdateUnclassifiedSampledEventCount
                         << "\t" << terminalMetrics.productionStateUpdateMultiChildSampledEventCount
                         << "\t" << terminalMetrics.productionStateUpdateBenchmarkCounterSampledEventCount
                         << "\t" << terminalMetrics.productionStateUpdateTraceReplayRequiredStateSampledEventCount
                         << "\t" << terminalMetrics.productionStateUpdateCoverageSource
                         << "\t" << terminalMetrics.stateUpdateEventCount
                         << "\t" << terminalMetrics.stateUpdateHeapBuildCount
                         << "\t" << terminalMetrics.stateUpdateHeapUpdateCount
                         << "\t" << terminalMetrics.stateUpdateStartIndexRebuildCount
                         << "\t" << terminalMetrics.stateUpdateTraceOrProfileBookkeepingCount
                         << "\t" << terminalMetrics.stateUpdateAuxUpdatesTotal
                         << "\t" << terminalMetrics.productionStateUpdateEventCount
                         << "\t" << terminalMetrics.productionStateUpdateBenchmarkCounterCount
                         << "\t" << terminalMetrics.productionStateUpdateTraceReplayRequiredStateCount
                         << "\t" << terminalMetrics.timerCallCount
                         << "\t" << terminalMetrics.terminalTimerCallCount
                         << "\t" << terminalMetrics.lexicalTimerCallCount
                         << "\t" << terminalMetrics.candidateBytesWritten
                         << "\t" << terminalMetrics.startIndexBytesWritten
                         << "\t";
            write_optional_metric(aggregateTsv,
                                  workloadBenchmarkMetrics.hasSimInitialScanSeconds,
                                  workloadBenchmarkMetrics.simInitialScanSeconds);
            aggregateTsv << "\t";
            write_optional_metric(aggregateTsv,
                                  workloadBenchmarkMetrics.hasSimInitialScanCpuMergeSeconds,
                                  workloadBenchmarkMetrics.simInitialScanCpuMergeSeconds);
            aggregateTsv << "\t";
            write_optional_metric(aggregateTsv,
                                  workloadBenchmarkMetrics.hasSimInitialScanCpuMergeSubtotalSeconds,
                                  workloadBenchmarkMetrics.simInitialScanCpuMergeSubtotalSeconds);
            aggregateTsv << "\t";
            write_optional_metric(aggregateTsv,
                                  workloadBenchmarkMetrics.hasSimSeconds,
                                  workloadBenchmarkMetrics.simSeconds);
            aggregateTsv << "\t";
            write_optional_metric(aggregateTsv,
                                  workloadBenchmarkMetrics.hasTotalSeconds,
                                  workloadBenchmarkMetrics.totalSeconds);
            aggregateTsv
                         << "\t";
            if (!benchmarkStderrPath.empty())
            {
                aggregateTsv << workloadId;
            }
            aggregateTsv << "\t";
            if (!benchmarkStderrPath.empty())
            {
                aggregateTsv << benchmarkStderrPath;
            }
            aggregateTsv
                         << "\t" << benchmarkSourceOriginalPath
                         << "\t" << benchmarkSourceCopiedPath
                         << "\t" << benchmarkSourceSha256
                         << "\t" << benchmarkSourceSizeBytes
                         << "\t" << benchmarkIdentityBasis
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
