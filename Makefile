UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)

CXX ?= clang++
CXXFLAGS ?= -O2 -std=c++11
CPPFLAGS ?=
LDFLAGS ?=
LDLIBS ?=
PTHREAD_FLAGS ?= -pthread
TARGET ?= longtarget_x86
SIMD_FLAGS ?= -msse2
SOURCES := longtarget.cpp cuda/calc_score_cuda_stub.cpp
SOURCES += cuda/sim_scan_cuda_stub.cpp
SOURCES += cuda/prealign_cuda_stub.cpp
SOURCES += cuda/sim_traceback_cuda_stub.cpp
SOURCES += cuda/sim_locate_cuda_stub.cpp
HEADERS := exact_sim.h sim.h stats.h rules.h cuda/calc_score_cuda.h cuda/sim_cuda_runtime.h cuda/sim_scan_cuda.h cuda/prealign_cuda.h cuda/sim_traceback_cuda.h cuda/sim_locate_cuda.h
ENABLE_OPENMP ?= 0
OPENMP_FLAGS ?=

ARCH_FLAGS :=
RUN_PREFIX :=

ifeq ($(UNAME_S),Darwin)
  ifeq ($(UNAME_M),arm64)
    ARCH_FLAGS += -arch x86_64
    RUN_PREFIX := arch -x86_64
  endif
endif

OPENMP_AUTODETECT_FLAGS := $(strip $(shell TMP_BASE=$$(mktemp /tmp/longtarget-omp-XXXXXX); TMP_OBJ=$${TMP_BASE}.o; TMP_BIN=$${TMP_BASE}.bin; if $(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) -x c++ /dev/null -c -fopenmp -o $$TMP_OBJ >/dev/null 2>&1 && $(CXX) $(ARCH_FLAGS) -fopenmp $$TMP_OBJ -o $$TMP_BIN >/dev/null 2>&1; then printf '%s' '-fopenmp'; fi; rm -f $$TMP_BASE $$TMP_OBJ $$TMP_BIN))
ifneq ($(strip $(OPENMP_FLAGS)),)
  OPENMP_AVAILABLE := 1
else ifneq ($(strip $(OPENMP_AUTODETECT_FLAGS)),)
  OPENMP_AVAILABLE := 1
else
  OPENMP_AVAILABLE := 0
endif

ifneq (,$(filter 1 yes YES true TRUE,$(ENABLE_OPENMP)))
  ifneq ($(strip $(OPENMP_FLAGS)),)
    ACTIVE_OPENMP_FLAGS := $(OPENMP_FLAGS)
    OPENMP_ACTIVE := 1
  else ifneq ($(strip $(OPENMP_AUTODETECT_FLAGS)),)
    ACTIVE_OPENMP_FLAGS := $(OPENMP_AUTODETECT_FLAGS)
    OPENMP_ACTIVE := 1
  else
    $(warning ENABLE_OPENMP=1 requested, but OpenMP flags were not detected. Building without OpenMP. Provide OPENMP_FLAGS to enable it explicitly.)
    OPENMP_ACTIVE := 0
  endif
else
  OPENMP_ACTIVE := 0
endif

build: $(TARGET)

$(TARGET): $(SOURCES) $(HEADERS)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(ACTIVE_OPENMP_FLAGS) $(PTHREAD_FLAGS) $(SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

build-avx2:
	$(MAKE) TARGET=longtarget_avx2 SIMD_FLAGS=-mavx2 build

build-openmp:
	$(MAKE) TARGET=longtarget_openmp ENABLE_OPENMP=1 build

build-openmp-avx2:
	$(MAKE) TARGET=longtarget_openmp_avx2 SIMD_FLAGS=-mavx2 ENABLE_OPENMP=1 build

NVCC ?= /usr/local/cuda/bin/nvcc
CUDA_HOME ?= /usr/local/cuda
CUDA_ARCH ?= 80
CUDA_CXXFLAGS ?= -O2 -std=c++11 --generate-code=arch=compute_$(CUDA_ARCH),code=compute_$(CUDA_ARCH)
CUDA_LDFLAGS ?= -L$(CUDA_HOME)/lib64 -lcudart

CUDA_TARGET ?= longtarget_cuda
CUDA_OBJ := cuda/calc_score_cuda.o cuda/sim_scan_cuda.o cuda/prealign_cuda.o cuda/sim_traceback_cuda.o cuda/sim_locate_cuda.o
CUDA_ADA_TARGET ?= longtarget_cuda_sm89
CUDA_ADA_CXXFLAGS ?= -O3 -std=c++11 --generate-code=arch=compute_89,code=sm_89 --generate-code=arch=compute_80,code=compute_80
CUDA_ADA_OBJ := cuda/calc_score_cuda.sm89.o cuda/sim_scan_cuda.sm89.o cuda/prealign_cuda.sm89.o cuda/sim_traceback_cuda.sm89.o cuda/sim_locate_cuda.sm89.o

cuda/calc_score_cuda.o: cuda/calc_score_cuda.cu cuda/calc_score_cuda.h
	$(NVCC) $(CUDA_CXXFLAGS) -c $< -o $@

cuda/calc_score_cuda.sm89.o: cuda/calc_score_cuda.cu cuda/calc_score_cuda.h
	$(NVCC) $(CUDA_ADA_CXXFLAGS) -c $< -o $@

cuda/sim_scan_cuda.o: cuda/sim_scan_cuda.cu cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h
	$(NVCC) $(CUDA_CXXFLAGS) -c $< -o $@

cuda/sim_scan_cuda.sm89.o: cuda/sim_scan_cuda.cu cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h
	$(NVCC) $(CUDA_ADA_CXXFLAGS) -c $< -o $@

cuda/prealign_cuda.o: cuda/prealign_cuda.cu cuda/prealign_cuda.h
	$(NVCC) $(CUDA_CXXFLAGS) -c $< -o $@

cuda/prealign_cuda.sm89.o: cuda/prealign_cuda.cu cuda/prealign_cuda.h
	$(NVCC) $(CUDA_ADA_CXXFLAGS) -c $< -o $@

cuda/sim_traceback_cuda.o: cuda/sim_traceback_cuda.cu cuda/sim_traceback_cuda.h cuda/sim_cuda_runtime.h
	$(NVCC) $(CUDA_CXXFLAGS) -c $< -o $@

cuda/sim_traceback_cuda.sm89.o: cuda/sim_traceback_cuda.cu cuda/sim_traceback_cuda.h cuda/sim_cuda_runtime.h
	$(NVCC) $(CUDA_ADA_CXXFLAGS) -c $< -o $@

cuda/sim_locate_cuda.o: cuda/sim_locate_cuda.cu cuda/sim_locate_cuda.h cuda/sim_cuda_runtime.h
	$(NVCC) $(CUDA_CXXFLAGS) -c $< -o $@

cuda/sim_locate_cuda.sm89.o: cuda/sim_locate_cuda.cu cuda/sim_locate_cuda.h cuda/sim_cuda_runtime.h
	$(NVCC) $(CUDA_ADA_CXXFLAGS) -c $< -o $@

build-cuda: $(CUDA_TARGET)

$(CUDA_TARGET): longtarget.cpp $(HEADERS) $(CUDA_OBJ)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) longtarget.cpp $(CUDA_OBJ) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

build-cuda-avx2:
	$(MAKE) CUDA_TARGET=longtarget_cuda_avx2 SIMD_FLAGS=-mavx2 build-cuda

build-cuda-native-ada: $(CUDA_ADA_TARGET)

$(CUDA_ADA_TARGET): longtarget.cpp $(HEADERS) $(CUDA_ADA_OBJ)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) longtarget.cpp $(CUDA_ADA_OBJ) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

check-cuda-native-ada-fatbin: build-cuda-native-ada
	TARGET=$(CURDIR)/$(CUDA_ADA_TARGET) CUDA_HOME=$(CUDA_HOME) sh ./scripts/check_cuda_native_ada_fatbin.sh

FASIM_CXXFLAGS ?= -O3 -std=c++11 -pthread
FASIM_SIMD_FLAGS ?= -msse2
FASIM_TARGET ?= fasim_longtarget_x86
FASIM_CUDA_TARGET ?= fasim_longtarget_cuda
FASIM_GASAL2_TARGET ?= fasim_longtarget_gasal2
FASIM_SOURCES := fasim/Fasim-LongTarget.cpp fasim/ssw_cpp.cpp fasim/sswNew.cpp
FASIM_HEADERS := $(wildcard fasim/*.h)
GASAL2_DIR ?= .tmp/GASAL2
GASAL2_REPO_URL ?= https://github.com/nahmedraja/GASAL2.git
GASAL2_COMMIT ?= 106d94ee53fc847214fb05f2f9f892538a5d3baf
GASAL2_PATCH ?= patches/gasal2-fasim-bridge.patch
GASAL2_CUDA_LIB ?= /usr/local/cuda-12.5/targets/x86_64-linux/lib
GASAL2_GPU_SM_ARCH ?= sm_89
GASAL2_MAX_QUERY_LEN ?= 2812
GASAL2_N_CODE ?= 0x4E
GASAL2_BUILD_STAMP := $(GASAL2_DIR)/.fasim_gasal2.$(GASAL2_GPU_SM_ARCH).$(GASAL2_MAX_QUERY_LEN).$(GASAL2_N_CODE).stamp

build-fasim: $(FASIM_TARGET)

$(FASIM_TARGET): $(FASIM_SOURCES) $(FASIM_HEADERS) fasim/gasal2_align_bridge_stub.cpp cuda/prealign_cuda_stub.cpp cuda/prealign_cuda.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(FASIM_SOURCES) fasim/gasal2_align_bridge_stub.cpp cuda/prealign_cuda_stub.cpp $(LDFLAGS) $(LDLIBS) -o $@

build-fasim-cuda: $(FASIM_CUDA_TARGET)

$(FASIM_CUDA_TARGET): $(FASIM_SOURCES) $(FASIM_HEADERS) fasim/gasal2_align_bridge_stub.cpp cuda/prealign_cuda.o cuda/prealign_cuda.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(FASIM_SOURCES) fasim/gasal2_align_bridge_stub.cpp cuda/prealign_cuda.o $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

setup-gasal2:
	GASAL2_DIR=$(GASAL2_DIR) GASAL2_REPO_URL=$(GASAL2_REPO_URL) GASAL2_COMMIT=$(GASAL2_COMMIT) GASAL2_PATCH=$(CURDIR)/$(GASAL2_PATCH) bash ./scripts/setup_gasal2.sh

build-gasal2: setup-gasal2 $(GASAL2_BUILD_STAMP)

$(GASAL2_BUILD_STAMP): $(wildcard $(GASAL2_DIR)/src/*) $(wildcard $(GASAL2_DIR)/src/kernels/*) $(GASAL2_DIR)/Makefile
	$(MAKE) -C $(GASAL2_DIR) GPU_SM_ARCH=$(GASAL2_GPU_SM_ARCH) MAX_QUERY_LEN=$(GASAL2_MAX_QUERY_LEN) N_CODE=$(GASAL2_N_CODE)
	@rm -f $(GASAL2_DIR)/.fasim_gasal2.*.stamp
	@touch $@

build-fasim-gasal2: $(FASIM_GASAL2_TARGET)

$(FASIM_GASAL2_TARGET): $(FASIM_SOURCES) $(FASIM_HEADERS) fasim/gasal2_align_bridge.cpp cuda/prealign_cuda.o cuda/prealign_cuda.h $(GASAL2_BUILD_STAMP) $(GASAL2_DIR)/lib/libgasal.a
	$(CXX) $(CPPFLAGS) -DFASIM_WITH_GASAL2 -I$(GASAL2_DIR)/include $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(FASIM_SOURCES) fasim/gasal2_align_bridge.cpp cuda/prealign_cuda.o $(LDFLAGS) $(LDLIBS) -L$(GASAL2_DIR)/lib -lgasal $(CUDA_LDFLAGS) -L$(GASAL2_CUDA_LIB) -lcudart -o $@

build-fasim-gasal2-nvtx:
	$(MAKE) build-fasim-gasal2 \
		FASIM_GASAL2_TARGET=$(or $(FASIM_GASAL2_NVTX_TARGET),$(CURDIR)/.tmp/fasim_longtarget_gasal2_nvtx) \
		CPPFLAGS="$(CPPFLAGS) -DFASIM_WITH_NVTX -I$(CUDA_HOME)/include" \
		LDFLAGS="$(LDFLAGS) -L$(CUDA_HOME)/lib64 -Wl,-rpath,$(CUDA_HOME)/lib64" \
		LDLIBS="$(LDLIBS) -lnvToolsExt"

.PHONY: build-fasim-gasal2-nvtx

oracle-sample: $(TARGET)
	./scripts/run_sample_exactness.sh --generate-oracle

check-sample: $(TARGET)
	./scripts/run_sample_exactness.sh

check-sample-cuda:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_sample_exactness_cuda.sh

check-sample-cuda-sim:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_SIM_CUDA=1 EXPECTED_SIM_INITIAL_BACKEND=cuda OUTPUT_SUBDIR=sample_exactness_cuda_sim TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_sample_exactness_cuda.sh

check-sample-cuda-sim-region:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1 EXPECTED_SIM_INITIAL_BACKEND=cuda EXPECTED_SIM_REGION_BACKEND=cuda OUTPUT_SUBDIR=sample_exactness_cuda_sim_region TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_sample_exactness_cuda.sh

check-sample-cuda-sim-region-locate:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1 LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 EXPECTED_SIM_INITIAL_BACKEND=cuda EXPECTED_SIM_REGION_BACKEND=cuda EXPECTED_SIM_LOCATE_MODE=safe_workset OUTPUT_SUBDIR=sample_exactness_cuda_sim_region_locate TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_sample_exactness_cuda.sh

check-sim-initial-chunked-handoff-matrix:
	$(MAKE) build-cuda
	for rows in 1 2 3 4 7 8 16 31 64 127 256 1024; do \
		LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF=1 \
		LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_ROWS_PER_CHUNK=$$rows \
		LONGTARGET_ENABLE_SIM_CUDA=1 \
		LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
		LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
		EXPECTED_SIM_INITIAL_BACKEND=cuda \
		EXPECTED_SIM_REGION_BACKEND=cuda \
		EXPECTED_SIM_LOCATE_MODE=safe_workset \
		OUTPUT_SUBDIR=sample_exactness_cuda_sim_region_locate_chunked_rows_$$rows \
		TARGET=$(CURDIR)/$(CUDA_TARGET) \
			./scripts/run_sample_exactness_cuda.sh || exit $$?; \
	done

check-sim-initial-pinned-async-handoff:
	$(MAKE) build-cuda
	LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF=1 \
	LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_HANDOFF=1 \
	LONGTARGET_ENABLE_SIM_CUDA=1 \
	LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
	LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
	EXPECTED_SIM_INITIAL_BACKEND=cuda \
	EXPECTED_SIM_REGION_BACKEND=cuda \
	EXPECTED_SIM_LOCATE_MODE=safe_workset \
	OUTPUT_SUBDIR=sample_exactness_cuda_sim_region_locate_pinned_async_handoff \
	TARGET=$(CURDIR)/$(CUDA_TARGET) \
	./scripts/run_sample_exactness_cuda.sh
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_enabled=1$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_requested=1$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_active=1$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_requested_batches=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_active_batches=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_disabled_reason=none$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_source_ready_mode=global_stop_event$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_chunks_total=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_slots=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_bytes=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_allocation_failures=0$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pageable_fallbacks=0$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_sync_copies=0$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_async_copies=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_slot_reuse_waits=[0-9]+$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_slots_reused_after_materialize=1$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_async_d2h_seconds=([1-9][0-9]*(\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)([eE][-+]?[0-9]+)?$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_d2h_wait_seconds=[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_apply_seconds=0(\.0+)?$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_d2h_overlap_seconds=0(\.0+)?$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_dp_d2h_overlap_seconds=0(\.0+)?$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_critical_path_seconds=([1-9][0-9]*(\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)([eE][-+]?[0-9]+)?$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff/stderr.log

check-sim-initial-pinned-async-handoff-disabled:
	$(MAKE) build-cuda
	LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_HANDOFF=1 \
	LONGTARGET_ENABLE_SIM_CUDA=1 \
	LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
	LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
	EXPECTED_SIM_INITIAL_BACKEND=cuda \
	EXPECTED_SIM_REGION_BACKEND=cuda \
	EXPECTED_SIM_LOCATE_MODE=safe_workset \
	OUTPUT_SUBDIR=sample_exactness_cuda_sim_region_locate_pinned_async_handoff_chunked_off \
	TARGET=$(CURDIR)/$(CUDA_TARGET) \
	./scripts/run_sample_exactness_cuda.sh
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_requested=1$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_chunked_off/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_active=0$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_chunked_off/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_requested_batches=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_chunked_off/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_active_batches=0$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_chunked_off/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_disabled_reason=chunked_handoff_off$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_chunked_off/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_async_copies=0$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_chunked_off/stderr.log
	LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF=1 \
	LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_HANDOFF=1 \
	LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY=1 \
	LONGTARGET_ENABLE_SIM_CUDA=1 \
	LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
	LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
	EXPECTED_SIM_INITIAL_BACKEND=cuda \
	EXPECTED_SIM_REGION_BACKEND=cuda \
	EXPECTED_SIM_LOCATE_MODE=safe_workset \
	OUTPUT_SUBDIR=sample_exactness_cuda_sim_region_locate_pinned_async_handoff_exact_replay \
	TARGET=$(CURDIR)/$(CUDA_TARGET) \
	./scripts/run_sample_exactness_cuda.sh
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_requested=1$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_exact_replay/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_active=0$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_exact_replay/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_requested_batches=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_exact_replay/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_active_batches=0$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_exact_replay/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_disabled_reason=unsupported_path$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_exact_replay/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_async_copies=0$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_exact_replay/stderr.log

check-sim-initial-pinned-async-handoff-fallback:
	$(MAKE) build-cuda
	LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF=1 \
	LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_HANDOFF=1 \
	LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_FORCE_ALLOC_FAIL=1 \
	LONGTARGET_ENABLE_SIM_CUDA=1 \
	LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
	LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
	EXPECTED_SIM_INITIAL_BACKEND=cuda \
	EXPECTED_SIM_REGION_BACKEND=cuda \
	EXPECTED_SIM_LOCATE_MODE=safe_workset \
	OUTPUT_SUBDIR=sample_exactness_cuda_sim_region_locate_pinned_async_handoff_forced_fallback \
	TARGET=$(CURDIR)/$(CUDA_TARGET) \
	./scripts/run_sample_exactness_cuda.sh
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_requested=1$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_forced_fallback/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_active=1$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_forced_fallback/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_requested_batches=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_forced_fallback/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_active_batches=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_forced_fallback/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_async_disabled_reason=none$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_forced_fallback/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pinned_allocation_failures=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_forced_fallback/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pageable_fallbacks=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_forced_fallback/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_sync_copies=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_forced_fallback/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_async_copies=0$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_handoff_forced_fallback/stderr.log

check-sim-initial-pinned-async-cpu-pipeline:
	$(MAKE) build-cuda
	LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF=1 \
	LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_HANDOFF=1 \
	LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE=1 \
	LONGTARGET_SIM_CUDA_INITIAL_HANDOFF_ROWS_PER_CHUNK=1 \
	LONGTARGET_ENABLE_SIM_CUDA=1 \
	LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
	LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
	EXPECTED_SIM_INITIAL_BACKEND=cuda \
	EXPECTED_SIM_REGION_BACKEND=cuda \
	EXPECTED_SIM_LOCATE_MODE=safe_workset \
	OUTPUT_SUBDIR=sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline \
	TARGET=$(CURDIR)/$(CUDA_TARGET) \
	./scripts/run_sample_exactness_cuda.sh
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_requested=1$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_active=1$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_disabled_reason=none$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_chunks_applied=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_summaries_applied=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_chunks_finalized=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	awk -F= '/^benchmark\.sim_initial_handoff_cpu_pipeline_chunks_applied=/{applied=$$2} /^benchmark\.sim_initial_handoff_cpu_pipeline_chunks_finalized=/{finalized=$$2} END{exit !(applied > 0 && finalized == applied)}' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_finalize_count=48$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_out_of_order_chunks=0$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_async_copies=[1-9][0-9]*$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_sync_copies=0$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_pageable_fallbacks=0$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_apply_seconds=([1-9][0-9]*(\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)([eE][-+]?[0-9]+)?$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_d2h_overlap_seconds=([1-9][0-9]*(\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)([eE][-+]?[0-9]+)?$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_source_ready_mode=global_stop_event$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_dp_d2h_overlap_seconds=0(\.0+)?$$' .tmp/sample_exactness_cuda_sim_region_locate_pinned_async_cpu_pipeline/stderr.log
	LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF=1 \
	LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE=1 \
	LONGTARGET_ENABLE_SIM_CUDA=1 \
	LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
	LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
	EXPECTED_SIM_INITIAL_BACKEND=cuda \
	EXPECTED_SIM_REGION_BACKEND=cuda \
	EXPECTED_SIM_LOCATE_MODE=safe_workset \
	OUTPUT_SUBDIR=sample_exactness_cuda_sim_region_locate_cpu_pipeline_pinned_async_off \
	TARGET=$(CURDIR)/$(CUDA_TARGET) \
	./scripts/run_sample_exactness_cuda.sh
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_requested=1$$' .tmp/sample_exactness_cuda_sim_region_locate_cpu_pipeline_pinned_async_off/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_active=0$$' .tmp/sample_exactness_cuda_sim_region_locate_cpu_pipeline_pinned_async_off/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_disabled_reason=pinned_async_off$$' .tmp/sample_exactness_cuda_sim_region_locate_cpu_pipeline_pinned_async_off/stderr.log
	LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF=1 \
	LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_HANDOFF=1 \
	LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE=1 \
	LONGTARGET_SIM_CUDA_INITIAL_EXACT_FRONTIER_REPLAY=1 \
	LONGTARGET_ENABLE_SIM_CUDA=1 \
	LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
	LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
	EXPECTED_SIM_INITIAL_BACKEND=cuda \
	EXPECTED_SIM_REGION_BACKEND=cuda \
	EXPECTED_SIM_LOCATE_MODE=safe_workset \
	OUTPUT_SUBDIR=sample_exactness_cuda_sim_region_locate_cpu_pipeline_exact_replay \
	TARGET=$(CURDIR)/$(CUDA_TARGET) \
	./scripts/run_sample_exactness_cuda.sh
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_requested=1$$' .tmp/sample_exactness_cuda_sim_region_locate_cpu_pipeline_exact_replay/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_active=0$$' .tmp/sample_exactness_cuda_sim_region_locate_cpu_pipeline_exact_replay/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_disabled_reason=unsupported_path$$' .tmp/sample_exactness_cuda_sim_region_locate_cpu_pipeline_exact_replay/stderr.log
	LONGTARGET_SIM_CUDA_INITIAL_CHUNKED_HANDOFF=1 \
	LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_HANDOFF=1 \
	LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_CPU_PIPELINE=1 \
	LONGTARGET_SIM_CUDA_INITIAL_PINNED_ASYNC_FORCE_ALLOC_FAIL=1 \
	LONGTARGET_ENABLE_SIM_CUDA=1 \
	LONGTARGET_ENABLE_SIM_CUDA_REGION=1 \
	LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 \
	EXPECTED_SIM_INITIAL_BACKEND=cuda \
	EXPECTED_SIM_REGION_BACKEND=cuda \
	EXPECTED_SIM_LOCATE_MODE=safe_workset \
	OUTPUT_SUBDIR=sample_exactness_cuda_sim_region_locate_cpu_pipeline_forced_fallback \
	TARGET=$(CURDIR)/$(CUDA_TARGET) \
	./scripts/run_sample_exactness_cuda.sh
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_requested=1$$' .tmp/sample_exactness_cuda_sim_region_locate_cpu_pipeline_forced_fallback/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_active=0$$' .tmp/sample_exactness_cuda_sim_region_locate_cpu_pipeline_forced_fallback/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_async_copies=0$$' .tmp/sample_exactness_cuda_sim_region_locate_cpu_pipeline_forced_fallback/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_d2h_overlap_seconds=0(\.0+)?$$' .tmp/sample_exactness_cuda_sim_region_locate_cpu_pipeline_forced_fallback/stderr.log
	grep -Eq '^benchmark\.sim_initial_handoff_cpu_pipeline_finalize_count=0$$' .tmp/sample_exactness_cuda_sim_region_locate_cpu_pipeline_forced_fallback/stderr.log

oracle-smoke: $(TARGET)
	RULE=1 EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1 ./scripts/run_sample_exactness.sh --generate-oracle

check-smoke: $(TARGET)
	RULE=1 EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1 ./scripts/run_sample_exactness.sh

check-smoke-cuda:
	$(MAKE) build-cuda
	RULE=1 EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1_cuda TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_sample_exactness_cuda.sh

check-smoke-cuda-sim:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_SIM_CUDA=1 RULE=1 EXPECTED_SIM_INITIAL_BACKEND=cuda EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1_cuda_sim TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_sample_exactness_cuda.sh

check-smoke-cuda-sim-region:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1 RULE=1 EXPECTED_SIM_INITIAL_BACKEND=cuda EXPECTED_SIM_REGION_BACKEND=cuda EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1_cuda_sim_region TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_sample_exactness_cuda.sh

check-smoke-cuda-sim-region-locate:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1 LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1 RULE=1 EXPECTED_SIM_INITIAL_BACKEND=cuda EXPECTED_SIM_REGION_BACKEND=cuda EXPECTED_SIM_LOCATE_MODE=safe_workset EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1_cuda_sim_region_locate TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_sample_exactness_cuda.sh

check-smoke-cuda-sim-full:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_SIM_CUDA_FULL=1 RULE=1 EXPECTED_SIM_SOLVER_BACKEND=cuda_full_exact EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1_cuda_sim_full TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_sample_exactness_cuda.sh

check-sample-cuda-sim-traceback-strict:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1 LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK=1 LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE=1 EXPECTED_SIM_INITIAL_BACKEND=cuda EXPECTED_SIM_REGION_BACKEND=cuda OUTPUT_SUBDIR=sample_exactness_cuda_sim_traceback_strict TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_sample_exactness_cuda.sh

check-smoke-cuda-sim-traceback-strict:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1 LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK=1 LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE=1 RULE=1 EXPECTED_SIM_INITIAL_BACKEND=cuda EXPECTED_SIM_REGION_BACKEND=cuda EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1_cuda_sim_traceback_strict TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_sample_exactness_cuda.sh

check-smoke-cuda-avx2:
	$(MAKE) build-cuda-avx2
	RULE=1 EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1_cuda_avx2 TARGET=$(CURDIR)/longtarget_cuda_avx2 ./scripts/run_sample_exactness_cuda.sh

check-sample-row: $(TARGET)
	LONGTARGET_SIM_INITIAL_BACKEND=row ./scripts/run_sample_exactness.sh

check-sample-wavefront: $(TARGET)
	LONGTARGET_SIM_INITIAL_BACKEND=wavefront ./scripts/run_sample_exactness.sh

check-smoke-row: $(TARGET)
	LONGTARGET_SIM_INITIAL_BACKEND=row RULE=1 EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1 ./scripts/run_sample_exactness.sh

check-smoke-wavefront: $(TARGET)
	LONGTARGET_SIM_INITIAL_BACKEND=wavefront RULE=1 EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1 ./scripts/run_sample_exactness.sh

check-smoke-avx2:
	$(MAKE) TARGET=longtarget_avx2 SIMD_FLAGS=-mavx2 build
	TARGET=$(CURDIR)/longtarget_avx2 LONGTARGET_SIM_INITIAL_BACKEND=wavefront RULE=1 EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1 ./scripts/run_sample_exactness.sh

check-sample-avx2:
	$(MAKE) TARGET=longtarget_avx2 SIMD_FLAGS=-mavx2 build
	TARGET=$(CURDIR)/longtarget_avx2 LONGTARGET_SIM_INITIAL_BACKEND=wavefront ./scripts/run_sample_exactness.sh

oracle-matrix: $(TARGET)
	./scripts/run_rule_matrix_exactness.sh --generate-oracle

check-matrix: $(TARGET)
	./scripts/run_rule_matrix_exactness.sh

check-matrix-cuda:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_rule_matrix_exactness_cuda.sh

check-matrix-cuda-sim:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_SIM_CUDA=1 EXPECTED_SIM_INITIAL_BACKEND=cuda OUTPUT_SUBDIR=rule_matrix_exactness_cuda_sim TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_rule_matrix_exactness_cuda.sh

check-matrix-cuda-sim-region:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1 EXPECTED_SIM_INITIAL_BACKEND=cuda EXPECTED_SIM_REGION_BACKEND=cuda OUTPUT_SUBDIR=rule_matrix_exactness_cuda_sim_region TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_rule_matrix_exactness_cuda.sh

check-matrix-cuda-avx2:
	$(MAKE) build-cuda-avx2
	TARGET=$(CURDIR)/longtarget_cuda_avx2 ./scripts/run_rule_matrix_exactness_cuda.sh

check-matrix-row: $(TARGET)
	BACKEND=row ./scripts/run_rule_matrix_exactness.sh

check-matrix-wavefront: $(TARGET)
	BACKEND=wavefront ./scripts/run_rule_matrix_exactness.sh

check-matrix-avx2:
	$(MAKE) TARGET=longtarget_avx2 SIMD_FLAGS=-mavx2 build
	TARGET=$(CURDIR)/longtarget_avx2 BACKEND=wavefront ./scripts/run_rule_matrix_exactness.sh

check-sample-openmp-1:
	@if [ "$(OPENMP_AVAILABLE)" != "1" ]; then \
		echo "OpenMP flags were not detected; rerun with OPENMP_FLAGS=... to enable OpenMP."; \
		exit 0; \
	fi; \
	$(MAKE) TARGET=longtarget_openmp ENABLE_OPENMP=1 build && \
	OMP_NUM_THREADS=1 TARGET=$(CURDIR)/longtarget_openmp ./scripts/run_sample_exactness.sh

check-sample-openmp-par:
	@if [ "$(OPENMP_AVAILABLE)" != "1" ]; then \
		echo "OpenMP flags were not detected; rerun with OPENMP_FLAGS=... to enable OpenMP."; \
		exit 0; \
	fi; \
	$(MAKE) TARGET=longtarget_openmp ENABLE_OPENMP=1 build && \
	OMP_NUM_THREADS=4 TARGET=$(CURDIR)/longtarget_openmp ./scripts/run_sample_exactness.sh

check-smoke-openmp-1:
	@if [ "$(OPENMP_AVAILABLE)" != "1" ]; then \
		echo "OpenMP flags were not detected; rerun with OPENMP_FLAGS=... to enable OpenMP."; \
		exit 0; \
	fi; \
	$(MAKE) TARGET=longtarget_openmp ENABLE_OPENMP=1 build && \
	OMP_NUM_THREADS=1 TARGET=$(CURDIR)/longtarget_openmp RULE=1 EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1 ./scripts/run_sample_exactness.sh

check-smoke-openmp-par:
	@if [ "$(OPENMP_AVAILABLE)" != "1" ]; then \
		echo "OpenMP flags were not detected; rerun with OPENMP_FLAGS=... to enable OpenMP."; \
		exit 0; \
	fi; \
	$(MAKE) TARGET=longtarget_openmp ENABLE_OPENMP=1 build && \
	OMP_NUM_THREADS=4 TARGET=$(CURDIR)/longtarget_openmp RULE=1 EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1 ./scripts/run_sample_exactness.sh

check-matrix-openmp-1:
	@if [ "$(OPENMP_AVAILABLE)" != "1" ]; then \
		echo "OpenMP flags were not detected; rerun with OPENMP_FLAGS=... to enable OpenMP."; \
		exit 0; \
	fi; \
	$(MAKE) TARGET=longtarget_openmp ENABLE_OPENMP=1 build && \
	OMP_NUM_THREADS=1 TARGET=$(CURDIR)/longtarget_openmp ./scripts/run_rule_matrix_exactness.sh

check-matrix-openmp-par:
	@if [ "$(OPENMP_AVAILABLE)" != "1" ]; then \
		echo "OpenMP flags were not detected; rerun with OPENMP_FLAGS=... to enable OpenMP."; \
		exit 0; \
	fi; \
	$(MAKE) TARGET=longtarget_openmp ENABLE_OPENMP=1 build && \
	OMP_NUM_THREADS=4 TARGET=$(CURDIR)/longtarget_openmp ./scripts/run_rule_matrix_exactness.sh

benchmark-sample: $(TARGET)
	LONGTARGET_BENCHMARK=1 ./scripts/run_sample_exactness.sh >/dev/null

benchmark-smoke: $(TARGET)
	LONGTARGET_BENCHMARK=1 RULE=1 EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1 ./scripts/run_sample_exactness.sh >/dev/null

benchmark-sample-cuda:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_CUDA=1 LONGTARGET_BENCHMARK=1 TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_sample_exactness.sh >/dev/null

benchmark-smoke-cuda:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_CUDA=1 LONGTARGET_BENCHMARK=1 RULE=1 EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1 TARGET=$(CURDIR)/$(CUDA_TARGET) ./scripts/run_sample_exactness.sh >/dev/null

benchmark-sample-cuda-avx2:
	$(MAKE) build-cuda-avx2
	LONGTARGET_ENABLE_CUDA=1 LONGTARGET_BENCHMARK=1 TARGET=$(CURDIR)/longtarget_cuda_avx2 ./scripts/run_sample_exactness.sh >/dev/null

benchmark-smoke-cuda-avx2:
	$(MAKE) build-cuda-avx2
	LONGTARGET_ENABLE_CUDA=1 LONGTARGET_BENCHMARK=1 RULE=1 EXPECTED_DIR=$(CURDIR)/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1 TARGET=$(CURDIR)/longtarget_cuda_avx2 ./scripts/run_sample_exactness.sh >/dev/null

benchmark-sample-cuda-fast:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA=1 TARGET=$(CURDIR)/$(CUDA_TARGET) OUTPUT_SUBDIR=sample_benchmark_fast_cuda EXPECTED_BACKEND=cuda EXPECTED_SIM_INITIAL_BACKEND=cuda ./scripts/run_sample_benchmark_fast.sh >/dev/null

benchmark-smoke-cuda-fast:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA=1 RULE=1 TARGET=$(CURDIR)/$(CUDA_TARGET) OUTPUT_SUBDIR=sample_benchmark_fast_rule1_cuda EXPECTED_BACKEND=cuda EXPECTED_SIM_INITIAL_BACKEND=cuda ./scripts/run_sample_benchmark_fast.sh >/dev/null

benchmark-sample-cuda-traceback:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1 LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK=1 LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE=0 TARGET=$(CURDIR)/$(CUDA_TARGET) OUTPUT_SUBDIR=sample_benchmark_traceback_cuda EXPECTED_BACKEND=cuda EXPECTED_SIM_INITIAL_BACKEND=cuda EXPECTED_SIM_REGION_BACKEND=cuda EXPECTED_SIM_TRACEBACK_BACKEND=cuda ./scripts/run_sample_benchmark_traceback_cuda.sh >/dev/null

benchmark-smoke-cuda-traceback:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1 LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK=1 LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE=0 RULE=1 TARGET=$(CURDIR)/$(CUDA_TARGET) OUTPUT_SUBDIR=sample_benchmark_traceback_rule1_cuda EXPECTED_BACKEND=cuda EXPECTED_SIM_INITIAL_BACKEND=cuda EXPECTED_SIM_REGION_BACKEND=cuda EXPECTED_SIM_TRACEBACK_BACKEND=cuda ./scripts/run_sample_benchmark_traceback_cuda.sh >/dev/null

benchmark-sample-cuda-sim-full:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_FULL=1 TARGET=$(CURDIR)/$(CUDA_TARGET) OUTPUT_SUBDIR=sample_benchmark_sim_full EXPECTED_BACKEND=cuda EXPECTED_SIM_SOLVER_BACKEND=cuda_full_exact ./scripts/run_sample_benchmark_traceback_cuda.sh >/dev/null

benchmark-smoke-cuda-sim-full:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_FULL=1 RULE=1 TARGET=$(CURDIR)/$(CUDA_TARGET) OUTPUT_SUBDIR=sample_benchmark_rule1_sim_full EXPECTED_BACKEND=cuda EXPECTED_SIM_SOLVER_BACKEND=cuda_full_exact ./scripts/run_sample_benchmark_traceback_cuda.sh >/dev/null

benchmark-sample-cuda-window-pipeline:
	$(MAKE) build-cuda
	LONGTARGET_ENABLE_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_WINDOW_PIPELINE=1 LONGTARGET_OUTPUT_MODE=lite TARGET=$(CURDIR)/$(CUDA_TARGET) OUTPUT_SUBDIR=sample_benchmark_window_pipeline EXPECTED_BACKEND=cuda EXPECTED_SIM_SOLVER_BACKEND=cuda_window_pipeline EXPECTED_SIM_INITIAL_BACKEND=cuda EXPECTED_SIM_REGION_BACKEND=cuda ./scripts/run_sample_benchmark_traceback_cuda.sh >/dev/null

benchmark-sample-cuda-vs-fasim:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) python3 ./scripts/benchmark_sample_vs_fasim.py >/dev/null

benchmark-sample-cuda-throughput-compare:
	$(MAKE) build-cuda build-fasim-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) python3 ./scripts/benchmark_sample_vs_fasim.py --mode throughput --compare-output-mode lite --fasim-local-cuda $(CURDIR)/fasim_longtarget_cuda >/dev/null

benchmark-sample-cuda-vs-fasim-two-stage:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) python3 ./scripts/benchmark_sample_vs_fasim.py --run-longtarget-two-stage >/dev/null

benchmark-sample-cuda-vs-fasim-two-stage-prealign:
	$(MAKE) build-cuda
	LONGTARGET_PREFILTER_TOPK=256 TARGET=$(CURDIR)/$(CUDA_TARGET) python3 ./scripts/benchmark_sample_vs_fasim.py --run-longtarget-two-stage --two-stage-prefilter-backend prealign_cuda >/dev/null

benchmark-two-stage-frontier-sweep:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) python3 ./scripts/benchmark_two_stage_frontier_sweep.py --longtarget $(CURDIR)/$(CUDA_TARGET)

benchmark-two-stage-threshold-modes:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) python3 ./scripts/benchmark_two_stage_threshold_modes.py --longtarget $(CURDIR)/$(CUDA_TARGET)

benchmark-two-stage-threshold-heavy-microanchors:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) python3 ./scripts/benchmark_two_stage_threshold_heavy_microanchors.py --longtarget $(CURDIR)/$(CUDA_TARGET)

benchmark-fasim-batch:
	$(MAKE) build-fasim build-fasim-cuda
	python3 ./scripts/benchmark_fasim_batch_throughput.py

benchmark-fasim-throughput-sweep:
	$(MAKE) build-cuda build-fasim-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) python3 ./scripts/benchmark_fasim_throughput_sweep.py --longtarget $(CURDIR)/$(CUDA_TARGET) --fasim-local-cuda $(CURDIR)/fasim_longtarget_cuda

benchmark-fasim-sharded-worker-scaling:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/fasim_longtarget_x86 bash ./scripts/check_fasim_sharded_worker_scaling.sh

benchmark-fasim-sharded-worker-workload-matrix:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/fasim_longtarget_x86 bash ./scripts/check_fasim_sharded_worker_workload_matrix.sh

FASIM_CIGAR_TEST_TARGET ?= tests/test_fasim_cigar_identity
FASIM_CIGAR_TEST_SOURCES := tests/test_fasim_cigar_identity.cpp fasim/ssw_cpp.cpp fasim/sswNew.cpp fasim/gasal2_align_bridge_stub.cpp cuda/prealign_cuda_stub.cpp

FASIM_TRANSFERSTRING_TABLE_TEST_TARGET ?= tests/test_fasim_transferstring_table
FASIM_TRANSFERSTRING_TABLE_TEST_SOURCES := tests/test_fasim_transferstring_table.cpp

FASIM_SSW_PROFILE_CACHE_TEST_TARGET ?= tests/test_fasim_ssw_profile_cache
FASIM_SSW_PROFILE_CACHE_TEST_SOURCES := tests/test_fasim_ssw_profile_cache.cpp fasim/ssw_cpp.cpp fasim/sswNew.cpp

SSW_AVX2_DIRECT_TEST_TARGET ?= tests/test_ssw_avx2_direct
SSW_AVX2_DIRECT_TEST_SOURCES := tests/test_ssw_avx2_direct.cpp fasim/sswNew.cpp

PREALIGN_SHARED_TEST_TARGET ?= tests/test_prealign_shared
PREALIGN_SHARED_TEST_SOURCES := tests/test_prealign_shared.cpp cuda/prealign_cuda_stub.cpp

SIM_SCAN_BATCH_TEST_TARGET ?= tests/test_sim_scan_batch
SIM_SCAN_BATCH_TEST_SOURCES := tests/test_sim_scan_batch.cpp cuda/sim_scan_cuda_stub.cpp

SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_TARGET ?= tests/test_sim_scan_cuda_true_batch_reduce
SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_SOURCES := tests/test_sim_scan_cuda_true_batch_reduce.cpp cuda/sim_scan_cuda.o

SIM_REGION_BUCKETED_TRUE_BATCH_TEST_TARGET ?= tests/test_sim_region_bucketed_true_batch
SIM_REGION_BUCKETED_TRUE_BATCH_TEST_SOURCES := tests/test_sim_region_bucketed_true_batch.cpp cuda/sim_scan_cuda.o

SIM_REGION_SCHEDULER_SHAPE_TELEMETRY_TEST_TARGET ?= tests/test_sim_region_scheduler_shape_telemetry
SIM_REGION_SCHEDULER_SHAPE_TELEMETRY_TEST_SOURCES := tests/test_sim_region_scheduler_shape_telemetry.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET ?= tests/test_sim_region_single_request_direct_reduce
SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_SOURCES := tests/test_sim_region_single_request_direct_reduce.cpp cuda/sim_scan_cuda.o

SIM_CUDA_PROPOSAL_SELECT_TEST_TARGET ?= tests/test_sim_cuda_proposal_select
SIM_CUDA_PROPOSAL_SELECT_TEST_SOURCES := tests/test_sim_cuda_proposal_select.cpp cuda/sim_scan_cuda.o

SIM_TRACEBACK_CUDA_BATCH_TEST_TARGET ?= tests/test_sim_traceback_cuda_batch
SIM_TRACEBACK_CUDA_BATCH_TEST_SOURCES := tests/test_sim_traceback_cuda_batch.cpp cuda/sim_traceback_cuda.o

SIM_INITIAL_CUDA_MERGE_TEST_TARGET ?= tests/test_sim_initial_cuda_merge
SIM_INITIAL_CUDA_MERGE_TEST_SOURCES := tests/test_sim_initial_cuda_merge.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_INITIAL_CONTEXT_APPLY_CHUNK_SKIP_TEST_TARGET ?= tests/test_sim_initial_context_apply_chunk_skip
SIM_INITIAL_CONTEXT_APPLY_CHUNK_SKIP_TEST_SOURCES := tests/test_sim_initial_context_apply_chunk_skip.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_INITIAL_CHUNKED_HANDOFF_TEST_TARGET ?= tests/test_sim_initial_chunked_handoff
SIM_INITIAL_CHUNKED_HANDOFF_TEST_SOURCES := tests/test_sim_initial_chunked_handoff.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_INITIAL_EXACT_FRONTIER_REPLAY_TEST_TARGET ?= tests/test_sim_initial_exact_frontier_replay
SIM_INITIAL_EXACT_FRONTIER_REPLAY_TEST_SOURCES := tests/test_sim_initial_exact_frontier_replay.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_INITIAL_CPU_FRONTIER_FAST_APPLY_TEST_TARGET ?= tests/test_sim_initial_cpu_frontier_fast_apply
SIM_INITIAL_CPU_FRONTIER_FAST_APPLY_TEST_SOURCES := tests/test_sim_initial_cpu_frontier_fast_apply.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_FRONTIER_EPOCH_ORACLE_TEST_TARGET ?= tests/test_sim_initial_frontier_epoch_oracle
SIM_FRONTIER_EPOCH_ORACLE_TEST_SOURCES := tests/test_sim_initial_frontier_epoch_oracle.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_FRONTIER_EPOCH_SHADOW_TEST_TARGET ?= tests/test_sim_frontier_epoch_shadow
SIM_FRONTIER_EPOCH_SHADOW_TEST_SOURCES := tests/test_sim_frontier_epoch_shadow.cpp cuda/sim_scan_cuda.o cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_INITIAL_REDUCE_SEMANTICS_TEST_TARGET ?= tests/test_sim_initial_reduce_semantics
SIM_INITIAL_REDUCE_SEMANTICS_TEST_SOURCES := tests/test_sim_initial_reduce_semantics.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_INITIAL_ORDERED_SEGMENTED_V3_EXACTNESS_TEST_TARGET ?= tests/test_sim_initial_ordered_segmented_v3_exactness
SIM_INITIAL_ORDERED_SEGMENTED_V3_EXACTNESS_TEST_SOURCES := tests/test_sim_initial_ordered_segmented_v3_exactness.cpp cuda/sim_scan_cuda.o cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_INITIAL_FRONTIER_TRANSDUCER_SHADOW_TEST_TARGET ?= tests/test_sim_initial_frontier_transducer_shadow
SIM_INITIAL_FRONTIER_TRANSDUCER_SHADOW_TEST_SOURCES := tests/test_sim_initial_frontier_transducer_shadow.cpp cuda/sim_scan_cuda.o cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_INITIAL_FRONTIER_TRANSDUCER_SEGMENTED_SHADOW_TEST_TARGET ?= tests/test_sim_initial_frontier_transducer_segmented_shadow
SIM_INITIAL_FRONTIER_TRANSDUCER_SEGMENTED_SHADOW_TEST_SOURCES := tests/test_sim_initial_frontier_transducer_segmented_shadow.cpp cuda/sim_scan_cuda.o cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_INITIAL_FRONTIER_COMPACT_TRANSDUCER_ORACLE_TEST_TARGET ?= tests/test_sim_initial_frontier_compact_transducer_oracle
SIM_INITIAL_FRONTIER_COMPACT_TRANSDUCER_ORACLE_TEST_SOURCES := tests/test_sim_initial_frontier_compact_transducer_oracle.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_INITIAL_SUMMARY_PACKED_D2H_TEST_TARGET ?= tests/test_sim_initial_summary_packed_d2h
SIM_INITIAL_SUMMARY_PACKED_D2H_TEST_SOURCES := tests/test_sim_initial_summary_packed_d2h.cpp cuda/sim_scan_cuda.o cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_INITIAL_SUMMARY_HOST_COPY_ELISION_TEST_TARGET ?= tests/test_sim_initial_summary_host_copy_elision
SIM_INITIAL_SUMMARY_HOST_COPY_ELISION_TEST_SOURCES := tests/test_sim_initial_summary_host_copy_elision.cpp cuda/sim_scan_cuda.o cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

CALC_SCORE_CUDA_TELEMETRY_TEST_TARGET ?= tests/test_calc_score_cuda_telemetry
CALC_SCORE_CUDA_TELEMETRY_TEST_SOURCES := tests/test_calc_score_cuda_telemetry.cpp cuda/calc_score_cuda_stub.cpp cuda/sim_scan_cuda_stub.cpp cuda/prealign_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_LOCATE_UPDATE_TEST_TARGET ?= tests/test_sim_locate_update
SIM_LOCATE_UPDATE_TEST_SOURCES := tests/test_sim_locate_update.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_SAFE_WORKSET_CUDA_TEST_TARGET ?= tests/test_sim_safe_workset_cuda
SIM_SAFE_WORKSET_CUDA_TEST_SOURCES := tests/test_sim_safe_workset_cuda.cpp cuda/sim_scan_cuda.o cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_SAFE_WINDOW_GEOMETRY_V2_TEST_TARGET ?= tests/test_sim_safe_window_geometry_v2
SIM_SAFE_WINDOW_GEOMETRY_V2_TEST_SOURCES := tests/test_sim_safe_window_geometry_v2.cpp cuda/sim_scan_cuda.o cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_SAFE_WINDOW_FINE_EXECUTION_TEST_TARGET ?= tests/test_sim_safe_window_fine_execution
SIM_SAFE_WINDOW_FINE_EXECUTION_TEST_SOURCES := tests/test_sim_safe_window_fine_execution.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_RESIDENCY_FRONTIER_TEST_TARGET ?= tests/test_sim_residency_frontier
SIM_RESIDENCY_FRONTIER_TEST_SOURCES := tests/test_sim_residency_frontier.cpp cuda/sim_scan_cuda.o cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

EXACT_SIM_TWO_STAGE_THRESHOLD_TEST_TARGET ?= tests/test_exact_sim_two_stage_threshold
EXACT_SIM_TWO_STAGE_THRESHOLD_TEST_SOURCES := tests/test_exact_sim_two_stage_threshold.cpp cuda/prealign_cuda_stub.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

build-fasim-cigar-test: $(FASIM_CIGAR_TEST_TARGET)

build-fasim-transferstring-table-test: $(FASIM_TRANSFERSTRING_TABLE_TEST_TARGET)

build-fasim-ssw-profile-cache-test: $(FASIM_SSW_PROFILE_CACHE_TEST_TARGET)

build-ssw-avx2-direct-test: $(SSW_AVX2_DIRECT_TEST_TARGET)

build-prealign-shared-test: $(PREALIGN_SHARED_TEST_TARGET)

build-sim-scan-batch-test: $(SIM_SCAN_BATCH_TEST_TARGET)

build-sim-scan-cuda-true-batch-reduce-test: $(SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_TARGET)

build-sim-region-bucketed-true-batch-test: $(SIM_REGION_BUCKETED_TRUE_BATCH_TEST_TARGET)

build-sim-region-scheduler-shape-telemetry-test: $(SIM_REGION_SCHEDULER_SHAPE_TELEMETRY_TEST_TARGET)

build-sim-region-single-request-direct-reduce-test: $(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET)

build-sim-cuda-proposal-select-test: $(SIM_CUDA_PROPOSAL_SELECT_TEST_TARGET)

build-sim-traceback-cuda-batch-test: $(SIM_TRACEBACK_CUDA_BATCH_TEST_TARGET)

build-sim-initial-cuda-merge-test: $(SIM_INITIAL_CUDA_MERGE_TEST_TARGET)

build-sim-initial-context-apply-chunk-skip-test: $(SIM_INITIAL_CONTEXT_APPLY_CHUNK_SKIP_TEST_TARGET)

build-sim-initial-chunked-handoff-test: $(SIM_INITIAL_CHUNKED_HANDOFF_TEST_TARGET)

build-sim-initial-exact-frontier-replay-test: $(SIM_INITIAL_EXACT_FRONTIER_REPLAY_TEST_TARGET)

build-sim-initial-cpu-frontier-fast-apply-test: $(SIM_INITIAL_CPU_FRONTIER_FAST_APPLY_TEST_TARGET)

build-sim-frontier-epoch-oracle-test: $(SIM_FRONTIER_EPOCH_ORACLE_TEST_TARGET)

build-sim-frontier-epoch-shadow-test: $(SIM_FRONTIER_EPOCH_SHADOW_TEST_TARGET)

build-sim-initial-reduce-semantics-test: $(SIM_INITIAL_REDUCE_SEMANTICS_TEST_TARGET)

build-sim-initial-ordered-segmented-v3-exactness-test: $(SIM_INITIAL_ORDERED_SEGMENTED_V3_EXACTNESS_TEST_TARGET)

build-sim-initial-frontier-transducer-shadow-test: $(SIM_INITIAL_FRONTIER_TRANSDUCER_SHADOW_TEST_TARGET)

build-sim-initial-frontier-transducer-segmented-shadow-test: $(SIM_INITIAL_FRONTIER_TRANSDUCER_SEGMENTED_SHADOW_TEST_TARGET)

build-sim-initial-frontier-compact-transducer-oracle-test: $(SIM_INITIAL_FRONTIER_COMPACT_TRANSDUCER_ORACLE_TEST_TARGET)

build-sim-initial-summary-packed-d2h-test: $(SIM_INITIAL_SUMMARY_PACKED_D2H_TEST_TARGET)

build-sim-initial-summary-host-copy-elision-test: $(SIM_INITIAL_SUMMARY_HOST_COPY_ELISION_TEST_TARGET)

build-calc-score-cuda-telemetry-test: $(CALC_SCORE_CUDA_TELEMETRY_TEST_TARGET)

build-sim-locate-update-test: $(SIM_LOCATE_UPDATE_TEST_TARGET)

build-sim-safe-workset-cuda-test: $(SIM_SAFE_WORKSET_CUDA_TEST_TARGET)

build-sim-safe-window-geometry-v2-test: $(SIM_SAFE_WINDOW_GEOMETRY_V2_TEST_TARGET)

build-sim-safe-window-fine-execution-test: $(SIM_SAFE_WINDOW_FINE_EXECUTION_TEST_TARGET)

build-sim-residency-frontier-test: $(SIM_RESIDENCY_FRONTIER_TEST_TARGET)

build-exact-sim-two-stage-threshold-test: $(EXACT_SIM_TWO_STAGE_THRESHOLD_TEST_TARGET)

$(FASIM_CIGAR_TEST_TARGET): $(FASIM_CIGAR_TEST_SOURCES) $(FASIM_HEADERS) cuda/prealign_cuda.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(FASIM_CIGAR_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(FASIM_TRANSFERSTRING_TABLE_TEST_TARGET): $(FASIM_TRANSFERSTRING_TABLE_TEST_SOURCES) fasim/rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(FASIM_TRANSFERSTRING_TABLE_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(FASIM_SSW_PROFILE_CACHE_TEST_TARGET): $(FASIM_SSW_PROFILE_CACHE_TEST_SOURCES) fasim/ssw_cpp.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(FASIM_SSW_PROFILE_CACHE_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SSW_AVX2_DIRECT_TEST_TARGET): $(SSW_AVX2_DIRECT_TEST_SOURCES) fasim/ssw.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) -mavx2 $(SSW_AVX2_DIRECT_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(PREALIGN_SHARED_TEST_TARGET): $(PREALIGN_SHARED_TEST_SOURCES) cuda/prealign_cuda.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(PREALIGN_SHARED_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_SCAN_BATCH_TEST_TARGET): $(SIM_SCAN_BATCH_TEST_SOURCES) cuda/sim_scan_cuda.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_SCAN_BATCH_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_TARGET): $(SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_SOURCES) cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_REGION_BUCKETED_TRUE_BATCH_TEST_TARGET): $(SIM_REGION_BUCKETED_TRUE_BATCH_TEST_SOURCES) cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_REGION_BUCKETED_TRUE_BATCH_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_REGION_SCHEDULER_SHAPE_TELEMETRY_TEST_TARGET): $(SIM_REGION_SCHEDULER_SHAPE_TELEMETRY_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h cuda/sim_locate_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_REGION_SCHEDULER_SHAPE_TELEMETRY_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET): $(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_SOURCES) cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_CUDA_PROPOSAL_SELECT_TEST_TARGET): $(SIM_CUDA_PROPOSAL_SELECT_TEST_SOURCES) cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_CUDA_PROPOSAL_SELECT_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_TRACEBACK_CUDA_BATCH_TEST_TARGET): $(SIM_TRACEBACK_CUDA_BATCH_TEST_SOURCES) cuda/sim_traceback_cuda.h cuda/sim_cuda_runtime.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_TRACEBACK_CUDA_BATCH_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_INITIAL_CUDA_MERGE_TEST_TARGET): $(SIM_INITIAL_CUDA_MERGE_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_INITIAL_CUDA_MERGE_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_INITIAL_CONTEXT_APPLY_CHUNK_SKIP_TEST_TARGET): $(SIM_INITIAL_CONTEXT_APPLY_CHUNK_SKIP_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_INITIAL_CONTEXT_APPLY_CHUNK_SKIP_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_INITIAL_CHUNKED_HANDOFF_TEST_TARGET): $(SIM_INITIAL_CHUNKED_HANDOFF_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_INITIAL_CHUNKED_HANDOFF_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_INITIAL_EXACT_FRONTIER_REPLAY_TEST_TARGET): $(SIM_INITIAL_EXACT_FRONTIER_REPLAY_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_INITIAL_EXACT_FRONTIER_REPLAY_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_FRONTIER_EPOCH_ORACLE_TEST_TARGET): $(SIM_FRONTIER_EPOCH_ORACLE_TEST_SOURCES) tests/sim_frontier_epoch_oracle_helpers.h sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_FRONTIER_EPOCH_ORACLE_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_FRONTIER_EPOCH_SHADOW_TEST_TARGET): $(SIM_FRONTIER_EPOCH_SHADOW_TEST_SOURCES) tests/sim_frontier_epoch_oracle_helpers.h sim.h cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h stats.h rules.h
	$(CXX) $(CPPFLAGS) -I$(CUDA_HOME)/include $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_FRONTIER_EPOCH_SHADOW_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_INITIAL_REDUCE_SEMANTICS_TEST_TARGET): $(SIM_INITIAL_REDUCE_SEMANTICS_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_INITIAL_REDUCE_SEMANTICS_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_INITIAL_ORDERED_SEGMENTED_V3_EXACTNESS_TEST_TARGET): $(SIM_INITIAL_ORDERED_SEGMENTED_V3_EXACTNESS_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h cuda/sim_traceback_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) -I$(CUDA_HOME)/include $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_INITIAL_ORDERED_SEGMENTED_V3_EXACTNESS_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_INITIAL_FRONTIER_TRANSDUCER_SHADOW_TEST_TARGET): $(SIM_INITIAL_FRONTIER_TRANSDUCER_SHADOW_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h cuda/sim_traceback_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) -I$(CUDA_HOME)/include $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_INITIAL_FRONTIER_TRANSDUCER_SHADOW_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_INITIAL_FRONTIER_TRANSDUCER_SEGMENTED_SHADOW_TEST_TARGET): $(SIM_INITIAL_FRONTIER_TRANSDUCER_SEGMENTED_SHADOW_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h cuda/sim_traceback_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) -I$(CUDA_HOME)/include $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_INITIAL_FRONTIER_TRANSDUCER_SEGMENTED_SHADOW_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_INITIAL_FRONTIER_COMPACT_TRANSDUCER_ORACLE_TEST_TARGET): $(SIM_INITIAL_FRONTIER_COMPACT_TRANSDUCER_ORACLE_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_INITIAL_FRONTIER_COMPACT_TRANSDUCER_ORACLE_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_INITIAL_CPU_FRONTIER_FAST_APPLY_TEST_TARGET): $(SIM_INITIAL_CPU_FRONTIER_FAST_APPLY_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_INITIAL_CPU_FRONTIER_FAST_APPLY_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_INITIAL_SUMMARY_PACKED_D2H_TEST_TARGET): $(SIM_INITIAL_SUMMARY_PACKED_D2H_TEST_SOURCES) cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h
	$(CXX) $(CPPFLAGS) -I$(CUDA_HOME)/include $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_INITIAL_SUMMARY_PACKED_D2H_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_INITIAL_SUMMARY_HOST_COPY_ELISION_TEST_TARGET): $(SIM_INITIAL_SUMMARY_HOST_COPY_ELISION_TEST_SOURCES) cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h
	$(CXX) $(CPPFLAGS) -I$(CUDA_HOME)/include $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_INITIAL_SUMMARY_HOST_COPY_ELISION_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(CALC_SCORE_CUDA_TELEMETRY_TEST_TARGET): $(CALC_SCORE_CUDA_TELEMETRY_TEST_SOURCES) longtarget.cpp exact_sim.h sim.h stats.h rules.h cuda/calc_score_cuda.h cuda/sim_scan_cuda.h cuda/prealign_cuda.h cuda/sim_traceback_cuda.h cuda/sim_locate_cuda.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(CALC_SCORE_CUDA_TELEMETRY_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_LOCATE_UPDATE_TEST_TARGET): $(SIM_LOCATE_UPDATE_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h cuda/sim_locate_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_LOCATE_UPDATE_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_SAFE_WORKSET_CUDA_TEST_TARGET): $(SIM_SAFE_WORKSET_CUDA_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h cuda/sim_locate_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_SAFE_WORKSET_CUDA_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_SAFE_WINDOW_GEOMETRY_V2_TEST_TARGET): $(SIM_SAFE_WINDOW_GEOMETRY_V2_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h cuda/sim_locate_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_SAFE_WINDOW_GEOMETRY_V2_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_SAFE_WINDOW_FINE_EXECUTION_TEST_TARGET): $(SIM_SAFE_WINDOW_FINE_EXECUTION_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h cuda/sim_locate_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_SAFE_WINDOW_FINE_EXECUTION_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_RESIDENCY_FRONTIER_TEST_TARGET): $(SIM_RESIDENCY_FRONTIER_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h cuda/sim_locate_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_RESIDENCY_FRONTIER_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(EXACT_SIM_TWO_STAGE_THRESHOLD_TEST_TARGET): $(EXACT_SIM_TWO_STAGE_THRESHOLD_TEST_SOURCES) exact_sim.h sim.h cuda/prealign_cuda.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h cuda/sim_locate_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(EXACT_SIM_TWO_STAGE_THRESHOLD_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

check-fasim-cigar: $(FASIM_CIGAR_TEST_TARGET)
	./$(FASIM_CIGAR_TEST_TARGET)

check-prealign-shared: $(PREALIGN_SHARED_TEST_TARGET)
	./$(PREALIGN_SHARED_TEST_TARGET)

check-sim-scan-batch: $(SIM_SCAN_BATCH_TEST_TARGET)
	./$(SIM_SCAN_BATCH_TEST_TARGET)

check-sim-scan-cuda-true-batch-reduce: $(SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_TARGET)
	./$(SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_TARGET)

check-sim-region-bucketed-true-batch: $(SIM_REGION_BUCKETED_TRUE_BATCH_TEST_TARGET)
	./$(SIM_REGION_BUCKETED_TRUE_BATCH_TEST_TARGET)

check-sim-region-scheduler-shape-telemetry: $(SIM_REGION_SCHEDULER_SHAPE_TELEMETRY_TEST_TARGET)
	./$(SIM_REGION_SCHEDULER_SHAPE_TELEMETRY_TEST_TARGET)

check-sim-region-single-request-direct-reduce: $(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET)
	./$(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET)

check-sim-region-direct-reduce-profile-telemetry: $(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET)
	./$(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET)

check-sim-region-direct-reduce-pipeline-telemetry: $(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET)
	./$(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET)

check-sim-region-direct-reduce-fused-dp: $(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET)
	./$(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET)

check-sim-region-direct-reduce-coop-dp: $(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET)
	./$(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET)

check-sim-initial-safe-store-handoff-region-deferred-composition: $(SIM_SAFE_WORKSET_CUDA_TEST_TARGET) $(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET)
	LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_HANDOFF=1 LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE=1 LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS=1 ./$(SIM_SAFE_WORKSET_CUDA_TEST_TARGET)
	LONGTARGET_SIM_CUDA_INITIAL_SAFE_STORE_HANDOFF=1 LONGTARGET_ENABLE_SIM_CUDA_REGION_SINGLE_REQUEST_DIRECT_REDUCE=1 LONGTARGET_ENABLE_SIM_CUDA_REGION_DIRECT_REDUCE_DEFERRED_COUNTS=1 ./$(SIM_REGION_SINGLE_REQUEST_DIRECT_REDUCE_TEST_TARGET)

check-sim-cuda-proposal-select: $(SIM_CUDA_PROPOSAL_SELECT_TEST_TARGET)
	./$(SIM_CUDA_PROPOSAL_SELECT_TEST_TARGET)

check-sim-traceback-cuda-batch: $(SIM_TRACEBACK_CUDA_BATCH_TEST_TARGET)
	./$(SIM_TRACEBACK_CUDA_BATCH_TEST_TARGET)

check-sim-initial-cuda-merge: $(SIM_INITIAL_CUDA_MERGE_TEST_TARGET)
	./$(SIM_INITIAL_CUDA_MERGE_TEST_TARGET)

check-sim-initial-context-apply-chunk-skip: $(SIM_INITIAL_CONTEXT_APPLY_CHUNK_SKIP_TEST_TARGET)
	./$(SIM_INITIAL_CONTEXT_APPLY_CHUNK_SKIP_TEST_TARGET)

check-sim-initial-chunked-handoff: $(SIM_INITIAL_CHUNKED_HANDOFF_TEST_TARGET)
	./$(SIM_INITIAL_CHUNKED_HANDOFF_TEST_TARGET)

check-sim-initial-exact-frontier-replay: $(SIM_INITIAL_EXACT_FRONTIER_REPLAY_TEST_TARGET)
	./$(SIM_INITIAL_EXACT_FRONTIER_REPLAY_TEST_TARGET)

check-sim-initial-cpu-frontier-fast-apply: $(SIM_INITIAL_CPU_FRONTIER_FAST_APPLY_TEST_TARGET)
	./$(SIM_INITIAL_CPU_FRONTIER_FAST_APPLY_TEST_TARGET)

check-sim-frontier-epoch-oracle: $(SIM_FRONTIER_EPOCH_ORACLE_TEST_TARGET)
	./$(SIM_FRONTIER_EPOCH_ORACLE_TEST_TARGET)

check-sim-frontier-epoch-shadow: $(SIM_FRONTIER_EPOCH_SHADOW_TEST_TARGET)
	./$(SIM_FRONTIER_EPOCH_SHADOW_TEST_TARGET)

check-sim-initial-reduce-semantics: $(SIM_INITIAL_REDUCE_SEMANTICS_TEST_TARGET)
	./$(SIM_INITIAL_REDUCE_SEMANTICS_TEST_TARGET)

check-sim-initial-ordered-segmented-v3-exactness: $(SIM_INITIAL_ORDERED_SEGMENTED_V3_EXACTNESS_TEST_TARGET)
	./$(SIM_INITIAL_ORDERED_SEGMENTED_V3_EXACTNESS_TEST_TARGET)

check-sim-initial-frontier-transducer-shadow: $(SIM_INITIAL_FRONTIER_TRANSDUCER_SHADOW_TEST_TARGET)
	./$(SIM_INITIAL_FRONTIER_TRANSDUCER_SHADOW_TEST_TARGET)

check-sim-initial-frontier-transducer-segmented-shadow: $(SIM_INITIAL_FRONTIER_TRANSDUCER_SEGMENTED_SHADOW_TEST_TARGET)
	./$(SIM_INITIAL_FRONTIER_TRANSDUCER_SEGMENTED_SHADOW_TEST_TARGET)

check-sim-initial-frontier-compact-transducer-oracle: $(SIM_INITIAL_FRONTIER_COMPACT_TRANSDUCER_ORACLE_TEST_TARGET)
	./$(SIM_INITIAL_FRONTIER_COMPACT_TRANSDUCER_ORACLE_TEST_TARGET)

check-sim-initial-summary-packed-d2h: $(SIM_INITIAL_SUMMARY_PACKED_D2H_TEST_TARGET)
	./$(SIM_INITIAL_SUMMARY_PACKED_D2H_TEST_TARGET)

check-sim-initial-summary-host-copy-elision: $(SIM_INITIAL_SUMMARY_HOST_COPY_ELISION_TEST_TARGET)
	./$(SIM_INITIAL_SUMMARY_HOST_COPY_ELISION_TEST_TARGET)

check-calc-score-cuda-telemetry: $(CALC_SCORE_CUDA_TELEMETRY_TEST_TARGET)
	./$(CALC_SCORE_CUDA_TELEMETRY_TEST_TARGET)
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) sh ./scripts/check_calc_score_cuda_telemetry.sh

check-calc-score-cuda-v2-shadow:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) sh ./scripts/check_calc_score_cuda_v2_shadow.sh

check-sim-locate-update: $(SIM_LOCATE_UPDATE_TEST_TARGET)
	./$(SIM_LOCATE_UPDATE_TEST_TARGET)

check-sim-safe-workset-cuda: $(SIM_SAFE_WORKSET_CUDA_TEST_TARGET)
	./$(SIM_SAFE_WORKSET_CUDA_TEST_TARGET)

check-sim-safe-window-geometry-v2: $(SIM_SAFE_WINDOW_GEOMETRY_V2_TEST_TARGET)
	./$(SIM_SAFE_WINDOW_GEOMETRY_V2_TEST_TARGET)

check-sim-safe-window-fine-execution: $(SIM_SAFE_WINDOW_FINE_EXECUTION_TEST_TARGET)
	./$(SIM_SAFE_WINDOW_FINE_EXECUTION_TEST_TARGET)

check-sim-residency-frontier: $(SIM_RESIDENCY_FRONTIER_TEST_TARGET)
	./$(SIM_RESIDENCY_FRONTIER_TEST_TARGET)

check-exact-sim-two-stage-threshold: $(EXACT_SIM_TWO_STAGE_THRESHOLD_TEST_TARGET)
	./$(EXACT_SIM_TWO_STAGE_THRESHOLD_TEST_TARGET)

check-benchmark-telemetry:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) sh ./scripts/check_benchmark_telemetry.sh

check-benchmark-worker-telemetry:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) sh ./scripts/check_benchmark_worker_telemetry.sh

check-fasim-throughput-preset:
	$(MAKE) build-fasim-cuda
	BIN=$(CURDIR)/fasim_longtarget_cuda bash ./scripts/check_fasim_throughput_preset.sh

check-benchmark-throughput-comparator:
	$(MAKE) build-cuda build-fasim-cuda
	LONGTARGET_BIN=$(CURDIR)/$(CUDA_TARGET) FASIM_BIN=$(CURDIR)/fasim_longtarget_cuda bash ./scripts/check_benchmark_throughput_comparator.sh

check-fasim-throughput-sweep:
	$(MAKE) build-cuda build-fasim-cuda
	LONGTARGET_BIN=$(CURDIR)/$(CUDA_TARGET) FASIM_BIN=$(CURDIR)/fasim_longtarget_cuda bash ./scripts/check_fasim_throughput_sweep.sh

check-sim-cuda-window-pipeline:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) sh ./scripts/check_sim_cuda_window_pipeline.sh

check-sim-cuda-initial-proposal-online-exactness:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) sh ./scripts/check_sim_cuda_initial_proposal_online_exactness.sh

check-sim-cuda-initial-proposal-v2-exactness:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) sh ./scripts/check_sim_cuda_initial_proposal_v2_exactness.sh

check-sim-cuda-window-pipeline-overlap:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) sh ./scripts/check_sim_cuda_window_pipeline_overlap.sh

check-project-whole-genome-runtime:
	python3 ./scripts/project_whole_genome_runtime.py --help >/dev/null
	sh ./scripts/check_project_whole_genome_runtime.sh

check-make-anchor-shards:
	python3 ./scripts/make_anchor_shards.py --help >/dev/null
	bash ./scripts/check_make_anchor_shards.sh

check-summarize-throughput-frontier:
	python3 ./scripts/summarize_throughput_frontier.py --help >/dev/null
	bash ./scripts/check_summarize_throughput_frontier.sh

check-two-stage-frontier-sweep:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) python3 ./scripts/benchmark_two_stage_frontier_sweep.py --help >/dev/null
	LONGTARGET_BIN=$(CURDIR)/$(CUDA_TARGET) bash ./scripts/check_two_stage_frontier_sweep.sh

check-two-stage-threshold-modes:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) python3 ./scripts/benchmark_two_stage_threshold_modes.py --help >/dev/null
	LONGTARGET_BIN=$(CURDIR)/$(CUDA_TARGET) bash ./scripts/check_two_stage_threshold_modes.sh

check-two-stage-task-rerun-runtime:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) python3 ./scripts/benchmark_two_stage_threshold_modes.py --help >/dev/null
	LONGTARGET_BIN=$(CURDIR)/$(CUDA_TARGET) bash ./scripts/check_two_stage_task_rerun_runtime.sh

check-two-stage-threshold-heavy-microanchors:
	$(MAKE) build-cuda
	TARGET=$(CURDIR)/$(CUDA_TARGET) python3 ./scripts/benchmark_two_stage_threshold_heavy_microanchors.py --help >/dev/null
	LONGTARGET_BIN=$(CURDIR)/$(CUDA_TARGET) bash ./scripts/check_two_stage_threshold_heavy_microanchors.sh

check-compare-two-stage-panel-summaries:
	python3 ./scripts/compare_two_stage_panel_summaries.py --help >/dev/null
	bash ./scripts/check_compare_two_stage_panel_summaries.sh

check-summarize-two-stage-panel-decision:
	python3 ./scripts/summarize_two_stage_panel_decision.py --help >/dev/null
	bash ./scripts/check_summarize_two_stage_panel_decision.sh

check-rerun-two-stage-panel-with-candidate-env:
	python3 ./scripts/rerun_two_stage_panel_with_candidate_env.py --help >/dev/null
	bash ./scripts/check_rerun_two_stage_panel_with_candidate_env.sh

check-rerun-two-stage-panel-task-rerun-runtime:
	python3 ./scripts/rerun_two_stage_panel_task_rerun_runtime.py --help >/dev/null
	bash ./scripts/check_rerun_two_stage_panel_task_rerun_runtime.sh

check-analyze-two-stage-selector-candidate-classes:
	python3 ./scripts/analyze_two_stage_selector_candidate_classes.py --help >/dev/null
	bash ./scripts/check_analyze_two_stage_selector_candidate_classes.sh

check-replay-two-stage-non-empty-candidate-classes:
	python3 ./scripts/replay_two_stage_non_empty_candidate_classes.py --help >/dev/null
	bash ./scripts/check_replay_two_stage_non_empty_candidate_classes.sh

check-analyze-two-stage-task-ambiguity:
	python3 ./scripts/analyze_two_stage_task_ambiguity.py --help >/dev/null
	bash ./scripts/check_analyze_two_stage_task_ambiguity.sh

check-replay-two-stage-task-level-rerun:
	python3 ./scripts/replay_two_stage_task_level_rerun.py --help >/dev/null
	bash ./scripts/check_replay_two_stage_task_level_rerun.sh

check-search-two-stage-task-trigger-rankings:
	python3 ./scripts/search_two_stage_task_trigger_rankings.py --help >/dev/null
	bash ./scripts/check_search_two_stage_task_trigger_rankings.sh

check-summarize-two-stage-frontier:
	python3 ./scripts/summarize_two_stage_frontier.py --help >/dev/null
	bash ./scripts/check_summarize_two_stage_frontier.sh

check-sim-cuda-region-docs:
	sh ./scripts/check_sim_cuda_region_docs.sh

check-longtarget-lite-output:
	$(MAKE) build
	bash ./scripts/check_longtarget_lite_output.sh

check-fasim-sharded-runner:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/fasim_longtarget_x86 bash ./scripts/check_fasim_sharded_runner.sh

check-fasim-sharded-scheduler:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/fasim_longtarget_x86 bash ./scripts/check_fasim_sharded_scheduler.sh

check-fasim-sharded-runner-resume:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/fasim_longtarget_x86 bash ./scripts/check_fasim_sharded_runner_resume.sh

check-fasim-sharded-cpu-affinity:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/fasim_longtarget_x86 bash ./scripts/check_fasim_sharded_cpu_affinity.sh

check-fasim-sharded-worker-readiness-matrix:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/fasim_longtarget_x86 bash ./scripts/check_fasim_sharded_worker_readiness_matrix.sh

check-fasim-shard-balance:
	bash ./scripts/check_fasim_shard_balance.sh

check-fasim-sharded-straggler-analysis:
	bash ./scripts/check_fasim_sharded_straggler_analysis.sh

check-fasim-ssw-profile-cache-env:
	BIN=$(CURDIR)/fasim_longtarget_cuda bash ./scripts/check_fasim_ssw_profile_cache_env.sh

check-fasim-exact-column-extend-batch-env:
	BIN=$(CURDIR)/fasim_longtarget_cuda bash ./scripts/check_fasim_exact_column_extend_batch_env.sh

check-fasim-exact-column-extend-batch-digest:
	BIN=$(CURDIR)/fasim_longtarget_cuda bash ./scripts/check_fasim_exact_column_extend_batch_digest.sh

check-fasim-exact-column-multigpu-guard:
	BIN=$(CURDIR)/fasim_longtarget_cuda bash ./scripts/check_fasim_exact_column_multigpu_guard.sh

check-fasim-gpu-dp-column-auto-digest:
	BIN=$(CURDIR)/fasim_longtarget_cuda CPU_BIN=$(CURDIR)/fasim_longtarget_x86 bash ./scripts/check_fasim_gpu_dp_column_auto_digest.sh

check-fasim-ssw-profile-context-env:
	BIN=$(CURDIR)/fasim_longtarget_cuda bash ./scripts/check_fasim_ssw_profile_context_env.sh

check-fasim-ssw-profile-context-digest:
	BIN=$(CURDIR)/fasim_longtarget_cuda bash ./scripts/check_fasim_ssw_profile_context_digest.sh

check-fasim-ssw-avx2-direct:
	$(MAKE) build-ssw-avx2-direct-test
	FASIM_SSW_AVX2=1 ./tests/test_ssw_avx2_direct

check-fasim-ssw-avx2-digest:
	mkdir -p $(CURDIR)/.tmp/fasim_ssw_avx2_digest
	$(MAKE) build-fasim
	$(MAKE) FASIM_SIMD_FLAGS=-mavx2 FASIM_TARGET=.tmp/fasim_ssw_avx2_digest/fasim_longtarget_x86_avx2 build-fasim
	CPU_BIN=$(CURDIR)/fasim_longtarget_x86 AVX2_BIN=$(CURDIR)/.tmp/fasim_ssw_avx2_digest/fasim_longtarget_x86_avx2 bash ./scripts/check_fasim_ssw_avx2_digest.sh

check-fasim-gasal2-longtarget-bridge-digest:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_bridge bash ./scripts/check_fasim_gasal2_longtarget_bridge_digest.sh

check-fasim-gasal2-gpu-scoreinfo-top5:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_gpu_scoreinfo_top5.sh

check-fasim-gasal2-scoreinfo-prune-top5-matrix:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct MATRIX_PRESET=examples bash ./scripts/check_fasim_gasal2_scoreinfo_prune_top5_matrix.sh

check-fasim-gasal2-scoreinfo-prune-top5-chr22-2mb:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct MATRIX_PRESET=chr22_2mb bash ./scripts/check_fasim_gasal2_scoreinfo_prune_top5_matrix.sh

check-fasim-sharded-gasal2-top5-prune-runner:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_sharded_gasal2_top5_prune_runner.sh

check-fasim-gasal2-sharded-characterization-env:
	bash ./scripts/check_fasim_gasal2_sharded_characterization_env.sh

characterize-fasim-gasal2-prealign-max-tasks-probe:
	bash ./scripts/characterize_fasim_gasal2_prealign_max_tasks_probe.sh

check-fasim-gasal2-prealign-max-tasks-probe:
	bash ./scripts/check_fasim_gasal2_prealign_max_tasks_probe.sh

check-fasim-gasal2-prealign-max-tasks-chr21-chr22-result:
	python3 ./scripts/check_fasim_gasal2_prealign_max_tasks_chr21_chr22_result.py

check-fasim-gasal2-scoreinfo-prune-sweep:
	bash ./scripts/check_fasim_gasal2_scoreinfo_prune_sweep.sh

check-fasim-exact-scoreinfo-gpu-max-per-task-sweep:
	bash ./scripts/check_fasim_exact_scoreinfo_gpu_max_per_task_sweep.sh

check-fasim-exact-scoreinfo-gpu-pruned-output:
	bash ./scripts/check_fasim_exact_scoreinfo_gpu_pruned_output.sh

characterize-fasim-exact-scoreinfo-gpu-column-pruned-output:
	BUILD_BIN=1 BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_exact_scoreinfo_gpu_column_pruned_output.sh

check-fasim-exact-scoreinfo-gpu-column-pruned-output:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_exact_scoreinfo_gpu_column_pruned_output.sh

characterize-fasim-exact-scoreinfo-gpu-column-pruned-output-matrix:
	BUILD_BIN=1 BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_exact_scoreinfo_gpu_column_pruned_output_matrix.sh

check-fasim-exact-scoreinfo-gpu-column-pruned-output-matrix:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_exact_scoreinfo_gpu_column_pruned_output_matrix.sh

characterize-fasim-gasal2-column-pruned-preset-top5-matrix:
	BUILD_BIN=1 BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_column_pruned_preset_top5_matrix.sh

check-fasim-gasal2-column-pruned-preset-top5-matrix:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_column_pruned_preset_top5_matrix.sh

check-fasim-gasal2-top5-binary-guard:
	BIN=$(CURDIR)/fasim_longtarget_cuda bash ./scripts/check_fasim_gasal2_top5_binary_guard.sh

check-fasim-gasal2-top5-lowercase-input:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_top5_lowercase_input.sh

check-fasim-gasal2-formal-preset-examples:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_formal_preset_examples.sh

check-fasim-gasal2-reproducible-setup:
	bash ./scripts/check_fasim_gasal2_reproducible_setup.sh

check-fasim-gasal2-long-query-phase0:
	$(MAKE) check-fasim-gasal2-reproducible-setup
	$(MAKE) check-sample
	$(MAKE) check-fasim-tfo-archive-integrity-parser
	$(MAKE) check-fasim-gasal2-archive-manifest-parser
	$(MAKE) check-fasim-lite-full-equivalence
	$(MAKE) check-fasim-gasal2-top5-output-contract
	$(MAKE) check-fasim-gasal2-short-query-top5-tfo-contract
	$(MAKE) check-fasim-gasal2-archive-first-output \
		WORK=$(CURDIR)/.tmp/check_fasim_gasal2_long_query_phase0_archive \
		TARGET=$(CURDIR)/.tmp/fasim_gasal2_chr22_slice_10m_12m.fa \
		RNA=$(CURDIR)/H19.fa
	PHASE0_ARCHIVE_SUMMARY=$(CURDIR)/.tmp/check_fasim_gasal2_long_query_phase0_archive/summary.txt \
		bash ./scripts/check_fasim_gasal2_long_query_phase0.sh

.PHONY: check-fasim-gasal2-long-query-phase0

check-fasim-gasal2-segmented-archive-first:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct \
	WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_segmented_archive_first) \
	bash ./scripts/check_fasim_gasal2_segmented_archive_first.sh

.PHONY: check-fasim-gasal2-segmented-archive-first

characterize-fasim-gasal2-segment-ownership-h19:
	FASIM_GASAL2_SEGMENT_OWNERSHIP_SHADOW=1 \
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct \
	WORK=$(or $(WORK),$(CURDIR)/.tmp/characterize_fasim_segment_ownership_h19) \
	python3 ./scripts/characterize_fasim_segment_ownership_h19.py

check-fasim-gasal2-segment-ownership:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct \
	WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_segment_ownership) \
	bash ./scripts/check_fasim_gasal2_segment_ownership.sh

.PHONY: characterize-fasim-gasal2-segment-ownership-h19 check-fasim-gasal2-segment-ownership

check-fasim-gasal2-multi-segment-context-phase3:
	WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_multi_segment_context_phase3) \
	bash ./scripts/check_fasim_gasal2_multi_segment_context_phase3.sh

.PHONY: check-fasim-gasal2-multi-segment-context-phase3

check-fasim-gasal2-exact-task-compaction-shadow:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct \
	WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_exact_task_compaction_shadow) \
	bash ./scripts/check_fasim_gasal2_exact_task_compaction_shadow.sh

check-fasim-gasal2-exact-scoreinfo-pruned-full-output:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct \
	WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_exact_scoreinfo_pruned_full_output) \
	bash ./scripts/check_fasim_gasal2_exact_scoreinfo_pruned_full_output.sh

characterize-fasim-gasal2-exact-column-long-query:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct \
	WORK=$(or $(WORK),$(CURDIR)/.tmp/characterize_fasim_gasal2_exact_column_long_query_exact_pruned) \
	bash ./scripts/characterize_fasim_gasal2_exact_column_long_query.sh

check-fasim-gasal2-exact-column-phase5:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct \
	WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_exact_column_phase5) \
	bash ./scripts/check_fasim_gasal2_exact_column_phase5.sh

characterize-fasim-gasal2-traceback-certificate-phase6:
	WORK=$(or $(WORK),$(CURDIR)/.tmp/phase6_traceback_certificate) \
	bash ./scripts/characterize_fasim_gasal2_traceback_certificate_phase6.sh

check-fasim-gasal2-traceback-certificate-unit:
	bash ./scripts/check_fasim_gasal2_traceback_certificate_unit.sh

check-fasim-gasal2-traceback-certificate-shadow-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 \
	bash ./scripts/check_fasim_gasal2_traceback_certificate_shadow_smoke.sh

check-fasim-gasal2-traceback-certificate-phase6:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct \
	WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_traceback_certificate_phase6) \
	bash ./scripts/check_fasim_gasal2_traceback_certificate_phase6.sh

characterize-fasim-gasal2-long-query-integrated-phase7:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct \
	WORK=$(or $(WORK),$(CURDIR)/.tmp/phase7_gasal2_long_query_integrated) \
	bash ./scripts/characterize_fasim_gasal2_long_query_integrated_phase7.sh

check-fasim-gasal2-long-query-integrated-unit:
	python3 ./tests/check_characterize_fasim_gasal2_segmented_archive_first_runner.py
	python3 ./tests/check_compare_fasim_gasal2_long_query_integrated.py
	python3 ./tests/check_summarize_fasim_gasal2_long_query_integrated.py

check-fasim-gasal2-long-query-integrated-phase7:
	WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_long_query_integrated_phase7) \
	bash ./scripts/check_fasim_gasal2_long_query_integrated_phase7.sh

check-fasim-gasal2-long-query-final:
	WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_long_query_final) \
	bash ./scripts/check_fasim_gasal2_long_query_final.sh

check-fasim-gasal2-paper-phase0:
	$(MAKE) check-fasim-gasal2-long-query-final
	bash ./scripts/check_fasim_gasal2_paper_phase0.sh

check-fasim-gasal2-paper-phase1:
	$(MAKE) check-fasim-gasal2-paper-phase0
	bash ./scripts/check_fasim_gasal2_paper_phase1.sh

check-fasim-gasal2-paper-phase2:
	$(MAKE) check-fasim-gasal2-paper-phase1
	bash ./scripts/check_fasim_gasal2_paper_phase2.sh

check-fasim-gasal2-paper-phase3:
	$(MAKE) check-fasim-gasal2-paper-phase2
	bash ./scripts/check_fasim_gasal2_paper_phase3.sh

check-fasim-gasal2-paper-phase4:
	$(MAKE) check-fasim-gasal2-paper-phase3
	bash ./scripts/check_fasim_gasal2_paper_phase4.sh

paper-source-data:
	python3 ./reproduce/collect_results.py
	python3 ./reproduce/analyze_results.py
	python3 ./reproduce/freeze_results.py

check-fasim-gasal2-paper-phase5:
	$(MAKE) check-fasim-gasal2-paper-phase4
	bash ./scripts/check_fasim_gasal2_paper_phase5.sh

paper-figures:
	python3 ./reproduce/render_figures.py

check-fasim-gasal2-paper-phase6:
	$(MAKE) check-fasim-gasal2-paper-phase5
	bash ./scripts/check_fasim_gasal2_paper_phase6.sh

check-fasim-gasal2-paper-reproduction:
	python3 ./tests/check_fasim_gasal2_paper_reproduction.py
	python3 -m py_compile ./reproduce/prepare_inputs.py
	bash ./reproduce/check_reproduction.sh

check-fasim-gasal2-paper-phase7:
	$(MAKE) check-fasim-gasal2-paper-phase6
	bash ./scripts/check_fasim_gasal2_paper_phase7.sh

.PHONY: check-fasim-gasal2-exact-task-compaction-shadow \
	check-fasim-gasal2-exact-scoreinfo-pruned-full-output \
	characterize-fasim-gasal2-exact-column-long-query \
	check-fasim-gasal2-exact-column-phase5 \
	characterize-fasim-gasal2-traceback-certificate-phase6 \
	check-fasim-gasal2-traceback-certificate-unit \
	check-fasim-gasal2-traceback-certificate-shadow-smoke \
	check-fasim-gasal2-traceback-certificate-phase6 \
	characterize-fasim-gasal2-long-query-integrated-phase7 \
	check-fasim-gasal2-long-query-integrated-unit \
	check-fasim-gasal2-long-query-integrated-phase7 \
	check-fasim-gasal2-long-query-final \
	check-fasim-gasal2-paper-phase0 \
	check-fasim-gasal2-paper-phase1 \
	check-fasim-gasal2-paper-phase2 \
	check-fasim-gasal2-paper-phase3 \
	check-fasim-gasal2-paper-phase4 \
	check-fasim-gasal2-paper-phase5 \
	check-fasim-gasal2-paper-phase6 \
	check-fasim-gasal2-paper-reproduction \
	check-fasim-gasal2-paper-phase7 \
	paper-source-data \
	paper-figures

check-fasim-gasal2-short-query-top5-readiness:
	bash ./scripts/check_fasim_gasal2_short_query_top5_readiness.sh

check-fasim-gasal2-short-query-top5-tfo-contract:
	bash ./scripts/check_fasim_gasal2_short_query_top5_tfo_contract.sh

KCNQ1OT1_FASTA ?= $(CURDIR)/.tmp/fasim_gasal2_query_inputs/KCNQ1OT1_ENST00000597346.fa

characterize-fasim-gasal2-short-query-generalization-panel:
	KCNQ1OT1_FASTA="$(KCNQ1OT1_FASTA)" \
	bash ./scripts/characterize_fasim_gasal2_short_query_generalization_panel.sh

check-fasim-gasal2-short-query-generalization-panel-result:
	bash ./scripts/check_fasim_gasal2_short_query_generalization_panel_result.sh

.PHONY: characterize-fasim-gasal2-short-query-generalization-panel check-fasim-gasal2-short-query-generalization-panel-result

characterize-fasim-gasal2-segmented-query-h19-control:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_segmented_query_h19_control.sh

check-fasim-gasal2-segmented-query-h19-control-result:
	bash ./scripts/check_fasim_gasal2_segmented_query_h19_control_result.sh

.PHONY: characterize-fasim-gasal2-segmented-query-h19-control check-fasim-gasal2-segmented-query-h19-control-result

characterize-fasim-gasal2-segmented-query-kcnq1ot1-pilot:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct KCNQ1OT1_FASTA="$(KCNQ1OT1_FASTA)" bash ./scripts/characterize_fasim_gasal2_segmented_query_kcnq1ot1_pilot.sh

check-fasim-gasal2-segmented-query-kcnq1ot1-pilot-result:
	bash ./scripts/check_fasim_gasal2_segmented_query_kcnq1ot1_pilot_result.sh

.PHONY: characterize-fasim-gasal2-segmented-query-kcnq1ot1-pilot check-fasim-gasal2-segmented-query-kcnq1ot1-pilot-result

check-fasim-gasal2-segmented-query-kcnq1ot1-target-scope-result:
	bash ./scripts/check_fasim_gasal2_segmented_query_kcnq1ot1_target_scope_result.sh

.PHONY: check-fasim-gasal2-segmented-query-kcnq1ot1-target-scope-result

check-fasim-gasal2-segmented-query-kcnq1ot1-coverage-ladder-result:
	bash ./scripts/check_fasim_gasal2_segmented_query_kcnq1ot1_coverage_ladder_result.sh

.PHONY: check-fasim-gasal2-segmented-query-kcnq1ot1-coverage-ladder-result

check-fasim-gasal2-formal-makefile-gate:
	bash ./scripts/check_fasim_gasal2_formal_makefile_gate.sh

check-fasim-gasal2-top5-scoreinfo-milestone:
	bash ./scripts/check_fasim_gasal2_top5_scoreinfo_milestone.sh

check-fasim-gasal2-top5-scoreinfo-milestone-result:
	REQUIRE_RESULT=1 bash ./scripts/check_fasim_gasal2_top5_scoreinfo_milestone.sh

check-fasim-gasal2-top5-scoreinfo-meg3-grouped-result:
	bash ./scripts/check_fasim_gasal2_top5_scoreinfo_meg3_grouped_result.sh

check-fasim-gasal2-top5-wrapper-meg3-grouped-result:
	bash ./scripts/check_fasim_gasal2_top5_wrapper_meg3_grouped_result.sh

check-fasim-gasal2-scoreinfo-current-state: check-fasim-gasal2-formal-makefile-gate check-fasim-gasal2-top5-scoreinfo-milestone check-fasim-gasal2-top5-scoreinfo-milestone-result check-fasim-gasal2-top5-scoreinfo-meg3-grouped-result check-fasim-gasal2-top5-wrapper-meg3-grouped-result check-fasim-sharded-gasal2-top5-prune-runner check-fasim-gasal2-column-pruned-preset-top5-matrix check-fasim-gasal2-top5-output-contract check-fasim-gasal2-top5-activation-contract check-fasim-gasal2-topk-lite-wrapper-contract check-fasim-gasal2-top5-lowercase-input check-fasim-gasal2-top5-binary-guard check-fasim-gasal2-formal-preset-examples check-fasim-top5-gasal2-gpu-scoreinfo-default-off check-fasim-top5-gasal2-gpu-scoreinfo-env check-fasim-exact-scoreinfo-gpu-examples-gate check-fasim-gasal2-long-query-boundary check-fasim-gasal2-long-query-segmented-no-last-scaling-result check-fasim-gasal2-long-query-current-stop check-fasim-gasal2-long-query-next-architecture-plan check-fasim-gasal2-long-query-next-architecture-decision check-fasim-long-query-streaming-scoreinfo-design check-fasim-long-query-streaming-scoreinfo-shared-smem-boundary check-fasim-long-query-streaming-scoreinfo-fused-minscore-design check-fasim-long-query-streaming-scoreinfo-fused-minscore-prototype check-fasim-long-query-streaming-scoreinfo-fused-minscore-boundary check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design check-fasim-long-query-streaming-scoreinfo-shadow-skeleton check-fasim-long-query-streaming-scoreinfo-shadow-active check-fasim-long-query-streaming-scoreinfo-shadow-mismatch-detail check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte-shared check-fasim-long-query-streaming-scoreinfo-shadow-gpu-minscore check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-shadow check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-trust check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-runner check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first64 check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first128 check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256 check-fasim-long-query-streaming-scoreinfo-shadow-gpu-minscore-hot check-fasim-long-query-streaming-scoreinfo-realpath-prototype check-fasim-long-query-streaming-scoreinfo-realpath-trust check-fasim-long-query-streaming-scoreinfo-trust-targets check-fasim-long-query-streaming-scoreinfo-trust-runner check-fasim-long-query-streaming-scoreinfo-trust-group32-runner check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner check-fasim-long-query-streaming-scoreinfo-trust-group32-segmented-probe-runner check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real check-fasim-long-query-streaming-scoreinfo-neat1-audited-runner-real check-fasim-long-query-streaming-scoreinfo-neat1-runtime-boundary check-fasim-gasal2-neat1-speed-ceiling check-fasim-gasal2-neat1-next-architecture-requirements check-fasim-gasal2-broad-path-architecture-gate check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan check-fasim-gasal2-broad-scoreinfo-consumer-shadow-env check-fasim-gasal2-broad-scoreinfo-consumer-triplex-export check-fasim-gasal2-broad-scoreinfo-attempt-planner check-fasim-gasal2-broad-replacement-consumer-shadow check-fasim-gasal2-broad-neat1-first64-result check-fasim-gasal2-attempt-consumer-shadow-plan check-fasim-gasal2-attempt-consumer-shadow-env check-fasim-gasal2-attempt-consumer-shadow-selection check-fasim-gasal2-attempt-consumer-shadow-runtime-smoke check-fasim-gasal2-emission-only-consumer-shadow-plan check-fasim-gasal2-emission-only-consumer-shadow-env check-fasim-gasal2-emission-only-consumer-neat1-first64-result check-fasim-gasal2-emission-only-consumer-debug check-fasim-gasal2-scoring-parameter-matrix check-fasim-gasal2-cpu-authority-candidate-coverage-plan check-fasim-gasal2-cpu-authority-candidate-coverage-env check-fasim-gasal2-cpu-authority-candidate-coverage-characterization check-fasim-gasal2-replacement-consumer-shadow-requirements check-fasim-gasal2-replacement-consumer-shadow-env check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke check-fasim-gasal2-score-prepass-state-machine-consumer check-fasim-gasal2-score-prepass-state-machine-consumer-env check-fasim-gasal2-score-prepass-state-machine-consumer-runtime-smoke check-fasim-gasal2-score-prepass-state-machine-consumer-segmented-runtime-smoke check-fasim-gasal2-score-prepass-state-machine-characterization check-fasim-gasal2-score-prepass-state-machine-trust check-fasim-gasal2-score-prepass-state-machine-trust-runtime-smoke check-fasim-gasal2-score-prepass-state-machine-stop check-fasim-long-query-streaming-scoreinfo-trust-runner-real check-fasim-gasal2-long-query-exact-tile-oracle-export check-fasim-gasal2-long-query-exact-tile-descriptors check-fasim-gasal2-long-query-exact-tile-candidate-equivalence-result check-fasim-gasal2-long-query-exact-tile-overlap-result check-fasim-long-query-exact-column-scoreinfo-shadow check-fasim-long-query-exact-column-scoreinfo-shadow-smem-optin check-fasim-gasal2-single-pass-topn-sweep check-fasim-gasal2-top5-broader-validation check-fasim-gasal2-top5-product-readiness check-fasim-gasal2-top5-recommended-runtime check-fasim-gasal2-top5-scoped-completion-candidate check-fasim-gasal2-top5-release-smoke check-fasim-gasal2-scoreinfo-scoped-milestone check-fasim-gasal2-scoreinfo-scoped-milestone-rollup check-fasim-gasal2-scoreinfo-scoped-release-smoke check-fasim-gasal2-scoreinfo-completion-gap check-fasim-gasal2-full-goal-decision check-fasim-lite-full-equivalence check-fasim-gasal2-malat1-lite-equivalence-evidence check-fasim-gasal2-malat1-tfosorted-equivalence-evidence check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full check-fasim-gasal2-malat1-two-contract-product-readiness check-fasim-gasal2-malat1-two-contract-recommended-runtime check-fasim-gasal2-malat1-no-probe-two-contract-runtime check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64 check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128 check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256 check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted
	bash ./scripts/check_fasim_gasal2_scoreinfo_current_state.sh

check-fasim-gasal2-neat1-speed-ceiling:
	bash ./scripts/check_fasim_gasal2_neat1_speed_ceiling.sh

check-fasim-gasal2-neat1-next-architecture-requirements:
	bash ./scripts/check_fasim_gasal2_neat1_next_architecture_requirements.sh

check-fasim-gasal2-broad-path-architecture-gate:
	bash ./scripts/check_fasim_gasal2_broad_path_architecture_gate.sh

check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan:
	bash ./scripts/check_fasim_gasal2_broad_co_designed_scoreinfo_consumer_plan.sh

check-fasim-gasal2-broad-scoreinfo-consumer-shadow-env:
	bash ./scripts/check_fasim_gasal2_broad_scoreinfo_consumer_shadow_env.sh

check-fasim-gasal2-broad-scoreinfo-consumer-triplex-export:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_broad_scoreinfo_consumer_triplex_export.sh

check-fasim-gasal2-broad-scoreinfo-attempt-planner:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_broad_scoreinfo_attempt_planner.sh

check-fasim-gasal2-broad-replacement-consumer-shadow:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_broad_replacement_consumer_shadow.sh

characterize-fasim-gasal2-broad-neat1-first64:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_gasal2_broad_neat1_first64.sh

check-fasim-gasal2-broad-neat1-first64-result:
	bash ./scripts/check_fasim_gasal2_broad_neat1_first64_result.sh

check-fasim-gasal2-attempt-consumer-shadow-plan:
	bash ./scripts/check_fasim_gasal2_attempt_consumer_shadow_plan.sh

check-fasim-gasal2-attempt-consumer-shadow-env:
	bash ./scripts/check_fasim_gasal2_attempt_consumer_shadow_env.sh

check-fasim-gasal2-attempt-consumer-shadow-selection:
	bash ./scripts/check_fasim_gasal2_attempt_consumer_shadow_selection.sh

check-fasim-gasal2-attempt-consumer-shadow-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_attempt_consumer_shadow_runtime_smoke.sh

characterize-fasim-gasal2-attempt-consumer-neat1-first64:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_gasal2_attempt_consumer_neat1_first64.sh

check-fasim-gasal2-attempt-consumer-neat1-first64-result:
	bash ./scripts/check_fasim_gasal2_attempt_consumer_neat1_first64_result.sh

check-fasim-gasal2-emission-only-consumer-shadow-plan:
	bash ./scripts/check_fasim_gasal2_emission_only_consumer_shadow_plan.sh

check-fasim-gasal2-emission-only-consumer-shadow-env:
	bash ./scripts/check_fasim_gasal2_emission_only_consumer_shadow_env.sh

check-fasim-gasal2-emission-only-consumer-shadow-debug:
	bash ./scripts/check_fasim_gasal2_emission_only_consumer_shadow_debug.sh

check-fasim-gasal2-emission-only-consumer-shadow-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_emission_only_consumer_shadow_runtime_smoke.sh

check-fasim-gasal2-emission-only-consumer-shadow-first1-clean:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_emission_only_consumer_shadow_first1_clean.sh

characterize-fasim-gasal2-emission-only-consumer-neat1-first64:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_gasal2_emission_only_consumer_neat1_first64.sh

check-fasim-gasal2-emission-only-consumer-neat1-first64-result:
	bash ./scripts/check_fasim_gasal2_emission_only_consumer_neat1_first64_result.sh

check-fasim-gasal2-emission-only-consumer-debug:
	bash ./scripts/check_fasim_gasal2_emission_only_consumer_debug.sh

check-fasim-gasal2-scoring-parameter-matrix:
	bash ./scripts/check_fasim_gasal2_scoring_parameter_matrix.sh

check-fasim-gasal2-cpu-authority-candidate-coverage-plan:
	bash ./scripts/check_fasim_gasal2_cpu_authority_candidate_coverage_plan.sh

check-fasim-gasal2-cpu-authority-candidate-coverage-env:
	bash ./scripts/check_fasim_gasal2_cpu_authority_candidate_coverage_env.sh

check-fasim-gasal2-cpu-authority-candidate-coverage-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_cpu_authority_candidate_coverage_runtime_smoke.sh

characterize-fasim-gasal2-cpu-authority-candidate-coverage:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_gasal2_cpu_authority_candidate_coverage.sh

check-fasim-gasal2-cpu-authority-candidate-coverage-result:
	bash ./scripts/check_fasim_gasal2_cpu_authority_candidate_coverage_result.sh

check-fasim-gasal2-cpu-authority-candidate-coverage-characterization:
	bash ./scripts/check_fasim_gasal2_cpu_authority_candidate_coverage_characterization.sh

.PHONY: check-fasim-gasal2-broad-path-architecture-gate check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan check-fasim-gasal2-broad-scoreinfo-consumer-shadow-env check-fasim-gasal2-broad-scoreinfo-consumer-triplex-export check-fasim-gasal2-broad-scoreinfo-attempt-planner check-fasim-gasal2-broad-replacement-consumer-shadow characterize-fasim-gasal2-broad-neat1-first64 check-fasim-gasal2-broad-neat1-first64-result check-fasim-gasal2-attempt-consumer-shadow-plan check-fasim-gasal2-attempt-consumer-shadow-env check-fasim-gasal2-attempt-consumer-shadow-selection check-fasim-gasal2-attempt-consumer-shadow-runtime-smoke characterize-fasim-gasal2-attempt-consumer-neat1-first64 check-fasim-gasal2-attempt-consumer-neat1-first64-result check-fasim-gasal2-emission-only-consumer-shadow-plan check-fasim-gasal2-emission-only-consumer-shadow-env check-fasim-gasal2-emission-only-consumer-shadow-debug check-fasim-gasal2-emission-only-consumer-shadow-runtime-smoke check-fasim-gasal2-emission-only-consumer-shadow-first1-clean characterize-fasim-gasal2-emission-only-consumer-neat1-first64 check-fasim-gasal2-emission-only-consumer-neat1-first64-result check-fasim-gasal2-emission-only-consumer-debug check-fasim-gasal2-scoring-parameter-matrix check-fasim-gasal2-cpu-authority-candidate-coverage-plan check-fasim-gasal2-cpu-authority-candidate-coverage-env check-fasim-gasal2-cpu-authority-candidate-coverage-runtime-smoke characterize-fasim-gasal2-cpu-authority-candidate-coverage check-fasim-gasal2-cpu-authority-candidate-coverage-result check-fasim-gasal2-cpu-authority-candidate-coverage-characterization check-fasim-long-query-streaming-scoreinfo-shared-smem-boundary

check-fasim-gasal2-replacement-consumer-shadow-requirements:
	bash ./scripts/check_fasim_gasal2_replacement_consumer_shadow_requirements.sh

check-fasim-gasal2-replacement-consumer-shadow-env:
	bash ./scripts/check_fasim_gasal2_replacement_consumer_shadow_env.sh

check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_replacement_consumer_shadow_runtime_smoke.sh

check-fasim-gasal2-score-prepass-state-machine-consumer:
	bash ./scripts/check_fasim_gasal2_score_prepass_state_machine_consumer.sh

check-fasim-gasal2-score-prepass-state-machine-consumer-env:
	bash ./scripts/check_fasim_gasal2_score_prepass_state_machine_consumer_env.sh

check-fasim-gasal2-score-prepass-state-machine-consumer-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_score_prepass_state_machine_consumer_runtime_smoke.sh

check-fasim-gasal2-score-prepass-state-machine-consumer-segmented-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_score_prepass_state_machine_consumer_segmented_runtime_smoke.sh

check-fasim-gasal2-score-prepass-state-machine-characterization:
	bash ./scripts/check_fasim_gasal2_score_prepass_state_machine_characterization.sh

check-fasim-gasal2-score-prepass-state-machine-trust:
	bash ./scripts/check_fasim_gasal2_score_prepass_state_machine_trust.sh

check-fasim-gasal2-score-prepass-state-machine-trust-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_score_prepass_state_machine_trust_runtime_smoke.sh

check-fasim-gasal2-score-prepass-state-machine-stop:
	bash ./scripts/check_fasim_gasal2_score_prepass_state_machine_stop.sh

check-fasim-long-query-streaming-scoreinfo-trust-runner:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_trust_runner.sh

check-fasim-long-query-streaming-scoreinfo-trust-group32-runner:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_trust_group32_runner.sh

check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_trust_group32_audited_runner.sh

check-fasim-long-query-streaming-scoreinfo-trust-group32-segmented-probe-runner:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_trust_group32_segmented_probe_runner.sh

check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_trust_group32_audited_runner_real.sh

check-fasim-long-query-streaming-scoreinfo-neat1-audited-runner-real:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_neat1_audited_runner_real.sh

check-fasim-long-query-streaming-scoreinfo-neat1-runtime-boundary:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_neat1_runtime_boundary.sh

check-fasim-long-query-streaming-scoreinfo-trust-runner-real:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_trust_runner_real.sh

characterize-fasim-long-query-streaming-scoreinfo-trust-runner:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner.sh

characterize-fasim-long-query-streaming-scoreinfo-trust-runner-workers:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_workers.sh

characterize-fasim-long-query-streaming-scoreinfo-trust-runner-groups:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_groups.sh

characterize-fasim-long-query-streaming-scoreinfo-trust-runner-group32-scaling:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_group32_scaling.sh

characterize-fasim-long-query-streaming-scoreinfo-trust-runner-malat1-full-group32:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_long_query_streaming_scoreinfo_trust_runner_malat1_full_group32.sh

characterize-fasim-long-query-streaming-scoreinfo-two-contract-trust:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_long_query_streaming_scoreinfo_two_contract_trust.sh

check-fasim-long-query-streaming-scoreinfo-two-contract-trust-characterization:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_trust_characterization.sh

check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner.sh

check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner_real.sh

check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first64:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 MALAT1_RECORD_LIMIT=64 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner_real.sh

check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first128:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 MALAT1_RECORD_LIMIT=128 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner_real.sh

check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 MALAT1_RECORD_LIMIT=256 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_group32_audited_runner_real.sh

check-fasim-gasal2-scoreinfo-scoped-milestone:
	bash ./scripts/check_fasim_gasal2_scoreinfo_scoped_milestone.sh

check-fasim-gasal2-scoreinfo-scoped-milestone-rollup:
	bash ./scripts/check_fasim_gasal2_scoreinfo_scoped_milestone_rollup.sh

.PHONY: check-fasim-gasal2-scoreinfo-scoped-milestone-rollup

check-fasim-gasal2-malat1-two-contract-product-readiness:
	bash ./scripts/check_fasim_gasal2_malat1_two_contract_product_readiness.sh

check-fasim-gasal2-malat1-two-contract-recommended-runtime:
	bash ./scripts/check_fasim_gasal2_malat1_two_contract_recommended_runtime.sh

.PHONY: check-fasim-gasal2-malat1-two-contract-product-readiness check-fasim-gasal2-malat1-two-contract-recommended-runtime

check-fasim-gasal2-scoreinfo-completion-gap:
	bash ./scripts/check_fasim_gasal2_scoreinfo_completion_gap.sh

check-fasim-gasal2-full-goal-decision:
	bash ./scripts/check_fasim_gasal2_full_goal_decision.sh

check-fasim-tfosorted-cigar-archive-probe:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(CURDIR)/.tmp/check_fasim_tfosorted_cigar_archive_probe ARCHIVE_OUTPUT_MODE=tfosorted bash ./scripts/check_fasim_tfosorted_cigar_archive_probe.sh
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(CURDIR)/.tmp/check_fasim_tfosorted_cigar_archive_probe_lite ARCHIVE_OUTPUT_MODE=lite bash ./scripts/check_fasim_tfosorted_cigar_archive_probe.sh

.PHONY: check-fasim-tfosorted-cigar-archive-probe

check-fasim-tfosorted-compact-archive-probe:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(CURDIR)/.tmp/check_fasim_tfosorted_compact_archive_probe ARCHIVE_OUTPUT_MODE=tfosorted bash ./scripts/check_fasim_tfosorted_compact_archive_probe.sh
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(CURDIR)/.tmp/check_fasim_tfosorted_compact_archive_probe_lite ARCHIVE_OUTPUT_MODE=lite bash ./scripts/check_fasim_tfosorted_compact_archive_probe.sh

.PHONY: check-fasim-tfosorted-compact-archive-probe

check-fasim-tfosorted-column-archive-probe:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(CURDIR)/.tmp/check_fasim_tfosorted_column_archive_probe ARCHIVE_OUTPUT_MODE=tfosorted bash ./scripts/check_fasim_tfosorted_column_archive_probe.sh
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(CURDIR)/.tmp/check_fasim_tfosorted_column_archive_probe_lite ARCHIVE_OUTPUT_MODE=lite bash ./scripts/check_fasim_tfosorted_column_archive_probe.sh

.PHONY: check-fasim-tfosorted-column-archive-probe

check-fasim-gasal2-convert-cpu-breakdown:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_convert_cpu_breakdown) bash ./scripts/check_fasim_gasal2_convert_cpu_breakdown.sh

.PHONY: check-fasim-gasal2-convert-cpu-breakdown

check-fasim-gasal2-direct-lite-archive-convert:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_direct_lite_archive_convert) bash ./scripts/check_fasim_gasal2_direct_lite_archive_convert.sh

.PHONY: check-fasim-gasal2-direct-lite-archive-convert

check-fasim-gasal2-archive-first-output:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_archive_first_output) bash ./scripts/check_fasim_gasal2_archive_first_output.sh

.PHONY: check-fasim-gasal2-archive-first-output

check-fasim-gasal2-flush-pipeline-parser:
	bash ./scripts/check_fasim_gasal2_flush_pipeline_parser.sh

.PHONY: check-fasim-gasal2-flush-pipeline-parser

check-fasim-gasal2-flush-pipeline-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_flush_pipeline_smoke) bash ./scripts/check_fasim_gasal2_flush_pipeline_smoke.sh

.PHONY: check-fasim-gasal2-flush-pipeline-smoke

check-fasim-gasal2-nvtx-trace-scaffold:
	bash ./scripts/check_fasim_gasal2_nvtx_trace_scaffold.sh

.PHONY: check-fasim-gasal2-nvtx-trace-scaffold

check-fasim-gasal2-nvtx-trace-smoke:
	$(MAKE) build-fasim-gasal2-nvtx FASIM_GASAL2_NVTX_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_nvtx
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_nvtx WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_nvtx_trace_smoke) bash ./scripts/check_fasim_gasal2_nvtx_trace_smoke.sh

.PHONY: check-fasim-gasal2-nvtx-trace-smoke

check-fasim-gasal2-flush-two-slot-overlap-scaffold:
	bash ./scripts/check_fasim_gasal2_flush_two_slot_overlap_scaffold.sh

.PHONY: check-fasim-gasal2-flush-two-slot-overlap-scaffold

check-fasim-gasal2-flush-two-slot-overlap-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_flush_two_slot_overlap_smoke) bash ./scripts/check_fasim_gasal2_flush_two_slot_overlap_smoke.sh

.PHONY: check-fasim-gasal2-flush-two-slot-overlap-smoke

characterize-fasim-gasal2-flush-two-slot-overlap-chr22:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/characterize_fasim_gasal2_flush_two_slot_overlap_chr22) bash ./scripts/characterize_fasim_gasal2_flush_two_slot_overlap_chr22.sh

.PHONY: characterize-fasim-gasal2-flush-two-slot-overlap-chr22

check-fasim-gasal2-flush-two-slot-overlap-chr22-result:
	bash ./scripts/check_fasim_gasal2_flush_two_slot_overlap_chr22_result.sh

.PHONY: check-fasim-gasal2-flush-two-slot-overlap-chr22-result

characterize-fasim-gasal2-flush-two-slot-overlap-broader-matrix:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	$(MAKE) build-fasim-gasal2-nvtx FASIM_GASAL2_NVTX_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_nvtx
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct NVTX_BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_nvtx WORK=$(or $(WORK),$(CURDIR)/.tmp/characterize_fasim_gasal2_flush_two_slot_overlap_broader_matrix_v2) bash ./scripts/characterize_fasim_gasal2_flush_two_slot_overlap_broader_matrix.sh

.PHONY: characterize-fasim-gasal2-flush-two-slot-overlap-broader-matrix

check-fasim-gasal2-flush-two-slot-overlap-broader-matrix-result:
	bash ./scripts/check_fasim_gasal2_flush_two_slot_overlap_broader_matrix_result.sh

.PHONY: check-fasim-gasal2-flush-two-slot-overlap-broader-matrix-result

characterize-fasim-gasal2-flush-two-slot-multi-worker-2gpu:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu_v1) bash ./scripts/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu.sh

.PHONY: characterize-fasim-gasal2-flush-two-slot-multi-worker-2gpu

check-fasim-gasal2-flush-two-slot-multi-worker-2gpu-result:
	bash ./scripts/check_fasim_gasal2_flush_two_slot_multi_worker_2gpu_result.sh

.PHONY: check-fasim-gasal2-flush-two-slot-multi-worker-2gpu-result

check-fasim-gasal2-two-slot-low-density-guard:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_two_slot_low_density_guard) bash ./scripts/check_fasim_gasal2_two_slot_low_density_guard.sh

.PHONY: check-fasim-gasal2-two-slot-low-density-guard

check-fasim-gasal2-two-slot-recommended-runtime-readiness:
	bash ./scripts/check_fasim_gasal2_two_slot_recommended_runtime_readiness.sh

.PHONY: check-fasim-gasal2-two-slot-recommended-runtime-readiness

check-fasim-gasal2-flush-result-boundary-scaffold:
	bash ./scripts/check_fasim_gasal2_flush_result_boundary_scaffold.sh

.PHONY: check-fasim-gasal2-flush-result-boundary-scaffold

check-fasim-gasal2-flush-result-boundary-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_flush_result_boundary_smoke) bash ./scripts/check_fasim_gasal2_flush_result_boundary_smoke.sh

.PHONY: check-fasim-gasal2-flush-result-boundary-smoke

check-fasim-gasal2-flush-pure-finalizer-scaffold:
	bash ./scripts/check_fasim_gasal2_flush_pure_finalizer_scaffold.sh

.PHONY: check-fasim-gasal2-flush-pure-finalizer-scaffold

check-fasim-gasal2-flush-pure-finalizer-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_flush_pure_finalizer_smoke) bash ./scripts/check_fasim_gasal2_flush_pure_finalizer_smoke.sh

.PHONY: check-fasim-gasal2-flush-pure-finalizer-smoke

check-fasim-gasal2-flush-ordered-commit-scaffold:
	bash ./scripts/check_fasim_gasal2_flush_ordered_commit_scaffold.sh

.PHONY: check-fasim-gasal2-flush-ordered-commit-scaffold

check-fasim-gasal2-flush-ordered-commit-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_flush_ordered_commit_smoke) bash ./scripts/check_fasim_gasal2_flush_ordered_commit_smoke.sh

.PHONY: check-fasim-gasal2-flush-ordered-commit-smoke

check-fasim-gasal2-flush-dual-finalizer-scaffold:
	bash ./scripts/check_fasim_gasal2_flush_dual_finalizer_scaffold.sh

.PHONY: check-fasim-gasal2-flush-dual-finalizer-scaffold

check-fasim-gasal2-flush-dual-finalizer-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_flush_dual_finalizer_smoke) bash ./scripts/check_fasim_gasal2_flush_dual_finalizer_smoke.sh

.PHONY: check-fasim-gasal2-flush-dual-finalizer-smoke

check-fasim-gasal2-flush-extracted-finalizer-scaffold:
	bash ./scripts/check_fasim_gasal2_flush_extracted_finalizer_scaffold.sh

.PHONY: check-fasim-gasal2-flush-extracted-finalizer-scaffold

check-fasim-gasal2-flush-extracted-finalizer-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_flush_extracted_finalizer_smoke) bash ./scripts/check_fasim_gasal2_flush_extracted_finalizer_smoke.sh

.PHONY: check-fasim-gasal2-flush-extracted-finalizer-smoke

characterize-fasim-gasal2-flush-extracted-finalizer-chr22:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/characterize_fasim_gasal2_flush_extracted_finalizer_chr22) bash ./scripts/characterize_fasim_gasal2_flush_extracted_finalizer_chr22.sh

.PHONY: characterize-fasim-gasal2-flush-extracted-finalizer-chr22

check-fasim-gasal2-flush-extracted-finalizer-chr22-result:
	bash ./scripts/check_fasim_gasal2_flush_extracted_finalizer_chr22_result.sh

.PHONY: check-fasim-gasal2-flush-extracted-finalizer-chr22-result

check-fasim-gasal2-full-run-determinism-oracle-parser:
	bash ./scripts/check_fasim_gasal2_full_run_determinism_oracle_parser.sh

.PHONY: check-fasim-gasal2-full-run-determinism-oracle-parser

characterize-fasim-gasal2-full-run-determinism-chr22:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/characterize_fasim_gasal2_full_run_determinism_chr22) bash ./scripts/characterize_fasim_gasal2_full_run_determinism_chr22.sh

.PHONY: characterize-fasim-gasal2-full-run-determinism-chr22

check-fasim-gasal2-full-run-determinism-chr22-result:
	bash ./scripts/check_fasim_gasal2_full_run_determinism_chr22_result.sh

.PHONY: check-fasim-gasal2-full-run-determinism-chr22-result

check-fasim-tfo-archive-integrity-parser:
	bash ./scripts/check_fasim_tfo_archive_integrity_parser.sh

.PHONY: check-fasim-tfo-archive-integrity-parser

check-fasim-gasal2-archive-manifest-parser:
	bash ./scripts/check_fasim_gasal2_archive_manifest_parser.sh

.PHONY: check-fasim-gasal2-archive-manifest-parser

check-fasim-gasal2-workload-matrix-parser:
	bash ./scripts/check_fasim_gasal2_workload_matrix_parser.sh

.PHONY: check-fasim-gasal2-workload-matrix-parser

check-fasim-gasal2-workload-matrix:
	python3 ./scripts/summarize_fasim_gasal2_workload_matrix.py --matrix ./docs/fasim_gasal2_workload_matrix.tsv

.PHONY: check-fasim-gasal2-workload-matrix

check-fasim-gasal2-goal-completion-decision:
	bash ./scripts/check_fasim_gasal2_goal_completion_decision.sh

.PHONY: check-fasim-gasal2-goal-completion-decision

check-fasim-gasal2-roadmap-broad-restart-gate:
	bash ./scripts/check_fasim_gasal2_roadmap_broad_restart_gate.sh

.PHONY: check-fasim-gasal2-roadmap-broad-restart-gate

check-fasim-gasal2-roadmap-phase-checklist:
	bash ./scripts/check_fasim_gasal2_roadmap_phase_checklist.sh

.PHONY: check-fasim-gasal2-roadmap-phase-checklist

check-fasim-gasal2-roadmap-gate-plan:
	bash ./scripts/check_fasim_gasal2_roadmap_gate_plan.sh

.PHONY: check-fasim-gasal2-roadmap-gate-plan

check-fasim-gasal2-roadmap-direct-phase-roadmap:
	bash ./scripts/check_fasim_gasal2_roadmap_direct_phase_roadmap.sh

.PHONY: check-fasim-gasal2-roadmap-direct-phase-roadmap

check-fasim-gasal2-roadmap-phase-roadmap:
	bash ./scripts/check_fasim_gasal2_roadmap_phase_roadmap.sh

.PHONY: check-fasim-gasal2-roadmap-phase-roadmap

check-fasim-gasal2-roadmap-phase-execution-plan:
	bash ./scripts/check_fasim_gasal2_roadmap_phase_execution_plan.sh

.PHONY: check-fasim-gasal2-roadmap-phase-execution-plan

check-fasim-gasal2-roadmap-phase-to-completion-plan:
	bash ./scripts/check_fasim_gasal2_roadmap_phase_to_completion_plan.sh

.PHONY: check-fasim-gasal2-roadmap-phase-to-completion-plan

check-fasim-gasal2-roadmap-phase-driver:
	bash ./scripts/check_fasim_gasal2_roadmap_phase_driver.sh

.PHONY: check-fasim-gasal2-roadmap-phase-driver

check-fasim-gasal2-roadmap-canonical-phase-plan:
	bash ./scripts/check_fasim_gasal2_roadmap_canonical_phase_plan.sh

.PHONY: check-fasim-gasal2-roadmap-canonical-phase-plan

check-fasim-gasal2-roadmap-goal-closure-phase-plan:
	bash ./scripts/check_fasim_gasal2_roadmap_goal_closure_phase_plan.sh

.PHONY: check-fasim-gasal2-roadmap-goal-closure-phase-plan

check-fasim-gasal2-roadmap-close-plan:
	bash ./scripts/check_fasim_gasal2_roadmap_close_plan.sh

.PHONY: check-fasim-gasal2-roadmap-close-plan

check-fasim-gasal2-roadmap-finish-plan:
	bash ./scripts/check_fasim_gasal2_roadmap_finish_plan.sh

.PHONY: check-fasim-gasal2-roadmap-finish-plan

check-fasim-gasal2-roadmap-execution-ladder:
	bash ./scripts/check_fasim_gasal2_roadmap_execution_ladder.sh

.PHONY: check-fasim-gasal2-roadmap-execution-ladder

check-fasim-gasal2-roadmap-scope-or-broad-design-decision:
	bash ./scripts/check_fasim_gasal2_roadmap_scope_or_broad_design_decision.sh

.PHONY: check-fasim-gasal2-roadmap-scope-or-broad-design-decision

check-fasim-gasal2-roadmap-phase0-reproducibility:
	bash ./scripts/check_fasim_gasal2_roadmap_phase0_reproducibility.sh

.PHONY: check-fasim-gasal2-roadmap-phase0-reproducibility

check-fasim-gasal2-roadmap-phase1-scoped-contract:
	bash ./scripts/check_fasim_gasal2_roadmap_phase1_scoped_contract.sh

.PHONY: check-fasim-gasal2-roadmap-phase1-scoped-contract

check-fasim-gasal2-roadmap-phase1-scoped-product:
	bash ./scripts/check_fasim_gasal2_roadmap_phase1_scoped_product.sh

.PHONY: check-fasim-gasal2-roadmap-phase1-scoped-product

check-fasim-gasal2-roadmap-path-a-scoped-acceptance:
	bash ./scripts/check_fasim_gasal2_roadmap_path_a_scoped_acceptance.sh

.PHONY: check-fasim-gasal2-roadmap-path-a-scoped-acceptance

check-fasim-gasal2-roadmap-phase2-equivalence-first-convert:
	bash ./scripts/check_fasim_gasal2_roadmap_phase2_equivalence_first_convert.sh

.PHONY: check-fasim-gasal2-roadmap-phase2-equivalence-first-convert

check-fasim-gasal2-roadmap-phase3-preconvert-prune:
	bash ./scripts/check_fasim_gasal2_roadmap_phase3_preconvert_prune.sh

.PHONY: check-fasim-gasal2-roadmap-phase3-preconvert-prune

check-fasim-gasal2-roadmap-phase3-cigar-nt-prefilter-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase3_cigar_nt_prefilter_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase3-cigar-nt-prefilter-design

check-fasim-gasal2-phase3-cigar-nt-prefilter-shadow:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase3_cigar_nt_prefilter_shadow.sh

.PHONY: check-fasim-gasal2-phase3-cigar-nt-prefilter-shadow

characterize-fasim-gasal2-phase3-cigar-nt-prefilter-full:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_phase3_cigar_nt_prefilter_full.sh

.PHONY: characterize-fasim-gasal2-phase3-cigar-nt-prefilter-full

check-fasim-gasal2-phase3-cigar-nt-prefilter-full-result:
	bash ./scripts/check_fasim_gasal2_phase3_cigar_nt_prefilter_full_result.sh

.PHONY: check-fasim-gasal2-phase3-cigar-nt-prefilter-full-result

check-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase3_cigar_nt_prefilter_real_validate.sh

.PHONY: check-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate

characterize-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate-full:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_phase3_cigar_nt_prefilter_real_validate_full.sh

.PHONY: characterize-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate-full

check-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate-full-result:
	bash ./scripts/check_fasim_gasal2_phase3_cigar_nt_prefilter_real_validate_full_result.sh

.PHONY: check-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate-full-result

check-fasim-gasal2-roadmap-phase4-sort-topn:
	bash ./scripts/check_fasim_gasal2_roadmap_phase4_sort_topn.sh

.PHONY: check-fasim-gasal2-roadmap-phase4-sort-topn

check-fasim-gasal2-roadmap-phase5-archive-artifact:
	bash ./scripts/check_fasim_gasal2_roadmap_phase5_archive_artifact.sh

.PHONY: check-fasim-gasal2-roadmap-phase5-archive-artifact

check-fasim-gasal2-roadmap-phase6-workload-matrix:
	bash ./scripts/check_fasim_gasal2_roadmap_phase6_workload_matrix.sh

.PHONY: check-fasim-gasal2-roadmap-phase6-workload-matrix

check-fasim-gasal2-roadmap-phase7-broad-restart:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart

check-fasim-gasal2-roadmap-phase7-candidate-coverage:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_candidate_coverage.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-candidate-coverage

check-fasim-gasal2-roadmap-phase7-candidate-coverage-stop:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_candidate_coverage_stop.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-candidate-coverage-stop

check-fasim-gasal2-roadmap-phase7-next-reducer-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_next_reducer_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-next-reducer-design

check-fasim-gasal2-roadmap-phase7-next-reducer-implementation-plan:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_next_reducer_implementation_plan.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-next-reducer-implementation-plan

check-fasim-gasal2-phase7-next-reducer-env:
	bash ./scripts/check_fasim_gasal2_phase7_next_reducer_env.sh

.PHONY: check-fasim-gasal2-phase7-next-reducer-env

check-fasim-gasal2-phase7-frontier-log-env:
	bash ./scripts/check_fasim_gasal2_phase7_frontier_log_env.sh

.PHONY: check-fasim-gasal2-phase7-frontier-log-env

check-fasim-gasal2-phase7-frontier-log-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_frontier_log_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-frontier-log-runtime-smoke

characterize-fasim-gasal2-phase7-frontier-replay:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_phase7_frontier_replay.sh

.PHONY: characterize-fasim-gasal2-phase7-frontier-replay

check-fasim-gasal2-phase7-frontier-replay-result:
	bash ./scripts/check_fasim_gasal2_phase7_frontier_replay_result.sh

.PHONY: check-fasim-gasal2-phase7-frontier-replay-result

check-fasim-gasal2-phase7-next-reducer-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_next_reducer_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-next-reducer-runtime-smoke

characterize-fasim-gasal2-phase7-next-reducer:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_phase7_next_reducer.sh

.PHONY: characterize-fasim-gasal2-phase7-next-reducer

check-fasim-gasal2-phase7-next-reducer-result:
	bash ./scripts/check_fasim_gasal2_phase7_next_reducer_result.sh

.PHONY: check-fasim-gasal2-phase7-next-reducer-result

characterize-fasim-gasal2-phase7-next-reducer-broad-gate:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_phase7_next_reducer_broad_gate.sh

.PHONY: characterize-fasim-gasal2-phase7-next-reducer-broad-gate

check-fasim-gasal2-phase7-next-reducer-broad-gate-result:
	bash ./scripts/check_fasim_gasal2_phase7_next_reducer_broad_gate_result.sh

.PHONY: check-fasim-gasal2-phase7-next-reducer-broad-gate-result

check-fasim-gasal2-roadmap-phase7-next-reducer-scaffold: check-fasim-gasal2-phase7-next-reducer-env check-fasim-gasal2-phase7-next-reducer-runtime-smoke characterize-fasim-gasal2-phase7-next-reducer check-fasim-gasal2-phase7-next-reducer-result
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_next_reducer_scaffold.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-next-reducer-scaffold

check-fasim-gasal2-roadmap-phase7-next-reducer-broad-gate: characterize-fasim-gasal2-phase7-next-reducer-broad-gate check-fasim-gasal2-phase7-next-reducer-broad-gate-result
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_next_reducer_broad_gate.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-next-reducer-broad-gate

check-fasim-gasal2-roadmap-phase7-broad-restart-v2-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v2_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v2-design

check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-log-scaffold: check-fasim-gasal2-phase7-frontier-log-env check-fasim-gasal2-phase7-frontier-log-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v2_frontier_log_scaffold.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-log-scaffold

check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-replay: characterize-fasim-gasal2-phase7-frontier-replay check-fasim-gasal2-phase7-frontier-replay-result
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v2_frontier_replay.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-replay

characterize-fasim-gasal2-phase7-frontier-reducer:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_phase7_frontier_reducer.sh

.PHONY: characterize-fasim-gasal2-phase7-frontier-reducer

check-fasim-gasal2-phase7-frontier-reducer-result:
	bash ./scripts/check_fasim_gasal2_phase7_frontier_reducer_result.sh

.PHONY: check-fasim-gasal2-phase7-frontier-reducer-result

check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-reducer: characterize-fasim-gasal2-phase7-frontier-reducer check-fasim-gasal2-phase7-frontier-reducer-result
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v2_frontier_reducer.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-reducer

characterize-fasim-gasal2-phase7-frontier-predictor:
	bash ./scripts/characterize_fasim_gasal2_phase7_frontier_predictor.sh

.PHONY: characterize-fasim-gasal2-phase7-frontier-predictor

check-fasim-gasal2-phase7-frontier-predictor-result:
	bash ./scripts/check_fasim_gasal2_phase7_frontier_predictor_result.sh

.PHONY: check-fasim-gasal2-phase7-frontier-predictor-result

check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-predictor: characterize-fasim-gasal2-phase7-frontier-predictor check-fasim-gasal2-phase7-frontier-predictor-result
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v2_frontier_predictor.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-predictor

characterize-fasim-gasal2-phase7-frontier-score-signal:
	bash ./scripts/characterize_fasim_gasal2_phase7_frontier_score_signal.sh

.PHONY: characterize-fasim-gasal2-phase7-frontier-score-signal

check-fasim-gasal2-phase7-frontier-score-signal-result:
	bash ./scripts/check_fasim_gasal2_phase7_frontier_score_signal_result.sh

.PHONY: check-fasim-gasal2-phase7-frontier-score-signal-result

check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-score-signal: characterize-fasim-gasal2-phase7-frontier-score-signal check-fasim-gasal2-phase7-frontier-score-signal-result
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v2_frontier_score_signal.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-score-signal

characterize-fasim-gasal2-phase7-frontier-early-stop:
	bash ./scripts/characterize_fasim_gasal2_phase7_frontier_early_stop.sh

.PHONY: characterize-fasim-gasal2-phase7-frontier-early-stop

check-fasim-gasal2-phase7-frontier-early-stop-result:
	bash ./scripts/check_fasim_gasal2_phase7_frontier_early_stop_result.sh

.PHONY: check-fasim-gasal2-phase7-frontier-early-stop-result

check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop: characterize-fasim-gasal2-phase7-frontier-early-stop check-fasim-gasal2-phase7-frontier-early-stop-result
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v2_frontier_early_stop.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop

check-fasim-gasal2-phase7-frontier-early-stop-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_frontier_early_stop_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-frontier-early-stop-runtime-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop-runtime: check-fasim-gasal2-phase7-frontier-early-stop-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v2_frontier_early_stop_runtime.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop-runtime

characterize-fasim-gasal2-phase7-frontier-early-stop-runtime:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_phase7_frontier_early_stop_runtime.sh

.PHONY: characterize-fasim-gasal2-phase7-frontier-early-stop-runtime

check-fasim-gasal2-phase7-frontier-early-stop-runtime-result:
	bash ./scripts/check_fasim_gasal2_phase7_frontier_early_stop_runtime_result.sh

.PHONY: check-fasim-gasal2-phase7-frontier-early-stop-runtime-result

check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop-runtime-first1: characterize-fasim-gasal2-phase7-frontier-early-stop-runtime check-fasim-gasal2-phase7-frontier-early-stop-runtime-result
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v2_frontier_early_stop_runtime_first1.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop-runtime-first1

check-fasim-gasal2-roadmap-phase7-next-reducer-after-early-stop-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_next_reducer_after_early_stop_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-next-reducer-after-early-stop-design

check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_all_attempt_early_stop_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-smoke

characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_phase7_all_attempt_early_stop_runtime.sh

.PHONY: characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime

check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-result:
	bash ./scripts/check_fasim_gasal2_phase7_all_attempt_early_stop_runtime_result.sh

.PHONY: check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-result

check-fasim-gasal2-roadmap-phase7-all-attempt-early-stop-runtime-first1: characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-result
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_all_attempt_early_stop_runtime_first1.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-all-attempt-early-stop-runtime-first1

characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	WORK=$(CURDIR)/.tmp/characterize_fasim_gasal2_phase7_all_attempt_early_stop_runtime_first64 BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct RECORD_LIMIT=64 WORKLOAD_LABEL=neat1_first64 DECISION_LABEL=first64 bash ./scripts/characterize_fasim_gasal2_phase7_all_attempt_early_stop_runtime.sh

.PHONY: characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64

check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64-result:
	bash ./scripts/check_fasim_gasal2_phase7_all_attempt_early_stop_runtime_first64_result.sh

.PHONY: check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64-result

check-fasim-gasal2-roadmap-phase7-all-attempt-early-stop-runtime-first64: characterize-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64 check-fasim-gasal2-phase7-all-attempt-early-stop-runtime-first64-result
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_all_attempt_early_stop_runtime_first64.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-all-attempt-early-stop-runtime-first64

check-fasim-gasal2-roadmap-phase7-gate-c-gpu-candidate-generator-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gate_c_gpu_candidate_generator_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gate-c-gpu-candidate-generator-design

check-fasim-gasal2-roadmap-phase7-gate-c-implementation-plan:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gate_c_implementation_plan.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gate-c-implementation-plan

check-fasim-gasal2-roadmap-phase7-gate-c-first1:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gate_c_first1.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gate-c-first1

check-fasim-gasal2-roadmap-phase7-gate-c-stop-checkpoint:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gate_c_stop_checkpoint.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gate-c-stop-checkpoint

check-fasim-gasal2-roadmap-phase7-current-broad-stop-decision:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_current_broad_stop_decision.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-current-broad-stop-decision

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-design

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-descriptor-source-smoke: check-fasim-gasal2-phase7-v3-descriptor-source-env check-fasim-gasal2-phase7-v3-descriptor-source-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_descriptor_source_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-descriptor-source-smoke

check-fasim-gasal2-phase7-gate-c-env:
	bash ./scripts/check_fasim_gasal2_phase7_gate_c_env.sh

.PHONY: check-fasim-gasal2-phase7-gate-c-env

check-fasim-gasal2-phase7-v3-descriptor-source-env:
	bash ./scripts/check_fasim_gasal2_phase7_v3_descriptor_source_env.sh

.PHONY: check-fasim-gasal2-phase7-v3-descriptor-source-env

check-fasim-gasal2-phase7-v3-pre-scoreinfo-descriptor-source-env:
	bash ./scripts/check_fasim_gasal2_phase7_v3_pre_scoreinfo_descriptor_source_env.sh

.PHONY: check-fasim-gasal2-phase7-v3-pre-scoreinfo-descriptor-source-env

check-fasim-gasal2-phase7-v3-certificate-env:
	bash ./scripts/check_fasim_gasal2_phase7_v3_certificate_env.sh

.PHONY: check-fasim-gasal2-phase7-v3-certificate-env

check-fasim-gasal2-phase7-v3-all-column-certificate-env:
	bash ./scripts/check_fasim_gasal2_phase7_v3_all_column_certificate_env.sh

.PHONY: check-fasim-gasal2-phase7-v3-all-column-certificate-env

check-fasim-gasal2-phase7-v3-descriptor-source-runtime-smoke:
	bash ./scripts/check_fasim_gasal2_phase7_v3_descriptor_source_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v3-descriptor-source-runtime-smoke

check-fasim-gasal2-phase7-v3-pre-scoreinfo-descriptor-source-runtime-smoke:
	bash ./scripts/check_fasim_gasal2_phase7_v3_pre_scoreinfo_descriptor_source_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v3-pre-scoreinfo-descriptor-source-runtime-smoke

check-fasim-gasal2-phase7-v3-certificate-runtime-smoke:
	bash ./scripts/check_fasim_gasal2_phase7_v3_certificate_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v3-certificate-runtime-smoke

check-fasim-gasal2-phase7-v3-all-column-certificate-runtime-smoke:
	bash ./scripts/check_fasim_gasal2_phase7_v3_all_column_certificate_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v3-all-column-certificate-runtime-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-pre-scoreinfo-descriptor-source-smoke: check-fasim-gasal2-phase7-v3-pre-scoreinfo-descriptor-source-env check-fasim-gasal2-phase7-v3-pre-scoreinfo-descriptor-source-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_pre_scoreinfo_descriptor_source_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-pre-scoreinfo-descriptor-source-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-certificate-smoke: check-fasim-gasal2-phase7-v3-certificate-env check-fasim-gasal2-phase7-v3-certificate-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_certificate_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-certificate-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-all-column-certificate-smoke: check-fasim-gasal2-phase7-v3-all-column-certificate-env check-fasim-gasal2-phase7-v3-all-column-certificate-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_all_column_certificate_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-all-column-certificate-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-all-column-replay-stop:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_all_column_replay_stop.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-all-column-replay-stop

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-narrow-certificate-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_narrow_certificate_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-narrow-certificate-design

check-fasim-gasal2-phase7-v3-narrow-certificate-env:
	bash ./scripts/check_fasim_gasal2_phase7_v3_narrow_certificate_env.sh

.PHONY: check-fasim-gasal2-phase7-v3-narrow-certificate-env

check-fasim-gasal2-phase7-v3-narrow-certificate-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_v3_narrow_certificate_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v3-narrow-certificate-runtime-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-narrow-certificate-smoke: check-fasim-gasal2-phase7-v3-narrow-certificate-env check-fasim-gasal2-phase7-v3-narrow-certificate-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_narrow_certificate_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-narrow-certificate-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-real-narrow-certificate-coverage-proof:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_real_narrow_certificate_coverage_proof.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-real-narrow-certificate-coverage-proof

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-next-source-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_next_source_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-next-source-design

check-fasim-gasal2-phase7-v3-next-source-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_v3_next_source_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v3-next-source-runtime-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-next-source-smoke: check-fasim-gasal2-phase7-v3-next-source-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_next_source_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-next-source-smoke

check-fasim-gasal2-phase7-v3-strong-seed-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_v3_strong_seed_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v3-strong-seed-runtime-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-strong-seed-smoke: check-fasim-gasal2-phase7-v3-strong-seed-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_strong_seed_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-strong-seed-smoke

check-fasim-gasal2-phase7-v3-attempt-coverage-seed-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_v3_attempt_coverage_seed_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v3-attempt-coverage-seed-runtime-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-attempt-coverage-seed-smoke: check-fasim-gasal2-phase7-v3-attempt-coverage-seed-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_attempt_coverage_seed_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-attempt-coverage-seed-smoke

check-fasim-gasal2-phase7-v3-oracle-min-cover-replay-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_v3_oracle_min_cover_replay_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v3-oracle-min-cover-replay-runtime-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-oracle-min-cover-replay-smoke: check-fasim-gasal2-phase7-v3-oracle-min-cover-replay-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_oracle_min_cover_replay_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-oracle-min-cover-replay-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v3-seed-path-stop:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v3_seed_path_stop.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v3-seed-path-stop

check-fasim-gasal2-roadmap-phase7-broad-restart-v4-scoreinfo-native-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v4_scoreinfo_native_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v4-scoreinfo-native-design

check-fasim-gasal2-phase7-v4-legacy-byte-scoreinfo-shadow-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_v4_legacy_byte_scoreinfo_shadow_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v4-legacy-byte-scoreinfo-shadow-runtime-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v4-legacy-byte-scoreinfo-shadow-smoke: check-fasim-gasal2-phase7-v4-legacy-byte-scoreinfo-shadow-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v4_legacy_byte_scoreinfo_shadow_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v4-legacy-byte-scoreinfo-shadow-smoke

check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-shadow-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_v4_gpu_legacy_byte_scoreinfo_shadow_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-shadow-runtime-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-scoreinfo-shadow-smoke: check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-shadow-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_shadow_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-scoreinfo-shadow-smoke

check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-source-replay-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_v4_gpu_legacy_byte_scoreinfo_source_replay_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-source-replay-runtime-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-scoreinfo-source-replay-smoke: check-fasim-gasal2-phase7-v4-gpu-legacy-byte-scoreinfo-source-replay-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_replay_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-scoreinfo-source-replay-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-scoreinfo-source-first64-broad-gate:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v4_gpu_legacy_byte_scoreinfo_source_first64_broad_gate.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-scoreinfo-source-first64-broad-gate

check-fasim-gasal2-roadmap-phase7-broad-restart-v5-fused-scoreinfo-consumer-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_fused_scoreinfo_consumer_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v5-fused-scoreinfo-consumer-design

check-fasim-gasal2-roadmap-phase7-broad-restart-v5-implementation-plan:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_implementation_plan.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v5-implementation-plan

check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-env:
	bash ./scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_env.sh

.PHONY: check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-env

check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-env:
	bash ./scripts/check_fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_env.sh

.PHONY: check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-env

check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-env-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_env_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-env-runtime-smoke

check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke

check-fasim-gasal2-phase7-v5-cpu-authority-replay-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_v5_cpu_authority_replay_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v5-cpu-authority-replay-runtime-smoke

characterize-fasim-gasal2-phase7-v5-cpu-authority-replay-first64:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_phase7_v5_cpu_authority_replay_first64.sh

.PHONY: characterize-fasim-gasal2-phase7-v5-cpu-authority-replay-first64

check-fasim-gasal2-phase7-v5-cpu-authority-replay-first64-result:
	bash ./scripts/check_fasim_gasal2_phase7_v5_cpu_authority_replay_first64_result.sh

.PHONY: check-fasim-gasal2-phase7-v5-cpu-authority-replay-first64-result

check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_v5_fused_scoreinfo_consumer_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-v5-fused-scoreinfo-consumer-runtime-smoke

check-fasim-gasal2-phase7-post-v5-3-gpu-consumer-summary-env-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_post_v5_3_gpu_consumer_summary_env_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-post-v5-3-gpu-consumer-summary-env-runtime-smoke

check-fasim-gasal2-phase7-post-v5-3-host-assisted-consumer-feasibility-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_post_v5_3_host_assisted_consumer_feasibility_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-post-v5-3-host-assisted-consumer-feasibility-runtime-smoke

check-fasim-gasal2-phase7-post-v5-3-task-frontier-certificate-env-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_env_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-post-v5-3-task-frontier-certificate-env-runtime-smoke

check-fasim-gasal2-phase7-post-v5-3-task-frontier-certificate-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_post_v5_3_task_frontier_certificate_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-post-v5-3-task-frontier-certificate-runtime-smoke

check-fasim-gasal2-phase7-post-v5-3-pre-d2h-proof-search-runtime-smoke:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_post_v5_3_pre_d2h_proof_search_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-post-v5-3-pre-d2h-proof-search-runtime-smoke

check-fasim-gasal2-roadmap-phase7-post-v5-3-gpu-consumer-summary-env-scaffold:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_gpu_consumer_summary_env_scaffold.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-gpu-consumer-summary-env-scaffold

check-fasim-gasal2-roadmap-phase7-broad-restart-v5-fused-scoreinfo-consumer-runtime-smoke:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_fused_scoreinfo_consumer_runtime_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v5-fused-scoreinfo-consumer-runtime-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-design

check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-env-scaffold:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_env_scaffold.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-env-scaffold

check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_true_pre_scoreinfo_descriptor_source_runtime_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-smoke:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_cpu_authority_replay_smoke.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-smoke

check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-first64-broad-gate:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_cpu_authority_replay_first64_broad_gate.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-first64-broad-gate

check-fasim-gasal2-roadmap-phase7-post-v5-3-architecture-decision:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_architecture_decision.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-architecture-decision

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-architecture-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_architecture_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-architecture-design

check-fasim-gasal2-roadmap-phase7-post-v5-3-long-query-safe-consumer-summary-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_long_query_safe_consumer_summary_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-long-query-safe-consumer-summary-design

check-fasim-gasal2-roadmap-phase7-post-v5-3-gpu-consumer-summary-first-attempt-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_gpu_consumer_summary_first_attempt_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-gpu-consumer-summary-first-attempt-no-go

check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-consumer-summary-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_stronger_consumer_summary_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-consumer-summary-design

check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-consumer-summary-prefix-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_stronger_consumer_summary_prefix_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-consumer-summary-prefix-no-go

check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_task_frontier_certificate_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-design

check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-env-scaffold:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_task_frontier_certificate_env_scaffold.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-env-scaffold

check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-first-attempt-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_task_frontier_certificate_first_attempt_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-first-attempt-no-go

check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-task-frontier-certificate-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_stronger_task_frontier_certificate_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-task-frontier-certificate-design

check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-task-frontier-certificate-feasibility-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_stronger_task_frontier_certificate_feasibility_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-task-frontier-certificate-feasibility-no-go

check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_pre_d2h_output_inert_proof_search_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-design

check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-first1-export:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_pre_d2h_output_inert_proof_search_first1_export.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-first1-export

check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-acceptance-first1:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_pre_d2h_output_inert_proof_acceptance_first1.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-acceptance-first1

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-pre-d2h-proof-family-or-scope-decision:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_pre_d2h_proof_family_or_scope_decision.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-pre-d2h-proof-family-or-scope-decision

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-pre-d2h-proof-family-first1-feasibility-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_pre_d2h_proof_family_first1_feasibility_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-pre-d2h-proof-family-first1-feasibility-no-go

check-fasim-gasal2-roadmap-phase7-post-v5-3-different-gpu-execution-design-or-scope-acceptance:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_different_gpu_execution_design_or_scope_acceptance.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-different-gpu-execution-design-or-scope-acceptance

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-design

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-spec-or-path-a-acceptance:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_spec_or_path_a_acceptance.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-spec-or-path-a-acceptance

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-spec-or-path-a-acceptance:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_first1_spec_or_path_a_acceptance.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-spec-or-path-a-acceptance

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-shadow-redirect:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_first1_shadow_redirect.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-shadow-redirect

check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-first1-shadow-env:
	bash ./scripts/check_fasim_gasal2_phase7_post_v5_3_new_gpu_engine_first1_shadow_env.sh

.PHONY: check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-first1-shadow-env

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-shadow-scaffold: check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-first1-shadow-env
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_first1_shadow_scaffold.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-shadow-scaffold

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-cuda-api:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_certificate_cuda_api.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-cuda-api

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-producer-first1:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_certificate_producer_first1.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-producer-first1

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-reducing-runtime-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_first1_reducing_runtime_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-reducing-runtime-no-go

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-design-after-first1-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_design_after_first1_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-design-after-first1-no-go

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-real-source-first1-spec-or-path-a-acceptance:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_real_source_first1_spec_or_path_a_acceptance.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-real-source-first1-spec-or-path-a-acceptance

check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-real-source-first1-shadow-env:
	bash ./scripts/check_fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_env.sh

.PHONY: check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-real-source-first1-shadow-env

check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-real-source-first1-shadow-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-real-source-first1-shadow-runtime-smoke

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-real-source-first1-shadow-scaffold: check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-real-source-first1-shadow-env check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-real-source-first1-shadow-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_real_source_first1_shadow_scaffold.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-real-source-first1-shadow-scaffold

check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-real-source-certificate-source-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-real-source-certificate-source-runtime-smoke

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-real-source-certificate-source: check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-real-source-certificate-source-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_real_source_certificate_source.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-real-source-certificate-source

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-design

check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-first1-shadow-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-first1-shadow-runtime-smoke

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-first1-shadow: check-fasim-gasal2-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-first1-shadow-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_first1_shadow.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-first1-shadow

check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-consumer-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_new_gpu_engine_pre_drop_work_drop_proof_consumer_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-consumer-no-go

check-fasim-gasal2-roadmap-phase7-post-v5-3-different-gpu-execution-design-after-consumer-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_v5_3_different_gpu_execution_design_after_consumer_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-v5-3-different-gpu-execution-design-after-consumer-no-go

check-fasim-gasal2-roadmap-phase7-post-consumer-gpu-scoreinfo-certificate-engine-spec-or-path-a-acceptance:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_consumer_gpu_scoreinfo_certificate_engine_spec_or_path_a_acceptance.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-consumer-gpu-scoreinfo-certificate-engine-spec-or-path-a-acceptance

check-fasim-gasal2-phase7-post-consumer-gpu-scoreinfo-certificate-engine-first1-shadow-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-post-consumer-gpu-scoreinfo-certificate-engine-first1-shadow-runtime-smoke

check-fasim-gasal2-roadmap-phase7-post-consumer-gpu-scoreinfo-certificate-engine-first1-shadow-scaffold: check-fasim-gasal2-phase7-post-consumer-gpu-scoreinfo-certificate-engine-first1-shadow-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_scaffold.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-consumer-gpu-scoreinfo-certificate-engine-first1-shadow-scaffold

check-fasim-gasal2-roadmap-phase7-post-consumer-gpu-scoreinfo-certificate-engine-first1-shadow-consumer-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_post_consumer_gpu_scoreinfo_certificate_engine_first1_shadow_consumer_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-post-consumer-gpu-scoreinfo-certificate-engine-first1-shadow-consumer-no-go

check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-scoreinfo-cert-engine-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_path_a_scope_acceptance_or_different_gpu_execution_design_after_scoreinfo_cert_engine_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-scoreinfo-cert-engine-no-go

check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-gpu-owned-consumer-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_owned_consumer_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-gpu-owned-consumer-no-go

check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-design-spec-or-path-a-acceptance:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gasal2_full_align_verifier_design_spec_or_path_a_acceptance.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-design-spec-or-path-a-acceptance

check-fasim-gasal2-phase7-full-align-verifier-first1-shadow-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_full_align_verifier_first1_shadow_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-full-align-verifier-first1-shadow-runtime-smoke

check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-first1-shadow-scaffold: check-fasim-gasal2-phase7-full-align-verifier-first1-shadow-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gasal2_full_align_verifier_first1_shadow_scaffold.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-first1-shadow-scaffold

check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-first1-shadow-consumer-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gasal2_full_align_verifier_first1_shadow_consumer_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-first1-shadow-consumer-no-go

check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-full-align-verifier-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_path_a_scope_acceptance_or_different_gpu_execution_design_after_full_align_verifier_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-full-align-verifier-no-go

check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-design-spec-or-path-a-acceptance:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_native_cuda_fasim_dp_engine_design_spec_or_path_a_acceptance.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-design-spec-or-path-a-acceptance

check-fasim-gasal2-phase7-native-cuda-fasim-dp-engine-first1-shadow-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_native_cuda_fasim_dp_engine_first1_shadow_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-native-cuda-fasim-dp-engine-first1-shadow-runtime-smoke

check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-first1-shadow-scaffold: check-fasim-gasal2-phase7-native-cuda-fasim-dp-engine-first1-shadow-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_native_cuda_fasim_dp_engine_first1_shadow_scaffold.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-first1-shadow-scaffold

check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-first1-shadow-consumer-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_native_cuda_fasim_dp_engine_first1_shadow_consumer_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-first1-shadow-consumer-no-go

check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-native-cuda-fasim-dp-engine-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_path_a_scope_acceptance_or_different_gpu_execution_design_after_native_cuda_fasim_dp_engine_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-native-cuda-fasim-dp-engine-no-go

check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-design-spec-or-path-a-acceptance:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gpu_upper_bound_reject_certificate_design_spec_or_path_a_acceptance.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-design-spec-or-path-a-acceptance

check-fasim-gasal2-phase7-gpu-upper-bound-reject-certificate-first1-shadow-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_gpu_upper_bound_reject_certificate_first1_shadow_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-gpu-upper-bound-reject-certificate-first1-shadow-runtime-smoke

check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-first1-shadow-scaffold: check-fasim-gasal2-phase7-gpu-upper-bound-reject-certificate-first1-shadow-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gpu_upper_bound_reject_certificate_first1_shadow_scaffold.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-first1-shadow-scaffold

check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-first1-shadow-consumer-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gpu_upper_bound_reject_certificate_first1_shadow_consumer_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-first1-shadow-consumer-no-go

check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-gpu-upper-bound-reject-certificate-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_path_a_scope_acceptance_or_different_gpu_execution_design_after_gpu_upper_bound_reject_certificate_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-gpu-upper-bound-reject-certificate-no-go

check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-design-spec-or-path-a-acceptance:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gpu_exact_work_unit_compaction_design_spec_or_path_a_acceptance.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-design-spec-or-path-a-acceptance

check-fasim-gasal2-phase7-gpu-exact-work-unit-compaction-first1-shadow-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_gpu_exact_work_unit_compaction_first1_shadow_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-gpu-exact-work-unit-compaction-first1-shadow-runtime-smoke

check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-first1-shadow-scaffold: check-fasim-gasal2-phase7-gpu-exact-work-unit-compaction-first1-shadow-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gpu_exact_work_unit_compaction_first1_shadow_scaffold.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-first1-shadow-scaffold

check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-first1-shadow-consumer-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gpu_exact_work_unit_compaction_first1_shadow_consumer_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-first1-shadow-consumer-no-go

check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-exact-work-unit-compaction-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_path_a_scope_acceptance_or_different_gpu_execution_design_after_exact_work_unit_compaction_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-exact-work-unit-compaction-no-go

check-fasim-gasal2-roadmap-new-gpu-execution-design-family-spec-or-path-a-acceptance-after-exact-work-unit-compaction-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_new_gpu_execution_design_family_spec_or_path_a_acceptance_after_exact_work_unit_compaction_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-new-gpu-execution-design-family-spec-or-path-a-acceptance-after-exact-work-unit-compaction-no-go

check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-external-new-path-b-design-after-exact-work-unit-compaction-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_path_a_scope_acceptance_or_external_new_path_b_design_after_exact_work_unit_compaction_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-external-new-path-b-design-after-exact-work-unit-compaction-no-go

check-fasim-gasal2-roadmap-phase7-gpu-owned-scoreinfo-consumer-design-spec-or-path-a-acceptance:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gpu_owned_scoreinfo_consumer_design_spec_or_path_a_acceptance.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gpu-owned-scoreinfo-consumer-design-spec-or-path-a-acceptance

check-fasim-gasal2-phase7-gpu-owned-scoreinfo-consumer-first1-shadow-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-gpu-owned-scoreinfo-consumer-first1-shadow-runtime-smoke

check-fasim-gasal2-roadmap-phase7-gpu-owned-scoreinfo-consumer-first1-shadow-scaffold: check-fasim-gasal2-phase7-gpu-owned-scoreinfo-consumer-first1-shadow-runtime-smoke
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_scaffold.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gpu-owned-scoreinfo-consumer-first1-shadow-scaffold

check-fasim-gasal2-roadmap-phase7-gpu-owned-scoreinfo-consumer-first1-shadow-consumer-no-go:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_gpu_owned_scoreinfo_consumer_first1_shadow_consumer_no_go.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-gpu-owned-scoreinfo-consumer-first1-shadow-consumer-no-go

check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-descriptor-emission-design:
	bash ./scripts/check_fasim_gasal2_roadmap_phase7_broad_restart_v5_cuda_descriptor_emission_design.sh

.PHONY: check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-descriptor-emission-design

check-fasim-gasal2-phase7-gate-c-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_gate_c_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-gate-c-runtime-smoke

characterize-fasim-gasal2-phase7-gate-c-first1:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_phase7_gate_c_first1.sh

.PHONY: characterize-fasim-gasal2-phase7-gate-c-first1

check-fasim-gasal2-phase7-gate-c-first1-result:
	bash ./scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh

.PHONY: check-fasim-gasal2-phase7-gate-c-first1-result

check-fasim-gasal2-roadmap-phase8-completion-decision:
	bash ./scripts/check_fasim_gasal2_roadmap_phase8_completion_decision.sh

.PHONY: check-fasim-gasal2-roadmap-phase8-completion-decision

check-fasim-gasal2-roadmap-current-state: check-fasim-gasal2-roadmap-phase-checklist check-fasim-gasal2-roadmap-gate-plan check-fasim-gasal2-roadmap-phase-roadmap check-fasim-gasal2-roadmap-phase-execution-plan check-fasim-gasal2-roadmap-phase-driver check-fasim-gasal2-roadmap-canonical-phase-plan check-fasim-gasal2-roadmap-goal-closure-phase-plan check-fasim-gasal2-roadmap-close-plan check-fasim-gasal2-roadmap-execution-ladder check-fasim-gasal2-roadmap-scope-or-broad-design-decision check-fasim-gasal2-roadmap-phase0-reproducibility check-fasim-gasal2-roadmap-phase1-scoped-product check-fasim-gasal2-roadmap-path-a-scoped-acceptance check-fasim-gasal2-roadmap-phase2-equivalence-first-convert check-fasim-gasal2-roadmap-phase3-preconvert-prune check-fasim-gasal2-roadmap-phase3-cigar-nt-prefilter-design check-fasim-gasal2-phase3-cigar-nt-prefilter-shadow check-fasim-gasal2-phase3-cigar-nt-prefilter-full-result check-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate check-fasim-gasal2-phase3-cigar-nt-prefilter-real-validate-full-result check-fasim-gasal2-roadmap-phase4-sort-topn check-fasim-gasal2-roadmap-phase5-archive-artifact check-fasim-gasal2-roadmap-phase6-workload-matrix check-fasim-gasal2-roadmap-phase7-broad-restart check-fasim-gasal2-roadmap-phase7-candidate-coverage check-fasim-gasal2-roadmap-phase7-candidate-coverage-stop check-fasim-gasal2-roadmap-phase7-next-reducer-design check-fasim-gasal2-roadmap-phase7-next-reducer-implementation-plan check-fasim-gasal2-roadmap-phase7-next-reducer-scaffold check-fasim-gasal2-roadmap-phase7-next-reducer-broad-gate check-fasim-gasal2-roadmap-phase7-broad-restart-v2-design check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-log-scaffold check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-replay check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-reducer check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-predictor check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-score-signal check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop-runtime check-fasim-gasal2-roadmap-phase7-broad-restart-v2-frontier-early-stop-runtime-first1 check-fasim-gasal2-roadmap-phase7-next-reducer-after-early-stop-design check-fasim-gasal2-roadmap-phase7-all-attempt-early-stop-runtime-first1 check-fasim-gasal2-roadmap-phase7-all-attempt-early-stop-runtime-first64 check-fasim-gasal2-roadmap-phase7-gate-c-gpu-candidate-generator-design check-fasim-gasal2-roadmap-phase7-gate-c-implementation-plan check-fasim-gasal2-roadmap-phase7-gate-c-first1 check-fasim-gasal2-roadmap-phase7-gate-c-stop-checkpoint check-fasim-gasal2-roadmap-phase7-current-broad-stop-decision check-fasim-gasal2-roadmap-phase7-broad-restart-v3-design check-fasim-gasal2-roadmap-phase7-broad-restart-v3-descriptor-source-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v3-pre-scoreinfo-descriptor-source-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v3-certificate-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v3-all-column-certificate-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v3-all-column-replay-stop check-fasim-gasal2-roadmap-phase7-broad-restart-v3-narrow-certificate-design check-fasim-gasal2-roadmap-phase7-broad-restart-v3-narrow-certificate-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v3-real-narrow-certificate-coverage-proof check-fasim-gasal2-roadmap-phase7-broad-restart-v3-next-source-design check-fasim-gasal2-roadmap-phase7-broad-restart-v3-next-source-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v3-strong-seed-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v3-attempt-coverage-seed-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v3-oracle-min-cover-replay-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v3-seed-path-stop check-fasim-gasal2-roadmap-phase7-broad-restart-v4-scoreinfo-native-design check-fasim-gasal2-roadmap-phase7-broad-restart-v4-legacy-byte-scoreinfo-shadow-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-scoreinfo-shadow-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-scoreinfo-source-replay-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v4-gpu-legacy-byte-scoreinfo-source-first64-broad-gate check-fasim-gasal2-roadmap-phase7-broad-restart-v5-fused-scoreinfo-consumer-design check-fasim-gasal2-roadmap-phase7-broad-restart-v5-implementation-plan check-fasim-gasal2-roadmap-phase7-broad-restart-v5-fused-scoreinfo-consumer-runtime-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-design check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-env-scaffold check-fasim-gasal2-roadmap-phase7-broad-restart-v5-true-pre-scoreinfo-descriptor-source-runtime-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-smoke check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cpu-authority-replay-first64-broad-gate check-fasim-gasal2-roadmap-phase7-post-v5-3-architecture-decision check-fasim-gasal2-roadmap-phase7-post-v5-3-new-architecture-design check-fasim-gasal2-roadmap-phase7-post-v5-3-gpu-consumer-summary-first-attempt-no-go check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-consumer-summary-design check-fasim-gasal2-roadmap-phase7-post-v5-3-task-frontier-certificate-design check-fasim-gasal2-roadmap-phase7-post-v5-3-stronger-task-frontier-certificate-feasibility-no-go check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-design check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-search-first1-export check-fasim-gasal2-roadmap-phase7-post-v5-3-pre-d2h-output-inert-proof-acceptance-first1 check-fasim-gasal2-roadmap-phase7-post-v5-3-new-pre-d2h-proof-family-or-scope-decision check-fasim-gasal2-roadmap-phase7-post-v5-3-new-pre-d2h-proof-family-first1-feasibility-no-go check-fasim-gasal2-roadmap-phase7-post-v5-3-different-gpu-execution-design-or-scope-acceptance check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-design check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-spec-or-path-a-acceptance check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-spec-or-path-a-acceptance check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-shadow-redirect check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-shadow-scaffold check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-cuda-api check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-certificate-producer-first1 check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-first1-reducing-runtime-no-go check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-design-after-first1-no-go check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-real-source-first1-spec-or-path-a-acceptance check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-real-source-first1-shadow-scaffold check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-real-source-certificate-source check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-design check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-first1-shadow check-fasim-gasal2-roadmap-phase7-post-v5-3-new-gpu-engine-pre-drop-work-drop-proof-consumer-no-go check-fasim-gasal2-roadmap-phase7-post-v5-3-different-gpu-execution-design-after-consumer-no-go check-fasim-gasal2-roadmap-phase7-post-consumer-gpu-scoreinfo-certificate-engine-spec-or-path-a-acceptance check-fasim-gasal2-roadmap-phase7-post-consumer-gpu-scoreinfo-certificate-engine-first1-shadow-scaffold check-fasim-gasal2-roadmap-phase7-post-consumer-gpu-scoreinfo-certificate-engine-first1-shadow-consumer-no-go check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-scoreinfo-cert-engine-no-go check-fasim-gasal2-roadmap-phase7-gpu-owned-scoreinfo-consumer-design-spec-or-path-a-acceptance check-fasim-gasal2-roadmap-phase7-gpu-owned-scoreinfo-consumer-first1-shadow-scaffold check-fasim-gasal2-roadmap-phase7-gpu-owned-scoreinfo-consumer-first1-shadow-consumer-no-go check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-gpu-owned-consumer-no-go check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-design-spec-or-path-a-acceptance check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-first1-shadow-scaffold check-fasim-gasal2-roadmap-phase7-gasal2-full-align-verifier-first1-shadow-consumer-no-go check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-full-align-verifier-no-go check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-design-spec-or-path-a-acceptance check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-first1-shadow-scaffold check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-first1-shadow-scaffold check-fasim-gasal2-roadmap-phase7-broad-restart-v5-cuda-descriptor-emission-design check-fasim-gasal2-roadmap-phase8-completion-decision
	bash ./scripts/check_fasim_gasal2_roadmap_current_state.sh

.PHONY: check-fasim-gasal2-roadmap-current-state

check-fasim-gasal2-roadmap-current-state: check-fasim-gasal2-roadmap-phase7-native-cuda-fasim-dp-engine-first1-shadow-consumer-no-go

check-fasim-gasal2-roadmap-current-state: check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-native-cuda-fasim-dp-engine-no-go

check-fasim-gasal2-roadmap-current-state: check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-design-spec-or-path-a-acceptance

check-fasim-gasal2-roadmap-current-state: check-fasim-gasal2-roadmap-phase7-gpu-upper-bound-reject-certificate-first1-shadow-consumer-no-go

check-fasim-gasal2-roadmap-current-state: check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-gpu-upper-bound-reject-certificate-no-go

check-fasim-gasal2-roadmap-current-state: check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-design-spec-or-path-a-acceptance

check-fasim-gasal2-roadmap-current-state: check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-first1-shadow-scaffold

check-fasim-gasal2-roadmap-current-state: check-fasim-gasal2-roadmap-phase7-gpu-exact-work-unit-compaction-first1-shadow-consumer-no-go

check-fasim-gasal2-roadmap-current-state: check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-different-gpu-execution-design-after-exact-work-unit-compaction-no-go

check-fasim-gasal2-roadmap-current-state: check-fasim-gasal2-roadmap-new-gpu-execution-design-family-spec-or-path-a-acceptance-after-exact-work-unit-compaction-no-go

check-fasim-gasal2-roadmap-current-state: check-fasim-gasal2-roadmap-path-a-scope-acceptance-or-external-new-path-b-design-after-exact-work-unit-compaction-no-go

check-fasim-gasal2-equivalence-first-convert:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/check_fasim_gasal2_equivalence_first_convert) bash ./scripts/check_fasim_gasal2_equivalence_first_convert.sh

.PHONY: check-fasim-gasal2-equivalence-first-convert

characterize-fasim-gasal2-cpu-vs-gasal2-full-plain:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/characterize_fasim_gasal2_cpu_vs_gasal2_full_plain_chr22) bash ./scripts/characterize_fasim_gasal2_cpu_vs_gasal2_full_plain.sh

.PHONY: characterize-fasim-gasal2-cpu-vs-gasal2-full-plain

check-fasim-gasal2-cpu-vs-gasal2-full-plain-result:
	bash ./scripts/check_fasim_gasal2_cpu_vs_gasal2_full_plain_result.sh

.PHONY: check-fasim-gasal2-cpu-vs-gasal2-full-plain-result

check-fasim-gasal2-full-plain-optimization-opportunity:
	bash ./scripts/check_fasim_gasal2_full_plain_optimization_opportunity.sh

.PHONY: check-fasim-gasal2-full-plain-optimization-opportunity

check-fasim-gasal2-limited-traceback-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_limited_traceback_smoke.sh

.PHONY: check-fasim-gasal2-limited-traceback-smoke

characterize-fasim-gasal2-limited-traceback-chr22:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct WORK=$(or $(WORK),$(CURDIR)/.tmp/characterize_fasim_gasal2_limited_traceback_chr22) bash ./scripts/characterize_fasim_gasal2_limited_traceback_chr22.sh

.PHONY: characterize-fasim-gasal2-limited-traceback-chr22

check-fasim-gasal2-limited-traceback-chr22-result:
	bash ./scripts/check_fasim_gasal2_limited_traceback_chr22_result.sh

.PHONY: check-fasim-gasal2-limited-traceback-chr22-result

check-fasim-gasal2-limited-traceback-attempt-export-parser:
	bash ./scripts/check_fasim_gasal2_limited_traceback_attempt_export_parser.sh

.PHONY: check-fasim-gasal2-limited-traceback-attempt-export-parser

check-fasim-gasal2-traceback-rejection-taxonomy-parser:
	bash ./scripts/check_fasim_gasal2_traceback_rejection_taxonomy_parser.sh

.PHONY: check-fasim-gasal2-traceback-rejection-taxonomy-parser

check-fasim-gasal2-traceback-rejection-taxonomy-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_traceback_rejection_taxonomy_smoke.sh

.PHONY: check-fasim-gasal2-traceback-rejection-taxonomy-smoke

characterize-fasim-gasal2-traceback-min-prealign-score-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_traceback_min_prealign_score_smoke.sh

.PHONY: characterize-fasim-gasal2-traceback-min-prealign-score-smoke

characterize-fasim-gasal2-traceback-min-prealign-score-chr22:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_traceback_min_prealign_score_chr22.sh

.PHONY: characterize-fasim-gasal2-traceback-min-prealign-score-chr22

check-fasim-gasal2-traceback-min-prealign-score-chr22-result:
	bash ./scripts/check_fasim_gasal2_traceback_min_prealign_score_chr22_result.sh

.PHONY: check-fasim-gasal2-traceback-min-prealign-score-chr22-result

check-fasim-gasal2-traceback-min-prealign-score-chr22-boundary-result:
	bash ./scripts/check_fasim_gasal2_traceback_min_prealign_score_chr22_boundary_result.sh

.PHONY: check-fasim-gasal2-traceback-min-prealign-score-chr22-boundary-result

check-fasim-gasal2-traceback-min-prealign-score-chr21-chr22-result:
	bash ./scripts/check_fasim_gasal2_traceback_min_prealign_score_chr21_chr22_result.sh

.PHONY: check-fasim-gasal2-traceback-min-prealign-score-chr21-chr22-result

check-fasim-gasal2-traceback-min-prealign-h19-calibration:
	bash ./scripts/check_fasim_gasal2_traceback_min_prealign_h19_calibration.sh

.PHONY: check-fasim-gasal2-traceback-min-prealign-h19-calibration

check-fasim-gasal2-traceback-threshold-estimator:
	bash ./scripts/check_fasim_gasal2_traceback_threshold_estimator.sh

.PHONY: check-fasim-gasal2-traceback-threshold-estimator

check-fasim-gasal2-traceback-threshold-calibration-preflight:
	bash ./scripts/check_fasim_gasal2_traceback_threshold_calibration_preflight.sh

.PHONY: check-fasim-gasal2-traceback-threshold-calibration-preflight

check-fasim-gasal2-traceback-threshold-window-sampler:
	bash ./scripts/check_fasim_gasal2_traceback_threshold_window_sampler.sh

.PHONY: check-fasim-gasal2-traceback-threshold-window-sampler

check-fasim-gasal2-traceback-guard-score-band-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_traceback_guard_score_band_smoke.sh

.PHONY: check-fasim-gasal2-traceback-guard-score-band-smoke

check-fasim-gasal2-stability-risk-attempts-parser:
	bash ./scripts/check_fasim_gasal2_stability_risk_attempts_parser.sh

.PHONY: check-fasim-gasal2-stability-risk-attempts-parser

check-fasim-gasal2-stability-upper-bound-parser:
	bash ./scripts/check_fasim_gasal2_stability_upper_bound_parser.sh

.PHONY: check-fasim-gasal2-stability-upper-bound-parser

check-fasim-gasal2-stability-proxy-rule-sweep-parser:
	bash ./scripts/check_fasim_gasal2_stability_proxy_rule_sweep_parser.sh

.PHONY: check-fasim-gasal2-stability-proxy-rule-sweep-parser

check-fasim-gasal2-convert-funnel-parser:
	bash ./scripts/check_fasim_gasal2_convert_funnel_parser.sh

.PHONY: check-fasim-gasal2-convert-funnel-parser

check-fasim-gasal2-preconvert-prune-shadow:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_preconvert_prune_shadow.sh

.PHONY: check-fasim-gasal2-preconvert-prune-shadow

check-fasim-gasal2-prune-authority-diff-parser:
	bash ./scripts/check_fasim_gasal2_prune_authority_diff_parser.sh

.PHONY: check-fasim-gasal2-prune-authority-diff-parser

check-fasim-gasal2-prune-frontier-safety-parser:
	bash ./scripts/check_fasim_gasal2_prune_frontier_safety_parser.sh

.PHONY: check-fasim-gasal2-prune-frontier-safety-parser

check-fasim-gasal2-preconvert-prune-readiness:
	bash ./scripts/check_fasim_gasal2_preconvert_prune_readiness.sh

.PHONY: check-fasim-gasal2-preconvert-prune-readiness

check-fasim-gasal2-task-frontier-proof-parser:
	bash ./scripts/check_fasim_gasal2_task_frontier_proof_parser.sh

.PHONY: check-fasim-gasal2-task-frontier-proof-parser

check-fasim-gasal2-task-frontier-proof-export:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_task_frontier_proof_export.sh

.PHONY: check-fasim-gasal2-task-frontier-proof-export

check-fasim-gasal2-sort-topn-breakdown-parser:
	bash ./scripts/check_fasim_gasal2_sort_topn_breakdown_parser.sh

.PHONY: check-fasim-gasal2-sort-topn-breakdown-parser

check-fasim-lite-full-equivalence:
	python3 ./scripts/check_fasim_lite_full_equivalence.py

check-fasim-gasal2-malat1-lite-equivalence-evidence:
	bash ./scripts/check_fasim_gasal2_malat1_lite_equivalence_evidence.sh

check-fasim-gasal2-malat1-tfosorted-equivalence-evidence:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_malat1_tfosorted_equivalence_evidence.sh

check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 MALAT1_RECORD_LIMIT=670 EXPECTED_ROWS=98713 CHECK_FULL=1 REPLAY_PROBE_MAX_TASKS=0 bash ./scripts/check_fasim_gasal2_malat1_tfosorted_equivalence_evidence.sh

check-fasim-gasal2-malat1-tfosorted-runtime-breakdown:
	bash ./scripts/check_fasim_gasal2_malat1_tfosorted_runtime_breakdown.sh

check-fasim-gasal2-malat1-no-probe-two-contract-runtime:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime.sh

check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 OUTPUT_MODE=tfosorted bash ./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime.sh

check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 CHECK_FIRST64=1 bash ./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime.sh

check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 CHECK_FIRST128=1 bash ./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime.sh

check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 CHECK_FIRST256=1 bash ./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime.sh

check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 MALAT1_RECORD_LIMIT=670 EXPECTED_ROWS=98713 CHECK_FULL=1 bash ./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime.sh

check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 MALAT1_RECORD_LIMIT=670 EXPECTED_ROWS=98713 CHECK_FULL=1 OUTPUT_MODE=tfosorted bash ./scripts/check_fasim_gasal2_malat1_no_probe_two_contract_runtime.sh

check-fasim-gasal2-scoreinfo-scoped-release-smoke: check-fasim-gasal2-malat1-no-probe-two-contract-runtime check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted check-fasim-gasal2-scoreinfo-scoped-milestone check-fasim-gasal2-scoreinfo-completion-gap check-fasim-gasal2-full-goal-decision

.PHONY: check-fasim-gasal2-scoreinfo-scoped-release-smoke

check-fasim-gasal2-top5-broader-validation:
	bash ./scripts/check_fasim_gasal2_top5_broader_validation.sh

check-fasim-gasal2-top5-product-readiness:
	bash ./scripts/check_fasim_gasal2_top5_product_readiness.sh

check-fasim-gasal2-top5-recommended-runtime:
	bash ./scripts/check_fasim_gasal2_top5_recommended_runtime.sh

check-fasim-gasal2-top5-scoped-completion-candidate:
	bash ./scripts/check_fasim_gasal2_top5_scoped_completion_candidate.sh

check-fasim-gasal2-top5-release-smoke: check-fasim-gasal2-topk-lite-wrapper-contract check-fasim-gasal2-formal-preset-examples check-fasim-gasal2-top5-product-readiness check-fasim-gasal2-top5-recommended-runtime check-fasim-gasal2-top5-scoped-completion-candidate

.PHONY: check-fasim-gasal2-top5-release-smoke

check-fasim-gasal2-top5-output-contract:
	bash ./scripts/check_fasim_gasal2_top5_output_contract.sh

check-fasim-gasal2-top5-activation-contract:
	python3 ./scripts/check_fasim_gasal2_top5_activation_contract.py

check-fasim-gasal2-topk-lite-wrapper-contract:
	bash ./scripts/check_fasim_gasal2_topk_lite_wrapper_contract.sh

check-fasim-gasal2-long-query-boundary:
	bash ./scripts/check_fasim_gasal2_long_query_boundary.sh

check-fasim-gasal2-long-query-segmented-plan:
	bash ./scripts/check_fasim_gasal2_long_query_segmented_plan.sh

check-fasim-gasal2-long-query-segmented-shadow-env:
	bash ./scripts/check_fasim_gasal2_long_query_segmented_shadow_env.sh

check-fasim-gasal2-long-query-segmented-shadow-default-off:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_long_query_segmented_shadow_default_off.sh

characterize-fasim-gasal2-long-query-segmented-shadow:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_long_query_segmented_shadow.sh

check-fasim-gasal2-long-query-segmented-shadow-probe:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_long_query_segmented_shadow_probe.sh

check-fasim-gasal2-long-query-segmented-score-prepass-shadow:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_long_query_segmented_score_prepass_shadow.sh

check-fasim-gasal2-long-query-segmented-score-prepass-reduction:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_long_query_segmented_score_prepass_reduction.sh

check-fasim-gasal2-long-query-segmented-score-prepass-batched:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_long_query_segmented_score_prepass_batched.sh

check-fasim-gasal2-long-query-segmented-score-prepass-replay:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_long_query_segmented_score_prepass_replay.sh

check-fasim-gasal2-long-query-segmented-scoreinfo-prune-mode:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_long_query_segmented_scoreinfo_prune_mode.sh

check-fasim-gasal2-long-query-segmented-workload-param:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_long_query_segmented_workload_param.sh

check-fasim-gasal2-long-query-segmented-replay-no-last:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_long_query_segmented_replay_no_last.sh

check-fasim-gasal2-long-query-segmented-replay-rank-cutoff:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_long_query_segmented_replay_rank_cutoff.sh

check-fasim-gasal2-long-query-segmented-replay-threshold-score-rank3:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_long_query_segmented_replay_threshold_score_rank3.sh

check-fasim-gasal2-long-query-segmented-no-last-scaling-result:
	bash ./scripts/check_fasim_gasal2_long_query_segmented_no_last_scaling_result.sh

check-fasim-gasal2-neat1-segmented-replay-result:
	bash ./scripts/check_fasim_gasal2_neat1_segmented_replay_result.sh

check-fasim-gasal2-long-query-current-stop:
	bash ./scripts/check_fasim_gasal2_long_query_current_stop.sh

check-fasim-gasal2-long-query-next-architecture-plan:
	bash ./scripts/check_fasim_gasal2_long_query_next_architecture_plan.sh

check-fasim-gasal2-long-query-next-architecture-decision:
	bash ./scripts/check_fasim_gasal2_long_query_next_architecture_decision.sh

check-fasim-long-query-streaming-scoreinfo-design:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_design.sh

check-fasim-long-query-streaming-scoreinfo-shared-smem-boundary:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_shared_smem_boundary.sh

check-fasim-long-query-streaming-scoreinfo-fused-minscore-design:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_fused_minscore_design.sh

check-fasim-long-query-streaming-scoreinfo-fused-minscore-prototype:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_fused_minscore_prototype.sh

check-fasim-long-query-streaming-scoreinfo-fused-minscore-boundary:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_fused_minscore_boundary.sh

check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_design.sh

check-fasim-long-query-streaming-scoreinfo-shadow-skeleton:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_shadow_skeleton.sh

check-fasim-long-query-streaming-scoreinfo-shadow-active:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_shadow_active.sh

check-fasim-long-query-streaming-scoreinfo-shadow-mismatch-detail:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_shadow_mismatch_detail.sh

check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_shadow_legacy_byte.sh

check-fasim-long-query-streaming-scoreinfo-shadow-legacy-byte-shared:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_shadow_legacy_byte_shared.sh

check-fasim-long-query-streaming-scoreinfo-shadow-gpu-minscore:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_shadow_gpu_minscore.sh

check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-shadow:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_shadow.sh

check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-trust:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_trust.sh

check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-runner:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_two_contract_bridge_runner.sh

check-fasim-long-query-streaming-scoreinfo-shadow-gpu-minscore-hot:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_shadow_gpu_minscore_hot.sh

check-fasim-long-query-streaming-scoreinfo-realpath-prototype:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_realpath_prototype.sh

check-fasim-long-query-streaming-scoreinfo-realpath-trust:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_streaming_scoreinfo_realpath_trust.sh

check-fasim-long-query-streaming-scoreinfo-trust-targets:
	bash ./scripts/check_fasim_long_query_streaming_scoreinfo_trust_targets.sh

characterize-fasim-long-query-streaming-scoreinfo-realpath:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_long_query_streaming_scoreinfo_realpath.sh

characterize-fasim-long-query-streaming-scoreinfo-realpath-trust:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_long_query_streaming_scoreinfo_realpath_trust.sh

characterize-fasim-long-query-streaming-scoreinfo-malat1-full-trust:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_long_query_streaming_scoreinfo_malat1_full_trust.sh

characterize-fasim-long-query-streaming-scoreinfo-neat1-trust:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_long_query_streaming_scoreinfo_neat1_trust.sh

characterize-fasim-long-query-streaming-scoreinfo-neat1-first64-trust:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_long_query_streaming_scoreinfo_neat1_first64_trust.sh

characterize-fasim-long-query-streaming-scoreinfo-hot:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_long_query_streaming_scoreinfo_hot.sh

check-fasim-gasal2-long-query-exact-tile-oracle-export:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_long_query_exact_tile_oracle_export.sh

check-fasim-gasal2-long-query-exact-tile-descriptors:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_long_query_exact_tile_descriptors.sh

check-fasim-gasal2-long-query-exact-tile-candidate-equivalence:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_long_query_exact_tile_candidate_equivalence.sh

check-fasim-gasal2-long-query-exact-tile-candidate-equivalence-result:
	bash ./scripts/check_fasim_gasal2_long_query_exact_tile_candidate_equivalence_result.sh

check-fasim-gasal2-long-query-exact-tile-overlap-probe:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_long_query_exact_tile_overlap_probe.sh

check-fasim-gasal2-long-query-exact-tile-overlap-result:
	bash ./scripts/check_fasim_gasal2_long_query_exact_tile_overlap_result.sh

check-fasim-long-query-exact-column-scoreinfo-shadow:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_exact_column_scoreinfo_shadow.sh

check-fasim-long-query-exact-column-scoreinfo-shadow-smem-optin:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_long_query_exact_column_scoreinfo_shadow_smem_optin.sh

check-fasim-gasal2-long-query-segmented-record-limit:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_long_query_segmented_record_limit.sh

check-fasim-gasal2-long-query-segmented-replay-score-order:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_long_query_segmented_replay_score_order.sh

check-fasim-gasal2-long-query-segmented-pruned-traceback-shadow:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_long_query_segmented_pruned_traceback_shadow.sh

check-fasim-gasal2-top5-formal-gate: check-fasim-gasal2-formal-makefile-gate check-fasim-gasal2-reproducible-setup check-fasim-gasal2-short-query-top5-readiness check-fasim-gasal2-top5-scoreinfo-milestone check-fasim-gasal2-top5-output-contract check-fasim-gasal2-top5-activation-contract check-fasim-gasal2-topk-lite-wrapper-contract check-fasim-gasal2-long-query-boundary check-fasim-gasal2-top5-binary-guard check-fasim-top5-gasal2-gpu-scoreinfo-default-off check-fasim-top5-gasal2-gpu-scoreinfo-env check-fasim-sharded-gasal2-top5-prune-runner check-fasim-gasal2-column-pruned-preset-top5-matrix check-fasim-gasal2-top5-lowercase-input check-fasim-gasal2-formal-preset-examples check-fasim-exact-scoreinfo-gpu-examples-gate

check-fasim-gasal2-single-pass-topn:
	bash ./scripts/check_fasim_gasal2_single_pass_topn.sh

check-fasim-gasal2-single-pass-topn-sweep:
	bash ./scripts/check_fasim_gasal2_single_pass_topn_sweep.sh

check-fasim-exact-scoreinfo-gpu-examples-gate:
	bash ./scripts/check_fasim_exact_scoreinfo_gpu_examples_gate.sh

investigate-fasim-gasal2-topk-lite-runner-legacy:
	ALLOW_LEGACY_GASAL2_TOPK_LITE=1 BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_topk_lite_runner.sh

investigate-fasim-gasal2-topk-lite-runner-examples-legacy:
	ALLOW_LEGACY_GASAL2_TOPK_LITE=1 BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct CASE_PRESET=examples bash ./scripts/check_fasim_gasal2_topk_lite_runner.sh

check-fasim-exact-column-legacy-score-gpu-replacement:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_exact_column_legacy_score_gpu_replacement.sh

check-fasim-top5-gasal2-gpu-scoreinfo-env:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_top5_gasal2_gpu_scoreinfo_env.sh

check-fasim-top5-gasal2-gpu-scoreinfo-default-off:
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_top5_gasal2_gpu_scoreinfo_default_off.sh

check-fasim-sharded-worker-gpu-env-hygiene:
	bash ./scripts/check_fasim_sharded_worker_gpu_env_hygiene.sh

.PHONY: build build-avx2 build-openmp build-openmp-avx2 \
		build-cuda build-cuda-avx2 build-cuda-native-ada check-cuda-native-ada-fatbin \
		build-fasim build-fasim-cuda setup-gasal2 build-gasal2 build-fasim-gasal2 \
		oracle-sample check-sample oracle-smoke check-smoke \
		check-sample-row check-sample-wavefront check-smoke-row check-smoke-wavefront \
		check-smoke-avx2 check-sample-avx2 oracle-matrix check-matrix check-matrix-row \
		check-matrix-wavefront check-matrix-avx2 check-sample-openmp-1 check-sample-openmp-par \
		check-smoke-openmp-1 check-smoke-openmp-par check-matrix-openmp-1 \
		check-matrix-openmp-par benchmark-sample benchmark-smoke benchmark-sample-cuda benchmark-smoke-cuda \
		benchmark-sample-cuda-avx2 benchmark-smoke-cuda-avx2 benchmark-sample-cuda-fast benchmark-smoke-cuda-fast \
		benchmark-sample-cuda-traceback benchmark-smoke-cuda-traceback benchmark-sample-cuda-sim-full benchmark-smoke-cuda-sim-full \
		benchmark-sample-cuda-window-pipeline benchmark-sample-cuda-vs-fasim benchmark-sample-cuda-throughput-compare benchmark-sample-cuda-vs-fasim-two-stage benchmark-fasim-batch benchmark-fasim-throughput-sweep benchmark-fasim-sharded-worker-scaling benchmark-fasim-sharded-worker-workload-matrix \
		benchmark-two-stage-threshold-modes benchmark-two-stage-threshold-heavy-microanchors \
		benchmark-sample-cuda-vs-fasim-two-stage-prealign \
		check-sample-cuda check-smoke-cuda \
		check-sample-cuda-sim check-smoke-cuda-sim check-matrix-cuda-sim \
		check-sample-cuda-sim-region check-smoke-cuda-sim-region check-matrix-cuda-sim-region \
		check-sample-cuda-sim-region-locate check-smoke-cuda-sim-region-locate \
		check-sample-cuda-sim-traceback-strict check-smoke-cuda-sim-traceback-strict \
		check-smoke-cuda-sim-full \
		check-smoke-cuda-avx2 check-matrix-cuda check-matrix-cuda-avx2 \
		build-fasim-cigar-test check-fasim-cigar \
		build-fasim-transferstring-table-test build-fasim-ssw-profile-cache-test build-ssw-avx2-direct-test \
		check-fasim-ssw-profile-cache-env check-fasim-ssw-avx2-direct check-fasim-ssw-avx2-digest \
			check-fasim-gasal2-longtarget-bridge-digest check-fasim-gasal2-gpu-scoreinfo-top5 check-fasim-gasal2-scoreinfo-prune-top5-matrix check-fasim-gasal2-scoreinfo-prune-top5-chr22-2mb check-fasim-sharded-gasal2-top5-prune-runner check-fasim-gasal2-sharded-characterization-env characterize-fasim-gasal2-prealign-max-tasks-probe check-fasim-gasal2-prealign-max-tasks-probe check-fasim-gasal2-prealign-max-tasks-chr21-chr22-result check-fasim-gasal2-scoreinfo-prune-sweep check-fasim-exact-scoreinfo-gpu-max-per-task-sweep check-fasim-exact-scoreinfo-gpu-pruned-output characterize-fasim-exact-scoreinfo-gpu-column-pruned-output check-fasim-exact-scoreinfo-gpu-column-pruned-output characterize-fasim-exact-scoreinfo-gpu-column-pruned-output-matrix check-fasim-exact-scoreinfo-gpu-column-pruned-output-matrix characterize-fasim-gasal2-column-pruned-preset-top5-matrix check-fasim-gasal2-column-pruned-preset-top5-matrix check-fasim-gasal2-top5-binary-guard check-fasim-gasal2-top5-lowercase-input check-fasim-gasal2-formal-preset-examples check-fasim-gasal2-reproducible-setup check-fasim-gasal2-short-query-top5-readiness check-fasim-gasal2-short-query-top5-tfo-contract check-fasim-gasal2-formal-makefile-gate check-fasim-gasal2-top5-scoreinfo-milestone check-fasim-gasal2-top5-scoreinfo-milestone-result check-fasim-gasal2-top5-scoreinfo-meg3-grouped-result check-fasim-gasal2-top5-wrapper-meg3-grouped-result check-fasim-gasal2-scoreinfo-current-state check-fasim-gasal2-scoreinfo-scoped-milestone check-fasim-gasal2-scoreinfo-scoped-milestone-rollup check-fasim-gasal2-scoreinfo-scoped-release-smoke check-fasim-lite-full-equivalence check-fasim-gasal2-malat1-lite-equivalence-evidence check-fasim-gasal2-malat1-tfosorted-equivalence-evidence check-fasim-gasal2-malat1-tfosorted-equivalence-evidence-full check-fasim-gasal2-malat1-tfosorted-runtime-breakdown check-fasim-gasal2-malat1-no-probe-two-contract-runtime check-fasim-gasal2-malat1-no-probe-two-contract-runtime-tfosorted check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first64 check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first128 check-fasim-gasal2-malat1-no-probe-two-contract-runtime-first256 check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full check-fasim-gasal2-malat1-no-probe-two-contract-runtime-full-tfosorted check-fasim-gasal2-neat1-speed-ceiling check-fasim-gasal2-neat1-next-architecture-requirements check-fasim-gasal2-broad-co-designed-scoreinfo-consumer-plan check-fasim-gasal2-broad-scoreinfo-consumer-shadow-env check-fasim-gasal2-broad-scoreinfo-consumer-triplex-export check-fasim-gasal2-broad-scoreinfo-attempt-planner check-fasim-gasal2-broad-replacement-consumer-shadow check-fasim-gasal2-broad-neat1-first64-result check-fasim-gasal2-attempt-consumer-shadow-plan check-fasim-gasal2-attempt-consumer-shadow-env check-fasim-gasal2-attempt-consumer-shadow-selection check-fasim-gasal2-replacement-consumer-shadow-requirements check-fasim-gasal2-replacement-consumer-shadow-env check-fasim-gasal2-replacement-consumer-shadow-runtime-smoke check-fasim-gasal2-score-prepass-state-machine-consumer check-fasim-gasal2-score-prepass-state-machine-consumer-env check-fasim-gasal2-score-prepass-state-machine-consumer-runtime-smoke check-fasim-gasal2-score-prepass-state-machine-consumer-segmented-runtime-smoke check-fasim-gasal2-score-prepass-state-machine-characterization check-fasim-gasal2-score-prepass-state-machine-trust check-fasim-gasal2-score-prepass-state-machine-trust-runtime-smoke check-fasim-gasal2-score-prepass-state-machine-stop check-fasim-long-query-streaming-scoreinfo-trust-runner check-fasim-long-query-streaming-scoreinfo-trust-group32-runner check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner check-fasim-long-query-streaming-scoreinfo-trust-group32-segmented-probe-runner check-fasim-long-query-streaming-scoreinfo-trust-group32-audited-runner-real check-fasim-long-query-streaming-scoreinfo-neat1-audited-runner-real check-fasim-long-query-streaming-scoreinfo-neat1-runtime-boundary check-fasim-long-query-streaming-scoreinfo-fused-minscore-design check-fasim-long-query-streaming-scoreinfo-fused-minscore-prototype check-fasim-long-query-streaming-scoreinfo-fused-minscore-boundary check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-design check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-shadow check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-trust check-fasim-long-query-streaming-scoreinfo-two-contract-bridge-runner check-fasim-long-query-streaming-scoreinfo-two-contract-trust-characterization check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first64 check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first128 check-fasim-long-query-streaming-scoreinfo-two-contract-group32-audited-runner-real-first256 check-fasim-long-query-streaming-scoreinfo-trust-runner-real characterize-fasim-long-query-streaming-scoreinfo-trust-runner characterize-fasim-long-query-streaming-scoreinfo-trust-runner-workers characterize-fasim-long-query-streaming-scoreinfo-trust-runner-groups characterize-fasim-long-query-streaming-scoreinfo-trust-runner-group32-scaling characterize-fasim-long-query-streaming-scoreinfo-trust-runner-malat1-full-group32 characterize-fasim-long-query-streaming-scoreinfo-two-contract-trust check-fasim-gasal2-top5-broader-validation check-fasim-gasal2-top5-product-readiness check-fasim-gasal2-top5-recommended-runtime check-fasim-gasal2-top5-output-contract check-fasim-gasal2-top5-activation-contract check-fasim-gasal2-topk-lite-wrapper-contract check-fasim-gasal2-long-query-boundary check-fasim-gasal2-long-query-segmented-plan check-fasim-gasal2-long-query-segmented-shadow-env check-fasim-gasal2-long-query-segmented-shadow-default-off characterize-fasim-gasal2-long-query-segmented-shadow check-fasim-gasal2-long-query-segmented-shadow-probe check-fasim-gasal2-long-query-segmented-score-prepass-shadow check-fasim-gasal2-long-query-segmented-score-prepass-reduction check-fasim-gasal2-long-query-segmented-score-prepass-batched check-fasim-gasal2-long-query-segmented-score-prepass-replay check-fasim-gasal2-long-query-segmented-scoreinfo-prune-mode check-fasim-gasal2-long-query-segmented-replay-no-last check-fasim-gasal2-long-query-segmented-no-last-scaling-result check-fasim-gasal2-long-query-segmented-record-limit check-fasim-gasal2-long-query-segmented-replay-score-order check-fasim-gasal2-long-query-segmented-pruned-traceback-shadow check-fasim-long-query-exact-column-scoreinfo-shadow check-fasim-long-query-streaming-scoreinfo-realpath-trust check-fasim-long-query-streaming-scoreinfo-trust-targets characterize-fasim-long-query-streaming-scoreinfo-realpath characterize-fasim-long-query-streaming-scoreinfo-realpath-trust characterize-fasim-long-query-streaming-scoreinfo-malat1-full-trust characterize-fasim-long-query-streaming-scoreinfo-neat1-trust characterize-fasim-long-query-streaming-scoreinfo-neat1-first64-trust check-fasim-gasal2-top5-formal-gate check-fasim-top5-gasal2-gpu-scoreinfo-default-off check-fasim-top5-gasal2-gpu-scoreinfo-env check-fasim-gasal2-single-pass-topn check-fasim-gasal2-single-pass-topn-sweep check-fasim-exact-scoreinfo-gpu-examples-gate investigate-fasim-gasal2-topk-lite-runner-legacy investigate-fasim-gasal2-topk-lite-runner-examples-legacy \
		build-prealign-shared-test check-prealign-shared \
		build-sim-scan-cuda-true-batch-reduce-test check-sim-scan-cuda-true-batch-reduce \
			build-sim-region-bucketed-true-batch-test check-sim-region-bucketed-true-batch \
			build-sim-region-scheduler-shape-telemetry-test check-sim-region-scheduler-shape-telemetry \
			build-sim-region-single-request-direct-reduce-test check-sim-region-single-request-direct-reduce check-sim-region-direct-reduce-profile-telemetry check-sim-region-direct-reduce-pipeline-telemetry check-sim-region-direct-reduce-fused-dp check-sim-region-direct-reduce-coop-dp \
			check-sim-initial-safe-store-handoff-region-deferred-composition \
			build-sim-cuda-proposal-select-test check-sim-cuda-proposal-select \
		build-sim-traceback-cuda-batch-test check-sim-traceback-cuda-batch \
		build-sim-initial-cuda-merge-test check-sim-initial-cuda-merge \
		build-sim-initial-context-apply-chunk-skip-test check-sim-initial-context-apply-chunk-skip \
		build-sim-initial-chunked-handoff-test check-sim-initial-chunked-handoff \
		check-sim-initial-chunked-handoff-matrix \
		build-sim-initial-exact-frontier-replay-test check-sim-initial-exact-frontier-replay \
		build-sim-initial-cpu-frontier-fast-apply-test check-sim-initial-cpu-frontier-fast-apply \
		build-sim-frontier-epoch-oracle-test check-sim-frontier-epoch-oracle \
		build-sim-frontier-epoch-shadow-test check-sim-frontier-epoch-shadow \
		build-sim-initial-reduce-semantics-test check-sim-initial-reduce-semantics \
		build-sim-initial-ordered-segmented-v3-exactness-test check-sim-initial-ordered-segmented-v3-exactness \
		build-sim-initial-frontier-transducer-shadow-test check-sim-initial-frontier-transducer-shadow \
		build-sim-initial-frontier-transducer-segmented-shadow-test check-sim-initial-frontier-transducer-segmented-shadow \
		build-sim-initial-frontier-compact-transducer-oracle-test check-sim-initial-frontier-compact-transducer-oracle \
		build-sim-initial-summary-packed-d2h-test check-sim-initial-summary-packed-d2h \
			build-sim-initial-summary-host-copy-elision-test check-sim-initial-summary-host-copy-elision \
				build-sim-safe-window-geometry-v2-test check-sim-safe-window-geometry-v2 \
				build-sim-safe-window-fine-execution-test check-sim-safe-window-fine-execution \
				build-sim-locate-update-test check-sim-locate-update \
			build-exact-sim-two-stage-threshold-test check-exact-sim-two-stage-threshold \
				check-calc-score-cuda-v2-shadow check-benchmark-telemetry check-benchmark-worker-telemetry check-fasim-throughput-preset check-benchmark-throughput-comparator check-fasim-throughput-sweep \
			check-make-anchor-shards check-summarize-throughput-frontier check-two-stage-frontier-sweep check-summarize-two-stage-frontier check-sim-cuda-initial-proposal-v2-exactness \
		check-sim-cuda-window-pipeline check-sim-cuda-window-pipeline-overlap check-project-whole-genome-runtime \
		check-sim-cuda-region-docs check-longtarget-lite-output check-fasim-sharded-runner check-fasim-sharded-scheduler check-fasim-sharded-runner-resume check-fasim-sharded-cpu-affinity check-fasim-sharded-worker-readiness-matrix check-fasim-shard-balance check-fasim-sharded-straggler-analysis check-two-stage-threshold-modes check-two-stage-threshold-heavy-microanchors \
		check-compare-two-stage-panel-summaries check-summarize-two-stage-panel-decision \
		check-rerun-two-stage-panel-with-candidate-env check-rerun-two-stage-panel-task-rerun-runtime check-analyze-two-stage-selector-candidate-classes \
		check-replay-two-stage-non-empty-candidate-classes check-analyze-two-stage-task-ambiguity \
		check-replay-two-stage-task-level-rerun check-search-two-stage-task-trigger-rankings check-two-stage-task-rerun-runtime
