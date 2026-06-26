# Fasim GASAL2 Phase 7 Next Reducer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prototype a default-off Phase 7 task-local / scoreInfo-local reducer that can reduce CPU `aligner.Align()` attempts while preserving CPU output authority.

**Architecture:** Keep CPU `aligner.Align()` as score, endpoint, CIGAR, output, and digest authority. GASAL2 may only produce candidate attempt scores; the new reducer must preserve legacy scoreInfo-local single-emission semantics and task-local frontiers before it can reduce CPU Align attempts.

**Tech Stack:** C++ Fasim runtime, GASAL2 bridge, shell check scripts, Python telemetry parsers, Makefile gates.

---

## Context

The current Phase 7 candidate coverage reducer is stopped:

```text
prefix coverage:
  false_negative_scoreinfos = 0
  candidate_align_attempts = 51
  reference_align_attempts = 51

selected-only coverage:
  false_negative_scoreinfos = 0
  candidate_attempts = 2352
  candidate_align_attempts = 51
  reference_align_attempts = 51

decision:
  current_reducer_no_go
  no_cpu_align_attempt_reduction
```

This plan implements a new default-off reducer scaffold. It must not reuse the
current prefix coverage reducer, selected-only coverage reducer, broad
replacement-consumer replay, or score-prepass state-machine trust as a broad
path.

## Files

- Modify: `fasim/fastsim.h`
- Modify: `fasim/gasal2_align_bridge.h`
- Modify: `fasim/Fasim-LongTarget.cpp`
- Create: `scripts/check_fasim_gasal2_phase7_next_reducer_env.sh`
- Create: `scripts/check_fasim_gasal2_phase7_next_reducer_runtime_smoke.sh`
- Create: `scripts/check_fasim_gasal2_phase7_next_reducer_result.sh`
- Create: `scripts/characterize_fasim_gasal2_phase7_next_reducer.sh`
- Modify: `Makefile`
- Modify: `docs/fasim_gasal2_phase7_next_reducer_design.md`
- Modify: `docs/fasim_gasal2_goal_completion_roadmap.md`
- Modify: `docs/fasim_gasal2_workload_matrix.tsv`

## Task 1: Add Default-Off Env And Telemetry Shape

**Files:**
- Modify: `fasim/fastsim.h`
- Modify: `fasim/gasal2_align_bridge.h`
- Create: `scripts/check_fasim_gasal2_phase7_next_reducer_env.sh`
- Modify: `Makefile`

- [ ] **Step 1: Write the failing checker**

Create `scripts/check_fasim_gasal2_phase7_next_reducer_env.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FASTSIM="$ROOT/fasim/fastsim.h"
STATS="$ROOT/fasim/gasal2_align_bridge.h"
MAKEFILE="$ROOT/Makefile"

python3 - "$FASTSIM" "$STATS" "$MAKEFILE" <<'PY'
from pathlib import Path
import re
import sys

fastsim = Path(sys.argv[1]).read_text(encoding="utf-8")
stats = Path(sys.argv[2]).read_text(encoding="utf-8")
makefile = Path(sys.argv[3]).read_text(encoding="utf-8")

required_fastsim = [
    "FASIM_GASAL2_PHASE7_NEXT_REDUCER_SHADOW",
    "fasim_gasal2_phase7_next_reducer_shadow_runtime",
]
for needle in required_fastsim:
    if needle not in fastsim:
        raise SystemExit(f"missing fastsim marker: {needle}")

required_stats = [
    "phase7_next_reducer_requested",
    "phase7_next_reducer_active",
    "phase7_next_reducer_tasks",
    "phase7_next_reducer_scoreinfos",
    "phase7_next_reducer_reference_attempts",
    "phase7_next_reducer_candidate_attempts",
    "phase7_next_reducer_candidate_align_attempts",
    "phase7_next_reducer_reference_align_attempts",
    "phase7_next_reducer_false_negative_scoreinfos",
    "phase7_next_reducer_triplex_mismatches",
    "phase7_next_reducer_missing_triplexes",
    "phase7_next_reducer_extra_triplexes",
    "phase7_next_reducer_digest_match",
    "phase7_next_reducer_full_rows_equal",
    "phase7_next_reducer_baseline_wall_seconds",
    "phase7_next_reducer_candidate_wall_seconds",
    "phase7_next_reducer_candidate_vs_baseline",
]
for needle in required_stats:
    if needle not in stats:
        raise SystemExit(f"missing stats marker: {needle}")

target = re.search(
    r"^check-fasim-gasal2-phase7-next-reducer-env:\n"
    r"\tbash \./scripts/check_fasim_gasal2_phase7_next_reducer_env\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("missing Makefile env target")

print("ok")
PY
```

- [ ] **Step 2: Verify the checker fails**

Run:

```bash
bash scripts/check_fasim_gasal2_phase7_next_reducer_env.sh
```

Expected: FAIL with missing `FASIM_GASAL2_PHASE7_NEXT_REDUCER_SHADOW`.

- [ ] **Step 3: Add env helper and stats fields**

Add a default-off helper in `fasim/fastsim.h`:

```cpp
inline bool fasim_gasal2_phase7_next_reducer_shadow_runtime()
{
    return fasim_env_flag_enabled("FASIM_GASAL2_PHASE7_NEXT_REDUCER_SHADOW");
}
```

Add the telemetry fields to the existing GASAL2/Fasim stats struct in
`fasim/gasal2_align_bridge.h` and initialize them to zero or sentinel values:

```cpp
uint64_t phase7_next_reducer_requested;
uint64_t phase7_next_reducer_active;
uint64_t phase7_next_reducer_tasks;
uint64_t phase7_next_reducer_scoreinfos;
uint64_t phase7_next_reducer_reference_attempts;
uint64_t phase7_next_reducer_candidate_attempts;
uint64_t phase7_next_reducer_candidate_align_attempts;
uint64_t phase7_next_reducer_reference_align_attempts;
uint64_t phase7_next_reducer_false_negative_scoreinfos;
uint64_t phase7_next_reducer_triplex_mismatches;
uint64_t phase7_next_reducer_missing_triplexes;
uint64_t phase7_next_reducer_extra_triplexes;
uint64_t phase7_next_reducer_digest_match;
uint64_t phase7_next_reducer_full_rows_equal;
double phase7_next_reducer_baseline_wall_seconds;
double phase7_next_reducer_candidate_wall_seconds;
double phase7_next_reducer_candidate_vs_baseline;
```

Add Makefile target:

```make
check-fasim-gasal2-phase7-next-reducer-env:
	bash ./scripts/check_fasim_gasal2_phase7_next_reducer_env.sh
```

- [ ] **Step 4: Verify the env checker passes**

Run:

```bash
make check-fasim-gasal2-phase7-next-reducer-env
```

Expected: PASS and print `ok`.

## Task 2: Add Runtime Smoke Scaffold

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Create: `scripts/check_fasim_gasal2_phase7_next_reducer_runtime_smoke.sh`
- Modify: `Makefile`

- [ ] **Step 1: Write the failing runtime smoke**

Create `scripts/check_fasim_gasal2_phase7_next_reducer_runtime_smoke.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_next_reducer_runtime_smoke"}"

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
rm -rf "$WORK"
mkdir -p "$WORK"

env \
  FASIM_OUTPUT_MODE=lite \
  FASIM_VERBOSE=0 \
  FASIM_GASAL2_PHASE7_NEXT_REDUCER_SHADOW=1 \
  "$BIN" \
  -f1 "$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa" \
  -f2 "$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa" \
  -r 0 \
  -O "$WORK/out" \
  >"$WORK/stdout.log" 2>"$WORK/stderr.log"

python3 - "$WORK/stderr.log" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
required = [
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_requested=1",
    "benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_active=1",
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
make check-fasim-gasal2-phase7-next-reducer-runtime-smoke
```

Expected: FAIL with missing Makefile target or missing runtime metric.

- [ ] **Step 3: Emit scaffold telemetry without changing output**

In `fasim/Fasim-LongTarget.cpp`, when
`fasim_gasal2_phase7_next_reducer_shadow_runtime()` is enabled, set:

```text
phase7_next_reducer_requested = 1
phase7_next_reducer_active = 1
phase7_next_reducer_candidate_align_attempts =
  phase7_next_reducer_reference_align_attempts
phase7_next_reducer_false_negative_scoreinfos = 0
```

The first scaffold is allowed to be a no-reduction scaffold. It must not change
candidate state, output rows, digest, endpoint, CIGAR, or traceback.

Print metrics with prefix:

```text
benchmark.fasim_long_query_streaming_scoreinfo_gpu_shadow_phase7_next_reducer_
```

- [ ] **Step 4: Add Makefile target and verify smoke passes**

Add:

```make
check-fasim-gasal2-phase7-next-reducer-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_next_reducer_runtime_smoke.sh
```

Run:

```bash
make check-fasim-gasal2-phase7-next-reducer-runtime-smoke
```

Expected: PASS and print `ok`.

## Task 3: Implement Task-Local / ScoreInfo-Local Reducer Shadow

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Create: `scripts/check_fasim_gasal2_phase7_next_reducer_result.sh`
- Create: `scripts/characterize_fasim_gasal2_phase7_next_reducer.sh`
- Modify: `Makefile`

- [ ] **Step 1: Write the result checker**

Create `scripts/check_fasim_gasal2_phase7_next_reducer_result.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_next_reducer/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Phase 7 next reducer report: $REPORT" >&2
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
    required = [
        "workload",
        "digest_match",
        "false_negative_scoreinfos",
        "triplex_mismatches",
        "candidate_align_attempts",
        "reference_align_attempts",
        "candidate_vs_baseline",
        "decision",
    ]
    for key in required:
        if key not in row:
            raise SystemExit(f"missing column: {key}")

go_rows = [row for row in rows if row["decision"] == "phase7_next_reducer_go"]
if go_rows:
    for row in go_rows:
        if int(row["digest_match"]) != 1:
            raise SystemExit("go row requires digest_match=1")
        if int(row["false_negative_scoreinfos"]) != 0:
            raise SystemExit("go row requires false_negative_scoreinfos=0")
        if int(row["triplex_mismatches"]) != 0:
            raise SystemExit("go row requires triplex_mismatches=0")
        if int(row["candidate_align_attempts"]) >= int(row["reference_align_attempts"]):
            raise SystemExit("go row requires align attempt reduction")
    print("phase7_next_reducer_result=go")
else:
    print("phase7_next_reducer_result=no_go")
print("ok")
PY
```

- [ ] **Step 2: Implement characterization runner**

Create `scripts/characterize_fasim_gasal2_phase7_next_reducer.sh` to run:

```text
NEAT1 first1 bounded smoke
NEAT1 first64 broad gate, if runtime cost is acceptable
```

The runner writes `report.tsv` with:

```text
workload
record_limit
digest_match
false_negative_scoreinfos
triplex_mismatches
candidate_align_attempts
reference_align_attempts
candidate_wall_seconds
baseline_wall_seconds
candidate_vs_baseline
decision
```

- [ ] **Step 3: Implement reducer**

Implement a task-local / scoreInfo-local reducer that:

```text
1. groups attempts by task and scoreInfo
2. preserves legacy attempt order
3. preserves scoreInfo-local single-emission state
4. computes candidate frontier before CPU Align
5. CPU-aligns only reduced candidates
6. compares reduced output with CPU authority
```

It must stop as diagnostic-only if:

```text
false_negative_scoreinfos > 0
triplex_mismatches > 0
digest differs
candidate_align_attempts >= reference_align_attempts
```

- [ ] **Step 4: Verify characterization**

Run:

```bash
make characterize-fasim-gasal2-phase7-next-reducer
make check-fasim-gasal2-phase7-next-reducer-result
```

Expected for an incomplete scaffold:

```text
phase7_next_reducer_result=no_go
ok
```

Expected for a successful prototype:

```text
phase7_next_reducer_result=go
ok
```

## Task 4: Wire Roadmap Completion Gates

**Files:**
- Modify: `docs/fasim_gasal2_goal_completion_roadmap.md`
- Modify: `docs/fasim_gasal2_workload_matrix.tsv`
- Modify: `scripts/decide_fasim_gasal2_goal_completion.py`
- Modify: `Makefile`

- [ ] **Step 1: Add workload matrix row only after real evidence**

Add a `broad_replacement` row only if NEAT1 first64 passes:

```text
contract = broad_replacement
scope = claimed
status = pass
row_equal = true
speedup > 1.0
fallbacks = 0
scoreinfo_reduced = true
align_side_reduced = true
```

- [ ] **Step 2: Verify completion decision**

Run:

```bash
make check-fasim-gasal2-goal-completion-decision
make check-fasim-gasal2-roadmap-current-state
```

Expected before broad evidence:

```text
broad_objective_status=open
must_not_call_update_goal_complete=1
```

Expected only after broad evidence:

```text
broad_objective_status=complete
must_not_call_update_goal_complete=0
```

Do not call `update_goal complete` until the latter state is supported by real
current-state evidence.

## Final Verification

Run:

```bash
make check-fasim-gasal2-roadmap-current-state
make check-fasim-gasal2-goal-completion-decision
make check-fasim-gasal2-roadmap-broad-restart-gate
make check-fasim-gasal2-roadmap-phase7-next-reducer-design
make check-fasim-gasal2-roadmap-phase7-next-reducer-implementation-plan
python3 -m py_compile \
  scripts/summarize_fasim_gasal2_roadmap_current_state.py \
  scripts/decide_fasim_gasal2_goal_completion.py
bash -n scripts/check_fasim_gasal2_roadmap_phase7_next_reducer_implementation_plan.sh
git diff --check
```

The goal remains open until the broad completion decision is supported by the
workload matrix and current-state gates.
