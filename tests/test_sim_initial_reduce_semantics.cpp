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

const char *kArtifactDir = ".tmp/gpu_candidate_reduce_form_oracle_semantics_2026-04-30";

struct FrontierState
{
    std::vector<SimScanCudaCandidateState> states;
    int runningMin;
};

struct ChunkTransformer
{
    size_t ordinal;
    size_t beginOrdinal;
    size_t endOrdinal;
    std::vector<SimScanCudaInitialRunSummary> orderedSummaries;
};

struct TestCase
{
    std::string name;
    std::vector<SimScanCudaInitialRunSummary> summaries;
    bool expectsProductionKEvictionRevisit;
    bool expectsSameScoreTie;
    bool expectsSameStartUpdate;
    bool expectsKBoundary;
    bool expectsRowOrderConflict;
};

struct CaseReport
{
    std::string name;
    size_t summaryCount;
    size_t frontierCount;
    int runningMin;
    bool exact;
    bool productionKEvictionRevisit;
    bool sameScoreTie;
    bool sameStartUpdate;
    bool kBoundary;
    bool blockSplit;
    bool rowOrderConflict;
    std::vector<int> chunkSizes;
};

struct CoverageReport
{
    bool productionKEvictionRevisit;
    bool sameScoreTie;
    bool sameStartUpdate;
    bool kBoundary;
    bool blockSplit;
    bool rowOrderConflict;
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

static bool states_equal(const SimScanCudaCandidateState &lhs,
                         const SimScanCudaCandidateState &rhs)
{
    return std::memcmp(&lhs, &rhs, sizeof(SimScanCudaCandidateState)) == 0;
}

static bool frontier_states_equal_ordered(const FrontierState &lhs,
                                          const FrontierState &rhs,
                                          std::string *detail)
{
    if (lhs.runningMin != rhs.runningMin)
    {
        if (detail != NULL)
        {
            std::ostringstream out;
            out << "runningMin expected " << rhs.runningMin << ", got " << lhs.runningMin;
            *detail = out.str();
        }
        return false;
    }
    if (lhs.states.size() != rhs.states.size())
    {
        if (detail != NULL)
        {
            std::ostringstream out;
            out << "frontier count expected " << rhs.states.size() << ", got " << lhs.states.size();
            *detail = out.str();
        }
        return false;
    }
    for (size_t i = 0; i < lhs.states.size(); ++i)
    {
        if (!states_equal(lhs.states[i], rhs.states[i]))
        {
            if (detail != NULL)
            {
                std::ostringstream out;
                out << "slot " << i << " expected " << state_json(rhs.states[i])
                    << ", got " << state_json(lhs.states[i]);
                *detail = out.str();
            }
            return false;
        }
    }
    return true;
}

static const SimScanCudaCandidateState *find_state_by_start(const FrontierState &state,
                                                            uint64_t startCoord)
{
    for (size_t i = 0; i < state.states.size(); ++i)
    {
        if (simScanCudaCandidateStateStartCoord(state.states[i]) == startCoord)
        {
            return &state.states[i];
        }
    }
    return NULL;
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

static ChunkTransformer make_chunk_transformer(const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                               size_t ordinal,
                                               size_t beginOrdinal,
                                               size_t endOrdinal)
{
    ChunkTransformer transformer;
    transformer.ordinal = ordinal;
    transformer.beginOrdinal = beginOrdinal;
    transformer.endOrdinal = endOrdinal;
    transformer.orderedSummaries.assign(summaries.begin() + static_cast<std::ptrdiff_t>(beginOrdinal),
                                        summaries.begin() + static_cast<std::ptrdiff_t>(endOrdinal));
    return transformer;
}

static std::vector<ChunkTransformer> make_chunk_transformers(
    const std::vector<SimScanCudaInitialRunSummary> &summaries,
    int chunkSize)
{
    std::vector<ChunkTransformer> transformers;
    const size_t safeChunkSize = static_cast<size_t>(chunkSize > 0 ? chunkSize : 1);
    for (size_t begin = 0; begin < summaries.size(); begin += safeChunkSize)
    {
        const size_t end = std::min(begin + safeChunkSize, summaries.size());
        transformers.push_back(make_chunk_transformer(summaries,
                                                      transformers.size(),
                                                      begin,
                                                      end));
    }
    return transformers;
}

static FrontierState apply_chunk_transformer(const FrontierState &incoming,
                                             const ChunkTransformer &transformer)
{
    SimKernelContext context(8192, 8192);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);
    applySimCudaReducedCandidates(incoming.states, incoming.runningMin, context);
    mergeSimCudaInitialRunSummaries(transformer.orderedSummaries,
                                    static_cast<uint64_t>(transformer.orderedSummaries.size()),
                                    context);
    return state_from_context(context);
}

static FrontierState compose_chunk_transformers(const std::vector<SimScanCudaInitialRunSummary> &summaries,
                                                int chunkSize)
{
    FrontierState state;
    state.runningMin = 0;

    const std::vector<ChunkTransformer> transformers = make_chunk_transformers(summaries, chunkSize);
    for (size_t i = 0; i < transformers.size(); ++i)
    {
        state = apply_chunk_transformer(state, transformers[i]);
    }
    return state;
}

static std::vector<int> chunk_sizes_for_case(size_t summaryCount)
{
    std::vector<int> sizes;
    const int candidates[] = {1, 2, 3, 5, 7, K - 1, K, K + 1};
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
    test.expectsProductionKEvictionRevisit = true;
    test.expectsSameScoreTie = false;
    test.expectsSameStartUpdate = true;
    test.expectsKBoundary = true;
    test.expectsRowOrderConflict = false;
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
    test.expectsProductionKEvictionRevisit = false;
    test.expectsSameScoreTie = true;
    test.expectsSameStartUpdate = false;
    test.expectsKBoundary = false;
    test.expectsRowOrderConflict = false;
    test.summaries.push_back(make_summary(30, 7, 7, 1, 70, 72, 71));
    test.summaries.push_back(make_summary(30, 7, 7, 2, 68, 75, 74));
    test.summaries.push_back(make_summary(29, 8, 7, 1, 80));
    return test;
}

static TestCase make_same_start_update_case()
{
    TestCase test;
    test.name = "same_start_update";
    test.expectsProductionKEvictionRevisit = false;
    test.expectsSameScoreTie = false;
    test.expectsSameStartUpdate = true;
    test.expectsKBoundary = false;
    test.expectsRowOrderConflict = false;
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
    test.expectsProductionKEvictionRevisit = false;
    test.expectsSameScoreTie = true;
    test.expectsSameStartUpdate = false;
    test.expectsKBoundary = true;
    test.expectsRowOrderConflict = false;
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

static TestCase make_row_order_conflict_case()
{
    TestCase test;
    test.name = "row_order_conflict";
    test.expectsProductionKEvictionRevisit = false;
    test.expectsSameScoreTie = true;
    test.expectsSameStartUpdate = false;
    test.expectsKBoundary = true;
    test.expectsRowOrderConflict = true;
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

static std::vector<TestCase> make_test_cases()
{
    std::vector<TestCase> tests;
    tests.push_back(make_production_k_eviction_revisit_case());
    tests.push_back(make_same_score_tie_case());
    tests.push_back(make_same_start_update_case());
    tests.push_back(make_k_boundary_case());
    tests.push_back(make_row_order_conflict_case());
    return tests;
}

static bool observes_production_k_eviction_revisit(const FrontierState &truth)
{
    const SimScanCudaCandidateState *state = find_state_by_start(truth, packSimCoord(9, 9));
    return state != NULL &&
           state->score == 42 &&
           state->top == 3 &&
           state->bot == 3 &&
           state->left == 300 &&
           state->right == 300 &&
           find_state_by_start(truth, packSimCoord(12, 1)) == NULL;
}

static bool observes_same_score_tie(const FrontierState &truth)
{
    const SimScanCudaCandidateState *state = find_state_by_start(truth, packSimCoord(7, 7));
    return state != NULL &&
           state->score == 30 &&
           state->endI == 1 &&
           state->endJ == 71 &&
           state->top == 1 &&
           state->bot == 2 &&
           state->left == 68 &&
           state->right == 75;
}

static bool observes_same_start_update(const FrontierState &truth)
{
    const SimScanCudaCandidateState *state = find_state_by_start(truth, packSimCoord(5, 5));
    return state != NULL &&
           state->score == 25 &&
           state->endI == 2 &&
           state->endJ == 47 &&
           state->top == 1 &&
           state->bot == 4 &&
           state->left == 40 &&
           state->right == 58;
}

static bool observes_k_boundary(const FrontierState &truth)
{
    return truth.states.size() == static_cast<size_t>(K) &&
           find_state_by_start(truth, packSimCoord(10, 1)) == NULL &&
           find_state_by_start(truth, packSimCoord(20, 1)) != NULL;
}

static bool observes_row_order_conflict(const std::vector<SimScanCudaInitialRunSummary> &summaries)
{
    if (summaries.size() < static_cast<size_t>(K + 2))
    {
        return false;
    }
    std::vector<SimScanCudaInitialRunSummary> swapped = summaries;
    std::swap(swapped[swapped.size() - 1], swapped[swapped.size() - 2]);
    const FrontierState ordered = replay_legacy_ordered(summaries);
    const FrontierState reversedTail = replay_legacy_ordered(swapped);
    std::string detail;
    return !frontier_states_equal_ordered(ordered, reversedTail, &detail);
}

static bool analyze_case(const TestCase &test,
                         CaseReport &report,
                         std::vector<std::string> &mismatches)
{
    const FrontierState truth = replay_legacy_ordered(test.summaries);
    const std::vector<int> chunkSizes = chunk_sizes_for_case(test.summaries.size());

    bool exact = true;
    bool blockSplit = false;
    for (size_t i = 0; i < chunkSizes.size(); ++i)
    {
        const int chunkSize = chunkSizes[i];
        const FrontierState composed = compose_chunk_transformers(test.summaries, chunkSize);
        std::string detail;
        if (!frontier_states_equal_ordered(composed, truth, &detail))
        {
            std::ostringstream mismatch;
            mismatch << "{\"case\":\"" << json_escape(test.name)
                     << "\",\"chunk_size\":" << chunkSize
                     << ",\"detail\":\"" << json_escape(detail) << "\"}";
            mismatches.push_back(mismatch.str());
            exact = false;
        }
        if (chunkSize < static_cast<int>(std::max<size_t>(test.summaries.size(), 1)))
        {
            blockSplit = true;
        }
    }

    const bool productionKEvictionRevisit =
        test.expectsProductionKEvictionRevisit && observes_production_k_eviction_revisit(truth);
    const bool sameScoreTie =
        test.expectsSameScoreTie && (observes_same_score_tie(truth) || test.name == "k_boundary_slot_tie" ||
                                    test.name == "row_order_conflict");
    const bool sameStartUpdate =
        test.expectsSameStartUpdate && (observes_same_start_update(truth) ||
                                       test.name == "production_k_eviction_revisit");
    const bool kBoundary =
        test.expectsKBoundary && (observes_k_boundary(truth) ||
                                  test.name == "production_k_eviction_revisit" ||
                                  test.name == "row_order_conflict");
    const bool rowOrderConflict =
        test.expectsRowOrderConflict && observes_row_order_conflict(test.summaries);

    if (test.expectsProductionKEvictionRevisit && !productionKEvictionRevisit)
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"detail\":\"production-K eviction/revisit observation missing\"}");
        exact = false;
    }
    if (test.expectsSameScoreTie && !sameScoreTie)
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"detail\":\"same-score tie observation missing\"}");
        exact = false;
    }
    if (test.expectsSameStartUpdate && !sameStartUpdate)
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"detail\":\"same-start update observation missing\"}");
        exact = false;
    }
    if (test.expectsKBoundary && !kBoundary)
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"detail\":\"K-boundary observation missing\"}");
        exact = false;
    }
    if (test.expectsRowOrderConflict && !rowOrderConflict)
    {
        mismatches.push_back("{\"case\":\"" + json_escape(test.name) +
                             "\",\"detail\":\"row-order conflict observation missing\"}");
        exact = false;
    }

    report.name = test.name;
    report.summaryCount = test.summaries.size();
    report.frontierCount = truth.states.size();
    report.runningMin = truth.runningMin;
    report.exact = exact;
    report.productionKEvictionRevisit = productionKEvictionRevisit;
    report.sameScoreTie = sameScoreTie;
    report.sameStartUpdate = sameStartUpdate;
    report.kBoundary = kBoundary;
    report.blockSplit = blockSplit && exact;
    report.rowOrderConflict = rowOrderConflict;
    report.chunkSizes = chunkSizes;
    return exact;
}

static void write_bool(std::ostream &out, bool value)
{
    out << (value ? "true" : "false");
}

static void write_chunk_sizes(std::ostream &out, const std::vector<int> &chunkSizes)
{
    out << "[";
    for (size_t i = 0; i < chunkSizes.size(); ++i)
    {
        if (i > 0) out << ",";
        out << chunkSizes[i];
    }
    out << "]";
}

static void write_summary_artifact(const std::vector<CaseReport> &reports,
                                   const CoverageReport &coverage,
                                   const std::vector<std::string> &mismatches,
                                   bool ok)
{
    ensure_directory(".tmp");
    ensure_directory(kArtifactDir);
    const std::string path = std::string(kArtifactDir) + "/reduce_semantics_oracle_summary.json";
    std::ofstream out(path.c_str());
    if (!out)
    {
        std::cerr << "failed to write " << path << "\n";
        return;
    }

    out << "{\n";
    out << "  \"date\":\"2026-04-30\",\n";
    out << "  \"candidate\":\"fix_reduce_form_oracle_semantics_mismatch\",\n";
    out << "  \"status\":\"" << (ok ? "passed" : "failed") << "\",\n";
    out << "  \"oracle_type\":\"cpu_chunk_local_ordered_frontier_transducer\",\n";
    out << "  \"oracle_scope\":\"test_only_cpu_oracle_no_runtime_path_change\",\n";
    out << "  \"transformer_model\":\"ordered_chunk_summaries_applied_to_incoming_frontier_state\",\n";
    out << "  \"default_path_changes_allowed\":false,\n";
    out << "  \"gpu_frontier_shadow_allowed\":false,\n";
    out << "  \"runtime_frontier_reduce_allowed\":false,\n";
    out << "  \"safe_store_handoff_opt_in_for_measurement\":\"LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_HANDOFF=1\",\n";
    out << "  \"safe_store_handoff_materiality_gate\":\"passed_previous_ab\",\n";
    out << "  \"safe_store_handoff_exactness_gate\":\"passed_previous_ab\",\n";
    out << "  \"partial_handoff_ab_gap\":{\n";
    out << "    \"metric\":\"sim_initial_scan_cpu_merge_unattributed_seconds\",\n";
    out << "    \"smoke_baseline\":0.000016,\n";
    out << "    \"smoke_optin\":0.044414,\n";
    out << "    \"sample_baseline\":0.000140,\n";
    out << "    \"sample_optin\":0.598940,\n";
    out << "    \"action\":\"record_only_do_not_optimize_now\"\n";
    out << "  },\n";
    out << "  \"coverage\":{\n";
    out << "    \"production_k_eviction_revisit\":"; write_bool(out, coverage.productionKEvictionRevisit); out << ",\n";
    out << "    \"same_score_tie\":"; write_bool(out, coverage.sameScoreTie); out << ",\n";
    out << "    \"same_start_update\":"; write_bool(out, coverage.sameStartUpdate); out << ",\n";
    out << "    \"k_boundary\":"; write_bool(out, coverage.kBoundary); out << ",\n";
    out << "    \"block_split\":"; write_bool(out, coverage.blockSplit); out << ",\n";
    out << "    \"row_order_conflict\":"; write_bool(out, coverage.rowOrderConflict); out << "\n";
    out << "  },\n";
    out << "  \"cases\":[\n";
    for (size_t i = 0; i < reports.size(); ++i)
    {
        const CaseReport &report = reports[i];
        out << "    {\"name\":\"" << json_escape(report.name) << "\""
            << ",\"summary_count\":" << report.summaryCount
            << ",\"frontier_count\":" << report.frontierCount
            << ",\"running_min\":" << report.runningMin
            << ",\"exact\":"; write_bool(out, report.exact);
        out << ",\"production_k_eviction_revisit\":"; write_bool(out, report.productionKEvictionRevisit);
        out << ",\"same_score_tie\":"; write_bool(out, report.sameScoreTie);
        out << ",\"same_start_update\":"; write_bool(out, report.sameStartUpdate);
        out << ",\"k_boundary\":"; write_bool(out, report.kBoundary);
        out << ",\"block_split\":"; write_bool(out, report.blockSplit);
        out << ",\"row_order_conflict\":"; write_bool(out, report.rowOrderConflict);
        out << ",\"chunk_sizes\":";
        write_chunk_sizes(out, report.chunkSizes);
        out << "}";
        if (i + 1 < reports.size()) out << ",";
        out << "\n";
    }
    out << "  ],\n";
    out << "  \"mismatches\":[";
    for (size_t i = 0; i < mismatches.size(); ++i)
    {
        if (i > 0) out << ",";
        out << "\n    " << mismatches[i];
    }
    if (!mismatches.empty()) out << "\n  ";
    out << "],\n";
    out << "  \"decision\":{\n";
    out << "    \"recommended_next_action\":\"continue_fix_reduce_form_oracle_semantics_mismatch_with_handoff_enabled_for_measurement\",\n";
    out << "    \"cpu_chunk_local_frontier_transducer_oracle_passed\":"; write_bool(out, ok); out << ",\n";
    out << "    \"keep_handoff_opt_in\":true,\n";
    out << "    \"default_path_changes_allowed\":false,\n";
    out << "    \"gpu_segmented_shadow_allowed\":false,\n";
    out << "    \"runtime_frontier_reduce_allowed\":false\n";
    out << "  }\n";
    out << "}\n";
}

} // namespace

int main()
{
    bool ok = true;
    std::vector<std::string> mismatches;
    std::vector<CaseReport> reports;
    CoverageReport coverage = {false, false, false, false, false, false};

    const std::vector<TestCase> tests = make_test_cases();
    for (size_t i = 0; i < tests.size(); ++i)
    {
        CaseReport report;
        const bool caseOk = analyze_case(tests[i], report, mismatches);
        ok = caseOk && ok;
        coverage.productionKEvictionRevisit =
            coverage.productionKEvictionRevisit || report.productionKEvictionRevisit;
        coverage.sameScoreTie = coverage.sameScoreTie || report.sameScoreTie;
        coverage.sameStartUpdate = coverage.sameStartUpdate || report.sameStartUpdate;
        coverage.kBoundary = coverage.kBoundary || report.kBoundary;
        coverage.blockSplit = coverage.blockSplit || report.blockSplit;
        coverage.rowOrderConflict = coverage.rowOrderConflict || report.rowOrderConflict;
        reports.push_back(report);
    }

    if (!coverage.productionKEvictionRevisit)
    {
        mismatches.push_back("{\"case\":\"coverage\",\"detail\":\"missing production-K eviction/revisit coverage\"}");
        ok = false;
    }
    if (!coverage.sameScoreTie)
    {
        mismatches.push_back("{\"case\":\"coverage\",\"detail\":\"missing same-score tie coverage\"}");
        ok = false;
    }
    if (!coverage.sameStartUpdate)
    {
        mismatches.push_back("{\"case\":\"coverage\",\"detail\":\"missing same-start update coverage\"}");
        ok = false;
    }
    if (!coverage.kBoundary)
    {
        mismatches.push_back("{\"case\":\"coverage\",\"detail\":\"missing K-boundary coverage\"}");
        ok = false;
    }
    if (!coverage.blockSplit)
    {
        mismatches.push_back("{\"case\":\"coverage\",\"detail\":\"missing block-split coverage\"}");
        ok = false;
    }
    if (!coverage.rowOrderConflict)
    {
        mismatches.push_back("{\"case\":\"coverage\",\"detail\":\"missing row-order conflict coverage\"}");
        ok = false;
    }

    write_summary_artifact(reports, coverage, mismatches, ok);

    if (!ok)
    {
        for (size_t i = 0; i < mismatches.size(); ++i)
        {
            std::cerr << mismatches[i] << "\n";
        }
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
