#include "exact_sim_task_rerun_replay.h"

#include <algorithm>
#include <atomic>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <thread>
#include <unordered_map>

using namespace std;

struct ReplayManifestRow
{
  string tileFilename;
  string taskKey;
  string dnaFastaPath;
  string rnaFastaPath;
  string replayWindowsPath;
  size_t fragmentIndex;
  long fragmentStartInSeq;
  long fragmentEndInSeq;
  long reverseMode;
  long parallelMode;
  string strand;
  int rule;
  int minScore;
};

struct ReplayTaskResult
{
  string outputText;
  string error;
};

static inline vector<string> splitTabLine(const string &line)
{
  vector<string> values;
  size_t start = 0;
  while(true)
  {
    const size_t pos = line.find('\t',start);
    if(pos == string::npos)
    {
      values.push_back(line.substr(start));
      break;
    }
    values.push_back(line.substr(start,pos - start));
    start = pos + 1;
  }
  return values;
}

static inline long parseLongValue(const string &value,const string &fieldName)
{
  char *end = NULL;
  const long parsed = strtol(value.c_str(),&end,10);
  if(end == value.c_str() || (end != NULL && *end != '\0'))
  {
    throw runtime_error("invalid integer for " + fieldName + ": " + value);
  }
  return parsed;
}

static inline string loadFastaSequence(const string &path)
{
  ifstream in(path.c_str());
  if(!in.is_open())
  {
    throw runtime_error("failed to open FASTA: " + path);
  }

  string line;
  string sequence;
  while(getline(in,line))
  {
    if(!line.empty() && line[line.size() - 1] == '\r')
    {
      line.erase(line.size() - 1);
    }
    if(line.empty() || line[0] == '>')
    {
      continue;
    }
    sequence += line;
  }
  return sequence;
}

static inline set<string> loadTaskListTsv(const string &path)
{
  ifstream in(path.c_str());
  if(!in.is_open())
  {
    throw runtime_error("failed to open task list TSV: " + path);
  }

  string line;
  if(!getline(in,line))
  {
    return set<string>();
  }
  const vector<string> header = splitTabLine(line);
  int taskKeyColumn = -1;
  for(size_t i = 0; i < header.size(); ++i)
  {
    if(header[i] == "task_key")
    {
      taskKeyColumn = static_cast<int>(i);
      break;
    }
  }
  if(taskKeyColumn < 0)
  {
    throw runtime_error("task list TSV missing required column: task_key");
  }

  set<string> taskKeys;
  while(getline(in,line))
  {
    if(!line.empty() && line[line.size() - 1] == '\r')
    {
      line.erase(line.size() - 1);
    }
    if(line.empty())
    {
      continue;
    }
    const vector<string> values = splitTabLine(line);
    if(static_cast<size_t>(taskKeyColumn) >= values.size())
    {
      continue;
    }
    if(!values[static_cast<size_t>(taskKeyColumn)].empty())
    {
      taskKeys.insert(values[static_cast<size_t>(taskKeyColumn)]);
    }
  }
  return taskKeys;
}

static inline string resolveManifestRelativePath(const string &manifestDir,const string &rawPath)
{
  if(rawPath.empty())
  {
    return rawPath;
  }
  if(rawPath[0] == '/')
  {
    return rawPath;
  }
  return manifestDir + "/" + rawPath;
}

static inline vector<ReplayManifestRow> loadManifestRows(const string &manifestPath,
                                                         const set<string> &tileFilters,
                                                         const set<string> &taskFilters)
{
  ifstream in(manifestPath.c_str());
  if(!in.is_open())
  {
    throw runtime_error("failed to open manifest: " + manifestPath);
  }

  const size_t lastSlash = manifestPath.find_last_of('/');
  const string manifestDir = lastSlash == string::npos ? "." : manifestPath.substr(0,lastSlash);

  string line;
  if(!getline(in,line))
  {
    return vector<ReplayManifestRow>();
  }
  const vector<string> header = splitTabLine(line);
  unordered_map<string,size_t> indexByName;
  for(size_t i = 0; i < header.size(); ++i)
  {
    indexByName[header[i]] = i;
  }

  const char *requiredColumns[] = {
    "tile_filename",
    "task_key",
    "dna_fasta_path",
    "rna_fasta_path",
    "replay_windows_tsv",
    "fragment_index",
    "fragment_start_in_seq",
    "fragment_end_in_seq",
    "reverse_mode",
    "parallel_mode",
    "strand",
    "rule",
    "min_score",
  };
  for(size_t i = 0; i < sizeof(requiredColumns) / sizeof(requiredColumns[0]); ++i)
  {
    if(indexByName.find(requiredColumns[i]) == indexByName.end())
    {
      throw runtime_error("manifest missing required column: " + string(requiredColumns[i]));
    }
  }

  vector<ReplayManifestRow> rows;
  while(getline(in,line))
  {
    if(!line.empty() && line[line.size() - 1] == '\r')
    {
      line.erase(line.size() - 1);
    }
    if(line.empty())
    {
      continue;
    }
    const vector<string> values = splitTabLine(line);
    auto field = [&](const string &name) -> string
    {
      const unordered_map<string,size_t>::const_iterator found = indexByName.find(name);
      if(found == indexByName.end() || found->second >= values.size())
      {
        return "";
      }
      return values[found->second];
    };

    ReplayManifestRow row;
    row.tileFilename = field("tile_filename");
    row.taskKey = field("task_key");
    if(!tileFilters.empty() && tileFilters.find(row.tileFilename) == tileFilters.end())
    {
      continue;
    }
    if(!taskFilters.empty() && taskFilters.find(row.taskKey) == taskFilters.end())
    {
      continue;
    }
    row.dnaFastaPath = resolveManifestRelativePath(manifestDir,field("dna_fasta_path"));
    row.rnaFastaPath = resolveManifestRelativePath(manifestDir,field("rna_fasta_path"));
    row.replayWindowsPath = resolveManifestRelativePath(manifestDir,field("replay_windows_tsv"));
    row.fragmentIndex = static_cast<size_t>(parseLongValue(field("fragment_index"),"fragment_index"));
    row.fragmentStartInSeq = parseLongValue(field("fragment_start_in_seq"),"fragment_start_in_seq");
    row.fragmentEndInSeq = parseLongValue(field("fragment_end_in_seq"),"fragment_end_in_seq");
    row.reverseMode = parseLongValue(field("reverse_mode"),"reverse_mode");
    row.parallelMode = parseLongValue(field("parallel_mode"),"parallel_mode");
    row.strand = field("strand");
    row.rule = static_cast<int>(parseLongValue(field("rule"),"rule"));
    row.minScore = static_cast<int>(parseLongValue(field("min_score"),"min_score"));
    rows.push_back(row);
  }
  return rows;
}

static inline vector<ExactSimRefineWindow> loadReplayWindows(const string &path,const string &taskKey)
{
  ifstream in(path.c_str());
  if(!in.is_open())
  {
    throw runtime_error("failed to open replay windows TSV: " + path);
  }

  string line;
  if(!getline(in,line))
  {
    return vector<ExactSimRefineWindow>();
  }
  const vector<string> header = splitTabLine(line);
  unordered_map<string,size_t> indexByName;
  for(size_t i = 0; i < header.size(); ++i)
  {
    indexByName[header[i]] = i;
  }

  const char *requiredColumns[] = {
    "task_key",
    "window_start_in_fragment",
    "window_end_in_fragment",
  };
  for(size_t i = 0; i < sizeof(requiredColumns) / sizeof(requiredColumns[0]); ++i)
  {
    if(indexByName.find(requiredColumns[i]) == indexByName.end())
    {
      throw runtime_error("replay windows missing required column: " + string(requiredColumns[i]));
    }
  }

  vector<ExactSimRefineWindow> windows;
  while(getline(in,line))
  {
    if(!line.empty() && line[line.size() - 1] == '\r')
    {
      line.erase(line.size() - 1);
    }
    if(line.empty())
    {
      continue;
    }
    const vector<string> values = splitTabLine(line);
    const string rowTaskKey = values[indexByName["task_key"]];
    if(rowTaskKey != taskKey)
    {
      continue;
    }
    const int startInFragment = static_cast<int>(
      parseLongValue(values[indexByName["window_start_in_fragment"]],"window_start_in_fragment"));
    const int endInFragment = static_cast<int>(
      parseLongValue(values[indexByName["window_end_in_fragment"]],"window_end_in_fragment"));
    windows.push_back(ExactSimRefineWindow(startInFragment,endInFragment));
  }
  return windows;
}

static inline string renderReplayTaskOutput(const ReplayManifestRow &row,
                                            const unordered_map<string,string> &fastaCache,
                                            const ExactSimConfig &exactSimConfig,
                                            const ExactSimTaskRerunReplayConfig &replayConfig)
{
  const unordered_map<string,string>::const_iterator dnaFound = fastaCache.find(row.dnaFastaPath);
  if(dnaFound == fastaCache.end())
  {
    throw runtime_error("DNA FASTA not preloaded for task: " + row.taskKey);
  }
  const unordered_map<string,string>::const_iterator rnaFound = fastaCache.find(row.rnaFastaPath);
  if(rnaFound == fastaCache.end())
  {
    throw runtime_error("RNA FASTA not preloaded for task: " + row.taskKey);
  }

  const string &dnaSequence = dnaFound->second;
  const string &cachedRnaSequence = rnaFound->second;
  string rnaSequence = cachedRnaSequence;
  if(row.fragmentStartInSeq < 1 || row.fragmentEndInSeq < row.fragmentStartInSeq)
  {
    throw runtime_error("invalid fragment span for task: " + row.taskKey);
  }
  const size_t fragmentStart = static_cast<size_t>(row.fragmentStartInSeq - 1);
  const size_t fragmentLength = static_cast<size_t>(row.fragmentEndInSeq - row.fragmentStartInSeq + 1);
  if(fragmentStart + fragmentLength > dnaSequence.size())
  {
    throw runtime_error("fragment span exceeds DNA length for task: " + row.taskKey);
  }

  const string fragmentSequence = dnaSequence.substr(fragmentStart,fragmentLength);
  vector<ExactSimTaskSpec> tasks;
  appendExactSimTask(tasks,
                     row.fragmentIndex,
                     fragmentSequence,
                     row.fragmentStartInSeq - 1,
                     row.reverseMode,
                     row.parallelMode,
                     row.rule);
  if(tasks.empty())
  {
    throw runtime_error("failed to build replay task for: " + row.taskKey);
  }

  vector<ExactSimRefineWindow> windows = loadReplayWindows(row.replayWindowsPath,row.taskKey);
  if(windows.empty())
  {
    throw runtime_error("replay windows TSV contained no windows for task: " + row.taskKey);
  }

  vector<struct triplex> triplexList;
  runExactReferenceSIMTwoStageDeferredWithMinScore(rnaSequence,
                                                   tasks[0].transformedSequence,
                                                   fragmentSequence,
                                                   tasks[0].dnaStartPos,
                                                   tasks[0].reverseMode,
                                                   tasks[0].parallelMode,
                                                   tasks[0].rule,
                                                   row.minScore,
                                                   exactSimConfig,
                                                   replayConfig.ntMin,
                                                   replayConfig.ntMax,
                                                   replayConfig.penaltyT,
                                                   replayConfig.penaltyC,
                                                   windows,
                                                   triplexList,
                                                   NULL);
  exactSimTaskRerunFilterTriplexListInPlace(triplexList,replayConfig);

  ostringstream out;
  for(size_t triplexIndex = 0; triplexIndex < triplexList.size(); ++triplexIndex)
  {
    exactSimTaskRerunWriteTaskOutputRow(out,row.taskKey,triplexList[triplexIndex],1,1);
  }
  return out.str();
}

int main(int argc,char **argv)
{
  string corpusManifestPath;
  string outputDirPath;
  set<string> tileFilters;
  set<string> taskFilters;
  vector<string> taskListPaths;
  int threads = 1;

  for(int i = 1; i < argc; ++i)
  {
    const string arg = argv[i];
    if(arg == "--corpus-manifest" && i + 1 < argc)
    {
      corpusManifestPath = argv[++i];
      continue;
    }
    if(arg == "--output-dir" && i + 1 < argc)
    {
      outputDirPath = argv[++i];
      continue;
    }
    if(arg == "--tile" && i + 1 < argc)
    {
      tileFilters.insert(argv[++i]);
      continue;
    }
    if(arg == "--task-key" && i + 1 < argc)
    {
      taskFilters.insert(argv[++i]);
      continue;
    }
    if(arg == "--task-list-tsv" && i + 1 < argc)
    {
      taskListPaths.push_back(argv[++i]);
      continue;
    }
    if(arg == "--threads" && i + 1 < argc)
    {
      threads = static_cast<int>(parseLongValue(argv[++i],"threads"));
      continue;
    }
    if(arg == "--help" || arg == "-h")
    {
      cout<<"Usage: "<<argv[0]<<" --corpus-manifest <path> --output-dir <dir> [--tile <tile_filename>] [--task-key <task_key>] [--task-list-tsv <path>] [--threads <n>]"<<endl;
      return 0;
    }
    throw runtime_error("unknown argument: " + arg);
  }

  if(corpusManifestPath.empty() || outputDirPath.empty())
  {
    throw runtime_error("--corpus-manifest and --output-dir are required");
  }
  if(threads <= 0)
  {
    throw runtime_error("--threads must be > 0");
  }
  for(size_t i = 0; i < taskListPaths.size(); ++i)
  {
    const set<string> loaded = loadTaskListTsv(taskListPaths[i]);
    taskFilters.insert(loaded.begin(),loaded.end());
  }

  const vector<ReplayManifestRow> manifestRows = loadManifestRows(corpusManifestPath,tileFilters,taskFilters);
  const string mkdirCommand = "mkdir -p '" + outputDirPath + "'";
  if(system(mkdirCommand.c_str()) != 0)
  {
    throw runtime_error("failed to create output directory: " + outputDirPath);
  }

  ExactSimConfig exactSimConfig;
  ExactSimTaskRerunReplayConfig replayConfig;
  unordered_map<string,string> fastaCache;
  vector<string> tileOrder;
  unordered_map<string, vector<ReplayManifestRow> > rowsByTile;

  for(size_t i = 0; i < manifestRows.size(); ++i)
  {
    const ReplayManifestRow &row = manifestRows[i];
    if(fastaCache.find(row.dnaFastaPath) == fastaCache.end())
    {
      fastaCache[row.dnaFastaPath] = loadFastaSequence(row.dnaFastaPath);
    }
    if(fastaCache.find(row.rnaFastaPath) == fastaCache.end())
    {
      fastaCache[row.rnaFastaPath] = loadFastaSequence(row.rnaFastaPath);
    }
    if(rowsByTile.find(row.tileFilename) == rowsByTile.end())
    {
      tileOrder.push_back(row.tileFilename);
    }
    rowsByTile[row.tileFilename].push_back(row);
  }

  for(size_t tileIndex = 0; tileIndex < tileOrder.size(); ++tileIndex)
  {
    const string &tileFilename = tileOrder[tileIndex];
    const string outputPath = outputDirPath + "/" + tileFilename;
    ofstream out(outputPath.c_str(),ios::trunc);
    if(!out.is_open())
    {
      throw runtime_error("failed to open replay output: " + outputPath);
    }
    exactSimTaskRerunWriteTaskOutputHeader(out);

    const vector<ReplayManifestRow> &tileRows = rowsByTile[tileFilename];
    vector<ReplayTaskResult> taskResults(tileRows.size());
    if(threads == 1 || tileRows.size() <= 1)
    {
      for(size_t rowIndex = 0; rowIndex < tileRows.size(); ++rowIndex)
      {
        try
        {
          taskResults[rowIndex].outputText =
            renderReplayTaskOutput(tileRows[rowIndex],fastaCache,exactSimConfig,replayConfig);
        }
        catch(const exception &ex)
        {
          taskResults[rowIndex].error = ex.what();
        }
      }
    }
    else
    {
      atomic<size_t> nextRowIndex(0);
      const size_t workerCount = std::min(static_cast<size_t>(threads),tileRows.size());
      vector<thread> workers;
      workers.reserve(workerCount);
      for(size_t workerIndex = 0; workerIndex < workerCount; ++workerIndex)
      {
        workers.push_back(thread([&]()
        {
          while(true)
          {
            const size_t rowIndex = nextRowIndex.fetch_add(1);
            if(rowIndex >= tileRows.size())
            {
              break;
            }
            try
            {
              taskResults[rowIndex].outputText =
                renderReplayTaskOutput(tileRows[rowIndex],fastaCache,exactSimConfig,replayConfig);
            }
            catch(const exception &ex)
            {
              taskResults[rowIndex].error = ex.what();
            }
          }
        }));
      }
      for(size_t workerIndex = 0; workerIndex < workers.size(); ++workerIndex)
      {
        workers[workerIndex].join();
      }
    }

    for(size_t rowIndex = 0; rowIndex < taskResults.size(); ++rowIndex)
    {
      if(!taskResults[rowIndex].error.empty())
      {
        throw runtime_error(taskResults[rowIndex].error);
      }
      out<<taskResults[rowIndex].outputText;
    }
  }
  return 0;
}
