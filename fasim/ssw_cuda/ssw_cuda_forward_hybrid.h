#ifndef FASIM_SSW_CUDA_FORWARD_HYBRID_H
#define FASIM_SSW_CUDA_FORWARD_HYBRID_H

#include "ssw_cuda_api.h"

#include <string>
#include <vector>

namespace fasim_ssw_cuda
{

struct ForwardHybridTask
{
    std::string case_id;
    std::string query;
    std::string reference;
    int threshold;
};

struct ForwardHybridSelectedAttempt
{
    int task_index;
    int scoreinfo_index;
    int scoreinfo_order;
    int attempt_index;
    int identity_round;
    int prealign_score;
    int start;
    int cutlength;
    int selection_reason;
    ForwardEndpoint endpoint;
};

struct ForwardHybridTelemetry
{
    ForwardHybridTelemetry();

    Telemetry preselect;
    Telemetry forward;
    double attempt_planning_seconds;
    double attempt_selection_seconds;
    double total_wall_seconds;
    size_t scoreinfo_count;
    size_t attempt_count;
    size_t selected_count;
    uint64_t cpu_prealign_calls;
    uint64_t cpu_forward_calls;
};

struct ForwardHybridOutput
{
    ForwardHybridOutput();

    StatusCode status;
    std::string error;
    std::vector<int> scoreinfo_offsets;
    std::vector<ScoreInfo> scoreinfos;
    std::vector<ForwardHybridSelectedAttempt> selected;
    ForwardHybridTelemetry telemetry;
};

struct ForwardHybridCpuTelemetry
{
    ForwardHybridCpuTelemetry();

    uint64_t continuation_calls;
    uint64_t cpu_forward_calls;
    uint64_t cpu_reverse_calls;
    uint64_t cpu_banded_sw_calls;
    uint64_t failures;
    double substring_seconds;
    double continuation_seconds;
    double reverse_start_seconds;
    double banded_traceback_seconds;
    double cigar_seconds;
    double conversion_seconds;
    double sort_seconds;
    double filter_seconds;
};

StatusCode forward_hybrid_select(const std::vector<ForwardHybridTask> &tasks,
                                 const BatchOptions &options,
                                 ForwardHybridOutput *output);

} // namespace fasim_ssw_cuda

#endif
