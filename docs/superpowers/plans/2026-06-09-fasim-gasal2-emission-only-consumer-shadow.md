# Fasim GASAL2 Emission-Only Consumer Shadow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prototype a default-off GASAL2 emission-only scoreInfo consumer shadow that can reduce CPU `scoreInfo/preAlign` and CPU `aligner.Align()` attempts for the broad long-query path.

**Architecture:** Reuse the existing GASAL2 score-only attempt scoring path, but replace replay-heavy selected/prefix consumers with an emission-only state machine: GASAL2 score/end decides which attempt would emit for each scoreInfo, and CPU traceback validates only emitted attempts. CPU output and digest remain authoritative until NEAT1 first64 proves triplex/full-output equivalence and lower CPU align attempts.

**Tech Stack:** C++11 Fasim runtime, existing `fasim/gasal2_align_bridge.*` score/select APIs, `fastSIM_extend_from_scoreinfo()` legacy contract in `fasim/fastsim.h`, runner benchmark parsing in `scripts/fasim_sharded_runner.py`, Makefile shell/Python gates.

---

## Context

The original objective remains broad `scoreInfo/preAlign` GPU/GASAL2 replacement. Current scoped positives are not enough:

```text
short-query/H19 top5:
  scoped go

MALAT1 group32 two-contract:
  scoped go, modest speedup

NEAT1 broad replacement-consumer:
  correctness-clean but performance no-go

NEAT1 attempt-consumer:
  correctness-clean but no CPU align attempt reduction
```

The no-go root cause is replay shape. `fasim_shadow_attempt_consumer_from_scoreinfo()` currently expands selected attempts back to whole scoreInfo groups or unselected prefixes before CPU alignment. That preserves output but keeps CPU align attempts at the realpath level.

The new prototype must not reuse that expansion strategy.

## Contract

Add one default-off env:

```text
FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1
```

When unset:

```text
benchmark.fasim_gasal2_emission_only_consumer_shadow_requested=0
benchmark.fasim_gasal2_emission_only_consumer_shadow_active=0
benchmark.fasim_gasal2_emission_only_consumer_shadow_decision=not_requested
```

When set, CPU `fastSIM_extend_from_scoreinfo()` remains output authority. The shadow must:

```text
1. build the legacy scoreInfo attempt stream in scoreInfo order
2. score attempts with GASAL2 score-only APIs
3. run a score/end-only legacy emit state machine
4. CPU-align only the emitted attempts for traceback/triplex validation
5. compare per-task triplexes against CPU authority
6. report whether CPU align attempts are lower than realpath reference
```

Do not:

```text
use GPU endpoint as output authority
use GPU CIGAR/traceback
write candidate output
change Fasim output semantics
change default scheduler/runtime
use selected-only replay
use prefix/group replay that keeps CPU align attempts unchanged
promote MALAT1 scoped evidence as broad replacement
```

## Emission State Machine

The shadow must preserve the legacy `fastSIM_extend_from_scoreinfo()` contract, but its first pass uses GASAL2 score/end instead of CPU traceback:

```text
for each scoreInfo in legacy order:
  for each Iden attempt in legacy order:
    score attempt with GASAL2
    if gasal2_score >= scoreInfo.score:
      mark this attempt as the emitted attempt
      stop this scoreInfo
    else if gasal2_ref_end == cutlength - 1:
      remember best terminal attempt for this scoreInfo
  if no threshold attempt emitted:
    emit the remembered best terminal attempt, if any
```

The CPU validation pass then calls `aligner.Align()` only for emitted attempts. It does not CPU-align every scored attempt. If output differs, the prototype reports mismatch and remains a shadow.

## Telemetry

Add benchmark keys:

```text
fasim_gasal2_emission_only_consumer_shadow_requested
fasim_gasal2_emission_only_consumer_shadow_active
fasim_gasal2_emission_only_consumer_shadow_decision
fasim_gasal2_emission_only_consumer_shadow_tasks
fasim_gasal2_emission_only_consumer_shadow_scoreinfos
fasim_gasal2_emission_only_consumer_shadow_scored_attempts
fasim_gasal2_emission_only_consumer_shadow_threshold_emits
fasim_gasal2_emission_only_consumer_shadow_terminal_emits
fasim_gasal2_emission_only_consumer_shadow_empty_emits
fasim_gasal2_emission_only_consumer_shadow_cpu_align_attempts
fasim_gasal2_emission_only_consumer_shadow_realpath_reference_align_attempts
fasim_gasal2_emission_only_consumer_shadow_align_attempt_reduction
fasim_gasal2_emission_only_consumer_shadow_score_seconds
fasim_gasal2_emission_only_consumer_shadow_select_seconds
fasim_gasal2_emission_only_consumer_shadow_cpu_align_seconds
fasim_gasal2_emission_only_consumer_shadow_convert_seconds
fasim_gasal2_emission_only_consumer_shadow_total_seconds
fasim_gasal2_emission_only_consumer_shadow_triplex_mismatches
fasim_gasal2_emission_only_consumer_shadow_missing_triplexes
fasim_gasal2_emission_only_consumer_shadow_extra_triplexes
fasim_gasal2_emission_only_consumer_shadow_first_mismatch
fasim_gasal2_emission_only_consumer_shadow_fallbacks
fasim_gasal2_emission_only_consumer_shadow_digest_match
fasim_gasal2_emission_only_consumer_shadow_full_rows_equal
```

`align_attempt_reduction` must be:

```text
realpath_reference_align_attempts - cpu_align_attempts
```

No broad go claim is allowed if it is `<= 0`.

## NEAT1 First64 Gate

The hard gate is NEAT1 first64:

```text
triplex_mismatches = 0
missing_triplexes = 0
extra_triplexes = 0
digest_match = 1 or full_rows_equal = 1
fallbacks = 0
cpu_align_attempts < realpath_reference_align_attempts
candidate_wall_seconds < baseline_wall_seconds
candidate_vs_baseline > 1.0x
```

If triplexes are clean but wall time is slower, keep the scaffold and do not promote. If CPU align attempts are not reduced, stop the broad GASAL2 scoreInfo/preAlign line.

## Task 1: Add Static Plan Gate

**Files:**
- Create: `scripts/check_fasim_gasal2_emission_only_consumer_shadow_plan.sh`
- Modify: `Makefile`
- Modify: `docs/fasim_gasal2_broad_path_architecture_gate.md`
- Modify: `docs/fasim_gasal2_scoreinfo_current_state.md`
- Modify: `docs/fasim_gasal2_scoreinfo_completion_gap.md`
- Modify: `docs/fasim_gasal2_full_goal_decision.md`

- [ ] **Step 1: Write `scripts/check_fasim_gasal2_emission_only_consumer_shadow_plan.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAN="$ROOT/docs/superpowers/plans/2026-06-09-fasim-gasal2-emission-only-consumer-shadow.md"
MAKEFILE="$ROOT/Makefile"
ARCH="$ROOT/docs/fasim_gasal2_broad_path_architecture_gate.md"
CURRENT="$ROOT/docs/fasim_gasal2_scoreinfo_current_state.md"
GAP="$ROOT/docs/fasim_gasal2_scoreinfo_completion_gap.md"
FULL="$ROOT/docs/fasim_gasal2_full_goal_decision.md"

python3 - "$PLAN" "$MAKEFILE" "$ARCH" "$CURRENT" "$GAP" "$FULL" <<'PY'
import re
import sys
from pathlib import Path

plan, makefile, arch, current, gap, full = [Path(p) for p in sys.argv[1:]]
for path in (plan, makefile, arch, current, gap, full):
    if not path.exists():
        raise SystemExit(f"missing file: {path}")

plan_text = plan.read_text(encoding="utf-8")
required_plan = [
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1",
    "CPU `fastSIM_extend_from_scoreinfo()` remains output authority",
    "score attempts with GASAL2 score-only APIs",
    "CPU-align only the emitted attempts",
    "cpu_align_attempts < realpath_reference_align_attempts",
    "candidate_vs_baseline > 1.0x",
    "If CPU align attempts are not reduced, stop the broad GASAL2 scoreInfo/preAlign line.",
]
for needle in required_plan:
    if needle not in plan_text:
        raise SystemExit(f"plan missing required text: {needle}")

make_text = makefile.read_text(encoding="utf-8")
if "check-fasim-gasal2-emission-only-consumer-shadow-plan:" not in make_text:
    raise SystemExit("missing Makefile emission-only plan target")
if "bash ./scripts/check_fasim_gasal2_emission_only_consumer_shadow_plan.sh" not in make_text:
    raise SystemExit("missing Makefile emission-only plan recipe")

for label, path in (("arch", arch), ("current", current), ("gap", gap), ("full", full)):
    text = path.read_text(encoding="utf-8")
    if "emission-only scoreInfo consumer shadow" not in text:
        raise SystemExit(f"{label} doc missing emission-only cross-link")
    if "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1" not in text:
        raise SystemExit(f"{label} doc missing env name")

print("ok")
PY
```

- [ ] **Step 2: Add Makefile target**

```make
check-fasim-gasal2-emission-only-consumer-shadow-plan:
	bash ./scripts/check_fasim_gasal2_emission_only_consumer_shadow_plan.sh
```

Add it to `.PHONY` and to the broad/current-state gate dependency list next to `check-fasim-gasal2-broad-path-architecture-gate`.

- [ ] **Step 3: Cross-link docs**

Add this paragraph to the four docs listed in **Files**:

```text
The next broad attempt is an emission-only scoreInfo consumer shadow:
FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1. It must use GASAL2 score/end to
choose emitted attempts and CPU-align only those emitted attempts. It is a
go only if NEAT1 first64 is triplex/digest clean and CPU align attempts are
lower than the realpath reference.
```

- [ ] **Step 4: Verify**

Run:

```bash
make check-fasim-gasal2-emission-only-consumer-shadow-plan
```

Expected:

```text
ok
```

- [ ] **Step 5: Commit**

```bash
git add Makefile \
  docs/superpowers/plans/2026-06-09-fasim-gasal2-emission-only-consumer-shadow.md \
  scripts/check_fasim_gasal2_emission_only_consumer_shadow_plan.sh \
  docs/fasim_gasal2_broad_path_architecture_gate.md \
  docs/fasim_gasal2_scoreinfo_current_state.md \
  docs/fasim_gasal2_scoreinfo_completion_gap.md \
  docs/fasim_gasal2_full_goal_decision.md
git commit -m "fasim: plan GASAL2 emission-only consumer shadow"
```

## Task 2: Add Default-Off Env And Zero Telemetry

**Files:**
- Modify: `fasim/fastsim.h`
- Modify: `fasim/gasal2_align_bridge.h`
- Modify: `fasim/gasal2_align_bridge_stub.cpp`
- Modify: `fasim/gasal2_align_bridge.cpp`
- Modify: `fasim/Fasim-LongTarget.cpp`
- Create: `scripts/check_fasim_gasal2_emission_only_consumer_shadow_env.sh`
- Modify: `Makefile`

- [ ] **Step 1: Add runtime flag helper in `fasim/fastsim.h`**

Near `fasim_gasal2_attempt_consumer_shadow_enabled_runtime()` add:

```cpp
inline bool fasim_gasal2_emission_only_consumer_shadow_enabled_runtime()
{
	static int cached = -1;
	if (cached < 0)
	{
		const char* env = getenv("FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW");
		cached = (env != NULL && env[0] != '\0' && env[0] != '0') ? 1 : 0;
	}
	return cached != 0;
}
```

- [ ] **Step 2: Add stats fields in `FasimGasal2Stats`**

In `fasim/gasal2_align_bridge.h`, add fields matching the telemetry list:

```cpp
uint64_t emission_only_consumer_shadow_requested;
uint64_t emission_only_consumer_shadow_active;
std::string emission_only_consumer_shadow_decision;
uint64_t emission_only_consumer_shadow_tasks;
uint64_t emission_only_consumer_shadow_scoreinfos;
uint64_t emission_only_consumer_shadow_scored_attempts;
uint64_t emission_only_consumer_shadow_threshold_emits;
uint64_t emission_only_consumer_shadow_terminal_emits;
uint64_t emission_only_consumer_shadow_empty_emits;
uint64_t emission_only_consumer_shadow_cpu_align_attempts;
uint64_t emission_only_consumer_shadow_realpath_reference_align_attempts;
int64_t emission_only_consumer_shadow_align_attempt_reduction;
double emission_only_consumer_shadow_score_seconds;
double emission_only_consumer_shadow_select_seconds;
double emission_only_consumer_shadow_cpu_align_seconds;
double emission_only_consumer_shadow_convert_seconds;
double emission_only_consumer_shadow_total_seconds;
uint64_t emission_only_consumer_shadow_triplex_mismatches;
uint64_t emission_only_consumer_shadow_missing_triplexes;
uint64_t emission_only_consumer_shadow_extra_triplexes;
std::string emission_only_consumer_shadow_first_mismatch;
uint64_t emission_only_consumer_shadow_fallbacks;
uint64_t emission_only_consumer_shadow_digest_match;
uint64_t emission_only_consumer_shadow_full_rows_equal;
```

Initialize numeric fields to zero, `decision` to `"not_requested"`, and `first_mismatch` to `"none"`.

- [ ] **Step 3: Print zero telemetry in the stub**

In `fasim/gasal2_align_bridge_stub.cpp::fasim_gasal2_print_stats()`, print each new key with zero/not-requested values. Use the exact `benchmark.` names from **Telemetry**.

- [ ] **Step 4: Print real telemetry in GASAL2 build**

In `fasim/gasal2_align_bridge.cpp::fasim_gasal2_print_stats()`, print each new key from `fasim_gasal2_snapshot_stats()`.

- [ ] **Step 5: Add env checker**

Create `scripts/check_fasim_gasal2_emission_only_consumer_shadow_env.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 - "$ROOT" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1])
fastsim = (root / "fasim/fastsim.h").read_text(encoding="utf-8")
bridge = (root / "fasim/gasal2_align_bridge.h").read_text(encoding="utf-8")
stub = (root / "fasim/gasal2_align_bridge_stub.cpp").read_text(encoding="utf-8")
runtime = (root / "fasim/gasal2_align_bridge.cpp").read_text(encoding="utf-8")
makefile = (root / "Makefile").read_text(encoding="utf-8")

needles = [
    "FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW",
    "fasim_gasal2_emission_only_consumer_shadow_enabled_runtime",
]
for needle in needles:
    if needle not in fastsim:
        raise SystemExit(f"fastsim.h missing {needle}")

fields = [
    "emission_only_consumer_shadow_requested",
    "emission_only_consumer_shadow_active",
    "emission_only_consumer_shadow_decision",
    "emission_only_consumer_shadow_cpu_align_attempts",
    "emission_only_consumer_shadow_realpath_reference_align_attempts",
    "emission_only_consumer_shadow_align_attempt_reduction",
]
for field in fields:
    if field not in bridge:
        raise SystemExit(f"bridge header missing {field}")
    if f"benchmark.fasim_gasal2_{field}" not in stub:
        raise SystemExit(f"stub missing benchmark for {field}")
    if f"benchmark.fasim_gasal2_{field}" not in runtime:
        raise SystemExit(f"runtime missing benchmark for {field}")

if "check-fasim-gasal2-emission-only-consumer-shadow-env:" not in makefile:
    raise SystemExit("Makefile missing env target")

print("ok")
PY
```

- [ ] **Step 6: Add Makefile target**

```make
check-fasim-gasal2-emission-only-consumer-shadow-env:
	bash ./scripts/check_fasim_gasal2_emission_only_consumer_shadow_env.sh
```

- [ ] **Step 7: Verify**

Run:

```bash
make check-fasim-gasal2-emission-only-consumer-shadow-env
make build-fasim-gasal2 FASIM_GASAL2_TARGET=$PWD/.tmp/fasim_longtarget_gasal2_direct
```

Expected:

```text
ok
```

and build exits 0.

- [ ] **Step 8: Commit**

```bash
git add fasim/fastsim.h fasim/gasal2_align_bridge.h fasim/gasal2_align_bridge_stub.cpp \
  fasim/gasal2_align_bridge.cpp fasim/Fasim-LongTarget.cpp \
  scripts/check_fasim_gasal2_emission_only_consumer_shadow_env.sh Makefile
git commit -m "fasim: add emission-only consumer shadow telemetry"
```

## Task 3: Implement Emission-Only Shadow Helper

**Files:**
- Modify: `fasim/fastsim.h`
- Modify: `fasim/gasal2_align_bridge.h`
- Modify: `fasim/gasal2_align_bridge.cpp`
- Modify: `fasim/gasal2_align_bridge_stub.cpp`
- Create: `scripts/check_fasim_gasal2_emission_only_consumer_shadow_runtime_smoke.sh`
- Modify: `Makefile`

- [ ] **Step 1: Add stat recorder declaration**

In `fasim/gasal2_align_bridge.h`, declare:

```cpp
void fasim_gasal2_record_emission_only_consumer_shadow_request(
	uint64_t tasks,
	uint64_t scoreinfos,
	uint64_t scoredAttempts,
	const char *decision);

void fasim_gasal2_record_emission_only_consumer_shadow_result(
	uint64_t thresholdEmits,
	uint64_t terminalEmits,
	uint64_t emptyEmits,
	uint64_t cpuAlignAttempts,
	uint64_t realpathReferenceAlignAttempts,
	double scoreSeconds,
	double selectSeconds,
	double cpuAlignSeconds,
	double convertSeconds,
	double totalSeconds,
	bool active,
	const char *decision);

void fasim_gasal2_record_emission_only_consumer_shadow_comparison(
	uint64_t triplexMismatches,
	uint64_t missingTriplexes,
	uint64_t extraTriplexes,
	const char *firstMismatch,
	uint64_t digestMatch,
	uint64_t fullRowsEqual);
```

- [ ] **Step 2: Implement recorders**

Implement the three recorders in `fasim/gasal2_align_bridge.cpp` by adding to the global stats under the existing stats mutex. Stub implementations in `fasim/gasal2_align_bridge_stub.cpp` should accept arguments and do nothing.

- [ ] **Step 3: Add helper signature in `fasim/fastsim.h`**

Add:

```cpp
inline bool fasim_shadow_emission_only_consumer_from_scoreinfo(
	StripedSmithWaterman::Aligner &aligner,
	StripedSmithWaterman::Filter &filter,
	int32_t maskLen,
	const string &strA,
	const string &strB,
	const string &strSrc,
	long dnaStartPos,
	const std::vector<struct StripedSmithWaterman::scoreInfo> &finalScoreInfo,
	uint64_t realpathReferenceAlignAttempts,
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
	std::string *errorOut);
```

- [ ] **Step 4: Implement attempt building**

Use the exact attempt-building loop from `fasim_shadow_attempt_consumer_from_scoreinfo()`:

```cpp
for each scoreInfo:
  for Iden = 0.6 to 1.0:
    cutlength = (score + 24) / (9 * Iden - 4) + 1
    clamp by scoreInfo.position
    start = scoreInfo.position - cutlength + 1
    skip invalid windows
    set target view on strB
```

Do not add unselected prefixes or group expansion.

- [ ] **Step 5: Implement score/end selection**

Call `fasim_gasal2_select_attempts(strA, attempts, &scoredAttempts, &error)` or `fasim_gasal2_select_attempt_indexes_from_scores()` depending on available API detail:

```text
preferred:
  fasim_gasal2_select_attempts returns FasimGasal2SelectedAlignment with
  score_prepass_score and score_prepass_ref_end for every selected/scored item

fallback:
  if the API only returns selected indexes, extend it to return score/end for
  all attempts before implementing runtime integration
```

The implementation must not CPU-align during selection.

- [ ] **Step 6: Implement emission-only state machine**

For each scoreInfo group:

```cpp
bool emitted = false;
bool haveTerminal = false;
FasimGasal2SelectedAlignment terminalBest;

for each scored attempt in legacy order:
  if (emitted) continue;
  if (attempt.score_prepass_score >= scoreInfo.score) {
    emittedAttempts.push_back(attempt);
    ++thresholdEmits;
    emitted = true;
    continue;
  }
  if (attempt.score_prepass_ref_end == attempt.cutlength - 1) {
    keep best terminal by score, then earlier legacy order
  }

if (!emitted && haveTerminal) {
  emittedAttempts.push_back(terminalBest);
  ++terminalEmits;
}
if (!emitted && !haveTerminal) {
  ++emptyEmits;
}
```

- [ ] **Step 7: CPU-align emitted attempts only**

For each `emittedAttempts` item:

```cpp
smallSeq.assign(strB.data() + attempt.start, attempt.cutlength);
aligner.Align(strA.c_str(), smallSeq.c_str(), smallSeq.size(), filter, &localAlignment, maskLen);
```

Convert with `convertMyTriplex()` after offsetting `ref_begin/ref_end` by `attempt.start`. Count `cpuAlignAttempts` only here.

- [ ] **Step 8: Fail closed on invalid result**

Return `false` and record fallback if:

```text
GASAL2 selection fails
emitted attempt index is out of range
scoreInfo index is invalid
cpuAlignAttempts >= realpathReferenceAlignAttempts
```

The last condition is intentional for the broad goal. A no-reduction implementation is not useful.

- [ ] **Step 9: Add runtime smoke checker**

Create `scripts/check_fasim_gasal2_emission_only_consumer_shadow_runtime_smoke.sh` to run a small NEAT1 first1 fixture with:

```bash
FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1
FASIM_GASAL2_SCORE_PREPASS_STATE_MACHINE_ALIGN_CACHE=1
```

The checker must require:

```text
benchmark.fasim_gasal2_emission_only_consumer_shadow_requested = 1
benchmark.fasim_gasal2_emission_only_consumer_shadow_active = 1
benchmark.fasim_gasal2_emission_only_consumer_shadow_scored_attempts > 0
benchmark.fasim_gasal2_emission_only_consumer_shadow_cpu_align_attempts > 0
benchmark.fasim_gasal2_emission_only_consumer_shadow_cpu_align_attempts
  < benchmark.fasim_gasal2_emission_only_consumer_shadow_realpath_reference_align_attempts
```

Do not require triplex clean in the first smoke. The first smoke proves the new shape reduces CPU align attempts.

- [ ] **Step 10: Add Makefile target**

```make
check-fasim-gasal2-emission-only-consumer-shadow-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/check_fasim_gasal2_emission_only_consumer_shadow_runtime_smoke.sh
```

- [ ] **Step 11: Verify**

Run:

```bash
make check-fasim-gasal2-emission-only-consumer-shadow-env
make check-fasim-gasal2-emission-only-consumer-shadow-runtime-smoke
```

Expected:

```text
ok
```

- [ ] **Step 12: Commit**

```bash
git add fasim/fastsim.h fasim/gasal2_align_bridge.h fasim/gasal2_align_bridge.cpp \
  fasim/gasal2_align_bridge_stub.cpp scripts/check_fasim_gasal2_emission_only_consumer_shadow_runtime_smoke.sh Makefile
git commit -m "fasim: add emission-only consumer shadow smoke"
```

## Task 4: Integrate Shadow Comparison In Realpath Flush

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Create: `scripts/characterize_fasim_gasal2_emission_only_consumer_neat1_first64.sh`
- Create: `scripts/check_fasim_gasal2_emission_only_consumer_neat1_first64_result.sh`
- Modify: `Makefile`

- [ ] **Step 1: Call helper after CPU authority realpath**

In the long-query streaming realpath section, immediately after `fastSIM_extend_from_scoreinfo()` records `extendTiming.realpath_extend_align_attempts`, call `fasim_shadow_emission_only_consumer_from_scoreinfo()` when the env is enabled.

Pass:

```cpp
extendTiming.align_attempts
```

as `realpathReferenceAlignAttempts`.

- [ ] **Step 2: Store triplexes by task**

Mirror `attemptConsumerTriplexesByTask`:

```cpp
std::vector< std::vector<triplex> > emissionOnlyTriplexesByTask;
std::vector<unsigned char> emissionOnlyTaskCovered;
std::string emissionOnlyFirstMismatch;
```

Store helper output by `task.taskIndex`.

- [ ] **Step 3: Compare against CPU authority**

After CPU task triplexes are available, compare with `triplex_probe_equal()`:

```cpp
if covered and !triplex_probe_equal(emissionOnlyTriplexesByTask[t], taskTriplexes):
  ++emission_only_consumer_shadow_triplex_mismatches
  record first mismatch string
```

Also count missing/extra task-level triplexes using the same logic as broad replacement consumer where possible.

- [ ] **Step 4: Add characterization script**

Create `scripts/characterize_fasim_gasal2_emission_only_consumer_neat1_first64.sh`. It should run baseline and candidate on NEAT1 first64 with the existing sharded runner conventions and emit `report.json` containing:

```text
decision
baseline_wall_seconds
candidate_wall_seconds
candidate_vs_baseline
triplex_mismatches
missing_triplexes
extra_triplexes
cpu_align_attempts
realpath_reference_align_attempts
align_attempt_reduction
score_seconds
total_seconds
digest_match or full_rows_equal
```

Set decision:

```text
emission_only_consumer_go
emission_only_consumer_clean_but_slow_no_go
emission_only_consumer_mismatch_no_go
emission_only_consumer_no_cpu_align_reduction_no_go
```

- [ ] **Step 5: Add result checker**

Create `scripts/check_fasim_gasal2_emission_only_consumer_neat1_first64_result.sh` requiring the report to exist and requiring hard gate fields to be present. For the first result, do not force `go`; force a hard decision:

```text
decision must be one of the four explicit values
cpu_align_attempts < realpath_reference_align_attempts unless decision is no_cpu_align_reduction_no_go
triplex_mismatches/missing/extra must be numeric
candidate_vs_baseline must be numeric
```

- [ ] **Step 6: Add Makefile targets**

```make
characterize-fasim-gasal2-emission-only-consumer-neat1-first64:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct BUILD_BIN=0 bash ./scripts/characterize_fasim_gasal2_emission_only_consumer_neat1_first64.sh

check-fasim-gasal2-emission-only-consumer-neat1-first64-result:
	bash ./scripts/check_fasim_gasal2_emission_only_consumer_neat1_first64_result.sh
```

- [ ] **Step 7: Verify**

Run:

```bash
make check-fasim-gasal2-emission-only-consumer-shadow-runtime-smoke
make characterize-fasim-gasal2-emission-only-consumer-neat1-first64
make check-fasim-gasal2-emission-only-consumer-neat1-first64-result
```

Expected:

```text
ok
```

The characterization may decide no-go. A no-go result is acceptable if it is explicit and measured.

- [ ] **Step 8: Commit**

```bash
git add fasim/Fasim-LongTarget.cpp scripts/characterize_fasim_gasal2_emission_only_consumer_neat1_first64.sh \
  scripts/check_fasim_gasal2_emission_only_consumer_neat1_first64_result.sh Makefile
git commit -m "fasim: characterize emission-only consumer shadow"
```

## Task 5: Update Decision Docs

**Files:**
- Modify: `docs/fasim_gasal2_broad_path_architecture_gate.md`
- Modify: `docs/fasim_gasal2_scoreinfo_current_state.md`
- Modify: `docs/fasim_gasal2_scoreinfo_completion_gap.md`
- Modify: `docs/fasim_gasal2_full_goal_decision.md`
- Modify: `docs/superpowers/plans/2026-06-09-fasim-gasal2-emission-only-consumer-shadow.md`

- [ ] **Step 1: Record the measured result**

Add an `Emission-Only Consumer Result` section to each decision doc with:

```text
env = FASIM_GASAL2_EMISSION_ONLY_CONSUMER_SHADOW=1
workload = NEAT1 first64
decision = <measured decision>
triplex_mismatches = <number>
missing_triplexes = <number>
extra_triplexes = <number>
cpu_align_attempts = <number>
realpath_reference_align_attempts = <number>
align_attempt_reduction = <number>
candidate_vs_baseline = <number>
```

- [ ] **Step 2: Preserve the original goal boundary**

Add:

```text
This does not complete the broad objective unless NEAT1 first64 is clean,
CPU align attempts are reduced, and candidate wall time beats baseline.
```

- [ ] **Step 3: Verify decision docs**

Update `scripts/check_fasim_gasal2_scoreinfo_current_state.sh`, `scripts/check_fasim_gasal2_scoreinfo_completion_gap.sh`, and `scripts/check_fasim_gasal2_full_goal_decision.sh` to require the new result section and decision value.

- [ ] **Step 4: Verify**

Run:

```bash
bash scripts/check_fasim_gasal2_scoreinfo_current_state.sh
bash scripts/check_fasim_gasal2_scoreinfo_completion_gap.sh
bash scripts/check_fasim_gasal2_full_goal_decision.sh
git diff --check
```

Expected:

```text
ok
```

- [ ] **Step 5: Commit**

```bash
git add docs/fasim_gasal2_broad_path_architecture_gate.md \
  docs/fasim_gasal2_scoreinfo_current_state.md \
  docs/fasim_gasal2_scoreinfo_completion_gap.md \
  docs/fasim_gasal2_full_goal_decision.md \
  docs/superpowers/plans/2026-06-09-fasim-gasal2-emission-only-consumer-shadow.md \
  scripts/check_fasim_gasal2_scoreinfo_current_state.sh \
  scripts/check_fasim_gasal2_scoreinfo_completion_gap.sh \
  scripts/check_fasim_gasal2_full_goal_decision.sh
git commit -m "fasim: record emission-only consumer decision"
```

## Final Verification

Run:

```bash
make build-fasim-gasal2 FASIM_GASAL2_TARGET=$PWD/.tmp/fasim_longtarget_gasal2_direct
make check-fasim-gasal2-emission-only-consumer-shadow-plan
make check-fasim-gasal2-emission-only-consumer-shadow-env
make check-fasim-gasal2-emission-only-consumer-shadow-runtime-smoke
make check-fasim-gasal2-emission-only-consumer-neat1-first64-result
bash scripts/check_fasim_gasal2_scoreinfo_current_state.sh
bash scripts/check_fasim_gasal2_scoreinfo_completion_gap.sh
bash scripts/check_fasim_gasal2_full_goal_decision.sh
git diff --check
python3 - <<'PY'
import pathlib, subprocess
names = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], text=True).splitlines()
markers = ["\u202a", "\u202b", "\u202c", "\u202d", "\u202e", "\u2066", "\u2067", "\u2068", "\u2069"]
bad = []
for name in names:
    p = pathlib.Path(name)
    if p.is_file():
        text = p.read_text(encoding="utf-8", errors="ignore")
        if any(m in text for m in markers):
            bad.append(name)
if bad:
    print("\n".join(bad))
    raise SystemExit(1)
print("ok")
PY
```

## Completion Decision

Do not mark the full goal complete unless:

```text
NEAT1 first64 hard gate passes
at least one additional broad long-query workload passes
MALAT1 scoped product-readiness remains clean
default behavior remains unchanged
the implementation has a documented real opt-in path or a measured stop decision
```

If NEAT1 first64 fails any hard gate, update docs with a no-go result and keep the broad objective open or stop the GASAL2 broad line explicitly.
