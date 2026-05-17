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

benchmark-fasim-profile:
	$(MAKE) build-fasim
	python3 ./scripts/benchmark_fasim_profile.py --mode profile --bin $(CURDIR)/$(FASIM_TARGET) --require-profile

benchmark-fasim-representative-profile:
	$(MAKE) build-fasim
	python3 ./scripts/benchmark_fasim_representative_profile.py --bin $(CURDIR)/$(FASIM_TARGET) --profile-set representative --require-profile

benchmark-fasim-real-corpus-profile:
	$(MAKE) build-fasim
	@if [ -z "$${FASIM_REAL_CORPUS_DNA:-}" ] || [ -z "$${FASIM_REAL_CORPUS_RNA:-}" ]; then \
		echo "set FASIM_REAL_CORPUS_DNA and FASIM_REAL_CORPUS_RNA to run this target" >&2; \
		exit 2; \
	fi
	python3 ./scripts/benchmark_fasim_real_corpus_profile.py --bin $(CURDIR)/$(FASIM_TARGET) --dna "$${FASIM_REAL_CORPUS_DNA}" --rna "$${FASIM_REAL_CORPUS_RNA}" --label "$${FASIM_REAL_CORPUS_LABEL:-real_corpus}" --repeat "$${FASIM_REAL_CORPUS_REPEAT:-1}" --require-profile

check-fasim-sim-gap-taxonomy:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_gap_taxonomy.sh

benchmark-fasim-sim-gap-taxonomy:
	$(MAKE) build-fasim
	PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_gap_taxonomy.py --bin $(CURDIR)/$(FASIM_TARGET) --profile-set representative --require-sim-gap-taxonomy

check-fasim-local-sim-recovery-shadow:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_local_sim_recovery_shadow.sh

benchmark-fasim-local-sim-recovery-shadow:
	$(MAKE) build-fasim
	FASIM_SIM_RECOVERY_SHADOW=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_gap_taxonomy.py --bin $(CURDIR)/$(FASIM_TARGET) --profile-set representative --require-sim-gap-taxonomy --recovery-shadow --recovery-shadow-output docs/fasim_local_sim_recovery_shadow.md

check-fasim-sim-recovery-risk-detector:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_risk_detector.sh

benchmark-fasim-sim-recovery-risk-detector:
	$(MAKE) build-fasim
	FASIM_SIM_RECOVERY_RISK_DETECTOR=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_gap_taxonomy.py --bin $(CURDIR)/$(FASIM_TARGET) --profile-set representative --require-sim-gap-taxonomy --risk-detector --risk-detector-output docs/fasim_sim_recovery_risk_detector.md

check-fasim-local-sim-recovery-executor-shadow:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_local_sim_recovery_executor_shadow.sh

benchmark-fasim-local-sim-recovery-executor-shadow:
	$(MAKE) build-fasim
	FASIM_SIM_RECOVERY_RISK_DETECTOR=1 FASIM_SIM_RECOVERY_EXECUTOR_SHADOW=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_gap_taxonomy.py --bin $(CURDIR)/$(FASIM_TARGET) --profile-set representative --require-sim-gap-taxonomy --risk-detector --executor-shadow --executor-shadow-output docs/fasim_local_sim_recovery_executor_shadow.md

check-fasim-local-sim-recovery-integration-shadow:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_local_sim_recovery_integration_shadow.sh

benchmark-fasim-local-sim-recovery-integration-shadow:
	$(MAKE) build-fasim
	FASIM_SIM_RECOVERY_RISK_DETECTOR=1 FASIM_SIM_RECOVERY_EXECUTOR_SHADOW=1 FASIM_SIM_RECOVERY_INTEGRATION_SHADOW=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_gap_taxonomy.py --bin $(CURDIR)/$(FASIM_TARGET) --profile-set representative --require-sim-gap-taxonomy --risk-detector --executor-shadow --integration-shadow --output $(CURDIR)/.tmp/fasim_local_sim_recovery_integration_shadow/taxonomy.md --risk-detector-output $(CURDIR)/.tmp/fasim_local_sim_recovery_integration_shadow/risk_detector.md --executor-shadow-output $(CURDIR)/.tmp/fasim_local_sim_recovery_integration_shadow/executor_shadow.md --integration-shadow-output docs/fasim_local_sim_recovery_integration_shadow.md --work-dir $(CURDIR)/.tmp/fasim_local_sim_recovery_integration_shadow

check-fasim-local-sim-recovery-filter-shadow:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_local_sim_recovery_filter_shadow.sh

benchmark-fasim-local-sim-recovery-filter-shadow:
	$(MAKE) build-fasim
	FASIM_SIM_RECOVERY_RISK_DETECTOR=1 FASIM_SIM_RECOVERY_EXECUTOR_SHADOW=1 FASIM_SIM_RECOVERY_INTEGRATION_SHADOW=1 FASIM_SIM_RECOVERY_FILTER_SHADOW=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_gap_taxonomy.py --bin $(CURDIR)/$(FASIM_TARGET) --profile-set representative --require-sim-gap-taxonomy --risk-detector --executor-shadow --integration-shadow --filter-shadow --output $(CURDIR)/.tmp/fasim_local_sim_recovery_filter_shadow/taxonomy.md --risk-detector-output $(CURDIR)/.tmp/fasim_local_sim_recovery_filter_shadow/risk_detector.md --executor-shadow-output $(CURDIR)/.tmp/fasim_local_sim_recovery_filter_shadow/executor_shadow.md --integration-shadow-output $(CURDIR)/.tmp/fasim_local_sim_recovery_filter_shadow/integration_shadow.md --filter-shadow-output docs/fasim_local_sim_recovery_filter_shadow.md --work-dir $(CURDIR)/.tmp/fasim_local_sim_recovery_filter_shadow

check-fasim-local-sim-recovery-replacement-shadow:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_local_sim_recovery_replacement_shadow.sh

benchmark-fasim-local-sim-recovery-replacement-shadow:
	$(MAKE) build-fasim
	FASIM_SIM_RECOVERY_RISK_DETECTOR=1 FASIM_SIM_RECOVERY_EXECUTOR_SHADOW=1 FASIM_SIM_RECOVERY_INTEGRATION_SHADOW=1 FASIM_SIM_RECOVERY_FILTER_SHADOW=1 FASIM_SIM_RECOVERY_REPLACEMENT_SHADOW=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_gap_taxonomy.py --bin $(CURDIR)/$(FASIM_TARGET) --profile-set representative --require-sim-gap-taxonomy --risk-detector --executor-shadow --integration-shadow --filter-shadow --replacement-shadow --output $(CURDIR)/.tmp/fasim_local_sim_recovery_replacement_shadow/taxonomy.md --risk-detector-output $(CURDIR)/.tmp/fasim_local_sim_recovery_replacement_shadow/risk_detector.md --executor-shadow-output $(CURDIR)/.tmp/fasim_local_sim_recovery_replacement_shadow/executor_shadow.md --integration-shadow-output $(CURDIR)/.tmp/fasim_local_sim_recovery_replacement_shadow/integration_shadow.md --filter-shadow-output $(CURDIR)/.tmp/fasim_local_sim_recovery_replacement_shadow/filter_shadow.md --replacement-shadow-output docs/fasim_local_sim_recovery_replacement_shadow.md --work-dir $(CURDIR)/.tmp/fasim_local_sim_recovery_replacement_shadow

check-fasim-local-sim-recovery-replacement-extra-taxonomy:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_local_sim_recovery_replacement_extra_taxonomy.sh

benchmark-fasim-local-sim-recovery-replacement-extra-taxonomy:
	$(MAKE) build-fasim
	FASIM_SIM_RECOVERY_RISK_DETECTOR=1 FASIM_SIM_RECOVERY_EXECUTOR_SHADOW=1 FASIM_SIM_RECOVERY_INTEGRATION_SHADOW=1 FASIM_SIM_RECOVERY_FILTER_SHADOW=1 FASIM_SIM_RECOVERY_REPLACEMENT_SHADOW=1 FASIM_SIM_RECOVERY_REPLACEMENT_EXTRA_TAXONOMY=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_gap_taxonomy.py --bin $(CURDIR)/$(FASIM_TARGET) --profile-set representative --require-sim-gap-taxonomy --risk-detector --executor-shadow --integration-shadow --filter-shadow --replacement-shadow --replacement-extra-taxonomy --output $(CURDIR)/.tmp/fasim_local_sim_recovery_replacement_extra_taxonomy/taxonomy.md --risk-detector-output $(CURDIR)/.tmp/fasim_local_sim_recovery_replacement_extra_taxonomy/risk_detector.md --executor-shadow-output $(CURDIR)/.tmp/fasim_local_sim_recovery_replacement_extra_taxonomy/executor_shadow.md --integration-shadow-output $(CURDIR)/.tmp/fasim_local_sim_recovery_replacement_extra_taxonomy/integration_shadow.md --filter-shadow-output $(CURDIR)/.tmp/fasim_local_sim_recovery_replacement_extra_taxonomy/filter_shadow.md --replacement-shadow-output $(CURDIR)/.tmp/fasim_local_sim_recovery_replacement_extra_taxonomy/replacement_shadow.md --replacement-extra-taxonomy-output docs/fasim_local_sim_recovery_replacement_extra_taxonomy.md --work-dir $(CURDIR)/.tmp/fasim_local_sim_recovery_replacement_extra_taxonomy

check-fasim-sim-recovery-real-mode:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_real_mode.sh

benchmark-fasim-sim-recovery-real-mode:
	$(MAKE) build-fasim
	FASIM_SIM_RECOVERY=1 FASIM_SIM_RECOVERY_VALIDATE=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_gap_taxonomy.py --bin $(CURDIR)/$(FASIM_TARGET) --profile-set representative --require-sim-gap-taxonomy --sim-recovery --sim-recovery-validate --sim-recovery-output $(CURDIR)/.tmp/fasim_sim_recovery_real_mode/sim_close.lite --sim-recovery-report docs/fasim_sim_recovery_real_mode.md --output $(CURDIR)/.tmp/fasim_sim_recovery_real_mode/taxonomy.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_real_mode

check-fasim-sim-recovery-real-mode-characterization:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_real_mode_characterization.sh

benchmark-fasim-sim-recovery-real-mode-characterization:
	$(MAKE) build-fasim
	PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_mode_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --profile-set representative --repeat $${FASIM_SIM_RECOVERY_CHARACTERIZATION_REPEAT:-3} --output docs/fasim_sim_recovery_real_mode_characterization.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_real_mode_characterization

check-fasim-sim-recovery-real-corpus-characterization:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_real_corpus_characterization.sh

check-fasim-sim-recovery-real-corpus-validation-coverage:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_real_corpus_validation_coverage.sh

check-fasim-sim-recovery-real-corpus-miss-taxonomy:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_real_corpus_miss_taxonomy.sh

check-fasim-sim-recovery-real-corpus-recall-repair:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_real_corpus_recall_repair.sh

check-fasim-sim-recovery-real-corpus-validation-matrix:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_real_corpus_validation_matrix.sh

check-fasim-sim-recovery-score-landscape-detector:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_score_landscape_detector.sh

check-fasim-sim-recovery-learned-detector-dataset:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_learned_detector_dataset.sh

check-fasim-sim-recovery-learned-detector-model:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_learned_detector_model.sh

check-fasim-sim-recovery-learned-detector-negative-dataset:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_learned_detector_negative_dataset.sh

check-fasim-sim-recovery-learned-detector-model-shadow:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_learned_detector_model_shadow.sh

check-fasim-sim-recovery-learned-detector-dataset-expansion:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_learned_detector_dataset_expansion.sh

check-fasim-sim-recovery-learned-detector-expanded-model-shadow:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_learned_detector_expanded_model_shadow.sh

check-fasim-sim-recovery-learned-detector-feature-expansion:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_learned_detector_feature_expansion.sh

check-fasim-sim-recovery-learned-detector-real-corpus-hard-negatives:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_learned_detector_real_corpus_hard_negatives.sh

check-fasim-sim-recovery-learned-detector-expanded-hard-negative-model-shadow:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_learned_detector_expanded_hard_negative_model_shadow.sh

check-fasim-sim-recovery-learned-detector-large-corpus-expansion:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_learned_detector_large_corpus_expansion.sh

check-fasim-sim-recovery-learned-detector-large-corpus-model-shadow:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_learned_detector_large_corpus_model_shadow.sh

check-fasim-sim-recovery-learned-detector-precision-sweep:
	$(MAKE) build-fasim
	BIN=$(CURDIR)/$(FASIM_TARGET) ./scripts/check_fasim_sim_recovery_learned_detector_precision_sweep.sh

benchmark-fasim-sim-recovery-real-corpus-characterization:
	$(MAKE) build-fasim
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	@if [ "$${FASIM_SIM_RECOVERY_SCORE_LANDSCAPE_DETECTOR_SHADOW:-0}" = "1" ]; then \
		PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --case human_lnc_atlas_17kb_target "$${FASIM_HUMAN_17KB_DNA}" "$${FASIM_HUMAN_17KB_RNA}" --case human_lnc_atlas_508kb_target "$${FASIM_HUMAN_508KB_DNA}" "$${FASIM_HUMAN_508KB_RNA}" --validate-cases "$${FASIM_SIM_RECOVERY_REAL_CORPUS_VALIDATE_CASES:-human_lnc_atlas_17kb_target,human_lnc_atlas_508kb_target}" --repeat "$${FASIM_SIM_RECOVERY_REAL_CORPUS_REPEAT:-1}" --require-profile --validation-coverage-report --miss-taxonomy-report --score-landscape-detector-shadow --report-title "Fasim SIM-Close Score-Landscape Detector Shadow" --base-branch fasim-sim-recovery-real-corpus-validation-matrix --output docs/fasim_sim_recovery_score_landscape_detector.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_score_landscape_detector; \
	elif [ "$${FASIM_SIM_RECOVERY_RECALL_REPAIR_SHADOW:-0}" = "1" ]; then \
		PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --case human_lnc_atlas_17kb_target "$${FASIM_HUMAN_17KB_DNA}" "$${FASIM_HUMAN_17KB_RNA}" --case human_lnc_atlas_508kb_target "$${FASIM_HUMAN_508KB_DNA}" "$${FASIM_HUMAN_508KB_RNA}" --validate-cases "$${FASIM_SIM_RECOVERY_REAL_CORPUS_VALIDATE_CASES:-human_lnc_atlas_17kb_target,human_lnc_atlas_508kb_target}" --repeat "$${FASIM_SIM_RECOVERY_REAL_CORPUS_REPEAT:-1}" --require-profile --validation-coverage-report --miss-taxonomy-report --recall-repair-shadow --report-title "Fasim SIM-Close Recovery Real-Corpus Recall Repair" --base-branch fasim-sim-recovery-real-corpus-miss-taxonomy --output docs/fasim_sim_recovery_real_corpus_recall_repair.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_real_corpus_recall_repair; \
	else \
		PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --case human_lnc_atlas_17kb_target "$${FASIM_HUMAN_17KB_DNA}" "$${FASIM_HUMAN_17KB_RNA}" --case human_lnc_atlas_508kb_target "$${FASIM_HUMAN_508KB_DNA}" "$${FASIM_HUMAN_508KB_RNA}" --validate-cases "$${FASIM_SIM_RECOVERY_REAL_CORPUS_VALIDATE_CASES:-}" --repeat "$${FASIM_SIM_RECOVERY_REAL_CORPUS_REPEAT:-2}" --require-profile --output docs/fasim_sim_recovery_real_corpus_characterization.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_real_corpus_characterization; \
	fi

benchmark-fasim-sim-recovery-real-corpus-validation-coverage:
	$(MAKE) build-fasim
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --case human_lnc_atlas_17kb_target "$${FASIM_HUMAN_17KB_DNA}" "$${FASIM_HUMAN_17KB_RNA}" --case human_lnc_atlas_508kb_target "$${FASIM_HUMAN_508KB_DNA}" "$${FASIM_HUMAN_508KB_RNA}" --validate-cases "$${FASIM_SIM_RECOVERY_REAL_CORPUS_VALIDATE_CASES:-human_lnc_atlas_17kb_target,human_lnc_atlas_508kb_target}" --repeat "$${FASIM_SIM_RECOVERY_REAL_CORPUS_REPEAT:-1}" --require-profile --validation-coverage-report --report-title "Fasim SIM-Close Recovery Real-Corpus Validation Coverage" --base-branch fasim-sim-recovery-real-corpus-characterization --output docs/fasim_sim_recovery_real_corpus_validation_coverage.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_real_corpus_validation_coverage

benchmark-fasim-sim-recovery-real-corpus-miss-taxonomy:
	$(MAKE) build-fasim
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --case human_lnc_atlas_17kb_target "$${FASIM_HUMAN_17KB_DNA}" "$${FASIM_HUMAN_17KB_RNA}" --case human_lnc_atlas_508kb_target "$${FASIM_HUMAN_508KB_DNA}" "$${FASIM_HUMAN_508KB_RNA}" --validate-cases "$${FASIM_SIM_RECOVERY_REAL_CORPUS_VALIDATE_CASES:-human_lnc_atlas_17kb_target,human_lnc_atlas_508kb_target}" --repeat "$${FASIM_SIM_RECOVERY_REAL_CORPUS_REPEAT:-1}" --require-profile --validation-coverage-report --miss-taxonomy-report --report-title "Fasim SIM-Close Recovery Real-Corpus Miss Taxonomy" --base-branch fasim-sim-recovery-real-corpus-validation-coverage --output docs/fasim_sim_recovery_real_corpus_miss_taxonomy.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_real_corpus_miss_taxonomy

benchmark-fasim-sim-recovery-real-corpus-recall-repair:
	$(MAKE) build-fasim
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	FASIM_SIM_RECOVERY_RECALL_REPAIR_SHADOW=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --case human_lnc_atlas_17kb_target "$${FASIM_HUMAN_17KB_DNA}" "$${FASIM_HUMAN_17KB_RNA}" --case human_lnc_atlas_508kb_target "$${FASIM_HUMAN_508KB_DNA}" "$${FASIM_HUMAN_508KB_RNA}" --validate-cases "$${FASIM_SIM_RECOVERY_REAL_CORPUS_VALIDATE_CASES:-human_lnc_atlas_17kb_target,human_lnc_atlas_508kb_target}" --repeat "$${FASIM_SIM_RECOVERY_REAL_CORPUS_REPEAT:-1}" --require-profile --validation-coverage-report --miss-taxonomy-report --recall-repair-shadow --report-title "Fasim SIM-Close Recovery Real-Corpus Recall Repair" --base-branch fasim-sim-recovery-real-corpus-miss-taxonomy --output docs/fasim_sim_recovery_real_corpus_recall_repair.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_real_corpus_recall_repair

benchmark-fasim-sim-recovery-real-corpus-validation-matrix:
	$(MAKE) build-fasim
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	FASIM_SIM_RECOVERY_VALIDATION_MATRIX=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --case human_lnc_atlas_17kb_target "$${FASIM_HUMAN_17KB_DNA}" "$${FASIM_HUMAN_17KB_RNA}" --case human_lnc_atlas_508kb_target "$${FASIM_HUMAN_508KB_DNA}" "$${FASIM_HUMAN_508KB_RNA}" $${FASIM_SIM_RECOVERY_REAL_CORPUS_EXTRA_CASE_ARGS:-} --validate-cases "$${FASIM_SIM_RECOVERY_REAL_CORPUS_VALIDATE_CASES:-human_lnc_atlas_17kb_target,human_lnc_atlas_508kb_target}" --repeat "$${FASIM_SIM_RECOVERY_REAL_CORPUS_REPEAT:-1}" --require-profile --validation-coverage-report --miss-taxonomy-report --validation-matrix-report --report-title "Fasim SIM-Close Recovery Real-Corpus Validation Matrix" --base-branch fasim-sim-recovery-real-corpus-recall-repair --output docs/fasim_sim_recovery_real_corpus_validation_matrix.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_real_corpus_validation_matrix

benchmark-fasim-sim-recovery-score-landscape-detector:
	$(MAKE) build-fasim
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	FASIM_SIM_RECOVERY_SCORE_LANDSCAPE_DETECTOR_SHADOW=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --case human_lnc_atlas_17kb_target "$${FASIM_HUMAN_17KB_DNA}" "$${FASIM_HUMAN_17KB_RNA}" --case human_lnc_atlas_508kb_target "$${FASIM_HUMAN_508KB_DNA}" "$${FASIM_HUMAN_508KB_RNA}" $${FASIM_SIM_RECOVERY_REAL_CORPUS_EXTRA_CASE_ARGS:-} --validate-cases "$${FASIM_SIM_RECOVERY_REAL_CORPUS_VALIDATE_CASES:-human_lnc_atlas_17kb_target,human_lnc_atlas_508kb_target}" --repeat "$${FASIM_SIM_RECOVERY_REAL_CORPUS_REPEAT:-1}" --require-profile --validation-coverage-report --miss-taxonomy-report --score-landscape-detector-shadow --report-title "Fasim SIM-Close Score-Landscape Detector Shadow" --base-branch fasim-sim-recovery-real-corpus-validation-matrix --output docs/fasim_sim_recovery_score_landscape_detector.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_score_landscape_detector

benchmark-fasim-sim-recovery-learned-detector-dataset:
	$(MAKE) build-fasim
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	FASIM_SIM_RECOVERY_LEARNED_DETECTOR_DATASET=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --case human_lnc_atlas_17kb_target "$${FASIM_HUMAN_17KB_DNA}" "$${FASIM_HUMAN_17KB_RNA}" --case human_lnc_atlas_508kb_target "$${FASIM_HUMAN_508KB_DNA}" "$${FASIM_HUMAN_508KB_RNA}" $${FASIM_SIM_RECOVERY_REAL_CORPUS_EXTRA_CASE_ARGS:-} --validate-cases "$${FASIM_SIM_RECOVERY_REAL_CORPUS_VALIDATE_CASES:-human_lnc_atlas_17kb_target,human_lnc_atlas_508kb_target}" --repeat "$${FASIM_SIM_RECOVERY_REAL_CORPUS_REPEAT:-1}" --require-profile --validation-coverage-report --miss-taxonomy-report --learned-detector-dataset $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_dataset/learned_detector_dataset.tsv --learned-detector-dataset-report --report-title "Fasim SIM-Close Learned Detector Dataset" --base-branch fasim-sim-recovery-score-landscape-detector-shadow --output docs/fasim_sim_recovery_learned_detector_dataset.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_dataset

benchmark-fasim-sim-recovery-learned-detector-model:
	$(MAKE) build-fasim
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	FASIM_SIM_RECOVERY_LEARNED_DETECTOR_DATASET=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --case human_lnc_atlas_17kb_target "$${FASIM_HUMAN_17KB_DNA}" "$${FASIM_HUMAN_17KB_RNA}" --case human_lnc_atlas_508kb_target "$${FASIM_HUMAN_508KB_DNA}" "$${FASIM_HUMAN_508KB_RNA}" $${FASIM_SIM_RECOVERY_REAL_CORPUS_EXTRA_CASE_ARGS:-} --validate-cases "$${FASIM_SIM_RECOVERY_REAL_CORPUS_VALIDATE_CASES:-human_lnc_atlas_17kb_target,human_lnc_atlas_508kb_target}" --repeat "$${FASIM_SIM_RECOVERY_REAL_CORPUS_REPEAT:-1}" --require-profile --validation-coverage-report --miss-taxonomy-report --learned-detector-dataset $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_model/learned_detector_dataset.tsv --learned-detector-dataset-report --report-title "Fasim SIM-Close Learned Detector Dataset" --base-branch fasim-sim-recovery-score-landscape-detector-shadow --output $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_model/dataset_report.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_model/dataset_work
	PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_learned_detector_model.py --dataset $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_model/learned_detector_dataset.tsv --output docs/fasim_sim_recovery_learned_detector_model.md

benchmark-fasim-sim-recovery-learned-detector-negative-dataset:
	$(MAKE) build-fasim
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	FASIM_SIM_RECOVERY_LEARNED_DETECTOR_DATASET=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --case human_lnc_atlas_17kb_target "$${FASIM_HUMAN_17KB_DNA}" "$${FASIM_HUMAN_17KB_RNA}" --case human_lnc_atlas_508kb_target "$${FASIM_HUMAN_508KB_DNA}" "$${FASIM_HUMAN_508KB_RNA}" $${FASIM_SIM_RECOVERY_REAL_CORPUS_EXTRA_CASE_ARGS:-} --validate-cases "$${FASIM_SIM_RECOVERY_REAL_CORPUS_VALIDATE_CASES:-human_lnc_atlas_17kb_target,human_lnc_atlas_508kb_target}" --repeat "$${FASIM_SIM_RECOVERY_REAL_CORPUS_REPEAT:-1}" --require-profile --validation-coverage-report --miss-taxonomy-report --learned-detector-dataset $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_negative_dataset/learned_detector_dataset.tsv --learned-detector-dataset-report --report-title "Fasim SIM-Close Learned Detector Dataset" --base-branch fasim-sim-recovery-learned-detector-negative-dataset --output $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_negative_dataset/dataset_report.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_negative_dataset/dataset_work
	PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_learned_detector_negative_dataset.py --dataset $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_negative_dataset/learned_detector_dataset.tsv --output-tsv $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_negative_dataset/negative_dataset.tsv --report docs/fasim_sim_recovery_learned_detector_negative_dataset.md

benchmark-fasim-sim-recovery-learned-detector-model-shadow:
	$(MAKE) build-fasim
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	FASIM_SIM_RECOVERY_LEARNED_DETECTOR_DATASET=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --case human_lnc_atlas_17kb_target "$${FASIM_HUMAN_17KB_DNA}" "$${FASIM_HUMAN_17KB_RNA}" --case human_lnc_atlas_508kb_target "$${FASIM_HUMAN_508KB_DNA}" "$${FASIM_HUMAN_508KB_RNA}" $${FASIM_SIM_RECOVERY_REAL_CORPUS_EXTRA_CASE_ARGS:-} --validate-cases "$${FASIM_SIM_RECOVERY_REAL_CORPUS_VALIDATE_CASES:-human_lnc_atlas_17kb_target,human_lnc_atlas_508kb_target}" --repeat "$${FASIM_SIM_RECOVERY_REAL_CORPUS_REPEAT:-1}" --require-profile --validation-coverage-report --miss-taxonomy-report --learned-detector-dataset $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_model_shadow/learned_detector_dataset.tsv --learned-detector-dataset-report --report-title "Fasim SIM-Close Learned Detector Dataset" --base-branch fasim-sim-recovery-learned-detector-model-shadow --output $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_model_shadow/dataset_report.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_model_shadow/dataset_work
	PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_learned_detector_negative_dataset.py --dataset $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_model_shadow/learned_detector_dataset.tsv --output-tsv $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_model_shadow/negative_dataset.tsv --report $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_model_shadow/negative_dataset_report.md
	PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_learned_detector_model_shadow.py --dataset $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_model_shadow/negative_dataset.tsv --source-dataset $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_model_shadow/learned_detector_dataset.tsv --report docs/fasim_sim_recovery_learned_detector_model_shadow.md

benchmark-fasim-sim-recovery-learned-detector-dataset-expansion:
	$(MAKE) build-fasim
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	FASIM_SIM_RECOVERY_LEARNED_DETECTOR_DATASET=1 PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_real_corpus_characterization.py --bin $(CURDIR)/$(FASIM_TARGET) --case human_lnc_atlas_17kb_target "$${FASIM_HUMAN_17KB_DNA}" "$${FASIM_HUMAN_17KB_RNA}" --case human_lnc_atlas_508kb_target "$${FASIM_HUMAN_508KB_DNA}" "$${FASIM_HUMAN_508KB_RNA}" $${FASIM_SIM_RECOVERY_REAL_CORPUS_EXTRA_CASE_ARGS:-} --validate-cases "$${FASIM_SIM_RECOVERY_REAL_CORPUS_VALIDATE_CASES:-human_lnc_atlas_17kb_target,human_lnc_atlas_508kb_target}" --repeat "$${FASIM_SIM_RECOVERY_REAL_CORPUS_REPEAT:-1}" --require-profile --validation-coverage-report --miss-taxonomy-report --learned-detector-dataset $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_dataset_expansion/learned_detector_dataset.tsv --learned-detector-dataset-report --report-title "Fasim SIM-Close Learned Detector Dataset" --base-branch fasim-sim-recovery-learned-detector-model-shadow --output $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_dataset_expansion/dataset_report.md --work-dir $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_dataset_expansion/dataset_work
	PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_learned_detector_negative_dataset.py --dataset $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_dataset_expansion/learned_detector_dataset.tsv --output-tsv $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_dataset_expansion/negative_dataset.tsv --report $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_dataset_expansion/negative_dataset_report.md
	PYTHONDONTWRITEBYTECODE=1 python3 ./scripts/benchmark_fasim_sim_recovery_learned_detector_dataset_expansion.py --dataset $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_dataset_expansion/negative_dataset.tsv --source-dataset $(CURDIR)/.tmp/fasim_sim_recovery_learned_detector_dataset_expansion/learned_detector_dataset.tsv --report docs/fasim_sim_recovery_learned_detector_dataset_expansion.md

benchmark-fasim-gpu-dp-column-topk-scoreinfo-repair:
	$(MAKE) build-fasim-cuda
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	python3 ./scripts/benchmark_fasim_gpu_dp_column_topk_scoreinfo_repair.py --cuda-bin $(CURDIR)/fasim_longtarget_cuda --human-17kb-dna "$${FASIM_HUMAN_17KB_DNA}" --human-17kb-rna "$${FASIM_HUMAN_17KB_RNA}" --human-508kb-dna "$${FASIM_HUMAN_508KB_DNA}" --human-508kb-rna "$${FASIM_HUMAN_508KB_RNA}" --caps "$${FASIM_GPU_DP_COLUMN_TOPK_SWEEP_CAPS:-current,8,16,32,64,128,256}" --repeat "$${FASIM_GPU_DP_COLUMN_TOPK_SWEEP_REPEAT:-1}" --require-human --require-profile

benchmark-fasim-gpu-dp-column-full-scoreinfo-debug:
	$(MAKE) build-fasim-cuda
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	python3 ./scripts/benchmark_fasim_gpu_dp_column_full_scoreinfo_debug.py --cuda-bin $(CURDIR)/fasim_longtarget_cuda --human-17kb-dna "$${FASIM_HUMAN_17KB_DNA}" --human-17kb-rna "$${FASIM_HUMAN_17KB_RNA}" --human-17kb-debug-window-index "$${FASIM_HUMAN_17KB_DEBUG_WINDOW_INDEX:-3}" --human-508kb-dna "$${FASIM_HUMAN_508KB_DNA}" --human-508kb-rna "$${FASIM_HUMAN_508KB_RNA}" --human-508kb-debug-window-index "$${FASIM_HUMAN_508KB_DEBUG_WINDOW_INDEX:-5}" --repeat "$${FASIM_GPU_DP_COLUMN_FULL_SCOREINFO_DEBUG_REPEAT:-1}" --debug-max-records "$${FASIM_GPU_DP_COLUMN_DEBUG_MAX_RECORDS:-8}" --require-human --require-profile

benchmark-fasim-gpu-dp-column-post-topk-pack-shadow:
	$(MAKE) build-fasim-cuda
	@if [ -z "$${FASIM_HUMAN_17KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_17KB_RNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_DNA:-}" ] || [ -z "$${FASIM_HUMAN_508KB_RNA:-}" ]; then \
		echo "set FASIM_HUMAN_17KB_DNA, FASIM_HUMAN_17KB_RNA, FASIM_HUMAN_508KB_DNA, and FASIM_HUMAN_508KB_RNA to run this target" >&2; \
		exit 2; \
	fi
	python3 ./scripts/benchmark_fasim_gpu_dp_column_post_topk_pack_shadow.py --cuda-bin $(CURDIR)/fasim_longtarget_cuda --human-17kb-dna "$${FASIM_HUMAN_17KB_DNA}" --human-17kb-rna "$${FASIM_HUMAN_17KB_RNA}" --human-17kb-debug-window-index "$${FASIM_HUMAN_17KB_DEBUG_WINDOW_INDEX:-3}" --human-508kb-dna "$${FASIM_HUMAN_508KB_DNA}" --human-508kb-rna "$${FASIM_HUMAN_508KB_RNA}" --human-508kb-debug-window-index "$${FASIM_HUMAN_508KB_DEBUG_WINDOW_INDEX:-5}" --repeat "$${FASIM_GPU_DP_COLUMN_POST_TOPK_PACK_SHADOW_REPEAT:-1}" --debug-max-records "$${FASIM_GPU_DP_COLUMN_DEBUG_MAX_RECORDS:-8}" --require-human --require-profile

FASIM_CIGAR_TEST_TARGET ?= tests/test_fasim_cigar_identity
FASIM_CIGAR_TEST_SOURCES := tests/test_fasim_cigar_identity.cpp fasim/ssw_cpp.cpp fasim/sswNew.cpp cuda/prealign_cuda_stub.cpp

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

check-fasim-exactness: build-fasim
	bash ./scripts/check_fasim_exactness.sh

check-fasim-profile-telemetry: build-fasim
	bash ./scripts/check_fasim_profile_telemetry.sh

check-fasim-representative-profile: build-fasim
	bash ./scripts/check_fasim_representative_profile.sh

check-fasim-real-corpus-profile: build-fasim
	bash ./scripts/check_fasim_real_corpus_profile.sh

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
		benchmark-sample-cuda-window-pipeline benchmark-sample-cuda-vs-fasim benchmark-sample-cuda-throughput-compare benchmark-sample-cuda-vs-fasim-two-stage benchmark-fasim-batch benchmark-fasim-throughput-sweep benchmark-fasim-profile benchmark-fasim-representative-profile benchmark-fasim-real-corpus-profile benchmark-fasim-gpu-dp-column-topk-scoreinfo-repair benchmark-fasim-gpu-dp-column-full-scoreinfo-debug benchmark-fasim-gpu-dp-column-post-topk-pack-shadow \
		benchmark-two-stage-threshold-modes benchmark-two-stage-threshold-heavy-microanchors \
		benchmark-sample-cuda-vs-fasim-two-stage-prealign \
		check-sample-cuda check-smoke-cuda \
		check-sample-cuda-sim check-smoke-cuda-sim check-matrix-cuda-sim \
		check-sample-cuda-sim-region check-smoke-cuda-sim-region check-matrix-cuda-sim-region \
		check-sample-cuda-sim-region-locate check-smoke-cuda-sim-region-locate \
		check-sample-cuda-sim-traceback-strict check-smoke-cuda-sim-traceback-strict \
		check-smoke-cuda-sim-full \
		check-smoke-cuda-avx2 check-matrix-cuda check-matrix-cuda-avx2 \
		build-fasim-cigar-test check-fasim-cigar check-fasim-exactness check-fasim-profile-telemetry check-fasim-representative-profile check-fasim-real-corpus-profile \
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
		check-sim-cuda-region-docs check-longtarget-lite-output check-two-stage-threshold-modes check-two-stage-threshold-heavy-microanchors \
		check-compare-two-stage-panel-summaries check-summarize-two-stage-panel-decision \
		check-rerun-two-stage-panel-with-candidate-env check-rerun-two-stage-panel-task-rerun-runtime check-analyze-two-stage-selector-candidate-classes \
		check-replay-two-stage-non-empty-candidate-classes check-analyze-two-stage-task-ambiguity \
		check-replay-two-stage-task-level-rerun check-search-two-stage-task-trigger-rankings check-two-stage-task-rerun-runtime
