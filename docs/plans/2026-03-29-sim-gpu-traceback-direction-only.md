# SIM GPU Traceback Direction-Only Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把 SIM（Gotoh affine gap）的 CUDA traceback 从“写回整张 `H/D/E/state` 矩阵再回溯”改为“只写 per-cell direction（含 tie bits）+ per-tile 边界”，显著降低显存占用与全局内存带宽；并提供 strict/fast 两种模式：strict 遇 tie 回退 CPU 保持稳定，fast 不回退允许少量差异换速度。

**Architecture:** forward DP 采用 tile wavefront：tile 内 `Hs/Ds/Es` 在 shared memory 计算，每个 cell 仅写 1 byte `dir`（含 H-state + gap open/extend + tie bits）。跨 tile 依赖通过 4 个边界数组（`bottomH/bottomD/rightH/rightE`）传递，避免写回完整 DP 矩阵。backtrace 只读 `dir` 运行状态机重建 ops，并用 tie bits 置位 `hadTie` 供上层决定是否回退 CPU。

**Tech Stack:** C++11, CUDA runtime (`cudart`), `cuda/sim_traceback_cuda.cu`, 现有 `sim.h` materialize 逻辑, shell + scripts benchmarks.

---

### Task 1: 修到 `build-cuda` 可编译（direction-only + boundary）

**Files:**
- Modify: `cuda/sim_traceback_cuda.cu`
- Modify (if needed): `cuda/sim_traceback_cuda.h`

**Step 1: 编译并收集 nvcc 报错**
- Run: `make build-cuda`
- 记录第一处错误位置（函数签名不匹配/未声明/未使用/重复定义等）

**Step 2: 逐个修复并反复编译**
- 修复点优先级：
  1) kernel/host 调用签名一致
  2) 旧 `sim_tb_init_boundaries_kernel` 与旧 `H/D/E/state` 残留引用清理或 `#if 0` 屏蔽
  3) 未使用变量/多余 include（保证 `-Werror` 环境也能过）
- Run: `make build-cuda` 直到成功

**Verification:**
- Expected: 产物 `./longtarget_cuda` 能链接生成；运行时不报 `cudaErrorInvalidDeviceFunction` 等 launch 错误。

---

### Task 2: 删除死代码并固化 direction bits 语义

**Files:**
- Modify: `cuda/sim_traceback_cuda.cu`

**Step 1: 删除不再使用的旧 DP buffer 与 kernel**
- 移除旧的 `HDevice/DDevice/EDevice/stateDevice` 分配/释放与相关 kernel 定义（如仍存在）
- 保留最小必要：`dirDevice` + 4 边界数组 + `ops/hadTie` buffer

**Step 2: 自检 corner/边界初始化**
- 确保 `H(0,0)=0`，`D/E` 初值满足 affine gap 公式
- 确保 tile 边界 index=0..T 都正确写回（覆盖 33 个值）

**Step 3: tie bits 语义一致**
- 要求：只有当“多个前驱在同一状态下打平”为 tie；blocked diag 时不应误报 tie
- fast 模式：不回退；strict 模式：回退 CPU（由上层 env 控制）

---

### Task 3: 跑 CUDA 回归（先 correctness 再性能）

**Files:**
- None (run tests)

**Step 1: CUDA smoke**
- Run: `make check-smoke-cuda`
- Expected: 不崩溃，能生成输出文件

**Step 2: sample exactness（strict）**
- Run: `LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK=1 LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE=1 ./scripts/run_sample_benchmark_traceback_cuda.sh`
- Expected: `benchmark.sim_traceback_backend` 显示 `cuda`（至少部分 case），并且与 oracle 不出现明显差异（tie 会触发回退）

**Step 3: sample speed（fast）**
- Run: `LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK=1 LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE=0 ./scripts/run_sample_benchmark_traceback_cuda.sh`
- Expected: `cuda` 使用比例更高；wall time 明显下降；若出现差异需在报告中量化（hadTie 触发但不回退导致）。

---

### Task 4: 输出差异量化（fast vs strict vs CPU）

**Files:**
- Modify (if needed): `scripts/run_sample_benchmark_traceback_cuda.sh`（仅限增加对比输出，不改默认行为）
- Modify (optional): `EXACT_SIM_PROGRESS.md`

**Step 1: 汇总指标**
- 收集：总候选数、GPU 使用比例、hadTie 比例、wall time、与 oracle 的差异统计（例如 score/coords/identity/stability）

**Step 2: 解释差异原因**
- 归因优先级：DP tie → 不同 tie-break path → 坐标/ops 变化；blocked/边界 bug；ops 容量截断等

---

### Task 5: 文档/进度更新（可选）

**Files:**
- Modify: `README.md`（若新增/调整 env 或注意事项）
- Modify (optional): `EXACT_SIM_PROGRESS.md`

**Step 1: README 增补**
- 说明 `LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE` 的 strict/fast 行为与适用场景
- 提醒：fast 可能非 byte-identical；strict 以回退换稳定

**Verification:**
- Run: `make build build-cuda`

