#ifndef LONGTARGET_EXACT_SIM_TASK_RERUN_REPLAY_H
#define LONGTARGET_EXACT_SIM_TASK_RERUN_REPLAY_H

#include <ostream>
#include <sstream>
#include <vector>

#include "exact_sim.h"

struct ExactFragmentInfo
{
  ExactFragmentInfo():dnaStartPos(0),skip(false) {}
  ExactFragmentInfo(const string &s1,long n1,bool n2):sequence(s1),dnaStartPos(n1),skip(n2) {}
  string sequence;
  long dnaStartPos;
  bool skip;
};

struct ExactSimTaskSpec
{
  ExactSimTaskSpec():fragmentIndex(0),dnaStartPos(0),reverseMode(0),parallelMode(0),rule(0) {}
  ExactSimTaskSpec(size_t n1,long n2,long n3,long n4,int n5,const string &s1):
    fragmentIndex(n1),dnaStartPos(n2),reverseMode(n3),parallelMode(n4),rule(n5),transformedSequence(s1) {}
  size_t fragmentIndex;
  long dnaStartPos;
  long reverseMode;
  long parallelMode;
  int rule;
  string transformedSequence;
};

struct ExactSimTaskRerunReplayConfig
{
  ExactSimTaskRerunReplayConfig():
    ntMin(20),
    ntMax(100000),
    scoreMin(0.0f),
    minIdentity(60.0f),
    minStability(1.0f),
    penaltyT(-1000),
    penaltyC(0) {}

  int ntMin;
  int ntMax;
  float scoreMin;
  float minIdentity;
  float minStability;
  int penaltyT;
  int penaltyC;
};

inline string exactSimTaskStrandLabel(long reverseMode,long parallelMode)
{
  if(reverseMode == 0 && parallelMode == 1)
  {
    return "ParaPlus";
  }
  if(reverseMode == 1 && parallelMode == 1)
  {
    return "ParaMinus";
  }
  if(reverseMode == 1 && parallelMode == -1)
  {
    return "AntiMinus";
  }
  if(reverseMode == 0 && parallelMode == -1)
  {
    return "AntiPlus";
  }
  return "";
}

inline string exactSimTaskRerunTaskKey(const ExactSimTaskSpec &task,size_t fragmentLength)
{
  const long fragmentStart = task.dnaStartPos + 1;
  const long fragmentEnd = task.dnaStartPos + static_cast<long>(fragmentLength);
  ostringstream out;
  out<<task.fragmentIndex<<"\t"
     <<fragmentStart<<"\t"
     <<fragmentEnd<<"\t"
     <<task.reverseMode<<"\t"
     <<task.parallelMode<<"\t"
     <<exactSimTaskStrandLabel(task.reverseMode,task.parallelMode)<<"\t"
     <<task.rule;
  return out.str();
}

inline string exactSimTaskRerunSafeTaskKey(const string &rawTaskKey)
{
  string safeTaskKey = rawTaskKey;
  for(size_t charIndex = 0; charIndex < safeTaskKey.size(); ++charIndex)
  {
    if(safeTaskKey[charIndex] == '\t')
    {
      safeTaskKey[charIndex] = '|';
    }
    else if(safeTaskKey[charIndex] == '\n' || safeTaskKey[charIndex] == '\r')
    {
      safeTaskKey[charIndex] = ' ';
    }
  }
  return safeTaskKey;
}

inline void appendExactSimTask(vector<ExactSimTaskSpec> &tasks,
                               size_t fragmentIndex,
                               const string &fragmentSequence,
                               long dnaStartPos,
                               long reverseMode,
                               long parallelMode,
                               int rule)
{
  string transformedSequence = transferString(fragmentSequence,reverseMode,parallelMode,rule);
  if(reverseMode == 1)
  {
    reverseSeq(transformedSequence);
  }
  tasks.push_back(ExactSimTaskSpec(fragmentIndex,dnaStartPos,reverseMode,parallelMode,rule,transformedSequence));
}

inline void appendExactSimTaskRange(vector<ExactSimTaskSpec> &tasks,
                                    size_t fragmentIndex,
                                    const string &fragmentSequence,
                                    long dnaStartPos,
                                    long reverseMode,
                                    long parallelMode,
                                    int firstRule,
                                    int lastRule)
{
  for(int rule = firstRule; rule <= lastRule; ++rule)
  {
    appendExactSimTask(tasks,fragmentIndex,fragmentSequence,dnaStartPos,reverseMode,parallelMode,rule);
  }
}

inline void exactSimTaskRerunFilterTriplexListInPlace(vector<struct triplex> &triplexList,
                                                      const ExactSimTaskRerunReplayConfig &config)
{
  size_t writeIndex = 0;
  for(size_t readIndex = 0; readIndex < triplexList.size(); ++readIndex)
  {
    const triplex &candidate = triplexList[readIndex];
    if(candidate.score>=config.scoreMin&&candidate.identity>=config.minIdentity&&candidate.tri_score>=config.minStability)
    {
      if(writeIndex != readIndex)
      {
        triplexList[writeIndex] = candidate;
      }
      ++writeIndex;
    }
  }
  triplexList.resize(writeIndex);
}

inline void exactSimTaskRerunWriteTaskOutputHeader(ostream &out)
{
  out<<"task_key\t"
     <<"selected\t"
     <<"effective\t"
     <<"Chr\t"
     <<"StartInGenome\t"
     <<"EndInGenome\t"
     <<"Strand\t"
     <<"Rule\t"
     <<"QueryStart\t"
     <<"QueryEnd\t"
     <<"StartInSeq\t"
     <<"EndInSeq\t"
     <<"Direction\t"
     <<"Score\t"
     <<"Nt(bp)\t"
     <<"MeanIdentity(%)\t"
     <<"MeanStability"
     <<endl;
}

inline void exactSimTaskRerunWriteTaskOutputRow(ostream &out,
                                                const string &taskKey,
                                                const triplex &atr,
                                                uint64_t selected = 1,
                                                uint64_t effective = 1)
{
  const bool forward = atr.starj < atr.endj;
  const long genomeStart = forward ? atr.starj : atr.endj;
  const long genomeEnd = forward ? atr.endj : atr.starj;
  out<<exactSimTaskRerunSafeTaskKey(taskKey)<<"\t"
     <<selected<<"\t"
     <<effective<<"\t"
     <<""<<"\t"
     <<genomeStart<<"\t"
     <<genomeEnd<<"\t"
     <<exactSimTaskStrandLabel(atr.reverse,atr.strand)<<"\t"
     <<atr.rule<<"\t"
     <<atr.stari<<"\t"
     <<atr.endi<<"\t"
     <<atr.starj<<"\t"
     <<atr.endj<<"\t"
     <<(forward ? "R" : "L")<<"\t"
     <<atr.score<<"\t"
     <<atr.nt<<"\t"
     <<atr.identity<<"\t"
     <<atr.tri_score
     <<endl;
}

#endif
