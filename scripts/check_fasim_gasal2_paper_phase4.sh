#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${WORK:-$ROOT/.tmp/check_fasim_gasal2_paper_phase4}"
ARTIFACT_ROOT="${ARTIFACT_ROOT:-$ROOT/.paper-artifacts/runtime-epoch-0-pre-freeze/phase4-ablation-resource}"
GOAL="$ROOT/goal-final.md"
REPORT="$ROOT/paper/ablation_resource_report.md"
ARTIFACT_MANIFEST="$ROOT/paper/phase4_artifact_manifest.tsv"
RUNS="$ROOT/paper/source_data/ablation_resource_runs_pre_freeze.tsv"
PAIRS="$ROOT/paper/source_data/ablation_resource_pairs_pre_freeze.tsv"
SUMMARY="$ROOT/paper/source_data/ablation_resource_summary_pre_freeze.tsv"
LINKED="$ROOT/paper/source_data/ablation_linked_contrasts_pre_freeze.tsv"
RESOURCES="$ROOT/paper/source_data/resource_boundary_pre_freeze.tsv"
FAILURES="$ROOT/paper/source_data/ablation_resource_failures_pre_freeze.tsv"
INVENTORY="$ROOT/paper/artifact_inventory.tsv"
CLAIMS="$ROOT/paper/claim_evidence.tsv"
DRIVER="$ROOT/scripts/run_fasim_gasal2_paper_phase4.py"
SUMMARIZER="$ROOT/scripts/summarize_fasim_gasal2_paper_phase4.py"
HARNESS_TEST="$ROOT/tests/check_run_fasim_gasal2_paper_benchmarks.py"
DRIVER_TEST="$ROOT/tests/check_run_fasim_gasal2_paper_phase4.py"
SUMMARY_TEST="$ROOT/tests/check_summarize_fasim_gasal2_paper_phase4.py"
MULTIWORKER="$ROOT/.tmp/characterize_fasim_gasal2_flush_two_slot_multi_worker_2gpu_v4/summary.json"
RUNTIME_COMMIT="0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"

for path in \
  "$GOAL" "$REPORT" "$ARTIFACT_MANIFEST" "$RUNS" "$PAIRS" "$SUMMARY" \
  "$LINKED" "$RESOURCES" "$FAILURES" "$INVENTORY" "$CLAIMS" \
  "$DRIVER" "$SUMMARIZER" "$HARNESS_TEST" "$DRIVER_TEST" "$SUMMARY_TEST" \
  "$MULTIWORKER" "$ARTIFACT_ROOT/phase4-runs.tsv" \
  "$ARTIFACT_ROOT/phase4-pairs.tsv" "$ARTIFACT_ROOT/phase4-failures.tsv" \
  "$ARTIFACT_ROOT/phase4-artifacts.tsv"; do
  if [[ ! -s "$path" ]]; then
    echo "missing paper Phase 4 dependency: $path" >&2
    exit 1
  fi
done

if [[ -n "$(git -C "$ROOT" diff --name-only "$RUNTIME_COMMIT" -- fasim)" ]]; then
  echo "paper runtime changed under fasim/ after frozen runtime commit" >&2
  exit 1
fi

rm -rf "$WORK"
mkdir -p "$WORK/generated-paper"

python3 "$HARNESS_TEST"
python3 "$DRIVER_TEST"
python3 "$SUMMARY_TEST"
python3 "$SUMMARIZER" \
  --artifact-root "$ARTIFACT_ROOT" \
  --paper-dir "$WORK/generated-paper" \
  --multiworker-summary "$MULTIWORKER" >"$WORK/summarize.stdout"

for relative in \
  ablation_resource_report.md \
  phase4_artifact_manifest.tsv \
  source_data/ablation_resource_runs_pre_freeze.tsv \
  source_data/ablation_resource_pairs_pre_freeze.tsv \
  source_data/ablation_resource_summary_pre_freeze.tsv \
  source_data/ablation_linked_contrasts_pre_freeze.tsv \
  source_data/resource_boundary_pre_freeze.tsv \
  source_data/ablation_resource_failures_pre_freeze.tsv; do
  cmp "$ROOT/paper/$relative" "$WORK/generated-paper/$relative"
done

python3 - \
  "$ROOT" "$ARTIFACT_ROOT" "$GOAL" "$REPORT" "$ARTIFACT_MANIFEST" \
  "$RUNS" "$PAIRS" "$SUMMARY" "$LINKED" "$RESOURCES" "$FAILURES" \
  "$INVENTORY" "$CLAIMS" "$MULTIWORKER" <<'PY'
from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path


(
    root,
    artifact_root,
    goal_path,
    report_path,
    artifact_manifest_path,
    runs_path,
    pairs_path,
    summary_path,
    linked_path,
    resources_path,
    failures_path,
    inventory_path,
    claims_path,
    multiworker_path,
) = (Path(value).resolve() for value in sys.argv[1:])

runtime_commit = "0d11aa2d61b7ccda59b462ab8e0750dad17ee18f"
expected_counts = {
    "c5_archive_h19_2mb": 3,
    "c5_archive_large_synthetic": 3,
    "c6_exact_h19_2mb": 3,
    "c6_exact_kcnq_segment_chr22": 3,
}


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


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON object required: {path}")
    return payload


def canonical_config_digest(payload: dict[str, object]) -> str:
    comparable = dict(payload)
    comparable.pop("config_digest_sha256", None)
    encoded = json.dumps(comparable, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


goal = goal_path.read_text(encoding="utf-8")
for phrase in (
    "active_phase = 5",
    "phase_4_status = pass",
    "last_completed_phase = 4",
    "last_decision = paper_ablation_resource_archive_characterized",
    "last_evidence_doc = paper/ablation_resource_report.md",
    "last_test_command = make check-fasim-gasal2-paper-phase4",
    "last_commit = bench: add paper ablation, resource and archive characterization",
):
    if phrase not in goal:
        raise SystemExit(f"goal-final Phase 4 state missing: {phrase}")

pair_fields, pairs = read_tsv(pairs_path)
required_pair_fields = {
    "pair_id_text", "workload_id", "claim_id", "pair_id", "runtime_epoch",
    "runtime_commit", "output_contract", "baseline_wall_seconds",
    "candidate_wall_seconds", "paired_speedup", "full_output_byte_equal",
    "fallbacks", "overflow_batches", "status", "decision", "pair_summary_path",
}
if not required_pair_fields.issubset(pair_fields):
    raise SystemExit("Phase 4 pair table is missing required fields")
if len(pairs) != 12 or Counter(row["workload_id"] for row in pairs) != Counter(expected_counts):
    raise SystemExit("Phase 4 pair count or workload set drifted")
if len({row["pair_id_text"] for row in pairs}) != len(pairs):
    raise SystemExit("duplicate Phase 4 pair ID")

for row in pairs:
    pair_id = row["pair_id_text"]
    workload = row["workload_id"]
    if row["runtime_epoch"] != "0" or row["runtime_commit"] != runtime_commit:
        raise SystemExit(f"runtime epoch mixing: {pair_id}")
    if row["status"] != "clean" or row["full_output_byte_equal"] != "1":
        raise SystemExit(f"Phase 4 output contract failed: {pair_id}")
    if row["fallbacks"] != "0" or row["overflow_batches"] != "0":
        raise SystemExit(f"fallback or overflow in {pair_id}")
    baseline = float(row["baseline_wall_seconds"])
    candidate = float(row["candidate_wall_seconds"])
    speedup = float(row["paired_speedup"])
    if min(baseline, candidate, speedup) <= 0 or not math.isclose(
        speedup, baseline / candidate, rel_tol=1e-12, abs_tol=1e-12
    ):
        raise SystemExit(f"paired speedup arithmetic mismatch: {pair_id}")
    if Path(row["pair_summary_path"]).is_absolute():
        raise SystemExit(f"machine-specific pair path exported: {pair_id}")
    pair_summary = artifact_root / row["pair_summary_path"]
    pair_config = pair_summary.with_name("pair-config.json")
    pair_complete = pair_summary.with_name("pair-complete.json")
    for path in (pair_summary, pair_config, pair_complete):
        if not path.is_file():
            raise SystemExit(f"missing pair receipt: {path}")
    config = load_json(pair_config)
    complete = load_json(pair_complete)
    if config.get("config_digest_sha256") != canonical_config_digest(config):
        raise SystemExit(f"pair config digest mismatch: {pair_id}")
    if complete.get("summary_sha256") != sha256(pair_summary):
        raise SystemExit(f"pair summary digest mismatch: {pair_id}")

    if workload == "c5_archive_h19_2mb":
        if (
            row["archive_restore_clean"] != "1"
            or float(row["storage_reduction_ratio"]) <= 1
            or float(row["restore_wall_seconds"]) <= 0
            or float(row["candidate_run_restore_wall_seconds"]) <= float(row["candidate_wall_seconds"])
        ):
            raise SystemExit(f"archive restore/storage gate failed: {pair_id}")
    elif workload == "c5_archive_large_synthetic":
        if (
            float(row["peak_rss_reduction_fraction"]) < 0.10
            or int(row["peak_rss_reduction_kb"]) < 8192
            or float(row["sqlite_merge_wall_seconds"]) <= float(row["memory_merge_wall_seconds"])
        ):
            raise SystemExit(f"bounded merge trade-off gate failed: {pair_id}")
    else:
        if any(row[field] != "1" for field in (
            "all_three_top5_equal", "boundary_ties_equal", "exact_work_equal",
            "request_counts_equal", "archive_restore_clean",
        )):
            raise SystemExit(f"exact-column correctness/work gate failed: {pair_id}")
        if (
            float(row["candidate_exact_stage_seconds"]) >= float(row["baseline_exact_stage_seconds"])
            or float(row["exact_stage_speedup"]) <= 1
            or int(row["exact_tasks"]) <= 0
            or int(row["exact_cells"]) <= 0
            or int(row["gasal2_requests"]) <= 0
            or int(row["traceback_requests"]) <= 0
        ):
            raise SystemExit(f"exact-column stage gate failed: {pair_id}")

_, runs = read_tsv(runs_path)
if len(runs) != 32 or Counter(row["warmup"] for row in runs) != Counter({"0": 24, "1": 8}):
    raise SystemExit("Phase 4 timed/warmup run count drifted")
if any(Path(row["receipt_path"]).is_absolute() for row in runs):
    raise SystemExit("machine-specific run path exported")
unsafe_flags = (
    "FASIM_GASAL2_LIMITED_TRACEBACK",
    "FASIM_GASAL2_TRACEBACK_THRESHOLD",
    "FASIM_TOP5_GASAL2_NT_SUM_SPAN_PRUNE",
)
for row in runs:
    receipt = artifact_root / row["receipt_path"]
    run_dir = receipt.parent
    execution = load_json(run_dir / "execution.json")
    command = " ".join(str(value) for value in execution.get("command", []))
    if any(flag in command for flag in unsafe_flags):
        raise SystemExit(f"unsafe runtime flag in Phase 4 run: {row['run_id']}")

_, summaries = read_tsv(summary_path)
if len(summaries) != 4 or any(row["valid_pairs"] != "3" for row in summaries):
    raise SystemExit("Phase 4 workload summary drifted")
summary_map = {row["workload_id"]: row for row in summaries}
if float(summary_map["c5_archive_h19_2mb"]["median_storage_reduction_ratio"]) <= 5:
    raise SystemExit("archive storage reduction summary regressed")
if float(summary_map["c5_archive_large_synthetic"]["median_paired_speedup"]) >= 1:
    raise SystemExit("SQLite wall cost was hidden from Phase 4 summary")
for workload in ("c6_exact_h19_2mb", "c6_exact_kcnq_segment_chr22"):
    row = summary_map[workload]
    if row["exact_work_equal_all"] != "1" or row["request_counts_equal_all"] != "1":
        raise SystemExit(f"exact work/request summary failed: {workload}")
    if float(row["median_exact_stage_speedup"]) <= float(row["median_paired_speedup"]):
        raise SystemExit(f"stage and end-to-end effects conflated: {workload}")

_, linked = read_tsv(linked_path)
if len(linked) != 3 or any(row["same_workload_abc_triad"] != "0" for row in linked):
    raise SystemExit("linked ablation triad scope drifted")
if {row["contrast"] for row in linked} != {"authority_vs_checked_gasal2", "sync_vs_two_slot"}:
    raise SystemExit("linked ablation contrasts are incomplete")

_, resources = read_tsv(resources_path)
if len(resources) != 8:
    raise SystemExit("Phase 4 resource boundary row count drifted")
resource_map = {row["resource_id"]: row for row in resources}
for resource_id in (
    "phase4_c5_archive_h19_2mb",
    "phase4_c6_exact_h19_2mb",
    "phase4_c6_exact_kcnq_segment_chr22",
):
    row = resource_map[resource_id]
    if float(row["reserved_headroom_mib"]) <= 0 or row["pinned_host_peak_bytes"] != "NA":
        raise SystemExit(f"resource headroom/method gate failed: {resource_id}")
if resource_map["historical_two_slot_workers_1"]["gpu_count"] != "1":
    raise SystemExit("historical active GPU count is incorrect")
for workers in (4, 6):
    row = resource_map[f"historical_two_slot_workers_{workers}"]
    if row["status"] != "oom" or row["oom"] != "1":
        raise SystemExit(f"historical high-density OOM was hidden: workers={workers}")
if sha256(multiworker_path) != "b8c33bf7c848881674c766bcae15d53afe95fa8f4e88f090ac384208ba685932":
    raise SystemExit("historical multi-worker summary digest drifted")

_, failures = read_tsv(failures_path)
if failures:
    raise SystemExit(f"unexpected Phase 4 technical failures: {len(failures)}")

artifact_fields, artifacts = read_tsv(artifact_manifest_path)
if artifact_fields != ["artifact_path", "size_bytes", "sha256"] or len(artifacts) != 539:
    raise SystemExit("Phase 4 artifact manifest schema/count drifted")
if sha256(artifact_manifest_path) != "6bc1e07681db54d0c543512b835b0030b702c366a31645b480e20bf4aedf4fec":
    raise SystemExit("Phase 4 artifact manifest digest drifted")
for row in artifacts:
    path = artifact_root / row["artifact_path"]
    if not path.is_file() or path.stat().st_size != int(row["size_bytes"]) or sha256(path) != row["sha256"]:
        raise SystemExit(f"immutable Phase 4 artifact mismatch: {path}")
if any(path.name.startswith("c7_") for path in artifact_root.iterdir()):
    raise SystemExit("forbidden full long-query workload appeared in Phase 4 root")

report = report_path.read_text(encoding="utf-8")
for phrase in (
    "not_available_under_checked_contract",
    "This is a bounded-memory trade-off, not compute acceleration.",
    "Stage speedup is reported separately from end-to-end speedup.",
    "Pinned-host peak is unavailable",
    "full_121_segment_runs = 0",
):
    if phrase not in report:
        raise SystemExit(f"Phase 4 report missing: {phrase}")

_, claims = read_tsv(claims_path)
claims_map = {row["claim_id"]: row for row in claims}
if claims_map["C5"]["status"] != "phase4_archive_clean" or claims_map["C6"]["status"] != "phase4_component_clean":
    raise SystemExit("C5/C6 claim ledger was not updated from Phase 4 evidence")
if claims_map["C5"]["current_evidence_path"] != "paper/ablation_resource_report.md":
    raise SystemExit("C5 evidence path drifted")

_, inventory = read_tsv(inventory_path)
inventory_paths = {row["artifact_path"] for row in inventory}
required_inventory = {
    "paper/ablation_resource_report.md",
    "paper/phase4_artifact_manifest.tsv",
    "paper/source_data/ablation_resource_runs_pre_freeze.tsv",
    "paper/source_data/ablation_resource_pairs_pre_freeze.tsv",
    "paper/source_data/ablation_resource_summary_pre_freeze.tsv",
    "paper/source_data/ablation_linked_contrasts_pre_freeze.tsv",
    "paper/source_data/resource_boundary_pre_freeze.tsv",
    "paper/source_data/ablation_resource_failures_pre_freeze.tsv",
}
if not required_inventory.issubset(inventory_paths):
    raise SystemExit("Phase 4 generated evidence is missing from artifact inventory")

print("GASAL2 paper Phase 4 gate OK")
print("phase4_pairs=12")
print("archive_storage_ratio=5.715078")
print("synthetic_sqlite_rss_reduction_fraction=0.336190")
print("exact_h19_end_to_end_speedup=1.082711")
print("exact_kcnq_end_to_end_speedup=1.115307")
print("technical_failures=0")
PY

echo "GASAL2 paper Phase 4 checks OK"
