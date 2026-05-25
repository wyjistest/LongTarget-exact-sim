# Fasim Current Base Phase Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Characterize current clean-base Fasim GPU/CPU phase behavior under the runtime envs actually active on `cuda-p0.2-initial-handoff-pipeline` after #141/#142.

**Architecture:** This is a characterization/docs change. Run the existing sharded runner on the local `rheMac10_nonchrom_top8.fa + H19` workload, summarize active envs, worker density, GPU sampler output, and currently observable phase fields. Do not change Fasim runtime semantics or claim historical final-speed-stack envs are active.

**Tech Stack:** Bash/Python measurement commands, existing `fasim_longtarget_cuda`, `scripts/fasim_sharded_runner.py`, `nvidia-smi`, Markdown docs.

---

### Task 1: Record Active Env Audit

**Files:**
- Create: `.tmp/fasim_current_base_phase_timeline/env_audit.txt`
- Read: `fasim/Fasim-LongTarget.cpp`
- Read: `fasim/fastsim.h`
- Read: `scripts/fasim_sharded_runner.py`

- [ ] **Step 1: Build the CUDA Fasim binary if needed**

Run:

```bash
make build-fasim-cuda
```

Expected: `fasim_longtarget_cuda` exists and command exits 0.

- [ ] **Step 2: Capture active envs from the binary**

Run:

```bash
mkdir -p .tmp/fasim_current_base_phase_timeline
strings ./fasim_longtarget_cuda \
  | rg 'FASIM_[A-Z0-9_]+' \
  | sort -u \
  > .tmp/fasim_current_base_phase_timeline/env_audit.txt
cat .tmp/fasim_current_base_phase_timeline/env_audit.txt
```

Expected: includes `FASIM_ENABLE_PREALIGN_CUDA`, `FASIM_EXTEND_THREADS`, `FASIM_OUTPUT_MODE`, `FASIM_CUDA_DEVICE`, `FASIM_CUDA_DEVICES`, `FASIM_PREALIGN_CUDA_TOPK`, `FASIM_PREALIGN_CUDA_MAX_TASKS`, `FASIM_PREALIGN_PEAK_SUPPRESS_BP`, and `FASIM_EXACT_COLUMN_EXTEND_BATCH`.

- [ ] **Step 3: Confirm historical final-speed-stack envs are not active source envs**

Run:

```bash
git grep -n 'FASIM_TRANSFERSTRING_TABLE\|FASIM_GPU_DP_COLUMN_AUTO\|FASIM_SSW_PROFILE_CACHE\|FASIM_SSW_AVX2\|FASIM_SSW_PROFILE_CONTEXT' -- fasim cuda scripts
```

Expected: no active source reads in `fasim`/`cuda`/runner code. Documentation references may exist elsewhere and must be called historical/stale for this clean base.

### Task 2: Run Current-Base Worker/Thread Matrix

**Files:**
- Create: `.tmp/fasim_current_base_phase_timeline/summary.tsv`
- Create: `.tmp/fasim_current_base_phase_timeline/summary.md`
- Inputs: `/data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa`
- Inputs: `H19.fa`

- [ ] **Step 1: Run matrix**

Run:

```bash
set -euo pipefail
ROOT=/data/wenyujianData/LongTarget-exact-sim
TARGET="$ROOT/.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa"
RNA="$PWD/H19.fa"
OUT="$PWD/.tmp/fasim_current_base_phase_timeline"
rm -rf "$OUT/runs" "$OUT/logs"
mkdir -p "$OUT/runs" "$OUT/logs"
printf 'extend_threads\tworkers\twall_seconds\tsingle_seconds\tdigest_match\tmerged_records\tgpu_avg_util\tgpu_max_util\tgpu_avg_power\tgpu_max_power\treport\n' > "$OUT/summary.tsv"
for et in 1 2 4; do
  for workers in 2 4 6; do
    run="$OUT/runs/et${et}_w${workers}"
    gpu_log="$OUT/logs/gpu_et${et}_w${workers}.csv"
    stdout_log="$OUT/logs/run_et${et}_w${workers}.stdout.log"
    stderr_log="$OUT/logs/run_et${et}_w${workers}.stderr.log"
    nvidia-smi --query-gpu=timestamp,index,utilization.gpu,utilization.memory,power.draw,memory.used --format=csv,noheader,nounits -lms 200 > "$gpu_log" 2>/dev/null &
    mon_pid=$!
    status=0
    env -u FASIM_CUDA_DEVICES python3 scripts/fasim_sharded_runner.py \
      --fasim-bin ./fasim_longtarget_cuda \
      --target "$TARGET" \
      --rna "$RNA" \
      --rule 1 \
      --work-dir "$run" \
      --output-mode lite \
      --validate-single \
      --workers "$workers" \
      --gpu-ids 0,1 \
      --auto-cpu-core-ranges \
      --cpu-pool 0-19 \
      --cpu-cores-per-worker 3 \
      --manifest "$run/run_manifest.json" \
      --env FASIM_ENABLE_PREALIGN_CUDA=1 \
      --env FASIM_EXTEND_THREADS="$et" \
      > "$stdout_log" 2> "$stderr_log" || status=$?
    kill "$mon_pid" 2>/dev/null || true
    wait "$mon_pid" 2>/dev/null || true
    if [ "$status" -ne 0 ]; then
      printf 'failed et=%s workers=%s status=%s stderr=%s\n' "$et" "$workers" "$status" "$stderr_log" >&2
      exit "$status"
    fi
    python3 - "$run/report.json" "$gpu_log" "$OUT/summary.tsv" "$et" "$workers" <<'PY'
import csv, json, statistics, sys
from pathlib import Path
report_path = Path(sys.argv[1])
gpu_log = Path(sys.argv[2])
out_path = Path(sys.argv[3])
et = sys.argv[4]
workers = sys.argv[5]
report = json.loads(report_path.read_text())
per_worker = report.get("per_worker") or []
wall = max(float(w.get("wall_seconds", 0.0)) for w in per_worker)
single = report.get("single_run") or {}
utils = []
powers = []
with gpu_log.open(newline="") as fh:
    for row in csv.reader(fh):
        if len(row) < 6:
            continue
        try:
            utils.append(float(row[2].strip()))
            powers.append(float(row[4].strip()))
        except ValueError:
            pass
avg_util = statistics.mean(utils) if utils else 0.0
max_util = max(utils) if utils else 0.0
avg_power = statistics.mean(powers) if powers else 0.0
max_power = max(powers) if powers else 0.0
with out_path.open("a") as fh:
    fh.write(
        f"{et}\t{workers}\t{wall:.6f}\t{float(single.get('wall_seconds', 0.0)):.6f}\t"
        f"{report.get('single_vs_sharded_digest_match')}\t{report.get('merged_records')}\t"
        f"{avg_util:.3f}\t{max_util:.3f}\t{avg_power:.3f}\t{max_power:.3f}\t{report_path}\n"
    )
PY
  done
done
cat "$OUT/summary.tsv"
```

Expected: all rows have `digest_match=True`.

- [ ] **Step 2: Summarize per-worker/per-shard balance**

Run:

```bash
python3 - <<'PY' > .tmp/fasim_current_base_phase_timeline/per_worker.tsv
import json
from pathlib import Path
base = Path(".tmp/fasim_current_base_phase_timeline/runs")
print("extend_threads\tworkers\tworker_seconds\tworker_records\tworker_shards\tgpu_ids\tcpu_ranges")
for path in sorted(base.glob("et*_w*/report.json")):
    report = json.loads(path.read_text())
    env = report.get("env_overrides", {})
    print(
        f"{env.get('FASIM_EXTEND_THREADS')}\t{report.get('worker_count')}\t"
        f"{[round(w.get('wall_seconds', 0), 3) for w in report.get('per_worker', [])]}\t"
        f"{[w.get('records') for w in report.get('per_worker', [])]}\t"
        f"{[w.get('shard_ids') for w in report.get('per_worker', [])]}\t"
        f"{[w.get('gpu_id') for w in report.get('per_worker', [])]}\t"
        f"{[w.get('cpu_core_range') for w in report.get('per_worker', [])]}"
    )
PY
cat .tmp/fasim_current_base_phase_timeline/per_worker.tsv
```

Expected: worker assignment and straggler shape are visible for 2/4/6 workers.

### Task 3: Write Current-Base Timeline Doc

**Files:**
- Create: `docs/fasim_current_base_gpu_cpu_phase_timeline.md`

- [ ] **Step 1: Create doc with measured table and current-base caveats**

Create `docs/fasim_current_base_gpu_cpu_phase_timeline.md` with:

```markdown
# Fasim Current-Base GPU/CPU Phase Timeline

This note characterizes the current clean `cuda-p0.2-initial-handoff-pipeline`
base after #141/#142. It intentionally does not describe historical final
speed-stack branches as active in this checkout.

## Current Active Runtime Env

...
```

Include:
- active env list from Task 1
- historical env list marked not active in current clean base
- benchmark command
- worker/thread table from Task 2
- observation that GPU avg remains low because current clean-base GPU path is preAlign CUDA burst
- explicit note that preAlign internal kernel/H2D/D2H timings are not currently emitted by Fasim, so timeline is limited to runner wall/per-worker/per-shard and external GPU sampler
- decision: current local candidate is `FASIM_EXTEND_THREADS=4`, `workers=4` on 2 GPUs, per worker single visible GPU

- [ ] **Step 2: Verify doc avoids historical speed-stack claims**

Run:

```bash
rg -n 'GPU_DP_COLUMN_AUTO|EXACT_COLUMN_EXTEND_BATCH|TRANSFERSTRING_TABLE|SSW_PROFILE_CACHE|SSW_AVX2|SSW_PROFILE_CONTEXT|final speed stack' docs/fasim_current_base_gpu_cpu_phase_timeline.md
```

Expected: any matches only appear in sections that explicitly say historical/not active in current clean base.

### Task 4: Verification and PR

**Files:**
- Modify: `docs/fasim_current_base_gpu_cpu_phase_timeline.md`

- [ ] **Step 1: Run verification**

Run:

```bash
make build-fasim-cuda
make check-fasim-sharded-worker-gpu-env-hygiene
make check-fasim-sharded-manifest-threadsafe
python3 -m py_compile scripts/fasim_sharded_runner.py scripts/check_fasim_sharded_manifest_threadsafe.py
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 2: Commit**

Run:

```bash
git add docs/superpowers/plans/2026-05-25-fasim-current-base-phase-timeline.md docs/fasim_current_base_gpu_cpu_phase_timeline.md
git commit -m "fasim: characterize current-base GPU CPU phase timeline"
```

Expected: commit succeeds with only docs changes.

- [ ] **Step 3: Open PR**

Run:

```bash
git push -u origin fasim-current-base-phase-timeline
gh pr create --base cuda-p0.2-initial-handoff-pipeline --head fasim-current-base-phase-timeline --title "fasim: characterize current-base GPU CPU phase timeline" --body-file -
```

Expected: PR URL is printed.

### Self-Review

- Spec coverage: active env audit, clean-base boundary, worker/thread matrix, GPU sampler, current recommended local config, and next decisions are covered.
- Placeholder scan: no TBD/TODO placeholders are allowed in the deliverable doc.
- Type consistency: all commands use existing script arguments from `scripts/fasim_sharded_runner.py`.
