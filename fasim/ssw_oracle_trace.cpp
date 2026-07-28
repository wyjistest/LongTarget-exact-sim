#include "ssw_oracle_trace.h"

#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <algorithm>
#include <fstream>
#include <iomanip>
#include <limits>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace fasim_ssw_oracle {
namespace {

const char* const kTraceEnv = "FASIM_SSW_ORACLE_TRACE";
const char* const kTraceDirEnv = "FASIM_SSW_ORACLE_TRACE_DIR";
const char* const kTraceFilterEnv = "FASIM_SSW_ORACLE_TRACE_FILTER";
const char* const kFullColumnsEnv = "FASIM_SSW_ORACLE_TRACE_FULL_COLUMNS";

struct Config {
	bool initialized;
	bool active;
	bool full_columns;
	std::string directory;
	std::vector<std::string> filters;

	Config() : initialized(false), active(false), full_columns(false) {}
};

struct Workload {
	bool active;
	std::string key;
	std::string query_digest;
	std::string target_digest;
	int32_t query_len;
	int32_t target_len;
	long dna_start;
	long rule;
	long strand;

	Workload() : active(false), query_len(0), target_len(0), dna_start(0), rule(0), strand(0) {}
};

struct ColumnPass {
	std::string stage;
	std::string numeric_path;
	int ref_dir;
	int32_t count;
	int max_score;
	std::string digest;
	std::vector<int> columns;
	int best_score;
	int best_ref;
	int best_read;
	int second_score;
	int second_ref;

	ColumnPass() : ref_dir(0), count(0), max_score(0), best_score(0), best_ref(-1),
		best_read(-1), second_score(0), second_ref(-1) {}
};

struct ScoreInfoValue {
	int index;
	int score;
	int position;
};

struct PrealignRecord {
	bool active;
	std::string key;
	std::string query_digest;
	std::string ref_digest;
	int32_t query_len;
	int32_t ref_len;
	int match_score;
	int mismatch_penalty;
	int gap_open;
	int gap_extend;
	int32_t mask_len;
	int threshold;
	std::string final_numeric_path;
	std::vector<ColumnPass> passes;
	std::vector<ScoreInfoValue> selected;

	PrealignRecord() : active(false), query_len(0), ref_len(0), match_score(0),
		mismatch_penalty(0), gap_open(0), gap_extend(0), mask_len(0), threshold(0) {}
};

struct Attempt {
	bool active;
	std::string key;
	int scoreinfo_index;
	int prealign_score;
	int identity_round;
	int identity_ppm;
	int target_start;
	int cutlength;

	Attempt() : active(false), scoreinfo_index(-1), prealign_score(0), identity_round(-1),
		identity_ppm(0), target_start(-1), cutlength(0) {}
};

struct BandStep {
	int band_width;
	int max_score;
	int target_score;
};

struct EmittedRow {
	int query_start;
	int query_end;
	int target_start;
	int target_end;
	int strand;
	int reverse;
	int rule;
	int nt;
	float score;
	float identity;
	float stability;
	std::string aligned_tfo;
	std::string aligned_tts;
	std::string ungapped_tfo;
	std::string ungapped_tts;
	std::string digest;
};

struct AlignmentRecord {
	std::string key;
	Attempt attempt;
	std::string query_digest;
	std::string ref_digest;
	int32_t query_len;
	int32_t ref_len;
	int match_score;
	int mismatch_penalty;
	int gap_open;
	int gap_extend;
	int32_t mask_len;
	int flag;
	int score_filter;
	int distance_filter;
	std::string final_numeric_path;
	std::vector<ColumnPass> passes;
	std::vector<BandStep> band_history;
	std::vector<EmittedRow> emitted_rows;
	std::string status;
	std::string failure_reason;
	int score1;
	int score2;
	int ref_begin1;
	int ref_end1;
	int read_begin1;
	int read_end1;
	int ref_end2;
	std::string cigar;
	int cigar_len;
	bool selected;
	std::string selection_reason;

	AlignmentRecord() : query_len(0), ref_len(0), match_score(0), mismatch_penalty(0),
		gap_open(0), gap_extend(0), mask_len(0), flag(0), score_filter(0),
		distance_filter(0), score1(0), score2(0), ref_begin1(-1), ref_end1(-1),
		read_begin1(-1), read_end1(-1), ref_end2(-1), cigar_len(0), selected(false) {}
};

struct State {
	Config config;
	Workload workload;
	PrealignRecord prealign;
	Attempt attempt;
	bool alignment_active;
	AlignmentRecord alignment;
	std::vector<AlignmentRecord> pending;
	uint64_t direct_call_ordinal;

	State() : alignment_active(false), direct_call_ordinal(0) {}
};

thread_local State g_state;
std::mutex g_write_mutex;

bool env_enabled(const char* name) {
	const char* value = getenv(name);
	return value != NULL && value[0] != '\0' && value[0] != '0';
}

uint64_t fnv1a_bytes(const void* data, size_t size, uint64_t hash = 1469598103934665603ULL) {
	const uint8_t* bytes = static_cast<const uint8_t*>(data);
	for (size_t i = 0; i < size; ++i) {
		hash ^= bytes[i];
		hash *= 1099511628211ULL;
	}
	return hash;
}

std::string hex64(uint64_t value) {
	std::ostringstream out;
	out << std::hex << std::setfill('0') << std::setw(16) << value;
	return out.str();
}

std::string digest_bytes(const char* data, int32_t size) {
	if (data == NULL || size <= 0) return hex64(fnv1a_bytes(NULL, 0));
	return hex64(fnv1a_bytes(data, static_cast<size_t>(size)));
}

template <typename T>
std::string digest_columns(const T* values, int32_t count) {
	uint64_t hash = 1469598103934665603ULL;
	for (int32_t i = 0; i < count; ++i) {
		const uint64_t value = static_cast<uint64_t>(values[i]);
		for (int shift = 0; shift < 64; shift += 8) {
			const uint8_t byte = static_cast<uint8_t>((value >> shift) & 0xffU);
			hash = fnv1a_bytes(&byte, 1, hash);
		}
	}
	const uint64_t count_value = static_cast<uint64_t>(count);
	for (int shift = 0; shift < 64; shift += 8) {
		const uint8_t byte = static_cast<uint8_t>((count_value >> shift) & 0xffU);
		hash = fnv1a_bytes(&byte, 1, hash);
	}
	return hex64(hash);
}

std::string json_escape(const std::string& value) {
	std::ostringstream out;
	for (size_t i = 0; i < value.size(); ++i) {
		const unsigned char c = static_cast<unsigned char>(value[i]);
		switch (c) {
		case '"': out << "\\\""; break;
		case '\\': out << "\\\\"; break;
		case '\b': out << "\\b"; break;
		case '\f': out << "\\f"; break;
		case '\n': out << "\\n"; break;
		case '\r': out << "\\r"; break;
		case '\t': out << "\\t"; break;
		default:
			if (c < 0x20) {
				out << "\\u" << std::hex << std::setfill('0') << std::setw(4)
					<< static_cast<unsigned int>(c) << std::dec;
			}
			else {
				out << static_cast<char>(c);
			}
		}
	}
	return out.str();
}

std::string quote(const std::string& value) {
	return std::string("\"") + json_escape(value) + "\"";
}

std::string float_text(float value) {
	std::ostringstream out;
	out << std::setprecision(std::numeric_limits<float>::max_digits10) << value;
	return out.str();
}

std::string without_gaps(const std::string& value) {
	std::string result;
	result.reserve(value.size());
	for (size_t i = 0; i < value.size(); ++i) {
		if (value[i] != '-') result.push_back(value[i]);
	}
	return result;
}

std::string emitted_row_payload(const EmittedRow& row) {
	std::ostringstream out;
	out << "triplex_l6_v1\t"
		<< row.query_start << '\t' << row.query_end << '\t'
		<< row.target_start << '\t' << row.target_end << '\t'
		<< (row.target_start < row.target_end ? "R" : "L") << '\t'
		<< row.strand << '\t' << row.reverse << '\t' << row.rule << '\t'
		<< float_text(row.score) << '\t' << row.nt << '\t'
		<< float_text(row.identity) << '\t' << float_text(row.stability) << '\t'
		<< row.aligned_tfo << '\t' << row.aligned_tts << '\t'
		<< row.ungapped_tfo << '\t' << row.ungapped_tts;
	return out.str();
}

void split_filters(const std::string& text, std::vector<std::string>* output) {
	output->clear();
	size_t begin = 0;
	while (begin <= text.size()) {
		const size_t comma = text.find(',', begin);
		const size_t end = comma == std::string::npos ? text.size() : comma;
		const std::string token = text.substr(begin, end - begin);
		if (!token.empty()) output->push_back(token);
		if (comma == std::string::npos) break;
		begin = comma + 1;
	}
}

void initialize_config() {
	Config& config = g_state.config;
	if (config.initialized) return;
	config.initialized = true;
	config.active = env_enabled(kTraceEnv);
	config.full_columns = env_enabled(kFullColumnsEnv);
	if (!config.active) return;
	const char* directory = getenv(kTraceDirEnv);
	if (directory == NULL || directory[0] == '\0') {
		throw std::runtime_error("FASIM_SSW_ORACLE_TRACE_DIR is required when oracle trace is enabled");
	}
	config.directory = directory;
	const char* filter = getenv(kTraceFilterEnv);
	if (filter != NULL && filter[0] != '\0' && std::string(filter) != "*") {
		split_filters(filter, &config.filters);
	}
}

bool record_matches_filter(const std::string& key) {
	const Config& config = g_state.config;
	if (config.filters.empty()) return true;
	for (size_t i = 0; i < config.filters.size(); ++i) {
		if (key.find(config.filters[i]) != std::string::npos ||
			g_state.workload.key.find(config.filters[i]) != std::string::npos) {
			return true;
		}
	}
	return false;
}

void mkdir_one(const std::string& path) {
	if (path.empty()) return;
	struct stat st;
	if (stat(path.c_str(), &st) == 0) {
		if (!S_ISDIR(st.st_mode)) throw std::runtime_error("oracle trace path is not a directory: " + path);
		return;
	}
	if (errno != ENOENT || mkdir(path.c_str(), 0775) != 0) {
		throw std::runtime_error("cannot create oracle trace directory: " + path);
	}
}

void mkdir_p(const std::string& path) {
	if (path.empty()) throw std::runtime_error("empty oracle trace directory");
	std::string current;
	if (path[0] == '/') current = "/";
	size_t begin = path[0] == '/' ? 1 : 0;
	while (begin <= path.size()) {
		const size_t slash = path.find('/', begin);
		const size_t end = slash == std::string::npos ? path.size() : slash;
		const std::string component = path.substr(begin, end - begin);
		if (!component.empty()) {
			if (!current.empty() && current[current.size() - 1] != '/') current += '/';
			current += component;
			mkdir_one(current);
		}
		if (slash == std::string::npos) break;
		begin = slash + 1;
	}
}

std::string safe_component(const std::string& value) {
	std::string result;
	result.reserve(value.size());
	for (size_t i = 0; i < value.size(); ++i) {
		const char c = value[i];
		if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
			(c >= '0' && c <= '9') || c == '-' || c == '_') {
			result.push_back(c);
		}
		else {
			result.push_back('_');
		}
	}
	return result;
}

void atomic_write_json(const std::string& key, const std::string& payload) {
	if (!record_matches_filter(key)) return;
	std::lock_guard<std::mutex> lock(g_write_mutex);
	mkdir_p(g_state.config.directory);
	const std::string final_path = g_state.config.directory + "/" + safe_component(key) + ".json";
	struct stat st;
	if (stat(final_path.c_str(), &st) == 0) {
		throw std::runtime_error("oracle trace refuses to overwrite: " + final_path);
	}
	std::ostringstream temp_name;
	temp_name << final_path << ".tmp." << static_cast<long>(getpid());
	const std::string temp_path = temp_name.str();
	{
		std::ofstream output(temp_path.c_str(), std::ios::out | std::ios::binary | std::ios::trunc);
		if (!output) throw std::runtime_error("cannot open oracle trace temporary file: " + temp_path);
		output << payload;
		output.flush();
		if (!output) throw std::runtime_error("cannot write oracle trace: " + temp_path);
	}
	if (rename(temp_path.c_str(), final_path.c_str()) != 0) {
		remove(temp_path.c_str());
		throw std::runtime_error("cannot publish oracle trace: " + final_path);
	}
}

void append_workload_json(std::ostringstream& out) {
	const Workload& workload = g_state.workload;
	out << "  \"workload\": {\n"
		<< "    \"key\": " << quote(workload.key) << ",\n"
		<< "    \"query_digest_fnv1a64\": " << quote(workload.query_digest) << ",\n"
		<< "    \"target_digest_fnv1a64\": " << quote(workload.target_digest) << ",\n"
		<< "    \"query_length\": " << workload.query_len << ",\n"
		<< "    \"target_length\": " << workload.target_len << ",\n"
		<< "    \"dna_start\": " << workload.dna_start << ",\n"
		<< "    \"rule\": " << workload.rule << ",\n"
		<< "    \"strand\": " << workload.strand << "\n"
		<< "  },\n";
}

void append_columns_json(std::ostringstream& out,
	const std::vector<ColumnPass>& passes,
	const std::string& indent) {
	out << indent << "\"dp_passes\": [";
	if (!passes.empty()) out << "\n";
	for (size_t i = 0; i < passes.size(); ++i) {
		const ColumnPass& pass = passes[i];
		out << indent << "  {\n"
			<< indent << "    \"stage\": " << quote(pass.stage) << ",\n"
			<< indent << "    \"numeric_path\": " << quote(pass.numeric_path) << ",\n"
			<< indent << "    \"ref_direction\": " << pass.ref_dir << ",\n"
			<< indent << "    \"column_count\": " << pass.count << ",\n"
			<< indent << "    \"column_max_digest_fnv1a64\": " << quote(pass.digest) << ",\n"
			<< indent << "    \"maximum_score\": " << pass.max_score << ",\n"
			<< indent << "    \"best_score\": " << pass.best_score << ",\n"
			<< indent << "    \"best_ref\": " << pass.best_ref << ",\n"
			<< indent << "    \"best_read\": " << pass.best_read << ",\n"
			<< indent << "    \"second_score\": " << pass.second_score << ",\n"
			<< indent << "    \"second_ref\": " << pass.second_ref << ",\n"
			<< indent << "    \"columns\": ";
		if (pass.columns.empty()) {
			out << "null\n";
		}
		else {
			out << "[";
			for (size_t j = 0; j < pass.columns.size(); ++j) {
				if (j != 0) out << ", ";
				out << pass.columns[j];
			}
			out << "]\n";
		}
		out << indent << "  }" << (i + 1 == passes.size() ? "\n" : ",\n");
	}
	out << indent << "]";
}

std::string serialize_prealign(const PrealignRecord& record) {
	std::ostringstream out;
	out << "{\n"
		<< "  \"schema_version\": \"1\",\n"
		<< "  \"oracle_epoch\": 2,\n"
		<< "  \"record_kind\": \"prealign\",\n"
		<< "  \"record_key\": " << quote(record.key) << ",\n";
	append_workload_json(out);
	out << "  \"input\": {\n"
		<< "    \"query_digest_fnv1a64\": " << quote(record.query_digest) << ",\n"
		<< "    \"reference_digest_fnv1a64\": " << quote(record.ref_digest) << ",\n"
		<< "    \"query_length\": " << record.query_len << ",\n"
		<< "    \"reference_length\": " << record.ref_len << "\n"
		<< "  },\n"
		<< "  \"scoring\": {\n"
		<< "    \"match\": " << record.match_score << ",\n"
		<< "    \"mismatch_penalty\": " << record.mismatch_penalty << ",\n"
		<< "    \"gap_open\": " << record.gap_open << ",\n"
		<< "    \"gap_extend\": " << record.gap_extend << ",\n"
		<< "    \"mask_len\": " << record.mask_len << "\n"
		<< "  },\n"
		<< "  \"final_numeric_path\": " << quote(record.final_numeric_path) << ",\n";
	append_columns_json(out, record.passes, "  ");
	out << ",\n"
		<< "  \"selection\": {\n"
		<< "    \"threshold\": " << record.threshold << ",\n"
		<< "    \"threshold_predicate\": \"score_strictly_greater_than_threshold\",\n"
		<< "    \"adjacent_distance_exclusive_upper_bound\": 5,\n"
		<< "    \"equal_score_tie\": \"lowest_reference_position\",\n"
		<< "    \"scoreinfos\": [";
	if (!record.selected.empty()) out << "\n";
	for (size_t i = 0; i < record.selected.size(); ++i) {
		out << "      {\"index\": " << record.selected[i].index
			<< ", \"score\": " << record.selected[i].score
			<< ", \"position\": " << record.selected[i].position << "}"
			<< (i + 1 == record.selected.size() ? "\n" : ",\n");
	}
	out << "    ]\n"
		<< "  }\n"
		<< "}\n";
	return out.str();
}

std::string serialize_alignment(const AlignmentRecord& record) {
	std::ostringstream out;
	out << "{\n"
		<< "  \"schema_version\": \"1\",\n"
		<< "  \"oracle_epoch\": 2,\n"
		<< "  \"record_kind\": \"alignment\",\n"
		<< "  \"record_key\": " << quote(record.key) << ",\n";
	append_workload_json(out);
	out << "  \"attempt\": {\n"
		<< "    \"key\": " << quote(record.attempt.key) << ",\n"
		<< "    \"scoreinfo_index\": " << record.attempt.scoreinfo_index << ",\n"
		<< "    \"prealign_score\": " << record.attempt.prealign_score << ",\n"
		<< "    \"identity_round\": " << record.attempt.identity_round << ",\n"
		<< "    \"identity_ppm\": " << record.attempt.identity_ppm << ",\n"
		<< "    \"target_start\": " << record.attempt.target_start << ",\n"
		<< "    \"cutlength\": " << record.attempt.cutlength << ",\n"
		<< "    \"selected\": " << (record.selected ? "true" : "false") << ",\n"
		<< "    \"selection_reason\": " << quote(record.selection_reason) << "\n"
		<< "  },\n"
		<< "  \"input\": {\n"
		<< "    \"query_digest_fnv1a64\": " << quote(record.query_digest) << ",\n"
		<< "    \"reference_digest_fnv1a64\": " << quote(record.ref_digest) << ",\n"
		<< "    \"query_length\": " << record.query_len << ",\n"
		<< "    \"reference_length\": " << record.ref_len << "\n"
		<< "  },\n"
		<< "  \"scoring\": {\n"
		<< "    \"match\": " << record.match_score << ",\n"
		<< "    \"mismatch_penalty\": " << record.mismatch_penalty << ",\n"
		<< "    \"gap_open\": " << record.gap_open << ",\n"
		<< "    \"gap_extend\": " << record.gap_extend << ",\n"
		<< "    \"mask_len\": " << record.mask_len << ",\n"
		<< "    \"flag\": " << record.flag << ",\n"
		<< "    \"score_filter\": " << record.score_filter << ",\n"
		<< "    \"distance_filter\": " << record.distance_filter << "\n"
		<< "  },\n"
		<< "  \"status\": " << quote(record.status) << ",\n"
		<< "  \"failure_reason\": " << quote(record.failure_reason) << ",\n"
		<< "  \"final_numeric_path\": " << quote(record.final_numeric_path) << ",\n";
	append_columns_json(out, record.passes, "  ");
	out << ",\n"
		<< "  \"forward_endpoint\": {\n"
		<< "    \"score1\": " << record.score1 << ",\n"
		<< "    \"score2\": " << record.score2 << ",\n"
		<< "    \"ref_end1\": " << record.ref_end1 << ",\n"
		<< "    \"read_end1\": " << record.read_end1 << ",\n"
		<< "    \"ref_end2\": " << record.ref_end2 << "\n"
		<< "  },\n"
		<< "  \"reverse_start\": {\n"
		<< "    \"ref_begin1\": " << record.ref_begin1 << ",\n"
		<< "    \"read_begin1\": " << record.read_begin1 << "\n"
		<< "  },\n"
		<< "  \"band_history\": [";
	if (!record.band_history.empty()) out << "\n";
	for (size_t i = 0; i < record.band_history.size(); ++i) {
		out << "    {\"band_width\": " << record.band_history[i].band_width
			<< ", \"maximum_score\": " << record.band_history[i].max_score
			<< ", \"target_score\": " << record.band_history[i].target_score << "}"
			<< (i + 1 == record.band_history.size() ? "\n" : ",\n");
	}
	out << "  ],\n"
		<< "  \"traceback\": {\n"
		<< "    \"stop_rule\": \"read_index_reaches_zero_then_force_terminal_match\",\n"
		<< "    \"cigar\": " << quote(record.cigar) << ",\n"
		<< "    \"cigar_operation_count\": " << record.cigar_len << ",\n"
		<< "    \"cigar_digest_fnv1a64\": "
		<< quote(hex64(fnv1a_bytes(record.cigar.data(), record.cigar.size()))) << "\n"
		<< "  },\n"
		<< "  \"emitted_rows\": [";
	if (!record.emitted_rows.empty()) out << "\n";
	for (size_t i = 0; i < record.emitted_rows.size(); ++i) {
		const EmittedRow& row = record.emitted_rows[i];
		out << "    {\n"
			<< "      \"row_contract\": \"triplex_l6_v1\",\n"
			<< "      \"query_start\": " << row.query_start << ",\n"
			<< "      \"query_end\": " << row.query_end << ",\n"
			<< "      \"target_start\": " << row.target_start << ",\n"
			<< "      \"target_end\": " << row.target_end << ",\n"
			<< "      \"direction\": " << quote(row.target_start < row.target_end ? "R" : "L") << ",\n"
			<< "      \"strand\": " << row.strand << ",\n"
			<< "      \"reverse\": " << row.reverse << ",\n"
			<< "      \"rule\": " << row.rule << ",\n"
			<< "      \"score\": " << float_text(row.score) << ",\n"
			<< "      \"nt\": " << row.nt << ",\n"
			<< "      \"mean_identity\": " << float_text(row.identity) << ",\n"
			<< "      \"mean_stability\": " << float_text(row.stability) << ",\n"
			<< "      \"aligned_tfo\": " << quote(row.aligned_tfo) << ",\n"
			<< "      \"aligned_tts\": " << quote(row.aligned_tts) << ",\n"
			<< "      \"ungapped_tfo\": " << quote(row.ungapped_tfo) << ",\n"
			<< "      \"ungapped_tts\": " << quote(row.ungapped_tts) << ",\n"
			<< "      \"row_digest_fnv1a64\": " << quote(row.digest) << "\n"
			<< "    }" << (i + 1 == record.emitted_rows.size() ? "\n" : ",\n");
	}
	out << "  ]\n"
		<< "}\n";
	return out.str();
}

template <typename T>
ColumnPass build_pass(const T* columns,
	int32_t count,
	const char* stage,
	int ref_dir,
	const char* numeric_path,
	int best_score,
	int best_ref,
	int best_read,
	int second_score,
	int second_ref) {
	ColumnPass pass;
	pass.stage = stage;
	pass.numeric_path = numeric_path == NULL ? "unknown" : numeric_path;
	pass.ref_dir = ref_dir;
	pass.count = count;
	pass.best_score = best_score;
	pass.best_ref = best_ref;
	pass.best_read = best_read;
	pass.second_score = second_score;
	pass.second_ref = second_ref;
	pass.digest = digest_columns(columns, count);
	for (int32_t i = 0; i < count; ++i) {
		pass.max_score = std::max(pass.max_score, static_cast<int>(columns[i]));
		if (g_state.config.full_columns) pass.columns.push_back(static_cast<int>(columns[i]));
	}
	return pass;
}

void write_alignment(AlignmentRecord record) {
	if (record.selection_reason.empty()) record.selection_reason = "not_selected";
	atomic_write_json(record.key, serialize_alignment(record));
}

void flush_pending_unresolved() {
	for (size_t i = 0; i < g_state.pending.size(); ++i) {
		g_state.pending[i].selected = false;
		g_state.pending[i].selection_reason = "unresolved_at_workload_end";
		write_alignment(g_state.pending[i]);
	}
	g_state.pending.clear();
}

}  // namespace

bool enabled() {
	initialize_config();
	return g_state.config.active;
}

bool full_columns_enabled() {
	initialize_config();
	return g_state.config.active && g_state.config.full_columns;
}

void begin_workload(const std::string& query,
	const std::string& target,
	long dna_start,
	long rule,
	long strand) {
	if (!enabled()) return;
	if (g_state.workload.active) throw std::runtime_error("nested SSW oracle workload");
	g_state.workload = Workload();
	g_state.workload.active = true;
	g_state.workload.query_digest = digest_bytes(query.data(), static_cast<int32_t>(query.size()));
	g_state.workload.target_digest = digest_bytes(target.data(), static_cast<int32_t>(target.size()));
	g_state.workload.query_len = static_cast<int32_t>(query.size());
	g_state.workload.target_len = static_cast<int32_t>(target.size());
	g_state.workload.dna_start = dna_start;
	g_state.workload.rule = rule;
	g_state.workload.strand = strand;
	std::ostringstream key;
	key << "w-q" << g_state.workload.query_digest
		<< "-t" << g_state.workload.target_digest
		<< "-d" << dna_start << "-r" << rule << "-s" << strand;
	g_state.workload.key = key.str();
}

void end_workload() {
	if (!enabled()) return;
	if (g_state.alignment_active) abort_alignment("workload_ended_during_alignment");
	if (g_state.prealign.active) finish_prealign(std::numeric_limits<int>::min());
	flush_pending_unresolved();
	g_state.attempt = Attempt();
	g_state.workload = Workload();
}

void begin_prealign(const char* query,
	int32_t query_len,
	const char* ref,
	int32_t ref_len,
	int match_score,
	int mismatch_penalty,
	int gap_open,
	int gap_extend,
	int32_t mask_len) {
	if (!enabled()) return;
	if (!g_state.workload.active) throw std::runtime_error("prealign trace has no workload context");
	if (g_state.prealign.active) throw std::runtime_error("nested prealign trace");
	g_state.prealign = PrealignRecord();
	g_state.prealign.active = true;
	g_state.prealign.key = "prealign-" + g_state.workload.key;
	g_state.prealign.query_digest = digest_bytes(query, query_len);
	g_state.prealign.ref_digest = digest_bytes(ref, ref_len);
	g_state.prealign.query_len = query_len;
	g_state.prealign.ref_len = ref_len;
	g_state.prealign.match_score = match_score;
	g_state.prealign.mismatch_penalty = mismatch_penalty;
	g_state.prealign.gap_open = gap_open;
	g_state.prealign.gap_extend = gap_extend;
	g_state.prealign.mask_len = mask_len;
}

void record_prealign_columns_u8(const uint8_t* columns,
	int32_t count,
	const char* numeric_path) {
	if (!enabled() || !g_state.prealign.active) return;
	g_state.prealign.passes.push_back(build_pass(columns, count, "prealign", 0,
		numeric_path, 0, -1, -1, 0, -1));
}

void record_prealign_columns_u16(const uint16_t* columns,
	int32_t count,
	const char* numeric_path) {
	if (!enabled() || !g_state.prealign.active) return;
	g_state.prealign.passes.push_back(build_pass(columns, count, "prealign", 0,
		numeric_path, 0, -1, -1, 0, -1));
}

void set_prealign_final_numeric_path(const char* numeric_path) {
	if (!enabled() || !g_state.prealign.active) return;
	g_state.prealign.final_numeric_path = numeric_path == NULL ? "unknown" : numeric_path;
}

void append_prealign_scoreinfo(int index, int score, int position) {
	if (!enabled() || !g_state.prealign.active) return;
	ScoreInfoValue value;
	value.index = index;
	value.score = score;
	value.position = position;
	g_state.prealign.selected.push_back(value);
}

void finish_prealign(int threshold) {
	if (!enabled() || !g_state.prealign.active) return;
	g_state.prealign.threshold = threshold;
	if (g_state.prealign.final_numeric_path.empty()) g_state.prealign.final_numeric_path = "unknown";
	atomic_write_json(g_state.prealign.key, serialize_prealign(g_state.prealign));
	g_state.prealign = PrealignRecord();
}

std::string begin_attempt(int scoreinfo_index,
	int prealign_score,
	int identity_round,
	double identity,
	int target_start,
	int cutlength) {
	if (!enabled()) return std::string();
	if (!g_state.workload.active) throw std::runtime_error("attempt trace has no workload context");
	if (g_state.attempt.active) throw std::runtime_error("nested SSW oracle attempt");
	g_state.attempt = Attempt();
	g_state.attempt.active = true;
	g_state.attempt.scoreinfo_index = scoreinfo_index;
	g_state.attempt.prealign_score = prealign_score;
	g_state.attempt.identity_round = identity_round;
	g_state.attempt.identity_ppm = static_cast<int>(llround(identity * 1000000.0));
	g_state.attempt.target_start = target_start;
	g_state.attempt.cutlength = cutlength;
	std::ostringstream key;
	key << "call-" << g_state.workload.key
		<< "-si" << std::setfill('0') << std::setw(6) << scoreinfo_index
		<< "-ir" << std::setw(2) << identity_round
		<< "-ts" << std::setw(8) << target_start
		<< "-cl" << std::setw(8) << cutlength;
	g_state.attempt.key = key.str();
	return g_state.attempt.key;
}

void finish_scoreinfo_group(int scoreinfo_index,
	const std::string& selected_attempt_key,
	const char* selection_reason) {
	if (!enabled()) return;
	for (size_t i = 0; i < g_state.pending.size(); ++i) {
		AlignmentRecord& record = g_state.pending[i];
		if (record.attempt.scoreinfo_index != scoreinfo_index) continue;
		record.selected = !selected_attempt_key.empty() && record.attempt.key == selected_attempt_key;
		record.selection_reason = record.selected ?
			(selection_reason == NULL ? "selected" : selection_reason) : "not_selected";
	}
}

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
	const std::string& aligned_tts) {
	if (!enabled() || attempt_key.empty()) return;
	AlignmentRecord* target = NULL;
	for (size_t i = 0; i < g_state.pending.size(); ++i) {
		if (g_state.pending[i].attempt.key == attempt_key) {
			if (target != NULL) {
				throw std::runtime_error("duplicate pending oracle attempt key");
			}
			target = &g_state.pending[i];
		}
	}
	if (target == NULL) throw std::runtime_error("emitted row has no pending oracle attempt");
	EmittedRow row;
	row.query_start = query_start;
	row.query_end = query_end;
	row.target_start = target_start;
	row.target_end = target_end;
	row.strand = strand;
	row.reverse = reverse;
	row.rule = rule;
	row.nt = nt;
	row.score = score;
	row.identity = identity;
	row.stability = stability;
	row.aligned_tfo = aligned_tfo;
	row.aligned_tts = aligned_tts;
	row.ungapped_tfo = without_gaps(aligned_tfo);
	row.ungapped_tts = without_gaps(aligned_tts);
	const std::string payload = emitted_row_payload(row);
	row.digest = hex64(fnv1a_bytes(payload.data(), payload.size()));
	target->emitted_rows.push_back(row);
}

void publish_workload_records() {
	if (!enabled()) return;
	for (size_t i = 0; i < g_state.pending.size(); ++i) write_alignment(g_state.pending[i]);
	g_state.pending.clear();
}

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
	int32_t distance_filter) {
	if (!enabled()) return;
	if (!g_state.workload.active) throw std::runtime_error("alignment trace has no workload context");
	if (g_state.alignment_active) throw std::runtime_error("nested SSW oracle alignment");
	g_state.alignment = AlignmentRecord();
	g_state.alignment_active = true;
	g_state.alignment.attempt = g_state.attempt;
	if (!g_state.alignment.attempt.active) {
		g_state.alignment.attempt.active = true;
		g_state.alignment.attempt.scoreinfo_index = -1;
		g_state.alignment.attempt.identity_round = -1;
		std::ostringstream direct;
		direct << "direct-" << g_state.workload.key << "-" << g_state.direct_call_ordinal++;
		g_state.alignment.attempt.key = direct.str();
	}
	g_state.alignment.key = g_state.alignment.attempt.key;
	g_state.alignment.query_digest = digest_bytes(query, query_len);
	g_state.alignment.ref_digest = digest_bytes(ref, ref_len);
	g_state.alignment.query_len = query_len;
	g_state.alignment.ref_len = ref_len;
	g_state.alignment.match_score = match_score;
	g_state.alignment.mismatch_penalty = mismatch_penalty;
	g_state.alignment.gap_open = gap_open;
	g_state.alignment.gap_extend = gap_extend;
	g_state.alignment.mask_len = mask_len;
	g_state.alignment.flag = flag;
	g_state.alignment.score_filter = score_filter;
	g_state.alignment.distance_filter = distance_filter;
	g_state.alignment.status = "running";
}

void record_alignment_dp_pass_u8(const uint8_t* columns,
	int32_t count,
	int ref_dir,
	const char* numeric_path,
	int best_score,
	int best_ref,
	int best_read,
	int second_score,
	int second_ref) {
	if (!enabled() || !g_state.alignment_active) return;
	g_state.alignment.passes.push_back(build_pass(columns, count,
		ref_dir == 0 ? "forward" : "reverse", ref_dir, numeric_path,
		best_score, best_ref, best_read, second_score, second_ref));
}

void record_alignment_dp_pass_u16(const uint16_t* columns,
	int32_t count,
	int ref_dir,
	const char* numeric_path,
	int best_score,
	int best_ref,
	int best_read,
	int second_score,
	int second_ref) {
	if (!enabled() || !g_state.alignment_active) return;
	g_state.alignment.passes.push_back(build_pass(columns, count,
		ref_dir == 0 ? "forward" : "reverse", ref_dir, numeric_path,
		best_score, best_ref, best_read, second_score, second_ref));
}

void set_alignment_final_numeric_path(const char* numeric_path) {
	if (!enabled() || !g_state.alignment_active) return;
	g_state.alignment.final_numeric_path = numeric_path == NULL ? "unknown" : numeric_path;
}

void record_band_iteration(int band_width, int max_score, int target_score) {
	if (!enabled() || !g_state.alignment_active) return;
	BandStep step;
	step.band_width = band_width;
	step.max_score = max_score;
	step.target_score = target_score;
	g_state.alignment.band_history.push_back(step);
}

void finish_alignment(int score1,
	int score2,
	int ref_begin1,
	int ref_end1,
	int read_begin1,
	int read_end1,
	int ref_end2,
	const std::string& cigar,
	int cigar_len) {
	if (!enabled() || !g_state.alignment_active) return;
	AlignmentRecord record = g_state.alignment;
	record.status = "complete";
	record.failure_reason = "none";
	record.score1 = score1;
	record.score2 = score2;
	record.ref_begin1 = ref_begin1;
	record.ref_end1 = ref_end1;
	record.read_begin1 = read_begin1;
	record.read_end1 = read_end1;
	record.ref_end2 = ref_end2;
	record.cigar = cigar;
	record.cigar_len = cigar_len;
	if (record.final_numeric_path.empty()) record.final_numeric_path = "unknown";
	if (record.attempt.scoreinfo_index >= 0) {
		g_state.pending.push_back(record);
	}
	else {
		record.selection_reason = "direct_call";
		write_alignment(record);
	}
	g_state.alignment = AlignmentRecord();
	g_state.alignment_active = false;
	g_state.attempt = Attempt();
}

void abort_alignment(const char* reason) {
	if (!enabled() || !g_state.alignment_active) return;
	AlignmentRecord record = g_state.alignment;
	record.status = "failed";
	record.failure_reason = reason == NULL ? "unknown" : reason;
	record.selection_reason = "alignment_failed";
	if (record.attempt.scoreinfo_index >= 0) g_state.pending.push_back(record);
	else write_alignment(record);
	g_state.alignment = AlignmentRecord();
	g_state.alignment_active = false;
	g_state.attempt = Attempt();
}

}  // namespace fasim_ssw_oracle
