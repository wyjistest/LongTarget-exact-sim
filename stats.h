#include<stdio.h>
#include<stdlib.h>
#include<math.h>
#include<ctype.h>
#include<emmintrin.h>
#include<string>
#include<string.h>
#include<sys/time.h>
#if defined(__APPLE__)
#include<sys/sysctl.h>
#endif
#include<iostream>
#include<time.h>
#include<vector>
#define BIGNUM 1000000
#define MAXTST 1500
#define MAXLIB 10000
#define EL 125
#define ES 126
#define MIN_RES 1000
#define NA 123
#define MAXSQ 60
#define AA 16807
#define MM 2147483647
#define QQ 127773	
#define RW 2836
#define PI_SQRT6 1.28254983016186409554
#define TINY 1.0e-6
#define MAX_NIT 100
#define MAX_LNCRNA 1000000
using namespace std;
double first_deriv_cen(double lambda, int *sptr, int *n1, int start, int stop, double sumlenL, double cenL, double sumlenH, double cenH);
double second_deriv_cen(double lambda, int *sptr, int *n1, int start, int stop, double sumlenL, double cenL, double sumlenH, double cenH);
double *mle_cen  (int *, int,int *, int, double, double , double );
void st_sort (int *v, int n)
{
  int gap, i, j;
  int tmp;
  double dtmp;
  int w_tmp;
  w_tmp=0;
  for (gap = 1; gap < n/3; gap = 3*gap +1) ;
  for (; gap > 0; gap = (gap-1)/3) 
  {
    for (i = gap; i < n; i++) 
    {
      for (j = i - gap; j >= 0; j -= gap) 
      {
       if (v[j] <= v[j + gap]) break;
       tmp = v[j];
       v[j] = v[j + gap];
       v[j + gap] = tmp;
      }
    }
  }
}

double *mle_cen(int *sptr, int n_len,int *n1, int m_len, double fc,double Lambda, double K_tmp)
{

  double sumlenL, sumlenH, cenL, cenH;
  double sum_s, sum2_s, mean_s, var_s, dtmp;
  int start, stop;
  int i, nf;
	double *wtmpa;
	wtmpa=(double *)malloc(2*sizeof(double));
  int nit = 0;
	double wtmpb=0.0;
  double deriv, deriv2, lambda, old_lambda, sum = 0.0;
  int w_tmp;
  w_tmp=0;
  nf = (fc/2.0) * n_len;
  start = nf;
  stop = n_len - nf;
  st_sort(sptr,n_len);
  sum_s = sum2_s = 0.0;
  for (i=start; i<stop; i++) 
  {
    sum_s += sptr[i];
  }
  dtmp = (double)(stop-start);
  mean_s = sum_s/dtmp;
  for (i=start; i<stop; i++) 
  {
    sum2_s += sptr[i] * sptr[i];
  }
  var_s = sum2_s/(dtmp-1.0);
  sumlenL = sumlenH = 0.0;
  for (i=0; i<start; i++) 
  {
    sumlenL += (double)n1[i];
  }
  for (i=stop; i<n_len; i++) 
  {
    sumlenH += (double)n1[i];
  }

  if (nf > 0) 
  {
    cenL = (double)sptr[start];
    cenH = (double)sptr[stop];
  }
  else 
  {
    cenL = (double)sptr[start]/2.0;
    cenH = (double)sptr[start]*2.0;
  }
  if (cenL >= cenH) 
  {
    printf("cenL is larger than cenH!mle_cen is wrong!\n");
    return NULL;
  }


  lambda = PI_SQRT6/sqrt(var_s);
  if (lambda > 1.0)
  {
    fprintf(stderr," Lambda initial estimate error: lambda: %6.4g; var_s: %6.4g\n",lambda,var_s);
    lambda = 0.2;
  }

  do 
  {
    deriv =   first_deriv_cen(lambda, sptr,n1, start, stop,sumlenL, cenL, sumlenH, cenH);
    deriv2 = second_deriv_cen(lambda, sptr,n1, start, stop,sumlenL, cenL, sumlenH, cenH); 
    old_lambda = lambda;
    if (lambda - deriv/deriv2 > 0.0) lambda = lambda - deriv/deriv2;
    else lambda = lambda/2.0;
    nit++;
  } while (fabs((lambda - old_lambda)/lambda) > TINY && nit < MAX_NIT);



  if (nit >= MAX_NIT) return NULL;
  
  for(i = start; i < stop ; i++) 
  {
    sum += (double) n1[i] * exp(- lambda * (double)sptr[i]);
  }
  wtmpa[0] = lambda;
  wtmpa[1]= (double)n_len/((double)(m_len)*(sum+sumlenL*exp(-lambda*cenL)-sumlenH*exp(-lambda*cenH)));
  return wtmpa;
}
double
first_deriv_cen(double lambda, int *sptr,int *n1, int start, int stop,double sumlenL, double cenL, double sumlenH, double cenH) 
{
  int i;
  double sum = 0.0, sum1 = 0.0, sum2 = 0.0;
  double s, l, es;

  for(i = start ; i < stop ; i++) 
  {
    s = (double)sptr[i];
    l = (double)n1[i];
    es = exp(-lambda * s );
    sum += s;
    sum2 += l * es;
    sum1 += s * l * es;
  }
  sum1 += sumlenL*cenL*exp(-lambda*cenL) - sumlenH*cenH*exp(-lambda*cenH);
  sum2 += sumlenL*exp(-lambda*cenL) - sumlenH*exp(-lambda*cenH);
  return (1.0 / lambda) - (sum /(double)(stop-start)) + (sum1 / sum2);
}

double
second_deriv_cen(double lambda, int *sptr,int *n1, int start, int stop,double sumlenL, double cenL, double sumlenH, double cenH) 
{

  double sum1 = 0.0, sum2 = 0.0, sum3 = 0.0;
  double s, l, es;
  int i;

  for(i = start ; i < stop ; i++) 
  {
    s = (double)sptr[i];
    l = (double)n1[i];
    es = exp(-lambda * s);
    sum2 += l * es;
    sum1 += l * s * es;
    sum3 += l * s * s * es;
  }
  sum1 += sumlenL*cenL*exp(-lambda*cenL) - sumlenH*cenH*exp(-lambda*cenH);
  sum2 += sumlenL*exp(-lambda * cenL) -  sumlenH*exp(-lambda * cenH);
  sum3 += sumlenL*cenL*cenL * exp(-lambda * cenL) -
    sumlenH*cenH*cenH * exp(-lambda * cenH);
  return ((sum1 * sum1) / (sum2 * sum2)) - (sum3 / sum2) - (1.0 / (lambda * lambda));
}
void findmax_score(int *a,int *b,int n)
{
  int i=0;
  int c[500];
  int wtmp;
  for(i=0;i<n;i++)
  {
    if(a[i]>b[i]||a[i]==b[i])
    {
      c[i]=a[i];
    }
    else
    {
      c[i]=b[i];
    }
  }
}
 int nascii[128]={
	EL,NA,NA,NA,NA,NA,NA,NA,NA,NA,EL,NA,NA,EL,NA,NA,
	NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,
	NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,ES,NA,NA,16,NA,NA,
	NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,ES,NA,NA,ES,NA,
	NA, 1,15, 2,12,NA,NA, 3,13,NA,NA,11,NA, 8,16,NA,
	 6, 7, 6,10, 4, 5,14, 9,17, 7,NA,NA,NA,NA,NA,NA,
	NA, 1,15, 2,12,NA,NA, 3,13,NA,NA,11,NA, 8,16,NA,
	 6, 7, 6,10, 4, 5,14, 9,17, 7,NA,NA,NA,NA,NA,NA};

int npam[450] = {
	 5,					
	-4, 5,						
	-4,-4, 5,				
	-4,-4,-4, 5,				
	-4,-4,-4, 5, 5,				
	 2,-1, 2,-1,-1, 2,				
	-1, 2,-1, 2, 2,-2, 2,				
	 2, 2,-1,-1,-1,-1,-1, 2,		
	 2,-1,-1, 2, 2, 1, 1, 1, 2,		
	-1, 2, 2,-1,-1, 1, 1, 1,-1, 2,			
	-1,-1, 2, 2, 2, 1, 1,-1, 1, 1, 2,		
	 1,-2, 1, 1, 1, 1,-1,-1, 1,-1, 1, 1,		
	 1, 1,-2, 1, 1,-1, 1, 1, 1,-1,-1,-1, 1,		
	 1, 1, 1,-2,-2, 1,-1, 1,-1, 1,-1,-1,-1, 1,	
	-2, 1, 1, 1, 1,-1, 1,-1,-1, 1, 1,-1,-1,-1, 1,	
	-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1, 
	-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1}; 
struct pstruct{
	int maxlen;
	int pam2[MAXSQ][MAXSQ];
	int dnaseq;
	int pam_h;
	int pam_l;
	int pamoff;
	int have_pam2;
	int nsq;
};
struct m_rand_struct {
	int seed;
};
struct f_struct {
  int 							max_res;
  unsigned char      bias;
  unsigned char *    byte_score;
  void *             workspace;
  int                alphabet_size;
  int                word_iter;
  int                byte_iter;
  void *             word_score_memory;
  unsigned short *    word_score;
  void *             byte_score_memory;
  void *             workspace_memory;
  size_t             workspace_bytes;
  int                try_8bit;
  int                done_8bit;
  int                done_16bit;
  int                owns_workspace_memory;
} ftr;
#if defined(__AVX2__)
inline bool calc_score_use_avx2_runtime();
#endif

static const int CALC_SCORE_SHUFFLE_COUNT = 1002;
static const int CALC_SCORE_MLE_COUNT = 500;
static const size_t CALC_SCORE_MAX_CACHED_SHUFFLE_LENGTH = 8192;
static const int CALC_SCORE_PROFILE_ROW_COUNT = 7;
static const unsigned char CALC_SCORE_PROFILE_CODES[CALC_SCORE_PROFILE_ROW_COUNT] = {0, 1, 2, 3, 4, 5, 16};
struct m_rand_struct *my_srand(int set)	
{
  struct timeval t;
  int n;
  struct m_rand_struct *my_rand_state;

  if ((my_rand_state = (struct m_rand_struct *)calloc(1, sizeof(struct m_rand_struct)))==NULL) 
  {
    fprintf(stderr," *** [my_srand] cannot allocate random state ***\n");
    exit(1);
  } 
  gettimeofday(&t,NULL);
  n = t.tv_usec % 65535;
  if ((n % 2)==0) n++;
  if (set > 0) {  my_rand_state->seed = set;}
  else {my_rand_state->seed = n;}
  my_rand_state->seed=33;
  return my_rand_state;
}
unsigned int my_nrand(int n, struct m_rand_struct *my_rand_state)
{
  unsigned int rn;
  int lo, hi, test;
  hi = my_rand_state->seed / QQ;
  lo = my_rand_state->seed % QQ;
  test = AA * lo - RW * hi;
  if (test > 0) { my_rand_state->seed = test;}
  else {my_rand_state->seed = test + MM;}
  rn = my_rand_state->seed;
  return rn%n;
}
void shuffle(unsigned char *from, unsigned char *to, int n, struct m_rand_struct *rand_state)
{
  int i,j; unsigned char tmp;

  if (from != to) 
  {
    memcpy((void *)to,(void *)from,n);
  }

  for (i=n; i>0; i--) 
  {
    j = my_nrand(i, rand_state);
    tmp = to[j];
    to[j] = to[i-1];
    to[i-1] = tmp;
  }
  to[n] = 0;
}
unsigned char *cg_str(char *str,int *ascii,int *n)
{
	int i=0,j=0;
	unsigned	char *a;
	i=strlen(str);
	a=(unsigned char *)malloc(i*sizeof(unsigned char));
	for(j=0;j<i;j++)
	{
    switch(ascii[str[j]])
    {
      case 1:
      a[j]='\001';break;
      case 2:
      a[j]='\002';break;
      case 3:
      a[j]='\003';break;
      case 4:
      a[j]='\004';break;
      case 5:
      a[j]='\005';break;
      case 16:
      a[j]='\020';break;
      default:
      a[j]='\020';break;
    }
	}
  *n=i;
	return a;
}
void alloc_pam (int d1, int d2, struct pstruct *ppst)
{
  int     i, *d2p;
  char err_str[128];
	ppst->dnaseq=0;
	ppst->pam_h=-1;
	ppst->pam_l=1;
	ppst->pamoff=0;
  ppst->have_pam2 = 1;
}
void
init_pam2 (struct pstruct *ppst,int *aascii)
{
  int     i, j, k, nsq, sa_t;
  int ix_j, ix_l, ix_i, p_i, p_j;
	char pam_sq[]="\0ACGTURYMWSKDHVBNX";
  nsq = ppst->nsq;
	int pam_sq_n=17;
  ppst->pam2[0][0] = -BIGNUM;
  ppst->pam_h = -1; ppst->pam_l = 1;
	int *pam;
	pam=npam;
  k = 0;
	int *pascii;
	pascii=aascii;
  sa_t = nascii['X'];
  for(i=0;i<MAXSQ;i++)
  {
    for(j=0;j<MAXSQ;j++)
    {
      ppst->pam2[i][j]=0;
    }
  }
  for (i = 1; i < sa_t; i++) 
  {
    p_i = pascii[pam_sq[i]];
    ppst->pam2[0][p_i] = ppst->pam2[p_i][0] = -BIGNUM;
    for (j = 1; j <= i; j++) 
    {
      p_j = pascii[pam_sq[j]];
      ppst->pam2[p_j][p_i] = ppst->pam2[p_i][p_j] = pam[k++] - ppst->pamoff;
      if (ppst->pam_l > ppst->pam2[p_i][p_j]) ppst->pam_l = ppst->pam2[p_i][p_j];
      if (ppst->pam_h < ppst->pam2[p_i][p_j]) ppst->pam_h = ppst->pam2[p_i][p_j];
    }
  }
  for (i = sa_t+1; i < pam_sq_n; i++) 
  {
    p_i = pascii[pam_sq[i]];
    ppst->pam2[0][p_i] = ppst->pam2[p_i][0] = -BIGNUM;
  } 
}
inline unsigned char calc_score_profile_code_for_index(int profileIndex)
{
  return CALC_SCORE_PROFILE_CODES[profileIndex];
}

inline unsigned char encode_calc_score_profile_index(unsigned char encodedBase)
{
  switch(encodedBase)
  {
    case 1: return 1;
    case 2: return 2;
    case 3: return 3;
    case 4: return 4;
    case 5: return 5;
    case 16: return 6;
    default: return 6;
  }
}

void init_work(unsigned char *aa0,
               int n0,
               struct pstruct *ppst,
               struct f_struct **f_arg,
               void *shared_workspace_memory = NULL,
               void *shared_workspace = NULL,
               size_t shared_workspace_bytes = 0)
{
  struct f_struct *f_str;
  int e,f,i,j;
	unsigned char *pc;
	unsigned short *ps;
  int ip=0;
  int n_count;
  int col_len;
  int bias,data,nsq=CALC_SCORE_PROFILE_ROW_COUNT,overflow;
  int word_col_len;
  int word_n_count;
  int byte_col_len;
  int byte_n_count;
  size_t workspace_bytes;
  const bool useAvx2Layout =
#if defined(__AVX2__)
    calc_score_use_avx2_runtime();
#else
    false;
#endif
  f_str=(struct f_struct *)calloc(1,sizeof(struct f_struct));
  word_col_len = (n0 + 7) / 8;
  word_n_count = (n0 + 7) & 0xfffffff8;
  byte_col_len = (n0 + 15) / 16;
  byte_n_count = (n0 + 15) & 0xfffffff0;
  if(useAvx2Layout)
  {
    word_col_len = (n0 + 15) / 16;
    word_n_count = (n0 + 15) & 0xfffffff0;
    byte_col_len = (n0 + 31) / 32;
    byte_n_count = (n0 + 31) & 0xffffffe0;
    workspace_bytes = static_cast<size_t>(3 * (word_col_len > byte_col_len ? word_col_len : byte_col_len)) * sizeof(__m256i) + 256;
  }
  else
  {
    workspace_bytes = static_cast<size_t>(3 * (word_col_len > byte_col_len ? word_col_len : byte_col_len)) * sizeof(__m128i) + 256;
  }
  if(shared_workspace_memory != NULL && shared_workspace != NULL && shared_workspace_bytes >= workspace_bytes)
  {
    f_str->workspace_memory = shared_workspace_memory;
    f_str->workspace = shared_workspace;
    f_str->workspace_bytes = shared_workspace_bytes;
    f_str->owns_workspace_memory = 0;
  }
  else
  {
    f_str->workspace_memory = (void *)malloc(workspace_bytes);
    f_str->workspace  = (void *) ((((size_t) f_str->workspace_memory) + 255) & (~0xff));
    f_str->workspace_bytes = workspace_bytes;
    f_str->owns_workspace_memory = 1;
  }
  f_str->word_score_memory = (void *)malloc(static_cast<size_t>(word_n_count) * static_cast<size_t>(nsq) * sizeof (short) + 256);
  f_str->byte_score_memory = (void *)malloc(static_cast<size_t>(byte_n_count) * static_cast<size_t>(nsq) * sizeof (char) + 256);
  f_str->word_score = (unsigned short *) ((((size_t) f_str->word_score_memory) + 255) & (~0xff));
  f_str->byte_score = (unsigned char *) ((((size_t) f_str->byte_score_memory) + 255) & (~0xff));
  overflow = 0;
  bias = 127;
  for (i = 1; i < nsq ; i++) 
	{
    for (j = 1; j < nsq ; j++) 
		{
      data = ppst->pam2[i][j];
	    if (data < -128) 
	    {
	      fprintf(stderr,"*** ERROR *** data out of range: %d[%d][%d,%d]\n",data, ip, i, j);
	    }
      if (data < bias) 
			{
        bias = data;
      }
    }
  }
	ps = f_str->word_score;
  col_len = word_col_len;
  n_count = word_n_count;
  for (f = 0; f < n_count; ++f) 
	{
    *ps++ = 0;
  }
  for (f = 1; f < nsq ; f++) 
	{
    const int targetCode = calc_score_profile_code_for_index(f);
    for (e = 0; e < col_len; e++) 
		{
      for (i = e; i < n_count; i += col_len) 
			{
        if (i >= n0) 
				{
          data = 0;
        } 
        else 
				{
          data = ppst->pam2[aa0[i]][targetCode];
        }
        *ps++ = (unsigned short)data;
      }
    }
  }
	pc = f_str->byte_score;
  col_len = byte_col_len;
  n_count = byte_n_count;
  for (f = 0; f < n_count; ++f) 
	{
    *pc++ = 0;
  }
  for (f = 1; f < nsq ; f++) 
	{
    const int targetCode = calc_score_profile_code_for_index(f);
    for (e = 0; e < col_len; e++) 
		{
      for (i = e; i < n_count; i += col_len) 
			{
        if (i >= n0) 
				{
          data = -bias;
        } 
        else 
				{
          data = ppst->pam2[aa0[i]][targetCode] - bias;
        }
        if (data > 255) 
				{
          printf("Fatal error. data: %d bias: %d, position: %d/%d, Score out of range for 8-bit SSE2 datatype.\n",data, bias, f, e);
          exit(1);
        }
        *pc++ = (unsigned char)data;
      }
    }
  }
  f_str->bias = (unsigned char) (-bias);
  f_str->alphabet_size = nsq;
  f_str->word_iter = word_col_len;
  f_str->byte_iter = byte_col_len;
  f_str->try_8bit = (overflow == 0) ? 1 : 0;
  f_str->done_8bit  = 0;
  f_str->done_16bit = 0;
  f_str->max_res =3*n0/2>MIN_RES?3*n0/2:MIN_RES;
  *f_arg = f_str;
}
void close_work_f_str(struct f_struct **f_arg)
{
  struct f_struct *f_str;
  f_str=*f_arg;
  if(f_str!=NULL)
  {
    if(f_str->owns_workspace_memory)
    {
      free(f_str->workspace_memory);
    }
    free(f_str->word_score_memory);
    free(f_str->byte_score_memory);
  }
  free(f_str);
  *f_arg=NULL;
}

#if defined(__AVX2__)
inline bool calc_score_use_avx2_runtime()
{
  const char *forceAvx2 = getenv("LONGTARGET_FORCE_AVX2");
  if(forceAvx2 != NULL && forceAvx2[0] != '\0' && strcmp(forceAvx2,"0") != 0)
  {
    return true;
  }
  const char *disableAvx2 = getenv("LONGTARGET_DISABLE_AVX2");
  if(disableAvx2 != NULL && disableAvx2[0] != '\0' && strcmp(disableAvx2,"0") != 0)
  {
    return false;
  }
#if defined(__APPLE__)
  static int cachedUseAvx2 = -1;
  if(cachedUseAvx2 >= 0)
  {
    return cachedUseAvx2 != 0;
  }
  int translated = 0;
  size_t translatedSize = sizeof(translated);
  if(sysctlbyname("sysctl.proc_translated", &translated, &translatedSize, NULL, 0) == 0 && translated != 0)
  {
    cachedUseAvx2 = 0;
    return false;
  }
  cachedUseAvx2 = 1;
  return true;
#else
  return true;
#endif
}

inline __m256i calc_score_shift_left_1_byte_256(__m256i value)
{
  const __m256i shifted = _mm256_slli_si256(value, 1);
  const __m256i carry = _mm256_srli_si256(_mm256_permute2x128_si256(value, value, 0x08), 15);
  return _mm256_or_si256(shifted, carry);
}

inline __m256i calc_score_shift_left_2_bytes_256(__m256i value)
{
  const __m256i shifted = _mm256_slli_si256(value, 2);
  const __m256i carry = _mm256_srli_si256(_mm256_permute2x128_si256(value, value, 0x08), 14);
  return _mm256_or_si256(shifted, carry);
}
#endif

template <bool kPermuted>
inline unsigned char calc_score_db_code_u16(const unsigned char *db_sequence,
                                            const uint16_t *permutation,
                                            int index);

template <>
inline unsigned char calc_score_db_code_u16<false>(const unsigned char *db_sequence,
                                                   const uint16_t *permutation,
                                                   int index)
{
  (void)permutation;
  return db_sequence[index];
}

template <>
inline unsigned char calc_score_db_code_u16<true>(const unsigned char *db_sequence,
                                                  const uint16_t *permutation,
                                                  int index)
{
  return db_sequence[permutation[index]];
}

template <bool kPermuted>
static inline int smith_waterman_sse2_word_impl_u16(const unsigned char *query_sequence,
                                                    unsigned short *query_profile_word,
                                                    const int query_length,
                                                    const unsigned char *db_sequence,
                                                    const uint16_t *permutation,
                                                    const int db_length,
                                                    unsigned short gap_open,
                                                    unsigned short gap_extend,
                                                    struct f_struct *f_str)
{
  (void)query_length;
#if defined(__AVX2__)
  if(calc_score_use_avx2_runtime())
  {
    int i, j, k;
    short score;
    int cmp;
    const int iter = f_str->word_iter;
    __m256i *p;
    __m256i *workspace = (__m256i *) f_str->workspace;
    __m256i E, F, H;
    __m256i v_maxscore;
    __m256i v_gapopen;
    __m256i v_gapextend;
    const __m256i v_min = _mm256_setr_epi16(static_cast<short>(0x8000),0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);
    __m256i v_temp;
    __m256i *pHLoad, *pHStore;
    __m256i *pE;
    __m256i *pScore;
    __m128i v_maxscore128;
    __m128i v_reduce128;
    (void)query_sequence;

    v_gapopen = _mm256_set1_epi16(static_cast<short>(gap_open));
    v_gapextend = _mm256_set1_epi16(static_cast<short>(gap_extend));
    v_maxscore = _mm256_set1_epi16(static_cast<short>(0x8000));
    k = 2 * iter;
    p = workspace;
    for(i = 0; i < k; ++i)
    {
      _mm256_store_si256(p++, v_maxscore);
    }
    pE = workspace;
    pHStore = pE + iter;
    pHLoad = pHStore + iter;
    for(i = 0; i < db_length; ++i)
    {
      const int db_code = static_cast<int>(calc_score_db_code_u16<kPermuted>(db_sequence, permutation, i));
      pScore = (__m256i *) query_profile_word + db_code * iter;
      F = _mm256_set1_epi16(static_cast<short>(0x8000));
      H = _mm256_load_si256(pHStore + iter - 1);
      H = calc_score_shift_left_2_bytes_256(H);
      H = _mm256_or_si256(H, v_min);
      p = pHLoad;
      pHLoad = pHStore;
      pHStore = p;
      for(j = 0; j < iter; ++j)
      {
        E = _mm256_load_si256(pE + j);
        H = _mm256_adds_epi16(H, *pScore++);
        v_maxscore = _mm256_max_epi16(v_maxscore, H);
        H = _mm256_max_epi16(H, E);
        H = _mm256_max_epi16(H, F);
        _mm256_store_si256(pHStore + j, H);
        H = _mm256_subs_epi16(H, v_gapopen);
        E = _mm256_subs_epi16(E, v_gapextend);
        E = _mm256_max_epi16(E, H);
        F = _mm256_subs_epi16(F, v_gapextend);
        F = _mm256_max_epi16(F, H);
        _mm256_store_si256(pE + j, E);
        H = _mm256_load_si256(pHLoad + j);
      }
      j = 0;
      H = _mm256_load_si256(pHStore + j);
      F = calc_score_shift_left_2_bytes_256(F);
      F = _mm256_or_si256(F, v_min);
      v_temp = _mm256_subs_epi16(H, v_gapopen);
      v_temp = _mm256_cmpgt_epi16(F, v_temp);
      cmp = _mm256_movemask_epi8(v_temp);
      while(cmp != 0x00000000)
      {
        E = _mm256_load_si256(pE + j);
        H = _mm256_max_epi16(H, F);
        _mm256_store_si256(pHStore + j, H);
        H = _mm256_subs_epi16(H, v_gapopen);
        E = _mm256_max_epi16(E, H);
        _mm256_store_si256(pE + j, E);
        F = _mm256_subs_epi16(F, v_gapextend);
        ++j;
        if(j >= iter)
        {
          j = 0;
          F = calc_score_shift_left_2_bytes_256(F);
          F = _mm256_or_si256(F, v_min);
        }
        H = _mm256_load_si256(pHStore + j);
        v_temp = _mm256_subs_epi16(H, v_gapopen);
        v_temp = _mm256_cmpgt_epi16(F, v_temp);
        cmp = _mm256_movemask_epi8(v_temp);
      }
    }

    v_maxscore128 = _mm_max_epi16(_mm256_castsi256_si128(v_maxscore), _mm256_extracti128_si256(v_maxscore, 1));
    v_reduce128 = _mm_srli_si128(v_maxscore128, 8);
    v_maxscore128 = _mm_max_epi16(v_maxscore128, v_reduce128);
    v_reduce128 = _mm_srli_si128(v_maxscore128, 4);
    v_maxscore128 = _mm_max_epi16(v_maxscore128, v_reduce128);
    v_reduce128 = _mm_srli_si128(v_maxscore128, 2);
    v_maxscore128 = _mm_max_epi16(v_maxscore128, v_reduce128);
    score = static_cast<short>(_mm_extract_epi16(v_maxscore128, 0));
    return score + 32768;
  }
#endif
  int     i, j, k;
  short   score;
  int     cmp;
  int     iter = f_str->word_iter;
  __m128i *p;
  __m128i *workspace = (__m128i *) f_str->workspace;
  __m128i E, F, H;
  __m128i v_maxscore;
  __m128i v_gapopen;
  __m128i v_gapextend;
  __m128i v_min;
  __m128i v_minimums;
  __m128i v_temp;
  __m128i *pHLoad, *pHStore;
  __m128i *pE;
  __m128i *pScore;
  v_gapopen = _mm_setzero_si128();	
  v_gapopen = _mm_insert_epi16 (v_gapopen, gap_open, 0);
  v_gapopen = _mm_shufflelo_epi16 (v_gapopen, 0);
  v_gapopen = _mm_shuffle_epi32 (v_gapopen, 0);
  v_gapextend = _mm_setzero_si128();
  v_gapextend = _mm_insert_epi16 (v_gapextend, gap_extend, 0);
  v_gapextend = _mm_shufflelo_epi16 (v_gapextend, 0);
  v_gapextend = _mm_shuffle_epi32 (v_gapextend, 0);
  v_maxscore = _mm_setzero_si128();	
  v_maxscore = _mm_cmpeq_epi16 (v_maxscore, v_maxscore);
  v_maxscore = _mm_slli_epi16 (v_maxscore, 15);
  v_minimums = _mm_shuffle_epi32 (v_maxscore, 0);
  v_min = _mm_shuffle_epi32 (v_maxscore, 0);
  v_min = _mm_srli_si128 (v_min, 14);
  k = 2 * iter;
  p = workspace;
  for (i = 0; i < k; i++)
  {
      _mm_store_si128 (p++, v_maxscore);
  }
  pE = workspace;
  pHStore = pE + iter;
  pHLoad = pHStore + iter;
  for (i = 0; i < db_length; ++i)
  {
    const int db_code = static_cast<int>(calc_score_db_code_u16<kPermuted>(db_sequence, permutation, i));
    pScore = (__m128i *) query_profile_word + db_code * iter;
    F = _mm_setzero_si128();	
    F = _mm_cmpeq_epi16 (F, F);
    F = _mm_slli_epi16 (F, 15);
    H = _mm_load_si128 (pHStore + iter - 1);
    H = _mm_slli_si128 (H, 2);
    H = _mm_or_si128 (H, v_min);
    p = pHLoad;
    pHLoad = pHStore;
    pHStore = p;
    for (j = 0; j < iter; j++)
    {
      E = _mm_load_si128 (pE + j);
      H = _mm_adds_epi16 (H, *pScore++);
      v_maxscore = _mm_max_epi16 (v_maxscore, H);
      H = _mm_max_epi16 (H, E);
      H = _mm_max_epi16 (H, F);
      _mm_store_si128 (pHStore + j, H);
      H = _mm_subs_epi16 (H, v_gapopen);
      E = _mm_subs_epi16 (E, v_gapextend);
      E = _mm_max_epi16 (E, H);
      F = _mm_subs_epi16 (F, v_gapextend);
      F = _mm_max_epi16 (F, H);
      _mm_store_si128 (pE + j, E);
      H = _mm_load_si128 (pHLoad + j);
    }
    j = 0;
    H = _mm_load_si128 (pHStore + j);
    F = _mm_slli_si128 (F, 2);
    F = _mm_or_si128 (F, v_min);
    v_temp = _mm_subs_epi16 (H, v_gapopen);
    v_temp = _mm_cmpgt_epi16 (F, v_temp);
    cmp  = _mm_movemask_epi8 (v_temp);
    while (cmp != 0x0000) 
    {
      E = _mm_load_si128 (pE + j);
      H = _mm_max_epi16 (H, F);
      _mm_store_si128 (pHStore + j, H);
      H = _mm_subs_epi16 (H, v_gapopen);
      E = _mm_max_epi16 (E, H);
      _mm_store_si128 (pE + j, E);
      F = _mm_subs_epi16 (F, v_gapextend);
      j++;
      if (j >= iter)
      {
        j = 0;
        F = _mm_slli_si128 (F, 2);
        F = _mm_or_si128 (F, v_min);
      }
      H = _mm_load_si128 (pHStore + j);
      v_temp = _mm_subs_epi16 (H, v_gapopen);
      v_temp = _mm_cmpgt_epi16 (F, v_temp);
      cmp  = _mm_movemask_epi8 (v_temp);
    }
  }
  v_temp = _mm_srli_si128 (v_maxscore, 8);
  v_maxscore = _mm_max_epi16 (v_maxscore, v_temp);
  v_temp = _mm_srli_si128 (v_maxscore, 4);
  v_maxscore = _mm_max_epi16 (v_maxscore, v_temp);
  v_temp = _mm_srli_si128 (v_maxscore, 2);
  v_maxscore = _mm_max_epi16 (v_maxscore, v_temp);
  score = _mm_extract_epi16 (v_maxscore, 0);
  return score + 32768;
}

int smith_waterman_sse2_word(const unsigned char *     query_sequence,
                         unsigned short *    query_profile_word,
                         const int                 query_length,
                         const unsigned char *     db_sequence,
                         const int                 db_length,
                         unsigned short      gap_open,
                         unsigned short      gap_extend,
                         struct f_struct *   f_str)
{
  (void)query_length;
#if defined(__AVX2__)
  if(calc_score_use_avx2_runtime())
  {
    int i, j, k;
    short score;
    int cmp;
    const int iter = f_str->word_iter;
    __m256i *p;
    __m256i *workspace = (__m256i *) f_str->workspace;
    __m256i E, F, H;
    __m256i v_maxscore;
    __m256i v_gapopen;
    __m256i v_gapextend;
    const __m256i v_min = _mm256_setr_epi16(static_cast<short>(0x8000),0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);
    __m256i v_temp;
    __m256i *pHLoad, *pHStore;
    __m256i *pE;
    __m256i *pScore;
    __m128i v_maxscore128;
    __m128i v_reduce128;
    (void)query_sequence;

    v_gapopen = _mm256_set1_epi16(static_cast<short>(gap_open));
    v_gapextend = _mm256_set1_epi16(static_cast<short>(gap_extend));
    v_maxscore = _mm256_set1_epi16(static_cast<short>(0x8000));
    k = 2 * iter;
    p = workspace;
    for(i = 0; i < k; ++i)
    {
      _mm256_store_si256(p++, v_maxscore);
    }
    pE = workspace;
    pHStore = pE + iter;
    pHLoad = pHStore + iter;
    for(i = 0; i < db_length; ++i)
    {
      pScore = (__m256i *) query_profile_word + db_sequence[i] * iter;
      F = _mm256_set1_epi16(static_cast<short>(0x8000));
      H = _mm256_load_si256(pHStore + iter - 1);
      H = calc_score_shift_left_2_bytes_256(H);
      H = _mm256_or_si256(H, v_min);
      p = pHLoad;
      pHLoad = pHStore;
      pHStore = p;
      for(j = 0; j < iter; ++j)
      {
        E = _mm256_load_si256(pE + j);
        H = _mm256_adds_epi16(H, *pScore++);
        v_maxscore = _mm256_max_epi16(v_maxscore, H);
        H = _mm256_max_epi16(H, E);
        H = _mm256_max_epi16(H, F);
        _mm256_store_si256(pHStore + j, H);
        H = _mm256_subs_epi16(H, v_gapopen);
        E = _mm256_subs_epi16(E, v_gapextend);
        E = _mm256_max_epi16(E, H);
        F = _mm256_subs_epi16(F, v_gapextend);
        F = _mm256_max_epi16(F, H);
        _mm256_store_si256(pE + j, E);
        H = _mm256_load_si256(pHLoad + j);
      }
      j = 0;
      H = _mm256_load_si256(pHStore + j);
      F = calc_score_shift_left_2_bytes_256(F);
      F = _mm256_or_si256(F, v_min);
      v_temp = _mm256_subs_epi16(H, v_gapopen);
      v_temp = _mm256_cmpgt_epi16(F, v_temp);
      cmp = _mm256_movemask_epi8(v_temp);
      while(cmp != 0x00000000)
      {
        E = _mm256_load_si256(pE + j);
        H = _mm256_max_epi16(H, F);
        _mm256_store_si256(pHStore + j, H);
        H = _mm256_subs_epi16(H, v_gapopen);
        E = _mm256_max_epi16(E, H);
        _mm256_store_si256(pE + j, E);
        F = _mm256_subs_epi16(F, v_gapextend);
        ++j;
        if(j >= iter)
        {
          j = 0;
          F = calc_score_shift_left_2_bytes_256(F);
          F = _mm256_or_si256(F, v_min);
        }
        H = _mm256_load_si256(pHStore + j);
        v_temp = _mm256_subs_epi16(H, v_gapopen);
        v_temp = _mm256_cmpgt_epi16(F, v_temp);
        cmp = _mm256_movemask_epi8(v_temp);
      }
    }

    v_maxscore128 = _mm_max_epi16(_mm256_castsi256_si128(v_maxscore), _mm256_extracti128_si256(v_maxscore, 1));
    v_reduce128 = _mm_srli_si128(v_maxscore128, 8);
    v_maxscore128 = _mm_max_epi16(v_maxscore128, v_reduce128);
    v_reduce128 = _mm_srli_si128(v_maxscore128, 4);
    v_maxscore128 = _mm_max_epi16(v_maxscore128, v_reduce128);
    v_reduce128 = _mm_srli_si128(v_maxscore128, 2);
    v_maxscore128 = _mm_max_epi16(v_maxscore128, v_reduce128);
    score = static_cast<short>(_mm_extract_epi16(v_maxscore128, 0));
    return score + 32768;
  }
#endif
  int     i, j, k;
  short   score;
  int     cmp;
  int     iter = f_str->word_iter;
  __m128i *p;
  __m128i *workspace = (__m128i *) f_str->workspace;
  __m128i E, F, H;
  __m128i v_maxscore;
  __m128i v_gapopen;
  __m128i v_gapextend;
  __m128i v_min;
  __m128i v_minimums;
  __m128i v_temp;
  __m128i *pHLoad, *pHStore;
  __m128i *pE;
  __m128i *pScore;
  v_gapopen = _mm_setzero_si128();	
  v_gapopen = _mm_insert_epi16 (v_gapopen, gap_open, 0);
  v_gapopen = _mm_shufflelo_epi16 (v_gapopen, 0);
  v_gapopen = _mm_shuffle_epi32 (v_gapopen, 0);
  v_gapextend = _mm_setzero_si128();
  v_gapextend = _mm_insert_epi16 (v_gapextend, gap_extend, 0);
  v_gapextend = _mm_shufflelo_epi16 (v_gapextend, 0);
  v_gapextend = _mm_shuffle_epi32 (v_gapextend, 0);
  v_maxscore = _mm_setzero_si128();	
  v_maxscore = _mm_cmpeq_epi16 (v_maxscore, v_maxscore);
  v_maxscore = _mm_slli_epi16 (v_maxscore, 15);
  v_minimums = _mm_shuffle_epi32 (v_maxscore, 0);
  v_min = _mm_shuffle_epi32 (v_maxscore, 0);
  v_min = _mm_srli_si128 (v_min, 14);
  k = 2 * iter;
  p = workspace;
  for (i = 0; i < k; i++)
  {
      _mm_store_si128 (p++, v_maxscore);
  }
  pE = workspace;
  pHStore = pE + iter;
  pHLoad = pHStore + iter;
  for (i = 0; i < db_length; ++i)
  {
    pScore = (__m128i *) query_profile_word + db_sequence[i] * iter;
    F = _mm_setzero_si128();	
    F = _mm_cmpeq_epi16 (F, F);
    F = _mm_slli_epi16 (F, 15);
    H = _mm_load_si128 (pHStore + iter - 1);
    H = _mm_slli_si128 (H, 2);
    H = _mm_or_si128 (H, v_min);
    p = pHLoad;
    pHLoad = pHStore;
    pHStore = p;
    for (j = 0; j < iter; j++)
    {
      E = _mm_load_si128 (pE + j);
      H = _mm_adds_epi16 (H, *pScore++);
      v_maxscore = _mm_max_epi16 (v_maxscore, H);
      H = _mm_max_epi16 (H, E);
      H = _mm_max_epi16 (H, F);
      _mm_store_si128 (pHStore + j, H);
      H = _mm_subs_epi16 (H, v_gapopen);
      E = _mm_subs_epi16 (E, v_gapextend);
      E = _mm_max_epi16 (E, H);
      F = _mm_subs_epi16 (F, v_gapextend);
      F = _mm_max_epi16 (F, H);
      _mm_store_si128 (pE + j, E);
      H = _mm_load_si128 (pHLoad + j);
    }
    j = 0;
    H = _mm_load_si128 (pHStore + j);
    F = _mm_slli_si128 (F, 2);
    F = _mm_or_si128 (F, v_min);
    v_temp = _mm_subs_epi16 (H, v_gapopen);
    v_temp = _mm_cmpgt_epi16 (F, v_temp);
    cmp  = _mm_movemask_epi8 (v_temp);
    while (cmp != 0x0000) 
    {
      E = _mm_load_si128 (pE + j);
      H = _mm_max_epi16 (H, F);
      _mm_store_si128 (pHStore + j, H);
      H = _mm_subs_epi16 (H, v_gapopen);
      E = _mm_max_epi16 (E, H);
      _mm_store_si128 (pE + j, E);
      F = _mm_subs_epi16 (F, v_gapextend);
      j++;
      if (j >= iter)
      {
        j = 0;
        F = _mm_slli_si128 (F, 2);
        F = _mm_or_si128 (F, v_min);
      }
      H = _mm_load_si128 (pHStore + j);
      v_temp = _mm_subs_epi16 (H, v_gapopen);
      v_temp = _mm_cmpgt_epi16 (F, v_temp);
      cmp  = _mm_movemask_epi8 (v_temp);
    }
  }
  v_temp = _mm_srli_si128 (v_maxscore, 8);
  v_maxscore = _mm_max_epi16 (v_maxscore, v_temp);
  v_temp = _mm_srli_si128 (v_maxscore, 4);
  v_maxscore = _mm_max_epi16 (v_maxscore, v_temp);
  v_temp = _mm_srli_si128 (v_maxscore, 2);
  v_maxscore = _mm_max_epi16 (v_maxscore, v_temp);
  score = _mm_extract_epi16 (v_maxscore, 0);
  return score + 32768;
}

static inline int smith_waterman_sse2_word_permuted_u16(const unsigned char *query_sequence,
                                                        unsigned short *query_profile_word,
                                                        const int query_length,
                                                        const unsigned char *db_sequence,
                                                        const uint16_t *permutation,
                                                        const int db_length,
                                                        unsigned short gap_open,
                                                        unsigned short gap_extend,
                                                        struct f_struct *f_str)
{
  return smith_waterman_sse2_word_impl_u16<true>(query_sequence,
                                                 query_profile_word,
                                                 query_length,
                                                 db_sequence,
                                                 permutation,
                                                 db_length,
                                                 gap_open,
                                                 gap_extend,
                                                 f_str);
}

template <bool kPermuted>
static inline int smith_waterman_sse2_byte_impl_u16(const unsigned char *query_sequence,
                                                    unsigned char *query_profile_byte,
                                                    const int query_length,
                                                    const unsigned char *db_sequence,
                                                    const uint16_t *permutation,
                                                    const int db_length,
                                                    unsigned char bias,
                                                    unsigned char gap_open,
                                                    unsigned char gap_extend,
                                                    struct f_struct *f_str)
{
  (void)query_length;
#if defined(__AVX2__)
  if(calc_score_use_avx2_runtime())
  {
    int i, j, k;
    int score;
    int cmp;
    const int iter = f_str->byte_iter;
    __m256i *p;
    __m256i *workspace = (__m256i *) f_str->workspace;
    __m256i E, F, H;
    __m256i v_maxscore;
    __m256i v_bias;
    __m256i v_gapopen;
    __m256i v_gapextend;
    __m256i v_temp;
    const __m256i v_zero = _mm256_setzero_si256();
    __m256i *pHLoad, *pHStore;
    __m256i *pE;
    __m256i *pScore;
    __m128i v_maxscore128;
    (void)query_sequence;

    v_bias = _mm256_set1_epi8(static_cast<char>(bias));
    v_gapopen = _mm256_set1_epi8(static_cast<char>(gap_open));
    v_gapextend = _mm256_set1_epi8(static_cast<char>(gap_extend));
    v_maxscore = _mm256_setzero_si256();
    k = iter * 2;
    p = workspace;
    for(i = 0; i < k; ++i)
    {
      _mm256_store_si256(p++, v_maxscore);
    }
    pE = workspace;
    pHStore = pE + iter;
    pHLoad = pHStore + iter;
    for(i = 0; i < db_length; ++i)
    {
      const int db_code = static_cast<int>(calc_score_db_code_u16<kPermuted>(db_sequence, permutation, i));
      pScore = (__m256i *) query_profile_byte + db_code * iter;
      F = _mm256_setzero_si256();
      H = _mm256_load_si256(pHStore + iter - 1);
      H = calc_score_shift_left_1_byte_256(H);
      p = pHLoad;
      pHLoad = pHStore;
      pHStore = p;
      for(j = 0; j < iter; ++j)
      {
        E = _mm256_load_si256(pE + j);
        H = _mm256_adds_epu8(H, *pScore++);
        H = _mm256_subs_epu8(H, v_bias);
        v_maxscore = _mm256_max_epu8(v_maxscore, H);
        H = _mm256_max_epu8(H, E);
        H = _mm256_max_epu8(H, F);
        _mm256_store_si256(pHStore + j, H);
        H = _mm256_subs_epu8(H, v_gapopen);
        E = _mm256_subs_epu8(E, v_gapextend);
        E = _mm256_max_epu8(E, H);
        F = _mm256_subs_epu8(F, v_gapextend);
        F = _mm256_max_epu8(F, H);
        _mm256_store_si256(pE + j, E);
        H = _mm256_load_si256(pHLoad + j);
      }
      j = 0;
      H = _mm256_load_si256(pHStore + j);
      F = calc_score_shift_left_1_byte_256(F);
      v_temp = _mm256_subs_epu8(H, v_gapopen);
      v_temp = _mm256_subs_epu8(F, v_temp);
      v_temp = _mm256_cmpeq_epi8(v_temp, v_zero);
      cmp = _mm256_movemask_epi8(v_temp);
      while(cmp != -1)
      {
        E = _mm256_load_si256(pE + j);
        H = _mm256_max_epu8(H, F);
        _mm256_store_si256(pHStore + j, H);
        H = _mm256_subs_epu8(H, v_gapopen);
        E = _mm256_max_epu8(E, H);
        _mm256_store_si256(pE + j, E);
        F = _mm256_subs_epu8(F, v_gapextend);
        ++j;
        if(j >= iter)
        {
          j = 0;
          F = calc_score_shift_left_1_byte_256(F);
        }
        H = _mm256_load_si256(pHStore + j);
        v_temp = _mm256_subs_epu8(H, v_gapopen);
        v_temp = _mm256_subs_epu8(F, v_temp);
        v_temp = _mm256_cmpeq_epi8(v_temp, v_zero);
        cmp = _mm256_movemask_epi8(v_temp);
      }
    }

    v_maxscore128 = _mm_max_epu8(_mm256_castsi256_si128(v_maxscore), _mm256_extracti128_si256(v_maxscore, 1));
    v_maxscore128 = _mm_max_epu8(v_maxscore128, _mm_srli_si128(v_maxscore128, 8));
    v_maxscore128 = _mm_max_epu8(v_maxscore128, _mm_srli_si128(v_maxscore128, 4));
    v_maxscore128 = _mm_max_epu8(v_maxscore128, _mm_srli_si128(v_maxscore128, 2));
    v_maxscore128 = _mm_max_epu8(v_maxscore128, _mm_srli_si128(v_maxscore128, 1));
    score = _mm_extract_epi16(v_maxscore128, 0);
    score = score & 0x00ff;
    if(score + bias >= 255)
    {
      score = 255;
    }
    return score;
  }
#endif
  int     i, j, k;
  int     score;
  int     dup;
  int     cmp;
  int     iter = f_str->byte_iter; 
  __m128i *p;
  __m128i *workspace = (__m128i *) f_str->workspace;
  __m128i E, F, H;
  __m128i v_maxscore;
  __m128i v_bias;
  __m128i v_gapopen;
  __m128i v_gapextend;
  __m128i v_temp;
  __m128i v_zero;
  __m128i *pHLoad, *pHStore;
  __m128i *pE;
  __m128i *pScore;
  dup    = ((short) bias << 8) | bias;
  v_bias = _mm_setzero_si128();
  v_bias = _mm_insert_epi16 (v_bias, dup, 0);
  v_bias = _mm_shufflelo_epi16 (v_bias, 0);
  v_bias = _mm_shuffle_epi32 (v_bias, 0);
  dup  = ((short) gap_open << 8) | gap_open;
  v_gapopen = _mm_setzero_si128();
  v_gapopen = _mm_insert_epi16 (v_gapopen, dup, 0);
  v_gapopen = _mm_shufflelo_epi16 (v_gapopen, 0);
  v_gapopen = _mm_shuffle_epi32 (v_gapopen, 0);
  dup  = ((short) gap_extend << 8) | gap_extend;
  v_gapextend = _mm_setzero_si128();
  v_gapextend = _mm_insert_epi16 (v_gapextend, dup, 0);
  v_gapextend = _mm_shufflelo_epi16 (v_gapextend, 0);
  v_gapextend = _mm_shuffle_epi32 (v_gapextend, 0);
  v_maxscore = _mm_setzero_si128();	
  v_zero = _mm_setzero_si128();	
  k = iter * 2;
  p = workspace;
  for (i = 0; i < k; i++)
  {
      _mm_store_si128 (p++, v_maxscore);
  }
  pE = workspace;
  pHStore = pE + iter;
  pHLoad = pHStore + iter;
  for (i = 0; i < db_length; ++i)
  {
    const int db_code = static_cast<int>(calc_score_db_code_u16<kPermuted>(db_sequence, permutation, i));
    pScore = (__m128i *) query_profile_byte + db_code * iter;
    F = _mm_setzero_si128();
    H = _mm_load_si128 (pHStore + iter - 1);
    H = _mm_slli_si128 (H, 1);
    p = pHLoad;
    pHLoad = pHStore;
    pHStore = p;
    for (j = 0; j < iter; j++)
    {
      E = _mm_load_si128 (pE + j);
      H = _mm_adds_epu8 (H, *pScore++);
      H = _mm_subs_epu8 (H, v_bias);
      v_maxscore = _mm_max_epu8 (v_maxscore, H);
      H = _mm_max_epu8 (H, E);
      H = _mm_max_epu8 (H, F);
      _mm_store_si128 (pHStore + j, H);
      H = _mm_subs_epu8 (H, v_gapopen);
      E = _mm_subs_epu8 (E, v_gapextend);
      E = _mm_max_epu8 (E, H);
      F = _mm_subs_epu8 (F, v_gapextend);
      F = _mm_max_epu8 (F, H);
      _mm_store_si128 (pE + j, E);
      H = _mm_load_si128 (pHLoad + j);
    }
    j = 0;
    H = _mm_load_si128 (pHStore + j);
    F = _mm_slli_si128 (F, 1);
    v_temp = _mm_subs_epu8 (H, v_gapopen);
    v_temp = _mm_subs_epu8 (F, v_temp);
    v_temp = _mm_cmpeq_epi8 (v_temp, v_zero);
    cmp  = _mm_movemask_epi8 (v_temp);
    while (cmp != 0xffff) 
    {
      E = _mm_load_si128 (pE + j);
      H = _mm_max_epu8 (H, F);
      _mm_store_si128 (pHStore + j, H);
      H = _mm_subs_epu8 (H, v_gapopen);
      E = _mm_max_epu8 (E, H);
      _mm_store_si128 (pE + j, E);
      F = _mm_subs_epu8 (F, v_gapextend);
      j++;
      if (j >= iter)
      {
        j = 0;
        F = _mm_slli_si128 (F, 1);
      }
      H = _mm_load_si128 (pHStore + j);
      v_temp = _mm_subs_epu8 (H, v_gapopen);
      v_temp = _mm_subs_epu8 (F, v_temp);
      v_temp = _mm_cmpeq_epi8 (v_temp, v_zero);
      cmp  = _mm_movemask_epi8 (v_temp);
    }
  }
  v_temp = _mm_srli_si128 (v_maxscore, 8);
  v_maxscore = _mm_max_epu8 (v_maxscore, v_temp);
  v_temp = _mm_srli_si128 (v_maxscore, 4);
  v_maxscore = _mm_max_epu8 (v_maxscore, v_temp);
  v_temp = _mm_srli_si128 (v_maxscore, 2);
  v_maxscore = _mm_max_epu8 (v_maxscore, v_temp);
  v_temp = _mm_srli_si128 (v_maxscore, 1);
  v_maxscore = _mm_max_epu8 (v_maxscore, v_temp);
  score = _mm_extract_epi16 (v_maxscore, 0);
  score = score & 0x00ff;
  if (score + bias >= 255)
  {
      score = 255;
  }
  return score;
}

int
smith_waterman_sse2_byte(const unsigned char *     query_sequence,
                         unsigned char *     query_profile_byte,
                         const int                 query_length,
                         const unsigned char *     db_sequence,
                         const int                 db_length,
                         unsigned char       bias,
                         unsigned char       gap_open,
                         unsigned char       gap_extend,
                         struct f_struct *   f_str)
{
  (void)query_length;
#if defined(__AVX2__)
  if(calc_score_use_avx2_runtime())
  {
    int i, j, k;
    int score;
    int cmp;
    const int iter = f_str->byte_iter;
    __m256i *p;
    __m256i *workspace = (__m256i *) f_str->workspace;
    __m256i E, F, H;
    __m256i v_maxscore;
    __m256i v_bias;
    __m256i v_gapopen;
    __m256i v_gapextend;
    __m256i v_temp;
    const __m256i v_zero = _mm256_setzero_si256();
    __m256i *pHLoad, *pHStore;
    __m256i *pE;
    __m256i *pScore;
    __m128i v_maxscore128;
    (void)query_sequence;

    v_bias = _mm256_set1_epi8(static_cast<char>(bias));
    v_gapopen = _mm256_set1_epi8(static_cast<char>(gap_open));
    v_gapextend = _mm256_set1_epi8(static_cast<char>(gap_extend));
    v_maxscore = _mm256_setzero_si256();
    k = iter * 2;
    p = workspace;
    for(i = 0; i < k; ++i)
    {
      _mm256_store_si256(p++, v_maxscore);
    }
    pE = workspace;
    pHStore = pE + iter;
    pHLoad = pHStore + iter;
    for(i = 0; i < db_length; ++i)
    {
      pScore = (__m256i *) query_profile_byte + db_sequence[i] * iter;
      F = _mm256_setzero_si256();
      H = _mm256_load_si256(pHStore + iter - 1);
      H = calc_score_shift_left_1_byte_256(H);
      p = pHLoad;
      pHLoad = pHStore;
      pHStore = p;
      for(j = 0; j < iter; ++j)
      {
        E = _mm256_load_si256(pE + j);
        H = _mm256_adds_epu8(H, *pScore++);
        H = _mm256_subs_epu8(H, v_bias);
        v_maxscore = _mm256_max_epu8(v_maxscore, H);
        H = _mm256_max_epu8(H, E);
        H = _mm256_max_epu8(H, F);
        _mm256_store_si256(pHStore + j, H);
        H = _mm256_subs_epu8(H, v_gapopen);
        E = _mm256_subs_epu8(E, v_gapextend);
        E = _mm256_max_epu8(E, H);
        F = _mm256_subs_epu8(F, v_gapextend);
        F = _mm256_max_epu8(F, H);
        _mm256_store_si256(pE + j, E);
        H = _mm256_load_si256(pHLoad + j);
      }
      j = 0;
      H = _mm256_load_si256(pHStore + j);
      F = calc_score_shift_left_1_byte_256(F);
      v_temp = _mm256_subs_epu8(H, v_gapopen);
      v_temp = _mm256_subs_epu8(F, v_temp);
      v_temp = _mm256_cmpeq_epi8(v_temp, v_zero);
      cmp = _mm256_movemask_epi8(v_temp);
      while(cmp != -1)
      {
        E = _mm256_load_si256(pE + j);
        H = _mm256_max_epu8(H, F);
        _mm256_store_si256(pHStore + j, H);
        H = _mm256_subs_epu8(H, v_gapopen);
        E = _mm256_max_epu8(E, H);
        _mm256_store_si256(pE + j, E);
        F = _mm256_subs_epu8(F, v_gapextend);
        ++j;
        if(j >= iter)
        {
          j = 0;
          F = calc_score_shift_left_1_byte_256(F);
        }
        H = _mm256_load_si256(pHStore + j);
        v_temp = _mm256_subs_epu8(H, v_gapopen);
        v_temp = _mm256_subs_epu8(F, v_temp);
        v_temp = _mm256_cmpeq_epi8(v_temp, v_zero);
        cmp = _mm256_movemask_epi8(v_temp);
      }
    }

    v_maxscore128 = _mm_max_epu8(_mm256_castsi256_si128(v_maxscore), _mm256_extracti128_si256(v_maxscore, 1));
    v_maxscore128 = _mm_max_epu8(v_maxscore128, _mm_srli_si128(v_maxscore128, 8));
    v_maxscore128 = _mm_max_epu8(v_maxscore128, _mm_srli_si128(v_maxscore128, 4));
    v_maxscore128 = _mm_max_epu8(v_maxscore128, _mm_srli_si128(v_maxscore128, 2));
    v_maxscore128 = _mm_max_epu8(v_maxscore128, _mm_srli_si128(v_maxscore128, 1));
    score = _mm_extract_epi16(v_maxscore128, 0);
    score = score & 0x00ff;
    if(score + bias >= 255)
    {
      score = 255;
    }
    return score;
  }
#endif
  int     i, j, k;
  int     score;
  int     dup;
  int     cmp;
  int     iter = f_str->byte_iter; 
  __m128i *p;
  __m128i *workspace = (__m128i *) f_str->workspace;
  __m128i E, F, H;
  __m128i v_maxscore;
  __m128i v_bias;
  __m128i v_gapopen;
  __m128i v_gapextend;
  __m128i v_temp;
  __m128i v_zero;
  __m128i *pHLoad, *pHStore;
  __m128i *pE;
  __m128i *pScore;
  dup    = ((short) bias << 8) | bias;
  v_bias = _mm_setzero_si128();
  v_bias = _mm_insert_epi16 (v_bias, dup, 0);
  v_bias = _mm_shufflelo_epi16 (v_bias, 0);
  v_bias = _mm_shuffle_epi32 (v_bias, 0);
  dup  = ((short) gap_open << 8) | gap_open;
  v_gapopen = _mm_setzero_si128();
  v_gapopen = _mm_insert_epi16 (v_gapopen, dup, 0);
  v_gapopen = _mm_shufflelo_epi16 (v_gapopen, 0);
  v_gapopen = _mm_shuffle_epi32 (v_gapopen, 0);
  dup  = ((short) gap_extend << 8) | gap_extend;
  v_gapextend = _mm_setzero_si128();
  v_gapextend = _mm_insert_epi16 (v_gapextend, dup, 0);
  v_gapextend = _mm_shufflelo_epi16 (v_gapextend, 0);
  v_gapextend = _mm_shuffle_epi32 (v_gapextend, 0);
  v_maxscore = _mm_setzero_si128();	
  v_zero = _mm_setzero_si128();	
  k = iter * 2;
  p = workspace;
  for (i = 0; i < k; i++)
  {
      _mm_store_si128 (p++, v_maxscore);
  }
  pE = workspace;
  pHStore = pE + iter;
  pHLoad = pHStore + iter;
  for (i = 0; i < db_length; ++i)
  {
    pScore = (__m128i *) query_profile_byte + db_sequence[i] * iter;
    F = _mm_setzero_si128();
    H = _mm_load_si128 (pHStore + iter - 1);
    H = _mm_slli_si128 (H, 1);
    p = pHLoad;
    pHLoad = pHStore;
    pHStore = p;
    for (j = 0; j < iter; j++)
    {
      E = _mm_load_si128 (pE + j);
      H = _mm_adds_epu8 (H, *pScore++);
      H = _mm_subs_epu8 (H, v_bias);
      v_maxscore = _mm_max_epu8 (v_maxscore, H);
      H = _mm_max_epu8 (H, E);
      H = _mm_max_epu8 (H, F);
      _mm_store_si128 (pHStore + j, H);
      H = _mm_subs_epu8 (H, v_gapopen);
      E = _mm_subs_epu8 (E, v_gapextend);
      E = _mm_max_epu8 (E, H);
      F = _mm_subs_epu8 (F, v_gapextend);
      F = _mm_max_epu8 (F, H);
      _mm_store_si128 (pE + j, E);
      H = _mm_load_si128 (pHLoad + j);
    }
    j = 0;
    H = _mm_load_si128 (pHStore + j);
    F = _mm_slli_si128 (F, 1);
    v_temp = _mm_subs_epu8 (H, v_gapopen);
    v_temp = _mm_subs_epu8 (F, v_temp);
    v_temp = _mm_cmpeq_epi8 (v_temp, v_zero);
    cmp  = _mm_movemask_epi8 (v_temp);
    while (cmp != 0xffff) 
    {
      E = _mm_load_si128 (pE + j);
      H = _mm_max_epu8 (H, F);
      _mm_store_si128 (pHStore + j, H);
      H = _mm_subs_epu8 (H, v_gapopen);
      E = _mm_max_epu8 (E, H);
      _mm_store_si128 (pE + j, E);
      F = _mm_subs_epu8 (F, v_gapextend);
      j++;
      if (j >= iter)
      {
        j = 0;
        F = _mm_slli_si128 (F, 1);
      }
      H = _mm_load_si128 (pHStore + j);
      v_temp = _mm_subs_epu8 (H, v_gapopen);
      v_temp = _mm_subs_epu8 (F, v_temp);
      v_temp = _mm_cmpeq_epi8 (v_temp, v_zero);
      cmp  = _mm_movemask_epi8 (v_temp);
    }
  }
  v_temp = _mm_srli_si128 (v_maxscore, 8);
  v_maxscore = _mm_max_epu8 (v_maxscore, v_temp);
  v_temp = _mm_srli_si128 (v_maxscore, 4);
  v_maxscore = _mm_max_epu8 (v_maxscore, v_temp);
  v_temp = _mm_srli_si128 (v_maxscore, 2);
  v_maxscore = _mm_max_epu8 (v_maxscore, v_temp);
  v_temp = _mm_srli_si128 (v_maxscore, 1);
  v_maxscore = _mm_max_epu8 (v_maxscore, v_temp);
  score = _mm_extract_epi16 (v_maxscore, 0);
  score = score & 0x00ff;
  if (score + bias >= 255)
  {
      score = 255;
  }
  return score;
}

static inline int smith_waterman_sse2_byte_permuted_u16(const unsigned char *query_sequence,
                                                        unsigned char *query_profile_byte,
                                                        const int query_length,
                                                        const unsigned char *db_sequence,
                                                        const uint16_t *permutation,
                                                        const int db_length,
                                                        unsigned char bias,
                                                        unsigned char gap_open,
                                                        unsigned char gap_extend,
                                                        struct f_struct *f_str)
{
  return smith_waterman_sse2_byte_impl_u16<true>(query_sequence,
                                                 query_profile_byte,
                                                 query_length,
                                                 db_sequence,
                                                 permutation,
                                                 db_length,
                                                 bias,
                                                 gap_open,
                                                 gap_extend,
                                                 f_str);
}

inline unsigned char encode_calc_score_base(char base)
{
  switch(nascii[static_cast<unsigned char>(base)])
  {
    case 1: return '\001';
    case 2: return '\002';
    case 3: return '\003';
    case 4: return '\004';
    case 5: return '\005';
    case 16: return '\020';
    default: return '\020';
  }
}

inline unsigned char encode_calc_score_target_base(char base)
{
  return encode_calc_score_profile_index(encode_calc_score_base(base));
}

struct CalcScoreTargetBaseLut
{
  CalcScoreTargetBaseLut()
  {
    for(int i = 0; i < 128; ++i)
    {
      lut[i] = encode_calc_score_target_base(static_cast<char>(i));
    }
    defaultCode = lut[static_cast<unsigned char>('N')];
    for(int i = 128; i < 256; ++i)
    {
      lut[i] = defaultCode;
    }
  }

  unsigned char lut[256];
  unsigned char defaultCode;
};

inline const CalcScoreTargetBaseLut &calc_score_target_base_lut()
{
  static const CalcScoreTargetBaseLut instance;
  return instance;
}

inline char reverse_complement_calc_score_base(char base)
{
  switch(base)
  {
    case 'A': return 'T';
    case 'T': return 'A';
    case 'C': return 'G';
    case 'G': return 'C';
    case 'U': return 'A';
    case 'N': return 'N';
    default: return 'N';
  }
}

inline void encode_calc_score_sequence(const string &sequence,vector<unsigned char> &encodedSequence)
{
  encodedSequence.resize(sequence.size() + 1);
  for(size_t i = 0; i < sequence.size(); ++i)
  {
    encodedSequence[i] = encode_calc_score_base(sequence[i]);
  }
  encodedSequence[sequence.size()] = 0;
}

inline void encode_reverse_complement_calc_score_sequence(const string &sequence,vector<unsigned char> &encodedSequence)
{
  encodedSequence.resize(sequence.size() + 1);
  for(size_t i = 0; i < sequence.size(); ++i)
  {
    encodedSequence[i] = encode_calc_score_base(reverse_complement_calc_score_base(sequence[sequence.size() - i - 1]));
  }
  encodedSequence[sequence.size()] = 0;
}

inline int calc_score_align_target(const unsigned char *querySequence,
                                   const struct f_struct *profile,
                                   int queryLength,
                                   const unsigned char *targetSequence,
                                   int targetLength)
{
  int score = smith_waterman_sse2_byte(querySequence,
                                       profile->byte_score,
                                       queryLength,
                                       targetSequence,
                                       targetLength,
                                       profile->bias,
                                       '\020',
                                       '\004',
                                       const_cast<struct f_struct *>(profile));
  if(score >= 255)
  {
    score = smith_waterman_sse2_word(querySequence,
                                     profile->word_score,
                                     queryLength,
                                     targetSequence,
                                     targetLength,
                                     '\020',
                                     '\004',
                                     const_cast<struct f_struct *>(profile));
  }
  return score;
}

inline int calc_score_align_target_permuted_u16(const unsigned char *querySequence,
                                                const struct f_struct *profile,
                                                int queryLength,
                                                const unsigned char *targetSequence,
                                                const uint16_t *targetPermutation,
                                                int targetLength)
{
  int score = smith_waterman_sse2_byte_permuted_u16(querySequence,
                                                    profile->byte_score,
                                                    queryLength,
                                                    targetSequence,
                                                    targetPermutation,
                                                    targetLength,
                                                    profile->bias,
                                                    '\020',
                                                    '\004',
                                                    const_cast<struct f_struct *>(profile));
  if(score >= 255)
  {
    score = smith_waterman_sse2_word_permuted_u16(querySequence,
                                                  profile->word_score,
                                                  queryLength,
                                                  targetSequence,
                                                  targetPermutation,
                                                  targetLength,
                                                  '\020',
                                                  '\004',
                                                  const_cast<struct f_struct *>(profile));
  }
  return score;
}

inline void apply_calc_score_shuffle_permutation(const unsigned char *from,
                                                 unsigned char *to,
                                                 const uint32_t *permutation,
                                                 size_t length)
{
  for(size_t i = 0; i < length; ++i)
  {
    to[i] = from[permutation[i]];
  }
  to[length] = 0;
}

inline void apply_calc_score_shuffle_permutation(const unsigned char *from,
                                                 unsigned char *to,
                                                 const uint16_t *permutation,
                                                 size_t length)
{
  for(size_t i = 0; i < length; ++i)
  {
    to[i] = from[permutation[i]];
  }
  to[length] = 0;
}

struct CalcScoreWorkspace
{
  CalcScoreWorkspace():
    queryLength(0),
    forwardProfile(NULL),
    reverseProfile(NULL),
    cachedAa1Len(-1),
    cachedShufflePlanLength(0),
    shufflePlanEnabled(false),
    useShortShufflePlan(false)
  {
    memset(&pst,0,sizeof(pst));
    randState.seed = 33;
  }

  ~CalcScoreWorkspace()
  {
    resetQueryProfiles();
  }

  void resetQueryProfiles()
  {
    close_work_f_str(&forwardProfile);
    close_work_f_str(&reverseProfile);
    cachedQuery.clear();
    queryLength = 0;
    encodedQuery.clear();
    encodedReverseComplementQuery.clear();
  }

  void ensureTargetCapacity(size_t targetLength)
  {
    if(encodedTarget.size() < targetLength + 1)
    {
      encodedTarget.resize(targetLength + 1);
    }
    if(shuffledTarget.size() < targetLength + 1)
    {
      shuffledTarget.resize(targetLength + 1);
    }
  }

  void ensureAa1Length(int targetLength)
  {
    if(cachedAa1Len == targetLength)
    {
      return;
    }
    for(int i = 0; i < CALC_SCORE_MLE_COUNT; ++i)
    {
      aa1Len[i] = targetLength;
    }
    cachedAa1Len = targetLength;
  }

  void ensureShufflePlan(size_t targetLength)
  {
    if(cachedShufflePlanLength == targetLength)
    {
      return;
    }

    cachedShufflePlanLength = targetLength;
    shufflePlanEnabled = targetLength <= CALC_SCORE_MAX_CACHED_SHUFFLE_LENGTH;
    useShortShufflePlan = targetLength <= 65535;
    shufflePermutations.clear();
    shufflePermutations16.clear();
    if(!shufflePlanEnabled || targetLength == 0)
    {
      return;
    }

    const size_t flattenedLength = static_cast<size_t>(CALC_SCORE_SHUFFLE_COUNT) * targetLength;
    struct m_rand_struct shuffleRandState;
    shuffleRandState.seed = 33;
    if(useShortShufflePlan)
    {
      shufflePermutations16.resize(flattenedLength);
      vector<uint16_t> permutation(targetLength);
      for(int shuf_cnt = 0; shuf_cnt < CALC_SCORE_SHUFFLE_COUNT; ++shuf_cnt)
      {
        for(size_t i = 0; i < targetLength; ++i)
        {
          permutation[i] = static_cast<uint16_t>(i);
        }
        for(int i = static_cast<int>(targetLength); i > 0; --i)
        {
          const int j = static_cast<int>(my_nrand(i, &shuffleRandState));
          const uint16_t tmp = permutation[static_cast<size_t>(j)];
          permutation[static_cast<size_t>(j)] = permutation[static_cast<size_t>(i - 1)];
          permutation[static_cast<size_t>(i - 1)] = tmp;
        }
        memcpy(&shufflePermutations16[static_cast<size_t>(shuf_cnt) * targetLength],
               permutation.data(),
               targetLength * sizeof(uint16_t));
      }
    }
    else
    {
      shufflePermutations.resize(flattenedLength);
      vector<uint32_t> permutation(targetLength);
      for(int shuf_cnt = 0; shuf_cnt < CALC_SCORE_SHUFFLE_COUNT; ++shuf_cnt)
      {
        for(size_t i = 0; i < targetLength; ++i)
        {
          permutation[i] = static_cast<uint32_t>(i);
        }
        for(int i = static_cast<int>(targetLength); i > 0; --i)
        {
          const int j = static_cast<int>(my_nrand(i, &shuffleRandState));
          const uint32_t tmp = permutation[static_cast<size_t>(j)];
          permutation[static_cast<size_t>(j)] = permutation[static_cast<size_t>(i - 1)];
          permutation[static_cast<size_t>(i - 1)] = tmp;
        }
        memcpy(&shufflePermutations[static_cast<size_t>(shuf_cnt) * targetLength],
               permutation.data(),
               targetLength * sizeof(uint32_t));
      }
    }
  }

  void ensureQueryProfiles(const string &querySequence)
  {
    if(queryLength > 0 && cachedQuery == querySequence)
    {
      return;
    }

    resetQueryProfiles();
    cachedQuery = querySequence;
    queryLength = static_cast<int>(querySequence.size());
    encode_calc_score_sequence(querySequence, encodedQuery);
    encode_reverse_complement_calc_score_sequence(querySequence, encodedReverseComplementQuery);
    alloc_pam(MAXSQ,MAXSQ,&pst);
    init_pam2(&pst,nascii);
    init_work(encodedQuery.data(),queryLength,&pst,&forwardProfile);
    init_work(encodedReverseComplementQuery.data(),
              queryLength,
              &pst,
              &reverseProfile,
              forwardProfile->workspace_memory,
              forwardProfile->workspace,
              forwardProfile->workspace_bytes);
  }

  struct pstruct pst;
  int queryLength;
  struct f_struct *forwardProfile;
  struct f_struct *reverseProfile;
  string cachedQuery;
  vector<unsigned char> encodedQuery;
  vector<unsigned char> encodedReverseComplementQuery;
  vector<unsigned char> encodedTarget;
  vector<unsigned char> shuffledTarget;
  struct m_rand_struct randState;
  int cachedAa1Len;
  size_t cachedShufflePlanLength;
  bool shufflePlanEnabled;
  bool useShortShufflePlan;
  vector<uint32_t> shufflePermutations;
  vector<uint16_t> shufflePermutations16;
  int maxShufScore[CALC_SCORE_MLE_COUNT];
  int aa1Len[CALC_SCORE_MLE_COUNT];
};

inline int calc_score_with_workspace(const string &strA,const string &strB,CalcScoreWorkspace &workspace)
{
  workspace.ensureQueryProfiles(strA);
  const int n0 = workspace.queryLength;
  const int n1 = static_cast<int>(strB.size());
  int mle_thresh = 0;
  double *mle_rst = NULL;
  double lambda_tmp = 0.0;
  double K_tmp = 0.0;
  int tmp_score = 0;
  int pair_even_score = 0;

  workspace.ensureTargetCapacity(static_cast<size_t>(n1));
  workspace.ensureAa1Length(n1);
  workspace.ensureShufflePlan(static_cast<size_t>(n1));
  const CalcScoreTargetBaseLut &targetBaseLut = calc_score_target_base_lut();
  for(int i = 0; i < n1; ++i)
  {
    const unsigned char base = static_cast<unsigned char>(strB[static_cast<size_t>(i)]);
    workspace.encodedTarget[static_cast<size_t>(i)] = targetBaseLut.lut[base];
  }
  workspace.encodedTarget[static_cast<size_t>(n1)] = 0;

	  int last_score=0;
	  if(workspace.shufflePlanEnabled)
	  {
	    if(workspace.useShortShufflePlan)
	    {
	      const bool useMaterializedTarget =
#if defined(__AVX2__)
	        calc_score_use_avx2_runtime();
#else
	        false;
#endif
	      const unsigned char *encodedTarget = workspace.encodedTarget.data();
	      unsigned char *shuffledTarget = workspace.shuffledTarget.data();
	      const size_t targetLength = static_cast<size_t>(n1);
	      const uint16_t *permutations = workspace.shufflePermutations16.data();

	      if(useMaterializedTarget)
	      {
	        for(int pairIndex = 0; pairIndex < CALC_SCORE_MLE_COUNT; ++pairIndex)
	        {
	          const uint16_t *evenPermutation = permutations + static_cast<size_t>(pairIndex * 2) * targetLength;
	          const uint16_t *oddPermutation = evenPermutation + targetLength;
	          apply_calc_score_shuffle_permutation(encodedTarget,
	                                               shuffledTarget,
	                                               evenPermutation,
	                                               targetLength);
	          pair_even_score = calc_score_align_target(workspace.encodedQuery.data(),
	                                                    workspace.forwardProfile,
	                                                    n0,
	                                                    shuffledTarget,
	                                                    n1);
	          apply_calc_score_shuffle_permutation(encodedTarget,
	                                               shuffledTarget,
	                                               oddPermutation,
	                                               targetLength);
	          tmp_score = calc_score_align_target(workspace.encodedReverseComplementQuery.data(),
	                                              workspace.reverseProfile,
	                                              n0,
	                                              shuffledTarget,
	                                              n1);
	          workspace.maxShufScore[pairIndex] = pair_even_score > tmp_score ? pair_even_score : tmp_score;
	        }

	        {
	          const int pairIndex = CALC_SCORE_MLE_COUNT;
	          const uint16_t *evenPermutation = permutations + static_cast<size_t>(pairIndex * 2) * targetLength;
	          const uint16_t *oddPermutation = evenPermutation + targetLength;
	          apply_calc_score_shuffle_permutation(encodedTarget,
	                                               shuffledTarget,
	                                               evenPermutation,
	                                               targetLength);
	          pair_even_score = calc_score_align_target(workspace.encodedQuery.data(),
	                                                    workspace.forwardProfile,
	                                                    n0,
	                                                    shuffledTarget,
	                                                    n1);
	          apply_calc_score_shuffle_permutation(encodedTarget,
	                                               shuffledTarget,
	                                               oddPermutation,
	                                               targetLength);
	          tmp_score = calc_score_align_target(workspace.encodedReverseComplementQuery.data(),
	                                              workspace.reverseProfile,
	                                              n0,
	                                              shuffledTarget,
	                                              n1);
	          last_score = pair_even_score > tmp_score ? pair_even_score : tmp_score;
	        }
	      }
	      else
	      {
	        for(int pairIndex = 0; pairIndex < CALC_SCORE_MLE_COUNT; ++pairIndex)
	        {
	          const uint16_t *evenPermutation = permutations + static_cast<size_t>(pairIndex * 2) * targetLength;
	          const uint16_t *oddPermutation = evenPermutation + targetLength;
	          pair_even_score = calc_score_align_target_permuted_u16(workspace.encodedQuery.data(),
	                                                                 workspace.forwardProfile,
	                                                                 n0,
	                                                                 encodedTarget,
	                                                                 evenPermutation,
	                                                                 n1);
	          tmp_score = calc_score_align_target_permuted_u16(workspace.encodedReverseComplementQuery.data(),
	                                                           workspace.reverseProfile,
	                                                           n0,
	                                                           encodedTarget,
	                                                           oddPermutation,
	                                                           n1);
	          workspace.maxShufScore[pairIndex] = pair_even_score > tmp_score ? pair_even_score : tmp_score;
	        }

	        {
	          const int pairIndex = CALC_SCORE_MLE_COUNT;
	          const uint16_t *evenPermutation = permutations + static_cast<size_t>(pairIndex * 2) * targetLength;
	          const uint16_t *oddPermutation = evenPermutation + targetLength;
	          pair_even_score = calc_score_align_target_permuted_u16(workspace.encodedQuery.data(),
	                                                                 workspace.forwardProfile,
	                                                                 n0,
	                                                                 encodedTarget,
	                                                                 evenPermutation,
	                                                                 n1);
	          tmp_score = calc_score_align_target_permuted_u16(workspace.encodedReverseComplementQuery.data(),
	                                                           workspace.reverseProfile,
	                                                           n0,
	                                                           encodedTarget,
	                                                           oddPermutation,
	                                                           n1);
	          last_score = pair_even_score > tmp_score ? pair_even_score : tmp_score;
	        }
	      }
	    }
	    else
	    {
	      for(int pairIndex = 0; pairIndex <= CALC_SCORE_MLE_COUNT; ++pairIndex)
	      {
        apply_calc_score_shuffle_permutation(workspace.encodedTarget.data(),
                                             workspace.shuffledTarget.data(),
                                             &workspace.shufflePermutations[static_cast<size_t>(pairIndex * 2) * static_cast<size_t>(n1)],
                                             static_cast<size_t>(n1));
        pair_even_score = calc_score_align_target(workspace.encodedQuery.data(),
                                                  workspace.forwardProfile,
                                                  n0,
                                                  workspace.shuffledTarget.data(),
                                                  n1);
        apply_calc_score_shuffle_permutation(workspace.encodedTarget.data(),
                                             workspace.shuffledTarget.data(),
                                             &workspace.shufflePermutations[static_cast<size_t>(pairIndex * 2 + 1) * static_cast<size_t>(n1)],
                                             static_cast<size_t>(n1));
        tmp_score = calc_score_align_target(workspace.encodedReverseComplementQuery.data(),
                                            workspace.reverseProfile,
                                            n0,
                                            workspace.shuffledTarget.data(),
                                            n1);
        if(pairIndex < CALC_SCORE_MLE_COUNT)
        {
          workspace.maxShufScore[pairIndex] = pair_even_score > tmp_score ? pair_even_score : tmp_score;
        }
        else
        {
          last_score = pair_even_score > tmp_score ? pair_even_score : tmp_score;
        }
      }
    }
  }
  else
  {
    workspace.randState.seed = 33;
    for(int pairIndex = 0; pairIndex <= CALC_SCORE_MLE_COUNT; ++pairIndex)
    {
      shuffle(workspace.encodedTarget.data(),workspace.shuffledTarget.data(),n1,&workspace.randState);
      pair_even_score = calc_score_align_target(workspace.encodedQuery.data(),
                                                workspace.forwardProfile,
                                                n0,
                                                workspace.shuffledTarget.data(),
                                                n1);
      shuffle(workspace.encodedTarget.data(),workspace.shuffledTarget.data(),n1,&workspace.randState);
      tmp_score = calc_score_align_target(workspace.encodedReverseComplementQuery.data(),
                                          workspace.reverseProfile,
                                          n0,
                                          workspace.shuffledTarget.data(),
                                          n1);
      if(pairIndex < CALC_SCORE_MLE_COUNT)
      {
        workspace.maxShufScore[pairIndex] = pair_even_score > tmp_score ? pair_even_score : tmp_score;
      }
      else
      {
        last_score = pair_even_score > tmp_score ? pair_even_score : tmp_score;
      }
    }
  }
  workspace.maxShufScore[150]=last_score;
  mle_rst=mle_cen(workspace.maxShufScore,CALC_SCORE_MLE_COUNT,workspace.aa1Len,n0,0.0,lambda_tmp,K_tmp);
  if(mle_rst==NULL)
  {
    return 0;
  }
  lambda_tmp=mle_rst[0];
  K_tmp=mle_rst[1];
  mle_thresh=(int)((log((double)K_tmp*n1*n0)-log((double)10))/lambda_tmp+0.5);
  free(mle_rst);
  return mle_thresh;
}

inline int calc_score(string &strA,string &strB,int dnaStartPos,int rule)
{
  (void)dnaStartPos;
  (void)rule;
  static thread_local CalcScoreWorkspace workspace;
  return calc_score_with_workspace(strA,strB,workspace);
}
