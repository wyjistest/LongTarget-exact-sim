#ifndef FASIM_SSW_CUDA_INTERNAL_H
#define FASIM_SSW_CUDA_INTERNAL_H

#include "ssw_cuda_api.h"

namespace fasim_ssw_cuda
{

struct DeviceTaskDescriptor
{
    int query_offset;
    int query_length;
    int reference_offset;
    int reference_length;
    int column_offset;
    int workspace_offset;
    int threshold;
};

struct DeviceScoreInfo
{
    int task_index;
    int index;
    int score;
    int position;
    int reason;
};

StatusCode select_device_scoreinfos(const DeviceTaskDescriptor *device_tasks,
                                    int task_count,
                                    const int *device_column_maxima,
                                    int total_columns,
                                    std::vector<int> *selection_offsets,
                                    std::vector<ScoreInfo> *scoreinfos,
                                    Telemetry *telemetry,
                                    std::string *error);

} // namespace fasim_ssw_cuda

#endif
