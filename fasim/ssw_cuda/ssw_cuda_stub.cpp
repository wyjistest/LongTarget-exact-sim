#include "ssw_cuda_api.h"

namespace fasim_ssw_cuda
{

ContractConfig::ContractConfig():
    match(kContractMatch),
    mismatch_penalty(kContractMismatchPenalty),
    gap_open(kContractGapOpen),
    gap_extend(kContractGapExtend),
    mask_length(kContractMaskLength),
    flag(0),
    score_filter(kContractScoreFilter),
    distance_filter(kContractDistanceFilter)
{
}

BatchOptions::BatchOptions():
    device(0),
    export_full_column_vectors(false),
    force_out_of_memory_for_test(false),
    maximum_total_dp_cells(static_cast<size_t>(1) << 31)
{
}

Telemetry::Telemetry():
    packing_seconds(0.0),
    h2d_seconds(0.0),
    prealign_seconds(0.0),
    forward_seconds(0.0),
    endpoint_reduce_seconds(0.0),
    selection_flag_seconds(0.0),
    selection_scan_seconds(0.0),
    selection_scatter_seconds(0.0),
    d2h_seconds(0.0),
    overhead_seconds(0.0),
    total_wall_seconds(0.0),
    host_input_bytes(0),
    device_input_bytes(0),
    device_workspace_bytes(0),
    device_output_bytes(0),
    task_count(0),
    device(-1),
    cpu_endpoint_calls(0)
{
}

BatchOutput::BatchOutput():status(STATUS_NOT_BUILT)
{
}

ForwardBatchOutput::ForwardBatchOutput():status(STATUS_NOT_BUILT)
{
}

bool is_built()
{
    return false;
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

StatusCode pre_align_and_select(const std::vector<TaskInput> &,
                                const BatchOptions &,
                                BatchOutput *output)
{
    if(output == NULL)
    {
        return STATUS_INVALID_ARGUMENT;
    }
    *output = BatchOutput();
    output->status = STATUS_NOT_BUILT;
    output->error = "SSW-CUDA backend was not built";
    return output->status;
}

StatusCode select_attempts(const std::vector<AttemptObservation> &,
                           std::vector<AttemptDecision> *decisions,
                           std::string *error)
{
    if(decisions != NULL)
    {
        decisions->clear();
    }
    if(error != NULL)
    {
        *error = "SSW-CUDA backend was not built";
    }
    return STATUS_NOT_BUILT;
}

StatusCode reduce_forward_columns(const std::vector<ColumnReductionInput> &,
                                  const BatchOptions &,
                                  std::vector<ColumnEndpoint> *endpoints,
                                  Telemetry *telemetry,
                                  std::string *error)
{
    if(endpoints != NULL) endpoints->clear();
    if(telemetry != NULL) *telemetry = Telemetry();
    if(error != NULL) *error = "SSW-CUDA backend was not built";
    return STATUS_NOT_BUILT;
}

StatusCode forward_align(const std::vector<TaskInput> &,
                         const BatchOptions &,
                         ForwardBatchOutput *output)
{
    if(output == NULL) return STATUS_INVALID_ARGUMENT;
    *output = ForwardBatchOutput();
    output->status = STATUS_NOT_BUILT;
    output->error = "SSW-CUDA backend was not built";
    return output->status;
}

} // namespace fasim_ssw_cuda
