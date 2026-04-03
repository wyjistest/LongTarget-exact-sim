#include <cstdint>
#include <iostream>
#include <vector>

#include "../cuda/prealign_shared.h"

namespace
{

static bool expect_equal_uint8(uint8_t actual, uint8_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << static_cast<int>(expected) << ", got " << static_cast<int>(actual) << "\n";
    return false;
}

static bool expect_equal_int16(int16_t actual, int16_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

} // namespace

int main()
{
    bool ok = true;

    ok = expect_equal_uint8(prealign_shared_encode_base(static_cast<unsigned char>('A')), 0, "encode A") && ok;
    ok = expect_equal_uint8(prealign_shared_encode_base(static_cast<unsigned char>('c')), 1, "encode c") && ok;
    ok = expect_equal_uint8(prealign_shared_encode_base(static_cast<unsigned char>('G')), 2, "encode G") && ok;
    ok = expect_equal_uint8(prealign_shared_encode_base(static_cast<unsigned char>('t')), 3, "encode t") && ok;
    ok = expect_equal_uint8(prealign_shared_encode_base(static_cast<unsigned char>('N')), 4, "encode N") && ok;

    std::vector<uint8_t> encoded;
    prealign_shared_encode_sequence("AcgTNx", encoded);
    ok = (encoded.size() == 6u) && ok;
    ok = expect_equal_uint8(encoded[0], 0, "encoded[0]") && ok;
    ok = expect_equal_uint8(encoded[1], 1, "encoded[1]") && ok;
    ok = expect_equal_uint8(encoded[2], 2, "encoded[2]") && ok;
    ok = expect_equal_uint8(encoded[3], 3, "encoded[3]") && ok;
    ok = expect_equal_uint8(encoded[4], 4, "encoded[4]") && ok;
    ok = expect_equal_uint8(encoded[5], 4, "encoded[5]") && ok;

    std::vector<int16_t> profile;
    int segLen = 0;
    prealign_shared_build_query_profile("ACTN", 5, 4, profile, segLen);
    if (segLen != 1)
    {
        std::cerr << "segLen: expected 1, got " << segLen << "\n";
        ok = false;
    }
    if (profile.size() != 5u * 1u * 32u)
    {
        std::cerr << "profile size: expected 160, got " << profile.size() << "\n";
        ok = false;
    }

    const size_t stride = 32u;
    ok = expect_equal_int16(profile[0u * stride + 0u], 5, "A row lane0") && ok;
    ok = expect_equal_int16(profile[1u * stride + 1u], 5, "C row lane1") && ok;
    ok = expect_equal_int16(profile[3u * stride + 2u], 5, "T row lane2") && ok;
    ok = expect_equal_int16(profile[0u * stride + 3u], -4, "A row lane3 mismatch") && ok;
    ok = expect_equal_int16(profile[4u * stride + 3u], -4, "N row lane3 mismatch") && ok;

    if (!ok)
    {
        return 1;
    }

    std::cout << "ok\n";
    return 0;
}
