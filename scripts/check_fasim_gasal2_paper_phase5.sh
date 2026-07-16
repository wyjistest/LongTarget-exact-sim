#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-$ROOT/.tmp/check_fasim_gasal2_paper_phase5}"
SOURCE="$ROOT/paper/source_data"
GOAL="$ROOT/goal-final.md"
CLAIMS="$ROOT/paper/claim_evidence.tsv"
FREEZE_ID="paper-data-v1-dccfd49-20260716"
RUNTIME_COMMIT="0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"

for path in \
  "$GOAL" "$CLAIMS" \
  "$ROOT/reproduce/collect_results.py" \
  "$ROOT/reproduce/analyze_results.py" \
  "$ROOT/reproduce/freeze_results.py" \
  "$ROOT/tests/check_collect_fasim_gasal2_paper_results.py" \
  "$ROOT/tests/check_analyze_fasim_gasal2_paper_results.py" \
  "$ROOT/tests/check_freeze_fasim_gasal2_paper_results.py" \
  "$SOURCE/DATA_FREEZE.md" "$SOURCE/source_data_manifest.tsv"; do
  if [[ ! -s "$path" ]]; then
    echo "missing paper Phase 5 dependency: $path" >&2
    exit 1
  fi
done

if [[ -n "$(git -C "$ROOT" diff --name-only "$RUNTIME_COMMIT" -- fasim)" ]]; then
  echo "paper runtime changed under fasim/ after frozen runtime commit" >&2
  exit 1
fi

python3 "$ROOT/tests/check_collect_fasim_gasal2_paper_results.py"
python3 "$ROOT/tests/check_analyze_fasim_gasal2_paper_results.py"
python3 "$ROOT/tests/check_freeze_fasim_gasal2_paper_results.py"
python3 -m py_compile \
  "$ROOT/reproduce/collect_results.py" \
  "$ROOT/reproduce/analyze_results.py" \
  "$ROOT/reproduce/freeze_results.py"

rm -rf "$WORK"
mkdir -p "$WORK/source_data"
cp "$SOURCE"/*_pre_freeze.tsv "$WORK/source_data/"
python3 "$ROOT/reproduce/collect_results.py" \
  --source-dir "$WORK/source_data" \
  --data-freeze-id "$FREEZE_ID" >"$WORK/collect.stdout"
python3 "$ROOT/reproduce/analyze_results.py" \
  --pairs "$WORK/source_data/paired_speedups.tsv" \
  --summary-tsv "$WORK/source_data/paired_speedup_summary.tsv" \
  --summary-json "$WORK/source_data/paired_speedup_summary.json" >"$WORK/analyze.stdout"
python3 "$ROOT/reproduce/freeze_results.py" \
  --source-dir "$WORK/source_data" \
  --data-freeze-id "$FREEZE_ID" >"$WORK/freeze.stdout"

for relative in \
  benchmark_runs.tsv paired_speedups.tsv correctness.tsv generalization.tsv \
  ablation.tsv resources.tsv archive_first.tsv operating_envelope.tsv \
  exclusions.tsv paired_speedup_summary.tsv paired_speedup_summary.json \
  source_data_manifest.tsv DATA_FREEZE.md; do
  cmp "$SOURCE/$relative" "$WORK/source_data/$relative"
done

python3 - "$ROOT" "$GOAL" "$CLAIMS" "$SOURCE" <<'PY'
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path


root, goal_path, claims_path, source = (Path(value).resolve() for value in sys.argv[1:])
freeze_id = "paper-data-v1-dccfd49-20260716"
runtime_commit = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"missing TSV header: {path}")
        return reader.fieldnames, list(reader)


goal = goal_path.read_text(encoding="utf-8")
state: dict[str, str] = {}
for raw in goal.splitlines():
    if " = " in raw:
        key, value = raw.split(" = ", 1)
        state.setdefault(key, value)
active = int(state.get("active_phase", "-1"))
completed = int(state.get("last_completed_phase", "-1"))
if active < 6 or completed < 5 or state.get("phase_5_status") != "pass":
    raise SystemExit("goal state has not completed paper Phase 5")
if state.get("data_freeze_id") != freeze_id:
    raise SystemExit("goal data_freeze_id drifted")
if active == 6:
    expected = {
        "last_completed_phase": "5",
        "last_decision": "paper_source_data_frozen",
        "last_evidence_doc": "paper/source_data/DATA_FREEZE.md",
        "last_test_command": "make check-fasim-gasal2-paper-phase5",
        "last_commit": "analysis: freeze GASAL2-LongTarget paper source data",
    }
    for key, value in expected.items():
        if state.get(key) != value:
            raise SystemExit(f"Phase 5 terminal state mismatch: {key}")

expected_counts = {
    "benchmark_runs.tsv": 167,
    "paired_speedups.tsv": 61,
    "correctness.tsv": 64,
    "generalization.tsv": 16,
    "ablation.tsv": 7,
    "resources.tsv": 8,
    "archive_first.tsv": 6,
    "operating_envelope.tsv": 6,
    "exclusions.tsv": 56,
    "paired_speedup_summary.tsv": 21,
}
for name, count in expected_counts.items():
    _, rows = read_tsv(source / name)
    if len(rows) != count or {row["data_freeze_id"] for row in rows} != {freeze_id}:
        raise SystemExit(f"source-data row count or freeze ID drifted: {name}")

pair_fields, pairs = read_tsv(source / "paired_speedups.tsv")
required_pair_fields = {
    "runtime_epoch", "runtime_commit", "machine_id", "workload_id", "pair_id_text",
    "preset_id", "output_contract", "baseline_wall_seconds", "candidate_wall_seconds",
    "paired_speedup", "status", "excluded", "artifact_path", "artifact_sha256",
}
if not required_pair_fields.issubset(pair_fields):
    raise SystemExit("frozen paired table is missing required fields")
if len({row["pair_id_text"] for row in pairs}) != len(pairs):
    raise SystemExit("duplicate frozen pair ID")
for row in pairs:
    if row["runtime_epoch"] != "0" or row["runtime_commit"] != runtime_commit:
        raise SystemExit(f"runtime epoch mixing: {row['pair_id_text']}")
    expected = float(row["baseline_wall_seconds"]) / float(row["candidate_wall_seconds"])
    if not math.isclose(expected, float(row["paired_speedup"]), rel_tol=1e-12, abs_tol=1e-12):
        raise SystemExit(f"paired speedup arithmetic drift: {row['pair_id_text']}")
    if row["excluded"] != "0" or len(row["artifact_sha256"]) != 64:
        raise SystemExit(f"pair inclusion/provenance drift: {row['pair_id_text']}")
if Counter(row["status"] for row in pairs) != Counter({"clean": 54, "mismatch": 7}):
    raise SystemExit("mismatch pairs were hidden or reclassified")

_, runs = read_tsv(source / "benchmark_runs.tsv")
if len({row["run_id"] for row in runs}) != len(runs):
    raise SystemExit("duplicate frozen run ID")
if any(len(row["artifact_sha256"]) != 64 for row in runs):
    raise SystemExit("run artifact digest missing")
excluded_runs = {row["run_id"] for row in runs if row["excluded"] == "1"}
_, exclusions = read_tsv(source / "exclusions.tsv")
listed = {row["record_id"] for row in exclusions if row["record_type"] == "run"}
if excluded_runs != listed:
    raise SystemExit("excluded runs are not represented exactly in exclusions.tsv")

_, correctness = read_tsv(source / "correctness.tsv")
paired_correctness = [row for row in correctness if row["row_type"] == "paired_contract"]
guards = [row for row in correctness if row["row_type"] == "preflight_guard"]
if Counter(row["status"] for row in paired_correctness) != Counter({"clean": 54, "mismatch": 7}):
    raise SystemExit("correctness mismatch accounting drifted")
if len(guards) != 3 or any(
    row["status"] != "guarded" or row["supported"] != "0" or row["gpu_fast_path_executed"] != "0"
    for row in guards
):
    raise SystemExit("full-length fail-closed guards drifted")

summary_fields, summaries = read_tsv(source / "paired_speedup_summary.tsv")
if "paired_speedup_bootstrap_ci_low" not in summary_fields:
    raise SystemExit("bootstrap interval fields missing")
for row in summaries:
    n = int(row["n"])
    has_ci = row["paired_speedup_bootstrap_ci_low"] != "NA"
    if has_ci != (n >= 3) or row["analysis_seed"] != "20260715":
        raise SystemExit(f"bootstrap contract drifted: {row['workload_id']}")

_, manifest = read_tsv(source / "source_data_manifest.tsv")
if len(manifest) != 11 or any(row["data_freeze_id"] != freeze_id for row in manifest):
    raise SystemExit("source-data manifest count/freeze drifted")
for row in manifest:
    path = source / row["path"]
    if not path.is_file() or path.stat().st_size != int(row["size_bytes"]) or sha256(path) != row["sha256"]:
        raise SystemExit(f"source-data manifest mismatch: {path}")
if {row["path"] for row in manifest} & {"source_data_manifest.tsv", "DATA_FREEZE.md"}:
    raise SystemExit("source-data manifest is self-referential")

_, claims = read_tsv(claims_path)
if {row["claim_id"] for row in claims} != {f"C{i}" for i in range(1, 8)}:
    raise SystemExit("claim ledger is incomplete")
for row in claims:
    if not row["status"].startswith("frozen"):
        raise SystemExit(f"claim is not frozen: {row['claim_id']}")
    if not row["source_data_filter"] or not row["allowed_manuscript_wording"]:
        raise SystemExit(f"claim final filter/wording missing: {row['claim_id']}")
claims_map = {row["claim_id"]: row for row in claims}
summary_map = {row["workload_id"]: row for row in summaries}
if not math.isclose(
    float(claims_map["C1"]["current_value"].split("=")[1]),
    float(summary_map["c1_h19_chr21_chr22_fast_topk"]["median_paired_speedup"]),
    rel_tol=1e-6,
):
    raise SystemExit("C1 ledger estimate does not trace to frozen summary")
_, generalization = read_tsv(source / "generalization.tsv")
supported = [row for row in generalization if row["row_type"] == "supported_query"]
if Counter(row["status"] for row in supported) != Counter({"clean": 10, "mismatch": 3}):
    raise SystemExit("C2 workload decision drifted")

document = (source / "DATA_FREEZE.md").read_text(encoding="utf-8")
for phrase in (
    freeze_id, runtime_commit, "analysis_seed = 20260715",
    "Full KCNQ1OT1 transcript coverage was not run.", "Full hg38 was not run.",
):
    if phrase not in document:
        raise SystemExit(f"data freeze document missing: {phrase}")

analyzer = (root / "reproduce/analyze_results.py").read_text(encoding="utf-8")
for forbidden in ("38.320882", "1.151205", "5.715078", "1.087369"):
    if forbidden in analyzer:
        raise SystemExit(f"manual result constant found in analyzer: {forbidden}")

print("GASAL2 paper Phase 5 gate OK")
print("data_freeze_id=paper-data-v1-dccfd49-20260716")
print("benchmark_runs=167")
print("paired_speedups=61")
print("paired_clean=54")
print("paired_mismatch=7")
print("bootstrap_seed=20260715")
PY

echo "GASAL2 paper Phase 5 checks OK"
