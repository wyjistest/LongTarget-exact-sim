#include "fasim/gasal2_align_bridge.h"
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

#ifndef FASIM_REPAIR_TEST_CPU_ONLY
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
#ifndef FASIM_REPAIR_TEST_CPU_ONLY
    check_selection();
    check_ragged_batch();
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
    std::cout << "case_id\tforward_equal\tcontinuation_equal\tcpu_score\tgpu_score\tcpu_begin\tgpu_begin\tnumeric_equal\tnumeric_path\n";
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
        std::cout << fields[0] << '\t' << forward_equal << '\t' << continuation_equal << '\t'
            << authority.sw_score << '\t' << gpu.score << '\t' << authority.ref_begin << '\t'
            << continuation.ref_begin << '\t' << numeric_equal << '\t' << gpu.numeric_path << '\n';
        failures += !forward_equal || !continuation_equal || !numeric_equal;
        ++cases;
        align_destroy(forward);
        init_destroy(profile);
    }
    std::cerr << "cases=" << cases << " failures=" << failures << '\n';
    return failures != 0;
}
