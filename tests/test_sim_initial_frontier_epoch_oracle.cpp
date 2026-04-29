#include <algorithm>
#include <cerrno>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <sys/stat.h>
#include <sys/types.h>
#include <unordered_map>
#include <vector>

#include "../sim.h"

namespace
{

static const char *kArtifactDir = ".tmp/gpu_candidate_frontier_epoch_oracle_2026-04-29";

struct FrontierEpoch
{
    uint64_t epochId;
    uint64_t startCoord;
    int slot;
    size_t firstSummaryOrdinal;
    size_t lastSummaryOrdinal;
    bool live;
    SimScanCudaCandidateState state;
};

struct FrontierTraceEvent
{
    size_t summaryOrdinal;
    uint64_t startCoord;
    int slot;
    std::string operation;
    bool hasEvictedStart;
    uint64_t evictedStartCoord;
    uint64_t evictedEpochId;
    uint64_t epochId;
    int floorBefore;
    int floorAfter;
    bool hasBeforeState;
    SimScanCudaCandidateState beforeState;
    SimScanCudaCandidateState afterState;
};

struct FrontierOracleResult
{
    std::vector<FrontierEpoch> epochs;
    std::vector<FrontierTraceEvent> trace;
    std::vector<SimScanCudaCandidateState> frontierStates;
    int runningMin;
    bool chunkable;
    size_t liveEpochCount;
};

struct TestCase
{
    std::string name;
    std::vector<SimScanCudaInitialRunSummary> summaries;
    uint64_t explainStartCoord;
    bool expectsReinsertBoundsSplit;
};

struct CaseReport
{
    std::string name;
    size_t summaryCount;
    size_t traceCount;
    size_t epochCount;
    size_t liveEpochCount;
    size_t frontierCount;
    size_t safeStoreCount;
    int runningMin;
    bool exact;
    bool chunkable;
    bool sawInsert;
    bool sawHit;
    bool sawEvictInsert;
    bool sawReinsert;
    bool sawLowerScoreFullSetMiss;
    bool sawSlotTieEviction;
    bool reinsertBoundsSplit;
};

static SimScanCudaInitialRunSummary make_summary(int score,
                                                uint32_t startI,
                                                uint32_t startJ,
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

static SimScanCudaInitialRunSummary make_summary(int score,
                                                uint32_t startI,
                                                uint32_t startJ,
                                                uint32_t endI,
                                                uint32_t endJ)
{
    return make_summary(score, startI, startJ, endI, endJ, endJ, endJ);
}

static std::string json_escape(const std::string &value)
{
    std::ostringstream out;
    for (size_t i = 0; i < value.size(); ++i)
    {
        const char ch = value[i];
        switch (ch)
        {
            case '\\': out << "\\\\"; break;
            case '"': out << "\\\""; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default: out << ch; break;
        }
    }
    return out.str();
}

static std::string coord_json(uint64_t startCoord)
{
    std::ostringstream out;
    out << "{\"startI\":" << unpackSimCoordI(startCoord)
        << ",\"startJ\":" << unpackSimCoordJ(startCoord)
        << ",\"packed\":" << startCoord << "}";
    return out.str();
}

static std::string state_json(const SimScanCudaCandidateState &state)
{
    std::ostringstream out;
    out << "{\"score\":" << state.score
        << ",\"startI\":" << state.startI
        << ",\"startJ\":" << state.startJ
        << ",\"endI\":" << state.endI
        << ",\"endJ\":" << state.endJ
        << ",\"top\":" << state.top
        << ",\"bot\":" << state.bot
        << ",\"left\":" << state.left
        << ",\"right\":" << state.right << "}";
    return out.str();
}

static bool ensure_directory(const char *path)
{
    if (mkdir(path, 0755) == 0)
    {
        return true;
    }
    if (errno == EEXIST)
    {
        return true;
    }
    std::cerr << "mkdir failed for " << path << ": " << std::strerror(errno) << "\n";
    return false;
}

static std::vector<SimScanCudaCandidateState> sorted_candidate_states(
    const std::vector<SimScanCudaCandidateState> &states)
{
    std::vector<SimScanCudaCandidateState> sorted = states;
    std::sort(sorted.begin(), sorted.end(), [](const SimScanCudaCandidateState &lhs,
                                               const SimScanCudaCandidateState &rhs) {
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

static bool states_equal(const SimScanCudaCandidateState &lhs,
                         const SimScanCudaCandidateState &rhs)
{
    return std::memcmp(&lhs, &rhs, sizeof(SimScanCudaCandidateState)) == 0;
}

static void add_mismatch(std::vector<std::string> &mismatches,
                         const std::string &caseName,
                         const std::string &kind,
                         const std::string &detail)
{
    std::ostringstream out;
    out << "{\"case\":\"" << json_escape(caseName)
        << "\",\"kind\":\"" << json_escape(kind)
        << "\",\"detail\":\"" << json_escape(detail) << "\"}";
    mismatches.push_back(out.str());
}

static bool expect_state_vectors_equal(const std::vector<SimScanCudaCandidateState> &actual,
                                       const std::vector<SimScanCudaCandidateState> &expected,
                                       const std::string &caseName,
                                       const std::string &label,
                                       std::vector<std::string> &mismatches)
{
    const std::vector<SimScanCudaCandidateState> lhs = sorted_candidate_states(actual);
    const std::vector<SimScanCudaCandidateState> rhs = sorted_candidate_states(expected);
    if (lhs.size() != rhs.size())
    {
        std::ostringstream detail;
        detail << label << " size expected " << rhs.size() << ", got " << lhs.size();
        add_mismatch(mismatches, caseName, label, detail.str());
        return false;
    }
    for (size_t i = 0; i < lhs.size(); ++i)
    {
        if (!states_equal(lhs[i], rhs[i]))
        {
            std::ostringstream detail;
            detail << label << " state[" << i << "] expected " << state_json(rhs[i])
                   << ", got " << state_json(lhs[i]);
            add_mismatch(mismatches, caseName, label, detail.str());
            return false;
        }
    }
    return true;
}

static const SimScanCudaCandidateState *find_state_by_start(
    const std::vector<SimScanCudaCandidateState> &states,
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

static SimScanCudaCandidateState candidate_state_from_context_slot(const SimKernelContext &context,
                                                                   int slot)
{
    return makeSimScanCudaCandidateState(context.candidates[static_cast<size_t>(slot)]);
}

static void reduce_epoch_chunk_states(const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                      const std::vector<FrontierTraceEvent> &trace,
                                      size_t chunkSize,
                                      std::map<uint64_t, SimScanCudaCandidateState> &outStates)
{
    outStates.clear();
    if (chunkSize == 0)
    {
        chunkSize = 1;
    }
    for (size_t chunkBase = 0; chunkBase < trace.size(); chunkBase += chunkSize)
    {
        const size_t chunkEnd = std::min(chunkBase + chunkSize, trace.size());
        std::map<uint64_t, SimScanCudaCandidateState> chunkStates;
        for (size_t traceIndex = chunkBase; traceIndex < chunkEnd; ++traceIndex)
        {
            const FrontierTraceEvent &event = trace[traceIndex];
            const SimScanCudaInitialRunSummary &summary = summaries[event.summaryOrdinal];
            std::map<uint64_t, SimScanCudaCandidateState>::iterator found =
                chunkStates.find(event.epochId);
            if (found == chunkStates.end())
            {
                SimScanCudaCandidateState state;
                initSimScanCudaCandidateStateFromInitialRunSummary(summary, state);
                chunkStates[event.epochId] = state;
            }
            else
            {
                updateSimScanCudaCandidateStateFromInitialRunSummary(summary, found->second);
            }
        }

        for (std::map<uint64_t, SimScanCudaCandidateState>::const_iterator it = chunkStates.begin();
             it != chunkStates.end();
             ++it)
        {
            std::map<uint64_t, SimScanCudaCandidateState>::iterator found = outStates.find(it->first);
            if (found == outStates.end())
            {
                outStates[it->first] = it->second;
            }
            else
            {
                mergeSimScanCudaCandidateState(it->second, found->second);
            }
        }
    }
}

static bool verify_chunkability(const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                const FrontierOracleResult &oracle,
                                const std::vector<size_t> &chunkSizes)
{
    std::set<uint64_t> liveEpochIds;
    std::map<uint64_t, SimScanCudaCandidateState> expectedByEpoch;
    for (size_t epochIndex = 0; epochIndex < oracle.epochs.size(); ++epochIndex)
    {
        const FrontierEpoch &epoch = oracle.epochs[epochIndex];
        if (epoch.live)
        {
            liveEpochIds.insert(epoch.epochId);
            expectedByEpoch[epoch.epochId] = epoch.state;
        }
    }

    for (size_t sizeIndex = 0; sizeIndex < chunkSizes.size(); ++sizeIndex)
    {
        std::map<uint64_t, SimScanCudaCandidateState> reducedByEpoch;
        reduce_epoch_chunk_states(summaries, oracle.trace, chunkSizes[sizeIndex], reducedByEpoch);
        for (std::set<uint64_t>::const_iterator it = liveEpochIds.begin();
             it != liveEpochIds.end();
             ++it)
        {
            const std::map<uint64_t, SimScanCudaCandidateState>::const_iterator found =
                reducedByEpoch.find(*it);
            if (found == reducedByEpoch.end())
            {
                return false;
            }
            if (!states_equal(found->second, expectedByEpoch[*it]))
            {
                return false;
            }
        }
    }
    return true;
}

static FrontierOracleResult build_frontier_epoch_oracle(
    const std::vector<SimScanCudaInitialRunSummary> &summaries)
{
    FrontierOracleResult result;
    result.runningMin = 0;
    result.chunkable = false;
    result.liveEpochCount = 0;

    SimKernelContext context(4096, 4096);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);
    clearSimCandidateStartIndex(context.candidateStartIndex);
    context.candidateMinHeap.clear();

    std::vector<uint64_t> liveEpochBySlot(static_cast<size_t>(K), 0);
    std::unordered_map<uint64_t, uint64_t> epochCountByStart;

    for (size_t summaryIndex = 0; summaryIndex < summaries.size(); ++summaryIndex)
    {
        const SimScanCudaInitialRunSummary &summary = summaries[summaryIndex];
        const uint64_t startCoord = summary.startCoord;
        const long startI = static_cast<long>(unpackSimCoordI(startCoord));
        const long startJ = static_cast<long>(unpackSimCoordJ(startCoord));
        const int floorBefore = static_cast<int>(simCurrentCandidateFloor(context));
        const long foundIndex = findSimCandidateIndex(context.candidateStartIndex, startI, startJ);

        FrontierTraceEvent event;
        event.summaryOrdinal = summaryIndex;
        event.startCoord = startCoord;
        event.slot = -1;
        event.operation = "insert";
        event.hasEvictedStart = false;
        event.evictedStartCoord = 0;
        event.evictedEpochId = 0;
        event.epochId = 0;
        event.floorBefore = floorBefore;
        event.floorAfter = floorBefore;
        event.hasBeforeState = false;
        std::memset(&event.beforeState, 0, sizeof(event.beforeState));
        std::memset(&event.afterState, 0, sizeof(event.afterState));

        if (foundIndex >= 0 && foundIndex < context.candidateCount)
        {
            event.operation = "hit";
            event.slot = static_cast<int>(foundIndex);
            event.epochId = liveEpochBySlot[static_cast<size_t>(event.slot)];
            event.hasBeforeState = true;
            event.beforeState = candidate_state_from_context_slot(context, event.slot);

            applySimCudaInitialRunSummary(summary, context, NULL);
            event.afterState = candidate_state_from_context_slot(context, event.slot);

            FrontierEpoch &epoch = result.epochs[static_cast<size_t>(event.epochId - 1)];
            updateSimScanCudaCandidateStateFromInitialRunSummary(summary, epoch.state);
            epoch.lastSummaryOrdinal = summaryIndex;
        }
        else
        {
            const bool fullBefore = context.candidateCount == K;
            int slot = static_cast<int>(context.candidateCount);
            if (fullBefore)
            {
                if (!context.candidateMinHeap.valid)
                {
                    buildSimCandidateMinHeap(context);
                }
                slot = peekMinSimCandidateIndex(context.candidateMinHeap);
                if (slot < 0 || slot >= static_cast<int>(context.candidateCount))
                {
                    slot = 0;
                }
                event.hasEvictedStart = true;
                event.evictedStartCoord =
                    packSimCoord(static_cast<uint32_t>(context.candidates[static_cast<size_t>(slot)].STARI),
                                 static_cast<uint32_t>(context.candidates[static_cast<size_t>(slot)].STARJ));
                event.evictedEpochId = liveEpochBySlot[static_cast<size_t>(slot)];
                event.hasBeforeState = true;
                event.beforeState = candidate_state_from_context_slot(context, slot);
                if (event.evictedEpochId > 0)
                {
                    result.epochs[static_cast<size_t>(event.evictedEpochId - 1)].live = false;
                }
                event.operation =
                    epochCountByStart[startCoord] > 0 ? "reinsert" : "evict_insert";
            }
            else if (epochCountByStart[startCoord] > 0)
            {
                event.operation = "reinsert";
            }

            applySimCudaInitialRunSummary(summary, context, NULL);
            event.slot = slot;
            event.afterState = candidate_state_from_context_slot(context, event.slot);

            FrontierEpoch epoch;
            epoch.epochId = static_cast<uint64_t>(result.epochs.size() + 1);
            epoch.startCoord = startCoord;
            epoch.slot = event.slot;
            epoch.firstSummaryOrdinal = summaryIndex;
            epoch.lastSummaryOrdinal = summaryIndex;
            epoch.live = true;
            initSimScanCudaCandidateStateFromInitialRunSummary(summary, epoch.state);
            result.epochs.push_back(epoch);

            event.epochId = epoch.epochId;
            liveEpochBySlot[static_cast<size_t>(event.slot)] = epoch.epochId;
            ++epochCountByStart[startCoord];
        }

        event.floorAfter = static_cast<int>(simCurrentCandidateFloor(context));
        result.trace.push_back(event);
    }

    refreshSimRunningMin(context);
    result.runningMin = static_cast<int>(context.runningMin);
    for (size_t epochIndex = 0; epochIndex < result.epochs.size(); ++epochIndex)
    {
        const FrontierEpoch &epoch = result.epochs[epochIndex];
        if (epoch.live)
        {
            result.frontierStates.push_back(epoch.state);
            ++result.liveEpochCount;
        }
    }

    std::vector<size_t> chunkSizes;
    chunkSizes.push_back(1);
    chunkSizes.push_back(2);
    chunkSizes.push_back(3);
    chunkSizes.push_back(5);
    chunkSizes.push_back(17);
    chunkSizes.push_back(64);
    result.chunkable = verify_chunkability(summaries, result, chunkSizes);
    return result;
}

static TestCase make_contiguous_same_start_case()
{
    TestCase test;
    test.name = "contiguous_same_start";
    test.explainStartCoord = 0;
    test.expectsReinsertBoundsSplit = false;
    test.summaries.push_back(make_summary(10, 1, 1, 1, 10));
    test.summaries.push_back(make_summary(12, 1, 1, 1, 11, 13, 12));
    test.summaries.push_back(make_summary(12, 1, 1, 2, 8, 14, 13));
    test.summaries.push_back(make_summary(9, 2, 1, 1, 20));
    return test;
}

static TestCase make_repeated_hit_update_case()
{
    TestCase test;
    test.name = "repeated_hit_update";
    test.explainStartCoord = 0;
    test.expectsReinsertBoundsSplit = false;
    test.summaries.push_back(make_summary(20, 5, 5, 1, 50));
    test.summaries.push_back(make_summary(18, 6, 5, 1, 60));
    test.summaries.push_back(make_summary(25, 5, 5, 2, 45, 55, 47));
    test.summaries.push_back(make_summary(24, 5, 5, 4, 40, 58, 52));
    return test;
}

static TestCase make_score_tie_case()
{
    TestCase test;
    test.name = "score_tie";
    test.explainStartCoord = 0;
    test.expectsReinsertBoundsSplit = false;
    test.summaries.push_back(make_summary(30, 7, 7, 1, 70, 72, 71));
    test.summaries.push_back(make_summary(30, 7, 7, 2, 68, 75, 74));
    test.summaries.push_back(make_summary(29, 8, 7, 1, 80));
    return test;
}

static TestCase make_slot_tie_case()
{
    TestCase test;
    test.name = "slot_tie";
    test.explainStartCoord = 0;
    test.expectsReinsertBoundsSplit = false;
    for (int i = 0; i < K; ++i)
    {
        test.summaries.push_back(make_summary(100,
                                              10,
                                              static_cast<uint32_t>(i + 1),
                                              1,
                                              static_cast<uint32_t>(1000 + i)));
    }
    test.summaries.push_back(make_summary(100, 20, 1, 1, 2000));
    return test;
}

static TestCase make_lower_score_full_set_miss_case()
{
    TestCase test;
    test.name = "lower_score_full_set_miss";
    test.explainStartCoord = 0;
    test.expectsReinsertBoundsSplit = false;
    for (int i = 0; i < K; ++i)
    {
        test.summaries.push_back(make_summary(200 + i,
                                              30,
                                              static_cast<uint32_t>(i + 1),
                                              1,
                                              static_cast<uint32_t>(3000 + i)));
    }
    test.summaries.push_back(make_summary(10, 40, 1, 1, 4000));
    return test;
}

static TestCase make_production_k_revisit_after_eviction_case()
{
    TestCase test;
    test.name = "production_k_revisit_after_eviction";
    test.explainStartCoord = packSimCoord(1, 1);
    test.expectsReinsertBoundsSplit = true;
    test.summaries.push_back(make_summary(10, 1, 1, 1, 100));
    for (int offset = 0; offset < K - 1; ++offset)
    {
        test.summaries.push_back(make_summary(100 + offset,
                                              2,
                                              static_cast<uint32_t>(offset + 1),
                                              1,
                                              static_cast<uint32_t>(200 + offset)));
    }
    test.summaries.push_back(make_summary(11, 3, 1, 1, 400));
    test.summaries.push_back(make_summary(50, 1, 1, 2, 300));
    return test;
}

static TestCase make_evicted_start_later_reinsert_case()
{
    TestCase test;
    test.name = "evicted_start_later_reinsert";
    test.explainStartCoord = packSimCoord(9, 9);
    test.expectsReinsertBoundsSplit = true;
    test.summaries.push_back(make_summary(40, 9, 9, 1, 100));
    test.summaries.push_back(make_summary(30, 9, 9, 2, 90, 110, 105));
    for (int offset = 0; offset < K - 1; ++offset)
    {
        test.summaries.push_back(make_summary(100 + offset,
                                              11,
                                              static_cast<uint32_t>(offset + 1),
                                              1,
                                              static_cast<uint32_t>(500 + offset)));
    }
    test.summaries.push_back(make_summary(41, 12, 1, 1, 700));
    test.summaries.push_back(make_summary(42, 9, 9, 3, 300));
    return test;
}

static bool analyze_case(const TestCase &test,
                         CaseReport &report,
                         std::vector<std::string> &mismatches)
{
    FrontierOracleResult oracle = build_frontier_epoch_oracle(test.summaries);

    SimKernelContext truthContext(4096, 4096);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, truthContext);
    mergeSimCudaInitialRunSummaries(test.summaries,
                                    static_cast<uint64_t>(test.summaries.size()),
                                    truthContext);
    std::vector<SimScanCudaCandidateState> truthFrontierStates;
    collectSimContextCandidateStates(truthContext, truthFrontierStates);

    std::vector<SimScanCudaCandidateState> allStates;
    reduceSimCudaInitialRunSummariesToAllCandidateStates(test.summaries, NULL, allStates);

    SimKernelContext materializedStoreContext(4096, 4096);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, materializedStoreContext);
    mergeSimCudaInitialRunSummariesIntoSafeStore(test.summaries, materializedStoreContext);

    SimCudaPersistentSafeStoreHandle oraclePersistentHandle;
    SimKernelContext oracleHandoffContext(4096, 4096);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, oracleHandoffContext);
    applySimCudaInitialReduceResults(oracle.frontierStates,
                                     oracle.runningMin,
                                     allStates,
                                     oraclePersistentHandle,
                                     static_cast<uint64_t>(test.summaries.size()),
                                     oracleHandoffContext,
                                     false,
                                     false);

    SimCudaPersistentSafeStoreHandle truthPersistentHandle;
    SimKernelContext truthHandoffContext(4096, 4096);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, truthHandoffContext);
    applySimCudaInitialReduceResults(truthFrontierStates,
                                     static_cast<int>(truthContext.runningMin),
                                     allStates,
                                     truthPersistentHandle,
                                     static_cast<uint64_t>(test.summaries.size()),
                                     truthHandoffContext,
                                     false,
                                     false);

    bool ok = true;
    ok = expect_state_vectors_equal(oracle.frontierStates,
                                    truthFrontierStates,
                                    test.name,
                                    "frontier",
                                    mismatches) && ok;
    if (oracle.runningMin != static_cast<int>(truthContext.runningMin))
    {
        std::ostringstream detail;
        detail << "runningMin expected " << truthContext.runningMin
               << ", got " << oracle.runningMin;
        add_mismatch(mismatches, test.name, "runningMin", detail.str());
        ok = false;
    }
    ok = expect_state_vectors_equal(oracleHandoffContext.safeCandidateStateStore.states,
                                    truthHandoffContext.safeCandidateStateStore.states,
                                    test.name,
                                    "safe_store_pruned",
                                    mismatches) && ok;
    ok = expect_state_vectors_equal(allStates,
                                    materializedStoreContext.safeCandidateStateStore.states,
                                    test.name,
                                    "safe_store_materialized",
                                    mismatches) && ok;
    if (!materializedStoreContext.safeCandidateStateStore.valid)
    {
        add_mismatch(mismatches, test.name, "safe_store_materialized", "materialized store is invalid");
        ok = false;
    }
    if (!oracleHandoffContext.safeCandidateStateStore.valid)
    {
        add_mismatch(mismatches, test.name, "safe_store_materialized", "store is invalid");
        ok = false;
    }
    if (!oracle.chunkable)
    {
        add_mismatch(mismatches, test.name, "chunkability", "epoch-labeled chunk reduce did not match live epochs");
        ok = false;
    }

    report.name = test.name;
    report.summaryCount = test.summaries.size();
    report.traceCount = oracle.trace.size();
    report.epochCount = oracle.epochs.size();
    report.liveEpochCount = oracle.liveEpochCount;
    report.frontierCount = oracle.frontierStates.size();
    report.safeStoreCount = oracleHandoffContext.safeCandidateStateStore.states.size();
    report.runningMin = oracle.runningMin;
    report.exact = ok;
    report.chunkable = oracle.chunkable;
    report.sawInsert = false;
    report.sawHit = false;
    report.sawEvictInsert = false;
    report.sawReinsert = false;
    report.sawLowerScoreFullSetMiss = false;
    report.sawSlotTieEviction = false;
    report.reinsertBoundsSplit = false;

    for (size_t traceIndex = 0; traceIndex < oracle.trace.size(); ++traceIndex)
    {
        const FrontierTraceEvent &event = oracle.trace[traceIndex];
        if (event.operation == "insert") report.sawInsert = true;
        if (event.operation == "hit") report.sawHit = true;
        if (event.operation == "evict_insert") report.sawEvictInsert = true;
        if (event.operation == "reinsert") report.sawReinsert = true;
        if (event.hasEvictedStart && event.afterState.score < event.floorBefore)
        {
            report.sawLowerScoreFullSetMiss = true;
        }
        if (test.name == "slot_tie" &&
            event.hasEvictedStart &&
            event.evictedStartCoord == packSimCoord(10, 1) &&
            event.floorBefore == event.afterState.score)
        {
            report.sawSlotTieEviction = true;
        }
    }

    if (test.expectsReinsertBoundsSplit)
    {
        const SimScanCudaCandidateState *frontierState =
            find_state_by_start(oracle.frontierStates, test.explainStartCoord);
        const SimScanCudaCandidateState *safeStoreState =
            find_state_by_start(oracleHandoffContext.safeCandidateStateStore.states,
                                test.explainStartCoord);
        if (frontierState == NULL || safeStoreState == NULL)
        {
            add_mismatch(mismatches,
                         test.name,
                         "reinsert_bounds_split",
                         "expected frontier and safe-store states for reinserted start");
            ok = false;
        }
        else
        {
            report.reinsertBoundsSplit =
                safeStoreState->top < frontierState->top ||
                safeStoreState->left < frontierState->left ||
                safeStoreState->right > frontierState->right ||
                safeStoreState->bot > frontierState->bot;
            if (!report.reinsertBoundsSplit)
            {
                add_mismatch(mismatches,
                             test.name,
                             "reinsert_bounds_split",
                             "safe-store bounds did not preserve older epoch history");
                ok = false;
            }
        }
    }

    if (test.name == "slot_tie" && !report.sawSlotTieEviction)
    {
        add_mismatch(mismatches,
                     test.name,
                     "slot_tie",
                     "expected full-set equal-score miss to evict slot 0/start(10,1)");
        ok = false;
    }
    if (test.name == "lower_score_full_set_miss" && !report.sawLowerScoreFullSetMiss)
    {
        add_mismatch(mismatches,
                     test.name,
                     "lower_score_full_set_miss",
                     "expected full-set miss to accept a score below the previous floor");
        ok = false;
    }
    if (test.expectsReinsertBoundsSplit && !report.sawReinsert)
    {
        add_mismatch(mismatches,
                     test.name,
                     "reinsert",
                     "expected a reinsert trace operation");
        ok = false;
    }
    if ((test.name == "contiguous_same_start" ||
         test.name == "repeated_hit_update" ||
         test.name == "score_tie") &&
        !report.sawHit)
    {
        add_mismatch(mismatches,
                     test.name,
                     "hit",
                     "expected at least one hit trace operation");
        ok = false;
    }

    report.exact = ok;
    return ok;
}

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
    std::vector<TestCase> tests;
    tests.push_back(make_contiguous_same_start_case());
    tests.push_back(make_repeated_hit_update_case());
    tests.push_back(make_score_tie_case());
    tests.push_back(make_slot_tie_case());
    tests.push_back(make_lower_score_full_set_miss_case());
    tests.push_back(make_production_k_revisit_after_eviction_case());
    tests.push_back(make_evicted_start_later_reinsert_case());

    bool ok = true;
    std::vector<std::string> mismatches;
    std::vector<CaseReport> reports;
    reports.reserve(tests.size());

    if (!ensure_directory(".tmp") || !ensure_directory(kArtifactDir))
    {
        return 1;
    }

    for (size_t i = 0; i < tests.size(); ++i)
    {
        CaseReport report;
        const bool caseOk = analyze_case(tests[i], report, mismatches);
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
