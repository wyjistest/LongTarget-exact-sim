#include "ssw_cuda_forward_hybrid.h"

#include <chrono>
#include <limits>
#include <new>

namespace fasim_ssw_cuda
{
namespace
{

struct PlannedAttempt
{
    int task_index;
    int scoreinfo_index;
    int scoreinfo_order;
    int attempt_index;
    int identity_round;
    int prealign_score;
    int start;
    int cutlength;
};

double elapsed_seconds(const std::chrono::steady_clock::time_point &start)
{
    return std::chrono::duration<double>(
        std::chrono::steady_clock::now() - start).count();
}

bool translate(const std::string &sequence, std::vector<uint8_t> *output)
{
    if(output == NULL || sequence.empty()) return false;
    output->clear();
    output->reserve(sequence.size());
    for(size_t index = 0; index < sequence.size(); ++index)
    {
        const unsigned char value = static_cast<unsigned char>(sequence[index]);
        if(value == 0 || value >= 128) return false;
        switch(value)
        {
        case 'A': case 'a': case 'U': case 'u': output->push_back(0); break;
        case 'C': case 'c': output->push_back(1); break;
        case 'G': case 'g': output->push_back(2); break;
        case 'T': case 't': output->push_back(3); break;
        default: output->push_back(4); break;
        }
    }
    return true;
}

StatusCode fail(ForwardHybridOutput *output, StatusCode status,
                const std::string &message)
{
    output->status = status;
    output->error = message;
    output->selected.clear();
    return status;
}

} // namespace

ForwardHybridTelemetry::ForwardHybridTelemetry():
    attempt_planning_seconds(0.0), attempt_selection_seconds(0.0),
    total_wall_seconds(0.0), scoreinfo_count(0), attempt_count(0),
    selected_count(0), cpu_prealign_calls(0), cpu_forward_calls(0)
{
}

ForwardHybridOutput::ForwardHybridOutput():status(STATUS_NOT_BUILT)
{
}

ForwardHybridCpuTelemetry::ForwardHybridCpuTelemetry():
    continuation_calls(0), cpu_forward_calls(0), cpu_reverse_calls(0),
    cpu_banded_sw_calls(0), failures(0), substring_seconds(0.0),
    continuation_seconds(0.0), reverse_start_seconds(0.0),
    banded_traceback_seconds(0.0), cigar_seconds(0.0),
    conversion_seconds(0.0), sort_seconds(0.0), filter_seconds(0.0)
{
}

StatusCode forward_hybrid_select(const std::vector<ForwardHybridTask> &tasks,
                                 const BatchOptions &options,
                                 ForwardHybridOutput *output)
{
    if(output == NULL) return STATUS_INVALID_ARGUMENT;
    *output = ForwardHybridOutput();
    const std::chrono::steady_clock::time_point total_start =
        std::chrono::steady_clock::now();
    if(tasks.empty())
        return fail(output, STATUS_INVALID_ARGUMENT, "forward-hybrid task batch is empty");

    std::vector<TaskInput> preselect_tasks;
    try
    {
        preselect_tasks.resize(tasks.size());
    }
    catch(const std::bad_alloc &)
    {
        return fail(output, STATUS_OUT_OF_MEMORY, "forward-hybrid task allocation failed");
    }
    for(size_t index = 0; index < tasks.size(); ++index)
    {
        if(tasks[index].case_id.empty() || tasks[index].threshold < 0 ||
           !translate(tasks[index].query, &preselect_tasks[index].query) ||
           !translate(tasks[index].reference, &preselect_tasks[index].reference))
            return fail(output, STATUS_UNSUPPORTED_INPUT,
                        "forward-hybrid input is outside the frozen alphabet or shape");
        preselect_tasks[index].case_id = tasks[index].case_id;
        preselect_tasks[index].threshold = tasks[index].threshold;
    }

    BatchOutput preselect;
    const StatusCode preselect_status = pre_align_and_select(preselect_tasks, options, &preselect);
    output->telemetry.preselect = preselect.telemetry;
    if(preselect_status != STATUS_OK)
        return fail(output, preselect_status,
                    std::string("forward-hybrid preselect failed: ") + preselect.error);
    if(preselect.selection_offsets.size() != tasks.size() + 1)
        return fail(output, STATUS_INTERNAL_ERROR,
                    "forward-hybrid scoreInfo offset cardinality drift");
    output->scoreinfo_offsets = preselect.selection_offsets;
    output->scoreinfos = preselect.scoreinfos;
    output->telemetry.scoreinfo_count = preselect.scoreinfos.size();

    const std::chrono::steady_clock::time_point planning_start =
        std::chrono::steady_clock::now();
    std::vector<PlannedAttempt> attempts;
    std::vector<TaskInput> forward_tasks;
    try
    {
        attempts.reserve(preselect.scoreinfos.size() * 5);
        forward_tasks.reserve(preselect.scoreinfos.size() * 5);
        for(size_t scoreinfo_index = 0;
            scoreinfo_index < preselect.scoreinfos.size(); ++scoreinfo_index)
        {
            const ScoreInfo &scoreinfo = preselect.scoreinfos[scoreinfo_index];
            if(scoreinfo.task_index < 0 ||
               static_cast<size_t>(scoreinfo.task_index) >= tasks.size() ||
               scoreinfo.index < 0 || scoreinfo.score < 0 || scoreinfo.position < 0)
                return fail(output, STATUS_INTERNAL_ERROR,
                            "forward-hybrid scoreInfo identity drift");
            float identity = 0.6f;
            int identity_round = 0;
            while(identity <= 1.0f)
            {
                int cutlength = static_cast<int>(scoreinfo.score + 24) /
                    (9 * identity - 4) + 1;
                cutlength = scoreinfo.position - cutlength + 1 > 0 ?
                    cutlength : scoreinfo.position + 1;
                const int start = scoreinfo.position - cutlength + 1;
                if(start < 0 || cutlength <= 0 ||
                   static_cast<size_t>(start + cutlength) >
                       tasks[static_cast<size_t>(scoreinfo.task_index)].reference.size())
                    return fail(output, STATUS_INTERNAL_ERROR,
                                "forward-hybrid attempt window is outside its task");
                PlannedAttempt attempt;
                attempt.task_index = scoreinfo.task_index;
                attempt.scoreinfo_index = static_cast<int>(scoreinfo_index);
                attempt.scoreinfo_order = scoreinfo.index;
                attempt.attempt_index = static_cast<int>(attempts.size());
                attempt.identity_round = identity_round;
                attempt.prealign_score = scoreinfo.score;
                attempt.start = start;
                attempt.cutlength = cutlength;
                attempts.push_back(attempt);

                TaskInput forward_task;
                forward_task.case_id = tasks[static_cast<size_t>(scoreinfo.task_index)].case_id +
                    ":si" + std::to_string(scoreinfo.index) +
                    ":ir" + std::to_string(identity_round);
                forward_task.query = preselect_tasks[static_cast<size_t>(scoreinfo.task_index)].query;
                const std::vector<uint8_t> &reference =
                    preselect_tasks[static_cast<size_t>(scoreinfo.task_index)].reference;
                forward_task.reference.assign(reference.begin() + start,
                                              reference.begin() + start + cutlength);
                forward_task.threshold = scoreinfo.score;
                forward_tasks.push_back(forward_task);
                identity += 0.1f;
                ++identity_round;
            }
        }
    }
    catch(const std::bad_alloc &)
    {
        return fail(output, STATUS_OUT_OF_MEMORY,
                    "forward-hybrid attempt allocation failed");
    }
    output->telemetry.attempt_planning_seconds = elapsed_seconds(planning_start);
    output->telemetry.attempt_count = attempts.size();
    if(attempts.empty())
    {
        output->status = STATUS_OK;
        output->telemetry.total_wall_seconds = elapsed_seconds(total_start);
        return STATUS_OK;
    }

    ForwardBatchOutput forward;
    const StatusCode forward_status = forward_align(forward_tasks, options, &forward);
    output->telemetry.forward = forward.telemetry;
    if(forward_status != STATUS_OK)
        return fail(output, forward_status,
                    std::string("forward-hybrid endpoint batch failed: ") + forward.error);
    if(forward.endpoints.size() != attempts.size())
        return fail(output, STATUS_INTERNAL_ERROR,
                    "forward-hybrid endpoint cardinality drift");

    const std::chrono::steady_clock::time_point selection_start =
        std::chrono::steady_clock::now();
    std::vector<AttemptObservation> observations;
    std::vector<AttemptDecision> decisions;
    try
    {
        observations.resize(attempts.size());
        for(size_t index = 0; index < attempts.size(); ++index)
        {
            const PlannedAttempt &attempt = attempts[index];
            const ForwardEndpoint &endpoint = forward.endpoints[index];
            AttemptObservation &observation = observations[index];
            observation.scoreinfo_index = attempt.scoreinfo_index;
            observation.attempt_order = attempt.identity_round;
            observation.prealign_score = attempt.prealign_score;
            observation.alignment_score = endpoint.score1;
            observation.ref_end = endpoint.ref_end1;
            observation.cutlength = attempt.cutlength;
        }
    }
    catch(const std::bad_alloc &)
    {
        return fail(output, STATUS_OUT_OF_MEMORY,
                    "forward-hybrid observation allocation failed");
    }
    std::string selection_error;
    const StatusCode selection_status =
        select_attempts(observations, &decisions, &selection_error);
    if(selection_status != STATUS_OK || decisions.size() != attempts.size())
        return fail(output,
                    selection_status == STATUS_OK ? STATUS_INTERNAL_ERROR : selection_status,
                    std::string("forward-hybrid attempt selection failed: ") + selection_error);
    try
    {
        for(size_t index = 0; index < decisions.size(); ++index)
        {
            if(!decisions[index].selected) continue;
            const PlannedAttempt &attempt = attempts[index];
            ForwardHybridSelectedAttempt selected;
            selected.task_index = attempt.task_index;
            selected.scoreinfo_index = attempt.scoreinfo_index;
            selected.scoreinfo_order = attempt.scoreinfo_order;
            selected.attempt_index = attempt.attempt_index;
            selected.identity_round = attempt.identity_round;
            selected.prealign_score = attempt.prealign_score;
            selected.start = attempt.start;
            selected.cutlength = attempt.cutlength;
            selected.selection_reason = decisions[index].reason;
            selected.endpoint = forward.endpoints[index];
            output->selected.push_back(selected);
        }
    }
    catch(const std::bad_alloc &)
    {
        return fail(output, STATUS_OUT_OF_MEMORY,
                    "forward-hybrid selected-attempt allocation failed");
    }
    output->telemetry.attempt_selection_seconds = elapsed_seconds(selection_start);
    output->telemetry.selected_count = output->selected.size();
    output->telemetry.total_wall_seconds = elapsed_seconds(total_start);
    output->status = STATUS_OK;
    return STATUS_OK;
}

} // namespace fasim_ssw_cuda
