#include "fasim/ssw.h"
#include "fasim/ssw_cpp.h"
#include "fasim/ssw_cuda/ssw_cuda_api.h"
#include "fasim/ssw_cuda/ssw_cuda_forward_hybrid.h"

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

#include "fasim/rules.h"

namespace
{

struct RawCase
{
    std::string case_id;
    int threshold;
    std::string query;
    std::string reference;
};

std::vector<std::string> split_tab(const std::string &line)
{
    std::vector<std::string> fields;
    size_t begin = 0;
    while(true)
    {
        const size_t end = line.find('\t', begin);
        fields.push_back(line.substr(begin, end == std::string::npos ? end : end - begin));
        if(end == std::string::npos) break;
        begin = end + 1;
    }
    return fields;
}

int hex_nibble(char value)
{
    if(value >= '0' && value <= '9') return value - '0';
    if(value >= 'a' && value <= 'f') return value - 'a' + 10;
    if(value >= 'A' && value <= 'F') return value - 'A' + 10;
    return -1;
}

std::string decode_hex(const std::string &value)
{
    if(value.size() % 2 != 0) throw std::runtime_error("hex payload has odd length");
    std::string output;
    output.reserve(value.size() / 2);
    for(size_t index = 0; index < value.size(); index += 2)
    {
        const int high = hex_nibble(value[index]);
        const int low = hex_nibble(value[index + 1]);
        if(high < 0 || low < 0)
            throw std::runtime_error("hex payload contains a non-hex character");
        output.push_back(static_cast<char>((high << 4) | low));
    }
    return output;
}

long parse_nonnegative(const std::string &value, const char *label, size_t line_number)
{
    char *end = NULL;
    const long parsed = std::strtol(value.c_str(), &end, 10);
    if(end == value.c_str() || *end != '\0' || parsed < 0 ||
       parsed > std::numeric_limits<int>::max())
        throw std::runtime_error(std::string("invalid ") + label +
                                 " at line " + std::to_string(line_number));
    return parsed;
}

std::vector<RawCase> read_cases(const std::string &path)
{
    std::ifstream handle(path.c_str(), std::ios::binary);
    if(!handle) throw std::runtime_error("cannot open input TSV: " + path);
    std::string line;
    if(!std::getline(handle, line)) throw std::runtime_error("input TSV header drift");
    const bool legacy_transform =
        line == "case_id\tthreshold\tquery_hex\treference_hex\ttransform_strand\ttransform_para\ttransform_rule";
    const bool mixed_transform =
        line == "case_id\tthreshold\tquery_hex\treference_hex\ttransform_enabled\ttransform_strand\ttransform_para\ttransform_rule";
    if(!legacy_transform && !mixed_transform &&
       line != "case_id\tthreshold\tquery_hex\treference_hex")
        throw std::runtime_error("input TSV header drift");

    std::vector<RawCase> cases;
    size_t line_number = 1;
    while(std::getline(handle, line))
    {
        ++line_number;
        if(line.empty()) continue;
        const std::vector<std::string> fields = split_tab(line);
        const size_t expected = mixed_transform ? 8U : (legacy_transform ? 7U : 4U);
        if(fields.size() != expected || fields[0].empty())
            throw std::runtime_error("invalid TSV row at line " + std::to_string(line_number));
        RawCase item;
        item.case_id = fields[0];
        item.threshold = static_cast<int>(parse_nonnegative(fields[1], "threshold", line_number));
        item.query = decode_hex(fields[2]);
        item.reference = decode_hex(fields[3]);
        const bool transform = legacy_transform ||
            (mixed_transform && parse_nonnegative(fields[4], "transform_enabled", line_number) == 1);
        if(transform)
        {
            const size_t offset = mixed_transform ? 1U : 0U;
            const int strand = static_cast<int>(parse_nonnegative(
                fields[4 + offset], "transform_strand", line_number));
            const int para = std::atoi(fields[5 + offset].c_str());
            const int rule = static_cast<int>(parse_nonnegative(
                fields[6 + offset], "transform_rule", line_number));
            item.reference = transferStringTableOptIn(item.reference, strand, para, rule);
        }
        cases.push_back(item);
    }
    if(cases.empty()) throw std::runtime_error("input TSV contains no cases");
    return cases;
}

std::vector<uint8_t> translate_cuda(const std::string &sequence)
{
    std::vector<uint8_t> output;
    output.reserve(sequence.size());
    for(size_t index = 0; index < sequence.size(); ++index)
    {
        switch(static_cast<unsigned char>(sequence[index]))
        {
        case 'A': case 'a': case 'U': case 'u': output.push_back(0); break;
        case 'C': case 'c': output.push_back(1); break;
        case 'G': case 'g': output.push_back(2); break;
        case 'T': case 't': output.push_back(3); break;
        default: output.push_back(4); break;
        }
    }
    return output;
}

std::vector<int8_t> translate_cpu(const std::string &sequence)
{
    const std::vector<uint8_t> source = translate_cuda(sequence);
    return std::vector<int8_t>(source.begin(), source.end());
}

void build_matrix(int8_t *matrix)
{
    int index = 0;
    for(int row = 0; row < 5; ++row)
        for(int column = 0; column < 5; ++column)
            matrix[index++] = row < 4 && row == column ? 5 : -4;
}

bool cigar_equal(const s_align *left, const s_align *right)
{
    return left->cigarLen == right->cigarLen &&
        (left->cigarLen == 0 ||
         std::memcmp(left->cigar, right->cigar,
                     static_cast<size_t>(left->cigarLen) * sizeof(uint32_t)) == 0);
}

bool alignment_equal(const s_align *left, const s_align *right)
{
    return left != NULL && right != NULL &&
        left->score1 == right->score1 && left->score2 == right->score2 &&
        left->ref_begin1 == right->ref_begin1 && left->ref_end1 == right->ref_end1 &&
        left->read_begin1 == right->read_begin1 && left->read_end1 == right->read_end1 &&
        left->ref_end2 == right->ref_end2 && cigar_equal(left, right);
}

bool alignment_equal(const StripedSmithWaterman::Alignment &left,
                     const StripedSmithWaterman::Alignment &right)
{
    return left.sw_score == right.sw_score &&
        left.sw_score_next_best == right.sw_score_next_best &&
        left.ref_begin == right.ref_begin && left.ref_end == right.ref_end &&
        left.query_begin == right.query_begin && left.query_end == right.query_end &&
        left.ref_end_next_best == right.ref_end_next_best &&
        left.cigar == right.cigar && left.cigar_string == right.cigar_string;
}

std::string cigar_text(const s_align *alignment)
{
    if(alignment == NULL) return "NA";
    std::string result;
    for(int32_t index = 0; index < alignment->cigarLen; ++index)
    {
        result += std::to_string(cigar_int_to_len(alignment->cigar[index]));
        result.push_back(cigar_int_to_op(alignment->cigar[index]));
    }
    return result.empty() ? "none" : result;
}

uint64_t delta(uint64_t after, uint64_t before)
{
    if(after < before) throw std::runtime_error("internal counter moved backwards");
    return after - before;
}

int run_batch(const std::string &input_path, int device)
{
    const std::vector<RawCase> cases = read_cases(input_path);
    std::vector<fasim_ssw_cuda::TaskInput> tasks;
    tasks.reserve(cases.size());
    for(size_t index = 0; index < cases.size(); ++index)
    {
        fasim_ssw_cuda::TaskInput task;
        task.case_id = cases[index].case_id;
        task.query = translate_cuda(cases[index].query);
        task.reference = translate_cuda(cases[index].reference);
        task.threshold = cases[index].threshold;
        tasks.push_back(task);
    }

    fasim_ssw_cuda::BatchOptions options;
    options.device = device;
    options.export_full_column_vectors = false;
    fasim_ssw_cuda::ForwardBatchOutput gpu;
    const fasim_ssw_cuda::StatusCode gpu_status =
        fasim_ssw_cuda::forward_align(tasks, options, &gpu);
    if(gpu_status != fasim_ssw_cuda::STATUS_OK)
    {
        std::cerr << "forward_status=" << fasim_ssw_cuda::status_name(gpu_status)
                  << " error=" << gpu.error << "\n";
        return 2;
    }
    if(gpu.endpoints.size() != cases.size())
        throw std::runtime_error("GPU endpoint cardinality drift");

    int8_t matrix[25];
    build_matrix(matrix);
    bool all_equal = gpu.telemetry.cpu_endpoint_calls == 0;
    std::cout << "case_id\tnumeric_path\tauthority_score1\tcontinuation_score1"
                 "\tauthority_ref_begin1\tcontinuation_ref_begin1"
                 "\tauthority_ref_end1\tcontinuation_ref_end1"
                 "\tauthority_read_begin1\tcontinuation_read_begin1"
                 "\tauthority_read_end1\tcontinuation_read_end1"
                 "\tauthority_score2\tcontinuation_score2"
                 "\tauthority_ref_end2\tcontinuation_ref_end2"
                 "\tauthority_cigar_len\tcontinuation_cigar_len"
                 "\tauthority_cigar\tcontinuation_cigar"
                 "\traw_equal\twrapper_equal\tcpu_forward_calls\tcpu_reverse_calls"
                 "\tcpu_banded_sw_calls\tgpu_cpu_endpoint_calls\n";

    for(size_t index = 0; index < cases.size(); ++index)
    {
        const std::vector<int8_t> query = translate_cpu(cases[index].query);
        const std::vector<int8_t> reference = translate_cpu(cases[index].reference);
        s_profile *profile = ssw_init(query.data(), static_cast<int32_t>(query.size()),
                                      matrix, 5, 2);
        if(profile == NULL) throw std::runtime_error("ssw_init failed");
        s_align *authority = ssw_align(profile, reference.data(),
            static_cast<int32_t>(reference.size()), 16, 4, 15, 0, 32767, 15);
        if(authority == NULL) throw std::runtime_error("authority alignment failed");

        const fasim_ssw_cuda::ForwardEndpoint &source = gpu.endpoints[index];
        ssw_forward_endpoint endpoint;
        endpoint.score1 = static_cast<uint16_t>(source.score1);
        endpoint.score2 = static_cast<uint16_t>(source.score2);
        endpoint.ref_end1 = source.ref_end1;
        endpoint.read_end1 = source.read_end1;
        endpoint.ref_end2 = source.ref_end2;
        endpoint.numeric_path = source.numeric_path == fasim_ssw_cuda::NUMERIC_PATH_BYTE8 ?
            SSW_FORWARD_NUMERIC_PATH_BYTE8 : SSW_FORWARD_NUMERIC_PATH_WORD16;

        const ssw_align_internal_stats before = ssw_align_internal_stats_snapshot();
        const uint8_t prior_stats = ssw_align_internal_stats_enabled();
        ssw_align_internal_stats_set_enabled(1);
        s_align *continuation = ssw_align_from_forward(profile, reference.data(),
            static_cast<int32_t>(reference.size()), 16, 4, 15, 0, 32767, 15,
            &endpoint);
        ssw_align_internal_stats_set_enabled(prior_stats);
        const ssw_align_internal_stats after = ssw_align_internal_stats_snapshot();
        const uint64_t forward_calls = delta(after.forward_calls, before.forward_calls);
        const uint64_t reverse_calls = delta(after.reverse_calls, before.reverse_calls);
        const uint64_t banded_calls = delta(after.banded_sw_calls, before.banded_sw_calls);
        const bool equal = alignment_equal(authority, continuation);
        const bool positive_alignment = source.score1 > 0;
        const bool counters_exact = forward_calls == 0 &&
            reverse_calls == (positive_alignment ? 1U : 0U) &&
            banded_calls == (positive_alignment ? 1U : 0U);
        StripedSmithWaterman::Aligner wrapper_aligner;
        StripedSmithWaterman::Filter wrapper_filter;
        StripedSmithWaterman::Alignment wrapper_authority;
        StripedSmithWaterman::Alignment wrapper_continuation;
        StripedSmithWaterman::ForwardEndpoint wrapper_endpoint;
        wrapper_endpoint.score1 = source.score1;
        wrapper_endpoint.score2 = source.score2;
        wrapper_endpoint.ref_end1 = source.ref_end1;
        wrapper_endpoint.query_end1 = source.read_end1;
        wrapper_endpoint.ref_end2 = source.ref_end2;
        wrapper_endpoint.numeric_path = endpoint.numeric_path;
        const bool wrapper_ok = wrapper_aligner.Align(
            cases[index].query.c_str(), cases[index].reference.c_str(),
            static_cast<int>(cases[index].reference.size()), wrapper_filter,
            &wrapper_authority, 15) &&
            wrapper_aligner.AlignFromForward(
                cases[index].query.c_str(), cases[index].reference.c_str(),
                static_cast<int>(cases[index].reference.size()), wrapper_filter,
                wrapper_endpoint, &wrapper_continuation, 15);
        const bool wrapper_equal = wrapper_ok &&
            alignment_equal(wrapper_authority, wrapper_continuation);
        all_equal = all_equal && equal && wrapper_equal && counters_exact;

        std::cout << cases[index].case_id << '\t'
                  << (endpoint.numeric_path == SSW_FORWARD_NUMERIC_PATH_BYTE8 ? "byte8" : "word16")
                  << '\t' << authority->score1 << '\t' << (continuation ? continuation->score1 : 0)
                  << '\t' << authority->ref_begin1 << '\t' << (continuation ? continuation->ref_begin1 : -1)
                  << '\t' << authority->ref_end1 << '\t' << (continuation ? continuation->ref_end1 : -1)
                  << '\t' << authority->read_begin1 << '\t' << (continuation ? continuation->read_begin1 : -1)
                  << '\t' << authority->read_end1 << '\t' << (continuation ? continuation->read_end1 : -1)
                  << '\t' << authority->score2 << '\t' << (continuation ? continuation->score2 : 0)
                  << '\t' << authority->ref_end2 << '\t' << (continuation ? continuation->ref_end2 : -1)
                  << '\t' << authority->cigarLen << '\t' << (continuation ? continuation->cigarLen : 0)
                  << '\t' << cigar_text(authority) << '\t' << cigar_text(continuation)
                  << '\t' << (equal ? 1 : 0) << '\t' << (wrapper_equal ? 1 : 0)
                  << '\t' << forward_calls << '\t'
                  << reverse_calls << '\t' << banded_calls << '\t'
                  << gpu.telemetry.cpu_endpoint_calls << '\n';
        align_destroy(authority);
        if(continuation != NULL) align_destroy(continuation);
        init_destroy(profile);
    }
    return all_equal ? 0 : 1;
}

int invalid_probe(const std::string &name)
{
    const std::vector<int8_t> query = translate_cpu("ACGT");
    const std::vector<int8_t> reference = translate_cpu("ACGT");
    int8_t matrix[25];
    build_matrix(matrix);
    s_profile *profile = ssw_init(query.data(), 4, matrix, 5, 2);
    ssw_forward_endpoint endpoint = {20, 0, 3, 3, -1, SSW_FORWARD_NUMERIC_PATH_BYTE8};
    const s_profile *actual_profile = profile;
    const int8_t *actual_reference = reference.data();
    const ssw_forward_endpoint *actual_endpoint = &endpoint;
    int32_t reference_length = 4;
    if(name == "null_profile") actual_profile = NULL;
    else if(name == "null_reference") actual_reference = NULL;
    else if(name == "null_endpoint") actual_endpoint = NULL;
    else if(name == "bad_ref_end") endpoint.ref_end1 = 4;
    else if(name == "bad_read_end") endpoint.read_end1 = 4;
    else if(name == "bad_second_end") endpoint.ref_end2 = 4;
    else if(name == "bad_numeric_path") endpoint.numeric_path = 99;
    else if(name == "empty_reference") reference_length = 0;
    else throw std::runtime_error("unknown invalid probe: " + name);
    s_align *result = ssw_align_from_forward(actual_profile, actual_reference,
        reference_length, 16, 4, 15, 0, 32767, 15, actual_endpoint);
    std::cout << "probe=" << name << " rejected=" << (result == NULL ? 1 : 0) << "\n";
    if(result != NULL) align_destroy(result);
    init_destroy(profile);
    return result == NULL ? 0 : 1;
}

struct CpuSelectedAttempt
{
    CpuSelectedAttempt():selected(false), start(0), cutlength(0), reason(0) {}
    bool selected;
    int start;
    int cutlength;
    int reason;
    StripedSmithWaterman::Alignment alignment;
};

int run_hybrid_batch(const std::string &input_path, int device)
{
    const std::vector<RawCase> cases = read_cases(input_path);
    std::vector<fasim_ssw_cuda::ForwardHybridTask> tasks(cases.size());
    for(size_t index = 0; index < cases.size(); ++index)
    {
        tasks[index].case_id = cases[index].case_id;
        tasks[index].query = cases[index].query;
        tasks[index].reference = cases[index].reference;
        tasks[index].threshold = cases[index].threshold;
    }
    fasim_ssw_cuda::BatchOptions options;
    options.device = device;
    fasim_ssw_cuda::ForwardHybridOutput output;
    const fasim_ssw_cuda::StatusCode status =
        fasim_ssw_cuda::forward_hybrid_select(tasks, options, &output);
    if(status != fasim_ssw_cuda::STATUS_OK)
    {
        std::cerr << "hybrid_status=" << fasim_ssw_cuda::status_name(status)
                  << " error=" << output.error << "\n";
        return 2;
    }

    std::map<std::pair<int, int>, fasim_ssw_cuda::ForwardHybridSelectedAttempt> selected;
    for(size_t index = 0; index < output.selected.size(); ++index)
    {
        const fasim_ssw_cuda::ForwardHybridSelectedAttempt &item = output.selected[index];
        selected[std::make_pair(item.task_index, item.scoreinfo_order)] = item;
    }
    std::cout << "case_id\tscoreinfo_order\tprealign_score\tcpu_selected\tgpu_selected"
                 "\tcpu_start\tgpu_start\tcpu_cutlength\tgpu_cutlength"
                 "\tcpu_reason\tgpu_reason\tendpoint_equal\tcontinuation_equal"
                 "\tcpu_forward_calls\tcpu_reverse_calls\tcpu_banded_sw_calls\n";
    bool all_equal = output.telemetry.cpu_prealign_calls == 0 &&
        output.telemetry.cpu_forward_calls == 0 &&
        output.telemetry.preselect.cpu_endpoint_calls == 0 &&
        output.telemetry.forward.cpu_endpoint_calls == 0;
    size_t expected_scoreinfo_count = 0;
    size_t expected_selected_count = 0;

    for(size_t task_index = 0; task_index < cases.size(); ++task_index)
    {
        StripedSmithWaterman::Aligner aligner;
        StripedSmithWaterman::Filter filter;
        StripedSmithWaterman::Alignment scratch;
        std::vector<StripedSmithWaterman::scoreInfo> scoreinfos;
        if(!aligner.preAlign(cases[task_index].query.c_str(),
                             cases[task_index].reference.c_str(),
                             static_cast<int>(cases[task_index].reference.size()),
                             filter, &scratch, 15, cases[task_index].threshold,
                             scoreinfos, 5, -4))
            throw std::runtime_error("CPU preAlign failed");
        const int begin = output.scoreinfo_offsets[task_index];
        const int end = output.scoreinfo_offsets[task_index + 1];
        const bool scoreinfo_count_equal =
            end - begin == static_cast<int>(scoreinfos.size());
        all_equal = all_equal && scoreinfo_count_equal;
        expected_scoreinfo_count += scoreinfos.size();
        for(size_t scoreinfo_order = 0; scoreinfo_order < scoreinfos.size(); ++scoreinfo_order)
        {
            const StripedSmithWaterman::scoreInfo &scoreinfo = scoreinfos[scoreinfo_order];
            bool scoreinfo_equal = scoreinfo_count_equal;
            if(scoreinfo_equal)
            {
                const fasim_ssw_cuda::ScoreInfo &gpu_scoreinfo =
                    output.scoreinfos[static_cast<size_t>(begin) + scoreinfo_order];
                scoreinfo_equal = gpu_scoreinfo.task_index == static_cast<int>(task_index) &&
                    gpu_scoreinfo.index == static_cast<int>(scoreinfo_order) &&
                    gpu_scoreinfo.score == scoreinfo.score &&
                    gpu_scoreinfo.position == scoreinfo.position;
            }

            CpuSelectedAttempt cpu;
            CpuSelectedAttempt best;
            CpuSelectedAttempt last_nonzero;
            float identity = 0.6f;
            while(identity <= 1.0f)
            {
                int cutlength = static_cast<int>(scoreinfo.score + 24) /
                    (9 * identity - 4) + 1;
                cutlength = scoreinfo.position - cutlength + 1 > 0 ?
                    cutlength : scoreinfo.position + 1;
                const int start = scoreinfo.position - cutlength + 1;
                const std::string window = cases[task_index].reference.substr(
                    static_cast<size_t>(start), static_cast<size_t>(cutlength));
                StripedSmithWaterman::Alignment current;
                if(!aligner.Align(cases[task_index].query.c_str(), window.c_str(),
                                  static_cast<int>(window.size()), filter, &current, 15))
                    throw std::runtime_error("CPU Align failed");
                if(current.sw_score != 0)
                {
                    last_nonzero.selected = true;
                    last_nonzero.start = start;
                    last_nonzero.cutlength = cutlength;
                    last_nonzero.reason = fasim_ssw_cuda::ATTEMPT_LAST;
                    last_nonzero.alignment = current;
                }
                if(current.sw_score >= scoreinfo.score)
                {
                    cpu.selected = true;
                    cpu.start = start;
                    cpu.cutlength = cutlength;
                    cpu.reason = fasim_ssw_cuda::ATTEMPT_THRESHOLD;
                    cpu.alignment = current;
                    break;
                }
                if(current.ref_end == cutlength - 1 &&
                   (!best.selected || current.sw_score > best.alignment.sw_score))
                {
                    best.selected = true;
                    best.start = start;
                    best.cutlength = cutlength;
                    best.reason = fasim_ssw_cuda::ATTEMPT_BEST_FALLBACK;
                    best.alignment = current;
                }
                identity += 0.1f;
            }
            if(!cpu.selected) cpu = best.selected ? best : last_nonzero;
            if(cpu.selected) ++expected_selected_count;

            const std::map<std::pair<int, int>,
                fasim_ssw_cuda::ForwardHybridSelectedAttempt>::const_iterator found =
                selected.find(std::make_pair(static_cast<int>(task_index),
                                             static_cast<int>(scoreinfo_order)));
            const bool gpu_selected = found != selected.end();
            bool endpoint_equal = false;
            bool continuation_equal = false;
            uint64_t forward_calls = 0;
            uint64_t reverse_calls = 0;
            uint64_t banded_calls = 0;
            int gpu_start = -1;
            int gpu_cutlength = 0;
            int gpu_reason = 0;
            if(gpu_selected)
            {
                const fasim_ssw_cuda::ForwardHybridSelectedAttempt &gpu = found->second;
                gpu_start = gpu.start;
                gpu_cutlength = gpu.cutlength;
                gpu_reason = gpu.selection_reason;
                endpoint_equal = cpu.selected &&
                    gpu.endpoint.score1 == cpu.alignment.sw_score &&
                    gpu.endpoint.score2 == cpu.alignment.sw_score_next_best &&
                    gpu.endpoint.ref_end1 == cpu.alignment.ref_end &&
                    gpu.endpoint.read_end1 == cpu.alignment.query_end &&
                    gpu.endpoint.ref_end2 == cpu.alignment.ref_end_next_best;
                StripedSmithWaterman::ForwardEndpoint endpoint;
                endpoint.score1 = gpu.endpoint.score1;
                endpoint.score2 = gpu.endpoint.score2;
                endpoint.ref_end1 = gpu.endpoint.ref_end1;
                endpoint.query_end1 = gpu.endpoint.read_end1;
                endpoint.ref_end2 = gpu.endpoint.ref_end2;
                endpoint.numeric_path = gpu.endpoint.numeric_path;
                const std::string window = cases[task_index].reference.substr(
                    static_cast<size_t>(gpu.start), static_cast<size_t>(gpu.cutlength));
                const ssw_align_internal_stats before = ssw_align_internal_stats_snapshot();
                const uint8_t prior = ssw_align_internal_stats_enabled();
                ssw_align_internal_stats_set_enabled(1);
                StripedSmithWaterman::Alignment canonical;
                const bool continuation_ok = aligner.AlignFromForward(
                    cases[task_index].query.c_str(), window.c_str(),
                    static_cast<int>(window.size()), filter, endpoint, &canonical, 15);
                ssw_align_internal_stats_set_enabled(prior);
                const ssw_align_internal_stats after = ssw_align_internal_stats_snapshot();
                forward_calls = delta(after.forward_calls, before.forward_calls);
                reverse_calls = delta(after.reverse_calls, before.reverse_calls);
                banded_calls = delta(after.banded_sw_calls, before.banded_sw_calls);
                continuation_equal = continuation_ok && cpu.selected &&
                    alignment_equal(cpu.alignment, canonical);
            }
            const bool row_equal = scoreinfo_equal && cpu.selected == gpu_selected &&
                (!cpu.selected ||
                 (cpu.start == gpu_start && cpu.cutlength == gpu_cutlength &&
                  cpu.reason == gpu_reason && endpoint_equal && continuation_equal &&
                  forward_calls == 0 && reverse_calls == 1 && banded_calls == 1));
            all_equal = all_equal && row_equal;
            std::cout << cases[task_index].case_id << '\t' << scoreinfo_order << '\t'
                      << scoreinfo.score << '\t' << (cpu.selected ? 1 : 0) << '\t'
                      << (gpu_selected ? 1 : 0) << '\t' << (cpu.selected ? cpu.start : -1)
                      << '\t' << gpu_start << '\t' << (cpu.selected ? cpu.cutlength : 0)
                      << '\t' << gpu_cutlength << '\t' << (cpu.selected ? cpu.reason : 0)
                      << '\t' << gpu_reason << '\t' << (endpoint_equal ? 1 : 0)
                      << '\t' << (continuation_equal ? 1 : 0) << '\t' << forward_calls
                      << '\t' << reverse_calls << '\t' << banded_calls << '\n';
        }
    }
    all_equal = all_equal && expected_scoreinfo_count == output.scoreinfos.size() &&
        expected_selected_count == output.selected.size();
    return all_equal ? 0 : 1;
}

} // namespace

int main(int argc, char **argv)
{
    try
    {
        std::string input_path;
        bool hybrid = false;
        std::string invalid_name;
        int device = 0;
        for(int index = 1; index < argc; ++index)
        {
            const std::string argument = argv[index];
            if(argument == "--input" && index + 1 < argc) input_path = argv[++index];
            else if(argument == "--hybrid") hybrid = true;
            else if(argument == "--device" && index + 1 < argc) device = std::atoi(argv[++index]);
            else if(argument == "--invalid-probe" && index + 1 < argc) invalid_name = argv[++index];
            else throw std::runtime_error("invalid command-line argument: " + argument);
        }
        if(!invalid_name.empty()) return invalid_probe(invalid_name);
        if(input_path.empty()) throw std::runtime_error("--input is required");
        if(hybrid) return run_hybrid_batch(input_path, device);
        return run_batch(input_path, device);
    }
    catch(const std::exception &error)
    {
        std::cerr << "driver_error=" << error.what() << "\n";
        return 2;
    }
}
