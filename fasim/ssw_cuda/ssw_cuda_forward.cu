#include "ssw_cuda_api.h"
#include "ssw_cuda_internal.h"
#include "ssw_cuda_striped.cuh"

#include <cuda_runtime.h>

#include <algorithm>
#include <chrono>
#include <climits>
#include <limits>
#include <new>
#include <sstream>

namespace fasim_ssw_cuda
{
namespace
{

template <typename T>
class DeviceBuffer
{
public:
    DeviceBuffer():pointer_(NULL) {}
    ~DeviceBuffer() { if(pointer_ != NULL) cudaFree(pointer_); }
    cudaError_t allocate(size_t count)
    {
        if(count == 0) return cudaSuccess;
        return cudaMalloc(reinterpret_cast<void **>(&pointer_), count * sizeof(T));
    }
    T *get() { return pointer_; }
    const T *get() const { return pointer_; }
private:
    DeviceBuffer(const DeviceBuffer &);
    DeviceBuffer &operator=(const DeviceBuffer &);
    T *pointer_;
};

struct ColumnDescriptor
{
    int offset;
    int length;
    int numeric_path;
    int mask_length;
};

double elapsed_seconds(const std::chrono::steady_clock::time_point &start)
{
    return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
}

StatusCode cuda_failure(cudaError_t status, const char *operation, std::string *error)
{
    if(error != NULL)
    {
        std::ostringstream stream;
        stream << operation << ": " << cudaGetErrorString(status);
        *error = stream.str();
    }
    if(status == cudaErrorMemoryAllocation) return STATUS_OUT_OF_MEMORY;
    if(status == cudaErrorNoDevice || status == cudaErrorInsufficientDriver ||
       status == cudaErrorInitializationError) return STATUS_CUDA_UNAVAILABLE;
    return STATUS_CUDA_ERROR;
}

bool contract_is_frozen(const ContractConfig &config)
{
    return config.match == kContractMatch &&
           config.mismatch_penalty == kContractMismatchPenalty &&
           config.gap_open == kContractGapOpen &&
           config.gap_extend == kContractGapExtend &&
           config.mask_length == kContractMaskLength &&
           config.flag == 0 &&
           config.score_filter == kContractScoreFilter &&
           config.distance_filter == kContractDistanceFilter;
}

StatusCode prepare_device(const BatchOptions &options, std::string *error)
{
    if(options.device < 0)
    {
        if(error != NULL) *error = "CUDA device index is negative";
        return STATUS_INVALID_ARGUMENT;
    }
    int device_count = 0;
    cudaError_t status = cudaGetDeviceCount(&device_count);
    if(status != cudaSuccess || device_count == 0)
        return cuda_failure(status == cudaSuccess ? cudaErrorNoDevice : status,
                            "cudaGetDeviceCount", error);
    if(options.device >= device_count)
    {
        if(error != NULL) *error = "CUDA device index is out of range";
        return STATUS_INVALID_ARGUMENT;
    }
    status = cudaSetDevice(options.device);
    if(status != cudaSuccess) return cuda_failure(status, "cudaSetDevice", error);
    if(options.force_out_of_memory_for_test)
    {
        if(error != NULL) *error = "forced device allocation failure for fail-closed testing";
        return STATUS_OUT_OF_MEMORY;
    }
    return STATUS_OK;
}

__device__ void reduce_columns(const int *columns,
                               int length,
                               int numeric_path,
                               int mask_length,
                               int *score1,
                               int *ref_end1,
                               int *score2,
                               int *ref_end2)
{
    int best_score = 0;
    int best_reference = numeric_path == NUMERIC_PATH_BYTE8 ? -1 : 0;
    for(int column = 0; column < length; ++column)
    {
        if(columns[column] > best_score)
        {
            best_score = columns[column];
            best_reference = column;
        }
    }

    int next_score = 0;
    int next_reference = 0;
    const int left_edge = best_reference - mask_length > 0 ?
                          best_reference - mask_length : 0;
    for(int column = 0; column < left_edge; ++column)
    {
        if(columns[column] > next_score)
        {
            next_score = columns[column];
            next_reference = column;
        }
    }
    int right_edge = best_reference + mask_length > length ?
                     length : best_reference + mask_length;
    if(numeric_path == NUMERIC_PATH_BYTE8) ++right_edge;
    for(int column = right_edge; column < length; ++column)
    {
        if(columns[column] > next_score)
        {
            next_score = columns[column];
            next_reference = column;
        }
    }
    *score1 = best_score;
    *ref_end1 = best_reference;
    *score2 = next_score;
    *ref_end2 = next_reference;
}

__global__ void column_endpoint_kernel(const ColumnDescriptor *descriptors,
                                       int task_count,
                                       const int *columns,
                                       ColumnEndpoint *endpoints)
{
    const int task_index = blockIdx.x * blockDim.x + threadIdx.x;
    if(task_index >= task_count) return;
    const ColumnDescriptor descriptor = descriptors[task_index];
    ColumnEndpoint endpoint;
    endpoint.task_index = task_index;
    endpoint.numeric_path = descriptor.numeric_path;
    reduce_columns(columns + descriptor.offset, descriptor.length,
                   descriptor.numeric_path, descriptor.mask_length,
                   &endpoint.score1, &endpoint.ref_end1,
                   &endpoint.score2, &endpoint.ref_end2);
    endpoints[task_index] = endpoint;
}

__global__ void full_forward_kernel(const uint8_t *queries,
                                    const uint8_t *references,
                                    const DeviceTaskDescriptor *tasks,
                                    int task_count,
                                    int *workspace,
                                    int *column_maxima,
                                    ForwardEndpoint *endpoints)
{
    const int task_index = blockIdx.x * blockDim.x + threadIdx.x;
    if(task_index >= task_count) return;
    const DeviceTaskDescriptor task = tasks[task_index];
    const int padded_query_length = ((task.query_length + 15) / 16) * 16;
    int *task_workspace = workspace + task.workspace_offset;
    int *best_column = task_workspace + 3 * padded_query_length;
    int *task_columns = column_maxima + task.column_offset;
    StripedPassResult pass;
    striped_forward_pass<16, true>(queries + task.query_offset, task.query_length,
                                   references + task.reference_offset, task.reference_length,
                                   task_workspace, task_columns, best_column, &pass);
    if(pass.overflow)
    {
        striped_forward_pass<8, false>(queries + task.query_offset, task.query_length,
                                       references + task.reference_offset, task.reference_length,
                                       task_workspace, task_columns, best_column, &pass);
    }

    ForwardEndpoint endpoint;
    endpoint.task_index = task_index;
    endpoint.score1 = pass.score1;
    endpoint.ref_end1 = pass.ref_end1;
    endpoint.read_end1 = pass.read_end1;
    endpoint.numeric_path = pass.numeric_path;
    int reduced_score1 = 0;
    int reduced_ref_end1 = 0;
    reduce_columns(task_columns, task.reference_length, pass.numeric_path,
                   kContractMaskLength, &reduced_score1, &reduced_ref_end1,
                   &endpoint.score2, &endpoint.ref_end2);
    endpoints[task_index] = endpoint;
}

} // namespace

StatusCode reduce_forward_columns(const std::vector<ColumnReductionInput> &inputs,
                                  const BatchOptions &options,
                                  std::vector<ColumnEndpoint> *endpoints,
                                  Telemetry *telemetry,
                                  std::string *error)
{
    if(endpoints == NULL || telemetry == NULL || error == NULL)
        return STATUS_INVALID_ARGUMENT;
    endpoints->clear();
    *telemetry = Telemetry();
    telemetry->task_count = static_cast<int>(inputs.size());
    telemetry->device = options.device;
    error->clear();
    if(inputs.empty())
    {
        *error = "column-reduction batch is empty";
        return STATUS_INVALID_ARGUMENT;
    }
    if(!contract_is_frozen(options.contract))
    {
        *error = "only the frozen modified-SSW contract is supported";
        return STATUS_UNSUPPORTED_INPUT;
    }

    const std::chrono::steady_clock::time_point packing_start = std::chrono::steady_clock::now();
    std::vector<int> packed_columns;
    std::vector<ColumnDescriptor> descriptors;
    try
    {
        descriptors.reserve(inputs.size());
        for(size_t task = 0; task < inputs.size(); ++task)
        {
            const ColumnReductionInput &input = inputs[task];
            if(input.column_maxima.empty() || input.column_maxima.size() > static_cast<size_t>(INT_MAX) ||
               (input.numeric_path != NUMERIC_PATH_BYTE8 && input.numeric_path != NUMERIC_PATH_WORD16) ||
               input.mask_length != kContractMaskLength)
            {
                *error = input.case_id + ": unsupported column-reduction input";
                return STATUS_UNSUPPORTED_INPUT;
            }
            if(std::find_if(input.column_maxima.begin(), input.column_maxima.end(),
                            [](int value) { return value < 0 || value > 32767; }) !=
               input.column_maxima.end() ||
               packed_columns.size() > static_cast<size_t>(INT_MAX) - input.column_maxima.size())
            {
                *error = input.case_id + ": invalid column score or capacity";
                return STATUS_CAPACITY_EXCEEDED;
            }
            ColumnDescriptor descriptor;
            descriptor.offset = static_cast<int>(packed_columns.size());
            descriptor.length = static_cast<int>(input.column_maxima.size());
            descriptor.numeric_path = input.numeric_path;
            descriptor.mask_length = input.mask_length;
            descriptors.push_back(descriptor);
            packed_columns.insert(packed_columns.end(), input.column_maxima.begin(), input.column_maxima.end());
        }
    }
    catch(const std::bad_alloc &)
    {
        *error = "host column packing allocation failed";
        return STATUS_OUT_OF_MEMORY;
    }
    telemetry->packing_seconds = elapsed_seconds(packing_start);
    telemetry->host_input_bytes = packed_columns.size() * sizeof(int) +
                                  descriptors.size() * sizeof(ColumnDescriptor);
    StatusCode prepared = prepare_device(options, error);
    if(prepared != STATUS_OK) return prepared;

    DeviceBuffer<int> device_columns;
    DeviceBuffer<ColumnDescriptor> device_descriptors;
    DeviceBuffer<ColumnEndpoint> device_endpoints;
    cudaError_t cuda_status;
    if((cuda_status = device_columns.allocate(packed_columns.size())) != cudaSuccess ||
       (cuda_status = device_descriptors.allocate(descriptors.size())) != cudaSuccess ||
       (cuda_status = device_endpoints.allocate(inputs.size())) != cudaSuccess)
        return cuda_failure(cuda_status, "cudaMalloc endpoint reducer", error);
    telemetry->device_input_bytes = telemetry->host_input_bytes;
    telemetry->device_output_bytes = inputs.size() * sizeof(ColumnEndpoint);

    std::chrono::steady_clock::time_point start = std::chrono::steady_clock::now();
    if((cuda_status = cudaMemcpy(device_columns.get(), packed_columns.data(),
                                 packed_columns.size() * sizeof(int), cudaMemcpyHostToDevice)) != cudaSuccess ||
       (cuda_status = cudaMemcpy(device_descriptors.get(), descriptors.data(),
                                 descriptors.size() * sizeof(ColumnDescriptor), cudaMemcpyHostToDevice)) != cudaSuccess)
        return cuda_failure(cuda_status, "cudaMemcpy endpoint reducer H2D", error);
    telemetry->h2d_seconds = elapsed_seconds(start);

    const int threads = 128;
    const int blocks = (static_cast<int>(inputs.size()) + threads - 1) / threads;
    start = std::chrono::steady_clock::now();
    column_endpoint_kernel<<<blocks, threads>>>(device_descriptors.get(),
                                                static_cast<int>(inputs.size()),
                                                device_columns.get(), device_endpoints.get());
    cuda_status = cudaGetLastError();
    if(cuda_status == cudaSuccess) cuda_status = cudaDeviceSynchronize();
    if(cuda_status != cudaSuccess) return cuda_failure(cuda_status, "column_endpoint_kernel", error);
    telemetry->endpoint_reduce_seconds = elapsed_seconds(start);

    try { endpoints->resize(inputs.size()); }
    catch(const std::bad_alloc &)
    {
        *error = "host endpoint allocation failed";
        return STATUS_OUT_OF_MEMORY;
    }
    start = std::chrono::steady_clock::now();
    cuda_status = cudaMemcpy(endpoints->data(), device_endpoints.get(),
                             endpoints->size() * sizeof(ColumnEndpoint), cudaMemcpyDeviceToHost);
    if(cuda_status != cudaSuccess) return cuda_failure(cuda_status, "cudaMemcpy endpoints D2H", error);
    telemetry->d2h_seconds = elapsed_seconds(start);
    return STATUS_OK;
}

StatusCode forward_align(const std::vector<TaskInput> &tasks,
                         const BatchOptions &options,
                         ForwardBatchOutput *output)
{
    if(output == NULL) return STATUS_INVALID_ARGUMENT;
    *output = ForwardBatchOutput();
    output->telemetry.task_count = static_cast<int>(tasks.size());
    output->telemetry.device = options.device;
    const std::chrono::steady_clock::time_point total_start = std::chrono::steady_clock::now();
    if(tasks.empty())
    {
        output->status = STATUS_INVALID_ARGUMENT;
        output->error = "forward batch is empty";
        return output->status;
    }
    if(!contract_is_frozen(options.contract))
    {
        output->status = STATUS_UNSUPPORTED_INPUT;
        output->error = "only the frozen modified-SSW contract is supported";
        return output->status;
    }

    const std::chrono::steady_clock::time_point packing_start = std::chrono::steady_clock::now();
    std::vector<uint8_t> packed_queries;
    std::vector<uint8_t> packed_references;
    std::vector<DeviceTaskDescriptor> descriptors;
    size_t total_columns = 0;
    size_t total_workspace = 0;
    size_t total_cells = 0;
    try
    {
        descriptors.reserve(tasks.size());
        for(size_t task_index = 0; task_index < tasks.size(); ++task_index)
        {
            const TaskInput &task = tasks[task_index];
            if(task.query.empty() || task.reference.empty() ||
               task.query.size() > static_cast<size_t>(kMaximumQueryLength) ||
               task.reference.size() > static_cast<size_t>(kMaximumReferenceLength) ||
               task.threshold < 0 ||
               std::find_if(task.query.begin(), task.query.end(),
                            [](uint8_t value) { return value > 4; }) != task.query.end() ||
               std::find_if(task.reference.begin(), task.reference.end(),
                            [](uint8_t value) { return value > 4; }) != task.reference.end())
            {
                output->status = STATUS_UNSUPPORTED_INPUT;
                output->error = task.case_id + ": unsupported forward input";
                return output->status;
            }
            if(task.query.size() > std::numeric_limits<size_t>::max() / task.reference.size())
            {
                output->status = STATUS_CAPACITY_EXCEEDED;
                output->error = task.case_id + ": DP cell count overflow";
                return output->status;
            }
            const size_t cells = task.query.size() * task.reference.size();
            if(cells > options.maximum_total_dp_cells ||
               total_cells > options.maximum_total_dp_cells - cells)
            {
                output->status = STATUS_CAPACITY_EXCEEDED;
                output->error = "forward batch exceeds maximum_total_dp_cells";
                return output->status;
            }
            total_cells += cells;
            const size_t padded = ((task.query.size() + 15) / 16) * 16;
            const size_t workspace = 4 * padded;
            if(packed_queries.size() > static_cast<size_t>(INT_MAX) - task.query.size() ||
               packed_references.size() > static_cast<size_t>(INT_MAX) - task.reference.size() ||
               total_columns > static_cast<size_t>(INT_MAX) - task.reference.size() ||
               total_workspace > static_cast<size_t>(INT_MAX) - workspace)
            {
                output->status = STATUS_CAPACITY_EXCEEDED;
                output->error = "forward batch exceeds 32-bit kernel indexing";
                return output->status;
            }
            DeviceTaskDescriptor descriptor;
            descriptor.query_offset = static_cast<int>(packed_queries.size());
            descriptor.query_length = static_cast<int>(task.query.size());
            descriptor.reference_offset = static_cast<int>(packed_references.size());
            descriptor.reference_length = static_cast<int>(task.reference.size());
            descriptor.column_offset = static_cast<int>(total_columns);
            descriptor.workspace_offset = static_cast<int>(total_workspace);
            descriptor.threshold = task.threshold;
            descriptors.push_back(descriptor);
            packed_queries.insert(packed_queries.end(), task.query.begin(), task.query.end());
            packed_references.insert(packed_references.end(), task.reference.begin(), task.reference.end());
            total_columns += task.reference.size();
            total_workspace += workspace;
        }
    }
    catch(const std::bad_alloc &)
    {
        output->status = STATUS_OUT_OF_MEMORY;
        output->error = "host forward packing allocation failed";
        return output->status;
    }
    output->telemetry.packing_seconds = elapsed_seconds(packing_start);
    output->telemetry.host_input_bytes = packed_queries.size() + packed_references.size() +
                                         descriptors.size() * sizeof(DeviceTaskDescriptor);
    output->status = prepare_device(options, &output->error);
    if(output->status != STATUS_OK) return output->status;

    DeviceBuffer<uint8_t> device_queries;
    DeviceBuffer<uint8_t> device_references;
    DeviceBuffer<DeviceTaskDescriptor> device_tasks;
    DeviceBuffer<int> device_workspace;
    DeviceBuffer<int> device_columns;
    DeviceBuffer<ForwardEndpoint> device_endpoints;
    cudaError_t cuda_status;
    if((cuda_status = device_queries.allocate(packed_queries.size())) != cudaSuccess ||
       (cuda_status = device_references.allocate(packed_references.size())) != cudaSuccess ||
       (cuda_status = device_tasks.allocate(descriptors.size())) != cudaSuccess ||
       (cuda_status = device_workspace.allocate(total_workspace)) != cudaSuccess ||
       (cuda_status = device_columns.allocate(total_columns)) != cudaSuccess ||
       (cuda_status = device_endpoints.allocate(tasks.size())) != cudaSuccess)
    {
        output->status = cuda_failure(cuda_status, "cudaMalloc forward", &output->error);
        return output->status;
    }
    output->telemetry.device_input_bytes = output->telemetry.host_input_bytes;
    output->telemetry.device_workspace_bytes = total_workspace * sizeof(int);
    output->telemetry.device_output_bytes = total_columns * sizeof(int) +
                                            tasks.size() * sizeof(ForwardEndpoint);

    std::chrono::steady_clock::time_point start = std::chrono::steady_clock::now();
    if((cuda_status = cudaMemcpy(device_queries.get(), packed_queries.data(), packed_queries.size(),
                                 cudaMemcpyHostToDevice)) != cudaSuccess ||
       (cuda_status = cudaMemcpy(device_references.get(), packed_references.data(), packed_references.size(),
                                 cudaMemcpyHostToDevice)) != cudaSuccess ||
       (cuda_status = cudaMemcpy(device_tasks.get(), descriptors.data(),
                                 descriptors.size() * sizeof(DeviceTaskDescriptor), cudaMemcpyHostToDevice)) != cudaSuccess ||
       (cuda_status = cudaMemset(device_columns.get(), 0, total_columns * sizeof(int))) != cudaSuccess)
    {
        output->status = cuda_failure(cuda_status, "cudaMemcpy forward H2D", &output->error);
        return output->status;
    }
    output->telemetry.h2d_seconds = elapsed_seconds(start);

    const int threads = 128;
    const int blocks = (static_cast<int>(tasks.size()) + threads - 1) / threads;
    start = std::chrono::steady_clock::now();
    full_forward_kernel<<<blocks, threads>>>(device_queries.get(), device_references.get(),
                                             device_tasks.get(), static_cast<int>(tasks.size()),
                                             device_workspace.get(), device_columns.get(),
                                             device_endpoints.get());
    cuda_status = cudaGetLastError();
    if(cuda_status == cudaSuccess) cuda_status = cudaDeviceSynchronize();
    if(cuda_status != cudaSuccess)
    {
        output->status = cuda_failure(cuda_status, "full_forward_kernel", &output->error);
        return output->status;
    }
    output->telemetry.forward_seconds = elapsed_seconds(start);

    try
    {
        output->endpoints.resize(tasks.size());
        output->column_offsets.reserve(tasks.size() + 1);
        for(size_t task = 0; task < descriptors.size(); ++task)
            output->column_offsets.push_back(descriptors[task].column_offset);
        output->column_offsets.push_back(static_cast<int>(total_columns));
        if(options.export_full_column_vectors) output->column_maxima.resize(total_columns);
    }
    catch(const std::bad_alloc &)
    {
        output->status = STATUS_OUT_OF_MEMORY;
        output->error = "host forward output allocation failed";
        return output->status;
    }
    start = std::chrono::steady_clock::now();
    cuda_status = cudaMemcpy(output->endpoints.data(), device_endpoints.get(),
                             output->endpoints.size() * sizeof(ForwardEndpoint),
                             cudaMemcpyDeviceToHost);
    if(cuda_status == cudaSuccess && options.export_full_column_vectors)
        cuda_status = cudaMemcpy(output->column_maxima.data(), device_columns.get(),
                                 total_columns * sizeof(int), cudaMemcpyDeviceToHost);
    if(cuda_status != cudaSuccess)
    {
        output->status = cuda_failure(cuda_status, "cudaMemcpy forward D2H", &output->error);
        return output->status;
    }
    output->telemetry.d2h_seconds = elapsed_seconds(start);
    output->status = STATUS_OK;
    output->error.clear();
    output->telemetry.total_wall_seconds = elapsed_seconds(total_start);
    const double accounted = output->telemetry.packing_seconds + output->telemetry.h2d_seconds +
                             output->telemetry.forward_seconds + output->telemetry.d2h_seconds;
    output->telemetry.overhead_seconds = std::max(
        0.0, output->telemetry.total_wall_seconds - accounted);
    return output->status;
}

} // namespace fasim_ssw_cuda
