# Fasim Current-Base Aligner Internal Decomposition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add telemetry-only decomposition for current-base `aligner.Align()` so we can tell whether score/end DP, reverse-start, CIGAR/traceback, setup, translation, or wrapper conversion dominates.

**Architecture:** Keep CPU `aligner.Align()` authoritative and add process-global SSW/Aligner counters emitted as existing `benchmark.fasim_*` stderr lines. The sharded runner already parses arbitrary `benchmark.fasim_*` keys; this plan only extends aggregation categories, smoke checks, and docs so per-shard/per-worker reports carry the new fields. No scoring, output, scheduler, GPU policy, or sharded merge semantics change.

**Tech Stack:** C++ Fasim telemetry in `fasim/Fasim-LongTarget.cpp`, `fasim/ssw_cpp.cpp`, `fasim/ssw_cpp.h`, `fasim/sswNew.cpp`, Python sharded runner telemetry aggregation, Bash/Python smoke checks, Markdown docs.

---

### Task 1: Add Failing Parser and Smoke Expectations

**Files:**
- Modify: `scripts/check_fasim_sharded_runner_telemetry_parser.py`
- Modify: `scripts/check_fasim_current_base_prealign_telemetry.sh`
- Modify: `scripts/check_fasim_sharded_runner_telemetry.sh`
- Modify: `scripts/fasim_sharded_runner.py`

- [x] **Step 1: Extend synthetic telemetry parser fixture**

Add these lines to the synthetic stderr fixture in
`scripts/check_fasim_sharded_runner_telemetry_parser.py`:

```text
benchmark.fasim_align_query_translate_seconds=0.010000
benchmark.fasim_align_ref_translate_seconds=0.020000
benchmark.fasim_align_profile_seconds=0.030000
benchmark.fasim_align_ssw_total_seconds=0.200000
benchmark.fasim_align_forward_score_end_seconds=0.110000
benchmark.fasim_align_reverse_start_seconds=0.040000
benchmark.fasim_align_traceback_seconds=0.050000
benchmark.fasim_align_convert_seconds=0.060000
benchmark.fasim_align_cleanup_seconds=0.005000
benchmark.fasim_align_calls=7
benchmark.fasim_align_byte_forward_calls=5
benchmark.fasim_align_word_forward_calls=2
benchmark.fasim_align_reverse_calls=7
benchmark.fasim_align_traceback_calls=7
benchmark.fasim_align_null_results=0
```

Assert parse and sum behavior:

```python
assert telemetry["fasim_align_forward_score_end_seconds"] == 0.11, telemetry
assert telemetry["fasim_align_traceback_seconds"] == 0.05, telemetry
assert telemetry["fasim_align_calls"] == 7, telemetry
assert telemetry["fasim_align_byte_forward_calls"] == 5, telemetry
assert summed["fasim_align_calls"] == 14, summed
assert summed["fasim_align_word_forward_calls"] == 4, summed
assert summed["fasim_align_traceback_seconds"] == 0.1, summed
```

- [x] **Step 2: Add runner count aggregation keys**

In `scripts/fasim_sharded_runner.py`, add these fields to `count_sum_keys`:

```python
"fasim_align_calls",
"fasim_align_byte_forward_calls",
"fasim_align_word_forward_calls",
"fasim_align_reverse_calls",
"fasim_align_traceback_calls",
"fasim_align_null_results",
```

Seconds fields already aggregate through the `_seconds` suffix.

- [x] **Step 3: Add e2e smoke field requirements**

In both smoke scripts, require the new `benchmark.fasim_align_*` fields with
numeric regexes. Use `[0-9]+` for counts and the existing seconds regex for
seconds.

- [x] **Step 4: Run red tests**

Run:

```bash
make check-fasim-sharded-runner-telemetry-parser
make check-fasim-current-base-prealign-telemetry
make check-fasim-sharded-runner-telemetry
```

Expected before implementation:

```text
parser check fails until aggregation keys exist
smoke checks fail because Fasim does not emit benchmark.fasim_align_* yet
```

### Task 2: Instrument `Aligner::Align()` Wrapper Phases

**Files:**
- Modify: `fasim/ssw_cpp.h`
- Modify: `fasim/ssw_cpp.cpp`

- [x] **Step 1: Add aligner telemetry API declarations**

In namespace `StripedSmithWaterman`, declare:

```cpp
struct AlignerTelemetryDelta {
    AlignerTelemetryDelta();
    long long alignCalls;
    double queryTranslateSeconds;
    double refTranslateSeconds;
    double profileSeconds;
    double sswTotalSeconds;
    double convertSeconds;
    double cleanupSeconds;
    long long nullResults;
};

void ResetAlignerTelemetry();
AlignerTelemetryDelta SnapshotAlignerTelemetry();
```

- [x] **Step 2: Add local timing helpers and process-global counters**

In `fasim/ssw_cpp.cpp`, add a file-local mutex and process-global
`AlignerTelemetryDelta`. Use `std::chrono::steady_clock` for wall seconds. Add
small helper functions to add deltas under the mutex.

- [x] **Step 3: Time `Aligner::Align(const char*, const char*, ...)`**

Record:

```text
alignCalls += 1 after passing initial validation
queryTranslateSeconds around TranslateBase(query)
refTranslateSeconds around TranslateBase(ref)
profileSeconds around ssw_init()
sswTotalSeconds around ssw_align()
convertSeconds around ConvertAlignment()
cleanupSeconds around delete[] / init_destroy / align_destroy
nullResults += 1 when ssw_align returns NULL
```

Do not change return values, alignment fields, memory ownership, or output.

- [x] **Step 4: Optionally time reference-sequence overload**

Apply the same query/profile/ssw/convert/cleanup/null result telemetry to
`Aligner::Align(const char*, const Filter&, ...)` so direct callers use the same
counter shape. There is no ref translation phase in this overload.

### Task 3: Instrument SSW Internal Phases

**Files:**
- Modify: `fasim/ssw.h`
- Modify: `fasim/sswNew.cpp`
- Modify: `fasim/ssw_cpp.cpp`
- Modify: `fasim/ssw_cpp.h`

- [x] **Step 1: Add C-compatible SSW telemetry functions**

In `fasim/ssw.h`, add:

```c
typedef struct {
    double forward_score_end_seconds;
    double reverse_start_seconds;
    double traceback_seconds;
    long long byte_forward_calls;
    long long word_forward_calls;
    long long reverse_calls;
    long long traceback_calls;
} ssw_telemetry_delta;

void ssw_reset_telemetry(void);
ssw_telemetry_delta ssw_snapshot_telemetry(void);
```

- [x] **Step 2: Implement SSW telemetry in `sswNew.cpp`**

Add file-local static counters and timing helpers. In `ssw_align()`:

```text
forward_score_end_seconds:
  time the forward sw_sse2_byte / sw_sse2_word calls that find score/end.

byte_forward_calls:
  increment when the forward byte path is called.

word_forward_calls:
  increment when the forward word path is called, including byte overflow fallback.

reverse_start_seconds:
  time read_reverse setup, reverse query profile build, reverse sw_sse2_* call, and reverse cleanup.

reverse_calls:
  increment when reverse-start recovery runs.

traceback_seconds:
  time banded_sw() and path ownership transfer/free.

traceback_calls:
  increment when banded_sw() is called.
```

Leave `ssw_pre_align()` unmodified for this PR because #147 showed the real
extension bottleneck is `aligner.Align()`, not preAlign.

- [x] **Step 3: Fold SSW snapshot into aligner snapshot**

In `ssw_cpp.cpp`, make `ResetAlignerTelemetry()` call `ssw_reset_telemetry()`.
Make `SnapshotAlignerTelemetry()` return wrapper counters plus SSW counters
converted to `AlignerTelemetryDelta` fields for forward/reverse/traceback and
path counts.

### Task 4: Emit and Document Telemetry

**Files:**
- Modify: `fasim/Fasim-LongTarget.cpp`
- Modify: `docs/fasim_current_base_cpu_extension_decomposition.md`
- Create: `docs/fasim_current_base_aligner_internal_decomposition.md`

- [x] **Step 1: Emit `benchmark.fasim_align_*` fields**

In `fasim_emit_runtime_telemetry()`, call
`StripedSmithWaterman::SnapshotAlignerTelemetry()` and emit:

```text
benchmark.fasim_align_query_translate_seconds
benchmark.fasim_align_ref_translate_seconds
benchmark.fasim_align_profile_seconds
benchmark.fasim_align_ssw_total_seconds
benchmark.fasim_align_forward_score_end_seconds
benchmark.fasim_align_reverse_start_seconds
benchmark.fasim_align_traceback_seconds
benchmark.fasim_align_convert_seconds
benchmark.fasim_align_cleanup_seconds
benchmark.fasim_align_calls
benchmark.fasim_align_byte_forward_calls
benchmark.fasim_align_word_forward_calls
benchmark.fasim_align_reverse_calls
benchmark.fasim_align_traceback_calls
benchmark.fasim_align_null_results
```

- [x] **Step 2: Document measurement boundaries**

Create `docs/fasim_current_base_aligner_internal_decomposition.md` explaining:

```text
current active GPU path remains FASIM_ENABLE_PREALIGN_CUDA
new fields are telemetry only
forward_score_end is the closest current proxy for score/end DP
reverse_start measures endpoint/start recovery
traceback_seconds measures banded_sw CIGAR generation
ConvertAlignment and wrapper translation/setup are outside ssw_align
seconds are summed across workers and can exceed wall time
```

State decision rules:

```text
if forward_score_end dominates: next PR can be score-only GPU shadow
if reverse_start dominates: endpoint/start shadow needs separate tie-policy gate
if traceback dominates: do not GPUize full output; consider CPU traceback optimization
if translation/profile dominates: consider query/ref/profile reuse
```

### Task 5: Verify, Characterize Smoke, and PR

**Files:**
- Modify: implementation, test, and docs files above

- [x] **Step 1: Run verification**

Run:

```bash
make build-fasim-cuda
make check-fasim-sharded-runner-telemetry-parser
make check-fasim-current-base-prealign-telemetry
make check-fasim-sharded-runner-telemetry
python3 -m py_compile scripts/fasim_sharded_runner.py scripts/check_fasim_sharded_runner_telemetry_parser.py
git diff --check
```

- [x] **Step 2: Capture smoke signal**

Inspect `.tmp/check_fasim_current_base_prealign_telemetry/on/stderr.log` and
record a small smoke table in the new doc:

```text
fasim_align_calls
fasim_align_forward_score_end_seconds
fasim_align_reverse_start_seconds
fasim_align_traceback_seconds
fasim_align_query_translate_seconds
fasim_align_ref_translate_seconds
fasim_align_profile_seconds
fasim_align_convert_seconds
```

- [x] **Step 3: Commit and PR**

Commit:

```bash
git add fasim/ssw.h fasim/ssw_cpp.h fasim/ssw_cpp.cpp fasim/sswNew.cpp fasim/Fasim-LongTarget.cpp scripts/fasim_sharded_runner.py scripts/check_fasim_sharded_runner_telemetry_parser.py scripts/check_fasim_current_base_prealign_telemetry.sh scripts/check_fasim_sharded_runner_telemetry.sh docs/fasim_current_base_aligner_internal_decomposition.md docs/fasim_current_base_cpu_extension_decomposition.md docs/superpowers/plans/2026-05-26-fasim-current-base-aligner-internal-decomposition.md
git commit -m "fasim: decompose current-base aligner internals"
```

Open PR against `cuda-p0.2-initial-handoff-pipeline`.
