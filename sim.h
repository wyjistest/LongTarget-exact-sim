#include <string.h>
#include <sstream>
#include <fstream>
#include <math.h>
#include <getopt.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>
#include <map>
#include <algorithm>
#include <ctype.h>
#if defined(__has_include)
#if __has_include(<omp.h>)
#include <omp.h>
#endif
#else
#include <omp.h>
#endif
#include <list>
#include<sys/types.h>
#include<dirent.h>
#include<unistd.h>
#include<string>
#include<vector>
#include <unordered_map>
#include <atomic>
#include <chrono>
#include <limits>
#include <mutex>
#if defined(__SSE2__) || defined(__AVX2__)
#include <immintrin.h>
#endif
#include "stats.h"
#include "cuda/sim_cuda_runtime.h"
#include "cuda/sim_locate_cuda.h"
#include "cuda/sim_scan_cuda.h"
#include "cuda/sim_traceback_cuda.h"
#define K 50  
#define SIM_CANDIDATE_INDEX_CAPACITY 128
#include "rules.h"
using namespace std;
struct triplex 
{
	triplex(){};
	triplex(int n1, int n2, int n3, int n4, int n5, int n6, int n7,int n8, float f1, float f2, float f3, const string &s1, const string &s2,int w1,int w2,int w3,int w4):
	stari(n1), endi(n2), starj(n3), endj(n4), reverse(n5), strand(n6), rule(n7),nt(n8), score(f1), identity(f2), tri_score(f3), stri_align(s1), strj_align(s2), middle(w1),center(w2), motif(w3),neartriplex(w4) {};
  	int stari;
	int endi;
	int starj;
	int endj;
	int reverse;
	int strand;
	int rule;
  	int nt;
	float score;
	float identity;
	float tri_score;
	string stri_align;
	string strj_align;
	int middle;
	int center;
	int motif;
	int neartriplex;
};

typedef struct NODE
{ 
	long  SCORE;
	long  STARI;
	long  STARJ;
	long  ENDI;
	long  ENDJ;
	long  TOP;
	long  BOT;
	long  LEFT;
	long  RIGHT; 
}  vertex, *vertexptr;

typedef vertex SimCandidate;

	struct SimWorkspace;
	inline bool simDiagonalAvailable(const SimWorkspace &workspace,long rowIndex,long columnIndex);
	inline void markSimDiagonalBlocked(SimWorkspace &workspace,long rowIndex,long columnIndex);
	struct SimInitialCellEvent;

struct SimCandidateStartIndex
{
  SimCandidateStartIndex()
  {
    clear();
  }

  void clear()
  {
    memset(slotState,0,sizeof(slotState));
    memset(candidateSlot,0xff,sizeof(candidateSlot));
    tombstoneCount = 0;
  }

  unsigned char slotState[SIM_CANDIDATE_INDEX_CAPACITY];
  long startI[SIM_CANDIDATE_INDEX_CAPACITY];
  long startJ[SIM_CANDIDATE_INDEX_CAPACITY];
  int candidateIndex[SIM_CANDIDATE_INDEX_CAPACITY];
  int candidateSlot[K];
  size_t tombstoneCount;
};

struct axis
{
    axis(int n1=0, int n2=0):
        triplexnum(n1), neartriplex(n2) {};              
    int triplexnum;
    int neartriplex;
};

struct tmp_class
{
    tmp_class(){};
    tmp_class(int n1,int n2,int n3,int n4,int n5):genome_start(n1),genome_end(n2),signal_level(n3),peak(n4),row(n5) {};
    int genome_start;
    int genome_end;
    int signal_level;
    int peak;
    int row;
};
float triplex_score(char c1, char c2, int Para)
{
	if (Para>0)
	{
		if     ( c1 == 'T' && c2 == 'T' ) return 3.7;
		else if( c1 == 'A' && c2 == 'G' ) return 2.8;
		else if( c1 == 'C' && c2 == 'G' ) return 2.2;
		else if( c1 == 'C' && c2 == 'T' ) return 2.4;
		else if( c1 == 'C' && c2 == 'C' ) return 4.5;
		else if( c1 == 'G' && c2 == 'T' ) return 2.6;
		else if( c1 == 'G' && c2 == 'C' ) return 2.4;
	}
	else
	{
		if     ( c1 == 'T' && c2 == 'A' ) return 3.0;
		else if( c1 == 'T' && c2 == 'T' ) return 3.5;
		else if( c1 == 'T' && c2 == 'C' ) return 1.0;
		else if( c1 == 'A' && c2 == 'G' ) return 1.0;
		else if( c1 == 'C' && c2 == 'A' ) return 1.0;
		else if( c1 == 'C' && c2 == 'G' ) return 3.0;
		else if( c1 == 'C' && c2 == 'C' ) return 3.0;		
		else if( c1 == 'G' && c2 == 'T' ) return 2.0;		
		else if( c1 == 'G' && c2 == 'C' ) return 1.0;		
	}
	return 0;
}
long addnode(long c, long ci, long cj, long i, long j, vertex  LIST[], long *pnumnode)
{
	short found;			
	long d;
	long  most = 0;
	long  low = 0;
	found = 0;
	for ( d = 0; d < *pnumnode ; d++ )
	{
		most = d;
		if ( LIST[most].STARI == ci && LIST[most].STARJ == cj )
		{
			found = 1;
			break;
		}
	}
	if ( found )
	{
		if ( LIST[most].SCORE < c )
		{
			LIST[most].SCORE = c;
			LIST[most].ENDI = i;
			LIST[most].ENDJ = j;
		}
		if ( LIST[most].TOP > i ) LIST[most].TOP = i;
		if ( LIST[most].BOT < i ) LIST[most].BOT = i;
		if ( LIST[most].LEFT > j ) LIST[most].LEFT = j;
		if ( LIST[most].RIGHT < j ) LIST[most].RIGHT = j;
	}
	else
	{
		if( *pnumnode == K )
		{
			for ( d = 1; d < *pnumnode ; d++ )
				if ( LIST[d].SCORE < LIST[low].SCORE )
					low = d;
			most = low;
		}
		else
			most = (*pnumnode)++;
		LIST[most].SCORE = c;
		LIST[most].STARI = ci;
		LIST[most].STARJ = cj;
		LIST[most].ENDI = i;
		LIST[most].ENDJ = j;
		LIST[most].TOP = LIST[most].BOT = i;
		LIST[most].LEFT = LIST[most].RIGHT = j;
	}
	return 1;
}

int no_cross(vertex  LIST[], long numnode,long  m1,long mm,long n1,long nn,long* prl,long* pcl)
{
	long  cur;
	long i;
	for ( i = 0; i < numnode; i++ )
	{
		cur = i;
		if ( LIST[cur].STARI <= mm && LIST[cur].STARJ <= nn && LIST[cur].BOT >= m1-1 && 
		LIST[cur].RIGHT >= n1-1 && ( LIST[cur].STARI < *prl || LIST[cur].STARJ < *pcl ))
		{
			if ( LIST[cur].STARI < *prl ) *prl = LIST[cur].STARI;
			if ( LIST[cur].STARJ < *pcl ) *pcl = LIST[cur].STARJ;
			break;
		}
	}
	if ( i == numnode )
		return 1;
	else
		return 0;
}

long diff(const char *A, const char *B, long M, long N, long *pI, long *pJ, long tb, long te, long Q, long R, long **psapp, long *plast, long V[][128], SimWorkspace &workspace, long *CC,long *DD,long *RR,long *SS)
{
	long *sapp;				
	sapp=*psapp;
#define gap(k)  ((k) <= 0 ? 0 : Q+R*(k))	

#define DEL(k)				\
{ (*pI) += k;				\
  if (*plast < 0)				\
    *plast = sapp[-1] -= (k);		\
  else					\
    *plast = *sapp++ = -(k);		\
}
						
#define INS(k)				\
{ (*pJ) += k;				\
  if (*plast < 0)				\
    { sapp[-1] = (k); *sapp++ = *plast; }	\
  else					\
    *plast = *sapp++ = (k);		\
}

						
#define REP 				\
{ *plast = *sapp++ = 0; 			\
}


#define DIAG(ii, jj, x, value)				\
{ if ( simDiagonalAvailable(workspace, (ii), (jj)) )		\
    x = ( value );					\
}

	long   midi, midj, type;	
	long midc;
	long   i, j;
	long c, e, d, s;
	long t, *va;
	if (N <= 0)
	{
		if (M > 0) DEL(M)
		*psapp=sapp;
		return - gap(M);
	}
	if (M <= 1)
	{
		if (M <= 0)
		{
			INS(N);
			return - gap(N);
		}
		if (tb > te) tb = te;
		midc = - (tb + R + gap(N) );
		midj = 0;
		va = V[A[1]];
		for (j = 1; j <= N; j++)
		{
			if (simDiagonalAvailable(workspace, *pI + 1, j + (*pJ)))
			{
				c = va[B[j]] - ( gap(j-1) + gap(N-j) );
				if (c > midc)
					{ midc = c; midj = j;}
			}
		}
		if (midj == 0)
			{ INS(N) DEL(1) }
		else
		{
			if (midj > 1) INS(midj-1)
				REP

			(*pI)++; (*pJ)++;
			markSimDiagonalBlocked(workspace,*pI,*pJ);
			if (midj < N) INS(N-midj)
		}
		*psapp=sapp;
		return midc;
    }
	midi = M/2;			
	CC[0] = 0;			
	t = -Q;
	for (j = 1; j <= N; j++)
	{
		CC[j] = t = t-R;
		DD[j] = t-Q;
	}
	t = -tb;
	for (i = 1; i <= midi; i++)
	{
		s = CC[0];
		CC[0] = c = t = t-R;
		e = t-Q;
		va = V[A[i]];
		for (j = 1; j <= N; j++)
		{
			if ((c = c - Q-R) > (e = e - R)) e = c;
			if ((c = CC[j] - Q-R) > (d = DD[j] - R)) d = c;
			DIAG(i+(*pI), j+(*pJ), c, s+va[B[j]])
			if (c < d) c = d;
			if (c < e) c = e;
			s = CC[j];
			CC[j] = c;
			DD[j] = d;
		}
	}
	DD[0] = CC[0];
	RR[N] = 0;		
	t = -Q;			
	for (j = N-1; j >= 0; j--)
	{
		RR[j] = t = t-R;
		SS[j] = t-Q;
	}
	t = -te;
	for (i = M-1; i >= midi; i--)
	{
		s = RR[N];
		RR[N] = c = t = t-R;
		e = t-Q;
		va = V[A[i+1]];
		for (j = N-1; j >= 0; j--)
		{
			if ((c = c - Q-R) > (e = e - R)) e = c;
			if ((c = RR[j] - Q-R) > (d = SS[j] - R)) d = c;
			DIAG(i+1+(*pI), j+1+(*pJ), c, s+va[B[j+1]])
			if (c < d) c = d;
			if (c < e) c = e;
			s = RR[j];
			RR[j] = c;
			SS[j] = d;
		}
	}
	SS[N] = RR[N];
	midc = CC[0]+RR[0];		
	midj = 0;
	type = 1;
	for (j = 0; j <= N; j++)
		if ((c = CC[j] + RR[j]) >= midc)
			if (c > midc || CC[j] != DD[j] && RR[j] == SS[j])
				{ midc = c; midj = j; }
	for (j = N; j >= 0; j--)
		if ((c = DD[j] + SS[j] + Q) > midc)
			{ midc = c; midj = j; type = 2; }

	*psapp=sapp;
	if (type == 1)
	{
		diff(A,B,midi,midj,pI,pJ,tb,Q,Q,R,psapp,plast,V,workspace,CC,DD,RR,SS);
		diff(A+midi,B+midj,M-midi,N-midj,pI,pJ,Q,te,Q,R,psapp,plast,V,workspace,CC,DD,RR,SS);
	}
	else
	{
		diff(A,B,midi-1,midj,pI,pJ,tb,0,Q,R,psapp,plast,V,workspace,CC,DD,RR,SS);
		sapp=*psapp;
		DEL(2);
		*psapp=sapp;
		diff(A+midi+1,B+midj,M-midi-1,N-midj,pI,pJ,0,te,Q,R,psapp,plast,V,workspace,CC,DD,RR,SS);
	}
	return midc;
}

float display(const char* A, const char* B, long M, long N, long S[], long AP, long BP,string& stri_align,string& strj_align)
{
	long   i, j, f, op, start_i, start_j, match, mis_match;
	string stra, strb;
	float identity;
  (void)AP;
  (void)BP;
	stra.reserve(static_cast<size_t>(M + N));
	strb.reserve(static_cast<size_t>(M + N));
	match = mis_match = 0;
	for (i = j = 0; i < M || j < N; ) 
	{
		start_i = i;
		start_j = j;
		while (i < M && j < N && *S == 0) 
		{
			++i;
			++j;
			if (A[i] == B[j])
				++match;
			else
				++mis_match;
			stra+=A[i];
			strb+=B[j];
			S++;
		}
		if (i < M || j < N)
			if ((op = *S++) > 0)
			{
				for(f=0; f<op; f++) {stra+='-';strb+=B[++j];++mis_match;}

			}
			else
			{

				for(f=0; f<-op; f++) {strb+='-';stra+=A[++i];++mis_match;}
			}
	}
	stri_align=stra;
	strj_align=strb;
	identity=(float)(100*match)/(float)(match+mis_match);
	return identity;
}

inline void computeSimIdentityAndNtFromTracebackScript(const char* A,
                                                       const char* B,
                                                       long M,
                                                       long N,
                                                       const long* S,
                                                       float &identity,
                                                       int &nt)
{
  long i = 0;
  long j = 0;
  long match = 0;
  long mis_match = 0;
  const long *p = S;
  while(i < M || j < N)
  {
    while(i < M && j < N && *p == 0)
    {
      ++i;
      ++j;
      if(A[i] == B[j])
      {
        ++match;
      }
      else
      {
        ++mis_match;
      }
      ++p;
    }
    if(i < M || j < N)
    {
      const long op = *p++;
      if(op > 0)
      {
        j += op;
        mis_match += op;
      }
      else if(op < 0)
      {
        i += -op;
        mis_match += -op;
      }
    }
  }
  const long total = match + mis_match;
  nt = static_cast<int>(total);
  identity = (total > 0) ? (float)(100 * match) / (float)total : 0.0f;
}

inline uint64_t countSimTracebackDiagonalSteps(const long *S,long M,long N)
{
  long i = 0;
  long j = 0;
  uint64_t diagonalCount = 0;
  const long *p = S;
  while(i < M || j < N)
  {
    while(i < M && j < N && *p == 0)
    {
      ++i;
      ++j;
      ++diagonalCount;
      ++p;
    }
    if(i < M || j < N)
    {
      const long op = *p++;
      if(op > 0)
      {
        j += op;
      }
      else if(op < 0)
      {
        i += -op;
      }
    }
  }
  return diagonalCount;
}

enum SimTracebackPathSegmentKind
{
  SIM_TRACEBACK_SEGMENT_DIAGONAL = 0,
  SIM_TRACEBACK_SEGMENT_HORIZONTAL = 1,
  SIM_TRACEBACK_SEGMENT_VERTICAL = 2
};

struct SimTracebackPathSegment
{
  SimTracebackPathSegment():
    kind(SIM_TRACEBACK_SEGMENT_DIAGONAL),
    rowStart(0),
    rowEnd(0),
    colStart(0),
    colEnd(0)
  {
  }

  SimTracebackPathSegment(SimTracebackPathSegmentKind segmentKind,long row,long col):
    kind(segmentKind),
    rowStart(row),
    rowEnd(row),
    colStart(col),
    colEnd(col)
  {
  }

  SimTracebackPathSegmentKind kind;
  long rowStart;
  long rowEnd;
  long colStart;
  long colEnd;
};

struct SimTracebackPathSummary
{
  SimTracebackPathSummary():
    valid(false),
    rowStart(0),
    rowEnd(0),
    colStart(0),
    colEnd(0),
    stepCount(0)
  {
  }

  bool valid;
  long rowStart;
  long rowEnd;
  long colStart;
  long colEnd;
  uint64_t stepCount;
  vector<long> rowMinCols;
  vector<long> rowMaxCols;
  vector<SimTracebackPathSegment> segments;
};

struct SimUpdateBand
{
  SimUpdateBand():
    rowStart(0),
    rowEnd(0),
    colStart(0),
    colEnd(0)
  {
  }

  long rowStart;
  long rowEnd;
  long colStart;
  long colEnd;
};

struct SimPathWorkset
{
  SimPathWorkset():
    hasWorkset(false),
    fallbackToRect(false),
    cellCount(0)
  {
  }

  bool hasWorkset;
  bool fallbackToRect;
  uint64_t cellCount;
  vector<SimUpdateBand> bands;
};

struct SimRegionSchedulerShapeTelemetryStats
{
  SimRegionSchedulerShapeTelemetryStats():
    calls(0),
    bands(0),
    singleBandCalls(0),
    affectedStarts(0),
    cells(0),
    maxBandRows(0),
    maxBandCols(0),
    mergeableCalls(0),
    mergeableCells(0),
    estimatedLaunchReduction(0),
    rejectedRunningMin(0),
    rejectedSafeStoreEpoch(0),
    rejectedScoreMatrix(0),
    rejectedFilter(0)
  {
  }

  uint64_t calls;
  uint64_t bands;
  uint64_t singleBandCalls;
  uint64_t affectedStarts;
  uint64_t cells;
  uint64_t maxBandRows;
  uint64_t maxBandCols;
  uint64_t mergeableCalls;
  uint64_t mergeableCells;
  uint64_t estimatedLaunchReduction;
  uint64_t rejectedRunningMin;
  uint64_t rejectedSafeStoreEpoch;
  uint64_t rejectedScoreMatrix;
  uint64_t rejectedFilter;
};

struct SimCandidateStateStore
{
  SimCandidateStateStore():
    valid(false),
    states(),
    startCoordToIndex()
  {
  }

  bool valid;
  vector<SimScanCudaCandidateState> states;
  unordered_map<uint64_t,size_t> startCoordToIndex;
};

inline uint64_t simUpdateBandCellCount(const SimUpdateBand &band)
{
  if(band.rowEnd < band.rowStart || band.colEnd < band.colStart)
  {
    return 0;
  }
  return static_cast<uint64_t>(band.rowEnd - band.rowStart + 1) *
         static_cast<uint64_t>(band.colEnd - band.colStart + 1);
}

inline uint64_t simUpdateBandBoundingCellCount(long rowStart,
                                               long rowEnd,
                                               long colStart,
                                               long colEnd)
{
  if(rowEnd < rowStart || colEnd < colStart)
  {
    return 0;
  }
  return static_cast<uint64_t>(rowEnd - rowStart + 1) *
         static_cast<uint64_t>(colEnd - colStart + 1);
}

inline uint64_t simPathWorksetCellCountFromBands(const vector<SimUpdateBand> &bands)
{
  uint64_t totalCellCount = 0;
  for(size_t bandIndex = 0; bandIndex < bands.size(); ++bandIndex)
  {
    totalCellCount += simUpdateBandCellCount(bands[bandIndex]);
  }
  return totalCellCount;
}

inline SimPathWorkset makeSimPathWorksetFromBands(const vector<SimUpdateBand> &bands)
{
  SimPathWorkset workset;
  workset.bands = bands;
  workset.hasWorkset = !workset.bands.empty();
  workset.cellCount = simPathWorksetCellCountFromBands(workset.bands);
  return workset;
}

inline SimPathWorkset makeSimPathWorksetFromCudaSafeWindows(const vector<SimScanCudaSafeWindow> &windows)
{
  vector<SimUpdateBand> bands;
  bands.reserve(windows.size());
  for(size_t windowIndex = 0; windowIndex < windows.size(); ++windowIndex)
  {
    SimUpdateBand band;
    band.rowStart = windows[windowIndex].rowStart;
    band.rowEnd = windows[windowIndex].rowEnd;
    band.colStart = windows[windowIndex].colStart;
    band.colEnd = windows[windowIndex].colEnd;
    bands.push_back(band);
  }
  return makeSimPathWorksetFromBands(bands);
}

inline vector<uint64_t> makeSortedUniqueSimStartCoords(const vector<uint64_t> &startCoords)
{
  vector<uint64_t> uniqueCoords = startCoords;
  sort(uniqueCoords.begin(),uniqueCoords.end());
  uniqueCoords.erase(unique(uniqueCoords.begin(),uniqueCoords.end()),uniqueCoords.end());
  return uniqueCoords;
}

inline bool simCandidateStateIntersectsPathSummary(const SimScanCudaCandidateState &candidate,
                                                   const SimTracebackPathSummary &summary)
{
  if(!summary.valid)
  {
    return false;
  }
  const long overlapRowStart = std::max<long>(candidate.startI, summary.rowStart);
  const long overlapRowEnd = std::min<long>(candidate.bot, summary.rowEnd);
  if(overlapRowEnd < overlapRowStart)
  {
    return false;
  }
  for(long row = overlapRowStart; row <= overlapRowEnd; ++row)
  {
    const size_t rowIndex = static_cast<size_t>(row - summary.rowStart);
    if(rowIndex >= summary.rowMinCols.size())
    {
      break;
    }
    if(summary.rowMinCols[rowIndex] <= candidate.right &&
       summary.rowMaxCols[rowIndex] >= candidate.startJ)
    {
      return true;
    }
  }
  return false;
}

inline bool clampSimCandidateStateBounds(const SimScanCudaCandidateState &candidate,
                                         long queryLength,
                                         long targetLength,
                                         long &rowStart,
                                         long &rowEnd,
                                         long &colStart,
                                         long &colEnd)
{
  if(candidate.startI < 1 ||
     candidate.startJ < 1 ||
     candidate.bot < candidate.startI ||
     candidate.right < candidate.startJ)
  {
    return false;
  }

  rowStart = std::max(1L, std::min<long>(candidate.startI, queryLength));
  rowEnd = std::max(rowStart, std::min<long>(candidate.bot, queryLength));
  colStart = std::max(1L, std::min<long>(candidate.startJ, targetLength));
  colEnd = std::max(colStart, std::min<long>(candidate.right, targetLength));
  return true;
}

inline void insertSimSafeWorksetInterval(vector< pair<long,long> > &intervals,
                                         long colStart,
                                         long colEnd)
{
  pair<long,long> merged(colStart,colEnd);
  vector< pair<long,long> >::iterator it = intervals.begin();
  while(it != intervals.end() && it->second + 1 < merged.first)
  {
    ++it;
  }
  while(it != intervals.end() && it->first <= merged.second + 1)
  {
    if(it->first < merged.first) merged.first = it->first;
    if(it->second > merged.second) merged.second = it->second;
    it = intervals.erase(it);
  }
  intervals.insert(it,merged);
}

inline bool simCandidateStateIntersectsSafeWorksetIntervals(const SimScanCudaCandidateState &candidate,
                                                            long queryLength,
                                                            long targetLength,
                                                            const vector< vector< pair<long,long> > > &rowIntervals)
{
  long rowStart = 0;
  long rowEnd = 0;
  long colStart = 0;
  long colEnd = 0;
  if(!clampSimCandidateStateBounds(candidate,queryLength,targetLength,rowStart,rowEnd,colStart,colEnd))
  {
    return false;
  }

  for(long row = rowStart; row <= rowEnd; ++row)
  {
    const vector< pair<long,long> > &intervals = rowIntervals[static_cast<size_t>(row)];
    for(size_t intervalIndex = 0; intervalIndex < intervals.size(); ++intervalIndex)
    {
      const pair<long,long> &interval = intervals[intervalIndex];
      if(interval.first > colEnd)
      {
        break;
      }
      if(interval.second >= colStart)
      {
        return true;
      }
    }
  }
  return false;
}

inline SimPathWorkset buildSimSafeWorksetFromCandidateStates(long queryLength,
                                                             long targetLength,
                                                             const SimTracebackPathSummary &summary,
                                                             const vector<SimScanCudaCandidateState> &candidateStates,
                                                             vector<uint64_t> *affectedStartCoords = NULL)
{
  SimPathWorkset workset;
  if(affectedStartCoords != NULL)
  {
    affectedStartCoords->clear();
  }
  if(!summary.valid || queryLength <= 0 || targetLength <= 0)
  {
    return workset;
  }

  vector< vector< pair<long,long> > > rowIntervals(static_cast<size_t>(queryLength + 1));
  vector<unsigned char> included(candidateStates.size(),0);
  const auto includeCandidate = [&](size_t candidateIndex) -> bool
  {
    const SimScanCudaCandidateState &candidate = candidateStates[candidateIndex];
    long rowStart = 0;
    long rowEnd = 0;
    long colStart = 0;
    long colEnd = 0;
    if(!clampSimCandidateStateBounds(candidate,queryLength,targetLength,rowStart,rowEnd,colStart,colEnd))
    {
      return false;
    }
    if(included[candidateIndex] != 0)
    {
      return false;
    }
    included[candidateIndex] = 1;
    if(affectedStartCoords != NULL)
    {
      affectedStartCoords->push_back(simScanCudaCandidateStateStartCoord(candidate));
    }
    for(long row = rowStart; row <= rowEnd; ++row)
    {
      insertSimSafeWorksetInterval(rowIntervals[static_cast<size_t>(row)],colStart,colEnd);
    }
    return true;
  };

  for(size_t candidateIndex = 0; candidateIndex < candidateStates.size(); ++candidateIndex)
  {
    if(!simCandidateStateIntersectsPathSummary(candidateStates[candidateIndex],summary))
    {
      continue;
    }
    includeCandidate(candidateIndex);
  }

  const vector< vector< pair<long,long> > > seedRowIntervals = rowIntervals;
  for(size_t candidateIndex = 0; candidateIndex < candidateStates.size(); ++candidateIndex)
  {
    if(included[candidateIndex] != 0)
    {
      continue;
    }
    if(!simCandidateStateIntersectsSafeWorksetIntervals(candidateStates[candidateIndex],
                                                        queryLength,
                                                        targetLength,
                                                        seedRowIntervals))
    {
      continue;
    }
    includeCandidate(candidateIndex);
  }

  vector< pair<long,long> > activeIntervals;
  vector<SimUpdateBand> activeBands;
  for(long row = 1; row <= queryLength; ++row)
  {
    vector< pair<long,long> > &intervals = rowIntervals[static_cast<size_t>(row)];
    if(intervals == activeIntervals)
    {
      for(size_t intervalIndex = 0; intervalIndex < activeBands.size(); ++intervalIndex)
      {
        activeBands[intervalIndex].rowEnd = row;
      }
      continue;
    }

    for(size_t bandIndex = 0; bandIndex < activeBands.size(); ++bandIndex)
    {
      workset.bands.push_back(activeBands[bandIndex]);
    }
    activeBands.clear();
    activeIntervals = intervals;
    if(intervals.empty())
    {
      continue;
    }
    for(size_t intervalIndex = 0; intervalIndex < intervals.size(); ++intervalIndex)
    {
      SimUpdateBand band;
      band.rowStart = row;
      band.rowEnd = row;
      band.colStart = intervals[intervalIndex].first;
      band.colEnd = intervals[intervalIndex].second;
      activeBands.push_back(band);
    }
  }
  for(size_t bandIndex = 0; bandIndex < activeBands.size(); ++bandIndex)
  {
    workset.bands.push_back(activeBands[bandIndex]);
  }

  if(!workset.bands.empty())
  {
    workset.hasWorkset = true;
    workset.cellCount = simPathWorksetCellCountFromBands(workset.bands);
  }
  return workset;
}

inline vector<SimScanCudaSafeWindow> buildSimSafeWindowsFromSparseRowIntervals(
  long queryLength,
  const vector<int> &rowOffsets,
  const vector<SimScanCudaColumnInterval> &intervals)
{
  vector<SimScanCudaSafeWindow> windows;
  if(queryLength <= 0 || rowOffsets.size() != static_cast<size_t>(queryLength + 2))
  {
    return windows;
  }

  vector<SimScanCudaSafeWindow> activeWindows;

  for(long row = 1; row <= queryLength; ++row)
  {
    const int intervalStart = rowOffsets[static_cast<size_t>(row)];
    const int intervalEnd = rowOffsets[static_cast<size_t>(row + 1)];
    vector<SimScanCudaColumnInterval> rowIntervals;
    if(intervalStart >= 0 && intervalEnd >= intervalStart)
    {
      rowIntervals.reserve(static_cast<size_t>(intervalEnd - intervalStart));
      for(int intervalIndex = intervalStart; intervalIndex < intervalEnd; ++intervalIndex)
      {
        if(static_cast<size_t>(intervalIndex) >= intervals.size())
        {
          rowIntervals.clear();
          break;
        }
        rowIntervals.push_back(intervals[static_cast<size_t>(intervalIndex)]);
      }
    }

    vector<SimScanCudaSafeWindow> nextActiveWindows;
    nextActiveWindows.reserve(max(activeWindows.size(),rowIntervals.size()));
    size_t activeIndex = 0;
    size_t intervalIndex = 0;
    while(activeIndex < activeWindows.size() && intervalIndex < rowIntervals.size())
    {
      const SimScanCudaSafeWindow &activeWindow = activeWindows[activeIndex];
      const SimScanCudaColumnInterval &interval = rowIntervals[intervalIndex];
      if(activeWindow.colStart == interval.colStart &&
         activeWindow.colEnd == interval.colEnd)
      {
        SimScanCudaSafeWindow extendedWindow = activeWindow;
        extendedWindow.rowEnd = static_cast<int>(row);
        nextActiveWindows.push_back(extendedWindow);
        ++activeIndex;
        ++intervalIndex;
        continue;
      }
      if(activeWindow.colStart < interval.colStart ||
         (activeWindow.colStart == interval.colStart && activeWindow.colEnd < interval.colEnd))
      {
        windows.push_back(activeWindow);
        ++activeIndex;
        continue;
      }
      nextActiveWindows.push_back(
        SimScanCudaSafeWindow(static_cast<int>(row),
                              static_cast<int>(row),
                              interval.colStart,
                              interval.colEnd));
      ++intervalIndex;
    }
    while(activeIndex < activeWindows.size())
    {
      windows.push_back(activeWindows[activeIndex]);
      ++activeIndex;
    }
    while(intervalIndex < rowIntervals.size())
    {
      nextActiveWindows.push_back(
        SimScanCudaSafeWindow(static_cast<int>(row),
                              static_cast<int>(row),
                              rowIntervals[intervalIndex].colStart,
                              rowIntervals[intervalIndex].colEnd));
      ++intervalIndex;
    }
    activeWindows.swap(nextActiveWindows);
  }

  windows.insert(windows.end(),activeWindows.begin(),activeWindows.end());
  sort(windows.begin(),windows.end(),[](const SimScanCudaSafeWindow &lhs,
                                        const SimScanCudaSafeWindow &rhs)
  {
    if(lhs.rowStart != rhs.rowStart) return lhs.rowStart < rhs.rowStart;
    if(lhs.colStart != rhs.colStart) return lhs.colStart < rhs.colStart;
    if(lhs.rowEnd != rhs.rowEnd) return lhs.rowEnd < rhs.rowEnd;
    return lhs.colEnd < rhs.colEnd;
  });
  return windows;
}

inline void clearSimCudaPersistentSafeStoreHandle(SimCudaPersistentSafeStoreHandle &handle)
{
  handle = SimCudaPersistentSafeStoreHandle();
}

inline void moveSimCudaPersistentSafeStoreHandle(SimCudaPersistentSafeStoreHandle &target,
                                                 SimCudaPersistentSafeStoreHandle &source)
{
  target = source;
  clearSimCudaPersistentSafeStoreHandle(source);
}

inline void releaseSimCudaPersistentSafeCandidateStateStore(SimCudaPersistentSafeStoreHandle &handle)
{
  sim_scan_cuda_release_persistent_safe_candidate_state_store(&handle);
}

inline bool uploadSimCudaPersistentSafeCandidateStateStore(const vector<SimScanCudaCandidateState> &candidateStates,
                                                           SimCudaPersistentSafeStoreHandle &handle,
                                                           string *errorOut = NULL)
{
  releaseSimCudaPersistentSafeCandidateStateStore(handle);
  if(candidateStates.empty())
  {
    clearSimCudaPersistentSafeStoreHandle(handle);
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }
  return sim_scan_cuda_upload_persistent_safe_candidate_state_store(candidateStates.data(),
                                                                    candidateStates.size(),
                                                                    &handle,
                                                                    errorOut);
}

inline bool eraseSimCudaPersistentSafeCandidateStateStoreStartCoords(const vector<uint64_t> &startCoords,
                                                                     SimCudaPersistentSafeStoreHandle &handle,
                                                                     string *errorOut = NULL)
{
  if(!handle.valid || startCoords.empty())
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }
  vector<uint64_t> sortedUniqueCoords = startCoords;
  sort(sortedUniqueCoords.begin(),sortedUniqueCoords.end());
  sortedUniqueCoords.erase(unique(sortedUniqueCoords.begin(),sortedUniqueCoords.end()),
                           sortedUniqueCoords.end());
  return sim_scan_cuda_erase_persistent_safe_candidate_state_store_start_coords(sortedUniqueCoords.data(),
                                                                                sortedUniqueCoords.size(),
                                                                                &handle,
                                                                                errorOut);
}

inline int simSafeWindowCudaMaxCountRuntime();
inline bool simCudaValidateEnabledRuntime();
inline SimScanCudaSafeWindowPlannerMode simSafeWindowCudaPlannerModeRuntime();

enum SimSafeWindowExecGeometry
{
  SIM_SAFE_WINDOW_EXEC_GEOMETRY_COARSENED = 0,
  SIM_SAFE_WINDOW_EXEC_GEOMETRY_FINE = 1
};

inline bool parseSimSafeWindowCompareBuilder(const char *env,bool validateEnabled)
{
  if(validateEnabled)
  {
    return true;
  }
  if(env == NULL || env[0] == '\0')
  {
    return false;
  }
  return strcmp(env,"0") != 0;
}

inline SimScanCudaSafeWindowPlannerMode parseSimSafeWindowPlannerMode(const char *env)
{
  if(env == NULL || env[0] == '\0')
  {
    return SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE;
  }
  if(strcmp(env,"sparse_v1") == 0)
  {
    return SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V1;
  }
  if(strcmp(env,"sparse_v2") == 0)
  {
    return SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2;
  }
  return SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE;
}

inline SimSafeWindowExecGeometry parseSimSafeWindowExecGeometry(const char *env)
{
  if(env == NULL || env[0] == '\0')
  {
    return SIM_SAFE_WINDOW_EXEC_GEOMETRY_COARSENED;
  }
  if(strcmp(env,"fine") == 0)
  {
    return SIM_SAFE_WINDOW_EXEC_GEOMETRY_FINE;
  }
  return SIM_SAFE_WINDOW_EXEC_GEOMETRY_COARSENED;
}

inline const char *simSafeWindowCudaPlannerModeName(SimScanCudaSafeWindowPlannerMode mode)
{
  switch(mode)
  {
    case SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2:
      return "sparse_v2";
    case SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V1:
      return "sparse_v1";
    case SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE:
    default:
      return "dense";
  }
}

inline const char *simSafeWindowExecGeometryName(SimSafeWindowExecGeometry geometry)
{
  switch(geometry)
  {
    case SIM_SAFE_WINDOW_EXEC_GEOMETRY_FINE:
      return "fine";
    case SIM_SAFE_WINDOW_EXEC_GEOMETRY_COARSENED:
    default:
      return "coarsened";
  }
}

inline bool shouldBuildSimSafeWorksetBuilderAfterSafeWindow(bool safeWindowPlanUsable,
                                                            bool compareBuilder)
{
  return !safeWindowPlanUsable || compareBuilder;
}

inline bool convertSimTracebackPathSummaryToCudaSafeWindowRanges(long queryLength,
                                                                 long targetLength,
                                                                 const SimTracebackPathSummary &summary,
                                                                 int &outSummaryRowStart,
                                                                 vector<int> &outRowMinCols,
                                                                 vector<int> &outRowMaxCols,
                                                                 string *errorOut = NULL)
{
  outSummaryRowStart = 0;
  outRowMinCols.clear();
  outRowMaxCols.clear();
  if(!summary.valid || queryLength <= 0 || targetLength <= 0)
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }
  if(queryLength > static_cast<long>(numeric_limits<int>::max()) ||
     targetLength > static_cast<long>(numeric_limits<int>::max()) ||
     summary.rowStart < static_cast<long>(numeric_limits<int>::min()) ||
     summary.rowStart > static_cast<long>(numeric_limits<int>::max()))
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM safe-window dimensions exceed CUDA helper range";
    }
    return false;
  }
  if(summary.rowMinCols.size() != summary.rowMaxCols.size())
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM traceback path summary row range mismatch";
    }
    return false;
  }

  outSummaryRowStart = static_cast<int>(summary.rowStart);
  outRowMinCols.resize(summary.rowMinCols.size(),0);
  outRowMaxCols.resize(summary.rowMaxCols.size(),0);
  for(size_t rowIndex = 0; rowIndex < summary.rowMinCols.size(); ++rowIndex)
  {
    if(summary.rowMinCols[rowIndex] < static_cast<long>(numeric_limits<int>::min()) ||
       summary.rowMinCols[rowIndex] > static_cast<long>(numeric_limits<int>::max()) ||
       summary.rowMaxCols[rowIndex] < static_cast<long>(numeric_limits<int>::min()) ||
       summary.rowMaxCols[rowIndex] > static_cast<long>(numeric_limits<int>::max()))
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM traceback path summary column range exceeds CUDA helper range";
      }
      outRowMinCols.clear();
      outRowMaxCols.clear();
      outSummaryRowStart = 0;
      return false;
    }
    outRowMinCols[rowIndex] = static_cast<int>(summary.rowMinCols[rowIndex]);
    outRowMaxCols[rowIndex] = static_cast<int>(summary.rowMaxCols[rowIndex]);
  }

  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
}

inline bool buildSimSafeWorksetFromCudaCandidateStateStore(long queryLength,
                                                           long targetLength,
                                                           const SimTracebackPathSummary &summary,
                                                           const SimCudaPersistentSafeStoreHandle &handle,
                                                           SimPathWorkset &outWorkset,
                                                           vector<uint64_t> &outAffectedStartCoords,
                                                           string *errorOut = NULL)
{
  outWorkset = SimPathWorkset();
  outAffectedStartCoords.clear();
  if(!summary.valid || queryLength <= 0 || targetLength <= 0)
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }
  if(!handle.valid)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid GPU safe-store handle";
    }
    return false;
  }
  if(queryLength > static_cast<long>(numeric_limits<int>::max()) ||
     targetLength > static_cast<long>(numeric_limits<int>::max()) ||
     summary.rowStart < static_cast<long>(numeric_limits<int>::min()) ||
     summary.rowStart > static_cast<long>(numeric_limits<int>::max()))
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM safe-workset dimensions exceed CUDA helper range";
    }
    return false;
  }
  if(summary.rowMinCols.size() != summary.rowMaxCols.size())
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM traceback path summary row range mismatch";
    }
    return false;
  }

  vector<int> rowMinCols(summary.rowMinCols.size(),0);
  vector<int> rowMaxCols(summary.rowMaxCols.size(),0);
  for(size_t rowIndex = 0; rowIndex < summary.rowMinCols.size(); ++rowIndex)
  {
    if(summary.rowMinCols[rowIndex] < static_cast<long>(numeric_limits<int>::min()) ||
       summary.rowMinCols[rowIndex] > static_cast<long>(numeric_limits<int>::max()) ||
       summary.rowMaxCols[rowIndex] < static_cast<long>(numeric_limits<int>::min()) ||
       summary.rowMaxCols[rowIndex] > static_cast<long>(numeric_limits<int>::max()))
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM traceback path summary column range exceeds CUDA helper range";
      }
      return false;
    }
    rowMinCols[rowIndex] = static_cast<int>(summary.rowMinCols[rowIndex]);
    rowMaxCols[rowIndex] = static_cast<int>(summary.rowMaxCols[rowIndex]);
  }

  vector<SimScanCudaCandidateState> seedCandidates;
  if(!sim_scan_cuda_filter_persistent_safe_candidate_state_store_by_path_summary(handle,
                                                                                 static_cast<int>(summary.rowStart),
                                                                                 rowMinCols,
                                                                                 rowMaxCols,
                                                                                 &seedCandidates,
                                                                                 errorOut))
  {
    return false;
  }
  if(seedCandidates.empty())
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }

  vector< vector< pair<long,long> > > seedRowIntervals(static_cast<size_t>(queryLength + 1));
  for(size_t candidateIndex = 0; candidateIndex < seedCandidates.size(); ++candidateIndex)
  {
    long rowStart = 0;
    long rowEnd = 0;
    long colStart = 0;
    long colEnd = 0;
    if(!clampSimCandidateStateBounds(seedCandidates[candidateIndex],
                                     queryLength,
                                     targetLength,
                                     rowStart,
                                     rowEnd,
                                     colStart,
                                     colEnd))
    {
      continue;
    }
    for(long row = rowStart; row <= rowEnd; ++row)
    {
      insertSimSafeWorksetInterval(seedRowIntervals[static_cast<size_t>(row)],colStart,colEnd);
    }
  }

  vector<int> rowOffsets(static_cast<size_t>(queryLength + 2),0);
  vector<SimScanCudaColumnInterval> flattenedIntervals;
  for(long row = 1; row <= queryLength; ++row)
  {
    rowOffsets[static_cast<size_t>(row)] = static_cast<int>(flattenedIntervals.size());
    const vector< pair<long,long> > &intervals = seedRowIntervals[static_cast<size_t>(row)];
    for(size_t intervalIndex = 0; intervalIndex < intervals.size(); ++intervalIndex)
    {
      flattenedIntervals.push_back(SimScanCudaColumnInterval(static_cast<int>(intervals[intervalIndex].first),
                                                             static_cast<int>(intervals[intervalIndex].second)));
    }
  }
  rowOffsets[static_cast<size_t>(queryLength + 1)] = static_cast<int>(flattenedIntervals.size());

  vector<SimScanCudaCandidateState> affectedCandidates;
  if(!sim_scan_cuda_filter_persistent_safe_candidate_state_store_by_row_intervals(handle,
                                                                                  static_cast<int>(queryLength),
                                                                                  static_cast<int>(targetLength),
                                                                                  rowOffsets,
                                                                                  flattenedIntervals,
                                                                                  &affectedCandidates,
                                                                                  errorOut))
  {
    return false;
  }

  outWorkset = buildSimSafeWorksetFromCandidateStates(queryLength,
                                                      targetLength,
                                                      summary,
                                                      affectedCandidates,
                                                      &outAffectedStartCoords);
  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
}

inline SimPathWorkset coarsenSimSafeWorksetForExecution(const SimPathWorkset &workset)
{
  if(!workset.hasWorkset || workset.bands.empty())
  {
    return workset;
  }

  vector<SimUpdateBand> execBands;
  execBands.reserve(workset.bands.size());
  size_t groupStart = 0;
  while(groupStart < workset.bands.size())
  {
    size_t groupEnd = groupStart + 1;
    long groupRowStart = workset.bands[groupStart].rowStart;
    long groupRowEnd = workset.bands[groupStart].rowEnd;
    long groupColStart = workset.bands[groupStart].colStart;
    long groupColEnd = workset.bands[groupStart].colEnd;
    uint64_t groupCellCount = simUpdateBandCellCount(workset.bands[groupStart]);
    while(groupEnd < workset.bands.size() &&
          workset.bands[groupEnd].rowStart <= groupRowEnd + 1)
    {
      if(groupRowEnd < workset.bands[groupEnd].rowEnd) groupRowEnd = workset.bands[groupEnd].rowEnd;
      if(groupColStart > workset.bands[groupEnd].colStart) groupColStart = workset.bands[groupEnd].colStart;
      if(groupColEnd < workset.bands[groupEnd].colEnd) groupColEnd = workset.bands[groupEnd].colEnd;
      groupCellCount += simUpdateBandCellCount(workset.bands[groupEnd]);
      ++groupEnd;
    }

    const uint64_t groupBoundingArea =
      simUpdateBandBoundingCellCount(groupRowStart,groupRowEnd,groupColStart,groupColEnd);
    if(groupEnd - groupStart > 1 && groupBoundingArea <= groupCellCount * static_cast<uint64_t>(2))
    {
      SimUpdateBand mergedBand;
      mergedBand.rowStart = groupRowStart;
      mergedBand.rowEnd = groupRowEnd;
      mergedBand.colStart = groupColStart;
      mergedBand.colEnd = groupColEnd;
      execBands.push_back(mergedBand);
    }
    else
    {
      for(size_t bandIndex = groupStart; bandIndex < groupEnd; ++bandIndex)
      {
        execBands.push_back(workset.bands[bandIndex]);
      }
    }
    groupStart = groupEnd;
  }

  SimPathWorkset execWorkset = makeSimPathWorksetFromBands(execBands);
  execWorkset.fallbackToRect = workset.fallbackToRect;
  if(execWorkset.bands.size() > 8)
  {
    long globalRowStart = execWorkset.bands[0].rowStart;
    long globalRowEnd = execWorkset.bands[0].rowEnd;
    long globalColStart = execWorkset.bands[0].colStart;
    long globalColEnd = execWorkset.bands[0].colEnd;
    for(size_t bandIndex = 1; bandIndex < execWorkset.bands.size(); ++bandIndex)
    {
      if(globalRowStart > execWorkset.bands[bandIndex].rowStart) globalRowStart = execWorkset.bands[bandIndex].rowStart;
      if(globalRowEnd < execWorkset.bands[bandIndex].rowEnd) globalRowEnd = execWorkset.bands[bandIndex].rowEnd;
      if(globalColStart > execWorkset.bands[bandIndex].colStart) globalColStart = execWorkset.bands[bandIndex].colStart;
      if(globalColEnd < execWorkset.bands[bandIndex].colEnd) globalColEnd = execWorkset.bands[bandIndex].colEnd;
    }
    const uint64_t globalBoundingArea =
      simUpdateBandBoundingCellCount(globalRowStart,globalRowEnd,globalColStart,globalColEnd);
    if(globalBoundingArea <= workset.cellCount * static_cast<uint64_t>(4))
    {
      SimUpdateBand mergedBand;
      mergedBand.rowStart = globalRowStart;
      mergedBand.rowEnd = globalRowEnd;
      mergedBand.colStart = globalColStart;
      mergedBand.colEnd = globalColEnd;
      execWorkset.bands.assign(1,mergedBand);
      execWorkset.hasWorkset = true;
      execWorkset.cellCount = globalBoundingArea;
    }
    else
    {
      vector<SimUpdateBand> denseExecBands = execWorkset.bands;
      while(denseExecBands.size() > 8)
      {
        vector<SimUpdateBand> nextBands;
        nextBands.reserve((denseExecBands.size() + 1u) / 2u);
        bool mergedAny = false;
        for(size_t bandIndex = 0; bandIndex < denseExecBands.size();)
        {
          if(bandIndex + 1 < denseExecBands.size() &&
             denseExecBands[bandIndex + 1].rowStart <= denseExecBands[bandIndex].rowEnd + 1)
          {
            const SimUpdateBand &leftBand = denseExecBands[bandIndex];
            const SimUpdateBand &rightBand = denseExecBands[bandIndex + 1];
            const long mergedRowStart = min(leftBand.rowStart,rightBand.rowStart);
            const long mergedRowEnd = max(leftBand.rowEnd,rightBand.rowEnd);
            const long mergedColStart = min(leftBand.colStart,rightBand.colStart);
            const long mergedColEnd = max(leftBand.colEnd,rightBand.colEnd);
            const uint64_t pairCellCount =
              simUpdateBandCellCount(leftBand) + simUpdateBandCellCount(rightBand);
            const uint64_t pairBoundingArea =
              simUpdateBandBoundingCellCount(mergedRowStart,mergedRowEnd,mergedColStart,mergedColEnd);
            if(pairBoundingArea <= pairCellCount * static_cast<uint64_t>(4))
            {
              SimUpdateBand mergedBand;
              mergedBand.rowStart = mergedRowStart;
              mergedBand.rowEnd = mergedRowEnd;
              mergedBand.colStart = mergedColStart;
              mergedBand.colEnd = mergedColEnd;
              nextBands.push_back(mergedBand);
              mergedAny = true;
              bandIndex += 2;
              continue;
            }
          }
          nextBands.push_back(denseExecBands[bandIndex]);
          ++bandIndex;
        }
        if(!mergedAny || nextBands.size() >= denseExecBands.size())
        {
          break;
        }
        denseExecBands.swap(nextBands);
      }
      if(denseExecBands.size() < execWorkset.bands.size())
      {
        execWorkset = makeSimPathWorksetFromBands(denseExecBands);
        execWorkset.fallbackToRect = workset.fallbackToRect;
      }
    }
  }
  return execWorkset;
}

inline SimPathWorkset buildSimSafeWindowExecutionWorkset(const SimPathWorkset &workset)
{
  return coarsenSimSafeWorksetForExecution(workset);
}

inline uint64_t simSafeWindowSaturatingAdd(uint64_t left,uint64_t right)
{
  if(numeric_limits<uint64_t>::max() - left < right)
  {
    return numeric_limits<uint64_t>::max();
  }
  return left + right;
}

inline uint64_t simSafeWindowCudaWindowCellCount(const SimScanCudaSafeWindow &window)
{
  if(window.rowEnd < window.rowStart || window.colEnd < window.colStart)
  {
    return 0;
  }
  return static_cast<uint64_t>(window.rowEnd - window.rowStart + 1) *
         static_cast<uint64_t>(window.colEnd - window.colStart + 1);
}

inline uint64_t simSafeWindowCudaWindowCellCount(const vector<SimScanCudaSafeWindow> &windows)
{
  uint64_t cellCount = 0;
  for(size_t windowIndex = 0; windowIndex < windows.size(); ++windowIndex)
  {
    cellCount = simSafeWindowSaturatingAdd(cellCount,
                                           simSafeWindowCudaWindowCellCount(windows[windowIndex]));
  }
  return cellCount;
}

inline uint64_t simSafeWindowCudaMaxWindowCellCount(const vector<SimScanCudaSafeWindow> &windows)
{
  uint64_t maxCellCount = 0;
  for(size_t windowIndex = 0; windowIndex < windows.size(); ++windowIndex)
  {
    maxCellCount = max(maxCellCount,simSafeWindowCudaWindowCellCount(windows[windowIndex]));
  }
  return maxCellCount;
}

inline uint64_t simSafeWindowMaxBandCellCount(const SimPathWorkset &workset)
{
  uint64_t maxCellCount = 0;
  for(size_t bandIndex = 0; bandIndex < workset.bands.size(); ++bandIndex)
  {
    maxCellCount = max(maxCellCount,simUpdateBandCellCount(workset.bands[bandIndex]));
  }
  return maxCellCount;
}

struct SimSafeWindowExecutePlan
{
  SimSafeWindowExecutePlan():
    plannerModeRequested(SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE),
    plannerModeUsed(SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE),
    windowCount(0),
    affectedStartCount(0),
    execBandCount(0),
    execCellCount(0),
    rawWindowCellCount(0),
    rawMaxWindowCellCount(0),
    execMaxBandCellCount(0),
    coarseningInflatedCellCount(0),
    overflowFallback(false),
    emptyPlan(true),
    coordBytesD2H(0),
    gpuNanoseconds(0),
    d2hNanoseconds(0),
    sparseV2Considered(false),
    sparseV2Selected(false),
    sparseV2SavedCells(0)
  {
  }

  SimPathWorkset execWorkset;
  SimPathWorkset rawWorkset;
  vector<uint64_t> uniqueAffectedStartCoords;
  SimScanCudaSafeWindowPlannerMode plannerModeRequested;
  SimScanCudaSafeWindowPlannerMode plannerModeUsed;
  uint64_t windowCount;
  uint64_t affectedStartCount;
  uint64_t execBandCount;
  uint64_t execCellCount;
  uint64_t rawWindowCellCount;
  uint64_t rawMaxWindowCellCount;
  uint64_t execMaxBandCellCount;
  uint64_t coarseningInflatedCellCount;
  bool overflowFallback;
  bool emptyPlan;
  uint64_t coordBytesD2H;
  uint64_t gpuNanoseconds;
  uint64_t d2hNanoseconds;
  bool sparseV2Considered;
  bool sparseV2Selected;
  uint64_t sparseV2SavedCells;
};

inline const SimPathWorkset &selectSimSafeWindowExecutePlanWorkset(
  const SimSafeWindowExecutePlan &plan,
  SimSafeWindowExecGeometry geometry)
{
  return geometry == SIM_SAFE_WINDOW_EXEC_GEOMETRY_FINE ? plan.rawWorkset : plan.execWorkset;
}

inline void assignSimSafeWindowExecutePlanFromCudaResult(
  const SimScanCudaSafeWindowExecutePlanResult &cudaPlan,
  SimScanCudaSafeWindowPlannerMode plannerModeRequested,
  SimScanCudaSafeWindowPlannerMode plannerModeUsed,
  SimSafeWindowExecutePlan &outPlan)
{
  outPlan = SimSafeWindowExecutePlan();
  const SimPathWorkset safeWindowWorkset =
    makeSimPathWorksetFromCudaSafeWindows(cudaPlan.execWindows);
  outPlan.rawWorkset = safeWindowWorkset;
  outPlan.execWorkset = buildSimSafeWindowExecutionWorkset(safeWindowWorkset);
  outPlan.uniqueAffectedStartCoords = cudaPlan.uniqueAffectedStartCoords;
  outPlan.plannerModeRequested = plannerModeRequested;
  outPlan.plannerModeUsed = plannerModeUsed;
  outPlan.windowCount = cudaPlan.windowCount;
  outPlan.affectedStartCount = cudaPlan.affectedStartCount;
  outPlan.execBandCount = static_cast<uint64_t>(outPlan.execWorkset.bands.size());
  outPlan.execCellCount = outPlan.execWorkset.cellCount;
  outPlan.rawWindowCellCount = simSafeWindowCudaWindowCellCount(cudaPlan.execWindows);
  outPlan.rawMaxWindowCellCount = simSafeWindowCudaMaxWindowCellCount(cudaPlan.execWindows);
  outPlan.execMaxBandCellCount = simSafeWindowMaxBandCellCount(outPlan.execWorkset);
  outPlan.coarseningInflatedCellCount =
    outPlan.execCellCount > outPlan.rawWindowCellCount ?
      outPlan.execCellCount - outPlan.rawWindowCellCount : 0;
  outPlan.overflowFallback = cudaPlan.overflowFallback;
  outPlan.emptyPlan = cudaPlan.emptyPlan;
  outPlan.coordBytesD2H = cudaPlan.coordBytesD2H;
  outPlan.gpuNanoseconds =
    (cudaPlan.gpuSeconds <= 0.0) ? 0 : static_cast<uint64_t>(cudaPlan.gpuSeconds * 1.0e9 + 0.5);
  outPlan.d2hNanoseconds =
    (cudaPlan.d2hSeconds <= 0.0) ? 0 : static_cast<uint64_t>(cudaPlan.d2hSeconds * 1.0e9 + 0.5);
}

inline bool buildSimSafeWindowExecutePlanFromCudaCandidateStateStoreWithPlanner(
  long queryLength,
  long targetLength,
  const SimTracebackPathSummary &summary,
  const SimCudaPersistentSafeStoreHandle &handle,
  SimScanCudaSafeWindowPlannerMode plannerMode,
  int maxWindowCount,
  SimSafeWindowExecutePlan &outPlan,
  string *errorOut = NULL)
{
  outPlan = SimSafeWindowExecutePlan();
  if(!summary.valid || queryLength <= 0 || targetLength <= 0)
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }
  if(!handle.valid)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid GPU safe-store handle";
    }
    return false;
  }

  int summaryRowStart = 0;
  vector<int> summaryRowMinCols;
  vector<int> summaryRowMaxCols;
  if(!convertSimTracebackPathSummaryToCudaSafeWindowRanges(queryLength,
                                                           targetLength,
                                                           summary,
                                                           summaryRowStart,
                                                           summaryRowMinCols,
                                                           summaryRowMaxCols,
                                                           errorOut))
  {
    return false;
  }

  if(plannerMode != SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2)
  {
    SimScanCudaSafeWindowExecutePlanResult cudaPlan;
    if(!sim_scan_cuda_build_safe_window_execute_plan(handle,
                                                     static_cast<int>(queryLength),
                                                     static_cast<int>(targetLength),
                                                     summaryRowStart,
                                                     summaryRowMinCols,
                                                     summaryRowMaxCols,
                                                     plannerMode,
                                                     maxWindowCount,
                                                     &cudaPlan,
                                                     errorOut))
    {
      return false;
    }
    assignSimSafeWindowExecutePlanFromCudaResult(cudaPlan,
                                                 plannerMode,
                                                 plannerMode,
                                                 outPlan);
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }

  SimScanCudaSafeWindowExecutePlanResult denseCudaPlan;
  if(!sim_scan_cuda_build_safe_window_execute_plan(handle,
                                                   static_cast<int>(queryLength),
                                                   static_cast<int>(targetLength),
                                                   summaryRowStart,
                                                   summaryRowMinCols,
                                                   summaryRowMaxCols,
                                                   SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE,
                                                   maxWindowCount,
                                                   &denseCudaPlan,
                                                   errorOut))
  {
    return false;
  }

  SimSafeWindowExecutePlan densePlan;
  assignSimSafeWindowExecutePlanFromCudaResult(denseCudaPlan,
                                               SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2,
                                               SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE,
                                               densePlan);

  SimScanCudaSafeWindowExecutePlanResult sparseCudaPlan;
  string sparseError;
  const bool sparseOk =
    sim_scan_cuda_build_safe_window_execute_plan(handle,
                                                 static_cast<int>(queryLength),
                                                 static_cast<int>(targetLength),
                                                 summaryRowStart,
                                                 summaryRowMinCols,
                                                 summaryRowMaxCols,
                                                 SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V1,
                                                 maxWindowCount,
                                                 &sparseCudaPlan,
                                                 &sparseError);

  SimSafeWindowExecutePlan sparsePlan;
  if(sparseOk)
  {
    assignSimSafeWindowExecutePlanFromCudaResult(sparseCudaPlan,
                                                 SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2,
                                                 SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2,
                                                 sparsePlan);
  }

  const bool sparseUsable =
    sparseOk &&
    !sparsePlan.overflowFallback &&
    !sparsePlan.emptyPlan &&
    sparsePlan.execWorkset.hasWorkset &&
    sparsePlan.affectedStartCount > 0;
  const bool selectSparse =
    sparseUsable && sparsePlan.execCellCount < densePlan.execCellCount;

  outPlan = selectSparse ? sparsePlan : densePlan;
  outPlan.plannerModeRequested = SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2;
  outPlan.plannerModeUsed =
    selectSparse ? SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_SPARSE_V2 :
                   SIM_SCAN_CUDA_SAFE_WINDOW_PLANNER_DENSE;
  outPlan.sparseV2Considered = true;
  outPlan.sparseV2Selected = selectSparse;
  outPlan.sparseV2SavedCells =
    selectSparse ? densePlan.execCellCount - sparsePlan.execCellCount : 0;
  if(sparseOk)
  {
    outPlan.coordBytesD2H =
      simSafeWindowSaturatingAdd(densePlan.coordBytesD2H,sparsePlan.coordBytesD2H);
    outPlan.gpuNanoseconds =
      simSafeWindowSaturatingAdd(densePlan.gpuNanoseconds,sparsePlan.gpuNanoseconds);
    outPlan.d2hNanoseconds =
      simSafeWindowSaturatingAdd(densePlan.d2hNanoseconds,sparsePlan.d2hNanoseconds);
  }
  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
}

inline bool buildSimSafeWindowExecutePlanFromCudaCandidateStateStore(long queryLength,
                                                                     long targetLength,
                                                                     const SimTracebackPathSummary &summary,
                                                                     const SimCudaPersistentSafeStoreHandle &handle,
                                                                     SimSafeWindowExecutePlan &outPlan,
                                                                     string *errorOut = NULL)
{
  return buildSimSafeWindowExecutePlanFromCudaCandidateStateStoreWithPlanner(
    queryLength,
    targetLength,
    summary,
    handle,
    simSafeWindowCudaPlannerModeRuntime(),
    simSafeWindowCudaMaxCountRuntime(),
    outPlan,
    errorOut);
}

inline bool shouldPreferSimSafeWindowExecution(const SimPathWorkset &safeWindowWorkset,
                                               uint64_t safeWindowAffectedStartCount,
                                               const SimPathWorkset &safeWorksetExec,
                                               uint64_t safeWorksetAffectedStartCount)
{
  return safeWindowWorkset.hasWorkset &&
         safeWindowAffectedStartCount > 0 &&
         safeWorksetExec.hasWorkset &&
         (safeWindowWorkset.cellCount < safeWorksetExec.cellCount ||
         (safeWindowWorkset.cellCount == safeWorksetExec.cellCount &&
           safeWindowAffectedStartCount < safeWorksetAffectedStartCount));
}

inline bool shouldPreferSimSafeWindowExecution(const SimPathWorkset &safeWindowWorkset,
                                               uint64_t safeWindowAffectedStartCount,
                                               const SimPathWorkset &safeWorksetExec)
{
  return shouldPreferSimSafeWindowExecution(safeWindowWorkset,
                                            safeWindowAffectedStartCount,
                                            safeWorksetExec,
                                            safeWindowAffectedStartCount);
}

enum SimSafeWindowPlanComparison
{
  SIM_SAFE_WINDOW_PLAN_COMPARISON_INVALID = 0,
  SIM_SAFE_WINDOW_PLAN_COMPARISON_BETTER = 1,
  SIM_SAFE_WINDOW_PLAN_COMPARISON_WORSE = 2,
  SIM_SAFE_WINDOW_PLAN_COMPARISON_EQUAL = 3
};

inline SimSafeWindowPlanComparison compareSimSafeWindowExecution(const SimSafeWindowExecutePlan &safeWindowPlan,
                                                                 const SimPathWorkset &safeWindowExecWorkset,
                                                                 const SimPathWorkset &safeWorksetExec,
                                                                 uint64_t safeWorksetAffectedStartCount)
{
  if(safeWindowPlan.overflowFallback ||
     safeWindowPlan.emptyPlan ||
     !safeWindowExecWorkset.hasWorkset ||
     safeWindowPlan.affectedStartCount == 0)
  {
    return SIM_SAFE_WINDOW_PLAN_COMPARISON_INVALID;
  }
  if(!safeWorksetExec.hasWorkset || safeWorksetAffectedStartCount == 0)
  {
    return SIM_SAFE_WINDOW_PLAN_COMPARISON_INVALID;
  }
  if(shouldPreferSimSafeWindowExecution(safeWindowExecWorkset,
                                        safeWindowPlan.affectedStartCount,
                                        safeWorksetExec,
                                        safeWorksetAffectedStartCount))
  {
    return SIM_SAFE_WINDOW_PLAN_COMPARISON_BETTER;
  }
  if(safeWindowExecWorkset.cellCount == safeWorksetExec.cellCount &&
     safeWindowPlan.affectedStartCount == safeWorksetAffectedStartCount)
  {
    return SIM_SAFE_WINDOW_PLAN_COMPARISON_EQUAL;
  }
  return SIM_SAFE_WINDOW_PLAN_COMPARISON_WORSE;
}

template <typename Visitor>
inline bool visitSimTracebackPath(long stari,
                                  long starj,
                                  long M,
                                  long N,
                                  const long *S,
                                  Visitor visitor)
{
  if(S == NULL || M < 0 || N < 0)
  {
    return false;
  }

  long i = 0;
  long j = 0;
  long globalI = stari - 1;
  long globalJ = starj - 1;
  const long *p = S;
  while(i < M || j < N)
  {
    while(i < M && j < N && *p == 0)
    {
      ++i;
      ++j;
      ++globalI;
      ++globalJ;
      visitor(globalI,globalJ);
      ++p;
    }
    if(i < M || j < N)
    {
      const long op = *p++;
      if(op > 0)
      {
        for(long gap = 0; gap < op; ++gap)
        {
          ++j;
          ++globalJ;
          visitor(globalI,globalJ);
        }
      }
      else if(op < 0)
      {
        for(long gap = 0; gap < -op; ++gap)
        {
          ++i;
          ++globalI;
          visitor(globalI,globalJ);
        }
      }
    }
  }
  return i == M && j == N;
}

inline SimTracebackPathSummary summarizeSimTracebackPath(long stari,
                                                         long starj,
                                                         long M,
                                                         long N,
                                                         const long *S)
{
  SimTracebackPathSummary summary;
  vector< pair<long,long> > points;
  points.reserve(static_cast<size_t>(M + N));
  if(!visitSimTracebackPath(stari,
                            starj,
                            M,
                            N,
                            S,
                            [&](long row,long col)
                            {
                              points.push_back(std::make_pair(row,col));
                            }))
  {
    return summary;
  }
  if(points.empty())
  {
    return summary;
  }

  long prevRow = stari - 1;
  long prevCol = starj - 1;
  for(size_t index = 0; index < points.size(); ++index)
  {
    SimTracebackPathSegmentKind segmentKind = SIM_TRACEBACK_SEGMENT_DIAGONAL;
    const long row = points[index].first;
    const long col = points[index].second;
    const long deltaRow = row - prevRow;
    const long deltaCol = col - prevCol;
    if(deltaRow == 1 && deltaCol == 1)
    {
      segmentKind = SIM_TRACEBACK_SEGMENT_DIAGONAL;
    }
    else if(deltaRow == 0 && deltaCol == 1)
    {
      segmentKind = SIM_TRACEBACK_SEGMENT_HORIZONTAL;
    }
    else if(deltaRow == 1 && deltaCol == 0)
    {
      segmentKind = SIM_TRACEBACK_SEGMENT_VERTICAL;
    }
    else
    {
      return SimTracebackPathSummary();
    }

    if(summary.segments.empty() || summary.segments.back().kind != segmentKind)
    {
      summary.segments.push_back(SimTracebackPathSegment(segmentKind,row,col));
    }
    else
    {
      summary.segments.back().rowEnd = row;
      summary.segments.back().colEnd = col;
    }
    prevRow = row;
    prevCol = col;
  }

  summary.valid = true;
  summary.stepCount = static_cast<uint64_t>(points.size());
  summary.rowStart = summary.rowEnd = points[0].first;
  summary.colStart = summary.colEnd = points[0].second;
  for(size_t index = 1; index < points.size(); ++index)
  {
    if(summary.rowStart > points[index].first) summary.rowStart = points[index].first;
    if(summary.rowEnd < points[index].first) summary.rowEnd = points[index].first;
    if(summary.colStart > points[index].second) summary.colStart = points[index].second;
    if(summary.colEnd < points[index].second) summary.colEnd = points[index].second;
  }

  const size_t rowCount = static_cast<size_t>(summary.rowEnd - summary.rowStart + 1);
  summary.rowMinCols.assign(rowCount, std::numeric_limits<long>::max());
  summary.rowMaxCols.assign(rowCount, std::numeric_limits<long>::min());
  for(size_t index = 0; index < points.size(); ++index)
  {
    const size_t rowIndex = static_cast<size_t>(points[index].first - summary.rowStart);
    if(summary.rowMinCols[rowIndex] > points[index].second)
    {
      summary.rowMinCols[rowIndex] = points[index].second;
    }
    if(summary.rowMaxCols[rowIndex] < points[index].second)
    {
      summary.rowMaxCols[rowIndex] = points[index].second;
    }
  }
  return summary;
}

inline SimPathWorkset buildSimPathWorkset(long queryLength,
                                          long targetLength,
                                          const SimTracebackPathSummary &summary,
                                          long halo,
                                          long maxBandHeight,
                                          uint64_t maxCellCount)
{
  SimPathWorkset workset;
  if(!summary.valid || queryLength <= 0 || targetLength <= 0)
  {
    return workset;
  }

  const long clampedHalo = std::max(0L, halo);
  const long clampedBandHeight = std::max(1L, maxBandHeight);
  vector<long> dilatedMin(static_cast<size_t>(queryLength + 1), std::numeric_limits<long>::max());
  vector<long> dilatedMax(static_cast<size_t>(queryLength + 1), std::numeric_limits<long>::min());

  for(size_t rowIndex = 0; rowIndex < summary.rowMinCols.size(); ++rowIndex)
  {
    const long pathMin = summary.rowMinCols[rowIndex];
    const long pathMax = summary.rowMaxCols[rowIndex];
    if(pathMin > pathMax)
    {
      continue;
    }
    const long row = summary.rowStart + static_cast<long>(rowIndex);
    const long colStart = std::max(1L, pathMin - clampedHalo);
    const long colEnd = std::min(targetLength, pathMax + clampedHalo);
    const long dilatedRowStart = std::max(1L, row - clampedHalo);
    const long dilatedRowEnd = std::min(queryLength, row + clampedHalo);
    for(long dilatedRow = dilatedRowStart; dilatedRow <= dilatedRowEnd; ++dilatedRow)
    {
      const size_t dilatedIndex = static_cast<size_t>(dilatedRow);
      if(dilatedMin[dilatedIndex] > colStart)
      {
        dilatedMin[dilatedIndex] = colStart;
      }
      if(dilatedMax[dilatedIndex] < colEnd)
      {
        dilatedMax[dilatedIndex] = colEnd;
      }
    }
  }

  for(long row = 1; row <= queryLength; ++row)
  {
    const size_t rowIndex = static_cast<size_t>(row);
    if(dilatedMin[rowIndex] > dilatedMax[rowIndex])
    {
      continue;
    }

    SimUpdateBand band;
    band.rowStart = row;
    band.rowEnd = row;
    band.colStart = dilatedMin[rowIndex];
    band.colEnd = dilatedMax[rowIndex];
    long rowsInBand = 1;
    while(band.rowEnd < queryLength && rowsInBand < clampedBandHeight)
    {
      const size_t nextIndex = static_cast<size_t>(band.rowEnd + 1);
      if(dilatedMin[nextIndex] > dilatedMax[nextIndex])
      {
        break;
      }
      ++band.rowEnd;
      ++rowsInBand;
      if(band.colStart > dilatedMin[nextIndex]) band.colStart = dilatedMin[nextIndex];
      if(band.colEnd < dilatedMax[nextIndex]) band.colEnd = dilatedMax[nextIndex];
    }
    workset.cellCount += static_cast<uint64_t>(band.rowEnd - band.rowStart + 1) *
                         static_cast<uint64_t>(band.colEnd - band.colStart + 1);
    workset.bands.push_back(band);
    row = band.rowEnd;
  }

  workset.hasWorkset = !workset.bands.empty();
  if(maxCellCount > 0 && workset.cellCount > maxCellCount)
  {
    workset.fallbackToRect = true;
  }
  return workset;
}

struct SimRequest
{
  SimRequest(const string &s1,long n1,long n2,long n3,long n4,int n5,int n6,int n7,int n8):
    sourceSequence(s1), dnaStartPos(n1), minScore(n2), reverseMode(n3), parallelMode(n4), ntMin(n5), ntMax(n6), penaltyT(n7), penaltyC(n8) {}

  const string &sourceSequence;
  long dnaStartPos;
  long minScore;
  long reverseMode;
  long parallelMode;
  int ntMin;
  int ntMax;
  int penaltyT;
  int penaltyC;
};

inline float computeSimTriScoreSumFromTracebackScript(const SimRequest &request,
                                                      const char *A,
                                                      long M,
                                                      long N,
                                                      const long *S,
                                                      long starj,
                                                      long targetLength)
{
  string seqtmp = request.sourceSequence;
  if(request.reverseMode == 0)
  {
    if(request.parallelMode > 0)
    {
      complement(seqtmp);
    }
  }
  else
  {
    if(request.parallelMode < 0)
    {
      complement(seqtmp);
    }
  }

  long i = 0;
  long j = 0;
  long seqj = 0;
  float tri_score = 0.0f;
  char prechar = 0;
  char curchar = 0;
  float hashvalue = 0.0f;
  float prescore = 0.0f;

  const long *p = S;
  while(i < M || j < N)
  {
    while(i < M && j < N && *p == 0)
    {
      ++i;
      ++j;
      if(request.reverseMode == 0)
      {
        curchar = seqtmp[starj + seqj - 1];
      }
      else
      {
        curchar = seqtmp[targetLength - starj - seqj];
      }
      hashvalue = triplex_score(curchar, A[i], request.parallelMode);
      if(request.reverseMode == 0)
      {
        if((curchar == prechar) && curchar == 'A')
        {
          tri_score = tri_score - prescore + request.penaltyT;
          hashvalue = request.penaltyT;
        }
        if((curchar == prechar) && curchar == 'G')
        {
          tri_score = tri_score - prescore + request.penaltyC;
          hashvalue = request.penaltyC;
        }
      }
      else
      {
        if((curchar == prechar) && curchar == 'A')
        {
          tri_score = tri_score - prescore - 1000;
          hashvalue = -1000;
        }
        if((curchar == prechar) && curchar == 'G')
        {
          tri_score = tri_score - prescore;
          hashvalue = 0;
        }
      }
      prescore = hashvalue;
      prechar = curchar;
      tri_score += hashvalue;
      ++seqj;
      ++p;
    }
    if(i < M || j < N)
    {
      const long op = *p++;
      if(op > 0)
      {
        for(long f = 0; f < op; ++f)
        {
          ++j;
          if(request.reverseMode == 0)
          {
            curchar = seqtmp[starj + seqj - 1];
          }
          else
          {
            curchar = seqtmp[targetLength - starj - seqj];
          }
          hashvalue = triplex_score(curchar, '-', request.parallelMode);
          if(request.reverseMode == 0)
          {
            if((curchar == prechar) && curchar == 'A')
            {
              tri_score = tri_score - prescore + request.penaltyT;
              hashvalue = request.penaltyT;
            }
            if((curchar == prechar) && curchar == 'G')
            {
              tri_score = tri_score - prescore + request.penaltyC;
              hashvalue = request.penaltyC;
            }
          }
          else
          {
            if((curchar == prechar) && curchar == 'A')
            {
              tri_score = tri_score - prescore - 1000;
              hashvalue = -1000;
            }
            if((curchar == prechar) && curchar == 'G')
            {
              tri_score = tri_score - prescore;
              hashvalue = 0;
            }
          }
          prescore = hashvalue;
          prechar = curchar;
          tri_score += hashvalue;
          ++seqj;
        }
      }
      else if(op < 0)
      {
        for(long f = 0; f < -op; ++f)
        {
          ++i;
          curchar = '-';
          hashvalue = triplex_score(curchar, A[i], request.parallelMode);
          if(request.reverseMode == 0)
          {
            if((curchar == prechar) && curchar == 'A')
            {
              tri_score = tri_score - prescore + request.penaltyT;
              hashvalue = request.penaltyT;
            }
            if((curchar == prechar) && curchar == 'G')
            {
              tri_score = tri_score - prescore + request.penaltyC;
              hashvalue = request.penaltyC;
            }
          }
          else
          {
            if((curchar == prechar) && curchar == 'A')
            {
              tri_score = tri_score - prescore - 1000;
              hashvalue = -1000;
            }
            if((curchar == prechar) && curchar == 'G')
            {
              tri_score = tri_score - prescore;
              hashvalue = 0;
            }
          }
          prescore = hashvalue;
          prechar = curchar;
          tri_score += hashvalue;
        }
      }
    }
  }
  return tri_score;
}

struct SimWorkspace
{
  SimWorkspace(long queryLength,long targetLength):
    CC(targetLength + 1),
    DD(targetLength + 1),
    RR(targetLength + 1),
    SS(targetLength + 1),
    EE(targetLength + 1),
    FF(targetLength + 1),
    HH(queryLength + 1),
    WW(queryLength + 1),
    II(queryLength + 1),
    JJ(queryLength + 1),
    XX(queryLength + 1),
    YY(queryLength + 1),
    blockedWordsPerRow(static_cast<size_t>((targetLength + 64) / 64)),
    blockedDenseStrideWords((queryLength > 0 &&
                             targetLength > 0 &&
                             queryLength <= 8192 &&
                             targetLength <= 8192) ? blockedWordsPerRow : 0),
    blocked(queryLength + 1),
    blockedDense(blockedDenseStrideWords > 0 ? static_cast<size_t>(queryLength + 1) * blockedDenseStrideWords : 0, 0) {}

  vector<long> CC;
  vector<long> DD;
  vector<long> RR;
  vector<long> SS;
  vector<long> EE;
  vector<long> FF;
  vector<long> HH;
  vector<long> WW;
  vector<long> II;
  vector<long> JJ;
  vector<long> XX;
  vector<long> YY;
  size_t blockedWordsPerRow;
  size_t blockedDenseStrideWords;
  vector< vector<uint64_t> > blocked;
  vector<uint64_t> blockedDense;
};

struct SimCandidateStats
{
  SimCandidateStats()
  {
    clear();
  }

  void clear()
  {
    addnodeCalls = 0;
    eventsSeen = 0;
    indexHits = 0;
    indexMisses = 0;
    fullEvictions = 0;
    minSelectionScans = 0;
    heapBuilds = 0;
    heapUpdates = 0;
    hashProbesTotal = 0;
    hashProbesMax = 0;
    runUpdaterRunsStarted = 0;
    runUpdaterFlushes = 0;
    runUpdaterTotalRunLen = 0;
    runUpdaterMaxRunLen = 0;
    runUpdaterSkippedEvents = 0;
  }

  uint64_t addnodeCalls;
  uint64_t eventsSeen;
  uint64_t indexHits;
  uint64_t indexMisses;
  uint64_t fullEvictions;
  uint64_t minSelectionScans;
  uint64_t heapBuilds;
  uint64_t heapUpdates;
  uint64_t hashProbesTotal;
  uint64_t hashProbesMax;
  uint64_t runUpdaterRunsStarted;
  uint64_t runUpdaterFlushes;
  uint64_t runUpdaterTotalRunLen;
  uint64_t runUpdaterMaxRunLen;
  uint64_t runUpdaterSkippedEvents;
};

struct SimCandidateMinHeap
{
  SimCandidateMinHeap()
  {
    clear();
  }

  void clear()
  {
    size = 0;
    valid = false;
    for(int i = 0; i < K; ++i)
    {
      heap[i] = -1;
      pos[i] = -1;
    }
  }

  int heap[K];
  int pos[K];
  int size;
  bool valid;
};

	inline bool simCandidateStatsEnabledRuntime()
	{
	  static const bool enabled = []()
	  {
	    const char *env = getenv("LONGTARGET_PRINT_SIM_STATS");
    if(env == NULL || env[0] == '\0')
    {
      return false;
    }
    return env[0] != '0';
	}();
	  return enabled;
	}

	inline bool simBenchmarkEnabledRuntime()
	{
	  static const bool enabled = []()
	  {
	    const char *env = getenv("LONGTARGET_BENCHMARK");
	    if(env == NULL || env[0] == '\0')
	    {
	      return false;
	    }
	    return env[0] != '0';
	  }();
	  return enabled;
	}

	inline bool simCandidateRunUpdaterEnabledRuntime()
	{
	  static const bool enabled = []()
	  {
	    const char *env = getenv("LONGTARGET_SIM_RUN_UPDATER");
	    if(env == NULL || env[0] == '\0')
	    {
	      return false;
	    }
	    return env[0] != '0';
	  }();
	  return enabled;
	}

	inline bool simRegionCudaCandidateReduceEnabledRuntime()
	{
	  static const bool enabled = []()
	  {
	    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_REDUCE");
	    if(env == NULL || env[0] == '\0')
	    {
	      return false;
	    }
	    return env[0] != '0';
	  }();
	  return enabled;
	}

		inline bool simInitialCudaCandidateReduceEnabledRuntime()
		{
	  static const bool enabled = []()
	  {
	    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_REDUCE");
	    if(env == NULL || env[0] == '\0')
	    {
	      return false;
	    }
	    return env[0] != '0';
	  }();
		  return enabled;
		}

		inline bool simSafeStoreGpuEnabledRuntime()
		{
		  static const bool enabled = []()
		  {
		    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_STORE_GPU");
		    if(env == NULL || env[0] == '\0')
		    {
		      return false;
		    }
		    return env[0] != '0';
		  }();
		  return enabled;
		}

		inline bool simCudaWindowPipelineEnabledRuntime()
		{
		  static const bool enabled = []()
		  {
		    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_WINDOW_PIPELINE");
		    if(env == NULL || env[0] == '\0')
		    {
		      return false;
		    }
		    return env[0] != '0';
		  }();
		  return enabled;
		}

		inline bool simCudaWindowPipelineOverlapEnabledRuntime()
		{
		  static const bool enabled = []()
		  {
		    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_WINDOW_PIPELINE_OVERLAP");
		    if(env == NULL || env[0] == '\0')
		    {
		      return false;
		    }
		    return env[0] != '0';
		  }();
		  return enabled;
		}

		inline bool simCudaProposalLoopEnabledRuntime()
		{
		  static const bool enabled = []()
		  {
		    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_PROPOSAL_LOOP");
		    if(env == NULL || env[0] == '\0')
		    {
		      return false;
		    }
		    return env[0] != '0';
		  }();
		  return enabled;
		}

		inline bool simCudaDeviceKLoopEnabledRuntime()
		{
		  static const bool enabled = []()
		  {
		    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_DEVICE_K_LOOP");
		    if(env == NULL || env[0] == '\0')
		    {
		      return false;
		    }
		    return env[0] != '0';
		  }();
		  return enabled;
		}

			inline bool simInitialScanCudaEnabledRuntime()
			{
			  static const bool enabled = []()
			  {
			    if(simCudaWindowPipelineEnabledRuntime())
			    {
			      return true;
			    }
			    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA");
			    if(env == NULL || env[0] == '\0')
			    {
		      return false;
		    }
		    return env[0] != '0';
		  }();
		  return enabled;
		}

			inline bool simRegionScanCudaEnabledRuntime()
			{
			  static const bool enabled = []()
			  {
			    if(simCudaWindowPipelineEnabledRuntime())
			    {
			      return true;
			    }
			    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_REGION");
			    if(env == NULL || env[0] == '\0')
			    {
		      return false;
		    }
		    return env[0] != '0';
		  }();
		  return enabled;
		}

		inline bool simExactCudaFullEnabledRuntime()
		{
		  static const bool enabled = []()
		  {
		    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_FULL");
		    if(env == NULL || env[0] == '\0')
		    {
		      return false;
		    }
		    return env[0] != '0';
		  }();
		  return enabled;
		}

			inline bool simTracebackCudaEnabledRuntime()
			{
			  static const bool enabled = []()
			  {
			    if(simCudaWindowPipelineEnabledRuntime())
			    {
			      return true;
			    }
			    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK");
			    if(env == NULL || env[0] == '\0')
			    {
		      env = getenv("LONGTARGET_ENABLE_TRACEBACK_CUDA");
		    }
		    if(env == NULL || env[0] == '\0')
		    {
		      return false;
		    }
		    return env[0] != '0';
		  }();
		  return enabled;
		}

		inline bool simLocateCudaEnabledRuntime()
		{
		  static const bool enabled = []()
			  {
			    if(simCudaWindowPipelineEnabledRuntime())
			    {
			      return true;
			    }
			    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_LOCATE");
			    if(env == NULL || env[0] == '\0')
			    {
		      return false;
		    }
		    return env[0] != '0';
		  }();
		  return enabled;
		}

		enum SimProposalMaterializeBackend
		{
		  SIM_PROPOSAL_MATERIALIZE_BACKEND_CPU = 0,
		  SIM_PROPOSAL_MATERIALIZE_BACKEND_CUDA_BATCH_TRACEBACK = 1,
		  SIM_PROPOSAL_MATERIALIZE_BACKEND_HYBRID = 2
		};

		inline SimProposalMaterializeBackend parseSimProposalMaterializeBackend(const char *env)
		{
		  if(env == NULL || env[0] == '\0')
		  {
		    return SIM_PROPOSAL_MATERIALIZE_BACKEND_CPU;
		  }
		  if(strcmp(env,"cuda_batch_traceback") == 0)
		  {
		    return SIM_PROPOSAL_MATERIALIZE_BACKEND_CUDA_BATCH_TRACEBACK;
		  }
		  if(strcmp(env,"hybrid") == 0)
		  {
		    return SIM_PROPOSAL_MATERIALIZE_BACKEND_HYBRID;
		  }
		  return SIM_PROPOSAL_MATERIALIZE_BACKEND_CPU;
		}

		inline SimProposalMaterializeBackend simProposalMaterializeBackendRuntime()
		{
		  static const SimProposalMaterializeBackend backend = []()
		  {
		    return parseSimProposalMaterializeBackend(getenv("LONGTARGET_SIM_CUDA_PROPOSAL_MATERIALIZE_BACKEND"));
		  }();
		  return backend;
		}

		inline long simParseProposalTracebackMinCells(const char *env)
		{
		  if(env == NULL || env[0] == '\0')
		  {
		    return 65536;
		  }
		  char *end = NULL;
		  long parsed = strtol(env,&end,10);
		  if(end == env || parsed <= 0)
		  {
		    return 65536;
		  }
		  return parsed;
		}

		inline long simProposalTracebackMinCellsRuntime()
		{
		  static const long minCells = []()
		  {
		    return simParseProposalTracebackMinCells(getenv("LONGTARGET_SIM_CUDA_PROPOSAL_TRACEBACK_MIN_CELLS"));
		  }();
		  return minCells;
		}

		inline SimLocateCudaMode simLocateCudaModeRuntime()
		{
		  static const SimLocateCudaMode mode = []()
		  {
		    return parseSimLocateCudaMode(getenv("LONGTARGET_SIM_CUDA_LOCATE_MODE"));
		  }();
		  return mode;
		}

		inline SimLocateExactPrecheckMode simLocateExactPrecheckModeRuntime()
		{
		  static const SimLocateExactPrecheckMode mode = []()
		  {
		    return parseSimLocateExactPrecheckMode(getenv("LONGTARGET_SIM_CUDA_LOCATE_EXACT_PRECHECK"));
		  }();
		  return mode;
		}

			inline bool simSafeWindowCudaEnabledRuntime()
			{
			  static const bool enabled = []()
			  {
			    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WINDOW");
			    if(env == NULL || env[0] == '\0')
			    {
			      return true;
			    }
			    return strcmp(env,"0") != 0;
			  }();
			  return enabled;
			}

		inline int simSafeWindowCudaMaxCountRuntime()
		{
		  static const int maxCount = []()
			  {
			    const char *env = getenv("LONGTARGET_SIM_CUDA_SAFE_WINDOW_MAX_COUNT");
			    if(env == NULL || env[0] == '\0')
			    {
			      return 128;
			    }
			    char *end = NULL;
			    long parsed = strtol(env,&end,10);
			    if(end == env || parsed <= 0)
			    {
			      return 128;
			    }
			    if(parsed > 1024)
			    {
		      return 1024;
		    }
		    return static_cast<int>(parsed);
		  }();
		  return maxCount;
		}

inline bool simSafeWindowCompareBuilderRuntime()
{
		  static const bool enabled = []()
		  {
		    return parseSimSafeWindowCompareBuilder(getenv("LONGTARGET_SIM_CUDA_SAFE_WINDOW_COMPARE_BUILDER"),
		                                           simCudaValidateEnabledRuntime());
		  }();
  return enabled;
}

inline SimScanCudaSafeWindowPlannerMode simSafeWindowCudaPlannerModeRuntime()
{
  static const SimScanCudaSafeWindowPlannerMode mode =
    parseSimSafeWindowPlannerMode(getenv("LONGTARGET_SIM_CUDA_SAFE_WINDOW_PLANNER"));
  return mode;
}

inline bool simSafeWindowGeometryTelemetryRuntime()
{
  static const bool enabled = []()
  {
    const char *env = getenv("LONGTARGET_SIM_CUDA_SAFE_WINDOW_GEOMETRY_TELEMETRY");
    return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
  }();
  return enabled;
}

inline bool simRegionSchedulerShapeTelemetryRuntime()
{
  static const bool enabled = []()
  {
    const char *env = getenv("LONGTARGET_SIM_CUDA_REGION_SCHEDULER_SHAPE_TELEMETRY");
    return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
  }();
  return enabled;
}

inline SimSafeWindowExecGeometry simSafeWindowExecGeometryRuntime()
{
  static const SimSafeWindowExecGeometry geometry =
    parseSimSafeWindowExecGeometry(getenv("LONGTARGET_SIM_CUDA_SAFE_WINDOW_EXEC_GEOMETRY"));
  return geometry;
}

inline bool simSafeWindowFineShadowEnabledRuntime()
{
  static const bool enabled = []()
  {
    const char *env = getenv("LONGTARGET_SIM_CUDA_SAFE_WINDOW_FINE_SHADOW");
    return env != NULL && env[0] != '\0' && strcmp(env,"0") != 0;
  }();
  return enabled;
}

			inline bool simLocateCudaFastShadowEnabledRuntime()
			{
		  static const bool enabled = []()
		  {
		    const char *env = getenv("LONGTARGET_SIM_CUDA_LOCATE_FAST_SHADOW");
		    if(env == NULL || env[0] == '\0')
		    {
		      return false;
		    }
		    return env[0] != '0';
		  }();
		  return enabled;
		}

		inline bool simCudaLocateDeviceKLoopEnabledRuntime()
		{
		  static const bool enabled = []()
		  {
		    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_LOCATE_DEVICE_K_LOOP");
		    if(env == NULL || env[0] == '\0')
		    {
		      return false;
		    }
		    return env[0] != '0';
		  }();
		  return enabled &&
		         simLocateCudaEnabledRuntime() &&
		         !simLocateCudaFastShadowEnabledRuntime() &&
		         simLocateCudaModeRuntime() == SIM_LOCATE_CUDA_MODE_SAFE_WORKSET;
		}

		inline bool simCudaMainlineResidencyEnabledRuntime()
		{
		  return simInitialCudaCandidateReduceEnabledRuntime() &&
		         simCudaProposalLoopEnabledRuntime() &&
		         simCudaDeviceKLoopEnabledRuntime() &&
		         simLocateCudaEnabledRuntime() &&
		         !simLocateCudaFastShadowEnabledRuntime() &&
		         simLocateCudaModeRuntime() == SIM_LOCATE_CUDA_MODE_SAFE_WORKSET;
		}

			inline bool simCudaRegionResidencyMaintenanceEnabledRuntime()
			{
			  static const bool enabled = []()
			  {
			    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_REGION_RESIDENCY_MAINTENANCE");
		    if(env == NULL || env[0] == '\0')
		    {
		      return false;
		    }
		    return env[0] != '0';
			  }();
			  return enabled && simCudaMainlineResidencyEnabledRuntime();
			}

		inline bool simCudaSafeWorksetDeviceMaintenanceEnabledRuntime()
		{
		  const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_SAFE_WORKSET_DEVICE_MAINTENANCE");
		  if(env == NULL || env[0] == '\0')
		  {
			    return false;
			  }
			  return env[0] != '0' &&
			         simLocateCudaEnabledRuntime() &&
			         !simLocateCudaFastShadowEnabledRuntime() &&
			         simLocateCudaModeRuntime() == SIM_LOCATE_CUDA_MODE_SAFE_WORKSET;
		}

inline bool simCudaInitialSafeStoreHandoffEnabledRuntime()
{
  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_HANDOFF");
  if(env == NULL || env[0] == '\0')
  {
    env = getenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_SAFE_STORE_DEVICE_MAINTENANCE");
  }
  if(env == NULL || env[0] == '\0')
  {
    return false;
  }
  return env[0] != '0' &&
         simLocateCudaEnabledRuntime() &&
         !simLocateCudaFastShadowEnabledRuntime() &&
         simLocateCudaModeRuntime() == SIM_LOCATE_CUDA_MODE_SAFE_WORKSET &&
         !simCudaProposalLoopEnabledRuntime();
}

inline bool simCudaInitialSafeStoreHandoffRequestedRuntime()
{
  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_HANDOFF");
  if(env == NULL || env[0] == '\0')
  {
    env = getenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_SAFE_STORE_DEVICE_MAINTENANCE");
  }
  return env != NULL && env[0] != '\0' && env[0] != '0';
}

inline bool simCudaInitialSafeStoreDeviceMaintenanceEnabledRuntime()
{
  return simCudaInitialSafeStoreHandoffEnabledRuntime();
}

				struct SimInitialContextApplyChunkSkipStats
				{
				  SimInitialContextApplyChunkSkipStats():
				    chunkCount(0),
			    chunkReplayedCount(0),
			    chunkSkippedCount(0),
			    summaryReplayedCount(0),
			    summarySkippedCount(0)
			  {
			  }

			  uint64_t chunkCount;
			  uint64_t chunkReplayedCount;
			  uint64_t chunkSkippedCount;
			  uint64_t summaryReplayedCount;
				  uint64_t summarySkippedCount;
				};

				struct SimInitialCpuFrontierFastApplyStats
				{
				  SimInitialCpuFrontierFastApplyStats():
				    summariesReplayed(0),
				    candidatesOut(0)
				  {
				  }

				  uint64_t summariesReplayed;
				  uint64_t candidatesOut;
				};

				enum SimInitialChunkedHandoffFallbackReason
				{
				  SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_NONE = 0,
				  SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_UNSUPPORTED_FAST_APPLY = 1,
				  SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_UNSUPPORTED_SHAPE = 2,
				  SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_PINNED_ALLOCATION = 3,
				  SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_PAGEABLE_COPY = 4,
				  SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_SYNC_COPY = 5
				};

					struct SimInitialChunkedHandoffStats
					{
				  SimInitialChunkedHandoffStats():
				    chunkCount(0),
				    summariesReplayed(0),
				    rowsPerChunk(0),
				    ringSlots(0),
				    pinnedAllocationFailures(0),
				    pageableFallbacks(0),
				    syncCopies(0),
				    cpuWaitNanoseconds(0),
				    criticalPathD2HNanoseconds(0),
				    measuredOverlapNanoseconds(0),
				    fallbackCount(0),
				    fallbackReason(SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_NONE)
				  {
				  }

				  uint64_t chunkCount;
				  uint64_t summariesReplayed;
				  uint64_t rowsPerChunk;
				  uint64_t ringSlots;
				  uint64_t pinnedAllocationFailures;
				  uint64_t pageableFallbacks;
				  uint64_t syncCopies;
				  uint64_t cpuWaitNanoseconds;
				  uint64_t criticalPathD2HNanoseconds;
				  uint64_t measuredOverlapNanoseconds;
				  uint64_t fallbackCount;
					  SimInitialChunkedHandoffFallbackReason fallbackReason;
					};

					struct SimInitialPinnedAsyncHandoffStats
					{
					  SimInitialPinnedAsyncHandoffStats():
					    requestedCount(0),
					    activeCount(0),
					    disabledReason(SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_NOT_REQUESTED),
					    sourceReadyMode(SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_SOURCE_READY_NONE),
					    cpuPipelineRequestedCount(0),
					    cpuPipelineActiveCount(0),
					    cpuPipelineDisabledReason(
					      SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_NOT_REQUESTED),
					    cpuPipelineChunksApplied(0),
					    cpuPipelineSummariesApplied(0),
					    cpuPipelineChunksFinalized(0),
					    cpuPipelineFinalizeCount(0),
					    cpuPipelineOutOfOrderChunks(0),
					    chunkCount(0),
					    pinnedSlots(0),
					    pinnedBytes(0),
					    pinnedAllocationFailures(0),
					    pageableFallbacks(0),
					    syncCopies(0),
					    asyncCopies(0),
					    slotReuseWaits(0),
					    slotsReusedAfterMaterializeCount(0),
					    asyncD2HNanoseconds(0),
					    d2hWaitNanoseconds(0),
					    cpuApplyNanoseconds(0),
					    cpuD2HOverlapNanoseconds(0),
					    dpD2HOverlapNanoseconds(0),
					    criticalPathNanoseconds(0)
					  {
					  }

					  uint64_t requestedCount;
					  uint64_t activeCount;
					  SimScanCudaInitialPinnedAsyncDisabledReason disabledReason;
					  SimScanCudaInitialPinnedAsyncSourceReadyMode sourceReadyMode;
					  uint64_t cpuPipelineRequestedCount;
					  uint64_t cpuPipelineActiveCount;
					  SimScanCudaInitialPinnedAsyncCpuPipelineDisabledReason cpuPipelineDisabledReason;
					  uint64_t cpuPipelineChunksApplied;
					  uint64_t cpuPipelineSummariesApplied;
					  uint64_t cpuPipelineChunksFinalized;
					  uint64_t cpuPipelineFinalizeCount;
					  uint64_t cpuPipelineOutOfOrderChunks;
					  uint64_t chunkCount;
					  uint64_t pinnedSlots;
					  uint64_t pinnedBytes;
					  uint64_t pinnedAllocationFailures;
					  uint64_t pageableFallbacks;
					  uint64_t syncCopies;
					  uint64_t asyncCopies;
					  uint64_t slotReuseWaits;
					  uint64_t slotsReusedAfterMaterializeCount;
					  uint64_t asyncD2HNanoseconds;
					  uint64_t d2hWaitNanoseconds;
					  uint64_t cpuApplyNanoseconds;
					  uint64_t cpuD2HOverlapNanoseconds;
					  uint64_t dpD2HOverlapNanoseconds;
					  uint64_t criticalPathNanoseconds;
					};

					struct SimInitialCpuFrontierFastApplyTelemetry
				{
				  SimInitialCpuFrontierFastApplyTelemetry():
				    enabledCount(0),
				    attempts(0),
				    successes(0),
				    fallbacks(0),
				    shadowMismatches(0),
				    summariesReplayed(0),
				    candidatesOut(0),
				    fastApplyNanoseconds(0),
				    oracleApplyNanosecondsShadow(0),
				    rejectedByStats(0),
				    rejectedByNonemptyContext(0)
				  {
				  }

				  uint64_t enabledCount;
				  uint64_t attempts;
				  uint64_t successes;
				  uint64_t fallbacks;
				  uint64_t shadowMismatches;
				  uint64_t summariesReplayed;
				  uint64_t candidatesOut;
				  uint64_t fastApplyNanoseconds;
				  uint64_t oracleApplyNanosecondsShadow;
				  uint64_t rejectedByStats;
				  uint64_t rejectedByNonemptyContext;
				};

				inline bool simCudaInitialContextApplyChunkSkipEnabledRuntime()
				{
				  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_CONTEXT_APPLY_CHUNK_SKIP");
			  if(env == NULL || env[0] == '\0')
			  {
			    return false;
			  }
				  return env[0] != '0';
				}

					inline bool simCudaInitialChunkedHandoffEnabledRuntime()
					{
					  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF");
					  return env != NULL && env[0] != '\0' && env[0] != '0';
					}

					inline bool simCudaInitialPinnedAsyncHandoffEnabledRuntime()
					{
					  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_HANDOFF");
					  return env != NULL && env[0] != '\0' && env[0] != '0';
					}

					inline bool simCudaInitialPinnedAsyncCpuPipelineEnabledRuntime()
					{
					  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE");
					  return env != NULL && env[0] != '\0' && env[0] != '0';
					}

				inline bool simCudaInitialExactFrontierReplayEnabledRuntime()
				{
				  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY");
				  return env != NULL && env[0] != '\0' && env[0] != '0' &&
				         !simCudaProposalLoopEnabledRuntime();
				}

				inline int simCudaInitialChunkedHandoffChunkRowsRuntime()
				{
				  const int defaultChunkRows = 256;
				  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_ROWS_PER_CHUNK");
				  if(env == NULL || env[0] == '\0')
				  {
				    env = getenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNK_ROWS");
				  }
				  if(env == NULL || env[0] == '\0')
				  {
				    env = getenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF_CHUNK_ROWS");
				  }
				  if(env == NULL || env[0] == '\0')
				  {
				    return defaultChunkRows;
				  }
				  char *end = NULL;
				  const long parsed = strtol(env,&end,10);
				  if(end == env || parsed <= 0)
				  {
				    return defaultChunkRows;
				  }
				  if(parsed > 8192)
				  {
				    return 8192;
				  }
				  return static_cast<int>(parsed);
				}

				inline const char *simCudaInitialChunkedHandoffChunkRowsSourceLabelRuntime()
				{
				  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_ROWS_PER_CHUNK");
				  if(env != NULL && env[0] != '\0')
				  {
				    return "canonical_env";
				  }
				  env = getenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNK_ROWS");
				  if(env != NULL && env[0] != '\0')
				  {
				    return "short_env";
				  }
				  env = getenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF_CHUNK_ROWS");
				  if(env != NULL && env[0] != '\0')
				  {
				    return "compat_env";
				  }
				  return "default";
				}

				inline int simCudaInitialChunkedHandoffRingSlotsRuntime()
				{
				  const int defaultRingSlots = 3;
				  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_RING_SLOTS");
				  if(env == NULL || env[0] == '\0')
				  {
				    env = getenv("LONGTARGET_SIM_CUDA_INITIAL_RING_SLOTS");
				  }
				  if(env == NULL || env[0] == '\0')
				  {
				    env = getenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF_RING_SLOTS");
				  }
				  if(env == NULL || env[0] == '\0')
				  {
				    return defaultRingSlots;
				  }
				  char *end = NULL;
				  const long parsed = strtol(env,&end,10);
				  if(end == env || parsed <= 0)
				  {
				    return defaultRingSlots;
				  }
				  if(parsed > 16)
				  {
				    return 16;
				  }
				  return static_cast<int>(parsed);
				}

				inline const char *simCudaInitialChunkedHandoffRingSlotsSourceLabelRuntime()
				{
				  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_RING_SLOTS");
				  if(env != NULL && env[0] != '\0')
				  {
				    return "canonical_env";
				  }
				  env = getenv("LONGTARGET_SIM_CUDA_INITIAL_RING_SLOTS");
				  if(env != NULL && env[0] != '\0')
				  {
				    return "short_env";
				  }
				  env = getenv("LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF_RING_SLOTS");
				  if(env != NULL && env[0] != '\0')
				  {
				    return "compat_env";
				  }
				  return "default";
				}

				inline bool simCudaInitialCpuFrontierFastApplyEnabledRuntime()
				{
				  const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_CPU_FRONTIER_FAST_APPLY");
				  return env != NULL && env[0] != '\0' && env[0] != '0';
				}

				inline bool simCudaInitialCpuFrontierFastApplyShadowEnabledRuntime()
				{
				  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_CPU_FRONTIER_FAST_APPLY_SHADOW");
				  return env != NULL && env[0] != '\0' && env[0] != '0';
				}

				inline int simCudaInitialContextApplyChunkSkipChunkSize()
				{
			  return 256;
			}

				inline bool simCudaInitialFrontierTransducerShadowEnabledRuntime()
				{
				  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_FRONTIER_TRANSDUCER_SHADOW");
			  if(env == NULL || env[0] == '\0')
			  {
			    return false;
			  }
			  return env[0] != '0' && !simCudaProposalLoopEnabledRuntime();
			}

			inline bool simCudaInitialOrderedSegmentedV3ShadowEnabledRuntime()
			{
			  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_ORDERED_SEGMENTED_V3_SHADOW");
			  if(env == NULL || env[0] == '\0')
			  {
			    return false;
			  }
			  return env[0] != '0';
			}

			inline int simCudaInitialFrontierTransducerShadowChunkSizeRuntime()
			{
			  const int defaultChunkSize = 256;
			  const char *env = getenv("LONGTARGET_SIM_CUDA_INITIAL_FRONTIER_TRANSDUCER_SHADOW_CHUNK_SIZE");
			  if(env == NULL || env[0] == '\0')
			  {
			    return defaultChunkSize;
			  }
			  char *end = NULL;
			  const long parsed = strtol(env,&end,10);
			  if(end == env || parsed <= 0)
			  {
			    return defaultChunkSize;
			  }
			  if(parsed > 4096)
			  {
			    return 4096;
			  }
			  return static_cast<int>(parsed);
			}

			inline bool simCudaInitialProposalResidencyEnabledRuntime()
			{
		  static const bool enabled = []()
		  {
		    const char *env = getenv("LONGTARGET_ENABLE_SIM_CUDA_INITIAL_PROPOSAL_RESIDENCY");
		    if(env == NULL || env[0] == '\0')
		    {
		      return false;
		    }
		    return env[0] != '0';
		  }();
		  return enabled &&
		         simInitialCudaCandidateReduceEnabledRuntime() &&
		         simCudaProposalLoopEnabledRuntime() &&
		         simCudaDeviceKLoopEnabledRuntime() &&
		         simLocateCudaEnabledRuntime() &&
		         !simLocateCudaFastShadowEnabledRuntime() &&
		         simLocateCudaModeRuntime() == SIM_LOCATE_CUDA_MODE_SAFE_WORKSET;
		}

		inline bool simCudaInitialReduceRequestEnabledRuntime()
		{
		  if(simCudaInitialExactFrontierReplayEnabledRuntime())
		  {
		    return true;
		  }
		  return simInitialCudaCandidateReduceEnabledRuntime() &&
		         !simCudaInitialProposalResidencyEnabledRuntime() &&
		         (!simCudaProposalLoopEnabledRuntime() ||
		          simCudaMainlineResidencyEnabledRuntime());
		}

		inline bool simCudaInitialProposalRequestEnabledRuntime()
		{
		  return simCudaProposalLoopEnabledRuntime() &&
		         (!simCudaMainlineResidencyEnabledRuntime() ||
		          simCudaInitialProposalResidencyEnabledRuntime());
		}

		inline bool simCudaInitialReducePersistOnDeviceRuntime()
		{
		  return simCudaInitialReduceRequestEnabledRuntime() &&
		         simLocateCudaEnabledRuntime() &&
		         !simLocateCudaFastShadowEnabledRuntime() &&
		         simLocateCudaModeRuntime() == SIM_LOCATE_CUDA_MODE_SAFE_WORKSET;
		}

		inline int simLocateCudaFastPadRuntime()
		{
		  static const int pad = []()
		  {
		    const char *env = getenv("LONGTARGET_SIM_CUDA_LOCATE_FAST_PAD");
		    if(env == NULL || env[0] == '\0')
		    {
		      return 128;
		    }
		    char *end = NULL;
		    long parsed = strtol(env,&end,10);
		    if(end == env)
		    {
		      return 128;
		    }
		    if(parsed <= 0)
		    {
		      return 0;
		    }
		    if(parsed > 4096L)
		    {
		      return 4096;
		    }
		    return static_cast<int>(parsed);
		  }();
		  return pad;
		}

		inline bool simTracebackCudaFallbackOnTieEnabledRuntime()
		{
		  static const bool enabled = []()
		  {
		    const char *env = getenv("LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE");
		    if(env == NULL || env[0] == '\0')
		    {
		      env = getenv("LONGTARGET_TRACEBACK_CUDA_FALLBACK_ON_TIE");
		    }
		    if(env == NULL || env[0] == '\0')
		    {
		      return true;
		    }
		    return env[0] != '0';
		  }();
		  return enabled;
		}

		inline int simTracebackCudaMaxDimRuntime()
		{
		  static const int maxDim = []()
		  {
		    const char *env = getenv("LONGTARGET_SIM_CUDA_TRACEBACK_MAX_DIM");
		    if(env == NULL || env[0] == '\0')
		    {
		      env = getenv("LONGTARGET_TRACEBACK_CUDA_MAX_DIM");
		    }
		    if(env == NULL || env[0] == '\0')
		    {
		      return 8192;
		    }
		    char *end = NULL;
		    long parsed = strtol(env, &end, 10);
		    if(end == env)
		    {
		      return 8192;
		    }
		    if(parsed <= 0)
		    {
		      return 8192;
		    }
		    if(parsed > 200000L)
		    {
		      return 200000;
		    }
		    return static_cast<int>(parsed);
		  }();
		  return maxDim;
		}

		inline long long simTracebackCudaMaxCellsRuntime()
		{
		  static const long long maxCells = []()
		  {
		    const char *env = getenv("LONGTARGET_SIM_CUDA_TRACEBACK_MAX_CELLS");
		    if(env == NULL || env[0] == '\0')
		    {
		      env = getenv("LONGTARGET_TRACEBACK_CUDA_MAX_CELLS");
		    }
		    if(env == NULL || env[0] == '\0')
		    {
		      return 8192ll * 8192ll;
		    }
		    char *end = NULL;
		    long long parsed = strtoll(env, &end, 10);
		    if(end == env)
		    {
		      return 8192ll * 8192ll;
		    }
		    if(parsed <= 0)
		    {
		      return 8192ll * 8192ll;
		    }
		    if(parsed > 20000000000ll)
		    {
		      return 20000000000ll;
		    }
		    return parsed;
		  }();
		  return maxCells;
		}

		inline bool simWriteAlignStringsEnabledRuntime()
		{
		  static const bool enabled = []()
		  {
		    const char *env = getenv("LONGTARGET_OUTPUT_MODE");
		    if(env == NULL || env[0] == '\0')
		    {
		      return true;
		    }
		    string value(env);
		    for(size_t i = 0; i < value.size(); ++i)
		    {
		      value[i] = static_cast<char>(tolower(static_cast<unsigned char>(value[i])));
		    }
		    if(value == "lite" || value == "tfosorted-lite" || value == "tfo-lite")
		    {
		      return false;
		    }
		    return true;
		  }();
		  return enabled;
		}

			inline bool simFastEnabledRuntime()
			{
			  static const bool enabled = []()
			  {
			    const char *env = getenv("LONGTARGET_SIM_FAST");
			    if(env == NULL || env[0] == '\0')
			    {
			      return false;
			    }
			    return env[0] != '0';
			  }();
			  return enabled;
			}

			inline int simFastUpdateBudgetRuntime()
			{
			  static const int budget = []()
			  {
			    const char *env = getenv("LONGTARGET_SIM_FAST_UPDATE_BUDGET");
			    if(env == NULL || env[0] == '\0')
			    {
			      return 0;
			    }
			    char *end = NULL;
			    long parsed = strtol(env,&end,10);
			    if(end == env)
			    {
			      return 0;
			    }
			    if(parsed <= 0)
			    {
			      return 0;
			    }
			    if(parsed > 1000000L)
			    {
			      return 1000000;
			    }
			    return static_cast<int>(parsed);
			  }();
			  return budget;
			}

			inline bool simFastUpdateOnFailEnabledRuntime()
			{
			  static const bool enabled = []()
			  {
			    const char *env = getenv("LONGTARGET_SIM_FAST_UPDATE_ON_FAIL");
			    if(env == NULL || env[0] == '\0')
			    {
			      return false;
			    }
			    return env[0] != '0';
			  }();
			  return enabled;
			}

	inline bool simCudaValidateEnabledRuntime()
	{
	  static const bool enabled = []()
	  {
	    const char *env = getenv("LONGTARGET_SIM_CUDA_VALIDATE");
	    if(env == NULL || env[0] == '\0')
	    {
	      return false;
	    }
	    return env[0] != '0';
	  }();
	  return enabled;
	}

		inline std::atomic<uint64_t> &simInitialScanCpuCallCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simScanTaskCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simScanLaunchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline void recordSimScanBatch(uint64_t taskCount,uint64_t launchCount)
		{
		  simScanTaskCount().fetch_add(taskCount, std::memory_order_relaxed);
		  simScanLaunchCount().fetch_add(launchCount, std::memory_order_relaxed);
		}

		inline void getSimScanExecutionCounts(uint64_t &taskCount,uint64_t &launchCount)
		{
		  taskCount = simScanTaskCount().load(std::memory_order_relaxed);
		  launchCount = simScanLaunchCount().load(std::memory_order_relaxed);
		}

		inline std::atomic<uint64_t> &simWindowPipelineBatchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simWindowPipelineTaskBatchedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

			inline std::atomic<uint64_t> &simWindowPipelineTaskFallbackCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			enum SimWindowPipelineIneligibleReason
			{
			  SIM_WINDOW_PIPELINE_INELIGIBLE_RUNTIME_DISABLED = 0,
			  SIM_WINDOW_PIPELINE_INELIGIBLE_TWO_STAGE = 1,
			  SIM_WINDOW_PIPELINE_INELIGIBLE_SIM_FAST = 2,
			  SIM_WINDOW_PIPELINE_INELIGIBLE_VALIDATE = 3,
			  SIM_WINDOW_PIPELINE_INELIGIBLE_QUERY_GT_8192 = 4,
			  SIM_WINDOW_PIPELINE_INELIGIBLE_TARGET_GT_8192 = 5,
			  SIM_WINDOW_PIPELINE_INELIGIBLE_NEGATIVE_MIN_SCORE = 6
			};

			inline std::atomic<uint64_t> &simWindowPipelineTaskConsideredCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simWindowPipelineTaskEligibleCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simWindowPipelineIneligibleRuntimeDisabledCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simWindowPipelineIneligibleTwoStageCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simWindowPipelineIneligibleSimFastCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simWindowPipelineIneligibleValidateCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simWindowPipelineIneligibleQueryGt8192Count()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simWindowPipelineIneligibleTargetGt8192Count()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simWindowPipelineIneligibleNegativeMinScoreCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simWindowPipelineBatchRuntimeFallbackCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline void recordSimWindowPipelineBatch(uint64_t taskCount)
			{
			  simWindowPipelineBatchCount().fetch_add(1, std::memory_order_relaxed);
			  simWindowPipelineTaskBatchedCount().fetch_add(taskCount, std::memory_order_relaxed);
		}

			inline void recordSimWindowPipelineFallback(uint64_t taskCount = 1)
			{
			  simWindowPipelineTaskFallbackCount().fetch_add(taskCount, std::memory_order_relaxed);
			}

			inline void recordSimWindowPipelineTaskConsidered(uint64_t taskCount = 1)
			{
			  simWindowPipelineTaskConsideredCount().fetch_add(taskCount, std::memory_order_relaxed);
			}

			inline void recordSimWindowPipelineTaskEligible(uint64_t taskCount = 1)
			{
			  simWindowPipelineTaskEligibleCount().fetch_add(taskCount, std::memory_order_relaxed);
			}

			inline void recordSimWindowPipelineIneligibleTask(SimWindowPipelineIneligibleReason reason,
			                                                 uint64_t taskCount = 1)
			{
			  switch(reason)
			  {
			    case SIM_WINDOW_PIPELINE_INELIGIBLE_TWO_STAGE:
			      simWindowPipelineIneligibleTwoStageCount().fetch_add(taskCount, std::memory_order_relaxed);
			      break;
			    case SIM_WINDOW_PIPELINE_INELIGIBLE_SIM_FAST:
			      simWindowPipelineIneligibleSimFastCount().fetch_add(taskCount, std::memory_order_relaxed);
			      break;
			    case SIM_WINDOW_PIPELINE_INELIGIBLE_VALIDATE:
			      simWindowPipelineIneligibleValidateCount().fetch_add(taskCount, std::memory_order_relaxed);
			      break;
			    case SIM_WINDOW_PIPELINE_INELIGIBLE_QUERY_GT_8192:
			      simWindowPipelineIneligibleQueryGt8192Count().fetch_add(taskCount, std::memory_order_relaxed);
			      break;
			    case SIM_WINDOW_PIPELINE_INELIGIBLE_TARGET_GT_8192:
			      simWindowPipelineIneligibleTargetGt8192Count().fetch_add(taskCount, std::memory_order_relaxed);
			      break;
			    case SIM_WINDOW_PIPELINE_INELIGIBLE_NEGATIVE_MIN_SCORE:
			      simWindowPipelineIneligibleNegativeMinScoreCount().fetch_add(taskCount, std::memory_order_relaxed);
			      break;
			    case SIM_WINDOW_PIPELINE_INELIGIBLE_RUNTIME_DISABLED:
			    default:
			      simWindowPipelineIneligibleRuntimeDisabledCount().fetch_add(taskCount, std::memory_order_relaxed);
			      break;
			  }
			}

			inline void recordSimWindowPipelineBatchRuntimeFallback(uint64_t taskCount = 1)
			{
			  simWindowPipelineBatchRuntimeFallbackCount().fetch_add(taskCount, std::memory_order_relaxed);
			}

		inline std::atomic<uint64_t> &simWindowPipelineOverlapBatchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline void recordSimWindowPipelineOverlapBatch(uint64_t batchCount = 1)
		{
		  simWindowPipelineOverlapBatchCount().fetch_add(batchCount, std::memory_order_relaxed);
		}

		inline void getSimWindowPipelineStats(uint64_t &batchCount,
		                                     uint64_t &taskBatchedCount,
		                                     uint64_t &taskFallbackCount)
		{
		  batchCount = simWindowPipelineBatchCount().load(std::memory_order_relaxed);
		  taskBatchedCount = simWindowPipelineTaskBatchedCount().load(std::memory_order_relaxed);
		  taskFallbackCount = simWindowPipelineTaskFallbackCount().load(std::memory_order_relaxed);
		}

			inline uint64_t getSimWindowPipelineOverlapBatchCount()
			{
			  return simWindowPipelineOverlapBatchCount().load(std::memory_order_relaxed);
			}

			inline void getSimWindowPipelineEligibilityStats(uint64_t &taskConsideredCount,
			                                                uint64_t &taskEligibleCount,
			                                                uint64_t &ineligibleTwoStageCount,
			                                                uint64_t &ineligibleSimFastCount,
			                                                uint64_t &ineligibleValidateCount,
			                                                uint64_t &ineligibleRuntimeDisabledCount,
			                                                uint64_t &ineligibleQueryGt8192Count,
			                                                uint64_t &ineligibleTargetGt8192Count,
			                                                uint64_t &ineligibleNegativeMinScoreCount,
			                                                uint64_t &batchRuntimeFallbackCount)
			{
			  taskConsideredCount = simWindowPipelineTaskConsideredCount().load(std::memory_order_relaxed);
			  taskEligibleCount = simWindowPipelineTaskEligibleCount().load(std::memory_order_relaxed);
			  ineligibleTwoStageCount = simWindowPipelineIneligibleTwoStageCount().load(std::memory_order_relaxed);
			  ineligibleSimFastCount = simWindowPipelineIneligibleSimFastCount().load(std::memory_order_relaxed);
			  ineligibleValidateCount = simWindowPipelineIneligibleValidateCount().load(std::memory_order_relaxed);
			  ineligibleRuntimeDisabledCount = simWindowPipelineIneligibleRuntimeDisabledCount().load(std::memory_order_relaxed);
			  ineligibleQueryGt8192Count = simWindowPipelineIneligibleQueryGt8192Count().load(std::memory_order_relaxed);
			  ineligibleTargetGt8192Count = simWindowPipelineIneligibleTargetGt8192Count().load(std::memory_order_relaxed);
			  ineligibleNegativeMinScoreCount = simWindowPipelineIneligibleNegativeMinScoreCount().load(std::memory_order_relaxed);
			  batchRuntimeFallbackCount = simWindowPipelineBatchRuntimeFallbackCount().load(std::memory_order_relaxed);
			}

		inline std::atomic<uint64_t> &simInitialScanCudaCallCount()
		{
		  static std::atomic<uint64_t> count(0);
	  return count;
	}

		inline void recordSimInitialScanBackend(bool usedCuda,uint64_t taskCount = 1,uint64_t launchCount = 1)
		{
		  recordSimScanBatch(taskCount,launchCount);
		  if(usedCuda)
		  {
		    simInitialScanCudaCallCount().fetch_add(1, std::memory_order_relaxed);
	  }
	  else
	  {
	    simInitialScanCpuCallCount().fetch_add(1, std::memory_order_relaxed);
	  }
	}

		inline void getSimInitialScanBackendCounts(uint64_t &cpuCalls,uint64_t &cudaCalls)
		{
		  cpuCalls = simInitialScanCpuCallCount().load(std::memory_order_relaxed);
		  cudaCalls = simInitialScanCudaCallCount().load(std::memory_order_relaxed);
		}

		inline std::atomic<uint64_t> &simRegionScanCpuCallCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionScanCudaCallCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

			inline void recordSimRegionScanBackend(bool usedCuda,uint64_t taskCount = 1,uint64_t launchCount = 1)
			{
			  recordSimScanBatch(taskCount,launchCount);
			  if(usedCuda)
			  {
			    simRegionScanCudaCallCount().fetch_add(1, std::memory_order_relaxed);
		  }
		  else
		  {
		    simRegionScanCpuCallCount().fetch_add(1, std::memory_order_relaxed);
		  }
		}

		inline void getSimRegionScanBackendCounts(uint64_t &cpuCalls,uint64_t &cudaCalls)
		{
		  cpuCalls = simRegionScanCpuCallCount().load(std::memory_order_relaxed);
		  cudaCalls = simRegionScanCudaCallCount().load(std::memory_order_relaxed);
		}

		inline std::atomic<uint64_t> &simLocateCpuCallCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simLocateCudaCallCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline void recordSimLocateBackend(bool usedCuda)
		{
		  if(usedCuda)
		  {
		    simLocateCudaCallCount().fetch_add(1, std::memory_order_relaxed);
		  }
		  else
		  {
		    simLocateCpuCallCount().fetch_add(1, std::memory_order_relaxed);
		  }
		}

		inline void getSimLocateBackendCounts(uint64_t &cpuCalls,uint64_t &cudaCalls)
		{
		  cpuCalls = simLocateCpuCallCount().load(std::memory_order_relaxed);
		  cudaCalls = simLocateCudaCallCount().load(std::memory_order_relaxed);
		}

		inline std::atomic<uint64_t> &simLocateExactModeCallCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simLocateFastModeCallCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simLocateSafeWorksetModeCallCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simLocateFastFallbackCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline void recordSimLocateMode(SimLocateCudaMode mode)
		{
		  if(mode == SIM_LOCATE_CUDA_MODE_FAST)
		  {
		    simLocateFastModeCallCount().fetch_add(1, std::memory_order_relaxed);
		  }
		  else if(mode == SIM_LOCATE_CUDA_MODE_SAFE_WORKSET)
		  {
		    simLocateSafeWorksetModeCallCount().fetch_add(1, std::memory_order_relaxed);
		  }
		  else
		  {
		    simLocateExactModeCallCount().fetch_add(1, std::memory_order_relaxed);
		  }
		}

		inline void recordSimLocateMode(bool usedFastMode)
		{
		  recordSimLocateMode(usedFastMode ? SIM_LOCATE_CUDA_MODE_FAST : SIM_LOCATE_CUDA_MODE_EXACT);
		}

		inline void recordSimLocateFastFallback()
		{
		  simLocateFastFallbackCount().fetch_add(1, std::memory_order_relaxed);
		}

		inline void getSimLocateModeCounts(uint64_t &exactCalls,
		                                  uint64_t &fastCalls,
		                                  uint64_t &safeWorksetCalls,
		                                  uint64_t &fastFallbacks)
		{
		  exactCalls = simLocateExactModeCallCount().load(std::memory_order_relaxed);
		  fastCalls = simLocateFastModeCallCount().load(std::memory_order_relaxed);
		  safeWorksetCalls = simLocateSafeWorksetModeCallCount().load(std::memory_order_relaxed);
		  fastFallbacks = simLocateFastFallbackCount().load(std::memory_order_relaxed);
		}

		inline void getSimLocateModeCounts(uint64_t &exactCalls,
		                                  uint64_t &fastCalls,
		                                  uint64_t &fastFallbacks)
		{
		  uint64_t safeWorksetCalls = 0;
		  getSimLocateModeCounts(exactCalls,fastCalls,safeWorksetCalls,fastFallbacks);
		}

		enum SimSafeWorksetFallbackReason
		{
		  SIM_SAFE_WORKSET_FALLBACK_INVALID_STORE = 0,
		  SIM_SAFE_WORKSET_FALLBACK_NO_AFFECTED_START = 1,
		  SIM_SAFE_WORKSET_FALLBACK_NO_WORKSET = 2,
		  SIM_SAFE_WORKSET_FALLBACK_INVALID_BANDS = 3,
		  SIM_SAFE_WORKSET_FALLBACK_SCAN_FAILURE = 4,
		  SIM_SAFE_WORKSET_FALLBACK_SHADOW_MISMATCH = 5
		};

		inline std::atomic<uint64_t> &simSafeWorksetPassCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetFallbackInvalidStoreCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetFallbackNoAffectedStartCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetFallbackNoWorksetCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetFallbackInvalidBandsCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetFallbackScanFailureCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetFallbackShadowMismatchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetAffectedStartCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetUniqueAffectedStartCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetInputBandCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetInputCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetExecBandCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetExecCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetCudaTaskCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetCudaLaunchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetCudaTrueBatchRequestCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetReturnedStateCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetBuildNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetMergeNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWorksetTotalNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeStoreRefreshAttemptCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeStoreRefreshSuccessCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeStoreRefreshFailureCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeStoreRefreshTrackedStartCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeStoreRefreshGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeStoreRefreshD2hNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeStoreInvalidatedAfterExactFallbackCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFrontierCacheInvalidateProposalEraseCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFrontierCacheInvalidateStoreUpdateCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFrontierCacheInvalidateReleaseOrErrorCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFrontierCacheRebuildFromResidencyCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFrontierCacheRebuildFromHostFinalCandidatesCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSafeStoreHandoffCreatedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSafeStoreHandoffAvailableForLocateCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSafeStoreHandoffHostStoreEvictedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSafeStoreHandoffHostMergeSkippedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSafeStoreHandoffHostMergeFallbackCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSafeStoreHandoffRejectedFastShadowCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSafeStoreHandoffRejectedProposalLoopCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSafeStoreHandoffRejectedMissingGpuStoreCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSafeStoreHandoffRejectedStaleEpochCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowAffectedStartCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowCoordBytesD2H()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowFallbackCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowD2hNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExecBandCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExecCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowRawCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowRawMaxWindowCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExecMaxBandCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowCoarseningInflatedCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowSparseV2ConsideredCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowSparseV2SelectedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowSparseV2RejectedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowSparseV2SavedCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowPlanBandCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowPlanCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowPlanGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowPlanD2hNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowPlanFallbackCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowPlanBetterThanBuilderCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowPlanWorseThanBuilderCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

			inline std::atomic<uint64_t> &simSafeWindowPlanEqualToBuilderCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simSafeWindowFineShadowCallCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simSafeWindowFineShadowMismatchCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simSafeWorksetBuilderCallsAfterSafeWindowCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

		enum SimSafeWindowFallbackReason
		{
		  SIM_SAFE_WINDOW_FALLBACK_SELECTOR_ERROR = 0,
		  SIM_SAFE_WINDOW_FALLBACK_OVERFLOW = 1,
		  SIM_SAFE_WINDOW_FALLBACK_EMPTY_SELECTION = 2
		};

		inline std::atomic<uint64_t> &simSafeWindowAttemptCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowSkippedUnconvertibleCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowSelectedWorksetCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowAppliedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowGpuBuilderFallbackCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowGpuBuilderPassCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExactFallbackCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExactFallbackNoUpdateRegionCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExactFallbackRefreshSuccessCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExactFallbackRefreshFailureCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExactFallbackBaseNoUpdateCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExactFallbackExpansionNoUpdateCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExactFallbackStopNoCrossCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExactFallbackStopBoundaryCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExactFallbackBaseCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExactFallbackExpansionCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowExactFallbackLocateGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowStoreInvalidationCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowFallbackSelectorErrorCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowFallbackOverflowCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSafeWindowFallbackEmptySelectionCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline void recordSimSafeWorksetPass()
		{
		  simSafeWorksetPassCount().fetch_add(1, std::memory_order_relaxed);
		}

		inline void recordSimSafeWorksetGeometry(uint64_t affectedStartCount,
		                                        const SimPathWorkset &inputWorkset,
		                                        const SimPathWorkset &execWorkset)
		{
		  simSafeWorksetAffectedStartCount().fetch_add(affectedStartCount, std::memory_order_relaxed);
		  simSafeWorksetInputBandCount().fetch_add(static_cast<uint64_t>(inputWorkset.bands.size()), std::memory_order_relaxed);
		  simSafeWorksetInputCellCount().fetch_add(inputWorkset.cellCount, std::memory_order_relaxed);
		  simSafeWorksetExecBandCount().fetch_add(static_cast<uint64_t>(execWorkset.bands.size()), std::memory_order_relaxed);
		  simSafeWorksetExecCellCount().fetch_add(execWorkset.cellCount, std::memory_order_relaxed);
		}

		inline void recordSimSafeWorksetBuild(uint64_t uniqueAffectedStartCount,
		                                     uint64_t nanoseconds)
		{
		  simSafeWorksetUniqueAffectedStartCount().fetch_add(uniqueAffectedStartCount, std::memory_order_relaxed);
		  simSafeWorksetBuildNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimSafeWorksetCudaBatch(uint64_t taskCount,uint64_t launchCount)
		{
		  simSafeWorksetCudaTaskCount().fetch_add(taskCount, std::memory_order_relaxed);
		  simSafeWorksetCudaLaunchCount().fetch_add(launchCount, std::memory_order_relaxed);
		}

		inline void recordSimSafeWorksetCudaTrueBatch(uint64_t requestCount)
		{
		  simSafeWorksetCudaTrueBatchRequestCount().fetch_add(requestCount, std::memory_order_relaxed);
		}

		inline void recordSimSafeWorksetMerge(uint64_t returnedStateCount,
		                                     uint64_t nanoseconds)
		{
		  simSafeWorksetReturnedStateCount().fetch_add(returnedStateCount, std::memory_order_relaxed);
		  simSafeWorksetMergeNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimSafeWorksetTotalNanoseconds(uint64_t nanoseconds)
		{
		  simSafeWorksetTotalNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimSafeStoreRefreshAttempt(uint64_t trackedStartCount)
		{
		  simSafeStoreRefreshAttemptCount().fetch_add(1, std::memory_order_relaxed);
		  simSafeStoreRefreshTrackedStartCount().fetch_add(trackedStartCount, std::memory_order_relaxed);
		}

		inline void recordSimSafeStoreRefreshSuccess(uint64_t gpuNanoseconds,
		                                            uint64_t d2hNanoseconds)
		{
		  simSafeStoreRefreshSuccessCount().fetch_add(1, std::memory_order_relaxed);
		  simSafeStoreRefreshGpuNanoseconds().fetch_add(gpuNanoseconds, std::memory_order_relaxed);
		  simSafeStoreRefreshD2hNanoseconds().fetch_add(d2hNanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimSafeStoreRefreshFailure()
		{
		  simSafeStoreRefreshFailureCount().fetch_add(1, std::memory_order_relaxed);
		}

		inline void recordSimSafeStoreInvalidatedAfterExactFallback()
		{
		  simSafeStoreInvalidatedAfterExactFallbackCount().fetch_add(1, std::memory_order_relaxed);
		}

		inline void recordSimFrontierCacheInvalidateProposalErase()
		{
		  simFrontierCacheInvalidateProposalEraseCount().fetch_add(1, std::memory_order_relaxed);
		}

		inline void recordSimFrontierCacheInvalidateStoreUpdate()
		{
		  simFrontierCacheInvalidateStoreUpdateCount().fetch_add(1, std::memory_order_relaxed);
		}

		inline void recordSimFrontierCacheInvalidateReleaseOrError()
		{
		  simFrontierCacheInvalidateReleaseOrErrorCount().fetch_add(1, std::memory_order_relaxed);
		}

		inline void recordSimFrontierCacheRebuildFromResidency()
		{
		  simFrontierCacheRebuildFromResidencyCount().fetch_add(1, std::memory_order_relaxed);
		}

			inline void recordSimFrontierCacheRebuildFromHostFinalCandidates()
			{
			  simFrontierCacheRebuildFromHostFinalCandidatesCount().fetch_add(1, std::memory_order_relaxed);
			}

			inline void recordSimInitialSafeStoreHandoffCreated()
			{
			  simInitialSafeStoreHandoffCreatedCount().fetch_add(1, std::memory_order_relaxed);
			}

			inline void recordSimInitialSafeStoreHandoffAvailableForLocate()
			{
			  simInitialSafeStoreHandoffAvailableForLocateCount().fetch_add(1, std::memory_order_relaxed);
			}

			inline void recordSimInitialSafeStoreHandoffHostStoreEvicted()
			{
			  simInitialSafeStoreHandoffHostStoreEvictedCount().fetch_add(1, std::memory_order_relaxed);
			}

			inline void recordSimInitialSafeStoreHandoffHostMergeSkipped()
			{
			  simInitialSafeStoreHandoffHostMergeSkippedCount().fetch_add(1, std::memory_order_relaxed);
			}

			inline void recordSimInitialSafeStoreHandoffHostMergeFallback()
			{
			  simInitialSafeStoreHandoffHostMergeFallbackCount().fetch_add(1, std::memory_order_relaxed);
			}

			inline void recordSimInitialSafeStoreHandoffRejectedFastShadow()
			{
			  simInitialSafeStoreHandoffRejectedFastShadowCount().fetch_add(1, std::memory_order_relaxed);
			}

			inline void recordSimInitialSafeStoreHandoffRejectedProposalLoop()
			{
			  simInitialSafeStoreHandoffRejectedProposalLoopCount().fetch_add(1, std::memory_order_relaxed);
			}

			inline void recordSimInitialSafeStoreHandoffRejectedMissingGpuStore()
			{
			  simInitialSafeStoreHandoffRejectedMissingGpuStoreCount().fetch_add(1, std::memory_order_relaxed);
			}

			inline void recordSimInitialSafeStoreHandoffRejectedStaleEpoch()
			{
			  simInitialSafeStoreHandoffRejectedStaleEpochCount().fetch_add(1, std::memory_order_relaxed);
			}

		inline void recordSimSafeWorksetFallbackReason(SimSafeWorksetFallbackReason reason)
		{
		  switch(reason)
		  {
		  case SIM_SAFE_WORKSET_FALLBACK_INVALID_STORE:
		    simSafeWorksetFallbackInvalidStoreCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  case SIM_SAFE_WORKSET_FALLBACK_NO_AFFECTED_START:
		    simSafeWorksetFallbackNoAffectedStartCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  case SIM_SAFE_WORKSET_FALLBACK_NO_WORKSET:
		    simSafeWorksetFallbackNoWorksetCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  case SIM_SAFE_WORKSET_FALLBACK_INVALID_BANDS:
		    simSafeWorksetFallbackInvalidBandsCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  case SIM_SAFE_WORKSET_FALLBACK_SCAN_FAILURE:
		    simSafeWorksetFallbackScanFailureCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  case SIM_SAFE_WORKSET_FALLBACK_SHADOW_MISMATCH:
		    simSafeWorksetFallbackShadowMismatchCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  }
		}

		inline void recordSimSafeWindowExecution(uint64_t windowCount,
		                                        uint64_t affectedStartCount,
		                                        uint64_t coordBytesD2H,
		                                        uint64_t gpuNanoseconds,
		                                        uint64_t d2hNanoseconds)
		{
		  simSafeWindowCount().fetch_add(windowCount,std::memory_order_relaxed);
		  simSafeWindowAffectedStartCount().fetch_add(affectedStartCount,std::memory_order_relaxed);
		  simSafeWindowCoordBytesD2H().fetch_add(coordBytesD2H,std::memory_order_relaxed);
		  simSafeWindowGpuNanoseconds().fetch_add(gpuNanoseconds,std::memory_order_relaxed);
		  simSafeWindowD2hNanoseconds().fetch_add(d2hNanoseconds,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowExecGeometry(const SimPathWorkset &execWorkset)
		{
		  simSafeWindowExecBandCount().fetch_add(static_cast<uint64_t>(execWorkset.bands.size()),
		                                       std::memory_order_relaxed);
		  simSafeWindowExecCellCount().fetch_add(execWorkset.cellCount,std::memory_order_relaxed);
		}

		inline void updateSimSafeWindowTelemetryMax(std::atomic<uint64_t> &target,uint64_t candidate)
		{
		  uint64_t current = target.load(std::memory_order_relaxed);
		  while(current < candidate &&
		        !target.compare_exchange_weak(current,
		                                      candidate,
		                                      std::memory_order_relaxed,
		                                      std::memory_order_relaxed))
		  {
		  }
		}

		inline void recordSimSafeWindowGeometryTelemetry(const SimSafeWindowExecutePlan &plan)
		{
		  simSafeWindowRawCellCount().fetch_add(plan.rawWindowCellCount,std::memory_order_relaxed);
		  updateSimSafeWindowTelemetryMax(simSafeWindowRawMaxWindowCellCount(),
		                                  plan.rawMaxWindowCellCount);
		  updateSimSafeWindowTelemetryMax(simSafeWindowExecMaxBandCellCount(),
		                                  plan.execMaxBandCellCount);
		  simSafeWindowCoarseningInflatedCellCount().fetch_add(
		    plan.coarseningInflatedCellCount,
		    std::memory_order_relaxed);
		  if(plan.sparseV2Considered)
		  {
		    simSafeWindowSparseV2ConsideredCount().fetch_add(1,std::memory_order_relaxed);
		    if(plan.sparseV2Selected)
		    {
		      simSafeWindowSparseV2SelectedCount().fetch_add(1,std::memory_order_relaxed);
		    }
		    else
		    {
		      simSafeWindowSparseV2RejectedCount().fetch_add(1,std::memory_order_relaxed);
		    }
		    simSafeWindowSparseV2SavedCellCount().fetch_add(plan.sparseV2SavedCells,
		                                                    std::memory_order_relaxed);
		  }
		}

		inline void recordSimSafeWindowPlan(const SimPathWorkset &execWorkset,
		                                   uint64_t gpuNanoseconds,
		                                   uint64_t d2hNanoseconds)
		{
		  simSafeWindowPlanBandCount().fetch_add(static_cast<uint64_t>(execWorkset.bands.size()),
		                                       std::memory_order_relaxed);
		  simSafeWindowPlanCellCount().fetch_add(execWorkset.cellCount,std::memory_order_relaxed);
		  simSafeWindowPlanGpuNanoseconds().fetch_add(gpuNanoseconds,std::memory_order_relaxed);
		  simSafeWindowPlanD2hNanoseconds().fetch_add(d2hNanoseconds,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowPlanFallback()
		{
		  simSafeWindowPlanFallbackCount().fetch_add(1,std::memory_order_relaxed);
		}

			inline void recordSimSafeWindowPlanComparison(SimSafeWindowPlanComparison comparison)
			{
			  switch(comparison)
			  {
		  case SIM_SAFE_WINDOW_PLAN_COMPARISON_BETTER:
		    simSafeWindowPlanBetterThanBuilderCount().fetch_add(1,std::memory_order_relaxed);
		    break;
		  case SIM_SAFE_WINDOW_PLAN_COMPARISON_WORSE:
		    simSafeWindowPlanWorseThanBuilderCount().fetch_add(1,std::memory_order_relaxed);
		    break;
		  case SIM_SAFE_WINDOW_PLAN_COMPARISON_EQUAL:
		    simSafeWindowPlanEqualToBuilderCount().fetch_add(1,std::memory_order_relaxed);
		    break;
		  case SIM_SAFE_WINDOW_PLAN_COMPARISON_INVALID:
		    break;
			  }
			}

			inline void recordSimSafeWindowFineShadow(bool mismatch)
			{
			  simSafeWindowFineShadowCallCount().fetch_add(1,std::memory_order_relaxed);
			  if(mismatch)
			  {
			    simSafeWindowFineShadowMismatchCount().fetch_add(1,std::memory_order_relaxed);
			  }
			}

			inline void recordSimSafeWorksetBuilderCallAfterSafeWindow()
			{
			  simSafeWorksetBuilderCallsAfterSafeWindowCount().fetch_add(1,std::memory_order_relaxed);
			}

		inline void recordSimSafeWindowAttempt()
		{
		  simSafeWindowAttemptCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowSkippedUnconvertible()
		{
		  simSafeWindowSkippedUnconvertibleCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowSelectedWorkset()
		{
		  simSafeWindowSelectedWorksetCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowApplied()
		{
		  simSafeWindowAppliedCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowGpuBuilderFallback()
		{
		  simSafeWindowGpuBuilderFallbackCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowGpuBuilderPass()
		{
		  simSafeWindowGpuBuilderPassCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowExactFallback()
		{
		  simSafeWindowExactFallbackCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowExactFallbackNoUpdateRegion()
		{
		  simSafeWindowExactFallbackNoUpdateRegionCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowExactFallbackRefreshSuccess()
		{
		  simSafeWindowExactFallbackRefreshSuccessCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowExactFallbackRefreshFailure()
		{
		  simSafeWindowExactFallbackRefreshFailureCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowExactFallbackBaseNoUpdate()
		{
		  simSafeWindowExactFallbackBaseNoUpdateCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowExactFallbackExpansionNoUpdate()
		{
		  simSafeWindowExactFallbackExpansionNoUpdateCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowExactFallbackStopNoCross()
		{
		  simSafeWindowExactFallbackStopNoCrossCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowExactFallbackStopBoundary()
		{
		  simSafeWindowExactFallbackStopBoundaryCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowExactFallbackBaseCells(uint64_t cellCount)
		{
		  simSafeWindowExactFallbackBaseCellCount().fetch_add(cellCount,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowExactFallbackExpansionCells(uint64_t cellCount)
		{
		  simSafeWindowExactFallbackExpansionCellCount().fetch_add(cellCount,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowExactFallbackLocateGpuNanoseconds(uint64_t nanoseconds)
		{
		  simSafeWindowExactFallbackLocateGpuNanoseconds().fetch_add(nanoseconds,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowStoreInvalidation()
		{
		  simSafeWindowStoreInvalidationCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowFallback()
		{
		  simSafeWindowFallbackCount().fetch_add(1,std::memory_order_relaxed);
		}

		inline void recordSimSafeWindowFallbackReason(SimSafeWindowFallbackReason reason)
		{
		  recordSimSafeWindowFallback();
		  switch(reason)
		  {
		  case SIM_SAFE_WINDOW_FALLBACK_SELECTOR_ERROR:
		    simSafeWindowFallbackSelectorErrorCount().fetch_add(1,std::memory_order_relaxed);
		    break;
		  case SIM_SAFE_WINDOW_FALLBACK_OVERFLOW:
		    simSafeWindowFallbackOverflowCount().fetch_add(1,std::memory_order_relaxed);
		    break;
		  case SIM_SAFE_WINDOW_FALLBACK_EMPTY_SELECTION:
		    simSafeWindowFallbackEmptySelectionCount().fetch_add(1,std::memory_order_relaxed);
		    break;
		  }
		}

		inline void getSimSafeWorksetStats(uint64_t &passCount,
		                                  uint64_t &fallbackInvalidStoreCount,
		                                  uint64_t &fallbackNoAffectedStartCount,
		                                  uint64_t &fallbackNoWorksetCount,
		                                  uint64_t &fallbackInvalidBandsCount,
		                                  uint64_t &fallbackScanFailureCount,
		                                  uint64_t &fallbackShadowMismatchCount)
		{
		  passCount = simSafeWorksetPassCount().load(std::memory_order_relaxed);
		  fallbackInvalidStoreCount = simSafeWorksetFallbackInvalidStoreCount().load(std::memory_order_relaxed);
		  fallbackNoAffectedStartCount = simSafeWorksetFallbackNoAffectedStartCount().load(std::memory_order_relaxed);
		  fallbackNoWorksetCount = simSafeWorksetFallbackNoWorksetCount().load(std::memory_order_relaxed);
		  fallbackInvalidBandsCount = simSafeWorksetFallbackInvalidBandsCount().load(std::memory_order_relaxed);
		  fallbackScanFailureCount = simSafeWorksetFallbackScanFailureCount().load(std::memory_order_relaxed);
		  fallbackShadowMismatchCount = simSafeWorksetFallbackShadowMismatchCount().load(std::memory_order_relaxed);
		}

		inline void getSimSafeWorksetExecutionStats(uint64_t &affectedStartCount,
		                                           uint64_t &uniqueAffectedStartCount,
		                                           uint64_t &inputBandCount,
		                                           uint64_t &inputCellCount,
		                                           uint64_t &execBandCount,
		                                           uint64_t &execCellCount,
		                                           uint64_t &cudaTaskCount,
		                                           uint64_t &cudaLaunchCount,
		                                           uint64_t &returnedStateCount)
		{
		  affectedStartCount = simSafeWorksetAffectedStartCount().load(std::memory_order_relaxed);
		  uniqueAffectedStartCount = simSafeWorksetUniqueAffectedStartCount().load(std::memory_order_relaxed);
		  inputBandCount = simSafeWorksetInputBandCount().load(std::memory_order_relaxed);
		  inputCellCount = simSafeWorksetInputCellCount().load(std::memory_order_relaxed);
		  execBandCount = simSafeWorksetExecBandCount().load(std::memory_order_relaxed);
		  execCellCount = simSafeWorksetExecCellCount().load(std::memory_order_relaxed);
		  cudaTaskCount = simSafeWorksetCudaTaskCount().load(std::memory_order_relaxed);
		  cudaLaunchCount = simSafeWorksetCudaLaunchCount().load(std::memory_order_relaxed);
		  returnedStateCount = simSafeWorksetReturnedStateCount().load(std::memory_order_relaxed);
		}

		inline uint64_t getSimSafeWorksetCudaTrueBatchRequestCount()
		{
		  return simSafeWorksetCudaTrueBatchRequestCount().load(std::memory_order_relaxed);
		}

		inline void getSimSafeWorksetTimingStats(uint64_t &buildNanoseconds,
		                                        uint64_t &mergeNanoseconds,
		                                        uint64_t &totalNanoseconds)
		{
		  buildNanoseconds = simSafeWorksetBuildNanoseconds().load(std::memory_order_relaxed);
		  mergeNanoseconds = simSafeWorksetMergeNanoseconds().load(std::memory_order_relaxed);
		  totalNanoseconds = simSafeWorksetTotalNanoseconds().load(std::memory_order_relaxed);
		}

		inline void getSimSafeStoreRefreshStats(uint64_t &attemptCount,
		                                       uint64_t &successCount,
		                                       uint64_t &failureCount,
		                                       uint64_t &trackedStartCount,
		                                       uint64_t &gpuNanoseconds,
		                                       uint64_t &d2hNanoseconds,
		                                       uint64_t &invalidatedAfterExactFallbackCount)
		{
		  attemptCount = simSafeStoreRefreshAttemptCount().load(std::memory_order_relaxed);
		  successCount = simSafeStoreRefreshSuccessCount().load(std::memory_order_relaxed);
		  failureCount = simSafeStoreRefreshFailureCount().load(std::memory_order_relaxed);
		  trackedStartCount = simSafeStoreRefreshTrackedStartCount().load(std::memory_order_relaxed);
		  gpuNanoseconds = simSafeStoreRefreshGpuNanoseconds().load(std::memory_order_relaxed);
		  d2hNanoseconds = simSafeStoreRefreshD2hNanoseconds().load(std::memory_order_relaxed);
		  invalidatedAfterExactFallbackCount =
		    simSafeStoreInvalidatedAfterExactFallbackCount().load(std::memory_order_relaxed);
		}

			inline void getSimFrontierCacheTransitionStats(uint64_t &invalidateProposalEraseCount,
			                                              uint64_t &invalidateStoreUpdateCount,
			                                              uint64_t &invalidateReleaseOrErrorCount,
			                                              uint64_t &rebuildFromResidencyCount,
		                                              uint64_t &rebuildFromHostFinalCandidatesCount)
		{
		  invalidateProposalEraseCount =
		    simFrontierCacheInvalidateProposalEraseCount().load(std::memory_order_relaxed);
		  invalidateStoreUpdateCount =
		    simFrontierCacheInvalidateStoreUpdateCount().load(std::memory_order_relaxed);
		  invalidateReleaseOrErrorCount =
		    simFrontierCacheInvalidateReleaseOrErrorCount().load(std::memory_order_relaxed);
		  rebuildFromResidencyCount =
		    simFrontierCacheRebuildFromResidencyCount().load(std::memory_order_relaxed);
			  rebuildFromHostFinalCandidatesCount =
			    simFrontierCacheRebuildFromHostFinalCandidatesCount().load(std::memory_order_relaxed);
			}

			inline void getSimInitialSafeStoreHandoffCompositionStats(uint64_t &createdCount,
			                                                         uint64_t &availableForLocateCount,
			                                                         uint64_t &hostStoreEvictedCount,
			                                                         uint64_t &hostMergeSkippedCount,
			                                                         uint64_t &hostMergeFallbackCount,
			                                                         uint64_t &rejectedFastShadowCount,
			                                                         uint64_t &rejectedProposalLoopCount,
			                                                         uint64_t &rejectedMissingGpuStoreCount,
			                                                         uint64_t &rejectedStaleEpochCount)
			{
			  createdCount =
			    simInitialSafeStoreHandoffCreatedCount().load(std::memory_order_relaxed);
			  availableForLocateCount =
			    simInitialSafeStoreHandoffAvailableForLocateCount().load(std::memory_order_relaxed);
			  hostStoreEvictedCount =
			    simInitialSafeStoreHandoffHostStoreEvictedCount().load(std::memory_order_relaxed);
			  hostMergeSkippedCount =
			    simInitialSafeStoreHandoffHostMergeSkippedCount().load(std::memory_order_relaxed);
			  hostMergeFallbackCount =
			    simInitialSafeStoreHandoffHostMergeFallbackCount().load(std::memory_order_relaxed);
			  rejectedFastShadowCount =
			    simInitialSafeStoreHandoffRejectedFastShadowCount().load(std::memory_order_relaxed);
			  rejectedProposalLoopCount =
			    simInitialSafeStoreHandoffRejectedProposalLoopCount().load(std::memory_order_relaxed);
			  rejectedMissingGpuStoreCount =
			    simInitialSafeStoreHandoffRejectedMissingGpuStoreCount().load(std::memory_order_relaxed);
			  rejectedStaleEpochCount =
			    simInitialSafeStoreHandoffRejectedStaleEpochCount().load(std::memory_order_relaxed);
			}

			inline void getSimSafeWindowStats(uint64_t &windowCount,
		                                 uint64_t &affectedStartCount,
		                                 uint64_t &coordBytesD2H,
		                                 uint64_t &fallbackCount,
		                                 uint64_t &gpuNanoseconds,
		                                 uint64_t &d2hNanoseconds)
		{
		  windowCount = simSafeWindowCount().load(std::memory_order_relaxed);
		  affectedStartCount = simSafeWindowAffectedStartCount().load(std::memory_order_relaxed);
		  coordBytesD2H = simSafeWindowCoordBytesD2H().load(std::memory_order_relaxed);
		  fallbackCount = simSafeWindowFallbackCount().load(std::memory_order_relaxed);
		  gpuNanoseconds = simSafeWindowGpuNanoseconds().load(std::memory_order_relaxed);
		  d2hNanoseconds = simSafeWindowD2hNanoseconds().load(std::memory_order_relaxed);
		}

		inline void getSimSafeWindowExecutionStats(uint64_t &execBandCount,
		                                          uint64_t &execCellCount)
		{
		  execBandCount = simSafeWindowExecBandCount().load(std::memory_order_relaxed);
		  execCellCount = simSafeWindowExecCellCount().load(std::memory_order_relaxed);
		}

		inline void getSimSafeWindowGeometryTelemetryStats(uint64_t &rawCellCount,
		                                                  uint64_t &rawMaxWindowCellCount,
		                                                  uint64_t &execMaxBandCellCount,
		                                                  uint64_t &coarseningInflatedCellCount,
		                                                  uint64_t &sparseV2ConsideredCount,
		                                                  uint64_t &sparseV2SelectedCount,
		                                                  uint64_t &sparseV2RejectedCount,
		                                                  uint64_t &sparseV2SavedCellCount)
		{
		  rawCellCount = simSafeWindowRawCellCount().load(std::memory_order_relaxed);
		  rawMaxWindowCellCount = simSafeWindowRawMaxWindowCellCount().load(std::memory_order_relaxed);
		  execMaxBandCellCount = simSafeWindowExecMaxBandCellCount().load(std::memory_order_relaxed);
		  coarseningInflatedCellCount =
		    simSafeWindowCoarseningInflatedCellCount().load(std::memory_order_relaxed);
		  sparseV2ConsideredCount =
		    simSafeWindowSparseV2ConsideredCount().load(std::memory_order_relaxed);
		  sparseV2SelectedCount =
		    simSafeWindowSparseV2SelectedCount().load(std::memory_order_relaxed);
		  sparseV2RejectedCount =
		    simSafeWindowSparseV2RejectedCount().load(std::memory_order_relaxed);
		  sparseV2SavedCellCount =
		    simSafeWindowSparseV2SavedCellCount().load(std::memory_order_relaxed);
		}

		inline void getSimSafeWindowPlanStats(uint64_t &bandCount,
		                                     uint64_t &cellCount,
		                                     uint64_t &gpuNanoseconds,
		                                     uint64_t &d2hNanoseconds,
		                                     uint64_t &fallbackCount)
		{
		  bandCount = simSafeWindowPlanBandCount().load(std::memory_order_relaxed);
		  cellCount = simSafeWindowPlanCellCount().load(std::memory_order_relaxed);
		  gpuNanoseconds = simSafeWindowPlanGpuNanoseconds().load(std::memory_order_relaxed);
		  d2hNanoseconds = simSafeWindowPlanD2hNanoseconds().load(std::memory_order_relaxed);
		  fallbackCount = simSafeWindowPlanFallbackCount().load(std::memory_order_relaxed);
		}

			inline void getSimSafeWindowPlanComparisonStats(uint64_t &betterCount,
			                                               uint64_t &worseCount,
			                                               uint64_t &equalCount)
			{
			  betterCount = simSafeWindowPlanBetterThanBuilderCount().load(std::memory_order_relaxed);
			  worseCount = simSafeWindowPlanWorseThanBuilderCount().load(std::memory_order_relaxed);
			  equalCount = simSafeWindowPlanEqualToBuilderCount().load(std::memory_order_relaxed);
			}

			inline void getSimSafeWindowFineShadowStats(uint64_t &callCount,
			                                           uint64_t &mismatchCount)
			{
			  callCount = simSafeWindowFineShadowCallCount().load(std::memory_order_relaxed);
			  mismatchCount = simSafeWindowFineShadowMismatchCount().load(std::memory_order_relaxed);
			}

			inline uint64_t getSimSafeWorksetBuilderCallsAfterSafeWindow()
			{
			  return simSafeWorksetBuilderCallsAfterSafeWindowCount().load(std::memory_order_relaxed);
			}

		inline void getSimSafeWindowPathStats(uint64_t &attemptCount,
		                                     uint64_t &skippedUnconvertibleCount,
		                                     uint64_t &selectedWorksetCount,
		                                     uint64_t &appliedCount,
		                                     uint64_t &gpuBuilderFallbackCount,
		                                     uint64_t &gpuBuilderPassCount,
		                                     uint64_t &exactFallbackCount,
		                                     uint64_t &storeInvalidationCount)
		{
		  attemptCount = simSafeWindowAttemptCount().load(std::memory_order_relaxed);
		  skippedUnconvertibleCount = simSafeWindowSkippedUnconvertibleCount().load(std::memory_order_relaxed);
		  selectedWorksetCount = simSafeWindowSelectedWorksetCount().load(std::memory_order_relaxed);
		  appliedCount = simSafeWindowAppliedCount().load(std::memory_order_relaxed);
		  gpuBuilderFallbackCount = simSafeWindowGpuBuilderFallbackCount().load(std::memory_order_relaxed);
		  gpuBuilderPassCount = simSafeWindowGpuBuilderPassCount().load(std::memory_order_relaxed);
		  exactFallbackCount = simSafeWindowExactFallbackCount().load(std::memory_order_relaxed);
		  storeInvalidationCount = simSafeWindowStoreInvalidationCount().load(std::memory_order_relaxed);
		}

		inline void getSimSafeWindowExactFallbackOutcomeStats(uint64_t &noUpdateRegionCount,
		                                                     uint64_t &refreshSuccessCount,
		                                                     uint64_t &refreshFailureCount)
		{
		  noUpdateRegionCount =
		    simSafeWindowExactFallbackNoUpdateRegionCount().load(std::memory_order_relaxed);
		  refreshSuccessCount =
		    simSafeWindowExactFallbackRefreshSuccessCount().load(std::memory_order_relaxed);
		  refreshFailureCount =
		    simSafeWindowExactFallbackRefreshFailureCount().load(std::memory_order_relaxed);
		}

		inline void getSimSafeWindowExactFallbackPrecheckStats(uint64_t &baseNoUpdateCount,
		                                                      uint64_t &expansionNoUpdateCount,
		                                                      uint64_t &stopNoCrossCount,
		                                                      uint64_t &stopBoundaryCount,
		                                                      uint64_t &baseCellCount,
		                                                      uint64_t &expansionCellCount,
		                                                      uint64_t &locateGpuNanoseconds)
		{
		  baseNoUpdateCount =
		    simSafeWindowExactFallbackBaseNoUpdateCount().load(std::memory_order_relaxed);
		  expansionNoUpdateCount =
		    simSafeWindowExactFallbackExpansionNoUpdateCount().load(std::memory_order_relaxed);
		  stopNoCrossCount =
		    simSafeWindowExactFallbackStopNoCrossCount().load(std::memory_order_relaxed);
		  stopBoundaryCount =
		    simSafeWindowExactFallbackStopBoundaryCount().load(std::memory_order_relaxed);
		  baseCellCount =
		    simSafeWindowExactFallbackBaseCellCount().load(std::memory_order_relaxed);
		  expansionCellCount =
		    simSafeWindowExactFallbackExpansionCellCount().load(std::memory_order_relaxed);
		  locateGpuNanoseconds =
		    simSafeWindowExactFallbackLocateGpuNanoseconds().load(std::memory_order_relaxed);
		}

		inline void getSimSafeWindowFallbackReasonStats(uint64_t &selectorErrorCount,
		                                               uint64_t &overflowCount,
		                                               uint64_t &emptySelectionCount)
		{
		  selectorErrorCount = simSafeWindowFallbackSelectorErrorCount().load(std::memory_order_relaxed);
		  overflowCount = simSafeWindowFallbackOverflowCount().load(std::memory_order_relaxed);
		  emptySelectionCount = simSafeWindowFallbackEmptySelectionCount().load(std::memory_order_relaxed);
		}

		enum SimFastFallbackReason
		{
		  SIM_FAST_FALLBACK_NO_WORKSET = 0,
		  SIM_FAST_FALLBACK_AREA_CAP = 1,
		  SIM_FAST_FALLBACK_SHADOW_RUNNING_MIN = 2,
		  SIM_FAST_FALLBACK_SHADOW_CANDIDATE_COUNT = 3,
		  SIM_FAST_FALLBACK_SHADOW_CANDIDATE_VALUE = 4
		};

		inline std::atomic<uint64_t> &simFastWorksetBandCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFastWorksetCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFastSegmentCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFastDiagonalSegmentCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFastHorizontalSegmentCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFastVerticalSegmentCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFastFallbackNoWorksetCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFastFallbackAreaCapCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFastFallbackShadowRunningMinCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFastFallbackShadowCandidateCountCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simFastFallbackShadowCandidateValueCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline void recordSimFastPathSummary(const SimTracebackPathSummary &summary)
		{
		  simFastSegmentCount().fetch_add(static_cast<uint64_t>(summary.segments.size()), std::memory_order_relaxed);
		  for(size_t index = 0; index < summary.segments.size(); ++index)
		  {
		    switch(summary.segments[index].kind)
		    {
		    case SIM_TRACEBACK_SEGMENT_DIAGONAL:
		      simFastDiagonalSegmentCount().fetch_add(1, std::memory_order_relaxed);
		      break;
		    case SIM_TRACEBACK_SEGMENT_HORIZONTAL:
		      simFastHorizontalSegmentCount().fetch_add(1, std::memory_order_relaxed);
		      break;
		    case SIM_TRACEBACK_SEGMENT_VERTICAL:
		      simFastVerticalSegmentCount().fetch_add(1, std::memory_order_relaxed);
		      break;
		    }
		  }
		}

		inline void recordSimFastWorkset(const SimPathWorkset &workset)
		{
		  simFastWorksetBandCount().fetch_add(static_cast<uint64_t>(workset.bands.size()), std::memory_order_relaxed);
		  simFastWorksetCellCount().fetch_add(workset.cellCount, std::memory_order_relaxed);
		}

		inline void recordSimFastFallbackReason(SimFastFallbackReason reason)
		{
		  switch(reason)
		  {
		  case SIM_FAST_FALLBACK_NO_WORKSET:
		    simFastFallbackNoWorksetCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  case SIM_FAST_FALLBACK_AREA_CAP:
		    simFastFallbackAreaCapCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  case SIM_FAST_FALLBACK_SHADOW_RUNNING_MIN:
		    simFastFallbackShadowRunningMinCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  case SIM_FAST_FALLBACK_SHADOW_CANDIDATE_COUNT:
		    simFastFallbackShadowCandidateCountCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  case SIM_FAST_FALLBACK_SHADOW_CANDIDATE_VALUE:
		    simFastFallbackShadowCandidateValueCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  }
		}

		inline void getSimFastPathStats(uint64_t &worksetBandCount,
		                               uint64_t &worksetCellCount,
		                               uint64_t &segmentCount,
		                               uint64_t &diagonalSegmentCount,
		                               uint64_t &horizontalSegmentCount,
		                               uint64_t &verticalSegmentCount,
		                               uint64_t &fallbackNoWorksetCount,
		                               uint64_t &fallbackAreaCapCount,
		                               uint64_t &fallbackShadowRunningMinCount,
		                               uint64_t &fallbackShadowCandidateCountCount,
		                               uint64_t &fallbackShadowCandidateValueCount)
		{
		  worksetBandCount = simFastWorksetBandCount().load(std::memory_order_relaxed);
		  worksetCellCount = simFastWorksetCellCount().load(std::memory_order_relaxed);
		  segmentCount = simFastSegmentCount().load(std::memory_order_relaxed);
		  diagonalSegmentCount = simFastDiagonalSegmentCount().load(std::memory_order_relaxed);
		  horizontalSegmentCount = simFastHorizontalSegmentCount().load(std::memory_order_relaxed);
		  verticalSegmentCount = simFastVerticalSegmentCount().load(std::memory_order_relaxed);
		  fallbackNoWorksetCount = simFastFallbackNoWorksetCount().load(std::memory_order_relaxed);
		  fallbackAreaCapCount = simFastFallbackAreaCapCount().load(std::memory_order_relaxed);
		  fallbackShadowRunningMinCount = simFastFallbackShadowRunningMinCount().load(std::memory_order_relaxed);
		  fallbackShadowCandidateCountCount = simFastFallbackShadowCandidateCountCount().load(std::memory_order_relaxed);
		  fallbackShadowCandidateValueCount = simFastFallbackShadowCandidateValueCount().load(std::memory_order_relaxed);
		}

		inline std::atomic<uint64_t> &simTracebackCpuCallCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simSolverCpuCallCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

			inline std::atomic<uint64_t> &simSolverCudaFullExactCallCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simSolverCudaWindowPipelineCallCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			enum SimSolverBackend
			{
			  SIM_SOLVER_BACKEND_CPU = 0,
			  SIM_SOLVER_BACKEND_CUDA_FULL_EXACT = 1,
			  SIM_SOLVER_BACKEND_CUDA_WINDOW_PIPELINE = 2
			};

			inline void recordSimSolverBackend(SimSolverBackend backend)
			{
			  if(backend == SIM_SOLVER_BACKEND_CUDA_FULL_EXACT)
			  {
			    simSolverCudaFullExactCallCount().fetch_add(1, std::memory_order_relaxed);
			  }
			  else if(backend == SIM_SOLVER_BACKEND_CUDA_WINDOW_PIPELINE)
			  {
			    simSolverCudaWindowPipelineCallCount().fetch_add(1, std::memory_order_relaxed);
			  }
			  else
			  {
			    simSolverCpuCallCount().fetch_add(1, std::memory_order_relaxed);
			  }
			}

			inline void getSimSolverBackendCounts(uint64_t &cpuCalls,
			                                     uint64_t &cudaFullExactCalls,
			                                     uint64_t &cudaWindowPipelineCalls)
			{
			  cpuCalls = simSolverCpuCallCount().load(std::memory_order_relaxed);
			  cudaFullExactCalls = simSolverCudaFullExactCallCount().load(std::memory_order_relaxed);
			  cudaWindowPipelineCalls = simSolverCudaWindowPipelineCallCount().load(std::memory_order_relaxed);
			}

		inline std::atomic<uint64_t> &simCudaFullExactIterationCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simCudaFullExactRescanCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simCudaFullExactBlockedDiagonalCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline void recordSimCudaFullExactExecution(uint64_t iterationCount,
		                                            uint64_t rescanCount,
		                                            uint64_t blockedDiagonalCount,
		                                            uint64_t taskCount,
		                                            uint64_t launchCount)
		{
		  recordSimScanBatch(taskCount,launchCount);
		  simCudaFullExactIterationCount().fetch_add(iterationCount, std::memory_order_relaxed);
		  simCudaFullExactRescanCount().fetch_add(rescanCount, std::memory_order_relaxed);
		  simCudaFullExactBlockedDiagonalCount().fetch_add(blockedDiagonalCount, std::memory_order_relaxed);
		}

		inline void getSimCudaFullExactStats(uint64_t &iterationCount,
		                                     uint64_t &rescanCount,
		                                     uint64_t &blockedDiagonalCount)
		{
		  iterationCount = simCudaFullExactIterationCount().load(std::memory_order_relaxed);
		  rescanCount = simCudaFullExactRescanCount().load(std::memory_order_relaxed);
		  blockedDiagonalCount = simCudaFullExactBlockedDiagonalCount().load(std::memory_order_relaxed);
		}

		inline std::atomic<uint64_t> &simBlockedPackWordCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simBlockedMirrorBytesMax()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionTotalCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simTracebackTotalCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionEventCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionCandidateSummaryCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionEventBytesD2HCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSummaryBytesD2HCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionPackedRequestCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionBucketedTrueBatchBatchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionBucketedTrueBatchRequestCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionBucketedTrueBatchFusedRequestCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionBucketedTrueBatchActualCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionBucketedTrueBatchPaddedCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionBucketedTrueBatchPaddingCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionBucketedTrueBatchRejectedPaddingCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionBucketedTrueBatchShadowMismatchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceAttemptCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceSuccessCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFallbackCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceOverflowCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceShadowMismatchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceHashCapacityMax()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCandidateCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceEventCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceRunSummaryCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceDpGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFilterReduceGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCompactGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCountD2HNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCandidateCountD2HNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceDeferredCountSnapshotD2HNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFusedDpGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFusedOracleDpGpuNanosecondsShadow()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFusedTotalGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceAffectedStartCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceWorkItemCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFusedDpAttemptCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFusedDpEligibleCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFusedDpSuccessCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFusedDpFallbackCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFusedDpShadowMismatchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFusedDpRejectedByCellsCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFusedDpRejectedByDiagLenCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFusedDpCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFusedDpRequestCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceFusedDpDiagLaunchesReplacedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopOracleDpGpuNanosecondsShadow()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopTotalGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpSupportedFlag()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpAttemptCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpEligibleCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpSuccessCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpFallbackCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpShadowMismatchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpRejectedByUnsupportedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpRejectedByCellsCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpRejectedByDiagLenCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpRejectedByResidencyCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpRequestCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReduceCoopDpDiagLaunchesReplacedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineRequestCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineRowCountTotal()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineRowCountMax()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineColCountTotal()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineColCountMax()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineCellCountTotal()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineCellCountMax()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineDiagCountTotal()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineDiagCountMax()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineFilterStartCountTotal()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineFilterStartCountMax()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineDiagLaunchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineEventCountLaunchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineEventPrefixLaunchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineRunCountLaunchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineRunPrefixLaunchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineRunCompactLaunchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineFilterReduceLaunchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineCandidatePrefixLaunchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineCandidateCompactLaunchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineCountSnapshotLaunchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineDpLt1msCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineDp1To5msCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineDp5To10msCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineDp10To50msCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineDpGte50msCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineDpMaxNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineMetadataH2DNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineDiagGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineEventCountGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineEventCountD2HNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineEventPrefixGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineRunCountGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineRunCountD2HNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineRunPrefixGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineRunCompactGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineCandidatePrefixGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineCandidateCompactGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineCountSnapshotD2HNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineAccountedGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionSingleRequestDirectReducePipelineUnaccountedGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionCpuMergeNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simLocateTotalCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialEventCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialRunSummaryCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

			inline std::atomic<uint64_t> &simInitialSummaryBytesD2HCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialSummaryPackedD2HEnabledCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialSummaryPackedBytesD2HCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialSummaryUnpackedEquivalentBytesD2HCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialSummaryPackNanoseconds()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

				inline std::atomic<uint64_t> &simInitialSummaryPackedD2HFallbackCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialSummaryHostCopyElisionEnabledCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialSummaryD2HCopyNanoseconds()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialSummaryUnpackNanoseconds()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialSummaryResultMaterializeNanoseconds()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

					inline std::atomic<uint64_t> &simInitialSummaryHostCopyElidedByteCount()
					{
					  static std::atomic<uint64_t> count(0);
					  return count;
					}

					inline std::atomic<uint64_t> &simInitialSummaryHostCopyElisionCountCopyReuseCount()
					{
					  static std::atomic<uint64_t> count(0);
					  return count;
					}

					inline std::atomic<uint64_t> &simInitialCpuFrontierFastApplyEnabledCount()
					{
					  static std::atomic<uint64_t> count(0);
					  return count;
					}

					inline std::atomic<uint64_t> &simInitialCpuFrontierFastApplyAttemptCount()
					{
					  static std::atomic<uint64_t> count(0);
					  return count;
					}

					inline std::atomic<uint64_t> &simInitialCpuFrontierFastApplySuccessCount()
					{
					  static std::atomic<uint64_t> count(0);
					  return count;
					}

					inline std::atomic<uint64_t> &simInitialCpuFrontierFastApplyFallbackCount()
					{
					  static std::atomic<uint64_t> count(0);
					  return count;
					}

					inline std::atomic<uint64_t> &simInitialCpuFrontierFastApplyShadowMismatchCount()
					{
					  static std::atomic<uint64_t> count(0);
					  return count;
					}

					inline std::atomic<uint64_t> &simInitialCpuFrontierFastApplySummaryReplayCount()
					{
					  static std::atomic<uint64_t> count(0);
					  return count;
					}

					inline std::atomic<uint64_t> &simInitialCpuFrontierFastApplyCandidateOutCount()
					{
					  static std::atomic<uint64_t> count(0);
					  return count;
					}

					inline std::atomic<uint64_t> &simInitialCpuFrontierFastApplyNanoseconds()
					{
					  static std::atomic<uint64_t> count(0);
					  return count;
					}

					inline std::atomic<uint64_t> &simInitialCpuFrontierFastApplyOracleNanosecondsShadow()
					{
					  static std::atomic<uint64_t> count(0);
					  return count;
					}

					inline std::atomic<uint64_t> &simInitialCpuFrontierFastApplyRejectedByStatsCount()
					{
					  static std::atomic<uint64_t> count(0);
					  return count;
					}

					inline std::atomic<uint64_t> &simInitialCpuFrontierFastApplyRejectedByNonemptyContextCount()
					{
					  static std::atomic<uint64_t> count(0);
					  return count;
					}

					inline std::atomic<uint64_t> &simInitialReducedCandidateCount()
					{
					  static std::atomic<uint64_t> count(0);
			  return count;
			}

		inline std::atomic<uint64_t> &simInitialAllCandidateStateCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialStoreBytesD2HCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialStoreBytesH2DCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialStoreUploadNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSafeStoreDeviceBuildNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSafeStoreDevicePruneNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSafeStoreFrontierBytesH2DCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

			inline std::atomic<uint64_t> &simInitialSafeStoreFrontierUploadNanoseconds()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialFrontierTransducerShadowCallCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialFrontierTransducerShadowNanoseconds()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialFrontierTransducerShadowDigestD2HBytes()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialFrontierTransducerShadowSummaryReplayCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialFrontierTransducerShadowMismatchCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialOrderedSegmentedV3ShadowCallCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialOrderedSegmentedV3ShadowFrontierMismatchCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialOrderedSegmentedV3ShadowRunningMinMismatchCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialOrderedSegmentedV3ShadowSafeStoreMismatchCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialOrderedSegmentedV3ShadowCandidateCountMismatchCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialOrderedSegmentedV3ShadowCandidateValueMismatchCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simProposalAllCandidateStateCount()
			{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialProposalV2BatchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialProposalV2RequestCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialProposalV3BatchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialProposalV3RequestCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialProposalV3SelectedCandidateStateCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialProposalV3GpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialProposalDirectTopKBatchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialProposalDirectTopKLogicalCandidateStateCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialProposalDirectTopKMaterializedCandidateStateCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialProposalDirectTopKGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalBytesD2HCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalSelectedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalMaterializedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalSelectedBoxCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalMaterializedQueryBaseCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalMaterializedTargetBaseCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalTracebackBatchRequestCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalTracebackBatchCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalTracebackBatchSuccessCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalTracebackBatchFallbackCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalTracebackBatchTieFallbackCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalTracebackCudaEligibleCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalTracebackCudaSizeFilteredCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalTracebackCudaBatchFailedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalTracebackCpuDirectCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalPostScoreRejectCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalPostNtRejectCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalTracebackCpuCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalTracebackCudaCellCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		enum SimProposalLoopFallbackReason
		{
		  SIM_PROPOSAL_LOOP_FALLBACK_NO_STORE = 0,
		  SIM_PROPOSAL_LOOP_FALLBACK_SELECTOR_FAILURE = 1,
		  SIM_PROPOSAL_LOOP_FALLBACK_EMPTY_SELECTION = 2
		};

		inline std::atomic<uint64_t> &simProposalLoopAttemptCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalLoopShortCircuitCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalLoopInitialSourceCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalLoopSafeStoreSourceCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalLoopGpuSafeStoreSourceCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalLoopGpuFrontierCacheSourceCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalLoopGpuSafeStoreFullSourceCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalLoopFallbackNoStoreCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalLoopFallbackSelectorFailureCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalLoopFallbackEmptySelectionCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simLocateDeviceKLoopAttemptCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simLocateDeviceKLoopShortCircuitCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalMaterializeCpuBackendCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalMaterializeCudaBatchBackendCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalMaterializeHybridBackendCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialReduceChunkCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialReduceChunkReplayedCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

			inline std::atomic<uint64_t> &simInitialReduceSummaryReplayCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialContextApplyChunkSkipChunkCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialContextApplyChunkSkipChunkReplayedCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialContextApplyChunkSkipChunkSkippedCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialContextApplyChunkSkipSummaryReplayedCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialContextApplyChunkSkipSummarySkippedCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialChunkedHandoffEnabledCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialChunkedHandoffChunkCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialChunkedHandoffSummaryReplayCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialChunkedHandoffRingSlotCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialChunkedHandoffPinnedAllocationFailureCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialChunkedHandoffPageableFallbackCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialChunkedHandoffSyncCopyCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialChunkedHandoffCpuWaitNanoseconds()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialChunkedHandoffCriticalPathD2HNanoseconds()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialChunkedHandoffMeasuredOverlapNanoseconds()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialChunkedHandoffFallbackCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

				inline std::atomic<uint64_t> &simInitialChunkedHandoffFallbackReasonCode()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffChunkCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffRequestedCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffActiveCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffDisabledReasonCode()
				{
				  static std::atomic<uint64_t> count(
				    static_cast<uint64_t>(
				      SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_NOT_REQUESTED));
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffSourceReadyModeCode()
				{
				  static std::atomic<uint64_t> count(
				    static_cast<uint64_t>(
				      SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_SOURCE_READY_NONE));
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncCpuPipelineRequestedCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncCpuPipelineActiveCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncCpuPipelineDisabledReasonCode()
				{
				  static std::atomic<uint64_t> count(
				    static_cast<uint64_t>(
				      SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_NOT_REQUESTED));
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncCpuPipelineChunksApplied()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncCpuPipelineSummariesApplied()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncCpuPipelineChunksFinalized()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncCpuPipelineFinalizeCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncCpuPipelineOutOfOrderChunks()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffPinnedSlotCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffPinnedBytes()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffPinnedAllocationFailureCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffPageableFallbackCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffSyncCopyCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffAsyncCopyCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffSlotReuseWaitCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffSlotsReusedAfterMaterializeCount()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffAsyncD2HNanoseconds()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffD2HWaitNanoseconds()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffCpuApplyNanoseconds()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffCpuD2HOverlapNanoseconds()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffDpD2HOverlapNanoseconds()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialPinnedAsyncHandoffCriticalPathNanoseconds()
				{
				  static std::atomic<uint64_t> count(0);
				  return count;
				}

				inline std::atomic<uint64_t> &simInitialExactFrontierReplayRequestCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialExactFrontierReplayFrontierStateCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialExactFrontierReplayDeviceSafeStoreCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simInitialScanNanoseconds()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

		inline std::atomic<uint64_t> &simInitialScanGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialScanD2HNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialScanCpuMergeNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialScanCpuContextApplyNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialScanCpuSafeStoreUpdateNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialScanCpuSafeStorePruneNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialScanDiagNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialScanOnlineReduceNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialScanWaitNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialScanCountCopyNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialScanBaseUploadNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialProposalSelectD2HNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialScanSyncWaitNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialScanTailNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialHashReduceNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSegmentedReduceNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSegmentedCompactNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialTopKNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSegmentedTileStateCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simInitialSegmentedGroupedStateCount()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalTracebackBatchGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simProposalPostNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simDeviceKLoopNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simLocateNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simLocateGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionScanGpuNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simRegionD2HNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simMaterializeNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simTracebackDpNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline std::atomic<uint64_t> &simTracebackPostNanoseconds()
		{
		  static std::atomic<uint64_t> count(0);
		  return count;
		}

		inline uint64_t simElapsedNanoseconds(const std::chrono::steady_clock::time_point &start)
		{
		  return static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
		                                 std::chrono::steady_clock::now() - start).count());
		}

		inline uint64_t simSecondsToNanoseconds(double seconds)
		{
		  if(seconds <= 0.0)
		  {
		    return 0;
		  }
		  return static_cast<uint64_t>(seconds * 1.0e9 + 0.5);
		}

		inline void updateSimTelemetryMax(std::atomic<uint64_t> &target,uint64_t candidate)
		{
		  uint64_t current = target.load(std::memory_order_relaxed);
		  while(current < candidate &&
		        !target.compare_exchange_weak(current,
		                                      candidate,
		                                      std::memory_order_relaxed,
		                                      std::memory_order_relaxed))
		  {
		  }
		}

		inline void recordSimBlockedPackWords(uint64_t packedWords)
		{
		  simBlockedPackWordCount().fetch_add(packedWords, std::memory_order_relaxed);
		}

		inline void recordSimBlockedMirrorBytes(uint64_t mirrorBytes)
		{
		  updateSimTelemetryMax(simBlockedMirrorBytesMax(),mirrorBytes);
		}

		inline void recordSimRegionTotalCells(uint64_t cellCount)
		{
		  simRegionTotalCellCount().fetch_add(cellCount, std::memory_order_relaxed);
		}

		inline void recordSimTracebackTotalCells(uint64_t cellCount)
		{
		  simTracebackTotalCellCount().fetch_add(cellCount, std::memory_order_relaxed);
		}

		inline void recordSimRegionEvents(uint64_t eventCount)
		{
		  simRegionEventCount().fetch_add(eventCount, std::memory_order_relaxed);
		}

		inline void recordSimRegionCandidateSummaries(uint64_t summaryCount)
		{
		  simRegionCandidateSummaryCount().fetch_add(summaryCount, std::memory_order_relaxed);
		}

		inline void recordSimRegionEventBytesD2H(uint64_t byteCount)
		{
		  simRegionEventBytesD2HCount().fetch_add(byteCount, std::memory_order_relaxed);
		}

		inline void recordSimRegionSummaryBytesD2H(uint64_t byteCount)
		{
		  simRegionSummaryBytesD2HCount().fetch_add(byteCount, std::memory_order_relaxed);
		}

		inline void recordSimRegionPackedRequests(uint64_t requestCount)
		{
		  simRegionPackedRequestCount().fetch_add(requestCount, std::memory_order_relaxed);
		}

		inline void recordSimRegionBucketedTrueBatch(const SimScanCudaBatchResult &batchResult)
		{
		  simRegionBucketedTrueBatchBatchCount().fetch_add(batchResult.regionBucketedTrueBatchBatches,
		                                                   std::memory_order_relaxed);
		  simRegionBucketedTrueBatchRequestCount().fetch_add(batchResult.regionBucketedTrueBatchRequests,
		                                                     std::memory_order_relaxed);
		  simRegionBucketedTrueBatchFusedRequestCount().fetch_add(batchResult.regionBucketedTrueBatchFusedRequests,
		                                                          std::memory_order_relaxed);
		  simRegionBucketedTrueBatchActualCellCount().fetch_add(batchResult.regionBucketedTrueBatchActualCells,
		                                                        std::memory_order_relaxed);
		  simRegionBucketedTrueBatchPaddedCellCount().fetch_add(batchResult.regionBucketedTrueBatchPaddedCells,
		                                                        std::memory_order_relaxed);
		  simRegionBucketedTrueBatchPaddingCellCount().fetch_add(batchResult.regionBucketedTrueBatchPaddingCells,
		                                                         std::memory_order_relaxed);
		  simRegionBucketedTrueBatchRejectedPaddingCount().fetch_add(batchResult.regionBucketedTrueBatchRejectedPadding,
		                                                             std::memory_order_relaxed);
		  simRegionBucketedTrueBatchShadowMismatchCount().fetch_add(batchResult.regionBucketedTrueBatchShadowMismatches,
		                                                            std::memory_order_relaxed);
		}

		inline void recordSimRegionSingleRequestDirectReduce(const SimScanCudaBatchResult &batchResult)
		{
		  simRegionSingleRequestDirectReduceAttemptCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceAttempts,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceSuccessCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceSuccesses,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFallbackCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceFallbacks,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceOverflowCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceOverflows,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceShadowMismatchCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceShadowMismatches,
		    std::memory_order_relaxed);
		  updateSimTelemetryMax(simRegionSingleRequestDirectReduceHashCapacityMax(),
		                        batchResult.regionSingleRequestDirectReduceHashCapacity);
		  simRegionSingleRequestDirectReduceCandidateCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceCandidateCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceEventCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceEventCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceRunSummaryCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceRunSummaryCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReduceGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceDpGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReduceDpGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFilterReduceGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReduceFilterReduceGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCompactGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReduceCompactGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCountD2HNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReduceCountD2HSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCandidateCountD2HNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReduceCandidateCountD2HSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceDeferredCountSnapshotD2HNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReduceDeferredCountSnapshotD2HSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFusedDpGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReduceFusedDpGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFusedOracleDpGpuNanosecondsShadow().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReduceFusedOracleDpGpuSecondsShadow),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFusedTotalGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReduceFusedTotalGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceAffectedStartCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceAffectedStartCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceWorkItemCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceReduceWorkItems,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFusedDpAttemptCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceFusedDpAttempts,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFusedDpEligibleCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceFusedDpEligible,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFusedDpSuccessCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceFusedDpSuccesses,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFusedDpFallbackCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceFusedDpFallbacks,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFusedDpShadowMismatchCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceFusedDpShadowMismatches,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFusedDpRejectedByCellsCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceFusedDpRejectedByCells,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFusedDpRejectedByDiagLenCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceFusedDpRejectedByDiagLen,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFusedDpCellCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceFusedDpCells,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFusedDpRequestCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceFusedDpRequests,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceFusedDpDiagLaunchesReplacedCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceFusedDpDiagLaunchesReplaced,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopDpGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReduceCoopDpGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopOracleDpGpuNanosecondsShadow().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReduceCoopOracleDpGpuSecondsShadow),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopTotalGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReduceCoopTotalGpuSeconds),
		    std::memory_order_relaxed);
		  updateSimTelemetryMax(simRegionSingleRequestDirectReduceCoopDpSupportedFlag(),
		                        batchResult.regionSingleRequestDirectReduceCoopDpSupported);
		  simRegionSingleRequestDirectReduceCoopDpAttemptCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceCoopDpAttempts,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopDpEligibleCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceCoopDpEligible,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopDpSuccessCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceCoopDpSuccesses,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopDpFallbackCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceCoopDpFallbacks,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopDpShadowMismatchCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceCoopDpShadowMismatches,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopDpRejectedByUnsupportedCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceCoopDpRejectedByUnsupported,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopDpRejectedByCellsCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceCoopDpRejectedByCells,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopDpRejectedByDiagLenCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceCoopDpRejectedByDiagLen,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopDpRejectedByResidencyCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceCoopDpRejectedByResidency,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopDpCellCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceCoopDpCells,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopDpRequestCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceCoopDpRequests,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReduceCoopDpDiagLaunchesReplacedCount().fetch_add(
		    batchResult.regionSingleRequestDirectReduceCoopDpDiagLaunchesReplaced,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineRequestCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineRequestCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineRowCountTotal().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineRowCountTotal,
		    std::memory_order_relaxed);
		  updateSimTelemetryMax(simRegionSingleRequestDirectReducePipelineRowCountMax(),
		                        batchResult.regionSingleRequestDirectReducePipelineRowCountMax);
		  simRegionSingleRequestDirectReducePipelineColCountTotal().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineColCountTotal,
		    std::memory_order_relaxed);
		  updateSimTelemetryMax(simRegionSingleRequestDirectReducePipelineColCountMax(),
		                        batchResult.regionSingleRequestDirectReducePipelineColCountMax);
		  simRegionSingleRequestDirectReducePipelineCellCountTotal().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineCellCountTotal,
		    std::memory_order_relaxed);
		  updateSimTelemetryMax(simRegionSingleRequestDirectReducePipelineCellCountMax(),
		                        batchResult.regionSingleRequestDirectReducePipelineCellCountMax);
		  simRegionSingleRequestDirectReducePipelineDiagCountTotal().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineDiagCountTotal,
		    std::memory_order_relaxed);
		  updateSimTelemetryMax(simRegionSingleRequestDirectReducePipelineDiagCountMax(),
		                        batchResult.regionSingleRequestDirectReducePipelineDiagCountMax);
		  simRegionSingleRequestDirectReducePipelineFilterStartCountTotal().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineFilterStartCountTotal,
		    std::memory_order_relaxed);
		  updateSimTelemetryMax(simRegionSingleRequestDirectReducePipelineFilterStartCountMax(),
		                        batchResult.regionSingleRequestDirectReducePipelineFilterStartCountMax);
		  simRegionSingleRequestDirectReducePipelineDiagLaunchCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineDiagLaunchCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineEventCountLaunchCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineEventCountLaunchCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineEventPrefixLaunchCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineEventPrefixLaunchCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineRunCountLaunchCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineRunCountLaunchCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineRunPrefixLaunchCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineRunPrefixLaunchCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineRunCompactLaunchCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineRunCompactLaunchCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineFilterReduceLaunchCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineFilterReduceLaunchCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineCandidatePrefixLaunchCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineCandidatePrefixLaunchCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineCandidateCompactLaunchCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineCandidateCompactLaunchCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineCountSnapshotLaunchCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineCountSnapshotLaunchCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineDpLt1msCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineDpLt1msCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineDp1To5msCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineDp1To5msCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineDp5To10msCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineDp5To10msCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineDp10To50msCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineDp10To50msCount,
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineDpGte50msCount().fetch_add(
		    batchResult.regionSingleRequestDirectReducePipelineDpGte50msCount,
		    std::memory_order_relaxed);
		  updateSimTelemetryMax(simRegionSingleRequestDirectReducePipelineDpMaxNanoseconds(),
		                        batchResult.regionSingleRequestDirectReducePipelineDpMaxNanoseconds);
		  simRegionSingleRequestDirectReducePipelineMetadataH2DNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineMetadataH2DSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineDiagGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineDiagGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineEventCountGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineEventCountGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineEventCountD2HNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineEventCountD2HSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineEventPrefixGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineEventPrefixGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineRunCountGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineRunCountGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineRunCountD2HNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineRunCountD2HSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineRunPrefixGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineRunPrefixGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineRunCompactGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineRunCompactGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineCandidatePrefixGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineCandidatePrefixGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineCandidateCompactGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineCandidateCompactGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineCountSnapshotD2HNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineCountSnapshotD2HSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineAccountedGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineAccountedGpuSeconds),
		    std::memory_order_relaxed);
		  simRegionSingleRequestDirectReducePipelineUnaccountedGpuNanoseconds().fetch_add(
		    simSecondsToNanoseconds(batchResult.regionSingleRequestDirectReducePipelineUnaccountedGpuSeconds),
		    std::memory_order_relaxed);
		}

		inline void recordSimRegionCpuMergeNanoseconds(uint64_t nanoseconds)
		{
		  simRegionCpuMergeNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimLocateTotalCells(uint64_t cellCount)
		{
		  simLocateTotalCellCount().fetch_add(cellCount, std::memory_order_relaxed);
		}

		inline void recordSimInitialEvents(uint64_t eventCount)
		{
		  simInitialEventCount().fetch_add(eventCount, std::memory_order_relaxed);
		}

		inline void recordSimInitialRunSummaries(uint64_t summaryCount)
		{
		  simInitialRunSummaryCount().fetch_add(summaryCount, std::memory_order_relaxed);
		}

			inline void recordSimInitialSummaryBytesD2H(uint64_t byteCount)
			{
			  simInitialSummaryBytesD2HCount().fetch_add(byteCount, std::memory_order_relaxed);
			}

			inline void recordSimInitialSummaryPackedD2H(bool usedPackedD2H,
			                                            uint64_t packedBytesD2H,
			                                            uint64_t unpackedEquivalentBytesD2H,
			                                            uint64_t packNanoseconds,
			                                            uint64_t fallbackCount)
			{
			  if(usedPackedD2H)
			  {
			    simInitialSummaryPackedD2HEnabledCount().fetch_add(1, std::memory_order_relaxed);
			  }
			  simInitialSummaryPackedBytesD2HCount().fetch_add(packedBytesD2H, std::memory_order_relaxed);
			  simInitialSummaryUnpackedEquivalentBytesD2HCount().fetch_add(unpackedEquivalentBytesD2H,
			                                                               std::memory_order_relaxed);
				  simInitialSummaryPackNanoseconds().fetch_add(packNanoseconds, std::memory_order_relaxed);
				  simInitialSummaryPackedD2HFallbackCount().fetch_add(fallbackCount, std::memory_order_relaxed);
				}

					inline void recordSimInitialSummaryHostCopyElision(bool usedHostCopyElision,
					                                                  uint64_t d2hCopyNanoseconds,
					                                                  uint64_t unpackNanoseconds,
					                                                  uint64_t resultMaterializeNanoseconds,
				                                                  uint64_t elidedBytes,
				                                                  uint64_t countCopyReuses)
				{
				  if(usedHostCopyElision)
				  {
				    simInitialSummaryHostCopyElisionEnabledCount().fetch_add(1, std::memory_order_relaxed);
				  }
				  simInitialSummaryD2HCopyNanoseconds().fetch_add(d2hCopyNanoseconds, std::memory_order_relaxed);
				  simInitialSummaryUnpackNanoseconds().fetch_add(unpackNanoseconds, std::memory_order_relaxed);
				  simInitialSummaryResultMaterializeNanoseconds().fetch_add(resultMaterializeNanoseconds,
				                                                            std::memory_order_relaxed);
					  simInitialSummaryHostCopyElidedByteCount().fetch_add(elidedBytes, std::memory_order_relaxed);
					  simInitialSummaryHostCopyElisionCountCopyReuseCount().fetch_add(countCopyReuses,
					                                                                  std::memory_order_relaxed);
					}

					inline void recordSimInitialCpuFrontierFastApplyEnabled()
					{
					  simInitialCpuFrontierFastApplyEnabledCount().fetch_add(1, std::memory_order_relaxed);
					}

					inline void recordSimInitialCpuFrontierFastApplyAttempt()
					{
					  simInitialCpuFrontierFastApplyAttemptCount().fetch_add(1, std::memory_order_relaxed);
					}

					inline void recordSimInitialCpuFrontierFastApplySuccess()
					{
					  simInitialCpuFrontierFastApplySuccessCount().fetch_add(1, std::memory_order_relaxed);
					}

					inline void recordSimInitialCpuFrontierFastApplyFallback()
					{
					  simInitialCpuFrontierFastApplyFallbackCount().fetch_add(1, std::memory_order_relaxed);
					}

					inline void recordSimInitialCpuFrontierFastApplyShadowMismatch()
					{
					  simInitialCpuFrontierFastApplyShadowMismatchCount().fetch_add(1, std::memory_order_relaxed);
					}

					inline void recordSimInitialCpuFrontierFastApplyRejectedByStats()
					{
					  simInitialCpuFrontierFastApplyRejectedByStatsCount().fetch_add(1, std::memory_order_relaxed);
					}

					inline void recordSimInitialCpuFrontierFastApplyRejectedByNonemptyContext()
					{
					  simInitialCpuFrontierFastApplyRejectedByNonemptyContextCount().fetch_add(1,
					                                                                           std::memory_order_relaxed);
					}

					inline void recordSimInitialCpuFrontierFastApplyReplayStats(
					  const SimInitialCpuFrontierFastApplyStats &stats,
					  uint64_t fastApplyNanoseconds)
					{
					  simInitialCpuFrontierFastApplySummaryReplayCount().fetch_add(stats.summariesReplayed,
					                                                               std::memory_order_relaxed);
					  simInitialCpuFrontierFastApplyCandidateOutCount().fetch_add(stats.candidatesOut,
					                                                              std::memory_order_relaxed);
					  simInitialCpuFrontierFastApplyNanoseconds().fetch_add(fastApplyNanoseconds,
					                                                        std::memory_order_relaxed);
					}

					inline void recordSimInitialCpuFrontierFastApplyOracleShadowNanoseconds(uint64_t nanoseconds)
					{
					  simInitialCpuFrontierFastApplyOracleNanosecondsShadow().fetch_add(nanoseconds,
					                                                                    std::memory_order_relaxed);
					}

					inline void recordSimInitialReducedCandidates(uint64_t candidateCount)
					{
					  simInitialReducedCandidateCount().fetch_add(candidateCount, std::memory_order_relaxed);
			}

		inline void recordSimInitialAllCandidateStates(uint64_t candidateCount)
		{
		  simInitialAllCandidateStateCount().fetch_add(candidateCount, std::memory_order_relaxed);
		}

		inline void recordSimInitialStoreBytesD2H(uint64_t byteCount)
		{
		  simInitialStoreBytesD2HCount().fetch_add(byteCount, std::memory_order_relaxed);
		}

		inline void recordSimInitialStoreBytesH2D(uint64_t byteCount)
		{
		  simInitialStoreBytesH2DCount().fetch_add(byteCount, std::memory_order_relaxed);
		}

		inline void recordSimInitialStoreUploadNanoseconds(uint64_t nanoseconds)
		{
		  simInitialStoreUploadNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialSafeStoreDeviceBuildNanoseconds(uint64_t nanoseconds)
		{
		  simInitialSafeStoreDeviceBuildNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialSafeStoreDevicePruneNanoseconds(uint64_t nanoseconds)
		{
		  simInitialSafeStoreDevicePruneNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialSafeStoreFrontierBytesH2D(uint64_t byteCount)
		{
		  simInitialSafeStoreFrontierBytesH2DCount().fetch_add(byteCount, std::memory_order_relaxed);
		}

		inline void recordSimInitialSafeStoreFrontierUploadNanoseconds(uint64_t nanoseconds)
		{
		  simInitialSafeStoreFrontierUploadNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialFrontierTransducerShadow(uint64_t nanoseconds,
		                                                     uint64_t digestD2HBytes,
		                                                     uint64_t summaryReplayCount,
		                                                     uint64_t mismatchCount)
		{
		  simInitialFrontierTransducerShadowCallCount().fetch_add(1, std::memory_order_relaxed);
		  simInitialFrontierTransducerShadowNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		  simInitialFrontierTransducerShadowDigestD2HBytes().fetch_add(digestD2HBytes, std::memory_order_relaxed);
		  simInitialFrontierTransducerShadowSummaryReplayCount().fetch_add(summaryReplayCount, std::memory_order_relaxed);
		  simInitialFrontierTransducerShadowMismatchCount().fetch_add(mismatchCount, std::memory_order_relaxed);
		}

		inline void recordSimInitialOrderedSegmentedV3Shadow(uint64_t frontierMismatch,
		                                                     uint64_t runningMinMismatch,
		                                                     uint64_t safeStoreMismatch,
		                                                     uint64_t candidateCountMismatch,
		                                                     uint64_t candidateValueMismatch)
		{
		  simInitialOrderedSegmentedV3ShadowCallCount().fetch_add(1, std::memory_order_relaxed);
		  simInitialOrderedSegmentedV3ShadowFrontierMismatchCount().fetch_add(frontierMismatch, std::memory_order_relaxed);
		  simInitialOrderedSegmentedV3ShadowRunningMinMismatchCount().fetch_add(runningMinMismatch, std::memory_order_relaxed);
		  simInitialOrderedSegmentedV3ShadowSafeStoreMismatchCount().fetch_add(safeStoreMismatch, std::memory_order_relaxed);
		  simInitialOrderedSegmentedV3ShadowCandidateCountMismatchCount().fetch_add(candidateCountMismatch, std::memory_order_relaxed);
		  simInitialOrderedSegmentedV3ShadowCandidateValueMismatchCount().fetch_add(candidateValueMismatch, std::memory_order_relaxed);
		}

		inline void recordSimProposalAllCandidateStates(uint64_t candidateCount)
		{
		  simProposalAllCandidateStateCount().fetch_add(candidateCount, std::memory_order_relaxed);
		}

		inline void recordSimInitialProposalV2(uint64_t batchCount,uint64_t requestCount)
		{
		  simInitialProposalV2BatchCount().fetch_add(batchCount, std::memory_order_relaxed);
		  simInitialProposalV2RequestCount().fetch_add(requestCount, std::memory_order_relaxed);
		}

		inline void recordSimInitialProposalV3(uint64_t batchCount,
		                                       uint64_t requestCount,
		                                       uint64_t selectedStateCount,
		                                       uint64_t gpuNanoseconds)
		{
		  simInitialProposalV3BatchCount().fetch_add(batchCount, std::memory_order_relaxed);
		  simInitialProposalV3RequestCount().fetch_add(requestCount, std::memory_order_relaxed);
		  simInitialProposalV3SelectedCandidateStateCount().fetch_add(selectedStateCount, std::memory_order_relaxed);
		  simInitialProposalV3GpuNanoseconds().fetch_add(gpuNanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialProposalDirectTopK(uint64_t batchCount,
		                                               uint64_t logicalCandidateCount,
		                                               uint64_t materializedCandidateCount,
		                                               uint64_t gpuNanoseconds)
		{
		  simInitialProposalDirectTopKBatchCount().fetch_add(batchCount, std::memory_order_relaxed);
		  simInitialProposalDirectTopKLogicalCandidateStateCount().fetch_add(logicalCandidateCount, std::memory_order_relaxed);
		  simInitialProposalDirectTopKMaterializedCandidateStateCount().fetch_add(materializedCandidateCount,
		                                                                          std::memory_order_relaxed);
		  simInitialProposalDirectTopKGpuNanoseconds().fetch_add(gpuNanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimProposalBytesD2H(uint64_t byteCount)
		{
		  simProposalBytesD2HCount().fetch_add(byteCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalSelected(uint64_t candidateCount)
		{
		  simProposalSelectedCount().fetch_add(candidateCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalMaterialized(uint64_t candidateCount = 1)
		{
		  simProposalMaterializedCount().fetch_add(candidateCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalSelectedBoxCells(uint64_t cellCount)
		{
		  simProposalSelectedBoxCellCount().fetch_add(cellCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalMaterializedQueryBases(uint64_t baseCount)
		{
		  simProposalMaterializedQueryBaseCount().fetch_add(baseCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalMaterializedTargetBases(uint64_t baseCount)
		{
		  simProposalMaterializedTargetBaseCount().fetch_add(baseCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalTracebackBatchRequests(uint64_t requestCount)
		{
		  simProposalTracebackBatchRequestCount().fetch_add(requestCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalTracebackBatchBatches(uint64_t batchCount = 1)
		{
		  simProposalTracebackBatchCount().fetch_add(batchCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalTracebackBatchSuccess(uint64_t successCount = 1)
		{
		  simProposalTracebackBatchSuccessCount().fetch_add(successCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalTracebackBatchFallbacks(uint64_t fallbackCount = 1)
		{
		  simProposalTracebackBatchFallbackCount().fetch_add(fallbackCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalTracebackBatchTieFallbacks(uint64_t fallbackCount = 1)
		{
		  simProposalTracebackBatchTieFallbackCount().fetch_add(fallbackCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalTracebackCudaEligible(uint64_t candidateCount = 1)
		{
		  simProposalTracebackCudaEligibleCount().fetch_add(candidateCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalTracebackCudaSizeFiltered(uint64_t candidateCount = 1)
		{
		  simProposalTracebackCudaSizeFilteredCount().fetch_add(candidateCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalTracebackCudaBatchFailed(uint64_t candidateCount = 1)
		{
		  simProposalTracebackCudaBatchFailedCount().fetch_add(candidateCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalTracebackCpuDirect(uint64_t candidateCount = 1)
		{
		  simProposalTracebackCpuDirectCount().fetch_add(candidateCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalPostScoreRejects(uint64_t candidateCount = 1)
		{
		  simProposalPostScoreRejectCount().fetch_add(candidateCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalPostNtRejects(uint64_t candidateCount = 1)
		{
		  simProposalPostNtRejectCount().fetch_add(candidateCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalTracebackCpuCells(uint64_t cellCount)
		{
		  simProposalTracebackCpuCellCount().fetch_add(cellCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalTracebackCudaCells(uint64_t cellCount)
		{
		  simProposalTracebackCudaCellCount().fetch_add(cellCount, std::memory_order_relaxed);
		}

		inline void recordSimProposalLoopAttempt(uint64_t count = 1)
		{
		  simProposalLoopAttemptCount().fetch_add(count, std::memory_order_relaxed);
		}

		inline void recordSimProposalLoopShortCircuit(uint64_t count = 1)
		{
		  simProposalLoopShortCircuitCount().fetch_add(count, std::memory_order_relaxed);
		}

		inline void recordSimProposalLoopSourceFromInitial(uint64_t count = 1)
		{
		  simProposalLoopInitialSourceCount().fetch_add(count, std::memory_order_relaxed);
		}

		inline void recordSimProposalLoopSourceFromSafeStore(uint64_t count = 1)
		{
		  simProposalLoopSafeStoreSourceCount().fetch_add(count, std::memory_order_relaxed);
		}

		inline void recordSimProposalLoopSourceFromGpuSafeStore(uint64_t count = 1)
		{
		  simProposalLoopGpuSafeStoreSourceCount().fetch_add(count, std::memory_order_relaxed);
		}

		inline void recordSimProposalLoopSourceFromGpuFrontierCache(uint64_t count = 1)
		{
		  simProposalLoopGpuFrontierCacheSourceCount().fetch_add(count, std::memory_order_relaxed);
		}

		inline void recordSimProposalLoopSourceFromGpuSafeStoreFull(uint64_t count = 1)
		{
		  simProposalLoopGpuSafeStoreFullSourceCount().fetch_add(count, std::memory_order_relaxed);
		}

		inline void recordSimProposalLoopFallbackReason(SimProposalLoopFallbackReason reason)
		{
		  switch(reason)
		  {
		  case SIM_PROPOSAL_LOOP_FALLBACK_NO_STORE:
		    simProposalLoopFallbackNoStoreCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  case SIM_PROPOSAL_LOOP_FALLBACK_SELECTOR_FAILURE:
		    simProposalLoopFallbackSelectorFailureCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  case SIM_PROPOSAL_LOOP_FALLBACK_EMPTY_SELECTION:
		    simProposalLoopFallbackEmptySelectionCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  }
		}

		inline void recordSimLocateDeviceKLoopAttempt(uint64_t count = 1)
		{
		  simLocateDeviceKLoopAttemptCount().fetch_add(count, std::memory_order_relaxed);
		}

		inline void recordSimLocateDeviceKLoopShortCircuit(uint64_t count = 1)
		{
		  simLocateDeviceKLoopShortCircuitCount().fetch_add(count, std::memory_order_relaxed);
		}

		inline void recordSimProposalMaterializeBackendCall(SimProposalMaterializeBackend backend)
		{
		  switch(backend)
		  {
		  case SIM_PROPOSAL_MATERIALIZE_BACKEND_CPU:
		    simProposalMaterializeCpuBackendCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  case SIM_PROPOSAL_MATERIALIZE_BACKEND_CUDA_BATCH_TRACEBACK:
		    simProposalMaterializeCudaBatchBackendCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  case SIM_PROPOSAL_MATERIALIZE_BACKEND_HYBRID:
		    simProposalMaterializeHybridBackendCount().fetch_add(1, std::memory_order_relaxed);
		    break;
		  }
		}

		inline void recordSimDeviceKLoopNanoseconds(uint64_t nanoseconds)
		{
		  simDeviceKLoopNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

			inline void recordSimInitialReduceReplayStats(const SimScanCudaInitialReduceReplayStats &stats)
			{
			  simInitialReduceChunkCount().fetch_add(stats.chunkCount, std::memory_order_relaxed);
			  simInitialReduceChunkReplayedCount().fetch_add(stats.chunkReplayedCount, std::memory_order_relaxed);
			  simInitialReduceSummaryReplayCount().fetch_add(stats.summaryReplayCount, std::memory_order_relaxed);
			}

			inline void recordSimInitialContextApplyChunkSkipStats(const SimInitialContextApplyChunkSkipStats &stats)
			{
			  simInitialContextApplyChunkSkipChunkCount().fetch_add(stats.chunkCount, std::memory_order_relaxed);
			  simInitialContextApplyChunkSkipChunkReplayedCount().fetch_add(stats.chunkReplayedCount,
			                                                                std::memory_order_relaxed);
			  simInitialContextApplyChunkSkipChunkSkippedCount().fetch_add(stats.chunkSkippedCount,
			                                                               std::memory_order_relaxed);
			  simInitialContextApplyChunkSkipSummaryReplayedCount().fetch_add(stats.summaryReplayedCount,
			                                                                  std::memory_order_relaxed);
			  simInitialContextApplyChunkSkipSummarySkippedCount().fetch_add(stats.summarySkippedCount,
			                                                                 std::memory_order_relaxed);
			}

			inline void recordSimInitialChunkedHandoffStats(const SimInitialChunkedHandoffStats &stats)
			{
			  simInitialChunkedHandoffEnabledCount().fetch_add(1, std::memory_order_relaxed);
			  simInitialChunkedHandoffChunkCount().fetch_add(stats.chunkCount, std::memory_order_relaxed);
			  simInitialChunkedHandoffSummaryReplayCount().fetch_add(stats.summariesReplayed,
			                                                         std::memory_order_relaxed);
			  simInitialChunkedHandoffRingSlotCount().fetch_add(stats.ringSlots, std::memory_order_relaxed);
			  simInitialChunkedHandoffPinnedAllocationFailureCount().fetch_add(
			    stats.pinnedAllocationFailures,
			    std::memory_order_relaxed);
			  simInitialChunkedHandoffPageableFallbackCount().fetch_add(stats.pageableFallbacks,
			                                                            std::memory_order_relaxed);
			  simInitialChunkedHandoffSyncCopyCount().fetch_add(stats.syncCopies,
			                                                    std::memory_order_relaxed);
			  simInitialChunkedHandoffCpuWaitNanoseconds().fetch_add(stats.cpuWaitNanoseconds,
			                                                         std::memory_order_relaxed);
			  simInitialChunkedHandoffCriticalPathD2HNanoseconds().fetch_add(
			    stats.criticalPathD2HNanoseconds,
			    std::memory_order_relaxed);
			  simInitialChunkedHandoffMeasuredOverlapNanoseconds().fetch_add(
			    stats.measuredOverlapNanoseconds,
			    std::memory_order_relaxed);
			  simInitialChunkedHandoffFallbackCount().fetch_add(stats.fallbackCount,
			                                                    std::memory_order_relaxed);
			  if(stats.fallbackReason != SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_NONE)
			  {
			    simInitialChunkedHandoffFallbackReasonCode().store(
			      static_cast<uint64_t>(stats.fallbackReason),
			      std::memory_order_relaxed);
			  }
			}

				inline void recordSimInitialChunkedHandoffTransferNanoseconds(
				  uint64_t criticalPathD2HNanoseconds,
				  uint64_t cpuWaitNanoseconds,
				  uint64_t measuredOverlapNanoseconds)
			{
			  simInitialChunkedHandoffCriticalPathD2HNanoseconds().fetch_add(
			    criticalPathD2HNanoseconds,
			    std::memory_order_relaxed);
			  simInitialChunkedHandoffCpuWaitNanoseconds().fetch_add(cpuWaitNanoseconds,
			                                                         std::memory_order_relaxed);
			  simInitialChunkedHandoffMeasuredOverlapNanoseconds().fetch_add(
				    measuredOverlapNanoseconds,
				    std::memory_order_relaxed);
				}

				inline void recordSimInitialPinnedAsyncHandoffStats(
				  const SimScanCudaBatchResult &batchResult)
				{
				  if(batchResult.initialHandoffPinnedAsyncRequested)
				  {
				    simInitialPinnedAsyncHandoffRequestedCount().fetch_add(1,
				                                                          std::memory_order_relaxed);
				  }
				  if(batchResult.initialHandoffPinnedAsyncActive)
				  {
				    simInitialPinnedAsyncHandoffActiveCount().fetch_add(1,
				                                                       std::memory_order_relaxed);
				  }
				  else if(batchResult.initialHandoffPinnedAsyncDisabledReason !=
				          SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_NOT_REQUESTED)
				  {
				    simInitialPinnedAsyncHandoffDisabledReasonCode().store(
				      static_cast<uint64_t>(batchResult.initialHandoffPinnedAsyncDisabledReason),
				      std::memory_order_relaxed);
				  }
				  if(batchResult.initialHandoffPinnedAsyncSourceReadyMode !=
				     SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_SOURCE_READY_NONE)
				  {
				    simInitialPinnedAsyncHandoffSourceReadyModeCode().store(
				      static_cast<uint64_t>(batchResult.initialHandoffPinnedAsyncSourceReadyMode),
				      std::memory_order_relaxed);
				  }
				  if(batchResult.initialHandoffCpuPipelineRequested)
				  {
				    simInitialPinnedAsyncCpuPipelineRequestedCount().fetch_add(
				      1,
				      std::memory_order_relaxed);
				  }
				  if(batchResult.initialHandoffCpuPipelineActive)
				  {
				    simInitialPinnedAsyncCpuPipelineActiveCount().fetch_add(
				      1,
				      std::memory_order_relaxed);
				  }
				  else if(batchResult.initialHandoffCpuPipelineDisabledReason !=
				          SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_NOT_REQUESTED)
				  {
				    simInitialPinnedAsyncCpuPipelineDisabledReasonCode().store(
				      static_cast<uint64_t>(
				        batchResult.initialHandoffCpuPipelineDisabledReason),
				      std::memory_order_relaxed);
				  }
				  simInitialPinnedAsyncCpuPipelineChunksApplied().fetch_add(
				    batchResult.initialHandoffCpuPipelineChunksApplied,
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncCpuPipelineSummariesApplied().fetch_add(
				    batchResult.initialHandoffCpuPipelineSummariesApplied,
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncCpuPipelineChunksFinalized().fetch_add(
				    batchResult.initialHandoffCpuPipelineChunksFinalized,
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncCpuPipelineFinalizeCount().fetch_add(
				    batchResult.initialHandoffCpuPipelineFinalizeCount,
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncCpuPipelineOutOfOrderChunks().fetch_add(
				    batchResult.initialHandoffCpuPipelineOutOfOrderChunks,
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncHandoffChunkCount().fetch_add(
				    batchResult.initialHandoffChunksTotal,
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncHandoffPinnedSlotCount().fetch_add(
				    batchResult.initialHandoffPinnedSlots,
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncHandoffPinnedBytes().fetch_add(
				    batchResult.initialHandoffPinnedBytes,
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncHandoffPinnedAllocationFailureCount().fetch_add(
				    batchResult.initialHandoffPinnedAllocationFailures,
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncHandoffPageableFallbackCount().fetch_add(
				    batchResult.initialHandoffPageableFallbacks,
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncHandoffSyncCopyCount().fetch_add(
				    batchResult.initialHandoffSyncCopies,
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncHandoffAsyncCopyCount().fetch_add(
				    batchResult.initialHandoffAsyncCopies,
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncHandoffSlotReuseWaitCount().fetch_add(
				    batchResult.initialHandoffSlotReuseWaits,
				    std::memory_order_relaxed);
				  if(batchResult.initialHandoffSlotsReusedAfterMaterialize)
				  {
				    simInitialPinnedAsyncHandoffSlotsReusedAfterMaterializeCount().fetch_add(
				      1,
				      std::memory_order_relaxed);
				  }
				  simInitialPinnedAsyncHandoffAsyncD2HNanoseconds().fetch_add(
				    simSecondsToNanoseconds(batchResult.initialHandoffAsyncD2HSeconds),
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncHandoffD2HWaitNanoseconds().fetch_add(
				    simSecondsToNanoseconds(batchResult.initialHandoffD2HWaitSeconds),
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncHandoffCpuApplyNanoseconds().fetch_add(
				    simSecondsToNanoseconds(batchResult.initialHandoffCpuApplySeconds),
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncHandoffCpuD2HOverlapNanoseconds().fetch_add(
				    simSecondsToNanoseconds(batchResult.initialHandoffCpuD2HOverlapSeconds),
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncHandoffDpD2HOverlapNanoseconds().fetch_add(
				    simSecondsToNanoseconds(batchResult.initialHandoffDpD2HOverlapSeconds),
				    std::memory_order_relaxed);
				  simInitialPinnedAsyncHandoffCriticalPathNanoseconds().fetch_add(
				    simSecondsToNanoseconds(batchResult.initialHandoffCriticalPathSeconds),
				    std::memory_order_relaxed);
				}

				inline void recordSimInitialExactFrontierReplay(uint64_t frontierStateCount,
			                                                bool deviceSafeStore)
			{
			  simInitialExactFrontierReplayRequestCount().fetch_add(1, std::memory_order_relaxed);
			  simInitialExactFrontierReplayFrontierStateCount().fetch_add(frontierStateCount,
			                                                              std::memory_order_relaxed);
			  if(deviceSafeStore)
			  {
			    simInitialExactFrontierReplayDeviceSafeStoreCount().fetch_add(1,
			                                                                  std::memory_order_relaxed);
			  }
			}

			inline void recordSimInitialScanNanoseconds(uint64_t nanoseconds)
			{
			  simInitialScanNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
			}

		inline void recordSimInitialScanGpuNanoseconds(uint64_t nanoseconds)
		{
		  simInitialScanGpuNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialScanD2HNanoseconds(uint64_t nanoseconds)
		{
		  simInitialScanD2HNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialScanCpuMergeNanoseconds(uint64_t nanoseconds)
		{
		  simInitialScanCpuMergeNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialScanCpuContextApplyNanoseconds(uint64_t nanoseconds)
		{
		  simInitialScanCpuContextApplyNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialScanCpuSafeStoreUpdateNanoseconds(uint64_t nanoseconds)
		{
		  simInitialScanCpuSafeStoreUpdateNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialScanCpuSafeStorePruneNanoseconds(uint64_t nanoseconds)
		{
		  simInitialScanCpuSafeStorePruneNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialScanDiagNanoseconds(uint64_t nanoseconds)
		{
		  simInitialScanDiagNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialScanOnlineReduceNanoseconds(uint64_t nanoseconds)
		{
		  simInitialScanOnlineReduceNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialScanWaitNanoseconds(uint64_t nanoseconds)
		{
		  simInitialScanWaitNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialScanCountCopyNanoseconds(uint64_t nanoseconds)
		{
		  simInitialScanCountCopyNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialScanBaseUploadNanoseconds(uint64_t nanoseconds)
		{
		  simInitialScanBaseUploadNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialProposalSelectD2HNanoseconds(uint64_t nanoseconds)
		{
		  simInitialProposalSelectD2HNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialScanSyncWaitNanoseconds(uint64_t nanoseconds)
		{
		  simInitialScanSyncWaitNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialScanTailNanoseconds(uint64_t nanoseconds)
		{
		  simInitialScanTailNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimInitialHashReduceNanoseconds(uint64_t nanoseconds)
		{
		  simInitialHashReduceNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline double getSimInitialHashReduceSeconds()
		{
		  return static_cast<double>(simInitialHashReduceNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		}

		inline void recordSimInitialSegmentedReduceNanoseconds(uint64_t nanoseconds)
		{
		  simInitialSegmentedReduceNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline double getSimInitialSegmentedReduceSeconds()
		{
		  return static_cast<double>(simInitialSegmentedReduceNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		}

		inline void recordSimInitialSegmentedCompactNanoseconds(uint64_t nanoseconds)
		{
		  simInitialSegmentedCompactNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline double getSimInitialSegmentedCompactSeconds()
		{
		  return static_cast<double>(simInitialSegmentedCompactNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		}

		inline void recordSimInitialTopKNanoseconds(uint64_t nanoseconds)
		{
		  simInitialTopKNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline double getSimInitialTopKSeconds()
		{
		  return static_cast<double>(simInitialTopKNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		}

		inline void recordSimInitialSegmentedStateStats(uint64_t tileStateCount,uint64_t groupedStateCount)
		{
		  simInitialSegmentedTileStateCount().fetch_add(tileStateCount, std::memory_order_relaxed);
		  simInitialSegmentedGroupedStateCount().fetch_add(groupedStateCount, std::memory_order_relaxed);
		}

		inline void getSimInitialSegmentedStateStats(uint64_t &tileStateCount,uint64_t &groupedStateCount)
		{
		  tileStateCount = simInitialSegmentedTileStateCount().load(std::memory_order_relaxed);
		  groupedStateCount = simInitialSegmentedGroupedStateCount().load(std::memory_order_relaxed);
		}

		inline void recordSimProposalGpuNanoseconds(uint64_t nanoseconds)
		{
		  simProposalGpuNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimProposalTracebackBatchGpuNanoseconds(uint64_t nanoseconds)
		{
		  simProposalTracebackBatchGpuNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimProposalPostNanoseconds(uint64_t nanoseconds)
		{
		  simProposalPostNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimLocateNanoseconds(uint64_t nanoseconds)
		{
		  simLocateNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimLocateGpuNanoseconds(uint64_t nanoseconds)
		{
		  simLocateGpuNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimRegionScanGpuNanoseconds(uint64_t nanoseconds)
		{
		  simRegionScanGpuNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimRegionD2HNanoseconds(uint64_t nanoseconds)
		{
		  simRegionD2HNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimMaterializeNanoseconds(uint64_t nanoseconds)
		{
		  simMaterializeNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimTracebackDpNanoseconds(uint64_t nanoseconds)
		{
		  simTracebackDpNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void recordSimTracebackPostNanoseconds(uint64_t nanoseconds)
		{
		  simTracebackPostNanoseconds().fetch_add(nanoseconds, std::memory_order_relaxed);
		}

		inline void getSimBlockedMirrorStats(uint64_t &packWords,uint64_t &mirrorBytes)
		{
		  packWords = simBlockedPackWordCount().load(std::memory_order_relaxed);
		  mirrorBytes = simBlockedMirrorBytesMax().load(std::memory_order_relaxed);
		}

		inline void getSimWorkCellStats(uint64_t &regionCells,uint64_t &tracebackCells)
		{
		  regionCells = simRegionTotalCellCount().load(std::memory_order_relaxed);
		  tracebackCells = simTracebackTotalCellCount().load(std::memory_order_relaxed);
		}

		inline void getSimRegionReductionStats(uint64_t &eventCount,
		                                      uint64_t &summaryCount,
		                                      uint64_t &eventBytesD2H,
		                                      uint64_t &summaryBytesD2H,
		                                      double &cpuMergeSeconds,
		                                      uint64_t &locateCells)
		{
		  eventCount = simRegionEventCount().load(std::memory_order_relaxed);
		  summaryCount = simRegionCandidateSummaryCount().load(std::memory_order_relaxed);
		  eventBytesD2H = simRegionEventBytesD2HCount().load(std::memory_order_relaxed);
		  summaryBytesD2H = simRegionSummaryBytesD2HCount().load(std::memory_order_relaxed);
		  cpuMergeSeconds = static_cast<double>(simRegionCpuMergeNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  locateCells = simLocateTotalCellCount().load(std::memory_order_relaxed);
		}

		inline uint64_t getSimRegionPackedRequestCount()
		{
		  return simRegionPackedRequestCount().load(std::memory_order_relaxed);
		}

		inline void getSimRegionBucketedTrueBatchStats(uint64_t &batches,
		                                               uint64_t &requests,
		                                               uint64_t &fusedRequests,
		                                               uint64_t &actualCells,
		                                               uint64_t &paddedCells,
		                                               uint64_t &paddingCells,
		                                               uint64_t &rejectedPadding,
		                                               uint64_t &shadowMismatches)
		{
		  batches = simRegionBucketedTrueBatchBatchCount().load(std::memory_order_relaxed);
		  requests = simRegionBucketedTrueBatchRequestCount().load(std::memory_order_relaxed);
		  fusedRequests = simRegionBucketedTrueBatchFusedRequestCount().load(std::memory_order_relaxed);
		  actualCells = simRegionBucketedTrueBatchActualCellCount().load(std::memory_order_relaxed);
		  paddedCells = simRegionBucketedTrueBatchPaddedCellCount().load(std::memory_order_relaxed);
		  paddingCells = simRegionBucketedTrueBatchPaddingCellCount().load(std::memory_order_relaxed);
		  rejectedPadding = simRegionBucketedTrueBatchRejectedPaddingCount().load(std::memory_order_relaxed);
		  shadowMismatches = simRegionBucketedTrueBatchShadowMismatchCount().load(std::memory_order_relaxed);
		}

		struct SimRegionSingleRequestDirectReducePipelineStats
		{
		  uint64_t requestCount;
		  uint64_t rowCountTotal;
		  uint64_t rowCountMax;
		  uint64_t colCountTotal;
		  uint64_t colCountMax;
		  uint64_t cellCountTotal;
		  uint64_t cellCountMax;
		  uint64_t diagCountTotal;
		  uint64_t diagCountMax;
		  uint64_t filterStartCountTotal;
		  uint64_t filterStartCountMax;
		  uint64_t diagLaunchCount;
		  uint64_t eventCountLaunchCount;
		  uint64_t eventPrefixLaunchCount;
		  uint64_t runCountLaunchCount;
		  uint64_t runPrefixLaunchCount;
		  uint64_t runCompactLaunchCount;
		  uint64_t filterReduceLaunchCount;
		  uint64_t candidatePrefixLaunchCount;
		  uint64_t candidateCompactLaunchCount;
		  uint64_t countSnapshotLaunchCount;
		  uint64_t dpLt1msCount;
		  uint64_t dp1To5msCount;
		  uint64_t dp5To10msCount;
		  uint64_t dp10To50msCount;
		  uint64_t dpGte50msCount;
		  double dpMaxSeconds;
		  double metadataH2DSeconds;
		  double diagGpuSeconds;
		  double eventCountGpuSeconds;
		  double eventCountD2HSeconds;
		  double eventPrefixGpuSeconds;
		  double runCountGpuSeconds;
		  double runCountD2HSeconds;
		  double runPrefixGpuSeconds;
		  double runCompactGpuSeconds;
		  double candidatePrefixGpuSeconds;
		  double candidateCompactGpuSeconds;
		  double countSnapshotD2HSeconds;
		  double accountedGpuSeconds;
		  double unaccountedGpuSeconds;
		};

		struct SimRegionSingleRequestDirectReduceFusedDpStats
		{
		  uint64_t attempts;
		  uint64_t eligible;
		  uint64_t successes;
		  uint64_t fallbacks;
		  uint64_t shadowMismatches;
		  uint64_t rejectedByCells;
		  uint64_t rejectedByDiagLen;
		  uint64_t cells;
		  uint64_t requests;
		  uint64_t diagLaunchesReplaced;
		  double fusedDpGpuSeconds;
		  double oracleDpGpuSecondsShadow;
		  double fusedTotalGpuSeconds;
		};

		struct SimRegionSingleRequestDirectReduceCoopDpStats
		{
		  uint64_t supported;
		  uint64_t attempts;
		  uint64_t eligible;
		  uint64_t successes;
		  uint64_t fallbacks;
		  uint64_t shadowMismatches;
		  uint64_t rejectedByUnsupported;
		  uint64_t rejectedByCells;
		  uint64_t rejectedByDiagLen;
		  uint64_t rejectedByResidency;
		  uint64_t cells;
		  uint64_t requests;
		  uint64_t diagLaunchesReplaced;
		  double coopDpGpuSeconds;
		  double oracleDpGpuSecondsShadow;
		  double coopTotalGpuSeconds;
		};

		inline void getSimRegionSingleRequestDirectReduceStats(uint64_t &attempts,
		                                                       uint64_t &successes,
		                                                       uint64_t &fallbacks,
		                                                       uint64_t &overflows,
		                                                       uint64_t &shadowMismatches,
		                                                       uint64_t &hashCapacityMax,
		                                                       uint64_t &candidateCount,
		                                                       uint64_t &eventCount,
		                                                       uint64_t &runSummaryCount,
		                                                       double &gpuSeconds,
		                                                       double &dpGpuSeconds,
		                                                       double &filterReduceGpuSeconds,
		                                                       double &compactGpuSeconds,
		                                                       double &countD2HSeconds,
		                                                       double &candidateCountD2HSeconds,
		                                                       double &deferredCountSnapshotD2HSeconds,
		                                                       uint64_t &affectedStartCount,
		                                                       uint64_t &reduceWorkItems)
		{
		  attempts = simRegionSingleRequestDirectReduceAttemptCount().load(std::memory_order_relaxed);
		  successes = simRegionSingleRequestDirectReduceSuccessCount().load(std::memory_order_relaxed);
		  fallbacks = simRegionSingleRequestDirectReduceFallbackCount().load(std::memory_order_relaxed);
		  overflows = simRegionSingleRequestDirectReduceOverflowCount().load(std::memory_order_relaxed);
		  shadowMismatches =
		    simRegionSingleRequestDirectReduceShadowMismatchCount().load(std::memory_order_relaxed);
		  hashCapacityMax =
		    simRegionSingleRequestDirectReduceHashCapacityMax().load(std::memory_order_relaxed);
		  candidateCount =
		    simRegionSingleRequestDirectReduceCandidateCount().load(std::memory_order_relaxed);
		  eventCount = simRegionSingleRequestDirectReduceEventCount().load(std::memory_order_relaxed);
		  runSummaryCount =
		    simRegionSingleRequestDirectReduceRunSummaryCount().load(std::memory_order_relaxed);
		  gpuSeconds =
		    static_cast<double>(simRegionSingleRequestDirectReduceGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  dpGpuSeconds =
		    static_cast<double>(simRegionSingleRequestDirectReduceDpGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  filterReduceGpuSeconds =
		    static_cast<double>(simRegionSingleRequestDirectReduceFilterReduceGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  compactGpuSeconds =
		    static_cast<double>(simRegionSingleRequestDirectReduceCompactGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  countD2HSeconds =
		    static_cast<double>(simRegionSingleRequestDirectReduceCountD2HNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  candidateCountD2HSeconds =
		    static_cast<double>(simRegionSingleRequestDirectReduceCandidateCountD2HNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  deferredCountSnapshotD2HSeconds =
		    static_cast<double>(simRegionSingleRequestDirectReduceDeferredCountSnapshotD2HNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  affectedStartCount =
		    simRegionSingleRequestDirectReduceAffectedStartCount().load(std::memory_order_relaxed);
		  reduceWorkItems =
		    simRegionSingleRequestDirectReduceWorkItemCount().load(std::memory_order_relaxed);
		}

		inline void getSimRegionSingleRequestDirectReduceFusedDpStats(
		  SimRegionSingleRequestDirectReduceFusedDpStats &stats)
		{
		  stats.attempts =
		    simRegionSingleRequestDirectReduceFusedDpAttemptCount().load(std::memory_order_relaxed);
		  stats.eligible =
		    simRegionSingleRequestDirectReduceFusedDpEligibleCount().load(std::memory_order_relaxed);
		  stats.successes =
		    simRegionSingleRequestDirectReduceFusedDpSuccessCount().load(std::memory_order_relaxed);
		  stats.fallbacks =
		    simRegionSingleRequestDirectReduceFusedDpFallbackCount().load(std::memory_order_relaxed);
		  stats.shadowMismatches =
		    simRegionSingleRequestDirectReduceFusedDpShadowMismatchCount().load(std::memory_order_relaxed);
		  stats.rejectedByCells =
		    simRegionSingleRequestDirectReduceFusedDpRejectedByCellsCount().load(std::memory_order_relaxed);
		  stats.rejectedByDiagLen =
		    simRegionSingleRequestDirectReduceFusedDpRejectedByDiagLenCount().load(std::memory_order_relaxed);
		  stats.cells =
		    simRegionSingleRequestDirectReduceFusedDpCellCount().load(std::memory_order_relaxed);
		  stats.requests =
		    simRegionSingleRequestDirectReduceFusedDpRequestCount().load(std::memory_order_relaxed);
		  stats.diagLaunchesReplaced =
		    simRegionSingleRequestDirectReduceFusedDpDiagLaunchesReplacedCount().load(std::memory_order_relaxed);
		  stats.fusedDpGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReduceFusedDpGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.oracleDpGpuSecondsShadow =
		    static_cast<double>(
		      simRegionSingleRequestDirectReduceFusedOracleDpGpuNanosecondsShadow().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.fusedTotalGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReduceFusedTotalGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		}

		inline void getSimRegionSingleRequestDirectReduceCoopDpStats(
		  SimRegionSingleRequestDirectReduceCoopDpStats &stats)
		{
		  stats.supported =
		    simRegionSingleRequestDirectReduceCoopDpSupportedFlag().load(std::memory_order_relaxed);
		  stats.attempts =
		    simRegionSingleRequestDirectReduceCoopDpAttemptCount().load(std::memory_order_relaxed);
		  stats.eligible =
		    simRegionSingleRequestDirectReduceCoopDpEligibleCount().load(std::memory_order_relaxed);
		  stats.successes =
		    simRegionSingleRequestDirectReduceCoopDpSuccessCount().load(std::memory_order_relaxed);
		  stats.fallbacks =
		    simRegionSingleRequestDirectReduceCoopDpFallbackCount().load(std::memory_order_relaxed);
		  stats.shadowMismatches =
		    simRegionSingleRequestDirectReduceCoopDpShadowMismatchCount().load(std::memory_order_relaxed);
		  stats.rejectedByUnsupported =
		    simRegionSingleRequestDirectReduceCoopDpRejectedByUnsupportedCount().load(std::memory_order_relaxed);
		  stats.rejectedByCells =
		    simRegionSingleRequestDirectReduceCoopDpRejectedByCellsCount().load(std::memory_order_relaxed);
		  stats.rejectedByDiagLen =
		    simRegionSingleRequestDirectReduceCoopDpRejectedByDiagLenCount().load(std::memory_order_relaxed);
		  stats.rejectedByResidency =
		    simRegionSingleRequestDirectReduceCoopDpRejectedByResidencyCount().load(std::memory_order_relaxed);
		  stats.cells =
		    simRegionSingleRequestDirectReduceCoopDpCellCount().load(std::memory_order_relaxed);
		  stats.requests =
		    simRegionSingleRequestDirectReduceCoopDpRequestCount().load(std::memory_order_relaxed);
		  stats.diagLaunchesReplaced =
		    simRegionSingleRequestDirectReduceCoopDpDiagLaunchesReplacedCount().load(std::memory_order_relaxed);
		  stats.coopDpGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReduceCoopDpGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.oracleDpGpuSecondsShadow =
		    static_cast<double>(
		      simRegionSingleRequestDirectReduceCoopOracleDpGpuNanosecondsShadow().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.coopTotalGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReduceCoopTotalGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		}

		inline void getSimRegionSingleRequestDirectReducePipelineStats(
		  SimRegionSingleRequestDirectReducePipelineStats &stats)
		{
		  stats.requestCount =
		    simRegionSingleRequestDirectReducePipelineRequestCount().load(std::memory_order_relaxed);
		  stats.rowCountTotal =
		    simRegionSingleRequestDirectReducePipelineRowCountTotal().load(std::memory_order_relaxed);
		  stats.rowCountMax =
		    simRegionSingleRequestDirectReducePipelineRowCountMax().load(std::memory_order_relaxed);
		  stats.colCountTotal =
		    simRegionSingleRequestDirectReducePipelineColCountTotal().load(std::memory_order_relaxed);
		  stats.colCountMax =
		    simRegionSingleRequestDirectReducePipelineColCountMax().load(std::memory_order_relaxed);
		  stats.cellCountTotal =
		    simRegionSingleRequestDirectReducePipelineCellCountTotal().load(std::memory_order_relaxed);
		  stats.cellCountMax =
		    simRegionSingleRequestDirectReducePipelineCellCountMax().load(std::memory_order_relaxed);
		  stats.diagCountTotal =
		    simRegionSingleRequestDirectReducePipelineDiagCountTotal().load(std::memory_order_relaxed);
		  stats.diagCountMax =
		    simRegionSingleRequestDirectReducePipelineDiagCountMax().load(std::memory_order_relaxed);
		  stats.filterStartCountTotal =
		    simRegionSingleRequestDirectReducePipelineFilterStartCountTotal().load(std::memory_order_relaxed);
		  stats.filterStartCountMax =
		    simRegionSingleRequestDirectReducePipelineFilterStartCountMax().load(std::memory_order_relaxed);
		  stats.diagLaunchCount =
		    simRegionSingleRequestDirectReducePipelineDiagLaunchCount().load(std::memory_order_relaxed);
		  stats.eventCountLaunchCount =
		    simRegionSingleRequestDirectReducePipelineEventCountLaunchCount().load(std::memory_order_relaxed);
		  stats.eventPrefixLaunchCount =
		    simRegionSingleRequestDirectReducePipelineEventPrefixLaunchCount().load(std::memory_order_relaxed);
		  stats.runCountLaunchCount =
		    simRegionSingleRequestDirectReducePipelineRunCountLaunchCount().load(std::memory_order_relaxed);
		  stats.runPrefixLaunchCount =
		    simRegionSingleRequestDirectReducePipelineRunPrefixLaunchCount().load(std::memory_order_relaxed);
		  stats.runCompactLaunchCount =
		    simRegionSingleRequestDirectReducePipelineRunCompactLaunchCount().load(std::memory_order_relaxed);
		  stats.filterReduceLaunchCount =
		    simRegionSingleRequestDirectReducePipelineFilterReduceLaunchCount().load(std::memory_order_relaxed);
		  stats.candidatePrefixLaunchCount =
		    simRegionSingleRequestDirectReducePipelineCandidatePrefixLaunchCount().load(std::memory_order_relaxed);
		  stats.candidateCompactLaunchCount =
		    simRegionSingleRequestDirectReducePipelineCandidateCompactLaunchCount().load(std::memory_order_relaxed);
		  stats.countSnapshotLaunchCount =
		    simRegionSingleRequestDirectReducePipelineCountSnapshotLaunchCount().load(std::memory_order_relaxed);
		  stats.dpLt1msCount =
		    simRegionSingleRequestDirectReducePipelineDpLt1msCount().load(std::memory_order_relaxed);
		  stats.dp1To5msCount =
		    simRegionSingleRequestDirectReducePipelineDp1To5msCount().load(std::memory_order_relaxed);
		  stats.dp5To10msCount =
		    simRegionSingleRequestDirectReducePipelineDp5To10msCount().load(std::memory_order_relaxed);
		  stats.dp10To50msCount =
		    simRegionSingleRequestDirectReducePipelineDp10To50msCount().load(std::memory_order_relaxed);
		  stats.dpGte50msCount =
		    simRegionSingleRequestDirectReducePipelineDpGte50msCount().load(std::memory_order_relaxed);
		  stats.dpMaxSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineDpMaxNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.metadataH2DSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineMetadataH2DNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.diagGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineDiagGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.eventCountGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineEventCountGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.eventCountD2HSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineEventCountD2HNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.eventPrefixGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineEventPrefixGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.runCountGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineRunCountGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.runCountD2HSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineRunCountD2HNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.runPrefixGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineRunPrefixGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.runCompactGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineRunCompactGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.candidatePrefixGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineCandidatePrefixGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.candidateCompactGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineCandidateCompactGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.countSnapshotD2HSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineCountSnapshotD2HNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.accountedGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineAccountedGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		  stats.unaccountedGpuSeconds =
		    static_cast<double>(
		      simRegionSingleRequestDirectReducePipelineUnaccountedGpuNanoseconds().load(std::memory_order_relaxed)) /
		    1.0e9;
		}

			inline void getSimInitialReductionStats(uint64_t &eventCount,
			                                       uint64_t &summaryCount,
			                                       uint64_t &summaryBytesD2H,
		                                       uint64_t &reducedCandidateCount,
		                                       uint64_t &allCandidateStateCount,
		                                       uint64_t &storeBytesD2H,
		                                       uint64_t &storeBytesH2D,
		                                       uint64_t &storeUploadNanoseconds,
		                                       uint64_t &chunkCount,
		                                       uint64_t &chunkReplayedCount,
		                                       uint64_t &summaryReplayCount)
		{
		  eventCount = simInitialEventCount().load(std::memory_order_relaxed);
		  summaryCount = simInitialRunSummaryCount().load(std::memory_order_relaxed);
		  summaryBytesD2H = simInitialSummaryBytesD2HCount().load(std::memory_order_relaxed);
		  reducedCandidateCount = simInitialReducedCandidateCount().load(std::memory_order_relaxed);
		  allCandidateStateCount = simInitialAllCandidateStateCount().load(std::memory_order_relaxed);
		  storeBytesD2H = simInitialStoreBytesD2HCount().load(std::memory_order_relaxed);
		  storeBytesH2D = simInitialStoreBytesH2DCount().load(std::memory_order_relaxed);
		  storeUploadNanoseconds = simInitialStoreUploadNanoseconds().load(std::memory_order_relaxed);
		  chunkCount = simInitialReduceChunkCount().load(std::memory_order_relaxed);
		  chunkReplayedCount = simInitialReduceChunkReplayedCount().load(std::memory_order_relaxed);
			  summaryReplayCount = simInitialReduceSummaryReplayCount().load(std::memory_order_relaxed);
			}

				inline void getSimInitialSummaryPackedD2HStats(uint64_t &enabledCount,
				                                              uint64_t &packedBytesD2H,
				                                              uint64_t &unpackedEquivalentBytesD2H,
				                                              double &packSeconds,
				                                              uint64_t &fallbackCount)
			{
			  enabledCount = simInitialSummaryPackedD2HEnabledCount().load(std::memory_order_relaxed);
			  packedBytesD2H = simInitialSummaryPackedBytesD2HCount().load(std::memory_order_relaxed);
			  unpackedEquivalentBytesD2H =
			    simInitialSummaryUnpackedEquivalentBytesD2HCount().load(std::memory_order_relaxed);
			  packSeconds =
			    static_cast<double>(simInitialSummaryPackNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
					  fallbackCount = simInitialSummaryPackedD2HFallbackCount().load(std::memory_order_relaxed);
					}

					inline void getSimInitialSummaryHostCopyElisionStats(uint64_t &enabledCount,
					                                                    double &d2hCopySeconds,
					                                                    double &unpackSeconds,
					                                                    double &resultMaterializeSeconds,
					                                                    uint64_t &elidedBytes,
					                                                    uint64_t &countCopyReuses)
				{
				  enabledCount =
				    simInitialSummaryHostCopyElisionEnabledCount().load(std::memory_order_relaxed);
				  d2hCopySeconds =
				    static_cast<double>(simInitialSummaryD2HCopyNanoseconds().load(std::memory_order_relaxed)) /
				    1.0e9;
				  unpackSeconds =
				    static_cast<double>(simInitialSummaryUnpackNanoseconds().load(std::memory_order_relaxed)) /
				    1.0e9;
				  resultMaterializeSeconds =
				    static_cast<double>(
				      simInitialSummaryResultMaterializeNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
				  elidedBytes =
				    simInitialSummaryHostCopyElidedByteCount().load(std::memory_order_relaxed);
				  countCopyReuses =
				    simInitialSummaryHostCopyElisionCountCopyReuseCount().load(std::memory_order_relaxed);
					}

					 inline void getSimInitialContextApplyChunkSkipStats(uint64_t &chunkCount,
					                                                    uint64_t &chunkSkippedCount,
					                                                    uint64_t &chunkReplayedCount,
					                                                    uint64_t &summarySkippedCount,
				                                                    uint64_t &summaryReplayedCount)
				{
				  chunkCount = simInitialContextApplyChunkSkipChunkCount().load(std::memory_order_relaxed);
				  chunkSkippedCount =
				    simInitialContextApplyChunkSkipChunkSkippedCount().load(std::memory_order_relaxed);
				  chunkReplayedCount =
				    simInitialContextApplyChunkSkipChunkReplayedCount().load(std::memory_order_relaxed);
				  summarySkippedCount =
				    simInitialContextApplyChunkSkipSummarySkippedCount().load(std::memory_order_relaxed);
					  summaryReplayedCount =
					    simInitialContextApplyChunkSkipSummaryReplayedCount().load(std::memory_order_relaxed);
					}

					inline const char *simInitialChunkedHandoffFallbackReasonLabel(
					  SimInitialChunkedHandoffFallbackReason reason)
					{
					  switch(reason)
					  {
					    case SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_NONE:
					      return "none";
					    case SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_UNSUPPORTED_FAST_APPLY:
					      return "unsupported_fast_apply";
					    case SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_UNSUPPORTED_SHAPE:
					      return "unsupported_shape";
					    case SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_PINNED_ALLOCATION:
					      return "pinned_allocation";
					    case SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_PAGEABLE_COPY:
					      return "pageable_copy";
					    case SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_SYNC_COPY:
					      return "sync_copy";
					  }
					  return "unknown";
					}

					inline const char *simInitialPinnedAsyncHandoffDisabledReasonLabel(
					  SimScanCudaInitialPinnedAsyncDisabledReason reason)
					{
					  switch(reason)
					  {
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_NOT_REQUESTED:
					      return "not_requested";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_NONE:
					      return "none";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_CHUNKED_HANDOFF_OFF:
					      return "chunked_handoff_off";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_UNSUPPORTED_PATH:
					      return "unsupported_path";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_NO_SUMMARIES:
					      return "no_summaries";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_PACKED_SUMMARY_D2H:
					      return "packed_summary_d2h";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_HOST_COPY_ELISION:
					      return "host_copy_elision";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_DISABLED_NO_CHUNKS:
					      return "no_chunks";
					  }
					  return "unknown";
					}

					inline const char *simInitialPinnedAsyncHandoffSourceReadyModeLabel(
					  SimScanCudaInitialPinnedAsyncSourceReadyMode mode)
					{
					  switch(mode)
					  {
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_SOURCE_READY_NONE:
					      return "none";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_SOURCE_READY_GLOBAL_STOP_EVENT:
					      return "global_stop_event";
					  }
					  return "unknown";
					}

					inline const char *simInitialPinnedAsyncCpuPipelineDisabledReasonLabel(
					  SimScanCudaInitialPinnedAsyncCpuPipelineDisabledReason reason)
					{
					  switch(reason)
					  {
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_NOT_REQUESTED:
					      return "not_requested";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_NONE:
					      return "none";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_PINNED_ASYNC_OFF:
					      return "pinned_async_off";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_CHUNKED_HANDOFF_OFF:
					      return "chunked_handoff_off";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_UNSUPPORTED_PATH:
					      return "unsupported_path";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_NO_SUMMARIES:
					      return "no_summaries";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_NO_CHUNKS:
					      return "no_chunks";
					    case SIM_SCAN_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE_DISABLED_PINNED_ASYNC_FALLBACK:
					      return "pinned_async_fallback";
					  }
					  return "unknown";
					}

						inline void getSimInitialChunkedHandoffStats(SimInitialChunkedHandoffStats &stats)
						{
					  stats.chunkCount =
					    simInitialChunkedHandoffChunkCount().load(std::memory_order_relaxed);
					  stats.summariesReplayed =
					    simInitialChunkedHandoffSummaryReplayCount().load(std::memory_order_relaxed);
					  stats.ringSlots =
					    simInitialChunkedHandoffRingSlotCount().load(std::memory_order_relaxed);
					  stats.pinnedAllocationFailures =
					    simInitialChunkedHandoffPinnedAllocationFailureCount().load(std::memory_order_relaxed);
					  stats.pageableFallbacks =
					    simInitialChunkedHandoffPageableFallbackCount().load(std::memory_order_relaxed);
					  stats.syncCopies =
					    simInitialChunkedHandoffSyncCopyCount().load(std::memory_order_relaxed);
					  stats.cpuWaitNanoseconds =
					    simInitialChunkedHandoffCpuWaitNanoseconds().load(std::memory_order_relaxed);
					  stats.criticalPathD2HNanoseconds =
					    simInitialChunkedHandoffCriticalPathD2HNanoseconds().load(std::memory_order_relaxed);
					  stats.measuredOverlapNanoseconds =
					    simInitialChunkedHandoffMeasuredOverlapNanoseconds().load(std::memory_order_relaxed);
					  stats.fallbackCount =
					    simInitialChunkedHandoffFallbackCount().load(std::memory_order_relaxed);
					  stats.fallbackReason =
					    static_cast<SimInitialChunkedHandoffFallbackReason>(
						      simInitialChunkedHandoffFallbackReasonCode().load(std::memory_order_relaxed));
						}

						inline void getSimInitialPinnedAsyncHandoffStats(
						  SimInitialPinnedAsyncHandoffStats &stats)
						{
						  stats.requestedCount =
						    simInitialPinnedAsyncHandoffRequestedCount().load(std::memory_order_relaxed);
						  stats.activeCount =
						    simInitialPinnedAsyncHandoffActiveCount().load(std::memory_order_relaxed);
						  stats.disabledReason =
						    static_cast<SimScanCudaInitialPinnedAsyncDisabledReason>(
						      simInitialPinnedAsyncHandoffDisabledReasonCode().load(
						        std::memory_order_relaxed));
						  stats.sourceReadyMode =
						    static_cast<SimScanCudaInitialPinnedAsyncSourceReadyMode>(
						      simInitialPinnedAsyncHandoffSourceReadyModeCode().load(
						        std::memory_order_relaxed));
						  stats.cpuPipelineRequestedCount =
						    simInitialPinnedAsyncCpuPipelineRequestedCount().load(
						      std::memory_order_relaxed);
						  stats.cpuPipelineActiveCount =
						    simInitialPinnedAsyncCpuPipelineActiveCount().load(
						      std::memory_order_relaxed);
						  stats.cpuPipelineDisabledReason =
						    static_cast<SimScanCudaInitialPinnedAsyncCpuPipelineDisabledReason>(
						      simInitialPinnedAsyncCpuPipelineDisabledReasonCode().load(
						        std::memory_order_relaxed));
						  stats.cpuPipelineChunksApplied =
						    simInitialPinnedAsyncCpuPipelineChunksApplied().load(
						      std::memory_order_relaxed);
						  stats.cpuPipelineSummariesApplied =
						    simInitialPinnedAsyncCpuPipelineSummariesApplied().load(
						      std::memory_order_relaxed);
						  stats.cpuPipelineChunksFinalized =
						    simInitialPinnedAsyncCpuPipelineChunksFinalized().load(
						      std::memory_order_relaxed);
						  stats.cpuPipelineFinalizeCount =
						    simInitialPinnedAsyncCpuPipelineFinalizeCount().load(
						      std::memory_order_relaxed);
						  stats.cpuPipelineOutOfOrderChunks =
						    simInitialPinnedAsyncCpuPipelineOutOfOrderChunks().load(
						      std::memory_order_relaxed);
						  stats.chunkCount =
						    simInitialPinnedAsyncHandoffChunkCount().load(std::memory_order_relaxed);
						  stats.pinnedSlots =
						    simInitialPinnedAsyncHandoffPinnedSlotCount().load(std::memory_order_relaxed);
						  stats.pinnedBytes =
						    simInitialPinnedAsyncHandoffPinnedBytes().load(std::memory_order_relaxed);
						  stats.pinnedAllocationFailures =
						    simInitialPinnedAsyncHandoffPinnedAllocationFailureCount().load(
						      std::memory_order_relaxed);
						  stats.pageableFallbacks =
						    simInitialPinnedAsyncHandoffPageableFallbackCount().load(std::memory_order_relaxed);
						  stats.syncCopies =
						    simInitialPinnedAsyncHandoffSyncCopyCount().load(std::memory_order_relaxed);
						  stats.asyncCopies =
						    simInitialPinnedAsyncHandoffAsyncCopyCount().load(std::memory_order_relaxed);
						  stats.slotReuseWaits =
						    simInitialPinnedAsyncHandoffSlotReuseWaitCount().load(std::memory_order_relaxed);
						  stats.slotsReusedAfterMaterializeCount =
						    simInitialPinnedAsyncHandoffSlotsReusedAfterMaterializeCount().load(
						      std::memory_order_relaxed);
						  stats.asyncD2HNanoseconds =
						    simInitialPinnedAsyncHandoffAsyncD2HNanoseconds().load(std::memory_order_relaxed);
						  stats.d2hWaitNanoseconds =
						    simInitialPinnedAsyncHandoffD2HWaitNanoseconds().load(std::memory_order_relaxed);
						  stats.cpuApplyNanoseconds =
						    simInitialPinnedAsyncHandoffCpuApplyNanoseconds().load(std::memory_order_relaxed);
						  stats.cpuD2HOverlapNanoseconds =
						    simInitialPinnedAsyncHandoffCpuD2HOverlapNanoseconds().load(
						      std::memory_order_relaxed);
						  stats.dpD2HOverlapNanoseconds =
						    simInitialPinnedAsyncHandoffDpD2HOverlapNanoseconds().load(
						      std::memory_order_relaxed);
						  stats.criticalPathNanoseconds =
						    simInitialPinnedAsyncHandoffCriticalPathNanoseconds().load(
						      std::memory_order_relaxed);
						}

						inline void getSimInitialExactFrontierReplayStats(uint64_t &requestCount,
					                                                  uint64_t &frontierStateCount,
					                                                  uint64_t &deviceSafeStoreCount)
					{
					  requestCount =
					    simInitialExactFrontierReplayRequestCount().load(std::memory_order_relaxed);
					  frontierStateCount =
					    simInitialExactFrontierReplayFrontierStateCount().load(std::memory_order_relaxed);
					  deviceSafeStoreCount =
					    simInitialExactFrontierReplayDeviceSafeStoreCount().load(std::memory_order_relaxed);
					}

					inline void getSimInitialCpuFrontierFastApplyStats(
					  SimInitialCpuFrontierFastApplyTelemetry &stats)
					{
					  stats.enabledCount =
					    simInitialCpuFrontierFastApplyEnabledCount().load(std::memory_order_relaxed);
					  stats.attempts =
					    simInitialCpuFrontierFastApplyAttemptCount().load(std::memory_order_relaxed);
					  stats.successes =
					    simInitialCpuFrontierFastApplySuccessCount().load(std::memory_order_relaxed);
					  stats.fallbacks =
					    simInitialCpuFrontierFastApplyFallbackCount().load(std::memory_order_relaxed);
					  stats.shadowMismatches =
					    simInitialCpuFrontierFastApplyShadowMismatchCount().load(std::memory_order_relaxed);
					  stats.summariesReplayed =
					    simInitialCpuFrontierFastApplySummaryReplayCount().load(std::memory_order_relaxed);
					  stats.candidatesOut =
					    simInitialCpuFrontierFastApplyCandidateOutCount().load(std::memory_order_relaxed);
					  stats.fastApplyNanoseconds =
					    simInitialCpuFrontierFastApplyNanoseconds().load(std::memory_order_relaxed);
					  stats.oracleApplyNanosecondsShadow =
					    simInitialCpuFrontierFastApplyOracleNanosecondsShadow().load(std::memory_order_relaxed);
					  stats.rejectedByStats =
					    simInitialCpuFrontierFastApplyRejectedByStatsCount().load(std::memory_order_relaxed);
					  stats.rejectedByNonemptyContext =
					    simInitialCpuFrontierFastApplyRejectedByNonemptyContextCount().load(std::memory_order_relaxed);
					}

						inline void getSimInitialSafeStoreDeviceStats(uint64_t &frontierBytesH2D,
						                                              double &buildSeconds,
						                                              double &pruneSeconds,
			                                              double &frontierUploadSeconds)
			{
		  frontierBytesH2D = simInitialSafeStoreFrontierBytesH2DCount().load(std::memory_order_relaxed);
		  buildSeconds =
		    static_cast<double>(simInitialSafeStoreDeviceBuildNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  pruneSeconds =
		    static_cast<double>(simInitialSafeStoreDevicePruneNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
			  frontierUploadSeconds =
			    static_cast<double>(simInitialSafeStoreFrontierUploadNanoseconds().load(std::memory_order_relaxed)) /
			    1.0e9;
			}

			inline void getSimInitialFrontierTransducerShadowStats(uint64_t &callCount,
			                                                       double &seconds,
			                                                       uint64_t &digestD2HBytes,
			                                                       uint64_t &summaryReplayCount,
			                                                       uint64_t &mismatchCount)
			{
			  callCount = simInitialFrontierTransducerShadowCallCount().load(std::memory_order_relaxed);
			  seconds =
			    static_cast<double>(simInitialFrontierTransducerShadowNanoseconds().load(std::memory_order_relaxed)) /
			    1.0e9;
			  digestD2HBytes = simInitialFrontierTransducerShadowDigestD2HBytes().load(std::memory_order_relaxed);
			  summaryReplayCount =
			    simInitialFrontierTransducerShadowSummaryReplayCount().load(std::memory_order_relaxed);
			  mismatchCount = simInitialFrontierTransducerShadowMismatchCount().load(std::memory_order_relaxed);
			}

			inline void getSimInitialOrderedSegmentedV3ShadowStats(uint64_t &callCount,
			                                                       uint64_t &frontierMismatchCount,
			                                                       uint64_t &runningMinMismatchCount,
			                                                       uint64_t &safeStoreMismatchCount,
			                                                       uint64_t &candidateCountMismatchCount,
			                                                       uint64_t &candidateValueMismatchCount)
			{
			  callCount = simInitialOrderedSegmentedV3ShadowCallCount().load(std::memory_order_relaxed);
			  frontierMismatchCount =
			    simInitialOrderedSegmentedV3ShadowFrontierMismatchCount().load(std::memory_order_relaxed);
			  runningMinMismatchCount =
			    simInitialOrderedSegmentedV3ShadowRunningMinMismatchCount().load(std::memory_order_relaxed);
			  safeStoreMismatchCount =
			    simInitialOrderedSegmentedV3ShadowSafeStoreMismatchCount().load(std::memory_order_relaxed);
			  candidateCountMismatchCount =
			    simInitialOrderedSegmentedV3ShadowCandidateCountMismatchCount().load(std::memory_order_relaxed);
			  candidateValueMismatchCount =
			    simInitialOrderedSegmentedV3ShadowCandidateValueMismatchCount().load(std::memory_order_relaxed);
			}

			inline void getSimProposalStats(uint64_t &allCandidateStateCount,
			                               uint64_t &bytesD2H,
		                               uint64_t &selectedCount,
		                               uint64_t &selectedBoxCellCount,
		                               uint64_t &materializedCount,
		                               uint64_t &materializedQueryBases,
		                               uint64_t &materializedTargetBases,
		                               double &gpuSeconds)
		{
		  allCandidateStateCount = simProposalAllCandidateStateCount().load(std::memory_order_relaxed);
		  bytesD2H = simProposalBytesD2HCount().load(std::memory_order_relaxed);
		  selectedCount = simProposalSelectedCount().load(std::memory_order_relaxed);
		  selectedBoxCellCount = simProposalSelectedBoxCellCount().load(std::memory_order_relaxed);
		  materializedCount = simProposalMaterializedCount().load(std::memory_order_relaxed);
		  materializedQueryBases = simProposalMaterializedQueryBaseCount().load(std::memory_order_relaxed);
		  materializedTargetBases = simProposalMaterializedTargetBaseCount().load(std::memory_order_relaxed);
		  gpuSeconds = static_cast<double>(simProposalGpuNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		}

		inline void getSimInitialProposalV2Stats(uint64_t &batchCount,
		                                        uint64_t &requestCount)
		{
		  batchCount = simInitialProposalV2BatchCount().load(std::memory_order_relaxed);
		  requestCount = simInitialProposalV2RequestCount().load(std::memory_order_relaxed);
		}

		inline void getSimInitialProposalV3Stats(uint64_t &batchCount,
		                                        uint64_t &requestCount,
		                                        uint64_t &selectedStateCount,
		                                        double &gpuSeconds)
		{
		  batchCount = simInitialProposalV3BatchCount().load(std::memory_order_relaxed);
		  requestCount = simInitialProposalV3RequestCount().load(std::memory_order_relaxed);
		  selectedStateCount = simInitialProposalV3SelectedCandidateStateCount().load(std::memory_order_relaxed);
		  gpuSeconds = static_cast<double>(simInitialProposalV3GpuNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		}

		inline void getSimInitialProposalDirectTopKStats(uint64_t &batchCount,
		                                                 uint64_t &logicalCandidateCount,
		                                                 uint64_t &materializedCandidateCount,
		                                                 double &gpuSeconds)
		{
		  batchCount = simInitialProposalDirectTopKBatchCount().load(std::memory_order_relaxed);
		  logicalCandidateCount = simInitialProposalDirectTopKLogicalCandidateStateCount().load(std::memory_order_relaxed);
		  materializedCandidateCount =
		    simInitialProposalDirectTopKMaterializedCandidateStateCount().load(std::memory_order_relaxed);
		  gpuSeconds = static_cast<double>(simInitialProposalDirectTopKGpuNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		}

		inline void getSimProposalMaterializeBatchStats(uint64_t &requestCount,
		                                                uint64_t &batchCount,
		                                                uint64_t &successCount,
		                                                uint64_t &fallbackCount,
		                                                uint64_t &tieFallbackCount,
		                                                double &gpuSeconds,
		                                                double &postSeconds)
		{
		  requestCount = simProposalTracebackBatchRequestCount().load(std::memory_order_relaxed);
		  batchCount = simProposalTracebackBatchCount().load(std::memory_order_relaxed);
		  successCount = simProposalTracebackBatchSuccessCount().load(std::memory_order_relaxed);
		  fallbackCount = simProposalTracebackBatchFallbackCount().load(std::memory_order_relaxed);
		  tieFallbackCount = simProposalTracebackBatchTieFallbackCount().load(std::memory_order_relaxed);
		  gpuSeconds = static_cast<double>(simProposalTracebackBatchGpuNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  postSeconds = static_cast<double>(simProposalPostNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		}

		inline void getSimProposalTracebackRoutingStats(uint64_t &cudaEligibleCount,
		                                                uint64_t &cudaSizeFilteredCount,
		                                                uint64_t &cudaBatchFailedCount,
		                                                uint64_t &cpuDirectCount,
		                                                uint64_t &postScoreRejectCount,
		                                                uint64_t &postNtRejectCount,
		                                                uint64_t &cpuCellCount,
		                                                uint64_t &cudaCellCount)
		{
		  cudaEligibleCount = simProposalTracebackCudaEligibleCount().load(std::memory_order_relaxed);
		  cudaSizeFilteredCount = simProposalTracebackCudaSizeFilteredCount().load(std::memory_order_relaxed);
		  cudaBatchFailedCount = simProposalTracebackCudaBatchFailedCount().load(std::memory_order_relaxed);
		  cpuDirectCount = simProposalTracebackCpuDirectCount().load(std::memory_order_relaxed);
		  postScoreRejectCount = simProposalPostScoreRejectCount().load(std::memory_order_relaxed);
		  postNtRejectCount = simProposalPostNtRejectCount().load(std::memory_order_relaxed);
		  cpuCellCount = simProposalTracebackCpuCellCount().load(std::memory_order_relaxed);
		  cudaCellCount = simProposalTracebackCudaCellCount().load(std::memory_order_relaxed);
		}

		inline void getSimProposalLoopStats(uint64_t &attemptCount,
		                                   uint64_t &shortCircuitCount,
		                                   uint64_t &initialSourceCount,
		                                   uint64_t &safeStoreSourceCount,
		                                   uint64_t &fallbackNoStoreCount,
		                                   uint64_t &fallbackSelectorFailureCount,
		                                   uint64_t &fallbackEmptySelectionCount)
		{
		  attemptCount = simProposalLoopAttemptCount().load(std::memory_order_relaxed);
		  shortCircuitCount = simProposalLoopShortCircuitCount().load(std::memory_order_relaxed);
		  initialSourceCount = simProposalLoopInitialSourceCount().load(std::memory_order_relaxed);
		  safeStoreSourceCount = simProposalLoopSafeStoreSourceCount().load(std::memory_order_relaxed);
		  fallbackNoStoreCount = simProposalLoopFallbackNoStoreCount().load(std::memory_order_relaxed);
		  fallbackSelectorFailureCount =
		    simProposalLoopFallbackSelectorFailureCount().load(std::memory_order_relaxed);
		  fallbackEmptySelectionCount =
		    simProposalLoopFallbackEmptySelectionCount().load(std::memory_order_relaxed);
		}

		inline void getSimDeviceKLoopStats(uint64_t &gpuSafeStoreSourceCount,
		                                  uint64_t &gpuFrontierCacheSourceCount,
		                                  uint64_t &gpuSafeStoreFullSourceCount,
		                                  double &deviceKLoopSeconds)
		{
		  gpuSafeStoreSourceCount =
		    simProposalLoopGpuSafeStoreSourceCount().load(std::memory_order_relaxed);
		  gpuFrontierCacheSourceCount =
		    simProposalLoopGpuFrontierCacheSourceCount().load(std::memory_order_relaxed);
		  gpuSafeStoreFullSourceCount =
		    simProposalLoopGpuSafeStoreFullSourceCount().load(std::memory_order_relaxed);
		  deviceKLoopSeconds =
		    static_cast<double>(simDeviceKLoopNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		}

		inline void getSimLocateDeviceKLoopStats(uint64_t &attemptCount,uint64_t &shortCircuitCount)
		{
		  attemptCount = simLocateDeviceKLoopAttemptCount().load(std::memory_order_relaxed);
		  shortCircuitCount = simLocateDeviceKLoopShortCircuitCount().load(std::memory_order_relaxed);
		}

		inline void getSimProposalMaterializeBackendStats(uint64_t &cpuBackendCount,
		                                                 uint64_t &cudaBatchBackendCount,
		                                                 uint64_t &hybridBackendCount)
		{
		  cpuBackendCount = simProposalMaterializeCpuBackendCount().load(std::memory_order_relaxed);
		  cudaBatchBackendCount =
		    simProposalMaterializeCudaBatchBackendCount().load(std::memory_order_relaxed);
		  hybridBackendCount = simProposalMaterializeHybridBackendCount().load(std::memory_order_relaxed);
		}

		inline void getSimPhaseTimingStats(double &initialScanSeconds,
		                                   double &initialScanGpuSeconds,
		                                   double &initialScanD2HSeconds,
		                                   double &initialScanCpuMergeSeconds,
		                                   double &initialScanDiagSeconds,
		                                   double &initialScanOnlineReduceSeconds,
		                                   double &initialScanWaitSeconds,
		                                   double &initialScanCountCopySeconds,
		                                   double &initialScanBaseUploadSeconds,
		                                   double &initialProposalSelectD2HSeconds,
		                                   double &initialScanSyncWaitSeconds,
		                                   double &initialScanTailSeconds,
		                                   double &locateSeconds,
		                                   double &locateGpuSeconds,
		                                   double &regionScanGpuSeconds,
		                                   double &regionD2HSeconds,
		                                   double &materializeSeconds,
		                                   double &tracebackDpSeconds,
		                                   double &tracebackPostSeconds)
		{
		  initialScanSeconds = static_cast<double>(simInitialScanNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  initialScanGpuSeconds = static_cast<double>(simInitialScanGpuNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  initialScanD2HSeconds = static_cast<double>(simInitialScanD2HNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  initialScanCpuMergeSeconds = static_cast<double>(simInitialScanCpuMergeNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  initialScanDiagSeconds = static_cast<double>(simInitialScanDiagNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  initialScanOnlineReduceSeconds =
		    static_cast<double>(simInitialScanOnlineReduceNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  initialScanWaitSeconds = static_cast<double>(simInitialScanWaitNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  initialScanCountCopySeconds =
		    static_cast<double>(simInitialScanCountCopyNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  initialScanBaseUploadSeconds =
		    static_cast<double>(simInitialScanBaseUploadNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  initialProposalSelectD2HSeconds =
		    static_cast<double>(simInitialProposalSelectD2HNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  initialScanSyncWaitSeconds =
		    static_cast<double>(simInitialScanSyncWaitNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  initialScanTailSeconds = static_cast<double>(simInitialScanTailNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  locateSeconds = static_cast<double>(simLocateNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  locateGpuSeconds = static_cast<double>(simLocateGpuNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  regionScanGpuSeconds = static_cast<double>(simRegionScanGpuNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  regionD2HSeconds = static_cast<double>(simRegionD2HNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  materializeSeconds = static_cast<double>(simMaterializeNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  tracebackDpSeconds = static_cast<double>(simTracebackDpNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		  tracebackPostSeconds = static_cast<double>(simTracebackPostNanoseconds().load(std::memory_order_relaxed)) / 1.0e9;
		}

		inline void getSimInitialCpuMergeTimingNanoseconds(uint64_t &contextApplyNanoseconds,
		                                                   uint64_t &safeStoreUpdateNanoseconds,
		                                                   uint64_t &safeStorePruneNanoseconds,
		                                                   uint64_t &safeStoreUploadNanoseconds)
		{
		  contextApplyNanoseconds = simInitialScanCpuContextApplyNanoseconds().load(std::memory_order_relaxed);
		  safeStoreUpdateNanoseconds = simInitialScanCpuSafeStoreUpdateNanoseconds().load(std::memory_order_relaxed);
		  safeStorePruneNanoseconds = simInitialScanCpuSafeStorePruneNanoseconds().load(std::memory_order_relaxed);
		  safeStoreUploadNanoseconds = simInitialStoreUploadNanoseconds().load(std::memory_order_relaxed);
		}

		inline void getSimInitialCpuMergeTimingStats(double &contextApplySeconds,
		                                             double &safeStoreUpdateSeconds,
		                                             double &safeStorePruneSeconds,
		                                             double &safeStoreUploadSeconds)
		{
		  uint64_t contextApplyNanoseconds = 0;
		  uint64_t safeStoreUpdateNanoseconds = 0;
		  uint64_t safeStorePruneNanoseconds = 0;
		  uint64_t safeStoreUploadNanoseconds = 0;
		  getSimInitialCpuMergeTimingNanoseconds(contextApplyNanoseconds,
		                                         safeStoreUpdateNanoseconds,
		                                         safeStorePruneNanoseconds,
		                                         safeStoreUploadNanoseconds);
		  contextApplySeconds = static_cast<double>(contextApplyNanoseconds) / 1.0e9;
		  safeStoreUpdateSeconds = static_cast<double>(safeStoreUpdateNanoseconds) / 1.0e9;
		  safeStorePruneSeconds = static_cast<double>(safeStorePruneNanoseconds) / 1.0e9;
		  safeStoreUploadSeconds = static_cast<double>(safeStoreUploadNanoseconds) / 1.0e9;
		}

		inline void getSimPhaseTimingStats(double &initialScanSeconds,
		                                   double &initialScanGpuSeconds,
		                                   double &initialScanD2HSeconds,
		                                   double &initialScanCpuMergeSeconds,
		                                   double &initialScanDiagSeconds,
		                                   double &initialScanOnlineReduceSeconds,
		                                   double &initialScanWaitSeconds,
		                                   double &locateSeconds,
		                                   double &locateGpuSeconds,
		                                   double &regionScanGpuSeconds,
		                                   double &regionD2HSeconds,
		                                   double &materializeSeconds,
		                                   double &tracebackDpSeconds,
		                                   double &tracebackPostSeconds)
		{
		  double initialScanCountCopySeconds = 0.0;
		  double initialScanBaseUploadSeconds = 0.0;
		  double initialProposalSelectD2HSeconds = 0.0;
		  double initialScanSyncWaitSeconds = 0.0;
		  double initialScanTailSeconds = 0.0;
		  getSimPhaseTimingStats(initialScanSeconds,
		                         initialScanGpuSeconds,
		                         initialScanD2HSeconds,
		                         initialScanCpuMergeSeconds,
		                         initialScanDiagSeconds,
		                         initialScanOnlineReduceSeconds,
		                         initialScanWaitSeconds,
		                         initialScanCountCopySeconds,
		                         initialScanBaseUploadSeconds,
		                         initialProposalSelectD2HSeconds,
		                         initialScanSyncWaitSeconds,
		                         initialScanTailSeconds,
		                         locateSeconds,
		                         locateGpuSeconds,
		                         regionScanGpuSeconds,
		                         regionD2HSeconds,
		                         materializeSeconds,
		                         tracebackDpSeconds,
		                         tracebackPostSeconds);
		}

		inline void getSimPhaseTimingStats(double &initialScanSeconds,
		                                   double &initialScanGpuSeconds,
		                                   double &initialScanD2HSeconds,
		                                   double &initialScanCpuMergeSeconds,
		                                   double &initialScanDiagSeconds,
		                                   double &initialScanOnlineReduceSeconds,
		                                   double &initialScanWaitSeconds,
		                                   double &initialScanCountCopySeconds,
		                                   double &initialScanBaseUploadSeconds,
		                                   double &initialScanSyncWaitSeconds,
		                                   double &locateSeconds,
		                                   double &locateGpuSeconds,
		                                   double &regionScanGpuSeconds,
		                                   double &regionD2HSeconds,
		                                   double &materializeSeconds,
		                                   double &tracebackDpSeconds,
		                                   double &tracebackPostSeconds)
		{
		  double initialProposalSelectD2HSeconds = 0.0;
		  double initialScanTailSeconds = 0.0;
		  getSimPhaseTimingStats(initialScanSeconds,
		                         initialScanGpuSeconds,
		                         initialScanD2HSeconds,
		                         initialScanCpuMergeSeconds,
		                         initialScanDiagSeconds,
		                         initialScanOnlineReduceSeconds,
		                         initialScanWaitSeconds,
		                         initialScanCountCopySeconds,
		                         initialScanBaseUploadSeconds,
		                         initialProposalSelectD2HSeconds,
		                         initialScanSyncWaitSeconds,
		                         initialScanTailSeconds,
		                         locateSeconds,
		                         locateGpuSeconds,
		                         regionScanGpuSeconds,
		                         regionD2HSeconds,
		                         materializeSeconds,
		                         tracebackDpSeconds,
		                         tracebackPostSeconds);
		}

			inline std::atomic<uint64_t> &simTracebackCudaCallCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simTracebackCandidateCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline std::atomic<uint64_t> &simTracebackTieCount()
			{
			  static std::atomic<uint64_t> count(0);
			  return count;
			}

			inline void recordSimTracebackCandidate(bool hadTie)
			{
			  simTracebackCandidateCount().fetch_add(1, std::memory_order_relaxed);
			  if(hadTie)
			  {
			    simTracebackTieCount().fetch_add(1, std::memory_order_relaxed);
			  }
			}

			inline void getSimTracebackStats(uint64_t &candidateCount,uint64_t &tieCount)
			{
			  candidateCount = simTracebackCandidateCount().load(std::memory_order_relaxed);
			  tieCount = simTracebackTieCount().load(std::memory_order_relaxed);
			}

		inline void recordSimTracebackBackend(bool usedCuda)
		{
		  if(usedCuda)
		  {
		    simTracebackCudaCallCount().fetch_add(1, std::memory_order_relaxed);
		  }
		  else
		  {
		    simTracebackCpuCallCount().fetch_add(1, std::memory_order_relaxed);
		  }
		}

		inline void getSimTracebackBackendCounts(uint64_t &cpuCalls,uint64_t &cudaCalls)
		{
		  cpuCalls = simTracebackCpuCallCount().load(std::memory_order_relaxed);
		  cudaCalls = simTracebackCudaCallCount().load(std::memory_order_relaxed);
		}

struct SimKernelContext
		{
  SimKernelContext(long queryLength,long targetLength):
    gapOpen(0),
    gapExtend(0),
	    runningMin(0),
	    candidateCount(0),
	    proposalCandidateLoop(false),
	    safeCandidateStateStore(),
	    gpuSafeCandidateStateStore(),
	    gpuFrontierCacheInSync(false),
	    initialSafeStoreHandoffActive(false),
	    workspace(queryLength,targetLength),
    tracebackScratch(static_cast<size_t>(queryLength + targetLength + 2),0),
    statsEnabled(simCandidateStatsEnabledRuntime()),
    stats()
  {
    memset(scoreMatrix,0,sizeof(scoreMatrix));
    recordSimBlockedMirrorBytes(static_cast<uint64_t>(workspace.blockedDense.size()) *
                                static_cast<uint64_t>(sizeof(uint64_t)));
    if(statsEnabled)
    {
      stats.clear();
    }
  }

  SimKernelContext(const SimKernelContext &other):
    gapOpen(other.gapOpen),
    gapExtend(other.gapExtend),
	    runningMin(other.runningMin),
	    candidateCount(other.candidateCount),
	    proposalCandidateLoop(other.proposalCandidateLoop),
	    safeCandidateStateStore(other.safeCandidateStateStore),
	    gpuSafeCandidateStateStore(),
	    gpuFrontierCacheInSync(false),
	    initialSafeStoreHandoffActive(false),
	    workspace(other.workspace),
    candidateStartIndex(other.candidateStartIndex),
    candidateMinHeap(other.candidateMinHeap),
    wavefrontSubstitutionStartI(other.wavefrontSubstitutionStartI),
    wavefrontSubstitutionScores(other.wavefrontSubstitutionScores),
    tracebackScratch(other.tracebackScratch),
    statsEnabled(other.statsEnabled),
    stats(other.stats)
  {
    memcpy(scoreMatrix,other.scoreMatrix,sizeof(scoreMatrix));
    memcpy(candidates,other.candidates,sizeof(candidates));
  }

  SimKernelContext(SimKernelContext &&other):
    gapOpen(other.gapOpen),
    gapExtend(other.gapExtend),
	    runningMin(other.runningMin),
	    candidateCount(other.candidateCount),
	    proposalCandidateLoop(other.proposalCandidateLoop),
	    safeCandidateStateStore(std::move(other.safeCandidateStateStore)),
	    gpuSafeCandidateStateStore(other.gpuSafeCandidateStateStore),
	    gpuFrontierCacheInSync(other.gpuFrontierCacheInSync),
	    initialSafeStoreHandoffActive(other.initialSafeStoreHandoffActive),
	    workspace(std::move(other.workspace)),
    candidateStartIndex(other.candidateStartIndex),
    candidateMinHeap(std::move(other.candidateMinHeap)),
    wavefrontSubstitutionStartI(std::move(other.wavefrontSubstitutionStartI)),
    wavefrontSubstitutionScores(std::move(other.wavefrontSubstitutionScores)),
    tracebackScratch(std::move(other.tracebackScratch)),
    statsEnabled(other.statsEnabled),
    stats(other.stats)
  {
    memcpy(scoreMatrix,other.scoreMatrix,sizeof(scoreMatrix));
    memcpy(candidates,other.candidates,sizeof(candidates));
    clearSimCudaPersistentSafeStoreHandle(other.gpuSafeCandidateStateStore);
    other.gpuFrontierCacheInSync = false;
    other.initialSafeStoreHandoffActive = false;
  }

  SimKernelContext &operator=(const SimKernelContext &other)
  {
    if(this != &other)
    {
      releaseSimCudaPersistentSafeCandidateStateStore(gpuSafeCandidateStateStore);
      memcpy(scoreMatrix,other.scoreMatrix,sizeof(scoreMatrix));
      gapOpen = other.gapOpen;
      gapExtend = other.gapExtend;
      runningMin = other.runningMin;
      candidateCount = other.candidateCount;
      proposalCandidateLoop = other.proposalCandidateLoop;
      memcpy(candidates,other.candidates,sizeof(candidates));
      safeCandidateStateStore = other.safeCandidateStateStore;
      clearSimCudaPersistentSafeStoreHandle(gpuSafeCandidateStateStore);
      gpuFrontierCacheInSync = false;
      initialSafeStoreHandoffActive = false;
      workspace = other.workspace;
      candidateStartIndex = other.candidateStartIndex;
      candidateMinHeap = other.candidateMinHeap;
      wavefrontSubstitutionStartI = other.wavefrontSubstitutionStartI;
      wavefrontSubstitutionScores = other.wavefrontSubstitutionScores;
      tracebackScratch = other.tracebackScratch;
      statsEnabled = other.statsEnabled;
      stats = other.stats;
    }
    return *this;
  }

  SimKernelContext &operator=(SimKernelContext &&other)
  {
    if(this != &other)
    {
      releaseSimCudaPersistentSafeCandidateStateStore(gpuSafeCandidateStateStore);
      memcpy(scoreMatrix,other.scoreMatrix,sizeof(scoreMatrix));
      gapOpen = other.gapOpen;
      gapExtend = other.gapExtend;
      runningMin = other.runningMin;
      candidateCount = other.candidateCount;
      proposalCandidateLoop = other.proposalCandidateLoop;
      memcpy(candidates,other.candidates,sizeof(candidates));
      safeCandidateStateStore = std::move(other.safeCandidateStateStore);
      gpuSafeCandidateStateStore = other.gpuSafeCandidateStateStore;
      clearSimCudaPersistentSafeStoreHandle(other.gpuSafeCandidateStateStore);
      gpuFrontierCacheInSync = other.gpuFrontierCacheInSync;
      other.gpuFrontierCacheInSync = false;
      initialSafeStoreHandoffActive = other.initialSafeStoreHandoffActive;
      other.initialSafeStoreHandoffActive = false;
      workspace = std::move(other.workspace);
      candidateStartIndex = other.candidateStartIndex;
      candidateMinHeap = std::move(other.candidateMinHeap);
      wavefrontSubstitutionStartI = std::move(other.wavefrontSubstitutionStartI);
      wavefrontSubstitutionScores = std::move(other.wavefrontSubstitutionScores);
      tracebackScratch = std::move(other.tracebackScratch);
      statsEnabled = other.statsEnabled;
      stats = other.stats;
    }
    return *this;
  }

  ~SimKernelContext()
  {
    releaseSimCudaPersistentSafeCandidateStateStore(gpuSafeCandidateStateStore);
  }

  long scoreMatrix[128][128];
  long gapOpen;
  long gapExtend;
  long runningMin;
  long candidateCount;
  bool proposalCandidateLoop;
  SimCandidate candidates[K];
  SimCandidateStateStore safeCandidateStateStore;
  SimCudaPersistentSafeStoreHandle gpuSafeCandidateStateStore;
  bool gpuFrontierCacheInSync;
  bool initialSafeStoreHandoffActive;
  SimWorkspace workspace;
  SimCandidateStartIndex candidateStartIndex;
  SimCandidateMinHeap candidateMinHeap;
  vector<long> wavefrontSubstitutionStartI;
  vector< vector<int> > wavefrontSubstitutionScores;
  vector<long> tracebackScratch;
  bool statsEnabled;
  SimCandidateStats stats;
};

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetryCallCount()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetryBandCount()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetrySingleBandCallCount()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetryAffectedStartCount()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetryCellCount()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetryMaxBandRows()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetryMaxBandCols()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetryMergeableCallCount()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetryMergeableCellCount()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetryEstimatedLaunchReductionCount()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetryRejectedRunningMinCount()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetryRejectedSafeStoreEpochCount()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetryRejectedScoreMatrixCount()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline std::atomic<uint64_t> &simRegionSchedulerShapeTelemetryRejectedFilterCount()
{
  static std::atomic<uint64_t> count(0);
  return count;
}

inline uint64_t simRegionSchedulerShapeHashCombine(uint64_t hash,uint64_t value)
{
  return hash ^ (value + 0x9e3779b97f4a7c15ull + (hash << 6) + (hash >> 2));
}

inline uint64_t simRegionSchedulerShapeCandidateStateFingerprint(const SimScanCudaCandidateState &state)
{
  uint64_t hash = 1469598103934665603ull;
  hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(static_cast<int64_t>(state.score)));
  hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(static_cast<int64_t>(state.startI)));
  hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(static_cast<int64_t>(state.startJ)));
  hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(static_cast<int64_t>(state.endI)));
  hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(static_cast<int64_t>(state.endJ)));
  hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(static_cast<int64_t>(state.top)));
  hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(static_cast<int64_t>(state.bot)));
  hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(static_cast<int64_t>(state.left)));
  hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(static_cast<int64_t>(state.right)));
  return hash;
}

inline uint64_t simRegionSchedulerShapeSafeStoreFingerprint(const SimKernelContext &context)
{
  uint64_t hash = 1469598103934665603ull;
  hash = simRegionSchedulerShapeHashCombine(hash,context.safeCandidateStateStore.valid ? 1ull : 0ull);
  if(context.safeCandidateStateStore.valid)
  {
    vector<uint64_t> stateFingerprints;
    stateFingerprints.reserve(context.safeCandidateStateStore.states.size());
    for(size_t stateIndex = 0; stateIndex < context.safeCandidateStateStore.states.size(); ++stateIndex)
    {
      stateFingerprints.push_back(
        simRegionSchedulerShapeCandidateStateFingerprint(context.safeCandidateStateStore.states[stateIndex]));
    }
    sort(stateFingerprints.begin(),stateFingerprints.end());
    hash = simRegionSchedulerShapeHashCombine(hash,
                                             static_cast<uint64_t>(stateFingerprints.size()));
    for(size_t stateIndex = 0; stateIndex < stateFingerprints.size(); ++stateIndex)
    {
      hash = simRegionSchedulerShapeHashCombine(hash,stateFingerprints[stateIndex]);
    }
  }

  const SimCudaPersistentSafeStoreHandle &gpuStore = context.gpuSafeCandidateStateStore;
  hash = simRegionSchedulerShapeHashCombine(hash,gpuStore.valid ? 1ull : 0ull);
  if(gpuStore.valid)
  {
    hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(static_cast<int64_t>(gpuStore.device)));
    hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(static_cast<int64_t>(gpuStore.slot)));
    hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(gpuStore.stateCount));
    hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(gpuStore.telemetryEpoch));
    hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(gpuStore.statesDevice));
    hash = simRegionSchedulerShapeHashCombine(hash,gpuStore.frontierValid ? 1ull : 0ull);
    hash = simRegionSchedulerShapeHashCombine(hash,
                                             static_cast<uint64_t>(static_cast<int64_t>(gpuStore.frontierRunningMin)));
    hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(gpuStore.frontierCapacity));
    hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(gpuStore.frontierCount));
    hash = simRegionSchedulerShapeHashCombine(hash,static_cast<uint64_t>(gpuStore.frontierStatesDevice));
  }
  return hash;
}

inline uint64_t simRegionSchedulerShapeScoreMatrixFingerprint(const SimKernelContext &context)
{
  uint64_t hash = 1469598103934665603ull;
  for(size_t row = 0; row < 128; ++row)
  {
    for(size_t col = 0; col < 128; ++col)
    {
      hash = simRegionSchedulerShapeHashCombine(
        hash,
        static_cast<uint64_t>(static_cast<int64_t>(context.scoreMatrix[row][col])));
    }
  }
  return hash;
}

struct SimRegionSchedulerShapeTelemetrySignature
{
  SimRegionSchedulerShapeTelemetrySignature():
    runningMin(0),
    safeStoreFingerprint(0),
    scoreMatrixFingerprint(0),
    cells(0)
  {
  }

  long runningMin;
  uint64_t safeStoreFingerprint;
  uint64_t scoreMatrixFingerprint;
  vector<uint64_t> filterStartCoords;
  uint64_t cells;
};

struct SimRegionSchedulerShapeTelemetryState
{
  SimRegionSchedulerShapeTelemetryState():
    hasPrevious(false),
    currentRunLength(0)
  {
  }

  bool hasPrevious;
  SimRegionSchedulerShapeTelemetrySignature previous;
  uint64_t currentRunLength;
};

inline std::mutex &simRegionSchedulerShapeTelemetryMutex()
{
  static std::mutex mutex;
  return mutex;
}

inline SimRegionSchedulerShapeTelemetryState &simRegionSchedulerShapeTelemetryState()
{
  static SimRegionSchedulerShapeTelemetryState state;
  return state;
}

inline void recordSimRegionSchedulerShapeTelemetryMax(std::atomic<uint64_t> &target,uint64_t candidate)
{
  uint64_t current = target.load(std::memory_order_relaxed);
  while(current < candidate &&
        !target.compare_exchange_weak(current,
                                      candidate,
                                      std::memory_order_relaxed,
                                      std::memory_order_relaxed))
  {
  }
}

inline void recordSimRegionSchedulerShapeTelemetry(const SimPathWorkset &workset,
                                                   const vector<uint64_t> &affectedStartCoords,
                                                   const SimKernelContext &context)
{
  const uint64_t callBands = static_cast<uint64_t>(workset.bands.size());
  const uint64_t callCells =
    workset.cellCount != 0 ? workset.cellCount : simPathWorksetCellCountFromBands(workset.bands);
  simRegionSchedulerShapeTelemetryCallCount().fetch_add(1,std::memory_order_relaxed);
  simRegionSchedulerShapeTelemetryBandCount().fetch_add(callBands,std::memory_order_relaxed);
  if(callBands == 1)
  {
    simRegionSchedulerShapeTelemetrySingleBandCallCount().fetch_add(1,std::memory_order_relaxed);
  }
  simRegionSchedulerShapeTelemetryAffectedStartCount().fetch_add(
    static_cast<uint64_t>(affectedStartCoords.size()),
    std::memory_order_relaxed);
  simRegionSchedulerShapeTelemetryCellCount().fetch_add(callCells,std::memory_order_relaxed);

  for(size_t bandIndex = 0; bandIndex < workset.bands.size(); ++bandIndex)
  {
    const SimUpdateBand &band = workset.bands[bandIndex];
    const uint64_t rowCount =
      band.rowEnd >= band.rowStart ? static_cast<uint64_t>(band.rowEnd - band.rowStart + 1) : 0;
    const uint64_t colCount =
      band.colEnd >= band.colStart ? static_cast<uint64_t>(band.colEnd - band.colStart + 1) : 0;
    recordSimRegionSchedulerShapeTelemetryMax(simRegionSchedulerShapeTelemetryMaxBandRows(),
                                              rowCount);
    recordSimRegionSchedulerShapeTelemetryMax(simRegionSchedulerShapeTelemetryMaxBandCols(),
                                              colCount);
  }

  SimRegionSchedulerShapeTelemetrySignature signature;
  signature.runningMin = context.runningMin;
  signature.safeStoreFingerprint = simRegionSchedulerShapeSafeStoreFingerprint(context);
  signature.scoreMatrixFingerprint = simRegionSchedulerShapeScoreMatrixFingerprint(context);
  signature.filterStartCoords = makeSortedUniqueSimStartCoords(affectedStartCoords);
  signature.cells = callCells;

  std::lock_guard<std::mutex> lock(simRegionSchedulerShapeTelemetryMutex());
  SimRegionSchedulerShapeTelemetryState &state = simRegionSchedulerShapeTelemetryState();
  if(state.hasPrevious)
  {
    const bool sameRunningMin = state.previous.runningMin == signature.runningMin;
    const bool sameSafeStore = state.previous.safeStoreFingerprint == signature.safeStoreFingerprint;
    const bool sameScoreMatrix =
      state.previous.scoreMatrixFingerprint == signature.scoreMatrixFingerprint;
    const bool sameFilter = state.previous.filterStartCoords == signature.filterStartCoords;
    if(sameRunningMin && sameSafeStore && sameScoreMatrix && sameFilter)
    {
      if(state.currentRunLength == 1)
      {
        simRegionSchedulerShapeTelemetryMergeableCallCount().fetch_add(1,
                                                                       std::memory_order_relaxed);
        simRegionSchedulerShapeTelemetryMergeableCellCount().fetch_add(state.previous.cells,
                                                                       std::memory_order_relaxed);
      }
      simRegionSchedulerShapeTelemetryMergeableCallCount().fetch_add(1,
                                                                     std::memory_order_relaxed);
      simRegionSchedulerShapeTelemetryMergeableCellCount().fetch_add(callCells,
                                                                     std::memory_order_relaxed);
      simRegionSchedulerShapeTelemetryEstimatedLaunchReductionCount().fetch_add(
        1,
        std::memory_order_relaxed);
      ++state.currentRunLength;
    }
    else
    {
      if(!sameRunningMin)
      {
        simRegionSchedulerShapeTelemetryRejectedRunningMinCount().fetch_add(
          1,
          std::memory_order_relaxed);
      }
      if(!sameSafeStore)
      {
        simRegionSchedulerShapeTelemetryRejectedSafeStoreEpochCount().fetch_add(
          1,
          std::memory_order_relaxed);
      }
      if(!sameScoreMatrix)
      {
        simRegionSchedulerShapeTelemetryRejectedScoreMatrixCount().fetch_add(
          1,
          std::memory_order_relaxed);
      }
      if(!sameFilter)
      {
        simRegionSchedulerShapeTelemetryRejectedFilterCount().fetch_add(
          1,
          std::memory_order_relaxed);
      }
      state.currentRunLength = 1;
    }
  }
  else
  {
    state.hasPrevious = true;
    state.currentRunLength = 1;
  }
  state.previous = signature;
}

inline void getSimRegionSchedulerShapeTelemetryStats(SimRegionSchedulerShapeTelemetryStats &stats)
{
  stats.calls = simRegionSchedulerShapeTelemetryCallCount().load(std::memory_order_relaxed);
  stats.bands = simRegionSchedulerShapeTelemetryBandCount().load(std::memory_order_relaxed);
  stats.singleBandCalls =
    simRegionSchedulerShapeTelemetrySingleBandCallCount().load(std::memory_order_relaxed);
  stats.affectedStarts =
    simRegionSchedulerShapeTelemetryAffectedStartCount().load(std::memory_order_relaxed);
  stats.cells = simRegionSchedulerShapeTelemetryCellCount().load(std::memory_order_relaxed);
  stats.maxBandRows = simRegionSchedulerShapeTelemetryMaxBandRows().load(std::memory_order_relaxed);
  stats.maxBandCols = simRegionSchedulerShapeTelemetryMaxBandCols().load(std::memory_order_relaxed);
  stats.mergeableCalls =
    simRegionSchedulerShapeTelemetryMergeableCallCount().load(std::memory_order_relaxed);
  stats.mergeableCells =
    simRegionSchedulerShapeTelemetryMergeableCellCount().load(std::memory_order_relaxed);
  stats.estimatedLaunchReduction =
    simRegionSchedulerShapeTelemetryEstimatedLaunchReductionCount().load(std::memory_order_relaxed);
  stats.rejectedRunningMin =
    simRegionSchedulerShapeTelemetryRejectedRunningMinCount().load(std::memory_order_relaxed);
  stats.rejectedSafeStoreEpoch =
    simRegionSchedulerShapeTelemetryRejectedSafeStoreEpochCount().load(std::memory_order_relaxed);
  stats.rejectedScoreMatrix =
    simRegionSchedulerShapeTelemetryRejectedScoreMatrixCount().load(std::memory_order_relaxed);
  stats.rejectedFilter =
    simRegionSchedulerShapeTelemetryRejectedFilterCount().load(std::memory_order_relaxed);
}

inline void rebuildSimCandidateStartIndex(SimKernelContext &context);
inline long findSimCandidateIndex(const SimCandidateStartIndex &index,long startI,long startJ);
inline void eraseSimSafeCandidateStateStoreSortedUniqueStartCoords(const vector<uint64_t> &uniqueCoords,
                                                                   SimKernelContext &context);
inline void applySimCudaReducedCandidates(const vector<SimScanCudaCandidateState> &candidateStates,
                                          int runningMin,
                                          SimKernelContext &context);
inline void applySimCudaInitialReduceResults(const vector<SimScanCudaCandidateState> &candidateStates,
                                             int runningMin,
                                             const vector<SimScanCudaCandidateState> &allCandidateStates,
                                             SimCudaPersistentSafeStoreHandle &persistentSafeStoreHandle,
                                             uint64_t logicalEventCount,
                                             SimKernelContext &context,
                                             bool benchmarkEnabled,
                                             bool proposalCandidates);
inline void runSimCudaInitialOrderedSegmentedV3ShadowIfEnabled(
  const vector<SimScanCudaInitialRunSummary> &summaries,
  const vector<SimScanCudaCandidateState> &candidateStates,
  int runningMin,
  const vector<SimScanCudaCandidateState> &allCandidateStates);
inline void invalidateSimSafeCandidateStateStore(SimKernelContext &context);
inline void mergeSimCudaInitialRunSummariesIntoSafeStore(const vector<SimScanCudaInitialRunSummary> &summaries,
                                                         SimKernelContext &context);
inline void pruneSimSafeCandidateStateStore(SimKernelContext &context);
inline void eraseSimSafeCandidateStateStoreStartCoords(const vector<uint64_t> &startCoords,
                                                       SimKernelContext &context);
inline void eraseSimCandidatesByStartCoords(const vector<uint64_t> &startCoords,
                                            SimKernelContext &context);
inline void mergeSimCudaCandidateStatesIntoContext(const vector<SimScanCudaCandidateState> &states,
                                                   SimKernelContext &context);
inline bool simCanUseGpuFrontierCacheForResidency(const SimKernelContext &context);
inline void collectSimSafeCandidateStateStoreIntersectingStartCoords(const SimCandidateStateStore &store,
                                                                     const vector<SimUpdateBand> &bands,
                                                                     vector<uint64_t> &outStartCoords);
inline bool collectSimCudaPersistentSafeCandidateStartCoordsIntersectingBands(long queryLength,
                                                                              long targetLength,
                                                                              const SimCudaPersistentSafeStoreHandle &handle,
                                                                              const vector<SimUpdateBand> &bands,
                                                                              vector<uint64_t> &outStartCoords,
                                                                              string *errorOut = NULL);
inline bool collectSimCudaPersistentSafeCandidateStatesIntersectingBands(long queryLength,
                                                                         long targetLength,
                                                                         const SimCudaPersistentSafeStoreHandle &handle,
                                                                         const vector<SimUpdateBand> &bands,
                                                                         vector<SimScanCudaCandidateState> &outStates,
                                                                         string *errorOut = NULL);
inline bool applySimLocatedUpdateRegionWithSafeStoreRefresh(const char *A,
                                                            const char *B,
                                                            const SimLocateResult &locateResult,
                                                            SimKernelContext &context);

inline long simCurrentCandidateFloor(const SimKernelContext &context)
{
  if(context.candidateCount <= 0)
  {
    return 0;
  }
  long minScore = context.candidates[0].SCORE;
  for(long i = 1; i < context.candidateCount; ++i)
  {
    if(context.candidates[i].SCORE < minScore)
    {
      minScore = context.candidates[i].SCORE;
    }
  }
  return minScore;
}

inline long refreshSimRunningMin(SimKernelContext &context)
{
  context.runningMin = simCurrentCandidateFloor(context);
  return context.runningMin;
}

inline SimScanCudaCandidateState makeSimScanCudaCandidateState(const SimCandidate &candidate)
{
  SimScanCudaCandidateState state;
  state.score = static_cast<int>(candidate.SCORE);
  state.startI = static_cast<int>(candidate.STARI);
  state.startJ = static_cast<int>(candidate.STARJ);
  state.endI = static_cast<int>(candidate.ENDI);
  state.endJ = static_cast<int>(candidate.ENDJ);
  state.top = static_cast<int>(candidate.TOP);
  state.bot = static_cast<int>(candidate.BOT);
  state.left = static_cast<int>(candidate.LEFT);
  state.right = static_cast<int>(candidate.RIGHT);
  return state;
}

inline SimCandidate makeSimCandidateFromCudaState(const SimScanCudaCandidateState &state)
{
  SimCandidate candidate;
  candidate.SCORE = static_cast<long>(state.score);
  candidate.STARI = static_cast<long>(state.startI);
  candidate.STARJ = static_cast<long>(state.startJ);
  candidate.ENDI = static_cast<long>(state.endI);
  candidate.ENDJ = static_cast<long>(state.endJ);
  candidate.TOP = static_cast<long>(state.top);
  candidate.BOT = static_cast<long>(state.bot);
  candidate.LEFT = static_cast<long>(state.left);
  candidate.RIGHT = static_cast<long>(state.right);
  return candidate;
}

inline void collectSimContextCandidateStates(const SimKernelContext &context,
                                             vector<SimScanCudaCandidateState> &outCandidateStates)
{
  outCandidateStates.clear();
  if(context.candidateCount <= 0)
  {
    return;
  }
  outCandidateStates.reserve(static_cast<size_t>(context.candidateCount));
  for(long candidateIndex = 0; candidateIndex < context.candidateCount; ++candidateIndex)
  {
    outCandidateStates.push_back(makeSimScanCudaCandidateState(context.candidates[candidateIndex]));
  }
}

inline void mergeSimScanCudaCandidateState(const SimScanCudaCandidateState &source,
                                           SimScanCudaCandidateState &target)
{
  if(target.score < source.score)
  {
    target.score = source.score;
    target.endI = source.endI;
    target.endJ = source.endJ;
  }
  if(target.top > source.top) target.top = source.top;
  if(target.bot < source.bot) target.bot = source.bot;
  if(target.left > source.left) target.left = source.left;
  if(target.right < source.right) target.right = source.right;
}

inline void resetSimCandidateStateStore(SimCandidateStateStore &store,bool valid)
{
  store.valid = valid;
  store.states.clear();
  store.startCoordToIndex.clear();
}

inline void upsertSimCandidateStateStoreState(const SimScanCudaCandidateState &state,
                                              SimCandidateStateStore &store)
{
  const uint64_t startCoord = simScanCudaCandidateStateStartCoord(state);
  unordered_map<uint64_t,size_t>::iterator found = store.startCoordToIndex.find(startCoord);
  if(found == store.startCoordToIndex.end())
  {
    store.startCoordToIndex[startCoord] = store.states.size();
    store.states.push_back(state);
    return;
  }
  mergeSimScanCudaCandidateState(state,store.states[found->second]);
}

inline void upsertSimCandidateStateStoreSummary(const SimScanCudaInitialRunSummary &summary,
                                                SimCandidateStateStore &store)
{
  unordered_map<uint64_t,size_t>::iterator found = store.startCoordToIndex.find(summary.startCoord);
  if(found == store.startCoordToIndex.end())
  {
    SimScanCudaCandidateState state;
    initSimScanCudaCandidateStateFromInitialRunSummary(summary,state);
    store.startCoordToIndex[summary.startCoord] = store.states.size();
    store.states.push_back(state);
    return;
  }
  updateSimScanCudaCandidateStateFromInitialRunSummary(summary,store.states[found->second]);
}

inline void rebuildSimCandidateStateStoreIndex(SimCandidateStateStore &store)
{
  store.startCoordToIndex.clear();
  for(size_t stateIndex = 0; stateIndex < store.states.size(); ++stateIndex)
  {
    store.startCoordToIndex[simScanCudaCandidateStateStartCoord(store.states[stateIndex])] = stateIndex;
  }
}

inline void clearSimSafeCandidateStores(SimKernelContext &context)
{
  resetSimCandidateStateStore(context.safeCandidateStateStore,false);
  releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
  context.gpuFrontierCacheInSync = false;
  context.initialSafeStoreHandoffActive = false;
}

inline void invalidateSimSafeCandidateStateStore(SimKernelContext &context)
{
  clearSimSafeCandidateStores(context);
  context.proposalCandidateLoop = false;
}

inline void markSimGpuFrontierCacheSynchronized(SimKernelContext &context)
{
  context.gpuFrontierCacheInSync =
    context.gpuSafeCandidateStateStore.valid &&
    context.gpuSafeCandidateStateStore.frontierValid;
}

inline bool simCanUseGpuFrontierCacheForResidency(const SimKernelContext &context)
{
  return context.gpuFrontierCacheInSync &&
         context.gpuSafeCandidateStateStore.valid &&
         context.gpuSafeCandidateStateStore.frontierValid;
}

inline bool simInvalidateInitialSafeStoreHandoffIfStaleForLocate(SimKernelContext &context)
{
  if(!context.initialSafeStoreHandoffActive ||
     !context.gpuSafeCandidateStateStore.valid ||
     simCanUseGpuFrontierCacheForResidency(context))
  {
    return false;
  }
  releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
  context.gpuFrontierCacheInSync = false;
  context.initialSafeStoreHandoffActive = false;
  recordSimInitialSafeStoreHandoffRejectedStaleEpoch();
  recordSimFrontierCacheInvalidateReleaseOrError();
  return true;
}

inline void rebuildSimCandidateStructures(SimKernelContext &context)
{
  rebuildSimCandidateStartIndex(context);
  context.candidateMinHeap.valid = false;
  refreshSimRunningMin(context);
}

inline bool simContextContainsCandidateStartCoord(const SimKernelContext &context,uint64_t startCoord)
{
  const long startI = static_cast<long>(static_cast<uint32_t>(startCoord >> 32));
  const long startJ = static_cast<long>(static_cast<uint32_t>(startCoord));
  return findSimCandidateIndex(context.candidateStartIndex,startI,startJ) >= 0;
}

inline size_t simCandidateIndexHash(long startI,long startJ)
{
  const uint64_t i = static_cast<uint64_t>(startI);
  const uint64_t j = static_cast<uint64_t>(startJ);
  return static_cast<size_t>(((i * 11400714819323198485ull) ^ (j + 0x9e3779b97f4a7c15ull + (i << 6) + (i >> 2))) & (SIM_CANDIDATE_INDEX_CAPACITY - 1));
}

inline void clearSimCandidateStartIndex(SimCandidateStartIndex &index)
{
  index.clear();
}

inline long findSimCandidateIndex(const SimCandidateStartIndex &index,long startI,long startJ)
{
  size_t slot = simCandidateIndexHash(startI,startJ);
  for(size_t probe = 0; probe < SIM_CANDIDATE_INDEX_CAPACITY; ++probe)
  {
    if(index.slotState[slot] == 0)
    {
      return -1;
    }
    if(index.slotState[slot] == 1 && index.startI[slot] == startI && index.startJ[slot] == startJ)
    {
      return index.candidateIndex[slot];
    }
    slot = (slot + 1) & (SIM_CANDIDATE_INDEX_CAPACITY - 1);
  }
  return -1;
}

inline long findSimCandidateIndexStats(const SimCandidateStartIndex &index,long startI,long startJ,SimCandidateStats &stats)
{
  size_t slot = simCandidateIndexHash(startI,startJ);
  uint64_t probes = 0;
  for(size_t probe = 0; probe < SIM_CANDIDATE_INDEX_CAPACITY; ++probe)
  {
    ++probes;
    if(index.slotState[slot] == 0)
    {
      stats.hashProbesTotal += probes;
      if(probes > stats.hashProbesMax) stats.hashProbesMax = probes;
      return -1;
    }
    if(index.slotState[slot] == 1 && index.startI[slot] == startI && index.startJ[slot] == startJ)
    {
      stats.hashProbesTotal += probes;
      if(probes > stats.hashProbesMax) stats.hashProbesMax = probes;
      return index.candidateIndex[slot];
    }
    slot = (slot + 1) & (SIM_CANDIDATE_INDEX_CAPACITY - 1);
  }
  stats.hashProbesTotal += probes;
  if(probes > stats.hashProbesMax) stats.hashProbesMax = probes;
  return -1;
}

inline void insertSimCandidateIndexEntry(SimCandidateStartIndex &index,long startI,long startJ,long candidateIndex)
{
  size_t slot = simCandidateIndexHash(startI,startJ);
  size_t firstTombstone = SIM_CANDIDATE_INDEX_CAPACITY;
  while(index.slotState[slot] != 0)
  {
    if(index.slotState[slot] == 2 && firstTombstone == SIM_CANDIDATE_INDEX_CAPACITY)
    {
      firstTombstone = slot;
    }
    slot = (slot + 1) & (SIM_CANDIDATE_INDEX_CAPACITY - 1);
  }
  if(firstTombstone != SIM_CANDIDATE_INDEX_CAPACITY)
  {
    slot = firstTombstone;
    --index.tombstoneCount;
  }
  index.slotState[slot] = 1;
  index.startI[slot] = startI;
  index.startJ[slot] = startJ;
  index.candidateIndex[slot] = static_cast<int>(candidateIndex);
  index.candidateSlot[candidateIndex] = static_cast<int>(slot);
}

inline void eraseSimCandidateIndexEntry(SimCandidateStartIndex &index,long candidateIndex)
{
  if(candidateIndex < 0 || candidateIndex >= K)
  {
    return;
  }
  const int slot = index.candidateSlot[candidateIndex];
  if(slot < 0)
  {
    return;
  }
  index.slotState[static_cast<size_t>(slot)] = 2;
  index.candidateSlot[candidateIndex] = -1;
  ++index.tombstoneCount;
}

inline void remapSimCandidateIndexEntry(SimCandidateStartIndex &index,long oldCandidateIndex,long newCandidateIndex)
{
  if(oldCandidateIndex == newCandidateIndex)
  {
    return;
  }
  const int slot = (oldCandidateIndex >= 0 && oldCandidateIndex < K) ? index.candidateSlot[oldCandidateIndex] : -1;
  if(slot < 0)
  {
    return;
  }
  index.candidateIndex[static_cast<size_t>(slot)] = static_cast<int>(newCandidateIndex);
  index.candidateSlot[newCandidateIndex] = slot;
  index.candidateSlot[oldCandidateIndex] = -1;
}

inline void rebuildSimCandidateStartIndex(SimKernelContext &context)
{
  SimCandidateStartIndex &index = context.candidateStartIndex;
  clearSimCandidateStartIndex(index);
  for(long candidateIndex = 0; candidateIndex < context.candidateCount; ++candidateIndex)
  {
    insertSimCandidateIndexEntry(index,
                                 context.candidates[candidateIndex].STARI,
                                 context.candidates[candidateIndex].STARJ,
                                 candidateIndex);
  }
}

inline void pruneSimSafeCandidateStateStore(SimKernelContext &context)
{
  SimCandidateStateStore &store = context.safeCandidateStateStore;
  if(!store.valid)
  {
    return;
  }

  const long floor = context.runningMin;
  vector<SimScanCudaCandidateState> keptStates;
  keptStates.reserve(store.states.size());
  for(size_t stateIndex = 0; stateIndex < store.states.size(); ++stateIndex)
  {
    const SimScanCudaCandidateState &state = store.states[stateIndex];
    const uint64_t startCoord = simScanCudaCandidateStateStartCoord(state);
    bool keepState = state.score > floor;
    if(!keepState)
    {
      keepState = simContextContainsCandidateStartCoord(context,startCoord);
    }
    if(keepState)
    {
      keptStates.push_back(state);
    }
  }
  store.states.swap(keptStates);
  rebuildSimCandidateStateStoreIndex(store);
}

inline bool updateSimCudaPersistentSafeCandidateStateStore(const vector<SimScanCudaCandidateState> &updatedStates,
                                                           const SimKernelContext &context,
                                                           SimCudaPersistentSafeStoreHandle &handle,
                                                           string *errorOut = NULL)
{
  vector<SimScanCudaCandidateState> finalCandidateStates;
  collectSimContextCandidateStates(context,finalCandidateStates);
  const bool updated = sim_scan_cuda_update_persistent_safe_candidate_state_store(updatedStates,
                                                                                  finalCandidateStates,
                                                                                  static_cast<int>(context.runningMin),
                                                                                  &handle,
                                                                                  errorOut);
  if(updated)
  {
    recordSimFrontierCacheRebuildFromHostFinalCandidates();
  }
  return updated;
}

inline void collectSimContextCandidateStatesBySortedUniqueStartCoords(const SimKernelContext &context,
                                                                      const vector<uint64_t> &uniqueCoords,
                                                                      vector<SimScanCudaCandidateState> &outCandidateStates)
{
  outCandidateStates.clear();
  if(uniqueCoords.empty() || context.candidateCount <= 0)
  {
    return;
  }
  vector<SimScanCudaCandidateState> allCandidateStates;
  collectSimContextCandidateStates(context,allCandidateStates);
  outCandidateStates.reserve(allCandidateStates.size());
  for(size_t stateIndex = 0; stateIndex < allCandidateStates.size(); ++stateIndex)
  {
    const uint64_t startCoord = simScanCudaCandidateStateStartCoord(allCandidateStates[stateIndex]);
    if(binary_search(uniqueCoords.begin(),uniqueCoords.end(),startCoord))
    {
      outCandidateStates.push_back(allCandidateStates[stateIndex]);
    }
  }
}

inline bool simCandidateStateIntersectsBand(const SimScanCudaCandidateState &state,
                                            const SimUpdateBand &band)
{
  return static_cast<long>(state.bot) >= band.rowStart &&
         static_cast<long>(state.top) <= band.rowEnd &&
         static_cast<long>(state.right) >= band.colStart &&
         static_cast<long>(state.left) <= band.colEnd;
}

inline void collectSimSafeCandidateStateStoreIntersectingStartCoords(const SimCandidateStateStore &store,
                                                                     const vector<SimUpdateBand> &bands,
                                                                     vector<uint64_t> &outStartCoords)
{
  outStartCoords.clear();
  if(!store.valid || store.states.empty() || bands.empty())
  {
    return;
  }

  outStartCoords.reserve(store.states.size());
  for(size_t stateIndex = 0; stateIndex < store.states.size(); ++stateIndex)
  {
    const SimScanCudaCandidateState &state = store.states[stateIndex];
    bool intersects = false;
    for(size_t bandIndex = 0; bandIndex < bands.size(); ++bandIndex)
    {
      if(simCandidateStateIntersectsBand(state,bands[bandIndex]))
      {
        intersects = true;
        break;
      }
    }
    if(intersects)
    {
      outStartCoords.push_back(simScanCudaCandidateStateStartCoord(state));
    }
  }
}

inline bool buildSimCudaPersistentSafeStoreRowIntervalsForBands(long queryLength,
                                                                long targetLength,
                                                                const vector<SimUpdateBand> &bands,
                                                                vector<int> &rowOffsets,
                                                                vector<SimScanCudaColumnInterval> &flattenedIntervals,
                                                                string *errorOut = NULL)
{
  rowOffsets.clear();
  flattenedIntervals.clear();
  if(queryLength <= 0 || targetLength <= 0 || bands.empty())
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }
  if(queryLength > static_cast<long>(numeric_limits<int>::max()) ||
     targetLength > static_cast<long>(numeric_limits<int>::max()))
  {
    if(errorOut != NULL)
    {
      *errorOut = "SIM safe-store band export dimensions exceed CUDA helper range";
    }
    return false;
  }

  vector< vector< pair<long,long> > > rowIntervals(static_cast<size_t>(queryLength + 1));
  for(size_t bandIndex = 0; bandIndex < bands.size(); ++bandIndex)
  {
    const SimUpdateBand &band = bands[bandIndex];
    if(band.rowStart < 1 ||
       band.colStart < 1 ||
       band.rowEnd < band.rowStart ||
       band.colEnd < band.colStart ||
       band.rowEnd > queryLength ||
       band.colEnd > targetLength)
    {
      if(errorOut != NULL)
      {
        *errorOut = "SIM safe-store band export received invalid band";
      }
      return false;
    }
    for(long row = band.rowStart; row <= band.rowEnd; ++row)
    {
      insertSimSafeWorksetInterval(rowIntervals[static_cast<size_t>(row)],
                                   band.colStart,
                                   band.colEnd);
    }
  }

  rowOffsets.assign(static_cast<size_t>(queryLength + 2),0);
  for(long row = 1; row <= queryLength; ++row)
  {
    rowOffsets[static_cast<size_t>(row)] = static_cast<int>(flattenedIntervals.size());
    const vector< pair<long,long> > &intervals = rowIntervals[static_cast<size_t>(row)];
    for(size_t intervalIndex = 0; intervalIndex < intervals.size(); ++intervalIndex)
    {
      flattenedIntervals.push_back(SimScanCudaColumnInterval(static_cast<int>(intervals[intervalIndex].first),
                                                             static_cast<int>(intervals[intervalIndex].second)));
    }
  }
  rowOffsets[static_cast<size_t>(queryLength + 1)] = static_cast<int>(flattenedIntervals.size());
  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
}

inline bool collectSimCudaPersistentSafeCandidateStartCoordsIntersectingBands(long queryLength,
                                                                              long targetLength,
                                                                              const SimCudaPersistentSafeStoreHandle &handle,
                                                                              const vector<SimUpdateBand> &bands,
                                                                              vector<uint64_t> &outStartCoords,
                                                                              string *errorOut)
{
  outStartCoords.clear();
  if(queryLength <= 0 || targetLength <= 0 || bands.empty())
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }
  if(!handle.valid)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid GPU safe-store handle";
    }
    return false;
  }

  vector<int> rowOffsets;
  vector<SimScanCudaColumnInterval> flattenedIntervals;
  if(!buildSimCudaPersistentSafeStoreRowIntervalsForBands(queryLength,
                                                          targetLength,
                                                          bands,
                                                          rowOffsets,
                                                          flattenedIntervals,
                                                          errorOut))
  {
    return false;
  }
  if(flattenedIntervals.empty())
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }
  return sim_scan_cuda_filter_persistent_safe_candidate_state_store_start_coords_by_row_intervals(handle,
                                                                                                  static_cast<int>(queryLength),
                                                                                                  static_cast<int>(targetLength),
                                                                                                  rowOffsets,
                                                                                                  flattenedIntervals,
                                                                                                  &outStartCoords,
                                                                                                  errorOut);
}

inline bool collectSimCudaPersistentSafeCandidateStatesIntersectingBands(long queryLength,
                                                                         long targetLength,
                                                                         const SimCudaPersistentSafeStoreHandle &handle,
                                                                         const vector<SimUpdateBand> &bands,
                                                                         vector<SimScanCudaCandidateState> &outStates,
                                                                         string *errorOut)
{
  outStates.clear();
  if(queryLength <= 0 || targetLength <= 0 || bands.empty())
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }
  if(!handle.valid)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid GPU safe-store handle";
    }
    return false;
  }
  vector<int> rowOffsets;
  vector<SimScanCudaColumnInterval> flattenedIntervals;
  if(!buildSimCudaPersistentSafeStoreRowIntervalsForBands(queryLength,
                                                          targetLength,
                                                          bands,
                                                          rowOffsets,
                                                          flattenedIntervals,
                                                          errorOut))
  {
    return false;
  }
  if(flattenedIntervals.empty())
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }

  if(!sim_scan_cuda_filter_persistent_safe_candidate_state_store_by_row_intervals(handle,
                                                                                  static_cast<int>(queryLength),
                                                                                  static_cast<int>(targetLength),
                                                                                  rowOffsets,
                                                                                  flattenedIntervals,
                                                                                  &outStates,
                                                                                  errorOut))
  {
    return false;
  }
  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
}

inline bool applySimUpdateBandsCpuExactOnly(const char *A,
                                            const char *B,
                                            const vector<SimUpdateBand> &bands,
                                            SimKernelContext &context,
                                            bool recordTelemetry = true);

inline bool applySimSafeWindowUpdate(const char *A,
                                     const char *B,
                                     const SimPathWorkset &workset,
                                     const vector<uint64_t> &affectedStartCoords,
                                     SimKernelContext &context,
                                     bool recordTelemetry = true,
                                     SimSafeWorksetFallbackReason *fallbackReason = NULL);

inline void eraseSimSafeCandidateStateStoreSortedUniqueStartCoords(const vector<uint64_t> &uniqueCoords,
                                                                   SimKernelContext &context)
{
  SimCandidateStateStore &store = context.safeCandidateStateStore;
  if(!store.valid || uniqueCoords.empty())
  {
    return;
  }

  vector<SimScanCudaCandidateState> keptStates;
  keptStates.reserve(store.states.size());
  for(size_t stateIndex = 0; stateIndex < store.states.size(); ++stateIndex)
  {
    const uint64_t startCoord = simScanCudaCandidateStateStartCoord(store.states[stateIndex]);
    if(!binary_search(uniqueCoords.begin(),uniqueCoords.end(),startCoord))
    {
      keptStates.push_back(store.states[stateIndex]);
    }
  }
  store.states.swap(keptStates);
  rebuildSimCandidateStateStoreIndex(store);
}

inline void eraseSimSafeCandidateStateStoreStartCoords(const vector<uint64_t> &startCoords,
                                                       SimKernelContext &context)
{
  eraseSimSafeCandidateStateStoreSortedUniqueStartCoords(makeSortedUniqueSimStartCoords(startCoords),context);
}

inline void eraseSimCandidatesBySortedUniqueStartCoords(const vector<uint64_t> &uniqueCoords,
                                                        SimKernelContext &context)
{
  if(uniqueCoords.empty() || context.candidateCount <= 0)
  {
    return;
  }
  context.gpuFrontierCacheInSync = false;

  SimCandidateStartIndex &index = context.candidateStartIndex;
  for(size_t coordIndex = 0; coordIndex < uniqueCoords.size(); ++coordIndex)
  {
    if(context.candidateCount <= 0)
    {
      break;
    }
    const long startI = static_cast<long>(static_cast<uint32_t>(uniqueCoords[coordIndex] >> 32));
    const long startJ = static_cast<long>(static_cast<uint32_t>(uniqueCoords[coordIndex]));
    const long foundIndex = findSimCandidateIndex(index,startI,startJ);
    if(foundIndex < 0 || foundIndex >= context.candidateCount)
    {
      continue;
    }
    eraseSimCandidateIndexEntry(index,foundIndex);
    const long lastIndex = --context.candidateCount;
    if(foundIndex != lastIndex)
    {
      context.candidates[foundIndex] = context.candidates[lastIndex];
      remapSimCandidateIndexEntry(index,lastIndex,foundIndex);
    }
  }
  if(index.tombstoneCount > static_cast<size_t>(K))
  {
    rebuildSimCandidateStartIndex(context);
  }
  context.candidateMinHeap.valid = false;
  refreshSimRunningMin(context);
}

inline void eraseSimCandidatesByStartCoords(const vector<uint64_t> &startCoords,
                                            SimKernelContext &context)
{
  eraseSimCandidatesBySortedUniqueStartCoords(makeSortedUniqueSimStartCoords(startCoords),context);
}

inline bool simCandidateHeapLess(const SimCandidate *candidates,int leftCandidateIndex,int rightCandidateIndex)
{
  const long leftScore = candidates[leftCandidateIndex].SCORE;
  const long rightScore = candidates[rightCandidateIndex].SCORE;
  if(leftScore != rightScore)
  {
    return leftScore < rightScore;
  }
  return leftCandidateIndex < rightCandidateIndex;
}

inline void simCandidateHeapSwap(SimCandidateMinHeap &heap,int leftPos,int rightPos)
{
  const int leftIndex = heap.heap[leftPos];
  const int rightIndex = heap.heap[rightPos];
  heap.heap[leftPos] = rightIndex;
  heap.heap[rightPos] = leftIndex;
  if(rightIndex >= 0 && rightIndex < K) heap.pos[rightIndex] = leftPos;
  if(leftIndex >= 0 && leftIndex < K) heap.pos[leftIndex] = rightPos;
}

inline void simCandidateHeapSiftDown(SimCandidateMinHeap &heap,const SimCandidate *candidates,int startPos)
{
  int pos = startPos;
  while(true)
  {
    const int left = pos * 2 + 1;
    if(left >= heap.size)
    {
      return;
    }
    int best = left;
    const int right = left + 1;
    if(right < heap.size &&
       simCandidateHeapLess(candidates, heap.heap[right], heap.heap[left]))
    {
      best = right;
    }
    if(!simCandidateHeapLess(candidates, heap.heap[best], heap.heap[pos]))
    {
      return;
    }
    simCandidateHeapSwap(heap, pos, best);
    pos = best;
  }
}

inline void simCandidateHeapSiftUp(SimCandidateMinHeap &heap,const SimCandidate *candidates,int startPos)
{
  int pos = startPos;
  while(pos > 0)
  {
    const int parent = (pos - 1) / 2;
    if(!simCandidateHeapLess(candidates, heap.heap[pos], heap.heap[parent]))
    {
      return;
    }
    simCandidateHeapSwap(heap, pos, parent);
    pos = parent;
  }
}

inline void buildSimCandidateMinHeap(SimKernelContext &context)
{
  SimCandidateMinHeap &heap = context.candidateMinHeap;
  heap.clear();
  if(context.candidateCount <= 0)
  {
    return;
  }
  heap.size = static_cast<int>(context.candidateCount);
  for(int i = 0; i < heap.size; ++i)
  {
    heap.heap[i] = i;
    heap.pos[i] = i;
  }
  for(int i = heap.size / 2 - 1; i >= 0; --i)
  {
    simCandidateHeapSiftDown(heap, context.candidates, i);
  }
  heap.valid = (context.candidateCount == K);
}

inline void updateSimCandidateMinHeapIndex(SimKernelContext &context,int candidateIndex)
{
  SimCandidateMinHeap &heap = context.candidateMinHeap;
  if(!heap.valid || candidateIndex < 0 || candidateIndex >= K)
  {
    return;
  }
  const int currentPos = heap.pos[candidateIndex];
  if(currentPos < 0 || currentPos >= heap.size)
  {
    return;
  }
  simCandidateHeapSiftUp(heap, context.candidates, currentPos);
  simCandidateHeapSiftDown(heap, context.candidates, heap.pos[candidateIndex]);
}

	inline int peekMinSimCandidateIndex(const SimCandidateMinHeap &heap)
	{
	  return (heap.valid && heap.size > 0) ? heap.heap[0] : -1;
	}

	inline int ensureSimCandidateIndexForRun(SimKernelContext &context,
	                                         long startI,
	                                         long startJ,
	                                         long score,
	                                         long endI,
	                                         long endJ)
	{
	  SimCandidateStartIndex &index = context.candidateStartIndex;
	  SimCandidateStats *stats = context.statsEnabled ? &context.stats : NULL;
	  long foundIndex = stats ? findSimCandidateIndexStats(index,startI,startJ,*stats) : findSimCandidateIndex(index,startI,startJ);
	  if(foundIndex >= 0 && foundIndex < context.candidateCount)
	  {
	    if(stats) ++stats->indexHits;
	    return static_cast<int>(foundIndex);
	  }
	  if(stats) ++stats->indexMisses;

	  int slotIndex = 0;
	  if(context.candidateCount == K)
	  {
	    if(stats) ++stats->fullEvictions;
	    if(!context.candidateMinHeap.valid)
	    {
	      buildSimCandidateMinHeap(context);
	      if(stats) ++stats->heapBuilds;
	    }
	    slotIndex = peekMinSimCandidateIndex(context.candidateMinHeap);
	    if(slotIndex < 0 || slotIndex >= static_cast<int>(context.candidateCount))
	    {
	      slotIndex = 0;
	    }
	    eraseSimCandidateIndexEntry(index,slotIndex);
	  }
	  else
	  {
	    slotIndex = static_cast<int>(context.candidateCount++);
	  }

	  SimCandidate &candidate = context.candidates[slotIndex];
	  candidate.SCORE = score;
	  candidate.STARI = startI;
	  candidate.STARJ = startJ;
	  candidate.ENDI = endI;
	  candidate.ENDJ = endJ;
	  candidate.TOP = candidate.BOT = endI;
	  candidate.LEFT = candidate.RIGHT = endJ;
	  insertSimCandidateIndexEntry(index,startI,startJ,slotIndex);
	  if(context.candidateCount == K)
	  {
	    if(!context.candidateMinHeap.valid)
	    {
	      buildSimCandidateMinHeap(context);
	      if(stats) ++stats->heapBuilds;
	    }
	    updateSimCandidateMinHeapIndex(context, slotIndex);
	    if(stats) ++stats->heapUpdates;
	  }
	  if(index.tombstoneCount > static_cast<size_t>(K))
	  {
	    rebuildSimCandidateStartIndex(context);
	  }
	  return slotIndex;
	}

inline void applySimCudaCandidateState(const SimScanCudaCandidateState &state,
                                       SimKernelContext &context,
                                       SimCandidateStats *stats = NULL)
{
  if(stats) ++stats->addnodeCalls;
  const int candidateIndex = ensureSimCandidateIndexForRun(context,
                                                           static_cast<long>(state.startI),
                                                           static_cast<long>(state.startJ),
                                                           static_cast<long>(state.score),
                                                           static_cast<long>(state.endI),
                                                           static_cast<long>(state.endJ));
  SimCandidate &candidate = context.candidates[candidateIndex];
  if(candidate.SCORE < static_cast<long>(state.score))
  {
    candidate.SCORE = static_cast<long>(state.score);
    candidate.ENDI = static_cast<long>(state.endI);
    candidate.ENDJ = static_cast<long>(state.endJ);
    if(context.candidateCount == K && context.candidateMinHeap.valid)
    {
      updateSimCandidateMinHeapIndex(context,candidateIndex);
      if(stats) ++stats->heapUpdates;
    }
  }
  if(candidate.TOP > static_cast<long>(state.top)) candidate.TOP = static_cast<long>(state.top);
  if(candidate.BOT < static_cast<long>(state.bot)) candidate.BOT = static_cast<long>(state.bot);
  if(candidate.LEFT > static_cast<long>(state.left)) candidate.LEFT = static_cast<long>(state.left);
  if(candidate.RIGHT < static_cast<long>(state.right)) candidate.RIGHT = static_cast<long>(state.right);
}

	inline long addnodeIndexed(long c,long ci,long cj,long i,long j,SimKernelContext &context)
	{
	  SimCandidateStartIndex &index = context.candidateStartIndex;
	  SimCandidateStats *stats = context.statsEnabled ? &context.stats : NULL;
	  if(stats) ++stats->addnodeCalls;
  long foundIndex = stats ? findSimCandidateIndexStats(index,ci,cj,*stats) : findSimCandidateIndex(index,ci,cj);
  long most = 0;
  long low = 0;

  if(foundIndex >= 0 && foundIndex < context.candidateCount)
  {
    if(stats) ++stats->indexHits;
    SimCandidate &candidate = context.candidates[foundIndex];
    if(candidate.SCORE < c)
    {
      candidate.SCORE = c;
      candidate.ENDI = i;
      candidate.ENDJ = j;
      if(context.candidateCount == K && context.candidateMinHeap.valid)
      {
        updateSimCandidateMinHeapIndex(context, static_cast<int>(foundIndex));
        if(stats) ++stats->heapUpdates;
      }
    }
    if(candidate.TOP > i) candidate.TOP = i;
    if(candidate.BOT < i) candidate.BOT = i;
    if(candidate.LEFT > j) candidate.LEFT = j;
    if(candidate.RIGHT < j) candidate.RIGHT = j;
    return refreshSimRunningMin(context);
  }
  if(stats) ++stats->indexMisses;

  if(context.candidateCount == K)
  {
    if(stats) ++stats->fullEvictions;
    if(!context.candidateMinHeap.valid)
    {
      buildSimCandidateMinHeap(context);
      if(stats) ++stats->heapBuilds;
    }
    most = peekMinSimCandidateIndex(context.candidateMinHeap);
    if(most < 0 || most >= context.candidateCount)
    {
      most = low;
    }
    eraseSimCandidateIndexEntry(index,most);
  }
  else
  {
    most = context.candidateCount++;
  }

  context.candidates[most].SCORE = c;
  context.candidates[most].STARI = ci;
  context.candidates[most].STARJ = cj;
  context.candidates[most].ENDI = i;
  context.candidates[most].ENDJ = j;
  context.candidates[most].TOP = context.candidates[most].BOT = i;
  context.candidates[most].LEFT = context.candidates[most].RIGHT = j;
  insertSimCandidateIndexEntry(index,ci,cj,most);
  if(context.candidateCount == K)
  {
    if(!context.candidateMinHeap.valid)
    {
      buildSimCandidateMinHeap(context);
      if(stats) ++stats->heapBuilds;
    }
    updateSimCandidateMinHeapIndex(context, static_cast<int>(most));
    if(stats) ++stats->heapUpdates;
  }
  if(index.tombstoneCount > static_cast<size_t>(K))
  {
    rebuildSimCandidateStartIndex(context);
  }
  return refreshSimRunningMin(context);
}

inline bool simDiagonalAvailable(const SimWorkspace &workspace,long rowIndex,long columnIndex)
{
  const vector<uint64_t> &blockedRow = workspace.blocked[static_cast<size_t>(rowIndex)];
  if(blockedRow.empty())
  {
    return true;
  }

  const size_t wordIndex = static_cast<size_t>(columnIndex) >> 6;
  const uint64_t mask = static_cast<uint64_t>(1) << (static_cast<size_t>(columnIndex) & 63);
  return (blockedRow[wordIndex] & mask) == 0;
}

inline bool simBlockedDenseMirrorEnabled(const SimWorkspace &workspace)
{
  return workspace.blockedDenseStrideWords > 0 && !workspace.blockedDense.empty();
}

inline const uint64_t *simBlockedDenseMirrorRowPtr(const SimWorkspace &workspace,long rowIndex)
{
  if(!simBlockedDenseMirrorEnabled(workspace))
  {
    return NULL;
  }
  return workspace.blockedDense.data() + static_cast<size_t>(rowIndex) * workspace.blockedDenseStrideWords;
}

inline uint64_t *simBlockedDenseMirrorRowPtr(SimWorkspace &workspace,long rowIndex)
{
  if(!simBlockedDenseMirrorEnabled(workspace))
  {
    return NULL;
  }
  return workspace.blockedDense.data() + static_cast<size_t>(rowIndex) * workspace.blockedDenseStrideWords;
}

inline uint64_t simBlockedDenseMirrorBytes(const SimWorkspace &workspace)
{
  return static_cast<uint64_t>(workspace.blockedDense.size()) * static_cast<uint64_t>(sizeof(uint64_t));
}

inline void markSimDiagonalBlocked(SimWorkspace &workspace,long rowIndex,long columnIndex)
{
  vector<uint64_t> &blockedRow = workspace.blocked[static_cast<size_t>(rowIndex)];
  if(blockedRow.empty())
  {
    blockedRow.assign(workspace.blockedWordsPerRow,0);
  }

  const size_t wordIndex = static_cast<size_t>(columnIndex) >> 6;
  const uint64_t mask = static_cast<uint64_t>(1) << (static_cast<size_t>(columnIndex) & 63);
  blockedRow[wordIndex] |= mask;
  uint64_t *blockedDenseRow = simBlockedDenseMirrorRowPtr(workspace,rowIndex);
  if(blockedDenseRow != NULL)
  {
    blockedDenseRow[wordIndex] |= mask;
  }
}

inline void orderSimState(long &score1,long &x1,long &y1,long score2,long x2,long y2)
{
  if(score1 < score2)
  {
    score1 = score2;
    x1 = x2;
    y1 = y2;
  }
  else if(score1 == score2)
  {
    if(x1 < x2)
    {
      x1 = x2;
      y1 = y2;
    }
    else if(x1 == x2 && y1 < y2)
    {
      y1 = y2;
    }
  }
}

inline uint64_t packSimCoord(uint32_t i,uint32_t j)
{
  return (static_cast<uint64_t>(i) << 32) | static_cast<uint64_t>(j);
}

inline uint32_t unpackSimCoordI(uint64_t coord)
{
  return static_cast<uint32_t>(coord >> 32);
}

inline uint32_t unpackSimCoordJ(uint64_t coord)
{
  return static_cast<uint32_t>(coord);
}

inline void orderSimStatePacked(long &score1,uint64_t &coord1,long score2,uint64_t coord2)
{
  if(score1 < score2)
  {
    score1 = score2;
    coord1 = coord2;
  }
  else if(score1 == score2)
  {
    if(coord1 < coord2)
    {
      coord1 = coord2;
    }
  }
}

inline void initializeSimKernel(float parm_M,float parm_I,float parm_O,float parm_E,SimKernelContext &context)
{
  context.scoreMatrix['A']['A'] = context.scoreMatrix['C']['C'] = context.scoreMatrix['G']['G'] = context.scoreMatrix['T']['T'] = 10 * parm_M;
  context.scoreMatrix['A']['G'] = context.scoreMatrix['G']['A'] = context.scoreMatrix['C']['T'] = context.scoreMatrix['T']['C'] = 10 * parm_I;
  context.scoreMatrix['A']['C'] = context.scoreMatrix['A']['T'] = context.scoreMatrix['C']['A'] = context.scoreMatrix['C']['G'] =
  context.scoreMatrix['G']['C'] = context.scoreMatrix['G']['T'] = context.scoreMatrix['T']['A'] = context.scoreMatrix['T']['G'] = 10 * parm_I;
  context.gapOpen = -10 * parm_O;
  context.gapExtend = -10 * parm_E;
	  context.runningMin = 0;
	  context.candidateCount = 0;
	  context.proposalCandidateLoop = false;
	  invalidateSimSafeCandidateStateStore(context);
  clearSimCandidateStartIndex(context.candidateStartIndex);
  context.candidateMinHeap.clear();
}

	struct SimInitialCellEvent
	{
	  SimInitialCellEvent(long n1=0,long n2=0,long n3=0,long n4=0,long n5=0):
	    score(n1), startI(n2), startJ(n3), endI(n4), endJ(n5) {}

	  long score;
	  long startI;
	  long startJ;
	  long endI;
	  long endJ;
	};

	struct SimCandidateRunUpdater
	{
	  explicit SimCandidateRunUpdater(SimKernelContext &context,long *runningMinPtr = NULL):
	    context(context),
	    runningMinPtr(runningMinPtr),
	    stats(context.statsEnabled ? &context.stats : NULL),
	    hasRun(false),
	    runStartI(0),
	    runStartJ(0),
	    runEndI(0),
	    runMinEndJ(0),
	    runMaxEndJ(0),
	    runMaxScore(0),
	    runMaxScoreEndJ(0),
	    runCandidateIndex(-1),
	    runLen(0)
	  {
	  }

	  void operator()(const SimInitialCellEvent &event)
	  {
	    if(stats) ++stats->eventsSeen;
	    const bool processable = (runningMinPtr == NULL) || (event.score > *runningMinPtr);
	    if(!hasRun)
	    {
	      if(processable)
	      {
	        startRun(event);
	      }
	      else
	      {
	        if(stats) ++stats->runUpdaterSkippedEvents;
	      }
	      return;
	    }
	    if(event.endI == runEndI && event.startI == runStartI && event.startJ == runStartJ)
	    {
	      if(processable)
	      {
	        extendRun(event);
	      }
	      else
	      {
	        if(stats) ++stats->runUpdaterSkippedEvents;
	      }
	      return;
	    }
	    flushRun();
	    if(processable)
	    {
	      startRun(event);
	    }
	    else
	    {
	      if(stats) ++stats->runUpdaterSkippedEvents;
	    }
	  }

	  void finish()
	  {
	    flushRun();
	  }

	  SimKernelContext &context;
	  long *runningMinPtr;
	  SimCandidateStats *stats;

	  bool hasRun;
	  long runStartI;
	  long runStartJ;
	  long runEndI;
	  long runMinEndJ;
	  long runMaxEndJ;
	  long runMaxScore;
	  long runMaxScoreEndJ;
	  int runCandidateIndex;
	  uint64_t runLen;

	private:
	  void applyFirstEventToCandidate(int candidateIndex,const SimInitialCellEvent &event)
	  {
	    SimCandidate &candidate = context.candidates[candidateIndex];
	    if(candidate.SCORE < event.score)
	    {
	      candidate.SCORE = event.score;
	      candidate.ENDI = event.endI;
	      candidate.ENDJ = event.endJ;
	      if(context.candidateCount == K && context.candidateMinHeap.valid)
	      {
	        updateSimCandidateMinHeapIndex(context, candidateIndex);
	        if(stats) ++stats->heapUpdates;
	      }
	    }
	    if(candidate.TOP > event.endI) candidate.TOP = event.endI;
	    if(candidate.BOT < event.endI) candidate.BOT = event.endI;
	    if(candidate.LEFT > event.endJ) candidate.LEFT = event.endJ;
	    if(candidate.RIGHT < event.endJ) candidate.RIGHT = event.endJ;
	  }

	  void startRun(const SimInitialCellEvent &event)
	  {
	    hasRun = true;
	    runStartI = event.startI;
	    runStartJ = event.startJ;
	    runEndI = event.endI;
	    runMinEndJ = event.endJ;
	    runMaxEndJ = event.endJ;
	    runMaxScore = event.score;
	    runMaxScoreEndJ = event.endJ;
	    runLen = 1;
	    if(stats) ++stats->runUpdaterRunsStarted;
	    runCandidateIndex = ensureSimCandidateIndexForRun(context,
	                                                      runStartI,
	                                                      runStartJ,
	                                                      runMaxScore,
	                                                      runEndI,
	                                                      runMaxScoreEndJ);
	    if(stats) ++stats->addnodeCalls;
	    applyFirstEventToCandidate(runCandidateIndex,event);
	    if(runningMinPtr != NULL)
	    {
	      *runningMinPtr = refreshSimRunningMin(context);
	    }
	  }

	  void extendRun(const SimInitialCellEvent &event)
	  {
	    ++runLen;
	    if(event.endJ < runMinEndJ) runMinEndJ = event.endJ;
	    if(event.endJ > runMaxEndJ) runMaxEndJ = event.endJ;
	    if(event.score > runMaxScore)
	    {
	      runMaxScore = event.score;
	      runMaxScoreEndJ = event.endJ;
	    }
	  }

	  void flushRun()
	  {
	    if(!hasRun)
	    {
	      return;
	    }
	    const uint64_t flushedLen = runLen;
	    hasRun = false;
	    runLen = 0;

	    if(runningMinPtr != NULL && runMaxScore <= *runningMinPtr)
	    {
	      return;
	    }

	    if(stats)
	    {
	      ++stats->runUpdaterFlushes;
	      stats->runUpdaterTotalRunLen += flushedLen;
	      if(flushedLen > stats->runUpdaterMaxRunLen) stats->runUpdaterMaxRunLen = flushedLen;
	    }
	    if(flushedLen <= 1)
	    {
	      return;
	    }
	    const int candidateIndex = runCandidateIndex;
	    SimCandidate &candidate = context.candidates[candidateIndex];
	    if(candidate.SCORE < runMaxScore)
	    {
	      candidate.SCORE = runMaxScore;
	      candidate.ENDI = runEndI;
	      candidate.ENDJ = runMaxScoreEndJ;
	      if(context.candidateCount == K && context.candidateMinHeap.valid)
	      {
	        updateSimCandidateMinHeapIndex(context, candidateIndex);
	        if(stats) ++stats->heapUpdates;
	      }
	    }
	    if(candidate.TOP > runEndI) candidate.TOP = runEndI;
	    if(candidate.BOT < runEndI) candidate.BOT = runEndI;
	    if(candidate.LEFT > runMinEndJ) candidate.LEFT = runMinEndJ;
	    if(candidate.RIGHT < runMaxEndJ) candidate.RIGHT = runMaxEndJ;
	    if(runningMinPtr != NULL)
	    {
	      *runningMinPtr = refreshSimRunningMin(context);
	    }
	  }
	};

	struct SimCandidateEventUpdater
	{
	  explicit SimCandidateEventUpdater(SimKernelContext &context,long *runningMinPtr = NULL):
	    context(context),
	    runningMinPtr(runningMinPtr),
	    stats(context.statsEnabled ? &context.stats : NULL)
	  {
	  }

	  void operator()(const SimInitialCellEvent &event)
	  {
	    if(stats) ++stats->eventsSeen;
	    if(runningMinPtr != NULL)
	    {
	      if(event.score > *runningMinPtr)
	      {
	        *runningMinPtr = addnodeIndexed(event.score,
	                                        event.startI,
	                                        event.startJ,
	                                        event.endI,
	                                        event.endJ,
	                                        context);
	      }
	      return;
	    }
	    addnodeIndexed(event.score,
	                   event.startI,
	                   event.startJ,
	                   event.endI,
	                   event.endJ,
	                   context);
	  }

	  void finish() {}

	  SimKernelContext &context;
	  long *runningMinPtr;
	  SimCandidateStats *stats;
	};

inline void applySimCudaInitialRowEventRun(uint64_t startCoord,
                                           long endI,
                                           long minEndJ,
                                           long maxEndJ,
                                           long maxScore,
                                           long maxScoreEndJ,
                                           SimKernelContext &context,
                                           SimCandidateStats *stats)
{
  const long startI = static_cast<long>(unpackSimCoordI(startCoord));
  const long startJ = static_cast<long>(unpackSimCoordJ(startCoord));
  if(stats) ++stats->addnodeCalls;
  const int candidateIndex = ensureSimCandidateIndexForRun(context,
                                                           startI,
                                                           startJ,
                                                           maxScore,
                                                           endI,
                                                           maxScoreEndJ);
  SimCandidate &candidate = context.candidates[candidateIndex];
  if(candidate.SCORE < maxScore)
  {
    candidate.SCORE = maxScore;
    candidate.ENDI = endI;
    candidate.ENDJ = maxScoreEndJ;
    if(context.candidateCount == K && context.candidateMinHeap.valid)
    {
      updateSimCandidateMinHeapIndex(context, candidateIndex);
      if(stats) ++stats->heapUpdates;
    }
  }
  if(candidate.TOP > endI) candidate.TOP = endI;
  if(candidate.BOT < endI) candidate.BOT = endI;
  if(candidate.LEFT > minEndJ) candidate.LEFT = minEndJ;
  if(candidate.RIGHT < maxEndJ) candidate.RIGHT = maxEndJ;
}

inline void applySimCudaInitialRunSummary(const SimScanCudaInitialRunSummary &summary,
                                          SimKernelContext &context,
                                          SimCandidateStats *stats)
{
  applySimCudaInitialRowEventRun(summary.startCoord,
                                 static_cast<long>(summary.endI),
                                 static_cast<long>(summary.minEndJ),
                                 static_cast<long>(summary.maxEndJ),
                                 static_cast<long>(summary.score),
                                 static_cast<long>(summary.scoreEndJ),
                                 context,
                                 stats);
}

inline bool simCudaInitialRunSummaryIsContextNoOp(const SimScanCudaInitialRunSummary &summary,
                                                  const SimKernelContext &context)
{
  const long startI = static_cast<long>(unpackSimCoordI(summary.startCoord));
  const long startJ = static_cast<long>(unpackSimCoordJ(summary.startCoord));
  const long candidateIndex = findSimCandidateIndex(context.candidateStartIndex,startI,startJ);
  if(candidateIndex < 0 || candidateIndex >= context.candidateCount)
  {
    return false;
  }

  const SimCandidate &candidate = context.candidates[static_cast<size_t>(candidateIndex)];
  return candidate.SCORE > static_cast<long>(summary.score) &&
         candidate.TOP <= static_cast<long>(summary.endI) &&
         candidate.BOT >= static_cast<long>(summary.endI) &&
         candidate.LEFT <= static_cast<long>(summary.minEndJ) &&
         candidate.RIGHT >= static_cast<long>(summary.maxEndJ);
}

	inline void mergeSimCudaInitialRunSummariesIntoSafeStore(const vector<SimScanCudaInitialRunSummary> &summaries,
	                                                         SimKernelContext &context)
	{
	  SimCandidateStateStore &store = context.safeCandidateStateStore;
  if(!store.valid)
  {
    resetSimCandidateStateStore(store,true);
  }
  for(size_t summaryIndex = 0; summaryIndex < summaries.size(); ++summaryIndex)
  {
	    upsertSimCandidateStateStoreSummary(summaries[summaryIndex],store);
	  }
	}

	struct SimInitialPinnedAsyncCpuPipelineApplyState
	{
	  SimInitialPinnedAsyncCpuPipelineApplyState():
	    logicalEventCount(0),
	    maintainSafeStore(false),
	    eventsSeenRecorded(false),
	    chunksApplied(0),
	    summariesApplied(0),
	    chunksFinalized(0),
	    finalizeCount(0),
	    nextExpectedChunkIndex(0),
	    outOfOrderChunks(0)
	  {
	  }

	  uint64_t logicalEventCount;
	  bool maintainSafeStore;
	  bool eventsSeenRecorded;
	  uint64_t chunksApplied;
	  uint64_t summariesApplied;
	  uint64_t chunksFinalized;
	  uint64_t finalizeCount;
	  uint64_t nextExpectedChunkIndex;
	  uint64_t outOfOrderChunks;
	};

	inline void beginSimInitialPinnedAsyncCpuPipelineApply(
	  uint64_t logicalEventCount,
	  SimKernelContext &context,
	  bool maintainSafeStore,
	  SimInitialPinnedAsyncCpuPipelineApplyState &state)
	{
	  state = SimInitialPinnedAsyncCpuPipelineApplyState();
	  state.logicalEventCount = logicalEventCount;
	  state.maintainSafeStore = maintainSafeStore;
	  SimCandidateStats *candidateStats = context.statsEnabled ? &context.stats : NULL;
	  if(candidateStats != NULL && logicalEventCount > 0)
	  {
	    candidateStats->eventsSeen += logicalEventCount;
	    state.eventsSeenRecorded = true;
	  }
	  if(maintainSafeStore && !context.safeCandidateStateStore.valid)
	  {
	    resetSimCandidateStateStore(context.safeCandidateStateStore,true);
	  }
	}

	inline void applySimInitialPinnedAsyncCpuPipelineChunk(
	  const SimScanCudaInitialRunSummary *summaries,
	  int batchIndex,
	  uint64_t chunkIndex,
	  uint64_t summaryBase,
	  size_t summaryCount,
	  SimKernelContext &context,
	  SimInitialPinnedAsyncCpuPipelineApplyState &state)
	{
	  (void)batchIndex;
	  (void)summaryBase;
	  if(chunkIndex < state.nextExpectedChunkIndex)
	  {
	    ++state.outOfOrderChunks;
	  }
	  state.nextExpectedChunkIndex = chunkIndex + 1;
	  ++state.chunksApplied;
	  if(summaries == NULL || summaryCount == 0)
	  {
	    return;
	  }
	  SimCandidateStats *candidateStats = context.statsEnabled ? &context.stats : NULL;
	  SimCandidateStateStore *safeStore =
	    state.maintainSafeStore ? &context.safeCandidateStateStore : NULL;
	  if(safeStore != NULL && !safeStore->valid)
	  {
	    resetSimCandidateStateStore(*safeStore,true);
	  }
	  for(size_t summaryIndex = 0; summaryIndex < summaryCount; ++summaryIndex)
	  {
	    const SimScanCudaInitialRunSummary &summary = summaries[summaryIndex];
	    applySimCudaInitialRunSummary(summary,context,candidateStats);
	    if(safeStore != NULL)
	    {
	      upsertSimCandidateStateStoreSummary(summary,*safeStore);
	    }
	  }
	  state.summariesApplied += static_cast<uint64_t>(summaryCount);
	}

	inline void finalizeSimInitialPinnedAsyncCpuPipelineApply(
	  SimKernelContext &context,
	  SimInitialPinnedAsyncCpuPipelineApplyState &state,
	  bool pruneSafeStore)
	{
	  SimCandidateStats *candidateStats = context.statsEnabled ? &context.stats : NULL;
	  if(candidateStats != NULL &&
	     !state.eventsSeenRecorded &&
	     state.logicalEventCount > 0)
	  {
	    candidateStats->eventsSeen += state.logicalEventCount;
	    state.eventsSeenRecorded = true;
	  }
	  refreshSimRunningMin(context);
	  if(state.maintainSafeStore && pruneSafeStore)
	  {
	    pruneSimSafeCandidateStateStore(context);
	  }
	  ++state.finalizeCount;
	  state.chunksFinalized = state.chunksApplied;
	}

	inline void recordSimInitialPinnedAsyncCpuPipelineFinalizeStats(
	  const SimInitialPinnedAsyncCpuPipelineApplyState &state)
	{
	  simInitialPinnedAsyncCpuPipelineChunksFinalized().fetch_add(
	    state.chunksFinalized,
	    std::memory_order_relaxed);
	  simInitialPinnedAsyncCpuPipelineFinalizeCount().fetch_add(
	    state.finalizeCount,
	    std::memory_order_relaxed);
	  simInitialPinnedAsyncCpuPipelineOutOfOrderChunks().fetch_add(
	    state.outOfOrderChunks,
	    std::memory_order_relaxed);
	}

	inline void applySimCudaInitialRunSummariesChunkedHandoff(
	  const vector<SimScanCudaInitialRunSummary> &summaries,
	  uint64_t logicalEventCount,
	  SimKernelContext &context,
	  bool maintainSafeStore,
	  SimInitialChunkedHandoffStats *statsOut = NULL)
	{
	  SimInitialChunkedHandoffStats stats;
	  stats.ringSlots = static_cast<uint64_t>(simCudaInitialChunkedHandoffRingSlotsRuntime());
	  const int chunkRowsRuntime = simCudaInitialChunkedHandoffChunkRowsRuntime();
	  stats.rowsPerChunk = static_cast<uint64_t>(chunkRowsRuntime > 0 ? chunkRowsRuntime : 1);
	  const size_t chunkRows = static_cast<size_t>(stats.rowsPerChunk);
	  SimCandidateStats *candidateStats = context.statsEnabled ? &context.stats : NULL;
	  if(candidateStats) candidateStats->eventsSeen += logicalEventCount;

	  SimCandidateStateStore *safeStore = NULL;
	  if(maintainSafeStore)
	  {
	    safeStore = &context.safeCandidateStateStore;
	    if(!safeStore->valid)
	    {
	      resetSimCandidateStateStore(*safeStore,true);
	    }
	  }

	  const std::chrono::steady_clock::time_point waitStart = std::chrono::steady_clock::now();
	  for(size_t chunkBase = 0; chunkBase < summaries.size();)
	  {
	    ++stats.chunkCount;
	    const uint64_t chunkStartRow =
	      static_cast<uint64_t>(summaries[chunkBase].endI);
	    const uint64_t chunkEndRow =
	      chunkStartRow + static_cast<uint64_t>(chunkRows) - 1u;
	    size_t chunkEnd = chunkBase + 1u;
	    while(chunkEnd < summaries.size() &&
	          static_cast<uint64_t>(summaries[chunkEnd].endI) <= chunkEndRow)
	    {
	      ++chunkEnd;
	    }
	    stats.summariesReplayed += static_cast<uint64_t>(chunkEnd - chunkBase);
	    for(size_t summaryIndex = chunkBase; summaryIndex < chunkEnd; ++summaryIndex)
	    {
	      const SimScanCudaInitialRunSummary &summary = summaries[summaryIndex];
	      applySimCudaInitialRunSummary(summary,context,candidateStats);
	      if(safeStore != NULL)
	      {
	        upsertSimCandidateStateStoreSummary(summary,*safeStore);
	      }
	    }
	    chunkBase = chunkEnd;
	  }
	  stats.cpuWaitNanoseconds = simElapsedNanoseconds(waitStart);
	  refreshSimRunningMin(context);
	  if(maintainSafeStore)
	  {
	    pruneSimSafeCandidateStateStore(context);
	  }
	  if(statsOut != NULL)
	  {
	    *statsOut = stats;
	  }
	  recordSimInitialChunkedHandoffStats(stats);
	}

	inline void applySimCudaInitialRunSummariesChunkedHandoffForTest(
	  const vector<SimScanCudaInitialRunSummary> &summaries,
	  uint64_t logicalEventCount,
	  SimKernelContext &context,
	  bool maintainSafeStore,
	  SimInitialChunkedHandoffStats *statsOut = NULL)
	{
	  applySimCudaInitialRunSummariesChunkedHandoff(summaries,
	                                               logicalEventCount,
	                                               context,
	                                               maintainSafeStore,
	                                               statsOut);
	}

	struct SimInitialCpuFrontierFastApplyTransducer
	{
	  enum { indexCapacity = 256 };

	  SimInitialCpuFrontierFastApplyTransducer():
	    candidateCount(0)
	  {
	    clearIndex();
	    heap.clear();
	  }

	  void clearIndex()
	  {
	    memset(slotState,0,sizeof(slotState));
	    memset(candidateSlot,0xff,sizeof(candidateSlot));
	    tombstoneCount = 0;
	  }

	  static size_t hashStartCoord(uint64_t startCoord)
	  {
	    uint64_t value = startCoord;
	    value ^= value >> 33;
	    value *= 0xff51afd7ed558ccdull;
	    value ^= value >> 33;
	    return static_cast<size_t>(value & (indexCapacity - 1));
	  }

	  int findIndex(uint64_t startCoord) const
	  {
	    size_t slot = hashStartCoord(startCoord);
	    for(size_t probe = 0; probe < indexCapacity; ++probe)
	    {
	      if(slotState[slot] == 0)
	      {
	        return -1;
	      }
	      if(slotState[slot] == 1 && slotStartCoord[slot] == startCoord)
	      {
	        return slotCandidateIndex[slot];
	      }
	      slot = (slot + 1) & (indexCapacity - 1);
	    }
	    return -1;
	  }

	  void insertIndex(uint64_t startCoord,int candidateIndex)
	  {
	    size_t slot = hashStartCoord(startCoord);
	    size_t firstTombstone = indexCapacity;
	    while(slotState[slot] != 0)
	    {
	      if(slotState[slot] == 2 && firstTombstone == indexCapacity)
	      {
	        firstTombstone = slot;
	      }
	      slot = (slot + 1) & (indexCapacity - 1);
	    }
	    if(firstTombstone != indexCapacity)
	    {
	      slot = firstTombstone;
	      --tombstoneCount;
	    }
	    slotState[slot] = 1;
	    slotStartCoord[slot] = startCoord;
	    slotCandidateIndex[slot] = candidateIndex;
	    candidateSlot[candidateIndex] = static_cast<int>(slot);
	  }

	  void eraseIndex(int candidateIndex)
	  {
	    if(candidateIndex < 0 || candidateIndex >= K)
	    {
	      return;
	    }
	    const int slot = candidateSlot[candidateIndex];
	    if(slot < 0)
	    {
	      return;
	    }
	    slotState[static_cast<size_t>(slot)] = 2;
	    candidateSlot[candidateIndex] = -1;
	    ++tombstoneCount;
	  }

	  void rebuildIndex()
	  {
	    clearIndex();
	    for(long candidateIndex = 0; candidateIndex < candidateCount; ++candidateIndex)
	    {
	      insertIndex(packSimCoord(static_cast<uint32_t>(candidates[candidateIndex].STARI),
	                               static_cast<uint32_t>(candidates[candidateIndex].STARJ)),
	                  static_cast<int>(candidateIndex));
	    }
	  }

	  void buildHeap()
	  {
	    heap.clear();
	    if(candidateCount <= 0)
	    {
	      return;
	    }
	    heap.size = static_cast<int>(candidateCount);
	    for(int candidateIndex = 0; candidateIndex < heap.size; ++candidateIndex)
	    {
	      heap.heap[candidateIndex] = candidateIndex;
	      heap.pos[candidateIndex] = candidateIndex;
	    }
	    for(int heapIndex = heap.size / 2 - 1; heapIndex >= 0; --heapIndex)
	    {
	      simCandidateHeapSiftDown(heap,candidates,heapIndex);
	    }
	    heap.valid = (candidateCount == K);
	  }

	  void updateHeapIndex(int candidateIndex)
	  {
	    if(!heap.valid || candidateIndex < 0 || candidateIndex >= K)
	    {
	      return;
	    }
	    const int currentPos = heap.pos[candidateIndex];
	    if(currentPos < 0 || currentPos >= heap.size)
	    {
	      return;
	    }
	    simCandidateHeapSiftUp(heap,candidates,currentPos);
	    simCandidateHeapSiftDown(heap,candidates,heap.pos[candidateIndex]);
	  }

	  int ensureCandidateIndex(uint64_t startCoord,long startI,long startJ,long score,long endI,long endJ)
	  {
	    const int foundIndex = findIndex(startCoord);
	    if(foundIndex >= 0 && foundIndex < candidateCount)
	    {
	      return foundIndex;
	    }

	    int slotIndex = 0;
	    if(candidateCount == K)
	    {
	      if(!heap.valid)
	      {
	        buildHeap();
	      }
	      slotIndex = peekMinSimCandidateIndex(heap);
	      if(slotIndex < 0 || slotIndex >= static_cast<int>(candidateCount))
	      {
	        slotIndex = 0;
	      }
	      eraseIndex(slotIndex);
	    }
	    else
	    {
	      slotIndex = static_cast<int>(candidateCount++);
	    }

	    SimCandidate &candidate = candidates[slotIndex];
	    candidate.SCORE = score;
	    candidate.STARI = startI;
	    candidate.STARJ = startJ;
	    candidate.ENDI = endI;
	    candidate.ENDJ = endJ;
	    candidate.TOP = candidate.BOT = endI;
	    candidate.LEFT = candidate.RIGHT = endJ;
	    insertIndex(startCoord,slotIndex);
	    if(candidateCount == K)
	    {
	      if(!heap.valid)
	      {
	        buildHeap();
	      }
	      updateHeapIndex(slotIndex);
	    }
	    if(tombstoneCount > static_cast<size_t>(K))
	    {
	      rebuildIndex();
	    }
	    return slotIndex;
	  }

	  void applySummary(const SimScanCudaInitialRunSummary &summary)
	  {
	    const long startI = static_cast<long>(unpackSimCoordI(summary.startCoord));
	    const long startJ = static_cast<long>(unpackSimCoordJ(summary.startCoord));
	    const long score = static_cast<long>(summary.score);
	    const long endI = static_cast<long>(summary.endI);
	    const long scoreEndJ = static_cast<long>(summary.scoreEndJ);
	    const int candidateIndex =
	      ensureCandidateIndex(summary.startCoord,startI,startJ,score,endI,scoreEndJ);
	    SimCandidate &candidate = candidates[candidateIndex];
	    if(candidate.SCORE < score)
	    {
	      candidate.SCORE = score;
	      candidate.ENDI = endI;
	      candidate.ENDJ = scoreEndJ;
	      if(candidateCount == K && heap.valid)
	      {
	        updateHeapIndex(candidateIndex);
	      }
	    }
	    if(candidate.TOP > endI) candidate.TOP = endI;
	    if(candidate.BOT < endI) candidate.BOT = endI;
	    if(candidate.LEFT > static_cast<long>(summary.minEndJ))
	    {
	      candidate.LEFT = static_cast<long>(summary.minEndJ);
	    }
	    if(candidate.RIGHT < static_cast<long>(summary.maxEndJ))
	    {
	      candidate.RIGHT = static_cast<long>(summary.maxEndJ);
	    }
	  }

	  void materialize(SimKernelContext &context) const
	  {
	    context.candidateCount = candidateCount;
	    for(long candidateIndex = 0; candidateIndex < candidateCount; ++candidateIndex)
	    {
	      context.candidates[candidateIndex] = candidates[candidateIndex];
	    }
	    rebuildSimCandidateStartIndex(context);
	    context.candidateMinHeap.clear();
	    if(context.candidateCount == K)
	    {
	      buildSimCandidateMinHeap(context);
	    }
	    refreshSimRunningMin(context);
	  }

	  SimCandidate candidates[K];
	  long candidateCount;
	  unsigned char slotState[indexCapacity];
	  uint64_t slotStartCoord[indexCapacity];
	  int slotCandidateIndex[indexCapacity];
	  int candidateSlot[K];
	  size_t tombstoneCount;
	  SimCandidateMinHeap heap;
	};

	inline bool applySimCudaInitialRunSummariesCpuFrontierFastApply(
	  const vector<SimScanCudaInitialRunSummary> &summaries,
	  uint64_t eventCount,
	  SimKernelContext &context,
	  SimInitialCpuFrontierFastApplyStats *statsOut = NULL)
	{
	  (void)eventCount;
	  if(statsOut != NULL)
	  {
	    *statsOut = SimInitialCpuFrontierFastApplyStats();
	  }
	  if(context.statsEnabled || context.candidateCount != 0)
	  {
	    return false;
	  }

	  SimInitialCpuFrontierFastApplyTransducer transducer;
	  for(size_t summaryIndex = 0; summaryIndex < summaries.size(); ++summaryIndex)
	  {
	    transducer.applySummary(summaries[summaryIndex]);
	  }
	  transducer.materialize(context);
	  if(statsOut != NULL)
	  {
	    statsOut->summariesReplayed = static_cast<uint64_t>(summaries.size());
	    statsOut->candidatesOut = static_cast<uint64_t>(context.candidateCount);
	  }
	  return true;
	}

	inline bool applySimCudaRegionRunSummary(const SimScanCudaInitialRunSummary &summary,
	                                         SimKernelContext &context,
	                                         SimCandidateStats *stats = NULL)
{
  if(static_cast<long>(summary.score) <= context.runningMin)
  {
    return false;
  }
  applySimCudaInitialRunSummary(summary,context,stats);
  refreshSimRunningMin(context);
  return true;
}

inline void applySimCudaRegionRunSummaries(const vector<SimScanCudaInitialRunSummary> &summaries,
                                           SimKernelContext &context,
                                           SimCandidateStats *stats = NULL)
{
  for(size_t summaryIndex = 0; summaryIndex < summaries.size(); ++summaryIndex)
  {
    applySimCudaRegionRunSummary(summaries[summaryIndex],context,stats);
  }
}

inline void summarizeSimCudaInitialRowEventRuns(const vector<SimScanCudaRowEvent> &events,
                                                const vector<int> &rowOffsets,
                                                long rowCount,
                                                vector<SimScanCudaInitialRunSummary> &outSummaries)
{
  outSummaries.clear();
  if(rowCount <= 0)
  {
    return;
  }

  for(long endI = 1; endI <= rowCount; ++endI)
  {
    const int startIndex = rowOffsets[static_cast<size_t>(endI)];
    const int endIndex = rowOffsets[static_cast<size_t>(endI + 1)];
    for(int eventIndex = startIndex; eventIndex < endIndex;)
    {
      const int runEndIndex = simScanCudaInitialRunEndExclusive(events,endIndex,eventIndex);
      SimScanCudaInitialRunSummary summary;
      initSimCudaInitialRunSummary(events[static_cast<size_t>(eventIndex)],summary);
      for(int runEventIndex = eventIndex + 1; runEventIndex < runEndIndex; ++runEventIndex)
      {
        updateSimCudaInitialRunSummary(events[static_cast<size_t>(runEventIndex)],summary);
      }
      outSummaries.push_back(summary);
      eventIndex = runEndIndex;
    }
  }
}

inline void mergeSimCudaInitialRunSummaries(const vector<SimScanCudaInitialRunSummary> &summaries,
                                            uint64_t logicalEventCount,
                                            SimKernelContext &context)
{
  SimCandidateStats *stats = context.statsEnabled ? &context.stats : NULL;
  if(stats) stats->eventsSeen += logicalEventCount;
  for(size_t summaryIndex = 0; summaryIndex < summaries.size(); ++summaryIndex)
  {
    applySimCudaInitialRunSummary(summaries[summaryIndex],context,stats);
  }
  refreshSimRunningMin(context);
}

inline void mergeSimCudaInitialRunSummariesWithContextApplyChunkSkip(
  const vector<SimScanCudaInitialRunSummary> &summaries,
  uint64_t logicalEventCount,
  SimKernelContext &context,
  int chunkSize,
  SimInitialContextApplyChunkSkipStats *statsOut = NULL)
{
  SimInitialContextApplyChunkSkipStats stats;
  SimCandidateStats *candidateStats = context.statsEnabled ? &context.stats : NULL;
  if(candidateStats) candidateStats->eventsSeen += logicalEventCount;
  const size_t safeChunkSize = static_cast<size_t>(chunkSize > 0 ? chunkSize : 1);

  for(size_t chunkBase = 0; chunkBase < summaries.size(); chunkBase += safeChunkSize)
  {
    ++stats.chunkCount;
    const size_t chunkEnd = min(chunkBase + safeChunkSize,summaries.size());
    bool chunkIsCoveredNoOp = true;
    for(size_t summaryIndex = chunkBase; summaryIndex < chunkEnd; ++summaryIndex)
    {
      if(!simCudaInitialRunSummaryIsContextNoOp(summaries[summaryIndex],context))
      {
        chunkIsCoveredNoOp = false;
        break;
      }
    }

    const uint64_t chunkSummaryCount = static_cast<uint64_t>(chunkEnd - chunkBase);
    if(chunkIsCoveredNoOp)
    {
      ++stats.chunkSkippedCount;
      stats.summarySkippedCount += chunkSummaryCount;
      continue;
    }

    ++stats.chunkReplayedCount;
    stats.summaryReplayedCount += chunkSummaryCount;
    for(size_t summaryIndex = chunkBase; summaryIndex < chunkEnd; ++summaryIndex)
    {
      applySimCudaInitialRunSummary(summaries[summaryIndex],context,candidateStats);
    }
  }

  refreshSimRunningMin(context);
  if(statsOut != NULL)
  {
    *statsOut = stats;
  }
}

inline void mergeSimCudaCandidateStatesIntoContext(const vector<SimScanCudaCandidateState> &states,
                                                   SimKernelContext &context)
{
  context.gpuFrontierCacheInSync = false;
  SimCandidateStats *stats = context.statsEnabled ? &context.stats : NULL;
  for(size_t stateIndex = 0; stateIndex < states.size(); ++stateIndex)
  {
    applySimCudaCandidateState(states[stateIndex],context,stats);
  }
  refreshSimRunningMin(context);
}

inline void reduceSimCudaInitialRunSummariesToCandidateStates(const vector<SimScanCudaInitialRunSummary> &summaries,
                                                              vector<SimScanCudaCandidateState> &outCandidateStates,
                                                              int &outRunningMin)
{
  SimKernelContext reduceContext(1,1);
  clearSimCandidateStartIndex(reduceContext.candidateStartIndex);
  reduceContext.candidateMinHeap.clear();
  mergeSimCudaInitialRunSummaries(summaries,
                                  static_cast<uint64_t>(summaries.size()),
                                  reduceContext);
  outCandidateStates.clear();
  outCandidateStates.reserve(static_cast<size_t>(reduceContext.candidateCount));
  for(long candidateIndex = 0; candidateIndex < reduceContext.candidateCount; ++candidateIndex)
  {
    outCandidateStates.push_back(makeSimScanCudaCandidateState(reduceContext.candidates[candidateIndex]));
  }
  outRunningMin = static_cast<int>(reduceContext.runningMin);
}

inline void reduceSimCudaInitialRunSummariesToCandidateStatesChunkPruned(const vector<SimScanCudaInitialRunSummary> &summaries,
                                                                         int chunkSize,
                                                                         vector<SimScanCudaCandidateState> &outCandidateStates,
                                                                         int &outRunningMin,
                                                                         SimScanCudaInitialReduceReplayStats *statsOut = NULL)
{
  SimKernelContext reduceContext(1,1);
  clearSimCandidateStartIndex(reduceContext.candidateStartIndex);
  reduceContext.candidateMinHeap.clear();

  SimScanCudaInitialReduceReplayStats stats;
  const size_t safeChunkSize =
    static_cast<size_t>(chunkSize > 0 ? chunkSize : 1);
  SimCandidateStats *candidateStats = reduceContext.statsEnabled ? &reduceContext.stats : NULL;
  for(size_t chunkBase = 0; chunkBase < summaries.size(); chunkBase += safeChunkSize)
  {
    ++stats.chunkCount;
    const size_t chunkEnd = min(chunkBase + safeChunkSize, summaries.size());
    bool chunkNeedsReplay = false;
    for(size_t summaryIndex = chunkBase; summaryIndex < chunkEnd; ++summaryIndex)
    {
      const SimScanCudaInitialRunSummary &summary = summaries[summaryIndex];
      const long candidateIndex =
        findSimCandidateIndex(reduceContext.candidateStartIndex,
                              static_cast<long>(summary.startCoord >> 32),
                              static_cast<long>(summary.startCoord & 0xffffffffu));
      if(candidateIndex < 0)
      {
        chunkNeedsReplay = true;
        break;
      }
      const SimCandidate &candidate = reduceContext.candidates[static_cast<size_t>(candidateIndex)];
      if(candidate.SCORE < static_cast<long>(summary.score) ||
         candidate.TOP > static_cast<long>(summary.endI) ||
         candidate.BOT < static_cast<long>(summary.endI) ||
         candidate.LEFT > static_cast<long>(summary.minEndJ) ||
         candidate.RIGHT < static_cast<long>(summary.maxEndJ))
      {
        chunkNeedsReplay = true;
        break;
      }
    }
    if(!chunkNeedsReplay)
    {
      ++stats.chunkSkippedCount;
      continue;
    }

    ++stats.chunkReplayedCount;
    stats.summaryReplayCount += static_cast<uint64_t>(chunkEnd - chunkBase);
    for(size_t summaryIndex = chunkBase; summaryIndex < chunkEnd; ++summaryIndex)
    {
      applySimCudaInitialRunSummary(summaries[summaryIndex],reduceContext,candidateStats);
    }
    refreshSimRunningMin(reduceContext);
  }

  outCandidateStates.clear();
  outCandidateStates.reserve(static_cast<size_t>(reduceContext.candidateCount));
  for(long candidateIndex = 0; candidateIndex < reduceContext.candidateCount; ++candidateIndex)
  {
    outCandidateStates.push_back(makeSimScanCudaCandidateState(reduceContext.candidates[candidateIndex]));
  }
  outRunningMin = static_cast<int>(reduceContext.runningMin);
  if(statsOut != NULL)
  {
    *statsOut = stats;
  }
}

inline void reduceSimCudaInitialRunSummariesToAllCandidateStates(const vector<SimScanCudaInitialRunSummary> &summaries,
                                                                 const vector<uint64_t> *allowedStartCoords,
                                                                 vector<SimScanCudaCandidateState> &outCandidateStates)
{
  outCandidateStates.clear();
  if(summaries.empty())
  {
    return;
  }

  vector<uint64_t> sortedAllowedStartCoords;
  if(allowedStartCoords != NULL && !allowedStartCoords->empty())
  {
    sortedAllowedStartCoords = *allowedStartCoords;
    sort(sortedAllowedStartCoords.begin(),sortedAllowedStartCoords.end());
    sortedAllowedStartCoords.erase(unique(sortedAllowedStartCoords.begin(),
                                          sortedAllowedStartCoords.end()),
                                   sortedAllowedStartCoords.end());
  }

  unordered_map<uint64_t,size_t> startCoordToIndex;
  outCandidateStates.reserve(summaries.size());
  for(size_t summaryIndex = 0; summaryIndex < summaries.size(); ++summaryIndex)
  {
    const SimScanCudaInitialRunSummary &summary = summaries[summaryIndex];
    if(!sortedAllowedStartCoords.empty() &&
       !binary_search(sortedAllowedStartCoords.begin(),
                      sortedAllowedStartCoords.end(),
                      summary.startCoord))
    {
      continue;
    }
    unordered_map<uint64_t,size_t>::iterator found = startCoordToIndex.find(summary.startCoord);
    if(found == startCoordToIndex.end())
    {
      SimScanCudaCandidateState candidate;
      initSimScanCudaCandidateStateFromInitialRunSummary(summary,candidate);
      startCoordToIndex[summary.startCoord] = outCandidateStates.size();
      outCandidateStates.push_back(candidate);
      continue;
    }
    updateSimScanCudaCandidateStateFromInitialRunSummary(summary,
                                                         outCandidateStates[found->second]);
  }
}

inline void mergeSimCudaInitialRowEventRuns(const vector<SimScanCudaRowEvent> &events,
                                            const vector<int> &rowOffsets,
                                            long rowCount,
                                            SimKernelContext &context)
{
  vector<SimScanCudaInitialRunSummary> summaries;
  summarizeSimCudaInitialRowEventRuns(events,rowOffsets,rowCount,summaries);
  mergeSimCudaInitialRunSummaries(summaries,
                                  static_cast<uint64_t>(events.size()),
                                  context);
}

	struct SimWavefrontDiagonal
	{
	  SimWavefrontDiagonal():startI(0) {}

  void reset(long firstI,long lastI)
  {
    startI = firstI;
    const size_t length = lastI >= firstI ? static_cast<size_t>(lastI - firstI + 1) : 0;
    H.resize(length);
    D.resize(length);
    F.resize(length);
    Hi.resize(length);
    Hj.resize(length);
    Di.resize(length);
    Dj.resize(length);
    Fi.resize(length);
    Fj.resize(length);
  }

  void clearRetainingCapacity()
  {
    startI = 0;
    H.clear();
    D.clear();
    F.clear();
    Hi.clear();
    Hj.clear();
    Di.clear();
    Dj.clear();
    Fi.clear();
    Fj.clear();
  }

  bool contains(long i) const
  {
    return !H.empty() && i >= startI && i < startI + static_cast<long>(H.size());
  }

  size_t index(long i) const
  {
    return static_cast<size_t>(i - startI);
  }

  long startI;
  vector<int> H;
  vector<int> D;
  vector<int> F;
  vector<long> Hi;
  vector<long> Hj;
  vector<long> Di;
  vector<long> Dj;
  vector<long> Fi;
  vector<long> Fj;
};

struct SimWavefrontDiagonalPacked
{
  SimWavefrontDiagonalPacked():startI(0) {}

  void reset(long firstI,long lastI)
  {
    startI = firstI;
    const size_t length = lastI >= firstI ? static_cast<size_t>(lastI - firstI + 1) : 0;
    H.resize(length);
    D.resize(length);
    F.resize(length);
    Hc.resize(length);
    Dc.resize(length);
    Fc.resize(length);
  }

  void clearRetainingCapacity()
  {
    startI = 0;
    H.clear();
    D.clear();
    F.clear();
    Hc.clear();
    Dc.clear();
    Fc.clear();
  }

  bool contains(long i) const
  {
    return !H.empty() && i >= startI && i < startI + static_cast<long>(H.size());
  }

  size_t index(long i) const
  {
    return static_cast<size_t>(i - startI);
  }

  long startI;
  vector<int> H;
  vector<int> D;
  vector<int> F;
  vector<uint64_t> Hc;
  vector<uint64_t> Dc;
  vector<uint64_t> Fc;
};

struct SimWavefrontRowEventPacked
{
  SimWavefrontRowEventPacked(int n1=0,uint64_t n2=0,uint32_t n3=0):
    score(n1), startCoord(n2), endJ(n3) {}

  int score;
  uint64_t startCoord;
  uint32_t endJ;
};

#if defined(__SSE2__)
inline __m128i simMaxEpi32(__m128i lhs,__m128i rhs)
{
  const __m128i lhsGreaterMask = _mm_cmpgt_epi32(lhs,rhs);
  return _mm_or_si128(_mm_and_si128(lhsGreaterMask,lhs),_mm_andnot_si128(lhsGreaterMask,rhs));
}
#endif

#if defined(__AVX2__)
inline __m256i simMaxEpi32Avx2(__m256i lhs,__m256i rhs)
{
  const __m256i lhsGreaterMask = _mm256_cmpgt_epi32(lhs,rhs);
  return _mm256_or_si256(_mm256_and_si256(lhsGreaterMask,lhs),_mm256_andnot_si256(lhsGreaterMask,rhs));
}
#endif

enum SimInitialScanBackend
{
  SIM_INITIAL_SCAN_ROW_MAJOR = 0,
  SIM_INITIAL_SCAN_WAVEFRONT = 1
};

inline bool tryParseSimInitialScanBackendEnv(SimInitialScanBackend &backend)
{
  const char *forcedBackend = getenv("LONGTARGET_SIM_INITIAL_BACKEND");
  if(forcedBackend == NULL || forcedBackend[0] == '\0')
  {
    return false;
  }
  if(strcmp(forcedBackend,"row") == 0 || strcmp(forcedBackend,"row-major") == 0)
  {
    backend = SIM_INITIAL_SCAN_ROW_MAJOR;
    return true;
  }
  if(strcmp(forcedBackend,"wave") == 0 || strcmp(forcedBackend,"wavefront") == 0)
  {
    backend = SIM_INITIAL_SCAN_WAVEFRONT;
    return true;
  }
  return false;
}

inline SimInitialScanBackend selectSimInitialScanBackend(const SimKernelContext &context)
{
  SimInitialScanBackend forcedBackend;
  if(tryParseSimInitialScanBackendEnv(forcedBackend))
  {
    return forcedBackend;
  }
  (void)context;
  return SIM_INITIAL_SCAN_WAVEFRONT;
}

inline void ensureSimWavefrontSubstitutionProfiles(const char *A,const char *B,SimKernelContext &context)
{
  const long rowEnd = static_cast<long>(context.workspace.HH.size()) - 1;
  const long colEnd = static_cast<long>(context.workspace.CC.size()) - 1;
  const size_t expectedSize = static_cast<size_t>(rowEnd + colEnd + 1);
  if(context.wavefrontSubstitutionScores.size() == expectedSize)
  {
    return;
  }

  context.wavefrontSubstitutionStartI.assign(expectedSize,0);
  context.wavefrontSubstitutionScores.assign(expectedSize, vector<int>());
  for(long diagonal = 2; diagonal <= rowEnd + colEnd; ++diagonal)
  {
    const long startI = max(1L, diagonal - colEnd);
    const long endI = min(rowEnd, diagonal - 1);
    context.wavefrontSubstitutionStartI[static_cast<size_t>(diagonal)] = startI;
    vector<int> &profileScore = context.wavefrontSubstitutionScores[static_cast<size_t>(diagonal)];
    profileScore.assign(endI >= startI ? static_cast<size_t>(endI - startI + 1) : 0, 0);
    for(long i = startI; i <= endI; ++i)
    {
      const long j = diagonal - i;
      profileScore[static_cast<size_t>(i - startI)] = static_cast<int>(context.scoreMatrix[A[i]][B[j]]);
    }
  }
}

template <typename EventHandler>
inline void enumerateSimCandidateRegionRowMajor(const char *A,
                                                const char *B,
                                                long rowStart,
                                                long rowEnd,
                                                long colStart,
                                                long colEnd,
                                                long eventScoreFloor,
                                                SimKernelContext &context,
                                                EventHandler onEvent)
{
  if(rowStart > rowEnd || colStart > colEnd)
  {
    return;
  }

  long *CC = context.workspace.CC.data();
  long *DD = context.workspace.DD.data();
  long *RR = context.workspace.RR.data();
  long *SS = context.workspace.SS.data();
  long *EE = context.workspace.EE.data();
  long *FF = context.workspace.FF.data();
  long Q = context.gapOpen;
  long R = context.gapExtend;

  long c;
  long f;
  long d;
  long p;
  long ci, cj;
  long di, dj;
  long fi, fj;
  long pi, pj;
  long limit;
  long i, j;
  long *va;

  for(j = colStart; j <= colEnd; ++j)
  {
    CC[j] = 0;
    RR[j] = rowStart - 1;
    EE[j] = j;
    DD[j] = -(Q);
    SS[j] = rowStart - 1;
    FF[j] = j;
  }

  for(i = rowStart; i <= rowEnd; ++i)
  {
    c = 0;
    f = -(Q);
    ci = fi = i;
    va = context.scoreMatrix[A[i]];
    p = 0;
    pi = i - 1;
    cj = fj = pj = colStart - 1;
    limit = colEnd;
    for(j = colStart; j <= limit; ++j)
    {
      f = f - R;
      c = c - Q - R;
      orderSimState(f, fi, fj, c, ci, cj);
      c = CC[j] - Q - R;
      ci = RR[j];
      cj = EE[j];
      d = DD[j] - R;
      di = SS[j];
      dj = FF[j];
      orderSimState(d, di, dj, c, ci, cj);
      c = 0;
      if(simDiagonalAvailable(context.workspace, i, j))
      {
        c = p + va[B[j]];
      }
      if(c <= 0)
      {
        c = 0;
        ci = i;
        cj = j;
      }
      else
      {
        ci = pi;
        cj = pj;
      }
      orderSimState(c, ci, cj, d, di, dj);
      orderSimState(c, ci, cj, f, fi, fj);
      p = CC[j];
      CC[j] = c;
      pi = RR[j];
      pj = EE[j];
      RR[j] = ci;
      EE[j] = cj;
      DD[j] = d;
      SS[j] = di;
      FF[j] = dj;
      if(c > eventScoreFloor)
      {
        onEvent(SimInitialCellEvent(c, ci, cj, i, j));
      }
    }
  }
}

template <typename EventHandler>
inline void enumerateSimCandidateRegionWavefrontWide(const char *A,
                                                     const char *B,
                                                     long rowStart,
                                                     long rowEnd,
                                                     long colStart,
                                                     long colEnd,
                                                     long eventScoreFloor,
                                                     SimKernelContext &context,
                                                     EventHandler onEvent)
{
  if(rowStart > rowEnd || colStart > colEnd)
  {
    return;
  }

  const long Q = context.gapOpen;
  const long R = context.gapExtend;
  const long boundaryRow = rowStart - 1;
  const long boundaryCol = colStart - 1;
  static thread_local vector< vector<SimInitialCellEvent> > rowEventsScratch;
  static thread_local SimWavefrontDiagonal prevPrevScratch;
  static thread_local SimWavefrontDiagonal prevScratch;
  static thread_local SimWavefrontDiagonal curScratch;
  if(rowEventsScratch.size() < static_cast<size_t>(rowEnd + 1))
  {
    rowEventsScratch.resize(static_cast<size_t>(rowEnd + 1));
  }
  for(long row = rowStart; row <= rowEnd; ++row)
  {
    rowEventsScratch[static_cast<size_t>(row)].clear();
  }
  vector< vector<SimInitialCellEvent> > &rowEvents = rowEventsScratch;
  SimWavefrontDiagonal &prevPrev = prevPrevScratch;
  SimWavefrontDiagonal &prev = prevScratch;
  SimWavefrontDiagonal &cur = curScratch;
  prevPrev.clearRetainingCapacity();
  prev.clearRetainingCapacity();
  cur.clearRetainingCapacity();

  ensureSimWavefrontSubstitutionProfiles(A,B,context);

  const auto finalizeWavefrontLane = [&](long i,
                                         long j,
                                         size_t curIndex,
                                         long leftH,long leftHi,long leftHj,long leftF,long leftFi,long leftFj,
                                         long upH,long upHi,long upHj,long upD,long upDi,long upDj,
                                         long diagHi,long diagHj,
                                         int fMaxScore,
                                         int dMaxScore,
                                         int hDiagScore)
  {
    long f = leftF - R;
    long fi = leftFi;
    long fj = leftFj;
    long candidateScore = leftH - Q - R;
    long candidateI = leftHi;
    long candidateJ = leftHj;
    orderSimState(f, fi, fj, candidateScore, candidateI, candidateJ);
    cur.F[curIndex] = static_cast<int>(f == fMaxScore ? fMaxScore : f);
    cur.Fi[curIndex] = fi;
    cur.Fj[curIndex] = fj;

    long d = upD - R;
    long di = upDi;
    long dj = upDj;
    candidateScore = upH - Q - R;
    candidateI = upHi;
    candidateJ = upHj;
    orderSimState(d, di, dj, candidateScore, candidateI, candidateJ);
    cur.D[curIndex] = static_cast<int>(d == dMaxScore ? dMaxScore : d);
    cur.Di[curIndex] = di;
    cur.Dj[curIndex] = dj;

    long h = hDiagScore;
    long hi;
    long hj;
    if(h <= 0)
    {
      h = 0;
      hi = i;
      hj = j;
    }
    else
    {
      hi = diagHi;
      hj = diagHj;
    }
    orderSimState(h, hi, hj, d, di, dj);
    orderSimState(h, hi, hj, f, fi, fj);
    cur.H[curIndex] = static_cast<int>(h);
    cur.Hi[curIndex] = hi;
    cur.Hj[curIndex] = hj;

    if(h > eventScoreFloor)
    {
      rowEvents[i].emplace_back(h, hi, hj, i, j);
    }
  };

  for(long diagonal = rowStart + colStart; diagonal <= rowEnd + colEnd; ++diagonal)
  {
    const long startI = max(rowStart, diagonal - colEnd);
    const long endI = min(rowEnd, diagonal - colStart);
    const long profileStartI = context.wavefrontSubstitutionStartI[static_cast<size_t>(diagonal)];
    const vector<int> &profileScore = context.wavefrontSubstitutionScores[static_cast<size_t>(diagonal)];
    cur.reset(startI,endI);
#if defined(__SSE2__)
    long i = startI;
#if defined(__AVX2__)
	    const __m256i gapExtendVec256 = _mm256_set1_epi32(static_cast<int>(R));
	    const __m256i gapOpenExtendVec256 = _mm256_set1_epi32(static_cast<int>(Q + R));
	    for(; i + 7 <= endI; i += 8)
	    {
	      int leftHScore[8];
	      int leftFScore[8];
	      int upHScore[8];
	      int upDScore[8];
	      int diagHScore[8];
	      long leftHi[8], leftHj[8], leftFi[8], leftFj[8];
	      long upHi[8], upHj[8], upDi[8], upDj[8];
	      long diagHi[8], diagHj[8];
	      long rowI[8], rowJ[8];
	      size_t curIndices[8];
	      bool diagAvailable[8];

	      const size_t curBaseIndex = static_cast<size_t>(i - startI);
	      for(int lane = 0; lane < 8; ++lane)
	      {
	        const long ii = i + lane;
	        const long jj = diagonal - ii;
	        rowI[lane] = ii;
	        rowJ[lane] = jj;
	        curIndices[lane] = curBaseIndex + static_cast<size_t>(lane);
	        diagAvailable[lane] = simDiagonalAvailable(context.workspace, ii, jj);
	      }

	      const bool prevHasLeftRange = prev.contains(i) && prev.contains(i + 7);
	      if(prevHasLeftRange)
	      {
	        const size_t prevIndexBase = prev.index(i);
	        _mm256_storeu_si256(reinterpret_cast<__m256i *>(leftHScore),
	                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.H.data() + prevIndexBase)));
	        _mm256_storeu_si256(reinterpret_cast<__m256i *>(leftFScore),
	                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.F.data() + prevIndexBase)));
	        memcpy(leftHi, prev.Hi.data() + prevIndexBase, 8 * sizeof(long));
	        memcpy(leftHj, prev.Hj.data() + prevIndexBase, 8 * sizeof(long));
	        memcpy(leftFi, prev.Fi.data() + prevIndexBase, 8 * sizeof(long));
	        memcpy(leftFj, prev.Fj.data() + prevIndexBase, 8 * sizeof(long));
	      }
	      else
	      {
	        for(int lane = 0; lane < 8; ++lane)
	        {
	          const long ii = rowI[lane];
	          leftHScore[lane] = 0;
	          leftHi[lane] = ii;
	          leftHj[lane] = boundaryCol;
	          leftFScore[lane] = static_cast<int>(-(Q));
	          leftFi[lane] = ii;
	          leftFj[lane] = boundaryCol;
	          if(prev.contains(ii))
	          {
	            const size_t prevIndex = prev.index(ii);
	            leftHScore[lane] = prev.H[prevIndex];
	            leftHi[lane] = prev.Hi[prevIndex];
	            leftHj[lane] = prev.Hj[prevIndex];
	            leftFScore[lane] = prev.F[prevIndex];
	            leftFi[lane] = prev.Fi[prevIndex];
	            leftFj[lane] = prev.Fj[prevIndex];
	          }
	        }
	      }

	      const bool prevHasUpRange = prev.contains(i - 1) && prev.contains(i + 6);
	      if(prevHasUpRange)
	      {
	        const size_t prevIndexBase = prev.index(i - 1);
	        _mm256_storeu_si256(reinterpret_cast<__m256i *>(upHScore),
	                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.H.data() + prevIndexBase)));
	        _mm256_storeu_si256(reinterpret_cast<__m256i *>(upDScore),
	                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.D.data() + prevIndexBase)));
	        memcpy(upHi, prev.Hi.data() + prevIndexBase, 8 * sizeof(long));
	        memcpy(upHj, prev.Hj.data() + prevIndexBase, 8 * sizeof(long));
	        memcpy(upDi, prev.Di.data() + prevIndexBase, 8 * sizeof(long));
	        memcpy(upDj, prev.Dj.data() + prevIndexBase, 8 * sizeof(long));
	      }
	      else
	      {
	        for(int lane = 0; lane < 8; ++lane)
	        {
	          const long ii = rowI[lane];
	          const long jj = rowJ[lane];
	          upHScore[lane] = 0;
	          upHi[lane] = boundaryRow;
	          upHj[lane] = jj;
	          upDScore[lane] = static_cast<int>(-(Q));
	          upDi[lane] = boundaryRow;
	          upDj[lane] = jj;
	          if(prev.contains(ii - 1))
	          {
	            const size_t prevIndex = prev.index(ii - 1);
	            upHScore[lane] = prev.H[prevIndex];
	            upHi[lane] = prev.Hi[prevIndex];
	            upHj[lane] = prev.Hj[prevIndex];
	            upDScore[lane] = prev.D[prevIndex];
	            upDi[lane] = prev.Di[prevIndex];
	            upDj[lane] = prev.Dj[prevIndex];
	          }
	        }
	      }

	      const bool prevPrevHasDiagRange = prevPrev.contains(i - 1) && prevPrev.contains(i + 6);
	      if(prevPrevHasDiagRange)
	      {
	        const size_t prevPrevIndexBase = prevPrev.index(i - 1);
	        _mm256_storeu_si256(reinterpret_cast<__m256i *>(diagHScore),
	                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prevPrev.H.data() + prevPrevIndexBase)));
	        memcpy(diagHi, prevPrev.Hi.data() + prevPrevIndexBase, 8 * sizeof(long));
	        memcpy(diagHj, prevPrev.Hj.data() + prevPrevIndexBase, 8 * sizeof(long));
	      }
	      else
	      {
	        for(int lane = 0; lane < 8; ++lane)
	        {
	          const long ii = rowI[lane];
	          const long jj = rowJ[lane];
	          diagHScore[lane] = 0;
	          diagHi[lane] = ii - 1;
	          diagHj[lane] = jj - 1;
	          if(prevPrev.contains(ii - 1))
	          {
	            const size_t prevPrevIndex = prevPrev.index(ii - 1);
	            diagHScore[lane] = prevPrev.H[prevPrevIndex];
	            diagHi[lane] = prevPrev.Hi[prevPrevIndex];
	            diagHj[lane] = prevPrev.Hj[prevPrevIndex];
	          }
	        }
	      }

	      const __m256i leftHVec = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(leftHScore));
	      const __m256i leftFVec = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(leftFScore));
	      const __m256i upHVec = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(upHScore));
	      const __m256i upDVec = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(upDScore));
	      const __m256i diagHVec = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(diagHScore));
	      const __m256i substitutionVec = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(profileScore.data() + static_cast<size_t>(i - profileStartI)));

      const __m256i fScoreVec = simMaxEpi32Avx2(_mm256_sub_epi32(leftFVec, gapExtendVec256), _mm256_sub_epi32(leftHVec, gapOpenExtendVec256));
      const __m256i dScoreVec = simMaxEpi32Avx2(_mm256_sub_epi32(upDVec, gapExtendVec256), _mm256_sub_epi32(upHVec, gapOpenExtendVec256));
      const __m256i hDiagScoreVec = _mm256_add_epi32(diagHVec, substitutionVec);

      int fMaxScore[8];
      int dMaxScore[8];
      int hDiagScore[8];
      _mm256_storeu_si256(reinterpret_cast<__m256i *>(fMaxScore), fScoreVec);
      _mm256_storeu_si256(reinterpret_cast<__m256i *>(dMaxScore), dScoreVec);
      _mm256_storeu_si256(reinterpret_cast<__m256i *>(hDiagScore), hDiagScoreVec);

      for(int lane = 0; lane < 8; ++lane)
      {
        if(!diagAvailable[lane])
        {
          hDiagScore[lane] = 0;
        }
        finalizeWavefrontLane(rowI[lane],rowJ[lane],curIndices[lane],
                              leftHScore[lane],leftHi[lane],leftHj[lane],leftFScore[lane],leftFi[lane],leftFj[lane],
                              upHScore[lane],upHi[lane],upHj[lane],upDScore[lane],upDi[lane],upDj[lane],
                              diagHi[lane],diagHj[lane],fMaxScore[lane],dMaxScore[lane],hDiagScore[lane]);
      }
    }
#endif
    const __m128i gapExtendVec = _mm_set1_epi32(static_cast<int>(R));
    const __m128i gapOpenExtendVec = _mm_set1_epi32(static_cast<int>(Q + R));
	    for(; i + 3 <= endI; i += 4)
	    {
	      int leftHScore[4];
	      int leftFScore[4];
	      int upHScore[4];
	      int upDScore[4];
	      int diagHScore[4];
	      long leftHi[4], leftHj[4], leftFi[4], leftFj[4];
	      long upHi[4], upHj[4], upDi[4], upDj[4];
	      long diagHi[4], diagHj[4];
	      long rowI[4], rowJ[4];
	      size_t curIndices[4];
	      bool diagAvailable[4];

	      const size_t curBaseIndex = static_cast<size_t>(i - startI);
	      for(int lane = 0; lane < 4; ++lane)
	      {
	        const long ii = i + lane;
	        const long jj = diagonal - ii;
	        rowI[lane] = ii;
	        rowJ[lane] = jj;
	        curIndices[lane] = curBaseIndex + static_cast<size_t>(lane);
	        diagAvailable[lane] = simDiagonalAvailable(context.workspace, ii, jj);
	      }

	      const bool prevHasLeftRange = prev.contains(i) && prev.contains(i + 3);
	      if(prevHasLeftRange)
	      {
	        const size_t prevIndexBase = prev.index(i);
	        _mm_storeu_si128(reinterpret_cast<__m128i *>(leftHScore),
	                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.H.data() + prevIndexBase)));
	        _mm_storeu_si128(reinterpret_cast<__m128i *>(leftFScore),
	                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.F.data() + prevIndexBase)));
	        memcpy(leftHi, prev.Hi.data() + prevIndexBase, 4 * sizeof(long));
	        memcpy(leftHj, prev.Hj.data() + prevIndexBase, 4 * sizeof(long));
	        memcpy(leftFi, prev.Fi.data() + prevIndexBase, 4 * sizeof(long));
	        memcpy(leftFj, prev.Fj.data() + prevIndexBase, 4 * sizeof(long));
	      }
	      else
	      {
	        for(int lane = 0; lane < 4; ++lane)
	        {
	          const long ii = rowI[lane];
	          leftHScore[lane] = 0;
	          leftHi[lane] = ii;
	          leftHj[lane] = boundaryCol;
	          leftFScore[lane] = static_cast<int>(-(Q));
	          leftFi[lane] = ii;
	          leftFj[lane] = boundaryCol;
	          if(prev.contains(ii))
	          {
	            const size_t prevIndex = prev.index(ii);
	            leftHScore[lane] = prev.H[prevIndex];
	            leftHi[lane] = prev.Hi[prevIndex];
	            leftHj[lane] = prev.Hj[prevIndex];
	            leftFScore[lane] = prev.F[prevIndex];
	            leftFi[lane] = prev.Fi[prevIndex];
	            leftFj[lane] = prev.Fj[prevIndex];
	          }
	        }
	      }

	      const bool prevHasUpRange = prev.contains(i - 1) && prev.contains(i + 2);
	      if(prevHasUpRange)
	      {
	        const size_t prevIndexBase = prev.index(i - 1);
	        _mm_storeu_si128(reinterpret_cast<__m128i *>(upHScore),
	                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.H.data() + prevIndexBase)));
	        _mm_storeu_si128(reinterpret_cast<__m128i *>(upDScore),
	                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.D.data() + prevIndexBase)));
	        memcpy(upHi, prev.Hi.data() + prevIndexBase, 4 * sizeof(long));
	        memcpy(upHj, prev.Hj.data() + prevIndexBase, 4 * sizeof(long));
	        memcpy(upDi, prev.Di.data() + prevIndexBase, 4 * sizeof(long));
	        memcpy(upDj, prev.Dj.data() + prevIndexBase, 4 * sizeof(long));
	      }
	      else
	      {
	        for(int lane = 0; lane < 4; ++lane)
	        {
	          const long ii = rowI[lane];
	          const long jj = rowJ[lane];
	          upHScore[lane] = 0;
	          upHi[lane] = boundaryRow;
	          upHj[lane] = jj;
	          upDScore[lane] = static_cast<int>(-(Q));
	          upDi[lane] = boundaryRow;
	          upDj[lane] = jj;
	          if(prev.contains(ii - 1))
	          {
	            const size_t prevIndex = prev.index(ii - 1);
	            upHScore[lane] = prev.H[prevIndex];
	            upHi[lane] = prev.Hi[prevIndex];
	            upHj[lane] = prev.Hj[prevIndex];
	            upDScore[lane] = prev.D[prevIndex];
	            upDi[lane] = prev.Di[prevIndex];
	            upDj[lane] = prev.Dj[prevIndex];
	          }
	        }
	      }

	      const bool prevPrevHasDiagRange = prevPrev.contains(i - 1) && prevPrev.contains(i + 2);
	      if(prevPrevHasDiagRange)
	      {
	        const size_t prevPrevIndexBase = prevPrev.index(i - 1);
	        _mm_storeu_si128(reinterpret_cast<__m128i *>(diagHScore),
	                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prevPrev.H.data() + prevPrevIndexBase)));
	        memcpy(diagHi, prevPrev.Hi.data() + prevPrevIndexBase, 4 * sizeof(long));
	        memcpy(diagHj, prevPrev.Hj.data() + prevPrevIndexBase, 4 * sizeof(long));
	      }
	      else
	      {
	        for(int lane = 0; lane < 4; ++lane)
	        {
	          const long ii = rowI[lane];
	          const long jj = rowJ[lane];
	          diagHScore[lane] = 0;
	          diagHi[lane] = ii - 1;
	          diagHj[lane] = jj - 1;
	          if(prevPrev.contains(ii - 1))
	          {
	            const size_t prevPrevIndex = prevPrev.index(ii - 1);
	            diagHScore[lane] = prevPrev.H[prevPrevIndex];
	            diagHi[lane] = prevPrev.Hi[prevPrevIndex];
	            diagHj[lane] = prevPrev.Hj[prevPrevIndex];
	          }
	        }
	      }

	      const __m128i leftHVec = _mm_loadu_si128(reinterpret_cast<const __m128i *>(leftHScore));
	      const __m128i leftFVec = _mm_loadu_si128(reinterpret_cast<const __m128i *>(leftFScore));
	      const __m128i upHVec = _mm_loadu_si128(reinterpret_cast<const __m128i *>(upHScore));
	      const __m128i upDVec = _mm_loadu_si128(reinterpret_cast<const __m128i *>(upDScore));
	      const __m128i diagHVec = _mm_loadu_si128(reinterpret_cast<const __m128i *>(diagHScore));
	      const __m128i substitutionVec = _mm_loadu_si128(reinterpret_cast<const __m128i *>(profileScore.data() + static_cast<size_t>(i - profileStartI)));

      const __m128i fScoreVec = simMaxEpi32(_mm_sub_epi32(leftFVec, gapExtendVec), _mm_sub_epi32(leftHVec, gapOpenExtendVec));
      const __m128i dScoreVec = simMaxEpi32(_mm_sub_epi32(upDVec, gapExtendVec), _mm_sub_epi32(upHVec, gapOpenExtendVec));
      const __m128i hDiagScoreVec = _mm_add_epi32(diagHVec, substitutionVec);

      int fMaxScore[4];
      int dMaxScore[4];
      int hDiagScore[4];
      _mm_storeu_si128(reinterpret_cast<__m128i *>(fMaxScore), fScoreVec);
      _mm_storeu_si128(reinterpret_cast<__m128i *>(dMaxScore), dScoreVec);
      _mm_storeu_si128(reinterpret_cast<__m128i *>(hDiagScore), hDiagScoreVec);

      for(int lane = 0; lane < 4; ++lane)
      {
        if(!diagAvailable[lane])
        {
          hDiagScore[lane] = 0;
        }
        finalizeWavefrontLane(rowI[lane],rowJ[lane],curIndices[lane],
                              leftHScore[lane],leftHi[lane],leftHj[lane],leftFScore[lane],leftFi[lane],leftFj[lane],
                              upHScore[lane],upHi[lane],upHj[lane],upDScore[lane],upDi[lane],upDj[lane],
                              diagHi[lane],diagHj[lane],fMaxScore[lane],dMaxScore[lane],hDiagScore[lane]);
      }
    }
    for(; i <= endI; ++i)
#else
    for(long i = startI; i <= endI; ++i)
#endif
    {
      const long j = diagonal - i;
      const size_t curIndex = cur.index(i);
      const bool diagAvailable = simDiagonalAvailable(context.workspace, i, j);

      long leftH = 0;
      long leftHi = i;
      long leftHj = boundaryCol;
      long leftF = -(Q);
      long leftFi = i;
      long leftFj = boundaryCol;
      if(prev.contains(i))
      {
        const size_t prevIndex = prev.index(i);
        leftH = prev.H[prevIndex];
        leftHi = prev.Hi[prevIndex];
        leftHj = prev.Hj[prevIndex];
        leftF = prev.F[prevIndex];
        leftFi = prev.Fi[prevIndex];
        leftFj = prev.Fj[prevIndex];
      }

      long upH = 0;
      long upHi = boundaryRow;
      long upHj = j;
      long upD = -(Q);
      long upDi = boundaryRow;
      long upDj = j;
      if(prev.contains(i - 1))
      {
        const size_t prevIndex = prev.index(i - 1);
        upH = prev.H[prevIndex];
        upHi = prev.Hi[prevIndex];
        upHj = prev.Hj[prevIndex];
        upD = prev.D[prevIndex];
        upDi = prev.Di[prevIndex];
        upDj = prev.Dj[prevIndex];
      }

      long diagHi = i - 1;
      long diagHj = j - 1;
      int hDiagScore = profileScore[static_cast<size_t>(i - profileStartI)];
      if(prevPrev.contains(i - 1))
      {
        const size_t prevPrevIndex = prevPrev.index(i - 1);
        hDiagScore += prevPrev.H[prevPrevIndex];
        diagHi = prevPrev.Hi[prevPrevIndex];
        diagHj = prevPrev.Hj[prevPrevIndex];
      }
      if(!diagAvailable)
      {
        hDiagScore = 0;
      }

      finalizeWavefrontLane(i,j,curIndex,
                            leftH,leftHi,leftHj,leftF,leftFi,leftFj,
                            upH,upHi,upHj,upD,upDi,upDj,
                            diagHi,diagHj,0,0,hDiagScore);
    }
    const long flushRow = diagonal - colEnd;
    if(flushRow >= rowStart && flushRow <= rowEnd)
    {
      vector<SimInitialCellEvent> &completedRowEvents = rowEvents[static_cast<size_t>(flushRow)];
      for(size_t eventIndex = 0; eventIndex < completedRowEvents.size(); ++eventIndex)
      {
        onEvent(completedRowEvents[eventIndex]);
      }
      completedRowEvents.clear();
    }
    std::swap(prevPrev, prev);
    std::swap(prev, cur);
	  }
	}

	template <typename EventHandler>
	inline void enumerateSimCandidateRegionWavefrontPacked(const char *A,
	                                                       const char *B,
	                                                       long rowStart,
	                                                       long rowEnd,
	                                                       long colStart,
	                                                       long colEnd,
	                                                       long eventScoreFloor,
	                                                       SimKernelContext &context,
	                                                       EventHandler onEvent)
	{
	  if(rowStart > rowEnd || colStart > colEnd)
	  {
	    return;
	  }

	  const long Q = context.gapOpen;
	  const long R = context.gapExtend;
	  const uint32_t boundaryRow = static_cast<uint32_t>(rowStart - 1);
	  const uint32_t boundaryCol = static_cast<uint32_t>(colStart - 1);
	  static thread_local vector< vector<SimWavefrontRowEventPacked> > rowEventsScratch;
	  static thread_local SimWavefrontDiagonalPacked prevPrevScratch;
	  static thread_local SimWavefrontDiagonalPacked prevScratch;
	  static thread_local SimWavefrontDiagonalPacked curScratch;
	  if(rowEventsScratch.size() < static_cast<size_t>(rowEnd + 1))
	  {
	    rowEventsScratch.resize(static_cast<size_t>(rowEnd + 1));
	  }
	  for(long row = rowStart; row <= rowEnd; ++row)
	  {
	    rowEventsScratch[static_cast<size_t>(row)].clear();
	  }
	  vector< vector<SimWavefrontRowEventPacked> > &rowEvents = rowEventsScratch;
	  SimWavefrontDiagonalPacked &prevPrev = prevPrevScratch;
	  SimWavefrontDiagonalPacked &prev = prevScratch;
	  SimWavefrontDiagonalPacked &cur = curScratch;
	  prevPrev.clearRetainingCapacity();
	  prev.clearRetainingCapacity();
	  cur.clearRetainingCapacity();

	  ensureSimWavefrontSubstitutionProfiles(A,B,context);

	  const auto finalizeWavefrontLane = [&](long i,
	                                         long j,
	                                         size_t curIndex,
	                                         long leftH,uint64_t leftHc,long leftF,uint64_t leftFc,
	                                         long upH,uint64_t upHc,long upD,uint64_t upDc,
	                                         uint64_t diagHc,
	                                         int fMaxScore,
	                                         int dMaxScore,
	                                         int hDiagScore)
	  {
	    long f = leftF - R;
	    uint64_t fc = leftFc;
	    long candidateScore = leftH - Q - R;
	    uint64_t candidateCoord = leftHc;
	    orderSimStatePacked(f, fc, candidateScore, candidateCoord);
	    cur.F[curIndex] = static_cast<int>(f == fMaxScore ? fMaxScore : f);
	    cur.Fc[curIndex] = fc;

	    long d = upD - R;
	    uint64_t dc = upDc;
	    candidateScore = upH - Q - R;
	    candidateCoord = upHc;
	    orderSimStatePacked(d, dc, candidateScore, candidateCoord);
	    cur.D[curIndex] = static_cast<int>(d == dMaxScore ? dMaxScore : d);
	    cur.Dc[curIndex] = dc;

	    long h = hDiagScore;
	    uint64_t hc;
	    if(h <= 0)
	    {
	      h = 0;
	      hc = packSimCoord(static_cast<uint32_t>(i), static_cast<uint32_t>(j));
	    }
	    else
	    {
	      hc = diagHc;
	    }
	    orderSimStatePacked(h, hc, d, dc);
	    orderSimStatePacked(h, hc, f, fc);
	    cur.H[curIndex] = static_cast<int>(h);
	    cur.Hc[curIndex] = hc;

	    if(h > eventScoreFloor)
	    {
	      rowEvents[i].emplace_back(static_cast<int>(h), hc, static_cast<uint32_t>(j));
	    }
	  };

	  for(long diagonal = rowStart + colStart; diagonal <= rowEnd + colEnd; ++diagonal)
	  {
	    const long startI = max(rowStart, diagonal - colEnd);
	    const long endI = min(rowEnd, diagonal - colStart);
	    const long profileStartI = context.wavefrontSubstitutionStartI[static_cast<size_t>(diagonal)];
	    const vector<int> &profileScore = context.wavefrontSubstitutionScores[static_cast<size_t>(diagonal)];
	    cur.reset(startI,endI);
	#if defined(__SSE2__)
	    long i = startI;
	#if defined(__AVX2__)
		    const __m256i gapExtendVec256 = _mm256_set1_epi32(static_cast<int>(R));
		    const __m256i gapOpenExtendVec256 = _mm256_set1_epi32(static_cast<int>(Q + R));
		    for(; i + 7 <= endI; i += 8)
		    {
		      int leftHScore[8];
		      int leftFScore[8];
		      int upHScore[8];
		      int upDScore[8];
		      int diagHScore[8];
		      uint64_t leftHCoord[8], leftFCoord[8];
		      uint64_t upHCoord[8], upDCoord[8];
		      uint64_t diagHCoord[8];
		      long rowI[8], rowJ[8];
		      size_t curIndices[8];
		      bool diagAvailable[8];

		      const size_t curBaseIndex = static_cast<size_t>(i - startI);
		      for(int lane = 0; lane < 8; ++lane)
		      {
		        const long ii = i + lane;
		        const long jj = diagonal - ii;
		        rowI[lane] = ii;
		        rowJ[lane] = jj;
		        curIndices[lane] = curBaseIndex + static_cast<size_t>(lane);
		        diagAvailable[lane] = simDiagonalAvailable(context.workspace, ii, jj);
		      }

		      const bool prevHasLeftRange = prev.contains(i) && prev.contains(i + 7);
			      if(prevHasLeftRange)
			      {
			        const size_t prevIndexBase = prev.index(i);
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(leftHScore),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.H.data() + prevIndexBase)));
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(leftFScore),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.F.data() + prevIndexBase)));
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(leftHCoord),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.Hc.data() + prevIndexBase)));
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(leftHCoord + 4),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.Hc.data() + prevIndexBase + 4)));
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(leftFCoord),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.Fc.data() + prevIndexBase)));
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(leftFCoord + 4),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.Fc.data() + prevIndexBase + 4)));
			      }
		      else
		      {
		        for(int lane = 0; lane < 8; ++lane)
		        {
		          const long ii = rowI[lane];
		          leftHScore[lane] = 0;
		          leftHCoord[lane] = packSimCoord(static_cast<uint32_t>(ii), boundaryCol);
		          leftFScore[lane] = static_cast<int>(-(Q));
		          leftFCoord[lane] = packSimCoord(static_cast<uint32_t>(ii), boundaryCol);
		          if(prev.contains(ii))
		          {
		            const size_t prevIndex = prev.index(ii);
		            leftHScore[lane] = prev.H[prevIndex];
		            leftHCoord[lane] = prev.Hc[prevIndex];
		            leftFScore[lane] = prev.F[prevIndex];
		            leftFCoord[lane] = prev.Fc[prevIndex];
		          }
		        }
		      }

		      const bool prevHasUpRange = prev.contains(i - 1) && prev.contains(i + 6);
			      if(prevHasUpRange)
			      {
			        const size_t prevIndexBase = prev.index(i - 1);
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(upHScore),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.H.data() + prevIndexBase)));
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(upDScore),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.D.data() + prevIndexBase)));
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(upHCoord),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.Hc.data() + prevIndexBase)));
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(upHCoord + 4),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.Hc.data() + prevIndexBase + 4)));
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(upDCoord),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.Dc.data() + prevIndexBase)));
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(upDCoord + 4),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prev.Dc.data() + prevIndexBase + 4)));
			      }
		      else
		      {
		        for(int lane = 0; lane < 8; ++lane)
		        {
		          const long ii = rowI[lane];
		          const long jj = rowJ[lane];
		          upHScore[lane] = 0;
		          upHCoord[lane] = packSimCoord(boundaryRow, static_cast<uint32_t>(jj));
		          upDScore[lane] = static_cast<int>(-(Q));
		          upDCoord[lane] = packSimCoord(boundaryRow, static_cast<uint32_t>(jj));
		          if(prev.contains(ii - 1))
		          {
		            const size_t prevIndex = prev.index(ii - 1);
		            upHScore[lane] = prev.H[prevIndex];
		            upHCoord[lane] = prev.Hc[prevIndex];
		            upDScore[lane] = prev.D[prevIndex];
		            upDCoord[lane] = prev.Dc[prevIndex];
		          }
		        }
		      }

		      const bool prevPrevHasDiagRange = prevPrev.contains(i - 1) && prevPrev.contains(i + 6);
			      if(prevPrevHasDiagRange)
			      {
			        const size_t prevPrevIndexBase = prevPrev.index(i - 1);
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(diagHScore),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prevPrev.H.data() + prevPrevIndexBase)));
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(diagHCoord),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prevPrev.Hc.data() + prevPrevIndexBase)));
			        _mm256_storeu_si256(reinterpret_cast<__m256i *>(diagHCoord + 4),
			                            _mm256_loadu_si256(reinterpret_cast<const __m256i *>(prevPrev.Hc.data() + prevPrevIndexBase + 4)));
			      }
		      else
		      {
		        for(int lane = 0; lane < 8; ++lane)
		        {
		          const long ii = rowI[lane];
		          const long jj = rowJ[lane];
		          diagHScore[lane] = 0;
		          diagHCoord[lane] = packSimCoord(static_cast<uint32_t>(ii - 1), static_cast<uint32_t>(jj - 1));
		          if(prevPrev.contains(ii - 1))
		          {
		            const size_t prevPrevIndex = prevPrev.index(ii - 1);
		            diagHScore[lane] = prevPrev.H[prevPrevIndex];
		            diagHCoord[lane] = prevPrev.Hc[prevPrevIndex];
		          }
		        }
		      }

		      const __m256i leftHVec = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(leftHScore));
		      const __m256i leftFVec = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(leftFScore));
		      const __m256i upHVec = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(upHScore));
		      const __m256i upDVec = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(upDScore));
		      const __m256i diagHVec = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(diagHScore));
		      const __m256i substitutionVec = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(profileScore.data() + static_cast<size_t>(i - profileStartI)));

	      const __m256i fScoreVec = simMaxEpi32Avx2(_mm256_sub_epi32(leftFVec, gapExtendVec256), _mm256_sub_epi32(leftHVec, gapOpenExtendVec256));
	      const __m256i dScoreVec = simMaxEpi32Avx2(_mm256_sub_epi32(upDVec, gapExtendVec256), _mm256_sub_epi32(upHVec, gapOpenExtendVec256));
	      const __m256i hDiagScoreVec = _mm256_add_epi32(diagHVec, substitutionVec);

	      int fMaxScore[8];
	      int dMaxScore[8];
	      int hDiagScore2[8];
	      _mm256_storeu_si256(reinterpret_cast<__m256i *>(fMaxScore), fScoreVec);
	      _mm256_storeu_si256(reinterpret_cast<__m256i *>(dMaxScore), dScoreVec);
	      _mm256_storeu_si256(reinterpret_cast<__m256i *>(hDiagScore2), hDiagScoreVec);

	      for(int lane = 0; lane < 8; ++lane)
	      {
	        if(!diagAvailable[lane])
	        {
	          hDiagScore2[lane] = 0;
	        }
	        finalizeWavefrontLane(rowI[lane],rowJ[lane],curIndices[lane],
	                              leftHScore[lane],leftHCoord[lane],leftFScore[lane],leftFCoord[lane],
	                              upHScore[lane],upHCoord[lane],upDScore[lane],upDCoord[lane],
	                              diagHCoord[lane],fMaxScore[lane],dMaxScore[lane],hDiagScore2[lane]);
	      }
	    }
	#endif
	    const __m128i gapExtendVec = _mm_set1_epi32(static_cast<int>(R));
	    const __m128i gapOpenExtendVec = _mm_set1_epi32(static_cast<int>(Q + R));
		    for(; i + 3 <= endI; i += 4)
		    {
		      int leftHScore[4];
		      int leftFScore[4];
		      int upHScore[4];
		      int upDScore[4];
		      int diagHScore[4];
		      uint64_t leftHCoord[4], leftFCoord[4];
		      uint64_t upHCoord[4], upDCoord[4];
		      uint64_t diagHCoord[4];
		      long rowI[4], rowJ[4];
		      size_t curIndices[4];
		      bool diagAvailable[4];

		      const size_t curBaseIndex = static_cast<size_t>(i - startI);
		      for(int lane = 0; lane < 4; ++lane)
		      {
		        const long ii = i + lane;
		        const long jj = diagonal - ii;
		        rowI[lane] = ii;
		        rowJ[lane] = jj;
		        curIndices[lane] = curBaseIndex + static_cast<size_t>(lane);
		        diagAvailable[lane] = simDiagonalAvailable(context.workspace, ii, jj);
		      }

		      const bool prevHasLeftRange = prev.contains(i) && prev.contains(i + 3);
			      if(prevHasLeftRange)
			      {
			        const size_t prevIndexBase = prev.index(i);
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(leftHScore),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.H.data() + prevIndexBase)));
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(leftFScore),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.F.data() + prevIndexBase)));
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(leftHCoord),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.Hc.data() + prevIndexBase)));
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(leftHCoord + 2),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.Hc.data() + prevIndexBase + 2)));
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(leftFCoord),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.Fc.data() + prevIndexBase)));
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(leftFCoord + 2),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.Fc.data() + prevIndexBase + 2)));
			      }
		      else
		      {
		        for(int lane = 0; lane < 4; ++lane)
		        {
		          const long ii = rowI[lane];
		          leftHScore[lane] = 0;
		          leftHCoord[lane] = packSimCoord(static_cast<uint32_t>(ii), boundaryCol);
		          leftFScore[lane] = static_cast<int>(-(Q));
		          leftFCoord[lane] = packSimCoord(static_cast<uint32_t>(ii), boundaryCol);
		          if(prev.contains(ii))
		          {
		            const size_t prevIndex = prev.index(ii);
		            leftHScore[lane] = prev.H[prevIndex];
		            leftHCoord[lane] = prev.Hc[prevIndex];
		            leftFScore[lane] = prev.F[prevIndex];
		            leftFCoord[lane] = prev.Fc[prevIndex];
		          }
		        }
		      }

		      const bool prevHasUpRange = prev.contains(i - 1) && prev.contains(i + 2);
			      if(prevHasUpRange)
			      {
			        const size_t prevIndexBase = prev.index(i - 1);
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(upHScore),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.H.data() + prevIndexBase)));
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(upDScore),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.D.data() + prevIndexBase)));
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(upHCoord),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.Hc.data() + prevIndexBase)));
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(upHCoord + 2),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.Hc.data() + prevIndexBase + 2)));
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(upDCoord),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.Dc.data() + prevIndexBase)));
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(upDCoord + 2),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prev.Dc.data() + prevIndexBase + 2)));
			      }
		      else
		      {
		        for(int lane = 0; lane < 4; ++lane)
		        {
		          const long ii = rowI[lane];
		          const long jj = rowJ[lane];
		          upHScore[lane] = 0;
		          upHCoord[lane] = packSimCoord(boundaryRow, static_cast<uint32_t>(jj));
		          upDScore[lane] = static_cast<int>(-(Q));
		          upDCoord[lane] = packSimCoord(boundaryRow, static_cast<uint32_t>(jj));
		          if(prev.contains(ii - 1))
		          {
		            const size_t prevIndex = prev.index(ii - 1);
		            upHScore[lane] = prev.H[prevIndex];
		            upHCoord[lane] = prev.Hc[prevIndex];
		            upDScore[lane] = prev.D[prevIndex];
		            upDCoord[lane] = prev.Dc[prevIndex];
		          }
		        }
		      }

		      const bool prevPrevHasDiagRange = prevPrev.contains(i - 1) && prevPrev.contains(i + 2);
			      if(prevPrevHasDiagRange)
			      {
			        const size_t prevPrevIndexBase = prevPrev.index(i - 1);
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(diagHScore),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prevPrev.H.data() + prevPrevIndexBase)));
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(diagHCoord),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prevPrev.Hc.data() + prevPrevIndexBase)));
			        _mm_storeu_si128(reinterpret_cast<__m128i *>(diagHCoord + 2),
			                         _mm_loadu_si128(reinterpret_cast<const __m128i *>(prevPrev.Hc.data() + prevPrevIndexBase + 2)));
			      }
		      else
		      {
		        for(int lane = 0; lane < 4; ++lane)
		        {
		          const long ii = rowI[lane];
		          const long jj = rowJ[lane];
		          diagHScore[lane] = 0;
		          diagHCoord[lane] = packSimCoord(static_cast<uint32_t>(ii - 1), static_cast<uint32_t>(jj - 1));
		          if(prevPrev.contains(ii - 1))
		          {
		            const size_t prevPrevIndex = prevPrev.index(ii - 1);
		            diagHScore[lane] = prevPrev.H[prevPrevIndex];
		            diagHCoord[lane] = prevPrev.Hc[prevPrevIndex];
		          }
		        }
		      }

		      const __m128i leftHVec = _mm_loadu_si128(reinterpret_cast<const __m128i *>(leftHScore));
		      const __m128i leftFVec = _mm_loadu_si128(reinterpret_cast<const __m128i *>(leftFScore));
		      const __m128i upHVec = _mm_loadu_si128(reinterpret_cast<const __m128i *>(upHScore));
		      const __m128i upDVec = _mm_loadu_si128(reinterpret_cast<const __m128i *>(upDScore));
		      const __m128i diagHVec = _mm_loadu_si128(reinterpret_cast<const __m128i *>(diagHScore));
		      const __m128i substitutionVec = _mm_loadu_si128(reinterpret_cast<const __m128i *>(profileScore.data() + static_cast<size_t>(i - profileStartI)));

	      const __m128i fScoreVec = simMaxEpi32(_mm_sub_epi32(leftFVec, gapExtendVec), _mm_sub_epi32(leftHVec, gapOpenExtendVec));
	      const __m128i dScoreVec = simMaxEpi32(_mm_sub_epi32(upDVec, gapExtendVec), _mm_sub_epi32(upHVec, gapOpenExtendVec));
	      const __m128i hDiagScoreVec = _mm_add_epi32(diagHVec, substitutionVec);

	      int fMaxScore[4];
	      int dMaxScore[4];
	      int hDiagScore2[4];
	      _mm_storeu_si128(reinterpret_cast<__m128i *>(fMaxScore), fScoreVec);
	      _mm_storeu_si128(reinterpret_cast<__m128i *>(dMaxScore), dScoreVec);
	      _mm_storeu_si128(reinterpret_cast<__m128i *>(hDiagScore2), hDiagScoreVec);

	      for(int lane = 0; lane < 4; ++lane)
	      {
	        if(!diagAvailable[lane])
	        {
	          hDiagScore2[lane] = 0;
	        }
	        finalizeWavefrontLane(rowI[lane],rowJ[lane],curIndices[lane],
	                              leftHScore[lane],leftHCoord[lane],leftFScore[lane],leftFCoord[lane],
	                              upHScore[lane],upHCoord[lane],upDScore[lane],upDCoord[lane],
	                              diagHCoord[lane],fMaxScore[lane],dMaxScore[lane],hDiagScore2[lane]);
	      }
	    }
	    for(; i <= endI; ++i)
	#else
	    for(long i = startI; i <= endI; ++i)
	#endif
	    {
	      const long j = diagonal - i;
	      const size_t curIndex = cur.index(i);
	      const bool diagAvailable = simDiagonalAvailable(context.workspace, i, j);

	      long leftH = 0;
	      uint64_t leftHc = packSimCoord(static_cast<uint32_t>(i), boundaryCol);
	      long leftF = -(Q);
	      uint64_t leftFc = packSimCoord(static_cast<uint32_t>(i), boundaryCol);
	      if(prev.contains(i))
	      {
	        const size_t prevIndex = prev.index(i);
	        leftH = prev.H[prevIndex];
	        leftHc = prev.Hc[prevIndex];
	        leftF = prev.F[prevIndex];
	        leftFc = prev.Fc[prevIndex];
	      }

	      long upH = 0;
	      uint64_t upHc = packSimCoord(boundaryRow, static_cast<uint32_t>(j));
	      long upD = -(Q);
	      uint64_t upDc = packSimCoord(boundaryRow, static_cast<uint32_t>(j));
	      if(prev.contains(i - 1))
	      {
	        const size_t prevIndex = prev.index(i - 1);
	        upH = prev.H[prevIndex];
	        upHc = prev.Hc[prevIndex];
	        upD = prev.D[prevIndex];
	        upDc = prev.Dc[prevIndex];
	      }

	      uint64_t diagHc = packSimCoord(static_cast<uint32_t>(i - 1), static_cast<uint32_t>(j - 1));
	      int hDiagScore = profileScore[static_cast<size_t>(i - profileStartI)];
	      if(prevPrev.contains(i - 1))
	      {
	        const size_t prevPrevIndex = prevPrev.index(i - 1);
	        hDiagScore += prevPrev.H[prevPrevIndex];
	        diagHc = prevPrev.Hc[prevPrevIndex];
	      }
	      if(!diagAvailable)
	      {
	        hDiagScore = 0;
	      }

	      finalizeWavefrontLane(i,j,curIndex,
	                            leftH,leftHc,leftF,leftFc,
	                            upH,upHc,upD,upDc,
	                            diagHc,0,0,hDiagScore);
	    }
	    const long flushRow = diagonal - colEnd;
	    if(flushRow >= rowStart && flushRow <= rowEnd)
	    {
	      vector<SimWavefrontRowEventPacked> &completedRowEvents = rowEvents[static_cast<size_t>(flushRow)];
	      for(size_t eventIndex = 0; eventIndex < completedRowEvents.size(); ++eventIndex)
	      {
	        const SimWavefrontRowEventPacked &event = completedRowEvents[eventIndex];
	        const long startI = static_cast<long>(unpackSimCoordI(event.startCoord));
	        const long startJ = static_cast<long>(unpackSimCoordJ(event.startCoord));
	        onEvent(SimInitialCellEvent(static_cast<long>(event.score),
	                                   startI,
	                                   startJ,
	                                   flushRow,
	                                   static_cast<long>(event.endJ)));
	      }
	      completedRowEvents.clear();
	    }
	    std::swap(prevPrev, prev);
	    std::swap(prev, cur);
	  }
	}

	template <typename EventHandler>
	inline void enumerateSimCandidateRegionWavefront(const char *A,
	                                                 const char *B,
	                                                 long rowStart,
	                                                 long rowEnd,
	                                                 long colStart,
	                                                 long colEnd,
	                                                 long eventScoreFloor,
	                                                 SimKernelContext &context,
	                                                 EventHandler onEvent)
	{
	  if(rowStart > rowEnd || colStart > colEnd)
	  {
	    return;
	  }

	  const long boundaryRow = rowStart - 1;
	  const long boundaryCol = colStart - 1;
	  bool usePacked = boundaryRow >= 0 && boundaryCol >= 0;
	  usePacked = usePacked && rowStart >= 1 && colStart >= 1;
	  usePacked = usePacked &&
	              rowStart <= static_cast<long>(0xffffffffu) &&
	              colStart <= static_cast<long>(0xffffffffu) &&
	              rowEnd <= static_cast<long>(0xffffffffu) &&
	              colEnd <= static_cast<long>(0xffffffffu);
	  if(usePacked)
	  {
	    enumerateSimCandidateRegionWavefrontPacked(A,B,rowStart,rowEnd,colStart,colEnd,eventScoreFloor,context,onEvent);
	    return;
	  }
	  enumerateSimCandidateRegionWavefrontWide(A,B,rowStart,rowEnd,colStart,colEnd,eventScoreFloor,context,onEvent);
	}

template <typename EventHandler>
inline void enumerateSimCandidateRegion(const char *A,
                                        const char *B,
	                                        long rowStart,
                                        long rowEnd,
                                        long colStart,
                                        long colEnd,
                                        long eventScoreFloor,
                                        SimKernelContext &context,
                                        EventHandler onEvent)
{
  if(selectSimInitialScanBackend(context) == SIM_INITIAL_SCAN_WAVEFRONT)
  {
    enumerateSimCandidateRegionWavefront(A,B,rowStart,rowEnd,colStart,colEnd,eventScoreFloor,context,onEvent);
    return;
  }
  enumerateSimCandidateRegionRowMajor(A,B,rowStart,rowEnd,colStart,colEnd,eventScoreFloor,context,onEvent);
}

inline void applySimCudaInitialRunSummariesToContext(const vector<SimScanCudaInitialRunSummary> &summaries,
                                                     uint64_t eventCount,
                                                     SimKernelContext &context,
                                                     bool benchmarkEnabled);
inline void finalizeSimCudaInitialRunSummariesToContext(const vector<SimScanCudaInitialRunSummary> &summaries,
                                                        SimKernelContext &context,
                                                        bool benchmarkEnabled,
                                                        bool hostSafeStoreAlreadyUpdated,
                                                        bool hostSafeStoreAlreadyPruned = false);
struct SimBlockedWordsView
{
  SimBlockedWordsView():
    words(NULL),
    wordStart(0),
    wordCount(0),
    wordStride(0) {}

  const uint64_t *words;
  int wordStart;
  int wordCount;
  int wordStride;
};
inline SimBlockedWordsView makeSimBlockedWordsView(const SimWorkspace &workspace,
                                                   long rowStart,
                                                   long rowEnd,
                                                   long colStart,
                                                   long colEnd,
                                                   vector<uint64_t> &scratchDenseWords);
inline bool popHighestScoringSimCandidate(SimKernelContext &context,SimCandidate &candidate);
inline bool materializeSimCandidate(const SimRequest &request,
                                    const char *A,
                                    const char *B,
                                    long targetLength,
                                    long score,
                                    long stari,
                                    long starj,
                                    long endi,
                                    long endj,
                                    long rule,
                                    SimKernelContext &context,
                                    vector<struct triplex> &triplex_list);
inline bool materializeSimCandidateImpl(const SimRequest &request,
                                        const char *A,
                                        const char *B,
                                        long targetLength,
                                        long score,
                                        long stari,
                                        long starj,
                                        long endi,
                                        long endj,
                                        long rule,
                                        bool recordProposalPostTiming,
                                        bool allowTracebackCuda,
                                        SimKernelContext &context,
                                        vector<struct triplex> &triplex_list);
inline bool materializeSimProposalStates(const SimRequest &request,
                                         const char *A,
                                         const char *B,
                                         long targetLength,
                                         long rule,
                                         const vector<SimScanCudaCandidateState> &proposalStates,
                                         SimKernelContext &context,
                                         vector<struct triplex> &triplex_list);
inline void updateSimCandidatesAfterTraceback(const char *A,
                                              const char *B,
                                              long stari,
                                              long endi,
                                              long starj,
                                              long endj,
                                              long m1,
                                              long mm,
                                              long n1,
                                              long nn,
                                              SimKernelContext &context);
inline bool runSimCandidateLoopWithCudaLocateDeviceKLoop(const SimRequest &request,
                                                         const char *A,
                                                         const char *B,
                                                         long targetLength,
                                                         long rule,
                                                         SimKernelContext &context,
                                                         vector<struct triplex> &triplex_list);
inline void runSimCandidateLoop(const SimRequest &request,
                                const char *A,
                                const char *B,
                                long targetLength,
                                long rule,
                                SimKernelContext &context,
                                vector<struct triplex> &triplex_list);

	inline void enumerateInitialSimCandidates(const char *A,const char *B,long M,long N,long minScore,SimKernelContext &context)
	{
	  context.candidateCount = 0;
	  invalidateSimSafeCandidateStateStore(context);
	  clearSimCandidateStartIndex(context.candidateStartIndex);
	  context.candidateMinHeap.valid = false;
	  const bool benchmarkEnabled = simBenchmarkEnabledRuntime();
	  const std::chrono::steady_clock::time_point initialScanStart =
	    benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();

	  bool usedCuda = false;
	  uint64_t scanTaskCount = 1;
	  uint64_t scanLaunchCount = 1;
	  if(simInitialScanCudaEnabledRuntime() &&
	     sim_scan_cuda_is_built() &&
	     M > 0 &&
	     N > 0 &&
	     M <= 8192 &&
	     N <= 8192 &&
	     minScore <= static_cast<long>(0x7fffffff))
	  {
	    int scoreMatrixInt[128][128];
	    for(int i = 0; i < 128; ++i)
	    {
	      for(int j = 0; j < 128; ++j)
	      {
	        scoreMatrixInt[i][j] = static_cast<int>(context.scoreMatrix[i][j]);
	      }
	    }

	    SimScanCudaBatchResult cudaBatchResult;
	    string cudaError;
	    const int device = simCudaDeviceRuntime();
	    const bool proposalCandidates = simCudaInitialProposalRequestEnabledRuntime();
	    const bool reduceCandidates = simCudaInitialReduceRequestEnabledRuntime();
	    const bool persistInitialCandidateStatesOnDevice =
	      (simCudaInitialReducePersistOnDeviceRuntime() &&
	       !simCudaInitialOrderedSegmentedV3ShadowEnabledRuntime()) ||
	      simCudaInitialProposalResidencyEnabledRuntime();
	    const bool useInitialPinnedAsyncCpuPipeline =
	      !reduceCandidates &&
	      !proposalCandidates &&
	      simCudaInitialChunkedHandoffEnabledRuntime() &&
	      simCudaInitialPinnedAsyncHandoffEnabledRuntime() &&
	      simCudaInitialPinnedAsyncCpuPipelineEnabledRuntime();
	    SimInitialPinnedAsyncCpuPipelineApplyState initialCpuPipelineState;
	    vector<SimScanCudaRequest> cudaRequests(1);
	    cudaRequests[0].kind = SIM_SCAN_CUDA_REQUEST_INITIAL;
	    cudaRequests[0].A = A;
	    cudaRequests[0].B = B;
	    cudaRequests[0].queryLength = static_cast<int>(M);
	    cudaRequests[0].targetLength = static_cast<int>(N);
	    cudaRequests[0].gapOpen = static_cast<int>(context.gapOpen);
	    cudaRequests[0].gapExtend = static_cast<int>(context.gapExtend);
	    cudaRequests[0].scoreMatrix = scoreMatrixInt;
	    cudaRequests[0].eventScoreFloor = static_cast<int>(minScore);
	    cudaRequests[0].reduceCandidates = reduceCandidates;
	    cudaRequests[0].proposalCandidates = proposalCandidates;
	    cudaRequests[0].persistAllCandidateStatesOnDevice = persistInitialCandidateStatesOnDevice;
	    if(useInitialPinnedAsyncCpuPipeline)
	    {
	      const bool maintainSafeStore =
	        simLocateCudaModeRuntime() == SIM_LOCATE_CUDA_MODE_SAFE_WORKSET ||
	        simCudaProposalLoopEnabledRuntime();
	      beginSimInitialPinnedAsyncCpuPipelineApply(0,
	                                                context,
	                                                maintainSafeStore,
	                                                initialCpuPipelineState);
	      cudaRequests[0].initialSummaryChunkConsumer =
	        [&context,&initialCpuPipelineState](const SimScanCudaInitialSummaryChunk &chunk)
	        {
	          applySimInitialPinnedAsyncCpuPipelineChunk(chunk.summaries,
	                                                    chunk.batchIndex,
	                                                    chunk.chunkIndex,
	                                                    chunk.summaryBase,
	                                                    static_cast<size_t>(chunk.summaryCount),
	                                                    context,
	                                                    initialCpuPipelineState);
	        };
	    }
	    vector<SimScanCudaRequestResult> cudaResults;
		    if(sim_scan_cuda_init(device,&cudaError) &&
		       sim_scan_cuda_enumerate_events_row_major_batch(cudaRequests,
		                                                     &cudaResults,
		                                                     &cudaBatchResult,
		                                                     &cudaError) &&
	       cudaResults.size() == 1u)
	    {
	      usedCuda = true;
	      scanTaskCount = cudaBatchResult.taskCount;
	      scanLaunchCount = cudaBatchResult.launchCount;
        if(benchmarkEnabled)
	        {
	          recordSimInitialScanGpuNanoseconds(simSecondsToNanoseconds(cudaBatchResult.gpuSeconds));
	          recordSimInitialScanD2HNanoseconds(simSecondsToNanoseconds(cudaBatchResult.d2hSeconds));
	          recordSimInitialScanDiagNanoseconds(simSecondsToNanoseconds(cudaBatchResult.initialDiagSeconds));
	          recordSimInitialScanOnlineReduceNanoseconds(
	            simSecondsToNanoseconds(cudaBatchResult.initialOnlineReduceSeconds));
	          recordSimInitialScanWaitNanoseconds(simSecondsToNanoseconds(cudaBatchResult.initialWaitSeconds));
	          recordSimInitialHashReduceNanoseconds(
	            simSecondsToNanoseconds(cudaBatchResult.initialHashReduceSeconds));
	          recordSimInitialSegmentedReduceNanoseconds(
	            simSecondsToNanoseconds(cudaBatchResult.initialSegmentedReduceSeconds));
	          recordSimInitialSegmentedCompactNanoseconds(
	            simSecondsToNanoseconds(cudaBatchResult.initialSegmentedCompactSeconds));
		          recordSimInitialTopKNanoseconds(
		            simSecondsToNanoseconds(cudaBatchResult.initialTopKSeconds));
		          recordSimInitialSegmentedStateStats(cudaBatchResult.initialSegmentedTileStateCount,
		                                             cudaBatchResult.initialSegmentedGroupedStateCount);
			          recordSimInitialSummaryPackedD2H(
			            cudaBatchResult.usedInitialPackedSummaryD2H,
			            cudaBatchResult.initialSummaryPackedBytesD2H,
			            cudaBatchResult.initialSummaryUnpackedEquivalentBytesD2H,
			            simSecondsToNanoseconds(cudaBatchResult.initialSummaryPackSeconds),
			            cudaBatchResult.initialSummaryPackedD2HFallbacks);
				          recordSimInitialSummaryHostCopyElision(
				            cudaBatchResult.usedInitialSummaryHostCopyElision,
				            simSecondsToNanoseconds(cudaBatchResult.initialSummaryD2HCopySeconds),
				            simSecondsToNanoseconds(cudaBatchResult.initialSummaryUnpackSeconds),
				            simSecondsToNanoseconds(cudaBatchResult.initialSummaryResultMaterializeSeconds),
				            cudaBatchResult.initialSummaryHostCopyElidedBytes,
				            cudaBatchResult.initialSummaryHostCopyElisionCountCopyReuses);
				          recordSimInitialPinnedAsyncHandoffStats(cudaBatchResult);
				          if(!cudaRequests[0].reduceCandidates &&
				             !cudaRequests[0].proposalCandidates &&
				             simCudaInitialChunkedHandoffEnabledRuntime())
			          {
			            recordSimInitialChunkedHandoffTransferNanoseconds(
			              simSecondsToNanoseconds(cudaBatchResult.d2hSeconds),
			              0,
			              0);
			          }
			          if(cudaBatchResult.usedInitialProposalV2Path)
		          {
	            recordSimInitialProposalV2(1,cudaBatchResult.initialProposalV2RequestCount);
	          }
	          if(cudaBatchResult.usedInitialProposalV2DirectTopKPath)
	          {
	            recordSimInitialProposalDirectTopK(1,
	                                               cudaBatchResult.initialProposalLogicalCandidateCount,
	                                               cudaBatchResult.initialProposalMaterializedCandidateCount,
	                                               simSecondsToNanoseconds(cudaBatchResult.initialProposalDirectTopKGpuSeconds));
	          }
	        }
	      recordSimInitialEvents(cudaResults[0].eventCount);
	      recordSimInitialRunSummaries(cudaResults[0].runSummaryCount);
		      if(!cudaRequests[0].reduceCandidates && !cudaRequests[0].proposalCandidates)
		      {
		        const uint64_t summaryBytesD2H =
		          static_cast<uint64_t>(cudaResults[0].initialRunSummaries.size()) *
		          (cudaBatchResult.usedInitialPackedSummaryD2H ?
		           static_cast<uint64_t>(sizeof(SimScanCudaPackedInitialRunSummary16)) :
		           static_cast<uint64_t>(sizeof(SimScanCudaInitialRunSummary)));
		        recordSimInitialSummaryBytesD2H(summaryBytesD2H);
		      }
		      if(cudaRequests[0].reduceCandidates || cudaRequests[0].proposalCandidates)
		      {
	        recordSimInitialAllCandidateStates(cudaResults[0].allCandidateStateCount);
	        recordSimInitialStoreBytesD2H((cudaRequests[0].proposalCandidates ||
	                                      cudaResults[0].persistentSafeStoreHandle.valid) ?
	                                     0 :
	                                     (static_cast<uint64_t>(cudaResults[0].allCandidateStates.size()) *
	                                      static_cast<uint64_t>(sizeof(SimScanCudaCandidateState))));
	        if(cudaRequests[0].reduceCandidates)
	        {
	          recordSimInitialReducedCandidates(static_cast<uint64_t>(cudaResults[0].candidateStates.size()));
	          recordSimInitialReduceReplayStats(cudaBatchResult.initialReduceReplayStats);
	          if(simCudaInitialExactFrontierReplayEnabledRuntime())
	          {
	            recordSimInitialExactFrontierReplay(
	              static_cast<uint64_t>(cudaResults[0].candidateStates.size()),
	              cudaResults[0].persistentSafeStoreHandle.valid);
	          }
	          runSimCudaInitialOrderedSegmentedV3ShadowIfEnabled(
	            cudaResults[0].initialRunSummaries,
	            cudaResults[0].candidateStates,
	            cudaResults[0].runningMin,
	            cudaResults[0].allCandidateStates);
	        }
	        else
	        {
	          recordSimProposalAllCandidateStates(cudaResults[0].allCandidateStateCount);
	          recordSimProposalBytesD2H(static_cast<uint64_t>(cudaResults[0].candidateStates.size()) *
	                                    static_cast<uint64_t>(sizeof(SimScanCudaCandidateState)));
	          recordSimProposalSelected(static_cast<uint64_t>(cudaResults[0].candidateStates.size()));
	          recordSimProposalGpuNanoseconds(simSecondsToNanoseconds(cudaBatchResult.proposalSelectGpuSeconds));
	        }
	        applySimCudaInitialReduceResults(cudaResults[0].candidateStates,
	                                         cudaResults[0].runningMin,
	                                         cudaResults[0].allCandidateStates,
	                                         cudaResults[0].persistentSafeStoreHandle,
	                                         cudaResults[0].eventCount,
	                                         context,
	                                         benchmarkEnabled,
	                                         cudaRequests[0].proposalCandidates);
	      }
		      else
		      {
	        if(useInitialPinnedAsyncCpuPipeline &&
	           cudaBatchResult.initialHandoffCpuPipelineActive)
	        {
	          initialCpuPipelineState.logicalEventCount = cudaResults[0].eventCount;
	          if(context.statsEnabled && !initialCpuPipelineState.eventsSeenRecorded)
	          {
	            context.stats.eventsSeen += cudaResults[0].eventCount;
	            initialCpuPipelineState.eventsSeenRecorded = true;
	          }
	          finalizeSimInitialPinnedAsyncCpuPipelineApply(context,
	                                                        initialCpuPipelineState,
	                                                        false);
	          cudaBatchResult.initialHandoffCpuPipelineChunksFinalized +=
	            initialCpuPipelineState.chunksFinalized;
	          cudaBatchResult.initialHandoffCpuPipelineFinalizeCount +=
	            initialCpuPipelineState.finalizeCount;
	          cudaBatchResult.initialHandoffCpuPipelineOutOfOrderChunks +=
	            initialCpuPipelineState.outOfOrderChunks;
	          if(benchmarkEnabled)
	          {
	            recordSimInitialPinnedAsyncCpuPipelineFinalizeStats(
	              initialCpuPipelineState);
	          }
	          finalizeSimCudaInitialRunSummariesToContext(cudaResults[0].initialRunSummaries,
	                                                      context,
	                                                      benchmarkEnabled,
	                                                      true);
	        }
	        else
	        {
	          applySimCudaInitialRunSummariesToContext(cudaResults[0].initialRunSummaries,
	                                                   cudaResults[0].eventCount,
	                                                   context,
	                                                   benchmarkEnabled);
	        }
	      }

	      if(simCudaValidateEnabledRuntime() && !cudaRequests[0].proposalCandidates)
	      {
	        SimKernelContext cpuContext(M,N);
	        cpuContext.gapOpen = context.gapOpen;
	        cpuContext.gapExtend = context.gapExtend;
	        memcpy(cpuContext.scoreMatrix, context.scoreMatrix, sizeof(context.scoreMatrix));
	        cpuContext.runningMin = 0;
	        cpuContext.candidateCount = 0;
	        clearSimCandidateStartIndex(cpuContext.candidateStartIndex);
	        cpuContext.candidateMinHeap.clear();

	        if(simCandidateRunUpdaterEnabledRuntime())
	        {
	          SimCandidateRunUpdater cpuUpdater(cpuContext);
	          enumerateSimCandidateRegionRowMajor(A,B,1,M,1,N,minScore,cpuContext,cpuUpdater);
	          cpuUpdater.finish();
	        }
	        else
	        {
	          SimCandidateEventUpdater cpuUpdater(cpuContext);
	          enumerateSimCandidateRegionRowMajor(A,B,1,M,1,N,minScore,cpuContext,cpuUpdater);
	          cpuUpdater.finish();
	        }

	        vector<SimCandidate> gpuCandidates(context.candidateCount);
	        for(long i = 0; i < context.candidateCount; ++i)
	        {
	          gpuCandidates[static_cast<size_t>(i)] = context.candidates[i];
	        }
	        vector<SimCandidate> cpuCandidates(cpuContext.candidateCount);
	        for(long i = 0; i < cpuContext.candidateCount; ++i)
	        {
	          cpuCandidates[static_cast<size_t>(i)] = cpuContext.candidates[i];
	        }
	        const auto candidateLess = [](const SimCandidate &lhs,const SimCandidate &rhs)
	        {
	          if(lhs.SCORE != rhs.SCORE) return lhs.SCORE < rhs.SCORE;
	          if(lhs.STARI != rhs.STARI) return lhs.STARI < rhs.STARI;
	          if(lhs.STARJ != rhs.STARJ) return lhs.STARJ < rhs.STARJ;
	          if(lhs.ENDI != rhs.ENDI) return lhs.ENDI < rhs.ENDI;
	          if(lhs.ENDJ != rhs.ENDJ) return lhs.ENDJ < rhs.ENDJ;
	          if(lhs.TOP != rhs.TOP) return lhs.TOP < rhs.TOP;
	          if(lhs.BOT != rhs.BOT) return lhs.BOT < rhs.BOT;
	          if(lhs.LEFT != rhs.LEFT) return lhs.LEFT < rhs.LEFT;
	          return lhs.RIGHT < rhs.RIGHT;
	        };
	        sort(gpuCandidates.begin(),gpuCandidates.end(),candidateLess);
	        sort(cpuCandidates.begin(),cpuCandidates.end(),candidateLess);
	        if(gpuCandidates.size() != cpuCandidates.size())
	        {
	          fprintf(stderr,
	                  "SIM CUDA validate: candidateCount mismatch cpu=%zu cuda=%zu\n",
	                  cpuCandidates.size(),
	                  gpuCandidates.size());
	          abort();
	        }
	        for(size_t i = 0; i < gpuCandidates.size(); ++i)
	        {
	          const SimCandidate &g = gpuCandidates[i];
	          const SimCandidate &c = cpuCandidates[i];
	          if(memcmp(&g,&c,sizeof(SimCandidate)) != 0)
	          {
	            fprintf(stderr,
	                    "SIM CUDA validate: candidate mismatch index=%zu cpu(score=%ld stari=%ld starj=%ld endi=%ld endj=%ld) cuda(score=%ld stari=%ld starj=%ld endi=%ld endj=%ld)\n",
	                    i,
	                    c.SCORE,
	                    c.STARI,
	                    c.STARJ,
	                    c.ENDI,
	                    c.ENDJ,
	                    g.SCORE,
	                    g.STARI,
	                    g.STARJ,
	                    g.ENDI,
	                    g.ENDJ);
	            abort();
	          }
	        }
	      }
	    }
	    else if(simCudaValidateEnabledRuntime() && !cudaError.empty())
	    {
	      fprintf(stderr, "SIM CUDA init/scan failed: %s\n", cudaError.c_str());
	    }
	  }

	  if(!usedCuda)
	  {
	    invalidateSimSafeCandidateStateStore(context);
	    if(simCandidateRunUpdaterEnabledRuntime())
	    {
	      SimCandidateRunUpdater updater(context);
	      enumerateSimCandidateRegion(A,B,1,M,1,N,minScore,context,updater);
	      updater.finish();
	    }
	    else
	    {
	      SimCandidateEventUpdater updater(context);
	      enumerateSimCandidateRegion(A,B,1,M,1,N,minScore,context,updater);
	      updater.finish();
	    }
	  }

	  recordSimInitialScanBackend(usedCuda,scanTaskCount,scanLaunchCount);
		  if(benchmarkEnabled)
		  {
		    recordSimInitialScanNanoseconds(simElapsedNanoseconds(initialScanStart));
		  }
		}

	inline SimScanCudaFrontierDigest digestSimCudaFrontierStatesForTransducerShadow(
	  const vector<SimScanCudaCandidateState> &states,
	  int runningMin)
	{
	  SimScanCudaFrontierDigest digest;
	  resetSimScanCudaFrontierDigest(digest,static_cast<int>(states.size()),runningMin);
	  for(size_t i = 0; i < states.size(); ++i)
	  {
	    updateSimScanCudaFrontierDigest(digest,states[i],static_cast<int>(i));
	  }
	  return digest;
	}

	inline void runSimCudaInitialFrontierTransducerShadowIfEnabled(
	  const vector<SimScanCudaInitialRunSummary> &summaries,
	  const SimKernelContext &context)
	{
	  if(!simCudaInitialFrontierTransducerShadowEnabledRuntime())
	  {
	    return;
	  }

	  vector<int> runBases(1,0);
	  vector<int> runTotals(1,static_cast<int>(summaries.size()));
	  vector<SimScanCudaFrontierTransducerSegmentedShadowResult> shadowResults;
	  double shadowSeconds = 0.0;
	  string shadowError;
	  uint64_t mismatchCount = 0;
	  uint64_t digestD2HBytes = 0;
	  uint64_t summaryReplayCount = 0;
	  const bool callOk =
	    sim_scan_cuda_reduce_frontier_chunk_transducer_segmented_shadow_for_test(
	      summaries,
	      runBases,
	      runTotals,
	      simCudaInitialFrontierTransducerShadowChunkSizeRuntime(),
	      &shadowResults,
	      &shadowSeconds,
	      &shadowError);
	  if(!callOk || shadowResults.size() != 1u)
	  {
	    mismatchCount = 1;
	  }
	  else
	  {
	    vector<SimScanCudaCandidateState> cpuStates;
	    collectSimContextCandidateStates(context,cpuStates);
	    const SimScanCudaFrontierDigest cpuDigest =
	      digestSimCudaFrontierStatesForTransducerShadow(
	        cpuStates,
	        static_cast<int>(context.runningMin));
	    const SimScanCudaFrontierTransducerSegmentedShadowResult &shadow = shadowResults[0];
	    digestD2HBytes =
	      static_cast<uint64_t>(sizeof(SimScanCudaFrontierDigest)) +
	      static_cast<uint64_t>(sizeof(SimScanCudaFrontierTransducerShadowStats)) +
	      static_cast<uint64_t>(shadow.candidateStates.size()) *
	        static_cast<uint64_t>(sizeof(SimScanCudaCandidateState));
	    summaryReplayCount = shadow.stats.summaryReplayCount;
	    const bool digestMatch =
	      cpuDigest.candidateCount == shadow.digest.candidateCount &&
	      cpuDigest.runningMin == shadow.digest.runningMin &&
	      cpuDigest.slotOrderHash == shadow.digest.slotOrderHash &&
	      cpuDigest.candidateIdentityHash == shadow.digest.candidateIdentityHash &&
	      cpuDigest.scoreHash == shadow.digest.scoreHash &&
	      cpuDigest.boundsHash == shadow.digest.boundsHash;
	    if(shadow.runningMin != static_cast<int>(context.runningMin) ||
	       shadow.candidateStates.size() != cpuStates.size() ||
	       !digestMatch)
	    {
	      mismatchCount = 1;
	    }
	    else
	    {
	      for(size_t i = 0; i < cpuStates.size(); ++i)
	      {
	        if(memcmp(&cpuStates[i],
	                  &shadow.candidateStates[i],
	                  sizeof(SimScanCudaCandidateState)) != 0)
	        {
	          mismatchCount = 1;
	          break;
	        }
	      }
	    }
	  }
	  recordSimInitialFrontierTransducerShadow(
	    simSecondsToNanoseconds(shadowSeconds),
	    digestD2HBytes,
	    summaryReplayCount,
	    mismatchCount);
	  if(mismatchCount != 0 && simCudaValidateEnabledRuntime())
	  {
	    fprintf(stderr,
	            "SIM CUDA initial frontier transducer shadow mismatch%s%s\n",
	            shadowError.empty() ? "" : ": ",
	            shadowError.empty() ? "" : shadowError.c_str());
	  }
	}

	inline bool simCudaCandidateStateVectorsEqualOrdered(
	  const vector<SimScanCudaCandidateState> &lhs,
	  const vector<SimScanCudaCandidateState> &rhs)
	{
	  if(lhs.size() != rhs.size())
	  {
	    return false;
	  }
	  for(size_t i = 0; i < lhs.size(); ++i)
	  {
	    if(memcmp(&lhs[i],&rhs[i],sizeof(SimScanCudaCandidateState)) != 0)
	    {
	      return false;
	    }
	  }
	  return true;
	}

	inline size_t simCudaFirstCandidateStateMismatchIndexOrdered(
	  const vector<SimScanCudaCandidateState> &lhs,
	  const vector<SimScanCudaCandidateState> &rhs)
	{
	  const size_t limit = min(lhs.size(),rhs.size());
	  for(size_t i = 0; i < limit; ++i)
	  {
	    if(memcmp(&lhs[i],&rhs[i],sizeof(SimScanCudaCandidateState)) != 0)
	    {
	      return i;
	    }
	  }
	  return limit;
	}

	inline void simCudaPrintCandidateStateForShadow(const char *label,
	                                                const SimScanCudaCandidateState &state)
	{
	  fprintf(stderr,
	          "%s(score=%d start=(%d,%d) end=(%d,%d) box=(%d,%d,%d,%d))",
	          label,
	          state.score,
	          state.startI,
	          state.startJ,
	          state.endI,
	          state.endJ,
	          state.top,
	          state.bot,
	          state.left,
	          state.right);
	}

	inline vector<SimScanCudaCandidateState> simCudaSortedCandidateStatesForShadow(
	  vector<SimScanCudaCandidateState> states)
	{
	  sort(states.begin(),states.end(),
	       [](const SimScanCudaCandidateState &lhs,
	          const SimScanCudaCandidateState &rhs)
	       {
	         const uint64_t lhsStart = simScanCudaCandidateStateStartCoord(lhs);
	         const uint64_t rhsStart = simScanCudaCandidateStateStartCoord(rhs);
	         if(lhsStart != rhsStart) return lhsStart < rhsStart;
	         if(lhs.score != rhs.score) return lhs.score < rhs.score;
	         if(lhs.endI != rhs.endI) return lhs.endI < rhs.endI;
	         if(lhs.endJ != rhs.endJ) return lhs.endJ < rhs.endJ;
	         if(lhs.top != rhs.top) return lhs.top < rhs.top;
	         if(lhs.bot != rhs.bot) return lhs.bot < rhs.bot;
	         if(lhs.left != rhs.left) return lhs.left < rhs.left;
	         return lhs.right < rhs.right;
	       });
	  return states;
	}

	inline bool simCudaCandidateStateVectorsEqualAsSet(
	  const vector<SimScanCudaCandidateState> &lhs,
	  const vector<SimScanCudaCandidateState> &rhs)
	{
	  return simCudaCandidateStateVectorsEqualOrdered(
	    simCudaSortedCandidateStatesForShadow(lhs),
	    simCudaSortedCandidateStatesForShadow(rhs));
	}

	inline bool simCudaCandidateStatesContainStartCoord(
	  const vector<SimScanCudaCandidateState> &states,
	  uint64_t startCoord)
	{
	  for(size_t i = 0; i < states.size(); ++i)
	  {
	    if(simScanCudaCandidateStateStartCoord(states[i]) == startCoord)
	    {
	      return true;
	    }
	  }
	  return false;
	}

	inline vector<SimScanCudaCandidateState> buildSimCudaInitialShadowExpectedSafeStore(
	  const vector<SimScanCudaInitialRunSummary> &summaries,
	  const vector<SimScanCudaCandidateState> &frontierStates,
	  int runningMin)
	{
	  vector<SimScanCudaCandidateState> allStates;
	  reduceSimCudaInitialRunSummariesToAllCandidateStates(summaries,NULL,allStates);
	  vector<SimScanCudaCandidateState> kept;
	  kept.reserve(allStates.size());
	  for(size_t i = 0; i < allStates.size(); ++i)
	  {
	    const uint64_t startCoord = simScanCudaCandidateStateStartCoord(allStates[i]);
	    if(allStates[i].score > runningMin ||
	       simCudaCandidateStatesContainStartCoord(frontierStates,startCoord))
	    {
	      kept.push_back(allStates[i]);
	    }
	  }
	  return kept;
	}

	inline void runSimCudaInitialOrderedSegmentedV3ShadowIfEnabled(
	  const vector<SimScanCudaInitialRunSummary> &summaries,
	  const vector<SimScanCudaCandidateState> &candidateStates,
	  int runningMin,
	  const vector<SimScanCudaCandidateState> &allCandidateStates)
	{
	  if(!simCudaInitialOrderedSegmentedV3ShadowEnabledRuntime() ||
	     summaries.empty())
	  {
	    return;
	  }

	  vector<SimScanCudaCandidateState> cpuCandidateStates;
	  int cpuRunningMin = 0;
	  reduceSimCudaInitialRunSummariesToCandidateStates(
	    summaries,
	    cpuCandidateStates,
	    cpuRunningMin);
	  const vector<SimScanCudaCandidateState> cpuSafeStoreStates =
	    buildSimCudaInitialShadowExpectedSafeStore(
	      summaries,
	      cpuCandidateStates,
	      cpuRunningMin);

	  const bool runningMinMismatch = runningMin != cpuRunningMin;
	  const bool candidateCountMismatch =
	    candidateStates.size() != cpuCandidateStates.size();
	  const bool candidateValueMismatch =
	    !candidateCountMismatch &&
	    !simCudaCandidateStateVectorsEqualOrdered(candidateStates,cpuCandidateStates);
	  const bool frontierMatch =
	    !runningMinMismatch &&
	    !candidateCountMismatch &&
	    !candidateValueMismatch;
	  const bool safeStoreMatch =
	    simCudaCandidateStateVectorsEqualAsSet(allCandidateStates,cpuSafeStoreStates);
	  recordSimInitialOrderedSegmentedV3Shadow(frontierMatch ? 0 : 1,
	                                           runningMinMismatch ? 1 : 0,
	                                           safeStoreMatch ? 0 : 1,
	                                           candidateCountMismatch ? 1 : 0,
	                                           candidateValueMismatch ? 1 : 0);
	  if(!frontierMatch || !safeStoreMatch)
	  {
	    fprintf(stderr,
	            "SIM CUDA initial ordered_segmented_v3 shadow mismatch: "
	            "frontier=%s safe_store=%s summaries=%zu gpu_candidates=%zu cpu_candidates=%zu "
	            "gpu_running_min=%d cpu_running_min=%d\n",
	            frontierMatch ? "match" : "mismatch",
	            safeStoreMatch ? "match" : "mismatch",
	            summaries.size(),
	            candidateStates.size(),
	            cpuCandidateStates.size(),
	            runningMin,
	            cpuRunningMin);
	    if(candidateValueMismatch)
	    {
	      const size_t mismatchIndex =
	        simCudaFirstCandidateStateMismatchIndexOrdered(candidateStates,cpuCandidateStates);
	      if(mismatchIndex < candidateStates.size() &&
	         mismatchIndex < cpuCandidateStates.size())
	      {
	        fprintf(stderr,
	                "SIM CUDA initial ordered_segmented_v3 first frontier mismatch index=%zu ",
	                mismatchIndex);
	        simCudaPrintCandidateStateForShadow("gpu=",
	                                            candidateStates[mismatchIndex]);
	        fprintf(stderr," ");
	        simCudaPrintCandidateStateForShadow("cpu=",
	                                            cpuCandidateStates[mismatchIndex]);
	        fprintf(stderr,"\n");
	      }
	    }
	    if(!safeStoreMatch)
	    {
	      const vector<SimScanCudaCandidateState> sortedGpuSafeStore =
	        simCudaSortedCandidateStatesForShadow(allCandidateStates);
	      const vector<SimScanCudaCandidateState> sortedCpuSafeStore =
	        simCudaSortedCandidateStatesForShadow(cpuSafeStoreStates);
	      const size_t mismatchIndex =
	        simCudaFirstCandidateStateMismatchIndexOrdered(sortedGpuSafeStore,
	                                                       sortedCpuSafeStore);
	      fprintf(stderr,
	              "SIM CUDA initial ordered_segmented_v3 safe-store mismatch index=%zu "
	              "gpu_safe_store=%zu cpu_safe_store=%zu",
	              mismatchIndex,
	              sortedGpuSafeStore.size(),
	              sortedCpuSafeStore.size());
	      if(mismatchIndex < sortedGpuSafeStore.size() &&
	         mismatchIndex < sortedCpuSafeStore.size())
	      {
	        fprintf(stderr," ");
	        simCudaPrintCandidateStateForShadow("gpu=",
	                                            sortedGpuSafeStore[mismatchIndex]);
	        fprintf(stderr," ");
	        simCudaPrintCandidateStateForShadow("cpu=",
	                                            sortedCpuSafeStore[mismatchIndex]);
	      }
	      fprintf(stderr,"\n");
	    }
	  }
	}

		inline void applySimCudaInitialRunSummariesLegacyContextApply(
		  const vector<SimScanCudaInitialRunSummary> &summaries,
		  uint64_t eventCount,
		  SimKernelContext &context)
		{
		  if(simCudaInitialContextApplyChunkSkipEnabledRuntime())
		  {
		    SimInitialContextApplyChunkSkipStats chunkSkipStats;
		    mergeSimCudaInitialRunSummariesWithContextApplyChunkSkip(
		      summaries,
		      eventCount,
		      context,
		      simCudaInitialContextApplyChunkSkipChunkSize(),
		      &chunkSkipStats);
		    recordSimInitialContextApplyChunkSkipStats(chunkSkipStats);
		  }
		  else
		  {
		    mergeSimCudaInitialRunSummaries(summaries,eventCount,context);
		  }
		}

		inline bool simInitialCpuFrontierFastApplyContextsEqual(const SimKernelContext &actual,
		                                                        const SimKernelContext &expected)
		{
		  if(actual.candidateCount != expected.candidateCount ||
		     actual.runningMin != expected.runningMin)
		  {
		    return false;
		  }
		  for(long candidateIndex = 0; candidateIndex < actual.candidateCount; ++candidateIndex)
		  {
		    if(memcmp(&actual.candidates[candidateIndex],
		              &expected.candidates[candidateIndex],
		              sizeof(SimCandidate)) != 0)
		    {
		      return false;
		    }
		  }
		  return true;
		}

		inline bool trySimCudaInitialCpuFrontierFastApply(
		  const vector<SimScanCudaInitialRunSummary> &summaries,
		  uint64_t eventCount,
		  SimKernelContext &context,
		  bool useFastResult)
		{
		  recordSimInitialCpuFrontierFastApplyAttempt();
		  if(context.statsEnabled)
		  {
		    recordSimInitialCpuFrontierFastApplyRejectedByStats();
		    recordSimInitialCpuFrontierFastApplyFallback();
		    return false;
		  }
		  if(context.candidateCount != 0)
		  {
		    recordSimInitialCpuFrontierFastApplyRejectedByNonemptyContext();
		    recordSimInitialCpuFrontierFastApplyFallback();
		    return false;
		  }

		  const bool shadowEnabled = simCudaInitialCpuFrontierFastApplyShadowEnabledRuntime();
		  if(shadowEnabled)
		  {
		    SimKernelContext oracleContext(context);
		    const std::chrono::steady_clock::time_point oracleStart =
		      std::chrono::steady_clock::now();
		    applySimCudaInitialRunSummariesLegacyContextApply(summaries,eventCount,oracleContext);
		    recordSimInitialCpuFrontierFastApplyOracleShadowNanoseconds(
		      simElapsedNanoseconds(oracleStart));

		    SimKernelContext fastContext(context);
		    SimInitialCpuFrontierFastApplyStats fastStats;
		    const std::chrono::steady_clock::time_point fastStart =
		      std::chrono::steady_clock::now();
		    const bool fastOk =
		      applySimCudaInitialRunSummariesCpuFrontierFastApply(summaries,
		                                                          eventCount,
		                                                          fastContext,
		                                                          &fastStats);
		    const uint64_t fastNanoseconds = simElapsedNanoseconds(fastStart);
		    if(fastOk)
		    {
		      recordSimInitialCpuFrontierFastApplyReplayStats(fastStats,fastNanoseconds);
		    }

		    if(!fastOk ||
		       !simInitialCpuFrontierFastApplyContextsEqual(fastContext,oracleContext))
		    {
		      recordSimInitialCpuFrontierFastApplyShadowMismatch();
		      recordSimInitialCpuFrontierFastApplyFallback();
		      context = oracleContext;
		      return true;
		    }

		    recordSimInitialCpuFrontierFastApplySuccess();
		    context = useFastResult ? fastContext : oracleContext;
		    return true;
		  }

		  SimInitialCpuFrontierFastApplyStats fastStats;
		  const std::chrono::steady_clock::time_point fastStart =
		    std::chrono::steady_clock::now();
		  const bool fastOk =
		    applySimCudaInitialRunSummariesCpuFrontierFastApply(summaries,
		                                                        eventCount,
		                                                        context,
		                                                        &fastStats);
		  const uint64_t fastNanoseconds = simElapsedNanoseconds(fastStart);
		  if(!fastOk)
		  {
		    recordSimInitialCpuFrontierFastApplyFallback();
		    return false;
		  }
		  recordSimInitialCpuFrontierFastApplyReplayStats(fastStats,fastNanoseconds);
		  recordSimInitialCpuFrontierFastApplySuccess();
		  return true;
		}

		inline void finalizeSimCudaInitialRunSummariesToContext(
		  const vector<SimScanCudaInitialRunSummary> &summaries,
		  SimKernelContext &context,
		  bool benchmarkEnabled,
		  bool hostSafeStoreAlreadyUpdated,
		  bool hostSafeStoreAlreadyPruned)
		{
		  const bool maintainSafeStore =
		    simLocateCudaModeRuntime() == SIM_LOCATE_CUDA_MODE_SAFE_WORKSET ||
		    simCudaProposalLoopEnabledRuntime();
		  if(maintainSafeStore)
		  {
		    bool maintainedSafeStoreOnDevice = false;
		    const bool initialSafeStoreHandoffRequested =
		      simCudaInitialSafeStoreHandoffRequestedRuntime();
		    const bool initialSafeStoreHandoffEnabled =
		      simCudaInitialSafeStoreHandoffEnabledRuntime();
		    if(initialSafeStoreHandoffRequested && !initialSafeStoreHandoffEnabled)
		    {
		      if(simLocateCudaFastShadowEnabledRuntime())
		      {
		        recordSimInitialSafeStoreHandoffRejectedFastShadow();
		      }
		      if(simCudaProposalLoopEnabledRuntime())
		      {
		        recordSimInitialSafeStoreHandoffRejectedProposalLoop();
		      }
		    }
		    if(initialSafeStoreHandoffEnabled)
		    {
		      vector<SimScanCudaCandidateState> finalCandidateStates;
		      collectSimContextCandidateStates(context,finalCandidateStates);
		      SimCudaPersistentSafeStoreHandle builtGpuSafeStore;
		      double deviceBuildSeconds = 0.0;
		      double devicePruneSeconds = 0.0;
		      double frontierUploadSeconds = 0.0;
		      string gpuStoreError;
		      if(sim_scan_cuda_build_persistent_safe_candidate_state_store_from_initial_run_summaries(
		           summaries,
		           finalCandidateStates,
		           static_cast<int>(context.runningMin),
		           &builtGpuSafeStore,
		           &deviceBuildSeconds,
		           &devicePruneSeconds,
		           &frontierUploadSeconds,
		           &gpuStoreError))
		      {
		        if(benchmarkEnabled)
		        {
		          recordSimInitialSafeStoreDeviceBuildNanoseconds(simSecondsToNanoseconds(deviceBuildSeconds));
		          recordSimInitialSafeStoreDevicePruneNanoseconds(simSecondsToNanoseconds(devicePruneSeconds));
		          recordSimInitialSafeStoreFrontierBytesH2D(
		            static_cast<uint64_t>(finalCandidateStates.size()) *
		            static_cast<uint64_t>(sizeof(SimScanCudaCandidateState)));
		          recordSimInitialSafeStoreFrontierUploadNanoseconds(simSecondsToNanoseconds(frontierUploadSeconds));
		        }
		        resetSimCandidateStateStore(context.safeCandidateStateStore,false);
		        releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
		        moveSimCudaPersistentSafeStoreHandle(context.gpuSafeCandidateStateStore,builtGpuSafeStore);
		        markSimGpuFrontierCacheSynchronized(context);
		        context.initialSafeStoreHandoffActive = true;
		        recordSimInitialSafeStoreHandoffCreated();
		        recordSimInitialSafeStoreHandoffHostStoreEvicted();
		        recordSimFrontierCacheRebuildFromHostFinalCandidates();
		        maintainedSafeStoreOnDevice = true;
		      }
		      else
		      {
		        releaseSimCudaPersistentSafeCandidateStateStore(builtGpuSafeStore);
		        recordSimInitialSafeStoreHandoffRejectedMissingGpuStore();
		        if(simCudaValidateEnabledRuntime() && !gpuStoreError.empty())
		        {
		          fprintf(stderr,
		                  "SIM CUDA initial safe-store device maintenance failed, falling back to host path: %s\n",
		                  gpuStoreError.c_str());
		        }
		      }
		    }

		    if(!maintainedSafeStoreOnDevice)
		    {
		      if(!hostSafeStoreAlreadyUpdated)
		      {
		        const std::chrono::steady_clock::time_point safeStoreUpdateStart =
		          benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
		        mergeSimCudaInitialRunSummariesIntoSafeStore(summaries,context);
		        if(benchmarkEnabled)
		        {
		          recordSimInitialScanCpuSafeStoreUpdateNanoseconds(simElapsedNanoseconds(safeStoreUpdateStart));
		        }
		      }
		      if(!hostSafeStoreAlreadyPruned)
		      {
		        const std::chrono::steady_clock::time_point safeStorePruneStart =
		          benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
		        pruneSimSafeCandidateStateStore(context);
		        if(benchmarkEnabled)
		        {
		          recordSimInitialScanCpuSafeStorePruneNanoseconds(simElapsedNanoseconds(safeStorePruneStart));
		        }
		      }
		      const bool wantSafeWorksetGpuMirror =
		        simLocateCudaEnabledRuntime() &&
		        simLocateCudaModeRuntime() == SIM_LOCATE_CUDA_MODE_SAFE_WORKSET &&
		        !simLocateCudaFastShadowEnabledRuntime();
		      if(wantSafeWorksetGpuMirror)
		      {
		        const uint64_t storeBytesH2D =
		          static_cast<uint64_t>(context.safeCandidateStateStore.states.size()) *
		          static_cast<uint64_t>(sizeof(SimScanCudaCandidateState));
		        const std::chrono::steady_clock::time_point storeUploadStart =
		          benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
		        string gpuStoreError;
		        if(!uploadSimCudaPersistentSafeCandidateStateStore(context.safeCandidateStateStore.states,
		                                                           context.gpuSafeCandidateStateStore,
		                                                           &gpuStoreError))
		        {
		          releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
		          context.initialSafeStoreHandoffActive = false;
		          if(simCudaValidateEnabledRuntime() && !gpuStoreError.empty())
		          {
		            fprintf(stderr, "SIM CUDA initial safe-store mirror upload failed: %s\n", gpuStoreError.c_str());
		          }
		        }
		        else
		        {
		          markSimGpuFrontierCacheSynchronized(context);
		          context.initialSafeStoreHandoffActive = false;
		          if(benchmarkEnabled)
		          {
		            recordSimInitialStoreBytesH2D(storeBytesH2D);
		          }
		        }
		        if(benchmarkEnabled)
		        {
		          recordSimInitialStoreUploadNanoseconds(simElapsedNanoseconds(storeUploadStart));
		        }
		      }
		      else if(context.gpuSafeCandidateStateStore.valid)
		      {
		        releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
		        context.initialSafeStoreHandoffActive = false;
		      }
		    }
		  }
		  runSimCudaInitialFrontierTransducerShadowIfEnabled(summaries,context);
		}

		inline void applySimCudaInitialRunSummariesToContext(const vector<SimScanCudaInitialRunSummary> &summaries,
		                                                     uint64_t eventCount,
		                                                     SimKernelContext &context,
	                                                     bool benchmarkEnabled)
	{
	  context.proposalCandidateLoop = false;
	  const bool maintainSafeStore =
	    simLocateCudaModeRuntime() == SIM_LOCATE_CUDA_MODE_SAFE_WORKSET ||
    simCudaProposalLoopEnabledRuntime();
	  const std::chrono::steady_clock::time_point cpuMergeStart =
	    benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
	  const std::chrono::steady_clock::time_point contextApplyStart =
	    benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
	  bool contextApplyDone = false;
	  const bool useInitialCpuFrontierFastApply =
	    simCudaInitialCpuFrontierFastApplyEnabledRuntime();
	  const bool shadowInitialCpuFrontierFastApply =
	    simCudaInitialCpuFrontierFastApplyShadowEnabledRuntime();
	  const bool useInitialChunkedHandoff =
	    simCudaInitialChunkedHandoffEnabledRuntime();
	  bool chunkedHandoffMaintainedHostSafeStore = false;
	  if(useInitialChunkedHandoff &&
	     (useInitialCpuFrontierFastApply || shadowInitialCpuFrontierFastApply))
	  {
	    SimInitialChunkedHandoffStats fallbackStats;
	    fallbackStats.ringSlots =
	      static_cast<uint64_t>(simCudaInitialChunkedHandoffRingSlotsRuntime());
	    fallbackStats.fallbackCount = 1;
	    fallbackStats.fallbackReason =
	      SIM_INITIAL_CHUNKED_HANDOFF_FALLBACK_UNSUPPORTED_FAST_APPLY;
	    recordSimInitialChunkedHandoffStats(fallbackStats);
	  }
	  if(useInitialCpuFrontierFastApply || shadowInitialCpuFrontierFastApply)
	  {
	    if(useInitialCpuFrontierFastApply)
	    {
	      recordSimInitialCpuFrontierFastApplyEnabled();
	    }
	    contextApplyDone =
	      trySimCudaInitialCpuFrontierFastApply(summaries,
	                                            eventCount,
	                                            context,
	                                            useInitialCpuFrontierFastApply);
	  }
	  if(!contextApplyDone)
	  {
	    if(useInitialChunkedHandoff)
	    {
	      applySimCudaInitialRunSummariesChunkedHandoff(summaries,
	                                                   eventCount,
	                                                   context,
	                                                   maintainSafeStore);
	      contextApplyDone = true;
	      chunkedHandoffMaintainedHostSafeStore = maintainSafeStore;
	    }
	    else
	    {
	      applySimCudaInitialRunSummariesLegacyContextApply(summaries,eventCount,context);
	    }
	  }
	  if(benchmarkEnabled)
	  {
    recordSimInitialScanCpuContextApplyNanoseconds(simElapsedNanoseconds(contextApplyStart));
  }
	  finalizeSimCudaInitialRunSummariesToContext(summaries,
	                                             context,
	                                             benchmarkEnabled,
	                                             chunkedHandoffMaintainedHostSafeStore,
	                                             chunkedHandoffMaintainedHostSafeStore);
	  if(benchmarkEnabled)
	  {
	    recordSimInitialScanCpuMergeNanoseconds(simElapsedNanoseconds(cpuMergeStart));
	  }
	}

inline bool collectSimCudaProposalStatesForLoop(int maxProposalCount,
                                                const SimKernelContext &context,
                                                vector<SimScanCudaCandidateState> &proposalStates,
                                                bool *outUsedGpuSafeStore = NULL,
                                                string *errorOut = NULL)
{
  auto collectContextFrontierStates = [&](int maxCount) -> bool
  {
    proposalStates.clear();
    if(maxCount <= 0 || context.candidateCount <= 0)
    {
      if(errorOut != NULL)
      {
        errorOut->clear();
      }
      return true;
    }

    recordSimProposalLoopSourceFromInitial();
    vector<SimCandidate> frontierStates(static_cast<size_t>(context.candidateCount));
    for(long candidateIndex = 0; candidateIndex < context.candidateCount; ++candidateIndex)
    {
      frontierStates[static_cast<size_t>(candidateIndex)] =
        context.candidates[static_cast<size_t>(candidateIndex)];
    }

    proposalStates.reserve(static_cast<size_t>(min(static_cast<long>(maxCount),context.candidateCount)));
    long frontierCount = context.candidateCount;
    while(frontierCount > 0 && static_cast<int>(proposalStates.size()) < maxCount)
    {
      long bestIndex = 0;
      for(long candidateIndex = 1; candidateIndex < frontierCount; ++candidateIndex)
      {
        if(frontierStates[static_cast<size_t>(candidateIndex)].SCORE >
           frontierStates[static_cast<size_t>(bestIndex)].SCORE)
        {
          bestIndex = candidateIndex;
        }
      }

      proposalStates.push_back(makeSimScanCudaCandidateState(frontierStates[static_cast<size_t>(bestIndex)]));
      --frontierCount;
      if(bestIndex != frontierCount)
      {
        frontierStates[static_cast<size_t>(bestIndex)] =
          frontierStates[static_cast<size_t>(frontierCount)];
      }
    }

    if(proposalStates.empty())
    {
      recordSimProposalLoopFallbackReason(SIM_PROPOSAL_LOOP_FALLBACK_EMPTY_SELECTION);
      return false;
    }
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  };

  proposalStates.clear();
  if(outUsedGpuSafeStore != NULL)
  {
    *outUsedGpuSafeStore = false;
  }
  if(maxProposalCount <= 0)
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }

  if((simCudaMainlineResidencyEnabledRuntime() ||
      simCudaDeviceKLoopEnabledRuntime() ||
      simCudaLocateDeviceKLoopEnabledRuntime()) &&
     context.gpuSafeCandidateStateStore.valid)
  {
    const std::chrono::steady_clock::time_point deviceKLoopStart =
      std::chrono::steady_clock::now();
    bool usedFrontierCache = false;
    if(!sim_scan_cuda_select_top_disjoint_candidate_states_from_persistent_store(
         context.gpuSafeCandidateStateStore,
         maxProposalCount,
         &proposalStates,
         errorOut,
         &usedFrontierCache))
    {
      recordSimProposalLoopSourceFromSafeStore();
      recordSimProposalLoopSourceFromGpuSafeStore();
      if(usedFrontierCache)
      {
        recordSimProposalLoopSourceFromGpuFrontierCache();
      }
      else
      {
        recordSimProposalLoopSourceFromGpuSafeStoreFull();
      }
      recordSimProposalLoopFallbackReason(SIM_PROPOSAL_LOOP_FALLBACK_SELECTOR_FAILURE);
      return false;
    }
    recordSimDeviceKLoopNanoseconds(simElapsedNanoseconds(deviceKLoopStart));
    recordSimProposalLoopSourceFromSafeStore();
    recordSimProposalLoopSourceFromGpuSafeStore();
    if(usedFrontierCache)
    {
      recordSimProposalLoopSourceFromGpuFrontierCache();
    }
    else
    {
      recordSimProposalLoopSourceFromGpuSafeStoreFull();
    }
    if(outUsedGpuSafeStore != NULL)
    {
      *outUsedGpuSafeStore = true;
    }
    if(proposalStates.empty())
    {
      recordSimProposalLoopFallbackReason(SIM_PROPOSAL_LOOP_FALLBACK_EMPTY_SELECTION);
      return false;
    }
    return true;
  }

  if((simCudaMainlineResidencyEnabledRuntime() ||
      simCudaDeviceKLoopEnabledRuntime()) &&
     context.safeCandidateStateStore.valid &&
     !context.safeCandidateStateStore.states.empty())
  {
    recordSimProposalLoopSourceFromSafeStore();
    if(!sim_scan_cuda_select_top_disjoint_candidate_states(context.safeCandidateStateStore.states,
                                                           maxProposalCount,
                                                           &proposalStates,
                                                           errorOut))
    {
      recordSimProposalLoopFallbackReason(SIM_PROPOSAL_LOOP_FALLBACK_SELECTOR_FAILURE);
      return false;
    }
    if(proposalStates.empty())
    {
      recordSimProposalLoopFallbackReason(SIM_PROPOSAL_LOOP_FALLBACK_EMPTY_SELECTION);
      return false;
    }
    return true;
  }

  if(simCudaMainlineResidencyEnabledRuntime() &&
     context.candidateCount > 0)
  {
    return collectContextFrontierStates(maxProposalCount);
  }

  if(context.proposalCandidateLoop)
  {
    return collectContextFrontierStates(maxProposalCount);
  }

  if(context.safeCandidateStateStore.valid &&
     !context.safeCandidateStateStore.states.empty())
  {
    recordSimProposalLoopSourceFromSafeStore();
    if(!sim_scan_cuda_select_top_disjoint_candidate_states(context.safeCandidateStateStore.states,
                                                           maxProposalCount,
                                                           &proposalStates,
                                                           errorOut))
    {
      recordSimProposalLoopFallbackReason(SIM_PROPOSAL_LOOP_FALLBACK_SELECTOR_FAILURE);
      return false;
    }
    if(proposalStates.empty())
    {
      recordSimProposalLoopFallbackReason(SIM_PROPOSAL_LOOP_FALLBACK_EMPTY_SELECTION);
      return false;
    }
    return true;
  }

  recordSimProposalLoopFallbackReason(SIM_PROPOSAL_LOOP_FALLBACK_NO_STORE);
  return false;
}

inline bool runSimCandidateLoopWithCudaSequentialProposalSelection(const SimRequest &request,
                                                                  const char *A,
                                                                  const char *B,
                                                                  long targetLength,
                                                                  long rule,
                                                                  SimKernelContext &context,
                                                                  vector<struct triplex> &triplex_list,
                                                                  bool requireGpuSafeStoreSelection,
                                                                  const char *failureLabel)
{
  const bool simFast = simFastEnabledRuntime();
  int fastUpdateBudget = simFast ? simFastUpdateBudgetRuntime() : 0;
  const bool fastUpdateOnFail = simFast && simFastUpdateOnFailEnabledRuntime();
  bool materializedAny = false;

  for(int iteration = 0; iteration < K; ++iteration)
  {
    vector<SimScanCudaCandidateState> proposalStates;
    bool usedGpuSafeStore = false;
    string cudaError;
    if(!collectSimCudaProposalStatesForLoop(1,
                                            context,
                                            proposalStates,
                                            &usedGpuSafeStore,
                                            &cudaError))
    {
      if(!materializedAny &&
         simCudaValidateEnabledRuntime() &&
         failureLabel != NULL &&
         failureLabel[0] != '\0' &&
         !cudaError.empty())
      {
        fprintf(stderr,"%s: %s\n",failureLabel,cudaError.c_str());
      }
      return materializedAny;
    }
    if(proposalStates.empty() || (requireGpuSafeStoreSelection && !usedGpuSafeStore))
    {
      return materializedAny;
    }

    const SimScanCudaCandidateState &proposal = proposalStates[0];
    const long stari = static_cast<long>(proposal.startI) + 1;
    const long starj = static_cast<long>(proposal.startJ) + 1;
    const long endi = static_cast<long>(proposal.endI);
    const long endj = static_cast<long>(proposal.endJ);
    const long m1 = static_cast<long>(proposal.top);
    const long mm = static_cast<long>(proposal.bot);
    const long n1 = static_cast<long>(proposal.left);
    const long nn = static_cast<long>(proposal.right);
    const uint64_t proposalStartCoord = simScanCudaCandidateStateStartCoord(proposal);
    const vector<uint64_t> consumedStartCoords(1,proposalStartCoord);

    eraseSimCandidatesByStartCoords(consumedStartCoords,context);
    if(context.safeCandidateStateStore.valid)
    {
      eraseSimSafeCandidateStateStoreStartCoords(consumedStartCoords,context);
    }
    if(context.gpuSafeCandidateStateStore.valid)
    {
      string eraseError;
      if(!eraseSimCudaPersistentSafeCandidateStateStoreStartCoords(consumedStartCoords,
                                                                   context.gpuSafeCandidateStateStore,
                                                                   &eraseError))
      {
	        recordSimFrontierCacheInvalidateProposalErase();
	        recordSimFrontierCacheInvalidateReleaseOrError();
	        releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
	        context.initialSafeStoreHandoffActive = false;
	        if(simCudaValidateEnabledRuntime() && !eraseError.empty())
        {
          fprintf(stderr,"SIM CUDA proposal erase failed: %s\n",eraseError.c_str());
        }
      }
    }

    if(!materializeSimProposalStates(request,
                                     A,
                                     B,
                                     targetLength,
                                     rule,
                                     proposalStates,
                                     context,
                                     triplex_list))
    {
      if(!simFast)
      {
        break;
      }
      if(fastUpdateOnFail && fastUpdateBudget > 0)
      {
        updateSimCandidatesAfterTraceback(A,B,stari,endi,starj,endj,m1,mm,n1,nn,context);
        --fastUpdateBudget;
      }
      continue;
    }

    materializedAny = true;
    if(iteration + 1 < K)
    {
      if(!simFast)
      {
        updateSimCandidatesAfterTraceback(A,B,stari,endi,starj,endj,m1,mm,n1,nn,context);
      }
      else if(fastUpdateBudget > 0)
      {
        updateSimCandidatesAfterTraceback(A,B,stari,endi,starj,endj,m1,mm,n1,nn,context);
        --fastUpdateBudget;
      }
    }
  }

  return materializedAny;
}

inline bool runSimCandidateLoopWithCudaLocateDeviceKLoop(const SimRequest &request,
                                                         const char *A,
                                                         const char *B,
                                                         long targetLength,
                                                         long rule,
                                                         SimKernelContext &context,
                                                         vector<struct triplex> &triplex_list)
{
  if(!simCudaLocateDeviceKLoopEnabledRuntime() ||
     !context.gpuSafeCandidateStateStore.valid)
  {
    return false;
  }

  recordSimLocateDeviceKLoopAttempt();
  if(!runSimCandidateLoopWithCudaSequentialProposalSelection(request,
                                                             A,
                                                             B,
                                                             targetLength,
                                                             rule,
                                                             context,
                                                             triplex_list,
                                                             true,
                                                             "SIM CUDA locate device-k-loop helper failed"))
  {
    return false;
  }

  recordSimLocateDeviceKLoopShortCircuit();
  return true;
}

inline bool runSimCandidateLoopWithCudaProposals(const SimRequest &request,
                                                 const char *A,
                                                 const char *B,
                                                 long targetLength,
                                                 long rule,
                                                 SimKernelContext &context,
                                                 vector<struct triplex> &triplex_list)
{
  if(!simCudaProposalLoopEnabledRuntime())
  {
    return false;
  }

  recordSimProposalLoopAttempt();
  return runSimCandidateLoopWithCudaSequentialProposalSelection(request,
                                                                A,
                                                                B,
                                                                targetLength,
                                                                rule,
                                                                context,
                                                                triplex_list,
                                                                false,
                                                                "SIM CUDA proposal helper failed");
}

inline void ensureSimTracebackScratchCapacity(long targetLength,long rl,SimKernelContext &context)
{
  const size_t requiredTracebackLength = static_cast<size_t>(targetLength + rl + 2);
  if(context.tracebackScratch.size() < requiredTracebackLength)
  {
    context.tracebackScratch.resize(requiredTracebackLength,0);
  }
}

inline bool canSimTracebackUseCudaForCandidate(long rl,
                                               long cl,
                                               long starj,
                                               const SimKernelContext &context)
{
  return rl > 0 &&
         cl > 0 &&
         rl <= static_cast<long>(simTracebackCudaMaxDimRuntime()) &&
         cl <= static_cast<long>(simTracebackCudaMaxDimRuntime()) &&
         (static_cast<long long>(rl + 1) * static_cast<long long>(cl + 1)) <= simTracebackCudaMaxCellsRuntime() &&
         context.gapOpen >= 0 &&
         context.gapExtend >= 0 &&
         rl <= static_cast<long>(0x7fffffff) &&
         cl <= static_cast<long>(0x7fffffff) &&
         starj >= 0 &&
         starj <= static_cast<long>(0x7fffffff);
}

inline bool convertSimTracebackOpsToScratchAndBlock(const vector<unsigned char> &opsReversed,
                                                    long rl,
                                                    long cl,
                                                    long stari,
                                                    long starj,
                                                    SimKernelContext &context)
{
  size_t outCount = 0;
  int pendingGapType = 0;
  int pendingGapLen = 0;

  auto flushGap = [&]() -> bool
  {
    if(pendingGapLen <= 0)
    {
      return true;
    }
    if(outCount >= context.tracebackScratch.size())
    {
      return false;
    }
    context.tracebackScratch[outCount++] = (pendingGapType == 1) ? pendingGapLen : -pendingGapLen;
    pendingGapType = 0;
    pendingGapLen = 0;
    return true;
  };

  bool ok = true;
  long localI = 0;
  long localJ = 0;
  for(vector<unsigned char>::const_reverse_iterator it = opsReversed.rbegin(); it != opsReversed.rend(); ++it)
  {
    const unsigned char op = *it;
    if(op == 0)
    {
      if(!flushGap())
      {
        ok = false;
        break;
      }
      if(outCount >= context.tracebackScratch.size())
      {
        ok = false;
        break;
      }
      context.tracebackScratch[outCount++] = 0;
      ++localI;
      ++localJ;
    }
    else if(op == 1)
    {
      if(pendingGapType == 1)
      {
        ++pendingGapLen;
      }
      else
      {
        if(!flushGap())
        {
          ok = false;
          break;
        }
        pendingGapType = 1;
        pendingGapLen = 1;
      }
      ++localJ;
    }
    else if(op == 2)
    {
      if(pendingGapType == 2)
      {
        ++pendingGapLen;
      }
      else
      {
        if(!flushGap())
        {
          ok = false;
          break;
        }
        pendingGapType = 2;
        pendingGapLen = 1;
      }
      ++localI;
    }
    else
    {
      ok = false;
      break;
    }
  }
  if(ok)
  {
    ok = flushGap();
  }
  if(ok && (localI != rl || localJ != cl))
  {
    ok = false;
  }
  if(!ok)
  {
    return false;
  }

  long globalI = stari - 1;
  long globalJ = starj - 1;
  for(vector<unsigned char>::const_reverse_iterator it = opsReversed.rbegin(); it != opsReversed.rend(); ++it)
  {
    const unsigned char op = *it;
    if(op == 0)
    {
      ++globalI;
      ++globalJ;
      markSimDiagonalBlocked(context.workspace, globalI, globalJ);
    }
    else if(op == 1)
    {
      ++globalJ;
    }
    else
    {
      ++globalI;
    }
  }
  return true;
}

inline bool postprocessSimMaterializedCandidate(const SimRequest &request,
                                                const char *A,
                                                const char *B,
                                                long targetLength,
                                                long score,
                                                long stari,
                                                long starj,
                                                long endi,
                                                long endj,
                                                long rule,
                                                SimKernelContext &context,
                                                vector<struct triplex> &triplex_list)
{
  const long rl = endi - stari + 1;
  const long cl = endj - starj + 1;
  int nt = endi - stari + 1;
  float identity;
  string stri_align;
  string strj_align;
  float final_score = 0.0f;
  struct triplex atriplex;
  float tri_score = 0.0f;
  char prechar = 0;
  char curchar = 0;

  if(simWriteAlignStringsEnabledRuntime())
  {
    identity = display(&A[stari]-1,&B[starj]-1,rl,cl,context.tracebackScratch.data(),stari,starj,stri_align,strj_align);
    nt = strj_align.size();
    if(request.reverseMode==0&&(nt>=request.ntMin&&nt<=request.ntMax))
    {
      string seqtmp=request.sourceSequence;
      if(request.parallelMode>0)  complement(seqtmp);
      int j = 0;
      float hashvalue=0, prescore=0;
      for(long i = 0; i < static_cast<long>(strj_align.size()) ; i++ )
      {
        if(strj_align[static_cast<size_t>(i)]=='-')
        {
          curchar='-';
          hashvalue=triplex_score(curchar, stri_align[static_cast<size_t>(i)],request.parallelMode);
        }
        else
        {
          curchar=seqtmp[static_cast<size_t>(starj+j-1)];
          hashvalue=triplex_score(curchar, stri_align[static_cast<size_t>(i)], request.parallelMode);
          j++;
        }
        if( (curchar==prechar) && curchar=='A')
        {
          tri_score=tri_score-prescore+request.penaltyT;
          hashvalue=request.penaltyT;
        }
        if( (curchar==prechar) && curchar=='G')
        {
          tri_score=tri_score-prescore+request.penaltyC;
          hashvalue=request.penaltyC;
        }
        prescore=hashvalue;
        prechar=curchar;
        tri_score+=hashvalue;
      }
      score/=10;
      final_score=(float)score/nt;
      tri_score/=nt;
      atriplex=triplex(stari,endi,starj+request.dnaStartPos,endj+request.dnaStartPos,request.reverseMode,request.parallelMode,rule,nt,final_score,identity,tri_score,stri_align,strj_align,0,0,0,0);
    }
    else if(request.reverseMode==1&&(nt>=request.ntMin&&nt<=request.ntMax))
    {
      string seqtmp=request.sourceSequence;
      if(request.parallelMode<0) complement(seqtmp);
      int j = 0;
      float hashvalue=0, prescore=0;
      for(long i = 0; i < static_cast<long>(strj_align.size()) ; i++ )
      {
        if(strj_align[static_cast<size_t>(i)]=='-')
        {
          curchar='-';
          hashvalue=triplex_score(curchar, stri_align[static_cast<size_t>(i)], request.parallelMode);
        }
        else
        {
          curchar=seqtmp[static_cast<size_t>(targetLength-starj-j)];
          hashvalue=triplex_score(curchar, stri_align[static_cast<size_t>(i)], request.parallelMode);
          j++;
        }
        if( (curchar==prechar) && curchar=='A')
        {
          tri_score=tri_score-prescore-1000;
          hashvalue=-1000;
        }
        if( (curchar==prechar) && curchar=='G')
        {
          tri_score=tri_score-prescore;
          hashvalue=0;
        }
        prescore=hashvalue;
        prechar=curchar;
        tri_score+=hashvalue;
      }
      score/=10;
      final_score=(float)score/nt;
      tri_score/=nt;
      atriplex=triplex(stari,endi,targetLength-starj+request.dnaStartPos+1,targetLength-endj+request.dnaStartPos+1,request.reverseMode,request.parallelMode,rule,nt,final_score,identity,tri_score,stri_align,strj_align,0,0,0,0);
    }
  }
  else
  {
    computeSimIdentityAndNtFromTracebackScript(&A[stari]-1,&B[starj]-1,rl,cl,context.tracebackScratch.data(),identity,nt);
    if(request.reverseMode==0&&(nt>=request.ntMin&&nt<=request.ntMax))
    {
      tri_score = computeSimTriScoreSumFromTracebackScript(request, &A[stari]-1, rl, cl, context.tracebackScratch.data(), starj, targetLength);
      score/=10;
      final_score=(float)score/nt;
      tri_score/=nt;
      atriplex=triplex(stari,endi,starj+request.dnaStartPos,endj+request.dnaStartPos,request.reverseMode,request.parallelMode,rule,nt,final_score,identity,tri_score,stri_align,strj_align,0,0,0,0);
    }
    else if(request.reverseMode==1&&(nt>=request.ntMin&&nt<=request.ntMax))
    {
      tri_score = computeSimTriScoreSumFromTracebackScript(request, &A[stari]-1, rl, cl, context.tracebackScratch.data(), starj, targetLength);
      score/=10;
      final_score=(float)score/nt;
      tri_score/=nt;
      atriplex=triplex(stari,endi,targetLength-starj+request.dnaStartPos+1,targetLength-endj+request.dnaStartPos+1,request.reverseMode,request.parallelMode,rule,nt,final_score,identity,tri_score,stri_align,strj_align,0,0,0,0);
    }
  }

  if(nt>=request.ntMin)
  {
    triplex_list.push_back(atriplex);
  }
  return true;
}

inline bool finalizeSimMaterializedCandidate(const SimRequest &request,
                                             const char *A,
                                             const char *B,
                                             long targetLength,
                                             long score,
                                             long stari,
                                             long starj,
                                             long endi,
                                             long endj,
                                             long rule,
                                             bool recordProposalPostTiming,
                                             SimKernelContext &context,
                                             vector<struct triplex> &triplex_list,
                                             bool benchmarkEnabled,
                                             const std::chrono::steady_clock::time_point &materializeStart)
{
  if(score/10.0 <= request.minScore)
  {
    if(recordProposalPostTiming)
    {
      recordSimProposalPostScoreRejects();
    }
    if(benchmarkEnabled)
    {
      recordSimMaterializeNanoseconds(simElapsedNanoseconds(materializeStart));
    }
    return false;
  }

  const std::chrono::steady_clock::time_point tracebackPostStart =
    benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
  const size_t triplexCountBefore = triplex_list.size();
  const bool success = postprocessSimMaterializedCandidate(request,
                                                           A,
                                                           B,
                                                           targetLength,
                                                           score,
                                                           stari,
                                                           starj,
                                                           endi,
                                                           endj,
                                                           rule,
                                                           context,
                                                           triplex_list);
  if(recordProposalPostTiming && success && triplex_list.size() == triplexCountBefore)
  {
    recordSimProposalPostNtRejects();
  }
  if(benchmarkEnabled)
  {
    const uint64_t postNanoseconds = simElapsedNanoseconds(tracebackPostStart);
    recordSimTracebackPostNanoseconds(postNanoseconds);
    if(recordProposalPostTiming)
    {
      recordSimProposalPostNanoseconds(postNanoseconds);
    }
    recordSimMaterializeNanoseconds(simElapsedNanoseconds(materializeStart));
  }
  return success;
}

inline bool materializeSimProposalStates(const SimRequest &request,
                                         const char *A,
                                         const char *B,
                                         long targetLength,
                                         long rule,
                                         const vector<SimScanCudaCandidateState> &proposalStates,
                                         SimKernelContext &context,
                                         vector<struct triplex> &triplex_list)
{
  if(proposalStates.empty())
  {
    return false;
  }

  const SimProposalMaterializeBackend backend = simProposalMaterializeBackendRuntime();
  recordSimProposalMaterializeBackendCall(backend);
  uint64_t selectedBoxCells = 0;
  for(size_t proposalIndex = 0; proposalIndex < proposalStates.size(); ++proposalIndex)
  {
    const SimScanCudaCandidateState &proposal = proposalStates[proposalIndex];
    const long stari = static_cast<long>(proposal.startI) + 1;
    const long starj = static_cast<long>(proposal.startJ) + 1;
    const long endi = static_cast<long>(proposal.endI);
    const long endj = static_cast<long>(proposal.endJ);
    if(endi < stari || endj < starj)
    {
      continue;
    }
    const uint64_t queryBases = static_cast<uint64_t>(endi - stari + 1);
    const uint64_t targetBases = static_cast<uint64_t>(endj - starj + 1);
    selectedBoxCells += queryBases * targetBases;
  }
  recordSimProposalSelectedBoxCells(selectedBoxCells);

  const bool benchmarkEnabled = simBenchmarkEnabledRuntime();
  const bool fallbackOnTie = simTracebackCudaFallbackOnTieEnabledRuntime();
  const long proposalTracebackMinCells = simProposalTracebackMinCellsRuntime();

  auto recordProposalMaterializedBases = [&](long rl,long cl) -> void
  {
    recordSimProposalMaterialized();
    recordSimProposalMaterializedQueryBases(static_cast<uint64_t>(rl));
    recordSimProposalMaterializedTargetBases(static_cast<uint64_t>(cl));
  };

  auto materializeProposalWithCpu = [&](const SimScanCudaCandidateState &proposal,
                                        bool countCpuDirect,
                                        bool allowTracebackCuda) -> bool
  {
    const long score = static_cast<long>(proposal.score);
    const long stari = static_cast<long>(proposal.startI) + 1;
    const long starj = static_cast<long>(proposal.startJ) + 1;
    const long endi = static_cast<long>(proposal.endI);
    const long endj = static_cast<long>(proposal.endJ);
    if(endi < stari || endj < starj)
    {
      return true;
    }
    const long rl = endi - stari + 1;
    const long cl = endj - starj + 1;
    const uint64_t tracebackCells = static_cast<uint64_t>(rl + 1) * static_cast<uint64_t>(cl + 1);
    if(countCpuDirect)
    {
      recordSimProposalTracebackCpuDirect();
    }
    recordSimProposalTracebackCpuCells(tracebackCells);
    if(!materializeSimCandidateImpl(request,
                                    A,
                                    B,
                                    targetLength,
                                    score,
                                    stari,
                                    starj,
                                    endi,
                                    endj,
                                    rule,
                                    true,
                                    allowTracebackCuda,
                                    context,
                                    triplex_list))
    {
      return false;
    }
    recordProposalMaterializedBases(rl,cl);
    return true;
  };

  if(backend == SIM_PROPOSAL_MATERIALIZE_BACKEND_CPU)
  {
    for(size_t proposalIndex = 0; proposalIndex < proposalStates.size(); ++proposalIndex)
    {
      const SimScanCudaCandidateState &proposal = proposalStates[proposalIndex];
      const long stari = static_cast<long>(proposal.startI) + 1;
      const long starj = static_cast<long>(proposal.startJ) + 1;
      const long endi = static_cast<long>(proposal.endI);
      const long endj = static_cast<long>(proposal.endJ);
      if(endi >= stari && endj >= starj)
      {
        const long rl = endi - stari + 1;
        const long cl = endj - starj + 1;
        if(canSimTracebackUseCudaForCandidate(rl,cl,starj,context))
        {
          recordSimProposalTracebackCudaEligible();
        }
      }
      if(!materializeProposalWithCpu(proposal,true,true))
      {
        break;
      }
    }
    return true;
  }

  vector<SimTracebackCudaBatchRequest> batchRequests;
  vector<int> batchItemIndex(proposalStates.size(),-1);
  vector<unsigned char> directCpuProposal(proposalStates.size(),0);
  vector< vector<uint64_t> > blockedDenseWordsStorage(proposalStates.size());
  batchRequests.reserve(proposalStates.size());
  for(size_t proposalIndex = 0; proposalIndex < proposalStates.size(); ++proposalIndex)
  {
    const SimScanCudaCandidateState &proposal = proposalStates[proposalIndex];
    const long stari = static_cast<long>(proposal.startI) + 1;
    const long starj = static_cast<long>(proposal.startJ) + 1;
    const long endi = static_cast<long>(proposal.endI);
    const long endj = static_cast<long>(proposal.endJ);
    if(endi < stari || endj < starj)
    {
      continue;
    }
    const long rl = endi - stari + 1;
    const long cl = endj - starj + 1;
    const uint64_t boxCells = static_cast<uint64_t>(rl) * static_cast<uint64_t>(cl);
    const bool cudaEligible = canSimTracebackUseCudaForCandidate(rl,cl,starj,context);
    if(cudaEligible)
    {
      recordSimProposalTracebackCudaEligible();
    }

    bool useBatch = false;
    if(backend == SIM_PROPOSAL_MATERIALIZE_BACKEND_HYBRID)
    {
      if(cudaEligible && boxCells < static_cast<uint64_t>(proposalTracebackMinCells))
      {
        recordSimProposalTracebackCudaSizeFiltered();
      }
      useBatch = cudaEligible && boxCells >= static_cast<uint64_t>(proposalTracebackMinCells);
    }
    else
    {
      useBatch = cudaEligible;
    }
    if(!useBatch)
    {
      directCpuProposal[proposalIndex] = 1;
      continue;
    }

    const auto blockedView =
      makeSimBlockedWordsView(context.workspace,stari,endi,starj,endj,blockedDenseWordsStorage[proposalIndex]);

    SimTracebackCudaBatchRequest batchRequest;
    batchRequest.A = &A[stari] - 1;
    batchRequest.B = &B[starj] - 1;
    batchRequest.queryLength = static_cast<int>(rl);
    batchRequest.targetLength = static_cast<int>(cl);
    batchRequest.matchScore = static_cast<int>(context.scoreMatrix['A']['A']);
    batchRequest.mismatchScore = static_cast<int>(context.scoreMatrix['A']['C']);
    batchRequest.gapOpen = static_cast<int>(context.gapOpen);
    batchRequest.gapExtend = static_cast<int>(context.gapExtend);
    batchRequest.globalColStart = static_cast<int>(starj);
    batchRequest.blockedWords = blockedView.words;
    batchRequest.blockedWordStart = blockedView.wordStart;
    batchRequest.blockedWordCount = blockedView.wordCount;
    batchRequest.blockedWordStride = blockedView.wordStride;
    batchItemIndex[proposalIndex] = static_cast<int>(batchRequests.size());
    batchRequests.push_back(batchRequest);
  }
  recordSimProposalTracebackBatchRequests(static_cast<uint64_t>(batchRequests.size()));
  if(!batchRequests.empty())
  {
    recordSimProposalTracebackBatchBatches();
  }

  vector<SimTracebackCudaBatchItemResult> batchItems;
  SimTracebackCudaBatchResult batchResult;
  string cudaError;
  bool batchCallOk = true;
  if(!batchRequests.empty())
  {
    batchCallOk = sim_traceback_cuda_traceback_global_affine_batch(batchRequests,
                                                                   &batchItems,
                                                                   &batchResult,
                                                                   &cudaError);
    if(!batchCallOk && simCudaValidateEnabledRuntime() && !cudaError.empty())
    {
      fprintf(stderr, "SIM CUDA traceback batch failed: %s\n", cudaError.c_str());
    }
    if(batchCallOk && benchmarkEnabled && batchResult.usedCuda)
    {
      const uint64_t batchGpuNanoseconds = simSecondsToNanoseconds(batchResult.gpuSeconds);
      recordSimProposalTracebackBatchGpuNanoseconds(batchGpuNanoseconds);
      recordSimTracebackDpNanoseconds(batchGpuNanoseconds);
      recordSimMaterializeNanoseconds(batchGpuNanoseconds);
    }
  }

  for(size_t proposalIndex = 0; proposalIndex < proposalStates.size(); ++proposalIndex)
  {
    const SimScanCudaCandidateState &proposal = proposalStates[proposalIndex];
    const long score = static_cast<long>(proposal.score);
    const long stari = static_cast<long>(proposal.startI) + 1;
    const long starj = static_cast<long>(proposal.startJ) + 1;
    const long endi = static_cast<long>(proposal.endI);
    const long endj = static_cast<long>(proposal.endJ);
    if(endi < stari || endj < starj)
    {
      continue;
    }
    const long rl = endi - stari + 1;
    const long cl = endj - starj + 1;
    const uint64_t tracebackCells = static_cast<uint64_t>(rl + 1) * static_cast<uint64_t>(cl + 1);
    const int itemIndex = proposalIndex < batchItemIndex.size() ? batchItemIndex[proposalIndex] : -1;
    if((proposalIndex < directCpuProposal.size() && directCpuProposal[proposalIndex] != 0) || itemIndex < 0)
    {
      const bool allowTracebackCuda = backend != SIM_PROPOSAL_MATERIALIZE_BACKEND_HYBRID;
      if(!materializeProposalWithCpu(proposal,true,allowTracebackCuda))
      {
        break;
      }
      continue;
    }

    bool fallbackToCpu = !batchCallOk;
    bool tieFallback = false;
    bool batchHadTie = false;
    bool batchFailed = !batchCallOk;
    const SimTracebackCudaBatchItemResult *batchItem =
      (!fallbackToCpu && static_cast<size_t>(itemIndex) < batchItems.size()) ? &batchItems[static_cast<size_t>(itemIndex)] : NULL;

    if(batchItem != NULL)
    {
      if(!batchItem->success)
      {
        fallbackToCpu = true;
        batchFailed = true;
      }
      else
      {
        batchHadTie = batchItem->tracebackResult.hadTie;
        if(fallbackOnTie && batchHadTie)
        {
          fallbackToCpu = true;
          tieFallback = true;
        }
        else
        {
          ensureSimTracebackScratchCapacity(targetLength,rl,context);
          if(!convertSimTracebackOpsToScratchAndBlock(batchItem->opsReversed,
                                                      rl,
                                                      cl,
                                                      stari,
                                                      starj,
                                                      context))
          {
            fallbackToCpu = true;
            batchFailed = true;
          }
          else
          {
            const std::chrono::steady_clock::time_point materializeStart =
              benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
            recordSimProposalTracebackBatchSuccess();
            recordSimTracebackCandidate(batchHadTie);
            recordSimTracebackTotalCells(tracebackCells);
            recordSimTracebackBackend(true);
            recordSimProposalTracebackCudaCells(tracebackCells);
            if(!finalizeSimMaterializedCandidate(request,
                                                 A,
                                                 B,
                                                 targetLength,
                                                 score,
                                                 stari,
                                                 starj,
                                                 endi,
                                                 endj,
                                                 rule,
                                                 true,
                                                 context,
                                                 triplex_list,
                                                 benchmarkEnabled,
                                                 materializeStart))
            {
              break;
            }
            recordProposalMaterializedBases(rl,cl);
            continue;
          }
        }
      }
    }
    else
    {
      fallbackToCpu = true;
      batchFailed = true;
    }

    if(batchHadTie)
    {
      simTracebackTieCount().fetch_add(1, std::memory_order_relaxed);
    }
    if(batchFailed)
    {
      recordSimProposalTracebackCudaBatchFailed();
    }
    recordSimProposalTracebackBatchFallbacks();
    if(tieFallback)
    {
      recordSimProposalTracebackBatchTieFallbacks();
    }
    const bool allowTracebackCuda = backend != SIM_PROPOSAL_MATERIALIZE_BACKEND_HYBRID;
    if(!materializeProposalWithCpu(proposal,false,allowTracebackCuda))
    {
      break;
    }
  }
  return true;
}

inline void runSimCandidateLoop(const SimRequest &request,
                                const char *A,
                                const char *B,
                                long targetLength,
                                long rule,
                                SimKernelContext &context,
                                vector<struct triplex> &triplex_list)
{
  SimCandidate currentCandidate;
  long score;
  long stari, starj, endi, endj;
  long m1, mm, n1, nn;
  const bool simFast = simFastEnabledRuntime();
  int fastUpdateBudget = simFast ? simFastUpdateBudgetRuntime() : 0;
  const bool fastUpdateOnFail = simFast && simFastUpdateOnFailEnabledRuntime();

  if(runSimCandidateLoopWithCudaLocateDeviceKLoop(request,A,B,targetLength,rule,context,triplex_list))
  {
    return;
  }

  if(runSimCandidateLoopWithCudaProposals(request,A,B,targetLength,rule,context,triplex_list))
  {
    recordSimProposalLoopShortCircuit();
    return;
  }

  for(long count = context.candidateCount - 1; count >= 0; --count)
  {
    if(!popHighestScoringSimCandidate(context,currentCandidate))
    {
      break;
    }

    score = currentCandidate.SCORE;
    stari = currentCandidate.STARI + 1;
    starj = currentCandidate.STARJ + 1;
    endi = currentCandidate.ENDI;
    endj = currentCandidate.ENDJ;
    m1 = currentCandidate.TOP;
    mm = currentCandidate.BOT;
    n1 = currentCandidate.LEFT;
    nn = currentCandidate.RIGHT;

    if(!materializeSimCandidate(request,A,B,targetLength,score,stari,starj,endi,endj,rule,context,triplex_list))
    {
      if(!simFast)
      {
        break;
      }
      if(fastUpdateOnFail && fastUpdateBudget > 0)
      {
        updateSimCandidatesAfterTraceback(A,B,stari,endi,starj,endj,m1,mm,n1,nn,context);
        --fastUpdateBudget;
      }
      continue;
    }

    if(count)
    {
      if(!simFast)
      {
        updateSimCandidatesAfterTraceback(A,B,stari,endi,starj,endj,m1,mm,n1,nn,context);
      }
      else if(fastUpdateBudget > 0)
      {
        updateSimCandidatesAfterTraceback(A,B,stari,endi,starj,endj,m1,mm,n1,nn,context);
        --fastUpdateBudget;
      }
    }
  }
}

inline void fillSimScoreMatrixInt(const long scoreMatrix[128][128],int scoreMatrixInt[128][128])
{
  for(int i = 0; i < 128; ++i)
  {
    for(int j = 0; j < 128; ++j)
    {
      scoreMatrixInt[i][j] = static_cast<int>(scoreMatrix[i][j]);
    }
  }
}

inline SimBlockedWordsView makeSimBlockedWordsView(const SimWorkspace &workspace,
                                                   long rowStart,
                                                   long rowEnd,
                                                   long colStart,
                                                   long colEnd,
                                                   vector<uint64_t> &packedScratch)
{
  SimBlockedWordsView view;
  packedScratch.clear();
  if(rowStart > rowEnd || colStart > colEnd)
  {
    return view;
  }

  bool anyBlocked = false;
  for(long i = rowStart; i <= rowEnd; ++i)
  {
    if(!workspace.blocked[static_cast<size_t>(i)].empty())
    {
      anyBlocked = true;
      break;
    }
  }
  if(!anyBlocked)
  {
    return view;
  }

  const size_t wordStart = static_cast<size_t>(colStart) >> 6;
  const size_t wordEnd = static_cast<size_t>(colEnd) >> 6;
  const int blockedWordStart = static_cast<int>(wordStart);
  const int blockedWordCount = static_cast<int>(wordEnd >= wordStart ? (wordEnd - wordStart + 1) : 0);
  if(blockedWordCount <= 0)
  {
    return view;
  }

  view.wordStart = blockedWordStart;
  view.wordCount = blockedWordCount;
  if(simBlockedDenseMirrorEnabled(workspace))
  {
    const uint64_t *rowPtr = simBlockedDenseMirrorRowPtr(workspace,rowStart);
    if(rowPtr != NULL)
    {
      view.words = rowPtr + wordStart;
      view.wordStride = static_cast<int>(workspace.blockedDenseStrideWords);
      return view;
    }
  }

  const int rowCount = static_cast<int>(rowEnd - rowStart + 1);
  packedScratch.assign(static_cast<size_t>(rowCount) * static_cast<size_t>(blockedWordCount), 0);
  for(int localRow = 0; localRow < rowCount; ++localRow)
  {
    const vector<uint64_t> &blockedRow = workspace.blocked[static_cast<size_t>(rowStart + static_cast<long>(localRow))];
    if(blockedRow.empty() || blockedRow.size() <= wordStart)
    {
      continue;
    }
    const size_t availableWords = blockedRow.size() - wordStart;
    const size_t toCopy = min(static_cast<size_t>(blockedWordCount), availableWords);
    if(toCopy > 0)
    {
      memcpy(packedScratch.data() + static_cast<size_t>(localRow) * static_cast<size_t>(blockedWordCount),
             blockedRow.data() + wordStart,
             toCopy * sizeof(uint64_t));
    }
  }
  recordSimBlockedPackWords(static_cast<uint64_t>(rowCount) * static_cast<uint64_t>(blockedWordCount));
  view.words = packedScratch.data();
  view.wordStride = blockedWordCount;
  return view;
}

inline void applySimCudaReducedCandidates(const vector<SimScanCudaCandidateState> &candidateStates,
                                          int runningMin,
                                          SimKernelContext &context)
{
  context.gpuFrontierCacheInSync = false;
  context.candidateCount = static_cast<long>(candidateStates.size());
  for(size_t i = 0; i < candidateStates.size(); ++i)
  {
    context.candidates[i] = makeSimCandidateFromCudaState(candidateStates[i]);
  }
  clearSimCandidateStartIndex(context.candidateStartIndex);
  context.candidateMinHeap.clear();
  rebuildSimCandidateStructures(context);
  if(context.candidateCount > 0 && context.runningMin < static_cast<long>(runningMin))
  {
    context.runningMin = static_cast<long>(runningMin);
  }
}

inline void applySimCudaInitialReduceResults(const vector<SimScanCudaCandidateState> &candidateStates,
                                             int runningMin,
                                             const vector<SimScanCudaCandidateState> &allCandidateStates,
                                             SimCudaPersistentSafeStoreHandle &persistentSafeStoreHandle,
                                             uint64_t logicalEventCount,
                                             SimKernelContext &context,
                                             bool benchmarkEnabled,
                                             bool proposalCandidates)
{
  const std::chrono::steady_clock::time_point cpuMergeStart =
    benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();

  const std::chrono::steady_clock::time_point contextApplyStart =
    benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
  applySimCudaReducedCandidates(candidateStates,runningMin,context);
  if(benchmarkEnabled)
  {
    recordSimInitialScanCpuContextApplyNanoseconds(simElapsedNanoseconds(contextApplyStart));
  }
  context.proposalCandidateLoop = proposalCandidates;
  if(context.statsEnabled)
  {
    context.stats.eventsSeen += logicalEventCount;
  }

	  if(proposalCandidates)
	  {
	    releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
	    context.initialSafeStoreHandoffActive = false;
	    if(persistentSafeStoreHandle.valid)
    {
      resetSimCandidateStateStore(context.safeCandidateStateStore,false);
      moveSimCudaPersistentSafeStoreHandle(context.gpuSafeCandidateStateStore,persistentSafeStoreHandle);
      markSimGpuFrontierCacheSynchronized(context);
    }
    else
    {
      clearSimSafeCandidateStores(context);
      releaseSimCudaPersistentSafeCandidateStateStore(persistentSafeStoreHandle);
      clearSimCudaPersistentSafeStoreHandle(persistentSafeStoreHandle);
    }
  }
	  else
	  {
	    releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
	    context.initialSafeStoreHandoffActive = false;
	    if(persistentSafeStoreHandle.valid)
    {
      resetSimCandidateStateStore(context.safeCandidateStateStore,false);
      moveSimCudaPersistentSafeStoreHandle(context.gpuSafeCandidateStateStore,persistentSafeStoreHandle);
      markSimGpuFrontierCacheSynchronized(context);
    }
    else
    {
      SimCandidateStateStore &store = context.safeCandidateStateStore;
      const std::chrono::steady_clock::time_point safeStoreUpdateStart =
        benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
      resetSimCandidateStateStore(store,true);
      store.states = allCandidateStates;
      rebuildSimCandidateStateStoreIndex(store);
      if(benchmarkEnabled)
      {
        recordSimInitialScanCpuSafeStoreUpdateNanoseconds(simElapsedNanoseconds(safeStoreUpdateStart));
      }
      const std::chrono::steady_clock::time_point safeStorePruneStart =
        benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
      pruneSimSafeCandidateStateStore(context);
      if(benchmarkEnabled)
      {
        recordSimInitialScanCpuSafeStorePruneNanoseconds(simElapsedNanoseconds(safeStorePruneStart));
      }
    }
  }

  if(benchmarkEnabled)
  {
    recordSimInitialScanCpuMergeNanoseconds(simElapsedNanoseconds(cpuMergeStart));
  }
}

inline bool enumerateFullRescanSimCandidatesCuda(const char *A,
                                                 const char *B,
                                                 long M,
                                                 long N,
                                                 long minScore,
                                                 SimKernelContext &context,
                                                 uint64_t &scanTaskCount,
                                                 uint64_t &scanLaunchCount)
{
  context.runningMin = 0;
  context.candidateCount = 0;
  clearSimCandidateStartIndex(context.candidateStartIndex);
  context.candidateMinHeap.clear();
  scanTaskCount = 0;
  scanLaunchCount = 0;

  if(!sim_scan_cuda_is_built() ||
     M <= 0 ||
     N <= 0 ||
     M > 8192 ||
     N > 8192 ||
     minScore > static_cast<long>(0x7fffffff))
  {
    return false;
  }

  int scoreMatrixInt[128][128];
  fillSimScoreMatrixInt(context.scoreMatrix,scoreMatrixInt);

  vector<uint64_t> blockedDenseWords;
  const SimBlockedWordsView blockedView = makeSimBlockedWordsView(context.workspace,1,M,1,N,blockedDenseWords);

  SimScanCudaBatchResult cudaBatchResult;
  string cudaError;
  const int device = simCudaDeviceRuntime();
  vector<SimScanCudaRequest> cudaRequests(1);
  cudaRequests[0].kind = SIM_SCAN_CUDA_REQUEST_REGION;
  cudaRequests[0].A = A;
  cudaRequests[0].B = B;
  cudaRequests[0].queryLength = static_cast<int>(M);
  cudaRequests[0].targetLength = static_cast<int>(N);
  cudaRequests[0].rowStart = 1;
  cudaRequests[0].rowEnd = static_cast<int>(M);
  cudaRequests[0].colStart = 1;
  cudaRequests[0].colEnd = static_cast<int>(N);
  cudaRequests[0].gapOpen = static_cast<int>(context.gapOpen);
  cudaRequests[0].gapExtend = static_cast<int>(context.gapExtend);
  cudaRequests[0].scoreMatrix = scoreMatrixInt;
  cudaRequests[0].eventScoreFloor = static_cast<int>(minScore);
  cudaRequests[0].blockedWords = blockedView.words;
  cudaRequests[0].blockedWordStart = blockedView.wordStart;
  cudaRequests[0].blockedWordCount = blockedView.wordCount;
  cudaRequests[0].blockedWordStride = blockedView.wordStride;
  cudaRequests[0].reduceCandidates = simRegionCudaCandidateReduceEnabledRuntime();
  cudaRequests[0].seedCandidates = NULL;
  cudaRequests[0].seedCandidateCount = 0;
  cudaRequests[0].seedRunningMin = 0;

  vector<SimScanCudaRequestResult> cudaResults;
  if(sim_scan_cuda_init(device,&cudaError) &&
     sim_scan_cuda_enumerate_events_row_major_batch(cudaRequests,
                                                   &cudaResults,
                                                   &cudaBatchResult,
                                                   &cudaError) &&
     cudaResults.size() == 1u)
  {
    scanTaskCount = cudaBatchResult.taskCount;
    scanLaunchCount = cudaBatchResult.launchCount;
    if(cudaRequests[0].reduceCandidates)
    {
      applySimCudaReducedCandidates(cudaResults[0].candidateStates,
                                    cudaResults[0].runningMin,
                                    context);
    }
    else
    {
      const vector<SimScanCudaRowEvent> &cudaEvents = cudaResults[0].events;
      const vector<int> &cudaRowOffsets = cudaResults[0].rowOffsets;
      if(simCandidateRunUpdaterEnabledRuntime())
      {
        SimCandidateRunUpdater updater(context);
        for(int endI = 1; endI <= static_cast<int>(M); ++endI)
        {
          const int localRow = endI - 1;
          const int startIndex = cudaRowOffsets[static_cast<size_t>(localRow)];
          const int endIndex = cudaRowOffsets[static_cast<size_t>(localRow + 1)];
          for(int eventIndex = startIndex; eventIndex < endIndex; ++eventIndex)
          {
            const SimScanCudaRowEvent &event = cudaEvents[static_cast<size_t>(eventIndex)];
            const long startI = static_cast<long>(unpackSimCoordI(event.startCoord));
            const long startJ = static_cast<long>(unpackSimCoordJ(event.startCoord));
            updater(SimInitialCellEvent(static_cast<long>(event.score),
                                       startI,
                                       startJ,
                                       static_cast<long>(endI),
                                       static_cast<long>(event.endJ)));
          }
        }
        updater.finish();
      }
      else
      {
        SimCandidateEventUpdater updater(context);
        for(int endI = 1; endI <= static_cast<int>(M); ++endI)
        {
          const int localRow = endI - 1;
          const int startIndex = cudaRowOffsets[static_cast<size_t>(localRow)];
          const int endIndex = cudaRowOffsets[static_cast<size_t>(localRow + 1)];
          for(int eventIndex = startIndex; eventIndex < endIndex; ++eventIndex)
          {
            const SimScanCudaRowEvent &event = cudaEvents[static_cast<size_t>(eventIndex)];
            const long startI = static_cast<long>(unpackSimCoordI(event.startCoord));
            const long startJ = static_cast<long>(unpackSimCoordJ(event.startCoord));
            updater(SimInitialCellEvent(static_cast<long>(event.score),
                                       startI,
                                       startJ,
                                       static_cast<long>(endI),
                                       static_cast<long>(event.endJ)));
          }
        }
        updater.finish();
      }
    }
    return true;
  }

  if(simCudaValidateEnabledRuntime() && !cudaError.empty())
  {
    fprintf(stderr, "SIM CUDA full rescan failed: %s\n", cudaError.c_str());
  }
  return false;
}

inline bool popHighestScoringSimCandidate(SimKernelContext &context,SimCandidate &candidate)
{
  if(context.candidateCount <= 0)
  {
    return false;
  }
  context.gpuFrontierCacheInSync = false;

  long bestIndex = 0;
  for(long i = 1; i < context.candidateCount; ++i)
  {
    if(context.candidates[i].SCORE > context.candidates[bestIndex].SCORE)
    {
      bestIndex = i;
    }
  }

  SimCandidateStartIndex &index = context.candidateStartIndex;
  candidate = context.candidates[bestIndex];
  eraseSimCandidateIndexEntry(index,bestIndex);
  const long lastIndex = --context.candidateCount;
  if(bestIndex != lastIndex)
  {
    context.candidates[bestIndex] = context.candidates[lastIndex];
    context.candidates[context.candidateCount] = candidate;
    remapSimCandidateIndexEntry(index,lastIndex,bestIndex);
  }
  if(index.tombstoneCount > static_cast<size_t>(K))
  {
    rebuildSimCandidateStartIndex(context);
  }
  context.candidateMinHeap.valid = false;
  refreshSimRunningMin(context);
  return true;
}

inline SimLocateResult locateSimUpdateRegionCpuBounded(const char *A,
                                                       const char *B,
                                                       long m1,
                                                       long mm,
                                                       long n1,
                                                       long nn,
                                                       long minRowBound,
                                                       long minColBound,
                                                       SimKernelContext &context)
{
  SimLocateResult result;
  long *CC = context.workspace.CC.data();
  long *DD = context.workspace.DD.data();
  long *RR = context.workspace.RR.data();
  long *SS = context.workspace.SS.data();
  long *EE = context.workspace.EE.data();
  long *FF = context.workspace.FF.data();
  long *HH = context.workspace.HH.data();
  long *WW = context.workspace.WW.data();
  long *II = context.workspace.II.data();
  long *JJ = context.workspace.JJ.data();
  long *XX = context.workspace.XX.data();
  long *YY = context.workspace.YY.data();
  const long Q = context.gapOpen;
  const long R = context.gapExtend;
  const long QR = Q + R;
  const long negQ = -Q;
  const vector<uint64_t> *blockedRows = context.workspace.blocked.data();

  long c;
  long f;
  long d;
  long p;
  long ci, cj;
  long di, dj;
  long fi, fj;
  long pi, pj;
  short cflag, rflag;
  long limit;
  long rl, cl;
  long i, j;
  long *va;
  short flag = 0;
  uint64_t locateCellCount = 0;
  uint64_t baseCellCount = 0;
  bool stopByNoCross = false;
  bool stopByBoundary = false;

  if(minRowBound < 1)
  {
    minRowBound = 1;
  }
  if(minColBound < 1)
  {
    minColBound = 1;
  }
  if(minRowBound > m1)
  {
    minRowBound = m1;
  }
  if(minColBound > n1)
  {
    minColBound = n1;
  }

  for(j = nn; j >= n1; --j)
  {
    CC[j] = 0;
    EE[j] = j;
    DD[j] = negQ;
    FF[j] = j;
    RR[j] = SS[j] = mm + 1;
  }
  for(i = mm; i >= m1; --i)
  {
    locateCellCount += static_cast<uint64_t>(nn - n1 + 1);
    c = p = 0;
    f = negQ;
    ci = fi = i;
    pi = i + 1;
    cj = fj = pj = nn + 1;
    va = context.scoreMatrix[A[i]];
    limit = n1;
    const vector<uint64_t> &blockedRow = blockedRows[static_cast<size_t>(i)];
    const uint64_t *blockedRowData = blockedRow.empty() ? NULL : blockedRow.data();
    for(j = nn; j >= limit; --j)
    {
      f -= R;
      c -= QR;
      orderSimState(f, fi, fj, c, ci, cj);
      c = CC[j] - QR;
      ci = RR[j];
      cj = EE[j];
      d = DD[j] - R;
      di = SS[j];
      dj = FF[j];
      orderSimState(d, di, dj, c, ci, cj);
      c = 0;
      if(blockedRowData == NULL ||
         (blockedRowData[static_cast<size_t>(j) >> 6] &
          (static_cast<uint64_t>(1) << (static_cast<size_t>(j) & 63))) == 0)
      {
        c = p + va[B[j]];
      }
      if(c <= 0)
      {
        c = 0;
        ci = i;
        cj = j;
      }
      else
      {
        ci = pi;
        cj = pj;
      }
      orderSimState(c, ci, cj, d, di, dj);
      orderSimState(c, ci, cj, f, fi, fj);
      p = CC[j];
      CC[j] = c;
      pi = RR[j];
      pj = EE[j];
      RR[j] = ci;
      EE[j] = cj;
      DD[j] = d;
      SS[j] = di;
      FF[j] = dj;
      if(c > context.runningMin)
      {
        flag = 1;
      }
    }
    HH[i] = CC[n1];
    II[i] = RR[n1];
    JJ[i] = EE[n1];
    WW[i] = f;
    XX[i] = fi;
    YY[i] = fj;
  }
  baseCellCount = locateCellCount;

  for(rl = m1, cl = n1; ; )
  {
    for(rflag = cflag = 1; (rflag && m1 > minRowBound) || (cflag && n1 > minColBound); )
    {
      if(rflag && m1 > minRowBound)
      {
        rflag = 0;
        m1--;
        locateCellCount += static_cast<uint64_t>(nn - n1 + 1);
        c = p = 0;
        f = negQ;
        ci = fi = m1;
        pi = m1 + 1;
        cj = fj = pj = nn + 1;
        va = context.scoreMatrix[A[m1]];
        const vector<uint64_t> &blockedRow = blockedRows[static_cast<size_t>(m1)];
        const uint64_t *blockedRowData = blockedRow.empty() ? NULL : blockedRow.data();
        for(j = nn; j >= n1; --j)
        {
          f -= R;
          c -= QR;
          orderSimState(f, fi, fj, c, ci, cj);
          c = CC[j] - QR;
          ci = RR[j];
          cj = EE[j];
          d = DD[j] - R;
          di = SS[j];
          dj = FF[j];
          orderSimState(d, di, dj, c, ci, cj);
          c = 0;
          if(blockedRowData == NULL ||
             (blockedRowData[static_cast<size_t>(j) >> 6] &
              (static_cast<uint64_t>(1) << (static_cast<size_t>(j) & 63))) == 0)
          {
            c = p + va[B[j]];
          }
          if(c <= 0)
          {
            c = 0;
            ci = m1;
            cj = j;
          }
          else
          {
            ci = pi;
            cj = pj;
          }
          orderSimState(c, ci, cj, d, di, dj);
          orderSimState(c, ci, cj, f, fi, fj);
          p = CC[j];
          CC[j] = c;
          pi = RR[j];
          pj = EE[j];
          RR[j] = ci;
          EE[j] = cj;
          DD[j] = d;
          SS[j] = di;
          FF[j] = dj;
          if(c > context.runningMin)
          {
            flag = 1;
          }
          if(!rflag && (ci > rl && cj > cl || di > rl && dj > cl || fi > rl && fj > cl))
          {
            rflag = 1;
          }
        }
        HH[m1] = CC[n1];
        II[m1] = RR[n1];
        JJ[m1] = EE[n1];
        WW[m1] = f;
        XX[m1] = fi;
        YY[m1] = fj;
        if(!cflag && (ci > rl && cj > cl || di > rl && dj > cl || fi > rl && fj > cl))
        {
          cflag = 1;
        }
      }
      if(cflag && n1 > minColBound)
      {
        cflag = 0;
        n1--;
        locateCellCount += static_cast<uint64_t>(mm - m1 + 1);
        c = 0;
        f = negQ;
        cj = fj = n1;
        va = context.scoreMatrix[B[n1]];
        p = 0;
        ci = fi = pi = mm + 1;
        pj = n1 + 1;
        limit = mm;
        const size_t blockedWordIndex = static_cast<size_t>(n1) >> 6;
        const uint64_t blockedMask = static_cast<uint64_t>(1) << (static_cast<size_t>(n1) & 63);
        for(i = limit; i >= m1; --i)
        {
          f -= R;
          c -= QR;
          orderSimState(f, fi, fj, c, ci, cj);
          c = HH[i] - QR;
          ci = II[i];
          cj = JJ[i];
          d = WW[i] - R;
          di = XX[i];
          dj = YY[i];
          orderSimState(d, di, dj, c, ci, cj);
          c = 0;
          const vector<uint64_t> &blockedRow = blockedRows[static_cast<size_t>(i)];
          if(blockedRow.empty() || (blockedRow[blockedWordIndex] & blockedMask) == 0)
          {
            c = p + va[A[i]];
          }
          if(c <= 0)
          {
            c = 0;
            ci = i;
            cj = n1;
          }
          else
          {
            ci = pi;
            cj = pj;
          }
          orderSimState(c, ci, cj, d, di, dj);
          orderSimState(c, ci, cj, f, fi, fj);
          p = HH[i];
          HH[i] = c;
          pi = II[i];
          pj = JJ[i];
          II[i] = ci;
          JJ[i] = cj;
          WW[i] = d;
          XX[i] = di;
          YY[i] = dj;
          if(c > context.runningMin)
          {
            flag = 1;
          }
          if(!cflag && (ci > rl && cj > cl || di > rl && dj > cl || fi > rl && fj > cl))
          {
            cflag = 1;
          }
        }
        CC[n1] = HH[m1];
        RR[n1] = II[m1];
        EE[n1] = JJ[m1];
        DD[n1] = f;
        SS[n1] = fi;
        FF[n1] = fj;
        if(!rflag && (ci > rl && cj > cl || di > rl && dj > cl || fi > rl && fj > cl))
        {
          rflag = 1;
        }
      }
    }
    const bool hitConfiguredBoundary = (m1 == minRowBound && n1 == minColBound);
    const bool hitFullBoundary = (m1 == 1 && n1 == 1);
    bool noCross = false;
    if(!hitConfiguredBoundary && !hitFullBoundary)
    {
      noCross = no_cross(context.candidates,context.candidateCount,m1,mm,n1,nn,&rl,&cl) != 0;
    }
    if(hitConfiguredBoundary || hitFullBoundary || noCross)
    {
      stopByBoundary = hitConfiguredBoundary || hitFullBoundary;
      stopByNoCross = noCross;
      break;
    }
  }

  result.locateCellCount = locateCellCount;
  result.baseCellCount = baseCellCount;
  result.expansionCellCount = locateCellCount - baseCellCount;
  result.stopByNoCross = stopByNoCross;
  result.stopByBoundary = stopByBoundary;
  --m1;
  --n1;
  if(flag)
  {
    result.hasUpdateRegion = true;
    result.rowStart = m1 + 1;
    result.rowEnd = mm;
    result.colStart = n1 + 1;
    result.colEnd = nn;
  }
  return result;
}

inline SimLocateResult locateSimUpdateRegionCpu(const char *A,
                                                const char *B,
                                                long m1,
                                                long mm,
                                                long n1,
                                                long nn,
                                                SimKernelContext &context)
{
  return locateSimUpdateRegionCpuBounded(A,B,m1,mm,n1,nn,1,1,context);
}

inline SimLocateResult locateSimUpdateRegionFastHost(long rowStart,
                                                     long rowEnd,
                                                     long colStart,
                                                     long colEnd,
                                                     SimKernelContext &context)
{
  SimLocateResult result;
  const long M = static_cast<long>(context.workspace.HH.size()) - 1;
  const long N = static_cast<long>(context.workspace.CC.size()) - 1;
  if(M <= 0 ||
     N <= 0 ||
     rowStart < 1 ||
     colStart < 1 ||
     rowEnd < rowStart ||
     colEnd < colStart)
  {
    return result;
  }

  vector<SimScanCudaCandidateState> candidateStates(static_cast<size_t>(context.candidateCount));
  for(long candidateIndex = 0; candidateIndex < context.candidateCount; ++candidateIndex)
  {
    candidateStates[static_cast<size_t>(candidateIndex)] =
      makeSimScanCudaCandidateState(context.candidates[candidateIndex]);
  }

  return computeSimLocateFastResult(static_cast<int>(M),
                                    static_cast<int>(N),
                                    rowStart,
                                    rowEnd,
                                    colStart,
                                    colEnd,
                                    candidateStates.empty() ? NULL : candidateStates.data(),
                                    static_cast<int>(candidateStates.size()),
                                    static_cast<long>(simLocateCudaFastPadRuntime()));
}

inline bool simLocateResultCovers(const SimLocateResult &outer,
                                  const SimLocateResult &inner)
{
  if(!inner.hasUpdateRegion)
  {
    return true;
  }
  if(!outer.hasUpdateRegion)
  {
    return false;
  }
  return outer.rowStart <= inner.rowStart &&
         outer.rowEnd >= inner.rowEnd &&
         outer.colStart <= inner.colStart &&
         outer.colEnd >= inner.colEnd;
}

struct SimLocateCudaPreparedCommon
{
  SimLocateCudaPreparedCommon():
    eligible(false),
    queryLength(0),
    targetLength(0)
  {
  }

  bool eligible;
  long queryLength;
  long targetLength;
  int scoreMatrixInt[128][128];
  vector<SimScanCudaCandidateState> candidateStates;
};

inline SimLocateCudaPreparedCommon prepareSimLocateCudaPreparedCommon(const char *A,
                                                                     const char *B,
                                                                     SimKernelContext &context)
{
  SimLocateCudaPreparedCommon prepared;
  if(!simLocateCudaEnabledRuntime() ||
     !sim_locate_cuda_is_built() ||
     A == NULL ||
     B == NULL ||
     context.gapOpen < 0 ||
     context.gapExtend < 0)
  {
    return prepared;
  }

  const long M = static_cast<long>(context.workspace.HH.size()) - 1;
  const long N = static_cast<long>(context.workspace.CC.size()) - 1;
  if(M <= 0 ||
     N <= 0 ||
     M > 8192 ||
     N > 8192 ||
     !simBlockedDenseMirrorEnabled(context.workspace) ||
     context.runningMin > static_cast<long>(0x7fffffff))
  {
    return prepared;
  }

  prepared.eligible = true;
  prepared.queryLength = M;
  prepared.targetLength = N;
  fillSimScoreMatrixInt(context.scoreMatrix,prepared.scoreMatrixInt);
  prepared.candidateStates.resize(static_cast<size_t>(context.candidateCount));
  for(long candidateIndex = 0; candidateIndex < context.candidateCount; ++candidateIndex)
  {
    prepared.candidateStates[static_cast<size_t>(candidateIndex)] =
      makeSimScanCudaCandidateState(context.candidates[candidateIndex]);
  }
  return prepared;
}

inline SimLocateCudaRequest makeSimLocateCudaRequestFromPreparedCommon(const char *A,
                                                                      const char *B,
                                                                      long m1,
                                                                      long mm,
                                                                      long n1,
                                                                      long nn,
                                                                      long minRowBound,
                                                                      long minColBound,
                                                                      SimKernelContext &context,
                                                                      SimLocateCudaPreparedCommon &prepared)
{
  SimLocateCudaRequest request;
  request.A = A;
  request.B = B;
  request.queryLength = static_cast<int>(prepared.queryLength);
  request.targetLength = static_cast<int>(prepared.targetLength);
  request.rowStart = static_cast<int>(m1);
  request.rowEnd = static_cast<int>(mm);
  request.colStart = static_cast<int>(n1);
  request.colEnd = static_cast<int>(nn);
  request.runningMin = static_cast<int>(context.runningMin);
  request.gapOpen = static_cast<int>(context.gapOpen);
  request.gapExtend = static_cast<int>(context.gapExtend);
  request.scoreMatrix = prepared.scoreMatrixInt;
  request.blockedWords = context.workspace.blockedDense.empty() ? NULL : context.workspace.blockedDense.data();
  request.blockedWordStride = static_cast<int>(context.workspace.blockedDenseStrideWords);
  request.candidates = prepared.candidateStates.empty() ? NULL : prepared.candidateStates.data();
  request.candidateCount = static_cast<int>(prepared.candidateStates.size());
  request.minRowBound = static_cast<int>(std::max(1L, std::min(minRowBound, m1)));
  request.minColBound = static_cast<int>(std::max(1L, std::min(minColBound, n1)));
  return request;
}

inline SimLocateResult locateSimUpdateRegionExactBounded(const char *A,
                                                         const char *B,
                                                         long m1,
                                                         long mm,
                                                         long n1,
                                                         long nn,
                                                         long minRowBound,
                                                         long minColBound,
                                                         SimKernelContext &context,
                                                         bool recordLocateGpuTelemetry = true)
{
  SimLocateResult result;
  bool haveResult = false;
  if(m1 >= 1 &&
     n1 >= 1 &&
     mm >= m1 &&
     nn >= n1)
  {
    SimLocateCudaPreparedCommon prepared =
      prepareSimLocateCudaPreparedCommon(A,B,context);
    if(prepared.eligible)
    {
      SimLocateCudaRequest request =
        makeSimLocateCudaRequestFromPreparedCommon(A,
                                                   B,
                                                   m1,
                                                   mm,
                                                   n1,
                                                   nn,
                                                   minRowBound,
                                                   minColBound,
                                                   context,
                                                   prepared);

      string cudaError;
      const int device = simCudaDeviceRuntime();
      if(sim_locate_cuda_init(device,&cudaError) &&
         sim_locate_cuda_locate_region(request,&result,&cudaError))
      {
        if(result.usedCuda && recordLocateGpuTelemetry)
        {
          recordSimLocateGpuNanoseconds(simSecondsToNanoseconds(result.gpuSeconds));
        }
        haveResult = true;
        if(simCudaValidateEnabledRuntime())
        {
          const SimLocateResult cpuResult =
            locateSimUpdateRegionCpuBounded(A,
                                            B,
                                            m1,
                                            mm,
                                            n1,
                                            nn,
                                            request.minRowBound,
                                            request.minColBound,
                                            context);
          if(result.hasUpdateRegion != cpuResult.hasUpdateRegion ||
             result.rowStart != cpuResult.rowStart ||
             result.rowEnd != cpuResult.rowEnd ||
             result.colStart != cpuResult.colStart ||
             result.colEnd != cpuResult.colEnd ||
             result.locateCellCount != cpuResult.locateCellCount ||
             result.baseCellCount != cpuResult.baseCellCount ||
             result.expansionCellCount != cpuResult.expansionCellCount ||
             result.stopByNoCross != cpuResult.stopByNoCross ||
             result.stopByBoundary != cpuResult.stopByBoundary)
          {
            fprintf(stderr,
                    "SIM CUDA validate(locate): mismatch cpu(has=%d row=%ld-%ld col=%ld-%ld cells=%llu base=%llu exp=%llu no_cross=%d boundary=%d) cuda(has=%d row=%ld-%ld col=%ld-%ld cells=%llu base=%llu exp=%llu no_cross=%d boundary=%d)\n",
                    cpuResult.hasUpdateRegion ? 1 : 0,
                    cpuResult.rowStart,
                    cpuResult.rowEnd,
                    cpuResult.colStart,
                    cpuResult.colEnd,
                    static_cast<unsigned long long>(cpuResult.locateCellCount),
                    static_cast<unsigned long long>(cpuResult.baseCellCount),
                    static_cast<unsigned long long>(cpuResult.expansionCellCount),
                    cpuResult.stopByNoCross ? 1 : 0,
                    cpuResult.stopByBoundary ? 1 : 0,
                    result.hasUpdateRegion ? 1 : 0,
                    result.rowStart,
                    result.rowEnd,
                    result.colStart,
                    result.colEnd,
                    static_cast<unsigned long long>(result.locateCellCount),
                    static_cast<unsigned long long>(result.baseCellCount),
                    static_cast<unsigned long long>(result.expansionCellCount),
                    result.stopByNoCross ? 1 : 0,
                    result.stopByBoundary ? 1 : 0);
            abort();
          }
        }
      }
      else if(simCudaValidateEnabledRuntime() && !cudaError.empty())
      {
        fprintf(stderr, "SIM CUDA locate failed: %s\n", cudaError.c_str());
      }
    }
  }
  if(!haveResult)
  {
    result = locateSimUpdateRegionCpuBounded(A,B,m1,mm,n1,nn,minRowBound,minColBound,context);
  }
  return result;
}

inline SimLocateResult locateSimUpdateRegionExact(const char *A,
                                                  const char *B,
                                                  long m1,
                                                  long mm,
                                                  long n1,
                                                  long nn,
                                                  SimKernelContext &context)
{
  return locateSimUpdateRegionExactBounded(A,B,m1,mm,n1,nn,1,1,context,true);
}

inline SimLocatePrecheckResult locateSimUpdateRegionExactPrecheck(const char *A,
                                                                  const char *B,
                                                                  long m1,
                                                                  long mm,
                                                                  long n1,
                                                                  long nn,
                                                                  SimKernelContext &context)
{
  SimLocatePrecheckResult precheck;
  const long M = static_cast<long>(context.workspace.HH.size()) - 1;
  const long N = static_cast<long>(context.workspace.CC.size()) - 1;
  vector<SimScanCudaCandidateState> candidateStates(static_cast<size_t>(context.candidateCount));
  for(long candidateIndex = 0; candidateIndex < context.candidateCount; ++candidateIndex)
  {
    candidateStates[static_cast<size_t>(candidateIndex)] =
      makeSimScanCudaCandidateState(context.candidates[candidateIndex]);
  }
  const SimLocateFastBounds bounds =
    computeSimLocateExactPrecheckBounds(static_cast<int>(std::max(0L, M)),
                                        static_cast<int>(std::max(0L, N)),
                                        m1,
                                        mm,
                                        n1,
                                        nn,
                                        candidateStates.empty() ? NULL : candidateStates.data(),
                                        static_cast<int>(candidateStates.size()));
  precheck.attempted = true;
  precheck.minRowBound = bounds.minRowStart;
  precheck.minColBound = bounds.minColStart;
  const SimLocateResult boundedResult =
    locateSimUpdateRegionExactBounded(A,
                                      B,
                                      m1,
                                      mm,
                                      n1,
                                      nn,
                                      bounds.minRowStart,
                                      bounds.minColStart,
                                      context,
                                      false);
  precheck.confirmedNoUpdate = !boundedResult.hasUpdateRegion;
  precheck.needsFullLocate = boundedResult.hasUpdateRegion;
  precheck.baseCellCount = boundedResult.baseCellCount;
  precheck.expansionCellCount = boundedResult.expansionCellCount;
  precheck.scannedCellCount = boundedResult.locateCellCount;
  precheck.stopByNoCross = boundedResult.stopByNoCross;
  precheck.stopByBoundary = boundedResult.stopByBoundary;
  precheck.usedCuda = boundedResult.usedCuda;
  precheck.gpuSeconds = boundedResult.gpuSeconds;
  return precheck;
}

inline SimLocateResult locateSimUpdateRegion(const char *A,
                                             const char *B,
                                             long m1,
                                             long mm,
                                             long n1,
                                             long nn,
                                             SimKernelContext &context)
{
  const bool benchmarkEnabled = simBenchmarkEnabledRuntime();
  const bool wantFastMode = simLocateCudaModeRuntime() == SIM_LOCATE_CUDA_MODE_FAST;
  const std::chrono::steady_clock::time_point locateStart =
    benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
  SimLocateResult result;
  bool usedCuda = false;
  bool usedFastMode = false;
  bool fastFallback = false;
  bool haveResult = false;
  if(!wantFastMode)
  {
    result = locateSimUpdateRegionExact(A,B,m1,mm,n1,nn,context);
    usedCuda = result.usedCuda;
    haveResult = true;
  }
  else if(simLocateCudaEnabledRuntime() &&
     sim_locate_cuda_is_built() &&
     m1 >= 1 &&
     n1 >= 1 &&
     mm >= m1 &&
     nn >= n1 &&
     context.gapOpen >= 0 &&
     context.gapExtend >= 0)
  {
    const long M = static_cast<long>(context.workspace.HH.size()) - 1;
    const long N = static_cast<long>(context.workspace.CC.size()) - 1;
    if(M > 0 &&
       N > 0 &&
       M <= 8192 &&
       N <= 8192 &&
       simBlockedDenseMirrorEnabled(context.workspace) &&
       context.runningMin <= static_cast<long>(0x7fffffff))
    {
      int scoreMatrixInt[128][128];
      fillSimScoreMatrixInt(context.scoreMatrix,scoreMatrixInt);

      vector<SimScanCudaCandidateState> candidateStates(static_cast<size_t>(context.candidateCount));
      for(long candidateIndex = 0; candidateIndex < context.candidateCount; ++candidateIndex)
      {
        candidateStates[static_cast<size_t>(candidateIndex)] =
          makeSimScanCudaCandidateState(context.candidates[candidateIndex]);
      }

      if(wantFastMode)
      {
        const SimLocateResult fastResult =
          computeSimLocateFastResult(static_cast<int>(M),
                                     static_cast<int>(N),
                                     m1,
                                     mm,
                                     n1,
                                     nn,
                                     candidateStates.empty() ? NULL : candidateStates.data(),
                                     static_cast<int>(candidateStates.size()),
                                     static_cast<long>(simLocateCudaFastPadRuntime()));
        if(simLocateCudaFastShadowEnabledRuntime())
        {
          const SimLocateResult cpuResult = locateSimUpdateRegionCpu(A,B,m1,mm,n1,nn,context);
          if(!simLocateResultCovers(fastResult,cpuResult))
          {
            result = cpuResult;
            fastFallback = true;
          }
          else
          {
            result = fastResult;
            usedFastMode = true;
          }
          haveResult = true;
        }
        else
        {
          result = fastResult;
          usedFastMode = true;
          haveResult = true;
        }
      }
    }
  }
  if(!haveResult)
  {
    result = locateSimUpdateRegionCpu(A,B,m1,mm,n1,nn,context);
    usedCuda = false;
    if(wantFastMode)
    {
      fastFallback = true;
    }
  }
  recordSimLocateTotalCells(result.locateCellCount);
  recordSimLocateMode(usedFastMode);
  if(fastFallback)
  {
    recordSimLocateFastFallback();
  }
  recordSimLocateBackend(usedCuda);
  if(benchmarkEnabled)
  {
    recordSimLocateNanoseconds(simElapsedNanoseconds(locateStart));
  }
  return result;
}

inline bool simCandidateContextsEqual(const SimKernelContext &lhs,
                                      const SimKernelContext &rhs,
                                      SimFastFallbackReason *fallbackReason = NULL)
{
  if(lhs.runningMin != rhs.runningMin)
  {
    if(fallbackReason != NULL)
    {
      *fallbackReason = SIM_FAST_FALLBACK_SHADOW_RUNNING_MIN;
    }
    return false;
  }

  if(lhs.candidateCount != rhs.candidateCount)
  {
    if(fallbackReason != NULL)
    {
      *fallbackReason = SIM_FAST_FALLBACK_SHADOW_CANDIDATE_COUNT;
    }
    return false;
  }

  vector<SimCandidate> lhsCandidates(static_cast<size_t>(lhs.candidateCount));
  vector<SimCandidate> rhsCandidates(static_cast<size_t>(rhs.candidateCount));
  for(long index = 0; index < lhs.candidateCount; ++index)
  {
    lhsCandidates[static_cast<size_t>(index)] = lhs.candidates[static_cast<size_t>(index)];
    rhsCandidates[static_cast<size_t>(index)] = rhs.candidates[static_cast<size_t>(index)];
  }
  const auto candidateLess = [](const SimCandidate &lhsCandidate,const SimCandidate &rhsCandidate)
  {
    if(lhsCandidate.SCORE != rhsCandidate.SCORE) return lhsCandidate.SCORE < rhsCandidate.SCORE;
    if(lhsCandidate.STARI != rhsCandidate.STARI) return lhsCandidate.STARI < rhsCandidate.STARI;
    if(lhsCandidate.STARJ != rhsCandidate.STARJ) return lhsCandidate.STARJ < rhsCandidate.STARJ;
    if(lhsCandidate.ENDI != rhsCandidate.ENDI) return lhsCandidate.ENDI < rhsCandidate.ENDI;
    if(lhsCandidate.ENDJ != rhsCandidate.ENDJ) return lhsCandidate.ENDJ < rhsCandidate.ENDJ;
    if(lhsCandidate.TOP != rhsCandidate.TOP) return lhsCandidate.TOP < rhsCandidate.TOP;
    if(lhsCandidate.BOT != rhsCandidate.BOT) return lhsCandidate.BOT < rhsCandidate.BOT;
    if(lhsCandidate.LEFT != rhsCandidate.LEFT) return lhsCandidate.LEFT < rhsCandidate.LEFT;
    return lhsCandidate.RIGHT < rhsCandidate.RIGHT;
  };
  sort(lhsCandidates.begin(),lhsCandidates.end(),candidateLess);
  sort(rhsCandidates.begin(),rhsCandidates.end(),candidateLess);
  for(size_t index = 0; index < lhsCandidates.size(); ++index)
  {
    if(memcmp(&lhsCandidates[index],&rhsCandidates[index],sizeof(SimCandidate)) != 0)
    {
      if(fallbackReason != NULL)
      {
        *fallbackReason = SIM_FAST_FALLBACK_SHADOW_CANDIDATE_VALUE;
      }
      return false;
    }
  }
  return true;
}

inline void applySimUpdateBands(const char *A,
                                const char *B,
                                const vector<SimUpdateBand> &bands,
                                uint64_t totalCellCount,
                                SimKernelContext &context,
                                bool recordTelemetry = true,
                                bool invalidateSafeStore = true)
{
  if(bands.empty())
  {
    return;
  }

  if(invalidateSafeStore &&
     (context.safeCandidateStateStore.valid || context.gpuSafeCandidateStateStore.valid))
  {
    invalidateSimSafeCandidateStateStore(context);
  }
  else if(!invalidateSafeStore)
  {
    context.gpuFrontierCacheInSync = false;
  }

  const long eventScoreFloor = context.runningMin;
  const bool benchmarkEnabled = recordTelemetry && simBenchmarkEnabledRuntime();
  if(recordTelemetry)
  {
    recordSimRegionTotalCells(totalCellCount);
  }

  bool usedCuda = false;
  uint64_t scanTaskCount = 1;
  uint64_t scanLaunchCount = 1;
  const long M = static_cast<long>(context.workspace.HH.size()) - 1;
  const long N = static_cast<long>(context.workspace.CC.size()) - 1;
  bool bandsValid = simInitialScanCudaEnabledRuntime() &&
                    simRegionScanCudaEnabledRuntime() &&
                    sim_scan_cuda_is_built() &&
                    M > 0 &&
                    N > 0 &&
                    M <= 8192 &&
                    N <= 8192 &&
                    eventScoreFloor <= static_cast<long>(0x7fffffff);
  for(size_t bandIndex = 0; bandIndex < bands.size() && bandsValid; ++bandIndex)
  {
    const SimUpdateBand &band = bands[bandIndex];
    bandsValid =
      band.rowStart >= 1 &&
      band.colStart >= 1 &&
      band.rowEnd >= band.rowStart &&
      band.colEnd >= band.colStart &&
      band.rowEnd <= M &&
      band.colEnd <= N &&
      band.rowEnd <= 8192 &&
      band.colEnd <= 8192;
  }

  if(bandsValid)
  {
    int scoreMatrixInt[128][128];
    for(int i = 0; i < 128; ++i)
    {
      for(int j = 0; j < 128; ++j)
      {
        scoreMatrixInt[i][j] = static_cast<int>(context.scoreMatrix[i][j]);
      }
    }

    const bool validate = recordTelemetry && simCudaValidateEnabledRuntime();
    SimKernelContext cpuContext = context;
    SimScanCudaBatchResult cudaBatchResult;
    string cudaError;
    const int device = simCudaDeviceRuntime();
    vector<SimScanCudaRequest> cudaRequests(bands.size());
    vector< vector<uint64_t> > blockedDenseWords(bands.size());
    const bool reduceCandidates =
      bands.size() == 1u &&
      simRegionCudaCandidateReduceEnabledRuntime() &&
      !simCandidateRunUpdaterEnabledRuntime();
    vector<SimScanCudaCandidateState> seedCandidateStates;
    if(reduceCandidates)
    {
      seedCandidateStates.resize(static_cast<size_t>(context.candidateCount));
      for(long candidateIndex = 0; candidateIndex < context.candidateCount; ++candidateIndex)
      {
        seedCandidateStates[static_cast<size_t>(candidateIndex)] =
          makeSimScanCudaCandidateState(context.candidates[candidateIndex]);
      }
    }

    for(size_t bandIndex = 0; bandIndex < bands.size(); ++bandIndex)
    {
      const SimUpdateBand &band = bands[bandIndex];
      const SimBlockedWordsView blockedView =
        makeSimBlockedWordsView(context.workspace,
                                band.rowStart,
                                band.rowEnd,
                                band.colStart,
                                band.colEnd,
                                blockedDenseWords[bandIndex]);
      SimScanCudaRequest &request = cudaRequests[bandIndex];
      request.kind = SIM_SCAN_CUDA_REQUEST_REGION;
      request.A = A;
      request.B = B;
      request.queryLength = static_cast<int>(M);
      request.targetLength = static_cast<int>(N);
      request.rowStart = static_cast<int>(band.rowStart);
      request.rowEnd = static_cast<int>(band.rowEnd);
      request.colStart = static_cast<int>(band.colStart);
      request.colEnd = static_cast<int>(band.colEnd);
      request.gapOpen = static_cast<int>(context.gapOpen);
      request.gapExtend = static_cast<int>(context.gapExtend);
      request.scoreMatrix = scoreMatrixInt;
      request.eventScoreFloor = static_cast<int>(eventScoreFloor);
      request.blockedWords = blockedView.words;
      request.blockedWordStart = blockedView.wordStart;
      request.blockedWordCount = blockedView.wordCount;
      request.blockedWordStride = blockedView.wordStride;
      request.reduceCandidates = reduceCandidates;
      request.seedCandidates = seedCandidateStates.empty() ? NULL : seedCandidateStates.data();
      request.seedCandidateCount = static_cast<int>(seedCandidateStates.size());
      request.seedRunningMin = static_cast<int>(context.runningMin);
    }

    vector<SimScanCudaRequestResult> cudaResults;
    if(sim_scan_cuda_init(device,&cudaError) &&
       sim_scan_cuda_enumerate_events_row_major_batch(cudaRequests,
                                                      &cudaResults,
                                                      &cudaBatchResult,
                                                      &cudaError) &&
       cudaResults.size() == bands.size())
    {
      usedCuda = true;
      scanTaskCount = cudaBatchResult.taskCount;
      scanLaunchCount = cudaBatchResult.launchCount;
      if(benchmarkEnabled)
      {
        recordSimRegionScanGpuNanoseconds(simSecondsToNanoseconds(cudaBatchResult.gpuSeconds));
        recordSimRegionD2HNanoseconds(simSecondsToNanoseconds(cudaBatchResult.d2hSeconds));
      }
      if(reduceCandidates)
      {
        if(recordTelemetry)
        {
          recordSimRegionEvents(cudaResults[0].eventCount);
          recordSimRegionCandidateSummaries(static_cast<uint64_t>(cudaResults[0].candidateStates.size()));
          recordSimRegionEventBytesD2H(0);
          recordSimRegionSummaryBytesD2H(static_cast<uint64_t>(cudaResults[0].candidateStates.size()) *
                                         static_cast<uint64_t>(sizeof(SimScanCudaCandidateState)));
        }
        applySimCudaReducedCandidates(cudaResults[0].candidateStates,
                                      cudaResults[0].runningMin,
                                      context);
      }
      else
      {
        uint64_t totalEventCount = 0;
        uint64_t totalEventBytesD2H = 0;
        if(recordTelemetry)
        {
          for(size_t bandIndex = 0; bandIndex < cudaResults.size(); ++bandIndex)
          {
            totalEventCount += cudaResults[bandIndex].eventCount;
            totalEventBytesD2H += static_cast<uint64_t>(cudaResults[bandIndex].events.size()) *
                                  static_cast<uint64_t>(sizeof(SimScanCudaRowEvent));
          }
          recordSimRegionEvents(totalEventCount);
          recordSimRegionCandidateSummaries(0);
          recordSimRegionEventBytesD2H(totalEventBytesD2H);
          recordSimRegionSummaryBytesD2H(0);
        }

        const std::chrono::steady_clock::time_point cpuMergeStart =
          benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
        if(simCandidateRunUpdaterEnabledRuntime())
        {
          SimCandidateRunUpdater updater(context,&context.runningMin);
          for(size_t bandIndex = 0; bandIndex < bands.size(); ++bandIndex)
          {
            const SimUpdateBand &band = bands[bandIndex];
            const vector<SimScanCudaRowEvent> &cudaEvents = cudaResults[bandIndex].events;
            const vector<int> &cudaRowOffsets = cudaResults[bandIndex].rowOffsets;
            for(int endI = static_cast<int>(band.rowStart); endI <= static_cast<int>(band.rowEnd); ++endI)
            {
              const int localRow = endI - static_cast<int>(band.rowStart);
              const int startIndex = cudaRowOffsets[static_cast<size_t>(localRow)];
              const int endIndex = cudaRowOffsets[static_cast<size_t>(localRow + 1)];
              for(int eventIndex = startIndex; eventIndex < endIndex; ++eventIndex)
              {
                const SimScanCudaRowEvent &event = cudaEvents[static_cast<size_t>(eventIndex)];
                const long startI = static_cast<long>(unpackSimCoordI(event.startCoord));
                const long startJ = static_cast<long>(unpackSimCoordJ(event.startCoord));
                updater(SimInitialCellEvent(static_cast<long>(event.score),
                                           startI,
                                           startJ,
                                           static_cast<long>(endI),
                                           static_cast<long>(event.endJ)));
              }
            }
          }
          updater.finish();
        }
        else
        {
          SimCandidateEventUpdater updater(context,&context.runningMin);
          for(size_t bandIndex = 0; bandIndex < bands.size(); ++bandIndex)
          {
            const SimUpdateBand &band = bands[bandIndex];
            const vector<SimScanCudaRowEvent> &cudaEvents = cudaResults[bandIndex].events;
            const vector<int> &cudaRowOffsets = cudaResults[bandIndex].rowOffsets;
            for(int endI = static_cast<int>(band.rowStart); endI <= static_cast<int>(band.rowEnd); ++endI)
            {
              const int localRow = endI - static_cast<int>(band.rowStart);
              const int startIndex = cudaRowOffsets[static_cast<size_t>(localRow)];
              const int endIndex = cudaRowOffsets[static_cast<size_t>(localRow + 1)];
              for(int eventIndex = startIndex; eventIndex < endIndex; ++eventIndex)
              {
                const SimScanCudaRowEvent &event = cudaEvents[static_cast<size_t>(eventIndex)];
                const long startI = static_cast<long>(unpackSimCoordI(event.startCoord));
                const long startJ = static_cast<long>(unpackSimCoordJ(event.startCoord));
                updater(SimInitialCellEvent(static_cast<long>(event.score),
                                           startI,
                                           startJ,
                                           static_cast<long>(endI),
                                           static_cast<long>(event.endJ)));
              }
            }
          }
          updater.finish();
        }
        if(benchmarkEnabled)
        {
          const uint64_t cpuMergeNanos =
            static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                    std::chrono::steady_clock::now() - cpuMergeStart).count());
          recordSimRegionCpuMergeNanoseconds(cpuMergeNanos);
        }
      }

      if(validate)
      {
        if(simCandidateRunUpdaterEnabledRuntime())
        {
          SimCandidateRunUpdater cpuUpdater(cpuContext,&cpuContext.runningMin);
          for(size_t bandIndex = 0; bandIndex < bands.size(); ++bandIndex)
          {
            const SimUpdateBand &band = bands[bandIndex];
            enumerateSimCandidateRegionRowMajor(A,
                                                B,
                                                band.rowStart,
                                                band.rowEnd,
                                                band.colStart,
                                                band.colEnd,
                                                eventScoreFloor,
                                                cpuContext,
                                                cpuUpdater);
          }
          cpuUpdater.finish();
        }
        else
        {
          SimCandidateEventUpdater cpuUpdater(cpuContext,&cpuContext.runningMin);
          for(size_t bandIndex = 0; bandIndex < bands.size(); ++bandIndex)
          {
            const SimUpdateBand &band = bands[bandIndex];
            enumerateSimCandidateRegionRowMajor(A,
                                                B,
                                                band.rowStart,
                                                band.rowEnd,
                                                band.colStart,
                                                band.colEnd,
                                                eventScoreFloor,
                                                cpuContext,
                                                cpuUpdater);
          }
          cpuUpdater.finish();
        }

        if(!simCandidateContextsEqual(context,cpuContext))
        {
          fprintf(stderr, "SIM CUDA validate(region): candidate state mismatch after banded update\n");
          abort();
        }
      }
    }
    else if(recordTelemetry && simCudaValidateEnabledRuntime() && !cudaError.empty())
    {
      fprintf(stderr, "SIM CUDA region scan failed: %s\n", cudaError.c_str());
    }
  }

  if(!usedCuda)
  {
    const std::chrono::steady_clock::time_point cpuMergeStart =
      benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
    if(simCandidateRunUpdaterEnabledRuntime())
    {
      SimCandidateRunUpdater updater(context,&context.runningMin);
      for(size_t bandIndex = 0; bandIndex < bands.size(); ++bandIndex)
      {
        const SimUpdateBand &band = bands[bandIndex];
        enumerateSimCandidateRegion(A,
                                    B,
                                    band.rowStart,
                                    band.rowEnd,
                                    band.colStart,
                                    band.colEnd,
                                    eventScoreFloor,
                                    context,
                                    updater);
      }
      updater.finish();
    }
    else
    {
      SimCandidateEventUpdater updater(context,&context.runningMin);
      for(size_t bandIndex = 0; bandIndex < bands.size(); ++bandIndex)
      {
        const SimUpdateBand &band = bands[bandIndex];
        enumerateSimCandidateRegion(A,
                                    B,
                                    band.rowStart,
                                    band.rowEnd,
                                    band.colStart,
                                    band.colEnd,
                                    eventScoreFloor,
                                    context,
                                    updater);
      }
      updater.finish();
    }
    if(benchmarkEnabled)
    {
      const uint64_t cpuMergeNanos =
        static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                std::chrono::steady_clock::now() - cpuMergeStart).count());
      recordSimRegionCpuMergeNanoseconds(cpuMergeNanos);
    }
  }

  if(recordTelemetry)
  {
    recordSimRegionScanBackend(usedCuda,scanTaskCount,scanLaunchCount);
  }
}

inline bool applySimSafeAggregatedGpuUpdate(const char *A,
                                            const char *B,
                                            const SimPathWorkset &workset,
                                            const vector<uint64_t> &affectedStartCoords,
                                            SimKernelContext &context,
                                            bool recordTelemetry,
                                            bool recordSafeWorksetCudaTelemetry,
                                            bool recordSafeWindowExecTelemetry,
                                            SimSafeWorksetFallbackReason *fallbackReason)
{
  const bool staleInitialHandoffAtEntry =
    simInvalidateInitialSafeStoreHandoffIfStaleForLocate(context);
  const bool hasSafeStore = context.safeCandidateStateStore.valid || context.gpuSafeCandidateStateStore.valid;
  const bool handoffActiveAtEntry = context.initialSafeStoreHandoffActive;
  const bool handoffHostStoreMissingAtEntry =
    (handoffActiveAtEntry || staleInitialHandoffAtEntry) && !context.safeCandidateStateStore.valid;
  bool handoffFallbackRecorded = false;
  auto recordInitialHandoffFallback = [&]()
  {
    if((handoffActiveAtEntry || staleInitialHandoffAtEntry) && !handoffFallbackRecorded)
    {
      recordSimInitialSafeStoreHandoffHostMergeFallback();
      handoffFallbackRecorded = true;
    }
  };
  if(handoffActiveAtEntry)
  {
    if(context.gpuSafeCandidateStateStore.valid)
    {
      recordSimInitialSafeStoreHandoffAvailableForLocate();
    }
    else
    {
      recordSimInitialSafeStoreHandoffRejectedMissingGpuStore();
      recordInitialHandoffFallback();
    }
  }
  if(!workset.hasWorkset ||
     affectedStartCoords.empty() ||
     !hasSafeStore)
  {
    recordInitialHandoffFallback();
    if(fallbackReason != NULL)
    {
      if(!hasSafeStore)
      {
        *fallbackReason = SIM_SAFE_WORKSET_FALLBACK_INVALID_STORE;
      }
      else if(affectedStartCoords.empty())
      {
        *fallbackReason = SIM_SAFE_WORKSET_FALLBACK_NO_AFFECTED_START;
      }
      else
      {
        *fallbackReason = SIM_SAFE_WORKSET_FALLBACK_NO_WORKSET;
      }
    }
    return false;
  }

  const vector<uint64_t> uniqueAffected = makeSortedUniqueSimStartCoords(affectedStartCoords);
  if(uniqueAffected.empty())
  {
    recordInitialHandoffFallback();
    if(fallbackReason != NULL)
    {
      *fallbackReason = SIM_SAFE_WORKSET_FALLBACK_NO_AFFECTED_START;
    }
    return false;
  }

  const long eventScoreFloor = context.runningMin;
  const bool benchmarkEnabled = recordTelemetry && simBenchmarkEnabledRuntime();
  if(recordTelemetry)
  {
    recordSimRegionTotalCells(workset.cellCount);
  }

  bool bandsValid = simInitialScanCudaEnabledRuntime() &&
                    simRegionScanCudaEnabledRuntime() &&
                    sim_scan_cuda_is_built() &&
                    eventScoreFloor <= static_cast<long>(0x7fffffff);
  const long M = static_cast<long>(context.workspace.HH.size()) - 1;
  const long N = static_cast<long>(context.workspace.CC.size()) - 1;
  if(!(M > 0 && N > 0 && M <= 8192 && N <= 8192))
  {
    bandsValid = false;
  }
  for(size_t bandIndex = 0; bandIndex < workset.bands.size() && bandsValid; ++bandIndex)
  {
    const SimUpdateBand &band = workset.bands[bandIndex];
    bandsValid =
      band.rowStart >= 1 &&
      band.colStart >= 1 &&
      band.rowEnd >= band.rowStart &&
      band.colEnd >= band.colStart &&
      band.rowEnd <= M &&
      band.colEnd <= N &&
      band.rowEnd <= 8192 &&
      band.colEnd <= 8192;
  }
  if(!bandsValid)
  {
    recordInitialHandoffFallback();
    if(fallbackReason != NULL)
    {
      *fallbackReason = SIM_SAFE_WORKSET_FALLBACK_INVALID_BANDS;
    }
    return false;
  }

  int scoreMatrixInt[128][128];
  fillSimScoreMatrixInt(context.scoreMatrix,scoreMatrixInt);

  SimScanCudaBatchResult cudaBatchResult;
  string cudaError;
  const int device = simCudaDeviceRuntime();
  vector<SimScanCudaRequest> cudaRequests(workset.bands.size());
  vector< vector<uint64_t> > blockedDenseWords(workset.bands.size());
  for(size_t bandIndex = 0; bandIndex < workset.bands.size(); ++bandIndex)
  {
    const SimUpdateBand &band = workset.bands[bandIndex];
    const SimBlockedWordsView blockedView =
      makeSimBlockedWordsView(context.workspace,
                              band.rowStart,
                              band.rowEnd,
                              band.colStart,
                              band.colEnd,
                              blockedDenseWords[bandIndex]);
    SimScanCudaRequest &request = cudaRequests[bandIndex];
    request.kind = SIM_SCAN_CUDA_REQUEST_REGION;
    request.A = A;
    request.B = B;
    request.queryLength = static_cast<int>(M);
    request.targetLength = static_cast<int>(N);
    request.rowStart = static_cast<int>(band.rowStart);
    request.rowEnd = static_cast<int>(band.rowEnd);
    request.colStart = static_cast<int>(band.colStart);
    request.colEnd = static_cast<int>(band.colEnd);
    request.gapOpen = static_cast<int>(context.gapOpen);
    request.gapExtend = static_cast<int>(context.gapExtend);
    request.scoreMatrix = scoreMatrixInt;
    request.eventScoreFloor = static_cast<int>(eventScoreFloor);
    request.blockedWords = blockedView.words;
    request.blockedWordStart = blockedView.wordStart;
    request.blockedWordCount = blockedView.wordCount;
    request.blockedWordStride = blockedView.wordStride;
    request.reduceCandidates = false;
    request.reduceAllCandidateStates = true;
    request.filterStartCoords = uniqueAffected.data();
    request.filterStartCoordCount = static_cast<int>(uniqueAffected.size());
    request.seedCandidates = NULL;
    request.seedCandidateCount = 0;
    request.seedRunningMin = static_cast<int>(context.runningMin);
  }

  const bool useResidencyMaintenance =
    (simCudaSafeWorksetDeviceMaintenanceEnabledRuntime() ||
     simCudaRegionResidencyMaintenanceEnabledRuntime()) &&
    context.gpuSafeCandidateStateStore.valid;
  if(useResidencyMaintenance)
  {
    vector<SimScanCudaCandidateState> seedFrontierStates;
    if(!simCanUseGpuFrontierCacheForResidency(context))
    {
      collectSimContextCandidateStates(context,seedFrontierStates);
    }

    SimScanCudaRegionResidencyResult residencyResult;
    if(!(sim_scan_cuda_init(device,&cudaError) &&
         sim_scan_cuda_apply_region_candidate_states_residency(cudaRequests,
                                                               seedFrontierStates,
                                                               static_cast<int>(context.runningMin),
                                                               &context.gpuSafeCandidateStateStore,
                                                               &residencyResult,
                                                               &cudaBatchResult,
                                                               &cudaError,
                                                               true)))
    {
      recordInitialHandoffFallback();
      if(fallbackReason != NULL)
      {
        *fallbackReason = SIM_SAFE_WORKSET_FALLBACK_SCAN_FAILURE;
      }
      if(recordTelemetry && simCudaValidateEnabledRuntime() && !cudaError.empty())
      {
        fprintf(stderr, "SIM CUDA safe update residency failed: %s\n", cudaError.c_str());
      }
      return false;
    }

    if(benchmarkEnabled)
    {
      recordSimRegionScanGpuNanoseconds(simSecondsToNanoseconds(cudaBatchResult.gpuSeconds));
      recordSimRegionD2HNanoseconds(simSecondsToNanoseconds(cudaBatchResult.d2hSeconds));
    }
    if(recordTelemetry)
    {
      recordSimRegionEvents(residencyResult.eventCount);
      recordSimRegionCandidateSummaries(residencyResult.runSummaryCount);
      recordSimRegionEventBytesD2H(0);
      recordSimRegionSummaryBytesD2H(static_cast<uint64_t>(residencyResult.frontierStates.size()) *
                                     static_cast<uint64_t>(sizeof(SimScanCudaCandidateState)));
      if(recordSafeWorksetCudaTelemetry)
      {
        recordSimSafeWorksetCudaBatch(cudaBatchResult.taskCount,cudaBatchResult.launchCount);
        if(cudaBatchResult.usedRegionTrueBatchPath)
        {
          recordSimSafeWorksetCudaTrueBatch(cudaBatchResult.regionTrueBatchRequestCount);
        }
      }
      if(cudaBatchResult.usedRegionPackedAggregationPath)
      {
        recordSimRegionPackedRequests(cudaBatchResult.regionPackedAggregationRequestCount);
      }
      recordSimRegionBucketedTrueBatch(cudaBatchResult);
      recordSimRegionSingleRequestDirectReduce(cudaBatchResult);
      if(recordSafeWindowExecTelemetry)
      {
        recordSimSafeWindowExecGeometry(workset);
      }
    }

    const std::chrono::steady_clock::time_point cpuMergeStart =
      benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
    applySimCudaReducedCandidates(residencyResult.frontierStates,
                                  residencyResult.runningMin,
                                  context);
    markSimGpuFrontierCacheSynchronized(context);
    recordSimFrontierCacheRebuildFromResidency();
    resetSimCandidateStateStore(context.safeCandidateStateStore,false);

    if(benchmarkEnabled)
    {
      const uint64_t cpuMergeNanoseconds = simElapsedNanoseconds(cpuMergeStart);
      recordSimRegionCpuMergeNanoseconds(cpuMergeNanoseconds);
      if(recordTelemetry)
      {
        recordSimSafeWorksetMerge(residencyResult.updatedStateCount,
                                  cpuMergeNanoseconds);
      }
    }
    else if(recordTelemetry)
    {
      recordSimSafeWorksetMerge(residencyResult.updatedStateCount,0);
    }
    if(recordTelemetry)
    {
      recordSimRegionScanBackend(true,cudaBatchResult.taskCount,cudaBatchResult.launchCount);
    }
    if(handoffHostStoreMissingAtEntry)
    {
      recordSimInitialSafeStoreHandoffHostMergeSkipped();
    }
    return true;
  }

  SimScanCudaRegionAggregationResult aggregatedResult;
  if(!(sim_scan_cuda_init(device,&cudaError) &&
       sim_scan_cuda_enumerate_region_candidate_states_aggregated(cudaRequests,
                                                                  &aggregatedResult,
                                                                  &cudaBatchResult,
                                                                  &cudaError)))
  {
    recordInitialHandoffFallback();
    if(fallbackReason != NULL)
    {
      *fallbackReason = SIM_SAFE_WORKSET_FALLBACK_SCAN_FAILURE;
    }
    if(recordTelemetry && simCudaValidateEnabledRuntime() && !cudaError.empty())
    {
      fprintf(stderr, "SIM CUDA safe update scan failed: %s\n", cudaError.c_str());
    }
    return false;
  }

  if(benchmarkEnabled)
  {
    recordSimRegionScanGpuNanoseconds(simSecondsToNanoseconds(cudaBatchResult.gpuSeconds));
    recordSimRegionD2HNanoseconds(simSecondsToNanoseconds(cudaBatchResult.d2hSeconds));
  }
  if(recordTelemetry)
  {
    recordSimRegionEvents(aggregatedResult.eventCount);
    recordSimRegionCandidateSummaries(aggregatedResult.runSummaryCount);
    recordSimRegionEventBytesD2H(0);
    recordSimRegionSummaryBytesD2H(static_cast<uint64_t>(aggregatedResult.candidateStates.size()) *
                                   static_cast<uint64_t>(sizeof(SimScanCudaCandidateState)));
    if(recordSafeWorksetCudaTelemetry)
    {
      recordSimSafeWorksetCudaBatch(cudaBatchResult.taskCount,cudaBatchResult.launchCount);
      if(cudaBatchResult.usedRegionTrueBatchPath)
      {
        recordSimSafeWorksetCudaTrueBatch(cudaBatchResult.regionTrueBatchRequestCount);
      }
    }
    if(cudaBatchResult.usedRegionPackedAggregationPath)
    {
      recordSimRegionPackedRequests(cudaBatchResult.regionPackedAggregationRequestCount);
    }
    recordSimRegionBucketedTrueBatch(cudaBatchResult);
    recordSimRegionSingleRequestDirectReduce(cudaBatchResult);
    if(recordSafeWindowExecTelemetry)
    {
      recordSimSafeWindowExecGeometry(workset);
    }
  }

  const std::chrono::steady_clock::time_point cpuMergeStart =
    benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
  vector<SimScanCudaCandidateState> updatedAffectedStates;
  updatedAffectedStates.swap(aggregatedResult.candidateStates);

  // 受影响的 start 必须按本轮重扫结果整体重建；否则“本轮没有返回 state”的旧候选会以 stale 形式残留。
  eraseSimCandidatesBySortedUniqueStartCoords(uniqueAffected,context);
  if(context.safeCandidateStateStore.valid)
  {
    eraseSimSafeCandidateStateStoreSortedUniqueStartCoords(uniqueAffected,context);
    for(size_t stateIndex = 0; stateIndex < updatedAffectedStates.size(); ++stateIndex)
    {
      upsertSimCandidateStateStoreState(updatedAffectedStates[stateIndex],
                                        context.safeCandidateStateStore);
    }
  }
  mergeSimCudaCandidateStatesIntoContext(updatedAffectedStates,context);
  if(context.safeCandidateStateStore.valid)
  {
    pruneSimSafeCandidateStateStore(context);
  }
  if(context.gpuSafeCandidateStateStore.valid)
  {
    string gpuStoreError;
    if(!updateSimCudaPersistentSafeCandidateStateStore(updatedAffectedStates,
                                                       context,
                                                       context.gpuSafeCandidateStateStore,
                                                       &gpuStoreError))
    {
      recordSimFrontierCacheInvalidateStoreUpdate();
      recordSimFrontierCacheInvalidateReleaseOrError();
      releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
      context.initialSafeStoreHandoffActive = false;
      if(recordTelemetry && simCudaValidateEnabledRuntime() && !gpuStoreError.empty())
      {
        fprintf(stderr, "SIM CUDA safe update store update failed: %s\n", gpuStoreError.c_str());
      }
    }
  }

  if(benchmarkEnabled)
  {
    const uint64_t cpuMergeNanoseconds = simElapsedNanoseconds(cpuMergeStart);
    recordSimRegionCpuMergeNanoseconds(cpuMergeNanoseconds);
    if(recordTelemetry)
    {
      recordSimSafeWorksetMerge(static_cast<uint64_t>(updatedAffectedStates.size()),
                                cpuMergeNanoseconds);
    }
  }
  else if(recordTelemetry)
  {
    recordSimSafeWorksetMerge(static_cast<uint64_t>(updatedAffectedStates.size()),0);
  }
  if(recordTelemetry)
  {
    recordSimRegionScanBackend(true,cudaBatchResult.taskCount,cudaBatchResult.launchCount);
  }
  if(handoffHostStoreMissingAtEntry)
  {
    recordSimInitialSafeStoreHandoffHostMergeSkipped();
  }
  return true;
}

inline bool refreshSimSafeCandidateStateStoreForBands(const char *A,
                                                      const char *B,
                                                      const vector<SimUpdateBand> &bands,
                                                      const vector<uint64_t> &trackedStartCoords,
                                                      SimKernelContext &context,
                                                      bool recordTelemetry = true)
{
  const bool hasHostSafeStore = context.safeCandidateStateStore.valid;
  const bool hasGpuSafeStore = context.gpuSafeCandidateStateStore.valid;
  if((!hasHostSafeStore && !hasGpuSafeStore) || bands.empty())
  {
    return false;
  }

  const vector<uint64_t> uniqueTrackedStartCoords =
    makeSortedUniqueSimStartCoords(trackedStartCoords);
  if(recordTelemetry)
  {
    recordSimSafeStoreRefreshAttempt(static_cast<uint64_t>(uniqueTrackedStartCoords.size()));
  }

  if(uniqueTrackedStartCoords.empty())
  {
    if(hasHostSafeStore)
    {
      pruneSimSafeCandidateStateStore(context);
    }
    if(hasGpuSafeStore)
    {
      string gpuStoreError;
      if(!updateSimCudaPersistentSafeCandidateStateStore(vector<SimScanCudaCandidateState>(),
                                                         context,
                                                         context.gpuSafeCandidateStateStore,
                                                         &gpuStoreError))
      {
	        recordSimFrontierCacheInvalidateStoreUpdate();
	        recordSimFrontierCacheInvalidateReleaseOrError();
	        releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
	        context.initialSafeStoreHandoffActive = false;
	        if(recordTelemetry)
        {
          recordSimSafeStoreRefreshFailure();
        }
        if(recordTelemetry && simCudaValidateEnabledRuntime() && !gpuStoreError.empty())
        {
          fprintf(stderr, "SIM CUDA safe-store refresh update failed: %s\n", gpuStoreError.c_str());
        }
        return false;
      }
    }
    if(recordTelemetry)
    {
      recordSimSafeStoreRefreshSuccess(0,0);
    }
    return true;
  }

  const long eventScoreFloor = context.runningMin;
  const bool benchmarkEnabled = recordTelemetry && simBenchmarkEnabledRuntime();
  if(recordTelemetry)
  {
    recordSimRegionTotalCells(simPathWorksetCellCountFromBands(bands));
  }

  bool bandsValid = simInitialScanCudaEnabledRuntime() &&
                    simRegionScanCudaEnabledRuntime() &&
                    sim_scan_cuda_is_built() &&
                    eventScoreFloor <= static_cast<long>(0x7fffffff);
  const long M = static_cast<long>(context.workspace.HH.size()) - 1;
  const long N = static_cast<long>(context.workspace.CC.size()) - 1;
  if(!(M > 0 && N > 0 && M <= 8192 && N <= 8192))
  {
    bandsValid = false;
  }
  for(size_t bandIndex = 0; bandIndex < bands.size() && bandsValid; ++bandIndex)
  {
    const SimUpdateBand &band = bands[bandIndex];
    bandsValid =
      band.rowStart >= 1 &&
      band.colStart >= 1 &&
      band.rowEnd >= band.rowStart &&
      band.colEnd >= band.colStart &&
      band.rowEnd <= M &&
      band.colEnd <= N &&
      band.rowEnd <= 8192 &&
      band.colEnd <= 8192;
  }
  if(!bandsValid)
  {
    if(recordTelemetry)
    {
      recordSimSafeStoreRefreshFailure();
    }
    return false;
  }

  int scoreMatrixInt[128][128];
  fillSimScoreMatrixInt(context.scoreMatrix,scoreMatrixInt);

  SimScanCudaBatchResult cudaBatchResult;
  string cudaError;
  const int device = simCudaDeviceRuntime();
  vector<SimScanCudaRequest> cudaRequests(bands.size());
  vector< vector<uint64_t> > blockedDenseWords(bands.size());
  for(size_t bandIndex = 0; bandIndex < bands.size(); ++bandIndex)
  {
    const SimUpdateBand &band = bands[bandIndex];
    const SimBlockedWordsView blockedView =
      makeSimBlockedWordsView(context.workspace,
                              band.rowStart,
                              band.rowEnd,
                              band.colStart,
                              band.colEnd,
                              blockedDenseWords[bandIndex]);
    SimScanCudaRequest &request = cudaRequests[bandIndex];
    request.kind = SIM_SCAN_CUDA_REQUEST_REGION;
    request.A = A;
    request.B = B;
    request.queryLength = static_cast<int>(M);
    request.targetLength = static_cast<int>(N);
    request.rowStart = static_cast<int>(band.rowStart);
    request.rowEnd = static_cast<int>(band.rowEnd);
    request.colStart = static_cast<int>(band.colStart);
    request.colEnd = static_cast<int>(band.colEnd);
    request.gapOpen = static_cast<int>(context.gapOpen);
    request.gapExtend = static_cast<int>(context.gapExtend);
    request.scoreMatrix = scoreMatrixInt;
    request.eventScoreFloor = static_cast<int>(eventScoreFloor);
    request.blockedWords = blockedView.words;
    request.blockedWordStart = blockedView.wordStart;
    request.blockedWordCount = blockedView.wordCount;
    request.blockedWordStride = blockedView.wordStride;
    request.reduceCandidates = false;
    request.reduceAllCandidateStates = true;
    request.filterStartCoords = uniqueTrackedStartCoords.data();
    request.filterStartCoordCount = static_cast<int>(uniqueTrackedStartCoords.size());
    request.seedCandidates = NULL;
    request.seedCandidateCount = 0;
    request.seedRunningMin = static_cast<int>(context.runningMin);
  }

  const bool useDeviceMaintenance =
    hasGpuSafeStore &&
    (simCudaSafeWorksetDeviceMaintenanceEnabledRuntime() ||
     simCudaRegionResidencyMaintenanceEnabledRuntime());
  if(useDeviceMaintenance)
  {
    vector<SimScanCudaCandidateState> seedFrontierStates;
    if(!simCanUseGpuFrontierCacheForResidency(context))
    {
      collectSimContextCandidateStates(context,seedFrontierStates);
    }

    SimScanCudaRegionResidencyResult residencyResult;
    if(!(sim_scan_cuda_init(device,&cudaError) &&
         sim_scan_cuda_apply_region_candidate_states_residency(cudaRequests,
                                                               seedFrontierStates,
                                                               static_cast<int>(context.runningMin),
                                                               &context.gpuSafeCandidateStateStore,
                                                               &residencyResult,
                                                               &cudaBatchResult,
                                                               &cudaError,
                                                               false)))
	    {
	      releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
	      context.initialSafeStoreHandoffActive = false;
	      recordSimFrontierCacheInvalidateReleaseOrError();
      if(recordTelemetry)
      {
        recordSimSafeStoreRefreshFailure();
      }
      if(recordTelemetry && simCudaValidateEnabledRuntime() && !cudaError.empty())
      {
        fprintf(stderr, "SIM CUDA safe-store refresh residency failed: %s\n", cudaError.c_str());
      }
      return false;
    }

    const uint64_t gpuNanoseconds = simSecondsToNanoseconds(cudaBatchResult.gpuSeconds);
    const uint64_t d2hNanoseconds = simSecondsToNanoseconds(cudaBatchResult.d2hSeconds);
    if(benchmarkEnabled)
    {
      recordSimRegionScanGpuNanoseconds(gpuNanoseconds);
      recordSimRegionD2HNanoseconds(d2hNanoseconds);
    }
    if(recordTelemetry)
    {
      recordSimRegionEvents(residencyResult.eventCount);
      recordSimRegionCandidateSummaries(residencyResult.runSummaryCount);
      recordSimRegionEventBytesD2H(0);
      recordSimRegionSummaryBytesD2H(0);
      if(cudaBatchResult.usedRegionPackedAggregationPath)
      {
        recordSimRegionPackedRequests(cudaBatchResult.regionPackedAggregationRequestCount);
      }
      recordSimRegionBucketedTrueBatch(cudaBatchResult);
      recordSimRegionSingleRequestDirectReduce(cudaBatchResult);
      recordSimRegionScanBackend(true,cudaBatchResult.taskCount,cudaBatchResult.launchCount);
    }
    if(hasHostSafeStore)
    {
      resetSimCandidateStateStore(context.safeCandidateStateStore,false);
    }
    markSimGpuFrontierCacheSynchronized(context);
    recordSimFrontierCacheRebuildFromResidency();
    if(recordTelemetry)
    {
      recordSimSafeStoreRefreshSuccess(gpuNanoseconds,d2hNanoseconds);
    }
    return true;
  }

  SimScanCudaRegionAggregationResult aggregatedResult;

  if(!(sim_scan_cuda_init(device,&cudaError) &&
       sim_scan_cuda_enumerate_region_candidate_states_aggregated(cudaRequests,
                                                                  &aggregatedResult,
                                                                  &cudaBatchResult,
                                                                  &cudaError)))
  {
    if(recordTelemetry)
    {
      recordSimSafeStoreRefreshFailure();
    }
    if(recordTelemetry && simCudaValidateEnabledRuntime() && !cudaError.empty())
    {
      fprintf(stderr, "SIM CUDA safe-store refresh scan failed: %s\n", cudaError.c_str());
    }
    return false;
  }

  const uint64_t gpuNanoseconds = simSecondsToNanoseconds(cudaBatchResult.gpuSeconds);
  const uint64_t d2hNanoseconds = simSecondsToNanoseconds(cudaBatchResult.d2hSeconds);
  if(benchmarkEnabled)
  {
    recordSimRegionScanGpuNanoseconds(gpuNanoseconds);
    recordSimRegionD2HNanoseconds(d2hNanoseconds);
  }
  if(recordTelemetry)
  {
    recordSimRegionEvents(aggregatedResult.eventCount);
    recordSimRegionCandidateSummaries(aggregatedResult.runSummaryCount);
    recordSimRegionEventBytesD2H(0);
    recordSimRegionSummaryBytesD2H(static_cast<uint64_t>(aggregatedResult.candidateStates.size()) *
                                   static_cast<uint64_t>(sizeof(SimScanCudaCandidateState)));
    if(cudaBatchResult.usedRegionPackedAggregationPath)
    {
      recordSimRegionPackedRequests(cudaBatchResult.regionPackedAggregationRequestCount);
    }
    recordSimRegionBucketedTrueBatch(cudaBatchResult);
    recordSimRegionSingleRequestDirectReduce(cudaBatchResult);
    recordSimRegionScanBackend(true,cudaBatchResult.taskCount,cudaBatchResult.launchCount);
  }

  vector<SimScanCudaCandidateState> updatedTrackedStates;
  updatedTrackedStates.swap(aggregatedResult.candidateStates);
  if(hasHostSafeStore)
  {
    eraseSimSafeCandidateStateStoreSortedUniqueStartCoords(uniqueTrackedStartCoords,context);
    for(size_t stateIndex = 0; stateIndex < updatedTrackedStates.size(); ++stateIndex)
    {
      upsertSimCandidateStateStoreState(updatedTrackedStates[stateIndex],
                                        context.safeCandidateStateStore);
    }
    pruneSimSafeCandidateStateStore(context);
  }
  if(hasGpuSafeStore)
  {
    string gpuStoreError;
    if(!updateSimCudaPersistentSafeCandidateStateStore(updatedTrackedStates,
                                                       context,
                                                       context.gpuSafeCandidateStateStore,
                                                       &gpuStoreError))
    {
	      recordSimFrontierCacheInvalidateStoreUpdate();
	      recordSimFrontierCacheInvalidateReleaseOrError();
	      releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
	      context.initialSafeStoreHandoffActive = false;
	      if(recordTelemetry)
      {
        recordSimSafeStoreRefreshFailure();
      }
      if(recordTelemetry && simCudaValidateEnabledRuntime() && !gpuStoreError.empty())
      {
        fprintf(stderr, "SIM CUDA safe-store refresh update failed: %s\n", gpuStoreError.c_str());
      }
      return false;
    }
  }

  if(recordTelemetry)
  {
    recordSimSafeStoreRefreshSuccess(gpuNanoseconds,d2hNanoseconds);
  }
  return true;
}

inline bool applySimSafeWorksetUpdate(const char *A,
                                      const char *B,
                                      const SimPathWorkset &workset,
                                      const vector<uint64_t> &affectedStartCoords,
                                      SimKernelContext &context,
                                      bool recordTelemetry = true,
                                      SimSafeWorksetFallbackReason *fallbackReason = NULL)
{
  return applySimSafeAggregatedGpuUpdate(A,
                                         B,
                                         workset,
                                         affectedStartCoords,
                                         context,
                                         recordTelemetry,
                                         true,
                                         false,
                                         fallbackReason);
}

inline bool applySimUpdateBandsCpuExactOnly(const char *A,
                                            const char *B,
                                            const vector<SimUpdateBand> &bands,
                                            SimKernelContext &context,
                                            bool recordTelemetry)
{
  if(bands.empty())
  {
    return true;
  }

  const long eventScoreFloor = context.runningMin;
  const bool benchmarkEnabled = recordTelemetry && simBenchmarkEnabledRuntime();
  if(recordTelemetry)
  {
    recordSimRegionTotalCells(simPathWorksetCellCountFromBands(bands));
  }

  const std::chrono::steady_clock::time_point cpuMergeStart =
    benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
  if(simCandidateRunUpdaterEnabledRuntime())
  {
    SimCandidateRunUpdater updater(context,&context.runningMin);
    for(size_t bandIndex = 0; bandIndex < bands.size(); ++bandIndex)
    {
      const SimUpdateBand &band = bands[bandIndex];
      enumerateSimCandidateRegion(A,
                                  B,
                                  band.rowStart,
                                  band.rowEnd,
                                  band.colStart,
                                  band.colEnd,
                                  eventScoreFloor,
                                  context,
                                  updater);
    }
    updater.finish();
  }
  else
  {
    SimCandidateEventUpdater updater(context,&context.runningMin);
    for(size_t bandIndex = 0; bandIndex < bands.size(); ++bandIndex)
    {
      const SimUpdateBand &band = bands[bandIndex];
      enumerateSimCandidateRegion(A,
                                  B,
                                  band.rowStart,
                                  band.rowEnd,
                                  band.colStart,
                                  band.colEnd,
                                  eventScoreFloor,
                                  context,
                                  updater);
    }
    updater.finish();
  }

  if(benchmarkEnabled)
  {
    const uint64_t cpuMergeNanos =
      static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
                              std::chrono::steady_clock::now() - cpuMergeStart).count());
    recordSimRegionCpuMergeNanoseconds(cpuMergeNanos);
  }
  if(recordTelemetry)
  {
    recordSimRegionScanBackend(false,1,1);
  }
  return true;
}

inline bool applySimSafeWindowUpdate(const char *A,
                                     const char *B,
                                     const SimPathWorkset &workset,
                                     const vector<uint64_t> &affectedStartCoords,
                                     SimKernelContext &context,
                                     bool recordTelemetry,
                                     SimSafeWorksetFallbackReason *fallbackReason)
{
  if(recordTelemetry && simRegionSchedulerShapeTelemetryRuntime())
  {
    recordSimRegionSchedulerShapeTelemetry(workset,affectedStartCoords,context);
  }
  return applySimSafeAggregatedGpuUpdate(A,
                                         B,
                                         workset,
                                         affectedStartCoords,
                                         context,
                                         recordTelemetry,
                                         false,
	                                         true,
	                                         fallbackReason);
}

inline bool collectSimSafeStoreStatesForShadow(const SimKernelContext &context,
                                               vector<SimScanCudaCandidateState> &outStates,
                                               string *errorOut = NULL)
{
  outStates.clear();
  if(context.safeCandidateStateStore.valid)
  {
    outStates = context.safeCandidateStateStore.states;
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }
  if(!context.gpuSafeCandidateStateStore.valid)
  {
    if(errorOut != NULL)
    {
      errorOut->clear();
    }
    return true;
  }

  const long queryLength = static_cast<long>(context.workspace.HH.size()) - 1;
  const long targetLength = static_cast<long>(context.workspace.CC.size()) - 1;
  if(queryLength <= 0 || targetLength <= 0)
  {
    if(errorOut != NULL)
    {
      *errorOut = "invalid context dimensions for safe-window shadow safe-store export";
    }
    return false;
  }
  vector<SimUpdateBand> fullBands(1);
  fullBands[0].rowStart = 1;
  fullBands[0].rowEnd = queryLength;
  fullBands[0].colStart = 1;
  fullBands[0].colEnd = targetLength;
  return collectSimCudaPersistentSafeCandidateStatesIntersectingBands(queryLength,
                                                                      targetLength,
                                                                      context.gpuSafeCandidateStateStore,
                                                                      fullBands,
                                                                      outStates,
                                                                      errorOut);
}

inline void installSimSafeStoreStatesForShadow(const vector<SimScanCudaCandidateState> &states,
                                               bool valid,
                                               SimKernelContext &context)
{
  resetSimCandidateStateStore(context.safeCandidateStateStore,valid);
  if(valid)
  {
    context.safeCandidateStateStore.states = states;
    rebuildSimCandidateStateStoreIndex(context.safeCandidateStateStore);
  }
}

inline bool simSafeWindowShadowContextsEqual(const SimKernelContext &lhs,
                                             const SimKernelContext &rhs,
                                             string *errorOut = NULL)
{
  if(!simCandidateContextsEqual(lhs,rhs))
  {
    if(errorOut != NULL)
    {
      *errorOut = "candidate frontier mismatch";
    }
    return false;
  }

  vector<SimScanCudaCandidateState> lhsSafeStoreStates;
  vector<SimScanCudaCandidateState> rhsSafeStoreStates;
  string lhsError;
  string rhsError;
  if(!collectSimSafeStoreStatesForShadow(lhs,lhsSafeStoreStates,&lhsError) ||
     !collectSimSafeStoreStatesForShadow(rhs,rhsSafeStoreStates,&rhsError))
  {
    if(errorOut != NULL)
    {
      *errorOut = !lhsError.empty() ? lhsError : rhsError;
    }
    return false;
  }
  if(!simCudaCandidateStateVectorsEqualAsSet(lhsSafeStoreStates,rhsSafeStoreStates))
  {
    if(errorOut != NULL)
    {
      *errorOut = "safe-store mismatch";
    }
    return false;
  }
  if(errorOut != NULL)
  {
    errorOut->clear();
  }
  return true;
}

inline bool runSimSafeWindowFineShadow(const char *A,
                                       const char *B,
                                       const SimSafeWindowExecutePlan &safeWindowPlan,
                                       const vector<uint64_t> &affectedStartCoords,
                                       const SimKernelContext &context,
                                       bool force)
{
  if((!force && !simSafeWindowFineShadowEnabledRuntime()) ||
     !safeWindowPlan.rawWorkset.hasWorkset ||
     !safeWindowPlan.execWorkset.hasWorkset ||
     affectedStartCoords.empty())
  {
    return true;
  }

  vector<SimScanCudaCandidateState> safeStoreStates;
  string shadowError;
  const bool haveSafeStore =
    context.safeCandidateStateStore.valid || context.gpuSafeCandidateStateStore.valid;
  if(haveSafeStore &&
     !collectSimSafeStoreStatesForShadow(context,safeStoreStates,&shadowError))
  {
    recordSimSafeWindowFineShadow(true);
    if(simCudaValidateEnabledRuntime())
    {
      fprintf(stderr,
              "SIM CUDA safe-window fine shadow mismatch: %s\n",
              shadowError.empty() ? "safe-store export failed" : shadowError.c_str());
    }
    return false;
  }

  SimKernelContext coarsenedContext = context;
  SimKernelContext fineContext = context;
  installSimSafeStoreStatesForShadow(safeStoreStates,haveSafeStore,coarsenedContext);
  installSimSafeStoreStatesForShadow(safeStoreStates,haveSafeStore,fineContext);

  SimSafeWorksetFallbackReason coarsenedReason = SIM_SAFE_WORKSET_FALLBACK_NO_WORKSET;
  SimSafeWorksetFallbackReason fineReason = SIM_SAFE_WORKSET_FALLBACK_NO_WORKSET;
  const bool coarsenedApplied =
    applySimSafeWindowUpdate(A,
                             B,
                             safeWindowPlan.execWorkset,
                             affectedStartCoords,
                             coarsenedContext,
                             false,
                             &coarsenedReason);
  const bool fineApplied =
    applySimSafeWindowUpdate(A,
                             B,
                             safeWindowPlan.rawWorkset,
                             affectedStartCoords,
                             fineContext,
                             false,
                             &fineReason);
  bool mismatch = coarsenedApplied != fineApplied;
  if(!mismatch && coarsenedApplied && fineApplied)
  {
    mismatch = !simSafeWindowShadowContextsEqual(coarsenedContext,
                                                 fineContext,
                                                 &shadowError);
  }
  recordSimSafeWindowFineShadow(mismatch);
  if(mismatch && simCudaValidateEnabledRuntime())
  {
    fprintf(stderr,
            "SIM CUDA safe-window fine shadow mismatch: coarsened_applied=%d fine_applied=%d detail=%s\n",
            coarsenedApplied ? 1 : 0,
            fineApplied ? 1 : 0,
            shadowError.empty() ? "context mismatch" : shadowError.c_str());
  }
  return !mismatch;
}

inline void applySimLocatedUpdateRegion(const char *A,
                                        const char *B,
                                        const SimLocateResult &locateResult,
                                        SimKernelContext &context,
                                        bool invalidateSafeStore = true)
{
  if(!locateResult.hasUpdateRegion)
  {
    return;
  }

  const long rowStart = locateResult.rowStart;
  const long rowEnd = locateResult.rowEnd;
  const long colStart = locateResult.colStart;
  const long colEnd = locateResult.colEnd;
  vector<SimUpdateBand> bands(1);
  bands[0].rowStart = rowStart;
  bands[0].rowEnd = rowEnd;
  bands[0].colStart = colStart;
  bands[0].colEnd = colEnd;
  applySimUpdateBands(A,
                      B,
                      bands,
                      static_cast<uint64_t>(rowEnd - rowStart + 1) *
                      static_cast<uint64_t>(colEnd - colStart + 1),
                      context,
                      true,
                      invalidateSafeStore);
}

inline bool applySimLocatedUpdateRegionWithSafeStoreRefresh(const char *A,
                                                            const char *B,
                                                            const SimLocateResult &locateResult,
                                                            SimKernelContext &context)
{
  simInvalidateInitialSafeStoreHandoffIfStaleForLocate(context);
  if(!locateResult.hasUpdateRegion)
  {
    return context.safeCandidateStateStore.valid || context.gpuSafeCandidateStateStore.valid;
  }

  const bool hadHostSafeStore = context.safeCandidateStateStore.valid;
  const bool hadGpuSafeStore = context.gpuSafeCandidateStateStore.valid;
  const bool hadAnySafeStore = hadHostSafeStore || hadGpuSafeStore;
  if(!hadAnySafeStore)
  {
    applySimLocatedUpdateRegion(A,B,locateResult,context);
    return false;
  }

  vector<SimUpdateBand> bands(1);
  bands[0].rowStart = locateResult.rowStart;
  bands[0].rowEnd = locateResult.rowEnd;
  bands[0].colStart = locateResult.colStart;
  bands[0].colEnd = locateResult.colEnd;
  vector<uint64_t> trackedStartCoords;
  if(hadHostSafeStore)
  {
    collectSimSafeCandidateStateStoreIntersectingStartCoords(context.safeCandidateStateStore,
                                                             bands,
                                                             trackedStartCoords);
  }
  else
  {
    const long queryLength = static_cast<long>(context.workspace.HH.size()) - 1;
    const long targetLength = static_cast<long>(context.workspace.CC.size()) - 1;
    string gpuStoreError;
    if(!collectSimCudaPersistentSafeCandidateStartCoordsIntersectingBands(queryLength,
                                                                          targetLength,
                                                                          context.gpuSafeCandidateStateStore,
                                                                          bands,
                                                                          trackedStartCoords,
                                                                          &gpuStoreError))
    {
	      recordSimFrontierCacheInvalidateReleaseOrError();
	      releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
	      context.initialSafeStoreHandoffActive = false;
	      if(simCudaValidateEnabledRuntime() && !gpuStoreError.empty())
      {
        fprintf(stderr,"SIM CUDA safe-store band export failed: %s\n",gpuStoreError.c_str());
      }
      applySimLocatedUpdateRegion(A,B,locateResult,context);
      return false;
    }
  }

  applySimLocatedUpdateRegion(A,B,locateResult,context,false);
  if(refreshSimSafeCandidateStateStoreForBands(A,
                                               B,
                                               bands,
                                               trackedStartCoords,
                                               context,
                                               true))
  {
    return true;
  }

  if(hadAnySafeStore)
  {
    invalidateSimSafeCandidateStateStore(context);
    recordSimSafeStoreInvalidatedAfterExactFallback();
  }
  return false;
}

inline void applySimPathWorkset(const char *A,
                                const char *B,
                                const SimPathWorkset &workset,
                                SimKernelContext &context,
                                bool recordTelemetry = true)
{
  if(!workset.hasWorkset)
  {
    return;
  }
  applySimUpdateBands(A,B,workset.bands,workset.cellCount,context,recordTelemetry);
}

inline void updateSimCandidatesAfterTraceback(const char *A,const char *B,long m1,long mm,long n1,long nn,SimKernelContext &context)
{
  const SimLocateResult locateResult = locateSimUpdateRegion(A,B,m1,mm,n1,nn,context);
  applySimLocatedUpdateRegion(A,B,locateResult,context);
}

inline void updateSimCandidatesAfterTraceback(const char *A,
                                              const char *B,
                                              long stari,
                                              long endi,
                                              long starj,
                                              long endj,
                                              long m1,
                                              long mm,
                                              long n1,
                                              long nn,
                                              SimKernelContext &context)
{
  const SimLocateCudaMode locateMode =
    simLocateCudaEnabledRuntime() ? simLocateCudaModeRuntime() : SIM_LOCATE_CUDA_MODE_EXACT;
  const bool wantFastMode = locateMode == SIM_LOCATE_CUDA_MODE_FAST;
  const bool wantSafeWorksetMode = locateMode == SIM_LOCATE_CUDA_MODE_SAFE_WORKSET;
  if(!wantFastMode && !wantSafeWorksetMode)
  {
    updateSimCandidatesAfterTraceback(A,B,m1,mm,n1,nn,context);
    return;
  }

  const bool benchmarkEnabled = simBenchmarkEnabledRuntime();
  const std::chrono::steady_clock::time_point locateStart =
    benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
  bool fastFallback = false;
  uint64_t locateCellCount = 0;
  const long queryLength = static_cast<long>(context.workspace.HH.size()) - 1;
  const long targetLength = static_cast<long>(context.workspace.CC.size()) - 1;
  const long tracebackRows = endi - stari + 1;
  const long tracebackCols = endj - starj + 1;
  const SimTracebackPathSummary pathSummary =
    summarizeSimTracebackPath(stari,
                              starj,
                              tracebackRows,
                              tracebackCols,
                              context.tracebackScratch.data());
  if(wantSafeWorksetMode)
  {
    uint64_t locateCellCount = 0;
    const std::chrono::steady_clock::time_point safeWorksetBuildStart =
      benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
	    vector<uint64_t> affectedStartCoords;
	    SimPathWorkset safeWorkset;
	    SimSafeWindowExecutePlan safeWindowPlan;
	    bool useSafeWindowPath = false;
	    bool safeWindowAttempted = false;
	    bool safeWindowPlanUsable = false;
		    string safeWorksetBuildError;
		    const bool hasSafeStore = context.safeCandidateStateStore.valid || context.gpuSafeCandidateStateStore.valid;
		    const bool compareSafeWindowWithBuilder = simSafeWindowCompareBuilderRuntime();
		    const SimSafeWindowExecGeometry safeWindowExecGeometry = simSafeWindowExecGeometryRuntime();
		    bool builtSafeWorkset = true;
		    bool usedSafeWorksetBuilderPath = false;
	    if(context.gpuSafeCandidateStateStore.valid && simSafeWindowCudaEnabledRuntime())
	    {
      safeWindowAttempted = true;
      recordSimSafeWindowAttempt();
      int summaryRowStart = 0;
      vector<int> summaryRowMinCols;
      vector<int> summaryRowMaxCols;
      const bool summaryConvertible =
        convertSimTracebackPathSummaryToCudaSafeWindowRanges(queryLength,
                                                             targetLength,
                                                             pathSummary,
                                                             summaryRowStart,
                                                             summaryRowMinCols,
                                                             summaryRowMaxCols,
                                                             &safeWorksetBuildError);
      if(!summaryConvertible)
      {
        recordSimSafeWindowSkippedUnconvertible();
        safeWorksetBuildError.clear();
      }
	      else if(buildSimSafeWindowExecutePlanFromCudaCandidateStateStore(queryLength,
	                                                                       targetLength,
	                                                                       pathSummary,
	                                                                       context.gpuSafeCandidateStateStore,
	                                                                       safeWindowPlan,
                                                                       &safeWorksetBuildError))
      {
        recordSimSafeWindowExecution(safeWindowPlan.windowCount,
                                     safeWindowPlan.affectedStartCount,
                                     safeWindowPlan.coordBytesD2H,
                                     safeWindowPlan.gpuNanoseconds,
                                     safeWindowPlan.d2hNanoseconds);
        if(simSafeWindowGeometryTelemetryRuntime())
        {
          recordSimSafeWindowGeometryTelemetry(safeWindowPlan);
        }
        if(safeWindowPlan.overflowFallback)
        {
          recordSimSafeWindowFallbackReason(SIM_SAFE_WINDOW_FALLBACK_OVERFLOW);
          recordSimSafeWindowPlanFallback();
        }
        else if(safeWindowPlan.emptyPlan)
        {
          recordSimSafeWindowFallbackReason(SIM_SAFE_WINDOW_FALLBACK_EMPTY_SELECTION);
          recordSimSafeWindowPlanFallback();
        }
	        else
	        {
	          const SimPathWorkset &safeWindowExecWorkset =
	            selectSimSafeWindowExecutePlanWorkset(safeWindowPlan,safeWindowExecGeometry);
	          safeWindowPlanUsable =
	            safeWindowExecWorkset.hasWorkset &&
	            safeWindowPlan.affectedStartCount > 0;
	          if(safeWindowPlanUsable)
	          {
	            recordSimSafeWindowPlan(safeWindowExecWorkset,
	                                    safeWindowPlan.gpuNanoseconds,
	                                    safeWindowPlan.d2hNanoseconds);
	          }
        }
        safeWorksetBuildError.clear();
      }
	      else
	      {
	        recordSimSafeWindowFallbackReason(SIM_SAFE_WINDOW_FALLBACK_SELECTOR_ERROR);
	        recordSimSafeWindowPlanFallback();
	      }
	    }
	    if(context.gpuSafeCandidateStateStore.valid &&
	       safeWindowPlanUsable &&
	       !shouldBuildSimSafeWorksetBuilderAfterSafeWindow(safeWindowPlanUsable,
	                                                       compareSafeWindowWithBuilder))
	    {
	      useSafeWindowPath = true;
	      recordSimSafeWindowSelectedWorkset();
	    }
	    if(context.gpuSafeCandidateStateStore.valid && !useSafeWindowPath)
	    {
	      usedSafeWorksetBuilderPath = true;
	      if(safeWindowAttempted)
	      {
	        recordSimSafeWorksetBuilderCallAfterSafeWindow();
	      }
      builtSafeWorkset =
        buildSimSafeWorksetFromCudaCandidateStateStore(queryLength,
                                                       targetLength,
                                                       pathSummary,
                                                       context.gpuSafeCandidateStateStore,
                                                       safeWorkset,
                                                       affectedStartCoords,
                                                       &safeWorksetBuildError);
      if(!builtSafeWorkset)
      {
	        recordSimFrontierCacheInvalidateReleaseOrError();
	        releaseSimCudaPersistentSafeCandidateStateStore(context.gpuSafeCandidateStateStore);
	        context.initialSafeStoreHandoffActive = false;
	        if(simCudaValidateEnabledRuntime() && !safeWorksetBuildError.empty())
        {
          fprintf(stderr, "SIM CUDA safe_workset build failed: %s\n", safeWorksetBuildError.c_str());
        }
      }
    }
    else
    {
      usedSafeWorksetBuilderPath = true;
      safeWorkset =
        buildSimSafeWorksetFromCandidateStates(queryLength,
                                               targetLength,
                                               pathSummary,
                                               context.safeCandidateStateStore.states,
                                               &affectedStartCoords);
    }
	    SimPathWorkset execSafeWorkset;
	    vector<uint64_t> uniqueAffectedStartCoords;
	    uint64_t safeWorksetAffectedStartCount = 0;
	    bool safeWindowMatchesBuilderAffectedStarts = false;
	    if(usedSafeWorksetBuilderPath)
	    {
	      execSafeWorkset = coarsenSimSafeWorksetForExecution(safeWorkset);
	      uniqueAffectedStartCoords = makeSortedUniqueSimStartCoords(affectedStartCoords);
	      safeWorksetAffectedStartCount =
	        static_cast<uint64_t>(uniqueAffectedStartCoords.size());
	      safeWindowMatchesBuilderAffectedStarts =
	        safeWindowPlanUsable &&
	        safeWindowPlan.uniqueAffectedStartCoords == uniqueAffectedStartCoords;
	      recordSimSafeWorksetGeometry(static_cast<uint64_t>(affectedStartCoords.size()),
	                                   safeWorkset,
	                                   execSafeWorkset);
	      recordSimSafeWorksetBuild(static_cast<uint64_t>(uniqueAffectedStartCoords.size()),
	                                benchmarkEnabled ? simElapsedNanoseconds(safeWorksetBuildStart) : 0);
	    }
	    const bool safeWorksetUsable =
	      usedSafeWorksetBuilderPath &&
	      hasSafeStore &&
	      builtSafeWorkset &&
	      execSafeWorkset.hasWorkset &&
	      safeWorksetAffectedStartCount > 0;
	    if(!useSafeWindowPath && safeWindowPlanUsable && safeWindowMatchesBuilderAffectedStarts)
	    {
	      if(!safeWorksetUsable)
	      {
	        useSafeWindowPath = true;
        recordSimSafeWindowSelectedWorkset();
      }
      else
	      {
	        const SimPathWorkset &safeWindowExecWorkset =
	          selectSimSafeWindowExecutePlanWorkset(safeWindowPlan,safeWindowExecGeometry);
	        const SimSafeWindowPlanComparison safeWindowPlanComparison =
	          compareSimSafeWindowExecution(safeWindowPlan,
	                                        safeWindowExecWorkset,
	                                        execSafeWorkset,
	                                        safeWorksetAffectedStartCount);
        recordSimSafeWindowPlanComparison(safeWindowPlanComparison);
        if(safeWindowPlanComparison == SIM_SAFE_WINDOW_PLAN_COMPARISON_BETTER)
        {
          useSafeWindowPath = true;
          recordSimSafeWindowSelectedWorkset();
        }
      }
    }
	    if(safeWindowAttempted && !useSafeWindowPath && usedSafeWorksetBuilderPath)
	    {
	      recordSimSafeWindowGpuBuilderFallback();
	    }
	    const vector<uint64_t> &selectedAffectedStartCoords =
	      useSafeWindowPath ? safeWindowPlan.uniqueAffectedStartCoords : uniqueAffectedStartCoords;
	    const bool safeApplicable =
	      useSafeWindowPath ? safeWindowPlanUsable : safeWorksetUsable;
	    bool fineSafeWindowMatchesCoarsened = true;
	    if(safeApplicable && useSafeWindowPath)
	    {
	      fineSafeWindowMatchesCoarsened =
	        runSimSafeWindowFineShadow(A,
	                                   B,
	                                   safeWindowPlan,
	                                   selectedAffectedStartCoords,
	                                   context,
	                                   safeWindowExecGeometry == SIM_SAFE_WINDOW_EXEC_GEOMETRY_FINE);
	    }
	    const bool useFineSafeWindowExecution =
	      useSafeWindowPath &&
	      safeWindowExecGeometry == SIM_SAFE_WINDOW_EXEC_GEOMETRY_FINE &&
	      fineSafeWindowMatchesCoarsened;
	    const SimPathWorkset &selectedExecWorkset =
	      useSafeWindowPath ?
	      (useFineSafeWindowExecution ? safeWindowPlan.rawWorkset : safeWindowPlan.execWorkset) :
	      execSafeWorkset;
    bool usedSafeWorkset = false;
    bool locateUsedCuda = false;
    SimSafeWorksetFallbackReason safeFallbackReason = SIM_SAFE_WORKSET_FALLBACK_NO_WORKSET;
    const SimLocateExactPrecheckMode exactPrecheckMode = simLocateExactPrecheckModeRuntime();
    const auto makeLocateResultFromPrecheck = [](const SimLocatePrecheckResult &precheck) -> SimLocateResult
    {
      SimLocateResult result;
      result.locateCellCount = precheck.scannedCellCount;
      result.baseCellCount = precheck.baseCellCount;
      result.expansionCellCount = precheck.expansionCellCount;
      result.stopByNoCross = precheck.stopByNoCross;
      result.stopByBoundary = precheck.stopByBoundary;
      result.usedCuda = precheck.usedCuda;
      result.gpuSeconds = precheck.gpuSeconds;
      return result;
    };
    const auto recordExactFallbackNoUpdateMetadata = [](const SimLocateResult &locateResult)
    {
      if(locateResult.expansionCellCount == 0)
      {
        recordSimSafeWindowExactFallbackBaseNoUpdate();
      }
      else
      {
        recordSimSafeWindowExactFallbackExpansionNoUpdate();
      }
      if(locateResult.stopByNoCross)
      {
        recordSimSafeWindowExactFallbackStopNoCross();
      }
      if(locateResult.stopByBoundary)
      {
        recordSimSafeWindowExactFallbackStopBoundary();
      }
      recordSimSafeWindowExactFallbackBaseCells(locateResult.baseCellCount);
      recordSimSafeWindowExactFallbackExpansionCells(locateResult.expansionCellCount);
    };
    if(!safeApplicable && (!hasSafeStore || !builtSafeWorkset))
    {
      safeFallbackReason = SIM_SAFE_WORKSET_FALLBACK_INVALID_STORE;
    }
    else if(!safeApplicable && selectedAffectedStartCoords.empty())
    {
      safeFallbackReason = SIM_SAFE_WORKSET_FALLBACK_NO_AFFECTED_START;
    }
	    else if(!safeApplicable && !selectedExecWorkset.hasWorkset)
	    {
	      safeFallbackReason = SIM_SAFE_WORKSET_FALLBACK_NO_WORKSET;
	    }
	    if(simLocateCudaFastShadowEnabledRuntime())
    {
      SimKernelContext exactShadowContext = context;
      const SimLocateResult exactShadowResult =
        locateSimUpdateRegionExact(A,B,m1,mm,n1,nn,exactShadowContext);
      if(exactShadowResult.hasUpdateRegion)
      {
        vector<SimUpdateBand> exactBands(1);
        exactBands[0].rowStart = exactShadowResult.rowStart;
        exactBands[0].rowEnd = exactShadowResult.rowEnd;
        exactBands[0].colStart = exactShadowResult.colStart;
        exactBands[0].colEnd = exactShadowResult.colEnd;
        applySimUpdateBands(A,
                            B,
                            exactBands,
                            static_cast<uint64_t>(exactShadowResult.rowEnd - exactShadowResult.rowStart + 1) *
                            static_cast<uint64_t>(exactShadowResult.colEnd - exactShadowResult.colStart + 1),
                            exactShadowContext,
                            false);
      }

      bool safeMatchesExact = false;
      bool shadowApplied = false;
      if(safeApplicable)
      {
        SimKernelContext safeShadowContext = context;
        SimSafeWorksetFallbackReason shadowApplyReason = safeFallbackReason;
        const bool appliedSafePath =
          useSafeWindowPath ?
          applySimSafeWindowUpdate(A,B,selectedExecWorkset,selectedAffectedStartCoords,safeShadowContext,false,&shadowApplyReason) :
          applySimSafeWorksetUpdate(A,B,selectedExecWorkset,selectedAffectedStartCoords,safeShadowContext,false,&shadowApplyReason);
        if(appliedSafePath)
        {
          shadowApplied = true;
          safeMatchesExact = simCandidateContextsEqual(safeShadowContext,exactShadowContext);
        }
        else
        {
          safeFallbackReason = shadowApplyReason;
        }
      }

      if(safeMatchesExact)
      {
        SimSafeWorksetFallbackReason applyReason = safeFallbackReason;
        usedSafeWorkset =
          useSafeWindowPath ?
          applySimSafeWindowUpdate(A,B,selectedExecWorkset,selectedAffectedStartCoords,context,true,&applyReason) :
          applySimSafeWorksetUpdate(A,B,selectedExecWorkset,selectedAffectedStartCoords,context,true,&applyReason);
        if(!usedSafeWorkset)
        {
          safeFallbackReason = applyReason;
        }
      }
      else if(shadowApplied)
      {
        safeFallbackReason = SIM_SAFE_WORKSET_FALLBACK_SHADOW_MISMATCH;
      }
      if(!usedSafeWorkset)
      {
        locateCellCount = exactShadowResult.locateCellCount;
        const bool hadSafeStoreBeforeExactFallback =
          context.safeCandidateStateStore.valid || context.gpuSafeCandidateStateStore.valid;
        if(safeWindowAttempted)
        {
          recordSimSafeWindowExactFallback();
          if(exactShadowResult.usedCuda && exactShadowResult.gpuSeconds > 0.0)
          {
            recordSimSafeWindowExactFallbackLocateGpuNanoseconds(
              simSecondsToNanoseconds(exactShadowResult.gpuSeconds));
          }
        }
        const bool preservedSafeStore =
          applySimLocatedUpdateRegionWithSafeStoreRefresh(A,B,exactShadowResult,context);
        if(safeWindowAttempted)
        {
          if(!exactShadowResult.hasUpdateRegion)
          {
            recordSimSafeWindowExactFallbackNoUpdateRegion();
            recordExactFallbackNoUpdateMetadata(exactShadowResult);
          }
          else if(preservedSafeStore)
          {
            recordSimSafeWindowExactFallbackRefreshSuccess();
          }
          else
          {
            recordSimSafeWindowExactFallbackRefreshFailure();
          }
        }
        if(safeWindowAttempted && hadSafeStoreBeforeExactFallback && !preservedSafeStore)
        {
          recordSimSafeWindowStoreInvalidation();
        }
        locateUsedCuda = exactShadowResult.usedCuda;
      }
    }
    else
    {
      if(safeApplicable)
      {
        SimSafeWorksetFallbackReason applyReason = safeFallbackReason;
        usedSafeWorkset =
          useSafeWindowPath ?
          applySimSafeWindowUpdate(A,B,selectedExecWorkset,selectedAffectedStartCoords,context,true,&applyReason) :
          applySimSafeWorksetUpdate(A,B,selectedExecWorkset,selectedAffectedStartCoords,context,true,&applyReason);
        if(!usedSafeWorkset)
        {
          safeFallbackReason = applyReason;
        }
      }
      if(!usedSafeWorkset)
      {
        SimLocatePrecheckResult exactPrecheckResult;
        SimLocateResult exactResult;
        bool haveExactPrecheck = false;
        bool haveExactResult = false;
        const bool batchExactPrecheckAndLocate =
          safeWindowAttempted &&
          exactPrecheckMode != SIM_LOCATE_EXACT_PRECHECK_OFF &&
          !simLocateCudaFastShadowEnabledRuntime() &&
          (exactPrecheckMode == SIM_LOCATE_EXACT_PRECHECK_SHADOW ||
           simCudaValidateEnabledRuntime());
        if(batchExactPrecheckAndLocate)
        {
          SimLocateCudaPreparedCommon prepared =
            prepareSimLocateCudaPreparedCommon(A,B,context);
          if(prepared.eligible)
          {
            const SimLocateFastBounds precheckBounds =
              computeSimLocateExactPrecheckBounds(static_cast<int>(std::max(0L, prepared.queryLength)),
                                                  static_cast<int>(std::max(0L, prepared.targetLength)),
                                                  m1,
                                                  mm,
                                                  n1,
                                                  nn,
                                                  prepared.candidateStates.empty() ? NULL : prepared.candidateStates.data(),
                                                  static_cast<int>(prepared.candidateStates.size()));
            vector<SimLocateCudaRequest> locateRequests;
            locateRequests.reserve(2);
	            locateRequests.push_back(makeSimLocateCudaRequestFromPreparedCommon(A,
	                                                                               B,
	                                                                               m1,
                                                                               mm,
                                                                               n1,
                                                                               nn,
                                                                               precheckBounds.minRowStart,
                                                                               precheckBounds.minColStart,
                                                                               context,
                                                                               prepared));
            locateRequests.push_back(makeSimLocateCudaRequestFromPreparedCommon(A,
                                                                               B,
                                                                               m1,
                                                                               mm,
                                                                               n1,
                                                                               nn,
                                                                               1,
                                                                               1,
	                                                                               context,
	                                                                               prepared));
	            vector<SimLocateResult> locateBatchResults;
	            string cudaError;
	            const int device = simCudaDeviceRuntime();
	            if(sim_locate_cuda_init(device,&cudaError) &&
	               sim_locate_cuda_locate_region_batch(locateRequests,
	                                                  &locateBatchResults,
	                                                  NULL,
	                                                  &cudaError) &&
	               locateBatchResults.size() == 2)
            {
              const SimLocateResult &boundedResult = locateBatchResults[0];
              exactPrecheckResult.attempted = true;
              exactPrecheckResult.confirmedNoUpdate = !boundedResult.hasUpdateRegion;
              exactPrecheckResult.needsFullLocate = boundedResult.hasUpdateRegion;
              exactPrecheckResult.minRowBound = precheckBounds.minRowStart;
              exactPrecheckResult.minColBound = precheckBounds.minColStart;
              exactPrecheckResult.baseCellCount = boundedResult.baseCellCount;
              exactPrecheckResult.expansionCellCount = boundedResult.expansionCellCount;
              exactPrecheckResult.scannedCellCount = boundedResult.locateCellCount;
              exactPrecheckResult.stopByNoCross = boundedResult.stopByNoCross;
              exactPrecheckResult.stopByBoundary = boundedResult.stopByBoundary;
              exactPrecheckResult.usedCuda = boundedResult.usedCuda;
              exactPrecheckResult.gpuSeconds = boundedResult.gpuSeconds;
              exactResult = locateBatchResults[1];
              haveExactPrecheck = true;
              haveExactResult = true;
              if(simCudaValidateEnabledRuntime() &&
                 exactPrecheckResult.confirmedNoUpdate &&
                 exactResult.hasUpdateRegion)
              {
                fprintf(stderr,
                        "SIM locate exact precheck mismatch: precheck confirmed no-update but exact locate found row=%ld-%ld col=%ld-%ld\n",
                        exactResult.rowStart,
                        exactResult.rowEnd,
                        exactResult.colStart,
                        exactResult.colEnd);
                abort();
              }
            }
            else if(simCudaValidateEnabledRuntime() && !cudaError.empty())
            {
              fprintf(stderr, "SIM CUDA locate batch failed: %s\n", cudaError.c_str());
            }
          }
        }
        if(!haveExactPrecheck)
        {
          haveExactPrecheck =
            safeWindowAttempted &&
            exactPrecheckMode != SIM_LOCATE_EXACT_PRECHECK_OFF &&
            !simLocateCudaFastShadowEnabledRuntime() &&
            ([&]() -> bool
            {
              SimKernelContext precheckContext = context;
              exactPrecheckResult =
                locateSimUpdateRegionExactPrecheck(A,B,m1,mm,n1,nn,precheckContext);
              return exactPrecheckResult.attempted;
            })();
        }
        if(!haveExactResult &&
           haveExactPrecheck &&
           exactPrecheckMode == SIM_LOCATE_EXACT_PRECHECK_ON &&
           exactPrecheckResult.confirmedNoUpdate &&
           !simCudaValidateEnabledRuntime())
        {
          exactResult = makeLocateResultFromPrecheck(exactPrecheckResult);
          haveExactResult = true;
        }
        if(!haveExactResult)
        {
          exactResult = locateSimUpdateRegionExact(A,B,m1,mm,n1,nn,context);
          haveExactResult = true;
          if(simCudaValidateEnabledRuntime() &&
             haveExactPrecheck &&
             exactPrecheckResult.confirmedNoUpdate &&
             exactResult.hasUpdateRegion)
          {
            fprintf(stderr,
                    "SIM locate exact precheck mismatch: precheck confirmed no-update but exact locate found row=%ld-%ld col=%ld-%ld\n",
                    exactResult.rowStart,
                    exactResult.rowEnd,
                    exactResult.colStart,
                    exactResult.colEnd);
            abort();
          }
        }
        locateCellCount = exactResult.locateCellCount;
        const bool hadSafeStoreBeforeExactFallback =
          context.safeCandidateStateStore.valid || context.gpuSafeCandidateStateStore.valid;
        if(safeWindowAttempted)
        {
          recordSimSafeWindowExactFallback();
          if(exactResult.usedCuda && exactResult.gpuSeconds > 0.0)
          {
            recordSimSafeWindowExactFallbackLocateGpuNanoseconds(
              simSecondsToNanoseconds(exactResult.gpuSeconds));
          }
        }
        const bool preservedSafeStore =
          applySimLocatedUpdateRegionWithSafeStoreRefresh(A,B,exactResult,context);
        if(safeWindowAttempted)
        {
          if(!exactResult.hasUpdateRegion)
          {
            recordSimSafeWindowExactFallbackNoUpdateRegion();
            recordExactFallbackNoUpdateMetadata(exactResult);
          }
          else if(preservedSafeStore)
          {
            recordSimSafeWindowExactFallbackRefreshSuccess();
          }
          else
          {
            recordSimSafeWindowExactFallbackRefreshFailure();
          }
        }
        if(safeWindowAttempted && hadSafeStoreBeforeExactFallback && !preservedSafeStore)
        {
          recordSimSafeWindowStoreInvalidation();
        }
        locateUsedCuda = exactResult.usedCuda;
      }
    }

    if(usedSafeWorkset)
    {
      recordSimSafeWorksetPass();
      if(safeWindowAttempted)
      {
        if(useSafeWindowPath)
        {
          recordSimSafeWindowApplied();
        }
        else
        {
          recordSimSafeWindowGpuBuilderPass();
        }
      }
      locateUsedCuda = true;
    }
    else
    {
      recordSimSafeWorksetFallbackReason(safeFallbackReason);
    }

    recordSimLocateTotalCells(locateCellCount);
    recordSimLocateMode(SIM_LOCATE_CUDA_MODE_SAFE_WORKSET);
    recordSimLocateBackend(locateUsedCuda);
    if(benchmarkEnabled)
    {
      const uint64_t locateNanoseconds = simElapsedNanoseconds(locateStart);
      recordSimSafeWorksetTotalNanoseconds(locateNanoseconds);
      recordSimLocateNanoseconds(locateNanoseconds);
    }
    return;
  }

  const long fastPad = static_cast<long>(simLocateCudaFastPadRuntime());
  const long maxBandHeight = 4;
  const uint64_t alignmentArea =
    static_cast<uint64_t>(std::max(0L, tracebackRows)) *
    static_cast<uint64_t>(std::max(0L, tracebackCols));
  const uint64_t candidateBoxArea =
    static_cast<uint64_t>(std::max(0L, mm - m1 + 1)) *
    static_cast<uint64_t>(std::max(0L, nn - n1 + 1));
  uint64_t maxWorksetCells = candidateBoxArea;
  if(alignmentArea > 0)
  {
    const uint64_t scaledAlignmentArea =
      alignmentArea > std::numeric_limits<uint64_t>::max() / 4 ? std::numeric_limits<uint64_t>::max() :
      alignmentArea * 4;
    if(maxWorksetCells == 0 || scaledAlignmentArea < maxWorksetCells)
    {
      maxWorksetCells = scaledAlignmentArea;
    }
  }
  const SimPathWorkset workset =
    buildSimPathWorkset(queryLength,
                        targetLength,
                        pathSummary,
                        fastPad,
                        maxBandHeight,
                        maxWorksetCells);
  recordSimFastPathSummary(pathSummary);
  recordSimFastWorkset(workset);

  const bool fastApplicable = workset.hasWorkset && !workset.fallbackToRect;
  if(simLocateCudaFastShadowEnabledRuntime())
  {
    SimKernelContext exactShadowContext = context;
    const SimLocateResult exactShadowResult =
      locateSimUpdateRegionCpu(A,B,m1,mm,n1,nn,exactShadowContext);
    if(exactShadowResult.hasUpdateRegion)
    {
      vector<SimUpdateBand> exactBands(1);
      exactBands[0].rowStart = exactShadowResult.rowStart;
      exactBands[0].rowEnd = exactShadowResult.rowEnd;
      exactBands[0].colStart = exactShadowResult.colStart;
      exactBands[0].colEnd = exactShadowResult.colEnd;
      applySimUpdateBands(A,
                          B,
                          exactBands,
                          static_cast<uint64_t>(exactShadowResult.rowEnd - exactShadowResult.rowStart + 1) *
                          static_cast<uint64_t>(exactShadowResult.colEnd - exactShadowResult.colStart + 1),
                          exactShadowContext,
                          false);
    }

    bool fastMatchesExact = false;
    SimFastFallbackReason shadowFallbackReason = SIM_FAST_FALLBACK_SHADOW_CANDIDATE_VALUE;
    if(fastApplicable)
    {
      SimKernelContext fastShadowContext = context;
      applySimPathWorkset(A,B,workset,fastShadowContext,false);
      fastMatchesExact = simCandidateContextsEqual(fastShadowContext,
                                                  exactShadowContext,
                                                  &shadowFallbackReason);
    }

    if(fastMatchesExact)
    {
      applySimPathWorkset(A,B,workset,context,true);
    }
    else
    {
      if(fastApplicable)
      {
        recordSimFastFallbackReason(shadowFallbackReason);
      }
      else if(!workset.hasWorkset)
      {
        recordSimFastFallbackReason(SIM_FAST_FALLBACK_NO_WORKSET);
      }
      else if(workset.fallbackToRect)
      {
        recordSimFastFallbackReason(SIM_FAST_FALLBACK_AREA_CAP);
      }
      locateCellCount = exactShadowResult.locateCellCount;
      applySimLocatedUpdateRegion(A,B,exactShadowResult,context);
      fastFallback = true;
    }
  }
  else if(fastApplicable)
  {
    applySimPathWorkset(A,B,workset,context,true);
  }
  else
  {
    if(!workset.hasWorkset)
    {
      recordSimFastFallbackReason(SIM_FAST_FALLBACK_NO_WORKSET);
    }
    else if(workset.fallbackToRect)
    {
      recordSimFastFallbackReason(SIM_FAST_FALLBACK_AREA_CAP);
    }
    const SimLocateResult exactResult = locateSimUpdateRegionCpu(A,B,m1,mm,n1,nn,context);
    locateCellCount = exactResult.locateCellCount;
    applySimLocatedUpdateRegion(A,B,exactResult,context);
    fastFallback = true;
  }

  recordSimLocateTotalCells(locateCellCount);
  recordSimLocateMode(SIM_LOCATE_CUDA_MODE_FAST);
  if(fastFallback)
  {
    recordSimLocateFastFallback();
  }
  recordSimLocateBackend(false);
  if(benchmarkEnabled)
  {
    recordSimLocateNanoseconds(simElapsedNanoseconds(locateStart));
  }
}

inline bool materializeSimCandidateImpl(const SimRequest &request,
                                        const char *A,
                                        const char *B,
                                        long targetLength,
                                        long score,
                                        long stari,
                                        long starj,
                                        long endi,
                                        long endj,
                                        long rule,
                                        bool recordProposalPostTiming,
                                        bool allowTracebackCuda,
                                        SimKernelContext &context,
                                        vector<struct triplex> &triplex_list)
{
  const bool benchmarkEnabled = simBenchmarkEnabledRuntime();
  const std::chrono::steady_clock::time_point materializeStart =
    benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
  recordSimTracebackCandidate(false);
  long I = stari - 1;
  long J = starj - 1;
  const long rl = endi - stari + 1;
  const long cl = endj - starj + 1;
  recordSimTracebackTotalCells(static_cast<uint64_t>(rl + 1) * static_cast<uint64_t>(cl + 1));
  ensureSimTracebackScratchCapacity(targetLength,rl,context);
  long *sapp = context.tracebackScratch.data();
  long last = 0;

  bool usedTracebackCuda = false;
  if(allowTracebackCuda &&
     simTracebackCudaEnabledRuntime() &&
     sim_traceback_cuda_is_built() &&
     canSimTracebackUseCudaForCandidate(rl,cl,starj,context))
  {
    vector<uint64_t> blockedDenseWords;
    const SimBlockedWordsView blockedView =
      makeSimBlockedWordsView(context.workspace,stari,endi,starj,endj,blockedDenseWords);

    const int matchScore = static_cast<int>(context.scoreMatrix['A']['A']);
    const int mismatchScore = static_cast<int>(context.scoreMatrix['A']['C']);

    vector<unsigned char> opsReversed;
    SimTracebackCudaResult tbResult;
    string cudaError;
    const int device = simCudaDeviceRuntime();
    if(sim_traceback_cuda_init(device, &cudaError) &&
       sim_traceback_cuda_traceback_global_affine(&A[stari] - 1,
                                                  &B[starj] - 1,
                                                  static_cast<int>(rl),
                                                  static_cast<int>(cl),
                                                  matchScore,
                                                  mismatchScore,
                                                  static_cast<int>(context.gapOpen),
                                                  static_cast<int>(context.gapExtend),
                                                  static_cast<int>(starj),
                                                  blockedView.words,
                                                  blockedView.wordStart,
                                                  blockedView.wordCount,
                                                  blockedView.wordStride,
                                                  &opsReversed,
                                                  &tbResult,
                                                  &cudaError))
    {
      if(benchmarkEnabled && tbResult.usedCuda)
      {
        recordSimTracebackDpNanoseconds(simSecondsToNanoseconds(tbResult.gpuSeconds));
      }
      const bool fallbackOnTie = simTracebackCudaFallbackOnTieEnabledRuntime();
      if(tbResult.hadTie)
      {
        simTracebackTieCount().fetch_add(1, std::memory_order_relaxed);
      }
      if((!fallbackOnTie || !tbResult.hadTie) &&
         convertSimTracebackOpsToScratchAndBlock(opsReversed,rl,cl,stari,starj,context))
      {
        usedTracebackCuda = true;
      }
    }
    else if(simCudaValidateEnabledRuntime() && !cudaError.empty())
    {
      fprintf(stderr, "SIM CUDA traceback failed: %s\n", cudaError.c_str());
    }
  }

  if(!usedTracebackCuda)
  {
    const std::chrono::steady_clock::time_point tracebackDpStart =
      benchmarkEnabled ? std::chrono::steady_clock::now() : std::chrono::steady_clock::time_point();
    diff(&A[stari]-1, &B[starj]-1,rl,cl,&I,&J,context.gapOpen,context.gapOpen,context.gapOpen,context.gapExtend,&sapp,&last,
         context.scoreMatrix,context.workspace,context.workspace.CC.data(),context.workspace.DD.data(),
         context.workspace.RR.data(),context.workspace.SS.data());
    if(benchmarkEnabled)
    {
      recordSimTracebackDpNanoseconds(simElapsedNanoseconds(tracebackDpStart));
    }
  }
  recordSimTracebackBackend(usedTracebackCuda);
  return finalizeSimMaterializedCandidate(request,
                                          A,
                                          B,
                                          targetLength,
                                          score,
                                          stari,
                                          starj,
                                          endi,
                                          endj,
                                          rule,
                                          recordProposalPostTiming,
                                          context,
                                          triplex_list,
                                          benchmarkEnabled,
                                          materializeStart);
}

inline bool materializeSimCandidate(const SimRequest &request,
                                    const char *A,
                                    const char *B,
                                    long targetLength,
                                    long score,
                                    long stari,
                                    long starj,
                                    long endi,
                                    long endj,
                                    long rule,
                                    SimKernelContext &context,
                                    vector<struct triplex> &triplex_list)
{
  return materializeSimCandidateImpl(request,
                                     A,
                                     B,
                                     targetLength,
                                     score,
                                     stari,
                                     starj,
                                     endi,
                                     endj,
                                     rule,
                                     false,
                                     true,
                                     context,
                                     triplex_list);
}

inline bool runSimCudaFullExactSolver(const SimRequest &request,
                                      const char *A,
                                      const char *B,
                                      long M,
                                      long N,
                                      long minScore,
                                      float parm_M,
                                      float parm_I,
                                      float parm_O,
                                      float parm_E,
                                      long rule,
                                      vector<struct triplex> &triplex_list)
{
  if(M <= 0 ||
     N <= 0 ||
     !sim_scan_cuda_is_built() ||
     M > 8192 ||
     N > 8192 ||
     minScore > static_cast<long>(0x7fffffff))
  {
    return false;
  }

  SimKernelContext gpuContext(M,N);
  initializeSimKernel(parm_M,parm_I,parm_O,parm_E,gpuContext);

  vector<struct triplex> fullTriplexList;
  fullTriplexList.reserve(K);

  uint64_t totalScanTasks = 0;
  uint64_t totalScanLaunches = 0;
  uint64_t fullRescanCount = 0;
  uint64_t fullIterationCount = 0;
  uint64_t blockedDiagonalCount = 0;

  for(int iteration = 0; iteration < K; ++iteration)
  {
    uint64_t scanTaskCount = 0;
    uint64_t scanLaunchCount = 0;
    if(!enumerateFullRescanSimCandidatesCuda(A,B,M,N,minScore,gpuContext,scanTaskCount,scanLaunchCount))
    {
      return false;
    }

    totalScanTasks += scanTaskCount;
    totalScanLaunches += scanLaunchCount;
    ++fullRescanCount;

    SimCandidate currentCandidate;
    if(!popHighestScoringSimCandidate(gpuContext,currentCandidate))
    {
      break;
    }

    const long score = currentCandidate.SCORE;
    const long stari = currentCandidate.STARI + 1;
    const long starj = currentCandidate.STARJ + 1;
    const long endi = currentCandidate.ENDI;
    const long endj = currentCandidate.ENDJ;
    if(!materializeSimCandidate(request,
                                A,
                                B,
                                N,
                                score,
                                stari,
                                starj,
                                endi,
                                endj,
                                rule,
                                gpuContext,
                                fullTriplexList))
    {
      break;
    }

    blockedDiagonalCount += countSimTracebackDiagonalSteps(gpuContext.tracebackScratch.data(),
                                                           endi - stari + 1,
                                                           endj - starj + 1);
    ++fullIterationCount;
  }

  triplex_list.insert(triplex_list.end(),fullTriplexList.begin(),fullTriplexList.end());
  recordSimSolverBackend(SIM_SOLVER_BACKEND_CUDA_FULL_EXACT);
  recordSimCudaFullExactExecution(fullIterationCount,
                                  fullRescanCount,
                                  blockedDiagonalCount,
                                  totalScanTasks,
                                  totalScanLaunches);
  return true;
}

struct SimPrefilterHit
{
  SimPrefilterHit():
    SCORE(0),
    STARI(0),
    STARJ(0),
    ENDI(0),
    ENDJ(0),
    TOP(0),
    BOT(0),
    LEFT(0),
    RIGHT(0) {}

  long SCORE;
  long STARI;
  long STARJ;
  long ENDI;
  long ENDJ;
  long TOP;
  long BOT;
  long LEFT;
  long RIGHT;
};

inline void SIM_PREFILTER(const string& strA,
                          const string& strB,
                          long min_score,
                          float parm_M,
                          float parm_I,
                          float parm_O,
                          float parm_E,
                          vector<SimPrefilterHit> &hits,
                          int maxHits = K)
{
  hits.clear();
  if(maxHits <= 0)
  {
    return;
  }

  long M, N;
  const char *A, *B;
  string tmpA, tmpB;
  tmpA = ' ' + strA;
  tmpB = ' ' + strB;
  A = tmpA.c_str();
  B = tmpB.c_str();
  M = strA.size();
  N = strB.size();
  if(M <= 0 || N <= 0)
  {
    return;
  }

  SimKernelContext context(M,N);
  initializeSimKernel(parm_M,parm_I,parm_O,parm_E,context);
  enumerateInitialSimCandidates(A,B,M,N,min_score,context);
  const int available = static_cast<int>(context.candidateCount);
  const int wanted = min(maxHits, available);
  if(wanted <= 0)
  {
    return;
  }

  vector<SimCandidate> candidates;
  candidates.reserve(static_cast<size_t>(available));
  for(long i = 0; i < context.candidateCount; ++i)
  {
    candidates.push_back(context.candidates[static_cast<size_t>(i)]);
  }
  sort(candidates.begin(),
       candidates.end(),
       [](const SimCandidate &lhs,const SimCandidate &rhs)
       {
         if(lhs.SCORE != rhs.SCORE) return lhs.SCORE > rhs.SCORE;
         if(lhs.STARI != rhs.STARI) return lhs.STARI < rhs.STARI;
         if(lhs.STARJ != rhs.STARJ) return lhs.STARJ < rhs.STARJ;
         if(lhs.ENDI != rhs.ENDI) return lhs.ENDI < rhs.ENDI;
         return lhs.ENDJ < rhs.ENDJ;
       });

  hits.reserve(static_cast<size_t>(wanted));
  for(int i = 0; i < wanted; ++i)
  {
    const SimCandidate &c = candidates[static_cast<size_t>(i)];
    SimPrefilterHit hit;
    hit.SCORE = c.SCORE;
    hit.STARI = c.STARI;
    hit.STARJ = c.STARJ;
    hit.ENDI = c.ENDI;
    hit.ENDJ = c.ENDJ;
    hit.TOP = c.TOP;
    hit.BOT = c.BOT;
    hit.LEFT = c.LEFT;
    hit.RIGHT = c.RIGHT;
    hits.push_back(hit);
  }
}

void SIM(const string& strA, const string& strB, const string& strSrc,long dnaStartPos, long min_score,float parm_M,float parm_I,float parm_O,float parm_E, vector<struct triplex>& triplex_list, long strand, long Para, long rule,int ntMin,int ntMax,int penaltyT,int penaltyC)
{
	long M, N;
	const char *A, *B;
	string tmpA, tmpB;
  SimRequest request(strSrc,dnaStartPos,min_score,strand,Para,ntMin,ntMax,penaltyT,penaltyC);
	tmpA=' '+strA;
	tmpB=' '+strB;
	A=tmpA.c_str();
	B=tmpB.c_str();
	M=strA.size();
	N=strB.size();
  const bool simFast = simFastEnabledRuntime();
  const bool windowPipelineRequested = !simFast && simCudaWindowPipelineEnabledRuntime();
  if(!windowPipelineRequested &&
     !simFast &&
     simExactCudaFullEnabledRuntime() &&
     runSimCudaFullExactSolver(request,A,B,M,N,min_score,parm_M,parm_I,parm_O,parm_E,rule,triplex_list))
  {
    return;
  }

  recordSimSolverBackend(SIM_SOLVER_BACKEND_CPU);

  SimKernelContext context(M,N);

	  initializeSimKernel(parm_M,parm_I,parm_O,parm_E,context);
	  enumerateInitialSimCandidates(A,B,M,N,min_score,context);
	  runSimCandidateLoop(request,A,B,N,rule,context,triplex_list);
			  if(context.statsEnabled)
			  {
	    const int runUpdaterEnabled = simCandidateRunUpdaterEnabledRuntime() ? 1 : 0;
	    fprintf(stderr,
	            "sim.stats run_updater=%d addnode_calls=%llu events_seen=%llu index_hits=%llu index_misses=%llu full_evictions=%llu min_selection_scans=%llu heap_builds=%llu heap_updates=%llu hash_probes_total=%llu hash_probes_max=%llu run_updater_runs_started=%llu run_updater_flushes=%llu run_updater_total_run_len=%llu run_updater_max_run_len=%llu run_updater_skipped_events=%llu\n",
	            runUpdaterEnabled,
	            static_cast<unsigned long long>(context.stats.addnodeCalls),
	            static_cast<unsigned long long>(context.stats.eventsSeen),
	            static_cast<unsigned long long>(context.stats.indexHits),
	            static_cast<unsigned long long>(context.stats.indexMisses),
	            static_cast<unsigned long long>(context.stats.fullEvictions),
	            static_cast<unsigned long long>(context.stats.minSelectionScans),
	            static_cast<unsigned long long>(context.stats.heapBuilds),
	            static_cast<unsigned long long>(context.stats.heapUpdates),
	            static_cast<unsigned long long>(context.stats.hashProbesTotal),
	            static_cast<unsigned long long>(context.stats.hashProbesMax),
	            static_cast<unsigned long long>(context.stats.runUpdaterRunsStarted),
	            static_cast<unsigned long long>(context.stats.runUpdaterFlushes),
	            static_cast<unsigned long long>(context.stats.runUpdaterTotalRunLen),
	            static_cast<unsigned long long>(context.stats.runUpdaterMaxRunLen),
	            static_cast<unsigned long long>(context.stats.runUpdaterSkippedEvents));
	  }
	}

void cluster_triplex(int dd,int length,vector<struct triplex>& triplex_list,map<size_t,size_t> class1[],map<size_t,size_t> class1a[],map<size_t,size_t> class1b[],int class_level)
{
    int i,j;
    int find=0;
    map<size_t, struct axis> axis_map;
    int max_neartriplexnum=0,max_pos=0;
    int middle=0;
    int count=0;
    for(vector<struct triplex>::iterator it=triplex_list.begin();it!=triplex_list.end();it++)
    {
      if(it->nt>length)
      {
        count++;
        middle=(int)((it->stari+it->endi)/2);
        it->middle=middle;
        it->motif=0;
        axis_map[middle].triplexnum++;

        for (i=-dd;i<=dd;i++)
        {
            if(i>0)
            {
            axis_map[middle+i].neartriplex = axis_map[middle+i].neartriplex + (dd-i);
            }
            else if(i<0)
            {
              axis_map[middle+i].neartriplex=axis_map[middle+i].neartriplex+(dd+i);
            }           
            else
            { 
            }
            if(axis_map[middle].triplexnum>0)
            {
            if (axis_map[middle+i].neartriplex >max_neartriplexnum)
              {
                max_neartriplexnum=axis_map[middle+i].neartriplex;
                max_pos=middle+i;
                find=1;
              }
            }
        }
        it->neartriplex=axis_map[middle].neartriplex;
      }
    }
    int theclass=1;
    while( find )
    {
        for(i=max_pos-dd; i<=max_pos+dd; i++)
        {
            for(vector<struct triplex>::iterator it=triplex_list.begin();it!=triplex_list.end();it++)
            {
              if(it->middle==i && it->motif==0)
                {
                    it->motif = theclass;
                    it->center=max_pos;
                    if (theclass > class_level) 
                    {
                      continue;
                    }
                    if(it->endj>it->starj)
                        for(j=it->starj;j<it->endj;j++)
                        {
                          class1[theclass][j]++;
                          class1a[theclass][j]++;
                        }
                    else
                        for(j=it->endj;j<it->starj;j++)
                        {
                          class1[theclass][j]++;
                          class1b[theclass][j]--;
                        }
                }
            }
            axis_map.erase(i);
        }
        max_neartriplexnum=0;
        find=0;
        for(map<size_t, struct axis>::iterator it=axis_map.begin(); it!=axis_map.end(); it++)
        {
            if(it->second.neartriplex>=max_neartriplexnum&&it->second.triplexnum>0)
            {
                max_neartriplexnum=it->second.neartriplex;
                max_pos=it->first;
                find=1;
            }
        }
        ++theclass;
    }
}

void print_cluster(int c_level,map<size_t,size_t> class1[],int start_genome,string &chro_info,int dna_size,string &rna_name,int distance,int length,string &outFilePath,string &c_tmp_dd,string &c_tmp_length,vector<struct tmp_class> &w_tmp_class)
{
  struct tmp_class a_tmp_class;
  w_tmp_class.clear();
  char c_level_tmp[3];
  sprintf(c_level_tmp,"%d",c_level);
  string c_tmp_level;
  int c_level_loop=0;
  for(c_level_loop=0;c_level_loop<strlen(c_level_tmp);c_level_loop++)
  {
    c_tmp_level+=c_level_tmp[c_level_loop];
  }
  string class_name=outFilePath.substr(0,outFilePath.size()-10)+"-TFOclass"+c_tmp_level+"-"+c_tmp_dd+"-"+c_tmp_length;
	ofstream outfile(class_name.c_str(),ios::trunc);
  int map_tmp0=0,map_tmp1=0,map_tmp2=0,map_tmp3=0,map_count=0,map_count1=0;
  int map_first1=0,map_second1=0;
  int map_first0=0,map_second0=0;
  int if_map1=0,if_map2=0,if_map3=0,if_map4=0;
  int if_map_flag=0;
  outfile<<"browser position "<<chro_info<<":"<<start_genome<<"-"<<start_genome+dna_size<<endl;
  outfile<<"browser hide all"<<endl;
  outfile<<"browser pack refGene encodeRegions"<<endl;
  outfile<<"browser full altGraph"<<endl;
  outfile<<"# 300 base wide bar graph, ausoScale is on by default == graphing"<<endl;
  outfile<<"# limits will dynamically change to always show full range of data"<<endl;
  outfile<<"# in viewing window, priority = 20 position this as the second graph"<<endl;
  outfile<<"# Note, zero-relative, half-open coordinate system in use for bedGraph format"<<endl;
  outfile<<"track type=bedGraph name='"<<rna_name<<" TTS ("<<c_level<<")' description='"<<distance<<"-"<<length<<"' visibility=full color=200,100,0 altColor=0,100,200 priority=20"<<endl;
  if(class1[c_level].empty())
  {
    return;
  }
  map<size_t,size_t>::iterator it=class1[c_level].begin();
  size_t run_start=it->first;
  size_t run_end=it->first;
  size_t run_signal=it->second;
  size_t prev_pos=it->first;
  ++it;
  for(;it!=class1[c_level].end();++it)
  {
    if(it->first==prev_pos+1&&it->second==run_signal)
    {
      run_end=it->first;
      prev_pos=it->first;
      continue;
    }
    a_tmp_class=tmp_class(run_start+start_genome-1,run_end+start_genome,run_signal,0,0);
    w_tmp_class.push_back(a_tmp_class);
    if(it->first>prev_pos+1)
    {
      a_tmp_class=tmp_class(run_end+start_genome,it->first+start_genome-1,0,0,0);
      w_tmp_class.push_back(a_tmp_class);
    }
    run_start=it->first;
    run_end=it->first;
    run_signal=it->second;
    prev_pos=it->first;
  }
  a_tmp_class=tmp_class(run_start+start_genome-1,run_end+start_genome,run_signal,0,0);
  w_tmp_class.push_back(a_tmp_class);
  for(size_t w_class_loop=0;w_class_loop<w_tmp_class.size();w_class_loop++)
  {
    tmp_class btc=w_tmp_class[w_class_loop];
    outfile<<chro_info<<"\t"<<btc.genome_start<<"\t"<<btc.genome_end<<"\t"<<btc.signal_level<<endl;
  }
}

