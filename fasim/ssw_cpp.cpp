// ssw_cpp.cpp
// Created by Wan-Ping Lee
// Last revision by Mengyao Zhao on 2017-05-30

#include "ssw_cpp.h"
#include "ssw.h"
#include<algorithm>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <mutex>
#include <set>
#include <sstream>
#include <string>
#include <unordered_map>

namespace {

	static const int8_t kBaseTranslation[128] = {
		4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
		4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
		4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
		4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
		//   A     C            G
		  4, 0, 4, 1,  4, 4, 4, 2,  4, 4, 4, 4,  4, 4, 4, 4,
		  //             T
			4, 4, 4, 4,  3, 0, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4,
			//   a     c            g
			  4, 0, 4, 1,  4, 4, 4, 2,  4, 4, 4, 4,  4, 4, 4, 4,
			  //             t
				4, 4, 4, 4,  3, 0, 4, 4,  4, 4, 4, 4,  4, 4, 4, 4
	};

	void BuildSwScoreMatrix(const uint8_t& match_score,
		const uint8_t& mismatch_penalty,
		int8_t* matrix) {

		// The score matrix looks like
		//                 // A,  C,  G,  T,  N
		//  score_matrix_ = { 2, -2, -2, -2, -2, // A
		//                   -2,  2, -2, -2, -2, // C
		//                   -2, -2,  2, -2, -2, // G
		//                   -2, -2, -2,  2, -2, // T
		//                   -2, -2, -2, -2, -2};// N

		int id = 0;
		for (int i = 0; i < 4; ++i) {
			for (int j = 0; j < 4; ++j) {
				matrix[id] = ((i == j) ? match_score : -mismatch_penalty);//static_cast<int8_t>(
				++id;
			}
			matrix[id] = static_cast<int8_t>(-mismatch_penalty); // For N
			++id;
		}

		for (int i = 0; i < 5; ++i)
			matrix[id++] = static_cast<int8_t>(-mismatch_penalty); // For N

	}

	void ConvertAlignment(const s_align& s_al,
		const int& query_len,
		StripedSmithWaterman::Alignment* al) {
		al->sw_score = s_al.score1;
		al->sw_score_next_best = s_al.score2;
		al->ref_begin = s_al.ref_begin1;
		al->ref_end = s_al.ref_end1;
		al->query_begin = s_al.read_begin1;
		al->query_end = s_al.read_end1;
		al->ref_end_next_best = s_al.ref_end2;

		al->cigar.clear();
		al->cigar_string.clear();

		if (s_al.cigarLen > 0) {
			std::ostringstream cigar_string;
			//2021-09-16 16:38:07: seems start and end is useless.
		//    if (al->query_begin > 0) {
		//      uint32_t cigar = to_cigar_int(al->query_begin, 'S');
		//      al->cigar.push_back(cigar);
		//      cigar_string << al->query_begin << 'S';
		//    }

			for (int i = 0; i < s_al.cigarLen; ++i) {
				//std::cout << cigar_int_to_len(s_al.cigar[i]) << cigar_int_to_op(s_al.cigar[i]);
				al->cigar.push_back(s_al.cigar[i]);
				cigar_string << cigar_int_to_len(s_al.cigar[i]) << cigar_int_to_op(s_al.cigar[i]);
			}
			//td::cout << std::endl;

		//    int end = query_len - al->query_end - 1;
		//    if (end > 0) {
		//      uint32_t cigar = to_cigar_int(end, 'S');
		//      al->cigar.push_back(cigar);
		//      cigar_string << end << 'S';
		//    }

			al->cigar_string = cigar_string.str();
		} // end if
	}

	// @Function:
	//     Calculate the length of the previous cigar operator
	//     and store it in new_cigar and new_cigar_string.
	//     Clean up in_M (false), in_X (false), length_M (0), and length_X(0).
	void CleanPreviousMOperator(
		bool* in_M,
		bool* in_X,
		uint32_t* length_M,
		uint32_t* length_X,
		std::vector<uint32_t>* new_cigar,
		std::ostringstream* new_cigar_string) {
		if (*in_M) {
			uint32_t match = to_cigar_int(*length_M, '=');
			new_cigar->push_back(match);
			(*new_cigar_string) << *length_M << '=';
		}
		else if (*in_X) { //in_X
			uint32_t match = to_cigar_int(*length_X, 'X');
			new_cigar->push_back(match);
			(*new_cigar_string) << *length_X << 'X';
		}

		// Clean up
		*in_M = false;
		*in_X = false;
		*length_M = 0;
		*length_X = 0;
	}

	// @Function:
	//     1. Calculate the number of mismatches.
	//     2. Modify the cigar string:
	//         differentiate matches (M) and mismatches(X).
	// @Return:
	//     The number of mismatches.
	int CalculateNumberMismatch(
		StripedSmithWaterman::Alignment* al,
		int8_t const *ref,
		int8_t const *query,
		const int& query_len) {

		ref += al->ref_begin;
		query += al->query_begin;
		int mismatch_length = 0;

		std::vector<uint32_t> new_cigar;
		std::ostringstream new_cigar_string;

		if (al->query_begin > 0) {
			uint32_t cigar = to_cigar_int(al->query_begin, 'S');
			new_cigar.push_back(cigar);
			new_cigar_string << al->query_begin << 'S';
		}

		bool in_M = false; // the previous is match
		bool in_X = false; // the previous is mismatch
		uint32_t length_M = 0;
		uint32_t length_X = 0;

		for (unsigned int i = 0; i < al->cigar.size(); ++i) {
			char op = cigar_int_to_op(al->cigar[i]);
			uint32_t length = cigar_int_to_len(al->cigar[i]);
			if (op == 'M') {
				for (uint32_t j = 0; j < length; ++j) {
					if (*ref != *query) {
						++mismatch_length;
						if (in_M) { // the previous is match; however the current one is mismatche
							uint32_t match = to_cigar_int(length_M, '=');
							new_cigar.push_back(match);
							new_cigar_string << length_M << '=';
						}
						length_M = 0;
						++length_X;
						in_M = false;
						in_X = true;
					}
					else { // *ref == *query
						if (in_X) { // the previous is mismatch; however the current one is matche
							uint32_t match = to_cigar_int(length_X, 'X');
							new_cigar.push_back(match);
							new_cigar_string << length_X << 'X';
						}
						++length_M;
						length_X = 0;
						in_M = true;
						in_X = false;
					} // end of if (*ref != *query)
					++ref;
					++query;
				}
			}
			else if (op == 'I') {
				query += length;
				mismatch_length += length;
				CleanPreviousMOperator(&in_M, &in_X, &length_M, &length_X, &new_cigar, &new_cigar_string);
				new_cigar.push_back(al->cigar[i]);
				new_cigar_string << length << 'I';
			}
			else if (op == 'D') {
				ref += length;
				mismatch_length += length;
				CleanPreviousMOperator(&in_M, &in_X, &length_M, &length_X, &new_cigar, &new_cigar_string);
				new_cigar.push_back(al->cigar[i]);
				new_cigar_string << length << 'D';
			}
		}

		CleanPreviousMOperator(&in_M, &in_X, &length_M, &length_X, &new_cigar, &new_cigar_string);

		int end = query_len - al->query_end - 1;
		if (end > 0) {
			uint32_t cigar = to_cigar_int(end, 'S');
			new_cigar.push_back(cigar);
			new_cigar_string << end << 'S';
		}

		al->cigar_string.clear();
		al->cigar.clear();
		al->cigar_string = new_cigar_string.str();
		al->cigar = new_cigar;

		return mismatch_length;
	}

	void SetFlag(const StripedSmithWaterman::Filter& filter, uint8_t* flag) {
		if (filter.report_begin_position) *flag |= 0x08;
		if (filter.report_cigar) *flag |= 0x0f;
	}

	// http://www.cplusplus.com/faq/sequences/arrays/sizeof-array/#cpp
	template <typename T, size_t N>
	inline size_t SizeOfArray(const T(&)[N])
	{
		return N;
	}

} // namespace



namespace StripedSmithWaterman {

	namespace {
		typedef std::chrono::steady_clock AlignerTelemetryClock;

		AlignerTelemetryDelta g_alignerTelemetry;
		std::mutex g_alignerTelemetryMutex;

		struct ProfileReuseShadowState {
			ProfileReuseShadowState()
				: enabled(false)
				, buildCalls(0)
				, reusableCalls(0)
				, buildSeconds(0.0)
				, estSavedSeconds(0.0)
				, queryReusableCalls(0)
			{}

			bool enabled;
			long long buildCalls;
			long long reusableCalls;
			double buildSeconds;
			double estSavedSeconds;
			long long queryReusableCalls;
			std::unordered_map<std::string, double> profileFirstBuildSeconds;
			std::set<std::string> queryKeys;
		};

		struct ProfileCacheState {
			ProfileCacheState()
				: requested(false)
				, active(false)
				, validate(false)
				, calls(0)
				, hits(0)
				, misses(0)
				, buildSeconds(0.0)
				, savedSeconds(0.0)
				, validateSeconds(0.0)
				, scoreMismatches(0)
				, endpointMismatches(0)
				, cigarMismatches(0)
				, digestMismatches(0)
				, fallbacks(0)
			{}

			bool requested;
			bool active;
			bool validate;
			long long calls;
			long long hits;
			long long misses;
			double buildSeconds;
			double savedSeconds;
			double validateSeconds;
			long long scoreMismatches;
			long long endpointMismatches;
			long long cigarMismatches;
			long long digestMismatches;
			long long fallbacks;
			std::set<std::string> uniqueKeys;
		};

		struct CachedProfileEntry {
			CachedProfileEntry()
				: queryLen(0)
				, scoreSize(0)
				, profile(NULL)
				, profileBuildSeconds(0.0)
			{}

			~CachedProfileEntry() {
				if (profile != NULL) {
					init_destroy(profile);
				}
			}

			int queryLen;
			int8_t scoreSize;
			std::vector<int8_t> query;
			std::vector<int8_t> scoreMatrix;
			s_profile* profile;
			double profileBuildSeconds;
		};

		ProfileReuseShadowState g_profileReuseShadow;
		std::mutex g_profileReuseShadowMutex;
		ProfileCacheState g_profileCacheState;
		std::mutex g_profileCacheMutex;
		thread_local std::unordered_map<std::string, std::shared_ptr<CachedProfileEntry> > t_profileCache;

		inline double elapsed_seconds(AlignerTelemetryClock::time_point start,
		                              AlignerTelemetryClock::time_point end) {
			return std::chrono::duration<double>(end - start).count();
		}

		void AddAlignerTelemetry(const AlignerTelemetryDelta& delta) {
			std::lock_guard<std::mutex> lock(g_alignerTelemetryMutex);
			g_alignerTelemetry.alignCalls += delta.alignCalls;
			g_alignerTelemetry.queryTranslateSeconds += delta.queryTranslateSeconds;
			g_alignerTelemetry.refTranslateSeconds += delta.refTranslateSeconds;
			g_alignerTelemetry.profileSeconds += delta.profileSeconds;
			g_alignerTelemetry.sswTotalSeconds += delta.sswTotalSeconds;
			g_alignerTelemetry.convertSeconds += delta.convertSeconds;
			g_alignerTelemetry.cleanupSeconds += delta.cleanupSeconds;
			g_alignerTelemetry.nullResults += delta.nullResults;
		}

		bool ProfileReuseShadowEnabledRuntime() {
			static const bool enabled = []() {
				const char* env = std::getenv("FASIM_ALIGN_PROFILE_REUSE_SHADOW");
				return env != NULL && env[0] != '\0' && env[0] != '0';
			}();
			return enabled;
		}

		bool ProfileCacheEnabledRuntime() {
			static const bool enabled = []() {
				const char* env = std::getenv("FASIM_ALIGN_PROFILE_CACHE");
				return env != NULL && env[0] != '\0' && env[0] != '0';
			}();
			return enabled;
		}

		bool ProfileCacheValidateRuntime() {
			static const bool enabled = []() {
				const char* env = std::getenv("FASIM_ALIGN_PROFILE_CACHE_VALIDATE");
				return env != NULL && env[0] != '\0' && env[0] != '0';
			}();
			return enabled;
		}

		uint64_t Fnv1a64(const void* data, size_t size) {
			const unsigned char* bytes = static_cast<const unsigned char*>(data);
			uint64_t hash = 1469598103934665603ULL;
			for (size_t i = 0; i < size; ++i) {
				hash ^= static_cast<uint64_t>(bytes[i]);
				hash *= 1099511628211ULL;
			}
			return hash;
		}

		void AppendKeyPart(std::ostringstream& key, const char* name, uint64_t value) {
			key << name << '=' << value << ';';
		}

		std::string BuildQueryReuseKey(const int8_t* translatedQuery, int queryLen) {
			std::ostringstream key;
			AppendKeyPart(key, "query_len", static_cast<uint64_t>(queryLen));
			AppendKeyPart(key, "query_hash",
			              Fnv1a64(translatedQuery, static_cast<size_t>(queryLen)));
			return key.str();
		}

		std::string BuildProfileReuseKey(const int8_t* translatedQuery,
		                                 int queryLen,
		                                 const int8_t* scoreMatrix,
		                                 int scoreMatrixSize,
		                                 uint8_t gapOpeningPenalty,
		                                 uint8_t gapExtendingPenalty,
		                                 int8_t scoreSize) {
			std::ostringstream key;
			key << BuildQueryReuseKey(translatedQuery, queryLen);
			AppendKeyPart(key, "matrix_size", static_cast<uint64_t>(scoreMatrixSize));
			AppendKeyPart(key, "matrix_hash",
			              Fnv1a64(scoreMatrix,
			                     static_cast<size_t>(scoreMatrixSize) *
			                         static_cast<size_t>(scoreMatrixSize) *
			                         sizeof(int8_t)));
			AppendKeyPart(key, "gap_open", static_cast<uint64_t>(gapOpeningPenalty));
			AppendKeyPart(key, "gap_extend", static_cast<uint64_t>(gapExtendingPenalty));
			AppendKeyPart(key, "score_size", static_cast<uint64_t>(scoreSize));
			return key.str();
		}

		void RecordProfileReuseShadow(const std::string& profileKey,
		                              const std::string& queryKey,
		                              double buildSeconds) {
			std::lock_guard<std::mutex> lock(g_profileReuseShadowMutex);
			g_profileReuseShadow.enabled = true;
			g_profileReuseShadow.buildCalls += 1;
			g_profileReuseShadow.buildSeconds += buildSeconds;
			std::unordered_map<std::string, double>::iterator existing =
				g_profileReuseShadow.profileFirstBuildSeconds.find(profileKey);
			if (existing == g_profileReuseShadow.profileFirstBuildSeconds.end()) {
				g_profileReuseShadow.profileFirstBuildSeconds[profileKey] = buildSeconds;
			}
			else {
				g_profileReuseShadow.reusableCalls += 1;
				g_profileReuseShadow.estSavedSeconds += buildSeconds;
			}

			std::pair<std::set<std::string>::iterator, bool> inserted =
				g_profileReuseShadow.queryKeys.insert(queryKey);
			if (!inserted.second) {
				g_profileReuseShadow.queryReusableCalls += 1;
			}
		}

		s_profile* BuildSswProfile(const int8_t* translatedQuery,
		                           int queryLen,
		                           const int8_t* scoreMatrix,
		                           int scoreMatrixSize,
		                           int8_t scoreSize,
		                           double* buildSeconds) {
			AlignerTelemetryClock::time_point start = AlignerTelemetryClock::now();
			s_profile* profile = ssw_init(translatedQuery,
			                              queryLen,
			                              scoreMatrix,
			                              scoreMatrixSize,
			                              scoreSize);
			*buildSeconds = elapsed_seconds(start, AlignerTelemetryClock::now());
			return profile;
		}

		std::shared_ptr<CachedProfileEntry> GetCachedProfile(
			const std::string& profileKey,
			const int8_t* translatedQuery,
			int queryLen,
			const int8_t* scoreMatrix,
			int scoreMatrixSize,
			int8_t scoreSize,
			bool* cacheHit,
			double* buildSeconds,
			double* savedSeconds) {
			std::unordered_map<std::string, std::shared_ptr<CachedProfileEntry> >::iterator it =
				t_profileCache.find(profileKey);
			if (it != t_profileCache.end()) {
				*cacheHit = true;
				*buildSeconds = 0.0;
				*savedSeconds = it->second->profileBuildSeconds;
				return it->second;
			}

			*cacheHit = false;
			*savedSeconds = 0.0;
			std::shared_ptr<CachedProfileEntry> entry(new CachedProfileEntry());
			entry->queryLen = queryLen;
			entry->scoreSize = scoreSize;
			entry->query.assign(translatedQuery, translatedQuery + queryLen);
			entry->scoreMatrix.assign(
				scoreMatrix,
				scoreMatrix +
					static_cast<size_t>(scoreMatrixSize) *
					static_cast<size_t>(scoreMatrixSize));
			entry->profile = BuildSswProfile(entry->query.data(),
			                                 queryLen,
			                                 entry->scoreMatrix.data(),
			                                 scoreMatrixSize,
			                                 scoreSize,
			                                 buildSeconds);
			entry->profileBuildSeconds = *buildSeconds;
			t_profileCache[profileKey] = entry;
			return entry;
		}

		bool AlignmentSameScore(const Alignment& a, const Alignment& b) {
			return a.sw_score == b.sw_score &&
			       a.sw_score_next_best == b.sw_score_next_best;
		}

		bool AlignmentSameEndpoint(const Alignment& a, const Alignment& b) {
			return a.ref_begin == b.ref_begin &&
			       a.ref_end == b.ref_end &&
			       a.query_begin == b.query_begin &&
			       a.query_end == b.query_end &&
			       a.ref_end_next_best == b.ref_end_next_best;
		}

		bool AlignmentSameCigar(const Alignment& a, const Alignment& b) {
			return a.cigar_string == b.cigar_string && a.cigar == b.cigar;
		}

		bool AlignmentSameDigest(const Alignment& a, const Alignment& b) {
			return AlignmentSameScore(a, b) &&
			       AlignmentSameEndpoint(a, b) &&
			       AlignmentSameCigar(a, b) &&
			       a.mismatches == b.mismatches;
		}

		void RecordProfileCacheCall(bool hit,
		                            const std::string& profileKey,
		                            double buildSeconds,
		                            double savedSeconds) {
			std::lock_guard<std::mutex> lock(g_profileCacheMutex);
			g_profileCacheState.requested = ProfileCacheEnabledRuntime();
			g_profileCacheState.active = g_profileCacheState.active || ProfileCacheEnabledRuntime();
			g_profileCacheState.validate =
				g_profileCacheState.validate ||
				(ProfileCacheEnabledRuntime() && ProfileCacheValidateRuntime());
			g_profileCacheState.calls += 1;
			if (hit) {
				g_profileCacheState.hits += 1;
				g_profileCacheState.savedSeconds += savedSeconds;
			}
			else {
				g_profileCacheState.misses += 1;
				g_profileCacheState.buildSeconds += buildSeconds;
			}
			g_profileCacheState.uniqueKeys.insert(profileKey);
		}

		void RecordProfileCacheValidate(double seconds,
		                                bool scoreMismatch,
		                                bool endpointMismatch,
		                                bool cigarMismatch,
		                                bool digestMismatch,
		                                bool fallback) {
			std::lock_guard<std::mutex> lock(g_profileCacheMutex);
			g_profileCacheState.validate =
				g_profileCacheState.validate ||
				(ProfileCacheEnabledRuntime() && ProfileCacheValidateRuntime());
			g_profileCacheState.validateSeconds += seconds;
			g_profileCacheState.scoreMismatches += scoreMismatch ? 1 : 0;
			g_profileCacheState.endpointMismatches += endpointMismatch ? 1 : 0;
			g_profileCacheState.cigarMismatches += cigarMismatch ? 1 : 0;
			g_profileCacheState.digestMismatches += digestMismatch ? 1 : 0;
			g_profileCacheState.fallbacks += fallback ? 1 : 0;
		}
	}

	void ResetAlignerTelemetry() {
		{
			std::lock_guard<std::mutex> lock(g_alignerTelemetryMutex);
			g_alignerTelemetry = AlignerTelemetryDelta();
		}
		{
			std::lock_guard<std::mutex> lock(g_profileReuseShadowMutex);
			g_profileReuseShadow = ProfileReuseShadowState();
			g_profileReuseShadow.enabled = ProfileReuseShadowEnabledRuntime();
		}
		{
			std::lock_guard<std::mutex> lock(g_profileCacheMutex);
			g_profileCacheState = ProfileCacheState();
			g_profileCacheState.requested = ProfileCacheEnabledRuntime();
			g_profileCacheState.active = ProfileCacheEnabledRuntime();
			g_profileCacheState.validate =
				ProfileCacheEnabledRuntime() && ProfileCacheValidateRuntime();
		}
		t_profileCache.clear();
		ssw_reset_telemetry();
	}

	AlignerTelemetryDelta SnapshotAlignerTelemetry() {
		AlignerTelemetryDelta snapshot;
		{
			std::lock_guard<std::mutex> lock(g_alignerTelemetryMutex);
			snapshot = g_alignerTelemetry;
		}
		const ssw_telemetry_delta sswSnapshot = ssw_snapshot_telemetry();
		snapshot.forwardScoreEndSeconds = sswSnapshot.forward_score_end_seconds;
		snapshot.reverseStartSeconds = sswSnapshot.reverse_start_seconds;
		snapshot.tracebackSeconds = sswSnapshot.traceback_seconds;
		snapshot.forwardScoreGpuShadowEnabled =
			sswSnapshot.forward_score_gpu_shadow_enabled != 0;
		snapshot.forwardScoreGpuRequests = sswSnapshot.forward_score_gpu_requests;
		snapshot.forwardScoreGpuCells = sswSnapshot.forward_score_gpu_cells;
		snapshot.forwardScoreGpuCpuSeconds = sswSnapshot.forward_score_gpu_cpu_seconds;
		snapshot.forwardScoreGpuPackSeconds = sswSnapshot.forward_score_gpu_pack_seconds;
		snapshot.forwardScoreGpuH2DSeconds = sswSnapshot.forward_score_gpu_h2d_seconds;
		snapshot.forwardScoreGpuKernelSeconds = sswSnapshot.forward_score_gpu_kernel_seconds;
		snapshot.forwardScoreGpuD2HSeconds = sswSnapshot.forward_score_gpu_d2h_seconds;
		snapshot.forwardScoreGpuUnpackSeconds = sswSnapshot.forward_score_gpu_unpack_seconds;
		snapshot.forwardScoreGpuTotalSeconds = sswSnapshot.forward_score_gpu_total_seconds;
		snapshot.forwardScoreGpuScoreMismatches =
			sswSnapshot.forward_score_gpu_score_mismatches;
		snapshot.forwardScoreGpuEndpointMismatches =
			sswSnapshot.forward_score_gpu_endpoint_mismatches;
		snapshot.forwardScoreGpuUnsupportedRequests =
			sswSnapshot.forward_score_gpu_unsupported_requests;
		snapshot.forwardScoreBatchShadowEnabled =
			sswSnapshot.forward_score_batch_shadow_enabled != 0;
		snapshot.forwardScoreBatchRequests = sswSnapshot.forward_score_batch_requests;
		snapshot.forwardScoreBatchCells = sswSnapshot.forward_score_batch_cells;
		snapshot.forwardScoreBatchPackSeconds =
			sswSnapshot.forward_score_batch_pack_seconds;
		snapshot.forwardScoreBatchH2DSeconds =
			sswSnapshot.forward_score_batch_h2d_seconds;
		snapshot.forwardScoreBatchKernelSeconds =
			sswSnapshot.forward_score_batch_kernel_seconds;
		snapshot.forwardScoreBatchD2HSeconds =
			sswSnapshot.forward_score_batch_d2h_seconds;
		snapshot.forwardScoreBatchUnpackSeconds =
			sswSnapshot.forward_score_batch_unpack_seconds;
		snapshot.forwardScoreBatchTotalSeconds =
			sswSnapshot.forward_score_batch_total_seconds;
		snapshot.forwardScoreBatchCpuReferenceSeconds =
			sswSnapshot.forward_score_batch_cpu_reference_seconds;
		snapshot.forwardScoreBatchScoreMismatches =
			sswSnapshot.forward_score_batch_score_mismatches;
		snapshot.forwardScoreBatchEndpointMismatches =
			sswSnapshot.forward_score_batch_endpoint_mismatches;
		snapshot.forwardScoreBatchUnsupportedRequests =
			sswSnapshot.forward_score_batch_unsupported_requests;
		snapshot.scoreBridgeShadowEnabled =
			sswSnapshot.score_bridge_shadow_enabled != 0;
		snapshot.scoreBridgeRequests = sswSnapshot.score_bridge_requests;
		snapshot.scoreBridgeCells = sswSnapshot.score_bridge_cells;
		snapshot.scoreBridgeGroups = sswSnapshot.score_bridge_groups;
		snapshot.scoreBridgeDescriptorCount = sswSnapshot.score_bridge_descriptor_count;
		snapshot.scoreBridgeDescriptorBytes = sswSnapshot.score_bridge_descriptor_bytes;
		snapshot.scoreBridgeQueryBufferBytes = sswSnapshot.score_bridge_query_buffer_bytes;
		snapshot.scoreBridgeTargetBufferBytes = sswSnapshot.score_bridge_target_buffer_bytes;
		snapshot.scoreBridgePackSeconds = sswSnapshot.score_bridge_pack_seconds;
		snapshot.scoreBridgeH2DSeconds = sswSnapshot.score_bridge_h2d_seconds;
		snapshot.scoreBridgeKernelSeconds = sswSnapshot.score_bridge_kernel_seconds;
		snapshot.scoreBridgeD2HSeconds = sswSnapshot.score_bridge_d2h_seconds;
		snapshot.scoreBridgeUnpackSeconds = sswSnapshot.score_bridge_unpack_seconds;
		snapshot.scoreBridgeTotalSeconds = sswSnapshot.score_bridge_total_seconds;
		snapshot.scoreBridgeCpuReferenceSeconds =
			sswSnapshot.score_bridge_cpu_reference_seconds;
		snapshot.scoreBridgeScoreMismatches = sswSnapshot.score_bridge_score_mismatches;
		snapshot.scoreBridgeEndpointMismatches =
			sswSnapshot.score_bridge_endpoint_mismatches;
		snapshot.scoreBridgeUnsupportedRequests =
			sswSnapshot.score_bridge_unsupported_requests;
		snapshot.byteForwardCalls = sswSnapshot.byte_forward_calls;
		snapshot.wordForwardCalls = sswSnapshot.word_forward_calls;
		snapshot.reverseCalls = sswSnapshot.reverse_calls;
		snapshot.tracebackCalls = sswSnapshot.traceback_calls;
		{
			std::lock_guard<std::mutex> lock(g_profileReuseShadowMutex);
			snapshot.profileReuseShadowEnabled = g_profileReuseShadow.enabled;
			snapshot.profileBuildCalls = g_profileReuseShadow.buildCalls;
			snapshot.profileUniqueKeys =
				static_cast<long long>(g_profileReuseShadow.profileFirstBuildSeconds.size());
			snapshot.profileReusableCalls = g_profileReuseShadow.reusableCalls;
			snapshot.profileBuildSeconds = g_profileReuseShadow.buildSeconds;
			snapshot.profileEstSavedSeconds = g_profileReuseShadow.estSavedSeconds;
			snapshot.queryUniqueKeys =
				static_cast<long long>(g_profileReuseShadow.queryKeys.size());
			snapshot.queryReusableCalls = g_profileReuseShadow.queryReusableCalls;
		}
		{
			std::lock_guard<std::mutex> lock(g_profileCacheMutex);
			snapshot.profileCacheRequested = g_profileCacheState.requested;
			snapshot.profileCacheActive = g_profileCacheState.active;
			snapshot.profileCacheValidate = g_profileCacheState.validate;
			snapshot.profileCacheCalls = g_profileCacheState.calls;
			snapshot.profileCacheHits = g_profileCacheState.hits;
			snapshot.profileCacheMisses = g_profileCacheState.misses;
			snapshot.profileCacheUniqueKeys =
				static_cast<long long>(g_profileCacheState.uniqueKeys.size());
			snapshot.profileCacheBuildSeconds = g_profileCacheState.buildSeconds;
			snapshot.profileCacheSavedSeconds = g_profileCacheState.savedSeconds;
			snapshot.profileCacheValidateSeconds = g_profileCacheState.validateSeconds;
			snapshot.profileCacheScoreMismatches = g_profileCacheState.scoreMismatches;
			snapshot.profileCacheEndpointMismatches = g_profileCacheState.endpointMismatches;
			snapshot.profileCacheCigarMismatches = g_profileCacheState.cigarMismatches;
			snapshot.profileCacheDigestMismatches = g_profileCacheState.digestMismatches;
			snapshot.profileCacheFallbacks = g_profileCacheState.fallbacks;
		}
		return snapshot;
	}

	Aligner::Aligner(void)
		: score_matrix_(NULL)
		, score_matrix_size_(5)
		, translation_matrix_(NULL)
		, match_score_(5)
		, mismatch_penalty_(4)
		, gap_opening_penalty_(16)
		, gap_extending_penalty_(4)
		, translated_reference_(NULL)
		, reference_length_(0)
	{
		BuildDefaultMatrix();
	}

	Aligner::Aligner(
		const uint8_t& match_score,
		const uint8_t& mismatch_penalty,
		const uint8_t& gap_opening_penalty,
		const uint8_t& gap_extending_penalty)

		: score_matrix_(NULL)
		, score_matrix_size_(5)
		, translation_matrix_(NULL)
		, match_score_(match_score)
		, mismatch_penalty_(mismatch_penalty)
		, gap_opening_penalty_(gap_opening_penalty)
		, gap_extending_penalty_(gap_extending_penalty)
		, translated_reference_(NULL)
		, reference_length_(0)
	{
		BuildDefaultMatrix();
	}

	Aligner::Aligner(const int8_t* score_matrix,
		const int&    score_matrix_size,
		const int8_t* translation_matrix,
		const int&    translation_matrix_size)

		: score_matrix_(NULL)
		, score_matrix_size_(score_matrix_size)
		, translation_matrix_(NULL)
		, match_score_(2)
		, mismatch_penalty_(2)
		, gap_opening_penalty_(3)
		, gap_extending_penalty_(1)
		, translated_reference_(NULL)
		, reference_length_(0)
	{
		score_matrix_ = new int8_t[score_matrix_size_ * score_matrix_size_];
		memcpy(score_matrix_, score_matrix, sizeof(int8_t) * score_matrix_size_ * score_matrix_size_);
		translation_matrix_ = new int8_t[translation_matrix_size];
		memcpy(translation_matrix_, translation_matrix, sizeof(int8_t) * translation_matrix_size);
	}


	Aligner::~Aligner(void) {
		Clear();
	}

	int Aligner::SetReferenceSequence(const char* seq, const int& length) {

		int len = 0;
		if (translation_matrix_) {
			// calculate the valid length
			//int calculated_ref_length = static_cast<int>(strlen(seq));
			//int valid_length = (calculated_ref_length > length)
			//                   ? length : calculated_ref_length;
			int valid_length = length;
			// delete the current buffer
			CleanReferenceSequence();
			// allocate a new buffer
			translated_reference_ = new int8_t[valid_length];

			len = TranslateBase(seq, valid_length, translated_reference_);
		}
		else {
			// nothing
		}

		reference_length_ = len;
		return len;


	}

	int Aligner::TranslateBase(const char* bases, const int& length,
		int8_t* translated) const {

		const char* ptr = bases;
		int len = 0;
		for (int i = 0; i < length; ++i) {
			translated[i] = translation_matrix_[(int8_t)*ptr];
			++ptr;
			++len;
		}

		return len;
	}


	bool Aligner::Align(const char* query, const Filter& filter,
		Alignment* alignment, const int32_t maskLen) const
	{
		if (!translation_matrix_) return false;
		if (reference_length_ == 0) return false;

		int query_len = strlen(query);
		if (query_len == 0) return false;
		AlignerTelemetryDelta telemetry;
		telemetry.alignCalls += 1;
		int8_t* translated_query = new int8_t[query_len];
		AlignerTelemetryClock::time_point stageStart = AlignerTelemetryClock::now();
		TranslateBase(query, query_len, translated_query);
		telemetry.queryTranslateSeconds += elapsed_seconds(stageStart, AlignerTelemetryClock::now());

		const int8_t score_size = 2;
		const std::string profileKey =
			BuildProfileReuseKey(translated_query,
			                     query_len,
			                     score_matrix_,
			                     score_matrix_size_,
			                     gap_opening_penalty_,
			                     gap_extending_penalty_,
			                     score_size);
		const std::string queryKey = BuildQueryReuseKey(translated_query, query_len);
		s_profile* profile = NULL;
		s_profile* legacyProfileForValidate = NULL;
		std::shared_ptr<CachedProfileEntry> cachedProfile;
		bool cacheHit = false;
		double profileBuildSeconds = 0.0;
		double profileSavedSeconds = 0.0;
		const bool profileCacheEnabled = ProfileCacheEnabledRuntime();
		const bool profileCacheValidate = profileCacheEnabled && ProfileCacheValidateRuntime();
		if (profileCacheEnabled) {
			cachedProfile = GetCachedProfile(profileKey,
			                                translated_query,
			                                query_len,
			                                score_matrix_,
			                                score_matrix_size_,
			                                score_size,
			                                &cacheHit,
			                                &profileBuildSeconds,
			                                &profileSavedSeconds);
			profile = cachedProfile->profile;
			RecordProfileCacheCall(cacheHit, profileKey, profileBuildSeconds, profileSavedSeconds);
		}
		else {
			profile = BuildSswProfile(translated_query,
			                          query_len,
			                          score_matrix_,
			                          score_matrix_size_,
			                          score_size,
			                          &profileBuildSeconds);
		}
		telemetry.profileSeconds += profileBuildSeconds;
		if (ProfileReuseShadowEnabledRuntime()) {
			RecordProfileReuseShadow(profileKey, queryKey, profileBuildSeconds);
		}

		uint8_t flag = 0;
		SetFlag(filter, &flag);
		stageStart = AlignerTelemetryClock::now();
		s_align* s_al = ssw_align(profile, translated_reference_, reference_length_,
			static_cast<int>(gap_opening_penalty_),
			static_cast<int>(gap_extending_penalty_),
			flag, filter.score_filter, filter.distance_filter, maskLen);
		telemetry.sswTotalSeconds += elapsed_seconds(stageStart, AlignerTelemetryClock::now());

		alignment->Clear();
		Alignment legacyAlignment;
		s_align* legacySAl = NULL;
		bool useLegacyFallback = false;
		if (s_al != NULL) {
			stageStart = AlignerTelemetryClock::now();
			ConvertAlignment(*s_al, query_len, alignment);
			alignment->mismatches = CalculateNumberMismatch(&*alignment, translated_reference_, translated_query, query_len);
			telemetry.convertSeconds += elapsed_seconds(stageStart, AlignerTelemetryClock::now());
		}
		else {
			telemetry.nullResults += 1;
			alignment->sw_score = 0;
		}

		if (profileCacheValidate) {
			AlignerTelemetryClock::time_point validateStart = AlignerTelemetryClock::now();
			double legacyBuildSeconds = 0.0;
			legacyProfileForValidate = BuildSswProfile(translated_query,
			                                           query_len,
			                                           score_matrix_,
			                                           score_matrix_size_,
			                                           score_size,
			                                           &legacyBuildSeconds);
			legacySAl = ssw_align(legacyProfileForValidate,
			                      translated_reference_,
			                      reference_length_,
			                      static_cast<int>(gap_opening_penalty_),
			                      static_cast<int>(gap_extending_penalty_),
			                      flag,
			                      filter.score_filter,
			                      filter.distance_filter,
			                      maskLen);
			legacyAlignment.Clear();
			if (legacySAl != NULL) {
				ConvertAlignment(*legacySAl, query_len, &legacyAlignment);
				legacyAlignment.mismatches =
					CalculateNumberMismatch(&legacyAlignment,
					                        translated_reference_,
					                        translated_query,
					                        query_len);
			}
			else {
				legacyAlignment.sw_score = 0;
			}
			const bool scoreMismatch = !AlignmentSameScore(*alignment, legacyAlignment);
			const bool endpointMismatch = !AlignmentSameEndpoint(*alignment, legacyAlignment);
			const bool cigarMismatch = !AlignmentSameCigar(*alignment, legacyAlignment);
			const bool digestMismatch = !AlignmentSameDigest(*alignment, legacyAlignment);
			useLegacyFallback =
				scoreMismatch || endpointMismatch || cigarMismatch || digestMismatch;
			if (useLegacyFallback) {
				*alignment = legacyAlignment;
			}
			RecordProfileCacheValidate(
				elapsed_seconds(validateStart, AlignerTelemetryClock::now()),
				scoreMismatch,
				endpointMismatch,
				cigarMismatch,
				digestMismatch,
				useLegacyFallback);
		}


		// Free memory
		stageStart = AlignerTelemetryClock::now();
		delete[] translated_query;
		if (s_al != NULL) align_destroy(s_al);
		if (legacySAl != NULL) align_destroy(legacySAl);
		if (legacyProfileForValidate != NULL) init_destroy(legacyProfileForValidate);
		if (!profileCacheEnabled) init_destroy(profile);
		telemetry.cleanupSeconds += elapsed_seconds(stageStart, AlignerTelemetryClock::now());
		AddAlignerTelemetry(telemetry);

		return true;
	}


	bool iscontinue(struct scoreInfo bScoreInfo, struct scoreInfo cScoreInfo) {
		if (abs(bScoreInfo.position - cScoreInfo.position) > 0&& abs(bScoreInfo.position - cScoreInfo.position) <5 )
			return true;
		else
			return false;
	}

	bool isMaxvalue(struct scoreInfo aScoreInfo, struct scoreInfo bScoreInfo) {
		if ((bScoreInfo.score - aScoreInfo.score) >= 0)
			return true;
		else
			return false;
	}

	bool Aligner::preAlign(const char* query, const char* ref, const int& ref_len,
		const Filter& filter, Alignment* alignment, const int32_t maskLen,
		int threshold, std::vector<struct scoreInfo> &finalScoreInfo,int match,int mismatch) const
	{
		if (!translation_matrix_) return false;

		int query_len = strlen(query);
		if (query_len == 0) return false;
		int8_t* translated_query = new int8_t[query_len];
		TranslateBase(query, query_len, translated_query);

		// calculate the valid length
		int valid_ref_len = ref_len;
		int8_t* translated_ref = new int8_t[valid_ref_len];
		TranslateBase(ref, valid_ref_len, translated_ref);


		const int8_t score_size = 2;
		s_profile* profile = ssw_init(translated_query, query_len, score_matrix_,
			score_matrix_size_, score_size);

		uint8_t flag = 0;
		SetFlag(filter, &flag);
		int *scoreMatrix;
		scoreMatrix = ssw_pre_align(profile, translated_ref, valid_ref_len,
			static_cast<int>(gap_opening_penalty_),
			static_cast<int>(gap_extending_penalty_),
			flag, filter.score_filter, filter.distance_filter, maskLen, threshold);

		//alignment->Clear();
		//ConvertAlignment(*s_al, query_len, alignment);
		//2021-09-16 22:38:00: to get original cigar string.
		//alignment->mismatches = CalculateNumberMismatch(&*alignment, translated_ref, translated_query, query_len);

		// Free memory
		delete[] translated_query;
		delete[] translated_ref;
		//align_destroy(s_al);
		init_destroy(profile);
		std::vector<int> tmpScorepos;

		//return true;
		// begin to process scoreMatrix, and generate scoreInfo.
		int i = 0;
		int outputNum = -1;
		int start = 0, num = 0, numa = 0, maxScore = 0, maxIndex = 0;
		std::vector<int> scoreVector;
		for (i = 0; i < ref_len; i++)
		{
			scoreVector.push_back(scoreMatrix[i]);
		}
		// free scoreMatrix.
		free(scoreMatrix);
		// begin to get information.
		std::vector<struct scoreInfo> tmpScoreInfo;

		struct scoreInfo aScoreInfo;
		int maxscore = 0;
		for (i = 0; i < scoreVector.size(); i++)
		{
		    //fprintf(stderr, "%d is score %d is position\n", scoreVector[i], i);
			if (scoreVector[i] > threshold)
			{
				aScoreInfo = scoreInfo(scoreVector[i], i);
				tmpScoreInfo.push_back(aScoreInfo);
//                std::cout<<scoreVector[i]<<" sc---ore,pos: "<<i<<std::endl;
			}
			if (scoreVector[i] > maxscore)
				maxscore = scoreVector[i];
		}
		//cout<< threshold <<" is threshold "<< maxscore << " is maxscore "<<endl;
		//fprintf(stderr, "%d is threshold %d is maxscore\n", threshold, maxscore);
			// DEBUG: check tmpScoreInfo.
			//for(i = 0; i < tmpScoreInfo.size(); i++)
			//{
			//  fprintf(stderr, "%d is score %d is ref\n", tmpScoreInfo[i].score,
			//    tmpScoreInfo[i].position);
			//}
			// then begin to get all information.
			std::vector<int> tmpScore;
			//std::vector<struct scoreInfo> finalScoreInfo;
			struct scoreInfo bScoreInfo;
			while (true)
			{
				numa = num + 1;
				if (numa > tmpScoreInfo.size()) break;
				if (num == (tmpScoreInfo.size() - 1)) {
					bScoreInfo = scoreInfo(tmpScoreInfo[tmpScoreInfo.size() - 1].score,
						tmpScoreInfo[tmpScoreInfo.size() - 1].position);
					finalScoreInfo.push_back(bScoreInfo);
//					std::cout<<tmpScoreInfo[tmpScoreInfo.size() - 1].score<<"-------"<<tmpScoreInfo[tmpScoreInfo.size() - 1].position<<std::endl;
					break;
				}
				if ((tmpScoreInfo[numa].position - tmpScoreInfo[num].position < 5)
					&& (tmpScoreInfo[numa].position - tmpScoreInfo[num].position > 0))
				{
					start = num;
					std::vector<int>().swap(tmpScore);
					while ((tmpScoreInfo[numa].position - tmpScoreInfo[num].position < 5)
						&& (tmpScoreInfo[numa].position - tmpScoreInfo[num].position > 0))
					{
						tmpScore.push_back(tmpScoreInfo[num].score);
						num = num + 1;
						numa = num + 1;
						if (numa > tmpScoreInfo.size() - 1)
						{
							break;
						}
					}
					tmpScore.push_back(tmpScoreInfo[num].score);
					num += 1;
					maxScore = 0;
					if (tmpScore.size() > 0)
					{
						// need to find maxScore.
						//if (tmpScore.begin() > tmpScore.end())
							//maxScore = *(tmpScore.begin());
						//else
							//maxScore = *(tmpScore.end());
							maxScore = *std::max_element(tmpScore.begin(), tmpScore.end());
					// and find maxScore's index.
					std::vector<int>::iterator itr = std::find(tmpScore.begin(),
						tmpScore.end(), maxScore);
					maxIndex = std::distance(tmpScore.begin(), itr);
					// is this OK???
					if (num != outputNum)
					{
						bScoreInfo = scoreInfo(tmpScoreInfo[start + maxIndex].score,
							tmpScoreInfo[start + maxIndex].position);
						finalScoreInfo.push_back(bScoreInfo);

					}
					outputNum = start + maxIndex;
//						int tmpindex = 0;
//                        while(tmpindex<tmpScore.size()){
//						    // and find maxScore's index.
//						    if(tmpindex==0){
//						        if(((tmpScore[tmpindex+1]-tmpScore[tmpindex]>=0)&&tmpScore[tmpindex+1]-tmpScore[tmpindex]!=match)||tmpScore[tmpindex+1]-tmpScore[tmpindex]<=0){
//						            bScoreInfo = scoreInfo(tmpScoreInfo[tmpindex+start].score,tmpScoreInfo[tmpindex+start].position);
//							        finalScoreInfo.push_back(bScoreInfo);
////							        std::cout<<tmpScoreInfo[tmpindex+start].score<<"----1---"<<tmpScoreInfo[tmpindex+start].position<<std::endl;
//							        tmpindex += 1;
//						        }
//						        else{
////						        	std::cout<<tmpScoreInfo[tmpindex+start].score<<"----1--error----"<<tmpScoreInfo[tmpindex+start].position<<std::endl;
//						            tmpindex += 1;
//						        }
//						    }
//						    else if(tmpindex == tmpScore.size()-1){
//						        	if(tmpScore[tmpindex]-tmpScore[tmpindex-1]>=0||((tmpScore[tmpindex]-tmpScore[tmpindex-1]<=0)&&tmpScore[tmpindex]-tmpScore[tmpindex-1]!=mismatch)){
//						                bScoreInfo = scoreInfo(tmpScoreInfo[tmpindex+start].score,tmpScoreInfo[tmpindex+start].position);
//							            finalScoreInfo.push_back(bScoreInfo);
////							            std::cout<<tmpScoreInfo[tmpindex+start].score<<"---2----"<<tmpScoreInfo[tmpindex+start].position<<std::endl;
//							            tmpindex += 1;
//						        }
//						        else{
////						        	std::cout<<tmpScoreInfo[tmpindex+start].score<<"---2-error---"<<tmpScoreInfo[tmpindex+start].position<<std::endl;
//						            tmpindex += 1;
//						        }
//						    }
//						    else{
//						        if(tmpScore[tmpindex+1]-tmpScore[tmpindex-1]==2*match||tmpScore[tmpindex]-tmpScore[tmpindex-1]==mismatch){
////						            std::cout<<tmpScore[tmpindex-1]<<"---3----"<<tmpScore[tmpindex]<<"---3----"<<tmpScore[tmpindex+1]<<std::endl;
////						            std::cout<<tmpScoreInfo[tmpindex+start].score<<"---3--error--"<<tmpScoreInfo[tmpindex+start].position<<std::endl;
//						            tmpindex += 1;
//						        }
//						        else{
//						                bScoreInfo = scoreInfo(tmpScoreInfo[tmpindex+start].score,tmpScoreInfo[tmpindex+start].position);
//							            finalScoreInfo.push_back(bScoreInfo);
////							            std::cout<<tmpScoreInfo[tmpindex+start].score<<"---3----"<<tmpScoreInfo[tmpindex+start].position<<std::endl;
//							            tmpindex += 1;
//						        }
//						    }
//                        }

					} // if(tmpScore.size)
				} // if((tmpScoreInfo[numa]))
				else
				{
                    bScoreInfo = scoreInfo(tmpScoreInfo[num].score,tmpScoreInfo[num].position);
                    finalScoreInfo.push_back(bScoreInfo);
//                    std::cout<<tmpScoreInfo[num].score<<"---4----"<<tmpScoreInfo[num].position<<std::endl;
					num = num + 1;
				}
			} // while TRUE.
		// always add the last line to finalScoreInfo.
		//bScoreInfo = scoreInfo(tmpScoreInfo[tmpScoreInfo.size() - 1].score,
			//tmpScoreInfo[tmpScoreInfo.size() - 1].position);
		//finalScoreInfo.push_back(bScoreInfo);

		return true;
	}

	//int main()
	//{
	//    std::vector<int> v = { 7, 3, 6, 2, 6 };
	//    int key = 6;
	// 
	//    std::vector<int>::iterator itr = std::find(v.begin(), v.end(), key);
	// 
	//    if (itr != v.cend()) {
	//        std::cout << "Element present at index " << std::distance(v.begin(), itr);
	//    }
	//    else {
	//        std::cout << "Element not found";
	//    }
	// 
	//    return 0;
	//}


	bool Aligner::Align(const char* query, const char* ref, const int& ref_len,
		const Filter& filter, Alignment* alignment, const int32_t maskLen) const
	{
		if (!translation_matrix_) return false;

		int query_len = strlen(query);
		if (query_len == 0) return false;
		AlignerTelemetryDelta telemetry;
		telemetry.alignCalls += 1;
		int8_t* translated_query = new int8_t[query_len];
		AlignerTelemetryClock::time_point stageStart = AlignerTelemetryClock::now();
		TranslateBase(query, query_len, translated_query);
		telemetry.queryTranslateSeconds += elapsed_seconds(stageStart, AlignerTelemetryClock::now());

		// calculate the valid length
		int valid_ref_len = ref_len;
		int8_t* translated_ref = new int8_t[valid_ref_len];
		stageStart = AlignerTelemetryClock::now();
		TranslateBase(ref, valid_ref_len, translated_ref);
		telemetry.refTranslateSeconds += elapsed_seconds(stageStart, AlignerTelemetryClock::now());


		const int8_t score_size = 2;
		const std::string profileKey =
			BuildProfileReuseKey(translated_query,
			                     query_len,
			                     score_matrix_,
			                     score_matrix_size_,
			                     gap_opening_penalty_,
			                     gap_extending_penalty_,
			                     score_size);
		const std::string queryKey = BuildQueryReuseKey(translated_query, query_len);
		s_profile* profile = NULL;
		s_profile* legacyProfileForValidate = NULL;
		std::shared_ptr<CachedProfileEntry> cachedProfile;
		bool cacheHit = false;
		double profileBuildSeconds = 0.0;
		double profileSavedSeconds = 0.0;
		const bool profileCacheEnabled = ProfileCacheEnabledRuntime();
		const bool profileCacheValidate = profileCacheEnabled && ProfileCacheValidateRuntime();
		if (profileCacheEnabled) {
			cachedProfile = GetCachedProfile(profileKey,
			                                translated_query,
			                                query_len,
			                                score_matrix_,
			                                score_matrix_size_,
			                                score_size,
			                                &cacheHit,
			                                &profileBuildSeconds,
			                                &profileSavedSeconds);
			profile = cachedProfile->profile;
			RecordProfileCacheCall(cacheHit, profileKey, profileBuildSeconds, profileSavedSeconds);
		}
		else {
			profile = BuildSswProfile(translated_query,
			                          query_len,
			                          score_matrix_,
			                          score_matrix_size_,
			                          score_size,
			                          &profileBuildSeconds);
		}
		telemetry.profileSeconds += profileBuildSeconds;
		if (ProfileReuseShadowEnabledRuntime()) {
			RecordProfileReuseShadow(profileKey, queryKey, profileBuildSeconds);
		}

		uint8_t flag = 0;
		SetFlag(filter, &flag);
		stageStart = AlignerTelemetryClock::now();
		s_align* s_al = ssw_align(profile, translated_ref, valid_ref_len,
			static_cast<int>(gap_opening_penalty_),
			static_cast<int>(gap_extending_penalty_),
			flag, filter.score_filter, filter.distance_filter, maskLen);
		telemetry.sswTotalSeconds += elapsed_seconds(stageStart, AlignerTelemetryClock::now());

		alignment->Clear();
		Alignment legacyAlignment;
		s_align* legacySAl = NULL;
		bool useLegacyFallback = false;
		if(s_al!=NULL){
			stageStart = AlignerTelemetryClock::now();
		    ConvertAlignment(*s_al, query_len, alignment);
			telemetry.convertSeconds += elapsed_seconds(stageStart, AlignerTelemetryClock::now());
		}
		else{
			telemetry.nullResults += 1;
		    alignment->sw_score = 0;
		}
		//2021-09-16 22:38:00: to get original cigar string.
		//alignment->mismatches = CalculateNumberMismatch(&*alignment, translated_ref, translated_query, query_len);

		if (profileCacheValidate) {
			AlignerTelemetryClock::time_point validateStart = AlignerTelemetryClock::now();
			double legacyBuildSeconds = 0.0;
			legacyProfileForValidate = BuildSswProfile(translated_query,
			                                           query_len,
			                                           score_matrix_,
			                                           score_matrix_size_,
			                                           score_size,
			                                           &legacyBuildSeconds);
			legacySAl = ssw_align(legacyProfileForValidate,
			                      translated_ref,
			                      valid_ref_len,
			                      static_cast<int>(gap_opening_penalty_),
			                      static_cast<int>(gap_extending_penalty_),
			                      flag,
			                      filter.score_filter,
			                      filter.distance_filter,
			                      maskLen);
			legacyAlignment.Clear();
			if (legacySAl != NULL) {
				ConvertAlignment(*legacySAl, query_len, &legacyAlignment);
			}
			else {
				legacyAlignment.sw_score = 0;
			}
			const bool scoreMismatch = !AlignmentSameScore(*alignment, legacyAlignment);
			const bool endpointMismatch = !AlignmentSameEndpoint(*alignment, legacyAlignment);
			const bool cigarMismatch = !AlignmentSameCigar(*alignment, legacyAlignment);
			const bool digestMismatch = !AlignmentSameDigest(*alignment, legacyAlignment);
			useLegacyFallback =
				scoreMismatch || endpointMismatch || cigarMismatch || digestMismatch;
			if (useLegacyFallback) {
				*alignment = legacyAlignment;
			}
			RecordProfileCacheValidate(
				elapsed_seconds(validateStart, AlignerTelemetryClock::now()),
				scoreMismatch,
				endpointMismatch,
				cigarMismatch,
				digestMismatch,
				useLegacyFallback);
		}

		// Free memory
		stageStart = AlignerTelemetryClock::now();
		delete[] translated_query;
		delete[] translated_ref;
		if (s_al != NULL) align_destroy(s_al);
		if (legacySAl != NULL) align_destroy(legacySAl);
		if (legacyProfileForValidate != NULL) init_destroy(legacyProfileForValidate);
		if (!profileCacheEnabled) init_destroy(profile);
		telemetry.cleanupSeconds += elapsed_seconds(stageStart, AlignerTelemetryClock::now());
		AddAlignerTelemetry(telemetry);

		return true;
	}

	void Aligner::Clear(void) {
		ClearMatrices();
		CleanReferenceSequence();
	}

	void Aligner::SetAllDefault(void) {
		score_matrix_size_ = 5;
		match_score_ = 2;
		mismatch_penalty_ = 2;
		gap_opening_penalty_ = 3;
		gap_extending_penalty_ = 1;
		reference_length_ = 0;
	}

	bool Aligner::ReBuild(void) {
		if (translation_matrix_) return false;

		SetAllDefault();
		BuildDefaultMatrix();

		return true;
	}

	bool Aligner::ReBuild(
		const uint8_t& match_score,
		const uint8_t& mismatch_penalty,
		const uint8_t& gap_opening_penalty,
		const uint8_t& gap_extending_penalty) {
		if (translation_matrix_) return false;

		SetAllDefault();

		match_score_ = match_score;
		mismatch_penalty_ = mismatch_penalty;
		gap_opening_penalty_ = gap_opening_penalty;
		gap_extending_penalty_ = gap_extending_penalty;

		BuildDefaultMatrix();

		return true;
	}

	bool Aligner::ReBuild(
		const int8_t* score_matrix,
		const int&    score_matrix_size,
		const int8_t* translation_matrix,
		const int&    translation_matrix_size) {

		ClearMatrices();
		score_matrix_ = new int8_t[score_matrix_size_ * score_matrix_size_];
		memcpy(score_matrix_, score_matrix, sizeof(int8_t) * score_matrix_size_ * score_matrix_size_);
		translation_matrix_ = new int8_t[translation_matrix_size];
		memcpy(translation_matrix_, translation_matrix, sizeof(int8_t) * translation_matrix_size);

		return true;
	}

	void Aligner::BuildDefaultMatrix(void) {
		ClearMatrices();
		score_matrix_ = new int8_t[score_matrix_size_ * score_matrix_size_];
		BuildSwScoreMatrix(match_score_, mismatch_penalty_, score_matrix_);
		translation_matrix_ = new int8_t[SizeOfArray(kBaseTranslation)];
		memcpy(translation_matrix_, kBaseTranslation, sizeof(int8_t) * SizeOfArray(kBaseTranslation));
	}

	void Aligner::ClearMatrices(void) {
		delete[] score_matrix_;
		score_matrix_ = NULL;

		delete[] translation_matrix_;
		translation_matrix_ = NULL;
	}
} // namespace StripedSmithWaterman
