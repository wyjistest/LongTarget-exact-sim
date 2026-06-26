# Fasim GASAL2 Phase 7 Broad Restart v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a default-off Phase 7 v2 frontier-log and replay-proof scaffold before attempting any broad reducer.

**Architecture:** CPU `aligner.Align()` remains authority. The first deliverable records a task-local / scoreInfo-local frontier log and proves exact replay against legacy output. Only after exact replay passes may a later reducer use GASAL2 descriptors to reduce CPU Align-side attempts.

**Tech Stack:** C++ Fasim runtime, existing GASAL2 bridge telemetry, shell gates, Python TSV parsers, Makefile targets.

---

## Context

The previous Phase 7 next reducer is stopped as a broad path:

```text
NEAT1 first1:
  digest_match = 0
  full_rows_equal = 0
  baseline_only_rows = 8
  candidate_only_rows = 5
  candidate_align_attempts = 1266
  reference_align_attempts = 2696
```

The next attempt must prove exact legacy frontier replay before reducing any
CPU Align work.

## Files

- Create: `docs/fasim_gasal2_phase7_broad_restart_v2_design.md`
- Create: `scripts/check_fasim_gasal2_phase7_frontier_log_env.sh`
- Create: `scripts/check_fasim_gasal2_phase7_frontier_log_runtime_smoke.sh`
- Create: `scripts/characterize_fasim_gasal2_phase7_frontier_replay.sh`
- Create: `scripts/check_fasim_gasal2_phase7_frontier_replay_result.sh`
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `fasim/gasal2_align_bridge.h`
- Modify: `fasim/gasal2_align_bridge.cpp`
- Modify: `Makefile`
- Modify: `docs/fasim_gasal2_goal_completion_roadmap.md`
- Modify: `scripts/summarize_fasim_gasal2_roadmap_current_state.py`

## Task 1: Add Frontier Log Env And Telemetry

**Files:**
- Create: `scripts/check_fasim_gasal2_phase7_frontier_log_env.sh`
- Modify: `fasim/gasal2_align_bridge.h`
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `Makefile`

Each task starts with this rule: write the failing checker before
implementation.

- [ ] **Step 1: Write the failing checker**

Create `scripts/check_fasim_gasal2_phase7_frontier_log_env.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP="$ROOT/fasim/Fasim-LongTarget.cpp"
STATS="$ROOT/fasim/gasal2_align_bridge.h"
MAKEFILE="$ROOT/Makefile"

python3 - "$CPP" "$STATS" "$MAKEFILE" <<'PY'
from pathlib import Path
import re
import sys

cpp = Path(sys.argv[1]).read_text(encoding="utf-8")
stats = Path(sys.argv[2]).read_text(encoding="utf-8")
makefile = Path(sys.argv[3]).read_text(encoding="utf-8")

for needle in [
    "FASIM_GASAL2_PHASE7_FRONTIER_LOG",
    "fasim_gasal2_phase7_frontier_log_runtime",
]:
    if needle not in cpp:
        raise SystemExit(f"missing runtime marker: {needle}")

for needle in [
    "phase7_frontier_log_requested",
    "phase7_frontier_log_active",
    "phase7_frontier_log_tasks",
    "phase7_frontier_log_scoreinfos",
    "phase7_frontier_log_align_attempts",
    "phase7_frontier_log_triplexes",
    "phase7_frontier_log_path",
    "phase7_frontier_log_digest",
]:
    if needle not in stats:
        raise SystemExit(f"missing telemetry marker: {needle}")

target = re.search(
    r"^check-fasim-gasal2-phase7-frontier-log-env:\n"
    r"\tbash \./scripts/check_fasim_gasal2_phase7_frontier_log_env\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("missing Makefile frontier-log env target")

print("ok")
PY
```

- [ ] **Step 2: Verify the checker fails**

Run:

```bash
bash scripts/check_fasim_gasal2_phase7_frontier_log_env.sh
```

Expected: FAIL with missing `FASIM_GASAL2_PHASE7_FRONTIER_LOG`.

- [ ] **Step 3: Add default-off env and telemetry fields**

Add an env helper in `fasim/Fasim-LongTarget.cpp`:

```cpp
static inline bool fasim_gasal2_phase7_frontier_log_runtime()
{
    return fasim_env_flag_enabled("FASIM_GASAL2_PHASE7_FRONTIER_LOG");
}
```

Add fields to the GASAL2 stats struct in `fasim/gasal2_align_bridge.h`:

```cpp
uint64_t phase7_frontier_log_requested;
uint64_t phase7_frontier_log_active;
uint64_t phase7_frontier_log_tasks;
uint64_t phase7_frontier_log_scoreinfos;
uint64_t phase7_frontier_log_align_attempts;
uint64_t phase7_frontier_log_triplexes;
std::string phase7_frontier_log_path;
std::string phase7_frontier_log_digest;
```

Add the Makefile target:

```make
check-fasim-gasal2-phase7-frontier-log-env:
	bash ./scripts/check_fasim_gasal2_phase7_frontier_log_env.sh
```

- [ ] **Step 4: Verify the env checker passes**

Run:

```bash
make check-fasim-gasal2-phase7-frontier-log-env
```

Expected: PASS and print `ok`.

## Task 2: Export CPU-Authority Frontier Log

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Create: `scripts/check_fasim_gasal2_phase7_frontier_log_runtime_smoke.sh`
- Modify: `Makefile`

- [ ] **Step 1: Write the failing runtime smoke**

Create `scripts/check_fasim_gasal2_phase7_frontier_log_runtime_smoke.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_frontier_log_runtime_smoke"}"

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/out"

cat >"$WORK/inputs/query.fa" <<'EOF'
>phase7_frontier_query
ACGTACGTACGTACGTACGTACGTACGTACGT
EOF
cat >"$WORK/inputs/target.fa" <<'EOF'
>phase7_frontier_target
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
EOF

env \
  FASIM_ALIGN_GASAL2=1 \
  FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  FASIM_GASAL2_PHASE7_FRONTIER_LOG=1 \
  "$BIN" \
  -f1 "$WORK/inputs/target.fa" \
  -f2 "$WORK/inputs/query.fa" \
  -r 0 \
  -O "$WORK/out" \
  >"$WORK/stdout.log" 2>"$WORK/stderr.log"

python3 - "$WORK/stderr.log" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
required = [
    "benchmark.fasim_gasal2_phase7_frontier_log_requested=1",
    "benchmark.fasim_gasal2_phase7_frontier_log_active=1",
    "benchmark.fasim_gasal2_phase7_frontier_log_path=",
    "benchmark.fasim_gasal2_phase7_frontier_log_digest=",
]
for needle in required:
    if needle not in text:
        raise SystemExit(f"missing runtime metric: {needle}")
print("ok")
PY
```

- [ ] **Step 2: Verify the smoke fails**

Run:

```bash
make check-fasim-gasal2-phase7-frontier-log-runtime-smoke
```

Expected: FAIL with missing Makefile target or missing runtime metric.

- [ ] **Step 3: Export a deterministic frontier log**

In `fasim/Fasim-LongTarget.cpp`, when
`FASIM_GASAL2_PHASE7_FRONTIER_LOG=1`, write a TSV under the output directory
with this frontier log schema:

```text
task_id
scoreinfo_index
scoreinfo_position
scoreinfo_score
attempt_index
attempt_start
attempt_cutlength
align_sw_score
align_ref_begin
align_ref_end
align_query_begin
align_query_end
selected
emitted_triplex_count_before
emitted_triplex_count_after
```

The log must be deterministic and must not change output.

- [ ] **Step 4: Verify the runtime smoke passes**

Run:

```bash
make check-fasim-gasal2-phase7-frontier-log-runtime-smoke
```

Expected: PASS and print `ok`.

## Task 3: Add Exact Replay Proof

**Files:**
- Create: `scripts/characterize_fasim_gasal2_phase7_frontier_replay.sh`
- Create: `scripts/check_fasim_gasal2_phase7_frontier_replay_result.sh`
- Modify: `Makefile`

- [ ] **Step 1: Write the failing result checker**

Create `scripts/check_fasim_gasal2_phase7_frontier_replay_result.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_frontier_replay/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing frontier replay report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
import csv
import sys
from pathlib import Path

rows = list(csv.DictReader(Path(sys.argv[1]).open(), delimiter="\t"))
if not rows:
    raise SystemExit("empty report")
for row in rows:
    if row["workload"] not in {"neat1_first1", "neat1_first64"}:
        raise SystemExit(f"unexpected workload {row['workload']}")
    if int(row["missing_rows"]) != 0:
        raise SystemExit(f"{row['workload']}: missing_rows != 0")
    if int(row["extra_rows"]) != 0:
        raise SystemExit(f"{row['workload']}: extra_rows != 0")
    if int(row["triplex_mismatches"]) != 0:
        raise SystemExit(f"{row['workload']}: triplex_mismatches != 0")
    if int(row["false_negative_scoreinfos"]) != 0:
        raise SystemExit(f"{row['workload']}: false_negative_scoreinfos != 0")
    if int(row["digest_match"]) != 1 and int(row["full_rows_equal"]) != 1:
        raise SystemExit(f"{row['workload']}: replay output not equal")
print("phase7_frontier_replay_result=pass")
print("ok")
PY
```

- [ ] **Step 2: Verify the result checker fails**

Run:

```bash
bash scripts/check_fasim_gasal2_phase7_frontier_replay_result.sh
```

Expected: FAIL with missing report.

- [ ] **Step 3: Implement the characterization script**

Create `scripts/characterize_fasim_gasal2_phase7_frontier_replay.sh` that:

```text
runs baseline CPU-authority output
runs FASIM_GASAL2_PHASE7_FRONTIER_LOG=1
loads the frontier log
replays selected/emitted rows without using GASAL2 output authority
compares baseline vs replay restored rows
emits report.tsv with:
  workload
  digest_match
  full_rows_equal
  missing_rows
  extra_rows
  triplex_mismatches
  false_negative_scoreinfos
  candidate_align_attempts
  reference_align_attempts
```

Run default workloads:

```text
NEAT1 first1
NEAT1 first64
```

- [ ] **Step 4: Verify replay proof passes before reducer work**

Run:

```bash
make characterize-fasim-gasal2-phase7-frontier-replay
make check-fasim-gasal2-phase7-frontier-replay-result
```

Expected: PASS only if missing_rows = 0 and extra_rows = 0 for both workloads.

## Task 4: Add Reducer Shadow Only After Replay Proof

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Create: `scripts/characterize_fasim_gasal2_phase7_frontier_reducer.sh`
- Create: `scripts/check_fasim_gasal2_phase7_frontier_reducer_result.sh`
- Modify: `Makefile`
- Modify: `docs/fasim_gasal2_workload_matrix.tsv`

- [ ] **Step 1: Write the failing reducer result checker**

The checker must require:

```text
NEAT1 first1:
  missing_rows = 0
  extra_rows = 0
  triplex_mismatches = 0
  false_negative_scoreinfos = 0
  candidate_align_attempts < reference_align_attempts

NEAT1 first64:
  same correctness fields
  candidate_wall_seconds < baseline_wall_seconds
  candidate_vs_baseline > 1.0
```

- [ ] **Step 2: Implement a reducer that consumes only the proven frontier log**

The reducer may skip CPU Align attempts only when the frontier log proves the
attempt cannot affect:

```text
task-local frontier identity
scoreInfo-local single-emission state
legacy top-N boundary
```

CPU aligner.Align() remains authority for every retained attempt.

- [ ] **Step 3: Verify before adding any broad workload-matrix row**

Run:

```bash
make characterize-fasim-gasal2-phase7-frontier-reducer
make check-fasim-gasal2-phase7-frontier-reducer-result
```

Expected: PASS before any `contract = broad_replacement` row is added.

## Completion Guard

Do not call the goal complete unless:

```text
NEAT1 first64 broad gate passes
full row-set equality or digest clean
candidate_vs_baseline > 1.0
scoreInfo/preAlign work reduced
Align-side attempts reduced or replaced
docs/fasim_gasal2_workload_matrix.tsv has a passing broad_replacement row
must_not_call_update_goal_complete = 0
```

Until then:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```
