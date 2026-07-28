#ifndef FASIM_SSW_ORACLE_TRACE_H
#define FASIM_SSW_ORACLE_TRACE_H

#include <stdint.h>

#include <string>

namespace fasim_ssw_oracle {

bool enabled();
bool full_columns_enabled();

void begin_workload(const std::string& query,
	const std::string& target,
	long dna_start,
	long rule,
	long strand);
void end_workload();

void begin_prealign(const char* query,
	int32_t query_len,
	const char* ref,
	int32_t ref_len,
	int match_score,
	int mismatch_penalty,
	int gap_open,
	int gap_extend,
	int32_t mask_len);
void record_prealign_columns_u8(const uint8_t* columns,
	int32_t count,
	const char* numeric_path);
void record_prealign_columns_u16(const uint16_t* columns,
	int32_t count,
	const char* numeric_path);
void set_prealign_final_numeric_path(const char* numeric_path);
void append_prealign_scoreinfo(int index, int score, int position);
void finish_prealign(int threshold);

std::string begin_attempt(int scoreinfo_index,
	int prealign_score,
	int identity_round,
	double identity,
	int target_start,
	int cutlength);
void finish_scoreinfo_group(int scoreinfo_index,
	const std::string& selected_attempt_key,
	const char* selection_reason);
void record_emitted_row(const std::string& attempt_key,
	int query_start,
	int query_end,
	int target_start,
	int target_end,
	int strand,
	int reverse,
	int rule,
	int nt,
	float score,
	float identity,
	float stability,
	const std::string& aligned_tfo,
	const std::string& aligned_tts);
void publish_workload_records();

void begin_alignment(const char* query,
	int32_t query_len,
	const char* ref,
	int32_t ref_len,
	int match_score,
	int mismatch_penalty,
	int gap_open,
	int gap_extend,
	int32_t mask_len,
	uint8_t flag,
	uint16_t score_filter,
	int32_t distance_filter);
void record_alignment_dp_pass_u8(const uint8_t* columns,
	int32_t count,
	int ref_dir,
	const char* numeric_path,
	int best_score,
	int best_ref,
	int best_read,
	int second_score,
	int second_ref);
void record_alignment_dp_pass_u16(const uint16_t* columns,
	int32_t count,
	int ref_dir,
	const char* numeric_path,
	int best_score,
	int best_ref,
	int best_read,
	int second_score,
	int second_ref);
void set_alignment_final_numeric_path(const char* numeric_path);
void record_band_iteration(int band_width, int max_score, int target_score);
void finish_alignment(int score1,
	int score2,
	int ref_begin1,
	int ref_end1,
	int read_begin1,
	int read_end1,
	int ref_end2,
	const std::string& cigar,
	int cigar_len);
void abort_alignment(const char* reason);

}  // namespace fasim_ssw_oracle

#endif
