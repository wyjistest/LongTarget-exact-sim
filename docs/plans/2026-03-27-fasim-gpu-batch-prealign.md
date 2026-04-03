# Fasim GPU Batched preAlign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 面向“全基因组/大量 region 批量预测”，把 `Fasim-LongTarget` 的 `fastSIM` 预筛阶段（`preAlign`）改为 **GPU 批处理**，并在 CUDA 路径下 **跳过 `calc_score_once()`**（用 GPU 的 top1 maxScore 代替），显著降低每个 region 的固定开销。

**Architecture:** 将 `fastSIM` 拆成两段：`preAlign -> scoreInfo peaks` 与 `extend(Align+convertMyTriplex)`。GPU 模式下先对一批 `(segment, rule, strand, Para)` 任务统一调用 `prealign_cuda_find_topk_column_maxima()` 得到 topK peaks/最大分数，再按原逻辑阈值 `minScore=int(maxScore*0.8)` 过滤 peaks，最后调用 extend 阶段生成 triplex。

**Tech Stack:** C++11, SSE2 (ssw/stats), CUDA runtime (`cudart`), 现有 `cuda/prealign_cuda.cu` 接口，Python 基准脚本。

---

### Task 1: 增加 fasim 可重复构建目标

**Files:**
- Modify: `Makefile`

**Step 1: 添加 CPU fasim 目标**
- 产物：`fasim_longtarget_x86`
- 源码：`fasim/Fasim-LongTarget.cpp`, `fasim/ssw_cpp.cpp`, `fasim/sswNew.cpp`, 以及依赖头文件（`fasim/*.h`）。

**Step 2: 添加 CUDA fasim 目标**
- 产物：`fasim_longtarget_cuda`
- 链接：`cuda/prealign_cuda.o` + `-lcudart`
- 运行期通过 `FASIM_ENABLE_PREALIGN_CUDA=1` 开启 GPU；默认走 CPU 逻辑。

**Step 3: 验证构建**
- Run: `make build-fasim`
- Run: `make build-fasim-cuda`
- Expected: 两个二进制均成功生成。

---

### Task 2: 把 fastSIM 拆成 “extend” 可复用函数

**Files:**
- Modify: `fasim/fastsim.h`

**Step 1: 提取 extend 阶段**
- 新增：`fastSIM_extend_from_scoreinfo(...)`（函数名可调整）
- 输入：`strA/strB/strSrc`、`dnaStartPos/minScore`、`scoreInfo 列表`、惩罚参数、`paraList` 等
- 行为：复用现有 `for (i = 0; i < finalScoreInfo.size(); i++) { Align(); convertMyTriplex(); ... }` + 尾部排序/unique/取 TopN 的逻辑。

**Step 2: fastSIM() 继续保留现有接口**
- fastSIM 仍负责生成 `finalScoreInfo`（CPU preAlign 或单 task CUDA preAlign），然后调用 `fastSIM_extend_from_scoreinfo()`。

**Step 3: 编译验证**
- Run: `make build-fasim`
- Expected: 编译通过。

---

### Task 3: 在 Fasim-LongTarget 主循环中实现 GPU 批处理 preAlign，并跳过 calc_score_once

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify (small): `fasim/fastsim.h`（添加批处理辅助结构/环境变量解析，如需要）

**Step 1: 定义批处理任务结构**
- 字段：`seq2`（transformed target）、`dnaStartPos`、`rule/strand/Para`、`srcTransform`（ORIG/COMP/REV/REVCOMP）、以及 `seq1` 指针（用于构造 `strSrc`）。

**Step 2: 新增批处理执行函数**
- 输入：`rnaSequence`、若干任务、`topK`、输出 `triplex_list`
- 逻辑：
  1) 准备/缓存 CUDA query profile（一次）
  2) 编码所有 `seq2` 到 `encodedTargetsHost`（一次）
  3) 调用 `prealign_cuda_find_topk_column_maxima(handle, encodedTargetsHost, taskCount, targetLength, topK, ...)`
  4) 对每个 task：
     - `maxScore = peaks[taskBase+0].score`
     - `minScore = int(maxScore * 0.8)`（与原逻辑一致）
     - 过滤 peaks（`score > minScore`，并做 “±5bp” 去重）
     - 构造 `strSrc`（按 `srcTransform` 从 `seq1` 生成）
     - 调用 `fastSIM_extend_from_scoreinfo(...)`

**Step 3: 在 LongTarget() 中切换逻辑**
- 条件：`paraList.doFastSim == true` 且 `FASIM_ENABLE_PREALIGN_CUDA=1` 且 CUDA init 成功
- 否则保持原 CPU 路径（包含 `calc_score_once()`）不变。

**Step 4: 加入批大小环境变量（可选但推荐）**
- `FASIM_PREALIGN_CUDA_MAX_TASKS`：单次 GPU 调用最大 tasks（默认例如 4096）
- `FASIM_PREALIGN_CUDA_TOPK`：默认 64（受 `cuda/prealign_cuda` 限制）

**Step 5: 样例跑通**
- Run: `FASIM_ENABLE_PREALIGN_CUDA=1 ./fasim_longtarget_cuda -f1 testDNA.fa -f2 H19.fa -r 0 -O .tmp/fasim_cuda_out`
- Expected: 输出 `*-TFOsorted` 等文件存在，且程序不崩溃。

---

### Task 4: 基准测试与对齐验证（sample + 批量）

**Files:**
- Modify: `scripts/benchmark_sample_vs_fasim.py`
- Modify: `README.md`

**Step 1: 在 benchmark 脚本里加入本地 fasim_cuda 运行项**
- 运行 `./fasim_longtarget_cuda`（或可配置路径）
- env：`FASIM_ENABLE_PREALIGN_CUDA=1`
- 输出同样做 `TFOsorted` overlap 对比（vs `longtarget_exact`）

**Step 2: 批量吞吐 micro-benchmark（可选）**
- 新增 `scripts/benchmark_fasim_batch_throughput.py`
- 生成 N 条相同长度的 DNA fasta entries（或重复 sample）
- 比较：CPU fasim vs GPU batched preAlign fasim 的 wall time

**Step 3: 更新 README**
- 说明新二进制与环境变量
- 说明适用场景：大量 region 时要用批处理参数 + 尽量多条序列在同一次运行中

---

### Task 5: 回归与交付

**Step 1: 跑一次基准**
- Run: `make benchmark-sample-cuda-vs-fasim`
- Run: `make build-fasim-cuda && FASIM_ENABLE_PREALIGN_CUDA=1 ./fasim_longtarget_cuda ...`（由脚本覆盖更好）

**Step 2: 记录结果与下一步**
- 记录：GPU preAlign 是否在 “大量 region” 场景显著缩短 wall time
- 若 GPU 仍不占优：下一步做真正的流水线（CPU extend 与 GPU preAlign overlap）或多 GPU 并行（两个进程分别 `FASIM_CUDA_DEVICE=0/1`）。

