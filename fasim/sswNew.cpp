/* The MIT License

   Copyright (c) 2012-2015 Boston College.

   Permission is hereby granted, free of charge, to any person obtaining
   a copy of this software and associated documentation files (the
   "Software"), to deal in the Software without restriction, including
   without limitation the rights to use, copy, modify, merge, publish,
   distribute, sublicense, and/or sell copies of the Software, and to
   permit persons to whom the Software is furnished to do so, subject to
   the following conditions:

   The above copyright notice and this permission notice shall be
   included in all copies or substantial portions of the Software.

   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
   EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
   MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
   NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
   BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
   ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
   CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
   SOFTWARE.
*/

/* The 2-clause BSD License

   Copyright 2006 Michael Farrar.

   Redistribution and use in source and binary forms, with or without
   modification, are permitted provided that the following conditions are
   met:

   1. Redistributions of source code must retain the above copyright
	  notice, this list of conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright
	  notice, this list of conditions and the following disclaimer in the
	  documentation and/or other materials provided with the distribution.

   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
   "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
   A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
   HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
   SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
   LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
   THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
   OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/*
 *  ssw.c
 *
 *  Created by Mengyao Zhao on 6/22/10.
 *  Copyright 2010 Boston College. All rights reserved.
 *	Version 1.2.4
 *	Last revision by Mengyao Zhao on 2019-03-04.
 *
 *  The lazy-F loop implementation was derived from SWPS3, which is
 *  MIT licensed under ETH Z  rich, Institute of Computational Science.
 *
 *  The core SW loop referenced the swsse2 implementation, which is
 *  BSD licensed under Micharl Farrar.
 */

 /* 2021-09-29 11:41:17: recursively getting alignment seems problematic,
  * some sub-optimal alignments will be ignored.
  * Now I considered another strategy: use maxColumn to record down all
  * alignments' score and end whose score is larger than threshold.
  * Then I begin to get all these alignments, which should be OK.
  * Now I need to record down the track information of maxColumn.
  *
  *
  *
  *
  *
  *



 */

 //#include <nmmintrin.h>
#include <emmintrin.h>
#if defined(__AVX2__)
#include <immintrin.h>
#endif
#include <stdint.h>
#include <limits.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include "ssw.h"
#include "ssw_oracle_trace.h"
#include <iostream>
using std::cout;
#ifdef __GNUC__
#define LIKELY(x) __builtin_expect((x),1)
#define UNLIKELY(x) __builtin_expect((x),0)
#else
#define LIKELY(x) (x)
#define UNLIKELY(x) (x)
#endif

/* Convert the coordinate in the scoring matrix into the coordinate in one line of the band. */
#define set_u(u, w, i, j) { int x=(i)-(w); x=x>0?x:0; (u)=(j)-x+1; }

/* Convert the coordinate in the direction matrix into the coordinate in one line of the band. */
#define set_d(u, w, i, j, p) { int x=(i)-(w); x=x>0?x:0; x=(j)-x; (u)=x*3+p; }

/*! @function
  @abstract  Round an integer to the next closest power-2 integer.
  @param  x  integer to be rounded (in place)
  @discussion x will be modified.
 */
#define kroundup32(x) (--(x), (x)|=(x)>>1, (x)|=(x)>>2, (x)|=(x)>>4, (x)|=(x)>>8, (x)|=(x)>>16, ++(x))

typedef struct {
	uint16_t score;
	int32_t ref;	 //0-based position
	int32_t read;    //alignment ending position on read, 0-based
} alignment_end;

typedef struct {
	uint32_t* seq;
	int32_t length;
	int32_t ref_begin_offset;
	int32_t read_begin_offset;
} cigar;

struct _profile {
	__m128i* profile_byte;	// 0: none
	__m128i* profile_word;	// 0: none
#if defined(__AVX2__)
	__m256i* profile_byte_avx2;	// 0: none
	__m256i* profile_word_avx2;	// 0: none
#endif
	const int8_t* read;
	const int8_t* mat;
	int32_t readLen;
	int32_t n;
	uint8_t bias;
};

static uint64_t g_ssw_avx2_active = 0;
static uint64_t g_ssw_avx2_calls = 0;
static uint64_t g_ssw_avx2_forward_calls = 0;
static uint64_t g_ssw_avx2_reverse_calls = 0;
static uint64_t g_ssw_avx2_byte_calls = 0;
static uint64_t g_ssw_avx2_word_calls = 0;
static uint64_t g_ssw_avx2_fallback_calls = 0;

static bool ssw_env_flag_enabled(const char* name) {
	const char* env = getenv(name);
	if (env == NULL || env[0] == '\0') return false;
	return env[0] != '0';
}

static bool ssw_avx2_requested_runtime() {
	static const bool enabled = ssw_env_flag_enabled("FASIM_SSW_AVX2");
	return enabled;
}

static bool ssw_env_equals(const char* name, const char* expected) {
	const char* env = getenv(name);
	return env != NULL && strcmp(env, expected) == 0;
}

static bool ssw_avx2_mode_all_runtime() {
	return ssw_env_equals("FASIM_SSW_AVX2_MODE", "all");
}

static uint64_t ssw_avx2_mode_runtime() {
	if (!ssw_avx2_requested_runtime()) return 0;
	if (ssw_env_equals("FASIM_SSW_AVX2_MODE", "all")) return 1;
	if (ssw_env_equals("FASIM_SSW_AVX2_MODE", "reverse_only")) return 3;
	if (ssw_env_equals("FASIM_SSW_AVX2_MODE", "off")) return 4;
	return 2;
}

static bool ssw_avx2_forward_enabled_runtime() {
	if (!ssw_avx2_requested_runtime()) return false;
	if (ssw_env_equals("FASIM_SSW_AVX2_MODE", "off")) return false;
	return !ssw_env_equals("FASIM_SSW_AVX2_MODE", "reverse_only");
}

static bool ssw_avx2_reverse_enabled_runtime() {
	if (!ssw_avx2_requested_runtime()) return false;
	if (ssw_env_equals("FASIM_SSW_AVX2_MODE", "off")) return false;
	return ssw_avx2_mode_all_runtime() || ssw_env_equals("FASIM_SSW_AVX2_MODE", "reverse_only");
}

static void* ssw_aligned_calloc(size_t count, size_t size, size_t alignment) {
	void* ptr = NULL;
	if (count == 0 || size == 0) return NULL;
	if (posix_memalign(&ptr, alignment, count * size) != 0) return NULL;
	memset(ptr, 0, count * size);
	return ptr;
}

/* array index is an ASCII character value from a CIGAR,
   element value is the corresponding integer opcode between 0 and 8 */
const uint8_t encoded_ops[] = {
	0,         0,         0,         0,
	0,         0,         0,         0,
	0,         0,         0,         0,
	0,         0,         0,         0,
	0,         0,         0,         0,
	0,         0,         0,         0,
	0,         0,         0,         0,
	0,         0,         0,         0,
	0 /*   */, 0 /* ! */, 0 /* " */, 0 /* # */,
	0 /* $ */, 0 /* % */, 0 /* & */, 0 /* ' */,
	0 /* ( */, 0 /* ) */, 0 /* * */, 0 /* + */,
	0 /* , */, 0 /* - */, 0 /* . */, 0 /* / */,
	0 /* 0 */, 0 /* 1 */, 0 /* 2 */, 0 /* 3 */,
	0 /* 4 */, 0 /* 5 */, 0 /* 6 */, 0 /* 7 */,
	0 /* 8 */, 0 /* 9 */, 0 /* : */, 0 /* ; */,
	0 /* < */, 7 /* = */, 0 /* > */, 0 /* ? */,
	0 /* @ */, 0 /* A */, 0 /* B */, 0 /* C */,
	2 /* D */, 0 /* E */, 0 /* F */, 0 /* G */,
	5 /* H */, 1 /* I */, 0 /* J */, 0 /* K */,
	0 /* L */, 0 /* M */, 3 /* N */, 0 /* O */,
	6 /* P */, 0 /* Q */, 0 /* R */, 4 /* S */,
	0 /* T */, 0 /* U */, 0 /* V */, 0 /* W */,
	8 /* X */, 0 /* Y */, 0 /* Z */, 0 /* [ */,
	0 /* \ */, 0 /* ] */, 0 /* ^ */, 0 /* _ */,
	0 /* ` */, 0 /* a */, 0 /* b */, 0 /* c */,
	0 /* d */, 0 /* e */, 0 /* f */, 0 /* g */,
	0 /* h */, 0 /* i */, 0 /* j */, 0 /* k */,
	0 /* l */, 0 /* m */, 0 /* n */, 0 /* o */,
	0 /* p */, 0 /* q */, 0 /* r */, 0 /* s */,
	0 /* t */, 0 /* u */, 0 /* v */, 0 /* w */,
	0 /* x */, 0 /* y */, 0 /* z */, 0 /* { */,
	0 /* | */, 0 /* } */, 0 /* ~ */, 0 /*  */
};

static thread_local ssw_align_internal_stats g_ssw_align_internal_stats = {0};
static thread_local uint8_t g_ssw_align_internal_stats_enabled = 0;

struct fasim_authority_profile_state {
	uint64_t stage_nanoseconds[FASIM_AUTHORITY_STAGE_COUNT];
	uint64_t stage_entries[FASIM_AUTHORITY_STAGE_COUNT];
	int current_stage;
	int parent_stack[64];
	uint64_t depth;
	uint64_t max_depth;
	uint64_t stack_errors;
	uint64_t last_transition_nanoseconds;
	uint8_t enabled;
};

static thread_local fasim_authority_profile_state g_fasim_authority_profile = {{0}, {0}, -1, {0}, 0, 0, 0, 0, 0};

static uint64_t ssw_now_nanoseconds(void) {
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return static_cast<uint64_t>(ts.tv_sec) * 1000000000ULL +
		static_cast<uint64_t>(ts.tv_nsec);
}

static void ssw_add_elapsed(uint64_t* slot, uint64_t start_nanoseconds) {
	if (slot != 0 && g_ssw_align_internal_stats_enabled) {
		*slot += ssw_now_nanoseconds() - start_nanoseconds;
	}
}

ssw_align_internal_stats ssw_align_internal_stats_snapshot(void) {
	return g_ssw_align_internal_stats;
}

void ssw_align_internal_stats_set_enabled(uint8_t enabled) {
	g_ssw_align_internal_stats_enabled = enabled != 0 ? 1 : 0;
}

uint8_t ssw_align_internal_stats_enabled(void) {
	return g_ssw_align_internal_stats_enabled;
}

static void fasim_authority_profile_charge_current(uint64_t now) {
	if (g_fasim_authority_profile.current_stage >= 0 &&
	    g_fasim_authority_profile.current_stage < FASIM_AUTHORITY_STAGE_COUNT) {
		g_fasim_authority_profile.stage_nanoseconds[
			g_fasim_authority_profile.current_stage] +=
			now - g_fasim_authority_profile.last_transition_nanoseconds;
	}
	g_fasim_authority_profile.last_transition_nanoseconds = now;
}

void fasim_authority_profile_reset(void) {
	memset(&g_fasim_authority_profile, 0, sizeof(g_fasim_authority_profile));
	g_fasim_authority_profile.current_stage = -1;
}

void fasim_authority_profile_set_enabled(uint8_t enabled) {
	if (enabled != 0) {
		if (!g_fasim_authority_profile.enabled) {
			g_fasim_authority_profile.last_transition_nanoseconds =
				ssw_now_nanoseconds();
		}
		g_fasim_authority_profile.enabled = 1;
		return;
	}
	if (g_fasim_authority_profile.enabled) {
		fasim_authority_profile_charge_current(ssw_now_nanoseconds());
	}
	g_fasim_authority_profile.enabled = 0;
}

uint8_t fasim_authority_profile_enabled(void) {
	return g_fasim_authority_profile.enabled;
}

void fasim_authority_profile_enter(uint8_t stage) {
	if (!g_fasim_authority_profile.enabled) {
		return;
	}
	const uint64_t now = ssw_now_nanoseconds();
	fasim_authority_profile_charge_current(now);
	if (stage >= FASIM_AUTHORITY_STAGE_COUNT ||
	    g_fasim_authority_profile.depth >=
			sizeof(g_fasim_authority_profile.parent_stack) /
			sizeof(g_fasim_authority_profile.parent_stack[0])) {
		++g_fasim_authority_profile.stack_errors;
		return;
	}
	g_fasim_authority_profile.parent_stack[g_fasim_authority_profile.depth++] =
		g_fasim_authority_profile.current_stage;
	g_fasim_authority_profile.current_stage = static_cast<int>(stage);
	++g_fasim_authority_profile.stage_entries[stage];
	if (g_fasim_authority_profile.depth > g_fasim_authority_profile.max_depth) {
		g_fasim_authority_profile.max_depth = g_fasim_authority_profile.depth;
	}
}

void fasim_authority_profile_leave(uint8_t stage) {
	if (!g_fasim_authority_profile.enabled) {
		return;
	}
	const uint64_t now = ssw_now_nanoseconds();
	fasim_authority_profile_charge_current(now);
	if (stage >= FASIM_AUTHORITY_STAGE_COUNT ||
	    g_fasim_authority_profile.depth == 0 ||
	    g_fasim_authority_profile.current_stage != static_cast<int>(stage)) {
		++g_fasim_authority_profile.stack_errors;
		return;
	}
	g_fasim_authority_profile.current_stage =
		g_fasim_authority_profile.parent_stack[--g_fasim_authority_profile.depth];
}

fasim_authority_profile_snapshot fasim_authority_profile_get_snapshot(void) {
	if (g_fasim_authority_profile.enabled) {
		fasim_authority_profile_charge_current(ssw_now_nanoseconds());
	}
	fasim_authority_profile_snapshot result;
	memset(&result, 0, sizeof(result));
	for (int i = 0; i < FASIM_AUTHORITY_STAGE_COUNT; ++i) {
		result.stage_nanoseconds[i] =
			g_fasim_authority_profile.stage_nanoseconds[i];
		result.stage_entries[i] = g_fasim_authority_profile.stage_entries[i];
	}
	result.stack_errors = g_fasim_authority_profile.stack_errors;
	result.max_depth = g_fasim_authority_profile.max_depth;
	result.active_depth = g_fasim_authority_profile.depth;
	return result;
}

class FasimAuthorityProfileScope {
public:
	explicit FasimAuthorityProfileScope(fasim_authority_profile_stage stage_value) :
		stage(stage_value), active(fasim_authority_profile_enabled() != 0) {
		if (active) {
			fasim_authority_profile_enter(static_cast<uint8_t>(stage));
		}
	}

	~FasimAuthorityProfileScope() {
		if (active) {
			fasim_authority_profile_leave(static_cast<uint8_t>(stage));
		}
	}

private:
	fasim_authority_profile_stage stage;
	bool active;
};

/* Generate query profile rearrange query sequence & calculate the weight of match/mismatch. */
static __m128i* qP_byte(const int8_t* read_num,
	const int8_t* mat,
	const int32_t readLen,
	const int32_t n,	/* the edge length of the squre matrix mat */
	uint8_t bias) {

	int32_t segLen = (readLen + 15) / 16; /* Split the 128 bit register into 16 pieces.
									 Each piece is 8 bit. Split the read into 16 segments.
									 Calculat 16 segments in parallel.
								   */
	__m128i* vProfile = (__m128i*)malloc(n * segLen * sizeof(__m128i));
	int8_t* t = (int8_t*)vProfile;
	int32_t nt, i, j, segNum;

	/* Generate query profile rearrange query sequence & calculate the weight of match/mismatch */
	for (nt = 0; LIKELY(nt < n); nt++) {
		for (i = 0; i < segLen; i++) {
			j = i;
			for (segNum = 0; LIKELY(segNum < 16); segNum++) {
				*t++ = j >= readLen ? bias : mat[nt * n + read_num[j]] + bias;
				j += segLen;
			}
		}
	}
	return vProfile;
}

#if defined(__AVX2__)
static __m256i* qP_byte_avx2(const int8_t* read_num,
	const int8_t* mat,
	const int32_t readLen,
	const int32_t n,
	uint8_t bias) {

	int32_t segLen = (readLen + 31) / 32;
	__m256i* vProfile = (__m256i*)ssw_aligned_calloc(
		static_cast<size_t>(n) * static_cast<size_t>(segLen),
		sizeof(__m256i),
		32);
	if (vProfile == NULL) return NULL;
	int8_t* t = (int8_t*)vProfile;
	int32_t nt, i, j, segNum;

	for (nt = 0; LIKELY(nt < n); nt++) {
		for (i = 0; i < segLen; i++) {
			j = i;
			for (segNum = 0; LIKELY(segNum < 32); segNum++) {
				*t++ = j >= readLen ? bias : mat[nt * n + read_num[j]] + bias;
				j += segLen;
			}
		}
	}
	return vProfile;
}

static inline __m256i ssw_shift_left_1_byte_avx2(__m256i value) {
	const __m256i shifted = _mm256_slli_si256(value, 1);
	const __m256i carry =
		_mm256_srli_si256(_mm256_permute2x128_si256(value, value, 0x08), 15);
	return _mm256_or_si256(shifted, carry);
}

static inline __m256i ssw_shift_left_2_bytes_avx2(__m256i value) {
	const __m256i shifted = _mm256_slli_si256(value, 2);
	const __m256i carry =
		_mm256_srli_si256(_mm256_permute2x128_si256(value, value, 0x08), 14);
	return _mm256_or_si256(shifted, carry);
}

static inline uint8_t ssw_hmax_epu8_avx2(__m256i value) {
	__m128i reduced =
		_mm_max_epu8(_mm256_castsi256_si128(value), _mm256_extracti128_si256(value, 1));
	reduced = _mm_max_epu8(reduced, _mm_srli_si128(reduced, 8));
	reduced = _mm_max_epu8(reduced, _mm_srli_si128(reduced, 4));
	reduced = _mm_max_epu8(reduced, _mm_srli_si128(reduced, 2));
	reduced = _mm_max_epu8(reduced, _mm_srli_si128(reduced, 1));
	return static_cast<uint8_t>(_mm_extract_epi16(reduced, 0) & 0x00ff);
}

static inline uint16_t ssw_hmax_epi16_avx2(__m256i value) {
	__m128i reduced =
		_mm_max_epi16(_mm256_castsi256_si128(value), _mm256_extracti128_si256(value, 1));
	reduced = _mm_max_epi16(reduced, _mm_srli_si128(reduced, 8));
	reduced = _mm_max_epi16(reduced, _mm_srli_si128(reduced, 4));
	reduced = _mm_max_epi16(reduced, _mm_srli_si128(reduced, 2));
	return static_cast<uint16_t>(_mm_extract_epi16(reduced, 0));
}
#endif

// ***** begin of sw_sse2_byte_once *****//

/* Striped Smith-Waterman
   Record the highest score of each reference position.
   Return the alignment score and ending position of the best alignment, 2nd best alignment, etc.
   Gap begin and gap extension are different.
   wight_match > 0, all other weights < 0.
   The returned positions are 0-based.
 */

 /* 2021-09-29 12:04:07: slightly modify this function, to return
  * a two-dimension array recording score and reference position.
  *
  *
  *
 */

 // ***** begin of allocating and freeing 2D array *****//
 //int **allocateMatrix(int dim1, int dim2)
 //{
 //    int i, j;
 //    int **matrix;
 //    matrix = malloc(sizeof(int *) * dim1);
 //     
 //    for(i = 0; i < dim1; i++) 
 //    {
 //        matrix[i] = malloc(sizeof(int*) * dim2);
 //    }
 // 
 //    for(i = 0; i < dim1; i++)
 //    {
 //        for(j = 0; j < dim2; j++)
 //        {
 //            matrix[i][j] = 0; // initialize.
 //        }
 //    }
 //    return matrix;
 //}//

 //// free matrix. 
 //void freeMatrix(int dim1, int **matrix)
 //{
 //	int i = 0;
 //	for(i = 0; i < dim1; i++)
 //	{
 //		free(matrix[i]);
 //	}
 //	free(matrix);
 //}
 // ***** end of allocating and freeing 2D array *****//


uint8_t * sw_sse2_byte_once(const int8_t* ref,
	int8_t ref_dir,	// 0: forward ref; 1: reverse ref
	int32_t refLen,
	int32_t readLen,
	const uint8_t weight_gapO, /* will be used as - */
	const uint8_t weight_gapE, /* will be used as - */
	const __m128i* vProfile,
	uint8_t terminate,	/* the best alignment score: used to terminate
						  the matrix calculation when locating the
						  alignment beginning point. If this score
						  is set to 0, it will not be used */
	uint8_t bias,  /* Shift 0 point to a positive value. */
	int32_t maskLen) {

	// Put the largest number of the 16 numbers in vm into m.
#define max16(m, vm) (vm) = _mm_max_epu8((vm), _mm_srli_si128((vm), 8)); \
					  (vm) = _mm_max_epu8((vm), _mm_srli_si128((vm), 4)); \
					  (vm) = _mm_max_epu8((vm), _mm_srli_si128((vm), 2)); \
					  (vm) = _mm_max_epu8((vm), _mm_srli_si128((vm), 1)); \
					  (m) = _mm_extract_epi16((vm), 0)

	uint8_t max = 0;		                     /* the max alignment score */
	int32_t end_read = readLen - 1;
	int32_t end_ref = -1; /* 0_based best alignment ending point; Initialized as isn't aligned -1. */
	int32_t segLen = (readLen + 15) / 16; /* number of segment */

	/* array to record the largest score of each reference position */
	uint8_t* maxColumn = (uint8_t*)calloc(refLen, 1);

	/* array to record the alignment read ending position of the largest score of each reference position */
	int32_t* end_read_column = (int32_t*)calloc(refLen, sizeof(int32_t));

	/* Define 16 byte 0 vector. */
	__m128i vZero = _mm_set1_epi32(0);

	__m128i* pvHStore = (__m128i*) calloc(segLen, sizeof(__m128i));
	__m128i* pvHLoad = (__m128i*) calloc(segLen, sizeof(__m128i));
	__m128i* pvE = (__m128i*) calloc(segLen, sizeof(__m128i));
	__m128i* pvHmax = (__m128i*) calloc(segLen, sizeof(__m128i));

	int32_t i, j, k;
	/* 16 byte insertion begin vector */
	__m128i vGapO = _mm_set1_epi8(weight_gapO);

	/* 16 byte insertion extension vector */
	__m128i vGapE = _mm_set1_epi8(weight_gapE);

	/* 16 byte bias vector */
	__m128i vBias = _mm_set1_epi8(bias);

	__m128i vMaxScore = vZero; /* Trace the highest score of the whole SW matrix. */
	__m128i vMaxMark = vZero; /* Trace the highest score till the previous column. */
	__m128i vTemp;
	int32_t edge, begin = 0, end = refLen, step = 1;

	/* outer loop to process the reference sequence */
	if (ref_dir == 1) {
		begin = refLen - 1;
		end = -1;
		step = -1;
	}
	for (i = begin; LIKELY(i != end); i += step) {
		int32_t cmp;
		__m128i e, vF = vZero, vMaxColumn = vZero; /* Initialize F value to 0.
							   Any errors to vH values will be corrected in the Lazy_F loop.
							 */

		__m128i vH = pvHStore[segLen - 1];
		vH = _mm_slli_si128(vH, 1); /* Shift the 128-bit value in vH left by 1 byte. */
		const __m128i* vP = vProfile + ref[i] * segLen; /* Right part of the vProfile */

		/* Swap the 2 H buffers. */
		__m128i* pv = pvHLoad;
		pvHLoad = pvHStore;
		pvHStore = pv;

		/* inner loop to process the query sequence */
		for (j = 0; LIKELY(j < segLen); ++j) {
			vH = _mm_adds_epu8(vH, _mm_load_si128(vP + j));
			vH = _mm_subs_epu8(vH, vBias); /* vH will be always > 0 */

			/* Get max from vH, vE and vF. */
			e = _mm_load_si128(pvE + j);
			vH = _mm_max_epu8(vH, e);
			vH = _mm_max_epu8(vH, vF);
			vMaxColumn = _mm_max_epu8(vMaxColumn, vH);

			/* Save vH values. */
			_mm_store_si128(pvHStore + j, vH);

			/* Update vE value. */
			vH = _mm_subs_epu8(vH, vGapO); /* saturation arithmetic, result >= 0 */
			e = _mm_subs_epu8(e, vGapE);
			e = _mm_max_epu8(e, vH);
			_mm_store_si128(pvE + j, e);

			/* Update vF value. */
			vF = _mm_subs_epu8(vF, vGapE);
			vF = _mm_max_epu8(vF, vH);

			/* Load the next vH. */
			vH = _mm_load_si128(pvHLoad + j);
		}

		/* Lazy_F loop: has been revised to disallow adjecent insertion and then deletion, so don't update E(i, j), learn from SWPS3 */
		for (k = 0; LIKELY(k < 16); ++k) {
			vF = _mm_slli_si128(vF, 1);
			for (j = 0; LIKELY(j < segLen); ++j) {
				vH = _mm_load_si128(pvHStore + j);
				vH = _mm_max_epu8(vH, vF);
				vMaxColumn = _mm_max_epu8(vMaxColumn, vH);	// newly added line
				_mm_store_si128(pvHStore + j, vH);
				vH = _mm_subs_epu8(vH, vGapO);
				vF = _mm_subs_epu8(vF, vGapE);
				if (UNLIKELY(!_mm_movemask_epi8(_mm_cmpgt_epi8(vF, vH)))) goto end;
			}
		}

	end:

		vMaxScore = _mm_max_epu8(vMaxScore, vMaxColumn);
		vTemp = _mm_cmpeq_epi8(vMaxMark, vMaxScore);
		cmp = _mm_movemask_epi8(vTemp);
		if (cmp != 0xffff) {
			uint8_t temp;
			vMaxMark = vMaxScore;
			max16(temp, vMaxScore);
			vMaxScore = vMaxMark;

			if (LIKELY(temp > max)) {
				max = temp;
				if (max + bias >= 255) break;	//overflow
				end_ref = i;

				/* Store the column with the highest alignment score in order to trace the alignment ending position on read. */
				for (j = 0; LIKELY(j < segLen); ++j) pvHmax[j] = pvHStore[j];
			}
		}

		/* Record the max score of current column. */
		max16(maxColumn[i], vMaxColumn);
		if (maxColumn[i] == terminate) break;
	}

	/* Trace the alignment ending position on read. */
	uint8_t *t = (uint8_t*)pvHmax;
	int32_t column_len = segLen * 16;
	for (i = 0; LIKELY(i < column_len); ++i, ++t) {
		int32_t temp;
		//if(*t > max * 0.8)
		//{
		//	fprintf(stderr, "%d is score %d is position %d is max (read)\n", *t,  
		//		i / 16 + i % 16 * segLen, max); // DEBUG.			
		//}

		if (*t == max) {
			temp = i / 16 + i % 16 * segLen;
			if (temp < end_read) end_read = temp;
		}
	}

	free(pvHmax);
	free(pvE);
	free(pvHLoad);
	free(pvHStore);

	/* Find the most possible 2nd best alignment. */
	alignment_end* bests = (alignment_end*)calloc(2, sizeof(alignment_end));
	bests[0].score = max + bias >= 255 ? 255 : max;
	bests[0].ref = end_ref;
	bests[0].read = end_read;

	bests[1].score = 0;
	bests[1].ref = 0;
	bests[1].read = 0;
	// 2021-09-28 11:24:36: DEBUG: to check if all scores can be reported.
	int threshold = 117;
	edge = (end_ref - maskLen) > 0 ? (end_ref - maskLen) : 0;
	for (i = 0; i < edge; i++) {
		if (maxColumn[i] > bests[1].score) {
			bests[1].score = maxColumn[i];
			bests[1].ref = i;
		}
	}
	edge = (end_ref + maskLen) > refLen ? refLen : (end_ref + maskLen);
	for (i = edge + 1; i < refLen; i++) {
		if (maxColumn[i] > bests[1].score) {
			bests[1].score = maxColumn[i];
			bests[1].ref = i;
		}
	}
	// output all score which is larger than threshold.
	// 2021-09-29 15:42:27: slightly modify the return value, now return the 
	// matrix instead of return the bests.
//	int **scoreMatrix;
//	scoreMatrix = allocateMatrix(refLen, 2);
//	for(i = 0; i < refLen; i++)
//	{
////		scoreMatrix[i][0] = (int)maxColumn[i];
////		scoreMatrix[i][1] = (int)i;
//		if(maxColumn[i] > threshold)
//		{
//			fprintf(stderr, "%d is score %d is ref\n", maxColumn[i], i);
//		}
//	}
//	free(maxColumn);
	free(end_read_column);
	return maxColumn;
	//return bests;
}
// ***** end of sw_sse2_byte_once *****//



/* Striped Smith-Waterman
   Record the highest score of each reference position.
   Return the alignment score and ending position of the best alignment, 2nd best alignment, etc.
   Gap begin and gap extension are different.
   wight_match > 0, all other weights < 0.
   The returned positions are 0-based.
 */
static alignment_end* sw_sse2_byte(const int8_t* ref,
	int8_t ref_dir,	// 0: forward ref; 1: reverse ref
	int32_t refLen,
	int32_t readLen,
	const uint8_t weight_gapO, /* will be used as - */
	const uint8_t weight_gapE, /* will be used as - */
	const __m128i* vProfile,
	uint8_t terminate,	/* the best alignment score: used to terminate
						  the matrix calculation when locating the
						  alignment beginning point. If this score
						  is set to 0, it will not be used */
	uint8_t bias,  /* Shift 0 point to a positive value. */
	int32_t maskLen) {

	// Put the largest number of the 16 numbers in vm into m.
#define max16(m, vm) (vm) = _mm_max_epu8((vm), _mm_srli_si128((vm), 8)); \
					  (vm) = _mm_max_epu8((vm), _mm_srli_si128((vm), 4)); \
					  (vm) = _mm_max_epu8((vm), _mm_srli_si128((vm), 2)); \
					  (vm) = _mm_max_epu8((vm), _mm_srli_si128((vm), 1)); \
					  (m) = _mm_extract_epi16((vm), 0)

	uint8_t max = 0;		                     /* the max alignment score */
	int32_t end_read = readLen - 1;
	int32_t end_ref = -1; /* 0_based best alignment ending point; Initialized as isn't aligned -1. */
	int32_t segLen = (readLen + 15) / 16; /* number of segment */

	/* array to record the largest score of each reference position */
	uint8_t* maxColumn = (uint8_t*)calloc(refLen, 1);

	/* array to record the alignment read ending position of the largest score of each reference position */
	int32_t* end_read_column = (int32_t*)calloc(refLen, sizeof(int32_t));

	/* Define 16 byte 0 vector. */
	__m128i vZero = _mm_set1_epi32(0);

	__m128i* pvHStore = (__m128i*) calloc(segLen, sizeof(__m128i));
	__m128i* pvHLoad = (__m128i*) calloc(segLen, sizeof(__m128i));
	__m128i* pvE = (__m128i*) calloc(segLen, sizeof(__m128i));
	__m128i* pvHmax = (__m128i*) calloc(segLen, sizeof(__m128i));

	int32_t i, j, k;
	/* 16 byte insertion begin vector */
	__m128i vGapO = _mm_set1_epi8(weight_gapO);

	/* 16 byte insertion extension vector */
	__m128i vGapE = _mm_set1_epi8(weight_gapE);

	/* 16 byte bias vector */
	__m128i vBias = _mm_set1_epi8(bias);

	__m128i vMaxScore = vZero; /* Trace the highest score of the whole SW matrix. */
	__m128i vMaxMark = vZero; /* Trace the highest score till the previous column. */
	__m128i vTemp;
	int32_t edge, begin = 0, end = refLen, step = 1;

	/* outer loop to process the reference sequence */
	if (ref_dir == 1) {
		begin = refLen - 1;
		end = -1;
		step = -1;
	}
	for (i = begin; LIKELY(i != end); i += step) {
		int32_t cmp;
		__m128i e, vF = vZero, vMaxColumn = vZero; /* Initialize F value to 0.
							   Any errors to vH values will be corrected in the Lazy_F loop.
							 */

		__m128i vH = pvHStore[segLen - 1];
		vH = _mm_slli_si128(vH, 1); /* Shift the 128-bit value in vH left by 1 byte. */
		const __m128i* vP = vProfile + ref[i] * segLen; /* Right part of the vProfile */

		/* Swap the 2 H buffers. */
		__m128i* pv = pvHLoad;
		pvHLoad = pvHStore;
		pvHStore = pv;

		/* inner loop to process the query sequence */
		for (j = 0; LIKELY(j < segLen); ++j) {
			vH = _mm_adds_epu8(vH, _mm_load_si128(vP + j));
			vH = _mm_subs_epu8(vH, vBias); /* vH will be always > 0 */

			/* Get max from vH, vE and vF. */
			e = _mm_load_si128(pvE + j);
			vH = _mm_max_epu8(vH, e);
			vH = _mm_max_epu8(vH, vF);
			vMaxColumn = _mm_max_epu8(vMaxColumn, vH);

			/* Save vH values. */
			_mm_store_si128(pvHStore + j, vH);

			/* Update vE value. */
			vH = _mm_subs_epu8(vH, vGapO); /* saturation arithmetic, result >= 0 */
			e = _mm_subs_epu8(e, vGapE);
			e = _mm_max_epu8(e, vH);
			_mm_store_si128(pvE + j, e);

			/* Update vF value. */
			vF = _mm_subs_epu8(vF, vGapE);
			vF = _mm_max_epu8(vF, vH);

			/* Load the next vH. */
			vH = _mm_load_si128(pvHLoad + j);
		}

		/* Lazy_F loop: has been revised to disallow adjecent insertion and then deletion, so don't update E(i, j), learn from SWPS3 */
		for (k = 0; LIKELY(k < 16); ++k) {
			vF = _mm_slli_si128(vF, 1);
			for (j = 0; LIKELY(j < segLen); ++j) {
				vH = _mm_load_si128(pvHStore + j);
				vH = _mm_max_epu8(vH, vF);
				vMaxColumn = _mm_max_epu8(vMaxColumn, vH);	// newly added line
				_mm_store_si128(pvHStore + j, vH);
				vH = _mm_subs_epu8(vH, vGapO);
				vF = _mm_subs_epu8(vF, vGapE);
				if (UNLIKELY(!_mm_movemask_epi8(_mm_cmpgt_epi8(vF, vH)))) goto end;
			}
		}

	end:

		vMaxScore = _mm_max_epu8(vMaxScore, vMaxColumn);
		vTemp = _mm_cmpeq_epi8(vMaxMark, vMaxScore);
		cmp = _mm_movemask_epi8(vTemp);
		if (cmp != 0xffff) {
			uint8_t temp;
			vMaxMark = vMaxScore;
			max16(temp, vMaxScore);
			vMaxScore = vMaxMark;

			if (LIKELY(temp > max)) {
				max = temp;
				if (max + bias >= 255) break;	//overflow
				end_ref = i;

				/* Store the column with the highest alignment score in order to trace the alignment ending position on read. */
				for (j = 0; LIKELY(j < segLen); ++j) pvHmax[j] = pvHStore[j];
			}
		}

		/* Record the max score of current column. */
		max16(maxColumn[i], vMaxColumn);
		if (maxColumn[i] == terminate) break;
	}

	/* Trace the alignment ending position on read. */
	uint8_t *t = (uint8_t*)pvHmax;
	int32_t column_len = segLen * 16;
	for (i = 0; LIKELY(i < column_len); ++i, ++t) {
		int32_t temp;
		if (*t == max) {
			temp = i / 16 + i % 16 * segLen;
			if (temp < end_read) end_read = temp;
		}
	}

	free(pvHmax);
	free(pvE);
	free(pvHLoad);
	free(pvHStore);

	/* Find the most possible 2nd best alignment. */
	alignment_end* bests = (alignment_end*)calloc(2, sizeof(alignment_end));
	bests[0].score = max + bias >= 255 ? 255 : max;
	bests[0].ref = end_ref;
	bests[0].read = end_read;

	bests[1].score = 0;
	bests[1].ref = 0;
	bests[1].read = 0;
	// 2021-09-28 11:24:36: DEBUG: to check if all scores can be reported.
	int threshold = 117;
	edge = (end_ref - maskLen) > 0 ? (end_ref - maskLen) : 0;
	for (i = 0; i < edge; i++) {
		if (maxColumn[i] > bests[1].score) {
			bests[1].score = maxColumn[i];
			bests[1].ref = i;
		}
	}
	edge = (end_ref + maskLen) > refLen ? refLen : (end_ref + maskLen);
	for (i = edge + 1; i < refLen; i++) {
		if (maxColumn[i] > bests[1].score) {
			bests[1].score = maxColumn[i];
			bests[1].ref = i;
		}
	}
	// output all score which is larger than threshold.
	//for(i = 0; i < refLen; i++)
	//{
	//	if(maxColumn[i] > threshold)
	//	{
	//		fprintf(stderr, "%d is score %d is ref\n", maxColumn[i], i);
	//	}
	//}
	fasim_ssw_oracle::record_alignment_dp_pass_u8(
		maxColumn, refLen, ref_dir, "byte8", bests[0].score, bests[0].ref,
		bests[0].read, bests[1].score, bests[1].ref);
	free(maxColumn);
	free(end_read_column);
	return bests;
}

#if defined(__AVX2__)
static alignment_end* sw_avx2_byte(const int8_t* ref,
	int8_t ref_dir,
	int32_t refLen,
	int32_t readLen,
	const uint8_t weight_gapO,
	const uint8_t weight_gapE,
	const __m256i* vProfile,
	uint8_t terminate,
	uint8_t bias,
	int32_t maskLen) {

	uint8_t max = 0;
	int32_t end_read = readLen - 1;
	int32_t end_ref = -1;
	int32_t segLen = (readLen + 31) / 32;

	uint8_t* maxColumn = (uint8_t*)calloc(refLen, 1);
	int32_t* end_read_column = (int32_t*)calloc(refLen, sizeof(int32_t));

	__m256i vZero = _mm256_setzero_si256();
	__m256i* pvHStore = (__m256i*)ssw_aligned_calloc(segLen, sizeof(__m256i), 32);
	__m256i* pvHLoad = (__m256i*)ssw_aligned_calloc(segLen, sizeof(__m256i), 32);
	__m256i* pvE = (__m256i*)ssw_aligned_calloc(segLen, sizeof(__m256i), 32);
	__m256i* pvHmax = (__m256i*)ssw_aligned_calloc(segLen, sizeof(__m256i), 32);
	if (maxColumn == NULL || end_read_column == NULL ||
	    pvHStore == NULL || pvHLoad == NULL || pvE == NULL || pvHmax == NULL) {
		free(maxColumn);
		free(end_read_column);
		free(pvHStore);
		free(pvHLoad);
		free(pvE);
		free(pvHmax);
		fprintf(stderr, "Failed to allocate AVX2 SSW byte workspace.\n");
		exit(1);
	}

	int32_t i, j, k;
	__m256i vGapO = _mm256_set1_epi8(weight_gapO);
	__m256i vGapE = _mm256_set1_epi8(weight_gapE);
	__m256i vBias = _mm256_set1_epi8(bias);
	__m256i vMaxScore = vZero;
	__m256i vMaxMark = vZero;
	__m256i vTemp;
	int32_t edge, begin = 0, end = refLen, step = 1;

	if (ref_dir == 1) {
		begin = refLen - 1;
		end = -1;
		step = -1;
	}
	for (i = begin; LIKELY(i != end); i += step) {
		int32_t cmp;
		__m256i e, vF = vZero, vMaxColumn = vZero;

		__m256i vH = pvHStore[segLen - 1];
		vH = ssw_shift_left_1_byte_avx2(vH);
		const __m256i* vP = vProfile + ref[i] * segLen;

		__m256i* pv = pvHLoad;
		pvHLoad = pvHStore;
		pvHStore = pv;

		for (j = 0; LIKELY(j < segLen); ++j) {
			vH = _mm256_adds_epu8(vH, _mm256_load_si256(vP + j));
			vH = _mm256_subs_epu8(vH, vBias);

			e = _mm256_load_si256(pvE + j);
			vH = _mm256_max_epu8(vH, e);
			vH = _mm256_max_epu8(vH, vF);
			vMaxColumn = _mm256_max_epu8(vMaxColumn, vH);
			_mm256_store_si256(pvHStore + j, vH);

			vH = _mm256_subs_epu8(vH, vGapO);
			e = _mm256_subs_epu8(e, vGapE);
			e = _mm256_max_epu8(e, vH);
			_mm256_store_si256(pvE + j, e);

			vF = _mm256_subs_epu8(vF, vGapE);
			vF = _mm256_max_epu8(vF, vH);

			vH = _mm256_load_si256(pvHLoad + j);
		}

		for (k = 0; LIKELY(k < 32); ++k) {
			vF = ssw_shift_left_1_byte_avx2(vF);
			for (j = 0; LIKELY(j < segLen); ++j) {
				vH = _mm256_load_si256(pvHStore + j);
				vH = _mm256_max_epu8(vH, vF);
				vMaxColumn = _mm256_max_epu8(vMaxColumn, vH);
				_mm256_store_si256(pvHStore + j, vH);
				vH = _mm256_subs_epu8(vH, vGapO);
				vF = _mm256_subs_epu8(vF, vGapE);
				if (UNLIKELY(!_mm256_movemask_epi8(_mm256_cmpgt_epi8(vF, vH)))) goto end;
			}
		}

	end:
		vMaxScore = _mm256_max_epu8(vMaxScore, vMaxColumn);
		vTemp = _mm256_cmpeq_epi8(vMaxMark, vMaxScore);
		cmp = _mm256_movemask_epi8(vTemp);
		if (cmp != -1) {
			uint8_t temp;
			vMaxMark = vMaxScore;
			temp = ssw_hmax_epu8_avx2(vMaxScore);
			vMaxScore = vMaxMark;

			if (LIKELY(temp > max)) {
				max = temp;
				if (max + bias >= 255) break;
				end_ref = i;
				for (j = 0; LIKELY(j < segLen); ++j) pvHmax[j] = pvHStore[j];
			}
		}

		maxColumn[i] = ssw_hmax_epu8_avx2(vMaxColumn);
		if (maxColumn[i] == terminate) break;
	}

	uint8_t *t = (uint8_t*)pvHmax;
	int32_t column_len = segLen * 32;
	for (i = 0; LIKELY(i < column_len); ++i, ++t) {
		int32_t temp;
		if (*t == max) {
			temp = i / 32 + i % 32 * segLen;
			if (temp < end_read) end_read = temp;
		}
	}

	free(pvHmax);
	free(pvE);
	free(pvHLoad);
	free(pvHStore);

	alignment_end* bests = (alignment_end*)calloc(2, sizeof(alignment_end));
	bests[0].score = max + bias >= 255 ? 255 : max;
	bests[0].ref = end_ref;
	bests[0].read = end_read;

	bests[1].score = 0;
	bests[1].ref = 0;
	bests[1].read = 0;
	edge = (end_ref - maskLen) > 0 ? (end_ref - maskLen) : 0;
	for (i = 0; i < edge; i++) {
		if (maxColumn[i] > bests[1].score) {
			bests[1].score = maxColumn[i];
			bests[1].ref = i;
		}
	}
	edge = (end_ref + maskLen) > refLen ? refLen : (end_ref + maskLen);
	for (i = edge + 1; i < refLen; i++) {
		if (maxColumn[i] > bests[1].score) {
			bests[1].score = maxColumn[i];
			bests[1].ref = i;
		}
	}
	fasim_ssw_oracle::record_alignment_dp_pass_u8(
		maxColumn, refLen, ref_dir, "byte8_avx2", bests[0].score, bests[0].ref,
		bests[0].read, bests[1].score, bests[1].ref);
	free(maxColumn);
	free(end_read_column);
	return bests;
}
#endif

static __m128i* qP_word(const int8_t* read_num,
	const int8_t* mat,
	const int32_t readLen,
	const int32_t n) {

	int32_t segLen = (readLen + 7) / 8;
	__m128i* vProfile = (__m128i*)malloc(n * segLen * sizeof(__m128i));
	int16_t* t = (int16_t*)vProfile;
	int32_t nt, i, j;
	int32_t segNum;

	/* Generate query profile rearrange query sequence & calculate the weight of match/mismatch */
	for (nt = 0; LIKELY(nt < n); nt++) {
		for (i = 0; i < segLen; i++) {
			j = i;
			for (segNum = 0; LIKELY(segNum < 8); segNum++) {
				*t++ = j >= readLen ? 0 : mat[nt * n + read_num[j]];
				j += segLen;
			}
		}
	}
	return vProfile;
}

#if defined(__AVX2__)
static __m256i* qP_word_avx2(const int8_t* read_num,
	const int8_t* mat,
	const int32_t readLen,
	const int32_t n) {

	int32_t segLen = (readLen + 15) / 16;
	__m256i* vProfile = (__m256i*)ssw_aligned_calloc(
		static_cast<size_t>(n) * static_cast<size_t>(segLen),
		sizeof(__m256i),
		32);
	if (vProfile == NULL) return NULL;
	int16_t* t = (int16_t*)vProfile;
	int32_t nt, i, j;
	int32_t segNum;

	for (nt = 0; LIKELY(nt < n); nt++) {
		for (i = 0; i < segLen; i++) {
			j = i;
			for (segNum = 0; LIKELY(segNum < 16); segNum++) {
				*t++ = j >= readLen ? 0 : mat[nt * n + read_num[j]];
				j += segLen;
			}
		}
	}
	return vProfile;
}
#endif

uint16_t * sw_sse2_word_once(const int8_t* ref,
	int8_t ref_dir,	// 0: forward ref; 1: reverse ref
	int32_t refLen,
	int32_t readLen,
	const uint8_t weight_gapO, /* will be used as - */
	const uint8_t weight_gapE, /* will be used as - */
	const __m128i* vProfile,
	uint16_t terminate,
	int32_t maskLen) {

#define max8(m, vm) (vm) = _mm_max_epi16((vm), _mm_srli_si128((vm), 8)); \
					(vm) = _mm_max_epi16((vm), _mm_srli_si128((vm), 4)); \
					(vm) = _mm_max_epi16((vm), _mm_srli_si128((vm), 2)); \
					(m) = _mm_extract_epi16((vm), 0)

	uint16_t max = 0;		                     /* the max alignment score */
	int32_t end_read = readLen - 1;
	int32_t end_ref = 0; /* 1_based best alignment ending point; Initialized as isn't aligned - 0. */
	int32_t segLen = (readLen + 7) / 8; /* number of segment */

	/* array to record the largest score of each reference position */
	uint16_t* maxColumn = (uint16_t*)calloc(refLen, 2);

	/* array to record the alignment read ending position of the largest score of each reference position */
	int32_t* end_read_column = (int32_t*)calloc(refLen, sizeof(int32_t));

	/* Define 16 byte 0 vector. */
	__m128i vZero = _mm_set1_epi32(0);

	__m128i* pvHStore = (__m128i*) calloc(segLen, sizeof(__m128i));
	__m128i* pvHLoad = (__m128i*) calloc(segLen, sizeof(__m128i));
	__m128i* pvE = (__m128i*) calloc(segLen, sizeof(__m128i));
	__m128i* pvHmax = (__m128i*) calloc(segLen, sizeof(__m128i));

	int32_t i, j, k;
	/* 16 byte insertion begin vector */
	__m128i vGapO = _mm_set1_epi16(weight_gapO);

	/* 16 byte insertion extension vector */
	__m128i vGapE = _mm_set1_epi16(weight_gapE);

	__m128i vMaxScore = vZero; /* Trace the highest score of the whole SW matrix. */
	__m128i vMaxMark = vZero; /* Trace the highest score till the previous column. */
	__m128i vTemp;
	int32_t edge, begin = 0, end = refLen, step = 1;

	/* outer loop to process the reference sequence */
	if (ref_dir == 1) {
		begin = refLen - 1;
		end = -1;
		step = -1;
	}
	for (i = begin; LIKELY(i != end); i += step) {
		int32_t cmp;
		__m128i e, vF = vZero; /* Initialize F value to 0.
							   Any errors to vH values will be corrected in the Lazy_F loop.
							 */
		__m128i vH = pvHStore[segLen - 1];
		vH = _mm_slli_si128(vH, 2); /* Shift the 128-bit value in vH left by 2 byte. */

		/* Swap the 2 H buffers. */
		__m128i* pv = pvHLoad;

		__m128i vMaxColumn = vZero; /* vMaxColumn is used to record the max values of column i. */

		const __m128i* vP = vProfile + ref[i] * segLen; /* Right part of the vProfile */
		pvHLoad = pvHStore;
		pvHStore = pv;

		/* inner loop to process the query sequence */
		for (j = 0; LIKELY(j < segLen); j++) {
			vH = _mm_adds_epi16(vH, _mm_load_si128(vP + j));

			/* Get max from vH, vE and vF. */
			e = _mm_load_si128(pvE + j);
			vH = _mm_max_epi16(vH, e);
			vH = _mm_max_epi16(vH, vF);
			vMaxColumn = _mm_max_epi16(vMaxColumn, vH);

			/* Save vH values. */
			_mm_store_si128(pvHStore + j, vH);

			/* Update vE value. */
			vH = _mm_subs_epu16(vH, vGapO); /* saturation arithmetic, result >= 0 */
			e = _mm_subs_epu16(e, vGapE);
			e = _mm_max_epi16(e, vH);
			_mm_store_si128(pvE + j, e);

			/* Update vF value. */
			vF = _mm_subs_epu16(vF, vGapE);
			vF = _mm_max_epi16(vF, vH);

			/* Load the next vH. */
			vH = _mm_load_si128(pvHLoad + j);
		}

		/* Lazy_F loop: has been revised to disallow adjecent insertion and then deletion, so don't update E(i, j), learn from SWPS3 */
		for (k = 0; LIKELY(k < 8); ++k) {
			vF = _mm_slli_si128(vF, 2);
			for (j = 0; LIKELY(j < segLen); ++j) {
				vH = _mm_load_si128(pvHStore + j);
				vH = _mm_max_epi16(vH, vF);
				vMaxColumn = _mm_max_epi16(vMaxColumn, vH); //newly added line
				_mm_store_si128(pvHStore + j, vH);
				vH = _mm_subs_epu16(vH, vGapO);
				vF = _mm_subs_epu16(vF, vGapE);
				if (UNLIKELY(!_mm_movemask_epi8(_mm_cmpgt_epi16(vF, vH)))) goto end;
			}
		}

	end:
		vMaxScore = _mm_max_epi16(vMaxScore, vMaxColumn);
		vTemp = _mm_cmpeq_epi16(vMaxMark, vMaxScore);
		cmp = _mm_movemask_epi8(vTemp);
		if (cmp != 0xffff) {
			uint16_t temp;
			vMaxMark = vMaxScore;
			max8(temp, vMaxScore);
			vMaxScore = vMaxMark;

			if (LIKELY(temp > max)) {
				max = temp;
				end_ref = i;
				for (j = 0; LIKELY(j < segLen); ++j) pvHmax[j] = pvHStore[j];
			}
		}

		/* Record the max score of current column. */
		max8(maxColumn[i], vMaxColumn);
		if (maxColumn[i] == terminate) break;
	}

	/* Trace the alignment ending position on read. */
	uint16_t *t = (uint16_t*)pvHmax;
	int32_t column_len = segLen * 8;
	for (i = 0; LIKELY(i < column_len); ++i, ++t) {
		int32_t temp;
		if (*t == max) {
			temp = i / 8 + i % 8 * segLen;
			if (temp < end_read) end_read = temp;
		}
	}

	free(pvHmax);
	free(pvE);
	free(pvHLoad);
	free(pvHStore);

	/* Find the most possible 2nd best alignment. */
	alignment_end* bests = (alignment_end*)calloc(2, sizeof(alignment_end));
	bests[0].score = max;
	bests[0].ref = end_ref;
	bests[0].read = end_read;

	bests[1].score = 0;
	bests[1].ref = 0;
	bests[1].read = 0;

	edge = (end_ref - maskLen) > 0 ? (end_ref - maskLen) : 0;
	for (i = 0; i < edge; i++) {
		if (maxColumn[i] > bests[1].score) {
			bests[1].score = maxColumn[i];
			bests[1].ref = i;
		}
	}
	edge = (end_ref + maskLen) > refLen ? refLen : (end_ref + maskLen);
	for (i = edge; i < refLen; i++) {
		if (maxColumn[i] > bests[1].score) {
			bests[1].score = maxColumn[i];
			bests[1].ref = i;
		}
	}
	// output all score which is larger than threshold.
	// 2021-09-29 15:42:27: slightly modify the return value, now return the 
	// matrix instead of return the bests.
	//int **scoreMatrix;
	//scoreMatrix = allocateMatrix(refLen, 2);
	//for(i = 0; i < refLen; i++)
	//{
	//	scoreMatrix[i][0] = (int)maxColumn[i];
	//	scoreMatrix[i][1] = (int)i;
		//if(maxColumn[i] > threshold)
		//{
		//	fprintf(stderr, "%d is score %d is ref\n", maxColumn[i], i);
		//}
	//}
	//free(maxColumn);
	free(end_read_column);
	//return bests;
	return maxColumn;
}




static alignment_end* sw_sse2_word(const int8_t* ref,
	int8_t ref_dir,	// 0: forward ref; 1: reverse ref
	int32_t refLen,
	int32_t readLen,
	const uint8_t weight_gapO, /* will be used as - */
	const uint8_t weight_gapE, /* will be used as - */
	const __m128i* vProfile,
	uint16_t terminate,
	int32_t maskLen) {

#define max8(m, vm) (vm) = _mm_max_epi16((vm), _mm_srli_si128((vm), 8)); \
					(vm) = _mm_max_epi16((vm), _mm_srli_si128((vm), 4)); \
					(vm) = _mm_max_epi16((vm), _mm_srli_si128((vm), 2)); \
					(m) = _mm_extract_epi16((vm), 0)

	uint16_t max = 0;		                     /* the max alignment score */
	int32_t end_read = readLen - 1;
	int32_t end_ref = 0; /* 1_based best alignment ending point; Initialized as isn't aligned - 0. */
	int32_t segLen = (readLen + 7) / 8; /* number of segment */

	/* array to record the largest score of each reference position */
	uint16_t* maxColumn = (uint16_t*)calloc(refLen, 2);

	/* array to record the alignment read ending position of the largest score of each reference position */
	int32_t* end_read_column = (int32_t*)calloc(refLen, sizeof(int32_t));

	/* Define 16 byte 0 vector. */
	__m128i vZero = _mm_set1_epi32(0);

	__m128i* pvHStore = (__m128i*) calloc(segLen, sizeof(__m128i));
	__m128i* pvHLoad = (__m128i*) calloc(segLen, sizeof(__m128i));
	__m128i* pvE = (__m128i*) calloc(segLen, sizeof(__m128i));
	__m128i* pvHmax = (__m128i*) calloc(segLen, sizeof(__m128i));

	int32_t i, j, k;
	/* 16 byte insertion begin vector */
	__m128i vGapO = _mm_set1_epi16(weight_gapO);

	/* 16 byte insertion extension vector */
	__m128i vGapE = _mm_set1_epi16(weight_gapE);

	__m128i vMaxScore = vZero; /* Trace the highest score of the whole SW matrix. */
	__m128i vMaxMark = vZero; /* Trace the highest score till the previous column. */
	__m128i vTemp;
	int32_t edge, begin = 0, end = refLen, step = 1;

	/* outer loop to process the reference sequence */
	if (ref_dir == 1) {
		begin = refLen - 1;
		end = -1;
		step = -1;
	}
	for (i = begin; LIKELY(i != end); i += step) {
		int32_t cmp;
		__m128i e, vF = vZero; /* Initialize F value to 0.
							   Any errors to vH values will be corrected in the Lazy_F loop.
							 */
		__m128i vH = pvHStore[segLen - 1];
		vH = _mm_slli_si128(vH, 2); /* Shift the 128-bit value in vH left by 2 byte. */

		/* Swap the 2 H buffers. */
		__m128i* pv = pvHLoad;

		__m128i vMaxColumn = vZero; /* vMaxColumn is used to record the max values of column i. */

		const __m128i* vP = vProfile + ref[i] * segLen; /* Right part of the vProfile */
		pvHLoad = pvHStore;
		pvHStore = pv;

		/* inner loop to process the query sequence */
		for (j = 0; LIKELY(j < segLen); j++) {
			vH = _mm_adds_epi16(vH, _mm_load_si128(vP + j));

			/* Get max from vH, vE and vF. */
			e = _mm_load_si128(pvE + j);
			vH = _mm_max_epi16(vH, e);
			vH = _mm_max_epi16(vH, vF);
			vMaxColumn = _mm_max_epi16(vMaxColumn, vH);

			/* Save vH values. */
			_mm_store_si128(pvHStore + j, vH);

			/* Update vE value. */
			vH = _mm_subs_epu16(vH, vGapO); /* saturation arithmetic, result >= 0 */
			e = _mm_subs_epu16(e, vGapE);
			e = _mm_max_epi16(e, vH);
			_mm_store_si128(pvE + j, e);

			/* Update vF value. */
			vF = _mm_subs_epu16(vF, vGapE);
			vF = _mm_max_epi16(vF, vH);

			/* Load the next vH. */
			vH = _mm_load_si128(pvHLoad + j);
		}

		/* Lazy_F loop: has been revised to disallow adjecent insertion and then deletion, so don't update E(i, j), learn from SWPS3 */
		for (k = 0; LIKELY(k < 8); ++k) {
			vF = _mm_slli_si128(vF, 2);
			for (j = 0; LIKELY(j < segLen); ++j) {
				vH = _mm_load_si128(pvHStore + j);
				vH = _mm_max_epi16(vH, vF);
				vMaxColumn = _mm_max_epi16(vMaxColumn, vH); //newly added line
				_mm_store_si128(pvHStore + j, vH);
				vH = _mm_subs_epu16(vH, vGapO);
				vF = _mm_subs_epu16(vF, vGapE);
				if (UNLIKELY(!_mm_movemask_epi8(_mm_cmpgt_epi16(vF, vH)))) goto end;
			}
		}

	end:
		vMaxScore = _mm_max_epi16(vMaxScore, vMaxColumn);
		vTemp = _mm_cmpeq_epi16(vMaxMark, vMaxScore);
		cmp = _mm_movemask_epi8(vTemp);
		if (cmp != 0xffff) {
			uint16_t temp;
			vMaxMark = vMaxScore;
			max8(temp, vMaxScore);
			vMaxScore = vMaxMark;

			if (LIKELY(temp > max)) {
				max = temp;
				end_ref = i;
				for (j = 0; LIKELY(j < segLen); ++j) pvHmax[j] = pvHStore[j];
			}
		}

		/* Record the max score of current column. */
		max8(maxColumn[i], vMaxColumn);
		if (maxColumn[i] == terminate) break;
	}

	/* Trace the alignment ending position on read. */
	uint16_t *t = (uint16_t*)pvHmax;
	int32_t column_len = segLen * 8;
	for (i = 0; LIKELY(i < column_len); ++i, ++t) {
		int32_t temp;
		if (*t == max) {
			temp = i / 8 + i % 8 * segLen;
			if (temp < end_read) end_read = temp;
		}
	}

	free(pvHmax);
	free(pvE);
	free(pvHLoad);
	free(pvHStore);

	/* Find the most possible 2nd best alignment. */
	alignment_end* bests = (alignment_end*)calloc(2, sizeof(alignment_end));
	bests[0].score = max;
	bests[0].ref = end_ref;
	bests[0].read = end_read;

	bests[1].score = 0;
	bests[1].ref = 0;
	bests[1].read = 0;

	edge = (end_ref - maskLen) > 0 ? (end_ref - maskLen) : 0;
	for (i = 0; i < edge; i++) {
		if (maxColumn[i] > bests[1].score) {
			bests[1].score = maxColumn[i];
			bests[1].ref = i;
		}
	}
	edge = (end_ref + maskLen) > refLen ? refLen : (end_ref + maskLen);
	for (i = edge; i < refLen; i++) {
		if (maxColumn[i] > bests[1].score) {
			bests[1].score = maxColumn[i];
			bests[1].ref = i;
		}
	}

	fasim_ssw_oracle::record_alignment_dp_pass_u16(
		maxColumn, refLen, ref_dir, "word16", bests[0].score, bests[0].ref,
		bests[0].read, bests[1].score, bests[1].ref);
	free(maxColumn);
	free(end_read_column);
	return bests;
}

#if defined(__AVX2__)
static alignment_end* sw_avx2_word(const int8_t* ref,
	int8_t ref_dir,
	int32_t refLen,
	int32_t readLen,
	const uint8_t weight_gapO,
	const uint8_t weight_gapE,
	const __m256i* vProfile,
	uint16_t terminate,
	int32_t maskLen) {

	uint16_t max = 0;
	int32_t end_read = readLen - 1;
	int32_t end_ref = 0;
	int32_t segLen = (readLen + 15) / 16;

	uint16_t* maxColumn = (uint16_t*)calloc(refLen, 2);
	int32_t* end_read_column = (int32_t*)calloc(refLen, sizeof(int32_t));

	__m256i vZero = _mm256_setzero_si256();
	__m256i* pvHStore = (__m256i*)ssw_aligned_calloc(segLen, sizeof(__m256i), 32);
	__m256i* pvHLoad = (__m256i*)ssw_aligned_calloc(segLen, sizeof(__m256i), 32);
	__m256i* pvE = (__m256i*)ssw_aligned_calloc(segLen, sizeof(__m256i), 32);
	__m256i* pvHmax = (__m256i*)ssw_aligned_calloc(segLen, sizeof(__m256i), 32);
	if (maxColumn == NULL || end_read_column == NULL ||
	    pvHStore == NULL || pvHLoad == NULL || pvE == NULL || pvHmax == NULL) {
		free(maxColumn);
		free(end_read_column);
		free(pvHStore);
		free(pvHLoad);
		free(pvE);
		free(pvHmax);
		fprintf(stderr, "Failed to allocate AVX2 SSW word workspace.\n");
		exit(1);
	}

	int32_t i, j, k;
	__m256i vGapO = _mm256_set1_epi16(weight_gapO);
	__m256i vGapE = _mm256_set1_epi16(weight_gapE);
	__m256i vMaxScore = vZero;
	__m256i vMaxMark = vZero;
	__m256i vTemp;
	int32_t edge, begin = 0, end = refLen, step = 1;

	if (ref_dir == 1) {
		begin = refLen - 1;
		end = -1;
		step = -1;
	}
	for (i = begin; LIKELY(i != end); i += step) {
		int32_t cmp;
		__m256i e, vF = vZero;
		__m256i vH = pvHStore[segLen - 1];
		vH = ssw_shift_left_2_bytes_avx2(vH);

		__m256i* pv = pvHLoad;
		__m256i vMaxColumn = vZero;
		const __m256i* vP = vProfile + ref[i] * segLen;
		pvHLoad = pvHStore;
		pvHStore = pv;

		for (j = 0; LIKELY(j < segLen); j++) {
			vH = _mm256_adds_epi16(vH, _mm256_load_si256(vP + j));

			e = _mm256_load_si256(pvE + j);
			vH = _mm256_max_epi16(vH, e);
			vH = _mm256_max_epi16(vH, vF);
			vMaxColumn = _mm256_max_epi16(vMaxColumn, vH);
			_mm256_store_si256(pvHStore + j, vH);

			vH = _mm256_subs_epu16(vH, vGapO);
			e = _mm256_subs_epu16(e, vGapE);
			e = _mm256_max_epi16(e, vH);
			_mm256_store_si256(pvE + j, e);

			vF = _mm256_subs_epu16(vF, vGapE);
			vF = _mm256_max_epi16(vF, vH);

			vH = _mm256_load_si256(pvHLoad + j);
		}

		for (k = 0; LIKELY(k < 16); ++k) {
			vF = ssw_shift_left_2_bytes_avx2(vF);
			for (j = 0; LIKELY(j < segLen); ++j) {
				vH = _mm256_load_si256(pvHStore + j);
				vH = _mm256_max_epi16(vH, vF);
				vMaxColumn = _mm256_max_epi16(vMaxColumn, vH);
				_mm256_store_si256(pvHStore + j, vH);
				vH = _mm256_subs_epu16(vH, vGapO);
				vF = _mm256_subs_epu16(vF, vGapE);
				if (UNLIKELY(!_mm256_movemask_epi8(_mm256_cmpgt_epi16(vF, vH)))) goto end;
			}
		}

	end:
		vMaxScore = _mm256_max_epi16(vMaxScore, vMaxColumn);
		vTemp = _mm256_cmpeq_epi16(vMaxMark, vMaxScore);
		cmp = _mm256_movemask_epi8(vTemp);
		if (cmp != -1) {
			uint16_t temp;
			vMaxMark = vMaxScore;
			temp = ssw_hmax_epi16_avx2(vMaxScore);
			vMaxScore = vMaxMark;

			if (LIKELY(temp > max)) {
				max = temp;
				end_ref = i;
				for (j = 0; LIKELY(j < segLen); ++j) pvHmax[j] = pvHStore[j];
			}
		}

		maxColumn[i] = ssw_hmax_epi16_avx2(vMaxColumn);
		if (maxColumn[i] == terminate) break;
	}

	uint16_t *t = (uint16_t*)pvHmax;
	int32_t column_len = segLen * 16;
	for (i = 0; LIKELY(i < column_len); ++i, ++t) {
		int32_t temp;
		if (*t == max) {
			temp = i / 16 + i % 16 * segLen;
			if (temp < end_read) end_read = temp;
		}
	}

	free(pvHmax);
	free(pvE);
	free(pvHLoad);
	free(pvHStore);

	alignment_end* bests = (alignment_end*)calloc(2, sizeof(alignment_end));
	bests[0].score = max;
	bests[0].ref = end_ref;
	bests[0].read = end_read;

	bests[1].score = 0;
	bests[1].ref = 0;
	bests[1].read = 0;

	edge = (end_ref - maskLen) > 0 ? (end_ref - maskLen) : 0;
	for (i = 0; i < edge; i++) {
		if (maxColumn[i] > bests[1].score) {
			bests[1].score = maxColumn[i];
			bests[1].ref = i;
		}
	}
	edge = (end_ref + maskLen) > refLen ? refLen : (end_ref + maskLen);
	for (i = edge; i < refLen; i++) {
		if (maxColumn[i] > bests[1].score) {
			bests[1].score = maxColumn[i];
			bests[1].ref = i;
		}
	}

	fasim_ssw_oracle::record_alignment_dp_pass_u16(
		maxColumn, refLen, ref_dir, "word16_avx2", bests[0].score, bests[0].ref,
		bests[0].read, bests[1].score, bests[1].ref);
	free(maxColumn);
	free(end_read_column);
	return bests;
}
#endif

static bool ssw_checked_multiply_size(size_t left, size_t right, size_t* product) {
	if (product == NULL || (left != 0 && right > SIZE_MAX / left)) return false;
	*product = left * right;
	return true;
}

template <typename T>
static bool ssw_resize_array(T** buffer, size_t count) {
	if (buffer == NULL) return false;
	size_t bytes = 0;
	if (!ssw_checked_multiply_size(count, sizeof(T), &bytes) || bytes == 0) {
		return false;
	}
	void* resized = realloc(*buffer, bytes);
	if (resized == NULL) return false;
	*buffer = static_cast<T*>(resized);
	return true;
}

static void ssw_destroy_cigar(cigar* path) {
	if (path == NULL) return;
	free(path->seq);
	free(path);
}

static bool ssw_append_cigar(uint32_t** values,
	size_t* length,
	size_t* capacity,
	uint32_t value) {
	if (values == NULL || length == NULL || capacity == NULL) return false;
	if (*length == *capacity) {
		if (*capacity > SIZE_MAX / 2) return false;
		const size_t next_capacity = *capacity == 0 ? 16 : *capacity * 2;
		if (!ssw_resize_array(values, next_capacity)) {
			return false;
		}
		*capacity = next_capacity;
	}
	(*values)[(*length)++] = value;
	return true;
}

static cigar* banded_sw(const int8_t* ref,
	const int8_t* read,
	int32_t refLen,
	int32_t readLen,
	int32_t score,
	const int32_t weight_gapO,  /* will be used as - */
	const int32_t weight_gapE,  /* will be used as - */
	int32_t band_width,
	const int8_t* mat,	/* pointer to the weight matrix */
	int32_t n,
	const char** failure_reason,
	int32_t* final_band_width) {

	if (failure_reason != NULL) *failure_reason = "unknown";
	if (final_band_width != NULL) *final_band_width = 0;
	if (ref == NULL || read == NULL || mat == NULL || refLen <= 0 ||
		readLen <= 0 || score <= 0 || weight_gapO < 0 || weight_gapE < 0 ||
		band_width <= 0 || n <= 0) {
		if (failure_reason != NULL) *failure_reason = "invalid_input";
		return NULL;
	}
	for (int32_t index = 0; index < refLen; ++index) {
		if (ref[index] < 0 || ref[index] >= n) {
			if (failure_reason != NULL) *failure_reason = "invalid_reference_symbol";
			return NULL;
		}
	}
	for (int32_t index = 0; index < readLen; ++index) {
		if (read[index] < 0 || read[index] >= n) {
			if (failure_reason != NULL) *failure_reason = "invalid_read_symbol";
			return NULL;
		}
	}

	uint32_t* c = NULL;
	uint32_t* c1 = NULL;
	cigar* result = NULL;
	size_t cigar_length = 0;
	size_t cigar_capacity = 0;
	int32_t i, j, e, f, temp1, temp2, max = 0;
	char op, prev_op;
	int32_t width = 0, width_d = 0, direction_width = 0;
	int32_t* h_b = NULL;
	int32_t* e_b = NULL;
	int32_t* h_c = NULL;
	int8_t* direction = NULL;
	int8_t* direction_line = NULL;
	size_t state_capacity = 0;
	size_t direction_capacity = 0;
	const int32_t neg_inf = INT32_MIN / 2;
	const int32_t full_band = refLen > readLen ? refLen : readLen;
	if (band_width > full_band) band_width = full_band;

	for (;;) {
		const int64_t width64 = static_cast<int64_t>(band_width) * 2 + 3;
		const int64_t width_d64 = static_cast<int64_t>(band_width) * 2 + 1;
		if (width64 > INT32_MAX || width_d64 > INT32_MAX) {
			if (failure_reason != NULL) *failure_reason = "band_width_overflow";
			goto fail;
		}
		width = static_cast<int32_t>(width64);
		width_d = static_cast<int32_t>(width_d64);
		// A very wide query band still has only refLen addressable columns.
		direction_width = width_d < refLen ? width_d : refLen;
		if (static_cast<size_t>(width) > state_capacity) {
			const size_t next_capacity = static_cast<size_t>(width);
			if (!ssw_resize_array(&h_b, next_capacity) ||
				!ssw_resize_array(&e_b, next_capacity) ||
				!ssw_resize_array(&h_c, next_capacity)) {
				if (failure_reason != NULL) *failure_reason = "state_allocation_failed";
				goto fail;
			}
			state_capacity = next_capacity;
		}
		size_t direction_elements = 0;
		if (!ssw_checked_multiply_size(static_cast<size_t>(direction_width),
				static_cast<size_t>(readLen), &direction_elements) ||
			!ssw_checked_multiply_size(direction_elements, 3, &direction_elements)) {
			if (failure_reason != NULL) *failure_reason = "direction_size_overflow";
			goto fail;
		}
		if (direction_elements > direction_capacity) {
			if (!ssw_resize_array(&direction, direction_elements)) {
				if (failure_reason != NULL) *failure_reason = "direction_allocation_failed";
				goto fail;
			}
			direction_capacity = direction_elements;
		}

		max = 0;
		direction_line = direction;
		for (j = 1; LIKELY(j < width - 1); j++) h_b[j] = 0;
		for (i = 0; LIKELY(i < readLen); i++) {
			int32_t beg = 0, end = refLen - 1, u = 0, edge;
			j = i - band_width;	beg = beg > j ? beg : j; // band start
			j = i + band_width; end = end < j ? end : j; // band end
			edge = end + 1 < width - 1 ? end + 1 : width - 1;
			f = neg_inf;
			h_b[0] = h_b[edge] = h_c[0] = 0;
			e_b[0] = e_b[edge] = neg_inf;
			direction_line = direction +
				static_cast<size_t>(direction_width) * static_cast<size_t>(i) * 3;

			for (j = beg; LIKELY(j <= end); j++) {
				int32_t b, e1, f1, d, de, df, dh;
				set_u(u, band_width, i, j);	set_u(e, band_width, i - 1, j);
				set_u(b, band_width, i, j - 1); set_u(d, band_width, i - 1, j - 1);
				set_d(de, band_width, i, j, 0);
				set_d(df, band_width, i, j, 1);
				set_d(dh, band_width, i, j, 2);

				temp1 = i == 0 ? -weight_gapO : h_b[e] - weight_gapO;
				temp2 = i == 0 ? neg_inf : e_b[e] - weight_gapE;
				e_b[u] = temp1 > temp2 ? temp1 : temp2;
				direction_line[de] = temp1 > temp2 ? 3 : 2;

				temp1 = h_c[b] - weight_gapO;
				temp2 = f - weight_gapE;
				f = temp1 > temp2 ? temp1 : temp2;
				direction_line[df] = temp1 > temp2 ? 5 : 4;

				e1 = e_b[u] > 0 ? e_b[u] : 0;
				f1 = f > 0 ? f : 0;
				temp1 = e1 > f1 ? e1 : f1;
				temp2 = h_b[d] + mat[ref[j] * n + read[i]];
				h_c[u] = temp1 > temp2 ? temp1 : temp2;

				if (h_c[u] > max) max = h_c[u];
				if (temp1 <= temp2) direction_line[dh] = 1;
				else direction_line[dh] = e1 > f1 ? direction_line[de] : direction_line[df];
//				cout<<"j:"<<j<<"\tscore:\t"<<h_c[u]<<"\t";
			}
			for (j = 1; j <= u; j++) h_b[j] = h_c[j];
		}
		fasim_ssw_oracle::record_band_iteration(band_width, max, score);
		// The fork's min(forward, reverse) score can be unreachable in this
		// scalar recurrence. Full band is therefore the hard terminal bound.
		if (max >= score || band_width >= full_band) break;
		const int64_t doubled = static_cast<int64_t>(band_width) * 2;
		band_width = doubled >= full_band ? full_band : static_cast<int32_t>(doubled);
	}
	if (final_band_width != NULL) *final_band_width = band_width;
	// trace back
	i = readLen - 1;
	j = refLen - 1;
	e = 0;	// Count the number of M, D or I.
	op = prev_op = 'M';
	temp2 = 2;	// h
	while (LIKELY(i > 0 && j > 0)) {
		const int32_t band_start = i > band_width ? i - band_width : 0;
		const int64_t cell = static_cast<int64_t>(j) - band_start;
		const int64_t direction_index =
			(static_cast<int64_t>(i) * direction_width + cell) * 3 + temp2;
		const int64_t direction_limit =
			static_cast<int64_t>(direction_width) * readLen * 3;
		if (cell < 0 || cell >= direction_width || temp2 < 0 || temp2 > 2 ||
			direction_index < 0 || direction_index >= direction_limit) {
			if (failure_reason != NULL) *failure_reason = "traceback_index_out_of_bounds";
			goto fail;
		}
		switch (direction[direction_index]) {
		case 1:
			--i;
			--j;
			temp2 = 2;
			op = 'M';
			break;
		case 2:
			--i;
			temp2 = 0;	// e
			op = 'I';
			break;
		case 3:
			--i;
			temp2 = 2;
			op = 'I';
			break;
		case 4:
			--j;
			temp2 = 1;
			op = 'D';
			break;
		case 5:
			--j;
			temp2 = 2;
			op = 'D';
			break;
		default:
			if (failure_reason != NULL) *failure_reason = "invalid_traceback_direction";
			goto fail;
		}
		if (op == prev_op) ++e;
		else {
			if (!ssw_append_cigar(&c, &cigar_length, &cigar_capacity,
					to_cigar_int(e, prev_op))) {
				if (failure_reason != NULL) *failure_reason = "cigar_allocation_failed";
				goto fail;
			}
			prev_op = op;
			e = 1;
		}
	}
	if (op == 'M') {
		if (!ssw_append_cigar(&c, &cigar_length, &cigar_capacity,
				to_cigar_int(e + 1, op))) {
			if (failure_reason != NULL) *failure_reason = "cigar_allocation_failed";
			goto fail;
		}
	}
	else {
		if (!ssw_append_cigar(&c, &cigar_length, &cigar_capacity,
				to_cigar_int(e, op)) ||
			!ssw_append_cigar(&c, &cigar_length, &cigar_capacity,
				to_cigar_int(1, 'M'))) {
			if (failure_reason != NULL) *failure_reason = "cigar_allocation_failed";
			goto fail;
		}
	}

	// reverse cigar
	if (cigar_length > static_cast<size_t>(INT32_MAX)) {
		if (failure_reason != NULL) *failure_reason = "cigar_length_overflow";
		goto fail;
	}
	if (!ssw_resize_array(&c1, cigar_length)) {
		if (failure_reason != NULL) *failure_reason = "cigar_allocation_failed";
		goto fail;
	}
	for (size_t index = 0; index < cigar_length; ++index) {
		c1[index] = c[cigar_length - index - 1];
	}
	result = static_cast<cigar*>(malloc(sizeof(cigar)));
	if (result == NULL) {
		free(c1);
		if (failure_reason != NULL) *failure_reason = "cigar_result_allocation_failed";
		goto fail;
	}
	result->seq = c1;
	result->length = static_cast<int32_t>(cigar_length);
	// A reverse endpoint can precede the true local start. Return the
	// unconsumed prefix so the public coordinates can be tightened exactly.
	result->ref_begin_offset = j;
	result->read_begin_offset = i;

	free(direction);
	free(h_c);
	free(e_b);
	free(h_b);
	free(c);
	if (failure_reason != NULL) *failure_reason = "none";
	return result;

fail:
	free(direction);
	free(h_c);
	free(e_b);
	free(h_b);
	free(c);
	return NULL;
}

static bool cigar_alignment_score(const cigar* path,
	const int8_t* ref,
	int32_t refLen,
	const int8_t* read,
	int32_t readLen,
	const int8_t* mat,
	int32_t n,
	const uint32_t weight_gapO,
	const uint32_t weight_gapE,
	int32_t* alignment_score) {
	if (path == NULL || path->seq == NULL || path->length <= 0 || ref == NULL ||
		read == NULL || mat == NULL || n <= 0 || alignment_score == NULL) {
		return false;
	}
	if (path->ref_begin_offset < 0 || path->ref_begin_offset >= refLen ||
		path->read_begin_offset < 0 || path->read_begin_offset >= readLen) {
		return false;
	}
	ref += path->ref_begin_offset;
	read += path->read_begin_offset;
	refLen -= path->ref_begin_offset;
	readLen -= path->read_begin_offset;
	int64_t score = 0;
	int32_t ref_pos = 0;
	int32_t read_pos = 0;
	for (int32_t index = 0; index < path->length; ++index) {
		const uint32_t length = cigar_int_to_len(path->seq[index]);
		const char op = cigar_int_to_op(path->seq[index]);
		if (length == 0 && op != 'M') return false;
		if (op == 'M') {
			if (length > static_cast<uint32_t>(refLen - ref_pos) ||
				length > static_cast<uint32_t>(readLen - read_pos)) {
				return false;
			}
			for (uint32_t offset = 0; offset < length; ++offset) {
				score += mat[ref[ref_pos] * n + read[read_pos]];
				++ref_pos;
				++read_pos;
			}
		}
		else if (op == 'I') {
			if (length > static_cast<uint32_t>(readLen - read_pos)) return false;
			score -= static_cast<int64_t>(weight_gapO) +
				static_cast<int64_t>(length - 1) * weight_gapE;
			read_pos += static_cast<int32_t>(length);
		}
		else if (op == 'D') {
			if (length > static_cast<uint32_t>(refLen - ref_pos)) return false;
			score -= static_cast<int64_t>(weight_gapO) +
				static_cast<int64_t>(length - 1) * weight_gapE;
			ref_pos += static_cast<int32_t>(length);
		}
		else {
			return false;
		}
	}
	if (score < INT32_MIN || score > INT32_MAX) return false;
	if (ref_pos != refLen || read_pos != readLen) return false;
	*alignment_score = static_cast<int32_t>(score);
	return true;
}

static cigar* exact_banded_sw(const int8_t* ref,
	const int8_t* read,
	int32_t refLen,
	int32_t readLen,
	int32_t score,
	const int32_t weight_gapO,
	const int32_t weight_gapE,
	int32_t band_width,
	const int8_t* mat,
	int32_t n,
	const char** failure_reason) {
	const int32_t full_band = refLen > readLen ? refLen : readLen;
	int32_t attempted_band = 0;
	const char* local_reason = "unknown";
	cigar* path = banded_sw(ref, read, refLen, readLen, score, weight_gapO,
		weight_gapE, band_width, mat, n, &local_reason, &attempted_band);
	int32_t observed_score = 0;
	// This fork reports min(forward, reverse). A structurally exact CIGAR can
	// therefore score differently; coordinates and full sequence consumption
	// remain the fail-closed contract.
	if (path != NULL &&
		cigar_alignment_score(path, ref, refLen, read, readLen, mat, n,
			weight_gapO, weight_gapE, &observed_score)) {
		if (failure_reason != NULL) *failure_reason = "none";
		return path;
	}
	if (path != NULL) local_reason = "cigar_contract_invalid";
	ssw_destroy_cigar(path);
	if (attempted_band < full_band) {
		path = banded_sw(ref, read, refLen, readLen, score, weight_gapO,
			weight_gapE, full_band, mat, n, &local_reason,
			&attempted_band);
		observed_score = 0;
		if (path != NULL &&
			cigar_alignment_score(path, ref, refLen, read, readLen, mat, n,
				weight_gapO, weight_gapE, &observed_score)) {
			if (failure_reason != NULL) *failure_reason = "none";
			return path;
		}
		if (path != NULL) local_reason = "cigar_contract_invalid";
		ssw_destroy_cigar(path);
	}
	if (failure_reason != NULL) {
		*failure_reason = local_reason;
	}
	return NULL;
}

#ifdef FASIM_SSW_BANDED_TRACEBACK_TEST_API
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
	uint32_t* only_cigar) {
	const char* failure_reason = "unknown";
	cigar* path = exact_banded_sw(ref, read, refLen, readLen, score,
		weight_gapO, weight_gapE, band_width, mat, n, &failure_reason);
	if (path == NULL || path->length != 1 || ref_begin_offset == NULL ||
		read_begin_offset == NULL || only_cigar == NULL) {
		ssw_destroy_cigar(path);
		return false;
	}
	*ref_begin_offset = path->ref_begin_offset;
	*read_begin_offset = path->read_begin_offset;
	*only_cigar = path->seq[0];
	ssw_destroy_cigar(path);
	return true;
}
#endif

static void ssw_fail_closed_traceback(const char* reason,
	int32_t refLen,
	int32_t readLen,
	int32_t score,
	int32_t band_width) {
	fprintf(stderr,
		"FATAL: exact SSW traceback failed: reason=%s ref_len=%d read_len=%d "
		"score=%d initial_band=%d\n",
		reason == NULL ? "unknown" : reason, refLen, readLen, score, band_width);
	fflush(stderr);
	abort();
}

static int8_t* seq_reverse(const int8_t* seq, int32_t end)	/* end is 0-based alignment ending position */
{
	int8_t* reverse = (int8_t*)calloc(end + 1, sizeof(int8_t));
	int32_t start = 0;
	while (LIKELY(start <= end)) {
		reverse[start] = seq[end];
		reverse[end] = seq[start];
		++start;
		--end;
	}
	return reverse;
}

s_profile* ssw_init(const int8_t* read, const int32_t readLen, const int8_t* mat, const int32_t n, const int8_t score_size) {
	s_profile* p = (s_profile*)calloc(1, sizeof(struct _profile));
	p->profile_byte = 0;
	p->profile_word = 0;
#if defined(__AVX2__)
	p->profile_byte_avx2 = 0;
	p->profile_word_avx2 = 0;
#endif
	p->bias = 0;

	if (score_size == 0 || score_size == 2) {
		/* Find the bias to use in the substitution matrix */
		int32_t bias = 0, i;
		for (i = 0; i < n*n; i++) if (mat[i] < bias) bias = mat[i];
		bias = abs(bias);

		p->bias = bias;
		p->profile_byte = qP_byte(read, mat, readLen, n, bias);
#if defined(__AVX2__)
		if (ssw_avx2_forward_enabled_runtime()) {
			p->profile_byte_avx2 = qP_byte_avx2(read, mat, readLen, n, bias);
		}
#endif
	}
	if (score_size == 1 || score_size == 2) {
		p->profile_word = qP_word(read, mat, readLen, n);
#if defined(__AVX2__)
		if (ssw_avx2_forward_enabled_runtime()) {
			p->profile_word_avx2 = qP_word_avx2(read, mat, readLen, n);
		}
#endif
	}
	p->read = read;
	p->mat = mat;
	p->readLen = readLen;
	p->n = n;
	return p;
}

void init_destroy(s_profile* p) {
	free(p->profile_byte);
	free(p->profile_word);
#if defined(__AVX2__)
	free(p->profile_byte_avx2);
	free(p->profile_word_avx2);
#endif
	free(p);
}

/*
 * 2021-09-29 15:47:52: This is a special pre-align function.
 * Use this function to get all ref end we need (score > threshold)
 * Then we can trace back these alignments based on these information.
 *
 */
int * ssw_pre_align(const s_profile* prof,
	const int8_t* ref,
	int32_t refLen,
	const uint8_t weight_gapO,
	const uint8_t weight_gapE,
	const uint8_t flag,	//  (from high to low) bit 5: return the best alignment beginning position; 6: if (ref_end1 - ref_begin1 <= filterd) && (read_end1 - read_begin1 <= filterd), return cigar; 7: if max score >= filters, return cigar; 8: always return cigar; if 6 & 7 are both setted, only return cigar when both filter fulfilled
	const uint16_t filters,
	const int32_t filterd,
	const int32_t maskLen,
	int threshold) {

	alignment_end* bests = 0, *bests_reverse = 0;
	__m128i* vP = 0;
	int32_t word = 0, band_width = 0, readLen = prof->readLen;
	int8_t* read_reverse = 0;
	int *scoreMatrix;
	uint8_t* byteColumn = (uint8_t*)calloc(refLen, 1);;
	uint16_t *wordColumn;
	byteColumn = NULL;
	wordColumn = NULL;
	cigar* path;
	s_align* r = (s_align*)calloc(1, sizeof(s_align));
	r->ref_begin1 = -1;
	r->read_begin1 = -1;
	r->cigar = 0;
	r->cigarLen = 0;
	if (maskLen < 15) {
		fprintf(stderr, "When maskLen < 15, the function ssw_align doesn't return 2nd best alignment information.\n");
	}

	// Find the alignment scores and ending positions
	if (prof->profile_byte) {
		byteColumn = sw_sse2_byte_once(ref, 0, refLen, readLen, weight_gapO, weight_gapE, prof->profile_byte, -1, prof->bias, maskLen);
		fasim_ssw_oracle::record_prealign_columns_u8(byteColumn, refLen, "byte8");
		int maxscore = 0;
		for (int i = 0; i < refLen; i++)
		{
			if ((int)byteColumn[i] > maxscore)
				maxscore = (int)byteColumn[i];
		}
		if (prof->profile_word && maxscore>=255) {//&& bests[0].score == 255
			//freeMatrix(scoreMatrix);
			byteColumn = NULL;
			wordColumn = sw_sse2_word_once(ref, 0, refLen, readLen, weight_gapO, weight_gapE, prof->profile_word, -1, maskLen);
			fasim_ssw_oracle::record_prealign_columns_u16(wordColumn, refLen, "word16");
			word = 1;
		} //else if (bests[0].score == 255) {
			//fprintf(stderr, "Please set 2 to the score_size parameter of the function ssw_init, otherwise the alignment results will be incorrect.\n");
			//free(r);
			//return NULL;
		//}
	}
	else if (prof->profile_word) {
		wordColumn = sw_sse2_word_once(ref, 0, refLen, readLen, weight_gapO, weight_gapE, prof->profile_word, -1, maskLen);
		fasim_ssw_oracle::record_prealign_columns_u16(wordColumn, refLen, "word16");
		word = 1;
	}
	else {
		fprintf(stderr, "Please call the function ssw_init before ssw_align.\n");
		//free(r);
		return NULL;
	}
	// convert byteColumn or wordColumn to int array.
	int i = 0;
	scoreMatrix = (int*)calloc(refLen, sizeof(int));
	if (byteColumn)
	{
		for (i = 0; i < refLen; i++)
		{
			scoreMatrix[i] = (int)byteColumn[i];
		}
		// free byteColumn.
		byteColumn =NULL;
	}
	else if (wordColumn)
	{
		for (i = 0; i < refLen; i++)
		{
			scoreMatrix[i] = (int)wordColumn[i];
		}
		// free wordColumn
		wordColumn =NULL;
	}

	fasim_ssw_oracle::set_prealign_final_numeric_path(word == 0 ? "byte8" : "word16");
	return scoreMatrix; // should be OK???
	//r->score1 = bests[0].score;
	//r->ref_end1 = bests[0].ref;
	//r->read_end1 = bests[0].read;
	//if (maskLen >= 1) {
	//	r->score2 = bests[1].score;
	//	r->ref_end2 = bests[1].ref;
	//} else {
	//	r->score2 = 0;
	//	r->ref_end2 = -1;
	//}
	//free(bests);
	//if (flag == 0 || (flag == 2 && r->score1 < filters)) goto end;

	// Find the beginning position of the best alignment.
	//read_reverse = seq_reverse(prof->read, r->read_end1);
	//if (word == 0) {
	//	vP = qP_byte(read_reverse, prof->mat, r->read_end1 + 1, prof->n, prof->bias);
	//	bests_reverse = sw_sse2_byte(ref, 1, r->ref_end1 + 1, r->read_end1 + 1, weight_gapO, weight_gapE, vP, r->score1, prof->bias, maskLen);
	//} else {
	//	vP = qP_word(read_reverse, prof->mat, r->read_end1 + 1, prof->n);
	//	bests_reverse = sw_sse2_word(ref, 1, r->ref_end1 + 1, r->read_end1 + 1, weight_gapO, weight_gapE, vP, r->score1, maskLen);
	//}
	//free(vP);
	//free(read_reverse);
	//r->ref_begin1 = bests_reverse[0].ref;
	//r->read_begin1 = r->read_end1 - bests_reverse[0].read;
	//free(bests_reverse);
	//if ((7&flag) == 0 || ((2&flag) != 0 && r->score1 < filters) || ((4&flag) != 0 && (r->ref_end1 - r->ref_begin1 > filterd || r->read_end1 - r->read_begin1 > filterd))) goto end;

	// Generate cigar.
	//refLen = r->ref_end1 - r->ref_begin1 + 1;
	//readLen = r->read_end1 - r->read_begin1 + 1;
	//band_width = abs(refLen - readLen) + 1;
	//path = banded_sw(ref + r->ref_begin1, prof->read + r->read_begin1, refLen, readLen, r->score1, weight_gapO, weight_gapE, band_width, prof->mat, prof->n);
	//if (path == 0) {
	//	free(r);
	//	r = NULL;
	//}
	//else {
	//	r->cigar = path->seq;
	//	r->cigarLen = path->length;
	//	free(path);
	//}

//end:
//	return r;
}



// 2021-09-22 16:38:46: SIM can report sub-optimal alignment whose 
// startPos only differ 2. So now I want to make maskLen 2 and see if this helps.
// 2021-09-22 16:42:42: After modifying maskLen to 2, the sub-optimal alignment 
// is too redundant, modify maskLen to 15, though we may lose some sub-optimal 
// alignment.
s_align* ssw_align(const s_profile* prof,
	const int8_t* ref,
	int32_t refLen,
	const uint8_t weight_gapO,
	const uint8_t weight_gapE,
	const uint8_t flag,	//  (from high to low) bit 5: return the best alignment beginning position; 6: if (ref_end1 - ref_begin1 <= filterd) && (read_end1 - read_begin1 <= filterd), return cigar; 7: if max score >= filters, return cigar; 8: always return cigar; if 6 & 7 are both setted, only return cigar when both filter fulfilled
	const uint16_t filters,
	const int32_t filterd,
	const int32_t maskLen) {

	alignment_end* bests = 0, *bests_reverse = 0;
	__m128i* vP = 0;
	int32_t word = 0, band_width = 0, readLen = prof->readLen;
	int8_t* read_reverse = 0;
	uint64_t reverse_start = 0;
	uint64_t reverse_endpoint_start = 0;
	uint64_t cigar_start = 0;
	uint64_t banded_sw_start = 0;
	cigar* path;
	const char* traceback_failure = "unknown";
	s_align* r = (s_align*)calloc(1, sizeof(s_align));
	r->ref_begin1 = -1;
	r->read_begin1 = -1;
	r->cigar = 0;
	r->cigarLen = 0;
	const uint8_t collect_internal_stats = ssw_align_internal_stats_enabled();
	if (maskLen < 1) {
		fprintf(stderr, "When maskLen < 15, the function ssw_align doesn't return 2nd best alignment information.\n");
	}

#if defined(__AVX2__)
	const bool useAvx2Forward = ssw_avx2_forward_enabled_runtime();
	const bool useAvx2Reverse = ssw_avx2_reverse_enabled_runtime();
#else
	if (ssw_avx2_requested_runtime()) {
		++g_ssw_avx2_fallback_calls;
	}
#endif

	// Find the alignment scores and ending positions
	if (collect_internal_stats) {
		++g_ssw_align_internal_stats.forward_calls;
	}
	const uint64_t forward_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
	{
		FasimAuthorityProfileScope authority_scope(
			FASIM_AUTHORITY_STAGE_FORWARD_ALIGNMENT);
	if (prof->profile_byte) {
		const uint64_t byte_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
#if defined(__AVX2__)
		if (useAvx2Forward && prof->profile_byte_avx2 != NULL) {
			++g_ssw_avx2_calls;
			++g_ssw_avx2_forward_calls;
			++g_ssw_avx2_byte_calls;
			g_ssw_avx2_active = 1;
			bests = sw_avx2_byte(ref, 0, refLen, readLen, weight_gapO, weight_gapE, prof->profile_byte_avx2, -1, prof->bias, maskLen);
		}
		else
#endif
		{
			bests = sw_sse2_byte(ref, 0, refLen, readLen, weight_gapO, weight_gapE, prof->profile_byte, -1, prof->bias, maskLen);
		}
		ssw_add_elapsed(&g_ssw_align_internal_stats.byte_path_nanoseconds, byte_start);
		if (prof->profile_word && bests[0].score == 255) {
			if (collect_internal_stats) {
				++g_ssw_align_internal_stats.fallback_calls;
			}
			free(bests);
			const uint64_t word_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
#if defined(__AVX2__)
			if (useAvx2Forward && prof->profile_word_avx2 != NULL) {
				++g_ssw_avx2_calls;
				++g_ssw_avx2_forward_calls;
				++g_ssw_avx2_word_calls;
				g_ssw_avx2_active = 1;
				bests = sw_avx2_word(ref, 0, refLen, readLen, weight_gapO, weight_gapE, prof->profile_word_avx2, -1, maskLen);
			}
			else
#endif
			{
				bests = sw_sse2_word(ref, 0, refLen, readLen, weight_gapO, weight_gapE, prof->profile_word, -1, maskLen);
			}
			ssw_add_elapsed(&g_ssw_align_internal_stats.word_path_nanoseconds, word_start);
			word = 1;
		}
		else if (bests[0].score == 255) {
			ssw_add_elapsed(&g_ssw_align_internal_stats.forward_score_end_nanoseconds, forward_start);
			fprintf(stderr, "Please set 2 to the score_size parameter of the function ssw_init, otherwise the alignment results will be incorrect.\n");
			free(r);
			return NULL;
		}
	}
	else if (prof->profile_word) {
		const uint64_t word_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
#if defined(__AVX2__)
		if (useAvx2Forward && prof->profile_word_avx2 != NULL) {
			++g_ssw_avx2_calls;
			++g_ssw_avx2_forward_calls;
			++g_ssw_avx2_word_calls;
			g_ssw_avx2_active = 1;
			bests = sw_avx2_word(ref, 0, refLen, readLen, weight_gapO, weight_gapE, prof->profile_word_avx2, -1, maskLen);
		}
		else
#endif
		{
			bests = sw_sse2_word(ref, 0, refLen, readLen, weight_gapO, weight_gapE, prof->profile_word, -1, maskLen);
		}
		ssw_add_elapsed(&g_ssw_align_internal_stats.word_path_nanoseconds, word_start);
		word = 1;
	}
	else {
		ssw_add_elapsed(&g_ssw_align_internal_stats.forward_score_end_nanoseconds, forward_start);
		fprintf(stderr, "Please call the function ssw_init before ssw_align.\n");
		free(r);
		return NULL;
	}
	ssw_add_elapsed(&g_ssw_align_internal_stats.forward_score_end_nanoseconds, forward_start);
	}
	fasim_ssw_oracle::set_alignment_final_numeric_path(word == 0 ? "byte8" : "word16");
	const uint64_t endpoint_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
	r->score1 = bests[0].score;
	r->ref_end1 = bests[0].ref;
	r->read_end1 = bests[0].read;
	if (maskLen >= 1) {
		r->score2 = bests[1].score;
		r->ref_end2 = bests[1].ref;
	}
	else {
		r->score2 = 0;
		r->ref_end2 = -1;
	}
	ssw_add_elapsed(&g_ssw_align_internal_stats.endpoint_bookkeeping_nanoseconds, endpoint_start);

	if (flag == 0 || (flag == 2 && r->score1 < filters)) {
		free(bests);
		goto end;
	}
	// Preserve the legacy no-alignment sentinel without taking ref - 1 into
	// traceback. The forward-continuation API uses the same representation.
	if (r->score1 == 0 && r->ref_end1 == -1 && r->read_end1 == 0) {
		free(bests);
		r->read_begin1 = 0;
		if ((7 & flag) != 0 && !((2 & flag) != 0 && r->score1 < filters) &&
			!((4 & flag) != 0 && filterd < 0)) {
			r->cigar = (uint32_t*)calloc(1, sizeof(uint32_t));
			if (r->cigar == NULL) ssw_fail_closed_traceback("allocation_failed", 0, 0, 0, 0);
			r->cigar[0] = to_cigar_int(1, 'M');
			r->cigarLen = 1;
		}
		return r;
	}

	// Find the beginning position of the best alignment.
	if (collect_internal_stats) {
		++g_ssw_align_internal_stats.reverse_calls;
	}
	reverse_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
	{
		FasimAuthorityProfileScope authority_scope(
			FASIM_AUTHORITY_STAGE_REVERSE_ALIGNMENT);
	read_reverse = seq_reverse(prof->read, r->read_end1);
	if (word == 0) {
#if defined(__AVX2__)
		__m256i* vPAvx2 = NULL;
#endif
		vP = qP_byte(read_reverse, prof->mat, r->read_end1 + 1, prof->n, prof->bias);
		const uint64_t byte_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
#if defined(__AVX2__)
		if (useAvx2Reverse) {
			vPAvx2 = qP_byte_avx2(read_reverse, prof->mat, r->read_end1 + 1, prof->n, prof->bias);
			if (vPAvx2 != NULL) {
				++g_ssw_avx2_calls;
				++g_ssw_avx2_reverse_calls;
				++g_ssw_avx2_byte_calls;
				g_ssw_avx2_active = 1;
				bests_reverse = sw_avx2_byte(ref, 1, r->ref_end1 + 1, r->read_end1 + 1, weight_gapO, weight_gapE, vPAvx2, r->score1, prof->bias, maskLen);
			}
			else {
				++g_ssw_avx2_fallback_calls;
				bests_reverse = sw_sse2_byte(ref, 1, r->ref_end1 + 1, r->read_end1 + 1, weight_gapO, weight_gapE, vP, r->score1, prof->bias, maskLen);
			}
			free(vPAvx2);
		}
		else
#endif
		{
			bests_reverse = sw_sse2_byte(ref, 1, r->ref_end1 + 1, r->read_end1 + 1, weight_gapO, weight_gapE, vP, r->score1, prof->bias, maskLen);
		}
		ssw_add_elapsed(&g_ssw_align_internal_stats.byte_path_nanoseconds, byte_start);
	}
	else {
#if defined(__AVX2__)
		__m256i* vPAvx2 = NULL;
#endif
		vP = qP_word(read_reverse, prof->mat, r->read_end1 + 1, prof->n);
		const uint64_t word_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
#if defined(__AVX2__)
		if (useAvx2Reverse) {
			vPAvx2 = qP_word_avx2(read_reverse, prof->mat, r->read_end1 + 1, prof->n);
			if (vPAvx2 != NULL) {
				++g_ssw_avx2_calls;
				++g_ssw_avx2_reverse_calls;
				++g_ssw_avx2_word_calls;
				g_ssw_avx2_active = 1;
				bests_reverse = sw_avx2_word(ref, 1, r->ref_end1 + 1, r->read_end1 + 1, weight_gapO, weight_gapE, vPAvx2, r->score1, maskLen);
			}
			else {
				++g_ssw_avx2_fallback_calls;
				bests_reverse = sw_sse2_word(ref, 1, r->ref_end1 + 1, r->read_end1 + 1, weight_gapO, weight_gapE, vP, r->score1, maskLen);
			}
			free(vPAvx2);
		}
		else
#endif
		{
			bests_reverse = sw_sse2_word(ref, 1, r->ref_end1 + 1, r->read_end1 + 1, weight_gapO, weight_gapE, vP, r->score1, maskLen);
		}
		ssw_add_elapsed(&g_ssw_align_internal_stats.word_path_nanoseconds, word_start);
	}
//	cout<<bests_reverse[0].score<<"\t"<<bests[0].score<<"\n";
	reverse_endpoint_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
	r->score1 = bests_reverse[0].score<bests[0].score?bests_reverse[0].score:bests[0].score;
	r->ref_begin1 = bests_reverse[0].ref;
	r->read_begin1 = r->read_end1 - bests_reverse[0].read;
	ssw_add_elapsed(&g_ssw_align_internal_stats.endpoint_bookkeeping_nanoseconds, reverse_endpoint_start);
	free(bests_reverse);
	free(vP);
	free(read_reverse);
	free(bests);
	ssw_add_elapsed(&g_ssw_align_internal_stats.reverse_start_nanoseconds, reverse_start);
	}
	if ((7 & flag) == 0 || ((2 & flag) != 0 && r->score1 < filters) || ((4 & flag) != 0 && (r->ref_end1 - r->ref_begin1 > filterd || r->read_end1 - r->read_begin1 > filterd))) goto end;

	// Generate cigar.
	cigar_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
	refLen = r->ref_end1 - r->ref_begin1 + 1;
	readLen = r->read_end1 - r->read_begin1 + 1;
	band_width = abs(refLen - readLen) + 1;

//	cout<<r->score1<<"\tref_begin1\t"<<r->ref_begin1<<"\tref_end1\t"<<r->ref_end1<<"\tread_begin1\t"<<r->read_begin1<<"\tread_end1\t"<<r->read_end1<<"\t"<<band_width<<"\n";

	if (collect_internal_stats) {
		++g_ssw_align_internal_stats.banded_sw_calls;
	}
	banded_sw_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
	{
		FasimAuthorityProfileScope authority_scope(
			FASIM_AUTHORITY_STAGE_BANDED_TRACEBACK);
		path = exact_banded_sw(ref + r->ref_begin1,
			prof->read + r->read_begin1, refLen, readLen, r->score1,
			weight_gapO, weight_gapE, band_width, prof->mat, prof->n,
			&traceback_failure);
	}
	ssw_add_elapsed(&g_ssw_align_internal_stats.banded_sw_nanoseconds, banded_sw_start);
	if (path == NULL) {
		ssw_fail_closed_traceback(traceback_failure, refLen, readLen,
			r->score1, band_width);
	}
	r->ref_begin1 += path->ref_begin_offset;
	r->read_begin1 += path->read_begin_offset;
	r->cigar = path->seq;
	r->cigarLen = path->length;
	free(path);
	ssw_add_elapsed(&g_ssw_align_internal_stats.cigar_nanoseconds, cigar_start);

end:
	return r;
}

#if defined(FASIM_WITH_SSW_CUDA_FORWARD_HYBRID) || \
	defined(FASIM_WITH_SSW_FORWARD_CONTINUATION)
s_align* ssw_align_from_forward(const s_profile* prof,
	const int8_t* ref,
	int32_t refLen,
	const uint8_t weight_gapO,
	const uint8_t weight_gapE,
	const uint8_t flag,
	const uint16_t filters,
	const int32_t filterd,
	const int32_t maskLen,
	const ssw_forward_endpoint* endpoint) {
	if (prof == NULL || ref == NULL || endpoint == NULL || refLen <= 0 ||
		prof->read == NULL || prof->mat == NULL || prof->readLen <= 0 ||
		endpoint->ref_end2 < -1 || endpoint->ref_end2 >= refLen ||
		(endpoint->numeric_path != SSW_FORWARD_NUMERIC_PATH_BYTE8 &&
		 endpoint->numeric_path != SSW_FORWARD_NUMERIC_PATH_WORD16) ||
		(endpoint->numeric_path == SSW_FORWARD_NUMERIC_PATH_BYTE8 &&
		 prof->profile_byte == NULL) ||
		(endpoint->numeric_path == SSW_FORWARD_NUMERIC_PATH_WORD16 &&
		 prof->profile_word == NULL)) {
		return NULL;
	}
	const bool no_alignment = endpoint->score1 == 0 &&
		endpoint->ref_end1 == -1 && endpoint->read_end1 == 0;
	if ((!no_alignment &&
		 (endpoint->ref_end1 < 0 || endpoint->ref_end1 >= refLen ||
		  endpoint->read_end1 < 0 || endpoint->read_end1 >= prof->readLen)) ||
		(no_alignment && endpoint->score2 != 0)) {
		return NULL;
	}

	s_align* r = (s_align*)calloc(1, sizeof(s_align));
	if (r == NULL) return NULL;
	r->ref_begin1 = -1;
	r->read_begin1 = -1;
	r->score1 = endpoint->score1;
	r->ref_end1 = endpoint->ref_end1;
	r->read_end1 = endpoint->read_end1;
	if (maskLen >= 1) {
		r->score2 = endpoint->score2;
		r->ref_end2 = endpoint->ref_end2;
	}
	else {
		r->score2 = 0;
		r->ref_end2 = -1;
	}

	if (flag == 0 || (flag == 2 && r->score1 < filters)) return r;
	if (no_alignment) {
		r->read_begin1 = 0;
		if ((7 & flag) == 0 ||
			((2 & flag) != 0 && r->score1 < filters) ||
			((4 & flag) != 0 && filterd < 0)) {
			return r;
		}
		r->cigar = (uint32_t*)calloc(1, sizeof(uint32_t));
		if (r->cigar == NULL) {
			free(r);
			return NULL;
		}
		r->cigar[0] = to_cigar_int(1, 'M');
		r->cigarLen = 1;
		return r;
	}

	const uint8_t collect_internal_stats = ssw_align_internal_stats_enabled();
	if (collect_internal_stats) ++g_ssw_align_internal_stats.reverse_calls;
	const uint64_t reverse_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
	alignment_end* bests_reverse = NULL;
	__m128i* vP = NULL;
	int8_t* read_reverse = NULL;

#if defined(__AVX2__)
	const bool useAvx2Reverse = ssw_avx2_reverse_enabled_runtime();
#else
	if (ssw_avx2_requested_runtime()) ++g_ssw_avx2_fallback_calls;
#endif

	{
		FasimAuthorityProfileScope authority_scope(
			FASIM_AUTHORITY_STAGE_REVERSE_ALIGNMENT);
		read_reverse = seq_reverse(prof->read, r->read_end1);
		if (read_reverse == NULL) {
			free(r);
			return NULL;
		}
		if (endpoint->numeric_path == SSW_FORWARD_NUMERIC_PATH_BYTE8) {
#if defined(__AVX2__)
			__m256i* vPAvx2 = NULL;
#endif
			vP = qP_byte(read_reverse, prof->mat, r->read_end1 + 1,
				prof->n, prof->bias);
			const uint64_t byte_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
#if defined(__AVX2__)
			if (useAvx2Reverse) {
				vPAvx2 = qP_byte_avx2(read_reverse, prof->mat,
					r->read_end1 + 1, prof->n, prof->bias);
				if (vPAvx2 != NULL) {
					++g_ssw_avx2_calls;
					++g_ssw_avx2_reverse_calls;
					++g_ssw_avx2_byte_calls;
					g_ssw_avx2_active = 1;
					bests_reverse = sw_avx2_byte(ref, 1, r->ref_end1 + 1,
						r->read_end1 + 1, weight_gapO, weight_gapE,
						vPAvx2, r->score1, prof->bias, maskLen);
				}
				else {
					++g_ssw_avx2_fallback_calls;
					bests_reverse = sw_sse2_byte(ref, 1, r->ref_end1 + 1,
						r->read_end1 + 1, weight_gapO, weight_gapE,
						vP, r->score1, prof->bias, maskLen);
				}
				free(vPAvx2);
			}
			else
#endif
			{
				bests_reverse = sw_sse2_byte(ref, 1, r->ref_end1 + 1,
					r->read_end1 + 1, weight_gapO, weight_gapE, vP,
					r->score1, prof->bias, maskLen);
			}
			ssw_add_elapsed(&g_ssw_align_internal_stats.byte_path_nanoseconds,
				byte_start);
		}
		else {
#if defined(__AVX2__)
			__m256i* vPAvx2 = NULL;
#endif
			vP = qP_word(read_reverse, prof->mat, r->read_end1 + 1, prof->n);
			const uint64_t word_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
#if defined(__AVX2__)
			if (useAvx2Reverse) {
				vPAvx2 = qP_word_avx2(read_reverse, prof->mat,
					r->read_end1 + 1, prof->n);
				if (vPAvx2 != NULL) {
					++g_ssw_avx2_calls;
					++g_ssw_avx2_reverse_calls;
					++g_ssw_avx2_word_calls;
					g_ssw_avx2_active = 1;
					bests_reverse = sw_avx2_word(ref, 1, r->ref_end1 + 1,
						r->read_end1 + 1, weight_gapO, weight_gapE,
						vPAvx2, r->score1, maskLen);
				}
				else {
					++g_ssw_avx2_fallback_calls;
					bests_reverse = sw_sse2_word(ref, 1, r->ref_end1 + 1,
						r->read_end1 + 1, weight_gapO, weight_gapE,
						vP, r->score1, maskLen);
				}
				free(vPAvx2);
			}
			else
#endif
			{
				bests_reverse = sw_sse2_word(ref, 1, r->ref_end1 + 1,
					r->read_end1 + 1, weight_gapO, weight_gapE, vP,
					r->score1, maskLen);
			}
			ssw_add_elapsed(&g_ssw_align_internal_stats.word_path_nanoseconds,
				word_start);
		}
	}

	if (bests_reverse == NULL || vP == NULL) {
		free(bests_reverse);
		free(vP);
		free(read_reverse);
		free(r);
		return NULL;
	}
	const uint64_t endpoint_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
	r->score1 = bests_reverse[0].score < endpoint->score1 ?
		bests_reverse[0].score : endpoint->score1;
	r->ref_begin1 = bests_reverse[0].ref;
	r->read_begin1 = r->read_end1 - bests_reverse[0].read;
	ssw_add_elapsed(&g_ssw_align_internal_stats.endpoint_bookkeeping_nanoseconds,
		endpoint_start);
	free(bests_reverse);
	free(vP);
	free(read_reverse);
	ssw_add_elapsed(&g_ssw_align_internal_stats.reverse_start_nanoseconds,
		reverse_start);

	if ((7 & flag) == 0 ||
		((2 & flag) != 0 && r->score1 < filters) ||
		((4 & flag) != 0 &&
		 (r->ref_end1 - r->ref_begin1 > filterd ||
		  r->read_end1 - r->read_begin1 > filterd))) {
		return r;
	}

	const uint64_t cigar_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
	const int32_t alignment_ref_len = r->ref_end1 - r->ref_begin1 + 1;
	const int32_t alignment_read_len = r->read_end1 - r->read_begin1 + 1;
	const int32_t band_width = abs(alignment_ref_len - alignment_read_len) + 1;
	if (collect_internal_stats) ++g_ssw_align_internal_stats.banded_sw_calls;
	const uint64_t banded_start = collect_internal_stats ? ssw_now_nanoseconds() : 0;
	cigar* path = NULL;
	const char* traceback_failure = "unknown";
	{
		FasimAuthorityProfileScope authority_scope(
			FASIM_AUTHORITY_STAGE_BANDED_TRACEBACK);
		path = exact_banded_sw(ref + r->ref_begin1,
			prof->read + r->read_begin1,
			alignment_ref_len, alignment_read_len, r->score1,
			weight_gapO, weight_gapE, band_width, prof->mat, prof->n,
			&traceback_failure);
	}
	ssw_add_elapsed(&g_ssw_align_internal_stats.banded_sw_nanoseconds,
		banded_start);
	if (path == NULL) {
		ssw_fail_closed_traceback(traceback_failure, alignment_ref_len,
			alignment_read_len, r->score1, band_width);
	}
	r->ref_begin1 += path->ref_begin_offset;
	r->read_begin1 += path->read_begin_offset;
	r->cigar = path->seq;
	r->cigarLen = path->length;
	free(path);
	ssw_add_elapsed(&g_ssw_align_internal_stats.cigar_nanoseconds, cigar_start);
	return r;
}
#endif

void align_destroy(s_align* a) {
	free(a->cigar);
	free(a);
}

uint64_t ssw_avx2_requested(void) {
	return ssw_avx2_requested_runtime() ? 1 : 0;
}

uint64_t ssw_avx2_compiled(void) {
#if defined(__AVX2__)
	return 1;
#else
	return 0;
#endif
}

uint64_t ssw_avx2_active(void) {
	return g_ssw_avx2_active;
}

uint64_t ssw_avx2_mode(void) {
	return ssw_avx2_mode_runtime();
}

uint64_t ssw_avx2_calls(void) {
	return g_ssw_avx2_calls;
}

uint64_t ssw_avx2_forward_calls(void) {
	return g_ssw_avx2_forward_calls;
}

uint64_t ssw_avx2_reverse_calls(void) {
	return g_ssw_avx2_reverse_calls;
}

uint64_t ssw_avx2_byte_calls(void) {
	return g_ssw_avx2_byte_calls;
}

uint64_t ssw_avx2_word_calls(void) {
	return g_ssw_avx2_word_calls;
}

uint64_t ssw_avx2_fallback_calls(void) {
	return g_ssw_avx2_fallback_calls;
}

uint32_t* add_cigar(uint32_t* new_cigar, int32_t* p, int32_t* s, uint32_t length, char op) {
	if ((*p) >= (*s)) {
		++(*s);
		kroundup32(*s);
		new_cigar = (uint32_t*)realloc(new_cigar, (*s) * sizeof(uint32_t));
	}
	new_cigar[(*p)++] = to_cigar_int(length, op);
	return new_cigar;
}

uint32_t* store_previous_m(int8_t choice,	// 0: current not M, 1: current match, 2: current mismatch
	uint32_t* length_m,
	uint32_t* length_x,
	int32_t* p,
	int32_t* s,
	uint32_t* new_cigar) {

	if ((*length_m) && (choice == 2 || !choice)) {
		new_cigar = add_cigar(new_cigar, p, s, (*length_m), '=');
		(*length_m) = 0;
	}
	else if ((*length_x) && (choice == 1 || !choice)) {
		new_cigar = add_cigar(new_cigar, p, s, (*length_x), 'X');
		(*length_x) = 0;
	}
	return new_cigar;
}

/*! @function:
	 1. Calculate the number of mismatches.
	 2. Modify the cigar string:
		 differentiate matches (=) and mismatches(X); add softclip(S) at the beginning and ending of the original cigar.
	@return:
	 The number of mismatches.
	 The cigar and cigarLen are modified.
*/
int32_t mark_mismatch(int32_t ref_begin1,
	int32_t read_begin1,
	int32_t read_end1,
	const int8_t* ref,
	const int8_t* read,
	int32_t readLen,
	uint32_t** cigar,
	int32_t* cigarLen) {

	int32_t mismatch_length = 0, p = 0, i, length, j, s = *cigarLen + 2;
	uint32_t *new_cigar = (uint32_t*)malloc(s * sizeof(uint32_t)), length_m = 0, length_x = 0;
	char op;

	ref += ref_begin1;
	read += read_begin1;
	if (read_begin1 > 0) new_cigar[p++] = to_cigar_int(read_begin1, 'S');
	for (i = 0; i < (*cigarLen); ++i) {
		op = cigar_int_to_op((*cigar)[i]);
		length = cigar_int_to_len((*cigar)[i]);
		if (op == 'M') {
			for (j = 0; j < length; ++j) {
				if (*ref != *read) {
					++mismatch_length;
					// the previous is match; however the current one is mismatche
					new_cigar = store_previous_m(2, &length_m, &length_x, &p, &s, new_cigar);
					++length_x;
				}
				else {
					// the previous is mismatch; however the current one is matche
					new_cigar = store_previous_m(1, &length_m, &length_x, &p, &s, new_cigar);
					++length_m;
				}
				++ref;
				++read;
			}
		}
		else if (op == 'I') {
			read += length;
			mismatch_length += length;
			new_cigar = store_previous_m(0, &length_m, &length_x, &p, &s, new_cigar);
			new_cigar = add_cigar(new_cigar, &p, &s, length, 'I');
		}
		else if (op == 'D') {
			ref += length;
			mismatch_length += length;
			new_cigar = store_previous_m(0, &length_m, &length_x, &p, &s, new_cigar);
			new_cigar = add_cigar(new_cigar, &p, &s, length, 'D');
		}
	}
	new_cigar = store_previous_m(0, &length_m, &length_x, &p, &s, new_cigar);

	length = readLen - read_end1 - 1;
	if (length > 0) new_cigar = add_cigar(new_cigar, &p, &s, length, 'S');

	(*cigarLen) = p;
	free(*cigar);
	(*cigar) = new_cigar;
	return mismatch_length;
}
