#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

#include "../fasim/ssw.h"

namespace
{

std::vector<int8_t> translate(const std::string &sequence)
{
    std::vector<int8_t> out(sequence.size(), 0);
    for (size_t i = 0; i < sequence.size(); ++i)
    {
        switch (sequence[i])
        {
        case 'A':
        case 'a':
            out[i] = 0;
            break;
        case 'C':
        case 'c':
            out[i] = 1;
            break;
        case 'G':
        case 'g':
            out[i] = 2;
            break;
        case 'T':
        case 't':
            out[i] = 3;
            break;
        default:
            out[i] = 4;
            break;
        }
    }
    return out;
}

std::string cigar_string(const s_align *alignment)
{
    if (alignment == NULL || alignment->cigar == NULL || alignment->cigarLen <= 0)
    {
        return "";
    }
    std::string out;
    for (int32_t i = 0; i < alignment->cigarLen; ++i)
    {
        out += std::to_string(cigar_int_to_len(alignment->cigar[i]));
        out.push_back(cigar_int_to_op(alignment->cigar[i]));
    }
    return out;
}

void require_equal(const char *field, int64_t lhs, int64_t rhs)
{
    if (lhs == rhs)
    {
        return;
    }
    std::cerr << field << " mismatch: " << lhs << " vs " << rhs << "\n";
    std::exit(1);
}

void require_expected_alignment(const s_align *alignment,
                                const uint16_t score,
                                const int32_t ref_begin,
                                const int32_t ref_end,
                                const int32_t read_begin,
                                const int32_t read_end,
                                const std::string &cigar)
{
    if (alignment == NULL)
    {
        std::cerr << "alignment unexpectedly null\n";
        std::exit(1);
    }
    require_equal("score1", alignment->score1, score);
    require_equal("ref_begin1", alignment->ref_begin1, ref_begin);
    require_equal("ref_end1", alignment->ref_end1, ref_end);
    require_equal("read_begin1", alignment->read_begin1, read_begin);
    require_equal("read_end1", alignment->read_end1, read_end);
    const std::string observed_cigar = cigar_string(alignment);
    if (observed_cigar != cigar)
    {
        std::cerr << "cigar mismatch: " << observed_cigar << " vs " << cigar << "\n";
        std::exit(1);
    }
}

s_align *run_alignment(const std::string &query,
                       const std::string &reference,
                       const int8_t score_size)
{
    static const int8_t matrix[] = {
        2, -2, -2, -2,
        -2, 2, -2, -2,
        -2, -2, 2, -2,
        -2, -2, -2, 2,
    };
    std::vector<int8_t> translated_query = translate(query);
    std::vector<int8_t> translated_ref = translate(reference);
    s_profile *profile = ssw_init(translated_query.data(),
                                  static_cast<int32_t>(translated_query.size()),
                                  matrix,
                                  4,
                                  score_size);
    if (profile == NULL)
    {
        std::cerr << "ssw_init returned null\n";
        std::exit(1);
    }
    s_align *alignment = ssw_align(profile,
                                   translated_ref.data(),
                                   static_cast<int32_t>(translated_ref.size()),
                                   3,
                                   1,
                                   0x0f,
                                   0,
                                   100000,
                                   static_cast<int32_t>(query.size() / 2));
    init_destroy(profile);
    return alignment;
}

std::string avx2_mode()
{
    const char *env = std::getenv("FASIM_SSW_AVX2_MODE");
    if (env == NULL || env[0] == '\0')
    {
        return "forward_only";
    }
    return env;
}

} // namespace

int main()
{
    const std::string byte_query(64, 'A');
    const std::string byte_ref(64, 'A');
    s_align *byte_alignment = run_alignment(byte_query, byte_ref, 2);
    require_expected_alignment(byte_alignment, 128, 0, 63, 0, 63, "64M");

    const std::string high_score_query(200, 'A');
    const std::string high_score_ref(200, 'A');
    s_align *word_alignment = run_alignment(high_score_query, high_score_ref, 2);
    require_expected_alignment(word_alignment, 400, 0, 199, 0, 199, "200M");
    if (word_alignment->score1 <= 255)
    {
        std::cerr << "word-path fixture did not exceed byte saturation threshold: "
                  << word_alignment->score1 << "\n";
        std::exit(1);
    }

    if (ssw_avx2_requested() != 1)
    {
        std::cerr << "AVX2 env was not observed\n";
        std::exit(1);
    }
    if (ssw_avx2_compiled() != 1)
    {
        std::cerr << "AVX2 was not compiled into this test binary\n";
        std::exit(1);
    }
    const std::string mode = avx2_mode();
    const bool expect_active = mode != "off";
    const uint64_t expected_byte_calls =
        mode == "all" ? 3 : mode == "forward_only" ? 2 : mode == "reverse_only" ? 1 : 0;
    const uint64_t expected_word_calls =
        mode == "all" ? 2 : mode == "forward_only" ? 1 : mode == "reverse_only" ? 1 : 0;
    const uint64_t expected_forward_calls =
        mode == "all" ? 3 : mode == "forward_only" ? 3 : 0;
    const uint64_t expected_reverse_calls =
        mode == "all" ? 2 : mode == "reverse_only" ? 2 : 0;

    if (ssw_avx2_active() != (expect_active ? 1 : 0))
    {
        std::cerr << "AVX2 active mismatch for mode " << mode
                  << ": " << ssw_avx2_active() << "\n";
        std::exit(1);
    }
    if (ssw_avx2_byte_calls() != expected_byte_calls ||
        ssw_avx2_word_calls() != expected_word_calls ||
        ssw_avx2_calls() != expected_byte_calls + expected_word_calls)
    {
        std::cerr << "AVX2 call distribution mismatch for mode " << mode
                  << ": calls=" << ssw_avx2_calls()
                  << " byte=" << ssw_avx2_byte_calls()
                  << " word=" << ssw_avx2_word_calls()
                  << " expected_calls=" << (expected_byte_calls + expected_word_calls)
                  << " expected_byte=" << expected_byte_calls
                  << " expected_word=" << expected_word_calls << "\n";
        std::exit(1);
    }
    if (ssw_avx2_forward_calls() != expected_forward_calls ||
        ssw_avx2_reverse_calls() != expected_reverse_calls)
    {
        std::cerr << "AVX2 forward/reverse distribution mismatch for mode " << mode
                  << ": forward=" << ssw_avx2_forward_calls()
                  << " reverse=" << ssw_avx2_reverse_calls()
                  << " expected_forward=" << expected_forward_calls
                  << " expected_reverse=" << expected_reverse_calls << "\n";
        std::exit(1);
    }
    if (ssw_avx2_fallback_calls() != 0)
    {
        std::cerr << "AVX2 fallback calls observed: " << ssw_avx2_fallback_calls() << "\n";
        std::exit(1);
    }

    align_destroy(byte_alignment);
    align_destroy(word_alignment);
    std::cout << "SSW AVX2 direct byte/word checks passed\n";
    return 0;
}
