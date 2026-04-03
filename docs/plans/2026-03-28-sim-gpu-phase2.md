# SIM GPU Phase-2 Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 面向“全基因组/海量 region 批量预测”，进一步降低 CUDA 路径的固定开销、提升多 GPU 并行能力，并新增 `*-TFOsorted.lite` 轻量输出以降低 I/O；在不破坏现有默认输出/CLI 的前提下提升吞吐。

**Architecture:** 重点做 4 类改动：1) 输出层新增可选 lite 文件（默认关闭）；2) `calc_score_cuda` 引入 per-device batch context 复用 device buffer + events，去掉每次调用的 `cudaMalloc/cudaFree` 与 event create；3) `sim_scan_cuda` 从全局单例改为 per-device context+mutex，并缓存 events（为后续多卡并行/流水做铺垫）；4) `prealign_cuda` 把 topK 维护从 O(K) 的 min 全扫描改为 O(logK) 的 min-heap，避免 topK=128/256 时吞吐崩。

**Tech Stack:** C++11, CUDA runtime (`cudart`), 现有 `cuda/*.cu` kernels，Python 基准脚本。

---

### Task 1: 新增 `*-TFOsorted.lite` 可选输出（LongTarget + Fasim）

**Files:**
- Modify: `longtarget.cpp`（`printResult()`）
- Modify: `fasim/Fasim-LongTarget.cpp`（tfosorted 流式输出路径）
- Modify: `README.md`

**Step 1: LongTarget 增加 lite 输出开关**
- 新增 env：`LONGTARGET_WRITE_TFOSORTED_LITE=1`
- 行为：在写 `*-TFOsorted` 的同时，额外写 `*-TFOsorted.lite`（默认不写，不影响现有文件）
- lite 列建议（tab 分隔）：`Chr, StartInGenome, EndInGenome, Strand, Rule, QueryStart, QueryEnd, StartInSeq, EndInSeq, Direction, Score, Nt(bp), MeanIdentity(%), MeanStability`

**Step 2: Fasim 增加 lite 输出开关**
- 新增 env：`FASIM_WRITE_TFOSORTED_LITE=1`
- 行为：在 `FASIM_OUTPUT_MODE=tfosorted` 时，额外写 `*-TFOsorted.lite`（默认不写）
- 注意：multi-GPU extend 的写出路径也要同步写 lite（同一把 `outMutex` 保护）。

**Step 3: 文档更新**
- README 增加两条 env 说明与 lite 文件列定义。

**Verification:**
- Run: `make build build-cuda build-fasim build-fasim-cuda`
- Run: `LONGTARGET_OUTPUT_MODE=tfosorted LONGTARGET_WRITE_TFOSORTED_LITE=1 ./longtarget_x86 -f1 testDNA.fa -f2 H19.fa -r 0 -O .tmp/out_lite`
- Run: `FASIM_OUTPUT_MODE=tfosorted FASIM_WRITE_TFOSORTED_LITE=1 ./fasim_longtarget_x86 -f1 testDNA.fa -f2 H19.fa -r 0 -O .tmp/out_lite`
- Expected: 同目录下出现 `*-TFOsorted` 与 `*-TFOsorted.lite`；lite 文件可用 `head` 查看列正确、无空文件（除非无结果）。

---

### Task 2: `calc_score_cuda` batch buffer + events 复用（per-device context）

**Files:**
- Modify: `cuda/calc_score_cuda.cu`

**Step 1: 修复 query handle device 记录**
- 在 `calc_score_cuda_prepare_query()` 中记录当前 device 到 `handle->device`（用于后续 set/free/context 选择）。

**Step 2: 引入 per-device batch context**
- 新增内部结构：`CalcScoreCudaBatchContext`（device、capacity、device buffers、events）
- 复用：`targetsDevice/permutationsDevice/scoresDevice` 与 `startEvent/stopEvent`
- 每次调用只做：ensure init/capacity、H2D copy、kernel、D2H copy；不再 `cudaMalloc/cudaFree` + event create/destroy

**Step 3: 稳健性**
- 每个入口在锁内 `cudaSetDevice(device)`，避免多线程/多卡场景下 device 混乱。

**Verification:**
- Run: `make build-cuda`
- Run: `LONGTARGET_ENABLE_CUDA=1 TARGET=$PWD/longtarget_cuda ./scripts/run_sample_exactness.sh`
- Expected: 结果与 oracle 一致；benchmark 下 wall time 有下降（尤其是大量 group 调用时）。

---

### Task 3: `sim_scan_cuda` 改为 per-device context + 缓存 events

**Files:**
- Modify: `cuda/sim_scan_cuda.cu`

**Step 1: 全局单例 → per-device contexts**
- 参考 `cuda/prealign_cuda.cu` 的写法：vector<unique_ptr<Context>> + vector<unique_ptr<mutex>>
- `sim_scan_cuda_init(device)`：获取对应 device 的 context+mutex，锁内初始化（含 events create）

**Step 2: enumerate 函数按当前 thread device 选择 context**
- 通过 `cudaGetDevice()` 获取当前 device（`sim_scan_cuda_init()` 会在该 thread 设置）
- 锁住该 device 的 mutex 后执行 ensure capacity + memcpy + kernel

**Step 3: 缓存 start/stop events**
- `startEvent/stopEvent` 放到 context，只创建一次；每次调用 record/sync/elapsedTime

**Verification:**
- Run: `make build-cuda`
- Run: `LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1 TARGET=$PWD/longtarget_cuda ./scripts/run_sample_exactness_cuda.sh`
- Expected: oracle 输出不变；无 CUDA 错误/崩溃。

---

### Task 4: `prealign_cuda` topK 维护改为 min-heap（降低 topK 依赖）

**Files:**
- Modify: `cuda/prealign_cuda.cu`

**Step 1: kernel 内 topK 结构替换**
- lane0 使用固定大小 min-heap（大小=topK），heap key：`(score asc, position desc)`（root 为“最差”）
- 新 peak 更好则替换 root 并 sift-down，复杂度 O(logK)
- 末尾仍输出 topK，并按 `(score desc, position asc)` 排序（保持旧行为）

**Verification:**
- Run: `make build-fasim-cuda`
- Run: `python3 ./scripts/benchmark_fasim_batch_throughput.py --entries 256 --cuda-topk 64`
- Run: `python3 ./scripts/benchmark_fasim_batch_throughput.py --entries 256 --cuda-topk 128`
- Expected: topK=128 时吞吐不再明显劣化（相对旧版本有改善）；输出格式不变。

---

### Task 5: 回归基准与文档/进度更新

**Files:**
- Modify: `README.md`
- Modify (optional): `EXACT_SIM_PROGRESS.md`

**Step 1: 跑基准并记录**
- Run: `make benchmark-sample-cuda-vs-fasim`
- Run: `python3 ./scripts/benchmark_fasim_batch_throughput.py --entries 128 --cuda-topk 64`
- Run: `python3 ./scripts/benchmark_fasim_batch_throughput.py --entries 128 --cuda-topk 128`

**Step 2: 更新 README**
- 补充 lite 输出 env 与字段定义
- 补充建议：大批量 region 时优先 lite 输出 + multi-GPU + 合理 topK

**Step 3: 更新进度文档**
- 把 Phase 2 完成项写入 `EXACT_SIM_PROGRESS.md`（便于后续继续迭代）

