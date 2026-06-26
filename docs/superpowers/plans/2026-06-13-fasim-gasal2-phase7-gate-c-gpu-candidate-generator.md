# Fasim GASAL2 Phase 7 Gate C GPU Candidate Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a default-off Gate C prototype that tests whether a GPU/GASAL2 candidate descriptor generator can reduce or replace CPU scoreInfo/preAlign work while preserving the all-attempt early-stop output contract.

**Architecture:** Gate C is a shadow path. GPU/GASAL2 may generate candidate descriptors, but CPU `aligner.Align()` remains authority for score/end replay, CIGAR/traceback, row construction, output, and digest. The implementation must prove coverage before any candidate reduction and must stop before broad promotion unless NEAT1 first64 passes the full broad gate.

**Tech Stack:** Fasim C++ runtime, existing GASAL2 bridge, GASAL2 telemetry structs, shell characterization scripts, Python TSV/result parsers, Makefile roadmap gates.

---

```text
phase7_gate_c_gpu_candidate_generator_implementation_plan = defined
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Source Design

Use [docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md](/data/wenyujianData/LongTarget-exact-sim/docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md) as the controlling design.

Hard invariants:

```text
FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES=1
default-off shadow path
CPU aligner.Align() remains authority
GASAL2 output authority = 0
no GPU endpoint authority
no GPU CIGAR or traceback authority
no real opt-in
workload matrix broad_replacement row is forbidden until Gate C first64 passes
```

## Files

- Modify: `fasim/gasal2_align_bridge.h`
- Modify: `fasim/gasal2_align_bridge.cpp`
- Modify: `fasim/gasal2_align_bridge_stub.cpp`
- Modify: `fasim/Fasim-LongTarget.cpp`
- Create: `scripts/check_fasim_gasal2_phase7_gate_c_env.sh`
- Create: `scripts/check_fasim_gasal2_phase7_gate_c_runtime_smoke.sh`
- Create: `scripts/characterize_fasim_gasal2_phase7_gate_c_first1.sh`
- Create: `scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh`
- Create: `scripts/characterize_fasim_gasal2_phase7_gate_c_first64.sh`
- Create: `scripts/check_fasim_gasal2_phase7_gate_c_first64_result.sh`
- Create: `scripts/check_fasim_gasal2_roadmap_phase7_gate_c_first1.sh`
- Create: `scripts/check_fasim_gasal2_roadmap_phase7_gate_c_first64.sh`
- Modify: `Makefile`
- Modify: `docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md`
- Modify: `docs/fasim_gasal2_goal_completion_roadmap.md`
- Modify: `docs/fasim_gasal2_goal_completion_phase_plan.md`
- Modify: `scripts/summarize_fasim_gasal2_roadmap_current_state.py`
- Modify: `scripts/check_fasim_gasal2_roadmap_current_state.sh`

## Task 1: Gate C Env And Telemetry

**Files:**
- Create: `scripts/check_fasim_gasal2_phase7_gate_c_env.sh`
- Modify: `fasim/gasal2_align_bridge.h`
- Modify: `fasim/gasal2_align_bridge.cpp`
- Modify: `fasim/gasal2_align_bridge_stub.cpp`
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `Makefile`

- [x] **Step 1: Write the failing env checker**

Create `scripts/check_fasim_gasal2_phase7_gate_c_env.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPP="$ROOT/fasim/Fasim-LongTarget.cpp"
HDR="$ROOT/fasim/gasal2_align_bridge.h"
IMPL="$ROOT/fasim/gasal2_align_bridge.cpp"
STUB="$ROOT/fasim/gasal2_align_bridge_stub.cpp"
MAKEFILE="$ROOT/Makefile"

python3 - "$CPP" "$HDR" "$IMPL" "$STUB" "$MAKEFILE" <<'PY'
from pathlib import Path
import sys

cpp = Path(sys.argv[1]).read_text(encoding="utf-8")
hdr = Path(sys.argv[2]).read_text(encoding="utf-8")
impl = Path(sys.argv[3]).read_text(encoding="utf-8")
stub = Path(sys.argv[4]).read_text(encoding="utf-8")
makefile = Path(sys.argv[5]).read_text(encoding="utf-8")

required_cpp = [
    "FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES",
    "fasim_gasal2_phase7_gate_c_gpu_candidates_runtime",
]
for needle in required_cpp:
    if needle not in cpp:
        raise SystemExit(f"missing Gate C runtime marker: {needle}")

required_stats = [
    "phase7_gate_c_requested",
    "phase7_gate_c_active",
    "phase7_gate_c_tasks",
    "phase7_gate_c_oracle_scoreinfos",
    "phase7_gate_c_oracle_attempts",
    "phase7_gate_c_gpu_candidate_scoreinfos",
    "phase7_gate_c_gpu_candidate_attempts",
    "phase7_gate_c_false_negative_scoreinfos",
    "phase7_gate_c_missing_required_attempts",
    "phase7_gate_c_extra_candidate_attempts",
    "phase7_gate_c_candidate_align_attempts",
    "phase7_gate_c_gate_b_candidate_align_attempts",
    "phase7_gate_c_scoreinfo_cpu_seconds",
    "phase7_gate_c_gpu_candidate_seconds",
    "phase7_gate_c_cpu_replay_seconds",
    "phase7_gate_c_total_seconds",
    "phase7_gate_c_digest_match",
    "phase7_gate_c_full_rows_equal",
]
for needle in required_stats:
    if needle not in hdr or needle not in impl or needle not in stub:
        raise SystemExit(f"missing Gate C telemetry marker: {needle}")

if "check-fasim-gasal2-phase7-gate-c-env:" not in makefile:
    raise SystemExit("missing Makefile Gate C env target")

print("phase7_gate_c_env=pass")
print("ok")
PY
```

- [x] **Step 2: Run the checker and verify RED**

Run:

```bash
bash scripts/check_fasim_gasal2_phase7_gate_c_env.sh
```

Expected: FAIL with missing `FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES`.

- [x] **Step 3: Add the default-off env helper**

Add to `fasim/Fasim-LongTarget.cpp` near the Phase 7 env helpers:

```cpp
static inline bool fasim_gasal2_phase7_gate_c_gpu_candidates_runtime()
{
	return fasim_env_flag_enabled(
		"FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES");
}
```

- [x] **Step 4: Add Gate C telemetry fields**

Add fields to `FasimGasal2Stats` in `fasim/gasal2_align_bridge.h`:

```cpp
uint64_t phase7_gate_c_requested;
uint64_t phase7_gate_c_active;
uint64_t phase7_gate_c_tasks;
uint64_t phase7_gate_c_oracle_scoreinfos;
uint64_t phase7_gate_c_oracle_attempts;
uint64_t phase7_gate_c_gpu_candidate_scoreinfos;
uint64_t phase7_gate_c_gpu_candidate_attempts;
uint64_t phase7_gate_c_false_negative_scoreinfos;
uint64_t phase7_gate_c_missing_required_attempts;
uint64_t phase7_gate_c_extra_candidate_attempts;
uint64_t phase7_gate_c_candidate_align_attempts;
uint64_t phase7_gate_c_gate_b_candidate_align_attempts;
double phase7_gate_c_scoreinfo_cpu_seconds;
double phase7_gate_c_gpu_candidate_seconds;
double phase7_gate_c_cpu_replay_seconds;
double phase7_gate_c_total_seconds;
uint64_t phase7_gate_c_digest_match;
uint64_t phase7_gate_c_full_rows_equal;
```

Initialize them to zero in the `FasimGasal2Stats` constructor.

- [x] **Step 5: Add the telemetry recorder signature**

Add to `fasim/gasal2_align_bridge.h`:

```cpp
void fasim_gasal2_record_phase7_gate_c(
	uint64_t tasks,
	uint64_t oracleScoreInfos,
	uint64_t oracleAttempts,
	uint64_t gpuCandidateScoreInfos,
	uint64_t gpuCandidateAttempts,
	uint64_t falseNegativeScoreInfos,
	uint64_t missingRequiredAttempts,
	uint64_t extraCandidateAttempts,
	uint64_t candidateAlignAttempts,
	uint64_t gateBCandidateAlignAttempts,
	double scoreInfoCpuSeconds,
	double gpuCandidateSeconds,
	double cpuReplaySeconds,
	double totalSeconds,
	uint64_t digestMatch,
	uint64_t fullRowsEqual,
	bool active);
```

- [x] **Step 6: Implement telemetry printing and stub output**

In `fasim/gasal2_align_bridge.cpp`, print metrics as:

```cpp
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_requested=" << stats.phase7_gate_c_requested << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_active=" << stats.phase7_gate_c_active << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_tasks=" << stats.phase7_gate_c_tasks << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_oracle_scoreinfos=" << stats.phase7_gate_c_oracle_scoreinfos << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_oracle_attempts=" << stats.phase7_gate_c_oracle_attempts << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_gpu_candidate_scoreinfos=" << stats.phase7_gate_c_gpu_candidate_scoreinfos << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_gpu_candidate_attempts=" << stats.phase7_gate_c_gpu_candidate_attempts << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_false_negative_scoreinfos=" << stats.phase7_gate_c_false_negative_scoreinfos << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_missing_required_attempts=" << stats.phase7_gate_c_missing_required_attempts << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_extra_candidate_attempts=" << stats.phase7_gate_c_extra_candidate_attempts << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_candidate_align_attempts=" << stats.phase7_gate_c_candidate_align_attempts << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_gate_b_candidate_align_attempts=" << stats.phase7_gate_c_gate_b_candidate_align_attempts << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_scoreinfo_cpu_seconds=" << stats.phase7_gate_c_scoreinfo_cpu_seconds << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_gpu_candidate_seconds=" << stats.phase7_gate_c_gpu_candidate_seconds << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_cpu_replay_seconds=" << stats.phase7_gate_c_cpu_replay_seconds << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_total_seconds=" << stats.phase7_gate_c_total_seconds << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_digest_match=" << stats.phase7_gate_c_digest_match << "\n";
std::cerr << "benchmark.fasim_gasal2_phase7_gate_c_full_rows_equal=" << stats.phase7_gate_c_full_rows_equal << "\n";
```

In `fasim/gasal2_align_bridge_stub.cpp`, print the same metrics with zero
values and add a no-op `fasim_gasal2_record_phase7_gate_c` function.

- [x] **Step 7: Add Makefile target and verify GREEN**

Add to `Makefile`:

```make
check-fasim-gasal2-phase7-gate-c-env:
	bash ./scripts/check_fasim_gasal2_phase7_gate_c_env.sh

.PHONY: check-fasim-gasal2-phase7-gate-c-env
```

Run:

```bash
make check-fasim-gasal2-phase7-gate-c-env
```

Expected: PASS and print `phase7_gate_c_env=pass`.

## Task 2: Oracle Frontier Export Reuse

**Files:**
- Create: `scripts/check_fasim_gasal2_phase7_gate_c_runtime_smoke.sh`
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `Makefile`

- [x] **Step 1: Write the failing runtime smoke**

Create `scripts/check_fasim_gasal2_phase7_gate_c_runtime_smoke.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/check_fasim_gasal2_phase7_gate_c_runtime_smoke"}"

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/baseline" "$WORK/candidate"

cat >"$WORK/inputs/query.fa" <<'EOF'
>phase7_gate_c_query
ACGTACGTACGTACGTACGTACGTACGTACGT
EOF
cat >"$WORK/inputs/target.fa" <<'EOF'
>phase7_gate_c_target
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
EOF

run_case() {
  local out_dir="$1"
  shift
  env \
    FASIM_ALIGN_GASAL2=1 \
    FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
    FASIM_OUTPUT_MODE=lite \
    FASIM_VERBOSE=0 \
    "$@" \
    "$BIN" \
    -f1 "$WORK/inputs/target.fa" \
    -f2 "$WORK/inputs/query.fa" \
    -r 0 \
    -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case "$WORK/baseline"
run_case "$WORK/candidate" FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES=1

python3 - "$WORK/baseline/stderr.log" "$WORK/candidate/stderr.log" <<'PY'
from pathlib import Path
import sys

base = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
candidate = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
prefix = "benchmark.fasim_gasal2_phase7_gate_c_"

def value(text: str, suffix: str) -> str:
    needle = prefix + suffix + "="
    for line in text.splitlines():
        if line.startswith(needle):
            return line.split("=", 1)[1]
    raise SystemExit(f"missing metric: {needle}")

if value(base, "requested") != "0" or value(base, "active") != "0":
    raise SystemExit("Gate C must be default-off")
if value(candidate, "requested") != "1":
    raise SystemExit("Gate C env did not request path")
if int(value(candidate, "oracle_attempts")) <= 0:
    raise SystemExit("Gate C smoke must record oracle attempts")
print("phase7_gate_c_runtime_smoke=pass")
print("ok")
PY
```

- [x] **Step 2: Verify RED**

Run:

```bash
bash scripts/check_fasim_gasal2_phase7_gate_c_runtime_smoke.sh
```

Expected: FAIL because `phase7_gate_c_requested` remains zero.

- [x] **Step 3: Wire Gate C to all-attempt oracle**

In `extend_tasks_with_gasal2_batch`, compute:

```cpp
const bool phase7GateCGpuCandidatesRequested =
	fasim_gasal2_phase7_gate_c_gpu_candidates_runtime();
```

For the first smoke, reuse the all-attempt early-stop oracle stream:

```cpp
const bool gateCOracleOnly =
	phase7GateCGpuCandidatesRequested &&
	phase7AllAttemptEarlyStopRequested;
```

If `phase7GateCGpuCandidatesRequested` is set without all-attempt replay
support, record `requested=1`, `active=0`, and leave output unchanged.

- [x] **Step 4: Record oracle-only telemetry**

When the all-attempt early-stop path computes `gasalAttempts`, `scoreGroups`,
and `cpuTracebackAlignCalls`, call:

```cpp
fasim_gasal2_record_phase7_gate_c(
	static_cast<uint64_t>(tasks.size()),
	static_cast<uint64_t>(scoreGroups.size()),
	static_cast<uint64_t>(gasalAttempts.size()),
	0,
	0,
	0,
	0,
	0,
	cpuTracebackAlignCalls,
	140087,
	0.0,
	0.0,
	cpuTracebackReplaySeconds,
	cpuTracebackReplaySeconds,
	0,
	0,
	useCpuTracebackReplay);
```

For small smoke, `gate_b_candidate_align_attempts` may be zero if no Gate B
reference applies. For NEAT1 characterization, use `140087` as the Gate B
first64 reference in result scripts, not as a hard-coded runtime correctness
claim.

- [x] **Step 5: Add Makefile target and verify GREEN**

Add:

```make
check-fasim-gasal2-phase7-gate-c-runtime-smoke:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/check_fasim_gasal2_phase7_gate_c_runtime_smoke.sh

.PHONY: check-fasim-gasal2-phase7-gate-c-runtime-smoke
```

Run:

```bash
make check-fasim-gasal2-phase7-gate-c-runtime-smoke
```

Expected: PASS and print `phase7_gate_c_runtime_smoke=pass`.

## Task 3: GPU Candidate Descriptor Shadow

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Create: `scripts/characterize_fasim_gasal2_phase7_gate_c_first1.sh`
- Create: `scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh`

- [x] **Step 1: Write the first1 result checker**

Create `scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="${REPORT:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_gate_c_first1/report.tsv"}"

if [[ ! -s "$REPORT" ]]; then
  echo "missing Gate C first1 report: $REPORT" >&2
  exit 1
fi

python3 - "$REPORT" <<'PY'
from pathlib import Path
import csv
import sys

rows = list(csv.DictReader(Path(sys.argv[1]).open(newline="", encoding="utf-8"), delimiter="\t"))
row = next((r for r in rows if r.get("workload") == "neat1_first1"), None)
if row is None:
    raise SystemExit("missing neat1_first1 row")

required = [
    "attempted",
    "digest_match",
    "full_rows_equal",
    "missing_rows",
    "extra_rows",
    "triplex_mismatches",
    "false_negative_scoreinfos",
    "candidate_align_attempts",
    "gate_b_candidate_align_attempts",
    "scoreinfo_reduced",
    "decision",
]
for key in required:
    if key not in row:
        raise SystemExit(f"missing column: {key}")

if row["attempted"] != "1":
    raise SystemExit("first1 was not attempted")
if row["decision"] == "phase7_gate_c_first1_go":
    if row["digest_match"] != "1" and row["full_rows_equal"] != "1":
        raise SystemExit("go requires digest or row equality")
    for key in ["missing_rows", "extra_rows", "triplex_mismatches", "false_negative_scoreinfos"]:
        if row[key] != "0":
            raise SystemExit(f"go requires {key}=0")
    if int(row["candidate_align_attempts"]) > int(row["gate_b_candidate_align_attempts"]):
        raise SystemExit("go requires candidate attempts <= Gate B")
    if row["scoreinfo_reduced"] != "1":
        raise SystemExit("go requires scoreInfo/preAlign reduction")

print("phase7_gate_c_first1_result=pass")
print("phase7_gate_c_first1_decision=" + row["decision"])
print("phase7_gate_c_first1_broad_gate_pass=0")
print("broad_objective_status=open")
print("must_not_call_update_goal_complete=1")
print("ok")
PY
```

- [x] **Step 2: Verify RED**

Run:

```bash
bash scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh
```

Expected: FAIL with missing report.

- [x] **Step 3: Implement descriptor shadow source**

Inside the Gate C path, create two vectors:

```cpp
std::vector<FasimGasal2Attempt> gateCOracleAttempts = gasalAttempts;
std::vector<FasimGasal2Attempt> gateCGpuCandidateAttempts;
```

For the first implementation, populate `gateCGpuCandidateAttempts` from the
existing GASAL2 or segmented GPU candidate generator if available. If the GPU
candidate generator cannot run for the query shape, leave it empty and record a
no-go decision in the characterization script.

Do not use `gateCGpuCandidateAttempts` for output until coverage comparison
passes.

- [x] **Step 4: Write first1 characterization script**

Create `scripts/characterize_fasim_gasal2_phase7_gate_c_first1.sh` that:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${BIN:-"$ROOT/.tmp/fasim_longtarget_gasal2_direct"}"
WORK="${WORK:-"$ROOT/.tmp/characterize_fasim_gasal2_phase7_gate_c_first1"}"
RNA_INPUT="${NEAT1_RNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1.fa"}"
DNA_INPUT="${NEAT1_DNA:-"$ROOT/.tmp/Fasim-LongTarget/example/NEAT1/NEAT1-DNAseq.fa"}"

make -C "$ROOT" build-fasim-gasal2 FASIM_GASAL2_TARGET="$BIN"
rm -rf "$WORK"
mkdir -p "$WORK/inputs" "$WORK/baseline" "$WORK/candidate"
awk 'BEGIN{n=0} /^>/{++n} n<=1{print}' "$DNA_INPUT" >"$WORK/inputs/neat1_first1.fa"

run_case() {
  local out_dir="$1"
  shift
  env FASIM_OUTPUT_MODE=lite FASIM_VERBOSE=0 "$@" "$BIN" \
    -f1 "$WORK/inputs/neat1_first1.fa" \
    -f2 "$RNA_INPUT" \
    -r 0 \
    -O "$out_dir" \
    >"$out_dir/stdout.log" 2>"$out_dir/stderr.log"
}

run_case "$WORK/baseline"
run_case "$WORK/candidate" \
  FASIM_ALIGN_GASAL2=1 \
  FASIM_ALIGN_GASAL2_LONGTARGET_BRIDGE=1 \
  FASIM_GASAL2_PHASE7_ALL_ATTEMPT_EARLY_STOP=1 \
  FASIM_GASAL2_PHASE7_GATE_C_GPU_CANDIDATES=1

python3 "$ROOT/scripts/parse_fasim_gasal2_phase7_gate_c_result.py" \
  --workload neat1_first1 \
  --gate-b-candidate-align-attempts 2008 \
  --baseline-dir "$WORK/baseline" \
  --candidate-dir "$WORK/candidate" \
  --report "$WORK/report.tsv"
cat "$WORK/report.tsv"
```

If no shared parser exists yet, implement the parser inline in this script
using the same row-set comparison pattern used by
`scripts/characterize_fasim_gasal2_phase7_all_attempt_early_stop_runtime.sh`.

- [x] **Step 5: Verify first1 checker passes**

Run:

```bash
bash scripts/characterize_fasim_gasal2_phase7_gate_c_first1.sh
bash scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh
```

Expected: PASS. A `no_go` decision is acceptable if it records why Gate C
failed; a broad completion claim is not acceptable.

## Task 4: Coverage Comparison Gate

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh`

- [ ] **Step 1: Extend first1 checker for coverage**

Add required columns to `scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh`:

```python
coverage_columns = [
    "oracle_scoreinfos",
    "oracle_attempts",
    "gpu_candidate_scoreinfos",
    "gpu_candidate_attempts",
    "missing_required_attempts",
    "extra_candidate_attempts",
]
for key in coverage_columns:
    if key not in row:
        raise SystemExit(f"missing coverage column: {key}")
```

- [ ] **Step 2: Verify RED**

Run:

```bash
bash scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh
```

Expected: FAIL until the characterization report includes coverage columns.

- [ ] **Step 3: Implement coverage comparison**

Compare the required selected frontier keys against GPU candidate keys using:

```cpp
struct GateCKey {
	int taskIndex;
	int scoreInfoIndex;
	int start;
	int cutlength;
};
```

Build sorted vectors of `GateCKey` for oracle-required attempts and GPU
candidate attempts. Count:

```text
missing_required_attempts
extra_candidate_attempts
false_negative_scoreinfos
```

The Gate C path may proceed to CPU replay only when:

```text
false_negative_scoreinfos = 0
missing_required_attempts = 0
```

- [ ] **Step 4: Verify coverage report passes parser**

Run:

```bash
bash scripts/characterize_fasim_gasal2_phase7_gate_c_first1.sh
bash scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh
```

Expected: PASS with either `phase7_gate_c_first1_go` or
`phase7_gate_c_first1_no_go`.

## Task 5: CPU-Authority Replay Gate

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `scripts/characterize_fasim_gasal2_phase7_gate_c_first1.sh`
- Modify: `scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh`
- Modify: `Makefile`

- [ ] **Step 1: Require CPU replay authority in first1 report**

Add columns:

```text
cpu_aligner_align_authority
gasal2_output_authority
gpu_endpoint_authority
gpu_cigar_traceback_authority
```

Checker values:

```text
cpu_aligner_align_authority = 1
gasal2_output_authority = 0
gpu_endpoint_authority = 0
gpu_cigar_traceback_authority = 0
```

- [ ] **Step 2: Verify RED**

Run:

```bash
bash scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh
```

Expected: FAIL until authority columns are present.

- [ ] **Step 3: Replay covered GPU candidates through CPU Align**

When coverage passes, construct replay-selected candidates from
`gateCGpuCandidateAttempts` and reuse the existing CPU traceback replay logic.
Do not call GASAL2 traceback. Do not use GPU endpoints. Do not alter row
construction outside the default-off Gate C path.

- [ ] **Step 4: Add Makefile first1 target**

Add:

```make
characterize-fasim-gasal2-phase7-gate-c-first1:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_phase7_gate_c_first1.sh

.PHONY: characterize-fasim-gasal2-phase7-gate-c-first1

check-fasim-gasal2-phase7-gate-c-first1-result:
	bash ./scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh

.PHONY: check-fasim-gasal2-phase7-gate-c-first1-result
```

- [ ] **Step 5: Verify first1 runtime gate**

Run:

```bash
make characterize-fasim-gasal2-phase7-gate-c-first1
make check-fasim-gasal2-phase7-gate-c-first1-result
```

Expected: PASS. If decision is no-go, stop before first64 and update docs.

## Task 6: NEAT1 first64 Broad Characterization

**Files:**
- Create: `scripts/characterize_fasim_gasal2_phase7_gate_c_first64.sh`
- Create: `scripts/check_fasim_gasal2_phase7_gate_c_first64_result.sh`
- Create: `scripts/check_fasim_gasal2_roadmap_phase7_gate_c_first64.sh`
- Modify: `Makefile`

- [ ] **Step 1: Write first64 result checker**

Create `scripts/check_fasim_gasal2_phase7_gate_c_first64_result.sh` mirroring
the first1 checker with `workload == neat1_first64` and
`gate_b_candidate_align_attempts == 140087`.

The `go` decision requires:

```text
digest_match = 1 or full_rows_equal = 1
missing_rows = 0
extra_rows = 0
triplex_mismatches = 0
false_negative_scoreinfos = 0
candidate_align_attempts <= 140087
candidate_vs_baseline > 1.0
scoreinfo_reduced = 1
cpu_aligner_align_authority = 1
gasal2_output_authority = 0
gpu_endpoint_authority = 0
gpu_cigar_traceback_authority = 0
```

- [ ] **Step 2: Verify RED**

Run:

```bash
bash scripts/check_fasim_gasal2_phase7_gate_c_first64_result.sh
```

Expected: FAIL with missing report.

- [ ] **Step 3: Write first64 characterization**

Create `scripts/characterize_fasim_gasal2_phase7_gate_c_first64.sh` from the
first1 script with:

```text
record limit = 64
workload = neat1_first64
gate_b_candidate_align_attempts = 140087
```

- [ ] **Step 4: Add Makefile targets**

Add:

```make
characterize-fasim-gasal2-phase7-gate-c-first64:
	$(MAKE) build-fasim-gasal2 FASIM_GASAL2_TARGET=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct
	BIN=$(CURDIR)/.tmp/fasim_longtarget_gasal2_direct bash ./scripts/characterize_fasim_gasal2_phase7_gate_c_first64.sh

.PHONY: characterize-fasim-gasal2-phase7-gate-c-first64

check-fasim-gasal2-phase7-gate-c-first64-result:
	bash ./scripts/check_fasim_gasal2_phase7_gate_c_first64_result.sh

.PHONY: check-fasim-gasal2-phase7-gate-c-first64-result
```

- [ ] **Step 5: Run first64 gate only if first1 passed**

Run:

```bash
make characterize-fasim-gasal2-phase7-gate-c-first64
make check-fasim-gasal2-phase7-gate-c-first64-result
```

Expected: PASS. A no-go decision must keep:

```text
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

## Task 7: Roadmap And Matrix Decision

**Files:**
- Create: `scripts/check_fasim_gasal2_roadmap_phase7_gate_c_first1.sh`
- Create: `scripts/check_fasim_gasal2_roadmap_phase7_gate_c_first64.sh`
- Modify: `docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md`
- Modify: `docs/fasim_gasal2_goal_completion_roadmap.md`
- Modify: `docs/fasim_gasal2_goal_completion_phase_plan.md`
- Modify: `docs/fasim_gasal2_workload_matrix.tsv`
- Modify: `scripts/summarize_fasim_gasal2_roadmap_current_state.py`
- Modify: `scripts/check_fasim_gasal2_roadmap_current_state.sh`
- Modify: `Makefile`

- [ ] **Step 1: Write roadmap first1 checker**

Create `scripts/check_fasim_gasal2_roadmap_phase7_gate_c_first1.sh` that
requires:

```text
phase7_gate_c_first1 = go
or
phase7_gate_c_first1 = no_go
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

- [ ] **Step 2: Write roadmap first64 checker**

Create `scripts/check_fasim_gasal2_roadmap_phase7_gate_c_first64.sh` that
requires:

```text
phase7_gate_c_first64 = go
or
phase7_gate_c_first64 = no_go
```

If `phase7_gate_c_first64 = go`, require a workload matrix row:

```text
contract = broad_replacement
row_equal = true
speedup > 1.0
fallbacks = 0
scoreinfo_reduced = true
align_side_reduced = true
```

If `phase7_gate_c_first64 = no_go`, require:

```text
workload matrix broad_replacement row is forbidden until Gate C first64 passes
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

- [ ] **Step 3: Update docs from measured evidence**

Update:

```text
docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md
docs/fasim_gasal2_goal_completion_roadmap.md
docs/fasim_gasal2_goal_completion_phase_plan.md
```

Record exact first1 and first64 decisions, including:

```text
digest_match
full_rows_equal
missing_rows
extra_rows
triplex_mismatches
false_negative_scoreinfos
candidate_align_attempts
gate_b_candidate_align_attempts
candidate_vs_baseline
scoreinfo_reduced
decision
decision_reasons
```

- [ ] **Step 4: Update current-state summary**

Add output keys:

```text
phase7_gate_c_first1
phase7_gate_c_first64
phase7_gate_c_broad_gate_pass
```

Keep:

```text
broad_objective_status = open
must_not_call_update_goal_complete = 1
```

until a broad replacement row exists and Phase 8 passes.

- [ ] **Step 5: Verify roadmap gates**

Run:

```bash
make check-fasim-gasal2-roadmap-phase7-gate-c-gpu-candidate-generator-design
make check-fasim-gasal2-roadmap-current-state
```

Expected: PASS. If Gate C first64 is no-go, current-state must still print
`broad_objective_status=open`.

- [ ] **Step 6: Final hygiene**

Run:

```bash
git diff --check
bash -n \
  scripts/check_fasim_gasal2_phase7_gate_c_env.sh \
  scripts/check_fasim_gasal2_phase7_gate_c_runtime_smoke.sh \
  scripts/characterize_fasim_gasal2_phase7_gate_c_first1.sh \
  scripts/check_fasim_gasal2_phase7_gate_c_first1_result.sh \
  scripts/characterize_fasim_gasal2_phase7_gate_c_first64.sh \
  scripts/check_fasim_gasal2_phase7_gate_c_first64_result.sh \
  scripts/check_fasim_gasal2_roadmap_phase7_gate_c_first1.sh \
  scripts/check_fasim_gasal2_roadmap_phase7_gate_c_first64.sh
python3 -m py_compile scripts/summarize_fasim_gasal2_roadmap_current_state.py
```

Run changed-file bidi scan:

```bash
grep -nP '[\x{202A}-\x{202E}\x{2066}-\x{2069}]' \
  Makefile \
  fasim/Fasim-LongTarget.cpp \
  fasim/gasal2_align_bridge.cpp \
  fasim/gasal2_align_bridge.h \
  fasim/gasal2_align_bridge_stub.cpp \
  docs/fasim_gasal2_phase7_gate_c_gpu_candidate_generator_design.md \
  docs/fasim_gasal2_goal_completion_roadmap.md \
  docs/fasim_gasal2_goal_completion_phase_plan.md \
  scripts/*.sh \
  scripts/*.py
```

Expected: no matches.

## Completion Rules

Do not mark the active goal complete after this implementation plan. Runtime
prototype execution is still required.

Path B completion remains blocked until:

```text
NEAT1 first64 broad gate passes
workload matrix contains a passing broad_replacement row
Phase 8 completion decision passes
```

Until then:

```text
broad_gate_pass = 0
broad_objective_status = open
must_not_call_update_goal_complete = 1
```
