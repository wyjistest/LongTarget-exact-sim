# Codex Handoff: LongTarget Exact SIM / Fasim Sharded Execution

This file is for continuing the work after copying this repository directory to
another server. It records the current branch/PR state, local artifacts, required
boundaries, and the next recommended actions.

## Current State

Repository:

```text
/data/wenyujianData/LongTarget-exact-sim
```

Current branch at handoff:

```text
fasim-hg38-primary-sharded-straggler-analysis
```

Recent commits:

```text
0bb4164 fasim: analyze hg38 primary sharded stragglers
1621b00 fasim: characterize hg38 primary genome sharding
1a1414e Merge pull request #138 from wyjistest/fasim-primary-contig-sharded-worker-matrix
```

Open PRs:

```text
#139
title: fasim: characterize hg38 primary genome sharding
url: https://github.com/wyjistest/LongTarget-exact-sim/pull/139
base: cuda-p0.2-initial-handoff-pipeline
head: fasim-hg38-genome-sharded-worker-matrix
state: OPEN
merge state: CLEAN

#140
title: fasim: analyze hg38 primary sharded stragglers
url: https://github.com/wyjistest/LongTarget-exact-sim/pull/140
base: fasim-hg38-genome-sharded-worker-matrix
head: fasim-hg38-primary-sharded-straggler-analysis
state: OPEN
merge state: CLEAN
```

#140 is intentionally stacked on #139 because #139 is still open. After #139 is
merged, retarget #140 to `cuda-p0.2-initial-handoff-pipeline`.

## Important Boundaries

Keep this line of work focused on outer parallelism and whole-genome readiness.

Do not add or change:

```text
chunk splitting
overlap heuristic
single-contig parallelism
in-process multi-GPU
default workers_per_gpu policy
Fasim C++ runtime
output/scoring/threshold/non-overlap semantics
4-GPU scaling claims on a 2-GPU machine
single whole-target full-genome digest claims unless actually measured
```

Digest equality remains the correctness gate before performance claims.

The local machine used for #139/#140 had 2 GPUs. Treat all 4/6/8 worker results
as local 2-GPU worker-density or oversubscription behavior, not 4-GPU scaling.

## What #139 Contains

#139 is a docs/result-only checkpoint for full hg38 primary chromosome
contig-level sharded execution.

Added file:

```text
docs/fasim_sharded_worker_hg38_primary_genome_matrix.md
```

Key result:

```text
workload: hg38 primary chromosomes chr1-22, chrX, chrY
shards: 24
merged_records: 178,425
duplicate_records_removed: 1,116
failed_shards: []

4 workers:
  wall_seconds: 2,898.2267

6 workers / workers_per_gpu=3:
  wall_seconds: 2,949.7175

4-worker merged_digest == 6-worker merged_digest:
  8dc08e4174c8174b816bd3f003b1c55314765a5df744940305bb6876880b7856
```

Interpretation:

```text
Full hg38 primary contig-level sharded execution is operational.
4-worker and 6-worker merged digests match.
workers_per_gpu=3 is not a global default; hg38 primary was slightly faster with 4 workers.
```

## What #140 Contains

#140 is a script/docs analysis checkpoint using #139 telemetry. It does not run
Fasim and does not change scheduler behavior.

Added files:

```text
scripts/analyze_fasim_sharded_run_stragglers.py
scripts/check_fasim_sharded_straggler_analysis.sh
docs/fasim_hg38_primary_sharded_straggler_analysis.md
```

Modified:

```text
Makefile
README.md
```

Main analyzer command:

```bash
python3 scripts/analyze_fasim_sharded_run_stragglers.py \
  --workload-name hg38_primary_chromosomes_H19 \
  --run workers_4=.tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_4/report.json \
  --run workers_6=.tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_6/report.json \
  --simulate-workers 1,2,3,4,5,6,8 \
  --output .tmp/fasim_hg38_genome_sharded_worker_matrix/hg38_primary_straggler_analysis.json
```

Key #140 conclusion:

```text
workers_4:
  wall_seconds: 2,898.2267
  total_shard_seconds: 11,340.0046
  scheduler_efficiency: 0.9782
  idle_estimate: 0.0218

workers_6:
  wall_seconds: 2,949.7175
  total_shard_seconds: 15,617.7752
  scheduler_efficiency: 0.8824
  idle_estimate: 0.1176

merged_digest_consistent: true
per_shard_digest_consistent: true
```

Interpretation:

```text
The hg38 primary 6-worker slowdown is not explained by a severe plan-only
contig imbalance. It looks more like workload-dependent oversubscription or
resource contention. Do not default workers_per_gpu=3 from rheMac10 top8.
```

## Local Artifacts Worth Preserving

If copying the current directory, preserve `.tmp/` if possible. It contains the
large input FASTA and reports/manifests used by #139/#140.

Important paths:

```text
.tmp/fasim_hg38_genome_sharded_worker_matrix/inputs/hg38_primary_chromosomes.fa
.tmp/fasim_hg38_genome_sharded_worker_matrix/hg38_primary_shard_balance_cpu0_17.json
.tmp/fasim_hg38_genome_sharded_worker_matrix/hg38_primary_straggler_analysis.json
.tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_4/report.json
.tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_4/run_manifest.json
.tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_6/report.json
.tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_6/run_manifest.json
H19.fa
```

Known input digest:

```text
hg38_primary_chromosomes.fa:
  d4b32d0c8e45e9c242fcada11025f73ff65275a7f0b01d4b8b26a70425f293ae
```

Prefer keeping the same repository path on the new server:

```text
/data/wenyujianData/LongTarget-exact-sim
```

Some manifests include absolute paths. Keeping the same path avoids unnecessary
resume incompatibility or stale-output confusion.

## New Server Setup Checklist

Use a modern Node for Codex:

```bash
node --version
# should be modern, e.g. v20+ or v22+
```

GitHub CLI status:

```bash
gh auth status
```

Expected account:

```text
wyjistest
```

If needed, set repo remote:

```bash
git remote -v
git remote set-url origin https://github.com/wyjistest/LongTarget-exact-sim.git
```

Or SSH, if SSH key is configured:

```bash
git remote set-url origin git@github.com:wyjistest/LongTarget-exact-sim.git
```

Check branch and PRs:

```bash
git status --short --branch
git fetch --all --prune
gh pr view 139
gh pr view 140
```

## Verification Commands Already Run for #140

These passed before handoff:

```bash
python3 -B -m py_compile \
  scripts/analyze_fasim_sharded_run_stragglers.py \
  scripts/analyze_fasim_shard_balance.py \
  scripts/fasim_sharded_runner.py \
  scripts/benchmark_fasim_sharded_worker_workload_matrix.py

make check-fasim-sharded-straggler-analysis
make check-fasim-shard-balance
make check-fasim-sharded-runner
make check-fasim-sharded-scheduler
make check-fasim-sharded-cpu-affinity
git diff --check
```

Also passed:

```text
changed-file bidi control scan
forbidden runtime/source scan
no leftover Fasim/runner process check
```

On the new server, rerun at least:

```bash
python3 -B -m py_compile scripts/analyze_fasim_sharded_run_stragglers.py
make check-fasim-sharded-straggler-analysis
git diff --check
```

If the full environment is available, rerun the larger set above.

## Recommended Next Actions

1. Review and merge #139 first.

2. After #139 merges, retarget #140:

```bash
gh pr edit 140 --base cuda-p0.2-initial-handoff-pipeline
```

Then confirm:

```bash
gh pr view 140 --json baseRefName,headRefName,mergeStateStatus
```

3. Review/merge #140 if the diff is clean.

4. Do not start chunking immediately from #140. The current #140 result says
   hg38 primary is more likely density/resource-contention-limited than
   obviously single-contig-straggler-limited.

5. The next useful PR after #140 is a focused hg38 primary density follow-up:

```text
fasim: characterize hg38 primary worker density
```

Suggested modes on a 2-GPU machine:

```text
3 workers / 2 GPUs
4 workers / 2 GPUs
5 workers / 2 GPUs
6 workers / 2 GPUs
```

Keep:

```text
manifest/resume
CPU affinity
explicit GPU ids
digest consistency gate
no default policy change
```

Only consider safe-overlap chunking design after showing that contig-level
sharding is truly limited by one or a few dominant chromosomes after resource
contention is controlled.

## Useful Commands

Show #140 stacked diff only:

```bash
git diff --stat fasim-hg38-genome-sharded-worker-matrix...HEAD
git diff --name-only fasim-hg38-genome-sharded-worker-matrix...HEAD
```

Show #140 PR files:

```bash
gh pr diff 140 --name-only
```

Run #140 analyzer:

```bash
python3 scripts/analyze_fasim_sharded_run_stragglers.py \
  --workload-name hg38_primary_chromosomes_H19 \
  --run workers_4=.tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_4/report.json \
  --run workers_6=.tmp/fasim_hg38_genome_sharded_worker_matrix/runs/workers_6/report.json \
  --simulate-workers 1,2,3,4,5,6,8 \
  --output .tmp/fasim_hg38_genome_sharded_worker_matrix/hg38_primary_straggler_analysis.json
```

Hygiene scans:

```bash
git diff --name-only HEAD^..HEAD | xargs -r grep -nP '[\x{202A}-\x{202E}\x{2066}-\x{2069}]' || true

git diff --name-only HEAD^..HEAD \
  | rg '(^|/)(cuda|longtarget|rules|fasim).*\.(cpp|cc|c|h|hpp|cu)$|longtarget\.cpp$' || true

ps -eo pid,args \
  | rg 'fasim_longtarget_cuda|fasim_longtarget_x86|benchmark_fasim_sharded_worker|fasim_sharded_runner|timeout' \
  | rg -v 'rg |bash -c|pgrep' || true
```

## Communication Preference

User prefers concise Chinese responses with concrete commands. For this project,
keep PRs tightly scoped and checkpoint-style. State exact boundaries clearly.
