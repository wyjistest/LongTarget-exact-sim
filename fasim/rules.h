#include<iostream>
#include<stdio.h>
#include<string>
#include<stdlib.h>
#include<vector>
#include<ctype.h>
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
string transferString(const string &seq1, int strand, int Para, int rule);
string transferStringTableDriven(const string &seq1, int strand, int Para, int rule);
string transferStringTableOptIn(const string &seq1, int strand, int Para, int rule);
void reverseSeq(string &seq);
void complement(string &seq);
void complement(string &seq)
{
	string compSeq;
	compSeq.reserve(seq.size());
	for (size_t i = 0; i < seq.size(); i++)
	{
		switch (seq[i])
		{
		case 'A':
		case 'a':
			compSeq += 'T';
			break;
		case 'C':
		case 'c':
			compSeq += 'G';
			break;
		case 'G':
		case 'g':
			compSeq += 'C';
			break;
		case 'T':
		case 't':
			compSeq += 'A';
			break;
		case 'N':
		case 'n':
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

static inline bool fasim_transfer_string_table_requested_runtime()
{
	static const bool enabled = []()
	{
		const char *env = getenv("FASIM_TRANSFERSTRING_TABLE");
		if (env != NULL && env[0] != '\0')
		{
			return env[0] != '0';
		}
		const char *top5PresetEnv = getenv("FASIM_TOP5_GASAL2_GPU_SCOREINFO");
		if (top5PresetEnv == NULL || top5PresetEnv[0] == '\0')
		{
			return false;
		}
		return top5PresetEnv[0] != '0';
	}();
	return enabled;
}

static inline bool fasim_transfer_string_table_validate_enabled_runtime()
{
	static const bool enabled = []()
	{
		const char *env = getenv("FASIM_TRANSFERSTRING_TABLE_VALIDATE");
		if (env == NULL || env[0] == '\0')
		{
			return false;
		}
		return env[0] != '0';
	}();
	return enabled;
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

static inline void fasim_transfer_build_lookup_table(const char *ruleSeq, char table[256])
{
	for (int i = 0; i < 256; ++i)
	{
		table[i] = 'N';
	}
	table[static_cast<unsigned char>(ruleSeq[0])] = ruleSeq[5];
	table[static_cast<unsigned char>(ruleSeq[1])] = ruleSeq[6];
	table[static_cast<unsigned char>(ruleSeq[2])] = ruleSeq[7];
	table[static_cast<unsigned char>(ruleSeq[3])] = ruleSeq[8];
	table[static_cast<unsigned char>(ruleSeq[4])] = ruleSeq[9];
	table[static_cast<unsigned char>(tolower(ruleSeq[0]))] = ruleSeq[5];
	table[static_cast<unsigned char>(tolower(ruleSeq[1]))] = ruleSeq[6];
	table[static_cast<unsigned char>(tolower(ruleSeq[2]))] = ruleSeq[7];
	table[static_cast<unsigned char>(tolower(ruleSeq[3]))] = ruleSeq[8];
	table[static_cast<unsigned char>(tolower(ruleSeq[4]))] = ruleSeq[9];
}

static inline int fasim_transfer_rule_table_index(int strand, int Para, int rule)
{
	if (Para >= 0)
	{
		if (rule < 1 || rule > 6)
		{
			return -1;
		}
		return (strand == 0 ? 0 : 6) + (rule - 1);
	}
	if (rule < 1 || rule > 18)
	{
		return -1;
	}
	return (strand == 1 ? 12 : 30) + (rule - 1);
}

static inline const char *fasim_transfer_rule_by_index(int index)
{
	static const char *rules[] = {
		PARARULE1, PARARULE2, PARARULE3, PARARULE4, PARARULE5, PARARULE6,
		PARARULE1REV, PARARULE2REV, PARARULE3REV, PARARULE4REV, PARARULE5REV, PARARULE6REV,
		ANTIRULE1, ANTIRULE2, ANTIRULE3, ANTIRULE4, ANTIRULE5, ANTIRULE6,
		ANTIRULE7, ANTIRULE8, ANTIRULE9, ANTIRULE10, ANTIRULE11, ANTIRULE12,
		ANTIRULE13, ANTIRULE14, ANTIRULE15, ANTIRULE16, ANTIRULE17, ANTIRULE18,
		ANTIRULE1REV, ANTIRULE2REV, ANTIRULE3REV, ANTIRULE4REV, ANTIRULE5REV, ANTIRULE6REV,
		ANTIRULE7REV, ANTIRULE8REV, ANTIRULE9REV, ANTIRULE10REV, ANTIRULE11REV, ANTIRULE12REV,
		ANTIRULE13REV, ANTIRULE14REV, ANTIRULE15REV, ANTIRULE16REV, ANTIRULE17REV, ANTIRULE18REV,
	};
	return rules[index];
}

static inline const char *fasim_transfer_cached_lookup_table(int strand, int Para, int rule)
{
	const int index = fasim_transfer_rule_table_index(strand, Para, rule);
	if (index < 0)
	{
		return NULL;
	}

	struct TableCache
	{
		TableCache()
		{
			for (int i = 0; i < 48; ++i)
			{
				fasim_transfer_build_lookup_table(
					fasim_transfer_rule_by_index(i),
					tables[i]);
			}
		}

		char tables[48][256];
	};

	static const TableCache cache;
	return cache.tables[index];
}

string transferStringTableDriven(const string &seq1, int strand, int Para, int rule)
{
	const char *table = fasim_transfer_cached_lookup_table(strand, Para, rule);
	if (table == NULL)
	{
		exit(1);
	}

	string out;
	out.resize(seq1.size());
	for (size_t i = 0; i < seq1.size(); i++)
	{
		out[i] = table[static_cast<unsigned char>(seq1[i])];
	}
	if (out.size() != seq1.size())
	{
		exit(1);
	}
	return out;
}

string transferStringTableOptIn(const string &seq1, int strand, int Para, int rule)
{
	if (!fasim_transfer_string_table_requested_runtime())
	{
		return transferString(seq1, strand, Para, rule);
	}

	string tableSeq = transferStringTableDriven(seq1, strand, Para, rule);
	if (fasim_transfer_string_table_validate_enabled_runtime())
	{
		string legacySeq = transferString(seq1, strand, Para, rule);
		if (tableSeq != legacySeq)
		{
			return legacySeq;
		}
	}
	return tableSeq;
}

string transferString(const string &seq1, int strand, int Para, int rule)
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
	for (i = 0; i < seq1.size(); i++)
	{
		const char base = static_cast<char>(toupper(static_cast<unsigned char>(seq1[i])));
		if (base == tmp[0])
		{
			tmpSeq = tmpSeq + tmp[5];
		}
		else if (base == tmp[1])
		{
			tmpSeq = tmpSeq + tmp[6];
		}
		else if (base == tmp[2])
		{
			tmpSeq = tmpSeq + tmp[7];
		}
		else if (base == tmp[3])
		{
			tmpSeq = tmpSeq + tmp[8];
		}
		else if (base == tmp[4])
		{
			tmpSeq = tmpSeq + tmp[9];
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
