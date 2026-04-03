#include <cmath>
#include <cstdlib>
#include <iostream>
#include <string>

#include "../fasim/fastsim.h"

namespace
{

static void calc_identity_and_triscore_from_strings(const StripedSmithWaterman::Alignment &alignment,
                                                    const std::string &ref_seq,
                                                    const std::string &read_seq,
                                                    const std::string &ref_seq_src,
                                                    const int8_t *table,
                                                    long Para,
                                                    int penaltyT,
                                                    int penaltyC,
                                                    int ntMin,
                                                    int ntMax,
                                                    float &identityOut,
                                                    float &triScoreOut,
                                                    int &ntOut)
{
    std::string ref_align;
    std::string read_align;
    std::string ref_align_src;
    getAlignment(alignment, ref_seq, read_seq, ref_seq_src, table, ref_align, read_align, ref_align_src);

    int match = 0;
    int mis_match = 0;
    const int nt = static_cast<int>(ref_align.size());
    for (int i = 0; i < nt; ++i)
    {
        if (ref_align[static_cast<size_t>(i)] == read_align[static_cast<size_t>(i)])
        {
            ++match;
        }
        else
        {
            ++mis_match;
        }
    }

    identityOut = (match + mis_match) ? (static_cast<float>(100 * match) / static_cast<float>(match + mis_match)) : 0.0f;
    ntOut = nt;

    float tri_score = 0.0f;
    if (nt >= ntMin && nt <= ntMax)
    {
        float hashvalue = 0.0f;
        float prescore = 0.0f;
        char prechar = 0;
        char curchar = 0;

        int j = 0;
        for (int i = 0; i < nt; ++i)
        {
            const char refc = ref_align[static_cast<size_t>(i)];
            const char readc = read_align[static_cast<size_t>(i)];
            if (refc == '-')
            {
                curchar = '-';
                hashvalue = triplex_score(curchar, readc, static_cast<int>(Para));
                ++j;
            }
            else
            {
                curchar = ref_align_src[static_cast<size_t>(j)];
                hashvalue = triplex_score(curchar, readc, static_cast<int>(Para));
                ++j;
            }

            if ((curchar == prechar) && curchar == 'T')
            {
                tri_score = tri_score - prescore + penaltyT;
                hashvalue = static_cast<float>(penaltyT);
            }
            if ((curchar == prechar) && curchar == 'C')
            {
                tri_score = tri_score - prescore + penaltyC;
                hashvalue = static_cast<float>(penaltyC);
            }
            prescore = hashvalue;
            if (refc != '-')
            {
                prechar = curchar;
            }
            tri_score += hashvalue;
        }
        tri_score = tri_score / static_cast<float>(nt);
    }

    triScoreOut = tri_score;
}

static bool nearly_equal(float a, float b, float eps = 1e-6f)
{
    return std::fabs(a - b) <= eps;
}

} // namespace

int main()
{
    // Build a deterministic alignment with mixed M/I/D ops so we exercise gap columns.
    const std::string ref_seq = "ACGTACGTA";
    const std::string read_seq = "ACGTTACTT";
    const std::string ref_seq_src = ref_seq;

    StripedSmithWaterman::Alignment alignment;
    alignment.Clear();
    alignment.sw_score = 42;
    alignment.ref_begin = 0;
    alignment.query_begin = 0;
    alignment.ref_end = static_cast<int32_t>(ref_seq.size() - 1);
    alignment.query_end = static_cast<int32_t>(read_seq.size() - 1);

    // 4M 1I 2M 1D 2M
    alignment.cigar.push_back((4u << 4) | 0u);
    alignment.cigar.push_back((1u << 4) | 1u);
    alignment.cigar.push_back((2u << 4) | 0u);
    alignment.cigar.push_back((1u << 4) | 2u);
    alignment.cigar.push_back((2u << 4) | 0u);

    int8_t table[128];
    for (int i = 0; i < 128; ++i)
    {
        table[i] = 4;
    }
    table[static_cast<int>('A')] = 0;
    table[static_cast<int>('C')] = 1;
    table[static_cast<int>('G')] = 2;
    table[static_cast<int>('T')] = 3;
    table[static_cast<int>('a')] = 0;
    table[static_cast<int>('c')] = 1;
    table[static_cast<int>('g')] = 2;
    table[static_cast<int>('t')] = 3;

    const long Para = 1;
    const int penaltyT = -6;
    const int penaltyC = -6;
    const int ntMin = 1;
    const int ntMax = 100000;

    float identity_strings = 0.0f;
    float tri_strings = 0.0f;
    int nt_strings = 0;
    calc_identity_and_triscore_from_strings(alignment,
                                            ref_seq,
                                            read_seq,
                                            ref_seq_src,
                                            table,
                                            Para,
                                            penaltyT,
                                            penaltyC,
                                            ntMin,
                                            ntMax,
                                            identity_strings,
                                            tri_strings,
                                            nt_strings);

    float identity_cigar = 0.0f;
    float tri_cigar = 0.0f;
    int nt_cigar = 0;
    fasim_calc_identity_and_triscore_from_cigar(alignment,
                                                ref_seq,
                                                read_seq,
                                                ref_seq_src,
                                                Para,
                                                penaltyT,
                                                penaltyC,
                                                ntMin,
                                                ntMax,
                                                identity_cigar,
                                                tri_cigar,
                                                nt_cigar);

    if (nt_strings != nt_cigar || !nearly_equal(identity_strings, identity_cigar) || !nearly_equal(tri_strings, tri_cigar))
    {
        std::cerr << "mismatch:\n";
        std::cerr << "  nt strings=" << nt_strings << " cigar=" << nt_cigar << "\n";
        std::cerr << "  identity strings=" << identity_strings << " cigar=" << identity_cigar << "\n";
        std::cerr << "  stability strings=" << tri_strings << " cigar=" << tri_cigar << "\n";
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
