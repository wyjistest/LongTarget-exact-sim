#include "fasim/ssw_cuda/ssw_cuda_api.h"

#include <iostream>
#include <string>
#include <vector>

int main()
{
    if(fasim_ssw_cuda::is_built())
    {
        std::cerr << "stub unexpectedly reports a built backend\n";
        return 1;
    }

    fasim_ssw_cuda::TaskInput task;
    task.case_id = "stub-probe";
    task.query.assign(1, 0);
    task.reference.assign(1, 0);
    task.threshold = 0;
    std::vector<fasim_ssw_cuda::TaskInput> tasks(1, task);
    fasim_ssw_cuda::BatchOptions options;
    fasim_ssw_cuda::BatchOutput output;
    if(fasim_ssw_cuda::pre_align_and_select(tasks, options, &output) !=
       fasim_ssw_cuda::STATUS_NOT_BUILT || output.status != fasim_ssw_cuda::STATUS_NOT_BUILT)
    {
        std::cerr << "stub pre-align did not fail closed\n";
        return 1;
    }

    std::vector<fasim_ssw_cuda::AttemptObservation> observations;
    std::vector<fasim_ssw_cuda::AttemptDecision> decisions;
    std::string error;
    if(fasim_ssw_cuda::select_attempts(observations, &decisions, &error) !=
       fasim_ssw_cuda::STATUS_NOT_BUILT)
    {
        std::cerr << "stub attempt selection did not fail closed\n";
        return 1;
    }

    fasim_ssw_cuda::ForwardBatchOutput forward;
    if(fasim_ssw_cuda::forward_align(tasks, options, &forward) !=
       fasim_ssw_cuda::STATUS_NOT_BUILT ||
       forward.status != fasim_ssw_cuda::STATUS_NOT_BUILT ||
       forward.telemetry.cpu_endpoint_calls != 0)
    {
        std::cerr << "stub forward endpoint did not fail closed\n";
        return 1;
    }
    std::vector<fasim_ssw_cuda::ColumnReductionInput> reduction_inputs(1);
    reduction_inputs[0].case_id = "stub-reducer-probe";
    reduction_inputs[0].column_maxima.assign(1, 0);
    reduction_inputs[0].numeric_path = fasim_ssw_cuda::NUMERIC_PATH_BYTE8;
    reduction_inputs[0].mask_length = fasim_ssw_cuda::kContractMaskLength;
    std::vector<fasim_ssw_cuda::ColumnEndpoint> endpoints;
    fasim_ssw_cuda::Telemetry telemetry;
    if(fasim_ssw_cuda::reduce_forward_columns(
           reduction_inputs, options, &endpoints, &telemetry, &error) !=
       fasim_ssw_cuda::STATUS_NOT_BUILT || telemetry.cpu_endpoint_calls != 0)
    {
        std::cerr << "stub endpoint reducer did not fail closed\n";
        return 1;
    }
    std::cout << "ssw_cuda_stub_status=not_built\n";
    return 0;
}
