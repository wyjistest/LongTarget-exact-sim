#include <algorithm>
#include <cerrno>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <sys/stat.h>
#include <sys/types.h>
#include <vector>

#include "../sim.h"

namespace
{

const char *kArtifactDir = ".tmp/gpu_frontier_compact_transducer_feasibility_2026-05-01";
const double kMaterialCompressionRatio = 0.5;

struct FrontierState
{
    std::vector<SimScanCudaCandidateState> states;
    int runningMin;
};

struct CompactFrontierEntry
{
    SimScanCudaCandidateState state;
    size_t rawBeginOrdinal;
    size_t rawEndOrdinal;
};

struct CompactChunkTransformer
{
    size_t ordinal;
    size_t beginOrdinal;
    size_t endOrdinal;
    std::vector<CompactFrontierEntry> entries;
};

struct TestCase
{
    std::string name;
    std::vector<SimScanCudaInitialRunSummary> summaries;
    bool randomized;
};

struct ChunkProfile
{
    int chunkSize;
    size_t chunkCount;
    size_t rawSummaryCount;
    size_t compactEntryCount;
    size_t rawBytes;
    size_t compactBytes;
    double compressionRatio;
    double entryReductionPct;
    bool exact;
    bool materiallySmaller;
};

struct CaseReport
{
    std::string name;
    size_t summaryCount;
    bool randomized;
    bool exact;
    bool anyMaterialCompression;
    bool allChunkSizesMaterial;
    std::vector<ChunkProfile> profiles;
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

static std::string state_vector_json(const std::vector<SimScanCudaCandidateState> &states)
{
    std::ostringstream out;
    out << "[";
    for (size_t i = 0; i < states.size(); ++i)
    {
        if (i > 0) out << ",";
        out << state_json(states[i]);
    }
    out << "]";
    return out.str();
}

static bool states_equal(const SimScanCudaCandidateState &lhs,
                         const SimScanCudaCandidateState &rhs)
{
    return std::memcmp(&lhs, &rhs, sizeof(SimScanCudaCandidateState)) == 0;
}

static bool frontier_states_equal_ordered(const FrontierState &actual,
                                          const FrontierState &expected,
                                          std::string *detail,
                                          size_t *slotOut)
{
    if (actual.runningMin != expected.runningMin)
    {
        if (detail != NULL)
        {
            std::ostringstream out;
            out << "runningMin expected " << expected.runningMin << ", got " << actual.runningMin;
            *detail = out.str();
        }
        if (slotOut != NULL) *slotOut = 0;
        return false;
    }
    if (actual.states.size() != expected.states.size())
    {
        if (detail != NULL)
        {
            std::ostringstream out;
            out << "frontier count expected " << expected.states.size()
                << ", got " << actual.states.size();
            *detail = out.str();
        }
        if (slotOut != NULL) *slotOut = 0;
        return false;
    }
    for (size_t i = 0; i < actual.states.size(); ++i)
    {
        if (!states_equal(actual.states[i], expected.states[i]))
        {
            if (detail != NULL)
            {
                std::ostringstream out;
                out << "slot " << i << " expected " << state_json(expected.states[i])
                    << ", got " << state_json(actual.states[i]);
                *detail = out.str();
            }
            if (slotOut != NULL) *slotOut = i;
            return false;
        }
    }
    return true;
}

static FrontierState state_from_context(const SimKernelContext &context)
{
    FrontierState state;
    collectSimContextCandidateStates(context, state.states);
    state.runningMin = static_cast<int>(context.runningMin);
    return state;
}

static FrontierState replay_legacy_ordered(const std::vector<SimScanCudaInitialRunSummary> &summaries)
{
    SimKernelContext context(8192, 8192);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);
    mergeSimCudaInitialRunSummaries(summaries,
                                    static_cast<uint64_t>(summaries.size()),
                                    context);
    return state_from_context(context);
}

static FrontierState apply_raw_chunk(const FrontierState &incoming,
                                     const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                     size_t begin,
                                     size_t end)
{
    SimKernelContext context(8192, 8192);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);
    applySimCudaReducedCandidates(incoming.states, incoming.runningMin, context);
    std::vector<SimScanCudaInitialRunSummary> chunk(summaries.begin() + static_cast<std::ptrdiff_t>(begin),
                                                    summaries.begin() + static_cast<std::ptrdiff_t>(end));
    mergeSimCudaInitialRunSummaries(chunk,
                                    static_cast<uint64_t>(chunk.size()),
                                    context);
    return state_from_context(context);
}

static SimScanCudaCandidateState candidate_state_from_summary(const SimScanCudaInitialRunSummary &summary)
{
    SimScanCudaCandidateState state;
    initSimScanCudaCandidateStateFromInitialRunSummary(summary, state);
    return state;
}

static void merge_summary_into_candidate_state(const SimScanCudaInitialRunSummary &summary,
                                               SimScanCudaCandidateState &state)
{
    updateSimScanCudaCandidateStateFromInitialRunSummary(summary, state);
}

static CompactChunkTransformer make_compact_chunk_transformer(
    const std::vector<SimScanCudaInitialRunSummary> &summaries,
    size_t ordinal,
    size_t begin,
    size_t end)
{
    CompactChunkTransformer transformer;
    transformer.ordinal = ordinal;
    transformer.beginOrdinal = begin;
    transformer.endOrdinal = end;
    for (size_t i = begin; i < end;)
    {
        CompactFrontierEntry entry;
        entry.rawBeginOrdinal = i;
        entry.state = candidate_state_from_summary(summaries[i]);
        size_t j = i + 1;
        while (j < end && summaries[j].startCoord == summaries[i].startCoord)
        {
            merge_summary_into_candidate_state(summaries[j], entry.state);
            ++j;
        }
        entry.rawEndOrdinal = j;
        transformer.entries.push_back(entry);
        i = j;
    }
    return transformer;
}

static std::vector<CompactChunkTransformer> make_compact_chunk_transformers(
    const std::vector<SimScanCudaInitialRunSummary> &summaries,
    int chunkSize)
{
    std::vector<CompactChunkTransformer> transformers;
    const size_t safeChunkSize = static_cast<size_t>(chunkSize > 0 ? chunkSize : 1);
    for (size_t begin = 0; begin < summaries.size(); begin += safeChunkSize)
    {
        const size_t end = std::min(begin + safeChunkSize, summaries.size());
        transformers.push_back(make_compact_chunk_transformer(summaries,
                                                              transformers.size(),
                                                              begin,
                                                              end));
    }
    return transformers;
}

static FrontierState apply_compact_chunk(const FrontierState &incoming,
                                         const CompactChunkTransformer &transformer)
{
    SimKernelContext context(8192, 8192);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);
    applySimCudaReducedCandidates(incoming.states, incoming.runningMin, context);
    for (size_t i = 0; i < transformer.entries.size(); ++i)
    {
        applySimCudaCandidateState(transformer.entries[i].state, context);
    }
    refreshSimRunningMin(context);
    return state_from_context(context);
}

static FrontierState compose_raw_chunks(const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                        int chunkSize)
{
    FrontierState state;
    state.runningMin = 0;
    const size_t safeChunkSize = static_cast<size_t>(chunkSize > 0 ? chunkSize : 1);
    for (size_t begin = 0; begin < summaries.size(); begin += safeChunkSize)
    {
        const size_t end = std::min(begin + safeChunkSize, summaries.size());
        state = apply_raw_chunk(state, summaries, begin, end);
    }
    return state;
}

static FrontierState compose_compact_chunks(const std::vector<CompactChunkTransformer> &transformers)
{
    FrontierState state;
    state.runningMin = 0;
    for (size_t i = 0; i < transformers.size(); ++i)
    {
        state = apply_compact_chunk(state, transformers[i]);
    }
    return state;
}

static size_t compact_entry_count(const std::vector<CompactChunkTransformer> &transformers)
{
    size_t count = 0;
    for (size_t i = 0; i < transformers.size(); ++i)
    {
        count += transformers[i].entries.size();
    }
    return count;
}

static std::vector<int> chunk_sizes_for_case(size_t summaryCount)
{
    std::vector<int> sizes;
    const int candidates[] = {1, 2, 3, 5, 7, K - 1, K, K + 1, 256};
    for (size_t i = 0; i < sizeof(candidates) / sizeof(candidates[0]); ++i)
    {
        if (candidates[i] > 0 &&
            static_cast<size_t>(candidates[i]) <= std::max<size_t>(summaryCount, 1))
        {
            sizes.push_back(candidates[i]);
        }
    }
    sizes.push_back(static_cast<int>(std::max<size_t>(summaryCount, 1)));
    std::sort(sizes.begin(), sizes.end());
    sizes.erase(std::unique(sizes.begin(), sizes.end()), sizes.end());
    return sizes;
}

static TestCase make_production_k_eviction_revisit_case()
{
    TestCase test;
    test.name = "production_k_eviction_revisit";
    test.randomized = false;
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

static TestCase make_same_score_tie_case()
{
    TestCase test;
    test.name = "same_score_tie";
    test.randomized = false;
    test.summaries.push_back(make_summary(30, 7, 7, 1, 70, 72, 71));
    test.summaries.push_back(make_summary(30, 7, 7, 2, 68, 75, 74));
    test.summaries.push_back(make_summary(29, 8, 7, 1, 80));
    return test;
}

static TestCase make_same_start_update_case()
{
    TestCase test;
    test.name = "same_start_update";
    test.randomized = false;
    test.summaries.push_back(make_summary(20, 5, 5, 1, 50));
    test.summaries.push_back(make_summary(18, 6, 5, 1, 60));
    test.summaries.push_back(make_summary(25, 5, 5, 2, 45, 55, 47));
    test.summaries.push_back(make_summary(24, 5, 5, 4, 40, 58, 52));
    return test;
}

static TestCase make_k_boundary_case()
{
    TestCase test;
    test.name = "k_boundary_slot_tie";
    test.randomized = false;
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

static TestCase make_block_split_case()
{
    TestCase test;
    test.name = "block_split";
    test.randomized = false;
    for (int i = 0; i < K - 1; ++i)
    {
        test.summaries.push_back(make_summary(120 + i,
                                              50,
                                              static_cast<uint32_t>(i + 1),
                                              1,
                                              static_cast<uint32_t>(5000 + i)));
    }
    test.summaries.push_back(make_summary(90, 61, 1, 1, 6100));
    test.summaries.push_back(make_summary(89, 62, 1, 1, 6200));
    test.summaries.push_back(make_summary(130, 61, 1, 2, 6090, 6110, 6105));
    test.summaries.push_back(make_summary(131, 63, 1, 1, 6300));
    return test;
}

static TestCase make_row_order_conflict_case()
{
    TestCase test;
    test.name = "row_order_conflict";
    test.randomized = false;
    for (int i = 0; i < K; ++i)
    {
        test.summaries.push_back(make_summary(100,
                                              30,
                                              static_cast<uint32_t>(i + 1),
                                              1,
                                              static_cast<uint32_t>(3000 + i)));
    }
    test.summaries.push_back(make_summary(100, 40, 1, 1, 4000));
    test.summaries.push_back(make_summary(100, 40, 2, 1, 4001));
    return test;
}

static TestCase make_repeated_hit_update_after_eviction_case()
{
    TestCase test;
    test.name = "repeated_hit_update_after_eviction";
    test.randomized = false;
    test.summaries.push_back(make_summary(10, 70, 70, 1, 7000));
    test.summaries.push_back(make_summary(12, 70, 70, 2, 6995, 7005, 7001));
    for (int i = 0; i < K - 1; ++i)
    {
        test.summaries.push_back(make_summary(80 + i,
                                              71,
                                              static_cast<uint32_t>(i + 1),
                                              1,
                                              static_cast<uint32_t>(7100 + i)));
    }
    test.summaries.push_back(make_summary(13, 72, 1, 1, 7200));
    test.summaries.push_back(make_summary(14, 70, 70, 3, 6988, 7010, 7009));
    test.summaries.push_back(make_summary(16, 70, 70, 4, 6980, 7020, 7018));
    return test;
}

static uint32_t next_lcg(uint32_t &state)
{
    state = state * 1664525u + 1013904223u;
    return state;
}

static TestCase make_random_case(uint32_t seed, int ordinal)
{
    TestCase test;
    std::ostringstream name;
    name << "random_seed_" << seed;
    test.name = name.str();
    test.randomized = true;
    uint32_t state = seed;
    const size_t summaryCount = 96 + static_cast<size_t>(ordinal * 7);
    for (size_t i = 0; i < summaryCount; ++i)
    {
        const uint32_t startBand = next_lcg(state) % 12u;
        const uint32_t startI = 100u + startBand;
        const uint32_t startJ = 1u + (next_lcg(state) % 9u);
        const int score = 25 + static_cast<int>(next_lcg(state) % 80u);
        const uint32_t endI = 1u + static_cast<uint32_t>(i % 7u);
        const uint32_t centerJ = 8000u + static_cast<uint32_t>(i * 3u) + (next_lcg(state) % 11u);
        const uint32_t width = next_lcg(state) % 5u;
        const uint32_t minEndJ = centerJ - width;
        const uint32_t maxEndJ = centerJ + width;
        const uint32_t scoreEndJ = minEndJ + (next_lcg(state) % (width * 2u + 1u));
        test.summaries.push_back(make_summary(score,
                                              startI,
                                              startJ,
                                              endI,
                                              minEndJ,
                                              maxEndJ,
                                              scoreEndJ));
        if ((i % 13u) == 3u)
        {
            test.summaries.push_back(make_summary(score + 1,
                                                  startI,
                                                  startJ,
                                                  endI + 1u,
                                                  minEndJ > 0 ? minEndJ - 1u : minEndJ,
                                                  maxEndJ + 2u,
                                                  scoreEndJ + 1u));
        }
    }
    return test;
}

static std::vector<TestCase> make_test_cases()
{
    std::vector<TestCase> tests;
    tests.push_back(make_production_k_eviction_revisit_case());
    tests.push_back(make_same_score_tie_case());
    tests.push_back(make_same_start_update_case());
    tests.push_back(make_k_boundary_case());
    tests.push_back(make_block_split_case());
    tests.push_back(make_row_order_conflict_case());
    tests.push_back(make_repeated_hit_update_after_eviction_case());
    tests.push_back(make_random_case(0x5eed1234u, 0));
    tests.push_back(make_random_case(0x5eed5678u, 1));
    tests.push_back(make_random_case(0x5eed9abcu, 2));
    return tests;
}

static ChunkProfile profile_chunk_size(const TestCase &test,
                                       int chunkSize,
                                       bool &exact,
                                       std::vector<std::string> &mismatches)
{
    const FrontierState truth = replay_legacy_ordered(test.summaries);
    const FrontierState rawComposed = compose_raw_chunks(test.summaries, chunkSize);
    const std::vector<CompactChunkTransformer> compactTransformers =
        make_compact_chunk_transformers(test.summaries, chunkSize);
    const FrontierState compactComposed = compose_compact_chunks(compactTransformers);

    std::string detail;
    size_t slot = 0;
    const bool rawExact = frontier_states_equal_ordered(rawComposed, truth, &detail, &slot);
    if (!rawExact)
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"chunk_size\":" + std::to_string(chunkSize) +
                             ",\"kind\":\"raw_chunk_composition\",\"first_mismatch_slot\":" +
                             std::to_string(slot) + ",\"detail\":\"" +
                             json_escape(detail) + "\"}");
    }

    detail.clear();
    slot = 0;
    const bool compactExact = frontier_states_equal_ordered(compactComposed, truth, &detail, &slot);
    if (!compactExact)
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"chunk_size\":" + std::to_string(chunkSize) +
                             ",\"kind\":\"compact_chunk_composition\",\"first_mismatch_slot\":" +
                             std::to_string(slot) + ",\"detail\":\"" +
                             json_escape(detail) + "\",\"expected_frontier\":" +
                             state_vector_json(truth.states) + ",\"actual_frontier\":" +
                             state_vector_json(compactComposed.states) + "}");
    }

    exact = rawExact && compactExact;
    const size_t compactEntries = compact_entry_count(compactTransformers);
    const size_t rawBytes =
        test.summaries.size() * sizeof(SimScanCudaInitialRunSummary);
    const size_t compactBytes =
        compactEntries * sizeof(SimScanCudaCandidateState);
    ChunkProfile profile;
    profile.chunkSize = chunkSize;
    profile.chunkCount = compactTransformers.size();
    profile.rawSummaryCount = test.summaries.size();
    profile.compactEntryCount = compactEntries;
    profile.rawBytes = rawBytes;
    profile.compactBytes = compactBytes;
    profile.compressionRatio =
        rawBytes == 0 ? 1.0 : static_cast<double>(compactBytes) / static_cast<double>(rawBytes);
    profile.entryReductionPct =
        test.summaries.empty()
            ? 0.0
            : 100.0 * (1.0 - static_cast<double>(compactEntries) /
                              static_cast<double>(test.summaries.size()));
    profile.exact = exact;
    profile.materiallySmaller =
        exact && profile.compressionRatio <= kMaterialCompressionRatio;
    return profile;
}

static bool analyze_cases(const std::vector<TestCase> &tests,
                          std::vector<CaseReport> &reports,
                          std::vector<std::string> &mismatches)
{
    bool allExact = true;
    reports.clear();
    for (size_t caseIndex = 0; caseIndex < tests.size(); ++caseIndex)
    {
        const TestCase &test = tests[caseIndex];
        CaseReport report;
        report.name = test.name;
        report.summaryCount = test.summaries.size();
        report.randomized = test.randomized;
        report.exact = true;
        report.anyMaterialCompression = false;
        report.allChunkSizesMaterial = true;

        const std::vector<int> chunkSizes = chunk_sizes_for_case(test.summaries.size());
        for (size_t i = 0; i < chunkSizes.size(); ++i)
        {
            bool chunkExact = false;
            ChunkProfile profile =
                profile_chunk_size(test, chunkSizes[i], chunkExact, mismatches);
            report.profiles.push_back(profile);
            report.exact = report.exact && chunkExact;
            report.anyMaterialCompression =
                report.anyMaterialCompression || profile.materiallySmaller;
            report.allChunkSizesMaterial =
                report.allChunkSizesMaterial && profile.materiallySmaller;
        }
        allExact = allExact && report.exact;
        reports.push_back(report);
    }
    return allExact;
}

static bool any_material_compression(const std::vector<CaseReport> &reports)
{
    for (size_t i = 0; i < reports.size(); ++i)
    {
        if (reports[i].anyMaterialCompression)
        {
            return true;
        }
    }
    return false;
}

static bool consistently_material_compression(const std::vector<CaseReport> &reports)
{
    if (reports.empty())
    {
        return false;
    }
    for (size_t i = 0; i < reports.size(); ++i)
    {
        if (!reports[i].allChunkSizesMaterial)
        {
            return false;
        }
    }
    return true;
}

static size_t mismatch_count(const std::vector<std::string> &mismatches)
{
    return mismatches.size();
}

static bool write_mismatches(const std::vector<std::string> &mismatches)
{
    const std::string path = std::string(kArtifactDir) + "/compact_transducer_mismatches.jsonl";
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

static void write_profile_json(std::ostream &out, const ChunkProfile &profile)
{
    out << "{\"chunk_size\":" << profile.chunkSize
        << ",\"chunk_count\":" << profile.chunkCount
        << ",\"raw_summary_count\":" << profile.rawSummaryCount
        << ",\"compact_entry_count\":" << profile.compactEntryCount
        << ",\"raw_bytes\":" << profile.rawBytes
        << ",\"compact_bytes\":" << profile.compactBytes
        << ",\"compression_ratio\":" << profile.compressionRatio
        << ",\"entry_reduction_pct\":" << profile.entryReductionPct
        << ",\"exact\":" << (profile.exact ? "true" : "false")
        << ",\"materially_smaller\":" << (profile.materiallySmaller ? "true" : "false")
        << "}";
}

static bool write_compression_profile(const std::vector<CaseReport> &reports)
{
    const std::string path = std::string(kArtifactDir) + "/compression_profile.json";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }
    out << "{\n";
    out << "  \"date\":\"2026-05-01\",\n";
    out << "  \"compact_representation\":\"consecutive_same_start_candidate_state_effects\",\n";
    out << "  \"material_compression_ratio_threshold\":" << kMaterialCompressionRatio << ",\n";
    out << "  \"cases\":[\n";
    for (size_t i = 0; i < reports.size(); ++i)
    {
        const CaseReport &report = reports[i];
        out << "    {\"name\":\"" << json_escape(report.name) << "\""
            << ",\"summary_count\":" << report.summaryCount
            << ",\"randomized\":" << (report.randomized ? "true" : "false")
            << ",\"any_material_compression\":" << (report.anyMaterialCompression ? "true" : "false")
            << ",\"all_chunk_sizes_material\":" << (report.allChunkSizesMaterial ? "true" : "false")
            << ",\"profiles\":[";
        for (size_t j = 0; j < report.profiles.size(); ++j)
        {
            if (j > 0) out << ",";
            write_profile_json(out, report.profiles[j]);
        }
        out << "]}";
        if (i + 1 < reports.size()) out << ",";
        out << "\n";
    }
    out << "  ]\n";
    out << "}\n";
    return true;
}

static const char *decision_action(bool exact,
                                   bool material)
{
    if (!exact)
    {
        return "fix_compact_transducer_semantics_or_abandon_compaction";
    }
    if (material)
    {
        return "gpu_compact_transducer_shadow";
    }
    return "stop_frontier_runtime_reduce_and_optimize_cpu_context_apply_or_d2h";
}

static bool write_summary_json(const std::vector<CaseReport> &reports,
                               const std::vector<std::string> &mismatches,
                               bool allExact)
{
    const bool anyMaterial = any_material_compression(reports);
    const bool consistentlyMaterial = consistently_material_compression(reports);
    const std::string path = std::string(kArtifactDir) + "/compact_transducer_summary.json";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }
    out << "{\n";
    out << "  \"date\":\"2026-05-01\",\n";
    out << "  \"candidate\":\"compact_frontier_transducer_feasibility_oracle\",\n";
    out << "  \"status\":\"" << (allExact ? "passed" : "failed") << "\",\n";
    out << "  \"oracle_scope\":\"test_only_cpu_oracle_no_runtime_path_change\",\n";
    out << "  \"compact_representation\":\"consecutive_same_start_candidate_state_effects\",\n";
    out << "  \"default_path_changes_allowed\":false,\n";
    out << "  \"runtime_frontier_reduce_allowed\":false,\n";
    out << "  \"gpu_frontier_shadow_allowed_next\":\"" << (allExact && consistentlyMaterial ? "compact_shadow_only" : "blocked") << "\",\n";
    out << "  \"safe_store_handoff_keep_opt_in\":true,\n";
    out << "  \"mismatch_count\":" << mismatch_count(mismatches) << ",\n";
    out << "  \"case_count\":" << reports.size() << ",\n";
    out << "  \"all_cases_exact\":" << (allExact ? "true" : "false") << ",\n";
    out << "  \"any_material_compression\":" << (anyMaterial ? "true" : "false") << ",\n";
    out << "  \"consistently_material_compression\":" << (consistentlyMaterial ? "true" : "false") << ",\n";
    out << "  \"material_compression_rule\":\"compact_bytes <= 50% of raw_summary_bytes for every case/chunk size\",\n";
    out << "  \"recommended_next_action\":\"" << decision_action(allExact, consistentlyMaterial) << "\",\n";
    out << "  \"cases\":[\n";
    for (size_t i = 0; i < reports.size(); ++i)
    {
        const CaseReport &report = reports[i];
        out << "    {\"name\":\"" << json_escape(report.name) << "\""
            << ",\"summary_count\":" << report.summaryCount
            << ",\"randomized\":" << (report.randomized ? "true" : "false")
            << ",\"exact\":" << (report.exact ? "true" : "false")
            << ",\"any_material_compression\":" << (report.anyMaterialCompression ? "true" : "false")
            << ",\"all_chunk_sizes_material\":" << (report.allChunkSizesMaterial ? "true" : "false")
            << "}";
        if (i + 1 < reports.size()) out << ",";
        out << "\n";
    }
    out << "  ]\n";
    out << "}\n";
    return true;
}

static bool write_summary_md(const std::vector<CaseReport> &reports,
                             const std::vector<std::string> &mismatches,
                             bool allExact)
{
    const bool consistentlyMaterial = consistently_material_compression(reports);
    const std::string path = std::string(kArtifactDir) + "/compact_transducer_summary.md";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }
    out << "# Compact Frontier Transducer Feasibility Oracle\n\n";
    out << "Date: 2026-05-01\n\n";
    out << "- Oracle: CPU test-only compact transducer feasibility\n";
    out << "- Representation: consecutive same-start candidate-state effects\n";
    out << "- Exactness: " << (allExact ? "passed" : "failed") << "\n";
    out << "- Mismatches: " << mismatches.size() << "\n";
    out << "- Consistently material compression: " << (consistentlyMaterial ? "yes" : "no") << "\n";
    out << "- Runtime frontier reducer: blocked\n";
    out << "- Default path changes: blocked\n";
    out << "- Recommended next action: " << decision_action(allExact, consistentlyMaterial) << "\n";
    return true;
}

static bool write_decision_json(const std::vector<CaseReport> &reports,
                                bool allExact)
{
    const bool consistentlyMaterial = consistently_material_compression(reports);
    const std::string path = std::string(kArtifactDir) + "/decision.json";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return false;
    }
    out << "{\n";
    out << "  \"recommended_next_action\":\"" << decision_action(allExact, consistentlyMaterial) << "\",\n";
    out << "  \"compact_frontier_transducer_oracle\":\"" << (allExact ? "passed" : "failed") << "\",\n";
    out << "  \"exact_compaction_gate\":\"" << (allExact ? "passed" : "failed") << "\",\n";
    out << "  \"material_compression_gate\":\"" << (consistentlyMaterial ? "passed" : "failed") << "\",\n";
    out << "  \"runtime_frontier_reduce_allowed\":false,\n";
    out << "  \"default_path_changes_allowed\":false,\n";
    out << "  \"gpu_frontier_shadow_allowed\":\"" << (allExact && consistentlyMaterial ? "compact_shadow_only" : "false") << "\",\n";
    out << "  \"safe_store_handoff_keep_opt_in\":true\n";
    out << "}\n";
    return true;
}

} // namespace

int main()
{
    if (!ensure_directory(".tmp") || !ensure_directory(kArtifactDir))
    {
        return 1;
    }

    const std::vector<TestCase> tests = make_test_cases();
    std::vector<CaseReport> reports;
    std::vector<std::string> mismatches;
    bool ok = analyze_cases(tests, reports, mismatches);

    ok = write_mismatches(mismatches) && ok;
    ok = write_compression_profile(reports) && ok;
    ok = write_summary_json(reports, mismatches, mismatches.empty()) && ok;
    ok = write_summary_md(reports, mismatches, mismatches.empty()) && ok;
    ok = write_decision_json(reports, mismatches.empty()) && ok;

    if (!mismatches.empty())
    {
        std::cerr << "compact transducer mismatches: " << mismatches.size() << "\n";
        std::cerr << "see " << kArtifactDir << "/compact_transducer_mismatches.jsonl\n";
    }
    if (!ok)
    {
        return 1;
    }
    std::cout << "ok\n";
    return 0;
}
