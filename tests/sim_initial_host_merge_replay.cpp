#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "../sim.h"

namespace
{

static void print_usage(const char *argv0)
{
    std::cerr << "Usage: " << argv0
              << " [--corpus-dir DIR] [--case CASE_ID | --all] [--verify] [--output-tsv PATH]"
              << " [--warmup-iterations N] [--iterations N] [--aggregate-tsv PATH]\n";
}

static bool write_text_file(const std::string &path, const std::string &content)
{
    std::ofstream output(path.c_str(), std::ios::out | std::ios::binary | std::ios::trunc);
    if (!output)
    {
        return false;
    }
    output.write(content.data(), static_cast<std::streamsize>(content.size()));
    return output.good();
}

} // namespace

int main(int argc, char **argv)
{
    std::string corpusDir(".");
    std::string caseId;
    std::string outputTsvPath;
    std::string aggregateTsvPath;
    bool selectAll = false;
    bool verify = false;
    size_t warmupIterations = 0;
    size_t iterations = 1;

    for (int index = 1; index < argc; ++index)
    {
        const std::string argument(argv[index]);
        if (argument == "--corpus-dir")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            corpusDir = argv[++index];
        }
        else if (argument == "--case")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            caseId = argv[++index];
        }
        else if (argument == "--all")
        {
            selectAll = true;
        }
        else if (argument == "--verify")
        {
            verify = true;
        }
        else if (argument == "--output-tsv")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            outputTsvPath = argv[++index];
        }
        else if (argument == "--warmup-iterations")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            warmupIterations = static_cast<size_t>(strtoull(argv[++index], NULL, 10));
        }
        else if (argument == "--iterations")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            iterations = static_cast<size_t>(strtoull(argv[++index], NULL, 10));
        }
        else if (argument == "--aggregate-tsv")
        {
            if (index + 1 >= argc)
            {
                print_usage(argv[0]);
                return 1;
            }
            aggregateTsvPath = argv[++index];
        }
        else if (argument == "--help" || argument == "-h")
        {
            print_usage(argv[0]);
            return 0;
        }
        else
        {
            std::cerr << "Unknown argument: " << argument << "\n";
            print_usage(argv[0]);
            return 1;
        }
    }

    if (selectAll && !caseId.empty())
    {
        std::cerr << "--case and --all are mutually exclusive\n";
        return 1;
    }
    if ((warmupIterations > 0 || iterations != 1) && aggregateTsvPath.empty())
    {
        std::cerr << "--aggregate-tsv is required when benchmark iterations are requested\n";
        return 1;
    }

    std::vector<std::string> selectedCases;
    std::string error;
    if (selectAll || caseId.empty())
    {
        if (!listSimInitialHostMergeCorpusCases(corpusDir, selectedCases, &error))
        {
            std::cerr << error << "\n";
            return 1;
        }
    }
    else
    {
        selectedCases.push_back(caseId);
    }

    if (selectedCases.empty())
    {
        std::cerr << "No corpus cases found under " << corpusDir << "\n";
        return 1;
    }

    std::stringstream tsv;
    tsv << "case_id\tsummary_count\tlogical_event_count\tcontext_apply_seconds\tstore_materialize_seconds"
        << "\tstore_materialize_reset_seconds\tstore_materialize_insert_seconds"
        << "\tstore_materialize_update_seconds\tstore_materialize_snapshot_copy_seconds"
        << "\tstore_materialize_inserted_count\tstore_materialize_updated_count"
        << "\tstore_materialize_peak_size\tstore_materialize_rehash_count"
        << "\tstore_other_merge_context_apply_seconds"
        << "\tstore_other_merge_context_apply_lookup_seconds"
        << "\tstore_other_merge_context_apply_mutate_seconds"
        << "\tstore_other_merge_context_apply_finalize_seconds"
        << "\tstore_other_merge_context_apply_attempted_count"
        << "\tstore_other_merge_context_apply_modified_count"
        << "\tstore_other_merge_context_apply_noop_count"
        << "\tstore_other_merge_context_apply_lookup_hit_count"
        << "\tstore_other_merge_context_apply_lookup_miss_count"
        << "\tstore_other_merge_context_apply_slot_created_count"
        << "\tstore_other_merge_context_apply_lookup_probe_steps_total"
        << "\tstore_other_merge_context_apply_lookup_probe_steps_max"
        << "\tstore_other_merge_context_apply_lookup_miss_open_slot_count"
        << "\tstore_other_merge_context_apply_lookup_miss_candidate_set_full_count"
        << "\tstore_other_merge_context_apply_eviction_selected_count"
        << "\tstore_other_merge_context_apply_reused_slot_count"
        << "\tstore_other_merge_context_apply_lookup_miss_seconds"
        << "\tstore_other_merge_context_apply_lookup_miss_open_slot_seconds"
        << "\tstore_other_merge_context_apply_lookup_miss_candidate_set_full_probe_seconds"
        << "\tstore_other_merge_context_apply_lookup_miss_eviction_select_seconds"
        << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_seconds"
        << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_victim_reset_seconds"
        << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_key_rebind_seconds"
        << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_candidate_copy_seconds"
        << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_aux_bookkeeping_seconds"
        << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_victim_reset_count"
        << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_candidate_copy_count"
        << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_aux_bookkeeping_count"
        << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_payload_bytes_total"
        << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_aux_updates_total"
        << "\tstore_other_merge_context_apply_lookup_ns_per_attempt"
        << "\tstore_other_merge_context_apply_lookup_hit_ns_per_event"
        << "\tstore_other_merge_context_apply_lookup_miss_ns_per_event"
        << "\tstore_other_merge_context_snapshot_seconds"
        << "\tstore_other_merge_state_snapshot_seconds"
        << "\tstore_other_merge_residual_seconds"
        << "\tstore_prune_seconds\tfull_host_merge_seconds\tcandidate_count_after_context_apply"
        << "\tstore_materialized_count\tstore_pruned_count\tstore_other_merge_seconds\tverify_ok\n";
    std::stringstream aggregateTsv;
    if (!aggregateTsvPath.empty())
    {
        aggregateTsv << "case_id\twarmup_iterations\titerations\tlogical_event_count\tstore_materialized_count\tstore_pruned_count"
                     << "\tstore_materialize_inserted_count\tstore_materialize_updated_count"
                     << "\tstore_materialize_peak_size\tstore_materialize_rehash_count"
                     << "\tstore_other_merge_context_apply_attempted_count"
                     << "\tstore_other_merge_context_apply_modified_count"
                     << "\tstore_other_merge_context_apply_noop_count"
                     << "\tstore_other_merge_context_apply_lookup_hit_count"
                     << "\tstore_other_merge_context_apply_lookup_miss_count"
                     << "\tstore_other_merge_context_apply_slot_created_count"
                     << "\tstore_other_merge_context_apply_lookup_probe_steps_total"
                     << "\tstore_other_merge_context_apply_lookup_probe_steps_max"
                     << "\tstore_other_merge_context_apply_lookup_miss_open_slot_count"
                     << "\tstore_other_merge_context_apply_lookup_miss_candidate_set_full_count"
                     << "\tstore_other_merge_context_apply_eviction_selected_count"
                     << "\tstore_other_merge_context_apply_reused_slot_count"
                     << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_victim_reset_count"
                     << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_candidate_copy_count"
                     << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_aux_bookkeeping_count"
                     << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_payload_bytes_total"
                     << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_aux_updates_total"
                     << "\tstore_other_merge_context_apply_lookup_ns_per_attempt"
                     << "\tstore_other_merge_context_apply_lookup_hit_ns_per_event"
                     << "\tstore_other_merge_context_apply_lookup_miss_ns_per_event"
                     << "\tcontext_apply_mean_seconds\tcontext_apply_p50_seconds\tcontext_apply_p95_seconds"
                     << "\tstore_materialize_mean_seconds\tstore_materialize_p50_seconds\tstore_materialize_p95_seconds"
                     << "\tstore_materialize_reset_mean_seconds\tstore_materialize_reset_p50_seconds\tstore_materialize_reset_p95_seconds"
                     << "\tstore_materialize_insert_mean_seconds\tstore_materialize_insert_p50_seconds\tstore_materialize_insert_p95_seconds"
                     << "\tstore_materialize_update_mean_seconds\tstore_materialize_update_p50_seconds\tstore_materialize_update_p95_seconds"
                     << "\tstore_materialize_snapshot_copy_mean_seconds\tstore_materialize_snapshot_copy_p50_seconds\tstore_materialize_snapshot_copy_p95_seconds"
                     << "\tstore_prune_mean_seconds\tstore_prune_p50_seconds\tstore_prune_p95_seconds"
                     << "\tstore_other_merge_mean_seconds\tstore_other_merge_p50_seconds\tstore_other_merge_p95_seconds"
                     << "\tstore_other_merge_context_apply_mean_seconds\tstore_other_merge_context_apply_p50_seconds\tstore_other_merge_context_apply_p95_seconds"
                     << "\tstore_other_merge_context_apply_lookup_mean_seconds\tstore_other_merge_context_apply_lookup_p50_seconds\tstore_other_merge_context_apply_lookup_p95_seconds"
                     << "\tstore_other_merge_context_apply_lookup_miss_mean_seconds\tstore_other_merge_context_apply_lookup_miss_p50_seconds\tstore_other_merge_context_apply_lookup_miss_p95_seconds"
                     << "\tstore_other_merge_context_apply_lookup_miss_open_slot_mean_seconds\tstore_other_merge_context_apply_lookup_miss_open_slot_p50_seconds\tstore_other_merge_context_apply_lookup_miss_open_slot_p95_seconds"
                     << "\tstore_other_merge_context_apply_lookup_miss_candidate_set_full_probe_mean_seconds\tstore_other_merge_context_apply_lookup_miss_candidate_set_full_probe_p50_seconds\tstore_other_merge_context_apply_lookup_miss_candidate_set_full_probe_p95_seconds"
                     << "\tstore_other_merge_context_apply_lookup_miss_eviction_select_mean_seconds\tstore_other_merge_context_apply_lookup_miss_eviction_select_p50_seconds\tstore_other_merge_context_apply_lookup_miss_eviction_select_p95_seconds"
                     << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_mean_seconds\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_p50_seconds\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_p95_seconds"
                     << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_victim_reset_mean_seconds\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_victim_reset_p50_seconds\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_victim_reset_p95_seconds"
                     << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_key_rebind_mean_seconds\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_key_rebind_p50_seconds\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_key_rebind_p95_seconds"
                     << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_candidate_copy_mean_seconds\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_candidate_copy_p50_seconds\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_candidate_copy_p95_seconds"
                     << "\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_aux_bookkeeping_mean_seconds\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_aux_bookkeeping_p50_seconds\tstore_other_merge_context_apply_lookup_miss_reuse_writeback_aux_bookkeeping_p95_seconds"
                     << "\tstore_other_merge_context_apply_mutate_mean_seconds\tstore_other_merge_context_apply_mutate_p50_seconds\tstore_other_merge_context_apply_mutate_p95_seconds"
                     << "\tstore_other_merge_context_apply_finalize_mean_seconds\tstore_other_merge_context_apply_finalize_p50_seconds\tstore_other_merge_context_apply_finalize_p95_seconds"
                     << "\tstore_other_merge_context_snapshot_mean_seconds\tstore_other_merge_context_snapshot_p50_seconds\tstore_other_merge_context_snapshot_p95_seconds"
                     << "\tstore_other_merge_state_snapshot_mean_seconds\tstore_other_merge_state_snapshot_p50_seconds\tstore_other_merge_state_snapshot_p95_seconds"
                     << "\tstore_other_merge_residual_mean_seconds\tstore_other_merge_residual_p50_seconds\tstore_other_merge_residual_p95_seconds"
                     << "\tfull_host_merge_mean_seconds\tfull_host_merge_p50_seconds\tfull_host_merge_p95_seconds"
                     << "\tns_per_logical_event\tns_per_materialized_record\tns_per_pruned_record\n";
    }

    bool success = true;
    for (size_t caseIndex = 0; caseIndex < selectedCases.size(); ++caseIndex)
    {
        SimInitialHostMergeCorpusCase corpus;
        if (!loadSimInitialHostMergeCorpusCase(simJoinInitialHostMergeCorpusPath(corpusDir, selectedCases[caseIndex]),
                                               corpus,
                                               &error))
        {
            std::cerr << error << "\n";
            return 1;
        }

        SimInitialHostMergeReplayResult replay;
        if (!replaySimInitialHostMergeCorpusCase(corpus, replay, &error))
        {
            std::cerr << error << "\n";
            return 1;
        }

        SimInitialHostMergeReplayBenchmarkResult benchmark;
        if (!aggregateTsvPath.empty())
        {
            if (!benchmarkSimInitialHostMergeCorpusCase(corpus,
                                                        warmupIterations,
                                                        iterations,
                                                        benchmark,
                                                        &error))
            {
                std::cerr << error << "\n";
                return 1;
            }
        }

        bool verifyOk = true;
        if (verify)
        {
            verifyOk = verifySimInitialHostMergeReplay(corpus, replay, &error);
            if (!verifyOk)
            {
                success = false;
                std::cerr << corpus.caseId << ": " << error << "\n";
            }
        }

        tsv << corpus.caseId << '\t'
            << corpus.summaries.size() << '\t'
            << corpus.logicalEventCount << '\t'
            << replay.contextApplySeconds << '\t'
            << replay.storeMaterializeSeconds << '\t'
            << replay.storeMaterializeResetSeconds << '\t'
            << replay.storeMaterializeInsertSeconds << '\t'
            << replay.storeMaterializeUpdateSeconds << '\t'
            << replay.storeMaterializeSnapshotCopySeconds << '\t'
            << replay.storeMaterializeInsertedCount << '\t'
            << replay.storeMaterializeUpdatedCount << '\t'
            << replay.storeMaterializePeakSize << '\t'
            << replay.storeMaterializeRehashCount << '\t'
            << replay.storeOtherMergeContextApplySeconds << '\t'
            << replay.storeOtherMergeContextApplyLookupSeconds << '\t'
            << replay.storeOtherMergeContextApplyMutateSeconds << '\t'
            << replay.storeOtherMergeContextApplyFinalizeSeconds << '\t'
            << replay.storeOtherMergeContextApplyAttemptedCount << '\t'
            << replay.storeOtherMergeContextApplyModifiedCount << '\t'
            << replay.storeOtherMergeContextApplyNoopCount << '\t'
            << replay.storeOtherMergeContextApplyLookupHitCount << '\t'
            << replay.storeOtherMergeContextApplyLookupMissCount << '\t'
            << replay.storeOtherMergeContextApplySlotCreatedCount << '\t'
            << replay.storeOtherMergeContextApplyLookupProbeStepsTotal << '\t'
            << replay.storeOtherMergeContextApplyLookupProbeStepsMax << '\t'
            << replay.storeOtherMergeContextApplyLookupMissOpenSlotCount << '\t'
            << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullCount << '\t'
            << replay.storeOtherMergeContextApplyEvictionSelectedCount << '\t'
            << replay.storeOtherMergeContextApplyReusedSlotCount << '\t'
            << replay.storeOtherMergeContextApplyLookupMissSeconds << '\t'
            << replay.storeOtherMergeContextApplyLookupMissOpenSlotSeconds << '\t'
            << replay.storeOtherMergeContextApplyLookupMissCandidateSetFullProbeSeconds << '\t'
            << replay.storeOtherMergeContextApplyLookupMissEvictionSelectSeconds << '\t'
            << replay.storeOtherMergeContextApplyLookupMissReuseWritebackSeconds << '\t'
            << replay.storeOtherMergeContextApplyLookupMissReuseWritebackVictimResetSeconds << '\t'
            << replay.storeOtherMergeContextApplyLookupMissReuseWritebackKeyRebindSeconds << '\t'
            << replay.storeOtherMergeContextApplyLookupMissReuseWritebackCandidateCopySeconds << '\t'
            << replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxBookkeepingSeconds << '\t'
            << replay.storeOtherMergeContextApplyLookupMissReuseWritebackVictimResetCount << '\t'
            << replay.storeOtherMergeContextApplyLookupMissReuseWritebackCandidateCopyCount << '\t'
            << replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxBookkeepingCount << '\t'
            << replay.storeOtherMergeContextApplyLookupMissReuseWritebackPayloadBytesTotal << '\t'
            << replay.storeOtherMergeContextApplyLookupMissReuseWritebackAuxUpdatesTotal << '\t'
            << replay.storeOtherMergeContextApplyLookupNsPerAttempt << '\t'
            << replay.storeOtherMergeContextApplyLookupHitNsPerEvent << '\t'
            << replay.storeOtherMergeContextApplyLookupMissNsPerEvent << '\t'
            << replay.storeOtherMergeContextSnapshotSeconds << '\t'
            << replay.storeOtherMergeStateSnapshotSeconds << '\t'
            << replay.storeOtherMergeResidualSeconds << '\t'
            << replay.storePruneSeconds << '\t'
            << replay.fullHostMergeSeconds << '\t'
            << replay.contextCandidates.size() << '\t'
            << replay.storeMaterialized.size() << '\t'
            << replay.storePruned.size() << '\t'
            << replay.storeOtherMergeSeconds << '\t'
            << (verifyOk ? "true" : "false") << '\n';

        if (!aggregateTsvPath.empty())
        {
            aggregateTsv << corpus.caseId << '\t'
                         << benchmark.warmupIterations << '\t'
                         << benchmark.iterations << '\t'
                         << benchmark.logicalEventCount << '\t'
                         << benchmark.storeMaterializedCount << '\t'
                         << benchmark.storePrunedCount << '\t'
                         << benchmark.storeMaterializeInsertedCount << '\t'
                         << benchmark.storeMaterializeUpdatedCount << '\t'
                         << benchmark.storeMaterializePeakSize << '\t'
                         << benchmark.storeMaterializeRehashCount << '\t'
                         << benchmark.storeOtherMergeContextApplyAttemptedCount << '\t'
                         << benchmark.storeOtherMergeContextApplyModifiedCount << '\t'
                         << benchmark.storeOtherMergeContextApplyNoopCount << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupHitCount << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissCount << '\t'
                         << benchmark.storeOtherMergeContextApplySlotCreatedCount << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupProbeStepsTotal << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupProbeStepsMax << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissOpenSlotCount << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissCandidateSetFullCount << '\t'
                         << benchmark.storeOtherMergeContextApplyEvictionSelectedCount << '\t'
                         << benchmark.storeOtherMergeContextApplyReusedSlotCount << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackVictimResetCount << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackCandidateCopyCount << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackAuxBookkeepingCount << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackPayloadBytesTotal << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackAuxUpdatesTotal << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupNsPerAttempt << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupHitNsPerEvent << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissNsPerEvent << '\t'
                         << benchmark.contextApply.meanSeconds << '\t'
                         << benchmark.contextApply.p50Seconds << '\t'
                         << benchmark.contextApply.p95Seconds << '\t'
                         << benchmark.storeMaterialize.meanSeconds << '\t'
                         << benchmark.storeMaterialize.p50Seconds << '\t'
                         << benchmark.storeMaterialize.p95Seconds << '\t'
                         << benchmark.storeMaterializeReset.meanSeconds << '\t'
                         << benchmark.storeMaterializeReset.p50Seconds << '\t'
                         << benchmark.storeMaterializeReset.p95Seconds << '\t'
                         << benchmark.storeMaterializeInsert.meanSeconds << '\t'
                         << benchmark.storeMaterializeInsert.p50Seconds << '\t'
                         << benchmark.storeMaterializeInsert.p95Seconds << '\t'
                         << benchmark.storeMaterializeUpdate.meanSeconds << '\t'
                         << benchmark.storeMaterializeUpdate.p50Seconds << '\t'
                         << benchmark.storeMaterializeUpdate.p95Seconds << '\t'
                         << benchmark.storeMaterializeSnapshotCopy.meanSeconds << '\t'
                         << benchmark.storeMaterializeSnapshotCopy.p50Seconds << '\t'
                         << benchmark.storeMaterializeSnapshotCopy.p95Seconds << '\t'
                         << benchmark.storePrune.meanSeconds << '\t'
                         << benchmark.storePrune.p50Seconds << '\t'
                         << benchmark.storePrune.p95Seconds << '\t'
                         << benchmark.storeOtherMerge.meanSeconds << '\t'
                         << benchmark.storeOtherMerge.p50Seconds << '\t'
                         << benchmark.storeOtherMerge.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextApply.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextApply.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextApply.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookup.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookup.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookup.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMiss.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMiss.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMiss.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissOpenSlot.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissOpenSlot.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissOpenSlot.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissCandidateSetFullProbe.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissCandidateSetFullProbe.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissCandidateSetFullProbe.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissEvictionSelect.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissEvictionSelect.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissEvictionSelect.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWriteback.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWriteback.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWriteback.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackVictimReset.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackVictimReset.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackVictimReset.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackKeyRebind.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackKeyRebind.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackKeyRebind.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackCandidateCopy.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackCandidateCopy.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackCandidateCopy.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackAuxBookkeeping.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackAuxBookkeeping.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyLookupMissReuseWritebackAuxBookkeeping.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyMutate.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextApplyMutate.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyMutate.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyFinalize.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextApplyFinalize.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextApplyFinalize.p95Seconds << '\t'
                         << benchmark.storeOtherMergeContextSnapshot.meanSeconds << '\t'
                         << benchmark.storeOtherMergeContextSnapshot.p50Seconds << '\t'
                         << benchmark.storeOtherMergeContextSnapshot.p95Seconds << '\t'
                         << benchmark.storeOtherMergeStateSnapshot.meanSeconds << '\t'
                         << benchmark.storeOtherMergeStateSnapshot.p50Seconds << '\t'
                         << benchmark.storeOtherMergeStateSnapshot.p95Seconds << '\t'
                         << benchmark.storeOtherMergeResidual.meanSeconds << '\t'
                         << benchmark.storeOtherMergeResidual.p50Seconds << '\t'
                         << benchmark.storeOtherMergeResidual.p95Seconds << '\t'
                         << benchmark.fullHostMerge.meanSeconds << '\t'
                         << benchmark.fullHostMerge.p50Seconds << '\t'
                         << benchmark.fullHostMerge.p95Seconds << '\t'
                         << benchmark.nsPerLogicalEvent << '\t'
                         << benchmark.nsPerMaterializedRecord << '\t'
                         << benchmark.nsPerPrunedRecord << '\n';
        }
    }

    if (!outputTsvPath.empty())
    {
        if (!write_text_file(outputTsvPath, tsv.str()))
        {
            std::cerr << "Failed to write TSV: " << outputTsvPath << "\n";
            return 1;
        }
    }
    else
    {
        std::cout << tsv.str();
    }

    if (!aggregateTsvPath.empty())
    {
        if (!write_text_file(aggregateTsvPath, aggregateTsv.str()))
        {
            std::cerr << "Failed to write aggregate TSV: " << aggregateTsvPath << "\n";
            return 1;
        }
    }

    return success ? 0 : 1;
}
