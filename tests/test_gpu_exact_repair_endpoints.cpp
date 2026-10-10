#include "fasim/gasal2_align_bridge.h"
#include "fasim/gpu_exact_batch.h"
#include "fasim/ssw_cpp.h"
#include "fasim/ssw.h"
#include <algorithm>
#include "fasim/rules.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <cstdlib>

static std::string unhex(const std::string &s) {
    std::string result;
    for (size_t i = 0; i < s.size(); i += 2)
        result.push_back(static_cast<char>(std::stoul(s.substr(i, 2), NULL, 16)));
    return result;
}
static std::vector<int8_t> encode(const std::string &s) {
    std::vector<int8_t> result;
    for (char c : s) {
        const size_t i = std::string("ACGT").find(std::toupper(static_cast<unsigned char>(c)));
        result.push_back(c == 'U' || c == 'u' ? 0 : i < 4 ? i : 4);
    }
    return result;
}

static bool alignment_equal(const StripedSmithWaterman::Alignment &a,
                            const StripedSmithWaterman::Alignment &b) {
    return a.sw_score == b.sw_score && a.sw_score_next_best == b.sw_score_next_best &&
        a.query_begin == b.query_begin && a.query_end == b.query_end &&
        a.ref_begin == b.ref_begin && a.ref_end == b.ref_end &&
        a.ref_end_next_best == b.ref_end_next_best && a.mismatches == b.mismatches &&
        a.cigar == b.cigar && a.cigar_string == b.cigar_string;
}

static void check_prepared_query_lifetime() {
    using namespace StripedSmithWaterman;
    Aligner aligner, other;
    ForwardQueryContext prepared;
    ForwardEndpoint endpoint;
    Filter filter;
    Alignment actual, expected;
    if (aligner.AlignFromForward(prepared, "A", 1, filter, endpoint, &actual, 15))
        throw std::runtime_error("unprepared query accepted");
    std::string source(129, 'A');
    if (!aligner.PrepareForwardQuery(source.c_str(), &prepared))
        throw std::runtime_error("prepare failed");
    source.assign(129, 'C'); // Prepared data must own its input.
    const std::string query(129, 'A');
    if (!prepared.MatchesQuery(query) || prepared.MatchesQuery(source))
        throw std::runtime_error("prepared query identity/lifetime mismatch");
    for (int pass = 0; pass < 3; ++pass) {
        for (int length : {1, 49, 50, 51, 129}) {
            const std::string storage = "GG" + std::string(length, 'A') + "CC";
            endpoint.score1 = length * 5;
            endpoint.query_end1 = endpoint.ref_end1 = length - 1;
            endpoint.numeric_path = length >= 51 ? 2 : 1;
            if (!aligner.AlignFromForward(query.c_str(), storage.data() + 2, length,
                    filter, endpoint, &expected, 15) ||
                !aligner.AlignFromForward(prepared, storage.data() + 2, length,
                    filter, endpoint, &actual, 15) || !alignment_equal(expected, actual))
                throw std::runtime_error("reused byte/word or nonterminated view differs");
        }
    }
    if (other.AlignFromForward(prepared, query.data(), query.size(), filter, endpoint, &actual, 15))
        throw std::runtime_error("wrong query owner accepted");
    aligner.Clear();
    if (aligner.AlignFromForward(prepared, query.data(), query.size(), filter, endpoint, &actual, 15))
        throw std::runtime_error("cleared aligner accepted prepared query");
    if (!aligner.ReBuild(5, 4, 16, 4) ||
        aligner.AlignFromForward(prepared, query.data(), query.size(), filter, endpoint, &actual, 15))
        throw std::runtime_error("rebuilt aligner accepted stale prepared query");
    if (!aligner.PrepareForwardQuery(source.c_str(), &prepared) ||
        !aligner.AlignFromForward(prepared, source.data(), source.size(), filter, endpoint, &actual, 15) ||
        !aligner.AlignFromForward(source.c_str(), source.data(), source.size(), filter, endpoint, &expected, 15) ||
        !alignment_equal(expected, actual))
        throw std::runtime_error("query replacement differs");
    for (int invalid : {-1, 65536}) {
        endpoint.score1 = invalid;
        if (aligner.AlignFromForward(prepared, source.data(), source.size(), filter, endpoint, &actual, 15))
            throw std::runtime_error("invalid forward score accepted");
    }
    if (aligner.PrepareForwardQuery("", &prepared) || prepared.MatchesQuery(source) ||
        aligner.PrepareForwardQuery(NULL, &prepared))
        throw std::runtime_error("failed preparation retained stale state");
    std::cerr << "prepared_query_ownership_reuse_numeric_rebuild_guards=pass\n";
}

static void check_batch_planner() {
    const std::string query(129, 'A'), target(129, 'A');
    const std::vector<StripedSmithWaterman::scoreInfo> infos = {{61, 100}};
    FasimGpuExactAttemptWindow window;
    if (!window.append(11, query, target, infos, 20, 7) || window.attempt_count != 4)
        throw std::runtime_error("planner lost the historical four rounds");
    const int lengths[] = {61, 37, 27, 21};
    const int starts[] = {40, 64, 74, 80};
    for (size_t i = 0; i < 4; ++i) {
        const auto &a = window.tasks[0].attempts[i];
        if (a.cutlength != lengths[i] || a.start != starts[i] ||
            a.identity_round != static_cast<int>(i) || a.target_source != &target ||
            a.target_offset != static_cast<size_t>(starts[i]))
            throw std::runtime_error("frozen attempt geometry changed");
    }
    if (window.append(12, query, target, infos, 20, 7) || window.attempt_count != 4)
        throw std::runtime_error("batch limit lost a task boundary");
    FasimGpuExactAttemptWindow oversized;
    if (!oversized.append(12, query, target, infos, 20, 1) || oversized.attempt_count != 4)
        throw std::runtime_error("single oversized task was dropped");
    if (window.tasks[0].matches(query, target, infos, 20))
        throw std::runtime_error("unscored task was marked ready");
    std::cerr << "cross_task_planner_boundaries=pass\n";
}

#ifndef FASIM_REPAIR_TEST_CPU_ONLY
static void check_cross_task_batches() {
    const std::string query(129, 'A');
    const std::vector<std::string> targets = {
        "A", "", std::string(17, 'A'), std::string(50, 'A'),
        std::string(51, 'A'), std::string(129, 'A'), "CCCAAAUUuNAAA",
        std::string(70, 'C'), "", "NAAANAAANAAA"
    };
    std::vector<std::vector<StripedSmithWaterman::scoreInfo> > infos(targets.size());
    std::vector<std::vector<FasimGasal2StreamedAttemptScore> > expected(targets.size());
    std::string error;
    for (size_t t = 0; t < targets.size(); ++t) {
        if (targets[t].empty()) continue;
        infos[t] = {{645, static_cast<int>(targets[t].size()) - 1},
                    {20, static_cast<int>(targets[t].size()) - 1}};
        std::vector<FasimGasal2Attempt> attempts;
        fasim_gpu_exact_plan_attempts(targets[t], infos[t], 20, attempts);
        if (!fasim_gasal2_streamed_attempt_score_v1(query, attempts, &expected[t], NULL, &error))
            throw std::runtime_error("serial batch control: " + error);
    }
    for (int limit : {1, 7, 16, 1024, 4096, 8192}) {
        const std::string setting = std::to_string(limit);
        setenv("FASIM_LONG_QUERY_STREAMED_ATTEMPT_BATCH", setting.c_str(), 1);
        for (size_t begin = 0; begin < targets.size();) {
            FasimGpuExactAttemptWindow window;
            size_t end = begin;
            while (end < targets.size() && window.append(100 + end, query, targets[end],
                   infos[end], 20, limit)) {
                ++end;
                if (window.attempt_count >= static_cast<size_t>(limit)) break;
            }
            if (!window.score(&error)) throw std::runtime_error("cross-task batch: " + error);
            uint64_t batches = 0, requests = 0;
            for (size_t t = begin; t < end; ++t) {
                const auto &task = window.tasks[t - begin];
                if (task.task_index != 100 + t || !task.matches(query, targets[t], infos[t], 20) ||
                    task.endpoints.size() != expected[t].size())
                    throw std::runtime_error("cross-task mapping mismatch");
                if (task.matches(query, targets[t], infos[t], 21))
                    throw std::runtime_error("prepared task accepted the wrong context");
                for (size_t i = 0; i < expected[t].size(); ++i) {
                    const auto &a = expected[t][i], &b = task.endpoints[i];
                    if (a.score != b.score || a.query_end != b.query_end ||
                        a.ref_end_local != b.ref_end_local || a.ref_end_global != b.ref_end_global ||
                        a.numeric_path != b.numeric_path)
                        throw std::runtime_error("cross-task endpoint tuple mismatch");
                }
                batches += task.telemetry.batches;
                requests += task.telemetry.gpu_scored_requests;
            }
            if (batches != window.telemetry.batches || requests != window.attempt_count)
                throw std::runtime_error("batch telemetry double-counted or missing");
            begin = end;
        }
    }
    unsetenv("FASIM_LONG_QUERY_STREAMED_ATTEMPT_BATCH");
    FasimGpuExactAttemptWindow empty;
    if (empty.score(&error)) throw std::runtime_error("empty window accepted");
    const std::string anotherQuery = query;
    FasimGpuExactAttemptWindow mixed;
    mixed.append(1, query, targets[0], infos[0], 20, 4096);
    mixed.append(2, anotherQuery, targets[2], infos[2], 20, 4096);
    if (mixed.score(&error)) throw std::runtime_error("mixed query contexts accepted");
    std::cerr << "cross_task_ragged_numeric_mapping=pass limits=1,7,16,1024,4096,8192\n";
}

static void check_selection() {
    setenv("FASIM_ALIGN_GASAL2", "1", 1);
    const char *targets[] = {"A", "AA", "AAA", "AAAA", "AAA", "AAAT", "AAT", "CCCC", "GGGG"};
    const int groups[] = {0, 0, 0, 1, 1, 2, 2, 3, 3};
    std::vector<FasimGasal2Attempt> attempts;
    for (int i = 0; i < 9; ++i) {
        FasimGasal2Attempt attempt;
        attempt.scoreinfo_index = groups[i];
        attempt.target = targets[i];
        attempt.cutlength = attempt.target.size();
        attempt.prealign_score = i < 3 ? 5 : 100;
        attempt.target_end_required_for_fallback = attempt.cutlength - 1;
        attempts.push_back(attempt);
    }
    std::vector<FasimGasal2SelectedAlignment> with, without, strict;
    std::vector<FasimGasal2AttemptScoreTelemetry> telemetry;
    std::string error;
    if (!fasim_gasal2_select_attempts_canonical_hybrid_v2("AAAA", attempts, &with, &telemetry, &error) ||
        !fasim_gasal2_select_attempts_canonical_hybrid_v2("AAAA", attempts, &without, NULL, &error) ||
        !fasim_gasal2_select_attempts_strict("AAAA", attempts, &strict, &error))
        throw std::runtime_error("selection call: " + error);
    const int expected[] = {0, 3, 6};
    for (const auto &selected : {with, without, strict}) {
        if (selected.size() != 3) throw std::runtime_error("strict selection count changed with telemetry");
        for (int i = 0; i < 3; ++i)
            if (selected[i].attempt_index != expected[i])
                throw std::runtime_error("strict threshold/best/last selection differs");
    }
    if (telemetry.size() != attempts.size()) throw std::runtime_error("selection telemetry missing");
    for (size_t i = 0; i < telemetry.size(); ++i)
        if (telemetry[i].selected != (i == 0 || i == 3 || i == 6))
            throw std::runtime_error("telemetry selected field includes an unselected attempt");
    std::cerr << "strict_selection_telemetry=pass\n";
}

static void check_ragged_batch() {
    const std::string query(129, 'A');
    std::vector<FasimGasal2Attempt> attempts;
    for (int length : {1, 15, 16, 17, 49, 50, 51, 52, 65, 129}) {
        FasimGasal2Attempt attempt;
        attempt.target.assign(length, 'A');
        attempt.cutlength = length;
        attempts.push_back(attempt);
    }
    std::vector<FasimGasal2StreamedAttemptScore> endpoints;
    FasimGasal2StreamedAttemptScoreTelemetry telemetry;
    std::string error;
    if (!fasim_gasal2_streamed_attempt_score_v1(query, attempts, &endpoints, &telemetry, &error) ||
        endpoints.size() != attempts.size()) throw std::runtime_error("ragged batch: " + error);
    for (size_t i = 0; i < attempts.size(); ++i) {
        const int length = attempts[i].cutlength;
        if (endpoints[i].score != length * 5 || endpoints[i].ref_end_local != length - 1 ||
            endpoints[i].query_end != length - 1 || endpoints[i].numeric_path != (length >= 51 ? 2 : 1))
            throw std::runtime_error("ragged mixed byte/word endpoint mismatch");
    }
    std::cerr << "ragged_mixed_numeric_batch=pass\n";
}
#endif

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    check_prepared_query_lifetime();
    check_batch_planner();
#ifndef FASIM_REPAIR_TEST_CPU_ONLY
    check_selection();
    check_ragged_batch();
    check_cross_task_batches();
#endif
    std::ifstream input(argv[1]);
    std::string line;
    std::getline(input, line);
    const bool mixed = line.find("transform_enabled") != std::string::npos;
    StripedSmithWaterman::Aligner aligner;
    StripedSmithWaterman::Filter filter;
    int failures = 0, cases = 0;
    ssw_align_internal_stats_set_enabled(1);
    int8_t matrix[25];
    for (int i = 0; i < 5; ++i)
        for (int j = 0; j < 5; ++j) matrix[i * 5 + j] = i == j && i < 4 ? 5 : -4;
    std::cout << "case_id\tforward_equal\tcontinuation_equal\tcpu_score\tgpu_score\tcpu_begin\tgpu_begin\tnumeric_equal\tnumeric_path\tprepared_equal\n";
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        std::vector<std::string> fields;
        std::istringstream stream(line);
        std::string field;
        while (std::getline(stream, field, '\t')) fields.push_back(field);
        if (fields.size() < 4) return 2;
        const std::string query = unhex(fields[2]);
        std::string target = unhex(fields[3]);
        if (fields.size() > 4 && (!mixed || fields[4] == "1")) {
            const size_t offset = mixed ? 1 : 0;
            target = transferStringTableOptIn(target, std::stoi(fields[4 + offset]),
                std::stoi(fields[5 + offset]), std::stoi(fields[6 + offset]));
        }
        const auto q = encode(query), r = encode(target);
        s_profile *profile = ssw_init(q.data(), q.size(), matrix, 5, 2);
        const auto before = ssw_align_internal_stats_snapshot();
        s_align *forward = ssw_align(profile, r.data(), r.size(), 16, 4, 0, 0, 32767, 15);
        const auto after = ssw_align_internal_stats_snapshot();
        const int expected_numeric = after.word_path_nanoseconds > before.word_path_nanoseconds ? 2 : 1;
#ifdef FASIM_REPAIR_TEST_CPU_ONLY
        FasimGasal2StreamedAttemptScore gpu;
        gpu.score = forward->score1;
        gpu.query_end = forward->read_end1;
        gpu.ref_end_local = forward->ref_end1;
        gpu.numeric_path = expected_numeric;
#else
        FasimGasal2Attempt attempt;
        attempt.start = 0;
        attempt.cutlength = target.size();
        attempt.set_target_view(&target, 0, target.size());
        std::vector<FasimGasal2StreamedAttemptScore> endpoints;
        FasimGasal2StreamedAttemptScoreTelemetry telemetry;
        std::string error;
        if (!fasim_gasal2_streamed_attempt_score_v1(query, {attempt}, &endpoints, &telemetry, &error)) {
            std::cerr << fields[0] << ": " << error << '\n'; return 2;
        }
        const auto &gpu = endpoints.at(0);
#endif
        const bool numeric_equal = gpu.numeric_path == expected_numeric;
        const bool forward_equal = forward && gpu.score == forward->score1 &&
            gpu.query_end == forward->read_end1 && gpu.ref_end_local == forward->ref_end1;
        StripedSmithWaterman::Alignment authority, continuation;
        aligner.Align(query.c_str(), target.c_str(), target.size(), filter, &authority, 15);
        StripedSmithWaterman::ForwardEndpoint endpoint;
        endpoint.score1 = gpu.score;
        endpoint.query_end1 = gpu.query_end;
        endpoint.ref_end1 = gpu.ref_end_local;
        endpoint.score2 = 0;
        endpoint.ref_end2 = -1;
        endpoint.numeric_path = gpu.numeric_path;
        const bool continued = aligner.AlignFromForward(query.c_str(), target.c_str(),
            target.size(), filter, endpoint, &continuation, 15);
        const bool continuation_equal = continued && authority.sw_score == continuation.sw_score &&
            authority.query_begin == continuation.query_begin && authority.ref_begin == continuation.ref_begin &&
            authority.query_end == continuation.query_end && authority.ref_end == continuation.ref_end &&
            authority.cigar == continuation.cigar;
        StripedSmithWaterman::ForwardQueryContext prepared;
        StripedSmithWaterman::Alignment reused;
        const bool prepared_equal = aligner.PrepareForwardQuery(query.c_str(), &prepared) &&
            aligner.AlignFromForward(prepared, target.c_str(), target.size(),
                filter, endpoint, &reused, 15) && alignment_equal(continuation, reused);
        std::cout << fields[0] << '\t' << forward_equal << '\t' << continuation_equal << '\t'
            << authority.sw_score << '\t' << gpu.score << '\t' << authority.ref_begin << '\t'
            << continuation.ref_begin << '\t' << numeric_equal << '\t' << gpu.numeric_path << '\t'
            << prepared_equal << '\n';
        failures += !forward_equal || !continuation_equal || !numeric_equal || !prepared_equal;
        ++cases;
        align_destroy(forward);
        init_destroy(profile);
    }
    std::cerr << "cases=" << cases << " failures=" << failures << '\n';
    return failures != 0;
}
