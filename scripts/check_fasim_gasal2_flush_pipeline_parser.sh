#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_flush_pipeline_parser"}"

rm -rf "$WORK"
mkdir -p "$WORK"

cat >"$WORK/flush_pipeline.tsv" <<'TSV'
flush_id	shard_name	worker_id	gpu_id	flush_sequence	pack_start_ns	pack_end_ns	wait_for_free_buffer_start_ns	wait_for_free_buffer_end_ns	h2d_start_ns	h2d_end_ns	gasal2_score_submit_start_ns	gasal2_score_submit_end_ns	gasal2_score_wait_start_ns	gasal2_score_wait_end_ns	exact_column_start_ns	exact_column_end_ns	traceback_pack_start_ns	traceback_pack_end_ns	traceback_submit_start_ns	traceback_submit_end_ns	traceback_wait_start_ns	traceback_wait_end_ns	d2h_start_ns	d2h_end_ns	convert_start_ns	convert_end_ns	archive_enqueue_start_ns	archive_enqueue_end_ns	archive_write_start_ns	archive_write_end_ns	sort_dedup_start_ns	sort_dedup_end_ns	flush_complete_ns	gpu_event_timing_available	gasal2_score_poll_wait_seconds	gasal2_score_result_copy_seconds	gasal2_traceback_poll_wait_seconds	gasal2_traceback_result_copy_seconds	gasal2_traceback_cigar_vector_seconds	gasal2_traceback_cigar_string_seconds	gasal2_synchronous_wait_seconds	synchronous_flush_path	queue_supported	gasal2_requests	dp_cells	scoreinfo_tasks	selected_scoreinfos	traceback_requests	traceback_cigar_raw_ops	traceback_cigar_merged_ops	converted_candidates	emitted_rows	final_rows_after_sort_dedup	dedup_removed_rows	archive_bytes	archive_blocks	input_queue_depth_at_start	input_queue_depth_at_end	input_queue_depth_available	ready_queue_depth_at_start	ready_queue_depth_at_end	ready_queue_depth_available	convert_queue_depth_at_start	convert_queue_depth_at_end	convert_queue_depth_available	archive_queue_depth_at_start	archive_queue_depth_at_end	archive_queue_depth_available	gpu_producer_blocked_seconds	gpu_producer_blocked_available	cpu_consumer_idle_seconds	cpu_consumer_idle_available	archive_writer_blocked_seconds	archive_writer_blocked_available	waiting_for_free_buffer_seconds	waiting_for_free_buffer_available	gpu_inter_flush_idle_gap_seconds	gpu_inter_flush_idle_gap_available	host_pack_gap_seconds	host_pack_gap_available	decision_hint
1	chrA	0	0	1	0	100000000	100000000	100000000	100000000	150000000	150000000	160000000	160000000	1000000000	1000000000	1100000000	1100000000	1200000000	1200000000	1300000000	1300000000	5000000000	5000000000	5100000000	5100000000	7100000000	7100000000	7150000000	7150000000	7350000000	7350000000	7450000000	7450000000	false	0.700000	0.140000	2.900000	0.320000	0.080000	0.010000	3.600000	true	false	1000	2500000	100	90	400	10000	5000	300	240	200	40	20000	2	NA	NA	false	NA	NA	false	NA	NA	false	NA	NA	false	0.0	false	0.0	false	0.0	false	0.0	false	0.0	false	0.0	false	gpu_dominant
2	chrA	0	0	2	7450000000	7550000000	7550000000	7550000000	7550000000	7600000000	7600000000	7610000000	7610000000	8610000000	8610000000	8710000000	8710000000	8810000000	8810000000	8820000000	8820000000	10820000000	10820000000	10870000000	10870000000	14870000000	14870000000	14920000000	14920000000	15020000000	15020000000	15120000000	15120000000	false	0.850000	0.150000	1.750000	0.200000	0.050000	0.000000	2.600000	true	false	1200	3000000	110	100	500	12000	6000	500	300	260	40	24000	3	NA	NA	false	NA	NA	false	NA	NA	false	NA	NA	false	0.0	false	0.0	false	0.0	false	0.0	false	0.0	false	0.0	false	convert_heavy
3	chrA	0	0	3	15120000000	15220000000	15220000000	15220000000	15220000000	15270000000	15270000000	15280000000	15280000000	17280000000	17280000000	17330000000	17330000000	17430000000	17430000000	17440000000	17440000000	21440000000	21440000000	21490000000	21490000000	22490000000	22490000000	22540000000	22540000000	22640000000	22640000000	22740000000	22740000000	false	1.800000	0.200000	3.300000	0.500000	0.110000	0.020000	5.100000	true	false	2000	5000000	180	170	900	20000	10000	900	550	500	50	40000	4	NA	NA	false	NA	NA	false	NA	NA	false	NA	NA	false	0.0	false	0.0	false	0.0	false	0.0	false	0.0	false	0.0	false	traceback_heavy
TSV

cat >"$WORK/trace.json" <<'JSON'
{"traceEvents":[
  {"name":"pack","cat":"Host pack","ph":"X","ts":0,"dur":100000,"pid":"chrA","tid":"Host pack","args":{"flush_id":1}},
  {"name":"gpu_path","cat":"GPU stream","ph":"X","ts":100000,"dur":4900000,"pid":"chrA","tid":"GPU stream","args":{"flush_id":1}},
  {"name":"convert","cat":"CPU convert","ph":"X","ts":5100000,"dur":2000000,"pid":"chrA","tid":"CPU convert","args":{"flush_id":1}}
]}
JSON

python3 "$ROOT/scripts/summarize_fasim_gasal2_flush_pipeline.py" \
  --flush-tsv "$WORK/flush_pipeline.tsv" \
  --chrome-trace "$WORK/trace.json" \
  --output-summary "$WORK/summary.txt" \
  --output-tsv "$WORK/summary_flush.tsv"

grep -q '^flushes=3$' "$WORK/summary.txt"
grep -q '^total_flush_wall_seconds=22.740000$' "$WORK/summary.txt"
grep -q '^p50_flush_wall_seconds=7.620000$' "$WORK/summary.txt"
grep -q '^p90_flush_wall_seconds=7.670000$' "$WORK/summary.txt"
grep -q '^max_flush_wall_seconds=7.670000$' "$WORK/summary.txt"
grep -q '^total_requests=4200$' "$WORK/summary.txt"
grep -q '^total_traceback_requests=1800$' "$WORK/summary.txt"
grep -q '^total_gasal2_score_poll_wait_seconds=3.350000$' "$WORK/summary.txt"
grep -q '^total_gasal2_traceback_poll_wait_seconds=7.950000$' "$WORK/summary.txt"
grep -q '^total_gasal2_synchronous_wait_seconds=11.300000$' "$WORK/summary.txt"
grep -q '^total_gasal2_result_copy_seconds=1.510000$' "$WORK/summary.txt"
grep -q '^queue_supported=0$' "$WORK/summary.txt"
grep -q '^synchronous_flush_path=1$' "$WORK/summary.txt"
grep -q '^wall_corr_requests=0.475218$' "$WORK/summary.txt"
grep -q '^simulated_two_buffer_speedup=' "$WORK/summary.txt"
grep -q '^simulated_convert_workers_2_speedup=' "$WORK/summary.txt"
grep -q '^archive_writer_is_bottleneck=0$' "$WORK/summary.txt"
grep -q '^gpu_is_bottleneck=1$' "$WORK/summary.txt"
grep -q '^decision=telemetry_incomplete$' "$WORK/summary.txt"
grep -q '^chrome_trace_events=3$' "$WORK/summary.txt"
grep -q '^simulation_assumption=' "$WORK/summary.txt"
grep -q '^1	chrA	7.450000	1000	400' "$WORK/summary_flush.tsv"
grep -q '3.600000' "$WORK/summary_flush.tsv"

echo "check_fasim_gasal2_flush_pipeline_parser: ok"
