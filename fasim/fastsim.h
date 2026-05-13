#include <iostream>
#include <string.h>
#include <sstream>
#include <fstream>
#include <cstdlib>
#include "ssw_cpp.h"
#include "ssw.h"
#include "sim.h"
#include "../cuda/prealign_cuda.h"
#include "../cuda/prealign_shared.h"
#define N 50
using std::string;
using std::cout;
using std::endl;
using std::ifstream;

inline bool fasim_gpu_dp_column_requested_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_GPU_DP_COLUMN");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_gpu_dp_column_validate_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_GPU_DP_COLUMN_VALIDATE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline bool fasim_prealign_cuda_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char* env = getenv("FASIM_ENABLE_PREALIGN_CUDA");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
}

inline int fasim_cuda_device_runtime()
{
	const char* env = getenv("FASIM_CUDA_DEVICE");
	if (env != NULL && env[0] != '\0')
	{
		return atoi(env);
	}
	env = getenv("LONGTARGET_CUDA_DEVICE");
	if (env != NULL && env[0] != '\0')
	{
		return atoi(env);
	}
	return -1;
}

inline int fasim_prealign_peak_suppress_bp_runtime()
{
	static const int suppressBp = []()
	{
		const char* env = getenv("FASIM_PREALIGN_PEAK_SUPPRESS_BP");
		if (env == NULL || env[0] == '\0')
		{
			return 5;
		}
		const int value = atoi(env);
		if (value <= 0)
		{
			return 5;
		}
		if (value > 1024)
		{
			return 1024;
		}
		return value;
	}();
	return suppressBp;
}

inline int fasim_prealign_cuda_topk_runtime()
{
	static const int topK = []()
	{
		const char* env = getenv("FASIM_PREALIGN_CUDA_TOPK");
		if (env == NULL || env[0] == '\0')
		{
			return 64;
		}
		int value = atoi(env);
		if (value <= 0)
		{
			return 64;
		}
		if (value > 256)
		{
			return 256;
		}
		return value;
	}();
	return topK;
}

inline uint8_t fasim_encode_base(unsigned char c)
{
	return prealign_shared_encode_base(c);
}

inline void fasim_build_query_profile(const string& query, int matchScore, int mismatchPenalty, std::vector<int16_t>& profile, int& segLenOut)
{
	prealign_shared_build_query_profile(query, matchScore, mismatchPenalty, profile, segLenOut);
}

struct mycutregion
{
	mycutregion() {};
	mycutregion(int ei, int ej) :start(ei), end(ej) {};
	int start;
	int end;
};

struct para
{
	string file1path;
	string file2path;
	string outpath;
	int corenum;
	int rule;
	int cutLength;
	int strand;
	int overlapLength;
	int minScore;
	bool detailOutput;
	bool doFastSim;
	int ntMin;
	int ntMax;
	float scoreMin;
	float minIdentity;
	float minStability;
	int penaltyT;
	int penaltyC;
	int cDistance;
	int cLength;
	// 2021-09-25 22:21:08: use this parameter to determine do fastSIM or not.
};

void getAlignment(const StripedSmithWaterman::Alignment &alignment,
	const string &ref_seq,
	const string &read_seq,
	const string &ref_seq_src,
	const int8_t* table,
	string &ref_align,
	string &read_align,
	string &ref_align_src);

inline void fasim_calc_identity_and_triscore_from_cigar(const StripedSmithWaterman::Alignment &alignment,
                                                        const string &ref_seq,
                                                        const string &read_seq,
                                                        const string &ref_seq_src,
                                                        long Para,
                                                        int penaltyT,
                                                        int penaltyC,
                                                        int ntMin,
                                                        int ntMax,
                                                        float &identityOut,
                                                        float &triScoreOut,
                                                        int &ntOut);

void convertMyTriplex(const StripedSmithWaterman::Alignment &alignment,
	std::vector<struct triplex> &triplex_list,
	const string &read_seq,
	const string &ref_seq,
	const string &ref_seq_src,
	const int8_t* table,
	long dnaStartPos,
	long rule,
	long strand,
	long Para,
	int penaltyT,
	int penaltyC,
	int ntMin,
	int ntMax,
	bool materializeAlignmentStrings);

void cutSequence(string& seq, vector<string>& seqsVec, vector<int>& seqsStartPos,
	int cutLength, int overlapLength, int &cut_num)
{
	unsigned int pos = 0;
	int tmpa = 0;
	int tmpb = 0;
	seqsVec.clear();
	seqsStartPos.clear();
	string cutSeq;
	while (pos < seq.size())
	{
		cutSeq = seq.substr(pos, cutLength);
		seqsVec.push_back(cutSeq);
		seqsStartPos.push_back(pos);
		pos += cutLength;
		pos -= overlapLength;
		tmpa++;
	}
	cut_num = tmpa;
}

bool compMyTriplexSingle(const triplex &a, const triplex &b)
{
	return a.score > b.score;
}

bool compMyTriplexMultiple(const triplex &a, const triplex &b)
{
	// need to sort myTriplexList based on score.
	if (a.stari == b.stari)
	{
		if (a.starj == b.starj)
		{
			return a.score > b.score;
		}
		else
		{
			return a.starj > b.starj;
		}
	}
	else
	{
		return a.starj > b.starj;
	}

}

bool compMyTriplexMultiple2(const triplex &a, const triplex &b)
{
	// need to sort myTriplexList based on score.
	if (a.endi == b.endi)
	{
		if (a.starj == b.starj)
		{
			return a.score > b.score;
		}
		else
		{
			return a.starj < b.starj;
		}
	}
	else
	{
		return a.starj < b.starj;
	}

}

bool sameMyTriplex(const triplex &a, const triplex &b)
{
	if (a.stari == b.stari && a.starj == b.starj && a.endi == b.endi &&
		a.endj == b.endj && a.score == b.score)
	{
		return true;
	}
	else if (b.stari >= a.stari && b.starj >= a.starj && b.endi <= a.endi &&
		b.endj <= a.endj && b.score < a.score)
	{
		return true;
	}
	else
	{
		return false;
	}

}

inline void fastSIM_extend_from_scoreinfo(StripedSmithWaterman::Aligner &aligner,
                                         StripedSmithWaterman::Filter &filter,
                                         StripedSmithWaterman::Alignment &alignment,
                                         int32_t maskLen,
                                         const string &strA,
                                         const string &strB,
                                         const string &strSrc,
                                         long dnaStartPos,
                                         const std::vector<struct StripedSmithWaterman::scoreInfo> &finalScoreInfo,
                                         vector<struct triplex> &triplex_list,
                                         long strand,
                                         long Para,
                                         long rule,
                                         int ntMin,
                                         int ntMax,
                                         int penaltyT,
                                         int penaltyC,
                                         const struct para &paraList,
                                         bool materializeAlignmentStrings = true);

void fastSIM(string& strA, string& strB, string& strSrc,
	long dnaStartPos, long min_score, float parm_M,
	float parm_I, float parm_O, float parm_E,
	vector<struct triplex>& triplex_list,
	long strand, long Para, long rule,
	int ntMin, int ntMax, int penaltyT,
	int penaltyC, struct para paraList,
	bool materializeAlignmentStrings = true)
{
	int32_t maskLen = 15;
	StripedSmithWaterman::Aligner aligner;
	StripedSmithWaterman::Filter filter;
	StripedSmithWaterman::Alignment alignment;
	std::vector<struct StripedSmithWaterman::scoreInfo> finalScoreInfo;
		bool prealigned = false;
		if (fasim_prealign_cuda_enabled_runtime() && prealign_cuda_is_built())
		{
			static thread_local bool cudaInitDone = false;
			static thread_local bool cudaInitOk = false;
			static thread_local PrealignSharedQueryCache queryCache;

			if (!cudaInitDone)
			{
			cudaInitDone = true;
			string cudaError;
			cudaInitOk = prealign_cuda_init(fasim_cuda_device_runtime(), &cudaError);
		}

			if (cudaInitOk)
			{
				string cudaError;
				if (!queryCache.prepare(fasim_cuda_device_runtime(), strA, 5, 5, 4, &cudaError))
				{
					cudaInitOk = false;
				}

				if (cudaInitOk && queryCache.query_handle().profileDevice != 0)
				{
					static std::vector<uint8_t> encodedTarget;
					prealign_shared_encode_sequence(strB, encodedTarget);

						std::vector<PreAlignCudaPeak> peaks;
						PreAlignCudaBatchResult batchResult;
						string cudaError;
						const int topK = fasim_prealign_cuda_topk_runtime();
						if (prealign_cuda_find_topk_column_maxima(queryCache.query_handle(),
						                                          encodedTarget.data(),
						                                          1,
						                                          static_cast<int>(encodedTarget.size()),
				                                          topK,
				                                          &peaks,
				                                          &batchResult,
				                                          &cudaError))
				{
					finalScoreInfo.clear();
					const int suppressBp = fasim_prealign_peak_suppress_bp_runtime();
					for (int k = 0; k < topK; ++k)
					{
						const PreAlignCudaPeak& p = peaks[static_cast<size_t>(k)];
						if (p.score <= min_score || p.position < 0)
						{
							continue;
						}
						bool suppressed = false;
						for (size_t s = 0; s < finalScoreInfo.size(); ++s)
						{
							if (abs(finalScoreInfo[s].position - p.position) < suppressBp)
							{
								suppressed = true;
								break;
							}
						}
						if (!suppressed)
						{
							finalScoreInfo.push_back(StripedSmithWaterman::scoreInfo(p.score, p.position));
						}
					}
					prealigned = true;
				}
			}
		}
	}

	if (!prealigned)
	{
		aligner.preAlign(strA.c_str(), strB.c_str(), strB.size(), filter, &alignment, maskLen, min_score, finalScoreInfo, parm_M, parm_I);
	}
	fastSIM_extend_from_scoreinfo(aligner,
	                              filter,
	                              alignment,
	                              maskLen,
	                              strA,
	                              strB,
	                              strSrc,
	                              dnaStartPos,
	                              finalScoreInfo,
	                              triplex_list,
	                              strand,
	                              Para,
	                              rule,
	                              ntMin,
	                              ntMax,
	                              penaltyT,
	                              penaltyC,
	                              paraList,
	                              materializeAlignmentStrings);
}

inline void fastSIM_extend_from_scoreinfo(StripedSmithWaterman::Aligner &aligner,
                                         StripedSmithWaterman::Filter &filter,
                                         StripedSmithWaterman::Alignment &alignment,
                                         int32_t maskLen,
                                         const string &strA,
                                         const string &strB,
                                         const string &strSrc,
                                         long dnaStartPos,
                                         const std::vector<struct StripedSmithWaterman::scoreInfo> &finalScoreInfo,
                                         vector<struct triplex> &triplex_list,
                                         long strand,
                                         long Para,
                                         long rule,
                                         int ntMin,
                                         int ntMax,
                                         int penaltyT,
                                         int penaltyC,
                                         const struct para &paraList,
                                         bool materializeAlignmentStrings)
{
	vector<struct triplex> myTriplexList;

	const int8_t nt_table[128] = {
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 0, 4, 1,	4, 4, 4, 2,	4, 4, 4, 4,	4, 4, 4, 4,
	4, 4, 4, 4,	3, 0, 4, 4,	4, 4, 4, 4,	4, 4, 4, 4
	};

	string smallSeq;
	for (int i = 0; i < finalScoreInfo.size(); i++)
	{
		float Iden = 0.6;
		int cutlength, bestcutregion;
		int myflag = 0;
		StripedSmithWaterman::Alignment bestalignment;
		bestalignment.sw_score = 0;
		while (Iden <= 1)
		{
			cutlength = (int)(finalScoreInfo[i].score + 24) / (9 * Iden - 4) + 1;
			cutlength = finalScoreInfo[i].position - cutlength + 1 > 0 ? cutlength : finalScoreInfo[i].position + 1;
			smallSeq = strB.substr(finalScoreInfo[i].position - cutlength + 1, cutlength);
			aligner.Align(strA.c_str(), smallSeq.c_str(), smallSeq.size(), filter, &alignment, maskLen);
			if (alignment.sw_score >= finalScoreInfo[i].score)
			{
				myflag = 1;
				break;
			}
			if (alignment.sw_score > bestalignment.sw_score && alignment.ref_end == cutlength - 1)
			{
				bestalignment.sw_score = alignment.sw_score;
				bestalignment.sw_score_next_best = alignment.sw_score_next_best;
				bestalignment.ref_begin = alignment.ref_begin;
				bestalignment.ref_end = alignment.ref_end;
				bestalignment.query_begin = alignment.query_begin;
				bestalignment.query_end = alignment.query_end;
				bestalignment.ref_end_next_best = alignment.ref_end_next_best;
				bestalignment.mismatches = alignment.mismatches;
				bestalignment.cigar_string = alignment.cigar_string;
				bestalignment.cigar = alignment.cigar;
				bestcutregion = cutlength;
				myflag = 2;
			}
			Iden += 0.1;
		}
		if (myflag == 2)
		{
			alignment.sw_score = bestalignment.sw_score;
			alignment.sw_score_next_best = bestalignment.sw_score_next_best;
			alignment.ref_begin = bestalignment.ref_begin;
			alignment.ref_end = bestalignment.ref_end;
			alignment.query_begin = bestalignment.query_begin;
			alignment.query_end = bestalignment.query_end;
			alignment.ref_end_next_best = bestalignment.ref_end_next_best;
			alignment.mismatches = bestalignment.mismatches;
			alignment.cigar_string = bestalignment.cigar_string;
			alignment.cigar = bestalignment.cigar;
			cutlength = bestcutregion;
		}
		bestalignment.Clear();
		if (alignment.sw_score != 0)
		{
			alignment.ref_begin = alignment.ref_begin + finalScoreInfo[i].position - cutlength + 1;
			alignment.ref_end = alignment.ref_end + finalScoreInfo[i].position - cutlength + 1;
			convertMyTriplex(alignment,
			                 myTriplexList,
			                 strA,
			                 strB,
			                 strSrc,
			                 nt_table,
			                 dnaStartPos,
			                 rule,
			                 strand,
			                 Para,
			                 penaltyT,
			                 penaltyC,
			                 ntMin,
			                 ntMax,
			                 materializeAlignmentStrings);
		}
	}
	std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple);
	myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
	std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexMultiple2);
	myTriplexList.erase(std::unique(myTriplexList.begin(), myTriplexList.end(), sameMyTriplex), myTriplexList.end());
	std::sort(myTriplexList.begin(), myTriplexList.end(), compMyTriplexSingle);
	for (int i = 0; i < (myTriplexList.size() > N ? N : myTriplexList.size()); i++)
	{
		triplex atr = myTriplexList[i];
		if (atr.identity >= paraList.minIdentity && atr.tri_score >= paraList.minStability && atr.nt >= ntMin)
		{
			triplex_list.push_back(atr);
		}
	}
}

inline void fasim_calc_identity_and_triscore_from_cigar(const StripedSmithWaterman::Alignment &alignment,
                                                        const string &ref_seq,
                                                        const string &read_seq,
                                                        const string &ref_seq_src,
                                                        long Para,
                                                        int penaltyT,
                                                        int penaltyC,
                                                        int ntMin,
                                                        int ntMax,
                                                        float &identityOut,
                                                        float &triScoreOut,
                                                        int &ntOut)
{
	int match = 0;
	int mis_match = 0;
	int nt = 0;

	float tri_score = 0.0f;
	float hashvalue = 0.0f;
	float prescore = 0.0f;
	char prechar = 0;
	char curchar = 0;

	int32_t q = alignment.ref_begin;
	int32_t p = alignment.query_begin;

	for (size_t cLoop = 0; cLoop < alignment.cigar.size(); ++cLoop)
	{
		const uint32_t cigarInt = alignment.cigar[cLoop];
		const char letter = cigar_int_to_op(cigarInt);
		const uint32_t length = cigar_int_to_len(cigarInt);
		for (uint32_t i = 0; i < length; ++i)
		{
			char refc = 0;
			char refc_src = 0;
			char readc = 0;
			bool ref_gap = false;

			if (letter == 'I')
			{
				refc = '-';
				refc_src = '-';
				readc = read_seq[static_cast<size_t>(p)];
				++p;
				ref_gap = true;
			}
			else if (letter == 'D')
			{
				refc = ref_seq[static_cast<size_t>(q)];
				refc_src = ref_seq_src[static_cast<size_t>(q)];
				++q;
				readc = '-';
			}
			else
			{
				refc = ref_seq[static_cast<size_t>(q)];
				refc_src = ref_seq_src[static_cast<size_t>(q)];
				++q;
				readc = read_seq[static_cast<size_t>(p)];
				++p;
			}

			++nt;
			if (refc == readc)
			{
				++match;
			}
			else
			{
				++mis_match;
			}

			curchar = (refc == '-') ? '-' : refc_src;
			hashvalue = triplex_score(curchar, readc, static_cast<int>(Para));

			if ((curchar == prechar) && curchar == 'T')
			{
				tri_score = tri_score - prescore + static_cast<float>(penaltyT);
				hashvalue = static_cast<float>(penaltyT);
			}
			if ((curchar == prechar) && curchar == 'C')
			{
				tri_score = tri_score - prescore + static_cast<float>(penaltyC);
				hashvalue = static_cast<float>(penaltyC);
			}
			prescore = hashvalue;
			if (!ref_gap)
			{
				prechar = curchar;
			}
			tri_score += hashvalue;
		}
	}

	ntOut = nt;
	identityOut = (match + mis_match) ? (static_cast<float>(100 * match) / static_cast<float>(match + mis_match)) : 0.0f;
	if (nt > 0 && nt >= ntMin && nt <= ntMax)
	{
		triScoreOut = tri_score / static_cast<float>(nt);
	}
	else
	{
		triScoreOut = 0.0f;
	}
}

void convertMyTriplex(const StripedSmithWaterman::Alignment &alignment,
	std::vector<struct triplex> &triplex_list,
	const string &read_seq,
	const string &ref_seq,
	const string &ref_seq_src,
	const int8_t* table,
	long dnaStartPos,
	long rule,
	long strand,
	long Para,
	int penaltyT,
	int penaltyC,
	int ntMin,
	int ntMax,
	bool materializeAlignmentStrings)
{
	int nt = 0;
	float identity = 0.0f;
	float tri_score = 0.0f;
	fasim_calc_identity_and_triscore_from_cigar(alignment,
	                                            ref_seq,
	                                            read_seq,
	                                            ref_seq_src,
	                                            Para,
	                                            penaltyT,
	                                            penaltyC,
	                                            ntMin,
	                                            ntMax,
	                                            identity,
	                                            tri_score,
	                                            nt);

	string read_align;
	string ref_align_src;
	if (materializeAlignmentStrings)
	{
		string ref_align;
		getAlignment(alignment, ref_seq, read_seq, ref_seq_src, table, ref_align, read_align, ref_align_src);
	}

	int refStart;
	int refEnd;
	if ((Para > 0 && strand == 1) || (Para < 0 && strand == 0))
	{
		refStart = static_cast<int>(ref_seq.size()) - alignment.ref_end - 1;
		refEnd = static_cast<int>(ref_seq.size()) - alignment.ref_begin - 1;
	}
	else
	{
		refStart = alignment.ref_begin + 1;
		refEnd = alignment.ref_end + 1;
	}

	const float score = static_cast<float>(alignment.sw_score);
	struct triplex fullTriplex;
	fullTriplex = triplex(alignment.query_begin + 1, alignment.query_end + 1,
	                      refStart + dnaStartPos, refEnd + dnaStartPos,
	                      strand, Para, rule, nt, score, identity, tri_score,
	                      read_align, ref_align_src, 0, 0, 0, 0, 0, 0, "");
	if (nt >= ntMin)
	{
		triplex_list.push_back(fullTriplex);
	}
}

void getAlignment(const StripedSmithWaterman::Alignment &alignment,
	const string &ref_seq,
	const string &read_seq,
	const string &ref_seq_src,
	const int8_t* table,
	string &ref_align,
	string &read_align,
	string &ref_align_src)
{
	// Use this function to get alignment of two sequences.
	int cLoop;
	std::vector<uint32_t> tmpCigar;
	for (cLoop = 0; cLoop < alignment.cigar.size(); cLoop++)
	{
		tmpCigar.push_back(alignment.cigar[cLoop]);
	}
	if (tmpCigar.size() > 0)
	{
		// begin to generate alignment.
		int32_t c = 0, left = 0, e = 0, qb = alignment.ref_begin, pb = alignment.query_begin;//need to CHECK
		uint32_t i;
		uint32_t j;
		while (e < tmpCigar.size() || left > 0)
		{
			int32_t count = 0;
			int32_t q = qb;
			int32_t p = pb;
			//fprintf(stdout, "Target: %8d		", q + 1);
			// DEBUG.
			//e = y + 1;
			for (c = e; c < tmpCigar.size(); ++c)
			{
				char letter = cigar_int_to_op(tmpCigar[c]);
				uint32_t length = cigar_int_to_len(tmpCigar[c]);
				uint32_t l = (count == 0 && left > 0) ? left : length;
				for (i = 0; i < l; ++i)
				{
					if (letter == 'I')
					{
						//fprintf(stdout, "-");
						ref_align = ref_align + "-";
						ref_align_src = ref_align_src + '-';
					}
					else
					{
						//fprintf(stdout, "%c", ref_seq[q]);
						ref_align = ref_align + ref_seq[q];
						ref_align_src = ref_align_src + ref_seq_src[q];
						++q;
					}
					++count;
					if (count == 60) goto step2;
				}
			}//for c = e.

		step2:
			//fprintf(stdout, "		%d\n										", q);
			q = qb;
			count = 0;
			for (c = e; c < tmpCigar.size(); ++c)
			{
				char letter = cigar_int_to_op(tmpCigar[c]);
				uint32_t length = cigar_int_to_len(tmpCigar[c]);
				uint32_t l = (count == 0 && left > 0) ? left : length;
				for (i = 0; i < l; ++i)
				{
					if (letter == 'M')
						//if (letter == '=')
					{
						if (table[(int)ref_seq[q]] == table[(int)read_seq[p]])
						{
							//fprintf(stdout, "|");
						}
						else
						{
							//fprintf(stdout, "*");
						}
						++q;
						++p;
					}
					else
					{
						//fprintf(stdout, "*");
						if (letter == 'I')
						{
							++p;
						}
						else
						{
							++q;
						}
					}
					++count;
					if (count == 60)
					{
						qb = q;
						goto step3;
					}
				}
			}// for c = e.
		step3:
			p = pb;
			//fprintf(stdout, "\nQuery:	%8d		", p + 1);
			count = 0;
			for (c = e; c < tmpCigar.size(); ++c)
			{
				char letter = cigar_int_to_op(tmpCigar[c]);
				uint32_t length = cigar_int_to_len(tmpCigar[c]);
				uint32_t l = (count == 0 && left > 0) ? left : length;
				for (i = 0; i < l; i++)
				{
					if (letter == 'D')
					{
						//fprintf(stdout, "-");
						read_align = read_align + "-";
					}
					else
					{
						//fprintf(stdout, "%c", read_seq[p]);
						read_align = read_align + read_seq[p];
						++p;
					}
					++count;
					if (count == 60)
					{
						pb = p;
						left = l - i - 1;
						e = (left == 0) ? (c + 1) : c;
						goto end;

					}
				}
			}// for c = e.
			e = c;
			left = 0;
		end:
			//fprintf(stdout, "		%d\n\n", p);
			j = 0;
			//2021-09-16 23:04:55: we don't need to print alignment, we 
			// just need to get alignment sequence.
			//cout << ref_align << " is ref_align" << endl;
			//cout << read_align << " is read_align" << endl;
		}
	}
}
