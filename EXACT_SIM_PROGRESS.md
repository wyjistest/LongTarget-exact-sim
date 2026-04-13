# LongTarget exact-SIM 进展记录

## 时间与目标

- 日期：2026-03-25（最近更新：2026-03-29）
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
