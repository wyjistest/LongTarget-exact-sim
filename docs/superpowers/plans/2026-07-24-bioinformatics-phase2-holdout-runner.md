# Bioinformatics Phase 2 Holdout Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and freeze a resumable, failure-preserving runner for the preregistered 24-workload/36-attempt Phase 2 holdout without executing a pilot or formal holdout attempt during implementation.

**Architecture:** A dedicated Python orchestrator validates the committed freeze, expands deterministic attempt IDs, and exposes mutually exclusive plan-only, pilot, and formal modes. Each attempt runs the existing contract-aware CLI in CPU-authority, fast-experimental, and verified modes; independently compares the two raw TFOsorted artifacts with the frozen comparator; measures resources with the existing paper GPU sampler and `/usr/bin/time`; publishes an immutable receipt directory; and rebuilds derived tables from receipts. The pilot has a fixed preregistered identity and a separate artifact namespace, and formal execution refuses to start without its receipt.

**Tech Stack:** Python 3 standard library, existing `scripts/gasal2_longtarget.py`, existing `scripts/compare_fasim_segmented_contract.py`, existing paper GPU sampler and environment capture helpers, `unittest`, TSV/JSON/SHA-256 receipts, GNU Make.

---

### Task 1: Freeze the execution supplement and deterministic plan

**Files:**
- Create: `paper/bioinformatics/holdout_execution_protocol.md`
- Create: `reproduce/bioinformatics/run_holdout.py`
- Create: `tests/check_run_bioinformatics_holdout.py`

- [ ] **Step 1: Write failing plan and protocol tests**

Add tests that load the runner module and assert:

```python
plan = module.build_plan(ROOT / "paper/bioinformatics/holdout_manifest.tsv")
self.assertEqual(plan["freeze_id"], "bioinformatics-phase2-holdout-v1-9e293b2c")
self.assertEqual(plan["manifest_sha256"], "9e293b2c3e8d0462e399fe64ff6f684e9c53f7dd428e9c88265b510909cee8c6")
self.assertEqual(plan["workload_count"], 24)
self.assertEqual(plan["formal_attempt_count"], 36)
self.assertEqual(plan["top_level_run_count"], 108)
self.assertEqual(plan["backend_execution_count"], 144)
self.assertEqual(plan["pilot"]["attempt_id"], "pilot__hq01_ht01__repeat00")
self.assertEqual(len({row["attempt_id"] for row in plan["formal_attempts"]}), 36)
```

The subprocess `--plan-only` test must be byte-deterministic, must not create the artifact root, and must reject manifest digest drift, duplicate/missing workload Cartesian pairs, changed repeat counts, a non-`preregistered_not_run` status, and any query/target checksum drift.

The protocol test must require the following exact rules:

```text
pilot workload = hq01_ht01
pilot is excluded from formal source data
no automatic or replacement retry
later supplemental retries are additive and cannot replace a primary attempt
formal execution requires a checksum-valid pilot receipt
runtime parameters may not change after pilot or holdout results
all technical failures, mismatches, fallback, OOM and timeout outcomes remain represented
```

- [ ] **Step 2: Run the plan tests and verify RED**

Run:

```bash
python3 tests/check_run_bioinformatics_holdout.py
```

Expected: FAIL because `run_holdout.py`, `build_plan()`, and the execution supplement do not exist.

- [ ] **Step 3: Implement strict freeze validation and plan expansion**

Implement constants and a strict loader:

```python
FREEZE_ID = "bioinformatics-phase2-holdout-v1-9e293b2c"
MANIFEST_SHA256 = "9e293b2c3e8d0462e399fe64ff6f684e9c53f7dd428e9c88265b510909cee8c6"
PILOT_WORKLOAD_ID = "hq01_ht01"
FORMAL_STATUS = "preregistered_not_run"
MODES = ("cpu-authority", "fast-experimental", "verified")
```

Resolve manifest paths relative to the repository root, verify query and target file SHA-256 values, enforce 24 unique query-target workload IDs, enforce the exact 12-by-2 Cartesian panel, and expand repeats in manifest order. Formal attempt IDs are `<workload_id>__repeatNN`; the pilot ID is fixed and lives outside the formal list. Report input base counts and conservative maximum backend wall time from the frozen attempt expansion.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run `python3 tests/check_run_bioinformatics_holdout.py` and confirm all plan/protocol tests pass.

### Task 2: Add measured, immutable single-attempt execution

**Files:**
- Modify: `reproduce/bioinformatics/run_holdout.py`
- Modify: `tests/check_run_bioinformatics_holdout.py`

- [ ] **Step 1: Write failing execution tests**

Use temporary fake workflow and comparator executables. Require a completed attempt to contain:

```text
attempt-config.json
environment.json
authority/output/**
authority/report.json
authority/stdout.log
authority/stderr.log
authority/time.txt
authority/gpu-memory.csv
candidate/output/**
candidate/report.json
candidate/stdout.log
candidate/stderr.log
candidate/time.txt
candidate/gpu-memory.csv
verified/output/**
verified/report.json
verified/stdout.log
verified/stderr.log
verified/time.txt
verified/gpu-memory.csv
comparator/details.tsv
comparator/stdout.log
comparator/stderr.log
comparison.json
attempt-summary.json
attempt-artifacts.tsv
attempt-complete.json
```

Assert argv arrays preserve paths with spaces/metacharacters, each mode receives the same query/target/rule/assembly/annotation/top-K contract, raw authority and candidate outputs are compared independently, reports and logs remain unmodified, resource fields use `NA` when unavailable, and the receipt hashes every retained file.

- [ ] **Step 2: Run the execution tests and verify RED**

Expected: FAIL because measured command execution and attempt receipts are absent.

- [ ] **Step 3: Implement execution using existing helpers**

Reuse the existing paper `GpuSampler` and environment capture command. Wrap each top-level CLI invocation with `/usr/bin/time -v` when available, use a process group, enforce an outer timeout larger than the CLI's per-backend timeout, and retain exact stdout/stderr. Invoke:

```text
cpu-authority: --mode cpu-authority --contract all-ranked-top5
candidate:     --mode fast-experimental --contract auto
verified:      --mode verified --contract all-ranked-top5
```

Locate exactly one raw TFOsorted file in successful authority/candidate output directories and run the existing comparator with `--k 5 --details`. Treat comparator return codes 0 and 1 as evaluated results; any other code is a technical comparator failure. Parse score, stability, Nt, tie, full missing/extra, and row-count metrics into `comparison.json`.

Run all three top-level modes even when an earlier mode fails. The summary must distinguish scientific mismatch from technical failure and cross-check the verified report's publication/fallback behavior without deleting an unfavorable output.

- [ ] **Step 4: Publish immutable receipts**

Build each attempt in a sibling `.partial.<pid>` directory, fsync JSON/TSV receipts, create a complete artifact manifest, and atomically rename it to the attempt ID. If orchestration fails, publish a retained technical-failure attempt with the exception and all artifacts produced so far. Never overwrite an attempt directory.

- [ ] **Step 5: Run execution tests and verify GREEN**

Run the focused suite and confirm successful, mismatch, candidate failure, comparator failure, timeout, OOM-report, and verified-fallback fixtures all remain represented.

### Task 3: Add pilot/formal separation, resume, and complete tables

**Files:**
- Modify: `reproduce/bioinformatics/run_holdout.py`
- Modify: `tests/check_run_bioinformatics_holdout.py`

- [ ] **Step 1: Write failing orchestration tests**

Require:

```python
self.assertFalse((artifact_root / "formal").exists())
self.assertEqual(formal_table_rows, 36)
self.assertEqual({row["attempt_id"] for row in formal_table}, expected_attempt_ids)
```

Test that formal mode rejects a missing/tampered pilot receipt; pilot mode always uses the frozen pilot ID; formal mode cannot select a subset; mismatches do not stop later attempts; technical failures remain rows; `--resume` reuses only checksum-valid complete attempts; altered config, report, output, or receipt files fail closed; duplicate invocation without `--resume` fails; and no automatic retry or replacement attempt appears.

- [ ] **Step 2: Run orchestration tests and verify RED**

Expected: FAIL because pilot/formal namespaces, resume validation, and tables are absent.

- [ ] **Step 3: Implement pilot and formal orchestration**

Use these namespaces:

```text
<artifact-root>/pilot/pilot__hq01_ht01__repeat00/
<artifact-root>/formal/<workload_id>__repeatNN/
```

Formal mode validates the pilot complete receipt and executes all 36 primary attempts in frozen order. `--resume` validates every artifact SHA and config digest before reuse. After each attempt, rebuild atomic derived tables by scanning immutable receipts rather than appending mutable state:

```text
formal-attempts.tsv
formal-failures.tsv
formal-artifacts.tsv
formal-summary.json
```

Return success when the full formal plan is represented, even if scientific mismatches exist. Return nonzero and state the incomplete count if an unexpected orchestration failure prevents representation of every planned attempt.

- [ ] **Step 4: Run orchestration tests and verify GREEN**

Run the full focused suite twice to confirm byte-stable planning and receipt-derived tables.

### Task 4: Add the pre-execution repository gate

**Files:**
- Create: `scripts/check_bioinformatics_phase2_preexecution.sh`
- Modify: `Makefile`
- Modify: `paper/bioinformatics/submission_manifest.tsv`
- Modify: `tests/check_run_bioinformatics_holdout.py`

- [ ] **Step 1: Write failing integration checks**

Require a Make target named `check-bioinformatics-phase2-preexecution` that depends on `check-bioinformatics-phase2-freeze`, runs both historical-analysis and runner suites, validates the execution supplement and submission-manifest rows, and exits only while no pilot/formal artifact receipt exists.

- [ ] **Step 2: Run the integration test and verify RED**

Run `python3 tests/check_run_bioinformatics_holdout.py`; expected failure is the missing gate/manifest integration.

- [ ] **Step 3: Implement the gate and manifest entries**

Add submission artifacts for the historical analysis, runner, tests, execution supplement, and pre-execution checker. The checker must print exact workload/attempt/mode/backend counts and `holdout_execution_started=0`.

- [ ] **Step 4: Run all pre-execution verification**

Run:

```bash
python3 tests/check_analyze_bioinformatics_frozen_contracts.py
python3 tests/check_run_bioinformatics_holdout.py
make check-bioinformatics-phase2-preexecution
git diff --check
```

Expected: all tests pass; workload count 24; formal attempt count 36; top-level runs 108; backend executions 144; pilot/formal execution started 0.

- [ ] **Step 5: Review and commit before execution**

Obtain separate specification and code-quality approvals. Stage only the runner checkpoint files, inspect `git diff --cached --check` and `git diff --cached --stat`, then commit:

```bash
git commit -m "repro: preregister Phase 2 holdout execution"
```

Do not run `--pilot` or `--formal` until this commit exists.
