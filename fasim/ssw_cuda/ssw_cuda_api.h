#ifndef FASIM_SSW_CUDA_API_H
#define FASIM_SSW_CUDA_API_H

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace fasim_ssw_cuda
{

static const int kContractMatch = 5;
static const int kContractMismatchPenalty = 4;
static const int kContractGapOpen = 16;
static const int kContractGapExtend = 4;
static const int kContractMaskLength = 15;
static const int kContractScoreFilter = 0;
static const int kContractDistanceFilter = 32767;
static const int kMaximumQueryLength = 2812;
static const int kMaximumReferenceLength = 1048576;

enum StatusCode
{
    STATUS_OK = 0,
    STATUS_NOT_BUILT = 1,
    STATUS_CUDA_UNAVAILABLE = 2,
    STATUS_INVALID_ARGUMENT = 3,
    STATUS_UNSUPPORTED_INPUT = 4,
    STATUS_CAPACITY_EXCEEDED = 5,
    STATUS_OUT_OF_MEMORY = 6,
    STATUS_CUDA_ERROR = 7,
    STATUS_INTERNAL_ERROR = 8
};

enum ScoreInfoReason
{
    SCOREINFO_THRESHOLD_RUN_MAX = 1
};

enum AttemptReason
{
    ATTEMPT_THRESHOLD = 1,
    ATTEMPT_BEST_FALLBACK = 2,
    ATTEMPT_LAST = 3,
    ATTEMPT_NOT_SELECTED_AFTER_THRESHOLD = 4,
    ATTEMPT_NOT_SELECTED_LOWER_SCORE = 5,
    ATTEMPT_NOT_SELECTED = 6
};

struct ContractConfig
{
    ContractConfig();

    int match;
    int mismatch_penalty;
    int gap_open;
    int gap_extend;
    int mask_length;
    int flag;
    int score_filter;
    int distance_filter;
};

struct TaskInput
{
    std::string case_id;
    std::vector<uint8_t> query;
    std::vector<uint8_t> reference;
    int threshold;
};

struct ScoreInfo
{
    int task_index;
    int index;
    int score;
    int position;
    int reason;
};

struct BatchOptions
{
    BatchOptions();

    int device;
    bool export_full_column_vectors;
    bool force_out_of_memory_for_test;
    size_t maximum_total_dp_cells;
    ContractConfig contract;
};

struct Telemetry
{
    Telemetry();

    double packing_seconds;
    double h2d_seconds;
    double prealign_seconds;
    double selection_flag_seconds;
    double selection_scan_seconds;
    double selection_scatter_seconds;
    double d2h_seconds;
    double overhead_seconds;
    double total_wall_seconds;
    size_t host_input_bytes;
    size_t device_input_bytes;
    size_t device_workspace_bytes;
    size_t device_output_bytes;
    int task_count;
    int device;
};

struct BatchOutput
{
    BatchOutput();

    StatusCode status;
    std::string error;
    std::vector<int> column_offsets;
    std::vector<int> column_maxima;
    std::vector<int> selection_offsets;
    std::vector<ScoreInfo> scoreinfos;
    Telemetry telemetry;
};

struct AttemptObservation
{
    int scoreinfo_index;
    int attempt_order;
    int prealign_score;
    int alignment_score;
    int ref_end;
    int cutlength;
};

struct AttemptDecision
{
    int scoreinfo_index;
    int attempt_order;
    bool selected;
    int reason;
};

bool is_built();
const char *status_name(StatusCode status);
const char *scoreinfo_reason_name(int reason);
const char *attempt_reason_name(int reason);

StatusCode pre_align_and_select(const std::vector<TaskInput> &tasks,
                                const BatchOptions &options,
                                BatchOutput *output);

StatusCode select_attempts(const std::vector<AttemptObservation> &observations,
                           std::vector<AttemptDecision> *decisions,
                           std::string *error);

} // namespace fasim_ssw_cuda

#endif
