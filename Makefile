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

cuda/calc_score_cuda.o: cuda/calc_score_cuda.cu cuda/calc_score_cuda.h
	$(NVCC) $(CUDA_CXXFLAGS) -c $< -o $@

cuda/sim_scan_cuda.o: cuda/sim_scan_cuda.cu cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h
	$(NVCC) $(CUDA_CXXFLAGS) -c $< -o $@

cuda/prealign_cuda.o: cuda/prealign_cuda.cu cuda/prealign_cuda.h
	$(NVCC) $(CUDA_CXXFLAGS) -c $< -o $@

cuda/sim_traceback_cuda.o: cuda/sim_traceback_cuda.cu cuda/sim_traceback_cuda.h cuda/sim_cuda_runtime.h
	$(NVCC) $(CUDA_CXXFLAGS) -c $< -o $@

cuda/sim_locate_cuda.o: cuda/sim_locate_cuda.cu cuda/sim_locate_cuda.h cuda/sim_cuda_runtime.h
	$(NVCC) $(CUDA_CXXFLAGS) -c $< -o $@

build-cuda: $(CUDA_TARGET)

$(CUDA_TARGET): longtarget.cpp $(HEADERS) $(CUDA_OBJ)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) longtarget.cpp $(CUDA_OBJ) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

build-cuda-avx2:
	$(MAKE) CUDA_TARGET=longtarget_cuda_avx2 SIMD_FLAGS=-mavx2 build-cuda

FASIM_CXXFLAGS ?= -O3 -std=c++11 -pthread
FASIM_SIMD_FLAGS ?= -msse2
FASIM_TARGET ?= fasim_longtarget_x86
FASIM_CUDA_TARGET ?= fasim_longtarget_cuda
FASIM_SOURCES := fasim/Fasim-LongTarget.cpp fasim/ssw_cpp.cpp fasim/sswNew.cpp
FASIM_HEADERS := $(wildcard fasim/*.h)

build-fasim: $(FASIM_TARGET)

$(FASIM_TARGET): $(FASIM_SOURCES) $(FASIM_HEADERS) cuda/prealign_cuda_stub.cpp cuda/prealign_cuda.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(FASIM_SOURCES) cuda/prealign_cuda_stub.cpp $(LDFLAGS) $(LDLIBS) -o $@

build-fasim-cuda: $(FASIM_CUDA_TARGET)

$(FASIM_CUDA_TARGET): $(FASIM_SOURCES) $(FASIM_HEADERS) cuda/prealign_cuda.o cuda/prealign_cuda.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(FASIM_SOURCES) cuda/prealign_cuda.o $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

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

FASIM_CIGAR_TEST_TARGET ?= tests/test_fasim_cigar_identity
FASIM_CIGAR_TEST_SOURCES := tests/test_fasim_cigar_identity.cpp fasim/ssw_cpp.cpp fasim/sswNew.cpp cuda/prealign_cuda_stub.cpp

PREALIGN_SHARED_TEST_TARGET ?= tests/test_prealign_shared
PREALIGN_SHARED_TEST_SOURCES := tests/test_prealign_shared.cpp cuda/prealign_cuda_stub.cpp

SIM_SCAN_BATCH_TEST_TARGET ?= tests/test_sim_scan_batch
SIM_SCAN_BATCH_TEST_SOURCES := tests/test_sim_scan_batch.cpp cuda/sim_scan_cuda_stub.cpp

SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_TARGET ?= tests/test_sim_scan_cuda_true_batch_reduce
SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_SOURCES := tests/test_sim_scan_cuda_true_batch_reduce.cpp cuda/sim_scan_cuda.o

SIM_CUDA_PROPOSAL_SELECT_TEST_TARGET ?= tests/test_sim_cuda_proposal_select
SIM_CUDA_PROPOSAL_SELECT_TEST_SOURCES := tests/test_sim_cuda_proposal_select.cpp cuda/sim_scan_cuda.o

SIM_TRACEBACK_CUDA_BATCH_TEST_TARGET ?= tests/test_sim_traceback_cuda_batch
SIM_TRACEBACK_CUDA_BATCH_TEST_SOURCES := tests/test_sim_traceback_cuda_batch.cpp cuda/sim_traceback_cuda.o

SIM_INITIAL_CUDA_MERGE_TEST_TARGET ?= tests/test_sim_initial_cuda_merge
SIM_INITIAL_CUDA_MERGE_TEST_SOURCES := tests/test_sim_initial_cuda_merge.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_LOCATE_UPDATE_TEST_TARGET ?= tests/test_sim_locate_update
SIM_LOCATE_UPDATE_TEST_SOURCES := tests/test_sim_locate_update.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_SAFE_WORKSET_CUDA_TEST_TARGET ?= tests/test_sim_safe_workset_cuda
SIM_SAFE_WORKSET_CUDA_TEST_SOURCES := tests/test_sim_safe_workset_cuda.cpp cuda/sim_scan_cuda.o cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

SIM_RESIDENCY_FRONTIER_TEST_TARGET ?= tests/test_sim_residency_frontier
SIM_RESIDENCY_FRONTIER_TEST_SOURCES := tests/test_sim_residency_frontier.cpp cuda/sim_scan_cuda.o cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

EXACT_SIM_TWO_STAGE_THRESHOLD_TEST_TARGET ?= tests/test_exact_sim_two_stage_threshold
EXACT_SIM_TWO_STAGE_THRESHOLD_TEST_SOURCES := tests/test_exact_sim_two_stage_threshold.cpp cuda/prealign_cuda_stub.cpp cuda/sim_scan_cuda_stub.cpp cuda/sim_traceback_cuda_stub.cpp cuda/sim_locate_cuda_stub.cpp

build-fasim-cigar-test: $(FASIM_CIGAR_TEST_TARGET)

build-prealign-shared-test: $(PREALIGN_SHARED_TEST_TARGET)

build-sim-scan-batch-test: $(SIM_SCAN_BATCH_TEST_TARGET)

build-sim-scan-cuda-true-batch-reduce-test: $(SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_TARGET)

build-sim-cuda-proposal-select-test: $(SIM_CUDA_PROPOSAL_SELECT_TEST_TARGET)

build-sim-traceback-cuda-batch-test: $(SIM_TRACEBACK_CUDA_BATCH_TEST_TARGET)

build-sim-initial-cuda-merge-test: $(SIM_INITIAL_CUDA_MERGE_TEST_TARGET)

build-sim-locate-update-test: $(SIM_LOCATE_UPDATE_TEST_TARGET)

build-sim-safe-workset-cuda-test: $(SIM_SAFE_WORKSET_CUDA_TEST_TARGET)

build-sim-residency-frontier-test: $(SIM_RESIDENCY_FRONTIER_TEST_TARGET)

build-exact-sim-two-stage-threshold-test: $(EXACT_SIM_TWO_STAGE_THRESHOLD_TEST_TARGET)

$(FASIM_CIGAR_TEST_TARGET): $(FASIM_CIGAR_TEST_SOURCES) $(FASIM_HEADERS) cuda/prealign_cuda.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(FASIM_CIGAR_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(PREALIGN_SHARED_TEST_TARGET): $(PREALIGN_SHARED_TEST_SOURCES) cuda/prealign_cuda.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(PREALIGN_SHARED_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_SCAN_BATCH_TEST_TARGET): $(SIM_SCAN_BATCH_TEST_SOURCES) cuda/sim_scan_cuda.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_SCAN_BATCH_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_TARGET): $(SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_SOURCES) cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_SCAN_CUDA_TRUE_BATCH_REDUCE_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_CUDA_PROPOSAL_SELECT_TEST_TARGET): $(SIM_CUDA_PROPOSAL_SELECT_TEST_SOURCES) cuda/sim_scan_cuda.h cuda/sim_cuda_runtime.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_CUDA_PROPOSAL_SELECT_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_TRACEBACK_CUDA_BATCH_TEST_TARGET): $(SIM_TRACEBACK_CUDA_BATCH_TEST_SOURCES) cuda/sim_traceback_cuda.h cuda/sim_cuda_runtime.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_TRACEBACK_CUDA_BATCH_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

$(SIM_INITIAL_CUDA_MERGE_TEST_TARGET): $(SIM_INITIAL_CUDA_MERGE_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_INITIAL_CUDA_MERGE_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_LOCATE_UPDATE_TEST_TARGET): $(SIM_LOCATE_UPDATE_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h cuda/sim_locate_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(FASIM_CXXFLAGS) $(ARCH_FLAGS) $(FASIM_SIMD_FLAGS) $(SIM_LOCATE_UPDATE_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) -o $@

$(SIM_SAFE_WORKSET_CUDA_TEST_TARGET): $(SIM_SAFE_WORKSET_CUDA_TEST_SOURCES) sim.h cuda/sim_scan_cuda.h cuda/sim_traceback_cuda.h cuda/sim_locate_cuda.h stats.h rules.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(ARCH_FLAGS) $(SIMD_FLAGS) $(PTHREAD_FLAGS) $(SIM_SAFE_WORKSET_CUDA_TEST_SOURCES) $(LDFLAGS) $(LDLIBS) $(CUDA_LDFLAGS) -o $@

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

check-sim-cuda-proposal-select: $(SIM_CUDA_PROPOSAL_SELECT_TEST_TARGET)
	./$(SIM_CUDA_PROPOSAL_SELECT_TEST_TARGET)

check-sim-traceback-cuda-batch: $(SIM_TRACEBACK_CUDA_BATCH_TEST_TARGET)
	./$(SIM_TRACEBACK_CUDA_BATCH_TEST_TARGET)

check-sim-initial-cuda-merge: $(SIM_INITIAL_CUDA_MERGE_TEST_TARGET)
	./$(SIM_INITIAL_CUDA_MERGE_TEST_TARGET)

check-sim-locate-update: $(SIM_LOCATE_UPDATE_TEST_TARGET)
	./$(SIM_LOCATE_UPDATE_TEST_TARGET)

check-sim-safe-workset-cuda: $(SIM_SAFE_WORKSET_CUDA_TEST_TARGET)
	./$(SIM_SAFE_WORKSET_CUDA_TEST_TARGET)

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

check-summarize-two-stage-frontier:
	python3 ./scripts/summarize_two_stage_frontier.py --help >/dev/null
	bash ./scripts/check_summarize_two_stage_frontier.sh

check-sim-cuda-region-docs:
	sh ./scripts/check_sim_cuda_region_docs.sh

check-longtarget-lite-output:
	$(MAKE) build
	bash ./scripts/check_longtarget_lite_output.sh

.PHONY: build build-avx2 build-openmp build-openmp-avx2 \
		build-cuda build-cuda-avx2 \
		build-fasim build-fasim-cuda \
		oracle-sample check-sample oracle-smoke check-smoke \
		check-sample-row check-sample-wavefront check-smoke-row check-smoke-wavefront \
		check-smoke-avx2 check-sample-avx2 oracle-matrix check-matrix check-matrix-row \
		check-matrix-wavefront check-matrix-avx2 check-sample-openmp-1 check-sample-openmp-par \
		check-smoke-openmp-1 check-smoke-openmp-par check-matrix-openmp-1 \
		check-matrix-openmp-par benchmark-sample benchmark-smoke benchmark-sample-cuda benchmark-smoke-cuda \
		benchmark-sample-cuda-avx2 benchmark-smoke-cuda-avx2 benchmark-sample-cuda-fast benchmark-smoke-cuda-fast \
		benchmark-sample-cuda-traceback benchmark-smoke-cuda-traceback benchmark-sample-cuda-sim-full benchmark-smoke-cuda-sim-full \
		benchmark-sample-cuda-window-pipeline benchmark-sample-cuda-vs-fasim benchmark-sample-cuda-throughput-compare benchmark-sample-cuda-vs-fasim-two-stage benchmark-fasim-batch benchmark-fasim-throughput-sweep \
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
		build-prealign-shared-test check-prealign-shared \
		build-sim-scan-cuda-true-batch-reduce-test check-sim-scan-cuda-true-batch-reduce \
		build-sim-cuda-proposal-select-test check-sim-cuda-proposal-select \
		build-sim-traceback-cuda-batch-test check-sim-traceback-cuda-batch \
		build-sim-initial-cuda-merge-test check-sim-initial-cuda-merge \
		build-sim-locate-update-test check-sim-locate-update \
		build-exact-sim-two-stage-threshold-test check-exact-sim-two-stage-threshold \
			check-benchmark-telemetry check-benchmark-worker-telemetry check-fasim-throughput-preset check-benchmark-throughput-comparator check-fasim-throughput-sweep \
			check-make-anchor-shards check-summarize-throughput-frontier check-two-stage-frontier-sweep check-summarize-two-stage-frontier check-sim-cuda-initial-proposal-v2-exactness \
		check-sim-cuda-window-pipeline check-sim-cuda-window-pipeline-overlap check-project-whole-genome-runtime \
		check-sim-cuda-region-docs check-longtarget-lite-output check-two-stage-threshold-modes check-two-stage-threshold-heavy-microanchors \
		check-compare-two-stage-panel-summaries check-summarize-two-stage-panel-decision \
		check-rerun-two-stage-panel-with-candidate-env check-analyze-two-stage-selector-candidate-classes \
		check-replay-two-stage-non-empty-candidate-classes check-analyze-two-stage-task-ambiguity \
		check-replay-two-stage-task-level-rerun check-two-stage-task-rerun-runtime
