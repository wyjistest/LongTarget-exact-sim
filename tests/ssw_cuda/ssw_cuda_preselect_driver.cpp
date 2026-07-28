#include "fasim/ssw_cuda/ssw_cuda_api.h"
#include "fasim/ssw_cpp.h"

#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
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
    bool transform_reference;
    int transform_strand;
    int transform_para;
    int transform_rule;
};

std::vector<std::string> split_tab(const std::string &line)
{
    std::vector<std::string> fields;
    size_t begin = 0;
    while(true)
    {
        const size_t end = line.find('\t', begin);
        fields.push_back(line.substr(begin, end == std::string::npos ? end : end - begin));
        if(end == std::string::npos)
        {
            break;
        }
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
    if(value.size() % 2 != 0)
    {
        throw std::runtime_error("hex payload has odd length");
    }
    std::string output;
    output.reserve(value.size() / 2);
    for(size_t index = 0; index < value.size(); index += 2)
    {
        const int high = hex_nibble(value[index]);
        const int low = hex_nibble(value[index + 1]);
        if(high < 0 || low < 0)
        {
            throw std::runtime_error("hex payload contains a non-hex character");
        }
        output.push_back(static_cast<char>((high << 4) | low));
    }
    return output;
}

std::vector<uint8_t> translate(const std::string &sequence)
{
    std::vector<uint8_t> output;
    output.reserve(sequence.size());
    for(size_t index = 0; index < sequence.size(); ++index)
    {
        const unsigned char value = static_cast<unsigned char>(sequence[index]);
        if(value == 0 || value >= 128)
        {
            throw std::runtime_error("unsupported raw input byte");
        }
        switch(value)
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

std::vector<RawCase> read_cases(const std::string &path)
{
    std::ifstream handle(path.c_str(), std::ios::binary);
    if(!handle)
    {
        throw std::runtime_error("cannot open input TSV: " + path);
    }
    std::string line;
    if(!std::getline(handle, line))
    {
        throw std::runtime_error("input TSV header drift");
    }
    const bool transform_rows =
        line == "case_id\tthreshold\tquery_hex\treference_hex\ttransform_strand\ttransform_para\ttransform_rule";
    if(!transform_rows && line != "case_id\tthreshold\tquery_hex\treference_hex")
    {
        throw std::runtime_error("input TSV header drift");
    }
    std::vector<RawCase> cases;
    size_t line_number = 1;
    while(std::getline(handle, line))
    {
        ++line_number;
        if(line.empty()) continue;
        const std::vector<std::string> fields = split_tab(line);
        if(fields.size() != (transform_rows ? 7U : 4U) || fields[0].empty())
        {
            throw std::runtime_error("invalid TSV row at line " + std::to_string(line_number));
        }
        char *end = NULL;
        const long threshold = std::strtol(fields[1].c_str(), &end, 10);
        if(end == fields[1].c_str() || *end != '\0' || threshold < 0 ||
           threshold > std::numeric_limits<int>::max())
        {
            throw std::runtime_error("invalid threshold at line " + std::to_string(line_number));
        }
        RawCase item;
        item.case_id = fields[0];
        item.threshold = static_cast<int>(threshold);
        item.query = decode_hex(fields[2]);
        item.reference = decode_hex(fields[3]);
        item.transform_reference = transform_rows;
        item.transform_strand = transform_rows ? std::atoi(fields[4].c_str()) : 0;
        item.transform_para = transform_rows ? std::atoi(fields[5].c_str()) : 0;
        item.transform_rule = transform_rows ? std::atoi(fields[6].c_str()) : 0;
        if(transform_rows)
        {
            item.reference = transferStringTableOptIn(item.reference, item.transform_strand,
                                                       item.transform_para, item.transform_rule);
        }
        cases.push_back(item);
    }
    if(cases.empty())
    {
        throw std::runtime_error("input TSV contains no cases");
    }
    return cases;
}

void fnv_update_u64(uint64_t value, uint64_t *digest)
{
    for(int byte = 0; byte < 8; ++byte)
    {
        *digest ^= static_cast<uint8_t>((value >> (byte * 8)) & 0xffU);
        *digest *= UINT64_C(1099511628211);
    }
}

std::string vector_digest(const std::vector<int> &values)
{
    uint64_t digest = UINT64_C(1469598103934665603);
    for(size_t index = 0; index < values.size(); ++index)
    {
        fnv_update_u64(static_cast<uint64_t>(values[index]), &digest);
    }
    fnv_update_u64(static_cast<uint64_t>(values.size()), &digest);
    std::ostringstream stream;
    stream << std::hex << std::setfill('0') << std::setw(16) << digest;
    return stream.str();
}

std::string scoreinfo_digest(const std::vector<StripedSmithWaterman::scoreInfo> &values)
{
    uint64_t digest = UINT64_C(1469598103934665603);
    for(size_t index = 0; index < values.size(); ++index)
    {
        fnv_update_u64(static_cast<uint64_t>(values[index].score), &digest);
        fnv_update_u64(static_cast<uint64_t>(values[index].position), &digest);
    }
    fnv_update_u64(static_cast<uint64_t>(values.size()), &digest);
    std::ostringstream stream;
    stream << std::hex << std::setfill('0') << std::setw(16) << digest;
    return stream.str();
}

std::string gpu_scoreinfo_digest(const std::vector<fasim_ssw_cuda::ScoreInfo> &values,
                                 int begin,
                                 int end)
{
    uint64_t digest = UINT64_C(1469598103934665603);
    for(int index = begin; index < end; ++index)
    {
        fnv_update_u64(static_cast<uint64_t>(values[static_cast<size_t>(index)].score), &digest);
        fnv_update_u64(static_cast<uint64_t>(values[static_cast<size_t>(index)].position), &digest);
    }
    fnv_update_u64(static_cast<uint64_t>(end - begin), &digest);
    std::ostringstream stream;
    stream << std::hex << std::setfill('0') << std::setw(16) << digest;
    return stream.str();
}

int run_batch(const std::string &input_path, int device, size_t maximum_cells)
{
    const std::vector<RawCase> cases = read_cases(input_path);
    std::vector<fasim_ssw_cuda::TaskInput> tasks;
    tasks.reserve(cases.size());
    for(size_t index = 0; index < cases.size(); ++index)
    {
        fasim_ssw_cuda::TaskInput task;
        task.case_id = cases[index].case_id;
        task.query = translate(cases[index].query);
        task.reference = translate(cases[index].reference);
        task.threshold = cases[index].threshold;
        tasks.push_back(task);
    }

    fasim_ssw_cuda::BatchOptions options;
    options.device = device;
    options.export_full_column_vectors = true;
    options.maximum_total_dp_cells = maximum_cells;
    fasim_ssw_cuda::BatchOutput gpu;
    const fasim_ssw_cuda::StatusCode status =
        fasim_ssw_cuda::pre_align_and_select(tasks, options, &gpu);
    if(status != fasim_ssw_cuda::STATUS_OK)
    {
        std::cerr << "batch_status=" << fasim_ssw_cuda::status_name(status)
                  << " error=" << gpu.error << "\n";
        return 2;
    }

    std::cout << "case_id\tquery_length\treference_length\tthreshold\tnumeric_path"
                 "\tcpu_column_digest\tgpu_column_digest\tcolumn_equal"
                 "\tcpu_scoreinfo_digest\tgpu_scoreinfo_digest\tscoreinfo_equal\n";
    bool all_equal = true;
    StripedSmithWaterman::Aligner aligner;
    StripedSmithWaterman::Filter filter;
    StripedSmithWaterman::Alignment alignment;
    for(size_t case_index = 0; case_index < cases.size(); ++case_index)
    {
        std::vector<int> cpu_columns;
        std::vector<StripedSmithWaterman::scoreInfo> cpu_scoreinfos;
        const RawCase &item = cases[case_index];
        if(!aligner.preAlignColumnScores(item.query.c_str(), item.reference.c_str(),
                                         static_cast<int>(item.reference.size()), filter, 15,
                                         item.threshold, cpu_columns) ||
           !aligner.preAlign(item.query.c_str(), item.reference.c_str(),
                             static_cast<int>(item.reference.size()), filter, &alignment, 15,
                             item.threshold, cpu_scoreinfos, 5, 4))
        {
            std::cerr << item.case_id << ": CPU authority failed\n";
            return 3;
        }

        const int column_begin = gpu.column_offsets[case_index];
        const int column_end = gpu.column_offsets[case_index + 1];
        const std::vector<int> gpu_columns(gpu.column_maxima.begin() + column_begin,
                                           gpu.column_maxima.begin() + column_end);
        const int scoreinfo_begin = gpu.selection_offsets[case_index];
        const int scoreinfo_end = gpu.selection_offsets[case_index + 1];
        bool scoreinfo_equal = static_cast<int>(cpu_scoreinfos.size()) == scoreinfo_end - scoreinfo_begin;
        if(scoreinfo_equal)
        {
            for(size_t index = 0; index < cpu_scoreinfos.size(); ++index)
            {
                const fasim_ssw_cuda::ScoreInfo &actual =
                    gpu.scoreinfos[static_cast<size_t>(scoreinfo_begin) + index];
                if(actual.task_index != static_cast<int>(case_index) ||
                   actual.index != static_cast<int>(index) ||
                   actual.score != cpu_scoreinfos[index].score ||
                   actual.position != cpu_scoreinfos[index].position ||
                   actual.reason != fasim_ssw_cuda::SCOREINFO_THRESHOLD_RUN_MAX)
                {
                    scoreinfo_equal = false;
                    break;
                }
            }
        }
        const bool column_equal = cpu_columns == gpu_columns;
        if(!column_equal)
        {
            size_t first_difference = 0;
            while(first_difference < cpu_columns.size() &&
                  first_difference < gpu_columns.size() &&
                  cpu_columns[first_difference] == gpu_columns[first_difference])
            {
                ++first_difference;
            }
            std::cerr << item.case_id << ": first_column_difference=" << first_difference;
            if(first_difference < cpu_columns.size())
                std::cerr << " cpu=" << cpu_columns[first_difference];
            if(first_difference < gpu_columns.size())
                std::cerr << " gpu=" << gpu_columns[first_difference];
            std::cerr << " cpu_vector=";
            for(size_t index = 0; index < cpu_columns.size(); ++index)
                std::cerr << (index == 0 ? "" : ",") << cpu_columns[index];
            std::cerr << " gpu_vector=";
            for(size_t index = 0; index < gpu_columns.size(); ++index)
                std::cerr << (index == 0 ? "" : ",") << gpu_columns[index];
            std::cerr << "\n";
        }
        all_equal = all_equal && column_equal && scoreinfo_equal;
        int maximum_score = 0;
        for(size_t index = 0; index < cpu_columns.size(); ++index)
        {
            if(cpu_columns[index] > maximum_score) maximum_score = cpu_columns[index];
        }
        std::cout << item.case_id << '\t' << item.query.size() << '\t' << item.reference.size()
                  << '\t' << item.threshold << '\t' << (maximum_score >= 255 ? "word16" : "byte8")
                  << '\t' << vector_digest(cpu_columns) << '\t' << vector_digest(gpu_columns)
                  << '\t' << (column_equal ? 1 : 0)
                  << '\t' << scoreinfo_digest(cpu_scoreinfos)
                  << '\t' << gpu_scoreinfo_digest(gpu.scoreinfos, scoreinfo_begin, scoreinfo_end)
                  << '\t' << (scoreinfo_equal ? 1 : 0) << '\n';
    }
    std::cerr << std::setprecision(9)
              << "batch_status=ok cases=" << cases.size()
              << " device=" << device
              << " packing_seconds=" << gpu.telemetry.packing_seconds
              << " h2d_seconds=" << gpu.telemetry.h2d_seconds
              << " prealign_seconds=" << gpu.telemetry.prealign_seconds
              << " selection_flag_seconds=" << gpu.telemetry.selection_flag_seconds
              << " selection_scan_seconds=" << gpu.telemetry.selection_scan_seconds
              << " selection_scatter_seconds=" << gpu.telemetry.selection_scatter_seconds
              << " d2h_seconds=" << gpu.telemetry.d2h_seconds
              << " overhead_seconds=" << gpu.telemetry.overhead_seconds
              << " device_input_bytes=" << gpu.telemetry.device_input_bytes
              << " device_workspace_bytes=" << gpu.telemetry.device_workspace_bytes
              << " device_output_bytes=" << gpu.telemetry.device_output_bytes
              << " total_wall_seconds=" << gpu.telemetry.total_wall_seconds << "\n";
    return all_equal ? 0 : 1;
}

int invalid_probe(const std::string &name, int device)
{
    std::vector<fasim_ssw_cuda::TaskInput> tasks(1);
    tasks[0].case_id = name;
    tasks[0].query.assign(1, 0);
    tasks[0].reference.assign(1, 0);
    tasks[0].threshold = 0;
    fasim_ssw_cuda::BatchOptions options;
    options.device = device;
    if(name == "empty_query") tasks[0].query.clear();
    else if(name == "empty_reference") tasks[0].reference.clear();
    else if(name == "invalid_base") tasks[0].query[0] = 5;
    else if(name == "query_too_long") tasks[0].query.assign(fasim_ssw_cuda::kMaximumQueryLength + 1, 0);
    else if(name == "capacity") options.maximum_total_dp_cells = 0;
    else if(name == "out_of_memory") options.force_out_of_memory_for_test = true;
    else if(name == "contract_drift") options.contract.match += 1;
    else if(name == "device_out_of_range") options.device = std::numeric_limits<int>::max();
    else throw std::runtime_error("unknown invalid probe: " + name);

    fasim_ssw_cuda::BatchOutput output;
    const fasim_ssw_cuda::StatusCode status =
        fasim_ssw_cuda::pre_align_and_select(tasks, options, &output);
    std::cout << "probe=" << name << " status=" << fasim_ssw_cuda::status_name(status)
              << " error=" << output.error << "\n";
    return status == fasim_ssw_cuda::STATUS_OK ? 1 : 0;
}

int attempt_probe()
{
    using fasim_ssw_cuda::AttemptObservation;
    std::vector<AttemptObservation> observations;
    const int values[][6] = {
        {0, 0, 70, 60, 9, 10}, {0, 1, 70, 70, 8, 10}, {0, 2, 70, 80, 9, 10},
        {1, 0, 90, 65, 9, 10}, {1, 1, 90, 68, 9, 10}, {1, 2, 90, 66, 9, 10},
        {2, 0, 80, 30, 7, 10}, {2, 1, 80, 40, 8, 10}, {2, 2, 80, 35, 7, 10},
        {3, 0, 50, 0, -1, 10}, {3, 1, 50, 0, -1, 10}
    };
    for(size_t index = 0; index < sizeof(values) / sizeof(values[0]); ++index)
    {
        AttemptObservation item;
        item.scoreinfo_index = values[index][0];
        item.attempt_order = values[index][1];
        item.prealign_score = values[index][2];
        item.alignment_score = values[index][3];
        item.ref_end = values[index][4];
        item.cutlength = values[index][5];
        observations.push_back(item);
    }
    std::vector<fasim_ssw_cuda::AttemptDecision> decisions;
    std::string error;
    const fasim_ssw_cuda::StatusCode status =
        fasim_ssw_cuda::select_attempts(observations, &decisions, &error);
    if(status != fasim_ssw_cuda::STATUS_OK)
    {
        std::cerr << error << "\n";
        return 1;
    }
    std::cout << "scoreinfo_index\tattempt_order\tselected\treason\n";
    for(size_t index = 0; index < decisions.size(); ++index)
    {
        std::cout << decisions[index].scoreinfo_index << '\t' << decisions[index].attempt_order
                  << '\t' << (decisions[index].selected ? 1 : 0) << '\t'
                  << fasim_ssw_cuda::attempt_reason_name(decisions[index].reason) << '\n';
    }
    return 0;
}

} // namespace

int main(int argc, char **argv)
{
    try
    {
        std::string input_path;
        std::string invalid_name;
        int device = 0;
        size_t maximum_cells = static_cast<size_t>(1) << 31;
        bool run_attempt_probe = false;
        for(int index = 1; index < argc; ++index)
        {
            const std::string argument = argv[index];
            if(argument == "--input" && index + 1 < argc) input_path = argv[++index];
            else if(argument == "--device" && index + 1 < argc) device = std::atoi(argv[++index]);
            else if(argument == "--maximum-cells" && index + 1 < argc)
                maximum_cells = static_cast<size_t>(std::strtoull(argv[++index], NULL, 10));
            else if(argument == "--invalid-probe" && index + 1 < argc) invalid_name = argv[++index];
            else if(argument == "--attempt-probe") run_attempt_probe = true;
            else throw std::runtime_error("invalid command-line argument: " + argument);
        }
        if(!invalid_name.empty()) return invalid_probe(invalid_name, device);
        if(run_attempt_probe) return attempt_probe();
        if(input_path.empty()) throw std::runtime_error("--input is required");
        return run_batch(input_path, device, maximum_cells);
    }
    catch(const std::exception &error)
    {
        std::cerr << "driver_error=" << error.what() << "\n";
        return 2;
    }
}
