# LongTarget exact-SIM 进展记录

## 时间与目标

- 日期：2026-03-25（最近更新：2026-04-13）
- 仓库：`/data/wenyujianData/LongTarget-exact-sim`
- 目标：在 **最终输出文件 byte-identical** 的前提下，尽可能把 x86_64 CPU 路径优化到极致。
- 约束：
  - 不改 CLI。
  - 不改输出格式。
  - 不接受“近似一致”；验收标准是输出目录逐字节一致。

## 当前已经完成的工作

### 1. 外层调度与 exact 执行框架

- 已把外层 rule/fragment 执行整理为确定性 task table。
- 已支持可选 OpenMP 任务级并行，但通过“按原始 task 序号合并结果”保持输出顺序不变。
- 已把 transformed DNA 的构造和阈值缓存整合到 exact 执行路径里。

涉及文件：

- `exact_sim.h`
- `longtarget.cpp`

### 2. SIM 内核 exact 优化

- 保留 exact backend，不改算法语义。
- 已加入 candidate-start 索引，加速 `addnode()` 查找，但保留原有替换和 tie 语义。
- 已加入可复用的 wavefront scratch，减少热点路径重复分配。

涉及文件：

- `sim.h`

### 3. `calc_score` / threshold 路径优化

这是当前最主要的瓶颈，最近完成了以下几项：

- 新增 **AVX2 exact threshold kernel**，并保留 SSE 路径。
- 加入 **AVX2 运行时门控**：
  - `LONGTARGET_FORCE_AVX2=1`：强制 AVX2
  - `LONGTARGET_DISABLE_AVX2=1`：禁用 AVX2
- 在 macOS arm64 + Rosetta 的 x86_64 运行环境下，默认会回退到 SSE，避免 AVX2 反而更慢。
- `init_work()` 已按 **运行时选择的 SIMD 宽度** 构建 profile 布局。
- `calc_score` profile 已从原先的大字母表压缩到当前实际使用的 6 个符号 + 0 行。
- forward / reverse-complement profile 现已 **共享同一块 DP workspace**，减少重复 scratch 内存。
- target 编码改为紧凑索引，减少 profile 访问 footprint。
- 1002 次 shuffle 已改成确定性的 pair-loop，仍保持：
  - 固定 seed
  - 原有 shuffle 次序
  - forward / RC 交替顺序
  - `maxShufScore` 填充顺序
  - MLE 输入顺序
- **Permutation-direct alignment（SSE2 threshold 路径）**：
  - SW 对齐时直接按 permutation 读取 `encodedTarget`，避免每次 shuffle 先物化 `shuffledTarget` 再读回。
  - 在 **AVX2 threshold** 路径上保留 `shuffledTarget` 物化（native x86_64 基准下更快）。
- SW kernel 现在直接复用 profile 里预存的 `iter`，去掉每次对齐的重复布局计算。

涉及文件：

- `stats.h`

### 4. 构建 / 精确性 / 基准工具

- 已有 `Makefile` 构建目标。
- 已有 smoke/sample/matrix exactness 脚本与 benchmark 目标。
- 修复 `TFOsorted` 输出顺序的跨平台不确定性：`longtarget.cpp` 的 `comp()` 现在为严格全序比较器，并重生成 `tests/oracle*`。

涉及文件：

- `Makefile`
- `scripts/run_sample_exactness.sh`
- `scripts/run_rule_matrix_exactness.sh`

## 最近一轮修改后，已确认通过的验证

以下命令在本轮 `stats.h` 修改之后已经通过：

- `make build`
- `make build-avx2`
- `make check-smoke`
- `make check-sample`
- `make check-sample-row`
- `make check-smoke-avx2`
- `make check-sample-avx2`
- `LONGTARGET_FORCE_AVX2=1 TARGET=$PWD/longtarget_avx2 LONGTARGET_SIM_INITIAL_BACKEND=wavefront RULE=1 EXPECTED_DIR=$PWD/tests/oracle_rule1 OUTPUT_SUBDIR=sample_exactness_rule1 ./scripts/run_sample_exactness.sh`
- `LONGTARGET_FORCE_AVX2=1 TARGET=$PWD/longtarget_avx2 LONGTARGET_SIM_INITIAL_BACKEND=wavefront ./scripts/run_sample_exactness.sh`
- `make check-matrix`

结论：

- 当前状态下，默认构建、row sample、AVX2 构建、强制真实 AVX2 的 smoke/sample，都仍然满足 exact 输出要求。

## 当前基准结果

### 默认构建

#### smoke

- `benchmark.calc_score_seconds=7.25591`
- `benchmark.sim_seconds=2.18211`
- `benchmark.postprocess_seconds=0.00127917`
- `benchmark.total_seconds=9.44139`

#### sample

- `benchmark.calc_score_seconds=113.072`
- `benchmark.sim_seconds=53.6071`
- `benchmark.postprocess_seconds=0.00263813`
- `benchmark.total_seconds=166.697`

### `longtarget_avx2` 构建（运行时自动 fallback）

#### smoke

- `benchmark.calc_score_seconds=7.38605`
- `benchmark.sim_seconds=2.46352`
- `benchmark.postprocess_seconds=0.00114233`
- `benchmark.total_seconds=9.85259`

#### sample

- `benchmark.calc_score_seconds=114.34`
- `benchmark.sim_seconds=59.7937`
- `benchmark.postprocess_seconds=0.00267559`
- `benchmark.total_seconds=174.154`

### 强制真实 AVX2（当前机器：Rosetta 转译）

#### smoke

- `benchmark.calc_score_seconds=18.3667`
- `benchmark.sim_seconds=2.42272`
- `benchmark.postprocess_seconds=0.00119246`
- `benchmark.total_seconds=20.7924`

解释：

- 当前开发机是 `arm64 macOS` 上通过 `arch -x86_64` 跑 x86_64 二进制。
- 在这个环境里，强制 AVX2 会因为 Rosetta 转译成本而明显变慢。
- 因此这里的 AVX2 性能数字 **不能代表 native x86_64 机器** 的真实性能。

## 当前判断

- 最大瓶颈仍然是 `calc_score`，而不是 SIM 本体。
- 在 smoke 上，`calc_score` 约占总时间的 77%。
- 在 sample 上，`calc_score` 约占总时间的 68%。
- 所以下一步继续压 `stats.h`，收益会比继续抠 `sim.h` 更大。

## 下一步建议的优先级

### P0：继续做 `calc_score` 的 exact 优化

优先看这几个点：

1. **Permutation-direct alignment**
   - 目标：直接按 permutation 读取 target 做对齐，不再先物化 `shuffledTarget`。
   - 预期收益：减少每次 shuffle 的一次完整写入 + 后续读回。
   - 风险：中等，需要非常小心保持统计顺序和当前 quirky 行为完全一致。

2. **进一步减少 kernel 常量装载 / 热路径 setup**
   - 目标：继续把 `calc_score_align_target()` 每次调用里不变的状态挪到 workspace/profile。
   - 风险：低。

3. **native x86_64 机器上复测 AVX2**
   - 当前机器不适合评估 AVX2 的真实收益。
   - 需要在真 x86_64 Linux 或 Intel Mac 上复测 smoke/sample。

### P1：补齐 exactness 矩阵

虽然当前关键路径已经过了默认 matrix 和 sample-row，但如果继续改动，建议补跑：

- `make check-matrix-row`
- `make check-matrix-wavefront`
- `make check-sample-openmp-1`
- `make check-sample-openmp-par`
- `make check-matrix-openmp-1`
- `make check-matrix-openmp-par`

### P2：工程收尾

- 清理构建 warning：
  - `sim.h` 里的 dangling `else` warning
  - `sprintf` deprecated warning
- 这些目前不影响 exact 性，但会干扰后续构建输出。

## 下次继续时建议的起手顺序

1. 打开并阅读：
   - `stats.h`
   - `exact_sim.h`
   - `longtarget.cpp`
   - `sim.h`
   - 本文件
2. 先跑一遍快速验收：
   - `make build`
   - `make check-smoke`
3. 如果继续动 `stats.h`：
   - 优先从 permutation-direct alignment 开始。
4. 每做完一轮后至少跑：
   - `make check-smoke`
   - `make check-sample`
   - `make check-matrix`

## 2026-03-26（Linux x86_64）SIM wavefront 提速

本节记录在 Linux x86_64（`g++`）上的一轮 `sim.h` 优化，目标是在 **exact 输出 byte-identical** 前提下继续压 `SIM` 的常数项开销。

### 改动点

- `sim.h`：
  - `enumerateSimCandidateRegionWavefront()` 的 AVX2(8-lane)/SSE(4-lane) 扫描，在“连续区间可用”时批量加载 `prev/prevPrev` 的 score/坐标数组，减少每 lane 的 `contains/index` 与 `_mm*_setr_epi32` 组装开销。
  - wavefront row-events 改为 `emplace_back()`（微优化）。
  - `SimCandidateStartIndex` 的 `candidateIndex/candidateSlot` 改为 `int`（值域固定，减少 footprint）。

### 已通过的验证

- `make check-smoke`
- `make check-sample`

## 2026-03-28（Linux + RTX 4090）CUDA/批量吞吐优化与 lite 输出

本节记录一轮面向“海量 region / 全基因组批处理”的 GPU 优化与工程改动。核心原则仍是：**默认行为不变**，exactness 脚本仍可通过；新增能力通过 env 开关启用。

### 改动点（Phase 2）

- `longtarget.cpp`：
  - 新增可选 `*-TFOsorted.lite` 输出：`LONGTARGET_WRITE_TFOSORTED_LITE=1`。
- `fasim/Fasim-LongTarget.cpp`：
  - 新增可选 `*-TFOsorted.lite` 输出：`FASIM_WRITE_TFOSORTED_LITE=1`（与 `FASIM_OUTPUT_MODE=tfosorted` 搭配更适合大批量）。
- `cuda/calc_score_cuda.cu`：
  - 引入 per-device batch context，复用 `targets/permutations/scores` device buffers 与 events，避免每次调用 `cudaMalloc/cudaFree` + event create/destroy。
  - `calc_score_cuda_prepare_query()` 记录 `handle->device`，`release_query()` 会先 `cudaSetDevice(handle->device)` 再 free。
  - 只拷贝 kernel 实际需要的 permutations（`pairCount * 2`），避免无用 H2D。
- `cuda/sim_scan_cuda.cu`：
  - 从全局单例改为 per-device context + per-device mutex（参考 `prealign_cuda` 风格），并缓存 events。
  - 修复 `sim_scan_cuda_init(-1)`（未设置 `LONGTARGET_CUDA_DEVICE` 时）会失败的问题：`-1` 现在会自动归一到 device 0。
- `cuda/prealign_cuda.cu`：
  - preAlign topK 维护从“每次插入 O(K) 重新扫 min”改为 lane0 min-heap（O(logK)），减少 topK=128/256 的 GPU 侧开销。

### 已通过的验证/基准（本机：Ubuntu + 2x RTX 4090，常用 `CUDA_VISIBLE_DEVICES=1` 避免抢卡）

- exactness：
  - `CUDA_VISIBLE_DEVICES=1 make check-sample-cuda-sim-region`（oracle 输出一致；SIM initial/region backend 均为 CUDA）
- sample benchmark（LongTarget exact vs fast vs fasim）：
  - `CUDA_VISIBLE_DEVICES=1 make benchmark-sample-cuda-vs-fasim`
  - 代表性结果（见 `.tmp/sample_benchmark_vs_fasim/report.json`）：
    - `longtarget_exact internal≈38.893s`
    - `longtarget_fast (budget=0) internal≈7.805s`，strict overlap `72/75`
- 批量吞吐（fasim CPU vs fasim CUDA-prealign）：
  - `CUDA_VISIBLE_DEVICES=1 python3 scripts/benchmark_fasim_batch_throughput.py --entries 256 --cuda-topk 64`：speedup `~1.477x`
  - `CUDA_VISIBLE_DEVICES=1 python3 scripts/benchmark_fasim_batch_throughput.py --entries 256 --cuda-topk 128`：speedup `~0.950x`（topK 变大后 CPU extend 仍可能成为主瓶颈）

- `make check-matrix`
- `make check-smoke-avx2`
- `make check-sample-avx2`

### 基准结果（`LONGTARGET_BENCHMARK=1`）

#### smoke（RULE=1）

- 优化前：
  - `benchmark.calc_score_seconds=4.24461`
  - `benchmark.sim_seconds=3.95812`
  - `benchmark.total_seconds=8.21198`
- 优化后：
  - `benchmark.calc_score_seconds=3.92048`
  - `benchmark.sim_seconds=3.59424`
  - `benchmark.total_seconds=7.52321`

#### sample（RULE=0）

- 优化前：
  - `benchmark.calc_score_seconds=62.0045`
  - `benchmark.sim_seconds=93.4702`
  - `benchmark.total_seconds=155.521`
- 优化后：
  - `benchmark.calc_score_seconds=61.1914`
  - `benchmark.sim_seconds=86.3726`
  - `benchmark.total_seconds=147.612`

### gprof（sample，`-pg`）

- `calc_score_with_workspace` 仍是最大单点热点（~41% self time）。
- `enumerateSimCandidateRegionWavefront` self time 明显下降。
- `addnodeIndexed` 仍然很重（~19% self time，调用量 5e8+），下一步如果继续抠 SIM，优先继续压这一块。

## 2026-03-29（Linux + RTX 4090）fasim/fastSIM：lite-only 模式与 CPU 侧去字符串化

本节记录一轮围绕 `fasim_longtarget_cuda` 的工程优化，目标是“全基因组/海量 region 批处理”时：

- lite-only 场景只输出关键字段（identity/stability/score/坐标），避免 full TFOsorted 的大 I/O；
- 尽量减少 CPU 端的 **字符串构造** 与 **stdout 噪音**（二者都会显著拖慢 wall time）。

### 改动点

- `fasim/Fasim-LongTarget.cpp`：
  - 新增 `FASIM_OUTPUT_MODE=lite`：只写 `*-TFOsorted.lite`，不生成 `*-TFOsorted`。
    - 仍保留旧用法：`FASIM_OUTPUT_MODE=tfosorted` + `FASIM_WRITE_TFOSORTED_LITE=1`（双写 full+lite）。
  - 输出文件名对 `-f1` 传路径安全：先取 basename 再 strip `.fa/.fasta`（避免输出路径里出现 `/` 导致 open 失败）。
  - `same_seq()`：
    - 支持 lowercase `acgtun`；
    - 遇到未知字符不再逐字符 `cout << "unknown letter"`（chr22 会刷千万级行，stdout I/O 直接成为瓶颈）。
  - lite-only 时 `fastSIM_extend_from_scoreinfo(... materializeAlignmentStrings=false)`：不再构造 `read_align/ref_align_src` 对齐字符串。
- `fasim/fastsim.h`：
  - 新增 `fasim_calc_identity_and_triscore_from_cigar()`：按 `alignment.cigar` 直接计算 `MeanIdentity(%)` 与 `MeanStability`。
  - `convertMyTriplex()` 默认使用 cigar 计算 identity/stability；仅在 full 输出需要 `TFO/TTS sequence` 两列时才 materialize alignment strings。

### 新增回归

- `scripts/check_fasim_lite_output.sh`：
  - 验证 `FASIM_OUTPUT_MODE=lite` 只产出 `.lite`；
  - 验证 `-f1` 传带路径的 fasta 不会触发“输出文件名包含 `/`”的 open 失败。
- `scripts/check_fasim_no_unknown_letter.sh`：
  - lowercase 输入下 stdout 不应出现 `unknown letter`（避免 I/O 退化）。
- `make check-fasim-cigar`：
  - `tests/test_fasim_cigar_identity.cpp`：对比“旧字符串法”与“cigar 直算”在 M/I/D 混合 cigar 下的 identity/stability 一致性。

### chr22 基准（hg38 chr22，fastSIM + GPU prealign）

- 输入：`.tmp/ucsc/hg38/hg38_chr22.fa`（50,818,468 bp）
- 命令（1 GPU，lite-only）：
  - `FASIM_OUTPUT_MODE=lite FASIM_ENABLE_PREALIGN_CUDA=1 FASIM_CUDA_DEVICES=0 FASIM_EXTEND_THREADS=20 FASIM_VERBOSE=0 ./fasim_longtarget_cuda -f1 .tmp/ucsc/hg38/hg38_chr22.fa -f2 H19.fa -r 0 -O <out>`
- 结果（本机）：
  - 修复 stdout 刷屏前：wall `≈548.63s`（stdout `~320MB`，`unknown letter` `~2.1e7` 行）
  - 修复后：wall `≈487.83s`（stdout/stderr 基本为 0）
  - 输出：`hg38-H19-hg38_chr22-TFOsorted.lite` 行数 `134,999`
- 2 GPU（`FASIM_CUDA_DEVICES=0,1`）：
  - wall `≈621.04s`（未见收益；推测此时瓶颈在 CPU extend/调度，GPU prealign 不是主瓶颈）

### 备注 / 待办

- 与旧的 `hg38-H19-hg38_chr22-TFOsorted`（2026-03-29 早前 run，`161,970` 行）相比，lite 输出行数更少（`134,999` 行）。
  - 已确认：1GPU/2GPU 的 lite 输出一致；
  - 若需要与旧结果对齐，需要进一步定位差异来源（可能与旧版本代码/环境参数差异有关）。

## 2026-03-26：SIM top-K 维护提速（min-heap）+ threshold 编码 LUT

### 改动点

- `sim.h`：
  - `addnodeIndexed()`：当候选满载（K=50）时，用固定大小 **min-heap** 维护“最小 SCORE 候选”，替代每次 miss 的 O(K) 扫描；比较键为 `(SCORE, index)`，保证与原实现的 tie-break 一致（score 相等时优先淘汰更小的 index）。
  - `popHighestScoringSimCandidate()`/`initializeSimKernel()`：会改变候选数组布局时将 heap 标记为无效，后续需要时重建（K 很小，重建成本可控且确定）。
  - 增加可选统计：`LONGTARGET_PRINT_SIM_STATS=1` 时在 stderr 打印 `sim.stats ...`（默认关闭，不影响 oracle 对比）。
- `stats.h`：
  - `calc_score_with_workspace()`：目标序列编码改为 256-entry LUT（对非 ASCII 字节按 `N` 处理），减少每次阈值计算的编码开销。

### 已通过的验证

- `make check-smoke`
- `make check-sample`
- `make check-matrix`
- `make check-smoke-avx2`
- `make check-sample-avx2`
- `make check-matrix-avx2`

### 基准结果（`LONGTARGET_BENCHMARK=1`）

#### sample（RULE=0，SSE2，`longtarget_x86`）

- 基线（修改前）：
  - `benchmark.calc_score_seconds=60.8933`
  - `benchmark.sim_seconds=85.6227`
  - `benchmark.total_seconds=146.582`
- 优化后（min-heap + LUT）：
  - `benchmark.calc_score_seconds=57.3219`
  - `benchmark.sim_seconds=63.7616`
  - `benchmark.total_seconds=121.152`

#### smoke（RULE=1，SSE2，`longtarget_x86`）

- 基线（修改前）：
  - `benchmark.calc_score_seconds=3.88936`
  - `benchmark.sim_seconds=3.55305`
  - `benchmark.total_seconds=7.4517`
- 优化后（min-heap + LUT）：
  - `benchmark.calc_score_seconds=3.886`
  - `benchmark.sim_seconds=2.54199`
  - `benchmark.total_seconds=6.4371`

#### sample（RULE=0，AVX2，`longtarget_avx2`）

- 基线（修改前）：
  - `benchmark.calc_score_seconds=31.2525`
  - `benchmark.sim_seconds=85.4272`
  - `benchmark.total_seconds=116.739`
- 优化后（min-heap + LUT）：
  - `benchmark.calc_score_seconds=31.1719`
  - `benchmark.sim_seconds=63.236`
  - `benchmark.total_seconds=94.4553`

## 2026-03-26：Wavefront 坐标压缩（packed uint64）+ rowEvents 压缩

### 改动点

- `sim.h`：
  - wavefront 初始扫描新增 packed 实现：用 `uint64_t (i<<32|j)` 表示起点坐标，替代 `Hi/Hj/Di/Dj/Fi/Fj` 六组 `long` 数组，降低坐标搬运与内存带宽压力。
  - packed 路径下 rowEvents 缓冲改为更小的 `SimWavefrontRowEventPacked`（`endI` 由 row 隐含），flush 时再还原成 `SimInitialCellEvent` 并调用 `onEvent`，减少事件写放大。
  - 通过 wrapper 自动选择 packed（`row/col` 在 `uint32` 范围且边界非负），否则回退到旧的 wide(long) 实现，保持兼容性。
  - packed 路径中，AVX2/SSE2 向量化分支用 `_mm256_loadu/_mm256_storeu`（以及 `_mm_loadu/_mm_storeu`）替代 `memcpy()` 拷贝坐标数组，减少坐标搬运的额外开销。

### 已通过的验证

- `make check-smoke`
- `make check-sample`
- `make check-matrix`
- `make check-smoke-avx2`
- `make check-sample-avx2`
- `make check-matrix-avx2`

### 基准结果（`LONGTARGET_BENCHMARK=1`）

#### sample（RULE=0，AVX2，`longtarget_avx2`）

- packed 前（已启用 min-heap + LUT）：
  - `benchmark.calc_score_seconds=31.1719`
  - `benchmark.sim_seconds=63.236`
  - `benchmark.total_seconds=94.4553`
- packed 后：
  - `benchmark.calc_score_seconds=31.0007`
  - `benchmark.sim_seconds=56.0907`
  - `benchmark.total_seconds=87.1437`
- packed 后（坐标拷贝 SIMD 化，示例一次运行）：
  - `benchmark.calc_score_seconds=31.4995`
  - `benchmark.sim_seconds=53.9707`
  - `benchmark.total_seconds=85.5325`

#### sample（RULE=0，SSE2，`longtarget_x86`）

- packed 后（示例一次运行；`calc_score_seconds` 会受系统负载影响波动较大，重点看 `sim_seconds`）：
  - `benchmark.calc_score_seconds=64.4522`
  - `benchmark.sim_seconds=58.6717`
  - `benchmark.total_seconds=123.174`

## 2026-03-26：SIM run-updater 实验（可回退）

- 新增运行时开关：`LONGTARGET_SIM_RUN_UPDATER=1` 启用（默认关闭）。
- 默认路径：逐 event 调用 `addnodeIndexed()`（候选插入/淘汰时序与原逻辑一致）。
- run-updater 路径：按 run（同一行内连续相同 `startI/startJ/endI`）聚合更新：
  - **run start**：先确保候选槽位（保持 top-K 在线淘汰时序不变），并立即对该首事件执行一次与 `addnodeIndexed()` 等价的候选更新；
  - **run end**：仅当 `runLen>1` 时再补写 max-score 与 `LEFT/RIGHT` 边界（`runLen==1` 走快速 no-op flush，避免额外开销）。

### 回归验证（本次修改后已通过）

- `make build` / `make build-avx2`
- `make check-smoke check-sample check-matrix`
- `make check-smoke-avx2 check-sample-avx2 check-matrix-avx2`
- 并且在 `LONGTARGET_SIM_RUN_UPDATER=1` 下同样通过上述两组回归。

### 基准对比（`LONGTARGET_BENCHMARK=1`，sample，`TARGET=longtarget_avx2`）

运行命令：

- run-updater 关闭（默认）：`LONGTARGET_BENCHMARK=1 TARGET=$PWD/longtarget_avx2 LONGTARGET_SIM_INITIAL_BACKEND=wavefront ./scripts/run_sample_exactness.sh`
- run-updater 开启：`LONGTARGET_SIM_RUN_UPDATER=1 LONGTARGET_BENCHMARK=1 TARGET=$PWD/longtarget_avx2 LONGTARGET_SIM_INITIAL_BACKEND=wavefront ./scripts/run_sample_exactness.sh`

结果（各 5 次运行，中位数；当前机器）：

- run-updater 关闭（默认）：
  - `benchmark.sim_seconds`：`[54.106, 53.9103, 54.2603, 53.575, 53.5093]`，median=`53.9103`
  - `benchmark.total_seconds`：median=`85.7285`
- run-updater 开启（`LONGTARGET_SIM_RUN_UPDATER=1`）：
  - `benchmark.sim_seconds`：`[58.2986, 58.2176, 58.1466, 58.1344, 58.0436]`，median=`58.1466`
  - `benchmark.total_seconds`：median=`89.7427`

结论（当前 workload）：

- run-updater 平均 run 长度约 `1.6~1.7`（`run_updater_total_run_len / run_updater_flushes`），max 约 `50+`，但整体明显变慢（`sim_seconds` 中位数增加约 `+4.24s`，约 `+7.9%`）。
- 因此建议保持 **默认关闭**，仅在需要继续实验时再显式开启。

### SIM stats（`LONGTARGET_PRINT_SIM_STATS=1`）

- `sim.stats` 输出新增字段：
  - `events_seen`：handler 收到的 event 数（run-updater=0 时应与 `addnode_calls` 一致；run-updater=1 时通常大于 `addnode_calls`）
  - `addnode_calls`：run-updater=1 时表示 run start 的“等价 addnode 更新次数”（与 `run_updater_runs_started` 一致）
  - `run_updater_runs_started` / `run_updater_flushes` / `run_updater_total_run_len` / `run_updater_max_run_len` / `run_updater_skipped_events`

## 2026-03-29（Linux + RTX 4090）SIM exact region CUDA：runningMin 语义修正、region telemetry、experimental reduce

这一轮的目标不是“放宽 exact 约束”，而是在保持 candidate 维护语义不变的前提下，继续逼近 SIM region 路径的真实瓶颈。

### 关键结论

- 论文里的“寻找 `k` 个不相交 local alignments”不能一次性 exact 地全 GPU 化并一把求完；它本质上仍然要迭代地维护当前候选集、更新 floor、屏蔽已确认区域。
- `runningMin` 必须代表“当前候选集合里的真实最小分数”，不能继续沿用旧的哨兵式语义；否则严格 `>` floor 的过滤顺序会偏掉。
- “单个 start key 只回传一个 summary” 不是 exact-safe。反例很直接：同一个 key 后续出现更高分事件时，会改变 floor 更新时序，从而改变最终 top-`K`。
- 因此，目前可以尝试的“更全 GPU”方案，只能是 GPU 端串行复现 candidate maintenance 语义；不能把整段时序压缩成一个无序 summary 再回放。

### 改动点

- `sim.h`：
  - `addnodeIndexed()` 现在返回并刷新当前候选集合的真实最小分数。
  - `popHighestScoringSimCandidate()` 之后也会刷新 `runningMin`。
  - 新增 `simCurrentCandidateFloor()` / `refreshSimRunningMin()`，把 floor 语义显式化。
  - 新增 `benchmark.sim_region_events_total`
  - 新增 `benchmark.sim_region_candidate_summaries_total`
  - 新增 `benchmark.sim_region_event_bytes_d2h`
  - 新增 `benchmark.sim_region_summary_bytes_d2h`
  - 新增 `benchmark.sim_region_cpu_merge_seconds`
  - 新增 `benchmark.sim_locate_total_cells`
  - 新增 `benchmark.sim_locate_backend`
  - 新增 `benchmark.sim_locate_mode`
  - 新增 `benchmark.sim_locate_fast_passes`
  - 新增 `benchmark.sim_locate_fast_fallbacks`
  - 新增 `benchmark.sim_locate_gpu_seconds`
- `cuda/sim_scan_cuda.h` / `cuda/sim_scan_cuda.cu`：
  - region CUDA 新增 `reduceCandidates` / `seedCandidates` / `seedRunningMin` 接口。
  - 默认路径仍是 raw events D2H + host merge。
  - 新增 experimental 路径：`LONGTARGET_ENABLE_SIM_CUDA_REGION_REDUCE=1` 时，region events 会先压成 row-major same-start run summaries，再在 GPU 上做 candidate reduction，只回传最终 candidate 集合。
- `cuda/sim_locate_cuda.h` / `cuda/sim_locate_cuda.cu`：
  - 新增 locate-first exact-safe CUDA backend：单个 request 由单线程 kernel 严格复现 CPU `locate()` / `no_cross()` 语义。
  - 运行时开关为 `LONGTARGET_ENABLE_SIM_CUDA_LOCATE=1`；默认关闭。
  - `LONGTARGET_SIM_CUDA_LOCATE_MODE=safe_workset` 现已作为 locate 加速开启时的默认 exact-safe 主线：直接从 materialized traceback + persisted safe candidate-state store 构造稀疏 workset，失败时保留 exact locate/update 回退。
  - `LONGTARGET_SIM_CUDA_LOCATE_MODE=exact` 仍可强制走旧的 locate-first exact backend，主要用于对拍、shadow 和定位 safe_workset 回退原因。
  - 新增 `LONGTARGET_SIM_CUDA_LOCATE_EXACT_PRECHECK=off|shadow|on`：给 `safe_workset` exact fallback 增加有界 exact precheck；`shadow` 只统计不改变语义，`on` 允许在 precheck 证明 `no_update_region` 时直接短路 exact fallback。
  - 新增 `LONGTARGET_SIM_CUDA_LOCATE_MODE=fast`：实验性 aggressive path-local update；当前 fast 路径不再跑 reverse-DP locate，而是从 traceback script 提取 row-local path summary，再构造 banded sparse workset 做 region update。
  - `LONGTARGET_SIM_CUDA_LOCATE_FAST_SHADOW=1` 时，fast 路径会 shadow exact CPU `locate()+update`；若 sparse workset 不能复现 exact candidate state，则回退 exact，并按 `runningMin` / `candidateCount` / `candidateValue` 分类统计。
  - traceback path summary 现在会额外保留方向性 `segments`（diagonal / horizontal / vertical），供 fast workset 和 telemetry 复用。
  - exact locate 结果现在还会记录 `baseCellCount` / `expansionCellCount` / `stopByNoCross` / `stopByBoundary`，benchmark 新增 `benchmark.sim_safe_window_exact_fallback_base_no_update`、`benchmark.sim_safe_window_exact_fallback_expansion_no_update`、`benchmark.sim_safe_window_exact_fallback_stop_no_cross`、`benchmark.sim_safe_window_exact_fallback_stop_boundary`、`benchmark.sim_safe_window_exact_fallback_base_cells`、`benchmark.sim_safe_window_exact_fallback_expansion_cells`、`benchmark.sim_safe_window_exact_fallback_locate_gpu_seconds`，用于继续拆解 exact fallback 里的 no-update 成本。
  - 当前状态：`test_sim_locate_update` 已覆盖 traceback path summary / segment 语义 / banded workset / fast telemetry 基础语义；fresh benchmark 已显示 locate 成为主瓶颈，而 `safe_workset` 可在样例口径上把总时间从约 `28.0s` 压到约 `13.1s`，因此现阶段改为默认主线。`fast` 在默认 `pad=128` 下仍偏保守，benchmark 口径会频繁回退到 exact，因此暂不作为默认主线。
- `longtarget.cpp`：
  - benchmark stderr 会打印上述 region telemetry 字段，以及 `benchmark.sim_locate_backend` / `benchmark.sim_locate_mode` / `benchmark.sim_locate_fast_passes` / `benchmark.sim_locate_fast_fallbacks` / `benchmark.sim_locate_gpu_seconds`。
  - 新增 `benchmark.sim_fast_workset_bands` / `benchmark.sim_fast_workset_cells` / `benchmark.sim_fast_segments` / `benchmark.sim_fast_diagonal_segments` / `benchmark.sim_fast_horizontal_segments` / `benchmark.sim_fast_vertical_segments`。
  - 新增 `benchmark.sim_fast_fallback_no_workset` / `benchmark.sim_fast_fallback_area_cap` / `benchmark.sim_fast_fallback_shadow_running_min` / `benchmark.sim_fast_fallback_shadow_candidate_count` / `benchmark.sim_fast_fallback_shadow_candidate_value`，用于判断 fast locate 的主要失败模式。

### 默认路径与实验路径

- 默认 exact-safe 路径：
  - `LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1`
  - CUDA 负责 region 扫描，但仍把 raw row-events 拷回 CPU，并在 host 端按原始时序合并到 exact candidate maintenance。
- 实验路径：
  - `LONGTARGET_ENABLE_SIM_CUDA_REGION_REDUCE=1`
  - 当前只建议用于 profiling/实验；traceback-update rescan 场景下如果 `LONGTARGET_SIM_RUN_UPDATER=1`，仍优先保持原始 host merge 语义。
- 当前结论：
  - experimental reduce 逻辑上更接近“candidate maintenance GPU 化”，但 benchmark 明显回归，因此默认关闭，不作为主线。

### 已通过的验证

- `make build-cuda`
- `make check-sim-scan-batch`
- `make check-sim-initial-cuda-merge`
- `sh ./scripts/check_benchmark_telemetry.sh`
- `make check-benchmark-telemetry`
- `make check-smoke-cuda-sim-region`
- `make check-sample-cuda-sim-region`
- `make check-matrix-cuda-sim-region`
- `make check-smoke`
- `make check-sample`

### 当前 benchmark 记录

- benchmark telemetry 样例（`LONGTARGET_BENCHMARK=1 LONGTARGET_ENABLE_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1 LONGTARGET_TWO_STAGE=1 LONGTARGET_PREFILTER_BACKEND=prealign_cuda`）：
  - `benchmark.sim_region_events_total=2589982`
  - `benchmark.sim_region_candidate_summaries_total=0`
  - `benchmark.sim_region_event_bytes_d2h=62159568`
  - `benchmark.sim_region_summary_bytes_d2h=0`
  - `benchmark.sim_region_cpu_merge_seconds=0.0315497`
  - `benchmark.sim_locate_total_cells=13856334`
  - `benchmark.sim_seconds=2.23443`
- 本轮继续补了 phase timing telemetry：
  - `benchmark.sim_initial_scan_seconds`
  - `benchmark.sim_initial_scan_gpu_seconds`
  - `benchmark.sim_initial_scan_d2h_seconds`
  - `benchmark.sim_initial_scan_cpu_merge_seconds`
  - `benchmark.sim_locate_seconds`
  - `benchmark.sim_region_scan_gpu_seconds`
  - `benchmark.sim_region_d2h_seconds`
  - `benchmark.sim_materialize_seconds`
  - `benchmark.sim_traceback_dp_seconds`
  - `benchmark.sim_traceback_post_seconds`
- 本轮继续把 CUDA initial scan 的 handoff 再往前推一层：GPU 侧先把 raw initial events 压成“同一 row 内 contiguous same-start run summaries”，host 只回放 summaries：
  - `cuda/sim_scan_cuda.h` / `cuda/sim_scan_cuda.cu`：
    - 新增 `SimScanCudaInitialRunSummary`。
    - initial path 不再走 `rowCounts D2H -> CPU prefix sum -> rowOffsets H2D -> raw events D2H`。
    - 改成 `GPU prefix sum -> raw event compact -> GPU run-summary count/compact -> summary D2H`。
  - `sim.h`：
    - 新增 `summarizeSimCudaInitialRowEventRuns()` / `mergeSimCudaInitialRunSummaries()` / `applySimCudaInitialRunSummary()`。
    - `mergeSimCudaInitialRowEventRuns()` 现在只是 tests / fallback 对照用 wrapper。
    - `enumerateInitialSimCandidates()` 的 CUDA 默认路径改为直接消费 `initialRunSummaries`。
  - `tests/test_sim_initial_cuda_merge.cpp`：
    - 扩展到同时校验 row-event merge 和 run-summary merge。
    - 补了“同一 run 内最大分数重复出现时，`scoreEndJ` 必须保留第一次达到最大值的位置”这一 exact 语义。
    - 这组样例里，逻辑 addnode/update 次数从 `12` 个 raw events 压到 `7` 个 summaries。
- 本轮继续把 initial run-summary kernels 本体从“每 row 单线程串行扫 events”推进到 block-parallel：
  - `cuda/sim_scan_cuda.h`：
    - 新增 host/device 共用 helper：`simScanCudaInitialRunStartsAt()`、`initSimCudaInitialRunSummary()`、`updateSimCudaInitialRunSummary()`。
    - 让 host summarize 与 CUDA compact 共享同一套 run 边界和 summary 更新语义。
  - `cuda/sim_scan_cuda.cu`：
    - `sim_scan_count_initial_run_summaries_kernel` 现在按 row 启一个 block，多线程并行识别 run 起点并做块内归约。
    - `sim_scan_compact_initial_run_summaries_kernel` 现在按 chunk 并行检测 run starts；只有 run 起点线程负责串行延伸该 run 并写 summary，因此仍保持 row 内时序和“首次达到最大分数的位置”语义。
  - `sim.h`：
    - `summarizeSimCudaInitialRowEventRuns()` 改为直接复用这些 helper，避免 host/CUDA 语义漂移。
  - `tests/test_sim_initial_cuda_merge.cpp`：
    - 新增 helper 级断言，覆盖 run start 边界与 summary 累加语义。
  - fresh 验证：
    - `make check-sim-initial-cuda-merge`
    - `make check-sim-scan-batch`
    - `make build-cuda`
    - `make check-smoke-cuda-sim-region`
    - `make check-sample-cuda-sim-region`
- 本轮继续把“initial summaries 之后的 candidate maintenance”往 GPU 推一层，但只作为 **experimental** 路径：
  - `sim.h`：
    - 新增 `simInitialCudaCandidateReduceEnabledRuntime()`，读取 `LONGTARGET_ENABLE_SIM_CUDA_INITIAL_REDUCE`（默认关闭）。
    - 新增 host reference reducer：`reduceSimCudaInitialRunSummariesToCandidateStates()`，作为 tests / CUDA 语义对照基线。
    - `enumerateInitialSimCandidates()` 在 experimental 模式下不再 host merge summaries，而是直接应用 CUDA 回传的 reduced candidate states。
    - 新增 initial telemetry：`benchmark.sim_initial_events_total` / `benchmark.sim_initial_run_summaries_total` / `benchmark.sim_initial_summary_bytes_d2h` / `benchmark.sim_initial_reduced_candidates_total`。
  - `cuda/sim_scan_cuda.h` / `cuda/sim_scan_cuda.cu` / `cuda/sim_scan_cuda_stub.cpp`：
    - initial enumerate 接口现在也支持 `reduceCandidates`，并可直接返回 `candidateStates + runningMin + runSummaryCount`。
    - 新增 `sim_scan_reduce_initial_candidate_states_kernel`，按 **run-summary 原始顺序** 在 GPU 上串行维护 candidate states。
    - 这条路径明确 **不** 复用 region reduce 的 `event.score <= runningMin` 早跳过逻辑，因为它对 initial summaries 不是 exact-safe。
  - `tests/test_sim_initial_cuda_merge.cpp`：
    - 新增 reduced candidate states 对照。
    - 新增反例，证明“live floor skip”会破坏 initial summary 的 bbox/candidate 语义。
  - fresh 验证：
    - `make check-sim-initial-cuda-merge`
    - `make build-cuda`
    - `LONGTARGET_ENABLE_SIM_CUDA_INITIAL_REDUCE=1 make check-smoke-cuda-sim-region`
    - `LONGTARGET_ENABLE_SIM_CUDA_INITIAL_REDUCE=1 make check-sample-cuda-sim-region`
- experimental initial reduce 的 fresh telemetry（2026-03-30，`LONGTARGET_ENABLE_SIM_CUDA_INITIAL_REDUCE=1`）：
  - `benchmark.sim_initial_events_total=102576873`
  - `benchmark.sim_initial_run_summaries_total=41537986`
  - `benchmark.sim_initial_summary_bytes_d2h=0`
  - `benchmark.sim_initial_reduced_candidates_total=2400`
  - `benchmark.sim_initial_scan_cpu_merge_seconds=0`
  - `benchmark.sim_initial_scan_seconds=240.447`
  - `benchmark.sim_initial_scan_gpu_seconds=240.436`
  - `benchmark.sim_initial_scan_d2h_seconds=239.636`
  - 结论：语义上已经能走通，并且彻底绕过了 host summary merge / summary D2H；但当前 GPU 端仍是单 block/单线程 replay `41M+` summaries，性能严重回退，所以必须继续默认关闭。
- experimental initial reduce ordered replay v2 的 fresh telemetry（2026-03-31，`LONGTARGET_ENABLE_SIM_CUDA_INITIAL_REDUCE=1`）：
  - `benchmark.sim_initial_events_total=102576873`
  - `benchmark.sim_initial_run_summaries_total=41537986`
  - `benchmark.sim_initial_summary_bytes_d2h=0`
  - `benchmark.sim_initial_reduced_candidates_total=2400`
  - `benchmark.sim_initial_all_candidate_states_total=3311201`
  - `benchmark.sim_initial_store_bytes_d2h=119203236`
  - `benchmark.sim_initial_scan_cpu_merge_seconds=0.799353`
  - `benchmark.sim_initial_scan_seconds=62.9735`
  - `benchmark.sim_initial_scan_gpu_seconds=62.0747`
  - `benchmark.sim_initial_scan_d2h_seconds=61.2036`
  - `benchmark.sim_locate_seconds=9.3675`
  - `benchmark.sim_seconds=77.6397`
  - `LONGTARGET_ENABLE_SIM_CUDA_INITIAL_REDUCE=1 make check-smoke-cuda-sim-region` / `make check-sample-cuda-sim-region`：通过
  - 结论：在保持 exact-safe 语义的前提下，initial ordered replay 已从 thread-0 串行 bookkeeping 切到 warp-cooperative min/hash replay；同口径大样本上，experimental initial reduce 的 `benchmark.sim_initial_scan_seconds` 从 `240.447s` 降到 `62.9735s`，`benchmark.sim_initial_scan_d2h_seconds` 从 `239.636s` 降到 `61.2036s`。它仍然显著慢于默认 summary-handoff 主线，但已经从“不可用的验证路径”推进到“可以继续围绕 all-state handoff / locate orchestration 继续拆”的阶段。
- fresh benchmark telemetry（当前主线，`LONGTARGET_BENCHMARK=1 LONGTARGET_ENABLE_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1 LONGTARGET_TWO_STAGE=1 LONGTARGET_PREFILTER_BACKEND=prealign_cuda`）显示：
  - `benchmark.sim_initial_scan_seconds=0.940329`
  - `benchmark.sim_initial_scan_gpu_seconds=0.580581`
  - `benchmark.sim_initial_scan_d2h_seconds=0.227262`
  - `benchmark.sim_initial_scan_cpu_merge_seconds=0.170375`
  - `benchmark.sim_locate_seconds=0.200503`
  - `benchmark.sim_region_scan_gpu_seconds=0.238014`
  - `benchmark.sim_region_d2h_seconds=0.102823`
  - `benchmark.sim_materialize_seconds=0.0234363`
  - `benchmark.sim_traceback_dp_seconds=0.0226141`
  - `benchmark.sim_traceback_post_seconds=0.000776931`
  - `benchmark.sim_seconds=1.98866`
- 结论更新：
  - 当前默认 exact-safe 主线里，下一瓶颈不是 `locate()`，而是 **initial scan 的整体成本**。
  - 这轮之后，`initial scan` 内部的 **CPU merge** 在 benchmark 口径进一步降到约 `0.17s`；host merge 已不再是最明显的主单项。
  - 对大样本口径（`sample_exactness_cuda_sim_region`），summary handoff 也开始真正压到 D2H：`benchmark.sim_initial_scan_d2h_seconds` 约 `0.91s -> 0.51s`，`benchmark.sim_initial_scan_cpu_merge_seconds` 约 `1.85s -> 1.56s`。
  - 这轮已把 summary kernels 从单线程 row scan 推到 block-parallel run-start 检测；下一轮更该继续拆的是 **更深一层的 initial device-side candidate maintenance**，而不是再回到 host raw-event replay。
- rule1 同口径样例（`LONGTARGET_ENABLE_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA=1 LONGTARGET_ENABLE_SIM_CUDA_REGION=1`）：
  - `benchmark.sim_initial_scan_seconds=0.69382`
  - `benchmark.sim_initial_scan_gpu_seconds=0.0813394`
  - `benchmark.sim_initial_scan_d2h_seconds=0.101101`
  - `benchmark.sim_initial_scan_cpu_merge_seconds=0.24531`
  - `benchmark.sim_locate_seconds=0.184216`
  - `benchmark.sim_region_scan_gpu_seconds=0.137605`
  - `benchmark.sim_region_d2h_seconds=0.0451942`
  - `benchmark.sim_materialize_seconds=0.00654041`
  - `benchmark.sim_traceback_dp_seconds=0.00531126`
  - `benchmark.sim_traceback_post_seconds=0.00121972`
  - `benchmark.sim_seconds=1.03987`
  - 相比上一轮 rule1 fresh 记录（`benchmark.sim_initial_scan_cpu_merge_seconds≈0.256482`、`benchmark.sim_seconds≈0.886468`），这条小样本口径主要看到的是 CPU merge 继续小降，但总时延波动更大；因此不能只看 rule1，要结合大样本与 benchmark 口径一起判断。
- 大样本口径（`sample_exactness_cuda_sim_region`）：
  - `benchmark.sim_initial_scan_seconds=3.51724`
  - `benchmark.sim_initial_scan_gpu_seconds=1.09364`
  - `benchmark.sim_initial_scan_d2h_seconds=0.506416`
  - `benchmark.sim_initial_scan_cpu_merge_seconds=1.55846`
  - `benchmark.sim_seconds=17.6897`
  - 相比上一轮同口径 fresh 记录（`benchmark.sim_initial_scan_seconds≈4.82037`、`benchmark.sim_initial_scan_d2h_seconds≈0.908488`、`benchmark.sim_initial_scan_cpu_merge_seconds≈1.85408`、`benchmark.sim_seconds≈19.1254`），这次 summary handoff 在真正大的 initial scan 上收益更稳定。
- experimental reduce 路径（`LONGTARGET_ENABLE_SIM_CUDA_REGION_REDUCE=1`）：
  - rule1 样例：`benchmark.sim_seconds=1.53914`
  - 说明：虽然 D2H 从 raw events 变成 candidate summaries，但当前 GPU 端串行 reduction 仍比默认路径慢，因此不宜默认开启。
- 2026-04-02 更新：
  - 新增 `LONGTARGET_SIM_CUDA_INITIAL_REDUCE_BACKEND=legacy|hash`，用于选择 experimental initial reduce backend；`hash` 会把 single-request initial reduce 也路由到现有 true-batch/hash/device-residency 框架，`LONGTARGET_SIM_CUDA_INITIAL_HASH_REDUCE=1` 保留为兼容别名。
  - benchmark stderr 新增 `benchmark.sim_initial_reduce_backend={off|legacy|hash}`，便于区分 sample / whole-genome projection 日志到底用的是哪条 initial reducer 路径。

### 下一步建议

- 如果继续做 exact-safe 优化，优先看 **initial run-summary kernels** 本身：
  - 优先从 profiler 看 block-parallel 版里是否仍被“长 run 的单线程延伸”拖住。
  - 如果是，再考虑引入更细粒度的 segmented reduce / warp-cooperative run aggregation。
- 下一条更值得推进的是 **experimental initial device-side candidate maintenance**：
  - 当前已经有可跑通的 experimental v1；下一轮不该再补接口，而该直接优化 `sim_scan_reduce_initial_candidate_states_kernel` 本体。
  - 输入仍应当是 row-run summaries，而不是 raw events，也不是“单 key 无序 summary”。
  - 优先看是否能把串行 replay 拆成更细粒度的 segmented / chunked candidate maintenance，同时保持原始 summary 顺序。
- `locate()` / backward pass 仍然有量化入口（`benchmark.sim_locate_total_cells` / `benchmark.sim_locate_seconds`），但它已不是当前最该先拆的单点。
- 不建议再回到“单 summary 替代单 key 全时序”的思路，它已经被证明不是 exact-safe。

## 2026-04-04（whole-genome harness / telemetry）Task 1 完成

这一轮不改 SIM / threshold 的算法语义，只补 **whole-genome harness** 缺的解释变量，目标是给下一步的并列 P0 提供可靠观测：

- `window pipeline` 侧新增 lane telemetry：
  - `benchmark.sim_window_pipeline_tasks_considered`
  - `benchmark.sim_window_pipeline_tasks_eligible`
  - `benchmark.sim_window_pipeline_ineligible_*`
  - `benchmark.sim_window_pipeline_batch_runtime_fallbacks`
- `calc_score` 侧新增 coverage telemetry：
  - `benchmark.calc_score_tasks_total`
  - `benchmark.calc_score_cuda_tasks`
  - `benchmark.calc_score_cpu_fallback_*`
  - `benchmark.calc_score_query_length`
  - `benchmark.calc_score_target_bin_*`
- `scripts/project_whole_genome_runtime.py` 保持原有线性外推：
  - `projected_total_seconds`
  - `projected_calc_score_seconds`
  - `projected_sim_seconds`
  - `projected_postprocess_seconds`
  - 但在源 benchmark 含新字段时，会额外给出 `window_pipeline_eligible_ratio`、`window_pipeline_fallback_ratio`、`calc_score_cuda_task_ratio`、`calc_score_cpu_fallback_ratio`

关键实现约束：

- `window pipeline` 的计数只做旁路 telemetry，不改变 batching / fallback 行为。
- task 级 ineligible reason 采用单一 primary reason，保证 `considered = eligible + sum(ineligible_*)` 可闭合。
- `calc_score` coverage 也采用单一 primary fallback reason，保证 `calc_score_tasks_total = calc_score_cuda_tasks + calc_score_cpu_fallback_tasks` 可闭合。
- target length histogram 先做 1D 分桶（`<=8192`、`8193..65535`、`>65535`），不在这一轮引入更复杂的 2D query-target 直方图。

验证：

- `make build`
- `make check-project-whole-genome-runtime`
- `make check-sim-cuda-window-pipeline`
- `make check-sim-cuda-window-pipeline-overlap`

结论：

- 现在 benchmark stderr 已经能区分“lane 不 eligible”和“lane eligible 但 runtime fallback”。
- 现在也能直接看 whole-genome workload 里有多少 `calc_score` 任务根本没进 CUDA，以及主因是不是长度门槛。
- 这一步把 Task 2 / Task 3 的 profiler 与 representative shard benchmark 前置条件补齐了；下一步可以直接围绕 `initial scan` 和 `calc_score/threshold coverage` 做并列 P0。

## 2026-04-04（Task 2 / initial-scan observability）

- 本轮先把 Task 2 的“先观测、后优化”部分落到代码上，但 **没有改变默认 exact-safe 的 initial-scan 语义**：
  - `longtarget.cpp` 新增两个 initial-scan 派生 benchmark 字段：
    - `benchmark.sim_initial_scan_cpu_merge_subtotal_seconds`
    - `benchmark.sim_initial_run_summary_pipeline_seconds`
  - `scripts/check_benchmark_telemetry.sh` 现在也会强制检查：
    - `benchmark.sim_initial_scan_sync_wait_seconds`
    - `benchmark.sim_initial_reduce_chunks_*`
    - 上面两个新的 derived subtotals
  - `scripts/project_whole_genome_runtime.py` / `scripts/check_project_whole_genome_runtime.sh` 现在会在源 log 含相关字段时额外输出：
    - `projected_sim_initial_scan_seconds`
    - `projected_sim_initial_scan_cpu_merge_seconds`
    - `projected_sim_initial_scan_cpu_merge_subtotal_seconds`
    - `projected_sim_initial_run_summary_pipeline_seconds`
- `tests/test_sim_initial_cuda_merge.cpp` 新增了 run-boundary helper 断言，覆盖 `simScanCudaInitialRunEndExclusive(...)` 的 row 内 run 结束边界语义；`sim.h` 的 host summarizer 也改成复用这条 helper，避免 host-side summary 逻辑分叉。
- 本轮也尝试过把 initial run-summary kernels 再往前推一层（尤其是 direct true-batch path 的更激进 chunk-local fast path），但在真实 smoke exactness 上触发了回归；因此这些 risky kernel 改动 **没有保留在默认主线里**。保留下来的只有：
  - whole-genome / initial-scan telemetry
  - projection / benchmark checks
  - helper-level exactness coverage
- 当前结论更新：
  - Task 2 第一轮已经把 initial-scan breakdown 变成一等 benchmark 指标，whole-genome harness 现在可以直接看 initial-scan 总量、CPU merge subtotal 和 run-summary pipeline subtotal。
  - 但 default exact-safe 主线还没有接受新的 initial-scan kernel fast path，因为现有 smoke/sample/matrix gate 说明“大样本 true-batch direct-summary exactness”还需要更强的专门 fixture。
  - 下一轮如果继续做 initial-scan GPU 优化，优先应该先补 **更大规模的 CUDA initial summary exactness fixture**（尤其是真正覆盖 `direct_true_batch` 的长样本模式），再重试 kernel 级 fast path；否则很容易在小 test 绿、大样本 exactness 红。

## 2026-04-08（two-stage frontier calibration）

- 这一轮把工作重点从“先补 telemetry”推进到“给实验性 two-stage lane 建质量前沿”：
  - 新增 `scripts/benchmark_two_stage_frontier_sweep.py`，用同一个 exact LongTarget baseline 对比多组 `LONGTARGET_TWO_STAGE=1` + `LONGTARGET_PREFILTER_BACKEND=prealign_cuda` 参数组合。
  - 新增 `scripts/summarize_two_stage_frontier.py`，把多个 `report.json` 聚合成 Pareto-oriented summary，直接输出 `best_overall`、`best_qualifying`、`pareto_optimal` 等决策字段。
  - `README.md` / `Makefile` 同步加入 `benchmark-two-stage-frontier-sweep`、`check-two-stage-frontier-sweep`、`check-summarize-two-stage-frontier`。
- 这一步的目标不是默认启用 two-stage，而是把“速度更快但质量是否可接受”从口头判断变成可批量跑的 frontier sweep：
  - report 会同时记录 wall time 与质量侧指标；
  - 也会保留 `prefilter_hits`、`refine_window_count`、`refine_total_bp` 这类 prefilter/refine telemetry，方便判断快慢来自哪里。
- 验证入口：
  - `make check-two-stage-frontier-sweep`
  - `make check-summarize-two-stage-frontier`
- 当前结论：
  - 现在已经能在多个真实 anchor shard 上复用同一个 exact baseline，批量筛出“值得继续观察”的 two-stage 参数组合；
  - 但这仍然是 **实验性质量前沿**，不是默认主线语义。

## 2026-04-09（heavy micro-anchor threshold calibration）

- 这一轮把 two-stage 质量校准从“全局 sweep”进一步收敛到“重灾区 micro-anchor”：
  - 新增 `scripts/benchmark_two_stage_threshold_modes.py`，对比 `legacy`、`deferred_exact`、`deferred_exact_minimal_v2` 等共享输入下的阈值门控行为；
  - 新增 `scripts/benchmark_two_stage_threshold_heavy_microanchors.py`，对 coarse tiling 选出的重热点 tile 生成 `discovery_report.json`、`summary.json`、`summary.md`，并附带 `decision_flags`；
  - `README.md` / `Makefile` 同步加入 `benchmark-two-stage-threshold-modes`、`check-two-stage-threshold-modes`、`benchmark-two-stage-threshold-heavy-microanchors`、`check-two-stage-threshold-heavy-microanchors`。
- 这一轮后续还把 heavy micro-anchor discovery 缩到单 arm：
  - 目的不是改语义，而是把探索成本压到更小，同时把代表性问题集中到一条最值得分析的候选链路上。
- 输出侧现在不只看 “有没有 diff”，而是开始看：
  - `top5_retention`
  - `top10_retention`
  - `score_weighted_recall`
  - 以及 per-tile `decision_flags`
- 验证入口：
  - `make check-two-stage-threshold-modes`
  - `make check-two-stage-threshold-heavy-microanchors`
- 当前结论：
  - 现在可以先挑出最容易暴露 gate 问题的热点 tile，再决定是继续收紧门槛、放松门槛，还是进入更大范围 anchor sweep；
  - 这让 two-stage 校准从“看总体 diff”变成“先看最有信息量的局部失败样本”。

## 2026-04-10（`minimal_v2` safeguard / coverage attribution / panel automation）

- 这一轮第一次把 two-stage 校准推进到 **核心 gate 语义 + 归因自动化** 两个层面：
  - `exact_sim.h` / `longtarget.cpp` 新增 `minimal_v2` reject mode：
    - 在 deferred two-stage shortlist 中，允许每个 task 最多救回一个 `singleton_missing_margin` 候选；
    - 仍然要求它是该 task 里最强的 singleton-no-margin 候选，并满足预设的 best-seed override 门槛；
    - stderr benchmark 新增 `benchmark.two_stage_singleton_rescued_windows`、`benchmark.two_stage_singleton_rescued_tasks`、`benchmark.two_stage_singleton_rescue_bp_total`。
  - 新增 `tests/test_exact_sim_two_stage_threshold.cpp`，覆盖 `minimal_v1/minimal_v2` gate 行为、reject reason label 与 rescued counter，保证 singleton safeguard 不是只停留在脚本层。
- 这一轮也补齐了“质量前沿为什么掉点”的分析工具链：
  - `scripts/replay_two_stage_singleton_safeguard.py`：离线重放 singleton safeguard，验证不同 rescue 策略/override 的影响；
  - `scripts/analyze_two_stage_top_hit_autopsy.py`：针对 top hit 丢失做 autopsy；
  - `scripts/analyze_two_stage_coverage_attribution.py`：把 legacy strict hits 的缺失归因为 `inside_kept_window`、`inside_rejected_window`、`outside_kept_but_near_kept`、`far_outside_all_kept`；
  - `scripts/analyze_two_stage_coverage_attribution_panel.py`：从 heavy micro-anchor `summary.json` 里挑代表性 tile，自动重跑 candidate lane debug window，并汇总成 panel 级 `summary.json` / `summary.md`。
- `docs/plans/2026-04-10-panel-coverage-attribution.md` 记录了 panel automation 的实现计划；这一层的目标不是继续调 gate，而是回答：
  - 当前 `minimal_v2` 的 miss 是否仍然主要被 `inside_rejected_window` 主导；
  - 如果不是，后续优化应该落在 selective fallback、prefilter coverage，还是 gate 细调。
- 验证入口：
  - `make check-exact-sim-two-stage-threshold`
  - `bash ./scripts/check_two_stage_coverage_attribution.sh`
  - `bash ./scripts/check_two_stage_coverage_attribution_panel.sh`
- 当前结论：
  - two-stage lane 的观察维度已经从“更快多少”推进到“丢失到底发生在 gate 内、kept-window 附近，还是 prefilter 覆盖之外”；
  - 这让后续决策可以围绕证据做：该继续调 `minimal_v2`，还是该给某些代表性 miss 加 selective fallback。

## 2026-04-13（panel compare / decision report / non-empty ambiguity rescue）

- 这一轮把 two-stage lane 的定位继续收紧为 **candidate generator + targeted exact rescue**，不再把 `minimal_v2` 当成 final-output 近似路径：
  - `exact_sim.h` / `longtarget.cpp` 把 `LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK=1` 从“空 task 兜底”扩展到“稀疏 non-empty task 的 ambiguity-triggered rescue”；
  - 新增 `LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_MAX_KEPT_WINDOWS`、`LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_SCORE_GAP` 两个运行时阈值；
  - stderr benchmark 新增 `benchmark.two_stage_selective_fallback_non_empty_triggered_tasks`，用于区分空 task rescue 与 non-empty rescue 是否真正命中。
- 这一轮也补齐了 panel 决策链缺的最后一段：
  - 新增 `scripts/compare_two_stage_panel_summaries.py`，在同一组 selected heavy micro-anchor tile 上直接对比 `minimal_v2` baseline 与 candidate lane；
  - 新增 `scripts/summarize_two_stage_panel_decision.py`，把 compare summary 和 coverage attribution summary 合成单一 decision report；
  - `exact_sim.h` / `longtarget.cpp` 为 non-empty selector 新增 **互斥 blocker telemetry**：`candidate_tasks`、`rejected_by_max_kept_windows`、`rejected_by_no_singleton_missing_margin`、`rejected_by_singleton_override`、`rejected_as_covered_by_kept`、`rejected_by_score_gap`；
  - `scripts/benchmark_two_stage_threshold_modes.py` 同步解析这些 selector counters，并新增 `--run-env LABEL:KEY=VALUE`，允许只对 candidate lane 注入窄范围 ablation 参数；
  - 新增 `scripts/rerun_two_stage_panel_with_candidate_env.py`，复用同一组 selected micro-anchor tile，重跑 `legacy + candidate` 并把候选 lane 的 env 覆盖显式落盘；
  - `scripts/summarize_two_stage_panel_decision.py` 现在还会产出 `selector_candidate_tasks`、`dominant_selector_blocker`、`recommended_selector_ablation`，把“下一步该放宽哪一条 selector 条件”写成机器可复用的决策层；
  - `README.md` / `Makefile` 同步加入对应入口与自检脚本，保证 compare / decision / rerun helper 不是一次性的临时分析。
- 真实 panel 结果已经在 `.tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor_fastlane_nonempty/` 落盘：
  - `compare_vs_minimal_v2/summary.json` 显示 12 个代表 tile 上：
    - `selective_fallback_triggered_tasks=0`
    - `selective_fallback_non_empty_triggered_tasks=0`
    - `selective_fallback_selected_windows=0`
    - `top5_retention` / `top10_retention` / `score_weighted_recall` / `threshold_skipped_after_gate` 的 `delta_mean` 全部为 `0.0`
    - 只有 `threshold_batched_seconds` 的 `delta_mean≈+2.7386s`
  - `coverage_attribution_panel/summary.json` 显示 residual miss 仍然主要落在 `inside_rejected_window`：
    - overall share `≈66.6%`
    - `top5_missing` share `70%`
    - `top10_missing` share `55%`
    - `score_weighted_missing` share `≈66.3%`
    - `outside_kept_but_near_kept` 仍然很低（overall `≈0.6%`，`top5/top10` 为 `0%`）
  - `panel_decision/summary.json` 因此给出的 `recommended_next_step` 仍是 `non_empty_ambiguity_triggered_selective_fallback`。
- 验证入口：
  - `make check-exact-sim-two-stage-threshold`
  - `make check-two-stage-threshold-modes`
  - `make check-two-stage-threshold-heavy-microanchors`
  - `make check-compare-two-stage-panel-summaries`
  - `make check-summarize-two-stage-panel-decision`
  - `make check-rerun-two-stage-panel-with-candidate-env`
  - `bash ./scripts/check_two_stage_coverage_attribution_panel.sh`
- 当前结论：
  - `minimal_v2` 现在已经明确是 shortlist / candidate-generator lane，而不是 final-output lane；
  - 第一版 non-empty ambiguity rescue 逻辑已经接入真实 runtime，但在当前代表 panel 上 **零触发、零质量增量**；
  - 这轮刻意 **不修改默认 selector 行为**，而是先补齐 blocker telemetry 和定向 rerun 工具；下一次默认变更仍应先看 `dominant_selector_blocker`，只放宽真正卡住触发的那一条 selector 条件；
  - 因为 residual miss 仍由 `inside_rejected_window` 主导，下一步应继续扩 non-empty selector，而不是先做 `REFINE_PAD_BP / REFINE_MERGE_GAP_BP` sweep。

## 2026-04-13（selector candidate-class attribution / offline replay）

- 在 `max_kept_windows` 单变量 rerun 之后，把“下一枪该怎么扩 non-empty selector”进一步从 blocker telemetry 收紧到了 **candidate class**：
  - `.tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor_fastlane_nonempty_rerun_baseline_selector_telemetry/panel_decision/summary.json` 里，`dominant_selector_blocker=max_kept_windows`，`selector_candidate_tasks=4151`，其中 `rejected_by_max_kept_windows=2811`、`rejected_by_no_singleton_missing_margin=1314`；
  - `.tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor_fastlane_nonempty_rerun_max_kept_windows_2/panel_decision/summary.json` 里，把 `LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_MAX_KEPT_WINDOWS` 从 `1` 放到 `2` 之后，`dominant_selector_blocker` 确实切到了 `no_singleton_missing_margin`，对应计数变成：
    - `rejected_by_max_kept_windows=1610`
    - `rejected_by_no_singleton_missing_margin=2444`
    - `rejected_by_singleton_override=75`
    - `rejected_by_score_gap=22`
  - 同时 quality delta 仍然是 `top5/top10/score_weighted_recall/threshold_skipped_after_gate = 0.0`，说明这一步完成了 blocker 迁移，但还没有带来 shortlist 质量增益。
- 为了不再盲调 runtime selector，这一轮新增了两个纯脚本侧工具，并已经在真实 panel 上落盘：
  - `scripts/analyze_two_stage_selector_candidate_classes.py`
    - 输入：固定 selected-tile 的 panel summary + debug TSV + 当前 selector 参数；
    - 输出：`selector_candidate_classes/summary.json|md`，把 `no_singleton_missing_margin` task 再拆成 `support1_margin_present`、`support2`、`support3plus_low_support_or_margin`、`score_lt_85`、`covered_by_kept`、`other`，并进一步给 `score_lt_85` 补 `80_84 / 75_79 / lt_75` 三档 band breakdown；
    - 真实 panel 结果在 `.tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor_fastlane_nonempty_rerun_max_kept_windows_2/selector_candidate_classes/summary.json`：
      - `recommended_next_candidate_class=score_lt_85`
      - `recommended_score_lt_85_band=75_79`
      - `task_count_by_class.score_lt_85=526`
      - `missing_hit_contribution_by_class.overall.count_by_class.score_lt_85=1626`
      - `score_weighted_missing.weight_by_class.score_lt_85≈2995.16`
      - `score_lt_85_band_breakdown.task_count_by_band = {80_84:0, 75_79:286, lt_75:240}`
      - `score_lt_85_band_breakdown.missing_hit_contribution_by_band.score_weighted_missing.weight_by_band = {80_84:0.0, 75_79:≈1731.33, lt_75:≈1263.83}`
    - 这说明在当前代表 panel 上，真正解释 residual missing-hit weight 的“下一层候选”并不是 `support1/support2`，而是 **当前 `singleton_override=85` 之下的 rejected windows**。
  - `scripts/replay_two_stage_non_empty_candidate_classes.py`
    - 输入：同一 panel summary + selector 参数；
    - 输出：`candidate_class_replay/summary.json|md`，既保留旧的 candidate-class replay，也新增 `score_band_80_84 / score_band_75_79 / score_band_lt_75 / score_band_dominant`；
    - 真实 panel 结果在 `.tmp/panel_minimal_v2_selective_fallback_2026-04-13_chr22_3anchor_fastlane_nonempty_rerun_max_kept_windows_2/candidate_class_replay/summary.json`：
      - `score_band_dominant` 解析到 `75_79`，且与 `score_band_75_79` 完全一致：
        - `predicted_rescued_task_count=286`
        - `predicted_rescued_window_count=286`
        - `predicted_top10_retention: 0.6 -> 0.7`
        - `predicted_score_weighted_recall: ≈0.5074 -> ≈0.5202`
        - `delta_refine_total_bp_total=77856`
      - `score_band_lt_75` 也能命中，但形态不同：
        - `predicted_rescued_task_count=410`
        - `predicted_top10_retention` 仍是 `0.6`
        - `predicted_score_weighted_recall: ≈0.5074 -> ≈0.5239`
        - `delta_refine_total_bp_total=98715`
      - 旧的窄 candidate-class replay（`support1/support2/strongest_low_support_or_margin`）保持不变，仍然是 `predicted_rescued_task_count=0`
    - 这说明当前真实 panel 上，**第一优先带不是 `80_84`，而是 `75_79`**；`lt_75` 更像一个“成本更高、只抬 weighted recall 的对照带”，不该先进入 runtime。
- 验证入口：
  - `make check-analyze-two-stage-selector-candidate-classes`
  - `make check-replay-two-stage-non-empty-candidate-classes`
- 当前结论：
  - `max_kept_windows=2` 已经回答了第一个问题：non-empty selector 不是完全没机会，而是 **入口 blocker 已从稀疏度条件转移到候选类型**；
  - 下一步不该回到 broad gate tuning，也不该先做 pad/merge，而应继续围绕 **candidate class 扩展**：
    - 首先应围绕 `score_lt_85` 的 `75_79` 这层做 very narrow runtime 原型，而不是直接放开整个 `<85`；
    - `lt_75` 暂时只保留为 offline 对照，因为它虽然还能抬 `score_weighted_recall`，但不会抬 `top10`，且成本更高；
  - 在拿到新的 offline replay 正增益之前，不应把这类 selector 扩展直接写进默认 runtime 行为。
- 这一轮已经把上述 runtime 原型落地成一个严格受限的 `minimal_v3`：
  - `exact_sim.h` 的 `ExactSimTwoStageSelectiveFallbackConfig` 新增 `LONGTARGET_TWO_STAGE_SELECTIVE_FALLBACK_NON_EMPTY_SCORE_BAND_75_79` 开关；
  - 在 `deferred_exact + minimal_v2 + selective_fallback` 的 non-empty path 上，若现有 `singleton_missing_margin` rescue 没有选中任何窗口，则允许再补救 **exactly one** 个未被 kept windows 覆盖的 `75-79` rejected window；
  - 这一步不改 `score_gap`、不改 `strong_score_override`、不包含 `<75`，也不碰 `REFINE_PAD_BP / REFINE_MERGE_GAP_BP`；
  - `scripts/benchmark_two_stage_threshold_modes.py` / `scripts/check_two_stage_threshold_modes.sh` 已新增对应 lane：`deferred_exact_minimal_v3_scoreband_75_79`，其唯一额外条件是 `NON_EMPTY_MAX_KEPT_WINDOWS=2` + `NON_EMPTY_SCORE_BAND_75_79=1`；
  - 目前已完成的验证只有实现级回归：`make check-exact-sim-two-stage-threshold`、`make check-two-stage-threshold-modes`。
- 因此当前最自然的下一步已经从“做 runtime 原型”收缩为“跑真实固定 selected-tiles panel rerun”：
  - 直接对比 `deferred_exact_minimal_v2_selective_fallback` vs `deferred_exact_minimal_v3_scoreband_75_79`；
  - 重点看 `selective_fallback_non_empty_triggered_tasks`、`top_hit_retention`、`top5/top10 retention`、`score_weighted_recall`、`threshold_skipped_after_gate`、`batch_retention`；
  - 只有在真实 panel 也出现净正增益时，才值得把这条 lane 继续扩到更广的评估面。
- 这轮真实固定 selected-tiles panel rerun 已经完成，结果落在：
  - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/summary.json`
  - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/compare_vs_current_fallback/summary.json`
  - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/panel_decision/summary.json`
  - 相对 `deferred_exact_minimal_v2_selective_fallback`（`max_kept_windows=2` rerun baseline），`minimal_v3` 的真实增量是：
    - `top_hit_retention: 1.0 -> 1.0`
    - `top5_retention: +0.016666666667`
    - `top10_retention: +0.033333333333`
    - `score_weighted_recall: +0.01849622676`
    - `threshold_skipped_after_gate: +0.0`
    - `threshold_batch_size_mean: +0.0`
    - `threshold_batched_seconds: -0.060024166667`
    - `refine_total_bp: +6873.416666666667`
    - `selective_fallback_non_empty_triggered_tasks=305`
  - 这证明了 `candidate generator + targeted exact rescue` 这条 runtime 方向已经真实成立；它不再只是 offline proxy。
- 在此基础上，这一轮又把“下一枪是否继续 score-band 下探”重新收回到 analysis-first：
  - `scripts/analyze_two_stage_selector_candidate_classes.py`
    - 仍保留原有 `score_lt_85_band_breakdown`（`80_84 / 75_79 / lt_75`）；
    - 新增 `score_lt_75_band_breakdown`（`70_74 / 65_69 / lt_65`）和 `recommended_score_lt_75_band`，用于在 `minimal_v3` 之后继续细分 residual `lt_75`。
  - `scripts/replay_two_stage_non_empty_candidate_classes.py`
    - 保留旧策略不变；
    - 新增 `score_band_lt_75_dominant / score_band_70_74 / score_band_65_69 / score_band_lt_65`，让 residual `lt_75` 可以继续做 fixed-tile offline replay。
  - 对 `minimal_v3` 的真实 panel 跑完新分析后，结果落在：
    - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/selector_candidate_classes_lt75_breakdown/summary.json`
    - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/candidate_class_replay_lt75_breakdown/summary.json`
  - 当前 residual 结论已经进一步收紧：
    - `recommended_next_candidate_class=score_lt_85`
    - `recommended_score_lt_85_band=lt_75`
    - `recommended_score_lt_75_band=70_74`
    - `score_lt_75_band_breakdown.task_count_by_band = {70_74:192, 65_69:79, lt_65:49}`
    - `score_lt_75_band_breakdown.missing_hit_contribution_by_band.score_weighted_missing.weight_by_band ≈ {70_74:972.06, 65_69:412.88, lt_65:215.22}`
    - `score_lt_75_band_breakdown.missing_hit_contribution_by_band.top10_missing.count_by_band = {70_74:2, 65_69:0, lt_65:0}`
  - 但新的 offline replay 同时回答了更关键的问题：**继续沿 score-band 下探已经不再改善 shortlist quality 的 `top5/top10`**
    - `score_band_lt_75_dominant` 解析到 `70_74`，且与 `score_band_70_74` 完全一致：
      - `predicted_rescued_task_count=225`
      - `delta_top5_retention=0.0`
      - `delta_top10_retention=0.0`
      - `delta_score_weighted_recall≈+0.00710`
      - `delta_refine_total_bp_total=56532`
    - `score_band_65_69`：
      - `predicted_rescued_task_count=173`
      - `delta_top10_retention=0.0`
      - `delta_score_weighted_recall≈+0.00572`
    - `score_band_lt_65`：
      - `predicted_rescued_task_count=119`
      - `delta_top10_retention=0.0`
      - `delta_score_weighted_recall≈+0.00498`
  - 这意味着在 **Top10-first** 目标下，下一步不该直接做 `minimal_v4 score-band`；`70_74` 虽然仍是 residual 上最值钱的低分带，但它已经只抬 weighted recall，不再抬 `top10`。
- 因此当前 two-stage 线的下一步又收紧了一层：
  - 不回到 broad gate tuning；
  - 不做 pad/merge sweep；
  - 也不直接上 `minimal_v4 score-band_70_74`；
  - 应该转向 **非 score-band 的 rescue object 扩展**（例如更 task-local / rule-strand-aware 的 rescue object），但仍要先用 offline replay 证明它能继续改善 `top5/top10`，再决定是否进入 runtime。
- 按上述收束，这一轮先把 **analysis-first / offline-first 的 rule-strand object tooling** 落地，而不碰 runtime：
  - `scripts/analyze_two_stage_selector_candidate_classes.py`
    - 保留原有 class / score-band summary 不变；
    - 新增 `aggregate.rule_strand_object_breakdown` 与 `per_tile[*].rule_strand_object_breakdown`，把 `no_singleton_missing_margin` task 里的 `uncovered_rejected_rows` 按 `(rule, strand)` 分组，并统计这些 object 对 residual `overall / top5 / top10 / score_weighted` miss 的解释度；
    - 新增 `recommended_next_candidate_object`，当前只在 `rule_strand_object_breakdown` 真的解释到 residual miss 时返回 `rule_strand_dominant`。
  - `scripts/replay_two_stage_non_empty_candidate_classes.py`
    - 保留默认 score-band replay 不变；
    - 新增 `rule_strand_strongest`：每个 `no_singleton_missing_margin` task 最多救 1 个最强 `(rule, strand)` object；
    - 新增 `rule_strand_dominant`：offline-only upper bound，优先选 attributed `top10_missing` 最大的 object，再看 `score_weighted_missing`、`overall_missing` 与代表窗口强度；
    - 每条新策略都会在 `summary.json|md` 里写出 `resolved_candidate_object`。
  - `scripts/check_analyze_two_stage_selector_candidate_classes.sh`
    - 新增 fixture，验证同一 task 内两个不同 `(rule, strand)` object 会被正确计数，并把 `recommended_next_candidate_object` 收敛到 `rule_strand_dominant`。
  - `scripts/check_replay_two_stage_non_empty_candidate_classes.sh`
    - 新增 fixture，强制 `rule_strand_strongest` 与 `rule_strand_dominant` 选中不同 object，确保 replay 真的按 object attribution 做决策，而不是退化成 strongest-window。
  - 这一步的意义不是宣布下一条 runtime lane，而是把下一轮 real-panel 判断条件锁死：
  - 如果 `rule_strand_strongest` 在 `minimal_v3` panel 上也能继续改善 `top5/top10`，才值得规划新的 runtime prototype；
  - 如果只有 `rule_strand_dominant` 有增益，它仍然只是 attribution / proxy 证据，不应直接翻译成 runtime selector；
  - 如果两者都不能改善 `top5/top10`，则应停止继续扩 selector，并把 `minimal_v3` 固定为当前 experimental shortlist baseline。
- 在此之后，又按更窄的 stop-rule 再做了一轮 **task-local rejected-window proxy replay**，仍然不碰 runtime：
  - `scripts/replay_two_stage_non_empty_candidate_classes.py`
    - 新增 `task_proxy_score_x_bp`：在每个 `no_singleton_missing_margin` task 内，选 `best_seed_score * window_bp` 最大的未覆盖 rejected window；
    - 新增 `task_proxy_score_x_support`：在每个 `no_singleton_missing_margin` task 内，选 `best_seed_score * support_count` 最大的未覆盖 rejected window；
    - 两条策略都沿用现有 fixed selected-tiles panel、每 task 最多 rescue 1 个窗口、`max_kept_windows=2` 的 offline replay 口径。
  - `scripts/check_replay_two_stage_non_empty_candidate_classes.sh`
    - 新增 fixture，强制 `score×bp` 与 `score×support` 选中不同窗口，验证两条 proxy strategy 真的按不同 proxy 排序，而不是退化成 strongest-window。
  - 真实 panel 结果落在：
    - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/candidate_object_replay_task_proxy/summary.json`
  - 结果继续收紧了 stop-signal：
    - `task_proxy_score_x_bp`：
      - `predicted_rescued_task_count=382`
      - `delta_top5_retention=0.0`
      - `delta_top10_retention=0.0`
      - `delta_score_weighted_recall≈+0.01726`
      - `delta_refine_total_bp_total=101350`
    - `task_proxy_score_x_support`：
      - `predicted_rescued_task_count=382`
      - `delta_top5_retention=0.0`
      - `delta_top10_retention=0.0`
      - `delta_score_weighted_recall≈+0.01657`
      - `delta_refine_total_bp_total=97926`
  - 这说明当前 `minimal_v3` residual 上，哪怕不再换 score-band、不再换分桶方式，而是直接改同一 task 内的 proxy 选窗，也依然只能抬 weighted recall，抬不动 `top5/top10`。
  - 因此 two-stage selector 的 stop-rule 现在已经非常明确：
    - 不继续扩 selector；
    - 不规划 `minimal_v4`；
    - 把 `minimal_v3` 固定为当前 experimental shortlist baseline；
    - 后续优化重心应转向更强的 exact rescue / exact-safe 主线，而不是继续在 two-stage selector 上挤 proxy。

## 2026-04-14（task-level ambiguity rerun upper bound）

- 在 selector / proxy 这条线确认“继续扩窗口对象也抬不动 `top5/top10`”之后，这一轮把 two-stage 的下一枪正式转成 **task-level exact rerun upper bound**，仍然坚持 analysis-first / offline-first，不改 runtime：
  - 固定 baseline 继续使用：
    - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/summary.json`
  - 复用同一批 fixed selected tiles，补跑 `deferred_exact` rescue source：
    - `.tmp/panel_deferred_exact_2026-04-14_chr22_3anchor_task_level_rerun/summary.json`
- 新增 `scripts/analyze_two_stage_task_ambiguity.py`
  - 输入：baseline `minimal_v3` panel summary + fixed-tile `deferred_exact` rescue panel summary；
  - 输出：`task_level_ambiguity_deferred_exact/summary.json|md`，给每个 task 同时写出：
    - baseline ambiguity 指标：`inside_rejected_window` 的 `overall / top5 / top10` missing-hit 计数与 `score_weighted` 质量权重；
    - rescue-gain 指标：如果把该 task 用 `deferred_exact` rerun 替换，能额外覆盖多少 baseline-missing legacy hits，以及代价是多少 `added_window_count / added_bp_total`。
  - 根因修正：
    - 真实 panel 证明，单靠 `(fragment_index, fragment_start/end_in_seq, reverse_mode, parallel_mode)` 不能唯一标识 task；
    - 实际上同一 fragment 会按 `strand + rule` 再拆成不同 task；
    - 因此脚本最终使用 `(fragment_index, fragment_start/end_in_seq, reverse_mode, parallel_mode, strand, rule)` 作为 stable task key，避免 real-panel join 冲突。
  - 真实 panel aggregate：
    - `eligible_task_count=4151`
    - `rescue_gain_task_count=355`
    - `false_positive_ambiguity_task_count=0`
  - 说明：
    - ambiguity signal 和 real rescue gain 在 real panel 上是对得上的；不是“高 ambiguity task 大多救不回来”，而是候选 task 很多，但真正有 gain 的只有其中一小部分。
- 新增 `scripts/replay_two_stage_task_level_rerun.py`
  - 输入：上一步的 `task_level_ambiguity_deferred_exact/summary.json`；
  - 做法：按 `oracle_rescue_gain` 对 task 全局排序，然后只在离线 coverage-proxy 上回放 rerun budgets `8 / 16 / 32 / 64`；
  - 输出：
    - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_rerun_replay_deferred_exact/summary.json`
  - 真实 budget frontier：
    - budget `8`
      - `top_hit_retention=1.0`
      - `top5_retention=0.6`（不变）
      - `top10_retention=0.8`（相对 baseline `+0.1`）
      - `delta_score_weighted_recall≈+0.00264`
      - `delta_refine_total_bp_total=+3735`
    - budget `16`
      - `top_hit_retention=1.0`
      - `top5_retention=0.6`（不变）
      - `top10_retention=0.8`（相对 baseline `+0.1`）
      - `delta_score_weighted_recall≈+0.00837`
      - `delta_refine_total_bp_total=+8097`
    - budget `32`
      - `top_hit_retention=1.0`
      - `top5_retention=0.6`（不变）
      - `top10_retention=0.8`（相对 baseline `+0.1`）
      - `delta_score_weighted_recall≈+0.01583`
      - `delta_refine_total_bp_total=+19915`
    - budget `64`
      - `top_hit_retention=1.0`
      - `top5_retention=0.6`（不变）
      - `top10_retention=0.8`（相对 baseline `+0.1`）
      - `delta_score_weighted_recall≈+0.02577`
      - `delta_refine_total_bp_total=+38185`
  - 这给出一个新的、比 selector 扩展更强的结论：
    - `minimal_v3` 之后，继续扩 selector 已经不值得；
    - 但 task-level exact rerun 的 offline upper bound **第一次重新抬动了 `top10`**；
    - 同时，这个增益在 budget `8` 时就已经达到 `+0.1`，之后主要只是在堆 `score_weighted_recall`，并没有继续抬 `top5` 或再推高 `top10`。
- 因此 two-stage 的下一步方向也被重新收紧：
  - 不回 broad selector tuning；
  - 不做 `pad/merge sweep`；
  - 不直接规划新的 runtime lane；
  - 下一枪应该转向 **deployable task-level ambiguity trigger** 的离线 trigger-design / calibration，目标是尽量逼近 budget-8/16 的 `top10` frontier，而不是继续在 window-level selector 上挤增量。
- 基于这条 offline frontier，这一轮又把 **oracle-guided task-level exact rerun** 落成了一个严格受限的 runtime prototype：
  - `exact_sim.h`
    - 新增 `ExactSimTwoStageTaskRerunConfig` / `ExactSimTwoStageTaskRerunStats`；
    - 新增运行时开关：
      - `LONGTARGET_TWO_STAGE_TASK_RERUN=1`
      - `LONGTARGET_TWO_STAGE_TASK_RERUN_BUDGET`
      - `LONGTARGET_TWO_STAGE_TASK_RERUN_SELECTED_TASKS_PATH`
    - `ExactSimDeferredTwoStagePrefilterResult` 现在同时保留：
      - baseline 执行窗口 `windows`（gate / selective fallback 之后）
      - `windowsBeforeGateList`（用于被选中的 task 做 stronger exact rerun）
    - 新增 `exact_sim_apply_two_stage_task_rerun_in_place()`：
      - 只在 task 被外部选中时触发；
      - 把该 task 的 exact 执行窗口从 baseline `after_gate` 升级成已缓存的 `before_gate` 窗口；
      - 同时精确回填 `addedWindowCount / addedBpTotal`。
  - `longtarget.cpp`
    - 新增 task-level rerun telemetry：
      - `benchmark.two_stage_task_rerun_enabled`
      - `benchmark.two_stage_task_rerun_budget`
      - `benchmark.two_stage_task_rerun_selected_tasks`
      - `benchmark.two_stage_task_rerun_effective_tasks`
      - `benchmark.two_stage_task_rerun_added_windows`
      - `benchmark.two_stage_task_rerun_refine_bp_total`
      - `benchmark.two_stage_task_rerun_seconds`
      - `benchmark.two_stage_task_rerun_selected_tasks_path`
    - runtime 读取 `LONGTARGET_TWO_STAGE_TASK_RERUN_SELECTED_TASKS_PATH` 指向的 TSV，并按完整 task key 精确匹配：
      - `(fragment_index, fragment_start_in_seq, fragment_end_in_seq, reverse_mode, parallel_mode, strand, rule)`
    - 这保持了前一轮 real-panel root cause 修正：**不能再退回 fragment-only join**。
  - `scripts/benchmark_two_stage_threshold_modes.py`
    - 新增两条 runtime lane：
      - `deferred_exact_minimal_v3_task_rerun_budget8`
      - `deferred_exact_minimal_v3_task_rerun_budget16`
    - 它们都以 `deferred_exact_minimal_v3_scoreband_75_79` 为 shortlist baseline，只额外打开 task-rerun runtime 开关。
  - `scripts/check_two_stage_task_rerun_runtime.sh`
    - 覆盖 selected-task TSV ingestion、task-rerun telemetry，以及 **strand-sensitive** task key 匹配；
    - 通过一个故意写错 `strand` 的 selected-task 文件，验证 runtime 不会把错误 task 误升级成 rerun。
  - `scripts/rerun_two_stage_panel_task_rerun_runtime.py`
    - 把 fixed-panel offline replay summary 里的 `selected_tasks` 按 tile 写成 TSV；
    - 复用同一批 selected micro-anchors，逐 tile 注入：
      - `deferred_exact_minimal_v3_task_rerun_budget8`
      - `deferred_exact_minimal_v3_task_rerun_budget16`
    - 这样 runtime-vs-offline 对拍就只剩一个变量：**runtime 是否忠实复现离线已选 task 的 rerun 行为**，而不是混进新的 selector / trigger 变化。
- 测试 / 接线：
  - 新增 `scripts/check_analyze_two_stage_task_ambiguity.sh`
    - 覆盖 real-panel root cause：同一 fragment、不同 `strand/rule` 的 task join 不再冲突；
    - 同时验证 ambiguity attribution、rescue gain 归因与 zero-gain task 列表。
  - 新增 `scripts/check_replay_two_stage_task_level_rerun.sh`
    - 覆盖 budget 排序、selected-task union 与 `delta_refine_total_bp_total` 统计。
  - 新增 `scripts/check_two_stage_task_rerun_runtime.sh`
    - 覆盖 runtime lane、selected-task TSV、task-rerun telemetry 和 `strand` 维度的 key 校验。
  - `Makefile`
    - 新增：
      - `check-analyze-two-stage-task-ambiguity`
      - `check-replay-two-stage-task-level-rerun`
      - `check-two-stage-task-rerun-runtime`

## 2026-04-15（task-rerun runtime real-panel confirmation）

- 在 `minimal_v3 + task-level rerun` runtime prototype 落地后，这一轮把 fixed selected tiles 的 **真实 runtime panel** 跑完，并补了一次 helper 输入路径的 root-cause 修正：
  - 初始 helper 曾把 per-tile `selected_tasks.tsv` 写进 `tiles/...` 的 benchmark `work-dir`；
  - 但 `scripts/benchmark_two_stage_threshold_modes.py` 启动时会先清空该 `work-dir`，导致 candidate lane 报：
    - `failed to load LONGTARGET_TWO_STAGE_TASK_RERUN_SELECTED_TASKS_PATH=...: failed to open selected task list`
  - 修正后，helper 改为把 TSV 写到：
    - `.tmp/.../task_rerun_selected_tasks/*.tsv`
    - 即每个 tile `work-dir` 之外，这样 runtime rerun 才能稳定读到外部选定的 task 列表。
- 真实 runtime panel 产物：
  - budget `8`
    - `.tmp/panel_minimal_v3_task_rerun_budget8_runtime_2026-04-14/summary.json`
    - `.tmp/panel_minimal_v3_task_rerun_budget8_runtime_2026-04-14/compare_vs_minimal_v3/summary.json`
  - budget `16`
    - `.tmp/panel_minimal_v3_task_rerun_budget16_runtime_2026-04-14/summary.json`
    - `.tmp/panel_minimal_v3_task_rerun_budget16_runtime_2026-04-14/compare_vs_minimal_v3/summary.json`
- 真实 runtime 结果：
  - budget `8`
    - `selected_tasks=8`
    - `effective_tasks=8`
    - `added_windows=14`
    - `added_bp=3735`
    - `task_rerun_seconds≈3.31`
    - 相对 `minimal_v3` 的 tile-mean 增量：
      - `top_hit_retention=+0.0`
      - `top5_retention≈+0.0833`
      - `top10_retention≈+0.0583`
      - `score_weighted_recall≈+0.00317`
      - `threshold_skipped_after_gate=+0.0`
      - `threshold_batch_size_mean=+0.0`
      - `threshold_batched_seconds≈+0.0574`
      - `refine_total_bp≈+311.25`
  - budget `16`
    - `selected_tasks=16`
    - `effective_tasks=16`
    - `added_windows=33`
    - `added_bp=8097`
    - `task_rerun_seconds≈8.23`
    - 相对 `minimal_v3` 的 tile-mean 增量：
      - `top_hit_retention=+0.0`
      - `top5_retention≈+0.0833`
      - `top10_retention≈+0.0667`
      - `score_weighted_recall≈+0.00760`
      - `threshold_skipped_after_gate=+0.0`
      - `threshold_batch_size_mean=+0.0`
      - `threshold_batched_seconds≈+0.0406`
      - `refine_total_bp≈+674.75`
- runtime-vs-offline fidelity 结论：
  - 两个 budget 的 runtime totals 都与 offline replay aggregate **精确对齐**：
    - budget `8`：`rerun_task_count=8`、`rerun_added_window_count=14`、`delta_refine_total_bp_total=3735`
    - budget `16`：`rerun_task_count=16`、`rerun_added_window_count=33`、`delta_refine_total_bp_total=8097`
  - 注意：`compare_two_stage_panel_summaries.py` 给的是 **tile-mean** 视角，而 `replay_two_stage_task_level_rerun.py` 的 summary 是 **panel-global aggregate**；两者的 `top5/top10/score_weighted_recall` 不应逐项硬对齐。
  - 因此最硬的 fidelity 证据是：
    - runtime 选中的 task 数、added windows、added bp 总量与 offline 完全一致；
    - 质量方向上，`top_hit` 保持稳定，`top10` 与 `score_weighted_recall` 在真实 runtime panel 上继续为正增量；
    - `threshold_skipped_after_gate` 与 `threshold_batch_size_mean` 没被吃回，说明这条 lane 仍保留 two-stage 的 skip/batch 形态。
- 这把 two-stage 的当前定位进一步收紧成：
  - `deferred_exact_minimal_v3_scoreband_75_79`：当前 experimental shortlist baseline；
  - `deferred_exact_minimal_v3_task_rerun_budget16`：当前 experimental runtime baseline；
  - `deferred_exact_minimal_v3_task_rerun_budget8`：更便宜的控制组 / 对照 lane。
- 下一步方向：
  - 不回 broad selector tuning；
  - 不做 `pad/merge sweep`；
  - 不再继续扩 window-level selector family；
  - 应转向 **deployable task-level ambiguity trigger** 的 trigger-design / calibration，目标是在不依赖 oracle-selected task TSV 的前提下，尽量逼近 budget `8/16` 的 frontier。

## 2026-04-15（oracle-free task trigger calibration v1）

- 按上一轮结论，这一轮不再继续扩 selector，也不先改 runtime，而是把 **oracle-free task-level ambiguity trigger calibration** 落到现有 analysis/replay 链路上：
  - `scripts/analyze_two_stage_task_ambiguity.py`
    - 保留原有 oracle 字段：
      - `baseline_inside_rejected_missing_count_*`
      - `baseline_inside_rejected_missing_weight`
      - `rescue_*`
    - 同时为每个 task 新增 `deployable_features`，且这些特征 **只能** 来自 baseline `minimal_v3` debug TSV / report telemetry：
      - `kept_window_count`
      - `uncovered_rejected_window_count`
      - `uncovered_rejected_bp_total`
      - `max_uncovered_rejected_window_bp`
      - `best_kept_score`
      - `best_rejected_score`
      - `best_score_gap`
      - `rejected_score_sum`
      - `rejected_score_mean`
      - `rejected_score_top3_sum`
      - `rejected_score_x_bp_sum`
      - `rejected_score_x_support_sum`
      - `score_band_counts` / `score_band_bp_totals`
        - `ge85 / 80_84 / 75_79 / 70_74 / lt70`
      - `support_bin_counts`
        - `support1 / support2 / support3plus`
      - `reject_reason_counts`
      - `reject_reason_bp_totals`
      - `rule_diversity_count`
      - `strand_diversity_count`
      - `rule_strand_object_count`
      - `rule_strand_entropy`
      - `tile_rank_by_best_rejected_score`
      - `tile_rank_by_rejected_score_x_bp_sum`
      - `selective_fallback_selected_window_count`
    - 这样 oracle-selected task TSV 现在可以被当成监督标签，而不是部署时输入。
  - `scripts/search_two_stage_task_trigger_rankings.py`
    - 在固定 panel 的 task-level ambiguity summary 上做 calibrated ranking search；
    - 候选库固定为：
      - rule-based：
        - `rule_score_mass_gap_v2`
        - `rule_support_reason_pressure_v2`
      - leave-anchor-out learned ranking：
        - `lr_budget16_rank_v1`
        - `hgb_budget16_rank_v1`
    - 输出继续沿用 replay 口径：
      - `delta_top_hit_retention`
      - `delta_top10_retention`
      - `delta_score_weighted_recall`
      - `delta_refine_total_bp_total`
      - `oracle_overlap`
    - 只有真的过 gate，`recommended_candidate` 才非空，并允许进入 runtime confirm。
  - `scripts/replay_two_stage_task_level_rerun.py`
    - 不再只保留 `rescue_gain > 0` 的 task；为了评估 false-positive trigger，replay 候选池扩成全部 eligible tasks。
    - 新增 `--ranking`：
      - `oracle_rescue_gain`
      - `deployable_sparse_gap_v1`
      - `deployable_support_pressure_v1`
    - 每个 budget 新增 `oracle_overlap`：
      - `oracle_selected_task_count`
      - `candidate_selected_task_count`
      - `overlap_task_count`
      - `precision`
      - `recall`
      - `jaccard`
    - 这样 replay summary 既能继续给 runtime helper 提供 `selected_tasks`，又能直接回答“oracle-free trigger 距离 oracle frontier 还有多远”。
- 测试 / 契约：
  - `scripts/check_analyze_two_stage_task_ambiguity.sh`
    - 新增 richer `deployable_features` 的 schema、聚合值与 tile-rank 断言。
  - `scripts/check_replay_two_stage_task_level_rerun.sh`
    - 新增两条 heuristic ranking 的 fixture 校验；
    - 同时验证 `oracle_overlap` 的 `precision / recall / jaccard`。
  - `scripts/check_search_two_stage_task_trigger_rankings.sh`
    - 覆盖 rule-based / learned candidates、leave-anchor-out training 摘要与 promotion gate 输出。
  - helper 兼容性仍保持通过：
    - `make check-rerun-two-stage-panel-task-rerun-runtime`
- 真实 offline calibration：
  - 分析产物：
    - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_ambiguity_deferred_exact_deployable/summary.json`
  - replay 产物：
    - oracle：
      - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_rerun_replay_deferred_exact_oracle/summary.json`
    - heuristic：
      - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_rerun_replay_deferred_exact_deployable_sparse_gap_v1/summary.json`
      - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_rerun_replay_deferred_exact_deployable_support_pressure_v1/summary.json`
  - 对比结果：
    - oracle budget `16`
      - `delta_top10_retention=+0.1`
      - `delta_score_weighted_recall≈+0.00837`
      - `delta_refine_total_bp_total=+8097`
    - `deployable_sparse_gap_v1`
      - budget `8`
        - `delta_top10_retention=0`
        - `delta_score_weighted_recall≈+0.00095`
        - `delta_refine_total_bp_total=+7189`
        - `oracle_overlap_jaccard=0.0`
      - budget `16`
        - `delta_top10_retention=0`
        - `delta_score_weighted_recall≈+0.00142`
        - `delta_refine_total_bp_total=+12093`
        - `oracle_overlap_precision=0.0625`
        - `oracle_overlap_recall=0.0625`
        - `oracle_overlap_jaccard≈0.0323`
    - `deployable_support_pressure_v1`
      - budget `8`
        - `delta_top10_retention=0`
        - `delta_score_weighted_recall≈+0.00156`
        - `delta_refine_total_bp_total=+9382`
        - `oracle_overlap_jaccard=0.0`
      - budget `16`
        - `delta_top10_retention=0`
        - `delta_score_weighted_recall≈+0.00273`
        - `delta_refine_total_bp_total=+20015`
        - `oracle_overlap_precision=0.0625`
        - `oracle_overlap_recall=0.0625`
        - `oracle_overlap_jaccard≈0.0323`
- calibrated trigger search v1：
  - 新分析产物：
    - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_level_ambiguity_deferred_exact_deployable_v2/summary.json`
  - 新 search 产物：
    - `.tmp/panel_minimal_v3_scoreband_75_79_2026-04-14_chr22_3anchor_fastlane_nonempty_rerun/task_trigger_ranking_search_v1/summary.json`
  - 目标 gate（budget `16`）：
    - `delta_top_hit_retention == 0.0`
    - `delta_top10_retention >= 0.08`
    - `delta_score_weighted_recall >= 0.006`
    - `delta_refine_total_bp_total <= 10121.25`
  - oracle 参考仍然不变：
    - `delta_top10_retention=+0.1`
    - `delta_score_weighted_recall≈+0.00837`
    - `delta_refine_total_bp_total=+8097`
  - candidate 结果：
    - `rule_score_mass_gap_v2`
      - budget `8`
        - `delta_top10_retention=0`
        - `delta_score_weighted_recall≈+0.00053`
        - `delta_refine_total_bp_total=+5567`
        - `oracle_overlap_jaccard≈0.0667`
      - budget `16`
        - `delta_top10_retention=0`
        - `delta_score_weighted_recall≈+0.00224`
        - `delta_refine_total_bp_total=+11242`
        - `oracle_overlap_jaccard≈0.0667`
    - `rule_support_reason_pressure_v2`
      - budget `8`
        - `delta_top10_retention=0`
        - `delta_score_weighted_recall≈+0.00096`
        - `delta_refine_total_bp_total=+10802`
        - `oracle_overlap_jaccard=0.0`
      - budget `16`
        - `delta_top10_retention=0`
        - `delta_score_weighted_recall≈+0.00224`
        - `delta_refine_total_bp_total=+20689`
        - `oracle_overlap_jaccard≈0.0323`
    - `hgb_budget16_rank_v1`
      - budget `8`
        - `delta_top10_retention=0`
        - `delta_score_weighted_recall≈+0.00144`
        - `delta_refine_total_bp_total=+3301`
        - `oracle_overlap_jaccard=0.0`
      - budget `16`
        - `delta_top10_retention=0`
        - `delta_score_weighted_recall≈+0.00169`
        - `delta_refine_total_bp_total=+6956`
        - `oracle_overlap_jaccard≈0.0323`
    - `lr_budget16_rank_v1`
      - budget `8`
        - `delta_top10_retention=0`
        - `delta_score_weighted_recall≈+0.00026`
        - `delta_refine_total_bp_total=+7932`
        - `oracle_overlap_jaccard=0.0`
      - budget `16`
        - `delta_top10_retention=0`
        - `delta_score_weighted_recall≈+0.00106`
        - `delta_refine_total_bp_total=+14153`
        - `oracle_overlap_jaccard=0.0`
  - 结论：
    - 没有一个 deployable trigger candidate 把 `top10` 从 `minimal_v3` baseline 拉起来；
    - `best_candidate=rule_support_reason_pressure_v2` 只是当前 offline 排序下的“最不差”者，但仍然不过 gate；
    - `recommended_candidate=null`，因此不做 runtime confirm。
- 结论：
  - 第一版 naive deployable heuristics **没有**逼近 oracle `budget16` frontier；
  - 它们不仅没抬动 `top10`，而且 overlap 极低、added bp 反而更大；
  - calibrated ranking search v1 也没有把 deployable trigger 拉到可部署水平；
  - 因此这一步仍然不做 runtime confirm，也不新增 runtime lane。
- 下一步方向进一步收紧成：
  - 继续冻结：
    - `deferred_exact_minimal_v3_scoreband_75_79` 作为 experimental shortlist baseline；
    - `deferred_exact_minimal_v3_task_rerun_budget16` 作为 oracle runtime / offline upper bound；
  - 这里先触发 stop-rule：
    - 不再继续发明新的 oracle-free trigger 名字；
    - 不把当前 calibrated ranking search 推进成 runtime lane；
  - 后续主火力应转向更强的 exact rescue 设计，或独立的 exact-safe 主线，而不是继续磨 two-stage deployable trigger。

## 常用命令

## CUDA（GPU）阈值加速：`calc_score_with_workspace()`

现状：

- 已新增 **可选 CUDA 后端**，仅加速 exact threshold 的 `calc_score_with_workspace()` 中的 **shuffle Smith-Waterman 评分**（1002 次 shuffle/target）。
- 默认情况下，`mle_cen()`（MLE + 阈值公式）与 exact `SIM()` 仍保持 CPU 路径以确保结果 **byte-identical**；但也提供了可选的 SIM CUDA 路径（见下文），用于吞吐/实验加速，可能非 byte-identical。

使用方式：

- 运行时开关：
  - 启用 CUDA：`LONGTARGET_ENABLE_CUDA=1`
  - 选择 GPU：`LONGTARGET_CUDA_DEVICE=0`（默认 0）
  - 对拍（慢）：`LONGTARGET_CUDA_VALIDATE=1`（逐 task 用 CPU 再算一次阈值，不一致直接 `abort()`）
- benchmark 输出新增字段：
  - `benchmark.calc_score_backend={cpu|cuda|mixed}`

构建与回归：

- 构建：
  - `make build-cuda`
  - `make build-cuda-avx2`
- 精确性检查（CUDA 开启）：
  - `make check-smoke-cuda`
  - `make check-sample-cuda`
  - `make check-matrix-cuda`
  - `make check-smoke-cuda-avx2`
  - `make check-matrix-cuda-avx2`

限制与回退：

- `queryLength > 8192`、`targetLength > 8192` 或 `targetLength > 65535` 会自动回退到 CPU（`benchmark.calc_score_backend` 可能显示为 `mixed`）。

## CUDA（GPU）SIM 加速（可选；默认关闭）

现状：

- 支持将 SIM 的多个阶段切到 CUDA（面向“全基因组/海量 region 批量预测”的吞吐优化）。这些路径默认关闭，且在部分 case 下可能 **非 byte-identical**。
- candidate materialization 的 global-affine traceback 提供两种策略：
  - strict：检测到 DP ties 时回退 CPU（更稳定）
  - fast：不回退（更快但允许少量差异）

运行时开关（见 `README.md`）：

- `LONGTARGET_ENABLE_SIM_CUDA=1`：SIM initial scan（候选枚举）走 CUDA
- `LONGTARGET_ENABLE_SIM_CUDA_REGION=1`：SIM traceback update rescan（exact/hybrid）走 CUDA
- `LONGTARGET_ENABLE_SIM_CUDA_TRACEBACK=1`：SIM candidate materialization 的 global-affine traceback 走 CUDA（可能非 byte-identical）
- `LONGTARGET_SIM_CUDA_TRACEBACK_FALLBACK_ON_TIE=1`：strict（默认 1）；设为 0 为 fast

实现要点（traceback CUDA 内存优化）：

- forward DP 不再写回整张 `H/D/E/state` 矩阵；改为每个 cell 写 1 byte `dir`（含状态 + tie bits），并用 per-tile 边界数组 `bottomH/bottomD/rightH/rightE` 传递跨 tile 依赖。
- 目标：显著降低显存占用与全局内存带宽，避免大尺寸 `(rl+1)*(cl+1)` 时 `H/D/E` 写回成为瓶颈。

样例（`testDNA.fa` vs `H19.fa`，rule=0，2026-03-29）：

- 全 CPU（不开任何 CUDA）：`benchmark.total_seconds≈115.3s`
- 全 CUDA（scan+region+score），CPU traceback：`benchmark.total_seconds≈36.46s`
- 全 CUDA（scan+region+score+traceback），fast（fallback=0）：`benchmark.total_seconds≈36.66s`
- 全 CUDA（scan+region+score+traceback），strict（fallback=1）：`benchmark.total_seconds≈37.34s`（traceback backend=mixed）
- fast vs oracle：差异只出现在 `MeanStability` 一列（21/75 行不同）；`Score` 与 `MeanIdentity(%)` 不变。

### 构建

- `make build`
- `make build-avx2`
- `make build-openmp`

### 精确性检查

- `make check-smoke`
- `make check-sample`
- `make check-sample-row`
- `make check-smoke-avx2`
- `make check-sample-avx2`
- `make check-matrix`

### 基准

- `make benchmark-smoke`
- `make benchmark-sample`
- `TARGET=$PWD/longtarget_avx2 make benchmark-smoke`
- `TARGET=$PWD/longtarget_avx2 make benchmark-sample`
- `LONGTARGET_FORCE_AVX2=1 TARGET=$PWD/longtarget_avx2 make benchmark-smoke`

## 备注

- 当前仓库里自带测试输入：
  - `testDNA.fa`
  - `H19.fa`
- oracle 目录：
  - `tests/oracle`
  - `tests/oracle_rule1`
- 当前重点已经分成两条：
  - **exact-safe 主线**：继续保住 `exact SIM` / `exact threshold` 的结果一致性，避免实验路径回流污染默认语义；
  - **实验性 two-stage lane**：围绕 `minimal_v2`、heavy micro-anchor、coverage attribution 与 panel summary 做质量门控校准，暂不提升为默认路径。
- exact-safe host-merge profiling 现在补齐了两类离线基建：
  - `tests/sim_initial_host_merge_replay` 可以对 frozen corpus case 做 `warmup + iterations` 的离线 microbenchmark，并输出 aggregate TSV（含 `store_materialize / store_prune / store_other_merge` 与归一化 `ns/*` 指标）；
  - runtime 侧除了 full-payload corpus dump，还支持 manifest-only census 与 `case_id` 定向二次 full dump，因此 real-shard 流程应先做 manifest census，再做小规模 representative corpus，而不是继续直接开 unbounded full dump。
- host-merge representative corpus 现在还有一层脚本化决策护栏：
  - `scripts/select_sim_initial_host_merge_cases.py` 输出的 `selected.tsv` 仍以 `case_id` 为首列，可直接作为 `LONGTARGET_SIM_INITIAL_HOST_MERGE_CORPUS_CASE_LIST`，同时补齐 `bucket_key`、三维 tertile bin、原始计数和 `selection_rank` / `selection_reason`；
  - selector 现在新增 `coverage_weighted` 策略与 `--logical-weight` / `--materialized-weight` / `--coverage-report`，允许按 bucket 级别的 `logical_event + weighted store_materialized` 覆盖率做 representative ranking，而不是只按 `logical_event_count` 取代表 case；
  - `scripts/analyze_sim_initial_host_merge_phase_shares.py` 会把 manifest census、selected corpus 与 replay aggregate TSV 拼起来，产出 `selected_joined.tsv`、`bucket_rollup.tsv`、`summary.json`、`summary.md`；
  - 只有当 `covered_logical_event_share >= 0.80` 且 `covered_store_materialized_share >= 0.80` 时，summary 才会给出 `optimize_store_materialize` / `optimize_store_prune` / `split_materialize_and_prune` 这类下一刀建议；否则固定返回 `decision_status=insufficient_coverage` 与 `next_action=expand_corpus`，避免用覆盖不足的小 corpus 直接下算法结论。
  - 运行期 observability 已补上：manifest-only census 现在会在 run 开始时 eager-create `manifest.tsv` header，按 `LONGTARGET_SIM_INITIAL_HOST_MERGE_HEARTBEAT_SECONDS` / `LONGTARGET_SIM_INITIAL_HOST_MERGE_HEARTBEAT_CASES` 向 stderr flush heartbeat，并在 `SIGINT` / `SIGTERM` 后停止继续调度新任务、保留 partial manifest。
  - heavy real-shard (`hg38_chr22_21500001_200000_100001_50000.fa` vs `H19.fa`) 的复测已验证新行为：在首个 case 完成前就能持续看到 `processed_cases=0` heartbeat，手动中断后也会留下带 header 的 partial manifest 和 `capture_interrupted` summary；因此当前 blocker 已从“黑盒长跑”收窄为“继续把 census 跑完并选 representative corpus”，而不是 observability 缺失。
  - 基于同一份 heavy real-shard census manifest（`processed_cases=528`）做 dry-run 时，`coverage_weighted(logical=1, materialized=2)` 相比 legacy 已经明显补强 materialized-heavy 覆盖：
    - `limit=16`: legacy `logical=0.7824 / materialized=0.6688`，coverage-weighted `logical=0.8544 / materialized=0.8988`
    - `limit=20`: legacy `logical=0.9186 / materialized=0.8587`，coverage-weighted `logical=0.9581 / materialized=0.9610`
    - `limit=24`: legacy `logical=0.9887 / materialized=0.9775`，coverage-weighted `logical=0.9948 / materialized=0.9963`
  - 因此当前最值钱的下一步已经从“继续改 `store_materialize` / `store_prune` 算法”收敛为“先用 coverage-driven selector 选对 representative corpus，再决定 materialize/prune 的离线优化方向”。
  - 随后在同一条 heavy real-shard 上做了真实 `coverage_weighted limit=16` bounded full dump + replay + analysis：
    - 第二遍 runtime 只保留 `selected.tsv` 指定的 16 个 case 做 full dump；在 `16/16` 个 case 目录都落齐 `meta.json + summaries + expected_*` 后，主动中断 LongTarget 主流程，避免继续消耗与 host-merge replay 无关的后续 wall time。
    - `full_run.time.log` 记录到中断前 runtime wall time `740.68s`；离线 replay summary 则正式过 gate：`covered_logical_event_share=0.8544`，`covered_store_materialized_share=0.8988`，`decision_status=ready`。
    - phase-share 结果明确把下一刀指向 `store_materialize`：`store_materialize=63.7346s (46.69%)`，`store_other_merge=52.1729s (38.22%)`，`store_prune=20.5919s (15.09%)`，因此 `next_action=optimize_store_materialize`。
    - 这意味着 selector 侧可以先冻结在 `coverage_weighted(logical=1, materialized=2, limit=16)` 这个代表性配置上；host-merge 主线的后续优化优先级更新为：先打 `store_materialize`，`store_other_merge` 作为第二热点继续保留观测，`store_prune` 暂不抢第一优先级。
  - 针对同一份 16-case frozen corpus，replay microbenchmark 现已把 `store_materialize` 再拆成 `reset / insert / update / snapshot_copy` 四个子阶段，并把 `store_materialize_inserted_count / updated_count` 落进 aggregate TSV：
    - 16-case 直接求和：`store_materialize=3.6621s`，其中 `insert=1.7502s`、`update=1.9119s`、`snapshot_copy=0.0698s`、`reset≈0`。
    - 按 `logical_event_count` 加权看 `store_materialize` 内部构成，`update` 约占 `56.64%`，`insert` 约占 `43.36%`，`snapshot_copy` 仅约为 `1.55%` 的 replay-side 额外成本，不是主矛盾。
    - 计数侧也印证了这个方向：16-case 合计约 `6.70M` inserted records 对 `41.04M` updated records；折算后 `insert` 单记录成本约 `261 ns`，`update` 单记录成本约 `46.6 ns`，但 `update` 总量更大，因此当前 `store_materialize` 的第一刀应优先落在 safe-store upsert/update bookkeeping，而不是 replay 输出拷贝。
  - 针对同一份 frozen corpus 的第一轮低风险 upsert/materialize 优化（`reserve()`、热路径单次 `emplace()` + 原位 insert/update、无 instrumentation 时的 fast path、`emplace_back()` 去临时对象）已经完成并回放到新的 `replay_materialize_optimized*.tsv`：
    - 16-case aggregate 直接求和后，`store_materialize` 从 `3.6621s` 降到 `2.6052s`，绝对减少 `1.0570s`，相对改善约 `28.86%`，已明显超过原先为 `store_materialize` 设的 `15–20%` continuation 门槛。
    - 改善几乎全部来自 insert/materialize 侧：`insert_total` 从 `1.7502s` 降到 `0.5636s`，`insert` 单记录成本从约 `261.3 ns` 降到 `84.2 ns`；与此同时 `update_total` 从 `1.9119s` 小幅升到 `2.0415s`，`update` 单记录成本从约 `46.6 ns` 升到 `49.8 ns`，说明这一刀已经把“insert 代价不低”压下去，但还没有真正打到“update 次数太多”的核心矛盾。
    - 新增的 `store_materialize_peak_size / rehash_count` 也给出了明确反馈：16 个 case 全部只发生 `1` 次 rehash，`rehash_total=16`、`rehash_max=1`，说明 upfront `reserve()` 已把 `startCoordToIndex` 的增长收敛到每 case 一次前置 rehash；因此下一刀更值得继续盯 `update` bookkeeping，而不是再回去磨 snapshot copy 或反复扩容。
    - 基于这组结果，`store_materialize` 这条线暂时不需要回到 selector 或 corpus 选择；下一步应优先做更窄的 update-focused microbenchmark / 优化。如果下一轮 update-focused 改动拿不到新的实质收益，再把主火力切回 `store_other_merge`。
  - `5aef41d` 已作为 `store_materialize` 第一刀基线推上远端；随后用同一份 16-case frozen corpus 重跑 coverage-gated phase-share，结果确认主瓶颈已经从 `store_materialize` 切到 `store_other_merge`：
    - 新的 `analysis_other_merge_split/summary.json` 给出 `store_materialize=62.8632s (42.75%)`、`store_other_merge=74.5294s (50.69%)`、`store_prune=9.6502s (6.56%)`，`dominant_phase=store_other_merge`，`next_action=revisit_store_other_merge`。
    - 因此这一步不应该回滚 `5aef41d`，也不应该直接继续假设“下一刀先打 update”；更值钱的是先把新的第一大块 `store_other_merge` 从 residual 黑箱拆开。
  - 针对同一份 16-case frozen corpus，`replay_other_merge_split.aggregate.tsv` 现已把 `store_other_merge` 再拆成 `context_apply / context_snapshot / state_snapshot / residual` 四个子阶段，并保持 replay aggregate 的加和守恒：
    - 16-case aggregate 直接求和后，`store_other_merge=3.0619s`，其中 `context_apply=1.9366s (63.25%)`、`context_snapshot=0.000031s (~0%)`、`state_snapshot=0.1087s (3.55%)`、`residual=1.0166s (33.20%)`。
    - 这说明 replay-only `context_snapshot` 基本可以忽略，`state_snapshot` 也不是主矛盾；当前 `store_other_merge` 的第一大真实子阶段是 `context_apply`，但 residual 仍有约三分之一，暂时还不值得在没有进一步 split/trace 的情况下直接做更大的结构改写。
    - runtime benchmark stderr 也同步新增 `benchmark.sim_initial_store_other_merge_context_apply_seconds` 与 `benchmark.sim_initial_store_other_merge_residual_seconds`，这样 whole-genome 投影和真实 shard profile 都能在保留顶层 `sim_initial_store_other_merge_seconds` 的前提下，继续观察 `context_apply` 与 residual 的相对占比。
