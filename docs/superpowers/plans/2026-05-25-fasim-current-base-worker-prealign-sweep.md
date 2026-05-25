# Fasim Current Base Worker PreAlign Sweep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Characterize the current clean-base Fasim worker, CPU extension, and preAlign parameter sweep on the local 2x4090 host using #144 telemetry.

**Architecture:** Run the existing sharded runner on the `rheMac10_nonchrom_top8.fa + H19` workload with current active envs only. Collect wall time, digest, worker balance, GPU sampler values, and #144 telemetry from `report.json`. Write a docs-only characterization with no Fasim runtime, scheduler, chunking, or multi-GPU semantic changes.

**Tech Stack:** Bash/Python measurement commands, `fasim_longtarget_cuda`, `scripts/fasim_sharded_runner.py`, `nvidia-smi`, JSON/TSV summaries, Markdown docs.

---

### Task 1: Baseline Setup and Validation

**Files:**
- Create: `.tmp/fasim_current_base_worker_prealign_sweep/`
- Read: `docs/fasim_current_base_prealign_cuda_decomposition.md`
- Read: `scripts/fasim_sharded_runner.py`

- [x] **Step 1: Build CUDA Fasim**

Run:

```bash
make build-fasim-cuda
```

Expected: command exits 0 and `./fasim_longtarget_cuda` exists.

- [x] **Step 2: Verify workload inputs**

Run:

```bash
TARGET=/data/wenyujianData/LongTarget-exact-sim/.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa
test -s "$TARGET"
test -s H19.fa
python3 - "$TARGET" <<'PY'
import sys
from pathlib import Path
target = Path(sys.argv[1])
contigs = 0
bases = 0
for line in target.read_text(encoding="utf-8").splitlines():
    if line.startswith(">"):
        contigs += 1
    elif line.strip():
        bases += len(line.strip())
print(f"contigs={contigs} bases={bases}")
assert contigs == 8
assert bases == 7181742
PY
```

Expected: `contigs=8 bases=7181742`.

### Task 2: Phase 1 Workers x EXTEND_THREADS Sweep

**Files:**
- Create: `.tmp/fasim_current_base_worker_prealign_sweep/phase1_summary.tsv`
- Create: `.tmp/fasim_current_base_worker_prealign_sweep/phase1_per_worker.tsv`
- Create: `.tmp/fasim_current_base_worker_prealign_sweep/phase1_gpu_logs/`
- Create: `.tmp/fasim_current_base_worker_prealign_sweep/phase1_runs/`

- [x] **Step 1: Run matrix**

Run:

```bash
set -euo pipefail
ROOT=/data/wenyujianData/LongTarget-exact-sim
TARGET="$ROOT/.tmp/fasim_sharded_worker_density_2gpu/inputs/rheMac10_nonchrom_top8.fa"
RNA="$PWD/H19.fa"
OUT="$PWD/.tmp/fasim_current_base_worker_prealign_sweep"
rm -rf "$OUT/phase1_runs" "$OUT/phase1_logs"
mkdir -p "$OUT/phase1_runs" "$OUT/phase1_logs"
printf 'phase\textend_threads\tworkers\twall_seconds\tsingle_seconds\tdigest_match\tmerged_records\tgpu_avg_util\tgpu_max_util\tprealign_active\tprealign_tasks\tprealign_batches\tprealign_h2d_seconds\tprealign_kernel_seconds\tprealign_d2h_seconds\tprealign_total_seconds\textend_seconds\toutput_seconds\tfallbacks\treport\n' > "$OUT/phase1_summary.tsv"
for et in 2 4 6; do
  for workers in 2 4 6; do
    run="$OUT/phase1_runs/et${et}_w${workers}"
    gpu_log="$OUT/phase1_logs/gpu_et${et}_w${workers}.csv"
    stdout_log="$OUT/phase1_logs/run_et${et}_w${workers}.stdout.log"
    stderr_log="$OUT/phase1_logs/run_et${et}_w${workers}.stderr.log"
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
    python3 - "$run/report.json" "$gpu_log" "$OUT/phase1_summary.tsv" "$et" "$workers" <<'PY'
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
telemetry = report.get("sharded_telemetry") or {}
utils = []
with gpu_log.open(newline="") as fh:
    for row in csv.reader(fh):
        if len(row) < 6:
            continue
        try:
            utils.append(float(row[2].strip()))
        except ValueError:
            pass
avg_util = statistics.mean(utils) if utils else 0.0
max_util = max(utils) if utils else 0.0
with out_path.open("a") as fh:
    fh.write(
        f"phase1\t{et}\t{workers}\t{wall:.6f}\t{float(single.get('wall_seconds', 0.0)):.6f}\t"
        f"{report.get('single_vs_sharded_digest_match')}\t{report.get('merged_records')}\t"
        f"{avg_util:.3f}\t{max_util:.3f}\t"
        f"{telemetry.get('fasim_prealign_cuda_active')}\t"
        f"{telemetry.get('fasim_prealign_cuda_tasks')}\t"
        f"{telemetry.get('fasim_prealign_cuda_batches')}\t"
        f"{float(telemetry.get('fasim_prealign_cuda_h2d_seconds', 0.0)):.9f}\t"
        f"{float(telemetry.get('fasim_prealign_cuda_kernel_seconds', 0.0)):.9f}\t"
        f"{float(telemetry.get('fasim_prealign_cuda_d2h_seconds', 0.0)):.9f}\t"
        f"{float(telemetry.get('fasim_prealign_cuda_total_seconds', 0.0)):.9f}\t"
        f"{float(telemetry.get('fasim_extend_seconds', 0.0)):.9f}\t"
        f"{float(telemetry.get('fasim_output_seconds', 0.0)):.9f}\t"
        f"{telemetry.get('fasim_prealign_cuda_fallbacks')}\t{report_path}\n"
    )
PY
  done
done
cat "$OUT/phase1_summary.tsv"
```

Expected: all rows complete and `digest_match=True`.

- [x] **Step 2: Summarize worker balance**

Run:

```bash
python3 - <<'PY' > .tmp/fasim_current_base_worker_prealign_sweep/phase1_per_worker.tsv
import json
from pathlib import Path
base = Path(".tmp/fasim_current_base_worker_prealign_sweep/phase1_runs")
print("extend_threads\tworkers\tworker_seconds\tworker_records\tworker_prealign_total\tworker_extend_seconds\tgpu_ids\tcpu_ranges")
for path in sorted(base.glob("et*_w*/report.json")):
    report = json.loads(path.read_text())
    env = report.get("env_overrides", {})
    print(
        f"{env.get('FASIM_EXTEND_THREADS')}\t{report.get('worker_count')}\t"
        f"{[round(w.get('wall_seconds', 0), 3) for w in report.get('per_worker', [])]}\t"
        f"{[w.get('records') for w in report.get('per_worker', [])]}\t"
        f"{[round((w.get('telemetry') or {}).get('fasim_prealign_cuda_total_seconds', 0), 6) for w in report.get('per_worker', [])]}\t"
        f"{[round((w.get('telemetry') or {}).get('fasim_extend_seconds', 0), 6) for w in report.get('per_worker', [])]}\t"
        f"{[w.get('gpu_id') for w in report.get('per_worker', [])]}\t"
        f"{[w.get('cpu_core_range') for w in report.get('per_worker', [])]}"
    )
PY
cat .tmp/fasim_current_base_worker_prealign_sweep/phase1_per_worker.tsv
```

Expected: per-worker wall and telemetry are visible.

### Task 3: Phase 2 Focused TOPK/MAX_TASKS Probe

**Files:**
- Create: `.tmp/fasim_current_base_worker_prealign_sweep/phase2_summary.tsv`

- [x] **Step 1: Select best phase1 workers/threads**

Use the lowest wall row from `phase1_summary.tsv`. If multiple rows are within
10%, keep the simpler/lower worker count as the primary candidate.

- [x] **Step 2: Run focused preAlign parameter probe**

Run at the selected workers/threads:

```text
TOPK=64 MAX_TASKS=4096
TOPK=128 MAX_TASKS=4096
TOPK=256 MAX_TASKS=4096
TOPK=64 MAX_TASKS=8192
```

Use the same command shape as Phase 1, adding:

```bash
--env FASIM_PREALIGN_CUDA_TOPK="$topk"
--env FASIM_PREALIGN_CUDA_MAX_TASKS="$max_tasks"
```

Expected: all rows complete and `digest_match=True`. If runtime budget is tight,
skip Phase 2 and document that it was not run.

### Task 4: Write Characterization Doc

**Files:**
- Create: `docs/fasim_current_base_worker_prealign_sweep.md`

- [x] **Step 1: Write measured summary**

Include:
- scope and current active env boundary
- workload and host
- command shape
- Phase 1 table
- Phase 2 table if run
- per-worker balance
- decision and local recommendation
- explicit note that no default policy changes are made

- [x] **Step 2: State decision using telemetry**

Decision text must cover:
- whether `fasim_extend_seconds` dominates `fasim_prealign_cuda_total_seconds`
- whether GPU utilization stayed low but wall time improved
- whether workers 4 or 6 is the local candidate
- whether TOPK/MAX_TASKS changed wall time or digest

### Task 5: Verification and PR

**Files:**
- Modify: `docs/fasim_current_base_worker_prealign_sweep.md`
- Modify: `docs/superpowers/plans/2026-05-25-fasim-current-base-worker-prealign-sweep.md`

- [x] **Step 1: Verify**

Run:

```bash
make build-fasim-cuda
make check-fasim-sharded-runner-telemetry
python3 -m py_compile scripts/fasim_sharded_runner.py
git diff --check
```

Expected: all commands exit 0.

- [x] **Step 2: Commit and PR**

Run:

```bash
git add docs/fasim_current_base_worker_prealign_sweep.md docs/superpowers/plans/2026-05-25-fasim-current-base-worker-prealign-sweep.md
git commit -m "fasim: characterize current-base worker preAlign sweep"
git push -u origin fasim-current-base-worker-prealign-sweep
gh pr create --base cuda-p0.2-initial-handoff-pipeline --head fasim-current-base-worker-prealign-sweep --title "fasim: characterize current-base worker preAlign sweep"
```

Expected: PR URL is printed.

### Self-Review

- Spec coverage: workers/extend sweep, #144 telemetry fields, optional TOPK/MAX_TASKS probe, digest, GPU sampler, local recommendation, and no default-policy change are covered.
- Placeholder scan: no TBD/TODO placeholders are used.
- Type consistency: telemetry field names match #144 runner report fields.
