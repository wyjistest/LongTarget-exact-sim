#include "ssw_cuda_api.h"
#include "ssw_cuda_internal.h"

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
    DeviceBuffer():pointer_(NULL), count_(0) {}
    ~DeviceBuffer() { reset(); }

    cudaError_t allocate(size_t count)
    {
        reset();
        count_ = count;
        if(count == 0)
        {
            return cudaSuccess;
        }
        const cudaError_t status = cudaMalloc(reinterpret_cast<void **>(&pointer_), count * sizeof(T));
        if(status != cudaSuccess)
        {
            pointer_ = NULL;
            count_ = 0;
        }
        return status;
    }

    void reset()
    {
        if(pointer_ != NULL)
        {
            cudaFree(pointer_);
            pointer_ = NULL;
            count_ = 0;
        }
    }

    T *get() { return pointer_; }
    const T *get() const { return pointer_; }
    size_t count() const { return count_; }

private:
    DeviceBuffer(const DeviceBuffer &);
    DeviceBuffer &operator=(const DeviceBuffer &);

    T *pointer_;
    size_t count_;
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
    if(status == cudaErrorMemoryAllocation)
    {
        return STATUS_OUT_OF_MEMORY;
    }
    if(status == cudaErrorNoDevice || status == cudaErrorInsufficientDriver ||
       status == cudaErrorInitializationError)
    {
        return STATUS_CUDA_UNAVAILABLE;
    }
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

__device__ int saturating_add(int left, int right, int maximum)
{
    const int value = left + right;
    return value > maximum ? maximum : value;
}

__device__ int saturating_subtract(int left, int right)
{
    return left > right ? left - right : 0;
}

template <int kLanes, bool kBytePath>
__device__ void striped_prealign_pass(const uint8_t *query,
                                      int query_length,
                                      const uint8_t *reference,
                                      int reference_length,
                                      int *workspace,
                                      int *column_maxima)
{
    const int segment_length = (query_length + kLanes - 1) / kLanes;
    const int numeric_maximum = kBytePath ? 255 : 32767;
    int *h_store = workspace;
    int *h_load = h_store + segment_length * kLanes;
    int *e_values = h_load + segment_length * kLanes;
    for(int index = 0; index < 3 * segment_length * kLanes; ++index)
    {
        workspace[index] = 0;
    }

    int global_lane_maximum[kLanes];
    int global_lane_mark[kLanes];
    for(int lane = 0; lane < kLanes; ++lane)
    {
        global_lane_maximum[lane] = 0;
        global_lane_mark[lane] = 0;
    }
    int global_maximum = 0;

    for(int column = 0; column < reference_length; ++column)
    {
        int h_value[kLanes];
        int f_value[kLanes];
        int column_lane_maximum[kLanes];
        const int last_segment_offset = (segment_length - 1) * kLanes;
        h_value[0] = 0;
        for(int lane = 1; lane < kLanes; ++lane)
        {
            h_value[lane] = h_store[last_segment_offset + lane - 1];
        }
        for(int lane = 0; lane < kLanes; ++lane)
        {
            f_value[lane] = 0;
            column_lane_maximum[lane] = 0;
        }

        int *swap = h_load;
        h_load = h_store;
        h_store = swap;

        for(int segment = 0; segment < segment_length; ++segment)
        {
            const int offset = segment * kLanes;
            for(int lane = 0; lane < kLanes; ++lane)
            {
                const int query_index = segment + lane * segment_length;
                int substitution = 0;
                if(query_index < query_length)
                {
                    substitution = query[query_index] == reference[column] && query[query_index] < 4 ?
                                   kContractMatch : -kContractMismatchPenalty;
                }
                if(kBytePath)
                {
                    h_value[lane] = saturating_add(h_value[lane], substitution + 4, numeric_maximum);
                    h_value[lane] = saturating_subtract(h_value[lane], 4);
                }
                else
                {
                    h_value[lane] = saturating_add(h_value[lane], substitution, numeric_maximum);
                    if(h_value[lane] < 0) h_value[lane] = 0;
                }
                if(e_values[offset + lane] > h_value[lane]) h_value[lane] = e_values[offset + lane];
                if(f_value[lane] > h_value[lane]) h_value[lane] = f_value[lane];
                if(h_value[lane] > column_lane_maximum[lane])
                    column_lane_maximum[lane] = h_value[lane];
                h_store[offset + lane] = h_value[lane];

                const int opened = saturating_subtract(h_value[lane], kContractGapOpen);
                const int extended_e = saturating_subtract(e_values[offset + lane], kContractGapExtend);
                e_values[offset + lane] = opened > extended_e ? opened : extended_e;
                const int extended_f = saturating_subtract(f_value[lane], kContractGapExtend);
                f_value[lane] = opened > extended_f ? opened : extended_f;
                h_value[lane] = h_load[offset + lane];
            }
        }

        bool lazy_done = false;
        for(int iteration = 0; iteration < kLanes && !lazy_done; ++iteration)
        {
            for(int lane = kLanes - 1; lane > 0; --lane)
            {
                f_value[lane] = f_value[lane - 1];
            }
            f_value[0] = 0;
            for(int segment = 0; segment < segment_length; ++segment)
            {
                const int offset = segment * kLanes;
                bool any_greater = false;
                for(int lane = 0; lane < kLanes; ++lane)
                {
                    int stored = h_store[offset + lane];
                    if(f_value[lane] > stored) stored = f_value[lane];
                    h_store[offset + lane] = stored;
                    if(stored > column_lane_maximum[lane]) column_lane_maximum[lane] = stored;
                    const int opened = saturating_subtract(stored, kContractGapOpen);
                    f_value[lane] = saturating_subtract(f_value[lane], kContractGapExtend);
                    if(kBytePath)
                    {
                        if(static_cast<int8_t>(f_value[lane]) > static_cast<int8_t>(opened))
                            any_greater = true;
                    }
                    else if(f_value[lane] > opened)
                    {
                        any_greater = true;
                    }
                }
                if(!any_greater)
                {
                    lazy_done = true;
                    break;
                }
            }
        }

        bool lane_maximum_changed = false;
        int current_global_maximum = 0;
        int scalar_column_maximum = 0;
        for(int lane = 0; lane < kLanes; ++lane)
        {
            if(column_lane_maximum[lane] > global_lane_maximum[lane])
                global_lane_maximum[lane] = column_lane_maximum[lane];
            if(global_lane_mark[lane] != global_lane_maximum[lane]) lane_maximum_changed = true;
            if(global_lane_maximum[lane] > current_global_maximum)
                current_global_maximum = global_lane_maximum[lane];
            if(column_lane_maximum[lane] > scalar_column_maximum)
                scalar_column_maximum = column_lane_maximum[lane];
        }
        if(lane_maximum_changed)
        {
            for(int lane = 0; lane < kLanes; ++lane)
                global_lane_mark[lane] = global_lane_maximum[lane];
            if(current_global_maximum > global_maximum)
            {
                global_maximum = current_global_maximum;
                if(kBytePath && global_maximum + 4 >= 255)
                {
                    break;
                }
            }
        }
        column_maxima[column] = scalar_column_maximum;
    }
}

__global__ void prealign_reference_kernel(const uint8_t *queries,
                                          const uint8_t *references,
                                          const DeviceTaskDescriptor *tasks,
                                          int task_count,
                                          int *workspace,
                                          int *column_maxima)
{
    const int task_index = blockIdx.x * blockDim.x + threadIdx.x;
    if(task_index >= task_count)
    {
        return;
    }

    const DeviceTaskDescriptor task = tasks[task_index];
    const uint8_t *query = queries + task.query_offset;
    const uint8_t *reference = references + task.reference_offset;
    int *task_workspace = workspace + task.workspace_offset;
    int *task_columns = column_maxima + task.column_offset;
    striped_prealign_pass<16, true>(query, task.query_length, reference,
                                    task.reference_length, task_workspace, task_columns);
    int byte_maximum = 0;
    for(int column = 0; column < task.reference_length; ++column)
    {
        if(task_columns[column] > byte_maximum) byte_maximum = task_columns[column];
    }
    if(byte_maximum >= 255)
    {
        striped_prealign_pass<8, false>(query, task.query_length, reference,
                                        task.reference_length, task_workspace, task_columns);
    }
}

} // namespace

bool is_built()
{
    return true;
}

StatusCode pre_align_and_select(const std::vector<TaskInput> &tasks,
                                const BatchOptions &options,
                                BatchOutput *output)
{
    if(output == NULL)
    {
        return STATUS_INVALID_ARGUMENT;
    }
    *output = BatchOutput();
    output->telemetry.task_count = static_cast<int>(tasks.size());
    output->telemetry.device = options.device;
    const std::chrono::steady_clock::time_point total_start = std::chrono::steady_clock::now();

    if(tasks.empty())
    {
        output->status = STATUS_INVALID_ARGUMENT;
        output->error = "task batch is empty";
        return output->status;
    }
    if(!contract_is_frozen(options.contract))
    {
        output->status = STATUS_UNSUPPORTED_INPUT;
        output->error = "only the frozen modified-SSW contract is supported";
        return output->status;
    }
    if(options.device < 0)
    {
        output->status = STATUS_INVALID_ARGUMENT;
        output->error = "CUDA device index is negative";
        return output->status;
    }

    const std::chrono::steady_clock::time_point packing_start = std::chrono::steady_clock::now();
    std::vector<uint8_t> packed_queries;
    std::vector<uint8_t> packed_references;
    std::vector<DeviceTaskDescriptor> descriptors;
    size_t total_columns_size = 0;
    size_t total_workspace_size = 0;
    size_t total_dp_cells = 0;

    try
    {
        descriptors.reserve(tasks.size());
        for(size_t task_index = 0; task_index < tasks.size(); ++task_index)
        {
            const TaskInput &task = tasks[task_index];
            if(task.query.empty() || task.reference.empty())
            {
                output->status = STATUS_UNSUPPORTED_INPUT;
                output->error = task.case_id + ": empty query or reference";
                return output->status;
            }
            if(task.query.size() > static_cast<size_t>(kMaximumQueryLength) ||
               task.reference.size() > static_cast<size_t>(kMaximumReferenceLength))
            {
                output->status = STATUS_UNSUPPORTED_INPUT;
                output->error = task.case_id + ": sequence length is outside the Phase 5 contract";
                return output->status;
            }
            if(task.threshold < 0)
            {
                output->status = STATUS_UNSUPPORTED_INPUT;
                output->error = task.case_id + ": negative threshold is unsupported";
                return output->status;
            }
            if(std::find_if(task.query.begin(), task.query.end(),
                            [](uint8_t value) { return value > 4; }) != task.query.end() ||
               std::find_if(task.reference.begin(), task.reference.end(),
                            [](uint8_t value) { return value > 4; }) != task.reference.end())
            {
                output->status = STATUS_UNSUPPORTED_INPUT;
                output->error = task.case_id + ": translated bases must be in [0,4]";
                return output->status;
            }

            if(task.query.size() > std::numeric_limits<size_t>::max() / task.reference.size())
            {
                output->status = STATUS_CAPACITY_EXCEEDED;
                output->error = task.case_id + ": DP cell count overflow";
                return output->status;
            }
            const size_t task_cells = task.query.size() * task.reference.size();
            if(task_cells > options.maximum_total_dp_cells ||
               total_dp_cells > options.maximum_total_dp_cells - task_cells)
            {
                output->status = STATUS_CAPACITY_EXCEEDED;
                output->error = "batch exceeds maximum_total_dp_cells";
                return output->status;
            }
            total_dp_cells += task_cells;

            const size_t padded_query_length = ((task.query.size() + 15) / 16) * 16;
            const size_t task_workspace = 3 * padded_query_length;
            if(packed_queries.size() > static_cast<size_t>(INT_MAX) - task.query.size() ||
               packed_references.size() > static_cast<size_t>(INT_MAX) - task.reference.size() ||
               total_columns_size > static_cast<size_t>(INT_MAX) - task.reference.size() ||
               total_workspace_size > static_cast<size_t>(INT_MAX) - task_workspace)
            {
                output->status = STATUS_CAPACITY_EXCEEDED;
                output->error = "packed batch exceeds 32-bit kernel indexing";
                return output->status;
            }

            DeviceTaskDescriptor descriptor;
            descriptor.query_offset = static_cast<int>(packed_queries.size());
            descriptor.query_length = static_cast<int>(task.query.size());
            descriptor.reference_offset = static_cast<int>(packed_references.size());
            descriptor.reference_length = static_cast<int>(task.reference.size());
            descriptor.column_offset = static_cast<int>(total_columns_size);
            descriptor.workspace_offset = static_cast<int>(total_workspace_size);
            descriptor.threshold = task.threshold;
            descriptors.push_back(descriptor);

            packed_queries.insert(packed_queries.end(), task.query.begin(), task.query.end());
            packed_references.insert(packed_references.end(), task.reference.begin(), task.reference.end());
            total_columns_size += task.reference.size();
            total_workspace_size += task_workspace;
        }
    }
    catch(const std::bad_alloc &)
    {
        output->status = STATUS_OUT_OF_MEMORY;
        output->error = "host packing allocation failed";
        return output->status;
    }
    output->telemetry.packing_seconds = elapsed_seconds(packing_start);
    output->telemetry.host_input_bytes = packed_queries.size() + packed_references.size() +
                                         descriptors.size() * sizeof(DeviceTaskDescriptor);

    int device_count = 0;
    cudaError_t cuda_status = cudaGetDeviceCount(&device_count);
    if(cuda_status != cudaSuccess || device_count == 0)
    {
        output->status = cuda_failure(cuda_status == cudaSuccess ? cudaErrorNoDevice : cuda_status,
                                      "cudaGetDeviceCount", &output->error);
        return output->status;
    }
    if(options.device >= device_count)
    {
        output->status = STATUS_INVALID_ARGUMENT;
        output->error = "CUDA device index is out of range";
        return output->status;
    }
    cuda_status = cudaSetDevice(options.device);
    if(cuda_status != cudaSuccess)
    {
        output->status = cuda_failure(cuda_status, "cudaSetDevice", &output->error);
        return output->status;
    }
    if(options.force_out_of_memory_for_test)
    {
        output->status = STATUS_OUT_OF_MEMORY;
        output->error = "forced device allocation failure for fail-closed testing";
        return output->status;
    }

    DeviceBuffer<uint8_t> device_queries;
    DeviceBuffer<uint8_t> device_references;
    DeviceBuffer<DeviceTaskDescriptor> device_tasks;
    DeviceBuffer<int> device_workspace;
    DeviceBuffer<int> device_columns;

    if((cuda_status = device_queries.allocate(packed_queries.size())) != cudaSuccess ||
       (cuda_status = device_references.allocate(packed_references.size())) != cudaSuccess ||
       (cuda_status = device_tasks.allocate(descriptors.size())) != cudaSuccess ||
       (cuda_status = device_workspace.allocate(total_workspace_size)) != cudaSuccess ||
       (cuda_status = device_columns.allocate(total_columns_size)) != cudaSuccess)
    {
        output->status = cuda_failure(cuda_status, "cudaMalloc", &output->error);
        return output->status;
    }
    output->telemetry.device_input_bytes = packed_queries.size() + packed_references.size() +
                                           descriptors.size() * sizeof(DeviceTaskDescriptor);
    output->telemetry.device_workspace_bytes = total_workspace_size * sizeof(int);
    output->telemetry.device_output_bytes = total_columns_size * sizeof(int);

    const std::chrono::steady_clock::time_point h2d_start = std::chrono::steady_clock::now();
    if((cuda_status = cudaMemcpy(device_queries.get(), packed_queries.data(), packed_queries.size(),
                                 cudaMemcpyHostToDevice)) != cudaSuccess ||
       (cuda_status = cudaMemcpy(device_references.get(), packed_references.data(), packed_references.size(),
                                 cudaMemcpyHostToDevice)) != cudaSuccess ||
       (cuda_status = cudaMemcpy(device_tasks.get(), descriptors.data(),
                                 descriptors.size() * sizeof(DeviceTaskDescriptor),
                                 cudaMemcpyHostToDevice)) != cudaSuccess)
    {
        output->status = cuda_failure(cuda_status, "cudaMemcpy H2D", &output->error);
        return output->status;
    }
    output->telemetry.h2d_seconds = elapsed_seconds(h2d_start);

    const std::chrono::steady_clock::time_point kernel_start = std::chrono::steady_clock::now();
    cuda_status = cudaMemset(device_columns.get(), 0, total_columns_size * sizeof(int));
    if(cuda_status != cudaSuccess)
    {
        output->status = cuda_failure(cuda_status, "cudaMemset column output", &output->error);
        return output->status;
    }
    const int threads = 128;
    const int blocks = (static_cast<int>(tasks.size()) + threads - 1) / threads;
    prealign_reference_kernel<<<blocks, threads>>>(device_queries.get(), device_references.get(),
                                                   device_tasks.get(), static_cast<int>(tasks.size()),
                                                   device_workspace.get(), device_columns.get());
    cuda_status = cudaGetLastError();
    if(cuda_status == cudaSuccess)
    {
        cuda_status = cudaDeviceSynchronize();
    }
    if(cuda_status != cudaSuccess)
    {
        output->status = cuda_failure(cuda_status, "prealign_reference_kernel", &output->error);
        return output->status;
    }
    output->telemetry.prealign_seconds = elapsed_seconds(kernel_start);

    output->column_offsets.reserve(descriptors.size() + 1);
    for(size_t i = 0; i < descriptors.size(); ++i)
    {
        output->column_offsets.push_back(descriptors[i].column_offset);
    }
    output->column_offsets.push_back(static_cast<int>(total_columns_size));

    output->status = select_device_scoreinfos(device_tasks.get(), static_cast<int>(tasks.size()),
                                               device_columns.get(), static_cast<int>(total_columns_size),
                                               &output->selection_offsets, &output->scoreinfos,
                                               &output->telemetry, &output->error);
    if(output->status != STATUS_OK)
    {
        return output->status;
    }

    if(options.export_full_column_vectors)
    {
        const std::chrono::steady_clock::time_point d2h_start = std::chrono::steady_clock::now();
        try
        {
            output->column_maxima.resize(total_columns_size);
        }
        catch(const std::bad_alloc &)
        {
            output->status = STATUS_OUT_OF_MEMORY;
            output->error = "host column-output allocation failed";
            return output->status;
        }
        cuda_status = cudaMemcpy(output->column_maxima.data(), device_columns.get(),
                                 total_columns_size * sizeof(int), cudaMemcpyDeviceToHost);
        if(cuda_status != cudaSuccess)
        {
            output->status = cuda_failure(cuda_status, "cudaMemcpy columns D2H", &output->error);
            return output->status;
        }
        output->telemetry.d2h_seconds += elapsed_seconds(d2h_start);
    }

    output->status = STATUS_OK;
    output->error.clear();
    output->telemetry.total_wall_seconds = elapsed_seconds(total_start);
    const double accounted = output->telemetry.packing_seconds + output->telemetry.h2d_seconds +
                             output->telemetry.prealign_seconds + output->telemetry.selection_flag_seconds +
                             output->telemetry.selection_scan_seconds + output->telemetry.selection_scatter_seconds +
                             output->telemetry.d2h_seconds;
    output->telemetry.overhead_seconds = std::max(0.0, output->telemetry.total_wall_seconds - accounted);
    return output->status;
}

} // namespace fasim_ssw_cuda
