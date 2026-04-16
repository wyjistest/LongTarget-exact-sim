#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "../sim.h"

namespace
{

static bool expect_true(bool value, const char *label)
{
    if (value)
    {
        return true;
    }
    std::cerr << label << ": expected true, got false\n";
    return false;
}

static bool expect_equal_size(size_t actual, size_t expected, const char *label)
{
    if (actual == expected)
    {
        return true;
    }
    std::cerr << label << ": expected " << expected << ", got " << actual << "\n";
    return false;
}

static bool read_text_file(const std::string &path, std::string &out)
{
    std::ifstream input(path.c_str(), std::ios::in | std::ios::binary);
    if (!input)
    {
        return false;
    }
    std::stringstream buffer;
    buffer << input.rdbuf();
    out = buffer.str();
    return input.good() || input.eof();
}

static std::vector<std::string> split_lines(const std::string &text)
{
    std::vector<std::string> lines;
    std::stringstream stream(text);
    std::string line;
    while (std::getline(stream, line))
    {
        if (!line.empty() && line[line.size() - 1] == '\r')
        {
            line.erase(line.size() - 1);
        }
        lines.push_back(line);
    }
    return lines;
}

static std::vector<SimScanCudaInitialRunSummary> make_summaries()
{
    std::vector<SimScanCudaInitialRunSummary> summaries;
    summaries.push_back(SimScanCudaInitialRunSummary{17, packSimCoord(1, 1), 3, 2, 4, 4});
    summaries.push_back(SimScanCudaInitialRunSummary{13, packSimCoord(1, 2), 1, 4, 6, 5});
    summaries.push_back(SimScanCudaInitialRunSummary{8, packSimCoord(2, 1), 2, 1, 4, 1});
    summaries.push_back(SimScanCudaInitialRunSummary{16, packSimCoord(3, 3), 3, 3, 3, 3});
    summaries.push_back(SimScanCudaInitialRunSummary{11, packSimCoord(1, 2), 4, 0, 7, 2});
    return summaries;
}

static void apply_capture_case(const std::vector<SimScanCudaInitialRunSummary> &summaries)
{
    SimKernelContext context(64, 128);
    initializeSimKernel(1.0f, -1.0f, 1.0f, 1.0f, context);
    applySimCudaInitialRunSummariesToContext(summaries,
                                             static_cast<uint64_t>(summaries.size() * 3),
                                             context,
                                             false);
}

} // namespace

int main(int argc, char **argv)
{
    if (argc != 2)
    {
        std::cerr << "Usage: " << argv[0] << " <manifest-only|manifest-progress|case-list>\n";
        return 1;
    }

    const std::string mode(argv[1]);
    const std::vector<SimScanCudaInitialRunSummary> summaries = make_summaries();
    bool ok = true;

    setenv("LONGTARGET_SIM_CUDA_LOCATE_MODE", "safe_workset", 1);

    if (mode == "manifest-only")
    {
        const char *manifestPath = getenv("LONGTARGET_SIM_INITIAL_HOST_MERGE_MANIFEST_PATH");
        ok = expect_true(manifestPath != NULL && manifestPath[0] != '\0', "manifest path configured") && ok;
        apply_capture_case(summaries);
        simInitialHostMergeManifestCaptureFinalizeForCurrentRun();

        std::string manifestText;
        ok = expect_true(read_text_file(manifestPath, manifestText), "manifest file written") && ok;
        const std::vector<std::string> lines = split_lines(manifestText);
        ok = expect_equal_size(lines.size(), 2, "manifest line count") && ok;
        if (lines.size() >= 2)
        {
            ok = expect_true(lines[0].find("case_id") == 0, "manifest header present") && ok;
            ok = expect_true(lines[1].find("case-00000001\t") == 0, "manifest row uses case-00000001") && ok;
        }
    }
    else if (mode == "manifest-progress")
    {
        const char *manifestPath = getenv("LONGTARGET_SIM_INITIAL_HOST_MERGE_MANIFEST_PATH");
        ok = expect_true(manifestPath != NULL && manifestPath[0] != '\0', "manifest path configured") && ok;

        simInitialHostMergeManifestCaptureBeginIfNeeded();

        std::string initialManifestText;
        ok = expect_true(read_text_file(manifestPath, initialManifestText), "manifest file eagerly created") && ok;
        const std::vector<std::string> initialLines = split_lines(initialManifestText);
        ok = expect_equal_size(initialLines.size(), 1, "manifest eager header line count") && ok;
        if (!initialLines.empty())
        {
            ok = expect_true(initialLines[0].find("case_id") == 0, "manifest eager header present") && ok;
        }

        apply_capture_case(summaries);
        apply_capture_case(summaries);
        simInitialHostMergeManifestCaptureFinalizeForCurrentRun();

        std::string manifestText;
        ok = expect_true(read_text_file(manifestPath, manifestText), "manifest file written after progress run") && ok;
        const std::vector<std::string> lines = split_lines(manifestText);
        ok = expect_equal_size(lines.size(), 3, "manifest progress line count") && ok;
        if (lines.size() >= 3)
        {
            ok = expect_true(lines[1].find("case-00000001\t") == 0, "manifest progress first case id") && ok;
            ok = expect_true(lines[2].find("case-00000002\t") == 0, "manifest progress second case id") && ok;
        }
    }
    else if (mode == "case-list")
    {
        const char *corpusDir = getenv("LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_DIR");
        ok = expect_true(corpusDir != NULL && corpusDir[0] != '\0', "corpus dir configured") && ok;
        apply_capture_case(summaries);
        apply_capture_case(summaries);

        std::vector<std::string> listedCases;
        std::string error;
        ok = expect_true(listSimInitialHostMergeCorpusCases(corpusDir, listedCases, &error),
                         error.empty() ? "listSimInitialHostMergeCorpusCases" : error.c_str()) &&
             ok;
        ok = expect_equal_size(listedCases.size(), 1, "selected dump case count") && ok;
        if (!listedCases.empty())
        {
            ok = expect_true(listedCases[0] == "case-00000002", "selected dump case id") && ok;
        }
    }
    else
    {
        std::cerr << "Unknown mode: " << mode << "\n";
        return 1;
    }

    if (!ok)
    {
        return 1;
    }
    std::cout << "ok\n";
    return 0;
}
