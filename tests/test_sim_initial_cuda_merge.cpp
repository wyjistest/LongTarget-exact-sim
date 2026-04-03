#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <vector>

#include "../sim.h"

namespace
{

static std::vector<SimCandidate> sorted_candidates(const SimKernelContext &context)
{
    std::vector<SimCandidate> candidates(static_cast<size_t>(context.candidateCount));
    for (long i = 0; i < context.candidateCount; ++i)
    {
        candidates[static_cast<size_t>(i)] = context.candidates[static_cast<size_t>(i)];
    }
    std::sort(candidates.begin(), candidates.end(), [](const SimCandidate &lhs, const SimCandidate &rhs) {
        if (lhs.SCORE != rhs.SCORE) return lhs.SCORE < rhs.SCORE;
        if (lhs.STARI != rhs.STARI) return lhs.STARI < rhs.STARI;
        if (lhs.STARJ != rhs.STARJ) return lhs.STARJ < rhs.STARJ;
        if (lhs.ENDI != rhs.ENDI) return lhs.ENDI < rhs.ENDI;
        if (lhs.ENDJ != rhs.ENDJ) return lhs.ENDJ < rhs.ENDJ;
        if (lhs.TOP != rhs.TOP) return lhs.TOP < rhs.TOP;
        if (lhs.BOT != rhs.BOT) return lhs.BOT < rhs.BOT;
        if (lhs.LEFT != rhs.LEFT) return lhs.LEFT < rhs.LEFT;
        return lhs.RIGHT < rhs.RIGHT;
    });
    return candidates;
}

static bool expect_equal_long(long actual, long expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_true(bool value, const char *label)
{
    if (value)
    {
        return true;
    }
    std::cerr << label << ": expected true, got false\n";
    return false;
}

static void get_initial_cpu_merge_breakdown(uint64_t &totalNanoseconds,
                                            uint64_t &contextApplyNanoseconds,
                                            uint64_t &safeStoreUpdateNanoseconds,
                                            uint64_t &safeStorePruneNanoseconds,
                                            uint64_t &safeStoreUploadNanoseconds)
{
    totalNanoseconds = simInitialScanCpuMergeNanoseconds().load(std::memory_order_relaxed);
    getSimInitialCpuMergeTimingNanoseconds(contextApplyNanoseconds,
                                           safeStoreUpdateNanoseconds,
                                           safeStorePruneNanoseconds,
                                           safeStoreUploadNanoseconds);
}

static bool expect_candidates_equal(const SimKernelContext &actual,
                                    const SimKernelContext &expected,
                                    const char *label)
{
    if (actual.candidateCount != expected.candidateCount)
    {
        std::cerr << label << ": candidateCount mismatch expected "
                  << expected.candidateCount << ", got " << actual.candidateCount << "\n";
        return false;
    }

    const std::vector<SimCandidate> lhs = sorted_candidates(actual);
    const std::vector<SimCandidate> rhs = sorted_candidates(expected);
    for (size_t i = 0; i < lhs.size(); ++i)
    {
        if (memcmp(&lhs[i], &rhs[i], sizeof(SimCandidate)) != 0)
        {
            std::cerr << label << ": candidate mismatch at index " << i
                      << " expected(score=" << rhs[i].SCORE
                      << ", stari=" << rhs[i].STARI
                      << ", starj=" << rhs[i].STARJ
                      << ", endi=" << rhs[i].ENDI
                      << ", endj=" << rhs[i].ENDJ
                      << ", top=" << rhs[i].TOP
                      << ", bot=" << rhs[i].BOT
                      << ", left=" << rhs[i].LEFT
                      << ", right=" << rhs[i].RIGHT
                      << ") got(score=" << lhs[i].SCORE
                      << ", stari=" << lhs[i].STARI
                      << ", starj=" << lhs[i].STARJ
                      << ", endi=" << lhs[i].ENDI
                      << ", endj=" << lhs[i].ENDJ
                      << ", top=" << lhs[i].TOP
                      << ", bot=" << lhs[i].BOT
                      << ", left=" << lhs[i].LEFT
                      << ", right=" << lhs[i].RIGHT
                      << ")\n";
            return false;
        }
    }
    return true;
}

static bool candidates_equal(const SimKernelContext &actual,
                             const SimKernelContext &expected)
{
    if (actual.candidateCount != expected.candidateCount)
    {
        return false;
    }

    const std::vector<SimCandidate> lhs = sorted_candidates(actual);
    const std::vector<SimCandidate> rhs = sorted_candidates(expected);
    for (size_t i = 0; i < lhs.size(); ++i)
    {
        if (memcmp(&lhs[i], &rhs[i], sizeof(SimCandidate)) != 0)
        {
            return false;
        }
    }
    return true;
}

static void replay_baseline(const std::vector<SimScanCudaRowEvent> &events,
                            const std::vector<int> &rowOffsets,
                            long rowCount,
                            SimKernelContext &context)
{
    SimCandidateEventUpdater updater(context);
    for (long endI = 1; endI <= rowCount; ++endI)
    {
        const int startIndex = rowOffsets[static_cast<size_t>(endI)];
        const int endIndex = rowOffsets[static_cast<size_t>(endI + 1)];
        for (int eventIndex = startIndex; eventIndex < endIndex; ++eventIndex)
        {
            const SimScanCudaRowEvent &event = events[static_cast<size_t>(eventIndex)];
            updater(SimInitialCellEvent(static_cast<long>(event.score),
                                        static_cast<long>(unpackSimCoordI(event.startCoord)),
                                        static_cast<long>(unpackSimCoordJ(event.startCoord)),
                                        static_cast<long>(endI),
                                        static_cast<long>(event.endJ)));
        }
    }
    updater.finish();
}

static bool expect_equal_size(size_t actual, size_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static std::vector<SimScanCudaCandidateState> sorted_candidate_states(const std::vector<SimScanCudaCandidateState> &states)
{
    std::vector<SimScanCudaCandidateState> sorted = states;
    std::sort(sorted.begin(), sorted.end(), [](const SimScanCudaCandidateState &lhs, const SimScanCudaCandidateState &rhs) {
        const uint64_t lhsStart = simScanCudaCandidateStateStartCoord(lhs);
        const uint64_t rhsStart = simScanCudaCandidateStateStartCoord(rhs);
        if (lhsStart != rhsStart) return lhsStart < rhsStart;
        if (lhs.score != rhs.score) return lhs.score < rhs.score;
        if (lhs.endI != rhs.endI) return lhs.endI < rhs.endI;
        if (lhs.endJ != rhs.endJ) return lhs.endJ < rhs.endJ;
        if (lhs.top != rhs.top) return lhs.top < rhs.top;
        if (lhs.bot != rhs.bot) return lhs.bot < rhs.bot;
        if (lhs.left != rhs.left) return lhs.left < rhs.left;
        return lhs.right < rhs.right;
    });
    return sorted;
}

static bool expect_candidate_states_equal(const std::vector<SimScanCudaCandidateState> &actual,
                                         const std::vector<SimScanCudaCandidateState> &expected,
                                         const char *label)
{
    if (actual.size() != expected.size())
    {
        std::cerr << label << ": size mismatch expected "
                  << expected.size() << ", got " << actual.size() << "\n";
        return false;
    }

    const std::vector<SimScanCudaCandidateState> lhs = sorted_candidate_states(actual);
    const std::vector<SimScanCudaCandidateState> rhs = sorted_candidate_states(expected);
    for (size_t i = 0; i < lhs.size(); ++i)
    {
        if (memcmp(&lhs[i], &rhs[i], sizeof(SimScanCudaCandidateState)) != 0)
        {
            std::cerr << label << ": state mismatch at index " << i << "\n";
            return false;
        }
    }
    return true;
}

static bool expect_store_states_equal(const SimCandidateStateStore &actual,
                                      const std::vector<SimScanCudaCandidateState> &expected,
                                      const char *label)
{
    if (!actual.valid)
    {
        std::cerr << label << ": expected valid store, got invalid\n";
        return false;
    }
    return expect_candidate_states_equal(actual.states, expected, label);
}

static const SimCandidate *find_candidate_by_start(const SimKernelContext &context,
                                                   long startI,
                                                   long startJ)
{
    for (long i = 0; i < context.candidateCount; ++i)
    {
        const SimCandidate &candidate = context.candidates[static_cast<size_t>(i)];
        if (candidate.STARI == startI && candidate.STARJ == startJ)
        {
            return &candidate;
        }
    }
    return NULL;
}

static const SimScanCudaCandidateState *find_candidate_state_by_start(const std::vector<SimScanCudaCandidateState> &states,
                                                                      uint64_t startCoord)
{
    for (size_t i = 0; i < states.size(); ++i)
    {
        if (simScanCudaCandidateStateStartCoord(states[i]) == startCoord)
        {
            return &states[i];
        }
    }
    return NULL;
}

static bool expect_summary_equal(const SimScanCudaInitialRunSummary &actual,
                                 const SimScanCudaInitialRunSummary &expected,
                                 const char *label)
{
    if (std::memcmp(&actual, &expected, sizeof(SimScanCudaInitialRunSummary)) == 0)
    {
        return true;
    }
    std::cerr << label << ": summary mismatch"
              << " expected(score=" << expected.score
              << ", startI=" << unpackSimCoordI(expected.startCoord)
              << ", startJ=" << unpackSimCoordJ(expected.startCoord)
              << ", endI=" << expected.endI
              << ", minEndJ=" << expected.minEndJ
              << ", maxEndJ=" << expected.maxEndJ
              << ", scoreEndJ=" << expected.scoreEndJ
              << ") got(score=" << actual.score
              << ", startI=" << unpackSimCoordI(actual.startCoord)
              << ", startJ=" << unpackSimCoordJ(actual.startCoord)
              << ", endI=" << actual.endI
              << ", minEndJ=" << actual.minEndJ
              << ", maxEndJ=" << actual.maxEndJ
              << ", scoreEndJ=" << actual.scoreEndJ
              << ")\n";
    return false;
}

static void reduce_summaries_with_live_floor_skip_unsafe(const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                                         SimKernelContext &context)
{
    SimCandidateStats *stats = context.statsEnabled ? &context.stats : NULL;
    refreshSimRunningMin(context);
    for (size_t summaryIndex = 0; summaryIndex < summaries.size(); ++summaryIndex)
    {
        const SimScanCudaInitialRunSummary &summary = summaries[summaryIndex];
        if (static_cast<long>(summary.score) <= context.runningMin)
        {
            continue;
        }
        applySimCudaInitialRunSummary(summary, context, stats);
        refreshSimRunningMin(context);
    }
}

} // namespace

int main()
{
    setenv("LONGTARGET_PRINT_SIM_STATS", "1", 1);
    setenv("LONGTARGET_ENABLE_SIM_CUDA_PROPOSAL_LOOP", "1", 1);

    bool ok = true;

    SimScanCudaProposalRowSummaryState proposalState;
    resetSimScanCudaProposalRowSummaryState(proposalState);
    SimScanCudaInitialRunSummary flushedSummary;
    const SimScanCudaRowEvent proposalEvent0{10, packSimCoord(1, 1), 1, 2};
    const SimScanCudaRowEvent proposalEvent1{13, packSimCoord(1, 1), 1, 5};
    const SimScanCudaRowEvent proposalEvent2{13, packSimCoord(1, 1), 1, 8};
    const SimScanCudaRowEvent proposalEvent3{9, packSimCoord(1, 3), 1, 9};
    ok = expect_true(!simScanCudaProposalRowSummaryPushEvent(proposalEvent0,
                                                             proposalState,
                                                             &flushedSummary),
                     "proposal state starts without flush") && ok;
    ok = expect_true(!simScanCudaProposalRowSummaryPushEvent(proposalEvent1,
                                                             proposalState,
                                                             &flushedSummary),
                     "proposal state keeps run across filtered gap") && ok;
    ok = expect_true(!simScanCudaProposalRowSummaryPushEvent(proposalEvent2,
                                                             proposalState,
                                                             &flushedSummary),
                     "proposal state keeps first scoreEndJ on tie") && ok;
    SimScanCudaInitialRunSummary expectedProposalSummary0{13, packSimCoord(1, 1), 1, 2, 8, 5};
    ok = expect_true(simScanCudaProposalRowSummaryPushEvent(proposalEvent3,
                                                            proposalState,
                                                            &flushedSummary),
                     "proposal state flushes on startCoord change") && ok;
    ok = expect_summary_equal(flushedSummary,
                              expectedProposalSummary0,
                              "proposal state flushed summary") && ok;
    SimScanCudaInitialRunSummary expectedProposalSummary1{9, packSimCoord(1, 3), 1, 9, 9, 9};
    ok = expect_true(simScanCudaProposalRowSummaryFlush(proposalState,
                                                        &flushedSummary),
                     "proposal state flushes at row end") && ok;
    ok = expect_summary_equal(flushedSummary,
                              expectedProposalSummary1,
                              "proposal state row-end summary") && ok;
    ok = expect_true(!simScanCudaProposalRowSummaryFlush(proposalState,
                                                         &flushedSummary),
                     "proposal state empty after row-end flush") && ok;

    const long rowCount = 3;
    std::vector<SimScanCudaRowEvent> events;
    events.push_back(SimScanCudaRowEvent{10, packSimCoord(1, 1), 1, 2});
    events.push_back(SimScanCudaRowEvent{12, packSimCoord(1, 1), 1, 3});
    events.push_back(SimScanCudaRowEvent{11, packSimCoord(1, 1), 1, 4});
    events.push_back(SimScanCudaRowEvent{9, packSimCoord(1, 2), 1, 4});
    events.push_back(SimScanCudaRowEvent{13, packSimCoord(1, 2), 1, 5});
    events.push_back(SimScanCudaRowEvent{13, packSimCoord(1, 2), 1, 6});
    events.push_back(SimScanCudaRowEvent{8, packSimCoord(2, 1), 2, 1});
    events.push_back(SimScanCudaRowEvent{14, packSimCoord(1, 1), 2, 2});
    events.push_back(SimScanCudaRowEvent{15, packSimCoord(1, 1), 2, 3});
    events.push_back(SimScanCudaRowEvent{7, packSimCoord(2, 1), 2, 4});
    events.push_back(SimScanCudaRowEvent{16, packSimCoord(3, 3), 3, 3});
    events.push_back(SimScanCudaRowEvent{17, packSimCoord(1, 1), 3, 4});

    std::vector<int> rowOffsets;
    rowOffsets.push_back(0);
    rowOffsets.push_back(0);
    rowOffsets.push_back(6);
    rowOffsets.push_back(10);
    rowOffsets.push_back(12);

    SimKernelContext baselineContext(8, 8);
    SimKernelContext coalescedContext(8, 8);
    SimKernelContext summaryContext(8, 8);
    SimKernelContext reducedContext(8, 8);
    SimKernelContext reducedWithStoreContext(8, 8);
    SimKernelContext proposalHandoffContext(8, 8);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, baselineContext);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, coalescedContext);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, summaryContext);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, reducedContext);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, reducedWithStoreContext);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, proposalHandoffContext);

    ok = expect_true(baselineContext.statsEnabled, "stats enabled") && ok;
    replay_baseline(events, rowOffsets, rowCount, baselineContext);
    mergeSimCudaInitialRowEventRuns(events, rowOffsets, rowCount, coalescedContext);
    std::vector<SimScanCudaInitialRunSummary> summaries;
    summarizeSimCudaInitialRowEventRuns(events, rowOffsets, rowCount, summaries);
    mergeSimCudaInitialRunSummaries(summaries, static_cast<uint64_t>(events.size()), summaryContext);
    std::vector<SimScanCudaCandidateState> reducedStates;
    int reducedRunningMin = 0;
    reduceSimCudaInitialRunSummariesToCandidateStates(summaries, reducedStates, reducedRunningMin);
    applySimCudaReducedCandidates(reducedStates, reducedRunningMin, reducedContext);

    std::vector<SimScanCudaCandidateState> allReducedStates;
    reduceSimCudaInitialRunSummariesToAllCandidateStates(summaries, NULL, allReducedStates);
    std::vector<SimScanCudaCandidateState> expectedAllReducedStates(4);
    expectedAllReducedStates[0] = SimScanCudaCandidateState{17, 1, 1, 3, 4, 1, 3, 2, 4};
    expectedAllReducedStates[1] = SimScanCudaCandidateState{13, 1, 2, 1, 5, 1, 1, 4, 6};
    expectedAllReducedStates[2] = SimScanCudaCandidateState{8, 2, 1, 2, 1, 2, 2, 1, 4};
    expectedAllReducedStates[3] = SimScanCudaCandidateState{16, 3, 3, 3, 3, 3, 3, 3, 3};

    std::vector<uint64_t> affectedStartCoords;
    affectedStartCoords.push_back(packSimCoord(1, 1));
    affectedStartCoords.push_back(packSimCoord(3, 3));
    std::vector<SimScanCudaCandidateState> filteredReducedStates;
    reduceSimCudaInitialRunSummariesToAllCandidateStates(summaries, &affectedStartCoords, filteredReducedStates);
    std::vector<SimScanCudaCandidateState> expectedFilteredReducedStates(2);
    expectedFilteredReducedStates[0] = expectedAllReducedStates[0];
    expectedFilteredReducedStates[1] = expectedAllReducedStates[3];

    SimCudaPersistentSafeStoreHandle persistentSafeStoreHandle;
    applySimCudaInitialReduceResults(reducedStates,
                                     reducedRunningMin,
                                     allReducedStates,
                                     persistentSafeStoreHandle,
                                     static_cast<uint64_t>(events.size()),
                                     reducedWithStoreContext,
                                     false,
                                     false);
    applySimCudaInitialReduceResults(reducedStates,
                                     reducedRunningMin,
                                     allReducedStates,
                                     persistentSafeStoreHandle,
                                     static_cast<uint64_t>(events.size()),
                                     proposalHandoffContext,
                                     false,
                                     true);

    ok = expect_candidates_equal(coalescedContext, baselineContext, "coalesced merge") && ok;
    ok = expect_candidates_equal(summaryContext, baselineContext, "summary merge") && ok;
    ok = expect_candidates_equal(reducedContext, baselineContext, "reduced summary states") && ok;
    ok = expect_candidate_states_equal(allReducedStates,
                                       expectedAllReducedStates,
                                       "all candidate states reduced from summaries") && ok;
    ok = expect_candidate_states_equal(filteredReducedStates,
                                       expectedFilteredReducedStates,
                                       "filtered candidate states reduced from summaries") && ok;
    ok = expect_equal_long(coalescedContext.runningMin, baselineContext.runningMin, "runningMin") && ok;
    ok = expect_equal_long(summaryContext.runningMin, baselineContext.runningMin, "summary runningMin") && ok;
    ok = expect_equal_long(reducedContext.runningMin, baselineContext.runningMin, "reduced runningMin") && ok;
    ok = expect_candidates_equal(reducedWithStoreContext, baselineContext, "reduced handoff candidates") && ok;
    ok = expect_equal_long(reducedWithStoreContext.runningMin, baselineContext.runningMin, "reduced handoff runningMin") && ok;
    ok = expect_candidates_equal(proposalHandoffContext, baselineContext, "proposal handoff candidates") && ok;
    ok = expect_equal_long(proposalHandoffContext.runningMin, baselineContext.runningMin, "proposal handoff runningMin") && ok;
    ok = expect_equal_long(coalescedContext.stats.eventsSeen, baselineContext.stats.eventsSeen, "eventsSeen") && ok;
    ok = expect_equal_long(summaryContext.stats.eventsSeen, baselineContext.stats.eventsSeen, "summary eventsSeen") && ok;
    ok = expect_equal_long(reducedWithStoreContext.stats.eventsSeen, baselineContext.stats.eventsSeen, "reduced handoff eventsSeen") && ok;
    ok = expect_equal_long(proposalHandoffContext.stats.eventsSeen, baselineContext.stats.eventsSeen, "proposal handoff eventsSeen") && ok;
    ok = expect_equal_size(reducedStates.size(),
                           static_cast<size_t>(baselineContext.candidateCount),
                           "reduced state count") && ok;
    ok = expect_store_states_equal(reducedWithStoreContext.safeCandidateStateStore,
                                   expectedAllReducedStates,
                                   "reduced handoff safe store") && ok;
    ok = expect_true(proposalHandoffContext.proposalCandidateLoop,
                     "proposal handoff proposal loop enabled") && ok;
    ok = expect_true(!proposalHandoffContext.safeCandidateStateStore.valid,
                     "proposal handoff safe store skipped") && ok;
    ok = expect_true(!proposalHandoffContext.gpuSafeCandidateStateStore.valid,
                     "proposal handoff gpu safe store skipped") && ok;
    ok = expect_true(coalescedContext.stats.addnodeCalls < baselineContext.stats.addnodeCalls,
                     "coalesced addnodeCalls reduced") && ok;
    ok = expect_true(summaryContext.stats.addnodeCalls < baselineContext.stats.addnodeCalls,
                     "summary addnodeCalls reduced") && ok;
    ok = expect_true(simScanCudaInitialRunStartsAt(events, rowOffsets[1], rowOffsets[1]),
                     "row1 first event starts run") && ok;
    ok = expect_true(!simScanCudaInitialRunStartsAt(events, rowOffsets[1], rowOffsets[1] + 1),
                     "row1 second event stays in run") && ok;
    ok = expect_true(simScanCudaInitialRunStartsAt(events, rowOffsets[1], rowOffsets[1] + 3),
                     "row1 second run starts at boundary") && ok;
    ok = expect_true(simScanCudaInitialRunStartsAt(events, rowOffsets[2], rowOffsets[2]),
                     "row2 first event starts run") && ok;
    ok = expect_true(simScanCudaInitialRunStartsAt(events, rowOffsets[2], rowOffsets[2] + 1),
                     "row2 second event starts new run") && ok;
    ok = expect_true(!simScanCudaInitialRunStartsAt(events, rowOffsets[2], rowOffsets[2] + 2),
                     "row2 third event stays in run") && ok;
    ok = expect_equal_long(coalescedContext.stats.addnodeCalls, 7, "coalesced run count") && ok;
    ok = expect_equal_long(summaryContext.stats.addnodeCalls, 7, "summary run count") && ok;
    ok = expect_equal_long(baselineContext.stats.addnodeCalls, 12, "baseline event count") && ok;
    ok = expect_equal_size(summaries.size(), 7u, "summary count") && ok;
    SimScanCudaInitialRunSummary helperSummary;
    initSimCudaInitialRunSummary(events[3], helperSummary);
    updateSimCudaInitialRunSummary(events[4], helperSummary);
    updateSimCudaInitialRunSummary(events[5], helperSummary);
    ok = expect_equal_long(static_cast<long>(helperSummary.score), 13, "helper max score") && ok;
    ok = expect_equal_long(static_cast<long>(helperSummary.endI), 1, "helper endI") && ok;
    ok = expect_equal_long(static_cast<long>(helperSummary.minEndJ), 4, "helper minEndJ") && ok;
    ok = expect_equal_long(static_cast<long>(helperSummary.maxEndJ), 6, "helper maxEndJ") && ok;
    ok = expect_equal_long(static_cast<long>(helperSummary.scoreEndJ), 5, "helper first max endJ") && ok;
    ok = expect_equal_long(static_cast<long>(summaries[1].score), 13, "summary max score") && ok;
    ok = expect_equal_long(static_cast<long>(unpackSimCoordI(summaries[1].startCoord)), 1, "summary startI") && ok;
    ok = expect_equal_long(static_cast<long>(unpackSimCoordJ(summaries[1].startCoord)), 2, "summary startJ") && ok;
    ok = expect_equal_long(static_cast<long>(summaries[1].endI), 1, "summary endI") && ok;
    ok = expect_equal_long(static_cast<long>(summaries[1].minEndJ), 4, "summary minEndJ") && ok;
    ok = expect_equal_long(static_cast<long>(summaries[1].maxEndJ), 6, "summary maxEndJ") && ok;
    ok = expect_equal_long(static_cast<long>(summaries[1].scoreEndJ), 5, "summary first max endJ") && ok;
    SimScanCudaCandidateState helperCandidate{999, 99, 88, 77, 66, 55, 44, 33, 22};
    initSimScanCudaCandidateStateFromInitialRunSummary(summaries[1], helperCandidate);
    ok = expect_equal_long(static_cast<long>(helperCandidate.score), 13, "candidate helper init score") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.startI), 1, "candidate helper init startI") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.startJ), 2, "candidate helper init startJ") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.endI), 1, "candidate helper init endI") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.endJ), 5, "candidate helper init endJ") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.top), 1, "candidate helper init top") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.bot), 1, "candidate helper init bot") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.left), 4, "candidate helper init left") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.right), 6, "candidate helper init right") && ok;
    SimScanCudaInitialRunSummary lowerScoreSameKeySummary{11, packSimCoord(1, 2), 3, 1, 9, 9};
    updateSimScanCudaCandidateStateFromInitialRunSummary(lowerScoreSameKeySummary, helperCandidate);
    ok = expect_equal_long(static_cast<long>(helperCandidate.score), 13, "candidate helper lower score keeps score") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.endI), 1, "candidate helper lower score keeps endI") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.endJ), 5, "candidate helper lower score keeps endJ") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.top), 1, "candidate helper lower score top") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.bot), 3, "candidate helper lower score bot") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.left), 1, "candidate helper lower score left") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.right), 9, "candidate helper lower score right") && ok;
    SimScanCudaInitialRunSummary equalScoreSameKeySummary{13, packSimCoord(1, 2), 5, 0, 10, 10};
    updateSimScanCudaCandidateStateFromInitialRunSummary(equalScoreSameKeySummary, helperCandidate);
    ok = expect_equal_long(static_cast<long>(helperCandidate.score), 13, "candidate helper equal score keeps score") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.endI), 1, "candidate helper equal score keeps endI") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.endJ), 5, "candidate helper equal score keeps endJ") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.top), 1, "candidate helper equal score top") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.bot), 5, "candidate helper equal score bot") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.left), 0, "candidate helper equal score left") && ok;
    ok = expect_equal_long(static_cast<long>(helperCandidate.right), 10, "candidate helper equal score right") && ok;

    std::vector<SimScanCudaInitialRunSummary> unsafeSkipSummaries;
    unsafeSkipSummaries.push_back(SimScanCudaInitialRunSummary{100, packSimCoord(1, 1), 5, 10, 10, 10});
    unsafeSkipSummaries.push_back(SimScanCudaInitialRunSummary{110, packSimCoord(2, 2), 5, 20, 20, 20});
    unsafeSkipSummaries.push_back(SimScanCudaInitialRunSummary{90, packSimCoord(1, 1), 6, 2, 12, 12});
    SimKernelContext safeSummaryContext(32, 32);
    SimKernelContext unsafeFloorContext(32, 32);
    SimKernelContext safeReducedContext(32, 32);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, safeSummaryContext);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, unsafeFloorContext);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, safeReducedContext);
    mergeSimCudaInitialRunSummaries(unsafeSkipSummaries, static_cast<uint64_t>(unsafeSkipSummaries.size()), safeSummaryContext);
    std::vector<SimScanCudaCandidateState> unsafeSkipReducedStates;
    int unsafeSkipReducedRunningMin = 0;
    reduceSimCudaInitialRunSummariesToCandidateStates(unsafeSkipSummaries,
                                                      unsafeSkipReducedStates,
                                                      unsafeSkipReducedRunningMin);
    applySimCudaReducedCandidates(unsafeSkipReducedStates, unsafeSkipReducedRunningMin, safeReducedContext);
    reduce_summaries_with_live_floor_skip_unsafe(unsafeSkipSummaries, unsafeFloorContext);
    ok = expect_candidates_equal(safeReducedContext, safeSummaryContext, "safe reduced equals summary merge") && ok;
    ok = expect_equal_long(safeReducedContext.runningMin, safeSummaryContext.runningMin, "safe reduced floor") && ok;
    ok = expect_true(!candidates_equal(unsafeFloorContext,
                                       safeSummaryContext),
                     "unsafe floor skip changes candidates") && ok;

    std::vector<SimScanCudaInitialRunSummary> chunkSkipSummaries;
    for (int offset = 0; offset < 50; ++offset)
    {
        chunkSkipSummaries.push_back(SimScanCudaInitialRunSummary{
            static_cast<int>(100 + offset),
            packSimCoord(10, static_cast<uint32_t>(offset + 1)),
            1,
            static_cast<uint32_t>(1000 + offset),
            static_cast<uint32_t>(1000 + offset),
            static_cast<uint32_t>(1000 + offset)});
    }
    chunkSkipSummaries.push_back(SimScanCudaInitialRunSummary{10, packSimCoord(10, 1), 1, 1000, 1000, 1000});
    chunkSkipSummaries.push_back(SimScanCudaInitialRunSummary{20, packSimCoord(10, 2), 1, 1001, 1001, 1001});
    std::vector<SimScanCudaCandidateState> chunkSkipReducedStates;
    int chunkSkipRunningMin = 0;
    reduceSimCudaInitialRunSummariesToCandidateStates(chunkSkipSummaries,
                                                      chunkSkipReducedStates,
                                                      chunkSkipRunningMin);
    std::vector<SimScanCudaCandidateState> chunkPrunedReducedStates;
    int chunkPrunedRunningMin = 0;
    SimScanCudaInitialReduceReplayStats chunkPrunedStats;
    reduceSimCudaInitialRunSummariesToCandidateStatesChunkPruned(chunkSkipSummaries,
                                                                 50,
                                                                 chunkPrunedReducedStates,
                                                                 chunkPrunedRunningMin,
                                                                 &chunkPrunedStats);
    ok = expect_candidate_states_equal(chunkPrunedReducedStates,
                                       chunkSkipReducedStates,
                                       "chunk-pruned reduced equals exact reduce") && ok;
    ok = expect_equal_long(chunkPrunedRunningMin,
                           chunkSkipRunningMin,
                           "chunk-pruned runningMin") && ok;
    ok = expect_equal_long(static_cast<long>(chunkPrunedStats.chunkCount), 2, "chunk-pruned chunk count") && ok;
    ok = expect_equal_long(static_cast<long>(chunkPrunedStats.chunkReplayedCount), 1, "chunk-pruned replayed chunks") && ok;
    ok = expect_equal_long(static_cast<long>(chunkPrunedStats.chunkSkippedCount), 1, "chunk-pruned skipped chunks") && ok;
    ok = expect_equal_long(static_cast<long>(chunkPrunedStats.summaryReplayCount), 50, "chunk-pruned replayed summaries") && ok;

    std::vector<SimScanCudaInitialRunSummary> reinsertionSummaries;
    reinsertionSummaries.push_back(SimScanCudaInitialRunSummary{10, packSimCoord(1, 1), 1, 100, 100, 100});
    for (int offset = 0; offset < 49; ++offset)
    {
        reinsertionSummaries.push_back(SimScanCudaInitialRunSummary{
            static_cast<int>(100 + offset),
            packSimCoord(2, static_cast<uint32_t>(offset + 1)),
            1,
            static_cast<uint32_t>(200 + offset),
            static_cast<uint32_t>(200 + offset),
            static_cast<uint32_t>(200 + offset)});
    }
    reinsertionSummaries.push_back(SimScanCudaInitialRunSummary{11, packSimCoord(3, 1), 1, 400, 400, 400});
    reinsertionSummaries.push_back(SimScanCudaInitialRunSummary{50, packSimCoord(1, 1), 2, 300, 300, 300});

    SimKernelContext reinsertionContext(512, 512);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, reinsertionContext);
    mergeSimCudaInitialRunSummaries(reinsertionSummaries,
                                    static_cast<uint64_t>(reinsertionSummaries.size()),
                                    reinsertionContext);
    std::vector<SimScanCudaCandidateState> reinsertionAllStates;
    reduceSimCudaInitialRunSummariesToAllCandidateStates(reinsertionSummaries,
                                                         NULL,
                                                         reinsertionAllStates);
    const SimCandidate *reinsertionCandidate = find_candidate_by_start(reinsertionContext, 1, 1);
    const SimScanCudaCandidateState *reinsertionAllState =
        find_candidate_state_by_start(reinsertionAllStates, packSimCoord(1, 1));
    ok = expect_true(reinsertionCandidate != NULL, "reinsertion candidate present") && ok;
    ok = expect_true(reinsertionAllState != NULL, "reinsertion all-state present") && ok;
    if (reinsertionCandidate != NULL && reinsertionAllState != NULL)
    {
        ok = expect_equal_long(reinsertionCandidate->TOP, 2, "reinsertion candidate top resets after eviction") && ok;
        ok = expect_equal_long(reinsertionCandidate->BOT, 2, "reinsertion candidate bot resets after eviction") && ok;
        ok = expect_equal_long(reinsertionCandidate->LEFT, 300, "reinsertion candidate left resets after eviction") && ok;
        ok = expect_equal_long(reinsertionCandidate->RIGHT, 300, "reinsertion candidate right resets after eviction") && ok;
        ok = expect_equal_long(static_cast<long>(reinsertionAllState->top), 1, "reinsertion all-state keeps historical top") && ok;
        ok = expect_equal_long(static_cast<long>(reinsertionAllState->bot), 2, "reinsertion all-state keeps historical bot") && ok;
        ok = expect_equal_long(static_cast<long>(reinsertionAllState->left), 100, "reinsertion all-state keeps historical left") && ok;
        ok = expect_equal_long(static_cast<long>(reinsertionAllState->right), 300, "reinsertion all-state keeps historical right") && ok;
    }

    std::vector<SimScanCudaInitialRunSummary> telemetrySummaries;
    for (int startIndex = 0; startIndex < 256; ++startIndex)
    {
        const uint32_t startI = static_cast<uint32_t>(1 + startIndex / 32);
        const uint32_t startJ = static_cast<uint32_t>(1 + startIndex % 32);
        for (int pass = 0; pass < 16; ++pass)
        {
            const uint32_t endI = static_cast<uint32_t>(4 + pass);
            const uint32_t minEndJ = static_cast<uint32_t>(100 + startIndex * 8 + pass * 2);
            telemetrySummaries.push_back(SimScanCudaInitialRunSummary{
                200 + pass,
                packSimCoord(startI, startJ),
                endI,
                minEndJ,
                static_cast<uint32_t>(minEndJ + 1),
                minEndJ});
        }
    }

    uint64_t summaryTotalBefore = 0;
    uint64_t summaryApplyBefore = 0;
    uint64_t summarySafeStoreUpdateBefore = 0;
    uint64_t summarySafeStorePruneBefore = 0;
    uint64_t summarySafeStoreUploadBefore = 0;
    get_initial_cpu_merge_breakdown(summaryTotalBefore,
                                    summaryApplyBefore,
                                    summarySafeStoreUpdateBefore,
                                    summarySafeStorePruneBefore,
                                    summarySafeStoreUploadBefore);

    SimKernelContext summaryTelemetryContext(1024, 4096);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, summaryTelemetryContext);
    applySimCudaInitialRunSummariesToContext(telemetrySummaries,
                                             static_cast<uint64_t>(telemetrySummaries.size()),
                                             summaryTelemetryContext,
                                             true);

    uint64_t summaryTotalAfter = 0;
    uint64_t summaryApplyAfter = 0;
    uint64_t summarySafeStoreUpdateAfter = 0;
    uint64_t summarySafeStorePruneAfter = 0;
    uint64_t summarySafeStoreUploadAfter = 0;
    get_initial_cpu_merge_breakdown(summaryTotalAfter,
                                    summaryApplyAfter,
                                    summarySafeStoreUpdateAfter,
                                    summarySafeStorePruneAfter,
                                    summarySafeStoreUploadAfter);

    const uint64_t summaryTotalDelta = summaryTotalAfter - summaryTotalBefore;
    const uint64_t summaryApplyDelta = summaryApplyAfter - summaryApplyBefore;
    const uint64_t summarySafeStoreUpdateDelta = summarySafeStoreUpdateAfter - summarySafeStoreUpdateBefore;
    const uint64_t summarySafeStorePruneDelta = summarySafeStorePruneAfter - summarySafeStorePruneBefore;
    const uint64_t summarySafeStoreUploadDelta = summarySafeStoreUploadAfter - summarySafeStoreUploadBefore;
    ok = expect_true(summaryTotalDelta > 0, "summary telemetry total cpu merge recorded") && ok;
    ok = expect_true(summaryApplyDelta > 0, "summary telemetry context apply recorded") && ok;
    ok = expect_true(summarySafeStoreUpdateDelta > 0, "summary telemetry safe-store update recorded") && ok;
    ok = expect_true(summarySafeStorePruneDelta > 0, "summary telemetry safe-store prune recorded") && ok;
    ok = expect_equal_long(static_cast<long>(summarySafeStoreUploadDelta), 0, "summary telemetry upload remains zero") && ok;
    ok = expect_true(summaryTotalDelta >=
                         summaryApplyDelta + summarySafeStoreUpdateDelta + summarySafeStorePruneDelta +
                             summarySafeStoreUploadDelta,
                     "summary telemetry sub-stages fit inside total cpu merge") &&
         ok;

    std::vector<SimScanCudaCandidateState> telemetryReducedStates;
    std::vector<SimScanCudaCandidateState> telemetryAllStates;
    for (int stateIndex = 0; stateIndex < K; ++stateIndex)
    {
        const int startI = 10 + stateIndex / 24;
        const int startJ = 10 + stateIndex % 24;
        telemetryReducedStates.push_back(SimScanCudaCandidateState{
            400 + stateIndex,
            startI,
            startJ,
            20 + stateIndex % 11,
            200 + stateIndex,
            startI,
            20 + stateIndex % 11,
            190 + stateIndex,
            210 + stateIndex});
        telemetryAllStates.push_back(telemetryReducedStates.back());
    }
    for (int stateIndex = 0; stateIndex < 4096; ++stateIndex)
    {
        const int startI = 1 + (stateIndex / 64) % 48;
        const int startJ = 1 + stateIndex % 64;
        telemetryAllStates.push_back(SimScanCudaCandidateState{
            120 + stateIndex % 220,
            startI,
            startJ,
            5 + stateIndex % 17,
            500 + stateIndex,
            startI,
            5 + stateIndex % 17,
            480 + stateIndex,
            520 + stateIndex});
    }

    uint64_t reduceTotalBefore = 0;
    uint64_t reduceApplyBefore = 0;
    uint64_t reduceSafeStoreUpdateBefore = 0;
    uint64_t reduceSafeStorePruneBefore = 0;
    uint64_t reduceSafeStoreUploadBefore = 0;
    get_initial_cpu_merge_breakdown(reduceTotalBefore,
                                    reduceApplyBefore,
                                    reduceSafeStoreUpdateBefore,
                                    reduceSafeStorePruneBefore,
                                    reduceSafeStoreUploadBefore);

    SimCudaPersistentSafeStoreHandle telemetryPersistentHandle;
    SimKernelContext reduceTelemetryContext(2048, 4096);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, reduceTelemetryContext);
    applySimCudaInitialReduceResults(telemetryReducedStates,
                                     220,
                                     telemetryAllStates,
                                     telemetryPersistentHandle,
                                     static_cast<uint64_t>(telemetrySummaries.size()),
                                     reduceTelemetryContext,
                                     true,
                                     false);

    uint64_t reduceTotalAfter = 0;
    uint64_t reduceApplyAfter = 0;
    uint64_t reduceSafeStoreUpdateAfter = 0;
    uint64_t reduceSafeStorePruneAfter = 0;
    uint64_t reduceSafeStoreUploadAfter = 0;
    get_initial_cpu_merge_breakdown(reduceTotalAfter,
                                    reduceApplyAfter,
                                    reduceSafeStoreUpdateAfter,
                                    reduceSafeStorePruneAfter,
                                    reduceSafeStoreUploadAfter);

    const uint64_t reduceTotalDelta = reduceTotalAfter - reduceTotalBefore;
    const uint64_t reduceApplyDelta = reduceApplyAfter - reduceApplyBefore;
    const uint64_t reduceSafeStoreUpdateDelta = reduceSafeStoreUpdateAfter - reduceSafeStoreUpdateBefore;
    const uint64_t reduceSafeStorePruneDelta = reduceSafeStorePruneAfter - reduceSafeStorePruneBefore;
    const uint64_t reduceSafeStoreUploadDelta = reduceSafeStoreUploadAfter - reduceSafeStoreUploadBefore;
    ok = expect_true(reduceTotalDelta > 0, "reduce telemetry total cpu merge recorded") && ok;
    ok = expect_true(reduceApplyDelta > 0, "reduce telemetry context apply recorded") && ok;
    ok = expect_true(reduceSafeStoreUpdateDelta > 0, "reduce telemetry safe-store update recorded") && ok;
    ok = expect_true(reduceSafeStorePruneDelta > 0, "reduce telemetry safe-store prune recorded") && ok;
    ok = expect_equal_long(static_cast<long>(reduceSafeStoreUploadDelta), 0, "reduce telemetry upload remains zero") && ok;
    ok = expect_true(reduceTotalDelta >=
                         reduceApplyDelta + reduceSafeStoreUpdateDelta + reduceSafeStorePruneDelta +
                             reduceSafeStoreUploadDelta,
                     "reduce telemetry sub-stages fit inside total cpu merge") &&
         ok;

    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
