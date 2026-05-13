#include<iostream>
#include<stdio.h>
#include<string>
#include<chrono>
#include<stdlib.h>
#include<vector>
#define PARARULE1     "ATGCNTGGTN"
#define PARARULE1REV  "ATGCNGTTGN"
#define PARARULE2     "ATGCNTGCTN"
#define PARARULE2REV  "ATGCNGTTCN"
#define PARARULE3     "ATGCNTGTTN"
#define PARARULE3REV  "ATGCNGTTTN"
#define PARARULE4     "ATGCNTGGCN"
#define PARARULE4REV  "ATGCNGTCGN"
#define PARARULE5     "ATGCNTGCCN"
#define PARARULE5REV  "ATGCNGTCCN"
#define PARARULE6     "ATGCNTGTCN"
#define PARARULE6REV  "ATGCNGTCTN"
#define ANTIRULE1     "ATGCNGTTGN"
#define ANTIRULE1REV  "ATGCNTGGTN"
#define ANTIRULE2     "ATGCNGTTCN"
#define ANTIRULE2REV  "ATGCNTGCTN"
#define ANTIRULE3     "ATGCNGTTAN"
#define ANTIRULE3REV  "ATGCNTGATN"
#define ANTIRULE4     "ATGCNGTCGN"
#define ANTIRULE4REV  "ATGCNTGGCN"
#define ANTIRULE5     "ATGCNGTCCN"
#define ANTIRULE5REV  "ATGCNTGCCN"
#define ANTIRULE6     "ATGCNGTCAN"
#define ANTIRULE6REV  "ATGCNTGACN"
#define ANTIRULE7     "ATGCNGATGN"
#define ANTIRULE7REV  "ATGCNAGGTN"
#define ANTIRULE8     "ATGCNGATCN"
#define ANTIRULE8REV  "ATGCNAGCTN"
#define ANTIRULE9     "ATGCNGATAN"
#define ANTIRULE9REV  "ATGCNAGATN"
#define ANTIRULE10    "ATGCNGACGN"
#define ANTIRULE10REV "ATGCNAGGCN"
#define ANTIRULE11    "ATGCNGACCN"
#define ANTIRULE11REV "ATGCNAGCCN"
#define ANTIRULE12    "ATGCNGACAN"
#define ANTIRULE12REV "ATGCNAGACN"
#define ANTIRULE13    "ATGCNGCTGN"
#define ANTIRULE13REV "ATGCNCGGTN"
#define ANTIRULE14    "ATGCNGCTCN"
#define ANTIRULE14REV "ATGCNCGCTN"
#define ANTIRULE15    "ATGCNGCTAN"
#define ANTIRULE15REV "ATGCNCGATN"
#define ANTIRULE16    "ATGCNGCCGN"
#define ANTIRULE16REV "ATGCNCGGCN"
#define ANTIRULE17    "ATGCNGCCCN"
#define ANTIRULE17REV "ATGCNCGCCN"
#define ANTIRULE18    "ATGCNGCCAN"
#define ANTIRULE18REV "ATGCNCGACN"

using namespace std;
string transferString(string seq1, int strand, int Para, int rule);
void reverseSeq(string &seq);
void complement(string &seq);
void complement(string &seq)
{
	string compSeq;
	int i = 0;
	for (i = 0; i < seq.size(); i++)
	{
		switch (seq[i])
		{
		case 'A':
			compSeq += 'T';
			break;
		case 'C':
			compSeq += 'G';
			break;
		case 'G':
			compSeq += 'C';
			break;
		case 'T':
			compSeq += 'A';
			break;
		case 'N':
			compSeq += 'N';
			break;
		default:
			break;
		}
	}
	seq = compSeq;
}
void reverseSeq(string &seq)
{
	int i = 0;
	string revSeq;
	reverse(seq.begin(), seq.end());
}

struct FasimTransferStringProfileStats
{
	FasimTransferStringProfileStats() :
		totalNanoseconds(0),
		ruleSelectNanoseconds(0),
		ruleMaterializeNanoseconds(0),
		convertNanoseconds(0),
		validateNanoseconds(0),
		residualNanoseconds(0),
		calls(0),
		inputBases(0),
		outputBases(0)
	{
		for (int i = 0; i < 4; ++i)
		{
			modeCalls[i] = 0;
			modeNanoseconds[i] = 0;
		}
		for (int i = 0; i < 19; ++i)
		{
			ruleCalls[i] = 0;
			ruleNanoseconds[i] = 0;
		}
	}

	unsigned long long totalNanoseconds;
	unsigned long long ruleSelectNanoseconds;
	unsigned long long ruleMaterializeNanoseconds;
	unsigned long long convertNanoseconds;
	unsigned long long validateNanoseconds;
	unsigned long long residualNanoseconds;
	unsigned long long calls;
	unsigned long long inputBases;
	unsigned long long outputBases;
	unsigned long long modeCalls[4];
	unsigned long long modeNanoseconds[4];
	unsigned long long ruleCalls[19];
	unsigned long long ruleNanoseconds[19];
};

static inline unsigned long long fasim_transfer_profile_now_nanoseconds()
{
	return static_cast<unsigned long long>(
		std::chrono::duration_cast<std::chrono::nanoseconds>(
			std::chrono::steady_clock::now().time_since_epoch()).count());
}

static inline void fasim_transfer_profile_add_elapsed(unsigned long long &slot,
                                                      unsigned long long startNanoseconds)
{
	slot += fasim_transfer_profile_now_nanoseconds() - startNanoseconds;
}

static inline int fasim_transfer_mode_index(int strand, int Para)
{
	if (Para >= 0)
	{
		return strand == 0 ? 0 : 1;
	}
	return strand == 1 ? 2 : 3;
}

static inline const char *fasim_transfer_select_rule(int strand, int Para, int rule)
{
	if (Para >= 0)
	{
		if (strand == 0)
		{
			switch (rule)
			{
			case 1: return PARARULE1;
			case 2: return PARARULE2;
			case 3: return PARARULE3;
			case 4: return PARARULE4;
			case 5: return PARARULE5;
			case 6: return PARARULE6;
			default: return NULL;
			}
		}
		switch (rule)
		{
		case 1: return PARARULE1REV;
		case 2: return PARARULE2REV;
		case 3: return PARARULE3REV;
		case 4: return PARARULE4REV;
		case 5: return PARARULE5REV;
		case 6: return PARARULE6REV;
		default: return NULL;
		}
	}
	if (strand == 1)
	{
		switch (rule)
		{
		case 1: return ANTIRULE1;
		case 2: return ANTIRULE2;
		case 3: return ANTIRULE3;
		case 4: return ANTIRULE4;
		case 5: return ANTIRULE5;
		case 6: return ANTIRULE6;
		case 7: return ANTIRULE7;
		case 8: return ANTIRULE8;
		case 9: return ANTIRULE9;
		case 10: return ANTIRULE10;
		case 11: return ANTIRULE11;
		case 12: return ANTIRULE12;
		case 13: return ANTIRULE13;
		case 14: return ANTIRULE14;
		case 15: return ANTIRULE15;
		case 16: return ANTIRULE16;
		case 17: return ANTIRULE17;
		case 18: return ANTIRULE18;
		default: return NULL;
		}
	}
	switch (rule)
	{
	case 1: return ANTIRULE1REV;
	case 2: return ANTIRULE2REV;
	case 3: return ANTIRULE3REV;
	case 4: return ANTIRULE4REV;
	case 5: return ANTIRULE5REV;
	case 6: return ANTIRULE6REV;
	case 7: return ANTIRULE7REV;
	case 8: return ANTIRULE8REV;
	case 9: return ANTIRULE9REV;
	case 10: return ANTIRULE10REV;
	case 11: return ANTIRULE11REV;
	case 12: return ANTIRULE12REV;
	case 13: return ANTIRULE13REV;
	case 14: return ANTIRULE14REV;
	case 15: return ANTIRULE15REV;
	case 16: return ANTIRULE16REV;
	case 17: return ANTIRULE17REV;
	case 18: return ANTIRULE18REV;
	default: return NULL;
	}
}

static inline unsigned long long fasim_transfer_profile_inner_nanoseconds(const FasimTransferStringProfileStats &stats)
{
	return stats.ruleSelectNanoseconds
		+ stats.ruleMaterializeNanoseconds
		+ stats.convertNanoseconds
		+ stats.validateNanoseconds;
}

string transferStringProfiled(string seq1,
                              int strand,
                              int Para,
                              int rule,
                              FasimTransferStringProfileStats *profileStats)
{
	unsigned long long profileStart = profileStats ? fasim_transfer_profile_now_nanoseconds() : 0;
	const char *tmp = fasim_transfer_select_rule(strand, Para, rule);
	if (profileStats)
	{
		fasim_transfer_profile_add_elapsed(profileStats->ruleSelectNanoseconds, profileStart);
	}
	if (tmp == NULL)
	{
		exit(1);
	}

	profileStart = profileStats ? fasim_transfer_profile_now_nanoseconds() : 0;
	string ruleSeq(tmp);
	if (profileStats)
	{
		fasim_transfer_profile_add_elapsed(profileStats->ruleMaterializeNanoseconds, profileStart);
	}

	string tmpSeq;
	profileStart = profileStats ? fasim_transfer_profile_now_nanoseconds() : 0;
	for (int i = 0; i < seq1.size(); i++)
	{
		if (seq1[i] == ruleSeq[0])
		{
			tmpSeq = tmpSeq + ruleSeq[5];
		}
		else if (seq1[i] == ruleSeq[1])
		{
			tmpSeq = tmpSeq + ruleSeq[6];
		}
		else if (seq1[i] == ruleSeq[2])
		{
			tmpSeq = tmpSeq + ruleSeq[7];
		}
		else if (seq1[i] == ruleSeq[3])
		{
			tmpSeq = tmpSeq + ruleSeq[8];
		}
		else if (seq1[i] == ruleSeq[4])
		{
			tmpSeq = tmpSeq + ruleSeq[9];
		}
		else
		{
			tmpSeq = tmpSeq + 'N';
		}
	}
	if (profileStats)
	{
		fasim_transfer_profile_add_elapsed(profileStats->convertNanoseconds, profileStart);
	}

	profileStart = profileStats ? fasim_transfer_profile_now_nanoseconds() : 0;
	if (tmpSeq.size() != seq1.size())
	{
		exit(1);
	}
	if (profileStats)
	{
		fasim_transfer_profile_add_elapsed(profileStats->validateNanoseconds, profileStart);
		++profileStats->calls;
		profileStats->inputBases += static_cast<unsigned long long>(seq1.size());
		profileStats->outputBases += static_cast<unsigned long long>(tmpSeq.size());
	}
	return tmpSeq;
}

string transferString(string seq1, int strand, int Para, int rule)
{
	const char *tmp = NULL;
	int i = 0;
	string tmpSeq;
	if (Para >= 0)
	{
		if (strand == 0)
		{
			switch (rule)
			{
			case 1:
				tmp = PARARULE1;
				break;
			case 2:
				tmp = PARARULE2;
				break;
			case 3:
				tmp = PARARULE3;
				break;
			case 4:
				tmp = PARARULE4;
				break;
			case 5:
				tmp = PARARULE5;
				break;
			case 6:
				tmp = PARARULE6;
				break;
			default:
				break;
			}
		}
		else
		{
			switch (rule)
			{
			case 1:
				tmp = PARARULE1REV;
				break;
			case 2:
				tmp = PARARULE2REV;
				break;
			case 3:
				tmp = PARARULE3REV;
				break;
			case 4:
				tmp = PARARULE4REV;
				break;
			case 5:
				tmp = PARARULE5REV;
				break;
			case 6:
				tmp = PARARULE6REV;
				break;
			default:
				break;
			}
		}
	}
	else
	{
		if (strand == 1)
		{
			switch (rule)
			{
			case 1:
				tmp = ANTIRULE1;
				break;
			case 2:
				tmp = ANTIRULE2;
				break;
			case 3:
				tmp = ANTIRULE3;
				break;
			case 4:
				tmp = ANTIRULE4;
				break;
			case 5:
				tmp = ANTIRULE5;
				break;
			case 6:
				tmp = ANTIRULE6;
				break;
			case 7:
				tmp = ANTIRULE7;
				break;
			case 8:
				tmp = ANTIRULE8;
				break;
			case 9:
				tmp = ANTIRULE9;
				break;
			case 10:
				tmp = ANTIRULE10;
				break;
			case 11:
				tmp = ANTIRULE11;
				break;
			case 12:
				tmp = ANTIRULE12;
				break;
			case 13:
				tmp = ANTIRULE13;
				break;
			case 14:
				tmp = ANTIRULE14;
				break;
			case 15:
				tmp = ANTIRULE15;
				break;
			case 16:
				tmp = ANTIRULE16;
				break;
			case 17:
				tmp = ANTIRULE17;
				break;
			case 18:
				tmp = ANTIRULE18;
				break;
			default:
				break;
			}
		}
		else
		{
			switch (rule)
			{
			case 1:
				tmp = ANTIRULE1REV;
				break;
			case 2:
				tmp = ANTIRULE2REV;
				break;
			case 3:
				tmp = ANTIRULE3REV;
				break;
			case 4:
				tmp = ANTIRULE4REV;
				break;
			case 5:
				tmp = ANTIRULE5REV;
				break;
			case 6:
				tmp = ANTIRULE6REV;
				break;
			case 7:
				tmp = ANTIRULE7REV;
				break;
			case 8:
				tmp = ANTIRULE8REV;
				break;
			case 9:
				tmp = ANTIRULE9REV;
				break;
			case 10:
				tmp = ANTIRULE10REV;
				break;
			case 11:
				tmp = ANTIRULE11REV;
				break;
			case 12:
				tmp = ANTIRULE12REV;
				break;
			case 13:
				tmp = ANTIRULE13REV;
				break;
			case 14:
				tmp = ANTIRULE14REV;
				break;
			case 15:
				tmp = ANTIRULE15REV;
				break;
			case 16:
				tmp = ANTIRULE16REV;
				break;
			case 17:
				tmp = ANTIRULE17REV;
				break;
			case 18:
				tmp = ANTIRULE18REV;
				break;
			default:
				break;
			}
		}
	}
	if (tmp == NULL)
	{
		exit(1);
	}
	string ruleSeq(tmp);
	for (i = 0; i < seq1.size(); i++)
	{
		if (seq1[i] == ruleSeq[0])
		{
			tmpSeq = tmpSeq + ruleSeq[5];
		}
		else if (seq1[i] == ruleSeq[1])
		{
			tmpSeq = tmpSeq + ruleSeq[6];
		}
		else if (seq1[i] == ruleSeq[2])
		{
			tmpSeq = tmpSeq + ruleSeq[7];
		}
		else if (seq1[i] == ruleSeq[3])
		{
			tmpSeq = tmpSeq + ruleSeq[8];
		}
		else if (seq1[i] == ruleSeq[4])
		{
			tmpSeq = tmpSeq + ruleSeq[9];
		}
		else
		{
			tmpSeq = tmpSeq + 'N';
		}
	}
	if (tmpSeq.size() != seq1.size())
	{
		exit(1);
	}
	return tmpSeq;
}
