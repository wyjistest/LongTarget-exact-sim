# GPU exact repair v1 — independent development candidate

Date: 2026-10-10. Branch: `codex/gpu-exact-repair-20261010`.

The candidate restores the frozen CPU's full `w010` TFOsorted result: 8,291
data rows, 19 columns, SHA-256
`8e6842d3967d86827ba22f1e0cd3aee17f1340f70f022be9ed537c47ba72d974`.
This is an engineering regression result. The original paper's acceptance
failure and no-go remain unchanged. Previously inspected holdouts are reused
development fixtures, not fresh acceptance data.

## Scope and identity

- Worktree: `/data/wenyujianData/LongTarget-exact-sim/.worktrees/gpu_exact_repair_20261010_v1`.
- Evidence: `/data/wenyujianData/linjieData/longtarget_runs/gasal2_exact_repair_20261010_v1`.
- Original HEAD: `9c9a59a9e86ef942c7819926b1c7e6c3df8d46e6`.
- Inherited prototype snapshot commit: `6e11d3f`; the repair is a subsequent change.
- Original dirty-source patch SHA-256:
  `cd5facb49e8871e49b0452e110d162f8a7ba8ae858d7b729e94bac1c1c404e99`.
- Final executable during validation: `.tmp/fasim_gpu_exact_repair_v1_04`.
- Executable SHA-256: `a5948c2568e8ac5918d1b21243282fcd5dfe303602a9fda1ad5b576d1f49b255`.
- CPU authority: original repo's
  `.paper-artifacts/bioinformatics-canonical-hybrid-v2/runtime-epoch1/fasim_longtarget_x86`,
  SHA-256 `75c59f80ee329fe913edce71ea8a0ec1a63620a978b15d3673f636d62268822e`.
- GPU: RTX 4090, CUDA 12.5, driver 555.42.06; complete `w010` runs use
  `GPU-d1f5be95-b8a3-3c18-f919-90913038a1a3`. Supplemental panel and fault
  probes also use physical GPU 1; each run receipt records the device selection.
- The copied GASAL2 development library is separate from the July paper
  binary/library. Do not substitute its identity for the frozen acceptance runtime.

The original worktree, production runtimes, queues, and acceptance artifacts
were not replaced. This executable is a local CUDA development build, not a
CentOS 6 deployment package or an OpenMP production release.

## Behavior

`FASIM_GPU_EXACT_REPAIR_V1=1` opts into the existing replacement pipeline for
short and long whole queries:

1. Exact legacy GPU min-score and 16-lane byte column maxima/scoreInfo.
2. GPU attempt forward DP with literal SSE2 16-lane byte semantics and 8-lane
   word replay on saturation; neutral query padding, signed byte Lazy-F
   predicates, endpoint ties and numeric path follow the CPU fork.
3. Ordered threshold/best-terminal/last selection on the host.
4. CPU reverse-start and banded CIGAR continuation using the actual numeric path.
5. Original triplex conversion and full output, committed from a `.partial.*`
   file after successful computation and checked stream closure.

There is no CPU forward replay in this replacement path. It remains a hybrid
backend: millions of selected alignments may still require CPU continuation.
It is not a GPU CIGAR implementation or an Accelign port.

The repair also fixes strict selection being overwritten when telemetry is
absent, maps `U/u` as the SSW fork does in the endpoint profile, and gives
ragged batches their actual target lengths. The independent legacy min-score
alphabet is preserved.

The prior `a6282b3` bounded traceback/memory-safety patch is carried forward to
both native and continuation code. Native zero-score alignments preserve the
existing no-alignment sentinel without dereferencing a negative target index;
forward-only native calls now release their temporary endpoint allocation.

The fork's `min(forward_score, reverse_score)` behavior is retained. If a
selected continuation lowers the score, only that scoreInfo group is resolved
again, in original order, using cached GPU forward endpoints. Counters record
reselection and additional continuation calls. No natural score-decrease case
occurred in the current regression corpus; this rare branch is not separately
claimed to have production coverage.

No recomputed-CIGAR-score equality gate or new zero-length CIGAR rejection was
added. Those are separate contracts and are not implicitly part of this repair.

GPU unavailability, incomplete scoreInfo capacity, missing continuation, or a
contract failure causes nonzero exit. A capacity cap must not silently discard
scientific candidates. Failed runs can retain `.partial.*` files for diagnosis,
but do not publish the normal TFOsorted name. Existing completed output names
are rejected rather than overwritten in this opt-in mode.

## Verification

| Check | Evidence | Result |
| --- | --- | --- |
| Full 492 nt query × 20,000,001 nt `w010` | `full03/w010` | 8,291 rows; byte-identical frozen CPU |
| Full-run accounting | `full03/w010/candidate/receipt.json` | 195,936 tasks; 12,594,048 GPU attempts; 3,148,512 CPU continuations; zero CPU forward oracle, fallback or continuation failure |
| Component corpus | `components_final` and `components04/cases.tsv` | 973/973 exact forward tuples, numeric paths, continued primary coordinates and CIGAR |
| Strict selection and ragged batch | `components_final/stderr.log` | telemetry on/off and strict API agree; mixed byte/word batches pass |
| Independent min-score/scoreInfo comparison | `scoreinfo03`, `panel04`, `panel05` | zero score, threshold, group-order or group-content mismatch on executed cases |
| H19 and three other natural short queries | first four cases in `panel04` | full output byte-identical; 145/311/95/159 rows |
| Natural 4,006 / 8,181 / 12,397 nt queries | `panel05` | full output byte-identical; 252/89/113 rows on 20 kb target views |
| CPU ASan + UBSan + leak detection | `host_sanitizers04` | 973/973 pass, no sanitizer report |
| Bounded/full-band traceback recovery | `tests/test_ssw_banded_traceback.cpp` | normal and ASan/UBSan builds pass |
| GPU compute-sanitizer memcheck | `gpu_memcheck04` | 973/973 pass; ERROR SUMMARY: 0 errors |
| GPU/capacity/output-mode negative controls | `faults04` | all return 1; no completed TFOsorted artifact |
| Final output publication | `smoke_final` and `benchmark_final` | final executable, exact output checks |

The 973 cases comprise the prior 625-case independent endpoint corpus plus
the two diagnosed tie fixtures, 90 vector-length/saturation boundary cases and
256 new deterministic mutation cases (seed 20261010). Secondary score/end
fields unused by this consumer are not claimed as an endpoint API contract.

GPU memcheck used the same CUDA object as the final executable. The final
CPU-only sanitizer driver covers native and forward-continuation paths without
requiring CUDA to run inside ASan. An earlier combined ASan/CUDA attempt failed
inside GASAL2 allocation before executing tests; its log is retained in
`sanitizers03`, and is not counted as a passing check.

Other retained failed development attempts: `components01` exposed U encoding;
`components02` exposed the native zero-score traceback path; `faults03` exposed
premature result-file creation. `panel04` stopped at its first long-query case
because the chr22 prefix was all N and executed no tasks. `panel05` selects the
first 20 kb window with at least 99% A/C/G/T using input content only, freezes
that choice before execution, and supplies the actual long-query evidence.

## Performance

Full-input AB/BA completed with four byte-identical outputs:

| Run | CPU authority | GPU exact repair |
| --- | ---: | ---: |
| AB | 338.0294 s | 137.4910 s |
| BA | 338.6481 s | 137.4149 s |

The ratio of median wall times is **2.4615×**, or about 59.4% less wall time.
This clears the bounded engineering 1.5× goal on `w010`, not the paper's 10×
goal or its separate fresh-input acceptance requirements.

The final full-input AB/BA receipt is `benchmark_final/performance.json`.
It times CPU, candidate, candidate, CPU sequentially, without the per-task
consumer TSV or in-process CPU oracle. Timing includes process/GPU startup,
transfers, CPU continuation, conversion, sorting and output. Every timed output
must match the frozen CPU file SHA-256.

The instrumented `full03` run localizes the remaining cost (these are stage
measurements, separate from the uninstrumented AB/BA result): min-score plus
main scoreInfo took about 4.10 s; attempt scoring took 77.88 s, including
50.14 s of GPU kernels and 4.88 s of transfers; CPU reverse/CIGAR continuation
took 30.03 s; conversion took 12.42 s. Consumer total was 123.15 s. These times
are nested, so they must not all be added together. The next performance study
should address the exact attempt-scoring stage and its many small launches,
then continuation/conversion; main scoreInfo alone cannot remove most of this
candidate's remaining wall time.

Interpretation is limited to this one workload and two repetitions per backend,
against the frozen serial CPU authority. This is not a comparison with the
12/18/112-thread OpenMP queues, an uncontended machine benchmark, a general
speedup claim, or evidence for a 10× paper claim. Eight unrelated CPU workers
were present on the 20-CPU host; no competing GPU workload was observed.

## Reproduction

Use the isolated worktree, with the copied/pinned `.tmp/GASAL2` checkout:

```bash
make -j2 build-fasim-gpu-exact-repair build-gpu-exact-repair-test \
  CUDA_CXXFLAGS='-O2 -std=c++11 --generate-code=arch=compute_89,code=sm_89'

python3 scripts/prepare_gpu_exact_repair_cases.py /new/path/components \
  --tie-receipt /data/wenyujianData/linjieData/longtarget_runs/gasal2_w010_diagnostic_20261010_v1/minimal_alignment_receipt.json
CUDA_VISIBLE_DEVICES=0 FASIM_GPU_EXACT_REPAIR_V1=1 \
  .tmp/test_gpu_exact_repair_endpoints /new/path/components/cases.tsv

python3 scripts/check_gpu_exact_repair_v1.py \
  --binary .tmp/fasim_gpu_exact_repair_v1 --work /new/path/smoke \
  --stage smoke --check-scoreinfo
python3 scripts/check_gpu_exact_repair_v1.py \
  --binary .tmp/fasim_gpu_exact_repair_v1 --work /new/path/full --stage full
python3 scripts/audit_gpu_exact_repair_v1.py \
  --binary .tmp/fasim_gpu_exact_repair_v1 --work /new/path/panel --stage panel
python3 scripts/audit_gpu_exact_repair_v1.py \
  --binary .tmp/fasim_gpu_exact_repair_v1 --work /new/path/faults --stage faults
python3 scripts/audit_gpu_exact_repair_v1.py \
  --binary .tmp/fasim_gpu_exact_repair_v1 --work /new/path/timing --stage benchmark
```

The Python runners clear inherited experimental `FASIM_*` settings and verify
the frozen authority identities. All evidence directories must be new. The
candidate currently supports `tfosorted` and `lite` output; full clustering is
outside this opt-in runtime. Oversized queries are limited by the endpoint
kernel's shared-memory capacity and must fail closed rather than be segmented
into independent scientific queries.
