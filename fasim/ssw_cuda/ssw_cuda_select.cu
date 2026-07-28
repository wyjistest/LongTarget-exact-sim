#include "ssw_cuda_api.h"
#include "ssw_cuda_internal.h"

#include <cuda_runtime.h>

#include <algorithm>
#include <chrono>
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
private:
    DeviceBuffer(const DeviceBuffer &);
    DeviceBuffer &operator=(const DeviceBuffer &);
    T *pointer_;
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
    return status == cudaErrorMemoryAllocation ? STATUS_OUT_OF_MEMORY : STATUS_CUDA_ERROR;
}

__global__ void selection_flag_kernel(const DeviceTaskDescriptor *tasks,
                                      int task_count,
                                      const int *columns,
                                      uint8_t *flags)
{
    const int task_index = blockIdx.x * blockDim.x + threadIdx.x;
    if(task_index >= task_count)
    {
        return;
    }
    const DeviceTaskDescriptor task = tasks[task_index];
    bool have_group = false;
    int previous_position = -1;
    int best_position = -1;
    int best_score = -1;

    for(int position = 0; position < task.reference_length; ++position)
    {
        const int score = columns[task.column_offset + position];
        if(score <= task.threshold)
        {
            continue;
        }
        if(!have_group || position - previous_position >= 5)
        {
            if(have_group)
            {
                flags[task.column_offset + best_position] = 1;
            }
            have_group = true;
            best_position = position;
            best_score = score;
        }
        else if(score > best_score)
        {
            best_position = position;
            best_score = score;
        }
        previous_position = position;
    }
    if(have_group)
    {
        flags[task.column_offset + best_position] = 1;
    }
}

__global__ void selection_scan_kernel(const DeviceTaskDescriptor *tasks,
                                      int task_count,
                                      const uint8_t *flags,
                                      int *scans,
                                      int *counts)
{
    const int task_index = blockIdx.x * blockDim.x + threadIdx.x;
    if(task_index >= task_count)
    {
        return;
    }
    const DeviceTaskDescriptor task = tasks[task_index];
    int count = 0;
    for(int position = 0; position < task.reference_length; ++position)
    {
        const int offset = task.column_offset + position;
        scans[offset] = count;
        count += flags[offset] != 0 ? 1 : 0;
    }
    counts[task_index] = count;
}

__global__ void selection_scatter_kernel(const DeviceTaskDescriptor *tasks,
                                         int task_count,
                                         const int *columns,
                                         const uint8_t *flags,
                                         const int *scans,
                                         const int *selection_offsets,
                                         DeviceScoreInfo *scoreinfos)
{
    const int task_index = blockIdx.x;
    if(task_index >= task_count)
    {
        return;
    }
    const DeviceTaskDescriptor task = tasks[task_index];
    for(int position = threadIdx.x; position < task.reference_length; position += blockDim.x)
    {
        const int column_offset = task.column_offset + position;
        if(flags[column_offset] == 0)
        {
            continue;
        }
        const int index = scans[column_offset];
        DeviceScoreInfo item;
        item.task_index = task_index;
        item.index = index;
        item.score = columns[column_offset];
        item.position = position;
        item.reason = SCOREINFO_THRESHOLD_RUN_MAX;
        scoreinfos[selection_offsets[task_index] + index] = item;
    }
}

bool valid_observation(const AttemptObservation &observation)
{
    return observation.scoreinfo_index >= 0 && observation.attempt_order >= 0 &&
           observation.prealign_score >= 0 && observation.alignment_score >= 0 &&
           observation.ref_end >= -1 && observation.cutlength > 0;
}

} // namespace

ContractConfig::ContractConfig():
    match(kContractMatch), mismatch_penalty(kContractMismatchPenalty),
    gap_open(kContractGapOpen), gap_extend(kContractGapExtend),
    mask_length(kContractMaskLength), flag(0),
    score_filter(kContractScoreFilter), distance_filter(kContractDistanceFilter)
{
}

BatchOptions::BatchOptions():
    device(0), export_full_column_vectors(false), force_out_of_memory_for_test(false),
    maximum_total_dp_cells(static_cast<size_t>(1) << 31)
{
}

Telemetry::Telemetry():
    packing_seconds(0.0), h2d_seconds(0.0), prealign_seconds(0.0),
    forward_seconds(0.0), endpoint_reduce_seconds(0.0),
    selection_flag_seconds(0.0), selection_scan_seconds(0.0),
    selection_scatter_seconds(0.0), d2h_seconds(0.0), overhead_seconds(0.0),
    total_wall_seconds(0.0), host_input_bytes(0), device_input_bytes(0),
    device_workspace_bytes(0), device_output_bytes(0), task_count(0), device(-1),
    cpu_endpoint_calls(0)
{
}

BatchOutput::BatchOutput():status(STATUS_NOT_BUILT)
{
}

ForwardBatchOutput::ForwardBatchOutput():status(STATUS_NOT_BUILT)
{
}

const char *status_name(StatusCode status)
{
    switch(status)
    {
    case STATUS_OK: return "ok";
    case STATUS_NOT_BUILT: return "not_built";
    case STATUS_CUDA_UNAVAILABLE: return "cuda_unavailable";
    case STATUS_INVALID_ARGUMENT: return "invalid_argument";
    case STATUS_UNSUPPORTED_INPUT: return "unsupported_input";
    case STATUS_CAPACITY_EXCEEDED: return "capacity_exceeded";
    case STATUS_OUT_OF_MEMORY: return "out_of_memory";
    case STATUS_CUDA_ERROR: return "cuda_error";
    default: return "internal_error";
    }
}

const char *scoreinfo_reason_name(int reason)
{
    return reason == SCOREINFO_THRESHOLD_RUN_MAX ? "threshold_run_max" : "unknown";
}

const char *attempt_reason_name(int reason)
{
    switch(reason)
    {
    case ATTEMPT_THRESHOLD: return "threshold";
    case ATTEMPT_BEST_FALLBACK: return "best_fallback";
    case ATTEMPT_LAST: return "last";
    case ATTEMPT_NOT_SELECTED_AFTER_THRESHOLD: return "not_selected_after_threshold";
    case ATTEMPT_NOT_SELECTED_LOWER_SCORE: return "not_selected_lower_score";
    case ATTEMPT_NOT_SELECTED: return "not_selected";
    default: return "unknown";
    }
}

StatusCode select_device_scoreinfos(const DeviceTaskDescriptor *device_tasks,
                                    int task_count,
                                    const int *device_column_maxima,
                                    int total_columns,
                                    std::vector<int> *selection_offsets,
                                    std::vector<ScoreInfo> *scoreinfos,
                                    Telemetry *telemetry,
                                    std::string *error)
{
    if(device_tasks == NULL || task_count <= 0 || device_column_maxima == NULL ||
       total_columns <= 0 || selection_offsets == NULL || scoreinfos == NULL || telemetry == NULL)
    {
        if(error != NULL) *error = "invalid device-selection argument";
        return STATUS_INVALID_ARGUMENT;
    }

    DeviceBuffer<uint8_t> flags;
    DeviceBuffer<int> scans;
    DeviceBuffer<int> counts;
    cudaError_t cuda_status;
    if((cuda_status = flags.allocate(static_cast<size_t>(total_columns))) != cudaSuccess ||
       (cuda_status = scans.allocate(static_cast<size_t>(total_columns))) != cudaSuccess ||
       (cuda_status = counts.allocate(static_cast<size_t>(task_count))) != cudaSuccess)
    {
        return cuda_failure(cuda_status, "cudaMalloc selection workspace", error);
    }
    telemetry->device_workspace_bytes += static_cast<size_t>(total_columns) * (sizeof(uint8_t) + sizeof(int)) +
                                         static_cast<size_t>(task_count) * sizeof(int);
    if((cuda_status = cudaMemset(flags.get(), 0, static_cast<size_t>(total_columns))) != cudaSuccess)
    {
        return cuda_failure(cuda_status, "cudaMemset selection flags", error);
    }

    const int threads = 128;
    const int blocks = (task_count + threads - 1) / threads;
    std::chrono::steady_clock::time_point start = std::chrono::steady_clock::now();
    selection_flag_kernel<<<blocks, threads>>>(device_tasks, task_count, device_column_maxima, flags.get());
    cuda_status = cudaGetLastError();
    if(cuda_status == cudaSuccess) cuda_status = cudaDeviceSynchronize();
    if(cuda_status != cudaSuccess) return cuda_failure(cuda_status, "selection_flag_kernel", error);
    telemetry->selection_flag_seconds = elapsed_seconds(start);

    start = std::chrono::steady_clock::now();
    selection_scan_kernel<<<blocks, threads>>>(device_tasks, task_count, flags.get(), scans.get(), counts.get());
    cuda_status = cudaGetLastError();
    if(cuda_status == cudaSuccess) cuda_status = cudaDeviceSynchronize();
    if(cuda_status != cudaSuccess) return cuda_failure(cuda_status, "selection_scan_kernel", error);
    telemetry->selection_scan_seconds = elapsed_seconds(start);

    std::vector<int> host_counts;
    try
    {
        host_counts.resize(static_cast<size_t>(task_count));
        selection_offsets->assign(static_cast<size_t>(task_count) + 1, 0);
    }
    catch(const std::bad_alloc &)
    {
        if(error != NULL) *error = "host selection-count allocation failed";
        return STATUS_OUT_OF_MEMORY;
    }
    start = std::chrono::steady_clock::now();
    cuda_status = cudaMemcpy(host_counts.data(), counts.get(), static_cast<size_t>(task_count) * sizeof(int),
                             cudaMemcpyDeviceToHost);
    if(cuda_status != cudaSuccess) return cuda_failure(cuda_status, "cudaMemcpy selection counts D2H", error);
    telemetry->d2h_seconds += elapsed_seconds(start);
    for(int task = 0; task < task_count; ++task)
    {
        (*selection_offsets)[static_cast<size_t>(task) + 1] =
            (*selection_offsets)[static_cast<size_t>(task)] + host_counts[static_cast<size_t>(task)];
    }
    const int total_scoreinfos = selection_offsets->back();
    if(total_scoreinfos < 0 || total_scoreinfos > total_columns)
    {
        if(error != NULL) *error = "invalid compacted scoreInfo count";
        return STATUS_INTERNAL_ERROR;
    }
    if(total_scoreinfos == 0)
    {
        scoreinfos->clear();
        return STATUS_OK;
    }

    DeviceBuffer<int> device_selection_offsets;
    DeviceBuffer<DeviceScoreInfo> device_scoreinfos;
    if((cuda_status = device_selection_offsets.allocate(selection_offsets->size())) != cudaSuccess ||
       (cuda_status = device_scoreinfos.allocate(static_cast<size_t>(total_scoreinfos))) != cudaSuccess)
    {
        return cuda_failure(cuda_status, "cudaMalloc compact scoreInfos", error);
    }
    telemetry->device_output_bytes += static_cast<size_t>(total_scoreinfos) * sizeof(DeviceScoreInfo);
    cuda_status = cudaMemcpy(device_selection_offsets.get(), selection_offsets->data(),
                             selection_offsets->size() * sizeof(int), cudaMemcpyHostToDevice);
    if(cuda_status != cudaSuccess) return cuda_failure(cuda_status, "cudaMemcpy selection offsets H2D", error);

    start = std::chrono::steady_clock::now();
    selection_scatter_kernel<<<task_count, 128>>>(device_tasks, task_count, device_column_maxima,
                                                  flags.get(), scans.get(), device_selection_offsets.get(),
                                                  device_scoreinfos.get());
    cuda_status = cudaGetLastError();
    if(cuda_status == cudaSuccess) cuda_status = cudaDeviceSynchronize();
    if(cuda_status != cudaSuccess) return cuda_failure(cuda_status, "selection_scatter_kernel", error);
    telemetry->selection_scatter_seconds = elapsed_seconds(start);

    std::vector<DeviceScoreInfo> host_scoreinfos;
    try
    {
        host_scoreinfos.resize(static_cast<size_t>(total_scoreinfos));
        scoreinfos->resize(static_cast<size_t>(total_scoreinfos));
    }
    catch(const std::bad_alloc &)
    {
        if(error != NULL) *error = "host scoreInfo allocation failed";
        return STATUS_OUT_OF_MEMORY;
    }
    start = std::chrono::steady_clock::now();
    cuda_status = cudaMemcpy(host_scoreinfos.data(), device_scoreinfos.get(),
                             host_scoreinfos.size() * sizeof(DeviceScoreInfo), cudaMemcpyDeviceToHost);
    if(cuda_status != cudaSuccess) return cuda_failure(cuda_status, "cudaMemcpy scoreInfos D2H", error);
    telemetry->d2h_seconds += elapsed_seconds(start);
    for(size_t index = 0; index < host_scoreinfos.size(); ++index)
    {
        const DeviceScoreInfo &source = host_scoreinfos[index];
        ScoreInfo &destination = (*scoreinfos)[index];
        destination.task_index = source.task_index;
        destination.index = source.index;
        destination.score = source.score;
        destination.position = source.position;
        destination.reason = source.reason;
    }
    return STATUS_OK;
}

StatusCode select_attempts(const std::vector<AttemptObservation> &observations,
                           std::vector<AttemptDecision> *decisions,
                           std::string *error)
{
    if(decisions == NULL)
    {
        if(error != NULL) *error = "decisions output is null";
        return STATUS_INVALID_ARGUMENT;
    }
    decisions->clear();
    if(error != NULL) error->clear();
    if(observations.empty())
    {
        return STATUS_OK;
    }

    try
    {
        decisions->resize(observations.size());
    }
    catch(const std::bad_alloc &)
    {
        if(error != NULL) *error = "attempt-decision allocation failed";
        return STATUS_OUT_OF_MEMORY;
    }
    for(size_t index = 0; index < observations.size(); ++index)
    {
        if(!valid_observation(observations[index]))
        {
            decisions->clear();
            if(error != NULL) *error = "invalid attempt observation";
            return STATUS_INVALID_ARGUMENT;
        }
        AttemptDecision decision;
        decision.scoreinfo_index = observations[index].scoreinfo_index;
        decision.attempt_order = observations[index].attempt_order;
        decision.selected = false;
        decision.reason = ATTEMPT_NOT_SELECTED;
        (*decisions)[index] = decision;
    }

    size_t group_begin = 0;
    while(group_begin < observations.size())
    {
        size_t group_end = group_begin + 1;
        while(group_end < observations.size() &&
              observations[group_end].scoreinfo_index == observations[group_begin].scoreinfo_index)
        {
            ++group_end;
        }
        if(group_end < observations.size() &&
           observations[group_end].scoreinfo_index < observations[group_begin].scoreinfo_index)
        {
            decisions->clear();
            if(error != NULL) *error = "scoreInfo groups are not in stable order";
            return STATUS_INVALID_ARGUMENT;
        }
        for(size_t index = group_begin + 1; index < group_end; ++index)
        {
            if(observations[index].attempt_order <= observations[index - 1].attempt_order ||
               observations[index].prealign_score != observations[group_begin].prealign_score)
            {
                decisions->clear();
                if(error != NULL) *error = "attempt order or prealign score drift within group";
                return STATUS_INVALID_ARGUMENT;
            }
        }

        size_t threshold_index = observations.size();
        size_t best_index = observations.size();
        size_t last_nonzero_index = observations.size();
        int best_score = 0;
        for(size_t index = group_begin; index < group_end; ++index)
        {
            const AttemptObservation &observation = observations[index];
            if(threshold_index != observations.size())
            {
                (*decisions)[index].reason = ATTEMPT_NOT_SELECTED_AFTER_THRESHOLD;
                continue;
            }
            if(observation.alignment_score != 0)
            {
                last_nonzero_index = index;
            }
            if(observation.alignment_score >= observation.prealign_score)
            {
                threshold_index = index;
                continue;
            }
            if(observation.ref_end == observation.cutlength - 1 &&
               observation.alignment_score > best_score)
            {
                if(best_index != observations.size())
                {
                    (*decisions)[best_index].reason = ATTEMPT_NOT_SELECTED_LOWER_SCORE;
                }
                best_score = observation.alignment_score;
                best_index = index;
            }
            else if(observation.ref_end == observation.cutlength - 1)
            {
                (*decisions)[index].reason = ATTEMPT_NOT_SELECTED_LOWER_SCORE;
            }
        }

        size_t selected_index = observations.size();
        int selected_reason = ATTEMPT_NOT_SELECTED;
        if(threshold_index != observations.size())
        {
            selected_index = threshold_index;
            selected_reason = ATTEMPT_THRESHOLD;
        }
        else if(best_index != observations.size())
        {
            selected_index = best_index;
            selected_reason = ATTEMPT_BEST_FALLBACK;
        }
        else if(last_nonzero_index != observations.size())
        {
            selected_index = last_nonzero_index;
            selected_reason = ATTEMPT_LAST;
        }
        if(selected_index != observations.size())
        {
            (*decisions)[selected_index].selected = true;
            (*decisions)[selected_index].reason = selected_reason;
        }
        group_begin = group_end;
    }
    return STATUS_OK;
}

} // namespace fasim_ssw_cuda
