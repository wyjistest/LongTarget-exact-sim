#include <cstdlib>
#include <cstdio>
#include <vector>

#include "../fasim/ssw.h"

bool ssw_test_exact_banded_traceback(const int8_t* ref,
                                     const int8_t* read,
                                     int32_t refLen,
                                     int32_t readLen,
                                     int32_t score,
                                     int32_t weight_gapO,
                                     int32_t weight_gapE,
                                     int32_t band_width,
                                     const int8_t* mat,
                                     int32_t n,
                                     int32_t* ref_begin_offset,
                                     int32_t* read_begin_offset,
                                     uint32_t* only_cigar);

namespace
{

void require(bool condition, const char *message)
{
    if (!condition)
    {
        fprintf(stderr, "%s\n", message);
        std::exit(1);
    }
}

} // namespace

int main()
{
    const int8_t matrix[] = {
         3, -2, -2, -2,
        -2,  3, -2, -2,
        -2, -2,  3, -2,
        -2, -2, -2,  3,
    };
    const std::vector<int8_t> reference(3, 0);
    const std::vector<int8_t> query(100, 0);
    int32_t ref_begin_offset = -1;
    int32_t read_begin_offset = -1;
    uint32_t only_cigar = 0;
    require(ssw_test_exact_banded_traceback(reference.data(), query.data(),
                                            3, 100, 1000, 2, 1, 98,
                                            matrix, 4, &ref_begin_offset,
                                            &read_begin_offset, &only_cigar),
            "bounded traceback recovery failed");
    require(ref_begin_offset == 0, "unexpected reference begin offset");
    require(read_begin_offset == 97, "unexpected query begin offset");
    require(cigar_int_to_len(only_cigar) == 3 &&
            cigar_int_to_op(only_cigar) == 'M',
            "unexpected recovered CIGAR");

    puts("SSW banded traceback regression passed");
    return 0;
}
