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

struct CpuEndpoint
{
    int score1;
    int ref_end1;
    int read_end1;
    int score2;
    int ref_end2;
    int numeric_path;
};

struct FrozenColumnCase
{
    std::string case_id;
    int numeric_path;
    int mask_length;
    std::vector<int> columns;
    int score1;
    int ref_end1;
    int score2;
    int ref_end2;
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
    {
        std::ostringstream message;
        message << "invalid " << label << " at line " << line_number;
        throw std::runtime_error(message.str());
    }
    return parsed;
}

std::vector<RawCase> read_cases(const std::string &path)
{
    std::ifstream handle(path.c_str(), std::ios::binary);
    if(!handle) throw std::runtime_error("cannot open input TSV: " + path);
    std::string line;
    if(!std::getline(handle, line)) throw std::runtime_error("input TSV header drift");
    const bool legacy_transform_rows =
        line == "case_id\tthreshold\tquery_hex\treference_hex\ttransform_strand\ttransform_para\ttransform_rule";
    const bool mixed_transform_rows =
        line == "case_id\tthreshold\tquery_hex\treference_hex\ttransform_enabled\ttransform_strand\ttransform_para\ttransform_rule";
    if(!legacy_transform_rows && !mixed_transform_rows &&
       line != "case_id\tthreshold\tquery_hex\treference_hex")
        throw std::runtime_error("input TSV header drift");

    std::vector<RawCase> cases;
    size_t line_number = 1;
    while(std::getline(handle, line))
    {
        ++line_number;
        if(line.empty()) continue;
        const std::vector<std::string> fields = split_tab(line);
        const size_t expected_fields = mixed_transform_rows ? 8U : (legacy_transform_rows ? 7U : 4U);
        if(fields.size() != expected_fields || fields[0].empty())
            throw std::runtime_error("invalid TSV row at line " + std::to_string(line_number));
        RawCase item;
        item.case_id = fields[0];
        item.threshold = static_cast<int>(parse_nonnegative(fields[1], "threshold", line_number));
        item.query = decode_hex(fields[2]);
        item.reference = decode_hex(fields[3]);
        item.transform_reference = legacy_transform_rows ||
            (mixed_transform_rows && parse_nonnegative(fields[4], "transform_enabled", line_number) == 1);
        const size_t transform_offset = mixed_transform_rows ? 1U : 0U;
        item.transform_strand = item.transform_reference ?
            static_cast<int>(parse_nonnegative(fields[4 + transform_offset], "transform_strand", line_number)) : 0;
        item.transform_para = item.transform_reference ? std::atoi(fields[5 + transform_offset].c_str()) : 0;
        item.transform_rule = item.transform_reference ?
            static_cast<int>(parse_nonnegative(fields[6 + transform_offset], "transform_rule", line_number)) : 0;
        if(item.transform_reference)
        {
            item.reference = transferStringTableOptIn(
                item.reference, item.transform_strand, item.transform_para, item.transform_rule);
        }
        cases.push_back(item);
    }
    if(cases.empty()) throw std::runtime_error("input TSV contains no cases");
    return cases;
}

std::vector<int> parse_columns(const std::string &value, size_t line_number)
{
    std::vector<int> columns;
    size_t begin = 0;
    while(begin <= value.size())
    {
        const size_t end = value.find(',', begin);
        const std::string field = value.substr(begin, end == std::string::npos ? end : end - begin);
        columns.push_back(static_cast<int>(parse_nonnegative(field, "column score", line_number)));
        if(end == std::string::npos) break;
        begin = end + 1;
    }
    if(columns.empty()) throw std::runtime_error("empty column vector");
    return columns;
}

std::vector<FrozenColumnCase> read_column_cases(const std::string &path)
{
    std::ifstream handle(path.c_str(), std::ios::binary);
    if(!handle) throw std::runtime_error("cannot open column TSV: " + path);
    std::string line;
    const std::string header =
        "case_id\tnumeric_path\tmask_length\tcolumns\tscore1\tref_end1\tscore2\tref_end2";
    if(!std::getline(handle, line) || line != header)
        throw std::runtime_error("column TSV header drift");
    std::vector<FrozenColumnCase> cases;
    size_t line_number = 1;
    while(std::getline(handle, line))
    {
        ++line_number;
        if(line.empty()) continue;
        const std::vector<std::string> fields = split_tab(line);
        if(fields.size() != 8 || fields[0].empty())
            throw std::runtime_error("invalid column TSV row at line " + std::to_string(line_number));
        FrozenColumnCase item;
        item.case_id = fields[0];
        if(fields[1] == "byte8") item.numeric_path = fasim_ssw_cuda::NUMERIC_PATH_BYTE8;
        else if(fields[1] == "word16") item.numeric_path = fasim_ssw_cuda::NUMERIC_PATH_WORD16;
        else throw std::runtime_error("invalid numeric path at line " + std::to_string(line_number));
        item.mask_length = static_cast<int>(parse_nonnegative(fields[2], "mask length", line_number));
        item.columns = parse_columns(fields[3], line_number);
        item.score1 = static_cast<int>(parse_nonnegative(fields[4], "score1", line_number));
        item.ref_end1 = static_cast<int>(parse_nonnegative(fields[5], "ref_end1", line_number));
        item.score2 = static_cast<int>(parse_nonnegative(fields[6], "score2", line_number));
        item.ref_end2 = static_cast<int>(parse_nonnegative(fields[7], "ref_end2", line_number));
        cases.push_back(item);
    }
    if(cases.empty()) throw std::runtime_error("column TSV contains no cases");
    return cases;
}

std::vector<uint8_t> translate(const std::string &sequence)
{
    std::vector<uint8_t> output;
    output.reserve(sequence.size());
    for(size_t index = 0; index < sequence.size(); ++index)
    {
        const unsigned char value = static_cast<unsigned char>(sequence[index]);
        if(value == 0 || value >= 128) throw std::runtime_error("unsupported raw input byte");
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
        fnv_update_u64(static_cast<uint64_t>(values[index]), &digest);
    fnv_update_u64(static_cast<uint64_t>(values.size()), &digest);
    std::ostringstream stream;
    stream << std::hex << std::setfill('0') << std::setw(16) << digest;
    return stream.str();
}

std::string endpoint_digest(int score1, int ref_end1, int read_end1,
                            int score2, int ref_end2, int numeric_path)
{
    uint64_t digest = UINT64_C(1469598103934665603);
    fnv_update_u64(static_cast<uint64_t>(score1), &digest);
    fnv_update_u64(static_cast<uint64_t>(ref_end1), &digest);
    fnv_update_u64(static_cast<uint64_t>(read_end1), &digest);
    fnv_update_u64(static_cast<uint64_t>(score2), &digest);
    fnv_update_u64(static_cast<uint64_t>(ref_end2), &digest);
    fnv_update_u64(static_cast<uint64_t>(numeric_path), &digest);
    std::ostringstream stream;
    stream << std::hex << std::setfill('0') << std::setw(16) << digest;
    return stream.str();
}

const char *numeric_path_name(int path)
{
    if(path == fasim_ssw_cuda::NUMERIC_PATH_BYTE8) return "byte8";
    if(path == fasim_ssw_cuda::NUMERIC_PATH_WORD16) return "word16";
    return "unknown";
}

bool reducer_equal(const CpuEndpoint &cpu, const fasim_ssw_cuda::ColumnEndpoint &actual)
{
    return actual.score1 == cpu.score1 && actual.ref_end1 == cpu.ref_end1 &&
           actual.score2 == cpu.score2 && actual.ref_end2 == cpu.ref_end2 &&
           actual.numeric_path == cpu.numeric_path;
}

bool forward_equal(const CpuEndpoint &cpu, const fasim_ssw_cuda::ForwardEndpoint &actual)
{
    return actual.score1 == cpu.score1 && actual.ref_end1 == cpu.ref_end1 &&
           actual.read_end1 == cpu.read_end1 && actual.score2 == cpu.score2 &&
           actual.ref_end2 == cpu.ref_end2 && actual.numeric_path == cpu.numeric_path;
}

int run_batch(const std::string &input_path, int device, size_t maximum_cells)
{
    const std::vector<RawCase> cases = read_cases(input_path);
    std::vector<fasim_ssw_cuda::TaskInput> tasks;
    std::vector<std::vector<int> > cpu_prealign_columns;
    std::vector<CpuEndpoint> cpu_endpoints;
    tasks.reserve(cases.size());
    cpu_prealign_columns.reserve(cases.size());
    cpu_endpoints.reserve(cases.size());

    StripedSmithWaterman::Aligner aligner;
    StripedSmithWaterman::Filter filter;
    for(size_t index = 0; index < cases.size(); ++index)
    {
        const RawCase &item = cases[index];
        fasim_ssw_cuda::TaskInput task;
        task.case_id = item.case_id;
        task.query = translate(item.query);
        task.reference = translate(item.reference);
        task.threshold = item.threshold;
        tasks.push_back(task);

        StripedSmithWaterman::Alignment alignment;
        std::vector<int> columns;
        if(!aligner.preAlignColumnScores(item.query.c_str(), item.reference.c_str(),
                                         static_cast<int>(item.reference.size()), filter, 15,
                                         item.threshold, columns) ||
           !aligner.Align(item.query.c_str(), item.reference.c_str(),
                          static_cast<int>(item.reference.size()), filter, &alignment, 15))
        {
            std::cerr << item.case_id << ": CPU authority failed\n";
            return 3;
        }
        CpuEndpoint endpoint;
        endpoint.score1 = alignment.sw_score;
        endpoint.ref_end1 = alignment.ref_end;
        endpoint.read_end1 = alignment.query_end;
        endpoint.score2 = alignment.sw_score_next_best;
        endpoint.ref_end2 = alignment.ref_end_next_best;
        endpoint.numeric_path = alignment.sw_score + fasim_ssw_cuda::kContractMismatchPenalty >= 255 ?
            fasim_ssw_cuda::NUMERIC_PATH_WORD16 : fasim_ssw_cuda::NUMERIC_PATH_BYTE8;
        cpu_endpoints.push_back(endpoint);
        cpu_prealign_columns.push_back(columns);
    }

    fasim_ssw_cuda::BatchOptions options;
    options.device = device;
    options.export_full_column_vectors = true;
    options.maximum_total_dp_cells = maximum_cells;
    fasim_ssw_cuda::ForwardBatchOutput gpu;
    const fasim_ssw_cuda::StatusCode gpu_status =
        fasim_ssw_cuda::forward_align(tasks, options, &gpu);
    if(gpu_status != fasim_ssw_cuda::STATUS_OK)
    {
        std::cerr << "forward_status=" << fasim_ssw_cuda::status_name(gpu_status)
                  << " error=" << gpu.error << "\n";
        return 2;
    }
    if(gpu.endpoints.size() != cases.size() ||
       gpu.column_offsets.size() != cases.size() + 1)
        throw std::runtime_error("GPU output cardinality drift");

    std::vector<fasim_ssw_cuda::ColumnReductionInput> reductions;
    reductions.reserve(cases.size());
    for(size_t index = 0; index < cases.size(); ++index)
    {
        fasim_ssw_cuda::ColumnReductionInput reduction;
        reduction.case_id = cases[index].case_id;
        reduction.column_maxima.assign(
            gpu.column_maxima.begin() + gpu.column_offsets[index],
            gpu.column_maxima.begin() + gpu.column_offsets[index + 1]);
        reduction.numeric_path = gpu.endpoints[index].numeric_path;
        reduction.mask_length = 15;
        reductions.push_back(reduction);
    }
    std::vector<fasim_ssw_cuda::ColumnEndpoint> reduced;
    fasim_ssw_cuda::Telemetry reducer_telemetry;
    std::string reducer_error;
    const fasim_ssw_cuda::StatusCode reducer_status =
        fasim_ssw_cuda::reduce_forward_columns(
            reductions, options, &reduced, &reducer_telemetry, &reducer_error);
    if(reducer_status != fasim_ssw_cuda::STATUS_OK)
    {
        std::cerr << "reducer_status=" << fasim_ssw_cuda::status_name(reducer_status)
                  << " error=" << reducer_error << "\n";
        return 2;
    }

    std::cout << "case_id\tquery_length\treference_length\tnumeric_path"
                 "\tcpu_score1\treducer_score1\tgpu_score1"
                 "\tcpu_ref_end1\treducer_ref_end1\tgpu_ref_end1"
                 "\tcpu_read_end1\tgpu_read_end1"
                 "\tcpu_score2\treducer_score2\tgpu_score2"
                 "\tcpu_ref_end2\treducer_ref_end2\tgpu_ref_end2"
                 "\treducer_equal\tgpu_equal\tcolumn_equal"
                 "\tcpu_column_digest\tgpu_column_digest"
                 "\tcpu_endpoint_digest\treducer_endpoint_digest\tgpu_endpoint_digest"
                 "\tcpu_endpoint_calls\n";
    bool all_equal = true;
    for(size_t index = 0; index < cases.size(); ++index)
    {
        const CpuEndpoint &cpu = cpu_endpoints[index];
        const fasim_ssw_cuda::ColumnEndpoint &reducer = reduced[index];
        const fasim_ssw_cuda::ForwardEndpoint &actual = gpu.endpoints[index];
        const int column_begin = gpu.column_offsets[index];
        const int column_end = gpu.column_offsets[index + 1];
        const std::vector<int> gpu_columns(gpu.column_maxima.begin() + column_begin,
                                           gpu.column_maxima.begin() + column_end);
        const bool columns_equal = cpu_prealign_columns[index] == gpu_columns;
        const bool reducer_matches = reducer_equal(cpu, reducer);
        const bool gpu_matches = forward_equal(cpu, actual);
        all_equal = all_equal && reducer_matches && gpu_matches &&
                    gpu.telemetry.cpu_endpoint_calls == 0;
        std::cout << cases[index].case_id << '\t' << cases[index].query.size() << '\t'
                  << cases[index].reference.size() << '\t' << numeric_path_name(cpu.numeric_path)
                  << '\t' << cpu.score1 << '\t' << reducer.score1 << '\t' << actual.score1
                  << '\t' << cpu.ref_end1 << '\t' << reducer.ref_end1 << '\t' << actual.ref_end1
                  << '\t' << cpu.read_end1 << '\t' << actual.read_end1
                  << '\t' << cpu.score2 << '\t' << reducer.score2 << '\t' << actual.score2
                  << '\t' << cpu.ref_end2 << '\t' << reducer.ref_end2 << '\t' << actual.ref_end2
                  << '\t' << (reducer_matches ? 1 : 0) << '\t' << (gpu_matches ? 1 : 0)
                  << '\t' << (columns_equal ? 1 : 0)
                  << '\t' << vector_digest(cpu_prealign_columns[index])
                  << '\t' << vector_digest(gpu_columns)
                  << '\t' << endpoint_digest(cpu.score1, cpu.ref_end1, cpu.read_end1,
                                              cpu.score2, cpu.ref_end2, cpu.numeric_path)
                  << '\t' << endpoint_digest(reducer.score1, reducer.ref_end1, cpu.read_end1,
                                              reducer.score2, reducer.ref_end2, reducer.numeric_path)
                  << '\t' << endpoint_digest(actual.score1, actual.ref_end1, actual.read_end1,
                                              actual.score2, actual.ref_end2, actual.numeric_path)
                  << '\t' << gpu.telemetry.cpu_endpoint_calls << '\n';
    }
    std::cerr << std::setprecision(9)
              << "forward_status=ok cases=" << cases.size() << " device=" << device
              << " reducer_seconds=" << reducer_telemetry.endpoint_reduce_seconds
              << " forward_seconds=" << gpu.telemetry.forward_seconds
              << " total_wall_seconds=" << gpu.telemetry.total_wall_seconds
              << " cpu_endpoint_calls=" << gpu.telemetry.cpu_endpoint_calls << "\n";
    return all_equal ? 0 : 1;
}

int invalid_forward_probe(const std::string &name, int device)
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
    else if(name == "query_too_long")
        tasks[0].query.assign(fasim_ssw_cuda::kMaximumQueryLength + 1, 0);
    else if(name == "capacity") options.maximum_total_dp_cells = 0;
    else if(name == "out_of_memory") options.force_out_of_memory_for_test = true;
    else if(name == "contract_drift") options.contract.match += 1;
    else if(name == "device_out_of_range") options.device = std::numeric_limits<int>::max();
    else throw std::runtime_error("unknown forward invalid probe: " + name);

    fasim_ssw_cuda::ForwardBatchOutput output;
    const fasim_ssw_cuda::StatusCode status =
        fasim_ssw_cuda::forward_align(tasks, options, &output);
    std::cout << "probe=" << name << " api=forward status="
              << fasim_ssw_cuda::status_name(status) << " error=" << output.error << "\n";
    return status == fasim_ssw_cuda::STATUS_OK ? 1 : 0;
}

int run_column_batch(const std::string &input_path, int device)
{
    const std::vector<FrozenColumnCase> cases = read_column_cases(input_path);
    std::vector<fasim_ssw_cuda::ColumnReductionInput> inputs;
    inputs.reserve(cases.size());
    for(size_t index = 0; index < cases.size(); ++index)
    {
        fasim_ssw_cuda::ColumnReductionInput input;
        input.case_id = cases[index].case_id;
        input.column_maxima = cases[index].columns;
        input.numeric_path = cases[index].numeric_path;
        input.mask_length = cases[index].mask_length;
        inputs.push_back(input);
    }
    fasim_ssw_cuda::BatchOptions options;
    options.device = device;
    std::vector<fasim_ssw_cuda::ColumnEndpoint> endpoints;
    fasim_ssw_cuda::Telemetry telemetry;
    std::string error;
    const fasim_ssw_cuda::StatusCode status = fasim_ssw_cuda::reduce_forward_columns(
        inputs, options, &endpoints, &telemetry, &error);
    if(status != fasim_ssw_cuda::STATUS_OK)
    {
        std::cerr << "reducer_status=" << fasim_ssw_cuda::status_name(status)
                  << " error=" << error << "\n";
        return 2;
    }
    std::cout << "case_id\tnumeric_path\texpected_score1\treducer_score1"
                 "\texpected_ref_end1\treducer_ref_end1\texpected_score2\treducer_score2"
                 "\texpected_ref_end2\treducer_ref_end2\treducer_equal\tcpu_endpoint_calls\n";
    bool all_equal = endpoints.size() == cases.size();
    for(size_t index = 0; index < cases.size() && index < endpoints.size(); ++index)
    {
        const FrozenColumnCase &expected = cases[index];
        const fasim_ssw_cuda::ColumnEndpoint &actual = endpoints[index];
        const bool equal = actual.task_index == static_cast<int>(index) &&
                           actual.numeric_path == expected.numeric_path &&
                           actual.score1 == expected.score1 &&
                           actual.ref_end1 == expected.ref_end1 &&
                           actual.score2 == expected.score2 &&
                           actual.ref_end2 == expected.ref_end2;
        all_equal = all_equal && equal;
        std::cout << expected.case_id << '\t' << numeric_path_name(expected.numeric_path)
                  << '\t' << expected.score1 << '\t' << actual.score1
                  << '\t' << expected.ref_end1 << '\t' << actual.ref_end1
                  << '\t' << expected.score2 << '\t' << actual.score2
                  << '\t' << expected.ref_end2 << '\t' << actual.ref_end2
                  << '\t' << (equal ? 1 : 0) << '\t' << telemetry.cpu_endpoint_calls << '\n';
    }
    std::cerr << "reducer_status=ok cases=" << cases.size()
              << " endpoint_reduce_seconds=" << telemetry.endpoint_reduce_seconds
              << " cpu_endpoint_calls=" << telemetry.cpu_endpoint_calls << "\n";
    return all_equal && telemetry.cpu_endpoint_calls == 0 ? 0 : 1;
}

int invalid_reducer_probe(const std::string &name, int device)
{
    std::vector<fasim_ssw_cuda::ColumnReductionInput> inputs(1);
    inputs[0].case_id = name;
    inputs[0].column_maxima.assign(1, 0);
    inputs[0].numeric_path = fasim_ssw_cuda::NUMERIC_PATH_BYTE8;
    inputs[0].mask_length = 15;
    fasim_ssw_cuda::BatchOptions options;
    options.device = device;
    if(name == "empty_batch") inputs.clear();
    else if(name == "empty_columns") inputs[0].column_maxima.clear();
    else if(name == "invalid_numeric_path") inputs[0].numeric_path = 99;
    else if(name == "invalid_mask") inputs[0].mask_length = 14;
    else if(name == "invalid_column_score") inputs[0].column_maxima[0] = -1;
    else throw std::runtime_error("unknown reducer invalid probe: " + name);

    std::vector<fasim_ssw_cuda::ColumnEndpoint> endpoints;
    fasim_ssw_cuda::Telemetry telemetry;
    std::string error;
    const fasim_ssw_cuda::StatusCode status = fasim_ssw_cuda::reduce_forward_columns(
        inputs, options, &endpoints, &telemetry, &error);
    std::cout << "probe=" << name << " api=reducer status="
              << fasim_ssw_cuda::status_name(status) << " error=" << error << "\n";
    return status == fasim_ssw_cuda::STATUS_OK ? 1 : 0;
}

} // namespace

int main(int argc, char **argv)
{
    try
    {
        std::string input_path;
        std::string column_input_path;
        std::string invalid_forward_name;
        std::string invalid_reducer_name;
        int device = 0;
        size_t maximum_cells = static_cast<size_t>(1) << 31;
        for(int index = 1; index < argc; ++index)
        {
            const std::string argument = argv[index];
            if(argument == "--input" && index + 1 < argc) input_path = argv[++index];
            else if(argument == "--column-input" && index + 1 < argc) column_input_path = argv[++index];
            else if(argument == "--device" && index + 1 < argc) device = std::atoi(argv[++index]);
            else if(argument == "--maximum-cells" && index + 1 < argc)
                maximum_cells = static_cast<size_t>(std::strtoull(argv[++index], NULL, 10));
            else if(argument == "--invalid-forward-probe" && index + 1 < argc)
                invalid_forward_name = argv[++index];
            else if(argument == "--invalid-reducer-probe" && index + 1 < argc)
                invalid_reducer_name = argv[++index];
            else throw std::runtime_error("invalid command-line argument: " + argument);
        }
        if(!invalid_forward_name.empty()) return invalid_forward_probe(invalid_forward_name, device);
        if(!invalid_reducer_name.empty()) return invalid_reducer_probe(invalid_reducer_name, device);
        if(!column_input_path.empty()) return run_column_batch(column_input_path, device);
        if(input_path.empty()) throw std::runtime_error("--input is required");
        return run_batch(input_path, device, maximum_cells);
    }
    catch(const std::exception &error)
    {
        std::cerr << "driver_error=" << error.what() << "\n";
        return 2;
    }
}
