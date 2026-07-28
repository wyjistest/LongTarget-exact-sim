#ifndef FASIM_SSW_CUDA_STRIPED_CUH
#define FASIM_SSW_CUDA_STRIPED_CUH

#include "ssw_cuda_api.h"

namespace fasim_ssw_cuda
{

struct StripedPassResult
{
    int score1;
    int ref_end1;
    int read_end1;
    int numeric_path;
    bool overflow;
};

__device__ inline int ssw_cuda_saturating_add(int left, int right, int maximum)
{
    const int value = left + right;
    return value > maximum ? maximum : value;
}

__device__ inline int ssw_cuda_saturating_subtract(int left, int right)
{
    return left > right ? left - right : 0;
}

template <int kLanes, bool kBytePath>
__device__ void striped_forward_pass(const uint8_t *query,
                                     int query_length,
                                     const uint8_t *reference,
                                     int reference_length,
                                     int *workspace,
                                     int *column_maxima,
                                     int *best_column,
                                     StripedPassResult *result)
{
    const int segment_length = (query_length + kLanes - 1) / kLanes;
    const int padded_query_length = segment_length * kLanes;
    const int numeric_maximum = kBytePath ? 255 : 32767;
    int *h_store = workspace;
    int *h_load = h_store + padded_query_length;
    int *e_values = h_load + padded_query_length;
    for(int index = 0; index < 3 * padded_query_length; ++index)
    {
        workspace[index] = 0;
    }
    if(best_column != NULL)
    {
        for(int index = 0; index < padded_query_length; ++index)
        {
            best_column[index] = 0;
        }
    }

    int global_lane_maximum[kLanes];
    int global_lane_mark[kLanes];
    for(int lane = 0; lane < kLanes; ++lane)
    {
        global_lane_maximum[lane] = 0;
        global_lane_mark[lane] = 0;
    }
    int global_maximum = 0;
    int best_reference = kBytePath ? -1 : 0;
    bool overflow = false;

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
                    h_value[lane] = ssw_cuda_saturating_add(
                        h_value[lane], substitution + 4, numeric_maximum);
                    h_value[lane] = ssw_cuda_saturating_subtract(h_value[lane], 4);
                }
                else
                {
                    h_value[lane] = ssw_cuda_saturating_add(
                        h_value[lane], substitution, numeric_maximum);
                    if(h_value[lane] < 0) h_value[lane] = 0;
                }
                if(e_values[offset + lane] > h_value[lane]) h_value[lane] = e_values[offset + lane];
                if(f_value[lane] > h_value[lane]) h_value[lane] = f_value[lane];
                if(h_value[lane] > column_lane_maximum[lane])
                    column_lane_maximum[lane] = h_value[lane];
                h_store[offset + lane] = h_value[lane];

                const int opened = ssw_cuda_saturating_subtract(
                    h_value[lane], kContractGapOpen);
                const int extended_e = ssw_cuda_saturating_subtract(
                    e_values[offset + lane], kContractGapExtend);
                e_values[offset + lane] = opened > extended_e ? opened : extended_e;
                const int extended_f = ssw_cuda_saturating_subtract(
                    f_value[lane], kContractGapExtend);
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
                    const int opened = ssw_cuda_saturating_subtract(
                        stored, kContractGapOpen);
                    f_value[lane] = ssw_cuda_saturating_subtract(
                        f_value[lane], kContractGapExtend);
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
                    overflow = true;
                    break;
                }
                best_reference = column;
                if(best_column != NULL)
                {
                    for(int index = 0; index < padded_query_length; ++index)
                    {
                        best_column[index] = h_store[index];
                    }
                }
            }
        }
        column_maxima[column] = scalar_column_maximum;
    }

    if(result != NULL)
    {
        int read_end = query_length - 1;
        if(best_column != NULL)
        {
            for(int flat_index = 0; flat_index < padded_query_length; ++flat_index)
            {
                if(best_column[flat_index] != global_maximum) continue;
                const int logical_read = flat_index / kLanes +
                                         (flat_index % kLanes) * segment_length;
                if(logical_read < read_end) read_end = logical_read;
            }
        }
        result->score1 = overflow ? 255 : global_maximum;
        result->ref_end1 = best_reference;
        result->read_end1 = read_end;
        result->numeric_path = kBytePath ? NUMERIC_PATH_BYTE8 : NUMERIC_PATH_WORD16;
        result->overflow = overflow;
    }
}

} // namespace fasim_ssw_cuda

#endif
