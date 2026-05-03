#include <cstdlib>
#include <iostream>

#include "../sim.h"

namespace
{

static bool expect_equal_int(int actual, int expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool expect_equal_u64(uint64_t actual, uint64_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static SimPathWorkset make_diagonal_two_band_workset()
{
    std::vector<SimUpdateBand> bands(2);
    bands[0].rowStart = 1;
    bands[0].rowEnd = 1;
    bands[0].colStart = 1;
    bands[0].colEnd = 1;
    bands[1].rowStart = 2;
    bands[1].rowEnd = 2;
    bands[1].colStart = 2;
    bands[1].colEnd = 2;
    return makeSimPathWorksetFromBands(bands);
}

} // namespace

int main()
{
    unsetenv("LONGTARGET_SIM_CUDA_SAFE_WINDOW_EXEC_GEOMETRY");

    bool ok = true;
    ok = expect_equal_int(static_cast<int>(parseSimSafeWindowExecGeometry(NULL)),
                          static_cast<int>(SIM_SAFE_WINDOW_EXEC_GEOMETRY_COARSENED),
                          "default safe-window exec geometry") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimSafeWindowExecGeometry("coarsened")),
                          static_cast<int>(SIM_SAFE_WINDOW_EXEC_GEOMETRY_COARSENED),
                          "parse coarsened safe-window exec geometry") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimSafeWindowExecGeometry("fine")),
                          static_cast<int>(SIM_SAFE_WINDOW_EXEC_GEOMETRY_FINE),
                          "parse fine safe-window exec geometry") && ok;
    ok = expect_equal_int(static_cast<int>(parseSimSafeWindowExecGeometry("unexpected")),
                          static_cast<int>(SIM_SAFE_WINDOW_EXEC_GEOMETRY_COARSENED),
                          "invalid safe-window exec geometry falls back to coarsened") && ok;

    SimSafeWindowExecutePlan plan;
    plan.rawWorkset = make_diagonal_two_band_workset();
    plan.execWorkset = buildSimSafeWindowExecutionWorkset(plan.rawWorkset);

    ok = expect_equal_u64(plan.rawWorkset.cellCount,
                          2,
                          "raw fine workset keeps two exact cells") && ok;
    ok = expect_equal_u64(plan.execWorkset.cellCount,
                          4,
                          "coarsened workset inflates adjacent diagonal cells") && ok;
    ok = expect_equal_u64(selectSimSafeWindowExecutePlanWorkset(plan,
                                                                SIM_SAFE_WINDOW_EXEC_GEOMETRY_COARSENED).cellCount,
                          4,
                          "coarsened execution selects coarsened workset") && ok;
    ok = expect_equal_u64(selectSimSafeWindowExecutePlanWorkset(plan,
                                                                SIM_SAFE_WINDOW_EXEC_GEOMETRY_FINE).cellCount,
                          2,
                          "fine execution selects raw safe-window workset") && ok;

    if (!ok)
    {
        return 1;
    }
    std::cout << "ok\n";
    return 0;
}
