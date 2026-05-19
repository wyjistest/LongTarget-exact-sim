// ssw_cpp.h
// Created by Wan-Ping Lee
// Last revision by Mengyao Zhao on 2017-05-30

#ifndef COMPLETE_STRIPED_SMITH_WATERMAN_CPP_H_
#define COMPLETE_STRIPED_SMITH_WATERMAN_CPP_H_

#include <stdint.h>
#include <string>
#include <vector>

namespace StripedSmithWaterman {

	struct AlignerCpuInternalsProfileStats {
		AlignerCpuInternalsProfileStats()
			: enabled(0)
			, strlenNanoseconds(0)
			, queryAllocNanoseconds(0)
			, queryTranslateNanoseconds(0)
			, refAllocNanoseconds(0)
			, refTranslateNanoseconds(0)
			, profileBuildNanoseconds(0)
			, sswAlignNanoseconds(0)
			, convertNanoseconds(0)
			, destroyNanoseconds(0)
			, calls(0)
			, nullResults(0)
			, sswProfileReuseShadowEnabled(0)
			, sswProfileBuildCalls(0)
			, sswProfileUniqueKeys(0)
			, sswProfileReusedPossibleCalls(0)
			, sswProfileBuildNanoseconds(0)
			, sswProfileEstReuseSavedNanoseconds(0)
			, sswProfileKeyQueryLength(0)
			, sswProfileKeyScoringHash(0)
			, sswProfileKeyOrientation(0)
			, sswProfileShadowCompared(0)
			, sswProfileShadowScoreMismatches(0)
			, sswProfileShadowEndpointMismatches(0)
			, sswProfileShadowCigarMismatches(0)
			, sswProfileShadowOutputDigestMismatches(0)
			, sswProfileCacheRequested(0)
			, sswProfileCacheActive(0)
			, sswProfileCacheValidateEnabled(0)
			, sswProfileCacheCalls(0)
			, sswProfileCacheHits(0)
			, sswProfileCacheMisses(0)
			, sswProfileCacheUniqueKeys(0)
			, sswProfileCacheBuildNanoseconds(0)
			, sswProfileCacheSavedBuildNanoseconds(0)
			, sswProfileCacheValidateNanoseconds(0)
			, sswProfileCacheScoreMismatches(0)
			, sswProfileCacheEndpointMismatches(0)
			, sswProfileCacheCigarMismatches(0)
			, sswProfileCacheDigestMismatches(0)
			, sswProfileCacheFallbacks(0)
		{};

		uint64_t enabled;
		uint64_t strlenNanoseconds;
		uint64_t queryAllocNanoseconds;
		uint64_t queryTranslateNanoseconds;
		uint64_t refAllocNanoseconds;
		uint64_t refTranslateNanoseconds;
		uint64_t profileBuildNanoseconds;
		uint64_t sswAlignNanoseconds;
		uint64_t convertNanoseconds;
		uint64_t destroyNanoseconds;
		uint64_t calls;
		uint64_t nullResults;
		uint64_t sswProfileReuseShadowEnabled;
		uint64_t sswProfileBuildCalls;
		uint64_t sswProfileUniqueKeys;
		uint64_t sswProfileReusedPossibleCalls;
		uint64_t sswProfileBuildNanoseconds;
		uint64_t sswProfileEstReuseSavedNanoseconds;
		uint64_t sswProfileKeyQueryLength;
		uint64_t sswProfileKeyScoringHash;
		uint64_t sswProfileKeyOrientation;
		uint64_t sswProfileShadowCompared;
		uint64_t sswProfileShadowScoreMismatches;
		uint64_t sswProfileShadowEndpointMismatches;
		uint64_t sswProfileShadowCigarMismatches;
		uint64_t sswProfileShadowOutputDigestMismatches;
		uint64_t sswProfileCacheRequested;
		uint64_t sswProfileCacheActive;
		uint64_t sswProfileCacheValidateEnabled;
		uint64_t sswProfileCacheCalls;
		uint64_t sswProfileCacheHits;
		uint64_t sswProfileCacheMisses;
		uint64_t sswProfileCacheUniqueKeys;
		uint64_t sswProfileCacheBuildNanoseconds;
		uint64_t sswProfileCacheSavedBuildNanoseconds;
		uint64_t sswProfileCacheValidateNanoseconds;
		uint64_t sswProfileCacheScoreMismatches;
		uint64_t sswProfileCacheEndpointMismatches;
		uint64_t sswProfileCacheCigarMismatches;
		uint64_t sswProfileCacheDigestMismatches;
		uint64_t sswProfileCacheFallbacks;
	};

	AlignerCpuInternalsProfileStats* SetAlignerCpuInternalsProfileStats(
		AlignerCpuInternalsProfileStats* stats);

	struct Alignment {
		uint16_t sw_score;           // The best alignment score
		uint16_t sw_score_next_best; // The next best alignment score
		int32_t  ref_begin;          // Reference begin position of the best alignment
		int32_t  ref_end;            // Reference end position of the best alignment
		int32_t  query_begin;        // Query begin position of the best alignment
		int32_t  query_end;          // Query end position of the best alignment
		int32_t  ref_end_next_best;  // Reference end position of the next best alignment
		int32_t  mismatches;         // Number of mismatches of the alignment
		std::string cigar_string;    // Cigar string of the best alignment
		std::vector<uint32_t> cigar; // Cigar stored in the BAM format
									 //   high 28 bits: length
						 //   low 4 bits: M/I/D/S/X (0/1/2/4/8);
		void Clear() {
			sw_score = 0;
			sw_score_next_best = 0;
			ref_begin = 0;
			ref_end = 0;
			query_begin = 0;
			query_end = 0;
			ref_end_next_best = 0;
			mismatches = 0;
			cigar_string.clear();
			cigar.clear();
		};
	};

	struct scoreInfo {
		scoreInfo() {};
		scoreInfo(int n1, int n2) :score(n1), position(n2) {};
		int score;
		int position;
	};

	struct Filter {
		// NOTE: No matter the filter, those five fields of Alignment will be given anyway.
		//       sw_score; sw_score_next_best; ref_end; query_end; ref_end_next_best.
		// NOTE: Only need score of alignments, please set 'report_begin_position'
		//       and 'report_cigar' false.

		bool report_begin_position;    // Give ref_begin and query_begin.
									   //   If it is not set, ref_begin and query_begin are -1.
		bool report_cigar;             // Give cigar_string and cigar.
									   //   report_begin_position is automatically TRUE.

		// When *report_cigar* is true and alignment passes these two filters,
		//   cigar_string and cigar will be given.
		uint16_t score_filter;         // score >= score_filter
		uint16_t distance_filter;      // ((ref_end - ref_begin) < distance_filter) &&
									   // ((query_end - read_begin) < distance_filter)

		Filter()
			: report_begin_position(true)
			, report_cigar(true)
			, score_filter(0)
			, distance_filter(32767)
		{};

		Filter(const bool& pos, const bool& cigar, const uint16_t& score, const uint16_t& dis)
			: report_begin_position(pos)
			, report_cigar(cigar)
			, score_filter(score)
			, distance_filter(dis)
		{};
	};

	class Aligner {
	public:
		// =========
		// @function Construct an Aligner on default values.
		//             The function will build the {A.C,G,T,N} aligner.
		//             If you target for other character aligners, then please
		//             use the other constructor and pass the corresponding matrix in.
		// =========
		Aligner(void);

		// =========
		// @function Construct an Aligner by assigning scores.
		//             The function will build the {A.C,G,T,N} aligner.
		//             If you target for other character aligners, then please
		//             use the other constructor and pass the corresponding matrix in.
		// =========
		Aligner(const uint8_t& match_score,
			const uint8_t& mismatch_penalty,
			const uint8_t& gap_opening_penalty,
			const uint8_t& gap_extending_penalty);

		// =========
		// @function Construct an Aligner by the specific matrixs.
		// =========
		Aligner(const int8_t* score_matrix,
			const int&    score_matrix_size,
			const int8_t* translation_matrix,
			const int&    translation_matrix_size);

		~Aligner(void);

		// =========
		// @function Build the reference sequence and thus make
		//             Align(const char* query, s_align* alignment) function;
		//             otherwise the reference should be given when aligning.
		//           [NOTICE] If there exists a sequence, that one will be deleted
		//                    and replaced.
		// @param    seq    The reference bases;
		//                  [NOTICE] It is not necessary null terminated.
		// @param    length The length of bases will be be built.
		// @return   The length of the built bases.
		// =========
		int SetReferenceSequence(const char* seq, const int& length);

		void CleanReferenceSequence(void);

		// =========
		// @function Set penalties for opening and extending gaps
		//           [NOTICE] The defaults are 3 and 1 respectively.
		// =========
		void SetGapPenalty(const uint8_t& opening, const uint8_t& extending) {
			gap_opening_penalty_ = opening;
			gap_extending_penalty_ = extending;
		};

		// =========
		// @function Align the query againt the reference that is set by
		//             SetReferenceSequence.
		// @param    query     The query sequence.
		// @param    filter    The filter for the alignment.
		// @param    alignment The container contains the result.
		// @param    maskLen   The distance between the optimal and suboptimal alignment ending position will >= maskLen. We suggest to 
		//                     use readLen/2, if you don't have special concerns. Note: maskLen has to be >= 15, otherwise this function 
		//                     will NOT return the suboptimal alignment information.
		// @return   True: succeed; false: fail.
		// =========
		bool Align(const char* query, const Filter& filter, Alignment* alignment, const int32_t maskLen) const;

		// =========
		// @function Align the query againt the reference.
		//           [NOTICE] The reference won't replace the reference
		//                      set by SetReferenceSequence.
		// @param    query     The query sequence.
		// @param    ref       The reference sequence.
		//                     [NOTICE] It is not necessary null terminated.
		// @param    ref_len   The length of the reference sequence.
		// @param    filter    The filter for the alignment.
		// @param    alignment The container contains the result.
		// @param    maskLen   The distance between the optimal and suboptimal alignment ending position will >= maskLen. We suggest to 
		//                     use readLen/2, if you don't have special concerns. Note: maskLen has to be >= 15, otherwise this function 
		//                     will NOT return the suboptimal alignment information.
		// @return   True: succeed; false: fail.
		// =========
		bool Align(const char* query, const char* ref, const int& ref_len,
			const Filter& filter, Alignment* alignment, const int32_t maskLen) const;
		// @function use this function to get all sub-optimal alignments whose 
		// score is larger than threshold. Highly similar with Align, but just gather
		// scoreMatrix, no alignments.
			bool  preAlign(const char* query, const char* ref, const int& ref_len,
				const Filter& filter, Alignment* alignment, const int32_t maskLen,
				int threshold, std::vector<struct scoreInfo> &finalScoreInfo,int match,int mismatch,
				std::vector<int> *scoreVectorOut = NULL) const;

		// @function Clear up all containers and thus the aligner is disabled.
		//             To rebuild the aligner please use Build functions.
		void Clear(void);

		// =========
		// @function Rebuild the aligner's ability on default values.
		//           [NOTICE] If the aligner is not cleaned, rebuilding will fail.
		// @return   True: succeed; false: fail.
		// =========
		bool ReBuild(void);

		// =========
		// @function Rebuild the aligner's ability by the specific matrixs.
		//           [NOTICE] If the aligner is not cleaned, rebuilding will fail.
		// @return   True: succeed; false: fail.
		// =========
		bool ReBuild(
			const uint8_t& match_score,
			const uint8_t& mismatch_penalty,
			const uint8_t& gap_opening_penalty,
			const uint8_t& gap_extending_penalty);

		// =========
		// @function Construct an Aligner by the specific matrixs.
		//           [NOTICE] If the aligner is not cleaned, rebuilding will fail.
		// @return   True: succeed; false: fail.
		// =========
		bool ReBuild(
			const int8_t* score_matrix,
			const int&    score_matrix_size,
			const int8_t* translation_matrix,
			const int&    translation_matrix_size);

	private:
		int8_t* score_matrix_;
		int     score_matrix_size_;
		int8_t* translation_matrix_;

		uint8_t match_score_;           // default: 2
		uint8_t mismatch_penalty_;      // default: 2
		uint8_t gap_opening_penalty_;   // default: 3
		uint8_t gap_extending_penalty_; // default: 1

		int8_t* translated_reference_;
		int32_t reference_length_;

		int TranslateBase(const char* bases, const int& length, int8_t* translated) const;
		void SetAllDefault(void);
		void BuildDefaultMatrix(void);
		void ClearMatrices(void);

		Aligner& operator= (const Aligner&);
		Aligner(const Aligner&);
	}; // class Aligner


	// ================
	// inline functions
	// ================
	inline void Aligner::CleanReferenceSequence(void) {
		if (reference_length_ == 0) return;

		// delete the current buffer
		if (reference_length_ > 1) delete[] translated_reference_;
		else delete translated_reference_;

		reference_length_ = 0;
	}
} // namespace StripedSmithWaterman

#endif // COMPLETE_STRIPED_SMITH_WATERMAN_CPP_H_
