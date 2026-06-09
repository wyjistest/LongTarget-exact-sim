# Fasim GASAL2 Attempt-Level Consumer Shadow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a default-off GASAL2 attempt-level consumer shadow that tests whether GASAL2 score-only attempt results can reduce CPU `aligner.Align()` attempts while preserving CPU-authority triplex output.

**Architecture:** Keep CPU `fastSIM_extend_from_scoreinfo()` output and digest authoritative. Generate the same per-scoreInfo Iden attempt stream as legacy, run GASAL2 score-only over those attempts, use legacy scoreInfo-local consumer semantics to select only the attempts that would need traceback, then CPU-align only those selected attempts in shadow and compare complete task triplex lists against CPU authority. Do not use GPU endpoint, CIGAR, traceback, output, or digest authority.

**Tech Stack:** C++11 Fasim runtime, existing `fasim/fastsim.h` scoreInfo consumer, existing `fasim/gasal2_align_bridge.{h,cpp}` score-only attempt API, shell checkers, Makefile gates.

---

## Context

Current broad checkpoint:

```text
decision = broad_path_current_architecture_no_go
broad_path_tasks = 3,058
broad_path_scoreinfo_groups = 52,994
broad_path_align_attempts = 264,970
broad_path_triplex_mismatches = 0
broad_path_missing_triplexes = 0
broad_path_extra_triplexes = 0
candidate_vs_baseline = 0.301413x
realpath_extend_align_attempts = 140,087
```

That proves the current replay-heavy broad replacement-consumer shadow is
correctness-clean, but it does not reduce align attempts and is not a real path.
The next architecture must reduce scoreInfo/align attempts before replaying CPU
aligner state.

This plan intentionally does not modify production output semantics. It builds
a shadow-only gate to answer:

```text
Can GASAL2 score-only attempt results select far fewer legacy attempts,
while CPU-aligning only those selected attempts still reproduces CPU authority
task triplexes?
```

## Non-Goals

Do not:

```text
use GASAL2 output for production output
use GASAL2 endpoint/CIGAR/traceback as authority
change scoring thresholds
change non-overlap / merge / scheduler behavior
change default runtime behavior
promote selected-only replay
promote current broad replay consumer
reuse historical final speed-stack env names
```

## Env And Telemetry

Add default-off env:

```text
FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1
```

Required benchmark keys:

```text
benchmark.fasim_gasal2_attempt_consumer_shadow_requested
benchmark.fasim_gasal2_attempt_consumer_shadow_active
benchmark.fasim_gasal2_attempt_consumer_shadow_decision
benchmark.fasim_gasal2_attempt_consumer_shadow_tasks
benchmark.fasim_gasal2_attempt_consumer_shadow_scoreinfos
benchmark.fasim_gasal2_attempt_consumer_shadow_attempts
benchmark.fasim_gasal2_attempt_consumer_shadow_score_seconds
benchmark.fasim_gasal2_attempt_consumer_shadow_select_seconds
benchmark.fasim_gasal2_attempt_consumer_shadow_selected_attempts
benchmark.fasim_gasal2_attempt_consumer_shadow_cpu_align_attempts
benchmark.fasim_gasal2_attempt_consumer_shadow_cpu_align_seconds
benchmark.fasim_gasal2_attempt_consumer_shadow_convert_seconds
benchmark.fasim_gasal2_attempt_consumer_shadow_total_seconds
benchmark.fasim_gasal2_attempt_consumer_shadow_triplex_mismatches
benchmark.fasim_gasal2_attempt_consumer_shadow_missing_triplexes
benchmark.fasim_gasal2_attempt_consumer_shadow_extra_triplexes
benchmark.fasim_gasal2_attempt_consumer_shadow_first_mismatch
benchmark.fasim_gasal2_attempt_consumer_shadow_fallbacks
benchmark.fasim_gasal2_attempt_consumer_shadow_digest_match
benchmark.fasim_gasal2_attempt_consumer_shadow_full_rows_equal
```

Decision values:

```text
not_requested
gasal2_unavailable
attempt_consumer_shadow_active
attempt_consumer_shadow_no_go
attempt_consumer_shadow_candidate_go
```

## Core Algorithm

For each task:

```text
1. Build legacy attempt descriptors:
   for each scoreInfo in original order:
     for Iden in 0.6, 0.7, 0.8, 0.9, 1.0:
       compute cutlength exactly like fastSIM_extend_from_scoreinfo()
       keep target view into strB
       store scoreinfo_index, start, cutlength, prealign_score

2. Run GASAL2 score-only:
   fasim_gasal2_select_attempts_strict(query, attempts, selected, error)
   or a new bridge helper that exposes selected indexes from score results.

3. Preserve legacy scoreInfo-local state:
   for each scoreInfo group in attempt order:
     if an attempt score >= scoreInfo.score:
       select the first threshold attempt and stop that scoreInfo
     otherwise select the best fallback attempt only if ref_end == cutlength - 1
     otherwise select last non-zero attempt if legacy behavior requires it

4. CPU-align only selected attempts:
   use aligner.Align() on selected target slices
   convertMyTriplex() using the existing CPU alignment result
   sort/unique/filter exactly like fastSIM_extend_from_scoreinfo()

5. Compare complete task triplexes against CPU authority:
   mismatch count
   missing count
   extra count
   first mismatch source/kind
```

The shadow must run beside the existing CPU authority path. It must not replace
`fastSIM_extend_from_scoreinfo()` or alter `triplex_list`.

## Task 1: Add Static Requirements Gate

**Files:**
- Create: `scripts/check_fasim_gasal2_attempt_consumer_shadow_plan.sh`
- Modify: `Makefile`
- Modify: `docs/fasim_gasal2_broad_path_architecture_gate.md`
- Modify: `docs/fasim_gasal2_scoreinfo_current_state.md`

- [ ] **Step 1: Write the checker**

Create `scripts/check_fasim_gasal2_attempt_consumer_shadow_plan.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAN="$ROOT/docs/plans/2026-06-09-fasim-gasal2-attempt-level-consumer-shadow.md"
BROAD_DOC="$ROOT/docs/fasim_gasal2_broad_path_architecture_gate.md"
CURRENT_DOC="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
MAKEFILE="$ROOT/Makefile"

for path in "$PLAN" "$BROAD_DOC" "$CURRENT_DOC" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing attempt-level consumer shadow dependency: $path" >&2
    exit 1
  fi
done

python3 - "$PLAN" "$BROAD_DOC" "$CURRENT_DOC" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

plan = " ".join(Path(sys.argv[1]).read_text(encoding="utf-8").split())
broad = " ".join(Path(sys.argv[2]).read_text(encoding="utf-8").split())
current = " ".join(Path(sys.argv[3]).read_text(encoding="utf-8").split())
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")

required_plan = [
    "Fasim GASAL2 Attempt-Level Consumer Shadow Implementation Plan",
    "FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1",
    "CPU `fastSIM_extend_from_scoreinfo()` output and digest authoritative",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_requested",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_selected_attempts",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_cpu_align_attempts",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_triplex_mismatches",
    "attempt_consumer_shadow_candidate_go",
    "Build legacy attempt descriptors",
    "Run GASAL2 score-only",
    "Preserve legacy scoreInfo-local state",
    "CPU-align only selected attempts",
    "Compare complete task triplexes against CPU authority",
    "selected_attempts << attempts",
    "cpu_align_attempts << broad_path_align_attempts",
    "triplex_mismatches = 0",
    "Do not use GPU endpoint",
    "Do not use GPU CIGAR",
    "Do not use GPU traceback",
]
missing = [phrase for phrase in required_plan if phrase not in plan]
if missing:
    raise SystemExit("attempt-level consumer shadow plan missing phrases: " + ", ".join(missing))

for forbidden in ("T" + "BD", "TO" + "DO", "fill in " + "details"):
    if forbidden in plan:
        raise SystemExit(f"attempt-level consumer shadow plan contains {forbidden!r}")

for phrase in (
    "prototype a materially different scoreInfo plus replacement consumer architecture",
    "reduce scoreInfo/align attempts before replaying CPU aligner state",
    "decision = broad_path_current_architecture_no_go",
):
    if phrase not in broad:
        raise SystemExit(f"broad architecture doc missing phrase: {phrase}")

for phrase in (
    "decision = broad_path_current_architecture_no_go",
    "current architecture should not proceed to a real path",
    "full objective remains open",
):
    if phrase not in current:
        raise SystemExit(f"current-state doc missing phrase: {phrase}")

target = re.search(
    r"^check-fasim-gasal2-attempt-consumer-shadow-plan:\n"
    r"\tbash \./scripts/check_fasim_gasal2_attempt_consumer_shadow_plan\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-attempt-consumer-shadow-plan target")
PY

echo "ok"
```

- [ ] **Step 2: Run the checker and verify it fails before Makefile wiring**

Run:

```bash
bash scripts/check_fasim_gasal2_attempt_consumer_shadow_plan.sh
```

Expected:

```text
Makefile missing check-fasim-gasal2-attempt-consumer-shadow-plan target
```

- [ ] **Step 3: Add Makefile target**

Add near the broad GASAL2 targets in `Makefile`:

```make
check-fasim-gasal2-attempt-consumer-shadow-plan:
	bash ./scripts/check_fasim_gasal2_attempt_consumer_shadow_plan.sh
```

Add `check-fasim-gasal2-attempt-consumer-shadow-plan` to the local `.PHONY`
line and to the `check-fasim-gasal2-scoreinfo-current-state` dependency list.

- [ ] **Step 4: Run the checker and current-state static gate**

Run:

```bash
make check-fasim-gasal2-attempt-consumer-shadow-plan
bash scripts/check_fasim_gasal2_scoreinfo_current_state.sh
```

Expected:

```text
ok
ok
```

## Task 2: Add Runtime Stats And Default-Off Env

**Files:**
- Modify: `fasim/gasal2_align_bridge.h`
- Modify: `fasim/gasal2_align_bridge.cpp`
- Modify: `fasim/gasal2_align_bridge_stub.cpp`
- Modify: `fasim/Fasim-LongTarget.cpp`
- Test: `scripts/check_fasim_gasal2_attempt_consumer_shadow_env.sh`

- [ ] **Step 1: Write the env checker**

Create `scripts/check_fasim_gasal2_attempt_consumer_shadow_env.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAIN="$ROOT/fasim/Fasim-LongTarget.cpp"
BRIDGE_H="$ROOT/fasim/gasal2_align_bridge.h"
BRIDGE_CPP="$ROOT/fasim/gasal2_align_bridge.cpp"
STUB="$ROOT/fasim/gasal2_align_bridge_stub.cpp"
MAKEFILE="$ROOT/Makefile"

for path in "$MAIN" "$BRIDGE_H" "$BRIDGE_CPP" "$STUB" "$MAKEFILE"; do
  if [[ ! -s "$path" ]]; then
    echo "missing attempt consumer env dependency: $path" >&2
    exit 1
  fi
done

python3 - "$MAIN" "$BRIDGE_H" "$BRIDGE_CPP" "$STUB" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

main = Path(sys.argv[1]).read_text(encoding="utf-8")
bridge_h = Path(sys.argv[2]).read_text(encoding="utf-8")
bridge_cpp = Path(sys.argv[3]).read_text(encoding="utf-8")
stub = Path(sys.argv[4]).read_text(encoding="utf-8")
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

env = "FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW"
required = [
    "attempt_consumer_shadow_requested",
    "attempt_consumer_shadow_active",
    "attempt_consumer_shadow_decision",
    "attempt_consumer_shadow_tasks",
    "attempt_consumer_shadow_scoreinfos",
    "attempt_consumer_shadow_attempts",
    "attempt_consumer_shadow_selected_attempts",
    "attempt_consumer_shadow_cpu_align_attempts",
    "attempt_consumer_shadow_triplex_mismatches",
    "attempt_consumer_shadow_missing_triplexes",
    "attempt_consumer_shadow_extra_triplexes",
    "attempt_consumer_shadow_first_mismatch",
    "attempt_consumer_shadow_fallbacks",
]
for phrase in required:
    if phrase not in bridge_h:
        raise SystemExit(f"bridge header missing {phrase}")

for phrase in (
    env,
    "attempt_consumer_shadow_decision",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_requested=",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_active=",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_selected_attempts=",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_cpu_align_attempts=",
):
    if phrase not in bridge_cpp and phrase not in main:
        raise SystemExit(f"runtime missing {phrase}")

for phrase in (
    "benchmark.fasim_gasal2_attempt_consumer_shadow_requested=0",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_active=0",
    "benchmark.fasim_gasal2_attempt_consumer_shadow_decision=not_requested",
):
    if phrase not in stub:
        raise SystemExit(f"stub missing {phrase}")

target = re.search(
    r"^check-fasim-gasal2-attempt-consumer-shadow-env:\n"
    r"\tbash \./scripts/check_fasim_gasal2_attempt_consumer_shadow_env\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing check-fasim-gasal2-attempt-consumer-shadow-env target")
PY

echo "ok"
```

- [ ] **Step 2: Run the checker and verify it fails**

Run:

```bash
bash scripts/check_fasim_gasal2_attempt_consumer_shadow_env.sh
```

Expected:

```text
bridge header missing attempt_consumer_shadow_requested
```

- [ ] **Step 3: Add stats fields**

In `fasim/gasal2_align_bridge.h`, extend `FasimGasal2Stats` with the required
attempt-consumer fields. Initialize counts to `0`, seconds to `0.0`, decision
to `"not_requested"`, and first mismatch to `"none"`.

- [ ] **Step 4: Print stats in real and stub builds**

In `fasim/gasal2_align_bridge.cpp::fasim_gasal2_print_stats()`, emit every
`benchmark.fasim_gasal2_attempt_consumer_shadow_*` key listed in this plan.

In `fasim/gasal2_align_bridge_stub.cpp::fasim_gasal2_print_stats()`, emit the
same keys with default values:

```text
requested=0
active=0
decision=not_requested
counts=0
seconds=0
first_mismatch=none
digest_match=0
full_rows_equal=0
```

- [ ] **Step 5: Add env helper**

Add a helper near the existing runtime env helpers in `fasim/Fasim-LongTarget.cpp`:

```cpp
static bool fasim_gasal2_attempt_consumer_shadow_runtime()
{
	const char *env = getenv("FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW");
	return env != NULL && env[0] != '\0' && env[0] != '0';
}
```

- [ ] **Step 6: Add Makefile target**

Add:

```make
check-fasim-gasal2-attempt-consumer-shadow-env:
	bash ./scripts/check_fasim_gasal2_attempt_consumer_shadow_env.sh
```

Add the target to `.PHONY` and to `check-fasim-gasal2-scoreinfo-current-state`.

- [ ] **Step 7: Verify env gate**

Run:

```bash
make check-fasim-gasal2-attempt-consumer-shadow-env
```

Expected:

```text
ok
```

## Task 3: Implement Score-Only Selection Shadow Helper

**Files:**
- Modify: `fasim/gasal2_align_bridge.h`
- Modify: `fasim/gasal2_align_bridge.cpp`
- Modify: `fasim/gasal2_align_bridge_stub.cpp`
- Test: `scripts/check_fasim_gasal2_attempt_consumer_shadow_selection.sh`

- [ ] **Step 1: Write static selection checker**

Create `scripts/check_fasim_gasal2_attempt_consumer_shadow_selection.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRIDGE_H="$ROOT/fasim/gasal2_align_bridge.h"
BRIDGE_CPP="$ROOT/fasim/gasal2_align_bridge.cpp"
STUB="$ROOT/fasim/gasal2_align_bridge_stub.cpp"
MAKEFILE="$ROOT/Makefile"

python3 - "$BRIDGE_H" "$BRIDGE_CPP" "$STUB" "$MAKEFILE" <<'PY'
import re
import sys
from pathlib import Path

bridge_h = Path(sys.argv[1]).read_text(encoding="utf-8")
bridge_cpp = Path(sys.argv[2]).read_text(encoding="utf-8")
stub = Path(sys.argv[3]).read_text(encoding="utf-8")
makefile = Path(sys.argv[4]).read_text(encoding="utf-8")

for phrase in (
    "fasim_gasal2_select_attempt_indexes_from_scores",
    "std::vector<size_t> *selectedAttemptIndexes",
):
    if phrase not in bridge_h:
        raise SystemExit(f"bridge header missing {phrase}")

for phrase in (
    "bool fasim_gasal2_select_attempt_indexes_from_scores",
    "run_score_only(&g_score_state",
    "select_attempts_from_scores(attempts, scoreResults",
    "attempt_consumer_shadow_score_seconds",
    "attempt_consumer_shadow_select_seconds",
):
    if phrase not in bridge_cpp:
        raise SystemExit(f"bridge implementation missing {phrase}")

if "bool fasim_gasal2_select_attempt_indexes_from_scores" not in stub:
    raise SystemExit("stub missing fasim_gasal2_select_attempt_indexes_from_scores")

target = re.search(
    r"^check-fasim-gasal2-attempt-consumer-shadow-selection:\n"
    r"\tbash \./scripts/check_fasim_gasal2_attempt_consumer_shadow_selection\.sh$",
    makefile,
    flags=re.MULTILINE,
)
if not target:
    raise SystemExit("Makefile missing selection checker target")
PY

echo "ok"
```

- [ ] **Step 2: Run checker and verify it fails**

Run:

```bash
bash scripts/check_fasim_gasal2_attempt_consumer_shadow_selection.sh
```

Expected:

```text
bridge header missing fasim_gasal2_select_attempt_indexes_from_scores
```

- [ ] **Step 3: Add bridge API**

Declare in `fasim/gasal2_align_bridge.h`:

```cpp
bool fasim_gasal2_select_attempt_indexes_from_scores(
	const std::string &query,
	const std::vector<FasimGasal2Attempt> &attempts,
	std::vector<size_t> *selectedAttemptIndexes,
	std::string *errorOut);
```

Implement in `fasim/gasal2_align_bridge.cpp`:

```cpp
bool fasim_gasal2_select_attempt_indexes_from_scores(
	const std::string &query,
	const std::vector<FasimGasal2Attempt> &attempts,
	std::vector<size_t> *selectedAttemptIndexes,
	std::string *errorOut)
{
	if (selectedAttemptIndexes != NULL)
	{
		selectedAttemptIndexes->clear();
	}
	if (!fasim_gasal2_enabled())
	{
		if (errorOut != NULL)
		{
			*errorOut = "gasal2_disabled";
		}
		return false;
	}
	if (attempts.empty())
	{
		if (errorOut != NULL)
		{
			*errorOut = "empty_attempts";
		}
		return false;
	}

	std::vector<ScoreOnlyResult> scoreResults;
	const int batchSize = fasim_gasal2_batch_size_runtime();
	const std::chrono::steady_clock::time_point scoreStart =
		std::chrono::steady_clock::now();
	if (!run_score_only(&g_score_state, query, attempts, batchSize, &scoreResults, errorOut))
	{
		return false;
	}
	g_stats.attempt_consumer_shadow_score_seconds += seconds_since(scoreStart);

	const std::chrono::steady_clock::time_point selectStart =
		std::chrono::steady_clock::now();
	select_attempts_from_scores(attempts, scoreResults, selectedAttemptIndexes);
	g_stats.attempt_consumer_shadow_select_seconds += seconds_since(selectStart);
	return true;
}
```

The implementation may use the existing mutex pattern if needed by surrounding
bridge functions. Keep the helper score-only: it must not run traceback.

Implement the stub to return `false` with `errorOut="gasal2_unavailable"`.

- [ ] **Step 4: Add Makefile target and verify**

Add:

```make
check-fasim-gasal2-attempt-consumer-shadow-selection:
	bash ./scripts/check_fasim_gasal2_attempt_consumer_shadow_selection.sh
```

Run:

```bash
make check-fasim-gasal2-attempt-consumer-shadow-selection
```

Expected:

```text
ok
```

## Task 4: Implement Task-Local Shadow Replay

**Files:**
- Modify: `fasim/fastsim.h`
- Modify: `fasim/Fasim-LongTarget.cpp`
- Test: `scripts/check_fasim_gasal2_attempt_consumer_shadow_runtime_smoke.sh`

- [ ] **Step 1: Write runtime smoke checker**

Create `scripts/check_fasim_gasal2_attempt_consumer_shadow_runtime_smoke.sh`.
Use the same fixture pattern as
`scripts/check_fasim_gasal2_broad_replacement_consumer_shadow.sh`, but set:

```bash
FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_LEGACY_BYTE=1
FASIM_LONG_QUERY_STREAMING_SCOREINFO_GPU_LEGACY_BYTE_SHARED=1
FASIM_GASAL2_LONGTARGET_BRIDGE=1
FASIM_GASAL2_CPU_TRACEBACK=1
```

Parse benchmark keys and require:

```text
attempt_consumer_shadow_requested = 1
attempt_consumer_shadow_active = 1
attempt_consumer_shadow_tasks > 0
attempt_consumer_shadow_scoreinfos > 0
attempt_consumer_shadow_attempts > 0
attempt_consumer_shadow_selected_attempts > 0
attempt_consumer_shadow_cpu_align_attempts == attempt_consumer_shadow_selected_attempts
attempt_consumer_shadow_cpu_align_attempts < attempt_consumer_shadow_attempts
attempt_consumer_shadow_triplex_mismatches = 0
attempt_consumer_shadow_missing_triplexes = 0
attempt_consumer_shadow_extra_triplexes = 0
```

For the first implementation, allow either:

```text
decision = attempt_consumer_shadow_active
decision = attempt_consumer_shadow_no_go
```

but fail if correctness counters are non-zero.

- [ ] **Step 2: Run smoke checker and verify it fails**

Run:

```bash
bash scripts/check_fasim_gasal2_attempt_consumer_shadow_runtime_smoke.sh
```

Expected:

```text
missing attempt_consumer_shadow_requested
```

- [ ] **Step 3: Add task-local shadow function**

In `fasim/fastsim.h`, add a helper near `fastSIM_extend_from_scoreinfo()`:

```cpp
inline bool fasim_shadow_attempt_consumer_from_scoreinfo(
	StripedSmithWaterman::Aligner &aligner,
	StripedSmithWaterman::Filter &filter,
	int32_t maskLen,
	const string &strA,
	const string &strB,
	const string &strSrc,
	long dnaStartPos,
	const std::vector<struct StripedSmithWaterman::scoreInfo> &finalScoreInfo,
	vector<struct triplex> &shadowTriplexList,
	long strand,
	long Para,
	long rule,
	int ntMin,
	int ntMax,
	int penaltyT,
	int penaltyC,
	const struct para &paraList,
	bool materializeAlignmentStrings,
	FasimFastsimExtendScoreInfoTiming *timing,
	std::string *errorOut)
```

Implementation rules:

```text
build the same attempts as fastSIM_extend_from_scoreinfo()
use target views
call fasim_gasal2_select_attempt_indexes_from_scores()
CPU-align only selected attempt indexes
convertMyTriplex() from CPU alignment
sort/unique/filter like fastSIM_extend_from_scoreinfo()
append accepted triplexes to shadowTriplexList
update timing and GASAL2 attempt-consumer stats
return false on empty attempts, GASAL2 failure, or invalid selected index
```

Do not mutate the real `triplex_list`.

- [ ] **Step 4: Wire into existing broad per-task comparison**

In `fasim/Fasim-LongTarget.cpp`, where `broadReplacementTriplexesByTask` and
CPU authority task triplexes are compared, add a parallel
`attemptConsumerTriplexesByTask` path when `FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1`.

Compare each task's attempt-consumer triplexes against CPU authority using the
existing `triplex_probe_equal()` / first-mismatch helpers. Record:

```text
triplex_mismatches
missing_triplexes
extra_triplexes
first_mismatch
digest_match
full_rows_equal
```

Set decision:

```text
attempt_consumer_shadow_active
```

If GASAL2 is unavailable, set:

```text
gasal2_unavailable
```

- [ ] **Step 5: Add Makefile target and verify smoke**

Add:

```make
check-fasim-gasal2-attempt-consumer-shadow-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_attempt_consumer_shadow_runtime_smoke.sh
```

Run:

```bash
make check-fasim-gasal2-attempt-consumer-shadow-runtime-smoke
```

Expected:

```text
attempt_consumer_shadow_triplex_mismatches=0
attempt_consumer_shadow_cpu_align_attempts < attempt_consumer_shadow_attempts
ok
```

If the smoke reports mismatches, do not broaden the workload. Record the first
mismatch and stop for debugging.

## Task 5: Characterize NEAT1 First64

**Files:**
- Create: `scripts/characterize_fasim_gasal2_attempt_consumer_neat1_first64.sh`
- Create: `scripts/check_fasim_gasal2_attempt_consumer_neat1_first64_result.sh`
- Modify: `Makefile`
- Modify: `docs/fasim_gasal2_broad_path_architecture_gate.md`
- Modify: `docs/fasim_gasal2_scoreinfo_current_state.md`

- [ ] **Step 1: Write characterization script**

Create `scripts/characterize_fasim_gasal2_attempt_consumer_neat1_first64.sh`.
Model it on `scripts/characterize_fasim_gasal2_broad_neat1_first64.sh`, but set
`FASIM_GASAL2_ATTEMPT_CONSUMER_SHADOW=1` and collect:

```text
baseline_wall_seconds
candidate_wall_seconds
candidate_vs_baseline
digest
records
attempt_consumer_shadow_tasks
attempt_consumer_shadow_scoreinfos
attempt_consumer_shadow_attempts
attempt_consumer_shadow_selected_attempts
attempt_consumer_shadow_cpu_align_attempts
attempt_consumer_shadow_score_seconds
attempt_consumer_shadow_select_seconds
attempt_consumer_shadow_cpu_align_seconds
attempt_consumer_shadow_convert_seconds
attempt_consumer_shadow_total_seconds
attempt_consumer_shadow_triplex_mismatches
attempt_consumer_shadow_missing_triplexes
attempt_consumer_shadow_extra_triplexes
realpath_extend_align_attempts
```

Decision logic:

```text
if mismatch/missing/extra != 0:
  decision = attempt_consumer_shadow_correctness_no_go
elif selected_attempts >= attempts:
  decision = attempt_consumer_shadow_no_reduction_no_go
elif cpu_align_attempts >= realpath_extend_align_attempts:
  decision = attempt_consumer_shadow_no_cpu_align_reduction_no_go
elif candidate_vs_baseline <= 1.0:
  decision = attempt_consumer_shadow_performance_no_go
else:
  decision = attempt_consumer_shadow_candidate_go
```

- [ ] **Step 2: Write result checker**

Create `scripts/check_fasim_gasal2_attempt_consumer_neat1_first64_result.sh`.
Require a report at:

```text
.tmp/characterize_fasim_gasal2_attempt_consumer_neat1_first64/report.json
```

Accept either candidate-go or measured no-go, but always require:

```text
digest clean
attempt_consumer_shadow_triplex_mismatches = 0
attempt_consumer_shadow_missing_triplexes = 0
attempt_consumer_shadow_extra_triplexes = 0
attempt_consumer_shadow_selected_attempts > 0
attempt_consumer_shadow_cpu_align_attempts == attempt_consumer_shadow_selected_attempts
attempt_consumer_shadow_cpu_align_attempts < attempt_consumer_shadow_attempts
decision_reasons present for any no-go
```

- [ ] **Step 3: Add Makefile targets**

Add:

```make
characterize-fasim-gasal2-attempt-consumer-neat1-first64:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_gasal2_attempt_consumer_neat1_first64.sh

check-fasim-gasal2-attempt-consumer-neat1-first64-result:
	bash ./scripts/check_fasim_gasal2_attempt_consumer_neat1_first64_result.sh
```

Add both targets to `.PHONY`. Add the result checker to
`check-fasim-gasal2-scoreinfo-current-state` only after a report exists.

- [ ] **Step 4: Run characterization**

Run:

```bash
make characterize-fasim-gasal2-attempt-consumer-neat1-first64
make check-fasim-gasal2-attempt-consumer-neat1-first64-result
```

Expected if this architecture works:

```text
decision=attempt_consumer_shadow_candidate_go
candidate_vs_baseline > 1.0
triplex_mismatches=0
cpu_align_attempts << realpath_extend_align_attempts
```

Expected acceptable stop result:

```text
decision=attempt_consumer_shadow_performance_no_go
triplex_mismatches=0
cpu_align_attempts < attempts
decision_reasons includes the failing gate
```

If correctness fails, stop and do not run larger workloads.

## Task 6: Update Decision Docs

**Files:**
- Modify: `docs/fasim_gasal2_broad_path_architecture_gate.md`
- Modify: `docs/fasim_gasal2_full_goal_decision.md`
- Modify: `docs/fasim_gasal2_scoreinfo_completion_gap.md`
- Modify: `docs/fasim_gasal2_scoreinfo_current_state.md`
- Modify: corresponding checker scripts

- [ ] **Step 1: Record measured result**

Add the NEAT1 first64 attempt-consumer shadow row to all decision docs:

```text
attempt-level consumer shadow:
  decision = <measured decision>
  digest clean
  triplex_mismatches = 0
  selected_attempts = <value>
  cpu_align_attempts = <value>
  attempts = <value>
  candidate_vs_baseline = <value>x
```

- [ ] **Step 2: Set continuation decision**

Use these rules:

```text
candidate_go:
  next PR = selected full-GASAL2 traceback shadow

performance_no_go:
  stop current attempt-level shadow as real path

correctness_no_go:
  debug GASAL2 score/ref_end equivalence before any performance claim

no_cpu_align_reduction_no_go:
  stop this architecture; it does not attack the blocker
```

- [ ] **Step 3: Update checkers**

Make the checkers require the measured decision and key numbers. The checker
must not accept stale text that still treats the attempt-level consumer as an
unmeasured future idea.

- [ ] **Step 4: Verify docs**

Run:

```bash
make check-fasim-gasal2-broad-path-architecture-gate
make check-fasim-gasal2-full-goal-decision
make check-fasim-gasal2-scoreinfo-completion-gap
bash scripts/check_fasim_gasal2_scoreinfo_current_state.sh
```

Expected:

```text
ok
ok
ok
ok
```

## Final Verification

Run:

```bash
make check-fasim-gasal2-attempt-consumer-shadow-plan
make check-fasim-gasal2-attempt-consumer-shadow-env
make check-fasim-gasal2-attempt-consumer-shadow-selection
make check-fasim-gasal2-attempt-consumer-shadow-runtime-smoke
bash scripts/check_fasim_gasal2_scoreinfo_current_state.sh
bash -n scripts/check_fasim_gasal2_attempt_consumer_shadow_plan.sh \
  scripts/check_fasim_gasal2_attempt_consumer_shadow_env.sh \
  scripts/check_fasim_gasal2_attempt_consumer_shadow_selection.sh \
  scripts/check_fasim_gasal2_attempt_consumer_shadow_runtime_smoke.sh \
  scripts/characterize_fasim_gasal2_attempt_consumer_neat1_first64.sh \
  scripts/check_fasim_gasal2_attempt_consumer_neat1_first64_result.sh
git diff --check -- Makefile fasim/fastsim.h fasim/Fasim-LongTarget.cpp \
  fasim/gasal2_align_bridge.h fasim/gasal2_align_bridge.cpp \
  fasim/gasal2_align_bridge_stub.cpp docs scripts
```

Run a changed-file bidi scan over touched docs, shell scripts, C++ headers, and
C++ sources.

## Decision

This plan is not a completion claim for the active objective. It is the next
materially different architecture probe after:

```text
decision = broad_path_current_architecture_no_go
```

The goal remains open until a GPU/GASAL2 scoreInfo/preAlign path is both
correctness-clean and faster than CPU authority on the claimed workload scope,
or the user explicitly accepts a narrower scoped product contract.
