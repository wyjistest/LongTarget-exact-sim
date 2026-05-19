// ssw_cpp.cpp
// Created by Wan-Ping Lee
// Last revision by Mengyao Zhao on 2017-05-30

#include "ssw_cpp.h"
#include "ssw.h"
#include<algorithm>
#include <chrono>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

namespace {

	static thread_local StripedSmithWaterman::AlignerCpuInternalsProfileStats*
		g_aligner_cpu_internals_profile_stats = NULL;

	struct SswProfileReuseShadowCacheEntry {
		SswProfileReuseShadowCacheEntry()
			: profile(NULL)
			, hits(0)
		{
		}

		~SswProfileReuseShadowCacheEntry()
		{
			if (profile != NULL) {
				init_destroy(profile);
			}
		}

		std::vector<int8_t> query;
		std::vector<int8_t> matrix;
		s_profile* profile;
		uint64_t hits;
	};

	static thread_local std::map<std::string, std::unique_ptr<SswProfileReuseShadowCacheEntry> >
		g_ssw_profile_reuse_shadow_cache;

	struct SswProfileCacheEntry {
		SswProfileCacheEntry()
			: profile(NULL)
			, buildNanoseconds(0)
		{
		}

		~SswProfileCacheEntry()
		{
			if (profile != NULL) {
				init_destroy(profile);
			}
		}

		std::vector<int8_t> query;
		std::vector<int8_t> matrix;
		s_profile* profile;
		uint64_t buildNanoseconds;
	};

	static thread_local std::map<std::string, std::unique_ptr<SswProfileCacheEntry> >
		g_ssw_profile_cache;

	uint64_t CpuInternalsNowNanoseconds() {
		return static_cast<uint64_t>(
			std::chrono::duration_cast<std::chrono::nanoseconds>(
				std::chrono::steady_clock::now().time_since_epoch()).count());
	}

	void CpuInternalsAddElapsed(uint64_t& slot, uint64_t startNanoseconds) {
		slot += CpuInternalsNowNanoseconds() - startNanoseconds;
	}

	void ConvertAlignment(const s_align& s_al,
		const int& query_len,
		StripedSmithWaterman::Alignment* al);

	bool SswProfileReuseShadowEnabledRuntime() {
		static const bool enabled = []() {
			const char* env = getenv("FASIM_SSW_PROFILE_REUSE_SHADOW");
			if (env == NULL || env[0] == '\0') {
				return false;
			}
			return env[0] != '0';
		}();
		return enabled;
	}

	bool SswProfileCacheEnabledRuntime() {
		static const bool enabled = []() {
			const char* env = getenv("FASIM_SSW_PROFILE_CACHE");
			if (env == NULL || env[0] == '\0') {
				return false;
			}
			return env[0] != '0';
		}();
		return enabled;
	}

	bool SswProfileCacheValidateRuntime() {
		static const bool enabled = []() {
			const char* env = getenv("FASIM_SSW_PROFILE_CACHE_VALIDATE");
			if (env == NULL || env[0] == '\0') {
				return false;
			}
			return env[0] != '0';
		}();
		return enabled;
	}

	uint64_t SswProfileReuseShadowMaxCompareRuntime() {
		static const uint64_t maxCompare = []() {
			const char* env = getenv("FASIM_SSW_PROFILE_REUSE_SHADOW_MAX_COMPARE");
			if (env == NULL || env[0] == '\0') {
				return static_cast<uint64_t>(1024);
			}
			const long long parsed = atoll(env);
			return parsed > 0 ? static_cast<uint64_t>(parsed) : static_cast<uint64_t>(0);
		}();
		return maxCompare;
	}

	uint64_t SswProfileReuseShadowHashBytes(const int8_t* data, size_t size) {
		uint64_t hash = 1469598103934665603ULL;
		for (size_t i = 0; i < size; ++i) {
			hash ^= static_cast<uint8_t>(data[i]);
			hash *= 1099511628211ULL;
		}
		return hash;
	}

	void SswProfileReuseShadowHashAppendUint64(uint64_t& hash, uint64_t value) {
		for (int i = 0; i < 8; ++i) {
			hash ^= static_cast<uint8_t>((value >> (i * 8)) & 0xff);
			hash *= 1099511628211ULL;
		}
	}

	uint64_t SswProfileReuseShadowScoringHash(const int8_t* matrix,
		const int matrixSize,
		const uint8_t gapOpeningPenalty,
		const uint8_t gapExtendingPenalty,
		const int8_t scoreSize) {
		uint64_t hash = SswProfileReuseShadowHashBytes(
			matrix, static_cast<size_t>(matrixSize) * static_cast<size_t>(matrixSize));
		SswProfileReuseShadowHashAppendUint64(hash, static_cast<uint64_t>(matrixSize));
		SswProfileReuseShadowHashAppendUint64(hash, static_cast<uint64_t>(gapOpeningPenalty));
		SswProfileReuseShadowHashAppendUint64(hash, static_cast<uint64_t>(gapExtendingPenalty));
		SswProfileReuseShadowHashAppendUint64(hash, static_cast<uint64_t>(scoreSize));
		return hash;
	}

	std::string SswProfileReuseShadowKey(const int8_t* query,
		const int queryLen,
		const int8_t* matrix,
		const int matrixSize,
		const uint8_t gapOpeningPenalty,
		const uint8_t gapExtendingPenalty,
		const int8_t scoreSize,
		uint64_t* scoringHashOut) {
		const uint64_t queryHash =
			SswProfileReuseShadowHashBytes(query, static_cast<size_t>(queryLen));
		const uint64_t scoringHash =
			SswProfileReuseShadowScoringHash(matrix, matrixSize,
			                                 gapOpeningPenalty,
			                                 gapExtendingPenalty,
			                                 scoreSize);
		if (scoringHashOut != NULL) {
			*scoringHashOut = scoringHash;
		}
		std::ostringstream key;
		key << queryLen << ':' << matrixSize << ':'
		    << static_cast<int>(scoreSize) << ':'
		    << queryHash << ':' << scoringHash;
		return key.str();
	}

	bool SswProfileReuseShadowCigarEquals(const StripedSmithWaterman::Alignment& lhs,
		const StripedSmithWaterman::Alignment& rhs) {
		if (lhs.cigar_string != rhs.cigar_string) {
			return false;
		}
		if (lhs.cigar.size() != rhs.cigar.size()) {
			return false;
		}
		for (size_t i = 0; i < lhs.cigar.size(); ++i) {
			if (lhs.cigar[i] != rhs.cigar[i]) {
				return false;
			}
		}
		return true;
	}

	bool SswProfileAlignmentEquals(const StripedSmithWaterman::Alignment& lhs,
		const StripedSmithWaterman::Alignment& rhs,
		StripedSmithWaterman::AlignerCpuInternalsProfileStats* stats,
		const bool countMismatches) {
		bool matches = true;
		if (lhs.sw_score != rhs.sw_score ||
		    lhs.sw_score_next_best != rhs.sw_score_next_best) {
			matches = false;
			if (countMismatches && stats != NULL) {
				++stats->sswProfileCacheScoreMismatches;
			}
		}
		if (lhs.ref_begin != rhs.ref_begin ||
		    lhs.ref_end != rhs.ref_end ||
		    lhs.query_begin != rhs.query_begin ||
		    lhs.query_end != rhs.query_end ||
		    lhs.ref_end_next_best != rhs.ref_end_next_best) {
			matches = false;
			if (countMismatches && stats != NULL) {
				++stats->sswProfileCacheEndpointMismatches;
			}
		}
		if (!SswProfileReuseShadowCigarEquals(lhs, rhs)) {
			matches = false;
			if (countMismatches && stats != NULL) {
				++stats->sswProfileCacheCigarMismatches;
			}
		}
		if (!matches && countMismatches && stats != NULL) {
			++stats->sswProfileCacheDigestMismatches;
		}
		return matches;
	}

	s_align* SswProfileRunAlign(s_profile* profile,
		const int8_t* translatedRef,
		const int validRefLen,
		const uint8_t gapOpeningPenalty,
		const uint8_t gapExtendingPenalty,
		const uint8_t flag,
		const StripedSmithWaterman::Filter& filter,
		const int32_t maskLen) {
		return ssw_align(profile, translatedRef, validRefLen,
			static_cast<int>(gapOpeningPenalty),
			static_cast<int>(gapExtendingPenalty),
			flag, filter.score_filter, filter.distance_filter, maskLen);
	}

	void SswProfileConvertNullableAlignment(s_align* sAl,
		const int queryLen,
		StripedSmithWaterman::Alignment* alignment,
		StripedSmithWaterman::AlignerCpuInternalsProfileStats* stats) {
		alignment->Clear();
		if (sAl != NULL) {
			ConvertAlignment(*sAl, queryLen, alignment);
		}
		else {
			alignment->sw_score = 0;
			if (stats != NULL) {
				++stats->nullResults;
			}
		}
	}

	s_profile* SswProfileCacheGetOrBuild(const int8_t* translatedQuery,
		const int queryLen,
		const int8_t* scoreMatrix,
		const int scoreMatrixSize,
		const int8_t scoreSize,
		const uint8_t gapOpeningPenalty,
		const uint8_t gapExtendingPenalty,
		StripedSmithWaterman::AlignerCpuInternalsProfileStats* stats) {
		uint64_t scoringHash = 0;
		const std::string key = SswProfileReuseShadowKey(
			translatedQuery, queryLen, scoreMatrix, scoreMatrixSize,
			gapOpeningPenalty, gapExtendingPenalty, scoreSize, &scoringHash);
		std::map<std::string, std::unique_ptr<SswProfileCacheEntry> >::iterator it =
			g_ssw_profile_cache.find(key);
		if (it != g_ssw_profile_cache.end()) {
			if (stats != NULL) {
				++stats->sswProfileCacheHits;
				stats->sswProfileCacheSavedBuildNanoseconds +=
					it->second->buildNanoseconds;
				stats->sswProfileCacheUniqueKeys =
					static_cast<uint64_t>(g_ssw_profile_cache.size());
			}
			return it->second->profile;
		}

		if (stats != NULL) {
			++stats->sswProfileCacheMisses;
		}
		std::unique_ptr<SswProfileCacheEntry> entry(new SswProfileCacheEntry());
		entry->query.assign(translatedQuery, translatedQuery + queryLen);
		entry->matrix.assign(scoreMatrix,
			scoreMatrix + scoreMatrixSize * scoreMatrixSize);
		const uint64_t buildStart =
			stats != NULL ? CpuInternalsNowNanoseconds() : 0;
		entry->profile = ssw_init(entry->query.data(), queryLen,
			entry->matrix.data(), scoreMatrixSize, scoreSize);
		if (stats != NULL) {
			entry->buildNanoseconds = CpuInternalsNowNanoseconds() - buildStart;
			stats->sswProfileCacheBuildNanoseconds += entry->buildNanoseconds;
		}
		s_profile* profile = entry->profile;
		g_ssw_profile_cache.insert(std::make_pair(key, std::move(entry)));
		if (stats != NULL) {
			stats->sswProfileCacheUniqueKeys =
				static_cast<uint64_t>(g_ssw_profile_cache.size());
		}
		return profile;
	}

	void SswProfileReuseShadowCompare(s_profile* profile,
		const int queryLen,
		const int8_t* translatedRef,
		const int validRefLen,
		const uint8_t gapOpeningPenalty,
		const uint8_t gapExtendingPenalty,
		const uint8_t flag,
		const StripedSmithWaterman::Filter& filter,
		const int32_t maskLen,
		const StripedSmithWaterman::Alignment& cpuAlignment,
		StripedSmithWaterman::AlignerCpuInternalsProfileStats* stats) {
		if (profile == NULL || translatedRef == NULL || stats == NULL) {
			return;
		}
		if (stats->sswProfileShadowCompared >= SswProfileReuseShadowMaxCompareRuntime()) {
			return;
		}
		s_align* shadowAlign = ssw_align(profile, translatedRef, validRefLen,
			static_cast<int>(gapOpeningPenalty),
			static_cast<int>(gapExtendingPenalty),
			flag, filter.score_filter, filter.distance_filter, maskLen);
		StripedSmithWaterman::Alignment shadowAlignment;
		shadowAlignment.Clear();
		if (shadowAlign != NULL) {
			ConvertAlignment(*shadowAlign, queryLen, &shadowAlignment);
		}
		else {
			shadowAlignment.sw_score = 0;
		}
		++stats->sswProfileShadowCompared;
		if (shadowAlignment.sw_score != cpuAlignment.sw_score ||
		    shadowAlignment.sw_score_next_best != cpuAlignment.sw_score_next_best) {
			++stats->sswProfileShadowScoreMismatches;
		}
		if (shadowAlignment.ref_begin != cpuAlignment.ref_begin ||
		    shadowAlignment.ref_end != cpuAlignment.ref_end ||
		    shadowAlignment.query_begin != cpuAlignment.query_begin ||
		    shadowAlignment.query_end != cpuAlignment.query_end ||
		    shadowAlignment.ref_end_next_best != cpuAlignment.ref_end_next_best) {
			++stats->sswProfileShadowEndpointMismatches;
		}
		if (!SswProfileReuseShadowCigarEquals(shadowAlignment, cpuAlignment)) {
			++stats->sswProfileShadowCigarMismatches;
		}
		if (shadowAlignment.sw_score != cpuAlignment.sw_score ||
		    shadowAlignment.sw_score_next_best != cpuAlignment.sw_score_next_best ||
		    shadowAlignment.ref_begin != cpuAlignment.ref_begin ||
		    shadowAlignment.ref_end != cpuAlignment.ref_end ||
		    shadowAlignment.query_begin != cpuAlignment.query_begin ||
		    shadowAlignment.query_end != cpuAlignment.query_end ||
		    shadowAlignment.ref_end_next_best != cpuAlignment.ref_end_next_best ||
		    !SswProfileReuseShadowCigarEquals(shadowAlignment, cpuAlignment)) {
			++stats->sswProfileShadowOutputDigestMismatches;
		}
		if (shadowAlign != NULL) {
			align_destroy(shadowAlign);
		}
	}

	void SswProfileReuseShadowRecordAndCompare(const int8_t* translatedQuery,
		const int queryLen,
		const int8_t* translatedRef,
		const int validRefLen,
		const int8_t* scoreMatrix,
		const int scoreMatrixSize,
		const int8_t scoreSize,
		const uint8_t gapOpeningPenalty,
		const uint8_t gapExtendingPenalty,
		const uint8_t flag,
		const StripedSmithWaterman::Filter& filter,
		const int32_t maskLen,
		const uint64_t profileBuildElapsed,
		const StripedSmithWaterman::Alignment& cpuAlignment,
		StripedSmithWaterman::AlignerCpuInternalsProfileStats* stats) {
		if (stats == NULL || !SswProfileReuseShadowEnabledRuntime()) {
			return;
		}
		stats->sswProfileReuseShadowEnabled = 1;
		++stats->sswProfileBuildCalls;
		stats->sswProfileBuildNanoseconds += profileBuildElapsed;
		stats->sswProfileKeyQueryLength = static_cast<uint64_t>(queryLen);
		stats->sswProfileKeyOrientation = 0;

		uint64_t scoringHash = 0;
		const std::string key = SswProfileReuseShadowKey(
			translatedQuery, queryLen, scoreMatrix, scoreMatrixSize,
			gapOpeningPenalty, gapExtendingPenalty, scoreSize, &scoringHash);
		stats->sswProfileKeyScoringHash = scoringHash;

		std::map<std::string, std::unique_ptr<SswProfileReuseShadowCacheEntry> >::iterator it =
			g_ssw_profile_reuse_shadow_cache.find(key);
		if (it == g_ssw_profile_reuse_shadow_cache.end()) {
			std::unique_ptr<SswProfileReuseShadowCacheEntry> entry(
				new SswProfileReuseShadowCacheEntry());
			entry->query.assign(translatedQuery, translatedQuery + queryLen);
			entry->matrix.assign(scoreMatrix,
				scoreMatrix + scoreMatrixSize * scoreMatrixSize);
			entry->profile = ssw_init(entry->query.data(), queryLen,
				entry->matrix.data(), scoreMatrixSize, scoreSize);
			entry->hits = 1;
			g_ssw_profile_reuse_shadow_cache.insert(std::make_pair(key, std::move(entry)));
			stats->sswProfileUniqueKeys =
				static_cast<uint64_t>(g_ssw_profile_reuse_shadow_cache.size());
			return;
		}

		++stats->sswProfileReusedPossibleCalls;
		stats->sswProfileEstReuseSavedNanoseconds += profileBuildElapsed;
		++it->second->hits;
		stats->sswProfileUniqueKeys =
			static_cast<uint64_t>(g_ssw_profile_reuse_shadow_cache.size());
		SswProfileReuseShadowCompare(it->second->profile, queryLen,
		                             translatedRef, validRefLen,
		                             gapOpeningPenalty, gapExtendingPenalty,
		                             flag, filter, maskLen, cpuAlignment,
		                             stats);
	}

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

	AlignerCpuInternalsProfileStats* SetAlignerCpuInternalsProfileStats(
		AlignerCpuInternalsProfileStats* stats) {
		AlignerCpuInternalsProfileStats* previous =
			g_aligner_cpu_internals_profile_stats;
		g_aligner_cpu_internals_profile_stats = stats;
		return previous;
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
		int8_t* translated_query = new int8_t[query_len];
		TranslateBase(query, query_len, translated_query);

		const int8_t score_size = 2;
		s_profile* profile = ssw_init(translated_query, query_len, score_matrix_,
			score_matrix_size_, score_size);

		uint8_t flag = 0;
		SetFlag(filter, &flag);
		s_align* s_al = ssw_align(profile, translated_reference_, reference_length_,
			static_cast<int>(gap_opening_penalty_),
			static_cast<int>(gap_extending_penalty_),
			flag, filter.score_filter, filter.distance_filter, maskLen);

		alignment->Clear();
		ConvertAlignment(*s_al, query_len, alignment);
		alignment->mismatches = CalculateNumberMismatch(&*alignment, translated_reference_, translated_query, query_len);


		// Free memory
		delete[] translated_query;
		align_destroy(s_al);
		init_destroy(profile);

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
			int threshold, std::vector<struct scoreInfo> &finalScoreInfo,int match,int mismatch,
			std::vector<int> *scoreVectorOut) const
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
			if (scoreVectorOut != NULL)
			{
				*scoreVectorOut = scoreVector;
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
		AlignerCpuInternalsProfileStats* internalsStats =
			g_aligner_cpu_internals_profile_stats;
		const bool profileCacheEnabled = SswProfileCacheEnabledRuntime();
		const bool profileCacheValidate =
			profileCacheEnabled && SswProfileCacheValidateRuntime();
		if (internalsStats != NULL) {
			internalsStats->enabled = 1;
			++internalsStats->calls;
			if (profileCacheEnabled) {
				internalsStats->sswProfileCacheRequested = 1;
				internalsStats->sswProfileCacheActive = 1;
				internalsStats->sswProfileCacheValidateEnabled =
					profileCacheValidate ? 1 : 0;
				++internalsStats->sswProfileCacheCalls;
			}
		}
		if (!translation_matrix_) return false;

		const uint64_t strlenStart =
			internalsStats != NULL ? CpuInternalsNowNanoseconds() : 0;
		int query_len = strlen(query);
		if (internalsStats != NULL) {
			CpuInternalsAddElapsed(internalsStats->strlenNanoseconds, strlenStart);
		}
		if (query_len == 0) return false;

		const uint64_t queryAllocStart =
			internalsStats != NULL ? CpuInternalsNowNanoseconds() : 0;
		int8_t* translated_query = new int8_t[query_len];
		if (internalsStats != NULL) {
			CpuInternalsAddElapsed(internalsStats->queryAllocNanoseconds, queryAllocStart);
		}

		const uint64_t queryTranslateStart =
			internalsStats != NULL ? CpuInternalsNowNanoseconds() : 0;
		TranslateBase(query, query_len, translated_query);
		if (internalsStats != NULL) {
			CpuInternalsAddElapsed(internalsStats->queryTranslateNanoseconds,
			                       queryTranslateStart);
		}

		// calculate the valid length
		int valid_ref_len = ref_len;
		const uint64_t refAllocStart =
			internalsStats != NULL ? CpuInternalsNowNanoseconds() : 0;
		int8_t* translated_ref = new int8_t[valid_ref_len];
		if (internalsStats != NULL) {
			CpuInternalsAddElapsed(internalsStats->refAllocNanoseconds, refAllocStart);
		}

		const uint64_t refTranslateStart =
			internalsStats != NULL ? CpuInternalsNowNanoseconds() : 0;
		TranslateBase(ref, valid_ref_len, translated_ref);
		if (internalsStats != NULL) {
			CpuInternalsAddElapsed(internalsStats->refTranslateNanoseconds,
			                       refTranslateStart);
		}


		const int8_t score_size = 2;
		s_profile* profile = NULL;
		bool destroyProfile = true;
		uint64_t profileBuildElapsed = 0;
		if (profileCacheEnabled) {
			profile = SswProfileCacheGetOrBuild(translated_query, query_len,
				score_matrix_, score_matrix_size_, score_size,
				gap_opening_penalty_, gap_extending_penalty_, internalsStats);
			destroyProfile = false;
		}
		else {
			const uint64_t profileBuildStart =
				internalsStats != NULL ? CpuInternalsNowNanoseconds() : 0;
			profile = ssw_init(translated_query, query_len, score_matrix_,
				score_matrix_size_, score_size);
			if (internalsStats != NULL) {
				profileBuildElapsed = CpuInternalsNowNanoseconds() - profileBuildStart;
				internalsStats->profileBuildNanoseconds += profileBuildElapsed;
			}
		}

		uint8_t flag = 0;
		SetFlag(filter, &flag);
		const uint64_t sswAlignStart =
			internalsStats != NULL ? CpuInternalsNowNanoseconds() : 0;
		s_align* s_al = SswProfileRunAlign(profile, translated_ref, valid_ref_len,
			gap_opening_penalty_, gap_extending_penalty_, flag, filter, maskLen);
		if (internalsStats != NULL) {
			CpuInternalsAddElapsed(internalsStats->sswAlignNanoseconds,
			                       sswAlignStart);
		}

		const uint64_t convertStart =
			internalsStats != NULL ? CpuInternalsNowNanoseconds() : 0;
		SswProfileConvertNullableAlignment(s_al, query_len, alignment, internalsStats);
		if (internalsStats != NULL) {
			CpuInternalsAddElapsed(internalsStats->convertNanoseconds,
			                       convertStart);
		}
		if (profileCacheValidate) {
			const uint64_t validateStart =
				internalsStats != NULL ? CpuInternalsNowNanoseconds() : 0;
			s_profile* legacyProfile = ssw_init(translated_query, query_len,
				score_matrix_, score_matrix_size_, score_size);
			s_align* legacyAlign = SswProfileRunAlign(legacyProfile,
				translated_ref, valid_ref_len,
				gap_opening_penalty_, gap_extending_penalty_,
				flag, filter, maskLen);
			Alignment legacyAlignment;
			SswProfileConvertNullableAlignment(legacyAlign, query_len,
			                                   &legacyAlignment, NULL);
			if (!SswProfileAlignmentEquals(*alignment, legacyAlignment,
			                               internalsStats, true)) {
				if (internalsStats != NULL) {
					++internalsStats->sswProfileCacheFallbacks;
				}
				*alignment = legacyAlignment;
			}
			if (legacyAlign != NULL) {
				align_destroy(legacyAlign);
			}
			init_destroy(legacyProfile);
			if (internalsStats != NULL) {
				CpuInternalsAddElapsed(
					internalsStats->sswProfileCacheValidateNanoseconds,
					validateStart);
			}
		}
		SswProfileReuseShadowRecordAndCompare(translated_query, query_len,
		                                      translated_ref, valid_ref_len,
		                                      score_matrix_, score_matrix_size_,
		                                      score_size,
		                                      gap_opening_penalty_,
		                                      gap_extending_penalty_,
		                                      flag, filter, maskLen,
		                                      profileBuildElapsed,
		                                      *alignment, internalsStats);
		//2021-09-16 22:38:00: to get original cigar string.
		//alignment->mismatches = CalculateNumberMismatch(&*alignment, translated_ref, translated_query, query_len);

		// Free memory
		const uint64_t destroyStart =
			internalsStats != NULL ? CpuInternalsNowNanoseconds() : 0;
		delete[] translated_query;
		delete[] translated_ref;
		if (s_al != NULL) {
		    align_destroy(s_al);
		}
		if (destroyProfile) {
			init_destroy(profile);
		}
		if (internalsStats != NULL) {
			CpuInternalsAddElapsed(internalsStats->destroyNanoseconds,
			                       destroyStart);
		}

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
